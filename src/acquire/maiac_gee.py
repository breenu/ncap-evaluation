"""Raw MAIAC AOD (MCD19A2 C6.1, 1 km) reduced to unit-month sums on Google Earth Engine (Phase 8b).

Rules: DEC-174 to DEC-178, committed and pushed before any AOD value was pulled. Settings: config/maiac.yaml.
Nothing is done in the GEE web interface; credentials stay in ~/.config/earthengine (hard rule 5).

Per overpass image: Optical_Depth_055 x 0.001, masked by each QA filter (primary, relaxed; DEC-175).
Per pixel and UTC day: the mean over that day's valid overpasses. Per pixel and month: the mean of the valid
daily values and the number of valid days (DEC-176). Per unit and month, with GEE's coverage-weighted sum
over the polygon (c = the fraction of each pixel inside it), in the granules' own sinusoidal grid:

    w      sum w.c          population weight (GHS-POP 2020, R2023A, onto the MODIS grid)
    px     sum c            pixels (equal-area grid, so area)
    pw_v   sum w.c.v        v = 1 where the pixel has a value that month (primary filter)
    pw_a   sum w.c.v.aod    aod = the pixel-month mean
    pw_d   sum w.c.days     days = valid days that month
    ar_v, ar_a, ar_d        the same with area weights (primary filter)
    rw_v, rw_a, rw_d        population-weighted, relaxed filter

Means and coverage are formed locally (src/causal/maiac.py). Commands, in order:

    python -m src.acquire.maiac_gee check      collection structure, band, scale, projection (DEC-174)
    python -m src.acquire.maiac_gee pilot      one month -> data/interim/maiac_gee_pilot/, EECU projection (DEC-178)
    python -m src.acquire.maiac_gee submit     one Export.table.toDrive per year (skips years done or running; DEC-183)
    python -m src.acquire.maiac_gee status
    python -m src.acquire.maiac_gee download   finished tables -> data/raw/maiac_gee/ with the manifest
"""

import hashlib
import json
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

import geopandas as gpd
import pandas as pd

from src.acquire.common import finish
from src.common.manifest import download, sha256_file
from src.common.paths import CONFIG, INTERIM, ROOT, load_yaml, raw_dir

CFG = load_yaml(CONFIG / "maiac.yaml")
SCRIPT = Path(__file__)
STATE = INTERIM / "maiac_gee"
PILOT = INTERIM / "maiac_gee_pilot"
SUMS = ["w", "px", "pw_v", "pw_a", "pw_d", "ar_v", "ar_a", "ar_d", "rw_v", "rw_a", "rw_d"]
COLUMNS = ["unit_id", "year", "month", *SUMS]


# ---------------------------------------------------------------- local helpers (no Earth Engine)


def units_geojson() -> dict:
    """The 1,036 Layer A units (treated + controls) as GeoJSON in EPSG:4326, unit_id only (DEC-178)."""
    u = pd.read_csv(ROOT / "data/processed/causal/design_units.csv")
    keep = set(u.unit_id[u.role_a.isin(["treated", "control"])])
    g = gpd.read_file(INTERIM / "sat_units.gpkg")
    g = g[g.unit_id.isin(keep)][["unit_id", "geometry"]].to_crs(4326).sort_values("unit_id")
    if len(g) != 1036:
        raise ValueError(f"expected 1,036 Layer A units, found {len(g)}")
    return json.loads(g.to_json(drop_id=True))


def request_params(proj_info: dict | None = None) -> dict:
    """Everything that defines the export, for the manifest (DEC-178)."""
    gj = units_geojson()
    keys = ("collection", "band", "scale", "qa_band", "qa_fields", "filters", "population", "population_band",
            "reduce_max_pixels", "years")  # fmt: skip
    return {**{k: CFG[k] for k in keys}, "day": "UTC date of system:time_start",
            "reducer": "ee.Reducer.sum() (coverage-weighted), crs = the granules' projection",
            "units": len(gj["features"]),
            "units_geojson_sha256": hashlib.sha256(json.dumps(gj, sort_keys=True).encode()).hexdigest(),
            "projection": proj_info}  # fmt: skip


def sha(obj) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, default=str).encode()).hexdigest()


def script_commit() -> str:
    """The commit holding this script; refuses to run with uncommitted changes to it (DEC-178)."""
    rel = SCRIPT.relative_to(ROOT).as_posix()
    dirty = subprocess.run(["git", "status", "--porcelain", "--", rel, "config/maiac.yaml"], cwd=ROOT,
                           capture_output=True, text=True, check=True).stdout.strip()  # fmt: skip
    if dirty:
        raise SystemExit(f"commit {rel} and config/maiac.yaml before exporting (DEC-178): the manifest names the commit")
    return subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()


def qa_value(fields: dict, values: dict) -> int:
    """Pack field values into an AOD_QA integer (used by the tests to check the bit logic)."""
    return sum(v << fields[k][0] for k, v in values.items())


def qa_accepts(qa: int, fields: dict, accept: dict) -> bool:
    """Pure-Python twin of `qa_mask`: does an AOD_QA value pass a filter?"""
    return all(((qa >> fields[k][0]) & ((1 << fields[k][1]) - 1)) in accept[k] for k in accept)


# ---------------------------------------------------------------- Earth Engine


def init():
    import ee

    ee.Initialize(project=CFG["gee_project"])
    return ee


def qa_mask(ee, qa, accept: dict):
    """1 where every QA field takes an accepted value (DEC-175)."""
    m = None
    for field, vals in accept.items():
        start, n = CFG["qa_fields"][field]
        b = qa.rightShift(start).bitwiseAnd((1 << n) - 1)
        f = None
        for v in vals:
            f = b.eq(v) if f is None else f.Or(b.eq(v))
        m = f if m is None else m.And(f)
    return m


def collection(ee):
    return ee.ImageCollection(CFG["collection"])


def projection(ee):
    return collection(ee).first().select(CFG["band"]).projection()


def ee_units(ee):
    feats = [ee.Feature(ee.Geometry(f["geometry"], "EPSG:4326", False), {"unit_id": f["properties"]["unit_id"]})
             for f in units_geojson()["features"]]  # fmt: skip
    return ee.FeatureCollection(feats)


def weights(ee, proj):
    """People per MODIS pixel: GHS-POP density averaged onto the MODIS grid, times its pixel area (DEC-176)."""
    pop = ee.Image(CFG["population"]).select(CFG["population_band"]).unmask(0)
    dens = pop.divide(ee.Image.pixelArea())
    return dens.reduceResolution(ee.Reducer.mean(), maxPixels=CFG["reduce_max_pixels"]).reproject(proj).multiply(ee.Image.pixelArea())


def month_image(ee, year: int, month: int, region, w):
    """The 11 sum bands for one month (see the module docstring)."""
    start = ee.Date.fromYMD(year, month, 1)
    end = start.advance(1, "month")
    filt = CFG["filters"]

    def prep(img):
        aod = img.select(CFG["band"]).multiply(CFG["scale"])
        qa = img.select(CFG["qa_band"])
        return ee.Image.cat([aod.updateMask(qa_mask(ee, qa, filt[k])).rename(k) for k in ("primary", "relaxed")]) \
            .copyProperties(img, ["system:time_start"])  # fmt: skip

    coll = collection(ee).filterDate(start, end).filterBounds(region).map(prep)
    days = coll.aggregate_array("system:time_start").map(lambda t: ee.Date(t).format("YYYY-MM-dd")).distinct()

    def daily(s):
        d0 = ee.Date.parse("YYYY-MM-dd", s)
        return coll.filterDate(d0, d0.advance(1, "day")).mean()  # mean over the day's valid overpasses

    dic = ee.ImageCollection.fromImages(days.map(daily))
    mean, cnt = dic.mean(), dic.count()
    out = {}
    for k, pre in (("primary", "p"), ("relaxed", "r")):
        n = cnt.select(k).unmask(0)
        v = n.gt(0)
        out[pre] = (v, mean.select(k).unmask(0).multiply(v), n)
    (vp, ap, dp), (vr, ar, dr) = out["p"], out["r"]
    return ee.Image.cat([
        w.rename("w"), ee.Image(1).rename("px"),
        w.multiply(vp).rename("pw_v"), w.multiply(ap).rename("pw_a"), w.multiply(dp).rename("pw_d"),
        vp.rename("ar_v"), ap.rename("ar_a"), dp.rename("ar_d"),
        w.multiply(vr).rename("rw_v"), w.multiply(ar).rename("rw_a"), w.multiply(dr).rename("rw_d"),
    ])  # fmt: skip


def month_table(ee, year: int, month: int, units, proj, w):
    img = month_image(ee, year, month, units.geometry(), w)
    red = img.reduceRegions(collection=units, reducer=ee.Reducer.sum(), crs=proj, tileScale=CFG["tile_scale"])
    return red.map(lambda f: ee.Feature(None, f.toDictionary(["unit_id", *SUMS])).set({"year": year, "month": month}))


def table(ee, year: int, months: list[int]):
    units, proj = ee_units(ee), projection(ee)
    w = weights(ee, proj)
    return ee.FeatureCollection([month_table(ee, year, m, units, proj, w) for m in months]).flatten()


def start_export(ee, fc, name: str) -> dict:
    """Export.table.toDrive into one Drive folder (DEC-183: the project has no asset root)."""
    task = ee.batch.Export.table.toDrive(collection=fc, description=name, folder=CFG["drive_folder"], fileNamePrefix=name,
                                         fileFormat="CSV", selectors=COLUMNS)  # fmt: skip
    task.start()
    return {"name": name, "drive_folder": CFG["drive_folder"], "task_id": task.id,
            "submitted_utc": datetime.now(UTC).isoformat(timespec="seconds")}  # fmt: skip


def drive():
    """Drive API client with the Earth Engine credentials (their scopes include Drive; DEC-183)."""
    import ee
    from googleapiclient.discovery import build

    return build("drive", "v3", credentials=ee.data.get_persistent_credentials(), cache_discovery=False)


def drive_file(name: str) -> dict:
    """The exported CSV in the export folder: id, md5Checksum, size. Refuses ambiguous duplicates."""
    d = drive()
    q = f"name = '{name}.csv' and trashed = false and mimeType != 'application/vnd.google-apps.folder'"
    fs = d.files().list(q=q, fields="files(id,name,md5Checksum,size,createdTime,parents)").execute()["files"]
    folders = d.files().list(q=f"name = '{CFG['drive_folder']}' and mimeType = 'application/vnd.google-apps.folder' and trashed = false",
                             fields="files(id)").execute()["files"]  # fmt: skip
    fids = {f["id"] for f in folders}
    fs = [f for f in fs if fids & set(f.get("parents", []))]
    if len({f["md5Checksum"] for f in fs}) != 1:
        raise SystemExit(f"{name}.csv: {len(fs)} files in Drive folder {CFG['drive_folder']} with different contents; decide by hand")
    return sorted(fs, key=lambda f: f["createdTime"])[-1]


def drive_fetch(file_id: str):
    def fetch(_url: str, tmp: Path) -> None:
        from googleapiclient.http import MediaIoBaseDownload

        with open(tmp, "wb") as fh:
            dl = MediaIoBaseDownload(fh, drive().files().get_media(fileId=file_id))
            done = False
            while not done:
                _, done = dl.next_chunk()

    return fetch


def task_status(ee, task_id: str) -> dict:
    return ee.data.getTaskStatus(task_id)[0]


def eecu_seconds(st: dict) -> float | None:
    for k in ("batch_eecu_usage_seconds", "batchEecuUsageSeconds"):
        if k in st:
            return float(st[k])
    return None


# ---------------------------------------------------------------- commands


def cmd_check() -> None:
    """DEC-174: verify the collection on the day before exporting anything."""
    ee = init()
    y, m = CFG["pilot_month"]
    start = ee.Date.fromYMD(y, m, 1)
    region = ee_units(ee).geometry()
    c = collection(ee).filterDate(start, start.advance(1, "day")).filterBounds(region)
    first = c.first()
    info = {
        "collection": CFG["collection"],
        "images_on_day": c.size().getInfo(),
        "image_ids": c.aggregate_array("system:index").getInfo(),
        "times_utc": [datetime.fromtimestamp(t / 1000, UTC).isoformat() for t in c.aggregate_array("system:time_start").getInfo()],
        "bands": first.bandNames().getInfo(),
        "band_types": {b: first.select(b).getInfo()["bands"][0]["data_type"] for b in (CFG["band"], CFG["qa_band"])},
        "properties": first.propertyNames().getInfo(),
        "projection": projection(ee).getInfo(),
        "nominal_scale_m": projection(ee).nominalScale().getInfo(),
        "population_projection": ee.Image(CFG["population"]).select(CFG["population_band"]).projection().getInfo(),
        "population_bands": ee.Image(CFG["population"]).bandNames().getInfo(),
    }
    STATE.mkdir(parents=True, exist_ok=True)
    (STATE / "check.json").write_text(json.dumps(info, indent=2), encoding="utf-8")
    print(json.dumps(info, indent=2))


def _wait(ee, task_id: str, every: int = 30) -> dict:
    while True:
        st = task_status(ee, task_id)
        if st["state"] in ("COMPLETED", "FAILED", "CANCELLED"):
            return st
        print(f"  {st['state']} ({datetime.now().strftime('%H:%M:%S')})", flush=True)
        time.sleep(every)


def cmd_pilot() -> None:
    """DEC-178: one month, timed; the EECU use scaled to 180 months against the budget."""
    ee = init()
    y, m = CFG["pilot_month"]
    name = f"maiac_pilot_{y}_{m:02d}"
    rec = start_export(ee, table(ee, y, [m]), name)
    t0 = time.time()
    st = _wait(ee, rec["task_id"])
    if st["state"] != "COMPLETED":
        raise SystemExit(f"pilot {st['state']}: {st.get('error_message')}")
    eecu = eecu_seconds(st)
    months = 12 * (CFG["years"][1] - CFG["years"][0] + 1)
    proj_h = None if eecu is None else eecu * months / 3600
    PILOT.mkdir(parents=True, exist_ok=True)
    out = PILOT / f"{name}.csv"
    f = drive_file(name)
    drive_fetch(f["id"])("", out)
    res = {**rec, "status": st, "wall_seconds": round(time.time() - t0), "eecu_seconds": eecu, "months_total": months,
           "projected_eecu_hours": proj_h, "budget_hours": CFG["eecu_budget_hours"],
           "within_budget": proj_h is not None and proj_h <= CFG["eecu_budget_hours"], "csv_sha256": sha256_file(out)}  # fmt: skip
    (PILOT / "pilot.json").write_text(json.dumps(res, indent=2), encoding="utf-8")
    print(json.dumps({k: res[k] for k in ("wall_seconds", "eecu_seconds", "projected_eecu_hours", "within_budget")}, indent=2))
    if not res["within_budget"]:
        raise SystemExit("projected compute is over budget or unknown: do not submit; tell Reenu (DEC-178)")


def _tasks() -> dict:
    f = STATE / "tasks.json"
    return json.loads(f.read_text(encoding="utf-8")) if f.exists() else {}


def cmd_submit() -> None:
    pilot = json.loads((PILOT / "pilot.json").read_text(encoding="utf-8"))
    if not pilot.get("within_budget"):
        raise SystemExit("the pilot did not pass the compute budget (DEC-178)")
    commit = script_commit()
    ee = init()
    proj = projection(ee).getInfo()
    req = request_params(proj)
    tasks = _tasks()
    for y in range(CFG["years"][0], CFG["years"][1] + 1):
        name = f"maiac_unit_month_{y}"
        prev = tasks.get(name)
        if prev and task_status(ee, prev["task_id"])["state"] in ("READY", "RUNNING", "COMPLETED"):
            continue
        rec = start_export(ee, table(ee, y, list(range(1, 13))), name)
        tasks[name] = {**rec, "year": y, "commit": commit, "script_sha256": sha256_file(SCRIPT),
                       "request_sha256": sha(req), "request": req}  # fmt: skip
        STATE.mkdir(parents=True, exist_ok=True)
        (STATE / "tasks.json").write_text(json.dumps(tasks, indent=2), encoding="utf-8")
        print("submitted", name, rec["task_id"], flush=True)


def cmd_status() -> None:
    ee = init()
    total = 0.0
    for name, t in sorted(_tasks().items()):
        st = task_status(ee, t["task_id"])
        e = eecu_seconds(st) or 0.0
        total += e
        print(f"{name}: {st['state']}  eecu {e / 3600:.2f} h  {st.get('error_message', '')}")
    print(f"total EECU so far: {total / 3600:.2f} h")


def cmd_download() -> None:
    """Finished tables -> data/raw/maiac_gee/, unchanged, with the manifest row of DEC-178."""
    ee = init()
    dest = raw_dir("maiac_gee")
    dest.mkdir(parents=True, exist_ok=True)
    tasks, errors = _tasks(), []
    years = range(CFG["years"][0], CFG["years"][1] + 1)
    for y in years:
        name = f"maiac_unit_month_{y}"
        t = tasks.get(name)
        if not t:
            errors.append(f"{name}: never submitted")
            continue
        st = task_status(ee, t["task_id"])
        if st["state"] != "COMPLETED":
            errors.append(f"{name}: {st['state']}")
            continue
        f = drive_file(name)
        remote = (f"ee-task:{t['task_id']} | drive:{f['id']} md5 {f['md5Checksum']} | commit {t['commit']} | "
                  f"script sha256 {t['script_sha256'][:16]} | request sha256 {t['request_sha256'][:16]} | eecu_s {eecu_seconds(st)}")  # fmt: skip
        notes = json.dumps({k: v for k, v in t["request"].items() if k != "projection"}, sort_keys=True)
        download(dest, f"{name}.csv", f"gdrive:{CFG['drive_folder']}/{name}.csv", remote_id=remote, notes=notes,
                 fetch=drive_fetch(f["id"]), expected_md5=f["md5Checksum"])  # fmt: skip
    proj = next(iter(tasks.values()))["request"]["projection"] if tasks else None
    (STATE / "projection.json").write_text(json.dumps(proj, indent=2), encoding="utf-8")
    finish(dest, "maiac_gee", errors)


def main(argv: list[str]) -> None:
    cmds = {"check": cmd_check, "pilot": cmd_pilot, "submit": cmd_submit, "status": cmd_status, "download": cmd_download}
    if not argv or argv[0] not in cmds:
        raise SystemExit(__doc__)
    cmds[argv[0]]()


if __name__ == "__main__":
    main(sys.argv[1:])

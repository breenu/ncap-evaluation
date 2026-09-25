"""Phase 2 step 0: feasibility probe, run before any bulk download (PLAN.md section 4).

Checks that each source contains what the proposal expects and measures exact
download sizes. Nothing here writes to data/raw/; small test files go to
data/interim/probe/ and each check writes a JSON summary there, which
`report` turns into docs/data-probe.md.

    python -m src.acquire.probe acag      # no key
    python -m src.acquire.probe firms     # no key
    python -m src.acquire.probe openaq    # OPENAQ_API_KEY in .env
    python -m src.acquire.probe cpcb_mirror  # no key; reads Parquet footers only
    python -m src.acquire.probe cds       # ~/.cdsapirc
    python -m src.acquire.probe report
"""

import argparse
import json
import os
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path

from src.acquire.s3 import list_objects, object_url
from src.common.manifest import _session, http_fetch
from src.common.paths import DOCS, INTERIM, ROOT, params

OUT = INTERIM / "probe"

# Generous India bounding box (includes Andaman & Nicobar and the northern claim line).
INDIA_BBOX = {"lat": (6.0, 37.5), "lon": (68.0, 97.5)}

# Extreme points and a spread of cities: every one must fall inside the grid and have a value.
INDIA_POINTS = {
    "Indira Point (south)": (6.75, 93.84),
    "Guhar Moti (west)": (23.71, 68.03),
    "Kibithu (east)": (28.02, 97.02),
    "Siachen (north)": (35.50, 77.00),
    "Delhi": (28.61, 77.21),
    "Kolkata": (22.57, 88.36),
    "Chennai": (13.08, 80.27),
    "Mumbai": (19.08, 72.88),
    "Guwahati": (26.14, 91.74),
    "Srinagar": (34.08, 74.80),
    "Port Blair": (11.62, 92.73),
    "Thiruvananthapuram": (8.52, 76.94),
}

DELHI = (28.61, 77.21)


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def _save(name: str, obj: dict) -> Path:
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / f"{name}.json"
    path.write_text(json.dumps(obj, indent=2, default=str), encoding="utf-8")
    return path


def _in_years(key: str, years: tuple[int, int]) -> bool:
    # ACAG names end in .YYYYMM-YYYYMM.nc
    stamp = key.rsplit(".", 2)[-2].split("-")[0]
    return years[0] <= int(stamp[:4]) <= years[1]


# ---------------------------------------------------------------- ACAG

ACAG_BUCKET = "satpmdata"

# (label, S3 folder, role). Years are filtered to params windows.satellite_download_years.
ACAG_PRODUCTS = [
    ("V5GL06 annual 0.01 Asia", "V5GL06/GWRPM25/Annual/Asia/", "primary"),
    ("V5GL06 annual uncertainty 0.01 Asia", "V5GL06/GWRPM25Uncertainty/Annual/Asia/", "primary"),
    ("V5GL06 monthly 0.05 Asia", "V5GL06/GWRPM25c0p05/Monthly/Asia/", "seasonal"),
    ("V6GL03 annual 0.01 AS", "V6GL03/CNNPM25/Annual/AS/", "comparison"),
    ("V6GL03 monthly 0.10 AS", "V6GL03/CNNPM25c0p10/Monthly/AS/", "comparison (seasonal)"),
    ("V6GL0204 annual 0.01 AS", "V6GL0204/CNNPM25/Annual/AS/", "vintage"),
]

# One annual 0.01 file per version, opened to check the grid extent.
ACAG_EXTENT_FILES = [
    "V5GL06/GWRPM25/Annual/Asia/V5GL06.HybridPM25.Asia.201901-201912.nc",
    "V6GL03/CNNPM25/Annual/AS/V6GL03.CNNPM25.AS.201901-201912.nc",
    "V6GL0204/CNNPM25/Annual/AS/V6GL02.04.CNNPM25.AS.201901-201912.nc",
]


def probe_acag() -> dict:
    import numpy as np
    import xarray as xr

    years = tuple(params()["windows"]["satellite_download_years"])
    products = []
    for label, prefix, role in ACAG_PRODUCTS:
        objs = [o for o in list_objects(ACAG_BUCKET, prefix) if o.key.endswith(".nc")]
        sel = [o for o in objs if _in_years(o.key, years)]
        products.append(
            {
                "label": label,
                "prefix": prefix,
                "role": role,
                "files_in_bucket": len(objs),
                "files_in_window": len(sel),
                "bytes_in_window": sum(o.size for o in sel),
                "first": sel[0].key.rsplit("/", 1)[-1] if sel else None,
                "last": sel[-1].key.rsplit("/", 1)[-1] if sel else None,
                "last_modified_max": max((o.last_modified for o in sel), default=None),
            }
        )

    extents = []
    for key in ACAG_EXTENT_FILES:
        dest = OUT / "acag" / key.rsplit("/", 1)[-1]
        if not dest.exists():
            dest.parent.mkdir(parents=True, exist_ok=True)
            tmp = dest.with_suffix(".part")
            http_fetch(object_url(ACAG_BUCKET, key), tmp)
            tmp.replace(dest)
        with xr.open_dataset(dest) as ds:
            lat = next(n for n in ("lat", "latitude") if n in ds.coords or n in ds.variables)
            lon = next(n for n in ("lon", "longitude") if n in ds.coords or n in ds.variables)
            var = next(v for v in ds.data_vars if ds[v].ndim == 2)
            la, lo = ds[lat].values, ds[lon].values
            points = {}
            for name, (py, px) in INDIA_POINTS.items():
                inside = la.min() <= py <= la.max() and lo.min() <= px <= lo.max()
                val = (
                    float(ds[var].sel({lat: py, lon: px}, method="nearest").values)
                    if inside
                    else None
                )
                points[name] = {"inside_grid": bool(inside), "value": val}
            box = ds[var].sel(
                {
                    lat: slice(*sorted(INDIA_BBOX["lat"], reverse=la[0] > la[-1])),
                    lon: slice(*INDIA_BBOX["lon"]),
                }
            )
            extents.append(
                {
                    "file": key,
                    "bytes": dest.stat().st_size,
                    "variable": var,
                    "units": ds[var].attrs.get("units"),
                    "lat_range": [float(la.min()), float(la.max())],
                    "lon_range": [float(lo.min()), float(lo.max())],
                    "resolution_deg": [
                        float(abs(np.diff(la[:2])[0])),
                        float(abs(np.diff(lo[:2])[0])),
                    ],
                    "covers_india_bbox": bool(
                        la.min() <= INDIA_BBOX["lat"][0]
                        and la.max() >= INDIA_BBOX["lat"][1]
                        and lo.min() <= INDIA_BBOX["lon"][0]
                        and lo.max() >= INDIA_BBOX["lon"][1]
                    ),
                    "india_bbox_valid_share": float(np.isfinite(box.values).mean()),
                    "points": points,
                    "global_attrs": {k: str(v)[:200] for k, v in ds.attrs.items()},
                }
            )
    result = {
        "checked_utc": _now(),
        "window_years": years,
        "products": products,
        "extents": extents,
    }
    _save("acag", result)
    return result


# ---------------------------------------------------------------- FIRMS

FIRMS_BASE = "https://firms.modaps.eosdis.nasa.gov/data/country"
FIRMS_PRODUCTS = {"modis": 2000, "viirs-snpp": 2012}  # DEC-010: MODIS covariate, VIIRS check


def probe_firms() -> dict:
    s = _session()
    last_year = int(params()["windows"]["ground_end"][:4])
    files = []
    for product, first in FIRMS_PRODUCTS.items():
        for year in range(first, last_year + 1):
            url = f"{FIRMS_BASE}/{product}/{year}/{product}_{year}_India.csv"
            r = s.head(url, timeout=(30, 60), allow_redirects=True)
            files.append(
                {
                    "product": product,
                    "year": year,
                    "url": url,
                    "status": r.status_code,
                    "bytes": int(r.headers.get("Content-Length", 0)) if r.ok else None,
                    "last_modified": r.headers.get("Last-Modified"),
                }
            )
    # First bytes of one file: column names and the 'type'/'version' fields.
    heads = {}
    for product in FIRMS_PRODUCTS:
        url = f"{FIRMS_BASE}/{product}/2019/{product}_2019_India.csv"
        r = s.get(url, headers={"Range": "bytes=0-1023"}, timeout=(30, 60))
        heads[product] = r.text.splitlines()[:3]
    # Processing version: first and last row of each yearly file (range reads, a few KB).
    for f in files:
        if f["status"] != 200:
            continue
        head = s.get(
            f["url"], headers={"Range": "bytes=0-1023"}, timeout=(30, 60)
        ).text.splitlines()
        tail = s.get(f["url"], headers={"Range": "bytes=-1024"}, timeout=(30, 60)).text.splitlines()
        cols = head[0].split(",")
        d, v = cols.index("acq_date"), cols.index("version")
        first, last = head[1].split(","), tail[-1].split(",")
        f["first_row"] = {"acq_date": first[d], "version": first[v]}
        f["last_row"] = {"acq_date": last[d], "version": last[v]}
    result = {"checked_utc": _now(), "files": files, "sample_head": heads}
    _save("firms", result)
    return result


# ---------------------------------------------------------------- OpenAQ

OPENAQ_API = "https://api.openaq.org/v3"
OPENAQ_BUCKET = "openaq-data-archive"
PM = {"pm25", "pm10"}


class _OpenAQ:
    """Minimal v3 client that respects the rate-limit headers (60/min, 2,000/h)."""

    def __init__(self, key: str):
        self.s = _session()
        self.s.headers["X-API-Key"] = key
        self.calls = 0

    def get(self, path: str, **params) -> dict:
        for _ in range(10):
            r = self.s.get(f"{OPENAQ_API}{path}", params=params, timeout=(30, 120))
            self.calls += 1
            if r.status_code == 429:
                time.sleep(int(r.headers.get("x-ratelimit-reset", 60)) + 1)
                continue
            r.raise_for_status()
            if int(r.headers.get("x-ratelimit-remaining", 10)) <= 1:
                time.sleep(int(r.headers.get("x-ratelimit-reset", 60)) + 1)
            return r.json()
        raise RuntimeError(f"OpenAQ: still rate-limited after 10 tries: {path}")

    def paged(self, path: str, **params) -> list[dict]:
        out, page = [], 1
        while True:
            res = self.get(path, limit=1000, page=page, **params)["results"]
            out += res
            if len(res) < 1000:
                return out
            page += 1


def _openaq_key() -> str:
    from dotenv import dotenv_values

    key = dotenv_values(ROOT / ".env").get("OPENAQ_API_KEY") or os.environ.get("OPENAQ_API_KEY", "")
    if not key or key.startswith("PASTE-"):
        raise SystemExit("OPENAQ_API_KEY is not set in .env")
    return key


def _s3_location_files(location_id: int) -> list[dict]:
    out = []
    for o in list_objects(OPENAQ_BUCKET, f"records/csv.gz/locationid={location_id}/"):
        # .../locationid=X/year=YYYY/month=MM/location-X-YYYYMMDD.csv.gz
        day = o.key.rsplit("-", 1)[-1].split(".")[0]
        out.append({"day": day, "bytes": o.size})
    return out


def probe_openaq() -> dict:
    w = params()["windows"]
    start, end = w["ground_start"], w["ground_end"]
    api = _OpenAQ(_openaq_key())

    # 1. every Indian location, with sensors and first/last dates
    locations = api.paged("/locations", iso="IN")
    _save("openaq_locations_IN", {"retrieved_utc": _now(), "results": locations})
    print(f"  {len(locations)} Indian locations", flush=True)

    sensors = []  # PM sensors on reference monitors
    for loc in locations:
        for s in loc.get("sensors", []):
            p = s["parameter"]["name"]
            if p in PM | {"no2"}:
                sensors.append(
                    {
                        "location_id": loc["id"],
                        "sensor_id": s["id"],
                        "parameter": p,
                        "is_monitor": loc.get("isMonitor"),
                        "is_mobile": loc.get("isMobile"),
                        "provider": (loc.get("provider") or {}).get("name"),
                        "owner": (loc.get("owner") or {}).get("name"),
                        "lat": (loc.get("coordinates") or {}).get("latitude"),
                        "lon": (loc.get("coordinates") or {}).get("longitude"),
                        "first": (loc.get("datetimeFirst") or {}).get("utc"),
                        "last": (loc.get("datetimeLast") or {}).get("utc"),
                    }
                )

    # 2. monthly coverage per PM sensor on reference monitors, from the daily rollup
    # (/days/monthly: observed = days with data). /hours/monthly times out (HTTP 408) on
    # decade-long sensors, so it is not used.
    # Months are labelled by the *local* (IST) start: the UTC start of February is 31 Jan 18:30Z.
    # Each sensor's rows are cached so an interrupted run resumes.
    pm_ref = [s for s in sensors if s["parameter"] in PM and s["is_monitor"] and not s["is_mobile"]]
    cache = OUT / "openaq_sensor_months"
    cache.mkdir(parents=True, exist_ok=True)
    months = []
    for i, s in enumerate(pm_ref, 1):
        cached = cache / f"{s['sensor_id']}.json"
        if cached.exists():
            rows = json.loads(cached.read_text(encoding="utf-8"))
        else:
            rows = api.paged(
                f"/sensors/{s['sensor_id']}/days/monthly",
                datetime_from=start,
                datetime_to=end,
            )
            cached.write_text(json.dumps(rows), encoding="utf-8")
        for r in rows:
            cov = r.get("coverage") or {}
            months.append(
                {
                    "location_id": s["location_id"],
                    "sensor_id": s["sensor_id"],
                    "parameter": s["parameter"],
                    "month": r["period"]["datetimeFrom"]["local"][:7],
                    "observed_days": cov.get("observedCount"),
                    "expected_days": cov.get("expectedCount"),
                    "pct": cov.get("percentCoverage"),
                }
            )
        if i % 50 == 0:
            print(f"  coverage: {i}/{len(pm_ref)} sensors, {api.calls} API calls", flush=True)

    # 3. exact archive size for the locations we would download
    loc_ids = sorted({s["location_id"] for s in pm_ref})
    with ThreadPoolExecutor(16) as pool:
        listings = dict(zip(loc_ids, pool.map(_s3_location_files, loc_ids), strict=True))
    lo, hi = start.replace("-", ""), end.replace("-", "")
    s3_bytes, s3_files, s3_months = 0, 0, defaultdict(set)
    s3_bytes_all, s3_files_all = 0, 0
    for lid, files in listings.items():
        for f in files:
            s3_bytes_all += f["bytes"]
            s3_files_all += 1
            if lo <= f["day"] <= hi:
                s3_bytes += f["bytes"]
                s3_files += 1
                s3_months[lid].add(f["day"][:6])

    result = {
        "retrieved_utc": _now(),
        "window": [start, end],
        "api_calls": api.calls,
        "n_locations_IN": len(locations),
        "sensors": sensors,
        "months": months,
        "s3": {
            "locations": len(loc_ids),
            "files_in_window": s3_files,
            "bytes_in_window": s3_bytes,
            "files_all_years": s3_files_all,
            "bytes_all_years": s3_bytes_all,
            "location_months": {str(k): sorted(v) for k, v in s3_months.items()},
        },
    }
    _save("openaq", result)
    return result


# ---------------------------------------------------------------- CPCB data repository mirror

# CPCB's own data repository endpoints (airquality.cpcb.gov.in/dataRepository/...) returned
# HTTP 404 on 2026-09-26. This third-party mirror (ODbL) holds yearly Parquet files scraped from
# them in Jan 2026. Only small, run-length-encoded columns and footers are read here (KBs).
CPCB_MIRROR = (
    "https://github.com/Vonter/india-cpcb-aqi/releases/download/{y}/cpcb-air-quality-{y}.parquet"
)
SLOTS_PER_DAY = 96  # 15-minute data


def probe_cpcb_mirror() -> dict:
    import pyarrow.compute as pc
    import pyarrow.parquet as pq

    from src.acquire.http_range import HTTPRangeFile

    w = params()["windows"]
    first, last = int(w["ground_start"][:4]), int(w["ground_end"][:4])
    years, stations = [], {}
    for y in range(first, last + 1):
        url = CPCB_MIRROR.format(y=y)
        try:
            f = HTTPRangeFile(url)
        except Exception as e:  # noqa: BLE001 - recorded, not hidden
            years.append({"year": y, "url": url, "error": str(e)[:200]})
            continue
        pf = pq.ParquetFile(f)
        md = pf.metadata
        nulls, tmin, tmax = defaultdict(int), None, None
        for i in range(md.num_row_groups):
            rg = md.row_group(i)
            for j in range(rg.num_columns):
                c = rg.column(j)
                if c.path_in_schema in ("PM2.5 (µg/m³)", "PM10 (µg/m³)") and c.statistics:
                    nulls[c.path_in_schema] += c.statistics.null_count
                if c.path_in_schema == "Timestamp" and c.statistics and c.statistics.has_min_max:
                    tmin = min(tmin, c.statistics.min) if tmin else c.statistics.min
                    tmax = max(tmax, c.statistics.max) if tmax else c.statistics.max
        t = pf.read(columns=["Station ID", "State", "City"])
        counts = pc.value_counts(t["Station ID"]).to_pylist()
        days = 366 if y % 4 == 0 else 365
        for r in counts:
            stations.setdefault(r["values"], {})[y] = round(r["counts"] / (days * SLOTS_PER_DAY), 3)
        meta = t.group_by(["Station ID", "State", "City"]).aggregate([]).to_pylist()
        for m in meta:
            stations[m["Station ID"]]["_city"] = f"{m['City']}, {m['State']}"
        years.append(
            {
                "year": y,
                "url": url,
                "bytes": f.size,
                "rows": md.num_rows,
                "stations": len(counts),
                "stations_ge_75pct_slots": sum(
                    r["counts"] >= 0.75 * days * SLOTS_PER_DAY for r in counts
                ),
                "pm25_null_share": round(nulls["PM2.5 (µg/m³)"] / md.num_rows, 3),
                "pm10_null_share": round(nulls["PM10 (µg/m³)"] / md.num_rows, 3),
                "timestamp_min": str(tmin),
                "timestamp_max": str(tmax),
                "bytes_read": f.bytes_fetched,
                "columns": md.schema.names,
            }
        )
        print(
            f"  mirror {y}: {len(counts)} stations, {f.bytes_fetched / 1e6:.1f} MB read", flush=True
        )
    result = {"checked_utc": _now(), "years": years, "stations": stations}
    _save("cpcb_mirror", result)
    return result


# ---------------------------------------------------------------- CDS / ERA5

ERA5_TS = "reanalysis-era5-single-levels-timeseries"
ERA5_VARS = [
    "2m_temperature",
    "2m_dewpoint_temperature",
    "10m_u_component_of_wind",
    "10m_v_component_of_wind",
    "boundary_layer_height",
    "total_precipitation",
    "surface_solar_radiation_downwards",
]


def probe_cds() -> dict:
    import cdsapi

    w = params()["windows"]
    dest = OUT / "era5_delhi_timeseries.zip"
    request = {
        "variable": ERA5_VARS,
        "location": {"latitude": DELHI[0], "longitude": DELHI[1]},
        "date": [f"{w['ground_start']}/{w['ground_end']}"],
        "data_format": "csv",
    }
    t0 = time.time()
    if not dest.exists():
        cdsapi.Client().retrieve(ERA5_TS, request, str(dest))
    result = {
        "checked_utc": _now(),
        "dataset": ERA5_TS,
        "request": request,
        "seconds": round(time.time() - t0, 1),
        "bytes": dest.stat().st_size,
        "file": str(dest.relative_to(ROOT)),
        "content": era5_csv_summary(dest),
    }
    log = OUT / "cds.log"
    if log.exists():
        result["content"]["CDS job time (accepted to successful)"] = _cds_job_seconds(
            log.read_text("utf-8")
        )
    _save("cds", result)
    return result


def era5_csv_summary(zip_path: Path) -> dict:
    """What the time-series CSV actually contains: columns, grid point, span, gaps."""
    import zipfile

    import pandas as pd

    with zipfile.ZipFile(zip_path) as z:
        (name,) = z.namelist()
        csv_bytes = z.getinfo(name).file_size
        df = pd.read_csv(z.open(name))
    t = pd.to_datetime(df["valid_time"])
    expected = pd.date_range(t.min(), t.max(), freq="h")
    return {
        "columns": ", ".join(df.columns),
        "grid point returned": f"{df['latitude'].iloc[0]} N, {df['longitude'].iloc[0]} E",
        "hourly rows": f"{len(df):,} ({t.min()} to {t.max()})",
        "missing hours": int(len(expected.difference(t))),
        "NaN values": int(df.isna().sum().sum()),
        "uncompressed CSV size": f"{csv_bytes / 1e6:.1f} MB",
        "negative ssrd values (min)": (
            f"{int((df['ssrd'] < 0).sum())} ({df['ssrd'].min():.2f} J/m2)"
        ),
    }


def _cds_job_seconds(log: str) -> str:
    """Seconds between 'accepted' and 'successful' in the cdsapi log (excludes local retries)."""
    import re

    stamps = {
        m.group(2): datetime.strptime(m.group(1), "%Y-%m-%d %H:%M:%S,%f")
        for m in re.finditer(r"^(\S+ \S+) INFO status has been updated to (\w+)", log, re.M)
    }
    if {"accepted", "successful"} <= stamps.keys():
        return f"{(stamps['successful'] - stamps['accepted']).total_seconds():.0f} s"
    return "not found in log"


# ---------------------------------------------------------------- CLI

CHECKS = {
    "acag": probe_acag,
    "firms": probe_firms,
    "openaq": probe_openaq,
    "cpcb_mirror": probe_cpcb_mirror,
    "cds": probe_cds,
}


def main() -> None:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("check", choices=[*CHECKS, "report"])
    args = ap.parse_args()
    if args.check == "report":
        from src.acquire.probe_report import write_report

        print(write_report(OUT, DOCS / "data-probe.md"))
        return
    CHECKS[args.check]()
    print(f"saved {OUT / (args.check + '.json')}")


if __name__ == "__main__":
    main()

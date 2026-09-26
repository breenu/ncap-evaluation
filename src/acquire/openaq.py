"""OpenAQ: Indian location metadata (v3 API) and daily measurement files (S3 archive).

Role (DEC-037): the ground source for Jan-Mar 2026, and an independent copy of CPCB data
for cross-checking the mirror wherever both have data. Stations are reference monitors
(isMonitor, not mobile) with a PM2.5 or PM10 sensor.

Raw layout, data/raw/openaq/:
  locations_IN_<date>.json                 API snapshot of every Indian location
  locationid=<id>/year=<YYYY>.zip          the S3 daily .csv.gz files of that location-year,
                                           stored uncompressed and byte-identical, plus an
                                           _index.csv (key, etag, bytes, sha256 per member)

Bundling ~430k small files into one zip per location-year keeps Windows file counts sane
and the committed manifest small (one row per zip). Member timestamps in the zip are fixed
from the file's date, so rebuilding a zip from the same S3 objects gives identical bytes.

    python -m src.acquire.openaq
"""

import argparse
import csv
import hashlib
import io
import json
import threading
import zipfile
from datetime import UTC, datetime
from pathlib import Path

from dotenv import dotenv_values

from src.acquire.common import finish, run_parallel
from src.acquire.s3 import S3Object, list_objects, object_url
from src.common.manifest import RawDataError, _session, download, read_manifest, record, s3_md5
from src.common.paths import ROOT, params, raw_dir

SOURCE = "openaq"
API = "https://api.openaq.org/v3"
BUCKET = "openaq-data-archive"
PM = {"pm25", "pm10"}

_local = threading.local()


def _s():
    if not hasattr(_local, "s"):
        _local.s = _session()
    return _local.s


# ------------------------------------------------------------------ metadata


def _api_key() -> str:
    key = dotenv_values(ROOT / ".env").get("OPENAQ_API_KEY", "")
    if not key or key.startswith("PASTE-"):
        raise SystemExit("OPENAQ_API_KEY is not set in .env")
    return key


def fetch_locations() -> list[dict]:
    s = _session()
    s.headers["X-API-Key"] = _api_key()
    out, page = [], 1
    while True:
        r = s.get(
            f"{API}/locations", params={"iso": "IN", "limit": 1000, "page": page}, timeout=(30, 120)
        )
        r.raise_for_status()
        res = r.json()["results"]
        out += res
        if len(res) < 1000:
            return out
        page += 1


def locations_snapshot(dest: Path) -> Path:
    """The newest saved snapshot, or a new one if none exists. Snapshots are never rewritten."""
    existing = sorted(dest.glob("locations_IN_*.json"))
    if existing:
        return existing[-1]
    name = f"locations_IN_{datetime.now(UTC).date().isoformat()}.json"
    path = dest / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(fetch_locations(), indent=1), encoding="utf-8")
    record(dest, name, f"{API}/locations?iso=IN", notes="v3 API snapshot (key not recorded)")
    return path


def reference_pm_locations(locations: list[dict]) -> list[int]:
    return sorted(
        loc["id"]
        for loc in locations
        if loc.get("isMonitor")
        and not loc.get("isMobile")
        and any(s["parameter"]["name"] in PM for s in loc.get("sensors", []))
    )


# ------------------------------------------------------------------ bundles


def _day(key: str) -> str:
    # records/csv.gz/locationid=X/year=YYYY/month=MM/location-X-YYYYMMDD.csv.gz
    return key.rsplit("-", 1)[-1].split(".")[0]


def listing_id(objs: list[S3Object]) -> str:
    """Upstream version id of a bundle: hash of its members' keys and ETags."""
    h = hashlib.sha256()
    for o in sorted(objs, key=lambda o: o.key):
        h.update(f"{o.key}:{o.etag}\n".encode())
    return "members-sha256:" + h.hexdigest()


def build_zip(objs: list[S3Object], dest: Path, get=None) -> None:
    """Write the objects into an uncompressed, deterministic zip at dest, verifying each
    member against its MD5 ETag (single-part uploads)."""
    get = get or (lambda url: _s().get(url, timeout=(30, 120)))
    rows = []
    with zipfile.ZipFile(dest, "w", compression=zipfile.ZIP_STORED) as z:
        for o in sorted(objs, key=lambda o: o.key):
            r = get(object_url(BUCKET, o.key))
            r.raise_for_status()
            data = r.content
            md5 = s3_md5(o.etag)
            if md5 and hashlib.md5(data, usedforsecurity=False).hexdigest() != md5:
                raise RawDataError(f"{o.key}: bytes do not match the S3 ETag")
            if len(data) != o.size:
                raise RawDataError(f"{o.key}: got {len(data)} bytes, listing says {o.size}")
            d = _day(o.key)
            info = zipfile.ZipInfo(
                o.key.rsplit("/", 1)[-1], date_time=(int(d[:4]), int(d[4:6]), int(d[6:8]), 0, 0, 0)
            )
            z.writestr(info, data)
            rows.append([o.key, o.etag, o.size, hashlib.sha256(data).hexdigest()])
        buf = io.StringIO()
        csv.writer(buf, lineterminator="\n").writerows([["key", "etag", "bytes", "sha256"], *rows])
        z.writestr(zipfile.ZipInfo("_index.csv", date_time=(2026, 1, 1, 0, 0, 0)), buf.getvalue())


def bundle_task(dest: Path, location_id: int, year: int, lo: str, hi: str):
    def run():
        name = f"locationid={location_id}/year={year}.zip"
        entry = read_manifest(dest).get(name)
        if entry and (dest / name).exists():
            return  # recorded and present: skip without listing S3
        prefix = f"records/csv.gz/locationid={location_id}/year={year}/"
        objs = [o for o in list_objects(BUCKET, prefix) if lo <= _day(o.key) <= hi]
        if not objs:
            return
        download(
            dest,
            name,
            object_url(BUCKET, prefix),
            remote_id=listing_id(objs),
            notes=f"{len(objs)} daily files {min(_day(o.key) for o in objs)}..{max(_day(o.key) for o in objs)}",
            fetch=lambda url, tmp: build_zip(objs, tmp),
        )

    return run


def main() -> None:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--workers", type=int, default=24)
    args = ap.parse_args()
    w = params()["windows"]
    lo, hi = w["ground_start"].replace("-", ""), w["ground_end"].replace("-", "")
    dest = raw_dir(SOURCE)
    snap = locations_snapshot(dest)
    ids = reference_pm_locations(json.loads(snap.read_text(encoding="utf-8")))
    print(f"{SOURCE}: {len(ids)} reference PM locations from {snap.name}")
    years = range(int(lo[:4]), int(hi[:4]) + 1)
    tasks = [bundle_task(dest, lid, y, lo, hi) for lid in ids for y in years]
    finish(dest, SOURCE, run_parallel(tasks, args.workers, SOURCE))


if __name__ == "__main__":
    main()

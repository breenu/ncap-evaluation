"""Ingest: raw ground data -> tidy Parquet in data/interim/, clocks corrected. Raw files are not touched.

mirror  CPCB mirror yearly Parquet (DEC-037) -> data/interim/mirror_15min/year=YYYY/*.parquet
        columns: sid, ts_utc (naive UTC), date_ist, pm25, pm10, no2
        - The mirror stores Indian times stamped as UTC (DEC-054): ts_utc = stored instant - 5.5 h,
          offset from config/params.yaml (mirror.stored_minus_utc_hours). DuckDB's session zone
          is pinned to UTC, so the result does not depend on the machine's time zone.
        - Rows are padded to every 15-minute slot, so rows with no PM2.5, PM10 or NO2 are dropped.
        - The shifted clock puts some rows in the "wrong" year file, and adjacent year files can
          hold the same station-slot. Duplicates are resolved (identical values: keep one;
          conflicting values: the slot is set to null for that pollutant) and counted.
        - Partitioned by the year of the Indian (IST) date, the unit every later stage aggregates to.

openaq  OpenAQ zips (DEC-041) -> data/interim/openaq_obs/year=YYYY/loc-<id>.parquet
        columns: location_id, sensors_id, ts_utc, parameter, value, units, lat, lon
        - `units` is kept as OpenAQ labels it; no rows are dropped for units. OpenAQ's 2025+ CPCB
          feed labels NO2 and CO "ppb", but its CO values are clearly mg/m3, so the labels are
          checked against the mirror (src/clean/crosscheck.py) before any NO2 use.
        - pm25, pm10, no2 only.
        - Timestamps carry explicit offsets; stored as naive UTC.

Summary counts go to data/interim/ingest/*.csv for the audit report.

    python -m src.clean.ingest [mirror|openaq|all]
"""

import gzip
import io
import shutil
import sys
import zipfile
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import duckdb
import pandas as pd

from src.common.paths import INTERIM, params, raw_dir

MIRROR_OUT = INTERIM / "mirror_15min"
OPENAQ_OUT = INTERIM / "openaq_obs"
SUMMARY = INTERIM / "ingest"

IST_OFFSET_MIN = 330  # UTC + 5:30
MIRROR_COLS = {"pm25": "PM2.5 (µg/m³)", "pm10": "PM10 (µg/m³)", "no2": "NO2 (µg/m³)"}
OPENAQ_PARAMS = ("pm25", "pm10", "no2")


# ------------------------------------------------------------------ mirror


def mirror_shift_minutes() -> int:
    """Minutes to subtract from a mirror's stored timestamp to get UTC (DEC-054)."""
    return int(round(params()["mirror"]["stored_minus_utc_hours"] * 60))


def mirror_select_sql(files: list[str], shift_min: int) -> str:
    """SQL selecting non-empty rows from mirror files on the corrected (UTC) clock."""
    cols = ", ".join(f'"{src}" as {dst}' for dst, src in MIRROR_COLS.items())
    any_value = " or ".join(f'"{src}" is not null' for src in MIRROR_COLS.values())
    flist = ", ".join(f"'{f}'" for f in files)
    # timezone('UTC', tstz) -> the stored instant as a naive UTC timestamp (independent of the
    # session zone); then remove the mirror's offset to get true UTC.
    return f"""
        select "Station ID" as sid,
               timezone('UTC', "Timestamp") - interval {shift_min} minute as ts_utc,
               {cols}
        from read_parquet([{flist}])
        where {any_value}"""


def dedupe_sql(src: str) -> str:
    """Collapse duplicate (sid, ts_utc) rows. Per pollutant: if all non-null copies agree, keep
    that value; if they conflict, set null (and count it). Also returns the copy count."""
    parts = []
    for p in MIRROR_COLS:
        parts.append(
            f"case when count(distinct {p}) <= 1 then max({p}) else null end as {p}, "
            f"(count(distinct {p}) > 1) as {p}_conflict"
        )
    return f"""
        select sid, ts_utc, {", ".join(parts)}, count(*) as copies
        from ({src}) group by sid, ts_utc"""


def ingest_mirror(
    mirror_dir: Path | None = None, out: Path = MIRROR_OUT, summary_dir: Path = SUMMARY
) -> pd.DataFrame:
    mirror_dir = mirror_dir or raw_dir("cpcb_mirror")
    files = sorted(p.as_posix() for p in mirror_dir.glob("cpcb-air-quality-*.parquet"))
    if not files:
        raise FileNotFoundError(f"no mirror files in {mirror_dir}")
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    con = duckdb.connect()
    con.execute("set TimeZone = 'UTC'")
    con.execute("set preserve_insertion_order = false")
    con.execute("set memory_limit = '8GB'")
    con.execute(f"set temp_directory = '{(out.parent / '_duckdb_tmp').as_posix()}'")
    tmp = out.parent / "_tmp_mirror.duckdb"
    con.execute(f"attach '{tmp.as_posix()}' as t")
    try:
        con.execute(
            f"create or replace table t.dedup as {dedupe_sql(mirror_select_sql(files, mirror_shift_minutes()))}"
        )
        cols = ", ".join(MIRROR_COLS)
        con.execute(
            f"""copy (select sid, ts_utc,
                        cast(ts_utc + interval {IST_OFFSET_MIN} minute as date) as date_ist,
                        year(ts_utc + interval {IST_OFFSET_MIN} minute) as year, {cols}
                      from t.dedup where coalesce({cols}) is not null
                      order by sid, ts_utc)
                to '{out.as_posix()}' (format parquet, partition_by (year), compression zstd)"""
        )
        summary = con.execute(
            f"""select year(ts_utc + interval {IST_OFFSET_MIN} minute) as year,
                       count(*) as slots, count(distinct sid) as stations,
                       sum((copies > 1)::int) as duplicated_slots,
                       {", ".join(f"count({p}) as {p}_values, sum({p}_conflict::int) as {p}_conflicts" for p in MIRROR_COLS)}
                from t.dedup group by 1 order by 1"""
        ).df()
    finally:
        con.close()
        tmp.unlink(missing_ok=True)
    summary_dir.mkdir(parents=True, exist_ok=True)
    summary.to_csv(summary_dir / "mirror_summary.csv", index=False)
    return summary


# ------------------------------------------------------------------ openaq


def read_openaq_zip(path: Path) -> tuple[pd.DataFrame, dict]:
    """All day files in one location-year zip -> one frame (pm25/pm10/no2, ug/m3), plus counts."""
    chunks, header = [], None
    with zipfile.ZipFile(path) as z:
        for name in sorted(z.namelist()):
            if not name.endswith(".csv.gz"):
                continue
            text = gzip.decompress(z.read(name)).decode("utf-8")
            first, _, body = text.partition("\n")
            header = header or first
            chunks.append(body if body.endswith("\n") or not body else body + "\n")
    counts = {"file": path.as_posix(), "rows": 0, "kept": 0}
    if header is None:
        return pd.DataFrame(), counts
    d = pd.read_csv(io.StringIO(header + "\n" + "".join(chunks)))
    counts["rows"] = len(d)
    d = d[d.parameter.isin(OPENAQ_PARAMS)]
    out = pd.DataFrame(
        {
            "location_id": d.location_id.astype("int64"),
            "sensors_id": d.sensors_id.astype("int64"),
            "ts_utc": pd.to_datetime(d.datetime, utc=True, format="ISO8601").dt.tz_localize(None),
            "parameter": d.parameter.astype(str),
            "value": d.value.astype(float),
            "units": d.units.astype(str),
            "lat": d.lat.astype(float),
            "lon": d.lon.astype(float),
        }
    )
    counts["kept"] = len(out)
    return out, counts


def _openaq_one(args: tuple[str, str]) -> dict:
    zpath, out_dir = args
    zpath = Path(zpath)
    d, counts = read_openaq_zip(zpath)
    if len(d):
        year = zpath.stem.split("=")[1]
        loc = zpath.parent.name.split("=")[1]
        dest = Path(out_dir) / f"year={year}"
        dest.mkdir(parents=True, exist_ok=True)
        d.to_parquet(dest / f"loc-{loc}.parquet", index=False)
    return counts


def ingest_openaq(
    openaq_dir: Path | None = None, out: Path = OPENAQ_OUT, workers: int = 8
) -> pd.DataFrame:
    openaq_dir = openaq_dir or raw_dir("openaq")
    zips = sorted(openaq_dir.glob("locationid=*/year=*.zip"))
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    with ProcessPoolExecutor(workers) as ex:
        counts = list(ex.map(_openaq_one, [(str(z), str(out)) for z in zips], chunksize=8))
    c = pd.DataFrame(counts)
    SUMMARY.mkdir(parents=True, exist_ok=True)
    c.to_csv(SUMMARY / "openaq_files.csv", index=False)
    return c


def main(which: str = "all") -> None:
    if which in ("mirror", "all"):
        s = ingest_mirror()
        print(s.to_string(index=False))
    if which in ("openaq", "all"):
        c = ingest_openaq()
        print(
            f"openaq: {len(c)} zips, {c.rows.sum():,} rows read, {c.kept.sum():,} PM2.5/PM10/NO2 kept"
        )


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "all")

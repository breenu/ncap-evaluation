"""Ingest rules: clock correction, padded rows, duplicates, OpenAQ zip reading.

All data here are SYNTHETIC, written to pytest's tmp_path (project rule: synthetic data only in tests, never in the pipeline).
"""

import gzip
import zipfile
from datetime import UTC, datetime

import duckdb
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from src.clean import ingest

PM25, PM10, NO2 = ingest.MIRROR_COLS["pm25"], ingest.MIRROR_COLS["pm10"], ingest.MIRROR_COLS["no2"]


def write_mirror(path, rows):
    """SYNTHETIC mirror file: same schema subset, Timestamp stored as tz=UTC like the real mirror."""
    t = pa.table(
        {
            "Station ID": [r[0] for r in rows],
            "Timestamp": pa.array([r[1] for r in rows], type=pa.timestamp("us", tz="UTC")),
            PM25: [r[2] for r in rows],
            PM10: [r[3] for r in rows],
            NO2: [r[4] for r in rows],
        }
    )
    pq.write_table(t, path)


def utc(*a):
    return datetime(*a, tzinfo=UTC)


@pytest.fixture
def mirror_dir(tmp_path):
    d = tmp_path / "raw"
    d.mkdir()
    write_mirror(
        d / "cpcb-air-quality-2020.parquet",
        [
            (
                "site_1",
                utc(2020, 1, 1, 0, 0),
                50.0,
                90.0,
                None,
            ),  # stored 00:00 = IST 00:00 -> UTC 18:30 prev day
            ("site_1", utc(2020, 1, 1, 0, 15), None, None, None),  # padded row: dropped
            ("site_1", utc(2020, 12, 31, 23, 45), 10.0, None, None),
            ("site_2", utc(2020, 6, 1, 12, 0), 5.0, 7.0, 3.0),
        ],
    )
    write_mirror(
        d / "cpcb-air-quality-2021.parquet",
        [
            ("site_1", utc(2020, 12, 31, 23, 45), 10.0, None, None),  # duplicate, identical value
            ("site_2", utc(2020, 6, 1, 12, 0), 6.0, 7.0, None),  # duplicate, conflicting PM2.5
        ],
    )
    return d


def read_out(out):
    return duckdb.sql(
        f"select * from read_parquet('{out.as_posix()}/*/*.parquet', hive_partitioning=true) order by sid, ts_utc"
    ).df()


def test_mirror_clock_is_stored_instant_minus_offset(mirror_dir, tmp_path, monkeypatch):
    monkeypatch.setattr(ingest, "mirror_shift_minutes", lambda: 330)
    out = tmp_path / "out" / "m"
    ingest.ingest_mirror(mirror_dir, out, summary_dir=tmp_path / "s")
    d = read_out(out)
    first = d[d.sid == "site_1"].iloc[0]
    assert first.ts_utc == pd.Timestamp("2019-12-31 18:30")
    # the Indian date of that slot is 1 Jan 2020, so it lands in the 2020 partition
    assert str(first.date_ist)[:10] == "2020-01-01" and first.year == 2020


def test_mirror_drops_padded_rows_and_resolves_duplicates(mirror_dir, tmp_path, monkeypatch):
    monkeypatch.setattr(ingest, "mirror_shift_minutes", lambda: 330)
    out = tmp_path / "out" / "m"
    s = ingest.ingest_mirror(mirror_dir, out, summary_dir=tmp_path / "s")
    d = read_out(out)
    assert len(d) == 3  # padded row gone; each duplicate collapsed to one row
    s2 = d[d.sid == "site_2"].iloc[0]
    assert pd.isna(s2.pm25)  # conflicting copies -> null, not a guess
    assert s2.pm10 == 7.0 and s2.no2 == 3.0  # agreeing / single copies kept
    assert int(s.pm25_conflicts.sum()) == 1
    assert int(s.duplicated_slots.sum()) == 2


@pytest.mark.parametrize("session_zone", ["UTC", "Asia/Calcutta", "America/New_York"])
def test_mirror_clock_does_not_depend_on_session_zone(mirror_dir, session_zone):
    """DEC-054: the offset was once measured on timestamps rendered in the laptop's zone."""
    con = duckdb.connect()
    con.execute(f"set TimeZone = '{session_zone}'")
    files = [p.as_posix() for p in sorted(mirror_dir.glob("*.parquet"))]
    got = con.execute(
        f"select min(ts_utc) from ({ingest.mirror_select_sql(files, 330)})"
    ).fetchone()[0]
    assert got == datetime(2019, 12, 31, 18, 30)


def make_openaq_zip(path, days):
    """SYNTHETIC OpenAQ location-year zip: one gzipped CSV per day, each with its own header."""
    header = "location_id,sensors_id,location,datetime,lat,lon,parameter,units,value\n"
    with zipfile.ZipFile(path, "w") as z:
        for name, lines in days.items():
            z.writestr(name, gzip.compress((header + "".join(lines)).encode("utf-8")))
        z.writestr("_index.csv", "key,etag,bytes,sha256\n")


def test_read_openaq_zip(tmp_path):
    p = tmp_path / "year=2025.zip"
    make_openaq_zip(
        p,
        {
            "location-7-20250101.csv.gz": [
                "7,1,X,2025-01-01T05:45:00+05:30,28.5,77.2,pm25,µg/m³,40.5\n",
                "7,2,X,2025-01-01T05:45:00+05:30,28.5,77.2,co,ppb,0.6\n",
            ],
            "location-7-20250102.csv.gz": [
                "7,3,X,2025-01-02T00:00:00+05:30,28.5,77.2,no2,ppb,44.0\n"
            ],
        },
    )
    d, counts = ingest.read_openaq_zip(p)
    assert counts["rows"] == 3 and counts["kept"] == 2  # co not kept
    assert set(d.parameter) == {"pm25", "no2"}
    assert d.loc[d.parameter == "pm25", "ts_utc"].iloc[0] == pd.Timestamp("2025-01-01 00:15")
    assert d.loc[d.parameter == "no2", "units"].iloc[0] == "ppb"  # label kept for the units check

"""Station-hour and station-day tables, with the quarter-hour and hourly flag rules applied.

Sources (DEC-037, DEC-055): the mirror's 15-minute values (data/interim/mirror_15min) up to its end
(Indian date 2025-12-31); after that OpenAQ's 15-minute values (data/interim/openaq_obs) for the
OpenAQ locations identified with each station by identical values (data/processed/stations.csv,
openaq_ids_by_data; DEC-058). Window: config windows.ground_start..ground_end, Indian dates.

Steps
 1. Instrument ceilings are detected from the network-wide histogram of exact 15-minute values
    (flags.detect_ceilings; config flags.ceiling_detect) -> data/interim/audit/ceilings.csv.
 2. Quarter-hours that are impossible (<= 0) or on a ceiling are removed and counted.
 3. Hourly means over Indian clock hours from the remaining quarter-hours; `{p}_q` = how many.
 4. Hourly flags: PM2.5 > PM10 beyond tolerance (both pollutants), flatlines of >= N hours.
    A flagged hour keeps its value in the table but is not used downstream (`{p}_ok` = False).
 5. Daily means over Indian days: the mean of the day's usable hourly means. `{p}_h1` = usable
    hours with >= 1 quarter-hour (primary rule), `{p}_h3` = with >= 3 (sensitivity; DEC-069), and
    `{p}_mean3` = the mean over those hours only.

Outputs
    data/processed/station_hour/year=YYYY/*.parquet
    data/processed/station_day.parquet
    data/interim/audit/flag_counts.csv  (per station-year and pollutant: quarter-hours removed,
                                         hours flagged by each rule)

    python -m src.clean.hourly
"""

import shutil

import duckdb
import numpy as np
import pandas as pd

from src.clean import flags
from src.clean.station_meta import load_stations
from src.common.paths import INTERIM, PROCESSED, params

MIRROR = (INTERIM / "mirror_15min" / "*" / "*.parquet").as_posix()
OPENAQ = (INTERIM / "openaq_obs" / "*" / "*.parquet").as_posix()
AUDIT = INTERIM / "audit"
HOUR_OUT = PROCESSED / "station_hour"
DAY_OUT = PROCESSED / "station_day.parquet"
POLLUTANTS = ("pm25", "pm10", "no2")
PM = ("pm25", "pm10")
IST = "interval 330 minute"
OPENAQ_FROM = "2026-01-01"  # first Indian date not covered by the mirror (its last file is 2025)


def _con() -> duckdb.DuckDBPyConnection:
    con = duckdb.connect()
    con.execute("set TimeZone = 'UTC'")
    con.execute("set memory_limit = '8GB'")
    con.execute(f"set temp_directory = '{(INTERIM / '_duckdb_tmp').as_posix()}'")
    return con


def quarters_view(con: duckdb.DuckDBPyConnection, stations: pd.DataFrame) -> None:
    """One view of all 15-minute values: sid, ts_ist (naive Indian time), pm25, pm10, no2, source."""
    w = params()["windows"]
    ids = [
        {"sid": r.sid, "location_id": int(i)}
        for r in stations.dropna(subset=["openaq_ids_by_data"]).itertuples()
        for i in str(r.openaq_ids_by_data).split(";")
    ]
    con.register("idmap", pd.DataFrame(ids))
    pivot = ", ".join(f"avg(value) filter (where parameter = '{p}') as {p}" for p in POLLUTANTS)
    con.execute(
        f"""create or replace temp view q as
        select sid, ts_utc + {IST} as ts_ist, pm25, pm10, no2, 'mirror' as source
        from read_parquet('{MIRROR}')
        where cast(ts_utc + {IST} as date) between '{w["ground_start"]}' and '{OPENAQ_FROM}'::date - 1
        union all
        select idmap.sid, ts_utc + {IST} as ts_ist, {pivot}, 'openaq' as source
        from read_parquet('{OPENAQ}') o join idmap using (location_id)
        where cast(ts_utc + {IST} as date) between '{OPENAQ_FROM}' and '{w["ground_end"]}'
        group by idmap.sid, ts_utc"""
    )


def ceilings(con: duckdb.DuckDBPyConnection) -> dict[str, list[float]]:
    cfg = params()["flags"]["ceiling_detect"]
    out, rows = {}, []
    for p in PM:
        h = con.execute(
            f"select round({p}, 2) as v, count(*) as n, count(distinct sid) as st from q where {p} is not null group by 1"
        ).df()
        out[p] = flags.detect_ceilings(
            h.v,
            h.n,
            cfg["min_value"],
            cfg["excess"],
            cfg["window"],
            h.st,
            cfg["min_stations"],
            cfg["min_count"],
        )
        for v in out[p]:
            hit = np.isclose(h.v, v)
            rows.append(
                {
                    "pollutant": p,
                    "ceiling": v,
                    "count": int(h.n[hit].sum()),
                    "stations": int(h.st[hit].sum()),
                }
            )
    AUDIT.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(AUDIT / "ceilings.csv", index=False)
    return out


def hourly_sql(ceil: dict[str, list[float]]) -> str:
    parts = []
    for p in POLLUTANTS:
        c = ceil.get(p, [])
        bad = f"({p} <= 0" + "".join(f" or abs({p} - {v}) < 0.005" for v in c) + ")"
        parts.append(
            f"avg({p}) filter (where not {bad}) as {p}, "
            f"count({p}) filter (where not {bad}) as {p}_q, "
            f"count({p}) filter (where {p} <= 0) as {p}_impossible, "
            f"count({p}) filter (where {p} > 0 and {bad}) as {p}_ceiling"
        )
    return f"""select sid, date_trunc('hour', ts_ist) as hour_ist, any_value(source) as source, {", ".join(parts)}
               from q where year(ts_ist) = ? group by sid, date_trunc('hour', ts_ist)"""


def hour_flags(h: pd.DataFrame) -> pd.DataFrame:
    """Hourly rules on one year of station-hours (all stations)."""
    fc = params()["flags"]
    tol = fc["pm25_gt_pm10_tolerance"]
    h = h.sort_values(["sid", "hour_ist"]).reset_index(drop=True)
    ratio = flags.pm25_exceeds_pm10(h.pm25, h.pm10, tol["abs_ugm3"], tol["rel"])
    for p in POLLUTANTS:
        h[f"{p}_ratio_flag"] = ratio if p in PM else False
        flat = pd.Series(False, index=h.index)
        for _, g in h[h[p].notna()].groupby("sid"):
            flat.loc[g.index] = flags.flatline(g[p].round(2), g.hour_ist, fc["flatline_min_hours"])
        h[f"{p}_flat_flag"] = flat
        h[f"{p}_ok"] = h[p].notna() & ~h[f"{p}_ratio_flag"] & ~h[f"{p}_flat_flag"]
    return h


def daily(h: pd.DataFrame) -> pd.DataFrame:
    q3 = params()["completeness"]["min_quarters_per_hour_sensitivity"]
    h = h.assign(date_ist=h.hour_ist.dt.normalize())
    out = h[["sid", "date_ist"]].drop_duplicates().set_index(["sid", "date_ist"])
    for p in POLLUTANTS:
        ok = h[h[f"{p}_ok"]]
        g = ok.groupby(["sid", "date_ist"])
        ok3 = ok[ok[f"{p}_q"] >= q3].groupby(["sid", "date_ist"])
        out[p] = g[p].mean()
        out[f"{p}_h1"] = g[p].size()
        out[f"{p}_mean3"] = ok3[p].mean()
        out[f"{p}_h3"] = ok3[p].size()
    out = out.reset_index()
    for c in out.columns:
        if c.endswith(("_h1", "_h3")):
            out[c] = out[c].fillna(0).astype("int16")
    return out


def counts(h: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for p in POLLUTANTS:
        g = h.groupby(["sid", h.hour_ist.dt.year.rename("year")])
        rows.append(
            g.agg(
                quarters_kept=(f"{p}_q", "sum"),
                quarters_impossible=(f"{p}_impossible", "sum"),
                quarters_ceiling=(f"{p}_ceiling", "sum"),
                hours=(p, "count"),
                hours_ratio_flag=(f"{p}_ratio_flag", "sum"),
                hours_flatline=(f"{p}_flat_flag", "sum"),
                hours_ok=(f"{p}_ok", "sum"),
            )
            .reset_index()
            .assign(pollutant=p)
        )
    return pd.concat(rows, ignore_index=True)


def main() -> None:
    stations = load_stations()
    con = _con()
    quarters_view(con, stations)
    ceil = ceilings(con)
    print("ceilings:", ceil)
    if HOUR_OUT.exists():
        shutil.rmtree(HOUR_OUT)
    w = params()["windows"]
    days, cnt = [], []
    sql = hourly_sql(ceil)
    for year in range(int(w["ground_start"][:4]), int(w["ground_end"][:4]) + 1):
        h = con.execute(sql, [year]).df()
        if h.empty:
            continue
        h = hour_flags(h)
        dest = HOUR_OUT / f"year={year}"
        dest.mkdir(parents=True)
        h.to_parquet(dest / "part.parquet", index=False)
        days.append(daily(h))
        cnt.append(counts(h))
        print(year, len(h), "station-hours", flush=True)
    pd.concat(days, ignore_index=True).to_parquet(DAY_OUT, index=False)
    pd.concat(cnt, ignore_index=True).to_csv(AUDIT / "flag_counts.csv", index=False)


if __name__ == "__main__":
    main()

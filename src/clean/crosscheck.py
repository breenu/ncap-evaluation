"""Cross-check: CPCB mirror vs OpenAQ, wherever both hold the same station (DEC-037 condition).

Both copies come from CPCB, through different pipelines: the mirror from CPCB's data repository
(scraped files), OpenAQ from its own ingestion of CPCB feeds. If they agree, a mirror error would have
to be repeated identically in an independent pipeline. Where they disagree, *how* they disagree
decides whether the mirror can be used for that period.

Pairs: every station in data/interim/station_crosswalk.csv with OpenAQ location ids, every id,
year and pollutant (PM2.5, PM10; NO2 as a units check). Both sides are on true UTC (mirror
corrected by DEC-054).

Per station-year-pollutant-location the metrics are:
  resolution     OpenAQ's time step for that location-year: '15-min' or 'hourly'
  pairs          paired values at that resolution (hourly: mirror averaged to the hour)
  exact_share    15-min: share of pairs equal to within 0.05 ug/m3 (both are printed to 2 dp)
                 hourly: share within 1 ug/m3
  r, bias        Pearson correlation and mean(mirror - openaq) at that resolution
  daily_*        on Indian days where both sides cover >= 75% of the day: count, correlation,
                 median and 95th percentile of |mirror - openaq| / mirror
  hourly_stamp   hourly pairs only: whether OpenAQ's hourly stamp marks the hour's start or end
                 (whichever correlates better; recorded, not assumed)

Outputs: data/interim/crosscheck/{pairs,monthly,anomalous_months}.csv and
docs/mirror-openaq-crosscheck.md (generated).

    python -m src.clean.crosscheck
"""

import duckdb
import numpy as np
import pandas as pd

from src.common.paths import DOCS, INTERIM

OUT = INTERIM / "crosscheck"
MIRROR = (INTERIM / "mirror_15min" / "*" / "*.parquet").as_posix()
OPENAQ = (INTERIM / "openaq_obs" / "*" / "*.parquet").as_posix()
EXACT_TOL = 0.05
HOURLY_TOL = 1.0
DAY_COVER = 0.75
POLLUTANTS = ("pm25", "pm10", "no2")


def agency(station_name: str) -> str:
    """Operating agency from a CPCB station name: 'Anand Vihar, Delhi - DPCC' -> 'DPCC'."""
    head, sep, tail = str(station_name).rpartition(" - ")
    return tail.split("(")[0].strip() if sep else ""


def monthly_agreement(con: duckdb.DuckDBPyConnection, years=range(2016, 2023)) -> pd.DataFrame:
    """PM2.5 15-minute pairs by month: exact share and median |difference|, all stations pooled.
    Needs the temp tables built by pair_metrics (m, o, map)."""
    ylist = ", ".join(str(y) for y in years)
    return con.execute(
        f"""select year(o.ts_utc + interval 330 minute) as year, month(o.ts_utc + interval 330 minute) as month,
                   count(distinct map.sid) as stations, count(*) as pairs,
                   avg((abs(m.value - o.value) < {EXACT_TOL})::int) as exact_share,
                   median(abs(m.value - o.value)) as median_abs_diff
            from o join map using (location_id)
            join m on m.sid = map.sid and m.parameter = o.parameter and m.ts_utc = o.ts_utc
            where o.parameter = 'pm25' and minute(o.ts_utc) <> 0
              and year(o.ts_utc + interval 330 minute) in ({ylist})
            group by all order by 1, 2"""
    ).df()


def pair_metrics(con: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    """All metrics in DuckDB. Tables expected: map(sid, location_id)."""
    unpivot = " union all ".join(
        f"select sid, ts_utc, '{p}' as parameter, {p} as value from read_parquet('{MIRROR}') where {p} is not null"
        for p in POLLUTANTS
    )
    con.execute(f"create or replace temp table m as {unpivot}")
    con.execute(
        f"""create or replace temp table o as
            select location_id, parameter, ts_utc, any_value(units) as units, avg(value) as value
            from read_parquet('{OPENAQ}') where location_id in (select location_id from map)
            group by all"""
    )
    # OpenAQ resolution per location-year-parameter: 15-min if most stamps are off the hour
    con.execute(
        """create or replace temp table res as
           select location_id, parameter, year(ts_utc + interval 330 minute) as year,
                  case when avg((minute(ts_utc) <> 0)::int) > 0.5 then '15-min' else 'hourly' end as resolution,
                  any_value(units) as units
           from o group by all"""
    )
    day = "cast(ts_utc + interval 330 minute as date)"
    q15 = f"""
      with j as (
        select map.sid, o.location_id, o.parameter, year(o.ts_utc + interval 330 minute) as year,
               o.ts_utc, m.value as mv, o.value as ov
        from o join map using (location_id)
        join res on res.location_id = o.location_id and res.parameter = o.parameter
             and res.year = year(o.ts_utc + interval 330 minute) and res.resolution = '15-min'
        join m on m.sid = map.sid and m.parameter = o.parameter and m.ts_utc = o.ts_utc),
      d as (
        select sid, location_id, parameter, year, {day} as d, avg(mv) as mv, avg(ov) as ov, count(*) as n
        from j group by all having count(*) >= {int(96 * DAY_COVER)})
      select a.*, b.daily_n, b.daily_r, b.daily_rel_med, b.daily_rel_p95, '' as hourly_stamp from (
        select sid, location_id, parameter, year, '15-min' as resolution, count(*) as pairs,
               avg((abs(mv - ov) < {EXACT_TOL})::int) as exact_share, corr(mv, ov) as r,
               avg(mv - ov) as bias, median(mv / nullif(ov, 0)) as ratio_med
        from j group by all) a
      left join (
        select sid, location_id, parameter, year, count(*) as daily_n, corr(mv, ov) as daily_r,
               median(abs(mv - ov) / nullif(mv, 0)) as daily_rel_med,
               quantile_cont(abs(mv - ov) / nullif(mv, 0), 0.95) as daily_rel_p95
        from d group by all) b using (sid, location_id, parameter, year)"""
    p15 = con.execute(q15).df()

    # hourly OpenAQ: mirror averaged to clock hours [h, h+1); OpenAQ stamp t compared with
    # the mirror hour starting at t ('start') and ending at t ('end').
    con.execute(
        """create or replace temp table mh as
           select sid, parameter, date_trunc('hour', ts_utc) as h, avg(value) as value, count(*) as q
           from m group by all having count(*) >= 3"""
    )
    out = []
    for stamp, shift in (("start", 0), ("end", 60)):
        q = f"""
          with j as (
            select map.sid, o.location_id, o.parameter, year(o.ts_utc + interval 330 minute) as year,
                   o.ts_utc, mh.value as mv, o.value as ov
            from o join map using (location_id)
            join res on res.location_id = o.location_id and res.parameter = o.parameter
                 and res.year = year(o.ts_utc + interval 330 minute) and res.resolution = 'hourly'
            join mh on mh.sid = map.sid and mh.parameter = o.parameter
                 and mh.h = o.ts_utc - interval {shift} minute),
          d as (
            select sid, location_id, parameter, year, {day} as d, avg(mv) as mv, avg(ov) as ov
            from j group by all having count(*) >= {int(24 * DAY_COVER)})
          select a.*, b.daily_n, b.daily_r, b.daily_rel_med, b.daily_rel_p95, '{stamp}' as hourly_stamp from (
            select sid, location_id, parameter, year, 'hourly' as resolution, count(*) as pairs,
                   avg((abs(mv - ov) < {HOURLY_TOL})::int) as exact_share, corr(mv, ov) as r,
                   avg(mv - ov) as bias, median(mv / nullif(ov, 0)) as ratio_med
            from j group by all) a
          left join (
            select sid, location_id, parameter, year, count(*) as daily_n, corr(mv, ov) as daily_r,
                   median(abs(mv - ov) / nullif(mv, 0)) as daily_rel_med,
                   quantile_cont(abs(mv - ov) / nullif(mv, 0), 0.95) as daily_rel_p95
            from d group by all) b using (sid, location_id, parameter, year)"""
        out.append(con.execute(q).df())
    ph = pd.concat(out)
    ph = ph.sort_values("r", ascending=False).drop_duplicates(
        ["sid", "location_id", "parameter", "year"]
    )
    pairs = pd.concat([p15, ph], ignore_index=True)
    units = con.execute("select location_id, parameter, year, units from res").df()
    return pairs.merge(units, on=["location_id", "parameter", "year"], how="left")


# CPCB National Air Quality Index (2014), PM2.5 (24-hour) breakpoints: (conc lo, conc hi, index lo, index hi)
AQI_PM25 = ((0, 30, 0, 50), (30, 60, 50, 100), (60, 90, 100, 200), (90, 120, 200, 300),
            (120, 250, 300, 400), (250, 380, 400, 500))  # fmt: skip


def aqi_pm25(conc: float) -> float:
    """CPCB PM2.5 AQI sub-index of a 24-hour mean concentration (linear within each band)."""
    for lo, hi, ilo, ihi in AQI_PM25:
        if conc <= hi:
            return ilo + (conc - lo) * (ihi - ilo) / (hi - lo)
    return 500.0


def anomalous_months(
    con: duckdb.DuckDBPyConnection,
    monthly: pd.DataFrame,
    max_exact: float = 0.05,
    min_pairs: int = 2000,
) -> pd.DataFrame:
    """For months where almost nothing matches, test what OpenAQ's series is instead. Per station:
    correlation with the mirror at the same time, with the mirror's trailing 24-hour mean, and the
    median gap to CPCB's PM2.5 AQI sub-index of that 24-hour mean (best of +-2 h alignments).
    Needs the temp tables built by pair_metrics (m, o, map)."""
    rows = []
    bad = monthly[(monthly.exact_share < max_exact) & (monthly.pairs >= min_pairs)]
    for y, mo in zip(bad.year, bad.month, strict=True):
        start = pd.Timestamp(year=int(y), month=int(mo), day=1)
        end = start + pd.offsets.MonthBegin(1)
        o = con.execute(
            """select map.sid, o.ts_utc, o.value as ov from o join map using (location_id)
               where o.parameter = 'pm25' and o.ts_utc >= ? and o.ts_utc < ?""",
            [start, end],
        ).df()
        m = con.execute(
            """select sid, ts_utc, value as mv from m where parameter = 'pm25'
               and ts_utc >= ? and ts_utc < ?""",
            [start - pd.Timedelta(days=2), end],
        ).df()
        for sid, g in o.groupby("sid"):
            ms = m[m.sid == sid].set_index("ts_utc").mv.sort_index()
            if len(ms) < 500 or len(g) < 50:
                continue
            ms = ms.reindex(pd.date_range(ms.index.min(), ms.index.max(), freq="15min"))
            roll = ms.rolling(96, min_periods=72).mean()
            same = ms.reindex(g.ts_utc).to_numpy()
            ok = ~np.isnan(same)
            best = None
            for sh in range(-120, 121, 15):
                x = roll.reindex(g.ts_utc + pd.Timedelta(minutes=sh)).to_numpy()
                k = ~np.isnan(x)
                if k.sum() < 50:
                    continue
                gap = np.median(np.abs(np.array([aqi_pm25(v) for v in x[k]]) - g.ov.to_numpy()[k]))
                r24 = np.corrcoef(x[k], g.ov.to_numpy()[k])[0, 1]
                if best is None or gap < best[0]:
                    best = (gap, r24)
            if best is None or ok.sum() < 50:
                continue
            rows.append(
                {
                    "year": int(y),
                    "month": int(mo),
                    "sid": sid,
                    "r_same_time": np.corrcoef(same[ok], g.ov.to_numpy()[ok])[0, 1],
                    "median_abs_diff": float(np.median(np.abs(same[ok] - g.ov.to_numpy()[ok]))),
                    "r_24h_mean": best[1],
                    "median_gap_to_aqi": best[0],
                }
            )
    d = pd.DataFrame(rows)
    if d.empty:
        return d
    return (
        d.groupby(["year", "month"])
        .agg(
            stations=("sid", "size"),
            r_same_time=("r_same_time", "median"),
            median_abs_diff_ugm3=("median_abs_diff", "median"),
            r_24h_mean=("r_24h_mean", "median"),
            median_gap_to_aqi=("median_gap_to_aqi", "median"),
        )
        .reset_index()
    )


def location_map(crosswalk: pd.DataFrame) -> pd.DataFrame:
    x = crosswalk.dropna(subset=["openaq_location_ids"])
    rows = [
        {"sid": r.sid, "location_id": int(i)}
        for r in x.itertuples()
        for i in str(r.openaq_location_ids).split(";")
    ]
    return pd.DataFrame(rows)


def run(crosswalk: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    con = duckdb.connect()
    con.execute("set TimeZone = 'UTC'")
    con.execute("set memory_limit = '8GB'")
    con.register("map_df", location_map(crosswalk))
    con.execute("create temp table map as select * from map_df")
    p = pair_metrics(con)
    monthly = monthly_agreement(con)
    anomalies = anomalous_months(con, monthly)
    names = crosswalk.set_index("sid").sname
    p["agency"] = p.sid.map(names).map(agency)
    p["sname"] = p.sid.map(names)
    return p.sort_values(["parameter", "year", "sid", "location_id"]), monthly, anomalies


# ------------------------------------------------------------------ report


def good_pairs(p: pd.DataFrame, min_pairs: int = 500) -> pd.DataFrame:
    """Station-year pairs with enough overlap to judge (and PM only)."""
    return p[(p.pairs >= min_pairs) & p.parameter.isin(["pm25", "pm10"])]


def by_year(p: pd.DataFrame) -> pd.DataFrame:
    g = good_pairs(p).groupby(["parameter", "year", "resolution"])
    return g.agg(
        station_years=("sid", "nunique"),
        pairs=("pairs", "sum"),
        exact_median=("exact_share", "median"),
        exact_ge_95pct=("exact_share", lambda s: (s >= 0.95).mean()),
        r_median=("r", "median"),
        bias_median=("bias", "median"),
        daily_rel_median=("daily_rel_med", "median"),
        daily_rel_p95_median=("daily_rel_p95", "median"),
        daily_r_median=("daily_r", "median"),
    ).reset_index()


def by_agency(p: pd.DataFrame, years=(2016, 2017, 2018, 2019, 2020, 2021)) -> pd.DataFrame:
    g = good_pairs(p)
    g = g[(g.parameter == "pm25") & g.year.isin(years) & (g.resolution == "15-min")]
    t = g.groupby("agency").agg(
        station_years=("sid", "size"),
        stations=("sid", "nunique"),
        exact_median=("exact_share", "median"),
        exact_ge_95pct=("exact_share", lambda s: (s >= 0.95).mean()),
        daily_rel_median=("daily_rel_med", "median"),
        daily_rel_p95_median=("daily_rel_p95", "median"),
        bias_median=("bias", "median"),
    )
    return t.sort_values("station_years", ascending=False).reset_index()


def _fmt(df: pd.DataFrame) -> str:
    d = df.copy()
    for c in d.columns:
        if d[c].dtype.kind == "f":
            d[c] = d[c].map(lambda v: "" if pd.isna(v) else f"{v:.3f}")
    head = "| " + " | ".join(d.columns) + " |\n|" + "---|" * len(d.columns) + "\n"
    return head + "\n".join(
        "| " + " | ".join(str(v) for v in r) + " |" for r in d.itertuples(index=False)
    )


def mixed_share(p: pd.DataFrame) -> pd.DataFrame:
    """Within one station-year, is disagreement all-or-nothing? Share of station-years whose exact
    share is below 5% or above 95% (bimodal = whole series re-processed, not scattered edits)."""
    g = good_pairs(p)
    g = g[(g.resolution == "15-min") & (g.parameter == "pm25")]
    return (
        g.assign(
            band=pd.cut(
                g.exact_share,
                [-0.01, 0.05, 0.5, 0.95, 1.0],
                labels=["<5%", "5-50%", "50-95%", ">95%"],
            )
        )
        .groupby(["year", "band"], observed=False)
        .size()
        .unstack(fill_value=0)
        .reset_index()
    )


def no2_units(p: pd.DataFrame) -> pd.DataFrame:
    g = p[(p.parameter == "no2") & (p.pairs >= 500)]
    return (
        g.groupby(["year", "units"])
        .agg(
            station_years=("sid", "size"),
            exact_median=("exact_share", "median"),
            ratio_median=("ratio_med", "median"),
        )
        .reset_index()
    )


def write_report(
    p: pd.DataFrame,
    monthly: pd.DataFrame,
    anomalies: pd.DataFrame,
    path=DOCS / "mirror-openaq-crosscheck.md",
) -> None:
    yr = by_year(p)
    ag = by_agency(p)
    mix = mixed_share(p)
    nu = no2_units(p)
    gp = good_pairs(p)
    pre = gp[(gp.year <= 2022) & (gp.parameter == "pm25")]
    low = pre[pre.exact_share < 0.05]
    lines = [
        "# Mirror vs OpenAQ cross-check",
        "",
        "*Generated by `python -m src.clean.crosscheck`. Do not edit by hand.*",
        "",
        "Both sources copy CPCB's station data through different pipelines. Pairs are the same station "
        "(name crosswalk, DEC-045) on the same true-UTC timestamp (mirror corrected by DEC-054). "
        f"Only station-years with at least 500 paired values are summarised ({gp.groupby(['sid', 'year']).ngroups} station-years, "
        f"{gp.pairs.sum():,} paired values).",
        "",
        "Definitions: *exact* = equal within 0.05 ug/m3 for 15-minute pairs (both are printed to 2 decimals), "
        "within 1 ug/m3 for hourly pairs. *daily_rel* = |mirror - OpenAQ| / mirror for Indian days where both "
        "cover at least 75% of the day; the table shows the median across station-years of each station-year's "
        "median and 95th percentile. *bias* = mean(mirror - OpenAQ), ug/m3.",
        "",
        "## 1. Agreement by year",
        "",
        _fmt(yr),
        "",
        "## 2. Pre-2023 disagreement is all-or-nothing per station-year (PM2.5, 15-minute pairs)",
        "",
        "Count of station-years by the share of exactly equal values. Scattered corrections (a few "
        "edited values) would fill the middle bands; whole series processed differently fall in '<5%'.",
        "",
        _fmt(mix),
        "",
        "## 3. Which stations disagree: by operating agency (PM2.5, 15-minute pairs, 2016-2021)",
        "",
        _fmt(ag),
        "",
        "## 4. What the disagreement looks like",
        "",
        f"Pre-2023 PM2.5 station-years with under 5% exact matches: {len(low)} of {len(pre)}. For these, "
        f"the median correlation of 15-minute values is {low.r.median():.3f}, the median bias is "
        f"{low.bias.median():+.2f} ug/m3, the median ratio mirror/OpenAQ is {low.ratio_med.median():.3f}, and "
        f"daily means differ by a median {100 * low.daily_rel_med.median():.2f}% "
        f"(95th percentile of days: median {100 * low.daily_rel_p95.median():.2f}% across station-years).",
        "",
        "## 5. Agreement by month, 2016-2022 (PM2.5, 15-minute pairs, all stations pooled)",
        "",
        "Where agreement is partial, this shows whether it is a period (a feed change) and how large the "
        "differences are (median |mirror - OpenAQ|, ug/m3).",
        "",
        _fmt(monthly[monthly.pairs >= 500]),
        "",
        "**Months where almost nothing matches** (exact share under 5%, at least 2,000 pairs): what "
        "OpenAQ's series is instead. Per station, medians across stations: correlation with the mirror at "
        "the same time; |difference| in ug/m3; correlation with the mirror's trailing 24-hour mean; and "
        "the median gap between OpenAQ's value and CPCB's PM2.5 AQI sub-index of that 24-hour mean "
        "(best alignment within +-2 h). A high 24-hour correlation with a small AQI gap means OpenAQ "
        "stored an index, not a concentration, that month.",
        "",
        _fmt(anomalies) if len(anomalies) else "(none)",
        "",
        "## 6. NO2 units in OpenAQ",
        "",
        "OpenAQ labels NO2 'ppb' from 2025. If the values were really ppb, the mirror (ug/m3) would be "
        "about 1.88 times OpenAQ's; a ratio of 1 with exact matches means the label is wrong and the "
        "values are ug/m3.",
        "",
        _fmt(nu),
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    x = pd.read_csv(INTERIM / "station_crosswalk.csv")
    p, monthly, anomalies = run(x)
    p.to_csv(OUT / "pairs.csv", index=False)
    monthly.to_csv(OUT / "monthly.csv", index=False)
    anomalies.to_csv(OUT / "anomalous_months.csv", index=False)
    write_report(p, monthly, anomalies)
    print(by_year(p).to_string(index=False))
    print(by_agency(p).to_string(index=False))


if __name__ == "__main__":
    main()

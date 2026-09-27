"""Near-constant (stuck or over-smoothed) analysers: a detector added in Phase 5 (DEC-110).

A dead-flat analyser is caught by the flatline rule (identical hourly means for >= 4 h, DEC-068).
This catches the slower failure: values that change a little every hour but barely move from day to
day, for weeks. The deweathering pilot found one (Bagalkot, site_5264: 2022-25, day-to-day SD of log
PM a few percent, against about 30% at a typical station).

Statistic, per station, pollutant and day: s = SD of log daily PM over a centred window of
`window_days` calendar days with at least `min_days` valid days (primary completeness rule).
Reference: the median s of the station's neighbours (within `flags.neighbour_radius_km`,
station-level coordinates, as in src/clean/spatial.py) on the same day, when at least one has one.

Day flag:   s < S  AND  (no neighbour reference  OR  s / reference < R)
    "near-constant" and "not a calm spell its airshed shares". S and R are calibrated from the data:
    each is the `calibration_quantile` (0.1%) quantile over the days of clearly working stations,
    i.e. station-years whose daily series correlates with the neighbours' at >= 0.8
    (station_year_quality.neighbour_corr), so the rule's false-alarm rate on working stations is
    at most 0.1% of days for each part. S is calibrated per region (DEC-075), because the calm tail
    differs by region (the IGP's air is rarely that steady, the coast's more often), with the
    national value for a region with fewer than `min_region_stations` working stations. R is
    national: it is already relative to the local airshed.
Station-year flag: >= `min_flag_days_per_year` flagged days in the year (a stuck month).

Use (DEC-110): flagged station-years are excluded in the primary analysis (from the deweathering fit
and from every station-year and city aggregate); the registered flags alone are the sensitivity.

Outputs
    data/interim/audit/near_constant_days.parquet    sid, pollutant, date_ist, s, ref, ratio, flag
    data/processed/station_year_near_constant.parquet sid, pollutant, year, flag_days, near_constant
    docs/near_constant_check.md                       calibration, false alarms, what it catches

    python -m src.clean.nearconstant
"""

import numpy as np
import pandas as pd

from src.clean.spatial import AUDIT, PM, neighbour_lists, valid_hours
from src.clean.station_meta import load_stations
from src.common.paths import DOCS, INTERIM, PROCESSED, params


def cfg() -> dict:
    return params()["flags"]["near_constant"]


def rolling_sd(day: pd.DataFrame, pollutant: str, window: int, min_days: int) -> pd.DataFrame:
    """Centred rolling SD of log daily PM over `window` calendar days, per station."""
    x = day[day[f"{pollutant}_h1"] >= valid_hours()][["sid", "date_ist", pollutant]]
    x = x[x[pollutant] > 0]
    wide = np.log(x.pivot(index="date_ist", columns="sid", values=pollutant))
    wide = wide.reindex(pd.date_range(wide.index.min(), wide.index.max(), freq="D"))
    s = wide.rolling(window, center=True, min_periods=min_days).std()
    s = s.where(wide.notna())  # only on the station's own valid days
    s.index.name = "date_ist"
    return s


def neighbour_ref(s: pd.DataFrame, nbrs: dict[str, list[str]]) -> pd.DataFrame:
    ref = pd.DataFrame(np.nan, index=s.index, columns=s.columns)
    for sid in s.columns:
        cols = [c for c in nbrs.get(sid, []) if c in s.columns]
        if cols:
            ref[sid] = s[cols].median(axis=1, skipna=True)
    return ref


def day_table(day: pd.DataFrame, nbrs: dict[str, list[str]]) -> pd.DataFrame:
    c = cfg()
    out = []
    for p in PM:
        s = rolling_sd(day, p, c["window_days"], c["min_days"])
        ref = neighbour_ref(s, nbrs)
        t = pd.DataFrame({"s": s.stack(), "ref": ref.stack(future_stack=True).reindex(s.stack().index)})
        out.append(t.reset_index().rename(columns={"level_1": "sid"}).assign(pollutant=p))
    t = pd.concat(out, ignore_index=True)
    t["ratio"] = t.s / t.ref
    t["year"] = t.date_ist.dt.year
    return t


def calibrate(t: pd.DataFrame, q: pd.DataFrame) -> dict:
    """Thresholds from clearly working station-years (neighbour correlation >= the minimum).
    `t` carries each station's region."""
    c = cfg()
    good = q[q.neighbour_corr >= c["normal_min_neighbour_corr"]][["sid", "pollutant", "year"]]
    n = t.merge(good, on=["sid", "pollutant", "year"])
    qq = c["calibration_quantile"]
    national = float(n.s.quantile(qq))
    reg = n.groupby("region").agg(stations=("sid", "nunique"), S=("s", lambda s: s.quantile(qq)))
    reg["S_used"] = reg.S.where(reg.stations >= c["min_region_stations"], national)
    return {
        "S_national": national,
        "S": reg.S_used.to_dict(),
        "S_table": reg.reset_index(),
        "R": float(n.ratio.dropna().quantile(qq)),
        "normal_days": len(n),
        "normal_station_years": len(good),
        "normal_stations": int(n.sid.nunique()),
    }


def flag_days(t: pd.DataFrame, S: dict, R: float, national: float) -> pd.Series:
    s_thr = t.region.map(S).fillna(national)
    return (t.s < s_thr) & (t.ref.isna() | (t.ratio < R))


def station_years(t: pd.DataFrame) -> pd.DataFrame:
    y = t.groupby(["sid", "pollutant", "year"]).agg(flag_days=("flag", "sum"), days=("flag", "size")).reset_index()
    y["near_constant"] = y.flag_days >= cfg()["min_flag_days_per_year"]
    return y


def md(df: pd.DataFrame) -> str:
    cols = list(df.columns)
    rows = ["| " + " | ".join(map(str, cols)) + " |", "|" + "---|" * len(cols)]
    rows += ["| " + " | ".join("" if pd.isna(v) else str(v) for v in r) + " |" for r in df.itertuples(index=False)]
    return "\n".join(rows)


def report(t: pd.DataFrame, y: pd.DataFrame, cal: dict, q: pd.DataFrame) -> str:
    c = cfg()
    good = q[q.neighbour_corr >= c["normal_min_neighbour_corr"]][["sid", "pollutant", "year"]]
    gy = y.merge(good, on=["sid", "pollutant", "year"])
    gd = t.merge(good, on=["sid", "pollutant", "year"])
    valid = q[q.valid_q1_t75][["sid", "pollutant", "year"]]
    yv = y.merge(valid, on=["sid", "pollutant", "year"])
    by = (
        yv.groupby(["pollutant", "year"])
        .agg(valid_station_years=("near_constant", "size"), near_constant=("near_constant", "sum"))
        .reset_index()
    )
    hit = yv[yv.near_constant].merge(
        load_stations()[["sid", "sname"]], on="sid", how="left"
    ).sort_values(["sid", "pollutant", "year"])
    per_station = hit.groupby(["sid", "sname", "pollutant"]).agg(
        years=("year", lambda s: ", ".join(map(str, s))), flag_days=("flag_days", "sum")
    ).reset_index()
    no_ref = t.ref.isna().mean()
    return f"""# Near-constant analyser check

*Generated by `python -m src.clean.nearconstant`. Do not edit by hand. Rule and reasons: DEC-110 (a dated deviation from the registered plan, added in Phase 5 before any treatment-effect estimate).*

## Rule

- **Statistic:** the SD of log daily PM over a centred {c['window_days']}-day window (≥ {c['min_days']} valid days), per station, pollutant and day. A typical station-day has about 0.3 (roughly ±30% day to day).
- **Neighbour reference:** the median of the same statistic at stations within {params()['flags']['neighbour_radius_km']} km on the same day. {100 * (1 - no_ref):.0f}% of station-days have one.
- **A day is flagged** if the statistic is below **S** (by region, below) and, where neighbours exist, also below **R = {cal['R']:.3f} × the neighbours' median**: nearly constant, and not a calm spell its airshed shares.
- **S by region:** the calm tail differs by region, so S is calibrated per region; a region with fewer than {c['min_region_stations']} clearly working stations uses the national value ({cal['S_national']:.4f}). A first version used one national S; it over-flagged the coast and peninsula, whose working stations are calmer in the tail, and under-flagged the IGP.
- **A station-year is flagged** with ≥ {c['min_flag_days_per_year']} flagged days.
- **Calibration:** S and R are each the {100 * c['calibration_quantile']:.1f}% quantile over the days of clearly working stations: station-years whose daily series correlates with the neighbours' at ≥ {c['normal_min_neighbour_corr']} ({cal['normal_station_years']:,} station-years, {cal['normal_days']:,} days, {cal['normal_stations']} stations).

S by region (0.1% quantile of working stations' days; `S_used` is what the rule applies):

{md(cal['S_table'].round(4))}

## False alarms on clearly working stations

- Days flagged: {int(gd.flag.sum()):,} of {len(gd):,} ({100 * gd.flag.mean():.3f}%).
- Station-years flagged: {int(gy.near_constant.sum())} of {len(gy):,}.

## What it catches (station-years valid under the primary completeness rule)

{md(by[by.near_constant > 0])}

**Total: {int(yv.near_constant.sum())} of {len(yv):,} valid station-years** ({int(yv[yv.pollutant == 'pm25'].near_constant.sum())} PM2.5, {int(yv[yv.pollutant == 'pm10'].near_constant.sum())} PM10), at {hit.sid.nunique()} stations. Also flagged but already invalid under the completeness rule: {int(y.near_constant.sum() - yv.near_constant.sum())} station-years.

{md(per_station)}

In the primary analysis these station-years are excluded from the deweathering fit and from every station-year and city aggregate. The sensitivity analysis keeps them (registered flags only).
"""


def main() -> None:
    day = pd.read_parquet(
        PROCESSED / "station_day.parquet", columns=["sid", "date_ist"] + [f"{p}{s}" for p in PM for s in ("", "_h1")]
    )
    q = pd.read_parquet(PROCESSED / "station_year_quality.parquet")
    nbrs = neighbour_lists(load_stations(), params()["flags"]["neighbour_radius_km"])
    t = day_table(day, nbrs)
    t = t.merge(pd.read_csv(INTERIM / "station_regions.csv")[["sid", "region"]], on="sid", how="left")
    cal = calibrate(t, q)
    t["flag"] = flag_days(t, cal["S"], cal["R"], cal["S_national"])
    y = station_years(t)
    AUDIT.mkdir(parents=True, exist_ok=True)
    t.drop(columns="year").to_parquet(AUDIT / "near_constant_days.parquet", index=False)
    y.to_parquet(PROCESSED / "station_year_near_constant.parquet", index=False)
    text = report(t, y, cal, q)
    (DOCS / "near_constant_check.md").write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()

"""Completeness rules and the per-station-year reliability score (proposal stage 3), DEC-073.

Completeness (config `completeness`). A threshold t applies to both levels: a valid day has usable
hourly values in >= ceil(24 t) hours, and a valid station-year has valid days on >= t of the days in
the analysis window that year (2026: 1 Jan-31 Mar). Variants, per pollutant:
    valid_q1_t75   primary: an hour counts with >= 1 clean quarter-hour, t = 75%
    valid_q1_t60, valid_q1_t90   threshold sensitivity (proposal validation table)
    valid_q3_t75   hour rule sensitivity: an hour counts only with >= 3 of 4 quarter-hours (DEC-069)

Reliability score, 0-100, for every station-year with any data:
    score = 100 x completeness x (1 - flagged share) x check_penalty ^ (failed checks)
    completeness   valid days (primary rule) / days in the window that year
    flagged share  (hours flagged PM2.5>PM10 + hours in flatlines + quarter-hours removed / 4)
                   / hours with any data
    failed checks  neighbour-correlation outlier, satellite-ratio outlier (PM2.5 only), and a level
                   shift (changepoint) dated in that year; each multiplies the score by
                   config reliability.check_penalty (0.8). A check that cannot be run (no
                   neighbours, no satellite year) is not counted as failed; `checks_run` says how
                   many were run.
The score describes trustworthiness for the audit and the heatmap (figure 8). It does not remove
data: exclusion is by the completeness rule (primary) and by flagged hours (already removed).

Output: data/processed/station_year_quality.parquet

    python -m src.clean.reliability
"""

import math

import pandas as pd

from src.clean.spatial import AUDIT, PM
from src.common.paths import INTERIM, PROCESSED, params

VARIANTS = {
    "q1_t75": ("h1", 0.75),
    "q1_t60": ("h1", 0.60),
    "q1_t90": ("h1", 0.90),
    "q3_t75": ("h3", 0.75),
}


def window_days(year: int) -> int:
    w = params()["windows"]
    start = max(pd.Timestamp(w["ground_start"]), pd.Timestamp(year, 1, 1))
    end = min(pd.Timestamp(w["ground_end"]), pd.Timestamp(year, 12, 31))
    return max(0, (end - start).days + 1)


def completeness(day: pd.DataFrame) -> pd.DataFrame:
    """Valid days and valid-year flags for every variant, per station-year-pollutant."""
    day = day.assign(year=pd.to_datetime(day.date_ist).dt.year)
    out = []
    for p in PM:
        base = day[day[f"{p}_h1"] > 0].groupby(["sid", "year"]).size().rename("days_with_data")
        t = base.to_frame()
        for name, (h, thr) in VARIANTS.items():
            ok = day[day[f"{p}_{h}"] >= math.ceil(24 * thr)]
            t[f"valid_days_{name}"] = ok.groupby(["sid", "year"]).size()
        t = t.fillna(0).reset_index()
        t["window_days"] = t.year.map(window_days)
        for name, (_, thr) in VARIANTS.items():
            t[f"valid_{name}"] = t[f"valid_days_{name}"] >= thr * t.window_days
        out.append(t.assign(pollutant=p))
    return pd.concat(out, ignore_index=True)


def score(q: pd.DataFrame, penalty: float) -> pd.Series:
    """Reliability score from its parts (pure; unit-tested)."""
    comp = (q.valid_days_q1_t75 / q.window_days).clip(0, 1)
    flagged = ((q.hours_ratio_flag + q.hours_flatline + (q.quarters_ceiling + q.quarters_impossible) / 4)
               / q.hours.clip(lower=1)).clip(0, 1)  # fmt: skip
    return 100 * comp * (1 - flagged) * penalty**q.failed_checks


def build() -> pd.DataFrame:
    day = pd.read_parquet(PROCESSED / "station_day.parquet")
    q = completeness(day)
    fc = pd.read_csv(AUDIT / "flag_counts.csv")
    q = q.merge(fc, on=["sid", "year", "pollutant"], how="left")
    sp = pd.read_csv(AUDIT / "spatial_station_year.csv")
    q = q.merge(
        sp[["sid", "year", "pollutant", "neighbour_corr", "sat_ratio", "flag_neighbour", "flag_satellite"]],
        on=["sid", "year", "pollutant"], how="left",
    )  # fmt: skip
    cp = pd.read_csv(AUDIT / "changepoints.csv", parse_dates=["date"])
    cp = (
        cp.assign(year=cp.date.dt.year)
        .groupby(["sid", "year", "pollutant"])
        .size()
        .rename("changepoints")
    )
    q = q.merge(cp.reset_index(), on=["sid", "year", "pollutant"], how="left")
    q["changepoints"] = q.changepoints.fillna(0).astype(int)
    q["flag_neighbour"] = q.flag_neighbour.astype("boolean").fillna(False).astype(bool)
    q["flag_satellite"] = q.flag_satellite.astype("boolean").fillna(False).astype(bool)
    q["failed_checks"] = (
        q.flag_neighbour.astype(int)
        + q.flag_satellite.astype(int)
        + (q.changepoints > 0).astype(int)
    )
    q["checks_run"] = q.neighbour_corr.notna().astype(int) + q.sat_ratio.notna().astype(int) + 1
    for c in [
        "hours",
        "hours_ratio_flag",
        "hours_flatline",
        "quarters_ceiling",
        "quarters_impossible",
    ]:
        q[c] = q[c].fillna(0)
    q["reliability"] = score(q, params()["reliability"]["check_penalty"]).round(1)
    return q


def main() -> None:
    q = build()
    q.to_parquet(PROCESSED / "station_year_quality.parquet", index=False)
    t = q[q.year <= 2025].groupby(["pollutant", "year"])[[f"valid_{v}" for v in VARIANTS]].sum()
    print(t.astype(int).to_string())
    (INTERIM / "audit").mkdir(parents=True, exist_ok=True)
    t.to_csv(INTERIM / "audit" / "valid_station_years.csv")
    print(q.groupby("pollutant").reliability.describe())


if __name__ == "__main__":
    main()

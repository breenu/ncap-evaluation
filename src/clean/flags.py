"""Data-quality flag rules (proposal stage 3). One pure function per rule; each is unit-tested on
synthetic data in tests/test_flags.py. Thresholds come from config/params.yaml `flags` (DEC-068).

Quarter-hour rules (applied to 15-minute values before hourly means):
    impossible_value   value <= 0 (none occur in the mirror, which suggests CPCB removed them; the
                       rule stays so that a new data vintage is still checked)
    ceiling_pin        value equals an instrument ceiling found by `detect_ceilings`

Hourly rules (on hourly means, Indian clock hours):
    pm25_exceeds_pm10  PM2.5 > PM10 + max(abs tolerance, rel tolerance x PM10) at the same station-hour
    flatline           a run of identical hourly means lasting >= N consecutive hours

A flagged value is removed before daily means; flags are counted per station-year for the
reliability score (src/clean/reliability.py).
"""

import numpy as np
import pandas as pd


def impossible_value(v: pd.Series) -> pd.Series:
    """Concentrations must be positive."""
    return v <= 0


def detect_ceilings(
    values: pd.Series,
    counts: pd.Series,
    min_value: float,
    excess: float,
    window: float,
    stations: pd.Series | None = None,
    min_stations: int = 1,
    min_count: int = 0,
) -> list[float]:
    """Instrument ceilings from a histogram of exact values: a value >= min_value that occurs more
    than `excess` times as often as the median count of the other distinct values within +-window
    that have the same precision (whole numbers, 1 decimal, 2 decimals). Precision matters: many
    analysers report whole numbers, so any integer is far more common than a 2-decimal value.
    An instrument ceiling is a network-wide pin, so it must also occur at >= min_stations stations
    and >= min_count times; a value stuck at one station is the flatline rule's job.
    `values`/`counts`/`stations`: one row per distinct value, network-wide."""
    st = stations.to_numpy() if stations is not None else np.full(len(values), min_stations)
    h = (
        pd.DataFrame({"v": values.to_numpy(), "n": counts.to_numpy(), "st": st})
        .sort_values("v")
        .reset_index(drop=True)
    )
    cents = np.round(h.v * 100).astype("int64")
    h["prec"] = np.where(cents % 100 == 0, 0, np.where(cents % 10 == 0, 1, 2))
    out = []
    for i in h.index[(h.v >= min_value) & (h.st >= min_stations) & (h.n >= min_count)]:
        v = h.v[i]
        near = h[(h.v >= v - window) & (h.v <= v + window) & (h.index != i) & (h.prec == h.prec[i])]
        base = near.n.median() if len(near) else 0
        if base > 0 and h.n[i] > excess * base:
            out.append(float(v))
    return out


def ceiling_pin(v: pd.Series, ceilings: list[float], tol: float = 0.005) -> pd.Series:
    """Value sits on a detected instrument ceiling."""
    if not ceilings:
        return pd.Series(False, index=v.index)
    return (
        np.isclose(v.to_numpy()[:, None], np.asarray(ceilings)[None, :], atol=tol, rtol=0).any(
            axis=1
        )
        & v.notna()
    )


def pm25_exceeds_pm10(
    pm25: pd.Series, pm10: pd.Series, abs_tol: float, rel_tol: float
) -> pd.Series:
    """PM2.5 is part of PM10, so PM2.5 > PM10 at the same station-hour means one instrument is wrong.
    Small excesses are within the two analysers' separate measurement noise, hence the tolerance.
    Both pollutants are flagged for that hour (which one is wrong is unknown)."""
    return (pm25 - pm10 > np.maximum(abs_tol, rel_tol * pm10)) & pm25.notna() & pm10.notna()


def flatline(v: pd.Series, hours: pd.Series, min_hours: int) -> pd.Series:
    """Runs of identical values in consecutive hours lasting >= min_hours. `hours` are the hour
    stamps (sorted, one station); a gap in time breaks a run. Returns True for every hour in a run."""
    t = pd.to_datetime(hours).reset_index(drop=True)
    x = v.reset_index(drop=True)
    new_run = (x != x.shift()) | (t - t.shift() != pd.Timedelta(hours=1)) | x.isna()
    run_id = new_run.cumsum()
    length = run_id.map(run_id.value_counts())
    return pd.Series(((length >= min_hours) & x.notna()).to_numpy(), index=v.index)

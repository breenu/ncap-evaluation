"""Level shifts / recalibrations (proposal stage 3): changepoints in each station's series, DEC-072.

Series: the weekly mean of the daily neighbour residual r = log(station) - log(neighbour median)
(src/clean/spatial.py). Removing the neighbours removes weather and season, which move a whole
airshed, so a lasting step in r is the station changing relative to its surroundings: a
recalibration, an instrument swap or a move. A real local change (e.g. a new road next to the
monitor) also shows up; the audit cannot tell the two apart and says so.
Stations without two neighbours: the weekly mean of log PM minus the station's own seasonal cycle
(three annual harmonics); such changepoints can also be regional changes and are marked
reference = 'own_season'.

Detection: PELT (ruptures), L2 cost on the series scaled by its robust spread (1.4826 x MAD), minimum
segment 26 weeks (a shift that matters for annual means lasts months), at least 52 weeks of data. A
changepoint counts only if |mean after - mean before| >= flags.changepoint_min_shift (log units;
0.223 = a 25% step).

Penalty, calibrated against a null (not chosen by eye): each series is shuffled in 4-week blocks,
which keeps its short-range autocorrelation but destroys any lasting level shift. For each reference
type, the penalty is the smallest value on flags.changepoint_penalty_grid (x log n) at which at most
flags.changepoint_false_alarm of the shuffled series show a changepoint. A first version scaled by
week-to-week differences, which understates the spread of autocorrelated series, and found ~11 shifts
per station; it was replaced before use (DEC-078).

Outputs: data/interim/audit/changepoints.csv  sid, pollutant, date, shift_log, shift_pct, reference
         data/interim/audit/changepoint_calibration.csv

    python -m src.clean.changepoints
"""

import numpy as np
import pandas as pd
import ruptures as rpt

from src.clean.spatial import AUDIT, PM, valid_hours
from src.common.paths import PROCESSED, params

MIN_SEG_WEEKS = 26
MIN_WEEKS = 52
BLOCK_WEEKS = 4
NULL_REPS = 2
JUMP = 2  # candidate break every 2 weeks: dates to +-2 weeks, ample for flagging station-years


def weekly(s: pd.Series) -> pd.Series:
    """Daily series (DatetimeIndex) -> weekly means, weeks with >= 4 days only."""
    w = s.resample("W").agg(["mean", "count"])
    return w["mean"][w["count"] >= 4]


def deseasonalise(logv: pd.Series) -> pd.Series:
    """Remove three annual harmonics fitted by least squares."""
    t = logv.index.dayofyear.to_numpy() / 365.25 * 2 * np.pi
    X = np.column_stack([np.ones_like(t)] + [f(k * t) for k in (1, 2, 3) for f in (np.sin, np.cos)])
    beta, *_ = np.linalg.lstsq(X, logv.to_numpy(), rcond=None)
    return logv - X @ beta


def _breaks(v: np.ndarray, penalty: float) -> list[int]:
    s = np.median(np.abs(v - np.median(v))) * 1.4826
    if not s > 0:
        return []
    z = (v - v.mean()) / s
    return (
        rpt.Pelt(model="l2", min_size=MIN_SEG_WEEKS, jump=JUMP)
        .fit(z)
        .predict(pen=penalty * np.log(len(v)))
    )


def detect(series: pd.Series, penalty: float, min_shift: float) -> list[dict]:
    """Changepoints in one weekly series. Returns [{date, shift_log}] for shifts >= min_shift."""
    x = series.dropna()
    if len(x) < MIN_WEEKS:
        return []
    v = x.to_numpy()
    bkps = _breaks(v, penalty)
    out = []
    edges = [0, *bkps]
    for i, b in enumerate(bkps[:-1]):
        shift = v[b : edges[i + 2]].mean() - v[edges[i] : b].mean()
        if abs(shift) >= min_shift:
            out.append({"date": x.index[b], "shift_log": float(shift)})
    return out


def block_shuffle(v: np.ndarray, rng: np.random.Generator, k: int = BLOCK_WEEKS) -> np.ndarray:
    blocks = [v[i : i + k] for i in range(0, len(v), k)]
    order = rng.permutation(len(blocks))
    return np.concatenate([blocks[i] for i in order])


def calibrate(series: list[pd.Series], grid: list[float], target: float, min_shift: float,
              rng: np.random.Generator) -> tuple[float, pd.DataFrame]:  # fmt: skip
    """Smallest penalty on the grid whose false-alarm rate on block-shuffled series is <= target."""
    vs = [s.dropna().to_numpy() for s in series]
    vs = [v for v in vs if len(v) >= MIN_WEEKS]
    rows = []
    for pen in grid:
        null = [
            bool(
                detect(
                    pd.Series(block_shuffle(v, rng), index=pd.RangeIndex(len(v))), pen, min_shift
                )
            )
            for v in vs
            for _ in range(NULL_REPS)
        ]
        real = [bool(detect(pd.Series(v, index=pd.RangeIndex(len(v))), pen, min_shift)) for v in vs]
        rows.append({"penalty": pen, "null_false_alarm": np.mean(null), "real_share_with_shift": np.mean(real),
                     "series": len(vs)})  # fmt: skip
    t = pd.DataFrame(rows)
    ok = t[t.null_false_alarm <= target]
    return (float(ok.penalty.min()) if len(ok) else float(max(grid))), t


def main() -> None:
    fc = params()["flags"]
    rng = np.random.default_rng(params()["seed"])
    day = pd.read_parquet(PROCESSED / "station_day.parquet")
    ref = pd.read_parquet(AUDIT / "neighbour_ref.parquet")
    series = {"neighbours": {}, "own_season": {}}
    for p in PM:
        r = ref[ref.pollutant == p]
        with_nb = set(r.sid)
        for sid, g in r.groupby("sid"):
            series["neighbours"][(sid, p)] = weekly(
                g.set_index(pd.to_datetime(g.date_ist)).resid.sort_index()
            )
        d = day[(day[f"{p}_h1"] >= valid_hours()) & ~day.sid.isin(with_nb) & (day[p] > 0)]
        for sid, g in d.groupby("sid"):
            logv = np.log(g.set_index(pd.to_datetime(g.date_ist))[p].sort_index())
            if len(logv) >= MIN_WEEKS * 4:
                series["own_season"][(sid, p)] = weekly(deseasonalise(logv))
    rows, cal = [], []
    for kind, ss in series.items():
        pen, t = calibrate(list(ss.values()), fc["changepoint_penalty_grid"], fc["changepoint_false_alarm"],
                           fc["changepoint_min_shift"], rng)  # fmt: skip
        cal.append(t.assign(reference=kind, chosen=t.penalty == pen))
        for (sid, p), s in ss.items():
            rows += [{**c, "sid": sid, "pollutant": p, "reference": kind, "penalty": pen}
                     for c in detect(s, pen, fc["changepoint_min_shift"])]  # fmt: skip
    pd.concat(cal, ignore_index=True).to_csv(AUDIT / "changepoint_calibration.csv", index=False)
    out = pd.DataFrame(
        rows, columns=["sid", "pollutant", "date", "shift_log", "reference", "penalty"]
    )
    out["shift_pct"] = 100 * (np.exp(out.shift_log) - 1)
    out.to_csv(AUDIT / "changepoints.csv", index=False)
    print(pd.concat(cal).to_string(index=False))
    print(out.groupby(["pollutant", "reference"]).size())


if __name__ == "__main__":
    main()

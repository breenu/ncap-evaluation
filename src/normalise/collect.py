"""Metrics and deweathered series from saved predictions, identical for both families (Phase 5).

Per task (station x pollutant x family), on the log scale the models were fitted on:
    r2_oos     1 - sum (y - cv_pred)^2 / sum (y - mean y)^2, pooled over every forward-chaining test
               day (all folds together, around the mean of those days). The registered selection
               metric is the median of this over series (DEC-088).
    rmse_oos   root mean squared out-of-sample error
    r2_in      the same for the final model's in-sample fitted values
    acf_oos_k  lag-k autocorrelation (k = 1..7) of out-of-sample residuals: the Pearson correlation
               of residual pairs exactly k days apart within the same test year (gaps are skipped,
               never bridged)
    acf_in_k   the same for in-sample residuals
    smear      Duan's smearing factor mean(exp(y - fitted)): exp of a mean log prediction estimates
               the median, not the mean, so deweathered values are multiplied by it to put them on
               the same scale as observed daily means. It is a constant per series, so it never
               changes a series' relative (%) changes.
"""

import json

import numpy as np
import pandas as pd

from src.normalise.features import series_dir
from src.normalise.store import task_paths

LAGS = range(1, 8)


def r2(y: np.ndarray, pred: np.ndarray) -> float:
    ok = ~(np.isnan(y) | np.isnan(pred))
    y, pred = y[ok], pred[ok]
    if len(y) < 2:
        return np.nan
    return 1 - np.sum((y - pred) ** 2) / np.sum((y - y.mean()) ** 2)


def acf_pairs(resid: pd.Series, dates: pd.Series, group: pd.Series, lag: int) -> float:
    """Correlation of residuals exactly `lag` days apart, within the same group; NaN residuals
    (and pairs across a gap or a group boundary) are skipped."""
    s = pd.DataFrame({"e": resid.to_numpy(), "d": pd.to_datetime(dates).to_numpy(), "g": group.to_numpy()})
    s = s.dropna(subset=["e"])
    later = s.assign(d=s.d - pd.Timedelta(days=lag))
    j = s.merge(later, on=["d", "g"], suffixes=("", "_k"))
    if len(j) < 30:
        return np.nan
    return float(np.corrcoef(j.e, j.e_k)[0, 1])


def load(run: str, family: str, pollutant: str, sid: str) -> tuple[pd.DataFrame, dict]:
    pq, js = task_paths(run, family, pollutant, sid)
    out = pd.read_parquet(pq)
    target = pd.read_parquet(series_dir(run, pollutant, sid) / "target.parquet", columns=["date"])
    if len(out) != len(target):
        raise ValueError(f"{family} {pollutant} {sid}: {len(out)} rows vs {len(target)} targets")
    out.insert(0, "date", target.date.to_numpy())
    return out, json.loads(js.read_text(encoding="utf-8"))


def metrics(out: pd.DataFrame) -> dict:
    fit = out[out.y.notna()]
    test = fit[fit.cv_fold > 0]
    m = {
        "n_fit": len(fit),
        "n_test": len(test),
        "r2_oos": r2(test.y.to_numpy(), test.cv_pred.to_numpy()),
        "rmse_oos": float(np.sqrt(np.mean((test.y - test.cv_pred) ** 2))) if len(test) else np.nan,
        "r2_in": r2(fit.y.to_numpy(), fit.fitted.to_numpy()),
        "smear": float(np.mean(np.exp(fit.y - fit.fitted))),
    }
    for k in LAGS:
        m[f"acf_oos_{k}"] = acf_pairs(test.y - test.cv_pred, test.date, test.cv_fold, k)
        m[f"acf_in_{k}"] = acf_pairs(fit.y - fit.fitted, fit.date, pd.Series(0, index=fit.index), k)
    return m


def deweathered(out: pd.DataFrame, smear: float) -> pd.DataFrame:
    """Observed and deweathered daily values in µg/m³: every dw_* column times the smearing factor."""
    d = out[["date"]].copy()
    d["obs"] = np.exp(out.y)
    for c in out.columns:
        if c.startswith("dw_"):
            d[c] = out[c] * smear
        elif c.startswith("sd_"):
            d[c] = out[c] * smear
    return d

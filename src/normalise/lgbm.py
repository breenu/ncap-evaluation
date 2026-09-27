"""LightGBM deweathering model, one station x pollutant per task (Phase 5, DEC-101).

log(PM) = f(temp, rh, ws, wd, blh_mean, blh_pm, precip, ssrd, doy, weekday, trend), fixed
hyperparameters from config (not tuned per station), one thread per model so that workers run in
parallel. Steps for a task, all from the input folder written by src.normalise.features:
    1. blocked forward-chaining CV: for each test year Y, train on years < Y, predict year Y with
       the trend clamped at the last training day (the model cannot see the future level)
    2. final model on all fit days; in-sample fitted values
    3. weather resampling (src.normalise.resample) for every target day, for each scheme
Metrics (R2, residual autocorrelation) and the smearing factor are computed later from the saved
predictions, by the same code for both families (src.normalise.collect).
"""

import time

import lightgbm as lgb
import numpy as np
import pandas as pd

from src.common.paths import params
from src.normalise.features import cfg, series_dir
from src.normalise.resample import MODEL_COLUMNS, normalise
from src.normalise.store import (
    cvcheck_path,
    model_path,
    task_paths,
    write_atomic_json,
    write_atomic_parquet,
)

FAMILY = "lgbm"


def make_model() -> lgb.LGBMRegressor:
    return lgb.LGBMRegressor(
        **cfg()["lgbm"], n_jobs=1, random_state=params()["seed"], deterministic=True,
        force_row_wise=True, verbose=-1,
    )  # fmt: skip


def clamp_trend(x: pd.DataFrame, lo: float, hi: float) -> pd.DataFrame:
    return x.assign(trend=x.trend.clip(lo, hi))


def test_trend(x: pd.DataFrame, train_trend: pd.Series, convention: str) -> pd.DataFrame:
    """The trend a model sees for an unseen test year (DEC-107). last_year: the same calendar day
    one year earlier, kept inside the training range; clamp: the last training day's value."""
    lo, hi = train_trend.min(), train_trend.max()
    if convention == "last_year":
        return clamp_trend(x.assign(trend=x.trend - 1.0), lo, hi)
    if convention == "clamp":
        return clamp_trend(x, -np.inf, hi)
    raise ValueError(f"unknown cv_trend {convention!r}")


def cv_predict(
    fit: pd.DataFrame, folds: list[int], make=make_model, convention: str | None = None
) -> tuple[np.ndarray, np.ndarray]:
    """Out-of-sample log predictions and the fold (test year) of every fit day; NaN / 0 outside."""
    convention = convention or cfg()["cv_trend"]
    pred = np.full(len(fit), np.nan)
    fold = np.zeros(len(fit), dtype="int16")
    for y in folds:
        tr, te = (fit.year < y).to_numpy(), (fit.year == y).to_numpy()
        m = make().fit(fit.loc[tr, MODEL_COLUMNS], fit.y[tr])
        pred[te] = m.predict(test_trend(fit.loc[te, MODEL_COLUMNS], fit.trend[tr], convention))
        fold[te] = y
    return pred, fold


def cv_only(run: str, pollutant: str, sid: str, convention: str) -> None:
    """CV predictions alone (no resampling), for comparing trend conventions in the pilot."""
    d = series_dir(run, pollutant, sid)
    fit = pd.read_parquet(d / "fit.parquet")
    folds = pd.read_parquet(d / "folds.parquet").year.astype(int).tolist()
    pred, fold = cv_predict(fit, folds, convention=convention)
    n = len(pd.read_parquet(d / "target.parquet", columns=["date"]))
    out = pd.DataFrame({"cv_pred": np.nan, "cv_fold": 0}, index=range(n))
    out.loc[fit.t_row.to_numpy(), "cv_pred"] = pred
    out.loc[fit.t_row.to_numpy(), "cv_fold"] = fold
    write_atomic_parquet(out, cvcheck_path(run, FAMILY, convention, pollutant, sid))


def run_task(run: str, pollutant: str, sid: str, schemes: list[str], checkpoints: list[int]) -> None:
    d = series_dir(run, pollutant, sid)
    fit = pd.read_parquet(d / "fit.parquet")
    target = pd.read_parquet(d / "target.parquet")
    pool = pd.read_parquet(d / "pool.parquet")
    folds = pd.read_parquet(d / "folds.parquet").year.astype(int).tolist()
    t0 = time.perf_counter()
    cv_pred, cv_fold = cv_predict(fit, folds)
    t1 = time.perf_counter()
    model = make_model().fit(fit[MODEL_COLUMNS], fit.y)
    fitted = model.predict(fit[MODEL_COLUMNS])
    t2 = time.perf_counter()
    tgt = clamp_trend(target, fit.trend.min(), fit.trend.max())
    dws = []
    for scheme in schemes:
        idx = pd.read_parquet(d / f"idx_{scheme}.parquet").idx.to_numpy()
        idx = idx.reshape(len(target), -1)
        dws.append(normalise(model.predict, tgt, pool, idx, scheme, checkpoints))
    t3 = time.perf_counter()

    out = pd.concat(dws, axis=1)
    for col, v in {"y": fit.y, "fitted": fitted, "cv_pred": cv_pred}.items():
        out[col] = np.nan
        out.loc[fit.t_row.to_numpy(), col] = np.asarray(v)
    out["cv_fold"] = 0
    out.loc[fit.t_row.to_numpy(), "cv_fold"] = cv_fold
    pq, js = task_paths(run, FAMILY, pollutant, sid)
    write_atomic_parquet(out, pq)
    if run == "main":
        mp = model_path(FAMILY, pollutant, sid, "txt")
        mp.parent.mkdir(parents=True, exist_ok=True)
        model.booster_.save_model(str(mp))
    write_atomic_json(
        {"sid": sid, "pollutant": pollutant, "family": FAMILY, "n_fit": len(fit),
         "n_target": len(target), "folds": folds, "draws": max(checkpoints), "schemes": schemes,
         "secs_cv": t1 - t0, "secs_fit": t2 - t1, "secs_normalise": t3 - t2,
         "secs_total": t3 - t0},
        js,
    )  # fmt: skip

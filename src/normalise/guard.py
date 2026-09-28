"""Extrapolation guard for the resampled predictions (Phase 5, DEC-117). Nothing is dropped.

For every series and resampling scheme, over all target days x draws:
    rows          resampled prediction rows (target days x N draws)
    oor_rows      rows with any weather input outside the range that series' model was trained on
                  (min-max of the fit days). Wind direction is left out: it enters as a cyclic
                  smooth / tree split on a closed circle, so there is nothing to extrapolate.
    oos_rows      rows pairing the day with a day of year more than `resample_window_days` away (an
                  out-of-season pairing; zero by construction under the seasonal scheme)
Both depend only on the training data and the draws, which every family shares, so they are the
same for every family. What differs is how a family behaves on those rows: a GAM's smooths
extrapolate, a tree ensemble cannot. The station-year ratio flags in src.normalise.aggregate show
the result.

    python -m src.normalise.guard   -> data/processed/deweathered/extrapolation.parquet
"""

import numpy as np
import pandas as pd

from src.normalise.era5_daily import FEATURES
from src.normalise.features import INPUTS, cfg, doy_distance, series_dir

GUARDED = [f for f in FEATURES if f != "wd"]


def series_guard(run: str, pollutant: str, sid: str, schemes: list[str], window: int) -> pd.DataFrame:
    d = series_dir(run, pollutant, sid)
    fit = pd.read_parquet(d / "fit.parquet", columns=GUARDED)
    target = pd.read_parquet(d / "target.parquet", columns=["date", "doy"])
    pool = pd.read_parquet(d / "pool.parquet", columns=[*GUARDED, "doy"])
    lo, hi = fit.min(), fit.max()
    pool_oor = ((pool[GUARDED] < lo) | (pool[GUARDED] > hi)).any(axis=1).to_numpy()
    rows = []
    for scheme in schemes:
        idx = pd.read_parquet(d / f"idx_{scheme}.parquet").idx.to_numpy().reshape(len(target), -1)
        oor = pool_oor[idx].sum(axis=1)
        oos = (doy_distance(pool.doy.to_numpy()[idx], target.doy.to_numpy()[:, None]) > window).sum(axis=1)
        y = pd.DataFrame({"year": target.date.dt.year, "rows": idx.shape[1], "oor_rows": oor, "oos_rows": oos})
        rows.append(y.groupby("year").sum().reset_index().assign(scheme=scheme))
    return pd.concat(rows).assign(sid=sid, pollutant=pollutant, run=run)


def main() -> None:
    from src.normalise.run import settings

    c = cfg()
    out = []
    for run in ("main", "registered"):
        _, schemes, _ = settings(run)
        s = pd.read_csv(INPUTS / run / "series.csv")
        if "skipped" in s:
            s = s[s.skipped.isna()]
        for r in s.itertuples():
            out.append(series_guard(run, r.pollutant, r.sid, schemes, c["resample_window_days"]))
    g = pd.concat(out, ignore_index=True)
    dest = INPUTS.parents[2] / "processed" / "deweathered" / "extrapolation.parquet"
    dest.parent.mkdir(parents=True, exist_ok=True)
    g.to_parquet(dest, index=False)
    t = g[g.run == "main"].groupby("scheme")[["rows", "oor_rows", "oos_rows"]].sum()
    print(t.assign(oor_share=t.oor_rows / t.rows, oos_share=t.oos_rows / t.rows))


if __name__ == "__main__":
    main()

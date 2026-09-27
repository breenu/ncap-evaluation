"""Grange & Carslaw weather resampling, vectorised (Phase 5; proposal stage 5; DEC-102).

For each target day t and draw k, the model predicts log PM with the day's own trend (and, in the
seasonal scheme, its own day of year and weekday) and the weather of pool day idx[t, k]. The
deweathered value of day t is the mean over draws of exp(prediction): the concentration expected on
that day under the station's typical weather for that time of year. All draws of a chunk are
predicted in one call. src/normalise/gam.R implements the same steps in R, from the same idx file.

The retransformation (smearing) factor is applied later, in src/normalise/collect.py, identically
for both families.
"""

from collections.abc import Callable

import numpy as np
import pandas as pd

from src.normalise.era5_daily import FEATURES

CHUNK = 50  # draws per prediction call; divides every value of the convergence grid
MODEL_COLUMNS = [*FEATURES, "doy", "weekday", "trend"]


def design(
    target: pd.DataFrame, pool: pd.DataFrame, idx: np.ndarray, scheme: str
) -> pd.DataFrame:
    """Rows t * m + j (target-major) for idx of shape (T, m)."""
    t, m = idx.shape
    flat = idx.ravel()
    x = pool[FEATURES].to_numpy()[flat]
    out = pd.DataFrame(x, columns=FEATURES)
    if scheme == "seasonal":
        out["doy"] = np.repeat(target.doy.to_numpy(), m)
        out["weekday"] = np.repeat(target.weekday.to_numpy(), m)
    elif scheme == "annual":
        out["doy"] = pool.doy.to_numpy()[flat]
        out["weekday"] = pool.weekday.to_numpy()[flat]
    else:
        raise ValueError(scheme)
    out["trend"] = np.repeat(target.trend.to_numpy(), m)
    return out[MODEL_COLUMNS]


def normalise(
    predict: Callable[[pd.DataFrame], np.ndarray],
    target: pd.DataFrame,
    pool: pd.DataFrame,
    idx: np.ndarray,
    scheme: str,
    checkpoints: list[int],
) -> pd.DataFrame:
    """Mean of exp(prediction) over the first N draws, for every N in checkpoints (each a multiple
    of CHUNK and <= idx.shape[1]); also the draws' standard deviation at the largest N."""
    n = max(checkpoints)
    if n > idx.shape[1] or any(c % CHUNK for c in checkpoints):
        raise ValueError(f"checkpoints {checkpoints} vs {idx.shape[1]} draws, chunk {CHUNK}")
    s1 = np.zeros(len(target))
    s2 = np.zeros(len(target))
    out = {}
    for k0 in range(0, n, CHUNK):
        sub = idx[:, k0 : k0 + CHUNK]
        p = np.exp(predict(design(target, pool, sub, scheme))).reshape(sub.shape)
        s1 += p.sum(axis=1)
        s2 += (p**2).sum(axis=1)
        k = k0 + CHUNK
        if k in checkpoints:
            out[f"dw_{scheme}_n{k}"] = s1 / k
    out[f"sd_{scheme}"] = np.sqrt(np.maximum(s2 / n - (s1 / n) ** 2, 0) * n / (n - 1))
    return pd.DataFrame(out, index=target.index)

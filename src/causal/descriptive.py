"""Descriptive context for Layer A (Reenu, DEC-154 item 2). DESCRIPTIVE ONLY: no effect is computed here.

Mean annual population-weighted PM2.5 (ACAG V5.GL.06, µg/m³) of the NCAP units (the 113 treated
units) and of the control pool (923 units), 2010-2024, 2020 included: the unweighted mean over units with
a 95% t-interval, and the median. GATED (it shows NCAP and non-NCAP units after 2018).

    python -m src.causal.descriptive    -> data/processed/causal/levels.csv
"""

import numpy as np
import pandas as pd
from scipy import stats

from src.causal import layer_a as A
from src.common.gate import require_gate

GROUP = {"treated": "NCAP units", "control": "control pool"}


def levels(pan: pd.DataFrame, units: pd.DataFrame) -> pd.DataFrame:
    """Per year and group: n, mean, 95% t-interval, median of the unit values."""
    d = pan.merge(units, on="unit_id")
    rows = []
    for (y, g), x in d.groupby(["year", "role_a"]):
        v = x.value.to_numpy(float)
        h = stats.t.ppf(0.975, len(v) - 1) * v.std(ddof=1) / np.sqrt(len(v))
        rows.append({"year": int(y), "group": GROUP[g], "n": len(v), "mean": v.mean(), "lo95": v.mean() - h,
                     "hi95": v.mean() + h, "median": float(np.median(v))})  # fmt: skip
    return pd.DataFrame(rows)


def main() -> None:
    require_gate("Descriptive post-2018 levels of NCAP and control units")
    u = pd.read_csv(A.OUT / "design_units.csv")
    u = u[u.role_a.isin(["treated", "control"])][["unit_id", "role_a"]]
    pan = pd.read_parquet(A.OUT / "panel_annual.parquet")
    pan = pan[pan.series == "popw_V5GL06"]
    out = levels(pan, u)
    if set(out.groupby("group").n.unique().explode()) != {113, 923}:
        raise ValueError("unexpected unit counts in the descriptive table")
    out.to_csv(A.OUT / "levels.csv", index=False)


if __name__ == "__main__":
    main()

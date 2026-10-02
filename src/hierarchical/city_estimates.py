"""City-level estimates for the hierarchical model: one SDID per treated unit, standard errors from
single-unit placebo fits over every control, the registered moderators (Phase 8, RQ4; DEC-162, DEC-163).
GATED (hard rule 4): uses post-2019 outcomes.

H1 is not identified (DEC-151), so a unit's estimate is a **city-level relative change** (its satellite
PM2.5 after listing relative to its synthetic comparison), never an effect of NCAP.

    python -m src.hierarchical.city_estimates run         Rscript src/hierarchical/unit_sdid.R (~10 min)
    python -m src.hierarchical.city_estimates table       -> data/processed/hierarchical/city_estimates.csv
"""

import os
import subprocess
import sys

import numpy as np
import pandas as pd

from src.causal import layer_a as A
from src.common.gate import require_gate
from src.common.paths import INTERIM, PROCESSED

OUT = PROCESSED / "hierarchical"
SERIES = ("popw_V5GL06", "popw_V6GL03")  # primary; rule (d)'s product for H5's sensitivity (DEC-162)
MODERATORS = ["baseline_pm25", "igp", "log_pop", "coastal", "xvfc"]  # DEC-163, registered order


def run(series: tuple[str, ...] = SERIES) -> None:
    require_gate("per-unit SDID (post-2019 satellite outcomes)")
    env = {**os.environ, "OMP_NUM_THREADS": "1", "OPENBLAS_NUM_THREADS": "1", "MKL_NUM_THREADS": "1"}
    subprocess.run(["Rscript", "src/hierarchical/unit_sdid.R", *series], env=env, check=True)


def placebo_p(est: float, null: np.ndarray) -> float:
    """Equal-tailed empirical p of `est` against a placebo distribution (as DEC-091)."""
    n = len(null)
    lo = (1 + np.sum(null <= est)) / (n + 1)
    hi = (1 + np.sum(null >= est)) / (n + 1)
    return float(min(1.0, 2 * min(lo, hi)))


def bh_reject(p: np.ndarray, q: float = 0.05) -> np.ndarray:
    """Benjamini-Hochberg step-up at level q: boolean array of rejections."""
    p = np.asarray(p, float)
    m = len(p)
    order = np.argsort(p)
    passed = p[order] <= q * np.arange(1, m + 1) / m
    k = np.max(np.nonzero(passed)[0]) + 1 if passed.any() else 0
    rej = np.zeros(m, bool)
    rej[order[:k]] = True
    return rej


def unit_estimates(fits: pd.DataFrame) -> pd.DataFrame:
    """Per treated unit: estimate, cohort placebo SE (primary), pre-fit-scaled SE (sensitivity), placebo p.
    `fits`: rows of unit_sdid.R (kind real/placebo, unit_id, cohort, att, prefit_sd)."""
    real = fits[fits.kind == "real"].copy()
    plac = fits[fits.kind == "placebo"]
    rows = []
    for g, pg in plac.groupby("cohort"):
        s_g = float(pg.att.std(ddof=1))
        z = pg.att / pg.prefit_sd
        s_std = float(z.std(ddof=1))
        r = real[real.cohort == g]
        for x in r.itertuples():
            rows.append({"unit_id": x.unit_id, "cohort": int(g), "est": x.att, "se": s_g,
                         "se_scaled": s_std * x.prefit_sd, "prefit_sd": x.prefit_sd,
                         "p_placebo": placebo_p(x.att, pg.att.to_numpy()), "n_placebo": len(pg),
                         "placebo_mean": float(pg.att.mean()), "warnings": x.warnings})  # fmt: skip
    out = pd.DataFrame(rows)
    out["bh_reject"] = bh_reject(out.p_placebo.to_numpy())
    return out


def moderators(units: pd.DataFrame, panel: pd.DataFrame, cities: pd.DataFrame) -> pd.DataFrame:
    """The registered moderators (DEC-163) for the treated units. Continuous ones standardised over them.
    `units`: design_units rows (unit_id, region, pop_2015, ncap_cities); `panel`: Phase 7 annual panel."""
    t = units[["unit_id", "ncap_cities", "region", "pop_2015"]].copy()
    p = panel[(panel.series == "popw_V5GL06") & panel.year.between(2010, 2018) & panel.unit_id.isin(t.unit_id)]
    base = np.log(p.value).groupby(p.unit_id).mean().rename("baseline_log_pm25")
    t = t.merge(base, left_on="unit_id", right_index=True, how="left")
    chan = dict(zip(cities.city, cities.channel, strict=True))
    members = t.ncap_cities.fillna("").str.split(";")
    t["xvfc"] = members.map(lambda m: int(any(chan.get(c) == "XVFC" for c in m))).astype(int)
    t["igp"] = (t.region == "igp").astype(int)
    t["coastal"] = (t.region == "coastal").astype(int)
    t["log_pop_raw"] = np.log(t.pop_2015)
    std = lambda s: (s - s.mean()) / s.std(ddof=1)  # noqa: E731
    t["baseline_pm25"] = std(t.baseline_log_pm25)
    t["log_pop"] = std(t.log_pop_raw)
    return t


def table() -> pd.DataFrame:
    require_gate("city-level estimates table")
    u = pd.read_csv(A.OUT / "design_units.csv")
    tr = u[u.role_a == "treated"]
    panel = pd.read_parquet(A.OUT / "panel_annual.parquet")
    cities = pd.read_csv(INTERIM / "ncap_cities.csv")
    mods = moderators(tr, panel, cities)
    est = unit_estimates(pd.read_parquet(OUT / f"unit_sdid_{SERIES[0]}.parquet"))
    alt = unit_estimates(pd.read_parquet(OUT / f"unit_sdid_{SERIES[1]}.parquet"))
    alt = alt[["unit_id", "est", "se", "se_scaled"]].rename(columns=lambda c: c if c == "unit_id" else f"{c}_{SERIES[1]}")
    est = est.merge(alt, on="unit_id", validate="one_to_one")
    out = mods.merge(est, on="unit_id", validate="one_to_one")
    if len(out) != len(tr):
        raise ValueError("a treated unit has no per-unit estimate")
    OUT.mkdir(parents=True, exist_ok=True)
    out.to_csv(OUT / "city_estimates.csv", index=False)
    # placebo summaries per cohort and series (for the report)
    rows = []
    for s in SERIES:
        f = pd.read_parquet(OUT / f"unit_sdid_{s}.parquet")
        for (k, g), d in f.groupby(["kind", "cohort"]):
            rows.append({"series": s, "kind": k, "cohort": int(g), "n": len(d), "mean": d.att.mean(), "sd": d.att.std(ddof=1),
                         "prefit_sd_median": d.prefit_sd.median(), "warnings": int(d.warnings.sum())})  # fmt: skip
    pd.DataFrame(rows).to_csv(OUT / "unit_sdid_summary.csv", index=False)
    return out


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "table"
    {"run": run, "table": table}[cmd]()

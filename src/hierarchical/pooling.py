"""Bayesian hierarchical (measurement-error) model of the city-level estimates, and H5 (Phase 8, RQ4;
plan §5 item 5; DEC-163, DEC-164). GATED (hard rule 4).

    est_i ~ Normal(theta_i, se_i^2)            se_i known (DEC-162)
    theta_i = alpha + x_i' beta + tau * z_i,   z_i ~ Normal(0, 1)   (non-centred)

H1 is not identified (DEC-151): theta_i is a **shrunken city-level relative change**, not an effect of NCAP,
and H5's IGP coefficient is a difference in city-level relative changes, not in NCAP effects.

    python -m src.hierarchical.pooling     -> data/processed/hierarchical/pool_*.csv, city_shrunken.csv, h5.json
"""

import json

import numpy as np
import pandas as pd

from src.common.gate import require_gate
from src.common.paths import params
from src.hierarchical.city_estimates import MODERATORS, OUT

PRIORS = {"alpha": 0.1, "beta": 0.05, "tau": 0.05}  # DEC-163 (log scale)
WIDE = 5.0  # prior sensitivity: every scale x 5
RHAT_MAX, ESS_MIN = 1.01, 400  # convergence rule (DEC-163)


def hcfg() -> dict:
    return params()["hierarchical"]


def fit(y, s, X, scale: float = 1.0, draws: int = 2000, tune: int = 2000, target_accept: float = 0.95,
        chains: int = 4, seed: int | None = None, cores: int = 4):  # fmt: skip
    """Sample the measurement-error model. X: (n, k) array or None (intercept-only)."""
    import pymc as pm

    y, s = np.asarray(y, float), np.asarray(s, float)
    n = len(y)
    with pm.Model():
        alpha = pm.Normal("alpha", 0.0, PRIORS["alpha"] * scale)
        mu = alpha
        if X is not None:
            X = np.asarray(X, float)
            beta = pm.Normal("beta", 0.0, PRIORS["beta"] * scale, shape=X.shape[1])
            mu = alpha + pm.math.dot(X, beta)
        tau = pm.HalfNormal("tau", PRIORS["tau"] * scale)
        z = pm.Normal("z", 0.0, 1.0, shape=n)
        theta = pm.Deterministic("theta", mu + tau * z)
        pm.Normal("obs", theta, s, observed=y)
        return pm.sample(draws, tune=tune, chains=chains, cores=cores, target_accept=target_accept,
                         random_seed=seed, progressbar=False)  # fmt: skip


def diagnostics(idata, has_beta: bool) -> dict:
    import arviz as az

    names = ["alpha", "tau", "theta"] + (["beta"] if has_beta else [])
    d = az.summary(idata, var_names=names, kind="diagnostics")
    div = int(np.asarray(idata.sample_stats["diverging"]).sum())
    out = {"rhat_max": float(d["r_hat"].max()), "ess_bulk_min": float(d["ess_bulk"].min()),
           "ess_tail_min": float(d["ess_tail"].min()), "divergences": div}  # fmt: skip
    out["converged"] = bool(out["rhat_max"] <= RHAT_MAX and out["ess_bulk_min"] >= ESS_MIN
                            and out["ess_tail_min"] >= ESS_MIN and div == 0)  # fmt: skip
    return out


def fit_checked(y, s, X, scale: float = 1.0, seed: int | None = None) -> tuple[object, dict]:
    """DEC-163's convergence rule: one re-run (target_accept 0.99, 4,000 draws) if the first fails."""
    c = hcfg()
    idata = fit(y, s, X, scale, c["draws"], c["tune"], c["target_accept"], c["chains"], seed)
    d = diagnostics(idata, X is not None) | {"attempt": 1}
    if not d["converged"]:
        idata = fit(y, s, X, scale, c["retry_draws"], c["tune"], c["retry_target_accept"], c["chains"], seed)
        d = diagnostics(idata, X is not None) | {"attempt": 2}
    return idata, d


def draws(idata, name: str) -> np.ndarray:
    """Posterior draws stacked over chains: (samples,) or (samples, k)."""
    a = np.asarray(idata.posterior[name])
    return a.reshape(a.shape[0] * a.shape[1], *a.shape[2:])


def pct(x):
    return 100 * (np.exp(x) - 1)


def interval(x: np.ndarray, axis: int = 0) -> tuple:
    return np.quantile(x, 0.025, axis=axis), np.quantile(x, 0.975, axis=axis)


def coef_rows(idata, names: list[str] | None, version: str) -> list[dict]:
    rows = []
    params_ = [("alpha", draws(idata, "alpha"))] + [("tau", draws(idata, "tau"))]
    if names:
        b = draws(idata, "beta")
        params_ += [(f"beta[{n}]", b[:, k]) for k, n in enumerate(names)]
    params_.append(("average city-level relative change", draws(idata, "theta").mean(axis=1)))
    for p, x in params_:
        lo, hi = interval(x)
        rows.append({"version": version, "param": p, "mean": float(x.mean()), "sd": float(x.std()), "lo95": float(lo),
                     "hi95": float(hi), "p_gt0": float((x > 0).mean())})  # fmt: skip
    return rows


def city_rows(idata, e: pd.DataFrame, se_col: str) -> pd.DataFrame:
    th = draws(idata, "theta")
    lo, hi = interval(th)
    ranks = th.argsort(axis=1).argsort(axis=1) + 1  # 1 = most negative
    rlo, rhi = np.quantile(ranks, 0.025, axis=0), np.quantile(ranks, 0.975, axis=0)
    return pd.DataFrame({
        "unit_id": e.unit_id.to_numpy(), "ncap_cities": e.ncap_cities.to_numpy(), "region": e.region.to_numpy(),
        "cohort": e.cohort.to_numpy(), "est": e.est.to_numpy(), "se": e[se_col].to_numpy(),
        "post_mean": th.mean(axis=0), "post_lo95": lo, "post_hi95": hi, "p_lt0": (th < 0).mean(axis=0),
        "rank_mean": ranks.mean(axis=0), "rank_lo95": rlo, "rank_hi95": rhi})  # fmt: skip


def versions(e: pd.DataFrame) -> list[dict]:
    """The models fitted (DEC-163/164). The first decides H5."""
    v6 = "popw_V6GL03"
    return [
        {"key": "primary", "label": "Primary: five registered moderators, cohort placebo SE, V5.GL.06", "y": "est", "se": "se", "X": MODERATORS, "scale": 1.0},
        {"key": "igp_only", "label": "IGP only (IGP minus everywhere else)", "y": "est", "se": "se", "X": ["igp"], "scale": 1.0},
        {"key": "se_scaled", "label": "Pre-fit-scaled SE", "y": "est", "se": "se_scaled", "X": MODERATORS, "scale": 1.0},
        {"key": "wide_priors", "label": "Prior scales x 5", "y": "est", "se": "se", "X": MODERATORS, "scale": WIDE},
        {"key": "v6gl03", "label": "V6.GL.03 per-unit estimates", "y": f"est_{v6}", "se": f"se_{v6}", "X": MODERATORS, "scale": 1.0},
    ]  # fmt: skip


def h5_verdict(lo95: float, hi95: float) -> str:
    """DEC-164: the registered rule is met if beta_IGP's 95% CrI lies entirely above 0."""
    return "met" if lo95 > 0 else "not met"


def main() -> None:
    require_gate("hierarchical model of city-level estimates (H5)")
    e = pd.read_csv(OUT / "city_estimates.csv")
    seed = int(params()["seed"])
    coefs, diags, cities = [], [], []
    for v in versions(e):
        X = e[v["X"]].to_numpy(float) if v["X"] else None
        idata, d = fit_checked(e[v["y"]], e[v["se"]], X, v["scale"], seed)
        diags.append({"version": v["key"], "label": v["label"], **d})
        if not d["converged"]:  # DEC-163: no number from a model that did not converge
            print(v["key"], "NOT CONVERGED", d, flush=True)
            continue
        coefs += coef_rows(idata, v["X"], v["key"])
        c = city_rows(idata, e.assign(est=e[v["y"]]), v["se"]).assign(version=v["key"])
        cities.append(c)
        if v["key"] == "primary":
            np.save(OUT / "theta_draws_primary.npy", draws(idata, "theta")[::2].astype(np.float32))
        print(v["key"], d, flush=True)
    co = pd.DataFrame(coefs)
    co.to_csv(OUT / "pool_coefs.csv", index=False)
    pd.DataFrame(diags).to_csv(OUT / "pool_diagnostics.csv", index=False)
    pd.concat(cities, ignore_index=True).to_csv(OUT / "city_shrunken.csv", index=False)
    e[MODERATORS].corr().to_csv(OUT / "moderator_corr.csv")
    b = co[(co.version == "primary") & (co.param == "beta[igp]")]
    if len(b) != 1:
        raise RuntimeError("the primary model did not converge; H5 cannot be decided (DEC-163)")
    b = b.iloc[0]
    h5 = {"beta_igp": b["mean"], "lo95": b["lo95"], "hi95": b["hi95"], "p_gt0": b["p_gt0"],
          "rule_met": h5_verdict(b["lo95"], b["hi95"]) == "met", "verdict": h5_verdict(b["lo95"], b["hi95"])}  # fmt: skip
    (OUT / "h5.json").write_text(json.dumps(h5, indent=2))
    print("H5:", h5)


if __name__ == "__main__":
    main()

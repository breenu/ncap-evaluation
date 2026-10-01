"""Layer A event study: Sun & Abraham (2021) interaction-weighted estimator (plan §5 item 2; DEC-142).

    y_it = a_i + l_{region(i), t} + X_it'g + sum_e sum_{l != ref_e} d_{e,l} 1{cohort_i = e} 1{t - e = l} + u_it

on the treated units and the never-treated controls, fitted with pyfixest (unit and region x year fixed
effects, ERA5 covariates, SEs clustered by unit). Cohort-specific coefficients are aggregated over
cohorts with their shares among treated units (the interaction weights); the covariance of the
aggregated coefficients follows by the delta method with the weights held fixed.

Reference period of each cohort: its last observed pre-year (l = -1 for 2019 and 2020; l = -2 for 2021
when 2020 is dropped, since its l = -1 is 2020). Relative years outside the reporting window get their
own indicators and are not reported. GATED (hard rule 4).

    python -m src.causal.event_study         primary (2020 dropped), 2020 own-coefficient fit, Himalayan
"""

import json

import numpy as np
import pandas as pd
import pyfixest as pf
from scipy import stats

from src.causal import layer_a as A
from src.common.gate import require_gate
from src.common.paths import params

OUT = A.OUT / "event_study"
COVARS = ["t2m_c", "rh", "ws", "blh", "precip_mm", "ssrd_mj"]


def rel_name(e: int, l: int) -> str:  # noqa: E741
    return f"sa_{e}_{'m' if l < 0 else 'p'}{abs(l)}"


def sa_design(d: pd.DataFrame, own_years: tuple[int, ...] = ()) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Add cohort x relative-year indicators (and cohort x calendar-year indicators for `own_years`).

    `d`: unit_id, year, cohort (0 = never treated), ... Returns (data with indicator columns, a table of
    the indicators: name, kind ('rel' or 'own'), cohort, rel (relative year) or year)."""
    d = d.copy()
    cols, meta = {}, []
    years = sorted(d.year.unique())
    for e in sorted(c for c in d.cohort.unique() if c > 0):
        pre = [y for y in years if y < e and y not in own_years]
        ref = max(pre) - e
        te = d.cohort == e
        for y in years:
            if y in own_years:
                name = f"own_{e}_{y}"
                cols[name] = (te & (d.year == y)).astype(float)
                meta.append({"name": name, "kind": "own", "cohort": e, "rel": y - e, "year": y})
                continue
            l = y - e  # noqa: E741
            if l == ref:
                continue
            name = rel_name(e, l)
            cols[name] = (te & (d.year == y)).astype(float)
            meta.append({"name": name, "kind": "rel", "cohort": e, "rel": l, "year": y})
        meta.append({"name": f"ref_{e}", "kind": "ref", "cohort": e, "rel": ref, "year": e + ref})
    d = pd.concat([d, pd.DataFrame(cols, index=d.index)], axis=1)
    return d, pd.DataFrame(meta)


def fit(d: pd.DataFrame, meta: pd.DataFrame, covars: list[str], region_col: str = "region"):
    """OLS with unit and region x year fixed effects; SEs clustered by unit (CRV1)."""
    xs = [n for n in meta.name if not n.startswith("ref_")] + covars
    f = pf.feols(f"y ~ {' + '.join(xs)} | unit_id + {region_col}^year", data=d, vcov={"CRV1": "unit_id"})
    names = [str(n) for n in f._coefnames]
    b = pd.Series(np.asarray(f.coef()), index=names)
    V = pd.DataFrame(np.asarray(f._vcov), index=names, columns=names)
    return b, V, f


def aggregate(b: pd.Series, V: pd.DataFrame, meta: pd.DataFrame, sizes: pd.Series, window: tuple[int, int],
              kind: str = "rel") -> tuple[pd.DataFrame, pd.DataFrame]:  # fmt: skip
    """Interaction-weighted aggregation: at each relative year l, the cohort-share-weighted mean of the
    estimated d_{e,l}. `sizes`: cohort -> number of treated units. Returns (table, covariance)."""
    m = meta[(meta.kind == kind) & meta.name.isin(b.index)]
    if kind == "rel":
        m = m[m.rel.between(*window)]
        key = "rel"
    else:
        key = "year"
    W, rows = [], []
    for k, g in m.groupby(key):
        w = sizes.reindex(g.cohort).to_numpy(float)
        w = w / w.sum()
        vec = pd.Series(0.0, index=b.index)
        vec[g.name.to_numpy()] = w
        W.append(vec)
        rows.append({key: int(k), "cohorts": ";".join(map(str, g.cohort)), "n_treated": int(sizes.reindex(g.cohort).sum())})
    W = pd.DataFrame(W)
    est = W.to_numpy() @ b.to_numpy()
    cov = W.to_numpy() @ V.loc[b.index, b.index].to_numpy() @ W.to_numpy().T
    t = pd.DataFrame(rows)
    t["coef"], t["se"] = est, np.sqrt(np.diag(cov))
    t["lo95"], t["hi95"] = t.coef - 1.959964 * t.se, t.coef + 1.959964 * t.se
    labels = t[key].tolist()
    return t, pd.DataFrame(cov, index=labels, columns=labels)


def wald(t: pd.DataFrame, cov: pd.DataFrame, rels: list[int]) -> dict:
    """Joint test that the aggregated coefficients at `rels` are all 0."""
    have = [r for r in rels if r in set(t.rel)]
    bb = t.set_index("rel").coef.loc[have].to_numpy()
    VV = cov.loc[have, have].to_numpy()
    stat = float(bb @ np.linalg.solve(VV, bb))
    return {"rels": have, "stat": stat, "df": len(have), "p": float(stats.chi2.sf(stat, len(have)))}


def average(t: pd.DataFrame, cov: pd.DataFrame, rels: list[int]) -> dict:
    have = [r for r in rels if r in set(t.rel)]
    w = np.full(len(have), 1 / len(have))
    est = float(w @ t.set_index("rel").coef.loc[have].to_numpy())
    se = float(np.sqrt(w @ cov.loc[have, have].to_numpy() @ w))
    return {"rels": have, "coef": est, "se": se, "lo95": est - 1.959964 * se, "hi95": est + 1.959964 * se}


# ---------------------------------------------------------------- real data


def panel(drop_years: tuple[int, ...], regions5: bool = False) -> pd.DataFrame:
    """Treated + never-treated units, log population-weighted V5.GL.06, ERA5 covariates."""
    u = pd.read_csv(A.OUT / "design_units.csv")
    u = u[u.role_a.isin(["treated", "control"])]
    pan = pd.read_parquet(A.OUT / "panel_annual.parquet")
    pan = pan[(pan.series == "popw_V5GL06") & pan.unit_id.isin(u.unit_id) & ~pan.year.isin(drop_years)]
    era = pd.read_parquet(A.OUT / "era5_unit_year.parquet")
    d = pan.merge(era, on=["unit_id", "year"], how="left", validate="one_to_one")
    if d[COVARS].isna().any().any():
        raise ValueError("ERA5 covariates missing for some unit-years")
    d = d.merge(u[["unit_id", "role_a", "cohort_listed", "region", "himalayan"]], on="unit_id")
    d["y"] = np.log(d.value)
    d["cohort"] = np.where(d.role_a == "treated", d.cohort_listed, 0).astype(int)
    if regions5:
        d["region"] = np.where(d.himalayan.astype(bool), "himalayan", d.region)
    return d


def run_one(name: str, drop_years: tuple[int, ...], own_years: tuple[int, ...] = (), regions5: bool = False) -> dict:
    P = params()["causal"]
    window = tuple(P["event_window"])
    d = panel(drop_years, regions5)
    sizes = d[d.cohort > 0].groupby("cohort").unit_id.nunique()
    dd, meta = sa_design(d, own_years)
    b, V, f = fit(dd, meta, COVARS)
    t, cov = aggregate(b, V, meta, sizes, window)
    pre = list(range(window[0], -1))  # -9 .. -2
    post = list(range(0, window[1] + 1))  # 0 .. +5
    res = {"name": name, "drop_years": list(drop_years), "own_years": list(own_years), "regions5": regions5,
           "n_obs": int(f._N), "n_units": int(d.unit_id.nunique()), "cohort_sizes": {int(k): int(v) for k, v in sizes.items()},
           "references": meta[meta.kind == "ref"][["cohort", "rel"]].to_dict("records"),
           "wald_pre": wald(t, cov, pre), "avg_post": average(t, cov, post)}  # fmt: skip
    if own_years:
        o, ocov = aggregate(b, V, meta, sizes, window, kind="own")
        res["own"] = o.to_dict("records")
        o.to_csv(OUT / f"{name}_own.csv", index=False)
    OUT.mkdir(parents=True, exist_ok=True)
    t.to_csv(OUT / f"{name}_coefs.csv", index=False)
    cov.to_csv(OUT / f"{name}_vcov.csv")
    b.rename("coef").to_frame().assign(se=np.sqrt(np.diag(V))).to_csv(OUT / f"{name}_cohort_coefs.csv")
    with open(OUT / f"{name}_meta.json", "w", encoding="utf-8") as fh:
        json.dump(res, fh, indent=2, default=float)
    return res


def main() -> None:
    require_gate("Layer A event study")
    OUT.mkdir(parents=True, exist_ok=True)
    for name, drop, own, r5 in (("es_primary", (2020,), (), False), ("es_own2020", (), (2020,), False),
                                ("es_himalayan", (2020,), (), True)):  # fmt: skip
        r = run_one(name, drop, own, r5)
        print(name, "Wald pre p =", round(r["wald_pre"]["p"], 4), "| units", r["n_units"], "| obs", r["n_obs"])


if __name__ == "__main__":
    main()

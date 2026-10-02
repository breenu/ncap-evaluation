"""The robustness table: every check in the plan's sensitivity table, whichever way it points (plan §5;
DEC-147, DEC-149). "Agrees" (DEC-135): the check's point estimate has the primary's sign and lies inside
the primary's 95% CI, on the same (log) scale. Phase 7 Part B. GATED (hard rule 4).

    python -m src.causal.robustness    -> data/processed/causal/robustness.csv
"""

import json

import numpy as np
import pandas as pd

from src.causal import decisions as D
from src.causal import layer_a as A
from src.causal import layer_b as B
from src.common.gate import require_gate

ES = A.OUT / "event_study"
LAYER_A_CHECKS = ["v6gl03", "v6gl0204", "area", "towns", "towns_nopatancheruvu", "asansol_alone", "treated100k",
                  "spill25", "funded", "anticip2018", "incl2020", "noigp"]  # fmt: skip


def own_2020(spec: str = "incl2020") -> dict:
    """SDID with 2020 included: the cohort-size-weighted 2020 value of the per-period effect curve (cohorts
    adopting by 2020), with its SE from the placebo replications' curves (DEC-147 item 11)."""
    d = A.SDID_DIR / spec
    cur = pd.read_parquet(d / "curve.parquet")
    est = pd.read_parquet(d / "estimates.parquet").set_index("fitset")
    c20 = cur[cur.year == 2020].copy()
    c20["n"] = c20.fitset.map(est.n_treated)
    val = float((c20.effect * c20.n).sum() / c20.n.sum())
    pl = pd.concat([pd.read_parquet(f) for f in sorted(d.glob("curves_*.parquet"))])
    pl = pl[pl.year == 2020].assign(n=lambda x: x.fitset.map(est.n_treated))
    null = pl.groupby("rep").apply(lambda g: (g.effect * g.n).sum() / g.n.sum(), include_groups=False)
    se = float(null.std(ddof=1))
    return {"est": val, "se": se, "lo95": val - 1.959964 * se, "hi95": val + 1.959964 * se, "cohorts": ";".join(c20.fitset)}


def loo_summary(primary_att: float, lo: float, hi: float) -> dict:
    loo = pd.read_parquet(A.SDID_DIR / "primary" / "loo.parquet")
    est = pd.read_parquet(A.SDID_DIR / "primary" / "estimates.parquet")
    n = est[est.fitset.str.startswith("all|") & (est.outcome == A.LOG)].set_index("fitset").n_treated
    agg = loo.groupby("dropped").apply(lambda g: (g.att * g.fitset.map(n)).sum() / g.fitset.map(n).sum(), include_groups=False)
    moved = (agg - primary_att).abs()
    top = moved.idxmax()
    return {"donors": int(len(agg)), "min": float(agg.min()), "max": float(agg.max()),
            "share_agree": float(np.mean([D.agrees(primary_att, lo, hi, x) for x in agg])),
            "most_influential": top, "att_without_it": float(agg[top])}  # fmt: skip


def main() -> None:
    require_gate("Robustness table")
    s = pd.read_csv(A.OUT / "sdid_summary.csv").set_index(["spec_id", "estimand"])
    specs = pd.read_csv(A.SPEC_DIR / "specs.csv").set_index("spec_id")
    p = s.loc[("primary", "att")]
    rows = []

    def add(layer, check, status, est, lo=np.nan, hi=np.nan, ref=(p.att, p.lo95, p.hi95), note=""):
        rows.append({"layer": layer, "check": check, "status": status, "est": est, "lo95": lo, "hi95": hi,
                     "agrees": D.agrees(*ref, est) if np.isfinite(est) else None, "note": note})  # fmt: skip

    for sid in LAYER_A_CHECKS:
        r = s.loc[(sid, "att")]
        add("A", specs.loc[sid, "label"], specs.loc[sid, "status"], r.att, r.lo95, r.hi95,
            note=f"{int(r.n_treated)} treated, {int(r.n_controls)} controls")  # fmt: skip
    add("A", "Patancheruvu excluded (primary)", "registered", p.att, p.lo95, p.hi95,
        note="identical to the primary by construction: no primary unit is Patancheruvu's (it lies inside Hyderabad's centre)")
    o = own_2020()
    rows.append({"layer": "A", "check": "2020 included: SDID per-period estimate in 2020 (own coefficient)", "status": "registered",
                 "est": o["est"], "lo95": o["lo95"], "hi95": o["hi95"], "agrees": None, "note": f"fit sets {o['cohorts']}; not an ATT"})  # fmt: skip
    for name in ("es_primary", "es_himalayan"):
        m = json.loads((ES / f"{name}_meta.json").read_text(encoding="utf-8"))
        a = m["avg_post"]
        lab = {"es_primary": "Event study, 4 regions: average post-period estimate",
               "es_himalayan": "Himalayan region split (event study, 5 regions): average post-period estimate"}[name]
        add("A", lab, "registered", a["coef"], a["lo95"], a["hi95"], note=f"pre-trend Wald p = {m['wald_pre']['p']:.4f}")
    for cg in ("nevertreated", "notyettreated"):
        r = pd.read_csv(A.OUT / "cs" / f"cs_{cg}_simple.csv").iloc[0]
        add("A", f"Callaway & Sant'Anna, {'never' if cg == 'nevertreated' else 'not-yet'}-treated controls", "registered", r.att, r.lo95, r.hi95)
    lo = loo_summary(p.att, p.lo95, p.hi95)
    add("A", "Leave-one-out donors: the most influential donor dropped", "registered", lo["att_without_it"],
        note=f"{lo['donors']} donors with weight > 0; estimate range {lo['min']:+.4f} to {lo['max']:+.4f} (log); {100 * lo['share_agree']:.0f}% agree; most influential {lo['most_influential']}")  # fmt: skip
    pl = s.loc[("placebo2016", "att")]
    add("A", "Placebo in time 2016 (rule c)", "registered", pl.att, pl.lo95, pl.hi95, ref=(0, -np.inf, np.inf),
        note="a placebo: expected near 0; 'agrees' not applicable")
    rows[-1]["agrees"] = None
    rows.append({"layer": "A", "check": "Placebo in space (500 permutations)", "status": "registered", "est": p.p_perm,
                 "agrees": None, "note": "equal-tailed permutation p of the primary ATT against the joint-placebo null"})  # fmt: skip
    if (ES / "es_fire_meta.json").exists():  # run 2026-10-03 after FIRMS was downloaded (DEC-171)
        m = json.loads((ES / "es_fire_meta.json").read_text(encoding="utf-8"))
        w = json.loads((ES / "es_fire_window_meta.json").read_text(encoding="utf-8"))
        a, fc = m["avg_post"], m["fire_coef"]
        add("A", "VIIRS fire covariate (from 2012)", "registered", a["coef"], a["lo95"], a["hi95"],
            note=(f"event study 2012-2024 with fire FRP within {m['radius_km']} km (DEC-171), average post-period estimate; "
                  f"same window without fire {D.pct(w['avg_post']['coef']):+.1f}%; fire coefficient {fc['coef']:+.4f} "
                  f"(SE {fc['se']:.4f}); pre-trend Wald p = {m['wald_pre']['p']:.4f}"))  # fmt: skip
    else:
        rows.append({"layer": "A", "check": "VIIRS fire covariate (from 2012)", "status": "registered", "est": np.nan, "agrees": None,
                     "note": "not run: FIRMS has not been downloaded (DEC-039, DEC-147 item 17)"})  # fmt: skip
    rows.append({"layer": "A", "check": "Raw MAIAC AOD", "status": "registered", "est": np.nan, "agrees": None,
                 "note": "not run: registered as 'if time allows'; not downloaded (DEC-147 item 18)"})  # fmt: skip

    est = pd.read_csv(B.OUT / "estimates.csv")
    labels = {v.key: v.label for v in B.versions()}
    for pol in B.POLS:
        for estimator in ("ITS", "DiD"):
            pr = est[(est.version == "primary") & (est.estimator == estimator) & (est.pollutant == pol)]
            if not len(pr) or not pr.iloc[0].get("computable", True):
                continue
            pr = pr.iloc[0]
            for _, r in est[(est.estimator == estimator) & (est.pollutant == pol) & (est.version != "primary")].iterrows():
                if not r.get("computable", True) or pd.isna(r.get("est")):
                    rows.append({"layer": f"B {pol}", "check": f"{estimator}: {labels.get(r.version, r.version)}", "status": "", "est": np.nan,
                                 "agrees": None, "note": "not computable: no treated city (or no control) holds a panel"})  # fmt: skip
                    continue
                add(f"B {pol}", f"{estimator}: {r.label}", r.status, r.est, r.lo95, r.hi95, ref=(pr.est, pr.lo95, pr.hi95),
                    note=(f"{int(r.cities_used)} of {int(r.cities)} panel cities used (cohorts listed 2020-21 only, DEC-157)"
                          if pd.notna(r.get("cities_used")) and int(r.cities_used) < int(r.cities)
                          else f"{int(r.cities)} cities ({int(r.single_station_cities)} single-station)"))  # fmt: skip
    pd.DataFrame(rows).to_csv(A.OUT / "robustness.csv", index=False)


if __name__ == "__main__":
    main()

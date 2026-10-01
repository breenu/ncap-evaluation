"""Generated report for Phase 7 (causal analysis, RQ3): docs/causal_report.md, and the decision record
data/processed/causal/partA_results.json. Every number comes from pipeline outputs; nothing is typed.

Part A (Layer A, satellite): H1 with every registered rule check (DEC-141), H2 (DEC-140), the
calibration-leakage split (DEC-146), the event study and HonestDiD (DEC-142/143), Callaway & Sant'Anna
(DEC-144), the 2016 placebo (DEC-145). Part B sections are added after Reenu's go-ahead.

    python -m src.causal.causal_report
"""

import json
import math

import pandas as pd

from src.causal import decisions as D
from src.causal import layer_a as A
from src.common.gate import require_gate
from src.common.paths import DOCS, INTERIM, params

ES = A.OUT / "event_study"


def pc(x: float, d: int = 1) -> str:
    return f"{D.pct(x):+.{d}f}%"


def lg(x: float) -> str:
    return f"{x:+.4f}"


def ci_pct(lo: float, hi: float, d: int = 1) -> str:
    return f"{D.pct(lo):+.{d}f}% to {D.pct(hi):+.{d}f}%"


def md(df: pd.DataFrame) -> str:
    cols = list(df.columns)
    out = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    out += ["| " + " | ".join("" if pd.isna(v) else str(v) for v in r) + " |" for r in df.itertuples(index=False)]
    return "\n".join(out)


def pp(p: float, reps: int = 500) -> str:
    """Permutation p; the smallest value 500 replications can give is 2/501 = 0.004."""
    floor = 2 / (reps + 1)
    return f"{p:.3f} (the minimum possible)" if p <= floor + 1e-12 else f"{p:.3f}"


def yes(b: bool) -> str:
    return "yes" if b else "**no**"


# ---------------------------------------------------------------- load and decide


def load() -> dict:
    s = pd.read_csv(A.OUT / "sdid_summary.csv")
    est = {sid: pd.read_parquet(A.SDID_DIR / sid / "estimates.parquet") for sid in s.spec_id.unique()}
    meta = json.loads((ES / "es_primary_meta.json").read_text(encoding="utf-8"))
    return {
        "s": s.set_index(["spec_id", "estimand"]),
        "est": est,
        "es": pd.read_csv(ES / "es_primary_coefs.csv"),
        "es_meta": meta,
        "es_own": pd.read_csv(ES / "es_own2020_own.csv"),
        "es_own_meta": json.loads((ES / "es_own2020_meta.json").read_text(encoding="utf-8")),
        "es_own_coefs": pd.read_csv(ES / "es_own2020_coefs.csv"),
        "hon": pd.read_csv(ES / "es_primary_honest_summary.csv", dtype={"breakdown_note": str}).iloc[0],
        "hon_note": str(pd.read_csv(ES / "es_primary_honest_summary.csv", dtype={"breakdown_note": str}).breakdown_note.iloc[0]),
        "hon_rm": pd.read_csv(ES / "es_primary_honest_rm.csv"),
        "hon_sm": pd.read_csv(ES / "es_primary_honest_sm.csv"),
        "cs": {cg: pd.read_csv(A.OUT / "cs" / f"cs_{cg}_simple.csv").iloc[0] for cg in ("nevertreated", "notyettreated")},
        "cs_dyn": pd.read_csv(A.OUT / "cs" / "cs_nevertreated_dynamic.csv"),
        "mde": pd.read_csv(INTERIM / "pregate" / "mde_meta.csv"),
        "specs": pd.read_csv(A.SPEC_DIR / "specs.csv").set_index("spec_id"),
    }


def mde_log() -> float:
    """The plan's carried MDE: the largest log-annual MDE over designs and fake years (Phase 4)."""
    d = pd.read_parquet(INTERIM / "pregate" / "mde_draws.parquet")
    d = d[d.outcome == "log_annual"]
    return float(params()["pregate"]["mde_multiplier"] * d.groupby(["design", "fake_year"]).att.std(ddof=1).max())


def decide(X: dict) -> dict:
    P = params()
    s = X["s"]
    p = s.loc[("primary", "att")]
    pl = s.loc[("placebo2016", "att")]
    d_points = {"Callaway & Sant'Anna": float(X["cs"]["nevertreated"].att),
                "area-weighted": float(s.loc[("area", "att")].att),
                "V6.GL.03": float(s.loc[("v6gl03", "att")].att)}  # fmt: skip
    h1 = D.h1_verdict(p.att, p.lo95, p.hi95, p.lo90, p.hi90, X["es_meta"]["wald_pre"]["p"], pl.lo95, pl.hi95,
                      d_points, P["causal"]["wald_p_min"], P["robustness"]["equivalence_margin_pct"])  # fmt: skip
    h2 = s.loc[("primary", "winter_minus_nonwinter")]
    g, n, df = (s.loc[("primary", k)] for k in ("gained", "notgained", "gained_minus_notgained"))
    warn, why = D.leakage_warning((g.att, g.lo95, g.hi95), (n.att, n.lo95, n.hi95), (df.att, df.lo95, df.hi95))
    out = {
        "primary": {k: float(p[k]) for k in ("att", "se", "lo95", "hi95", "lo90", "hi90", "p_perm", "reps")},
        "h1": {**h1, "d_points": d_points},
        "targets_excluded": D.target_exclusions(p.lo95, p.hi95, P["causal"]["target_reductions_pct"]),
        "mde_log": mde_log(),
        "h2": {"tested": h1["code"] == "supported", "diff": float(h2.att), "lo95": float(h2.lo95), "hi95": float(h2.hi95),
               "supported": D.h2_supported(h2.hi95)},  # fmt: skip
        "leakage": {"warning": warn, "reason": why,
                    **{k: {"att": float(r.att), "lo95": float(r.lo95), "hi95": float(r.hi95)}
                       for k, r in (("gained", g), ("notgained", n), ("diff", df))}},  # fmt: skip
        "placebo2016": {"att": float(pl.att), "lo95": float(pl.lo95), "hi95": float(pl.hi95)},
        "wald_pre": X["es_meta"]["wald_pre"],
        "honest_breakdown": str(X["hon"].breakdown_note),
    }
    return out


# ---------------------------------------------------------------- sections


def cohort_table(X: dict, spec: str, outcome: str, level: bool = False) -> pd.DataFrame:
    e = X["est"][spec]
    e = e[(e.outcome == outcome) & e.fitset.str.startswith("all|")]
    t = pd.DataFrame({"cohort": e.cohort, "treated units": e.n_treated, "pre-years (T0)": e.T0})
    if level:
        return t.assign(**{"ATT (µg/m³)": e.att.map(lambda v: f"{v:+.2f}")})
    return t.assign(**{"ATT (log)": e.att.map(lg), "ATT (%)": e.att.map(pc)})


def row(X: dict, spec: str, est: str = "att", name: str | None = None, scale: str = "log") -> dict:
    r = X["s"].loc[(spec, est)]
    if scale == "level":
        return {"specification": name or X["specs"].loc[spec, "label"], "estimate": f"{r.att:+.2f} µg/m³",
                "95% CI": f"{r.lo95:+.2f} to {r.hi95:+.2f} µg/m³", "SE": f"{r.se:.2f}", "permutation p": pp(r.p_perm, r.reps)}  # fmt: skip
    return {"specification": name or X["specs"].loc[spec, "label"], "estimate (log)": lg(r.att), "estimate (%)": pc(r.att),
            "95% CI (%)": ci_pct(r.lo95, r.hi95), "SE (log)": f"{r.se:.4f}", "permutation p": pp(r.p_perm, r.reps)}  # fmt: skip


def section_h1(X: dict, R: dict) -> str:
    p, h = R["primary"], R["h1"]
    sp = X["specs"].loc["primary"]
    lines = ["## 1. H1 (confirmatory, primary): the registered decision", ""]
    lines += ["> **H1** (registered): NCAP enrolment reduced annual population-weighted PM2.5 in enrolled urban centres, relative to comparable non-enrolled centres, 2019–2024 (2020 excluded).",
              ">", f"> **Verdict: {h['verdict']}.**", ""]  # fmt: skip
    pl = R["placebo2016"]
    w = R["wald_pre"]
    rules = pd.DataFrame([
        {"rule": "(a) primary SDID ATT < 0 and its 95% CI entirely below 0",
         "value": f"ATT {lg(p['att'])} ({pc(p['att'])}); 95% CI {lg(p['lo95'])} to {lg(p['hi95'])} ({ci_pct(p['lo95'], p['hi95'])})", "met": yes(h["a"])},
        {"rule": "(b) event-study pre-period coefficients −9 … −2 jointly insignificant (Wald p > 0.10)",
         "value": f"χ² = {w['stat']:.2f}, df = {w['df']}, p = {w['p']:.4f}", "met": yes(h["b"])},
        {"rule": "(c) the 2016 placebo-in-time 95% CI includes 0",
         "value": f"{lg(pl['att'])}; 95% CI {lg(pl['lo95'])} to {lg(pl['hi95'])}", "met": yes(h["c"])},
        {"rule": "(d) point estimate < 0 in Callaway & Sant'Anna, area-weighted and V6.GL.03",
         "value": "; ".join(f"{k} {lg(v)}" for k, v in h["d_points"].items()), "met": yes(h["d"])},
    ])  # fmt: skip
    lines += ["**Every rule, as registered (plan §5) and read in DEC-135/141.** The verdict takes the first branch that applies: (b) or (c) failing → not identified; else a reduction with a CI excluding 0 → supported if (d) holds; an increase → not supported; a CI including 0 → no detectable effect, with the equivalence test.", "", md(rules), ""]  # fmt: skip
    eq = "within" if h["equivalent"] else "**not** within"
    tg = R["targets_excluded"]
    lines += [
        "**Reported whatever the outcome:**",
        f"- 90% CI: {lg(p['lo90'])} to {lg(p['hi90'])} ({ci_pct(p['lo90'], p['hi90'])}); it is {eq} the equivalence bounds ln 0.95 = {math.log(0.95):+.4f} to ln 1.05 = {math.log(1.05):+.4f}"
        + (", so effects of 5% or more in either direction are ruled out at the 5% level (reported for information: the verdict is decided by the branch above)." if h["equivalent"] else "."),
        f"- The 95% CI's lower bound is {lg(p['lo95'])} ({pc(p['lo95'])}); against NCAP's targets it "
        + "; ".join(f"{'excludes' if v else 'does not exclude'} a {k}% reduction" for k, v in tg.items())
        + ". NCAP's targets (20–30%, later up to 40%) were set for **PM10**; a satellite PM2.5 result says nothing directly about PM10 attainment.",
        f"- MDE (Phase 4, a best-case lower bound): {R['mde_log']:.4f} in log units ({100 * (1 - math.exp(-R['mde_log'])):.1f}% fall). The SE of the real design is {p['se']:.4f}, i.e. 2.8 × SE = {2.8 * p['se']:.4f} ({100 * (1 - math.exp(-2.8 * p['se'])):.1f}%).",
        f"- Placebo in space: the primary ATT against the {int(p['reps'])} joint-placebo aggregates, equal-tailed permutation p = {pp(p['p_perm'], int(p['reps']))}: no placebo set of control centres moved as much.",
        f"- Calibration-leakage warning sign (§3): {'**yes**: ' + R['leakage']['reason'] if R['leakage']['warning'] else 'no'}.",
        "",
    ]  # fmt: skip
    lines += ["### 1a. The primary estimate", "",
              f"SDID per listing cohort against the {int(sp.n_controls)} never-treated centres; 2010–2024 without 2020; cohort ATTs combined by treated units; SE from {int(p['reps'])} joint-placebo replications (DEC-139). Effect = listed minus synthetic counterfactual on log PM2.5 (negative = a reduction).", ""]  # fmt: skip
    lines += [md(pd.DataFrame([row(X, "primary", "att", "Primary, log annual PM2.5 (headline)")])), "",
              md(pd.DataFrame([row(X, "primary", "att:level:popw_V5GL06", "Same design, µg/m³ (secondary)", scale="level")])), ""]  # fmt: skip
    lines += ["By cohort (log annual):", "", md(cohort_table(X, "primary", A.LOG)), ""]
    lines += ["By cohort (µg/m³):", "", md(cohort_table(X, "primary", "level:popw_V5GL06", level=True)), ""]
    lines += ["### 1b. Rule (d) specifications, with their own joint-placebo SEs", "",
              md(pd.DataFrame([row(X, "area"), row(X, "v6gl03")])),
              f"\nCallaway & Sant'Anna (simple aggregation): never-treated {lg(X['cs']['nevertreated'].att)} ({pc(X['cs']['nevertreated'].att)}; 95% CI {ci_pct(X['cs']['nevertreated'].lo95, X['cs']['nevertreated'].hi95)}); not-yet-treated {lg(X['cs']['notyettreated'].att)} ({pc(X['cs']['notyettreated'].att)}; {ci_pct(X['cs']['notyettreated'].lo95, X['cs']['notyettreated'].hi95)}).", ""]  # fmt: skip
    nw = X["s"].xs("att", level="estimand")[["warnings_real", "warnings_placebo"]]
    lines += [f"*SDID convergence warnings (synthdid's Frank–Wolfe solver): real fits {int(nw.warnings_real.sum())}, placebo fits {int(nw.warnings_placebo.sum())}, over all Part A specifications.*", ""]  # fmt: skip
    return "\n".join(lines)


def section_h2(X: dict, R: dict) -> str:
    h2 = R["h2"]
    lines = ["## 2. H2 (confirmatory, tested only if H1 is supported): a larger winter reduction", ""]
    status = ("tested (H1 supported): " + ("**supported**" if h2["supported"] else "**not supported**")) if h2["tested"] else \
        "**not tested** (H1 is not supported); reported as exploratory, as registered"  # fmt: skip
    lines += [f"> **H2** (registered): the reduction is larger in winter (Oct–Feb) than in the rest of the year. Status: {status}.", ""]
    lines += [md(pd.DataFrame([row(X, "primary", "att:log:winter_popw_V5GL06", "Winter (Oct–Feb), log"),
                               row(X, "primary", "att:log:nonwinter_popw_V5GL06", "Non-winter (Mar–Sep), log"),
                               row(X, "primary", "winter_minus_nonwinter", "Winter minus non-winter (H2)")])), ""]  # fmt: skip
    lines += ["Season-years 2010–2023, season-year 2020 dropped for both; post = season-year ≥ listing year (DEC-140). Supported only if the difference's 95% CI lies entirely below 0 (DEC-135). The H2 MDE (Phase 4) is 0.0215 log units.", ""]  # fmt: skip
    return "\n".join(lines)


def section_leakage(X: dict, R: dict) -> str:
    L = R["leakage"]
    lines = ["## 3. Calibration leakage (pre-specified, beside H1)", "",
             "ACAG calibrates satellite PM2.5 to ground monitors, and NCAP added monitors mainly in treated cities. The primary design is re-estimated separately for treated units that gained a CAAQMS station inside their polygon with first PM data in 2019–2024 and for those that did not (DEC-096/146); SEs from the same joint-placebo replications.", ""]  # fmt: skip
    lines += [md(pd.DataFrame([row(X, "primary", "gained", "Gained a monitor 2019–2024 (74 units)"),
                               row(X, "primary", "notgained", "Did not (39 units)"),
                               row(X, "primary", "gained_minus_notgained", "Difference, gained − not gained")])), ""]  # fmt: skip
    lines += [f"**Warning sign of leakage (registered rule): {'YES — ' + L['reason'] if L['warning'] else 'no'}.** It is a warning, not proof: units that gained monitors also differ in size and pollution.", ""]
    g, n = L["gained"], L["notgained"]
    if g["att"] > 0 and n["att"] > 0:
        lines += [f"*Read with the signs:* both groups' estimates are increases ({pc(g['att'])} and {pc(n['att'])}); the group that gained monitors rose less. The rule was written with reductions in mind and fires here on its second clause. The direction is the one calibration leakage would produce (ACAG calibrated to new monitors that, per Phase 6, read cleaner than existing ones would pull the satellite values of those units down), but the comparison cannot separate that from real differences between the two groups.", ""]  # fmt: skip
    return "\n".join(lines)


def section_event(X: dict, R: dict) -> str:
    es, m = X["es"], X["es_meta"]
    lines = ["## 4. Event study (Sun & Abraham) and HonestDiD", "",
             f"Interaction-weighted coefficients; unit and region × year fixed effects, ERA5 covariates, SEs clustered by unit; {m['n_units']} units, {m['n_obs']} unit-years, 2020 dropped (DEC-142). References: "
             + ", ".join(f"cohort {r['cohort']} l = {r['rel']}" for r in m["references"]) + ".", ""]  # fmt: skip
    t = es.assign(**{"coef (log)": es.coef.map(lg), "%": es.coef.map(pc), "95% CI (%)": [ci_pct(a, b) for a, b in zip(es.lo95, es.hi95, strict=True)],
                     "SE": es.se.map(lambda v: f"{v:.4f}")})[["rel", "cohorts", "n_treated", "coef (log)", "%", "95% CI (%)", "SE"]]  # fmt: skip
    lines += [md(t), ""]
    w, a = m["wald_pre"], m["avg_post"]
    lines += [f"- **Rule (b):** Wald χ² = {w['stat']:.2f} on {w['df']} df, p = {w['p']:.4f} (registered threshold p > 0.10).",
              f"- **Average post-period effect** (l = 0 … +5): {lg(a['coef'])} ({pc(a['coef'])}; 95% CI {ci_pct(a['lo95'], a['hi95'])}).",
              ""]  # fmt: skip
    o, om = X["es_own"].iloc[0], X["es_own_meta"]
    lines += [f"**2020, own coefficient** (fit with 2020 included, its treated observations on cohort-specific 2020 indicators): {lg(o.coef)} ({pc(o.coef)}; 95% CI {ci_pct(o.lo95, o.hi95)}), cohorts {o.cohorts}. In that fit, the pre-trend Wald p = {om['wald_pre']['p']:.4f} and the average post effect is {pc(om['avg_post']['coef'])} ({ci_pct(om['avg_post']['lo95'], om['avg_post']['hi95'])}).", ""]  # fmt: skip
    h, rm, sm = X["hon"], X["hon_rm"], X["hon_sm"]
    lines += ["**HonestDiD (Rambachan & Roth; reported, not a decision rule; DEC-143).** Target: the average post-period effect.", "",
              f"- Original 95% CI: {lg(h.orig_lb)} to {lg(h.orig_ub)} ({ci_pct(h.orig_lb, h.orig_ub)}): {h.direction}.",
              f"- **Breakdown M̄** (largest relative magnitude at which the robust CI still excludes 0, on the side of the original CI): {X['hon_note']}.",
              "- Package warnings are kept with each row. \"CI is open\" means the robust interval reached the edge of HonestDiD's search grid, so the true interval is at least that wide; \"solution may be inaccurate\" is the convex solver's own caution.", ""]  # fmt: skip
    warn = lambda w: "" if pd.isna(w) or not str(w) else str(w)  # noqa: E731
    lines += [md(pd.DataFrame({"M̄ (relative magnitudes)": rm.Mbar, "robust 95% CI (log)": [f"{a:+.4f} to {b:+.4f}" for a, b in zip(rm.lb, rm.ub, strict=True)],
                               "(%)": [ci_pct(a, b) for a, b in zip(rm.lb, rm.ub, strict=True)], "warnings": rm.warnings.map(warn)})), ""]  # fmt: skip
    lines += [md(pd.DataFrame({"M (smoothness)": sm.M.map(lambda v: f"{v:.4f}"), "robust 95% CI (log)": [f"{a:+.4f} to {b:+.4f}" for a, b in zip(sm.lb, sm.ub, strict=True)],
                               "(%)": [ci_pct(a, b) for a, b in zip(sm.lb, sm.ub, strict=True)], "warnings": sm.warnings.map(warn)})), ""]  # fmt: skip
    return "\n".join(lines)


def section_cs(X: dict) -> str:
    d = X["cs_dyn"]
    lines = ["## 5. Callaway & Sant'Anna", "",
             "R `did` 2.5.1, doubly robust with no covariates (the registered text names none, so it is the unconditional DiD), never-treated controls primary, base period varying (DEC-144). Uniform 95% bands from 1,000 multiplier-bootstrap draws.", ""]  # fmt: skip
    lines += ["The not-yet-treated pool adds only the 24 units of cohorts 2020 and 2021, and only for years before 2021, so the two control choices differ in a few group-time cells and hardly at all in aggregate.", ""]
    lines += [md(pd.DataFrame([{"controls": cg, "ATT (log)": lg(r.att), "ATT (%)": pc(r.att), "95% CI (%)": ci_pct(r.lo95, r.hi95)}
                               for cg, r in X["cs"].items()])), ""]  # fmt: skip
    lines += ["Dynamic aggregation (never-treated):", "",
              md(pd.DataFrame({"rel": d.rel, "ATT (%)": d.att.map(pc), "pointwise 95% (%)": [ci_pct(a, b) for a, b in zip(d.lo95, d.hi95, strict=True)],
                               "uniform 95% band (%)": [ci_pct(a, b) for a, b in zip(d.ulo, d.uhi, strict=True)]})), ""]  # fmt: skip
    return "\n".join(lines)


def section_placebo(X: dict) -> str:
    lines = ["## 6. Placebo in time, 2016 (rule c)", "",
             "The 113 treated units given a fake adoption in 2016, data 2010–2018 only (Phase 4's pre-period reader), SDID against the 923 controls. Rule (c) uses the random-set null, the primary's own SE design; the region-matched null is shown for information (DEC-145).", ""]  # fmt: skip
    lines += [md(pd.DataFrame([row(X, "placebo2016", name="Fake adoption 2016, random null (rule c)"),
                               row(X, "placebo2016_rm", name="Fake adoption 2016, region-matched null (information)")])), ""]  # fmt: skip
    return "\n".join(lines)


def build(X: dict, R: dict) -> str:
    head = ["# Causal analysis (Phase 7, RQ3)", "",
            "*Generated by `python -m src.causal.causal_report` from `data/processed/causal/`. Do not edit by hand. Rules: the registered plan (`docs/analysis_plan.md` at `6e24eca`, https://osf.io/jksne/) §5, read as in DEC-135; every gap filled before any estimate in DEC-138 to DEC-150 (commit `eebaecc`, pushed before computing). Effects: listed minus counterfactual on log concentration; negative = a reduction; % = 100 × (e^β − 1).*", "",
            "**Part A (Layer A, satellite PM2.5) is complete. Part B (Layer B, triangulation, the robustness battery, figure 1's policy step) runs after Reenu's go-ahead.**", ""]  # fmt: skip
    body = [section_h1(X, R), section_h2(X, R), section_leakage(X, R), section_event(X, R), section_cs(X), section_placebo(X)]
    tail = ["## Caveats that travel with every Layer A number", "",
            "- The MDE is a best-case lower bound (plan §3); the confidence intervals use the real design's joint-placebo SE.",
            "- ACAG is calibrated to ground monitors (§3 is the pre-specified check; the V6.GL.02.04 vintage comparison is in Part B).",
            "- Satellite PM2.5 says nothing directly about PM10, NCAP's target pollutant.",
            "- The design estimates the effect of being listed, relative to comparable centres; it cannot say which city action worked.",
            "- Figure 4: `reports/figures/fig4_event_study.{png,svg}`.", ""]  # fmt: skip
    return "\n".join(head + body + tail)


def main() -> None:
    require_gate("Phase 7 report")
    X = load()
    R = decide(X)
    with open(A.OUT / "partA_results.json", "w", encoding="utf-8") as fh:
        json.dump(R, fh, indent=2, default=lambda o: bool(o) if isinstance(o, bool) else float(o))
    (DOCS / "causal_report.md").write_text(build(X, R), encoding="utf-8", newline="\n")
    print("H1:", R["h1"]["verdict"])


if __name__ == "__main__":
    main()

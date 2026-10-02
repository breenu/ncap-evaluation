"""docs/heterogeneity_report.md (Phase 8, RQ4), generated from data/processed/hierarchical/. Every number comes
from pipeline outputs. Rules: DEC-162 to DEC-166 (pushed before computing).

Wording rule (DEC-154, extended by Reenu on 2026-10-02): H1 is not identified, so every per-unit number and
H5 are **city-level relative changes**, never effects of NCAP, with the caveat beside each.

    python -m src.hierarchical.report
"""

import json

import numpy as np
import pandas as pd

from src.causal import layer_a as A
from src.causal.causal_report import md
from src.causal.report_part_b import ci_pct, lg, pc
from src.common.paths import DOCS
from src.hierarchical.city_estimates import MODERATORS, OUT

NOT_ID = ("H1 is not identified by this design (Phase 7, DEC-151), so this is a city-level relative change, "
          "not an effect of NCAP.")  # fmt: skip
MOD_LABEL = {"baseline_pm25": "baseline PM2.5 (per SD of 2010-2018 mean log PM2.5)", "igp": "Indo-Gangetic Plain (vs peninsular/other + north-east)",
             "log_pop": "log population 2015 (per SD)", "coastal": "coastal (vs peninsular/other + north-east)",
             "xvfc": "funding channel XV-FC (vs NCAP channel)"}  # fmt: skip
POLN = {"pm25": "PM2.5", "pm10": "PM10"}
REGION = {"igp": "IGP", "coastal": "coastal", "peninsular/other": "peninsular/other", "north-east": "north-east"}


def load() -> dict:
    j = lambda f: json.loads((OUT / f).read_text())  # noqa: E731
    return {
        "e": pd.read_csv(OUT / "city_estimates.csv"), "us": pd.read_csv(OUT / "unit_sdid_summary.csv"),
        "co": pd.read_csv(OUT / "pool_coefs.csv"), "dg": pd.read_csv(OUT / "pool_diagnostics.csv"),
        "c": pd.read_csv(OUT / "city_shrunken.csv"), "corr": pd.read_csv(OUT / "moderator_corr.csv", index_col=0),
        "h5": j("h5.json"), "h3": j("h3.json"), "b": pd.read_csv(OUT / "h3_betas.csv"), "r": pd.read_csv(OUT / "h3_ratio.csv"),
        "ii": pd.read_csv(OUT / "h3_condition_ii.csv"), "lb": pd.read_csv(A.OUT / "layer_b" / "estimates.csv"),
        "tri": pd.read_csv(A.OUT / "triangulation.csv"), "rob": pd.read_csv(A.OUT / "robustness.csv"),
        "sd": pd.read_csv(A.OUT / "sdid_summary.csv"),
        "dc": pd.read_csv(OUT / "dose_coefs.csv"), "dd": pd.read_csv(OUT / "dose_diagnostics.csv"),
        "du": pd.read_csv(OUT / "dose_units.csv"), "ws": pd.read_csv(OUT / "dose_within_state.csv"),
    }  # fmt: skip


def coef(X: dict, version: str, param: str) -> pd.Series:
    return X["co"][(X["co"].version == version) & (X["co"].param == param)].iloc[0]


def section_estimates(X: dict) -> str:
    e, us, sd = X["e"], X["us"], X["sd"]
    prim = sd[(sd.spec_id == "primary") & (sd.estimand == "att")].iloc[0]
    p = us[(us.series == "popw_V5GL06") & (us.kind == "placebo")]
    rows = [{"cohort": int(r.cohort), "treated units": int((e.cohort == r.cohort).sum()), "placebo fits": int(r.n),
             "placebo mean (log)": lg(r["mean"]), "placebo SD = SE (log)": f"{r.sd:.4f}", "± 1.96 SE (%)": f"±{1.96 * 100 * r.sd:.1f} pp"}
            for _, r in p.iterrows()]  # fmt: skip
    warn = int(us[us.series == "popw_V5GL06"].warnings.sum())
    nbh = int(e.bh_reject.sum())
    r56 = float(np.corrcoef(e.est, e["est_popw_V6GL03"])[0, 1])
    return "\n".join([
        "## 1. City-level estimates (DEC-162)", "",
        "One synthetic difference-in-differences per NCAP unit: the unit alone against all 923 controls, with its listing cohort, "
        "log population-weighted ACAG V5.GL.06, 2010–2024 without 2020 (the primary design otherwise). " + NOT_ID, "",
        "**Standard errors.** For each cohort year, every control in turn was the single fake treated unit against the other 922: "
        "the SD of those placebo estimates is the SE of every unit in that cohort (no random draws).", "",
        md(pd.DataFrame(rows)), "",
        f"- Mean of the {len(e)} per-unit estimates: {lg(e.est.mean())} ({pc(e.est.mean())}); median {pc(e.est.median())}. "
        f"The Phase 7 primary SDID (one synthetic comparison per cohort) is {lg(prim.att)} ({pc(prim.att)}). They differ in construction, "
        "so this is orientation, not a check.",
        f"- Per-unit estimates range from {pc(e.est.min())} to {pc(e.est.max())}; {int((e.est > 0).sum())} of {len(e)} are above 0.",
        f"- Pre-fit-scaled SEs (sensitivity): median {e.se_scaled.median():.4f}, range {e.se_scaled.min():.4f} to {e.se_scaled.max():.4f} "
        f"(cohort placebo SEs: {e.se.min():.4f} to {e.se.max():.4f}).",
        f"- V6.GL.03 per-unit estimates correlate with V5.GL.06's at r = {r56:.2f} across units.",
        f"- **Unshrunk city claims under Benjamini–Hochberg 5% over the {len(e)} units (plan §5): {nbh} units pass.** "
        f"Unadjusted, {int((e.p_placebo < 0.05).sum())} have p < 0.05; the smallest p is {e.p_placebo.min():.4f}, and the smallest attainable with "
        f"{int(e.n_placebo.iloc[0])} placebos is {2 / (e.n_placebo.iloc[0] + 1):.4f}. "
        "They are not named: city-level statements come from the shrunken estimates below, and there is no best/worst table.",
        "- Cohorts 2020 and 2021 share one placebo distribution: with 2020 dropped, both have pre-years 2010–2019 and post-years "
        "2021–2024, so the single-unit design is identical.",
        f"- SDID convergence warnings over all {int(us[us.series == 'popw_V5GL06'].n.sum())} V5.GL.06 fits: {warn}.", ""])  # fmt: skip


def section_model(X: dict) -> str:
    dg, c = X["dg"], X["c"]
    drows = [{"model": r.label, "converged": "yes" if r.converged else "**no**", "attempt": int(r.attempt),
              "max R-hat": f"{r.rhat_max:.3f}", "min bulk ESS": f"{r.ess_bulk_min:.0f}", "min tail ESS": f"{r.ess_tail_min:.0f}",
              "divergences": int(r.divergences)} for r in dg.itertuples()]  # fmt: skip
    crows = []
    for p in ["alpha", *[f"beta[{m}]" for m in MODERATORS], "tau", "average city-level relative change"]:
        r = coef(X, "primary", p)
        name = MOD_LABEL.get(p[5:-1], p) if p.startswith("beta") else {"alpha": "intercept (reference unit)", "tau": "between-unit SD τ (log)"}.get(p, p)
        pct_ci = "" if p == "tau" else f"{pc(r['mean'])} ({ci_pct(r.lo95, r.hi95)})"
        crows.append({"parameter": name, "posterior mean (log)": lg(r["mean"]) if p != "tau" else f"{r['mean']:.4f}",
                      "95% CrI (log)": f"{r.lo95:+.4f} to {r.hi95:+.4f}", "as % (95% CrI)": pct_ci, "P(> 0)": f"{r.p_gt0:.3f}"})  # fmt: skip
    p = c[c.version == "primary"]
    corr = X["corr"].round(2)
    corr.index.name = "moderator"
    return "\n".join([
        "## 2. The hierarchical model (DEC-163)", "",
        "est_i ~ Normal(θ_i, SE_i²); θ_i = α + β′x_i + τ z_i; priors α ~ N(0, 0.1), β ~ N(0, 0.05), τ ~ HalfNormal(0.05) on the log scale; "
        "NUTS, 4 chains × 2,000 draws. Intervals are 95% equal-tailed credible intervals. θ_i is a **shrunken city-level relative change**. " + NOT_ID, "",
        "**Convergence** (rule: R-hat ≤ 1.01, bulk and tail ESS ≥ 400, no divergences; no number is used from a model that fails):", "",
        md(pd.DataFrame(drows)), "",
        "**Primary model** (the five registered moderators; continuous moderators standardised over the 113 units):", "",
        md(pd.DataFrame(crows)), "",
        f"- Shrunken city-level relative changes: 95% CrI entirely below 0 for **{int((p.post_hi95 < 0).sum())} of {len(p)}** units, entirely above 0 for "
        f"**{int((p.post_lo95 > 0).sum())}**, spanning 0 for {int(((p.post_lo95 <= 0) & (p.post_hi95 >= 0)).sum())}.",
        f"- Median width of a unit's 95% rank interval: {np.median(p.rank_hi95 - p.rank_lo95):.0f} places out of {len(p)} (figure 6).",
        "- The errors of the per-unit estimates are correlated (shared donors, shared regional shocks) but the model treats them as "
        "independent, so its intervals are probably too narrow and a regional coefficient can carry a shock common to that region.", "",
        "Correlations among the moderators (treated units):", "", md(corr.reset_index()), ""])  # fmt: skip


def section_h5(X: dict) -> str:
    h5 = X["h5"]
    rows = []
    for v in X["dg"].itertuples():
        if not v.converged:
            rows.append({"model": v.label, "β_IGP (log)": "not converged"})
            continue
        r = coef(X, v.version, "beta[igp]")
        rows.append({"model": v.label, "β_IGP (log)": lg(r["mean"]), "95% CrI (log)": f"{r.lo95:+.4f} to {r.hi95:+.4f}",
                     "as % (95% CrI)": f"{pc(r['mean'])} ({ci_pct(r.lo95, r.hi95)})", "P(> 0)": f"{r.p_gt0:.3f}",
                     "decides H5": "yes" if v.version == "primary" else "no"})  # fmt: skip
    cbi = float(X["corr"].loc["baseline_pm25", "igp"])
    noigp = X["rob"][X["rob"].check.str.startswith("Exclude the Indo-Gangetic")].iloc[0]
    prim = X["sd"][(X["sd"].spec_id == "primary") & (X["sd"].estimand == "att")].iloc[0]
    verdict = "MET" if h5["rule_met"] else "NOT MET"
    return "\n".join([
        "## 3. H5 (secondary): the Indo-Gangetic Plain coefficient", "",
        "> **H5** (registered): effects are smaller (less negative) in IGP cities, where regional sources dominate. "
        "Rule (plan §5, read in DEC-135/164): the IGP coefficient's 95% credible interval lies entirely above 0.",
        ">",
        f"> **The registered rule is {verdict}:** β_IGP = {lg(h5['beta_igp'])} ({pc(h5['beta_igp'])}), 95% CrI {h5['lo95']:+.4f} to {h5['hi95']:+.4f} "
        f"({ci_pct(h5['lo95'], h5['hi95'])}).",
        ">",
        "> H1 is not identified by this design, so β_IGP is a difference in **city-level relative changes** between IGP units and "
        "peninsular/other + north-east units with the same other moderators. It is not a difference in NCAP effects, and it says nothing "
        "about whether NCAP worked less in the IGP.", "",
        "Every model (only the primary decides; DEC-164):", "", md(pd.DataFrame(rows)), "",
        f"*Context (Phase 7, not part of the rule):* excluding IGP units from both groups moved the Layer A estimate from {pc(prim.att)} to "
        f"{pc(noigp.est)} ({ci_pct(noigp.lo95, noigp.hi95)}). IGP membership and baseline PM2.5 correlate at r = {cbi:.2f} across the "
        "113 units, so the primary model compares IGP and other units of similar baseline pollution, while the IGP-only model does not; "
        "and its reference group also contains the coastal units. Both differences can move the IGP coefficient; which one does is not "
        "tested here. A regional coefficient also mixes in anything that happened to the whole "
        "region after 2018 (crop-residue burning, transport, weather), which the per-unit estimates share.", ""])  # fmt: skip


def section_cities(X: dict) -> str:
    c = X["c"][X["c"].version == "primary"].copy()
    c = c.sort_values("ncap_cities", key=lambda s: s.str.lower())
    rows = [{"NCAP unit (cities)": r.ncap_cities.replace(";", ", "), "region": REGION.get(r.region, r.region), "cohort": int(r.cohort),
             "shrunken relative change (%)": pc(r.post_mean), "95% CrI (%)": ci_pct(r.post_lo95, r.post_hi95),
             "P(< 0)": f"{r.p_lt0:.2f}", "95% rank interval": f"{r.rank_lo95:.0f}–{r.rank_hi95:.0f}"} for r in c.itertuples()]  # fmt: skip
    return "\n".join([
        "## 4. Shrunken city-level relative changes, every NCAP unit (alphabetical)", "",
        "Listed alphabetically, never ranked; there is no best/worst table (plan §5). Rank 1 = the largest relative fall. " + NOT_ID +
        " Each value is the unit's satellite PM2.5 after listing relative to its own synthetic comparison of non-NCAP centres, pulled "
        "towards what the moderators predict.", "",
        md(pd.DataFrame(rows)), ""])  # fmt: skip


def section_h3(X: dict) -> str:
    h3, b, r, ii, lb = X["h3"], X["b"], X["r"], X["ii"], X["lb"]
    cond = [
        {"condition": "(i) log(PM2.5/PM10) estimate > 0 with 95% CI above 0, ITS and DiD (co-located stations, deweathered)",
         "met": "yes" if h3["i_met"] else "no"},
        {"condition": "(ii) β_PM10 < β_PM2.5 and β_PM10 < 0 in ≥ 2 of 3 specifications, for both estimators",
         "met": ("yes" if h3["ii_met"] else "no") + f" (ITS {h3['ii_count'].get('ITS', 0)} of 3; DiD {h3['ii_count'].get('DiD', 0)} of 3)"},
        {"condition": "(iii) neither Phase 7 triangulation pair is 'conflict' (DEC-150)",
         "met": ("yes" if h3["iii_met"] else "no") + " (" + "; ".join(f"{k}: {v}" for k, v in h3["iii_categories"].items()) + ")"},
    ]  # fmt: skip
    brows = []
    for (spec, est), g in b.groupby(["spec", "estimator"], sort=False):
        x25, x10 = g[g.pollutant == "pm25"].iloc[0], g[g.pollutant == "pm10"].iloc[0]
        w = ii[(ii.spec == spec) & (ii.estimator == est)].iloc[0]
        brows.append({"specification": spec, "estimator": est + (f" ({x25.did_level})" if est == "DiD" else ""),
                      "PM2.5 (95% CI)": f"{pc(x25.est)} ({ci_pct(x25.lo95, x25.hi95)})", "PM10 (95% CI)": f"{pc(x10.est)} ({ci_pct(x10.lo95, x10.hi95)})",
                      "PM10 fell, and more": "yes" if w.pm10_fell_more else "no",
                      "cities (single-station) / control cities": f"{int(x25.cities)} ({int(x25.single_station_cities)}) / {int(x25.control_cities)}"})  # fmt: skip
    rrows = [{"series": x.series, "estimator": x.estimator, "estimate (log)": lg(x.est), "ratio change (95% CI)": f"{pc(x.est)} ({ci_pct(x.lo95, x.hi95)})",
              "cities / stations / control cities": f"{int(x.cities)} / {int(x.stations)} / {int(x.control_cities)}"} for x in r.itertuples()]  # fmt: skip
    own = []
    for spec, ver in (("raw", "all_stations_raw"), ("deweathered", "all_stations"), ("balanced panel", "primary")):
        for est in ("ITS", "DiD, city means" if ver != "primary" else "DiD"):
            g = lb[(lb.version == ver) & (lb.estimator == est)]
            if len(g) == 2:
                d = {p: g[g.pollutant == p].iloc[0] for p in ("pm25", "pm10")}
                own.append({"specification": spec, "estimator": est, **{f"{POLN[p]} (own cities)": f"{pc(d[p].est)} ({int(d[p].cities_used)} cities)" for p in d}})
    return "\n".join([
        "## 5. H3 (secondary, mechanism): PM10 vs PM2.5 on the ground", "",
        "> **H3** (registered): if dust control dominated action, PM10 fell more than PM2.5 in enrolled cities, and the PM2.5/PM10 ratio rose. "
        "Labelled 'consistent with dust control' only if (i)–(iii) all hold; otherwise 'inconclusive'; never 'confirmed'.",
        ">",
        f"> **Verdict: {h3['verdict']}.**",
        ">",
        "> Condition (iii) was already known to fail before this phase's rules were written (DEC-159, DEC-165), so H3 was going to be "
        "inconclusive whatever (i) and (ii) showed. Layer B is secondary, with one pre-year, and none of these is an effect of NCAP (H1 is not identified).", "",
        md(pd.DataFrame(cond)), "",
        "**(ii) on the cities that hold both pollutants** (DEC-165; raw = all stations raw, deweathered = all stations deweathered, balanced panel = "
        "the Layer B primary; ITS = after listing minus before, DiD = against control-pool cities; 95% cluster-bootstrap CIs):", "",
        md(pd.DataFrame(brows)), "",
        "**(i) the ratio**, on stations in both strict 2018 panels:", "", md(pd.DataFrame(rrows)), "",
        "Phase 7's values, each pollutant on its own cities (not used for the rule):", "", md(pd.DataFrame(own)), "",
        "*Scope:* the cities with both pollutants are a subset of Layer B's 18 (PM2.5) and 13 (PM10) cities, mostly single stations, against "
        "5 control cities. The audit's missingness bias on annual means (median +0.5 to +0.7%) applies. Ground PM10 is never set against "
        "satellite PM2.5 as agreement.", ""])  # fmt: skip


def section_dose(X: dict) -> str:
    du, dc, dd, ws = X["du"], X["dc"], X["dd"], X["ws"]
    inc = du[du.excluded.fillna("") == ""]
    exc = du[du.excluded.fillna("") != ""]
    rows = []
    for v in dd.itertuples():
        if not v.converged:
            rows.append({"model": v.label, "units": int(v.units), "per doubling of the dose": "not converged"})
            continue
        r = dc[(dc.version == v.version) & (dc.param == "per doubling of dose")].iloc[0]
        rows.append({"model": v.label, "units": int(v.units), "per doubling of the dose (log)": lg(r["mean"]),
                     "as % (95% CrI)": f"{pc(r['mean'])} ({ci_pct(r.lo95, r.hi95)})", "P(> 0)": f"{r.p_gt0:.3f}"})  # fmt: skip
    wsr = ws[ws["count"] >= 2]
    return "\n".join([
        "## 6. Funding dose-response (EXPLORATORY; DEC-166)", "",
        "*Exploratory, not a hypothesis test.* H1 is not identified by this design (Phase 7, DEC-151), so this relates city-level relative changes, not effects of NCAP, to money." +
        " Dose = XV Finance Commission air-quality **allocation** (FY2020-21 + FY2021-26) per person, not releases: XV-FC releases reward "
        "cities that improved (reverse causality). Allocations avoid that link but not every reverse-causal path.", "",
        f"- Units with a dose: **{len(inc)}** NCAP units (all their cities XV-FC, matched to an allocation row). "
        f"Excluded: {'; '.join(f'{r.ncap_cities.replace(';', ', ')} ({r.excluded})' for r in exc.itertuples())}. NCAP-channel cities have no "
        "allocation table in the extracted documents, so they have no dose.",
        f"- Dose range: Rs {inc.rs_per_person.min():,.0f} to Rs {inc.rs_per_person.max():,.0f} per person (median Rs {inc.rs_per_person.median():,.0f}).",
        f"- **Per-person allocations are set largely state by state:** in the {len(wsr)} states with two or more UAs, the within-state range "
        f"is a median {wsr.range_pct_of_mean.median():.1f}% of the state mean (maximum {wsr.range_pct_of_mean.max():.1f}%), while state means run from "
        f"Rs {ws['mean'].min():,.0f} to Rs {ws['mean'].max():,.0f}. So the dose is confounded with state and region.", "",
        md(pd.DataFrame(rows)), ""])  # fmt: skip


def build(X: dict) -> str:
    return "\n".join([
        "# Heterogeneity and mechanism (Phase 8, RQ4)", "",
        "*Generated by `python -m src.hierarchical.report` from `data/processed/hierarchical/`. Do not edit by hand. Rules: the registered plan "
        "(`docs/analysis_plan.md` at `6e24eca`, https://osf.io/jksne/) §5, read as in DEC-135, with the gaps filled before any estimate in "
        "DEC-162 to DEC-166 (pushed in `2f80dc4` before computing). Estimates are on log concentration; negative = a fall; % = 100 × (e^β − 1).*", "",
        "**Read this first.** H1 is *not identified by this design* (Phase 7): the registered pre-trend test failed. So no number in this "
        "report is an effect of NCAP. The per-unit numbers are **city-level relative changes**: how a unit's satellite PM2.5 moved after "
        "listing relative to its own synthetic comparison of non-NCAP centres. H5 is a statement about those relative changes, not about "
        "where NCAP worked.", "",
        section_estimates(X), section_model(X), section_h5(X), section_cities(X), section_h3(X), section_dose(X),
        "## Figures", "",
        "- Figure 5, `reports/figures/fig5_city_map.{png,svg}`: maps of the shrunken city-level relative changes, their CrI widths and P(< 0).",
        "- Figure 6, `reports/figures/fig6_shrinkage.{png,svg}`: per-unit estimates before and after shrinkage, and rank intervals (no names).",
        "- Figure 7, `reports/figures/fig7_mechanism.{png,svg}`: PM2.5 vs PM10 on the ground, and the ratio (H3).", ""])  # fmt: skip


def main() -> None:
    X = load()
    (DOCS / "heterogeneity_report.md").write_text(build(X), encoding="utf-8")
    print("H5:", X["h5"]["verdict"], "| H3:", X["h3"]["verdict"])


if __name__ == "__main__":
    main()

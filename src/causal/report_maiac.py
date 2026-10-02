"""§12 of docs/causal_report.md: the raw MAIAC AOD check (Phase 8b; DEC-174 to DEC-183). Imported by
src/causal/causal_report.py; every number comes from data/processed/causal/maiac/.

Wording (DEC-154, DEC-181): nothing is an effect of NCAP; "H1 is not identified by this design" sits beside every
estimate; AOD results are % changes in AOD, never PM2.5, and are read for direction only (DEC-180).
"""

import json

import pandas as pd

from src.causal import layer_a as A
from src.causal.report_part_b import ci_pct, lg, md, pc

MOUT = A.OUT / "maiac"
CAVEAT = "H1 is not identified by this design; not an effect of NCAP"

MEANING = {  # DEC-180, written before any AOD value
    "rise_in_aod": "The relative rise of NCAP units also appears in a signal that no ground monitor calibrates, so ACAG's calibration did not produce it. (Leakage as hypothesised pulls units that gained monitors down, so it could not have produced a rise anyway; Q1 tests ACAG's processing more broadly.)",
    "opposite": "Raw AOD does not show the rise. Either something in ACAG's processing produced it, or the link between column AOD and surface PM2.5 changed differently in NCAP units (boundary layer, humidity, aerosol mix). This check cannot tell which.",
    "not_reproduced": "Raw AOD does not show the rise. Either something in ACAG's processing produced it, or the link between column AOD and surface PM2.5 changed differently in NCAP units (boundary layer, humidity, aerosol mix). This check cannot tell which.",
    "gap_reproduced": "Units that gained monitors also rose less in a monitor-free signal, so calibration leakage is an unlikely explanation for the gap. Real differences between the two groups (size, pollution, the AOD–PM link) remain.",
    "gap_absent": "The gap is not in the monitor-free signal. That is what calibration leakage would produce. It is consistent with leakage, not proof: a group difference in the AOD–PM link would look the same.",
    "uninformative": "AOD is too noisy here to tell.",
    "not_testable": "The comparison cannot be made on this sample (reason in the label).",
    "not_estimated": "Not estimated for this specification (DEC-182).",
}


def have() -> bool:
    return (MOUT / "results.json").exists()


def results() -> dict:
    return json.loads((MOUT / "results.json").read_text(encoding="utf-8"))


def est(t) -> str:
    a, lo, hi = t
    return f"{lg(a)} ({pc(a)}; 95% CI {ci_pct(lo, hi)})"


def robustness_row() -> dict:
    """The "Raw MAIAC AOD" row of §9 (DEC-181): not on the PM2.5 scale, so "agrees" is not applicable."""
    r = results()["specs"]["aod_primary"]
    a, lo, hi = r["aod"]
    return {"layer": "A", "check": "Raw MAIAC AOD", "status": "registered", "est": a, "lo95": lo, "hi95": hi, "agrees": None,
            "note": (f"log AOD, not PM2.5: direction only, 'agrees' not applicable (DEC-180/181); {r['n_treated']} treated, "
                     f"{r['n_controls']} controls; Q1: {r['q1']['label']}; Q2: {r['q2']['label']}; ACAG on the same units "
                     f"{pc(r['acag'][0])}; {CAVEAT}")}  # fmt: skip


def investigation_row() -> dict | None:
    """Step 2 of the registered investigation (DEC-181): Layer A restricted on raw AOD."""
    s = pd.read_csv(MOUT / "sdid_summary.csv").set_index(["spec_id", "estimand"])
    if ("aod_restricted", "att") not in s.index:
        return None
    r = s.loc[("aod_restricted", "att")]
    return {"step": 2, "quantity": f"Layer A restricted, raw MAIAC AOD (log AOD; direction only; {int(r.n_treated)} units)",
            "est": r.att, "lo95": r.lo95, "hi95": r.hi95, "note": "AOD, not PM2.5 (DEC-180)"}  # fmt: skip


def section() -> str:
    R = results()
    s = pd.read_csv(MOUT / "sdid_summary.csv").set_index(["spec_id", "estimand"])
    wc = json.loads((MOUT / "weight_check.json").read_text(encoding="utf-8"))
    samp = pd.read_csv(MOUT / "sample.csv")
    cov = pd.read_csv(MOUT / "coverage_by_month.csv")
    p = R["specs"]["aod_primary"]
    L = ["## 12. Raw MAIAC AOD (Phase 8b; registered \"if time allows\" under calibration leakage)", "",
         "*Rules: DEC-174 to DEC-183, committed and pushed (`85acc2a`) before any AOD value was pulled.* MODIS MAIAC MCD19A2 C6.1 "
         "aerosol optical depth at 0.55 µm, 1 km, best-quality retrievals, reduced on Google Earth Engine to population-weighted "
         "unit-month means over the same GHSL polygons as Layer A, then annual means. AOD uses no ground monitor. **AOD is a column "
         "measure, not surface PM2.5: this check reads direction, not size (DEC-180).** Every estimate below is a relative change in "
         f"AOD of listed units against their synthetic comparison. **{CAVEAT}.**", ""]  # fmt: skip
    # data
    L += ["### 12a. Data, weights and coverage", "",
          f"- **Population weights** (GHS-POP R2023A 2020, 100 m, summed onto the MODIS grid in GEE) against Phase 3's 30″ GHS-POP sums "
          f"over the same {wc['units']} polygons: median difference {wc['median_pct']:+.1f}%, median absolute {wc['median_abs_pct']:.1f}% "
          f"(90th percentile {wc['p90_abs_pct']:.1f}%; stop rule > {wc['limit_pct']}%): **{'passed' if wc['passed'] else 'FAILED'}**.",
          "- **Valid unit-month:** ≥ 50% of the unit's population under pixels with a value, and ≥ 4 population-weighted valid days. "
          "**Valid year:** ≥ 6 of the 8 non-monsoon months (January–May, October–December). **Kept unit:** valid every year 2010–2019 "
          "and 2021–2024. Nothing is imputed (DEC-177).", ""]  # fmt: skip
    cols = [c for c in samp.columns if c.startswith("complete_")]
    t = samp.groupby("role_a")[cols].sum().astype(int).T
    t.index = [c.replace("complete_", "") for c in t.index]
    n = samp.role_a.value_counts()
    L += ["Units kept per AOD series (of 113 treated and 923 controls):", "",
          md(t.reset_index().rename(columns={"index": "series", "treated": f"treated (of {n.get('treated', 0)})",
                                             "control": f"controls (of {n.get('control', 0)})"})), ""]  # fmt: skip
    k = samp[samp.role_a == "treated"].assign(gained=lambda x: x.gained_monitor.map({True: "gained", False: "not gained"}))
    g = k.groupby("gained").complete_aod_popw.agg(["sum", "size"]).astype(int)
    rg = samp.groupby(["region", "role_a"]).complete_aod_popw.agg(["sum", "size"]).astype(int).reset_index()
    rg["kept"] = [f"{a} of {b}" for a, b in zip(rg["sum"], rg["size"], strict=True)]
    L += ["Kept by region (primary series):", "", md(rg.pivot(index="region", columns="role_a", values="kept").reset_index()), "",
          "Kept treated units by monitor-gain group: " + "; ".join(f"{i} {r['sum']} of {r['size']}" for i, r in g.iterrows()) + ".", ""]  # fmt: skip
    if R["limited_coverage"]:
        L += ["**Limited coverage:** fewer than half of the 113 treated units are kept, so every AOD result below carries that label (DEC-177).", ""]
    cv = cov.pivot(index="month", columns="region", values="share_valid").map(lambda v: f"{100 * v:.0f}%").reset_index()
    L += ["Share of unit-months valid, by calendar month and region (primary filter, all 1,036 units, 2010–2024):", "", md(cv), ""]
    # estimates
    L += ["### 12b. Estimates (SDID, Layer A's design; 500 joint-placebo replications each)", "",
          f"Listing cohorts, never-treated controls, 2010–2024 without 2020 (DEC-139/179). Each AOD row has beside it ACAG PM2.5 "
          f"estimated on exactly the same units (the yardstick). **{CAVEAT}.**", ""]  # fmt: skip
    rows = []
    for sid, rec in R["specs"].items():
        rows.append({"specification": s.loc[(sid, "att")].label, "units (treated / controls)": f"{rec['n_treated']} / {rec['n_controls']}",
                     "AOD: estimate (95% CI)": f"{pc(rec['aod'][0])} ({ci_pct(*rec['aod'][1:])})",
                     "ACAG on the same units": f"{pc(rec['acag'][0])} ({ci_pct(*rec['acag'][1:])})", "Q1": rec["q1"]["label"]})  # fmt: skip
    L += [md(pd.DataFrame(rows)), ""]
    L += [f"Primary in log units: AOD {est(p['aod'])}, SE {p['se']:.4f}; 2.8 × SE = {2.8 * p['se']:.4f}. ACAG on the same units {est(p['acag'])}. "
          f"Layer A's primary on all 113 / 923 units: +3.6% (§1).", ""]  # fmt: skip
    if "diff" in p:
        L += ["**Monitor-gain split (DEC-146 design, on AOD):**", "",
              md(pd.DataFrame([
                  {"group": f"gained a monitor 2019–2024 ({p['n_gained']} units)", "AOD": f"{pc(p['gained'][0])} ({ci_pct(*p['gained'][1:])})",
                   "ACAG, same units": f"{pc(p['acag_gained'][0])} ({ci_pct(*p['acag_gained'][1:])})"},
                  {"group": f"did not ({p['n_notgained']} units)", "AOD": f"{pc(p['notgained'][0])} ({ci_pct(*p['notgained'][1:])})",
                   "ACAG, same units": f"{pc(p['acag_notgained'][0])} ({ci_pct(*p['acag_notgained'][1:])})"},
                  {"group": "difference, gained − not gained", "AOD": f"{pc(p['diff'][0])} ({ci_pct(*p['diff'][1:])})",
                   "ACAG, same units": f"{pc(p['acag_diff'][0])} ({ci_pct(*p['acag_diff'][1:])})"},
              ])), "",
              f"AOD difference in log units {est(p['diff'])}, SE {p['diff_se']:.4f} (2.8 × SE = {2.8 * p['diff_se']:.4f}). {CAVEAT}.", ""]  # fmt: skip
    # classification
    L += ["### 12c. The pre-specified reading (DEC-180)", "",
          f"> **Q1, does the relative rise appear in AOD? {p['q1']['label'][0].upper() + p['q1']['label'][1:]}.** {MEANING[p['q1']['code']]}",
          ">",
          f"> **Q2, does the gained/not-gained gap appear in AOD? {p['q2']['label'][0].upper() + p['q2']['label'][1:]}.** {MEANING[p['q2']['code']]}",
          ">",
          f"> {CAVEAT[0].upper() + CAVEAT[1:]}: the verdict rests on the failed pre-trend test (rule b), which this check does not touch.", ""]  # fmt: skip
    if R["limited_coverage"]:
        L += ["*Limited coverage (DEC-177): fewer than half of the treated units are kept.*", ""]
    # event study
    es = R.get("event_study")
    if es:
        c = pd.read_csv(MOUT / "event_study" / "es_aod_coefs.csv")
        w, a = es["wald_pre"], es["avg_post"]
        L += ["### 12d. Event study on log AOD (information only; decides nothing)", "",
              f"Sun & Abraham as §4 (unit and region × year effects, ERA5 covariates, SEs clustered by unit), {es['n_units']} units, "
              f"{es['n_obs']} unit-years. Pre-trend Wald χ² = {w['stat']:.2f} on {w['df']} df, p = {w['p']:.4f}; average post-period "
              f"estimate {pc(a['coef'])} (95% CI {ci_pct(a['lo95'], a['hi95'])}). Rule (b) belongs to H1 and is unchanged. {CAVEAT}.", "",
              md(pd.DataFrame({"rel": c.rel, "cohorts": c.cohorts, "AOD %": c.coef.map(pc),
                               "95% CI (%)": [ci_pct(x, y) for x, y in zip(c.lo95, c.hi95, strict=True)]})), ""]  # fmt: skip
    L += ["### 12e. Caveats", "",
          "- AOD is the whole atmospheric column; surface PM2.5 also depends on boundary-layer height, humidity and aerosol type. A "
          "change in that link that differs between NCAP and comparison units would move AOD without moving PM2.5, or the reverse.",
          "- Best-quality retrievals need clear skies, so AOD describes clear days. MAIAC can flag thick winter haze or smoke as cloud; "
          "the relaxed-filter row shows how much that matters.",
          "- Units without a complete AOD series are dropped; the ACAG yardstick on the same units separates that sample change "
          "from a difference between the two products.",
          "- Terra's and Aqua's overpass times drifted late in the period. That affects every unit alike unless the daily cycle "
          "of aerosol differs between NCAP and comparison units.",
          f"- {CAVEAT[0].upper() + CAVEAT[1:]}.", ""]  # fmt: skip
    return "\n".join(L)


"""Part B sections of docs/causal_report.md, and the additions from Reenu's Part A review (DEC-154 to DEC-157).
Imported by src/causal/causal_report.py. Every number comes from pipeline outputs.

Wording rule (DEC-154): the positive Layer A estimates are never described as an effect of NCAP.
"""

import math

import pandas as pd

from src.causal import decisions as D
from src.causal import layer_a as A
from src.common.paths import INTERIM
from src.normalise.composition import OUT as C_OUT

LB = A.OUT / "layer_b"
POLN = {"pm25": "PM2.5", "pm10": "PM10"}


def pc(x: float, d: int = 1) -> str:
    return f"{D.pct(x):+.{d}f}%"


def lg(x: float) -> str:
    return f"{x:+.4f}"


def ci_pct(lo: float, hi: float, d: int = 1) -> str:
    return f"{D.pct(lo):+.{d}f}% to {D.pct(hi):+.{d}f}%"


def md(df: pd.DataFrame) -> str:
    cols = list(df.columns)
    out = ["| " + " | ".join(map(str, cols)) + " |", "|" + "---|" * len(cols)]
    out += ["| " + " | ".join("" if pd.isna(v) else str(v) for v in r) + " |" for r in df.itertuples(index=False)]
    return "\n".join(out)


def have_part_b() -> bool:
    files = [A.OUT / f for f in ("robustness.csv", "triangulation.csv", "investigation.csv")] + [LB / "estimates.csv"]
    return all(f.exists() for f in files)


def city_names() -> pd.Series:
    from src.viz.fig3_deweathered import names

    return names()


# ---------------------------------------------------------------- review additions


def section_descriptive() -> str:
    d = pd.read_csv(A.OUT / "levels.csv")
    lines = ["### 1c. Descriptive context (descriptive; no effect is computed)", "",
             "Mean annual population-weighted PM2.5 (ACAG V5.GL.06, µg/m³) over the 113 NCAP units and the 923 control-pool "
             "units, unweighted across units, with a 95% t-interval and the median; 2020 included (DEC-154). Figure: "
             "`reports/figures/figS1_levels`.", ""]  # fmt: skip
    d["v"] = [f"{m:.1f} ({a:.1f} to {b:.1f}); median {q:.1f}" for m, a, b, q in zip(d["mean"], d.lo95, d.hi95, d["median"], strict=True)]
    t = d.pivot(index="year", columns="group", values="v").reset_index()
    lines += [md(t[["year", "NCAP units", "control pool"]]), ""]
    m = d.pivot(index="year", columns="group", values="mean")
    ch = {g: 100 * (m.loc[2024, g] / m.loc[2018, g] - 1) for g in m.columns}
    ch10 = {g: 100 * (m.loc[2018, g] / m.loc[2010, g] - 1) for g in m.columns}
    lines += [f"From 2018 to 2024 the NCAP units' mean went from {m.loc[2018, 'NCAP units']:.1f} to {m.loc[2024, 'NCAP units']:.1f} µg/m³ "
              f"({ch['NCAP units']:+.1f}%) and the control pool's from {m.loc[2018, 'control pool']:.1f} to "
              f"{m.loc[2024, 'control pool']:.1f} ({ch['control pool']:+.1f}%); from 2010 to 2018, {ch10['NCAP units']:+.1f}% and "
              f"{ch10['control pool']:+.1f}%. **Both groups fell after 2018; the control pool fell more.** These are raw means of "
              "groups that differ in size and region: context, not an estimate.", ""]  # fmt: skip
    return "\n".join(lines)


def leakage_mechanism() -> str:
    """DEC-154 item 4: the leakage result beside the Phase 3/6 finding that new stations read cleaner."""
    e = pd.read_csv(C_OUT / "entrants_summary.csv")
    e = e[(e.year == "all") & (e.pollutant == "pm25")].set_index("measure")
    p3 = pd.read_csv(INTERIM / "eda" / "entrants.csv")
    p3 = p3[(p3.year == "all") & (p3.pollutant == "pm25")].iloc[0]
    r, dw = e.loc["lr_raw"], e.loc["lr_dw_gam"]
    return (f"**A possible mechanism the design cannot test.** Phases 3 and 6 found that new CAAQMS stations read cleaner than the "
            f"existing stations of the same city and year: PM2.5 {p3.mean_pct:+.1f}% in Phase 3 (raw), and in Phase 6 "
            f"{r.mean_pct:+.1f}% raw (95% CI {r.lo_pct:+.1f} to {r.hi_pct:+.1f}) and {dw.mean_pct:+.1f}% deweathered "
            f"({dw.lo_pct:+.1f} to {dw.hi_pct:+.1f}): the gap is about where the new monitors stand, not the weather. If ACAG's "
            "calibration absorbed those cleaner readings, the satellite values of the units that gained monitors would be pulled down, "
            "which is the direction of the difference above. This design cannot test it: the calibration inputs are not observed "
            "here, and the two groups also differ in size and pollution. The V6.GL.02.04 vintage, calibrated to an earlier monitor "
            "set, is the registered related check (§9).")


# ---------------------------------------------------------------- Layer B


def b_rows(e: pd.DataFrame, version: str, pol: str) -> pd.DataFrame:
    rows = []
    for _, r in e[(e.version == version) & (e.pollutant == pol)].iterrows():
        if not bool(r.computable) or pd.isna(r.get("est")):
            rows.append({"estimator": r.estimator, "estimate (log)": "", "estimate (%)": "not computable", "95% CI (%)": "", "cities used": ""})
            continue
        rows.append({"estimator": r.estimator, "estimate (log)": lg(r.est), "estimate (%)": pc(r.est), "95% CI (%)": ci_pct(r.lo95, r.hi95),
                     "cities used": "" if pd.isna(r.get("cities_used")) else int(r.cities_used)})  # fmt: skip
    return pd.DataFrame(rows)


def section_layer_b() -> str:
    e = pd.read_csv(LB / "estimates.csv")
    mb = pd.read_csv(INTERIM / "audit" / "missingness_bias.csv").groupby("pollutant").bias_pct.median()
    lines = ["## 7. Layer B (ground; secondary)", "",
             "Deweathered city-year series on the strict balanced panel (stations inside the polygon, valid every year 2018–2025): "
             "the same stations as H4 (DEC-148). **ITS** = each NCAP city's mean log level after listing minus before (2020 excluded), "
             "averaged over cities. **Ground DiD** = NCAP stations against control-pool stations, per listing cohort, station and year "
             "effects. 95% CIs from a cluster bootstrap over cities (1,000; the DiD's stratified by cohort and control). **Secondary, "
             "with one pre-year:** parallel trends cannot be tested, and the ITS cannot separate national shocks from anything else.", ""]  # fmt: skip
    for pol in ("pm25", "pm10"):
        r0 = e[(e.version == "primary") & (e.pollutant == pol) & (e.estimator == "ITS")].iloc[0]
        lines += [f"**{POLN[pol]}.** Scope: {int(r0.cities)} NCAP cities ({int(r0.single_station_cities)} with a single panel station; "
                  f"{int(r0.stations)} stations) against {int(r0.control_cities)} control-pool cities ({int(r0.control_stations)} stations); "
                  "not NCAP cities in general. Deweathered values exclude each station's unmodelled change (DEC-136). The audit's "
                  f"missingness bias on annual means (median {mb.get(pol, float('nan')):+.1f}%, `audit_report.md`) applies to these series.", "",
                  md(b_rows(e, "primary", pol)), ""]  # fmt: skip
    lines += ["The \"2020 own coefficient\" rows are the 2020 level against the pre-years (ITS) or its treated-minus-control version "
              "(DiD); the 2020 term leaves the other estimates unchanged by construction (DEC-148).", ""]  # fmt: skip
    its = pd.read_csv(LB / "its_cities.csv")
    its = its[its.version == "primary"].copy()
    its["city"] = its.unit_id.map(city_names()).fillna(its.unit_id)
    its["pollutant"] = its.pollutant.map(POLN)
    its = its.sort_values(["pollutant", "d"])
    lines += ["Per city (ITS, primary). **Descriptive:** no city-level claim is made here (plan §5).", "",
              md(pd.DataFrame({"pollutant": its.pollutant, "city": its.city, "ITS (log)": its.d.map(lg), "ITS (%)": its.d.map(pc)})), ""]  # fmt: skip
    return "\n".join(lines)


def section_triangulation() -> str:
    t = pd.read_csv(A.OUT / "triangulation.csv")
    inv = pd.read_csv(A.OUT / "investigation.csv")
    lines = ["## 8. Triangulation between the layers (PM2.5 only; never averaged)", "",
             "Layer A restricted to the units with a Layer B PM2.5 panel, against the ground DiD (the like-for-like pair) and the ITS, "
             "classified in DEC-135's fixed order. The windows differ: satellite post-years 2019 and 2021–2024, ground 2019 and "
             "2021–2025 (DEC-150).", ""]  # fmt: skip
    lines += [md(pd.DataFrame({"pair": t.pair,
                               "Layer A restricted": [f"{pc(a)} ({ci_pct(lo, hi)}), {u} units" for a, lo, hi, u in zip(t.a_est, t.a_lo95, t.a_hi95, t.a_units, strict=True)],
                               "Layer B": [f"{pc(a)} ({ci_pct(lo, hi)}), {c} cities" for a, lo, hi, c in zip(t.b_est, t.b_lo95, t.b_hi95, t.b_cities, strict=True)],
                               "category": t.category,
                               "investigation": t.investigate.map({True: "triggered", False: "not needed"})})), ""]  # fmt: skip
    if t.investigate.any():
        def val(r):
            if pd.isna(r.lo95):
                return f"{r.est:+.2f}"
            return f"{pc(r.est)} ({ci_pct(r.lo95, r.hi95)})"
        lines += ["**The registered investigation** (steps 1 network composition, 2 satellite calibration, 3 spatial coverage, "
                  "4 deweathering; every step reported whether or not it closes the gap):", "",
                  md(pd.DataFrame({"step": inv.step, "quantity": inv.quantity, "value": [val(r) for r in inv.itertuples()]})), ""]  # fmt: skip
    return "\n".join(lines)


def section_robustness() -> str:
    r = pd.read_csv(A.OUT / "robustness.csv")

    def est(x):
        if pd.isna(x.est):
            return ""
        if str(x.check).startswith("Placebo in space"):
            return f"p = {x.est:.3f}"
        return pc(x.est) + ("" if pd.isna(x.lo95) else f" ({ci_pct(x.lo95, x.hi95)})")

    lines = ["## 9. Every sensitivity check in the plan's table", "",
             "\"Agrees\" (DEC-135): same sign as the primary of its layer and the point estimate inside that primary's 95% CI. Layer A "
             "checks are set against the primary SDID; Layer B checks against the Layer B primary of the same estimator and pollutant. "
             "Every check is shown, whichever way it points.", ""]  # fmt: skip
    for layer, title in (("A", "Layer A (satellite)"), ("B pm25", "Layer B, PM2.5"), ("B pm10", "Layer B, PM10")):
        x = r[r.layer == layer]
        lines += [f"**{title}**", "",
                  md(pd.DataFrame({"check": x.check, "status": x.status.fillna(""), "estimate (95% CI)": [est(v) for v in x.itertuples()],
                                   "agrees": x.agrees.map({True: "yes", False: "**no**"}).fillna("—"), "note": x.note.fillna("")})), ""]  # fmt: skip
        a = x.agrees.dropna()
        if len(a):
            lines += [f"{int(a.astype(bool).sum())} of {len(a)} checks agree.", ""]
    lines += ["The 2019-baseline Layer B rows cover only the cities listed in 2020–2021 (DEC-157), so their \"agrees\" says little "
              "about the 2019 cohort.", ""]  # fmt: skip
    return "\n".join(lines)


def section_dec137() -> str:
    m = pd.read_csv(LB / "misfit_by_year.csv")
    e = pd.read_csv(LB / "estimates.csv")
    lines = ["## 10. Without 2019 (DEC-123), and the GAM's 2019-baseline unmodelled change (DEC-137)", "",
             "Mean over the treated Layer B panel stations of log(raw / fitted annual mean), per year: how far each family's fitted "
             "values miss the observed annual mean (positive = the fit is below the observation). Descriptive; no threshold was set "
             "(DEC-149).", ""]  # fmt: skip
    for pol in ("pm25", "pm10"):
        x = m[m.pollutant == pol].pivot_table(index="year", columns=["baseline", "family"], values="mean")
        x.columns = [f"baseline {b}, {'GAM' if f == 'gam' else 'LightGBM'}" for b, f in x.columns]
        lines += [f"*{POLN[pol]}*", "", md(x.map(lambda v: "" if pd.isna(v) else f"{v:+.3f}").reset_index()), ""]
    rows = []
    for pol in ("pm25", "pm10"):
        def get(v, pol=pol):
            return e[(e.version == v) & (e.pollutant == pol) & (e.estimator == "ITS")].iloc[0]

        for a, b, lab in (("primary", "lgbm", "baseline 2018, with 2019"), ("no2019", "no2019_lgbm", "baseline 2018, without 2019"),
                          ("base2019", "base2019_lgbm", "baseline 2019 (cities listed 2020–21 only, DEC-157)")):  # fmt: skip
            ra, rb = get(a), get(b)
            if bool(ra.computable) and bool(rb.computable) and pd.notna(ra.est) and pd.notna(rb.est):
                rows.append({"pollutant": POLN[pol], "version": lab, "ITS, GAM": pc(ra.est), "ITS, LightGBM": pc(rb.est),
                             "GAM − LightGBM (pp)": f"{D.pct(ra.est) - D.pct(rb.est):+.1f}"})  # fmt: skip
    lines += ["GAM against LightGBM, ITS:", "", md(pd.DataFrame(rows)), ""]
    return "\n".join(lines)


def section_exploratory(s: pd.DataFrame, specs: pd.DataFrame) -> str:
    u = pd.read_csv(A.OUT / "design_units.csv").set_index("unit_id")
    sp = pd.read_parquet(A.SPEC_DIR / "spec_units.parquet")
    lp = u.pop_2015.map(math.log10)
    rows = []
    for sid in ("primary", "explore_support_minmax", "explore_support_q5_95"):
        mem = sp[sp.spec_id == sid]
        t, c = lp.reindex(mem.unit_id[mem.role == "treated"]), lp.reindex(mem.unit_id[mem.role == "control"])
        smd = (t.mean() - c.mean()) / math.sqrt((t.var() + c.var()) / 2)
        r = s.loc[(sid, "att")]
        rows.append({"sample": specs.loc[sid, "label"], "treated": len(t), "controls": len(c), "log-population SMD": f"{smd:.2f}",
                     "estimate (log)": lg(r.att), "estimate (%)": pc(r.att), "95% CI (%)": ci_pct(r.lo95, r.hi95)})  # fmt: skip
    lines = ["## 11. Exploratory, added after seeing H1: overlapping ranges of 2015 population (DEC-155)", "",
             "*Not a decision rule; it cannot change the H1 verdict.* City size was the largest pre-registration imbalance "
             "(log-population SMD 1.44). Variant (i), min–max common support, drops the megacity units and the sub-100,000 towns but "
             "does not improve balance, because the control pool is concentrated at 100,000–200,000. Variant (ii) keeps the overlap of "
             "the 5–95% ranges, which halves the imbalance. Both use the primary design otherwise, with joint-placebo SEs from their "
             "own pools.", "", md(pd.DataFrame(rows)), ""]  # fmt: skip
    return "\n".join(lines)

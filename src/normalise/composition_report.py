"""docs/composition_report.md: the Phase 6 results (RQ1 and H4), generated from
data/processed/composition/ (src.normalise.composition, src.normalise.family_diag).

    python -m src.normalise.composition_report

Every number here comes from those tables. Rules: DEC-125 to DEC-131. Nothing contrasts NCAP with
non-NCAP units: all-city summaries show measurement quantities only; H4 is over NCAP units only.
"""

import numpy as np
import pandas as pd

from src.common.paths import DOCS, params
from src.normalise import composition as C
from src.normalise.pilot import md_table
from src.viz.fig3_deweathered import names

POL = {"pm25": "PM2.5", "pm10": "PM10"}
METRIC = {"comp_raw": "composition bias, raw (all − panel)", "comp_dw": "composition bias, deweathered",
          "weather": "weather part of the reported change", "composition": "composition part (deweathered)",
          "weather_pan": "weather part on the panel (other order)", "h4": "H4 (reported fall − corrected fall)",
          "h4_weather": "… of which weather", "h4_composition": "… of which composition",
          "reported": "reported change (all stations, raw)", "corrected": "corrected change (panel, deweathered)",
          "gap_panel_sat": "panel (raw) − satellite", "gap_all_sat": "all stations (raw) − satellite",
          "gap_panel_dw_sat": "panel (deweathered) − satellite",
          "gap_panel_sat_comparison": "panel (raw) − satellite V6.GL.03",
          "gap_panel_sat_area": "panel (raw) − satellite, area-weighted",
          "chg_panel_raw": "panel change (raw)", "chg_sat": "satellite change",
          "corr_panel_sat_changes": "correlation of panel and satellite changes across cities"}  # fmt: skip
GROUP_ORDER = ["boundary layer", "wind", "precipitation", "temperature", "humidity", "radiation", "calendar", "trend"]
VAR = {"temp": "temperature (°C)", "rh": "relative humidity (%)", "ws": "wind speed (m/s)",
       "blh_mean": "boundary layer, daily mean (m)", "blh_pm": "boundary layer, afternoon max (m)",
       "precip": "precipitation (mm/day)", "ssrd": "solar radiation (MJ/m²/day)"}  # fmt: skip
p1, p2 = "{:.1f}", "{:.2f}"


def ci(m, lo, hi, fmt="{:+.1f}") -> str:
    return f"{fmt.format(m)} ({fmt.format(lo)} to {fmt.format(hi)})" if pd.notna(lo) else fmt.format(m)


def city_name(nm: pd.Series, u: str) -> str:
    x = nm.get(u)
    return x if isinstance(x, str) else u


def summary_table(s: pd.DataFrame, labels: dict[str, str], group: str, metrics: list[str]) -> pd.DataFrame:
    rows = []
    for lab, name in labels.items():
        for pol in ("pm25", "pm10"):
            g = s[(s.spec == lab) & (s.pollutant == pol) & (s.group == group)].set_index("metric")
            r = {"version": name, "pollutant": POL[pol], "cities": int(g.n.iloc[0]) if len(g) else 0}
            for m in metrics:
                r[METRIC[m]] = ci(g.loc[m, "mean"], g.loc[m, "lo"], g.loc[m, "hi"]) if m in g.index else ""
            rows.append(r)
    return pd.DataFrame(rows)


def h4_rows(h: pd.DataFrame) -> pd.DataFrame:
    t = h.copy()
    t["H4, pp (95% CI)"] = [ci(a, b, c) for a, b, c in zip(t.h4_mean, t.h4_lo, t.h4_hi, strict=True)]
    t["2.8 × SE"] = t.detectable_2p8se.map(lambda x: "" if pd.isna(x) else f"{x:.1f}")
    t["supported"] = t.supported.map({True: "yes", False: "no"})
    tag = np.where(t.is_primary, " **(primary)**", np.where(t.is_as_registered, " **(as registered, no deviations)**", ""))
    t["version"] = t.description + tag
    t["pollutant"] = t.pollutant.map(POL)
    return t[["version", "pollutant", "cities", "reported_mean", "corrected_mean", "h4_weather_mean",
              "h4_composition_mean", "H4, pp (95% CI)", "2.8 × SE", "cities_positive", "supported"]].rename(columns={
        "reported_mean": "reported %", "corrected_mean": "corrected %", "h4_weather_mean": "weather pp",
        "h4_composition_mean": "composition pp", "cities_positive": "cities > 0"})  # fmt: skip


def verdict(h: pd.DataFrame, label: str, pol: str) -> str:
    r = h[(h.spec == label) & (h.pollutant == pol)]
    if r.empty:
        return f"{POL[pol]}: no NCAP city has a panel"
    r = r.iloc[0]
    s = (f"{POL[pol]}: {r.h4_mean:+.1f} pp (95% CI {r.h4_lo:+.1f} to {r.h4_hi:+.1f}; {int(r.cities)} cities, "
         f"{int(r.cities_positive)} positive) — {'supported' if r.supported else 'not supported'}")
    if pd.notna(r.detectable_2p8se):
        s += f"; smallest reliably detectable mean 2.8 × SE = {r.detectable_2p8se:.1f} pp"
    return s


def family_section(nm: pd.Series) -> list[str]:
    try:
        cities = pd.read_csv(C.OUT / "family_diag_cities.csv")
        chk = pd.read_csv(C.OUT / "family_diag_check.csv")
        att = pd.read_csv(C.OUT / "family_diag_attribution.csv")
        era = pd.read_csv(C.OUT / "family_diag_era5.csv")
        mf = pd.read_csv(C.OUT / "family_diag_misfit_h4.csv")
    except FileNotFoundError:
        return ["*Not run: `python -m src.normalise.family_diag`.*"]
    flag = C.ccfg()["family_flag_pp"]
    b, e = C.PRIMARY.baseline, C.ccfg()["end_year"]
    groups = [g for g in ["boundary layer", "wind", "precipitation", "temperature", "humidity", "radiation", "calendar"]
              if g in att.columns]  # fmt: skip
    out = [f"Cities: Kolkata, and every city whose GAM and LightGBM deweathered panel changes {b}–{e} differ by more "
           f"than {flag:g} pp under either scheme (primary rule, strict panel; every city with a panel, NCAP or not). "
           "Differences are GAM − LightGBM in pp:", ""]  # fmt: skip
    c = cities.assign(city=cities.city.fillna(cities.unit_id), pollutant=cities.pollutant.map(POL))
    out.append(md_table(c[["city", "pollutant", "n_panel", "chg_raw_panel", "chg_dw_gam_seasonal", "chg_dw_lgbm_seasonal",
                           "diff_pp_seasonal", "diff_pp_annual", "reason"]],
                        {"chg_raw_panel": "{:+.1f}", "chg_dw_gam_seasonal": "{:+.1f}", "chg_dw_lgbm_seasonal": "{:+.1f}",
                         "diff_pp_seasonal": "{:+.1f}", "diff_pp_annual": "{:+.1f}"}))  # fmt: skip
    k = chk[chk.scheme == "seasonal"]
    gap = (k.sum_of_parts - k.implied_weather_change).abs()
    a = att[att.scheme == "seasonal"]
    gap2 = (a.total - a.implied_weather_change).abs()
    out += ["", "### 5a. The method fixed in DEC-130 failed its own check, and what replaced it (DEC-133)", "",
            f"DEC-130 split each family's weather effect into variable groups on the **log scale** (GAM terms; LightGBM "
            f"TreeSHAP) and required the parts to add up to the implied weather change, 100 × change in "
            f"log(raw/deweathered). They do not: the gap is a median {gap.median():.1f} and up to {gap.max():.1f} points "
            f"over {len(k)} station × family pairs (seasonal scheme); for Kolkata's GAM (PM2.5) the parts sum to "
            f"{k[(k.city == 'Kolkata') & (k.pollutant == 'pm25') & (k.family == 'gam')].sum_of_parts.iloc[0]:+.1f} against "
            f"{k[(k.city == 'Kolkata') & (k.pollutant == 'pm25') & (k.family == 'gam')].implied_weather_change.iloc[0]:+.1f}. "
            "The reason: H4 and the deweathered change are changes in **arithmetic** annual means, where weather acting "
            "on the most polluted days counts for more than on the log scale, and a model's fitted values need not "
            "reproduce a station's arithmetic mean. The log-scale table is kept, unused, in `family_diag_contrib.csv`.",
            "",
            "**Replacement (on the annual-mean scale; adds up by construction).** For each group, the annual mean is "
            "recomputed with that group alone at the actual weather and every other group at the station's typical "
            f"weather ({C.ccfg()['diag_draws']} of the 500 shared draws); `joint` is what the groups do only together; "
            "`misfit` is the change in log(observed mean / the model's fitted mean): the part of the measured change "
            "the model reproduces neither with its trend nor with its weather terms. Deweathering drops the misfit, so "
            "raw − deweathered counts it as weather. Sum = the implied weather change, up to Monte-Carlo error: "
            f"median gap {gap2.median():.2f}, largest {gap2.max():.2f} points ({len(a)} station × family pairs).", ""]  # fmt: skip
    out += [f"### 5b. Which parts drive each family's weather effect, {b} → {e} (seasonal scheme)", "",
            "Changes × 100 (≈ %; negative = made the later year cleaner). `deweathered` = the family's deweathered "
            "change (%); raw change in the row header.", ""]  # fmt: skip
    rows = []
    for r in a.itertuples():
        city = r.city if isinstance(r.city, str) else r.unit_id
        d = {"city": city, "pollutant": POL[r.pollutant], "family": {"gam": "GAM", "lgbm": "LightGBM"}[r.family]}
        d.update({g: a.loc[r.Index, g] for g in groups})
        d.update({"joint": r.joint, "misfit": r.misfit, "total": r.total, "implied": r.implied_weather_change,
                  "deweathered": r.chg_dw, "raw": r.chg_raw})  # fmt: skip
        rows.append(d)
    t = pd.DataFrame(rows)
    fmt = {x: "{:+.1f}" for x in [*groups, "joint", "misfit", "total", "implied", "deweathered", "raw"]}
    out += [md_table(t, fmt), ""]
    # the headline difference per city: which part differs most between the families
    lines = []
    for (city, pol), g in t.groupby(["city", "pollutant"], sort=False):
        if set(g.family) != {"GAM", "LightGBM"}:
            continue
        gg, ll = g[g.family == "GAM"].iloc[0], g[g.family == "LightGBM"].iloc[0]
        diffs = {p: gg[p] - ll[p] for p in [*groups, "joint", "misfit"] if pd.notna(gg[p]) and pd.notna(ll[p])}
        top = max(diffs, key=lambda p: abs(diffs[p]))
        lines.append(f"- **{city}, {pol}:** families differ by {gg.deweathered - ll.deweathered:+.1f} pp in the deweathered "
                     f"change; the largest single part of that is **{top}** ({diffs[top]:+.1f} points; GAM {gg[top]:+.1f}, "
                     f"LightGBM {ll[top]:+.1f}).")  # fmt: skip
    out += ["**Largest difference per city** (GAM − LightGBM, seasonal scheme):", "", *lines, ""]
    m = mf.groupby(["pollutant", "unit_id", "family"]).misfit_change.mean().unstack()
    mm = m.groupby("pollutant").agg(["mean", "median", lambda s: s.abs().max()])
    out += [f"**The misfit across all H4 cities** (every panel station of the NCAP cities in H4; per-city mean, then "
            f"over cities; pp of the {b}–{e} change that raw − deweathered counts as weather although the model does "
            "not attribute it to weather): " + "; ".join(
                f"{POL[p]}: GAM mean {mm.loc[p, ('gam', 'mean')]:+.1f} (largest |city| {mm.loc[p, ('gam', '<lambda_0>')]:.1f}), "
                f"LightGBM mean {mm.loc[p, ('lgbm', 'mean')]:+.1f} (largest {mm.loc[p, ('lgbm', '<lambda_0>')]:.1f})"
                for p in ("pm25", "pm10") if p in mm.index)
            + ". A negative misfit change raises H4 (the model reproduces less of the fall than was measured). "
            "Compare these means with H4's weather part in §1.", ""]  # fmt: skip
    out += [f"### 5c. The actual ERA5 weather at each flagged station's cell ({b} → {e}; all complete days; cold "
            f"months = {', '.join(str(x) for x in C.ccfg()['cold_months'])})", "",
            "`Δ/SD` = the change in SDs of the station's 2015–2025 annual means; trend per decade by OLS over the 11 "
            "annual means (95% CI; autocorrelation ignored, descriptive); `r(year)` = correlation of the annual mean "
            "with the year. A higher boundary layer, faster wind or more rain lowers PM; for temperature, humidity and "
            "radiation the sign depends on season and place, so none is stated.", ""]  # fmt: skip
    ev = era.copy()
    ev["city"] = ev.city.where(ev.city.notna(), ev.unit_id)
    ev = ev.drop_duplicates(["unit_id", "season", "variable"])
    ev["variable"] = ev.variable.map(VAR)
    out.append(md_table(ev[["city", "season", "variable", "value_base", "value_end", "delta_sd", "slope_per_decade",
                            "slope_lo", "slope_hi", "corr_year"]].rename(columns={
        "value_base": str(b), "value_end": str(e), "delta_sd": "Δ/SD", "slope_per_decade": "trend/decade",
        "slope_lo": "lo", "slope_hi": "hi", "corr_year": "r(year)"}),
        {str(b): p1, str(e): p1, "Δ/SD": "{:+.1f}", "trend/decade": "{:+.2f}", "lo": "{:+.2f}", "hi": "{:+.2f}",
         "r(year)": p2}))  # fmt: skip
    out += ["", "**Consistency of each family's physically signed parts with the actual change** (annual means; "
            "`matches` = the part has the sign the actual change implies):", ""]
    cons = []
    ea = era[era.season == "annual"]
    for r in a.itertuples():
        city = r.city if isinstance(r.city, str) else r.unit_id
        ev2 = ea[(ea.sid == r.sid) & (ea.pollutant == r.pollutant)].set_index("variable")
        row = {"city": city, "pollutant": POL[r.pollutant], "family": {"gam": "GAM", "lgbm": "LightGBM"}[r.family]}
        for grp, v in (("boundary layer", "blh_mean"), ("wind", "ws"), ("precipitation", "precip")):
            exp_sign = ev2.loc[v, "expected_sign_of_pm_effect"] if v in ev2.index else np.nan
            part = a.loc[r.Index, grp]
            row[grp] = ("" if pd.isna(exp_sign) or exp_sign == 0 or abs(part) < 0.5 else
                        ("matches" if np.sign(part) == exp_sign else "opposite")) + f" ({part:+.1f}; Δ {ev2.loc[v, 'delta_sd']:+.1f} SD)"
        cons.append(row)
    cons = pd.DataFrame(cons)
    out.append(md_table(cons))
    tally = []
    for fam in ("GAM", "LightGBM"):
        for grp in ("boundary layer", "wind", "precipitation"):
            s = cons[cons.family == fam][grp]
            tally.append(f"{fam} {grp}: {int(s.str.startswith('matches').sum())} match, "
                         f"{int(s.str.startswith('opposite').sum())} opposite")  # fmt: skip
    out += ["", "Tally: " + "; ".join(tally) + ". Parts smaller than 0.5 points in absolute value are not given a sign.",
            "",
            "Reading: where a variable's part has the opposite sign to its actual change, the model's credit for that "
            "variable is not explained by the change in its annual mean. The annual mean is a poor summary of the "
            "days that matter for PM, and switching one variable at a time to its actual values creates weather "
            "combinations that do not occur together. So the per-variable split describes the models; it does not "
            "establish which weather changed the air. This is a finding about the models, reported as such; it does "
            "not choose a family (DEC-118)."]  # fmt: skip
    return out


def main() -> None:
    c = C.ccfg()
    b, e, se = C.PRIMARY.baseline, c["end_year"], c["satellite_end_year"]
    nm = names()
    ch = pd.read_parquet(C.OUT / "city_changes.parquet")
    s = pd.read_csv(C.OUT / "summary.csv")
    h = pd.read_csv(C.OUT / "h4.csv")
    boot = pd.read_csv(C.OUT / "city_boot.csv")
    cby = pd.read_csv(C.OUT / "composition_by_year.csv")
    gs = pd.read_csv(C.OUT / "ground_sat.csv")
    gss = pd.read_csv(C.OUT / "ground_sat_summary.csv")
    ent = pd.read_csv(C.OUT / "entrants_summary.csv")
    cov = pd.read_csv(C.OUT / "coverage.csv")
    lg = C.Spec("lgbm").label
    b2 = c["baseline_years"][1]
    L = []
    w = L.append

    w("# Network composition, ground vs satellite, and H4 (Phase 6, RQ1)")
    w("")
    w("*Generated by `python -m src.normalise.composition_report` from `data/processed/composition/`. Do not edit by hand. "
      "Rules: DEC-125 to DEC-131, fixed and committed before any of these numbers existed. Figure 1 v1: "
      "`reports/figures/fig1_decomposition` and `fig1_decomposition_cities`. All-city summaries show measurement "
      "quantities only; H4 is over NCAP cities only; nothing here contrasts NCAP with non-NCAP cities (Phase 7).*")
    w("")
    w(f"**Primary version:** GAM with one-year knots (the primary family, DEC-118), weather resampled within ±15 days "
      f"(DEC-109), near-constant station-years excluded (DEC-110), balanced panel = stations inside the city's GHSL "
      f"polygon valid every year {b}–{e}, completeness 75%/75%. **LightGBM is shown beside it throughout.** Change = "
      f"100 × (mean {e} / mean {b} − 1), %; differences in percentage points (pp). 95% CIs across cities: cluster "
      f"bootstrap over cities, {c['bootstrap_draws']:,} resamples.")
    w("")

    # ---------------------------------------------------------------- 1. H4
    w("## 1. H4: do reported improvements exceed corrected improvements?")
    w("")
    w("Registered (plan §5): per NCAP city with ground data, the raw all-station change 2018–2025 minus the deweathered "
      "balanced-panel change; supported if the mean across cities is positive with a 95% cluster-bootstrap CI "
      "excluding 0. Descriptive, not causal. **Sign (DEC-127):** read as improvements, i.e. H4 = reported fall − "
      "corrected fall = corrected change − reported change; positive = the reported number overstates the "
      "improvement. Each pollutant is its own test (DEC-131).")
    w("")
    for pol in ("pm25", "pm10"):
        w(f"- **Primary, GAM** — {verdict(h, C.PRIMARY.label, pol)}")
        w(f"- **Same, LightGBM** — {verdict(h, lg, pol)}")
        w(f"- **As registered, no deviations** (GAM k = 4/yr, Grange & Carslaw, registered flags) — "
          f"{verdict(h, C.AS_REGISTERED.label, pol)}")
    w("")
    n_sup = h.groupby("pollutant").supported.agg(["sum", "size"])
    w("Across every version computed, H4 is supported in " + "; ".join(
        f"{int(n_sup.loc[p, 'sum'])} of {int(n_sup.loc[p, 'size'])} for {POL[p]}" for p in ("pm25", "pm10") if p in n_sup.index)
      + ". Versions where it is not:")
    w("")
    ns = h[~h.supported]
    w(md_table(h4_rows(ns), {"reported %": p1, "corrected %": p1, "weather pp": "{:+.1f}", "composition pp": "{:+.1f}"})
      if len(ns) else "*none*")
    w("")
    missing = [x for x in C.specs() for pol in ("pm25", "pm10") if h[(h.spec == x.label) & (h.pollutant == pol)].empty]
    if missing:
        w("Versions with **no NCAP city holding a panel** (H4 not computable): " + "; ".join(
            sorted({f"{x.describe()} ({POL[p]})" for x in missing for p in ('pm25', 'pm10')
                    if h[(h.spec == x.label) & (h.pollutant == p)].empty})) + ".")
        w("")
    w("### 1a. The family × resampling × validity-rule grid (DEC-128)")
    w("")
    w(md_table(h4_rows(h[h.kind == "grid"]), {"reported %": p1, "corrected %": p1, "weather pp": "{:+.1f}",
                                               "composition pp": "{:+.1f}"}))
    w("")
    g = h[(h.spec == C.AS_REGISTERED.label)]
    if len(g) and g.guard_flags_all.sum():
        w(f"The as-registered family (GAM k = 4/yr) under Grange & Carslaw resampling has {int(g.guard_flags_all.sum())} "
          "station-years in the H4 cities' all-station sets outside the extrapolation guard (DEC-115/117) and "
          f"{int(g.guard_flags_panel.sum())} in their panels. H4 uses only the panel's deweathered values, so H4 itself is "
          "unaffected, but its split into weather and composition parts is distorted in that version (the all-station "
          "deweathered mean carries the blow-ups). Versions with any other family or scheme have "
          f"{int(h[~((h.family == 'gam_k4') & (h.scheme == 'annual'))].guard_flags_all.sum())} such station-years.")
        w("")
    w("### 1b. Post-hoc: without site_1433 (Satna), registered-flags versions — *added after inspecting the data* (DEC-124)")
    w("")
    w("Satna's urban centre is not an NCAP unit, so the station cannot enter H4; the rows below are identical to their "
      "registered-flags twins by construction and are shown because DEC-124 requires the check wherever the "
      "registered-rules version is reported. Where the station does contribute (the all-city composition "
      "summaries) the effect is in §2.")
    w("")
    w(md_table(h4_rows(h[h.kind == "posthoc"]), {"reported %": p1, "corrected %": p1, "weather pp": "{:+.1f}",
                                                  "composition pp": "{:+.1f}"}))
    w("")
    w("### 1c. One change at a time from the primary, both competing families; and no deweathering")
    w("")
    w(md_table(h4_rows(h[h.kind.isin(["one-at-a-time", "no-deweathering"])]),
               {"reported %": p1, "corrected %": p1, "weather pp": "{:+.1f}", "composition pp": "{:+.1f}"}))
    w("")
    w("Station-years used (baseline and end years, all stations of the H4 cities): primary "
      + ", ".join(f"{POL[p]} {int(h[(h.spec == C.PRIMARY.label) & (h.pollutant == p)].station_years_used.iloc[0])}"
                  for p in ("pm25", "pm10"))
      + ". The drop-5-Reenu-decided and reliability < 50 versions use "
      + ", ".join(f"{int(x)}" for x in h[h.description.str.contains('Reenu-decided|reliability') & (h.family == 'gam')]
                  .sort_values('pollutant').station_years_used)
      + " (PM10, PM2.5): where the numbers equal the primary's, the exclusion removed nothing from these cities.")
    w("")
    w("**Not computable: the FY2025-26 sensitivity** (plan §5, + January–March 2026). The deweathered series end on "
      "2025-12-31 (DEC-079), so there is no deweathered January–March 2026 (DEC-128).")
    w("")
    w("### 1d. Per city (primary settings; GAM and LightGBM side by side)")
    w("")
    p = ch[(ch.spec == C.PRIMARY.label) & ch.ncap].copy()
    pl = ch[(ch.spec == lg) & ch.ncap].set_index(["unit_id", "pollutant"])
    bb = boot[boot.family == "gam"].set_index(["unit_id", "pollutant"])
    p["city"] = [city_name(nm, u) for u in p.unit_id]
    p["stations 2018→2025 (panel)"] = [f"{a}→{z} ({n})" for a, z, n in zip(p.n_all_base, p.n_all_end, p.n_panel, strict=True)]
    p["H4 GAM (station CI)"] = [ci(r.h4, bb.loc[(r.unit_id, r.pollutant), "h4_lo"], bb.loc[(r.unit_id, r.pollutant), "h4_hi"])
                                for r in p.itertuples()]  # fmt: skip
    p["H4 LightGBM"] = [pl.loc[(r.unit_id, r.pollutant), "h4"] for r in p.itertuples()]
    p["pollutant"] = p.pollutant.map(POL)
    p = p.sort_values(["pollutant", "h4"], ascending=[False, False])
    w(md_table(p[["city", "pollutant", "stations 2018→2025 (panel)", "reported", "weather", "composition", "corrected",
                  "H4 GAM (station CI)", "H4 LightGBM", "watch_stations"]],
               {"reported": "{:+.1f}", "weather": "{:+.1f}", "composition": "{:+.1f}", "corrected": "{:+.1f}",
                "H4 LightGBM": "{:+.1f}"}))  # fmt: skip
    w("")
    w("`weather` and `composition` are each part's contribution to the reported change (pp); reported = weather + "
      "composition + corrected. A station CI equal to the point value means one station in each stratum: no "
      "between-station uncertainty can be estimated for that city (DEC-129); the GAM–LightGBM gap is shown instead.")
    w("")

    # ---------------------------------------------------------------- 2. composition
    w("## 2. Composition bias (RQ1): all stations vs the balanced panel")
    w("")
    w("Every city with a panel, NCAP or not. Composition bias = change(all stations) − change(balanced panel), pp; "
      "negative = the changing set of stations makes the city look as if it improved more than its continuous "
      "stations did.")
    w("")
    labels = {C.PRIMARY.label: "primary (GAM)", lg: "LightGBM",
              C.Spec(baseline=b2, kind="one-at-a-time").label: f"baseline {b2} (GAM)",
              C.Spec(rule="registered_flags").label: "registered flags (GAM)",
              C.Spec(rule="registered_flags", drop_posthoc=True).label: "registered flags without site_1433 (post-hoc)"}
    w(md_table(summary_table(s, labels, "all cities", ["comp_raw", "comp_dw", "weather", "composition"])))
    w("")
    reg = ch[ch.spec == C.Spec(rule="registered_flags").label]
    ws = reg[reg.watch_stations.fillna("").str.len() > 0]
    if len(ws):
        w("**Watch station (DEC-121).** site_1433 (Satna) contributes, under the registered-flags rule, to: "
          + "; ".join(f"{city_name(nm, r.unit_id)} {POL[r.pollutant]} (panel {r.n_panel}, composition bias raw "
                      f"{r.comp_raw:+.1f} pp)" for r in ws.itertuples()) + ". It is in no primary-rule panel.")
        w("")
    w(f"**By year** (all cities with a {b} panel; mean gap between the all-station and panel trends, each indexed to "
      f"{b}, pp; `cities changed` = cities whose station set differs from the panel that year):")
    w("")
    t = cby[cby.spec == C.PRIMARY.label].copy()
    t["value"] = [ci(a, lo, hi) for a, lo, hi in zip(t["mean"], t.lo, t.hi, strict=True)]
    t = t.pivot_table(index=["pollutant", "year", "cities_changed"], columns="metric", values="value", aggfunc="first").reset_index()
    t["pollutant"] = t.pollutant.map(POL)
    w(md_table(t.rename(columns={"gap_raw": "raw", "gap_dw": "deweathered (GAM)", "cities_changed": "cities changed"})))
    w("")
    w("**Per city** (primary; composition bias on raw values with its station-bootstrap 95% CI):")
    w("")
    a = ch[ch.spec == C.PRIMARY.label].copy()
    a["city"] = [city_name(nm, u) for u in a.unit_id]
    a["NCAP"] = a.ncap.map({True: "yes", False: ""})
    a["stations 2018→2025 (panel)"] = [f"{x}→{z} ({n})" for x, z, n in zip(a.n_all_base, a.n_all_end, a.n_panel, strict=True)]
    a["comp. bias raw (station CI)"] = [ci(r.comp_raw, *bb.loc[(r.unit_id, r.pollutant), ["comp_raw_lo", "comp_raw_hi"]])
                                        if (r.unit_id, r.pollutant) in bb.index else f"{r.comp_raw:+.1f}" for r in a.itertuples()]  # fmt: skip
    a["pollutant"] = a.pollutant.map(POL)
    a = a.sort_values(["pollutant", "comp_raw"], ascending=[False, True])
    w(md_table(a[["city", "NCAP", "pollutant", "stations 2018→2025 (panel)", "chg_raw_all", "chg_raw_panel",
                  "comp. bias raw (station CI)", "comp_dw"]].rename(columns={"chg_raw_all": "all stations %",
                  "chg_raw_panel": "panel %", "comp_dw": "comp. bias deweathered"}),
               {"all stations %": "{:+.1f}", "panel %": "{:+.1f}", "comp. bias deweathered": "{:+.1f}"}))  # fmt: skip
    w("")
    w("*Station CIs exist only for NCAP cities (the station bootstrap is run for the H4 set's primary settings); a "
      "city whose station set never changed has a bias of exactly 0.*")
    w("")

    # ---------------------------------------------------------------- 3. ground vs satellite
    w(f"## 3. Ground vs satellite (PM2.5, {b} → {se})")
    w("")
    w(f"Balanced panel (raw) change minus the satellite change (ACAG V5.GL.06, population-weighted over the same "
      f"polygon), pp. The satellite ends in {se}, so the ground change here runs to {se} too. A positive gap = the "
      "ground panel improved less than the satellite says.")
    w("")
    g2 = gss.copy()
    g2["value"] = [ci(m, lo, hi) if r != "corr_panel_sat_changes" else f"{m:.2f}"
                   for m, lo, hi, r in zip(g2["mean"], g2.lo, g2.hi, g2.metric, strict=True)]  # fmt: skip
    g2["metric"] = g2.metric.map(METRIC)
    w(md_table(g2[["group", "metric", "n", "value"]]))
    w("")
    g3 = gs.copy()
    g3["city"] = [city_name(nm, u) for u in g3.unit_id]
    g3["NCAP"] = g3.ncap.map({True: "yes", False: ""})
    g3 = g3.sort_values("gap_panel_sat")
    w(md_table(g3[["city", "NCAP", "n_panel", "panel_raw_base", "sat_base", "chg_panel_raw", "chg_all_raw", "chg_panel_dw",
                   "chg_panel_dw_lgbm", "chg_sat", "gap_panel_sat"]],
               {"panel_raw_base": p1, "sat_base": p1, "chg_panel_raw": "{:+.1f}", "chg_all_raw": "{:+.1f}",
                "chg_panel_dw": "{:+.1f}", "chg_panel_dw_lgbm": "{:+.1f}", "chg_sat": "{:+.1f}",
                "gap_panel_sat": "{:+.1f}"}))  # fmt: skip
    w("")
    w(f"`panel_raw_base`, `sat_base`: {b} levels in µg/m³ (ground panel mean; satellite population-weighted mean).")
    w("")

    # ---------------------------------------------------------------- 4. entrants
    w("## 4. Do new stations read cleaner? Phase 3's comparison on deweathered data (DEC-130)")
    w("")
    w("Per city-year with both new and existing valid stations: log(mean of entrants) − log(mean of incumbents), "
      "shown as %. Pooled over all city-years with a cluster bootstrap over cities. `paired` = deweathered minus raw "
      "on the same city-years, pp. If new stations read cleaner only because of the weather in their first year, the "
      "gap would shrink after deweathering.")
    w("")
    ea = ent[ent.year == "all"].copy()
    ea["value"] = [ci(m, lo, hi) for m, lo, hi in zip(ea.mean_pct, ea.lo_pct, ea.hi_pct, strict=True)]
    nm_m = {"lr_raw": "raw", "lr_dw_gam": "deweathered, GAM", "lr_dw_lgbm": "deweathered, LightGBM",
            "lr_dw_gam_annual": "deweathered, GAM, Grange & Carslaw", "lr_dw_lgbm_annual": "deweathered, LightGBM, Grange & Carslaw",
            "lr_dw_gam_k4": "deweathered, GAM k = 4/yr"}  # fmt: skip
    nm_m.update({k.replace("lr_", "diff_"): f"paired: {v} − raw" for k, v in nm_m.items() if k != "lr_raw"})
    ea["measure"] = ea.measure.map(nm_m)
    ea["pollutant"] = ea.pollutant.map(POL)
    w(md_table(ea[["pollutant", "measure", "units", "value"]].rename(columns={"units": "cities"})))
    w("")
    try:
        p3 = pd.read_csv(C.INTERIM / "eda" / "entrants.csv")
        p3 = p3[p3.year == "all"]
        w("Phase 3's version (raw; stations assigned to their nearest unit, including those outside polygons; t-interval "
          "over city-years): " + "; ".join(f"{POL[r.pollutant]} {ci(r.mean_pct, r.pct_lo, r.pct_hi)}% ({int(r.units)} cities)"
                                            for r in p3.itertuples()) + ".")  # fmt: skip
        w("")
    except FileNotFoundError:
        pass
    ey = ent[(ent.year != "all") & ent.measure.isin(["lr_raw", "lr_dw_gam", "diff_dw_gam"]) & (ent.units >= 3)].copy()
    ey["value"] = [ci(m, lo, hi) for m, lo, hi in zip(ey.mean_pct, ey.lo_pct, ey.hi_pct, strict=True)]
    ey = ey.pivot_table(index=["pollutant", "year", "units"], columns="measure", values="value", aggfunc="first").reset_index()
    ey["pollutant"] = ey.pollutant.map(POL)
    w("By entry year (years with ≥ 3 cities; 95% t-intervals):")
    w("")
    w(md_table(ey.rename(columns={"lr_raw": "raw %", "lr_dw_gam": "deweathered GAM %", "diff_dw_gam": "paired pp",
                                  "units": "cities"})))
    w("")

    # ---------------------------------------------------------------- 5. family diagnostic
    w("## 5. Where GAM and LightGBM disagree, and why (DEC-130; a finding, not a family choice)")
    w("")
    L.extend(family_section(nm))
    w("")

    # ---------------------------------------------------------------- 6. coverage
    w("## 6. Coverage notes")
    w("")
    miss = cov[cov.what == "missing_station_years"]
    w(f"- Valid station-years inside a polygon to {e} that are not in the deweathered table (series with fewer than "
      f"365 valid days, DEC-131): " + ", ".join(f"{POL[r.pollutant]} {r.year}: {int(r.value)}" for r in miss.itertuples())
      + ". NCAP H4 cities whose reported change would move if they were added: "
      + ", ".join(f"{POL[r.pollutant]} {int(r.value)}" for r in cov[cov.what == 'ncap_cities_affected'].itertuples()) + ".")
    w(f"- Cities with a {b} panel: " + ", ".join(
        f"{POL[pp]} {len(ch[(ch.spec == C.PRIMARY.label) & (ch.pollutant == pp)])} (of which NCAP "
        f"{len(ch[(ch.spec == C.PRIMARY.label) & (ch.pollutant == pp) & ch.ncap])})" for pp in ("pm25", "pm10"))
      + "; single-station panels: " + ", ".join(
        f"{POL[pp]} {int((ch[(ch.spec == C.PRIMARY.label) & (ch.pollutant == pp)].n_panel == 1).sum())}" for pp in ("pm25", "pm10"))
      + ". Most results are therefore one monitor's story per city.")
    w(f"- Watch stations (`watch_stations`): {', '.join(params().get('watch_stations', []))}; named wherever they contribute.")
    w("")
    w("## 7. Outputs")
    w("")
    w("`data/processed/composition/`: `city_changes.parquet` (every version × city × pollutant), `summary.csv`, `h4.csv`, "
      "`city_boot.csv`, `trends.parquet` (annual all-station, panel and satellite series, primary version, LightGBM "
      "beside), `composition_by_year.csv`, `ground_sat*.csv`, `entrants*.csv`, `coverage.csv`, `family_diag_*.csv`. "
      "Figure 1 v1: `reports/figures/fig1_decomposition.{png,svg}`, `fig1_decomposition_cities.{png,svg}`.")
    (DOCS / "composition_report.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("docs/composition_report.md written")


if __name__ == "__main__":
    main()

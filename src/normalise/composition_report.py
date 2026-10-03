"""docs/composition_report.md: the Phase 6 results (RQ1 and H4), generated from
data/processed/composition/ (src.normalise.composition, src.normalise.family_diag).

    python -m src.normalise.composition_report

Every number here comes from those tables. Rules: DEC-125 to DEC-136. Nothing contrasts NCAP with
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
          "weather": "modelled weather part (fitted − deweathered)", "composition": "composition part (deweathered)",
          "unmodelled": "unmodelled change (raw − fitted)", "raw_minus_dw": "raw − deweathered (unmodelled + weather)",
          "weather_pan": "raw − deweathered on the panel (other order)", "h4": "H4 (reported fall − corrected fall)",
          "h4_unmodelled": "… of which unmodelled change", "h4_weather": "… of which modelled weather",
          "h4_composition": "… of which composition",
          "reported": "reported change (all stations, raw)", "corrected": "corrected change (panel, deweathered)",
          "gap_panel_sat": "panel (raw) − satellite", "gap_all_sat": "all stations (raw) − satellite",
          "gap_panel_dw_sat": "panel (deweathered) − satellite",
          "gap_panel_sat_comparison": "panel (raw) − satellite V6.GL.03",
          "gap_panel_sat_area": "panel (raw) − satellite, area-weighted",
          "chg_panel_raw": "panel change (raw)", "chg_sat": "satellite change",
          "corr_panel_sat_changes": "correlation of panel and satellite changes across cities"}  # fmt: skip
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
    return t[["version", "pollutant", "cities", "reported_mean", "corrected_mean", "h4_unmodelled_mean",
              "h4_weather_mean", "h4_raw_minus_dw_mean", "h4_composition_mean", "H4, pp (95% CI)", "2.8 × SE",
              "cities_positive", "supported"]].rename(columns={
        "reported_mean": "reported %", "corrected_mean": "corrected %", "h4_unmodelled_mean": "unmodelled pp",
        "h4_weather_mean": "modelled weather pp", "h4_raw_minus_dw_mean": "raw − dw pp",
        "h4_composition_mean": "composition pp", "cities_positive": "cities > 0"})  # fmt: skip


H4FMT = {"reported %": "{:.1f}", "corrected %": "{:.1f}", "unmodelled pp": "{:+.1f}", "modelled weather pp": "{:+.1f}",
         "raw − dw pp": "{:+.1f}", "composition pp": "{:+.1f}"}  # fmt: skip


def scope(h: pd.DataFrame) -> str:
    """DEC-136: who H4 covers, generated from the primary version."""
    r = h[h.is_primary].set_index("pollutant")
    part = [f"{int(r.loc[p, 'cities'])} NCAP cities for {POL[p]} ({int(r.loc[p, 'single_station_panels'])} of them with "
            "a single such station)" for p in ("pm25", "pm10") if p in r.index]  # fmt: skip
    return ("**Scope:** H4 covers only the NCAP cities with a station valid in every year 2018–2025: "
            + " and ".join(part) + ". It is not a statement about NCAP cities in general.")


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
    """DEC-133/136: the family diagnostic, reported as modelled weather (all variables together) and
    misfit only. The per-variable outputs stay in the CSVs for the record; no claim about an
    individual weather variable is made here."""
    try:
        cities = pd.read_csv(C.OUT / "family_diag_cities.csv")
        chk = pd.read_csv(C.OUT / "family_diag_check.csv")
        att = pd.read_csv(C.OUT / "family_diag_attribution.csv")
    except FileNotFoundError:
        return ["*Not run: `python -m src.normalise.family_diag`.*"]
    flag = C.ccfg()["family_flag_pp"]
    b, e = C.PRIMARY.baseline, C.ccfg()["end_year"]
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
    kk = k[(k.city == "Kolkata") & (k.pollutant == "pm25") & (k.family == "gam")]
    a = att[att.scheme == "seasonal"].copy()
    gap2 = (a.total - a.implied_weather_change).abs()
    out += ["", "### 5a. The method fixed in DEC-130 failed its own check, and what replaced it (DEC-133)", "",
            f"DEC-130 split each family's weather effect on the **log scale** and required the parts to add up to the "
            f"implied weather change, 100 × change in log(raw/deweathered). They do not: the gap is a median "
            f"{gap.median():.1f} and up to {gap.max():.1f} points over {len(k)} station × family pairs (seasonal scheme)"
            + (f"; for Kolkata's GAM (PM2.5) the parts sum to {kk.sum_of_parts.iloc[0]:+.1f} against "
               f"{kk.implied_weather_change.iloc[0]:+.1f}" if len(kk) else "")
            + ". The reason: H4 and the deweathered change are changes in **arithmetic** annual means, where weather "
            "acting on the most polluted days counts for more than on the log scale, and a model's fitted values need "
            "not reproduce a station's arithmetic mean. The failed version is kept, unused, in "
            "`family_diag_contrib.csv` and `family_diag_check.csv`.", "",
            "**Replacement (annual-mean scale).** The implied weather change is split into **modelled weather** (the "
            f"model's weather effect, all variables together; {C.ccfg()['diag_draws']} of the 500 shared draws) and "
            "**misfit** (the change in log(observed mean / the model's fitted mean): what the model reproduces with "
            "neither its trend nor its weather terms; deweathering drops it, so raw − deweathered counts it as weather). "
            f"They add up to the implied change up to Monte-Carlo error: median gap {gap2.median():.2f}, largest "
            f"{gap2.max():.2f} points ({len(a)} station × family pairs). H4's own split (§1, DEC-136) is the same idea "
            "on the scale of % changes.", "",
            "*No claim is made here about individual weather variables (DEC-136). The per-variable splits and ERA5 "
            "summaries that were computed stay in `family_diag_attribution.csv` and `family_diag_era5.csv` for the "
            "record only.*", ""]  # fmt: skip
    out += [f"### 5b. Modelled weather and misfit per family, {b} → {e} (seasonal scheme)", "",
            "Changes × 100 (≈ %; negative = made the later year look cleaner). `deweathered` = the family's deweathered "
            "change (%); `raw` = the measured change (%).", ""]  # fmt: skip
    a["city"] = [x if isinstance(x, str) else u for x, u in zip(a.city, a.unit_id, strict=True)]
    t = pd.DataFrame({"city": a.city, "pollutant": a.pollutant.map(POL), "family": a.family.map({"gam": "GAM", "lgbm": "LightGBM"}),
                      "modelled weather": a.model_weather, "misfit": a.misfit, "total": a.total,
                      "implied": a.implied_weather_change, "deweathered": a.chg_dw, "raw": a.chg_raw})  # fmt: skip
    out += [md_table(t, {x: "{:+.1f}" for x in ["modelled weather", "misfit", "total", "implied", "deweathered", "raw"]}), ""]
    lines = []
    for (city, pol), g in t.groupby(["city", "pollutant"], sort=False):
        if set(g.family) != {"GAM", "LightGBM"}:
            continue
        gg, ll = g[g.family == "GAM"].iloc[0], g[g.family == "LightGBM"].iloc[0]
        dm, dw_ = gg.misfit - ll.misfit, gg["modelled weather"] - ll["modelled weather"]
        big = "misfit" if abs(dm) >= abs(dw_) else "modelled weather"
        lines.append(f"- **{city}, {pol}:** GAM − LightGBM in the deweathered change {gg.deweathered - ll.deweathered:+.1f} "
                     f"pp; of the weather-effect gap, misfit {dm:+.1f} and modelled weather {dw_:+.1f} points; larger: "
                     f"**{big}**.")  # fmt: skip
    n_mis = sum("larger: **misfit**" in x for x in lines)
    out += [f"**Which is larger per city** (GAM − LightGBM): misfit in {n_mis} of {len(lines)}.", "", *lines, ""]
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
      "Rules: DEC-125 to DEC-131, fixed and committed before any of these numbers existed; review rulings and the weather split: DEC-135 to DEC-136. Figures (Phase 9, DEC-190): "
      "figure 1 `reports/figures/fig1_decomposition`, per city `figS3_decomposition_cities`, PM10 `figS4_decomposition_pm10`. All-city summaries show measurement "
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
    w(scope(h))
    w("")
    w("Registered (plan §5): per NCAP city with ground data, the raw all-station change 2018–2025 minus the deweathered "
      "balanced-panel change; supported if the mean across cities is positive with a 95% cluster-bootstrap CI "
      "excluding 0. Descriptive, not causal. **Sign (DEC-127):** read as improvements, i.e. H4 = reported fall − "
      "corrected fall = corrected change − reported change; positive = the reported number overstates the "
      "improvement. Each pollutant is its own test (DEC-131). **Decomposition (DEC-136, added description; the test is "
      "unchanged):** H4 = unmodelled change (raw − fitted: what the model reproduces with neither its trend nor its "
      "weather terms) + modelled weather (fitted − deweathered) + composition. `raw − dw` = the first two together, the "
      "only form available where fitted values are missing (completeness 60%).")
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
    w(md_table(h4_rows(ns), H4FMT)
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
    w(md_table(h4_rows(h[h.kind == "grid"]), H4FMT))
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
    w(md_table(h4_rows(h[h.kind == "posthoc"]), H4FMT))
    w("")
    w("### 1c. One change at a time from the primary, both competing families; and no deweathering")
    w("")
    w(md_table(h4_rows(h[h.kind.isin(["one-at-a-time", "no-deweathering"])]),
               H4FMT))
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
    w(scope(h))
    w("")
    w(md_table(p[["city", "pollutant", "stations 2018→2025 (panel)", "reported", "unmodelled", "weather", "composition", "corrected",
                  "H4 GAM (station CI)", "H4 LightGBM", "watch_stations"]],
               {"reported": "{:+.1f}", "unmodelled": "{:+.1f}", "weather": "{:+.1f}", "composition": "{:+.1f}", "corrected": "{:+.1f}",
                "H4 LightGBM": "{:+.1f}"}))  # fmt: skip
    w("")
    w("`unmodelled`, `weather` (modelled weather only) and `composition` are each part's contribution to the reported "
      "change (pp); reported = unmodelled + weather + "
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
    w(md_table(summary_table(s, labels, "all cities", ["comp_raw", "comp_dw", "unmodelled", "weather", "composition"])))
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
      "Figures (Phase 9, DEC-190): `reports/figures/fig1_decomposition`, `figS3_decomposition_cities`, `figS4_decomposition_pm10` (PNG, SVG).")
    (DOCS / "composition_report.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("docs/composition_report.md written")


if __name__ == "__main__":
    main()

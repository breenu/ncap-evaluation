"""Every number in the technical report, the results summary, the policy brief and the figure 1 slide
(Phase 10; DEC-206, DEC-210). Nothing in those documents is typed by hand (hard rule 3): the prose reads
each value from `reports/_variables.yml` through Quarto's `{{< var … >}}`, and the tables are included
from `reports/_generated/`.

    python -m src.report.values

Values come from the processed outputs the phase reports already read, through the same loaders and
decision functions (`src.causal.causal_report`, `src.hierarchical.report`, `src.causal.report_maiac`), so
no rule is re-implemented here. Every value is stored as text, formatted as the documents print it.

Wording (DEC-154 and its extensions): nothing is an effect of NCAP. Every value and table passes
`src/viz/wording.py` before anything is written.
"""

import json
import re

import numpy as np
import pandas as pd
import yaml

from src.causal import causal_report as CR
from src.causal import decisions as D
from src.causal import layer_a as A
from src.causal import report_maiac as RM
from src.common.gate import require_gate
from src.common.paths import FIGURES, INTERIM, PROCESSED, REPORTS, params
from src.viz import wording

VARS = REPORTS / "_variables.yml"
GEN = REPORTS / "_generated"
MINUS = "−"

LINKS = {
    "osf": "https://osf.io/jksne/",
    "repo": "https://github.com/breenu/ncap-evaluation",
    "site": "https://breenu.github.io/ncap-evaluation/",
    "plan_commit": "6e24eca",
    "gate_commit": "0d9aa42",
}


# ---------------------------------------------------------------- formatting


def s(x: float, d: int = 1) -> str:
    """Signed number with a typographic minus."""
    return f"{x:+.{d}f}".replace("-", MINUS)


def u(x: float, d: int = 1) -> str:
    return f"{x:.{d}f}".replace("-", MINUS)


def n(x: float) -> str:
    return f"{int(round(x)):,}"


def pc(log_units: float, d: int = 1) -> str:
    """A log-scale estimate as a signed % change, 100 × (e^β − 1)."""
    return s(D.pct(log_units), d) + "%"


def ci(lo: float, hi: float, d: int = 1) -> str:
    return f"{pc(lo, d)} to {pc(hi, d)}"


def pv(v: float, d: int = 1) -> str:
    """A value already in %."""
    return s(v, d) + "%"


def civ(lo: float, hi: float, d: int = 1, unit: str = "") -> str:
    return f"{s(lo, d)}{unit} to {s(hi, d)}{unit}"


def pval(p: float) -> str:
    return f"{p:.4f}" if p < 0.01 else f"{p:.3f}"


def dashes(widths: list[int]) -> str:
    """A pipe-table separator whose dash counts are proportional to each column's longest cell, so that
    Pandoc gives wide columns more room (relative widths are taken from the dashes)."""
    return "|" + "|".join("-" * max(4, min(60, w)) for w in widths) + "|"


def md(df: pd.DataFrame) -> str:
    cols = list(df.columns)
    widths = [max([len(str(c))] + [len(str(v)) for v in df[c]]) for c in cols]
    out = ["| " + " | ".join(cols) + " |", dashes(widths)]
    out += ["| " + " | ".join("" if pd.isna(v) else str(v) for v in r) + " |" for r in df.itertuples(index=False)]
    return "\n".join(out) + "\n"


def yes(b) -> str:
    return "yes" if bool(b) else "no"


# ---------------------------------------------------------------- sections


def settings() -> dict:
    """Method settings quoted in the text, read from config/params.yaml so none is typed by hand."""
    P = params()
    c, f, dw, cs, rb, pg, hi = P["completeness"], P["flags"], P["deweathering"], P["causal"], P["robustness"], P["pregate"], P["hierarchical"]
    pct0 = lambda x: f"{100 * x:.0f}%"  # noqa: E731
    return {
        "completeness": pct0(c["min_hour_share_per_day"]),
        "completeness_sens": " and ".join(pct0(x) for x in c["sensitivity"]),
        "quarters_sens": n(c["min_quarters_per_hour_sensitivity"]),
        "flatline_hours": n(f["flatline_min_hours"]),
        "ratio_abs": n(f["pm25_gt_pm10_tolerance"]["abs_ugm3"]),
        "ratio_rel": pct0(f["pm25_gt_pm10_tolerance"]["rel"]),
        "ceiling_min": n(f["ceiling_detect"]["min_value"]),
        "neighbour_km": n(f["neighbour_radius_km"]),
        "robust_z": n(f["robust_z"]),
        "cp_false_alarm": pct0(f["changepoint_false_alarm"]),
        "cp_min_shift": f"{100 * (np.exp(f['changepoint_min_shift']) - 1):.0f}%",
        "nc_window": n(f["near_constant"]["window_days"]),
        "nc_flag_days": n(f["near_constant"]["min_flag_days_per_year"]),
        "check_penalty": f"{P['reliability']['check_penalty']:g}",
        "min_pop": n(P["control_pool"]["min_population"]),
        "spill_km": n(P["control_pool"]["spillover_buffer_km"]),
        "draws": n(dw["resamples_default"]),
        "window_days": n(dw["resample_window_days"]),
        "min_fit_days": n(dw["min_fit_days"]),
        "within_folds": n(dw["cv_within_folds"]),
        "within_buffer": n(dw["cv_within_buffer_days"]),
        "divergence_pct": n(dw["divergence_flag_pct"]) + "%",
        "guard": f"{dw['guard_ratio'][0]:g}–{dw['guard_ratio'][1]:g}×",
        "lockdown": "{} {:%B} to {} {:%B %Y}".format(*(v for d in map(pd.Timestamp, dw["lockdown"]) for v in (d.day, d))),
        "bootstrap": n(P["composition"]["bootstrap_draws"]),
        "placebo_reps": n(cs["placebo_reps"]),
        "event_from": s(cs["event_window"][0], 0), "event_to": s(cs["event_window"][1], 0),
        "wald_min": f"{cs['wald_p_min']:.2f}",
        "targets": ", ".join(f"{t}%" for t in cs["target_reductions_pct"]),
        "honest_grid": ", ".join(f"{x:g}" for x in cs["honest_mbar"]),
        "cs_biters": n(cs["cs_biters"]),
        "chains": n(hi["chains"]), "mcmc_draws": n(hi["draws"]),
        "placebo_year": str(rb["placebo_year"]),
        "leakage_min": n(rb["leakage_min_units"]),
        "equiv": n(rb["equivalence_margin_pct"]) + "%",
        "alpha": "0.05",  # the registered test level for every hypothesis and for Benjamini–Hochberg (plan §5)
        "fdr": "5%",
        "fake_years": " and ".join(str(y) for y in pg["fake_adoption_years"]),
        "mde_mult": f"{pg['mde_multiplier']:g}",
        "sat_first": str(P["windows"]["satellite_analysis_years"][0]),
        "sat_last": str(P["windows"]["satellite_analysis_years"][1]),
        "listed_by": pd.Timestamp(f"2019-{P['treatment']['listed_by']}").strftime("%d %B").lstrip("0"),
    }  # fmt: skip


def ncap_and_units() -> dict:
    cities = pd.read_csv(INTERIM / "ncap_cities.csv")
    match = pd.read_csv(INTERIM / "ncap_ucdb_match.csv")
    units = pd.read_csv(INTERIM / "pregate" / "units.csv")
    steps = pd.read_csv(INTERIM / "pregate" / "pool_steps.csv").units.tolist()
    bal = pd.read_csv(INTERIM / "pregate" / "balance.csv").set_index("characteristic")
    gain = pd.read_csv(INTERIM / "pregate" / "monitor_gain.csv")
    t = units[units.role == "treated"]
    matched = match[match.status == "matched"].city.nunique()
    first = pd.to_datetime(cities.first_listed_date)
    row = lambda k: bal[bal.index.str.startswith(k)].iloc[0]  # noqa: E731
    return {
        "cities_master": n(cities.in_master_131.sum()),
        "cities_latest": n(cities.in_ls18_au386_2026_02_02.sum()),
        "xvfc": n((cities.channel == "XVFC").sum()),
        "ncap_channel": n((cities.channel == "NCAP").sum()),
        "on_2017_list": n((first.dt.year == 2017).sum()),
        "at_launch": n((first <= "2019-01-31").sum()),
        "cities_in_units": n(matched),
        "towns_no_centre": n((match.status == "no_uc").sum()),
        "treated": n(len(t)),
        "cohort_2019": n((t.cohort_listed == 2019).sum()),
        "cohort_2020": n((t.cohort_listed == 2020).sum()),
        "cohort_2021": n((t.cohort_listed == 2021).sum()),
        "fcohort_2020": n((t.cohort_funded == 2020).sum()),
        "fcohort_2021": n((t.cohort_funded == 2021).sum()),
        "fcohort_2022": n((t.cohort_funded == 2022).sum()),
        "centres": n(steps[0]),
        "nonncap": n(steps[2]),
        "pop100k": n(steps[3]),
        "controls": n(steps[4]),
        "buffered": n(steps[6]),
        "smd_pop": u(row("Population").smd_vs_control_pool, 2),
        "igp_treated": u(100 * row("Region: igp").treated, 0) + "%",
        "igp_control": u(100 * row("Region: igp").control_pool, 0) + "%",
        "pm_treated": u(row("PM2.5 mean").treated),
        "pm_control": u(row("PM2.5 mean").control_pool),
        "gained": n(gain.gained_monitor.sum()),
        "notgained": n((~gain.gained_monitor).sum()),
        "notgained_had": n(((~gain.gained_monitor) & (gain.stations_before > 0)).sum()),
        "notgained_never": n(((~gain.gained_monitor) & (gain.stations_before == 0)).sum()),
    }


def network_and_audit() -> dict:
    st = pd.read_csv(PROCESSED / "stations.csv")
    first = pd.read_csv(INTERIM / "eda" / "station_first_year.csv")
    fc = pd.read_csv(INTERIM / "audit" / "flag_counts.csv")
    cp = pd.read_csv(INTERIM / "audit" / "changepoints.csv")
    sp = pd.read_csv(INTERIM / "audit" / "spatial_station_year.csv")
    ce = pd.read_csv(INTERIM / "audit" / "ceilings.csv")
    vs = pd.read_csv(INTERIM / "audit" / "valid_station_years.csv").set_index(["pollutant", "year"])
    mb = pd.read_csv(INTERIM / "audit" / "missingness_bias.csv")
    mm = pd.read_csv(INTERIM / "audit" / "missingness_models.csv")
    nc = pd.read_parquet(PROCESSED / "station_year_near_constant.parquet")
    q = pd.read_parquet(PROCESSED / "station_year_quality.parquet")
    by = fc.groupby(["pollutant", "year"])[["hours", "hours_ratio_flag", "hours_flatline"]].sum()
    ratio = 100 * by.hours_ratio_flag / by.hours
    flat = 100 * by.hours_flatline / by.hours
    removed = fc[["quarters_impossible", "quarters_ceiling"]].sum().sum() / fc[
        ["quarters_kept", "quarters_impossible", "quarters_ceiling"]].sum().sum()  # fmt: skip
    p25 = sp[sp.pollutant == "pm25"]
    # coefficients are probabilities; ×100 gives percentage points, as in the audit report
    term = lambda m, t: 100 * mm[(mm.model == m) & (mm.pollutant == "pm25") & (mm.term == t)].iloc[0].Estimate  # noqa: E731
    # near-constant station-years among those valid under the primary completeness rule (DEC-110)
    v = q[q.valid_q1_t75][["sid", "pollutant", "year"]].merge(nc, on=["sid", "pollutant", "year"], how="left")
    ncv = v[v.near_constant.fillna(False).astype(bool)]
    fy = first.first_year
    pre, post = [y for y in range(2015, 2019)], [y for y in range(2019, 2026)]
    return {
        "stations": n(len(st)),
        "stations_2015": n((fy == 2015).sum()),
        "stations_by_2018": n((fy <= 2018).sum()),
        "stations_from_2019": n((fy >= 2019).sum()),
        "stations_2023": n((fy == 2023).sum()),
        "ceilings_pm25": ", ".join(f"{c:g}" for c in ce[ce.pollutant == "pm25"].ceiling),
        "ceilings_pm10": ", ".join(f"{c:g}" for c in ce[ce.pollutant == "pm10"].ceiling),
        "removed_pct": u(100 * removed, 2) + "%",
        "ratio_pre_lo": u(min(ratio[(p, y)] for p in ("pm25", "pm10") for y in pre)) + "%",
        "ratio_pre_hi": u(max(ratio[(p, y)] for p in ("pm25", "pm10") for y in pre)) + "%",
        "ratio_post_hi": u(max(ratio[(p, y)] for p in ("pm25", "pm10") for y in post if y >= 2020), 2) + "%",
        "flat_post_lo": u(min(flat[(p, y)] for p in ("pm25", "pm10") for y in range(2017, 2026))) + "%",
        "flat_post_hi": u(max(flat[(p, y)] for p in ("pm25", "pm10") for y in range(2017, 2026))) + "%",
        "changepoints": n(len(cp)),
        "changepoint_stations": n(cp.sid.nunique()),
        "neighbour_corr": u(p25.neighbour_corr.median(), 2),
        "sat_flagged": n(p25.flag_satellite.sum()),
        "pm10_valid_2017": n(vs.loc[("pm10", 2017), "valid_q1_t75"]),
        "pm10_valid_2018": n(vs.loc[("pm10", 2018), "valid_q1_t75"]),
        "pm25_valid_2018": n(vs.loc[("pm25", 2018), "valid_q1_t75"]),
        "pm25_valid_2025": n(vs.loc[("pm25", 2025), "valid_q1_t75"]),
        "miss_winter_pp": s(term("season_year", "C(season)[T.winter]")),
        "miss_high_pp": s(term("pollution_level", "C(ref_tercile)[T.high]")),
        "miss_winter_abs": u(abs(term("season_year", "C(season)[T.winter]"))),
        "miss_high_abs": u(abs(term("pollution_level", "C(ref_tercile)[T.high]"))),
        "miss_bias_pm25": pv(mb[mb.pollutant == "pm25"].bias_pct.median()),
        "miss_bias_pm10": pv(mb[mb.pollutant == "pm10"].bias_pct.median()),
        "nearconst_years": n(len(ncv)),
        "valid_station_years": n(len(v)),
        "nearconst_stations": n(ncv.sid.nunique()),
    }


def deweathering() -> dict:
    from src.normalise.aggregate import OUT
    from src.normalise.report import city_weather_share, weather_by_year

    ch = json.loads((OUT / "family_choice.json").read_text(encoding="utf-8"))
    sm = pd.read_parquet(OUT / "series_metrics.parquet")
    sm = sm[(sm.run == "main") & (sm.family == ch["primary"])]
    cy = pd.read_parquet(OUT / "city_year.parquet")
    sy = pd.read_parquet(OUT / "station_year.parquet")
    lt = json.loads((OUT / "lockdown_test.json").read_text(encoding="utf-8"))
    w = city_weather_share(cy, "dw").set_index("pollutant")
    wa = city_weather_share(cy, "dw_annual").set_index("pollutant")
    wy = weather_by_year(sy, "dw").set_index(["pollutant", "year"])["median"] * 100
    P = params()["deweathering"]
    return {
        "series": n(len(sm)),
        "series_pm25": n((sm.pollutant == "pm25").sum()),
        "series_pm10": n((sm.pollutant == "pm10").sum()),
        "draws": n(P["resamples_default"]),
        "window_days": n(P["resample_window_days"]),
        "r2_gam": u(ch["median_r2_oos"]["gam"], 3),
        "r2_lgbm": u(ch["median_r2_oos"]["lgbm"], 3),
        "r2_series": n(ch["series_with_cv"]),
        "r2_gam_better": n(ch["series_where_gam_better"]),
        "r2_gam_clamp": u(ch["median_r2_oos_clamp"]["gam"], 3),
        "r2_lgbm_clamp": u(ch["median_r2_oos_clamp"]["lgbm"], 3),
        "weather_pm25": u(w.loc["pm25", "median_abs_weather_pct"]) + "%",
        "weather_pm25_p90": u(w.loc["pm25", "p90_abs_weather_pct"]) + "%",
        "raw_change_pm25": u(w.loc["pm25", "median_abs_raw_change_pct"]) + "%",
        "weather_pm10": u(w.loc["pm10", "median_abs_weather_pct"]) + "%",
        "weather_pm25_gc": u(wa.loc["pm25", "median_abs_weather_pct"]) + "%",
        "weather_cities": n(w.loc["pm25", "cities"]),
        "weather_2015": pv(wy[("pm25", 2015)]),
        "weather_2025": pv(wy[("pm25", 2025)]),
        "diverging": n(sm.diverges.sum()),
        "with_d": n(sm.D_pct.notna().sum()),
        "lockdown_median": u(lt["median_abs_diff_pct_2019_2021"], 2) + "%",
        "lockdown_2019": u(lt["median_abs_diff_pct_2019"], 2) + "%",
        "lockdown_threshold": u(lt["threshold_pct"], 0) + "%",
    }


def composition() -> dict:
    C = PROCESSED / "composition"
    h = pd.read_csv(C / "h4.csv")
    sm = pd.read_csv(C / "summary.csv")
    by = pd.read_csv(C / "composition_by_year.csv")
    gs = pd.read_csv(C / "ground_sat_summary.csv")
    en = pd.read_csv(C / "entrants_summary.csv")
    en = en[en.year.astype(str) == "all"].set_index(["pollutant", "measure"])
    prim = h[h.is_primary]
    spec = prim.spec.iloc[0]
    out = {}
    versions = {"primary": h.is_primary, "lgbm": (h.description == "LightGBM, seasonal, primary rule"),
                "asreg": h.is_as_registered}  # fmt: skip
    for vk, mask in versions.items():
        for pol in ("pm25", "pm10"):
            r = h[mask & (h.pollutant == pol)].iloc[0]
            out[f"{vk}_{pol}"] = {
                "cities": n(r.cities), "single": n(r.single_station_panels), "stations": n(r.stations_panel),
                "reported": pv(r.reported_mean), "corrected": pv(r.corrected_mean),
                "unmodelled": s(r.h4_unmodelled_mean), "weather": s(r.h4_weather_mean),
                "composition": s(r.h4_composition_mean), "h4": s(r.h4_mean), "ci": civ(r.h4_lo, r.h4_hi),
                "supported": "supported" if r.supported else "not supported",
                "share_removed": u(100 * (r.reported_mean - r.corrected_mean) / r.reported_mean, 0) + "%",
                "reported_abs": u(abs(r.reported_mean)) + "%", "corrected_abs": u(abs(r.corrected_mean)) + "%",
            }  # fmt: skip
    for pol in ("pm25", "pm10"):
        hp = h[h.pollutant == pol]
        out[f"versions_{pol}"] = n(len(hp))
        out[f"supported_{pol}"] = n(hp.supported.sum())
        out[f"failing_{pol}"] = "; ".join(f"{r.description}: {s(r.h4_mean)} pp ({civ(r.h4_lo, r.h4_hi)})"
                                          for r in hp[~hp.supported].itertuples()) or "none"  # fmt: skip
        b = sm[(sm.spec == spec) & (sm.pollutant == pol) & (sm.group == "all cities") & (sm.metric == "comp_raw")].iloc[0]
        out[f"bias_{pol}"] = s(b["mean"])
        out[f"bias_{pol}_abs"] = u(abs(b["mean"]))
        out[f"bias_{pol}_ci"] = civ(b.lo, b.hi)
        out[f"bias_{pol}_cities"] = n(b.n)
        e = en.loc[(pol, "lr_raw")]
        out[f"entrants_{pol}_raw"] = pv(e.mean_pct)
        out[f"entrants_{pol}_raw_abs"] = u(abs(e.mean_pct)) + "%"
        out[f"entrants_{pol}_raw_ci"] = civ(e.lo_pct, e.hi_pct)
    for k, m in (("dw", "lr_dw_gam"), ("paired", "diff_dw_gam")):
        e = en.loc[("pm25", m)]
        out[f"entrants_pm25_{k}"] = pv(e.mean_pct) if k == "dw" else s(e.mean_pct)
        out[f"entrants_pm25_{k}_abs"] = u(abs(e.mean_pct)) + ("%" if k == "dw" else "")
        out[f"entrants_pm25_{k}_ci"] = civ(e.lo_pct, e.hi_pct)
    y = by[(by.spec == spec) & (by.pollutant == "pm25") & (by.metric == "gap_raw")].set_index("year")
    for yr in (2021, 2022, 2023, 2025):
        out[f"bias_pm25_{yr}"] = s(y.loc[yr, "mean"])
    out["changed_2025"] = n(y.loc[2025, "cities_changed"])
    g = gs[gs.group == "all cities"].set_index("metric")
    out["gap_panel_sat"] = s(g.loc["gap_panel_sat", "mean"])
    out["gap_panel_sat_ci"] = civ(g.loc["gap_panel_sat", "lo"], g.loc["gap_panel_sat", "hi"])
    out["corr_changes"] = u(g.loc["corr_panel_sat_changes", "mean"], 2)
    out["gs_cities"] = n(g.loc["gap_panel_sat", "n"])
    return out


def causal() -> dict:
    require_gate("report values (Phase 10)")
    X = CR.load()
    R = CR.decide(X)
    s_ = X["s"]
    p, h1 = R["primary"], R["h1"]
    lvl = s_.loc[("primary", "att:level:popw_V5GL06")]
    win = s_.loc[("primary", "att:log:winter_popw_V5GL06")]
    nwin = s_.loc[("primary", "att:log:nonwinter_popw_V5GL06")]
    es = X["es_meta"]["avg_post"]
    cs = X["cs"]["nevertreated"]
    lv = pd.read_csv(A.OUT / "levels.csv").set_index(["group", "year"])["mean"]
    rob = pd.read_csv(A.OUT / "robustness.csv")
    ra = rob[rob.layer == "A"]
    judged = ra[ra.agrees.notna()]
    agrees = judged.agrees.astype(str).str.lower() == "true"
    est_rows = ra[~ra.check.str.contains("Placebo|MAIAC", regex=True)]
    loo = re.search(r"range ([+-]\d\.\d+) to ([+-]\d\.\d+)", ra[ra.check.str.startswith("Leave-one-out")].note.iloc[0])
    fire = ra[ra.check.str.startswith("VIIRS")].iloc[0]
    tri = pd.read_csv(A.OUT / "triangulation.csv")
    inv = pd.read_csv(A.OUT / "investigation.csv")
    iv = lambda pat: inv[inv.quantity.str.contains(pat, regex=False)].iloc[0]  # noqa: E731
    lb = pd.read_csv(A.OUT / "layer_b" / "estimates.csv")
    lbp = lb[lb.version == "primary"]
    out = {
        "sentence": CR.wording(X),
        # the "about 3–5%" range, from the same sentence (src.causal.causal_report.wording), never typed
        "rise_range": re.search(r"relative rise of about ([^.]+%)", CR.wording(X)).group(1),
        "verdict": h1["verdict"],
        "met_a": yes(h1["a"]), "met_b": yes(h1["b"]), "met_c": yes(h1["c"]), "met_d": yes(h1["d"]),
        "h2_tested": yes(R["h2"]["tested"]),
        "att": pc(p["att"]), "ci": ci(p["lo95"], p["hi95"]), "att_log": s(p["att"], 4), "se_log": u(p["se"], 4),
        "ci90": ci(p["lo90"], p["hi90"]),
        "att_ug": s(lvl.att, 2), "ci_ug": civ(lvl.lo95, lvl.hi95, 2),
        "p_perm": u(p["p_perm"], 3),
        "wald_stat": u(R["wald_pre"]["stat"], 1), "wald_df": n(R["wald_pre"]["df"]), "wald_p": pval(R["wald_pre"]["p"]),
        "wald_min": u(params()["causal"]["wald_p_min"], 2),
        "placebo2016": pc(R["placebo2016"]["att"]), "placebo2016_ci": ci(R["placebo2016"]["lo95"], R["placebo2016"]["hi95"]),
        "cs": pc(cs.att), "cs_ci": ci(cs.lo95, cs.hi95),
        "area": pc(s_.loc[("area", "att")].att), "v6": pc(s_.loc[("v6gl03", "att")].att),
        "es_avg": pc(es["coef"]), "es_ci": ci(es["lo95"], es["hi95"]),
        "honest_breakdown": R["honest_breakdown"],
        "equiv_margin": u(params()["robustness"]["equivalence_margin_pct"], 0) + "%",
        "equivalent": yes(h1["equivalent"]),
        "targets": ", ".join(f"{k}%" for k, v in R["targets_excluded"].items() if v),
        "mde": u(D.pct(R["mde_log"])) + "%",  # the plan's carried MDE, read as a fall (Phase 4)
        "mde_real": u(D.pct(2.8 * p["se"])) + "%",
        "h2_winter": pc(win.att), "h2_nonwinter": pc(nwin.att), "h2_diff": pc(R["h2"]["diff"]),
        "h2_ci": ci(R["h2"]["lo95"], R["h2"]["hi95"]),
        "leak_gained": pc(R["leakage"]["gained"]["att"]), "leak_notgained": pc(R["leakage"]["notgained"]["att"]),
        "leak_diff": pc(R["leakage"]["diff"]["att"]),
        "leak_diff_ci": ci(R["leakage"]["diff"]["lo95"], R["leakage"]["diff"]["hi95"]),
        "leak_fires": yes(R["leakage"]["reason"]),
        "ncap_2018": u(lv[("NCAP units", 2018)]), "ncap_2024": u(lv[("NCAP units", 2024)]),
        "pool_2018": u(lv[("control pool", 2018)]), "pool_2024": u(lv[("control pool", 2024)]),
        "ncap_fall": pv(100 * (lv[("NCAP units", 2024)] / lv[("NCAP units", 2018)] - 1)),
        "ncap_fall_abs": u(abs(100 * (lv[("NCAP units", 2024)] / lv[("NCAP units", 2018)] - 1))) + "%",
        "pool_fall_abs": u(abs(100 * (lv[("control pool", 2024)] / lv[("control pool", 2018)] - 1))) + "%",
        "pool_fall": pv(100 * (lv[("control pool", 2024)] / lv[("control pool", 2018)] - 1)),
        "rob_agree": n(agrees.sum()), "rob_judged": n(len(judged)),
        "rob_all_positive": yes((est_rows.est > 0).all()),
        "rob_min": pc(est_rows.est.min()), "rob_max": pc(est_rows.est.max()),
        "loo_lo": s(float(loo.group(1)), 4), "loo_hi": s(float(loo.group(2)), 4),
        "fire": pc(fire.est), "fire_ci": ci(fire.lo95, fire.hi95),
        "restricted": pc(tri.a_est.iloc[0]), "restricted_ci": ci(tri.a_lo95.iloc[0], tri.a_hi95.iloc[0]),
        "restricted_units": n(tri.a_units.iloc[0]),
        "cat_did": tri.category.iloc[0], "cat_its": tri.category.iloc[1],
        "inv_sat_cells": pc(iv("satellite at the panel stations").est),
        "inv_sat_poly": pc(iv("satellite, population-weighted polygon").est),
        "inv_ground": pc(iv("ground panel, deweathered, same years").est),
        "inv_ground_ci": ci(iv("ground panel, deweathered, same years").lo95, iv("ground panel, deweathered, same years").hi95),
        "inv_vintage": pc(iv("V6.GL.02.04 vintage").est), "inv_vintage_ci": ci(iv("V6.GL.02.04 vintage").lo95, iv("V6.GL.02.04 vintage").hi95),
        "inv_all_its": pc(iv("ITS: all stations, deweathered").est),
        "inv_raw_its": pc(inv[inv.quantity == "ITS: raw"].est.iloc[0]),
    }  # fmt: skip
    for _, r in judged[~agrees].iterrows():
        key = "vintage" if "vintage" in r.check else "noigp" if "Indo-Gangetic" in r.check else "other"
        out[f"rob_no_{key}"] = pc(r.est)
        out[f"rob_no_{key}_ci"] = ci(r.lo95, r.hi95)
    for k, spec in (("minmax", "explore_support_minmax"), ("q5_95", "explore_support_q5_95")):
        r = s_.loc[(spec, "att")]
        out[f"size_{k}"] = pc(r.att)
        out[f"size_{k}_ci"] = ci(r.lo95, r.hi95)
        out[f"size_{k}_treated"] = n(r.n_treated)
    for pol in ("pm25", "pm10"):
        q = lbp[lbp.pollutant == pol]
        g = lambda e, q=q: q[q.estimator == e].iloc[0]  # noqa: E731
        its, did, dcm = g("ITS"), g("DiD"), g("DiD, city means")
        out[f"lb_{pol}"] = {
            "its": pc(its.est), "its_ci": ci(its.lo95, its.hi95), "did": pc(did.est), "did_ci": ci(did.lo95, did.hi95),
            "did_cm": pc(dcm.est), "did_cm_ci": ci(dcm.lo95, dcm.hi95),
            "cities": n(its.cities), "single": n(its.single_station_cities), "stations": n(its.stations),
            "controls": n(its.control_cities),
        }  # fmt: skip
        rb = rob[rob.layer == f"B {pol}"]
        jb = rb[rb.agrees.notna()]
        out[f"lb_{pol}"]["rob_agree"] = n((jb.agrees.astype(str).str.lower() == "true").sum())
        out[f"lb_{pol}"]["rob_judged"] = n(len(jb))
    out["no2019_its"] = pc(lb[(lb.version == "no2019") & (lb.pollutant == "pm25") & (lb.estimator == "ITS")].est.iloc[0])
    return out


def maiac() -> dict:
    r = RM.results()
    pr = r["specs"]["aod_primary"]
    x = json.loads((RM.MOUT / "exploratory_notgained.json").read_text(encoding="utf-8"))["groups"]
    specs = r["specs"]
    below = sum(v["aod"][0] < v["acag"][0] for v in specs.values())
    above0 = sum(v["aod"][1] > 0 for v in specs.values())
    nm = specs["aod_nonmonsoon"]
    es = r["event_study"]
    t3 = lambda v: (pc(v[0]), ci(v[1], v[2]))  # noqa: E731
    return {
        "aod": t3(pr["aod"])[0], "aod_ci": t3(pr["aod"])[1], "acag": t3(pr["acag"])[0], "acag_ci": t3(pr["acag"])[1],
        "q1": pr["q1"]["label"], "q2": pr["q2"]["label"],
        "treated": n(pr["n_treated"]), "controls": n(pr["n_controls"]),
        "gained": n(pr["n_gained"]), "notgained": n(pr["n_notgained"]),
        "diff": t3(pr["diff"])[0], "diff_ci": t3(pr["diff"])[1],
        "acag_diff": t3(pr["acag_diff"])[0], "acag_diff_ci": t3(pr["acag_diff"])[1],
        "specs": n(len(specs)), "below": n(below), "above0": n(above0),
        "nonmonsoon": t3(nm["aod"])[0], "nonmonsoon_ci": t3(nm["aod"])[1], "nonmonsoon_q1": nm["q1"]["label"],
        "es_avg": pc(es["avg_post"]["coef"]), "es_ci": ci(es["avg_post"]["lo95"], es["avg_post"]["hi95"]),
        "es_p": pval(es["wald_pre"]["p"]),
        "ng_aod": t3(x["notgained"]["aod"])[0], "ng_aod_ci": t3(x["notgained"]["aod"])[1],
        "ng_acag": t3(x["notgained"]["acag"])[0], "ng_acag_ci": t3(x["notgained"]["acag"])[1],
        "g_aod": t3(x["gained"]["aod"])[0], "g_acag": t3(x["gained"]["acag"])[0],
    }  # fmt: skip


def heterogeneity() -> dict:
    from src.hierarchical import report as HR

    X = HR.load()
    e, c, co = X["e"], X["c"], X["co"]
    c = c[c.version == "primary"]
    cf = lambda v, p: co[(co.version == v) & (co.param == p)].iloc[0]  # noqa: E731
    b = lambda v, p: (pc(cf(v, p)["mean"]), ci(cf(v, p).lo95, cf(v, p).hi95))  # noqa: E731
    est_pct = 100 * (np.exp(e.est) - 1)
    width = (c.rank_hi95 - c.rank_lo95).median()  # as in docs/heterogeneity_report.md
    h3 = X["h3"]
    r = X["r"]
    rr = lambda ser, est: r[(r.series == ser) & (r.estimator == est)].iloc[0]  # noqa: E731
    dc = X["dc"]
    dose = lambda v: dc[(dc.version == v) & (dc.param == "per doubling of dose")].iloc[0]  # noqa: E731
    ws = X["ws"][X["ws"]["count"] >= 2]  # states with two or more UAs, as in docs/heterogeneity_report.md
    out = {
        "units": n(len(e)),
        "mean": pc(e.est.mean()), "min": pv(est_pct.min()), "max": pv(est_pct.max()),
        "above0": n((e.est > 0).sum()),
        "bh_pass": n(e.bh_reject.sum()), "unadj_p05": n((e.p_placebo < 0.05).sum()),
        "se_2019": u(e[e.cohort == 2019].se.iloc[0], 3), "se_later": u(e[e.cohort == 2021].se.iloc[0], 3),
        "tau": u(cf("primary", "tau")["mean"], 3),
        "avg": b("primary", "average city-level relative change")[0],
        "avg_ci": b("primary", "average city-level relative change")[1],
        "beta_baseline": b("primary", "beta[baseline_pm25]")[0], "beta_baseline_ci": b("primary", "beta[baseline_pm25]")[1],
        "beta_coastal": b("primary", "beta[coastal]")[0], "beta_coastal_ci": b("primary", "beta[coastal]")[1],
        "beta_xvfc": b("primary", "beta[xvfc]")[0], "beta_xvfc_ci": b("primary", "beta[xvfc]")[1],
        "beta_logpop": b("primary", "beta[log_pop]")[0], "beta_logpop_ci": b("primary", "beta[log_pop]")[1],
        "h5": b("primary", "beta[igp]")[0], "h5_ci": b("primary", "beta[igp]")[1],
        "h5_verdict": "met" if X["h5"]["rule_met"] else "not met",
        "igp_only": b("igp_only", "beta[igp]")[0], "igp_only_ci": b("igp_only", "beta[igp]")[1],
        "cri_above": n((c.post_lo95 > 0).sum()), "cri_below": n((c.post_hi95 < 0).sum()),
        "cri_span": n(((c.post_lo95 <= 0) & (c.post_hi95 >= 0)).sum()),
        "rank_width": n(width),
        "converged": n(X["dg"].converged.sum()), "models": n(len(X["dg"])),
        "corr_xvfc_pop": u(X["corr"].loc["xvfc", "log_pop"], 2), "corr_igp_base": u(X["corr"].loc["igp", "baseline_pm25"], 2),
        "h3_verdict": h3["verdict"],
        "h3_i": yes(h3["i_met"]), "h3_ii": yes(h3["ii_met"]), "h3_iii": yes(h3["iii_met"]),
        "h3_ii_its": n(h3["ii_count"]["ITS"]), "h3_ii_did": n(h3["ii_count"]["DiD"]),
        "ratio_its": pc(rr("deweathered", "ITS").est), "ratio_its_ci": ci(rr("deweathered", "ITS").lo95, rr("deweathered", "ITS").hi95),
        "ratio_did": pc(rr("deweathered", "DiD").est), "ratio_did_ci": ci(rr("deweathered", "DiD").lo95, rr("deweathered", "DiD").hi95),
        "h3_cities": n(rr("deweathered", "ITS").cities),
        "dose_units": n(dose("dose").units),
        "dose": pc(dose("dose")["mean"]), "dose_ci": ci(dose("dose").lo95, dose("dose").hi95),
        "dose_igp": pc(dose("dose_igp")["mean"]), "dose_notop": pc(dose("dose_no_top")["mean"]),
        "dose_state_spread_median": u(ws.range_pct_of_mean.median()) + "%",
        "dose_state_spread_max": u(ws.range_pct_of_mean.max()) + "%",
        "dose_states": n(len(ws)),
        "dose_state_min": "Rs " + n(X["ws"]["mean"].min()), "dose_state_max": "Rs " + n(X["ws"]["mean"].max()),
    }  # fmt: skip
    return out


def figures() -> dict:
    out = {}
    for p in sorted(FIGURES.glob("*.json")):
        m = json.loads(p.read_text(encoding="utf-8"))
        out[m["name"]] = {k: str(m[k]) for k in ("number", "title", "question", "caption", "alt")}
    return out


# ---------------------------------------------------------------- tables


def tables(V: dict) -> dict[str, str]:
    c, h, co, m = V["causal"], V["het"], V["comp"], V["maiac"]
    T = {}
    T["hypotheses"] = md(pd.DataFrame([
        ["H1", "confirmatory", "A", "NCAP enrolment reduced annual population-weighted PM2.5 relative to comparable centres", f"not identified by this design (pre-trend Wald p = {c['wald_p']})"],
        ["H2", "confirmatory, only if H1 is supported", "A", "the reduction is larger in winter", ("tested" if c["h2_tested"] == "yes" else "not tested (H1 not supported); exploratory difference ") + c["h2_diff"]],
        ["H3", "secondary", "B", "PM10 fell more than PM2.5 and the PM2.5/PM10 ratio rose (dust control)", h["h3_verdict"]],
        ["H4", "secondary, descriptive", "B", "reported improvements exceed weather- and composition-corrected ones", f"supported: PM2.5 {co['primary_pm25']['h4']} pp, PM10 {co['primary_pm10']['h4']} pp"],
        ["H5", "secondary", "A", "smaller (less negative) changes in Indo-Gangetic Plain centres", f"registered rule {h['h5_verdict']}"],
    ], columns=["", "status", "layer", "hypothesis (registered)", "result"]))  # fmt: skip
    T["h1_rules"] = md(pd.DataFrame([
        ["(a) primary SDID estimate < 0, 95% CI entirely below 0", f"{c['att']} ({c['ci']})", c["met_a"]],
        [f"(b) event-study pre-period coefficients jointly zero (Wald p > {c['wald_min']})", f"χ² = {c['wald_stat']}, {c['wald_df']} df, p = {c['wald_p']}", c["met_b"]],
        ["(c) 2016 placebo-in-time 95% CI includes 0", f"{c['placebo2016']} ({c['placebo2016_ci']})", c["met_c"]],
        ["(d) negative in Callaway & Sant'Anna, area-weighted and V6.GL.03", f"{c['cs']}; {c['area']}; {c['v6']}", c["met_d"]],
    ], columns=["registered rule (as read in DEC-135)", "value", "met"]))  # fmt: skip
    rows = []
    for vk, lab in (("primary", "Primary (GAM)"), ("lgbm", "LightGBM"), ("asreg", "As registered, no deviations")):
        for pol, pn in (("pm25", "PM2.5"), ("pm10", "PM10")):
            r = co[f"{vk}_{pol}"]
            rows.append([lab, pn, f"{r['cities']} ({r['single']})", r["reported"], r["corrected"], r["unmodelled"],
                         r["weather"], r["composition"], f"{r['h4']} ({r['ci']})", r["supported"]])  # fmt: skip
    T["h4"] = md(pd.DataFrame(rows, columns=["version", "pollutant", "cities (single-station)", "reported change", "corrected change",
                                             "unmodelled (pp)", "modelled weather (pp)", "composition (pp)", "H4, pp (95% CI)", "verdict"]))  # fmt: skip
    rows = []
    for pol, pn in (("pm25", "PM2.5"), ("pm10", "PM10")):
        b = c[f"lb_{pol}"]
        sc = f"{b['cities']} NCAP cities ({b['single']} single-station) vs {b['controls']} control cities"
        rows += [[pn, "ITS (before–after)", f"{b['its']} ({b['its_ci']})", sc],
                 [pn, "ground DiD (stations)", f"{b['did']} ({b['did_ci']})", sc],
                 [pn, "ground DiD (city means)", f"{b['did_cm']} ({b['did_cm_ci']})", sc]]  # fmt: skip
    T["layer_b"] = md(pd.DataFrame(rows, columns=["pollutant", "estimator", "estimate (95% CI)", "scope"]))
    rob = pd.read_csv(A.OUT / "robustness.csv")
    ra = rob[rob.layer == "A"].copy()

    def est(r):
        if r.check.startswith("Placebo in space"):
            return f"p = {r.est:.3f}"
        if pd.isna(r.lo95):
            return pc(r.est)
        return f"{pc(r.est)} ({ci(r.lo95, r.hi95)})"

    ra["estimate (95% CI)"] = ra.apply(est, axis=1)
    ra["agrees"] = ra.agrees.map(lambda v: "—" if pd.isna(v) else ("yes" if str(v).lower() == "true" else "**no**"))
    ra.loc[ra.check == "Raw MAIAC AOD", "estimate (95% CI)"] += " (AOD, not PM2.5)"
    T["robustness_a"] = md(ra[["check", "estimate (95% CI)", "agrees"]].rename(columns={"check": "registered check (Layer A)"}))
    T["maiac"] = md(pd.DataFrame([
        ["Primary: population-weighted, best-quality retrievals", f"{m['aod']} ({m['aod_ci']})", f"{m['acag']} ({m['acag_ci']})", m["q1"]],
        ["Monitor-gain gap (gained − not gained)", f"{m['diff']} ({m['diff_ci']})", f"{m['acag_diff']} ({m['acag_diff_ci']})", m["q2"]],
        ["Exploratory: units that gained no monitor", f"{m['ng_aod']} ({m['ng_aod_ci']})", f"{m['ng_acag']} ({m['ng_acag_ci']})", "diverge (exploratory, DEC-188)"],
    ], columns=["specification", "raw AOD (direction only)", "ACAG PM2.5, same units", "pre-written reading"]))  # fmt: skip
    T["deviations"] = (REPORTS / "deviations.md").read_text(encoding="utf-8")
    return T


# ---------------------------------------------------------------- main


def build() -> tuple[dict, dict]:
    V = {
        "links": LINKS,
        "set": settings(),
        "units": ncap_and_units(),
        "audit": network_and_audit(),
        "dw": deweathering(),
        "comp": composition(),
        "causal": causal(),
        "maiac": maiac(),
        "het": heterogeneity(),
        "fig": figures(),
    }
    T = tables(V)
    return V, T


def strings(x) -> list[str]:
    if isinstance(x, dict):
        return [t for v in x.values() for t in strings(v)]
    if isinstance(x, (list, tuple)):
        return [t for v in x for t in strings(v)]
    return [str(x)]


def main() -> None:
    V, T = build()
    for t in strings(V):
        for line in t.split("\n"):
            wording.check(line, "reports/_variables.yml")
    for k, t in T.items():
        if k == "deviations":
            continue  # included verbatim from reports/deviations.md, checked by tests/test_report.py
        for line in t.split("\n"):
            wording.check(line, f"reports/_generated/{k}.md")
    VARS.write_text("# Generated by `python -m src.report.values`. Do not edit by hand.\n"
                    + yaml.safe_dump(V, allow_unicode=True, sort_keys=True, width=1000), encoding="utf-8")  # fmt: skip
    GEN.mkdir(parents=True, exist_ok=True)
    for k, t in T.items():
        if k == "deviations":
            continue
        (GEN / f"{k}.md").write_text(t, encoding="utf-8")
    from src.report import readme

    for line in readme.block(V).split("\n"):
        wording.check(line, "README.md headline findings")
    rd = REPORTS.parent / "README.md"
    rd.write_text(readme.sync(rd.read_text(encoding="utf-8"), V), encoding="utf-8")
    print(f"wrote {VARS} ({len(strings(V))} values), {len(T) - 1} tables in {GEN}, and the README's headline findings")


if __name__ == "__main__":
    main()

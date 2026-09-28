"""docs/deweathering_report.md: the Phase 5 results, generated from the full run (RQ2).

    python -m src.normalise.report

Every number comes from data/processed/deweathered/ (src.normalise.aggregate) and the run inputs.
Nothing here compares NCAP with non-NCAP cities: deweathering is fitted per station without NCAP
status. Rules and schemes: primary = seasonal resampling (DEC-109) and near-constant station-years
excluded (DEC-110); sensitivities = Grange & Carslaw resampling, registered flags only.
"""

import json

import numpy as np
import pandas as pd

from src.common.paths import DOCS
from src.normalise.aggregate import OUT
from src.normalise.features import INPUTS, cfg
from src.normalise.pilot import POL, md_table

FAM = {"lgbm": "LightGBM", "gam": "GAM (one-year knots)", "gam_k4": "GAM, previous trend (k = 4/yr)"}
FAMS = ("lgbm", "gam", "gam_k4")
SCHEME_NAME = {"": "seasonal", "_annual": "Grange & Carslaw"}
SCHEMES = {"dw": "seasonal (primary)", "dw_annual": "Grange & Carslaw (sensitivity)"}


def weather_by_year(sy: pd.DataFrame, col: str) -> pd.DataFrame:
    """How much weather raised or lowered each year's annual mean relative to typical 2015-2025
    weather: log(raw / deweathered) per valid station-year (primary rule and variant), centred per
    series (the smearing constant and fixed offsets drop out); median over stations, in %."""
    y = sy[(sy.rule == "primary") & (sy.variant == "q1_t75") & sy.valid & sy[col].notna()].copy()
    y["w"] = np.log(y.raw / y[col])
    y["w"] -= y.groupby(["sid", "pollutant"]).w.transform("mean")
    return y.groupby(["pollutant", "year"]).w.agg(["size", "median"]).reset_index()


def city_weather_share(cy: pd.DataFrame, col: str) -> pd.DataFrame:
    cy = cy[cy.rule == "primary"].sort_values(["pollutant", "unit_id", "year"])
    k = [cy.pollutant, cy.unit_id]
    w = np.log(cy.raw).groupby(k).diff() - np.log(cy[col]).groupby(k).diff()
    w = w.where(cy.groupby(["pollutant", "unit_id"]).year.diff() == 1)
    d = cy.assign(w=100 * w.abs(), raw_change=100 * np.log(cy.raw).groupby(k).diff().abs()).dropna(subset=["w"])
    return d.groupby("pollutant").agg(
        city_year_pairs=("w", "size"), cities=("unit_id", "nunique"),
        median_abs_raw_change_pct=("raw_change", "median"), median_abs_weather_pct=("w", "median"),
        p90_abs_weather_pct=("w", lambda s: s.quantile(0.9)),
    ).reset_index()  # fmt: skip


def trend_absorption(sm: pd.DataFrame) -> pd.DataFrame:
    """Within-year SD of log monthly means (valid station-years with >= 9 valid months), relative
    to the raw series. Under Grange & Carslaw resampling a deweathered series has no seasonal cycle
    of its own, so what is left shows how much within-year movement the trend term absorbed."""
    m = sm[(sm.rule == "primary") & sm.valid]
    cols = ["raw"] + [f"dw_{f}{x}" for x in ("", "_annual") for f in FAMS if f"dw_{f}{x}" in sm]
    g = m.groupby(["sid", "pollutant", "year"])
    sd = pd.concat([g[c].apply(lambda s: np.log(s).std() if len(s) >= 9 else np.nan).rename(c) for c in cols], axis=1)
    sd = sd.dropna()
    ratio = sd.div(sd.raw, axis=0).drop(columns="raw")
    out = ratio.groupby(level="pollutant").median().reset_index()
    out.insert(1, "station_years", sd.groupby(level="pollutant").size().to_numpy())
    return out.rename(columns={c: f"{c} / raw" for c in cols[1:]})


def implausible(sm: pd.DataFrame, sy: pd.DataFrame) -> pd.DataFrame:
    """Deweathered values far from what was measured (ratio to the raw mean over the same days), per
    family and scheme: valid station-months and station-years (primary rule, primary variant).
    Weather normalisation should move a month or year by tens of %, not multiples."""
    m = sm[(sm.rule == "primary") & sm.valid]
    y = sy[(sy.rule == "primary") & (sy.variant == "q1_t75") & sy.valid]
    lo, hi = cfg()["guard_ratio"]
    rows = []
    for fam in FAMS:
        for sfx, scheme in SCHEME_NAME.items():
            col = f"dw_{fam}{sfx}"
            if col not in y:
                continue
            rm, ry = m[col] / m.raw, y[col] / y.raw
            rows.append({"family": fam, "scheme": scheme, "station_years": len(ry),
                         f"years_over_{hi}x": int((ry > hi).sum()), f"years_under_{lo}x": int((ry < lo).sum()),
                         "years_over_2x": int((ry > 2).sum()), "max_year_ratio": float(ry.max()),
                         "min_year_ratio": float(ry.min()), "months_over_5x": int((rm > 5).sum())})  # fmt: skip
    return pd.DataFrame(rows)


def extrapolation() -> pd.DataFrame:
    """DEC-117 (a) and (b), from src.normalise.guard: shared by every family."""
    g = pd.read_parquet(OUT / "extrapolation.parquet")
    t = g[g.run == "main"].groupby("scheme")[["rows", "oor_rows", "oos_rows"]].sum()
    t["share_outside_training_range"] = t.oor_rows / t.rows
    t["share_out_of_season"] = t.oos_rows / t.rows
    t = t.reset_index().replace({"scheme": {"seasonal": "seasonal", "annual": "Grange & Carslaw"}})
    return t[["scheme", "rows", "share_outside_training_range", "share_out_of_season"]]


def watch_lines(sy: pd.DataFrame) -> str:
    """DEC-121: where each watch station stands (valid years under each rule, reliability)."""
    from src.common.paths import PROCESSED, params

    q = pd.read_parquet(PROCESSED / "station_year_quality.parquet")
    names = pd.read_csv(PROCESSED / "stations.csv").set_index("sid").sname
    out = []
    for sid in params().get("watch_stations", []):
        y = sy[(sy.sid == sid) & (sy.variant == "q1_t75")]
        for pol, g in y.groupby("pollutant"):
            yrs = {r: ", ".join(map(str, sorted(g[(g.rule == r) & g.valid].year))) or "none" for r in ("primary", "registered_flags")}
            rel = q[(q.sid == sid) & (q.pollutant == pol) & q.valid_q1_t75].reliability
            out.append(f"- **{names.get(sid, sid)}** ({sid}), {POL[pol]}: valid years, primary rule: {yrs['primary']}; "
                       f"registered flags only: {yrs['registered_flags']}. Reliability of its valid station-years "
                       f"{rel.min():.1f}–{rel.max():.1f}, so the registered reliability < 50 sensitivity removes "
                       f"{int((rel < 50).sum())} of them.")  # fmt: skip
    return "\n".join(out)


def main() -> None:
    c = cfg()
    choice = json.loads((OUT / "family_choice.json").read_text(encoding="utf-8"))
    mets_all = pd.read_parquet(OUT / "series_metrics.parquet")
    mets = mets_all[mets_all.run == "main"]
    sy = pd.read_parquet(OUT / "station_year.parquet")
    sm = pd.read_parquet(OUT / "station_month.parquet")
    cy = pd.read_parquet(OUT / "city_year.parquet")
    cm = pd.read_parquet(OUT / "city_month.parquet")
    series = pd.read_csv(INPUTS / "main" / "series.csv")
    reg = pd.read_csv(INPUTS / "registered" / "series.csv")
    skipped = series[series.skipped.notna()] if "skipped" in series else series.iloc[:0]
    done = series[series.skipped.isna()] if "skipped" in series else series
    lab = lambda d: d.assign(**{k: d[k].map(v) for k, v in (("family", FAM), ("pollutant", POL)) if k in d})  # noqa: E731
    pct, f3 = "{:.1f}", "{:.3f}"

    cov = done.groupby("pollutant").agg(
        series=("sid", "size"), median_fit_days=("n_fit", "median"), median_folds=("n_folds", "median"),
        no_cv_fold=("n_folds", lambda s: int((s == 0).sum())),
        with_excluded_years=("excluded_years", lambda s: int(s.fillna("").astype(str).str.len().gt(0).sum())),
    ).reset_index()  # fmt: skip
    sk = skipped.groupby(["pollutant", "skipped"]).size().rename("series").reset_index()
    r2 = mets.groupby(["family", "pollutant"]).agg(
        series=("r2_oos", "count"), r2_oos=("r2_oos", "median"), r2_oos_clamp=("r2_oos_clamp", "median"),
        r2_within=("r2_within", "median"), r2_in=("r2_in", "median"),
    ).reset_index()  # fmt: skip
    q = mets.groupby(["family", "pollutant"]).r2_oos.quantile([0.1, 0.25, 0.5, 0.75, 0.9]).unstack().reset_index()
    q.columns = ["family", "pollutant"] + [f"p{int(100 * x)}" for x in q.columns[2:]]
    acf = mets.groupby(["family", "pollutant"])[[f"acf_oos_{k}" for k in range(1, 8)]].median().reset_index()
    div = mets[mets.family == choice["primary"]]
    dv = div.groupby("pollutant").agg(series=("sid", "size"), with_D=("D_pct", "count"),
                                      median_D_pct=("D_pct", "median"), p90_D_pct=("D_pct", lambda s: s.quantile(0.9)),
                                      diverging=("diverges", "sum")).reset_index()  # fmt: skip
    top = div.dropna(subset=["D_pct"]).sort_values("D_pct", ascending=False).head(10)[["sid", "pollutant", "valid_years", "D_pct"]]
    wy = []
    for col, name in SCHEMES.items():
        t = weather_by_year(sy, col).pivot_table(index="year", columns="pollutant", values="median")
        t.columns = [f"{POL[p]}, {name.split(' ')[0]}" for p in t.columns]
        wy.append(100 * t)
    wy = pd.concat(wy, axis=1).reset_index()
    cws = pd.concat([lab(city_weather_share(cy, col)).assign(scheme=name) for col, name in SCHEMES.items()])
    ta = trend_absorption(sm)
    lt = json.loads((OUT / "lockdown_test.json").read_text(encoding="utf-8"))
    ltt = pd.read_csv(OUT / "lockdown_test.csv")
    ltt = ltt[ltt.valid].groupby("year").abs_diff_pct.agg(["size", "median", "max"]).reset_index()
    from src.normalise.city_disagreement import summary as cd_summary

    cdt = pd.read_csv(OUT / "city_disagreement.csv")
    cds = cd_summary(cdt)
    cdf = cdt[cdt.flag_seasonal | cdt.flag_grange][["panel", "city", "pollutant", "stations", "chg_raw", "chg_dw_gam",
                                                     "chg_dw_lgbm", "diff_pp_seasonal", "diff_pp_grange"]]  # fmt: skip
    wl = watch_lines(sy)
    imp = implausible(sm, sy)
    ext = extrapolation()
    lo_g, hi_g = c["guard_ratio"]
    mm = sm[(sm.rule == "primary") & sm.valid]
    worst = {}
    for f in ("gam_k4", "gam"):
        r = mm[f"dw_{f}_annual"] / mm.raw
        worst[f] = (mm.loc[r.idxmax()], float(r.max()), float(mm.month.dt.month[r > 5].isin([6, 7, 8, 9]).mean()) if (r > 5).any() else float("nan"))
    ia = imp.set_index(["family", "scheme"])
    y2 = lambda f: int(ia.loc[(f, "Grange & Carslaw"), "years_over_2x"])  # noqa: E731
    wk, wg = worst["gam_k4"], worst["gam"]
    gc_verdict = (
        f"With the one-year-knot trend (DEC-116), the GAM's Grange & Carslaw station-years more than 2x raw fall from "
        f"{y2('gam_k4')} to {y2('gam')}; its worst station-month ratio is {wg[1]:,.1f}x (previously {wk[1]:,.3g}x)."
    )
    reg_y = sy[(sy.variant == "q1_t75") & (sy.rule == "registered_flags")]
    nc = reg_y[reg_y.valid & reg_y.near_constant]  # valid under the registered rules, removed by DEC-110
    cy_n = cy.groupby(["rule", "pollutant"]).size().unstack("rule").reset_index()
    other = choice["sensitivity"]
    clamp_note = (
        f"Under the `clamp` convention the medians are LightGBM {choice['median_r2_oos_clamp']['lgbm']:.3f}, "
        f"GAM {choice['median_r2_oos_clamp']['gam']:.3f}, which would pick {FAM[choice['primary_under_clamp']]}"
        + (" too." if choice["primary_under_clamp"] == choice["primary"] else ": **the two conventions pick different families**.")
    ) if "median_r2_oos_clamp" in choice else ""

    text = f"""# Deweathering results (Phase 5, RQ2)

*Generated by `python -m src.normalise.report` from `data/processed/deweathered/`. Do not edit by hand. Rules: DEC-100 to DEC-113; pilot: [`deweathering_pilot.md`](deweathering_pilot.md); near-constant rule: [`near_constant_check.md`](near_constant_check.md). Nothing here compares NCAP with non-NCAP cities.*

**Primary specification:** weather resampled within ±{c['resample_window_days']} days of each date from ERA5 {c['weather_pool_years'][0]}–{c['weather_pool_years'][1]} (a registered-plan deviation, DEC-109), {c['resamples_default']} draws, near-constant station-years excluded (a registered-plan deviation, DEC-110), the GAM's trend with knots one year apart (a registered-plan deviation, DEC-116). **Sensitivities carried in every table:** Grange & Carslaw's all-year resampling (`dw_annual`), the registered flags only (`rule = registered_flags`), the other competing family, and the previous GAM trend (`gam_k4`, 4 basis functions per year).

## 1. Coverage

Station-pollutant series with ≥ {c['min_fit_days']} valid days to {c['fit_end']}, each fitted by both families:

{md_table(lab(cov), {"median_fit_days": "{:.0f}", "median_folds": "{:.0f}"})}

`with_excluded_years`: series fitted without their near-constant station-years (primary). The {len(reg[reg.get('skipped', pd.Series(np.nan, index=reg.index)).isna()])} series with such years were also refitted with them kept (registered-flags sensitivity).

Not deweathered:

{md_table(lab(sk)) if len(sk) else "None."}

## 2. Primary model family (registered rule, DEC-088)

Median out-of-sample R² (log scale; blocked forward-chaining CV by year; `{c['cv_trend']}` test-year trend, DEC-107) over the {choice['series_with_cv']} series with a CV fold: **LightGBM {choice['median_r2_oos']['lgbm']:.3f}, GAM {choice['median_r2_oos']['gam']:.3f}. Primary: {FAM[choice['primary']]}; {FAM[other]} is the sensitivity analysis.** The GAM predicts better in {choice['series_where_gam_better']} of {choice['series_with_cv']} series. {clamp_note} The choice is between LightGBM and the refitted GAM (DEC-117); the previous GAM (`gam_k4`) is shown in the tables below but does not compete.

Median R² by family and pollutant: the registered metric (`r2_oos`), the same under the `clamp` convention, the within-period blocked CV (`r2_within`: months held out with a {c['cv_within_buffer_days']}-day buffer, each predicted with its own trend; a diagnostic of the weather response, never used for the choice, DEC-112), and in-sample:

{md_table(lab(r2), {k: f3 for k in ["r2_oos", "r2_oos_clamp", "r2_within", "r2_in"]})}

Distribution of `r2_oos`:

{md_table(lab(q), {k: f3 for k in q.columns if k[1:].isdigit()})}

Residual autocorrelation (median, out-of-sample, lags 1–7):

{md_table(lab(acf), {k: "{:.2f}" for k in acf.columns if k.startswith("acf")})}

## 3. Where the two families diverge (DEC-111)

D = the largest gap, over a series' valid years (primary rule), between the two families' log annual deweathered means, each centred on its own mean over those years (%). It measures disagreement in how the level moves, not in the level itself. D needs ≥ {c['divergence_min_years']} valid years; a series diverges if D > {c['divergence_flag_pct']}%.

{md_table(lab(dv), {"median_D_pct": pct, "p90_D_pct": pct, "diverging": "{:.0f}"})}

Largest:

{md_table(lab(top), {"D_pct": pct})}

## 4. How much weather moved annual numbers, under both resampling schemes

Weather effect in a year = log(raw annual mean / deweathered annual mean) per valid station-year, centred within each series; median over stations valid that year, in % (positive: that year's weather raised the annual mean). 2020 is included: its fall is mostly the lockdown, an emissions change, not weather. The GAM's one-year-knot trend (DEC-116) cannot follow a shock lasting a few months, so the deweathered 2020 value partly averages the lockdown out, and the 2020 weather effect here also contains part of the lockdown; read 2020 with care (it is flagged `covid_2020` in every table).

{md_table(wy, {k: "{:+.1f}" for k in wy.columns if k != "year"})}

City level (all-station city-year means, consecutive valid years), both schemes:

{md_table(cws, {"median_abs_raw_change_pct": pct, "median_abs_weather_pct": pct, "p90_abs_weather_pct": pct})}

H4 (raw minus deweathered balanced-panel change, 2018–2025) needs the balanced panel and is computed in Phase 6, under both schemes and both validity rules.

## 5. How much the trend term absorbs

Under Grange & Carslaw resampling a deweathered series should keep almost none of the raw series' within-year movement, because day of year is resampled too. What it keeps shows how much within-year variation the trend term followed (and so, possibly, year-specific weather such as a stagnant month). Median within-year SD of log monthly means relative to raw:

{md_table(lab(ta), {k: "{:.2f}" for k in ta.columns if "/ raw" in k})}

Under the seasonal scheme most within-year movement is kept by design (the seasonal cycle).

**Extrapolation guard (DEC-117).** (a) and (b) come from the training data and the draws, which every family shares; (c) shows how each family behaves on them. Nothing is dropped.

(a) resampled prediction rows with any weather input outside the station's training range, and (b) rows pairing a day with another season (more than ±{c['resample_window_days']} days of day of year away):

{md_table(ext, {"rows": "{:,.0f}", "share_outside_training_range": "{:.4f}", "share_out_of_season": "{:.4f}"})}

(c) valid station-years (primary rule) whose deweathered mean is more than {hi_g}x or less than {lo_g}x the raw mean over the same days (flagged `guard_<column>` in `station_year.parquet`), with more extreme counts and the station-month count above 5x:

{md_table(lab(imp), {"max_year_ratio": "{:,.2f}", "min_year_ratio": "{:.2f}"})}

What (a) and (b) say together: only a small share of draws take weather outside what a station was trained on, but under Grange & Carslaw almost every draw pairs a day with another season. The extreme values in (c) therefore come from out-of-season *combinations* (a day's trend value with another season's day of year and weather), not from weather values the model never saw. A GAM's smooths extrapolate linearly on the log scale and a deweathered value is a mean of exponentials, so a few such draws can dominate; trees cannot extrapolate. Under the previous GAM trend the worst case was {wk[0].sid} in {wk[0].month:%B %Y}: {wk[0].dw_gam_k4_annual:,.0f} µg/m³ against a measured {wk[0].raw:.0f}. {gc_verdict} Under the primary seasonal scheme no pairing is out of season.

## 6. Near-constant station-years (DEC-110)

{len(nc)} station-years that the registered rules keep (to {c['fit_end'][:4]}; {(nc.pollutant == 'pm25').sum()} PM2.5, {(nc.pollutant == 'pm10').sum()} PM10, at {nc.sid.nunique()} stations) are excluded in the primary analysis. City-years per rule:

{md_table(lab(cy_n))}

## 7. Lockdown smear test (DEC-119, rule fixed before the test)

The one-year-knot trend cannot follow the spring-2020 lockdown dip, which might pull 2019 and 2021 deweathered annual means with it. Test: the GAM plus a 0/1 term for the national lockdown days ({c['lockdown'][0]} to {c['lockdown'][1]}), fitted on the {lt['series']} pilot series from the full-run inputs (the term entered {lt['series_with_lockdown_term']} of them), compared with the current GAM. Metric: median |difference| in deweathered annual means over valid 2019 and 2021 station-years ({lt['station_years_2019_2021']}), seasonal scheme.

**Result: {lt['median_abs_diff_pct_2019_2021']:.2f}%, {"above" if lt['adopt_indicator'] else "below"} the {lt['threshold_pct']}% threshold, so {"the indicator is adopted for all stations" if lt['adopt_indicator'] else "the model is left as it is"}.** Separately: 2019 {lt['median_abs_diff_pct_2019']:.2f}%, 2021 {lt['median_abs_diff_pct_2021']:.2f}%, 2020 {lt['median_abs_diff_pct_2020']:.2f}% (largest 2019/2021 difference {lt['max_abs_diff_pct_2019_2021']:.1f}%). Any smear falls mostly backward, on 2019. By year:

{md_table(ltt.rename(columns={"size": "station_years", "median": "median_abs_diff_pct", "max": "max_abs_diff_pct"}), {"median_abs_diff_pct": "{:.2f}", "max_abs_diff_pct": "{:.2f}"})}

## 8. Family disagreement at city level, on the H4 quantity (DEC-120)

Per urban centre: the change in the deweathered mean from 2018 to 2025 over a balanced panel of stations inside the polygon (strict: valid 2018 and every year to 2025; loose: valid in 2018 and 2025), for the GAM and LightGBM; disagreement = GAM change − LightGBM change, in percentage points (primary validity rule). Every city with a panel is included (no NCAP comparison):

{md_table(lab(cds), {k: "{:.1f}" for k in ["median_abs_diff_pp", "p90_abs_diff_pp", "max_abs_diff_pp", "median_diff_pp"]})}

Cities where the families differ by more than 5 pp (either scheme), with the raw change over the same panel for scale:

{md_table(lab(cdf), {k: "{:+.1f}" for k in ["chg_raw", "chg_dw_gam", "chg_dw_lgbm", "diff_pp_seasonal", "diff_pp_grange"]})}

Most panels hold a single station (median {int(cdt.stations.median())} per city), so a city's change here is often one monitor's. Where the families disagree by several points, how much of a city's measured change H4 attributes to weather depends on the model family; Phase 6 reports H4 under both.

## 9. Named stations (DEC-121)

{wl}

## 10. Outputs

`data/processed/deweathered/`: `series_metrics`, `family_choice.json`, `station_day`, `station_year` (2 rules × 4 completeness variants), `station_month`, `city_month` ({cm.unit_id.nunique()} urban centres), `city_year` ({cy.unit_id.nunique()}). Columns `dw` (primary family, seasonal) and `dw_annual` (primary family, Grange & Carslaw), plus each family's. City series are all-station means over stations inside the urban-centre polygon (DEC-105); the balanced panel is Phase 6. Figure 3: `reports/figures/fig3_deweathered` (seasonal) and `fig3_deweathered_grange_carslaw`.
"""
    (DOCS / "deweathering_report.md").write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()

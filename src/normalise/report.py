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
from src.normalise.pilot import FAM, POL, md_table

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
    cols = ["raw", "dw_lgbm", "dw_gam", "dw_lgbm_annual", "dw_gam_annual"]
    g = m.groupby(["sid", "pollutant", "year"])
    sd = pd.concat([g[c].apply(lambda s: np.log(s).std() if len(s) >= 9 else np.nan).rename(c) for c in cols], axis=1)
    sd = sd.dropna()
    ratio = sd.div(sd.raw, axis=0).drop(columns="raw")
    out = ratio.groupby(level="pollutant").median().reset_index()
    out.insert(1, "station_years", sd.groupby(level="pollutant").size().to_numpy())
    return out.rename(columns={c: f"{c} / raw" for c in cols[1:]})


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
    nc = sy[(sy.variant == "q1_t75") & (sy.rule == "primary") & sy.near_constant]
    cy_n = cy.groupby(["rule", "pollutant"]).size().unstack("rule").reset_index()
    other = choice["sensitivity"]
    clamp_note = (
        f"Under the `clamp` convention the medians are LightGBM {choice['median_r2_oos_clamp']['lgbm']:.3f}, "
        f"GAM {choice['median_r2_oos_clamp']['gam']:.3f}, which would pick {FAM[choice['primary_under_clamp']]}"
        + (" too." if choice["primary_under_clamp"] == choice["primary"] else ": **the two conventions pick different families**.")
    ) if "median_r2_oos_clamp" in choice else ""

    text = f"""# Deweathering results (Phase 5, RQ2)

*Generated by `python -m src.normalise.report` from `data/processed/deweathered/`. Do not edit by hand. Rules: DEC-100 to DEC-113; pilot: [`deweathering_pilot.md`](deweathering_pilot.md); near-constant rule: [`near_constant_check.md`](near_constant_check.md). Nothing here compares NCAP with non-NCAP cities.*

**Primary specification:** weather resampled within ±{c['resample_window_days']} days of each date from ERA5 {c['weather_pool_years'][0]}–{c['weather_pool_years'][1]} (a registered-plan deviation, DEC-109), {c['resamples_default']} draws, near-constant station-years excluded (a registered-plan deviation, DEC-110). **Sensitivities carried in every table:** Grange & Carslaw's all-year resampling (`dw_annual`), and the registered flags only (`rule = registered_flags`).

## 1. Coverage

Station-pollutant series with ≥ {c['min_fit_days']} valid days to {c['fit_end']}, each fitted by both families:

{md_table(lab(cov), {"median_fit_days": "{:.0f}", "median_folds": "{:.0f}"})}

`with_excluded_years`: series fitted without their near-constant station-years (primary). The {len(reg[reg.get('skipped', pd.Series(np.nan, index=reg.index)).isna()])} series with such years were also refitted with them kept (registered-flags sensitivity).

Not deweathered:

{md_table(lab(sk)) if len(sk) else "None."}

## 2. Primary model family (registered rule, DEC-088)

Median out-of-sample R² (log scale; blocked forward-chaining CV by year; `{c['cv_trend']}` test-year trend, DEC-107) over the {choice['series_with_cv']} series with a CV fold: **LightGBM {choice['median_r2_oos']['lgbm']:.3f}, GAM {choice['median_r2_oos']['gam']:.3f}. Primary: {FAM[choice['primary']]}; {FAM[other]} is the sensitivity analysis.** The GAM predicts better in {choice['series_where_gam_better']} of {choice['series_with_cv']} series. {clamp_note}

Median R² by family and pollutant: the registered metric (`r2_oos`), the same under the `clamp` convention, the within-period blocked CV (`r2_within`: months held out with a {c['cv_within_buffer_days']}-day buffer, each predicted with its own trend; a diagnostic of the weather response, never used for the choice, DEC-112), and in-sample:

{md_table(lab(r2), {k: f3 for k in ["r2_oos", "r2_oos_clamp", "r2_within", "r2_in"]})}

Distribution of `r2_oos`:

{md_table(lab(q), {k: f3 for k in q.columns if k.startswith("p")})}

Residual autocorrelation (median, out-of-sample, lags 1–7):

{md_table(lab(acf), {k: "{:.2f}" for k in acf.columns if k.startswith("acf")})}

## 3. Where the two families diverge (DEC-111)

D = the largest gap, over a series' valid years (primary rule), between the two families' log annual deweathered means, each centred on its own mean over those years (%). It measures disagreement in how the level moves, not in the level itself. D needs ≥ {c['divergence_min_years']} valid years; a series diverges if D > {c['divergence_flag_pct']}%.

{md_table(lab(dv), {"median_D_pct": pct, "p90_D_pct": pct, "diverging": "{:.0f}"})}

Largest:

{md_table(lab(top), {"D_pct": pct})}

## 4. How much weather moved annual numbers, under both resampling schemes

Weather effect in a year = log(raw annual mean / deweathered annual mean) per valid station-year, centred within each series; median over stations valid that year, in % (positive: that year's weather raised the annual mean). 2020 is included: its fall is mostly the lockdown, an emissions change that deweathering leaves in (it is flagged `covid_2020` in every table).

{md_table(wy, {k: "{:+.1f}" for k in wy.columns if k != "year"})}

City level (all-station city-year means, consecutive valid years), both schemes:

{md_table(cws, {"median_abs_raw_change_pct": pct, "median_abs_weather_pct": pct, "p90_abs_weather_pct": pct})}

H4 (raw minus deweathered balanced-panel change, 2018–2025) needs the balanced panel and is computed in Phase 6, under both schemes and both validity rules.

## 5. How much the trend term absorbs

Under Grange & Carslaw resampling a deweathered series should keep almost none of the raw series' within-year movement, because day of year is resampled too. What it keeps shows how much within-year variation the trend term followed (and so, possibly, year-specific weather such as a stagnant month). Median within-year SD of log monthly means relative to raw:

{md_table(lab(ta), {k: "{:.2f}" for k in ta.columns if "/ raw" in k})}

Under the seasonal scheme most within-year movement is kept by design (the seasonal cycle).

## 6. Near-constant station-years (DEC-110)

{len(nc)} station-pollutant-years are excluded in the primary analysis. City-years per rule:

{md_table(lab(cy_n))}

## 7. Outputs

`data/processed/deweathered/`: `series_metrics`, `family_choice.json`, `station_day`, `station_year` (2 rules × 4 completeness variants), `station_month`, `city_month` ({cm.unit_id.nunique()} urban centres), `city_year` ({cy.unit_id.nunique()}). Columns `dw` (primary family, seasonal) and `dw_annual` (primary family, Grange & Carslaw), plus each family's. City series are all-station means over stations inside the urban-centre polygon (DEC-105); the balanced panel is Phase 6. Figure 3: `reports/figures/fig3_deweathered` (seasonal) and `fig3_deweathered_grange_carslaw`.
"""
    (DOCS / "deweathering_report.md").write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()

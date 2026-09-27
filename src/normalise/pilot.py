"""Deweathering pilot on about 20 stations across regions (Phase 5, DEC-103, DEC-104).

    python -m src.normalise.pilot select    -> data/interim/normalise/pilot_stations.csv
    python -m src.normalise.pilot report    -> docs/deweathering_pilot.md (+ tables in
                                               data/interim/normalise/pilot/)

Selection: stations with a coordinate and at least pilot.min_valid_days valid days (primary rule, to
fit_end) of BOTH PM2.5 and PM10, drawn at random (config seed) within each region, at most one per
urban centre (a random eligible centre, then a random eligible station in it), so that no city
dominates: per_region each, and a region's shortfall goes to the regions with the most eligible
centres, until n_stations. Region is the station's urban-centre region (DEC-075).
"""

import sys

import numpy as np
import pandas as pd

from src.common.paths import DOCS, INTERIM, PROCESSED, params
from src.normalise import collect
from src.normalise.store import cvcheck_path
from src.normalise.features import (
    INPUTS,
    POLLUTANTS,
    cfg,
    forward_folds,
    load_station_day,
    series_dir,
    station_cells,
    valid_day_hours,
)

PILOT = INTERIM / "normalise" / "pilot"
STATIONS_CSV = INTERIM / "normalise" / "pilot_stations.csv"


def allocate(eligible: pd.Series, total: int, per_region: int) -> pd.Series:
    """Stations per region: per_region each (or all a region has), shortfall to the largest regions."""
    take = eligible.clip(upper=per_region)
    for region in eligible.sort_values(ascending=False, kind="stable").index:
        extra = min(total - take.sum(), eligible[region] - take[region])
        if extra > 0:
            take[region] += extra
    return take


def select() -> pd.DataFrame:
    c = cfg()["pilot"]
    day = pd.read_parquet(
        PROCESSED / "station_day.parquet", columns=["sid", "date_ist", "pm25_h1", "pm10_h1"]
    )
    day = day[day.date_ist <= pd.Timestamp(cfg()["fit_end"])]
    h = valid_day_hours()
    v = day.assign(**{p: day[f"{p}_h1"] >= h for p in POLLUTANTS}).groupby("sid")[list(POLLUTANTS)].sum()
    reg = pd.read_csv(INTERIM / "station_regions.csv").set_index("sid")
    st = pd.read_csv(PROCESSED / "stations.csv").set_index("sid")
    v = v.join(reg[["unit_id", "region"]]).join(st[["sname", "city", "lat", "lon", "coord_quality"]])
    ok = v[(v[list(POLLUTANTS)] >= c["min_valid_days"]).all(axis=1) & v.lat.notna()]
    take = allocate(ok.groupby("region").unit_id.nunique(), c["n_stations"], c["per_region"])
    rng = np.random.default_rng(params()["seed"])
    picks = []
    for region in sorted(take.index):
        units = np.sort(ok[ok.region == region].unit_id.unique())
        for u in np.sort(rng.choice(units, take[region], replace=False)):
            pool = ok[ok.unit_id == u].sort_index()
            picks.append(pool.iloc[[rng.integers(len(pool))]])
    out = pd.concat(picks).reset_index()
    out = out.rename(columns={"pm25": "valid_days_pm25", "pm10": "valid_days_pm10"})
    STATIONS_CSV.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(STATIONS_CSV, index=False)
    print(out[["sid", "sname", "region", "valid_days_pm25", "valid_days_pm10"]].to_string())
    return out


# --- report ---------------------------------------------------------------------------------------

FAMILIES = ("lgbm", "gam")
FAM = {"lgbm": "LightGBM", "gam": "GAM"}
POL = {"pm25": "PM2.5", "pm10": "PM10"}


def load_all(run: str = "pilot") -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Metrics, daily values and timings of every task of a run."""
    series = pd.read_csv(INPUTS / run / "series.csv")
    series = series[series.get("skipped", pd.Series(np.nan, index=series.index)).isna()]
    mets, days, times = [], [], []
    conv = cfg()["cv_trend"]
    for r in series.itertuples():
        for fam in FAMILIES:
            out, js = collect.load(run, fam, r.pollutant, r.sid)
            cvp = cvcheck_path(run, fam, conv, r.pollutant, r.sid)
            if cvp.exists():  # CV under the configured test-year trend convention (DEC-107)
                cv = pd.read_parquet(cvp)
                out["cv_pred"], out["cv_fold"] = cv.cv_pred.to_numpy(), cv.cv_fold.to_numpy()
            m = collect.metrics(out)
            key = {"sid": r.sid, "pollutant": r.pollutant, "family": fam}
            mets.append({**key, "n_folds": r.n_folds, **m})
            d = collect.deweathered(out, m["smear"])
            d = d.assign(**key, valid=out.y.notna(), y=out.y, cv_pred=out.cv_pred, cv_fold=out.cv_fold)
            days.append(d)
            times.append({**key, "n_fit": r.n_fit, "n_target": r.n_target, "n_folds": r.n_folds,
                          "draws": js["draws"], "n_schemes": len(js["schemes"]),
                          **{k: js[k] for k in ("secs_cv", "secs_fit", "secs_normalise", "secs_total")}})  # fmt: skip
    return pd.DataFrame(mets), pd.concat(days, ignore_index=True), pd.DataFrame(times)


def fold_r2(days: pd.DataFrame) -> pd.DataFrame:
    t = days[days.valid & (days.cv_fold > 0)]
    r = t.groupby(["family", "pollutant", "sid", "cv_fold"]).apply(
        lambda g: collect.r2(g.y.to_numpy(), g.cv_pred.to_numpy()), include_groups=False
    )
    return r.rename("r2").reset_index()


def convention_table(days: pd.DataFrame, run: str = "pilot") -> pd.DataFrame:
    """Median out-of-sample R² per family and pollutant under both test-year trend conventions."""
    from src.normalise.run import CONVENTIONS

    obs = days[days.valid][["family", "pollutant", "sid", "date", "y"]]
    rows = []
    for (fam, pol, sid), g in obs.groupby(["family", "pollutant", "sid"]):
        target = pd.read_parquet(series_dir(run, pol, sid) / "target.parquet", columns=["date"])
        for c in CONVENTIONS:
            cv = pd.read_parquet(cvcheck_path(run, fam, c, pol, sid)).assign(date=target.date.to_numpy())
            j = g.merge(cv[cv.cv_fold > 0], on="date")
            rows.append({"family": fam, "pollutant": pol, "sid": sid, "convention": c,
                         "r2_oos": collect.r2(j.y.to_numpy(), j.cv_pred.to_numpy())})  # fmt: skip
    t = pd.DataFrame(rows)
    s = t.groupby(["convention", "family", "pollutant"]).r2_oos.median().unstack(["family", "pollutant"])
    s.columns = [f"{FAM[f]} {POL[p]}" for f, p in s.columns]
    s["all series, LightGBM"] = t[t.family == "lgbm"].groupby("convention").r2_oos.median()
    s["all series, GAM"] = t[t.family == "gam"].groupby("convention").r2_oos.median()
    return s.reset_index()


def worst_series(days: pd.DataFrame, mets: pd.DataFrame) -> pd.DataFrame:
    """Series with negative out-of-sample R²: how variable the test days are, and how far off the
    predicted level is (a level error in a whole test year, or a nearly constant series)."""
    t = days[days.valid & (days.cv_fold > 0)]
    g = t.groupby(["family", "pollutant", "sid"])
    d = pd.DataFrame({"sd_log_test": g.y.std(), "mean_bias_log": g.apply(
        lambda x: (x.cv_pred - x.y).mean(), include_groups=False)}).reset_index()  # fmt: skip
    w = mets[mets.r2_oos < 0][["family", "pollutant", "sid", "r2_oos"]].merge(d, on=["family", "pollutant", "sid"])
    return w.sort_values("r2_oos")


def station_months(days: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    """Means over valid days of station-months with >= 75% valid days (the completeness rule)."""
    d = days[days.valid].assign(month=days.date.dt.to_period("M"))
    g = d.groupby(["family", "pollutant", "sid", "month"])
    m = g[cols].mean().assign(n=g.size())
    share = params()["completeness"]["min_day_share_per_year"]
    dim = m.index.get_level_values("month").days_in_month
    return m[m.n >= share * dim].reset_index()


def convergence(days: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    c = cfg()
    grid, nmax = c["convergence_grid"], c["resamples_max"]
    rows = []
    for scheme in ("seasonal", "annual"):
        cols = [f"dw_{scheme}_n{n}" for n in grid]
        sm = station_months(days, cols)
        for (fam, pol), g in sm.groupby(["family", "pollutant"]):
            ref = g[f"dw_{scheme}_n{nmax}"]
            for n in grid:
                dev = (g[f"dw_{scheme}_n{n}"] / ref - 1).abs()
                rows.append({"scheme": scheme, "family": fam, "pollutant": pol, "N": n,
                             "station_months": len(g), "share_within_tol": (dev < c["convergence_tol"]).mean(),
                             "p95_dev_pct": 100 * dev.quantile(0.95)})  # fmt: skip
    conv = pd.DataFrame(rows)
    s = conv[conv.scheme == c["resample_scheme"]]
    ok = s.groupby("N").share_within_tol.min() >= c["convergence_share"]
    return conv, int(ok[ok].index.min())


def station_years(days: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    """Annual means over valid days, for station-years valid under the primary rule (q1_t75)."""
    q = pd.read_parquet(PROCESSED / "station_year_quality.parquet", columns=["sid", "year", "pollutant", "valid_q1_t75"])
    d = days[days.valid].assign(year=days.date.dt.year)
    y = d.groupby(["family", "pollutant", "sid", "year"])[cols].mean().reset_index()
    y = y.merge(q, on=["sid", "year", "pollutant"], how="left")
    return y[y.valid_q1_t75.fillna(False).astype(bool)]


def yoy(y: pd.DataFrame, col: str) -> pd.Series:
    """Change in log annual mean between consecutive valid years of a series (NaN across a gap)."""
    y = y.sort_values(["family", "pollutant", "sid", "year"])
    g = y.groupby(["family", "pollutant", "sid"])
    d = np.log(y[col]).groupby([y.family, y.pollutant, y.sid]).diff()
    return d.where(g.year.diff() == 1)


def scheme_and_weather(days: pd.DataFrame, nmax: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    cols = ["obs", f"dw_seasonal_n{nmax}", f"dw_annual_n{nmax}"]
    y = station_years(days, cols)
    y = y.assign(**{f"d_{c}": yoy(y, c) for c in cols})
    s, a = f"d_dw_seasonal_n{nmax}", f"d_dw_annual_n{nmax}"
    rows_s, rows_w = [], []
    for (fam, pol), g in y.groupby(["family", "pollutant"]):
        p = g.dropna(subset=[s, a, "d_obs"])
        lvl = np.log(g[f"dw_seasonal_n{nmax}"] / g[f"dw_annual_n{nmax}"])
        rows_s.append({"family": fam, "pollutant": pol, "station_years": len(g), "year_pairs": len(p),
                       "median_abs_level_diff_pct": 100 * lvl.abs().median(),
                       "corr_yoy_change": np.corrcoef(p[s], p[a])[0, 1],
                       "median_abs_yoy_diff_pct": 100 * (p[s] - p[a]).abs().median()})  # fmt: skip
        w = p.d_obs - p[s]  # the weather part of the year-on-year change
        rows_w.append({"family": fam, "pollutant": pol, "year_pairs": len(p),
                       "sd_raw_change_pct": 100 * p.d_obs.std(), "sd_dw_change_pct": 100 * p[s].std(),
                       "median_abs_weather_pct": 100 * w.abs().median(),
                       "p90_abs_weather_pct": 100 * w.abs().quantile(0.9),
                       "share_weather_over_5pct": (w.abs() > 0.05).mean()})  # fmt: skip
    return pd.DataFrame(rows_s), pd.DataFrame(rows_w)


def scheme_by_completeness(days: pd.DataFrame, nmax: int) -> pd.DataFrame:
    """Median |seasonal - annual| year-on-year change, split by whether both years of the pair have
    >= 90% valid days: a test of whether the schemes differ because of which days were observed."""
    cols = ["obs", f"dw_seasonal_n{nmax}", f"dw_annual_n{nmax}"]
    y = station_years(days, cols)
    nd = days[days.valid].assign(year=days.date.dt.year).groupby(["family", "pollutant", "sid", "year"]).size()
    y = y.merge(nd.rename("ndays").reset_index(), on=["family", "pollutant", "sid", "year"])
    y = y.assign(**{f"d_{c}": yoy(y, c) for c in cols})
    y["prev"] = y.groupby(["family", "pollutant", "sid"]).ndays.shift()
    p = y.dropna(subset=[f"d_{c}" for c in cols])
    full = (p.ndays >= 0.9 * 365) & (p.prev >= 0.9 * 365)
    rows = []
    for lab, q in (("both years >= 90% valid days", p[full]), ("other year pairs", p[~full])):
        s, a = q[f"d_dw_seasonal_n{nmax}"], q[f"d_dw_annual_n{nmax}"]
        rows.append({"year pairs": lab, "n": len(q), "median_abs_scheme_diff_pct": 100 * (s - a).abs().median(),
                     "weather_part_seasonal_pct": 100 * (q.d_obs - s).abs().median(),
                     "weather_part_annual_pct": 100 * (q.d_obs - a).abs().median()})  # fmt: skip
    return pd.DataFrame(rows)


def divergence(days: pd.DataFrame, col: str) -> pd.DataFrame:
    """Per station-pollutant: D = max over valid years of the gap between the two families'
    deweathered annual series, each expressed relative to its own mean (log scale); and the
    correlation of their year-on-year changes."""
    y = station_years(days, [col])
    y["dev"] = np.log(y[col]) - np.log(y[col]).groupby([y.family, y.pollutant, y.sid]).transform("mean")
    y["d"] = yoy(y, col)
    w = y.pivot_table(index=["pollutant", "sid", "year"], columns="family", values=["dev", "d"])
    rows = []
    for (pol, sid), g in w.groupby(level=["pollutant", "sid"]):
        gap = (g[("dev", "lgbm")] - g[("dev", "gam")]).abs()
        dd = g["d"].dropna()
        rows.append({"pollutant": pol, "sid": sid, "valid_years": len(g), "D_pct": 100 * gap.max(),
                     "corr_yoy": dd.lgbm.corr(dd.gam) if len(dd) >= 3 else np.nan})  # fmt: skip
    return pd.DataFrame(rows)


def all_series_sizes() -> pd.DataFrame:
    """n_fit, n_target and CV folds of every station-pollutant the full run would fit."""
    c = cfg()
    cells = station_cells(pd.read_csv(PROCESSED / "stations.csv"))
    day = load_station_day()
    day = day[(day.date <= pd.Timestamp(c["fit_end"])) & day.sid.isin(cells.index)]
    rows = []
    for p in POLLUTANTS:
        d = day[(day[f"{p}_h1"] > 0) & (day[p] > 0)]
        fit = d[d[f"{p}_h1"] >= valid_day_hours()]
        nt = d.groupby("sid").size()
        for sid, g in fit.groupby("sid"):
            if len(g) < c["min_fit_days"]:
                continue
            folds = forward_folds(g.date.dt.year, c["cv_min_train_days"], c["cv_min_test_days"])
            rows.append({"sid": sid, "pollutant": p, "n_fit": len(g), "n_target": nt[sid], "n_folds": len(folds)})
    return pd.DataFrame(rows)


def runtime(times: pd.DataFrame, sizes: pd.DataFrame, n_main: int) -> pd.DataFrame:
    """Extrapolate pilot task times (measured with the full run's worker count) to the full run:
    model time proportional to training rows x (folds + 1); resampling time proportional to
    target days x draws x schemes."""
    workers = cfg()["workers"]
    rows = []
    for fam, t in times.groupby("family"):
        a = (t.secs_cv + t.secs_fit).sum() / (t.n_fit * (t.n_folds + 1)).sum()
        b = t.secs_normalise.sum() / (t.n_target * t.draws * t.n_schemes).sum()
        per = a * sizes.n_fit * (sizes.n_folds + 1) + b * sizes.n_target * n_main
        rows.append({"family": fam, "pilot_tasks": len(t), "pilot_task_median_s": t.secs_total.median(),
                     "model_s_per_1000_rows": 1000 * a, "resample_us_per_row": 1e6 * b,
                     "full_tasks": len(sizes), "full_cpu_h": per.sum() / 3600,
                     "full_wall_h": per.sum() / 3600 / workers})  # fmt: skip
    return pd.DataFrame(rows)


def md_table(df: pd.DataFrame, fmt: dict | None = None) -> str:
    fmt = fmt or {}
    cols = list(df.columns)
    lines = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    for r in df.itertuples(index=False):
        cells = []
        for c, v in zip(cols, r):
            f = fmt.get(c)
            cells.append(f.format(v) if f and pd.notna(v) else ("" if pd.isna(v) else str(v)))
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def report() -> None:
    c = cfg()
    nmax = c["resamples_max"]
    PILOT.mkdir(parents=True, exist_ok=True)
    stations = pd.read_csv(STATIONS_CSV)
    mets, days, times = load_all("pilot")
    mets.to_csv(PILOT / "metrics.csv", index=False)
    times.to_csv(PILOT / "timings.csv", index=False)

    lab = lambda d: d.assign(family=d.family.map(FAM), pollutant=d.pollutant.map(POL))  # noqa: E731
    r2 = mets.groupby(["family", "pollutant"]).agg(
        series=("r2_oos", "size"), median_r2_oos=("r2_oos", "median"),
        q25=("r2_oos", lambda s: s.quantile(0.25)), q75=("r2_oos", lambda s: s.quantile(0.75)),
        min_r2_oos=("r2_oos", "min"), median_r2_in=("r2_in", "median"), median_rmse_oos=("rmse_oos", "median"),
    ).reset_index()  # fmt: skip
    overall = mets.groupby("family").r2_oos.median()
    w = mets.pivot_table(index=["pollutant", "sid"], columns="family", values="r2_oos")
    gam_better = (w.gam > w.lgbm).mean()
    fr = fold_r2(days)
    by_year = fr.groupby(["family", "pollutant", "cv_fold"]).r2.agg(["size", "median"]).reset_index()
    by_year = by_year.pivot_table(index="cv_fold", columns=["family", "pollutant"], values="median")
    by_year.columns = [f"{FAM[f]} {POL[p]}" for f, p in by_year.columns]
    by_year = by_year.reset_index().rename(columns={"cv_fold": "test year"})
    convs = convention_table(days)
    convs.to_csv(PILOT / "cv_conventions.csv", index=False)
    worst = worst_series(days, mets)
    acf = mets.groupby(["family", "pollutant"])[
        [f"acf_oos_{k}" for k in collect.LAGS] + [f"acf_in_{k}" for k in (1, 7)]
    ].median().reset_index()
    conv, n_chosen = convergence(days)
    conv.to_csv(PILOT / "convergence.csv", index=False)
    mcse = days[days.valid].assign(
        rel=lambda d: d[f"sd_{c['resample_scheme']}"] / np.sqrt(n_chosen) / d[f"dw_{c['resample_scheme']}_n{nmax}"]
    ).groupby(["family", "pollutant"]).rel.median().mul(100).rename("median_daily_mc_se_pct").reset_index()
    scheme, weather = scheme_and_weather(days, nmax)
    scheme_c = scheme_by_completeness(days, nmax)
    cs = conv[(conv.scheme == c["resample_scheme"]) & (conv.N == n_chosen)].sort_values("share_within_tol").iloc[0]
    cv_lower = (convs.set_index("convention")[["all series, LightGBM", "all series, GAM"]].diff().iloc[-1] < 0).all()
    same_rank = (convs["all series, GAM"] > convs["all series, LightGBM"]).nunique() == 1
    div = divergence(days, f"dw_{c['resample_scheme']}_n{nmax}")
    div.to_csv(PILOT / "divergence.csv", index=False)
    sizes = all_series_sizes()
    rt = runtime(times, sizes, n_chosen)
    primary_hint = overall.idxmax()

    st = stations.assign(years=lambda s: s.sid.map(
        pd.read_csv(INPUTS / "pilot" / "series.csv").query("pollutant == 'pm25'").set_index("sid")
        .apply(lambda r: f"{r.first_year}-{r.last_year}", axis=1)))  # fmt: skip
    st = st[["sid", "sname", "region", "valid_days_pm25", "valid_days_pm10", "years"]]
    conv_s = conv[conv.scheme == c["resample_scheme"]].pivot_table(
        index="N", columns=["family", "pollutant"], values="share_within_tol")
    conv_s.columns = [f"{FAM[f]} {POL[p]}" for f, p in conv_s.columns]
    conv_s = conv_s.reset_index()
    conv_a = conv[conv.scheme == "annual"].groupby("N").share_within_tol.min().reset_index(name="annual scheme, worst cell")
    conv_s = conv_s.merge(conv_a, on="N")
    div_s = div.groupby("pollutant").agg(series=("D_pct", "size"), median_D_pct=("D_pct", "median"),
                                         p90_D_pct=("D_pct", lambda s: s.quantile(0.9)), max_D_pct=("D_pct", "max"),
                                         over_5pct=("D_pct", lambda s: int((s > 5).sum())),
                                         median_corr_yoy=("corr_yoy", "median")).reset_index()  # fmt: skip
    pct = "{:.1f}"
    f3 = "{:.3f}"
    f2 = "{:.2f}"
    text = f"""# Deweathering pilot

*Generated by `python -m src.normalise.pilot report` from the pilot run (`data/interim/normalise/fits/pilot/`). Do not edit by hand. Rules: DEC-100 to DEC-104. The full run waits for Reenu's go-ahead.*

**What the pilot is.** Both model families (LightGBM, mgcv GAM) fitted on {len(stations)} stations × 2 pollutants = {mets.groupby(['sid', 'pollutant']).ngroups} series, with blocked forward-chaining CV by year, then deweathered with {nmax:,} weather draws under two resampling schemes (seasonal window, proposed primary; Grange & Carslaw's annual default, for comparison), on {c['workers']} workers as in the full run. R² and residual autocorrelation are on the log scale the models are fitted on. No NCAP information is used anywhere.

## 1. Pilot stations

{md_table(st)}

## 2. Out-of-sample R² (registered selection metric: median over series, DEC-088)

{md_table(lab(r2), {"median_r2_oos": f3, "q25": f3, "q75": f3, "min_r2_oos": f3, "median_r2_in": f3, "median_rmse_oos": f3})}

- **Median over all {len(w)} pilot series:** LightGBM {overall['lgbm']:.3f}, GAM {overall['gam']:.3f}. The GAM has the higher out-of-sample R² in {100 * gam_better:.0f}% of series. **In the pilot, {FAM[primary_hint]} would be primary**; the registered choice is made on the full run.
- In-sample R² is much higher than out-of-sample for both families: the forward-chaining test years are genuinely unseen, including their level.
- CV uses the `{c['cv_trend']}` test-year trend convention (DEC-107): a test day gets the trend of the same calendar day one year earlier.

**Test-year trend convention** (median out-of-sample R²). The rule fixed before the pilot (DEC-103) clamped the trend at the last training day. The pilot showed that this carries the last training day's season into the whole test year, because with few training years the trend smooth absorbs part of the seasonal cycle (a GAM fitted on 2019–20 for Palwal predicted 2021 about 9 times too high, from the trend term alone). Both conventions, both families:

{md_table(convs, {k: f3 for k in convs.columns if k != "convention"})}

{"The `last_year` convention gives a **lower** median R² than the clamp for both families (the level it assumes is a year older than the last training day's)." if cv_lower else "The two conventions change the medians in different directions for the two families."} {"The ranking of the families is the same under both conventions." if same_rank else "**The ranking of the families differs between the conventions.**"} The convention is chosen on principle (no extrapolation of the trend, no confusion of season with level), not on which gives the higher R².

**Series with negative out-of-sample R²** (`{c['cv_trend']}` convention): the SD of log PM over the test days, and the mean error of the predicted log level. A large mean error means a level the model could not foresee from earlier years (a level shift, a new instrument, a changed surrounding); a very small SD means a nearly constant series, where even small errors give a large negative R².

{md_table(lab(worst), {"r2_oos": f2, "sd_log_test": f2, "mean_bias_log": f2})}

**Median out-of-sample R² by test year** (each series' fold R², median over series):

{md_table(by_year, {k: f3 for k in by_year.columns if k != "test year"})}

## 3. Residual autocorrelation (median over series)

Lag-k correlation of out-of-sample residuals (days exactly k apart, same test year); last two columns: in-sample residuals at lags 1 and 7.

{md_table(lab(acf), {k: f2 for k in acf.columns if k.startswith("acf")})}

Residuals are strongly autocorrelated at short lags: pollution episodes last several days and the weather inputs do not explain all of that persistence. This is why the CV must be blocked (a random split would put the neighbour of every test day in training), and why daily residuals cannot be treated as independent in any later uncertainty calculation.

## 4. How many weather draws? (convergence rule, DEC-103)

Share of pilot station-months (≥ 75% valid days) whose deweathered mean after N draws is within {100 * c['convergence_tol']:.1f}% of its {nmax:,}-draw value; the rule needs ≥ {100 * c['convergence_share']:.0f}% in every family × pollutant for the `{c['resample_scheme']}` scheme.

{md_table(conv_s, {k: "{:.3f}" for k in conv_s.columns if k != "N"})}

**Result: N = {n_chosen}.** The binding cell is {FAM[cs.family]} {POL[cs.pollutant]}: {cs.share_within_tol:.4f} of station-months within {100 * c['convergence_tol']:.1f}% at N = {n_chosen} (95th-percentile deviation {cs.p95_dev_pct:.2f}%), so the rule is met {"only narrowly" if cs.share_within_tol < c['convergence_share'] + 0.01 else "with margin"}. The proposal says 500–1,000 draws; PLAN.md's default is 300. {"N is below the proposal's range: the rule shows fewer draws already reach the stated precision at the station-month level." if n_chosen < 500 else "N is within the proposal's range."} Median Monte-Carlo standard error of a single *daily* deweathered value at N = {n_chosen}:

{md_table(lab(mcse), {"median_daily_mc_se_pct": "{:.2f}%"})}

Daily values are noisier than monthly ones by about √30; nothing downstream uses a single day.

## 5. Resampling scheme: seasonal window vs Grange & Carslaw's annual default (DEC-102)

Station-years valid under the primary rule; both schemes at {nmax:,} draws.

{md_table(lab(scheme), {"median_abs_level_diff_pct": pct, "corr_yoy_change": f3, "median_abs_yoy_diff_pct": pct})}

- *Level difference:* the two schemes give different annual levels (the annual scheme mixes all seasons' weather into every day, the seasonal one keeps each day's own season).
- *Year-on-year changes*, which are what RQ2, H4 and Layer B use, are what matters; the correlation and median absolute difference show how far the schemes agree on them.
- The schemes' year-on-year changes differ by about as much as the weather part itself (§6), so the choice of scheme matters. Part of the difference comes from which days were observed: under the seasonal scheme an annual mean over valid days depends on the seasons covered (as the raw mean does, so it cancels in raw minus deweathered), while the annual scheme gives every day the same mix of seasons. Split by completeness:

{md_table(scheme_c, {"median_abs_scheme_diff_pct": pct, "weather_part_seasonal_pct": pct, "weather_part_annual_pct": pct})}

  The difference is smaller when both years are nearly complete, but it does not vanish: completeness explains part of it, not all.

## 6. How much does weather move annual numbers? (a first look at RQ2)

For consecutive valid station-years: the weather part of the year-on-year change = raw change − deweathered change (log scale, shown as %), `{c['resample_scheme']}` scheme.

{md_table(lab(weather), {"sd_raw_change_pct": pct, "sd_dw_change_pct": pct, "median_abs_weather_pct": pct, "p90_abs_weather_pct": pct, "share_weather_over_5pct": "{:.2f}"})}

## 7. Where the two families diverge

Per series, D = the largest gap, over valid years, between the two families' deweathered annual series (each relative to its own mean, log scale, as %); and the correlation of their year-on-year changes.

{md_table(div_s.assign(pollutant=div_s.pollutant.map(POL)), {"median_D_pct": pct, "p90_D_pct": pct, "max_D_pct": pct, "median_corr_yoy": f3})}

Proposed flag for the full run: a series **diverges** if D > 5%. Flagged series are listed in the Phase 5 report and carried into the Phase 7 "other family" sensitivity check.

## 8. Run time on this laptop

Measured in the pilot with {c['workers']} parallel workers (so contention is included), extrapolated to all {len(sizes)} series with ≥ {c['min_fit_days']} valid days ({(sizes.pollutant == 'pm25').sum()} PM2.5, {(sizes.pollutant == 'pm10').sum()} PM10) at N = {n_chosen}, one scheme:

{md_table(rt.assign(family=rt.family.map(FAM)), {"pilot_task_median_s": "{:.0f}", "model_s_per_1000_rows": "{:.3f}", "resample_us_per_row": "{:.1f}", "full_cpu_h": "{:.1f}", "full_wall_h": "{:.1f}"})}

**Estimated full run: about {rt.full_wall_h.sum():.1f} h of wall-clock time for both families** (run one after the other on {c['workers']} workers). LightGBM's cost is almost all prediction during resampling (500 trees for every draw of every day). The run is resumable per series (`python -m src.normalise.run fit --run main`), so it can be split across sessions.
"""
    (DOCS / "deweathering_pilot.md").write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    {"select": select, "report": report}[sys.argv[1]]()

"""Why do the GAM and LightGBM disagree about some cities' 2018-2025 change? (Phase 6, DEC-130)

Cities: Kolkata, and every city whose GAM and LightGBM deweathered balanced-panel changes (baseline
-> 2025; strict panel, primary rule, q1_t75) differ by more than composition.family_flag_pp under
either resampling scheme. Every city with a panel is eligible (no NCAP comparison).

1. Which weather variables drive each family's weather effect. Each model's log prediction is a
   sum of parts: the GAM's terms (predict type = "terms", src/normalise/family_terms.R) and
   LightGBM's TreeSHAP contributions (pred_contrib). Parts are grouped (GROUPS). For a station-year,
   the weather effect of group g = mean over the station's fit days in that year of
   [part_g under the actual weather - mean part_g over the day's first `diag_draws` shared weather
   draws]; its change from the baseline to 2025 is g's contribution to the change in the weather
   effect, in log units x 100 (about %). For the GAM the trend part is identical in both terms (the
   trend is never resampled), so it contributes 0; for LightGBM, TreeSHAP can assign part of a
   weather-driven change to the trend or calendar features through interactions. The sum over
   groups is checked against each family's implied weather change, 100 x change in
   log(raw / deweathered) (station_year.parquet); the gap is Jensen's inequality (the deweathered
   value is a mean of exponentials) and Monte-Carlo error from using 100 of the 500 draws.
   `fitted` = the change in the part's mean under the actual weather alone: how each model splits the
   station's measured change between trend (kept as "emissions") and weather.
2. Is the actual ERA5 weather consistent with it. At the station's cell (the weather pool: all
   complete ERA5 days 2015-2025): annual and cold-month means per variable, 2025 minus the baseline
   in units and in SDs of the 2015-2025 annual means, the OLS trend per decade (95% CI) and the
   correlation of the annual mean with the year. For the variables with an unambiguous physical sign
   (a higher boundary layer, faster wind, more rain -> lower PM) the sign a family's contribution
   should have, given the actual change, is stated beside it.
3. (DEC-133, added after step 1 failed its own check.) Step 1 works on the log scale, but H4 and
   the deweathered change are changes in ARITHMETIC annual means, where weather acting on the
   high-pollution days counts for more; for Kolkata's GAM the log-scale parts summed to -3.5
   against an implied -18.4. `attribution` therefore splits the implied weather change on the
   annual-mean scale: one group at a time switched to the actual weather (others at typical), the
   groups' joint part, and the model's misfit (the change it reproduces neither by trend nor by
   weather; deweathering drops it, so raw - deweathered counts it as weather). These add up to the
   implied change exactly, up to Monte-Carlo error. `misfit_h4` gives the misfit for every H4 panel.
   Step 1's log-scale table is kept for the record (family_diag_contrib.csv).
A finding only: it never chooses the family (the registered rule did, DEC-118).

    python -m src.normalise.family_diag   -> data/processed/composition/family_diag_*.csv
"""

import re
import subprocess

import lightgbm as lgb
import numpy as np
import pandas as pd
from scipy import stats

from src.common.paths import INTERIM
from src.normalise import collect
from src.normalise import composition as C
from src.normalise.aggregate import OUT as DW_OUT
from src.normalise.features import series_dir
from src.normalise.resample import MODEL_COLUMNS, design
from src.normalise.store import model_path

WORK = INTERIM / "composition" / "family_diag"
GROUPS = {"temp": "temperature", "rh": "humidity", "ws": "wind", "wd": "wind", "blh_mean": "boundary layer",
          "blh_pm": "boundary layer", "precip": "precipitation", "precip_l": "precipitation", "ssrd": "radiation",
          "doy": "calendar", "weekday": "calendar", "trend": "trend"}  # fmt: skip
WEATHER = ["temp", "rh", "ws", "blh_mean", "blh_pm", "precip", "ssrd"]
# a higher value of these lowers PM (dispersion, mixing, wet removal); others have no single sign
LOWERS_PM = {"blh_mean": "boundary layer", "blh_pm": "boundary layer", "ws": "wind", "precip": "precipitation"}
SCHEMES = ("seasonal", "annual")


def group_of(term: str) -> str | None:
    """Model part -> group. GAM names look like 's(blh_mean)', 'ti(ws,wd)', 'weekday', 'trend'."""
    if term in ("intercept", "bias"):
        return None
    inner = re.sub(r"^(s|ti|te)\((.*)\)$", r"\2", term).split(",")[0].strip()
    return GROUPS[inner]


def grouped(parts: pd.DataFrame) -> pd.DataFrame:
    cols = [c for c in parts.columns if group_of(c)]
    return parts[cols].T.groupby([group_of(c) for c in cols]).sum().T


def flagged_cities() -> pd.DataFrame:
    """Cities where |GAM - LightGBM| on the change in the deweathered panel mean exceeds the flag,
    under either scheme (primary rule, strict panel, q1_t75), plus Kolkata by name."""
    ch = pd.read_parquet(C.OUT / "city_changes.parquet")
    k = ["unit_id", "pollutant"]
    rows = {}
    for sch in SCHEMES:
        g = ch[ch.spec == C.Spec("gam", sch).label].set_index(k)
        lg = ch[ch.spec == C.Spec("lgbm", sch).label].set_index(k)
        rows[f"chg_dw_gam_{sch}"] = g.chg_dw_panel
        rows[f"chg_dw_lgbm_{sch}"] = lg.chg_dw_panel
        rows[f"diff_pp_{sch}"] = g.chg_dw_panel - lg.chg_dw_panel
        rows["chg_raw_panel"] = g.chg_raw_panel
        rows["n_panel"] = g.n_panel
    t = pd.DataFrame(rows).reset_index()
    from src.viz.fig3_deweathered import names

    t["city"] = t.unit_id.map(names())
    flag = C.ccfg()["family_flag_pp"]
    t["reason"] = ""
    for sch in SCHEMES:
        t.loc[t[f"diff_pp_{sch}"].abs() > flag, "reason"] += f"|diff| > {flag:g} pp ({C.SCHEME_NAME[sch]}); "
    t.loc[t.city == "Kolkata", "reason"] += "named (Kolkata)"
    return t[t.reason != ""].reset_index(drop=True)


def panel_series(cities: pd.DataFrame) -> pd.DataFrame:
    sy = pd.read_parquet(DW_OUT / "station_year.parquet")
    v = C.mark_panel(C.select(sy, C.PRIMARY), C.PRIMARY)
    p = v[v.in_panel][["unit_id", "pollutant", "sid"]].drop_duplicates()
    return p.merge(cities[["unit_id", "pollutant", "city"]], on=["unit_id", "pollutant"])


def gam_terms(series: pd.DataFrame) -> None:
    WORK.mkdir(parents=True, exist_ok=True)
    tasks = WORK / "tasks.csv"
    series[["pollutant", "sid"]].to_csv(tasks, index=False)
    subprocess.run(["Rscript", "src/normalise/family_terms.R", str(tasks), str(WORK / "terms")], check=True)


def contributions(pol: str, sid: str, years: tuple[int, int], k: int) -> pd.DataFrame:
    """Per family, scheme, year and group: mean actual part and mean (actual - typical) part."""
    d = series_dir("main", pol, sid)
    fit = pd.read_parquet(d / "fit.parquet")
    target = pd.read_parquet(d / "target.parquet")
    pool = pd.read_parquet(d / "pool.parquet")
    tgt = target.assign(trend=target.trend.clip(fit.trend.min(), fit.trend.max()))  # as in deweathering
    sel = fit.year.isin(years).to_numpy()
    f = fit[sel].reset_index(drop=True)
    t_rows = f.t_row.to_numpy()
    booster = lgb.Booster(model_file=str(model_path("lgbm", pol, sid, "txt")))
    gt_fit = grouped(pd.read_parquet(WORK / "terms" / f"{pol}_{sid}_fit.parquet")[sel].reset_index(drop=True))
    gt_pool = grouped(pd.read_parquet(WORK / "terms" / f"{pol}_{sid}_pool.parquet"))
    lg_act = grouped(pd.DataFrame(booster.predict(f[MODEL_COLUMNS], pred_contrib=True), columns=[*MODEL_COLUMNS, "bias"]))
    out = []
    for sch in SCHEMES:
        idx = pd.read_parquet(d / f"idx_{sch}.parquet").idx.to_numpy().reshape(len(target), -1)[t_rows, :k]
        # GAM: additive, so a draw's weather (and, under Grange & Carslaw, calendar) parts are the pool
        # day's; the trend, and under the seasonal scheme the calendar, are the day's own
        g_typ = pd.DataFrame({c: gt_pool[c].to_numpy()[idx].mean(axis=1) for c in gt_pool.columns})
        for c in ("trend",) + (("calendar",) if sch == "seasonal" else ()):
            if c in gt_fit:
                g_typ[c] = gt_fit[c].to_numpy()
        # LightGBM: SHAP on the actual resampled rows (same construction as src.normalise.resample)
        x = design(tgt.iloc[t_rows].reset_index(drop=True), pool, idx, sch)
        sh = booster.predict(x, pred_contrib=True).reshape(len(f), k, -1).mean(axis=1)
        l_typ = grouped(pd.DataFrame(sh, columns=[*MODEL_COLUMNS, "bias"]))
        for fam, act, typ in (("gam", gt_fit, g_typ), ("lgbm", lg_act, l_typ)):
            for y in years:
                m = (f.year == y).to_numpy()
                for grp in act.columns:
                    out.append({"pollutant": pol, "sid": sid, "scheme": sch, "family": fam, "year": y, "group": grp,
                                "fitted": act[grp][m].mean(), "effect": (act[grp][m] - typ[grp][m]).mean(),
                                "days": int(m.sum())})  # fmt: skip
    return pd.DataFrame(out)


def attribution(pol: str, sid: str, years: tuple[int, int], k: int) -> pd.DataFrame:
    """Weather effect by variable group ON THE SCALE OF THE ANNUAL MEAN (DEC-133), per family, scheme
    and year. With pred_draw = the model's log prediction for a day under draw j (the deweathering
    row) and pred_g = the same with group g's inputs set to the day's actual values:
        W_g   = log mean_{days, draws} exp(pred_g) - log mean_{days, draws} exp(pred_draw)
        W_all = log mean_days exp(fitted) - log mean_{days, draws} exp(pred_draw)   (every group actual)
        misfit = log mean_days exp(y) - log mean_days exp(fitted)
    so that log(raw / deweathered) = misfit + W_all (+ Monte-Carlo error from k of the 500 draws;
    the smearing constant cancels in any change), and W_all - sum W_g = the groups' joint
    (interaction) part. GAM predictions are sums of its terms (additive on the log scale);
    LightGBM's are recomputed with the mixed rows."""
    d = series_dir("main", pol, sid)
    fit = pd.read_parquet(d / "fit.parquet")
    target = pd.read_parquet(d / "target.parquet")
    pool = pd.read_parquet(d / "pool.parquet")
    tgt = target.assign(trend=target.trend.clip(fit.trend.min(), fit.trend.max()))
    sel = fit.year.isin(years).to_numpy()
    f = fit[sel].reset_index(drop=True)
    t_rows = f.t_row.to_numpy()
    booster = lgb.Booster(model_file=str(model_path("lgbm", pol, sid, "txt")))
    gf = pd.read_parquet(WORK / "terms" / f"{pol}_{sid}_fit.parquet")[sel].reset_index(drop=True)
    gp = pd.read_parquet(WORK / "terms" / f"{pol}_{sid}_pool.parquet")
    parts = [c for c in gf.columns if group_of(c)]
    lg_fitted = booster.predict(f[MODEL_COLUMNS])
    # mgcv's discrete bam gives no constant with type = "terms": recover it from the saved fitted values,
    # which also checks that the terms add up to the model's own prediction
    saved = collect.load("main", "gam", pol, sid)[0].fitted.to_numpy()[t_rows]
    off = saved - gf[parts].sum(axis=1).to_numpy()
    if np.ptp(off) > 1e-6:
        raise ValueError(f"{pol} {sid}: GAM terms do not add up to the fitted values (spread {np.ptp(off):.2e})")
    intercept = float(off.mean())
    if np.abs(lg_fitted - collect.load("main", "lgbm", pol, sid)[0].fitted.to_numpy()[t_rows]).max() > 1e-6:
        raise ValueError(f"{pol} {sid}: the saved LightGBM model does not reproduce its fitted values")
    out = []
    for sch in SCHEMES:
        idx = pd.read_parquet(d / f"idx_{sch}.parquet").idx.to_numpy().reshape(len(target), -1)[t_rows, :k]
        resampled = {"calendar"} if sch == "annual" else set()
        resampled |= {g for g in set(GROUPS.values()) if g not in ("calendar", "trend")}
        groups = sorted(resampled)
        # GAM: log prediction = intercept + own-day parts + drawn-day parts, per (day, draw)
        own = sum(gf[c].to_numpy() for c in parts if group_of(c) not in resampled) + intercept
        drawn = {g: sum(gp[c].to_numpy()[idx] for c in parts if group_of(c) == g) for g in groups}
        actual = {g: sum(gf[c].to_numpy() for c in parts if group_of(c) == g)[:, None] for g in groups}
        g_draw = own[:, None] + sum(drawn.values())
        g_fit = own + sum(a[:, 0] for a in actual.values())
        g_one = {g: g_draw - drawn[g] + actual[g] for g in groups}
        # LightGBM: the deweathering rows, then the same rows with one group's inputs set to actual
        x = design(tgt.iloc[t_rows].reset_index(drop=True), pool, idx, sch)
        l_draw = booster.predict(x).reshape(len(f), k)
        l_one = {}
        for g in groups:
            xg = x.copy()
            for col in (c for c in MODEL_COLUMNS if GROUPS[c] == g):
                xg[col] = np.repeat(f[col].to_numpy(), k)
            l_one[g] = booster.predict(xg).reshape(len(f), k)
        for fam, draw, one, fitted in (("gam", g_draw, g_one, g_fit), ("lgbm", l_draw, l_one, lg_fitted)):
            for y in years:
                m = (f.year == y).to_numpy()
                base = np.log(np.exp(draw[m]).mean())
                row = {"pollutant": pol, "sid": sid, "scheme": sch, "family": fam, "year": y, "days": int(m.sum()),
                       "W_all": np.log(np.exp(fitted[m]).mean()) - base,
                       "misfit": np.log(np.exp(f.y[m]).mean()) - np.log(np.exp(fitted[m]).mean())}  # fmt: skip
                row.update({f"W_{g}": np.log(np.exp(one[g][m]).mean()) - base for g in groups})
                out.append(row)
    return pd.DataFrame(out)


def attribution_table(a: pd.DataFrame, years: tuple[int, int]) -> pd.DataFrame:
    """Changes from the baseline to the end year (x 100 ~ %): one row per station x family x scheme."""
    cols = [c for c in a.columns if c.startswith("W_") or c == "misfit"]
    k = ["pollutant", "sid", "scheme", "family"]
    b, e = (a[a.year == y].set_index(k)[cols] for y in years)
    d = 100 * (e - b)
    groups = [c for c in cols if c not in ("W_all", "misfit")]
    d["joint"] = d.W_all - d[groups].fillna(0).sum(axis=1)
    d["model_weather"] = d.W_all
    d["total"] = d.W_all + d.misfit
    return d.drop(columns="W_all").rename(columns={c: c[2:] for c in groups}).reset_index()


def misfit_h4(years: tuple[int, int]) -> pd.DataFrame:
    """For every panel station of the NCAP cities in H4 (primary settings), each family's misfit
    change: 100 x change in [log mean exp(y) - log mean exp(fitted)] over the fit days of the
    baseline and end years. It is the part of the measured change the model reproduces neither with
    its trend nor with its weather terms; deweathering drops it, so raw - deweathered counts it as
    'weather' (DEC-133). Averaged per city, then over cities."""
    ch = pd.read_parquet(C.OUT / "city_changes.parquet")
    h4c = ch[(ch.spec == C.PRIMARY.label) & ch.ncap][["unit_id", "pollutant"]]
    sy = pd.read_parquet(DW_OUT / "station_year.parquet")
    v = C.mark_panel(C.select(sy, C.PRIMARY), C.PRIMARY)
    st = v[v.in_panel][["unit_id", "pollutant", "sid"]].drop_duplicates().merge(h4c)
    rows = []
    for r in st.itertuples():
        for fam in ("gam", "lgbm"):
            out = collect.load("main", fam, r.pollutant, r.sid)[0]
            f = out[out.y.notna()]
            yr = pd.to_datetime(f.date).dt.year
            m = {y: np.log(np.exp(f.y[yr == y]).mean()) - np.log(np.exp(f.fitted[yr == y]).mean()) for y in years}
            rows.append({"unit_id": r.unit_id, "pollutant": r.pollutant, "sid": r.sid, "family": fam,
                         "misfit_change": 100 * (m[years[1]] - m[years[0]])})  # fmt: skip
    return pd.DataFrame(rows)


def implied(series: pd.DataFrame, years: tuple[int, int]) -> pd.DataFrame:
    """Each family's implied weather change, 100 x change in log(raw / deweathered), per station."""
    sy = pd.read_parquet(DW_OUT / "station_year.parquet")
    y = sy[(sy.rule == "primary") & (sy.variant == "q1_t75") & sy.year.isin(years)].merge(series[["pollutant", "sid"]])
    rows = []
    for (pol, sid), g in y.groupby(["pollutant", "sid"]):
        g = g.set_index("year")
        for fam in ("gam", "lgbm"):
            for sch in SCHEMES:
                col = f"dw_{fam}" + ("_annual" if sch == "annual" else "")
                w = np.log(g.raw / g[col])
                rows.append({"pollutant": pol, "sid": sid, "family": fam, "scheme": sch,
                             "implied_weather_change": 100 * (w[years[1]] - w[years[0]]),
                             "chg_dw": 100 * (g[col][years[1]] / g[col][years[0]] - 1),
                             "chg_raw": 100 * (g.raw[years[1]] / g.raw[years[0]] - 1)})  # fmt: skip
    return pd.DataFrame(rows)


def era5_facts(series: pd.DataFrame, years: tuple[int, int]) -> pd.DataFrame:
    """ERA5 at each station's cell (its weather pool, all complete days 2015-2025)."""
    cold = C.ccfg()["cold_months"]
    rows = []
    for (pol, sid), _ in series.groupby(["pollutant", "sid"]):
        pool = pd.read_parquet(series_dir("main", pol, sid) / "pool.parquet")
        pool = pool.assign(year=pool.date.dt.year, month=pool.date.dt.month)
        for season, p in (("annual", pool), ("cold months", pool[pool.month.isin(cold)])):
            a = p.groupby("year")[WEATHER].mean()
            for v in WEATHER:
                s = a[v].dropna()
                lr = stats.linregress(s.index, s.to_numpy())
                h = stats.t.ppf(0.975, len(s) - 2) * lr.stderr
                d = s.get(years[1], np.nan) - s.get(years[0], np.nan)
                rows.append({"pollutant": pol, "sid": sid, "season": season, "variable": v,
                             "value_base": s.get(years[0], np.nan), "value_end": s.get(years[1], np.nan), "delta": d,
                             "sd_annual": s.std(ddof=1), "delta_sd": d / s.std(ddof=1),
                             "slope_per_decade": 10 * lr.slope, "slope_lo": 10 * (lr.slope - h),
                             "slope_hi": 10 * (lr.slope + h), "corr_year": lr.rvalue,
                             "expected_sign_of_pm_effect": -np.sign(d) if v in LOWERS_PM else np.nan})  # fmt: skip
    return pd.DataFrame(rows)


def main() -> None:
    c = C.ccfg()
    years = (C.PRIMARY.baseline, c["end_year"])
    C.OUT.mkdir(parents=True, exist_ok=True)
    cities = flagged_cities()
    cities.to_csv(C.OUT / "family_diag_cities.csv", index=False)
    series = panel_series(cities)
    gam_terms(series)
    att = pd.concat([attribution(r.pollutant, r.sid, years, c["diag_draws"]) for r in series.itertuples()])
    at = attribution_table(att, years).merge(implied(series, years), on=["pollutant", "sid", "family", "scheme"])
    at.merge(series, on=["pollutant", "sid"]).to_csv(C.OUT / "family_diag_attribution.csv", index=False)
    print(at.round(1).to_string(index=False))
    mf = misfit_h4(years)
    mf.to_csv(C.OUT / "family_diag_misfit_h4.csv", index=False)
    print(mf.groupby(["pollutant", "unit_id", "family"]).misfit_change.mean().groupby(["pollutant", "family"]).describe().round(1))
    parts = pd.concat([contributions(r.pollutant, r.sid, years, c["diag_draws"]) for r in series.itertuples()])
    w = parts.pivot_table(index=["pollutant", "sid", "scheme", "family", "group"], columns="year",
                          values=["fitted", "effect"]).reset_index()  # fmt: skip
    w.columns = ["_".join(str(x) for x in col if x != "") for col in w.columns]
    w["delta_effect"] = 100 * (w[f"effect_{years[1]}"] - w[f"effect_{years[0]}"])
    w["delta_fitted"] = 100 * (w[f"fitted_{years[1]}"] - w[f"fitted_{years[0]}"])
    w = w.merge(series, on=["pollutant", "sid"])
    w.to_csv(C.OUT / "family_diag_contrib.csv", index=False)
    chk = w.groupby(["pollutant", "sid", "scheme", "family"]).delta_effect.sum().rename("sum_of_parts").reset_index()
    chk = chk.merge(implied(series, years), on=["pollutant", "sid", "family", "scheme"]).merge(series, on=["pollutant", "sid"])
    chk.to_csv(C.OUT / "family_diag_check.csv", index=False)
    era5_facts(series, years).merge(series, on=["pollutant", "sid"]).to_csv(C.OUT / "family_diag_era5.csv", index=False)
    print(cities.round(1).to_string(index=False))
    print(chk.round(1).to_string(index=False))


if __name__ == "__main__":
    main()

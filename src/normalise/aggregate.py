"""Collect the full deweathering run, choose the primary family, aggregate to city-month and
city-year (Phase 5, RQ2; DEC-088, DEC-105, DEC-109 to DEC-113).

    python -m src.normalise.aggregate [--run main|pilot]

Families: lgbm, gam (one-year-knot trend, DEC-116) compete for primary under the registered rule;
gam_k4 (the DEC-101 trend) is carried as the trend-flexibility sensitivity (main run only).
Two resampling schemes (DEC-109): `seasonal` (primary) and `annual` (Grange & Carslaw's default,
sensitivity). Columns dw_<family> (seasonal) and dw_<family>_annual; `dw` and `dw_annual` are the
primary family's. Guard (DEC-117): guard_<column> flags a station-year whose deweathered mean is
outside deweathering.guard_ratio times the raw mean over the same days; nothing is dropped.

Two validity rules (DEC-110), in a `rule` column:
    primary            registered completeness rule AND not near-constant; the series are fitted
                       without their near-constant station-years (run `main`)
    registered_flags   registered completeness rule only; series that have near-constant
                       station-years come from the refit that keeps them (run `registered`)

Outputs (data/processed/deweathered/):
    series_metrics.parquet   station x pollutant x family: out-of-sample R² under the configured
                             test-year trend (`last_year`) and under `clamp` (DEC-107), within-period
                             R² (DEC-112), RMSE, in-sample R², residual ACF 1-7, smearing; D and
                             `diverges` (DEC-111)
    family_choice.json       the primary family by the registered rule (DEC-088), and what the other
                             convention would have chosen
    station_day.parquet      primary rule: raw daily means and deweathered values, both families, both
                             schemes
    station_year.parquet     rule x completeness variant (q1_t75 primary, q1_t60, q1_t90, q3_t75):
                             raw and deweathered means over the SAME valid days, valid flag, unit,
                             region, reliability, reenu_decided, near_constant, covid_2020
    station_month.parquet    rule x month (primary completeness rule): valid = >= 75% valid days
    city_month.parquet, city_year.parquet
                             rule x unit x period: all-station means over valid stations inside the
                             unit polygon (DEC-105); n_stations; covid_2020. Balanced panel: Phase 6.
"""

import argparse
import json

import numpy as np
import pandas as pd

from src.common.paths import INTERIM, PROCESSED, params
from src.normalise import collect
from src.normalise.features import INPUTS, POLLUTANTS, cfg
from src.normalise.store import FITS, cvcheck_path

OUT = PROCESSED / "deweathered"
VARIANTS = {"q1_t75": ("h1", 0.75), "q1_t60": ("h1", 0.60), "q1_t90": ("h1", 0.90), "q3_t75": ("h3", 0.75)}
COMPETING = ("lgbm", "gam")  # the registered choice is between these (DEC-117)
ALL_FAMILIES = ("lgbm", "gam", "gam_k4")
DW = [f"dw_{f}{s}" for f in ALL_FAMILIES for s in ("", "_annual")]
KEY = ["sid", "pollutant"]


def families(run: str) -> list[str]:
    return [f for f in ALL_FAMILIES if (FITS / run / f).is_dir()]


def scheme_columns(run: str) -> dict[str, str]:
    """Saved column -> output suffix: '' for the primary scheme, '_annual' for Grange & Carslaw."""
    c = cfg()
    n = c["resamples_max"] if run == "pilot" else c["resamples_default"]
    schemes = [c["resample_scheme"], *c["resample_schemes_sensitivity"]]
    return {f"dw_{s}_n{n}": ("" if s == c["resample_scheme"] else f"_{s}") for s in schemes}


def load_run(run: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Metrics per task, and daily deweathered values (µg/m³, smeared) of both families side by side."""
    cols = scheme_columns(run)
    series = pd.read_csv(INPUTS / run / "series.csv")
    if "skipped" in series:
        series = series[series.skipped.isna()]
    mets, days = [], []
    fams = families(run) if run != "pilot" else list(COMPETING)
    for r in series.itertuples():
        per = []
        for fam in fams:
            out, _ = collect.load(run, fam, r.pollutant, r.sid)
            m = collect.metrics(out)
            clamp = cvcheck_path(run, fam, "clamp", r.pollutant, r.sid)
            if clamp.exists():
                cv = pd.read_parquet(clamp)
                m["r2_oos_clamp"] = collect.r2(out.y.where(cv.cv_fold.to_numpy() > 0).to_numpy(), cv.cv_pred.to_numpy())
            mets.append({"sid": r.sid, "pollutant": r.pollutant, "family": fam, "run": run, "n_folds": r.n_folds, **m})
            d = collect.deweathered(out, m["smear"])
            per.append(d[["date", *cols]].rename(columns={k: f"dw_{fam}{v}" for k, v in cols.items()}))
        d = per[0]
        for q in per[1:]:
            d = d.merge(q, on="date")
        days.append(d.assign(sid=r.sid, pollutant=r.pollutant))
    return pd.DataFrame(mets), pd.concat(days, ignore_index=True)


def choose_family(mets: pd.DataFrame) -> dict:
    """Registered rule (DEC-088): the family with the higher median out-of-sample R² over all
    series is primary. Series without a CV fold have no out-of-sample R² and do not vote. The
    choice under the other test-year trend convention is recorded beside it (DEC-107)."""
    m = mets[mets.family.isin(COMPETING)].dropna(subset=["r2_oos"])
    med = m.groupby("family").r2_oos.median()
    by_pol = m.groupby(["pollutant", "family"]).r2_oos.median().unstack()
    w = m.pivot_table(index=KEY, columns="family", values="r2_oos").dropna()
    out = {
        "primary": med.idxmax(),
        "sensitivity": med.idxmin(),
        "median_r2_oos": med.round(4).to_dict(),
        "median_r2_oos_by_pollutant": {p: by_pol.loc[p].round(4).to_dict() for p in by_pol.index},
        "series_with_cv": int(len(w)),
        "series_where_gam_better": int((w.gam > w.lgbm).sum()),
        "cv_trend": cfg()["cv_trend"],
        "rule": "higher median out-of-sample R2 (log scale) under blocked forward-chaining CV by year (DEC-088)",
    }
    if "r2_oos_clamp" in m:
        mc = m.dropna(subset=["r2_oos_clamp"]).groupby("family").r2_oos_clamp.median()
        out["median_r2_oos_clamp"] = mc.round(4).to_dict()
        out["primary_under_clamp"] = mc.idxmax()
    return out


def present(d: pd.DataFrame) -> list[str]:
    return [c for c in DW if c in d]


def guard_flags(t: pd.DataFrame) -> pd.DataFrame:
    """DEC-117 (c): flag, never drop, a deweathered mean outside guard_ratio x the raw mean."""
    lo, hi = cfg()["guard_ratio"]
    for c in [*present(t), "dw", "dw_annual"]:
        r = t[c] / t.raw
        t[f"guard_{c}"] = (r > hi) | (r < lo)
    return t


def raw_days() -> pd.DataFrame:
    cols = ["sid", "date_ist"] + [f"{p}{s}" for p in POLLUTANTS for s in ("", "_h1", "_mean3", "_h3")]
    d = pd.read_parquet(PROCESSED / "station_day.parquet", columns=cols).rename(columns={"date_ist": "date"})
    parts = []
    for p in POLLUTANTS:
        x = d[["sid", "date", p, f"{p}_h1", f"{p}_mean3", f"{p}_h3"]]
        x.columns = ["sid", "date", "obs", "h1", "obs3", "h3"]
        parts.append(x.assign(pollutant=p))
    return pd.concat(parts, ignore_index=True)


def near_constant() -> pd.DataFrame:
    y = pd.read_parquet(PROCESSED / "station_year_near_constant.parquet")
    return y[["sid", "pollutant", "year", "near_constant"]]


def station_year_table(day: pd.DataFrame, primary: str) -> pd.DataFrame:
    """Raw and deweathered means over each variant's valid days; `valid` is the registered rule."""
    q = pd.read_parquet(PROCESSED / "station_year_quality.parquet")
    rows = []
    for v, (hcol, t) in VARIANTS.items():
        need = int(np.ceil(24 * t))
        obs = "obs3" if hcol == "h3" else "obs"
        d = day[day[hcol] >= need].assign(year=lambda x: x.date.dt.year)
        g = d.groupby(["sid", "pollutant", "year"])
        y = g[[obs, *present(d)]].mean().rename(columns={obs: "raw"}).assign(days=g.size())
        y = y.reset_index().merge(
            q[["sid", "pollutant", "year", f"valid_{v}"]].rename(columns={f"valid_{v}": "valid"}),
            on=["sid", "pollutant", "year"], how="left",
        )  # fmt: skip
        rows.append(y.assign(variant=v, valid=y.valid.fillna(False).astype(bool)))
    y = pd.concat(rows, ignore_index=True)
    y["dw"], y["dw_annual"] = y[f"dw_{primary}"], y[f"dw_{primary}_annual"]
    return y


def station_month_table(day: pd.DataFrame, primary: str) -> pd.DataFrame:
    share = params()["completeness"]["min_day_share_per_year"]
    need = int(np.ceil(24 * params()["completeness"]["min_hour_share_per_day"]))
    d = day[day.h1 >= need].assign(month=lambda x: x.date.dt.to_period("M"))
    g = d.groupby(["sid", "pollutant", "month"])
    m = g[["obs", *present(d)]].mean().rename(columns={"obs": "raw"}).assign(days=g.size()).reset_index()
    m["valid"] = m.days >= share * m.month.dt.days_in_month
    m["dw"], m["dw_annual"] = m[f"dw_{primary}"], m[f"dw_{primary}_annual"]
    m["month"] = m.month.dt.to_timestamp()
    m["year"] = m.month.dt.year
    return m


def attach_station_info(t: pd.DataFrame) -> pd.DataFrame:
    reg = pd.read_csv(INTERIM / "station_regions.csv")
    st = pd.read_csv(PROCESSED / "stations.csv", usecols=["sid", "reenu_decided"])
    q = pd.read_parquet(PROCESSED / "station_year_quality.parquet", columns=["sid", "pollutant", "year", "reliability"])
    t = t.merge(reg, on="sid", how="left").merge(st, on="sid", how="left")
    t = t.merge(q, on=["sid", "pollutant", "year"], how="left").merge(near_constant(), on=["sid", "pollutant", "year"], how="left")
    t["near_constant"] = t.near_constant.fillna(False).astype(bool)
    return t.assign(inside_unit=t.km_to_unit.eq(0), covid_2020=t.year.eq(2020))


def with_rules(primary_t: pd.DataFrame, registered_t: pd.DataFrame, refit: pd.DataFrame) -> pd.DataFrame:
    """Stack the two validity rules. `refit` lists the (sid, pollutant) series of the registered run."""
    p = primary_t.assign(rule="primary", valid=primary_t.valid & ~primary_t.near_constant)
    keep = primary_t.merge(refit, on=KEY, how="left", indicator=True)._merge.eq("left_only").to_numpy()
    r = pd.concat([primary_t[keep], registered_t], ignore_index=True).assign(rule="registered_flags")
    return pd.concat([p, r], ignore_index=True)


def city(t: pd.DataFrame, period: str) -> pd.DataFrame:
    v = t[t.valid & t.inside_unit & t.dw.notna()]
    g = v.groupby(["rule", "unit_id", "region", "pollutant", period])
    c = g[["raw", "dw", "dw_annual", *present(v)]].mean().assign(n_stations=g.sid.nunique()).reset_index()
    year = c[period].dt.year if period == "month" else c[period]
    return c.assign(covid_2020=year.eq(2020))


def divergence_flags(sy: pd.DataFrame) -> pd.DataFrame:
    """DEC-111. Per station-pollutant, over its valid station-years (primary rule, primary
    completeness variant, seasonal scheme): centre each family's log annual deweathered mean on its
    own mean over those years; D = the largest absolute gap between the two centred series, in %.
    A constant difference in level between the families is not divergence; a difference in how the
    level moves from year to year is. Needs >= divergence_min_years valid years."""
    c = cfg()
    y = sy[(sy.rule == "primary") & (sy.variant == "q1_t75") & sy.valid].copy()
    for f in COMPETING:
        ly = np.log(y[f"dw_{f}"])
        y[f"dev_{f}"] = ly - ly.groupby([y.sid, y.pollutant]).transform("mean")
    y["gap"] = (y.dev_lgbm - y.dev_gam).abs()
    d = y.groupby(KEY).agg(valid_years=("year", "size"), D_pct=("gap", "max")).reset_index()
    d["D_pct"] = (100 * d.D_pct).where(d.valid_years >= c["divergence_min_years"])
    d["diverges"] = d.D_pct > c["divergence_flag_pct"]
    return d


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", default="main", choices=["main", "pilot"])
    run = ap.parse_args().run
    out = OUT if run == "main" else INTERIM / "normalise" / "pilot" / "aggregate"
    out.mkdir(parents=True, exist_ok=True)
    mets, dw = load_run(run)
    choice = choose_family(mets)
    primary = choice["primary"]
    raw = raw_days()
    day = raw.merge(dw, on=["sid", "pollutant", "date"], how="inner")
    has_reg = run == "main" and (INPUTS / "registered" / "series.csv").exists()
    if has_reg:
        mets_r, dw_r = load_run("registered")
        day_r = raw.merge(dw_r, on=["sid", "pollutant", "date"], how="inner")
        refit = dw_r[KEY].drop_duplicates()
    else:
        mets_r, day_r, refit = mets.iloc[:0], day.iloc[:0], day[KEY].iloc[:0]
    sy = with_rules(
        attach_station_info(station_year_table(day, primary)),
        attach_station_info(station_year_table(day_r, primary)), refit,
    )  # fmt: skip
    sm = with_rules(
        attach_station_info(station_month_table(day, primary)),
        attach_station_info(station_month_table(day_r, primary)), refit,
    )  # fmt: skip
    sy = guard_flags(sy)
    div = divergence_flags(sy)
    mets = pd.concat([mets.merge(div, on=KEY, how="left"), mets_r], ignore_index=True)

    mets.to_parquet(out / "series_metrics.parquet", index=False)
    (out / "family_choice.json").write_text(json.dumps(choice, indent=1), encoding="utf-8")
    day.to_parquet(out / "station_day.parquet", index=False)
    sy.to_parquet(out / "station_year.parquet", index=False)
    sm.to_parquet(out / "station_month.parquet", index=False)
    city(sm, "month").to_parquet(out / "city_month.parquet", index=False)
    city(sy[sy.variant == "q1_t75"], "year").to_parquet(out / "city_year.parquet", index=False)
    print(json.dumps(choice, indent=1))
    n = div.D_pct.notna().sum()
    print(f"{len(div)} series; D defined for {n}; {int(div.diverges.sum())} diverge (D > {cfg()['divergence_flag_pct']}%)")


if __name__ == "__main__":
    main()

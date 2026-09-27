"""Collect the full deweathering run, choose the primary family, aggregate to city-month and
city-year (Phase 5, RQ2; DEC-088, DEC-105).

    python -m src.normalise.aggregate [--run main]

Outputs (data/processed/deweathered/):
    series_metrics.parquet   one row per station x pollutant x family: out-of-sample R², RMSE,
                             in-sample R², residual ACF lags 1-7, smearing factor; plus D (family
                             divergence, %) and `diverges` (D > divergence_flag_pct)
    family_choice.json       the primary family by the registered rule and the numbers behind it
    station_day.parquet      sid, pollutant, date, raw daily means (primary and 3-of-4-hour rule,
                             with their valid-hour counts), deweathered daily values of both families
    station_year.parquet     station x pollutant x year x completeness variant (q1_t75 primary,
                             q1_t60, q1_t90, q3_t75): raw and deweathered means over the SAME valid
                             days, so raw minus deweathered is the weather part only; valid flag,
                             unit, region, reliability, reenu_decided, covid_2020
    station_month.parquet    primary variant: month means over valid days; valid = >= 75% valid days
    city_month.parquet, city_year.parquet
                             all-stations means over stations INSIDE the unit polygon with a valid
                             station-month / station-year (primary rule), raw and both families,
                             `dw` = the primary family; n_stations; covid_2020 flags 2020, whose
                             lockdown deweathering does not remove (analysis plan §5). The balanced
                             panel is Phase 6.
"""

import argparse
import json

import numpy as np
import pandas as pd

from src.common.paths import INTERIM, PROCESSED, params
from src.normalise import collect
from src.normalise.features import INPUTS, POLLUTANTS, cfg
from src.normalise.pilot import FAMILIES

OUT = PROCESSED / "deweathered"
VARIANTS = {"q1_t75": ("h1", 0.75), "q1_t60": ("h1", 0.60), "q1_t90": ("h1", 0.90), "q3_t75": ("h3", 0.75)}


def dw_column(run: str) -> str:
    c = cfg()
    n = c["resamples_max"] if run == "pilot" else c["resamples_default"]
    return f"dw_{c['resample_scheme']}_n{n}"


def load_run(run: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Metrics per task, and daily deweathered values (µg/m³, smeared) of both families side by side."""
    col = dw_column(run)
    series = pd.read_csv(INPUTS / run / "series.csv")
    if "skipped" in series:
        series = series[series.skipped.isna()]
    mets, days = [], []
    for r in series.itertuples():
        per = []
        for fam in FAMILIES:
            out, _ = collect.load(run, fam, r.pollutant, r.sid)
            m = collect.metrics(out)
            mets.append({"sid": r.sid, "pollutant": r.pollutant, "family": fam, "n_folds": r.n_folds, **m})
            per.append(collect.deweathered(out, m["smear"])[["date", col]].rename(columns={col: f"dw_{fam}"}))
        d = per[0].merge(per[1], on="date").assign(sid=r.sid, pollutant=r.pollutant)
        days.append(d)
    return pd.DataFrame(mets), pd.concat(days, ignore_index=True)


def choose_family(mets: pd.DataFrame) -> dict:
    """Registered rule (DEC-088): the family with the higher median out-of-sample R² over all
    series is primary. Series without a CV fold have no out-of-sample R² and do not vote."""
    m = mets.dropna(subset=["r2_oos"])
    med = m.groupby("family").r2_oos.median()
    by_pol = m.groupby(["pollutant", "family"]).r2_oos.median().unstack()
    w = m.pivot_table(index=["pollutant", "sid"], columns="family", values="r2_oos").dropna()
    return {
        "primary": med.idxmax(),
        "sensitivity": med.idxmin(),
        "median_r2_oos": med.round(4).to_dict(),
        "median_r2_oos_by_pollutant": {p: by_pol.loc[p].round(4).to_dict() for p in by_pol.index},
        "series_with_cv": int(len(w)),
        "series_where_gam_better": int((w.gam > w.lgbm).sum()),
        "rule": "higher median out-of-sample R2 (log scale) under blocked forward-chaining CV by year (DEC-088)",
    }


def raw_days() -> pd.DataFrame:
    cols = ["sid", "date_ist"] + [f"{p}{s}" for p in POLLUTANTS for s in ("", "_h1", "_mean3", "_h3")]
    d = pd.read_parquet(PROCESSED / "station_day.parquet", columns=cols).rename(columns={"date_ist": "date"})
    parts = []
    for p in POLLUTANTS:
        x = d[["sid", "date", p, f"{p}_h1", f"{p}_mean3", f"{p}_h3"]]
        x.columns = ["sid", "date", "obs", "h1", "obs3", "h3"]
        parts.append(x.assign(pollutant=p))
    return pd.concat(parts, ignore_index=True)


def station_year_table(day: pd.DataFrame, primary: str) -> pd.DataFrame:
    q = pd.read_parquet(PROCESSED / "station_year_quality.parquet")
    rows = []
    for v, (hcol, t) in VARIANTS.items():
        need = int(np.ceil(24 * t))
        obs = "obs3" if hcol == "h3" else "obs"
        d = day[day[hcol] >= need].assign(year=lambda x: x.date.dt.year)
        g = d.groupby(["sid", "pollutant", "year"])
        y = g[[obs, "dw_lgbm", "dw_gam"]].mean().rename(columns={obs: "raw"}).assign(days=g.size())
        y = y.reset_index().merge(
            q[["sid", "pollutant", "year", f"valid_{v}"]].rename(columns={f"valid_{v}": "valid"}),
            on=["sid", "pollutant", "year"], how="left",
        )  # fmt: skip
        rows.append(y.assign(variant=v, valid=y.valid.fillna(False).astype(bool)))
    y = pd.concat(rows, ignore_index=True)
    y["dw"] = y[f"dw_{primary}"]
    return y


def attach_station_info(t: pd.DataFrame) -> pd.DataFrame:
    reg = pd.read_csv(INTERIM / "station_regions.csv")
    st = pd.read_csv(PROCESSED / "stations.csv", usecols=["sid", "reenu_decided"])
    q = pd.read_parquet(PROCESSED / "station_year_quality.parquet", columns=["sid", "pollutant", "year", "reliability"])
    t = t.merge(reg, on="sid", how="left").merge(st, on="sid", how="left")
    if "year" in t:
        t = t.merge(q, on=["sid", "pollutant", "year"], how="left")
    return t.assign(inside_unit=t.km_to_unit.eq(0))


def station_month_table(day: pd.DataFrame, primary: str) -> pd.DataFrame:
    share = params()["completeness"]["min_day_share_per_year"]
    need = int(np.ceil(24 * params()["completeness"]["min_hour_share_per_day"]))
    d = day[day.h1 >= need].assign(month=lambda x: x.date.dt.to_period("M"))
    g = d.groupby(["sid", "pollutant", "month"])
    m = g[["obs", "dw_lgbm", "dw_gam"]].mean().rename(columns={"obs": "raw"}).assign(days=g.size()).reset_index()
    m["valid"] = m.days >= share * m.month.dt.days_in_month
    m["dw"] = m[f"dw_{primary}"]
    m["month"] = m.month.dt.to_timestamp()
    return m


def city(t: pd.DataFrame, period: str) -> pd.DataFrame:
    v = t[t.valid & t.inside_unit & t.dw.notna()]
    g = v.groupby(["unit_id", "region", "pollutant", period])
    c = g[["raw", "dw", "dw_lgbm", "dw_gam"]].mean().assign(n_stations=g.sid.nunique()).reset_index()
    year = c[period].dt.year if period == "month" else c[period]
    return c.assign(covid_2020=year.eq(2020))


def divergence_flags(sy: pd.DataFrame) -> pd.DataFrame:
    """D per station-pollutant (primary variant, valid station-years): the largest gap between the
    families' deweathered annual series, each relative to its own mean (log scale, %)."""
    y = sy[(sy.variant == "q1_t75") & sy.valid].copy()
    for f in FAMILIES:
        ly = np.log(y[f"dw_{f}"])
        y[f"dev_{f}"] = ly - ly.groupby([y.sid, y.pollutant]).transform("mean")
    y["gap"] = (y.dev_lgbm - y.dev_gam).abs()
    d = y.groupby(["sid", "pollutant"]).agg(valid_years=("year", "size"), D_pct=("gap", "max")).reset_index()
    d["D_pct"] *= 100
    d["diverges"] = d.D_pct > cfg()["divergence_flag_pct"]
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
    day = raw_days().merge(dw, on=["sid", "pollutant", "date"], how="inner")
    sy = attach_station_info(station_year_table(day, primary))
    sy["covid_2020"] = sy.year.eq(2020)
    sm = attach_station_info(station_month_table(day, primary))
    div = divergence_flags(sy)
    mets = mets.merge(div, on=["sid", "pollutant"], how="left")

    mets.to_parquet(out / "series_metrics.parquet", index=False)
    (out / "family_choice.json").write_text(json.dumps(choice, indent=1), encoding="utf-8")
    day.to_parquet(out / "station_day.parquet", index=False)
    sy.to_parquet(out / "station_year.parquet", index=False)
    sm.to_parquet(out / "station_month.parquet", index=False)
    city(sm, "month").to_parquet(out / "city_month.parquet", index=False)
    city(sy[sy.variant == "q1_t75"], "year").to_parquet(out / "city_year.parquet", index=False)
    print(json.dumps(choice, indent=1))
    print(f"{len(mets) // 2} series; {int(div.diverges.sum())} diverge (D > {cfg()['divergence_flag_pct']}%)")


if __name__ == "__main__":
    main()

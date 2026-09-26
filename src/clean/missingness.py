"""Missingness as data (proposal stage 3), DEC-074: do gaps cluster in polluted periods?

Unit: station-days inside each station's active span (first to last day with any data for that
pollutant). missing = the day is not valid under the primary rule (< 18 usable hours).

1. Season and year (all stations). Linear probability model with station fixed effects:
       missing ~ season + year | station, standard errors clustered by station.
   Seasons: winter Dec-Feb, pre-monsoon Mar-May, monsoon Jun-Sep, post-monsoon Oct-Nov.
2. Pollution level (stations with two neighbours). The neighbour reference (src/clean/spatial.py)
   is observed on the days the station itself is missing, so it measures how polluted a missing
   day was. Within each station, days are split into terciles of the reference:
       missing ~ reference tercile + season + year | station
   A positive high-tercile coefficient, net of season, means missing-not-at-random: gaps fall on
   the dirtiest days, beyond what winter alone explains.
3. What it does to annual means. For station-years valid under the primary rule that have a
   reference: fill each missing day with exp(reference + that station-year's median residual) and
   compare the filled annual mean with the naive mean of observed days.

Outputs (data/interim/audit/): missingness_models.csv, missingness_by_month.csv, missingness_bias.csv

    python -m src.clean.missingness
"""

import math

import numpy as np
import pandas as pd
import pyfixest as pf

from src.clean.spatial import AUDIT, PM
from src.common.paths import PROCESSED, params

SEASON = {12: "winter", 1: "winter", 2: "winter", 3: "pre-monsoon", 4: "pre-monsoon", 5: "pre-monsoon",
          6: "monsoon", 7: "monsoon", 8: "monsoon", 9: "monsoon", 10: "post-monsoon", 11: "post-monsoon"}  # fmt: skip


def station_days(day: pd.DataFrame, p: str) -> pd.DataFrame:
    """Every day in each station's active span, with missing = not valid (primary rule)."""
    need = math.ceil(24 * params()["completeness"]["min_hour_share_per_day"])
    d = day[["sid", "date_ist", p, f"{p}_h1"]].copy()
    d["date_ist"] = pd.to_datetime(d.date_ist)
    active = d[d[f"{p}_h1"] > 0].groupby("sid").date_ist.agg(["min", "max"])
    frames = []
    for sid, (a, b) in active.iterrows():
        idx = pd.DataFrame({"sid": sid, "date_ist": pd.date_range(a, b, freq="D")})
        frames.append(idx)
    full = pd.concat(frames, ignore_index=True).merge(d, on=["sid", "date_ist"], how="left")
    full["missing"] = (full[f"{p}_h1"].fillna(0) < need).astype(int)
    full["year"] = full.date_ist.dt.year
    full["month"] = full.date_ist.dt.month
    full["season"] = full.month.map(SEASON)
    return full


def fit(formula: str, data: pd.DataFrame, label: str, p: str) -> pd.DataFrame:
    m = pf.feols(formula, data=data, vcov={"CRV1": "sid"})
    t = m.tidy().reset_index().rename(columns={"Coefficient": "term"})
    return t.assign(model=label, pollutant=p, n_obs=m._N, n_stations=data.sid.nunique())


def main() -> None:
    day = pd.read_parquet(PROCESSED / "station_day.parquet")
    ref = pd.read_parquet(AUDIT / "neighbour_ref.parquet")
    models, months, bias = [], [], []
    for p in PM:
        d = station_days(day, p)
        d["season"] = pd.Categorical(d.season, ["monsoon", "pre-monsoon", "post-monsoon", "winter"])
        models.append(fit("missing ~ C(season) + C(year) | sid", d, "season_year", p))
        months.append(
            d.groupby(["year", "month"])
            .missing.mean()
            .rename("missing_share")
            .reset_index()
            .assign(pollutant=p)
        )
        # neighbour reference is needed on ALL days (including the station's missing ones)
        r = ref[ref.pollutant == p]
        nb_days = _reference_all_days(day, r, p)
        dn = d.merge(nb_days, on=["sid", "date_ist"], how="inner")
        dn["ref_tercile"] = dn.groupby("sid").ref.transform(
            lambda s: pd.qcut(s.rank(method="first"), 3, labels=["low", "mid", "high"])
        )
        dn["ref_tercile"] = pd.Categorical(dn.ref_tercile, ["low", "mid", "high"])
        models.append(
            fit("missing ~ C(ref_tercile) + C(season) + C(year) | sid", dn, "pollution_level", p)
        )
        bias.append(_annual_bias(dn, r, p))
    pd.concat(models, ignore_index=True).to_csv(AUDIT / "missingness_models.csv", index=False)
    pd.concat(months, ignore_index=True).to_csv(AUDIT / "missingness_by_month.csv", index=False)
    b = pd.concat(bias, ignore_index=True)
    b.to_csv(AUDIT / "missingness_bias.csv", index=False)
    print(
        pd.concat(models)
        .query("~term.str.contains('year')")[
            ["model", "pollutant", "term", "Estimate", "Std. Error"]
        ]
        .to_string()
    )
    print(b.groupby("pollutant").bias_pct.describe())


def _reference_all_days(day: pd.DataFrame, r: pd.DataFrame, p: str) -> pd.DataFrame:
    """The neighbour reference for every day, including days the station itself is missing.
    neighbour_ref.parquet holds only days where the station is valid, so it is rebuilt here from
    the neighbours alone."""
    from src.clean.spatial import neighbour_lists, valid_hours
    from src.clean.station_meta import load_stations

    nbrs = neighbour_lists(load_stations(), params()["flags"]["neighbour_radius_km"])
    d = day[day[f"{p}_h1"] >= valid_hours()][["sid", "date_ist", p]].dropna()
    d = d[d[p] > 0]
    wide = np.log(d.pivot(index="date_ist", columns="sid", values=p))
    rows = []
    for sid in r.sid.unique():
        cols = [c for c in nbrs.get(sid, []) if c in wide.columns]
        if len(cols) < 2:
            continue
        sub = wide[cols]
        ref = sub.median(axis=1).where(sub.notna().sum(axis=1) >= 2).dropna()
        rows.append(
            pd.DataFrame({"sid": sid, "date_ist": pd.to_datetime(ref.index), "ref": ref.to_numpy()})
        )
    return pd.concat(rows, ignore_index=True)


def _annual_bias(dn: pd.DataFrame, r: pd.DataFrame, p: str) -> pd.DataFrame:
    q = pd.read_parquet(PROCESSED / "station_year_quality.parquet")
    valid = q[(q.pollutant == p) & q.valid_q1_t75][["sid", "year"]]
    x = dn.merge(valid, on=["sid", "year"])
    res = (
        r.assign(year=pd.to_datetime(r.date_ist).dt.year)
        .groupby(["sid", "year"])
        .resid.median()
        .rename("med_resid")
    )
    x = x.merge(res.reset_index(), on=["sid", "year"], how="inner")
    x["filled"] = np.where(x.missing == 1, np.exp(x.ref + x.med_resid), x[p])
    g = x.groupby(["sid", "year"])
    out = pd.DataFrame({"naive": g.apply(lambda t: t.loc[t.missing == 0, p].mean(), include_groups=False),
                        "filled": g.filled.mean(), "missing_share": g.missing.mean()})  # fmt: skip
    out["bias_pct"] = 100 * (out.naive / out.filled - 1)
    return out.reset_index().assign(pollutant=p)


if __name__ == "__main__":
    main()

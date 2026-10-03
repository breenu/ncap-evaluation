"""Exploratory analysis (proposal stage 4): the Phase 3 EDA tables.

BLINDING (pre-registration rule, until the analysis plan is approved): nothing here compares NCAP with non-NCAP
units.

Tables -> data/interim/eda/*.csv (read by src/clean/audit_report.py and the figure modules);
station_year.parquet -> data/processed. Since Phase 9 (DEC-190) this module draws nothing: figure 2 is
src/viz/fig2_station_entry.py, figure 8 src/viz/fig8_quality_heatmap.py, and E1-E4 src/viz/eda_figures.py.

    python -m src.viz.eda
"""

import geopandas as gpd
import numpy as np
import pandas as pd

from src.common.paths import INTERIM, PROCESSED

EDA = INTERIM / "eda"
RNG = np.random.default_rng(20260926)


def _ci(x: pd.Series) -> tuple[float, float, float]:
    """Mean and 95% t-interval (NaN interval if n < 2)."""
    x = x.dropna()
    m = x.mean()
    if len(x) < 2:
        return m, np.nan, np.nan
    from scipy import stats

    h = stats.t.ppf(0.975, len(x) - 1) * x.std(ddof=1) / np.sqrt(len(x))
    return m, m - h, m + h


# ------------------------------------------------------------------ tables


def station_year() -> pd.DataFrame:
    """Annual mean of valid days, per station-year-pollutant, with validity and reliability."""
    day = pd.read_parquet(PROCESSED / "station_day.parquet")
    q = pd.read_parquet(PROCESSED / "station_year_quality.parquet")
    reg = pd.read_csv(INTERIM / "station_regions.csv")
    rows = []
    for p in ("pm25", "pm10"):
        d = day[day[f"{p}_h1"] >= 18].assign(year=pd.to_datetime(day.date_ist).dt.year)
        m = (
            d.groupby(["sid", "year"])[p]
            .mean()
            .rename("annual_mean")
            .reset_index()
            .assign(pollutant=p)
        )
        rows.append(m)
    y = pd.concat(rows).merge(
        q[["sid", "year", "pollutant", "valid_q1_t75", "valid_q3_t75", "valid_q1_t60", "valid_q1_t90", "reliability"]],
        on=["sid", "year", "pollutant"], how="right",
    )  # fmt: skip
    y = y.merge(reg[["sid", "unit_id", "region"]], on="sid", how="left")
    y.to_parquet(PROCESSED / "station_year.parquet", index=False)
    return y


def first_years(day: pd.DataFrame) -> pd.Series:
    any_pm = day[(day.pm25_h1 > 0) | (day.pm10_h1 > 0)]
    return pd.to_datetime(any_pm.groupby("sid").date_ist.min()).dt.year.rename("first_year")


def entrants(sy: pd.DataFrame) -> pd.DataFrame:
    """For each unit-year: log(mean of entrants' annual means) - log(mean of incumbents'), where
    entrants have their first valid year then and incumbents were valid before and in that year.
    All units pooled (no NCAP split)."""
    v = sy[sy.valid_q1_t75 & sy.annual_mean.notna() & sy.unit_id.notna()]
    rows = []
    for p, g in v.groupby("pollutant"):
        first = g.groupby("sid").year.min()
        g = g.assign(first=g.sid.map(first))
        for (u, y), c in g.groupby(["unit_id", "year"]):
            ent, inc = c[c["first"] == y], c[c["first"] < y]
            if len(ent) and len(inc):
                rows.append({"pollutant": p, "unit_id": u, "year": y, "n_entrants": len(ent), "n_incumbents": len(inc),
                             "log_ratio": np.log(ent.annual_mean.mean()) - np.log(inc.annual_mean.mean())})  # fmt: skip
    e = pd.DataFrame(rows)
    summ = []
    for (p, y), g in e.groupby(["pollutant", "year"]):
        m, lo, hi = _ci(g.log_ratio)
        summ.append({"pollutant": p, "year": y, "units": len(g), "entrants": g.n_entrants.sum(), "mean_log_ratio": m,
                     "ci_lo": lo, "ci_hi": hi})  # fmt: skip
    for p, g in e.groupby("pollutant"):
        m, lo, hi = _ci(g.log_ratio)
        summ.append({"pollutant": p, "year": "all", "units": g.unit_id.nunique(), "entrants": g.n_entrants.sum(),
                     "mean_log_ratio": m, "ci_lo": lo, "ci_hi": hi})  # fmt: skip
    s = pd.DataFrame(summ)
    for c in ("mean_log_ratio", "ci_lo", "ci_hi"):
        s[c.replace("log_ratio", "pct").replace("ci_lo", "pct_lo").replace("ci_hi", "pct_hi")] = (
            100 * (np.exp(s[c]) - 1)
        )
    return s


def ground_vs_sat(sy: pd.DataFrame) -> pd.DataFrame:
    sat = pd.read_parquet(PROCESSED / "station_year_sat.parquet")
    v = sy[(sy.pollutant == "pm25") & sy.valid_q1_t75 & sy.annual_mean.notna()]
    rows = []
    for prod in ("V5GL06", "V6GL03"):
        x = v.merge(sat[sat["product"] == prod], on=["sid", "year"]).dropna(subset=["pm25_cell"])
        for y, g in x.groupby("year"):
            if len(g) < 5:
                continue
            a, b = np.log(g.annual_mean.to_numpy()), np.log(g.pm25_cell.to_numpy())
            r = np.corrcoef(a, b)[0, 1]
            boots = []
            for _ in range(1000):
                i = RNG.integers(0, len(a), len(a))
                boots.append(np.corrcoef(a[i], b[i])[0, 1])
            rows.append({"product": prod, "year": y, "stations": len(g), "r": r, "r_lo": np.nanpercentile(boots, 2.5),
                         "r_hi": np.nanpercentile(boots, 97.5),
                         "median_ratio": float(np.median(g.annual_mean / g.pm25_cell))})  # fmt: skip
    return pd.DataFrame(rows)


def seasonal(sy_day: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    reg = pd.read_csv(INTERIM / "station_regions.csv")
    d = sy_day[sy_day.pm25_h1 >= 18].merge(reg[["sid", "region"]], on="sid")
    d = d.assign(date=pd.to_datetime(d.date_ist))
    d = d[d.date.dt.year <= 2025]
    sm = d.groupby(["region", "sid", d.date.dt.month.rename("month")]).pm25.mean().reset_index()
    ground = []
    for (r, mth), g in sm.groupby(["region", "month"]):
        m, lo, hi = _ci(g.pm25)
        ground.append(
            {"region": r, "month": mth, "stations": len(g), "mean": m, "lo": lo, "hi": hi}
        )
    sat = pd.read_parquet(PROCESSED / "unit_month_sat.parquet")
    ur = pd.read_csv(INTERIM / "unit_regions.csv")
    units = gpd.read_file(INTERIM / "sat_units.gpkg", ignore_geometry=True)
    s = sat[(sat["product"] == "V5GL06") & sat.year.between(2015, 2024)].merge(ur, on="unit_id")
    s = s.merge(units[["unit_id", "in_primary", "pop_2020"]], on="unit_id")
    s = s[s.in_primary & (s.pop_2020 >= 1e5)]
    um = s.groupby(["region", "unit_id", "month"]).pm25_popw.mean().reset_index()
    satr = []
    for (r, mth), g in um.groupby(["region", "month"]):
        m, lo, hi = _ci(g.pm25_popw)
        satr.append({"region": r, "month": mth, "units": len(g), "mean": m, "lo": lo, "hi": hi})
    return pd.DataFrame(ground), pd.DataFrame(satr)


def city_trends(sy: pd.DataFrame, n: int = 6) -> pd.DataFrame:
    units = gpd.read_file(INTERIM / "sat_units.gpkg", ignore_geometry=True)
    v = sy[(sy.pollutant == "pm25") & sy.valid_q1_t75 & sy.annual_mean.notna() & (sy.year <= 2025)]
    top = v.groupby("unit_id").size().sort_values(ascending=False).head(n).index
    rows = []
    for (u, y), g in v[v.unit_id.isin(top)].groupby(["unit_id", "year"]):
        m, lo, hi = _ci(g.annual_mean)
        rows.append({"unit_id": u, "year": y, "stations": len(g), "mean": m, "lo": lo, "hi": hi})
    t = pd.DataFrame(rows).merge(units[["unit_id", "ncap_cities", "uc_ids"]], on="unit_id")
    uc = gpd.read_file(INTERIM / "ghsl" / "ucdb_india.gpkg", ignore_geometry=True)[
        ["uc_id", "uc_name"]
    ]
    first_uc = t.uc_ids.str.split(";").str[0].astype(int)
    t["name"] = first_uc.map(uc.set_index("uc_id").uc_name)
    return t.drop(columns=["ncap_cities"])  # names only; no NCAP labels (blinding)


def main() -> None:
    EDA.mkdir(parents=True, exist_ok=True)
    day = pd.read_parquet(PROCESSED / "station_day.parquet")
    sy = station_year()
    first = first_years(day)
    first.to_csv(EDA / "station_first_year.csv")
    e = entrants(sy)
    e.to_csv(EDA / "entrants.csv", index=False)
    gs = ground_vs_sat(sy)
    gs.to_csv(EDA / "ground_vs_satellite.csv", index=False)
    ground, sat = seasonal(day)
    ground.to_csv(EDA / "seasonal_ground.csv", index=False)
    sat.to_csv(EDA / "seasonal_satellite.csv", index=False)
    t = city_trends(sy)
    t.to_csv(EDA / "city_trends.csv", index=False)
    print("EDA tables written")


if __name__ == "__main__":
    main()

"""City-level family disagreement on the H4 quantity (DEC-120).

Per urban centre, pollutant and resampling scheme (primary validity rule, primary completeness
variant, stations inside the unit polygon, DEC-105):
    panel      strict: stations valid in 2018 and in every year to 2025 (DEC-088's balanced panel);
               loose: stations valid in both 2018 and 2025
    change     100 x (mean 2025 / mean 2018 - 1) of the city's deweathered mean over the panel, per
               family (GAM primary, LightGBM)
    diff_pp    GAM change - LightGBM change, in percentage points; flagged if |diff_pp| > 5
The raw change over the same panel is shown for scale. Covers every city with a panel (no NCAP
comparison). Stations in `watch_stations` (DEC-121) are named where they are in a city's panel.

    python -m src.normalise.city_disagreement  -> data/processed/deweathered/city_disagreement.csv
"""

import pandas as pd

from src.common.paths import params
from src.normalise.aggregate import OUT

Y0, Y1 = 2018, 2025
FLAG_PP = 5.0


def panel(sy: pd.DataFrame, strict: bool) -> pd.DataFrame:
    v = sy[(sy.rule == "primary") & (sy.variant == "q1_t75") & sy.valid & sy.inside_unit]
    years = set(range(Y0, Y1 + 1)) if strict else {Y0, Y1}
    ok = v[v.year.isin(years)].groupby(["sid", "pollutant"]).year.nunique().eq(len(years))
    keep = ok[ok].reset_index()[["sid", "pollutant"]]
    return v[v.year.isin([Y0, Y1])].merge(keep, on=["sid", "pollutant"])


def changes(p: pd.DataFrame, label: str) -> pd.DataFrame:
    watch = set(params().get("watch_stations", []))
    rows = []
    for (u, pol), g in p.groupby(["unit_id", "pollutant"]):
        a, b = g[g.year == Y0], g[g.year == Y1]
        r = {"panel": label, "unit_id": u, "pollutant": pol, "stations": g.sid.nunique(),
             "watch_stations": ", ".join(sorted(watch & set(g.sid)))}  # fmt: skip
        for col in ("raw", "dw_gam", "dw_lgbm", "dw_gam_annual", "dw_lgbm_annual"):
            r[f"chg_{col}"] = 100 * (b[col].mean() / a[col].mean() - 1)
        rows.append(r)
    t = pd.DataFrame(rows)
    t["diff_pp_seasonal"] = t.chg_dw_gam - t.chg_dw_lgbm
    t["diff_pp_grange"] = t.chg_dw_gam_annual - t.chg_dw_lgbm_annual
    t["flag_seasonal"] = t.diff_pp_seasonal.abs() > FLAG_PP
    t["flag_grange"] = t.diff_pp_grange.abs() > FLAG_PP
    return t


def build() -> pd.DataFrame:
    sy = pd.read_parquet(OUT / "station_year.parquet")
    t = pd.concat([changes(panel(sy, True), "strict"), changes(panel(sy, False), "loose")], ignore_index=True)
    from src.viz.fig3_deweathered import names

    nm = names()
    t.insert(2, "city", t.unit_id.map(nm).where(lambda s: s.notna(), t.unit_id))
    t.to_csv(OUT / "city_disagreement.csv", index=False)
    return t


def summary(t: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (pnl, pol), g in t.groupby(["panel", "pollutant"], sort=False):
        for s in ("seasonal", "grange"):
            d = g[f"diff_pp_{s}"].dropna()
            rows.append({"panel": pnl, "pollutant": pol, "scheme": s, "cities": len(d),
                         "median_abs_diff_pp": d.abs().median(), "p90_abs_diff_pp": d.abs().quantile(0.9),
                         "max_abs_diff_pp": d.abs().max(), "median_diff_pp": d.median(),
                         f"cities_over_{FLAG_PP:g}pp": int((d.abs() > FLAG_PP).sum())})  # fmt: skip
    return pd.DataFrame(rows).replace({"scheme": {"seasonal": "seasonal", "grange": "Grange & Carslaw"}})


if __name__ == "__main__":
    t = build()
    print(summary(t).round(2).to_string(index=False))
    f = t[(t.panel == "strict") & (t.flag_seasonal | t.flag_grange)]
    print(f[["city", "pollutant", "stations", "chg_raw", "chg_dw_gam", "chg_dw_lgbm", "diff_pp_seasonal",
             "diff_pp_grange", "watch_stations"]].round(1).to_string(index=False))

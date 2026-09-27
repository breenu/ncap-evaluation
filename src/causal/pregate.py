"""Phase 4 pre-gate inputs: the pre-2019 satellite panel, the control pool, baseline balance, and the
ground PM10 feasibility counts (docs/analysis_plan.md §6; DEC-013, DEC-087).

PRE-PERIOD ONLY. Every outcome table is read through `read_pre_period`, which filters to
year <= pregate.last_year (2018) *while reading* and asserts it afterwards, so no post-2018 value is
ever loaded. The MDE itself is estimated by src/causal/mde_placebo.R from the panel written here.

    python -m src.causal.pregate

Writes data/interim/pregate/: units.csv, pool_steps.csv, panel_annual.parquet, panel_season.parquet,
balance.csv, ground_counts.csv, ground_pairs.csv, monitor_gain.csv.
"""

import geopandas as gpd
import numpy as np
import pandas as pd

from src.causal import treatment
from src.common.paths import INTERIM, PROCESSED, params

OUT = INTERIM / "pregate"
# India-wide equal-area-ish projection for distances (WGS 84 / India NSF LCC).
INDIA_CRS = "EPSG:7755"


class PostPeriodLeak(RuntimeError):
    """Raised if a pre-gate table contains any year after pregate.last_year."""


def last_year() -> int:
    return int(params()["pregate"]["last_year"])


def assert_pre_period(df: pd.DataFrame, col: str = "year", last: int | None = None) -> pd.DataFrame:
    last = last_year() if last is None else last
    if len(df) and int(df[col].max()) > last:
        raise PostPeriodLeak(f"pre-gate table has {col} up to {int(df[col].max())} (> {last})")
    return df


def read_pre_period(path, columns=None, last: int | None = None, **filters) -> pd.DataFrame:
    """Read a Parquet table keeping only year <= last (filtered in the reader, then asserted)."""
    last = last_year() if last is None else last
    f = [("year", "<=", last)] + [(k, "==", v) for k, v in filters.items()]
    df = pd.read_parquet(path, columns=columns, filters=f)
    return assert_pre_period(df, last=last)


# ---------------------------------------------------------------- units, pool, spillover distance


def distance_to_ncap_km(units: gpd.GeoDataFrame) -> pd.Series:
    """Edge-to-edge distance (km) from every unit to the nearest *other* NCAP place.

    NCAP places are all units with an NCAP city, including the 10 buffered towns (they are treated
    places even though they are not in the primary estimate). A treated unit's own polygon is ignored.
    """
    g = units.to_crs(INDIA_CRS)
    ncap = g[g.ncap_cities.fillna("") != ""]
    dist = {uid: ncap[ncap.unit_id != uid].distance(geom).min() / 1000.0
            for uid, geom in zip(g.unit_id, g.geometry, strict=True)}  # fmt: skip
    return pd.Series(dist, name="dist_ncap_km")


def assign_roles(units: pd.DataFrame, min_pop: float, buffer_km: float) -> pd.DataFrame:
    """Role of every unit in the primary design, and whether it survives the spillover buffer.

    treated: in the primary set (a GHSL centre) and holds an NCAP city.
    control: in the primary set, no NCAP city, 2015 population >= min_pop, and does not contain the
             point of an NCAP town that has no centre of its own (drops Kalka, DEC-063).
    Everything else gets a reason. `in_buffered_pool`: a control at least buffer_km from every NCAP place.
    """
    u = units.copy()
    ncap = u.ncap_cities.fillna("") != ""
    holds_town = u.contains_ncap_town.fillna("") != ""
    u["role"] = np.select(
        [~u.in_primary & ncap, ~u.in_primary, ncap, u.pop_2015 < min_pop, holds_town],
        ["town_buffer (sensitivity only)", "not a GHSL centre", "treated", "below population threshold",
         "contains an NCAP town"],
        default="control",
    )  # fmt: skip
    u["in_buffered_pool"] = (u.role == "control") & (u.dist_ncap_km >= buffer_km)
    return u


def pool_steps(u: pd.DataFrame, buffers_km: list[float]) -> pd.DataFrame:
    """How the control pool shrinks at each rule, and its size under several spillover buffers."""
    prim = u[u.in_primary]
    non = prim[prim.ncap_cities.fillna("") == ""]
    big = non[non.pop_2015 >= params()["control_pool"]["min_population"]]
    ctl = u[u.role == "control"]
    rows = [
        ("GHSL urban centres in India (primary units)", len(prim)),
        ("... of which hold an NCAP city (treated units)", int((prim.role == "treated").sum())),
        ("Non-NCAP centres", len(non)),
        ("... with 2015 population >= 100,000", len(big)),
        ("... not containing an NCAP town's point (control pool)", len(ctl)),
    ]
    for b in buffers_km:
        rows.append(
            (f"... and at least {b:g} km from every NCAP place", int((ctl.dist_ncap_km >= b).sum()))
        )
    return pd.DataFrame(rows, columns=["step", "units"])


# ---------------------------------------------------------------- panels (pre-period only)


def season_panel(month: pd.DataFrame, winter_months: list[int]) -> pd.DataFrame:
    """Winter and non-winter means per unit and season-year.

    Winter season-year t = Oct t to Feb t+1 (so winter t=2019, Oct 2019 to Feb 2020, is the first
    fully after launch); non-winter t = the other months of year t (Mar to Sep). A season needs every
    one of its months; with data to Dec 2018 the last complete winter is 2017.
    """
    m = month.copy()
    m["season"] = np.where(m.month.isin(winter_months), "winter", "nonwinter")
    # Jan/Feb belong to the winter that started the previous October
    m["season_year"] = np.where((m.season == "winter") & (m.month <= 6), m.year - 1, m.year)
    need = {"winter": len(winter_months), "nonwinter": 12 - len(winter_months)}
    g = m.groupby(["unit_id", "season", "season_year"]).agg(pm25_popw=("pm25_popw", "mean"),
                                                            pm25_area=("pm25_area", "mean"),
                                                            months=("month", "nunique")).reset_index()  # fmt: skip
    g = g[g.months == g.season.map(need)].drop(columns="months")
    return g


def unit_slope(df: pd.DataFrame, y: str = "pm25_popw") -> pd.Series:
    """Per-unit OLS slope of log(y) on year: the pre-period trend, in log points per year."""

    def slope(g):
        x = g.year.to_numpy(float)
        return np.polyfit(x - x.mean(), np.log(g[y].to_numpy(float)), 1)[0]

    return df.groupby("unit_id")[["year", y]].apply(slope)


def smd(a: pd.Series, b: pd.Series, binary: bool = False) -> float:
    """Standardised mean difference (treated - control) / sqrt((var_t + var_c) / 2)."""
    a, b = a.dropna().astype(float), b.dropna().astype(float)
    if binary:
        va, vb = a.mean() * (1 - a.mean()), b.mean() * (1 - b.mean())
    else:
        va, vb = a.var(ddof=1), b.var(ddof=1)
    s = np.sqrt((va + vb) / 2)
    return float((a.mean() - b.mean()) / s) if s > 0 else 0.0


def balance_table(chars: pd.DataFrame, groups: dict[str, pd.Series]) -> pd.DataFrame:
    """Means of each characteristic for treated vs each control group, with SMDs.

    `chars`: one row per unit (index unit_id); `groups`: name -> boolean mask over chars' index, the
    first being the treated group.
    """
    (tname, tmask), *controls = groups.items()
    rows = []
    for col in chars.columns:
        binary = chars[col].dropna().isin([0, 1]).all()
        r = {"characteristic": col, tname: chars.loc[tmask, col].mean()}
        for cname, cmask in controls:
            r[cname] = chars.loc[cmask, col].mean()
            r[f"smd_vs_{cname}"] = smd(chars.loc[tmask, col], chars.loc[cmask, col], binary)
        rows.append(r)
    return pd.DataFrame(rows)


# ---------------------------------------------------------------- ground PM10 feasibility


def monitor_gain(
    first_year: pd.Series, station_units: pd.DataFrame, treated: pd.Series, years: list[int]
) -> pd.DataFrame:
    """Per treated unit: CAAQMS stations inside its polygon before `years[0]`, and new ones whose first
    PM data fall in years[0]..years[1] (the satellite post-period, DEC-096).

    NETWORK METADATA ONLY: uses the year each station first reported, never a pollution value, and
    no comparison with control units, so it is allowed before the gate.
    `first_year`: sid -> first year with any PM; `station_units`: sid, unit_id, km_to_unit (0 = inside).
    """
    inside = station_units[station_units.km_to_unit == 0][["sid", "unit_id"]]
    s = inside.assign(first_year=inside.sid.map(first_year)).dropna(subset=["first_year"])
    before = s[s.first_year < years[0]].groupby("unit_id").sid.nunique()
    new = s[s.first_year.between(years[0], years[1])].groupby("unit_id").sid.nunique()
    out = pd.DataFrame({"unit_id": treated.values})
    out["stations_before"] = out.unit_id.map(before).fillna(0).astype(int)
    out["stations_new"] = out.unit_id.map(new).fillna(0).astype(int)
    out["gained_monitor"] = out.stations_new > 0
    return out


def ground_counts(
    sy: pd.DataFrame, ncap_units: set[str], valid_col: str = "valid_q1_t75"
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Valid station-years and units by year and NCAP status, and stations valid in consecutive pre-years."""
    s = assert_pre_period(sy)
    s = s.assign(group=np.where(s.unit_id.isin(ncap_units), "NCAP unit", "non-NCAP unit"))
    v = s[s[valid_col]]
    counts = (v.groupby(["pollutant", "year", "group"])
               .agg(station_years=("sid", "nunique"), units=("unit_id", "nunique")).reset_index())  # fmt: skip
    pairs = []
    years = sorted(v.year.unique())
    for pol, g in v.groupby("pollutant"):
        for y0, y1 in zip(years[:-1], years[1:], strict=True):
            both = set(g[g.year == y0].sid) & set(g[g.year == y1].sid)
            for grp in ("NCAP unit", "non-NCAP unit"):
                gg = g[(g.year == y1) & g.sid.isin(both) & (g.group == grp)]
                pairs.append({"pollutant": pol, "years": f"{y0}-{y1}", "group": grp,
                              "stations": gg.sid.nunique(), "units": gg.unit_id.nunique()})  # fmt: skip
    return counts, pd.DataFrame(pairs)


# ---------------------------------------------------------------- main


def build() -> None:
    P = params()
    first, last = int(P["pregate"]["first_year"]), last_year()
    OUT.mkdir(parents=True, exist_ok=True)

    geo = gpd.read_file(INTERIM / "sat_units.gpkg")
    regions = pd.read_csv(INTERIM / "unit_regions.csv")
    cities = pd.read_csv(INTERIM / "ncap_cities.csv")
    funding = pd.read_csv(INTERIM / "ncap_funding_clean.csv")

    cp = P["control_pool"]
    units = pd.DataFrame(geo.drop(columns="geometry"))
    units["dist_ncap_km"] = units.unit_id.map(distance_to_ncap_km(geo))
    units = assign_roles(units, cp["min_population"], cp["spillover_buffer_km"])
    city_c = treatment.city_cohorts(cities, funding)
    units = units.merge(treatment.unit_cohorts(units, city_c), on="unit_id", how="left")
    units = units.merge(regions[["unit_id", "region"]], on="unit_id", how="left")
    keep = units.role.isin(["treated", "control"])
    units.to_csv(OUT / "units.csv", index=False)
    city_c.to_csv(OUT / "city_cohorts.csv", index=False)
    pool_steps(units, cp["spillover_buffer_report_km"]).to_csv(OUT / "pool_steps.csv", index=False)

    # --- satellite panels, pre-period only
    prod = P["satellite"]["primary"]
    ann = read_pre_period(PROCESSED / "unit_year_sat.parquet", product=prod,
                          columns=["unit_id", "year", "pm25_popw", "pm25_area", "product"])  # fmt: skip
    ann = ann[(ann.year >= first) & ann.unit_id.isin(units.unit_id[keep])]
    roles = units.loc[keep, ["unit_id", "role", "cohort_listed", "in_buffered_pool", "region"]]
    ann = ann.merge(roles, on="unit_id").drop(columns="product")
    if ann[["pm25_popw", "pm25_area"]].isna().any().any() or (ann.pm25_popw <= 0).any():
        raise ValueError("pre-period annual panel has missing or non-positive PM2.5")
    if ann.groupby("unit_id").size().nunique() != 1:
        raise ValueError("pre-period annual panel is not balanced")
    ann.to_parquet(OUT / "panel_annual.parquet", index=False)

    mon = read_pre_period(PROCESSED / "unit_month_sat.parquet", product=prod,
                          columns=["unit_id", "year", "month", "pm25_popw", "pm25_area", "product"])  # fmt: skip
    mon = mon[(mon.year >= first) & mon.unit_id.isin(units.unit_id[keep])]
    sea = season_panel(mon, P["pregate"]["winter_months"])
    # both seasons over the same season-years (2010-2017), so winter minus non-winter compares like with like
    sea = sea[sea.season_year.between(first, sea[sea.season == "winter"].season_year.max())]
    sea = sea.merge(roles, on="unit_id")
    if (
        sea.groupby(["season", "unit_id"]).size().nunique() != 1
        or sea.groupby("season").season_year.nunique().nunique() != 1
    ):
        raise ValueError("pre-period season panel is not balanced")
    sea.to_parquet(OUT / "panel_season.parquet", index=False)

    # --- baseline balance, 2010-2018
    u = units[keep].set_index("unit_id")
    lvl = ann.groupby("unit_id").pm25_popw.mean()
    win = sea[sea.season == "winter"].groupby("unit_id").pm25_popw.mean()
    chars = pd.DataFrame({
        f"PM2.5 mean {first}-{last} (ug/m3)": lvl,
        f"PM2.5 trend {first}-{last} (% per year)": 100 * (np.exp(unit_slope(ann)) - 1),
        f"Winter PM2.5 mean {first}-{last - 1} seasons (ug/m3)": win,
        "Population 2015 (log10)": np.log10(u.pop_2015),
        "Area (km2)": u.area_km2,
        **{f"Region: {r}": (u.region == r).astype(int) for r in sorted(u.region.dropna().unique())},
    })  # fmt: skip
    groups = {
        "treated": (u.role == "treated").reindex(chars.index),
        "control_pool": (u.role == "control").reindex(chars.index),
        "buffered_pool": u.in_buffered_pool.reindex(chars.index).fillna(False).astype(bool),
    }
    bt = balance_table(chars, groups)
    bt.insert(1, "n_treated", int(groups["treated"].sum()))
    bt["n_control_pool"] = int(groups["control_pool"].sum())
    bt["n_buffered_pool"] = int(groups["buffered_pool"].sum())
    bt.to_csv(OUT / "balance.csv", index=False)

    # --- ground PM10 (and PM2.5) pre-period feasibility
    sy = read_pre_period(PROCESSED / "station_year.parquet",
                         columns=["sid", "year", "pollutant", "unit_id", "valid_q1_t75"])  # fmt: skip
    ncap_units = set(units.unit_id[units.ncap_cities.fillna("") != ""])
    counts, pairs = ground_counts(sy, ncap_units)
    counts.to_csv(OUT / "ground_counts.csv", index=False)
    pairs.to_csv(OUT / "ground_pairs.csv", index=False)

    # --- calibration-leakage split: which treated units gained a monitor in the satellite post-period
    first = pd.read_csv(INTERIM / "eda" / "station_first_year.csv").set_index("sid").first_year
    st_units = pd.read_csv(INTERIM / "station_regions.csv")
    treated = units.unit_id[units.role == "treated"]
    monitor_gain(first, st_units, treated, P["robustness"]["leakage_gain_years"]).to_csv(
        OUT / "monitor_gain.csv", index=False
    )

    print(f"pregate: {int((units.role == 'treated').sum())} treated, {int((units.role == 'control').sum())} controls "
          f"({int(units.in_buffered_pool.sum())} after the {cp['spillover_buffer_km']} km buffer); "
          f"annual panel {ann.year.min()}-{ann.year.max()}, seasons to {sea.season_year.max()}")  # fmt: skip


if __name__ == "__main__":
    build()

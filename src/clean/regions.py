"""Region of every satellite unit and every station (rules: config/regions.yaml, DEC-075).

Outputs
    data/interim/unit_regions.csv     unit_id, region, elevation_m, coast_km
    data/interim/station_regions.csv  sid, region (the unit holding the station; else the station's
                                      own point by the same rules)

    python -m src.clean.regions
"""

import zipfile

import geopandas as gpd
import pandas as pd

from src.clean.geo import norm, states
from src.clean.station_meta import load_stations
from src.common.paths import CONFIG, INTERIM, load_yaml, raw_dir

METRIC = 7755


def coastline() -> gpd.GeoSeries:
    with zipfile.ZipFile(raw_dir("naturalearth") / "ne_10m_coastline.zip") as z:
        z.extractall(INTERIM / "naturalearth")
    c = gpd.read_file(INTERIM / "naturalearth" / "ne_10m_coastline.shp").to_crs(4326)
    return c.clip((60, 0, 100, 40)).to_crs(METRIC).geometry


def elevation() -> pd.Series:
    g = gpd.read_file(
        INTERIM / "ghsl" / "GHS_UCDB_GLOBE_R2024A.gpkg",
        layer="GHSL_UCDB_THEME_GEOGRAPHY_GLOBE_R2024A",
        where="GC_CNT_GAD_2025 = 'India'",
        ignore_geometry=True,
    )
    return g.set_index("ID_UC_G0").GE_ELV_AVG_2025


def assign(state: str, elev_m: float, coast_km: float, cfg: dict) -> str:
    """Pure rule, in the order of config/regions.yaml."""
    st = norm(state)
    if st in {norm(s) for s in cfg["northeast_states"]}:
        return "north-east"
    if (
        st in {norm(s) for s in cfg["igp_states"]}
        and pd.notna(elev_m)
        and elev_m < cfg["igp_max_elevation_m"]
    ):
        return "igp"
    if coast_km <= cfg["coastal_max_km"]:
        return "coastal"
    return "peninsular/other"


def main() -> None:
    cfg = load_yaml(CONFIG / "regions.yaml")
    units = gpd.read_file(INTERIM / "sat_units.gpkg")
    coast = coastline().union_all()
    st = states()[["state", "geometry"]]
    elev = elevation()
    pts = gpd.GeoDataFrame(
        units[["unit_id"]], geometry=units.geometry.representative_point(), crs=4326
    )
    ust = gpd.sjoin_nearest(pts.to_crs(METRIC), st.to_crs(METRIC), how="left").drop_duplicates(
        "unit_id"
    )
    units["state"] = units.unit_id.map(ust.set_index("unit_id").state)
    units["coast_km"] = units.to_crs(METRIC).geometry.distance(coast) / 1000
    # elevation: population-weighted by centre where a unit has several; buffers use the nearest centre's
    ids = units.uc_ids.fillna("").str.split(";")
    units["elevation_m"] = [
        pd.Series([elev.get(int(i)) for i in u if i]).mean() if any(i for i in u) else None
        for u in ids
    ]
    miss = units.elevation_m.isna()
    if miss.any():
        ucs = units[~miss]
        near = gpd.sjoin_nearest(
            units[miss].to_crs(METRIC), ucs[["elevation_m", "geometry"]].to_crs(METRIC), how="left"
        )
        units.loc[miss, "elevation_m"] = near.groupby(level=0).elevation_m_right.first()
    units["region"] = [
        assign(s, e, c, cfg)
        for s, e, c in zip(units.state, units.elevation_m, units.coast_km, strict=True)
    ]
    units[["unit_id", "state", "region", "elevation_m", "coast_km"]].to_csv(
        INTERIM / "unit_regions.csv", index=False
    )
    # stations: the unit holding them, else nearest unit's region
    s = load_stations().dropna(subset=["lat", "lon"])
    sp = gpd.GeoDataFrame(s[["sid"]], geometry=gpd.points_from_xy(s.lon, s.lat), crs=4326).to_crs(
        METRIC
    )
    j = gpd.sjoin_nearest(
        sp, units[["unit_id", "region", "geometry"]].to_crs(METRIC), how="left", distance_col="km"
    )
    j = j.drop_duplicates("sid")
    j["km"] = j.km / 1000
    j[["sid", "unit_id", "region", "km"]].rename(columns={"km": "km_to_unit"}).to_csv(
        INTERIM / "station_regions.csv", index=False
    )
    print(units.region.value_counts().to_dict())


if __name__ == "__main__":
    main()

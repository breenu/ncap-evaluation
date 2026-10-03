"""Station metadata and geography rules. All data SYNTHETIC (project rule: synthetic data only in tests, never in the pipeline)."""

import geopandas as gpd
import pandas as pd
import pytest
from shapely.geometry import box

from src.clean import geo, station_meta
from src.clean.crosscheck import agency


def test_agency_parsing():
    assert agency("Anand Vihar, Delhi - DPCC") == "DPCC"
    assert agency("Womens College, Durgapur - WBPCB (Formerly known as X)") == "WBPCB"
    assert agency("No agency here") == ""


def test_norm():
    assert geo.norm("Asansol & Raniganj") == "asansol and raniganj"
    assert geo.norm("  Hubli-Dharwad ") == "hubli dharwad"


@pytest.fixture
def ucs():
    """SYNTHETIC urban centres in two made-up states."""
    return gpd.GeoDataFrame(
        {
            "uc_id": [1, 2, 3],
            "uc_name": ["Alpha", "Beta", "Alpha"],
            "uc_names": ["Alpha; Alpha East", "Beta; Gamma", "Alpha"],
            "state": ["State A", "State A", "State B"],
            "uc_area_km2": [1.0, 1.0, 1.0],
            "pop_2015": [1e5, 2e5, 3e5],
            "pop_2025": [1e5, 2e5, 3e5],
        },
        geometry=[box(0, 0, 1, 1), box(2, 0, 3, 1), box(5, 5, 6, 6)],
        crs=4326,
    )


def test_name_candidates_are_exact_and_state_bound(ucs):
    assert geo.name_candidates("Alpha", "State A", ucs, {}) == [1]
    assert geo.name_candidates("Gamma", "State A", ucs, {}) == [2]  # listed secondary name
    assert geo.name_candidates("Alph", "State A", ucs, {}) == []  # no fuzzy matching
    assert geo.name_candidates("Delta", "State A", ucs, {"ucdb_name": {"Delta": ["Beta"]}}) == [2]


def test_main_name_beats_listed_name(ucs):
    ucs = ucs.copy()
    ucs.loc[2, ["state", "uc_names"]] = [
        "State A",
        "Alpha Village; Gamma",
    ]  # centre 3 also lists Gamma
    ucs.loc[1, "uc_name"] = "Gamma"  # centre 2's main name is Gamma
    assert geo.name_candidates("Gamma", "State A", ucs, {}) == [2]


def test_match_table_flags_shared_and_disagree(ucs):
    ncap = pd.DataFrame({"city": ["Alpha", "Gamma", "Beta"], "state": ["State A"] * 3})
    stations = gpd.GeoDataFrame(
        {
            "city": ["Alpha", "Gamma"],
            "state": ["State A", "State A"],
            "coord_is_station_level": [True, True],
            "uc_id": [2.0, 2.0],  # Alpha's station sits in centre 2, not its name match (1)
        },
        geometry=gpd.points_from_xy([2.5, 2.5], [0.5, 0.5]),
        crs=4326,
    )
    m = geo.match_table(ncap, ucs, stations, {})
    alpha = m[m.city == "Alpha"].set_index("uc_id")
    assert (alpha.status == "disagree").all()
    # the name match defines the unit; the station's centre is recorded but not part of it
    assert alpha.loc[1, "role"] == "primary" and alpha.loc[2, "role"] == "secondary"
    gamma = m[m.city == "Gamma"].iloc[0]
    assert gamma.method == "name+stations" and gamma.shared_uc  # Beta also names centre 2


def test_station_matching_is_state_bound(ucs):
    ncap = pd.DataFrame({"city": ["Delta"], "state": ["State B"]})
    stations = gpd.GeoDataFrame(
        {"city": ["Delta"], "state": ["State A"], "coord_is_station_level": [True], "uc_id": [2.0]},
        geometry=gpd.points_from_xy([2.5], [0.5]),
        crs=4326,
    )
    m = geo.match_table(ncap, ucs, stations, {})
    assert m.iloc[0].status == "no_uc"  # a same-named city in another state is not evidence


def test_identity_threshold():
    ident = pd.DataFrame(
        {
            "sid": ["a", "a", "b"],
            "location_id": [1, 2, 3],
            "equal": [990, 30, 400],
            "shared": [1000, 1000, 400],
        }
    ).assign(share=lambda d: d.equal / d.shared)
    got = station_meta.identified(ident)
    assert list(got.location_id) == [1]  # 3% is coincidence; 400 slots is too few to call
    dup = pd.DataFrame(
        {"sid": ["a", "b"], "location_id": [9, 9], "equal": [600, 700], "shared": [1000, 1000]}
    )
    dup["share"] = dup.equal / dup.shared
    assert station_meta.identified(dup).empty and len(station_meta.not_unique(dup)) == 2


def test_haversine():
    assert station_meta.haversine_km(28.6, 77.2, 28.6, 77.2) == 0
    assert 110 < station_meta.haversine_km(0, 0, 1, 0) < 112


def test_aqi_pm25_breakpoints():
    from src.clean.crosscheck import aqi_pm25

    assert aqi_pm25(0) == 0 and aqi_pm25(30) == 50 and aqi_pm25(60) == 100
    assert aqi_pm25(75) == 150  # halfway through the 60-90 band -> halfway through 100-200
    assert aqi_pm25(1000) == 500


def test_town_lookup_rules():
    """GeoNames lookup (src/clean/towns.py). SYNTHETIC gazetteer rows."""
    from src.clean import towns

    g = pd.DataFrame(
        {
            "geonameid": [1, 2, 3, 4, 5],
            "name": ["Alpha", "Alpha", "Beta", "Gamma Nagar", "Delta"],
            "fclass": ["P", "P", "P", "A", "P"],
            "fcode": ["PPL", "PPL", "PPL", "ADM3", "PPL"],
            "population": [100, 5000, 0, 900, 0],
            "lat": [1.0, 2.0, 3.0, 4.0, 5.0],
            "lon": [1.0, 2.0, 3.0, 4.0, 5.0],
            "state": ["S", "S", "S", "S", "T"],
        }
    )
    g["names"] = g.name.map(lambda n: {geo.norm(n)})
    cfg = {"name": {"Gamma": ["Gamma Nagar"]}}
    alpha = towns.lookup("Alpha", "S", g, cfg)
    assert alpha["geonameid"] == 2 and not alpha["tie"]  # larger population wins
    assert (
        towns.lookup("Gamma", "S", g, cfg)["method"] == "admin_centroid"
    )  # no P record: A fallback
    assert towns.lookup("Delta", "S", g, cfg)["method"] == "none"  # exists only in another state


def test_region_rule_order():
    from src.clean.regions import assign

    cfg = {"northeast_states": ["Assam"], "igp_states": ["Bihar", "West Bengal"], "igp_max_elevation_m": 350,
           "coastal_max_km": 50}  # fmt: skip
    assert assign("Assam", 50, 10, cfg) == "north-east"
    assert assign("West Bengal", 6, 0, cfg) == "igp"  # IGP wins over coastal (Kolkata)
    assert assign("West Bengal", 1400, 400, cfg) == "peninsular/other"  # hills are not the plain
    assert assign("Kerala", 10, 5, cfg) == "coastal"

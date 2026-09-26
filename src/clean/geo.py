"""Geography: GHSL urban centres (UCDB R2024A) for India, state boundaries, and the NCAP-city <-> UCDB
matching table.

Urban centres
    data/interim/ghsl/ucdb_india.gpkg: India's 1,925 urban centres (EPSG:4326), with population by
    epoch (GH_POP_TOT_1975..2030), area, all listed names, and the state holding the centre's
    centroid (DataMeet boundaries, DEC-018).

Matching table (data/interim/ncap_ucdb_match.csv), one row per NCAP city and urban centre:
    Evidence is collected in two independent ways, and every row records which one it came from.
    name      the city's name (after config/ncap_ucdb_names.yaml) equals one of the names UCDB
              lists for a centre in the same state. Exact after normalisation; no fuzzy matching.
    stations  the city's monitoring stations (mirror City name, config/ncap_ucdb_names.yaml
              `station_city`) that have a station-level coordinate fall inside the centre.
    manual    a centre named in config/ncap_ucdb_names.yaml `ucdb_ids`, with its reason.
    role: 'primary' centres define the city's satellite unit (the name match, else the centre
    holding most of the city's stations); 'secondary' centres hold some of its stations (e.g. an
    industrial town at its edge) but are not part of the unit. Station evidence is state-bound
    (Maharashtra and Bihar both have an Aurangabad).
    status: matched | no_uc | disagree (name and stations point to different centres) | tie.
    shared_uc: a primary centre that is also another NCAP city's primary centre (e.g. Delhi, Noida,
    Ghaziabad, Faridabad in one polygon); such cities form one unit for satellite analysis.

    python -m src.clean.geo
"""

import re
import shutil
import zipfile

import geopandas as gpd
import pandas as pd

from src.common.paths import CONFIG, INTERIM, load_yaml, raw_dir

GHSL_DIR = INTERIM / "ghsl"
UCDB_INDIA = GHSL_DIR / "ucdb_india.gpkg"
MATCH_OUT = INTERIM / "ncap_ucdb_match.csv"
UCDB_GPKG = "GHS_UCDB_GLOBE_R2024A.gpkg"
UCDB_LAYER_GENERAL = "GHSL_UCDB_THEME_GENERAL_CHARACTERISTICS_GLOBE_R2024A"
UCDB_LAYER_GHSL = "GHSL_UCDB_THEME_GHSL_GLOBE_R2024A"
POP_EPOCHS = (2005, 2010, 2015, 2020, 2025)


def norm(s: str) -> str:
    """Name normalisation used for every comparison: lower case, '&' -> 'and', punctuation to
    spaces, collapsed whitespace."""
    s = str(s).lower().replace("&", " and ")
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


# ------------------------------------------------------------------ inputs


def states() -> gpd.GeoDataFrame:
    s = gpd.read_file(raw_dir("boundaries") / "datameet@b3fbbde" / "States" / "Admin2.shp")
    return s.rename(columns={"ST_NM": "state"}).to_crs(4326)


def build_ucdb_india() -> gpd.GeoDataFrame:
    """Extract UCDB from the raw zip (to data/interim, raw untouched) and keep India."""
    GHSL_DIR.mkdir(parents=True, exist_ok=True)
    gpkg = GHSL_DIR / UCDB_GPKG
    if not gpkg.exists():
        with (
            zipfile.ZipFile(raw_dir("ghsl") / "GHS_UCDB_GLOBE_R2024A_V1_2.zip") as z,
            open(gpkg, "wb") as f,
        ):
            shutil.copyfileobj(z.open(UCDB_GPKG), f)
    gen = gpd.read_file(gpkg, layer=UCDB_LAYER_GENERAL, where="GC_CNT_GAD_2025 = 'India'")
    pop_cols = [f"GH_POP_TOT_{y}" for y in POP_EPOCHS]
    ghs = gpd.read_file(
        gpkg, layer=UCDB_LAYER_GHSL, where="GC_CNT_GAD_2025 = 'India'", ignore_geometry=True
    )
    uc = gen.merge(ghs[["ID_UC_G0", *pop_cols]], on="ID_UC_G0", how="left").to_crs(4326)
    uc = uc.rename(
        columns={
            "ID_UC_G0": "uc_id",
            "GC_UCN_MAI_2025": "uc_name",
            "GC_UCN_LIS_2025": "uc_names",
            "GC_UCA_KM2_2025": "uc_area_km2",
            "GC_POP_TOT_2025": "uc_pop_2025",
            **{f"GH_POP_TOT_{y}": f"pop_{y}" for y in POP_EPOCHS},
        }
    )[
        [
            "uc_id",
            "uc_name",
            "uc_names",
            "uc_area_km2",
            "uc_pop_2025",
            *[f"pop_{y}" for y in POP_EPOCHS],
            "geometry",
        ]
    ]
    pts = gpd.GeoDataFrame(uc[["uc_id"]], geometry=uc.geometry.representative_point(), crs=4326)
    sts = states()[["state", "geometry"]]
    st = gpd.sjoin(pts, sts, how="left", predicate="within").drop_duplicates("uc_id")
    # a coastal centre's interior point can fall just outside the drawn coastline: nearest state
    miss = st.state.isna()
    if miss.any():
        near = gpd.sjoin_nearest(
            pts[pts.uc_id.isin(st[miss].uc_id)].to_crs(7755), sts.to_crs(7755), how="left"
        )
        st.loc[miss, "state"] = st.loc[miss, "uc_id"].map(
            near.drop_duplicates("uc_id").set_index("uc_id").state
        )
    uc = uc.merge(st[["uc_id", "state"]], on="uc_id", how="left")
    uc.to_file(UCDB_INDIA, driver="GPKG")
    return uc


def ucdb_india() -> gpd.GeoDataFrame:
    return gpd.read_file(UCDB_INDIA) if UCDB_INDIA.exists() else build_ucdb_india()


def names_config() -> dict:
    return load_yaml(CONFIG / "ncap_ucdb_names.yaml")


# ------------------------------------------------------------------ matching


def name_candidates(city: str, state: str, uc: pd.DataFrame, cfg: dict) -> list[int]:
    """Centres in the city's state that list the city's name (or its configured UCDB names)."""
    wanted = {norm(n) for n in cfg.get("ucdb_name", {}).get(city, [city])}
    st = norm(state)
    main, listed_only = [], []
    for r in uc.itertuples():
        if norm(r.state or "") != st:
            continue
        listed = {norm(n) for n in str(r.uc_names or "").split(";")}
        if norm(r.uc_name) in wanted:
            main.append(int(r.uc_id))
        elif wanted & listed:
            listed_only.append(int(r.uc_id))
    # A centre whose main name is the city's beats one that merely lists it among its settlements
    # (UCDB lists a village "Durgapur" inside a South 24 Parganas centre).
    return main or listed_only


def station_candidates(
    city: str, state: str, stations: gpd.GeoDataFrame, cfg: dict
) -> tuple[dict, int, int]:
    """Centres holding the city's stations (same mirror city name AND same state; two states have an
    Aurangabad). Returns ({centre id: stations inside}, stations used, stations outside every
    centre). Only station-level coordinates are used."""
    mirror_names = {norm(n) for n in cfg.get("station_city", {}).get(city, [city])}
    s = stations[
        stations.city.map(norm).isin(mirror_names)
        & (stations.state.map(norm) == norm(state))
        & stations.coord_is_station_level
    ]
    counts = s.uc_id.dropna().astype(int).value_counts().to_dict()
    return counts, len(s), int(s.uc_id.isna().sum())


def match_table(
    ncap: pd.DataFrame, uc: pd.DataFrame, stations: gpd.GeoDataFrame, cfg: dict
) -> pd.DataFrame:
    """One row per (city, centre). role 'primary' centres define the city's satellite unit: the name
    match(es), else the centre holding most of the city's stations. 'secondary' centres hold some of
    the city's stations (e.g. an industrial town at its edge) but are not part of the unit."""
    manual = cfg.get("ucdb_ids", {})
    rows = []
    for c in ncap.itertuples():
        by_name = name_candidates(c.city, c.state, uc, cfg)
        by_st, n_st, n_out = station_candidates(c.city, c.state, stations, cfg)
        if c.city in manual:
            primary = [int(i) for i in manual[c.city]["ids"]]
            how = {i: "manual" for i in primary}
        elif by_name:
            primary = by_name
            how = {i: "name+stations" if i in by_st else "name" for i in primary}
        elif by_st:
            top = max(by_st.values())
            primary = [i for i, n in by_st.items() if n == top]
            how = {i: "stations" for i in primary}
        else:
            primary, how = [], {}
        status = "matched" if primary else "no_uc"
        if by_name and by_st and not set(by_name) & set(by_st):
            status = "disagree"
        if len(primary) > 1 and not by_name and c.city not in manual:
            status = "tie"
        ids = [(i, "primary", how[i]) for i in sorted(primary)]
        ids += [(i, "secondary", "stations") for i in sorted(by_st) if i not in primary]
        for i, role, method in ids or [(None, "", "")]:
            rows.append(
                {
                    "city": c.city,
                    "state": c.state,
                    "uc_id": i,
                    "role": role,
                    "method": method,
                    "status": status,
                    "stations_in_uc": by_st.get(i, 0) if i is not None else 0,
                    "name_ucs": ";".join(map(str, by_name)),
                    "station_ucs": ";".join(f"{k}:{v}" for k, v in sorted(by_st.items())),
                    "stations_with_coords": n_st,
                    "stations_outside_uc": n_out,
                    "manual_why": manual.get(c.city, {}).get("why", ""),
                }
            )
    m = pd.DataFrame(rows)
    m["uc_id"] = pd.to_numeric(m.uc_id).astype("float64")  # NaN where a city has no centre
    info = uc[["uc_id", "uc_name", "uc_area_km2", "pop_2015", "pop_2025"]].astype(
        {"uc_id": "float64"}
    )
    m = m.merge(info, on="uc_id", how="left")
    prim = m[m.role == "primary"]
    shared = prim.groupby("uc_id").city.nunique()
    m["shared_uc"] = (m.role == "primary") & (m.uc_id.map(shared).fillna(0).astype(int) > 1)
    m["shared_with"] = [
        ";".join(sorted(set(prim[(prim.uc_id == u) & (prim.city != c)].city)))
        if r == "primary"
        else ""
        for u, c, r in zip(m.uc_id, m.city, m.role, strict=True)
    ]
    return m


def stations_in_ucs(stations: pd.DataFrame, uc: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Point-in-polygon: the urban centre (if any) holding each station coordinate."""
    s = stations.dropna(subset=["lat", "lon"])
    g = gpd.GeoDataFrame(s, geometry=gpd.points_from_xy(s.lon, s.lat), crs=4326)
    j = gpd.sjoin(g, uc[["uc_id", "geometry"]], how="left", predicate="within")
    return j.drop(columns="index_right").drop_duplicates("sid")


SPECIAL_UNITS = {
    # DECISIONS entries that define how a listed city maps to geography
    "Bhilai": "DEC-047: Durg-Bhilai twin city, one unit covering both towns",
    "Asansol & Raniganj": "DEC-050: one unit covering both towns",
    "Bhubaneswar": "DEC-048: enrolled city; funding per head for the combined Bhubaneswar & Cuttack row uses the pair's population",
    "Cuttack": "DEC-048: as Bhubaneswar",
    "Angul": "DEC-048: enrolled city; funding per head for the combined Angul & Talcher row uses the pair's population",
    "Talcher": "DEC-048: as Angul",
    "Patancheruvu": "DEC-049: enrolled from its listing date; exclusion sensitivity",
}
LARGE_KM2 = 1000


def _md(df: pd.DataFrame) -> str:
    df = df.astype(
        {c: "Int64" for c in df.columns if c.endswith("_id") or c.startswith("stations")}
    )
    head = "| " + " | ".join(df.columns) + " |\n|" + "---|" * len(df.columns) + "\n"
    return head + "\n".join(
        "| "
        + " | ".join(
            "" if pd.isna(v) else (f"{v:,.0f}" if isinstance(v, float) else str(v)) for v in r
        )
        + " |"
        for r in df.itertuples(index=False)
    )


def write_review(m: pd.DataFrame, uc: pd.DataFrame, path=None) -> None:
    from src.common.paths import DOCS

    path = path or DOCS / "ncap_ucdb_review.md"
    per_city = m.drop_duplicates("city")
    prim = m[m.role == "primary"]
    cols = [
        "city",
        "state",
        "uc_id",
        "uc_name",
        "method",
        "stations_in_uc",
        "pop_2025",
        "uc_area_km2",
    ]
    special = prim[prim.city.isin(SPECIAL_UNITS)][cols].assign(
        rule=lambda d: d.city.map(SPECIAL_UNITS)
    )
    special = pd.concat(
        [
            special,
            m[(m.city.isin(SPECIAL_UNITS)) & (m.status == "no_uc")][["city", "state"]].assign(
                rule=lambda d: d.city.map(SPECIAL_UNITS)
            ),
        ]
    )
    shared = (
        prim[prim.shared_uc]
        .groupby(["uc_id", "uc_name"])
        .city.apply(lambda s: ", ".join(sorted(s)))
        .reset_index()
    )
    large = prim[prim.uc_area_km2 > LARGE_KM2][cols]
    L = [
        "# NCAP city <-> GHSL urban centre matching",
        "",
        "*Generated by `python -m src.clean.geo`. Do not edit by hand. Table: `data/interim/ncap_ucdb_match.csv`; "
        "name mappings and their reasons: `config/ncap_ucdb_names.yaml`.*",
        "",
        f"{len(per_city)} NCAP cities (the J&K state-level funding row is not a city, DEC-051). Status: "
        + ", ".join(f"{k} {v}" for k, v in per_city.status.value_counts().items())
        + ". Primary centres by method: "
        + ", ".join(
            f"{k} {v}" for k, v in prim.drop_duplicates("city").method.value_counts().items()
        )
        + ".",
        "",
        "`primary` centres define a city's satellite unit. `secondary` centres hold some of the city's stations "
        "but are separate settlements (not part of the unit). Station evidence uses only station-level "
        "coordinates (`data/processed/stations.csv`) and must match the city's state.",
        "",
        "## 1. Units defined in DECISIONS",
        "",
        _md(special),
        "",
        "## 2. Centres shared by several NCAP cities (one satellite unit)",
        "",
        _md(shared),
        "",
        "## 3. Secondary centres (a city's stations in a separate settlement)",
        "",
        _md(
            m[m.role == "secondary"][
                ["city", "uc_id", "uc_name", "stations_in_uc", "pop_2025", "uc_area_km2"]
            ]
        ),
        "",
        f"## 4. Very large primary polygons (over {LARGE_KM2:,} km2)",
        "",
        "A city-average satellite value over these polygons mixes the city with a wide belt of dense "
        "peri-urban or rural settlement.",
        "",
        _md(large),
        "",
        "## 5. For Reenu: cities with no urban centre",
        "",
        "These have no UCDB centre (UCDB only includes centres of at least 50,000 people in dense cells) "
        "or a match that could not be made without guessing. For the satellite layer they need a town "
        "geometry (e.g. a buffer around a town coordinate); where the city has a located station, that "
        "station is a candidate anchor.",
        "",
        _md(
            m[m.status == "no_uc"][["city", "state", "stations_with_coords", "stations_outside_uc"]]
        ),
        "",
    ]
    path.write_text("\n".join(L), encoding="utf-8")


def main() -> None:
    from src.clean.station_meta import load_stations  # resolved coordinates

    uc = build_ucdb_india()
    print(f"India urban centres: {len(uc)}; >= 100k in 2020: {(uc.pop_2020 >= 1e5).sum()}")
    st = stations_in_ucs(load_stations(), uc)
    ncap = pd.read_csv(INTERIM / "ncap_cities.csv")
    m = match_table(ncap, uc, st, names_config())
    m.to_csv(MATCH_OUT, index=False)
    write_review(m, uc)
    per_city = m.groupby("city").status.first().value_counts().to_dict()
    print(f"saved {MATCH_OUT}: {per_city}; shared centres: {m[m.shared_uc].city.nunique()} cities")


if __name__ == "__main__":
    main()

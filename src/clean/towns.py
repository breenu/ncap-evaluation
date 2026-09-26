"""Town points from GeoNames and the satellite analysis units.

Town points (data/interim/geonames_towns.csv)
    For NCAP towns with no GHSL urban centre (data/interim/ncap_ucdb_match.csv, status no_uc) and for
    Raniganj (DEC-064). Lookup rules: config/geonames_towns.yaml.

Buffer rule (DEC-063)
    A town point becomes a circle whose area is the median area of India's smallest GHSL urban
    centres (2020 population 50,000-99,999), so buffered towns are sized like the smallest GHSL
    centres they sit beside. The radius is computed from the data, not typed in.

Satellite units (data/interim/sat_units.gpkg), one row per unit:
    - every Indian GHSL urban centre (kind 'uc');
    - NCAP cities sharing a primary centre are one unit (e.g. Delhi, Faridabad, Ghaziabad, Noida);
    - the Asansol & Raniganj unit is the Asansol centre joined with Raniganj's buffered point
      (DEC-064; in the primary estimate);
    - NCAP towns with no centre are buffered points (kind 'town_buffer'), in_primary = False: they
      enter only a sensitivity analysis, because controls are GHSL centres and treated and control
      units must be defined the same way (DEC-063).
    Columns: unit_id, kind, uc_ids, ncap_cities, in_primary, area_km2, pop_2015, pop_2020,
    contains_ncap_town (a centre holding the point of an NCAP town that has no centre), geometry.

    python -m src.clean.towns
"""

import zipfile

import geopandas as gpd
import numpy as np
import pandas as pd

from src.clean.geo import norm, states, ucdb_india
from src.common.paths import CONFIG, INTERIM, load_yaml, raw_dir

TOWNS_OUT = INTERIM / "geonames_towns.csv"
UNITS_OUT = INTERIM / "sat_units.gpkg"
GEONAMES_COLS = [
    "geonameid", "name", "asciiname", "alternatenames", "lat", "lon", "fclass", "fcode", "cc", "cc2",
    "admin1", "admin2", "admin3", "admin4", "population", "elevation", "dem", "tz", "moddate",
]  # fmt: skip
SMALL_UC_POP = (50_000, 100_000)  # the smallest GHSL urban-centre class
EXTRA_TOWNS = {"Raniganj": ("West Bengal", "Asansol & Raniganj")}  # DEC-064: joined to that unit
METRIC = 7755  # India Lambert conformal conic, metres


def load_geonames() -> pd.DataFrame:
    """GeoNames India, with state names and a set of normalised names per record."""
    with zipfile.ZipFile(raw_dir("geonames") / "IN.zip") as z:
        g = pd.read_csv(
            z.open("IN.txt"), sep="\t", header=None, names=GEONAMES_COLS, dtype={"admin1": str},
            quoting=3, keep_default_na=False,
        )  # fmt: skip
    a1 = pd.read_csv(
        raw_dir("geonames") / "admin1CodesASCII.txt",
        sep="\t",
        header=None,
        names=["code", "state", "ascii", "id"],
    )
    a1 = a1[a1.code.str.startswith("IN.")].assign(admin1=lambda d: d.code.str[3:])
    g = g.merge(a1[["admin1", "state"]], on="admin1", how="left")
    g["names"] = [
        {norm(n), norm(a)} | {norm(x) for x in alt.split(",") if x}
        for n, a, alt in zip(g["name"], g.asciiname, g.alternatenames, strict=True)
    ]
    return g


def lookup(town: str, state: str, g: pd.DataFrame, cfg: dict) -> dict:
    """One town -> one GeoNames record, by the rules in config/geonames_towns.yaml."""
    wanted = {norm(n) for n in cfg.get("name", {}).get(town, [town])}
    st = cfg.get("state", {}).get(town, state)
    in_state = g[g.state.map(norm) == norm(st)]
    hit = in_state[in_state.names.map(lambda s: bool(s & wanted))]
    method = "exact" if town not in cfg.get("name", {}) else "alias"
    cand = hit[hit.fclass == "P"]
    if cand.empty:
        cand = hit[hit.fclass == "A"]
        method = "admin_centroid" if len(cand) else "none"
    rec = {"town": town, "state": state, "method": method, "candidates": len(cand), "tie": False}
    if cand.empty:
        return rec
    cand = cand.sort_values(["population", "geonameid"], ascending=[False, True])
    top = cand.iloc[0]
    rec["tie"] = len(cand) > 1 and cand.population.iloc[1] == top.population
    rec.update(
        geonameid=int(top.geonameid), gn_name=top["name"], fcode=top.fcode, population=int(top.population),
        lat=float(top.lat), lon=float(top.lon),
    )  # fmt: skip
    return rec


def buffer_radius_km(uc: pd.DataFrame) -> float:
    lo, hi = SMALL_UC_POP
    area = uc[(uc.pop_2020 >= lo) & (uc.pop_2020 < hi)].uc_area_km2.median()
    return float(np.sqrt(area / np.pi))


def town_points(match: pd.DataFrame, uc: gpd.GeoDataFrame) -> pd.DataFrame:
    g = load_geonames()
    cfg = load_yaml(CONFIG / "geonames_towns.yaml")
    no_uc = match[match.status == "no_uc"].drop_duplicates("city")
    towns = [(r.city, r.state, r.city) for r in no_uc.itertuples()]
    towns += [(t, st, unit) for t, (st, unit) in EXTRA_TOWNS.items()]
    rows = [{**lookup(t, st, g, cfg), "ncap_unit": unit} for t, st, unit in towns]
    t = pd.DataFrame(rows)
    # checks: which state polygon and which urban centre (if any) holds the point
    ok = t.dropna(subset=["lat"])
    pts = gpd.GeoDataFrame(ok[["town"]], geometry=gpd.points_from_xy(ok.lon, ok.lat), crs=4326)
    j = gpd.sjoin(pts, states()[["state", "geometry"]], how="left", predicate="within")
    t["point_state"] = t.town.map(j.drop_duplicates("town").set_index("town").state)
    j = gpd.sjoin(pts, uc[["uc_id", "uc_name", "geometry"]], how="left", predicate="within")
    j = j.drop_duplicates("town").set_index("town")
    t["inside_uc_id"] = t.town.map(j.uc_id)
    t["inside_uc_name"] = t.town.map(j.uc_name)
    return t


def sat_units(
    match: pd.DataFrame, towns: pd.DataFrame, uc: gpd.GeoDataFrame, radius_km: float
) -> gpd.GeoDataFrame:
    prim = match[match.role == "primary"].dropna(subset=["uc_id"])
    # A town joined to a unit (DEC-064) whose point lies inside a GHSL centre joins as that centre's
    # polygon, so the unit stays made of GHSL polygons like every other unit; else as a buffer.
    joined = towns[towns.town.isin(EXTRA_TOWNS) & towns.inside_uc_id.notna()]
    prim = pd.concat(
        [
            prim,
            pd.DataFrame(
                {
                    "city": joined.ncap_unit,
                    "uc_id": joined.inside_uc_id.astype(float),
                    "role": "primary",
                }
            ),
        ],
        ignore_index=True,
    )
    cities_by_uc = prim.groupby(prim.uc_id.astype(int)).city.apply(lambda s: ";".join(sorted(s)))
    units = uc[["uc_id", "uc_area_km2", "pop_2015", "pop_2020", "geometry"]].copy()
    units["ncap_cities"] = units.uc_id.map(cities_by_uc).fillna("")
    # a city with several primary centres (Hubli-Dharwad) is one unit
    multi = prim.groupby("city").uc_id.nunique()
    rows = []
    done = set()
    for city in multi[multi > 1].index:
        ids = sorted(prim[prim.city == city].uc_id.astype(int))
        part = units[units.uc_id.isin(ids)]
        rows.append({"uc_ids": ";".join(map(str, ids)), "ncap_cities": city, "geometry": part.union_all(),
                     "pop_2015": part.pop_2015.sum(), "pop_2020": part.pop_2020.sum(), "kind": "uc"})  # fmt: skip
        done |= set(ids)
    for r in units[~units.uc_id.isin(done)].itertuples():
        rows.append({"uc_ids": str(r.uc_id), "ncap_cities": r.ncap_cities, "geometry": r.geometry,
                     "pop_2015": r.pop_2015, "pop_2020": r.pop_2020, "kind": "uc"})  # fmt: skip
    for r in rows:
        r["in_primary"] = True
    # buffered town points
    t = towns.dropna(subset=["lat"])
    circles = (
        gpd.GeoSeries(gpd.points_from_xy(t.lon, t.lat), crs=4326)
        .to_crs(METRIC)
        .buffer(radius_km * 1000)
        .to_crs(4326)
    )
    for (_, r), circ in zip(t.iterrows(), circles, strict=True):
        if r.town in EXTRA_TOWNS:  # joined to an existing NCAP unit (DEC-064)
            if pd.notna(r.inside_uc_id):
                continue  # joined above as its GHSL polygon
            unit = next(u for u in rows if r.ncap_unit in u["ncap_cities"].split(";"))
            unit["geometry"] = unit["geometry"].union(circ)
            unit["kind"] = "uc+town_buffer"
        else:
            rows.append({"uc_ids": "", "ncap_cities": r.town, "geometry": circ, "pop_2015": np.nan,
                         "pop_2020": np.nan, "kind": "town_buffer", "in_primary": False})  # fmt: skip
    out = gpd.GeoDataFrame(rows, geometry="geometry", crs=4326)
    out["area_km2"] = out.to_crs(METRIC).area / 1e6
    # a GHSL centre holding an NCAP town's point (a town with no centre of its own): not a clean
    # control (analysis plan decides the donor-pool rule)
    inside = towns[~towns.town.isin(EXTRA_TOWNS) & towns.inside_uc_id.notna()]
    contains = inside.groupby(inside.inside_uc_id.astype(int).astype(str)).town.apply(
        lambda s: ";".join(sorted(s))
    )
    out["contains_ncap_town"] = [
        ";".join(contains[i] for i in ids.split(";") if i in contains.index) if ids else ""
        for ids in out.uc_ids
    ]
    out.insert(0, "unit_id", [f"u{i:04d}" for i in range(len(out))])
    return out


def main() -> None:
    uc = ucdb_india()
    match = pd.read_csv(INTERIM / "ncap_ucdb_match.csv")
    towns = town_points(match, uc)
    r = buffer_radius_km(uc)
    towns["buffer_radius_km"] = round(r, 3)
    towns.to_csv(TOWNS_OUT, index=False)
    units = sat_units(match, towns, uc, r)
    units.to_file(UNITS_OUT, driver="GPKG")
    print(towns.drop(columns=["candidates"]).to_string())
    print(f"buffer radius {r:.2f} km; units {len(units)}; primary {units.in_primary.sum()}; "
          f"NCAP units {(units.ncap_cities != '').sum()}")  # fmt: skip


if __name__ == "__main__":
    main()

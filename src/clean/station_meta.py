"""Station metadata: one row per mirror station, with a coordinate and how far to trust it.

The mirror has no coordinates. Phase 2 matched stations to OpenAQ by name (DEC-045): 520 matched,
45 did not, and some matched stations have several OpenAQ ids whose coordinates disagree. This
module settles what the data can settle, marks how each coordinate was obtained, and lists the
rest for Reenu. It never picks between conflicting coordinates without evidence.

Evidence used
  identity   Identical values at identical true-UTC timestamps. Most station-years are
             value-identical in the two feeds (docs/mirror-openaq-crosscheck.md). Different stations
             share <= ~10% of values by coincidence; the same station shares 50-100% (less where a
             feed differs, e.g. IMD stations or 2022). So an OpenAQ location is identified with a
             station if >= 50% of >= 500 shared 15-minute PM2.5 slots are equal AND it passes that bar
             for no other station. The report shows the full distribution of scores.
  overrides  config/station_overrides.yaml: documented corrections to mirror metadata (e.g. a
             wrong state), each with its evidence (column state_corrected).
  plausible  A coordinate is plausible for a station if it lies in the station's state (DataMeet
             boundaries) and within `near_km` of the urban centre that holds the station's city
             (the centre holding the city's other located stations, else its name match).

coord_quality
  station     a plausible coordinate from a data-confirmed OpenAQ location. Candidates within 1 km
              agree (resolved_by 'agree'). Candidates further apart but all in the same urban centre
              (or all outside any centre) are settled by DEC-067 R1: the most recently used one,
              with coord_uncertainty_km = the spread. Candidates in different centres are not
              chosen: decision_needed, with a recommendation, for Reenu.
  station_unconfirmed   as above, from a name match only (no overlapping data to confirm)
  locality    no OpenAQ coordinate at all; the site name matches exactly one GeoNames populated place
              inside the city's centre (DEC-067 R2)
  urban_centre          the city's urban-centre point (approximate: good for city assignment and a
                        0.25 degree ERA5 cell, not for neighbour tests)
  none                  nothing usable
  station, station_unconfirmed and locality count as station-level (coord_is_station_level).

Outputs
  data/processed/stations.csv
  data/interim/station_meta/identity_search.csv, candidates.csv
  docs/station_metadata_review.md (generated): what was settled, how, and what is left for Reenu.

    python -m src.clean.station_meta
"""

import glob
import json
import re
from pathlib import Path

import duckdb
import geopandas as gpd
import numpy as np
import pandas as pd

from src.clean.crosscheck import agency
from src.clean.geo import name_candidates, norm, states, ucdb_india
from src.common.paths import CONFIG, DOCS, INTERIM, PROCESSED, load_yaml, raw_dir

OUT = INTERIM / "station_meta"
STATIONS = PROCESSED / "stations.csv"
MIRROR = (INTERIM / "mirror_15min" / "*" / "*.parquet").as_posix()
OPENAQ = (INTERIM / "openaq_obs" / "*" / "*.parquet").as_posix()

IDENTITY_MIN_SLOTS = 500
IDENTITY_MIN_SHARE = 0.5
AMBIGUOUS_SHARE = 0.1  # between this and IDENTITY_MIN_SHARE: neither coincidence nor identity
AGREE_KM = 1.0  # coordinates this close are the same site
USABLE_KM = 3.0  # coordinates this close: usable, with the spread as stated uncertainty
NEAR_KM = 15.0  # plausible distance from the city's urban centre (edge of polygon)


def haversine_km(lat1, lon1, lat2, lon2):
    lat1, lon1, lat2, lon2 = map(np.radians, (lat1, lon1, lat2, lon2))
    a = (
        np.sin((lat2 - lat1) / 2) ** 2
        + np.cos(lat1) * np.cos(lat2) * np.sin((lon2 - lon1) / 2) ** 2
    )
    return 6371.0 * 2 * np.arcsin(np.sqrt(a))


# ------------------------------------------------------------------ inputs


def openaq_locations() -> pd.DataFrame:
    """Location metadata (API snapshot) plus every coordinate each location has had in the archive."""
    snap = sorted(glob.glob(str(raw_dir("openaq") / "locations_IN_*.json")))[-1]
    meta = pd.DataFrame(
        [
            {
                "location_id": loc["id"],
                "oname": loc["name"],
                "provider": (loc.get("provider") or {}).get("name"),
                "lat": (loc.get("coordinates") or {}).get("latitude"),
                "lon": (loc.get("coordinates") or {}).get("longitude"),
                "first_utc": (loc.get("datetimeFirst") or {}).get("utc"),
                "last_utc": (loc.get("datetimeLast") or {}).get("utc"),
            }
            for loc in json.loads(Path(snap).read_text(encoding="utf-8"))
        ]
    )
    hist = duckdb.sql(
        f"""select location_id, round(lat, 5) as lat, round(lon, 5) as lon,
                   min(ts_utc) as first_seen, max(ts_utc) as last_seen, count(*) as n
            from read_parquet('{OPENAQ}') group by all"""
    ).df()
    return meta, hist


# ------------------------------------------------------------------ identity search


def identity_search(sids: list[str]) -> pd.DataFrame:
    """For each station, every OpenAQ location sharing identical PM2.5 values at identical times.

    share = equal slots / slots where both have a value. Computed for every location that has any
    equal value, so the report can show how far the best non-identical candidate falls short."""
    if not sids:
        return pd.DataFrame(columns=["sid", "location_id", "equal", "shared", "share"])
    con = duckdb.connect()
    con.execute("set TimeZone = 'UTC'")
    con.execute("set memory_limit = '8GB'")
    con.register("s", pd.DataFrame({"sid": sids}))
    con.execute(
        f"""create temp table mm as select sid, ts_utc, round(pm25, 2) as v
            from read_parquet('{MIRROR}') where pm25 is not null and sid in (select sid from s)"""
    )
    con.execute(
        f"""create temp table oo as select location_id, ts_utc, round(avg(value), 2) as v
            from read_parquet('{OPENAQ}') where parameter = 'pm25'
            group by location_id, ts_utc"""
    )
    eq = con.execute(
        """select mm.sid, oo.location_id, count(*) as equal
           from mm join oo on mm.ts_utc = oo.ts_utc and mm.v = oo.v
           group by all having count(*) >= 20"""
    ).df()
    if eq.empty:
        return eq.assign(shared=[], share=[])
    con.register("eq", eq)
    shared = con.execute(
        """select eq.sid, eq.location_id, count(*) as shared
           from eq join mm on mm.sid = eq.sid join oo on oo.location_id = eq.location_id and oo.ts_utc = mm.ts_utc
           group by all"""
    ).df()
    out = eq.merge(shared, on=["sid", "location_id"])
    out["share"] = out.equal / out.shared
    return out.sort_values(["sid", "share"], ascending=[True, False])


def _passing(ident: pd.DataFrame) -> pd.DataFrame:
    ok = ident[(ident.shared >= IDENTITY_MIN_SLOTS) & (ident.share >= IDENTITY_MIN_SHARE)]
    return ok.assign(n_sids=ok.groupby("location_id").sid.transform("nunique"))


def identified(ident: pd.DataFrame) -> pd.DataFrame:
    """Station <-> location identities: enough shared slots, high share, and the location passes
    the bar for exactly one station."""
    ok = _passing(ident)
    return ok[ok.n_sids == 1].drop(columns="n_sids")


def not_unique(ident: pd.DataFrame) -> pd.DataFrame:
    """Locations that pass the bar for more than one station: evidence for none of them."""
    ok = _passing(ident)
    return ok[ok.n_sids > 1].drop(columns="n_sids")


# ------------------------------------------------------------------ plausibility


def city_reference(stations: pd.DataFrame, uc: gpd.GeoDataFrame) -> dict:
    """(state, mirror city) -> urban-centre id, from the city's name-matched stations' coordinates
    where most of them fall, else from a UCDB name match in the same state."""
    pts = stations[stations.match_kind.isin(["exact", "site_city"]) & stations.name_lat.notna()]
    g = gpd.GeoDataFrame(pts, geometry=gpd.points_from_xy(pts.name_lon, pts.name_lat), crs=4326)
    j = gpd.sjoin(g, uc[["uc_id", "geometry"]], how="inner", predicate="within")
    ref = {}
    for (st, city), grp in j.groupby(["state", "city"]):
        ref[(st, city)] = int(grp.uc_id.mode().iloc[0])
    for st, city in stations[["state", "city"]].drop_duplicates().itertuples(index=False):
        if (st, city) not in ref:
            hits = name_candidates(city, st, uc, {})
            if len(hits) == 1:
                ref[(st, city)] = hits[0]
    return ref


def plausibility(lat, lon, state: str, uc_id, uc: gpd.GeoDataFrame, st: gpd.GeoDataFrame) -> dict:
    p = gpd.GeoSeries(gpd.points_from_xy([lon], [lat]), crs=4326)
    in_state = bool(st[st.state.map(norm) == norm(state)].geometry.contains(p.iloc[0]).any())
    dist = np.nan
    if uc_id is not None and not pd.isna(uc_id):
        poly = uc[uc.uc_id == int(uc_id)].to_crs(7755).geometry.iloc[0]  # India LCC, metres
        dist = float(poly.distance(p.to_crs(7755).iloc[0]) / 1000)
    ok = in_state and (np.isnan(dist) or dist <= NEAR_KM)
    return {
        "in_state": in_state,
        "km_from_city_uc": round(dist, 2) if not np.isnan(dist) else np.nan,
        "plausible": ok,
    }


def state_name_map(stations: pd.DataFrame, st: gpd.GeoDataFrame) -> dict:
    """Mirror state names -> DataMeet names (only where they differ after normalisation)."""
    dm = {norm(s): s for s in st.state}
    fix = {"jammu and kashmir": "jammu and kashmir"}
    return {s: dm.get(fix.get(norm(s), norm(s)), s) for s in stations.state.unique()}


# ------------------------------------------------------------------ resolve


def resolve(
    crosswalk: pd.DataFrame,
    meta: pd.DataFrame,
    hist: pd.DataFrame,
    ident: pd.DataFrame,
    uc: gpd.GeoDataFrame,
    st: gpd.GeoDataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    x = crosswalk.rename(columns={"match": "match_kind"}).copy()
    over = overrides().get("state", {})
    x["state_mirror"] = x.state
    x["state"] = [
        over[s]["to"] if s in over else st_ for s, st_ in zip(x.sid, x.state, strict=True)
    ]
    x["name_lat"] = x.lat.where(x.coord_source == "openaq")
    x["name_lon"] = x.lon.where(x.coord_source == "openaq")
    smap = state_name_map(x, st)
    x["state_dm"] = x.state.map(smap)
    ref = city_reference(x.assign(state=x.state_dm), uc)
    confirmed = identified(ident)
    no_cand = x[x.openaq_location_ids.isna() & ~x.sid.isin(confirmed.sid)]
    localities = locality_points(no_cand, ref, uc)

    rows, cands = [], []
    for r in x.itertuples():
        name_ids = (
            [int(i) for i in str(r.openaq_location_ids).split(";")]
            if pd.notna(r.openaq_location_ids)
            else []
        )
        conf_ids = sorted(set(confirmed[confirmed.sid == r.sid].location_id.astype(int)))
        city_uc = ref.get((r.state_dm, r.city))
        # every coordinate any candidate id has had: API snapshot plus archive history
        cand = []
        for lid in sorted(set(name_ids) | set(conf_ids)):
            coords = hist[hist.location_id == lid][["lat", "lon", "first_seen", "last_seen", "n"]]
            m = meta[meta.location_id == lid]
            if coords.empty and len(m) and pd.notna(m.lat.iloc[0]):
                coords = pd.DataFrame(
                    [
                        {
                            "lat": m.lat.iloc[0],
                            "lon": m.lon.iloc[0],
                            "first_seen": None,
                            "last_seen": None,
                            "n": 0,
                        }
                    ]
                )
            for c in coords.itertuples():
                pl = plausibility(c.lat, c.lon, r.state_dm, city_uc, uc, st)
                cand.append(
                    {
                        "sid": r.sid,
                        "location_id": lid,
                        "oname": m.oname.iloc[0] if len(m) else "",
                        "by_name": lid in name_ids,
                        "data_confirmed": lid in conf_ids,
                        "lat": c.lat,
                        "lon": c.lon,
                        "first_seen": c.first_seen,
                        "last_seen": c.last_seen,
                        "rows": c.n,
                        **pl,
                    }
                )
        cand = pd.DataFrame(cand)
        cands.append(cand)
        rec = {
            "sid": r.sid,
            "sname": r.sname,
            "city": r.city,
            "state": r.state,
            "state_mirror": r.state_mirror,
            "agency": agency(r.sname),
            "name_match": r.match_kind,
            "openaq_ids_by_name": ";".join(map(str, name_ids)),
            "openaq_ids_by_data": ";".join(map(str, conf_ids)),
            "city_uc_id": city_uc,
            "lat": np.nan,
            "lon": np.nan,
            "coord_quality": "none",
            "coord_location_id": np.nan,
            "coord_uncertainty_km": np.nan,
            "state_corrected": r.state != r.state_mirror,
            "note": f"state corrected from {r.state_mirror} (config/station_overrides.yaml)"
            if r.state != r.state_mirror
            else "",
        }
        if len(cand):
            cand["cand_uc"] = uc_containing(cand.lat, cand.lon, uc)
        rec.update(resolved_by="", decision_needed=False, recommendation="")
        notes = [rec["note"]] if rec["note"] else []
        good = cand[cand.plausible] if len(cand) else cand
        pool = good[good.data_confirmed] if len(good) and good.data_confirmed.any() else good
        quality = "station" if len(pool) and pool.data_confirmed.any() else "station_unconfirmed"
        if len(pool):
            spread = max(
                haversine_km(a.lat, a.lon, b.lat, b.lon)
                for a in pool.itertuples()
                for b in pool.itertuples()
            )
            # DEC-045's rule: the coordinate in use most recently
            best = pool.sort_values(
                ["last_seen", "rows"], ascending=False, na_position="last"
            ).iloc[0]
            same_uc = pool.cand_uc.nunique(dropna=False) == 1
            if spread <= AGREE_KM:
                rule = "agree"
            elif same_uc:
                # DEC-067 R1: the candidates disagree but all lie in the same urban centre (or all
                # outside any centre), so the choice cannot move the station to another city.
                rule = "R1_same_centre"
                notes.append(
                    f"{len(pool)} coordinates up to {spread:.1f} km apart, all in "
                    f"{_uc_label(best.cand_uc)}; most recent used"
                )
            else:
                rule = "decision"
            if rule != "decision":
                rec.update(
                    lat=best.lat,
                    lon=best.lon,
                    coord_quality=quality,
                    coord_location_id=best.location_id,
                    coord_uncertainty_km=round(spread, 2),
                    resolved_by=rule,
                )
                aside = good[~good.location_id.isin(pool.location_id)]
                far = [
                    a
                    for a in aside.itertuples()
                    if haversine_km(a.lat, a.lon, best.lat, best.lon) > AGREE_KM
                ]
                if far:
                    notes.append(
                        "unconfirmed id(s) not used: "
                        + "; ".join(
                            f"id {a.location_id} at {haversine_km(a.lat, a.lon, best.lat, best.lon):.1f} km"
                            for a in far
                        )
                    )
                dropped = cand[~cand.plausible]
                if len(dropped):
                    notes.append(
                        "implausible coordinate(s) ignored: "
                        + "; ".join(
                            f"id {d.location_id} ({d.lat:.4f}, {d.lon:.4f}; in_state={d.in_state}, "
                            f"{d.km_from_city_uc} km from city centre)"
                            for d in dropped.itertuples()
                        )
                    )
            else:
                rec.update(
                    decision_needed=True,
                    recommendation=f"id {best.location_id} ({best.lat:.5f}, {best.lon:.5f}), in "
                    f"{_uc_label(best.cand_uc)}: the most recently used data-confirmed coordinate",
                )
                notes.append(
                    f"{len(pool)} coordinates up to {spread:.1f} km apart in different centres: "
                    + ", ".join(sorted({_uc_label(u) for u in pool.cand_uc}))
                )
        elif len(cand):
            # every candidate is outside the state or far from the city: any choice relocates it
            conf = cand[cand.data_confirmed]
            best = (
                (conf if len(conf) else cand)
                .sort_values("last_seen", ascending=False, na_position="last")
                .iloc[0]
            )
            where = (
                f"is {best.km_from_city_uc} km from the city's centre"
                if pd.notna(best.km_from_city_uc)
                else "cannot be checked against a city centre (the city has none)"
            )
            rec.update(
                decision_needed=True,
                recommendation=f"keep the approximate city point; the best candidate, id {best.location_id} "
                f"({best.lat:.5f}, {best.lon:.5f}, in {_uc_label(best.cand_uc)}, in_state={best.in_state}), {where}",
            )
            notes.append(
                "every candidate coordinate is implausible (wrong state or far from the city)"
            )
        if rec["coord_quality"] == "none" and not rec["decision_needed"] and not len(cand):
            loc = localities.get(r.sid)
            if loc is not None:
                rec.update(
                    lat=loc["lat"],
                    lon=loc["lon"],
                    coord_quality="locality",
                    resolved_by="R2_locality",
                )
                notes.append(
                    f"GeoNames locality '{loc['name']}' (geonameid {loc['geonameid']}) inside the city's centre"
                )
        if rec["coord_quality"] == "none":
            if city_uc is not None:
                p = uc[uc.uc_id == city_uc].geometry.iloc[0].representative_point()
                rec.update(lat=p.y, lon=p.x, coord_quality="urban_centre")
                notes.append(f"approximate: urban centre {city_uc}")
            else:
                notes.append("no urban centre found for the city")
        rec["note"] = "; ".join(notes)
        rows.append(rec)
    out = pd.DataFrame(rows)
    out["coord_is_station_level"] = out.coord_quality.isin(STATION_LEVEL)
    return out, pd.concat(cands, ignore_index=True)


STATION_LEVEL = ("station", "station_unconfirmed", "locality")


def _uc_label(u) -> str:
    return "no urban centre" if pd.isna(u) else f"centre {int(u)}"


def uc_containing(lat: pd.Series, lon: pd.Series, uc: gpd.GeoDataFrame) -> list:
    pts = gpd.GeoDataFrame(geometry=gpd.points_from_xy(lon, lat), crs=4326)
    j = gpd.sjoin(pts, uc[["uc_id", "geometry"]], how="left", predicate="within")
    return j[~j.index.duplicated()].uc_id.tolist()


LOCALITY_DROP = (
    r"\b(sector|phase|near|opp|opposite|office|campus|station|ground|school|college|hospital)\b"
)


def locality_points(stations: pd.DataFrame, ref: dict, uc: gpd.GeoDataFrame) -> dict:
    """DEC-067 R2, for stations with no OpenAQ coordinate at all: the station's site name (before the
    comma) equals exactly one GeoNames populated place (normalised name, same state) lying inside the
    city's urban centre. Names that describe a building rather than a place are not tried."""
    from src.clean.towns import load_geonames

    g = load_geonames()
    g = g[g.fclass == "P"]
    out = {}
    for r in stations.itertuples():
        site = norm(str(r.sname).split(",")[0])
        city_uc = ref.get((r.state_dm, r.city))
        if not site or city_uc is None or re.search(LOCALITY_DROP, site):
            continue
        hit = g[
            (g.state.map(norm) == norm(r.state_dm)) & g.names.map(lambda s, site=site: site in s)
        ]
        if hit.empty:
            continue
        hit = hit.assign(u=uc_containing(hit.lat, hit.lon, uc))
        hit = hit[hit.u == city_uc]
        if len(hit) == 1:
            h = hit.iloc[0]
            out[r.sid] = {
                "lat": float(h.lat),
                "lon": float(h.lon),
                "name": h["name"],
                "geonameid": int(h.geonameid),
            }
    return out


def overrides() -> dict:
    return load_yaml(CONFIG / "station_overrides.yaml")


def load_stations() -> pd.DataFrame:
    s = pd.read_csv(STATIONS)
    s["coord_is_station_level"] = s.coord_is_station_level.astype(bool)
    return s


# ------------------------------------------------------------------ report


def write_report(
    s: pd.DataFrame,
    cand: pd.DataFrame,
    ident: pd.DataFrame,
    crosswalk: pd.DataFrame,
    path: Path = DOCS / "station_metadata_review.md",
) -> None:
    q = s.coord_quality.value_counts()
    was_unmatched = set(crosswalk[crosswalk.match == "unmatched"].sid)
    newly = s[s.sid.isin(was_unmatched) & s.coord_is_station_level]
    conflicted = set(crosswalk[crosswalk.coord_spread_km > AGREE_KM].sid)
    dec = s[s.decision_needed]
    scored = ident[ident.shared >= IDENTITY_MIN_SLOTS]
    bands = [0, 0.01, 0.05, AMBIGUOUS_SHARE, 0.2, IDENTITY_MIN_SHARE, 0.8, 0.95, 1.0]
    dist = (
        scored.assign(band=pd.cut(scored.share, bands, include_lowest=True).astype(str))
        .groupby("band", sort=False)
        .size()
        .reindex(
            pd.cut(pd.Series(bands[1:]), bands, include_lowest=True).astype(str).unique(),
            fill_value=0,
        )
        .rename("station_location_pairs")
        .reset_index()
    )
    ambiguous = scored[(scored.share >= AMBIGUOUS_SHARE) & (scored.share < IDENTITY_MIN_SHARE)]
    nu = not_unique(ident)
    over = overrides().get("state", {})

    def tbl(df):
        head = "| " + " | ".join(df.columns) + " |\n|" + "---|" * len(df.columns) + "\n"
        return head + "\n".join(
            "| " + " | ".join("" if pd.isna(v) else str(v) for v in r) + " |"
            for r in df.itertuples(index=False)
        )

    L = [
        "# Station metadata review",
        "",
        "*Generated by `python -m src.clean.station_meta`. Do not edit by hand.*",
        "",
        f"{len(s)} mirror stations. Coordinate quality: "
        + ", ".join(f"{k} {v}" for k, v in q.items())
        + f". Station-level (used for neighbour tests and station maps): {', '.join(STATION_LEVEL)}.",
        "",
        "## 1. Stations found by their data",
        "",
        "Every mirror station was compared with every OpenAQ location: the share of shared 15-minute "
        f"PM2.5 slots (at least {IDENTITY_MIN_SLOTS}) whose values are equal. Scores mostly fall in two groups. "
        f"Different stations share at most ~{AMBIGUOUS_SHARE:.0%} of values by coincidence; the same station shares "
        f"{IDENTITY_MIN_SHARE:.0%}-100% (below 100% where a feed differs, e.g. IMD stations and 2022). "
        f"Identity rule: share >= {IDENTITY_MIN_SHARE:.0%}, and the location passes it for no other station.",
        "",
        tbl(dist),
        "",
        f"Of the {len(was_unmatched)} stations the name crosswalk could not match, {len(newly)} were identified "
        "this way and now have station coordinates:",
        "",
        tbl(newly[["sid", "sname", "openaq_ids_by_data", "lat", "lon", "coord_quality"]].round(5))
        if len(newly)
        else "(none)",
        "",
        f"**Scores between {AMBIGUOUS_SHARE:.0%} and {IDENTITY_MIN_SHARE:.0%}** (not used as identity evidence). "
        "Two kinds. `own_name_id` = True: the station's own name-matched OpenAQ id, where the two feeds "
        "differ value-for-value but agree on daily means (IMD-operated stations; "
        "docs/mirror-openaq-crosscheck.md section 3). `own_name_id` = False: an id registered to a "
        "*different* station that carried this station's data for part of its life (e.g. two stations' "
        "ids swapped for a period).",
        "",
        tbl(
            ambiguous.merge(s[["sid", "sname", "openaq_ids_by_name"]], on="sid")
            .assign(
                own_name_id=lambda d: [
                    str(loc) in str(o).split(";")
                    for loc, o in zip(d.location_id, d.openaq_ids_by_name, strict=True)
                ]
            )[["sid", "sname", "location_id", "own_name_id", "equal", "shared", "share"]]
            .sort_values(["own_name_id", "sid"])
            .round(3)
        )
        if len(ambiguous)
        else "(none)",
        "",
        "**Locations matching more than one station** (evidence for none of them; the two mirror stations "
        "may carry the same instrument's data for part of the period, checked in the audit):",
        "",
        tbl(
            nu.merge(s[["sid", "sname"]], on="sid")[["sid", "sname", "location_id", "share"]].round(
                3
            )
        )
        if len(nu)
        else "(none)",
        "",
        "## 1b. Corrections to mirror metadata (config/station_overrides.yaml)",
        "",
        tbl(
            pd.DataFrame(
                [
                    {"sid": k, "field": "state", "to": v["to"], "why": v["why"]}
                    for k, v in over.items()
                ]
            )
        )
        if over
        else "(none)",
        "",
        "## 2. How each coordinate was settled (DEC-059, DEC-067)",
        "",
        "Rules, in order: `agree` = the station's plausible, data-confirmed coordinates agree within "
        f"{AGREE_KM:g} km. `R1_same_centre` = they disagree, but all lie in the same urban centre (or all "
        "outside any centre), so the choice cannot move the station to another city; the most recently "
        "used one is taken and `coord_uncertainty_km` is the spread. `R2_locality` = no OpenAQ coordinate "
        "exists; the site name matches exactly one GeoNames populated place inside the city's centre. "
        "Otherwise the city's urban-centre point is used, marked `urban_centre` (approximate, kept out of "
        "neighbour tests).",
        "",
        tbl(
            s.groupby(["coord_quality", "resolved_by"], dropna=False)
            .size()
            .rename("stations")
            .reset_index()
        ),
        "",
        f"Stations whose OpenAQ ids were more than {AGREE_KM:g} km apart in Phase 2 (DEC-045), and their outcome:",
        "",
        tbl(
            s[s.sid.isin(conflicted)][
                ["sid", "sname", "coord_quality", "resolved_by", "coord_uncertainty_km", "note"]
            ]
        ),
        "",
        "Resolved by locality (R2):",
        "",
        tbl(s[s.resolved_by == "R2_locality"][["sid", "sname", "lat", "lon", "note"]].round(5))
        if (s.resolved_by == "R2_locality").any()
        else "(none)",
        "",
        "Still approximate (no OpenAQ coordinate and no unique locality): usable for city assignment and an "
        "ERA5 cell, excluded from neighbour tests.",
        "",
        tbl(s[(s.coord_quality == "urban_centre") & ~s.decision_needed][["sid", "sname", "city"]]),
        "",
        "## 3. For Reenu: stations where the choice would put the station in a different city or centre",
        "",
        f"{len(dec)} stations. Until decided, each keeps its city's approximate point and is kept out of "
        "neighbour tests.",
        "",
        tbl(dec[["sid", "sname", "coord_quality", "recommendation", "note"]])
        if len(dec)
        else "(none)",
        "",
        "Their candidate coordinates (first_seen/last_seen: when OpenAQ's archive used that coordinate, UTC):",
        "",
        tbl(
            cand[cand.sid.isin(dec.sid)][
                [
                    "sid",
                    "location_id",
                    "data_confirmed",
                    "plausible",
                    "lat",
                    "lon",
                    "cand_uc",
                    "first_seen",
                    "last_seen",
                    "rows",
                ]
            ].assign(
                first_seen=lambda d: pd.to_datetime(d.first_seen).dt.date,
                last_seen=lambda d: pd.to_datetime(d.last_seen).dt.date,
            )
        )
        if len(dec)
        else "(none)",
        "",
        "## 4. Candidate coordinates behind each decision",
        "",
        "Full table: `data/interim/station_meta/candidates.csv` (one row per station, OpenAQ id and "
        "coordinate that id has had; `data_confirmed` = identical values; `plausible` = in state and near the city).",
        "",
    ]
    path.write_text("\n".join(L), encoding="utf-8")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    PROCESSED.mkdir(parents=True, exist_ok=True)
    crosswalk = pd.read_csv(INTERIM / "station_crosswalk.csv")
    meta, hist = openaq_locations()
    # search every station: confirms name matches too, and finds renamed or unmatched ones
    ident = identity_search(sorted(crosswalk.sid))
    ident.to_csv(OUT / "identity_search.csv", index=False)
    uc, st = ucdb_india(), states()
    s, cand = resolve(crosswalk, meta, hist, ident, uc, st)
    s.to_csv(STATIONS, index=False)
    cand.to_csv(OUT / "candidates.csv", index=False)
    write_report(s, cand, ident, crosswalk)
    print(
        s.coord_quality.value_counts().to_dict(),
        s.resolved_by.value_counts().to_dict(),
        "decisions:",
        int(s.decision_needed.sum()),
    )


if __name__ == "__main__":
    main()

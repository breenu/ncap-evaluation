"""Station crosswalk: CPCB mirror stations <-> OpenAQ locations, with coordinates.

The mirror (DEC-037) has CPCB site ids and names but no coordinates. OpenAQ lists the
same CPCB stations, with coordinates, under one or more location ids. Stations are matched
by name only, in two passes, and every match records how it was made:

  exact       normalised full name ("site, city - agency") equal
  site_city   normalised site and city equal, agency ignored

No fuzzy matching. Where one station has several OpenAQ ids with different coordinates, the
most recently active id's coordinates are used and the spread is recorded for the Phase 3
metadata audit. Stations left unmatched get their city's mean matched coordinate
(`city_centroid`), used only to pick an ERA5 0.25 degree cell, never as a station location.
Matches are confirmed later by the data themselves (the timezone check compares values).

Output: data/interim/station_crosswalk.csv

    python -m src.acquire.stations
"""

import glob
import json
import re
from pathlib import Path

import duckdb
import pandas as pd

from src.common.paths import INTERIM, raw_dir

ERA5_GRID = 0.25


def mirror_stations(mirror_dir: Path | None = None) -> pd.DataFrame:
    mirror_dir = mirror_dir or raw_dir("cpcb_mirror")
    return (
        duckdb.connect()
        .execute(
            f"""select "Station ID" as sid, any_value("Station Name") as sname,
                   any_value(City) as city, any_value(State) as state
            from read_parquet('{mirror_dir.as_posix()}/*.parquet') group by 1 order by 1"""
        )
        .df()
    )


def openaq_locations(openaq_dir: Path | None = None) -> pd.DataFrame:
    openaq_dir = openaq_dir or raw_dir("openaq")
    snap = sorted(glob.glob(str(openaq_dir / "locations_IN_*.json")))[-1]
    rows = []
    for loc in json.loads(Path(snap).read_text(encoding="utf-8")):
        c = loc.get("coordinates") or {}
        rows.append(
            {
                "location_id": loc["id"],
                "oname": loc["name"],
                "provider": (loc.get("provider") or {}).get("name"),
                "lat": c.get("latitude"),
                "lon": c.get("longitude"),
                "is_monitor": loc.get("isMonitor"),
                "last_utc": (loc.get("datetimeLast") or {}).get("utc") or "",
            }
        )
    return pd.DataFrame(rows)


def _clean(s: str) -> str:
    s = s.lower().replace("&", " and ")
    s = re.sub(r"\bnew delhi\b", "delhi", s)
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


def split_name(name: str) -> tuple[str, str, str]:
    """'Anand Vihar, New Delhi - DPCC' -> ('anand vihar', 'delhi', 'dpcc')."""
    agency = ""
    m = re.match(r"^(.*?)\s+-\s+([^,]+)$", name.strip())
    if m:
        name, agency = m.group(1), m.group(2)
    site, _, city = name.rpartition(",")
    if not site:
        site, city = city, ""
    return _clean(site), _clean(city), _clean(agency)


def snap_to_grid(x: float, step: float = ERA5_GRID) -> float:
    return round(round(x / step) * step, 4)


def build(mirror: pd.DataFrame, oaq: pd.DataFrame) -> pd.DataFrame:
    oaq = oaq[oaq.is_monitor.fillna(False) & oaq.lat.notna()].copy()
    oaq["full"] = oaq.oname.map(lambda n: " | ".join(split_name(n)))
    oaq["sc"] = oaq.oname.map(lambda n: " | ".join(split_name(n)[:2]))
    by_full = oaq.groupby("full")
    by_sc = oaq.groupby("sc")
    out = []
    for r in mirror.itertuples():
        site, city, agency = split_name(r.sname)
        hit, how = None, ""
        if f"{site} | {city} | {agency}" in by_full.groups:
            hit, how = by_full.get_group(f"{site} | {city} | {agency}"), "exact"
        elif city and f"{site} | {city}" in by_sc.groups:
            hit, how = by_sc.get_group(f"{site} | {city}"), "site_city"
        rec = {
            "sid": r.sid,
            "sname": r.sname,
            "city": r.city,
            "state": r.state,
            "match": how or "unmatched",
            "openaq_location_ids": "",
            "lat": None,
            "lon": None,
            "coord_location_id": None,
            "coord_spread_km": None,
        }
        if hit is not None:
            rec["openaq_location_ids"] = ";".join(str(i) for i in sorted(hit.location_id))
            # Several OpenAQ ids for one station can disagree on coordinates (up to ~30 km).
            # Use the most recently active registration, not an average of conflicting points.
            newest = hit.sort_values(["last_utc", "location_id"]).iloc[-1]
            rec["lat"], rec["lon"], rec["coord_location_id"] = (
                newest.lat,
                newest.lon,
                newest.location_id,
            )
            # several OpenAQ ids for one station: how far apart are their coordinates?
            rec["coord_spread_km"] = round(
                111 * max(hit.lat.max() - hit.lat.min(), hit.lon.max() - hit.lon.min()), 3
            )
        out.append(rec)
    x = pd.DataFrame(out)
    cent = x[x.lat.notna()].groupby(["state", "city"])[["lat", "lon"]].mean()
    x["coord_source"] = x.lat.notna().map({True: "openaq", False: ""})
    for i, r in x[x.lat.isna()].iterrows():
        if (r.state, r.city) in cent.index:
            x.loc[i, ["lat", "lon"]] = cent.loc[(r.state, r.city)].values
            x.loc[i, "coord_source"] = "city_centroid"
    x["era5_lat"] = x.lat.map(lambda v: snap_to_grid(v) if pd.notna(v) else None)
    x["era5_lon"] = x.lon.map(lambda v: snap_to_grid(v) if pd.notna(v) else None)
    return x


def main() -> None:
    x = build(mirror_stations(), openaq_locations())
    path = INTERIM / "station_crosswalk.csv"
    x.to_csv(path, index=False)
    print(x.match.value_counts().to_dict(), x.coord_source.value_counts().to_dict())
    print(
        f"unique ERA5 cells: {x.dropna(subset=['era5_lat'])[['era5_lat', 'era5_lon']].drop_duplicates().shape[0]}"
    )
    print(f"saved {path}")


if __name__ == "__main__":
    main()

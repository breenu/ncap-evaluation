"""Turn the step 0 probe JSONs (data/interim/probe/) into docs/data-probe.md.

Every number in the report is computed here from the probe outputs.
The coverage logic is kept in pure functions so it can be unit-tested.
"""

import json
import math
from collections import defaultdict
from pathlib import Path

import pandas as pd

from src.common.paths import params

SITE_RADIUS_KM = 0.5  # locations closer than this are treated as one physical site (probe only)
GOOD_MONTH_PCT = 75.0  # a month with >= 75% of days observed (informational; not the audit rule)


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * 6371.0 * math.asin(math.sqrt(a))


def cluster_sites(
    coords: dict[int, tuple[float, float]], radius_km: float = SITE_RADIUS_KM
) -> dict[int, int]:
    """Single-linkage clustering: location_id -> site_id (the smallest location_id in its cluster).

    OpenAQ lists one physical CPCB station under several location ids (different providers,
    re-registrations), so counting location-months overstates the network."""
    parent = {k: k for k in coords}

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    ids = sorted(coords)
    for i, a in enumerate(ids):
        for b in ids[i + 1 :]:
            (la, lo), (lb, lob) = coords[a], coords[b]
            if abs(la - lb) > 0.01 or abs(lo - lob) > 0.01:  # cheap pre-filter (~1 km)
                continue
            if haversine_km(la, lo, lb, lob) < radius_km:
                ra, rb = find(a), find(b)
                parent[max(ra, rb)] = min(ra, rb)
    return {k: find(k) for k in ids}


def unit_months(months: pd.DataFrame, unit: str) -> pd.DataFrame:
    """One row per (unit, parameter, month) with any observed hour; pct = best coverage across
    the unit's sensors that month. unit is 'location_id' or 'site_id'."""
    m = months[months["observed_days"].fillna(0) > 0]
    return m.groupby([unit, "parameter", "month"], as_index=False)["pct"].max()


def coverage_by_year(um: pd.DataFrame, unit: str, good_pct: float = GOOD_MONTH_PCT) -> pd.DataFrame:
    """Per year: unit-months with PM2.5, PM10 and both; the same for well-covered months;
    and the number of distinct units."""
    um = um.assign(year=um["month"].str[:4].astype(int))
    wide = um.pivot_table(
        index=[unit, "year", "month"], columns="parameter", values="pct", aggfunc="max"
    )
    wide = wide.reindex(columns=["pm25", "pm10"])
    has25, has10 = wide["pm25"].notna(), wide["pm10"].notna()
    good25, good10 = wide["pm25"].fillna(0) >= good_pct, wide["pm10"].fillna(0) >= good_pct
    flags = pd.DataFrame(
        {
            "pm25": has25,
            "pm10": has10,
            "both": has25 & has10,
            "pm25_good": good25,
            "pm10_good": good10,
            "both_good": good25 & good10,
        }
    ).reset_index()
    out = flags.groupby("year")[
        ["pm25", "pm10", "both", "pm25_good", "pm10_good", "both_good"]
    ].sum()
    out["units_pm25"] = flags[flags["pm25"]].groupby("year")[unit].nunique()
    out["units_pm10"] = flags[flags["pm10"]].groupby("year")[unit].nunique()
    return out.fillna(0).astype(int)


def _gb(b: float) -> str:
    return f"{b / 1e9:.2f} GB"


def _md(df: pd.DataFrame) -> str:
    cols = [str(df.index.name or "")] + [str(c) for c in df.columns]
    lines = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    for idx, row in df.iterrows():
        lines.append(
            "| "
            + " | ".join([str(idx)] + [f"{v:,}" if isinstance(v, int) else str(v) for v in row])
            + " |"
        )
    return "\n".join(lines)


def _load(probe: Path, name: str) -> dict | None:
    p = probe / f"{name}.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def openaq_section(o: dict) -> list[str]:
    sensors = pd.DataFrame(o["sensors"])
    months = pd.DataFrame(o["months"])
    lo, hi = (d[:7] for d in o["window"])
    months = months[(months["month"] >= lo) & (months["month"] <= hi)]

    ref = sensors[sensors["is_monitor"].fillna(False) & ~sensors["is_mobile"].fillna(False)]
    pm_ref = ref[ref["parameter"].isin(["pm25", "pm10"])]
    coords = pm_ref.drop_duplicates("location_id").set_index("location_id")[["lat", "lon"]]
    site_of = cluster_sites({int(k): (r.lat, r.lon) for k, r in coords.iterrows()})
    months["site_id"] = months["location_id"].map(site_of)

    loc_um = unit_months(months, "location_id")
    site_um = unit_months(months, "site_id")
    loc_cov = coverage_by_year(loc_um, "location_id")
    site_cov = coverage_by_year(site_um, "site_id")

    n_pm_locs = pm_ref["location_id"].nunique()
    n_with_data = loc_um["location_id"].nunique()
    n_sites = len(set(site_of.values()))
    n_sites_data = site_um["site_id"].nunique()
    low_cost = sensors[
        ~sensors["is_monitor"].fillna(False) & sensors["parameter"].isin(["pm25", "pm10"])
    ]

    prov = (
        loc_um[loc_um["parameter"] == "pm25"]
        .merge(pm_ref.drop_duplicates("location_id")[["location_id", "provider"]], on="location_id")
        .assign(year=lambda d: d["month"].str[:4].astype(int))
        .pivot_table(
            index="year", columns="provider", values="month", aggfunc="count", fill_value=0
        )
    )
    prov.columns.name = None

    # S3 archive: location-months with at least one daily file
    s3 = o["s3"]
    s3_months = defaultdict(int)
    for ms in s3["location_months"].values():
        for m in ms:
            s3_months[int(m[:4])] += 1
    s3_tab = pd.DataFrame({"S3 location-months (any file)": pd.Series(s3_months)}).sort_index()
    s3_tab.index.name = "year"
    both = (
        loc_cov[["pm25"]]
        .rename(columns={"pm25": "API location-months PM2.5"})
        .join(s3_tab, how="outer")
    )
    both = both.fillna(0).astype(int)

    return [
        "## OpenAQ (ground stations)",
        "",
        f"Retrieved {o['retrieved_utc']} ({o['api_calls']:,} API calls). "
        f"Window {o['window'][0]} to {o['window'][1]}.",
        "",
        f"- Indian locations in OpenAQ: **{o['n_locations_IN']:,}**.",
        "- Reference-monitor (non-mobile) locations with a PM2.5 or PM10 sensor: "
        f"**{n_pm_locs:,}**; "
        f"with at least one day of PM data in the window: **{n_with_data:,}**.",
        f"- After merging locations within {SITE_RADIUS_KM} km into one site: "
        f"**{n_sites:,}** sites, "
        f"**{n_sites_data:,}** with data in the window.",
        "- Low-cost (non-monitor) PM sensors excluded: "
        f"{low_cost['sensor_id'].nunique():,} sensors at "
        f"{low_cost['location_id'].nunique():,} locations.",
        "",
        "Coverage comes from OpenAQ's daily rollup (`/sensors/{id}/days/monthly`). "
        "Months are local (IST) "
        "calendar months. A unit-month counts if any day has data; "
        f"'good' = at least {GOOD_MONTH_PCT:.0f}% of days have data "
        "(informational only; the audit's "
        "completeness rules come in Phase 3). Where a unit has several sensors for one pollutant, "
        "the best-covered sensor that month is used.",
        "",
        "### Site-months (de-duplicated, the number that matters)",
        "",
        _md(site_cov.rename(columns={"units_pm25": "sites PM2.5", "units_pm10": "sites PM10"})),
        "",
        "### Location-months (as listed by OpenAQ, before de-duplication)",
        "",
        _md(
            loc_cov.rename(
                columns={"units_pm25": "locations PM2.5", "units_pm10": "locations PM10"}
            )
        ),
        "",
        "### PM2.5 location-months by provider",
        "",
        _md(prov),
        "",
        "### S3 archive vs API",
        "",
        f"Archive files for these {s3['locations']:,} locations: "
        f"{s3['files_in_window']:,} daily files, "
        f"**{_gb(s3['bytes_in_window'])}** compressed in the window "
        f"({s3['files_all_years']:,} files, {_gb(s3['bytes_all_years'])} across all years). "
        "Each file holds every parameter for one location-day, so this is the exact download size.",
        "",
        _md(both),
        "",
    ]


def cpcb_mirror_section(c: dict) -> list[str]:
    ok = [y for y in c["years"] if "error" not in y]
    bad = [y for y in c["years"] if "error" in y]
    rows = []
    for y in ok:
        slots = (366 if y["year"] % 4 == 0 else 365) * 96
        rows.append(
            {
                "year": y["year"],
                "stations listed": y["stations"],
                "15-min rows": y["rows"],
                "PM2.5 null share": f"{y['pm25_null_share']:.0%}",
                "PM10 null share": f"{y['pm10_null_share']:.0%}",
                "PM2.5 station-year equiv.": round(y["rows"] * (1 - y["pm25_null_share"]) / slots),
                "PM10 station-year equiv.": round(y["rows"] * (1 - y["pm10_null_share"]) / slots),
                "file size": _gb(y["bytes"]),
            }
        )
    tab = pd.DataFrame(rows).set_index("year")
    total = sum(y["bytes"] for y in ok)
    read = sum(y["bytes_read"] for y in ok)
    return [
        "## CPCB data repository (via third-party mirror)",
        "",
        f"Checked {c['checked_utc']}. CPCB's own repository endpoints "
        "(`airquality.cpcb.gov.in/dataRepository/...`) return HTTP 404; the CCR web app is now an "
        "obfuscated bundle. The mirror `github.com/Vonter/india-cpcb-aqi` (ODbL 1.0) "
        "publishes yearly Parquet files of CPCB's 15-minute station data scraped from those "
        "endpoints (releases dated "
        f"2026-01-07). Only footers and the station-id column were read ({read / 1e6:.1f} MB).",
        "",
        "Files are padded: every listed station has a row for every 15-minute slot, "
        "including slots "
        "with no measurement. So 'stations listed' overstates the network; the station-year "
        "equivalents (non-null PM rows / slots in the year) are the meaningful measure.",
        "",
        _md(tab),
        "",
        f"Total for {ok[0]['year']}–{ok[-1]['year']}: **{_gb(total)}** (Parquet)."
        + (f" Not available: {', '.join(str(y['year']) for y in bad)}." if bad else ""),
        "",
    ]


def acag_section(a: dict) -> list[str]:
    rows = pd.DataFrame(a["products"]).set_index("label")
    rows.index.name = "product"
    tab = pd.DataFrame(
        {
            "role": rows["role"],
            "files": rows["files_in_window"].astype(int),
            "size": rows["bytes_in_window"].map(_gb),
            "first": rows["first"],
            "last": rows["last"],
        }
    )
    lines = [
        "## ACAG satellite PM2.5",
        "",
        f"Checked {a['checked_utc']}; years {a['window_years'][0]}–{a['window_years'][1]}. "
        f"Total for the rows below: **{_gb(rows['bytes_in_window'].sum())}**.",
        "",
        _md(tab),
        "",
        "### Extent (one 2019 annual 0.01° file per version)",
        "",
    ]
    for e in a["extents"]:
        missing = [
            k for k, v in e["points"].items() if v["value"] is None or math.isnan(v["value"])
        ]
        lines += [
            f"- `{e['file'].rsplit('/', 1)[-1]}`: variable `{e['variable']}` ({e['units']}), "
            f"lat {e['lat_range'][0]:.2f} to {e['lat_range'][1]:.2f}, "
            f"lon {e['lon_range'][0]:.2f} to {e['lon_range'][1]:.2f}, "
            f"covers India bbox: **{e['covers_india_bbox']}**; finite share inside the bbox "
            f"{e['india_bbox_valid_share']:.1%}; "
            f"{len(e['points']) - len(missing)}/{len(e['points'])} test points have a value"
            + (f" (missing: {', '.join(missing)})" if missing else "")
            + "."
        ]
    return lines + [""]


def firms_section(f: dict) -> list[str]:
    df = pd.DataFrame(f["files"])
    lines = [
        "## NASA FIRMS (keyless yearly country archive)",
        "",
        f"Checked {f['checked_utc']}.",
        "",
    ]
    for product, g in df.groupby("product", sort=False):
        ok = g[g["status"] == 200]
        bad = g[g["status"] != 200]
        lines.append(
            f"- **{product}**: {ok['year'].min()}–{ok['year'].max()} available "
            f"({len(ok)} files, {_gb(ok['bytes'].sum())})"
            + (
                f"; not available: {', '.join(map(str, bad['year']))} "
                f"(HTTP {bad['status'].iloc[0]})"
                if len(bad)
                else ""
            )
            + "."
        )
    if "first_row" in df:
        ok = df[df["status"] == 200].copy()
        ok["versions"] = ok.apply(
            lambda r: (
                r["first_row"]["version"]
                if r["first_row"]["version"] == r["last_row"]["version"]
                else f"{r['first_row']['version']} -> {r['last_row']['version']}"
            ),
            axis=1,
        )
        lines += ["", "`version` field in the first and last row of each yearly file:", ""]
        for product, g in ok.groupby("product", sort=False):
            runs, start = [], None
            rows = list(g.itertuples())
            for i, row in enumerate(rows):
                if start is None:
                    start = row
                if i == len(rows) - 1 or rows[i + 1].versions != row.versions:
                    span = f"{start.year}" if start.year == row.year else f"{start.year}–{row.year}"
                    runs.append(f"{span}: `{row.versions}`")
                    start = None
            lines.append(f"- {product}: " + "; ".join(runs))
    lines += ["", "Columns: `" + f["sample_head"]["modis"][0] + "`", ""]
    return lines


def cds_section(c: dict) -> list[str]:
    return (
        [
            "## ERA5 via CDS (Delhi test)",
            "",
            f"Dataset `{c['dataset']}`, point {c['request']['location']}, "
            f"dates {c['request']['date'][0]}, "
            f"{len(c['request']['variable'])} variables. Returned {c['bytes'] / 1e6:.1f} MB (zip).",
            "",
        ]
        + [f"- {k}: {v}" for k, v in c.get("content", {}).items()]
        + [""]
    )


def write_report(probe: Path, dest: Path) -> Path:
    parts = [
        "# Data probe (Phase 2, step 0)",
        "",
        "*Generated by `python -m src.acquire.probe report` from `data/interim/probe/*.json`. "
        "Do not edit by hand.*",
        "",
        f"Ground window: {params()['windows']['ground_start']} to "
        f"{params()['windows']['ground_end']}.",
        "",
    ]
    for name, fn in [
        ("openaq", openaq_section),
        ("cpcb_mirror", cpcb_mirror_section),
        ("acag", acag_section),
        ("cds", cds_section),
        ("firms", firms_section),
    ]:
        data = _load(probe, name)
        parts += fn(data) if data else [f"## {name}", "", "*Not run.*", ""]
    dest.write_text("\n".join(parts), encoding="utf-8")
    return dest

"""Checks on the CPCB mirror before any analysis uses it (Reenu's conditions on DEC-037).

1. Timezone. The mirror labels timestamps UTC, but its parse script only *stamps* CPCB's naive
   times as UTC (parse.py: .dt.replace_time_zone("UTC")), and CPCB publishes Indian time. Three
   independent tests of what the labels really are:
   a. Values: at stations present in both sources, shift the mirror's labels by candidate
      offsets (15-minute steps, -12 h to +12 h) and count exact matches with OpenAQ's values,
      whose timestamps carry an explicit UTC offset.
   b. Sun: the daily solar-radiation (SR) cycle measured at the stations peaks at local solar
      noon, 12:00 - longitude/15 h in UTC. Compare with the SR centroid on the label clock.
   c. Reanalysis: lag of maximum correlation between station SR and ERA5 solar radiation
      (true UTC) at the same grid point.
2. Station-years with valid PM2.5 and PM10 data, using the completeness rules in
   config/params.yaml (valid day >= 75% of hours, valid year >= 75% of days), on Indian
   (IST) days after applying the timestamp correction found in 1 (DEC-040).

Outputs: data/interim/mirror_checks/*.csv and docs/mirror-checks.md (generated).

    python -m src.acquire.mirror_checks
"""

import glob
import gzip
import io
import json
import zipfile
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

from src.common.paths import DOCS, INTERIM, params, raw_dir

OUT = INTERIM / "mirror_checks"
MIRROR = (raw_dir("cpcb_mirror") / "*.parquet").as_posix()
OFFSETS_H = np.arange(-12, 12.25, 0.25)
MATCH_TOL = 0.05  # ug/m3: values are printed to 2 decimals, so equal values differ by < this


# ------------------------------------------------------------------ loading


def openaq_series(location_id: int, year: int, parameter: str) -> pd.DataFrame:
    """OpenAQ measurements for one location-year: utc (naive UTC), value."""
    z = raw_dir("openaq") / f"locationid={location_id}" / f"year={year}.zip"
    if not z.exists():
        return pd.DataFrame(columns=["utc", "value"])
    frames = []
    with zipfile.ZipFile(z) as f:
        for name in f.namelist():
            if name.endswith(".csv.gz"):
                frames.append(pd.read_csv(io.BytesIO(gzip.decompress(f.read(name)))))
    if not frames:
        return pd.DataFrame(columns=["utc", "value"])
    d = pd.concat(frames)
    d = d[d.parameter == parameter]
    utc = pd.to_datetime(d.datetime, utc=True, format="ISO8601").dt.tz_localize(None)
    return pd.DataFrame({"utc": utc, "value": d.value.astype(float)}).drop_duplicates("utc")


def mirror_series(sid: str, year: int, column: str) -> pd.DataFrame:
    """Mirror values for one station-year on the label clock (tz dropped): label, value."""
    q = f"""select "Timestamp" as label, "{column}" as value from read_parquet('{MIRROR}')
            where "Station ID" = ? and year("Timestamp") = ? and "{column}" is not null"""
    d = duckdb.connect().execute(q, [sid, year]).df()
    d["label"] = pd.to_datetime(d.label).dt.tz_localize(None)
    return d


# ------------------------------------------------------------------ 1a: values


def offset_scan(mirror: pd.DataFrame, openaq: pd.DataFrame, offsets=OFFSETS_H) -> pd.DataFrame:
    """For each offset h (true UTC = label - h), share of paired values that are equal."""
    oq = openaq.set_index("utc").value
    rows = []
    for h in offsets:
        t = mirror.label - pd.Timedelta(hours=float(h))
        v = oq.reindex(t.values).to_numpy()
        ok = ~np.isnan(v)
        diff = np.abs(mirror.value.to_numpy()[ok] - v[ok])
        rows.append(
            {
                "offset_h": float(h),
                "pairs": int(ok.sum()),
                "exact_share": float((diff < MATCH_TOL).mean()) if ok.any() else np.nan,
                "median_abs_diff": float(np.median(diff)) if ok.any() else np.nan,
            }
        )
    return pd.DataFrame(rows)


def hourly_scan(mirror: pd.DataFrame, openaq: pd.DataFrame, offsets=OFFSETS_H) -> pd.DataFrame:
    """As offset_scan, for OpenAQ hourly values: the mirror's 15-minute values are averaged into
    hours on each candidate clock. 'exact' here means within 1 ug/m3 (averaging and rounding)."""
    oq = openaq.set_index("utc").value
    rows = []
    for h in offsets:
        s = pd.Series(mirror.value.to_numpy(), index=mirror.label - pd.Timedelta(hours=float(h)))
        hourly = s.resample("1h").mean()
        v = oq.reindex(hourly.index)
        ok = v.notna() & hourly.notna()
        diff = (hourly[ok] - v[ok]).abs()
        rows.append(
            {
                "offset_h": float(h),
                "pairs": int(ok.sum()),
                "exact_share": float((diff < 1.0).mean()) if ok.any() else np.nan,
                "median_abs_diff": float(diff.median()) if ok.any() else np.nan,
            }
        )
    return pd.DataFrame(rows)


def value_test(
    crosswalk: pd.DataFrame, years=(2025, 2022, 2021, 2019, 2017), max_pairs: int = 40
) -> pd.DataFrame:
    done, out = 0, []
    cands = crosswalk[(crosswalk.match == "exact") & crosswalk.openaq_location_ids.notna()]
    for r in cands.itertuples():
        for y in years:
            for lid in str(r.openaq_location_ids).split(";"):
                oq = openaq_series(int(lid), y, "pm25")
                if len(oq) < 500:
                    continue
                mi = mirror_series(r.sid, y, "PM2.5 (µg/m³)")
                if len(mi) < 500:
                    continue
                step = oq.utc.sort_values().diff().median()
                hourly = step >= pd.Timedelta(minutes=60)
                s = hourly_scan(mi, oq) if hourly else offset_scan(mi, oq)
                best = s.loc[s.exact_share.idxmax()]
                out.append(
                    {
                        "sid": r.sid,
                        "sname": r.sname,
                        "openaq_location_id": int(lid),
                        "year": y,
                        "openaq_resolution": "hourly" if hourly else "15-min",
                        "pairs_at_best": int(best.pairs),
                        "best_offset_h": best.offset_h,
                        "exact_share_at_best": round(best.exact_share, 4),
                        "exact_share_at_0h": round(
                            float(s.loc[s.offset_h == 0, "exact_share"].iloc[0]), 4
                        ),
                        "exact_share_at_5.5h": round(
                            float(s.loc[s.offset_h == 5.5, "exact_share"].iloc[0]), 4
                        ),
                    }
                )
                done += 1
                break
            if done >= max_pairs:
                return pd.DataFrame(out)
    return pd.DataFrame(out)


# ------------------------------------------------------------------ 1b: sun


def solar_test(crosswalk: pd.DataFrame, year: int = 2024) -> pd.DataFrame:
    """SR-weighted mean time of day on the label clock vs expected solar noon (UTC)."""
    q = f"""select "Station ID" as sid, (hour("Timestamp") * 60 + minute("Timestamp")) as minute_of_day,
                   avg("SR (W/mt2)") as sr, count(*) as n
            from read_parquet('{MIRROR}')
            where year("Timestamp") = {year} and "SR (W/mt2)" is not null and "SR (W/mt2)" >= 0
            group by 1, 2"""
    d = duckdb.connect().execute(q).df()
    lon = crosswalk.set_index("sid").lon
    out = []
    for sid, g in d.groupby("sid"):
        if sid not in lon.index or pd.isna(lon[sid]) or g.n.sum() < 5000 or g.sr.max() < 100:
            continue
        g = g.sort_values("minute_of_day")
        # centroid of the daytime bump (values above a fifth of the peak), in hours
        day = g[g.sr > 0.2 * g.sr.max()]
        centroid = float((day.minute_of_day * day.sr).sum() / day.sr.sum() / 60)
        noon_utc = 12 - float(lon[sid]) / 15
        out.append(
            {
                "sid": sid,
                "lon": float(lon[sid]),
                "sr_centroid_label_h": round(centroid, 3),
                "solar_noon_utc_h": round(noon_utc, 3),
                "implied_offset_h": round(centroid - noon_utc, 3),
            }
        )
    return pd.DataFrame(out)


# ------------------------------------------------------------------ 1c: reanalysis


def era5_test(crosswalk: pd.DataFrame, year: int = 2019, max_stations: int = 15) -> pd.DataFrame:
    """Lag (hours) that maximises the correlation of station SR with ERA5 ssrd at its cell."""
    files = {Path(f).name: f for f in glob.glob(str(raw_dir("era5_timeseries") / "era5ts_*.zip"))}
    out = []
    for r in crosswalk[crosswalk.coord_source == "openaq"].itertuples():
        name = f"era5ts_{r.era5_lat:.2f}_{r.era5_lon:.2f}.zip"
        if name not in files:
            continue
        mi = mirror_series(r.sid, year, "SR (W/mt2)")
        if len(mi) < 5000:
            continue
        with zipfile.ZipFile(files[name]) as z:
            e = pd.read_csv(z.open(z.namelist()[0]), usecols=["valid_time", "ssrd"])
        # ssrd at valid_time T is accumulated over (T - 1 h, T], in UTC
        e = e.assign(t=pd.to_datetime(e.valid_time)).set_index("t").ssrd

        def corr_at(lag: float, mi=mi, e=e) -> float:
            s = pd.Series(mi.value.to_numpy(), index=mi.label - pd.Timedelta(hours=float(lag)))
            hourly = s.resample("1h", label="right", closed="right").mean()
            return hourly.reindex(e.index).corr(e)

        best = max(
            ((lag, corr_at(lag)) for lag in np.arange(-12, 12.25, 0.25)),
            key=lambda x: np.nan_to_num(x[1], nan=-2),
        )
        out.append(
            {
                "sid": r.sid,
                "cell": name,
                "best_lag_h": float(best[0]),
                "corr_at_best": round(float(best[1]), 4),
            }
        )
        if len(out) >= max_stations:
            break
    return pd.DataFrame(out)


# ------------------------------------------------------------------ 2: station-years


def station_years() -> pd.DataFrame:
    c = params()["completeness"]
    hours_needed = int(np.ceil(24 * c["min_hour_share_per_day"]))
    # days are Indian (IST) days: label - (label_minus_utc - 5.5) hours
    shift_min = int(round((params()["mirror"]["label_minus_utc_hours"] - 5.5) * 60))
    q = f"""
    with hourly as (
      select "Station ID" as sid, date_trunc('hour', "Timestamp" - interval {shift_min} minute) as h,
             count("PM2.5 (µg/m³)") > 0 as has25, count("PM10 (µg/m³)") > 0 as has10
      from read_parquet('{MIRROR}') group by 1, 2),
    daily as (
      select sid, cast(h as date) as d, sum(has25::int) as h25, sum(has10::int) as h10
      from hourly group by 1, 2),
    yearly as (
      select sid, year(d) as year,
             sum((h25 >= {hours_needed})::int) as days25, sum((h10 >= {hours_needed})::int) as days10,
             sum((h25 >= {hours_needed} and h10 >= {hours_needed})::int) as days_both,
             sum((h25 > 0)::int) as any25, sum((h10 > 0)::int) as any10
      from daily group by 1, 2)
    select * from yearly order by year, sid"""
    con = duckdb.connect()
    # bounded memory, spilling to disk: the query scans ~150 million 15-minute rows
    con.execute(
        f"set memory_limit='6GB'; set threads=6; set temp_directory='{(INTERIM / 'duckdb_tmp').as_posix()}'"
    )
    return con.execute(q).df()


def station_year_table(sy: pd.DataFrame) -> pd.DataFrame:
    share = params()["completeness"]["min_day_share_per_year"]
    sy = sy.copy()
    sy["days_in_year"] = sy.year.map(lambda y: 366 if y % 4 == 0 else 365)
    need = sy.days_in_year * share
    rows = []
    for y, g in sy.groupby("year"):
        n = need[g.index]
        rows.append(
            {
                "year": int(y),
                "stations with any PM2.5": int((g.any25 > 0).sum()),
                "stations with any PM10": int((g.any10 > 0).sum()),
                "valid station-years PM2.5": int((g.days25 >= n).sum()),
                "valid station-years PM10": int((g.days10 >= n).sum()),
                "valid station-years both": int((g.days_both >= n).sum()),
            }
        )
    return pd.DataFrame(rows).set_index("year")


# ------------------------------------------------------------------ report


def _md(df: pd.DataFrame) -> str:
    cols = [df.index.name or ""] + list(df.columns)
    lines = ["| " + " | ".join(map(str, cols)) + " |", "|" + "---|" * len(cols)]
    lines += [
        "| " + " | ".join(map(str, [i, *r])) + " |"
        for i, r in zip(df.index, df.itertuples(index=False), strict=True)
    ]
    return "\n".join(lines)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    cw = pd.read_csv(INTERIM / "station_crosswalk.csv")
    a = value_test(cw)
    a.to_csv(OUT / "timezone_values.csv", index=False)
    b = pd.concat(
        [solar_test(cw, year=y).assign(year=y) for y in range(2015, 2026)], ignore_index=True
    )
    b.to_csv(OUT / "timezone_solar.csv", index=False)
    c = era5_test(cw)
    c.to_csv(OUT / "timezone_era5.csv", index=False)
    sy = station_years()
    sy.to_csv(OUT / "station_year_days.csv", index=False)
    table = station_year_table(sy)
    table.to_csv(OUT / "station_years.csv")
    cfg = params()["completeness"]

    lines = [
        "# CPCB mirror checks",
        "",
        "*Generated by `python -m src.acquire.mirror_checks`. Do not edit by hand.*",
        "",
        "## 1. Timezone of the mirror's timestamps",
        "",
        "Offsets are hours to subtract from the mirror's label to get UTC. IST is +5.5.",
        "",
    ]
    if len(a):
        vc = a.best_offset_h.value_counts()
        lines += [
            f"**a. Matched values.** {len(a)} station-years at {a.sid.nunique()} stations, PM2.5, "
            f"15-minute values, offsets scanned from -12 h to +12 h in 15-minute steps. "
            f"Best offset: "
            + ", ".join(f"{k:+g} h at {v} station-years" for k, v in vc.items())
            + ". "
            f"Median share of exactly equal values at the best offset: {a.exact_share_at_best.median():.1%}; "
            f"at +5.5 h: {a['exact_share_at_5.5h'].median():.1%}; at 0 h (labels taken as UTC): "
            f"{a.exact_share_at_0h.median():.1%}.",
            "",
        ]
    else:
        lines += [
            "**a. Matched values.** Not run: no station-year with data in both sources yet.",
            "",
        ]
    if len(a):
        by = (
            a.groupby(["year", "openaq_resolution"])
            .agg(
                station_years=("sid", "size"),
                best_offset_median=("best_offset_h", "median"),
                match_share_at_best=("exact_share_at_best", "median"),
            )
            .round(3)
        )
        lines += [
            "Matched values by year ('match' = identical 15-minute value, or hourly mean within "
            "1 ug/m3 where OpenAQ holds hourly data):",
            "",
            _md(by.reset_index().set_index("year")),
            "",
        ]
    if len(b):
        by = (
            b.groupby("year")
            .implied_offset_h.agg(
                stations="size",
                p10=lambda s: s.quantile(0.1),
                p25=lambda s: s.quantile(0.25),
                median="median",
                p75=lambda s: s.quantile(0.75),
                p90=lambda s: s.quantile(0.9),
            )
            .round(2)
        )
        lines += [
            "**b. Sun.** Stations with a working solar-radiation (SR) sensor. The SR-weighted centre "
            "of the day on the label clock, minus the station's solar noon in UTC (12:00 - "
            "longitude/15). Labels in UTC would give about 0 h; in IST about +5.5 h. The centroid "
            "reads slightly early when afternoons are hazier than mornings.",
            "",
            _md(by),
            "",
        ]
    if len(c):
        lines += [
            f"**c. ERA5.** {len(c)} stations (2019): the lag that best aligns station SR with ERA5 surface "
            f"solar radiation (true UTC): median {c.best_lag_h.median():+.1f} h "
            f"(values: {', '.join(f'{k:+g} h x{v}' for k, v in c.best_lag_h.value_counts().items())}); "
            f"median correlation {c.corr_at_best.median():.2f}.",
            "",
        ]
    else:
        lines += [
            "**c. ERA5.** Not run: no ERA5 point series downloaded yet for these stations.",
            "",
        ]
    lines += [
        f"**Applied correction** (config/params.yaml, `mirror.label_minus_utc_hours`): "
        f"{params()['mirror']['label_minus_utc_hours']:+g} h from label to UTC.",
        "",
        "## 2. Station-years with valid data (mirror)",
        "",
        f"A valid day has PM data in at least {cfg['min_hour_share_per_day']:.0%} of its hours; a valid "
        f"year has at least {cfg['min_day_share_per_year']:.0%} valid days (config/params.yaml). "
        "Days are Indian (IST) days after the timestamp correction above.",
        "",
        _md(table),
        "",
    ]
    (DOCS / "mirror-checks.md").write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({"value_pairs": len(a), "solar_stations": len(b), "era5_stations": len(c)}))


if __name__ == "__main__":
    main()

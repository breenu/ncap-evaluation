"""Spatial consistency (proposal stage 3): each station against its neighbours and the satellite.

Neighbour reference (used here, by changepoints.py and by missingness.py)
    For each station-day, the median of log daily PM at the OTHER stations within
    `flags.neighbour_radius_km` that have a valid day (config completeness rule), when at least two
    such neighbours exist. Only station-level coordinates are used (stations.csv). The residual
    r = log(station) - reference measures how the station departs from its airshed that day,
    removing weather and season, which move neighbours together.

Station-year checks (per pollutant), DEC-071
    neighbour_corr   correlation of the station's daily log PM with the reference. A station that
                     does not move with its airshed is suspect. Flag: robust z (median/MAD across
                     station-years of that year) below -z.
    sat_ratio        log(station annual mean / ACAG V5GL06 value of the station's 0.01 deg cell).
                     Flag: robust z beyond +-z within the year. ACAG ends in 2024.
    Stations without two neighbours, or without a satellite value, are 'not assessable' (NaN), and
    are not penalised for it.

Outputs
    data/interim/audit/neighbour_ref.parquet  sid, date_ist, pollutant, value, ref, n_nb, resid
    data/interim/audit/spatial_station_year.csv

    python -m src.clean.spatial
"""

import numpy as np
import pandas as pd

from src.clean.station_meta import haversine_km, load_stations
from src.common.paths import INTERIM, PROCESSED, params

AUDIT = INTERIM / "audit"
PM = ("pm25", "pm10")


def valid_hours() -> int:
    return int(np.ceil(24 * params()["completeness"]["min_hour_share_per_day"]))


def neighbour_lists(stations: pd.DataFrame, radius_km: float) -> dict[str, list[str]]:
    s = stations[stations.coord_is_station_level].reset_index(drop=True)
    la, lo = s.lat.to_numpy(), s.lon.to_numpy()
    d = haversine_km(la[:, None], lo[:, None], la[None, :], lo[None, :])
    np.fill_diagonal(d, np.inf)
    return {s.sid[i]: list(s.sid[np.where(d[i] <= radius_km)[0]]) for i in range(len(s))}


def neighbour_reference(
    day: pd.DataFrame, nbrs: dict[str, list[str]], pollutant: str, min_nb: int = 2
) -> pd.DataFrame:
    """Daily log reference from neighbours. `day`: sid, date_ist, {p}, {p}_h1 (station_day)."""
    d = day[day[f"{pollutant}_h1"] >= valid_hours()][["sid", "date_ist", pollutant]].dropna()
    d = d[d[pollutant] > 0].assign(logv=lambda x: np.log(x[pollutant]))
    wide = d.pivot(index="date_ist", columns="sid", values="logv")
    rows = []
    for sid, nb in nbrs.items():
        if sid not in wide.columns:
            continue
        cols = [c for c in nb if c in wide.columns]
        if len(cols) < min_nb:
            continue
        sub = wide[cols]
        n = sub.notna().sum(axis=1)
        ref = sub.median(axis=1).where(n >= min_nb)
        own = wide[sid]
        ok = own.notna() & ref.notna()
        rows.append(
            pd.DataFrame(
                {
                    "sid": sid,
                    "date_ist": own.index[ok],
                    "logv": own[ok].to_numpy(),
                    "ref": ref[ok].to_numpy(),
                    "n_nb": n[ok].to_numpy(),
                }  # fmt: skip
            )
        )
    out = (
        pd.concat(rows, ignore_index=True)
        if rows
        else pd.DataFrame(columns=["sid", "date_ist", "logv", "ref", "n_nb"])
    )
    out["resid"] = out.logv - out.ref
    return out.assign(pollutant=pollutant)


def robust_z(x: pd.Series) -> pd.Series:
    """(x - median) / (1.4826 x MAD); NaN-safe; 0 where MAD is 0."""
    med = x.median()
    mad = 1.4826 * (x - med).abs().median()
    return (x - med) / mad if mad and np.isfinite(mad) else x * 0


def station_year_checks(
    ref: pd.DataFrame, day: pd.DataFrame, sat: pd.DataFrame, z: float
) -> pd.DataFrame:
    out = []
    for p in PM:
        r = ref[ref.pollutant == p].assign(year=lambda d: pd.to_datetime(d.date_ist).dt.year)
        corr = (
            r.groupby(["sid", "year"])
            .apply(lambda g: g.logv.corr(g.ref) if len(g) >= 60 else np.nan, include_groups=False)
            .rename("neighbour_corr")
        )
        dv = day[day[f"{p}_h1"] >= valid_hours()].assign(
            year=lambda d: pd.to_datetime(d.date_ist).dt.year
        )
        annual = (
            dv.groupby(["sid", "year"])[p]
            .agg(["mean", "size"])
            .rename(columns={"mean": "annual_mean", "size": "valid_days"})
        )
        t = annual.join(corr, how="left").reset_index()
        s = sat[sat["product"] == "V5GL06"][["sid", "year", "pm25_cell"]]
        t = t.merge(s, on=["sid", "year"], how="left")
        t["sat_ratio"] = np.log(t.annual_mean / t.pm25_cell) if p == "pm25" else np.nan
        # only station-years with a reasonable number of valid days enter the network distribution
        enough = t.valid_days >= 60
        t["corr_z"] = np.nan
        t["sat_z"] = np.nan
        for _y, g in t[enough].groupby("year"):
            t.loc[g.index, "corr_z"] = robust_z(g.neighbour_corr)
            t.loc[g.index, "sat_z"] = robust_z(g.sat_ratio)
        t["flag_neighbour"] = t.corr_z < -z
        t["flag_satellite"] = t.sat_z.abs() > z
        out.append(t.assign(pollutant=p))
    return pd.concat(out, ignore_index=True)


def main() -> None:
    fc = params()["flags"]
    stations = load_stations()
    day = pd.read_parquet(PROCESSED / "station_day.parquet")
    nbrs = neighbour_lists(stations, fc["neighbour_radius_km"])
    ref = pd.concat([neighbour_reference(day, nbrs, p) for p in PM], ignore_index=True)
    AUDIT.mkdir(parents=True, exist_ok=True)
    ref.to_parquet(AUDIT / "neighbour_ref.parquet", index=False)
    sat = pd.read_parquet(PROCESSED / "station_year_sat.parquet")
    t = station_year_checks(ref, day, sat, fc["robust_z"])
    t.to_csv(AUDIT / "spatial_station_year.csv", index=False)
    print(t.groupby("pollutant")[["flag_neighbour", "flag_satellite"]].sum())


if __name__ == "__main__":
    main()

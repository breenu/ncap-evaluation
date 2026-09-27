"""ERA5 hourly point series -> daily weather per 0.25 degree cell, on Indian days (Phase 5, DEC-100).

Input: data/raw/era5_timeseries/era5ts_<lat>_<lon>.zip, one CSV per grid point, hourly in UTC
(DEC-035): t2m, d2m (K), u10, v10 (m/s), blh (m), tp (m, accumulated over the hour ending at
valid_time), ssrd (J/m2, same accumulation).

An Indian day d runs from 18:30 UTC on d-1 to 18:30 UTC on d, so it holds exactly the 24 UTC hours
19:00 (d-1) to 18:00 (d); an hour is assigned by valid_time + 5.5 h. (An accumulation stamped
19:00 UTC covers 23:30-00:30 IST, so half an hour of one accumulation per day falls on the
neighbouring day; negligible for daily sums.) Days without all 24 hours (the first day of the
window) are dropped.

Daily features, one row per cell and Indian day:
    temp      mean 2 m temperature (deg C)
    rh        mean relative humidity (%) from hourly T and dew point (Magnus formula)
    ws        mean scalar wind speed at 10 m (m/s): dispersion depends on speed, whatever the direction
    wd        direction of the vector-mean wind (degrees the wind blows FROM, 0-360)
    blh_mean  mean boundary-layer height (m)
    blh_pm    afternoon maximum boundary-layer height (m), 11:30-17:30 IST
    precip    precipitation sum (mm)
    ssrd      surface solar radiation sum (MJ/m2); small negative values clipped to 0 (DEC-035)

    python -m src.normalise.era5_daily
    -> data/interim/normalise/era5_daily.parquet
"""

import re
import zipfile
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

from src.common.paths import INTERIM, params, raw_dir

OUT = INTERIM / "normalise"
IST_OFFSET = pd.Timedelta(hours=5, minutes=30)
FEATURES = ["temp", "rh", "ws", "wd", "blh_mean", "blh_pm", "precip", "ssrd"]
NAME = re.compile(r"era5ts_(-?\d+\.\d+)_(-?\d+\.\d+)\.zip$")


def cell_id(lat: float, lon: float) -> str:
    return f"{lat:.2f}_{lon:.2f}"


def rh_from_dewpoint(t_c, td_c):
    """Relative humidity (%) from temperature and dew point (deg C), Magnus form with the
    Alduchov & Eskridge (1996) coefficients: RH = 100 e_s(Td) / e_s(T)."""
    a, b = 17.625, 243.04
    return 100 * np.exp(a * td_c / (b + td_c) - a * t_c / (b + t_c))


def wind_from_direction(u, v):
    """Meteorological direction (degrees the wind blows FROM, clockwise from north) of vector (u, v)."""
    return np.mod(270 - np.degrees(np.arctan2(v, u)), 360)


def read_cell(path: Path) -> pd.DataFrame:
    with zipfile.ZipFile(path) as z:
        members = [m for m in z.namelist() if m.endswith(".csv")]
        if len(members) != 1:
            raise ValueError(f"{path.name}: expected one CSV, found {members}")
        with z.open(members[0]) as f:
            return pd.read_csv(f, parse_dates=["valid_time"])


def daily(h: pd.DataFrame, afternoon_utc: tuple[int, int]) -> pd.DataFrame:
    """Hourly UTC rows of one cell -> one row per complete Indian day."""
    ist = h.valid_time + IST_OFFSET
    t = h.t2m - 273.15
    td = h.d2m - 273.15
    x = pd.DataFrame(
        {
            "date": ist.dt.normalize(),
            "temp": t,
            "rh": rh_from_dewpoint(t, td),
            "ws": np.hypot(h.u10, h.v10),
            "u": h.u10,
            "v": h.v10,
            "blh": h.blh,
            "blh_aft": h.blh.where(h.valid_time.dt.hour.between(*afternoon_utc)),
            "precip": h.tp * 1000,
            "ssrd": h.ssrd.clip(lower=0) / 1e6,
        }
    )
    g = x.groupby("date")
    d = g.agg(
        n=("temp", "size"),
        temp=("temp", "mean"),
        rh=("rh", "mean"),
        ws=("ws", "mean"),
        u=("u", "mean"),
        v=("v", "mean"),
        blh_mean=("blh", "mean"),
        blh_pm=("blh_aft", "max"),
        precip=("precip", "sum"),
        ssrd=("ssrd", "sum"),
    )
    d = d[d.n == 24].drop(columns="n")
    d["wd"] = wind_from_direction(d.u, d.v)
    return d.drop(columns=["u", "v"]).reset_index()[["date", *FEATURES]]


def one(path: Path) -> pd.DataFrame:
    lat, lon = (float(g) for g in NAME.search(path.name).groups())
    afternoon = tuple(params()["deweathering"]["afternoon_utc_hours"])
    d = daily(read_cell(path), afternoon)
    d.insert(0, "cell", cell_id(lat, lon))
    return d


def main() -> None:
    paths = sorted(raw_dir("era5_timeseries").glob("era5ts_*.zip"))
    with ProcessPoolExecutor(params()["deweathering"]["workers"]) as pool:
        out = pd.concat(pool.map(one, paths), ignore_index=True)
    out[FEATURES] = out[FEATURES].astype("float32")
    OUT.mkdir(parents=True, exist_ok=True)
    out.to_parquet(OUT / "era5_daily.parquet", index=False)
    print(f"era5_daily: {out.cell.nunique()} cells, {len(out):,} cell-days, "
          f"{out.date.min():%Y-%m-%d} to {out.date.max():%Y-%m-%d}")  # fmt: skip


if __name__ == "__main__":
    main()

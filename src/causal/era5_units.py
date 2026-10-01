"""ERA5 weather covariates per satellite unit and year, for the Layer A event study (DEC-142).

Source: ERA5 monthly means over the India box, 2005-2024 (data/raw/era5_monthly, DEC-004). Each unit's
value is the area-weighted mean of the 0.25 deg cells over its polygon, with exact coverage fractions
(exactextract), the same rule for treated and control units. Annual values:

    t2m_c        mean 2 m temperature (deg C), months weighted by their days
    rh           mean relative humidity (%), from each month's mean temperature and dew point (Magnus,
                 as Phase 5, DEC-100); an approximation, since RH of monthly means is not the mean RH
    ws           mean 10 m wind speed (m/s): the speed of each month's mean wind vector. The monthly
                 download has no scalar speed, so this understates it where the wind turns (stated)
    blh          mean boundary-layer height (m)
    precip_mm    total precipitation (mm per year): monthly means of daily totals x days in the month
    ssrd_mj      mean daily surface solar radiation (MJ/m2)

Weather only: no pollution value and no NCAP information is read.

    python -m src.causal.era5_units
"""

import tempfile
import zipfile
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import rioxarray  # noqa: F401 - registers the .rio accessor
import xarray as xr
from exactextract import exact_extract

from src.common.paths import INTERIM, PROCESSED, raw_dir
from src.normalise.era5_daily import rh_from_dewpoint

OUT = PROCESSED / "causal"
ZIP = raw_dir("era5_monthly") / "era5_monthly_india_2005_2024.zip"
VARS = ["t2m_c", "rh", "ws", "blh", "precip_mm", "ssrd_mj"]


def monthly_fields(folder: Path) -> xr.Dataset:
    """Monthly derived fields on the ERA5 grid (one time step per month)."""
    parts = []
    for p in sorted(folder.glob("*.nc")):
        d = xr.open_dataset(p).drop_vars(["expver", "number"], errors="ignore")
        # the accumulated file stamps each month at 06:00, the instantaneous one at 00:00: align on the
        # month (an outer join on the raw stamps would double the time axis and half-fill every variable)
        d = d.assign_coords(valid_time=d.valid_time.dt.floor("D"))
        if (d.valid_time.dt.day != 1).any():
            raise ValueError(f"{p.name}: monthly stamps not on the 1st of the month")
        parts.append(d)
    ds = xr.merge(parts, join="exact", compat="override")
    t = ds.valid_time.dt
    days = xr.DataArray(pd.DatetimeIndex(ds.valid_time.values).days_in_month, dims="valid_time",
                        coords={"valid_time": ds.valid_time})  # fmt: skip
    t_c, td_c = ds.t2m - 273.15, ds.d2m - 273.15
    out = xr.Dataset({
        "t2m_c": t_c,
        "rh": rh_from_dewpoint(t_c, td_c),
        "ws": np.hypot(ds.u10, ds.v10),
        "blh": ds.blh,
        "precip_mm": ds.tp * 1000.0 * days,   # m per day (monthly mean of daily totals) -> mm per month
        "ssrd_mj": ds.ssrd / 1e6,             # J/m2 per day -> MJ/m2 per day
    })  # fmt: skip
    return out.assign_coords(year=t.year, month=t.month, days=days)


def annual(fields: xr.Dataset) -> xr.Dataset:
    """Calendar-year values: day-weighted means, except precipitation (a sum)."""
    w = fields.days
    mean = (fields.drop_vars("precip_mm") * w).groupby("year").sum() / w.groupby("year").sum()
    return mean.assign(precip_mm=fields.precip_mm.groupby("year").sum())


def to_raster(da: xr.DataArray, path: Path) -> Path:
    """A (year, latitude, longitude) field as a multi-band GeoTIFF, one band per year."""
    r = da.rename({"longitude": "x", "latitude": "y"}).transpose("year", "y", "x")
    r = r.sortby("y", ascending=False).rio.write_crs(4326).astype("float32")
    r.rio.to_raster(path)
    return path


def unit_values(units: gpd.GeoDataFrame, ann: xr.Dataset, work: Path) -> pd.DataFrame:
    years = ann.year.values.astype(int)
    rows = []
    for v in VARS:
        tif = to_raster(ann[v], work / f"{v}.tif")
        r = exact_extract(str(tif), units, "mean", include_cols=["unit_id"], output="pandas")
        cols = [c for c in r.columns if c != "unit_id"]
        if len(cols) != len(years):
            raise ValueError(f"{v}: {len(cols)} bands for {len(years)} years")
        long = r.melt(id_vars="unit_id", value_vars=cols, var_name="band", value_name=v)
        long["year"] = long.band.map(dict(zip(cols, years, strict=True)))
        rows.append(long.drop(columns="band").set_index(["unit_id", "year"]))
    out = pd.concat(rows, axis=1).reset_index()
    if out[VARS].isna().any().any():
        bad = out[out[VARS].isna().any(axis=1)].unit_id.unique()
        raise ValueError(f"ERA5 covariates missing for {len(bad)} units, e.g. {list(bad[:5])}")
    return out


def main() -> None:
    units = gpd.read_file(INTERIM / "sat_units.gpkg")[["unit_id", "geometry"]]
    OUT.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        with zipfile.ZipFile(ZIP) as z:
            z.extractall(tmp)
        ann = annual(monthly_fields(tmp))
        out = unit_values(units, ann, tmp)
    out.to_parquet(OUT / "era5_unit_year.parquet", index=False)
    print(f"era5_units: {out.unit_id.nunique()} units x {out.year.nunique()} years "
          f"({out.year.min()}-{out.year.max()})")  # fmt: skip


if __name__ == "__main__":
    main()

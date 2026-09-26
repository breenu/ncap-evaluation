"""Satellite PM2.5 (ACAG) over the satellite units, and at station locations.

Weighting (DEC-070): the primary city value is the POPULATION-WEIGHTED mean over the unit's polygon,
for every unit (treated and control alike). Weights are GHS-POP 2020 (30 arc-seconds) summed onto
each ACAG grid. This handles oversized polygons (New Delhi 2,139 km2, Hajipur/Muzaffarpur 3,166 km2,
and rural-dense control centres in Bihar, Kerala and West Bengal): the value is what the people
living in the unit breathe, not an average over empty or sparse ground. The unweighted, area-weighted
mean over the same polygon is kept as the sensitivity check. Both use exact cell-coverage fractions
(exactextract).

Products (DEC-001, DEC-002): V5GL06 annual 0.01 deg (primary), V6GL03 annual (comparison),
V6GL0204 annual (vintage), V5GL06 monthly 0.05 deg (primary, seasonal), V6GL03 monthly 0.1 deg.

Outputs
    data/processed/unit_year_sat.parquet    unit_id, product, year, pm25_popw, pm25_area, pm25_sd, pop, cells
    data/processed/unit_month_sat.parquet   unit_id, product, year, month, pm25_popw, pm25_area
    data/processed/station_year_sat.parquet sid, product, year, pm25_cell (value of the 0.01 deg cell
                                            holding the station; station-level coordinates only)

    python -m src.clean.zonal
"""

import glob
import re
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import rioxarray  # noqa: F401 - registers the .rio accessor
import xarray as xr
from exactextract import exact_extract
from rasterio.enums import Resampling

from src.clean.station_meta import load_stations
from src.common.paths import INTERIM, PROCESSED, raw_dir

BBOX = (68.0, 6.0, 98.0, 38.0)  # lon_min, lat_min, lon_max, lat_max (DEC-004)
WORK = INTERIM / "zonal"
UNITS = INTERIM / "sat_units.gpkg"
POP_ZIP = raw_dir("ghsl") / "GHS_POP_E2020_GLOBE_R2023A_4326_30ss_V1_0.zip"
POP_TIF = "GHS_POP_E2020_GLOBE_R2023A_4326_30ss_V1_0.tif"
PRODUCTS = {
    # name: (glob under data/raw/acag, variable, frequency)
    "V5GL06": ("V5GL06/GWRPM25/Annual/Asia/*.nc", "GWRPM25", "annual"),
    "V6GL03": ("V6GL03/CNNPM25/Annual/AS/*.nc", "PM25", "annual"),
    "V6GL0204": ("V6GL0204/CNNPM25/Annual/AS/*.nc", "PM25", "annual"),
    "V5GL06_monthly": ("V5GL06/GWRPM25c0p05/Monthly/Asia/*.nc", "GWRPM25", "monthly"),
    "V6GL03_monthly": ("V6GL03/CNNPM25c0p10/Monthly/AS/*.nc", "PM25", "monthly"),
}


def period(path: str) -> tuple[int, int | None]:
    """'...Asia.200501-200512.nc' -> (2005, None); '...200503-200503.nc' -> (2005, 3)."""
    a, b = re.search(r"(\d{6})-(\d{6})\.nc$", path).groups()
    return int(a[:4]), (None if a[4:] == "01" and b[4:] == "12" else int(a[4:]))


def load_acag(path: str, var: str) -> xr.DataArray:
    """One ACAG grid cropped to India, as a georeferenced DataArray (EPSG:4326)."""
    da = xr.open_dataset(path)[var]
    da = da.sortby("lat", ascending=False).sel(
        lon=slice(BBOX[0], BBOX[2]), lat=slice(BBOX[3], BBOX[1])
    )
    da = da.rename({"lon": "x", "lat": "y"}).rio.write_crs(4326)
    return da.astype("float32").rio.write_nodata(np.nan)


def pop_on_grid(template: xr.DataArray) -> xr.DataArray:
    """GHS-POP 2020 summed onto the template grid (people per cell)."""
    pop = rioxarray.open_rasterio(f"/vsizip/{POP_ZIP.as_posix()}/{POP_TIF}", masked=True).squeeze(
        "band", drop=True
    )
    pop = pop.rio.clip_box(*BBOX)
    out = pop.rio.reproject_match(template, resampling=Resampling.sum)
    return out.where(out > 0, 0).astype("float32")


def _tif(da: xr.DataArray, name: str) -> Path:
    WORK.mkdir(parents=True, exist_ok=True)
    p = WORK / f"{name}.tif"
    da.rio.to_raster(p)
    return p


def zonal(units: gpd.GeoDataFrame, value_tif: Path, pop_tif: Path) -> pd.DataFrame:
    r = exact_extract(
        str(value_tif), units, ["mean", "weighted_mean", "stdev", "count"], weights=str(pop_tif),
        include_cols=["unit_id"], output="pandas",
    )  # fmt: skip
    p = exact_extract(str(pop_tif), units, ["sum"], include_cols=["unit_id"], output="pandas")
    r = r.merge(p.rename(columns={"sum": "pop"}), on="unit_id")
    return r.rename(
        columns={
            "mean": "pm25_area",
            "weighted_mean": "pm25_popw",
            "stdev": "pm25_sd",
            "count": "cells",
        }
    )


def station_cells(stations: pd.DataFrame, da: xr.DataArray) -> np.ndarray:
    return da.sel(
        x=xr.DataArray(stations.lon.to_numpy()),
        y=xr.DataArray(stations.lat.to_numpy()),
        method="nearest",
    ).to_numpy()


def main() -> None:
    units = gpd.read_file(UNITS)
    stations = load_stations()
    stations = stations[stations.coord_is_station_level]
    pops: dict[tuple, Path] = {}
    ann, mon, st_rows = [], [], []
    for name, (pat, var, freq) in PRODUCTS.items():
        files = sorted(glob.glob(str(raw_dir("acag") / pat)))
        for f in files:
            year, month = period(f)
            da = load_acag(f, var)
            key = (da.sizes["x"], da.sizes["y"], float(da.x[0]), float(da.y[0]))
            if key not in pops:
                pops[key] = _tif(pop_on_grid(da), f"pop_{len(pops)}")
            vt = _tif(da, "value")
            z = zonal(units, vt, pops[key]).assign(product=name.replace("_monthly", ""), year=year)
            if freq == "annual":
                ann.append(z)
                st_rows.append(
                    pd.DataFrame(
                        {
                            "sid": stations.sid.to_numpy(),
                            "product": name,
                            "year": year,
                            "pm25_cell": station_cells(stations, da),
                        }
                    )
                )
            else:
                mon.append(
                    z.assign(month=month)[
                        ["unit_id", "product", "year", "month", "pm25_popw", "pm25_area"]
                    ]
                )
            print(name, year, month or "", flush=True)
    PROCESSED.mkdir(parents=True, exist_ok=True)
    pd.concat(ann, ignore_index=True).to_parquet(PROCESSED / "unit_year_sat.parquet", index=False)
    pd.concat(mon, ignore_index=True).to_parquet(PROCESSED / "unit_month_sat.parquet", index=False)
    pd.concat(st_rows, ignore_index=True).to_parquet(
        PROCESSED / "station_year_sat.parquet", index=False
    )


if __name__ == "__main__":
    main()

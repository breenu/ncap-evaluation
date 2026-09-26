"""ERA5 weather from the Copernicus CDS (DEC-004, DEC-035). Key in ~/.cdsapirc.

1. Hourly point time series (reanalysis-era5-single-levels-timeseries) for every 0.25 degree
   grid point that holds a station (data/interim/station_crosswalk.csv), over the ground
   window. The request is made at the grid point itself, so the returned cell is unambiguous.
   -> data/raw/era5_timeseries/era5ts_<lat>_<lon>.zip
2. Monthly means (reanalysis-era5-single-levels-monthly-means) for an India bounding box over
   the satellite download years, for the satellite layer.
   -> data/raw/era5_monthly/era5_monthly_india_<y0>_<y1>.zip

Never downloads hourly ERA5 for all of India (CLAUDE.md hard rule 6).

    python -m src.acquire.era5 [--points-only | --monthly-only]
"""

import argparse
import hashlib
import json
from pathlib import Path

import pandas as pd

from src.acquire.common import finish, run_parallel
from src.common.manifest import download
from src.common.paths import INTERIM, params, raw_dir

TS_DATASET = "reanalysis-era5-single-levels-timeseries"
MONTHLY_DATASET = "reanalysis-era5-single-levels-monthly-means"
VARIABLES = [
    "2m_temperature",
    "2m_dewpoint_temperature",
    "10m_u_component_of_wind",
    "10m_v_component_of_wind",
    "boundary_layer_height",
    "total_precipitation",
    "surface_solar_radiation_downwards",
]
INDIA_AREA = [38, 68, 6, 98]  # N, W, S, E


def request_id(dataset: str, request: dict) -> str:
    blob = json.dumps({"dataset": dataset, **request}, sort_keys=True).encode()
    return "cds-request-sha256:" + hashlib.sha256(blob).hexdigest()[:16]


def cds_fetch(dataset: str, request: dict):
    def fetch(url: str, tmp: Path) -> None:
        import cdsapi

        cdsapi.Client(quiet=True, progress=False).retrieve(dataset, request, str(tmp))

    return fetch


def station_cells(crosswalk: Path | None = None) -> list[tuple[float, float]]:
    x = pd.read_csv(crosswalk or INTERIM / "station_crosswalk.csv")
    cells = x.dropna(subset=["era5_lat", "era5_lon"])[["era5_lat", "era5_lon"]].drop_duplicates()
    return sorted((float(a), float(b)) for a, b in cells.itertuples(index=False))


def point_tasks(dest: Path) -> list:
    w = params()["windows"]
    tasks = []
    for lat, lon in station_cells():
        request = {
            "variable": VARIABLES,
            "location": {"latitude": lat, "longitude": lon},
            "date": [f"{w['ground_start']}/{w['ground_end']}"],
            "data_format": "csv",
        }
        name = f"era5ts_{lat:.2f}_{lon:.2f}.zip"
        tasks.append(
            lambda name=name, request=request: download(
                dest,
                name,
                f"cds:{TS_DATASET}",
                remote_id=request_id(TS_DATASET, request),
                notes=json.dumps(request["location"]),
                fetch=cds_fetch(TS_DATASET, request),
            )
        )
    return tasks


def monthly_task(dest: Path):
    y0, y1 = params()["windows"]["satellite_download_years"]
    request = {
        "product_type": ["monthly_averaged_reanalysis"],
        "variable": VARIABLES,
        "year": [str(y) for y in range(y0, y1 + 1)],
        "month": [f"{m:02d}" for m in range(1, 13)],
        "time": ["00:00"],
        "area": INDIA_AREA,
        "data_format": "netcdf",
        "download_format": "zip",
    }
    name = f"era5_monthly_india_{y0}_{y1}.zip"
    return lambda: download(
        dest,
        name,
        f"cds:{MONTHLY_DATASET}",
        remote_id=request_id(MONTHLY_DATASET, request),
        notes=f"area N,W,S,E = {INDIA_AREA}",
        fetch=cds_fetch(MONTHLY_DATASET, request),
    )


def main() -> None:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--points-only", action="store_true")
    ap.add_argument("--monthly-only", action="store_true")
    ap.add_argument("--workers", type=int, default=4)
    args = ap.parse_args()
    if not args.points_only:
        d = raw_dir("era5_monthly")
        finish(d, "era5_monthly", run_parallel([monthly_task(d)], 1, "era5_monthly"))
    if not args.monthly_only:
        d = raw_dir("era5_timeseries")
        tasks = point_tasks(d)
        print(f"era5_timeseries: {len(tasks)} grid points")
        finish(d, "era5_timeseries", run_parallel(tasks, args.workers, "era5_timeseries"))


if __name__ == "__main__":
    main()

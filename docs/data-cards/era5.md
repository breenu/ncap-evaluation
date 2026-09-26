# Data card: ERA5 reanalysis (ECMWF, via the Copernicus Climate Data Store)

**Role:** weather inputs for deweathering (RQ2) and weather covariates for the satellite layer (RQ3). DEC-004, DEC-035.

| | Point time series | Monthly means |
|---|---|---|
| CDS dataset | `reanalysis-era5-single-levels-timeseries` | `reanalysis-era5-single-levels-monthly-means` (`monthly_averaged_reanalysis`) |
| Where | every 0.25° grid point holding a station (from `data/interim/station_crosswalk.csv`; 283 points), requested at the grid point itself | India box N38 W68 S6 E98 |
| When | 2015-01-01 to 2026-03-31, hourly | 2005–2024, monthly |
| Raw file | `data/raw/era5_timeseries/era5ts_<lat>_<lon>.zip` (CSV) | `data/raw/era5_monthly/era5_monthly_india_2005_2024.zip` (NetCDF) |

Variables: 2 m temperature and dew point, 10 m u/v wind, boundary-layer height, total precipitation, surface solar radiation downwards.

| | |
|---|---|
| Access | CDS account; key in `~/.cdsapirc` (never in the repo) |
| Licence | Copernicus licence: free use with attribution ("Contains modified Copernicus Climate Change Service information") |
| Upstream id | hash of the CDS request (the product has no file checksum); sha256 in the manifest |
| Time zone | UTC. `ssrd` and `tp` at time T are accumulated over the hour ending at T. |

## Verified

- Delhi test: complete hourly series, no gaps or NaNs (DEC-035, `docs/data-probe.md`).
- Used as the third, independent test of the mirror's clock: station solar radiation vs ERA5 `ssrd`, correlation about 0.93 (DEC-040).

## Known issues

- `ssrd` has tiny negative values (min about −2 J/m²): clip at 0 in Phase 5.
- 0.25° (~28 km) misses urban and coastal micro-meteorology (risk R13).
- 19 stations have no coordinates yet (DEC-045); their cells are added in Phase 3.
- The local network's DNS intermittently failed for the CDS hosts on 2026-09-26; `cdsapi` retries.

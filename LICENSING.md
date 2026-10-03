# Licensing

This repository holds three kinds of material under three licences.

| What | Where | Licence |
|---|---|---|
| Code: the pipeline, tests, workflow and configuration | `src/`, `tests/`, `workflow/`, `Snakefile`, `config/`, `.github/`, `envs/`, environment and lock files | MIT ([`LICENSE`](LICENSE)) |
| Text and figures: the report, results summary, policy brief, documentation and every figure | `reports/`, `docs/`, `dashboard/` pages and images, `README.md` | CC BY 4.0 ([`LICENSE-CC-BY-4.0.txt`](LICENSE-CC-BY-4.0.txt)) |
| Ground-derived data: any table derived from the CPCB station data | e.g. `dashboard/data/` ground series and the tables in `reports/_generated/` | ODbL 1.0 ([`LICENSE-ODbL-1.0.txt`](LICENSE-ODbL-1.0.txt)) |
| Other derived data (satellite, weather and city-level tables) | e.g. `dashboard/data/` satellite and city-level series | CC BY 4.0, with the source attributions below |

## Ground data notice (ODbL)

The ground data come from `india-cpcb-aqi` (<https://github.com/Vonter/india-cpcb-aqi>), a mirror of the Central Pollution Control Board's data repository, which is made available under the Open Database License 1.0; some individual contents are © CPCB. Figures and tables made from it contain information from that database. The adapted station data, and the method that produced them (the code in this repository), are made available under the ODbL 1.0, as the licence requires for works produced from an adapted database.

## Attributions

- ACAG satellite PM2.5, Washington University in St. Louis (CC BY 4.0). Cite van Donkelaar et al. (2021), Hammer et al. (2023) and Zhang et al. (2025); full references are in the technical report.
- Contains modified Copernicus Climate Change Service information (2026): ERA5, Hersbach et al. (2020) (CC BY 4.0).
- GHSL Urban Centre Database R2024A and GHS-POP R2023A, © European Union 1995–2026 (CC BY 4.0). Polygons were joined into units and population-weighted means computed.
- India boundaries by the DataMeet India community (CC BY 4.0).
- GeoNames (CC BY 4.0); Natural Earth (public domain).
- NASA LANCE FIRMS (<https://earthdata.nasa.gov/firms>), part of the NASA Earth Science Data and Information System (ESDIS); MODIS MAIAC MCD19A2 v061, NASA LP DAAC. NASA open data.
- OpenAQ (<https://openaq.org>) and the original data providers.

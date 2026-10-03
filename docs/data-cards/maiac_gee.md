# Data card: MODIS MAIAC aerosol optical depth, reduced on Google Earth Engine

**Role:** the registered "if time allows" check under the calibration-leakage threat (plan §5). This is a satellite aerosol signal that no ground monitor calibrates. Phase 8b; rules DEC-174 to DEC-185.

| | |
|---|---|
| Product | MCD19A2 Collection 6.1 (MODIS Terra + Aqua MAIAC land AOD), GEE collection `MODIS/061/MCD19A2_GRANULES`: one image per tile and overpass, 1 km sinusoidal grid (SR-ORG:6974, 926.6 m) |
| Band and QA | `Optical_Depth_055` × 0.001 (valid −0.1 to 8.0; negatives kept). Primary filter: land, cloud mask clear, adjacency normal, AOD QA best. Relaxed filter as a sensitivity check (DEC-175) |
| Weights | GHS-POP R2023A epoch 2020, 100 m (`JRC/GHSL/P2023A/GHS_POP/2020`), summed onto the MODIS grid. Same release and epoch as our 30″ file; per-unit totals differ by a median of +3.4% (DEC-176 check passed) |
| Reduction | Daily mean of each pixel's valid overpasses, then the pixel-month mean and valid-day count, then coverage-weighted sums over each of the 1,036 Layer A polygons (`src/acquire/maiac_gee.py`) |
| What is stored | Sums, not means: per unit and month, Σw·c, Σc, and the valid-pixel sums of w·c, w·c·AOD and w·c·days for each filter (columns in the script's docstring). Means are formed locally in `src/causal/maiac.py` |
| Coverage | January 2010 – December 2024, 1,036 units × 180 months |
| Raw layout | `data/raw/maiac_gee/maiac_unit_month_<year>.csv` (15 files, 38.2 MB) plus `MANIFEST.csv`. Each row records: the Drive file id and md5 (checked at download), the Earth Engine task id, the commit and sha256 of the script, the sha256 of the request, the compute used, and the full request parameters |
| Route | `Export.table.toDrive` into a private Drive folder `ncap_maiac_gee`, then a download through the Drive API. The project has no Earth Engine asset area (DEC-183) |
| Compute | 167.9 EECU-hours for the 15 yearly tasks, plus 2.8 for two one-month pilots, on the Contributor tier (DEC-185) |
| Licence | LP DAAC: no restriction on use or redistribution. GHSL: CC BY 4.0 |

## Verified on 2026-10-03

- QA bit layout: identical in the MCD19 C6.1 user guide (§5.4) and the GEE catalogue (DEC-174).
- Collection structure, band type, projection and the 9 Indian tiles: `data/interim/maiac_gee/check.json`. The tile list matches the tiles touched by the units' bounding boxes.
- Restricting to those 9 tiles changes no value: two pilot tables agree to within 4 × 10⁻⁸ relative (DEC-184).

## Known issues

- **Earth Engine reruns are not byte-identical.** Population-weighted sums can differ in about the 8th significant figure, from floating-point order in Earth Engine's resampling. A re-download of the same exported file is identical; a re-export may not be.
- **Clear-sky only.** Best-quality retrievals need cloud-free skies. July–August unit-months are valid only 4–8% of the time; see `docs/causal_report.md` §12a.
- **Satellite overpass drift.** Terra's and Aqua's overpass times drifted late in the record.
- **AOD is a column measure, not surface PM2.5.** Results are read for direction only (DEC-180).
- **Reproducing from scratch** needs Earth Engine credentials for a registered noncommercial project, and about 170 EECU-hours.

# Scoping note: the raw MAIAC AOD check (registered "if time allows")

*Written 2026-10-02, end of Phase 8. Nothing has been downloaded. This is a planning note, like `PLAN.md`: sizes and run times are estimates, labelled as such, not pipeline results. Product facts were checked against the sources listed at the end on 2026-10-02.*

## Why the check exists

ACAG's satellite PM2.5 is calibrated to ground monitors, and NCAP added monitors mainly in listed cities. Phase 7's pre-specified calibration-leakage warning fired (DEC-151): units that gained a monitor showed a smaller relative rise (+2.5%) than units that did not (+5.5%), a difference of −2.8% (CI −5.1% to −0.5%).

The registered plan (§5) names one independent check: raw MODIS MAIAC aerosol optical depth (AOD). It is a satellite retrieval that uses no ground PM monitors. The question it answers: **does the post-2018 relative rise of NCAP units, and its split by monitor gain, also appear in a signal that no monitor could have calibrated?**

AOD is not PM2.5. It is a column quantity, and its link to surface PM depends on boundary-layer height, humidity and aerosol type. So the check compares the *direction and pattern* of the relative changes, never their size in µg/m³.

## Product and resolution that would work

**MCD19A2 Collection 6.1 (MODIS Terra + Aqua MAIAC land AOD).**
- Daily, 1 km, on the MODIS sinusoidal tile grid, HDF-EOS2.
- Available from 24 February 2000 to the present.
- Bands: `Optical_Depth_055` (0.55 µm), plus the `AOD_QA` bitmask (cloud mask, adjacency, quality).
- Access: NASA Earthdata login, or Google Earth Engine (`MODIS/061/MCD19A2_GRANULES`, free for research with registration).
- LP DAAC data carry no restriction on use or redistribution.

**Why 1 km.**
- The study's units are GHSL urban centres. Their mean areas are about 210 km² (NCAP units) and 48 km² (controls), and the smallest are around 10 km².
- At 1 km, every unit has tens to thousands of pixels, and the satellite layer can be built exactly like ACAG's: population-weighted mean over the polygon, then the annual mean (DEC-070).
- The leakage concern works at the scale of a city and its monitors, so the check must resolve cities.

**Processing it would need.**
- Keep best-quality retrievals (`AOD_QA` QA = best, cloud mask clear).
- Average both overpasses per day, then form unit-month and unit-year means.
- Set a minimum number of valid days per unit-month. Monsoon cloud removes many July–August retrievals, so the rule must be fixed before looking.
- Then run the Phase 7 SDID design unchanged on log AOD:
  - the primary specification;
  - the gained/not-gained leakage split with its joint-placebo SE.
- Rules would be written in DECISIONS before anything is computed, as in every phase.

## Download size for India, 2010–2024

The 1,036 analysis units (113 treated, 923 controls) fall in **9 MODIS tiles**: h24v05, h24v06, h24v07, h25v06, h25v07, h25v08, h26v06, h26v07, h27v07. This was computed from the unit polygons in `data/interim/sat_units.gpkg` with the standard sinusoidal tile formula. Their total area is about 70,300 km² (NCAP units 24,700 km²).

| Route | What is downloaded | Estimated size | Status |
|---|---|---|---|
| A. Full granules (Earthdata) | 9 tiles × 5,479 days (2010–2024) = 49,311 HDF files | ≈ **330 GB** at the catalogue's 6.7 MB per granule | Far above the 2 GB threshold (hard rule 6), and above the ~169 GB free disk. It would have to be streamed: download a granule, extract the unit pixels, delete it. |
| B. Polygon subset (NASA AppEEARS area request) | `Optical_Depth_055` + `AOD_QA`, clipped to the unit polygons | Not verified. A rough floor is 70,300 px × 2 bands × 2 bytes × 5,479 days ≈ 1.5 GB of pixel data; the GeoTIFF overhead and masked extent depend on how AppEEARS handles 1,036 separate polygons. | AppEEARS's request limits (number of features, area, duration) could not be confirmed from its documentation today. Test one month first. |
| C. Server-side reduction (Google Earth Engine) | Only a table: unit × day (or month) mean AOD and valid-pixel count | ≈ 1,036 units × 5,479 days × a few fields ≈ **< 0.5 GB** as CSV (≈ 15 MB at unit-month) | Needs a GEE account and the `earthengine-api` package (not in the locked environment). The exported table would be the "raw" file, with a manifest. The pixel-level QA filtering would run on Google's servers, from a committed script. |

## Run time on this laptop

These are estimates. They assume mains power: on battery, Windows throttled Phase 8's R workers to about a tenth of normal speed (2026-10-02).

- **Route A:** the download dominates. 330 GB takes about 15 h at 50 Mbit/s, or about 37 h at 20 Mbit/s. Reading and zonal-averaging 49,000 granules (1,200 × 1,200 pixels each) takes roughly 1 s per granule per core, so about 2 h on 8 workers. It is feasible over two or three days of downloading, but it is the most fragile route.
- **Route B:** AppEEARS processes the request on NASA's side, typically hours to a day for a request this size (not verified). The local download is minutes to an hour. Local aggregation is under an hour.
- **Route C:** GEE export jobs of this kind typically take 1–3 h server-side (not verified). The local download is seconds.
- **All routes:** the SDID step itself is about 1–1.5 h on mains power: the primary and the leakage split, 500 joint-placebo replications each, on one outcome. The pace is Phase 7's measured 0.38 s per fit with 8 workers.

## Would a coarser or monthly product still test calibration leakage?

| Alternative | Resolution | Verdict |
|---|---|---|
| **MCD19A2CMG C6.1** (MAIAC, daily, 0.05° ≈ 5.6 km) | about 30 km² cells | **Usable as a fallback, with a stated dilution.** Most controls (≈ 48 km²) are only 1–3 cells, so their values mix the town with its surroundings; NCAP cities are mostly resolved. Treated and control values would both be diluted towards the regional background, which biases the contrast towards zero rather than creating one. But the files are global (≈ 50 MB per day, so ≈ 274 GB for 2010–2024) unless a subsetting service is used, so it does not save download. |
| MOD08_M3 / MYD08_M3 (Dark Target/Deep Blue, monthly, 1°) | about 110 km cells | **No.** One cell holds a city, its suburbs and often several control towns, and many units share a cell. Treated–control contrasts at city scale would be mostly washed out. It also is not MAIAC. |
| Monthly composites of MAIAC 1 km (made by us from daily data, e.g. in GEE) | 1 km | **Yes:** the same test. Monthly is enough, because the outcome is annual. Monthly only reduces what is stored, not what has to be read. |
| MERRA-2 AOD reanalysis | 0.5° × 0.625° | **No.** Too coarse for the same reason, and it assimilates MODIS AOD, so it is not an independent retrieval. |

**Recommendation, if the check is run:**
1. Try Route C (GEE server-side reduction of MCD19A2 1 km to unit-month means), or Route B if Reenu prefers to stay within NASA's own services.
2. Write the QA, valid-day and aggregation rules in DECISIONS first.
3. Then run the primary SDID and the leakage split on log AOD.

Route A is only worth it if neither service is acceptable. The 0.05° CMG product is the fallback if 1 km access fails. Coarser monthly products would not test leakage at city scale.

**What the check can and cannot show.**
- If the post-2018 relative rise and its gained/not-gained pattern also appear in raw AOD, calibration leakage is an unlikely explanation for the Layer A numbers.
- If they vanish in AOD, leakage becomes more plausible, but AOD's own changes (humidity, boundary layer, aerosol mix) are an alternative explanation.
- Either way, H1 stays "not identified": the registered verdict rests on the failed pre-trend test, which this check does not touch.

## Sources (checked 2026-10-02)

- [NASA Earthdata, MCD19A2 V061](https://www.earthdata.nasa.gov/data/catalog/lpcloud-mcd19a2-061): daily, 1 km, sinusoidal grid, 2000-02-24 to present, HDF-EOS2, 6.7 MB, Earthdata login.
- [LP DAAC, MCD19A2CMG V061](https://lpdaac.usgs.gov/products/mcd19a2cmgv061/) and [Earthdata catalogue](https://www.earthdata.nasa.gov/fr/data/catalog/lpcloud-mcd19a2cmg-061): daily 0.05° CMG, about 50 MB per file.
- [Google Earth Engine, MODIS/061/MCD19A2_GRANULES](https://developers.google.com/earth-engine/datasets/catalog/MODIS_061_MCD19A2_GRANULES): 1 km, granule-level, `Optical_Depth_055`, `AOD_QA`, no restriction on use (LP DAAC), registration required.
- [MCD19 C6.1 user guide](https://lpdaac.usgs.gov/documents/1500/MCD19_User_Guide_V61.pdf).
- [NASA AppEEARS](https://appeears.earthdatacloud.nasa.gov/): area requests by polygon (shapefile/GeoJSON). Request limits were not confirmed.

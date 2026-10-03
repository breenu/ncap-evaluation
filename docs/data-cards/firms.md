# Data card: NASA FIRMS active fires (VIIRS S-NPP)

**Role:** fire covariate in one robustness check (crop-burning shocks in IGP cities). Lowest priority: cut item #4. DEC-039 (supersedes DEC-010).

| | |
|---|---|
| Product | VIIRS S-NPP 375 m active fires, India; version field `2` throughout 2012–2024 |
| 2012–2024 | keyless yearly country files `data/country/viirs-snpp/<y>/viirs-snpp_<y>_India.csv` |
| 2025 – Mar 2026 | country API with the MAP_KEY (`.env`), 5-day requests; standard processing where available, near-real-time after |
| Raw layout | `data/raw/firms/archive/…`, `data/raw/firms/api/<source>_<start>.csv`; the key is recorded as `<MAP_KEY>` |
| Licence | NASA open data; cite FIRMS (LANCE/ESDIS) |

## Status

**2012–2024 downloaded on 2026-10-03 and used** (DEC-172): the 13 yearly VIIRS S-NPP India files (566 MB), checksum-verified and recorded in `data/raw/firms/MANIFEST.csv`. They feed the registered fire-covariate check (DEC-171).

**January 2025 – March 2026 not downloaded** (DEC-172, DEC-173): FIRMS's country API returned HTTP 400 for every request, and no analysis needs those months, because the satellite layer ends in 2024.

*(Status updated 2026-10-03, Phase 10. Until then this card recorded the earlier status, "not downloaded yet", from 2026-09-26, when the FIRMS host was unreachable.)*

## Why not MODIS

The keyless MODIS archive changes processing version in 2018 (`6.2` → `6.03`) and 2023 (`→ 61.03`). The 2018 break sits just before NCAP and could put an artificial step into the covariate (DEC-036). It could not be checked whether the MAP_KEY standard-processing API avoids the break, so VIIRS is used and the fire check starts in 2012.

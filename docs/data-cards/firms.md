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

**Not downloaded yet.** `firms.modaps.eosdis.nasa.gov` is unreachable from the current network (connect timeout, IPv4 and IPv6, 2026-09-26), though it answered from the phone hotspot earlier that day. `python -m src.acquire.firms` runs as soon as the host is reachable.

## Why not MODIS

The keyless MODIS archive changes processing version in 2018 (`6.2` → `6.03`) and 2023 (`→ 61.03`). The 2018 break sits just before NCAP and could put an artificial step into the covariate (DEC-036). It could not be checked whether the MAP_KEY standard-processing API avoids the break, so VIIRS is used and the fire check starts in 2012.

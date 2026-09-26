# Data card: OpenAQ (India, reference monitors)

**Role:** ground source for Jan–Mar 2026 and an independent copy of CPCB data for cross-checking the mirror (DEC-037); station coordinates for the crosswalk (DEC-045).

| | |
|---|---|
| Publisher | OpenAQ (aggregator; Indian data mostly from CPCB, plus AirNow/StateAir, Clean Air Catalyst and others) |
| Access | location metadata: v3 API (`/v3/locations?iso=IN`, key in `.env`); measurements: public S3 bucket `openaq-data-archive`, `records/csv.gz/locationid=<id>/year=<y>/month=<m>/location-<id>-<yyyymmdd>.csv.gz` |
| Licence | per provider, recorded in the location metadata; CPCB data are Government of India open data |
| Selection | locations with `isMonitor` true, not mobile, with a PM2.5 or PM10 sensor (640 in the 2026-09-26 snapshot; see `docs/data-probe.md`) |
| Window | 2015-01-01 to 2026-03-31 |
| Raw layout | `locations_IN_<date>.json` (API snapshot); `locationid=<id>/year=<y>.zip`, the day files stored uncompressed and byte-identical, plus `_index.csv` (key, ETag, bytes, sha256), one manifest row per zip (DEC-041) |
| Integrity | each day file checked against its S3 MD5 ETag; zip sha256 in the manifest |
| Timestamps | ISO 8601 with explicit offset (`+05:30`); these are the reference for the mirror's clock (DEC-040) |

## Verified

- Coverage by year and provider: `docs/data-probe.md`. Almost no CPCB data for 2023–2024 (DEC-030).
- 2025 15-minute values are identical to the mirror's at matched stations after the mirror's clock correction.

## Known issues

- One physical station appears under several location ids (provider changes, re-registrations), and some of these ids disagree on coordinates by up to 30 km (DEC-045).
- ~~The pre-2023 CPCB feed matches the mirror's clock but not its values exactly (about 2% identical at the best offset in 2019–2021).~~ *Corrected in Phase 3 (DEC-057):* that figure came from a sample dominated by IMD-operated stations. Across all 1,608 overlapping station-years, 2019–2021 values are identical to the mirror's (median 100%). IMD stations differ at 15 minutes but agree on daily means (median 0.4%). 2016–17 and March–October 2022 differ slightly. See `docs/mirror-openaq-crosscheck.md`.
- **March 2018: OpenAQ's "PM2.5" is not a concentration.** In that month, across 64 stations, it correlates with the mirror's value at the same time at only r = 0.46 and differs by a median 55 µg/m³. It tracks the mirror's trailing 24-hour mean at r = 0.95 and lies a median 8 index points from CPCB's AQI sub-index of that mean. It behaves like a 24-hour AQI-type index stored under a concentration label. February and April 2018 match the mirror again. Do not use OpenAQ PM2.5 for March 2018 (DEC-057; `docs/mirror-openaq-crosscheck.md` §5).
- **Unit labels are wrong from 2025.** NO2 is labelled `ppb` but is identical to the mirror's µg/m³ values (median exact share 100%, ratio 1.000), so it is treated as µg/m³ (DEC-056). CO is labelled `ppb` but reads on CPCB's mg/m³ scale (not used). Ingest keeps OpenAQ's labels as published and does not drop rows for units.
- **Some location ids carried another station's data for part of their life** (e.g. R K Puram and Punjabi Bagh, Delhi, ids 6357/7044). Station identity is therefore settled by identical values, not by names or ids (DEC-058; `docs/station_metadata_review.md`).
- 2021–22: fewer than half of site-months with any data have 75% of days.

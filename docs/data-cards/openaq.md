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
- The pre-2023 CPCB feed matches the mirror's clock but not its values exactly (about 2% identical at the best offset in 2019–2021), so treat it as a related series, not a copy, when cross-checking.
- 2021–22: fewer than half of site-months with any data have 75% of days.

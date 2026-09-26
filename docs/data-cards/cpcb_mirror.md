# Data card: CPCB CAAQMS station data (via the Vonter/india-cpcb-aqi mirror)

**Role:** main ground source, 2015–2025 (DEC-037). The raw material for the station audit (RQ1), deweathering (RQ2) and the ground layer (RQ3 Layer B).

| | |
|---|---|
| Original publisher | Central Pollution Control Board (CPCB), Continuous Ambient Air Quality Monitoring Stations (CAAQMS), "Data Repository" of the CCR portal |
| What we download | `github.com/Vonter/india-cpcb-aqi` release assets `cpcb-air-quality-<year>.parquet`, 2015–2025 (releases published 2026-01-07) |
| Why a mirror | CPCB's repository endpoints (`airquality.cpcb.gov.in/dataRepository/…`) return 404 since at least 2026-09-26 (DEC-031); OpenAQ lacks 2023–24 (DEC-030) |
| Licence | Open Database License 1.0 (mirror); "some individual contents … under copyright by CPCB". Any derived dataset we publish must be ODbL and attribute the mirror and CPCB. Code licence is separate. |
| Provenance saved | `data/raw/cpcb_mirror/repo@a58f478/` (README, DATA.md, LICENSE, fetch.py, parse.py, requirements.txt at the commit that built the releases) |
| Integrity | every file matches GitHub's published sha256 digest; sha256 in `data/raw/cpcb_mirror/MANIFEST.csv` |
| Resolution | 15-minute; one row per station per 15-minute slot (padded: rows exist where nothing was measured) |
| Variables used | `PM2.5 (µg/m³)`, `PM10 (µg/m³)`; `NO2 (µg/m³)` (secondary); `SR (W/mt2)` and the met columns only for checks |
| Station identity | `Station ID` (CPCB `site_NNNN`, one stable name per id); no coordinates, which come from the OpenAQ crosswalk (DEC-045) |

## Verified

- **Timestamps are not UTC.** The stored instants are Indian clock times stamped as UTC (the mirror's `parse.py` uses `replace_time_zone("UTC")` without converting), so true UTC = stored − 5.5 h, constant 2015–2025, on three independent tests (DEC-054, which corrects DEC-040's "11 h"; `docs/mirror-checks.md`). Read the file with DuckDB `TimeZone='UTC'` (or pyarrow), never in the machine's local zone. Ingest subtracts `mirror.stored_minus_utc_hours` from `config/params.yaml`.
- **Values are CPCB's.** 15-minute PM2.5 values are identical to OpenAQ's independent copy of CPCB data at matched stations. The exceptions are explained: IMD-operated stations differ quarter-hour by quarter-hour but agree on daily means within a fraction of a percent, and OpenAQ's March 2018 PM2.5 is an index, not a concentration (`docs/mirror-openaq-crosscheck.md`, DEC-057).
- **Metadata errors.** Three MPCB Aurangabad stations are labelled Bihar; corrected in `config/station_overrides.yaml` (DEC-060). No station coordinates.
- **Station-years with valid PM2.5/PM10**, by year: see `docs/mirror-checks.md` §2. The network before 2018 is small in every source (DEC-033).

## Known issues

- One step removed from CPCB; the mirror could change. Pinned by release asset id and sha256; a changed asset is refused (DEC-042).
- No 2026 data; Jan–Mar 2026 comes from OpenAQ.
- Padded rows: count non-null values, never rows.
- Some stations' solar sensors or clocks disagree with the rest (lowest decile of the solar test), flagged for the Phase 3 audit.
- Rows with a label year one greater than the file's year exist at year ends (a consequence of the shifted clock).

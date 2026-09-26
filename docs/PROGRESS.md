# PROGRESS

Handoff file: a fresh session should be able to continue from this alone.
Read with [`PLAN.md`](PLAN.md) (what and how), [`DECISIONS.md`](DECISIONS.md) (why) and `CLAUDE.md` (rules).

*Last updated: 2026-09-26. Phase 3 part A done (ingest, cross-check, station metadata, NCAP-UCDB matching); **stopped at the checkpoint for Reenu's review**. Part B (audit flags, reliability, EDA, analysis plan) not started.*

## Status

| Phase | State |
|---|---|
| 0 Plan | ✅ approved 2026-09-26 (answers in PLAN.md §8) |
| 1 Skeleton | ✅ approved 2026-09-26; pushed; CI green |
| 2 Acquisition | ✅ approved 2026-09-26; pushed. FIRMS pending (Reenu will run it from another network with a new key) |
| 3 Storage, cleaning, audit, EDA | 🟡 part A done, at checkpoint (see "Phase 3 checkpoint" below) |
| 4–10 | not started |

Pre-registration gate: **closed** (`config/gate.yaml`). No post-2019 effect estimates exist.

## Done

- **Phase 0:** `docs/PLAN.md`; review answers recorded; DEC-001 to DEC-021.
- **Phase 1:**
  - Miniforge installed at `%USERPROFILE%\miniforge3`. Env `ncap` has Python 3.12.14 and R 4.5, pinned in `conda-lock.yml` for win-64 and linux-64.
    The local env was rebuilt from the lock file (`conda-lock install -n ncap conda-lock.yml`), and all checks were re-run on it.
  - R extras (did, DRDID, fastglm, synthdid) are installed by `workflow/scripts/install_r_extra.R` (DEC-022).
  - Snakemake DAG: 9 stub stages plus `pregate` and `all` targets. `all` stops at the gate (tested).
  - `src/common/`: `paths.py`, `manifest.py` (idempotent downloads, immutable raw data), `gate.py`.
  - Config: `params.yaml` (undecided thresholds are `null`, DEC-024), `gate.yaml`, `regions.yaml` (draft).
  - Tests: 41 passing. They cover gate, manifest, heavy imports, and R estimators actually running.
  - CI: `.github/workflows/tests.yml` on the private repo `breenu/ncap-evaluation`.
    - First run failed: `fastglm` source build on Linux lacked the RcppEigen/BH headers.
    - Fixed in `dd31f52` by adding `r-rcppeigen` and `r-bh` (lock diff: only those two added).
    - Run 36187837666 passed: 41 tests, none skipped, R estimators ran on Linux.
  - Phase note: `docs/phase-notes/01-skeleton.md`.
- **Phase 2, step 0 (feasibility probe):**
  - Keys: `~/.cdsapirc` (CDS) and `.env` (`OPENAQ_API_KEY`, optional `FIRMS_MAP_KEY`) were created with placeholders and filled in by Reenu. `.env` is gitignored; `.env.example` is committed.
  - `src/acquire/probe.py` (checks), `probe_report.py` (report), `s3.py` (anonymous S3 listing), `http_range.py` (read remote Parquet footers without downloading). Tests: `tests/test_probe.py`. 48 tests pass.
  - Report: `docs/data-probe.md` (generated; do not edit). Facts are in DEC-028 to DEC-036.
- **Phase 2, steps 1–6 (acquisition):**
  - Decisions DEC-037 to DEC-046. Phase note: `docs/phase-notes/02-acquisition.md`. Data cards: `docs/data-cards/`.
  - Downloads (all resumable, checksum-verified, manifests committed; DEC-042):
    - `src/acquire/cpcb_mirror.py`: main ground source, 2015–2025 (DEC-037)
    - `src/acquire/openaq.py`: zip per location-year (DEC-041)
    - `src/acquire/acag.py`, `ghsl.py`, `boundaries.py`
    - `src/acquire/era5.py`: 283 grid points plus India monthly means
    - `src/acquire/firms.py`: written, **not yet run** (DEC-039)
  - `src/acquire/stations.py`: mirror ↔ OpenAQ crosswalk with coordinates → `data/interim/station_crosswalk.csv` (DEC-045).
  - `src/acquire/mirror_checks.py` → `docs/mirror-checks.md`:
    - timezone: mirror stores Indian times stamped as UTC; true UTC = stored − 5.5 h (`mirror.stored_minus_utc_hours`, DEC-054, which corrects DEC-040's "11 h")
    - PM2.5 and PM10 station-year tables
  - NCAP: `ncap_pdfs.py` → `ncap_extract.py` → `ncap_validate.py`. Sources in `config/ncap_sources.yaml`, aliases in `config/ncap_city_aliases.yaml`.
    - Outputs: `data/interim/ncap_cities.csv`, `ncap_funding_clean.csv`, and **`docs/ncap_extraction_mismatches.md` (for Reenu)**.
    - Counts reconciled (DEC-044).
  - Snakemake: real acquisition rules in `workflow/rules/acquire.smk`. FIRMS is built on request.
  - Tests: 77 passing.
  - Reenu reviewed all 37 mismatch items; rulings are DEC-047 to DEC-053.

## How to run (Windows, Git Bash or PowerShell)

**Always run inside the activated environment.** Never call `envs/ncap/python.exe` directly: Oracle XE's `mkl_rt.dll` on this machine's PATH crashes NumPy (DEC-046).

```bash
conda activate ncap            # or: ~/miniforge3/Scripts/conda.exe run -n ncap --no-capture-output <cmd>
pytest
snakemake -n all               # dry run
snakemake --cores 8 pregate
```

## Next: Phase 3 (storage, cleaning, audit, EDA for RQ1)

Follow PLAN.md §4 (Phase 3) and CLAUDE.md. Start with a short plan of files and functions, then build. Draft `docs/analysis_plan.md` during Phase 3, in OSF format (DEC-017). The gate stays closed, and no figure or table may compare NCAP with non-NCAP after 2018 (blinding rule).

Inputs are all in `data/raw/` (see `docs/data-cards/`). Things Phase 3 must apply:

- **Mirror timestamps:** subtract `mirror.stored_minus_utc_hours` (5.5 h) from the *stored* instant, read with DuckDB `TimeZone='UTC'` (DEC-054; DEC-040's "11 h" was measured on local-zone rendering). Store UTC and aggregate days in IST. The raw files stay unchanged.
- **Mirror rows are padded:** count non-null values, never rows.
- **OpenAQ:**
  - several location ids per station, so de-duplicate them (crosswalk: `data/interim/station_crosswalk.csv`);
  - the only source for Jan–Mar 2026;
  - its pre-2023 CPCB values are not identical to the mirror's, so compare with tolerances.
- **Station coordinates:** 19 stations have none, so give them a GHSL urban-centre coordinate. Stations whose OpenAQ ids disagree (up to 30 km) go on the metadata review list (DEC-045).
- **Clock or solar-sensor outliers:** flag stations in the lowest decile of `data/interim/mirror_checks/timezone_solar.csv`.
- **ERA5:** clip `ssrd` at 0 (Phase 5); stations without coordinates need their ERA5 cells added once located.
- **NCAP units** (`data/interim/ncap_cities.csv`), for the NCAP-city ↔ UCDB matching table:
  - Bhilai = the Durg-Bhilai twin city, covering both towns (DEC-047);
  - Asansol & Raniganj is one unit (DEC-050);
  - Bhubaneswar & Cuttack and Angul & Talcher are enrolled cities whose combined-row funding uses combined population (DEC-048);
  - Patancheruvu is enrolled from its listing date, with an exclusion sensitivity (DEC-049);
  - the J&K state row is excluded (DEC-051);
  - addition dates are interval-censored (DEC-043/044); the treatment definition is decided in `analysis_plan.md`.
- **Region map:** finalise `config/regions.yaml`.

**FIRMS (pending, Reenu):** from a network where `firms.modaps.eosdis.nasa.gov` is reachable, put the new key in `.env` as `FIRMS_MAP_KEY`, then run `python -m src.acquire.firms` (or `snakemake --cores 4 data/interim/_flags/acquire_firms.done`). It is VIIRS S-NPP only, from 2012 (DEC-039).

## Phase 3 plan (written 2026-09-26, before coding)

Part A, then a checkpoint report to Reenu before Part B.

**Part A: ingest, cross-check, station metadata**
- `src/clean/ingest.py`
  - `mirror`: raw yearly Parquet → `data/interim/mirror_15min/year=YYYY/` (sid, ts_utc, date_ist, pm25, pm10, no2). Stored instant minus 5.5 h (DEC-054); rows with no PM/NO2 dropped; duplicates across year files resolved and counted.
  - `openaq`: zips → `data/interim/openaq_obs/year=YYYY/` (location_id, ts_utc, parameter, value), µg/m³ only.
- `src/clean/crosscheck.py`: mirror vs OpenAQ for every matched station-year-pollutant.
  - Metrics: exact share at 15 min, hourly and daily agreement, correlation, bias; broken down by year and operating agency.
  - Output: `docs/mirror-openaq-crosscheck.md` (generated).
- `src/clean/geo.py`: UCDB India polygons, state boundaries, and the NCAP-city ↔ UCDB matching table `data/interim/ncap_ucdb_match.csv` (DEC-047 to DEC-051).
- `src/clean/station_meta.py`: resolves coordinates.
  - Unmatched stations: value-matched against unused OpenAQ locations.
  - Conflicting OpenAQ ids: which id's data match the mirror, plus coordinate plausibility (state polygon, city's urban centre).
  - What is left gets an urban-centre coordinate, flagged approximate, and goes on the review list.
  - Outputs: `data/processed/stations.csv` and `docs/station_metadata_review.md`.
- `src/clean/hourly.py`: `data/processed/station_hour/` (IST-hour bins), with the mirror up to its end and OpenAQ after it.

**Part B (after the checkpoint)**
- `src/clean/flags.py` (one pure function per rule), `changepoints.py`, `spatial.py`, `reliability.py`, `missingness.py`
- `src/clean/zonal.py`: ACAG over UCDB
- `src/viz/eda_*.py`: seasonal cycles, raw trends, ground vs satellite, station-entry map, quality heatmap
- `src/clean/audit_report.py` → `docs/audit_report.md`
- `docs/analysis_plan.md` (draft)
- `config/regions.yaml` finalised

## Phase 3 checkpoint (part A done, 2026-09-26)

Built and run (all generated, all in Snakemake `workflow/rules/clean.smk`):
- `src/clean/ingest.py` → `data/interim/mirror_15min/`, `data/interim/openaq_obs/` (DEC-055, DEC-056)
- `src/clean/crosscheck.py` → `docs/mirror-openaq-crosscheck.md` (DEC-057)
- `src/clean/station_meta.py` → `data/processed/stations.csv`, `docs/station_metadata_review.md` (DEC-058 to DEC-060)
- `src/clean/geo.py` → `data/interim/ghsl/ucdb_india.gpkg`, `data/interim/ncap_ucdb_match.csv`, `docs/ncap_ucdb_review.md` (DEC-061, DEC-062)
- `src/acquire/mirror_checks.py` re-run on the machine-independent clock (DEC-054); `docs/mirror-checks.md` regenerated
- Tests: 91 passing (`tests/test_ingest.py`, `tests/test_station_geo.py` new).

Waiting on Reenu:
1. Accept DEC-054 (clock restated as stored − 5.5 h)?
2. Hour-validity rule for completeness: any quarter-hour (Phase 2's rule) or ≥3 of 4? It changes valid station-years (e.g. PM10 2018: 69 vs 56).
3. `docs/station_metadata_review.md` §3: 54 stations to review (coordinates, overrides).
4. `docs/ncap_ucdb_review.md` §5: 10 NCAP cities without an urban centre need a town-coordinate source; Raniganj (WB) and Patancheruvu geography.

Next (part B, after approval): `src/clean/hourly.py` (station-hour, IST bins; OpenAQ for 2026-Q1), flags, changepoints, spatial checks, reliability score, missingness, ACAG zonal stats, EDA figures (station-entry map, quality heatmap), `docs/audit_report.md`, draft `docs/analysis_plan.md`, `config/regions.yaml` final.

## Open problems

- **FIRMS not downloaded**: host unreachable from the current network; Reenu will run it later with a new key (DEC-039). Lowest priority (cut item #4).
- **Mirror provenance** is one step removed from CPCB (DEC-037). Mitigations: sha256 pinning, cross-check against OpenAQ, and ODbL for any derived dataset we publish.
- **Pre-2018 ground network is thin** (DEC-033). It limits the ground-layer baseline, not Layer A.
- **OpenAQ's pre-2023 CPCB feed is not value-identical to the mirror** (about 2% exact matches), so the Phase 3 cross-check must use correlations and tolerances, not equality.
- **Station metadata:** some OpenAQ ids for one station disagree by up to 30 km; 19 stations have no coordinates (DEC-045).
- **V6.GL.03 has no methods note.** If one appears, revisit DEC-001.
- `config/regions.yaml` is a draft (IGP membership of Jharkhand, coastal distance, whether "peninsular/other" needs splitting). It gets finalised in Phase 3.
- **Treatment definition** (listed vs funded; interval-censored addition dates, DEC-044) is decided in Phase 4's analysis plan.
- Possible extension (not scheduled): official PRANA/NAMP PM10 series as a "reported" reference (DEC-016).

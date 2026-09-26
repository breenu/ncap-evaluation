# PROGRESS

Handoff file: a fresh session should be able to continue from this alone.
Read with [`PLAN.md`](PLAN.md) (what and how), [`DECISIONS.md`](DECISIONS.md) (why) and `CLAUDE.md` (rules).

*Last updated: 2026-09-26. Phase 3 complete (parts A and B), committed, **stopped for Reenu's review**. Gate closed. Next: Phase 4 after approval.*

## Status

| Phase | State |
|---|---|
| 0 Plan | ✅ approved 2026-09-26 (answers in PLAN.md §8) |
| 1 Skeleton | ✅ approved 2026-09-26; pushed; CI green |
| 2 Acquisition | ✅ approved 2026-09-26; pushed. FIRMS pending (Reenu will run it from another network with a new key) |
| 3 Storage, cleaning, audit, EDA | ✅ done 2026-09-26; awaiting Reenu's review (5 station decisions, DEC-064, DEC-070, analysis plan) |
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

## Next: Phase 4 (analysis-plan gate), after Reenu approves Phase 3

1. Reenu reviews and edits `docs/analysis_plan.md` (draft, OSF format), and may register it on OSF.
2. Pre-gate computations, pre-2019 data only (plan §6):
   - the MDE, by placebo-in-time on 2010–2018 satellite data;
   - baseline balance of treated units vs the control pool.
   Their numbers go into the plan before approval.
3. After approval: commit the plan. Then, in a *separate* commit citing the plan's hash, flip `config/gate.yaml`.

The gate stays **closed**. Blinding still applies: no NCAP vs non-NCAP comparison after 2018 until the gate opens.

## Phase 3: what was built (2026-09-26)

Part A (checkpoint approved by Reenu): see "Phase 3 checkpoint" below. Part B, after Reenu's rulings (DEC-063 to DEC-078):

- **Towns and satellite units:** `src/clean/towns.py` → `data/interim/geonames_towns.csv`, `data/interim/sat_units.gpkg`.
  - GeoNames town points; buffer rule r = 1.87 km (DEC-063).
  - Raniganj joined to Asansol as its GHSL polygon (DEC-064, **flagged for Reenu**).
  - 1,932 units; the 10 no-centre towns are sensitivity-only.
- **Regions:** `src/clean/regions.py` → `data/interim/unit_regions.csv`, `station_regions.csv`; `config/regions.yaml` final (DEC-075).
- **Station-hour and station-day:** `src/clean/hourly.py` + `src/clean/flags.py` → `data/processed/station_hour/`, `station_day.parquet`.
  - Ceilings detected from the data; flatline ≥ 4 h; PM2.5 > PM10 with tolerance (DEC-068).
  - OpenAQ supplies Jan–Mar 2026.
- **Satellite:** `src/clean/zonal.py` → `unit_year_sat.parquet`, `unit_month_sat.parquet`, `station_year_sat.parquet`. Population-weighted primary, area-weighted sensitivity (DEC-070).
- **Audit checks:**
  - `src/clean/spatial.py`: neighbours within 25 km, and the satellite (DEC-071)
  - `src/clean/changepoints.py`: penalty calibrated against a block-shuffled null (DEC-072, DEC-078)
  - `src/clean/reliability.py`: completeness variants and score (DEC-073)
  - `src/clean/missingness.py` (DEC-074)
- **EDA and figures:** `src/viz/eda.py` + `src/viz/style.py` → `reports/figures/`:
  - fig2 station-entry map; fig8 quality heatmap;
  - seasonal cycles by region; city trends; ground vs satellite; new vs existing stations.
- **Generated reports:** `docs/audit_report.md` (`src/clean/audit_report.py`), `docs/station_metadata_review.md`, `docs/ncap_ucdb_review.md`, `docs/mirror-openaq-crosscheck.md`, `docs/mirror-checks.md` (with the corrected-clock solar check, DEC-077).
- **New sources:** GeoNames and Natural Earth coastline (data cards, manifests).
- **Snakemake:** `workflow/rules/clean.smk` and `eda.smk` hold the real Phase 3 rules; `pregate` builds everything through the audit report.
- **Phase note:** `docs/phase-notes/03-audit.md`. **Draft analysis plan:** `docs/analysis_plan.md`.

**Waiting on Reenu (end of Phase 3):**
1. `docs/station_metadata_review.md` §3: 5 stations whose candidate coordinates are in different centres, each with a recommendation.
2. DEC-064: Raniganj joined as the GHSL polygon containing its point (UCDB calls it "Mejia"), rather than as a buffer. Confirm.
3. DEC-070: the oversized-polygon rule (population-weighted mean for every unit; area-weighted as sensitivity). Confirm.
4. `docs/analysis_plan.md`: review and edit.
5. Repo visibility: public after Phase 3 (DEC-020), once Reenu approves.

## Phase 3 checkpoint (part A, approved 2026-09-26 with rulings DEC-063 to DEC-069)

Built and run (all generated, all in Snakemake `workflow/rules/clean.smk`):
- `src/clean/ingest.py` → `data/interim/mirror_15min/`, `data/interim/openaq_obs/` (DEC-055, DEC-056)
- `src/clean/crosscheck.py` → `docs/mirror-openaq-crosscheck.md` (DEC-057)
- `src/clean/station_meta.py` → `data/processed/stations.csv`, `docs/station_metadata_review.md` (DEC-058 to DEC-060, DEC-067)
- `src/clean/geo.py` → `data/interim/ghsl/ucdb_india.gpkg`, `data/interim/ncap_ucdb_match.csv`, `docs/ncap_ucdb_review.md` (DEC-061, DEC-062, DEC-076)
- `src/acquire/mirror_checks.py` re-run on the machine-independent clock (DEC-054, confirmed by DEC-077)

## Open problems

- **FIRMS not downloaded**: the host is unreachable from the current network; Reenu will run it later with a new key (DEC-039). Lowest priority (cut item #4).
- **Mirror provenance** is one step removed from CPCB (DEC-037). Mitigations: sha256 pinning, the cross-check (2019–21 value-identical), and ODbL for any derived dataset we publish.
- **Pre-2018 ground network is tiny**: PM10 has 9 valid station-years in 2017 and 66 in 2018. Ground-based and PM10 results are secondary (analysis plan §0).
- **Stations with no coordinate anywhere** keep an approximate city point (count in `docs/station_metadata_review.md`); 5 await Reenu's decision.
- **ERA5 cells for newly located stations**: stations located in Phase 3 (by identity or locality) may sit in 0.25° cells not yet downloaded. Check and fetch in Phase 5 (small, under 2 GB).
- **V6.GL.03 has no methods note.** If one appears, revisit DEC-001.
- **The treatment definition** (listed vs funded; interval-censored dates) is proposed in `docs/analysis_plan.md` and decided at the Phase 4 gate.
- Possible extension (not scheduled): the official PRANA/NAMP PM10 series as a "reported" reference (DEC-016).

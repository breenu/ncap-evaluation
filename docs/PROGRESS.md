# PROGRESS

Handoff file: a fresh session should be able to continue from this alone.
Read with [`PLAN.md`](PLAN.md) (what and how), [`DECISIONS.md`](DECISIONS.md) (why) and `CLAUDE.md` (rules).

*Last updated: 2026-09-26, Phase 2 approved and pushed. FIRMS download pending (Reenu runs it later). Next: Phase 3.*

## Status

| Phase | State |
|---|---|
| 0 Plan | ✅ approved 2026-09-26 (answers in PLAN.md §8) |
| 1 Skeleton | ✅ approved 2026-09-26; pushed; CI green |
| 2 Acquisition | ✅ approved 2026-09-26; pushed. FIRMS pending (Reenu will run it from another network with a new key) |
| 3–10 | not started |

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
    - timezone: **mirror labels = UTC + 11 h**, corrected via `config/params.yaml: mirror.label_minus_utc_hours` (DEC-040)
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

- **Mirror timestamps:** subtract `mirror.label_minus_utc_hours` (11 h) to get UTC (DEC-040). Store UTC and aggregate days in IST. The raw files stay unchanged.
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

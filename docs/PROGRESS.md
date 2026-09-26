# PROGRESS

Handoff file: a fresh session should be able to continue from this alone.
Read with [`PLAN.md`](PLAN.md) (what and how), [`DECISIONS.md`](DECISIONS.md) (why) and `CLAUDE.md` (rules).

*Last updated: 2026-09-26, Phase 2 complete except the FIRMS download (network); stopped for Reenu's review of the NCAP mismatch list.*

## Status

| Phase | State |
|---|---|
| 0 Plan | ✅ approved 2026-09-26 (answers in PLAN.md §8) |
| 1 Skeleton | ✅ approved 2026-09-26; pushed; CI green |
| 2 Acquisition | ✅ built; awaiting Reenu's review (NCAP mismatch list). FIRMS not downloaded (host unreachable) |
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

## How to run (Windows, Git Bash or PowerShell)

**Always run inside the activated environment.** Never call `envs/ncap/python.exe` directly: Oracle XE's `mkl_rt.dll` on this machine's PATH crashes NumPy (DEC-046).

```bash
conda activate ncap            # or: ~/miniforge3/Scripts/conda.exe run -n ncap --no-capture-output <cmd>
pytest
snakemake -n all               # dry run
snakemake --cores 8 pregate
```

## Next

1. **Reenu reviews `docs/ncap_extraction_mismatches.md`** (48 items: names mapped by judgement, combined rows, utilisation > release, small total differences) and records conclusions in DECISIONS.
2. **Reenu approves Phase 2.** Then commit, push, and start Phase 3 (storage, cleaning, audit, EDA). Phase 3's ingest must:
   - subtract 11 h from mirror timestamps (DEC-040);
   - de-duplicate OpenAQ location ids per station;
   - give the 19 stations without coordinates a GHSL urban-centre location (DEC-045);
   - flag stations whose solar-radiation clock disagrees (lowest decile in `data/interim/mirror_checks/timezone_solar.csv`).
3. **FIRMS:** run `python -m src.acquire.firms` from a network where `firms.modaps.eosdis.nasa.gov` is reachable (it was reachable from the phone hotspot).

## Open problems

- **FIRMS host unreachable** from the current network (DEC-039). Lowest priority (cut item #4).
- **Mirror provenance** is one step removed from CPCB (DEC-037). Mitigations: sha256 pinning, cross-check against OpenAQ, and ODbL for any derived dataset we publish.
- **Pre-2018 ground network is thin** (DEC-033). It limits the ground-layer baseline, not Layer A.
- **OpenAQ's pre-2023 CPCB feed is not value-identical to the mirror** (about 2% exact matches), so the Phase 3 cross-check must use correlations and tolerances, not equality.
- **Station metadata:** some OpenAQ ids for one station disagree by up to 30 km; 19 stations have no coordinates (DEC-045).
- **V6.GL.03 has no methods note.** If one appears, revisit DEC-001.
- `config/regions.yaml` is a draft (IGP membership of Jharkhand, coastal distance, whether "peninsular/other" needs splitting). It gets finalised in Phase 3.
- **Treatment definition** (listed vs funded; interval-censored addition dates, DEC-044) is decided in Phase 4's analysis plan.
- Possible extension (not scheduled): official PRANA/NAMP PM10 series as a "reported" reference (DEC-016).

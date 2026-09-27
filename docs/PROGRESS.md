# PROGRESS

Handoff file: a fresh session should be able to continue from this alone.
Read with [`PLAN.md`](PLAN.md) (what and how), [`DECISIONS.md`](DECISIONS.md) (why) and `CLAUDE.md` (rules).

*Last updated: 2026-09-27. Phase 4 built and reviewed; Reenu's rulings and the units correction are in the plan (DEC-091 to DEC-093); mgcv fixed; full pregate rebuild from raw data done in the rebuilt environment. Gate still closed. Final pre-registration changes made (DEC-095 to DEC-098). **Next: Reenu registers the plan on OSF and returns with the link** (see "Next: the gate" below).*

## Status

| Phase | State |
|---|---|
| 0 Plan | ✅ approved 2026-09-26 (answers in PLAN.md §8) |
| 1 Skeleton | ✅ approved 2026-09-26; pushed; CI green |
| 2 Acquisition | ✅ approved 2026-09-26; pushed. FIRMS pending (Reenu will run it from another network with a new key) |
| 3 Storage, cleaning, audit, EDA | ✅ approved 2026-09-26; pushed (DEC-080 to DEC-082) |
| 4 Analysis-plan gate | 🟡 built 2026-09-26; reviewed 2026-09-27 (DEC-091 to DEC-098); plan final, awaiting OSF registration |
| 5–10 | not started |

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
    - Fixed in `5af0edf` by adding `r-rcppeigen` and `r-bh` (lock diff: only those two added).
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
snakemake --cores 1 pregate      # single core: several steps give DuckDB 8 GB (DEC-082)
```

## Next: the gate. START HERE in a new chat

Phase 4 is built; nothing after it may start until Reenu approves the plan.

**Decided 2026-09-27 (DEC-092):** first listing is the primary treatment date (funding timing is a sensitivity only); H4, H5 and the Asansol-alone check accepted; Reenu registers the plan on OSF before the gate opens.

**Final changes before registration (DEC-095 to DEC-098):** equivalence margin ±5% (smallest effect of interest, not the MDE); calibration-leakage split (74 treated units gained a monitor in 2019–2024, 39 did not; `pregate_checks.md` §7); HonestDiD bounds as a reported sensitivity; plan and summary rewritten in Reenu's first person (wording only, verified).

**What Reenu does next:** register `docs/analysis_plan.md` on OSF and bring back the link. **Final plan commit: `6e24ecaf38c54c1f31774c966c243e4183c1b2ca`** (the version to register). The file to upload to OSF is `docs/osf/analysis_plan_osf.pdf`, made by `python -m src.causal.osf_export` from that commit: markers stripped, the status paragraph replaced by a version line naming the commit, repository links pinned to it. If the plan is edited again, commit it and re-run the export. Note: the GitHub repo is still **private**, so the repo links in the PDF only work once Reenu makes it public. After registration, in its own commit, set `config/gate.yaml` `analysis_plan_commit` to this hash (or to a later commit if the plan is edited again) and record the OSF link in DECISIONS.

**After approval, in this order (DEC-012):**
1. Commit the approved plan (and summary). Note the commit hash.
2. In a *separate* commit, set `config/gate.yaml`: `analysis_plan_approved: true`, `analysis_plan_commit: <hash>`. Nothing else in that commit.
3. Record the approval and the OSF link in DECISIONS.
4. Then Phase 5 (deweathering). mgcv is fixed (DEC-093).
5. Housekeeping: the pre-fix environment is kept as `ncap_prev`; delete it (`conda env remove -n ncap_prev`) once Reenu is happy.

**Editing the plan:** numbers sit between `<!--g:key-->` and `<!--/g-->` markers and are written by `python -m src.causal.pregate_report sync-plan`; never type over them. `snakemake pregate` runs `check-plan` and fails if any quoted number no longer matches the pipeline (then: sync, and log the deviation).

## Phase 4 review fixes (2026-09-27)

- **Pre-registration changes (DEC-095 to DEC-098):** see "Next: the gate" above. New pre-gate output `data/interim/pregate/monitor_gain.csv` (network metadata only). HonestDiD 0.2.8 is in the CRAN snapshot; install it in Phase 7 via `install_r_extra.R`.

- **Units (DEC-091):** log-scale results were labelled "log points" (100 × log difference), which read as 100 times too large. All reports now give natural-log units with the implied % (e.g. placebo +0.0047 = +0.47%). No estimate changed.
- **p-values (DEC-091):** permutation p-values are now equal-tailed, because the region-matched null is not centred on zero. Real-NCAP placebo: 2014 p = 0.32 (was 0.22), 2015 p = 0.75 (was 0.41).
- **MDE reconciliation (DEC-091):** the 1.2% MDE is about 0.6 µg/m³ at the NCAP mean; the separate µg/m³-scale MDE (0.9) is larger because absolute noise sits in the dirtiest cities. Generated in `docs/pregate_checks.md` §4.
- **mgcv (DEC-093):** not the Oracle MKL conflict; now installed from the 2026-09-25 CRAN snapshot. `conda-lock.yml` re-locked in update mode (only change: r-mgcv removed). The `ncap` environment was rebuilt from the lock; the R environment test passed 10/10.
- **Full rebuild from raw (DEC-094):** `snakemake --cores 1 --forceall pregate` with `--allowed-rules` excluding downloaders, 30 jobs, 1 h 25 min; every plan number and every generated report unchanged. Intermediates are content- but not byte-reproducible (timestamps, tie order).
- **Re-locking on this machine:** `PYTHONNOUSERSITE=1 uvx conda-lock lock -f environment.yml -p win-64 -p linux-64 --lockfile conda-lock.yml --update <pkg> --conda %USERPROFILE%/miniforge3/Scripts/conda.exe`. Without `PYTHONNOUSERSITE`, conda's Python picks up user-site packages and update mode fails.

## Phase 4: what was built (2026-09-26)

- **Pre-gate code** (`workflow/rules/causal.smk`, part of `pregate`, not gated):
  - `src/causal/treatment.py`: listing-date cohorts (primary) and first-funding cohorts (alternative, DEC-086).
  - `src/causal/pregate.py` → `data/interim/pregate/`: pre-2019 satellite panels (reader filters year ≤ 2018 and asserts it), control pool with 25 km spillover distances (DEC-085), baseline balance, ground PM10 feasibility counts.
  - `src/causal/mde_placebo.R`: SDID placebo-in-time (fake 2014/2015), 500 draws × {random, region-matched} null designs × 4 outcomes; the real treated set at the fake years (DEC-087). ~35 min on 8 workers; BLAS pinned to one thread per worker.
  - `src/causal/pregate_report.py` → `docs/pregate_checks.md` (generated), plus `sync-plan` / `check-plan` for the numbers quoted in the plan and summary.
- **Docs:** `docs/analysis_plan.md` (OSF Preregistration layout, final draft), `docs/analysis_plan_summary.md`, `docs/phase-notes/04-gate.md`, DEC-084 to DEC-090.
- **Tests:** `tests/test_pregate.py` (19, synthetic).
- **Run:** R steps run inside the env (`conda run -n ncap`, or `snakemake` from an activated env). mgcv's load failure is fixed (DEC-093).

## Phase 3: what was built (2026-09-26, approved)

Part A: see "Phase 3 checkpoint" below. Part B, after Reenu's rulings (DEC-063 to DEC-082):

- **Towns and satellite units:** `src/clean/towns.py` → `data/interim/geonames_towns.csv`, `data/interim/sat_units.gpkg`.
  - GeoNames town points; buffer rule r = 1.87 km (DEC-063).
  - Raniganj joined to Asansol as its GHSL polygon (DEC-064, confirmed DEC-081).
  - The 10 no-centre towns are sensitivity-only.
- **Regions:** `src/clean/regions.py` → `data/interim/unit_regions.csv`, `station_regions.csv`; `config/regions.yaml` final (DEC-075).
- **Station metadata:** `data/processed/stations.csv`. Reenu's decisions on the last 5 stations (DEC-080) live in `config/station_overrides.yaml`; `reenu_decided` marks them for a drop-all-5 sensitivity.
- **Station-hour and station-day:** `src/clean/hourly.py` + `src/clean/flags.py` → `data/processed/station_hour/`, `station_day.parquet`.
  - Ceilings detected from the data; flatline ≥ 4 h; PM2.5 > PM10 with tolerance (DEC-068).
  - OpenAQ supplies Jan–Mar 2026, which is provisional (raw feed, DEC-079).
- **Satellite:** `src/clean/zonal.py` → `unit_year_sat.parquet`, `unit_month_sat.parquet`, `station_year_sat.parquet`. Population-weighted primary, unweighted sensitivity (DEC-070, confirmed DEC-081).
- **Audit checks:**
  - `src/clean/spatial.py`: neighbours within 25 km, and the satellite (DEC-071)
  - `src/clean/changepoints.py`: penalty calibrated against a block-shuffled null (DEC-072, DEC-078)
  - `src/clean/reliability.py`: completeness variants and score (DEC-073)
  - `src/clean/missingness.py` (DEC-074)
- **EDA and figures:** `src/viz/eda.py` + `src/viz/style.py` → `reports/figures/`:
  - fig2 station-entry map; fig8 quality heatmap;
  - seasonal cycles by region; city trends; ground vs satellite; new vs existing stations.
- **Generated reports:** `docs/audit_report.md`, `docs/station_metadata_review.md`, `docs/ncap_ucdb_review.md`, `docs/mirror-openaq-crosscheck.md`, `docs/mirror-checks.md`.
- **New sources:** GeoNames and Natural Earth coastline (data cards, manifests).
- **Snakemake:** `workflow/rules/clean.smk` and `eda.smk`. `snakemake --cores 1 pregate` rebuilt everything end to end (DEC-082; logs `data/interim/logs/snakemake_pregate_phase3*.log`). That run exposed and fixed three workflow bugs (DEC-083); `snakemake -n pregate` now reports nothing to do.
- **Phase note:** `docs/phase-notes/03-audit.md`. **Draft analysis plan:** `docs/analysis_plan.md`; Reenu reviews it after Phase 4 adds the MDE and baseline balance.
- **README** rewritten for the public repo (Phases 1–3, next steps, reproduce; no results beyond the audit).
- **Git history audited before going public** (2026-09-26): no `.env`, `.cdsapirc` or key file has ever been committed; the actual key values appear in no commit; nothing under `data/` except the 10 `MANIFEST.csv` files. Reenu changes the visibility.

## Phase 3 checkpoint (part A, approved 2026-09-26)

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
- **Stations with no coordinate anywhere** keep an approximate city point (count in `docs/station_metadata_review.md`); they stay out of neighbour checks.
- **ERA5 cells for newly located stations**: stations located in Phase 3 (by identity or locality) may sit in 0.25° cells not yet downloaded. Check and fetch in Phase 5 (small, under 2 GB).
- **V6.GL.03 has no methods note.** If one appears, revisit DEC-001.
- **The treatment definition** (listed vs funded) is proposed in `docs/analysis_plan.md` (listed primary) and decided by Reenu at the gate.
- **No LICENSE file yet.** Reenu to choose a code licence before or when the repo goes public. Any derived dataset from the CPCB mirror must be ODbL (DEC-037).
- **Jan–Mar 2026 ground data are provisional** (OpenAQ raw feed, DEC-079).
- **Outputs are not byte-deterministic** (GeoPackage timestamps, tie order in DuckDB/pandas writes, SVG dates and ids; DEC-094). Content and numbers reproduce. Fix before the Phase 10 clean-clone check.
- Possible extension (not scheduled): the official PRANA/NAMP PM10 series as a "reported" reference (DEC-016).

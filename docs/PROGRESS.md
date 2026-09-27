# PROGRESS

Handoff file: a fresh session should be able to continue from this alone.
Read with [`PLAN.md`](PLAN.md) (what and how), [`DECISIONS.md`](DECISIONS.md) (why) and `CLAUDE.md` (rules).

*Last updated: 2026-09-27. Phase 5 (deweathering): pilot approved with changes (DEC-109 to DEC-113); the **full run is in progress** (see "Phase 5" below).*

## Status

| Phase | State |
|---|---|
| 0 Plan | ✅ approved 2026-09-26 (answers in PLAN.md §8) |
| 1 Skeleton | ✅ approved 2026-09-26; pushed; CI green |
| 2 Acquisition | ✅ approved 2026-09-26; pushed. FIRMS pending (Reenu will run it from another network with a new key) |
| 3 Storage, cleaning, audit, EDA | ✅ approved 2026-09-26; pushed (DEC-080 to DEC-082) |
| 4 Analysis-plan gate | ✅ 2026-09-27: plan `6e24eca` registered at https://osf.io/jksne/; gate opened in `0d9aa42` (DEC-084 to DEC-099) |
| 5 Deweathering | pilot approved 2026-09-27 with changes (DEC-100 to DEC-113); full run in progress |
| 6–10 | not started |

Pre-registration gate: **open** since 2026-09-27 (`config/gate.yaml` cites plan commit `6e24ecaf38c54c1f31774c966c243e4183c1b2ca` and https://osf.io/jksne/). No post-2019 effect estimates exist yet; they belong to Phase 7.

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

## Phase 5 (deweathering, RQ2): IN PROGRESS. START HERE in a new chat

**State (2026-09-27, 22:45): the full run is RUNNING.** Reenu approved the pilot with changes (DEC-109 to DEC-113). The run writes to `data/interim/logs/normalise_main.log`: GAM main, then LightGBM main (the long part, about 7 h), then the registered-flags refits (66 series), then `cvcheck` for main and registered. **If the laptop slept or the run stopped, re-run the same commands. Done series are skipped:**
```bash
python -m src.normalise.run fit --run main --family both
python -m src.normalise.run fit --run registered --family both
python -m src.normalise.run cvcheck --run main
python -m src.normalise.run cvcheck --run registered
touch data/interim/normalise/fits/main/_all.done
```
Then: `python -m src.normalise.aggregate`, `python -m src.normalise.report`, `python -m src.viz.fig3_deweathered --scheme seasonal` and `--scheme annual`. Look at both figures, run the tests, commit, update this file, write `docs/phase-notes/05-deweathering.md`, then stop for Reenu.

**Reenu's pilot rulings (2026-09-27), all in DECISIONS:**
- N = 500 for both schemes (DEC-113).
- Seasonal resampling is primary: a **registered-plan deviation** (DEC-109). Grange & Carslaw's all-year default runs on the full set; H4 and figure 3 are reported under both.
- `last_year` CV convention accepted; both conventions keep being reported (`r2_oos_clamp`). The family choice stays as registered.
- Within-period blocked CV (10 round-robin month folds, 7-day buffer) as a diagnostic only (DEC-112).
- Divergence flag defined exactly (DEC-111): D needs ≥ 2 valid years. The pilot's 37 of 40: 3 series had no valid station-year.
- Near-constant analyser rule: a **registered-plan deviation**, made before any treatment-effect estimate (DEC-110; `src/clean/nearconstant.py`, `docs/near_constant_check.md`). It flags 77 of 4,129 valid station-years (1.9%) at 33 stations. Primary analysis: excluded from the fit and from aggregates (run `main`). Sensitivity: registered flags only (run `registered` refits the 66 affected series with those years kept). All tables carry `rule`.

**The plan is registered and frozen** (`docs/analysis_plan.md` at `6e24eca`; OSF https://osf.io/jksne/). Commitments binding Phase 5: LightGBM and mgcv GAM on log daily PM per station and pollutant; the primary family is the one with the better **median out-of-sample R² under blocked, forward-chaining CV by year** (DEC-088); a no-deweathering baseline is kept; no NCAP information is used and no treatment effect is estimated.

**Built so far:**
- ERA5 for the 20 missing grid points: `python -m src.acquire.era5 --located` (303 cells, manifest verified, flag `acquire_era5_located`; DEC-100).
- `src/normalise/`:
  - `era5_daily.py` → `data/interim/normalise/era5_daily.parquet` (Indian-day weather per cell)
  - `features.py` (inputs, folds, shared resample indices)
  - `resample.py` (vectorised resampling)
  - `lgbm.py`, `gam.R` (the two families)
  - `store.py` (atomic writes; a task is done when its `.json` exists)
  - `run.py` (prepare / fit / cvcheck; resumable)
  - `collect.py` (metrics, smearing)
  - `pilot.py` (selection + report)
  - `aggregate.py` (family choice, station/city-month/city-year tables)
  - `report.py` (→ `docs/deweathering_report.md`)
- `src/viz/fig3_deweathered.py`.
- Snakemake: `workflow/rules/normalise.smk` (pilot and full-run rules; `normalise` is no longer a stub).
- `src/clean/nearconstant.py` (DEC-110); tests: `tests/test_normalise.py` (21, synthetic); full suite 156 passed.
- Pilot: 20 stations × 2 pollutants, both families, 1,000 draws, both resampling schemes (GAM about 5 min, LightGBM 44 min on 8 workers). Aggregation and figure 3 were tested on pilot outputs (`data/interim/normalise/pilot/aggregate/`, not report outputs).

**Pilot findings (numbers in `docs/deweathering_pilot.md`):**
- Median out-of-sample R², all pilot series: GAM 0.315, LightGBM 0.305 (`last_year` convention); GAM is higher under both CV conventions.
- Residual ACF at lag 1 is about 0.8: the CV must be blocked.
- N = 300 meets the convergence rule, but only narrowly (LightGBM PM2.5: 0.9502 against 0.95).
- The weather part of year-on-year changes: median 2–4%.
- Families diverge by more than 5% in 3 of 37 series.
- Full-run estimate: about 2.5 h wall-clock at the pilot's settings (300 draws, one scheme). The approved run (500 draws, two schemes, plus the within-period CV) scales to about 8–9 h: LightGBM resampling time grows with draws × schemes.


**Open observations from the pilot:**
- ~~Bagalkot near-constant series~~: now caught by the near-constant rule (DEC-110).
- **Question for Reenu (found after the go-ahead, not acted on):** the trend term absorbs within-year movement. Under Grange & Carslaw resampling the deweathered series should have almost no within-year variation, but pilot series keep 12% (LightGBM) and 25% (GAM) of the raw within-year SD of log monthly means. So the trend may also absorb year-specific weather, and deweathering would under-remove it. A less flexible GAM trend (e.g. 1–2 basis functions per year instead of 4) would need a GAM re-run (about 1 h). This is a model-specification change, so it waits for Reenu. `docs/deweathering_report.md` §5 measures it on the full run.
- LightGBM's in-sample R² (0.99) is far above its out-of-sample R² (0.3). It memorises individual days through the trend feature, a known property of this method; watch whether it under-removes weather.

**Housekeeping:**
- The GitHub repo is **public** since 2026-09-27; the repository links in the registered OSF PDF resolve.
- **Still open: no LICENSE file.** Reenu to choose a code licence; any derived dataset from the CPCB mirror must be ODbL (DEC-037).
- The registered PDF is `docs/osf/analysis_plan_osf.pdf` (from `6e24eca`); do not re-export it.

## Phase 4 review fixes (2026-09-27)

- **Pre-registration changes (DEC-095 to DEC-098):** ±5% equivalence margin; calibration-leakage split (74 vs 39 treated units); HonestDiD bounds; first-person voice. New pre-gate output `data/interim/pregate/monitor_gain.csv` (network metadata only). HonestDiD 0.2.8 is in the CRAN snapshot; install it in Phase 7 via `install_r_extra.R`.

- **Units (DEC-091):** log-scale results were labelled "log points" (100 × log difference), which read as 100 times too large. All reports now give natural-log units with the implied % (e.g. placebo +0.0047 = +0.47%). No estimate changed.
- **p-values (DEC-091):** permutation p-values are now equal-tailed, because the region-matched null is not centred on zero. Real-NCAP placebo: 2014 p = 0.32 (was 0.22), 2015 p = 0.75 (was 0.41).
- **MDE reconciliation (DEC-091):** the 1.2% MDE is about 0.6 µg/m³ at the NCAP mean; the separate µg/m³-scale MDE (0.9) is larger because absolute noise sits in the dirtiest cities. Generated in `docs/pregate_checks.md` §4.
- **mgcv (DEC-093):** not the Oracle MKL conflict; now installed from the 2026-09-25 CRAN snapshot. `conda-lock.yml` re-locked in update mode (only change: r-mgcv removed). The `ncap` environment was rebuilt from the lock; the R environment test passed 10/10.
- **Full rebuild from raw (DEC-094):** `snakemake --cores 1 --forceall pregate` with `--allowed-rules` excluding downloaders, 30 jobs, 1 h 25 min; every plan number and every generated report unchanged. Intermediates are content- but not byte-reproducible (timestamps, tie order).
- **Registration and gate (DEC-099):** OSF https://osf.io/jksne/, verified via the OSF API (public, OSF Preregistration template; archived PDF byte-identical to the export of `6e24eca`). Commit `0d9c5a4` records the link; commit `0d9aa42` opens the gate and contains only `config/gate.yaml`. `tests/test_gate.py` now checks that the committed gate is either shut or cites a full commit hash that contains the plan.
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
- ~~ERA5 cells for newly located stations~~: resolved in Phase 5 (20 cells fetched, DEC-100).
- **V6.GL.03 has no methods note.** If one appears, revisit DEC-001.
- **The treatment definition** (listed vs funded) is proposed in `docs/analysis_plan.md` (listed primary) and decided by Reenu at the gate.
- **No LICENSE file yet, and the repo is public (since 2026-09-27).** Reenu to choose a code licence. Any derived dataset from the CPCB mirror must be ODbL (DEC-037).
- **Jan–Mar 2026 ground data are provisional** (OpenAQ raw feed, DEC-079).
- **Outputs are not byte-deterministic** (GeoPackage timestamps, tie order in DuckDB/pandas writes, SVG dates and ids; DEC-094). Content and numbers reproduce. Fix before the Phase 10 clean-clone check.
- Possible extension (not scheduled): the official PRANA/NAMP PM10 series as a "reported" reference (DEC-016).

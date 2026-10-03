# PROGRESS

Handoff file: a fresh session should be able to continue from this alone.
Read with [`PLAN.md`](PLAN.md) (what and how), [`DECISIONS.md`](DECISIONS.md) (why) and `CLAUDE.md` (rules).

*Last updated: 2026-10-03. **Phase 8b approved and closed (DEC-174 to DEC-189). Next: Phase 9, figures and dashboard.** START at "Next: Phase 9" below.*

## Status

| Phase | State |
|---|---|
| 0 Plan | ✅ approved 2026-09-26 (answers in PLAN.md §8) |
| 1 Skeleton | ✅ approved 2026-09-26; pushed; CI green |
| 2 Acquisition | ✅ approved 2026-09-26; pushed. FIRMS VIIRS 2012–2024 downloaded 2026-10-03; the 2025+ part is not fetched (DEC-172/173) |
| 3 Storage, cleaning, audit, EDA | ✅ approved 2026-09-26; pushed (DEC-080 to DEC-082) |
| 4 Analysis-plan gate | ✅ 2026-09-27: plan `6e24eca` registered at https://osf.io/jksne/; gate opened in `0d9aa42` (DEC-084 to DEC-099) |
| 5 Deweathering | ✅ approved 2026-09-28; pushed (DEC-100 to DEC-124) |
| 6 Network composition, H4 | ✅ reviewed and closed 2026-10-01; pushed (DEC-125 to DEC-137) |
| 7 Causal analysis | ✅ approved 2026-10-02 (H1 not identified: rule (b) fails); pushed (DEC-138 to DEC-161) |
| 8 Heterogeneity and mechanism | ✅ approved 2026-10-03 (H5 rule not met; H3 inconclusive; dose: nothing); pushed (DEC-161 to DEC-172) |
| 8b MAIAC AOD check (Earth Engine) | ✅ approved 2026-10-03 (Q1 rise not reproduced; Q2 gap absent; exploratory: ACAG and AOD also diverge where no monitor was added); pushed (DEC-174 to DEC-189) |
| 9 Figures and dashboard | **next** |
| 10 Report and release | not started |

Pre-registration gate: **open** since 2026-09-27 (`config/gate.yaml` cites plan commit `6e24ecaf38c54c1f31774c966c243e4183c1b2ca` and https://osf.io/jksne/). Phase 7's rules (DEC-138 to DEC-150) were pushed in `eebaecc` before any estimate; the first post-2019 effect estimates are Part A's (DEC-151).

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

## Next: Phase 9 (figures and dashboard). START HERE in a new chat

**Per CLAUDE.md:**
- write a short plan first (files and functions);
- record any open choice in DECISIONS and push it before building;
- build;
- at the end: run the tests, commit and push, update this file and DECISIONS, write `docs/phase-notes/09-figures.md`, and stop.
- Run everything inside the `ncap` env (DEC-046). In PowerShell: `& "$env:USERPROFILE\miniforge3\Scripts\conda.exe" run -n ncap --no-capture-output <cmd>`.

**Spec:** the proposal's "Visualisation plan" (`docs/proposal.pdf`, pp. 10–11) and PLAN.md §4 Phase 9:
- **Eight figures, each answering one question:**
  1. decomposition waterfall (reported → weather → composition → policy step);
  2. station-entry map;
  3. raw vs deweathered series for 4–6 cities;
  4. event study;
  5. city-level maps;
  6. before/after shrinkage;
  7. PM10 vs PM2.5;
  8. data-quality heatmap.
  Figure 1 is the one to show in interviews.
- **Style rules:** units (µg/m³, or % with what it is a % of) on every axis; uncertainty on every estimate; colour-blind-safe palettes; colour never carries meaning alone.
- **Dashboard (cut item #3 if time runs short):** read-only and precomputed (Streamlit or a static Quarto site). Pick a city and see its raw, deweathered, composition-corrected and counterfactual trends plus its data-quality score. No real-time data, no deployment.

**What exists already** (all generated, PNG + SVG in `reports/figures/`):
- fig1: `fig1_decomposition`, `_cities`, `_policy` (`src/viz/fig1_decomposition.py`; policy step DEC-150);
- fig2 and fig8: `src/viz/eda.py`;
- fig3: `fig3_deweathered`, `_annual`, `_grange_carslaw`;
- fig4: `fig4_event_study`;
- fig5–7: `fig5_city_map`, `fig6_shrinkage`, `fig7_mechanism` (DEC-167, DEC-170);
- `figS1_levels`; four EDA extras.
- Shared style: `src/viz/style.py`.
- `workflow/rules/viz.smk` is still a stub; `dashboard/` does not exist yet.
- So Phase 9 is mostly an audit of each figure against the style rules and its one question, plus the dashboard.

**Binding wording, carried from Phases 7–8b (do not lose it in figure titles, notes or the dashboard):**
- **H1 is "not identified by this design" (DEC-151).** No figure or dashboard view may call anything an effect of NCAP.
  - The proposal's question for figure 5 ("Where did NCAP work?") and figure 1's "policy-attributable residual" must be reworded. Use DEC-154's sentence and "city-level relative change" (DEC-162/167).
  - The "counterfactual trend" in the dashboard is the unit's synthetic comparison, with that caveat beside it.
- **No per-city ranking or unshrunk city names** (plan §5; DEC-167).
- **Layer B is secondary, with one pre-year,** and carries a scope line (cities, single-station panels; DEC-136/148).
- **No claims about individual weather variables** (DEC-136).
- **Raw AOD (Phase 8b) is not PM2.5:** if it appears in any figure, label it as a relative change in AOD and read it for direction only (DEC-180). It is not one of the eight figures.

**Known items:**
- SVGs embed a date and random ids, so they are not byte-reproducible (DEC-094). Fixing that (`svg.hashsalt`, no date metadata) fits here or in Phase 10.
- Figure 7's panel layout departs from DEC-167 (DEC-170).
- Phase 8b's §12f (exploratory): ACAG and AOD diverge most where no monitor was added. Keep this in mind if any figure discusses calibration leakage.

## Phase 8b (raw MAIAC AOD, Earth Engine): DONE and approved (2026-10-03)

**Approved by Reenu 2026-10-03.**
- Closing items: the exploratory not-gained comparison (§12f; DEC-188/189), and the Drive folder `ncap_maiac_gee` kept as a backup until the project ends.
- **CI** passed on the main Phase 8b commit (run 37081522142).

**Rules:**
- the specification, DEC-174 to DEC-181, pushed in `85acc2a` before any AOD value was pulled;
- implementation: DEC-182 (environment, `config/maiac.yaml`, Q1-only sensitivities), DEC-183 (export to Google Drive: no asset root), DEC-184 (the pilot tripped the compute stop rule), DEC-185 (Contributor tier, limit 400 EECU-hours; Reenu).
- Results DEC-186; workflow DEC-187.

**Results** (numbers in `causal_report.md` §12; DEC-186). **H1 stays "not identified"; nothing here is an effect of NCAP; AOD ≠ PM2.5, so direction only.**
- **Data:**
  - export 167.9 EECU-hours;
  - weight check passed (median +3.4%);
  - kept 95 of 113 treated and 741 of 923 controls (most drops coastal);
  - ACAG on the kept units +4.2%.
- **Q1: "rise not reproduced in AOD".** Primary AOD +0.8% (−0.4% to +2.0%) against ACAG +4.2% on the same units.
  - **Caveat:** non-monsoon AOD +1.5% (+0.4% to +2.6%) would be "rise also in AOD", and the event study's average is +1.3% (+0.1% to +2.6%).
  - AOD's change is below ACAG's in all 5 specifications.
- **Q2: "gap absent from AOD (consistent with calibration leakage)".** In AOD, gained − not gained = +1.6% (−0.8% to +4.0%); in ACAG on the same units, −4.1% (−6.7% to −1.4%).
- **Event study on AOD** (information only): the pre-trend test also fails (p = 0.005).
- **Changed elsewhere:**
  - robustness row "Raw MAIAC AOD" (agrees "—", so 17 of 19 is unchanged);
  - one new row in investigation step 2;
  - Phase 7 note addendum.
  - H1–H5 unchanged.

**How to rebuild.** The export needs Earth Engine credentials and the Contributor tier. Run inside the `ncap` env; in PowerShell, `& "$env:USERPROFILE\miniforge3\Scripts\conda.exe" run -n ncap --no-capture-output <cmd>`.
```bash
earthengine authenticate                        # once; credentials in ~/.config/earthengine/
python -m src.acquire.maiac_gee check           # collection structure (DEC-174)
python -m src.acquire.maiac_gee pilot tiles     # one month; projected EECU against the limit
python -m src.acquire.maiac_gee submit          # 15 yearly Drive exports (~1 h, 3 at a time)
python -m src.acquire.maiac_gee status
python -m src.acquire.maiac_gee download        # -> data/raw/maiac_gee/ + MANIFEST.csv (md5-checked)
snakemake --cores 1 causal                      # causal_maiac_* rules (SDID ~84 min on mains power), then report
```

**Code:**
- `src/acquire/maiac_gee.py`;
- `src/causal/maiac.py`;
- `src/causal/report_maiac.py`;
- `decisions.aod_q1` / `aod_q2`;
- `config/maiac.yaml`;
- `causal_maiac_*` rules in `workflow/rules/causal.smk`;
- `tests/test_maiac.py` (11, synthetic); the full suite has 222 tests, all passing (`data/interim/logs/pytest_phase8b.log`);
- data card `docs/data-cards/maiac_gee.md`.

**Outputs:** `data/processed/causal/maiac/` (panels, sample, coverage, weight check, specs, `sdid/`, `event_study/`, `sdid_summary.csv`, `results.json`).

**Exploratory, after review (DEC-188/189):**
- In the 31 units that gained no monitor: AOD −0.4% against ACAG +7.1%, so they diverge.
- Monitor leakage therefore cannot explain the overall ACAG–AOD difference. The difference is largest where no monitors were added, which weakens Q2 as evidence for leakage specifically (Q2's classification stands).

**Drive:** Reenu keeps `ncap_maiac_gee` (17 CSVs) until the project ends, as a backup of the raw export (data card).


## Phase 8b: the original handoff (2026-10-03; kept for the record)

**What and why.** This is the registered "if time allows" check under the calibration-leakage threat (plan §5; DEC-096, DEC-147 item 18).
- ACAG's satellite PM2.5 is calibrated to ground monitors, and Phase 7's pre-specified leakage warning fired (DEC-151).
- Raw MAIAC AOD uses no ground monitors.
- The check asks whether Layer A's post-2018 relative rise, and its gained/not-gained-monitor pattern, also appear in a signal that no monitor calibrated.
- It **cannot change H1**: "not identified" rests on the failed pre-trend test, which this check does not touch.
- AOD is not PM2.5, so the check compares direction and pattern, never µg/m³.
- Reenu's decision (2026-10-03): run it through **Google Earth Engine**, as a separate phase.

**Read first:**
- `docs/maiac_scoping.md` (product, tiles, sizes, routes, what the check can and cannot show);
- DEC-096 and DEC-146 (the leakage split);
- DEC-139 (the SDID design and the joint placebo);
- DEC-070 (population-weighted unit values);
- DEC-135 (signs);
- DEC-154 and the Phase 8 wording rule: nothing is an effect of NCAP.

**Before any code: what Reenu must provide** (hard rule 5: credentials are never in code or git).
- **A Google Earth Engine account** registered for non-commercial or research use, and a Google Cloud project with the Earth Engine API enabled. Ask Reenu for the **project id**.
- **Authentication**, run by Reenu: `earthengine authenticate` (OAuth). The credentials land in `~/.config/earthengine/`, outside the repo.
- **The `earthengine-api` package.**
  - Add it to `environment.yml` (conda-forge), and update the lock in update mode for that one package (see "Re-locking on this machine" under Phase 4 below; needs `PYTHONNOUSERSITE=1`).
  - Check the lock diff: only it and its new dependencies should change. Then re-run the tests.
  - **Ask Reenu before changing the locked environment.**

**Then, as in every phase: write the open choices in DECISIONS and push them before any AOD value is computed.** At least these:
- **Product:** `MODIS/061/MCD19A2_GRANULES` (1 km, daily, both overpasses). Verify the collection id and version on the day.
- **QA:** the `AOD_QA` bit fields.
  - Read the MCD19 C6.1 user guide for the exact bits.
  - Keep cloud mask "clear" and QA "best".
  - Fix how adjacency and glint are handled.
- **Daily value:** `Optical_Depth_055` × its scale factor (verify; 0.001), averaged over the day's overpasses.
- **Unit value.**
  - Population-weighted (DEC-070), with GHS-POP 2020 weights matching our 30 arc-second file. Verify which GEE GHSL asset and epoch match `data/raw/ghsl`.
  - Area-weighted as the sensitivity.
  - If the weights cannot be matched exactly, say so and decide.
- **Aggregation.**
  - Unit-month mean and valid pixel-day count; the annual value from the monthly means.
  - Fix the minimum valid days per month and valid months per year before looking (the July–August monsoon is cloudy).
- **Units:** the 1,036 Layer A units. Roles (treated / control) are in `data/processed/causal/design_units.csv`; polygons are in `data/interim/sat_units.gpkg`. Upload them to GEE as a FeatureCollection asset, or pass them in the script.
- **Raw data (hard rule 7).**
  - The exported table (unit × month × fields, CSV, < 0.5 GB) is the raw file. **Confirm its size before exporting.**
  - It goes in `data/raw/maiac_gee/`, with a manifest: GEE script commit, collection id, export date, sha256.
  - The GEE script lives in `src/acquire/maiac_gee.py`. Nothing is done by clicking in the GEE web interface.
- **Analysis:** the Phase 7 SDID engine (`src/causal/sdid.R`, through `layer_a` specs) on log annual AOD, 2010–2024 without 2020:
  - the primary design (113 treated, 923 controls, listing cohorts, joint placebo 500);
  - the gained/not-gained leakage split and its difference (DEC-146);
  - a rule, fixed in advance, for how these are read against ACAG's numbers (+3.6% primary; +2.5% vs +5.5%; difference −2.8%).
  - Run time: about 1–1.5 h **on mains power**. On battery, Windows throttles the R workers to about a tenth of normal speed (DEC-168).
- **Outputs.**
  - The "Raw MAIAC AOD" row of the robustness table (`docs/causal_report.md` §9). Decide in the rules whether an AOD log-change belongs on the "agrees" scale. It probably does not, in which case it is reported as information and the "17 of 19" count is unchanged.
  - A short report section.
  - A phase note, `docs/phase-notes/08b-maiac.md`.

**FIRMS is closed** (DEC-173): 2012–2024 is downloaded and used; Reenu decided not to fetch January 2025 – March 2026.

## Phase 8 (heterogeneity and mechanism, RQ4): DONE and approved (2026-10-03)

**Approved by Reenu 2026-10-03.** Closing items:
- figure 7's panel change is logged as a deviation (DEC-170);
- CI passed on the final Phase 8 commit (run 37045282068);
- FIRMS was downloaded and the fire check run (DEC-171/172).

After Phase 8b comes Phase 9: figures 1–8 to the style rules, and the read-only dashboard (cut item #3 if time runs short).

**Rules:** DEC-162 to DEC-167, pushed in `2f80dc4` before any Phase 8 number. Results DEC-168; workflow DEC-169. Housekeeping DEC-161 (`ncap_prev` removed; DEC-155's order of events stated in DEC-155 and `causal_report.md` §11). **Wording:** H1 is not identified, so every per-unit number and H5 are "city-level relative changes", never effects of NCAP, with the caveat beside each.

**Results** (numbers in `docs/heterogeneity_report.md`; DEC-168):
- **City-level estimates:** 113 per-unit SDIDs. The SE is the SD over 923 single-control placebos (about 0.05 log units). The mean is +3.5%. BH 5%: 0 of 113 pass.
- **Hierarchical model:** all 5 versions converged at the first attempt. τ = 0.013, so shrinkage is strong. The average city-level relative change is +3.5% (+2.6% to +4.4%). The median 95% rank interval spans 75 of 113 places.
- **H5: the registered rule is NOT met.** β_IGP = −0.3% (−3.3% to +2.6%). The IGP-only model gives −2.6% (−4.6% to −0.4%); it does not decide.
- **H3: inconclusive.** (iii) fails (known in advance); (i) fails (ratio ITS +4.5%, CI −0.0% to +9.2%; DiD +0.6%); (ii) fails (ITS 2/3, DiD 0/3). 11 cities.
- **Dose (exploratory):** 40 XV-FC units. −0.4% per doubling of the allocation (−3.5% to +2.7%). Per-person allocations are nearly constant within a state, so the dose is really "which state".
- **MAIAC scoping:** `docs/maiac_scoping.md`. MCD19A2 1 km; 9 tiles; full granules about 330 GB. Recommended: reduce to unit-month means on Google Earth Engine or AppEEARS (< 0.5 GB), then about 1–1.5 h of SDID. Nothing downloaded.

**How to rebuild Phase 8:** `snakemake --cores 1 hierarchical` (gated; about 40 min on mains power). Or, inside the `ncap` env:
```bash
python -m src.hierarchical.city_estimates run     # per-unit + placebo SDID, 5,764 fits (~40 min; resumable, saves every 200 fits)
python -m src.hierarchical.city_estimates table
python -m src.hierarchical.pooling                # PyMC, 5 models (~10 min)
python -m src.hierarchical.dose                   # exploratory (~5 min)
python -m src.hierarchical.mechanism              # H3 (~1 min)
python -m src.viz.fig5_city_map; python -m src.viz.fig6_shrinkage; python -m src.viz.fig7_mechanism
python -m src.hierarchical.report                 # -> docs/heterogeneity_report.md
```
**Run on mains power.** On battery, Windows throttles the R workers to about a tenth of normal speed (DEC-168).

**Code:**
- `src/hierarchical/unit_sdid.R`: per-unit and single-unit placebo SDID, with the pre-fit SD.
- `src/hierarchical/city_estimates.py`: SEs, placebo p, BH, moderators.
- `src/hierarchical/pooling.py`: the measurement-error model, the convergence rule, the versions, H5.
- `src/hierarchical/dose.py`.
- `src/hierarchical/mechanism.py`: H3, reusing Phase 7's Layer B functions.
- `src/hierarchical/report.py`.
- `src/viz/fig5_city_map.py`, `fig6_shrinkage.py`, `fig7_mechanism.py`.
- `workflow/rules/hierarchical.smk` (real, gated rules).
- `tests/test_hierarchical.py` (9, synthetic). The full suite has 208 tests.

**Outputs:** `data/processed/hierarchical/`: `unit_sdid_*.parquet`, `city_estimates.csv`, `pool_*.csv`, `city_shrunken.csv`, `h5.json`, `h3*.csv/json`, `dose_*.csv`; `docs/heterogeneity_report.md`; `reports/figures/fig5_city_map`, `fig6_shrinkage`, `fig7_mechanism`.

**Decided by Reenu (2026-10-03):** the MAIAC check runs through Google Earth Engine, as Phase 8b (above). The VIIRS fire check has been run, and it agrees (DEC-172).

## Phase 7 (causal analysis, RQ3): DONE and approved (2026-10-02)

**Next:** Reenu reviews Part B. Then Phase 8 (heterogeneity and mechanism: hierarchical model of city effects, H5, H3 with DEC-135's readings; H3 (iii) uses the triangulation categories of DEC-150: neither pair may be "conflict", and the ITS pair IS "conflict").

**Part B result (DEC-159; review additions DEC-154 to DEC-158; phase note `docs/phase-notes/07-causal.md`):**
- **Wording (DEC-154):** the positive Layer A estimates are never an effect of NCAP. The fixed sentence: "NCAP units' satellite PM2.5 did not fall relative to comparable units; the estimates point to a relative rise of about 3–5%", always beside "not identified".
- **Layer B (secondary):** PM2.5 ITS −14.0%, ground DiD −4.7% (CI includes 0); PM10 ITS −5.0%, DiD +9.2%. 18 / 13 cities, mostly single stations, against 5–6 control cities.
- **Triangulation:** Layer A restricted +3.8%. Against the DiD: uninformative; against the ITS: conflict. In the investigation, ground and satellite agree on the before–after fall in the same cities (−13.4% vs −11.1%), so the conflict is about the estimand, not the measurement.
- **Robustness:** Layer A 17/19 agree, all positive (the VIIRS fire check, run 2026-10-03, agrees: +3.1%; DEC-172); Layer B 26/32 per pollutant. MAIAC not run (Phase 8b).
- **Descriptive:** 2018 → 2024, NCAP units −16.8%, control pool −24.3%.
- **Exploratory (DEC-155):** population overlap +3.7% / +3.0%.
- **Environment (DEC-156):** win-64 lock without conda's r-matrix / r-rcppeigen / r-bmisc / r-rcpparmadillo; CRAN binaries via `install_r_extra.R`. Built fresh as `ncap_new`; 199 tests passed; it then replaced `ncap` (old kept as `ncap_prev`; DEC-160).
- **CI:** the DAG check failed on undeclared EDA outputs; fixed (DEC-158).
- **FIRMS:** downloaded 2026-10-03 (2012–2024); the VIIRS check has been run (DEC-171/172).
- **Rebuild in the new environment (DEC-160):** Part A plus every quick Part B step reproduce. 272 of 300 files are byte-identical, the rest within 1.4e-13, and the report is unchanged. Part B's SDID and leave-one-out outputs were carried over (Reenu's choice). `snakemake -n causal` and `-n pregate` have nothing to do. A rebuild of Phases 2–6 from raw is left for Phase 10.

**How to rebuild all of Phase 7:** `snakemake --cores 1 causal` (gated; ~5 h: SDID ~3.5 h, leave-one-out ~50 min, HonestDiD ~11 min).

**Rules:** DEC-138 to DEC-150, committed and pushed in `eebaecc` before any Phase 7 estimate (Part A and Part B both). Reenu's instruction (2026-10-01): implement plan §5 exactly with DEC-135's readings; any departure is a dated deviation; **checkpoint after Part A** (push, report H1/H2 in the registered wording with every rule check), then Part B only after her go-ahead.

**Part A result (DEC-151; numbers in `docs/causal_report.md`, figure `reports/figures/fig4_event_study`):**
- **H1: "not identified by this design"**, because rule (b) fails (event-study pre-trend Wald p = 0.0008). Rule (c) holds (2016 placebo −0.1%). Rules (a) and (d) fail too: every estimate is an *increase*. Primary SDID +3.6% (95% CI +2.4% to +4.8%); CS +4.6%; area-weighted +3.5%; V6.GL.03 +3.2%.
- **HonestDiD:** original CI above 0; relative-magnitudes breakdown M̄ = 0.20.
- **H2 not tested;** exploratory winter − non-winter +0.1%.
- **Calibration-leakage warning fires** (difference −2.8%, CI −5.1% to −0.5%; both groups are increases).
- **Environment (DEC-138):** CRAN binaries of Matrix/RcppArmadillo/RcppEigen on Windows (conda-forge's builds stopped loading); HonestDiD 0.2.8 installed. **Implementation fixes and checks (DEC-152):** none changes a specification.
- ~~VIIRS fire check waiting for FIRMS~~: run 2026-10-03, agrees (DEC-172).

**How to rebuild Part A:** `snakemake --cores 1 causal` (gated). Or, inside the `ncap` env:
```bash
python -m src.causal.era5_units           # ERA5 monthly -> unit-year covariates (~20 s)
python -m src.causal.layer_a panels       # satellite panels, Asansol-alone value (~35 s)
python -m src.causal.layer_a specs        # every SDID specification (Part A and Part B)
python -m src.causal.layer_a run primary v6gl03 area placebo2016 placebo2016_rm   # ~83 min, resumable
python -m src.causal.layer_a summarise
python -m src.causal.event_study          # Sun & Abraham (~20 s)
python -m src.causal.r_steps cs           # Callaway & Sant'Anna (~15 s)
python -m src.causal.r_steps honest       # HonestDiD (~11 min)
python -m src.causal.causal_report        # -> docs/causal_report.md, data/processed/causal/partA_results.json
python -m src.viz.fig4_event_study
```
Workflow: `snakemake --touch` was used for upstream outputs after adding the `causal:` config block, and for the 83-minute SDID rule run by hand with the rule's own command (as DEC-108/134). The seven quick Part A rules then ran through Snakemake (log `data/interim/logs/snakemake_phase7_partA.log`).

**Part B, step by step** (inside the `ncap` env, after Part A):
```bash
python -m src.causal.layer_a run v6gl0204 towns towns_nopatancheruvu asansol_alone treated100k spill25 funded anticip2018 incl2020 noigp restricted_pm25 restricted_pm25_v6gl0204 explore_support_minmax explore_support_q5_95   # ~2 h
python -m src.causal.layer_a loo primary          # ~50 min (all 923 donors have weight > 0)
python -m src.causal.layer_a summarise
python -m src.causal.layer_b                      # ground ITS / DiD and checks (~1 min)
python -m src.causal.descriptive                  # levels.csv
python -m src.causal.triangulation
python -m src.causal.robustness
python -m src.causal.causal_report
python -m src.viz.figS1_levels
python -m src.viz.fig1_decomposition --policy     # figure 1 with the Phase 7 step (gated; v1 stays Phase 6's)
python -m src.viz.fig4_event_study
```

**Build plan (files and functions):**
- `src/causal/era5_units.py`: ERA5 monthly means → unit-year covariates (`data/processed/causal/era5_unit_year.parquet`; DEC-142).
- `src/causal/layer_a.py`: `panels()` (annual + season panels for every product and weighting, Asansol-alone value; gated), `specs()` (membership, fit sets and estimands of every SDID specification, DEC-139/145/146/147/150), `run()` (calls `sdid.R`), `summarise()` (ATT, SE, CIs, permutation p, equivalence, leakage) → `data/processed/causal/`.
- `src/causal/sdid.R`: generic, resumable SDID engine: per-spec real fits, joint-placebo replications in chunks, effect curves, unit weights, leave-one-out donors.
- `src/causal/event_study.py`: Sun & Abraham via pyfixest (`sa_design`, `fit`, `aggregate`, `wald`), 2020 own-coefficient fit, Himalayan 5-region variant.
- `src/causal/honest.R` (HonestDiD) and `src/causal/cs_did.R` (Callaway & Sant'Anna).
- `src/causal/decisions.py`: H1 verdict (DEC-141), equivalence, targets, H2, leakage warning, robustness "agrees", layer categories (DEC-135).
- `src/causal/layer_b.py` (Part B): ITS, ground DiD, the Layer B checks; `src/causal/triangulation.py` (Part B).
- `src/causal/causal_report.py` → `docs/causal_report.md` (generated). `src/viz/fig4_event_study.py`; figure 1's policy step (Part B).
- `workflow/rules/causal.smk`: real, gated rules. `tests/test_causal.py`: synthetic tests of every rule.

**Run-time estimate** (8 workers; ~0.38 s per SDID fit at full size, scaled from Phase 4's measured 8,000 fits in 35 min by a synthetic timing test):
- **Part A ≈ 1.5–2 h:** primary + seasonal + level + leakage joint placebo (9,000 fits, ~60 min); V6.GL.03 and area-weighted with SEs (3,000 fits, ~20 min); 2016 placebo (1,000 short fits, ~5 min); ERA5 covariates, event study, HonestDiD, CS (~20–30 min).
- **Robustness battery (Part B) ≈ 2.5–3 h:** 13 more SDID specifications with SEs (~2 h), leave-one-out donors (≤ 2,800 fits, ~20 min), Layer B estimators and checks with bootstraps (~20 min).
- Neither exceeds 6 h.

## Next: Phase 7 (causal analysis, RQ3). Handoff notes written at the end of Phase 6

**Phase 6 was reviewed and closed by Reenu on 2026-10-01** (DEC-135 to DEC-137). Start Phase 7. Per CLAUDE.md:
- write a short plan first (files and functions);
- fix any rule the plan leaves open in DECISIONS, and commit it before computing (the practice since Phase 5);
- build;
- at the end: run the tests, commit and push, update this file and DECISIONS, write `docs/phase-notes/07-causal.md`, and stop.

**Spec:**
- proposal stage 7 and the validation table;
- PLAN.md §4 Phase 7;
- `docs/analysis_plan.md` §2 (treatment, controls), §4 (variables), §5 (models, decision rules, leakage check, triangulation, the robustness table);
- the gate is open (`config/gate.yaml` cites `6e24eca`).

**Binding readings of the registered rules (DEC-135, committed and pushed in `ba397a2` before any Phase 7 computation).** Apply them exactly:
- **Sign convention:** effect = treated − counterfactual on log concentration; negative = reduction.
- **H1:**
  - (a) ATT < 0 with its 95% CI entirely below 0;
  - (d) the point estimate < 0 in CS, area-weighted and V6.GL.03.
- **Equivalence:** the 90% CI strictly between ln 0.95 and ln 1.05, as registered (asymmetric).
- **H2:** the winter − non-winter difference < 0, with its CI entirely below 0.
- **H3:**
  - the log(PM2.5/PM10) effect > 0 with its CI above 0;
  - β_PM10 < β_PM2.5 **and** β_PM10 < 0 in ≥ 2 of 3 specifications;
  - the Layer A vs Layer B PM2.5 comparison is not "conflict".
- **H5:** the IGP coefficient (IGP = 1; effect in IGP minus elsewhere) has its credible interval above 0.
- **Robustness "agrees":** same sign as the primary, and the point estimate inside the primary 95% CI, on the same scale.
- **Layer-disagreement categories, in this order:** uninformative → conflict → consistent → different magnitude → "unclassified". Every category except consistent triggers the registered investigation.

**Carried into Phase 7 (added checks, not rule changes):**
- **Layer B without 2019 (DEC-123):** rerun the ground-layer estimates excluding 2019. Label it as added on 2026-09-28. Phase 6 adds a reason: under the 2019 baseline, the GAM's raw − deweathered part is almost all unmodelled change (DEC-137).
- **Satna post-hoc drop** in every registered-flags version where site_1433 contributes (DEC-124; `config/params.yaml: posthoc_drop_registered`). Label it "added after inspecting the data". Satna's unit (u0908) is a control, so it can enter ground DiD as a control station.
- **LightGBM beside the GAM** wherever deweathered ground data are used (DEC-118). Layer B's deweathered series drop each station's unmodelled change (DEC-133/136).
- **Triangulation inputs from Phase 6:**
  - investigation step 1 (network composition) = `data/processed/composition/city_changes.parquet` and `trends.parquet`;
  - step 2 (ground–satellite) = `ground_sat.csv`. The mean gap is small, but per-city gaps are large (single monitors in Agra, Lucknow, Kanpur and Jodhpur fell 45–63% where the satellite fell 22–27%).
- **Single-station panels dominate** the ground layer (16 of 18 PM2.5 and 11 of 13 PM10 NCAP panels). State the scope wherever a Layer B result appears, as for H4 (DEC-136).
- **No claims about individual weather variables** anywhere (DEC-136).
- **HonestDiD 0.2.8:** install via `workflow/scripts/install_r_extra.R` (DEC-097) before the event study.

**For Reenu:** post the OSF clarification, `docs/osf/clarification_2026-10-01.md` (159 words, first person). It covers DEC-127 and DEC-135, with the commit hashes.

## Phase 6 (network composition, RQ1 and H4): what was built (2026-09-30; review changes 2026-10-01)

**Rules first:**
- DEC-125 to DEC-130 in `29874cf` and DEC-131 in `2254a70`, both before any Phase 6 number was computed. Results: DEC-132.
- Method change after a failed pre-set check: DEC-133.
- Review: DEC-135 (sign audit of every registered rule; `ba397a2`, pushed before Phase 7), then DEC-136 (weather split, scope, no per-variable claims; `86e62c7`, before computing). Split results: DEC-137.

**How to rebuild:** `snakemake --cores 1 composition`. Or, inside the `ncap` env:
```bash
python -m src.normalise.composition          # ~2-3 min (reads every Phase 5 fit for the fitted means); all tables
python -m src.normalise.family_diag          # ~25-30 min (LightGBM TreeSHAP for the pre-set log-scale split)
python -m src.viz.fig1_decomposition
python -m src.normalise.composition_report   # -> docs/composition_report.md
```

**Code:**
- `src/normalise/composition.py`:
  - `Spec` (one version) and `specs()` (the 31 versions of DEC-128);
  - `select`, `panel_members`, `mark_panel`;
  - `decompose` (reported = unmodelled + modelled weather + composition + corrected);
  - `city_changes`, `station_bootstrap`, `cluster_boot`, `h4_table`;
  - `trends`, `composition_by_year`, `ground_vs_sat`, `entrants`, `coverage`;
  - `fitted_station_years` (DEC-136).
- `src/normalise/family_diag.py` + `family_terms.R`: GAM terms, LightGBM SHAP, the annual-mean attribution (DEC-133), ERA5 summaries, `misfit_h4`. The per-variable outputs are kept for the record only; no per-variable claims (DEC-136).
- `src/normalise/composition_report.py`, `src/viz/fig1_decomposition.py`.
- `workflow/rules/composition.smk` (real rules).
- Tests: `tests/test_composition.py` (15, synthetic); full suite 174 passed.

**Outputs:** `data/processed/composition/`:
- `city_changes.parquet`, `summary.csv`, `h4.csv`, `city_boot.csv`;
- `trends.parquet`, `composition_by_year.csv`;
- `ground_sat*.csv`, `entrants*.csv`, `coverage.csv`;
- `station_year_fitted.parquet`, `family_diag_*.csv`.

OSF clarification draft: `docs/osf/clarification_2026-10-01.md`.

**Results in brief** (numbers in `docs/composition_report.md`). H4's scope: only the 18 (PM2.5) and 13 (PM10) NCAP cities with a station valid every year 2018–2025, mostly single stations.
- **H4 supported** in the primary version:
  - PM2.5 +9.5 pp (95% CI +4.8 to +14.5) = unmodelled +0.8, modelled weather +2.9, composition +5.8;
  - PM10 +6.0 (+1.8 to +10.0) = −0.5, +5.4, +1.0;
  - LightGBM beside it: +8.6 / +5.3;
  - as registered, no deviations: +10.3 / +6.5.
  - It fails in 2 of 31 PM10 versions: LightGBM with the 2019 baseline, and no deweathering.
  - With the 2019 baseline, the GAM's raw − deweathered part is almost all unmodelled change (DEC-137).
- **Composition bias (all 23 PM2.5 panel cities):** −3.7 pp (−7.2 to −0.4), appearing from 2022–23. PM10: +0.9 (−1.1 to +3.3).
- **Ground vs satellite (PM2.5, 2018 → 2024):** mean gap +3.0 pp (−5.0 to +10.6); correlation of changes 0.68. Per-city gaps are large.
- **New stations read cleaner** (PM2.5 −6.3% raw, −6.8% deweathered; paired −0.6 pp, CI spans 0): location, not weather.
- **Family disagreement:** in 8 of 13 flagged city-pollutants the GAM–LightGBM gap is mostly the GAM's misfit (change it reproduces with neither trend nor weather), not modelled weather.

**Workflow notes:** DEC-134 and DEC-137 (`snakemake --touch` after the config block; Snakemake re-runs; `snakemake -n pregate` has nothing to do).

## Phase 5 (deweathering, RQ2): how it was built and run

**How to rebuild Phase 5:** `snakemake --cores 1 normalise`. Or step by step (`both` = lgbm and gam; gam = one-year-knot trend, gam_k4 = previous trend):
```bash
python -m src.clean.nearconstant
python -m src.normalise.run prepare --run main
python -m src.normalise.run prepare --run registered
python -m src.normalise.run fit --run main --family both
python -m src.normalise.run fit --run main --family gam_k4
python -m src.normalise.run fit --run registered --family both
python -m src.normalise.run fit --run registered --family gam_k4
python -m src.normalise.run cvcheck --run main --family both        # and --family gam_k4
python -m src.normalise.run cvcheck --run registered --family both  # and --family gam_k4
python -m src.normalise.guard
python -m src.normalise.run fit --run main --family gam_lock --sids <the 20 pilot sids>   # DEC-119 test
python -m src.normalise.lockdown_test
python -m src.normalise.city_disagreement
python -m src.normalise.aggregate
python -m src.normalise.report
python -m src.viz.fig3_deweathered --scheme seasonal
python -m src.viz.fig3_deweathered --scheme annual
python -m src.viz.fig3_deweathered --view annual
```
The fits are resumable per series: re-run the same command after a crash or sleep. Measured run time on this laptop (8 workers): each GAM family about 1–1.5 h, LightGBM about 7 h, registered refits and CV checks about 1 h, guard about 8 min, aggregation about 8 min.

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
- `src/clean/nearconstant.py` (DEC-110), `src/normalise/guard.py` (DEC-117); `src/normalise/lockdown_test.py` (DEC-119), `src/normalise/city_disagreement.py` (DEC-120); tests: `tests/test_normalise.py` (25, synthetic); full suite 159 passed.
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
- ~~Trend absorption~~: resolved by the GAM refit with one-year knots (DEC-116 to DEC-118).
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

- ~~FIRMS~~: closed. 2012–2024 is downloaded and used; January 2025 – March 2026 will not be fetched (Reenu, DEC-173).
- **Mirror provenance** is one step removed from CPCB (DEC-037). Mitigations: sha256 pinning, the cross-check (2019–21 value-identical), and ODbL for any derived dataset we publish.
- **Pre-2018 ground network is tiny**: PM10 has 9 valid station-years in 2017 and 66 in 2018. Ground-based and PM10 results are secondary (analysis plan §0).
- **Stations with no coordinate anywhere** keep an approximate city point (count in `docs/station_metadata_review.md`); they stay out of neighbour checks.
- ~~ERA5 cells for newly located stations~~: resolved in Phase 5 (20 cells fetched, DEC-100).
- **V6.GL.03 has no methods note.** If one appears, revisit DEC-001.
- **The treatment definition** (listed vs funded) is proposed in `docs/analysis_plan.md` (listed primary) and decided by Reenu at the gate.
- **No LICENSE file yet, and the repo is public (since 2026-09-27).** Reenu to choose a code licence. Any derived dataset from the CPCB mirror must be ODbL (DEC-037).
- **Jan–Mar 2026 ground data are provisional** (OpenAQ raw feed, DEC-079).
- **The locked `wcwidth 0.9.1` build (`pyh5ded981_0`) is no longer on conda-forge's main label** (found 2026-10-03, DEC-182). `conda-lock install` still works, because it fetches each package by its exact URL: CI's linux-64 install from the updated lock passed (runs 37066116964, 37066872977, 37081522142). A fresh *solve* from `environment.yml` would pick another build. Recheck in the Phase 10 clean-clone test.
- **Earth Engine exports are not byte-reproducible** (about 8 significant figures, DEC-184). The raw MAIAC tables are pinned by sha256; re-exporting them would need credentials and about 170 EECU-hours.
- **Outputs are not byte-deterministic** (GeoPackage timestamps, tie order in DuckDB/pandas writes, SVG dates and ids; DEC-094). Content and numbers reproduce. Fix before the Phase 10 clean-clone check.
- Possible extension (not scheduled): the official PRANA/NAMP PM10 series as a "reported" reference (DEC-016).

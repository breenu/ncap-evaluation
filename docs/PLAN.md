# PLAN: NCAP evaluation, Phase 0

*Status: Phase 0 reviewed and approved by Reenu on 2026-09-26. Answers are recorded in §8 and logged in `DECISIONS.md`.*

*Written 2026-09-26, after reading `CLAUDE.md` and all 20 pages of `docs/proposal.pdf`. Facts marked ✔ were checked against the live source today. Facts marked ⚠ could not be confirmed and are checked first in Phase 2.*

## 1. Summary: where this plan departs from the proposal

The proposal stays the spec. The changes below make the work cheaper, faster or more defensible without changing the research questions or cutting the core. Each one becomes a `DECISIONS.md` entry once you agree (§8).

| # | Proposal says | Plan does | Why |
|---|---|---|---|
| D1 | ACAG **V6.GL.02.04** and **V5.GL.05.02**, 1998–2023 | Use **V5.GL.06** as primary (documented on satpm.org), **V6.GL.03** for the version comparison, and **V6.GL.02.04** as the vintage check. All but V6.GL.02.04 cover **1998–2024** ✔. *(Revised at review: V6.GL.03 has no published methods note.)* | This adds a sixth post-treatment year, 2024, and shrinks the "satellite ends in 2023" limitation. Comparing vintages also partly tests whether ground-network growth leaks into the satellite product (proposal threat #3). |
| D2 | Download ACAG from Box, global files | Download the **Asia-region files** from the public AWS bucket `s3://satpmdata` with no sign-in and no key ✔ | Global 0.01° monthly files are about 437 MB each. The Asia annual files are about 92 MB each (V6) and 18 MB each (V5). This is scriptable, has checksums through ETags, and avoids Box links. |
| D3 | ERA5 through `cdsapi`, or Open-Meteo | Use one source: the CDS **ERA5 hourly time-series** point dataset (`reanalysis-era5-single-levels-timeseries`) for the station grid cells. Use the **ERA5 monthly means** for an India bounding box for the satellite layer. | The point dataset has every variable the model needs, including **boundary-layer height**, solar radiation and precipitation ✔. It returns long point series quickly and never touches all-India hourly data. The free Open-Meteo tier is capped at 10,000 weighted calls a day ✔, so about 400 points × 11 years would take days. Open-Meteo stays as a no-key fallback. |
| D4 | OpenAQ API v3 | Use the **OpenAQ S3 archive** (`openaq-data-archive`, no key, no rate limit ✔) for the measurements. Use the v3 API only for station metadata. | The API is limited to about 2,000 requests an hour. Hourly PM data for about 1,200 station-pollutant series would need over 100,000 paged calls. |
| D5 | GHSL + WorldPop | Use **GHSL UCDB R2024A** for boundaries and populations, plus GHS-POP only for an optional population-weighted sensitivity check. **Drop WorldPop.** | UCDB already carries multi-year population. WorldPop would add a second, inconsistent population model for no gain. |
| D6 | pyGAM or mgcv | Use **mgcv only**, called from R. | pyGAM has no REML smoothing selection and is weakly maintained. mgcv is the reference implementation and easier to defend. |
| D7 | pdfplumber or camelot | Use **pdfplumber only.** | camelot needs Ghostscript on Windows. One tool is enough. |
| D8 | Makefile or Snakemake | Use **Snakemake only.** `snakemake --cores 8 all` is the single entry point. | Neither is installed. Make is awkward on Windows, and Snakemake handles the file DAG, R steps and partial rebuilds natively. |
| D9 | FIRMS VIIRS only | Use **MODIS C6.1 (2000+) for the covariate**. Keep VIIRS as a 2012+ check. | VIIRS starts in January 2012, but the satellite panel starts in about 2010, so a VIIRS covariate would leave pre-period years missing. |
| D10 | Ground data 2015 onward | Extend the ground window to **31 Mar 2026**. | NCAP targets are for financial years, and FY2025-26 ended in March 2026. |
| D11 | Analysis-plan gate is a process rule | Enforce it in code as well. `config/gate.yaml: analysis_plan_approved: false`. Every causal rule checks the flag and refuses to run while it is false. | This makes Hard Rule 4 mechanical instead of relying on discipline. |
| D12 | MDE reported at the end | **Compute the minimum detectable effect (MDE) before the gate**, by placebo-in-time on pre-2019 satellite data only. | Rule 4 allows pre-2019 checks. Knowing the MDE up front makes `analysis_plan.md` state realistic decision rules. |

Approved at review: D1 (revised), D2–D12. Tooling additions that are not in the proposal, also approved: `conda-lock` for exact pinning, and a GitHub Actions job that runs `pytest` on synthetic fixtures only (cheap insurance for the clean-clone check in Phase 10).

## 2. Data sources: access, sizes, verification status

Totals are about **8–15 GB raw**, most of it the OpenAQ archive. Free disk is about 169 GB. The two items marked ⚑ exceed the ~2 GB threshold, so I will re-confirm exact sizes with you before downloading them (Hard Rule 6).

| Source | What we take | Access / key | Est. size | Status |
|---|---|---|---|---|
| **CAAQMS through OpenAQ S3 archive** ⚑ | Hourly PM2.5 and PM10, plus NO2 as a secondary check, for all Indian locations, 2015-01 to 2026-03 | S3 anonymous. OpenAQ v3 API key for location metadata (IDs, coordinates, first and last dates) | **3–8 GB** compressed; about 1–1.5 M small daily `csv.gz` files | ⚠ India coverage unknown: one secondary source says the legacy CPCB provider tree stops in 2022. **First task of Phase 2 is a coverage probe.** |
| CPCB CCR portal (fallback) | Same, for gaps | Web portal with captcha; about 1 week of 15-min data per query ✔. Hourly and daily queries allow longer ranges. | Depends on the gaps | Only if the probe shows gaps. It may need manual downloads by you. |
| **ACAG V5.GL.06 SatPM2.5 (primary)** | Annual 0.01° Asia 2005–2024, annual uncertainty grids, monthly 0.05° Asia (seasonal analysis; ⚠ confirm folder) | `s3://satpmdata/V5GL06/…` anonymous | About 0.36 GB + 0.18 GB ✔, monthly coarse < 0.5 GB | Documented on satpm.org, 1998–2024 ✔ |
| ACAG V6.GL.03 (comparison) ⚑ | Annual 0.01° Asia 2005–2024 | `s3://satpmdata/V6GL03/…` | About **1.8 GB** (20 × 92 MB ✔) | The bucket has no methods note or README (checked 2026-09-26). The files were uploaded 2026-09-22. |
| ACAG V6.GL.02.04 (vintage check) ⚑ | Annual 0.01° Asia 2005–2023 | `s3://satpmdata/V6GL0204/…` | About 1.8 GB | Approved (Q1) |
| **ERA5 hourly time-series** | T2m, Td2m, u10, v10, BLH, total precipitation, SSRD at unique 0.25° cells containing stations (about 300–450), 2015-01 to 2026-03 | CDS account + API key in `~/.cdsapirc`; accept the ERA5 licence | About 1 GB | Variables ✔ |
| **ERA5 monthly means** | Same variables, India bounding box (6–38°N, 68–98°E), 2005–2024 | Same key | About 0.1 GB | Standard product |
| **GHSL UCDB R2024A** | Urban-centre polygons, population by epoch, 11,422 centres worldwide ✔ | Direct download, GPKG | < 1 GB (⚠ exact size) | ✔ release exists |
| GHS-POP 2020, 1 km (optional) | Population weights inside polygons | Direct download, tiles covering India | < 0.2 GB | Sensitivity only |
| **NASA FIRMS** | MODIS C6.1 (2000+) and VIIRS S-NPP (2012+) India detections and FRP | Country yearly CSV archive (probably no key); otherwise a free MAP_KEY (5,000 transactions per 10 min ✔) | About 0.5–1.5 GB | ⚠ endpoint did not respond during today's check. Lowest priority (cut item #4). |
| **NCAP treatment data** | City list, date added, funding channel, allocations, releases, utilisation | PRANA, PIB, sansad.in PDFs; pdfplumber | < 0.1 GB | ⚠ counts to reconcile: the proposal says 49 XV-FC + 82 MoEFCC = 131. Other sources say "48 million-plus cities/UAs" under XV-FC, and PIB says "131 cities". |
| State boundaries | Region assignment (IGP, coastal, peninsular, NE) and maps | DataMeet or Survey-of-India-consistent boundaries | < 0.05 GB | Choice logged in DECISIONS |

Access actions for you, in order of need: **CDS account and key** and **OpenAQ key** (both at the start of Phase 2). **FIRMS MAP_KEY** only if the keyless archive fails.

## 3. Architecture (Phase 1 builds this)

- **Environment:** Miniforge (conda-forge) with one `environment.yml`: Python 3.12 (not the system 3.14, where the scientific wheels lag) plus R 4.4 with `mgcv`, `did`, `arrow`, and `synthdid` installed from a pinned GitHub commit. It is not on CRAN. Exact pins go in `conda-lock.yml` for win-64 and linux-64. Quarto is installed at Phase 10.
- **Languages:** Python for everything except three R steps: GAM deweathering (`mgcv`), SDID (`synthdid`) and Callaway & Sant'Anna (`did`). These are the reference implementations by the methods' own authors. R scripts read and write Parquet, so there is no rpy2.
- **Data:** polars + DuckDB + Parquet. One DuckDB file (`data/processed/ncap.duckdb`) holds *views* over Parquet, so it is always rebuildable. Raw data is immutable, with `data/raw/<source>/MANIFEST.csv` recording url, s3_key/etag, download date, sha256 and bytes.
- **Orchestration:** `Snakefile` plus `workflow/rules/*.smk`, one per stage. Rules call `python -m src.<stage>.<module>` or `Rscript src/<stage>/<script>.R`. The pipeline is `snakemake --cores 8 all`.
- **Config:** `config/params.yaml` holds thresholds (completeness 75/60/90, flatline N, ceilings, changepoint penalty, population cutoff, resample N, CV folds, seeds). `config/gate.yaml` holds the pre-registration flag. `config/regions.yaml` maps states to regions.
- **Layout:** the proposal's layout exactly, plus `workflow/` for Snakemake rules and `src/common/` for paths, manifest, logging and the gate check.
- **Tests:** pytest with **synthetic fixtures only in `tests/`**, clearly labelled. There is at least one test per cleaning or flagging rule, plus manifest idempotency, PDF-row provenance and the gate guard.

## 4. Phase-by-phase breakdown

Each phase ends by running `pytest`, committing, updating `PROGRESS.md` and `DECISIONS.md`, writing `docs/phase-notes/NN-<name>.md`, and **stopping**.

### Phase 1: Skeleton (about 1 day)
- Files: `README.md` (stub), `environment.yml`, `conda-lock.yml`, `Snakefile`, `workflow/rules/{acquire,clean,eda,normalise,composition,causal,hierarchical,viz,report}.smk` (stub rules that `touch` outputs), `config/{params,gate,regions}.yaml`, `src/{acquire,clean,normalise,causal,hierarchical,viz,common}/__init__.py`, `src/common/{paths,manifest,gate}.py`, `tests/{conftest.py,test_manifest.py,test_gate.py}`, `docs/{PROGRESS,DECISIONS}.md`, `.github/workflows/tests.yml`. The existing `.gitignore` already covers secrets and data ✔.
- **Smoke test on Windows:** import every heavy dependency (lightgbm, pymc, exactextract, rioxarray, geopandas, ruptures) and run `Rscript -e 'library(synthdid); library(did); library(mgcv)'`. Toolchain problems surface here, not in Phase 7.
- Exit: `snakemake -n all` shows a complete DAG, `pytest` passes, and the environment resolves from the lock file.

### Phase 2: Acquisition (about 1 week)
0. **Feasibility probe, before any bulk download:** (a) list every Indian OpenAQ location with first and last dates, plus a coverage matrix of station-months with PM data by year. (b) Confirm the ACAG "AS" region extent covers all of India. (c) Run one CDS time-series request for Delhi. (d) Test FIRMS access. Report sizes and **go/no-go on the ground source to you**. This is the cheapest point to find out that a source doesn't contain what the proposal expects.
1. `src/acquire/openaq.py`: get location metadata (API), then fetch India files from S3 in parallel. Downloads are idempotent: skip when the S3 ETag already matches the manifest. The many small files are **bundled into one uncompressed zip per location-year**, with bytes unchanged and each member's ETag and sha256 in the manifest. The reason is Windows file-count performance; the decision gets logged.
2. `src/acquire/acag.py`: fetch V6GL03 and V5GL06 (and optionally V6GL0204) annual Asia 0.01°, V6GL03 monthly 0.1°, and V5GL06 uncertainty.
3. `src/acquire/era5.py`: build the set of unique station cells from station metadata, then request time series for each cell, plus one monthly-means request for the India bounding box.
4. `src/acquire/ghsl.py`, `src/acquire/firms.py`, `src/acquire/boundaries.py`.
5. `src/acquire/ncap_pdfs.py` downloads the source PDFs. `src/acquire/ncap_extract.py` uses pdfplumber to produce `data/interim/ncap_cities.csv` and `ncap_funding.csv`. **Every row carries `source_doc`, `page`, `table_idx`.** `ncap_validate.py` compares extracted sums with each document's printed totals and writes `docs/ncap_extraction_mismatches.md` for you to check by hand. It also reconciles the 131 vs 130 and 48 vs 49 counts, and dates each city's addition (needed for staggered adoption).
6. Data cards `docs/data-cards/<source>.md`: provenance, licence, version, coverage, known issues and what was verified.
- Tests: manifest skip logic, zip bundling round-trip, PDF-row provenance schema, and total-check logic (synthetic tables).

### Phase 3: Storage, cleaning, audit, EDA for RQ1 (about 1.5 weeks)
- `src/clean/ingest.py`: raw to `data/interim/stations_hourly.parquet`, partitioned by year and pollutant. It handles unit harmonisation, timezone (IST, stored as UTC), and deduplication of stations that appear under more than one OpenAQ provider.
- `src/clean/flags.py`, one pure function per rule, each unit-tested:
  - impossible values: negatives, PM2.5 > PM10 at the same station-hour, ceiling pins such as 999, 985 and 1000
  - flatlines of N or more identical hours
  - Spatial inconsistency (residual z-score against neighbours within k km and against the ACAG cell).
- `src/clean/changepoints.py`: `ruptures` PELT on daily log-PM residuals after removing the seasonal pattern, with the penalty set in config.
- `src/clean/reliability.py`: combines flags into a per-station-year **reliability score** (documented weights), then applies completeness rules at **75% as primary and 60/90 as sensitivity**. Output: `data/processed/station_day.parquet` and `station_year_quality.parquet`.
- `src/clean/missingness.py`: tests whether missingness depends on season, pollution level and year, i.e. whether it is informative (MNAR).
- `src/geo/zonal.py` (inside `src/clean/` or `src/common/`): station-to-UCDB spatial join and the NCAP-city ↔ UCDB **matching table** (`data/interim/ncap_ucdb_match.csv`, with a match method and manual flags for merged agglomerations such as Delhi NCR). **ACAG zonal stats** use exactextract, with area-weighting as primary and population-weighting as sensitivity. Output: `city_year_sat.parquet` and `city_month_sat.parquet` for all urban centres.
- EDA (`src/viz/eda_*.py`): seasonal cycles by region; raw city trends; ground-vs-satellite correlation over time; **station-entry map** (fig 2); data-quality heatmap (fig 8).
- **Blinding rule until the gate:** no figure or table compares NCAP and non-NCAP units after 2018.
- Output: `docs/audit_report.md`, generated from the pipeline with every number templated.

### Phase 4: Analysis-plan gate (about 2 days drafting, plus your review)
- Pre-gate computations, all on pre-2019 data only:
  - MDE by placebo-in-time on 2010–2018 satellite data (assign fake 2014/2015 treatment, estimate the null spread)
  - covariate balance of NCAP vs pool at baseline
  - size of the control pool after the population threshold
- `docs/analysis_plan.md` (about 2 pages) covers:
  - the estimand (ATT of enrolment, annual plus winter/non-winter)
  - hypotheses H1–H3
  - **treatment definition**: primary = listed by Jan 2019, with staggered additions dated from the source documents; alternative = first funding-release year
  - the control pool rules (population ≥ 100k, spillover buffer)
  - the analysis window
  - estimators (SDID primary; event study with region×year FE; Callaway & Sant'Anna; ITS on the ground layer)
  - handling of 2020
  - the full robustness table from the proposal, with decision rules and the MDE
  - how disagreement between layers will be reported
- You review and edit, and may register on OSF. After commit, I flip `gate.yaml` in a separate commit that references the plan's hash.

### Phase 5: Deweathering for RQ2 (about 1 week)
- `src/normalise/features.py`: join station-day with ERA5 daily aggregates (mean T, RH from Td, vector-mean wind speed and direction, daily-mean and afternoon-max BLH, precipitation sum, SSRD sum) plus day of year, weekday and a trend term.
- `src/normalise/lgbm.py` and `src/normalise/gam.R`: fit per station and pollutant on log PM. **Blocked time-series CV** is forward-chaining by year, reporting out-of-sample R² and residual autocorrelation (ACF at lag 1–7).
- `src/normalise/resample.py`: Grange & Carslaw weather resampling. It is **vectorised**, predicting all N resamples × all days as one batch per station. N is chosen by a convergence check (default 300, capped at 1,000). Both model families share the same resample indices.
- Aggregation to city-month and city-year. The LightGBM vs GAM divergence is flagged per station.
- Compute estimate: about 600 stations × 2 pollutants × 2 families, roughly 1–3 hours on 10 cores. Models are saved under `data/processed/models/`.

### Phase 6: Network-composition correction for RQ1 (about 3 days)
- `src/normalise/composition.py` builds three city trends: all stations as reported; a balanced panel (stations valid in the baseline year and every later year, with the baseline year chosen in config and a sensitivity run); and satellite over the UCDB polygon. Composition bias = (1) − (2); ground check = (2) vs (3).
- Figure 1 v1: the decomposition waterfall. The policy bar stays a placeholder until Phase 7.

### Phase 7: Causal analysis for RQ3 (about 2 weeks)
- **Layer A** (`src/causal/panel.py` builds the panel, `sdid.R`, `event_study.py` using pyfixest, and `cs_did.R`):
  - SDID primary, per adoption cohort and then aggregated
  - event study with region×year effects and ERA5 monthly covariates
  - Callaway & Sant'Anna
- **Layer B** (`its.py`, `ground_did.py`): deweathered interrupted time series per NCAP city; ground DiD where control-city stations exist. 2020 gets its own indicator, with an exclude-2020 sensitivity run.
- **Robustness** (`src/causal/robustness.py`, which runs every row of the proposal's table from one config list):
  - placebo in time (2016)
  - placebo in space (≥ 500 permutations)
  - leave-one-out donors
  - exclude 2020; exclude IGP; FIRMS FRP covariate
  - satellite version (V6GL03 vs V5GL06, plus vintage)
  - completeness 60/90
  - no-normalisation baseline
  - FDR for city-level claims
  - spillover buffer; area- vs population-weighted
- Output: `data/processed/results/*.parquet`, figure 4 (event study) and a triangulation table.

### Phase 8: Heterogeneity and mechanism for RQ4 (about 1 week)
- `src/hierarchical/pooling.py` (PyMC): a measurement-error hierarchical model on city effects and their SEs, like the classic "eight schools" setup, with moderators: baseline PM, IGP, log population, coastal, funding channel. Output: figures 5 and 6.
- `dose.py`: effect against **allocated** funds per capita, with the reverse-causality caveat built into the output text. This is cut item #1.
- `mechanism.py`: PM10 vs PM2.5 effects and the change in the PM2.5/PM10 ratio on the ground layer. Output: figure 7.

### Phase 9: Figures and dashboard (about 1 week)
- `src/viz/style.py` sets the shared style: units on every axis, a colour-blind-safe palette (Okabe–Ito / viridis), redundant encoding, and uncertainty on every estimate. There is one module per figure, 1–8, each writing PNG and SVG to `reports/figures/`.
- `dashboard/app.py`: a read-only Streamlit app over precomputed Parquet. This is cut item #3.

### Phase 10: Report and release (about 2 weeks)
- A Quarto report in `reports/report.qmd` (20–30 pages), where every number is inline code reading pipeline outputs.
- `reports/summary.qmd` (one page), `reports/policy_brief.qmd` (2 pages), and the final README.
- A clean-clone rebuild in a fresh directory, with timings recorded, and a tagged release.

## 5. Schedule mapping
The phases fit the proposal's 15 weeks (28 Sep 2026 to 10 Jan 2027):

| Weeks | Phases |
|---|---|
| 1 | Phase 1 |
| 1–3 | Phase 2 |
| 3–5 | Phase 3 |
| 5 | Phase 4 |
| 6–7 | Phase 5 |
| 8 | Phase 6 |
| 9–10 | Phase 7 |
| 11–12 | Phases 8 and 9 |
| 13–15 | Phase 10 |

The application milestone (audit plus deweathered trends by about 22 Nov) holds. The main schedule risk is idle time waiting on the Phase 4 review; see Q8. *Update at review: Reenu has time until November with no academic constraints, so this calendar is an upper bound and phases proceed as soon as each is approved.*

## 6. Risks

| # | Risk | Impact | Mitigation / trigger |
|---|---|---|---|
| R1 | OpenAQ India coverage is patchy: pre-2018, ingestion outages, the legacy tree stopping in 2022 | Layer B, RQ1, RQ2 | Coverage probe first (Phase 2 step 0). Fill from CPCB CCR, possibly with manual downloads. Layer A does not depend on it. |
| R2 | NCAP cities merged into one UCDB polygon (Delhi NCR, Kolkata UA), or too small to be in UCDB | Treatment misassignment | Matching table with a method column; merged units treated as one; a buffer polygon for missing towns; all logged. |
| R3 | ACAG is calibrated to ground monitors, so network growth leaks in | Layer A bias toward the ground trend | Vintage and version comparison; stated as a limitation. The raw MAIAC AOD check is optional if time allows. |
| R4 | PDF tables are inconsistent (city counts, funding totals) | Wrong treatment or dose | Provenance per row, total checks, and a mismatch list for manual verification. Nothing is guessed. |
| R5 | Treatment timing is ambiguous (launch Jan 2019 vs funds flowing 2019–22) | Diluted or mistimed effect | Primary and alternative definitions pre-registered; event study shows timing. |
| R6 | 2020 (COVID, BS-VI switch) | Distorted post-period | Own indicator plus exclude-2020 sensitivity; region×year effects. |
| R7 | Windows toolchain: GDAL, PyTensor compiler, `synthdid` from GitHub | Lost days | conda-forge, a lock file, and the Phase 1 smoke test. Fallback: WSL2 for the R steps. |
| R8 | Low power | Uninformative null | MDE computed before the gate (D12); equivalence bounds. |
| R9 | V6.GL.03 is undocumented or turns out to be a pre-release | Version provenance | Check before Phase 2 downloads; fall back to V6.GL.02.04 (1998–2023). |
| R10 | Information leaks before the gate | Invalidates pre-registration | Code-level gate (D11) plus the blinding rule in Phase 3. |
| R11 | The control pool differs structurally (small towns, missing monitors) | Weak counterfactual | SDID weights, a population threshold, and pre-trend checks; reported honestly. |
| R12 | Station metadata errors (moved, renamed, duplicate IDs) | False changepoints and composition artefacts | Deduplication rules with tests; manual review list in the audit report. |
| R13 | ERA5 at 0.25° misrepresents urban or coastal micro-meteorology | Residual weather in "deweathered" series | Stated limitation; out-of-sample R² and residual diagnostics per station. |

## 7. Out of scope (kept out)
Forecasting models, extra pollutants beyond PM2.5, PM10 and NO2 (secondary), health modelling, source apportionment, live dashboards or APIs, regression discontinuity (RD), causal forests or double ML as the headline method, LLM components, and the Kaggle dataset.

## 8. Questions for Reenu (answered 2026-09-26)
1. **ACAG version.** Should V6.GL.03 (primary) and V5.GL.06 (comparison) replace the proposal's versions, since both run to 2024? Should I also download V6.GL.02.04 as a vintage check (+1.8 GB)? *Recommend yes and yes, conditional on confirming V6.GL.03's release status.*
   → **V5.GL.06 primary; V6.GL.03 comparison; V6.GL.02.04 vintage check (+1.8 GB approved).** Revisit if a V6.GL.03 methods note appears.
2. **Environment.** OK to install Miniforge and use a conda env with Python 3.12 and R 4.4, with R used only for mgcv, synthdid and did? *Recommend yes.*
   → Yes.
3. **Simplifications D5–D9** (drop WorldPop, pyGAM, camelot and Make; use MODIS FRP): OK?
   → Yes.
4. **Keys.** Please create a Copernicus CDS account (and accept the ERA5 licence) and an OpenAQ account before Phase 2. I'll ask for the keys to be placed in `~/.cdsapirc` and `.env`, never pasted into code.
   → Both accounts exist. In Phase 2 I create `~/.cdsapirc` and `.env` with placeholders and say where they are; Reenu pastes the keys.
5. **Download budget.** OK in principle to 8–15 GB total? I'll confirm exact sizes for the OpenAQ archive and ACAG before each item over 2 GB.
   → Approved in principle; still confirm before any item over 2 GB.
6. **Ground window to 31 Mar 2026** (complete FY2025-26): OK?
   → Yes.
7. **The "reported change" bar in the waterfall.** Primary = all-CAAQMS raw PM, which is what CREA and similar trackers use. NCAP's *official* metric is PM10 that also includes NAMP manual stations. Do you want the official PRANA/NAMP figures extracted as an extra reference series? That adds PDF extraction work. *Recommend: only if city-level numbers are published in extractable form.*
   → No. Skip the PRANA/NAMP series for now; noted as a possible extension.
8. **Gate timing.** CLAUDE.md puts the analysis plan after the audit. To avoid idle weeks, may I draft `analysis_plan.md` *during* Phase 3 (it doesn't need post-2019 results), so your review overlaps with the audit? Phase order stays the same.
   → Yes, draft during Phase 3. The gate itself is unchanged.
9. **OSF.** Will you pre-register on OSF? If so, I'll format `analysis_plan.md` to OSF's template.
   → Yes; use OSF's pre-registration template.
10. **Maps.** Use Survey-of-India-consistent boundaries (e.g. DataMeet) for all maps? *Recommend yes, since the audience is Indian policy.*
   → Yes.
11. **Schedule.** Any exam weeks or application deadlines I should plan around?
   → No academic constraints; Reenu has time until November, so phases run as fast as reviews allow rather than to the 15-week calendar.
12. **Repo visibility.** Public on GitHub from Phase 1, or private until release?
   → Private now (confirmed private on GitHub); public after Phase 3.

*Sources checked 2026-09-26:*
- ACAG dataset page (sites.wustl.edu/acag) and satpm.org (V5.GL.06)
- `s3://satpmdata` bucket listing
- CDS `reanalysis-era5-single-levels-timeseries` form
- Open-Meteo docs and terms
- OpenAQ AWS docs and bucket listing
- GHSL UCDB R2024A overview
- NASA FIRMS API docs
- PIB PRID 1989207 (131 cities)
- urbanemissions.info CPCB access guide

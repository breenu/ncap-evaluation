# DECISIONS

Append-only log of judgement calls. Each entry has a date, an ID, the decision, and one or two sentences of reasoning. Do not edit past entries. If a decision changes, add a new entry that references the one it replaces.

---

## 2026-09-26: Phase 0 review (approved by Reenu)

**DEC-001: Primary satellite product is ACAG V5.GL.06.**
V5.GL.06 is documented on satpm.org (GWR method; van Donkelaar et al. 2021, Hammer et al. 2023), covers 1998–2024, and ships uncertainty grids. V6.GL.03 is also in `s3://satpmdata` for 1998–2024. However, neither the ACAG site nor the bucket has a methods note or README for it (checked 2026-09-26; files uploaded 2026-09-22). So V6.GL.03 is not the primary. Revisit if documentation appears. This replaces the proposal's V6.GL.02.04 / V5.GL.05.02 pairing.

**DEC-002: Satellite version comparison uses V6.GL.03, and V6.GL.02.04 is the vintage check.**
V6.GL.03 (CNN method) against V5.GL.06 (GWR method) tests dependence on the retrieval algorithm. V6.GL.02.04 (to 2023) against V6.GL.03 tests calibration vintage. Because each vintage is calibrated to a different set of ground monitors, this partly tests whether network growth leaks into the satellite product.

**DEC-003: ACAG files are downloaded as Asia-region files from the public AWS bucket `s3://satpmdata`.**
Access is anonymous and scriptable, and the S3 ETags serve as checksums. The Asia annual 0.01° files are about 18 MB (V5.GL.06) and 92 MB (V6) per year, against about 437 MB for a global monthly 0.01° file. The download covers 2005–2024; the analysis window is fixed in `analysis_plan.md`.

**DEC-004: Weather comes from ERA5 only.** Station cells use the CDS point time-series dataset (`reanalysis-era5-single-levels-timeseries`). The satellite layer uses ERA5 monthly means over an India bounding box.
The point dataset includes boundary-layer height, SSRD and total precipitation (checked against the CDS form on 2026-09-26) and never requires all-India hourly data. Open-Meteo's free tier is capped at 10,000 calls a day, so it is kept only as a no-key fallback.

**DEC-005: Ground measurements come from the OpenAQ S3 archive (`openaq-data-archive`). The v3 API is used only for station metadata.**
The API allows about 2,000 requests an hour, which is impractical for about 1,200 station-pollutant hourly series. India coverage is unverified, so a coverage probe runs before any bulk download (Phase 2 step 0). The CPCB CCR portal is the fallback.

**DEC-006: Boundaries and population come from GHSL UCDB R2024A. WorldPop is dropped.** GHS-POP is used only for a population-weighted sensitivity check.
UCDB already carries population by epoch, so a second population model would add inconsistency without adding information.

**DEC-007: GAMs are fitted with R `mgcv` only. pyGAM is dropped.**
mgcv selects smoothing by REML and is the reference implementation. pyGAM is weakly maintained.

**DEC-008: PDF extraction uses pdfplumber only. camelot is dropped.**
camelot needs Ghostscript on Windows, and one tool is enough.

**DEC-009: Orchestration uses Snakemake only (`snakemake --cores 8 all`). Make is dropped.**
Make is not native on Windows. Snakemake handles the file DAG, R steps and partial rebuilds.

**DEC-010: The fire covariate uses MODIS C6.1 FRP (2000+). VIIRS S-NPP (2012+) is a secondary check.**
VIIRS starts in January 2012, but the satellite panel's pre-period starts earlier, so a VIIRS-only covariate would leave pre-period years missing.

**DEC-011: The ground-data window is 2015-01-01 to 2026-03-31.**
NCAP targets are set by financial year, and FY2025-26 ended on 31 March 2026.

**DEC-012: The pre-registration gate is enforced in code through `config/gate.yaml` (`analysis_plan_approved: false`).**
Every rule that estimates post-2019 treatment effects checks the flag and refuses to run while it is false. This makes Hard Rule 4 mechanical. The flag is flipped only in a separate commit, after `docs/analysis_plan.md` is approved and committed.

**DEC-013: The minimum detectable effect is computed before the gate, by placebo-in-time on pre-2019 satellite data only.**
Rule 4 permits pre-2019 checks. Knowing the MDE lets the analysis plan state realistic decision rules.

**DEC-014: The environment is Miniforge (conda-forge) with Python 3.12 and R 4.4, pinned with conda-lock (win-64 and linux-64).** R is used only for mgcv, synthdid and did.
conda-forge is the reliable route for the geospatial stack on Windows, and system Python 3.14 is too new for parts of the scientific stack. `synthdid` is not on CRAN, so it is installed from a pinned GitHub commit.

**DEC-015: A GitHub Actions job runs pytest on synthetic fixtures only.**
It provides continuous evidence that the cleaning rules behave as specified, ahead of the Phase 10 clean-clone check. No real data is used in CI.

**DEC-016: The "reported change" in the decomposition uses all CAAQMS stations as reported. The official PRANA/NAMP PM10 series is not extracted.**
All-CAAQMS matches what public trackers such as CREA use. The official NCAP metric also draws on NAMP manual stations; it is recorded as a possible extension rather than core work.

**DEC-017: `docs/analysis_plan.md` is drafted during Phase 3 and formatted to the OSF pre-registration template.**
This lets Reenu's review overlap with the audit. The gate is unchanged: nothing estimates post-2019 effects until the plan is approved and committed.

**DEC-018: Maps use Survey-of-India-consistent boundaries (e.g. DataMeet).**
The audience is Indian policy, and official boundary depiction matters for credibility.

**DEC-019: API keys are never handled by Claude.** In Phase 2 Claude creates `~/.cdsapirc` and `.env` with placeholder values, and Reenu pastes the real keys.
This keeps secrets out of transcripts and git (Hard Rule 5).

**DEC-020: The GitHub repo (`breenu/ncap-evaluation`) stays private until after Phase 3.**
It is confirmed private as of 2026-09-26.

## 2026-09-26: Facts checked against sources (Hard Rule 2)

**DEC-021: Proposal facts that differ from, or were confirmed against, live sources.**
- ACAG: V6.GL.02.04 and V5.GL.05.02 exist and cover 1998–2023, as the proposal says. Newer V5.GL.06 and V6.GL.03 cover 1998–2024.
- NCAP city count: PIB (PRID 1989207) says 131 cities. The proposal's split of 49 XV-FC + 82 MoEFCC conflicts with other sources that give 48 XV-FC cities/UAs. This is to be reconciled from the source PDFs in Phase 2.
- The OpenAQ S3 archive is anonymous, organised by location and day, and hourly. Its India coverage is unverified.
- The NASA FIRMS country archive did not respond on 2026-09-26; to be re-tested in Phase 2.

## 2026-09-26: Phase 1 (skeleton)

**DEC-022: R is 4.5, not 4.4. `did`, `DRDID` and `fastglm` come from a dated CRAN snapshot, not conda-forge. Supersedes the R-version part of DEC-014.**
conda-forge's `r-did` cannot be installed with R ≥ 4.4: every recent build requires `r-drdid >= 1.1.0`, which conda-forge does not have, and its `r-drdid`/`r-fastglm` builds are stale. So conda-forge supplies R 4.5 and all of did's other dependencies. `workflow/scripts/install_r_extra.R` installs fastglm 0.1.2, DRDID 1.3.0 and did 2.5.1 from Posit Package Manager's 2026-09-25 CRAN snapshot (Windows binaries; source on Linux). It installs synthdid 0.0.9 from GitHub commit `70c1ce3` (2024-01-15). `tests/test_environment.py` proves these work, compiled code included: it runs `att_gt` on did's `mpdta` example and `synthdid_estimate` on the Prop 99 example.

**DEC-023: Each source's `data/raw/<source>/MANIFEST.csv` is committed to git. The raw files are not.**
Manifests are small provenance records (url, upstream id, date, sha256). Committing them lets a clean clone re-download and prove the bytes are identical. `src/common/manifest.py` refuses to overwrite raw files, to accept unrecorded files, or to accept a re-download whose hash differs.

**DEC-024: Undecided thresholds are `null` in `config/params.yaml`, not placeholder numbers.**
Examples are the flatline length, ceiling values, changepoint penalty, neighbour radius and spillover buffer. A placeholder could silently become the final value. `null` forces the stage that needs a threshold to set it, with a DECISIONS entry. `config/regions.yaml` is likewise a draft, to be finalised in Phase 3.

**DEC-025: The Snakemake workflow has a `pregate` target alongside `all`.**
`pregate` builds everything allowed before the analysis plan is approved (acquisition, audit, EDA, deweathering, composition, pre-period checks). `all` includes the gated causal and hierarchical stages, which stop with `GateClosedError` while the gate is shut (tested).

**DEC-026: Snakemake comes from bioconda (noarch `snakemake-minimal`) and pyfixest from PyPI.**
Neither is on conda-forge. Both are pinned in `conda-lock.yml`.

**DEC-027 (fact noted): `synthdid` supports only simultaneous adoption.**
Its DESCRIPTION says "methods only for the case that all treated units adopt treatment at the same time". This confirms the plan's approach of estimating SDID per adoption cohort and aggregating, with Callaway & Sant'Anna as the staggered-adoption check.

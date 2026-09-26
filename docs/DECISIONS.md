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

## 2026-09-26: Phase 2 step 0 (feasibility probe)

Numbers below are from `docs/data-probe.md`, which `python -m src.acquire.probe report` generates from `data/interim/probe/*.json`.

**DEC-028: The feasibility probe is scripted and its report is generated.**
`src/acquire/probe.py` has one subcommand per source (`acag`, `firms`, `openaq`, `cpcb_mirror`, `cds`) and writes JSON to `data/interim/probe/`, never to `data/raw/`. `report` renders `docs/data-probe.md`. This keeps the go/no-go evidence reproducible and stops hand-typed numbers.

**DEC-029: OpenAQ monthly coverage is measured with `/v3/sensors/{id}/days/monthly`, not `/hours/monthly`.**
`/hours/monthly` returned HTTP 408 (timeout) for sensors with a decade of history; `/days/monthly` answers in about 1 s. A month counts if any day has data. For the probe only, locations within 0.5 km are merged into one site, because OpenAQ lists one physical CPCB station under several location ids (e.g. Anand Vihar is 235, 5509 and 10487). Phase 3 replaces this with proper de-duplication rules.

**DEC-030 (fact): OpenAQ has almost no Indian CPCB data for 2023 and 2024, and no PM for 2015 in the API.**
The API and the S3 archive agree. Only 8 non-CPCB sites (AirNow, StateAir, Clean Air Catalyst) report in 2023–24; CPCB returns in 2025 with about 520 sites. The S3 archive has 22 location-months in 2015. In 2021–22 fewer than half of the site-months with any data have ≥75% of days. So OpenAQ cannot be the sole ground source (DEC-005 is not viable as written).

**DEC-031 (fact and judgement): CPCB's own data-repository endpoints return HTTP 404 (checked 2026-09-26). I did not reverse-engineer the new CCR web app.**
The `airquality.cpcb.gov.in/dataRepository/{all_india_stationlist,file_Path,download_file}` endpoints used by public scrapers until at least January 2026 now return an HTML "page not found". The CCR app is now an obfuscated JavaScript bundle. Reverse-engineering it would be fragile and is a decision for Reenu, not something to do unasked.

**DEC-032 (fact): a third-party mirror of CPCB's repository covers 2015–2025.**
`github.com/Vonter/india-cpcb-aqi` (ODbL 1.0; releases dated 2026-01-07) has yearly Parquet files of 15-minute CPCB station data, 4.12 GB for 2015–2025, with no 2026 file. The files are padded to every 15-minute slot, so the meaningful size measure is PM2.5 station-year equivalents: 374 (2023), 429 (2024). Its data dictionary labels timestamps as UTC. CPCB publishes IST, so this must be verified before use.

**DEC-033 (fact): the pre-2018 PM monitoring network is small in every source.**
PM2.5 station-year equivalents in the mirror are 16 (2015), 25 (2016), 35 (2017) and 95 (2018). OpenAQ has 31 and 41 PM2.5 sites in 2016 and 2017. This is the CAAQMS network's history, not a source defect. It limits the ground layer's pre-period (Layer B, RQ1 baselines) and does not affect Layer A.

**DEC-034 (fact): ACAG sizes and extent confirmed; V5.GL.06 was also uploaded on 2026-09-22.**
V5.GL.06, V6.GL.03 and V6.GL.02.04 Asia grids all contain India at 0.01°. 2005–2024 as planned is 4.68 GB in total (V6.GL.03 annual 1.84 GB, V6.GL.02.04 annual 1.73 GB). V5.GL.06 masks water; V6 fills it. The V5.GL.06 files carry the same 2026-09-22 bucket date as V6.GL.03, so that date does not show V6.GL.03 is newer. DEC-001 still stands on documentation grounds alone.

**DEC-035 (fact): the CDS ERA5 point time series works for our variables and window.**
A Delhi request (2015-01-01 to 2026-03-31, 7 variables) returned 98,592 hourly rows with no gaps or NaNs in a 3.1 MB zip. The CDS job took 37 s. The point snaps to the nearest 0.25° grid point (28.61, 77.21 → 28.50, 77.25). `ssrd` has tiny negative values (min −1.90 J/m²), to be clipped at zero in Phase 5.

**DEC-036 (fact): the FIRMS keyless country archive ends in 2024, and its MODIS processing version changes mid-series.**
MODIS India is available for 2000–2024 and VIIRS S-NPP for 2012–2024; 2025 and 2026 return 404. The MODIS `version` field is `6.2` for 2000–2017, `6.03` for 2018–2022 and `61.03` for 2023–2024. The 2018 switch falls just before NCAP, so a MODIS FRP covariate could carry a processing artefact at the treatment boundary. VIIRS is `2` throughout. To be resolved before FIRMS is used (cut item #4).

## 2026-09-26: Phase 2 (acquisition)

**DEC-037: The ground source is the Vonter/india-cpcb-aqi mirror of CPCB's data repository for 2015–2025, with OpenAQ for Jan–Mar 2026 and as a cross-check wherever they overlap. Replaces DEC-005.** (Approved by Reenu after step 0.)
OpenAQ has almost no CPCB data for 2023–24 (DEC-030), and CPCB's own repository endpoints return 404 (DEC-031). The mirror's yearly Parquet release assets are downloaded as published and each is verified against GitHub's sha256 digest. The mirror's README, DATA.md, LICENSE and scripts are saved at commit `a58f478`. It is licensed ODbL 1.0: any derived *dataset* we publish carries ODbL; the code licence is separate. Reverse-engineering CPCB's new web app is ruled out (Reenu).

**DEC-038: GHSL UCDB R2024A version V1-2 (2026-05-19) is used, the newest release of R2024A.** GHS-POP 2020 at 30 arc-seconds (482 MB) supplies population weights for the sensitivity check. Both are CC BY 4.0. The JRC server publishes no checksum, so the upstream id is ETag + Last-Modified + size.

**DEC-039: The fire covariate uses VIIRS S-NPP only, from 2012. Supersedes DEC-010.**
The keyless MODIS archive changes processing version in 2018 and 2023 (DEC-036). Whether the MAP_KEY API gives one consistent MODIS collection could not be tested: `firms.modaps.eosdis.nasa.gov` is unreachable from the current network (connect timeout over IPv4 and IPv6, 2026-09-26), though it was reachable from the phone hotspot earlier the same day. Following Reenu's instruction not to spend long on it, VIIRS is used: one version (`2`) throughout, 2012 onward, and the fire sensitivity check starts in 2012. `src/acquire/firms.py` is written but not yet run: yearly VIIRS files 2012–2024, then the API for 2025 to Mar 2026. It is an open item until the host is reachable.

**DEC-040: The mirror's timestamps are 11 h ahead of UTC (5.5 h ahead of IST), not UTC as labelled. Ingest subtracts 11 h (`config/params.yaml: mirror.label_minus_utc_hours`).**
Three independent tests (`docs/mirror-checks.md`):
- (a) exact matches of 15-minute PM2.5 values with OpenAQ, whose timestamps carry explicit offsets, are best at +11.0 h (100% identical values in 2025; +5.5 h gives 0.2%, 0 h gives 0.1%);
- (b) the daily solar-radiation cycle at 27–376 stations per year peaks a median 10.7 h after solar noon in UTC, in every year 2015–2025;
- (c) station solar radiation best matches ERA5 (true UTC) at a lag of +10.5 to +11 h (correlation about 0.93; ERA5's hourly accumulation windows limit this test to about half an hour; exact figures in `docs/mirror-checks.md`).

The shift is constant over time. A residual 15-minute ambiguity (10.75 vs 11.0) is the start-versus-end convention for a 15-minute stamp, irrelevant for daily means. The mirror's parse script only *labels* naive times as UTC; where the second 5.5 h comes from (the scrape or CPCB's files) is unknown and does not change the correction. Raw files are untouched. Stations in the lowest decile of the solar test (implied offset about 7 h) are flagged for the Phase 3 audit (a faulty solar sensor or a station clock). OpenAQ's 2019–2021 values line up at +11 h but match the mirror exactly only about 2% of the time, so OpenAQ's older CPCB feed is not the same series value-for-value; the Phase 3 cross-check must allow for that.

**DEC-041: OpenAQ daily files are bundled into one uncompressed zip per location-year, with one manifest row per zip.**
There are about 430,000 daily files. The members are byte-identical, and an `_index.csv` inside each zip lists every member's S3 key, ETag and sha256. Each member is checked against its MD5 ETag. Zip member timestamps are fixed from the file date, so rebuilding from the same S3 objects gives identical zip bytes and the manifest sha256 still verifies. The zip's upstream id is a hash of its members' keys and ETags.

**DEC-042: Downloads resume after a dropped connection and verify upstream checksums.**
`http_fetch` resumes with HTTP Range requests (retrying with backoff) and restarts if the server ignores Range. `download()` keeps `<name>.part` plus a sidecar recording the url and upstream id, and discards a partial file if either changed, so two versions are never spliced together. Where the upstream publishes a checksum (S3 single-part ETag = MD5; GitHub asset digest = sha256), the file must match it. This replaces the Phase 1 rule that a failed fetch leaves no partial file; that test was rewritten.

**DEC-043: NCAP treatment data come from 14 documents listed in `config/ncap_sources.yaml`, each row carrying document, page and table.**
- **City lists and addition dates:** a dated sequence of lists. These are CPCB's `Non-Attainment_Cities.pdf` as captured by the Internet Archive on five dates (PDF CreationDates 2017-06-09, 2020-06-04, 2020-12-08, 2021-06-18, 2022-10-10), the NCAP report of January 2019 (archived; moef.gov.in unreachable), Lok Sabha AU164 (Dec 2023) and AU386 (Feb 2026). A city's date added is the first list that contains it. The last list without it gives the lower bound, so dates are interval-censored.
- **Allocations:** XV Finance Commission 2020-21 report Annex 5.3, and 2021-26 Vol II Annex 7.6 (landscape pages, rotated before extraction).
- **Releases and utilisation:** Lok Sabha answers AU5104, AU2467, AU164, AU307 (17th LS) and AU2080 (18th LS), found through sansad.in's question index. PIB 1989207 (HTML) was not used because AU164 covers the same period as a PDF.
- **Name matching:** exact after normalisation, otherwise only through `config/ncap_city_aliases.yaml`, where every alias records why. No fuzzy matching.
- **Nothing is corrected:** every failed check goes to `docs/ncap_extraction_mismatches.md` for manual verification.

**DEC-044 (facts reconciled from the documents): 131 vs 130 cities and 49 vs 48 XV-FC.**
- **132 → 131:** the June 2021 CPCB list prints Asansol and Raniganj as two entries (132); from October 2022 they are one (131).
- **131 → 130:** Patancheruvu, an XV-FC member city inside Hyderabad UA, is absent from the 2026 list. This takes XV-FC cities from 49 to 48.
- **Channel split:** 49 XV-FC + 82 NCAP = 131, matching the proposal; 48 + 82 = 130 matches AU2080 ("82 non-attainment cities", "48 Million Plus Cities").
- **Dates added:** 94 cities come from the 2017 pre-NCAP list; 8 more were in the January 2019 launch list (102); 19 by June 2020; 2 by December 2020; the 8 million-plus-only cities (Chennai, Faridabad, Jabalpur, Jamshedpur, Meerut, Rajkot, Ranchi, Vasai-Virar) by June 2021.
- **Supersedes DEC-021's open items.** Treatment timing for the analysis plan (listed vs funded) is decided in Phase 4.

**DEC-045: The station crosswalk matches mirror stations to OpenAQ by name only; coordinates come from the most recently active OpenAQ registration.**
- **Matches:** 514 exact matches and 6 on site + city, out of 565 stations. 26 unmatched stations take their city's mean coordinate (used only to pick the ERA5 cell), and 19 have none; those 19 get a GHSL urban-centre coordinate in Phase 3.
- **Conflicting coordinates:** some stations have OpenAQ ids up to 30 km apart (e.g. Dwarka Sector 8), so averaging would misplace them. These are listed for the Phase 3 metadata audit (risk R12).
- **ERA5 requests:** made at the 0.25° grid point itself (283 points), so the cell returned is unambiguous.

**DEC-046: The pipeline must run inside the activated conda environment (`conda activate ncap` or `conda run -n ncap`). Calling `envs/ncap/python.exe` directly is not supported.**
On this machine Oracle XE puts its own `mkl_rt.dll` on the system PATH. Without activation NumPy loads it, and any BLAS call (e.g. `corrcoef`) crashes with Windows error 0xc06d007f. Activation puts the environment's `Library\bin` first.

## 2026-09-26: Phase 2 review (Reenu's rulings on docs/ncap_extraction_mismatches.md)

Phase 2 approved. All 37 items were checked by hand.

**DEC-047: The 13 name mappings made by judgement are correct. 'Durg' → Bhilai means the Durg-Bhilai twin city: one unit covering both Durg and Bhilai.**
The master list has only "Bhilai"; the XV-FC documents name the unit "Durg Bhilainagar UA". Phase 3 defines the unit's geography (UCDB polygon, stations) to include both towns.

**DEC-048: Combined rows (Bhubaneswar & Cuttack; Angul & Talcher): both cities in each pair are enrolled. Funding per head for a combined row uses the pair's combined population.**
Amounts printed for a combined row cannot be split between the two cities, so the pair is the unit for dose calculations.

**DEC-049: Patancheruvu stays enrolled from its listing date (intention to treat), with a sensitivity analysis that excludes it.**
It was listed from 2017 and is absent only from the 2026 list (DEC-044). Dropping it would condition on a post-treatment event.

**DEC-050: Asansol and Raniganj are one enrolled unit covering both towns.** This matches the 2022 CPCB list and the XV-FC "Asansol UA". The separate entries in the 2020–21 lists are the same unit.

**DEC-051: The Jammu & Kashmir state-level row (AU5104) is excluded from city-level analysis.** It is not attributable to Jammu or Srinagar.

**DEC-052: Utilisation above release, and small drops in cumulative releases between documents, are kept as printed.**
They affect only the funding dose analysis, and that uses allocations, not releases or utilisation (proposal stage 8).

**DEC-053: Column totals that differ from the rows by 0.01–0.05 are accepted as rounding in the source documents.**

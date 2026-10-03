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

## 2026-09-26: Phase 3, part A (ingest, cross-check, station metadata, NCAP-UCDB matching)

**DEC-054: The mirror's stored timestamps are Indian clock times stamped as UTC: true UTC = stored instant − 5.5 h (`config/params.yaml: mirror.stored_minus_utc_hours`). Corrects DEC-040's "11 h" and its explanation.**
DuckDB shows `TIMESTAMP WITH TIME ZONE` values in its session time zone, which defaults to the machine's zone (Asia/Calcutta on this laptop). Phase 2's three tests therefore measured the offset on timestamps displayed 5.5 h after the stored instant, and found 11 h. Read with `TimeZone='UTC'` (and confirmed with pyarrow), the stored first row of 2025 is 2025-01-01 00:00 UTC, and the exact-match test gives 100% at 5.5 h against 0.2% at 0 h and at 11 h. The regenerated `docs/mirror-checks.md` puts all three tests at 5.0–5.5 h. There is no unexplained "second 5.5 h"; the mirror is exactly what its `parse.py` implies. Phase 2's station-year counts were computed consistently within the IST rendering and are identical after the re-run (e.g. PM10: 9 in 2017, 69 in 2018). Every DuckDB connection that reads the mirror now sets `TimeZone='UTC'`, the parameter was renamed so its old meaning cannot be reused silently, and `tests/test_ingest.py` checks that the result is the same under three session zones.

**DEC-055: Ingest layout.** The mirror is stored as `data/interim/mirror_15min/year=YYYY/` (sid, ts_utc, date_ist, pm25, pm10, no2): rows with no PM2.5, PM10 or NO2 are dropped (padding), and data are partitioned by Indian date. Duplicate station-slots across year files would be collapsed (identical copies → one; conflicting copies → null, counted); none were found. OpenAQ is stored as `data/interim/openaq_obs/year=YYYY/` with its unit labels kept. Days are Indian days throughout; hourly bins will be Indian clock hours.

**DEC-056: OpenAQ's "ppb" label on 2025+ NO2 is wrong; the values are µg/m³.** They are identical to the mirror's µg/m³ values (median exact share 100%, median ratio 1.000; `docs/mirror-openaq-crosscheck.md` §6). OpenAQ's CO in 2025 is labelled ppb but reads like CPCB's mg/m³. So Jan–Mar 2026 NO2 from OpenAQ is used as µg/m³.

**DEC-057: The mirror is relied on for 2015–2022. Why Phase 2 saw about 2% exact matches.** Phase 2's value test sampled the first 11 crosswalk stations in id order, and 7 of them are IMD-operated. Across all 1,608 matched station-years, on the corrected clock:
- 2019–2021: median exact-match share is 100%, and 94–97% of station-years are at least 95% identical.
- The exceptions are IMD-operated stations (7 stations, 24 station-years). Their 15-minute values differ from OpenAQ's (median exact share 1.3%) with no bias, but daily means agree to a median 0.4% (95th-percentile day about 1.5–2%). That is consistent with the two pipelines receiving separately averaged 15-minute values from the same analysers; the cause is not verified.
- 2016–2017: 50–85% exact, and daily means within about 0.5%.
- 2022: March–October partly differ, by a median of 0.1–0.6 µg/m³ (small revisions).
- March 2018: OpenAQ's PM2.5 is not a concentration series. It correlates with the mirror's trailing 24-hour mean (median r 0.95; 0.46 at the same time), and sits a median 8 index points from CPCB's AQI sub-index of that mean. This is an OpenAQ ingestion artefact; February and April 2018 match the mirror again.
Since daily means are the unit of analysis, none of these differences threatens the mirror's use.

**DEC-058: Station ↔ OpenAQ identity rule.** A location is the same station if at least 50% of at least 500 shared 15-minute PM2.5 slots are equal *and* it passes that bar for no other station. Across all 65,000+ station-location pairs, coincidental overlap is at most about 10%. The 10–50% band (16 pairs) mixes IMD stations' own ids with ids that carried a neighbouring station's data for part of their life: R K Puram and Punjabi Bagh appear swapped in OpenAQ (ids 6357/7044). That band is listed and not used. One OpenAQ id (6959) passes for two mirror stations (Worli MPCB and Siddharth Nagar-Worli IITM), so it is evidence for neither. This replaces Phase 2's name-only matching as the basis for coordinates; 17 previously unmatched stations were found this way.

**DEC-059: Station coordinate rules.** Candidates are every coordinate each matched OpenAQ id has had in the archive, not only the API snapshot (96 locations changed coordinates over time). A coordinate is plausible if it is in the station's state and within 15 km of the urban centre holding the city's other stations. Among plausible, data-confirmed coordinates:
- if they agree within 1 km, the coordinate is used;
- if they spread up to 3 km, the most recently used one is taken (DEC-045's rule), `coord_uncertainty_km` records the spread, and the station is reviewed;
- beyond 3 km, none is chosen, and the station gets its city's urban-centre point, marked `urban_centre`: usable for city assignment and an ERA5 cell, excluded from neighbour tests.
Result: 505 `station`, 19 `station_unconfirmed`, 38 `urban_centre`, 3 `none`; 54 on the review list (`docs/station_metadata_review.md`). This replaces DEC-045's `city_centroid` fallback. Phase 2 said coordinate conflicts reach "up to 30 km"; the largest is 313 km (Manali Village, Chennai: one id is placed at 11.26 N, 77.55 E, 313 km from the Chennai centre).

**DEC-060: Mirror metadata can be wrong; corrections live in `config/station_overrides.yaml` with their evidence.** The first entries: three MPCB (Maharashtra board) Aurangabad stations that the mirror labels Bihar, whose identical-value OpenAQ locations lie inside Aurangabad, Maharashtra. Every override is on the review list.

**DEC-061: NCAP city ↔ UCDB matching (`data/interim/ncap_ucdb_match.csv`, `docs/ncap_ucdb_review.md`).** Evidence comes from exact names (after `config/ncap_ucdb_names.yaml`, each mapping with its reason) and from the centres holding the city's station-level coordinates, restricted to the same state.
- The *primary* centre (the name match, else the centre holding most of the city's stations) defines the satellite unit. Centres holding a few outlying stations (e.g. Mejia for Asansol, Siltara for Raipur) are *secondary* and not part of the unit.
- Result: 121 of 131 cities matched; 10 have no centre.
- Four polygons are shared by several NCAP cities: New Delhi (Delhi, Faridabad, Ghaziabad, Noida); Kolkata (with Howrah, Barrackpore); Mumbai (with Navi Mumbai, Thane); Kalyan-Dombivli (Badlapur, Ulhasnagar).
- DEC-047 (Bhilai) → centre "Durg"; DEC-048 pairs are separate centres.
- DEC-050: "Asansol & Raniganj" uses the Asansol centre only. UCDB's "Raniganj" (10988) is Raniganj in Araria, Bihar, and the Asansol polygon stops west of Raniganj (WB); this is on the review list.
- DEC-049: Patancheruvu has no centre of its own; whether it lies in the Hyderabad polygon needs a town coordinate.
- DEC-051: the J&K state row is not a city.

**DEC-062: Urban centres get their state from DataMeet boundaries at the polygon's interior point, or the nearest state for coastal centres whose point falls offshore (one case, Dahanu).**

## 2026-09-26: Phase 3 checkpoint review (Reenu's rulings) and part B

**DEC-063: The 10 NCAP towns with no GHSL urban centre stay out of the primary satellite estimate; they enter one sensitivity analysis as buffered GeoNames points (Reenu).**
Controls are all GHSL centres of 100k+, and treated and control units must be defined the same way. Town points come from GeoNames (`docs/data-cards/geonames.md`) by exact name in the town's state (`config/geonames_towns.yaml`; aliases with reasons; ties go to the lowest geonameid and are flagged: Kala Amb). Kalinga Nagar has only an administrative-area record, flagged `admin_centroid`. **Buffer rule:** a circle with the median area of India's smallest GHSL centres (2020 population 50,000–99,999): 11 km², radius 1.87 km, computed from the data (`src/clean/towns.py`). Three town points lie inside another GHSL centre: Dera Bassi (Chandigarh), Patancheruvu (Hyderabad) and Parwanoo (Kalka, Haryana). Kalka is therefore marked `contains_ncap_town`; the analysis plan proposes dropping it from the control pool.

**DEC-064: Asansol & Raniganj is one unit covering both towns (Reenu). Raniganj joins as a GHSL polygon, not a buffer.**
Raniganj's GeoNames point (1258470; population 131,261) lies inside UCDB centre 11128. UCDB names that centre "Mejia", but it holds Raniganj's built-up area and 2 of the unit's stations. Reenu asked for a buffered point joined to Asansol. Joining the containing GHSL polygon meets the same intent, a unit covering both towns, and keeps the unit made only of GHSL polygons like every control. The buffer rule applies only if the point is outside every centre. **Flagged for Reenu's confirmation.**

**DEC-065: The coastal region uses the Natural Earth 1:10m coastline (public domain; `docs/data-cards/naturalearth.md`).** UCDB has no documented distance-to-coast field.

**DEC-066: Mirror accepted as the primary ground source for 2015–2022 (Reenu), on the cross-check (DEC-057).** OpenAQ's March 2018 PM2.5 fault and the NO2 unit mislabel are recorded in `docs/data-cards/openaq.md`.

**DEC-067: Station review rules (Reenu: resolve by a stated rule; bring only stations whose candidates would put them in a different city or urban centre).**
- **R1.** When a station's plausible, data-confirmed coordinates disagree by more than 1 km but all lie in the same urban centre (or all outside any centre), the most recently used one is taken (DEC-045's rule), with `coord_uncertainty_km` = the spread. This settles 19 stations.
- **R2.** A station with no OpenAQ coordinate at all whose site name matches exactly one GeoNames populated place inside the city's centre gets that point (`coord_quality` = `locality`). This settles 3.
- **Decisions for Reenu:** 5 stations are listed, with a recommendation, in `docs/station_metadata_review.md` §3. Until decided, each keeps its city's approximate point and stays out of neighbour tests.
- Stations with no candidate coordinate anywhere keep an approximate city point. They are used for city assignment and ERA5 cells, not neighbour tests.
- The Aurangabad state correction (DEC-060) is accepted (Reenu).

**DEC-068: Flag thresholds, set from the data (`config/params.yaml: flags`).**
- **Impossible values:** none at or below zero exist in the mirror; the rule stays for new vintages.
- **Ceilings** are detected, not typed in. A value ≥ 500 µg/m³ counts if it is more than 10 times as frequent as other values *of the same precision* within ±10 µg/m³, at ≥ 5 stations and ≥ 500 times.
  - A first version compared all neighbours and flagged hundreds of ordinary integers: many analysers report whole numbers, so any integer is far more frequent than a 2-decimal value. It was caught and fixed before any output was used, and a test covers it.
  - Detected: PM2.5 842, 887, 985, 995, 999.99, 1000; PM10 985, 999.99, 1000 (`data/interim/audit/ceilings.csv`).
- **Flatline:** identical hourly means for ≥ 4 consecutive hours. Runs of 2–3 hours occur at the rate expected by chance given the instruments' precision (the 2→3 decay predicts the observed 3-hour count); from 4 hours, counts exceed chance about 3-fold, with a long tail of stuck analysers.
- **PM2.5 > PM10:** flagged when PM2.5 − PM10 > max(5 µg/m³, 10% of PM10) at the same station-hour, allowing for the two analysers' separate noise; both pollutants are flagged for that hour.
- Flags are applied to 15-minute values (impossible, ceiling) and to hourly means (the other two), and flagged values are removed before daily means.

**DEC-069: Valid hour. Primary: any 15-minute value present; sensitivity: at least 3 of 4 (Reenu).** The analysis plan quotes the primary rule's counts and reports both. After flagged hours are removed, PM10 valid station-years are 9 (2017) and 66 (2018). The 69 quoted before Phase 3 was counted before flagging.

**DEC-070: The oversized-polygon rule: the primary satellite city value is the population-weighted mean over the unit's polygon, for every unit, treated and control alike. The area-weighted, unclipped mean is the sensitivity check.** Replaces the area-weighted primary of DEC-006 and `config/params.yaml`.
- Weights: GHS-POP 2020, 30 arc-seconds, summed onto each ACAG grid.
- Why: it is what residents breathe, it needs no arbitrary clipping radius or core definition, and it treats every unit identically.
- Oversized polygons are not only an NCAP problem. Rural-dense control centres in Bihar, Kerala and West Bengal are also 600–3,000 km².
- A clip-to-core rule was rejected. A core circle needs a centre point, and for shared or oversized centres (Muzaffarpur inside the "Hajipur" polygon) the polygon's own centre is not the NCAP city's.
- The audit report (§11) shows how much the choice matters.

**DEC-071: Spatial consistency checks** (`src/clean/spatial.py`).
- **Neighbour radius: 25 km.** Station spacing is bimodal (city clusters vs isolated stations); 25 km gives 59% of located stations two neighbours in the same airshed, and larger radii add few until 50 km, which starts comparing different cities.
- **Checks:** a station-year is flagged if its daily correlation with the neighbours' median, or (PM2.5) its log ratio to its ACAG cell, lies more than 3 robust SDs from that year's network. A check that cannot run is not a failure.

**DEC-072: Changepoints** (`src/clean/changepoints.py`).
- **Method:** PELT (L2 cost) on the weekly departure from the neighbours' median, scaled by a robust noise estimate; penalty 3 × log(n); minimum segment 8 weeks; only steps ≥ 25% count.
- **Stations without neighbours** use their own deseasonalised series, and are labelled so.
- **Limitation:** a step cannot be told apart from a real local change beside the monitor, and the report says so.

**DEC-073: Completeness variants and the reliability score** (`src/clean/reliability.py`).
- **Completeness:** a threshold applies to both levels (hours per day and days per year). The variants are 75% primary, 60% and 90%, plus the 3-of-4 hour rule. The 2026 year counts January–March only.
- **Score:** 100 × completeness × (1 − flagged share) × 0.8 per failed check (neighbour, satellite, changepoint in that year).
- The score describes; it does not exclude data.

**DEC-074: Missingness design** (`src/clean/missingness.py`).
- **Models:** linear probability models with station fixed effects, year effects and station-clustered standard errors.
  - Season model: all stations.
  - Pollution-level model: the neighbours' level on the day, in within-station terciles. It is observed even when the station is missing, which makes a missing-not-at-random test possible.
- **Bias:** the effect on annual means, from filling missing days as exp(neighbour reference + the station-year's median residual).

**DEC-075: Regions final** (`config/regions.yaml`, `src/clean/regions.py`).
- Assigned per urban centre, in order:
  1. north-east (by state);
  2. IGP (plains states, including Uttarakhand, with centre mean elevation < 350 m);
  3. coastal (≤ 50 km from the coastline);
  4. peninsular/other.
- **Jharkhand is out of the IGP** (Chota Nagpur plateau).
- **The 350 m cutoff** keeps Chandigarh (323 m) and Haridwar (293 m) in, and leaves Rishikesh (365 m), Dehradun and the hills out.
- The four groups follow the proposal; a Himalayan split is a sensitivity option.
- Limitation: buffered towns take the nearest centre's elevation, which matters only for IGP membership of the Punjab buffers.

**DEC-076: UCDB name matching prefers a centre's main name over its list of settlements.** UCDB lists a village "Durgapur" among the 37 settlements of a South 24 Parganas centre (11408), about 130 km from Durgapur city; the first version matched both. One list-only match remains: Kashipur → the "Thakurdwara" centre, which lists Kashipur and lies in Uttarakhand.

**DEC-077: DEC-054 confirmed independently (Reenu's request).** On the corrected clock (stored − 5.5 h, read with DuckDB `TimeZone='UTC'`), the station solar-radiation peak lands within about 15 minutes of local solar noon in every year 2015–2025 (median −0.19 to −0.30 h; `docs/mirror-checks.md` §1 b2). The small early bias is expected: afternoon haze, and a 15-minute value stamped at its interval start.

**DEC-078: The changepoint penalty is calibrated against a no-shift null, not chosen by eye. Refines DEC-072.**
- **What went wrong first.** The first version scaled each weekly series by its week-to-week differences and used segments of 8 weeks or more. It found about 6,500 level shifts, roughly 11 per station. Week-to-week differences understate the spread of autocorrelated weekly residuals, so PELT split the series at every slow wobble. This was caught before any output was used.
- **Now:**
  - Scale by the series' own robust spread (1.4826 × MAD).
  - Segments of at least 26 weeks: a shift that matters for annual means lasts months. Break dates every 2 weeks.
  - For each series type, the penalty is the smallest on a grid (3–20 × log n) at which ≤ 5% of block-shuffled series show a changepoint. The series are shuffled in 4-week blocks, which keeps short-range autocorrelation but destroys any lasting shift.
- **Result:** penalty 8 for neighbour-referenced series (2.7% false alarms; 40% of real series show a shift), and 5 for own-season series (2.8%; 54%). That gives 653 level shifts at 317 stations. The calibration table is in `docs/audit_report.md` §5.

**DEC-079: CPCB's repository (the mirror) holds validated data; OpenAQ holds the raw real-time feed. January–March 2026, which comes only from OpenAQ, is provisional.**
- **Evidence:** in every overlapping year, OpenAQ carries 2–3% PM values at or below zero (including −9999 sentinels), and the mirror is empty at more than 95% of those slots (100.0% in 2025). OpenAQ's PM2.5 > PM10 rate is 1.4–1.8%, against 0.04–0.12% in the mirror since 2019 (`docs/mirror-openaq-crosscheck.md` §6).
- **What the pipeline does:** it removes the ≤ 0 values and flags PM2.5 > PM10 hours in 2026 as in every year. Whatever else CPCB's validation removes cannot be reproduced.
- **Proposed in the analysis plan:** ground analyses use calendar years to 2025 as primary; January–March 2026 enters only as a sensitivity check (FY2025-26).
- **Two consequences:**
  - The Phase 2 statement that the two sources are "identical in 2025" holds only on slots where both hold a value.
  - The pre-2019 mirror has a PM2.5 > PM10 rate of 0.9–2%, so CPCB's validation was less strict before 2019. That is part of why the baseline years score lower on reliability.

## 2026-09-26: Phase 3 review (approved by Reenu)

**DEC-080: The 5 stations whose candidate coordinates lay in different urban centres take the recommended coordinates (Reenu), and a sensitivity analysis drops all 5.**
- **Chosen coordinates.** Patna IGSC Planetarium (site_157), Varanasi Ardhali Bazar (site_273) and Panipat Sector-18 (site_5048) take their most recently used, data-confirmed coordinate.
- **Kept approximate.** Chamarajanagar (site_5124) keeps no station-level coordinate: its only candidate is outside Karnataka, and the city has no GHSL centre. Nayagarh (site_5674) keeps the city's approximate point: its only candidate is 187 km away.
- **Where recorded:** `config/station_overrides.yaml` (`coordinates`, each with why). `data/processed/stations.csv` marks them `reenu_decided` = True and `resolved_by` = `reenu_decision`.
- **Sensitivity:** added to the ground-layer robustness list in `docs/analysis_plan.md`: every ground-based estimate is re-run without these 5 stations.

**DEC-081: Reenu confirmed DEC-064 (Raniganj joins the Asansol unit as the GHSL centre UCDB names "Mejia") and DEC-070 (population-weighted satellite mean for every unit as primary; unweighted as sensitivity).**

**DEC-082: The Phase 3 outputs were rebuilt end to end with `snakemake --cores 1 pregate`, the first full run of the workflow rather than module by module.** It is single-core because several steps give DuckDB 8 GB and the machine has 16 GB. The log is `data/interim/logs/snakemake_pregate_phase3.log`. With the 3 newly located stations, the rebuilt outputs move slightly: level shifts 653 at 316 stations (was 317; DEC-078's calibrated penalties unchanged), and satellite-flagged PM2.5 station-years 49 (was 52). Valid station-years, missingness and EDA results are unchanged.

**DEC-083: The first end-to-end `pregate` run exposed three workflow bugs that module-by-module runs had hidden; all are fixed.**
(1) `src/clean/towns.py` prints GeoNames names with diacritics, which the Windows console code page (cp1252) cannot encode; manual runs had set `PYTHONIOENCODING=utf-8` by hand. The Snakefile now sets it for every rule. (2) The NCAP-UCDB matching step (`python -m src.clean.geo`) rebuilt `data/interim/ghsl/ucdb_india.gpkg`, the output of a different rule and an input of `station_meta`, so every run silently invalidated an upstream step (a hidden cycle). It now only reads that file. (3) The `ucdb_india` rule's command came out as `python -m -c ...` and had never run through Snakemake; it is now `python -m src.clean.geo ucdb`. This is why the pipeline is run end to end before each phase is closed.

## 2026-09-26: Phase 4 (analysis-plan gate)

Numbers are in the generated `docs/pregate_checks.md`; `docs/analysis_plan.md` quotes them through markers that `python -m src.causal.pregate_report sync-plan` fills and `snakemake pregate` checks.

**DEC-084: The satellite analysis window is 2010–2024 (`windows.satellite_analysis_years`).** Nine pre-years, as the Phase 3 draft plan proposed; ACAG V5.GL.06 ends in 2024. Starting earlier would add pre-years from a thinner, older satellite record at no gain to the question.

**DEC-085: The spillover buffer is 25 km, edge to edge, and it is a sensitivity analysis only (`control_pool.spillover_buffer_km`).** 25 km is the audit's neighbour radius, i.e. the same airshed (DEC-071). Distances are measured to every NCAP place, including the 10 buffered towns, because those are treated places even though they are outside the primary estimate. Pool sizes at 10, 25 and 50 km are in `docs/pregate_checks.md` §1 so the choice can be seen against alternatives.

**DEC-086: Treatment timing rules (`src/causal/treatment.py`; proposed for Reenu's decision at the gate).**
- **Listed (primary):** listed on or before 30 June → treated from that calendar year, otherwise the next; nothing before 2019. A unit takes its earliest member's year.
- **Funded (alternative):** the first financial year with a central release > 0, counted from the *next* calendar year (FY2019-20 → 2020). Why the next year: a release anywhere in FY *t* can only fund a full calendar year of action from *t*+1; counting from *t* would make the alternative almost identical to the listing date and so a weak check. Sources: Lok Sabha AU2467 per-FY releases (NCAP channel, FY2019-20 to FY2021-22); XV-FC cities from FY2020-21 (the first XV-FC air-quality grant year) unless AU2467 shows an earlier NCAP-channel release (e.g. Agra). Every city has a dated first release; the cumulative-only fallback (AU2080, interval FY2022-24) is coded and tested but not needed.

**DEC-087: How the minimum detectable effect is computed before the gate (implements DEC-013).**
- **Pre-period only, enforced:** `src/causal/pregate.py` reads every outcome table with a year ≤ 2018 filter inside the Parquet reader and asserts it; `mde_placebo.R` checks again; winter seasons must end by December 2018 (so winter seasons run 2010–2017, and non-winter is restricted to the same season-years).
- **Null spread:** 500 sets of controls, each the size of the real treated set, given fake adoption in 2014 and in 2015; SDID (R `synthdid`, default settings) against the remaining controls. SE = SD of the placebo ATTs; MDE = 2.8 × SE. The same draws serve four outcomes (log annual, level annual, log winter, log non-winter), so the winter-minus-non-winter SE is joint.
- **Two null designs, largest MDE carried:** random sets, and region-matched sets (as many controls per region as the real treated set). The first run used random sets only and gave a very small MDE; random sets scattered over India average away regional shocks that the real, regionally clustered treated set carries, so the region-matched design was added before the plan was written. The plan carries the largest MDE over designs and fake years, and says it is a lower bound. The real treated set's placebo takes its SE from the region-matched null. **Outcome:** matching regions did not raise the SE (region-matched SEs are slightly smaller), so the carried MDE comes from the random design; the region-matched null is not centred on zero (a small SDID bias for regionally structured treated sets, below one SE), which `docs/pregate_checks.md` §4 reports.
- **Simultaneous, not per-cohort:** the placebo assigns all units at once. The real estimator averages per-cohort SDIDs, but the 2019 cohort is most of the treated units, so the simultaneous design is a close and simpler guide. Stated as a caveat.
- **Real treated set at the fake years:** also estimated (data ≤ 2018 only), with SE and permutation p from the same null draws. This is a pre-period check, allowed by hard rule 4, and it was computed *before* the plan's decision rules were finalised; the plan therefore keeps the draft's H1 rules unchanged and lists every other change made afterwards (§6).
- **Engineering:** all random sets are drawn in the master process from `seed`, so results do not depend on the number of workers; each R worker runs single-threaded BLAS (multi-threaded MKL made each fit ~9× slower).

**DEC-088: Ground-layer choices fixed in the plan that earlier phases left open.**
- **Deweathering family:** the family (LightGBM or mgcv GAM) with the better median out-of-sample R² under blocked forward-chaining CV is primary; the other is a sensitivity analysis. The selection uses only model fit, never an NCAP comparison, so it can be made after the gate without risk.
- **Balanced-panel baseline:** 2018 primary (the only substantial pre-NCAP year), 2019 sensitivity (more stations).

**DEC-089: Hypotheses and multiple comparisons.**
- **H4 and H5 added:** the proposal's own pre-specified hypotheses 1 (weather and composition explain part of reported change) and 3 (smaller effects in the IGP) were missing from the Phase 3 draft; both are now secondary hypotheses with decision rules.
- **Confirmatory family {H1, H2} in fixed sequence at α = 0.05:** H2 is tested only if H1 is supported. This keeps the familywise error at 5% without halving α, and H2 (a larger winter effect) is hard to interpret without an overall effect.
- **SE for the cohort-aggregated SDID:** a joint placebo (disjoint random control sets of the cohorts' sizes, re-aggregated each replication), because cohorts share controls and per-cohort SEs are not independent.
- **Event study:** Sun & Abraham interaction-weighted estimator against never-treated units, instead of the proposal's plain two-way fixed-effects formula, which is biased under staggered adoption with heterogeneous effects.
- **Layer disagreement:** four categories fixed in advance (consistent, different magnitude, conflict, uninformative) and a fixed four-step investigation.
- **Asansol & Raniganj:** no sensitivity was logged for DEC-064; the plan proposes "Asansol centre alone", flagged for Reenu.

**DEC-090 (fact): R `mgcv` from conda-forge (1.9-4) now fails to load on this machine; not fixed, pending Reenu.**
`library(mgcv)` stops with "Mingw-w64 runtime failure: 32 bit pseudo relocation ... out of range" in almost every try (0 of 6, 0 of 2, 0 of 6 successes in separate batches; the environment test failed 6 times; one full `pytest` run at 22:17 passed it, while R workers were running, and the next 3 tries failed again), from Git Bash, from PowerShell and with a minimal PATH (only Windows system folders), so it is not a PATH clash (Oracle's MKL, `C:\MinGW`, Git's mingw64 were each ruled out). `did`, `synthdid`, `arrow`, `yaml`, `data.table`, `Matrix` and `nlme` load every time. The error class arises when a DLL built with 32-bit pseudo-relocations imports data from a DLL loaded more than 2 GB away, which depends on per-boot address randomisation; that fits `tests/test_environment.py::test_r_estimators_run` having passed earlier the same day. CRAN's Windows binary of the same version (mgcv 1.9-4 from the 2026-09-25 Posit snapshot, DEC-022), installed into a throwaway library, loads and fits a REML GAM 3 of 3 times. Proposed fix (not applied: it changes the pinned environment): install mgcv from that snapshot in `workflow/scripts/install_r_extra.R`, as DEC-022 does for `did`. Phase 4 does not use mgcv; Phase 5 does.

## 2026-09-27: Phase 4 review (Reenu's rulings and corrections)

**DEC-091: Log-scale results are reported in natural-log units with the implied percentage, never as "log points"; permutation p-values are equal-tailed; the % and µg/m³ MDEs are reported separately. Corrects DEC-087's reporting, not its numbers.**
- **What was wrong.** `docs/pregate_checks.md`, the plan and the phase note printed 100 × (log difference) and labelled it "log points". The real-NCAP placebo ATTs (stored as +0.0047 and −0.0041) therefore appeared as "+0.47 and −0.41 log points", which Reenu read, reasonably, as log units (about +60% and −34%), inconsistent with a 1.2% MDE. The stored estimates and the MDE were always on the same scale and consistent: +0.47%, −0.41%, and MDE = 2.8 × 0.0042 = 0.0117 → a 1.2% fall.
- **The p-values were wrong.** They counted |placebo| ≥ |ATT|, which assumes a null centred on zero; the region-matched null is not (DEC-087). They are now equal-tailed (twice the smaller empirical tail): 2014 0.22 → 0.32, 2015 0.41 → 0.75 (log); level scale 0.87 → 0.31 and 0.74 → 0.53. Conclusions unchanged.
- **"1.2% (0.9 µg/m³)" paired two numbers that are not conversions of each other.** 1.2% of the NCAP 2010–2018 mean (51.7 µg/m³) is 0.6 µg/m³. 0.9 µg/m³ is the MDE of a separate SDID fit on the µg/m³ scale, whose SE is 1.1–1.4× the log SE × the pool mean because absolute noise is concentrated in the dirtiest units (the dirtiest third holds about 71% of the µg/m³ noise variance; generated in `pregate_checks.md` §4). The primary outcome is on the log scale, so the % MDE is the plan's.
- Tests now pin the labels as text (`tests/test_pregate.py`).

**DEC-092: Treatment timing: first listing is primary; first funding is a sensitivity analysis only (Reenu). Confirms DEC-086's proposal.** Funding timing is partly performance-linked (XV-FC grants reward improvement), so it is partly an outcome and must not define treatment. Also accepted: H4 and H5 as secondary hypotheses and the Asansol-alone sensitivity. H4/H5 are hypotheses 1 and 3 of the proposal dated 25 September 2026; verified that it predates all data access: the PDF's creation time is 2026-09-25 18:26 UTC, it is in the repository's first commit (2026-09-26 00:22 IST), the feasibility probe was committed at 03:25 IST, and the earliest `downloaded_utc` in any manifest is 2026-09-26 04:44 UTC. Reenu will register the plan on OSF before the gate opens.

**DEC-093: R `mgcv` 1.9-4 now comes from the 2026-09-25 CRAN snapshot (Posit binary), not conda-forge. Resolves DEC-090.**
- **Not the Oracle conflict (Reenu asked first).** In a live R process with mgcv loaded, every BLAS/LAPACK/MKL DLL is the environment's own (`Library\bin\mkl_rt.3.dll`, `libblas.dll`, `liblapack.dll`, R's `Rblas`/`Rlapack`); no Oracle DLL is loaded, and Oracle ships `mkl_rt.dll`, a different file name from the `mkl_rt.3.dll` R's chain loads. The failure also persisted with Oracle's folder removed from PATH and with a system-only PATH (DEC-090). So it is not DEC-046's problem and cannot be fixed in the activation.
- **What it is.** mgcv.dll imports data (`R_NilValue`, `R_NamesSymbol`) from R.dll and functions from Rblas, Rlapack and libgomp; MinGW patches such data references with 32-bit pseudo-relocations, which fail when Windows happens to load the two DLLs more than 2 GB apart. Base addresses are randomised per boot: on 2026-09-26 conda-forge's build failed in about 20 of 21 loads; after the machine restarted (2026-09-27) it loaded 5 of 5. CRAN's build of the same version loaded 3 of 3 on 2026-09-26 under the failing layout.
- **Change.** `environment.yml` drops `r-mgcv` and lists `r-nlme` (mgcv's dependency) explicitly; `workflow/scripts/install_r_extra.R` installs mgcv 1.9.4 from the snapshot beside did/DRDID/fastglm. `conda-lock.yml` was re-locked in update mode (`conda-lock lock --update r-nlme`), so the only change in both platforms is r-mgcv removed; a full re-solve had also bumped arviz-base, platformdirs and wcwidth and was discarded. conda-lock's update mode needs `PYTHONNOUSERSITE=1` on this machine (conda's Python 3.14 otherwise picks up user-site packages and its JSON output breaks).
- **Environment rebuilt** from the new lock (`conda-lock install -n ncap`), R extras installed; the previous environment is kept as `ncap_prev` until the rebuild is verified. `tests/test_environment.py::test_r_estimators_run` passed 10 of 10 consecutive runs. Caveat: on this boot the old build also loads, so the 10 runs show the new install works; the evidence that it survives the bad layout is the 3 of 3 on 2026-09-26.

**DEC-094: Full pregate rebuild from raw data in the rebuilt environment (2026-09-27): every plan number unchanged; outputs are content-reproducible but not byte-reproducible.**
- **Run:** `snakemake --cores 1 --forceall pregate`, restricted with `--allowed-rules` to every derivation rule and no downloader (so nothing is re-fetched): 30 jobs from ingest through NCAP extraction, audit, EDA and the pre-gate checks, 00:35–02:00 (log `data/interim/logs/snakemake_pregate_phase4_full.log`).
- **Result:** all values quoted in `docs/analysis_plan.md` and the summary are identical before and after (compared as a set, and `check-plan` passed inside the run); every generated report (`audit_report.md`, `pregate_checks.md`, `mirror-checks.md`, `mirror-openaq-crosscheck.md`, `ncap_ucdb_review.md`, `ncap_extraction_mismatches.md`) is byte-identical. The only tracked differences were two rows of site_5048 swapping order in `station_metadata_review.md` (a tie in the sort key) and the timestamp and random clip-path ids inside the SVG figures (PNGs identical); those files were restored to their committed, content-identical versions.
- **Byte-level differences:** 37 of 2,575 intermediate files have new checksums. Running one of those steps twice back-to-back in the same environment (`ucdb_india`) also gives new bytes with identical content (GeoPackage writes a timestamp; DuckDB and pandas do not fix the order of tied rows), so checksums are not a valid reproducibility test for this pipeline; content and downstream numbers are. Making outputs byte-deterministic (stable sort keys, `svg.hashsalt` and no SVG date, fixed GeoPackage timestamps, ordered DuckDB writes) is an open item for the Phase 10 clean-clone check.

## 2026-09-27: Final changes before OSF registration (Reenu)

**DEC-095: The H1 equivalence margin is a smallest effect of interest of ±5% in annual PM2.5, not ±MDE (`robustness.equivalence_margin_pct`).** The MDE (1.2%) is a best-case noise level, not the smallest effect that matters; with it as the margin a null would almost always be "inconclusive". ±5% is one quarter of NCAP's smallest target (a 20% reduction), which was set for PM10, so the margin is a stated judgement rather than an official threshold. Test: two one-sided tests at 5%, i.e. the 90% CI within ln 0.95 to ln 1.05. The MDE is still reported.

**DEC-096: Pre-specified calibration-leakage check.** ACAG calibrates to ground monitors, and NCAP added monitors mainly in treated cities. H1's primary SDID is estimated separately for treated units that gained a CAAQMS station inside their polygon with first PM data in 2019–2024 (the satellite post-period; a station first reporting in 2025 cannot affect satellite years to 2024) and for those that did not; the difference gets a joint-placebo SE. Groups under 10 units are not estimated (`robustness.leakage_min_units`). Group sizes are generated from network metadata only (first-report years, no pollution values; `src/causal/pregate.py: monitor_gain`, `data/interim/pregate/monitor_gain.csv`): 74 gained, 39 did not (12 with a station before 2019, 27 never with one inside the polygon). Stations are counted only inside the polygon (`km_to_unit` = 0). A pre-stated warning rule flags an effect concentrated in units that gained monitors; it is a warning, not proof, because those cities also differ in size and pollution. Raw MAIAC AOD is listed under this threat, conditional on time. The CPCB network is a proxy for the monitors ACAG actually used.

**DEC-097: HonestDiD bounds (Rambachan & Roth 2023) on the event study, as a reported sensitivity analysis.** R `HonestDiD` 0.2.8 is in the 2026-09-25 Posit CRAN snapshot (checked 2026-09-27); it will be installed through `install_r_extra.R` in Phase 7 (its dependencies include CVXR and Rglpk, not needed before then). Relative-magnitudes bounds (M̄ = 0, 0.5, 1, 1.5, 2) and smoothness bounds (M from 0 to twice the largest pre-period coefficient's SE, 5 steps) on the average post-period effect, with the breakdown M̄. Rule (b) is unchanged; if (b) fails, the bounds are reported alongside "not identified".

**DEC-098: `docs/analysis_plan.md` and `docs/analysis_plan_summary.md` are written in the author's first person (Reenu).** Wording only: generated values, DEC references and every rule, hypothesis and table entry are unchanged, checked mechanically before and after (markers and DEC references identical; the only changed table cells are attribution wording). Project logs (this file, PROGRESS, phase notes) keep their existing voice.

## 2026-09-27: Registration and the gate (Phase 4 closes)

**DEC-099: The analysis plan is registered on OSF: https://osf.io/jksne/ (Reenu).** Verified through the OSF API on 2026-09-27: a public registration (not embargoed, not withdrawn) using the "OSF Preregistration" template, registered 2026-09-27 11:58 UTC, title matching the plan. Its archive holds one file, `analysis_plan_osf.pdf` (374,444 bytes, sha256 `569e2a5845aefabaa57981aa87ee0f99cd90add99c0bf5eb1f64a94b997a06a8`), byte-identical to `docs/osf/analysis_plan_osf.pdf` exported from the plan at commit `6e24ecaf38c54c1f31774c966c243e4183c1b2ca`. **That commit is the registered plan.** The next commit adds only the OSF link to the plan's status line and the summary (checked with `git diff`); the gate cites `6e24eca`. The registered PDF is not re-exported. `tests/test_gate.py::test_repo_gate_is_closed` (valid only until Phase 4) is replaced by a permanent test: the committed gate is either shut, or open and naming a full commit hash that contains the plan (the commit check is skipped in shallow CI clones).

## 2026-09-27: Phase 5 (deweathering), rules fixed before the pilot

The gate is open (`config/gate.yaml` cites plan `6e24eca`, registered at https://osf.io/jksne/). Phase 5 fits weather models per station; it never uses NCAP status and estimates no treatment effect. The registered plan binds: LightGBM and mgcv GAM on log daily PM per station and pollutant; the family with the better median out-of-sample R² under blocked forward-chaining CV by year is primary (DEC-088); ground rules DEC-069/073/079/080. Everything below is a choice the plan left open, recorded before any pilot result was seen.

**DEC-100: ERA5 for the stations located in Phase 3, and daily weather features.**
- **Download.** 22 stations (13 station-level coordinates, 9 approximate points) lay in 20 grid cells with no ERA5 file, because Phase 2 chose cells from the crosswalk before Phase 3 located the stations. `python -m src.acquire.era5 --located` adds the cells of `data/processed/stations.csv` to the crosswalk's and fetches only the missing ones (idempotent; 20 files of about 3.2 MB; manifest verified; own Snakemake flag `acquire_era5_located`, so the Phase 2 rule is not re-triggered). 303 cells now cover every station with a coordinate. The 2 stations with no coordinate at all cannot be deweathered and are listed as such.
- **Indian days.** An Indian day holds the 24 UTC hours 19:00 (day − 1) to 18:00. Accumulations (`tp`, `ssrd`) are stamped at the end of their hour, so one half-hour per day falls on the neighbouring day (negligible). Days without all 24 hours are dropped, which removes only 1 January 2015.
- **Features** (`src/normalise/era5_daily.py`):
  - weather: mean temperature; mean relative humidity from hourly T and dew point (Magnus, Alduchov & Eskridge coefficients); mean **scalar** wind speed; direction of the vector-mean wind; mean and afternoon-maximum (11:30–17:30 IST) boundary-layer height; precipitation sum (mm); SSRD sum (MJ/m², negatives clipped to 0, DEC-035);
  - calendar: day of year, weekday, and a trend (years since 2015-01-01).
- **Scalar, not vector, speed.** PLAN.md said "vector-mean wind speed". Scalar speed is used because dilution depends on how fast air moves, whatever its direction, and a vector mean is near zero on days when the wind turns. Direction stays vector-mean.

**DEC-101: Model specifications (fixed, not tuned per station).**
- **Fit days:** valid days under the primary rule (≥ 18 of 24 valid hours) up to 31 Dec 2025 (DEC-079); the outcome is the log daily mean. A station-pollutant with fewer than 365 valid days is not deweathered, because a model needs at least one seasonal cycle.
- **LightGBM** (`src/normalise/lgbm.py`): 500 trees, learning rate 0.05, 31 leaves, ≥ 20 rows per leaf, 80% row and 90% column subsampling, one thread, fixed seed. The settings are fixed rather than tuned: tuning per station on ~2,000 days would add a second layer of CV and more overfitting risk for little gain, and the registered comparison is between families, not tuning effort.
- **GAM** (`src/normalise/gam.R`, mgcv `bam`, fREML, discretised covariates): `y ~ s(trend) + s(doy, cyclic) + weekday + s(temp) + s(rh) + s(ws) + s(wd, cyclic) + ti(ws, wd) + s(blh_mean) + s(blh_pm) + s(log1p precip) + s(ssrd)`. The trend's basis size is 4 per year of record (5 to 45), so it can follow step changes such as 2020; REML chooses the actual wiggliness.
- **Retransformation:** deweathered values are mean(exp(prediction)) × Duan's smearing factor mean(exp(residual)), which puts them on the scale of observed daily means. The factor is a constant per series, so no relative (%) change depends on it.

**DEC-102: Weather resampling scheme: a seasonal window, drawn from the cell's full 2015–2025 ERA5 record (proposed; the pilot also runs Grange & Carslaw's default for comparison).**
- **Proposal and default:** Grange & Carslaw (2019) and `rmweather` resample every non-trend input from the whole record, day of year and weekday included. The normalised series then has no seasonal cycle.
- **Proposed primary (`seasonal`):** for each day, draw the whole weather vector (all eight variables together, so their joint behaviour is kept) from ERA5 days within ±15 days of the same day of year, in any year 2015–2025. The day's own day of year and weekday are kept. This:
  - removes year-to-year weather variation, which is the question RQ2 asks;
  - keeps the seasonal cycle that city-month series and the winter/non-winter split need;
  - avoids predicting with impossible combinations, such as July weather on a January day.
- **The pool is ERA5 at the station's cell over 2015–2025, not only the days the station observed.** Every station is then normalised to the same 11-year climate, whether it opened in 2015 or 2023. With an observed-days pool, a new station would be normalised to 2023–25 weather only, and stations would not be comparable. This is still "the station's full historical distribution" (proposal stage 5), taken from the reanalysis rather than from the monitor's record.
- **Shared draws:** the draws are generated once per station and pollutant from the config seed (`src/normalise/features.py`), and both families read them.
- **Deweathering does not remove the 2020 lockdown.** Emission changes are not weather, and the trend term carries them. 2020 stays flagged in every output (analysis plan §5).

**DEC-103: Blocked CV, metrics, and the convergence rule for N.**
- **Folds:** forward-chaining by calendar year: test year Y trains on all years before Y. A fold is used if the training years hold ≥ 365 fit days and Y holds ≥ 30.
- **Trend at prediction:** clamped at the last training day for both families. A tree model does this implicitly; a GAM's spline would otherwise extrapolate its end slope into the unseen year. The plan does not specify extrapolation, so this is an implementation choice, applied identically to both families.
- **Metrics:** one Python implementation for both families (`src/normalise/collect.py`), on the log scale the models are fitted on:
  - out-of-sample R², pooled over all test days of a series;
  - RMSE and in-sample R²;
  - residual autocorrelation at lags 1–7: the correlation of residuals exactly k days apart within the same test year (gaps are never bridged).
- **Selection metric:** the median over series of the out-of-sample R² is the registered metric (DEC-088); I report it by pollutant too.
- **Convergence rule for the number of draws N, fixed now:**
  - The pilot draws 1,000 times and records the running mean at N = 50, 100, 200, 300, 500, 1000.
  - N is the smallest grid value at which the deweathered **station-month** mean (months with ≥ 75% valid days) is within **0.5%** of its 1,000-draw value for **≥ 95%** of pilot station-months, in both families and both pollutants. Station-months are the finest unit that gets aggregated (city-month).
  - The proposal says "500–1,000 times" and PLAN.md "300 by default, capped at 1,000". The rule decides, and I will report where N falls against the proposal's range.

**DEC-104: The pilot (20 stations, before the full run).**
- **Selection** (`src/normalise/pilot.py`): stations with a coordinate and ≥ 1,095 valid days of both PM2.5 and PM10, drawn at random (config seed) within each region, **at most one per urban centre**. Five per region; a region's shortfall goes to the regions with the most eligible centres.
- **Why one per centre.** The first draw, without that rule, gave five Mumbai stations for the coastal region and three Delhi stations for the IGP, which is not "across regions". The rule was added before anything was fitted.
- **Result:** 20 stations in 20 urban centres: coastal 5, IGP 8, peninsular/other 5, north-east 2 (only Guwahati and Shillong have eligible stations).
- **What the pilot runs:** both families, both resampling schemes, 1,000 draws, 8 workers (as in the full run). It reports out-of-sample R², residual ACF, convergence in N, the scheme comparison, the family divergence and a run-time estimate for the full run. The full run waits for Reenu's go-ahead.

**DEC-105: A city's deweathered series uses only stations inside its urban-centre polygon.** `station_regions.csv` gives every located station a unit, but 55 stations lie outside any polygon (up to 53 km away) and were given their nearest unit only to assign a region. City-month and city-year means use stations with `km_to_unit` = 0, the same rule as the Phase 4 monitor-gain count (DEC-096) and the satellite polygon. Stations outside a polygon are still deweathered and kept at station level. City series here are all-station means (a station counts in a month or year if it is valid then); the balanced panel is Phase 6. Station-month validity uses the completeness threshold (≥ 75% valid days in the month).

**DEC-106: Figure 3's six cities are chosen by a coverage rule, not by eye.** For PM2.5: in each region, the urban centre with the most valid city-months (ties: more stations), then the next best-covered centres overall until six. Each panel shows the raw city-month mean, the primary family's deweathered series, and the range between the two families as the uncertainty band. The Monte-Carlo error from resampling is much smaller (pilot §4), so the band shows model choice, the larger source of uncertainty. 2020 is shaded.

**DEC-107: Change after seeing pilot output. CV predicts a test year with the trend of the same calendar day one year earlier (`cv_trend: last_year`), not the last training day's trend (DEC-103's clamp).**
- **What the pilot showed.** With few training years, the flexible trend term absorbs part of the seasonal cycle. Clamping the trend at the last training day (late December, peak winter) then carries a winter level into every day of the test year. Example: a GAM trained on 2019–20 at Palwal (site_5050, PM2.5) predicted 2021 at a mean of 5.73 in log units against 3.49 observed (about 9 times too high). The trend term alone contributed +1.78; clamping every weather covariate to its training range changed nothing, so weather extrapolation was ruled out. LightGBM's trees clamp the trend implicitly and are exposed to the same effect.
- **New convention.** A test day gets the trend value of the same day one year earlier, clipped to the training range: "last year's level, at this time of year". It never extrapolates, does not mix up season and level, and is identical for both families.
- **What it affects.** Only the out-of-sample predictions, and so the R² that selects the primary family. The fitted models and the deweathered series do not use CV at all.
- **Honesty about the forking path.** I noticed this while looking at the GAM's pilot results, before LightGBM's were available. The selection between families is registered (DEC-088) and this changes how the selection metric is computed, so the pilot reports the median R² of both families under **both** conventions (`python -m src.normalise.run cvcheck --run pilot`; `docs/deweathering_pilot.md` §2). The full run uses `last_year`. If the two conventions would pick different primary families in the full run, I report that alongside the choice.
- **Not a deviation from the registered plan.** The plan specifies "blocked forward-chaining CV by year" and the median out-of-sample R², both unchanged. How to set the trend for an unseen year was open; DEC-103 filled that gap before the pilot, and this entry replaces DEC-103's choice.
- **Pilot result (added after the run, `docs/deweathering_pilot.md` §2).** `last_year` gives a *lower* median out-of-sample R² than the clamp for both families (all pilot series: LightGBM 0.363 → 0.305, GAM 0.411 → 0.315), because the level it assumes is a year older. The family ranking is the same under both (GAM higher). The convention stays `last_year` on the principle above; I did not choose it for its R², and I report both.

**DEC-108: Upstream outputs marked current with `snakemake --touch` after the Phase 5 config edit (workflow note).** `config/params.yaml` is an input of `ingest_mirror`, so adding the `deweathering:` block made every Phase 2–4 output look stale by modification time. `git diff config/params.yaml` shows that only the `deweathering:` block changed, and only `src/normalise/` and `src/viz/fig3_deweathered.py` read it. So `snakemake --touch` was run for `eda`, `pre_period_checks` and the pilot report instead of a 1.5-hour rebuild with identical results. The pilot fits were produced by hand (`run fit --run pilot`, then `run cvcheck --run pilot`) with the same commands the `normalise_pilot_fit` rule runs. Afterwards `snakemake -n pregate` lists only the full-run steps. The coarse dependency on the whole params file remains (DEC-083 is the same family of problem); narrowing it is left for the Phase 10 clean-clone work.

## 2026-09-27: Phase 5 pilot review (Reenu's rulings) and the full-run set-up

Reenu reviewed `docs/deweathering_pilot.md` and ruled on each open item. **DEC-109 and DEC-110 are deviations from the registered plan** (OSF https://osf.io/jksne/, plan commit `6e24eca`). Both were decided on 2026-09-27, in Phase 5, before any treatment-effect estimate exists, and both will be listed in the final report. The same `snakemake --touch` step as DEC-108 was repeated after this config edit. The only new key outside `deweathering:` is `flags.near_constant`, and every Phase 3 module reads `flags` by key (checked with `grep`), so no earlier output can change.

**DEC-109 (DEVIATION from the registered plan, 2026-09-27): weather resampling within ±15 days of the same date (the seasonal scheme, DEC-102) is primary. Grange & Carslaw's all-year default is run on the full set as a sensitivity analysis.**
- **What the plan says.** The registered plan describes the deweathering as following Grange & Carslaw (2019), whose default resamples weather, day of year and weekday from the whole record.
- **What is done instead, and why (Reenu).** Whole-year resampling pairs a date with weather that never occurs in that season (July weather on a January day, a monsoon week in December). The model then predicts outside the joint conditions it was fitted on. The seasonal scheme draws each day's whole weather vector from ERA5 days within ±15 days of the same date, in any year 2015–2025. It keeps the seasonal cycle, and it still removes the year-to-year weather variation that RQ2 asks about.
- **Sensitivity.** The Grange & Carslaw default (`annual`) is run on every series with the same N, the same draws file per scheme and both families. The pilot showed that the two schemes' year-on-year changes differ by about as much as the weather effect itself (pilot §5). So **H4 and figure 3 are reported under both schemes**: `reports/figures/fig3_deweathered` (seasonal) and `fig3_deweathered_grange_carslaw` (annual). The deweathered tables carry both (`dw`, `dw_annual`).

**DEC-110 (DEVIATION from the registered plan, 2026-09-27): a near-constant-analyser rule, added before any treatment-effect estimate. It is applied in the primary analysis; the registered flags alone are the sensitivity analysis.**
- **Why.** The pilot found a station (Bagalkot, site_5264) whose PM series barely moves from day to day for four years: a 15-day rolling SD of log PM of 0.001–0.05, against about 0.3 at a typical station. The flatline rule (≥ 4 identical hourly means, DEC-068) misses it because the hourly values still change slightly. The registered plan's exclusion rules (flags, completeness) do not cover this.
- **Rule** (`src/clean/nearconstant.py`, `config/params.yaml: flags.near_constant`; generated report `docs/near_constant_check.md`):
  - A day is flagged if the 15-day centred rolling SD of log daily PM (≥ 10 valid days) is below S, **and** either no neighbour within 25 km has a value that day, or the SD is below R × the neighbours' median SD that day. The first condition says "nearly constant"; the second says "not a calm spell the whole airshed shares".
  - A station-year is flagged with ≥ 30 flagged days, i.e. a stuck month.
- **Calibration.** S and R are each the 0.1% quantile over days of clearly working stations: station-years that correlate with their neighbours at r ≥ 0.8 (2,649 station-years, 286 stations). Result: R = 0.218.
  - A first version used one national S (0.0485). A regional check then showed the calm tail differs by region: working stations' 0.1% quantile is 0.077 in the IGP, 0.037 in the peninsula and 0.024 on the coast. So a national S over-flags the coast and peninsula and under-flags the IGP.
  - S is therefore calibrated per region, with the national value for the north-east (only 4 working stations; minimum 20). This refinement was made while developing the rule, before its results were used anywhere.
  - A second check: 59% of flagged days have a rolling SD below 0.01 (essentially constant), and flagged days fall in every month rather than in one season.
- **Result.** **77 of 4,129 station-years valid under the registered rules (1.9%), at 33 stations** (39 PM2.5, 38 PM10), plus 37 that were already invalid. False alarms on clearly working stations: 0.051% of days, and 5 of 2,649 station-years. At least 3 of those 5 are unmistakably stuck spells (median SD 0.004–0.007) inside otherwise good years.
- **How it is applied.**
  - *Primary* (`rule = primary`): flagged station-years are left out of the deweathering fit (run `main`), and they are invalid in every station-year, station-month and city aggregate.
  - *Sensitivity* (`rule = registered_flags`): the registered rules only. Series that have flagged station-years are refitted with those years kept (run `registered`, only those series), so the sensitivity analysis is exactly what the registered plan would have produced.
  - Every later phase carries both rules.

**DEC-111: What the 5% family-disagreement flag is 5% of, and why the pilot counted 37 of 40 series.**
- **Definition.** For each station-pollutant, over its station-years valid under the primary rule (primary completeness variant, seasonal scheme): take each family's log annual deweathered mean and subtract that family's own mean over those years. D is the largest absolute gap between the two centred series, in % (100 × log units).
  - So D compares **how the annual level moves over the years**. It is not the level itself (a constant difference between the families is not disagreement), and it is not one year-on-year change (a gap that builds up over several years counts).
  - A series **diverges** if D > 5% (`deweathering.divergence_flag_pct`).
- **Why 37 of 40.** 3 pilot series (Coimbatore PM2.5 and PM10, site_5094; Shillong PM10, site_5131) have 1,100–1,250 valid days in total but no single year with ≥ 75% valid days, so they have no valid station-year and no D.
- **A flaw it exposed, now fixed.** One series had a single valid year, where D is 0 by construction and counted as "agreeing". D now needs ≥ 2 valid years (`divergence_min_years`); with this rule the pilot has D for 34 series.

**DEC-112: A within-period blocked CV, reported beside the registered forward-chaining CV, never used to choose the family (Reenu).**
- **Why.** Forward-chaining CV also tests how well the trend term extrapolates to an unseen year, which deweathering never needs: the deweathered series uses each day's own trend. It therefore understates how well the models capture the weather response.
- **Design** (`deweathering.cv_within_folds`, `cv_within_buffer_days`):
  - Calendar months are dealt round-robin into 10 folds, so consecutive months fall in different folds and each fold's months are spread over the record.
  - Each fold's held-out days are predicted with their own trend, by a model trained without them and without any day within 7 days of one. The buffer stops the multi-day persistence of pollution episodes from leaking across the boundary (residual ACF at lag 7 is still about 0.55; pilot §3).
- **Why 10 folds, not literally one month at a time.** Reenu suggested leave-one-month-out as an example. That is 80–130 model fits per series (about 100,000 in total); 10 folds give the same kind of test with 10 fits per series. Metric: `r2_within`, pooled like `r2_oos`.

**DEC-113: N = 500 weather draws for the full run (Reenu), for both schemes.**
- **Why.** The pre-stated convergence rule gave N = 300, but only narrowly (LightGBM PM2.5: 0.9502 of station-months within 0.5% against the 0.95 threshold). N = 500 is inside the proposal's 500–1,000 range, and every cell of the seasonal scheme is then above 0.994.
- **Station-year check (pilot, 1,000-draw reference).** At N = 500, every valid station-year is within 0.5% under both schemes (95th-percentile deviation 0.08% seasonal, 0.16% Grange & Carslaw).
- **The Grange & Carslaw scheme's monthly values** converge more slowly (worst cell 0.911 of station-months within 0.5% at N = 500). This is noted for its figure 3; its annual numbers, which H4 uses, are converged.

## 2026-09-28: Phase 5 full run (results that bear on decisions)

Numbers from `docs/deweathering_report.md` (generated). The full run completed on 2026-09-28 with no failed task: 1,054 series × 2 families (main), 66 × 2 (registered-flags refits), and CV-only predictions for every series under both trend conventions. As in the pilot, the CV-only `last_year` predictions are identical to the main fits' (checked on 60 sampled series, maximum difference 0).

**DEC-114: The primary family is the GAM, by the registered rule (DEC-088) under the approved `last_year` convention (DEC-107). The choice is sensitive to that convention, and I report it that way.**
- **Registered rule.** Median out-of-sample R² over 946 series with a CV fold: GAM 0.460, LightGBM 0.432; the GAM is better in 713 series. So the GAM is primary and LightGBM is the sensitivity analysis.
- **Under the `clamp` convention the choice flips:** LightGBM 0.450, GAM 0.390. The pilot had the GAM ahead under both; the full set does not. The GAM loses most under `clamp` because its trend term follows more within-year movement (report §5), so a trend frozen at late December carries more season into the test year.
- **Consequence.** The primary-family choice rests on DEC-107, a convention I changed after seeing pilot output and Reenu approved. It stays as registered (Reenu, 2026-09-27). The final report states that the other convention would have picked LightGBM, and every downstream result is shown under both families anyway (the "other family" sensitivity).
- **Within-period CV** (DEC-112, diagnostic only): medians GAM 0.63–0.64, LightGBM 0.64. Both families capture the weather response about equally well once trend extrapolation is removed from the test. In-sample R² is 0.78 (GAM) and 0.99 (LightGBM).

**DEC-115 (finding, no change made): under Grange & Carslaw resampling the GAM gives implausible deweathered values at some stations. The primary (seasonal) results are unaffected.**
- **Evidence** (report §5; valid station-months and station-years, primary rule): deweathered-to-raw ratio above 5 in 330 station-months for the GAM under Grange & Carslaw (0 seasonal), and above 2 in 52 GAM station-years (maximum 370×). LightGBM under Grange & Carslaw: 18 months above 5, 0 station-years above 2 (maximum 1.3). The seasonal scheme's largest station-year ratio is 1.2 for the GAM and 1.1 for LightGBM.
- **Mechanism (likely).** The flexible trend absorbs part of the seasonal cycle. Under Grange & Carslaw the deweathered GAM series keeps 22–23% of the raw within-year variation, against LightGBM's 9–10%. Whole-year resampling then pairs a day's trend with another season's day of year and weather, outside the fitted data. Splines extrapolate linearly on the log scale, and the mean of exponentials is dominated by the extreme draws.
- **Consequence.** The Grange & Carslaw sensitivity (DEC-109), and H4 under it, would be contaminated if taken from the GAM.
- **Options for Reenu:**
  - (a) take the Grange & Carslaw sensitivity from LightGBM, which is clean at station-year level;
  - (b) refit the GAM with a less flexible trend (e.g. 1–2 basis functions per year instead of 4; about 1.5 h). This also bears on the trend-absorption question (PROGRESS);
  - (c) both.
- **Not changed unilaterally:** it is a model-specification choice made after seeing results.

## 2026-09-28: Phase 5 review (Reenu). Rules written BEFORE the GAM refit

Reenu reviewed Phase 5 and asked for a stiffer GAM trend, set by a timescale rule decided before looking at any refit result. This section is committed and pushed before the refit is run, so the rule's timestamp precedes its results.

**DEC-116 (DEVIATION from the registered plan and from DEC-101, 2026-09-28): the GAM's trend has knots exactly one year apart, so it cannot follow seasons or weather episodes. The previous GAM (4 basis functions per year) is kept as a sensitivity family, `gam_k4`.**
- **Why (Reenu).** The trend should represent slow emission change, not seasons or individual weather episodes. A trend that absorbs part of the seasonal cycle can also absorb year-specific weather, which would understate the weather effect. Report §5 showed the old trend kept 22–23% of the raw within-year variation under Grange & Carslaw resampling, and DEC-115 showed where that leads.
- **The rule** (`config/params.yaml: deweathering.gam.trend_rule = annual_knots`), applied identically to every station and to every model fitted, including each CV training set:
  - Let span = the years between the first and last day the model is fitted on.
  - The trend is a penalised cubic regression spline (mgcv `bs = "cr"`) with k = ⌊span⌋ + 1 knots **evenly spaced over the span**, so neighbouring knots are at least one year apart. Knots are placed by date, not at data quantiles, so gaps in a record cannot bunch them.
  - If k < 3 (span under 2 years), the trend is a straight line (a parametric term), because `cr` needs 3 knots.
  - REML (fREML) still chooses how smooth the spline is within that limit, as before.
- **Why "one year apart".** A cubic spline can bend only at its knots. Following a cycle needs at least two knots per cycle, so with knots a year apart the trend cannot represent any periodic change of one year or shorter: not the seasonal cycle, not a stagnant month, not a monsoon. It can follow changes that build up over about two years or more, which is the timescale of emission policy.
- **Consequence stated in advance.** Short emission shocks, such as the 2020 lockdown (a few months), can no longer be followed by the trend. They move into the residuals and are partly smoothed out of the deweathered series; the raw series keeps them. So "deweathering does not remove the lockdown" becomes "the lockdown is partly averaged into the neighbouring months". 2020 keeps its own handling in every later analysis (plan §5), and the flag stays. The same holds for a sudden instrument level shift.
- **Pilot runs** keep the old trend (`deweathering.pilot.gam_trend_rule = k_per_year`), so `docs/deweathering_pilot.md` rebuilds as the historical record it is.
- **Unchanged:** everything else (other smooths, inputs, the same resample draws, CV folds, schemes, N). LightGBM is not refitted.

**DEC-117: selection and reporting after the refit (Reenu, fixed before the refit).**
- **Selection.** The registered rule (DEC-088; median out-of-sample R², forward-chaining CV, `last_year` convention, DEC-107) is re-applied between the refitted GAM and LightGBM. **Whichever wins is primary, even if that is LightGBM.** The refitted GAM's `clamp`-convention and within-period R² are reported too.
- **Grange & Carslaw sensitivity:** from both families, after the refit. The old `gam_k4` results are reported beside them as the sensitivity to trend flexibility.
- **Extrapolation guard**, reported for every family and scheme; nothing is dropped:
  - (a) the number and share of resampled prediction rows with any weather input outside the range that station's model was trained on;
  - (b) the share of rows pairing a day with a day of year more than the seasonal window (±15 days) away, i.e. out-of-season pairings;
  - (c) station-years whose deweathered annual mean is more than 1.5× or less than 0.67× the raw annual mean over the same days (`deweathering.guard_ratio`), flagged in `station_year.parquet`.
  - (a) and (b) depend only on the training data and the draws, so they are the same for every family. How each family behaves there differs: a GAM extrapolates, trees do not. (c) shows the result.
- **Figure 3** gets an annual view (raw vs deweathered annual means, both schemes).

## 2026-09-28: Phase 5 GAM refit results (after DEC-116/117, committed in `72f2fc3` before the refit)

**DEC-118: The refitted GAM is primary under the registered rule, and now under both CV conventions. The refit fixed the Grange & Carslaw failure, and it shows the old trend was absorbing weather.**
- **Refit.** The refit (`python -m src.normalise.run fit --family gam`, main and registered, then `cvcheck --family gam`) completed on 2026-09-28 with no failed task. The previous GAM's outputs were moved, unchanged, to the family `gam_k4` (a rename, not a recomputation). The CV-only `last_year` predictions of the refitted GAM match its main fits exactly (60 sampled series).
- **Selection (DEC-117, registered rule).** Median out-of-sample R², 946 series: refitted GAM 0.476, LightGBM 0.433 (the GAM better in 756). Under `clamp`: GAM 0.469, LightGBM 0.450. **The GAM is primary under both conventions**, so DEC-114's sensitivity to the convention is gone. The previous GAM scored 0.460 (`clamp` 0.390): the stiffer trend predicts unseen years better.
- **Within-period CV** (diagnostic): the refitted GAM scores 0.59–0.61, against 0.63–0.64 for the previous GAM and LightGBM. That is expected: a trend that cannot follow within-year movement fits held-out months slightly less closely.
- **Trend absorption** (report §5, Grange & Carslaw): the refitted GAM keeps 7–8% of the raw within-year variation, against the previous GAM's 22–23% and LightGBM's 9–10%.
- **Extrapolation guard** (report §5; DEC-117):
  - (a) Under both schemes, 0.9% of the 887 million resampled rows take any weather input outside the station's training range.
  - (b) 91.5% of Grange & Carslaw rows pair a day with another season; none do under the seasonal scheme.
  - (c) Station-years outside 0.67–1.5× raw: in the refitted GAM, 0 above 1.5× under either scheme (maximum 1.33× seasonal, 1.36× Grange & Carslaw). The previous GAM under Grange & Carslaw has 68 above 1.5× (maximum 370×). LightGBM has 0 above 1.5×.
  - In every family, exactly one station-year is below 0.67×: Satna, Bandhavgar Colony (site_1433, an industry-run station), PM2.5 in 2018 (raw 18.2 µg/m³). The near-constant rule flags most of that station's other years, and it stays flagged, not dropped.
- **The weather effect is larger than the previous GAM said.** City-level year-on-year changes in annual PM2.5 have a median of 10.3%. Their weather part has a median of **5.1%** (90th percentile 12.6%), against 3.0% (8.1%) with the previous trend. The two schemes now agree (5.1% vs 5.2%, where before they gave 3.0% vs 4.3%).
  - This supports Reenu's reason for DEC-116: the flexible trend was absorbing year-specific weather and understating its effect.
- **Family divergence** (DEC-111, D > 5%): 355 of 822 series (median D 4.0% PM10, 4.8% PM2.5), against 72 before the refit.
  - The refitted GAM's trend moves only slowly, while LightGBM's trend splits can still follow short-lived movements, so their annual series now differ more.
  - Divergence is therefore a property of the trend definitions as much as of the weather models. The LightGBM ("other family") sensitivity in Phases 6–7 is correspondingly more informative, and its results must be reported beside the primary, not summarised away.
- **2020 wording corrected.** With the one-year-knot trend, the lockdown is partly averaged out of the deweathered series (stated in advance in DEC-116). The report and figure notes now say so instead of "deweathering does not remove the lockdown".

## 2026-09-28: Phase 5 second review (Reenu). Lockdown rule written BEFORE the test fit

**DEC-119: A pre-set test of whether the 2020 lockdown smears into 2019 and 2021 under the one-year-knot trend (Reenu). This section is committed before the test is fitted.**
- **The concern.** The trend (DEC-116) cannot follow a dip lasting a few months. The spring-2020 lockdown could therefore pull the trend down around 2020, and the deweathered annual means of 2019 and 2021 with it.
- **Lockdown period.** Indian days **25 March 2020 to 31 May 2020, inclusive**: India's national lockdown, phases 1–4 (25 Mar–14 Apr, 15 Apr–3 May, 4–17 May, 18–31 May). Unlock 1 took effect on 1 June 2020 (MHA guidelines of 30 May 2020; PIB PRID 1627965; checked 2026-09-28).
  - One national definition for every station. State-level restrictions before 25 March or after 31 May, and containment zones, are not modelled.
  - `config/params.yaml: deweathering.lockdown = ["2020-03-25", "2020-05-31"]`.
- **Model tested (`gam_lock`).** The DEC-116 GAM plus a parametric 0/1 term `lockdown` (1 on lockdown days).
  - The term is included only when the data a model is fitted on hold ≥ 10 lockdown days; otherwise it is omitted, because it cannot be estimated. The same holds for each CV training set.
  - In resampling the indicator is a calendar variable, like the trend and day of year: each day keeps its own value, and only weather is resampled.
  - Everything else is identical: the same inputs, fit days, near-constant exclusions, weather draws and N.
- **Test set.** The 20 pilot stations × 2 pollutants (40 series), fitted from the full-run (`main`) inputs as family `gam_lock` and compared with the full-run `gam` fits of the same series.
- **Metric, fixed now.** Over pilot station-years in **2019 and 2021** that are valid under the primary rule (primary completeness variant, near-constant station-years excluded), primary seasonal scheme: the absolute difference |dw_gam_lock / dw_gam − 1| in %. Take the median over those station-years, both pollutants and both years pooled.
- **Decision rule, fixed now (Reenu).**
  - **If the median exceeds 1%:** add the indicator to the primary GAM for all stations (a dated deviation from the registered plan); refit `main` and `registered` and their CV checks; re-run the registered selection rule between the new GAM and LightGBM.
  - **Otherwise:** record the result and leave the model as it is.
- **Also reported, not used for the decision:** the medians for 2019 and 2021 separately, and for 2020.

**DEC-120: City-level family disagreement on the H4 quantity (Reenu).**
- **Why at city level.** DEC-111's D measures disagreement in station-level movement. H4 is a city-level change, so disagreement is also reported at the level H4 analyses.
- **Quantity, per urban centre, pollutant and resampling scheme** (primary validity rule, primary completeness variant):
  - take the **balanced panel**: stations inside the unit polygon (DEC-105) that are valid in 2018 and in every year to 2025 (DEC-088's baseline definition);
  - city deweathered mean = the mean over those stations, for each family;
  - change = 100 × (mean₂₀₂₅ / mean₂₀₁₈ − 1), in %;
  - disagreement = GAM change − LightGBM change, in percentage points.
- **Reported:** the distribution over cities, and every city where |disagreement| > 5 pp, named.
- **Looser panel.** A version on the looser panel (valid in both 2018 and 2025, not necessarily every year between) is shown too, because the strict panel may hold few cities.
- **No NCAP comparison.** The Phase 6 H4 restricts to NCAP cities; this diagnostic covers every city with a panel.

**DEC-121: Satna, Bandhavgar Colony (site_1433): no station-level override (Reenu). It is named wherever it appears in Phase 6 results.**
- **Status.** It stays under the registered rules; its near-constant station-years are excluded in the primary analysis like any other (DEC-110).
- **The reliability sensitivity does not reach it.** Reenu asked that the reliability-score sensitivity cover this station. The registered check (plan §5: drop station-years with reliability < 50, DEC-073) removes **none of its valid station-years**.
  - Its valid station-years score 55.3–93.6. The one below 50 (PM2.5 2024, 36.6) is already invalid under the completeness rule.
  - The suspect PM2.5 2018 station-year scores 61.5. Its PM2.5 fails the satellite check in 2018–2022 (station far below the satellite value), which supports an instrument problem.
- **Not done unilaterally.** Making the check cover it would need a different threshold (a registered value) or an extra named-station sensitivity. That choice is Reenu's; it is raised at the end of Phase 5.
- **Naming in Phase 6.** `config/params.yaml: watch_stations: [site_1433]` lists it, so Phase 6 outputs name it wherever it contributes.

**DEC-122: Results of the two checks (2026-09-28; rules in DEC-119/120, committed in `f09c22e` before the test fit).**
- **Lockdown smear test (DEC-119).**
  - *What was fitted:* `gam_lock` on the 40 pilot series (the lockdown term entered 35).
  - *Result:* median |difference| in 2019/2021 deweathered annual means over 48 valid station-years = **0.55%, below the 1% threshold. The primary GAM stays as it is**, as the pre-set rule requires.
  - *Separately:* 2019 0.95% (75th percentile 2.3%, maximum 4.2%), 2021 0.30%, 2020 1.02%. The smear that exists falls mostly backward, on 2019, which alone is just under the threshold.
  - *Why no action on 2019:* the rule pooled 2019 and 2021, and it was applied as written.
  - *Consequences for later phases:* Phase 7 already drops 2020 from the primary satellite panel and gives it its own indicator on the ground (plan §5). The 2019 figure is reported in `deweathering_report.md` §7 so Phase 7 can weigh it: 2019 is the first NCAP year for most cities.
  - *Kept for the record:* the `gam_lock` fits of the pilot series (`fits/main/gam_lock/`).
- **City-level disagreement on the H4 quantity (DEC-120).**
  - *Panel size:* the strict 2018–2025 balanced panel holds 19 cities for PM10 and 23 for PM2.5, and most cities hold one station.
  - *Size of the disagreement:* GAM minus LightGBM change in the deweathered city mean from 2018 to 2025 has a median absolute value of 2.4–3.2 pp and a 90th percentile of 5.5–8.6 pp. More than 5 pp in 5 cities per pollutant (primary scheme) and 3–7 (Grange & Carslaw); up to 14 pp on the loose panel.
  - *Largest:* Kolkata PM2.5 (raw −18.4%; GAM −1.9%, LightGBM −14.6%) and Bengaluru PM2.5 on the loose panel (+13.9 pp).
  - *Consequence:* where the families differ this much, the share of a city's measured change that H4 attributes to weather depends on the model family. Phase 6 reports H4 under both families, never one alone.
  - Table: `deweathering_report.md` §8; `data/processed/deweathered/city_disagreement.csv`.
- **Satna (DEC-121).** Under the primary rule it is in no 2018–2025 panel: its near-constant years (PM10 2024–25; PM2.5 2021–23 and 2025) are excluded. Under the registered-flags rule it would be. The reliability < 50 sensitivity removes 0 of its valid station-years (report §9); the question is open for Reenu.

## 2026-09-28: Phase 5 approved (Reenu)

**DEC-123: Lockdown: the pre-set rule stands, so there is no lockdown indicator. Phase 7 adds a Layer B sensitivity analysis that excludes 2019 (an added check, not a rule change).**
- **The model.** The primary GAM stays as it is (DEC-119/122: median 0.55% < 1%).
- **Why the added check.** The small smear the test found falls mostly on 2019 (0.95% on its own), and 2019 is the first NCAP year for most cities. So Phase 7 reruns the ground-layer (Layer B) estimates **without 2019**, as an additional sensitivity analysis.
- **How it is labelled.** It is logged and reported as a check added on 2026-09-28 after the smear test. It changes no registered rule or primary result, and it does not affect Layer A: the satellite panel is not deweathered.

**DEC-124: Satna, Bandhavgar Colony (site_1433): the registered reliability threshold stays at 50. One post-hoc sensitivity analysis drops the station from the registered-rules-only version (Reenu).**
- **Where it applies.** Wherever results are computed under `rule = registered_flags` and site_1433 contributes (Phases 6–7), they are also computed without it.
- **How it is labelled.** It is marked everywhere as **"added after inspecting the data"**, because it was chosen after seeing this station's values. Config: `posthoc_drop_registered: [site_1433]`.
- **Why the primary rule needs no such check.** Under the primary rule the station's near-constant years are already excluded (DEC-110), and it is in no 2018–2025 panel.
- **What the report says.** `deweathering_report.md` §9 states that the reliability score does not catch this station (its valid station-years score 55–94, above the < 50 threshold), while the stuck-instrument rule does (it flags most of its later years). The numbers are generated.
- **Unchanged:** no station-level override (DEC-121). The station stays named via `watch_stations`.

## 2026-09-30: Phase 6 (network-composition correction, RQ1 and H4). Rules written BEFORE any Phase 6 result

The gate is open (plan `6e24eca`, OSF https://osf.io/jksne/). Phase 6 uses NCAP status in one place only, H4, which the plan registers as a secondary, descriptive hypothesis over NCAP cities (plan §5). Nothing here contrasts NCAP with non-NCAP units; that is Phase 7's job. Everything below was written and committed before any Phase 6 quantity was computed.

**DEC-125: The three city trends, and what a "city" is.**
- **City = urban-centre unit** (DEC-105; the same polygon as the satellite value). NCAP cities sharing a polygon are one unit (e.g. Delhi, Faridabad, Ghaziabad and Noida). The registered text says "per NCAP city"; splitting a shared polygon by the station's city label would give ground series with no matching satellite unit, so the unit is used throughout.
- **NCAP units** = the units in `data/interim/pregate/units.csv` that hold an NCAP city. This includes a buffered town (DEC-063) if a station lies inside its buffer: H4 describes NCAP cities only, so Layer A's reason for excluding buffered towns (treated and control units must be defined alike) does not apply.
- **Trend 1, all stations as reported:** each year, the mean of the annual means of every station inside the polygon that is valid that year (flagged values removed, completeness rule applied). This is the network "as reported" after the audit's cleaning, not the portal's unvalidated number.
- **Trend 2, balanced panel:** stations inside the polygon that are valid in the baseline year **and every year to 2025** (strict). Baseline 2018 is primary and 2019 the sensitivity (DEC-088). Each year's value is the mean over the panel stations, raw and deweathered. Years before the baseline are not part of the panel.
- **Trend 3, satellite:** ACAG V5.GL.06, population-weighted over the unit (DEC-070), 2015–2024 (the product ends in 2024). V6.GL.03 is the product sensitivity.
- A city mean is the unweighted mean of station annual means, as in `city_year` (DEC-105).

**DEC-126: Changes, composition bias, ground vs satellite, and the decomposition.**
- **Change** from the baseline to 2025 = 100 × (mean₂₀₂₅ / mean_baseline − 1), in % (DEC-120's definition). Differences of changes are in percentage points (pp).
- **Composition bias** = change(all stations) − change(balanced panel).
  - Primary on raw values (what a tracker reports); also computed on deweathered values.
  - Also given per year, as the gap between the two trends indexed to the baseline.
- **Ground vs satellite** (PM2.5 only) = change(balanced panel, raw) − change(satellite), 2018 → **2024**, because the satellite ends in 2024.
  - Raw, because the satellite is not deweathered.
  - The all-station and deweathered versions are shown beside it.
- **Decomposition for figure 1, in the proposal's order** (reported → weather → composition → policy):
  - reported = change(all stations, raw);
  - weather = change(all, raw) − change(all, deweathered);
  - composition = change(all, deweathered) − change(panel, deweathered);
  - corrected = change(panel, deweathered) = reported − weather − composition (exact);
  - policy: a placeholder until Phase 7.
- **The other order** (composition on raw values first, then weather on the panel) is reported as a check. The two orders differ only by an interaction term.

**DEC-127: H4's sign, read from the hypothesis. This clarifies an ambiguous registered rule and will be listed with the deviations in the final report.**
- **The ambiguity.**
  - H4 (plan §1): "Reported (raw, all-station) *improvements* in NCAP cities exceed deweathered, composition-corrected *improvements*."
  - The decision rule (plan §5): "raw all-station change minus deweathered balanced-panel change … Supported if the mean across cities is positive."
  - If "change" means the change in concentration (a fall is negative), a reported fall larger than the corrected fall makes that difference **negative**. The rule, computed literally, would then call the opposite of the hypothesis "supported".
- **Reading adopted:** "change" in the rule means improvement, i.e. the fall in %.
  - Per city, **H4 = (reported fall) − (corrected fall) = change(panel, deweathered) − change(all, raw)**, in pp. This is weather + composition from DEC-126, with the sign flipped.
  - **H4 is supported if the mean across NCAP cities is positive and its 95% cluster-bootstrap CI excludes 0.**
- **Why this is the test that was registered.** Both readings test the same statement: the reported fall is larger than the corrected fall. Only the sign label differs, and the hypothesis text fixes which sign counts as support. Decided before computing any Phase 6 value.

**DEC-128: H4's primary version, and every version reported beside it.**
- **Primary:** GAM with one-year knots (the primary family, DEC-118), seasonal resampling (DEC-109), the primary validity rule (DEC-110), baseline 2018, completeness q1_t75, strict panel, and every NCAP unit with a panel. **LightGBM with the same settings is shown beside it in every table**, never summarised away (DEC-118/120).
- **As registered, with no deviations:** GAM with the previous trend (`gam_k4`, the family the registered rule chose before DEC-116; DEC-114), Grange & Carslaw resampling, and the registered flags only. Reported and labelled as such.
- **Grid:** {GAM, LightGBM, GAM k4} × {seasonal, Grange & Carslaw} × {primary, registered flags}.
- **One change at a time from the primary, for both competing families:**
  - baseline 2019;
  - completeness 60%, 90%, and 3 of 4 quarter-hours;
  - drop the 5 Reenu-decided stations (DEC-080);
  - drop station-years with reliability < 50 (DEC-073);
  - loose panel: valid in the baseline year and 2025 only (not registered; DEC-120);
  - no deweathering: the raw balanced panel, so H4 = composition only.
- **Post-hoc sensitivity, "added after inspecting the data" (DEC-124):** every registered-flags row is recomputed without site_1433.
  - Satna's unit (u0908) is not an NCAP unit, so this cannot change H4. It is computed anyway.
  - It is also applied to the all-city composition summaries, where the station can contribute.
- **The FY2025-26 sensitivity (plan §5, "+ Jan–Mar 2026") cannot be computed here.** The deweathered series end on 2025-12-31 (`deweathering.fit_end`, DEC-079), so no deweathered January–March 2026 exists. The report states this.

**DEC-129: Uncertainty.**
- **Across cities** (H4 and every summary):
  - cluster bootstrap over cities, 1,000 resamples (`composition.bootstrap_draws`), percentile 95% CI, config seed;
  - SE = SD of the bootstrap means;
  - the mean is unweighted across cities, as registered;
  - where a CI includes 0, 2.8 × SE is reported beside it as the smallest mean the design could reliably detect (hard rule 8; the descriptive analogue of an MDE).
- **Per city:** a stratified station bootstrap inside the city, 1,000 resamples.
  - Panel stations are resampled among the panel stations and the other stations among the others, so every draw keeps a panel.
  - A city with one station in a stratum gets no between-station uncertainty from that stratum. The report says so and shows the family range (GAM vs LightGBM) separately.
- **Coverage:** composition summaries cover every city with a panel, NCAP or not; **H4** covers NCAP units only.

**DEC-130: Two diagnostics, method fixed now.**
- **"Do new stations read cleaner?", on deweathered data.**
  - Definition as in Phase 3 (`src/viz/eda.py: entrants`): per unit-year, log(mean of entrants' annual means) − log(mean of incumbents'). An entrant is in its first valid year; an incumbent was valid before.
  - Here: stations inside the polygon (DEC-105), primary rule, q1_t75, over the same station-years for raw and deweathered (both families, both schemes), plus the paired difference deweathered − raw.
  - Per-year t-intervals as in Phase 3; the pooled estimate uses a cluster bootstrap over units.
- **Family disagreement.** Covers Kolkata and every city whose GAM and LightGBM 2018–2025 deweathered changes differ by more than 5 pp in the primary H4 setting (strict panel, primary rule, either scheme).
  - *Which variables drive it:*
    - Each model's log prediction is split into additive parts: the GAM's terms (`predict(type = "terms")`) and LightGBM's TreeSHAP contributions (`pred_contrib`).
    - Parts are grouped as temperature; humidity; wind (speed, direction, their interaction); boundary-layer height (daily mean, afternoon maximum); precipitation; solar radiation; and trend/calendar.
    - A group's weather effect in year Y = the mean over the station's fit days in Y of [its part under the actual weather − its mean part over the first 100 of the station's 500 shared weather draws].
    - The change from 2018 to 2025 is that group's contribution, per family, in log units × 100 (≈ %).
    - Their sum is checked against each family's implied weather change, log(raw/deweathered).
  - *Is the actual weather consistent with it:* ERA5 at the station's cell, all days:
    - annual and cold-month (January, February, October–December) means for 2015–2025;
    - 2025 − 2018, in units and in SDs of the annual means;
    - OLS trend per decade with a 95% CI;
    - the correlation of each variable's annual mean with the year. A trending variable can be credited to the trend by one family and to weather by the other.
    - Physically expected signs are stated only where they are unambiguous: a higher boundary layer, faster wind or more rain → lower PM.
  - Reported as a finding. **It does not choose a family**; the registered rule did that (DEC-118).

**DEC-131: H4 is tested for PM2.5 and PM10 separately; neither is designated primary, and they are never pooled (written before computing, after DEC-125 to DEC-130 were committed in `29874cf`).**
- The plan registers H4 without naming a pollutant, and reports Layer B "for PM2.5 and PM10 separately". Each pollutant is one test of a secondary hypothesis at 0.05 (plan §5). If they disagree, both are reported as they are.
- **"All stations as reported" is limited to deweathered series.** 11 valid station-years to 2025 inside a polygon (PM2.5: 1 in 2024 and 5 in 2025; PM10: 5 in 2025; registered completeness rule) belong to series too short to deweather (fewer than 365 valid days). Keeping one station set for every quantity makes the decomposition add up exactly. The report shows how much adding them back would change each NCAP city's reported change.

## 2026-09-30: Phase 6 results and one method change (numbers from `docs/composition_report.md`, generated)

**DEC-132: H4 results. Supported for PM2.5 and PM10 in the primary version, beside LightGBM and as registered.**
- **Primary (GAM, seasonal, primary rule, 2018 panel):**
  - PM2.5: +9.5 pp (95% CI +4.8 to +14.5; 18 NCAP cities, 16 with a panel of one station);
  - PM10: +6.0 pp (+1.8 to +10.0; 13 cities).
- **LightGBM, same settings:** PM2.5 +8.6 (+4.7 to +12.6); PM10 +5.3 (+3.1 to +7.7).
- **As registered, no deviations:** PM2.5 +10.3 (+5.3 to +14.8); PM10 +6.5 (+3.9 to +9.5).
- **Robustness:** supported in 31 of 31 versions for PM2.5 and 29 of 31 for PM10. Not supported:
  - LightGBM with the 2019 baseline, PM10: +1.7 (−0.1 to +3.5; 2.8 × SE = 2.6);
  - no deweathering, PM10: +0.1 (−2.1 to +2.4). This version measures composition alone.
- **What drives it:**
  - PM2.5: mostly composition (+5.8 pp of the +9.5);
  - PM10: mostly weather (+4.9 of +6.0).
  - The weather part compares two single years (2018, 2025), because that is how H4 is registered.
- **Not computable:**
  - completeness 90%: no NCAP city has a 2018 panel;
  - the FY2025-26 sensitivity (DEC-128).
- **Satna (post-hoc, DEC-124):** it cannot enter H4 (not an NCAP unit). Under the registered-flags rule it is a one-station PM10 panel in its own city with composition bias 0, so dropping it changes no H4 result. In the all-city summaries it removes one PM10 city with a bias of 0: the mean PM10 composition bias moves from +0.80 to +0.84 pp. PM2.5 is unchanged, because the station has no strict PM2.5 panel.
- **The as-registered version's weather/composition split is distorted** by 3 all-station station-years outside the extrapolation guard (the DEC-115 blow-ups). Its panels hold none, so its H4 is unaffected.

**DEC-133: The family-disagreement split of DEC-130 failed its own pre-set check; it is replaced by a split on the annual-mean scale (changed after seeing the check fail; the diagnostic chooses nothing).**
- **What failed.** DEC-130 split each family's weather effect into variable groups on the log scale (GAM terms, LightGBM TreeSHAP) and required the parts to add up to the implied weather change, 100 × change in log(raw/deweathered). They do not. For Kolkata's GAM (PM2.5) the parts sum to −3.5 against an implied −18.4; the generated report gives the full gap distribution.
- **Why.** Two reasons, both checked on the saved fits:
  - *Scale.* H4 and the deweathered change are changes in arithmetic annual means. There, weather acting on the most polluted days counts for more than on the log scale: Kolkata's mean log PM2.5 fell 6.8 points while its arithmetic mean fell 18.4%.
  - *Misfit.* A model's fitted values need not reproduce a station's arithmetic annual mean. Kolkata's GAM fitted mean is 8.1% below the observed mean in 2018 and 3.3% above it in 2025. So 11.4 points of the fall are reproduced by neither its trend nor its weather terms. Deweathering drops that part, so raw − deweathered counts it as "weather". LightGBM's fitted means match the observed to within 1.5%.
- **Replacement** (`family_diag.attribution`). Everything is on the annual-mean scale, and the parts add up to the implied change exactly, up to Monte-Carlo error:
  - each variable group switched alone to its actual values, with the others at typical weather;
  - the groups' joint part;
  - the model's misfit.
- **Added for H4** (`misfit_h4`): the misfit change for every panel station of the H4 cities, per family. It shows how much of H4's "weather" part is misfit rather than weather.
- **Kept for the record.** The log-scale table (`family_diag_contrib.csv`) and its failed check (`family_diag_check.csv`) stay in the outputs and in the report.
- **Why changing the method after the check is acceptable here.** The diagnostic is not a hypothesis test and selects nothing; the registered rule chose the family (DEC-118). The check was written in advance precisely to catch a split that does not explain the quantity, and it did.

**DEC-134 (workflow note): outputs marked current with `snakemake --touch` after adding the `composition:` config block; the Phase 6 rules then run through Snakemake.**
- **What changed.** The only change to `config/params.yaml` is the new `composition:` block (checked with `git diff 7ecd0a1 -- config/params.yaml`). It is read only by `src/normalise/composition*.py`, `family_diag.py` and `src/viz/fig1_decomposition.py` (checked with `grep`). So, as in DEC-108, every Phase 2–5 output and the pre-gate branch (`pregate_mde`, `pregate_report`) were marked current rather than rebuilt.
- **What ran through Snakemake.** `composition_tables`, `fig1` and `composition_report` were then run with Snakemake's own commands. The regenerated report is byte-identical to the one built by hand.
- **`family_diag` was run by hand** (twice: before and after DEC-133), with the same command as its rule. It was then marked current after `composition_tables` rewrote its input with identical content: the tables are seeded, so the content is the same.
- **Result.** `snakemake -n pregate` reports nothing to do. Logs: `data/interim/logs/snakemake_phase6_*.log`.

## 2026-09-30: Phase 6 review (Reenu). Sign audit of every registered decision rule, BEFORE Phase 7 computes anything

**DEC-135: How every registered decision rule is read (clarifications of the registered plan, `6e24eca`; listed with the deviations in the final report). Committed and pushed before any Phase 7 estimate exists.**

Reenu accepted DEC-127 (H4 read as improvements). She asked for every registered rule in plan §5 to be audited for the same kind of ambiguity. The convention below applies to all of them. Where a rule was already unambiguous, it says so. None of the readings uses a result: no Phase 7 quantity has been computed.

- **Convention for every effect.** An effect is treated minus counterfactual, on log concentration. **Negative = a reduction.** A "larger reduction" or "larger effect" means a more negative log effect. Percentages are 100 × (e^β − 1), so a reduction prints as a negative %.
- **H1.**
  - *(a) Unambiguous:* the primary SDID ATT < 0, with its 95% CI entirely below 0.
  - *(b) and (c):* no sign involved.
  - *(d) "keeps its sign":* the point estimate is also < 0 in Callaway & Sant'Anna, in the area-weighted outcome and in V6.GL.03. Significance is not required there.
- **Equivalence test.** Registered exactly as written: the 90% CI lies strictly between ln 0.95 = −0.0513 and ln 1.05 = +0.0488. The bounds are slightly asymmetric in log units, and they are kept as registered, not symmetrised.
- **"Which effect sizes the 95% CI excludes" against NCAP's targets.** A 20%, 30% or 40% reduction is ln 0.80, ln 0.70, ln 0.60. The CI "excludes a 20% reduction" if its lower bound is above ln 0.80. PM2.5 results are never read as PM10 attainment.
- **H2.** "In the direction of a larger winter reduction" = the winter-minus-non-winter difference in log ATTs is **negative**, with its 95% CI entirely below 0. The plan's MDE table already labels this difference "winter minus non-winter".
- **H3: the same ambiguity as H4.** Read literally, "the PM10 effect exceeds the PM2.5 effect", with both effects reductions (negative), would mean a *smaller* PM10 reduction, the opposite of the hypothesis ("PM10 fell more than PM2.5"). Read as:
  - (i) the effect on log(PM2.5/PM10) is **positive** with its 95% CI entirely above 0. This is the ratio rising; the rule is unambiguous here.
  - (ii) in ≥ 2 of the 3 specifications (raw, deweathered, balanced panel), β_PM10 < β_PM2.5 (a larger PM10 reduction) **and** β_PM10 < 0. The hypothesis says PM10 *fell*, so a PM10 increase that is merely smaller than PM2.5's does not count. This is the stricter of the two possible readings. Point estimates only, as registered.
  - (iii) "Layer A is not in the opposite direction" = the registered layer comparison for PM2.5 (Layer A restricted to units with Layer B stations, against Layer B's PM2.5 effect) is not classified **conflict** (below).
  - Otherwise "inconclusive"; never "confirmed".
- **H4.** DEC-127: H4 = reported fall − corrected fall = change(panel, deweathered) − change(all stations, raw). Supported if the mean is > 0 with its 95% CI entirely above 0.
- **H5.** Unambiguous given the coding, now fixed:
  - the IGP indicator is 1 for IGP units;
  - its coefficient = the effect in IGP units minus the effect elsewhere, on log ATTs;
  - "above 0 (a less negative effect)" = the 95% credible interval entirely above 0, i.e. smaller reductions in the IGP.
- **Robustness "agrees".** The check's point estimate has the same sign as the primary point estimate and lies inside the primary 95% CI, on the same scale: log-scale checks against the log-scale primary, the µg/m³ outcome against the µg/m³ fit. Every check is reported either way.
- **Calibration-leakage warning.** Unambiguous: difference = gained − not gained; "negative" = a larger reduction in the units that gained a monitor.
- **Layer-disagreement categories: they overlap and leave a gap, so they need an order.** "Sign" = sign of the point estimates. Applied in this order, first match wins:
  1. **uninformative:** the Layer B 95% CI contains both 0 and the Layer A point estimate;
  2. **conflict:** opposite signs, and at least one 95% CI excludes 0;
  3. **consistent:** same sign, and the 95% CIs overlap;
  4. **different magnitude:** same sign, and the CIs do not overlap;
  5. **unclassified (not in the plan):** opposite signs, neither CI excludes 0, and the Layer B CI does not contain the Layer A estimate. Reported under that name.

  Why this order: "uninformative" is the more precise statement whenever it applies. Putting it first can only increase the number of pairs that trigger the registered investigation, because every category except "consistent" triggers it, including category 5.
- **City-level claims.** Benjamini–Hochberg at 5% on two-sided p-values.

**DEC-136: Phase 6 review rulings (Reenu, 2026-10-01). The "weather" part of H4 and figure 1 is split into modelled weather and unmodelled change (added description; the registered H4 test is unchanged). Written and committed before the split is computed.**
- **Accepted:**
  - DEC-127 (H4 read as improvements), with the audit in DEC-135 and an OSF clarification draft (`docs/osf/clarification_2026-10-01.md`, for Reenu to post);
  - DEC-133, with the failed log-scale version kept in the outputs.
- **The split.** Raw − deweathered contains change the model does not reproduce (DEC-133), so "weather" must mean only modelled weather.
  - Per station-year, a **fitted annual mean** = the mean over the same valid days of exp(fitted log value) × the series' smearing factor: the model's own prediction under the actual weather, on the scale of the deweathered value (DEC-101).
  - At city level, over the same station sets as before:
    - **unmodelled** = change(all, raw) − change(all, fitted): what neither the trend nor the weather terms reproduce;
    - **weather** = change(all, fitted) − change(all, deweathered): *modelled weather only*;
    - composition and corrected are unchanged.
  - reported = unmodelled + weather + composition + corrected (exact).
  - In H4 terms: H4 = h4_unmodelled + h4_weather + h4_composition. **H4's value and its test do not change**; only its description does.
- **Where the split is not available: completeness 60%.** Days with 15–17 valid hours are not fit days, so they have no fitted value. A city-year whose station-years lack a fitted mean keeps the combined raw − deweathered part, labelled as combined. Every other version has fitted values on all its valid days: q1_t90 and the 3-of-4 rule select subsets of the fit days. No-deweathering: fitted = raw, so both parts are 0.
- **Scope, stated wherever H4 appears (Reenu).** H4 covers the NCAP cities with a station valid in every year 2018–2025: 18 for PM2.5 and 13 for PM10 under the primary settings, mostly single stations. It is not a statement about NCAP cities in general. The counts in the text are generated.
- **No claims about individual weather variables anywhere (Reenu).**
  - The per-variable outputs of the family diagnostic stay in `data/processed/composition/family_diag_*.csv` for the record.
  - The report and figures make no statement about which variable drove anything.
  - The family diagnostic is reported only as modelled weather (all variables together) and misfit.

**DEC-137: Results of the DEC-136 split (rule committed in `86e62c7` before computing). Phase 6 closes.**
- **H4 is unchanged** in every version: all 62 rows (31 versions × 2 pollutants) are identical in mean, CI and verdict before and after the split (checked programmatically).
- **Primary (GAM) split of H4.** Scope: the 18 and 13 NCAP cities with a station valid every year 2018–2025.

  | | H4 | unmodelled change | modelled weather | composition |
  |---|---|---|---|---|
  | PM2.5 | +9.5 pp | +0.8 | +2.9 | +5.8 |
  | PM10 | +6.0 pp | −0.5 | +5.4 | +1.0 |

  - LightGBM: unmodelled +0.5 and +0.2.
  - So on average the old combined "weather" part was mostly modelled weather.
- **One version where it is not: the GAM with the 2019 baseline.**
  - The raw − deweathered part is almost all unmodelled change (PM2.5 +4.8, PM10 +5.7 pp; modelled weather ≈ 0). LightGBM's is not (unmodelled +0.6 and +0.4).
  - This is consistent with the lockdown smear that DEC-122 found falling on 2019; the mechanism is untested. It is reported, and it feeds Phase 7's added without-2019 Layer B check (DEC-123).
- **Not split:** completeness 60%, where fitted values are missing on the 15–17-hour days. The combined raw − deweathered part is shown, as DEC-136 states.
- **Family diagnostic (two-way: modelled weather vs misfit):** misfit is the larger part of the GAM–LightGBM gap in 8 of the 13 flagged city-pollutants.
- **Workflow:**
  - `composition_tables` now also writes `station_year_fitted.parquet` and depends on the Phase 5 fits;
  - it, `fig1` and `composition_report` ran through Snakemake (the report was byte-identical to the hand-built one);
  - `family_diag` was marked current, as in DEC-134 (its inputs were rewritten with the same seeded content);
  - `snakemake -n pregate` reports nothing to do;
  - 174 tests pass.

## 2026-10-01: Phase 7 (causal analysis, RQ3). Rules written BEFORE any Phase 7 estimate

The gate is open (plan `6e24eca`, OSF https://osf.io/jksne/). The registered plan (§2, §4, §5) and the sign readings of DEC-135 bind. Everything below fills a gap the plan leaves open, for Part A (satellite, H1/H2) **and** Part B (ground, triangulation, the robustness battery). All of it is committed and pushed before any Phase 7 quantity is computed, so no Part B choice can depend on a Part A result. Any later change will be a dated deviation with its reason.

**DEC-138 (environment, no analysis change): CRAN's Windows binaries of Matrix, RcppArmadillo and RcppEigen replace conda-forge's builds of the same versions; HonestDiD 0.2.8 is installed.**
- **What happened.** Installing HonestDiD (DEC-097) failed because `library(Matrix)` (conda-forge build 1.7.6) stopped with "Mingw-w64 runtime failure: 32 bit pseudo relocation … out of range" on every load, taking `did` and `mgcv` with it. `did` had loaded normally earlier the same session, so the DLL layout can change within a boot, not only between boots as DEC-093 assumed. Nothing in the R library had changed (folder timestamps checked).
- **Test, under the failing layout.** CRAN's binary of the same Matrix version (1.7-6, 2026-09-25 snapshot), in a throwaway library, loaded 3 of 3 times, with `did` and `mgcv` loading through it. With it in place, every one of the 46 compiled packages in the environment was loaded once: only RcppArmadillo (15.6.0-1) and RcppEigen (0.3.4.0.2) failed, and CRAN's binaries of the same versions loaded.
- **Change.** `workflow/scripts/install_r_extra.R` installs these three CRAN binaries into the environment's library on Windows only, before anything loads Matrix, with a stamp file so it is idempotent. Same versions, so no code changes; `conda-lock.yml` is unchanged (conda's files are overwritten on Windows). It then installs HonestDiD 0.2.8 and its 24 dependencies from the same snapshot. After the change all 63 compiled packages load under the failing layout, and the R environment tests (now including a HonestDiD test on its bundled example) passed 3 of 3 runs.
- **CI (Linux)** skips HonestDiD (`NCAP_SKIP_HONESTDID=1`): its dependencies would build from source against GLPK and GMP. Its test skips when the package is absent. The Linux build is unaffected by the Windows DLL problem.

**DEC-139: Layer A primary SDID, implemented exactly as plan §5 item 1.**
- **Units and roles** are read from the gate-time file `data/interim/pregate/units.csv` (113 treated, 923 controls; cohorts 89 / 15 / 9), never recomputed.
- **Outcome:** log of the population-weighted ACAG V5.GL.06 annual mean, 2010–2024. **2020 is removed before any estimation.** The panel must be complete (asserted).
- **Per cohort g:** `synthdid_estimate` with default settings (as in Phase 4) on the matrix of all 923 controls plus cohort g's treated units, over 2010–2024 without 2020; T0 = the number of those years before g. Cohort 2020 therefore has pre-years 2010–2019 and post-years 2021–2024.
- **Aggregate ATT** = Σ_g N_g · ATT_g / Σ_g N_g.
- **Joint placebo SE** (500 replications; the draws are made in the master process from the config seed, so results do not depend on the number of workers): each replication draws 113 distinct controls and partitions them into disjoint sets of the cohorts' sizes. Each set gets its cohort's adoption year and is estimated against the controls not drawn in that replication; the aggregate is formed as for the real data. SE = SD of the 500 placebo aggregates. 95% CI = ATT ± 1.96 SE; 90% CI = ATT ± 1.645 SE (equivalence).
- **The same draws serve every outcome** (log annual, µg/m³ annual, log winter, log non-winter) and the calibration-leakage split (DEC-146): each replication's 113 controls are partitioned into the six (leakage group × cohort) cells, and a cohort's set is the union of its two cells.
- **Placebo in space** (plan's "500 permutations") = the equal-tailed permutation p of the primary ATT against these 500 placebo aggregates, computed as in Phase 4 (DEC-091). These are the same draws as the SE, not a separate run.
- **Effects** follow DEC-135: treated − counterfactual, natural-log units; % = 100 × (e^β − 1). The µg/m³ fit is secondary.

**DEC-140: Seasonal outcomes for H2.**
- ACAG V5.GL.06 monthly, population-weighted (`unit_month_sat`). Winter season-year t = October t to February t+1; non-winter t = March to September t. A season's value is the mean of its monthly means, and it needs every month.
- **Season-years 2010–2023 for both seasons.** Winter 2024 would need February 2025, which the product does not have. Non-winter is restricted to the same season-years, as in Phase 4 (DEC-087).
- **Season-year 2020 is dropped for both seasons.** Non-winter 2020 holds the national lockdown; dropping the same season-year from both keeps winter minus non-winter like with like.
- **Post = season-year ≥ the cohort year.** For cohort 2019, winter 2018 (October 2018 to February 2019) counts as pre, as plan §4 implies ("winter 2019 is the first fully after launch"). The two months of it after launch can only pull the estimate towards zero.
- **H2** = ATT_winter − ATT_non-winter, with its SE from the per-replication differences of the same joint-placebo draws. Supported if the 95% CI lies entirely below 0 (DEC-135). Tested only if H1 is supported; otherwise reported as exploratory.

**DEC-141: The H1 verdict, every branch fixed in advance** (rules from plan §5, read as in DEC-135).
- (a) primary ATT < 0 and its 95% CI entirely below 0;
- (b) event-study pre-period coefficients −9 to −2 jointly insignificant: Wald p > 0.10 (DEC-142);
- (c) the 2016 placebo-in-time 95% CI includes 0 (DEC-145);
- (d) point estimate < 0 in Callaway & Sant'Anna (simple aggregation, never-treated controls), in SDID on the area-weighted outcome and in SDID on V6.GL.03 (each with the primary design otherwise).
- **Verdict, first match wins:**
  1. (b) or (c) fails → **"not identified by this design"**, whatever the ATT. If (b) fails, the HonestDiD bounds are reported alongside and do not overturn it.
  2. the 95% CI excludes 0 and ATT < 0: if (d) holds → **"H1 supported"**; otherwise → **"H1 not supported: the sign is not robust"** (naming the specification that flips).
  3. the 95% CI excludes 0 and ATT > 0 → **"H1 not supported: the estimate is an increase"**.
  4. the 95% CI includes 0 → **"no detectable effect"** (never "no effect"), with the equivalence test: if the 90% CI lies strictly between ln 0.95 and ln 1.05, "effects of 5% or larger in either direction are ruled out"; otherwise "inconclusive".
- **Always reported:** the 90% CI and the equivalence result; whether the 95% CI excludes a 20%, 30% and 40% reduction (ln 0.80, 0.70, 0.60; DEC-135), with the statement that a PM2.5 result says nothing directly about PM10 attainment; the MDE (1.2%); the calibration-leakage result beside H1.

**DEC-142: Event study (Sun & Abraham), plan §5 item 2.**
- **Sample:** the 113 treated and 923 never-treated units, 2010–2024 without 2020 (primary); outcome as in DEC-139.
- **Regressors:** cohort-specific relative-year indicators 1{cohort = e} · 1{t − e = l} for every observed l except the reference. The reference is l = −1 for cohorts 2019 and 2020. For cohort 2021, l = −1 is 2020, which is dropped, so its reference is l = −2 (2019), the last observed pre-year; `did` makes the same choice for this panel (checked on synthetic data). Relative years outside −9 to +5 (cohort 2020: −10; cohort 2021: −11, −10) get their own indicators, so they are not pooled into −9, and are not reported (Sun & Abraham advise against binning).
- **Fixed effects:** unit, and region × year (the 4 regions of DEC-075).
- **ERA5 covariates** (unit-year): annual means of 2 m temperature, relative humidity (from monthly-mean temperature and dew point, Magnus formula as DEC-100), 10 m wind speed (the speed of the monthly-mean wind vector: the monthly-means download has no scalar speed, a stated limitation), boundary-layer height and solar radiation (SSRD), and annual total precipitation. Each is the area-weighted mean of the 0.25° ERA5 cells over the unit's polygon (exact coverage fractions, exactextract), the same for treated and control units. Entered linearly. No claim is made about any individual covariate (DEC-136).
- **Estimation:** pyfixest OLS, SEs clustered by unit (CRV1, pyfixest's default small-sample adjustment).
- **Aggregation (interaction-weighted):** δ_l = Σ_e w_{e,l} δ_{e,l}, with w_{e,l} the share of cohort e among treated units in cohorts that have an estimated δ_{e,l} (a cohort is not counted at its own reference period). The covariance of the aggregated coefficients comes from the delta method on the clustered covariance, with the weights treated as fixed.
- **Rule (b):** the Wald χ² test (8 df) of the aggregated δ_{−9} … δ_{−2} = 0 with their aggregated covariance; (b) holds if p > 0.10.
- **Average post-period effect** = the mean of δ_0 … δ_5, with its delta-method SE; reported, and used as the event study's comparison number.
- **The 2020 coefficient, shown separately:** a second fit includes 2020. There, a treated unit's 2020 observation gets a cohort-specific "2020" indicator instead of its relative-year indicator; cohort 2021 keeps l = −2 as its reference. The cohort-share-weighted 2020 coefficient is shown on its own in figure 4, and this fit's relative-year coefficients are the "2020 included; own coefficient" event-study sensitivity.

**DEC-143: HonestDiD (Rambachan & Roth), plan §5 item 2 and DEC-097.**
- **Inputs:** the aggregated δ at l = −9 … −2 (8 pre-periods) and 0 … +5 (6 post-periods) and their aggregated covariance; the target is the average post-period effect (weights 1/6 on each post-period).
- **Relative magnitudes:** M̄ = 0, 0.5, 1, 1.5, 2 (the package's default method, C-LF). **Smoothness:** 6 values of M evenly spaced from 0 to twice the largest SE among the pre-period coefficients ("0 to that value in 5 equal steps"), the package's default method (FLCI). The original (unrestricted) CI is shown beside them.
- **Breakdown value:** the largest M̄ at which the relative-magnitudes robust 95% CI excludes 0. It is found by bisection to 0.01 between the grid points that bracket the change, because the robust CI widens as M̄ grows. Reported as "none" if the CI includes 0 at M̄ = 0, and as "> 5" if it still excludes 0 at M̄ = 5.

**DEC-144: Callaway & Sant'Anna, plan §5 item 3.**
- R `did` 2.5.1 `att_gt` on the primary panel (2010–2024 without 2020). With that gap, `did` uses 2019 as the base year of cohorts 2020 and 2021, which a synthetic check confirmed against a hand-computed DiD.
- Settings: gname = listing cohort (0 for never-treated), est_method = "dr" (as registered), xformla = ~1, base_period = "varying" (the package default), bootstrap with uniform bands (biters = 1,000), clustered by unit, config seed. **The registered text names no covariates, so none are added; without covariates the doubly robust estimator is the unconditional DiD.** Stated in the report.
- Never-treated controls are primary; not-yet-treated is the sensitivity check.
- Simple aggregation (rule d uses its point estimate) and dynamic aggregation over e = −9 … +5, with uniform 95% bands (shown in figure 4).

**DEC-145: The 2016 placebo in time (rule c).**
- Data 2010–2018 only, read through Phase 4's pre-period reader (it filters to year ≤ 2018 and asserts it).
- The real 113 treated units get a simultaneous fake adoption in 2016 (every real cohort adopts after 2018, so there are no cohorts to keep); SDID against all 923 controls.
- **SE from 500 random control sets of 113** given fake adoption in 2016 against the remaining controls. That is the same kind of null as the primary's joint placebo, so (c) is judged on the primary's SE design. 95% CI = ATT ± 1.96 SE; (c) holds if it includes 0. The region-matched null (as in Phase 4) is reported beside it for information and is not used for the rule.

**DEC-146: Calibration-leakage split, as registered (DEC-096).**
- Groups from `data/interim/pregate/monitor_gain.csv`: gained 74 (cohorts 61 / 7 / 6), not gained 39 (28 / 8 / 3). Both are ≥ 10 units, so both are estimated.
- Each group: per-cohort SDID with all 923 controls, aggregated by cohort size within the group, 2020 dropped.
- SEs for each group and for the difference (gained − not gained) come from the primary's joint-placebo replications (DEC-139), with disjoint cells of the six group × cohort sizes.
- The warning rule is as registered: the gained group's ATT < 0 with its 95% CI excluding 0 while the not-gained CI includes 0, **or** the difference < 0 with its 95% CI excluding 0. Reported beside H1 as a warning, not proof.

**DEC-147: Layer A robustness checks: definitions.** Every SDID check uses the primary design except for the one change named, and gets its own 500-replication joint-placebo SE, drawn from its own control pool. "Agrees" follows DEC-135: same sign as the primary and the point estimate inside the primary's 95% CI, log scale.
1. **V6.GL.03** (population-weighted, annual). Also rule (d).
2. **V6.GL.02.04** (vintage): 2010–2023, so its post-period ends in 2023.
3. **Area-weighted** V5.GL.06 mean. Also rule (d).
4. **Towns without a GHSL centre included** as 1.87 km buffers: the 10 buffered towns join as treated units with their listing cohorts (123 treated).
5. **Patancheruvu excluded:** the primary has no Patancheruvu unit (its point lies inside the Hyderabad centre, which is treated on Hyderabad's own listing), so the primary is unchanged by construction and is reported as such. The check is run on version 4, without Patancheruvu's buffer.
6. **Asansol centre alone:** the unit's value is replaced by the population-weighted V5.GL.06 mean over UCDB centre 11080 alone, computed in this phase with Phase 3's zonal code (`src/clean/zonal.py`); nothing else changes.
7. **Treated units ≥ 100k** (2015 population): drops 4 treated units.
8. **Spillover:** only controls ≥ 25 km from every NCAP place (754).
9. **First-funding cohorts** (units: 2020: 86, 2021: 25, 2022: 2).
10. **Anticipation:** units holding any of the 94 cities on CPCB's 2017 list are treated from 2018; the others keep their listing cohort.
11. **2020 included** as an ordinary year. The cohort-size-weighted 2020 value of SDID's per-period effect curve (cohorts 2019 and 2020) is reported as its own coefficient.
12. **Exclude the IGP:** treated and control units in the IGP region are both removed.
13. **Himalayan region split:** Himalayan = a non-north-east centre in Jammu & Kashmir, Ladakh or Himachal Pradesh, or in an IGP state with mean elevation ≥ 350 m (the complement of DEC-075's plains rule within those states). The split changes only the region × year effects, so it applies to the event study (5 regions); SDID has no region term, so it is not applicable there. Its comparison number is the event study's average post-period effect, set against the primary SDID as the rule requires, with the 4-region event study beside it.
14. **Callaway & Sant'Anna with not-yet-treated controls** (DEC-144).
15. **Leave-one-out donors:** every control with SDID unit weight > 0 in any cohort's primary fit is dropped in turn, and the aggregate is re-estimated (point estimates only). Reported: the range, the share that "agree", and the donor whose removal moves the ATT most.
16. **Placebo in space** = DEC-139's permutation p. **Placebo in time** = rule (c), DEC-145. **HonestDiD** = DEC-143.
17. **VIIRS fire covariate: not run.** FIRMS has not been downloaded (DEC-039; cut item 4). It is listed as not run, with the reason, until Reenu supplies the data; it is not substituted.
18. **Raw MAIAC AOD: not run** (registered as "if time allows"; not downloaded).

**DEC-148: Layer B (ground) estimators, plan §5 item 4.**
- **Stations and panels:** Phase 6's selection code (`src/normalise/composition.py`), so a Layer B version and the H4 version with the same settings use the same stations. Stations inside the unit polygon (DEC-105), strict balanced panel valid every year from the baseline to 2025 (DEC-125), city-year = the mean of the panel stations' annual means. **Primary version** = H4's: GAM, seasonal resampling, primary validity rule, baseline 2018, completeness q1_t75. Deweathered values exclude each station's unmodelled change by construction (DEC-136); stated beside every Layer B result.
- **Treated cities** = NCAP units with a panel, including a buffered town if a station is inside it (DEC-125); cohort = the unit's listing cohort. **Control stations** = panel stations inside control-pool units (role = control), so Satna's unit (a control) can enter.
- **ITS, per city c** (deweathered, log): β_c = mean of log y_ct over post-years (t ≥ g_c) − mean over pre-years (baseline ≤ t < g_c), 2020 excluded from both. With the 2018 baseline, cohort 2019 has one pre-year, so this is the registered before–after contrast; no pre-trend can be fitted. Pooled ITS = the unweighted mean of β_c over cities; 95% CI from a cluster bootstrap over cities (1,000 resamples, percentile, config seed).
- **Ground DiD:** for each treated cohort g, OLS on station-years of cohort-g treated stations plus all control stations: log y_st = α_s + λ_t + β_g · 1{treated} · 1{t ≥ g}, baseline to 2025 without 2020. A cohort is compared only with never-treated controls, which avoids staggered-adoption bias. Aggregate β = Σ_g n_g β_g / Σ_g n_g, n_g = treated cities in cohort g. Observations are stations, as registered ("NCAP vs non-NCAP stations"). 95% CI from a cluster bootstrap over cities (1,000), **stratified by treated cohort and control**, so every draw keeps both groups. A stratum with one city contributes no between-city variance, and the report says where that happens.
- **Added before computing (labelled as such):** the same DiD on city means (each city's panel mean is one observation), because one city (New Delhi, 23 of 41 treated PM2.5 panel stations at the 2018 baseline) dominates the station-level version.
- **2020, sensitivity "included; own coefficient":** a treated × 2020 indicator (DiD) or a 2020 term (ITS). The β is then identical to the primary by construction; the 2020 coefficient itself is reported.
- PM2.5 and PM10 are estimated separately; never pooled. **Scope line wherever a Layer B result appears:** cities, stations, and how many panels hold one station (DEC-136). Every Layer B result is secondary (plan §1) and carries the one-pre-year limitation. The audit's missingness bias (median +0.7%, `audit_report.md`) is stated beside it.
- City-level ITS values are shown descriptively. No unshrunk city-level claim is made in Phase 7: city claims come from Phase 8's shrunken estimates, or are held to Benjamini–Hochberg 5% (plan §5).

**DEC-149: Layer B robustness checks** (each for ITS and DiD, PM2.5 and PM10; "agrees" against the Layer B primary of the same estimator and pollutant, DEC-135):
- **deweathering:** LightGBM (the other family); none (raw panel means, the proposal's "no-normalisation baseline"); GAM with Grange & Carslaw resampling (DEC-109's sensitivity);
- **as registered, no deviations:** GAM k = 4/yr, Grange & Carslaw, registered flags only (as in H4, DEC-128); and registered flags only with the primary GAM;
- **post-hoc, "added after inspecting the data" (DEC-124):** each registered-flags version again without site_1433;
- **baseline 2019; completeness 60% and 90%, and 3 of 4 quarter-hours; without the 5 Reenu-decided stations; without station-years with reliability < 50.** A version with no treated city holding a panel is reported as not computable;
- **without 2019 (DEC-123, added 2026-09-28):** post-years 2021–2025 under the 2018 baseline, for the GAM and LightGBM. **The DEC-137 follow-up:** per year, the mean over the Layer B panel stations of log(raw / fitted) for each family, at both baselines; and the GAM − LightGBM ITS gap with and without 2019 and at the 2019 baseline. This is reported descriptively; no threshold was set, so no claim is made beyond the numbers;
- **2020 included, own coefficient** (DEC-148);
- **FY2025-26 (+ January–March 2026): not computable.** No deweathered values exist after 2025-12-31 (DEC-079/128).

**DEC-150: Triangulation and figure 1's policy step.**
- **Layer A restricted** (plan §5): the primary SDID design with only the treated units that have a Layer B PM2.5 panel, all 923 controls, and a joint-placebo SE (500) with sets of the same cohort sizes. Buffered towns are not Layer A units, so they cannot enter.
- **Two pairs are classified** with DEC-135's ordered categories: Layer A restricted against the PM2.5 ground DiD (the like-for-like pair, both treated-vs-control contrasts) and against the PM2.5 ITS. The windows differ (satellite post-years 2019 and 2021–2024; ground 2019 and 2021–2025); this is stated, not adjusted.
- **H3 (iii) (Phase 8)** is met only if neither pair is "conflict".
- **The registered investigation**, run for every pair not classified "consistent", with each step reported whether or not it closes the gap:
  1. network composition: ITS and DiD on the all-station city series instead of the panel;
  2. calibration: Layer A restricted on V6.GL.02.04 (to 2023) against V5.GL.06, and the yearly correlation between ground panel means and the satellite over the same cities (Phase 6 trends);
  3. spatial coverage: the ITS of the satellite value at the panel stations' own 0.01° cells (`station_year_sat`) against the population-weighted polygon value, same cities, 2018–2024;
  4. deweathering: Layer B on raw against deweathered values.
- **Figure 1's policy step (both views fixed now):**
  - *PM2.5 (pooled view):* the Layer A restricted ATT (the H4 PM2.5 cities are exactly the units with a 2018 PM2.5 panel), as % with its 95% CI, drawn from the corrected level. A last bar, "remaining change" = corrected − policy, is the part of the corrected change not attributed to NCAP. The figure states that the time bases differ (ground endpoints 2018 → 2025; satellite average effect over 2019 and 2021–2024).
  - *PM10 (pooled view):* there is no satellite PM10, so the policy step is the ground DiD for PM10, labelled "Layer B, secondary, one pre-year".
  - *Per-city view:* the policy step stays a placeholder, "city effects: Phase 8 (shrunken)", because unshrunk city claims are not made (plan §5).

## 2026-10-01: Phase 7 Part A results (rules DEC-138 to DEC-150, committed and pushed in `eebaecc` before computing)

Numbers from `docs/causal_report.md` (generated). No specification was changed after any estimate was seen. Two implementation fixes were made before the outputs they affect were first produced; both are recorded in DEC-152.

**DEC-151: H1 is "not identified by this design": the registered pre-trend test (rule b) fails. Every Layer A estimate is an increase, not a reduction. H2 is not tested.**
- **Rules, as registered and read in DEC-135/141:**
  - (a) **not met:** primary SDID ATT = +0.0352 (+3.6%), 95% CI +2.4% to +4.8%. This is an increase relative to the synthetic counterfactual. By cohort: 2019 +3.9%, 2020 +2.0%, 2021 +3.3%. In µg/m³: +1.88 (+1.19 to +2.57).
  - (b) **failed:** the Sun & Abraham pre-period coefficients −9 … −2 are jointly significant (Wald χ² = 26.8, 8 df, p = 0.0008). The individual pre-coefficients are small (−1.6% to +0.8%). The satellite series is smooth, so their SEs are 0.5–0.8%, and l = −7 alone has z ≈ −3.1.
  - (c) **met:** the 2016 placebo is −0.1% (95% CI −0.9% to +0.7%).
  - (d) **not met:** Callaway & Sant'Anna +4.6%, area-weighted +3.5%, V6.GL.03 +3.2%; all positive.
- **Verdict (first branch of DEC-141):** "not identified by this design (failed: (b) pre-trend Wald test)". Even setting (b) aside, branch 3 would give "not supported: the estimate is an increase".
- **HonestDiD, reported alongside as registered:**
  - The original CI of the average post-period effect lies above 0 (+1.7% to +4.5%).
  - The relative-magnitudes breakdown is M̄ = 0.20. The robust CI keeps excluding 0 only if post-period violations of parallel trends are at most a fifth of the largest pre-period one.
  - Smoothness bounds include 0 from the first M > 0.
  - Package warnings are kept with each row: the relative-magnitudes CIs are open at the grid edge from M̄ = 1; the smoothness solver flags every row as possibly inaccurate.
- **Always reported:**
  - Equivalence: the 90% CI (+2.6% to +4.6%) lies inside ±5%.
  - The 95% CI excludes a 20%, 30% and 40% reduction (PM2.5, not PM10).
  - The MDE is 1.2% (2.8 × the real design's SE = 1.6%).
  - Placebo in space: permutation p = 0.004, the minimum possible with 500 replications.
- **H2: not tested** (H1 not supported). Exploratory: winter +2.9%, non-winter +2.8%, difference +0.1% (−1.3% to +1.4%).
- **Calibration leakage (registered warning rule): fires, on its second clause.**
  - Gained a monitor (74 units): +2.5% (+1.1% to +4.0%).
  - Did not (39): +5.5% (+3.5% to +7.5%).
  - Difference: −2.8% (−5.1% to −0.5%).
  - Both groups are increases. The direction is the one leakage would produce, but the comparison cannot separate it from real differences between the groups. The report says so.
- **Checks made before accepting the numbers** (implementation only; nothing was re-specified):
  - **Event study:** 1,036 units × 14 years = 14,504 observations. The aggregated coefficient at l = −9 equals the cohort-share-weighted mean of the cohort coefficients, recomputed by hand. The references are as DEC-142 states.
  - **The positive sign:** an unweighted DiD of means on the same panel gives +5.0% (cohort 2019), +5.8% (2020) and +2.1% (2021). By region, cohort 2019 against same-region controls is positive in the IGP (+4.6%) and peninsular/other (+5.2%), and slightly negative on the coast (−0.7%) and in the north-east (−1.4%). The sign is in the data, not in the estimator.
  - **Callaway & Sant'Anna:** never- and not-yet-treated agree to 4 decimals. The not-yet-treated pool adds only 24 units, and only before 2021; 27 of the 39 group-time cells differ, slightly.
- **Run:** primary 58.5 min (500 replications × 18 fits), V6.GL.03 8.7, area-weighted 9.1, 2016 placebos 2.7 and 3.8 min; HonestDiD 11.5 min. This matches the pre-run estimate (Part A ≈ 1.5–2 h).

**DEC-152: Implementation fixes and checks during Part A (none changes a specification).**
- **The estimand names were made unique per outcome** (`att` = the headline log outcome; `att:<outcome>` for the others). The first version would have summed fit-set ATTs across outcomes under one name. Caught in code review before `summarise` first ran; a regression test was added.
- **`honest.R` records the package warnings with each result row** and states the direction of the original CI. The first run printed the warnings only to the log. The re-run gave identical numbers (checked).
- **Wald test size, checked on synthetic panels** shaped like the real design (100 controls, cohorts 2019 and 2021, 2020 dropped), 40 seeds per design, nothing planted before adoption:
  - with no effects planted, rejection at nominal 10% / 5% was 10.0% / 5.0% (cohorts of 30 and 10 units), 10.0% / 5.0% (30 and 40) and 12.5% / 7.5% (90 and 40);
  - one batch with planted post-period effects gave 20% / 12.5%. Monte Carlo SE ≈ 5 pp at 10%, so that batch is about two SEs high.
  - Read together, the test is not grossly over-sized, so the p = 0.0008 in DEC-151 is not an artefact of it. The unit test checks the algebra and a gross-failure bound, not one draw's p.
- **Figure 4** was re-laid out twice after looking at the render: the header text overlapped the axes, and the legend overlapped the source note. It now states that Callaway & Sant'Anna's pre-listing points are year-on-year differences (base period varying), so the two estimators are like-for-like only after listing.
- **Windows:** a spec id `nul` (a reserved device name) broke a synthetic test's output folder; it was renamed.

**DEC-153 (workflow note): Part A through Snakemake; reproducibility of the re-run.** After adding the `causal:` config block (read only by `src/causal/` Phase 7 modules; `git diff` shows nothing else changed), upstream outputs were marked current with `snakemake --touch`, as in DEC-108/134. So was the 83-minute SDID rule, which had been run by hand with the rule's own command. The seven quick Part A rules (summary, event study, CS, HonestDiD, report, figure 4, target) then ran through Snakemake (log `data/interim/logs/snakemake_phase7_partA.log`), and `snakemake -n causal` has nothing to do.
- **Against the hand-built outputs:** the SDID summary and every Callaway & Sant'Anna file are byte-identical. The event-study coefficients differ by at most 1e-16 (floating-point summation order). HonestDiD's smoothness rows, which the solver already flags as possibly inaccurate, move by up to 9e-6. That changes one cell of the report in the fourth decimal (M = 0 lower bound +0.0040 → +0.0041). No verdict, rule check or headline number changed.

## 2026-10-01: Part A reviewed (Reenu); additions for Part B, written BEFORE Part B computes anything

**DEC-154: Part A review (Reenu). The H1 verdict stands exactly as registered: "not identified by this design". No rule or specification changes because of it. Five additions for Part B.**
1. **Wording.** The positive Layer A estimate is never described as an effect of NCAP. The fixed wording is: *"NCAP units' satellite PM2.5 did not fall relative to comparable units; the estimates point to a relative rise of about 3–5%"*. It always appears next to the "not identified" verdict. This applies to the report, the figures, the phase note and PROGRESS.
2. **Descriptive context, labelled descriptive.**
   - What: the mean annual population-weighted PM2.5 (ACAG V5.GL.06, µg/m³) of the 113 NCAP units and of the 923 control-pool units, 2010–2024, 2020 included. Each is the unweighted mean over units, with a 95% t-interval and the median.
   - Where: a table in `docs/causal_report.md` and a supplementary figure, `reports/figures/figS1_levels` (not one of the proposal's eight).
   - No effect is computed from it.
3. **One exploratory check, "exploratory, added after seeing H1"** (DEC-155).
4. **Calibration leakage.** The report connects the leakage result to the Phase 3/6 finding that new stations read about 6% cleaner (Phase 3 −5.8%; Phase 6 −6.3% raw, −6.8% deweathered; numbers read from the pipeline outputs). It is presented as a possible mechanism the design cannot test.
5. **Environment** (DEC-156): update `conda-lock.yml` for the CRAN builds; confirm CI on the results commit (done: run 36843581029 passed on `655fb65`); at the end, a full rebuild of Phase 7 that confirms Part A's numbers reproduce.

FIRMS: Reenu will try to download it during Part B. If it is not in `data/raw/firms/` when the battery runs, the VIIRS check stays listed as not run (DEC-147 item 17). On 2026-10-01 before Part B it is not there.

**DEC-155 (EXPLORATORY, added after seeing H1, 2026-10-01): SDID restricted to an overlapping range of 2015 population. Not a decision rule; it cannot change the H1 verdict.**
- **Why (Reenu).** City size was the largest pre-registration imbalance: log-population SMD 1.44 (plan §6). The check asks whether the Layer A estimate depends on comparing large NCAP cities with small control towns.
- **Size measure:** log10 of the unit's 2015 population (GHSL UCDB, the pre-treatment epoch used for the control pool).
- **Variant (i), Reenu's example as written: min–max common support.**
  - Keep treated and control units whose log10 population lies in [max(min_T, min_C), min(max_T, max_C)], i.e. 100,050 to 4,593,947.
  - Result: 98 of 113 treated units (cohorts 75 / 15 / 8) and all 923 controls.
  - It drops the 11 treated units above the largest control (the megacity units: Delhi, Kolkata, Mumbai, Bengaluru, Chennai, Hyderabad, Ahmedabad, Pune, Surat, Lucknow, and the Hajipur centre holding Muzaffarpur) and the 4 below 100,000.
  - **It does not improve size balance:** SMD 1.63 against 1.44. The controls are concentrated at 100,000–200,000, so trimming the ends of the range leaves the two distributions different in shape.
- **Variant (ii): overlap of the 5–95% population ranges.**
  - Keep units within [max(P5_T, P5_C), min(P95_T, P95_C)] of log10 population, i.e. 121,197 to 721,889.
  - Result: 42 treated, 704 controls; SMD 0.91.
  - It is shown because variant (i) cannot address the imbalance. Narrower overlaps were checked: P10–P90 leaves 23 treated units, P25–P75 leaves none.
- **How these were chosen.** The variants and their sizes were compared on 2015 population only (counts and SMDs), before any outcome was estimated under any restriction. Neither variant was chosen for its result.
- **Design otherwise the primary's:** V5.GL.06 population-weighted log annual mean, listing cohorts, never-treated controls from the restricted pool, 2020 dropped, 500-replication joint placebo drawn from the restricted pool.
- **Reported** in its own "exploratory" section, never in the registered robustness table.
- *Clarification added 2026-10-02 (Reenu's request; nothing above is changed; see DEC-161):* variant (ii) was written **after seeing variant (i)'s result** on size balance (SMD 1.63 against 1.44, from 2015 population alone), and **before it was run**. Neither restricted SDID had been run when both variants were committed together in `a90213d`. Both stay reported, both labelled exploratory.

**DEC-156: Lock the Windows CRAN builds (Reenu's request on DEC-138).**
- **Change.** On Windows, conda no longer installs `r-matrix`, `r-rcppeigen` or `r-bmisc`, and so not `r-rcpparmadillo`, which only `r-bmisc` requires in the lock. In `environment.yml` these become `# [linux]`, and the lock is re-solved in update mode for those four names only.
- **On Windows,** `install_r_extra.R` installs CRAN's binaries of the same versions from the 2026-09-25 snapshot: Matrix 1.7-6, RcppArmadillo 15.6.0-1, RcppEigen 0.3.4.0.2, BMisc 1.4.10. They are then ordinary pins rather than an overwrite of conda's files, so the stamp files of DEC-138 are no longer needed.
- **Linux is unchanged.** CI needs conda's `r-rcppeigen` headers to build `fastglm` from source.
- **Checks:**
  - the lock diff for linux-64 must be empty, and for win-64 only these four packages removed;
  - the new environment is built under a new name, tested (full `pytest`, every compiled R package loads), and only then replaces `ncap`; the old environment is kept as `ncap_prev` until the end-of-phase rebuild passes.

**DEC-157 (gap found while running; written before any Layer B number was seen): Layer B at the 2019 baseline.** Under DEC-148, a city's pre-years are baseline ≤ t < its cohort year. With the 2019 balanced-panel baseline (registered sensitivity, DEC-088/149), the 2019 cohort has **no pre-year**. The first run stopped with an error on that version before writing any output, so no Layer B estimate had been seen.
- **Rule (the literal reading):** a city or station with no pre-year contributes no contrast and is dropped. A treated cohort with no contrast is dropped from the DiD aggregate.
- **Consequence:** the 2019-baseline versions cover only the cities listed in 2020–2021. With these data that is 1 + 1 PM2.5 cities and 1 PM10 city.
- **How it is reported:** each 2019-baseline row states its coverage. It is not a check on the 2019 cohort, and an "agrees" flag on it means little; the report says so.
- **The DEC-137 follow-up is unaffected:** the per-year misfit table needs no pre-period.
- **Code:** `layer_b.py` skips empty cohorts and marks a version "not computable" when no treated contrast remains. A synthetic test covers it.

## 2026-10-02: Phase 7 Part B results (rules DEC-138 to DEC-150 and DEC-154 to DEC-157, all pushed before the numbers they govern)

Numbers from `docs/causal_report.md` (generated). The H1 verdict is unchanged: "not identified by this design" (DEC-151, confirmed by Reenu, DEC-154).

**DEC-158 (workflow): six EDA outputs declared; CI's DAG check had failed on `5a9d462`.**
- **What failed.** The environment and all tests passed on Linux CI, but `snakemake -n all` failed. Reproduced in a fresh local clone: `pregate_panel` reads `data/interim/eda/station_first_year.csv`, which `src/viz/eda.py` has written since Phase 3 without any rule declaring it.
- **Why only now.** No earlier DAG needed `pregate_panel` in a clean clone, because its committed downstream outputs were present. Phase 7's `causal_panels` needs `pregate/units.csv`, which drags `pregate_panel` in.
- **Fix.** `eda_figures` now declares all six CSVs that `eda.py` writes (`station_first_year`, `entrants`, `ground_vs_satellite`, `seasonal_ground`, `seasonal_satellite`, `city_trends`). The fresh-clone `snakemake -n all` then resolves (80 jobs).
- Same family of problem as DEC-083: only an end-to-end run, or a DAG check on a clean clone, finds it.

**DEC-159: Part B results.**
- **Layer B (secondary; one pre-year; strict 2018 panel, mostly single stations):**
  - *PM2.5* (18 NCAP cities, 16 single-station, against 5 control cities): ITS −14.0% (95% CI −22.7% to −5.3%); ground DiD −4.7% (−13.4% to +4.7%); city-mean DiD −5.1% (−15.9% to +6.7%).
  - *PM10* (13 cities, 11 single-station, against 6 control cities): ITS −5.0% (−11.3% to +1.7%); ground DiD +9.2% (−0.7% to +23.5%); city-mean DiD +12.2% (+1.3% to +26.5%).
  - The 2020 own coefficients (ITS) are −14.2% (PM2.5) and −15.3% (PM10).
- **Triangulation (PM2.5; DEC-135 order):**
  - Layer A restricted to the 18 ground cities: +3.8% (+1.0% to +6.6%).
  - Against the ground DiD (like-for-like): **uninformative**. Against the ITS: **conflict**. The registered investigation ran in full.
  - **Step 3 is the telling one.** Over the same cities and years (2018 → 2024), the ITS of the satellite at the stations' own cells is −11.1%, of the satellite over the polygon −11.2%, and of the ground panel −13.4%. Ground and satellite agree on the before–after fall in these cities. The conflict is between a before–after contrast, which contains the fall shared with every city, and a comparison against comparable units. It is not a disagreement between the two measurements.
  - **Step 2:** the V6.GL.02.04 vintage gives +1.8% (−1.2% to +4.9%) for the restricted set; the yearly ground–satellite correlation across these cities is 0.71–0.85 over 2018–2024.
  - **Steps 1 and 4:** the all-station ITS is −18.6% and the raw ITS −16.1%.
- **Robustness:**
  - **Layer A:** 16 of 18 checks agree; every Layer A estimate is positive. The two that do not agree have the same sign but lie below the primary CI: the V6.GL.02.04 vintage (+1.4%, +0.1% to +2.7%; to 2023) and the version excluding the IGP (+1.9%, +0.7% to +3.1%).
  - **Leave-one-out donors:** all 923 controls have positive weight; the estimate ranges from +0.0349 to +0.0354.
  - **Layer B:** 26 of 32 checks agree for each pollutant. The 2019-baseline rows cover only the cities listed in 2020–21 (2 for PM2.5, 1 for PM10; DEC-157).
  - **Not run:** VIIRS fire (FIRMS still not downloaded at the time of the battery) and MAIAC AOD.
- **Descriptive (DEC-154):** from 2018 to 2024 the NCAP units' mean fell from 54.8 to 45.6 µg/m³ (−16.8%) and the control pool's from 59.3 to 44.9 (−24.3%). Both fell; the control pool fell more.
- **Exploratory (DEC-155; cannot change H1):** min–max common support +3.7% (+2.5% to +5.0%; SMD 1.63); overlap of the 5–95% ranges +3.0% (+1.2% to +4.9%; SMD 0.91). The relative rise does not depend on comparing megacities with small towns.
- **DEC-123/137 follow-up:**
  - The GAM's fitted annual means sit 3.7% below the observed in 2019 (PM2.5; PM10 3.0%), against 3.3% above them in 2018. LightGBM's misfit is 1.2–1.8% in both years.
  - At the 2019 baseline this misfit sits in the baseline year, which is where DEC-137 found the GAM's raw − deweathered part to be almost all unmodelled change. That is consistent with the lockdown smear landing on 2019; the mechanism itself is still untested.
  - At the 2018 baseline, excluding 2019 barely moves Layer B: ITS PM2.5 −14.0% → −15.0%, and the GAM − LightGBM gap −0.1 → +0.2 pp.

**DEC-160 (workflow): the end-of-phase rebuild in the new environment. Part A reproduces; Part B's SDID outputs were carried over (Reenu's choice, 2026-10-02).**
- **Environment.** `ncap_new`, built from the DEC-156 lock plus `install_r_extra.R`, replaced `ncap` (`conda rename`). The old environment is kept as `ncap_prev`. In the new environment, 199 tests passed before the switch, and the suite was run again after it (`data/interim/logs/pytest_phase7_final.log`).
- **Scope (Reenu chose this over a full ~5 h rebuild).**
  - Rebuilt from their inputs in the new environment: ERA5 covariates, panels, specifications, the five Part A SDID specifications, the event study, Callaway & Sant'Anna, HonestDiD, the descriptive table, Layer B, triangulation, the robustness table, the report and figures 1 (Phase 7 step), 4 and S1. Script: `rebuild_partA.sh`; log `data/interim/logs/phase7_rebuild_newenv.log`; 17:01–18:29.
  - **Carried over from the old environment, not re-run:** the 14 Part B SDID specifications (12 registered, 2 exploratory) and the leave-one-out donors.
  - Why the carry-over is safe: the new environment differs only in the build source of four R packages, at the same versions. The rebuilt specification hashes are identical to the old ones, so the carried-over outputs match the code that would produce them.
- **Result, against copies of every output taken before the rebuild:**
  - 272 of 300 files are byte-identical. That includes every Part A SDID file (real fits, unit weights, all 500 placebo replications of every specification), the panels, the ERA5 covariates, Layer B, triangulation and the summaries.
  - 19 files differ numerically by at most 3.3e-14: event-study coefficients and covariances, CS group-time and dynamic estimates, the HonestDiD rows. Four JSON files differ by at most 1.4e-13 (the Wald statistic), with no non-numeric field changed.
  - The 5 `done.txt` timestamps differ.
  - **`docs/causal_report.md` is unchanged line for line,** and so is every verdict, rule check, category and printed number.
  - Figure PNGs are byte-identical. The SVGs differ only in their embedded date and element ids (DEC-094); the committed SVGs were kept.
- **Snakemake:** the outputs were then marked current with `snakemake --touch causal`, as DEC-108/134/153 did: DEC-158's newly declared EDA outputs otherwise mark everything downstream stale. `snakemake -n causal` and `snakemake -n pregate` report nothing to do.
- **Not done:** a rebuild of Phases 2–6 from raw data in the new environment (several hours, mostly deweathering). It is left for the Phase 10 clean-clone check, as DEC-094 already planned.

## 2026-10-02: Phase 7 housekeeping (Reenu, after approving Phase 7)

**DEC-161: `ncap_prev` removed; DEC-155's order of events made explicit.**
- **Environment.** Part A reproduced exactly in the new `ncap` environment (DEC-160), so the old environment `ncap_prev` was removed (`conda env remove -n ncap_prev`). `conda env list` now shows only `base` and `ncap`.
- **DEC-155 (exploratory size check).** Checked against git: both variants were committed together in `a90213d` (2026-10-01 17:37 IST), before any restricted SDID was run (they ran in Part B, `1433b03`). Variant (ii), the overlap of the 5–95% ranges, was written after seeing variant (i)'s *balance* result (SMD 1.63, computed from 2015 population alone) and before running it. `docs/causal_report.md` §11 (generated by `src/causal/report_part_b.py`) and DEC-155 now say so. DEC-155 gets a dated clarification line; its original text is unchanged. Both variants stay reported and labelled exploratory.

## 2026-10-02: Phase 8 (heterogeneity and mechanism, RQ4). Rules written BEFORE any Phase 8 estimate

The gate is open (plan `6e24eca`, OSF https://osf.io/jksne/). The registered plan §5 (item 5, H3, H5, multiple comparisons, exploratory analyses) and DEC-135's sign readings bind.

**H1 is "not identified by this design" (DEC-151), so nothing estimated in this phase is an effect of NCAP.**
- Every per-unit quantity is called a **city-level relative change**: the unit's satellite PM2.5 after listing, relative to its synthetic comparison.
- The "not identified" caveat travels with every such number, H5 included. This is DEC-154's wording rule, extended by Reenu on 2026-10-02.

Everything below was committed and pushed before any Phase 8 quantity was computed. While writing it, the only data looked at were the XV-FC allocation tables and the unit membership (for DEC-166), never an outcome.

**DEC-162: the city-level estimates and their standard errors (input to the hierarchical model).**
- **One SDID per treated unit.**
  - Each of the 113 treated units alone is the treated set, with its listing cohort, against all 923 controls.
  - Outcome, years and 2020 handling are exactly as in the primary: log population-weighted V5.GL.06, 2010–2024 without 2020 (DEC-139).
  - θ̂_i = that unit's listed-minus-synthetic estimate on log PM2.5.
  - Each unit gets its own synthetic comparison, so θ̂_i is not the unit's share of the cohort estimate. The unweighted mean of the θ̂_i is reported beside the primary ATT for orientation only.
- **SE (primary): the cohort placebo SD.**
  - For each cohort year g (2019, 2020, 2021), every one of the 923 controls in turn is the single fake treated unit, adopting in g, estimated against the other 922.
  - s_g = the SD of those 923 placebo estimates, and s_i = s_g for every unit of cohort g.
  - This is synthdid's own placebo variance for a single treated unit, run over every control instead of a random subset, so it involves no random draws.
- **SE (sensitivity): pre-fit scaled.**
  - r = the SD over pre-years of (unit − its synthetic comparison), using the fit's own unit weights. It measures how closely the synthetic tracked that unit before listing.
  - s_i = SD_j(θ̂_j / r_j) × r_i, over the placebo fits j of the unit's cohort (the normalisation of Abadie et al. 2010).
  - Units that were matched noisily then get larger SEs and shrink more.
- **Product sensitivity:** the same per-unit and placebo fits on V6.GL.03 (rule (d)'s product), used only for H5's sensitivity.
- **Unshrunk p-values (for the FDR count only):**
  - the equal-tailed empirical p of θ̂_i against its cohort's 923 placebo estimates, as in DEC-091;
  - Benjamini–Hochberg at 5% over the 113 (plan §5);
  - **only the count of units passing is reported; no unit is named from unshrunk estimates** (no best/worst table).

**DEC-163: the hierarchical (measurement-error) model, plan §5 item 5.**
- **Model.** θ̂_i ~ Normal(θ_i, s_i²) with s_i known; θ_i = α + Σ_k β_k x_ik + τ z_i, z_i ~ Normal(0, 1) (non-centred). Fitted with PyMC (6.3.1 in the locked env).
- **The registered moderators, coded now** (treated units only):
  - *baseline PM2.5:* the unit's mean of log population-weighted V5.GL.06 over 2010–2018 (pre-NCAP for every cohort), standardised over the 113;
  - *IGP:* 1 if the unit's region (DEC-075) is IGP;
  - *log population:* log of the 2015 GHSL population (the pool's pre-treatment epoch), standardised;
  - *coastal:* 1 if the region is coastal;
  - *funding channel:* 1 if any of the unit's NCAP cities is in the XV-FC (million-plus) channel (`ncap_cities.csv: channel`). The New Delhi unit, which mixes channels, counts as XV-FC.
- **Reference category and correlations.**
  - Regions are mutually exclusive. The registered list names only IGP and coastal, so the reference category is peninsular/other plus north-east together.
  - The correlations among moderators are reported. XV-FC and log population are expected to be strongly correlated (million-plus cities are the large ones), which widens both coefficients.
- **Priors (log scale), fixed now.**
  - α ~ Normal(0, 0.1); each β_k ~ Normal(0, 0.05); τ ~ HalfNormal(0.05).
  - A one-SD (or indicator) moderator difference beyond about ±10% is a priori unlikely, but the data dominate: per-unit SEs are expected to be a few per cent.
  - **Sensitivity:** every prior scale × 5.
- **Sampler:** NUTS, 4 chains, 2,000 tuning and 2,000 draws each, target_accept 0.95, seed from `config/params.yaml`.
- **Convergence rule.**
  - Required: R-hat ≤ 1.01, bulk and tail ESS ≥ 400 for α, every β, τ and every θ_i, and 0 divergences.
  - If it fails: one re-run with target_accept 0.99 and 4,000 draws.
  - If that also fails, the model is reported as not converged and no number from it is used.
- **Intervals:** 95% equal-tailed credible intervals (2.5% and 97.5% quantiles), set explicitly (ArviZ's default is 89%).
- **Reported:**
  - α, every β_k (in log units and as %), τ;
  - the average city-level relative change (mean of θ_i over the 113, per draw);
  - per unit: the posterior mean of θ_i (the **shrunken city-level relative change**), its 95% CrI, P(θ_i < 0), and a 95% rank interval (ranks over the 113 per draw);
  - the count of units whose CrI lies entirely below 0, and entirely above 0;
  - a full per-unit table in **alphabetical** order, never ranked.
- **Stated limitation:** the θ̂_i share donors and regional shocks, so their errors are correlated, but the model treats them as independent. A regional coefficient can therefore carry a shock common to the region's units.

**DEC-164: H5, decided exactly by its registered rule.**
- **What decides:** β_IGP in the primary model of DEC-163: all five registered moderators, cohort placebo SEs, primary priors, V5.GL.06.
  - **The rule is met if its 95% equal-tailed credible interval lies entirely above 0.**
  - Reading (DEC-135): IGP minus the reference category. A positive value means a less negative city-level relative change in the IGP, or here possibly a more positive one.
- **Wording.**
  - The verdict is reported as "the registered rule is met" or "not met".
  - H1 is not identified, so β_IGP is a difference in city-level relative changes between IGP units and reference-region units with the same other moderators. It is **not** a difference in NCAP effects.
  - That caveat sits next to the verdict everywhere.
- **Reported beside it, not deciding:**
  - an IGP-only model (the literal "IGP minus everywhere else");
  - pre-fit-scaled SEs;
  - wide priors;
  - V6.GL.03 per-unit estimates.
  - Phase 7's "exclude the IGP" check is cited as context.

**DEC-165: H3 (PM10 vs PM2.5), decided exactly by its registered rule as read in DEC-135 and DEC-150.**
- **Condition (iii) is already known.**
  - Before this rule was written, DEC-159 classified the PM2.5 pair "Layer A restricted vs ITS" as **conflict**.
  - DEC-150 says (iii) is met only if neither pair is "conflict".
  - So **H3 is "inconclusive" whatever (i) and (ii) show.** The choices below only govern how (i) and (ii) are computed and reported; none of them can change the verdict.
- **Condition (ii), the three specifications.** The registered "raw, deweathered, balanced panel" are read as the three Layer B series of Phase 7's investigation, in the decomposition's order:
  - *raw* = all stations, raw (Phase 7 version `all_stations_raw`);
  - *deweathered* = all stations, deweathered (`all_stations`);
  - *balanced panel* = the Layer B primary (strict 2018 panel, deweathered).
- **Condition (ii), the estimators.** Both Layer B estimators are used:
  - the ITS;
  - the DiD: on city means for the two all-station series, which have no balanced station panel; on stations for the panel, as in Phase 7's primary.
- **Condition (ii), the same cities for both pollutants.**
  - Per specification: the treated cities (and, for the DiD, the control cities) that have both PM2.5 and PM10 in that series.
  - The Phase 7 values, each on its own pollutant's cities, are shown beside them.
- **Condition (ii), when it holds.**
  - For one estimator: in ≥ 2 of the 3 specifications, β_PM10 < β_PM2.5 **and** β_PM10 < 0 (point estimates, DEC-135).
  - **(ii) is met only if it holds for both estimators.** This is the stricter reading, as DEC-135 took for (ii) itself.
- **Condition (i): the ratio.**
  - Stations: those in both the PM2.5 and the PM10 strict 2018 panels (co-located).
  - Station-year value = deweathered PM2.5 / deweathered PM10 (each pollutant was deweathered separately in Phase 5).
  - Phase 7's ITS (city means) and DiD (stations) are applied to the log of that ratio, with the same cluster bootstrap over cities (1,000).
  - **(i) is met only if the effect on log(PM2.5/PM10) is > 0, with its 95% CI entirely above 0, for both estimators.**
  - The raw ratio is reported beside it.
- **Verdict.**
  - "Consistent with dust control" only if (i), (ii) and (iii) all hold; otherwise "inconclusive"; never "confirmed".
  - Every condition is reported whichever way it points, with Layer B's scope line (cities, stations, single-station panels) and the one-pre-year limitation.
  - Ground PM10 is never set against satellite PM2.5 as "agreement".

**DEC-166: Funding dose-response, EXPLORATORY (plan §5; proposal stage 8; cut item 1).**
- **Dose.**
  - The XV Finance Commission's air-quality **allocation** to a million-plus urban agglomeration (UA): FY2020-21 (2020-21 report, Annex 5.3) plus FY2021-26 (2021-26 report, Vol II Annex 7.6), in ₹ crore.
  - It is divided by the UA population printed in Annex 7.6 (millions) and reported as ₹ per person.
  - Allocations are fixed in the Commission's reports before the money flows. So they avoid the performance-linked part of *releases* (DEC-052, DEC-092), though not every reverse-causal path.
- **Units with a dose.**
  - Treated units whose NCAP cities are all in the XV-FC channel and match at least one UA allocation row. With several rows, the unit's dose is Σ allocations / Σ populations.
  - The Mumbai unit (Mumbai, Navi Mumbai, Thane) and the Kolkata unit (Kolkata, Howrah, Barrackpore) take their UA's figure, because the UA covers those members.
  - **Excluded:** the New Delhi unit (Delhi is in the NCAP channel, so the unit mixes channels) and the Badlapur–Ulhasnagar unit (no allocation row of its own).
  - The NCAP-channel cities have no allocation table in the extracted documents (only releases), so they get no dose. Nothing is imputed.
- **Model:** the DEC-163 measurement-error model on those units, with one moderator, the centred log dose.
  - β is reported per doubling of the dose (β × ln 2), with its 95% CrI.
  - Same priors, sampler and convergence rule.
- **Versions reported beside it:**
  - with the IGP indicator added;
  - without the highest-dose unit: Patna's, whose per-person allocation is about twice the next one's. This was chosen from the allocation table alone, before any outcome.
- **Caveats printed with it:**
  - exploratory, not a hypothesis test;
  - H1 is not identified, so this relates **city-level relative changes**, not effects, to money;
  - per-person allocations are set largely state by state (the report shows the within-state spread), so the dose is confounded with state and region;
  - XV-FC releases reward improvement; allocations avoid that link but not, for example, a state's prior pollution entering the formula;
  - it covers the million-plus XV-FC units only.

**DEC-167: Figures 5, 6 and 7, and where Phase 8 lives.**
- **Figure 5** (proposal: "small-multiple maps of city-level effect estimates (posterior means)").
  - Three India maps (DataMeet boundaries) of the 113 units at their representative points:
    - (a) the posterior mean of the shrunken city-level relative change (%), on a diverging palette centred at 0;
    - (b) the width of its 95% CrI (pp);
    - (c) P(θ_i < 0).
  - The title and note say: "city-level relative change, not an effect of NCAP; H1 not identified".
- **Figure 6** (proposal: "posterior distributions of city effects, before and after shrinkage").
  - (a) Each unit's unshrunk θ̂_i ± 1.96 s_i beside its shrunken 95% CrI, units sorted by posterior mean.
  - (b) 95% rank intervals.
  - **No city names on either panel**, so neither reads as a best/worst list. The named estimates are in the report's alphabetical table, shrunken only.
- **Figure 7** (proposal: "PM10 vs PM2.5 effect comparison").
  - (a) β_PM2.5 and β_PM10 with 95% CIs, for each specification × estimator, on the same cities.
  - (b) The effect on log(PM2.5/PM10) with 95% CIs (deweathered and raw, ITS and DiD), with Layer A restricted (PM2.5) shown for reference.
  - Labelled "Layer B, secondary, one pre-year".
- **Code:**
  - `src/hierarchical/`: `unit_sdid.R`, `city_estimates.py`, `pooling.py`, `dose.py`, `mechanism.py`, and `report.py` → `docs/heterogeneity_report.md` (generated);
  - `src/viz/fig5_city_map.py`, `fig6_shrinkage.py`, `fig7_mechanism.py`;
  - real gated rules in `workflow/rules/hierarchical.smk`;
  - synthetic tests in `tests/test_hierarchical.py`.
- **Not in Phase 8's figures:** any per-city ranking or unshrunk city name.

## 2026-10-02: Phase 8 results (rules DEC-162 to DEC-167, pushed in `2f80dc4` before computing)

Numbers from `docs/heterogeneity_report.md` (generated). No rule or specification was changed after any Phase 8 estimate was seen. **H1 is not identified (DEC-151), so every number below is a city-level relative change, not an effect of NCAP.**

**DEC-168: Phase 8 results. H5's registered rule is not met; H3 is inconclusive; the dose-response shows nothing.**
- **City-level estimates (DEC-162).**
  - 113 per-unit SDIDs, plus 923 single-unit placebos for each cohort year, on V5.GL.06 and V6.GL.03: 5,764 fits, 0 solver warnings.
  - Placebo SD (= SE) is 0.0487 for cohort 2019 and 0.0524 for cohorts 2020/2021, i.e. about ±10% per unit at 95%.
  - Cohorts 2020 and 2021 share one placebo distribution: with 2020 dropped, both designs have pre-years 2010–2019 and post-years 2021–2024.
  - Per-unit estimates: mean +3.5% (Phase 7 primary +3.6%); range −12.3% to +16.4%; 87 of 113 above 0.
  - **Benjamini–Hochberg 5% on the unshrunk placebo p-values: 0 of 113 units pass.**
    - Unadjusted, 17 units have p < 0.05. The smallest p is 0.0043 (3 units); the smallest attainable with 923 placebos is 0.0022.
    - So BH could reject only if several units sat at that floor, and none do.
  - V6.GL.03 and V5.GL.06 per-unit estimates correlate at r = 0.71.
- **Hierarchical model (DEC-163).**
  - All five versions converged at the first attempt: R-hat ≤ 1.007, min ESS ≥ 1,455, 0 divergences.
  - Primary: between-unit SD τ = 0.013 log units against per-unit SEs of about 0.05, so the estimates shrink strongly towards the moderators' prediction.
  - Average city-level relative change: +3.5% (95% CrI +2.6% to +4.4%).
  - Coefficients (log scale, as %):
    - baseline PM2.5 −1.9% per SD (−3.2% to −0.5%);
    - IGP −0.3% (−3.3% to +2.6%);
    - log population −1.1% per SD (−2.5% to +0.3%);
    - coastal −4.0% (−6.6% to −1.3%);
    - XV-FC channel +3.1% (+0.2% to +6.0%).
  - XV-FC and log population correlate at r = 0.72, and IGP and baseline PM2.5 at r = 0.70. Moderators other than IGP are exploratory (plan §5).
  - Shrunken CrIs: entirely below 0 for 1 unit, entirely above 0 for 62, spanning 0 for 50.
  - The median 95% rank interval spans 75 of 113 places, so city rankings are mostly uninformative.
- **H5 (DEC-164): the registered rule is not met.** β_IGP = −0.0034 (−0.3%), 95% CrI −3.3% to +2.6%.
  - Beside it, none deciding:
    - IGP-only model −2.6% (−4.6% to −0.4%), the opposite direction to H5;
    - pre-fit-scaled SEs +0.0%;
    - wide priors −0.3%;
    - V6.GL.03 −0.0%.
  - Because H1 is not identified, this says nothing about whether NCAP worked less in the IGP.
- **H3 (DEC-165): inconclusive.**
  - (iii) fails, as known in advance: the ITS pair is "conflict".
  - (i) fails: the deweathered ratio estimate is +4.5% for the ITS (95% CI −0.0% to +9.2%, its lower bound just below 0) and +0.6% for the DiD (−8.7% to +11.7%).
  - (ii) fails: it holds for the ITS (2 of 3 specifications) but not the DiD (0 of 3).
  - Scope: 11 cities with both pollutants (27 co-located stations), against 5 control cities.
- **Dose-response (DEC-166, exploratory): no association.**
  - 40 XV-FC units.
  - −0.4% per doubling of the per-person allocation (95% CrI −3.5% to +2.7%); with IGP +0.1% (−3.1% to +3.3%); without Patna +0.6% (−2.7% to +4.1%).
  - The caveat is visible in the data: within a state, per-person allocations differ by a median 0.7% (at most 1.5%), while state means run from Rs 788 to Rs 3,746. The dose is effectively a state-level variable.
- **Layout changes after looking at the renders (no number affected).**
  - Figure 5's panel titles were wrapped (they overlapped).
  - Figure 6's legend was moved below the axes (it covered data) and its axis labels wrapped.
  - Figure 7 shows Layer A restricted (satellite PM2.5) as a reference row in panel (a), not (b) as DEC-167 said. A PM2.5 effect on the ratio's axis would have read as a ratio.
- **Run notes.**
  - The first per-unit SDID run stalled because the laptop was on battery: Windows throttled the R workers to about a tenth of normal speed. It was stopped, and `unit_sdid.R` now saves its fits in 200-fit chunks and resumes.
  - On mains power, V6.GL.03's 2,882 fits took 12.3 min. V5.GL.06 took 25.1 min, its first chunks on battery.
  - The H3 mechanism step ran before the pooling model; neither reads the other.

**DEC-169 (workflow): Phase 8 through Snakemake; reproducibility of the re-run.**
- **Config.** The only change to `config/params.yaml` is the new `hierarchical:` block (checked with `git diff 170deac`). Only `src/hierarchical/pooling.py` and `dose.py` read it (checked with `grep`). So, as in DEC-108/134/153, the upstream outputs were marked current with `snakemake --touch causal`.
- **The long rule.** The per-unit SDID was run by hand with the rule's own command (`python -m src.hierarchical.city_estimates run`), and its two outputs were marked current the same way.
- **What ran through Snakemake.** The other eight Phase 8 rules ran through Snakemake (`snakemake --cores 1 hierarchical`; log `data/interim/logs/snakemake_phase8.log`): the city table, pooling, dose, mechanism, figures 5–7, the report and the target.
- **Result.** All 20 outputs are byte-identical to the hand-built ones, including the seeded PyMC posteriors, and `docs/heterogeneity_report.md` is byte-identical. Afterwards `snakemake -n hierarchical`, `-n causal` and `-n pregate` report nothing to do.
- **Tests:** 208 passed (`data/interim/logs/pytest_phase8.log`).

## 2026-10-03: Phase 8 approved (Reenu); closing items

**DEC-170 (DEVIATION from DEC-167, dated 2026-10-02, logged 2026-10-03): figure 7 shows the satellite PM2.5 reference (Layer A restricted) in panel (a), not panel (b).**
- **What DEC-167 said:** panel (b), the PM2.5/PM10 ratio, would show "Layer A restricted (PM2.5) for reference".
- **What was done:** the reference row sits at the bottom of panel (a), the panel of PM2.5 and PM10 estimates in %, labelled "Satellite PM2.5 (reference)".
- **Why:** panel (b)'s axis is the change in the PM2.5/PM10 *ratio*. A PM2.5 estimate drawn on that axis would read as a ratio estimate, and Layer A has no PM10. Panel (a)'s axis has the same units as the satellite estimate.
- **Effect:** layout only. No number, rule or verdict changes. It was decided after looking at the render and before Reenu's review. DEC-168 already mentions it; this entry records it as a deviation.

**DEC-171 (written 2026-10-03, BEFORE any fire-covariate estimate; FIRMS was being downloaded, no FIRMS value had been read): how the registered "VIIRS fire covariate (from 2012)" check is run.**
- **What is registered.** Plan §4 lists "VIIRS fire radiative power, from 2012, in one sensitivity check (DEC-039)" among the covariates. The §5 table lists "VIIRS fire covariate (from 2012)" under other checks. The proposal's purpose is "add regional fire radiative power as a covariate", against crop-burning shocks confounding IGP cities. DEC-147 item 17 only recorded "not run". Phase 7 never fixed the details, so they are fixed here.
- **Data.**
  - VIIRS S-NPP standard-processing yearly country files, 2012–2024 (`data/raw/firms/archive/`, DEC-039). The 2025–March 2026 API files are downloaded by the same script but not used: Layer A ends in 2024.
  - Detections kept: `type` = 0 (presumed vegetation fire; static land sources, volcanoes and offshore detections dropped) and `confidence` nominal or high (low dropped).
  - If these columns are absent or coded differently from FIRMS's documentation, the check stops and Reenu is told. Nothing is substituted.
- **Covariate, per unit-year.**
  - fire = log(1 + Σ FRP), with FRP in MW, summed over the kept detections of the calendar year that lie within 100 km of the unit polygon, inside it included.
  - Distances are measured in EPSG:7755, Phase 4's metric CRS for India (`src/causal/pregate.py`).
  - The same rule applies to treated and control units.
- **Why 100 km.** Crop-residue smoke reaches cities over hundreds of kilometres, but anything shared by a whole region in a year is already absorbed by the region × year fixed effects. A 100 km neighbourhood gives each unit its own exposure, varying within a region. This is a judgement made before any fire value was looked at, not a tuned value.
- **Estimator: the event study, as DEC-142, with fire added to the ERA5 covariates.**
  - The primary SDID has no covariates (DEC-139). Covariates enter the event study (plan §5 item 2), and plan §4 lists FRP with them.
  - The precedent is DEC-147 item 13 (Himalayan split): a check that SDID cannot express runs in the event study.
- **Years.** 2012–2024 without 2020, because VIIRS starts in 2012. Reference periods follow DEC-142's rule (each cohort's last observed pre-year). The earliest relative year becomes −7 for cohort 2019 (−8 for cohorts 2020 and 2021, outside the window and given its own indicator).
- **Comparison number.** The average post-period estimate (l = 0 … +5). As in DEC-147 item 13, it is set against the primary SDID with DEC-135's "agrees" rule: same sign, point estimate inside the primary's 95% CI.
- **Reported beside it, not deciding:**
  - the same event study on 2012–2024 without the fire covariate, which separates the effect of adding fire from the effect of the shorter window;
  - the fire coefficient;
  - the pre-trend Wald p over the pre-periods available (−7 … −2), for information. Rule (b) belongs to the primary event study and is unchanged.
- **What changes in Phase 7's outputs:**
  - the "VIIRS fire covariate (from 2012)" row of the robustness table (`robustness.csv`, `docs/causal_report.md` §9) and its "x of y checks agree" count;
  - every summary count that quotes it (PROGRESS, the Phase 7 phase note, as a dated addendum).
  - Nothing else in Phase 7 is re-run or changed. H1's verdict cannot change: this is a robustness check, not a rule.

**DEC-172: FIRMS downloaded (2012–2024); the 2025+ API part fails because FIRMS changed its API; the fire-covariate check agrees (Layer A robustness now 17 of 19).** Rules: DEC-171, pushed in `4eb69f7` before any fire value was read.
- **Download (2026-10-03, new network, new key in `.env`).**
  - The 13 VIIRS S-NPP yearly India files, 2012–2024: 566 MB, verified and recorded in `data/raw/firms/MANIFEST.csv` (url, upstream ETag / Last-Modified / size, sha256).
  - Upstream, they are dated 24 June 2025.
- **The January 2025 – March 2026 part failed.**
  - All 91 country-API requests returned HTTP 400 "Invalid API call".
  - The key itself is valid: `mapkey_status` answers, 5,000 transactions per 10 minutes.
  - FIRMS's area (bounding-box) endpoint answers normally for the same dates. So the country endpoint has changed or been withdrawn.
  - Under hard rule 1 the downloader was **not** switched to another endpoint. The 91 empty sidecar stubs of the failed attempts were deleted, and the acquisition flag stays unwritten.
  - No current analysis needs 2025+ fire data: Layer A ends in 2024. This is open for Reenu.
- **Snakemake.** The fire rules (`causal_fire_covariate`, `causal_fire`) depend on the FIRMS manifest, not on the acquisition flag.
- **Data as documented.** The code checks every file's columns: `type` codes are within {0, 1, 2, 3} and `confidence` within {l, n, h}. 5,496,513 detections were kept (type 0, nominal or high confidence). Every one of the 1,036 units has at least one kept detection within 100 km in every year 2012–2024.
- **Result.**
  - The event study with fire, 2012–2024 without 2020, gives an average post-period estimate of +0.0302 (+3.1%; 95% CI +1.7% to +4.5%). It **agrees** with the primary SDID: same sign, inside +2.4% to +4.8%.
  - The same window without fire gives +0.0304 (+3.1%), so adding fire changes the estimate by 0.0002.
  - Fire coefficient: −0.0090 (SE 0.0021). It is reported, not interpreted: as for ERA5's covariates, no claim is made about an individual covariate (DEC-136).
  - Pre-trend Wald p = 0.0002, for information; rule (b) is the primary's and is unchanged.
- **Correction to DEC-171's wording.** Relative years −8 (cohort 2020) and −9 (cohort 2021) are *inside* the −9 … +5 window, not outside it. So the Wald test covers −9 … −2, with only the later cohorts at the earliest lags. Nothing computed depends on that sentence.
- **Changed in Phase 7's outputs, and nothing else:**
  - the fire row of `robustness.csv` and `docs/causal_report.md` §9;
  - "16 of 18" → **"17 of 19" Layer A checks agree**. Every Layer A estimate is still positive, and H1's verdict is unchanged.
  - Rebuilt through Snakemake: `causal_robustness`, `causal_report` and `heterogeneity_report`. All are byte-identical to the hand-built files, and `snakemake -n causal`, `-n hierarchical` and `-n pregate` report nothing to do.
  - The Phase 7 phase note gets a dated addendum, and PROGRESS is updated.

**DEC-173: FIRMS January 2025 – March 2026 will not be downloaded (Reenu, 2026-10-03).** No analysis needs those months: Layer A ends in 2024, and the fire check uses 2012–2024. The country-API part of `src/acquire/firms.py` stays as written and fails (DEC-172); it is not switched to the area API. FIRMS is closed.

## 2026-10-03: Phase 8b (raw MAIAC AOD check). Rules written BEFORE any AOD value is pulled

The registered plan (§5, calibration-leakage threat) lists raw MAIAC aerosol optical depth "if time allows" and says nothing more. Reenu decided on 2026-10-03 to run it through Google Earth Engine (GEE), as Phase 8b. Everything below fills that gap. It was committed and pushed before the Earth Engine API was installed, so before any AOD value existed. **H1 is "not identified by this design" (DEC-151), and nothing in this phase can change that:** the verdict rests on the failed pre-trend test. Nothing here is an effect of NCAP.

**DEC-174 (facts checked 2026-10-03, hard rule 2): the product and the population weights.**
- **Product:** MODIS MAIAC MCD19A2 Collection 6.1, GEE collection `MODIS/061/MCD19A2_GRANULES`. The catalogue gives availability 2000-02-24 to 2026-09-25, 1 km pixels, band `Optical_Depth_055` with scale 0.001 and valid range −100 to 8000 (so AOD −0.1 to 8.0), and the `AOD_QA` bitmask. LP DAAC data carry no restriction on use or redistribution.
- **QA bits,** checked against the MCD19 C6.1 user guide (§5.4) and identical in the GEE catalogue: bits 0–2 cloud mask (001 = clear, 010 = possibly cloudy); bits 3–4 surface (00 = land); bits 5–7 adjacency (000 = normal/clear, 011 = adjacent to a single cloudy pixel); bits 8–11 AOD QA (0000 = best quality, 0011 = one neighbour cloud, 1011 = land, research quality: AOD retrieved but cloud mask possibly cloudy); bit 12 glint; bits 13–14 aerosol model.
- **What the guide recommends (§4):** "The best quality AOD is represented by the QA bit 0000 'Best quality'. It is a combination of the two filters: QA.CloudMask = Clear and QA.AdjacencyMask = Clear." Adjacency should be Normal for general use; "AdjacentToASingleCloudyPixel can also be used as it often represents false cloud detection".
- **Structure:** each MCD19A2 file holds one layer per overpass (1–2 orbits a day near the equator, Terra and Aqua; guide §3.1). The GEE "_GRANULES" collection is expected to hold one image per tile and overpass. **This is checked on the day, before the export: if the collection is instead a daily composite, or the band or scale differs, the export stops and Reenu is told.**
- **Population weights:** our local weights are GHS-POP E2020 **R2023A**, 30 arc-seconds (DEC-038). GEE holds `JRC/GHSL/P2023A/GHS_POP`, the same release (R2023A) and epoch (2020), at 100 m (Mollweide). So the release and epoch match exactly; only the grid differs (100 m instead of 30″). Exact weights cannot be uploaded without a Cloud Storage bucket or the web interface, so the GEE 100 m layer is used, summed onto the MODIS grid (DEC-176). A check against our own weights is fixed in DEC-176.
- **GEE quota:** since 27 April 2026, noncommercial projects have a monthly compute quota. The default "Community" tier is 150 EECU-hours a month (developers.google.com/earth-engine/guides/noncommercial_tiers; checked 2026-10-03). DEC-178 sets how the export stays inside it.

**DEC-175: QA filtering and band.**
- **Band:** `Optical_Depth_055` (0.55 µm) × 0.001. Small negative retrievals (down to −0.1) are kept as retrieved, not clipped: clipping would bias clean-air means upward. The annual means used are expected to be well above 0; if any unit-year mean is ≤ 0, the analysis stops (the log is undefined) and Reenu is told.
- **Primary filter (per pixel and overpass):** land (bits 3–4 = 00) **and** cloud mask clear (bits 0–2 = 001) **and** adjacency normal (bits 5–7 = 000) **and** AOD QA best (bits 8–11 = 0000). This is the guide's "best quality", with its two component filters checked explicitly.
- **Glint (bit 12) is not filtered.** Sun glint matters over water, and water pixels are already excluded; a glint filter on land would remove pixels by viewing geometry (season and latitude), not by quality.
- **Relaxed filter (sensitivity):** land **and** cloud mask clear or possibly cloudy (001, 010) **and** adjacency normal or adjacent to a single cloudy pixel (000, 011) **and** AOD QA in {0000 best, 0011 one neighbour cloud, 1011 land research quality}. Why it is worth running: MAIAC can flag thick winter haze or smoke as cloud, which removes the most polluted days from the strict filter. The relaxed filter keeps more of them, at the cost of more cloud contamination.

**DEC-176: from overpasses to unit-month values.**
- **Day:** the UTC date of the overpass (`system:time_start`). Indian MODIS overpasses (about 10:30 and 13:30 local time, i.e. about 05:00 and 08:00 UTC) fall on the same UTC date as the Indian date.
- **Daily pixel value:** the mean of that day's valid overpasses (Terra and Aqua weighted equally), after the QA filter.
- **Pixel-month value:** the mean of the pixel's valid daily values in the calendar month, and the pixel's number of valid days. A pixel with no valid day has no value that month.
- **Unit-month value, primary (population-weighted, as Layer A, DEC-070):** Σ w·c·AOD / Σ w·c over the unit's pixels with a value, where w = the 2020 population of the MODIS pixel and c = the fraction of the pixel inside the polygon.
  - w: GHS-POP 2020 (R2023A, 100 m) converted to people per m², averaged onto the MODIS 1 km sinusoidal grid with `reduceResolution(mean)` (area-fraction weights, as GEE recommends for count-like layers), times the MODIS pixel area. This is "GHS-POP summed onto the product grid", as DEC-070 does for ACAG.
  - c: GEE's weighted reducers use the fraction of each pixel covered by the polygon (quantised to 1/256). It plays the role of exactextract's exact coverage fraction in Layer A.
  - The reduction runs in the MODIS granules' own projection and grid, so no AOD pixel is resampled.
- **Unit-month value, sensitivity (area-weighted):** Σ c·AOD / Σ c over pixels with a value. The sinusoidal grid is equal-area, so this is an area-weighted mean.
- **Coverage measures per unit-month:** population coverage = Σ w·c over pixels with a value / Σ w·c over all pixels; population-weighted valid days = Σ w·c·days / Σ w·c (pixels with no value count as 0 days); and the same two on area weights.
- **What is exported** (per unit and month): the raw sums (Σ w·c, Σ c, and for each filter the sums of w·c, w·c·AOD and w·c·days over valid pixels, plus their area-weighted counterparts for the primary filter). Means and coverage are formed locally, in committed code, from these sums.
- **Weight check, fixed now:** the GEE weights summed over each unit (Σ w·c) are compared with Phase 3's GHS-POP 30″ population of the same polygon (`unit_year_sat.parquet: pop`). **If the median absolute difference over the 1,036 units exceeds 10%, the analysis stops and Reenu is told.** Otherwise the median and 90th-percentile differences are reported.

**DEC-177: coverage rules, the monsoon, and the analysis sample (fixed before any coverage figure is seen).**
- **Valid unit-month:** population coverage ≥ 50% **and** population-weighted valid days ≥ 4 (about one clear day a week). The area-weighted sensitivity applies the same thresholds to its area-weighted measures; the relaxed filter applies them to its own measures.
- **Seasons:** the monsoon months are June–September (IMD's southwest-monsoon season); the other eight (January–May, October–December) are "non-monsoon".
- **Valid unit-year:** at least 6 of the year's 8 non-monsoon months are valid. Cloud removes most monsoon retrievals in many units in many years, so monsoon months are never required: a rule that needed them would drop units because of where it rains, not because of data quality.
- **Annual value, primary:** the mean of the year's valid monthly values, monsoon months included when they are valid. (The annual value is formed from the monthly means; ACAG's annual mean also covers the whole year.)
  - Which monsoon months are valid changes from year to year, so the annual mean's seasonal mix changes too. That adds noise, and it could add bias if monsoon cloudiness trended differently in NCAP units.
- **Sensitivity, non-monsoon annual:** the mean of the year's valid non-monsoon months only (same year rule). Its seasonal mix varies far less.
- **Analysis sample:** a unit enters an AOD specification only if that specification's annual series is valid in every year 2010–2019 and 2021–2024 (SDID needs a balanced panel, DEC-139; 2020 is dropped as in Layer A and is not required). Nothing is imputed. The same rule applies to treated and control units.
  - Reported: units kept and dropped by role, cohort, region and leakage group; valid-month shares by calendar month and region.
  - A leakage group with fewer than 10 kept units is not estimated (`robustness.leakage_min_units`, as registered). A cohort with no kept unit drops out of the cohort aggregate.
  - **If fewer than half of the 113 treated units are kept,** every AOD result is labelled "limited coverage" beside its classification.
  - Dropping units by cloudiness is a selection on geography, not on outcome trends. Its consequence (the AOD sample is not Layer A's sample) is handled by estimating ACAG PM2.5 on the same sample (DEC-179).

**DEC-178: the export (`src/acquire/maiac_gee.py`; nothing is done in the GEE web interface).**
- **Units:** the 1,036 Layer A units (113 treated, 923 controls) from `data/interim/sat_units.gpkg`, passed in the script as GeoJSON (1.4 MB, 30,443 vertices; under GEE's 10 MB request limit). Roles stay local; nothing about treatment goes to GEE.
- **Window:** January 2010 to December 2024.
- **Tasks:** one `Export.table.toAsset` per calendar year (15 tasks, 12 months × 1,036 units each) into the project's assets (`projects/ncap-evaluation/assets/…`). Each table is then downloaded as CSV with `getDownloadURL` and saved, unchanged, as the raw file.
- **Pilot first:** one month is exported and timed. Its compute (the task's EECU usage) is scaled to 180 months. **If the projected total exceeds 100 EECU-hours** (two thirds of the Community tier's 150 a month, leaving room for re-runs), the full export is not started and Reenu is told. The pilot table is stored under `data/interim/maiac_gee_pilot/`, not as raw data, and no estimate uses it.
- **Raw data (hard rule 7):** `data/raw/maiac_gee/maiac_unit_month_<year>.csv`, one per year. The manifest records for each file: the GEE asset id as its url; a remote id made of the task id, the commit and sha256 of `maiac_gee.py` at export, and the sha256 of the request parameters; the download time; the sha256 and size of the file; and the request parameters themselves in the notes (collection, band, scale, both QA filters, population asset, projection, years, months). The script is committed before the export runs, so the commit named in the manifest contains the exact code.
- **Credentials (hard rule 5):** Reenu authenticates in the browser (`earthengine authenticate`). The credentials stay in `~/.config/earthengine/`, outside the repository. The project id (`ncap-evaluation`) is not a secret; it goes in `config/params.yaml`.

**DEC-179: the analysis (Phase 7's engine, unchanged).**
- **Outcome:** log of the annual unit mean of AOD (dimensionless), 2010–2024 without 2020.
- **Design, exactly as Layer A's primary (DEC-139):** SDID per listing cohort with never-treated controls, cohort estimates combined by treated units, 2020 dropped, SE from 500 joint-placebo replications drawn from the specification's own controls, 95% CI = estimate ± 1.96 SE. `src/causal/sdid.R` is run unchanged, on its own folder (`data/processed/causal/maiac/`), so no Phase 7 specification, panel or hash changes.
- **Monitor-gain split (DEC-146):** the same groups (`monitor_gain.csv`: gained a monitor 2019–2024 or not), each group's estimate and the difference (gained − not gained), all from the same joint-placebo draws.
- **Specifications** (each with its own 500 replications):
  1. `aod_primary`: log AOD, population-weighted, primary filter, all valid months, with the monitor-gain split. **This one is classified by DEC-180.**
  2. `acag_aod_sample`: log ACAG V5.GL.06 PM2.5 (population-weighted, Phase 7's series), on exactly the units of `aod_primary`, with the split. It is the like-for-like yardstick: it separates "AOD differs from ACAG" from "the AOD sample differs from Layer A's".
  3. `aod_nonmonsoon`: as 1, non-monsoon annual (DEC-177).
  4. `aod_area`: as 1, area-weighted.
  5. `aod_relaxed`: as 1, relaxed QA filter (DEC-175).
  6. `aod_restricted`: as 1, with only the treated units that have a Layer B PM2.5 panel (Phase 7's restricted set; DEC-150), for the triangulation investigation's calibration step.
  Specifications 3–6 are reported beside 1 and classified by the same rule for information; they do not change 1's classification. Each uses the units whose own series is complete (DEC-177), and its yardstick is ACAG on those units.
- **Event study (DEC-142, unchanged):** Sun & Abraham on log AOD, the `aod_primary` units, unit and region × year fixed effects, the same ERA5 covariates, SEs clustered by unit, relative years −9 to +5. Reported: the coefficients, the pre-trend Wald p and the average post-period estimate. **For information only; it decides nothing here.** Rule (b) belongs to H1 and is unchanged.
- **Run time:** about 1.5–2 h of SDID on 8 workers (about 0.39 s per fit, DEC-151), on mains power (DEC-168).

**DEC-180: how the AOD results are read, fixed in advance.** AOD is a column measure, not surface PM2.5. Its link to PM2.5 depends on boundary-layer height, humidity and aerosol type, all of which can change over time and differ between places. **So the check tests direction, not size.** No AOD estimate is ever turned into µg/m³ or set on the PM2.5 "agrees" scale. Sizes enter in one place only, as a resolution yardstick: whether an AOD interval is wide enough to contain both "no change" and a change of the same relative size as ACAG's on the same units. That mirrors the registered "uninformative" layer category (plan §5, DEC-135).

Two questions, each classified by the first rule that applies. The inputs are `aod_primary` and `acag_aod_sample`, both on the same units.

- **Q1. Does the relative rise appear in AOD?** A = the AOD estimate (log) with its 95% CI; P = the ACAG estimate on the same units.
  0. *Not testable on this sample* if P < 0 or P's 95% CI includes 0 (the rise Q1 asks about is then not present in ACAG on these units).
  1. *Uninformative* if A's 95% CI contains both 0 and P.
  2. *Rise also in AOD* if A > 0 and its CI excludes 0.
  3. *Opposite direction* if A < 0 and its CI excludes 0.
  4. *Rise not reproduced* otherwise (A's CI includes 0 but lies below P).
- **Q2. Does the gained/not-gained gap appear in AOD?** D_A = the AOD difference (gained − not gained) with its 95% CI; D_P = the ACAG difference on the same units.
  0. *Not testable on this sample* if D_P is not negative with a 95% CI excluding 0 (the leakage warning is not reproduced in ACAG on these units), or if either group has fewer than 10 kept units.
  1. *Uninformative* if D_A's 95% CI contains both 0 and D_P.
  2. *Gap reproduced in AOD (against leakage)* if D_A < 0 and its CI excludes 0.
  3. *Gap absent from AOD (consistent with leakage)* otherwise (D_A's CI lies above D_P).
- **What each outcome means, written now:**
  - Q1 "rise also in AOD": the relative rise of NCAP units also appears in a signal that no ground monitor calibrates, so ACAG's calibration did not produce it. (Leakage as hypothesised pulls units that gained monitors *down*, so it could not have produced a rise anyway; Q1 tests ACAG's processing more broadly.)
  - Q1 "opposite direction" or "rise not reproduced": raw AOD does not show the rise. Either something in ACAG's processing produced it, or the link between column AOD and surface PM2.5 changed differently in NCAP units (boundary layer, humidity, aerosol mix). This check cannot tell which.
  - Q2 "gap reproduced": units that gained monitors also rose less in a monitor-free signal, so calibration leakage is an unlikely explanation for the gap. Real differences between the two groups (size, pollution, the AOD–PM link) remain.
  - Q2 "gap absent": the gap is not in the monitor-free signal. That is what calibration leakage would produce. It is consistent with leakage, not proof: a group difference in the AOD–PM link would look the same.
  - "Uninformative": AOD is too noisy here to tell. 2.8 × SE is reported beside it as the smallest difference the design could reliably detect (hard rule 8).
  - "Not testable": stated with the reason.
- **Always:** H1 stays "not identified by this design" whatever the classification. Every AOD estimate is printed as a % change in AOD (100 × (e^β − 1)), labelled "AOD, not PM2.5", next to that caveat.

**DEC-181: where the results go, and the wording.**
- **`docs/causal_report.md`, a new section §12 "Raw MAIAC AOD (Phase 8b)",** generated from the outputs: the coverage and sample tables, the weight check, every specification's estimates, the event study, the Q1/Q2 classifications with their pre-written meanings, and the caveats.
- **The robustness table (§9):** the "Raw MAIAC AOD" row shows the `aod_primary` estimate and CI with "agrees: —". An AOD log change is not on the PM2.5 scale, so DEC-135's "agrees" does not apply and the "17 of 19" count is unchanged. The note gives Q1 and Q2.
- **The triangulation investigation (§8), step 2 (satellite calibration):** a row "Layer A restricted, raw MAIAC AOD (log AOD; direction only)" from `aod_restricted`, beside the V5.GL.06 and V6.GL.02.04 rows. The two registered pair classifications (§8's first table) are not changed: they compare ground PM2.5 with satellite PM2.5, and AOD is neither.
- **Wording (DEC-154 and the Phase 8 rule):** nothing is an effect of NCAP. Every AOD estimate carries "H1 is not identified by this design" beside it. Estimates are "relative changes in AOD of listed units against their synthetic comparison".

**DEC-182 (implementation, written before any AOD value was pulled; nothing here changes DEC-174 to DEC-181's rules).**
- **Environment: `earthengine-api` 1.7.46 added, and nothing else changed.** Re-locking in update mode (`conda-lock --update earthengine-api`) re-solved the whole environment, because the package was new: about 40 unrelated packages moved (duckdb, geopandas 1.1 → 1.2, xarray, pytensor, arviz, …). As in DEC-093, that re-solve was discarded. Instead:
  - every locked version was pinned and `earthengine-api` added, in a dry-run solve per platform. Both solved with **30 new packages** (earthengine-api and Google's client libraries) **and 0 changed**;
  - those 30 entries per platform, with conda-forge's URLs, md5 and sha256, were inserted into `conda-lock.yml` in its sorted order. The diff is insertions only; all 1,008 old entries are unchanged, and every dependency of a new package is in the lock;
  - the win-64 entries were installed into `ncap` from the lock's URLs. Afterwards `conda list` matches the lock's 491 win-64 conda packages exactly.
  - The lock's `content_hash` field still describes the previous `environment.yml`: conda-lock's hash function did not reproduce the stored hash of the old file, so a recomputed value could not be checked and was not written. It only means a future `conda-lock lock` will re-solve, which it would do anyway.
  - **Found while doing this (open for Phase 10):** the locked `wcwidth 0.9.1` build (`pyh5ded981_0`) is no longer offered on conda-forge's main label. A clean `conda-lock install` from this lock may fail on that one package; the clean-clone check must test it.
- **Settings live in `config/maiac.yaml`, not `config/params.yaml`** (DEC-178 said params.yaml). `params.yaml` is an input of the first ingest rule, so any edit to it marks every Phase 2–8 output stale (DEC-108). The project id, collection, QA filters and thresholds are the same values either way.
- **The sensitivity specifications (DEC-179 items 3–6) estimate the overall relative change only, and are classified by Q1 only.** The monitor-gain split, and so Q2, is estimated on the primary (`aod_primary` with `acag_aod_sample`), as DEC-180 classifies. Running the split on every sensitivity would roughly triple the SDID time for numbers that classify nothing. If a sensitivity's units equal the primary's, its yardstick is `acag_aod_sample`; otherwise it gets its own ACAG specification on its own units (DEC-179).
- **Engine:** `SdidSpec`'s monitor-gain split now uses the specification's first outcome instead of a hard-coded `log:popw_V5GL06`, so it can run on log AOD. Every Phase 7 specification's first outcome is that same series. Rebuilding Phase 7's 19 specifications into a scratch folder gave 19 identical spec hashes and byte-identical fit-set and estimand tables, so no Phase 7 output is touched.

**DEC-183 (implementation change to DEC-178's route, 2026-10-03, before any AOD value was computed): the tables are exported to Google Drive, not to Earth Engine assets.**
- **What happened.** Reenu authenticated, and `python -m src.acquire.maiac_gee check` ran under project `ncap-evaluation` (so the project is registered for computation). The check confirmed DEC-174's expectations: one image per tile and overpass (`…_h25v06_…_01`, `_02`, …), `Optical_Depth_055` an integer band, the MODIS sinusoidal grid (SR-ORG:6974, 926.6 m, one global transform), all 9 Indian tiles present, and Indian overpasses at about 05:55 and 07:35 UTC (`data/interim/maiac_gee/check.json`). The first pilot export then failed before computing anything: "Asset 'projects/ncap-evaluation/assets' does not exist or doesn't allow this operation". `listAssets` and `createAsset` on that root fail the same way, so the project has no asset area to write to.
- **Change.** `Export.table.toDrive` into one folder of Reenu's Google Drive (`ncap_maiac_gee`), with the same columns. The CSV is then downloaded through the Drive API with the same Earth Engine credentials (their scopes include Drive; only the scope list was read). Drive reports each file's md5, and the download must match it before the file is accepted (`download(..., expected_md5=…)`). The manifest url becomes `gdrive:ncap_maiac_gee/<file>`, and the remote id adds the Drive file id and md5. Everything else in DEC-178 is unchanged: the computation, the pilot and its compute budget, one task per year, the commit check, the manifest fields.
- **Why not fix the asset root:** that would need a change in the Cloud or Earth Engine web console, which DEC-178 rules out, and the route does not change any value. The Drive files (16 CSVs, about 2 MB each) are private and can be deleted once downloaded and recorded.
- **Also seen in the check:** `filterBounds` over the Indian units also returns Antarctic tiles (h15v17–h20v17), probably because of their footprint geometry. They hold no pixel inside any unit, so they cannot change a value; they can only add compute, which the pilot measures.

**DEC-184 (2026-10-03): the pilot trips DEC-178's compute stop rule. The full export is NOT started; Reenu decides.**
- **Pilot (January 2019, all 1,036 units, both filters):** the Drive export completed in 97 s of wall time and used **5,199 EECU-seconds (1.44 EECU-hours)**. Scaled to 180 months that is **≈ 260 EECU-hours**: above DEC-178's limit of 100, and above the Community tier's 150 a month. The table is complete (1,036 rows, every column). No AOD value was read; only row and column counts and the comparison below.
- **A diagnostic second pilot, with the collection restricted to the 9 MODIS tiles that hold the units** (`config/maiac.yaml: tiles`; it removes the Antarctic granules that `filterBounds` lets through, DEC-183): 4,811 EECU-seconds, ≈ 241 EECU-hours projected. Still over budget. The cost is the work itself, not the stray granules.
  - **The tile filter changes no value:** the two pilot tables agree to within 4 × 10⁻⁸ relative, only in the population-weighted sums (floating-point order inside Earth Engine's resampling of the 100 m population layer); the area-weighted sums are identical. So Earth Engine reruns agree to about 8 significant figures, not byte for byte. The filter stays in the script because it is cheaper.
- **Compute used so far:** 2.78 EECU-hours of this month's 150.
- **Options put to Reenu** (none taken):
  - (a) Move the project to the **Contributor tier** (1,000 EECU-hours a month; needs a billing account linked to the Cloud project, which Google says is not charged for noncommercial use). Then run the specification unchanged, with the compute limit raised before the export (a new entry).
  - (b) Stay on the Community tier and **spread the export over two calendar months** (about 120 EECU-hours in each), with the limit restated per month. Results would arrive in November.
  - (c) **Reduce the work:** for example, drop the relaxed-filter sensitivity, or compute the population weights once instead of every month. Each needs its own measured pilot (about 1.4 EECU-hours each), and dropping a sensitivity changes DEC-179, so it would be logged as a change before any AOD value is used.

**DEC-185 (Reenu, 2026-10-03; written before the export is submitted): DEC-184's option (a). The project is on the Contributor tier, and the compute limit is 400 EECU-hours.**
- Reenu moved the `ncap-evaluation` project to the Contributor tier (1,000 EECU-hours a month; a billing account linked, which Google says is not charged for noncommercial use). The tier change was made by Reenu in the Cloud console; the API offers no way to confirm it, so a quota error during the export would stop the run and be reported.
- **The new limit is 400 EECU-hours** (`config/maiac.yaml: eecu_budget_hours`), 40% of the monthly tier, leaving room for re-runs. The latest pilot projects ≈ 241 (tile filter, DEC-184), so the export proceeds. `submit` now checks the pilot's projection against the limit in force, not the flag stored under the old limit.
- **During the export:** `status` sums the tasks' EECU use. If it passes 400 before all 15 years finish, the remaining tasks are cancelled and Reenu is told.
- Nothing else in DEC-174 to DEC-184 changes.

## 2026-10-03: Phase 8b results (rules DEC-174 to DEC-185, all pushed before the values they govern)

Numbers from `docs/causal_report.md` §12 (generated). **H1 is "not identified by this design" (DEC-151) and is unchanged; nothing below is an effect of NCAP.** Every AOD number is a relative change in AOD, not PM2.5, and is read for direction only (DEC-180).

**DEC-186: Q1 "rise not reproduced in AOD"; Q2 "gap absent from AOD (consistent with calibration leakage)".**
- **Export:** 15 yearly tasks, all completed; 167.9 EECU-hours (the pilot projected ≈ 241). Tables: 15 × 12,432 unit-months, md5-checked against Drive. Total compute including the two pilots: 170.7 EECU-hours, inside the 400 limit.
- **Weight check (DEC-176): passed.** The GEE population per unit is a median 3.4% above Phase 3's (90th percentile of the absolute difference 9.2%; log correlation 0.9995).
- **Coverage and sample (DEC-177):**
  - July and August unit-months are valid 4–8% of the time in every region; October–April mostly above 80%.
  - **Kept units:** 95 of 113 treated and 741 of 923 controls (primary series), so no "limited coverage" label.
  - Kept treated by monitor-gain group: gained 64 of 74, not gained 31 of 39 (both ≥ 10).
  - Retention is lowest on the coast (47 of 128 coastal controls) and highest in the IGP (391 of 399 controls).
  - ACAG on the kept units gives +4.2% (Layer A's primary on all units: +3.6%), so the sample shift moves the ACAG estimate a little. That is why every AOD result is set against ACAG on the same units.
- **Primary (`aod_primary`, 95 / 741):** AOD **+0.8% (95% CI −0.4% to +2.0%)**; ACAG on the same units +4.2% (+2.7% to +5.6%). SE 0.0062, so 2.8 × SE = 0.0173 (≈ 1.7%). The AOD interval includes 0 and lies below ACAG's estimate, so **Q1 = "rise not reproduced"**.
- **Monitor-gain split:**
  - AOD: gained +1.2% (−0.2% to +2.7%); not gained −0.4% (−2.3% to +1.6%); difference **+1.6% (−0.8% to +4.0%)**.
  - ACAG on the same units: +2.8%, +7.1%, difference **−4.1% (−6.7% to −1.4%)**. The warning is reproduced on this sample, so Q2 is testable.
  - The AOD interval lies above −4.1%, so **Q2 = "gap absent (consistent with leakage)"**. The AOD point estimate has the opposite sign.
- **Sensitivities (Q1 for information, DEC-182):**
  - non-monsoon **+1.5% (+0.4% to +2.6%): "rise also in AOD"**;
  - area-weighted +0.8% (−0.4% to +2.0%): not reproduced;
  - relaxed QA +0.4% (−0.8% to +1.6%): not reproduced;
  - restricted to 17 Layer B units −2.0% (−4.5% to +0.6%; ACAG on them +3.9%): not reproduced; also the new row in investigation step 2.
  - So the primary's classification holds in 3 of 4 sensitivities; non-monsoon is the exception. In all 5 AOD specifications the point estimate is below ACAG's on the same units; 1 of the 5 intervals lies entirely above 0.
- **Event study on log AOD (information):** average post-period +1.3% (95% CI +0.1% to +2.6%); the pre-trend Wald test also fails (χ² = 22.1, 8 df, p = 0.0048).
- **SDID solver warnings:** 0 in every fit.
- **How this reads (DEC-180's pre-written meanings, nothing added):**
  - Q1: raw AOD does not show ACAG's relative rise in the primary. Either something in ACAG's processing produced it, or the AOD–PM2.5 link changed differently in NCAP units; this check cannot tell which. The non-monsoon and event-study numbers say AOD's relative change is small, and whether it is above 0 depends on the specification; it is below ACAG's everywhere.
  - Q2: the gained/not-gained gap is not in the monitor-free signal. That is what calibration leakage would produce; it is consistent with leakage, not proof, because a group difference in the AOD–PM link would look the same.
- **Changed elsewhere:**
  - the "Raw MAIAC AOD" row of the robustness table (estimate shown, "agrees: —", so "17 of 19" is unchanged);
  - one new row in investigation step 2;
  - §12 of `causal_report.md`.
  - The two registered triangulation categories, H1, H2, H3, H4 and H5 are unchanged.

**DEC-187 (workflow): Phase 8b through Snakemake; reproducibility.**
- **Rules:** `causal_maiac_panels`, `_specs`, `_sdid`, `_event` and `_summary` (`workflow/rules/causal.smk`). Robustness, triangulation and the report now also read the Phase 8b outputs. The export itself is run on request (it needs Reenu's credentials), like FIRMS.
- **The SDID rule's command was fixed for Windows.** Snakemake runs rule commands in `cmd`, where the `VAR=1` prefix and `touch` do not exist. The module now sets one BLAS thread per worker itself (through `layer_a.run`) and writes the `sdid/all.done` flag. The Phase 7 SDID rules carry the same prefix; they have always been run by hand with their own command (DEC-153), and are left as they are.
- **Order of events:**
  1. The SDID specifications were run by hand with the rule's command (84 min, on mains power).
  2. Phase 7's outputs were marked current with `snakemake --touch causal`. `layer_a.py` had changed, but all 19 Phase 7 spec hashes are identical (DEC-182).
  3. The whole Phase 8b chain was then forced through Snakemake from `causal_maiac_panels` (logs `data/interim/logs/snakemake_phase8b*.log`).
- **Result, against copies taken before the rerun:**
  - The rebuilt specifications have identical hashes, so the SDID engine recomputed nothing.
  - `causal_report.md`, `heterogeneity_report.md`, `robustness.csv`, `triangulation.csv`, `investigation.csv` and `partA_results.json` are byte-identical.
  - Within `maiac/`, 120 of 132 files are byte-identical. The 9 `done.txt` files differ by timestamp. The event-study coefficients differ by at most 7 × 10⁻¹⁶, and `results.json` by at most 3 × 10⁻¹³ (the Wald statistic).
  - `snakemake -n causal`, `-n hierarchical` and `-n pregate` report nothing to do.
- **Drive:** 17 exported CSVs remain in Reenu's Drive folder `ncap_maiac_gee`: the 15 yearly tables and the 2 one-month pilots (the first pilot attempt, to assets, wrote nothing). Each raw file's Drive id and md5 are in the manifest; Reenu may delete the folder.

## 2026-10-03: Phase 8b approved (Reenu); closing items

**DEC-188 (EXPLORATORY, added after Phase 8b's results were seen, at Reenu's request): ACAG vs AOD in the units that did not gain a monitor, on their own.**
- **Question.** If ACAG and AOD also diverge in the 31 kept treated units that gained **no** monitor in 2019–2024, then monitor leakage cannot explain the overall ACAG–AOD difference, because those units had no new monitors to calibrate to. Another explanation would be needed, e.g. the AOD–surface PM2.5 relationship differing between NCAP and control units.
- **Order of events, stated plainly.** Both group estimates were already printed in §12's monitor-gain table, and I had seen them: not gained, AOD −0.4% and ACAG +7.1%. This entry adds no new estimate. It adds an explicit comparison, a classification and a conditional sentence. That is why it is labelled exploratory and kept out of DEC-180's classifications.
- **"Diverge" is defined with the existing DEC-180 Q1 rule, nothing new:** apply Q1 to the not-gained group's AOD estimate, with ACAG on the same units as the yardstick.
  - *Diverge* = "rise not reproduced" or "opposite direction".
  - "Uninformative" = AOD too noisy to tell; then the conditional sentence is not written.
  - "Rise also in AOD" = no divergence.
  - "Not testable" if ACAG's not-gained estimate is not positive with a CI excluding 0.
- **Shown beside it, for information:**
  - the same classification for the gained group;
  - the paired difference ACAG − AOD per group, with its SE from the per-replication differences. The two specifications have the same units, cohorts, cells, controls and seed, so the 500 placebo sets are identical draws. This is checked: the first replication's ATTs differ, but the draw design is identical by construction.
  - The paired difference mixes two quantities (log PM2.5, log AOD), so it is information only. The reading stays direction only (DEC-180).
- **Where:** `data/processed/causal/maiac/exploratory_notgained.json` (written by `python -m src.causal.maiac summarise`), and a new subsection §12f, labelled exploratory. Nothing else changes: Q1, Q2, H1–H5 and the robustness count stay as they are.

**DEC-189 (2026-10-03): DEC-188's result; the Drive folder is kept; Phase 8b closed.**
- **Exploratory (DEC-188), in the 31 kept treated units that gained no monitor:** AOD −0.4% (95% CI −2.3% to +1.6%), ACAG on the same units +7.1% (+4.7% to +9.6%). Under DEC-180's Q1 rule this is "rise not reproduced", so **ACAG and AOD diverge there**.
  - §12f therefore states that monitor leakage cannot explain the overall ACAG–AOD difference, since those units had no new monitors. Another explanation would be needed, for example the AOD–surface PM2.5 relationship differing between NCAP and control units, or something else in ACAG's processing.
  - **For information:** the paired ACAG − AOD difference is +0.0725 log units (+0.0448 to +0.1003) in the not-gained units and +0.0152 (−0.0036 to +0.0340) in the gained units. The gained group also classifies as "rise not reproduced", narrowly: its AOD interval ends at +2.7%, just below ACAG's +2.8%.
  - So the ACAG–AOD difference is largest where no monitors were added. Leakage as hypothesised would pull ACAG down where monitors *were* added. §12f says that this weakens Q2's "gap absent from AOD" as evidence for leakage specifically. Q2's classification stands as registered, and nothing else changes.
  - The membership of `aod_primary` and `acag_aod_sample` was asserted identical in code before the replications were paired.
- **The Drive folder `ncap_maiac_gee` stays until the project ends,** as a backup of the raw export (Reenu). This replaces DEC-187's "Reenu may delete the folder". The data card says so.
- **Workflow:** `causal_maiac_summary` also writes `exploratory_notgained.json`, and the report reads it. The chain was rerun through Snakemake. Rebuilding Phase 8b's panels and specs gave the same spec hashes, so no SDID was recomputed. Figure 7's PNG was unchanged; its SVG differed only in date and element ids and was restored to the committed file (DEC-094/160).
- **Phase 8b approved by Reenu on 2026-10-03.** Next: Phase 9.

## 2026-10-03: Phase 9 (figures and dashboard). Rules written BEFORE any figure is changed

Phase 9 estimates nothing. It redraws figures from outputs that already exist (Phases 3–8b) and adds one supplementary figure (ACAG vs AOD) from Phase 8b's existing estimates. The wording rules of DEC-151/154 and the Phase 8 extension bind every title, label, note, caption and alt text: **H1 is not identified by this design, so nothing is an effect of NCAP.** Written and pushed before any figure module is edited.

**DEC-190: The figure set, and where figures are built.**
- **Eight main figures** (proposal visualisation plan), each answering one question. The proposal's questions are reworded where they presuppose an effect:
  1. `fig1_decomposition`: how much of a city's reported improvement survives weather and network-composition correction, and how did its satellite PM2.5 move relative to comparison cities? (DEC-191)
  2. `fig2_station_entry`: did the measuring instrument change under the programme?
  3. `fig3_deweathered_annual` is the main view, because the question is about *annual* numbers; the monthly views `fig3_deweathered` and `fig3_deweathered_grange_carslaw` are 3b and 3c. Question: how much does weather move annual numbers?
  4. `fig4_event_study`: were pre-trends parallel, and when did listed and comparison centres diverge? (The proposal's "when did any effect appear?" is reworded.)
  5. `fig5_city_map`: where did satellite PM2.5 rise or fall relative to comparison units after listing? (The proposal's "where did NCAP work?" is reworded, as PROGRESS required.)
  6. `fig6_shrinkage`: how uncertain are city-level estimates and their ranks?
  7. `fig7_mechanism`: is the ground PM10/PM2.5 pattern consistent with dust control?
  8. `fig8_quality_heatmap`: how trustworthy is the network over time?
- **Supplementary:**
  - S1 `figS1_levels` (role unchanged);
  - **S2 `figS2_aod_acag`** (new): ACAG PM2.5 vs raw MAIAC AOD relative changes, every Phase 8b specification and the monitor-gain split (DEC-195);
  - **S3 `figS3_decomposition_cities`**: the old per-city view, every H4 city, both pollutants, **alphabetical**;
  - **S4 `figS4_decomposition_pm10`**: the PM10 cross-city summary, which leaves figure 1.
  - The four Phase 3 EDA figures stay as exploratory E1–E4 under their file names.
- **Retired:** `fig1_decomposition_cities` (→ S3) and `fig1_decomposition_policy` (→ figure 1 and S4) are deleted. `fig1_decomposition` is overwritten by the final figure 1.
- **Workflow:**
  - Every figure rule moves to `workflow/rules/viz.smk`, and figure modules read only files already on disk.
  - Data rules no longer draw figures. `src/viz/eda.py` keeps its tables; its drawing functions move to `src/viz/fig2_station_entry.py`, `fig8_quality_heatmap.py` and `eda_figures.py`.
  - The `fig1`, `fig1_policy`, `fig3`, `fig4`, `figS1`, `fig5`, `fig6` and `fig7` rules move out of `composition.smk`, `normalise.smk`, `causal.smk` and `hierarchical.smk`.
  - The phase targets (`eda`, `causal`, `hierarchical`) drop their figure inputs. `viz` collects every figure, and the pre-gate figures (2, 3, 8, E1–E4) also join `pregate`. Rules that read gated outputs check the gate.
  - Editing `eda.py` marks its outputs stale by modification time. Its tables must come out content-identical; downstream outputs are then marked current with `snakemake --touch`, as in DEC-108/134/153, and logged at the end of the phase.

**DEC-191: Figure 1, the main figure. DEVIATION from DEC-150's design of the pooled view, dated 2026-10-03.**
- **Pollutant: PM2.5 only.** Satellite PM2.5 exists only for PM2.5, and one pollutant keeps the figure readable at slide size. The PM10 summary moves to S4, with unchanged content.
- **Panel (a), cross-city summary.** The existing waterfall over the 18 H4 PM2.5 cities: reported → unmodelled change → modelled weather → network composition → weather- and composition-corrected change (DEC-126/136). GAM with 95% cluster-bootstrap CIs, LightGBM beside it.
- **Panel (b), the relative change against comparison cities, on its own axis (not a waterfall step).**
  - Layer A restricted to these cities' units (+3.8% in Phase 7), labelled "relative change against comparison cities (satellite PM2.5)" and "not identified as an effect of NCAP".
  - Below it, the **shrunken** city-level relative change of each illustrative city (Phase 8, `city_shrunken.csv`), with its 95% CrI.
- **What changes from DEC-150, and why.**
  - DEC-150 was written before H1's verdict. It drew the Layer A estimate as a step down from the corrected level, plus a "remaining change" bar (corrected minus that step) described as "the part not attributed to NCAP".
  - After DEC-151 nothing is attributed to NCAP. Subtracting the estimate from the corrected change presupposes the attribution the design failed to identify.
  - The two quantities are also on different bases: a ground change 2018 → 2025 in % of 2018, against a satellite difference from a synthetic comparison averaged over 2019 and 2021–2024. They do not belong on one stacked axis.
  - Hence: no step, no "remaining change" bar, and a separate axis with its own label. No number changes.
- **Panel (c), illustrative cities, chosen by a rule on network metadata only.**
  - Among the 18 PM2.5 H4 cities, in each region present (coastal, IGP, peninsular/other), take the city with the most stations valid in 2025 (ties: more panel stations, then alphabetical).
  - Then add the city with the most stations valid in 2025 not yet chosen, for four in total.
  - Result: Chennai, New Delhi, Hyderabad and Kolkata, drawn **alphabetically**.
  - Why station counts: composition can matter only where the network changed, and the rule uses no outcome.
  - *Stated plainly:* I had seen every city's decomposition (`composition_report.md` §1d) before writing this rule. The rule is fixed on station counts, but the choice of rule is not blind.
  - Each city panel shows the same steps, the station-bootstrap CI where the city has more than one station in a stratum, and LightGBM beside the GAM.
- **Wording on the figure.** Never "policy", "policy effect" or "policy-attributable". The step names are "reported", "unmodelled change", "modelled weather", "network composition" and "corrected". Panel (b) carries "not identified as an effect of NCAP (registered pre-trend test failed)".

**DEC-192: Style rules, as implemented in `src/viz/style.py`.**
- **One palette.**
  - The validated categorical order: blue, orange, aqua, yellow. Re-run on 2026-10-03: worst adjacent CVD ΔE 9.1, normal-vision 22.9. Aqua and yellow are below 3:1 contrast, so every chart using them carries direct labels or a legend plus distinct markers.
  - One sequential blue ramp.
  - One diverging blue–grey–red pair with a grey midpoint, now defined in `style.py` and used by figure 5.
- **One font** (DejaVu Sans), with sizes raised for slides: base 10 pt, ticks 9, panel titles 10.5, figure titles 12, notes at least 8 pt.
- **Every figure has:**
  - a title "Figure N." that states its question;
  - units on every axis (µg/m³, or % with what it is a % of);
  - uncertainty on every estimate;
  - colour never the only carrier of meaning.
- **Fixes this needs:**
  - **Figure 2:** entry periods reduced to three (before NCAP ≤ 2018, 2019–2021, 2022–2025), each with its own marker shape as well as colour.
  - **Figure 5:** in panel (a), marker shape shows the 95% CrI class (▲ entirely above 0, ▼ entirely below, ● spans 0). The land fill no longer equals the diverging midpoint.
  - **Figure 8:** a line panel beside the heatmap shows the median reliability score per year, with an interquartile band and the number of stations, so the trend is readable without colour.
- **No ranking of cities.** Every named per-city list is alphabetical (figure 1c, S3). Figure 6 keeps its unnamed units sorted by shrunken estimate, and its rank intervals, because that figure's question is how uncertain ranks are. No unit is named there.
- **In-figure notes are short:** scope, the binding caveat, sources. The full explanation is the caption (DEC-194).
- **Byte-stable SVGs** (the DEC-094 open item): `svg.hashsalt` is fixed and there is no date metadata.

**DEC-193: An automated wording check on every figure and caption.**
- `src/viz/wording.py` scans all text drawn in a figure (titles, labels, ticks, notes, legends) before it is saved, and every caption and alt text. It **refuses to save** on a banned phrase:
  - "policy effect", "policy-attributable", "attributable to NCAP" or "to the programme", "impact of NCAP", "NCAP caused/reduced/cut/lowered/improved/worked", "due to NCAP", "because of NCAP", "thanks to NCAP";
  - "effect(s) of NCAP" unless negated in the same clause ("not an effect of NCAP", "not effects of NCAP", "not identified as an effect of NCAP");
  - "counterfactual": the comparison is a synthetic or comparison unit, and the word implies identification;
  - "best", "worst", "top N" and "league table" (ranking language).
- The same check runs on the dashboard text in Part B. Unit tests use synthetic strings.

**DEC-194: Captions and alt text are generated.**
- Each figure module returns, beside the figure, its number, question, caption and alt text. Every number in them is formatted from the same pipeline outputs the figure draws (hard rule 3).
- `S.save` writes them to `reports/figures/<name>.json`.
- `python -m src.viz.catalogue` assembles `docs/figures.md` (generated): one section per figure with file links, question, caption and alt text, plus the wording-check result.
- Alt text says, in one to four sentences, what the chart shows and its main reading. Where a caveat binds, it ends with it.

**DEC-195: Figure S2, ACAG vs raw MAIAC AOD.**
- **Rows:**
  - the five Phase 8b specifications: primary, non-monsoon, area-weighted, relaxed QA, and the 17 Layer B units;
  - then the monitor-gain split on the primary: gained, not gained, and gained − not gained.
- **Each row** shows ACAG PM2.5 on the same units (filled circle) and AOD (open square), each with its 95% CI. The pre-specified classification is written at the row's end: Q1 per specification, Q2 for the difference (DEC-180). The not-gained row also carries DEC-188's exploratory label.
- **One shared % axis.** DEC-180's rule itself reads the AOD interval against ACAG's estimate on a common % scale (the yardstick). The axis label and title state "AOD, not PM2.5: direction only". No ACAG–AOD difference is plotted as a quantity.
- **Caveats on the figure:** H1 is not identified; AOD is a column measure; the AOD sample is 95 of 113 treated units.

## 2026-10-03: Phase 9 Part A (figures) built (rules DEC-190 to DEC-195, pushed in `09209e7` before any figure changed)

**DEC-196: Part A results, implementation notes and workflow. No estimate was made or changed.**
- **What exists.** 18 figures, each with PNG, SVG and a caption/alt-text sidecar, listed in the generated `docs/figures.md`:
  - eight main figures: 1, 2, 3 (with 3b and 3c), 4–8;
  - four supplementary: S1–S4;
  - four exploratory: E1–E4.
- **Figure 1's illustrative cities, by DEC-191's rule:** Chennai (coastal), New Delhi (IGP), Hyderabad (peninsular/other), then Kolkata (most stations in 2025 not yet chosen). Drawn alphabetically.
- **The wording check (DEC-193) caught three things before any file was saved:**
  - "counterfactual" in figure 4's y-axis label, now "comparison centres";
  - "attributable to NCAP" in the notes of figures 5 and 6, now "not identified as effects of NCAP";
  - "best-quality QA" in figure S2. This is MAIAC's own name for a QA level (DEC-175), not ranking language, so the ranking pattern now excludes "best/worst" followed by "quality". A test covers the exception.
- **Alt text and captions are generated, and every factual claim in them was checked against the tables before it was written as code:**
  - E1's draft alt text said the IGP is highest in every month. That holds for the satellite series but not the ground one. The sentence is now computed per series.
  - Figure 3's caption gives the median over cities of each city's median weather part of the year-on-year change (5.3%). This is a different statistic from DEC-118's pooled 5.1%, and the caption names it exactly so the two do not look inconsistent.
- **Layout fixes after looking at each render** (no number affected):
  - figure 1: panel (b) labels clipped; the caveat collided with a panel title;
  - figure 2: legend over a label; the note over an axis label;
  - figure 5: the CrI legend moved off the map;
  - figure 8: the colour bar collided with the year ticks;
  - S2: block labels moved to the top of each block.
- **Workflow (as DEC-190 stated in advance):**
  - `src/viz/eda.py` now writes only tables. Rerun, all six EDA CSVs and `station_year.parquet` came out byte-identical to the committed run.
  - The data stages were then marked current with `snakemake --touch hierarchical` plus the `eda`, `composition` and `pre_period_checks` stubs (as DEC-108/134/153). Every figure rule then ran through Snakemake (`snakemake --cores 1 viz viz_pregate`; log `data/interim/logs/snakemake_phase9_partA.log`).
  - `composition_report.md` was regenerated, because its text named the retired figure files. Only those two lines changed.
  - Afterwards `snakemake -n pregate` has nothing to do, and `snakemake -n all` lists only the Phase 10 `report` stub and `all`.
- **Byte reproducibility (the DEC-094 open item, for figures):** re-running every figure module gives 54 of 54 figure files byte-identical (PNG, SVG, JSON). The fix is a fixed SVG hash salt, no SVG date and no PNG "Software" tag. Tables and GeoPackages are not covered; that stays open for Phase 10.
- **Tests:** `tests/test_viz.py`, 26 synthetic tests covering:
  - banned and allowed wording, the clause rule, per-label checking;
  - byte-identical saves, and refusal to save on banned wording;
  - catalogue order, a missing sidecar, re-checked wording;
  - DEC-191's city rule.
  
  The full suite has 248 tests, all passing (`data/interim/logs/pytest_phase9_partA.log`).

## 2026-10-03: Phase 9 Part A reviewed (Reenu); Part B rules written BEFORE any dashboard code

**DEC-197: Reenu's Part A rulings, and the figure fixes they required. No number changed.**
- **DEVIATION from DEC-150, dated 2026-10-03 (approved by Reenu): figure 1 has no "policy" step and no "remaining change" bar.**
  - DEC-150 was written on 2026-10-01, before H1's verdict. It drew the Layer A restricted estimate as a step down from the corrected ground change, followed by "remaining change = corrected − that step, the part not attributed to NCAP".
  - DEC-151 then found H1 not identified, so nothing can be attributed to NCAP. Subtracting the estimate presupposes the attribution the design failed to identify.
  - The two quantities are also on different bases: a ground change from 2018 to 2025, in % of 2018, against a satellite difference from a synthetic comparison averaged over 2019 and 2021–2024. They cannot be stacked on one axis.
  - The estimate is therefore drawn on its own axis (DEC-191), labelled "relative change against comparison cities … not identified as an effect of NCAP". It will be listed with the deviations in the final report.
- **Figure 6 stays, with no city named** (Reenu). Its subtitle now reads: "Purpose: to show that city ranks are too uncertain to be meaningful, so units are deliberately unnamed. Not identified as effects of NCAP: the registered pre-trend test failed."
- **Figure 1's illustrative-city rule is accepted** (Reenu). The panel (c) heading now says "chosen by a station-count rule written after viewing results (DEC-191); every city in Fig. S3". The caption says the same.
- **Figure 3:** the annual view is main (Reenu agreed).
- **Fixes:**
  - **Figure 1 (a) and (c), and S4, which shares the drawing code:** each removed part is labelled with the step it makes, "+2.9 pp removed" (the sign of −contribution), so the label matches the bar's direction. Totals stay as % changes. This applies in the tick labels, the caption and the alt text. The alt text's "largest part removed" is computed, not typed.
  - **Figure 1 legend:** the dark bars are "Reported and corrected change (correction uses the GAM, the primary model)". The reported change is raw data, not a GAM output.
  - **Figure 4:** "l = −9 … −2" and "l = 0 … +5" now read "relative years −9 to −2" and "relative years 0 to +5", in the subtitle and the caption.
- **Checks:**
  - every figure passed the wording check when saved, and the catalogue passed it again;
  - a rebuild of every figure module gave 55 of 55 files byte-identical (54 figure files and `docs/figures.md`);
  - `snakemake -n pregate` and `-n viz` have nothing to do.

**DEC-198: The site gets its own small environment and lock file; the analysis lock is not touched (Reenu).**
- `envs/site.yml` holds conda-forge `quarto` pinned to 1.9.38 (the newest on conda-forge on 2026-10-03), and nothing else.
- `envs/site-lock.yml` is made with `conda-lock` for win-64 and linux-64. It installs as the environment `ncap-site`.
- **The site runs no code.** Every page is plain Markdown with pre-rendered images and CSV downloads, so Quarto needs neither Python nor Jupyter. All content is precomputed in the analysis environment by `python -m src.dashboard.build`.
- **`conda-lock.yml` (the analysis lock) and `environment.yml` must not change.** This is checked with `git diff` before the commit and stated in the phase note.

**DEC-199: What the dashboard shows, and what it does not.**
- **Units.** One page for each of the 113 NCAP units of Layer A (GHSL urban centres holding an NCAP city), named by their NCAP cities. A shared polygon lists all its member cities, e.g. "Delhi, Faridabad, Ghaziabad, Noida". The 10 NCAP towns with no GHSL centre have no page; the index lists them as "not covered" with the reason (DEC-063).
- **Order.** Cities are listed alphabetically on the index and in a select box, never ranked or sorted by any result. No page shows a rank or rank interval, a p-value or a "significant" label.
- **Each page shows, all precomputed:**
  1. **Facts:** member cities; state; region; listing year (cohort); 2015 population; whether a monitor was added inside the polygon in 2019–2024 (DEC-096).
  2. **Ground PM2.5 and PM10, where ground data exist** (85 of 113 units). Annual series, 2015–2025:
     - raw all-station mean (as reported, after the audit's cleaning);
     - deweathered all-station mean (GAM, the primary model), with the GAM–LightGBM range as a band;
     - **composition-corrected** = the 2018 balanced panel, deweathered, from 2018. It exists for 20 units; elsewhere the page says no station was valid every year 2018–2025.
     - The number of stations behind each year is shown.
     - Source: `data/processed/composition/trends.parquet` (primary version), identical to `deweathered/city_year.parquet` for the all-station series (checked).
  3. **Satellite PM2.5:** the unit's annual population-weighted ACAG V5.GL.06 mean, 2010–2024, with the listing year marked. Descriptive.
  4. **City-level relative change:** the unit's own SDID estimate against its synthetic comparison, with ± 1.96 × the placebo SE (DEC-162), and its shrunken posterior mean with the 95% credible interval (DEC-163). The average city-level relative change is shown for reference.
     - Every page carries the fixed caveat, in a box: "H1 is not identified by this design: the registered pre-trend test failed. NCAP units' satellite PM2.5 did not fall relative to comparable units; the estimates point to a relative rise of about 3–5%. Nothing on this page is an effect of NCAP." (DEC-154).
  5. **Data quality:** per year, the number of PM2.5 and PM10 stations reporting inside the polygon and their median reliability score (0–100, DEC-073).
- **Not shown:**
  - the synthetic comparison's own trajectory. The proposal's "counterfactual trend" is not saved per unit, and drawing it would invite reading the gap as an effect;
  - Layer B per-city ITS values (Phase 7 keeps them descriptive only);
  - AOD.
- **Figures:** one PNG per page (150 dpi), drawn with `src/viz/style.py`, so the same palette, font, units-on-axes and uncertainty rules apply. Each has generated alt text.
- **Downloads:** CSVs per dataset under `dashboard/data/`, with every number on the pages:
  - ground series (derived from the CPCB mirror; ODbL 1.0, share-alike);
  - satellite series;
  - city-level estimates;
  - quality.
- **Wording:** every generated page passes `src/viz/wording.py` (DEC-193); the build refuses to write otherwise. A test re-checks the committed pages, so CI checks them too.

**DEC-200: The "About the data" page, with attributions verified on 2026-10-03 (hard rule 2).**
- **CPCB data via the `india-cpcb-aqi` mirror (Vonter), ODbL 1.0.**
  - The mirror README requires attribution and share-alike: "If you publicly use any adapted version of this database, or works produced from an adapted database, you must also offer that adapted database under the ODbL".
  - So the page says: "Contains information from india-cpcb-aqi, a mirror of CPCB's data repository, made available under the ODbL 1.0; some contents © CPCB. The ground-derived data on this site are made available under the ODbL 1.0."
- **ERA5 (Copernicus).** The CDS pages give a CC-BY licence (since 2 July 2025) and DOIs 10.24381/1cf1ad76 (hourly time series) and 10.24381/cds.f17050d7 (monthly means).
  - Notice: "Contains modified Copernicus Climate Change Service information (2026)".
  - Citation: Hersbach et al. (2020), *QJRMS* 146, 1999–2049, doi:10.1002/qj.3803.
- **ACAG SatPM V5.GL.06 (WashU), CC BY 4.0.** satpm.org asks for three citations:
  - van Donkelaar et al. (2021), *ES&T*, doi:10.1021/acs.est.1c05309;
  - Hammer et al. (2023), *RSE* 294, 113624, doi:10.1016/j.rse.2023.113624;
  - Zhang et al. (2025), *GMD* 18, 6767–6803, doi:10.5194/gmd-18-6767-2025.
- **GHSL UCDB R2024A (JRC), CC BY 4.0, © European Union 1995–2026.** The licence text is in our download. Citation: Mari Rivero et al. (2026), GHS-UCDB R2024A, doi:10.2905/JRC.05RDPR0. The page states that changes were made (polygons joined into units, population-weighted means).
- **MODIS MAIAC (NASA), openly shared without restriction** (EOSDIS policy). Citation: Lyapustin & Wang (2022), MCD19A2 v061, NASA LP DAAC, doi:10.5067/MODIS/MCD19A2.061. The page says AOD appears only in the report, not in the city pages.
- **OpenAQ.** The terms page says "Attribution to OpenAQ as the source data is also required when using OpenAQ services", and the original providers must be acknowledged. OpenAQ supplied January–March 2026 (not shown on the dashboard) and station coordinates.
- **Also listed,** because the pages or their maps use them:
  - DataMeet boundaries (CC BY 4.0, as their data card says);
  - GHS-POP R2023A weights (CC BY 4.0).
- **Links:** the OSF registration https://osf.io/jksne/ and the repository https://github.com/breenu/ncap-evaluation.
- **Code licence:** none has been chosen yet (open item). The page says so, rather than implying one.

**DEC-201: Build and deployment.**
- **Sources.** `python -m src.dashboard.build` (gated; analysis environment) writes the site sources to `dashboard/`:
  - `_quarto.yml`, `index.qmd`, `about.qmd`;
  - `cities/<slug>.qmd`, `cities/img/<slug>.png`;
  - `data/*.csv`.
- **The generated sources are committed.** `data/` is not in git, so CI cannot regenerate them. The rendered `dashboard/_site/` is gitignored.
- **Snakemake:** rule `dashboard` in `viz.smk` (gated), part of `viz`. Rendering is a separate rule, `dashboard_render` (`conda run -n ncap-site quarto render dashboard`). It is not part of `all`, because it needs the site environment.
- **Deployment:** `.github/workflows/pages.yml`.
  - It runs on pushes to `main` that touch `dashboard/**` or `envs/site*`, and on manual dispatch.
  - It installs `ncap-site` from `envs/site-lock.yml`, renders, and deploys with GitHub's Pages actions.
  - Nothing is pushed to a `gh-pages` branch.
  - It deploys only after Reenu sets the repository's Pages source to "GitHub Actions"; until then the deploy job fails, and that is expected.
- **Static only:** no server, no live data, no analytics, no external scripts beyond what Quarto bundles.

## 2026-10-03: Phase 9 Part B (dashboard) built (rules DEC-197 to DEC-201, pushed in `406f544` before any dashboard code)

**DEC-202: Part B results, implementation notes and workflow. No estimate was made or changed.**
- **Site environment (DEC-198).** `envs/site.yml` holds `quarto=1.9.38`. `envs/site-lock.yml` (conda-lock, win-64 and linux-64) locks 23 packages: Quarto with its bundled pandoc 3.8.3, deno, dart-sass, esbuild and typst, plus the platform runtime libraries. It installs as `ncap-site` with `conda-lock install -n ncap-site envs/site-lock.yml`. `conda-lock.yml` and `environment.yml` are unchanged (`git diff` empty).
- **What was built (DEC-199).** `python -m src.dashboard.build` writes:
  - 113 city pages (one per NCAP unit, A–Z) with a four-panel PNG each (120 dpi) and generated alt text;
  - the index (a select box and an A–Z list; the 10 towns without a GHSL centre listed as not covered);
  - "About the data";
  - four CSV downloads.
  - The sources are 17 MB in `dashboard/`; the rendered site is 21 MB.
- **Coverage, generated on the index:** ground data exist for 85 of the 113 units, and a station valid every year 2018–2025 for 20.
- **The caveat on every page** is DEC-154's sentence produced by `src.causal.causal_report.wording()` (the range "about 3–5%" is computed from the estimates, not typed), plus a fixed line that nothing on the page is an effect of NCAP. A test checks it is on all 113 pages.
- **Precision fixes made while checking the pages** (before the first commit of the site):
  - **Averaging years.** A city's relative change averages its own cohort's post-years: "2019 and 2021–2024" for the 89 units listed in 2019, "2021–2024" for the 24 listed in 2020–2021. The first draft printed the 2019 cohort's years on every page.
  - **Station counts.** The quality table counts stations with *any* data that year, while the charts count *valid* stations. The table heading now says so. In Kolkata in 2018, for example, the table shows 4 stations with data and the chart 1 valid station.
  - **Score summary.** The summary score is labelled as the median of the yearly medians.
- **Wording.** Every generated page and every city figure passed `src/viz/wording.py`. The tests re-check the committed pages:
  - the wording check;
  - the caveat on every page;
  - the A–Z order in both the list and the select box;
  - no rank wording, except the page's own "cities cannot be ranked";
  - every attribution and DOI that DEC-200 requires.
- **Rendering.** `quarto render dashboard` in `ncap-site` produced 115 pages with no Quarto warnings. A link check over the rendered HTML found 0 broken internal links. Headless-browser screenshots of the index, a city page and the About page were inspected; the city chart was then widened to the page column.
- **Reproducibility.** A second build gives 230 of 230 site source files byte-identical. All figure rules ran again through Snakemake (`style.save` gained an output-directory argument), and every figure came out byte-identical to the committed files. Afterwards `snakemake -n viz` and `-n pregate` have nothing to do, and `snakemake -n all` lists only the Phase 10 `report` stub (log `data/interim/logs/snakemake_phase9_partB.log`).
- **Tests:** `tests/test_dashboard.py`, with 6 tests. The full suite has 254 tests, all passing (`data/interim/logs/pytest_phase9_final.log`).
- **Deployment (DEC-201).** `.github/workflows/pages.yml` renders the committed sources with the site lock and deploys through GitHub's Pages actions. It needs Reenu to set the repository's Pages source to "GitHub Actions"; until then the deploy job fails.

## 2026-10-03: Phase 9 approved (Reenu); the deployed site checked

**DEC-203: Phase 9 approved by Reenu (2026-10-03). The dashboard leaves out the synthetic comparison's trajectory: a DEVIATION from the proposal's dashboard description, dated 2026-10-03.**
- **What the proposal says.** The dashboard should show a city's "raw, deweathered, composition-corrected and counterfactual trends".
- **What is done instead.** Each city page shows the raw, deweathered and composition-corrected ground trends, the satellite PM2.5 series, and the city-level relative change with its interval and its shrunken estimate. It does not draw the synthetic comparison's trajectory.
- **Why (Reenu agreed, as DEC-199 proposed):**
  - H1 is not identified (DEC-151). A drawn gap between a city and its "counterfactual" would be read as an effect of NCAP, which the design failed to establish.
  - The per-unit synthetic trajectories were not saved in Phase 8 (`unit_sdid_*.parquet` holds estimates, not paths). Drawing them would mean re-running 113 per-unit SDIDs for a view the wording rules would forbid labelling as a counterfactual.
- **Effect:** none on any number; it will be listed with the deviations in the final report.
- **Also decided:** the repository size is acceptable, and the code licence is decided in Phase 10.
- **Pages:** Reenu enabled GitHub Pages (source: GitHub Actions). A manual run of the `dashboard` workflow deployed the site to https://breenu.github.io/ncap-evaluation/ (run 37112646867).

**DEC-204: Check of the deployed site (not the local build), and one fix: city charts were unreadable at phone width.**
- **Links.**
  - A crawl of the live site requested every internal page and asset reachable from the index: 249 URLs, including 116 HTML pages, every chart, every CSV and Quarto's own files. All returned 200.
  - The 14 external links all resolve. Wiley and ACS answer a scripted request with 403 after the DOI has correctly redirected to the article page, so those two are publisher bot-blocking, not broken links.
- **Caveat and content.** All 113 city pages carry the "not identified" caveat, the chart and its alt text. The About page carries every attribution and DOI of DEC-200.
- **Mobile check: how it was done.** Headless Edge on Windows will not lay out a page narrower than 504 px (measured), so a "390 px" screenshot is really a clipped 504 px layout. The pages were therefore loaded inside a 390 px-wide iframe, which gives them a true 390 px viewport.
- **Mobile check: what it found.**
  - **Passed:** text, tables, the navigation (collapsed to a menu) and the About page fit with no sideways scrolling.
  - **Failed:** each city's 2 × 2 chart shrank to about 350 px wide, which made its text unreadable.
- **Fix.**
  - Each city also gets a one-column chart: the same four panels stacked, about 4 in wide, at 130 dpi. Pages serve it through `<picture><source media="(max-width: 600px)">`, so phones get the stacked chart and wider screens keep the 2 × 2 one. The alt text covers both.
  - The page text now refers to "the first two charts", "the third chart" and "the fourth chart" instead of positions that differ between layouts.
  - Same data and same numbers; the images add about 17 MB to `dashboard/`.
- **Test:** every committed city page must serve both images, and both files must exist (`tests/test_dashboard.py`).
- After redeployment the live checks were repeated (DEC-205).

**DEC-205: The deployed site re-checked after the phone fix (2026-10-03). One further defect was found and fixed; the checks then passed.**
- **Defect: the phone charts were never published.**
  - The first redeploy (`a139fe3`) served all 113 phone charts as 404. Quarto copies images it finds in Markdown or in `img src`, but not ones referenced only from a raw-HTML `<source srcset>`.
  - Fix: `_quarto.yml` declares `cities/img/*-narrow.png` as project resources (`e30a829`). A test now requires that declaration.
- **Phone chart text was still small** (about 8 px at a 390 px viewport). The phone chart's fonts are now 30% larger at the same width (`dc29306`). The desktop charts are byte-identical to before.
  - While making this change, a font-scale variable was briefly shadowed by a loop counter. The resulting oversized labels were caught by comparing the desktop charts with their committed bytes, before anything was pushed.
- **Final live checks** (deploy run 37115838189):
  - **Links:** 362 internal URLs, including all 226 chart images, return 200. The 14 external links resolve (Wiley and ACS refuse scripted requests after a correct DOI redirect).
  - **Caveat and content:** all 113 city pages carry the caveat, the chart and the alt text, and the About page carries every DEC-200 attribution.
  - **Deployment matches the commit:** every live chart file is byte-identical to the committed one.
  - **Phone layout:** at a true 390 px viewport (inside an iframe, because headless Edge on Windows will not lay out below 504 px) the pages fit with no sideways scrolling, and phones get the one-column chart with legible text.
- **Tests:** 7 dashboard tests (one new).

## 2026-10-03: Phase 10 (report and release), Part A. Rules written BEFORE any report text or code

Phase 10 estimates nothing. It writes the report, the results summary, the policy brief and a slide, chooses licences, cleans the public repository and checks that everything rebuilds from raw data. My instructions for it (2026-10-03): every written document is in my first person, as sole author; the wording rules of Phases 7–9 apply everywhere (nothing is an effect of NCAP, the "H1 not identified" verdict sits beside every causal estimate, no city is ranked); there are four checkpoints (A structure, B writing, C repository clean-up, D clean-clone rebuild), each pushed for my review.

**DEC-206: How the report is built (proposed at the Part A checkpoint; Part B builds it only after my approval).**
- **Sources.** `reports/report.qmd` (technical report), `reports/summary.qmd` (one page), `reports/policy_brief.qmd` (two pages) and a Quarto project file `reports/_quarto.yml`. The outline is `reports/report_outline.md`.
- **No hand-typed results (hard rule 3).**
  - The prose is written by hand, but every number in it is a Quarto variable (`{{< var … >}}`) read from `reports/_variables.yml`.
  - That file is written by `python -m src.report.values` (analysis environment `ncap`, gated) from the processed outputs the phase reports already read.
  - Tables are generated as Markdown under `reports/_generated/` and included with `{{< include >}}`.
  - The fixed H1 sentence comes from `src.causal.causal_report.wording()`, as on the dashboard.
- **Checks (`tests/test_report.py`).**
  - No result-like number in the prose outside a variable. Years, section, figure, table and DEC numbers, and H1–H5 are allowed.
  - Every variable the prose uses exists in `_variables.yml`.
  - Every DECISIONS entry marked "DEVIATION" appears in `reports/deviations.md`.
  - `src/viz/wording.py` runs on the prose, the variables and the generated tables of every document, and on the slide, as it already does on figures and the dashboard.
- **Rendering.**
  - `quarto render reports` in the site environment `ncap-site` (DEC-198) produces HTML and PDF.
  - The PDF is made with Typst, which ships inside the locked Quarto 1.9.38 (`envs/site-lock.yml`). So neither lock file changes and no LaTeX distribution is installed.
  - The report needs no Python at render time, as with the dashboard.
- **Snakemake.** The `report` stub becomes `report_values` (part of `all`) and `report_render` (which calls `ncap-site`, like `dashboard_render`).
- **Slide.** Figure 1 panel (a) alone, with one takeaway line built from the same values, made by the existing figure module with a slide option, so the style rules and the wording check apply unchanged.
- **Licences (my choice, to be checked against each source's terms in Part B before anything is applied).** MIT for code. CC BY 4.0 for the report text and figures, with the ODbL attribution notice wherever a figure uses ground-derived data. ODbL 1.0 for ground-derived data (DEC-037, DEC-200). Any conflict is reported to me before a licence file is written.

**DEC-207: The deviations list (`reports/deviations.md`), included verbatim as the report's Appendix A.**
- **What it covers.** The registration promised to list every deviation, dated and justified. The list goes further than the entries labelled "DEVIATION", so that every judgement call touching a registered rule can be seen with its timing. Six groups:
  - A, deviations from the registered plan (DEC-109, DEC-110, DEC-116);
  - B, registered analyses not carried out or not computable;
  - C, the clarifications posted on OSF on 1 October (DEC-127, DEC-135);
  - D, departures from rules fixed after registration, and from the proposal;
  - E, readings of registered text that was incomplete or could not be applied literally;
  - F, analyses added after registration.
- **Timing.** Every row states whether the decision came before or after the estimate it affects. The evidence is the commit that first recorded the decision (`git log -S` on `docs/DECISIONS.md`), set against the commit of the first result it governs (for example H4 in `132b788`, the first Phase 7 estimate in `655fb65`). Git shows when a rule was committed, not when a number was first looked at; the appendix says so.
- **A1 and A3 are listed as deviations although the registered text does not spell out the resampling scheme or the GAM's trend.** The registered plan refers to the proposal's deweathering method (Grange & Carslaw 2019) and fixes only the family-selection rule. Each change alters what the registered analysis would have computed, so I list it. DEC-109's statement that the registered plan "describes the deweathering as following Grange & Carslaw" is looser than the registered text; this entry records the more exact wording, and DEC-109 itself is not edited.
- **No result numbers.** The list holds dates, DEC numbers and commit hashes only, so it needs no generated values.

**DEC-208 (fact, found while compiling the list): the registered exploratory analysis "NO2 as a secondary pollutant" (plan §5) was never carried out.** NO2 was ingested and cleaned in Phase 3, and its units were checked (DEC-056), but no phase analysed it. It is listed as B3, "not carried out". Whether to run it before the report, as an exploratory analysis carried out after every other result was seen, or to leave it as a stated omission, is my decision at the Part A checkpoint.

## 2026-10-03: Phase 10 Part A reviewed (Reenu); Part B rules written BEFORE any report text or code

**DEC-209: My Part A rulings.**
- **Approved, with edits:**
  - The headline paragraph's first sentence is scoped to the cities I could check.
  - "All 113 NCAP urban centres" becomes "the 113 urban centres containing 121 of NCAP's 131 cities".
  - The sentence that satellite PM2.5 fell in both groups now comes before the relative-change estimate, so "a relative rise" cannot be read as pollution rising.
  - One sentence is added on the pre-specified Q2 result: the monitor-gain gap seen in satellite PM2.5 is absent from raw AOD, which is consistent with, but does not prove, the satellite product absorbing the new monitors.
  - The abstract uses the same wording.
- **The deviations list:**
  - Group C now says that a summary was posted on OSF and that the full set of readings is DEC-135.
  - C1 states that `29874cf` was pushed publicly on 1 October 2026, after H4 had been computed.
  - A new row, D5, records that figure 1(c)'s city rule was written after viewing every city's decomposition (DEC-191). Later group D rows are renumbered.
- **The PDF is made with Typst** (DEC-206).
- **Where the report goes:** the PDF is committed in `reports/` and attached to the v1.0 release; the HTML goes on the Pages site.
- **NO2 stays a stated omission** (B3, DEC-208). It is not run.
- **The OSF clarification:** the text I posted on 1 October 2026 replaces the local draft in `docs/osf/clarification_2026-10-01.md`. It differs from the draft: it states that `29874cf` was pushed after H4 had been computed, and that deviations are logged in DECISIONS.md.
- **For Part C:**
  - Every code comment that cites "CLAUDE.md hard rule N" is reworded to state the rule itself.
  - `docs/osf/test.pdf` is removed.
  - How DEC-019 is handled is still open; I decide at the Part C checkpoint.

**DEC-210: Part B build rules (implementing DEC-206).**
- **Values.**
  - `python -m src.report.values` (analysis environment, gated) writes `reports/_variables.yml` and the tables in `reports/_generated/`.
  - It reads the same processed outputs as the phase reports, reusing their loaders and decision functions (`src.causal.causal_report.load/decide/wording`, `src.hierarchical.report.load`, `src.causal.report_maiac.results`), so no rule is re-implemented.
  - Each value is stored already formatted, as the documents print it.
- **Figures.** Each figure's caption in the report is the caption the figure module generated (its JSON sidecar, DEC-194), copied into `_variables.yml`. Captions are therefore never retyped, and they have already passed the wording check.
- **Pages and the release.**
  - The HTML is published on the Pages site in Part C, when the site's links are revised.
  - The PDF is attached to the release in Part D.
  - Until my review of Part B, nothing new is deployed.
- **The slide.**
  - `python -m src.viz.fig1_decomposition --slide` writes `reports/figures/fig1_slide.{png,svg,json}`: figure 1 panel (a) alone, 16:9.
  - Its title is one takeaway line built from the same numbers as panel (a).
  - It is saved through `style.save`, so the wording check and byte-stability apply.
- **Length targets, measured on the rendered PDF:** the technical report 20–30 pages; the summary one page; the brief two pages.
- **Licences.**
  - Each source's terms are checked against my choices (MIT for code; CC BY 4.0 for text and figures, with the ODbL notice where figures use ground-derived data; ODbL 1.0 for ground-derived data).
  - Licence files are written only where no conflict is found. Any conflict is reported at the Part B checkpoint and is not applied.

## 2026-10-03: Phase 10 Part B (writing) built (rules DEC-206, DEC-209 and DEC-210, pushed in `5aeaaaa` before any report text or code)

**DEC-211: Part B results and implementation notes. No estimate was made or changed.**
- **What exists.**
  - The technical report (`reports/report.qmd`): 26 pages as PDF.
  - The results summary (`reports/summary.qmd`): one page.
  - The policy brief (`reports/policy_brief.qmd`): two pages.
  - The figure 1 slide (`reports/figures/fig1_slide`).
  - All three documents render to HTML and PDF from `reports/_quarto.yml` in `ncap-site`; the PDFs are made with Typst.
  - Appendix A is `reports/deviations.md`, included verbatim. The data-sources table, references and Appendices B–C are hand-written include files that hold facts about inputs and decisions, not results.
- **Where the numbers come from.**
  - `python -m src.report.values` writes `reports/_variables.yml` (537 values) and six tables in `reports/_generated/`.
  - It reuses the phase reports' loaders and decision functions, and reads method settings from `config/params.yaml`.
  - Figure captions are each figure's own generated caption (DEC-194).
  - While building it, three values first differed from the phase reports in definition (missingness in percentage points, the rank-interval width, the within-state dose spread). Each was corrected to the phase report's own definition before any text used it.
  - Values that a sentence already describes as a fall or as "below" are also stored unsigned (`_abs`), so the text never reads "a fall of −23.6%".
- **Checks (`src/report/check.py`, `tests/test_report.py`, 15 tests; the `report` rule runs them too).**
  - No stand-alone number in the prose outside a variable, except years, dates, names, cross-references and the conventional 95%/90% levels.
  - Every variable used exists.
  - The wording check runs on the prose with variables filled in, on the generated tables and on the include files.
  - The include files may hold no signed percentage, percentage point or concentration.
  - Every DECISIONS entry headed "DEVIATION" is listed in Appendix A.
  - **What the checks caught while writing:**
    - typed numbers ("3–5%" twice, now the variable `causal.rise_range`, taken from the same sentence `wording()` builds; "15-minute values");
    - "best-case" (the ranking pattern);
    - "says where NCAP worked";
    - "an effect of NCAP" un-negated in Appendix B.
    All were reworded.
- **Two things removed rather than generated:**
  - I had written that the comparison pool's PM2.5 "fell most" in the Indo-Gangetic Plain. An ad hoc calculation confirms it, but no pipeline output holds that number and Phase 10 computes nothing new. The sentence now cites the registered exclude-IGP check instead.
  - Two dataset-paper titles and one volume/page reference that I could not verify against DEC-200 were removed from the references; those entries keep authors, journal and DOI only.
- **Byte-stable PDFs.** With `#set document(date: none)` in `reports/_typst_style.typ`, two renders give byte-identical PDFs (checked twice, with and without `SOURCE_DATE_EPOCH`).
- **Snakemake.** The `report` stub is replaced by `fig1_slide`, `report_values`, `report` (runs the checks; part of `all`) and `report_render` (calls `ncap-site`; not part of `all`, like `dashboard_render`). Editing `src/viz/fig1_decomposition.py` re-ran `fig1`; every existing figure and `docs/figures.md` came out byte-identical, and `snakemake --cores 1 all` completed.
- **Not committed:** the rendered HTML (`reports/*.html`, gitignored). The Pages workflow builds it from the committed sources in Part C (DEC-210).
- **To fill in Part D:** Appendix B's line on the clean-clone rebuild points to this file; its result is recorded there.
- **Tests:** 270 pass.

**DEC-212: The licence check (DEC-206, DEC-210). No conflict found, so my choices are applied; two points need my review.**
- **The terms checked, on 2026-10-03.**
  - The CPCB mirror (ODbL 1.0; README and LICENSE saved at `a58f478`).
  - ACAG, ERA5, GHSL/GHS-POP, MAIAC, OpenAQ and DataMeet (DEC-200).
  - GeoNames (CC BY 4.0; `data/raw/geonames/readme.txt`).
  - Natural Earth (public domain).
  - NASA FIRMS (open data with the acknowledgement text from the FIRMS FAQ, read 2026-10-03).
- **Code, MIT.** No source licence constrains the code. The R packages the pipeline calls (some GPL) are installed from conda-forge or CRAN, not distributed here, and MIT is GPL-compatible.
- **Text and figures, CC BY 4.0.** This is compatible with every CC BY and public-domain source, given the attributions in Appendix C and `LICENSING.md`.
- **Ground-derived data, ODbL 1.0.** As the mirror requires.
- **An obligation, not a conflict.** The report, figures and dashboard are works produced from an adapted version of the ODbL database (the cleaned, deweathered station data). ODbL §4.6 then requires offering either the adapted database or "the method of making the alterations". The public repository's code is that method, and the notice says so. This holds only while the code stays public.
- **Two points for my review.**
  - **CPCB's own rights:** the mirror says "some individual contents of the database are under copyright by CPCB". The ODbL covers the database, not those contents, and CPCB's own terms could not be checked (its repository pages are offline, DEC-031). The notice keeps "some contents © CPCB".
  - **Derived data that is not ground data** (the satellite and city-level series among the dashboard CSVs) was not covered by my choices. I applied CC BY 4.0, matching their CC BY sources; to confirm.
- **Files written:**
  - `LICENSE` (MIT, © 2026 Reenu);
  - `LICENSE-CC-BY-4.0.txt` (the legal code from creativecommons.org, sha256 `9ba9550a…`);
  - `LICENSE-ODbL-1.0.txt` (the full ODbL 1.0 text as shipped by the mirror, sha256 `1d553fee…`);
  - `LICENSING.md` (which licence covers which part, the ODbL notice, and the attributions).
- **Still to change in Part C:** the dashboard's About page still says no code licence has been chosen.

## 2026-10-03: Phase 10 Part B reviewed (Reenu)

**DEC-213: My Part B rulings, applied before Part C.**
- **Registration wording.** The report abstract, the summary and the brief now say the plan was registered "before comparing NCAP with non-NCAP cities after 2018", as in the report's section on pre-registration. "Before any post-2019 comparison" and "before looking at the results" overclaimed.
- **"Already moving apart before 2019"** (the brief, twice) becomes "did not move together closely enough before 2019"; the failed test does not show a steady divergence. The report and summary did not use the phrase.
- **Scope and size, in the conclusion.**
  - The first sentence is scoped to "the NCAP cities I could check".
  - Weather moves a single year by "about half of a typical year's change", matching the weather section; before, it said "about as much as".
- **Table 4** now has a note: the "as registered, no deviations" rows' parts (generated values) are unstable because of the original GAM's extrapolation problem that motivated deviations A1 and A3. Only their H4 total is comparable with the other rows.
- **The abstract's AOD sentence** now carries the exploratory caveat that the two signals diverge most where no monitor was added.
- **NCAP and the monitoring network.** "NCAP paid for a large expansion of the monitoring network" is replaced with what the documents support, and a "Policy documents" group lists all fourteen NCAP documents in the references.
  - The NCAP report of January 2019 (section 8.1, PDF pages 61–62) proposes augmenting the continuous stations.
  - Lok Sabha answer AU5104 (4 April 2022, page 1) lists "expansion of monitoring network" among the activities that NCAP funds support.
  - Neither shows NCAP paid for any particular station, so the brief no longer says "many of them paid for by NCAP".
- **Scope on the slide and in the brief's caption:** "In the 18 NCAP cities with a continuous monitor since 2018…". The count is generated.
- **Smaller edits:**
  - "about 5.1%" becomes "a median 5.1%";
  - "On average, new monitors stand in cleaner spots";
  - the fire check now reads "nearby fire activity, as measured, does not account for it".
- **Licences:** CC BY 4.0 for the non-ground derived data (satellite and city-level series) is confirmed.
- **DEC-019:** my message again listed both options (leave unchanged, or replace the tool name with a visible note and a new entry), so the choice is still open and is asked at the Part C checkpoint.
- **Checks after the edits:** `python -m src.report.check` passes. `snakemake --cores 1 all` and `report_render` ran. Figure 1, S3, S4 and `docs/figures.md` rebuilt byte-identical; only the slide changed. The PDFs are 26, 1 and 2 pages.

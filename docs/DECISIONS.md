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

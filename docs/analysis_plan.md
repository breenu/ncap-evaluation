# Analysis plan (pre-registration draft)

**Weather, Monitors, or Policy? A meteorologically normalised, quasi-experimental evaluation of India's National Clean Air Programme, 2015–2025**

*DRAFT for Reenu's review (Phase 3, 2026-09-26). Follows the OSF Preregistration template. Nothing in the estimation stages may run until this plan is approved and committed, and `config/gate.yaml` is then flipped in a separate commit that cites this file's hash (DEC-012). Counts quoted below are pipeline outputs; each cites its source file.*

## 0. Read this first: how much pre-NCAP ground data exists

The ground network before NCAP is very small. Under the primary completeness rule, the number of valid station-years (an hour counts with at least one 15-minute value; a day needs 18 of 24 hours; a year needs 75% of days; flagged hours removed) is:

| | 2015 | 2016 | 2017 | 2018 | 2019 |
|---|---|---|---|---|---|
| PM10 | 2 | 6 | **9** | **66** | 123 |
| PM2.5 | 2 | 12 | 17 | 82 | 138 |

*Source: `data/interim/audit/valid_station_years.csv`. With hours requiring 3 of 4 quarter-hours (sensitivity, DEC-069): PM10 8 in 2017 and 55 in 2018. The 2018 PM10 figure of 69 given before Phase 3 was counted before flagged hours were removed; 3 station-years fall below 75% once flatlines and PM2.5 > PM10 hours are taken out.*

So the ground layer has **effectively one pre-NCAP year for PM10 (2018)**, and one for PM2.5. One pre-period year cannot test parallel trends. Therefore:
- The **primary evidence is the satellite PM2.5 layer (Layer A)**, which has a pre-period from 2010.
- **Ground-based effects (Layer B), PM10 effects, and the PM10-vs-PM2.5 mechanism test are secondary.** They are reported with this limitation stated beside every estimate, and the decision rules below treat them as weaker evidence.

## 1. Study information

**Research questions** (proposal): RQ1, how much of reported change is network composition; RQ2, how much is weather; **RQ3, the effect of NCAP enrolment on PM2.5** (this plan's confirmatory question); RQ4, heterogeneity and mechanism (exploratory apart from H3).

**Hypotheses**
- **H1 (confirmatory, Layer A).** Enrolment in NCAP reduced annual population-weighted PM2.5 in enrolled urban centres relative to comparable non-enrolled centres, 2019–2024.
- **H2 (confirmatory, direction).** The effect is larger in winter (Oct–Feb) than in the rest of the year. Most measures target winter episodes, and GRAP (the Graded Response Action Plan) actions apply in winter.
- **H3 (secondary, mechanism).** If dust control dominated spending, PM10 falls more than PM2.5 in enrolled cities, and the PM2.5/PM10 ratio rises.

## 2. Design plan

**Study type:** observational, quasi-experimental; staggered adoption; secondary data.

**Blinding.** Before approval, the authors have seen: all pre-2019 data; descriptive post-2019 series for individual cities, regions and the network as a whole; and data-quality diagnostics for all years. No NCAP vs non-NCAP comparison after 2018 has been computed or plotted (blinding rule, Phase 3). The pre-gate computations in §6 use pre-2019 data only.

**Units and treatment**
- **Units:** GHSL UCDB R2024A urban centres (DEC-006), one satellite unit per centre. NCAP cities sharing a centre are one unit (e.g. Delhi, Faridabad, Ghaziabad and Noida). The matching rules are in `docs/ncap_ucdb_review.md`.
- **Treated:** 113 units containing 121 NCAP cities, including Asansol & Raniganj as one unit (DEC-064).
- **Towns without a centre:** the 10 NCAP towns with no GHSL centre are **excluded from the primary estimate** (DEC-063). Controls are all GHSL centres, and treated and control units must be defined the same way. The towns enter one sensitivity analysis as 1.87 km buffered points.
- **Treatment timing (primary): the date a city first appears on an official NCAP list.** A city listed by 30 June counts as treated from that year, otherwise from the next year (interval-censored dates, DEC-043/044):
  - 2019 cohort: 102 cities (launch list, January 2019)
  - 2020 cohort: 19 cities (June 2020 list)
  - 2021 cohort: 10 cities (December 2020 and June 2021 lists)
  - A shared unit takes its earliest member's date.
- **Treatment timing (alternative):** the first financial year with a recorded central release (`ncap_funding_clean.csv`).
- **Anticipation:** 94 of the 102 launch cities were already on CPCB's 2017 non-attainment list. The event study will show any change between 2017 and 2018. A sensitivity analysis dates treatment from 2018 for those 94.

**Control pool**
- Non-NCAP GHSL centres with 2015 population ≥ 100,000 (a pre-treatment epoch, so the pool cannot depend on post-treatment growth): 924 centres.
- **Excluded:** any centre that contains the point of an NCAP town without its own centre. This removes 1 centre (Kalka, containing Parwanoo), leaving 923.
- **Spillover:** primary = no buffer. Sensitivity = drop controls within 25 km of a treated unit (`control_pool.spillover_buffer_km`).
- **Size:** treated units are kept whatever their size. A sensitivity analysis restricts treated units to ≥ 100,000 too, which drops 4 (Sunder Nagar, Nalagarh, Paonta Sahib, Talcher).

## 3. Sampling plan (existing data)
All data exist and are downloaded, with checksums in manifests (`docs/data-cards/`). Satellite analysis years: **2010–2024** (ACAG ends in 2024; nine pre-years). The ground window is 2015-01-01 to 2026-03-31. Ground analyses use **calendar years up to 2025 as primary**. January–March 2026 comes only from OpenAQ's raw real-time feed, not CPCB's validated repository (DEC-079), so it enters only a sensitivity check (FY2025-26). Sample sizes are fixed by the data; there is no stopping rule.

## 4. Variables
- **Outcome, Layer A:** log of annual population-weighted mean PM2.5 over the unit (ACAG V5.GL.06; GHS-POP 2020 weights; DEC-070). Also winter (Oct–Feb) and non-winter means from monthly V5.GL.06 (0.05°). Effects are reported as % change, with levels in µg/m³ secondary.
- **Outcome, Layer B:** deweathered station-level log daily PM2.5 and PM10 (Phase 5), aggregated to city-year on a balanced station panel (Phase 6).
- **Covariates:** ERA5 monthly meteorology averaged over the unit (temperature, humidity, wind, boundary-layer height, precipitation, radiation); region × year effects (`config/regions.yaml`: IGP, coastal, north-east, peninsular/other).

## 5. Analysis plan

**Estimators**
1. **Primary: synthetic difference-in-differences** (Arkhangelsky et al. 2021), estimated separately for each adoption cohort (the `synthdid` package requires simultaneous adoption, DEC-027) and combined as a treated-unit-weighted average. Standard errors: placebo method.
2. **Event study:** unit effects, region × year effects and ERA5 covariates; coefficients for years relative to adoption, with −1 omitted; standard errors clustered by unit. It shows pre-trends and when any effect appears.
3. **Callaway & Sant'Anna (2021)** staggered-adoption ATT, with not-yet-treated and never-treated controls.
4. **Layer B:** interrupted time series on deweathered ground data for each NCAP city with valid 2018 data; difference-in-differences where control-city stations exist.

**2020.** The 2020 coefficient is estimated and shown separately (COVID lockdown; the BS-VI fuel switch in April 2020). The post-period ATT is reported both with 2020 included and with it excluded; the primary ATT excludes 2020.

**Inference criteria and decision rules**
- **H1 supported** if all of these hold:
  - the primary SDID ATT (2019–2024, excluding 2020) is negative and its 95% CI excludes 0;
  - the event-study pre-period coefficients (2010–2017) are jointly insignificant (p > 0.10);
  - the 2016 placebo-in-time ATT's 95% CI includes 0;
  - the estimate keeps its sign in the Callaway & Sant'Anna estimate and in the area-weighted and V6.GL.03 versions.
- **If the CI includes 0:** report the minimum detectable effect (MDE, §6), and an equivalence statement. Effects larger than ±MDE are ruled out if the 90% CI lies within ±MDE.
- **H1 not supported:** "no detectable effect", never "no effect".
- **If the pre-trend test fails:** the effect is reported as "not identified by this design".
- **H2:** the winter-minus-rest difference, with 95% CI; supported if the CI excludes 0 in the direction of a larger winter reduction.
- **H3 (secondary):** evaluated on the ground layer only, where PM10 is measured, and with one pre-year. The result is labelled "consistent with dust control" only if all of these hold:
  - the PM2.5/PM10 ratio rises with a 95% CI excluding 0;
  - the PM10 effect exceeds the PM2.5 effect in ≥ 2 of 3 specifications (raw, deweathered, balanced panel);
  - H1's Layer A effect is not in the opposite direction.
  Otherwise it is "inconclusive". It is never "confirmed", because parallel trends cannot be tested with one pre-year.
- **Layers A and B disagree:** both are reported, the disagreement is investigated (network composition, satellite calibration), and the layers are not averaged.
- **City-level claims:** from the hierarchical model's shrunken estimates (Phase 8), or with FDR control at 5%; no unshrunk "best/worst cities" table.

**Robustness** (all reported, whichever way they point):
- placebo in time (2016);
- placebo in space (≥ 500 permutations);
- leave-one-out donors;
- exclude 2020; exclude IGP;
- FIRMS fire covariate (from 2012);
- satellite version (V6.GL.03) and vintage (V6.GL.02.04);
- area-weighted outcome;
- spillover buffer;
- treatment dates (funding-based; 2018 anticipation);
- include buffered no-centre towns; exclude Patancheruvu (DEC-049); treated units ≥ 100k only;
- completeness 60/90% and the 3-of-4 quarter-hour rule (ground);
- ground station-years with reliability score < 50 excluded (`docs/audit_report.md` §8); include January–March 2026 (ground);
- no deweathering (ground);
- a Himalayan region split.

## 6. Computed before approval (pre-2019 data only)
- **Minimum detectable effect:** placebo-in-time on 2010–2018 satellite data. Fake adoption in 2014 and 2015, the same estimator, and the spread of placebo ATTs across 500 permuted treated sets. MDE = 2.8 × SE (80% power, 5% two-sided). *To be filled in Phase 4 before approval.*
- **Baseline balance** of treated units vs the control pool, 2010–2018: PM2.5 level and trend, population, region.

## 7. Other
Deviations from this plan will be logged in `docs/DECISIONS.md`, dated and justified, and reported in the final report.

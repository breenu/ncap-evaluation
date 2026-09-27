# Analysis plan (pre-registration)

**Weather, Monitors, or Policy? A meteorologically normalised, quasi-experimental evaluation of India's National Clean Air Programme, 2015–2025**

*Status: final, 2026-09-27 (first drafted 2026-09-26). My decisions of 2026-09-27 are incorporated: treatment timing, H4/H5, the Asansol-alone check, OSF registration, units corrections (DEC-091/092). I will register this plan on OSF before the gate opens. Laid out in the order of the OSF Preregistration template (sections 1–6 below match its sections). Every number marked in the source as `<!--g:…-->` is written by `python -m src.causal.pregate_report sync-plan` from pipeline outputs, and `snakemake pregate` fails if any is stale. The full pre-gate tables are in [`pregate_checks.md`](pregate_checks.md) (generated). Nothing estimating post-2019 effects runs until I have approved and committed this file; I then flip `config/gate.yaml` in a separate commit citing this file's commit hash (DEC-012).*

---

## 1. Study information

**Title.** As above.

**Authors.** Reenu (sole author).

**Description.** NCAP, launched in January 2019, enrolled 131 Indian cities with a target of up to 40% lower PM10 by 2025-26. Public progress reports compare raw concentrations with a baseline. That comparison mixes three things: weather, changes in which monitors exist, and policy. This study separates them:
- **RQ1, measurement:** how much of a city's reported change comes from data-quality artefacts and network composition.
- **RQ2, weather:** how much comes from meteorology.
- **RQ3, policy:** the effect of NCAP enrolment on PM2.5 (and PM10), relative to comparable non-enrolled urban centres. This is the confirmatory question.
- **RQ4, heterogeneity and mechanism:** mostly exploratory.

**The central data limitation, stated first.** The ground network before NCAP is very small. Under the primary completeness rule, PM10 has <!--g:pm10_2017_ncap-->9<!--/g--> valid station-years in 2017 and <!--g:pm10_2018_ncap-->56<!--/g--> + <!--g:pm10_2018_non-->10<!--/g--> (NCAP + non-NCAP urban centres) in 2018. Non-NCAP centres have <!--g:pm10_2017_non-->0<!--/g--> valid PM10 station-years before 2018. So the ground layer has **one pre-NCAP year**, which cannot test parallel trends. Consequences:
- The **primary evidence is satellite PM2.5 (Layer A)**, which has nine pre-years (2010–2018).
- **Ground-based effects (Layer B), all PM10 effects, and the PM10-vs-PM2.5 mechanism test are secondary.** They carry that limitation beside every estimate.
- No minimum detectable effect is claimed for ground PM10 (§3).

**Hypotheses.**

| # | Status | Hypothesis | Layer |
|---|---|---|---|
| **H1** | Confirmatory, primary | NCAP enrolment reduced annual population-weighted PM2.5 in enrolled urban centres, relative to comparable non-enrolled centres, 2019–2024 (2020 excluded). | A |
| **H2** | Confirmatory, tested only if H1 is supported | The reduction is larger in winter (Oct–Feb) than in the rest of the year. Most city measures and GRAP (the Graded Response Action Plan) target winter episodes. | A |
| H3 | Secondary (mechanism) | If dust control dominated action, PM10 fell more than PM2.5 in enrolled cities, and the PM2.5/PM10 ratio rose. | B |
| H4 | Secondary (RQ1/RQ2; proposal hypothesis 1) | Reported (raw, all-station) improvements in NCAP cities exceed deweathered, composition-corrected improvements: weather and network change explain part of the reported change. | B |
| H5 | Secondary (RQ4; proposal hypothesis 3) | Effects are smaller (less negative) in Indo-Gangetic Plain (IGP) cities, where regional sources dominate. | A |

H4 and H5 are hypotheses 1 and 3 of the original proposal (dated 25 September 2026, written before any data were downloaded). I left them out of my first draft and have restored them (see §6).

## 2. Design plan

**Study type.** Observational; quasi-experimental; staggered adoption; secondary data only.

**Blinding.** I am not blinded in the usual sense: I am the only analyst and the data are public. The substitute is a **data-access rule** that I enforce in code (`config/gate.yaml`; `src/common/gate.py`):
- **What I had seen before writing this plan:**
  - all pre-2019 data;
  - post-2019 series for individual cities, regions and the whole network, descriptively;
  - data-quality diagnostics for every year.
- **My pre-gate computations** (all on data up to 2018; the code's data reader filters and asserts it):
  - the minimum detectable effect;
  - baseline balance;
  - a placebo on the real NCAP units at fake adoption years 2014 and 2015.
- **What I have not computed or plotted:** any comparison of NCAP with non-NCAP units after 2018.

**Study design: units, treatment, controls.**
- **Units (Layer A):** GHSL UCDB R2024A urban centres, one satellite unit per centre (DEC-006).
  - NCAP cities sharing a centre are one unit, e.g. Delhi, Faridabad, Ghaziabad and Noida.
  - **Asansol & Raniganj is one unit:** the Asansol centre joined with the GHSL centre UCDB names "Mejia", which holds Raniganj's built-up area (DEC-064, confirmed DEC-081).
- **Treated:** <!--g:n_treated-->113<!--/g--> units holding 121 NCAP cities.
- **Towns without a GHSL centre:** the 10 NCAP towns with none are **excluded from the primary estimate**, because treated and control units must be defined the same way (DEC-063). They enter one sensitivity analysis as 1.87 km buffered GeoNames points.
- **Patancheruvu (DEC-049): intention to treat.** It is enrolled from its listing date even though it is absent from the 2026 list, because dropping it would condition on a post-treatment event.
  - Layer A: its point lies inside the Hyderabad centre, which is treated anyway. The rule matters in the buffered-towns sensitivity analysis and on the ground (one station).
  - Sensitivity: exclude it.
- **Treatment timing, primary: first appearance on an official NCAP list.** Listed on or before 30 June counts as treated from that calendar year, otherwise from the next. Nothing is treated before 2019. A shared unit takes its earliest member's date.
  - Unit cohorts: 2019: <!--g:coh_2019-->89<!--/g-->; 2020: <!--g:coh_2020-->15<!--/g-->; 2021: <!--g:coh_2021-->9<!--/g-->.
- **Treatment timing, sensitivity only: the first financial year with a recorded central release** (my decision of 2026-09-27: XV-FC grants are partly performance-linked, so the timing of money is partly an outcome of air quality and must not define treatment), counted from the next calendar year (FY2019-20 → 2020; DEC-086). Sources: Lok Sabha AU2467 per-FY releases; XV-FC grants start in FY2020-21.
  - Unit cohorts: 2020: <!--g:fcoh_2020-->86<!--/g-->; 2021: <!--g:fcoh_2021-->25<!--/g-->; 2022: <!--g:fcoh_2022-->2<!--/g-->.
- **Anticipation:** 94 launch cities were already on CPCB's 2017 non-attainment list. Sensitivity: treat them from 2018.
- **Control pool:** non-NCAP centres with 2015 population ≥ 100,000. 2015 is a pre-treatment epoch, so the pool cannot depend on post-treatment growth.
  - Any centre containing the point of an NCAP town that has no centre of its own is excluded (Kalka, which contains Parwanoo).
  - This leaves **<!--g:n_controls-->923<!--/g--> controls**, from <!--g:n_nonncap-->1,810<!--/g--> non-NCAP centres (<!--g:n_pop-->924<!--/g--> of them ≥ 100k).
- **Spillover:** primary = no buffer. Sensitivity = drop controls within 25 km, edge to edge, of any NCAP place, including the buffered towns. This leaves <!--g:n_buffered-->754<!--/g--> controls (DEC-085).

<!--g:table_pool-->

| Rule | Units |
|---|---|
| GHSL urban centres in India (primary units) | 1,923 |
| ... of which hold an NCAP city (treated units) | 113 |
| Non-NCAP centres | 1,810 |
| ... with 2015 population >= 100,000 | 924 |
| ... not containing an NCAP town's point (control pool) | 923 |
| ... and at least 10 km from every NCAP place | 852 |
| ... and at least 25 km from every NCAP place | 754 |
| ... and at least 50 km from every NCAP place | 511 |

<!--/g-->

- **Size of treated units:** they are kept whatever their size. Sensitivity: restrict them to ≥ 100k too, which drops <!--g:n_below_100k_treated-->4<!--/g-->.

**Randomization.** None; treatment was assigned by policy. Enrolled cities were chosen *because* they were polluted, so selection and regression to the mean are the main threats. SDID's unit and time weights, the pre-trend tests and the placebos address them.

## 3. Sampling plan

**Existing data.** *Registration following analysis of the data.* I have downloaded, audited and described the data. I have not run the analyses that bear on the hypotheses (post-2018 NCAP vs non-NCAP comparisons), and a code-level gate prevents them from running.

**Explanation of existing data.** I checked every source and recorded it in manifests with checksums (`docs/data-cards/`):
- **Satellite:** ACAG V5.GL.06, V6.GL.03 and V6.GL.02.04.
- **Ground:** the CPCB mirror 2015–2025, plus OpenAQ for January–March 2026.
- **Weather:** ERA5.
- **Boundaries and population:** GHSL.
- **Treatment:** NCAP lists and funding tables from PDFs, with source page for every row.

Pre-period results I have already seen (details in [`pregate_checks.md`](pregate_checks.md) §5): the real NCAP units show a placebo ATT of <!--g:placebo_2014_pct-->+0.47%<!--/g--> at fake adoption 2014 (95% CI <!--g:placebo_2014_ci-->-0.24% to +1.19%<!--/g-->; equal-tailed permutation p = <!--g:placebo_2014_p-->0.32<!--/g-->) and <!--g:placebo_2015_pct-->-0.41%<!--/g--> at 2015 (95% CI <!--g:placebo_2015_ci-->-1.13% to +0.32%<!--/g-->; p = <!--g:placebo_2015_p-->0.75<!--/g-->). Both are consistent with no pre-NCAP divergence.

**Data collection procedures.** None; all data are secondary. The pipeline is `snakemake pregate` / `all`.

**Sample size.**
- **Layer A:** <!--g:n_treated-->113<!--/g--> treated and <!--g:n_controls-->923<!--/g--> control units. Years 2010–2024: nine pre-years; the primary post-period is 2019 and 2021–2024.
- **Layer B:** NCAP-city stations with a valid 2018 baseline. In 2018 that is <!--g:pm10_2018_ncap-->56<!--/g--> PM10 station-years in <!--g:pm10_2018_ncap_units-->25<!--/g--> NCAP centres.

**Sample size rationale: minimum detectable effect (MDE).** The sample is fixed by the data, so I report what the design can detect.
- **Method:** placebo-in-time on 2010–2018 satellite data. <!--g:draws-->500<!--/g--> sets of <!--g:n_treated-->113<!--/g--> control units were given fake adoption in 2014 and in 2015, and SDID was re-estimated each time.
- **Two null designs:** random sets, and region-matched sets (the same regional make-up as the real treated set).
- **Formula:** SE = SD of the placebo ATTs; MDE = 2.8 × SE (5% two-sided test, 80% power). The largest over both designs and both fake years is used.

<!--g:table_mde-->

| Outcome | Null design | Fake adoption | SE | Mean placebo ATT | MDE |
|---|---|---|---|---|---|
| Annual PM2.5, log (primary) | random | 2014 | 0.0042 | +0.0001 | 0.0117 (1.2% fall) |
| Annual PM2.5, log (primary) | region-matched | 2014 | 0.0036 | +0.0011 | 0.0102 (1.0% fall) |
| Annual PM2.5, log (primary) | random | 2015 | 0.0041 | +0.0002 | 0.0115 (1.1% fall) |
| Annual PM2.5, log (primary) | region-matched | 2015 | 0.0037 | -0.0028 | 0.0104 (1.0% fall) |
| Annual PM2.5, level (µg/m³) | random | 2014 | 0.27 µg/m³ | +0.00 µg/m³ | 0.75 µg/m³ |
| Annual PM2.5, level (µg/m³) | region-matched | 2014 | 0.24 µg/m³ | -0.36 µg/m³ | 0.66 µg/m³ |
| Annual PM2.5, level (µg/m³) | random | 2015 | 0.33 µg/m³ | +0.00 µg/m³ | 0.93 µg/m³ |
| Annual PM2.5, level (µg/m³) | region-matched | 2015 | 0.29 µg/m³ | -0.48 µg/m³ | 0.81 µg/m³ |
| Winter PM2.5 (Oct-Feb), log | random | 2014 | 0.0059 | +0.0001 | 0.0165 (1.6% fall) |
| Winter PM2.5 (Oct-Feb), log | region-matched | 2014 | 0.0057 | -0.0020 | 0.0158 (1.6% fall) |
| Winter PM2.5 (Oct-Feb), log | random | 2015 | 0.0055 | +0.0001 | 0.0155 (1.5% fall) |
| Winter PM2.5 (Oct-Feb), log | region-matched | 2015 | 0.0053 | -0.0051 | 0.0148 (1.5% fall) |
| Non-winter PM2.5 (Mar-Sep), log | random | 2014 | 0.0054 | +0.0001 | 0.0151 (1.5% fall) |
| Non-winter PM2.5 (Mar-Sep), log | region-matched | 2014 | 0.0053 | +0.0003 | 0.0147 (1.5% fall) |
| Non-winter PM2.5 (Mar-Sep), log | random | 2015 | 0.0059 | +0.0002 | 0.0164 (1.6% fall) |
| Non-winter PM2.5 (Mar-Sep), log | region-matched | 2015 | 0.0055 | -0.0048 | 0.0155 (1.5% fall) |
| Winter minus non-winter, log (H2) | random | 2014 | 0.0072 | -0.0000 | 0.0201 (≈ 2.0 pp) |
| Winter minus non-winter, log (H2) | region-matched | 2014 | 0.0077 | -0.0023 | 0.0215 (≈ 2.1 pp) |
| Winter minus non-winter, log (H2) | random | 2015 | 0.0065 | -0.0001 | 0.0182 (≈ 1.8 pp) |
| Winter minus non-winter, log (H2) | region-matched | 2015 | 0.0068 | -0.0003 | 0.0191 (≈ 1.9 pp) |

<!--/g-->

**The MDE for H1 is a <!--g:mde_pct-->1.2<!--/g-->% fall in annual population-weighted PM2.5** (<!--g:mde_log-->0.0117<!--/g--> in natural-log units). At the NCAP units' 2010–2018 mean of <!--g:level_treated-->51.7<!--/g--> µg/m³ that is about <!--g:mde_ugm3_implied-->0.6<!--/g--> µg/m³. A separate fit on the µg/m³ scale gives <!--g:mde_ugm3-->0.9<!--/g--> µg/m³: absolute noise is concentrated in the most polluted units, so the µg/m³ MDE is not the % MDE times the mean (`pregate_checks.md` §4). The primary outcome is on the log scale, so the % MDE is the one that counts. The MDE for H2 (winter minus non-winter) is <!--g:mde_h2_log-->0.0215<!--/g--> in log units (≈ <!--g:mde_h2_pp-->2.1<!--/g--> percentage points). **Read this MDE as a lower bound, not a power calculation.** ACAG PM2.5 is a smooth, calibrated product averaged over a hundred units, so pre-period noise is small. The real design is noisier:
- its post-years reach 6 years after adoption, where synthetic controls drift more (the placebo post-periods are 4–5 years);
- the placebo assigns every unit at once, while the real estimator averages cohorts;
- even region-matched sets are more dispersed than the real treated set;
- the post-period holds shocks the pre-period does not (COVID, BS-VI).

The confidence intervals use the real design's own SE (joint placebo, §5). I report the MDE for information only: it is a best-case noise level, not the smallest effect that matters, so it is **not** the equivalence margin. The margin is a substantive smallest effect of interest, ±<!--g:equiv_margin-->5<!--/g-->% (§5).

**Ground PM10: no MDE.** Non-NCAP centres have no valid PM10 before 2018, so no pre-period change exists on the control side. Only <!--g:pm10_pair_stations-->6<!--/g--> stations in <!--g:pm10_pair_units-->5<!--/g--> NCAP cities are valid in both 2017 and 2018. A placebo is therefore impossible, and a variance from one year-pair would not be an MDE.

**Stopping rule.** None (fixed existing data).

## 4. Variables

**Manipulated variables.** None. The treatment indicator is NCAP enrolment (timing as in §2).

**Measured variables.**
- **Layer A outcome (primary):** log annual population-weighted mean PM2.5 over the unit: ACAG V5.GL.06, 0.01°, weighted by GHS-POP 2020 (DEC-070, DEC-081). Sensitivity: the area-weighted mean.
- **Seasonal outcomes (H2):** V5.GL.06 monthly.
  - Winter season-year *t* = October *t* to February *t*+1, so winter 2019 is the first fully after launch and winter 2023 the last complete one.
  - Non-winter *t* = March to September *t*.
  - A season needs all its months.
- **Layer B outcome:** station daily PM2.5 and PM10 → deweathered (Phase 5) → city-year on a balanced station panel (Phase 6).
  - Balanced-panel baseline 2018 (primary), 2019 (sensitivity).
  - Ground years: **calendar 2025 is the last primary year.** January–March 2026 exists only in OpenAQ's raw real-time feed, not CPCB's validated archive (DEC-079), so it enters a FY2025-26 sensitivity analysis only.
- **Ground validity rules:**
  - Valid hour: at least 1 of 4 quarter-hours (primary); at least 3 of 4 (sensitivity) (DEC-069).
  - Valid day and valid year: 75% of hours and 75% of days (primary); 60% and 90% (sensitivity).
  - Flagged values are removed before daily means: ceilings, flatlines of 4 or more hours, PM2.5 > PM10 (DEC-068).
- **Covariates:**
  - ERA5 monthly meteorology averaged over each unit: temperature, humidity, wind, boundary-layer height, precipitation, radiation.
  - Region × year effects, with regions IGP, coastal, north-east and peninsular/other (DEC-075).
  - VIIRS fire radiative power, from 2012, in one sensitivity check (DEC-039).

**Indices.**
- The station reliability score (0–100; DEC-073) is descriptive. It is used only in the "exclude score < 50" sensitivity analysis.
- Deweathered series: the model family with the better median out-of-sample R² under blocked, forward-chaining CV is primary; the other is the sensitivity (DEC-088). Choosing on CV fit is blind to treatment.

## 5. Analysis plan

**Statistical models.**
1. **Primary: synthetic difference-in-differences** (SDID; Arkhangelsky et al. 2021; R `synthdid`).
   - Estimated separately per listing cohort with never-treated controls, since the package needs simultaneous adoption (DEC-027).
   - Pre-period: 2010 to the year before the cohort's adoption. Post-period: adoption to 2024.
   - **The year 2020 is dropped from the primary panel.**
   - Cohort ATTs are combined weighted by their number of treated units.
   - **SE by joint placebo:** in each of 500 replications, disjoint random sets of controls, of the cohorts' sizes, are given the cohorts' adoption years; the aggregate is re-estimated each time. 95% CI = ATT ± 1.96 SE.
2. **Event study.**
   - Unit effects, region × year effects, ERA5 covariates, and relative-year indicators from −9 to +5 with −1 omitted.
   - Estimated with the Sun & Abraham (2021) interaction-weighted estimator against never-treated units, which avoids the bias of two-way fixed effects under staggered adoption.
   - SEs clustered by unit. The 2020 coefficient is shown separately.
   - **Sensitivity to pre-trends (reported, not a decision rule):** Rambachan & Roth (2023) bounds from R `HonestDiD` (0.2.8, in the same 2026-09-25 CRAN snapshot; installed in Phase 7), applied to the event-study coefficients and their clustered covariance. I report two restrictions for the average post-period effect: relative magnitudes (post-period violations at most M̄ times the largest pre-period one; M̄ = 0, 0.5, 1, 1.5, 2) and smoothness (a limit M on how much the trend's slope may change between consecutive periods; M from 0 to twice the largest pre-period coefficient's SE, in 5 equal steps). I report the robust 95% CIs and the breakdown value: the largest M̄ at which the CI still excludes 0.
3. **Callaway & Sant'Anna (2021)**, R `did`: doubly robust, never-treated controls (primary for this estimator) and not-yet-treated (sensitivity). Simple and dynamic aggregations, with uniform bands.
4. **Layer B.**
   - **ITS:** deweathered interrupted time series per NCAP city with valid 2018 data. It is a before–after contrast of deweathered series and cannot separate national shocks.
   - **Ground DiD:** NCAP vs non-NCAP stations with year effects, only where both have 2018 data.
   - Both are reported for PM2.5 and PM10 separately; 95% CIs by cluster bootstrap over cities (1,000 resamples).
5. **Hierarchical model (Phase 8):** a measurement-error model of city effects and their SEs, with moderators: baseline PM2.5, IGP, log population, coastal, funding channel. This gives shrunken city estimates. H5 is the IGP coefficient.

**Transformations.** Natural log of concentrations; effects reported as % change (100 × (e^β − 1)), with µg/m³ from the level-scale fit as secondary.

**Inference criteria and decision rules** (unchanged from my first draft except where §6 says otherwise).
- **H1 supported** if all of these hold:
  - (a) the primary SDID ATT is negative and its 95% CI excludes 0;
  - (b) the event-study pre-period coefficients (−9 to −2) are jointly insignificant (Wald p > 0.10);
  - (c) the 2016 placebo-in-time ATT's 95% CI includes 0;
  - (d) the estimate keeps its sign in Callaway & Sant'Anna, in the area-weighted outcome and in V6.GL.03.
- **If (b) or (c) fails:** "not identified by this design", whatever the ATT. If (b) fails, I report the HonestDiD bounds alongside, showing how large a pre-trend violation the estimate could withstand; they do not overturn the verdict.
- **If the CI includes 0:** "no detectable effect", never "no effect". Plus an equivalence test (two one-sided tests at 5%) against a **smallest effect of interest of ±<!--g:equiv_margin-->5<!--/g-->% in annual PM2.5**: if the 90% CI lies within ±<!--g:equiv_margin-->5<!--/g-->% (in log units, between ln 0.95 and ln 1.05), effects of that size or larger are ruled out; otherwise the result is inconclusive. Why ±<!--g:equiv_margin-->5<!--/g-->%: one quarter of NCAP's smallest target (a 20% reduction). That target was set for PM10, not PM2.5, so the margin is a judgement, not an official threshold. The MDE (<!--g:mde_pct-->1.2<!--/g-->%) is still reported.
- **Whatever the outcome:** report which effect sizes the 95% CI excludes, set against NCAP's own targets (a 20–30% reduction, later up to 40%, in PM10). A satellite PM2.5 result says nothing directly about PM10 attainment, and I will say so.
- **H2** (tested only if H1 is supported): the winter-minus-non-winter ATT difference, from the same joint placebo draws. Supported if the 95% CI excludes 0 in the direction of a larger winter reduction. If H1 is not supported, I report H2 as exploratory.
- **H3:** labelled "consistent with dust control" only if all of these hold:
  - the PM2.5/PM10 ratio rises, with a 95% CI excluding 0;
  - the PM10 effect exceeds the PM2.5 effect in ≥ 2 of 3 specifications (raw, deweathered, balanced panel);
  - Layer A is not in the opposite direction.

  Otherwise "inconclusive". Never "confirmed", because one pre-year cannot test parallel trends.
- **H4:** per NCAP city with ground data, raw all-station change minus deweathered balanced-panel change, from 2018 to 2025. Supported if the mean across cities is positive with a 95% cluster-bootstrap CI excluding 0. This is descriptive (NCAP cities only), not causal.
- **H5:** supported if the IGP coefficient's 95% credible interval lies above 0 (a less negative effect).
- **Robustness:** a check "agrees" if it has the primary's sign and its point estimate lies inside the primary 95% CI. I report every check in one table, whichever way it points.

**Threat: satellite calibration leakage** (pre-specified sensitivity check). ACAG calibrates satellite PM2.5 to ground monitors, and NCAP added monitors mainly in treated cities, so a Layer A effect could partly reflect calibration rather than air quality.
- **Split.** I estimate the primary SDID (same controls, cohorts, 2020 handling and joint-placebo SE) separately for treated units that gained a CAAQMS station inside their polygon with first PM data in <!--g:leak_from-->2019<!--/g-->–<!--g:leak_to-->2024<!--/g--> (the satellite post-period) and for those that did not. The difference (gained minus not gained) gets its SE from joint placebo draws of both group sizes.
- **Group sizes** (network metadata only, `pregate_checks.md` §7): <!--g:leak_gain-->74<!--/g--> units gained a monitor; <!--g:leak_nogain-->39<!--/g--> did not (<!--g:leak_nogain_had-->12<!--/g--> already had a station before <!--g:leak_from-->2019<!--/g-->, <!--g:leak_nogain_never-->27<!--/g--> never had one inside the polygon). A group with fewer than <!--g:leak_min-->10<!--/g--> units is not estimated, and I say that it is too small; with these sizes, <!--g:leak_estimable-->both groups are large enough to estimate<!--/g-->.
- **Warning sign of leakage**, which I report as such beside H1: the gained group's ATT is negative with a 95% CI excluding 0 while the not-gained group's CI includes 0, or the difference is negative with a 95% CI excluding 0. It is a warning, not proof: cities that gained monitors also differ in size and pollution, so the gap could be real heterogeneity.
- **Related evidence under the same threat:** the V6.GL.02.04 vintage comparison (calibrated to an earlier monitor set), and, if time allows, raw MAIAC aerosol optical depth, which uses no ground monitors.

**Multiple comparisons.**
- **Confirmatory family = {H1, H2}, tested in fixed sequence at α = 0.05.** H2 is tested only if H1 is supported. This keeps the familywise error rate at 5% without splitting α.
- **H3–H5 are secondary:** each at 0.05, labelled secondary, never promoted to confirmatory.
- **Robustness checks and event-study coefficients** are not hypothesis tests. The event study gets one joint pre-trend test, plus pointwise CIs and uniform (simultaneous) bands from the CS estimator.
- **City-level claims** come from the hierarchical model's shrunken estimates. Any unshrunk city claim is held to Benjamini–Hochberg FDR 5% across all 113 treated units. There is no unshrunk "best/worst cities" table.
- **Moderators other than IGP** are exploratory.

**Triangulation, and how disagreement between layers is reported.**
- Layer A remains the headline. I show Layer B beside it and never average the two.
- The like-for-like comparison is Layer A restricted to the units that have Layer B stations, PM2.5 only.
- The pair is classified in advance as one of:
  - **consistent:** same sign and overlapping 95% CIs;
  - **different magnitude:** same sign, non-overlapping CIs;
  - **conflict:** opposite signs with at least one CI excluding 0;
  - **uninformative:** the Layer B CI contains both 0 and the Layer A estimate.
- **Any category other than "consistent" triggers a fixed investigation**, and I report each step whether or not it closes the gap:
  1. network composition (all stations vs balanced panel);
  2. satellite calibration to the ground (V6.GL.02.04 vintage vs V5.GL.06; the ground–satellite correlation over time);
  3. spatial coverage (station sites vs the population-weighted polygon);
  4. deweathering (raw vs deweathered).
- I never treat ground PM10 and satellite PM2.5 as "agreement".

**Primary choices and their sensitivity checks** (I run and report every one).

| Choice | Primary | Sensitivity | Log |
|---|---|---|---|
| Satellite product | V5.GL.06 | V6.GL.03 (algorithm); V6.GL.02.04 (vintage, to 2023) | DEC-001/002 |
| Unit value | population-weighted mean | area-weighted mean | DEC-070/081 |
| Towns without a GHSL centre (10) | excluded | included as 1.87 km buffers | DEC-063 |
| Patancheruvu | intention to treat | excluded | DEC-049 |
| Asansol & Raniganj | one unit incl. the "Mejia" centre | Asansol centre alone (added 2026-09-27) | DEC-064/081 |
| Treated-unit size | all | ≥ 100k only | first draft |
| Spillover | none | 25 km buffer | DEC-085 |
| Treatment date | first listing | first funding year (never primary: funding is partly performance-linked); 2018 for the 94 on the 2017 list | DEC-086, DEC-092 |
| 2020 | dropped | included; own coefficient | first draft |
| Controls (CS) | never-treated | not-yet-treated | — |
| Valid hour (ground) | ≥ 1 of 4 quarter-hours | ≥ 3 of 4 | DEC-069 |
| Completeness (ground) | 75% / 75% | 60%, 90% | DEC-073 |
| Ground end | calendar 2025 | + Jan–Mar 2026 (FY2025-26, provisional) | DEC-079 |
| Station coordinates I set by judgement (5) | recommended coordinates | drop all 5 | DEC-080 |
| Balanced-panel baseline | 2018 | 2019 | DEC-088 |
| Deweathering | better-CV family | other family; none | DEC-088 |
| Reliability | all valid station-years | drop score < 50 | DEC-073 |
| Calibration leakage | all treated units | split by gained a monitor 2019–2024 or not; MAIAC AOD if time allows | DEC-096 |
| Pre-trends | rule (b) | HonestDiD bounds (relative magnitudes, smoothness) | DEC-097 |
| Other checks | — | placebo in time (2016); placebo in space (500 permutations); leave-one-out donors; exclude IGP; Himalayan region split; VIIRS fire covariate (from 2012) | proposal |

**Data exclusion.** Only by the rules above (flags, completeness, control-pool rules). No outlier exclusion on outcome values.

**Missing data.**
- The satellite panel is complete (no missing unit-years).
- The completeness rules handle ground gaps; I do not impute in the primary analysis.
- The audit found missingness is *lower* on polluted days, which biases naive annual means slightly upward (median +0.7%, `audit_report.md`). I report this beside Layer B.

**Exploratory analyses** (I label them as such):
- funding dose-response on *allocations*, with the reverse-causality caveat (cut item 1);
- moderators other than IGP;
- NO2 as a secondary pollutant.

(Raw MAIAC AOD is listed under the calibration-leakage threat above, still conditional on time.)

## 6. Other

**Changes I made to my first draft after computing the pre-gate numbers** (listed here for transparency):
1. Numbers filled in: MDE, pool, balance, cohorts.
2. H4 and H5 restored. They are hypotheses 1 and 3 of the original proposal dated 25 September 2026, written before any data were downloaded (the proposal PDF was created 2026-09-25 18:26 UTC and committed in the repository's first commit; the earliest raw download in any manifest is 2026-09-26 04:44 UTC). So they were not chosen after seeing data.
3. H2 made conditional on H1 (fixed sequence).
4. The joint-placebo SE for the cohort aggregate; never-treated donors in each per-cohort SDID.
5. The season-year definition.
6. The Sun & Abraham event-study estimator.
7. The layer-disagreement categories.
8. The deweathering-family rule.
9. The funding-date rule.
10. The Asansol-alone sensitivity (added 2026-09-27).
11. Units and p-values corrected (DEC-091): I give log-scale results in natural-log units with the implied percentage (my draft's "log points" label could be read as 100 times too large), permutation p-values are equal-tailed, and the % and µg/m³ MDEs are reported separately. No estimate changed.

**Further changes I made on 2026-09-27, before OSF registration:**
1. **Equivalence margin:** a smallest effect of interest of ±<!--g:equiv_margin-->5<!--/g-->% in annual PM2.5 (one quarter of NCAP's smallest target, 20%, which was set for PM10) replaces ±MDE. The MDE is a best-case noise level, so with it as the margin a null would almost always be "inconclusive". The MDE is still reported (DEC-095).
2. **Calibration-leakage check:** H1 split by whether treated units gained a CAAQMS station in the satellite post-period, with group sizes, a minimum group size and a pre-stated warning rule; MAIAC AOD listed under this threat, conditional on time (DEC-096).
3. **HonestDiD bounds** on the event study as a reported sensitivity analysis; rule (b) unchanged, and if (b) fails the bounds are reported alongside "not identified" (DEC-097).

H1's decision rules (a)–(d) are unchanged.

**Baseline balance** (unweighted, 2010–2018). NCAP units are much larger than the pool (log-population SMD <!--g:smd_pop-->1.44<!--/g-->) and less often in the IGP (<!--g:igp_treated-->28<!--/g-->% vs <!--g:igp_control-->43<!--/g-->%). Their mean PM2.5 is similar (<!--g:level_treated-->51.7<!--/g--> vs <!--g:level_control-->56.4<!--/g--> µg/m³), and so is their pre-trend (<!--g:trend_treated-->2.3<!--/g--> vs <!--g:trend_control-->2.1<!--/g-->% a year). SDID does not need level balance, only a matched pre-period path, which the placebos test.

<!--g:table_balance-->

| Characteristic (2010-2018 unless stated) | NCAP units (n=113) | Control pool (n=923) | SMD | Buffered pool (n=754) | SMD (buffered) |
|---|---|---|---|---|---|
| PM2.5 mean 2010-2018 (µg/m³) | 51.67 | 56.37 | -0.22 | 54.30 | -0.12 |
| PM2.5 trend 2010-2018 (% per year) | 2.28 | 2.11 | 0.17 | 2.11 | 0.18 |
| Winter PM2.5 mean 2010-2017 seasons (µg/m³) | 72.09 | 80.80 | -0.23 | 76.98 | -0.13 |
| Population 2015 (log10) | 5.94 | 5.32 | 1.44 | 5.31 | 1.46 |
| Area (km2) | 211.58 | 48.26 | 0.53 | 43.81 | 0.55 |
| Region: coastal | 15.9% | 13.9% | 0.06 | 14.7% | 0.03 |
| Region: igp | 28.3% | 43.2% | -0.31 | 39.5% | -0.24 |
| Region: north-east | 5.3% | 4.4% | 0.04 | 4.5% | 0.04 |
| Region: peninsular/other | 50.4% | 38.5% | 0.24 | 41.2% | 0.19 |

<!--/g-->

**Deviations.** I will log any deviation from this plan in `docs/DECISIONS.md`, dated and justified, and list it in the final report.

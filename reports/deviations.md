# Appendix A. Deviations from the registered plan

I registered my analysis plan on OSF on 27 September 2026 (<https://osf.io/jksne/>). The registered file is `docs/analysis_plan.md` at commit `6e24eca`, and the code gate that allowed post-2019 estimates was opened in a separate commit, `0d9aa42`, citing it. On 1 October 2026 I posted a clarification of how I read some of the registered decision rules. The registration promised that every deviation would be dated, justified and listed in this report. This appendix is that list.

Every entry gives the date I decided, the commit that first recorded the decision in the public repository, its entry in `docs/DECISIONS.md`, my reason, and whether I made it before or after I had seen the estimate it affects. Git shows when a rule was committed, not when I first looked at a number; where the order of events matters, the DECISIONS entry states it.

The entries fall into six groups:

- **A.** Deviations from the registered plan.
- **B.** Registered analyses that I did not carry out, or that the data could not support.
- **C.** Clarifications of registered rules, posted on OSF on 1 October 2026.
- **D.** Departures from rules I fixed after registration, and from the original proposal.
- **E.** Places where the registered text was incomplete or could not be applied literally, and how I read it.
- **F.** Analyses I added after registration. Each is labelled as such wherever it appears.

Implementation fixes that changed no specification (for example DEC-083, DEC-152 and DEC-158) are not listed.

## A. Deviations from the registered plan

The registered text fixes the rule that chooses the deweathering model family, the data-validity rules and the exclusion rules. It does not spell out the model specification or the weather-resampling scheme. I list A1 and A3 as deviations anyway, because each changes what the registered analysis would have computed. Wherever a result depends on A1–A3, I also report the version with none of them ("as registered, no deviations": the original GAM trend, Grange & Carslaw resampling, registered flags only).

| # | Registered | What I did instead | Decided | DEC | Why | Timing |
|---|---|---|---|---|---|---|
| A1 | Deweathering by the proposal's method (Grange & Carslaw 2019), whose default resamples each day's weather from any time of year. | Each day's weather is resampled from ERA5 days within ±15 days of the same date. The all-year scheme is run on every series as a sensitivity analysis. | 2026-09-27, `083370b` | DEC-109 | All-year resampling pairs a date with weather that never occurs in that season, so the model predicts outside the conditions it was fitted on. | After the pilot's deweathering output on 20 stations; before the full deweathering run, before H4 and before any treatment estimate. |
| A2 | Data are excluded only by the registered flags, completeness rules and control-pool rules. | A near-constant-analyser rule removes station-years in which an instrument barely moved for a month or more while its neighbours did. The registered flags alone are the sensitivity analysis. | 2026-09-27, `083370b` | DEC-110 | The pilot found a stuck instrument that the registered flatline rule cannot catch, because its hourly values still change slightly. | After the pilot; before the full deweathering run, before H4 and before any treatment estimate. |
| A3 | The family-selection rule (better median out-of-sample R² under blocked, forward-chaining CV) chooses between LightGBM and the GAM. | The GAM's trend has knots exactly one year apart, so it cannot follow seasons or weather episodes. The original GAM is kept as a sensitivity family, and the registered rule was re-applied to the refitted GAM (DEC-117), which it chose again (DEC-118). | 2026-09-28, `72f2fc3` (pushed before the refit) | DEC-116 | The original trend absorbed part of the seasonal cycle and year-specific weather, and under all-year resampling it produced physically impossible values. | After the full deweathering run and after the registered rule had chosen the original GAM (DEC-114, DEC-115); before H4 and before any treatment estimate. |

## B. Registered analyses not carried out or not computable

| # | Registered | What happened | Decided | DEC | Why | Timing |
|---|---|---|---|---|---|---|
| B1 | A FY2025-26 sensitivity analysis for ground results, adding January–March 2026. | Not computable. | 2026-09-30 (H4), 2026-10-01 (Layer B) | DEC-128, DEC-149 | The deweathering models are fitted on days up to 31 December 2025 (DEC-101), because January–March 2026 exists only in OpenAQ's unvalidated real-time feed (DEC-079). So no deweathered values exist for 2026. | Known before H4 and Layer B were computed. |
| B2 | Completeness 90% as a sensitivity analysis for ground results. | Not computable for H4 or Layer B. | 2026-09-30 | DEC-132 | At 90% completeness no NCAP city has a station valid every year from 2018, so there is no balanced panel. | Found when H4 was first computed. |
| B3 | NO2 as a secondary pollutant (registered as exploratory). | Not carried out. | 2026-10-03 | DEC-208 | I found this omission while compiling this list. NO2 was ingested and cleaned but never analysed. | Found after every other result had been seen. |
| B4 | H2 (a larger winter reduction), tested only if H1 is supported. | Not tested, as registered; the winter and non-winter estimates are reported as exploratory. | 2026-10-01 | DEC-151 | H1 was not supported. | Follows the registered sequence. |

The registered "if time allows" check on raw MAIAC aerosol optical depth was carried out (Phase 8b; its rules are E12), and so was the VIIRS fire-covariate check (E11).

## C. Clarifications of registered rules

These change no hypothesis, threshold or estimator. Some registered rules call effects "changes" that can be read with either sign; I fixed one reading for each. On 1 October 2026 I posted a summary of these readings on the OSF registration (saved as `docs/osf/clarification_2026-10-01.md`). The full set of readings is DEC-135, so C2 covers more than the posted text.

| # | Registered text | My reading | Decided | DEC | Why | Timing |
|---|---|---|---|---|---|---|
| C1 | H4: "raw all-station change minus deweathered balanced-panel change … supported if the mean across cities is positive". | "Change" means improvement: H4 = reported fall minus corrected fall, positive when the reported number overstates the improvement. | 2026-09-30, `29874cf` | DEC-127 | Read literally on concentration changes (a fall is negative), the rule would call the opposite of the hypothesis "supported". The hypothesis text fixes which sign counts as support. | Committed before H4 was first computed (`132b788`, the same morning). The commit was pushed publicly on 1 October 2026, after H4 had been computed, as the OSF clarification states. |
| C2 | Every decision rule in plan §5. | One sign convention for all effects (negative = a reduction); H1 rule (d) as "point estimate < 0"; the equivalence bounds kept exactly as registered (ln 0.95 to ln 1.05); H2 as a negative winter-minus-non-winter difference; H3 as a larger PM10 reduction with PM10 actually falling; H5's coding; "agrees" judged on the same scale as the primary; a fixed order for the layer-disagreement categories, which overlap, with a fifth "unclassified" case reported under that name; Benjamini–Hochberg on two-sided p-values. | 2026-09-30, `ba397a2` | DEC-135 | After C1 I audited every registered rule for the same kind of ambiguity. | Committed and pushed before any Phase 7 estimate (the first is `655fb65`, 2026-10-01). |

## D. Departures from rules fixed after registration, and from the proposal

| # | Earlier rule | What I did instead | Decided | DEC | Why | Timing |
|---|---|---|---|---|---|---|
| D1 | DEC-103: in cross-validation, the trend for an unseen test year is clamped at the last training day. | A test day takes the trend of the same calendar day one year earlier. Both conventions are reported. | 2026-09-27, `d57c495` | DEC-107 | Clamping carried the last training day's season (late December) into the whole test year. This changes how the registered selection metric is computed, not the rule itself. | After seeing the GAM's pilot results and before LightGBM's; before the full run. The full run's family choice depended on the convention (DEC-114); after A3 the GAM is chosen under both (DEC-118). |
| D2 | DEC-103: the number of weather draws is the smallest that meets a convergence rule (300 in the pilot). | 500 draws for every series. | 2026-09-27, `083370b` | DEC-113 | 300 met the rule only narrowly; 500 is inside the proposal's range of 500–1,000. | After the pilot; before the full run. Unrelated to any treatment comparison. |
| D3 | DEC-130: the GAM–LightGBM disagreement diagnostic splits each model's weather effect on the log scale. | The split is made on the annual-mean scale, into modelled weather and model misfit. The failed version stays in the outputs. | 2026-09-30, `132b788` | DEC-133 | The log-scale split failed its own pre-set additivity check. The diagnostic chooses nothing; the registered rule chose the family. | After the check failed; it affects no hypothesis test. |
| D4 | DEC-150 (and the proposal's figure 1): a final "policy" step drawn from the corrected ground change, followed by a "remaining change" bar. | Figure 1 has no policy step and no remaining-change bar. The satellite relative change is drawn on its own axis, labelled "not identified as an effect of NCAP". | 2026-10-03, `09209e7`; approved `406f544` | DEC-191, DEC-197 | After H1 was not identified, subtracting the satellite estimate presupposes the attribution the design failed to establish. The two quantities also differ in time base and definition. No number changes. | After the H1 verdict (DEC-151). |
| D5 | No rule existed for which cities illustrate figure 1. | Panel (c) shows four cities chosen by a rule on station counts: in each region present, the city with the most stations valid in 2025, then the next city with the most, drawn alphabetically. Every city is in figure S3. | 2026-10-03, `09209e7`; approved `406f544` | DEC-191, DEC-197 | Composition can matter only where the network changed, and station counts use no outcome. The figure's panel heading and caption say when the rule was written. | After I had seen every city's decomposition (`docs/composition_report.md` §1d). The rule uses station counts only, but the choice of rule was not blind. |
| D6 | The proposal's figure questions, e.g. figure 5: "Where did NCAP work, and where not?" | Questions that presuppose an effect are reworded, e.g. "Where did satellite PM2.5 rise or fall relative to comparison units after listing?" | 2026-10-03, `09209e7` | DEC-190 | The same reason as D4. | After the H1 verdict. |
| D7 | DEC-167: figure 7 shows the satellite PM2.5 reference in panel (b). | The reference row is in panel (a). | 2026-10-02; logged 2026-10-03, `4eb69f7` | DEC-170 | Panel (b)'s axis is the change in the PM2.5/PM10 ratio, so a PM2.5 estimate drawn there would read as a ratio. Layout only. | After the figure was drawn; no number changes. |
| D8 | DEC-179: every MAIAC sensitivity specification is estimated with the monitor-gain split. | The sensitivity specifications estimate the overall relative change only and are classified by Q1 only; the split (and Q2) is estimated on the primary specification. | 2026-10-03, `05ab2f7` | DEC-182 | The split on every sensitivity would roughly triple the run time for numbers that classify nothing. | Before any AOD value existed. |
| D9 | DEC-178: export to Earth Engine assets, and stop if the pilot projects more than 100 EECU-hours of compute. | Export to a private Google Drive folder, with md5 checks; the compute limit was raised to 400 EECU-hours after I moved the project to the Contributor tier. | 2026-10-03, `d6289c5`, `b7eca89`, `9ae23d9` | DEC-183, DEC-184, DEC-185 | The project had no asset area to write to, and the pilot tripped the stop rule. Neither change alters any computed value. | Before the export, so before any AOD value existed. |
| D10 | The proposal's dashboard: each city's raw, deweathered, composition-corrected and synthetic-comparison trends. | The dashboard leaves out the synthetic comparison's trajectory. | 2026-10-03, `a139fe3` | DEC-203 | A drawn gap between a city and its synthetic comparison invites a causal reading that the design did not identify; the per-unit trajectories were also not saved. | After the H1 verdict. |

Earlier departures from the proposal (satellite product versions, the ground-data source, dropping WorldPop and pyGAM, VIIRS instead of MODIS fire data, the data window) were made before registration and are part of the registered plan; they are described in Section 2 and logged in DEC-001 to DEC-046.

## E. Readings of incomplete or inapplicable registered text

Each of these fills a gap the registered text leaves open, or resolves a case where it cannot be applied literally. Each was committed before the estimate it governs. E10 to E12 were written after the Phase 7 estimates had been seen, which is why I list them here with their timing.

| # | Registered text | My reading | Decided | DEC | Timing |
|---|---|---|---|---|---|
| E1 | H4 "per NCAP city with ground data". | Per GHSL urban-centre unit: NCAP cities sharing one polygon form one unit, so each ground series has a matching satellite unit. | 2026-09-30, `29874cf` | DEC-125 | Before H4. |
| E2 | H4 names no pollutant. | PM2.5 and PM10 are tested separately and never pooled; the all-station set is limited to stations with deweathered series. | 2026-09-30, `2254a70` | DEC-131 | Before H4. |
| E3 | Placebo in space, 500 permutations. | The permutation p-value of the primary estimate against the same 500 joint-placebo replications that give its standard error. | 2026-10-01, `eebaecc` | DEC-139 | Before any Phase 7 estimate. |
| E4 | Event study with relative years −9 to +5 and −1 omitted; 2020 dropped from the primary panel. | For the 2021 cohort, relative year −1 is calendar 2020, which is dropped, so its reference is −2. Relative years outside −9 to +5 get their own indicators rather than being binned. | 2026-10-01, `eebaecc` | DEC-142 | Before any Phase 7 estimate. |
| E5 | Callaway & Sant'Anna, doubly robust. | No covariates are added, because the registered text names none; without covariates the estimator is the unconditional difference-in-differences. | 2026-10-01, `eebaecc` | DEC-144 | Before any Phase 7 estimate. |
| E6 | Sensitivities "exclude Patancheruvu" and "Himalayan region split". | Patancheruvu has no unit of its own in the primary (it lies inside Hyderabad's centre), so its exclusion is run on the buffered-towns version. The Himalayan split changes only region × year effects, so it applies to the event study, not to SDID. | 2026-10-01, `eebaecc` | DEC-147 | Before any Phase 7 estimate. |
| E7 | Layer B: "deweathered interrupted time series" and "NCAP vs non-NCAP stations with year effects". | With one pre-year, the ITS is the before–after contrast of mean log levels. The ground DiD is estimated per listing cohort against never-treated control stations, with a cluster bootstrap stratified by cohort and control. | 2026-10-01, `eebaecc` | DEC-148 | Before any Layer B estimate. |
| E8 | "Layer A restricted to the units that have Layer B stations"; H3's "Layer A is not in the opposite direction". | Two pairs are classified (against the ground DiD and against the ITS); H3 condition (iii) holds only if neither pair is "conflict". | 2026-10-01, `eebaecc` | DEC-150 | Before any Phase 7 estimate. |
| E9 | Layer B at the 2019 balanced-panel baseline (registered sensitivity). | At that baseline the 2019 cohort has no pre-year, so it contributes no contrast; those rows cover only the cities listed in 2020–2021, and say so. | 2026-10-01, `9a04145` | DEC-157 | Found when the first run stopped with an error, before any Layer B number was written. |
| E10 | The hierarchical model of city effects, H5 and H3 (plan §5). | One SDID per treated unit with placebo-based standard errors; the moderators' coding (reference region = peninsular/other plus north-east), priors, sampler and convergence rule; H3's three specifications mapped to the Layer B series, with condition (ii) required for both estimators; the units that receive a funding dose. | 2026-10-02, `2f80dc4` | DEC-162 to DEC-166 | After the Phase 7 estimates had been seen; before any Phase 8 estimate. H3's verdict was already fixed by condition (iii), which had failed. |
| E11 | "VIIRS fire covariate (from 2012)". | Log fire radiative power within 100 km of each unit, added to the event study; the check is judged by the "agrees" rule. | 2026-10-03, `4eb69f7` | DEC-171 | After the primary estimate had been seen; before any fire value was read. |
| E12 | Raw MAIAC aerosol optical depth "if time allows", with no further detail. | The product, QA filter, aggregation, coverage rules, design and a pre-written reading of every possible outcome (two questions, read for direction only). | 2026-10-03, `85acc2a` | DEC-174 to DEC-181 | After the primary estimate had been seen; before any AOD value existed. |

## F. Analyses added after registration

None of these is a decision rule, and none can change a registered verdict.

| # | What I added | Label in the outputs | Decided | DEC | Timing |
|---|---|---|---|---|---|
| F1 | A pre-set test of whether the 2020 lockdown smears into 2019 and 2021 under the one-year-knot trend, with a rule to add a lockdown term if it did. The rule was not triggered. | Reported in the deweathering report | 2026-09-28, `f09c22e` | DEC-119, DEC-122 | Rule committed before the test was fitted. |
| F2 | Layer B re-estimated without 2019. | "added 2026-09-28" | 2026-09-28, `7ecd0a1` | DEC-123 | After the lockdown test (F1); before any Layer B estimate. |
| F3 | One station (Satna, site_1433) dropped from every registered-flags version. | "added after inspecting the data" | 2026-09-28, `7ecd0a1` | DEC-124 | After inspecting that station's data; before H4 and Layer B. |
| F4 | H4's weather part split into modelled weather and unmodelled change. H4's value and test are unchanged. | Described as an added decomposition | 2026-10-01, `86e62c7` | DEC-136 | After H4 had been seen; before the split was computed. |
| F5 | The ground DiD on city means beside the station-level DiD, and a LightGBM follow-up at the 2019 baseline. | "added before computing" | 2026-10-01, `eebaecc` | DEC-148, DEC-149 | Before any Layer B estimate. |
| F6 | Satellite SDID restricted to overlapping ranges of city population (two variants). | "exploratory, added after seeing H1" | 2026-10-01, `a90213d` | DEC-155, DEC-161 | After the H1 verdict. The second variant was written after seeing the first variant's population balance, and before either was run. |
| F7 | Satellite PM2.5 against raw AOD in the units that gained no monitor. | "exploratory" | 2026-10-03, `d43cddb` | DEC-188 | After the Phase 8b results had been seen; both group estimates were already printed. |

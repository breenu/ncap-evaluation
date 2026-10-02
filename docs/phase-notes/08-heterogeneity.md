# Phase 8: Heterogeneity and mechanism (RQ4)

**What this phase produced:**
- A city-level estimate for each of the 113 NCAP units, with a standard error.
- A Bayesian hierarchical model that pools them (the registered moderators; H5).
- The PM10 vs PM2.5 mechanism test (H3), decided by its registered rule.
- An exploratory funding dose-response on XV Finance Commission allocations.
- Figures 5, 6 and 7.
- A scoping note for the raw MAIAC AOD check.
- The generated report, [`heterogeneity_report.md`](../heterogeneity_report.md). Every number below comes from it or from DECISIONS (DEC-161 to DEC-168).

**Rules first.** Every choice the plan left open was written and pushed in `2f80dc4` before any Phase 8 number existed (DEC-162 to DEC-167). These were:
- how a city estimate and its SE are built;
- the priors, the sampler, and the convergence rule;
- how each moderator is coded;
- which model decides H5;
- how the three H3 specifications map onto the data;
- which units get a funding dose.

Nothing was re-specified after a result was seen.

**The one sentence to keep in mind.** H1 is *not identified* (Phase 7: the registered pre-trend test failed). So nothing here is an effect of NCAP. A unit's number is a **city-level relative change**: how its satellite PM2.5 moved after listing, compared with its own synthetic twin built from non-NCAP centres.

## Housekeeping from the Phase 7 review

- The old conda environment `ncap_prev` was removed. Part A had reproduced exactly in the new one (DEC-160/161).
- **DEC-155's order of events, checked in git.** Both population-overlap variants were committed together (`a90213d`) before either restricted SDID ran. Variant (ii) was written *after seeing variant (i)'s balance result* (SMD 1.63, from population alone) and *before it was run*. The causal report and DEC-155 now say this. Both variants stay, labelled exploratory.

## Step 1: one estimate per city

The Phase 7 SDID gives one number per listing cohort. To study heterogeneity you need one number per city, so each of the 113 NCAP units was given its own SDID: the unit alone against all 923 controls, with the same outcome, years and 2020 handling as the primary.

**Where the SE comes from.** For each cohort year, every one of the 923 controls in turn was treated as a fake listed unit and estimated the same way. The spread of those 923 placebo estimates is what a single unit's estimate looks like when nothing happened. That spread, an SD of about 0.05 log units (±10% at 95%), is each city's SE.

*If asked why not bootstrap or random placebos:* with a single treated unit, synthdid's own variance method is exactly this placebo approach. Running it over every control rather than a random subset removes the random draws altogether.

**What the city estimates look like:**
- The mean is +3.5%, against Phase 7's +3.6%.
- They range from −12.3% to +16.4%, and 87 of 113 are above 0.
- But each one is noisy. Unadjusted, 17 have a placebo p below 0.05. After Benjamini–Hochberg at 5% over the 113, **none** pass.

## Step 2: the hierarchical model ("eight schools")

Each city's estimate is treated as a noisy measurement of its true value, θ_i. The true values are modelled as a common average, plus the five registered moderators, plus a city-specific deviation with spread τ:
- baseline PM2.5;
- IGP;
- log population;
- coastal;
- funding channel.

Bayes then pulls each noisy estimate towards what the moderators predict, by an amount that depends on how noisy it is relative to τ. That pull is "shrinkage".

**Results** (all five model versions converged at the first attempt, with 0 divergences):
- **τ = 0.013** against per-city SEs of about 0.05. The cities differ from one another much less than their noise, so most of the spread in step 1 is noise and the estimates shrink a lot (figure 6a).
- Average city-level relative change: +3.5% (+2.6% to +4.4%).
- **Rankings are mostly uninformative.** A typical city's 95% rank interval spans 75 of the 113 places (figure 6b). This is why the plan bans a best/worst table, and the data justify the ban.
- Shrunken intervals: 62 cities lie entirely above 0, 1 entirely below, and 50 span 0.

*If asked "so which cities did best?":* the data can't rank them. Even after pooling, most rank intervals cover most of the list. The report's per-city table is alphabetical for that reason, and figure 6 has no names.

**Moderators other than IGP are exploratory.** Higher-baseline and coastal units show smaller relative rises; XV-FC units show a larger one. XV-FC is the million-plus channel, and its correlation with population is 0.72, so the two coefficients share information. None of this is causal.

## Finding 1: H5, the IGP coefficient — the registered rule is not met

- H5 predicted smaller (less negative) changes in the IGP. Rule: the IGP coefficient's 95% credible interval lies entirely above 0.
- **β_IGP = −0.3%, CrI −3.3% to +2.6%.** It spans zero, so the rule is not met.
- The IGP-only model, reported beside it and not deciding, gives −2.6% (−4.6% to −0.4%), the *opposite* direction.
- The two differ because IGP correlates 0.70 with baseline PM2.5, which the full model holds fixed, and because their reference groups differ.
- Because H1 is not identified, this is a statement about relative changes, not about whether NCAP worked less in the IGP.

*If asked "why not report the IGP-only model, which is significant?":* because the registered rule names the full model's coefficient. Choosing the version that "works" after seeing both is the forking path pre-registration exists to stop. Both are shown.

## Finding 2: H3, PM10 vs PM2.5 — inconclusive

Dust control should make PM10 fall more than PM2.5, so the PM2.5/PM10 ratio should rise. The rule needs all three conditions:

| condition | result |
|---|---|
| (i) the ratio rises, CI above 0 (ITS and DiD) | no: ITS +4.5% (CI −0.0% to +9.2%), DiD +0.6% |
| (ii) PM10 fell, and more than PM2.5, in ≥ 2 of 3 specifications (both estimators) | no: ITS 2 of 3, DiD 0 of 3 |
| (iii) Layer A does not conflict with Layer B | no: the ITS pair is "conflict" (Phase 7) |

(iii) was known to fail before this phase's rules were written, so H3 was always going to be inconclusive. DEC-165 says so in writing. The remaining choices could not change the verdict.

*If asked "is there any sign of dust control?":* the ITS ratio leans that way, but it is a before–after contrast on 11 mostly single-station cities, and the DiD against control cities shows nothing. That is not evidence either way.

## Finding 3: funding dose-response — exploratory, nothing there

- **Dose:** XV-FC air-quality *allocations* per person, FY2020-21 plus FY2021-26. Allocations are used, not releases, because releases reward cities that improved (reverse causality).
- **Sample:** 40 million-plus units. NCAP-channel cities have no allocation table, and nothing was imputed.
- **Result:** −0.4% per doubling of the dose (−3.5% to +2.7%). Adding IGP, or dropping the highest-dose unit (Patna), changes nothing.
- **The bigger caveat is in the data itself.** Allocations per person are almost identical within a state (median spread 0.7%, at most 1.5%) and differ widely between states (Rs 788 to Rs 3,746). So "dose" is really "which state", and any association would be confounded with state and region.

## Step 3: the MAIAC scoping note

[`maiac_scoping.md`](../maiac_scoping.md) answers the four questions asked. Nothing has been downloaded.

- **Product:** MCD19A2 C6.1 (MAIAC AOD, 1 km, daily).
- **Download size:** nine MODIS tiles cover all 1,036 units. Full granules for 2010–2024 come to about 330 GB, too much for this laptop.
- **Recommended route:** reduce to unit-month means on Google Earth Engine or NASA AppEEARS. That gives a table under 0.5 GB; the SDID re-run then takes about 1–1.5 h here.
- **Coarser alternatives:** the 0.05° MAIAC grid would still work with some dilution; 1° monthly products would not test leakage at city scale.

## Things that went wrong and were fixed

- **The laptop was on battery.** Windows throttled the R workers to about a tenth of normal speed, so the per-city SDIDs would have taken about 8 h. The run was stopped. `unit_sdid.R` now saves every 200 fits and resumes. On mains power, 2,882 fits take 12 min.
- **A PyMC smoke test hung.** Multi-chain sampling on Windows needs an `if __name__ == "__main__"` guard. The pipeline modules have one; the throwaway test script did not.
- **Figures 5 and 6 were re-laid out after looking at the renders:** overlapping titles, a legend over the data, colliding axis labels.
- **Figure 7's layout departs from DEC-167:** Layer A's PM2.5 reference row moved to panel (a), because on the ratio's axis it would have read as a ratio.
- **The report first said "that is why the two IGP coefficients differ".** That was a guess, so it was softened to state both reasons, untested.

## What was checked

- **Tests:** `tests/test_hierarchical.py`, synthetic only. They cover:
  - the placebo p and BH step-up;
  - SEs from placebo SDs and the pre-fit scaling;
  - moderator coding;
  - the H5 and H3 verdicts;
  - condition (ii)'s "PM10 fell, and more";
  - the co-located ratio frame;
  - every DEC-166 dose rule;
  - the PyMC model recovering a planted moderator;
  - the per-unit SDID recovering planted per-unit effects and running every placebo.
- **Convergence:** every model passed R-hat ≤ 1.01, ESS ≥ 400 and 0 divergences at the first attempt.
- **Hand checks:**
  - the mean of the per-unit estimates (+3.5%) sits next to Phase 7's +3.6%;
  - the placebo means are about 0;
  - cohorts 2020 and 2021 have identical placebo designs, as they must once 2020 is dropped;
  - the BH result is put in context: the smallest attainable p with 923 placebos is 0.0022.

**Not done:** the MAIAC check (scoped only; Reenu will run it through Google Earth Engine as Phase 8b). The VIIRS fire covariate was run on 2026-10-03, after Phase 8 closed: it agrees, and Layer A robustness is now 17 of 19 (DEC-172; addendum in `07-causal.md`).

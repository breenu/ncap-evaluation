# Phase 7: Causal analysis (RQ3)

**What this phase produced:**
- The registered confirmatory test of H1: did NCAP listing reduce satellite PM2.5 relative to comparable cities? The verdict is "not identified by this design".
- Every registered check behind that verdict: the event study, HonestDiD bounds, Callaway & Sant'Anna, the 2016 placebo, and the calibration-leakage split.
- The ground layer (ITS and DiD, PM2.5 and PM10), triangulation between the layers, and every sensitivity check in the plan's table.
- Additions from Reenu's Part A review: a fixed wording, descriptive context, one exploratory check, the leakage mechanism, and a locked environment.
- Figures 4, S1 and figure 1 with its Phase 7 step.
- A generated report, [`causal_report.md`](../causal_report.md). Every number below comes from it or from DECISIONS (DEC-138 to DEC-159).

**Rules first.**
- Every choice the plan left open, for both parts, was written and pushed before any estimate: `eebaecc` (DEC-138 to DEC-150).
- The review additions were pushed before they ran: `a90213d` (DEC-154 to DEC-156).
- So was one gap found mid-run: `9a04145` (DEC-157).
- Nothing was re-specified after a result was seen.

## The idea in one paragraph

Layer A compares the 113 NCAP urban centres with 923 comparable non-NCAP centres on satellite PM2.5, 2010–2024, using synthetic difference-in-differences (SDID). SDID builds each listed group a weighted "synthetic twin" from the controls, chosen to track its pre-2019 path, and asks whether the listed group moved away from its twin after listing.

The plan says in advance what would count as support (rules a–d) and what would make the design unable to answer at all: pre-trends that are not parallel (rule b), or a fake 2016 "effect" (rule c).

## Finding 1: H1 is not identified by this design

| Registered rule | Result | Met |
|---|---|---|
| (a) SDID estimate < 0, CI below 0 | +3.6% (+2.4% to +4.8%) | no |
| (b) pre-period event-study coefficients jointly zero (Wald p > 0.10) | p = 0.0008 | **no** |
| (c) 2016 placebo CI includes 0 | −0.1% (−0.9% to +0.7%) | yes |
| (d) sign negative in CS, area-weighted, V6.GL.03 | +4.6%, +3.5%, +3.2% | no |

Rule (b) fails, so the first branch of the fixed verdict applies: **not identified by this design**. That holds whatever the estimate is.

**The fixed wording (DEC-154), which always travels with the verdict:** *NCAP units' satellite PM2.5 did not fall relative to comparable units; the estimates point to a relative rise of about 3–5%.* It is never described as an effect of NCAP.

*If asked "so NCAP made air worse?":* no.
- The design cannot attribute anything to NCAP, because its own pre-trend test fails.
- What the data show is descriptive: both groups' PM2.5 fell after 2018 (NCAP units −16.8%, the control pool −24.3%, 2018 → 2024), and the NCAP units fell less.
- The cities that were listed differ from the controls in ways the design does not fully absorb: much bigger cities, and fewer of them in the IGP.

*If asked "why does the pre-trend test fail when the pre-coefficients look flat?":*
- They are small: −1.6% to +0.8%.
- But the satellite series is so smooth that each is estimated to within about ±1%, so even small, irregular wiggles are "significant". One year (l = −7) has z ≈ −3.1.
- I checked on synthetic panels that the test is not over-rejecting: it rejects at the nominal rate when nothing is planted (DEC-152).

*If asked "why not just report the SDID number then?":* because the plan registered, before any result, that a failed pre-trend test means "not identified". Changing that after seeing the result would be exactly the forking path pre-registration exists to stop.

## Finding 2: the other Layer A checks tell the same story

- **HonestDiD.** The average post-period event-study estimate is +3.1% (+1.7% to +4.5%). It stays clear of zero only if post-listing departures from parallel trends are at most 0.2 times the largest pre-listing one (breakdown M̄ = 0.20). That is fragile.
- **Robustness:** 16 of 18 registered checks agree with the primary, and every Layer A estimate is positive. The two that don't "agree" are smaller but still positive:
  - V6.GL.02.04, the older calibration vintage: +1.4%;
  - excluding the IGP: +1.9%.
- **Leave-one-out:** dropping any one of the 923 donors moves the estimate by at most 0.0003.
- **H2 (winter) was not tested,** because H1 is not supported. Exploratory: winter and non-winter move alike (difference +0.1%).

## Finding 3: calibration leakage, a warning the design cannot resolve

ACAG calibrates satellite PM2.5 to ground monitors, and NCAP added monitors mostly in listed cities. Split by whether a unit gained a monitor in 2019–2024:

| | Estimate |
|---|---|
| Gained a monitor (74 units) | +2.5% |
| Did not (39) | +5.5% |
| Difference | −2.8% (−5.1% to −0.5%) |

The registered warning rule fires: the difference is negative with a CI excluding 0. Phases 3 and 6 found new stations read about 6% cleaner than existing ones, and not because of weather. If ACAG absorbed those cleaner readings, the satellite would be pulled down exactly where monitors were added, which is the direction seen.

*If asked:* this is a possible mechanism, not a finding. The calibration inputs are not observed, and the two groups also differ in size and pollution.

## Finding 4: the ground layer, and why it seems to "conflict"

Layer B uses deweathered ground data on the same balanced panel as H4: 18 PM2.5 cities and 13 PM10 cities, almost all single stations, against only 5–6 control cities. It is secondary and has one pre-year.

| | PM2.5 | PM10 |
|---|---|---|
| ITS (before–after, NCAP cities only) | −14.0% (−22.7% to −5.3%) | −5.0% (−11.3% to +1.7%) |
| Ground DiD (against control stations) | −4.7% (−13.4% to +4.7%) | +9.2% (−0.7% to +23.5%) |

**Triangulation** (Layer A restricted to the same 18 cities: +3.8%):
- against the ground DiD: **uninformative** (the ground CI is too wide);
- against the ITS: **conflict**, which triggered the registered four-step investigation.

**The investigation's key step is 3.** Over the same cities and years, the satellite's own before–after change is −11.1% (at the stations' cells) or −11.2% (over the polygon), and the ground panel's is −13.4%. **Ground and satellite agree** that air in these cities got cleaner.

The "conflict" is between two different questions:
- the ITS: did these cities get cleaner? Yes.
- Layer A: did they get cleaner *than comparable cities*? No.

*If asked "which layer is right?":* both, for their own question. The ITS cannot separate national trends from anything else, which is why it is secondary.

## Finding 5: the exploratory size check (added after seeing H1; cannot change the verdict)

City size was the largest pre-registration imbalance. Restricting both groups to overlapping population ranges gives:
- min–max common support: +3.7%;
- 5–95% overlap: +3.0%, with the imbalance halved.

The relative rise is not an artefact of comparing megacities with small towns.

*If asked why the min–max version barely helps:* the control pool is concentrated at 100,000–200,000 people, so trimming the ends of the range doesn't make the two size distributions alike. That is why a second variant was written down before running anything.

## Finding 6: the 2019 question from Phase 5/6

The GAM's fitted annual means sit 3.7% below the observed in 2019 (PM2.5), against 3.3% above in 2018; LightGBM's misfit is about 1–2% in both years.
- At the 2019 baseline, that misfit sits in the baseline year. That is consistent with what DEC-137 saw (the GAM's raw − deweathered part being almost all unmodelled change), and with the lockdown smear landing on 2019. The mechanism itself is untested.
- At the 2018 baseline, dropping 2019 hardly matters: ITS −14.0% → −15.0%.

## Things that went wrong and were fixed

- **The R environment broke mid-session.** conda-forge's `Matrix` stopped loading on Windows (the DLL-layout problem of DEC-093), taking `did` and `mgcv` with it. CRAN's builds of the same versions are now locked in on Windows (DEC-138, DEC-156). The new environment was built from the edited lock and all 199 tests passed in it.
- **Code-review catches before first use:**
  - estimand names that would have summed across outcomes (DEC-152);
  - a city-level DiD map that dropped its own key column (found on the first real Layer B run; fixed and tested).
- **The 2019-baseline gap:** at that baseline the 2019 cohort has no pre-year. It was logged before any Layer B number existed (DEC-157).
- **CI's DAG check failed** on outputs that Phase 3's EDA had never declared. Reproduced on a fresh clone and fixed (DEC-158).
- **Figure 4 was re-laid out after looking at the render.** Callaway & Sant'Anna's pre-listing points are year-on-year differences, so the figure now says the two estimators are like-for-like only after listing.

## What was checked

- **Tests:** 24 synthetic tests in `tests/test_causal.py`. They cover:
  - the SDID engine recovers a planted effect and resumes without recomputing;
  - Sun & Abraham recovers cohort-weighted dynamics, the cohort-2021 reference, and the 2020 own coefficient;
  - the Wald algebra, and that the test detects a planted pre-trend;
  - CS recovers a planted effect with 2020 dropped;
  - HonestDiD runs;
  - every branch of the H1 verdict, the equivalence bounds and the layer categories;
  - the closed-form ground DiD equals TWFE OLS exactly;
  - the stratified bootstrap;
  - DEC-157's empty cohorts.
  
  The full suite has 199 tests.
- **Hand checks:**
  - the event-study aggregation by hand;
  - an unweighted DiD of means (+5.0%) confirming the positive sign is in the data;
  - CS never vs not-yet-treated differing only where they should;
  - Layer B's PM2.5 ITS (−14.0%) close to H4's corrected change for the same cities (−14.1%; a different quantity: an endpoint change, not a before–after mean).
- **Reproducibility (DEC-160):** Part A and every quick Part B step were rebuilt in the new environment.
  - 272 of 300 output files are byte-identical, including every SDID replication. The rest differ by at most 1.4e-13 (floating-point order), or only in a timestamp.
  - `causal_report.md` came out unchanged line for line.
  - Part B's SDID outputs were carried over from the old environment (Reenu's choice), with their specification hashes confirmed unchanged.

**Not run:** the VIIRS fire covariate (FIRMS not yet downloaded) and raw MAIAC AOD (registered "if time allows").

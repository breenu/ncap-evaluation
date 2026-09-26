# Phase 4: The analysis-plan gate

**What this phase produced:**
- the numbers the analysis plan needed before it could be approved, all computed on data up to 2018 only: minimum detectable effect, control pool, baseline balance, and whether a ground PM10 MDE is possible;
- the finished plan, `docs/analysis_plan.md`, laid out in OSF's Preregistration format;
- a one-page summary, `docs/analysis_plan_summary.md`.

The generated evidence is `docs/pregate_checks.md`. Every number below comes from it.

The gate is still closed. Nothing has compared NCAP with non-NCAP cities after 2018.

## Why this phase exists

Pre-registration means writing down *before looking* what will count as evidence. The risk it guards against is the "garden of forking paths": with dozens of reasonable choices (which satellite version, which years, which controls, how to treat 2020), an analyst who has seen the results can drift, even honestly, towards the choices that give a clean story. Fixing the choices first, and making the code refuse to run the real analysis until they are fixed, removes that option.

Two things needed computing first, both allowed because they use only pre-2019 data:
- **How small an effect the design can detect.** A null result is only informative if you know what it rules out.
- **How similar the NCAP cities are to the controls before NCAP.**

**How "pre-2019 only" is enforced.**
- The code filters `year ≤ 2018` inside the Parquet reader, so later rows are never loaded, and asserts it afterwards.
- The R script checks again.
- Winter seasons crossing into 2019 are dropped.
- A test proves the reader cannot return 2019.

## Finding 1: the comparison group

- **Treated:** 113 GHSL urban centres hold an NCAP city.
- **Controls:** of the 1,810 non-NCAP centres, 924 had at least 100,000 people in 2015. Dropping Kalka, which contains the NCAP town Parwanoo, leaves **923 controls**.
- **Spillover buffer (sensitivity):** controls must be at least 25 km from any NCAP place, leaving 754. At 10 km 852 would remain, at 50 km 511.

*Why 2015 population?* It is before treatment. Using a later year would let NCAP itself (if it changed growth) decide who is a control.

*Why 25 km?* It is the audit's neighbour radius, roughly one airshed. Cleaner air in a treated city could drift into a nearby control and make NCAP look *less* effective.

## Finding 2: NCAP cities are bigger, not dirtier, than the pool

| | NCAP units | Controls | SMD |
|---|---|---|---|
| PM2.5, 2010–2018 mean | 51.7 µg/m³ | 56.4 µg/m³ | −0.22 |
| PM2.5 trend, 2010–2018 | +2.3%/yr | +2.1%/yr | 0.17 |
| Population (log10) | 5.94 | 5.32 | **1.44** |
| Share in the IGP | 28% | 43% | −0.31 |

The surprise is that NCAP units are *not* more polluted than the pool on average. The pool is full of Indo-Gangetic Plain towns, the most polluted region in the country, and NCAP cities are spread more widely.

**Why the big population gap is acceptable.** SDID does not need controls to match on levels. City fixed effects absorb permanent differences. What it needs is that the synthetic control *moved like* the NCAP cities before 2019. It chooses control weights to make that happen, and the pre-trends are already close. Population is a moderator in Phase 8, and a sensitivity run restricts the treated units to ≥ 100k.

## Finding 3: the minimum detectable effect is about 1.2%, and that is a best case

**How it was computed.**
1. Pick 113 control cities at random and pretend they joined NCAP in 2014 (or 2015).
2. Run SDID against the other 810.
3. Repeat 500 times.

No real treatment happened, so the spread of these fake effects is pure noise: SE ≈ 0.4 log points (about 0.4%). The minimum detectable effect is 2.8 × SE, i.e. **about a 1.2% reduction** (0.9 µg/m³).

*Where 2.8 comes from:* 1.96 (for a 5% two-sided test) + 0.84 (for 80% power).

**Why so small?** Two reasons:
- ACAG satellite PM2.5 is a smooth, calibrated surface, so year-to-year noise in a city average is small.
- Averaging over 113 cities shrinks it further.

**Why it is a best case, not a promise:**
- the real design's post-period reaches six years after adoption, where synthetic controls drift more;
- it averages three adoption cohorts;
- the post-period contains COVID and the BS-VI fuel switch, which the pre-period does not.

The confidence intervals in Phase 7 use the real design's own placebo SE, not this number. The MDE's job is to set the equivalence bound: if the result is null, can we rule out effects bigger than ±1.2%?

**A check that failed to find a problem, and a small one it did find.** I expected random sets to *understate* noise, because 113 random controls are scattered across India and average away regional shocks, while the real NCAP set is regionally clustered. So I added a second null in which each fake set has the same regional mix as the real one. That was my prediction; the data disagreed:
- Matched sets were slightly *less* noisy (SE 0.36–0.37 vs 0.41–0.42), so the carried MDE still comes from the random design.
- Matched sets are not centred exactly on zero. Their mean fake effect is up to −0.5 log points, against a Monte Carlo error of 0.02, so the offset is real.
- SDID has a small bias when the treated group shares a regional structure the donors lack. It is below one SE and it is reported.

## Finding 4: the real NCAP cities were not already diverging before NCAP

The same fake starts, applied to the actual NCAP units (data to 2018 only):
- **2014:** +0.47 log points (95% CI −0.25 to +1.18; permutation p = 0.22);
- **2015:** −0.41 log points (95% CI −1.14 to +0.32; p = 0.41).

Both intervals include zero. This matters: if NCAP cities had already been improving faster before 2019, any post-2019 "effect" could just be that trend continuing.

This check was run *before* the plan's decision rules were final. So the plan keeps the Phase 3 draft's rules for H1 unchanged and lists every other change made afterwards (§6 of the plan) for Reenu to judge.

## Finding 5: no honest MDE exists for ground PM10

An MDE needs to know how much the NCAP-minus-control *change* wobbles when nothing happens. That takes at least two pre-NCAP years on both sides.
- **Control side:** non-NCAP cities have **zero** valid PM10 station-years before 2018.
- **NCAP side:** only 6 stations in 5 cities are valid in both 2017 and 2018.

So a ground placebo cannot be built. A variance from one year-pair in five cities would be a number, not an MDE. The plan says this plainly. Ground PM10 results, including the dust-control test H3, are secondary and can never be "confirmed".

## Treatment timing

- **Primary: date of first listing.** Listed by 30 June counts as treated that year; nothing before 2019. This gives unit cohorts of 89 (2019), 15 (2020) and 9 (2021).
- **Alternative: first year money arrived,** counted from the calendar year after the financial year of the first central release: 86 (2020), 25 (2021), 2 (2022).
  - *Why the year after:* a release late in FY2019-20 cannot pay for a year of action in 2019.
  - Every one of the 131 cities has a dated first release in the Lok Sabha answers, or is an XV-FC city (grants from FY2020-21).

## What the plan adds beyond the Phase 3 draft

- **Multiple comparisons.** H1 and H2 form the confirmatory family, tested in fixed sequence: H2 (winter effect larger) only counts if H1 is supported. This keeps the familywise false-positive rate at 5% without halving the threshold. H3–H5 are secondary. City-level claims come from shrunken estimates, or BH-FDR at 5%.
- **H4 and H5.** The proposal's own pre-registered hypotheses (weather and new monitors explain part of reported gains; smaller effects in the IGP) had been left out of the draft.
- **Layer disagreement.**
  - Satellite and ground are compared like for like: the same cities, PM2.5.
  - Each comparison is labelled consistent / different magnitude / conflict / uninformative.
  - Any disagreement triggers a fixed four-step investigation. The two layers are never averaged.
- **The sensitivity table.** Every choice Reenu made, each with its check: the valid-hour rule, population weighting, 2025 vs Q1 2026, the 10 towns, Patancheruvu, Raniganj, the 5 stations.
- **Event-study estimator.** Sun & Abraham instead of plain two-way fixed effects. With staggered adoption, two-way fixed effects can weight some comparisons negatively (Goodman-Bacon 2021).

## Problems met

- **R `mgcv` stopped loading** on this machine. The error is a MinGW "32-bit pseudo relocation out of range": a DLL linked in a way that breaks when Windows places another DLL more than 2 GB away, which varies with address randomisation.
  - It fails in almost every try (one pass in about 20).
  - Ruled out: PATH clashes (Oracle, old MinGW, Git's toolchain).
  - CRAN's build of the same version works every time. It is not installed yet, because it changes the pinned environment (DEC-090).
  - Phase 4 does not use mgcv; Phase 5 does. `test_r_estimators_run` fails until it is fixed.
- **The placebo run was slow.** Each SDID fit took 4.6 s because MKL was spinning up threads. With one BLAS thread per R worker, a fit takes 0.5 s, and 8,000 fits take about 35 minutes.
- **A balance check that was wrong, not the data.** Winter seasons end in February of the next year, so with data to December 2018 there are 8 winters but 9 non-winters. The first version called that "unbalanced". Both seasons now use 2010–2017.
- **Editing `params.yaml` dirties every rule in Snakemake**, because every rule lists it as input. Only new Phase 4 keys were added, and no Phase 3 code reads them. So the Phase 4 rules were run through Snakemake on their own (`--allowed-rules`; log `data/interim/logs/snakemake_pregate_phase4.log`), rather than repeating the one-hour Phase 3 rebuild. Afterwards the new Python files were auto-formatted (whitespace only); rerunning the panel step with the formatted code gave byte-identical outputs (sha256), so the outputs were marked current with `snakemake --touch` instead of repeating the 35-minute placebo run.

## If asked…

- *"Isn't a 1.2% MDE suspiciously good?"* Yes, and the plan says so. It is a lower bound from a smoother, shorter placebo design, and the real CIs use the real design's SE. Its only formal job is the equivalence bound.
- *"You looked at NCAP vs control before writing the rules. Isn't that cheating?"* Only pre-2019 data, which pre-registration allows. The H1 rules were written before; every later change is listed in the plan for the reviewer.
- *"Why is the satellite primary when NCAP targets PM10?"* Only the satellite has a pre-period long enough to test whether NCAP and control cities moved together before 2019. The ground network has one year. The report states that satellite PM2.5 says nothing directly about PM10 targets.

## Open items for Reenu

1. Approve or edit `docs/analysis_plan.md`. Numbers are generated, so edit prose only.
2. Decide: listing vs funding date as primary; H4/H5 and the Asansol-alone check.
3. OSF registration: yes or no, before the gate opens.
4. OK to install CRAN's mgcv 1.9-4 (DEC-090)?

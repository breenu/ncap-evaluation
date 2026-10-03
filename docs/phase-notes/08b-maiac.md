# Phase 8b: Raw MAIAC AOD, a satellite signal no monitor calibrates

**What this phase produced:**
- The registered "if time allows" check under the calibration-leakage threat (plan §5): Layer A's design re-run on raw MODIS MAIAC aerosol optical depth (AOD), which uses no ground monitors.
- The export from Google Earth Engine, with its raw tables and manifest.
- A new section, §12, in [`causal_report.md`](../causal_report.md), plus one row each in the robustness table and the triangulation investigation.
- A data card, [`data-cards/maiac_gee.md`](../data-cards/maiac_gee.md).

Every number below comes from the report or from DECISIONS (DEC-174 to DEC-187).

**The one sentence to keep in mind.** H1 is still "not identified by this design". The registered pre-trend test failed in Phase 7, and nothing here touches that test. So nothing in this note is an effect of NCAP, and every AOD number is a *relative change in AOD*, not in PM2.5.

## Why this check exists

ACAG's satellite PM2.5, the headline outcome, is calibrated to ground monitors, and NCAP added monitors mostly in NCAP cities. In Phase 7 the pre-specified leakage warning fired:
- units that gained a monitor showed a smaller relative rise (+2.5%) than units that did not (+5.5%);
- the difference was −2.8%, with a CI that excludes 0.

New monitors read cleaner than the old ones (Phase 6). If ACAG calibrated to them, the satellite values of the units that gained monitors would be pulled down. That is the direction of the gap. But the gained group also differs in size and pollution, so Phase 7 could not separate the two explanations.

Raw AOD is the satellite's own aerosol measurement, before any calibration to monitors. If the gap is a calibration artefact, it should vanish in AOD. If it is a real difference between the groups, it should still be there.

*If asked "why not just compare the two satellite products?":* the V6.GL.02.04 vintage check did that in Phase 7. But both vintages are calibrated to monitors, only to different sets of them. AOD is the only signal here with no monitor in it.

## Rules first

The full specification was pushed in `85acc2a`, before the Earth Engine API was even installed. It fixed:
- the QA filter;
- how unit-month and annual values are formed;
- the coverage rules;
- the design;
- the reading of every possible outcome (DEC-174 to DEC-181).

Implementation choices were logged before any AOD value existed (DEC-182 to DEC-185).

**The pre-written reading (DEC-180).** AOD measures the whole column of air, not the air people breathe. Its link to surface PM2.5 depends on boundary-layer height, humidity and aerosol type. So the check reads **direction, not size**. Two questions, each with categories fixed in advance:
- **Q1: does the relative rise appear in AOD?**
- **Q2: does the gained/not-gained gap appear in AOD?**

Sizes enter only as a yardstick: ACAG estimated on exactly the same units. If the AOD interval is wide enough to contain both 0 and ACAG's estimate, the result is "uninformative". This mirrors the registered rule for comparing layers.

## Step 1: getting the data (Earth Engine)

**Product.** MCD19A2 C6.1 at 1 km, both MODIS satellites, best-quality retrievals only (clear sky, normal adjacency, QA "best"), at 0.55 µm. A relaxed filter is a sensitivity check, because MAIAC can mistake thick winter haze for cloud.

**From pixels to a unit-year:**
1. Average each pixel's overpasses within a day.
2. Average the valid days within a month.
3. Take the population-weighted mean over each unit's GHSL polygon, as Layer A does.
4. Annual value = the mean of the valid months.

A month counts if half the unit's population sits under pixels with data and the average pixel has at least 4 clear days. A year counts if at least 6 of its 8 non-monsoon months do. Monsoon months are never required: July and August are valid only 4–8% of the time.

**Three things that went wrong, and what was done:**
1. **The project had no place to store exported tables** (no Earth Engine asset area). The export went to a private Google Drive folder instead. Each file's md5 is checked on download. Computation unchanged (DEC-183).
2. **The one-month pilot projected about 260 compute-hours**, above the 100 I had set as a stop rule and above the free tier's 150 a month. So I stopped and asked. Reenu moved the project to the Contributor tier, and the limit was raised to 400 before anything was submitted (DEC-184/185). The real export used 168.
3. **Re-locking the environment to add `earthengine-api` re-solved everything** and moved about 40 unrelated packages. I discarded that and inserted only the 30 new packages; nothing existing changed (DEC-182).

**Checks before the analysis:**
- **Weights.** Earth Engine's population weights against ours, unit by unit: a median of +3.4% apart, correlation 0.9995. The stop rule was 10%, so this passed.
- **Tiles.** Restricting the satellite tiles to the 9 over India changed no value (two pilots agree to 4 in 100 million).

## Step 2: the analysis

Layer A's design, unchanged:
- SDID per listing cohort;
- never-treated controls;
- 2020 dropped;
- 500 joint-placebo replications;
- the monitor-gain split.

Units need a complete AOD series. That keeps **95 of 113 treated and 741 of 923 controls**. Most of the drops are coastal (cloud).

Because the sample changed, every AOD estimate sits beside **ACAG PM2.5 on exactly the same units**. On those units ACAG gives +4.2%, against +3.6% on the full sample.

## Finding 1, Q1: the relative rise is not reproduced in AOD (with a caveat)

- **Primary: AOD +0.8% (95% CI −0.4% to +2.0%), against ACAG +4.2% (+2.7% to +5.6%) on the same units.** The AOD interval includes 0 and excludes ACAG's estimate: "rise not reproduced".
- **Not robust across specifications:**
  - The non-monsoon annual mean gives +1.5% (+0.4% to +2.6%), which by itself would be "rise also in AOD".
  - The event study (information only) gives +1.3% (+0.1% to +2.6%).
  - Area-weighted (+0.8%), relaxed QA (+0.4%) and the 17 Layer B units (−2.0%) agree with the primary.
- **The fair summary:** AOD's relative change is small, and whether it is above 0 depends on the specification. In every specification it is below ACAG's on the same units.

**What it means (written before the data):** either something in ACAG's processing produced part of the rise, or the link between column AOD and surface PM2.5 changed differently in NCAP units. This check cannot tell which.

*If asked "so the rise is an ACAG artefact?":* no, that doesn't follow. AOD is not PM2.5. A city whose boundary layer, humidity or aerosol mix changed could see surface PM2.5 move differently from the column. All the check says is that the uncalibrated signal shows less of the rise.

## Finding 2, Q2: the monitor-gain gap is absent from AOD

| | AOD | ACAG, same units |
|---|---|---|
| gained a monitor (64 units) | +1.2% | +2.8% |
| did not (31 units) | −0.4% | +7.1% |
| **difference** | **+1.6% (−0.8% to +4.0%)** | **−4.1% (−6.7% to −1.4%)** |

On the same units, ACAG's gap is even larger than in Phase 7, but in AOD it disappears. The point estimate has the opposite sign, and the interval lies entirely above ACAG's gap. Under the pre-written rule: **"gap absent from AOD (consistent with calibration leakage)."**

**What it means:** this is what calibration leakage would produce. It is consistent with leakage, not proof: if the AOD–PM2.5 link changed differently in the two groups, the result would look the same.

*If asked "is this evidence of leakage?":* it is the pattern leakage predicts, in the one signal that leakage cannot reach. Together with Phase 6's finding that new monitors read cleaner, it makes leakage a more plausible explanation of the Phase 7 gap than it was. But it is still circumstantial, and the plan calls the original rule a warning, not proof.

## Finding 3: the event study on AOD

The pre-trend test fails on AOD too (p = 0.005), as it did on PM2.5. The pre-listing coefficients are jointly different from zero in a signal with no monitors in it, so the pre-trend problem is not only an ACAG problem. It is one more reason to report H1 as "not identified" and not to read any estimate as an effect. The test decides nothing here; it is reported for information.

## What changed elsewhere

- **Robustness table:** the "Raw MAIAC AOD" row now has a number, but "agrees" is "—". A change in AOD is not on the PM2.5 scale, so the "17 of 19" count is unchanged.
- **Triangulation investigation, step 2:** one new row (the 17 Layer B units on AOD, −2.0%). The two registered pair categories are unchanged: they compare ground PM2.5 with satellite PM2.5, and AOD is neither.
- **H1–H5:** all unchanged.

## What was checked

- **Tests:** `tests/test_maiac.py` (11, synthetic only). They cover:
  - every QA bit and both filters;
  - the unit-month ratios;
  - the month and year rules;
  - complete-series selection;
  - every branch of Q1 and Q2;
  - and that the engine change leaves Phase 7's specs as they were.
- **Phase 7 untouched:** after the engine change, all 19 Phase 7 spec hashes are identical.
- **Reproducibility:** the whole Phase 8b chain re-run through Snakemake reproduced the report byte for byte. The event-study numbers differ only at 10⁻¹³, and the SDID engine recomputed nothing.
- **0 solver warnings in any fit.**

## Limits to state in an interview

- **AOD is not PM2.5.** Read direction only.
- **Clear days only.** AOD sees only clear days; the monsoon is mostly missing, and the annual mix of months varies from year to year (the non-monsoon version reduces this, and it is the one that differs).
- **Sample.** The AOD sample drops 18 treated and 182 control units, most of them coastal. The same-units ACAG yardstick handles the comparison, but the result describes those 95 units.
- **Satellite drift.** Terra's and Aqua's overpass times drifted late in the record. This affects every unit alike unless the daily aerosol cycle differs between groups.
- **Earth Engine is not byte-reproducible.** A rerun agrees to about 8 significant figures.

## Addendum after review (2026-10-03): where no monitor was added (exploratory; DEC-188/189)

Reenu asked one more question: do ACAG and AOD also disagree in the units that gained **no** monitor? Those units had no new monitors for ACAG to calibrate to. A disagreement there cannot come from monitor leakage.

| group | AOD | ACAG, same units |
|---|---|---|
| no monitor added (31 units) | −0.4% (−2.3% to +1.6%) | +7.1% (+4.7% to +9.6%) |
| monitor added (64 units) | +1.2% (−0.2% to +2.7%) | +2.8% (+1.1% to +4.5%) |

**They disagree, and they disagree most where no monitor was added.** So monitor leakage cannot explain the overall gap between ACAG and AOD. Something else is needed, for example the link between column AOD and surface PM2.5 differing between NCAP and control units, or something in ACAG's processing.

This changes how to read Q2. "Gap absent from AOD" looked like the leakage pattern. But the gap comes mostly from ACAG being high in the units *without* new monitors, which is not the mechanism leakage describes: leakage would push ACAG down where monitors were added. The registered Q2 classification stands, but as evidence for leakage it is weaker than it first looked.

*If asked "so was it leakage or not?":* the evidence no longer points to leakage specifically. The pre-specified Q2 rule says "consistent with leakage". The follow-up, which I labelled exploratory because it came after seeing the results, shows the ACAG–AOD disagreement is largest where leakage is impossible. The honest answer: ACAG and raw AOD disagree about NCAP units in general, and this project cannot say why.

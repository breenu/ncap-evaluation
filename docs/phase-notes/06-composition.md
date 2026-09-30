# Phase 6: Network composition, ground vs satellite, and H4 (RQ1)

**What this phase produced:**
- For every city (GHSL urban centre) with ground data, three annual trends:
  - all stations as reported;
  - a balanced panel of stations valid every year from 2018 (2019 as sensitivity);
  - satellite PM2.5 over the same polygon, to 2024.
- Per city: composition bias (all stations − panel) and the ground − satellite gap, with uncertainty.
- H4, the registered secondary hypothesis, computed as registered and under every version Reenu asked for.
- Phase 3's "do new stations read cleaner?" redone on deweathered data.
- A diagnostic of why GAM and LightGBM disagree for some cities.
- Figure 1, version 1 (the decomposition), with the policy step left as a marked placeholder.
- A generated report, [`composition_report.md`](../composition_report.md). Every number below comes from it or from DECISIONS (DEC-125 to DEC-134).

**Rules first.** Every definition was written into DECISIONS and committed before any Phase 6 number existed: `29874cf` (DEC-125 to DEC-130) and `2254a70` (DEC-131). That includes the sign of H4, which version is primary, and how uncertainty is computed.

## The idea in one paragraph

A tracker compares a city's 2025 average with its 2018 average. Three things move that number besides policy:
- **Weather:** 2025 may simply have been a windier, better-mixed year. Phase 5 removed that.
- **Which monitors exist:** Kolkata had 1 valid PM2.5 station in 2018 and 13 in 2025. If the new ones sit in cleaner neighbourhoods, the city average falls even if nobody's air changed. This is "the treatment changed the thermometer": NCAP paid for many of those monitors.
- **Policy**, which Phase 7 estimates.

A **balanced panel** (only the stations that measured every year) removes the second effect by construction. The gap between "all stations" and "panel" is the composition bias.

## Finding 1: H4 is supported, for both pollutants and both model families

H4 (registered): reported, raw, all-station improvements in NCAP cities exceed deweathered, composition-corrected improvements.

**A sign problem, caught before computing (DEC-127).** The registered decision rule says "raw change minus deweathered change … supported if positive". Measured as changes in concentration (a fall is negative), a bigger reported fall makes that difference *negative*, the opposite of the hypothesis. The hypothesis text is unambiguous, so "change" is read as "improvement". This is logged as a clarification to be listed beside the deviations.

*If asked "did you flip the sign to get a positive result?":* no. The reading was committed (`29874cf`) before any number was computed, and both readings test the same statement: the reported fall is bigger than the corrected one.

**Primary version** (GAM, ±15-day resampling, near-constant years excluded, 2018 panel):

| | PM2.5 | PM10 |
|---|---|---|
| NCAP cities with a panel | 18 | 13 |
| Reported change 2018 → 2025 (mean) | −23.6% | −9.6% |
| Corrected change | −14.1% | −3.6% |
| **H4 (reported fall − corrected fall)** | **+9.5 pp (95% CI +4.8 to +14.5)** | **+6.0 pp (+1.8 to +10.0)** |
| … weather part | +3.7 | +4.9 |
| … composition part | +5.8 | +1.0 |
| LightGBM beside it | +8.6 (+4.7 to +12.6) | +5.3 (+3.1 to +7.7) |
| As registered, no deviations (old GAM trend, Grange & Carslaw, registered flags) | +10.3 (+5.3 to +14.8) | +6.5 (+3.9 to +9.5) |

**Across all 31 versions per pollutant:** H4 holds in 31 of 31 for PM2.5 and 29 of 31 for PM10. The two that fail are both PM10:
- **LightGBM with the 2019 baseline:** +1.7 pp (−0.1 to +3.5).
- **No deweathering:** +0.1 pp (−2.1 to +2.4). Without deweathering, H4 measures composition alone.

**What this means, with its caveats:**
- **PM2.5:** roughly 40% of the average reported fall disappears once weather and monitor changes are removed. Composition is the larger part.
- **PM10:** the gap is mostly weather. Composition barely moves PM10, and without deweathering PM10's H4 is essentially zero.
- **The weather part rests on two single years.** H4 is defined on the 2018 and 2025 endpoints, and 2025's weather was favourable (the Phase 5 report put the network-level weather effect at about −3% in 2025). A different end year could give a different weather part. This is a property of the registered quantity, not something to fix here.
- **The panels are thin.** 16 of 18 PM2.5 panels and 11 of 13 PM10 panels hold one station, so a city's "corrected" change is often one monitor's record.
- **It is descriptive, not causal.** H4 says reported numbers overstate improvement. It says nothing about whether NCAP worked; that is Phase 7's question.

**The version where it could have gone wrong but didn't matter for H4.** The as-registered family (old GAM trend under all-year resampling) has the Phase 5 blow-ups (DEC-115). In the H4 cities, 3 station-years in the all-station sets are outside the extrapolation guard, and none in the panels. H4 uses only the panel, so it is unaffected. But that version's weather/composition split is nonsense (+29 / −19 pp for PM2.5), and the report says so.

## Finding 2: composition bias is real for PM2.5 and appears from about 2022

Across all 23 cities with a PM2.5 panel (NCAP or not), composition bias by 2025 = **−3.7 pp (95% CI −7.2 to −0.4)**. The changing station set makes cities look about 4 points cleaner than their continuous monitors. PM10: +0.9 pp (−1.1 to +3.3), i.e. none detectable.

By year (PM2.5), the bias is near zero until 2021, then −1.8 (2022), −4.1 (2023), −3.4 (2024) and −3.7 (2025). By 2025, 13 of the 23 cities measure with a different set of stations than their panel. The biggest single cases:
- Hyderabad −22 pp (5 → 9 stations);
- Kota −19;
- Chennai −17;
- Kolkata −15.

It is not one-directional: Ahmedabad is +13 (its new stations read dirtier than its one continuous station).

## Finding 3: ground and satellite agree on average, not city by city

PM2.5, 2018 → 2024 (the satellite ends in 2024):
- **On average:** panel change minus satellite change = +3.0 pp (95% CI −5.0 to +10.6) over 23 cities. The two changes correlate at 0.68 across cities.
- **City by city, gaps are large.** Single monitors in Agra, Lucknow, Kanpur and Jodhpur fell 45–63%, while the satellite over the same polygon fell 22–27%.
- **A single monitor is not the polygon.** It measures its own street, and the satellite (population-weighted) is smooth by construction.

This is the input to Phase 7's triangulation rule (plan §5, step 1–3 of the investigation).

## Finding 4: new stations do read cleaner, and it is not the weather

Phase 3 found new PM2.5 stations read about 6% cleaner than the existing ones in the same city and year. The question here: could that be the weather of their first year? No.

| PM2.5 | raw | deweathered (GAM) | paired difference |
|---|---|---|---|
| New vs existing stations | −6.3% (−11.7 to −0.3) | −6.8% (−12.4 to −0.9) | −0.6 pp (−2.2 to +1.1) |

Entrants and incumbents in the same city share the same year's weather, so weather should cancel, and it does. The gap is about *where* the new monitors are. PM10 shows no gap either way (−1.5%, CI −6.9 to +5.3).

## Finding 5: why GAM and LightGBM disagree for some cities

**The question.** For 13 city-pollutants, the GAM and LightGBM deweathered changes 2018–2025 differ by more than 5 points under at least one resampling scheme. Kolkata was named in advance and meets the rule anyway. All 13 are one-station panels. Kolkata PM2.5 is the extreme: GAM −1.9%, LightGBM −14.6%, against a raw −18.4%. Is one family crediting some weather variable the other ignores?

**The pre-set method failed its own check, and I replaced it (DEC-133).**
- DEC-130 split each model's weather effect into variables on the log scale. It required the pieces to add up to the family's implied weather change; they did not (Kolkata GAM: −3.5 against −18.4).
- **Scale.** H4 is about *arithmetic* annual means, and Kolkata's fall is concentrated on the most polluted winter days. Its mean log PM2.5 fell only 6.8 points, while its arithmetic mean fell 18.4%.
- **The replacement works on the annual-mean scale.** It switches each variable group alone to its actual values and adds a "joint" part and a "misfit" part. These add up exactly (median gap 0.11 points).
- The failed version stays in the outputs and the report, labelled.

*If asked "you changed the method after seeing results?":* yes, and it is logged as such. The diagnostic selects nothing (the registered rule chose the family). The check was written in advance to catch a split that does not explain the quantity, and it did its job.

**What it shows: mostly not weather but misfit.**
- **The finding.** In 8 of 13 flagged cases, including Kolkata PM2.5 and PM10 and Kanpur, the largest part of the GAM–LightGBM difference is the GAM's *misfit*: the part of the measured change the model reproduces with neither its trend nor its weather terms.
- **Kolkata PM2.5 in numbers:**
  - the GAM's fitted annual mean is 8% below the observed in 2018 and 3% above it in 2025, so 11.4 points of the fall go unexplained;
  - deweathering throws that part away, so raw − deweathered calls it "weather";
  - LightGBM's fitted means match the observed ones, so its trend keeps the fall.
- **Why the families differ.** This is the cost of the stiff one-year-knot trend (DEC-116), which cannot bend to a change in how often the worst days occur. LightGBM (in-sample R² 0.99) can, but it may also absorb weather into its trend. Neither is simply right.
- **Among actual weather variables**, humidity carries the largest GAM part in several cities (Kolkata −5.6, Mandideep −8.2). Boundary layer is the largest single part only in Pithampur.

**Is the actual weather consistent with the models? Often not, variable by variable.**
- **Kolkata's 2025 annual means (ERA5):** boundary layer lower by 2.6 SD of its 2015–2025 annual means, humidity higher by 3.6 SD.
- **The physics:** a lower boundary layer should *raise* PM. Yet both families credit the boundary layer with cleaner air in Kolkata PM2.5.
- **The tally** (report §5c) shows this "opposite sign" for the boundary layer in most flagged cities, in both families.
- **Reading:** the per-variable split describes the models; it does not establish which weather changed the air. An annual mean is a poor summary of the few stagnant days that matter, and switching one variable at a time creates weather that never occurs together.
- **Pithampur is not an ERA5 fault.** 2018 was an unusually dry, well-mixed year there (RH 54%, boundary layer 791 m), and later years are more humid.

**What this means for H4.**
- Across all H4 cities, the GAM's misfit averages −1.2 pp for PM2.5 and −0.4 for PM10 (LightGBM −0.5 and −0.2). So H4's "weather" part is mostly weather on average.
- In single cities, up to 11 points of "weather" are really "change the model cannot reproduce".
- This is why every H4 number is shown under both families. The report says it where it matters.

## Things that went wrong and were fixed

- **Figure 1's first render:**
  - value labels collided with the step connectors;
  - the policy placeholder spanned the full height, so it read like a magnitude;
  - the weather label showed +3.7 where the part's contribution to the change is −3.7;
  - three city rows were clipped at the axis limits.
  All were caught by looking at the render, not by the tests.
- **The pre-set family diagnostic (DEC-130)** failed its own additivity check. It was replaced by the annual-mean attribution (DEC-133), and the failure is reported, not hidden (Finding 5).
- **mgcv's discrete `bam`** returns no intercept with `predict(type = "terms")`. The intercept is now recovered from the saved fitted values, and the code checks that the terms add up to them (to 1e-6). The code also checks that the saved LightGBM model reproduces its fitted values.
- **DECISIONS is append-only.** Twice an anchor for an edit landed inside a committed entry. Both times the edit was reverted at once and `git diff` confirmed the committed entries unchanged.
- **A shell heredoc** broke on quoting when appending to DECISIONS. The file was checked to be unchanged before the text was re-added with the editor.
- **Adding the `composition:` config block** made upstream outputs look stale. They were marked current, as in DEC-108 (DEC-134).

## What was checked

- **13 synthetic tests** in `tests/test_composition.py`:
  - strict vs loose panel;
  - the decomposition adds up in both orders;
  - H4's sign on a city where a clean entrant flatters the reported fall;
  - cities without a panel dropped;
  - every exclusion (rule, completeness, reliability, post-hoc Satna);
  - the station bootstrap has zero spread with one station per stratum, and spread with several;
  - the cluster bootstrap;
  - the entrant log ratio and paired difference;
  - version labels unique;
  - "supported" only when the CI is above 0;
  - the model-part → variable-group mapping.
- **Hand checks:**
  - Kolkata's panel change (−18.4%) equals the Phase 5 city-disagreement table;
  - the 11 station-years too short to deweather touch no H4 city (the report shows 0 affected);
  - the diagnostic's annual-mean parts add up to each family's implied weather change (median gap 0.11 points; report §5a);
  - Kolkata's and Kanpur's identical GAM misfit (−11.4) was recomputed from the saved fits, year by year: a coincidence, not a bug.
- **Full suite:** 172 passed.
- **Snakemake:** `composition_tables`, `fig1` and `composition_report` ran through Snakemake, and the report came out byte-identical to the hand-built one. `snakemake -n pregate` then had nothing to do.
- **Figure 1** was looked at after each render.

## Open items for Reenu

1. Approval of Phase 6.
2. **The H4 sign reading (DEC-127).** It is committed and applied, but it is a clarification of registered text, so you may want to note it on OSF.
3. **The family-diagnostic method change (DEC-133).** Its main message for Phase 7: a stiff GAM trend drops station-level change it cannot follow, and raw − deweathered then calls that change "weather". Layer B's deweathered ITS inherits this, so LightGBM stays beside the GAM there too.
4. **Completeness 90%:** no NCAP city has a 2018 panel under it, so that sensitivity cannot be computed for H4. It is stated in the report, not hidden.
5. **FY2025-26 (Jan–Mar 2026) sensitivity:** not computable, because the deweathered series end in 2025.
6. **Single-station panels dominate.** Phase 7's Layer B (ground ITS/DiD) inherits this. Phase 7 is where to decide whether to report Layer B per city at all, or only pooled.

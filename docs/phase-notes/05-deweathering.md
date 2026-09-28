# Phase 5: Deweathering (RQ2)

**What this phase produced:**
- Weather-normalised ("deweathered") daily PM2.5 and PM10 for 1,054 station-pollutant series (530 PM2.5, 524 PM10). They come from two competing model families plus one sensitivity family, under two resampling schemes and two data-validity rules.
- Aggregates at station-month, station-year, city-month and city-year.
- A new data-quality rule for stuck analysers, an extrapolation guard, and figure 3 in three views (monthly under each scheme, and annual).
- Two generated reports: [`deweathering_pilot.md`](../deweathering_pilot.md) and [`deweathering_report.md`](../deweathering_report.md).

Every number below comes from those reports, from [`near_constant_check.md`](../near_constant_check.md), or from DECISIONS (DEC-100 to DEC-122).

No NCAP comparison was made. The models are fitted per station and never see NCAP status.

## The idea in one paragraph

A city's PM changes from one year to the next for two broad reasons: what is emitted, and the weather that disperses it (wind, mixing height, rain, humidity). To see the first, remove the second.
- For each station, a model learns daily log PM from that day's weather, the calendar, and a slowly moving trend that stands for emissions.
- Then, for every day, it predicts PM again 500 times, each time with the weather of a randomly drawn other day, and averages. The result is "what that day would have been under typical weather".

That is Grange & Carslaw's (2019) method. Only the weather is swapped; the trend stays, so emission changes stay in.

## How it was checked before trusting it

**Blocked, forward-chaining cross-validation (the registered test).** Train on the years before year Y, predict Y, which the model has never seen. Random splits would be dishonest: pollution episodes last days (errors are correlated at about 0.7 one day apart), so a random test day would have its neighbours in training.

**A within-period test (Reenu's diagnostic).** Hold out months, with a one-week buffer, and predict them with their own trend. The forward test also asks the model to guess next year's *level*, which deweathering never needs; this one does not, so it isolates the weather response. It scores about 0.6 for every family.

**The pilot first.** Twenty stations in twenty cities across all four regions were run with every option before committing about 10 hours of computing. It settled:
1. **The number of resamples:** 500. A pre-stated rule gave 300, but only narrowly.
2. **A flaw in my first CV rule**, fixed and openly logged. Freezing the trend at the last training day carried that day's season into the whole test year. The fix uses the trend of the same day one year earlier.
3. **A stuck-instrument problem** (Finding 1).
4. **The resampling scheme** (Finding 4).

## Finding 1: stuck analysers the audit missed

The Phase 3 flatline rule catches instruments that report *identical* values for 4+ hours. It misses the slower failure: values that change slightly every hour but hardly move from day to day for weeks. The pilot found one such station, Bagalkot.

**The new rule** (a dated deviation from the registered plan, made before any policy estimate):
- A day is suspect if the station's 15-day variability is (a) below a threshold and (b) far below its neighbours' on the same days. Part (b) means a calm spell the whole airshed shares is not flagged.
- A station-year is flagged with 30 or more suspect days.
- **Calibration:** the thresholds are set so that clearly working stations trip each part on at most 0.1% of days. A first national threshold over-flagged calm southern and coastal air, so it is set per region.

**Result:**
- It flags 77 of 4,129 valid station-years (1.9%) at 33 stations; 67 of them are in deweathered series to 2025.
- The primary analysis drops them, from the model fit too. A sensitivity analysis keeps them, using a refit, so the registered plan's version also exists.

## Finding 2: the GAM's trend was absorbing weather, and the refit fixed it

The first GAM gave its trend 4 basis functions per year. That let the trend follow within-year movement:
- under whole-year resampling, its deweathered series kept 22–23% of the raw within-year variation, where it should keep almost none;
- in the worst case it produced a physically absurd value (3.8 × 10¹² µg/m³ on a day measured at 41).

Reenu's point: a trend that can follow seasons can also follow a stagnant winter or a wet monsoon in one particular year. That weather would then be credited to "emissions", understating the weather effect.

**The rule, written down and pushed before any refit (DEC-116):**
- The trend is a spline with knots **exactly one year apart**, so it cannot bend fast enough to follow anything shorter than about a year.
- Records under two years get a straight-line trend.
- It applies identically to every station.
- The old GAM is kept as a sensitivity family (`gam_k4`).

**What the refit showed:**
- **Trend absorption** fell to 7–8% (LightGBM: 9–10%).
- **The absurd values disappeared:** 0 station-years beyond 1.5× raw under either scheme, against 68 before under whole-year resampling.
- **Out-of-sample R² rose**, 0.460 → 0.476: the stiffer trend predicts unseen years better.
- **The weather effect roughly doubled in size** (Finding 3). That is the evidence that the old trend had been absorbing weather.
- **Known cost, stated in advance:** a short emission shock like the 2020 lockdown (a few months) can no longer be followed by the trend, so the deweathered series partly averages it out. 2020 stays flagged everywhere and is handled separately in the causal analysis.

## Finding 3: how much weather moves annual numbers (RQ2)

**City level:**
- Year-on-year changes in a city's annual PM2.5 have a median size of 10.3%.
- **The weather part of that change has a median of 5.1%, and 12.6% at the 90th percentile.** PM10 is the same (5.1%, 12.9%).
- Both resampling schemes agree (5.2% under whole-year resampling).

**Network level:** weather made the network-wide annual mean several percent higher or lower than typical. Examples: 2015 about −7% for PM2.5 (favourable weather), 2016 about +3%, 2025 about −3% (report §4).

**What this means:** weather is roughly half of a typical single-year change in a city's PM2.5. So a one-year improvement of 5–10% says little about policy until weather is removed. A sustained multi-year decline is a different matter, because weather's year-to-year push and pull largely cancels over several years. This is the core of RQ2 and H4 (Phase 6).

*If asked "why did the number change from 3% to 5%?":* the first model let its emissions trend soak up some weather. Once the trend was forced to be slow, that weather had to be explained by the weather terms, and the measured weather effect grew. A rule fixed before the refit decided the direction; the outcome was not chosen.

## Finding 4: the primary model family, and how firm that choice is

The registered rule picks the family with the higher median out-of-sample R², between LightGBM and the refitted GAM. **It is the GAM: 0.476 vs 0.433, better in 756 of 946 series.** It wins under both CV conventions (the other convention gives 0.469 vs 0.450). Before the refit the convention mattered: the old GAM would have lost under the other one. That fragility is gone.

**The families now disagree more often** about how a station's level moves from year to year: D > 5% in 355 of 822 series, against 72 before. LightGBM's trend can still follow short-lived movements; the GAM's can no longer. The LightGBM results are the "other family" sensitivity in Phases 6–7, and they should be shown beside the primary, not summarised away.

## Two checks before approval (Reenu, DEC-119 to DEC-122)

**Does the lockdown smear into neighbouring years?** A trend that cannot follow a two-month dip might pull 2019 and 2021 down with it.
- **The rule, fixed before any fitting:** refit the 20 pilot stations with an indicator for India's national lockdown (25 March to 31 May 2020) and compare their 2019 and 2021 deweathered annual means with the current model. If the median change exceeds 1%, add the indicator for every station.
- **Result: 0.55%, so the model stays as it is.**
- The small smear that exists falls backward on 2019 (0.95% on its own, just under the line). It is reported so Phase 7 can weigh it, since 2019 is the first NCAP year.

*If asked "why not add the indicator anyway?":* the decision rule was fixed before the result was known. Changing the model because the number came close would defeat the point of fixing it.

**Do the two model families agree at the level H4 uses?** The earlier disagreement measure (D) is about one station's year-to-year movement. H4 asks about a city's change from 2018 to 2025, so that was checked directly, on a balanced station panel:
- The families usually agree within 2–3 percentage points.
- They differ by more than 5 points in about a quarter of the cities (5 of 19–23 per pollutant), and by up to 14.
- **Kolkata is the clearest case:** its measured PM2.5 fell 18%. The GAM says almost all of that was weather (deweathered −2%); LightGBM says little of it was (−15%).
- Most cities' panels hold a single station, so these are often one monitor's story.
- **Consequence:** H4 must be reported under both families, never one.

**Satna** (Bandhavgar Colony) keeps no special treatment. It drops out of every primary-rule panel because its near-constant years are excluded, and the registered reliability sensitivity (drop scores below 50) would not remove any of its valid years. Whether that sensitivity should reach it is Reenu's decision.

## Two resampling schemes, and why the default is not primary

Grange & Carslaw's default draws weather (and the day of year) from any time of year. Reenu made the primary scheme draw only from within ±15 days of the same date, because the default pairs a date with weather that never happens then, such as monsoon rain in December. This is a dated deviation from the registered plan.

The default was run on everything as a sensitivity analysis. The extrapolation guard shows the concern concretely:
- only 0.9% of resampled draws use weather values outside what a station was trained on;
- but under the default, 91.5% of draws pair a day with another season (none do under the primary scheme).

With the old flexible trend, those out-of-season pairings produced the absurd values. With the refitted trend, both schemes give sensible, similar results.

## Things that went wrong and were fixed

- **The trend-freezing CV rule** (pilot).
- **A single national threshold** for stuck analysers.
- **The flexible GAM trend** (Finding 2).
- **Code slips:** a test with day indices off by one; a report column starting with "p" formatted as a number; figure 3 crashing on buffered towns with no GHSL centre.
- **Stale Snakemake timestamps** after config edits. The changed keys are read only by Phase 5, so upstream outputs were marked current rather than rebuilt (DEC-108).
- **Wrong prose caught by the pipeline:** I had written "mostly monsoon" and "thousands of µg/m³" about the extreme values. The generated numbers showed 46% in June–September and a maximum of 3.8 × 10¹², and the text now says that. Likewise, "deweathering does not remove the lockdown" stopped being true after the refit and was corrected.

## What was checked

- **25 unit tests on synthetic data** in `tests/test_normalise.py`, among them:
  - Indian-day ERA5 aggregation;
  - folds and buffers;
  - resampling windows;
  - averaging and smearing;
  - gap-aware autocorrelation;
  - resumability;
  - the near-constant rule;
  - the variant day sets;
  - the city rule;
  - divergence;
  - primary vs registered stacking;
  - the extrapolation guard and its ratio flags;
  - the city-level panel and disagreement.
- The full suite passes.
- The CV-only reruns reproduce each family's main-fit predictions exactly.
- `snakemake -n pregate` has nothing left to do.
- All three figure-3 views were looked at after rendering.

## Open items for Reenu

1. Approval of Phase 5.
2. **Satna, Bandhavgar Colony (site_1433):** no override (Reenu). The registered reliability < 50 sensitivity removes none of its valid station-years (its valid years score 55–94). Making that check cover it would need a different threshold or an extra named-station sensitivity. That is Reenu's choice; it is named wherever it appears in Phase 6.
3. **H4** (raw vs deweathered, composition-corrected change) moves to Phase 6. It will be reported under both schemes, both validity rules, and both competing families; the city-level disagreement (above) makes the family comparison essential.

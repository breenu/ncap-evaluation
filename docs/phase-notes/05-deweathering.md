# Phase 5: Deweathering (RQ2)

**What this phase produced:** weather-normalised ("deweathered") daily PM2.5 and PM10 for 1,054 station-pollutant series (530 PM2.5, 524 PM10), from two model families, under two resampling schemes and two data-validity rules. These are aggregated to station-month, station-year, city-month and city-year. It also produced a new data-quality rule for stuck analysers, figure 3 in two versions, and two generated reports: [`deweathering_pilot.md`](../deweathering_pilot.md) and [`deweathering_report.md`](../deweathering_report.md). Every number below comes from those reports or from [`near_constant_check.md`](../near_constant_check.md).

No NCAP comparison was made. The models are fitted per station and never see NCAP status.

## The idea in one paragraph

A city's PM changes from one year to the next for two broad reasons: what is emitted, and the weather that disperses it (wind, mixing height, rain, humidity). To see the first, remove the second. For each station, a model learns daily log PM from that day's weather, the calendar and a slowly moving trend. Then, for every day, the model predicts PM again 500 times, each time with the weather of a randomly chosen other day, and averages. The result is "what that day would have been under typical weather". That is Grange & Carslaw's (2019) method. Only the weather inputs are swapped; the trend stays, so emission changes stay in.

## How it was checked before trusting it

**Blocked, forward-chaining cross-validation.** To test a model, train it on the years before year Y and predict Y, which it has never seen. Random splits would be dishonest: pollution episodes last days (residuals are correlated at about 0.7 one day apart), so a random test day would have its neighbours in training.
- Median out-of-sample R² on the log scale: GAM 0.460, LightGBM 0.432.
- A second, within-period test holds out months (with a one-week buffer) and predicts them with their own trend. It gives 0.63–0.64 for both. It is higher because the first test also asks the model to guess next year's *level*, which deweathering never needs. So the models capture the weather response better than the registered test suggests.

**The pilot first.** Twenty stations in twenty cities across all four regions were run with every option before committing about 10 hours of computing. It fixed four things:
1. **How many resamples.** A rule stated in advance said 300 draws were enough, but only narrowly (95.02% of station-months against a 95% bar). Reenu chose 500: at 500, every station-year is within 0.5% of its 1,000-draw value.
2. **A flaw in my CV rule.** I first froze the trend at the last training day to predict the next year. With few training years, the trend absorbs some of the seasonal cycle, so freezing it on a late-December (winter peak) day predicted a whole year about 9 times too high at one station. I changed it to "the trend of the same day last year", logged openly as a change made after seeing output.
3. **A stuck-instrument problem.** One station's PM barely moved for four years (next section).
4. **The resampling scheme.** See "Two schemes".

## Finding 1: stuck analysers the audit missed

The Phase 3 flatline rule catches instruments that report *identical* values for 4+ hours. It misses the slower failure: values that change slightly every hour but hardly move from day to day for weeks. The pilot found one such station, Bagalkot: its day-to-day variability was about 1–5%, against about 30% at a normal station.

**The new rule** (a dated deviation from the registered plan, made before any policy estimate):
- A day is suspect if the station's 15-day variability is (a) below a threshold, and (b) far below its neighbours' on the same days. Part (b) means a calm spell the whole airshed shares is not flagged.
- A station-year is flagged with 30 or more suspect days.
- **Calibration:** the thresholds are set so that clearly working stations trip each part on at most 0.1% of days.
- **A correction on the way:** a first, single national threshold over-flagged calm southern and coastal air and under-flagged the IGP. It is now set per region.

**Result:**
- It flags 77 of 4,129 valid station-years (1.9%) at 33 stations.
- False alarms on clearly working stations: 0.05% of days.
- The primary analysis drops the flagged years (from the model fit too). A sensitivity analysis keeps them, using a refit, so the registered plan's version is also available.

*If asked "why not just trust CPCB's validation?":* the mirror is CPCB's validated archive, and these series passed it. A stuck analyser is an instrument fault, not a pollution value, and its annual mean would look like perfectly stable air.

## Finding 2: the primary model family, and how firm that choice is

The registered rule picks the family with the higher median out-of-sample R². That is the **GAM** (0.460 vs 0.432; better in 713 of 946 series), and LightGBM becomes the sensitivity analysis.

**The honest caveat:** under the first CV convention (freezing the trend), LightGBM would have won (0.450 vs 0.390). So the choice depends on a convention I changed after seeing pilot output. Three things keep this from being a problem:
- the convention was changed for a documented reason (it mixed season into level) before the full results existed, and Reenu approved it;
- the other family is carried through every later result as a sensitivity analysis;
- the two families mostly agree: their deweathered annual series differ by a median of 2–3%, and by more than 5% in 72 of 822 series.

*If asked "did you pick the convention that favoured your model?":* the change was made when only the GAM's pilot results existed, and in the pilot both conventions ranked the GAM first. The full run is where the conventions disagree, and the report says so on the page that announces the choice.

## Finding 3: how much weather moves annual numbers (RQ2)

- **City level:** year-on-year changes in a city's annual PM2.5 have a median size of 10.3%. The weather part of that change has a median of 3.0%, and 8.1% at the 90th percentile (seasonal scheme).
- **Network level:** weather made the network-wide annual mean a few percent higher or lower than typical. For example, 2015 was about −4.5% for PM2.5 (a favourable year) and 2016 about +2.3% (an unfavourable one) (report §4).
- **What this means:** weather is a real but modest part of a single year's change, and it is larger in some cities and years. A city claiming a 5% improvement in one year could owe all of it to weather; a 30% improvement over several years could not.
- **2020:** its fall is mostly the lockdown. Deweathering does not remove it (it is an emissions change), so 2020 is flagged everywhere.

## Two resampling schemes, and why the default was not primary

Grange & Carslaw's default draws weather (and the day of year) from any time of year. Reenu made the primary scheme draw only from within ±15 days of the same date, because the default pairs a date with weather that never happens then, such as monsoon rain in December. This is a dated deviation from the registered plan. The default was still run on everything as a sensitivity analysis.

The full run showed the concern was real. **Under the default scheme, the GAM produced absurd values at some stations**, up to trillions of µg/m³ on a day measured at 41, and more than 2× the measured annual mean in 52 station-years.

The likely cause: the GAM's trend term absorbs part of the seasonal cycle, and the default pairs that with another season's weather, far outside anything the model was fitted on. The GAM's smooth curves then extrapolate, and averaging exponentials lets a few extreme draws dominate. LightGBM's trees cannot extrapolate, so it stays sensible (at most 1.3× at annual level).

Under the primary seasonal scheme, both families are clean (at most 1.2×). **Open for Reenu:** take the default-scheme sensitivity from LightGBM, refit the GAM with a stiffer trend, or both.

## Things that went wrong and were fixed

- **The trend-freezing CV rule** (above).
- **A test with the wrong expected answer:** a buffer test had day indices off by one; the code was right.
- **A report bug:** a report column starting with "p" (pollutant) was formatted as a number.
- **Figure 3 unit names:** these crashed for buffered towns, which have no GHSL centre.
- **Stale Snakemake timestamps:** editing the config made every upstream step look stale. The changed keys are read only by Phase 5, so the upstream outputs were marked current with `--touch` rather than rebuilt (DEC-108).
- **Wrong claims caught by the pipeline:** I had written "the extreme values are mostly in the monsoon" and "thousands of µg/m³". Generating the numbers showed 46% in June–September and a maximum of 3.8 × 10¹², so the text now says that. This is why prose numbers are generated.

## What was checked

- 21 new unit tests on synthetic data, covering:
  - Indian-day ERA5 aggregation, humidity and wind direction;
  - fold construction (no training on the future; the month buffers);
  - resampling windows and reproducibility;
  - the averaging of draws, smearing, R² and gap-aware autocorrelation;
  - atomic writes and resumability;
  - the near-constant rule, variant day sets, the inside-polygon city rule, the divergence definition and the primary/registered stacking.
- The full suite has 156 tests, all passing.
- The CV-only reruns reproduce the main fits' predictions exactly.
- `snakemake -n pregate` has nothing left to do.
- Both figures were looked at after rendering.

## Open items for Reenu

1. **The Grange & Carslaw sensitivity:** from LightGBM, from a stiffer-trend GAM refit, or both (DEC-115).
2. **Trend flexibility.** The GAM's trend absorbs about 22% of within-year variation (LightGBM about 10%), so some year-specific weather may survive deweathering. A stiffer trend (1–2 basis functions per year) is a model change that needs your decision.
3. **Figure 3.** Under the primary scheme, raw and deweathered monthly lines nearly overlap, because the scheme keeps the seasonal cycle and the weather part of a month is small. An annual view would show "how much weather moves annual numbers" more directly; that could be the Phase 9 version.
4. **H4** (raw vs deweathered, composition-corrected change) needs the balanced panel. It moves to Phase 6, under both schemes and both validity rules.

# Phase 3: Storage, cleaning, station audit, EDA (RQ1)

**What this phase produced:** a cleaned, flagged station-hour and station-day panel for 565 CPCB stations (2015 to March 2026); satellite PM2.5 for all 1,923 Indian urban centres (plus 10 buffered towns); a reliability score for every station-year; the Phase 3 figures, including the station-entry map and the data-quality heatmap; a generated audit report (`docs/audit_report.md`); and a draft analysis plan (`docs/analysis_plan.md`). Every number in the audit report is produced by the pipeline.

Blinding held throughout: nothing compares NCAP with non-NCAP cities after 2018.

## Finding 1: the "11-hour" clock error was ours; the real offset is 5.5 hours

Phase 2 concluded the mirror's timestamps were 11 hours ahead of UTC and could not explain the "second 5.5 hours". The explanation turned out to be simple and embarrassing. The database tool (DuckDB) *displays* timestamps in the computer's own time zone, which on this laptop is India's. Every test had looked at times already shifted 5.5 hours for display.

Read in UTC, the stored times are just Indian clock times labelled as UTC, which is exactly what the mirror's code implies. The correction is **−5.5 h**.

- **Nothing Phase 2 reported changed:** its counts were computed consistently within the display zone, and the re-run gives the same station-years.
- **Why it still mattered:** the "11 h" rule would have been 5.5 hours wrong on any other computer, including the Linux CI server.
- **Independent confirmation:** on the corrected clock, stations' solar-radiation peaks land within about 15 minutes of local solar noon in every year (DEC-054, DEC-077).
- **Guard:** every reader now forces UTC, and a test checks three time zones.

*If asked "how did you find it?":* the cross-check in this phase gave 2% agreement in 2025, where Phase 2 had shown 100%. The contradiction pointed at the reader, not the data.

## Finding 2: why only "2%" of old values matched, and why the mirror can be trusted anyway

Phase 2 saw only about 2% of pre-2023 values match OpenAQ exactly. Across **all 1,608 overlapping station-years**, the picture is different:

- **2019–2021 values are identical** (median 100%).
- **The 2% came from Phase 2's sample.** It took the first 11 stations by id, and 7 of them are run by IMD.
- **IMD stations** differ at 15 minutes, but their daily means agree within about 0.4% with no bias.
- **March 2018 is an OpenAQ fault.** That month OpenAQ stored something that behaves like a 24-hour air-quality index, not a concentration.
- **OpenAQ's 2025 "ppb" NO2 is really µg/m³.** The values are identical to the mirror's.

The deeper discovery: **the mirror holds CPCB's validated data, OpenAQ the raw real-time feed.**
- OpenAQ carries 2–3% zero or negative values (including −9999 codes), and at more than 95% of those moments the mirror has no value.
- OpenAQ has PM2.5 > PM10 30–40 times as often (since 2020).
- So January–March 2026, which only OpenAQ has, is **provisional**. The analysis plan uses it only as a sensitivity check (DEC-079).

## Finding 3: where the stations are

- **Station identity is settled by data, not names.** Two copies of the same instrument's data share identical values at identical moments; different stations almost never do (≤ 10%).
- **Result:** 513 stations have a data-confirmed coordinate and 3 more a unique locality point. 5 are left for Reenu because their candidate coordinates sit in different urban centres. 24 have no coordinate anywhere and keep an approximate city point, kept out of neighbour checks.
- **Along the way:**
  - some OpenAQ ids swapped two stations' data for a while (R K Puram and Punjabi Bagh);
  - one coordinate was 313 km out;
  - the mirror labels three Maharashtra stations as Bihar.

## Finding 4: what is wrong in the data (the audit, RQ1)

- **Impossible values and ceilings.** No zeros or negatives in the validated mirror. Instrument ceilings are pinned values that repeat far more than their neighbours, at many stations: 985, 999.99 and 1000 µg/m³ (and 842, 887, 995 for PM2.5). About 0.09% of 15-minute values were removed.
- **Flatlines.** Identical hourly means for 4+ hours. Why 4: runs of 2–3 hours happen by chance given instruments that report whole numbers; from 4 hours they happen about three times more often than chance allows. About 0.3–0.9% of hours are flatlined after 2017, and 1.4–2.9% in 2015–16. A few stations are chronic: the worst 10 hold 30% of all flatlined hours.
- **PM2.5 > PM10.** Physically impossible beyond measurement noise. It is rare after 2019 (under 0.2% of hours) but 0.7–1.0% in 2015–2018: CPCB's own validation was looser then.
- **Level shifts.** A station whose level jumps relative to its neighbours has probably been recalibrated, replaced or moved.
  - The first attempt found about 11 per station, which is absurd. The detector underestimated noise in slowly drifting series.
  - Its sensitivity is now calibrated so that at most 5% of series with the shifts scrambled out show a false one.
  - Result: 653 shifts at 317 stations. The audit cannot tell a recalibration from a real local change, such as a new road beside the monitor, and says so.
- **Spatial checks.** Most stations track their neighbours closely (median correlation 0.91). About 160 station-years per pollutant do not. 52 PM2.5 station-years sit far from the satellite.
- **Reliability score** (0–100): completeness × share of unflagged data × a penalty per failed check. The median station-year scores about 80 after 2018, but about 37 in 2017 and 57 in 2015–16 (Figure 8).

## Finding 5: gaps do not hide the dirty days, the opposite of the worry

The proposal worried that monitors fail most in polluted winters, which would bias annual means *down*. The data say the opposite:
- a station-day is about **6 percentage points less likely to be missing in winter** than in the monsoon;
- it is **4–5 points less likely to be missing on the dirtiest third of days**, measured by the neighbours' level that day, net of season.

So the naive annual mean is slightly *too high*, not too low: a median +0.7% for PM2.5, filling missing days from the neighbours.

*If asked "how can you know how polluted a missing day was?":* from the neighbours, which report on the days the station is silent.

## Finding 6: the network grew and changed

- **Growth:** 30 stations had data in 2015; 127 new stations started in 2023 alone (Figure 2).
- **Ground–satellite agreement fell as the network grew.** It rose to r = 0.91 in 2021, then dropped to 0.79 by 2024 as many new stations were added, which is worth understanding in Phase 6.
- **New stations vs existing ones:** new stations are a little cleaner than the existing stations in the same city and year (PM2.5 −5.8%, 95% CI −11.5% to +0.2%). That is the first hint of the composition effect RQ1 is about, and not yet conclusive.

## The satellite layer and the oversized-polygon rule

GHSL draws some "urban centres" enormous: the one containing Muzaffarpur is 3,166 km² and includes Hajipur and dense countryside. This is not only an NCAP problem; rural-dense centres in Bihar, Kerala and West Bengal are in the control pool too.

**Rule (proposed, DEC-070):** a city's satellite value is the **population-weighted** mean over its polygon, for every unit alike. Why:
- it is what residents breathe;
- it needs no arbitrary clipping radius;
- it treats treated and control units identically.

The unweighted mean is the sensitivity check. The choice changes a typical unit by 0.2%, and oversized ones by a median 1.7%.

**Towns and joined units** (Reenu's rulings):
- The 10 NCAP towns with no GHSL centre are kept out of the primary analysis and enter a sensitivity analysis as 1.87 km circles, sized like the smallest GHSL centres (DEC-063).
- Raniganj's town point lies inside a GHSL centre (named "Mejia"), so that polygon was joined to Asansol (DEC-064).

## Problems met along the way

- **The clock rendering (Finding 1).**
- **A ceiling detector that flagged hundreds of ordinary values.** Whole-number readings are simply more common than 2-decimal ones. Fixed by comparing like with like, and requiring a pin to appear at many stations.
- **A changepoint detector that found too much.** Fixed by calibrating against a null.
- **UCDB lists a village "Durgapur" 130 km from Durgapur city.** Main names now beat list names.

## What was checked

- 112 unit tests on synthetic data, covering every flag rule, the clock, identity matching, town lookups, regions, changepoints and the reliability score.
- Every figure was looked at after rendering; label collisions and misleading uncertainty bands were fixed.

## Open items for Reenu

1. **5 stations** whose candidate coordinates lie in different urban centres (`docs/station_metadata_review.md` §3).
2. **Confirm DEC-064:** Raniganj joined as its GHSL polygon rather than a buffer.
3. **Confirm DEC-070:** the oversized-polygon rule.
4. **Review `docs/analysis_plan.md`.**

## Update after review (2026-09-26)

Reenu accepted the recommended coordinates for the 5 reviewed stations (DEC-080), and the whole Phase 3 pipeline was then rebuilt end to end with `snakemake --cores 1 pregate` (DEC-082, DEC-083). With 3 more stations located:

- Level shifts: 653 at **316** stations (was 317). The calibrated penalties are unchanged (8 and 5).
- Station-years flagged against the satellite: **49** PM2.5 station-years (was 52).
- Coordinates: 516 stations have a station-level coordinate from OpenAQ (3 of them by Reenu's decision), plus 3 GeoNames localities; 26 keep an approximate city point or none.
- Everything else quoted above is unchanged, including the valid station-years, the missingness findings, the new-vs-existing station comparison and the ground–satellite correlations. The generated `docs/audit_report.md` carries the current numbers.

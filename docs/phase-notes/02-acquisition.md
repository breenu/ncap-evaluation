# Phase 2: Acquisition

**What this phase produced:** every raw input the project needs, downloaded by scripts that can be re-run safely, each file recorded with where it came from and a fingerprint. It also produced three findings that change how the data must be used: the ground source had to be replaced, its clock is wrong by 11 hours, and the NCAP city and funding numbers now reconcile across documents.

## What was downloaded, and from where

| Source | What | Where it lives |
|---|---|---|
| CPCB station data (via a mirror) | 15-minute PM2.5/PM10, ~565 stations, 2015–2025 | `data/raw/cpcb_mirror/` |
| OpenAQ | same stations' data from an independent pipeline; the only source for Jan–Mar 2026; station coordinates | `data/raw/openaq/` |
| ACAG satellite PM2.5 | three product versions, 2005–2024, 0.01° | `data/raw/acag/` |
| ERA5 weather | hourly series at 283 station grid points; monthly means for India | `data/raw/era5_*` |
| GHSL | urban-centre boundaries and population | `data/raw/ghsl/` |
| DataMeet | state and country boundaries | `data/raw/boundaries/` |
| NCAP documents | 14 PDFs: city lists, Finance Commission allocations, Parliament answers | `data/raw/ncap_docs/` |
| FIRMS fires | written, not yet downloaded (network) | `data/raw/firms/` |

Each source has a data card in `docs/data-cards/`.

## Finding 1: the planned ground source was not usable, so it was replaced

Step 0 showed that OpenAQ, the planned source, has almost no government station data for 2023 and 2024, two of NCAP's post-treatment years. CPCB's own download service had disappeared (HTTP 404). A public mirror, `Vonter/india-cpcb-aqi`, holds CPCB's 15-minute data for 2015–2025, collected before the service went away. Reenu approved it as the main source, with OpenAQ as an independent cross-check.

A mirror is one step removed from the government, so it is checked rather than trusted:
- each file must match the checksum GitHub publishes;
- the scripts that built it are saved;
- its values are compared with OpenAQ's independent copy of the same stations.

In 2025 they are identical, value for value, once the clock is corrected (Finding 2).

*If asked "why trust a GitHub repo?":* because it was tested against an independent copy of the same government data, and every file is fingerprinted. If the mirror changes, the pipeline refuses the new files instead of silently using them.

## Finding 2: the mirror's timestamps are 11 hours ahead of UTC

The mirror labels its times "UTC". Its own code shows it only *stamps* CPCB's local times as UTC without converting them, so the expectation was that the times are really Indian time (UTC + 5:30). Reenu asked for this to be settled with evidence, not assumed. Three independent tests were run:

1. **Matched values.** At stations in both sources, the mirror's times were shifted by every candidate offset from −12 to +12 hours in 15-minute steps, and the share of 15-minute values that were *exactly equal* to OpenAQ's was counted. OpenAQ's timestamps carry an explicit offset. The match jumps to 100% at +11 hours and is about 0% everywhere else, including +5.5 and 0.
2. **The sun.** Many stations measure solar radiation, which peaks at local solar noon: 12:00 minus longitude/15 hours in UTC. On the mirror's clock the peak comes about 10.7 hours after that, in every year from 2015 to 2025, at up to 376 stations. This test uses no other dataset at all.
3. **Weather reanalysis.** Station solar radiation lines up best with ERA5's (which is in true UTC) at a lag of 10.5 to 11 hours, with correlation about 0.93. ERA5 is hourly, so this test can only resolve to about half an hour.

So the mirror's times are Indian time shifted forward a *second* time. Where the extra 5.5 hours came from is unknown, and it doesn't change the fix: subtract 11 hours. The raw files are left untouched. The correction lives in `config/params.yaml` and is applied when the data are read (DEC-040).

*Why it matters:* NCAP analysis uses daily and seasonal averages, and deweathering pairs each hour's pollution with that hour's weather. An 11-hour error would pair night-time pollution with daytime weather, and a winter night's inversion with an afternoon's mixing. The deweathering model would be learning from scrambled inputs.

*If asked "how do you know it isn't OpenAQ that's wrong?":* the solar test does not use OpenAQ, and it gives the same answer.

> **Correction (2026-09-26, Phase 3; DEC-054).** The "second 5.5 hours" was ours, not the mirror's. The tests read timestamps through DuckDB, whose display time zone defaults to the computer's own (IST on this laptop), so every timestamp was shown 5.5 h later than the instant stored in the file before the offset was measured. Measured against the stored instant, the offset is **5.5 h**: the mirror holds Indian clock times stamped as UTC, exactly what its `parse.py` suggests. The station-year counts above were computed consistently on this laptop and are unchanged after re-running on the corrected clock, but the "11 h" rule would have been 5.5 h wrong on any other computer. Every reader now fixes DuckDB's time zone to UTC, and a test checks that the result does not depend on the machine's zone.

## Finding 3: the NCAP city and funding numbers reconcile

The proposal took some facts from secondary sources (131 cities; 49 funded through the Finance Commission and 82 by the Ministry), while other sources said 130 and 48. Fourteen official documents were extracted with pdfplumber. Every extracted row records its document and page, and every table was checked against its own printed totals.

- **Counts.** The June 2021 CPCB list had 132 entries because Asansol and Raniganj were listed separately; from 2022 they are one entry (131). Patancheruvu, a city inside Hyderabad's urban agglomeration funded through the Finance Commission, drops out by 2026. That gives 130 cities and 48 Finance-Commission cities. Both "131 / 49" and "130 / 48" are right, at different dates.
- **When each city joined.** CPCB republished its city list several times at the same web address. Old versions survive in the Internet Archive, and each PDF records its own creation date. The first list containing a city dates its entry: 102 cities at launch (Jan 2019), 19 more by June 2020, 2 by December 2020, and 8 large "million-plus" cities by June 2021. That staggering matters for the causal design in Phase 7.
- **Checks.** All Parliament tables add up to their printed totals within 0.02 crore. The Finance Commission's city allocations match the Parliament answer's allocations for every city. The 37 remaining items (odd names, combined rows such as "Twin City Bhubaneshwar & Cuttack", and cases where more was spent than released) are listed in `docs/ncap_extraction_mismatches.md` for a manual check. None were "fixed" in code.

## How the downloads stay trustworthy

- **Resume, don't restart.** If the connection drops mid-file, the next run continues from the last byte (HTTP Range requests). A partial file is never spliced onto a different version of the file.
- **Fingerprints.** Where the source publishes a checksum (S3 and GitHub do), the download must match it; every file's SHA-256 goes into a committed manifest.
- **Small-file problem.** OpenAQ stores about 430,000 tiny daily files. They are packed, unchanged, into one zip per station-year with an index inside, so the manifest has about 2,500 rows instead of 430,000.

## Problems met along the way

- **A backtracking regular expression** took the PDF extraction from 6 seconds to over 10 minutes; it was replaced by simple token splitting.
- **Tables that change shape between pages,** numbers printed vertically in merged cells ("3 . 6 2"), and a row whose values wrapped onto the next page were each found because a column failed to sum to its printed total. That is the value of checking against printed totals.
- **An environment trap.** Oracle's database software puts its own maths library on this laptop's system path. If the pipeline runs without activating the conda environment, NumPy loads Oracle's library and crashes. The rule is now: always run inside the activated environment (DEC-046).

## Open items

- **FIRMS** is blocked by the current network. The downloader is ready; the fire covariate will use VIIRS from 2012 (DEC-039).
- **19 stations** have no coordinates; they get a GHSL urban-centre location in Phase 3.
- **Some OpenAQ ids for the same station disagree on coordinates** (up to 30 km); listed for the Phase 3 metadata audit.
- **Before 2018 the monitoring network is small** in every source (a handful of valid station-years). This limits the ground layer's pre-NCAP baseline, not the satellite layer.

## What was checked

- 77 tests pass, including new ones for resumable downloads, zip bundling, the PDF parsing rules, name matching, and a synthetic test that the offset scan recovers a known 5.5-hour shift.
- `docs/data-probe.md`, `docs/mirror-checks.md` and `docs/ncap_extraction_mismatches.md` are generated by the pipeline; no number in them was typed by hand.

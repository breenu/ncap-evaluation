# Technical report: outline (Phase 10, Part A)

*Status: draft for review, 2026-10-03. This file is the plan for `reports/report.qmd`. Once the report is written it is superseded by the report itself. The numbers quoted in the headline paragraph (§3 below) are copied from the generated reports so that I can review the wording; in the report itself each one is filled in from pipeline outputs (§4).*

**Title.** Weather, Monitors, or Policy? A Meteorologically Normalised, Quasi-Experimental Evaluation of India's National Clean Air Programme, 2015–2025.
**Author.** Reenu (sole author). **Formats.** Quarto to HTML and PDF.
**Length.** 20–30 pages: main text about 24 pages including references, appendices about 6. If the PDF runs over 30 pages, I cut methods detail first, since the phase reports in `docs/` hold the full detail and the report cites them.

## 1. How the report is organised

The order follows the paper structure the proposal asks for: introduction, data, methods, results by research question, robustness, limitations, conclusion. Every results section opens with the registered question and its verdict, then the evidence.

Five reading rules apply everywhere, and section 1.5 states them once for the reader:
1. H1 is not identified by this design, so no number in the report is an effect of NCAP. The fixed sentence ("NCAP units' satellite PM2.5 did not fall relative to comparable units; the estimates point to a relative rise of about 3–5%") always sits next to the verdict.
2. Cities are never ranked. Every named list is alphabetical.
3. Ground (Layer B) results are secondary and have one pre-NCAP year. Each carries its scope: how many cities, and how many rest on a single station.
4. Raw aerosol optical depth (AOD) is read for direction only.
5. No claim is made about any individual weather variable.

### Front matter (1 page)

- Title, author, date, version (v1.0), and links to the OSF registration, the repository and the city explorer.
- Abstract, about 200 words, built from the headline paragraph (§3).
- A short box, "What this report does and does not claim".

### 1 Introduction (2 pages)

- **1.1 NCAP and how its progress is reported.** Launched in January 2019, 131 cities at its widest (130 in the 2026 list), with PM10 targets of up to a 40% cut by 2025-26. Public trackers compare raw concentrations with a baseline.
- **1.2 Three things tangled in one reported number:** weather, which monitors exist, and policy. The network NCAP paid for is also the one used to judge it ("the treatment changed the thermometer").
- **1.3 Research questions and hypotheses.** RQ1 measurement, RQ2 weather, RQ3 policy, RQ4 heterogeneity and mechanism.
  - **Table 1:** H1–H5, with status (confirmatory or secondary), layer, the registered decision rule in one line, and the verdict. The verdict column is generated.
- **1.4 Pre-registration.**
  - The plan registered on OSF before any post-2019 comparison, and the code gate that enforced it (plan `6e24eca`, gate `0d9aa42`).
  - What I had and had not seen before registering.
  - The 1 October clarification. Every deviation is listed in Appendix A.
- **1.5 Contributions and reading rules.**
  - Contributions: a station-level audit and reliability score; network composition measured systematically; weather normalisation combined with a long satellite pre-period and a comparison group; a falsifiable mechanism test.
  - The five reading rules above.

### 2 Data (3 pages)

- **2.1 Ground monitors.**
  - CPCB's continuous stations, taken from a public mirror of CPCB's repository, because the repository itself is offline and OpenAQ lacks 2023–24.
  - How I checked the mirror: checksums, a value-by-value cross-check against OpenAQ, and a clock correction confirmed by three independent tests. January–March 2026 is provisional and is not used.
  - **Figure 2** (station entry): most of today's network did not exist at the 2018 baseline.
- **2.2 Satellite PM2.5.**
  - ACAG V5.GL.06 is primary; V6.GL.03 and V6.GL.02.04 are the algorithm and vintage checks.
  - The product is calibrated to ground monitors, which is the leakage threat tested in §4.3.
- **2.3 Units and the comparison group.**
  - GHSL R2024A urban centres; population-weighted city values.
  - 113 treated units holding 121 NCAP cities; the 10 towns without a centre; the 923-unit control pool and how it was built.
  - **Table 2:** control-pool construction and listing cohorts (generated from `pregate_checks.md` §1–2).
- **2.4 Treatment timing.**
  - First listing on an official list is the treatment date, with interval-censored dates from dated list versions.
  - First funding is a sensitivity analysis only, because XV-FC money is partly performance-linked.
  - How I extracted the NCAP documents, with every row traced to its source page.
- **2.5 Weather, fire and aerosol data.** ERA5 point series at the station cells and monthly means; FIRMS VIIRS fires; MODIS MAIAC AOD reduced on Earth Engine.
- **Table 3:** data sources, with version, coverage, access and licence.

### 3 Methods (4.5 pages)

- **3.1 Audit and validity rules (RQ1).**
  - Flag rules: detected instrument ceilings, flatlines of 4 or more hours, PM2.5 > PM10.
  - Changepoints, with the penalty calibrated against a no-shift null.
  - Neighbour and satellite consistency checks; the reliability score; completeness rules at 75%, with 60% and 90% as sensitivities.
  - The near-constant-analyser rule (deviation A2).
  - The missingness models.
- **3.2 Deweathering (RQ2).**
  - The GAM with a one-year-knot trend, and LightGBM.
  - Weather resampled within ±15 days of each date as primary (deviation A1), Grange & Carslaw's all-year scheme as sensitivity; 500 draws.
  - Blocked forward-chaining CV and the registered family rule; the extrapolation guard; the lockdown test.
- **3.3 Network composition and H4.**
  - Three trends per city: all stations, the balanced 2018 panel, and satellite.
  - The additive decomposition: reported = unmodelled change + modelled weather + composition + corrected.
  - Cluster bootstrap over cities. Scope: cities with a station valid every year from 2018 to 2025.
- **3.4 Layer A, satellite (RQ3, confirmatory).**
  - SDID per listing cohort against never-treated centres, 2020 dropped, with joint-placebo standard errors.
  - Sun & Abraham event study; Callaway & Sant'Anna; HonestDiD bounds; the 2016 placebo; the equivalence test at ±5%; the MDE.
  - The calibration-leakage split, and the raw AOD check with its pre-written reading.
- **3.5 Layer B, ground (secondary), and triangulation.**
  - ITS as a before–after contrast; ground DiD per cohort.
  - The ordered disagreement categories and the four-step investigation.
- **3.6 Heterogeneity and mechanism (RQ4).**
  - One SDID per unit, with placebo-based standard errors.
  - The measurement-error hierarchical model with the five registered moderators. H5 is its IGP coefficient.
  - H3's three conditions; the exploratory dose on allocations.
- **Table 4:** every registered decision rule, as registered and as read (C1, C2).

### 4 Results (9.5 pages)

- **4.0 The argument in one figure.**
  - **Figure 1:** (a) the PM2.5 decomposition over the 18 H4 cities; (b) the satellite relative change on its own axis, labelled "not identified as an effect of NCAP"; (c) four illustrative cities chosen by a station-count rule, drawn alphabetically.
  - One paragraph on how to read it. Each later section refers back to its panel.
- **4.1 RQ1: measurement.**
  - What the audit found:
    - ceilings and flatlines;
    - PM2.5 > PM10 rates falling after 2019, when CPCB's validation tightened;
    - level shifts, which the audit cannot tell apart from real local change;
    - missingness that is *lower* on polluted days, so naive annual means are biased slightly upward.
  - **Figure 8** (data-quality heatmap).
  - Composition bias across all cities with a 2018 panel, appearing from 2022–23.
  - New stations read cleaner, and deweathering does not remove the gap: it is about where they stand, not the weather.
  - Ground against satellite: they agree on average, not city by city.
  - **Table 5:** H4 for PM2.5 and PM10, in three versions: primary (GAM), LightGBM, and as registered with no deviations. Plus the count of versions in which it holds, with each failing version named. Every city: Figure S3 (Appendix D).
- **4.2 RQ2: weather.**
  - **Figure 3** (annual raw against deweathered for six cities chosen by coverage).
  - The weather part of a typical year-on-year change, against the size of that change.
  - The network-wide weather effect by year.
  - The family choice under the registered rule, and how much the families disagree at city level, which is why both are always shown.
- **4.3 RQ3: policy (Layer A, then Layer B).**
  - **Table 6:** H1's four rules with their values and the verdict, "not identified by this design". The fixed sentence goes next to it.
  - **Figure 4** (event study with Callaway & Sant'Anna).
  - The HonestDiD breakdown value. The equivalence result and the NCAP targets the interval excludes, reported for information.
  - Descriptive context: both groups' satellite PM2.5 fell after 2018, the comparison pool more (**Figure S1**).
  - The calibration-leakage split, and the possible mechanism I cannot test.
  - Raw AOD: Q1 "rise not reproduced", Q2 "gap absent", and the exploratory finding that ACAG and AOD diverge most where no monitor was added (**Figure S2**).
  - Layer B, ITS and DiD for PM2.5 and PM10, each with its scope line (**Table 7**).
  - Triangulation: one pair "uninformative", one "conflict". Investigation step 3 shows that ground and satellite agree on the before–after fall, so the conflict is between two different questions, not two measurements.
  - H2: not tested; the exploratory winter and non-winter numbers.
- **4.4 RQ4: heterogeneity and mechanism.**
  - City-level relative changes: none passes Benjamini–Hochberg at 5%.
  - The hierarchical model: strong shrinkage; rank intervals too wide to rank cities.
  - **Figure 5** (maps) and **Figure 6** (before and after shrinkage, unnamed rows).
  - H5: the registered rule is not met. The IGP-only model is shown beside it and does not decide.
  - H3: inconclusive (**Figure 7**).
  - The exploratory dose shows no association, and the dose is effectively "which state".
  - A pointer to the alphabetical per-city table in `docs/heterogeneity_report.md` §4 and to the city explorer. The table is not reproduced in the report.

### 5 Robustness (2 pages)

- **Table 8:** the 19 registered Layer A checks.
  - The count that "agree", with the two that do not (the older calibration vintage, and excluding the IGP).
  - Every Layer A estimate is positive.
  - Leave-one-out donor range; placebo in space.
- Layer B: the count of checks that agree per pollutant, and which do not. The 2019-baseline rows cover only the cities listed in 2020–21.
- H4 across all versions, with the two failing PM10 versions named.
- **"What weakens the results"**, an explicit list:
  - the pre-trend failure;
  - the leakage warning and the ACAG–AOD divergence;
  - single-station panels;
  - the GAM–LightGBM disagreement in individual cities;
  - the post-hoc checks (F2, F3, F6, F7), each with its label.

### 6 Limitations (1.5 pages)

- Identification: a failed pre-trend test, and selection into treatment (NCAP cities are much larger and less often in the IGP).
- The satellite product is calibrated to monitors, and raw AOD diverges from it.
- The ground network before 2018 is thin, with one pre-year and mostly single-station panels.
- PM2.5 results say nothing directly about NCAP's PM10 targets.
- NCAP is a bundle of actions, so even an identified estimate could not say which action worked.
- 2020.
- Weather at 0.25° resolution, and dependence on the model family.
- Mirror provenance.
- What is not covered: NO2 (B3), January–March 2026, and the 10 towns without a GHSL centre in the primary analysis.

### 7 Conclusion and implications for measuring NCAP progress (1 page)

- What I can say, what I cannot, and why both matter.
- Evidence-bounded recommendations, each tied to a finding:
  - report a fixed panel of stations beside the all-station average;
  - report weather-normalised values beside raw ones;
  - publish station entry dates and metadata;
  - report PM2.5 as well as PM10;
  - evaluate against a comparison group with a long pre-period, registered in advance.

### References (1 page)

Methods papers (Grange & Carslaw 2019; Arkhangelsky et al. 2021; Sun & Abraham 2021; Callaway & Sant'Anna 2021; Rambachan & Roth 2023; Abadie et al. 2010; Benjamini & Hochberg 1995; Duan 1983), plus the data citations required by each source's terms.

### Appendices (about 6 pages)

- **A. Deviations from the registered plan:** `reports/deviations.md`, included verbatim.
- **B. Reproducibility:**
  - environments and lock files; one command per stage; the code gate;
  - the clean-clone rebuild (Part D): timings, the checksum check of `data/raw`, and the comparison with the committed outputs;
  - what is not byte-identical, and why.
- **C. Data licences and attributions.**
- **D. Supplementary figures:** S3 (every H4 city, alphabetical) and S4 (the PM10 decomposition).

### Figure and table placement

| Figure | Where | Why there |
|---|---|---|
| 1 Decomposition (a, b, c) | §4.0 | It summarises RQ1–RQ3; the figure I show in interviews. |
| 2 Station entry | §2.1 | It shows the data problem before the methods. |
| 3 Raw vs deweathered (annual) | §4.2 | RQ2. |
| 4 Event study | §4.3 | H1 rule (b). |
| 5 City maps | §4.4 | RQ4. |
| 6 Shrinkage and rank intervals | §4.4 | Why cities are not ranked. |
| 7 PM10 vs PM2.5 | §4.4 | H3. |
| 8 Data-quality heatmap | §4.1 | RQ1. |
| S1 Satellite levels | §4.3 | Descriptive context for the positive estimate. |
| S2 ACAG vs AOD | §4.3 | The leakage check. |
| S3, S4 | Appendix D | Per-city detail and PM10. |
| E1–E4 (exploratory) | not in the report | Cited from `docs/figures.md`. |

Tables: 1 hypotheses and verdicts (§1.3); 2 control pool and cohorts (§2.3); 3 data sources (§2.5); 4 decision rules (§3); 5 H4 (§4.1); 6 H1 rules (§4.3); 7 Layer B and triangulation (§4.3); 8 robustness (§5); A deviations (Appendix A).

## 2. Companion documents (Part B)

- **One-page results summary** (`reports/summary.qmd`): effect sizes with intervals, verdicts and the key caveats. Same reading rules.
- **Two-page policy brief** (`reports/policy_brief.qmd`), for a non-technical reader: why raw tracker numbers mislead; what survives correction; what the comparison with other cities can and cannot say; the recommendations of §7 for measuring progress.
- **Slide version of Figure 1:** panel (a) only, plus one takeaway line generated from the same values. It goes through the same wording check.

## 3. Headline findings (one paragraph; approved 2026-10-03 with Reenu's edits, DEC-209)

The abstract uses the same wording.

> Public progress reports compare a city's raw pollution with a baseline year, and in the cities where I could check this, that comparison overstates the improvement. In the 18 NCAP cities that had a PM2.5 monitor valid every year from 2018 to 2025 (16 of them with only one such monitor), the reported fall of 23.6% becomes 14.1% once I remove modelled weather and the change in which monitors exist. Most of the difference comes from the changing set of monitors: the stations added since 2018 read cleaner than the ones already there (H4 supported: +9.5 percentage points, 95% CI +4.8 to +14.5). Weather alone moves a typical city's annual PM2.5 by about 5% from one year to the next. For the policy question, I compared the 113 urban centres containing 121 of NCAP's 131 cities with 923 comparable non-NCAP centres on satellite PM2.5. Satellite PM2.5 fell in both groups after 2018: by 16.8% in NCAP units and by 24.3% in the comparison pool. NCAP units' satellite PM2.5 did not fall relative to comparable units; the estimates point to a relative rise of about 3–5% (primary estimate +3.6%, 95% CI +2.4% to +4.8%). But the pre-trend test I registered in advance failed (p = 0.0008), so H1 is not identified by this design, and I do not attribute this or any other number to NCAP. Raw aerosol optical depth, which no ground monitor calibrates, shows a smaller relative change than the satellite PM2.5 product on the same units in every specification, for reasons this design cannot separate. The gap seen in satellite PM2.5 between units that gained a monitor and units that did not is absent from raw aerosol optical depth, which is consistent with, but does not prove, the satellite product absorbing the new monitors. City-level differences are too uncertain to rank cities. The registered tests for a smaller change in the Indo-Gangetic Plain (H5) and for dust control (H3) came out "not met" and "inconclusive".

Where each number comes from (in the report, each is a generated variable):

| Number | Source |
|---|---|
| 18 cities, 16 single-station; −23.6% → −14.1%; H4 +9.5 pp (+4.8 to +14.5) | `docs/composition_report.md` §1, §1a (primary row); `docs/figures.md` figure 1 |
| "most of the difference" = composition +5.8 of +9.5 pp; added stations read cleaner (PM2.5 −6.3% raw, −6.8% deweathered) | `composition_report.md` §1a, §4 |
| weather about 5% (median 5.1% of the year-on-year change in a city's annual PM2.5) | `docs/deweathering_report.md` §4 |
| 113 and 923 units | `docs/pregate_checks.md` §1 |
| "about 3–5%" | `src.causal.causal_report.wording()` |
| +3.6% (+2.4% to +4.8%); p = 0.0008 | `docs/causal_report.md` §1 |
| −16.8% and −24.3% (2018 → 2024) | `causal_report.md` §1c |
| AOD below ACAG in 5 of 5 specifications | `causal_report.md` §12c; `figures.md` S2 |
| H5 not met; H3 inconclusive | `docs/heterogeneity_report.md` §3, §5 |

## 4. How the numbers get into the report (proposed; DEC-206)

- **Prose with no typed numbers.** The prose is written by hand in `reports/report.qmd`, but it contains no hand-typed result.
  - Every number is a Quarto variable, `{{< var h4.pm25.h4_pp >}}`, read from `reports/_variables.yml`.
  - That file is written by `python -m src.report.values` (in the `ncap` environment, gated) from the same processed outputs the phase reports are built from.
  - Tables are generated as Markdown files under `reports/_generated/` and pulled in with `{{< include >}}`.
- **Tests (`tests/test_report.py`).**
  - No result-like number in the prose outside a variable. Years, section, figure, table and DEC numbers, and H1–H5 are allowed.
  - Every variable the prose uses exists.
  - Every DEC marked "DEVIATION" in `docs/DECISIONS.md` appears in `reports/deviations.md`.
  - The wording check (`src/viz/wording.py`) runs on the prose, the variables and the generated tables of the report, summary, brief and slide.
- **Rendering.** `quarto render reports` runs in the site environment `ncap-site` and produces HTML and PDF. The PDF is made with Typst, which ships with the locked Quarto 1.9.38, so neither lock file changes and no LaTeX install is needed.
- **Snakemake.** The `report` stub becomes two real rules: `report_values` (part of `all`) and `report_render` (which calls the site environment, like `dashboard_render`).

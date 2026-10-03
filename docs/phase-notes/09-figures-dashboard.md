# Phase 9: Figures and the read-only dashboard

**What this phase produced:**
- **The figures.** Eight main figures, four supplementary (S1–S4, including a new ACAG vs AOD comparison) and four exploratory (E1–E4). Each comes as PNG and SVG, with a caption and alt text generated from the pipeline outputs. All are listed in [`figures.md`](../figures.md).
- **A wording check.** `src/viz/wording.py` refuses to save any figure, caption, alt text or dashboard page that calls something an effect of NCAP or ranks cities.
- **A read-only city explorer:** 113 precomputed pages, published as a static Quarto site on GitHub Pages. It is built in its own small environment, so the analysis lock never changed.

**Rules first.**
- Figures: DEC-190 to DEC-195, pushed in `09209e7` before any figure changed.
- After Reenu's review, and before any dashboard code: DEC-197 to DEC-201, pushed in `406f544`.
- Results: DEC-196 (figures) and DEC-202 (dashboard).
- Nothing was estimated in this phase. Every number is read from Phases 3–8b.

## The one sentence to keep in mind

H1 is "not identified by this design" (Phase 7: the registered pre-trend test failed). So no figure, caption or page may call anything an effect of NCAP. The satellite numbers are **relative changes against comparison cities**, and every place they appear says so.

## Figure 1, the main figure, and why its last step was removed

**What it shows.**
- **(a)** For the 18 NCAP cities with a station valid every year 2018–2025: the reported fall in PM2.5 (−23.6%), minus what the model cannot reproduce, minus modelled weather, minus the change in which monitors exist. What is left is the corrected change (−14.1%).
- **(b)** On its own axis: how these cities' satellite PM2.5 moved against comparison cities (+3.8% pooled), and each illustrative city's shrunken estimate.
- **(c)** The same decomposition for four cities: Chennai, Hyderabad, Kolkata and New Delhi. Every city is in figure S3.

**The change from the plan (a dated deviation from DEC-150, approved by Reenu).**
- The proposal's figure ended with a "policy-attributable residual". DEC-150, written before the H1 verdict, drew the satellite estimate as a step down from the corrected change and called what was left "the part not attributed to NCAP".
- Once H1 was not identified, that subtraction assumes exactly what the design could not establish.
- The two numbers are also different quantities on different time bases:
  - a ground change from 2018 to 2025, in % of 2018;
  - a satellite difference from a synthetic comparison, averaged over the post-listing years.
- So the satellite estimate now sits on its own axis, with its own label, and is never subtracted.

**How to read the step labels.** Each removed part is labelled with the step it makes, e.g. "+2.9 pp removed" for modelled weather. The sign is the bar's direction. This was a review fix: the first version printed the part's contribution to the reported change (−2.9 pp) on a bar that moved up.

**How the four cities were chosen.** By a rule on station counts: per region, the city with the most stations in 2025, then the next most. That uses no outcome. But I wrote the rule after seeing every city's decomposition, so the figure says so and points to S3 for all cities.

*If asked "why not just show the policy effect?":* because the study did not identify one. The registered pre-trend test failed, so the honest figure shows what the data support:
- how much of the reported fall survives correction;
- separately, that these cities' satellite PM2.5 did not fall relative to comparable cities.

*If asked "isn't Hyderabad going from −18% reported to +14% corrected suspicious?":*
- It has one continuous station and gained four more.
- The new stations read much cleaner, so the all-station average fell even though the continuous station rose.
- That is the network-composition effect the project is about, and it rests on one monitor. That is why each city panel shows its station counts.

## Style rules, and how they are enforced

- **One palette** (validated for colour blindness; re-run this phase), **one font**, sizes raised so the figures are readable on a slide.
- **Colour never carries meaning alone:**
  - figure 2's entry periods have marker shapes;
  - figure 5's markers show whether each city's credible interval is above 0, below 0, or spans it;
  - figure 8 has a line panel beside the heatmap.
- **Units on every axis, and uncertainty on every estimate:** CIs, credible intervals, the GAM–LightGBM range, station bootstraps.
- **No ranking.**
  - Every named list is alphabetical.
  - Figure 6 keeps its sorted, unnamed units because its purpose is to show that ranks are too uncertain to mean anything (Reenu kept it, with that purpose stated on the figure).
- **The wording check is code, not discipline.**
  - It caught "counterfactual" on figure 4's axis and "attributable to NCAP" in two notes.
  - It also flagged "best-quality QA" in figure S2. That is MAIAC's own name for a QA level, so it is allowed explicitly.
- **Alt text and captions are generated, and every claim in them was checked against the tables.** Two first drafts were wrong and were fixed:
  - E1 claimed the IGP is highest in every month; that holds for satellite, not ground.
  - Figure 3 quoted a 5.3% weather share. That is a different statistic from the report's 5.1% (a median of per-city medians), so the caption now says exactly which it is.
- **Byte-stable output.** Rebuilding gives byte-identical figures: 55 of 55 files, including `figures.md`. This closes the figure half of an open item from Phase 4.

## Figure S2, the new supplementary figure

ACAG PM2.5 and raw MAIAC AOD, on exactly the same units, for every Phase 8b specification and the monitor-gain split, with the pre-written readings at each row's end.

What it makes visible at a glance:
- AOD's relative change is below ACAG's in all five specifications.
- The two differ most in the units that gained **no** monitor. That is why the leakage reading weakened in Phase 8b.

The axis says "AOD, not PM2.5: read its direction only".

## The dashboard

**What a visitor sees.**
- An index with a select box and an A–Z list of the 113 NCAP urban centres.
- For each city:
  - its facts (cities, state, region, listing year, population, whether it gained a monitor);
  - ground PM2.5 and PM10, raw, deweathered and composition-corrected where they exist;
  - its satellite PM2.5;
  - its city-level relative change, unshrunk and shrunken;
  - a data-quality table.
- The "not identified" caveat is at the top of every page.
- An About page with each source's licence and citation.

**What it deliberately does not show:**
- **The synthetic comparison's own trajectory** (the proposal's "counterfactual trend"). It is not saved per city, and a drawn gap would be read as an effect.
- **Ranks or p-values.**
- **AOD.**

**How it is built.**
- Everything is precomputed in the analysis environment by `python -m src.dashboard.build`.
- The site is plain Markdown, so Quarto runs no code.
- Quarto lives in a separate environment (`envs/site.yml`, locked in `envs/site-lock.yml`). This was Reenu's instruction, so the analysis lock stays exactly as registered and tested.
- GitHub Actions renders the committed sources and deploys them; there is no server.

**Licences, checked on the day (hard rule 2).**
- The CPCB mirror is ODbL with share-alike, so the site's ground-derived data are offered under the ODbL.
- ERA5 moved to CC BY in July 2025; the page carries the Copernicus notice and DOIs.
- ACAG's V5.GL.06 page asks for three citations, including a 2025 dust paper.
- GHSL and MAIAC citations are from their own catalogue pages.

*If asked "can I find the best city on the dashboard?":* no, by design. The shrunken estimates have rank intervals spanning about 75 of 113 places (figure 6). A league table would present noise as information, so the cities are alphabetical and no rank is shown.

## Things that went wrong and were fixed

- **Snakemake.** Moving figure drawing out of `eda.py` marked everything downstream stale.
  - The tables were rerun and compared: byte-identical.
  - The data stages were then marked current with `--touch`, as in earlier phases, and every figure rule ran through Snakemake.
- **Layout.** Many layout fixes after looking at each render: clipped labels, colliding captions, a legend over a map, rotated labels running into a note.
- **Dashboard text.**
  - The first city pages printed the 2019 cohort's averaging years for every city.
  - They also compared station counts that meant different things (stations with any data, against valid stations).
  - Both were fixed before the site was committed.
- **Shell escapes.** This shell turns `\\n` in heredocs into line breaks. Edits containing escapes were redone with the editor.

## What was checked

- **Tests:** 254 pass, including 26 for figures (`tests/test_viz.py`) and 6 for the dashboard (`tests/test_dashboard.py`). They cover:
  - wording rules;
  - byte-stable saves;
  - the catalogue;
  - the city-selection rule;
  - the dashboard helpers;
  - the committed pages: caveat on every page, A–Z order, no rank wording, every required attribution.
- **Snakemake:** `snakemake -n pregate` and `-n viz` have nothing to do; `-n all` lists only the Phase 10 report stub.
- **The rendered site:** 115 pages, 0 broken internal links, the caveat on all 113 city pages, screenshots inspected.

## Turning the site on (Reenu, once)

In the GitHub repository:
1. Open **Settings → Pages**.
2. Under **Build and deployment → Source**, choose **GitHub Actions**.
3. Open **Actions → dashboard → Run workflow** (branch `main`), or push any change under `dashboard/`.

The site then appears at https://breenu.github.io/ncap-evaluation/. The first run before step 2 fails at "deploy", which is expected.

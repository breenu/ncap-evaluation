# Weather, Monitors, or Policy?

**A meteorologically normalised, quasi-experimental evaluation of India's National Clean Air Programme (NCAP), 2015–2025.**

India's National Clean Air Programme, launched in January 2019, set 131 cities targets for cutting particulate pollution. Progress is judged on the readings of their monitoring stations. Those readings move for three reasons that are hard to tell apart:

- **Measurement:** stations fail, get stuck, are recalibrated, and the network grew several-fold during the programme itself.
- **Weather:** a still, cold winter raises pollution with no change in emissions.
- **Policy:** the question of interest.

This project separates the three, and asks whether NCAP cities saw larger falls in PM2.5 and PM10 than comparable cities once measurement and weather are accounted for.

## Research questions

| # | Theme | Question |
|---|---|---|
| RQ1 | Measurement | How much of each city's reported change comes from data-quality artefacts and changes in which stations exist? |
| RQ2 | Weather | How much of the year-to-year change is driven by meteorology? |
| RQ3 | Policy | What is the causal effect of NCAP enrolment on PM2.5 (and, as weaker evidence, PM10)? |
| RQ4 | Heterogeneity | Does the effect vary across cities, and does it look like dust control (PM10 falling more than PM2.5)? |

The specification is [`docs/proposal.pdf`](docs/proposal.pdf).

**Effect estimation is pre-registered.** No post-2019 treatment effect is computed until the analysis plan ([`docs/analysis_plan.md`](docs/analysis_plan.md), currently a draft) is approved and committed. The pipeline enforces this through [`config/gate.yaml`](config/gate.yaml): gated steps refuse to run while it is closed. Until then, no figure or table compares NCAP with non-NCAP cities after 2018.

## Status

**Phases 1–3 of 10 are complete. There are no effect estimates.** Progress and the next steps are in [`docs/PROGRESS.md`](docs/PROGRESS.md); every judgement call is logged in [`docs/DECISIONS.md`](docs/DECISIONS.md), and each phase has a plain-language note in [`docs/phase-notes/`](docs/phase-notes/).

| Phase | What it did |
|---|---|
| 1. Skeleton | Pinned environment (Python 3.12 + R 4.5, `conda-lock`), Snakemake workflow, tests, CI |
| 2. Acquisition | Resumable, checksum-verified downloaders for every source ([data cards](docs/data-cards/)); NCAP city lists and funding extracted from 14 official PDFs, each row traceable to its page, and checked against printed totals |
| 3. Storage, cleaning, audit | Cleaned station-hour and station-day panel; data-quality flags; reliability score for every station-year; satellite PM2.5 for every Indian urban centre; station audit ([`docs/audit_report.md`](docs/audit_report.md)); draft analysis plan |

### What the Phase 3 audit found about the data

These are findings about data quality, not about NCAP.

- **The ground data source was verified, not trusted.** CPCB's own download service is offline, so station data come from a public mirror of CPCB's repository. The mirror was checked against OpenAQ's independent copy of the same stations; the two are identical where both hold data, and the few exceptions are explained ([`docs/mirror-openaq-crosscheck.md`](docs/mirror-openaq-crosscheck.md)).
- **The mirror holds CPCB's *validated* data, while OpenAQ carries the raw real-time feed**, with zero, negative and impossible values that CPCB's validation removes. So the most recent months, January–March 2026, which only OpenAQ has, are treated as provisional.
- **The mirror's timestamps are Indian time labelled as UTC.** This was found by three independent tests (matched values, the sun, weather reanalysis), and every reader corrects it.
- **Station locations were settled from the data.** Two copies of one instrument's record share identical values at identical moments, which identifies stations whose names or coordinates disagree ([`docs/station_metadata_review.md`](docs/station_metadata_review.md)).
- **Instrument faults are flagged by rules set from the data.** The rules cover values pinned at instrument ceilings, "flatlined" analysers, PM2.5 exceeding PM10, and level shifts relative to neighbouring stations, with the detector calibrated against a no-shift null.
- **Monitoring gaps are not concentrated on the dirtiest days**, contrary to a common concern.
- **The pre-NCAP ground network was tiny.** For PM10 there is effectively one baseline year (2018). The satellite layer, which reaches back to 2010, is therefore the primary evidence for effects.

Figures: [station-entry map](reports/figures/fig2_station_entry.png) (where and when stations came online) and [data-quality heatmap](reports/figures/fig8_quality_heatmap.png) (reliability of every station-year).

### What comes next

| Phase | |
|---|---|
| 4 | Pre-gate computations on pre-2019 data only (minimum detectable effect, baseline balance); analysis plan finalised, reviewed and approved |
| 5 | Deweathering (RQ2): Grange & Carslaw weather normalisation with LightGBM and GAM |
| 6 | Network-composition correction (RQ1): all stations vs a balanced station panel vs satellite |
| 7 | Causal analysis (RQ3): satellite synthetic difference-in-differences, event study, staggered-adoption estimator, ground-station checks, full robustness table |
| 8 | Heterogeneity and mechanism (RQ4): Bayesian hierarchical model of city effects; PM10 vs PM2.5 |
| 9–10 | Figures, read-only dashboard, technical report, policy brief, clean-clone reproducibility check |

## Reproduce

Requires [Miniforge](https://github.com/conda-forge/miniforge) (conda-forge). Python 3.12 and R 4.5 live in one environment, pinned exactly in `conda-lock.yml` (win-64 and linux-64).

```bash
# 1. Environment
conda install -n base -c conda-forge conda-lock      # once
conda-lock install -n ncap conda-lock.yml
conda activate ncap                                   # always run inside the activated environment
Rscript workflow/scripts/install_r_extra.R           # did, DRDID, fastglm, synthdid (pinned versions)

# 2. Tests (synthetic data only)
pytest

# 3. Pipeline
snakemake -n pregate           # dry run: what would be built
snakemake --cores 1 pregate    # downloads, cleaning, audit, EDA: everything allowed before the gate
snakemake --cores 8 all        # the full analysis (stops at the gate until the plan is approved)
```

**Data access.**
- Raw data are downloaded by the pipeline into `data/raw/` and never committed. Each source's `MANIFEST.csv` is committed, with source URL, download date and SHA-256, so a fresh download is verified byte for byte.
- Most sources need no account. Two need free keys: Copernicus CDS (ERA5 weather) in `~/.cdsapirc`, and OpenAQ in `.env` (copy [`.env.example`](.env.example)).
- The raw downloads total about 11 GB.
- On a 16 GB laptop the Phase 1–3 pipeline takes a few hours, most of it downloading. `--cores 1` keeps memory in bounds.

**Sources and licences.** Each source's provenance, version, licence and known issues are in [`docs/data-cards/`](docs/data-cards/):
- CPCB station data via the `Vonter/india-cpcb-aqi` mirror (ODbL 1.0);
- OpenAQ;
- ACAG satellite PM2.5 (Washington University in St. Louis);
- ERA5 (Copernicus);
- GHSL Urban Centre Database and population (JRC, CC BY 4.0);
- DataMeet boundaries (CC BY 4.0);
- GeoNames (CC BY 4.0);
- Natural Earth (public domain);
- NASA FIRMS;
- official NCAP documents.

Any derived dataset built from the CPCB mirror is published under ODbL.

## Layout

```
config/           thresholds and parameters (params.yaml), pre-registration gate, regions, name mappings
data/raw/         immutable downloads + MANIFEST.csv per source (manifests committed, data not)
data/interim/     intermediate Parquet and audit tables (rebuilt by the pipeline)
data/processed/   analysis-ready Parquet (rebuilt by the pipeline)
src/acquire/      one downloader per source; NCAP PDF extraction and checks
src/clean/        ingest, cross-check, station metadata, flags, audit, reliability, satellite zonal statistics
src/normalise/    deweathering and network-composition correction (Phases 5–6)
src/causal/       causal estimators (Phase 7; gated)
src/hierarchical/ Bayesian pooling of city effects (Phase 8; gated)
src/viz/          figures
src/common/       paths, manifest, gate
workflow/         Snakemake rules and setup scripts
tests/            pytest, synthetic fixtures only
reports/figures/  generated figures
docs/             plan, decisions log, progress, data cards, generated reports, phase notes
```

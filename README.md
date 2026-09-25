# Weather, Monitors, or Policy?

**A meteorologically normalised, quasi-experimental evaluation of India's National Clean Air Programme (NCAP), 2015–2025.**

Did NCAP cities see larger falls in particulate matter than comparable non-NCAP cities once two things are removed: weather, and changes in which monitoring stations exist? The project separates three things tangled together in every reported number: **measurement** (data-quality artefacts and network composition), **weather** (removed by deweathering) and **policy** (what remains, estimated against comparable cities).

> **Status:** Phase 1 (skeleton) complete. No data has been downloaded yet and there are no results.
> Progress and next steps: [`docs/PROGRESS.md`](docs/PROGRESS.md). Full plan: [`docs/PLAN.md`](docs/PLAN.md).

## Research questions

| # | Theme | Question |
|---|---|---|
| RQ1 | Measurement | How much of each city's reported change comes from data-quality artefacts and changes in which stations exist? |
| RQ2 | Weather | How much of the year-to-year change is driven by meteorology? |
| RQ3 | Policy | What is the causal effect of NCAP enrolment on PM2.5 and PM10? |
| RQ4 | Heterogeneity | Does the effect scale with funding? Is it larger for PM10 than PM2.5? |

The specification is [`docs/proposal.pdf`](docs/proposal.pdf). Effect estimation is pre-registered: no post-2019 treatment effect is computed until `docs/analysis_plan.md` (written in Phase 3–4) is approved, and the pipeline enforces this ([`config/gate.yaml`](config/gate.yaml)).

## Reproduce

Requires [Miniforge](https://github.com/conda-forge/miniforge) (conda-forge). Python 3.12 and R 4.5 are installed into one environment.

```bash
# 1. Environment (exact pins from the lock file)
conda install -n base -c conda-forge conda-lock      # once (or run it via: uvx conda-lock ...)
conda-lock install -n ncap conda-lock.yml
conda activate ncap
Rscript workflow/scripts/install_r_extra.R           # did, DRDID, fastglm, synthdid (pinned)

# 2. Tests
pytest

# 3. Pipeline
snakemake --cores 8 pregate    # everything allowed before the analysis plan is approved
snakemake --cores 8 all        # full rebuild from data/raw/ (needs the gate open)
```

Some downloads need free accounts: Copernicus CDS (ERA5) and OpenAQ. Keys go in `~/.cdsapirc` and `.env`, never in code. See [`docs/PLAN.md`](docs/PLAN.md) §2.

## Layout

```
config/        thresholds and parameters (params.yaml), pre-registration gate, region definitions
data/raw/      immutable downloads + MANIFEST.csv per source (manifests committed, data not)
data/interim/  intermediate Parquet
data/processed/ analysis-ready Parquet
src/acquire/   one downloader per source
src/clean/     audit flags, reliability score
src/normalise/ deweathering (LightGBM, mgcv GAM), network-composition correction
src/causal/    synthetic DiD, event study, Callaway & Sant'Anna, placebos
src/hierarchical/ Bayesian pooling of city effects
src/viz/       figures
src/common/    paths, manifest, gate
workflow/      Snakemake rules and setup scripts
tests/         pytest, synthetic fixtures only
notebooks/     exploration only; nothing the report depends on
reports/       Quarto report, figures, policy brief
dashboard/     read-only precomputed city explorer
docs/          plan, decisions log, progress, data cards, audit report, phase notes
```

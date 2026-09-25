# Phase 1: Skeleton

**What this phase produced:** an empty but working pipeline. There is no data and there are no results yet. What exists now is the structure every later result will pass through, and three safety mechanisms that make the project's rules enforceable instead of promises.

## What was built

1. **A pinned environment.** One conda environment (`ncap`) holds Python 3.12 and R 4.5. `conda-lock.yml` records the exact version and build of every package for Windows and Linux, so the environment can be rebuilt identically on a clean machine.
2. **A pipeline skeleton.** `snakemake` knows every stage of the project and the order they depend on each other: acquire → clean → EDA / deweather → composition → causal → hierarchical → figures → report. Each stage is a stub for now and gets filled in by its phase.
3. **Three safety mechanisms** in `src/common/`, each with tests.

## The three safety mechanisms, and why they matter

**The pre-registration gate** (`gate.py`, `config/gate.yaml`). The project promises to write down its analysis plan *before* looking at post-2019 results. Without that, it would be possible, even unconsciously, to try specifications until one "works" (the garden of forking paths). Here the promise is code: any step that estimates NCAP's effect calls `require_gate()`, which refuses to run until the plan is approved and the commit containing it is recorded. Running `snakemake all` today stops at the causal stage with a clear error. That is intended.

*If asked "how do I know you didn't peek?":* the gate file, the commit history and the test `test_repo_gate_is_closed` show that the effect-estimating code could not run before the plan was committed.

**Immutable raw data with a manifest** (`manifest.py`). Every downloaded file will be recorded with its source URL, the upstream version id, the download date and a SHA-256 fingerprint. The downloader skips files it already has, so re-running is safe (idempotent). It *refuses* three things:
- overwriting a file whose upstream version changed
- accepting a file of unknown origin
- accepting a re-download whose fingerprint differs from the recorded one

Each of those would mean the raw data had silently changed, and the project's numbers could no longer be traced back. The manifests are committed to git, and the data is not. So someone cloning the repo can re-download and *prove* they got byte-identical inputs.

**No placeholder thresholds** (`config/params.yaml`). Parameters the proposal fixes are filled in, such as the 75% completeness rule and the 60/90% sensitivity values. Those it leaves open, such as how many identical hours count as a "flatline", are deliberately `null`. A made-up number typed in "for now" tends to survive to the final report. `null` forces the choice to be made with evidence, and logged, when it is first needed.

## A problem found and how it was solved

The staggered-adoption estimator (Callaway & Sant'Anna, R package `did`) could not be installed from conda-forge: its recent builds depend on a package version that conda-forge does not have. Two options were rejected:
- **Downgrading to R 4.3**, which would have meant old versions of everything else.
- **Switching to a less-established Python port**, which would have meant a less trusted implementation of a headline method.

Instead, conda-forge provides R and all of `did`'s other dependencies. The three missing packages come from a **dated snapshot of CRAN** (Posit Package Manager, 25 Sep 2026), which fixes their versions as firmly as the lock file does. A smoke test proves the result works: it runs `did` on the package's own example dataset and `synthdid` on the California Prop 99 example from the SDID paper. Import alone isn't enough, because the compiled parts only fail when they actually run.

The same check turned up a design constraint: `synthdid` supports only *simultaneous* adoption. Because NCAP added cities in waves, SDID will be run per adoption cohort and aggregated, with Callaway & Sant'Anna as the check designed for staggered timing.

## Why Python *and* R

Python runs the pipeline. R is used for exactly three things, where the R package is the reference implementation written by the method's own authors: `mgcv` (GAMs), `synthdid` (Arkhangelsky et al.) and `did` (Callaway & Sant'Anna). In an interview, "I used the authors' implementation and tested it on their published example" is easier to defend than a re-implementation.

## What was checked

- 41 tests pass. They cover:
  - gate logic, including the committed gate being shut
  - every manifest rule, on synthetic files only
  - that every heavy library imports and the R estimators run
- `snakemake -n all` shows the full 11-job DAG.
- `snakemake pregate` runs.
- `snakemake all` stops at the gate.

## What's next

Phase 2 (acquisition), starting with a cheap feasibility probe of the ground data, which is the biggest risk (see `PROGRESS.md`).

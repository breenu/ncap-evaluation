# PROGRESS

Handoff file: a fresh session should be able to continue from this alone.
Read with [`PLAN.md`](PLAN.md) (what and how), [`DECISIONS.md`](DECISIONS.md) (why) and `CLAUDE.md` (rules).

*Last updated: 2026-09-26, end of Phase 1.*

## Status

| Phase | State |
|---|---|
| 0 Plan | ✅ approved 2026-09-26 (answers in PLAN.md §8) |
| 1 Skeleton | ✅ done, **awaiting Reenu's approval** |
| 2 Acquisition | not started |
| 3–10 | not started |

Pre-registration gate: **closed** (`config/gate.yaml`). No post-2019 effect estimates exist.

## Done

- **Phase 0:** `docs/PLAN.md`; review answers recorded; DEC-001 to DEC-021.
- **Phase 1:**
  - Miniforge installed at `%USERPROFILE%\miniforge3`. Env `ncap` has Python 3.12.14 and R 4.5, pinned in `conda-lock.yml` for win-64 and linux-64.
    The local env was rebuilt from the lock file (`conda-lock install -n ncap conda-lock.yml`), and all checks were re-run on it.
  - R extras (did, DRDID, fastglm, synthdid) are installed by `workflow/scripts/install_r_extra.R` (DEC-022).
  - Snakemake DAG: 9 stub stages plus `pregate` and `all` targets. `all` stops at the gate (tested).
  - `src/common/`: `paths.py`, `manifest.py` (idempotent downloads, immutable raw data), `gate.py`.
  - Config: `params.yaml` (undecided thresholds are `null`, DEC-024), `gate.yaml`, `regions.yaml` (draft).
  - Tests: 41 passing. They cover gate, manifest, heavy imports, and R estimators actually running.
  - CI: `.github/workflows/tests.yml`. It has **not run yet**, because nothing has been pushed.
  - Phase note: `docs/phase-notes/01-skeleton.md`.

## How to run (Windows, Git Bash or PowerShell)

```bash
conda activate ncap            # or: ~/miniforge3/Scripts/conda.exe run -n ncap --no-capture-output <cmd>
pytest
snakemake -n all               # dry run
snakemake --cores 8 pregate
```

## Next: Phase 2 (acquisition)

Start with **step 0, the feasibility probe**, before any bulk download (PLAN.md §4):
- the OpenAQ India location list and a coverage matrix by year
- confirm the ACAG Asia extent covers India
- one CDS time-series request for Delhi
- a FIRMS access test

Report go/no-go on the ground source to Reenu.

Before step 0: create `~/.cdsapirc` and `.env` with **placeholder** values and tell Reenu where they are. Reenu pastes the keys (DEC-019). Confirm sizes before any download over 2 GB.

## Open problems

- **OpenAQ India coverage is unknown** (R1). This is the biggest risk to Layer B, RQ1 and RQ2.
- **NCAP city counts** (131 vs 130; 48 vs 49 XV-FC) are to be reconciled from source PDFs.
- **FIRMS archive** did not respond on 2026-09-26.
- **V6.GL.03 has no methods note.** If one appears, revisit DEC-001.
- **CI is unverified** until the first push. Micromamba's handling of the lock file's pip entry (pyfixest) is the likeliest failure point.
- `config/regions.yaml` is a draft (IGP membership of Jharkhand, coastal distance, whether "peninsular/other" needs splitting). It gets finalised in Phase 3.
- Possible extension (not scheduled): official PRANA/NAMP PM10 series as a "reported" reference (DEC-016).

# PROGRESS

Handoff file: a fresh session should be able to continue from this alone.
Read with [`PLAN.md`](PLAN.md) (what and how), [`DECISIONS.md`](DECISIONS.md) (why) and `CLAUDE.md` (rules).

*Last updated: 2026-09-26, Phase 2 step 0 (feasibility probe) done; waiting for Reenu's go/no-go decision on the ground source.*

## Status

| Phase | State |
|---|---|
| 0 Plan | ✅ approved 2026-09-26 (answers in PLAN.md §8) |
| 1 Skeleton | ✅ approved 2026-09-26; pushed; CI green |
| 2 Acquisition | step 0 done (probe); bulk downloads **not started**, awaiting decision |
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
  - CI: `.github/workflows/tests.yml` on the private repo `breenu/ncap-evaluation`.
    - First run failed: `fastglm` source build on Linux lacked the RcppEigen/BH headers.
    - Fixed in `dd31f52` by adding `r-rcppeigen` and `r-bh` (lock diff: only those two added).
    - Run 36187837666 passed: 41 tests, none skipped, R estimators ran on Linux.
  - Phase note: `docs/phase-notes/01-skeleton.md`.
- **Phase 2, step 0 (feasibility probe):**
  - Keys: `~/.cdsapirc` (CDS) and `.env` (`OPENAQ_API_KEY`, optional `FIRMS_MAP_KEY`) were created with placeholders and filled in by Reenu. `.env` is gitignored; `.env.example` is committed.
  - `src/acquire/probe.py` (checks), `probe_report.py` (report), `s3.py` (anonymous S3 listing), `http_range.py` (read remote Parquet footers without downloading). Tests: `tests/test_probe.py`. 48 tests pass.
  - Report: `docs/data-probe.md` (generated; do not edit). Facts are in DEC-028 to DEC-036.

## How to run (Windows, Git Bash or PowerShell)

```bash
conda activate ncap            # or: ~/miniforge3/Scripts/conda.exe run -n ncap --no-capture-output <cmd>
pytest
snakemake -n all               # dry run
snakemake --cores 8 pregate
```

## Next: Reenu decides the ground source, then Phase 2 steps 1–6

The step 0 finding: **OpenAQ is a no-go as the sole ground source.** It has essentially no CPCB data for 2023–2024 (DEC-030). CPCB's own repository endpoints return 404 (DEC-031).

Proposed (awaiting approval):
- **Primary ground source:** the CPCB repository mirror (Vonter, ODbL) for 2015–2025, 4.12 GB of Parquet.
- **OpenAQ:** for Jan–Mar 2026 and as an independent cross-check on the overlapping years (2016–22, 2025), 1.10 GB from S3.

Downloads over 2 GB need confirmation: mirror 4.12 GB; ACAG 4.68 GB in total (largest single item 1.84 GB).

Open questions for Reenu:
- whether to accept the mirror
- whether to reverse-engineer CPCB's new CCR endpoints instead (not done)
- whether to get a FIRMS MAP_KEY for 2025–26 and for a consistent MODIS collection (DEC-036)
- whether bulk downloads should wait for a non-hotspot connection

Then steps 1–6 of PLAN.md §4. The OpenAQ module becomes a mirror + OpenAQ module.

## Open problems

- **Ground source (R1 realised):**
  - OpenAQ has a 2023–24 hole. The proposed replacement is a third-party mirror, so its provenance is one step removed from CPCB. Mitigation: cross-check against OpenAQ's independent ingestion wherever the two overlap, and record asset sha256s.
  - Mirror timestamps are labelled UTC; confirm whether they are really IST (compare the diurnal cycle with OpenAQ).
  - ODbL share-alike applies to any derived *database* published from the mirror.
- **The pre-2018 ground network is thin in every source** (DEC-033). This limits the ground-layer pre-period and RQ1 baselines. It does not affect Layer A.
- **Network:** the machine is on an iPhone hotspot (mobile data). Its DNS intermittently fails for `cds.climate.copernicus.eu` and the ECMWF object store; cdsapi's retries got through. The planned total of about 12 GB is heavy on mobile data.
- **NCAP city counts** (131 vs 130; 48 vs 49 XV-FC) are to be reconciled from source PDFs.
- **FIRMS:** the keyless archive works but stops at 2024, and the MODIS processing version switches in 2018 and 2023 (DEC-036).
- **V6.GL.03 has no methods note.** If one appears, revisit DEC-001.
- `config/regions.yaml` is a draft (IGP membership of Jharkhand, coastal distance, whether "peninsular/other" needs splitting). It gets finalised in Phase 3.
- Possible extension (not scheduled): official PRANA/NAMP PM10 series as a "reported" reference (DEC-016).

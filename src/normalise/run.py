"""Run deweathering tasks, resumably (Phase 5).

    python -m src.normalise.run prepare --run main [--sids a,b,...]
    python -m src.normalise.run fit --run main --family lgbm|gam|gam_k4|both [--workers 8]
    python -m src.normalise.run cvcheck --run main [--family ...]   (CV only, both trend conventions)

`gam` is the GAM with the one-year-knot trend (DEC-116); `gam_k4` the previous GAM (DEC-101), kept
as a sensitivity family; `both` = lgbm and gam.

A task is one station x pollutant x family. `fit` lists the input folders of the run, skips tasks
whose .json already exists (src.normalise.store), and runs the rest: LightGBM in a process pool,
the GAM in `workers` Rscript processes, each given its share of the tasks. Stopping the run (Ctrl+C,
a crash, a reboot) loses at most the tasks in progress; running the same command again resumes.

Run settings: pilot = 1000 draws, both resampling schemes, convergence checkpoints; main and
registered = N draws from config (DEC-113), the primary scheme and the sensitivity scheme (DEC-109).
`registered` refits only the series with near-constant station-years, keeping them (DEC-110).
"""

import argparse
import os
import subprocess
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed

import pandas as pd

from src.common.paths import INTERIM, ROOT
from src.normalise import lgbm
from src.normalise.features import INPUTS, POLLUTANTS, cfg, prepare
from src.normalise.store import FITS, is_done

LOGS = INTERIM / "logs"
ONE_THREAD = {k: "1" for k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS")}


def settings(run: str) -> tuple[int, list[str], list[int]]:
    """(draws, schemes, checkpoints) for a run."""
    c = cfg()
    if run == "pilot":
        return c["resamples_max"], ["seasonal", "annual"], list(c["convergence_grid"])
    n = c["resamples_default"]
    return n, [c["resample_scheme"], *c["resample_schemes_sensitivity"]], [n]


def all_tasks(run: str) -> pd.DataFrame:
    rows = [
        {"run": run, "pollutant": p, "sid": d.name, "n_fit": (d / "fit.parquet").stat().st_size}
        for p in POLLUTANTS
        for d in sorted((INPUTS / run / p).glob("*"))
        if (d / "folds.parquet").exists()
    ]
    return pd.DataFrame(rows, columns=["run", "pollutant", "sid", "n_fit"])


def pending(run: str, family: str) -> pd.DataFrame:
    t = all_tasks(run)
    keep = [not is_done(run, family, p, s) for p, s in zip(t.pollutant, t.sid)]
    # largest first, so the long tasks do not all end up last
    return t[keep].sort_values("n_fit", ascending=False).reset_index(drop=True)


def _lgbm_task(run, pollutant, sid, schemes, checkpoints):
    os.environ.update(ONE_THREAD)
    lgbm.run_task(run, pollutant, sid, schemes, checkpoints)
    return pollutant, sid


def fit_lgbm(run: str, workers: int) -> None:
    _, schemes, checkpoints = settings(run)
    todo = pending(run, "lgbm")
    print(f"lgbm: {len(todo)} tasks to run", flush=True)
    t0, failed = time.time(), []
    with ProcessPoolExecutor(workers) as pool:
        futs = {
            pool.submit(_lgbm_task, run, p, s, schemes, checkpoints): (p, s)
            for p, s in zip(todo.pollutant, todo.sid)
        }
        for i, f in enumerate(as_completed(futs), 1):
            try:
                f.result()
            except Exception as e:  # noqa: BLE001 - reported; the task stays pending for a re-run
                failed.append(futs[f])
                print(f"  FAILED {futs[f]}: {type(e).__name__}: {e}", flush=True)
            if i % 10 == 0 or i == len(futs):
                print(f"  lgbm {i}/{len(futs)} ({time.time() - t0:.0f} s)", flush=True)
    if failed:
        raise SystemExit(f"lgbm: {len(failed)} tasks failed; re-run to retry them")


def fit_gam(run: str, workers: int, family: str = "gam") -> None:
    _, schemes, checkpoints = settings(run)
    todo = pending(run, family)
    print(f"{family}: {len(todo)} tasks to run", flush=True)
    if todo.empty:
        return
    LOGS.mkdir(parents=True, exist_ok=True)
    tmp = FITS / run / "_gam_tasks"
    tmp.mkdir(parents=True, exist_ok=True)
    env = {**os.environ, **ONE_THREAD, "NCAP_GAM_FAMILY": family}
    procs = []
    for w in range(min(workers, len(todo))):
        part = todo.iloc[w::workers][["run", "pollutant", "sid"]]
        f = tmp / f"{family}_worker{w}.csv"
        part.to_csv(f, index=False)
        log = open(LOGS / f"normalise_{run}_{family}_worker{w}.log", "a", encoding="utf-8")  # noqa: SIM115
        cmd = ["Rscript", "src/normalise/gam.R", str(f), ",".join(schemes), ",".join(map(str, checkpoints))]
        procs.append((subprocess.Popen(cmd, cwd=ROOT, env=env, stdout=log, stderr=log), log))
    t0 = time.time()
    while any(p.poll() is None for p, _ in procs):
        time.sleep(30)
        left = len(pending(run, family))
        print(f"  {family} {len(todo) - left}/{len(todo)} ({time.time() - t0:.0f} s)", flush=True)
    for _, log in procs:
        log.close()
    left = pending(run, family)
    if len(left):
        raise SystemExit(f"{family}: {len(left)} tasks not done; see {LOGS}/normalise_{run}_{family}_worker*.log")


CONVENTIONS = ("clamp", "last_year")


def _cv_lgbm(run, pollutant, sid, convention):
    os.environ.update(ONE_THREAD)
    lgbm.cv_only(run, pollutant, sid, convention)


def cvcheck(run: str, workers: int, families: list[str]) -> None:
    """CV predictions only, for the given families, both test-year trend conventions (DEC-107).
    Cheap: no resampling. Always recomputed in full."""
    t = all_tasks(run)
    if "lgbm" in families:
        with ProcessPoolExecutor(workers) as pool:
            futs = [pool.submit(_cv_lgbm, run, p, s, c) for c in CONVENTIONS for p, s in zip(t.pollutant, t.sid)]
            for f in as_completed(futs):
                f.result()
    for fam in [f for f in families if f != "lgbm"]:
        _cv_gam(run, workers, t, fam)
    print(f"cvcheck: {len(t)} series x {families} x {len(CONVENTIONS)} conventions", flush=True)


def _cv_gam(run: str, workers: int, t: pd.DataFrame, family: str) -> None:
    tmp = FITS / run / "_gam_tasks"
    tmp.mkdir(parents=True, exist_ok=True)
    env = {**os.environ, **ONE_THREAD, "NCAP_GAM_FAMILY": family}
    procs = []
    for c in CONVENTIONS:
        for w in range(workers // 2):
            f = tmp / f"cvcheck_{family}_{c}_{w}.csv"
            t.iloc[w :: workers // 2][["run", "pollutant", "sid"]].to_csv(f, index=False)
            cmd = ["Rscript", "src/normalise/gam.R", str(f), "cvonly", c]
            procs.append(subprocess.Popen(cmd, cwd=ROOT, env=env))
    codes = [p.wait() for p in procs]
    if any(codes):
        raise SystemExit(f"cvcheck: {family} workers exited with {codes}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("step", choices=["prepare", "fit", "cvcheck"])
    ap.add_argument("--run", choices=["pilot", "main", "registered"], required=True)
    ap.add_argument("--family", choices=["lgbm", "gam", "gam_k4", "both"], default="both")
    ap.add_argument("--sids", help="comma-separated station ids (prepare; default all)")
    ap.add_argument("--workers", type=int, default=cfg()["workers"])
    a = ap.parse_args()
    if a.step == "prepare":
        n, schemes, _ = settings(a.run)
        sids = a.sids.split(",") if a.sids else None
        s = prepare(a.run, sids, n, schemes)
        (INPUTS / a.run).mkdir(parents=True, exist_ok=True)
        s.to_csv(INPUTS / a.run / "series.csv", index=False)
        print(f"prepared {s.skipped.isna().sum() if 'skipped' in s else len(s)} series; "
              f"skipped: {s.skipped.value_counts().to_dict() if 'skipped' in s else {}}")  # fmt: skip
        return
    families = ["lgbm", "gam"] if a.family == "both" else [a.family]
    if a.step == "cvcheck":
        cvcheck(a.run, a.workers, families)
        return
    if "lgbm" in families:
        fit_lgbm(a.run, a.workers)
    for fam in [f for f in families if f != "lgbm"]:
        fit_gam(a.run, a.workers, fam)


if __name__ == "__main__":
    sys.exit(main())

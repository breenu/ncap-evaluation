"""Where deweathering outputs live, and how a task is marked done (resumable runs, Phase 5).

One task = one station x pollutant x model family. Its outputs are
    data/interim/normalise/fits/<run>/<family>/<pollutant>/<sid>.parquet   daily predictions
    data/interim/normalise/fits/<run>/<family>/<pollutant>/<sid>.json      timings; written LAST
Each file is written to a temporary name and renamed into place, so a crash, a kill or the laptop
sleeping mid-write never leaves a half-written file under the final name. A task is done when its
.json exists; a re-run skips done tasks and redoes the rest.
"""

import json
import os
from pathlib import Path

import pandas as pd

from src.common.paths import INTERIM, PROCESSED

FITS = INTERIM / "normalise" / "fits"
MODELS = PROCESSED / "models"


def task_paths(run: str, family: str, pollutant: str, sid: str) -> tuple[Path, Path]:
    d = FITS / run / family / pollutant
    return d / f"{sid}.parquet", d / f"{sid}.json"


def is_done(run: str, family: str, pollutant: str, sid: str) -> bool:
    return task_paths(run, family, pollutant, sid)[1].exists()


def write_atomic_parquet(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    df.to_parquet(tmp, index=False)
    os.replace(tmp, path)


def write_atomic_json(obj: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(obj, indent=1), encoding="utf-8")
    os.replace(tmp, path)


def cvcheck_path(run: str, family: str, convention: str, pollutant: str, sid: str) -> Path:
    """CV-only predictions under one trend convention (pilot comparison, DEC-107)."""
    return FITS / run / "cvcheck" / f"{family}_{convention}" / pollutant / f"{sid}.parquet"


def model_path(family: str, pollutant: str, sid: str, ext: str) -> Path:
    return MODELS / family / pollutant / f"{sid}.{ext}"

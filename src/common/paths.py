"""Project paths and config loading.

Every module gets file locations from here instead of hard-coding strings,
so the layout can change in one place.
"""

from functools import cache
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]

CONFIG = ROOT / "config"
DATA = ROOT / "data"
RAW = DATA / "raw"  # immutable downloads + MANIFEST.csv per source (hard rule 7)
INTERIM = DATA / "interim"
PROCESSED = DATA / "processed"
REPORTS = ROOT / "reports"
FIGURES = REPORTS / "figures"
DOCS = ROOT / "docs"


def raw_dir(source: str) -> Path:
    """Folder holding one source's raw files and its manifest, e.g. data/raw/openaq."""
    return RAW / source


def load_yaml(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


@cache
def params() -> dict:
    """Analysis parameters from config/params.yaml (cached; the file is read once per process)."""
    return load_yaml(CONFIG / "params.yaml")

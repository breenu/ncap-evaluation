"""Shared figure style (proposal style rules; DEC-192). Every figure:
- has a title "Figure N." that states the question it answers;
- labels units on every axis (ug/m3 written as µg/m³, or % with what it is a % of);
- shows uncertainty on every estimate;
- uses one validated colour-blind-safe palette (categorical slots 1-4 pass CVD and normal-vision checks
  on the light surface, re-run 2026-10-03; slots 3-4 are below 3:1 contrast, so every multi-series chart
  also carries a legend, direct labels and distinct markers: colour never carries meaning alone), one
  sequential blue ramp and one diverging blue-grey-red pair;
- uses one font (DejaVu Sans) at sizes readable on a slide (base 10 pt, notes >= 8 pt);
- thin marks (2 px lines, >= 6 pt markers), hairline recessive grid, text in ink colours.
Figures are written as PNG (300 dpi) and SVG to reports/figures/, with a JSON sidecar holding the
generated caption and alt text (DEC-194). Every text drawn on the figure, and the caption and alt text,
pass the wording check (DEC-193) before anything is written. SVGs are byte-stable: fixed hash salt and no
date metadata (DEC-094/192).
"""

import json
from dataclasses import asdict, dataclass
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap

from src.common.paths import FIGURES
from src.viz import wording

SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK_2 = "#52514e"
GRID = "#e6e5e1"
NEUTRAL = "#b9b8b2"
LAND = "#f4f3ef"  # map fill: lighter than the diverging midpoint, so a near-0 marker never melts into the land
MID = "#d9d8d3"  # diverging midpoint (grey)
CATEGORICAL = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100"]  # fixed order, never cycled
MARKERS = ["o", "s", "^", "D"]
SEQ_BLUE = ["#cde2fb", "#b7d3f6", "#9ec5f4", "#86b6ef", "#6da7ec", "#5598e7", "#3987e5",
            "#2a78d6", "#256abf", "#1c5cab", "#184f95", "#104281", "#0d366b"]  # fmt: skip
DIVERGING = LinearSegmentedColormap.from_list("blue_grey_red", ["#2a78d6", MID, "#e34948"])
SEQ = LinearSegmentedColormap.from_list("seq_blue", [SEQ_BLUE[1], SEQ_BLUE[12]])
REGIONS = ["igp", "coastal", "peninsular/other", "north-east"]
REGION_LABEL = {"igp": "Indo-Gangetic Plain", "coastal": "Coastal", "peninsular/other": "Peninsular / other",
                "north-east": "North-east"}  # fmt: skip
UG = "µg/m³"
NOTE_SIZE = 8
NOT_IDENTIFIED = "H1 is not identified by this design (registered pre-trend test failed): not an effect of NCAP."


@dataclass
class Meta:
    """What the catalogue (docs/figures.md) and the dashboard show beside a figure (DEC-194)."""

    number: str  # "1", "3b", "S2", "E1"
    title: str
    question: str
    caption: str
    alt: str


def pct(x):
    """Natural-log estimate -> % change, 100 (e^b - 1)."""
    import numpy as np

    return 100 * np.expm1(np.asarray(x, dtype=float))


def apply() -> None:
    mpl.rcParams.update(
        {
            "figure.facecolor": SURFACE,
            "axes.facecolor": SURFACE,
            "savefig.facecolor": SURFACE,
            "font.family": "DejaVu Sans",
            "font.size": 10,
            "axes.edgecolor": NEUTRAL,
            "axes.linewidth": 0.6,
            "axes.labelcolor": INK_2,
            "axes.labelsize": 10,
            "axes.titlecolor": INK,
            "axes.titlesize": 10.5,
            "axes.titleweight": "bold",
            "axes.titlelocation": "left",
            "axes.grid": True,
            "grid.color": GRID,
            "grid.linewidth": 0.6,
            "grid.linestyle": "-",
            "axes.axisbelow": True,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "xtick.color": INK_2,
            "ytick.color": INK_2,
            "xtick.labelsize": 9,
            "ytick.labelsize": 9,
            "lines.linewidth": 2,
            "lines.solid_capstyle": "round",
            "lines.markersize": 6,
            "legend.frameon": False,
            "legend.fontsize": 9,
            "legend.labelcolor": INK,
            "svg.hashsalt": "ncap-evaluation",  # stable element ids (DEC-094)
            "svg.fonttype": "path",
        }
    )


def header(fig: plt.Figure, number: str, title: str, y: float = 0.995) -> None:
    """The figure's title: 'Figure N. <the question it answers>'."""
    fig.suptitle(f"Figure {number}. {title}", x=0.0, y=y, ha="left", va="top", fontsize=12, fontweight="bold",
                 color=INK)  # fmt: skip


def source_note(fig: plt.Figure, text: str, y: float = -0.01) -> None:
    fig.text(0.0, y, text, ha="left", va="top", fontsize=NOTE_SIZE, color=INK_2, wrap=True)


def save(fig: plt.Figure, name: str, meta: Meta | None = None, directory: Path | None = None,
         formats: tuple[str, ...] = ("png", "svg"), dpi: int = 300) -> list[Path]:
    """Check the wording (DEC-193), then write the figure (PNG and SVG by default) and the caption/alt-text sidecar.
    `directory` defaults to reports/figures/; the dashboard writes its own PNGs elsewhere (DEC-199)."""
    wording.check_figure(fig, name)
    if meta is not None:
        for field in ("title", "question", "caption", "alt"):
            wording.check(getattr(meta, field), f"{name} {field}")
    out_dir = FIGURES if directory is None else directory
    out_dir.mkdir(parents=True, exist_ok=True)
    out = []
    for ext in formats:
        p = out_dir / f"{name}.{ext}"
        md = {"Date": None} if ext == "svg" else {"Software": None}
        fig.savefig(p, dpi=dpi if ext == "png" else None, bbox_inches="tight", metadata=md)
        out.append(p)
    if meta is not None:
        p = out_dir / f"{name}.json"
        p.write_text(json.dumps({"name": name, **asdict(meta)}, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        out.append(p)
    plt.close(fig)
    return out

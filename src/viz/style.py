"""Shared figure style (proposal style rules; dataviz method). Every figure:
- labels units on every axis (ug/m3 written as µg/m³);
- shows uncertainty on every estimate;
- uses a colour-blind-safe palette, validated (categorical slots 1-4 pass CVD and normal-vision
  checks on the light surface; slots 3-4 are below 3:1 contrast, so every multi-series chart also
  carries a legend, direct end-labels and distinct markers: colour never carries meaning alone);
- thin marks (2 px lines, >= 8 px markers), hairline recessive grid, text in ink colours.
Figures are written as PNG (300 dpi) and SVG to reports/figures/.
"""

from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt

from src.common.paths import FIGURES

SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK_2 = "#52514e"
GRID = "#e6e5e1"
NEUTRAL = "#b9b8b2"
CATEGORICAL = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100"]  # fixed order, never cycled
MARKERS = ["o", "s", "^", "D"]
SEQ_BLUE = ["#cde2fb", "#b7d3f6", "#9ec5f4", "#86b6ef", "#6da7ec", "#5598e7", "#3987e5",
            "#2a78d6", "#256abf", "#1c5cab", "#184f95", "#104281", "#0d366b"]  # fmt: skip
REGIONS = ["igp", "coastal", "peninsular/other", "north-east"]
REGION_LABEL = {"igp": "Indo-Gangetic Plain", "coastal": "Coastal", "peninsular/other": "Peninsular / other",
                "north-east": "North-east"}  # fmt: skip
UG = "µg/m³"


def apply() -> None:
    mpl.rcParams.update(
        {
            "figure.facecolor": SURFACE,
            "axes.facecolor": SURFACE,
            "savefig.facecolor": SURFACE,
            "font.family": "DejaVu Sans",
            "font.size": 9,
            "axes.edgecolor": NEUTRAL,
            "axes.linewidth": 0.6,
            "axes.labelcolor": INK_2,
            "axes.titlecolor": INK,
            "axes.titlesize": 10,
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
            "lines.linewidth": 2,
            "lines.solid_capstyle": "round",
            "lines.markersize": 6,
            "legend.frameon": False,
            "legend.labelcolor": INK,
        }
    )


def save(fig: plt.Figure, name: str) -> list[Path]:
    FIGURES.mkdir(parents=True, exist_ok=True)
    out = []
    for ext in ("png", "svg"):
        p = FIGURES / f"{name}.{ext}"
        fig.savefig(p, dpi=300 if ext == "png" else None, bbox_inches="tight")
        out.append(p)
    plt.close(fig)
    return out


def source_note(fig: plt.Figure, text: str) -> None:
    fig.text(0.0, -0.02, text, ha="left", va="top", fontsize=7, color=INK_2, wrap=True)

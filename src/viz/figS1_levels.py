"""Supplementary figure S1 (DESCRIPTIVE; DEC-154 item 2): what happened to satellite PM2.5 in NCAP units
and in the control pool, 2010-2024. Not one of the proposal's eight figures; no effect is computed.

    python -m src.viz.figS1_levels
"""

import pandas as pd
from matplotlib import pyplot as plt
from matplotlib.lines import Line2D

from src.causal import layer_a as A
from src.viz import style as S

COL = {"NCAP units": S.CATEGORICAL[0], "control pool": S.CATEGORICAL[1]}
MARK = {"NCAP units": S.MARKERS[0], "control pool": S.MARKERS[1]}


def figure(d: pd.DataFrame) -> plt.Figure:
    S.apply()
    fig, ax = plt.subplots(figsize=(8, 4.6))
    ax.axvspan(2019.5, 2020.5, color=S.GRID, zorder=0)
    ax.text(2020, 1.0, "2020", transform=ax.get_xaxis_transform(), ha="center", va="top", fontsize=7, color=S.INK_2)
    ax.axvline(2018.5, color=S.NEUTRAL, linewidth=1, linestyle="--", zorder=1)
    ax.text(2018.6, 0.02, "NCAP launched (Jan 2019)", transform=ax.get_xaxis_transform(), fontsize=7, color=S.INK_2)
    handles = []
    for g, x in d.groupby("group"):
        x = x.sort_values("year")
        ax.fill_between(x.year, x.lo95, x.hi95, color=COL[g], alpha=0.18, linewidth=0, zorder=1)
        ax.plot(x.year, x["mean"], color=COL[g], marker=MARK[g], markersize=5, zorder=3)
        last = x.iloc[-1]
        ax.annotate(f"{g} ({int(last.n)})", (last.year, last["mean"]), xytext=(6, 0), textcoords="offset points",
                    va="center", fontsize=8, color=S.INK)  # fmt: skip
        handles.append(Line2D([], [], color=COL[g], marker=MARK[g], label=f"{g}: mean over units, 95% CI band"))
    ax.set_xlim(2009.5, 2026.3)
    ax.set_xticks(range(2010, 2025, 2))
    ax.set_xlabel("Year")
    ax.set_ylabel(f"Annual population-weighted PM2.5 ({S.UG})")
    ax.set_title("What happened to satellite PM2.5 in NCAP units and in the control pool? (descriptive)", fontsize=9.5)
    ax.legend(handles=handles, loc="lower left", fontsize=7.5)
    S.source_note(fig, "DESCRIPTIVE: unweighted means over units of ACAG V5.GL.06 annual PM2.5, population-weighted over each "
                  "GHSL urban centre; 113 NCAP units and 923 control-pool centres (2015 population >= 100,000). No effect is "
                  "computed here: the groups differ in size and region, which the causal designs try to account for. "
                  "Numbers: docs/causal_report.md.")  # fmt: skip
    fig.tight_layout()
    return fig


def main() -> None:
    S.save(figure(pd.read_csv(A.OUT / "levels.csv")), "figS1_levels")


if __name__ == "__main__":
    main()

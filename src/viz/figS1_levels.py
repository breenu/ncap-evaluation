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


def figure(d: pd.DataFrame) -> tuple[plt.Figure, S.Meta]:
    S.apply()
    fig, ax = plt.subplots(figsize=(9.5, 5.6))
    ax.axvspan(2019.5, 2020.5, color=S.GRID, zorder=0)
    ax.text(2020, 1.0, "2020", transform=ax.get_xaxis_transform(), ha="center", va="top", fontsize=8.5, color=S.INK_2)
    ax.axvline(2018.5, color=S.NEUTRAL, linewidth=1, linestyle="--", zorder=1)
    ax.text(2018.6, 0.02, "NCAP launched (Jan 2019)", transform=ax.get_xaxis_transform(), fontsize=8.5, color=S.INK_2)
    handles = []
    for g, x in d.groupby("group"):
        x = x.sort_values("year")
        ax.fill_between(x.year, x.lo95, x.hi95, color=COL[g], alpha=0.18, linewidth=0, zorder=1)
        ax.plot(x.year, x["mean"], color=COL[g], marker=MARK[g], markersize=5, zorder=3)
        last = x.iloc[-1]
        ax.annotate(f"{g} ({int(last.n)})", (last.year, last["mean"]), xytext=(6, 0), textcoords="offset points",
                    va="center", fontsize=9, color=S.INK)  # fmt: skip
        handles.append(Line2D([], [], color=COL[g], marker=MARK[g], label=f"{g}: mean over units, 95% CI band"))
    ax.set_xlim(2009.5, 2026.3)
    ax.set_xticks(range(2010, 2025, 2))
    ax.set_xlabel("Year")
    ax.set_ylabel(f"Annual population-weighted PM2.5 ({S.UG})")
    ax.legend(handles=handles, loc="lower left", fontsize=9)
    fig.tight_layout(rect=(0, 0, 1, 0.9))
    S.header(fig, "S1", "What happened to satellite PM2.5 in NCAP units and in the control pool? (descriptive)")
    S.source_note(fig, "DESCRIPTIVE: unweighted means over units of ACAG V5.GL.06 annual PM2.5, population-weighted over each "
                  "GHSL urban centre; 2015 population ≥ 100,000 for the pool. No effect is computed: the groups differ in size "
                  "and region.")  # fmt: skip
    m = d.set_index(["group", "year"])["mean"]
    a, c = (m[("NCAP units", 2018)], m[("NCAP units", 2024)]), (m[("control pool", 2018)], m[("control pool", 2024)])
    ch = lambda x: 100 * (x[1] / x[0] - 1)  # noqa: E731
    n_t, n_c = int(d[d.group == "NCAP units"].n.max()), int(d[d.group == "control pool"].n.max())
    cap = (f"Mean annual population-weighted satellite PM2.5 (ACAG V5.GL.06, {S.UG}) over the {n_t} NCAP units and the {n_c} "
           f"control-pool centres, 2010–2024, unweighted across units, with 95% t-intervals; 2020 shaded. From 2018 to 2024 the "
           f"NCAP units' mean went from {a[0]:.1f} to {a[1]:.1f} {S.UG} ({ch(a):+.1f}%) and the pool's from {c[0]:.1f} to "
           f"{c[1]:.1f} ({ch(c):+.1f}%): both fell, the pool more. Descriptive: the groups differ in size and region, and no "
           "effect is computed from these means.")  # fmt: skip
    peaks = sorted({int(x.loc[x["mean"].idxmax(), "year"]) for _, x in d.groupby("group")})
    alt = (f"Line chart of satellite PM2.5, 2010–2024, for NCAP units and control-pool centres. Both peak in "
           f"{' and '.join(map(str, peaks))} and "
           f"fall after 2018; the control pool starts higher and falls further, from {c[0]:.0f} to {c[1]:.0f} {S.UG}, against "
           f"{a[0]:.0f} to {a[1]:.0f} for NCAP units, so by 2024 the two are about equal.")  # fmt: skip
    return fig, S.Meta("S1", "What happened to satellite PM2.5 in NCAP units and in the control pool?",
                       "Descriptive context for figure 4", cap, alt)  # fmt: skip


def main() -> None:
    f, m = figure(pd.read_csv(A.OUT / "levels.csv"))
    S.save(f, "figS1_levels", m)


if __name__ == "__main__":
    main()

"""Figure 6: city-level estimates before and after shrinkage, and how uncertain their ranking is
(proposal figure plan: "posterior distributions of city effects, before and after shrinkage"; DEC-167).
Phase 8.

(a) every NCAP unit's unshrunk per-unit SDID estimate with +-1.96 x its placebo SE, beside its shrunken 95%
credible interval, units sorted by posterior mean; (b) 95% intervals of each unit's rank among the 113.
No city names: neither panel is a best/worst list (plan §5). H1 is not identified (DEC-151): these are
city-level relative changes, not effects of NCAP.

    python -m src.viz.fig6_shrinkage
"""

import numpy as np
import pandas as pd
from matplotlib import pyplot as plt
from matplotlib.lines import Line2D

from src.hierarchical.city_estimates import OUT
from src.viz import style as S

C_RAW, C_POST = S.NEUTRAL, S.CATEGORICAL[0]


def pct(x):
    return 100 * np.expm1(np.asarray(x, float))


def main() -> None:
    S.apply()
    c = pd.read_csv(OUT / "city_shrunken.csv")
    c = c[c.version == "primary"].sort_values("post_mean").reset_index(drop=True)
    co = pd.read_csv(OUT / "pool_coefs.csv")
    avg = co[(co.version == "primary") & (co.param == "average city-level relative change")].iloc[0]
    tau = co[(co.version == "primary") & (co.param == "tau")].iloc[0]
    y = np.arange(len(c))
    fig, (ax, bx) = plt.subplots(1, 2, figsize=(11, 7.5), gridspec_kw={"width_ratios": [1.6, 1]}, sharey=True)
    ax.hlines(y + 0.22, pct(c.est - 1.96 * c.se), pct(c.est + 1.96 * c.se), color=C_RAW, linewidth=1.2)
    ax.scatter(pct(c.est), y + 0.22, s=10, facecolors=S.SURFACE, edgecolors=S.INK_2, linewidths=0.6, zorder=3)
    ax.hlines(y - 0.22, pct(c.post_lo95), pct(c.post_hi95), color=C_POST, linewidth=1.4)
    ax.scatter(pct(c.post_mean), y - 0.22, s=10, color=C_POST, zorder=3)
    ax.axvline(0, color=S.INK_2, linewidth=0.8)
    ax.axvline(pct(avg["mean"]), color=C_POST, linewidth=0.8, linestyle="--")
    ax.set_xlabel("Relative change in satellite PM2.5 after listing\n(%; listed unit minus its synthetic comparison)")
    ax.set_ylabel(f"NCAP urban centres (n = {len(c)}), sorted by shrunken estimate")
    ax.set_yticks([])
    ax.set_title("(a) Before and after shrinkage")
    ax.legend(handles=[
        Line2D([], [], color=C_RAW, marker="o", markerfacecolor=S.SURFACE, markeredgecolor=S.INK_2, label="Unshrunk: estimate ± 1.96 × placebo SE"),
        Line2D([], [], color=C_POST, marker="o", label="Shrunken: posterior mean, 95% credible interval"),
        Line2D([], [], color=C_POST, linestyle="--", label=f"Average city-level relative change ({pct(avg['mean']):+.1f}%)"),
    ], loc="upper center", bbox_to_anchor=(0.5, -0.1), ncol=2, fontsize=7.5)  # fmt: skip
    bx.hlines(y, c.rank_lo95, c.rank_hi95, color=C_POST, linewidth=1.4)
    bx.scatter(c.rank_mean, y, s=10, color=C_POST, zorder=3)
    bx.set_xlabel(f"Rank among the {len(c)}, 95% interval\n(1 = largest relative fall)")
    bx.set_xlim(0, len(c) + 1)
    bx.set_title("(b) How uncertain the ranking is")
    med_w = float(np.median(c.rank_hi95 - c.rank_lo95))
    fig.suptitle("City-level relative changes before and after shrinkage: NOT effects of NCAP (H1 not identified)",
                 x=0.0, ha="left", fontsize=11, fontweight="bold", color=S.INK)  # fmt: skip
    S.source_note(fig, "Unshrunk: each NCAP unit's own synthetic difference-in-differences (ACAG V5.GL.06, log population-weighted, "
                  "2010-2024 without 2020) with the SD of the same estimator over every control used as a fake treated unit (DEC-162). "
                  "Shrunken: Bayesian measurement-error model with the five registered moderators (DEC-163); between-unit SD "
                  f"tau = {tau['mean']:.3f} log units. Median width of a unit's 95% rank interval: {med_w:.0f} places. "
                  "No names are shown: this is not a best/worst list. The registered pre-trend test failed, so nothing here is "
                  "attributable to NCAP.")  # fmt: skip
    S.save(fig, "fig6_shrinkage")


if __name__ == "__main__":
    main()

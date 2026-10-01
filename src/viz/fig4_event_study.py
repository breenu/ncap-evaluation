"""Figure 4: event study (proposal figure plan; question: were pre-trends parallel, and when did any
effect appear?). Phase 7, Layer A; rules DEC-142 to DEC-144.

Left panel: effect of NCAP listing on annual population-weighted PM2.5 (ACAG V5.GL.06) by year relative
to the listing year, 2020 dropped:
    - Sun & Abraham interaction-weighted coefficients with pointwise 95% CIs (clustered by unit);
    - Callaway & Sant'Anna dynamic aggregation (never-treated controls) with uniform 95% bands.
Right panel: the calendar-2020 coefficient from the fit that includes 2020 with its own indicator.
Effects are shown as % change, 100 (e^b - 1), on one axis; the reference year has no coefficient.

    python -m src.viz.fig4_event_study
"""

import json

import numpy as np
import pandas as pd
from matplotlib import pyplot as plt
from matplotlib.lines import Line2D

from src.causal import layer_a as A
from src.viz import style as S

ES = A.OUT / "event_study"
C_SA, C_CS, C_OWN = S.CATEGORICAL[0], S.CATEGORICAL[1], S.INK_2


def pct(x):
    return 100 * np.expm1(np.asarray(x, dtype=float))


def load() -> dict:
    meta = json.loads((ES / "es_primary_meta.json").read_text(encoding="utf-8"))
    return {
        "sa": pd.read_csv(ES / "es_primary_coefs.csv"),
        "meta": meta,
        "cs": pd.read_csv(A.OUT / "cs" / "cs_nevertreated_dynamic.csv"),
        "own": pd.read_csv(ES / "es_own2020_own.csv"),
        "honest": pd.read_csv(ES / "es_primary_honest_summary.csv", dtype={"breakdown_note": str}).iloc[0],
        "sdid": pd.read_csv(A.OUT / "sdid_summary.csv"),
    }


def figure(D: dict) -> plt.Figure:
    S.apply()
    fig, (ax, ax2) = plt.subplots(1, 2, figsize=(10, 5.8), gridspec_kw={"width_ratios": [7, 1], "wspace": 0.08}, sharey=True)
    sa, cs = D["sa"], D["cs"]
    ax.axhline(0, color=S.INK_2, linewidth=0.8, zorder=1)
    ax.axvline(-0.5, color=S.NEUTRAL, linewidth=1, linestyle="--", zorder=1)
    ax.text(-0.4, 0.98, "listing year →", transform=ax.get_xaxis_transform(), fontsize=7.5, color=S.INK_2, va="top")
    ax.errorbar(sa.rel - 0.14, pct(sa.coef), yerr=[pct(sa.coef) - pct(sa.lo95), pct(sa.hi95) - pct(sa.coef)],
                fmt=S.MARKERS[0], color=C_SA, markersize=6, elinewidth=1.2, capsize=0, zorder=3)  # fmt: skip
    ax.errorbar(cs.rel + 0.14, pct(cs.att), yerr=[pct(cs.att) - pct(cs.ulo), pct(cs.uhi) - pct(cs.att)],
                fmt=S.MARKERS[1], color=C_CS, markerfacecolor=S.SURFACE, markeredgewidth=1.4, markersize=6,
                elinewidth=1.2, capsize=0, zorder=3)  # fmt: skip
    ax.plot([-1.14], [0], marker="o", markersize=6, markerfacecolor=S.SURFACE, markeredgecolor=S.NEUTRAL, linestyle="none")
    ax.annotate("Sun & Abraham\nreference", (-1.14, -0.15), xytext=(-1.6, -4.2), ha="center", fontsize=6.5, color=S.INK_2,
                arrowprops={"arrowstyle": "-", "color": S.NEUTRAL, "linewidth": 0.6})  # fmt: skip
    ax.set_xticks(range(-9, 6))
    ax.set_xlim(-9.6, 5.6)
    ax.set_xlabel("Years relative to NCAP listing (calendar 2020 dropped)")
    ax.set_ylabel("Effect on annual population-weighted PM2.5\n(% change, listed minus counterfactual)")
    m = D["meta"]
    w, avg, h = m["wald_pre"], m["avg_post"], D["honest"]
    p = D["sdid"].set_index(["spec_id", "estimand"]).loc[("primary", "att")]
    bd = f"{h.breakdown_note} (original CI {str(h.direction).split(' (')[0]})"
    ax.set_title("Did PM2.5 in NCAP-listed urban centres diverge from comparable centres, before or after listing?",
                 fontsize=9.5, pad=34)  # fmt: skip
    ax.text(0.0, 1.015, (f"Pre-trend test (l = −9 … −2): Wald p = {w['p']:.4f}, so registered rule (b) fails.   "
                         f"Average effect l = 0 … +5: {pct(avg['coef']):+.1f}% (95% CI {pct(avg['lo95']):+.1f} to {pct(avg['hi95']):+.1f}).\n"
                         f"HonestDiD breakdown M̄: {bd}.   Primary SDID: {pct(p.att):+.1f}% "
                         f"(95% CI {pct(p.lo95):+.1f} to {pct(p.hi95):+.1f})."),
            transform=ax.transAxes, ha="left", va="bottom", fontsize=7.2, color=S.INK_2, linespacing=1.4)  # fmt: skip
    ax.grid(axis="x", visible=False)

    o = D["own"].iloc[0]
    ax2.axhline(0, color=S.INK_2, linewidth=0.8)
    ax2.errorbar([0], pct([o.coef]), yerr=[pct([o.coef]) - pct([o.lo95]), pct([o.hi95]) - pct([o.coef])],
                 fmt=S.MARKERS[3], color=C_OWN, markersize=6, elinewidth=1.2)  # fmt: skip
    ax2.set_xticks([0], ["2020"])
    ax2.set_xlim(-1, 1)
    ax2.set_title("Calendar 2020,\nown coefficient", fontsize=8, pad=34)
    ax2.grid(axis="x", visible=False)

    handles = [Line2D([], [], color=C_SA, marker=S.MARKERS[0], linestyle="none", label="Sun & Abraham, 95% CI (pointwise)"),
               Line2D([], [], color=C_CS, marker=S.MARKERS[1], markerfacecolor=S.SURFACE, linestyle="none",
                      label="Callaway & Sant'Anna, 95% band (uniform)"),
               Line2D([], [], color=C_OWN, marker=S.MARKERS[3], linestyle="none", label="2020 coefficient (fit with 2020 included)")]  # fmt: skip
    fig.suptitle("Figure 4. Event study: NCAP listing and satellite PM2.5", x=0.0, y=0.995, ha="left", fontsize=10, fontweight="bold")
    fig.legend(handles=handles, loc="upper left", bbox_to_anchor=(0.0, 0.965), ncol=3, fontsize=7.5)
    sizes = ", ".join(f"{n} ({c})" for c, n in m["cohort_sizes"].items())
    S.source_note(fig, ("Layer A: ACAG V5.GL.06 annual PM2.5, population-weighted over GHSL urban centres; "
                        f"{sizes} treated units by listing cohort vs 923 never-treated centres of 100,000+ "
                        "(2015). Sun & Abraham: unit and region × year effects, ERA5 covariates, SEs clustered by unit; "
                        "cohort 2021's reference is 2019 (its l = −1 is 2020). Callaway & Sant'Anna: did 2.5.1, doubly "
                        "robust without covariates, base period varying: its pre-listing points are year-on-year differences, "
                        "not differences from l = −1 like Sun & Abraham's, so the two are like-for-like only after listing. "
                        "Effects are % changes, 100(e^β − 1). Satellite PM2.5 says nothing directly about PM10, NCAP's "
                        "target pollutant. Numbers: docs/causal_report.md."))  # fmt: skip
    fig.subplots_adjust(left=0.09, right=0.985, top=0.76, bottom=0.11, wspace=0.08)  # explicit: header rows above the axes
    return fig


def main() -> None:
    S.save(figure(load()), "fig4_event_study")


if __name__ == "__main__":
    main()

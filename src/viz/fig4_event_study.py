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


def figure(D: dict) -> tuple[plt.Figure, S.Meta]:
    S.apply()
    fig, (ax, ax2) = plt.subplots(1, 2, figsize=(11.5, 6.6), gridspec_kw={"width_ratios": [7, 1], "wspace": 0.08}, sharey=True)
    sa, cs = D["sa"], D["cs"]
    ax.axhline(0, color=S.INK_2, linewidth=0.8, zorder=1)
    ax.axvline(-0.5, color=S.NEUTRAL, linewidth=1, linestyle="--", zorder=1)
    ax.text(-0.4, 0.98, "listing year →", transform=ax.get_xaxis_transform(), fontsize=8.5, color=S.INK_2, va="top")
    ax.errorbar(sa.rel - 0.14, pct(sa.coef), yerr=[pct(sa.coef) - pct(sa.lo95), pct(sa.hi95) - pct(sa.coef)],
                fmt=S.MARKERS[0], color=C_SA, markersize=6, elinewidth=1.2, capsize=0, zorder=3)  # fmt: skip
    ax.errorbar(cs.rel + 0.14, pct(cs.att), yerr=[pct(cs.att) - pct(cs.ulo), pct(cs.uhi) - pct(cs.att)],
                fmt=S.MARKERS[1], color=C_CS, markerfacecolor=S.SURFACE, markeredgewidth=1.4, markersize=6,
                elinewidth=1.2, capsize=0, zorder=3)  # fmt: skip
    ax.plot([-1.14], [0], marker="o", markersize=6, markerfacecolor=S.SURFACE, markeredgecolor=S.NEUTRAL, linestyle="none")
    ax.annotate("Sun & Abraham\nreference", (-1.14, -0.15), xytext=(-1.6, -4.2), ha="center", fontsize=8, color=S.INK_2,
                arrowprops={"arrowstyle": "-", "color": S.NEUTRAL, "linewidth": 0.6})  # fmt: skip
    ax.set_xticks(range(-9, 6))
    ax.set_xlim(-9.6, 5.6)
    ax.set_xlabel("Years relative to NCAP listing (calendar 2020 dropped)")
    ax.set_ylabel("Listed minus comparison centres, annual\npopulation-weighted PM2.5 (% difference)")
    m = D["meta"]
    w, avg, h = m["wald_pre"], m["avg_post"], D["honest"]
    p = D["sdid"].set_index(["spec_id", "estimand"]).loc[("primary", "att")]
    bd = f"{h.breakdown_note} (original CI {str(h.direction).split(' (')[0]})"
    ax.set_title("Sun & Abraham and Callaway & Sant'Anna, by year relative to listing", fontsize=10.5, pad=44)
    ax.text(0.0, 1.015, (f"H1: not identified by this design. Pre-trend test (relative years −9 to −2): Wald p = {w['p']:.4f}, so registered rule (b) fails.\n"
                         f"Average over relative years 0 to +5: {pct(avg['coef']):+.1f}% (95% CI {pct(avg['lo95']):+.1f} to {pct(avg['hi95']):+.1f}).   "
                         f"HonestDiD breakdown M̄: {bd}.   Primary SDID: {pct(p.att):+.1f}% "
                         f"(95% CI {pct(p.lo95):+.1f} to {pct(p.hi95):+.1f})."),
            transform=ax.transAxes, ha="left", va="bottom", fontsize=8.5, color=S.INK_2, linespacing=1.4)  # fmt: skip
    ax.grid(axis="x", visible=False)

    o = D["own"].iloc[0]
    ax2.axhline(0, color=S.INK_2, linewidth=0.8)
    ax2.errorbar([0], pct([o.coef]), yerr=[pct([o.coef]) - pct([o.lo95]), pct([o.hi95]) - pct([o.coef])],
                 fmt=S.MARKERS[3], color=C_OWN, markersize=6, elinewidth=1.2)  # fmt: skip
    ax2.set_xticks([0], ["2020"])
    ax2.set_xlim(-1, 1)
    ax2.set_title("Calendar 2020,\nown coefficient", fontsize=9, pad=44)
    ax2.grid(axis="x", visible=False)

    handles = [Line2D([], [], color=C_SA, marker=S.MARKERS[0], linestyle="none", label="Sun & Abraham, 95% CI (pointwise)"),
               Line2D([], [], color=C_CS, marker=S.MARKERS[1], markerfacecolor=S.SURFACE, linestyle="none",
                      label="Callaway & Sant'Anna, 95% band (uniform)"),
               Line2D([], [], color=C_OWN, marker=S.MARKERS[3], linestyle="none", label="2020 coefficient (fit with 2020 included)")]  # fmt: skip
    S.header(fig, "4", "Were pre-trends parallel, and when did satellite PM2.5 in listed and comparison centres diverge?")
    fig.legend(handles=handles, loc="upper left", bbox_to_anchor=(0.0, 0.955), ncol=3, fontsize=9)
    sizes = ", ".join(f"{n} ({c})" for c, n in m["cohort_sizes"].items())
    S.source_note(fig, ("ACAG V5.GL.06 annual PM2.5, population-weighted over GHSL urban centres; listed units by cohort "
                        f"{sizes} vs 923 never-treated centres. Callaway & Sant'Anna's pre-listing points are year-on-year "
                        "differences, so the two estimators are like-for-like only after listing. " + S.NOT_IDENTIFIED))  # fmt: skip
    fig.subplots_adjust(left=0.1, right=0.985, top=0.75, bottom=0.12, wspace=0.08)  # explicit: header rows above the axes
    pre = sa[sa.rel < 0]
    o = D["own"].iloc[0]
    cap = (f"Event-study estimates of annual population-weighted satellite PM2.5 (ACAG V5.GL.06) in NCAP-listed urban centres "
           f"minus comparison centres, by year relative to listing (calendar 2020 dropped): Sun & Abraham interaction-weighted "
           f"coefficients with pointwise 95% CIs (unit and region × year effects, ERA5 covariates, SEs clustered by unit) and "
           f"Callaway & Sant'Anna dynamic estimates with uniform 95% bands (never-treated controls). Listed units by cohort: "
           f"{sizes}; 923 never-treated centres. Pre-listing Sun & Abraham coefficients range from {pct(pre.coef.min()):+.1f}% to "
           f"{pct(pre.coef.max()):+.1f}%, but are jointly different from zero (Wald p = {w['p']:.4f}), so the registered rule (b) "
           f"fails and H1 is not identified by this design. Average over relative years 0 to +5: {pct(avg['coef']):+.1f}% (95% CI "
           f"{pct(avg['lo95']):+.1f} to {pct(avg['hi95']):+.1f}); HonestDiD breakdown M̄ = {h.breakdown_note}. Right: the "
           f"calendar-2020 coefficient from a fit that includes 2020 ({pct(o.coef):+.1f}%). Values are % differences, "
           "100(e^β − 1). Satellite PM2.5 says nothing directly about PM10, NCAP's target pollutant. "
           "These are relative changes, not effects of NCAP.")  # fmt: skip
    alt = (f"Event-study chart. Before listing, the yearly differences between listed and comparison centres are small "
           f"({pct(pre.coef.min()):+.1f}% to {pct(pre.coef.max()):+.1f}%) but jointly significant (p = {w['p']:.4f}), so the "
           f"pre-trend test fails. After listing they turn positive, averaging {pct(avg['coef']):+.1f}%: listed centres' PM2.5 "
           "did not fall relative to comparison centres. Not identified as an effect of NCAP.")  # fmt: skip
    return fig, S.Meta("4", "Were pre-trends parallel, and when did satellite PM2.5 in listed and comparison centres diverge?",
                       "Were pre-trends parallel? When did listed and comparison centres diverge?", cap, alt)  # fmt: skip


def main() -> None:
    f, m = figure(load())
    S.save(f, "fig4_event_study", m)


if __name__ == "__main__":
    main()

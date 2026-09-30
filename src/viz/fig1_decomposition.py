"""Figure 1, version 1: how much of an NCAP city's reported change is weather and network composition
(proposal figure plan; question: how much of a city's reported improvement is real?). Phase 6;
rules DEC-125 to DEC-128.

Decomposition, in the proposal's order, of the change 2018 -> 2025 (% of the 2018 value):
    reported     all stations as reported (raw)
    weather      reported minus the same stations deweathered
    composition  all stations deweathered minus the balanced panel deweathered
    corrected    the balanced panel, deweathered (= reported - weather - composition)
    policy       PLACEHOLDER: estimated in Phase 7 (the corrected change still holds national
                 trends shared with non-NCAP cities)
Primary version (GAM, seasonal resampling, primary validity rule, 2018 baseline, strict panel);
LightGBM beside it as open markers (DEC-118/128).

    fig1_decomposition           mean over NCAP cities with a panel, PM2.5 and PM10; 95% CIs from the
                                 cluster bootstrap over cities (DEC-129)
    fig1_decomposition_cities    one waterfall row per NCAP city; 95% station-bootstrap CI on the
                                 corrected change where the city has more than one station

    python -m src.viz.fig1_decomposition
"""

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

from src.normalise import composition as C
from src.viz import style as S
from src.viz.fig3_deweathered import names

POL = {"pm25": "PM2.5", "pm10": "PM10"}
STEPS = [("reported", "Reported\nchange"), ("weather", "Weather"), ("composition", "Network\ncomposition"),
         ("corrected", "Weather- and\ncomposition-\ncorrected"), ("policy", "Policy\n(Phase 7)")]  # fmt: skip
C_WEATHER, C_COMP, C_TOTAL = S.CATEGORICAL[0], S.CATEGORICAL[1], S.INK_2


def load() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    ch = pd.read_parquet(C.OUT / "city_changes.parquet")
    ch = ch[ch.ncap]
    s = pd.read_csv(C.OUT / "summary.csv")
    b = pd.read_csv(C.OUT / "city_boot.csv")
    return ch, s, b


def mean_panel(ax: plt.Axes, s: pd.DataFrame, pol: str) -> None:
    lg = C.Spec("lgbm").label
    get = lambda spec, m: s[(s.spec == spec) & (s.pollutant == pol) & (s.group == "NCAP") & (s.metric == m)].iloc[0]  # noqa: E731
    level, x = 0.0, np.arange(len(STEPS))
    n = int(get(C.PRIMARY.label, "reported").n)
    ticks = []
    for i, (m, lab) in enumerate(STEPS):
        if m == "policy":  # an empty outline over the corrected change: Phase 7 splits it
            corr = get(C.PRIMARY.label, "corrected")["mean"]
            ax.bar(i, corr, width=0.6, facecolor="none", edgecolor=S.NEUTRAL, hatch="///", linewidth=0.8, zorder=1)
            ax.text(i, corr / 2, "Phase 7", ha="center", va="center", fontsize=7, color=S.INK_2,
                    bbox={"facecolor": S.SURFACE, "edgecolor": "none", "pad": 1.5})  # fmt: skip
            ticks.append(lab)
            continue
        r = get(C.PRIMARY.label, m)
        rl = get(lg, m)
        if m in ("reported", "corrected"):
            lo_bar, hi_bar, col, end, end_l = 0.0, r["mean"], C_TOTAL, r["mean"], rl["mean"]
            elo, ehi = r.lo, r.hi
            lvl_l = rl["mean"]
        else:  # a step down from the running level: the change minus this component
            lo_bar, hi_bar = level, level - r["mean"]
            col = C_WEATHER if m == "weather" else C_COMP
            end, end_l = hi_bar, lvl_l - rl["mean"]
            elo, ehi = level - r.hi, level - r.lo
        ax.bar(i, hi_bar - lo_bar, bottom=lo_bar, width=0.6, color=col, linewidth=0, zorder=2)
        ax.errorbar(i - 0.12, end, yerr=[[end - elo], [ehi - end]], fmt="none", ecolor=S.INK, elinewidth=1, capsize=3, zorder=3)
        ax.plot(i + 0.14, end_l, marker="s", markersize=6, markerfacecolor=S.SURFACE, markeredgecolor=S.INK,
                markeredgewidth=1, linestyle="none", zorder=4)  # fmt: skip
        ax.errorbar(i + 0.14, end_l, yerr=[[end_l - (rl.lo if m in ("reported", "corrected") else lvl_l - rl.hi)],
                                           [(rl.hi if m in ("reported", "corrected") else lvl_l - rl.lo) - end_l]],
                    fmt="none", ecolor=S.INK_2, elinewidth=0.8, capsize=2, zorder=3)  # fmt: skip
        val = end if m in ("reported", "corrected") else r["mean"]  # a part's own contribution to the change
        ticks.append(f"{lab}\n{val:+.1f}{'%' if m in ('reported', 'corrected') else ' pp'}")
        level, lvl_l = end, end_l
        if i < 3:
            ax.plot([i + 0.3, i + 0.7], [end, end], color=S.NEUTRAL, linewidth=0.8, zorder=1)
    ax.axhline(0, color=S.INK_2, linewidth=0.8)
    ax.set_xticks(x, ticks, fontsize=7.5)
    ax.set_ylabel("Change in annual mean, 2018 → 2025\n(% of the 2018 value)")
    h = get(C.PRIMARY.label, "h4")
    ax.set_title(f"{POL[pol]}: mean over {n} NCAP cities with a 2018 panel", fontsize=9, pad=16)
    ax.text(0.0, 1.0, f"H4: reported fall minus corrected fall = {h['mean']:.1f} pp (95% CI {h.lo:.1f} to {h.hi:.1f})",
            transform=ax.transAxes, ha="left", va="bottom", fontsize=7.5, color=S.INK_2)  # fmt: skip
    ax.grid(axis="x", visible=False)


def fig_mean(s: pd.DataFrame) -> plt.Figure:
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.4), sharey=True)
    for ax, pol in zip(axes, ("pm25", "pm10"), strict=True):
        mean_panel(ax, s, pol)
    axes[1].set_ylabel("")
    handles = [Patch(color=C_TOTAL, label="Change (GAM, primary)"), Patch(color=C_WEATHER, label="Weather part (its contribution to the change, in pp)"),
               Patch(color=C_COMP, label="Network-composition part"),
               Line2D([], [], color=S.INK, marker="|", linestyle="none", markersize=8, label="95% CI across cities"),
               Line2D([], [], marker="s", markerfacecolor=S.SURFACE, markeredgecolor=S.INK, linestyle="none",
                      label="LightGBM (other family), running level with 95% CI"),
               Patch(facecolor="none", edgecolor=S.NEUTRAL, hatch="///", label="Policy: placeholder until Phase 7")]  # fmt: skip
    fig.tight_layout(rect=(0, 0, 1, 0.85))
    fig.legend(handles=handles, loc="lower left", bbox_to_anchor=(0.0, 0.855), ncol=3, fontsize=7.5)
    fig.suptitle("Figure 1 (v1). How much of NCAP cities' reported change is weather and network composition?",
                 x=0.0, y=0.99, ha="left", va="top", fontsize=10, fontweight="bold")  # fmt: skip
    S.source_note(fig, "Reported = mean over all stations inside the city's GHSL urban centre valid that year (CPCB, "
                  "after the audit's cleaning). Weather = reported minus the same stations deweathered (weather resampled "
                  "within ±15 days of each date, ERA5 2015-2025). Composition = all stations minus the balanced panel "
                  "(stations valid every year 2018-2025), both deweathered. Unweighted means over cities; shared "
                  "polygons (e.g. Delhi NCR) are one city. Most panels hold one station. The corrected change is not "
                  "a policy effect: it still contains trends shared with non-NCAP cities, which Phase 7 estimates. "
                  "Numbers: docs/composition_report.md.")  # fmt: skip
    return fig


def city_panel(ax: plt.Axes, ch: pd.DataFrame, b: pd.DataFrame, pol: str, nm: pd.Series) -> None:
    g = ch[(ch.spec == C.PRIMARY.label) & (ch.pollutant == pol)].copy()
    lg = ch[(ch.spec == C.Spec("lgbm").label) & (ch.pollutant == pol)].set_index("unit_id")
    bb = b[(b.family == "gam") & (b.pollutant == pol)].set_index("unit_id")
    g["name"] = g.unit_id.map(nm).fillna(g.unit_id)
    g = g.sort_values("reported", ascending=False).reset_index(drop=True)
    for i, r in g.iterrows():
        a1 = r.reported - r.weather
        ax.barh(i, r.reported, height=0.22, color=C_TOTAL, linewidth=0, zorder=2)
        ax.barh(i, a1 - r.reported, left=r.reported, height=0.5, color=C_WEATHER, linewidth=0, zorder=2)
        ax.barh(i, r.corrected - a1, left=a1, height=0.5, color=C_COMP, linewidth=0, zorder=2)
        ax.plot(r.corrected, i, marker="D", markersize=5.5, color=S.INK, linestyle="none", zorder=4)
        lo, hi = bb.loc[r.unit_id, ["corrected_lo", "corrected_hi"]]
        if hi > lo:
            ax.plot([lo, hi], [i, i], color=S.INK, linewidth=1, zorder=3)
        ax.plot(lg.loc[r.unit_id, "corrected"], i, marker="s", markersize=5.5, markerfacecolor=S.SURFACE,
                markeredgecolor=S.INK, linestyle="none", zorder=4)  # fmt: skip
    labels = [f"{r['name']}  ({r.n_all_base}→{r.n_all_end} st., panel {r.n_panel})" for _, r in g.iterrows()]
    ax.set_yticks(range(len(g)), labels, fontsize=7)
    xs = np.concatenate([g.reported, g.reported - g.weather, g.corrected, lg.loc[g.unit_id, "corrected"], [0]])
    pad = 0.05 * (xs.max() - xs.min())
    ax.set_xlim(xs.min() - pad, xs.max() + pad)
    ax.invert_yaxis()
    ax.axvline(0, color=S.INK_2, linewidth=0.8)
    ax.set_xlabel("Change in annual mean, 2018 → 2025 (% of the 2018 value)")
    ax.set_title(POL[pol], fontsize=9)
    ax.grid(axis="y", visible=False)


def fig_cities(ch: pd.DataFrame, b: pd.DataFrame) -> plt.Figure:
    nm = names()
    n = [len(ch[(ch.spec == C.PRIMARY.label) & (ch.pollutant == p)]) for p in ("pm25", "pm10")]
    fig, axes = plt.subplots(2, 1, figsize=(8, 0.32 * sum(n) + 2.6), gridspec_kw={"height_ratios": n})
    for ax, pol in zip(axes, ("pm25", "pm10"), strict=True):
        city_panel(ax, ch, b, pol, nm)
    handles = [Patch(color=C_TOTAL, label="Reported change (thin bar, from 0)"), Patch(color=C_WEATHER, label="minus weather"),
               Patch(color=C_COMP, label="minus network composition"),
               Line2D([], [], marker="D", color=S.INK, linestyle="-", linewidth=1, markersize=5,
                      label="Corrected change, GAM (line: 95% station-bootstrap CI, if > 1 station)"),
               Line2D([], [], marker="s", markerfacecolor=S.SURFACE, markeredgecolor=S.INK, linestyle="none",
                      label="Corrected change, LightGBM")]  # fmt: skip
    fig.tight_layout(rect=(0, 0, 1, 0.955))
    fig.legend(handles=handles, loc="lower left", bbox_to_anchor=(0.0, 0.955), ncol=2, fontsize=7)
    fig.suptitle("Figure 1 (v1), per city: reported change → minus weather → minus composition → corrected "
                 "(policy: Phase 7)", x=0.0, y=0.995, ha="left", va="bottom", fontsize=9.5, fontweight="bold")  # fmt: skip
    S.source_note(fig, "NCAP cities (GHSL urban centres) with at least one station valid every year 2018-2025. "
                  "'a→b st.' = stations valid in 2018 and in 2025; 'panel' = stations valid in every year. Each row "
                  "reads left to right from the thin grey bar's end: the blue segment removes weather, the orange "
                  "segment removes the change in which stations exist, and the diamond is what is left. A city with "
                  "one station has no between-station uncertainty; the gap between the diamond and the square shows "
                  "the model-family uncertainty. Primary: GAM, seasonal resampling, primary validity rule.")  # fmt: skip
    return fig


def main() -> None:
    S.apply()
    ch, s, b = load()
    S.save(fig_mean(s), "fig1_decomposition")
    S.save(fig_cities(ch, b), "fig1_decomposition_cities")
    print("figure 1 v1 written")


if __name__ == "__main__":
    main()

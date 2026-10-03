"""Figure 1 (the main figure) and supplementary figures S3 and S4: how much of NCAP cities' reported change
in ground PM is weather and network composition, and how did their satellite PM2.5 move relative to
comparison cities? Rules: DEC-125/126/136 (decomposition), DEC-150 as changed by DEC-191 (no subtraction of
the satellite estimate, no "remaining change"), DEC-162/163 (shrunken city-level relative changes).
Scope (DEC-136): only the NCAP cities with a station valid in every year 2018-2025, mostly single stations;
not NCAP cities in general. H1 is not identified (DEC-151): nothing here is an effect of NCAP.

Decomposition of the change 2018 -> 2025 (% of the 2018 value), in the proposal's order:
    reported      all stations as reported (raw)
    unmodelled    raw minus the same stations' fitted values (DEC-136)
    weather       fitted minus deweathered: modelled weather only (DEC-136)
    composition   all stations deweathered minus the balanced panel deweathered
    corrected     the balanced panel, deweathered (= reported - unmodelled - weather - composition)
Each step removes that part's contribution. Primary: GAM, seasonal resampling, primary validity rule,
2018 baseline, strict panel; LightGBM beside it (DEC-118/128).

    fig1_decomposition          PM2.5: (a) cross-city summary waterfall; (b) satellite PM2.5 relative to
                                comparison units, on its own axis: Layer A restricted to these cities, and the
                                shrunken city-level relative change of each illustrative city; (c) four
                                illustrative cities chosen by DEC-191's station-count rule, alphabetical
    figS3_decomposition_cities  every H4 city, both pollutants, alphabetical
    figS4_decomposition_pm10    PM10 cross-city summary, with the ground DiD (Layer B, secondary) on its own axis
    fig1_slide                  Phase 10 (DEC-210): panel (a) alone at 16:9, titled with one takeaway line built from
                                the same values

    python -m src.viz.fig1_decomposition           (gated: reads Phase 7 and Phase 8 outputs)
    python -m src.viz.fig1_decomposition --slide   (the slide only)
"""

import sys

import numpy as np
import pandas as pd
from matplotlib import pyplot as plt
from matplotlib.gridspec import GridSpec
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

from src.common.paths import INTERIM
from src.normalise import composition as C
from src.viz import style as S
from src.viz.fig3_deweathered import names

POL = {"pm25": "PM2.5", "pm10": "PM10"}
STEPS = ["reported", "unmodelled", "weather", "composition", "corrected"]
LONG = {"reported": "Reported\nchange", "unmodelled": "Unmodelled\nchange", "weather": "Modelled\nweather",
        "composition": "Network\ncomposition", "corrected": "Corrected\nchange"}  # fmt: skip
SHORT = {"reported": "Reported", "unmodelled": "Unmod.", "weather": "Weather", "composition": "Network", "corrected": "Corrected"}
C_TOTAL, C_UNMOD, C_WEATHER, C_COMP = S.INK_2, S.CATEGORICAL[2], S.CATEGORICAL[0], S.CATEGORICAL[1]
STEP_COLOUR = {"reported": C_TOTAL, "unmodelled": C_UNMOD, "weather": C_WEATHER, "composition": C_COMP, "corrected": C_TOTAL}
C_REL = S.INK
N_ILLUSTRATIVE = 4
XLAB_CHANGE = "Change in annual mean, 2018 → 2025\n(% of the 2018 value)"


# ------------------------------------------------------------------ data


def load() -> dict:
    from src.causal import layer_a as A
    from src.hierarchical.city_estimates import OUT as HIER

    ch = pd.read_parquet(C.OUT / "city_changes.parquet")
    sd = pd.read_csv(A.OUT / "sdid_summary.csv").set_index(["spec_id", "estimand"])
    lb = pd.read_csv(A.OUT / "layer_b" / "estimates.csv")
    shr = pd.read_csv(HIER / "city_shrunken.csv")
    return {
        "ch": ch[ch.ncap],
        "s": pd.read_csv(C.OUT / "summary.csv"),
        "b": pd.read_csv(C.OUT / "city_boot.csv"),
        "h4": pd.read_csv(C.OUT / "h4.csv"),
        "restricted": sd.loc[("restricted_pm25", "att")],
        "did_pm10": lb[(lb.version == "primary") & (lb.pollutant == "pm10") & (lb.estimator == "DiD")].iloc[0],
        "shrunken": shr[shr.version == "primary"].set_index("unit_id"),
        "regions": pd.read_csv(INTERIM / "unit_regions.csv").set_index("unit_id").region,
        "names": names(),
    }


def illustrative_cities(ch: pd.DataFrame, regions: pd.Series, n: int = N_ILLUSTRATIVE) -> list[str]:
    """DEC-191: among the primary-version PM2.5 H4 cities, per region the city with the most stations valid in
    2025 (ties: more panel stations, then unit id); then the most stations not yet chosen, up to n. Network
    metadata only, no outcome. Returned in the order chosen; callers sort by name for display."""
    g = ch[(ch.spec == C.PRIMARY.label) & (ch.pollutant == "pm25")].copy()
    g["region"] = g.unit_id.map(regions)
    if g.region.isna().any():
        raise ValueError("an H4 city has no region")
    g = g.sort_values(["n_all_end", "n_panel", "unit_id"], ascending=[False, False, True])
    picks = [x.unit_id.iloc[0] for _, x in g.groupby("region", sort=True)]
    for u in g.unit_id:
        if len(picks) >= n:
            break
        if u not in picks:
            picks.append(u)
    return picks[:n]


def scope(h4: pd.DataFrame, pol: str) -> tuple[int, int]:
    r = h4[h4.is_primary & (h4.pollutant == pol)].iloc[0]
    return int(r.cities), int(r.single_station_panels)


def summary_values(s: pd.DataFrame, pol: str, spec: str) -> dict:
    g = s[(s.spec == spec) & (s.pollutant == pol) & (s.group == "NCAP")].set_index("metric")
    return {m: (g.loc[m, "mean"], g.loc[m, "lo"], g.loc[m, "hi"]) for m in STEPS + ["h4"]}


def city_values(ch: pd.DataFrame, b: pd.DataFrame, unit: str, pol: str, spec: str, family: str) -> dict:
    r = ch[(ch.spec == spec) & (ch.pollutant == pol) & (ch.unit_id == unit)].iloc[0]
    bb = b[(b.unit_id == unit) & (b.pollutant == pol) & (b.family == family)]
    out = {}
    for m in STEPS:
        lo = hi = r[m]
        if len(bb) and bb.iloc[0][f"{m}_hi"] > bb.iloc[0][f"{m}_lo"]:
            lo, hi = bb.iloc[0][f"{m}_lo"], bb.iloc[0][f"{m}_hi"]
        out[m] = (r[m], lo, hi)
    return out


# ------------------------------------------------------------------ drawing


PARTS = {"unmodelled": "unmodelled change", "weather": "modelled weather", "composition": "network composition"}


def step_label(m: str, x: float) -> str:
    """Totals as changes in %; a part as the step it makes when removed (Reenu's review): removing a contribution x
    moves the level by -x, so the label's sign is the direction of the bar."""
    return f"{x:+.1f}%" if m in ("reported", "corrected") else f"{-x:+.1f} pp removed"


def largest_part(v: dict) -> tuple[str, float]:
    """The part whose removal moves the level most, and its step (-contribution)."""
    m = max(PARTS, key=lambda k: abs(v[k][0]))
    return PARTS[m], -v[m][0]


def waterfall(ax: plt.Axes, v: dict, v_alt: dict | None, ticks: dict, value_labels: bool = True) -> None:
    """Reported (from 0) -> each part removed in turn -> corrected (from 0). v[m] = (value, lo, hi): totals are
    changes in %, parts are contributions in pp. The interval of a part is drawn at the running level it
    produces. v_alt (LightGBM) is drawn as open squares at its own running levels, with its interval."""

    def levels(vals):
        lvl, out = 0.0, {}
        for m in STEPS:
            x, lo, hi = vals[m]
            if m in ("reported", "corrected"):
                out[m] = (0.0, x, lo, hi)
                lvl = x
            else:
                out[m] = (lvl, lvl - x, lvl - hi, lvl - lo)
                lvl = lvl - x
        return out

    L = levels(v)
    for i, m in enumerate(STEPS):
        start, end, lo, hi = L[m]
        ax.bar(i, end - start, bottom=start, width=0.62, color=STEP_COLOUR[m], linewidth=0, zorder=2)
        ax.errorbar(i - 0.12, end, yerr=[[end - lo], [hi - end]], fmt="none", ecolor=S.INK, elinewidth=1.1, capsize=3, zorder=3)
        if i < len(STEPS) - 1:  # connector: each step starts where the previous one ended
            ax.plot([i + 0.31, i + 0.69], [end, end], color=S.NEUTRAL, linewidth=0.8, zorder=1)
    if v_alt is not None:
        La = levels(v_alt)
        for i, m in enumerate(STEPS):
            _, end, lo, hi = La[m]
            ax.errorbar(i + 0.14, end, yerr=[[end - lo], [hi - end]], fmt="s", markersize=5.5, markerfacecolor=S.SURFACE,
                        markeredgecolor=S.INK, markeredgewidth=1, ecolor=S.INK_2, elinewidth=0.8, capsize=2, zorder=4)  # fmt: skip
    labs = []
    for m in STEPS:
        x = v[m][0]
        labs.append(f"{ticks[m]}\n{step_label(m, x)}" if value_labels else f"{ticks[m]}  {step_label(m, x)}")
    ax.set_xticks(range(len(STEPS)), labs)
    ax.axhline(0, color=S.INK_2, linewidth=0.8)
    ax.grid(axis="x", visible=False)


def relative_rows(ax: plt.Axes, rows: list[tuple[str, float, float, float, str]], xlabel: str, caveat: str = "") -> None:
    """A forest on its own axis: (label, est %, lo %, hi %, marker); the caveat sits inside the axis, on top."""
    n = len(rows)
    for k, (_lab, est, lo, hi, mk) in enumerate(rows):
        y = n - 1 - k
        ax.errorbar(est, y, xerr=[[est - lo], [hi - est]], fmt=mk, color=C_REL, markersize=7 if mk == "D" else 6,
                    markerfacecolor=C_REL if mk == "D" else S.SURFACE, markeredgewidth=1.3, elinewidth=1.4, capsize=3)  # fmt: skip
    ax.set_yticks(range(n - 1, -1, -1), [r[0] for r in rows])
    ax.set_ylim(-0.7, n - 0.3 + (1.3 if caveat else 0))
    if caveat:
        ax.text(0.03, 0.985, caveat, transform=ax.transAxes, ha="left", va="top", fontsize=9, fontweight="bold", color=S.INK,
                bbox={"facecolor": S.SURFACE, "edgecolor": "none", "pad": 2}, zorder=5)
    ax.axvline(0, color=S.INK_2, linewidth=0.8)
    ax.set_xlabel(xlabel)
    ax.grid(axis="y", visible=False)


def legend_handles(alt_label: str = "LightGBM (other model family), with its 95% interval") -> list:
    return [Patch(color=C_TOTAL, label="Reported and corrected change (correction uses the GAM, the primary model)"),
            Patch(color=C_UNMOD, label="Unmodelled change removed (raw − fitted)"),
            Patch(color=C_WEATHER, label="Modelled weather removed (fitted − deweathered)"),
            Patch(color=C_COMP, label="Network composition removed (all stations − balanced panel)"),
            Line2D([], [], color=S.INK, marker="|", linestyle="none", markersize=9, label="95% interval"),
            Line2D([], [], marker="s", markerfacecolor=S.SURFACE, markeredgecolor=S.INK, linestyle="none", label=alt_label)]  # fmt: skip


# ------------------------------------------------------------------ figure 1


def fig_main(D: dict) -> tuple[plt.Figure, S.Meta]:
    pol, spec, lg = "pm25", C.PRIMARY.label, C.Spec("lgbm").label
    n_c, n_single = scope(D["h4"], pol)
    v, va = summary_values(D["s"], pol, spec), summary_values(D["s"], pol, lg)
    picks = sorted(illustrative_cities(D["ch"], D["regions"]), key=lambda u: D["names"].get(u, u))
    nm = lambda u: D["names"].get(u, u)  # noqa: E731
    r = D["restricted"]
    rel = (S.pct(r.att), S.pct(r.lo95), S.pct(r.hi95))

    fig = plt.figure(figsize=(13, 12.2))
    gs = GridSpec(2, 4, figure=fig, height_ratios=[1.15, 1], hspace=0.55, wspace=0.28, left=0.07, right=0.985, top=0.83,
                  bottom=0.17)  # fmt: skip
    top = gs[0, :].subgridspec(1, 2, width_ratios=[2.35, 1], wspace=0.5)
    ax = fig.add_subplot(top[0, 0])
    bx = fig.add_subplot(top[0, 1])
    waterfall(ax, v, va, LONG)
    ax.set_ylabel(XLAB_CHANGE)
    ax.set_title(f"(a) Ground PM2.5, mean over {n_c} NCAP cities ({n_single} with a single continuous station)", pad=24)
    h = v["h4"]
    ax.text(0.0, 1.015, f"Reported fall minus corrected fall (H4): {h[0]:+.1f} pp (95% CI {h[1]:+.1f} to {h[2]:+.1f})",
            transform=ax.transAxes, ha="left", va="bottom", fontsize=9, color=S.INK_2)  # fmt: skip

    rows = [(f"All {n_c}, pooled", *rel, "D")]
    for u in picks:
        t = D["shrunken"].loc[u]
        rows.append((f"{nm(u)} (shrunken)", S.pct(t.post_mean), S.pct(t.post_lo95), S.pct(t.post_hi95), "o"))
    relative_rows(bx, rows, "Satellite PM2.5, listed unit minus\nits synthetic comparison (%)",
                  caveat="Not identified as an\neffect of NCAP: the registered\npre-trend test failed.")  # fmt: skip
    bx.axhline(len(rows) - 1.5, color=S.GRID, linewidth=1)
    bx.set_title("(b) Relative change against\ncomparison cities", pad=10)

    lo_all, hi_all = [], []
    vals = {u: (city_values(D["ch"], D["b"], u, pol, spec, "gam"), city_values(D["ch"], D["b"], u, pol, lg, "lgbm")) for u in picks}
    for a, b in vals.values():
        for vv in (a, b):
            run = 0.0
            for m in STEPS:
                x, lo, hi = vv[m]
                if m in ("reported", "corrected"):
                    lo_all.append(min(0, lo)), hi_all.append(max(0, hi))
                    run = x
                else:
                    run -= x
                    lo_all.append(run - (hi - x)), hi_all.append(run + (x - lo))
    ylim = (min(lo_all) - 4, max(hi_all) + 4)
    c_top = gs[1, 0].get_position(fig).y1 + 0.052  # the (c) heading sits above the city titles
    for k, u in enumerate(picks):
        cx = fig.add_subplot(gs[1, k])
        waterfall(cx, *vals[u], SHORT, value_labels=False)  # tick labels carry each step's value
        cx.set_ylim(*ylim)
        cx.tick_params(axis="x", labelrotation=90, labelsize=8.5)
        row = D["ch"][(D["ch"].spec == spec) & (D["ch"].pollutant == pol) & (D["ch"].unit_id == u)].iloc[0]
        cx.set_title(f"{nm(u)}\n{int(row.n_all_base)}→{int(row.n_all_end)} stations, {int(row.n_panel)} continuous", fontsize=10, pad=6)
        if k == 0:
            cx.set_ylabel(XLAB_CHANGE)
        else:
            cx.tick_params(axis="y", labelleft=False)
    fig.text(0.07, c_top, f"(c) {N_ILLUSTRATIVE} illustrative cities, chosen by a station-count rule written after viewing "
             "results (DEC-191); every city in Fig. S3",
             fontsize=10.5, fontweight="bold", color=S.INK, ha="left")  # fmt: skip
    S.header(fig, "1", "How much of NCAP cities' reported fall in PM2.5 survives weather and network correction,\n"
             "and how did their satellite PM2.5 move relative to comparison cities?")  # fmt: skip
    fig.legend(handles=legend_handles(), loc="upper left", bbox_to_anchor=(0.0, 0.925), ncol=3, fontsize=9)
    S.source_note(fig, f"SCOPE: only the {n_c} NCAP cities with a PM2.5 station valid every year 2018–2025; not NCAP cities in general. "
                  "(a) and (c): CPCB ground stations inside each GHSL urban centre; weather from ERA5; 2018 → 2025. "
                  "(b): ACAG V5.GL.06 satellite PM2.5, population-weighted, each listed unit against a synthetic comparison "
                  "built from 923 non-NCAP centres, averaged over 2019 and 2021–2024; a different quantity and time base "
                  "from (a), so it is not subtracted from it. "
                  + S.NOT_IDENTIFIED)  # fmt: skip

    names4 = ", ".join(nm(u) for u in picks)
    big = largest_part(v)
    flips = sum(1 for u in picks if vals[u][0]["reported"][0] < 0 < vals[u][0]["corrected"][0])
    rel_rows = "; ".join(f"{lab.replace(" (shrunken)", "")} {est:+.1f}% ({lo:+.1f} to {hi:+.1f})" for lab, est, lo, hi, _ in rows[1:])
    cap = (f"(a) Mean change in annual ground PM2.5 from 2018 to 2025 over the {n_c} NCAP cities with a station valid every year "
           f"({n_single} of them with only one such station), decomposed in the proposal's order. Reported change (all stations "
           f"as reported, after the audit's cleaning) {v['reported'][0]:+.1f}%; removing the part the deweathering model does not "
           f"reproduce ({step_label('unmodelled', v['unmodelled'][0])}), modelled weather ({step_label('weather', v['weather'][0])}) "
           f"and the change in which stations exist ({step_label('composition', v['composition'][0])}) leaves a weather- and "
           f"composition-corrected change of "
           f"{v['corrected'][0]:+.1f}% (balanced panel, deweathered). Bars: GAM (primary); squares: LightGBM; intervals: 95% "
           f"cluster bootstrap over cities. H4 (reported fall minus corrected fall) = {h[0]:+.1f} pp (95% CI {h[1]:+.1f} to "
           f"{h[2]:+.1f}). (b) Satellite PM2.5 of the listed units relative to their synthetic comparison units after listing: "
           f"the {n_c} cities' units pooled (Phase 7, Layer A restricted) {rel[0]:+.1f}% (95% CI {rel[1]:+.1f} to {rel[2]:+.1f}), "
           f"and the shrunken city-level relative change of each illustrative city (Phase 8; 95% credible interval): {rel_rows}. "
           "This is a different quantity on a different time base from (a), so it is drawn on its own axis and not subtracted. "
           f"Each removed part is labelled with the step it makes, so its sign is the direction of its bar. "
           f"(c) The same decomposition for {names4}, chosen by a rule on station counts that was written after viewing the "
           f"per-city results (DEC-191); every city is in Figure S3. Intervals are station "
           "bootstraps where a city has more than one station in a stratum, otherwise none can be estimated and the "
           "GAM–LightGBM gap shows the model uncertainty. " + S.NOT_IDENTIFIED)  # fmt: skip
    alt = (f"Waterfall chart. Across {n_c} NCAP cities, the reported fall in ground PM2.5 from 2018 to 2025 averages "
           f"{v['reported'][0]:.1f}%; after removing modelled weather and the change in which monitors exist it is "
           f"{v['corrected'][0]:.1f}%, so about {100 * h[0] / -v['reported'][0]:.0f}% of the reported fall does not survive "
           f"correction. The largest part removed is {big[0]} ({big[1]:+.1f} pp removed). Four illustrative cities "
           f"({names4}) show the same steps; in {flips} of them the correction turns a reported fall into a rise. On a "
           f"separate axis, the same cities' "
           f"satellite PM2.5 rose {rel[0]:.1f}% relative to comparison units after listing. "
           "That relative change is not identified as an effect of NCAP.")  # fmt: skip
    return fig, S.Meta("1", "How much of NCAP cities' reported fall in PM2.5 survives weather and network correction, and how "
                       "did their satellite PM2.5 move relative to comparison cities?",
                       "How much of a city's reported improvement is real?", cap, alt)  # fmt: skip


# ------------------------------------------------------------------ the slide (Phase 10)


def fig_slide(D: dict) -> tuple[plt.Figure, S.Meta]:
    """Figure 1 panel (a) alone, 16:9, for a slide (DEC-210). The title is the takeaway line; the same scope
    and caveats as figure 1 sit in the note."""
    pol, spec, lg = "pm25", C.PRIMARY.label, C.Spec("lgbm").label
    n_c, n_single = scope(D["h4"], pol)
    v, va = summary_values(D["s"], pol, spec), summary_values(D["s"], pol, lg)
    h = v["h4"]
    share = 100 * h[0] / -v["reported"][0]
    take = (f"In {n_c} NCAP cities, about {share:.0f}% of the reported fall in PM2.5 since 2018 does not survive\n"
            "correction for weather and for changes in which monitors exist")
    fig = plt.figure(figsize=(13.33, 7.5))
    ax = fig.add_axes([0.08, 0.2, 0.9, 0.53])
    waterfall(ax, v, va, LONG)
    ax.tick_params(axis="x", labelsize=11)
    ax.set_ylabel(XLAB_CHANGE, fontsize=11)
    ax.set_title(f"Ground PM2.5, mean over {n_c} NCAP cities ({n_single} with a single continuous station): "
                 f"reported fall minus corrected fall = {h[0]:+.1f} pp (95% CI {h[1]:+.1f} to {h[2]:+.1f})",
                 loc="left", fontsize=11, pad=10)  # fmt: skip
    fig.suptitle(take, x=0.01, y=0.975, ha="left", va="top", fontsize=17, fontweight="bold", color=S.INK)
    fig.legend(handles=legend_handles(), loc="upper left", bbox_to_anchor=(0.01, 0.875), ncol=3, fontsize=9.5)
    S.source_note(fig, f"SCOPE: only the {n_c} NCAP cities with a PM2.5 station valid every year 2018–2025; not NCAP cities in "
                  "general. CPCB ground stations inside each GHSL urban centre (via the Vonter/india-cpcb-aqi mirror, ODbL); weather "
                  "from ERA5 (Copernicus). Ground data only; " + S.NOT_IDENTIFIED, y=0.045)  # fmt: skip
    big = largest_part(v)
    cap = (f"Slide version of Figure 1, panel (a). Mean change in annual ground PM2.5 from 2018 to 2025 over the {n_c} NCAP cities "
           f"with a station valid every year ({n_single} of them with only one such station): reported {v['reported'][0]:+.1f}%, "
           f"corrected {v['corrected'][0]:+.1f}%; H4 = {h[0]:+.1f} pp (95% CI {h[1]:+.1f} to {h[2]:+.1f}). Bars: GAM (primary); "
           "squares: LightGBM; intervals: 95% cluster bootstrap over cities. " + S.NOT_IDENTIFIED)  # fmt: skip
    alt = (f"Waterfall chart. Across {n_c} NCAP cities, the reported fall in ground PM2.5 from 2018 to 2025 averages "
           f"{v['reported'][0]:.1f}%; after removing modelled weather and the change in which monitors exist it is "
           f"{v['corrected'][0]:.1f}%. The largest part removed is {big[0]} ({big[1]:+.1f} pp removed). Not an effect of NCAP.")  # fmt: skip
    return fig, S.Meta("1 (slide)", take.replace("\n", " "), "How much of a city's reported improvement is real?", cap, alt)


# ------------------------------------------------------------------ S4: PM10 summary


def fig_pm10(D: dict) -> tuple[plt.Figure, S.Meta]:
    pol, spec, lg = "pm10", C.PRIMARY.label, C.Spec("lgbm").label
    n_c, n_single = scope(D["h4"], pol)
    v, va = summary_values(D["s"], pol, spec), summary_values(D["s"], pol, lg)
    d = D["did_pm10"]
    did = (S.pct(d.est), S.pct(d.lo95), S.pct(d.hi95))
    fig = plt.figure(figsize=(12, 5.6))
    gs = GridSpec(1, 4, figure=fig, wspace=0.35, left=0.08, right=0.985, top=0.72, bottom=0.2)
    ax, bx = fig.add_subplot(gs[0, :3]), fig.add_subplot(gs[0, 3])
    waterfall(ax, v, va, LONG)
    ax.set_ylabel(XLAB_CHANGE)
    ax.set_title(f"(a) Ground PM10, mean over {n_c} NCAP cities ({n_single} with a single continuous station)", pad=10)
    h = v["h4"]
    ax.text(0.99, 0.03, f"Reported fall minus corrected fall (H4):\n{h[0]:+.1f} pp (95% CI {h[1]:+.1f} to {h[2]:+.1f})",
            transform=ax.transAxes, ha="right", va="bottom", fontsize=9, color=S.INK_2)  # fmt: skip
    relative_rows(bx, [("Ground DiD\n(Layer B,\nsecondary)", *did, "D")], "Ground PM10, listed cities minus\ncontrol cities (%)",
                  caveat="Secondary, one pre-year.\nNot an effect of NCAP.")
    bx.set_title("(b) Relative change against\ncontrol cities", pad=10)
    S.header(fig, "S4", "How much of NCAP cities' reported fall in PM10 survives weather and network correction?")
    fig.legend(handles=legend_handles(), loc="upper left", bbox_to_anchor=(0.0, 0.92), ncol=3, fontsize=9)
    S.source_note(fig, f"SCOPE: only the {n_c} NCAP cities with a PM10 station valid every year 2018–2025; not NCAP cities in general. "
                  "(b): ground difference-in-differences against a handful of control-pool cities, one pre-year (2018): "
                  "secondary, parallel trends untestable. " + S.NOT_IDENTIFIED, y=0.02)  # fmt: skip
    cap = (f"(a) Mean change in annual ground PM10 from 2018 to 2025 over the {n_c} NCAP cities with a PM10 station valid every "
           f"year ({n_single} with one such station): reported {v['reported'][0]:+.1f}%; unmodelled change "
           f"{step_label('unmodelled', v['unmodelled'][0])}, modelled weather {step_label('weather', v['weather'][0])}, network "
           f"composition {step_label('composition', v['composition'][0])}; corrected "
           f"{v['corrected'][0]:+.1f}%. H4 = {h[0]:+.1f} pp (95% CI {h[1]:+.1f} to {h[2]:+.1f}). GAM bars, LightGBM squares, 95% "
           f"cluster-bootstrap intervals. (b) Ground difference-in-differences against control-pool cities (Layer B, secondary, one "
           f"pre-year): {did[0]:+.1f}% (95% CI {did[1]:+.1f} to {did[2]:+.1f}). There is no satellite PM10. " + S.NOT_IDENTIFIED)  # fmt: skip
    alt = (f"Waterfall chart for PM10 across {n_c} NCAP cities: reported change {v['reported'][0]:.1f}%, corrected change "
           f"{v['corrected'][0]:.1f}%; the largest part removed is {largest_part(v)[0]} ({largest_part(v)[1]:+.1f} pp removed). A "
           f"separate axis "
           f"shows the secondary ground comparison with control cities, {did[0]:+.1f}% with a wide interval "
           f"({did[1]:+.1f} to {did[2]:+.1f}). Not identified as an effect of NCAP.")  # fmt: skip
    return fig, S.Meta("S4", "How much of NCAP cities' reported fall in PM10 survives weather and network correction?",
                       "How much of a city's reported PM10 improvement is real?", cap, alt)  # fmt: skip


# ------------------------------------------------------------------ S3: every city


def city_rows(ax: plt.Axes, D: dict, pol: str) -> int:
    ch, b, nm = D["ch"], D["b"], D["names"]
    g = ch[(ch.spec == C.PRIMARY.label) & (ch.pollutant == pol)].copy()
    lg = ch[(ch.spec == C.Spec("lgbm").label) & (ch.pollutant == pol)].set_index("unit_id")
    bb = b[(b.family == "gam") & (b.pollutant == pol)].set_index("unit_id")
    g["name"] = g.unit_id.map(nm).fillna(g.unit_id)
    g = g.sort_values("name").reset_index(drop=True)  # alphabetical: never ranked (DEC-192)
    for i, r in g.iterrows():
        a0 = r.reported - r.unmodelled
        a1 = a0 - r.weather
        ax.barh(i, r.reported, height=0.22, color=C_TOTAL, linewidth=0, zorder=2)
        ax.barh(i, a0 - r.reported, left=r.reported, height=0.55, color=C_UNMOD, linewidth=0, zorder=2)
        ax.barh(i, a1 - a0, left=a0, height=0.55, color=C_WEATHER, linewidth=0, zorder=2)
        ax.barh(i, r.corrected - a1, left=a1, height=0.55, color=C_COMP, linewidth=0, zorder=2)
        lo, hi = bb.loc[r.unit_id, ["corrected_lo", "corrected_hi"]]
        if hi > lo:
            ax.plot([lo, hi], [i, i], color=S.INK, linewidth=1.1, zorder=3)
        ax.plot(r.corrected, i, marker="D", markersize=6, color=S.INK, linestyle="none", zorder=4)
        ax.plot(lg.loc[r.unit_id, "corrected"], i, marker="s", markersize=6, markerfacecolor=S.SURFACE,
                markeredgecolor=S.INK, linestyle="none", zorder=4)  # fmt: skip
    ax.set_yticks(range(len(g)), [f"{r['name']}  ({r.n_all_base}→{r.n_all_end} st., {r.n_panel} cont.)" for _, r in g.iterrows()],
                  fontsize=9)  # fmt: skip
    xs = np.concatenate([g.reported, g.reported - g.unmodelled, g.reported - g.unmodelled - g.weather, g.corrected,
                         lg.loc[g.unit_id, "corrected"], [0]])  # fmt: skip
    pad = 0.05 * (xs.max() - xs.min())
    ax.set_xlim(xs.min() - pad, xs.max() + pad)
    ax.invert_yaxis()
    ax.axvline(0, color=S.INK_2, linewidth=0.8)
    ax.set_xlabel("Change in annual mean, 2018 → 2025 (% of the 2018 value)")
    ax.grid(axis="y", visible=False)
    return len(g)


def fig_cities(D: dict) -> tuple[plt.Figure, S.Meta]:
    n = [len(D["ch"][(D["ch"].spec == C.PRIMARY.label) & (D["ch"].pollutant == p)]) for p in ("pm25", "pm10")]
    fig, axes = plt.subplots(2, 1, figsize=(10, 0.36 * sum(n) + 3.6), gridspec_kw={"height_ratios": n, "hspace": 0.32})
    for ax, pol in zip(axes, ("pm25", "pm10"), strict=True):
        k = city_rows(ax, D, pol)
        n_c, n_single = scope(D["h4"], pol)
        ax.set_title(f"({'a' if pol == 'pm25' else 'b'}) {POL[pol]}: {k} NCAP cities ({n_single} with a single continuous station)")
    handles = [Patch(color=C_TOTAL, label="Reported change (thin bar, from 0)"), Patch(color=C_UNMOD, label="Unmodelled change removed"),
               Patch(color=C_WEATHER, label="Modelled weather removed"), Patch(color=C_COMP, label="Network composition removed"),
               Line2D([], [], marker="D", color=S.INK, linestyle="-", linewidth=1, markersize=6,
                      label="Corrected change, GAM (line: 95% station bootstrap, if > 1 station)"),
               Line2D([], [], marker="s", markerfacecolor=S.SURFACE, markeredgecolor=S.INK, linestyle="none", label="Corrected change, LightGBM")]  # fmt: skip
    fig.subplots_adjust(top=1 - 1.45 / fig.get_figheight(), left=0.3, right=0.98, bottom=0.6 / fig.get_figheight())
    S.header(fig, "S3", "City by city: reported change, the parts removed, and the corrected change (alphabetical)")
    fig.legend(handles=handles, loc="upper left", bbox_to_anchor=(0.0, 1 - 0.45 / fig.get_figheight()), ncol=2, fontsize=9)
    S.source_note(fig, "SCOPE: NCAP cities (GHSL urban centres) with at least one station valid every year 2018–2025; not NCAP cities "
                  "in general. 'a→b st.' = stations valid in 2018 and 2025; 'cont.' = stations valid every year. Each row starts at the "
                  "thin bar's end and removes each part in turn; the diamond is what is left. Ground data only; not an effect of NCAP.")  # fmt: skip
    c25 = D["ch"][(D["ch"].spec == C.PRIMARY.label) & (D["ch"].pollutant == "pm25")]
    flips = int(((c25.reported < 0) & (c25.corrected > 0)).sum())
    cap = ("Every NCAP city in H4's scope, listed alphabetically (never ranked): (a) PM2.5, (b) PM10. Each row shows the reported "
           "change in the annual mean 2018 → 2025 (thin bar), then removes the unmodelled change, modelled weather and network "
           "composition; the diamond is the weather- and composition-corrected change (GAM; line: 95% station bootstrap where the "
           "city has more than one station), the square the same with LightGBM. Most cities have one continuous station, so their "
           "corrected change is one monitor's record. Ground data only; nothing here is an effect of NCAP.")  # fmt: skip
    alt = (f"Two horizontal bar charts listing {n[0]} PM2.5 and {n[1]} PM10 NCAP cities alphabetically. For each city, bars show the "
           f"reported 2018-to-2025 change and the parts removed for unmodelled change, weather and network composition, ending at "
           f"the corrected change. In {flips} PM2.5 cities a reported fall becomes a corrected rise. Not effects of NCAP.")  # fmt: skip
    return fig, S.Meta("S3", "City by city: reported change, the parts removed, and the corrected change",
                       "How much of each city's reported improvement is real?", cap, alt)  # fmt: skip


def main() -> None:
    from src.common.gate import require_gate

    require_gate("figure 1 and S4 (Phase 7 and Phase 8 outputs)")
    S.apply()
    D = load()
    if "--slide" in sys.argv[1:]:
        f, m = fig_slide(D)
        S.save(f, "fig1_slide", m)
        print("figure 1 slide written")
        return
    f, m = fig_main(D)
    S.save(f, "fig1_decomposition", m)
    f, m = fig_cities(D)
    S.save(f, "figS3_decomposition_cities", m)
    f, m = fig_pm10(D)
    S.save(f, "figS4_decomposition_pm10", m)
    print("figure 1, S3 and S4 written")


if __name__ == "__main__":
    main()

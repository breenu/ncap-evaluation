"""Figure 7: PM10 vs PM2.5 on the ground layer (proposal figure plan: "PM10 vs PM2.5 effect comparison";
question: is the mechanism consistent with dust control?). H3, DEC-165/167. Phase 8.

(a) Layer B estimates for PM2.5 and PM10 on the cities that hold both, for each registered specification
(raw = all stations raw; deweathered = all stations deweathered; balanced panel = Layer B primary) and both
estimators (ITS, DiD), with 95% cluster-bootstrap CIs; Layer A restricted (satellite PM2.5) for reference.
(b) the estimate for log(PM2.5/PM10) on co-located stations (condition (i)).
Layer B is secondary with one pre-year; H1 is not identified, so none of these is an effect of NCAP.

    python -m src.viz.fig7_mechanism
"""

import json

import numpy as np
import pandas as pd
from matplotlib import pyplot as plt
from matplotlib.lines import Line2D

from src.causal import layer_a as A
from src.hierarchical.city_estimates import OUT
from src.viz import style as S

C25, C10, CR = S.CATEGORICAL[0], S.CATEGORICAL[1], S.INK_2
SPEC_ORDER = ["raw", "deweathered", "balanced panel"]


def pct(x):
    return 100 * np.expm1(np.asarray(x, float))


def main() -> None:
    S.apply()
    b = pd.read_csv(OUT / "h3_betas.csv")
    r = pd.read_csv(OUT / "h3_ratio.csv")
    h3 = json.loads((OUT / "h3.json").read_text())
    tri = pd.read_csv(A.OUT / "triangulation.csv").iloc[0]
    fig, (ax, bx) = plt.subplots(1, 2, figsize=(13, 6.4), gridspec_kw={"width_ratios": [1.5, 1]})
    rows = [(e, s) for e in ("ITS", "DiD") for s in SPEC_ORDER]
    labels = []
    for k, (est, spec) in enumerate(rows):
        yk = len(rows) - k
        for pol, col, mk, off in (("pm25", C25, "o", 0.15), ("pm10", C10, "s", -0.15)):
            x = b[(b.estimator == est) & (b.spec == spec) & (b.pollutant == pol)].iloc[0]
            ax.hlines(yk + off, pct(x.lo95), pct(x.hi95), color=col, linewidth=1.6)
            ax.scatter(pct(x.est), yk + off, color=col, marker=mk, s=36, edgecolors=S.SURFACE, linewidths=0.8, zorder=3)
        n = int(b[(b.estimator == est) & (b.spec == spec)].cities.max())
        labels.append((yk, f"{est}, {spec} ({n} cities)"))
    ax.hlines(0, pct(tri.a_lo95), pct(tri.a_hi95), color=CR, linewidth=1.6)
    ax.scatter(pct(tri.a_est), 0, color=CR, marker="D", s=30, zorder=3)
    labels.append((0, f"Layer A restricted, satellite PM2.5 ({int(tri.a_units)} units)"))
    ax.set_yticks([p for p, _ in labels], [t for _, t in labels], fontsize=9)
    ax.axvline(0, color=S.INK_2, linewidth=0.8)
    ax.set_xlabel("Estimate (%; NCAP city after listing vs before, or vs control cities)")
    ax.set_title("(a) PM2.5 and PM10 on the same cities")
    ax.legend(handles=[Line2D([], [], color=C25, marker="o", label="Ground PM2.5"), Line2D([], [], color=C10, marker="s", label="Ground PM10"),
                       Line2D([], [], color=CR, marker="D", label="Satellite PM2.5 (reference)")],
              loc="upper center", bbox_to_anchor=(0.5, -0.16), ncol=3, fontsize=9)  # fmt: skip
    rr = [(s, e) for s in ("deweathered", "raw") for e in ("ITS", "DiD")]
    for k, (s, e) in enumerate(rr):
        x = r[(r.series == s) & (r.estimator == e)].iloc[0]
        yk = len(rr) - k
        dw = s == "deweathered"
        bx.hlines(yk, pct(x.lo95), pct(x.hi95), color=C25 if dw else S.INK_2, linewidth=1.6)
        bx.scatter(pct(x.est), yk, color=C25 if dw else S.SURFACE, edgecolors=C25 if dw else S.INK_2, marker="o", s=34,
                   linewidths=1.2, zorder=3)  # fmt: skip
    n_ratio = int(r.cities.max())
    bx.set_yticks(range(len(rr), 0, -1), [f"{e}, {s}" for s, e in rr], fontsize=9)
    bx.axvline(0, color=S.INK_2, linewidth=0.8)
    bx.set_xlabel("Change in the PM2.5/PM10 ratio after listing (%)")
    bx.set_title(f"(b) Ratio, co-located stations ({n_ratio} cities)")
    fig.tight_layout(rect=(0, 0.02, 1, 0.88))
    S.header(fig, "7", "Is the ground PM10/PM2.5 pattern consistent with dust control?")
    fig.text(0.0, 0.925, f"H3: {h3['verdict']}. Layer B (ground): secondary, one pre-year, mostly single-station cities. "
             "Not effects of NCAP.", fontsize=10, color=S.INK, ha="left", va="top")  # fmt: skip
    S.source_note(fig, "CPCB stations inside each urban centre, 2018 baseline, 2020 excluded; ITS = mean after listing minus "
                  "before; DiD = against control-pool stations; 95% CIs: cluster bootstrap over cities (1,000). Dust control "
                  "predicts PM10 falling more than PM2.5 and the ratio rising.", y=-0.02)  # fmt: skip
    ri = r[(r.series == "deweathered") & (r.estimator == "ITS")].iloc[0]
    rd = r[(r.series == "deweathered") & (r.estimator == "DiD")].iloc[0]
    n_cities = int(b.cities.max())
    cap = (f"(a) Ground estimates for PM2.5 (circles) and PM10 (squares) on the {n_cities} NCAP cities that have both, for the "
           "three registered specifications (all stations raw, all stations deweathered, balanced panel) and both Layer B "
           "estimators: interrupted time series (after listing minus before) and difference-in-differences against "
           f"control-pool stations; satellite PM2.5 for the {int(tri.a_units)} Layer A units with a ground panel is shown for "
           f"reference ({pct(tri.a_est):+.1f}%). (b) The change in the PM2.5/PM10 ratio on co-located stations: deweathered ITS "
           f"{pct(ri.est):+.1f}% (95% CI {pct(ri.lo95):+.1f} to {pct(ri.hi95):+.1f}), deweathered DiD {pct(rd.est):+.1f}% "
           f"({pct(rd.lo95):+.1f} to {pct(rd.hi95):+.1f}); raw values as hollow markers. Dust control predicts PM10 falling "
           f"more than PM2.5 and the ratio rising. H3 is {h3['verdict']} by its registered rule: condition (iii) already fails "
           "(the Layer A vs ITS pair is 'conflict'), and (i) and (ii) fail too. Ground results are secondary, with one "
           "pre-year; not effects of NCAP.")  # fmt: skip
    alt = (f"Dot-and-interval charts comparing ground PM2.5 and PM10 changes in {n_cities} NCAP cities across six "
           f"estimator-specification pairs, and the change in their ratio. The intervals are wide and mostly include 0; the "
           f"ratio rises by {pct(ri.est):+.1f}% in the before-after comparison, with an interval reaching "
           f"{pct(ri.lo95):+.1f}%, and by {pct(rd.est):+.1f}% against control cities. H3 is {h3['verdict']}. Not effects of NCAP.")  # fmt: skip
    S.save(fig, "fig7_mechanism", S.Meta("7", "Is the ground PM10/PM2.5 pattern consistent with dust control?",
                                         "Is the mechanism consistent with dust control?", cap, alt))  # fmt: skip


if __name__ == "__main__":
    main()

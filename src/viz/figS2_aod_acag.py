"""Supplementary figure S2 (DEC-195): does a satellite signal that no ground monitor calibrates show the same
relative change as ACAG PM2.5? Every Phase 8b specification (raw MAIAC AOD) beside ACAG PM2.5 estimated on
exactly the same units, and the monitor-gain split on the primary, with the pre-specified readings (DEC-180)
and DEC-188's exploratory label on the not-gained row. Read from data/processed/causal/maiac/ (no estimate is
made here).

AOD is a column measure, not surface PM2.5: direction only. H1 is not identified by this design (DEC-151):
every row is a relative change of listed units against their synthetic comparison, not an effect of NCAP.

    python -m src.viz.figS2_aod_acag      (gated: reads Phase 8b outputs)
"""

import json

from matplotlib import pyplot as plt
from matplotlib.lines import Line2D

from src.causal import layer_a as A
from src.viz import style as S

MAIAC = A.OUT / "maiac"
C_ACAG, C_AOD = S.CATEGORICAL[0], S.CATEGORICAL[1]
SPECS = [("aod_primary", "Primary (population-weighted,\nbest-quality QA, all valid months)"),
         ("aod_nonmonsoon", "Non-monsoon months only"),
         ("aod_area", "Area-weighted"),
         ("aod_relaxed", "Relaxed QA filter"),
         ("aod_restricted", "Units with a ground panel")]  # fmt: skip


def rows(r: dict, ex: dict) -> list[dict]:
    out = []
    for sid, lab in SPECS:
        s = r["specs"][sid]
        out.append({"label": f"{lab}\n({s['n_treated']} listed / {s['n_controls']} comparison)", "acag": s["acag"], "aod": s["aod"],
                    "reading": f"Q1: {s['q1']['label']}", "group": "spec"})  # fmt: skip
    p = r["specs"]["aod_primary"]
    out.append({"label": f"Gained a monitor 2019–2024\n({p['n_gained']} listed units)", "acag": p["acag_gained"], "aod": p["gained"],
                "reading": "", "group": "split"})  # fmt: skip
    ng = ex["groups"]["notgained"]
    out.append({"label": f"Gained no monitor\n({p['n_notgained']} listed units)", "acag": p["acag_notgained"], "aod": p["notgained"],
                "reading": f"exploratory (DEC-188): {ng['q1']['label']}", "group": "split"})  # fmt: skip
    out.append({"label": "Difference,\ngained − not gained", "acag": p["acag_diff"], "aod": p["diff"],
                "reading": f"Q2: {p['q2']['label']}", "group": "split"})  # fmt: skip
    return out


def figure(r: dict, ex: dict) -> tuple[plt.Figure, S.Meta]:
    S.apply()
    R = rows(r, ex)
    fig, ax = plt.subplots(figsize=(13, 8.6))
    n = len(R)
    ys = [n - 1 - k + (0.6 if R[k]["group"] == "spec" else 0) for k in range(n)]  # a gap between the two blocks
    for y, row in zip(ys, R, strict=True):
        for key, col, mk, off, face in (("acag", C_ACAG, "o", 0.16, C_ACAG), ("aod", C_AOD, "s", -0.16, S.SURFACE)):
            e, lo, hi = S.pct(row[key])
            ax.errorbar(e, y + off, xerr=[[e - lo], [hi - e]], fmt=mk, color=col, markerfacecolor=face, markeredgewidth=1.4,
                        markersize=7, elinewidth=1.6, capsize=3)  # fmt: skip
        if row["reading"]:
            ax.text(1.01, y, row["reading"], transform=ax.get_yaxis_transform(), ha="left", va="center", fontsize=9, color=S.INK)
    ax.set_yticks(ys, [row["label"] for row in R], fontsize=9)
    ax.axvline(0, color=S.INK_2, linewidth=0.8)
    split_top = ys[len(SPECS)] + 0.8
    ax.axhline(split_top, color=S.GRID, linewidth=1.2)
    ax.text(0.01, ys[0] + 0.5, "Every specification", transform=ax.get_yaxis_transform(), fontsize=9.5, fontweight="bold",
            color=S.INK_2, va="bottom")  # fmt: skip
    ax.text(0.01, split_top - 0.08, "Monitor-gain split (primary specification)", transform=ax.get_yaxis_transform(), fontsize=9.5,
            fontweight="bold", color=S.INK_2, va="top")  # fmt: skip
    ax.set_ylim(ys[-1] - 0.6, ys[0] + 0.95)
    ax.set_xlabel("Relative change of listed units against their synthetic comparison (%)\n"
                  "ACAG: PM2.5. MAIAC: aerosol optical depth, not PM2.5 (read its direction only)")  # fmt: skip
    ax.grid(axis="y", visible=False)
    ax.legend(handles=[Line2D([], [], color=C_ACAG, marker="o", label="ACAG V5.GL.06 PM2.5 (calibrated to ground monitors), 95% CI"),
                       Line2D([], [], color=C_AOD, marker="s", markerfacecolor=S.SURFACE, label="Raw MAIAC AOD (no ground monitor), 95% CI")],
              loc="upper center", bbox_to_anchor=(0.5, -0.13), ncol=2)  # fmt: skip
    fig.subplots_adjust(left=0.25, right=0.66, top=0.86, bottom=0.17)
    S.header(fig, "S2", "Does a satellite signal that no ground monitor calibrates show the same relative change?\n"
             "ACAG PM2.5 against raw MAIAC aerosol optical depth, on the same units")  # fmt: skip
    S.source_note(fig, "Phase 8b: MODIS MAIAC MCD19A2 C6.1 AOD (0.55 µm, 1 km; NASA LP DAAC), population-weighted over the same GHSL "
                  "polygons, reduced on Google Earth Engine; SDID with 500 joint-placebo replications, ACAG estimated on exactly "
                  "the same units. Readings pre-specified in DEC-180; the not-gained row's reading is exploratory (DEC-188). "
                  + S.NOT_IDENTIFIED, y=0.03)  # fmt: skip

    p = r["specs"]["aod_primary"]
    f = lambda v: f"{S.pct(v[0]):+.1f}% ({S.pct(v[1]):+.1f} to {S.pct(v[2]):+.1f})"  # noqa: E731
    above = sum(1 for sid, _ in SPECS if r["specs"][sid]["aod"][1] > 0)
    below = sum(1 for sid, _ in SPECS if r["specs"][sid]["aod"][0] < r["specs"][sid]["acag"][0])
    cap = (f"Relative change of NCAP-listed units against their synthetic comparison in raw MAIAC aerosol optical depth "
           f"(squares) and in ACAG PM2.5 estimated on exactly the same units (circles), with 95% CIs. Primary: AOD {f(p['aod'])}, "
           f"ACAG {f(p['acag'])}, read as \"{p['q1']['label']}\". Across the {len(SPECS)} specifications, AOD is below ACAG in "
           f"{below} and its interval lies entirely above 0 in {above} (non-monsoon months). Monitor-gain split: AOD gained "
           f"{f(p['gained'])}, not gained {f(p['notgained'])}, difference {f(p['diff'])}; ACAG on the same units: difference "
           f"{f(p['acag_diff'])}, read as \"{p['q2']['label']}\". Exploratory (DEC-188): ACAG and AOD diverge most in the units "
           f"that gained no monitor (ACAG {f(p['acag_notgained'])}, AOD {f(p['notgained'])}), where calibration leakage cannot "
           "act, which weakens Q2 as evidence for leakage specifically. AOD is a column measure, not surface PM2.5, so only its "
           "direction is read. These are relative changes, not effects of NCAP: H1 is not identified by this design.")  # fmt: skip
    alt = (f"Paired dot-and-interval chart. In every one of the {len(SPECS)} specifications the raw-AOD relative change is below "
           f"the ACAG PM2.5 one on the same units ({below} of {len(SPECS)}); the primary AOD estimate is {S.pct(p['aod'][0]):+.1f}% "
           f"against ACAG's {S.pct(p['acag'][0]):+.1f}%. ACAG's smaller rise in units that gained monitors is absent from AOD, "
           "and the two signals differ most in units that gained no monitor. AOD is not PM2.5; not effects of NCAP.")  # fmt: skip
    if below != len(SPECS):
        alt = alt.replace(f"In every one of the {len(SPECS)} specifications the", "The")
    return fig, S.Meta("S2", "Does a satellite signal that no ground monitor calibrates show the same relative change as ACAG PM2.5?",
                       "Does the relative rise appear in raw AOD, and the monitor-gain gap?", cap, alt)  # fmt: skip


def main() -> None:
    from src.common.gate import require_gate

    require_gate("figure S2 (Phase 8b outputs)")
    r = json.loads((MAIAC / "results.json").read_text(encoding="utf-8"))
    ex = json.loads((MAIAC / "exploratory_notgained.json").read_text(encoding="utf-8"))
    f, m = figure(r, ex)
    S.save(f, "figS2_aod_acag", m)


if __name__ == "__main__":
    main()

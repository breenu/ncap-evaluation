"""Figure 5: small-multiple maps of the shrunken city-level relative changes (proposal figure plan:
"small-multiple maps of city-level effect estimates (posterior means)"; DEC-167). Phase 8.

H1 is not identified (DEC-151): these are city-level relative changes in satellite PM2.5 (each NCAP unit
against its own synthetic comparison, after listing), shrunken by the hierarchical model (DEC-163), not
effects of NCAP. Panels: (a) posterior mean, % (diverging blue-grey-red, centred at 0); (b) width of the
95% credible interval, percentage points; (c) posterior probability that the relative change is below 0.

    python -m src.viz.fig5_city_map
"""

import geopandas as gpd
import numpy as np
import pandas as pd
from matplotlib import pyplot as plt
from matplotlib.colors import TwoSlopeNorm

from src.common.paths import INTERIM, raw_dir
from src.hierarchical.city_estimates import OUT
from src.viz import style as S

CLASSES = [("hi", "^", "95% CrI entirely above 0 (rose)"), ("lo", "v", "95% CrI entirely below 0 (fell)"),
           ("span", "o", "95% CrI spans 0")]  # fmt: skip


def main() -> None:
    from matplotlib.lines import Line2D

    S.apply()
    c = pd.read_csv(OUT / "city_shrunken.csv")
    c = c[c.version == "primary"].copy()
    units = gpd.read_file(INTERIM / "sat_units.gpkg")[["unit_id", "geometry"]]
    pts = units.merge(c, on="unit_id")
    if len(pts) != len(c):
        raise ValueError("a unit has no geometry")
    pts["geometry"] = pts.geometry.representative_point()
    pts["mean_pct"] = S.pct(pts.post_mean)
    pts["width_pp"] = S.pct(pts.post_hi95) - S.pct(pts.post_lo95)
    pts["cls"] = np.where(pts.post_lo95 > 0, "hi", np.where(pts.post_hi95 < 0, "lo", "span"))
    india = gpd.read_file(raw_dir("boundaries") / "datameet@b3fbbde" / "Country" / "india-composite.geojson")
    states = gpd.read_file(raw_dir("boundaries") / "datameet@b3fbbde" / "States" / "Admin2.shp")

    lim = float(np.ceil(np.abs(pts.mean_pct).max()))
    panels = [
        ("mean_pct", "(a) Shrunken relative change\n(posterior mean, %)", S.DIVERGING, TwoSlopeNorm(0, -lim, lim),
         "% (listed unit minus its synthetic comparison)"),
        ("width_pp", "(b) Width of its 95% credible\ninterval (percentage points)", S.SEQ, None, "percentage points"),
        ("p_lt0", "(c) Probability that the relative\nchange is below 0", S.SEQ, plt.Normalize(0, 1), "posterior probability"),
    ]  # fmt: skip
    fig, axes = plt.subplots(1, 3, figsize=(14, 6.4))
    for k, (ax, (col, title, cmap, norm, unit)) in enumerate(zip(axes, panels, strict=True)):
        india.plot(ax=ax, color=S.LAND, edgecolor=S.NEUTRAL, linewidth=0.5)
        states.boundary.plot(ax=ax, color=S.GRID, linewidth=0.35)
        groups = CLASSES if k == 0 else [("all", "o", "")]
        for cls, mk, _ in groups:  # (a): marker shape carries the CrI class, so colour is not the only carrier
            g = pts if cls == "all" else pts[pts.cls == cls]
            sc = ax.scatter(g.geometry.x, g.geometry.y, c=g[col], cmap=cmap, norm=norm if norm is not None else
                            plt.Normalize(pts[col].min(), pts[col].max()), s=46 if mk != "o" else 36, marker=mk,
                            edgecolors=S.INK_2, linewidths=0.6, zorder=3)  # fmt: skip
        ax.set_axis_off()
        ax.set_title(title, fontsize=10.5)
        cb = fig.colorbar(sc, ax=ax, orientation="horizontal", fraction=0.045, pad=0.02)
        cb.set_label(unit, fontsize=9, color=S.INK_2)
        cb.outline.set_visible(False)
    counts = pts.cls.value_counts()
    axes[0].legend(handles=[Line2D([], [], marker=mk, color=S.INK_2, markerfacecolor="none", linestyle="none", markersize=7,
                                   label=f"{lab} ({int(counts.get(cls, 0))})") for cls, mk, lab in CLASSES],
                   loc="upper right", bbox_to_anchor=(1.08, 1.0), fontsize=8.5)  # fmt: skip
    n_lo, n_hi, n = int(counts.get("lo", 0)), int(counts.get("hi", 0)), len(c)
    S.header(fig, "5", "Where did satellite PM2.5 rise or fall relative to comparison units after listing?")
    fig.text(0.0, 0.925, "City-level relative changes, shrunken. Not identified as effects of NCAP: the registered pre-trend "
             "test failed.", fontsize=10, color=S.INK, ha="left", va="top")  # fmt: skip
    S.source_note(fig, f"Each point is one of the {n} NCAP urban centres against its own synthetic comparison from 923 non-NCAP "
                  "centres (ACAG V5.GL.06, population-weighted, 2010–2024 without 2020), pooled in a Bayesian measurement-error "
                  "model (DEC-162/163). Sources: ACAG; GHSL UCDB R2024A; DataMeet boundaries.")  # fmt: skip
    co = pd.read_csv(OUT / "pool_coefs.csv")
    avg = co[(co.version == "primary") & (co.param == "average city-level relative change")].iloc[0]
    cap = (f"Maps of the {n} NCAP urban centres. (a) Each centre's shrunken city-level relative change in satellite PM2.5 after "
           f"listing (posterior mean, %; blue = fell relative to its synthetic comparison, red = rose); marker shape gives "
           f"its 95% credible interval: entirely above 0 for {n_hi}, entirely below 0 for {n_lo}, spanning 0 for {n - n_hi - n_lo}. "
           f"(b) The width of that interval ({pts.width_pp.min():.1f}–{pts.width_pp.max():.1f} pp). (c) The posterior probability "
           f"that the relative change is below 0. The average city-level relative change is {S.pct(avg['mean']):+.1f}% (95% CrI "
           f"{S.pct(avg['lo95']):+.1f} to {S.pct(avg['hi95']):+.1f}). Each unit is estimated against its own synthetic comparison "
           "(ACAG V5.GL.06, log population-weighted, 2010–2024 without 2020) and pooled with the five registered moderators. "
           "No city is ranked or named. These are relative changes, not effects of NCAP: H1 is not identified by this design.")  # fmt: skip
    alt = (f"Three maps of India with one marker per NCAP city. {int((pts.post_mean > 0).sum())} of {n} posterior means are "
           f"above 0 (red). Satellite PM2.5 in {n_hi} cities rose relative to comparison units after listing with a "
           f"credible interval above 0, and in {n_lo} it fell "
           f"with an interval below 0; the rest are uncertain. Interval widths are {pts.width_pp.min():.0f}–"
           f"{pts.width_pp.max():.0f} percentage points. Not identified as effects of NCAP.")  # fmt: skip
    S.save(fig, "fig5_city_map", S.Meta("5", "Where did satellite PM2.5 rise or fall relative to comparison units after listing?",
                                        "Where did satellite PM2.5 rise or fall relative to comparison units?", cap, alt))  # fmt: skip


if __name__ == "__main__":
    main()

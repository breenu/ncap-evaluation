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
from matplotlib.colors import LinearSegmentedColormap, TwoSlopeNorm

from src.common.paths import INTERIM, raw_dir
from src.hierarchical.city_estimates import OUT
from src.viz import style as S

DIVERGING = LinearSegmentedColormap.from_list("blue_grey_red", ["#2a78d6", "#f0efec", "#e34948"])
SEQ = LinearSegmentedColormap.from_list("seq_blue", [S.SEQ_BLUE[1], S.SEQ_BLUE[12]])


def pct(x):
    return 100 * np.expm1(np.asarray(x, float))


def main() -> None:
    S.apply()
    c = pd.read_csv(OUT / "city_shrunken.csv")
    c = c[c.version == "primary"].copy()
    units = gpd.read_file(INTERIM / "sat_units.gpkg")[["unit_id", "geometry"]]
    pts = units.merge(c, on="unit_id")
    if len(pts) != len(c):
        raise ValueError("a unit has no geometry")
    pts["geometry"] = pts.geometry.representative_point()
    pts["mean_pct"] = pct(pts.post_mean)
    pts["width_pp"] = pct(pts.post_hi95) - pct(pts.post_lo95)
    india = gpd.read_file(raw_dir("boundaries") / "datameet@b3fbbde" / "Country" / "india-composite.geojson")
    states = gpd.read_file(raw_dir("boundaries") / "datameet@b3fbbde" / "States" / "Admin2.shp")

    lim = float(np.ceil(np.abs(pts.mean_pct).max()))
    panels = [
        ("mean_pct", "(a) Shrunken relative change\n(posterior mean, %)", DIVERGING, TwoSlopeNorm(0, -lim, lim), "%"),
        ("width_pp", "(b) Width of its 95% credible\ninterval (percentage points)", SEQ, None, "percentage points"),
        ("p_lt0", "(c) Probability that the relative\nchange is below 0", SEQ, plt.Normalize(0, 1), "probability"),
    ]  # fmt: skip
    fig, axes = plt.subplots(1, 3, figsize=(13, 5.6))
    for ax, (col, title, cmap, norm, unit) in zip(axes, panels, strict=True):
        india.plot(ax=ax, color="#f0efec", edgecolor=S.NEUTRAL, linewidth=0.5)
        states.boundary.plot(ax=ax, color=S.GRID, linewidth=0.35)
        sc = ax.scatter(pts.geometry.x, pts.geometry.y, c=pts[col], cmap=cmap, norm=norm, s=34,
                        edgecolors=S.INK_2, linewidths=0.5, zorder=3)  # fmt: skip
        ax.set_axis_off()
        ax.set_title(title, fontsize=9.5)
        cb = fig.colorbar(sc, ax=ax, orientation="horizontal", fraction=0.045, pad=0.02)
        cb.set_label(unit, fontsize=8, color=S.INK_2)
        cb.outline.set_visible(False)
    n_lo = int((c.post_hi95 < 0).sum())
    n_hi = int((c.post_lo95 > 0).sum())
    fig.suptitle("City-level relative change in satellite PM2.5 after NCAP listing, shrunken: NOT an effect of NCAP "
                 "(H1 not identified)", x=0.0, y=0.93, ha="left", fontsize=11, fontweight="bold", color=S.INK)  # fmt: skip
    S.source_note(fig, f"Each point is one of the {len(c)} NCAP urban centres: its own synthetic difference-in-differences against "
                  "923 non-NCAP centres (log population-weighted ACAG V5.GL.06, 2010-2024 without 2020), pooled in a Bayesian "
                  "measurement-error model with the five registered moderators (DEC-162/163). Blue = PM2.5 fell relative to its "
                  "synthetic comparison; red = it rose. The registered event-study pre-trend test failed, so none of this is "
                  f"attributable to NCAP. 95% credible interval entirely below 0: {n_lo} of {len(c)} units; entirely above 0: {n_hi}. "
                  "Sources: ACAG V5.GL.06; GHSL UCDB R2024A; DataMeet boundaries.")  # fmt: skip
    S.save(fig, "fig5_city_map")


if __name__ == "__main__":
    main()

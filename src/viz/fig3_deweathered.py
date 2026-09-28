"""Figure 3: raw vs deweathered monthly PM2.5 for six illustrative cities (proposal figure plan;
question: how much does weather move annual numbers?).

City choice is a rule, not a visual pick (DEC-106): in each region, the urban centre with the most
valid PM2.5 city-months (ties: more stations); the remaining slots go to the next best-covered
centres overall. Each panel: raw all-station city-month mean (grey), deweathered with the primary
model family (blue), and the range between the two model families (band; the uncertainty from the
choice of model; Monte-Carlo error from resampling is far smaller). 2020 is shaded: the lockdown is
an emissions change that deweathering does not remove. The text in each panel gives the median size
of the weather part of that city's year-on-year change in annual means.

Drawn under both resampling schemes (DEC-109): `seasonal` (primary; weather drawn within +-15 days
of the same date) -> fig3_deweathered; `annual` (Grange & Carslaw's default, which also removes the
seasonal cycle) -> fig3_deweathered_grange_carslaw. City series use the primary validity rule
(near-constant station-years excluded, DEC-110).

    python -m src.viz.fig3_deweathered [--run main|pilot] [--scheme seasonal|annual]
"""

import argparse
import json

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from src.common.paths import INTERIM
from src.normalise.aggregate import OUT
from src.normalise.features import cfg
from src.viz import style as S

N_CITIES = 6


def choose_cities(cm: pd.DataFrame, n: int = N_CITIES) -> list[str]:
    cov = cm.groupby(["unit_id", "region"]).agg(months=("month", "size"), st=("n_stations", "max")).reset_index()
    cov = cov.sort_values(["months", "st", "unit_id"], ascending=[False, False, True])
    picks = [g.unit_id.iloc[0] for _, g in cov.groupby("region", sort=True)]
    for u in cov.unit_id:
        if len(picks) >= n:
            break
        if u not in picks:
            picks.append(u)
    return picks[:n]


def weather_share(cy: pd.DataFrame, col: str = "dw") -> pd.Series:
    """Median |raw - deweathered| year-on-year log change per city, in %."""
    cy = cy.sort_values(["unit_id", "year"])
    g = cy.groupby("unit_id")
    d = (np.log(cy.raw).groupby(cy.unit_id).diff() - np.log(cy[col]).groupby(cy.unit_id).diff())
    d = d.where(g.year.diff() == 1)
    return (100 * d.abs()).groupby(cy.unit_id).median()


def names() -> pd.Series:
    import geopandas as gpd

    # as in src/viz/eda.py: the name of the unit's first GHSL centre (no NCAP labels)
    u = gpd.read_file(INTERIM / "sat_units.gpkg", ignore_geometry=True)[["unit_id", "uc_ids"]]
    uc = gpd.read_file(INTERIM / "ghsl" / "ucdb_india.gpkg", ignore_geometry=True).set_index("uc_id").uc_name
    first = pd.to_numeric(u.set_index("unit_id").uc_ids.str.split(";").str[0], errors="coerce")
    return first.map(uc)  # buffered towns have no centre: NaN, and the unit id is shown instead


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", default="main", choices=["main", "pilot"])
    ap.add_argument("--scheme", default="seasonal", choices=["seasonal", "annual"])
    a = ap.parse_args()
    run, scheme = a.run, a.scheme
    sfx = "" if scheme == "seasonal" else "_annual"
    col = f"dw{sfx}"
    src = OUT if run == "main" else INTERIM / "normalise" / "pilot" / "aggregate"
    choice = json.loads((src / "family_choice.json").read_text(encoding="utf-8"))
    fam = {"lgbm": "LightGBM", "gam": "GAM"}
    cm = pd.read_parquet(src / "city_month.parquet").query("pollutant == 'pm25' and rule == 'primary'")
    cy = pd.read_parquet(src / "city_year.parquet").query("pollutant == 'pm25' and rule == 'primary'")
    picks = choose_cities(cm)  # the same cities under both schemes
    ws = weather_share(cy, col)
    nm = names()

    S.apply()
    fig, axes = plt.subplots(3, 2, figsize=(10, 8.2), sharex=True)
    for ax, u in zip(axes.flat, picks, strict=False):
        g = cm[cm.unit_id == u].set_index("month").sort_index()
        full = pd.date_range(g.index.min(), g.index.max(), freq="MS")
        g = g.reindex(full)  # lines break at missing months instead of bridging them
        ax.axvspan(pd.Timestamp("2020-01-01"), pd.Timestamp("2021-01-01"), color=S.GRID, linewidth=0, zorder=0)
        fams = [f"dw_lgbm{sfx}", f"dw_gam{sfx}"]
        lo, hi = g[fams].min(axis=1), g[fams].max(axis=1)
        ax.fill_between(g.index, lo, hi, color=S.CATEGORICAL[0], alpha=0.25, linewidth=0,
                        label="Range across the two model families")  # fmt: skip
        ax.plot(g.index, g.raw, color=S.NEUTRAL, linewidth=1.2, label="Raw (as measured)")
        ax.plot(g.index, g[col], color=S.CATEGORICAL[0], linewidth=2, label=f"Deweathered ({fam[choice['primary']]})")
        region = S.REGION_LABEL.get(cm[cm.unit_id == u].region.iloc[0], "")
        name = nm.get(u)
        ax.set_title(f"{name if isinstance(name, str) else u} ({region})", fontsize=9)
        st = int(cm[cm.unit_id == u].n_stations.max())
        ax.text(0.99, 0.97, f"weather part of year-on-year change:\nmedian {ws.get(u, np.nan):.0f}%  ·  up to {st} station{'s' if st != 1 else ''}",
                transform=ax.transAxes, ha="right", va="top", fontsize=6.5, color=S.INK_2)  # fmt: skip
        ax.set_ylim(0, np.nanmax([g.raw.max(), hi.max()]) * 1.25)
    for ax in axes.flat[len(picks):]:
        ax.set_visible(False)
    for ax in axes[:, 0]:
        ax.set_ylabel(f"PM2.5, monthly mean ({S.UG})")
    for ax in axes[-1]:
        ax.set_xlabel("Month")
    axes.flat[0].annotate("2020", (pd.Timestamp("2020-07-01"), axes.flat[0].get_ylim()[1] * 0.97), ha="center",
                          va="top", fontsize=6.5, color=S.INK_2)  # fmt: skip
    h, lab = axes.flat[0].get_legend_handles_labels()
    order = [2, 1, 0]
    fig.legend([h[i] for i in order], [lab[i] for i in order], loc="upper left", bbox_to_anchor=(0.0, 0.965),
               ncol=3, fontsize=8)  # fmt: skip
    how = ("weather resampled within ±15 days of each date" if scheme == "seasonal"
           else "Grange & Carslaw all-year resampling (removes the seasonal cycle)")  # fmt: skip
    fig.suptitle(f"Raw vs deweathered monthly PM2.5, six illustrative cities: {how}", x=0.0, ha="left",
                 fontsize=10, fontweight="bold")  # fmt: skip
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    y0, y1 = cfg()["weather_pool_years"]
    n = cfg()["resamples_max" if run == "pilot" else "resamples_default"]
    S.source_note(fig, "City-month = mean over stations inside the city's GHSL urban centre with >= 75% valid days that "
                  "month (all stations; the balanced panel is Phase 6). Deweathered = expected concentration under the "
                  f"city's typical {y0}-{y1} weather ({'for that time of year' if scheme == 'seasonal' else 'from any time of year'}; "
                  f"ERA5; {n} resampled weather days per day). "
                  "Shaded year: 2020, whose lockdown is an emissions change that deweathering does not remove. "
                  "Cities chosen by a coverage rule, one per region first (DEC-106); near-constant station-years "
                  "excluded (DEC-110)."
                  + (" Under this scheme the GAM gives implausible values at some stations (pairing a day's trend with "
                     "another season's weather; docs/deweathering_report.md §5): spikes far above the raw series are "
                     "that artefact, not weather." if scheme == "annual" else ""))  # fmt: skip
    if run == "main":
        S.save(fig, "fig3_deweathered" if scheme == "seasonal" else "fig3_deweathered_grange_carslaw")
    else:  # a preview on the pilot's single-station cities; not a report figure
        fig.savefig(src / f"fig3_preview_{scheme}.png", dpi=150, bbox_inches="tight")
        plt.close(fig)


if __name__ == "__main__":
    main()

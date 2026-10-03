"""Exploratory figures E1-E4 from Phase 3 (proposal stage 4), drawn from the tables `src/viz/eda.py` writes to
data/interim/eda/. Descriptive; none compares NCAP with non-NCAP units (the Phase 3 blinding rule).

    E1 eda_seasonal_regions     monthly PM2.5 cycle by region: ground stations and satellite
    E2 eda_city_trends          raw all-station annual PM2.5, the six most-monitored urban centres
    E3 eda_ground_vs_satellite  station annual PM2.5 vs its ACAG cell: correlation by year
    E4 eda_entrants             do new stations read cleaner or dirtier than the stations already in their city?

    python -m src.viz.eda_figures
"""

import numpy as np
import pandas as pd
from matplotlib import pyplot as plt

from src.common.paths import INTERIM
from src.viz import style as S

EDA = INTERIM / "eda"


def fig_seasonal(ground: pd.DataFrame, sat: pd.DataFrame) -> tuple[plt.Figure, S.Meta]:
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.8), sharey=True)
    for ax, d, title, what in [(axes[0], ground, "(a) Ground stations, 2015–2025", "stations"),
                               (axes[1], sat, "(b) Satellite (ACAG V5.GL.06), centres ≥ 100k, 2015–2024", "units")]:  # fmt: skip
        for i, r in enumerate(S.REGIONS):
            g = d[d.region == r].sort_values("month")
            if g.empty:
                continue
            ax.fill_between(g.month, g.lo, g.hi, color=S.CATEGORICAL[i], alpha=0.12, linewidth=0)
            ax.plot(g.month, g["mean"], color=S.CATEGORICAL[i], marker=S.MARKERS[i], markersize=5,
                    label=f"{S.REGION_LABEL[r]} (n = {int(g[what].max())})")  # fmt: skip
        ax.legend(fontsize=8.5, loc="upper center")
        ax.set_xticks(range(1, 13), list("JFMAMJJASOND"))
        ax.set_xlim(0.7, 12.3)
        ax.set_xlabel("Month")
        ax.set_title(title, fontsize=10)
    axes[0].set_ylabel(f"PM2.5 ({S.UG}), mean across stations or units")
    fig.tight_layout(rect=(0, 0, 1, 0.9))
    S.header(fig, "E1", "How does PM2.5 vary through the year in each region?")
    S.source_note(fig, "Bands: 95% CI across stations (a) or urban centres (b). Exploratory (Phase 3).")
    pk = ground.loc[ground.groupby("region")["mean"].idxmax()]
    cap = ("Monthly mean PM2.5 by region, (a) over ground stations 2015–2025 and (b) over satellite urban-centre values "
           "2015–2024, with 95% intervals across stations or centres. " +
           "; ".join(f"{S.REGION_LABEL[r.region]} ground peak in month {int(r.month)} ({r['mean']:.0f} {S.UG})" for _, r in pk.iterrows()) + ".")  # fmt: skip
    pk_months = sorted({int(m) for d in (ground, sat) for m in d.loc[d.groupby("region")["mean"].idxmax(), "month"]})
    lo_months = sorted({int(m) for d in (ground, sat) for m in d.loc[d.groupby("region")["mean"].idxmin(), "month"]})
    igp_top = {k: bool((d.pivot(index="month", columns="region", values="mean").idxmax(axis=1) == "igp").all())
               for k, d in (("ground", ground), ("satellite", sat))}  # fmt: skip
    top = " and ".join(k for k, v in igp_top.items() if v)
    alt = (f"Two line charts of the seasonal PM2.5 cycle by region, ground and satellite. Every region peaks in month(s) "
           f"{', '.join(map(str, pk_months))} and is lowest in month(s) {', '.join(map(str, lo_months))}."
           + (f" The Indo-Gangetic Plain is highest in every month in the {top} series." if top else ""))  # fmt: skip
    return fig, S.Meta("E1", "How does PM2.5 vary through the year in each region?", "Seasonality by region (exploratory)", cap, alt)


def fig_city_trends(t: pd.DataFrame) -> tuple[plt.Figure, S.Meta]:
    names = t.groupby("unit_id").name.first()
    units = sorted(names.index, key=lambda u: names[u])  # alphabetical
    fig, axes = plt.subplots(2, 3, figsize=(11, 6.2), sharex=True)
    for ax, u in zip(axes.flat, units, strict=False):
        g = t[t.unit_id == u]
        g = g.set_index("year").reindex(range(int(g.year.min()), int(g.year.max()) + 1)).rename_axis("year").reset_index()
        band = g.stations >= 3
        ax.fill_between(g.year, g.lo.where(band).clip(lower=0), g.hi.where(band), color=S.CATEGORICAL[0], alpha=0.12, linewidth=0)
        ax.plot(g.year, g["mean"], color=S.CATEGORICAL[0], marker="o", markersize=4)
        g = g.dropna(subset=["mean"])
        for y, v, n in zip(g.year, g["mean"], g.stations.astype(int), strict=True):
            if y in (g.year.min(), g.year.max()):
                ax.annotate(f"{n} st.", (y, v), textcoords="offset points", xytext=(0, 7), fontsize=8, color=S.INK_2, ha="center")
        ax.set_title(names[u], fontsize=10)
        top = np.nanmax([g["mean"].max(), g.hi.where(g.stations >= 3).max()])
        ax.set_ylim(0, top * 1.18)
    for ax in axes[:, 0]:
        ax.set_ylabel(f"PM2.5 ({S.UG})")
    for ax in axes[1]:
        ax.set_xlabel("Year")
    fig.tight_layout(rect=(0, 0, 1, 0.9))
    S.header(fig, "E2", "What do public trackers see? Raw all-station annual PM2.5, six most-monitored centres")
    S.source_note(fig, "Mean of station annual means over the stations valid that year; the set of stations changes from year to "
                  "year. Band: 95% CI, years with 3+ stations. 'st.' = stations. Alphabetical. Exploratory (Phase 3).")  # fmt: skip
    cap = ("Raw all-station annual mean PM2.5 for the six urban centres with the most station-years, in alphabetical order: "
           f"{', '.join(names[u] for u in units)}. Each point averages whichever stations were valid that year, which is what "
           "public trackers report before any correction for weather or network composition. Bands: 95% intervals across "
           "stations in years with three or more; labels give the station count in the first and last year.")  # fmt: skip
    alt = (f"Six small line charts of raw annual PM2.5 for {', '.join(names[u] for u in units)}, with the number of stations "
           "growing over the years in each city.")  # fmt: skip
    return fig, S.Meta("E2", "What do public trackers see?", "Raw city trends (exploratory)", cap, alt)


def fig_ground_vs_sat(gs: pd.DataFrame) -> tuple[plt.Figure, S.Meta]:
    fig, ax = plt.subplots(figsize=(8.5, 4.6))
    for i, (prod, lab) in enumerate([("V5GL06", "ACAG V5.GL.06 (primary)"), ("V6GL03", "ACAG V6.GL.03")]):
        g = gs[gs["product"] == prod].sort_values("year")
        ax.fill_between(g.year, g.r_lo, g.r_hi, color=S.CATEGORICAL[i], alpha=0.12, linewidth=0)
        ax.plot(g.year, g.r, color=S.CATEGORICAL[i], marker=S.MARKERS[i], markersize=5, label=lab)
    n = gs[gs["product"] == "V5GL06"].set_index("year").stations
    ax.set_xticks(n.index, [f"{y}\n{s}" for y, s in n.items()], fontsize=8.5)
    ax.set_xlabel("Year (and number of stations)")
    ax.set_ylabel("Correlation (r), log station annual mean\nvs log satellite cell value")
    ax.set_ylim(0, 1)
    ax.set_xlim(n.index.min() - 0.5, n.index.max() + 0.5)
    ax.legend(loc="lower left")
    fig.tight_layout(rect=(0, 0, 1, 0.9))
    S.header(fig, "E3", "Does ground–satellite agreement change as the network grows?")
    S.source_note(fig, "Band: bootstrap 95% CI over stations. Exploratory (Phase 3).")
    v = gs[gs["product"] == "V5GL06"].sort_values("year")
    cap = (f"Correlation across stations between log station annual mean PM2.5 and log ACAG value of the station's grid cell, by "
           f"year, for both satellite products, with bootstrap 95% intervals. V5.GL.06: r = {v.r.iloc[0]:.2f} in {int(v.year.iloc[0])} "
           f"({int(v.stations.iloc[0])} stations) and {v.r.iloc[-1]:.2f} in {int(v.year.iloc[-1])} ({int(v.stations.iloc[-1])} stations).")  # fmt: skip
    alt = (f"Line chart of the yearly correlation between ground and satellite PM2.5, from {v.r.iloc[0]:.2f} in "
           f"{int(v.year.iloc[0])} to {v.r.iloc[-1]:.2f} in {int(v.year.iloc[-1])}, as the number of stations grows from "
           f"{int(v.stations.iloc[0])} to {int(v.stations.iloc[-1])}.")  # fmt: skip
    return fig, S.Meta("E3", "Does ground–satellite agreement change as the network grows?", "Ground vs satellite (exploratory)", cap, alt)


def fig_entrants(e: pd.DataFrame) -> tuple[plt.Figure, S.Meta]:
    fig, ax = plt.subplots(figsize=(8.5, 4.6))
    for i, p in enumerate(["pm25", "pm10"]):
        g = e[(e.pollutant == p) & (e.year != "all")].copy()
        g = g[g.units >= 3]
        g["year"] = g.year.astype(int) + (i - 0.5) * 0.18
        ax.errorbar(g.year, g.mean_pct, yerr=[g.mean_pct - g.pct_lo, g.pct_hi - g.mean_pct], fmt=S.MARKERS[i],
                    color=S.CATEGORICAL[i], markersize=6, capsize=0, linewidth=1.2, label={"pm25": "PM2.5", "pm10": "PM10"}[p])  # fmt: skip
    ax.axhline(0, color=S.INK_2, linewidth=0.8)
    ax.set_xlabel("Year the new stations joined")
    ax.set_ylabel("New vs existing stations, same city\nand year (% difference in annual mean)")
    ax.legend()
    fig.tight_layout(rect=(0, 0, 1, 0.9))
    S.header(fig, "E4", "Do new stations read cleaner or dirtier than the ones already there?")
    S.source_note(fig, "95% CI across cities; years with fewer than 3 such cities not shown. Exploratory (Phase 3); the deweathered "
                  "version is in docs/composition_report.md §4.")  # fmt: skip
    a = e[(e.pollutant == "pm25") & (e.year == "all")]
    pooled = f" Pooled over all city-years, PM2.5: {a.mean_pct.iloc[0]:+.1f}% ({a.pct_lo.iloc[0]:+.1f} to {a.pct_hi.iloc[0]:+.1f})." if len(a) else ""
    cap = ("For each city-year with both newly opened and existing valid stations, the % difference between the mean annual PM "
           "of the new stations and of the existing ones, averaged over cities by entry year, with 95% intervals." + pooled)  # fmt: skip
    y25 = e[(e.pollutant == "pm25") & (e.year != "all") & (e.units >= 3)]
    alt = (f"Dot-and-interval chart by entry year: new PM2.5 stations read below the existing stations in the same city in "
           f"{int((y25.mean_pct < 0).sum())} of {len(y25)} entry years shown, each with a wide interval." + pooled)  # fmt: skip
    return fig, S.Meta("E4", "Do new stations read cleaner or dirtier than the ones already there?", "New vs existing stations (exploratory)", cap, alt)


def main() -> None:
    S.apply()
    f, m = fig_seasonal(pd.read_csv(EDA / "seasonal_ground.csv"), pd.read_csv(EDA / "seasonal_satellite.csv"))
    S.save(f, "eda_seasonal_regions", m)
    f, m = fig_city_trends(pd.read_csv(EDA / "city_trends.csv"))
    S.save(f, "eda_city_trends", m)
    f, m = fig_ground_vs_sat(pd.read_csv(EDA / "ground_vs_satellite.csv"))
    S.save(f, "eda_ground_vs_satellite", m)
    f, m = fig_entrants(pd.read_csv(EDA / "entrants.csv", dtype={"year": str}))
    S.save(f, "eda_entrants", m)
    print("E1-E4 written")


if __name__ == "__main__":
    main()

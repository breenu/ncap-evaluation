"""Figure 8: the data-quality heatmap (proposal figure plan; question: how trustworthy is the network over
time?). Drawn from Phase 3 outputs (`station_year_quality.parquet`, reliability score DEC-073).

(a) PM2.5 stations x years coloured by reliability score (0-100), grouped by region, ordered by first year
of data. (b) The same scores as a line: median over the stations reporting each year with the interquartile
band and the number of stations, so the trend is readable without colour (DEC-192).

    python -m src.viz.fig8_quality_heatmap
"""

import numpy as np
import pandas as pd
from matplotlib import pyplot as plt
from matplotlib.colors import BoundaryNorm, ListedColormap

from src.common.paths import INTERIM, PROCESSED
from src.viz import style as S
from src.viz.fig2_station_entry import first_years

YEARS = range(2015, 2026)


def figure(q: pd.DataFrame, first: pd.Series) -> tuple[plt.Figure, S.Meta]:
    S.apply()
    reg = pd.read_csv(INTERIM / "station_regions.csv")
    q = q[(q.pollutant == "pm25") & (q.year <= 2025)]
    x = q.pivot(index="sid", columns="year", values="reliability").reindex(columns=YEARS)
    meta = pd.DataFrame({"sid": x.index}).merge(reg[["sid", "region"]], on="sid", how="left")
    meta["region"] = meta.region.fillna("peninsular/other")
    meta["first"] = meta.sid.map(first)
    meta["r"] = meta.region.map({r: i for i, r in enumerate(S.REGIONS)})
    meta = meta.sort_values(["r", "first", "sid"])
    x = x.loc[meta.sid]
    cmap = ListedColormap([S.SEQ_BLUE[i] for i in (0, 1, 2, 3, 4, 5, 6, 8, 10, 12)])
    cmap.set_bad(S.LAND)

    fig, (ax, bx) = plt.subplots(1, 2, figsize=(12, 9.5), gridspec_kw={"width_ratios": [1.45, 1], "wspace": 0.42})
    im = ax.imshow(x.to_numpy(), aspect="auto", cmap=cmap, norm=BoundaryNorm(np.arange(0, 101, 10), cmap.N), interpolation="none")
    ax.set_xticks(range(0, len(x.columns), 2), list(x.columns)[::2])
    ax.set_yticks([])
    ax.grid(False)
    y0 = 0
    for r in S.REGIONS:
        n = int((meta.region == r).sum())
        if n:
            ax.axhline(y0 - 0.5, color=S.SURFACE, linewidth=2)
            ax.text(-0.7, y0 + n / 2, f"{S.REGION_LABEL[r]}\n({n} stations)", ha="right", va="center", fontsize=9, color=S.INK)
        y0 += n
    ax.set_xlabel("Year")
    ax.set_title(f"(a) Reliability score, {len(x)} PM2.5 stations × year")
    cb = fig.colorbar(im, ax=ax, fraction=0.04, pad=0.09, location="bottom", aspect=30)
    cb.set_label("Reliability score (0–100); pale grey = no data")
    cb.outline.set_visible(False)

    yr = q.groupby("year").reliability.agg(median="median", q1=lambda s: s.quantile(0.25), q3=lambda s: s.quantile(0.75),
                                           n="size").reindex(YEARS)  # fmt: skip
    bx.fill_between(yr.index, yr.q1, yr.q3, color=S.CATEGORICAL[0], alpha=0.18, linewidth=0, label="Interquartile range")
    bx.plot(yr.index, yr["median"], color=S.CATEGORICAL[0], marker="o", label="Median over stations reporting")
    for y, r in yr.iterrows():  # stations reporting, one row along the bottom
        bx.text(y, 3, f"{int(r.n)}", ha="center", va="bottom", fontsize=8, color=S.INK_2)
    bx.text(2014.6, 8, "stations reporting:", ha="left", va="bottom", fontsize=8, color=S.INK_2)
    bx.axvline(2018.5, color=S.NEUTRAL, linewidth=1, linestyle="--")
    bx.text(2018.6, 97, "NCAP launched", fontsize=8.5, color=S.INK_2, va="top")
    bx.set_ylim(0, 100)
    bx.set_xticks(list(YEARS)[::2])
    bx.set_xlabel("Year")
    bx.set_ylabel("Reliability score (0–100)")
    bx.set_title("(b) The same scores over time")
    bx.legend(loc="lower right", bbox_to_anchor=(1.0, 0.1))
    S.header(fig, "8", "How trustworthy is the PM2.5 network over time?", y=1.0)
    S.source_note(fig, "Score = 100 × completeness × share of unflagged data × 0.8 per failed check (neighbour, satellite, "
                  "changepoint) in that station-year (DEC-073). It describes; it excludes nothing. Rows in (a): stations grouped "
                  "by region, ordered by first year of data. Source: CPCB via the Vonter/india-cpcb-aqi mirror (ODbL).", y=0.02)  # fmt: skip
    a, b = yr.loc[2018], yr.loc[2025]
    q1st = q.assign(first=q.sid.map(q.groupby("sid").year.min()))
    m_first = q1st[q1st.year == q1st["first"]].reliability.median()
    m_later = q1st[q1st.year > q1st["first"]].reliability.median()
    cap = (f"(a) The reliability score (0–100) of every PM2.5 station in every year it reported, {len(x)} stations, grouped by "
           f"region and ordered by first year of data; pale grey cells have no data. (b) The median score over the stations "
           f"reporting each year, with its interquartile range: {a['median']:.0f} over {int(a.n)} stations in 2018 and "
           f"{b['median']:.0f} over {int(b.n)} in 2025. The score is 100 × completeness × share of unflagged data, times 0.8 for each "
           "failed consistency check (neighbours, satellite, changepoints). It describes data quality; no data are excluded by it.")  # fmt: skip
    alt = (f"Heatmap of {len(x)} PM2.5 monitoring stations by year, shaded by reliability score, showing how the network grew "
           f"from {int(yr.loc[2015].n)} stations in 2015 to {int(b.n)} in 2025. A station's first, usually partial, year scores a "
           f"median {m_first:.0f}, against {m_later:.0f} in its later years. "
           f"A line chart beside it shows the median score: {a['median']:.0f} in 2018 and {b['median']:.0f} in 2025.")  # fmt: skip
    return fig, S.Meta("8", "How trustworthy is the PM2.5 network over time?", "How trustworthy is the network over time?", cap, alt)


def main() -> None:
    f, m = figure(pd.read_parquet(PROCESSED / "station_year_quality.parquet"), first_years())
    S.save(f, "fig8_quality_heatmap", m)


if __name__ == "__main__":
    main()

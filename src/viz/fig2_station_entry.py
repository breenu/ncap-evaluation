"""Figure 2: the station-entry map (proposal figure plan; question: did the measuring instrument change
under the programme?). Drawn from Phase 3 outputs (`src/viz/eda.py` writes the first-year table).

Left: every station with a station-level coordinate, by the year of its first PM data, in three periods
(before NCAP <= 2018, 2019-2021, 2022-2025), each with its own marker shape and shade (DEC-192: colour is
never the only carrier), over NCAP city locations. Right: new stations per year (all stations).

    python -m src.viz.fig2_station_entry
"""

import geopandas as gpd
import pandas as pd
from matplotlib import pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

from src.clean.station_meta import load_stations
from src.common.paths import INTERIM, raw_dir
from src.viz import style as S

PERIODS = [(2015, 2018, "before NCAP (≤ 2018)", "o", S.SEQ_BLUE[3]),
           (2019, 2021, "2019–2021", "s", S.SEQ_BLUE[7]),
           (2022, 2025, "2022–2025", "^", S.SEQ_BLUE[12])]  # fmt: skip


def first_years() -> pd.Series:
    return pd.read_csv(INTERIM / "eda" / "station_first_year.csv", index_col=0).iloc[:, 0].astype(int)


def period(y: int) -> int:
    return next(i for i, (a, b, *_) in enumerate(PERIODS) if a <= y <= b)


def figure(first: pd.Series) -> tuple[plt.Figure, S.Meta]:
    S.apply()
    st = load_stations()
    st = st[st.coord_is_station_level].merge(first.rename("first_year"), left_on="sid", right_index=True)
    st["p"] = st.first_year.map(period)
    india = gpd.read_file(raw_dir("boundaries") / "datameet@b3fbbde" / "Country" / "india-composite.geojson")
    states = gpd.read_file(raw_dir("boundaries") / "datameet@b3fbbde" / "States" / "Admin2.shp")
    units = gpd.read_file(INTERIM / "sat_units.gpkg")
    ncap = units[(units.ncap_cities != "") & units.in_primary].copy()
    ncap["geometry"] = ncap.geometry.representative_point()

    fig, (ax, bx) = plt.subplots(1, 2, figsize=(12, 7.2), gridspec_kw={"width_ratios": [1.9, 1], "wspace": 0.12})
    india.plot(ax=ax, color=S.LAND, edgecolor=S.NEUTRAL, linewidth=0.6)
    states.boundary.plot(ax=ax, color=S.GRID, linewidth=0.4)
    ax.scatter(ncap.geometry.x, ncap.geometry.y, s=85, facecolors="none", edgecolors=S.INK_2, linewidths=0.9, zorder=2)
    counts = {}
    for i, (_a, _b, _lab, mk, col) in enumerate(PERIODS):
        g = st[st.p == i]
        counts[i] = len(g)
        ax.scatter(g.lon, g.lat, s=22 if mk != "^" else 26, color=col, marker=mk, edgecolors=S.SURFACE, linewidths=0.5,
                   zorder=3 + i)  # fmt: skip
    ax.set_axis_off()
    ax.set_title(f"(a) The {len(st)} located stations, by year of first PM data")
    handles = [Line2D([], [], marker="o", markersize=10, markerfacecolor="none", markeredgecolor=S.INK_2, linestyle="none",
                      label="NCAP city (location)")]  # fmt: skip
    handles += [Line2D([], [], marker=mk, color=col, linestyle="none", markersize=7, label=f"first data {lab} (n = {counts[i]})")
                for i, (a, b, lab, mk, col) in enumerate(PERIODS)]  # fmt: skip
    ax.legend(handles=handles, loc="upper center", bbox_to_anchor=(0.5, 0.02), ncol=2)

    per_year = first.value_counts().reindex(range(2015, 2026), fill_value=0)
    hatches = ["", "///", "..."]
    for y, v in per_year.items():
        bx.bar(y, v, width=0.66, color=PERIODS[period(y)][4], hatch=hatches[period(y)], edgecolor=S.SURFACE, linewidth=0)
        bx.text(y, v + 1.5, str(v), ha="center", fontsize=8.5, color=S.INK_2)
    bx.axvline(2018.5, color=S.INK_2, linewidth=0.8)
    bx.text(2018.35, per_year.max() * 0.7, "NCAP\nlaunched\nJan 2019", fontsize=8.5, color=S.INK_2, va="top", ha="right")
    bx.set_xlabel("Year of a station's first PM data")
    bx.set_ylabel("New stations (count)")
    bx.set_title(f"(b) New stations per year (all {len(first)})")
    bx.set_xticks(range(2015, 2026, 2), ["≤2015", "2017", "2019", "2021", "2023", "2025"])
    bx.grid(axis="x", visible=False)
    bx.legend(handles=[Patch(facecolor=c, hatch=h, edgecolor=S.SURFACE, label=lab) for (_, _, lab, _, c), h in zip(PERIODS, hatches, strict=True)],
              loc="upper left", fontsize=8.5)  # fmt: skip
    S.header(fig, "2", "Did the measuring instrument change under the programme?", y=0.99)
    fig.subplots_adjust(top=0.88)
    S.source_note(fig, f"(a) The {len(st)} stations with a station-level coordinate; (b) all {len(first)} stations. '≤2015': the data "
                  "start in 2015, so stations running earlier appear there. Sources: CPCB via the Vonter/india-cpcb-aqi mirror "
                  "(ODbL); OpenAQ coordinates; DataMeet boundaries; GHSL UCDB R2024A.", y=0.0)  # fmt: skip
    before = int(per_year[per_year.index <= 2018].sum())
    after = int(per_year[per_year.index >= 2019].sum())
    peak_y, peak = int(per_year.idxmax()), int(per_year.max())
    cap = (f"(a) The {len(st)} CPCB continuous monitoring stations with a station-level coordinate, by the period of their first "
           f"PM data: {counts[0]} before NCAP (to 2018), {counts[1]} in 2019–2021 and {counts[2]} in 2022–2025; open circles mark "
           f"NCAP cities. (b) New stations per year, all {len(first)} stations: {before} first reported in 2015–2018 and {after} "
           f"from 2019 onward, peaking at {peak} in {peak_y}. Most of the network that measures NCAP cities today did not exist "
           "at the 2018 baseline, which is why reported city averages mix air-quality change with changes in where monitors stand.")  # fmt: skip
    alt = (f"Map of India with monitoring stations marked by when they first reported: {counts[0]} before 2019, {counts[1]} in "
           f"2019–2021 and {counts[2]} in 2022–2025, most of them in or near NCAP cities. A bar chart shows new stations per year, "
           f"{before} up to 2018 and {after} from 2019, with the peak of {peak} in {peak_y}.")  # fmt: skip
    return fig, S.Meta("2", "Did the measuring instrument change under the programme?",
                       "Did the measuring instrument change under the programme?", cap, alt)  # fmt: skip


def main() -> None:
    f, m = figure(first_years())
    S.save(f, "fig2_station_entry", m)


if __name__ == "__main__":
    main()

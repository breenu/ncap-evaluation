"""Exploratory analysis (proposal stage 4) and the Phase 3 figures.

BLINDING (CLAUDE.md, until the analysis plan is approved): nothing here compares NCAP with non-NCAP
units. NCAP cities appear only as locations on the station-entry map (proposal figure 2).

Tables -> data/interim/eda/*.csv (read by src/clean/audit_report.py); station_year.parquet -> data/processed.
Figures -> reports/figures/:
    fig2_station_entry       stations by year of first data, over NCAP city locations; count by entry year
    fig8_quality_heatmap     stations x years, coloured by reliability score (PM2.5)
    eda_seasonal_regions     monthly PM2.5 cycle by region: ground stations and satellite
    eda_city_trends          raw all-station annual PM2.5, 2015 onward, six best-covered cities
    eda_ground_vs_satellite  station annual PM2.5 vs its ACAG cell: correlation by year
    eda_entrants             are new stations cleaner or dirtier than the stations already in their city?

    python -m src.viz.eda
"""

import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import BoundaryNorm, ListedColormap

from src.clean.station_meta import load_stations
from src.common.paths import INTERIM, PROCESSED, raw_dir
from src.viz import style as S

EDA = INTERIM / "eda"
ENTRY_BINS = [(2015, 2016, "2015–16"), (2017, 2018, "2017–18"), (2019, 2020, "2019–20"),
              (2021, 2022, "2021–22"), (2023, 2025, "2023–25")]  # fmt: skip
RNG = np.random.default_rng(20260926)


def _ci(x: pd.Series) -> tuple[float, float, float]:
    """Mean and 95% t-interval (NaN interval if n < 2)."""
    x = x.dropna()
    m = x.mean()
    if len(x) < 2:
        return m, np.nan, np.nan
    from scipy import stats

    h = stats.t.ppf(0.975, len(x) - 1) * x.std(ddof=1) / np.sqrt(len(x))
    return m, m - h, m + h


# ------------------------------------------------------------------ tables


def station_year() -> pd.DataFrame:
    """Annual mean of valid days, per station-year-pollutant, with validity and reliability."""
    day = pd.read_parquet(PROCESSED / "station_day.parquet")
    q = pd.read_parquet(PROCESSED / "station_year_quality.parquet")
    reg = pd.read_csv(INTERIM / "station_regions.csv")
    rows = []
    for p in ("pm25", "pm10"):
        d = day[day[f"{p}_h1"] >= 18].assign(year=pd.to_datetime(day.date_ist).dt.year)
        m = (
            d.groupby(["sid", "year"])[p]
            .mean()
            .rename("annual_mean")
            .reset_index()
            .assign(pollutant=p)
        )
        rows.append(m)
    y = pd.concat(rows).merge(
        q[["sid", "year", "pollutant", "valid_q1_t75", "valid_q3_t75", "valid_q1_t60", "valid_q1_t90", "reliability"]],
        on=["sid", "year", "pollutant"], how="right",
    )  # fmt: skip
    y = y.merge(reg[["sid", "unit_id", "region"]], on="sid", how="left")
    y.to_parquet(PROCESSED / "station_year.parquet", index=False)
    return y


def first_years(day: pd.DataFrame) -> pd.Series:
    any_pm = day[(day.pm25_h1 > 0) | (day.pm10_h1 > 0)]
    return pd.to_datetime(any_pm.groupby("sid").date_ist.min()).dt.year.rename("first_year")


def entrants(sy: pd.DataFrame) -> pd.DataFrame:
    """For each unit-year: log(mean of entrants' annual means) - log(mean of incumbents'), where
    entrants have their first valid year then and incumbents were valid before and in that year.
    All units pooled (no NCAP split)."""
    v = sy[sy.valid_q1_t75 & sy.annual_mean.notna() & sy.unit_id.notna()]
    rows = []
    for p, g in v.groupby("pollutant"):
        first = g.groupby("sid").year.min()
        g = g.assign(first=g.sid.map(first))
        for (u, y), c in g.groupby(["unit_id", "year"]):
            ent, inc = c[c["first"] == y], c[c["first"] < y]
            if len(ent) and len(inc):
                rows.append({"pollutant": p, "unit_id": u, "year": y, "n_entrants": len(ent), "n_incumbents": len(inc),
                             "log_ratio": np.log(ent.annual_mean.mean()) - np.log(inc.annual_mean.mean())})  # fmt: skip
    e = pd.DataFrame(rows)
    summ = []
    for (p, y), g in e.groupby(["pollutant", "year"]):
        m, lo, hi = _ci(g.log_ratio)
        summ.append({"pollutant": p, "year": y, "units": len(g), "entrants": g.n_entrants.sum(), "mean_log_ratio": m,
                     "ci_lo": lo, "ci_hi": hi})  # fmt: skip
    for p, g in e.groupby("pollutant"):
        m, lo, hi = _ci(g.log_ratio)
        summ.append({"pollutant": p, "year": "all", "units": g.unit_id.nunique(), "entrants": g.n_entrants.sum(),
                     "mean_log_ratio": m, "ci_lo": lo, "ci_hi": hi})  # fmt: skip
    s = pd.DataFrame(summ)
    for c in ("mean_log_ratio", "ci_lo", "ci_hi"):
        s[c.replace("log_ratio", "pct").replace("ci_lo", "pct_lo").replace("ci_hi", "pct_hi")] = (
            100 * (np.exp(s[c]) - 1)
        )
    return s


def ground_vs_sat(sy: pd.DataFrame) -> pd.DataFrame:
    sat = pd.read_parquet(PROCESSED / "station_year_sat.parquet")
    v = sy[(sy.pollutant == "pm25") & sy.valid_q1_t75 & sy.annual_mean.notna()]
    rows = []
    for prod in ("V5GL06", "V6GL03"):
        x = v.merge(sat[sat["product"] == prod], on=["sid", "year"]).dropna(subset=["pm25_cell"])
        for y, g in x.groupby("year"):
            if len(g) < 5:
                continue
            a, b = np.log(g.annual_mean.to_numpy()), np.log(g.pm25_cell.to_numpy())
            r = np.corrcoef(a, b)[0, 1]
            boots = []
            for _ in range(1000):
                i = RNG.integers(0, len(a), len(a))
                boots.append(np.corrcoef(a[i], b[i])[0, 1])
            rows.append({"product": prod, "year": y, "stations": len(g), "r": r, "r_lo": np.nanpercentile(boots, 2.5),
                         "r_hi": np.nanpercentile(boots, 97.5),
                         "median_ratio": float(np.median(g.annual_mean / g.pm25_cell))})  # fmt: skip
    return pd.DataFrame(rows)


def seasonal(sy_day: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    reg = pd.read_csv(INTERIM / "station_regions.csv")
    d = sy_day[sy_day.pm25_h1 >= 18].merge(reg[["sid", "region"]], on="sid")
    d = d.assign(date=pd.to_datetime(d.date_ist))
    d = d[d.date.dt.year <= 2025]
    sm = d.groupby(["region", "sid", d.date.dt.month.rename("month")]).pm25.mean().reset_index()
    ground = []
    for (r, mth), g in sm.groupby(["region", "month"]):
        m, lo, hi = _ci(g.pm25)
        ground.append(
            {"region": r, "month": mth, "stations": len(g), "mean": m, "lo": lo, "hi": hi}
        )
    sat = pd.read_parquet(PROCESSED / "unit_month_sat.parquet")
    ur = pd.read_csv(INTERIM / "unit_regions.csv")
    units = gpd.read_file(INTERIM / "sat_units.gpkg", ignore_geometry=True)
    s = sat[(sat["product"] == "V5GL06") & sat.year.between(2015, 2024)].merge(ur, on="unit_id")
    s = s.merge(units[["unit_id", "in_primary", "pop_2020"]], on="unit_id")
    s = s[s.in_primary & (s.pop_2020 >= 1e5)]
    um = s.groupby(["region", "unit_id", "month"]).pm25_popw.mean().reset_index()
    satr = []
    for (r, mth), g in um.groupby(["region", "month"]):
        m, lo, hi = _ci(g.pm25_popw)
        satr.append({"region": r, "month": mth, "units": len(g), "mean": m, "lo": lo, "hi": hi})
    return pd.DataFrame(ground), pd.DataFrame(satr)


def city_trends(sy: pd.DataFrame, n: int = 6) -> pd.DataFrame:
    units = gpd.read_file(INTERIM / "sat_units.gpkg", ignore_geometry=True)
    v = sy[(sy.pollutant == "pm25") & sy.valid_q1_t75 & sy.annual_mean.notna() & (sy.year <= 2025)]
    top = v.groupby("unit_id").size().sort_values(ascending=False).head(n).index
    rows = []
    for (u, y), g in v[v.unit_id.isin(top)].groupby(["unit_id", "year"]):
        m, lo, hi = _ci(g.annual_mean)
        rows.append({"unit_id": u, "year": y, "stations": len(g), "mean": m, "lo": lo, "hi": hi})
    t = pd.DataFrame(rows).merge(units[["unit_id", "ncap_cities", "uc_ids"]], on="unit_id")
    uc = gpd.read_file(INTERIM / "ghsl" / "ucdb_india.gpkg", ignore_geometry=True)[
        ["uc_id", "uc_name"]
    ]
    first_uc = t.uc_ids.str.split(";").str[0].astype(int)
    t["name"] = first_uc.map(uc.set_index("uc_id").uc_name)
    return t.drop(columns=["ncap_cities"])  # names only; no NCAP labels (blinding)


# ------------------------------------------------------------------ figures


def fig_station_entry(first: pd.Series) -> None:
    st = load_stations()
    st = st[st.coord_is_station_level].merge(first, left_on="sid", right_index=True)
    labels = [b[2] for b in ENTRY_BINS]
    st["bin"] = pd.cut(
        st.first_year, [b[0] - 0.5 for b in ENTRY_BINS] + [ENTRY_BINS[-1][1] + 0.5], labels=labels
    )
    colors = [S.SEQ_BLUE[i] for i in (3, 5, 7, 9, 12)]  # ordinal steps, lightest >= step 250
    india = gpd.read_file(
        raw_dir("boundaries") / "datameet@b3fbbde" / "Country" / "india-composite.geojson"
    )
    states = gpd.read_file(raw_dir("boundaries") / "datameet@b3fbbde" / "States" / "Admin2.shp")
    units = gpd.read_file(INTERIM / "sat_units.gpkg")
    ncap = units[(units.ncap_cities != "") & units.in_primary].copy()
    ncap["geometry"] = ncap.geometry.representative_point()
    fig, (ax, bx) = plt.subplots(1, 2, figsize=(10, 6.2), gridspec_kw={"width_ratios": [2.1, 1]})
    india.plot(ax=ax, color="#f0efec", edgecolor=S.NEUTRAL, linewidth=0.6)
    states.boundary.plot(ax=ax, color=S.GRID, linewidth=0.4)
    ax.scatter(ncap.geometry.x, ncap.geometry.y, s=70, facecolors="none", edgecolors=S.INK_2, linewidths=0.8,
               label="NCAP city (location)", zorder=2)  # fmt: skip
    for lab, col, mk in zip(labels, colors, ["o", "o", "o", "o", "o"], strict=True):
        g = st[st.bin == lab]
        ax.scatter(g.lon, g.lat, s=14, color=col, edgecolors=S.SURFACE, linewidths=0.5, marker=mk,
                   label=f"first data {lab} (n={len(g)})", zorder=3)  # fmt: skip
    ax.set_axis_off()
    ax.set_title("Where and when monitoring stations came online")
    ax.legend(
        loc="upper center", bbox_to_anchor=(0.5, 0.0), ncol=2, fontsize=7.5, handletextpad=0.3
    )
    counts = first.value_counts().reindex(range(2015, 2026), fill_value=0)  # all stations
    cmap = {y: colors[i] for i, (a, b, _) in enumerate(ENTRY_BINS) for y in range(a, b + 1)}
    bx.bar(counts.index, counts.values, width=0.6, color=[cmap[y] for y in counts.index])
    for x, v in counts.items():
        bx.text(x, v + 1.5, str(v), ha="center", fontsize=7, color=S.INK_2)
    bx.set_xlabel("Year of a station's first PM data")
    bx.set_ylabel("Stations (count)")
    bx.axvline(2018.5, color=S.INK_2, linewidth=0.8)
    bx.text(
        2018.6, counts.max() * 0.95, "NCAP launched\nJan 2019", fontsize=7, color=S.INK_2, va="top"
    )
    bx.set_title(f"New stations per year (all {len(first)})")
    bx.set_xticks(range(2015, 2026, 2), ["≤2015", "2017", "2019", "2021", "2023", "2025"])
    S.source_note(fig, f"Map: the {len(st)} stations with a station-level coordinate (data/processed/stations.csv); "
                  "bars: all stations. '≤2015': the data start in 2015, so stations running earlier appear there. "
                  "Sources: CPCB via the Vonter/india-cpcb-aqi mirror; OpenAQ coordinates; DataMeet boundaries; "
                  "GHSL UCDB R2024A.")  # fmt: skip
    S.save(fig, "fig2_station_entry")


def fig_quality_heatmap(q: pd.DataFrame, first: pd.Series) -> None:
    reg = pd.read_csv(INTERIM / "station_regions.csv")
    x = q[(q.pollutant == "pm25") & (q.year <= 2025)].pivot(
        index="sid", columns="year", values="reliability"
    )
    x = x.reindex(columns=range(2015, 2026))
    meta = pd.DataFrame({"sid": x.index}).merge(reg[["sid", "region"]], on="sid", how="left")
    meta["region"] = meta.region.fillna("peninsular/other")
    meta["first"] = meta.sid.map(first)
    meta["r"] = meta.region.map({r: i for i, r in enumerate(S.REGIONS)})
    meta = meta.sort_values(["r", "first", "sid"])
    x = x.loc[meta.sid]
    bounds = np.arange(0, 101, 10)
    cmap = ListedColormap([S.SEQ_BLUE[i] for i in (0, 1, 2, 3, 4, 5, 6, 8, 10, 12)])
    cmap.set_bad("#f0efec")
    fig, ax = plt.subplots(figsize=(6.5, 9))
    im = ax.imshow(
        x.to_numpy(),
        aspect="auto",
        cmap=cmap,
        norm=BoundaryNorm(bounds, cmap.N),
        interpolation="none",
    )
    ax.set_xticks(range(len(x.columns)), x.columns, rotation=0, fontsize=7.5)
    ax.set_yticks([])
    ax.grid(False)
    y0 = 0
    for r in S.REGIONS:
        n = (meta.region == r).sum()
        if n:
            ax.axhline(y0 - 0.5, color=S.SURFACE, linewidth=2)
            ax.text(-0.7, y0 + n / 2, f"{S.REGION_LABEL[r]}\n({n} stations)", ha="right", va="center", fontsize=7.5,
                    color=S.INK)  # fmt: skip
        y0 += n
    ax.set_xlabel("Year")
    ax.set_title(
        "How trustworthy is each station's PM2.5 record? Reliability score by station and year"
    )
    cb = fig.colorbar(im, ax=ax, fraction=0.04, pad=0.02)
    cb.set_label("Reliability score (0–100); grey = no data")
    S.source_note(fig, "Rows: stations, grouped by region, ordered by first year of data. Score = completeness × share of "
                  "unflagged data × 0.8 per failed check (src/clean/reliability.py).")  # fmt: skip
    S.save(fig, "fig8_quality_heatmap")


def fig_seasonal(ground: pd.DataFrame, sat: pd.DataFrame) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(10, 4), sharey=True)
    for ax, d, title, what in [(axes[0], ground, "Ground stations, 2015–2025", "stations"),
                               (axes[1], sat, "Satellite (ACAG V5.GL.06), urban centres ≥100k, 2015–2024", "units")]:  # fmt: skip
        for i, r in enumerate(S.REGIONS):
            g = d[d.region == r].sort_values("month")
            if g.empty:
                continue
            ax.fill_between(g.month, g.lo, g.hi, color=S.CATEGORICAL[i], alpha=0.12, linewidth=0)
            ax.plot(g.month, g["mean"], color=S.CATEGORICAL[i], marker=S.MARKERS[i], markersize=4,
                    label=f"{S.REGION_LABEL[r]} (n={int(g[what].max())})")  # fmt: skip
        # December values of three regions coincide, so no end-labels (they would collide): each
        # panel carries its own legend with distinct markers; values are in data/interim/eda/.
        ax.legend(fontsize=7, loc="upper center")
        ax.set_xticks(range(1, 13), list("JFMAMJJASOND"))
        ax.set_xlim(0.7, 12.3)
        ax.set_xlabel("Month")
        ax.set_title(title, fontsize=9)
    axes[0].set_ylabel(f"PM2.5 ({S.UG}), mean across {''}stations/units")
    fig.suptitle("Seasonal cycle of PM2.5 by region (band: 95% CI across stations or units)", x=0.0, ha="left",
                 fontsize=10, fontweight="bold")  # fmt: skip
    S.save(fig, "eda_seasonal_regions")


def fig_city_trends(t: pd.DataFrame) -> None:
    names = t.groupby("unit_id").name.first()
    fig, axes = plt.subplots(2, 3, figsize=(10, 5.5), sharex=True)
    for ax, (u, g) in zip(axes.flat, t.groupby("unit_id"), strict=False):
        # full year range so the line breaks at missing years; bands only with >= 3 stations
        g = (
            g.set_index("year")
            .reindex(range(int(g.year.min()), int(g.year.max()) + 1))
            .rename_axis("year")
            .reset_index()
        )
        band = g.stations >= 3
        ax.fill_between(g.year, g.lo.where(band).clip(lower=0), g.hi.where(band), color=S.CATEGORICAL[0],
                        alpha=0.12, linewidth=0)  # fmt: skip
        ax.plot(g.year, g["mean"], color=S.CATEGORICAL[0], marker="o", markersize=4)
        g = g.dropna(subset=["mean"])
        g["stations"] = g.stations.astype(int)
        for y, v, n in zip(g.year, g["mean"], g.stations, strict=True):
            if y in (g.year.min(), g.year.max()):
                ax.annotate(f"{n} st.", (y, v), textcoords="offset points", xytext=(0, 6), fontsize=6.5,
                            color=S.INK_2, ha="center")  # fmt: skip
        ax.set_title(names[u], fontsize=9)
        top = np.nanmax([g["mean"].max(), g.hi.where(g.stations >= 3).max()])
        ax.set_ylim(0, top * 1.15)  # headroom for the station-count labels
    for ax in axes[:, 0]:
        ax.set_ylabel(f"PM2.5 ({S.UG})")
    for ax in axes[1]:
        ax.set_xlabel("Year")
    fig.suptitle("Raw all-station annual PM2.5, six best-monitored urban centres (band: 95% CI, years with 3+ stations)",
                 x=0.0, ha="left", fontsize=10, fontweight="bold")  # fmt: skip
    S.source_note(fig, "Mean of station annual means over the stations valid that year (primary completeness rule). "
                  "The set of stations changes from year to year: this is the series public trackers report, "
                  "before any correction for weather or network composition. 'st.' = stations.")  # fmt: skip
    S.save(fig, "eda_city_trends")


def fig_ground_vs_sat(gs: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(7, 3.8))
    for i, (prod, lab) in enumerate(
        [("V5GL06", "ACAG V5.GL.06 (primary)"), ("V6GL03", "ACAG V6.GL.03")]
    ):
        g = gs[gs["product"] == prod].sort_values("year")
        ax.fill_between(g.year, g.r_lo, g.r_hi, color=S.CATEGORICAL[i], alpha=0.12, linewidth=0)
        ax.plot(g.year, g.r, color=S.CATEGORICAL[i], marker=S.MARKERS[i], markersize=5, label=lab)
    n = gs[gs["product"] == "V5GL06"].set_index("year").stations
    ax.set_xticks(n.index, [f"{y}\n{s}" for y, s in n.items()], fontsize=7)
    ax.set_xlabel("Year (and number of stations)")
    ax.set_ylabel("Correlation, log station annual mean\nvs log satellite cell value (r)")
    ax.set_ylim(0, 1)
    ax.set_xlim(n.index.min() - 0.5, n.index.max() + 0.5)
    ax.legend(fontsize=7.5, loc="lower left")
    ax.set_title(
        "Does ground-satellite agreement change as the network grows? (band: bootstrap 95% CI)"
    )
    S.save(fig, "eda_ground_vs_satellite")


def fig_entrants(e: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(7, 3.8))
    for i, p in enumerate(["pm25", "pm10"]):
        g = e[(e.pollutant == p) & (e.year != "all")].copy()
        g = g[g.units >= 3]
        g["year"] = g.year.astype(int) + (i - 0.5) * 0.18
        ax.errorbar(g.year, g.mean_pct, yerr=[g.mean_pct - g.pct_lo, g.pct_hi - g.mean_pct], fmt=S.MARKERS[i],
                    color=S.CATEGORICAL[i], markersize=5, capsize=0, linewidth=1.2,
                    label={"pm25": "PM2.5", "pm10": "PM10"}[p])  # fmt: skip
    ax.axhline(0, color=S.INK_2, linewidth=0.8)
    ax.set_xlabel("Year the new stations joined")
    ax.set_ylabel("New stations vs existing stations\nin the same city, same year (%)")
    ax.legend(fontsize=7.5)
    ax.set_title(
        "Are new stations cleaner or dirtier than the ones already there? (95% CI across cities)"
    )
    S.source_note(fig, "Each city-year with both new and existing valid stations contributes one comparison of mean "
                  "annual PM; years with fewer than 3 such cities are not shown. All cities pooled.")  # fmt: skip
    S.save(fig, "eda_entrants")


def main() -> None:
    S.apply()
    EDA.mkdir(parents=True, exist_ok=True)
    day = pd.read_parquet(PROCESSED / "station_day.parquet")
    sy = station_year()
    q = pd.read_parquet(PROCESSED / "station_year_quality.parquet")
    first = first_years(day)
    first.to_csv(EDA / "station_first_year.csv")
    e = entrants(sy)
    e.to_csv(EDA / "entrants.csv", index=False)
    gs = ground_vs_sat(sy)
    gs.to_csv(EDA / "ground_vs_satellite.csv", index=False)
    ground, sat = seasonal(day)
    ground.to_csv(EDA / "seasonal_ground.csv", index=False)
    sat.to_csv(EDA / "seasonal_satellite.csv", index=False)
    t = city_trends(sy)
    t.to_csv(EDA / "city_trends.csv", index=False)
    fig_station_entry(first)
    fig_quality_heatmap(q, first)
    fig_seasonal(ground, sat)
    fig_city_trends(t)
    fig_ground_vs_sat(gs)
    fig_entrants(e)
    print("figures written")


if __name__ == "__main__":
    main()

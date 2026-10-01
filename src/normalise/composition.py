"""Network-composition correction (Phase 6, RQ1) and H4 (analysis plan §5). Rules: DEC-125 to DEC-131.

Three annual trends per city (= urban-centre unit, stations inside the polygon only, DEC-105/125):
    all      every station valid that year ("as reported", after the audit's cleaning)
    panel    stations valid in the baseline year and every year to 2025 (strict; 2018 primary,
             2019 sensitivity) or in the baseline year and 2025 only (loose; not registered)
    sat      ACAG V5.GL.06 population-weighted over the unit, to 2024 (DEC-070)
A city value is the unweighted mean of its stations' annual means. Ground trends come raw and
deweathered (any family, either resampling scheme).

Per city, baseline -> 2025, change = 100 x (m_end / m_base - 1) in %; differences in pp (DEC-126):
    reported     change(all, raw)                                the proposal's order for figure 1:
    weather      change(all, raw) - change(all, dw)              reported = weather + composition
    composition  change(all, dw) - change(panel, dw)                        + corrected (exact)
    corrected    change(panel, dw)
    comp_raw     change(all, raw) - change(panel, raw)          composition bias on raw values, and
    weather_pan  change(panel, raw) - change(panel, dw)         weather on the panel (the other order)
    h4           corrected - reported  (DEC-127: the reported FALL minus the corrected fall;
                 positive = the reported number flatters the city) = h4_weather + h4_composition
H4 is computed for NCAP units only; the all-city summaries show measurement quantities only
(composition, weather, ground - satellite), never NCAP against non-NCAP (Phase 7's job).

Uncertainty (DEC-129): across cities, a cluster bootstrap over cities (percentile 95% CI); per city,
a station bootstrap stratified by panel membership.

    python -m src.normalise.composition   -> data/processed/composition/
        city_changes.parquet   spec x unit x pollutant: the quantities above, station counts, watch stations
        summary.csv            spec x pollutant x group x metric: n, mean, 95% CI, SE, median
        h4.csv                 spec x pollutant: H4 over NCAP units, CI, SE, 2.8 x SE, supported
        city_boot.csv          primary spec, both competing families: per-city station-bootstrap CIs
        trends.parquet         primary spec: unit x pollutant x year x series (all/panel raw/dw, sat)
        composition_by_year.csv  all-city mean gap between the all-station and panel trends, per year
        ground_sat.csv, ground_sat_summary.csv   PM2.5 panel vs satellite, baseline -> 2024
        entrants.csv, entrants_summary.csv       "do new stations read cleaner?" raw vs deweathered
        coverage.csv           valid station-years not in the deweathered table, and their effect
"""

import warnings
import zlib
from dataclasses import asdict, dataclass, replace

import numpy as np
import pandas as pd

from src.common.paths import INTERIM, PROCESSED, params
from src.normalise.aggregate import OUT as DW_OUT

OUT = PROCESSED / "composition"
FAMILY_NAME = {"gam": "GAM", "lgbm": "LightGBM", "gam_k4": "GAM (k = 4/yr)", "raw": "none (raw)"}
SCHEME_NAME = {"seasonal": "seasonal", "annual": "Grange & Carslaw"}
CHANGE_COLS = ["reported", "unmodelled", "weather", "raw_minus_dw", "composition", "corrected", "comp_raw",
               "weather_pan", "comp_dw", "h4", "h4_unmodelled", "h4_weather", "h4_raw_minus_dw",
               "h4_composition"]  # fmt: skip
ALL_CITY_METRICS = ["comp_raw", "comp_dw", "unmodelled", "weather", "raw_minus_dw", "composition",
                    "weather_pan"]  # measurement only
NCAP_METRICS = ["h4", "h4_unmodelled", "h4_weather", "h4_raw_minus_dw", "h4_composition", "reported", "corrected",
                *ALL_CITY_METRICS]  # fmt: skip
FAMILIES = ("gam", "lgbm", "gam_k4")


def ccfg() -> dict:
    return params()["composition"]


@dataclass(frozen=True)
class Spec:
    """One version of the composition analysis (DEC-128)."""

    family: str = "gam"  # gam | lgbm | gam_k4 | raw (no deweathering)
    scheme: str = "seasonal"  # seasonal | annual (Grange & Carslaw)
    rule: str = "primary"  # primary | registered_flags (DEC-110)
    baseline: int = 2018
    variant: str = "q1_t75"  # completeness: q1_t75 primary; q1_t60, q1_t90, q3_t75
    panel: str = "strict"  # strict | loose
    drop_reenu: bool = False  # drop the 5 Reenu-decided stations (DEC-080)
    drop_rel50: bool = False  # drop station-years with reliability < 50 (DEC-073)
    drop_posthoc: bool = False  # drop posthoc_drop_registered (site_1433), ADDED AFTER INSPECTING THE DATA
    kind: str = "grid"

    @property
    def dw_col(self) -> str:
        if self.family == "raw":
            return "raw"
        return f"dw_{self.family}" + ("_annual" if self.scheme == "annual" else "")

    @property
    def label(self) -> str:
        parts = [self.family, self.scheme, self.rule, str(self.baseline), self.variant, self.panel]
        parts += [x for x, on in (("drop_reenu", self.drop_reenu), ("drop_rel50", self.drop_rel50),
                                  ("drop_posthoc", self.drop_posthoc)) if on]  # fmt: skip
        return "|".join(parts)

    def describe(self) -> str:
        d = [f"{FAMILY_NAME[self.family]}", SCHEME_NAME[self.scheme] if self.family != "raw" else "no deweathering",
             "primary rule" if self.rule == "primary" else "registered flags only"]  # fmt: skip
        if self.baseline != PRIMARY.baseline:
            d.append(f"baseline {self.baseline}")
        if self.variant != PRIMARY.variant:
            d.append({"q1_t60": "completeness 60%", "q1_t90": "completeness 90%", "q3_t75": "3 of 4 quarter-hours"}[self.variant])
        if self.panel != "strict":
            d.append("loose panel (not registered)")
        if self.drop_reenu:
            d.append("without the 5 Reenu-decided stations")
        if self.drop_rel50:
            d.append("without reliability < 50")
        if self.drop_posthoc:
            d.append("without site_1433 (added after inspecting the data)")
        return ", ".join(d)


PRIMARY = Spec()
AS_REGISTERED = Spec(family="gam_k4", scheme="annual", rule="registered_flags")


def specs() -> list[Spec]:
    """Every version reported (DEC-128): the family x scheme x rule grid, the post-hoc Satna rows,
    one change at a time from the primary for both competing families, and no deweathering."""
    base = ccfg()["baseline_years"]
    out = []
    for fam in ("gam", "lgbm", "gam_k4"):
        for sch in ("seasonal", "annual"):
            for rule in ("primary", "registered_flags"):
                out.append(Spec(fam, sch, rule))
                if rule == "registered_flags":
                    out.append(Spec(fam, sch, rule, drop_posthoc=True, kind="posthoc"))
    for fam in ("gam", "lgbm"):
        s = Spec(fam, kind="one-at-a-time")
        out += [replace(s, baseline=b) for b in base[1:]]
        out += [replace(s, variant=v) for v in ("q1_t60", "q1_t90", "q3_t75")]
        out += [replace(s, drop_reenu=True), replace(s, drop_rel50=True), replace(s, panel="loose")]
    out.append(Spec(family="raw", kind="no-deweathering"))
    return out


# ------------------------------------------------------------------ station-level selection


def select(sy: pd.DataFrame, spec: Spec) -> pd.DataFrame:
    """Valid station-years inside a unit polygon for one version: sid, pollutant, unit_id, year, raw, dw."""
    v = sy[(sy.rule == spec.rule) & (sy.variant == spec.variant) & sy.valid & sy.inside_unit]
    if spec.drop_reenu:
        v = v[~v.reenu_decided.fillna(False).astype(bool)]
    if spec.drop_rel50:
        v = v[~(v.reliability < 50)]
    if spec.drop_posthoc:
        v = v[~v.sid.isin(params().get("posthoc_drop_registered", []))]
    v = v[v.raw.notna() & v[spec.dw_col].notna()]
    guard = v[f"guard_{spec.dw_col}"] if f"guard_{spec.dw_col}" in v else False  # DEC-117 flag, never a filter
    # fitted annual mean (DEC-136): the family's prediction under the actual weather; raw has none
    fcol = f"fit_{spec.family}"
    fit = v.raw if spec.family == "raw" else (v[fcol] if fcol in v else np.nan)
    return pd.DataFrame({"sid": v.sid, "pollutant": v.pollutant, "unit_id": v.unit_id, "year": v.year.astype(int),
                         "raw": v.raw, "dw": v[spec.dw_col], "fit": fit, "guard": guard}).reset_index(drop=True)  # fmt: skip


def panel_members(v: pd.DataFrame, baseline: int, end: int, strict: bool = True) -> pd.DataFrame:
    """(sid, pollutant) valid in the baseline year and every year to `end` (strict), or in the
    baseline year and `end` only (loose)."""
    years = set(range(baseline, end + 1)) if strict else {baseline, end}
    n = v[v.year.isin(years)].groupby(["sid", "pollutant"]).year.nunique()
    ok = n[n == len(years)].reset_index()[["sid", "pollutant"]]
    return ok


def mark_panel(v: pd.DataFrame, spec: Spec) -> pd.DataFrame:
    m = panel_members(v, spec.baseline, ccfg()["end_year"], spec.panel == "strict").assign(in_panel=True)
    v = v.merge(m, on=["sid", "pollutant"], how="left")
    return v.assign(in_panel=v.in_panel.fillna(False).astype(bool))


# ------------------------------------------------------------------ per-city quantities


def pct(a, b):
    """100 x (b / a - 1), elementwise."""
    return 100 * (np.asarray(b, dtype=float) / np.asarray(a, dtype=float) - 1)


def decompose(raw_all, dw_all, raw_pan, dw_pan, fit_all=None) -> dict:
    """The per-city quantities from (baseline, end) pairs of the city means. Each argument is an
    array whose last axis is (baseline, end); works for one city or a batch of bootstrap draws.
    `fit_all` (the all-station fitted mean, DEC-136) splits raw - deweathered into unmodelled change
    (raw - fitted) and modelled weather (fitted - deweathered); without it both are NaN and only
    the combined `raw_minus_dw` exists."""
    ra, da, rp, dp = (pct(x[..., 0], x[..., 1]) for x in map(np.asarray, (raw_all, dw_all, raw_pan, dw_pan)))
    fa = np.full_like(ra, np.nan) if fit_all is None else pct(np.asarray(fit_all)[..., 0], np.asarray(fit_all)[..., 1])
    return {
        "chg_raw_all": ra, "chg_dw_all": da, "chg_raw_panel": rp, "chg_dw_panel": dp, "chg_fit_all": fa,
        "reported": ra, "unmodelled": ra - fa, "weather": fa - da, "raw_minus_dw": ra - da,
        "composition": da - dp, "corrected": dp,
        "comp_raw": ra - rp, "weather_pan": rp - dp, "comp_dw": da - dp,
        "h4": dp - ra, "h4_unmodelled": fa - ra, "h4_weather": da - fa, "h4_raw_minus_dw": da - ra,
        "h4_composition": dp - da,
    }  # fmt: skip


def city_matrix(g: pd.DataFrame, b: int, e: int) -> tuple:
    """One unit-pollutant: per station, raw, dw and fitted annual means at (b, e) (NaN where not
    valid), and its panel flag."""
    g = g[g.year.isin([b, e])]
    raw = g.pivot_table(index="sid", columns="year", values="raw").reindex(columns=[b, e])
    dw = g.pivot_table(index="sid", columns="year", values="dw").reindex(columns=[b, e]).loc[raw.index]
    fit = g.pivot_table(index="sid", columns="year", values="fit", dropna=False).reindex(index=raw.index, columns=[b, e])
    pan = g.groupby("sid").in_panel.first().loc[raw.index].to_numpy()
    return raw.to_numpy(), dw.to_numpy(), fit.to_numpy(), pan, list(raw.index)


def means_from(raw: np.ndarray, dw: np.ndarray, fit: np.ndarray, pan: np.ndarray, idx: np.ndarray) -> tuple:
    """City means over the stations in `idx` (last axis): all stations valid in each year (raw, dw,
    fitted) and the panel stations (raw, dw). idx may be (n,) or (draws, n). The fitted mean is NaN
    for a year in which any valid station lacks a fitted value (DEC-136), never a partial mean."""
    r, d, f, p = raw[idx], dw[idx], fit[idx], pan[idx]
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)  # a draw with no station valid in a year -> NaN
        ra, da = np.nanmean(r, axis=-2), np.nanmean(d, axis=-2)
        fa = np.nanmean(f, axis=-2)
        fa = np.where(np.isfinite(f).sum(axis=-2) == np.isfinite(r).sum(axis=-2), fa, np.nan)
        pm = p[..., None]
        rp = np.nanmean(np.where(pm, r, np.nan), axis=-2)
        dp = np.nanmean(np.where(pm, d, np.nan), axis=-2)
    return ra, da, rp, dp, fa


def city_changes(v: pd.DataFrame, spec: Spec) -> pd.DataFrame:
    """Per unit-pollutant with a panel: counts, the four city means at baseline and end, and the
    quantities of `decompose`."""
    b, e = spec.baseline, ccfg()["end_year"]
    watch = set(params().get("watch_stations", []))
    rows = []
    for (u, pol), g in v.groupby(["unit_id", "pollutant"]):
        if not g.in_panel.any():
            continue
        raw, dw, fit, pan, sids = city_matrix(g, b, e)
        ra, da, rp, dp, fa = means_from(raw, dw, fit, pan, np.arange(len(sids)))
        r = {"unit_id": u, "pollutant": pol, "n_panel": int(pan.sum()),
             "n_all_base": int(np.isfinite(raw[:, 0]).sum()), "n_all_end": int(np.isfinite(raw[:, 1]).sum()),
             "raw_all_base": ra[0], "raw_all_end": ra[1], "dw_all_base": da[0], "dw_all_end": da[1],
             "raw_panel_base": rp[0], "raw_panel_end": rp[1], "dw_panel_base": dp[0], "dw_panel_end": dp[1],
             "fit_all_base": fa[0], "fit_all_end": fa[1],
             "watch_stations": ", ".join(sorted(watch & set(sids))),
             "guard_all": int(g[g.year.isin([b, e])].guard.sum()),
             "guard_panel": int(g[g.year.isin([b, e]) & g.in_panel].guard.sum())}  # fmt: skip
        r.update({k: float(x) for k, x in decompose(ra, da, rp, dp, fa).items()})
        rows.append(r)
    return pd.DataFrame(rows).assign(spec=spec.label, **asdict(spec))


def station_bootstrap(v: pd.DataFrame, spec: Spec, draws: int, seed: int) -> pd.DataFrame:
    """Per city: resample stations within the city, stratified by panel membership (panel stations
    among panel stations, the others among the others), recompute every quantity; percentile 95% CI.
    A stratum of one station contributes no between-station variation (DEC-129)."""
    b, e = spec.baseline, ccfg()["end_year"]
    rows = []
    for (u, pol), g in v.groupby(["unit_id", "pollutant"]):
        if not g.in_panel.any():
            continue
        raw, dw, fit, pan, sids = city_matrix(g, b, e)
        rng = np.random.default_rng([seed, zlib.crc32(f"{spec.label}|{u}|{pol}".encode())])
        ip, io = np.flatnonzero(pan), np.flatnonzero(~pan)
        idx = np.concatenate([rng.choice(ip, (draws, len(ip))), rng.choice(io, (draws, len(io))) if len(io)
                              else np.empty((draws, 0), dtype=int)], axis=1)  # fmt: skip
        ra, da, rp, dp, fa = means_from(raw, dw, fit, pan, idx)  # each (draws, 2)
        res = decompose(ra, da, rp, dp, fa)
        r = {"unit_id": u, "pollutant": pol, "n_panel": len(ip), "n_other": len(io)}
        for k in CHANGE_COLS:
            x = res[k][np.isfinite(res[k])]
            r[f"{k}_lo"], r[f"{k}_hi"] = (np.percentile(x, [2.5, 97.5]) if len(x) else (np.nan, np.nan))
        rows.append(r)
    return pd.DataFrame(rows).assign(spec=spec.label, family=spec.family)


# ------------------------------------------------------------------ across-city summaries


def cluster_boot(x: np.ndarray, draws: int, rng: np.random.Generator) -> dict:
    """Unweighted mean across cities with a percentile 95% CI from resampling cities (DEC-129)."""
    x = np.asarray(x, dtype=float)
    x = x[np.isfinite(x)]
    n = len(x)
    if n == 0:
        return {"n": 0, "mean": np.nan, "lo": np.nan, "hi": np.nan, "se": np.nan, "median": np.nan}
    m = x[rng.integers(0, n, (draws, n))].mean(axis=1)
    lo, hi = np.percentile(m, [2.5, 97.5])
    return {"n": n, "mean": float(x.mean()), "lo": float(lo), "hi": float(hi), "se": float(m.std(ddof=1)),
            "median": float(np.median(x))}  # fmt: skip


def spec_rng(label: str, extra: str = "") -> np.random.Generator:
    return np.random.default_rng([params()["seed"], zlib.crc32(f"{label}|{extra}".encode())])


def summarise(ch: pd.DataFrame, ncap: set[str], draws: int) -> pd.DataFrame:
    rows = []
    for (label, pol), g in ch.groupby(["spec", "pollutant"], sort=False):
        for group, gg, metrics in (("all cities", g, ALL_CITY_METRICS), ("NCAP", g[g.unit_id.isin(ncap)], NCAP_METRICS)):
            for mtr in metrics:
                s = cluster_boot(gg[mtr].to_numpy(), draws, spec_rng(label, f"{pol}|{group}|{mtr}"))
                rows.append({"spec": label, "pollutant": pol, "group": group, "metric": mtr, **s})
    return pd.DataFrame(rows)


def h4_table(ch: pd.DataFrame, ncap: set[str], spec_list: list[Spec], draws: int) -> pd.DataFrame:
    """H4 (DEC-127/128/131): over NCAP units with a panel, per pollutant; supported if the mean is
    positive and its 95% CI excludes 0. 2.8 x SE beside every CI that includes 0."""
    meta = {s.label: s for s in spec_list}
    rows = []
    for (label, pol), g in ch[ch.unit_id.isin(ncap)].groupby(["spec", "pollutant"], sort=False):
        s = meta[label]
        b = cluster_boot(g.h4.to_numpy(), draws, spec_rng(label, f"{pol}|NCAP|h4"))
        rows.append({
            "spec": label, "kind": s.kind, "family": s.family, "scheme": s.scheme, "rule": s.rule,
            "description": s.describe(), "pollutant": pol, "cities": b["n"],
            "stations_panel": int(g.n_panel.sum()), "single_station_panels": int((g.n_panel == 1).sum()),
            "station_years_used": int((g.n_all_base + g.n_all_end).sum()),
            "guard_flags_all": int(g.guard_all.sum()), "guard_flags_panel": int(g.guard_panel.sum()),
            "reported_mean": g.reported.mean(), "corrected_mean": g.corrected.mean(),
            "h4_unmodelled_mean": g.h4_unmodelled.mean(), "h4_weather_mean": g.h4_weather.mean(),
            "h4_raw_minus_dw_mean": g.h4_raw_minus_dw.mean(), "h4_composition_mean": g.h4_composition.mean(),
            "cities_without_split": int(g.h4_weather.isna().sum()),
            "h4_mean": b["mean"], "h4_lo": b["lo"], "h4_hi": b["hi"], "h4_se": b["se"], "h4_median": b["median"],
            "cities_positive": int((g.h4 > 0).sum()),
            "detectable_2p8se": 2.8 * b["se"] if b["lo"] <= 0 <= b["hi"] else np.nan,
            "supported": bool(b["mean"] > 0 and b["lo"] > 0),
            "watch_stations": ", ".join(sorted({w for x in g.watch_stations for w in x.split(", ") if w})),
            "is_primary": label == PRIMARY.label, "is_as_registered": label == AS_REGISTERED.label,
        })  # fmt: skip
    return pd.DataFrame(rows)


# ------------------------------------------------------------------ trends, ground vs satellite


def sat_table() -> pd.DataFrame:
    s = pd.read_parquet(PROCESSED / "unit_year_sat.parquet")
    return s.pivot_table(index=["unit_id", "year"], columns="product", values="pm25_popw").reset_index().merge(
        s[s["product"] == params()["satellite"]["primary"]][["unit_id", "year", "pm25_area"]], on=["unit_id", "year"]
    )  # fmt: skip


def trends(v: pd.DataFrame, v_other: pd.DataFrame, sat: pd.DataFrame, spec: Spec) -> pd.DataFrame:
    """Long table of annual city series for the primary version: all stations and panel, raw and
    deweathered (primary family and the other competing family), and the satellite."""
    rows = []
    for name, x in (("all", v), ("panel", v[v.in_panel])):
        g = x.groupby(["unit_id", "pollutant", "year"])
        rows.append(g[["raw", "dw"]].mean().assign(n_stations=g.sid.nunique()).reset_index().assign(set=name))
    t = pd.concat(rows, ignore_index=True)
    o = pd.concat([v_other.groupby(["unit_id", "pollutant", "year"]).dw.mean().rename("dw_other").reset_index().assign(set="all"),
                   v_other[v_other.in_panel].groupby(["unit_id", "pollutant", "year"]).dw.mean().rename("dw_other")
                   .reset_index().assign(set="panel")])  # fmt: skip
    t = t.merge(o, on=["unit_id", "pollutant", "year", "set"], how="left")
    units = t.unit_id.unique()
    p = params()["satellite"]
    s = sat[sat.unit_id.isin(units) & sat.year.between(2015, ccfg()["satellite_end_year"])]
    s = s.rename(columns={p["primary"]: "sat", p["comparison"]: "sat_comparison"})[["unit_id", "year", "sat", "sat_comparison"]]
    return t.merge(s, on=["unit_id", "year"], how="left").assign(spec=spec.label)


def composition_by_year(v: pd.DataFrame, spec: Spec, draws: int) -> pd.DataFrame:
    """Per year t from the baseline: across cities with a panel, the mean of
    100 x (all_t / all_base - panel_t / panel_base), raw and deweathered (all cities; DEC-126)."""
    b, e = spec.baseline, ccfg()["end_year"]
    keep = v.groupby(["unit_id", "pollutant"]).in_panel.transform("any")
    x = v[keep & v.year.between(b, e)]
    a = x.groupby(["unit_id", "pollutant", "year"])[["raw", "dw"]].mean()
    p = x[x.in_panel].groupby(["unit_id", "pollutant", "year"])[["raw", "dw"]].mean()
    j = a.join(p, rsuffix="_p").reset_index()
    base = j[j.year == b].set_index(["unit_id", "pollutant"])
    j = j.join(base[["raw", "dw", "raw_p", "dw_p"]], on=["unit_id", "pollutant"], rsuffix="_b")
    j["gap_raw"] = 100 * (j.raw / j.raw_b - j.raw_p / j.raw_p_b)
    j["gap_dw"] = 100 * (j.dw / j.dw_b - j.dw_p / j.dw_p_b)
    rows = []
    for (pol, y), g in j[j.year > b].groupby(["pollutant", "year"]):
        for col in ("gap_raw", "gap_dw"):
            s = cluster_boot(g[col].to_numpy(), draws, spec_rng(spec.label, f"{pol}|{y}|{col}"))
            rows.append({"pollutant": pol, "year": y, "metric": col, **s,
                         "cities_changed": int((g[col].abs() > 1e-9).sum())})  # fmt: skip
    return pd.DataFrame(rows)


def ground_vs_sat(v: pd.DataFrame, v_lgbm: pd.DataFrame, sat: pd.DataFrame, spec: Spec) -> pd.DataFrame:
    """PM2.5 only, baseline -> satellite_end_year (DEC-126): panel raw minus satellite, with the
    all-station raw and both families' deweathered panel changes beside it."""
    b, e = spec.baseline, ccfg()["satellite_end_year"]
    p = params()["satellite"]
    rows = []
    for u, g in v[v.pollutant == "pm25"].groupby("unit_id"):
        if not g.in_panel.any():
            continue
        s = sat[sat.unit_id == u].set_index("year")
        if not {b, e} <= set(s.index):
            continue
        gl = v_lgbm[(v_lgbm.pollutant == "pm25") & (v_lgbm.unit_id == u)]
        at = lambda x, y, c: x[x.year == y][c].mean()  # noqa: E731
        pan, pan_l = g[g.in_panel], gl[gl.in_panel]
        r = {"unit_id": u, "n_panel": int(pan.sid.nunique()),
             "chg_panel_raw": pct(at(pan, b, "raw"), at(pan, e, "raw")),
             "chg_all_raw": pct(at(g, b, "raw"), at(g, e, "raw")),
             "chg_panel_dw": pct(at(pan, b, "dw"), at(pan, e, "dw")),
             "chg_panel_dw_lgbm": pct(at(pan_l, b, "dw"), at(pan_l, e, "dw")),
             "chg_sat": pct(s.loc[b, p["primary"]], s.loc[e, p["primary"]]),
             "chg_sat_comparison": pct(s.loc[b, p["comparison"]], s.loc[e, p["comparison"]]),
             "chg_sat_area": pct(s.loc[b, "pm25_area"], s.loc[e, "pm25_area"]),
             "sat_base": s.loc[b, p["primary"]], "panel_raw_base": at(pan, b, "raw")}  # fmt: skip
        rows.append({k: float(x) if isinstance(x, np.ndarray) else x for k, x in r.items()})
    t = pd.DataFrame(rows)
    t["gap_panel_sat"] = t.chg_panel_raw - t.chg_sat
    t["gap_all_sat"] = t.chg_all_raw - t.chg_sat
    t["gap_panel_dw_sat"] = t.chg_panel_dw - t.chg_sat
    t["gap_panel_sat_comparison"] = t.chg_panel_raw - t.chg_sat_comparison
    t["gap_panel_sat_area"] = t.chg_panel_raw - t.chg_sat_area
    return t


def ground_sat_summary(gs: pd.DataFrame, ncap: set[str], draws: int) -> pd.DataFrame:
    rows = []
    for group, g in (("all cities", gs), ("NCAP", gs[gs.unit_id.isin(ncap)])):
        for c in ("gap_panel_sat", "gap_all_sat", "gap_panel_dw_sat", "gap_panel_sat_comparison", "gap_panel_sat_area",
                  "chg_panel_raw", "chg_sat"):  # fmt: skip
            if group == "all cities" and c in ("chg_panel_raw", "chg_sat"):
                continue  # levels of change are summarised for NCAP units only (no NCAP contrast)
            rows.append({"group": group, "metric": c, **cluster_boot(g[c].to_numpy(), draws, spec_rng("ground_sat", f"{group}|{c}"))})
        r = np.corrcoef(g.chg_panel_raw, g.chg_sat)[0, 1] if len(g) > 2 else np.nan
        rows.append({"group": group, "metric": "corr_panel_sat_changes", "n": len(g), "mean": r})
    return pd.DataFrame(rows)


# ------------------------------------------------------------------ do new stations read cleaner?

ENTRANT_COLS = ["raw", "dw_gam", "dw_lgbm", "dw_gam_annual", "dw_lgbm_annual", "dw_gam_k4"]


def entrants(sy: pd.DataFrame) -> pd.DataFrame:
    """Phase 3's comparison (src/viz/eda.py: entrants) on the deweathered table (DEC-130): per
    unit-year, log(mean of entrants) - log(mean of incumbents) for raw and each deweathered column,
    over the same station-years. Entrant = first valid year; incumbent = valid before and now."""
    v = sy[(sy.rule == "primary") & (sy.variant == "q1_t75") & sy.valid & sy.inside_unit].dropna(subset=ENTRANT_COLS)
    rows = []
    for p, g in v.groupby("pollutant"):
        g = g.assign(first=g.sid.map(g.groupby("sid").year.min()))
        for (u, y), c in g.groupby(["unit_id", "year"]):
            ent, inc = c[c["first"] == y], c[c["first"] < y]
            if len(ent) and len(inc):
                r = {"pollutant": p, "unit_id": u, "year": int(y), "n_entrants": len(ent), "n_incumbents": len(inc)}
                for col in ENTRANT_COLS:
                    r[f"lr_{col}"] = np.log(ent[col].mean()) - np.log(inc[col].mean())
                rows.append(r)
    e = pd.DataFrame(rows)
    for col in ENTRANT_COLS[1:]:
        e[f"diff_{col}"] = e[f"lr_{col}"] - e.lr_raw  # paired: deweathered minus raw, same unit-year
    return e


def entrants_summary(e: pd.DataFrame, draws: int) -> pd.DataFrame:
    """Per entry year: mean and 95% t-interval across unit-years (as Phase 3). Pooled ('all'): mean
    over unit-years with a cluster bootstrap over units. Log ratios reported as % (100 x (e^x - 1))."""
    from scipy import stats

    cols = [c for c in e.columns if c.startswith(("lr_", "diff_"))]
    rows = []
    for (p, y), g in e.groupby(["pollutant", "year"]):
        for c in cols:
            x = g[c].dropna()
            m = x.mean()
            h = stats.t.ppf(0.975, len(x) - 1) * x.std(ddof=1) / np.sqrt(len(x)) if len(x) > 1 else np.nan
            rows.append({"pollutant": p, "year": str(y), "measure": c, "units": len(x), "mean": m, "lo": m - h, "hi": m + h})
    for p, g in e.groupby("pollutant"):
        units = g.unit_id.unique()
        rng = spec_rng("entrants", p)
        draw = rng.integers(0, len(units), (draws, len(units)))
        by_unit = {u: gg for u, gg in g.groupby("unit_id")}
        for c in cols:
            sums = np.array([by_unit[u][c].sum() for u in units])
            cnts = np.array([by_unit[u][c].notna().sum() for u in units])
            m = sums[draw].sum(axis=1) / cnts[draw].sum(axis=1)
            lo, hi = np.percentile(m, [2.5, 97.5])
            rows.append({"pollutant": p, "year": "all", "measure": c, "units": len(units), "mean": g[c].mean(),
                         "lo": lo, "hi": hi})  # fmt: skip
    s = pd.DataFrame(rows)
    for c in ("mean", "lo", "hi"):
        s[f"{c}_pct"] = np.where(s.measure.str.startswith("lr_"), 100 * (np.exp(s[c]) - 1), 100 * s[c])
    return s


# ------------------------------------------------------------------ coverage check (DEC-131)


def coverage(ch_reg: pd.DataFrame, ncap: set[str]) -> pd.DataFrame:
    """Valid station-years (registered completeness rule, inside a polygon, to end_year) that are not
    in the deweathered table, and how much adding them back moves each NCAP city's reported change
    (compared with the registered-flags version, which applies the same validity rules)."""
    e = ccfg()["end_year"]
    p3 = pd.read_parquet(PROCESSED / "station_year.parquet")
    reg = pd.read_csv(INTERIM / "station_regions.csv", usecols=["sid", "km_to_unit"])
    p3 = p3[p3.valid_q1_t75 & p3.annual_mean.notna() & (p3.year <= e)].merge(reg, on="sid")
    p3 = p3[p3.km_to_unit.eq(0)]
    sy = pd.read_parquet(DW_OUT / "station_year.parquet", columns=["sid", "pollutant", "year", "rule", "variant", "valid"])
    d = sy[(sy.rule == "registered_flags") & (sy.variant == "q1_t75") & sy.valid]
    m = p3.merge(d[["sid", "pollutant", "year"]], on=["sid", "pollutant", "year"], how="left", indicator=True)
    miss = m[m._merge == "left_only"]
    rows = [{"what": "missing_station_years", "pollutant": pol, "year": int(y), "value": len(g)}
            for (pol, y), g in miss.groupby(["pollutant", "year"])]  # fmt: skip
    b = PRIMARY.baseline
    full = p3.groupby(["unit_id", "pollutant", "year"]).annual_mean.mean().unstack("year")
    c = ch_reg[ch_reg.unit_id.isin(ncap)].set_index(["unit_id", "pollutant"])
    f = full.reindex(c.index)
    diff = pct(f[b], f[e]) - c.reported.to_numpy()
    for pol in ("pm25", "pm10"):
        dd = diff[c.index.get_level_values("pollutant") == pol]
        rows.append({"what": "ncap_reported_change_abs_diff_max_pp", "pollutant": pol, "year": e,
                     "value": float(np.nanmax(np.abs(dd))) if len(dd) else np.nan})  # fmt: skip
        rows.append({"what": "ncap_cities_affected", "pollutant": pol, "year": e,
                     "value": int((np.abs(dd) > 1e-9).sum())})  # fmt: skip
    return pd.DataFrame(rows)


# ------------------------------------------------------------------ fitted annual means (DEC-136)


def fitted_station_years() -> pd.DataFrame:
    """Per station-year, completeness variant and validity rule: each family's fitted annual mean =
    the mean over the variant's valid days of exp(fitted) x the series' smearing factor (the model's
    prediction under the actual weather, on the deweathered scale, DEC-101). NaN if any of those
    days has no fitted value (days that are not fit days: the 60% variant's 15-17-hour days).
    Rules are stacked as in src.normalise.aggregate.with_rules: primary = run `main`; registered
    flags = run `registered` for the refitted series, `main` otherwise."""
    from src.normalise import collect
    from src.normalise.aggregate import VARIANTS, raw_days
    from src.normalise.features import INPUTS

    raw = raw_days()
    runs = {}
    for run in ("main", "registered"):
        series = pd.read_csv(INPUTS / run / "series.csv")
        if "skipped" in series:
            series = series[series.skipped.isna()]
        parts = []
        for r in series.itertuples():
            per = None
            for fam in FAMILIES:
                out = collect.load(run, fam, r.pollutant, r.sid)[0]
                f = out.fitted.to_numpy()
                ok = out.y.notna().to_numpy()
                smear = float(np.mean(np.exp(out.y.to_numpy()[ok] - f[ok])))
                d = pd.DataFrame({"date": out.date, f"fit_{fam}": np.exp(f) * smear})
                per = d if per is None else per.merge(d, on="date")
            parts.append(per.assign(sid=r.sid, pollutant=r.pollutant))
        day = raw.merge(pd.concat(parts, ignore_index=True), on=["sid", "pollutant", "date"], how="inner")
        cols = [f"fit_{f}" for f in FAMILIES]
        rows = []
        for v, (hcol, t) in VARIANTS.items():
            d = day[day[hcol] >= int(np.ceil(24 * t))].assign(year=lambda x: x.date.dt.year)
            g = d.groupby(["sid", "pollutant", "year"])[cols]
            m = g.mean().where(g.count().eq(g.size(), axis=0))  # a partial mean is never used
            rows.append(m.reset_index().assign(variant=v))
        runs[run] = (pd.concat(rows, ignore_index=True), series[["sid", "pollutant"]])
    main_t, (reg_t, reg_series) = runs["main"][0], runs["registered"]
    keep = main_t.merge(reg_series.assign(_r=True), on=["sid", "pollutant"], how="left")._r.isna().to_numpy()
    return pd.concat([main_t.assign(rule="primary"), main_t[keep].assign(rule="registered_flags"),
                      reg_t.assign(rule="registered_flags")], ignore_index=True)  # fmt: skip


# ------------------------------------------------------------------ main


def ncap_units() -> set[str]:
    u = pd.read_csv(INTERIM / "pregate" / "units.csv", usecols=["unit_id", "ncap_cities"])
    return set(u[u.ncap_cities.notna()].unit_id)


def run_spec(sy: pd.DataFrame, spec: Spec) -> tuple[pd.DataFrame, pd.DataFrame]:
    v = mark_panel(select(sy, spec), spec)
    return v, city_changes(v, spec)


def main() -> None:
    c = ccfg()
    draws, seed = c["bootstrap_draws"], params()["seed"]
    OUT.mkdir(parents=True, exist_ok=True)
    sy = pd.read_parquet(DW_OUT / "station_year.parquet")
    fitted = fitted_station_years()
    fitted.to_parquet(OUT / "station_year_fitted.parquet", index=False)
    sy = sy.merge(fitted, on=["sid", "pollutant", "year", "variant", "rule"], how="left")
    ncap = ncap_units()
    spec_list = specs()
    chs, vs = [], {}
    for s in spec_list:
        v, ch = run_spec(sy, s)
        vs[s.label] = v
        chs.append(ch)
    ch = pd.concat(chs, ignore_index=True)
    ch["ncap"] = ch.unit_id.isin(ncap)
    ch.to_parquet(OUT / "city_changes.parquet", index=False)
    summarise(ch, ncap, draws).to_csv(OUT / "summary.csv", index=False)
    h4 = h4_table(ch, ncap, spec_list, draws)
    h4.to_csv(OUT / "h4.csv", index=False)

    lg = Spec("lgbm")
    boots = [station_bootstrap(vs[s.label], s, draws, seed) for s in (PRIMARY, lg)]
    pd.concat(boots, ignore_index=True).to_csv(OUT / "city_boot.csv", index=False)

    sat = sat_table()
    trends(vs[PRIMARY.label], vs[lg.label], sat, PRIMARY).to_parquet(OUT / "trends.parquet", index=False)
    pd.concat([composition_by_year(vs[s.label], s, draws).assign(spec=s.label)
               for s in (PRIMARY, lg, replace(PRIMARY, baseline=c["baseline_years"][1], kind="one-at-a-time"))]
              ).to_csv(OUT / "composition_by_year.csv", index=False)  # fmt: skip
    gs = ground_vs_sat(vs[PRIMARY.label], vs[lg.label], sat, PRIMARY)
    gs.assign(ncap=gs.unit_id.isin(ncap)).to_csv(OUT / "ground_sat.csv", index=False)
    ground_sat_summary(gs, ncap, draws).to_csv(OUT / "ground_sat_summary.csv", index=False)

    e = entrants(sy)
    e.to_csv(OUT / "entrants.csv", index=False)
    entrants_summary(e, draws).to_csv(OUT / "entrants_summary.csv", index=False)
    reg = ch[ch.spec == Spec(rule="registered_flags").label]
    coverage(reg, ncap).to_csv(OUT / "coverage.csv", index=False)

    show = h4[h4.kind.isin(["grid"])][["description", "pollutant", "cities", "h4_mean", "h4_lo", "h4_hi", "supported"]]
    print(show.round(2).to_string(index=False))


if __name__ == "__main__":
    main()

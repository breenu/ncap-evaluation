"""Layer B (ground) estimators and their checks: ITS and ground DiD for PM2.5 and PM10 (plan §5 item 4;
DEC-148, DEC-149). Phase 7 Part B. GATED (hard rule 4).

Stations and panels come from Phase 6's selection code (`src.normalise.composition.select` and
`mark_panel`), so a Layer B version and the H4 version with the same settings use the same stations:
inside the unit polygon, strict balanced panel valid every year from the baseline to 2025.

    ITS, per city c       d_c = mean log y over post-years (t >= g_c) - mean over pre-years (baseline <= t < g_c),
                          2020 excluded from both; pooled = unweighted mean over cities
    ground DiD, cohort g  stations of cohort-g cities and all control stations, station and year effects;
                          on a balanced panel this equals mean_{treated} d_s - mean_{control} d_s exactly
                          (tested against OLS); aggregate = sum_g n_g b_g / sum n_g, n_g = treated cities
    city-level DiD        the same on city means (added before computing, DEC-148)
95% CIs: percentile cluster bootstrap over cities (1,000; ITS one stratum; DiD stratified by treated
cohort and control). Effects: log units, negative = a reduction (DEC-135).

    python -m src.causal.layer_b    -> data/processed/causal/layer_b/
"""

import zlib
from dataclasses import dataclass, field, replace

import numpy as np
import pandas as pd

from src.causal import layer_a as A
from src.common.gate import require_gate
from src.common.paths import params
from src.normalise import composition as C
from src.normalise.aggregate import OUT as DW_OUT

OUT = A.OUT / "layer_b"
POLS = ("pm25", "pm10")


@dataclass(frozen=True)
class BVersion:
    """One Layer B version: a Phase 6 selection (`spec`) plus the year handling."""

    key: str
    label: str
    status: str
    spec: C.Spec = field(default_factory=C.Spec)
    exclude_post: tuple[int, ...] = ()  # e.g. (2019,) for the without-2019 check (DEC-123)
    series: str = "panel"  # panel | all (investigation step 1)


def versions() -> list[BVersion]:
    """Every Layer B version reported (DEC-148/149)."""
    P = C.PRIMARY
    reg = "registered"
    v = [
        BVersion("primary", "Primary: GAM, seasonal, primary rule, 2018 panel", reg, P),
        BVersion("lgbm", "LightGBM (other family)", reg, replace(P, family="lgbm")),
        BVersion("raw", "No deweathering (raw panel)", reg, replace(P, family="raw")),
        BVersion("gam_annual", "GAM, Grange & Carslaw resampling", reg, replace(P, scheme="annual")),
        BVersion("as_registered", "As registered, no deviations (GAM k = 4/yr, Grange & Carslaw, registered flags)", reg,
                 C.Spec("gam_k4", "annual", "registered_flags")),
        BVersion("as_registered_posthoc", "As registered, without site_1433 (added after inspecting the data)",
                 "added after inspecting the data", C.Spec("gam_k4", "annual", "registered_flags", drop_posthoc=True)),
        BVersion("regflags", "Registered flags only (GAM, seasonal)", reg, replace(P, rule="registered_flags")),
        BVersion("regflags_posthoc", "Registered flags only, without site_1433 (added after inspecting the data)",
                 "added after inspecting the data", replace(P, rule="registered_flags", drop_posthoc=True)),
        BVersion("base2019", "Balanced-panel baseline 2019", reg, replace(P, baseline=2019)),
        BVersion("base2019_lgbm", "Baseline 2019, LightGBM (DEC-137 follow-up)", "added before computing",
                 replace(P, baseline=2019, family="lgbm")),
        BVersion("q1_t60", "Completeness 60%", reg, replace(P, variant="q1_t60")),
        BVersion("q1_t90", "Completeness 90%", reg, replace(P, variant="q1_t90")),
        BVersion("q3_t75", "Valid hour: 3 of 4 quarter-hours", reg, replace(P, variant="q3_t75")),
        BVersion("drop_reenu", "Without the 5 Reenu-decided stations", reg, replace(P, drop_reenu=True)),
        BVersion("drop_rel50", "Without station-years with reliability < 50", reg, replace(P, drop_rel50=True)),
        BVersion("no2019", "Without 2019 (added 2026-09-28, DEC-123)", "added 2026-09-28 (DEC-123)", P, (2019,)),
        BVersion("no2019_lgbm", "Without 2019, LightGBM (DEC-123)", "added 2026-09-28 (DEC-123)", replace(P, family="lgbm"), (2019,)),
        BVersion("all_stations", "All stations instead of the panel (investigation step 1)", "registered", P, (), "all"),
        BVersion("all_stations_raw", "All stations, raw (investigation steps 1 and 4)", "registered", replace(P, family="raw"), (), "all"),
    ]
    return v


# ---------------------------------------------------------------- data


def load_station_years() -> pd.DataFrame:
    sy = pd.read_parquet(DW_OUT / "station_year.parquet")
    fitted = pd.read_parquet(C.OUT / "station_year_fitted.parquet")
    return sy.merge(fitted, on=["sid", "pollutant", "year", "variant", "rule"], how="left")


def roles() -> pd.DataFrame:
    """unit_id -> group ('treated' for NCAP units incl. buffered towns, DEC-125/148; 'control' for the
    control pool), cohort (listing; 0 for controls)."""
    u = pd.read_csv(A.OUT / "design_units.csv")
    ncap = u.ncap_cities.fillna("") != ""
    g = np.where(ncap, "treated", np.where(u.role_a == "control", "control", ""))
    out = pd.DataFrame({"unit_id": u.unit_id, "group": g, "cohort": np.where(ncap, u.cohort_listed, 0)})
    out = out[out.group != ""]
    out["cohort"] = out.cohort.astype(int)
    return out


def station_panel(sy: pd.DataFrame, bv: BVersion) -> pd.DataFrame:
    """Station-years of the version's series inside treated / control units, baseline..end, 2020 kept
    (callers drop it): sid, unit_id, pollutant, year, y (deweathered or raw value), raw, fit, group, cohort."""
    spec, end = bv.spec, C.ccfg()["end_year"]
    v = C.mark_panel(C.select(sy, spec), spec)
    v = v[v.year.between(spec.baseline, end)]
    # 'all': every valid station of a city that has a panel (investigation step 1), else the panel only
    has_panel = v[v.in_panel].groupby(["unit_id", "pollutant"]).size().rename("np").reset_index()
    v = v.merge(has_panel, on=["unit_id", "pollutant"])
    if bv.series == "panel":
        v = v[v.in_panel]
    v = v.merge(roles(), on="unit_id")
    return v.rename(columns={"dw": "y"})[["sid", "unit_id", "pollutant", "year", "y", "raw", "fit", "group", "cohort"]]


def city_series(st: pd.DataFrame) -> pd.DataFrame:
    """City-year means of the stations present (the panel: every station every year)."""
    return st.groupby(["unit_id", "pollutant", "year", "group", "cohort"], as_index=False).agg(
        y=("y", "mean"), raw=("raw", "mean"), fit=("fit", "mean"), n_stations=("sid", "nunique"))


# ---------------------------------------------------------------- estimators


def contrasts(d: pd.DataFrame, key: str, cohort: int | None, base: int, drop: tuple[int, ...],
              exclude_post: tuple[int, ...] = (), year_col: str = "year") -> pd.Series:  # fmt: skip
    """Per entity (`key`): mean log y over post-years minus mean over pre-years. Post = t >= cohort
    (the entity's own cohort if `cohort` is None), pre = base <= t < cohort; `drop` years excluded from
    both, `exclude_post` from the post-years."""
    x = d[~d[year_col].isin(drop)].copy()
    g = x.cohort if cohort is None else cohort
    x["ly"] = np.log(x.y)
    post = (x[year_col] >= g) & ~x[year_col].isin(exclude_post)
    pre = (x[year_col] < g) & (x[year_col] >= base)
    a = x[post].groupby(key).ly.mean()
    b = x[pre].groupby(key).ly.mean()
    out = (a - b).dropna()
    return out


def year_contrast(d: pd.DataFrame, key: str, cohort: int | None, base: int, year: int, drop: tuple[int, ...]) -> pd.Series:
    """Per entity: log y in `year` minus the pre-year mean (the '2020, own coefficient')."""
    x = d.copy()
    g = x.cohort if cohort is None else cohort
    x["ly"] = np.log(x.y)
    pre = (x.year < g) & (x.year >= base) & ~x.year.isin(drop)
    a = x[x.year == year].groupby(key).ly.mean()
    b = x[pre].groupby(key).ly.mean()
    return (a - b).dropna()


def its_city(cs: pd.DataFrame, base: int, drop=(2020,), exclude_post=()) -> pd.DataFrame:
    t = cs[cs.group == "treated"]
    d = contrasts(t, "unit_id", None, base, drop, exclude_post)
    return d.rename("d").reset_index()


def did_parts(frame: pd.DataFrame, key: str, base: int, drop=(2020,), exclude_post=()) -> dict:
    """Per treated cohort g: (treated entity contrasts, control entity contrasts) with g's pre/post split.
    `frame`: station- or city-level rows with key, unit_id, group, cohort, year, y."""
    out = {}
    for g in sorted(frame[frame.group == "treated"].cohort.unique()):
        t = frame[(frame.group == "treated") & (frame.cohort == g)]
        c = frame[frame.group == "control"]
        out[int(g)] = (contrasts(t, key, g, base, drop, exclude_post), contrasts(c, key, g, base, drop, exclude_post))
    return out


def balanced(frame: pd.DataFrame, key: str, drop=(2020,)) -> bool:
    x = frame[~frame.year.isin(drop)]
    return x.groupby(key).year.nunique().nunique() == 1


# ---------------------------------------------------------------- bootstrap


def _rng(label: str) -> np.random.Generator:
    return np.random.default_rng([params()["seed"], zlib.crc32(label.encode())])


def boot_its(d: pd.DataFrame, draws: int, rng: np.random.Generator) -> np.ndarray:
    x = d.d.to_numpy()
    idx = rng.integers(0, len(x), size=(draws, len(x)))
    return x[idx].mean(axis=1)


def did_estimate(parts: dict, unit_of: dict[str, pd.Series]) -> tuple[float, dict]:
    """Aggregate DiD from per-cohort contrasts; weights = treated cities per cohort."""
    bg, ng = {}, {}
    for g, (t, c) in parts.items():
        bg[g] = t.mean() - c.mean()
        ng[g] = unit_of["t"][g].nunique()
    tot = sum(ng.values())
    return sum(ng[g] * bg[g] for g in bg) / tot, bg


def boot_did(parts: dict, units_t: dict, units_c: pd.Series, draws: int, rng: np.random.Generator) -> np.ndarray:
    """Cluster bootstrap over cities, stratified by treated cohort and control. Entity contrasts are
    averaged with each resampled city's multiplicity. `units_t[g]`, `units_c`: entity -> city."""
    cities_c = np.array(sorted(units_c.unique()))
    out = np.zeros(draws)
    ng = {g: units_t[g].nunique() for g in parts}
    tot = sum(ng.values())
    # control contrasts per city differ by cohort (pre/post split); resample the control cities once per draw
    draw_c = rng.integers(0, len(cities_c), size=(draws, len(cities_c)))
    draw_t = {g: rng.integers(0, ng[g], size=(draws, ng[g])) for g in sorted(parts)}
    for g, (t, c) in parts.items():
        ct = np.array(sorted(units_t[g].unique()))
        # sum and count of entity contrasts per city
        ts = t.groupby(units_t[g].reindex(t.index)).agg(["sum", "count"]).reindex(ct)
        cs = c.groupby(units_c.reindex(c.index)).agg(["sum", "count"]).reindex(cities_c)
        tsum, tcnt = ts["sum"].to_numpy()[draw_t[g]].sum(1), ts["count"].to_numpy()[draw_t[g]].sum(1)
        csum, ccnt = cs["sum"].to_numpy()[draw_c].sum(1), cs["count"].to_numpy()[draw_c].sum(1)
        out += ng[g] / tot * (tsum / tcnt - csum / ccnt)
    return out


def ci(boot: np.ndarray) -> tuple[float, float, float]:
    b = boot[np.isfinite(boot)]
    return float(np.percentile(b, 2.5)), float(np.percentile(b, 97.5)), float(np.std(b, ddof=1))


# ---------------------------------------------------------------- one version


def scope(st: pd.DataFrame) -> dict:
    t = st[st.group == "treated"]
    per = t.groupby("unit_id").sid.nunique()
    return {"cities": int(per.size), "stations": int(t.sid.nunique()), "single_station_cities": int((per == 1).sum()),
            "control_cities": int(st[st.group == "control"].unit_id.nunique()),
            "control_stations": int(st[st.group == "control"].sid.nunique())}  # fmt: skip


def run_version(sy: pd.DataFrame, bv: BVersion, draws: int) -> tuple[list[dict], pd.DataFrame]:
    rows, city_rows = [], []
    base = bv.spec.baseline
    st_all = station_panel(sy, bv)
    for pol in POLS:
        st = st_all[st_all.pollutant == pol]
        if not len(st[st.group == "treated"]):
            rows.append({"version": bv.key, "pollutant": pol, "estimator": "ITS", "computable": False})
            continue
        cs = city_series(st)
        sc = scope(st)
        common = {"version": bv.key, "label": bv.label, "status": bv.status, "pollutant": pol, "baseline": base,
                  "exclude_post": ";".join(map(str, bv.exclude_post)), "series": bv.series, "computable": True, **sc}  # fmt: skip
        # ITS
        d = its_city(cs, base, exclude_post=bv.exclude_post)
        b = boot_its(d, draws, _rng(f"its|{bv.key}|{pol}"))
        lo, hi, se = ci(b)
        rows.append({**common, "estimator": "ITS", "est": float(d.d.mean()), "lo95": lo, "hi95": hi, "se": se})
        city_rows.append(d.assign(version=bv.key, pollutant=pol))
        # 2020 own coefficient (ITS)
        y20 = year_contrast(cs[cs.group == "treated"], "unit_id", None, base, 2020, (2020,))
        b20 = boot_its(y20.rename("d").reset_index(), draws, _rng(f"its2020|{bv.key}|{pol}"))
        lo, hi, se = ci(b20)
        rows.append({**common, "estimator": "ITS, 2020 own coefficient", "est": float(y20.mean()), "lo95": lo, "hi95": hi, "se": se})
        # DiD (stations, as registered) and on city means (added before computing)
        if not len(st[st.group == "control"]):
            rows.append({**common, "estimator": "DiD", "computable": False})
            continue
        # the all-station series is not a balanced station panel, so only its city means enter a DiD
        pairs = (("DiD", st, "sid"), ("DiD, city means", cs, "unit_id")) if bv.series == "panel" else (("DiD, city means", cs, "unit_id"),)
        for est_name, frame, key in pairs:
            if not balanced(frame, key):
                raise ValueError(f"{bv.key}/{pol}/{est_name}: panel not balanced; the closed-form DiD needs it")
            parts = did_parts(frame, key, base, exclude_post=bv.exclude_post)
            emap = frame.drop_duplicates(key).set_index(key).unit_id
            units_t = {g: emap.reindex(t.index) for g, (t, _) in parts.items()}
            units_c = emap.reindex(next(iter(parts.values()))[1].index)
            est, bg = did_estimate(parts, {"t": units_t})
            bb = boot_did(parts, units_t, units_c, draws, _rng(f"did|{est_name}|{bv.key}|{pol}"))
            lo, hi, se = ci(bb)
            rows.append({**common, "estimator": est_name, "est": float(est), "lo95": lo, "hi95": hi, "se": se,
                         "by_cohort": "; ".join(f"{g}: {v:+.4f} ({units_t[g].nunique()} cities)" for g, v in bg.items())})  # fmt: skip
        if bv.series != "panel":
            continue
        # 2020 own coefficient (DiD, stations)
        t20 = {g: year_contrast(st[(st.group == "treated") & (st.cohort == g)], "sid", g, base, 2020, (2020,))
               for g in sorted(st[st.group == "treated"].cohort.unique())}  # fmt: skip
        c20 = {g: year_contrast(st[st.group == "control"], "sid", g, base, 2020, (2020,)) for g in t20}
        parts20 = {g: (t20[g], c20[g]) for g in t20}
        emap = st.drop_duplicates("sid").set_index("sid").unit_id
        units_t = {g: emap.reindex(t.index) for g, (t, _) in parts20.items()}
        est, _ = did_estimate(parts20, {"t": units_t})
        bb = boot_did(parts20, units_t, emap.reindex(next(iter(parts20.values()))[1].index), draws, _rng(f"did2020|{bv.key}|{pol}"))
        lo, hi, se = ci(bb)
        rows.append({**common, "estimator": "DiD, 2020 own coefficient", "est": float(est), "lo95": lo, "hi95": hi, "se": se})
    return rows, pd.concat(city_rows, ignore_index=True) if city_rows else pd.DataFrame()


# ---------------------------------------------------------------- DEC-137 follow-up, satellite at stations


def misfit_by_year(sy: pd.DataFrame) -> pd.DataFrame:
    """Mean over the treated Layer B panel stations of log(raw / fitted), per year, family and baseline."""
    rows = []
    for fam in ("gam", "lgbm"):
        for base in C.ccfg()["baseline_years"]:
            bv = BVersion("x", "x", "x", replace(C.PRIMARY, family=fam, baseline=base))
            st = station_panel(sy, bv)
            st = st[st.group == "treated"]
            g = st.assign(m=np.log(st.raw / st.fit)).groupby(["pollutant", "year"]).m.agg(["mean", "count"]).reset_index()
            rows.append(g.assign(family=fam, baseline=base))
    return pd.concat(rows, ignore_index=True)


def satellite_at_stations(sy: pd.DataFrame, draws: int) -> pd.DataFrame:
    """Investigation step 3 (DEC-150): ITS 2018 -> 2024 of the satellite value at the PM2.5 panel stations'
    own 0.01 deg cells, against the population-weighted polygon value, same cities."""
    from src.common.paths import PROCESSED

    st = station_panel(sy, BVersion("primary", "", "", C.PRIMARY))
    st = st[(st.pollutant == "pm25") & (st.group == "treated")]
    cell = pd.read_parquet(PROCESSED / "station_year_sat.parquet")
    cell = cell[cell["product"] == "V5GL06"]
    sids = st[["sid", "unit_id", "cohort"]].drop_duplicates()
    yrs = range(C.PRIMARY.baseline, C.ccfg()["satellite_end_year"] + 1)
    c = cell[cell.sid.isin(sids.sid) & cell.year.isin(yrs)].merge(sids, on="sid")
    c = c.groupby(["unit_id", "cohort", "year"], as_index=False).pm25_cell.mean().rename(columns={"pm25_cell": "y"})
    pan = pd.read_parquet(A.OUT / "panel_annual.parquet")
    p = pan[(pan.series == "popw_V5GL06") & pan.unit_id.isin(sids.unit_id) & pan.year.isin(yrs)]
    p = p.merge(sids[["unit_id", "cohort"]].drop_duplicates(), on="unit_id").rename(columns={"value": "y"})
    rows = []
    for name, frame in (("satellite at the panel stations' cells", c), ("satellite, population-weighted polygon", p)):
        d = contrasts(frame, "unit_id", None, C.PRIMARY.baseline, (2020,)).rename("d").reset_index()
        lo, hi, se = ci(boot_its(d, draws, _rng(f"satcell|{name}")))
        rows.append({"series": name, "cities": len(d), "est": float(d.d.mean()), "lo95": lo, "hi95": hi, "se": se})
    gd = st.groupby(["unit_id", "cohort", "year"], as_index=False).y.mean()
    gd = gd[gd.year.isin(yrs)]
    d = contrasts(gd, "unit_id", None, C.PRIMARY.baseline, (2020,)).rename("d").reset_index()
    lo, hi, se = ci(boot_its(d, draws, _rng("satcell|ground")))
    rows.append({"series": "ground panel, deweathered, same years", "cities": len(d), "est": float(d.d.mean()), "lo95": lo, "hi95": hi, "se": se})
    return pd.DataFrame(rows)


def main() -> None:
    require_gate("Layer B: ground ITS and DiD")
    draws = int(params()["causal"]["ground_bootstrap"])
    OUT.mkdir(parents=True, exist_ok=True)
    sy = load_station_years()
    rows, cities = [], []
    for bv in versions():
        r, c = run_version(sy, bv, draws)
        rows += r
        cities.append(c)
        print(bv.key, "done", flush=True)
    pd.DataFrame(rows).to_csv(OUT / "estimates.csv", index=False)
    pd.concat(cities, ignore_index=True).to_csv(OUT / "its_cities.csv", index=False)
    misfit_by_year(sy).to_csv(OUT / "misfit_by_year.csv", index=False)
    satellite_at_stations(sy, draws).to_csv(OUT / "satellite_at_stations.csv", index=False)


if __name__ == "__main__":
    main()

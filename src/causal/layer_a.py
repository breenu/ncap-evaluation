"""Layer A (satellite) synthetic difference-in-differences: panels, specifications, runs, summaries.

Phase 7, RQ3. Rules: docs/analysis_plan.md §5 (registered, `6e24eca`), read as in DEC-135, with the gaps
filled before any estimate in DEC-139 to DEC-150. GATED (hard rule 4): estimates post-2019 effects.

    python -m src.causal.layer_a panels            satellite panels for every series (+ pre-2019 panel)
    python -m src.causal.layer_a specs             every SDID specification -> data/processed/causal/specs/
    python -m src.causal.layer_a run <id> ...      Rscript src/causal/sdid.R <id> ... (resumable)
    python -m src.causal.layer_a loo <id>          leave-one-out donors (DEC-147 item 15)
    python -m src.causal.layer_a summarise         estimands with joint-placebo SEs -> sdid_summary.csv

Effects (DEC-135): treated minus counterfactual on log concentration; negative = a reduction.
"""

import hashlib
import json
import os
import subprocess
import sys
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from src.causal.pregate import read_pre_period, season_panel
from src.common.gate import require_gate
from src.common.paths import INTERIM, PROCESSED, params

OUT = PROCESSED / "causal"
SPEC_DIR = OUT / "specs"
SDID_DIR = OUT / "sdid"
PREGATE = INTERIM / "pregate"

PATANCHERUVU = "u1932"  # buffered-town unit (DEC-063), sensitivity only
ASANSOL = "u0000"  # Asansol & Raniganj: centres 11080 (Asansol) + 11128 ("Mejia") (DEC-064)
LOG = "log:popw_V5GL06"  # the primary outcome
SEASONS = ["log:winter_popw_V5GL06", "log:nonwinter_popw_V5GL06"]


# ---------------------------------------------------------------- design table


def himalayan(regions: pd.DataFrame, igp_states: list[str], states: list[str], min_elev: float) -> pd.Series:
    """DEC-147 item 13: a non-north-east centre in J&K, Ladakh or Himachal Pradesh, or in an IGP state at
    or above the IGP plains' elevation limit (the complement of DEC-075's rule within those states)."""
    hills = regions.state.isin(states) | (regions.state.isin(igp_states) & (regions.elevation_m >= min_elev))
    return hills & (regions.region != "north-east")


def design_units() -> pd.DataFrame:
    """Every unit with its roles and cohorts (all fixed at the gate: data/interim/pregate/units.csv)."""
    P = params()
    u = pd.read_csv(PREGATE / "units.csv")
    reg = pd.read_csv(INTERIM / "unit_regions.csv")[["unit_id", "state", "elevation_m"]]
    u = u.merge(reg, on="unit_id", how="left")
    from src.common.paths import CONFIG, load_yaml

    R = load_yaml(CONFIG / "regions.yaml")
    c = P["causal"]
    u["himalayan"] = himalayan(u, R["igp_states"], c["himalayan_states"], c["himalayan_min_elevation_m"])
    gain = pd.read_csv(PREGATE / "monitor_gain.csv")[["unit_id", "gained_monitor"]]
    u = u.merge(gain, on="unit_id", how="left")
    # anticipation (DEC-147 item 10): units holding a city on CPCB's 2017 non-attainment list -> 2018
    cities = pd.read_csv(INTERIM / "ncap_cities.csv")
    on2017 = set(cities.city[cities.in_cpcb_nac_2017.astype(bool)])
    holds = u.ncap_cities.fillna("").str.split(";").map(lambda cs: any(x in on2017 for x in cs if x))
    u["cohort_anticip"] = np.where(holds, 2018, u.cohort_listed)
    u["role_a"] = np.select([u.role == "treated", u.role == "control", u.role.str.startswith("town")],
                            ["treated", "control", "town"], "other")  # fmt: skip
    return u


# ---------------------------------------------------------------- panels


def season_long(month: pd.DataFrame, P: dict) -> pd.DataFrame:
    """Winter / non-winter season panel (DEC-140) as long rows: series, season-year as `year`."""
    s = season_panel(month, P["pregate"]["winter_months"])
    y0, y1 = P["causal"]["season_years"]
    s = s[s.season_year.between(y0, y1)]
    s = s.assign(series=s.season + "_popw_V5GL06", year=s.season_year, value=s.pm25_popw)
    return s[["unit_id", "year", "series", "value"]]


def asansol_alone(years: list[int]) -> pd.DataFrame:
    """Population-weighted V5.GL.06 over Asansol's own GHSL centre (11080) alone (DEC-147 item 6),
    with Phase 3's zonal code (same weights, same exact coverage fractions)."""
    import glob

    import geopandas as gpd

    from src.clean import zonal as Z
    from src.common.paths import raw_dir

    ucdb = gpd.read_file(INTERIM / "ghsl" / "ucdb_india.gpkg")
    poly = ucdb[ucdb.uc_id == params()["causal"]["asansol_alone_ucdb"]][["geometry"]].assign(unit_id=ASANSOL)
    if len(poly) != 1:
        raise ValueError("Asansol's GHSL centre not found in ucdb_india.gpkg")
    pat, var, _ = Z.PRODUCTS["V5GL06"]
    rows, pop = [], None
    for f in sorted(glob.glob(str(raw_dir("acag") / pat))):
        year, _ = Z.period(f)
        if year not in years:
            continue
        da = Z.load_acag(f, var)
        pop = pop or Z._tif(Z.pop_on_grid(da), "pop_asansol_alone")
        z = Z.zonal(poly, Z._tif(da, "value_asansol_alone"), pop)
        rows.append({"unit_id": ASANSOL, "year": year, "value": float(z.pm25_popw.iloc[0])})
    out = pd.DataFrame(rows)
    if sorted(out.year) != sorted(years):
        raise ValueError("Asansol-alone series incomplete")
    return out


def panels() -> None:
    require_gate("Layer A panels (post-2019 satellite outcomes for treated and control units)")
    P = params()
    y0, y1 = P["windows"]["satellite_analysis_years"]
    u = design_units()
    keep = set(u.unit_id[u.role_a.isin(["treated", "control", "town"])])
    ann = pd.read_parquet(PROCESSED / "unit_year_sat.parquet")
    ann = ann[ann.unit_id.isin(keep) & ann.year.between(y0, y1)]
    long = []
    for prod in ("V5GL06", "V6GL03", "V6GL0204"):
        a = ann[ann["product"] == prod]
        long.append(a.assign(series=f"popw_{prod}", value=a.pm25_popw)[["unit_id", "year", "series", "value"]])
        if prod == "V5GL06":
            long.append(a.assign(series="area_V5GL06", value=a.pm25_area)[["unit_id", "year", "series", "value"]])
            alone = asansol_alone(sorted(a.year.unique()))
            b = a.set_index(["unit_id", "year"]).pm25_popw.copy()
            b.loc[list(zip(alone.unit_id, alone.year, strict=True))] = alone.value.to_numpy()
            long.append(b.rename("value").reset_index().assign(series="popw_V5GL06_asansol"))
    mon = pd.read_parquet(PROCESSED / "unit_month_sat.parquet")
    mon = mon[(mon["product"] == "V5GL06") & mon.unit_id.isin(keep) & mon.year.between(y0, y1 + 1)]
    long.append(season_long(mon, P))
    pan = pd.concat(long, ignore_index=True)
    OUT.mkdir(parents=True, exist_ok=True)
    pan.to_parquet(OUT / "panel_annual.parquet", index=False)
    # the 2016 placebo reads through Phase 4's pre-period reader (DEC-145): year <= 2018, asserted
    pre = read_pre_period(PROCESSED / "unit_year_sat.parquet", product="V5GL06",
                          columns=["unit_id", "year", "pm25_popw", "product"])  # fmt: skip
    pre = pre[pre.unit_id.isin(keep) & (pre.year >= y0)]
    pre.assign(series="popw_V5GL06", value=pre.pm25_popw)[["unit_id", "year", "series", "value"]].to_parquet(
        OUT / "panel_pre2019.parquet", index=False
    )
    u.to_csv(OUT / "design_units.csv", index=False)
    print(pan.groupby("series").agg(units=("unit_id", "nunique"), y0=("year", "min"), y1=("year", "max")))


# ---------------------------------------------------------------- specifications


@dataclass
class SdidSpec:
    """One SDID specification (DEC-139/145/146/147/150)."""

    spec_id: str
    label: str
    part: str  # A or B (Reenu's checkpoint split)
    status: str  # registered | added before computing | added after inspecting the data | ...
    treated: pd.DataFrame  # unit_id, cohort, cell
    controls: list[str]
    outcomes: list[str] = field(default_factory=lambda: [LOG])
    panel: str = "panel_annual.parquet"
    years: tuple[int, int] = (2010, 2024)
    drop_years: tuple[int, ...] = (2020,)
    null_design: str = "random"
    keep_curve: bool = False
    keep_weights: bool = False
    leakage: bool = False  # add the gained / not-gained fit sets (log annual only), DEC-146
    note: str = ""
    reps: int = 500  # joint-placebo replications (config causal.placebo_reps)

    def fitsets(self) -> pd.DataFrame:
        rows = []
        cells = sorted(self.treated.cell.unique())
        for g in sorted(self.treated.cohort.unique()):
            rows.append({"fitset": f"all|{g}", "cohort": int(g), "cells": ";".join(cells), "outcomes": ";".join(self.outcomes)})
            if self.leakage:
                for c in cells:
                    rows.append({"fitset": f"{c}|{g}", "cohort": int(g), "cells": c, "outcomes": LOG})
        return pd.DataFrame(rows)

    def estimands(self) -> pd.DataFrame:
        """Estimand = weighted sum over (outcome, fit set) of fit-set ATTs (cohort-size weights)."""
        t = self.treated
        n = t.groupby("cohort").size()
        rows = []
        for o in self.outcomes:  # "att" = the first (headline) outcome; others "att:<outcome>"
            name = "att" if o == self.outcomes[0] else f"att:{o}"
            for g, k in n.items():
                rows.append({"estimand": name, "outcome": o, "fitset": f"all|{g}", "weight": k / n.sum()})
        if set(SEASONS) <= set(self.outcomes):  # H2: winter minus non-winter (DEC-140)
            for g, k in n.items():
                rows.append({"estimand": "winter_minus_nonwinter", "outcome": SEASONS[0], "fitset": f"all|{g}", "weight": k / n.sum()})
                rows.append({"estimand": "winter_minus_nonwinter", "outcome": SEASONS[1], "fitset": f"all|{g}", "weight": -k / n.sum()})
        if self.leakage:
            for c in sorted(t.cell.unique()):
                nc = t[t.cell == c].groupby("cohort").size()
                for g, k in nc.items():
                    rows.append({"estimand": c, "outcome": LOG, "fitset": f"{c}|{g}", "weight": k / nc.sum()})
            a, b = sorted(t.cell.unique())  # gained, notgained
            for c, sign in ((a, 1), (b, -1)):
                nc = t[t.cell == c].groupby("cohort").size()
                for g, k in nc.items():
                    rows.append({"estimand": f"{a}_minus_{b}", "outcome": LOG, "fitset": f"{c}|{g}", "weight": sign * k / nc.sum()})
        return pd.DataFrame(rows)


def _treated(u: pd.DataFrame, mask: pd.Series, cohort_col: str = "cohort_listed", cell: str | pd.Series = "all") -> pd.DataFrame:
    t = u.loc[mask, ["unit_id", cohort_col]].rename(columns={cohort_col: "cohort"})
    t["cohort"] = t.cohort.astype(int)
    t["cell"] = cell[mask].to_numpy() if isinstance(cell, pd.Series) else cell
    return t.reset_index(drop=True)


def restricted_units(pollutant: str = "pm25") -> list[str]:
    """Treated Layer A units with a Layer B panel at the primary settings (DEC-150): the H4 cities."""
    from src.normalise import composition as C

    ch = pd.read_parquet(C.OUT / "city_changes.parquet", columns=["unit_id", "pollutant", "spec", "ncap", "n_panel"])
    ch = ch[(ch.spec == C.PRIMARY.label) & (ch.pollutant == pollutant) & ch.ncap & (ch.n_panel > 0)]
    return sorted(ch.unit_id.unique())


def build_specs() -> list[SdidSpec]:
    P = params()
    u = design_units()
    tr = u.role_a == "treated"
    ctl = sorted(u.unit_id[u.role_a == "control"])
    reps = int(P["causal"]["placebo_reps"])
    gained = np.where(u.gained_monitor.fillna(False).astype(bool), "gained", "notgained")
    gained = pd.Series(gained, index=u.index)
    towns = u.role_a == "town"
    S = [
        # ---- Part A
        SdidSpec("primary", "Primary: V5.GL.06, population-weighted, listing cohorts, never-treated controls, 2020 dropped",
                 "A", "registered", _treated(u, tr, cell=gained), ctl,
                 outcomes=[LOG, "level:popw_V5GL06", *SEASONS], keep_weights=True, leakage=True),
        SdidSpec("v6gl03", "Satellite product V6.GL.03 (rule d)", "A", "registered", _treated(u, tr), ctl,
                 outcomes=["log:popw_V6GL03"]),
        SdidSpec("area", "Area-weighted mean (rule d)", "A", "registered", _treated(u, tr), ctl,
                 outcomes=["log:area_V5GL06"]),
        SdidSpec("placebo2016", "Placebo in time: fake adoption 2016, data to 2018 (rule c; random null)", "A",
                 "registered", _treated(u, tr).assign(cohort=2016), ctl, panel="panel_pre2019.parquet",
                 years=(2010, 2018), drop_years=()),
        SdidSpec("placebo2016_rm", "Placebo in time 2016, region-matched null (information only)", "A",
                 "added before computing", _treated(u, tr).assign(cohort=2016), ctl, panel="panel_pre2019.parquet",
                 years=(2010, 2018), drop_years=(), null_design="region_matched"),
        # ---- Part B (robustness battery and triangulation)
        SdidSpec("v6gl0204", "Satellite vintage V6.GL.02.04 (to 2023)", "B", "registered", _treated(u, tr), ctl,
                 outcomes=["log:popw_V6GL0204"], years=(2010, 2023)),
        SdidSpec("towns", "Towns without a GHSL centre included as 1.87 km buffers", "B", "registered",
                 _treated(u, tr | towns), ctl),
        SdidSpec("towns_nopatancheruvu", "Towns included, Patancheruvu excluded", "B", "registered",
                 _treated(u, (tr | towns) & (u.unit_id != PATANCHERUVU)), ctl),
        SdidSpec("asansol_alone", "Asansol centre alone (without the 'Mejia' centre)", "B", "registered",
                 _treated(u, tr), ctl, outcomes=["log:popw_V5GL06_asansol"]),
        SdidSpec("treated100k", "Treated units with 2015 population >= 100,000 only", "B", "registered",
                 _treated(u, tr & (u.pop_2015 >= P["control_pool"]["min_population"])), ctl),
        SdidSpec("spill25", "Spillover: controls >= 25 km from every NCAP place", "B", "registered",
                 _treated(u, tr), sorted(u.unit_id[(u.role_a == "control") & u.in_buffered_pool.astype(bool)])),
        SdidSpec("funded", "Treatment date = first funding year", "B", "registered",
                 _treated(u, tr, "cohort_funded"), ctl),
        SdidSpec("anticip2018", "Anticipation: units on the 2017 list treated from 2018", "B", "registered",
                 _treated(u, tr, "cohort_anticip"), ctl),
        SdidSpec("incl2020", "2020 included (own per-period coefficient reported)", "B", "registered",
                 _treated(u, tr), ctl, drop_years=(), keep_curve=True),
        SdidSpec("noigp", "Exclude the Indo-Gangetic Plain (treated and controls)", "B", "registered",
                 _treated(u, tr & (u.region != "igp")), sorted(u.unit_id[(u.role_a == "control") & (u.region != "igp")])),
    ]
    rest = restricted_units("pm25")
    rmask = tr & u.unit_id.isin(rest)
    S += [
        SdidSpec("restricted_pm25", "Layer A restricted to units with a Layer B PM2.5 panel (triangulation, figure 1)",
                 "B", "registered", _treated(u, rmask), ctl),
        SdidSpec("restricted_pm25_v6gl0204", "Layer A restricted, V6.GL.02.04 (investigation step 2)", "B",
                 "registered", _treated(u, rmask), ctl, outcomes=["log:popw_V6GL0204"], years=(2010, 2023)),
    ]
    for s in S:
        s.reps = reps
    return S


def _hash(obj) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, default=str).encode()).hexdigest()[:16]


def write_spec_tables(S: list[SdidSpec], regions: pd.Series, base=OUT) -> pd.DataFrame:
    """Write specs.csv, spec_units.parquet, spec_fitsets.csv and spec_estimands.csv under base/specs.
    `regions`: unit_id -> region (for region-matched placebo draws)."""
    pan_hash = {}
    for f in {s.panel for s in S}:
        d = pd.read_parquet(base / f)
        pan_hash[f] = str(int(pd.util.hash_pandas_object(d.sort_values(["series", "unit_id", "year"]), index=False).sum()))
    meta, units, fits, ests = [], [], [], []
    for s in S:
        m = s.treated.assign(role="treated")
        c = pd.DataFrame({"unit_id": s.controls, "cohort": 0, "cell": "", "role": "control"})
        mem = pd.concat([m, c], ignore_index=True)
        mem["region"] = mem.unit_id.map(regions)
        if mem.unit_id.duplicated().any() or mem.region.isna().any():
            raise ValueError(f"{s.spec_id}: duplicated unit or missing region")
        fs = s.fitsets()
        es = s.estimands()
        row = {"spec_id": s.spec_id, "label": s.label, "part": s.part, "status": s.status, "panel": s.panel,
               "outcomes": ";".join(s.outcomes), "year_min": s.years[0], "year_max": s.years[1],
               "drop_years": ";".join(map(str, s.drop_years)), "reps": s.reps, "null_design": s.null_design,
               "keep_curve": s.keep_curve, "keep_weights": s.keep_weights, "note": s.note,
               "n_treated": int(len(m)), "n_controls": int(len(c))}  # fmt: skip
        row["spec_hash"] = _hash([row, mem.sort_values("unit_id").to_dict("records"), fs.to_dict("records"), pan_hash[s.panel]])
        meta.append(row)
        units.append(mem.assign(spec_id=s.spec_id))
        fits.append(fs.assign(spec_id=s.spec_id))
        ests.append(es.assign(spec_id=s.spec_id))
    d = base / "specs"
    d.mkdir(parents=True, exist_ok=True)
    meta = pd.DataFrame(meta)
    meta.to_csv(d / "specs.csv", index=False)
    pd.concat(units, ignore_index=True).to_parquet(d / "spec_units.parquet", index=False)
    pd.concat(fits, ignore_index=True).to_csv(d / "spec_fitsets.csv", index=False)
    pd.concat(ests, ignore_index=True).to_csv(d / "spec_estimands.csv", index=False)
    return meta


def write_specs() -> None:
    meta = write_spec_tables(build_specs(), design_units().set_index("unit_id").region)
    print(meta[["spec_id", "part", "n_treated", "n_controls", "outcomes", "year_min", "year_max", "drop_years"]].to_string(index=False))


# ---------------------------------------------------------------- run and summarise


def run(ids: list[str], loo: bool = False, env_extra: dict | None = None) -> None:
    require_gate("Layer A SDID: " + " ".join(ids))
    env = {**os.environ, "OMP_NUM_THREADS": "1", "OPENBLAS_NUM_THREADS": "1", "MKL_NUM_THREADS": "1", **(env_extra or {})}
    cmd = ["Rscript", "src/causal/sdid.R", *(["--loo"] if loo else []), *ids]
    subprocess.run(cmd, env=env, check=True)


def p_equal_tailed(null: np.ndarray, att: float) -> float:
    """Two-sided permutation p from the empirical null, not assuming it is centred on 0 (DEC-091)."""
    n = len(null)
    lo = (1 + (null <= att).sum()) / (1 + n)
    hi = (1 + (null >= att).sum()) / (1 + n)
    return float(min(1.0, 2 * min(lo, hi)))


def combine(fits: pd.DataFrame, est: pd.DataFrame, by: list[str] | None = None) -> pd.DataFrame:
    """Estimand values from fit-set ATTs: sum of weight x att over (outcome, fitset), per `by` group."""
    by = by or []
    m = fits.merge(est, on=["outcome", "fitset"])
    m["w_att"] = m.weight * m.att
    need = est.groupby("estimand").size()
    g = m.groupby([*by, "estimand"]).agg(value=("w_att", "sum"), parts=("w_att", "size")).reset_index()
    full = g.parts == g.estimand.map(need)
    if not full.all():
        raise ValueError(f"incomplete estimands: {g[~full].head()}")
    return g.drop(columns="parts")


def summarise_spec(spec_id: str, base=OUT) -> pd.DataFrame:
    d = base / "sdid" / spec_id
    est = pd.read_csv(base / "specs" / "spec_estimands.csv")
    est = est[est.spec_id == spec_id].drop(columns="spec_id")
    real = combine(pd.read_parquet(d / "estimates.parquet"), est)
    files = sorted(d.glob("draws_*.parquet"))
    draws = pd.concat([pd.read_parquet(f) for f in files], ignore_index=True) if files else pd.DataFrame()
    z95, z90 = 1.959964, 1.644854
    pl = combine(draws, est, by=["rep"]) if len(draws) else None
    rows = []
    for _, r in real.iterrows():
        row = {"spec_id": spec_id, "estimand": r.estimand, "att": r.value}
        if pl is not None:
            null = pl[pl.estimand == r.estimand].value.to_numpy()
            se = float(np.std(null, ddof=1))
            row.update(se=se, lo95=r.value - z95 * se, hi95=r.value + z95 * se, lo90=r.value - z90 * se,
                       hi90=r.value + z90 * se, p_perm=p_equal_tailed(null, r.value), reps=len(null),
                       null_mean=float(null.mean()))  # fmt: skip
        rows.append(row)
    out = pd.DataFrame(rows)
    fits = pd.read_parquet(d / "estimates.parquet")
    out["warnings_real"] = int(fits.warnings.sum())
    out["warnings_placebo"] = int(draws.warnings.sum()) if len(draws) else 0
    return out


def summarise() -> None:
    require_gate("Layer A summaries")
    specs = pd.read_csv(SPEC_DIR / "specs.csv")
    done = [s for s in specs.spec_id if (SDID_DIR / s / "done.txt").exists()]
    out = pd.concat([summarise_spec(s) for s in done], ignore_index=True)
    out = out.merge(specs[["spec_id", "label", "part", "status", "n_treated", "n_controls"]], on="spec_id")
    out.to_csv(OUT / "sdid_summary.csv", index=False)
    print(out[["spec_id", "estimand", "att", "se", "lo95", "hi95", "reps"]].to_string(index=False))


def main(argv: list[str]) -> None:
    cmd = argv[0] if argv else ""
    if cmd == "panels":
        panels()
    elif cmd == "specs":
        require_gate("Layer A specifications")
        write_specs()
    elif cmd == "run":
        run(argv[1:])
    elif cmd == "loo":
        run(argv[1:], loo=True)
    elif cmd == "summarise":
        summarise()
    else:
        raise SystemExit(__doc__)


if __name__ == "__main__":
    main(sys.argv[1:])

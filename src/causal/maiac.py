"""Phase 8b: the registered raw-AOD check under the calibration-leakage threat (plan §5; DEC-174 to DEC-181,
committed and pushed in `85acc2a` before any AOD value was pulled). GATED (hard rule 4).

H1 is "not identified by this design" (DEC-151); nothing here can change that, and nothing here is an effect of
NCAP. AOD is a column measure, not surface PM2.5: the check reads direction, not size (DEC-180).

    python -m src.causal.maiac panels       raw GEE sums -> unit-month / unit-year AOD, coverage, sample, weight check
    python -m src.causal.maiac specs        SDID specifications -> data/processed/causal/maiac/specs/
    python -m src.causal.maiac run [ids]    Rscript src/causal/sdid.R on the maiac folder (resumable; all specs if none)
    python -m src.causal.maiac event        Sun & Abraham on log AOD (information only)
    python -m src.causal.maiac summarise    estimates and the DEC-180 classifications -> maiac/results.json
"""

import glob
import json
import os
import sys

import numpy as np
import pandas as pd

from src.causal import decisions as D
from src.causal import event_study as E
from src.causal import layer_a as A
from src.common.gate import require_gate
from src.common.paths import CONFIG, PROCESSED, load_yaml, params, raw_dir

CFG = load_yaml(CONFIG / "maiac.yaml")
MOUT = A.OUT / "maiac"
ACAG = "popw_V5GL06"
# series -> (weight, filter, months): DEC-176/177
SERIES = {
    "aod_popw": ("pop", "primary", "all"),
    "aod_popw_nonmonsoon": ("pop", "primary", "nonmonsoon"),
    "aod_area": ("area", "primary", "all"),
    "aod_relaxed": ("pop", "relaxed", "all"),
}
SUM_KEYS = {("pop", "primary"): ("pw_v", "pw_a", "pw_d", "w"), ("area", "primary"): ("ar_v", "ar_a", "ar_d", "px"),
            ("pop", "relaxed"): ("rw_v", "rw_a", "rw_d", "w")}  # fmt: skip


# ---------------------------------------------------------------- unit-month and unit-year values (pure)


def month_measures(sums: pd.DataFrame, weight: str, filt: str, min_cov: float, min_days: float) -> pd.DataFrame:
    """Unit-month AOD mean, coverage and weighted valid days from the exported sums (DEC-176/177)."""
    v, a, d, tot = SUM_KEYS[(weight, filt)]
    out = sums[["unit_id", "year", "month"]].copy()
    with np.errstate(divide="ignore", invalid="ignore"):
        out["aod"] = np.where(sums[v] > 0, sums[a] / sums[v], np.nan)
        out["coverage"] = np.where(sums[tot] > 0, sums[v] / sums[tot], 0.0)
        out["days"] = np.where(sums[tot] > 0, sums[d] / sums[tot], 0.0)
    out["valid"] = (out.coverage >= min_cov) & (out.days >= min_days) & out.aod.notna()
    return out


def annual(m: pd.DataFrame, monsoon: list[int], min_nm: int, months: str) -> pd.DataFrame:
    """Unit-year value from the valid monthly means (DEC-177). A year is valid with >= min_nm valid non-monsoon
    months; `months` = 'all' (primary: every valid month) or 'nonmonsoon'."""
    m = m.assign(nm=~m.month.isin(monsoon))
    g = m.groupby(["unit_id", "year"])
    n_nm = g.apply(lambda x: int((x.valid & x.nm).sum()), include_groups=False).rename("n_nonmonsoon_valid")
    use = m[m.valid & (m.nm if months == "nonmonsoon" else True)]
    val = use.groupby(["unit_id", "year"]).aod.mean().rename("value")
    n_used = use.groupby(["unit_id", "year"]).size().rename("months_used")
    y = pd.concat([n_nm, val, n_used], axis=1).reset_index()
    y["months_used"] = y.months_used.fillna(0).astype(int)
    y["valid"] = y.n_nonmonsoon_valid >= min_nm
    y.loc[~y.valid, "value"] = np.nan
    return y


def complete_units(y: pd.DataFrame, years: list[int]) -> set[str]:
    """Units valid in every analysis year (DEC-177; SDID needs a balanced panel)."""
    ok = y[y.year.isin(years) & y.valid].groupby("unit_id").year.nunique()
    return set(ok.index[ok == len(years)])


def analysis_years() -> list[int]:
    y0, y1 = params()["windows"]["satellite_analysis_years"]
    return [y for y in range(y0, y1 + 1) if y not in params()["causal"]["years_drop"]]


# ---------------------------------------------------------------- panels


def read_raw() -> pd.DataFrame:
    files = sorted(glob.glob(str(raw_dir("maiac_gee") / "maiac_unit_month_*.csv")))
    y0, y1 = CFG["years"]
    if len(files) != y1 - y0 + 1:
        raise FileNotFoundError(f"expected {y1 - y0 + 1} yearly MAIAC tables in data/raw/maiac_gee, found {len(files)}")
    d = pd.concat([pd.read_csv(f) for f in files], ignore_index=True)
    if d.duplicated(["unit_id", "year", "month"]).any():
        raise ValueError("duplicate unit-months in the raw MAIAC tables")
    n = d.groupby("year").size()
    if (n != 1036 * 12).any():
        raise ValueError(f"raw MAIAC tables are incomplete: {n[n != 1036 * 12].to_dict()}")
    return d.sort_values(["unit_id", "year", "month"]).reset_index(drop=True)


def weight_check(raw: pd.DataFrame) -> dict:
    """DEC-176: GEE population weights per unit against Phase 3's GHS-POP 30-arc-second sums; stop above 10%."""
    gee = raw.groupby("unit_id").w.first()
    loc = pd.read_parquet(PROCESSED / "unit_year_sat.parquet", columns=["unit_id", "product", "year", "pop"])
    loc = loc[(loc["product"] == "V5GL06")].groupby("unit_id")["pop"].first()
    j = pd.concat([gee.rename("gee"), loc.rename("local")], axis=1, join="inner")
    diff = 100 * (j.gee / j.local - 1)
    res = {"units": int(len(j)), "median_abs_pct": float(diff.abs().median()), "p90_abs_pct": float(diff.abs().quantile(0.9)),
           "median_pct": float(diff.median()), "corr_log": float(np.corrcoef(np.log(j.gee.clip(lower=1)), np.log(j.local.clip(lower=1)))[0, 1]),
           "zero_weight_units": int((gee <= 0).sum()), "limit_pct": CFG["weight_check_max_median_abs_pct"]}  # fmt: skip
    res["passed"] = res["median_abs_pct"] <= res["limit_pct"]
    return res


def panels() -> None:
    require_gate("Phase 8b AOD panels (post-2019 AOD for treated and control units)")
    MOUT.mkdir(parents=True, exist_ok=True)
    raw = read_raw()
    wc = weight_check(raw)
    (MOUT / "weight_check.json").write_text(json.dumps(wc, indent=2), encoding="utf-8")
    if not wc["passed"]:
        raise SystemExit(f"weight check failed (median |diff| {wc['median_abs_pct']:.1f}% > {wc['limit_pct']}%): stop and tell Reenu (DEC-176)")
    years = analysis_years()
    months, years_t, long = [], [], []
    for series, (weight, filt, mo) in SERIES.items():
        m = month_measures(raw, weight, filt, CFG["month_min_coverage"], CFG["month_min_days"])
        y = annual(m, CFG["monsoon_months"], CFG["year_min_nonmonsoon_months"], mo)
        if mo == "all":
            months.append(m.assign(weight=weight, filter=filt))
        years_t.append(y.assign(series=series))
        keep = complete_units(y, years)
        v = y[y.unit_id.isin(keep) & y.valid]
        if (v.value <= 0).any():
            raise SystemExit(f"{series}: a unit-year AOD mean is <= 0; the log is undefined (DEC-175): stop and tell Reenu")
        long.append(v.assign(series=series)[["unit_id", "year", "series", "value"]])
    pan7 = pd.read_parquet(A.OUT / "panel_annual.parquet")
    long.append(pan7[pan7.series == ACAG][["unit_id", "year", "series", "value"]])
    pd.concat(long, ignore_index=True).to_parquet(MOUT / "panel_aod.parquet", index=False)
    pd.concat(months, ignore_index=True).to_parquet(MOUT / "unit_month.parquet", index=False)
    yt = pd.concat(years_t, ignore_index=True)
    yt.to_parquet(MOUT / "unit_year.parquet", index=False)
    # sample table: one row per Layer A unit, completeness per series (DEC-177)
    u = A.design_units()
    u = u[u.role_a.isin(["treated", "control"])][["unit_id", "role_a", "cohort_listed", "region", "gained_monitor"]].copy()
    for series in SERIES:
        u[f"complete_{series}"] = u.unit_id.isin(complete_units(yt[yt.series == series], years))
    u.to_csv(MOUT / "sample.csv", index=False)
    # valid-month shares by calendar month and region (primary series' months)
    m = months[0].merge(u[["unit_id", "region"]], on="unit_id")
    m.groupby(["region", "month"]).valid.mean().rename("share_valid").reset_index().to_csv(MOUT / "coverage_by_month.csv", index=False)
    print(json.dumps(wc, indent=2))
    print(u.groupby("role_a")[[f"complete_{s}" for s in SERIES]].sum().to_string())


# ---------------------------------------------------------------- specifications


def build_specs() -> tuple[list, dict]:
    """DEC-179. Returns the specs and, per AOD spec, its ACAG yardstick spec id."""
    u = A.design_units()
    s = pd.read_csv(MOUT / "sample.csv")
    u = u.merge(s[["unit_id", *[c for c in s.columns if c.startswith("complete_")]]], on="unit_id", how="left")
    tr, ctl = u.role_a == "treated", u.role_a == "control"
    gained = pd.Series(np.where(u.gained_monitor.fillna(False).astype(bool), "gained", "notgained"), index=u.index)
    min_g = params()["robustness"]["leakage_min_units"]
    reps = int(params()["causal"]["placebo_reps"])
    rest = set(A.restricted_units("pm25"))
    S, yard = [], {}

    def pair(sid, label, series, keep, tmask=None, split=False):
        t = tr & keep & (tmask if tmask is not None else True)
        c = sorted(u.unit_id[ctl & keep])
        split = split and all((gained[t] == g).sum() >= min_g for g in ("gained", "notgained"))
        cell = gained if split else "all"
        S.append(A.SdidSpec(sid, label, "8b", "registered (details DEC-179)", A._treated(u, t, cell=cell), c,
                            outcomes=[f"log:{series}"], panel="panel_aod.parquet", leakage=split))  # fmt: skip
        return t, c, split

    # 1 + 2: the classified pair (DEC-180), with the monitor-gain split
    k = u.complete_aod_popw.astype(bool)
    pair("aod_primary", "Raw MAIAC AOD, population-weighted, best-quality QA, all valid months (log AOD)", "aod_popw", k, split=True)
    pair("acag_aod_sample", "ACAG V5.GL.06 PM2.5 on the units of the AOD primary (yardstick)", ACAG, k, split=True)
    yard["aod_primary"] = "acag_aod_sample"
    base_t = set(S[0].treated.unit_id) | set(S[0].controls)
    # 3-6: sensitivities (overall estimate; Q1 for information), each with its own ACAG yardstick if its units differ
    for sid, label, series, tmask in (
        ("aod_nonmonsoon", "Raw MAIAC AOD, non-monsoon annual mean (Jan-May, Oct-Dec)", "aod_popw_nonmonsoon", None),
        ("aod_area", "Raw MAIAC AOD, area-weighted", "aod_area", None),
        ("aod_relaxed", "Raw MAIAC AOD, relaxed QA filter", "aod_relaxed", None),
        ("aod_restricted", "Raw MAIAC AOD, treated units with a Layer B PM2.5 panel (investigation step 2)", "aod_popw", u.unit_id.isin(rest)),
    ):  # fmt: skip
        keep = u[f"complete_{series}"].astype(bool)
        t, c, _ = pair(sid, label, series, keep, tmask)
        if sid != "aod_restricted" and set(u.unit_id[t]) | set(c) == base_t:
            yard[sid] = "acag_aod_sample"
        else:
            pair(f"acag_{sid}", f"ACAG V5.GL.06 PM2.5 on the units of {sid} (yardstick)", ACAG, keep, tmask)
            yard[sid] = f"acag_{sid}"
    for x in S:
        x.reps = reps
    return S, yard


def specs() -> None:
    require_gate("Phase 8b AOD specifications")
    S, yard = build_specs()
    meta = A.write_spec_tables(S, A.design_units().set_index("unit_id").region, base=MOUT)
    (MOUT / "specs" / "yardsticks.json").write_text(json.dumps(yard, indent=2), encoding="utf-8")
    print(meta[["spec_id", "n_treated", "n_controls", "outcomes"]].to_string(index=False))


def run(ids: list[str]) -> None:
    ids = ids or list(pd.read_csv(MOUT / "specs" / "specs.csv").spec_id)
    A.run(ids, env_extra={"NCAP_CAUSAL_DIR": MOUT.relative_to(A.OUT.parents[2]).as_posix()})
    specs_t = pd.read_csv(MOUT / "specs" / "specs.csv")
    if all((MOUT / "sdid" / s / "done.txt").exists() for s in specs_t.spec_id):
        (MOUT / "sdid" / "all.done").write_text("\n".join(specs_t.spec_id) + "\n", encoding="utf-8")  # Snakemake flag


# ---------------------------------------------------------------- event study (information only, DEC-179)


def event() -> None:
    require_gate("Phase 8b AOD event study")
    P = params()["causal"]
    window = tuple(P["event_window"])
    sp = pd.read_parquet(MOUT / "specs" / "spec_units.parquet")
    mem = sp[sp.spec_id == "aod_primary"]
    pan = pd.read_parquet(MOUT / "panel_aod.parquet")
    pan = pan[(pan.series == "aod_popw") & pan.unit_id.isin(mem.unit_id) & ~pan.year.isin(P["years_drop"])]
    era = pd.read_parquet(A.OUT / "era5_unit_year.parquet")
    d = pan.merge(era, on=["unit_id", "year"], how="left", validate="one_to_one")
    if d[E.COVARS].isna().any().any():
        raise ValueError("ERA5 covariates missing for some unit-years")
    u = pd.read_csv(A.OUT / "design_units.csv")[["unit_id", "region"]]
    d = d.merge(u, on="unit_id").merge(mem[["unit_id", "cohort"]], on="unit_id")
    d["y"] = np.log(d.value)
    sizes = d[d.cohort > 0].groupby("cohort").unit_id.nunique()
    dd, meta = E.sa_design(d)
    b, V, f = E.fit(dd, meta, E.COVARS)
    t, cov = E.aggregate(b, V, meta, sizes, window)
    res = {"name": "es_aod", "n_obs": int(f._N), "n_units": int(d.unit_id.nunique()),
           "cohort_sizes": {int(k): int(v) for k, v in sizes.items()},
           "references": meta[meta.kind == "ref"][["cohort", "rel"]].to_dict("records"),
           "wald_pre": E.wald(t, cov, list(range(window[0], -1))), "avg_post": E.average(t, cov, list(range(0, window[1] + 1)))}  # fmt: skip
    (MOUT / "event_study").mkdir(parents=True, exist_ok=True)
    t.to_csv(MOUT / "event_study" / "es_aod_coefs.csv", index=False)
    (MOUT / "event_study" / "es_aod_meta.json").write_text(json.dumps(res, indent=2, default=float), encoding="utf-8")
    print("AOD event study: Wald pre p =", round(res["wald_pre"]["p"], 4), "| avg post", round(res["avg_post"]["coef"], 4))


# ---------------------------------------------------------------- summary and classification (DEC-180)


def summarise() -> None:
    require_gate("Phase 8b AOD summaries")
    specs_t = pd.read_csv(MOUT / "specs" / "specs.csv")
    done = [s for s in specs_t.spec_id if (MOUT / "sdid" / s / "done.txt").exists()]
    if set(done) != set(specs_t.spec_id):
        raise SystemExit(f"SDID not finished for: {sorted(set(specs_t.spec_id) - set(done))}")
    s = pd.concat([A.summarise_spec(x, base=MOUT) for x in done], ignore_index=True)
    s = s.merge(specs_t[["spec_id", "label", "n_treated", "n_controls"]], on="spec_id")
    s.to_csv(MOUT / "sdid_summary.csv", index=False)
    S = s.set_index(["spec_id", "estimand"])
    yard = json.loads((MOUT / "specs" / "yardsticks.json").read_text(encoding="utf-8"))
    units = pd.read_parquet(MOUT / "specs" / "spec_units.parquet")
    min_g = params()["robustness"]["leakage_min_units"]

    def tri(sid, est="att"):
        r = S.loc[(sid, est)]
        return (float(r.att), float(r.lo95), float(r.hi95))

    out = {"specs": {}, "limited_coverage": None}
    n_tr = int((units[(units.spec_id == "aod_primary")].role == "treated").sum())
    out["limited_coverage"] = n_tr < CFG["min_kept_treated_share"] * 113
    for sid, ysid in yard.items():
        a, p = tri(sid), tri(ysid)
        rec = {"yardstick": ysid, "aod": a, "acag": p, "se": float(S.loc[(sid, "att")].se),
               "q1": D.aod_q1(a, p), "n_treated": int(S.loc[(sid, "att")].n_treated), "n_controls": int(S.loc[(sid, "att")].n_controls)}  # fmt: skip
        if (sid, "gained_minus_notgained") in S.index and (ysid, "gained_minus_notgained") in S.index:
            mem = units[(units.spec_id == sid) & (units.role == "treated")]
            n_g, n_n = int((mem.cell == "gained").sum()), int((mem.cell == "notgained").sum())
            rec.update(gained=tri(sid, "gained"), notgained=tri(sid, "notgained"), diff=tri(sid, "gained_minus_notgained"),
                       diff_se=float(S.loc[(sid, "gained_minus_notgained")].se),
                       acag_gained=tri(ysid, "gained"), acag_notgained=tri(ysid, "notgained"), acag_diff=tri(ysid, "gained_minus_notgained"),
                       n_gained=n_g, n_notgained=n_n,
                       q2=D.aod_q2(tri(sid, "gained_minus_notgained"), tri(ysid, "gained_minus_notgained"), n_g, n_n, min_g))  # fmt: skip
        else:
            rec["q2"] = {"code": "not_estimated", "label": "not estimated for this specification (DEC-179: Q2 uses the primary's split)"}
        out["specs"][sid] = rec
    es = MOUT / "event_study" / "es_aod_meta.json"
    if es.exists():
        out["event_study"] = json.loads(es.read_text(encoding="utf-8"))
    (MOUT / "results.json").write_text(json.dumps(out, indent=2, default=float), encoding="utf-8")
    r = out["specs"]["aod_primary"]
    print("Q1:", r["q1"]["label"], "| Q2:", r["q2"]["label"])


def main(argv: list[str]) -> None:
    cmd = argv[0] if argv else ""
    if cmd == "panels":
        panels()
    elif cmd == "specs":
        specs()
    elif cmd == "run":
        run(argv[1:])
    elif cmd == "event":
        event()
    elif cmd == "summarise":
        summarise()
    else:
        raise SystemExit(__doc__)


if __name__ == "__main__":
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    main(sys.argv[1:])

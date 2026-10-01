"""Tests for Phase 7 (causal analysis, RQ3): src/causal/layer_a.py, sdid.R, event_study.py, decisions.py
and layer_b.py (DEC-139 to DEC-150). SYNTHETIC DATA ONLY: every panel below is made up, with a known
effect planted in it, to check that an estimator or a rule does what DECISIONS says. None of it is real
air-quality data, and nothing is written under data/."""

import shutil
import subprocess

import numpy as np
import pandas as pd
import pytest

from src.causal import layer_a as A

needs_r = pytest.mark.skipif(shutil.which("Rscript") is None, reason="Rscript not on PATH")


# ---------------------------------------------------------------- synthetic Layer A panel


def synthetic_panel(effect: float = -0.10, n_ctl: int = 60, cohorts=((2019, 8), (2021, 4)), seed: int = 1):
    """Log PM2.5-like panel 2010-2024: unit level + common year shocks + noise, and `effect` (log units)
    added to treated units from their cohort year on. Returns (long panel of levels, treated table)."""
    rng = np.random.default_rng(seed)
    years = np.arange(2010, 2025)
    shocks = rng.normal(0, 0.05, len(years)).cumsum()
    rows, treated = [], []
    units = [(f"c{i:03d}", 0) for i in range(n_ctl)]
    for g, n in cohorts:
        units += [(f"t{g}_{i}", g) for i in range(n)]
    for uid, g in units:
        level = rng.normal(4.0, 0.3)
        y = level + shocks + rng.normal(0, 0.02, len(years))
        if g:
            y = y + effect * (years >= g)
            treated.append({"unit_id": uid, "cohort": g, "cell": "all"})
        rows += [{"unit_id": uid, "year": int(t), "series": "popw_V5GL06", "value": float(np.exp(v))}
                 for t, v in zip(years, y, strict=True)]  # fmt: skip
    return pd.DataFrame(rows), pd.DataFrame(treated)


def test_estimands_weight_cohorts_by_size_and_difference_sums_to_zero():
    t = pd.DataFrame({"unit_id": [f"u{i}" for i in range(10)], "cohort": [2019] * 6 + [2021] * 4,
                      "cell": ["gained"] * 4 + ["notgained"] * 2 + ["gained"] * 1 + ["notgained"] * 3})  # fmt: skip
    s = A.SdidSpec("x", "x", "A", "registered", t, ["c1"], outcomes=[A.LOG, "level:popw_V5GL06", *A.SEASONS], leakage=True)
    e = s.estimands()
    att = e[(e.estimand == "att") & (e.outcome == A.LOG)].set_index("fitset").weight
    assert att.to_dict() == pytest.approx({"all|2019": 0.6, "all|2021": 0.4})
    assert e[e.estimand == "gained_minus_notgained"].weight.sum() == pytest.approx(0.0)
    assert e[e.estimand == "winter_minus_nonwinter"].weight.sum() == pytest.approx(0.0)
    assert set(e[e.outcome == "level:popw_V5GL06"].estimand) <= {"att:level:popw_V5GL06"}  # never summed across outcomes
    assert e.groupby("estimand").outcome.nunique().drop("winter_minus_nonwinter").eq(1).all()
    g = e[e.estimand == "gained"].set_index("fitset").weight
    assert g.to_dict() == pytest.approx({"gained|2019": 0.8, "gained|2021": 0.2})
    fs = s.fitsets()
    assert set(fs.fitset) == {"all|2019", "all|2021", "gained|2019", "gained|2021", "notgained|2019", "notgained|2021"}
    assert (fs[fs.fitset.str.startswith("gained")].outcomes == A.LOG).all()  # leakage on the primary outcome only


def test_combine_refuses_incomplete_estimands():
    est = pd.DataFrame({"estimand": ["att", "att"], "outcome": ["o", "o"], "fitset": ["a", "b"], "weight": [0.5, 0.5]})
    fits = pd.DataFrame({"outcome": ["o", "o"], "fitset": ["a", "b"], "att": [-0.2, 0.0]})
    assert A.combine(fits, est).value.iloc[0] == pytest.approx(-0.1)
    with pytest.raises(ValueError):
        A.combine(fits.iloc[:1], est)


def test_permutation_p_is_equal_tailed():
    null = np.linspace(-1, 1, 99)
    assert A.p_equal_tailed(null, 0.0) == pytest.approx(1.0)
    assert A.p_equal_tailed(null, -2.0) == pytest.approx(2 / 100)
    assert A.p_equal_tailed(null + 5, 0.0) == pytest.approx(2 / 100)  # a null not centred on 0


def test_himalayan_rule():
    r = pd.DataFrame({"state": ["Himachal Pradesh", "Uttarakhand", "Uttarakhand", "Punjab", "Sikkim", "Kerala"],
                      "elevation_m": [900, 700, 290, 250, 1500, 2000],
                      "region": ["peninsular/other", "peninsular/other", "igp", "igp", "north-east", "peninsular/other"]})  # fmt: skip
    got = A.himalayan(r, ["Punjab", "Uttarakhand"], ["Jammu & Kashmir", "Ladakh", "Himachal Pradesh"], 350)
    assert got.tolist() == [True, True, False, False, False, False]


@needs_r
def test_sdid_engine_recovers_a_planted_effect_with_2020_dropped(tmp_path, monkeypatch):
    """sdid.R end to end on a synthetic panel: per-cohort fits, cohort-size aggregation, joint placebo."""
    monkeypatch.setattr("src.causal.layer_a.require_gate", lambda what: None)
    pan, tr = synthetic_panel(effect=-0.10)
    pan.to_parquet(tmp_path / "panel_annual.parquet", index=False)
    ctl = sorted(pan.unit_id[pan.unit_id.str.startswith("c")].unique())
    spec = A.SdidSpec("syn", "synthetic", "A", "test", tr, ctl, reps=20)
    regions = pd.Series("igp", index=pan.unit_id.unique())
    A.write_spec_tables([spec], regions, base=tmp_path)
    A.run(["syn"], env_extra={"NCAP_CAUSAL_DIR": str(tmp_path), "NCAP_WORKERS": "2"})
    est = pd.read_parquet(tmp_path / "sdid" / "syn" / "estimates.parquet")
    assert set(est.fitset) == {"all|2019", "all|2021"}
    # 2020 dropped: 2019 cohort has 9 pre-years (2010-2018), 2021 cohort 10 (2010-2019)
    assert est.set_index("fitset").T0.to_dict() == {"all|2019": 9, "all|2021": 10}
    s = A.summarise_spec("syn", base=tmp_path).set_index("estimand").loc["att"]
    assert s.att == pytest.approx(-0.10, abs=0.02)
    assert s.reps == 20 and 0 < s.se < 0.05
    assert s.hi95 < 0  # a planted 10% fall is detected
    # placebo replications re-estimate on control units only: centred near 0
    assert abs(s.null_mean) < 0.02
    # resumable: a second run recomputes nothing
    before = sorted(p.stat().st_mtime for p in (tmp_path / "sdid" / "syn").glob("draws_*.parquet"))
    A.run(["syn"], env_extra={"NCAP_CAUSAL_DIR": str(tmp_path), "NCAP_WORKERS": "2"})
    after = sorted(p.stat().st_mtime for p in (tmp_path / "sdid" / "syn").glob("draws_*.parquet"))
    assert before == after


@needs_r
def test_sdid_engine_null_effect_gives_ci_covering_zero(tmp_path, monkeypatch):
    monkeypatch.setattr("src.causal.layer_a.require_gate", lambda what: None)
    pan, tr = synthetic_panel(effect=0.0, seed=7)
    pan.to_parquet(tmp_path / "panel_annual.parquet", index=False)
    ctl = sorted(pan.unit_id[pan.unit_id.str.startswith("c")].unique())
    spec = A.SdidSpec("noeffect", "synthetic", "A", "test", tr, ctl, reps=20)
    A.write_spec_tables([spec], pd.Series("igp", index=pan.unit_id.unique()), base=tmp_path)
    A.run(["noeffect"], env_extra={"NCAP_CAUSAL_DIR": str(tmp_path), "NCAP_WORKERS": "2"})
    s = A.summarise_spec("noeffect", base=tmp_path).set_index("estimand").loc["att"]
    # one synthetic draw: a 95% CI misses 0 one time in twenty, so test the size of the estimate instead
    assert abs(s.att) < 0.02 and abs(s.att) < 3 * s.se


def test_rscript_present_for_engine():
    """Guard: the engine's tests above are skipped, not silently passed, without R."""
    if shutil.which("Rscript") is None:
        pytest.skip("Rscript not on PATH")
    out = subprocess.run(["Rscript", "-e", "cat(requireNamespace('synthdid', quietly=TRUE))"],
                         capture_output=True, text=True, timeout=120)  # fmt: skip
    assert "TRUE" in out.stdout


# ---------------------------------------------------------------- event study (Sun & Abraham)


def synthetic_es(drop_2020: bool = True, seed: int = 3):
    """Synthetic panel: cohorts 2019 (30 units) and 2021 (10), 100 never-treated, 2 regions with their own
    year shocks, one covariate. Effects: cohort 2019 d_l = -0.05 (l + 1) from l = 0; cohort 2021 -0.10
    flat from l = 0; nothing before adoption. A 2020 shock of -0.3 hits treated units only."""
    from src.causal import event_study as E

    rng = np.random.default_rng(seed)
    years = [y for y in range(2010, 2025) if not (drop_2020 and y == 2020)]
    rows = []
    shocks = {r: dict(zip(years, rng.normal(0, 0.05, len(years)), strict=True)) for r in ("a", "b")}
    units = [(f"c{i}", 0) for i in range(100)] + [(f"t19_{i}", 2019) for i in range(30)] + [(f"t21_{i}", 2021) for i in range(10)]
    for k, (uid, g) in enumerate(units):
        reg, lvl = ("a" if k % 2 else "b"), rng.normal(4, 0.3)
        for y in years:
            x = rng.normal()
            eff = 0.0
            if g == 2019 and y >= g:
                eff = -0.05 * (y - g + 1)
            if g == 2021 and y >= g:
                eff = -0.10
            if g and y == 2020:
                eff += -0.3
            rows.append({"unit_id": uid, "year": y, "cohort": g, "region": reg, "x": x,
                         "y": lvl + shocks[reg][y] + 0.2 * x + eff + rng.normal(0, 0.01)})  # fmt: skip
    return E, pd.DataFrame(rows)


def test_event_study_recovers_cohort_weighted_dynamics_with_2020_dropped():
    E, d = synthetic_es()
    sizes = d[d.cohort > 0].groupby("cohort").unit_id.nunique()
    dd, meta = E.sa_design(d)
    refs = meta[meta.kind == "ref"].set_index("cohort").rel.to_dict()
    assert refs == {2019: -1, 2021: -2}  # 2021's l = -1 is 2020, which is dropped
    b, V, _ = E.fit(dd, meta, ["x"])
    t, cov = E.aggregate(b, V, meta, sizes, (-9, 5))
    c = t.set_index("rel").coef
    assert c[0] == pytest.approx(0.75 * -0.05 + 0.25 * -0.10, abs=0.01)  # both cohorts observed at l = 0
    assert c[1] == pytest.approx(-0.10, abs=0.01)  # l = +1: cohort 2019's is 2020 (dropped) -> 2021 only
    assert c[5] == pytest.approx(-0.30, abs=0.01)  # l = +5: cohort 2019 only
    assert t.set_index("rel").cohorts[-2] == "2019"  # cohort 2021 is not counted at its own reference
    assert -1 not in set(t.rel)
    w = E.wald(t, cov, list(range(-9, -1)))
    # one draw: a correctly sized test still rejects 1 time in 10 (its size was checked on seeded
    # panels in Phase 7, DEC-152), so test the algebra and only rule out a gross failure
    bb = t.set_index("rel").coef.loc[w["rels"]].to_numpy()
    assert w["stat"] == pytest.approx(float(bb @ np.linalg.inv(cov.loc[w["rels"], w["rels"]].to_numpy()) @ bb))
    assert w["df"] == 8 and w["p"] > 0.01
    avg = E.average(t, cov, list(range(0, 6)))
    assert avg["coef"] == pytest.approx(c.loc[0:5].mean())


def test_event_study_detects_a_planted_pre_trend():
    E, d = synthetic_es(seed=4)
    d.loc[(d.cohort == 2019) & (d.year < 2019), "y"] += 0.02 * (d.year - 2018)  # treated drift up to adoption
    sizes = d[d.cohort > 0].groupby("cohort").unit_id.nunique()
    dd, meta = E.sa_design(d)
    b, V, _ = E.fit(dd, meta, ["x"])
    t, cov = E.aggregate(b, V, meta, sizes, (-9, 5))
    assert E.wald(t, cov, list(range(-9, -1)))["p"] < 0.10


def test_event_study_own_2020_coefficient_is_separate():
    E, d = synthetic_es(drop_2020=False)
    sizes = d[d.cohort > 0].groupby("cohort").unit_id.nunique()
    dd, meta = E.sa_design(d, own_years=(2020,))
    assert meta[meta.kind == "ref"].set_index("cohort").rel.to_dict() == {2019: -1, 2021: -2}
    b, V, _ = E.fit(dd, meta, ["x"])
    own, _ = E.aggregate(b, V, meta, sizes, (-9, 5), kind="own")
    # 2020 for cohort 2019 (l = +1): -0.10 effect - 0.3 shock; for cohort 2021 (pre): -0.3 shock
    want = 0.75 * (-0.10 - 0.3) + 0.25 * -0.3
    assert own.set_index("year").coef[2020] == pytest.approx(want, abs=0.01)
    t, _ = E.aggregate(b, V, meta, sizes, (-9, 5))
    assert t.set_index("rel").coef[5] == pytest.approx(-0.30, abs=0.01)  # 2020 does not leak into l's


# ---------------------------------------------------------------- decision rules (DEC-135, DEC-141)


def test_h1_verdict_branches():
    from src.causal import decisions as D

    ok = dict(wald_p=0.5, placebo_lo=-0.01, placebo_hi=0.01, d_points={"CS": -0.02, "area": -0.01, "V6": -0.03})
    r = D.h1_verdict(-0.05, -0.08, -0.02, -0.075, -0.025, **ok)
    assert r["code"] == "supported" and r["a"] and r["d"]
    r = D.h1_verdict(-0.05, -0.08, -0.02, -0.075, -0.025, **{**ok, "d_points": {"CS": 0.01, "area": -0.01, "V6": -0.03}})
    assert r["code"] == "sign_not_robust" and r["d_failed"] == ["CS"]
    r = D.h1_verdict(0.05, 0.02, 0.08, 0.025, 0.075, **ok)
    assert r["code"] == "increase"
    r = D.h1_verdict(-0.01, -0.03, 0.01, -0.027, 0.007, **ok)
    assert r["code"] == "no_detectable_effect" and r["equivalent"] and "ruled out" in r["verdict"]
    r = D.h1_verdict(-0.03, -0.07, 0.01, -0.06, 0.002, **ok)
    assert r["code"] == "no_detectable_effect" and not r["equivalent"] and "inconclusive" in r["verdict"]
    # (b) or (c) failing overrides everything, even a significant reduction
    r = D.h1_verdict(-0.05, -0.08, -0.02, -0.075, -0.025, **{**ok, "wald_p": 0.05})
    assert r["code"] == "not_identified" and "(b)" in r["verdict"]
    r = D.h1_verdict(-0.05, -0.08, -0.02, -0.075, -0.025, **{**ok, "placebo_lo": 0.001})
    assert r["code"] == "not_identified" and "(c)" in r["verdict"]
    r = D.h1_verdict(-0.05, -0.08, -0.02, -0.075, -0.025, **{**ok, "wald_p": 0.10})
    assert not r["b"]  # registered: p > 0.10, so exactly 0.10 fails


def test_equivalence_uses_the_registered_asymmetric_bounds():
    from src.causal import decisions as D

    assert D.equivalence(-0.05, 0.048)  # ln 0.95 = -0.0513, ln 1.05 = +0.0488
    assert not D.equivalence(-0.052, 0.0)
    assert not D.equivalence(0.0, 0.049)


def test_target_exclusions_and_pct():
    from src.causal import decisions as D

    t = D.target_exclusions(-0.30, -0.10)  # lower bound -0.30 = a 25.9% reduction
    assert t == {20: False, 30: True, 40: True}
    assert D.pct(np.log(0.9)) == pytest.approx(-10.0)


def test_leakage_warning_rules():
    from src.causal import decisions as D

    assert D.leakage_warning((-0.05, -0.08, -0.02), (-0.01, -0.04, 0.02), (-0.04, -0.09, 0.01))[0]
    assert D.leakage_warning((-0.02, -0.05, 0.01), (0.0, -0.03, 0.03), (-0.04, -0.07, -0.01))[0]
    assert not D.leakage_warning((-0.05, -0.08, -0.02), (-0.04, -0.07, -0.01), (-0.01, -0.05, 0.03))[0]


def test_layer_categories_follow_the_fixed_order():
    from src.causal import decisions as D

    assert D.layer_category((-0.05, -0.08, -0.02), (-0.04, -0.20, 0.10)) == "uninformative"
    assert D.layer_category((-0.05, -0.08, -0.02), (0.10, 0.02, 0.18)) == "conflict"
    assert D.layer_category((-0.05, -0.08, -0.02), (-0.07, -0.12, -0.03)) == "consistent"
    assert D.layer_category((-0.05, -0.08, -0.02), (-0.30, -0.40, -0.20)) == "different magnitude"
    # opposite signs, neither CI excludes 0, and B's CI does not contain A's estimate
    assert D.layer_category((-0.05, -0.12, 0.02), (0.02, -0.01, 0.05)) == "unclassified"
    # uninformative wins over conflict when it applies
    assert D.layer_category((-0.05, -0.08, -0.02), (0.01, -0.10, 0.12)) == "uninformative"


def test_robustness_agrees():
    from src.causal import decisions as D

    assert D.agrees(-0.05, -0.08, -0.02, -0.03)
    assert not D.agrees(-0.05, -0.08, -0.02, -0.01)  # outside the primary CI
    assert not D.agrees(-0.01, -0.03, 0.01, 0.005)  # opposite sign, though inside the CI


@needs_r
def test_cs_did_recovers_planted_effect_with_2020_dropped(tmp_path):
    pan, tr = synthetic_panel(effect=-0.10, seed=11)
    pan.to_parquet(tmp_path / "panel_annual.parquet", index=False)
    u = pd.DataFrame({"unit_id": pan.unit_id.unique()})
    u["role_a"] = np.where(u.unit_id.str.startswith("t"), "treated", "control")
    u["cohort_listed"] = u.unit_id.map(tr.set_index("unit_id").cohort)
    u.to_csv(tmp_path / "design_units.csv", index=False)
    out = subprocess.run(["Rscript", "src/causal/cs_did.R", str(tmp_path)], capture_output=True, text=True, timeout=900)
    assert out.returncode == 0, out.stderr[-2000:]
    s = pd.read_csv(tmp_path / "cs" / "cs_nevertreated_simple.csv").iloc[0]
    assert s.att == pytest.approx(-0.10, abs=0.02)
    dy = pd.read_csv(tmp_path / "cs" / "cs_nevertreated_dynamic.csv")
    assert dy.rel.min() >= -9 and dy.rel.max() <= 5
    assert (dy.crit_uniform >= 1.95).all()  # uniform bands are at least as wide as pointwise
    assert (tmp_path / "cs" / "cs_notyettreated_simple.csv").exists()


@needs_r
def test_honestdid_runs_on_a_synthetic_event_study(tmp_path):
    if subprocess.run(["Rscript", "-e", "quit(status = !requireNamespace('HonestDiD', quietly = TRUE))"]).returncode:
        pytest.skip("HonestDiD not installed")
    E, d = synthetic_es(seed=5)
    sizes = d[d.cohort > 0].groupby("cohort").unit_id.nunique()
    dd, meta = E.sa_design(d)
    b, V, _ = E.fit(dd, meta, ["x"])
    t, cov = E.aggregate(b, V, meta, sizes, (-9, 5))
    t.to_csv(tmp_path / "es_primary_coefs.csv", index=False)
    cov.to_csv(tmp_path / "es_primary_vcov.csv")
    out = subprocess.run(["Rscript", "src/causal/honest.R", str(tmp_path), "es_primary"], capture_output=True, text=True, timeout=1800)
    assert out.returncode == 0, out.stderr[-2000:]
    s = pd.read_csv(tmp_path / "es_primary_honest_summary.csv").iloc[0]
    assert s.orig_ub < 0  # the planted average post effect (about -0.17) is far from 0
    rm = pd.read_csv(tmp_path / "es_primary_honest_rm.csv")
    assert list(rm.Mbar) == [0, 0.5, 1, 1.5, 2]
    assert (rm.ub - rm.lb).is_monotonic_increasing  # robust CIs widen with Mbar
    sm = pd.read_csv(tmp_path / "es_primary_honest_sm.csv")
    assert len(sm) == 6 and sm.M.iloc[0] == 0


# ---------------------------------------------------------------- Layer B (ground)


def synthetic_ground(effect: float = -0.10, seed: int = 9):
    """Station-level balanced panel 2018-2025: 12 treated cities (cohort 2019; city 0 has 6 stations),
    1 treated city in cohort 2021, 6 control cities with one station each. A common year shock, and
    `effect` (log) on treated stations from their cohort year. 2020 adds -0.3 to every station."""
    rng = np.random.default_rng(seed)
    years = range(2018, 2026)
    shock = {y: rng.normal(0, 0.05) for y in years}
    rows = []
    cities = [(f"t{i}", "treated", 2019, 6 if i == 0 else 1) for i in range(12)] + [("t21", "treated", 2021, 2)]
    cities += [(f"c{i}", "control", 0, 1) for i in range(6)]
    for u, grp, g, n in cities:
        for k in range(n):
            lvl = rng.normal(4, 0.3)
            for y in years:
                eff = effect if (grp == "treated" and y >= g) else 0.0
                rows.append({"sid": f"{u}_s{k}", "unit_id": u, "pollutant": "pm25", "year": y, "group": grp, "cohort": g,
                             "y": float(np.exp(lvl + shock[y] + eff + (-0.3 if y == 2020 else 0) + rng.normal(0, 0.01)))})  # fmt: skip
    d = pd.DataFrame(rows)
    return d.assign(raw=d.y, fit=d.y)


def test_closed_form_did_equals_twfe_ols_on_a_balanced_panel():
    import pyfixest as pf

    from src.causal import layer_b as B

    st = synthetic_ground()
    parts = B.did_parts(st, "sid", 2018)
    for g, (t, c) in parts.items():
        d = st[((st.group == "treated") & (st.cohort == g)) | (st.group == "control")]
        d = d[d.year != 2020].copy()
        d["ly"], d["D"] = np.log(d.y), ((d.group == "treated") & (d.year >= g)).astype(float)
        ols = pf.feols("ly ~ D | sid + year", data=d).coef().iloc[0]
        assert t.mean() - c.mean() == pytest.approx(ols, abs=1e-10)
    emap = st.drop_duplicates("sid").set_index("sid").unit_id
    est, bg = B.did_estimate(parts, {"t": {g: emap.reindex(t.index) for g, (t, _) in parts.items()}})
    assert est == pytest.approx(-0.10, abs=0.02)
    assert est == pytest.approx((12 * bg[2019] + 1 * bg[2021]) / 13)  # weights = treated cities per cohort


def test_its_contrasts_drop_2020_and_can_exclude_2019():
    from src.causal import layer_b as B

    st = synthetic_ground(effect=-0.10)
    cs = B.city_series(st)
    d = B.its_city(cs, 2018)
    assert set(d.unit_id) == {f"t{i}" for i in range(12)} | {"t21"}
    # ITS includes the common year shocks (it cannot separate national shocks), but never 2020's -0.3
    assert d.d.mean() > -0.3
    d19 = B.its_city(cs, 2018, exclude_post=(2019,))
    x = cs[cs.unit_id == "t1"].set_index("year").y.apply(np.log)
    assert d19.set_index("unit_id").d["t1"] == pytest.approx(x.loc[[2021, 2022, 2023, 2024, 2025]].mean() - x.loc[2018])
    # cohort 2021: pre = 2018 and 2019 (2020 dropped)
    z = cs[cs.unit_id == "t21"].set_index("year").y.apply(np.log)
    assert d.set_index("unit_id").d["t21"] == pytest.approx(z.loc[2021:2025].mean() - z.loc[[2018, 2019]].mean())


def test_ground_bootstrap_is_stratified_and_counts_city_multiplicity():
    from src.causal import layer_b as B

    st = synthetic_ground()
    parts = B.did_parts(st, "sid", 2018)
    emap = st.drop_duplicates("sid").set_index("sid").unit_id
    units_t = {g: emap.reindex(t.index) for g, (t, _) in parts.items()}
    units_c = emap.reindex(parts[2019][1].index)
    b = B.boot_did(parts, units_t, units_c, 500, np.random.default_rng(0))
    assert np.isfinite(b).all()  # every draw keeps treated and control cities in every stratum
    est, _ = B.did_estimate(parts, {"t": units_t})
    lo, hi, se = B.ci(b)
    assert lo < est < hi and se > 0
    # a draw that picks city t0 (6 stations) counts all six of its stations: the bootstrap mean of the
    # treated side is station-weighted, like the estimate
    t = parts[2019][0]
    assert t.groupby(units_t[2019]).size()["t0"] == 6


def test_city_level_did_uses_the_city_as_its_own_entity():
    from src.causal import layer_b as B

    st = synthetic_ground()
    cs = B.city_series(st)
    for frame, key in ((st, "sid"), (cs, "unit_id")):
        emap = B.entity_city(frame, key)
        assert (emap.reindex(frame[key]).to_numpy() == frame.unit_id.to_numpy()).all()
    parts = B.did_parts(cs, "unit_id", 2018)
    emap = B.entity_city(cs, "unit_id")
    units_t = {g: emap.reindex(t.index) for g, (t, _) in parts.items()}
    est, _ = B.did_estimate(parts, {"t": units_t})
    b = B.boot_did(parts, units_t, emap.reindex(parts[2019][1].index), 200, np.random.default_rng(1))
    assert est == pytest.approx(-0.10, abs=0.02) and np.isfinite(b).all()


def test_a_cohort_without_a_pre_year_is_dropped_dec157():
    from src.causal import layer_b as B

    st = synthetic_ground()
    st = st[st.year >= 2019]  # a 2019 baseline: cohort 2019 has no pre-year, cohort 2021 has 2019
    parts = B.did_parts(st, "sid", 2019)
    assert set(parts) == {2021}
    d = B.its_city(B.city_series(st), 2019)
    assert set(d.unit_id) == {"t21"}


def test_descriptive_levels_are_unweighted_means_with_t_intervals():
    from src.causal import descriptive as Dd

    pan = pd.DataFrame({"unit_id": ["a", "b", "c", "a", "b", "c"], "year": [2018] * 3 + [2019] * 3,
                        "value": [10.0, 20.0, 60.0, 12.0, 18.0, 30.0]})  # fmt: skip
    units = pd.DataFrame({"unit_id": ["a", "b", "c"], "role_a": ["treated", "treated", "control"]})
    d = Dd.levels(pan, units).set_index(["year", "group"])
    assert d.loc[(2018, "NCAP units"), "mean"] == pytest.approx(15.0)
    assert d.loc[(2018, "NCAP units"), "n"] == 2 and d.loc[(2019, "control pool"), "mean"] == pytest.approx(30.0)
    r = d.loc[(2018, "NCAP units")]
    assert r.lo95 < 15 < r.hi95 and r["median"] == pytest.approx(15.0)

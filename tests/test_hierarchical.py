"""Tests for Phase 8 (heterogeneity and mechanism, RQ4): src/hierarchical/ (DEC-162 to DEC-166).
SYNTHETIC DATA ONLY: every table below is made up, with known values planted in it, to check that a rule
or an estimator does what DECISIONS says. None of it is real air-quality or funding data, and nothing is
written under data/."""

import os
import shutil
import subprocess

import numpy as np
import pandas as pd
import pytest

from src.hierarchical import city_estimates as CE
from src.hierarchical import dose as D
from src.hierarchical import mechanism as M
from src.hierarchical import pooling as PL
from tests.test_causal import synthetic_panel

needs_r = pytest.mark.skipif(shutil.which("Rscript") is None, reason="Rscript not on PATH")


def test_placebo_p_is_equal_tailed_and_bh_steps_up():
    null = np.arange(-50, 50) / 100.0
    assert CE.placebo_p(10.0, null) == pytest.approx(2 / 101)
    assert CE.placebo_p(0.0, null) == 1.0
    # BH: with p = (0.001, 0.02, 0.03, 0.5) at q = 0.05, thresholds are 0.0125, 0.025, 0.0375, 0.05:
    # step-up rejects the first three (0.03 <= 0.0375), even though 0.02 alone would pass at its own rank
    assert CE.bh_reject(np.array([0.5, 0.03, 0.001, 0.02])).tolist() == [False, True, True, True]
    assert not CE.bh_reject(np.array([0.2, 0.3])).any()


def test_unit_estimates_use_the_cohort_placebo_sd_and_the_prefit_scaling():
    rng = np.random.default_rng(3)
    plac = pd.DataFrame({"kind": "placebo", "unit_id": [f"c{i}" for i in range(200)] * 2,
                         "cohort": [2019] * 200 + [2021] * 200, "att": rng.normal(0, 0.02, 400),
                         "prefit_sd": rng.uniform(0.01, 0.03, 400), "warnings": 0})  # fmt: skip
    real = pd.DataFrame({"kind": "real", "unit_id": ["a", "b"], "cohort": [2019, 2021], "att": [0.05, -0.01],
                         "prefit_sd": [0.02, 0.04], "warnings": 0})  # fmt: skip
    e = CE.unit_estimates(pd.concat([plac, real])).set_index("unit_id")
    p19 = plac[plac.cohort == 2019]
    assert e.loc["a", "se"] == pytest.approx(p19.att.std(ddof=1))
    assert e.loc["a", "se_scaled"] == pytest.approx((p19.att / p19.prefit_sd).std(ddof=1) * 0.02)
    assert e.loc["b", "se"] == pytest.approx(plac[plac.cohort == 2021].att.std(ddof=1))
    assert e.loc["a", "p_placebo"] < 0.05


def test_moderators_code_regions_channel_and_standardise():
    units = pd.DataFrame({"unit_id": ["u1", "u2", "u3"], "ncap_cities": ["A", "B;C", "D"],
                          "region": ["igp", "coastal", "north-east"], "pop_2015": [1e5, 1e6, 1e7]})  # fmt: skip
    panel = pd.DataFrame([{"unit_id": u, "year": y, "series": "popw_V5GL06", "value": v}
                          for u, v in (("u1", 20.0), ("u2", 40.0), ("u3", 80.0)) for y in range(2008, 2025)])  # fmt: skip
    cities = pd.DataFrame({"city": list("ABCD"), "channel": ["NCAP", "NCAP", "XVFC", "NCAP"]})
    m = CE.moderators(units, panel, cities).set_index("unit_id")
    assert m.igp.tolist() == [1, 0, 0] and m.coastal.tolist() == [0, 1, 0]
    assert m.xvfc.tolist() == [0, 1, 0]  # any XV-FC member makes the unit XV-FC (DEC-163)
    assert m.baseline_log_pm25["u2"] == pytest.approx(np.log(40.0))  # 2010-2018 only
    assert m.log_pop.mean() == pytest.approx(0.0) and m.log_pop.std(ddof=1) == pytest.approx(1.0)


def test_h5_and_h3_verdicts():
    assert PL.h5_verdict(0.001, 0.05) == "met"
    assert PL.h5_verdict(-0.001, 0.05) == "not met"
    assert M.verdict(True, True, True) == "consistent with dust control"
    assert M.verdict(True, True, False) == "inconclusive"


def test_condition_ii_needs_pm10_to_fall_and_fall_more():
    b = pd.DataFrame({"estimator": ["ITS"] * 6, "spec": ["r", "r", "d", "d", "p", "p"],
                      "pollutant": ["pm25", "pm10"] * 3, "est": [-0.10, -0.20, 0.05, 0.02, -0.10, -0.05]})  # fmt: skip
    w = M.condition_ii(b).set_index("spec")
    # r: PM10 fell more -> counts; d: PM10 rose less than PM2.5 -> does not count (DEC-135); p: fell less
    assert w.pm10_fell_more.to_dict() == {"d": False, "p": False, "r": True}


def test_ratio_frame_keeps_colocated_stations_with_every_year():
    rows = []
    for sid, years, pols in (("s1", range(2018, 2026), ("pm25", "pm10")), ("s2", range(2018, 2026), ("pm25",)),
                             ("s3", range(2019, 2026), ("pm25", "pm10"))):  # fmt: skip
        for y in years:
            for p in pols:
                rows.append({"sid": sid, "unit_id": "u", "year": y, "group": "treated", "cohort": 2019, "pollutant": p,
                             "y": 50.0 if p == "pm25" else 100.0, "raw": 1.0})  # fmt: skip
    r = M.ratio_frame(pd.DataFrame(rows), "y")
    assert set(r.sid) == {"s1"} and r.y.eq(0.5).all()


def test_dose_units_follow_dec166():
    cities = pd.DataFrame({"city": ["A", "B", "C", "D", "E", "F"], "channel": ["XVFC", "XVFC", "XVFC", "NCAP", "XVFC", "XVFC"]})
    ua = pd.DataFrame({"city": ["A", "B", "E"], "alloc_total": [10.0, 30.0, 5.0], "pop_millions": [1.0, 2.0, 1.0],
                       "state": ["S1", "S1", "S2"]})  # fmt: skip
    ua["rs_per_person"] = ua.alloc_total / ua.pop_millions * D.RS_PER_PERSON
    units = pd.DataFrame({"unit_id": ["u1", "u2", "u3", "u4"], "ncap_cities": ["A;B", "C", "D;E", "F;E"],
                          "region": "igp"})  # fmt: skip
    d = D.unit_dose(units, cities, ua).set_index("unit_id")
    assert d.loc["u1", "rs_per_person"] == pytest.approx(40.0 / 3.0 * 10)  # sum alloc / sum pop
    assert d.loc["u2", "excluded"] == "no allocation row of its own"
    assert d.loc["u3", "excluded"] == "a member city is in the NCAP channel"
    assert d.loc["u4", "excluded"] == "" and d.loc["u4", "matched"] == "E"  # a UA figure covers the unit


@pytest.mark.slow
def test_measurement_error_model_recovers_a_planted_moderator():
    rng = np.random.default_rng(5)
    n = 100
    X = np.column_stack([rng.normal(size=n), rng.integers(0, 2, n)])
    theta = 0.02 + X @ np.array([0.0, 0.04]) + rng.normal(0, 0.01, n)
    s = np.full(n, 0.01)
    y = theta + rng.normal(0, s)
    idata = PL.fit(y, s, X, draws=500, tune=500, chains=2, seed=1, cores=1)
    b = PL.draws(idata, "beta")
    lo, hi = PL.interval(b[:, 1])
    assert lo < 0.04 < hi and lo > 0
    assert PL.diagnostics(idata, True)["divergences"] == 0


@needs_r
def test_unit_sdid_recovers_per_unit_effects_and_runs_every_placebo(tmp_path):
    panel, treated = synthetic_panel(effect=-0.10, n_ctl=25, cohorts=((2019, 3), (2021, 2)))
    panel.to_parquet(tmp_path / "panel_annual.parquet", index=False)
    ids = sorted(panel.unit_id.unique())
    tr = treated.set_index("unit_id").cohort
    pd.DataFrame({"unit_id": ids, "role_a": ["treated" if i in tr.index else "control" for i in ids],
                  "cohort_listed": [float(tr.get(i, np.nan)) for i in ids]}).to_csv(tmp_path / "design_units.csv", index=False)  # fmt: skip
    env = {**os.environ, "NCAP_CAUSAL_DIR": str(tmp_path), "NCAP_HIER_DIR": str(tmp_path), "NCAP_WORKERS": "2",
           "OMP_NUM_THREADS": "1"}  # fmt: skip
    out = subprocess.run(["Rscript", "src/hierarchical/unit_sdid.R", "popw_V5GL06"], env=env, capture_output=True,
                         text=True, timeout=900)  # fmt: skip
    assert out.returncode == 0, out.stderr
    f = pd.read_parquet(tmp_path / "unit_sdid_popw_V5GL06.parquet")
    real = f[f.kind == "real"]
    assert len(real) == 5 and len(f[f.kind == "placebo"]) == 25 * 2  # every control x each cohort year
    assert real.att.between(-0.16, -0.04).all()
    plac = f[f.kind == "placebo"]
    assert abs(plac.att.mean()) < 0.03 and (f.prefit_sd > 0).all()

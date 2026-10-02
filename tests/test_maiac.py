"""Tests for Phase 8b (raw MAIAC AOD; DEC-174 to DEC-181): the QA bit logic of src/acquire/maiac_gee.py, the
unit-month and unit-year rules of src/causal/maiac.py, and the DEC-180 classifications in decisions.py.
SYNTHETIC DATA ONLY: every table below is made up to check a rule. None of it is real AOD, and nothing is
written under data/."""

import numpy as np
import pandas as pd
import pytest

from src.acquire import maiac_gee as G
from src.causal import decisions as D
from src.causal import layer_a as A
from src.causal import maiac as M

F = G.CFG["qa_fields"]
PRIMARY, RELAXED = G.CFG["filters"]["primary"], G.CFG["filters"]["relaxed"]


# ---------------------------------------------------------------- QA bits (DEC-175)


def test_qa_bits_follow_the_user_guide_layout():
    # clear (001), land (00), adjacency normal (000), best (0000) packs to 1
    assert G.qa_value(F, {"cloud": 1, "surface": 0, "adjacency": 0, "aod_qa": 0}) == 0b1
    # possibly cloudy (010), water (01), adjacent to a single cloudy pixel (011), research quality (1011)
    assert G.qa_value(F, {"cloud": 2, "surface": 1, "adjacency": 3, "aod_qa": 11}) == 0b1011_011_01_010


def test_primary_filter_keeps_only_best_quality_clear_land():
    best = G.qa_value(F, {"cloud": 1, "surface": 0, "adjacency": 0, "aod_qa": 0})
    assert G.qa_accepts(best, F, PRIMARY)
    assert G.qa_accepts(best | (1 << 12) | (2 << 13), F, PRIMARY)  # glint and aerosol model are not filtered
    for change in ({"cloud": 2}, {"surface": 1}, {"adjacency": 3}, {"aod_qa": 3}, {"aod_qa": 11}):
        v = {"cloud": 1, "surface": 0, "adjacency": 0, "aod_qa": 0, **change}
        assert not G.qa_accepts(G.qa_value(F, v), F, PRIMARY), change


def test_relaxed_filter_adds_exactly_the_listed_values():
    ok = [{"cloud": c, "surface": 0, "adjacency": a, "aod_qa": q} for c in (1, 2) for a in (0, 3) for q in (0, 3, 11)]
    assert all(G.qa_accepts(G.qa_value(F, v), F, RELAXED) for v in ok)
    for bad in ({"cloud": 3}, {"surface": 1}, {"adjacency": 1}, {"aod_qa": 4}, {"aod_qa": 5}):
        v = {"cloud": 1, "surface": 0, "adjacency": 0, "aod_qa": 0, **bad}
        assert not G.qa_accepts(G.qa_value(F, v), F, RELAXED), bad


# ---------------------------------------------------------------- unit-month and unit-year (DEC-176/177)


def sums(rows):
    cols = ["unit_id", "year", "month", *G.SUMS]
    return pd.DataFrame(rows, columns=cols)


def test_month_measures_are_ratios_of_the_exported_sums():
    # synthetic unit: population 1000; 600 people under pixels with a value, mean AOD 0.5, 5 days on average
    s = sums([["u1", 2015, 1, 1000, 10, 600, 300, 5000, 6, 3.0, 50, 0, 0, 0],
              ["u1", 2015, 2, 1000, 10, 400, 200, 8000, 4, 2.0, 40, 0, 0, 0]])  # fmt: skip
    m = M.month_measures(s, "pop", "primary", 0.5, 4)
    assert m.aod.tolist() == pytest.approx([0.5, 0.5])
    assert m.coverage.tolist() == pytest.approx([0.6, 0.4])
    assert m.days.tolist() == pytest.approx([5.0, 8.0])
    assert m.valid.tolist() == [True, False]  # coverage 40% < 50%
    a = M.month_measures(s, "area", "primary", 0.5, 4)
    assert a.aod.tolist() == pytest.approx([0.5, 0.5]) and a.days.tolist() == pytest.approx([5.0, 4.0])
    r = M.month_measures(s, "pop", "relaxed", 0.5, 4)
    assert r.aod.isna().all() and not r.valid.any()  # no pixel with a value: no mean, not valid


def test_month_needs_four_weighted_days():
    s = sums([["u1", 2015, 1, 1000, 10, 900, 450, 3999, 9, 4.5, 39.99, 0, 0, 0]])
    assert not M.month_measures(s, "pop", "primary", 0.5, 4).valid.iloc[0]


def month_frame(valid_months, values=None, unit="u1", year=2015):
    values = values or {}
    return pd.DataFrame({"unit_id": unit, "year": year, "month": range(1, 13),
                         "aod": [values.get(m, 0.4) for m in range(1, 13)],
                         "valid": [m in valid_months for m in range(1, 13)]})  # fmt: skip


def test_year_rule_counts_only_non_monsoon_months():
    mon, k = G.CFG["monsoon_months"], G.CFG["year_min_nonmonsoon_months"]
    nm = [1, 2, 3, 4, 5, 10, 11, 12]
    y = M.annual(month_frame(nm[:6]), mon, k, "all")
    assert bool(y.valid.iloc[0]) and y.n_nonmonsoon_valid.iloc[0] == 6
    y = M.annual(month_frame(nm[:5] + [6, 7, 8, 9]), mon, k, "all")  # all four monsoon months cannot rescue it
    assert not bool(y.valid.iloc[0]) and np.isnan(y.value.iloc[0])


def test_annual_primary_uses_valid_monsoon_months_nonmonsoon_does_not():
    mon, k = G.CFG["monsoon_months"], G.CFG["year_min_nonmonsoon_months"]
    f = month_frame([1, 2, 3, 4, 5, 10, 11, 12, 7], values={7: 1.3})
    allm = M.annual(f, mon, k, "all").iloc[0]
    nonm = M.annual(f, mon, k, "nonmonsoon").iloc[0]
    assert allm.value == pytest.approx((8 * 0.4 + 1.3) / 9) and allm.months_used == 9
    assert nonm.value == pytest.approx(0.4) and nonm.months_used == 8


def test_complete_units_need_every_analysis_year():
    years = [2010, 2011, 2012]
    y = pd.DataFrame({"unit_id": ["a"] * 3 + ["b"] * 3, "year": years * 2, "valid": [True] * 3 + [True, False, True]})
    assert M.complete_units(y, years) == {"a"}
    assert 2020 not in M.analysis_years() and M.analysis_years()[0] == 2010 and M.analysis_years()[-1] == 2024


def test_leakage_split_uses_the_specs_first_outcome_and_phase7_is_unchanged():
    t = pd.DataFrame({"unit_id": ["u1", "u2", "u3"], "cohort": [2019] * 3, "cell": ["gained", "notgained", "gained"]})
    s = A.SdidSpec("x", "x", "8b", "test", t, ["c1"], outcomes=["log:aod_popw"], panel="panel_aod.parquet", leakage=True)
    assert (s.fitsets().outcomes == "log:aod_popw").all()
    assert set(s.estimands().outcome) == {"log:aod_popw"}
    p7 = A.SdidSpec("p", "p", "A", "test", t, ["c1"], outcomes=[A.LOG, "level:popw_V5GL06"], leakage=True)
    fs = p7.fitsets()
    assert (fs[~fs.fitset.str.startswith("all")].outcomes == A.LOG).all()


# ---------------------------------------------------------------- DEC-180 classifications


def test_q1_branches_in_order():
    acag = (0.035, 0.024, 0.047)
    assert D.aod_q1((0.05, 0.01, 0.09), (0.01, -0.01, 0.03))["code"] == "not_testable"
    assert D.aod_q1((0.05, 0.01, 0.09), (-0.03, -0.05, -0.01))["code"] == "not_testable"
    assert D.aod_q1((0.01, -0.02, 0.04), acag)["code"] == "uninformative"  # contains 0 and 0.035
    assert D.aod_q1((0.04, 0.02, 0.06), acag)["code"] == "rise_in_aod"
    assert D.aod_q1((-0.04, -0.06, -0.02), acag)["code"] == "opposite"
    assert D.aod_q1((0.0, -0.02, 0.02), acag)["code"] == "not_reproduced"  # contains 0, lies below 0.035
    assert D.aod_q1((0.10, -0.01, 0.21), acag)["code"] == "uninformative"


def test_q2_branches_in_order():
    gap = (-0.029, -0.051, -0.005)
    assert D.aod_q2((-0.03, -0.05, -0.01), gap, 9, 30)["code"] == "not_testable"  # a group under 10
    assert D.aod_q2((-0.03, -0.05, -0.01), (-0.01, -0.03, 0.01), 70, 39)["code"] == "not_testable"
    assert D.aod_q2((-0.01, -0.04, 0.02), gap, 70, 39)["code"] == "uninformative"  # contains 0 and -0.029
    assert D.aod_q2((-0.03, -0.05, -0.01), gap, 70, 39)["code"] == "gap_reproduced"
    assert D.aod_q2((0.0, -0.02, 0.02), gap, 70, 39)["code"] == "gap_absent"  # interval lies above -0.029
    assert D.aod_q2((0.03, 0.01, 0.05), gap, 70, 39)["code"] == "gap_absent"  # reversed
    assert "fewer than 10" in D.aod_q2((0, -1, 1), gap, 5, 39)["label"]

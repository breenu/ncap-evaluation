"""Audit rules: neighbour reference, spatial outliers, changepoints, completeness, reliability score.

All data here are SYNTHETIC, generated in the test (CLAUDE.md hard rule 1).
"""

import numpy as np
import pandas as pd
import pytest

from src.clean import changepoints, reliability, spatial


def test_robust_z():
    x = pd.Series([1.0, 1.1, 0.9, 1.0, 5.0])
    z = spatial.robust_z(x)
    assert abs(z.iloc[0]) < 1 and z.iloc[-1] > 3
    assert (spatial.robust_z(pd.Series([2.0, 2.0, 2.0])) == 0).all()


def test_neighbour_reference_needs_two_neighbours(monkeypatch):
    monkeypatch.setattr(spatial, "valid_hours", lambda: 18)
    dates = pd.date_range("2020-01-01", periods=3)
    rows = []
    for sid, level in [("a", 100.0), ("b", 50.0), ("c", 200.0), ("d", 80.0)]:
        for dt in dates:
            rows.append({"sid": sid, "date_ist": dt, "pm25": level, "pm25_h1": 24})
    day = pd.DataFrame(rows)
    ref = spatial.neighbour_reference(day, {"a": ["b", "c"], "d": ["a"]}, "pm25")
    assert set(ref.sid) == {"a"}  # d has only one neighbour
    # reference = median of log(50), log(200) = log(100): station a sits exactly on it
    assert np.allclose(ref.resid, 0.0)


def test_changepoint_finds_a_step_and_ignores_noise():
    rng = np.random.default_rng(1)
    idx = pd.date_range("2019-01-06", periods=120, freq="W")
    noise = pd.Series(rng.normal(0, 0.05, 120), index=idx)
    assert changepoints.detect(noise, penalty=3, min_shift=0.223) == []
    step = noise + np.where(np.arange(120) >= 60, 0.4, 0.0)  # a 49% step up at week 60
    got = changepoints.detect(step, penalty=3, min_shift=0.223)
    assert len(got) == 1 and abs((got[0]["date"] - idx[60]).days) <= 14
    assert got[0]["shift_log"] == pytest.approx(0.4, abs=0.05)


def test_block_shuffle_keeps_values():
    rng = np.random.default_rng(3)
    v = np.arange(10.0)
    out = changepoints.block_shuffle(v, rng, k=4)
    assert sorted(out) == list(v) and len(out) == 10


def test_calibrate_picks_smallest_penalty_meeting_target():
    rng = np.random.default_rng(4)
    idx = pd.date_range("2019-01-06", periods=120, freq="W")
    noise = [pd.Series(rng.normal(0, 0.1, 120), index=idx) for _ in range(20)]
    pen, t = changepoints.calibrate(noise, [3, 10, 50], target=0.05, min_shift=0.223, rng=rng)
    assert pen == t[t.null_false_alarm <= 0.05].penalty.min()


def test_changepoint_small_step_below_min_shift_is_ignored():
    rng = np.random.default_rng(2)
    idx = pd.date_range("2019-01-06", periods=120, freq="W")
    s = pd.Series(rng.normal(0, 0.02, 120) + np.where(np.arange(120) >= 60, 0.1, 0.0), index=idx)
    assert changepoints.detect(s, penalty=3, min_shift=0.223) == []  # a real but 10% step


def test_deseasonalise_removes_annual_cycle():
    idx = pd.date_range("2018-01-01", "2020-12-31")
    cyc = pd.Series(np.cos(2 * np.pi * idx.dayofyear / 365.25) + 3.0, index=idx)
    assert changepoints.deseasonalise(cyc).abs().max() < 0.02


def test_window_days(monkeypatch):
    monkeypatch.setattr(
        reliability,
        "params",
        lambda: {"windows": {"ground_start": "2015-01-01", "ground_end": "2026-03-31"}},
    )
    assert reliability.window_days(2016) == 366
    assert reliability.window_days(2026) == 90


def test_completeness_variants(monkeypatch):
    monkeypatch.setattr(
        reliability,
        "params",
        lambda: {"windows": {"ground_start": "2019-01-01", "ground_end": "2019-01-10"}},
    )
    dates = pd.date_range("2019-01-01", "2019-01-10")
    # 8 days with 20 usable hours (18 of them with >= 3 quarter-hours), 2 days with 10 hours
    h1 = [20] * 8 + [10] * 2
    h3 = [18] * 8 + [10] * 2
    day = pd.DataFrame(
        {"sid": "s", "date_ist": dates, "pm25_h1": h1, "pm25_h3": h3, "pm10_h1": 0, "pm10_h3": 0}
    )
    q = reliability.completeness(day)
    r = q[q.pollutant == "pm25"].iloc[0]
    assert r.valid_days_q1_t75 == 8 and r.valid_q1_t75  # 8/10 >= 75%
    assert r.valid_days_q1_t90 == 0 and not r.valid_q1_t90  # 20 hours < 22
    assert r.valid_days_q3_t75 == 8  # 18 hours with >= 3 quarter-hours still meets 18


def test_reliability_score():
    q = pd.DataFrame(
        {
            "valid_days_q1_t75": [365, 365, 182],
            "window_days": [365, 365, 365],
            "hours_ratio_flag": [0, 0, 0],
            "hours_flatline": [0, 876, 0],
            "quarters_ceiling": [0, 0, 0],
            "quarters_impossible": [0, 0, 0],
            "hours": [8760, 8760, 4380],
            "failed_checks": [0, 0, 2],
        }
    )
    s = reliability.score(q, penalty=0.8)
    assert s.iloc[0] == pytest.approx(100)
    assert s.iloc[1] == pytest.approx(90)  # 10% of hours flatlined
    assert s.iloc[2] == pytest.approx(100 * 182 / 365 * 0.64)

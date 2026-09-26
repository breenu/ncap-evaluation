"""Flag rules (src/clean/flags.py). All data here are SYNTHETIC (CLAUDE.md hard rule 1)."""

import numpy as np
import pandas as pd

from src.clean import flags


def test_impossible_value():
    v = pd.Series([12.0, 0.0, -3.0, np.nan])
    assert flags.impossible_value(v).tolist() == [False, True, True, False]


def test_detect_ceilings_finds_spikes_not_ordinary_high_values():
    values = pd.Series(np.arange(500.0, 1000.5, 1.0))
    counts = pd.Series(10, index=values.index)
    counts[values == 985.0] = 5000  # a pinned ceiling
    counts[values == 700.0] = 25  # a little noise: not a ceiling
    got = flags.detect_ceilings(values, counts, min_value=500, excess=10, window=10)
    assert got == [985.0]


def test_detect_ceilings_compares_like_precision_only():
    """Integer readings are far more common than 2-decimal ones (many analysers report whole
    numbers); an ordinary integer must not look like a spike against rare decimal neighbours."""
    ints = np.arange(500.0, 1001.0, 1.0)
    decs = np.arange(500.37, 1000.0, 1.0)
    values = pd.Series(np.concatenate([ints, decs, [999.99]]))
    counts = pd.Series(np.concatenate([np.full(len(ints), 600), np.full(len(decs), 2), [4000]]))
    counts[values == 985.0] = 12000  # a pinned integer ceiling
    got = flags.detect_ceilings(values, counts, min_value=500, excess=10, window=10)
    assert got == [985.0, 999.99]


def test_detect_ceilings_needs_many_stations():
    values = pd.Series([700.0, 701.0, 702.0, 703.0, 704.0])
    counts = pd.Series([10, 10, 5000, 10, 10])
    stations = pd.Series([30, 30, 1, 30, 30])  # 702 is stuck at a single analyser
    assert (
        flags.detect_ceilings(values, counts, 500, 10, 10, stations, min_stations=5, min_count=500)
        == []
    )


def test_ceiling_pin():
    v = pd.Series([999.99, 985.0, 984.9, np.nan])
    assert flags.ceiling_pin(v, [985.0, 999.99]).tolist() == [True, True, False, False]
    assert not flags.ceiling_pin(v, []).any()


def test_pm25_exceeds_pm10_uses_tolerance():
    pm25 = pd.Series([50.0, 54.0, 60.0, 300.0, 340.0, np.nan])
    pm10 = pd.Series([50.0, 50.0, 50.0, 300.0, 300.0, 50.0])
    # tolerance: max(5, 10% of PM10) -> 5 at PM10=50, 30 at PM10=300
    got = flags.pm25_exceeds_pm10(pm25, pm10, abs_tol=5, rel_tol=0.10)
    assert got.tolist() == [False, False, True, False, True, False]


def test_flatline_needs_consecutive_hours():
    hours = pd.date_range("2020-01-01", periods=8, freq="h").to_series(index=range(8))
    v = pd.Series([10.0, 20.0, 20.0, 20.0, 20.0, 30.0, 30.0, 30.0])
    got = flags.flatline(v, hours, min_hours=4)
    assert got.tolist() == [False, True, True, True, True, False, False, False]


def test_flatline_broken_by_time_gap():
    hours = pd.Series(
        pd.to_datetime(
            ["2020-01-01 00:00", "2020-01-01 01:00", "2020-01-01 05:00", "2020-01-01 06:00"]
        )
    )
    v = pd.Series([7.0, 7.0, 7.0, 7.0])
    assert not flags.flatline(v, hours, min_hours=3).any()  # two runs of 2, not one run of 4

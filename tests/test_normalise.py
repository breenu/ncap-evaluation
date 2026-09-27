"""Tests for Phase 5 deweathering (src/normalise). SYNTHETIC DATA ONLY: every frame below is made up
to exercise one rule; none of it is real air-quality or weather data."""

import numpy as np
import pandas as pd
import pytest

from src.normalise import collect, era5_daily, features, lgbm, resample, store
from src.normalise.pilot import allocate


# --- ERA5 daily features --------------------------------------------------------------------------


def test_rh_is_100_at_saturation_and_plausible_otherwise():
    assert era5_daily.rh_from_dewpoint(25.0, 25.0) == pytest.approx(100)
    # 30 C with a 20 C dew point is about 55% (standard psychrometric tables)
    assert era5_daily.rh_from_dewpoint(30.0, 20.0) == pytest.approx(55.4, abs=1)


def test_wind_direction_is_where_the_wind_blows_from():
    assert era5_daily.wind_from_direction(0.0, -1.0) % 360 == pytest.approx(0)  # from the north
    assert era5_daily.wind_from_direction(-1.0, 0.0) == pytest.approx(90)  # from the east
    assert era5_daily.wind_from_direction(1.0, 0.0) == pytest.approx(270)  # from the west


def _hourly(start: str, hours: int) -> pd.DataFrame:
    """Synthetic hourly ERA5 rows."""
    t = pd.date_range(start, periods=hours, freq="h")
    return pd.DataFrame(
        {
            "valid_time": t,
            "t2m": 300.0, "d2m": 290.0, "u10": 1.0, "v10": 0.0,
            "blh": np.arange(hours, dtype=float), "ssrd": -1.0, "tp": 0.001,
        }
    )  # fmt: skip


def test_daily_uses_indian_days_and_drops_incomplete_days():
    # 18:00 UTC on 1 Jan is 23:30 IST on 1 Jan; 19:00 UTC is 00:30 IST on 2 Jan.
    h = _hourly("2020-01-01 18:00", 1 + 24 + 5)
    d = era5_daily.daily(h, (6, 12))
    assert list(d.date) == [pd.Timestamp("2020-01-02")]  # 1 Jan and 3 Jan are incomplete
    row = d.iloc[0]
    assert row.precip == pytest.approx(24.0)  # 24 h x 1 mm
    assert row.ssrd == 0  # negative radiation clipped (DEC-035)
    assert row.temp == pytest.approx(26.85)
    assert row.wd == pytest.approx(270)
    # afternoon maximum: the latest hour with UTC hour in 6..12 on 2 Jan is 12:00 UTC (row 1 + 17)
    assert row.blh_pm == pytest.approx(18.0)


# --- folds and resampling -------------------------------------------------------------------------


def test_forward_folds_need_enough_training_and_test_days():
    years = pd.Series([2017] * 200 + [2018] * 200 + [2019] * 20 + [2020] * 300)
    # 2017: no training; 2018: 200 < 365 training days; 2019: only 20 test days; 2020: ok
    assert features.forward_folds(years, 365, 30) == [2020]


def test_seasonal_draws_stay_within_the_window_and_wrap_the_year():
    pool_doy = np.tile(np.arange(1, 366), 3)
    target = np.array([2, 180, 365])
    idx = features.resample_indices(target, pool_doy, 400, "seasonal", 15, np.random.default_rng(1))
    assert idx.shape == (3, 400)
    for t, row in zip(target, idx):
        assert features.doy_distance(pool_doy[row], np.array(t)).max() <= 15
    assert (pool_doy[idx[0]] > 300).any()  # day 2 draws from late December too


def test_annual_draws_cover_the_year_and_indices_are_reproducible():
    pool_doy = np.arange(1, 366)
    a = features.resample_indices(np.array([100]), pool_doy, 2000, "annual", 15, np.random.default_rng(7))
    b = features.resample_indices(np.array([100]), pool_doy, 2000, "annual", 15, np.random.default_rng(7))
    assert (a == b).all()
    assert features.doy_distance(pool_doy[a[0]], np.array(100)).max() > 100


def test_normalise_averages_exp_predictions_over_draws():
    target = pd.DataFrame({"doy": [10, 20], "weekday": [0, 1], "trend": [0.0, 1.0]})
    pool = pd.DataFrame({f: 0.0 for f in era5_daily.FEATURES} | {"doy": [5, 6], "weekday": [2, 3]})
    pool["temp"] = [0.0, np.log(3.0)]  # exp(pred) is 1 or 3 depending on the drawn day
    idx = np.array([[0, 1] * 25 + [0] * 50, [1] * 100])

    def predict(x):  # weather-only model plus the trend
        return x.temp.to_numpy() + x.trend.to_numpy()

    out = resample.normalise(predict, target, pool, idx, "seasonal", [50, 100])
    assert out.dw_seasonal_n50.tolist() == pytest.approx([2.0, 3 * np.e])
    assert out.dw_seasonal_n100.tolist() == pytest.approx([1.5, 3 * np.e])
    # seasonal keeps the target's own calendar; annual takes it from the drawn pool day
    d = resample.design(target, pool, idx[:, :2], "seasonal")
    assert d.doy.tolist() == [10, 10, 20, 20]
    d = resample.design(target, pool, idx[:, :2], "annual")
    assert d.doy.tolist() == [5, 6, 6, 6]


# --- models and metrics ---------------------------------------------------------------------------


class _Recorder:
    """Stand-in model that records the years it was trained on."""

    seen: list = []

    def fit(self, x, y):
        _Recorder.seen.append(sorted(set(np.floor(x.trend + 2015).astype(int))))
        self.hi = x.trend.max()
        return self

    def predict(self, x):
        assert (x.trend <= self.hi + 1e-9).all()  # the test year's trend is clamped
        return np.zeros(len(x))


def test_cv_never_trains_on_the_test_year_or_later():
    dates = pd.date_range("2018-01-01", "2020-12-31", freq="D")
    fit = pd.concat(
        [pd.DataFrame({"date": dates, "y": 0.0}), features.time_features(pd.Series(dates))], axis=1
    ).assign(**{f: 0.0 for f in era5_daily.FEATURES}, year=dates.year)
    _Recorder.seen = []
    pred, fold = lgbm.cv_predict(fit, [2019, 2020], make=_Recorder)
    assert _Recorder.seen == [[2018], [2018, 2019]]
    assert set(fold[fit.year == 2018]) == {0} and np.isnan(pred[fit.year == 2018]).all()
    assert set(fold[fit.year == 2020]) == {2020}


def test_test_year_trend_conventions():
    train = pd.Series([0.0, 1.0, 1.99])  # training days span 2015-01-01 to late 2016
    x = pd.DataFrame({"trend": [2.0, 2.5, 2.99]})  # test year 2017
    # last_year: the same calendar day a year earlier, never outside the training range
    assert lgbm.test_trend(x, train, "last_year").trend.tolist() == pytest.approx([1.0, 1.5, 1.99])
    # clamp: every test day gets the last training day's value (carries that day's season along)
    assert lgbm.test_trend(x, train, "clamp").trend.tolist() == pytest.approx([1.99] * 3)
    with pytest.raises(ValueError):
        lgbm.test_trend(x, train, "nope")


def test_r2():
    y = np.array([1.0, 2.0, 3.0, np.nan])
    assert collect.r2(y, y) == 1
    assert collect.r2(y, np.array([2.0, 2.0, 2.0, 5.0])) == pytest.approx(0)


def test_acf_skips_gaps_and_group_boundaries():
    dates = pd.Series(pd.date_range("2020-01-01", periods=100))
    e = pd.Series(np.where(np.arange(100) % 2 == 0, 1.0, -1.0))  # alternating: lag-1 corr = -1
    g = pd.Series(np.zeros(100))
    assert collect.acf_pairs(e, dates, g, 1) == pytest.approx(-1)
    assert collect.acf_pairs(e, dates, g, 2) == pytest.approx(1)
    # remove every other day: no pair is 1 day apart any more, so none may be bridged
    keep = np.arange(100) % 2 == 0
    assert np.isnan(collect.acf_pairs(e[keep], dates[keep], g[keep], 1))
    # pairs across a group (test-year) boundary are not used
    assert np.isnan(collect.acf_pairs(e, dates, pd.Series(np.arange(100)), 1))


def test_smearing_rescales_but_keeps_relative_changes():
    out = pd.DataFrame(
        {"date": pd.date_range("2020-01-01", periods=4), "y": np.log([10, 20, 10, 20.0]),
         "fitted": np.log([10, 10, 20, 20.0]), "cv_pred": np.nan, "cv_fold": 0,
         "dw_seasonal_n300": [1.0, 2.0, 3.0, 4.0], "sd_seasonal": 0.0}
    )  # fmt: skip
    m = collect.metrics(out)
    assert m["smear"] == pytest.approx((1 + 2 + 0.5 + 1) / 4)
    d = collect.deweathered(out, m["smear"])
    assert (d.dw_seasonal_n300 / d.dw_seasonal_n300.iloc[0]).tolist() == pytest.approx([1, 2, 3, 4])


# --- resumability and pilot allocation ------------------------------------------------------------


def test_done_only_after_the_json_is_written(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "FITS", tmp_path)
    pq, js = store.task_paths("main", "lgbm", "pm25", "site_1")
    assert not store.is_done("main", "lgbm", "pm25", "site_1")
    store.write_atomic_parquet(pd.DataFrame({"a": [1]}), pq)
    assert not store.is_done("main", "lgbm", "pm25", "site_1")  # predictions alone are not done
    store.write_atomic_json({"ok": 1}, js)
    assert store.is_done("main", "lgbm", "pm25", "site_1")
    assert not list(tmp_path.rglob("*.tmp"))


def test_station_year_variants_average_raw_and_deweathered_over_the_same_days(monkeypatch):
    from src.normalise import aggregate

    q = pd.DataFrame({"sid": "s1", "pollutant": "pm25", "year": 2020, "valid_q1_t75": True,
                      "valid_q1_t60": True, "valid_q1_t90": False, "valid_q3_t75": True}, index=[0])  # fmt: skip
    monkeypatch.setattr(aggregate.pd, "read_parquet", lambda *a, **k: q)
    day = pd.DataFrame(
        {"sid": "s1", "pollutant": "pm25", "date": pd.date_range("2020-01-01", periods=3),
         "obs": [10.0, 20.0, 30.0], "h1": [24, 16, 18], "obs3": [11.0, 21.0, 31.0], "h3": [24, 10, 18],
         "dw_lgbm": [1.0, 2.0, 3.0], "dw_gam": [4.0, 5.0, 6.0]}
    )  # fmt: skip
    y = aggregate.station_year_table(day, "gam").set_index("variant")
    assert y.loc["q1_t75", "raw"] == 20 and y.loc["q1_t75", "dw"] == 5  # days 1 and 3 (>= 18 h)
    assert y.loc["q1_t60", "raw"] == 20 and y.loc["q1_t60", "days"] == 3  # >= 15 h: all three
    assert y.loc["q1_t90", "raw"] == 10 and not y.loc["q1_t90", "valid"]  # >= 22 h: day 1 only
    assert y.loc["q3_t75", "raw"] == 21 and y.loc["q3_t75", "dw_lgbm"] == 2  # 3-of-4 values, days 1, 3


def test_city_means_use_valid_stations_inside_the_polygon_only():
    from src.normalise.aggregate import city

    t = pd.DataFrame(
        {"unit_id": "u1", "region": "igp", "pollutant": "pm25", "year": 2020, "sid": ["a", "b", "c", "d"],
         "raw": [10.0, 20.0, 99.0, 99.0], "dw": [1.0, 3.0, 99.0, 99.0], "dw_lgbm": 1.0, "dw_gam": 1.0,
         "valid": [True, True, False, True], "inside_unit": [True, True, True, False]}
    )  # fmt: skip
    c = city(t, "year").iloc[0]
    assert (c.raw, c.dw, c.n_stations, c.covid_2020) == (15, 2, 2, True)


def test_divergence_is_relative_to_each_familys_own_mean(monkeypatch):
    from src.normalise import aggregate

    y = pd.DataFrame({"sid": "s", "pollutant": "pm25", "variant": "q1_t75", "valid": True,
                      "year": [2019, 2020, 2021], "dw_lgbm": [10.0, 10.0, 10.0],
                      "dw_gam": [20.0, 20.0, 20.0 * np.exp(0.09)]})  # fmt: skip
    monkeypatch.setattr(aggregate, "cfg", lambda: {"divergence_flag_pct": 5})
    d = aggregate.divergence_flags(y).iloc[0]
    # a constant level difference (x2) is not divergence; the 2021 step of 0.09 is: gap 0.06
    assert d.D_pct == pytest.approx(6.0) and d.diverges


def test_allocate_gives_a_regions_shortfall_to_the_largest_regions():
    eligible = pd.Series({"igp": 40, "coastal": 20, "north-east": 2, "peninsular/other": 30})
    take = allocate(eligible, 20, 5)
    assert take.sum() == 20
    assert take["north-east"] == 2 and take["igp"] == 8 and take["coastal"] == 5

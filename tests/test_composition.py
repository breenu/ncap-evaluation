"""Tests for Phase 6 network-composition correction and H4 (src/normalise/composition.py; DEC-125 to
DEC-131). SYNTHETIC DATA ONLY: every frame below is made up to exercise one rule; none of it is real
air-quality data."""

import numpy as np
import pandas as pd
import pytest

from src.normalise import composition as C

DW = ["dw_gam", "dw_lgbm", "dw_gam_k4", "dw_gam_annual", "dw_lgbm_annual", "dw_gam_k4_annual"]


def _sy(rows: list[tuple]) -> pd.DataFrame:
    """Synthetic station-years: (sid, unit, year, raw, dw). Every deweathered column = dw."""
    d = pd.DataFrame(rows, columns=["sid", "unit_id", "year", "raw", "dw"])
    for c in DW:
        d[c] = d.dw
    return d.assign(pollutant="pm25", rule="primary", variant="q1_t75", valid=True, inside_unit=True,
                    reenu_decided=False, reliability=90.0).drop(columns="dw")  # fmt: skip


def _city(extra: list[tuple] = ()) -> pd.DataFrame:
    """One unit: station A valid 2018-2025 (the panel), raw 100 -> 80, deweathered 100 -> 90."""
    a = [("A", "u1", y, 100 - 20 * (y - 2018) / 7, 100 - 10 * (y - 2018) / 7) for y in range(2018, 2026)]
    return _sy(a + list(extra))


def test_panel_strict_needs_every_year_loose_only_the_ends():
    v = C.select(_city([("B", "u1", 2018, 50, 50), ("B", "u1", 2025, 50, 50)]), C.PRIMARY)
    strict = C.panel_members(v, 2018, 2025, strict=True)
    loose = C.panel_members(v, 2018, 2025, strict=False)
    assert set(strict.sid) == {"A"}
    assert set(loose.sid) == {"A", "B"}


def test_decomposition_adds_up_and_h4_is_minus_weather_plus_composition():
    d = C.decompose(np.array([200.0, 120.0]), np.array([180.0, 150.0]), np.array([100.0, 80.0]), np.array([95.0, 90.0]))
    assert d["reported"] == pytest.approx(d["raw_minus_dw"] + d["composition"] + d["corrected"])
    assert d["h4"] == pytest.approx(d["h4_raw_minus_dw"] + d["h4_composition"])
    assert d["h4"] == pytest.approx(-(d["raw_minus_dw"] + d["composition"]))
    # the other order (composition first on raw, then weather on the panel) adds up to the same total
    assert d["comp_raw"] + d["weather_pan"] == pytest.approx(d["raw_minus_dw"] + d["composition"])


def test_weather_split_into_unmodelled_and_modelled_adds_up():
    # DEC-136: raw - deweathered = (raw - fitted) + (fitted - deweathered)
    d = C.decompose(np.array([200.0, 120.0]), np.array([180.0, 150.0]), np.array([100.0, 80.0]),
                    np.array([95.0, 90.0]), np.array([190.0, 130.0]))  # fmt: skip
    assert d["unmodelled"] + d["weather"] == pytest.approx(d["raw_minus_dw"])
    assert d["reported"] == pytest.approx(d["unmodelled"] + d["weather"] + d["composition"] + d["corrected"])
    assert d["h4"] == pytest.approx(d["h4_unmodelled"] + d["h4_weather"] + d["h4_composition"])
    no_fit = C.decompose(np.array([200.0, 120.0]), np.array([180.0, 150.0]), np.array([100.0, 80.0]), np.array([95.0, 90.0]))
    assert np.isnan(no_fit["weather"]) and np.isfinite(no_fit["raw_minus_dw"])


def test_fitted_city_mean_is_never_partial():
    raw = np.array([[100.0, 80.0], [50.0, 40.0]])
    fit = np.array([[98.0, 81.0], [np.nan, 41.0]])  # station 2 has no fitted value in the baseline year
    ra, da, rp, dp, fa = C.means_from(raw, raw, fit, np.array([True, False]), np.arange(2))
    assert np.isnan(fa[0]) and fa[1] == pytest.approx(61.0)


def test_h4_is_positive_when_a_clean_entrant_and_good_weather_flatter_the_reported_fall():
    # a clean station joins in 2025: the all-station mean falls more than the panel's
    v = C.mark_panel(C.select(_city([("B", "u1", 2025, 20, 22)]), C.PRIMARY), C.PRIMARY)
    ch = C.city_changes(v, C.PRIMARY).iloc[0]
    assert ch.chg_raw_panel == pytest.approx(-20)
    assert ch.corrected == pytest.approx(-10)
    assert ch.reported == pytest.approx(100 * ((80 + 20) / 2 / 100 - 1))  # -50%
    assert ch.comp_raw < 0  # composition made the reported fall larger
    assert ch.h4 == pytest.approx(ch.corrected - ch.reported) and ch.h4 > 0  # DEC-127: supports H4
    assert ch.n_panel == 1 and ch.n_all_base == 1 and ch.n_all_end == 2


def test_units_without_a_panel_are_left_out():
    v = C.mark_panel(C.select(_sy([("Z", "u9", 2019, 50, 50), ("Z", "u9", 2025, 40, 40)]), C.PRIMARY), C.PRIMARY)
    assert C.city_changes(v, C.PRIMARY).empty


def test_select_applies_rule_variant_and_exclusions():
    sy = _city([("S", "u1", 2025, 30, 30)])
    sy.loc[sy.sid == "S", "reliability"] = 40.0
    other = sy.assign(rule="registered_flags")
    sy = pd.concat([sy, other, sy.assign(variant="q1_t60")], ignore_index=True)
    assert len(C.select(sy, C.PRIMARY)) == 9
    assert "S" not in set(C.select(sy, C.Spec(drop_rel50=True)).sid)
    posthoc = C.params()["posthoc_drop_registered"][0]
    sy2 = sy.assign(sid=sy.sid.replace({"S": posthoc}))
    reg = C.select(sy2, C.Spec(rule="registered_flags", drop_posthoc=True))
    assert posthoc not in set(reg.sid) and len(reg) == 8


def test_station_bootstrap_has_no_spread_with_one_station_per_stratum():
    v = C.mark_panel(C.select(_city([("B", "u1", 2025, 20, 22)]), C.PRIMARY), C.PRIMARY)
    b = C.station_bootstrap(v, C.PRIMARY, draws=50, seed=1).iloc[0]
    ch = C.city_changes(v, C.PRIMARY).iloc[0]
    assert b.h4_lo == pytest.approx(ch.h4) and b.h4_hi == pytest.approx(ch.h4)


def test_station_bootstrap_spreads_with_several_panel_stations():
    rows = [(s, "u1", y, 100 * f, 100 * f * (1 - 0.01 * (y - 2018) * k)) for s, f, k in (("A", 1, 1), ("B", 2, 3), ("C", 1.5, 0))
            for y in range(2018, 2026)]  # fmt: skip
    v = C.mark_panel(C.select(_sy(rows), C.PRIMARY), C.PRIMARY)
    b = C.station_bootstrap(v, C.PRIMARY, draws=200, seed=1).iloc[0]
    assert b.corrected_hi > b.corrected_lo


def test_cluster_boot_mean_and_constant_case():
    rng = np.random.default_rng(0)
    s = C.cluster_boot(np.array([2.0, 2.0, 2.0, np.nan]), 100, rng)
    assert s["n"] == 3 and s["mean"] == 2 and s["lo"] == 2 and s["hi"] == 2 and s["se"] == 0
    s = C.cluster_boot(np.arange(10.0), 500, rng)
    assert s["lo"] < 4.5 < s["hi"] and s["mean"] == pytest.approx(4.5)


def test_entrants_log_ratio_and_paired_difference():
    rows = [("A", "u1", y, 100.0, 100.0) for y in range(2018, 2021)] + [("B", "u1", 2020, 50.0, 60.0)]
    e = C.entrants(_sy(rows))
    r = e[e.year == 2020].iloc[0]
    assert r.lr_raw == pytest.approx(np.log(0.5))
    assert r.lr_dw_gam == pytest.approx(np.log(0.6))
    assert r.diff_dw_gam == pytest.approx(np.log(0.6) - np.log(0.5))
    assert len(e) == 1  # 2018 and 2019 have no entrant; 2018 has no incumbent


def test_specs_include_primary_as_registered_and_unique_labels():
    s = C.specs()
    labels = [x.label for x in s]
    assert len(labels) == len(set(labels))
    assert C.PRIMARY.label in labels and C.AS_REGISTERED.label in labels
    assert all(x.rule == "registered_flags" for x in s if x.drop_posthoc)
    assert {x.family for x in s if x.kind == "one-at-a-time"} == {"gam", "lgbm"}


def test_h4_table_supported_only_with_positive_ci():
    ch = pd.DataFrame({"spec": C.PRIMARY.label, "pollutant": "pm25", "unit_id": [f"u{i}" for i in range(6)],
                       "h4": [5.0, 6, 7, 4, 5, 6], "n_panel": 1, "reported": -20.0, "corrected": -14.0,
                       "h4_weather": 3.0, "h4_composition": 3.0, "watch_stations": "",
                       "n_all_base": 1, "n_all_end": 1, "guard_all": 0, "guard_panel": 0, "h4_unmodelled": 1.0,
                       "h4_raw_minus_dw": 3.0})  # fmt: skip
    t = C.h4_table(ch, set(ch.unit_id), [C.PRIMARY], 500).iloc[0]
    assert t.supported and t.h4_lo > 0 and np.isnan(t.detectable_2p8se)
    ch2 = ch.assign(h4=[5.0, -6, 7, -4, 5, -6])
    t2 = C.h4_table(ch2, set(ch2.unit_id), [C.PRIMARY], 500).iloc[0]
    assert not t2.supported and t2.detectable_2p8se == pytest.approx(2.8 * t2.h4_se)


# --- family-disagreement diagnostic (src/normalise/family_diag.py) --------------------------------


def test_model_parts_map_to_variable_groups():
    from src.normalise.family_diag import group_of

    assert group_of("s(blh_mean)") == group_of("blh_pm") == "boundary layer"
    assert group_of("ti(ws,wd)") == group_of("s(wd)") == group_of("ws") == "wind"
    assert group_of("s(precip_l)") == group_of("precip") == "precipitation"
    assert group_of("s(trend)") == group_of("trend") == "trend"
    assert group_of("weekday") == group_of("s(doy)") == "calendar"
    assert group_of("intercept") is None and group_of("bias") is None


def test_grouped_sums_parts_within_a_group_and_drops_the_constant():
    from src.normalise.family_diag import grouped

    parts = pd.DataFrame({"s(ws)": [1.0, 2.0], "ti(ws,wd)": [0.5, 0.5], "s(blh_mean)": [-1.0, 0.0], "intercept": 9.0})
    g = grouped(parts)
    assert set(g.columns) == {"wind", "boundary layer"}
    assert list(g.wind) == [1.5, 2.5]

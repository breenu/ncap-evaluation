"""Phase 4 pre-gate rules: treatment timing, control pool, spillover distance, seasons, balance,
the post-2018 guard, and the plan's generated-number markers.

All data here are SYNTHETIC, generated in the test (CLAUDE.md hard rule 1).
"""

import geopandas as gpd
import numpy as np
import pandas as pd
import pytest
from shapely.geometry import box

from src.causal import pregate, pregate_report, treatment

# ---------------------------------------------------------------- treatment timing


@pytest.mark.parametrize(
    "date, year",
    [
        ("2017-06-09", 2019),  # pre-NCAP list: nothing is treated before launch
        ("2019-01-10", 2019),
        ("2020-06-04", 2020),
        ("2020-06-30", 2020),  # the cut-off day itself counts
        ("2020-07-01", 2021),
        ("2020-12-08", 2021),
        ("2021-06-18", 2021),
    ],
)
def test_listed_year(date, year):
    assert treatment.listed_year(date, first_year=2019, listed_by="06-30") == year


def test_funded_year_is_the_calendar_year_after_the_fy_starts():
    assert treatment.funded_year(2019) == 2020  # FY2019-20 -> 2020


def _funding(rows):
    cols = ["cities", "level", "measure", "value", "source_doc"]
    return pd.DataFrame(rows, columns=cols)


def test_first_release_fy_rules():
    f = _funding([
        ("A", "city", "released_fy2019_20", 1.0, "ls17_au2467_2022_08_01"),
        ("B", "city", "released_fy2019_20", 0.0, "ls17_au2467_2022_08_01"),
        ("B", "city", "released_fy2020_21", 2.0, "ls17_au2467_2022_08_01"),
        ("C;D", "city", "released_fy2021_22", 1.0, "ls17_au2467_2022_08_01"),  # combined row
        ("F", "city", "released_to_fy2023_24", 5.0, treatment.CUMULATIVE_DOC),
        ("H", "city", "released_fy2019_20", 3.0, "ls17_au2467_2022_08_01"),
    ])  # fmt: skip
    channels = pd.Series({"A": "NCAP", "B": "NCAP", "C": "NCAP", "D": "NCAP", "E": "XVFC", "F": "NCAP",
                          "G": "NCAP", "H": "XVFC"})  # fmt: skip
    got = treatment.first_release_fy(f, channels).set_index("city")
    assert got.fy_first["A"] == 2019
    assert got.fy_first["B"] == 2020  # a zero release does not count
    assert got.fy_first["C"] == got.fy_first["D"] == 2021
    assert got.fy_first["E"] == treatment.XVFC_FIRST_FY  # XV-FC city with no per-FY row
    assert got.fy_first["H"] == 2019  # an earlier NCAP-channel release beats the XV-FC start
    assert (got.fy_first["F"], got.fy_first_upper["F"]) == (
        2022,
        2023,
    )  # interval from a cumulative table
    assert pd.isna(got.fy_first["G"])


def test_unit_takes_earliest_member_and_rejects_unknown_cities():
    cc = pd.DataFrame({"city": ["A", "B"], "cohort_listed": [2020, 2019], "cohort_funded": [2021, 2020],
                       "cohort_funded_upper": [2021, 2020]})  # fmt: skip
    units = pd.DataFrame({"unit_id": ["u1", "u2"], "ncap_cities": ["A;B", ""]})
    got = treatment.unit_cohorts(units, cc)
    assert list(got.unit_id) == ["u1"] and got.cohort_listed.iloc[0] == 2019
    with pytest.raises(ValueError, match="Z"):
        treatment.unit_cohorts(pd.DataFrame({"unit_id": ["u3"], "ncap_cities": ["Z"]}), cc)


# ---------------------------------------------------------------- pool and spillover


def _units():
    # SYNTHETIC unit table covering every role
    return pd.DataFrame({
        "unit_id": ["t", "c_far", "c_near", "small", "holds_town", "town"],
        "ncap_cities": ["X", "", "", "", "", "Y"],
        "in_primary": [True, True, True, True, True, False],
        "pop_2015": [5e5, 2e5, 2e5, 5e4, 3e5, np.nan],
        "contains_ncap_town": ["", "", "", "", "Y", ""],
        "dist_ncap_km": [0.0, 60.0, 5.0, 70.0, 1.0, 0.0],
    })  # fmt: skip


def test_assign_roles():
    got = pregate.assign_roles(_units(), min_pop=100_000, buffer_km=25).set_index("unit_id")
    assert got.role["t"] == "treated"
    assert got.role["c_far"] == got.role["c_near"] == "control"
    assert got.role["small"] == "below population threshold"
    assert got.role["holds_town"] == "contains an NCAP town"
    assert got.role["town"].startswith("town_buffer")
    assert got.in_buffered_pool.to_dict() == {"t": False, "c_far": True, "c_near": False, "small": False,
                                              "holds_town": False, "town": False}  # fmt: skip


def test_distance_to_ncap_ignores_own_polygon_and_measures_edges():
    # SYNTHETIC squares in central India, 0.1 degree wide, gaps of 0.1 and 0.5 degree
    geoms = [box(78.0, 22.0, 78.1, 22.1), box(78.2, 22.0, 78.3, 22.1), box(78.8, 22.0, 78.9, 22.1)]
    g = gpd.GeoDataFrame(
        {"unit_id": ["t1", "t2", "c"], "ncap_cities": ["A", "B", ""]}, geometry=geoms, crs=4326
    )
    d = pregate.distance_to_ncap_km(g)
    assert 9 < d["t1"] < 12  # to t2, not to itself (0)
    assert 9 < d["t2"] < 12
    assert 50 < d["c"] < 56  # ~0.5 degree of longitude at 22N


# ---------------------------------------------------------------- seasons, trends, balance


def test_season_panel_assigns_jan_feb_to_previous_winter_and_drops_incomplete():
    months = [(y, m) for y in (2016, 2017) for m in range(1, 13)]
    df = pd.DataFrame({"unit_id": "u", "year": [y for y, _ in months], "month": [m for _, m in months],
                       "pm25_popw": [100.0 if m in (10, 11, 12, 1, 2) else 10.0 for _, m in months]})  # fmt: skip
    df["pm25_area"] = df.pm25_popw
    got = pregate.season_panel(df, [10, 11, 12, 1, 2]).set_index(["season", "season_year"])
    assert ("winter", 2016) in got.index  # Oct 2016 - Feb 2017
    assert ("winter", 2015) not in got.index  # only Jan-Feb 2016 present
    assert ("winter", 2017) not in got.index  # Jan-Feb 2018 missing
    assert got.loc[("winter", 2016)].pm25_popw == 100.0
    assert got.loc[("nonwinter", 2017)].pm25_popw == 10.0


def test_unit_slope_recovers_growth_rate():
    yrs = np.arange(2010, 2019)
    df = pd.DataFrame({"unit_id": "u", "year": yrs, "pm25_popw": 50 * 1.03 ** (yrs - 2010)})
    assert np.isclose(np.exp(pregate.unit_slope(df)["u"]) - 1, 0.03)


def test_smd():
    a, b = pd.Series([1.0, 3.0]), pd.Series([0.0, 2.0])
    assert np.isclose(pregate.smd(a, b), 1 / np.sqrt(2))
    assert np.isclose(pregate.smd(pd.Series([1, 1, 0, 0]), pd.Series([0, 0, 0, 0]), binary=True),
                      0.5 / np.sqrt(0.125))  # fmt: skip


# ---------------------------------------------------------------- the post-2018 guard


def test_read_pre_period_never_returns_post_2018(tmp_path):
    p = tmp_path / "panel.parquet"
    pd.DataFrame({"unit_id": "u", "year": [2017, 2018, 2019, 2020], "product": "V5GL06",
                  "pm25_popw": [1.0, 2, 3, 4]}).to_parquet(p)  # fmt: skip
    got = pregate.read_pre_period(p, last=2018, product="V5GL06")
    assert got.year.max() == 2018 and len(got) == 2
    with pytest.raises(pregate.PostPeriodLeak):
        pregate.assert_pre_period(pd.DataFrame({"year": [2018, 2019]}), last=2018)


def test_ground_counts_by_group_and_consecutive_pairs():
    sy = pd.DataFrame({
        "sid": ["a", "a", "b", "c"], "year": [2017, 2018, 2018, 2018], "pollutant": "pm10",
        "unit_id": ["n1", "n1", "n2", "x"], "valid_q1_t75": [True, True, True, True],
    })  # fmt: skip
    counts, pairs = pregate.ground_counts(sy, ncap_units={"n1", "n2"})
    c = counts.set_index(["year", "group"]).station_years
    assert c[(2018, "NCAP unit")] == 2 and c[(2018, "non-NCAP unit")] == 1
    p = pairs.set_index(["years", "group"]).stations
    assert p[("2017-2018", "NCAP unit")] == 1 and p[("2017-2018", "non-NCAP unit")] == 0


# ---------------------------------------------------------------- MDE arithmetic and plan markers


def test_mde_table_is_multiplier_times_sd_of_placebo_atts():
    rng = np.random.default_rng(0)
    rows = [{"design": "random", "draw": d, "fake_year": 2014, "outcome": o, "att": rng.normal(0, s)}
            for d in range(200) for o, s in [("log_annual", 0.02), ("level_annual", 1.0),
                                             ("log_winter", 0.03), ("log_nonwinter", 0.02)]]  # fmt: skip
    draws = pd.DataFrame(rows)
    t = pregate_report.mde_table(draws, 2.8).set_index("outcome")
    assert (t.design == "random").all()
    sd = draws[draws.outcome == "log_annual"].att.std(ddof=1)
    assert np.isclose(t.loc["log_annual"].mde, 2.8 * sd)
    assert "winter_minus_nonwinter" in t.index
    assert np.isclose(pregate_report.pct_reduction(np.log(2)), 50.0)


def test_plan_markers_fill_and_check():
    text = "MDE <!--g:mde-->?<!--/g-->%, pool <!--g:n-->?<!--/g-->.\n<!--g:tab-->\nold\n<!--/g-->"
    vals = {"mde": "6.1", "n": "923", "tab": "\n| a |\n"}
    out = pregate_report.fill(text, vals)
    assert "MDE <!--g:mde-->6.1<!--/g-->%" in out and "old" not in out
    assert pregate_report.stale(out, vals) == []
    assert pregate_report.stale(out, {**vals, "n": "900"}) == ["n"]
    with pytest.raises(KeyError):
        pregate_report.fill("<!--g:nope-->x<!--/g-->", vals)


def test_equal_tailed_p_does_not_assume_a_null_centred_on_zero():
    # SYNTHETIC null centred at -1: an ATT of -1 is typical (p ~ 1), an ATT of +1 is extreme
    null = pd.Series(np.linspace(-2, 0, 201))
    assert pregate_report.p_equal_tailed(null, -1.0) > 0.95
    assert pregate_report.p_equal_tailed(null, 1.0) < 0.02
    # the |ATT| rule would call -1 and +1 equally (un)usual; this one does not
    assert pregate_report.p_equal_tailed(null, 1.0) < pregate_report.p_equal_tailed(null, -1.0)


def test_log_units_are_labelled_as_log_units_and_percent():
    assert pregate_report.lg(0.0047) == "+0.0047"
    assert pregate_report.pc(0.0047) == "+0.47%"
    assert pregate_report.pc(0.47) == "+60.00%"  # what "0.47 log points" was misread as


def test_monitor_gain_counts_only_stations_inside_and_new_in_window():
    # SYNTHETIC: unit a gains a station in 2020; b only has a 2016 station; c's 2021 station lies outside
    # its polygon; d has a station that first reports in 2025, after the satellite window
    first = pd.Series({"s1": 2016, "s2": 2020, "s3": 2016, "s4": 2021, "s5": 2025})
    st = pd.DataFrame({"sid": ["s1", "s2", "s3", "s4", "s5"], "unit_id": ["a", "a", "b", "c", "d"],
                       "km_to_unit": [0.0, 0.0, 0.0, 3.2, 0.0]})  # fmt: skip
    got = pregate.monitor_gain(first, st, pd.Series(["a", "b", "c", "d"]), [2019, 2024]).set_index(
        "unit_id"
    )
    assert got.gained_monitor.to_dict() == {"a": True, "b": False, "c": False, "d": False}
    assert got.stations_before["a"] == 1 and got.stations_new["a"] == 1
    assert got.stations_before["c"] == 0  # outside the polygon: not counted


def test_osf_export_strips_markers_replaces_status_and_pins_links():
    from src.causal import osf_export

    # SYNTHETIC plan text
    text = ("# Plan\n\n*Status: draft, with `sync-plan` notes.*\n\nMDE <!--g:mde-->1.2<!--/g-->%.\n\n"
            "<!--g:tab-->\n\n| a |\n|---|\n| 1 |\n\n<!--/g-->\n\nSee [checks](pregate_checks.md) and "
            "[web](https://example.org).\n")  # fmt: skip
    out = osf_export.clean(text, "abc123", "2026-09-27")
    assert "<!--" not in out and "MDE 1.2%." in out and "| 1 |" in out
    assert "Status:" not in out and "commit `abc123`" in out and "version of 2026-09-27" in out
    assert f"]({osf_export.REPO_URL}/blob/abc123/docs/pregate_checks.md)" in out
    assert "](https://example.org)" in out  # absolute links untouched
    with pytest.raises(ValueError):
        osf_export.clean("# Plan\n\nno status here\n", "abc123", "2026-09-27")

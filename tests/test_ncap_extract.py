"""NCAP extraction and validation rules. All strings and tables are SYNTHETIC (made up to
look like the printed layouts; no real document text)."""

from datetime import date

import pandas as pd
import pytest

from src.acquire.firms import chunks
from src.acquire.ncap_extract import (
    _split_row,
    clean,
    parse_number,
    split_name_numbers,
    state_prefix,
)
from src.acquire.ncap_validate import Matcher, norm
from src.acquire.stations import snap_to_grid, split_name


@pytest.mark.parametrize(
    "raw, value",
    [
        ("6.00", 6.0),
        ("1,234.5", 1234.5),
        ("-", 0.0),
        ("NIL", 0.0),
        ("*4.95", 4.95),
        ("4.95*", 4.95),
        ("", None),
        ("Delhi", None),
    ],
)
def test_parse_number(raw, value):
    assert parse_number(raw) == value


def test_clean_rejoins_vertically_printed_number():
    assert clean("3 . 6 2") == "3.62"
    assert clean("2 0 . 96") == "20.96"
    assert clean("Uttar\nPradesh") == "Uttar Pradesh"  # text is only whitespace-normalised
    assert clean("12 34") == "1234"  # documented behaviour: digit runs split by spaces are joined


def test_state_prefix():
    assert state_prefix("Andhra Pradesh Vijayawada") == ("Andhra Pradesh", "Vijayawada")
    assert state_prefix("Orissa") == ("Odisha", "")
    assert state_prefix("Vijayawada") == (None, "Vijayawada")


def test_split_name_numbers_keeps_dashes_and_needs_enough_numbers():
    assert split_name_numbers("Kochi U.A. 2.12 - 59 59") == (
        "Kochi U.A.",
        ["2.12", "-", "59", "59"],
    )
    assert split_name_numbers("Total 141.97 4400 4829 9229") == (
        "Total",
        ["141.97", "4400", "4829", "9229"],
    )
    assert (
        split_name_numbers("Some footnote with 2 numbers 5") is None
    )  # fewer than 3 trailing numbers


def test_split_row_compacts_irregular_grid():
    assert _split_row(["43", "Madhya", "", "Bhopal", None and "", "10.00", "-"]) == (
        "43",
        ["Madhya", "Bhopal"],
        ["10.00", "-"],
    )
    assert _split_row(["", "Pradesh", "", "10.00", "-", "-", "10.00", ""]) == (
        "",
        ["Pradesh"],
        ["10.00", "-", "-", "10.00"],
    )


def test_matcher_exact_alias_and_exclusions():
    m = Matcher(
        ["Vijayawada", "Bangalore", "Asansol & Raniganj"],
        {
            "aliases": {
                "Bruhat Bangalore": {"to": ["Bangalore"], "why": "renamed"},
                "Asansol": {"to": ["Asansol & Raniganj"], "why": "renamed"},
            },
            "not_ncap": ["Kochi"],
            "not_city": ["Jammu & Kashmir"],
        },
    )
    assert m.match("Vijayawada U.A.") == (["Vijayawada"], "exact")  # UA suffix normalised away
    assert m.match("Bruhat Bangalore UA") == (["Bangalore"], "renamed")
    assert m.match("Asansol UA") == (["Asansol & Raniganj"], "renamed")
    assert m.match("Kochi U.A.") == ([], "not_ncap")
    assert m.match("Jammu & Kashmir") == ([], "not_city")
    assert m.match("Vijaywada") == ([], "unmatched")  # no fuzzy matching


def test_norm_strips_ua_codes():
    assert norm("Howrah K UA") == norm("Howrah") == "howrah"
    assert norm("Greater Mumbai (GM) UA") == "greatermumbai"


def test_station_name_split_and_grid():
    assert split_name("Anand Vihar, New Delhi - DPCC") == ("anand vihar", "delhi", "dpcc")
    assert split_name("IGI Airport") == ("igi airport", "", "")
    assert (
        snap_to_grid(28.61) == 28.5
        and snap_to_grid(77.21) == 77.25
        and snap_to_grid(-0.13) == -0.25
        and snap_to_grid(0.12) == 0.0
    )


def test_firms_chunks_cover_range_without_gaps():
    cs = list(chunks(date(2025, 1, 1), date(2025, 1, 12), step=5))
    assert cs == [
        (date(2025, 1, 1), date(2025, 1, 5)),
        (date(2025, 1, 6), date(2025, 1, 10)),
        (date(2025, 1, 11), date(2025, 1, 12)),
    ]


def test_offset_scan_recovers_known_shift():
    """SYNTHETIC: mirror labels are UTC + 5.5 h; the scan must find +5.5."""
    from src.acquire.mirror_checks import offset_scan

    utc = pd.date_range("2025-01-01", periods=2000, freq="15min")
    rng = pd.Series(range(2000), dtype=float).sample(frac=1, random_state=0).to_numpy()
    openaq = pd.DataFrame({"utc": utc, "value": rng})
    mirror = pd.DataFrame({"label": utc + pd.Timedelta(hours=5.5), "value": rng})
    s = offset_scan(mirror, openaq)
    best = s.loc[s.exact_share.idxmax()]
    assert best.offset_h == 5.5 and best.exact_share == 1.0
    assert s.loc[s.offset_h == 0, "exact_share"].iloc[0] < 0.01

"""NCAP treatment timing: which calendar year each city and satellite unit counts as treated from.

Two definitions (docs/analysis_plan.md §2):

- **Listed (primary).** The date a city first appears on an official NCAP list
  (`data/interim/ncap_cities.csv`, DEC-043/044). Listed on or before 30 June -> treated from that
  calendar year, otherwise from the next. Nothing is treated before NCAP's launch year (2019): the
  94 cities on CPCB's 2017 non-attainment list join the 2019 cohort.
- **Funded (alternative).** The first financial year with a recorded central release
  (`data/interim/ncap_funding_clean.csv`). A release in FY t-(t+1) counts from calendar year t+1,
  the first calendar year in which the money could have been spent for most of the year (DEC-086).

A unit shared by several NCAP cities takes its earliest member's year.

These are treatment data, not outcomes: nothing here reads pollution.
"""

import datetime as dt
import re

import pandas as pd

from src.common.paths import params

# Per-financial-year release columns (Lok Sabha AU2467, NCAP channel, FY2019-20 to FY2021-22).
FY_RELEASE = re.compile(r"^released_fy(\d{4})_(\d{2})$")
# The XV Finance Commission air-quality grant starts in FY2020-21 (2020-21 report, Annex 5.3).
XVFC_FIRST_FY = 2020
# Lok Sabha AU2080 (Dec 2024): cumulative releases to FY2023-24. A city first seen here was first
# funded in FY2022-23 or FY2023-24 (the per-FY series ends in FY2021-22).
CUMULATIVE_DOC = "ls18_au2080_2024_12_09"
PER_FY_LAST = 2021


def listed_year(
    date: str | dt.date, first_year: int | None = None, listed_by: str | None = None
) -> int:
    """Calendar year a city listed on `date` counts as treated from."""
    P = params()["treatment"]
    first_year = P["first_year"] if first_year is None else first_year
    listed_by = P["listed_by"] if listed_by is None else listed_by
    d = pd.Timestamp(date).date()
    month, day = (int(x) for x in listed_by.split("-"))
    year = d.year if (d.month, d.day) <= (month, day) else d.year + 1
    return max(year, first_year)


def funded_year(fy_start: int) -> int:
    """Calendar year a first release in FY fy_start-(fy_start+1) counts as treated from."""
    return fy_start + 1


def first_release_fy(funding: pd.DataFrame, channels: pd.Series) -> pd.DataFrame:
    """First financial year (its start year) with a recorded central release, per city.

    `funding`: ncap_funding_clean.csv rows. `channels`: city -> 'NCAP' or 'XVFC' (ncap_cities.csv).
    Returns city, fy_first (start year), fy_first_upper (same unless only an interval is known), source.
    """
    rows = funding[funding.cities.notna() & (funding.level == "city")].copy()
    rows["city"] = rows.cities.str.split(";")
    rows = rows.explode("city")

    per_fy = rows[rows.measure.str.match(FY_RELEASE) & (rows.value > 0)].copy()
    per_fy["fy"] = per_fy.measure.str.extract(FY_RELEASE)[0].astype(int)
    first = per_fy.groupby("city").fy.min()

    out = []
    for city, channel in channels.items():
        if city in first.index and (channel != "XVFC" or first[city] <= XVFC_FIRST_FY):
            out.append((city, int(first[city]), int(first[city]), "per-FY release (AU2467)"))
        elif channel == "XVFC":
            out.append((city, XVFC_FIRST_FY, XVFC_FIRST_FY, "XV-FC grant from FY2020-21"))
        elif ((rows.city == city) & (rows.source_doc == CUMULATIVE_DOC) & (rows.value > 0)).any():
            out.append(
                (
                    city,
                    PER_FY_LAST + 1,
                    PER_FY_LAST + 2,
                    "cumulative only (AU2080): FY2022-23 or FY2023-24",
                )
            )
        else:
            out.append((city, pd.NA, pd.NA, "no release recorded"))
    return pd.DataFrame(out, columns=["city", "fy_first", "fy_first_upper", "fy_source"])


def city_cohorts(cities: pd.DataFrame, funding: pd.DataFrame) -> pd.DataFrame:
    """Per NCAP city: cohort_listed (primary) and cohort_funded (alternative; lower bound if interval)."""
    c = cities[["city", "channel", "first_listed_date"]].copy()
    c["cohort_listed"] = c.first_listed_date.map(listed_year)
    fr = first_release_fy(funding, c.set_index("city").channel)
    c = c.merge(fr, on="city", how="left")
    c["cohort_funded"] = c.fy_first.map(lambda v: pd.NA if pd.isna(v) else funded_year(int(v)))
    c["cohort_funded_upper"] = c.fy_first_upper.map(
        lambda v: pd.NA if pd.isna(v) else funded_year(int(v))
    )
    return c


def unit_cohorts(units: pd.DataFrame, city_c: pd.DataFrame) -> pd.DataFrame:
    """Per treated unit: the earliest member city's cohorts. `units` needs unit_id and ncap_cities (';'-joined)."""
    u = units.loc[units.ncap_cities.fillna("") != "", ["unit_id", "ncap_cities"]].copy()
    u["city"] = u.ncap_cities.str.split(";")
    u = u.explode("city").merge(city_c, on="city", how="left", validate="many_to_one")
    missing = u[u.cohort_listed.isna()].city.tolist()
    if missing:
        raise ValueError(f"NCAP cities in units but not in ncap_cities.csv: {missing}")
    agg = {"cohort_listed": "min", "cohort_funded": "min", "cohort_funded_upper": "min"}
    for col in agg:
        u[col] = pd.to_numeric(u[col], errors="coerce")
    return u.groupby("unit_id", as_index=False).agg(agg)

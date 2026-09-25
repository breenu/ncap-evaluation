"""Tests for the step 0 probe logic. All inputs are SYNTHETIC (made-up ids, coordinates, XML)."""

import pandas as pd
import pytest

from src.acquire import s3
from src.acquire.probe import _in_years
from src.acquire.probe_report import cluster_sites, coverage_by_year, haversine_km, unit_months


def test_haversine_known_distance():
    # one degree of latitude is about 111.2 km
    assert haversine_km(28.0, 77.0, 29.0, 77.0) == pytest.approx(111.2, abs=0.2)


def test_cluster_sites_merges_close_locations_only():
    coords = {
        10: (28.6468, 77.3160),  # synthetic "station A"
        20: (28.6470, 77.3162),  # ~30 m from 10: same site
        30: (28.6500, 77.3160),  # ~360 m from 10: same site
        40: (28.7000, 77.3160),  # ~5.9 km away: different site
    }
    site = cluster_sites(coords, radius_km=0.5)
    assert site[10] == site[20] == site[30] == 10
    assert site[40] == 40


def test_cluster_sites_is_transitive():
    # 1-2 and 2-3 are within 0.5 km but 1-3 are not: single linkage joins all three
    coords = {1: (20.0, 80.0), 2: (20.004, 80.0), 3: (20.008, 80.0)}
    assert len(set(cluster_sites(coords, radius_km=0.5).values())) == 1


def _months(rows):
    return pd.DataFrame(
        rows, columns=["location_id", "sensor_id", "parameter", "month", "observed_days", "pct"]
    )


def test_unit_months_takes_best_sensor_and_drops_empty_months():
    m = _months(
        [
            (1, 11, "pm25", "2019-01", 10, 32.0),
            (1, 12, "pm25", "2019-01", 30, 97.0),  # second sensor, same month: keep 97
            (1, 11, "pm25", "2019-02", 0, 0.0),  # no data: dropped
        ]
    )
    um = unit_months(m, "location_id")
    assert len(um) == 1
    assert um.iloc[0]["pct"] == 97.0


def test_coverage_by_year_counts_both_and_good():
    m = _months(
        [
            (1, 11, "pm25", "2019-01", 30, 97.0),
            (1, 12, "pm10", "2019-01", 20, 65.0),
            (1, 11, "pm25", "2019-02", 28, 100.0),
            (2, 21, "pm10", "2019-01", 31, 100.0),
            (2, 21, "pm10", "2020-05", 31, 100.0),
        ]
    )
    cov = coverage_by_year(unit_months(m, "location_id"), "location_id", good_pct=75.0)
    y19 = cov.loc[2019]
    assert (y19["pm25"], y19["pm10"], y19["both"]) == (2, 2, 1)
    assert (y19["pm25_good"], y19["pm10_good"], y19["both_good"]) == (2, 1, 0)
    assert (y19["units_pm25"], y19["units_pm10"]) == (1, 2)
    assert cov.loc[2020, "pm25"] == 0 and cov.loc[2020, "pm10"] == 1


def test_in_years_parses_acag_names():
    assert _in_years("V5GL06/x/V5GL06.HybridPM25.Asia.200501-200512.nc", (2005, 2024))
    assert not _in_years("V5GL06/x/V5GL06.HybridPM25.Asia.200401-200412.nc", (2005, 2024))
    assert _in_years("V6GL03/x/V6GL03.CNNPM25.0p10.AS.202412-202412.nc", (2005, 2024))


_PAGE1 = b"""<?xml version="1.0" encoding="UTF-8"?>
<ListBucketResult xmlns="http://s3.amazonaws.com/doc/2006-03-01/"><IsTruncated>true</IsTruncated>
<NextContinuationToken>tok</NextContinuationToken>
<Contents><Key>p/</Key><Size>0</Size><ETag>&quot;e0&quot;</ETag><LastModified>t</LastModified></Contents>
<Contents><Key>p/a.nc</Key><Size>5</Size><ETag>&quot;e1&quot;</ETag><LastModified>t1</LastModified></Contents>
</ListBucketResult>"""
_PAGE2 = b"""<?xml version="1.0" encoding="UTF-8"?>
<ListBucketResult xmlns="http://s3.amazonaws.com/doc/2006-03-01/"><IsTruncated>false</IsTruncated>
<Contents><Key>p/b.nc</Key><Size>7</Size><ETag>&quot;e2&quot;</ETag><LastModified>t2</LastModified></Contents>
</ListBucketResult>"""


def test_s3_list_objects_follows_pages_and_skips_folder_markers(monkeypatch):
    """SYNTHETIC S3 responses: two pages, one zero-byte folder marker."""

    class Resp:
        def __init__(self, content):
            self.content = content

        def raise_for_status(self):
            pass

    class Session:
        seen = []

        def get(self, url, params, timeout):
            Session.seen.append(dict(params))
            return Resp(_PAGE2 if "continuation-token" in params else _PAGE1)

    monkeypatch.setattr(s3, "_session", Session)
    objs = list(s3.list_objects("bucket", "p/"))
    assert [(o.key, o.size, o.etag) for o in objs] == [("p/a.nc", 5, "e1"), ("p/b.nc", 7, "e2")]
    assert Session.seen[1]["continuation-token"] == "tok"

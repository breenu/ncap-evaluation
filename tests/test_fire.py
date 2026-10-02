"""Tests for the fire covariate (src/causal/fire.py; DEC-171). SYNTHETIC DATA ONLY: the fire detections and
unit polygons below are made up to check the filtering and the 100 km sum. Nothing is written under data/."""

import geopandas as gpd
import numpy as np
import pandas as pd
import pytest
from shapely.geometry import box

from src.causal import fire as F


def test_read_year_keeps_vegetation_fires_with_nominal_or_high_confidence(tmp_path):
    p = tmp_path / "viirs-snpp_2015_India.csv"
    pd.DataFrame({"latitude": [28.0] * 5, "longitude": [77.0] * 5, "acq_date": ["2015-11-01"] * 5,
                  "confidence": ["h", "n", "l", "h", "n"], "frp": [10.0, 5.0, 99.0, 7.0, 1.0],
                  "type": [0, 0, 0, 2, 3], "satellite": "N"}).to_csv(p, index=False)  # fmt: skip
    d = F.read_year(str(p))
    assert d.frp.tolist() == [10.0, 5.0] and (d.year == 2015).all()


def test_read_year_stops_on_unexpected_codes(tmp_path):
    p = tmp_path / "viirs-snpp_2015_India.csv"
    pd.DataFrame({"latitude": [28.0], "longitude": [77.0], "acq_date": ["2015-11-01"], "confidence": [80],
                  "frp": [1.0], "type": [0]}).to_csv(p, index=False)  # fmt: skip
    with pytest.raises(ValueError, match="confidence"):
        F.read_year(str(p))


def test_unit_fire_sums_frp_within_the_radius_and_fills_zeros():
    # a small square unit near Delhi; one fire inside, one ~50 km east, one ~300 km east
    units = gpd.GeoDataFrame({"unit_id": ["u1", "u2"]}, geometry=[box(77.0, 28.5, 77.1, 28.6), box(88.0, 22.5, 88.1, 22.6)], crs=4326)
    pts = pd.DataFrame({"latitude": [28.55, 28.55, 28.55], "longitude": [77.05, 77.6, 80.2], "year": [2015, 2015, 2015],
                        "frp": [10.0, 20.0, 40.0]})  # fmt: skip
    out = F.unit_fire(pts, units, range(2015, 2017)).set_index(["unit_id", "year"])
    assert out.loc[("u1", 2015), "frp_sum"] == pytest.approx(30.0)
    assert out.loc[("u1", 2016), "frp_sum"] == 0.0 and out.loc[("u2", 2015), "frp_sum"] == 0.0
    assert out.loc[("u1", 2015), "fire"] == pytest.approx(np.log1p(30.0))
    assert len(out) == 4

"""OpenAQ location-year bundling. Objects and bytes are SYNTHETIC."""

import hashlib
import zipfile

import pytest

from src.acquire.openaq import build_zip, listing_id, reference_pm_locations
from src.acquire.s3 import S3Object
from src.common.manifest import RawDataError

FILES = {
    "records/csv.gz/locationid=9/year=2019/month=01/location-9-20190102.csv.gz": b"\x1f\x8bfake-a",
    "records/csv.gz/locationid=9/year=2019/month=01/location-9-20190101.csv.gz": b"\x1f\x8bfake-b",
}


def objs(files=FILES):
    return [
        S3Object(k, len(v), hashlib.md5(v, usedforsecurity=False).hexdigest(), "t")
        for k, v in files.items()
    ]


class Resp:
    def __init__(self, content):
        self.content = content

    def raise_for_status(self):
        pass


def getter(files=FILES):
    return lambda url: Resp(files[url.split(".amazonaws.com/", 1)[1]])


def test_bundle_is_byte_identical_and_deterministic(tmp_path):
    a, b = tmp_path / "a.zip", tmp_path / "b.zip"
    build_zip(objs(), a, get=getter())
    build_zip(list(reversed(objs())), b, get=getter())
    assert a.read_bytes() == b.read_bytes()  # same members -> same zip bytes
    with zipfile.ZipFile(a) as z:
        assert (
            z.read("location-9-20190101.csv.gz")
            == FILES[next(k for k in FILES if k.endswith("0101.csv.gz"))]
        )
        assert all(i.compress_type == zipfile.ZIP_STORED for i in z.infolist())
        index = z.read("_index.csv").decode().splitlines()
    assert index[0] == "key,etag,bytes,sha256" and len(index) == 3


def test_bundle_rejects_bytes_that_do_not_match_etag(tmp_path):
    bad = {k: v + b"corrupt" for k, v in FILES.items()}
    with pytest.raises(RawDataError, match="ETag"):
        build_zip(objs(), tmp_path / "x.zip", get=getter(bad))


def test_listing_id_changes_when_any_member_changes():
    o = objs()
    changed = [o[0], S3Object(o[1].key, o[1].size, "different-etag", "t")]
    assert listing_id(o) == listing_id(list(reversed(o)))
    assert listing_id(o) != listing_id(changed)


def test_reference_pm_locations_filters_monitors_and_parameters():
    locs = [
        {
            "id": 1,
            "isMonitor": True,
            "isMobile": False,
            "sensors": [{"parameter": {"name": "pm25"}}],
        },
        {
            "id": 2,
            "isMonitor": False,
            "isMobile": False,
            "sensors": [{"parameter": {"name": "pm25"}}],
        },
        {
            "id": 3,
            "isMonitor": True,
            "isMobile": True,
            "sensors": [{"parameter": {"name": "pm10"}}],
        },
        {"id": 4, "isMonitor": True, "isMobile": False, "sensors": [{"parameter": {"name": "o3"}}]},
    ]
    assert reference_pm_locations(locs) == [1]

"""Raw-data manifest and idempotent download rules (hard rule 7). All data here is SYNTHETIC."""

import hashlib

import pytest

from src.common.manifest import (
    RawDataError,
    download,
    read_manifest,
    record,
    sha256_file,
    verify,
)

URL = "https://example.org/file.nc"


def test_sha256_matches_hashlib(tmp_path):
    f = tmp_path / "x.bin"
    f.write_bytes(b"synthetic bytes")
    assert sha256_file(f) == hashlib.sha256(b"synthetic bytes").hexdigest()


def test_first_download_records_row(tmp_path, fake_fetch):
    fetch = fake_fetch(b"abc")
    download(tmp_path, "a/file.nc", URL, remote_id="etag1", fetch=fetch)
    row = read_manifest(tmp_path)["a/file.nc"]
    assert row["url"] == URL
    assert row["remote_id"] == "etag1"
    assert row["bytes"] == "3"
    assert row["sha256"] == hashlib.sha256(b"abc").hexdigest()
    assert not (tmp_path / "a" / "file.nc.part").exists()


def test_second_download_is_skipped(tmp_path, fake_fetch):
    fetch = fake_fetch(b"abc")
    download(tmp_path, "f.nc", URL, remote_id="etag1", fetch=fetch)
    download(tmp_path, "f.nc", URL, remote_id="etag1", fetch=fetch)
    assert fetch.calls == 1
    assert len(read_manifest(tmp_path)) == 1


def test_changed_upstream_version_is_refused(tmp_path, fake_fetch):
    download(tmp_path, "f.nc", URL, remote_id="etag1", fetch=fake_fetch(b"abc"))
    with pytest.raises(RawDataError, match="upstream version changed"):
        download(tmp_path, "f.nc", URL, remote_id="etag2", fetch=fake_fetch(b"new"))
    assert (tmp_path / "f.nc").read_bytes() == b"abc"  # original untouched


def test_unrecorded_existing_file_is_refused(tmp_path, fake_fetch):
    (tmp_path / "f.nc").write_bytes(b"who made me?")
    with pytest.raises(RawDataError, match="not in the manifest"):
        download(tmp_path, "f.nc", URL, fetch=fake_fetch(b"abc"))


def test_modified_raw_file_is_detected_on_rerun(tmp_path, fake_fetch):
    download(tmp_path, "f.nc", URL, fetch=fake_fetch(b"abc"))
    (tmp_path / "f.nc").write_bytes(b"abcd")  # someone edited raw data
    with pytest.raises(RawDataError, match="size on disk differs"):
        download(tmp_path, "f.nc", URL, fetch=fake_fetch(b"abc"))


def test_clean_clone_redownload_must_match_hash(tmp_path, fake_fetch):
    download(tmp_path, "f.nc", URL, fetch=fake_fetch(b"abc"))
    (tmp_path / "f.nc").unlink()  # as in a clean clone: manifest present, data absent
    download(tmp_path, "f.nc", URL, fetch=fake_fetch(b"abc"))
    assert (tmp_path / "f.nc").read_bytes() == b"abc"

    (tmp_path / "f.nc").unlink()
    with pytest.raises(RawDataError, match="differ from the recorded sha256"):
        download(tmp_path, "f.nc", URL, fetch=fake_fetch(b"xyz"))
    assert not (tmp_path / "f.nc").exists()
    assert not (tmp_path / "f.nc.part").exists()


def test_failed_fetch_leaves_no_partial_file(tmp_path):
    def broken(url, dest):
        dest.write_bytes(b"half")
        raise ConnectionError("network dropped")

    with pytest.raises(ConnectionError):
        download(tmp_path, "f.nc", URL, fetch=broken)
    assert not (tmp_path / "f.nc").exists()
    assert not (tmp_path / "f.nc.part").exists()
    assert read_manifest(tmp_path) == {}


def test_verify_reports_missing_tampered_and_unrecorded(tmp_path):
    for name, data in [("ok.nc", b"1"), ("gone.nc", b"2"), ("edited.nc", b"3")]:
        (tmp_path / name).write_bytes(data)
        record(tmp_path, name, URL)
    assert verify(tmp_path) == []

    (tmp_path / "gone.nc").unlink()
    (tmp_path / "edited.nc").write_bytes(b"X")
    (tmp_path / "stray.nc").write_bytes(b"?")
    assert sorted(verify(tmp_path)) == [
        "hash mismatch: edited.nc",
        "missing: gone.nc",
        "unrecorded: stray.nc",
    ]

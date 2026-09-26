"""Raw-data manifest and idempotent download rules (hard rule 7). All data here is SYNTHETIC."""

import hashlib

import pytest

from src.common.manifest import (
    RawDataError,
    download,
    read_manifest,
    record,
    s3_md5,
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


def test_failed_fetch_keeps_partial_for_resume_but_records_nothing(tmp_path):
    def broken(url, dest):
        dest.write_bytes(b"half")
        raise ConnectionError("network dropped")

    with pytest.raises(ConnectionError):
        download(tmp_path, "f.nc", URL, remote_id="e1", fetch=broken)
    assert not (tmp_path / "f.nc").exists()  # never a half file under the real name
    assert (tmp_path / "f.nc.part").read_bytes() == b"half"  # kept so the next run resumes
    assert read_manifest(tmp_path) == {}


def test_next_run_resumes_the_partial_file(tmp_path):
    def broken(url, dest):
        dest.write_bytes(b"hal")
        raise ConnectionError("network dropped")

    def resume(url, dest):  # appends the rest, like an HTTP Range request
        with open(dest, "ab") as f:
            f.write(b"f and half")

    with pytest.raises(ConnectionError):
        download(tmp_path, "f.nc", URL, remote_id="e1", fetch=broken)
    download(tmp_path, "f.nc", URL, remote_id="e1", fetch=resume)
    assert (tmp_path / "f.nc").read_bytes() == b"half and half"
    assert not (tmp_path / "f.nc.part").exists()
    assert not (tmp_path / "f.nc.part.json").exists()
    assert read_manifest(tmp_path)["f.nc"]["sha256"] == hashlib.sha256(b"half and half").hexdigest()


def test_partial_from_another_upstream_version_is_discarded(tmp_path, fake_fetch):
    def broken(url, dest):
        dest.write_bytes(b"old-version-bytes")
        raise ConnectionError("network dropped")

    with pytest.raises(ConnectionError):
        download(tmp_path, "f.nc", URL, remote_id="v1", fetch=broken)
    seen = []

    def fetch(url, dest):
        seen.append(dest.exists())
        dest.write_bytes(b"new")

    download(tmp_path, "f.nc", URL, remote_id="v2", fetch=fetch)
    assert seen == [False]  # the v1 partial was deleted before fetching v2
    assert (tmp_path / "f.nc").read_bytes() == b"new"


def test_upstream_checksum_mismatch_is_rejected(tmp_path, fake_fetch):
    good = hashlib.sha256(b"abc").hexdigest()
    download(tmp_path, "ok.nc", URL, fetch=fake_fetch(b"abc"), expected_sha256=good)
    with pytest.raises(RawDataError, match="upstream checksum"):
        download(tmp_path, "bad.nc", URL, fetch=fake_fetch(b"abd"), expected_sha256=good)
    with pytest.raises(RawDataError, match="md5"):
        download(tmp_path, "bad2.nc", URL, fetch=fake_fetch(b"abd"), expected_md5=md5(b"abc"))
    assert not (tmp_path / "bad.nc").exists() and not (tmp_path / "bad.nc.part").exists()
    assert set(read_manifest(tmp_path)) == {"ok.nc"}


def md5(b: bytes) -> str:
    return hashlib.md5(b, usedforsecurity=False).hexdigest()


def test_s3_md5_only_for_single_part_etags():
    assert s3_md5('"d41d8cd98f00b204e9800998ecf8427e"') == "d41d8cd98f00b204e9800998ecf8427e"
    assert s3_md5("abc123-12") is None


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

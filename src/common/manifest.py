"""Raw-data manifest and idempotent, resumable downloads (project rule: raw data are immutable, each file recorded in a manifest).

Each source folder under data/raw/ has a MANIFEST.csv with one row per file:
where it came from, when, the upstream version id (e.g. S3 ETag) and a sha256.
Raw files are never overwritten. Anything that would silently change raw data
raises RawDataError so that a person decides what to do.

Downloads resume: bytes go to `<name>.part`, with a sidecar `<name>.part.json`
recording the url and upstream id. If the connection drops, the next run (or the
next retry inside http_fetch) continues from where it stopped with an HTTP Range
request. A partial file whose sidecar does not match the current url/upstream id
is discarded, so a resume never splices two versions of a file together. Where
the upstream publishes a checksum (S3 single-part ETag = MD5, GitHub asset
digest = sha256), the finished file must match it before it is accepted.

The manifests are committed to git (the data is not), so a clean clone can
re-download and prove it got byte-identical files.
"""

import csv
import hashlib
import json
import threading
import time
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

MANIFEST_NAME = "MANIFEST.csv"
COLUMNS = ["file", "url", "remote_id", "downloaded_utc", "sha256", "bytes", "notes"]

_write_lock = threading.Lock()


class RawDataError(RuntimeError):
    """Raw data would change, or its provenance is unknown. Needs a human decision."""


class IncompleteDownload(ConnectionError):
    """The server closed the connection before sending the whole file."""


def sha256_file(path: Path, chunk: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while block := f.read(chunk):
            h.update(block)
    return h.hexdigest()


def md5_file(path: Path, chunk: int = 1 << 20) -> str:
    h = hashlib.md5(usedforsecurity=False)
    with open(path, "rb") as f:
        while block := f.read(chunk):
            h.update(block)
    return h.hexdigest()


def read_manifest(source_dir: Path) -> dict[str, dict]:
    """Manifest rows keyed by file name (relative to source_dir, forward slashes)."""
    path = source_dir / MANIFEST_NAME
    if not path.exists():
        return {}
    with open(path, newline="", encoding="utf-8") as f:
        return {row["file"]: row for row in csv.DictReader(f)}


def record(
    source_dir: Path,
    name: str,
    url: str,
    remote_id: str = "",
    notes: str = "",
    sha256: str | None = None,
) -> dict:
    """Append a manifest row for a file that is already on disk."""
    file = source_dir / name
    row = {
        "file": name,
        "url": url,
        "remote_id": remote_id,
        "downloaded_utc": datetime.now(UTC).isoformat(timespec="seconds"),
        "sha256": sha256 or sha256_file(file),
        "bytes": str(file.stat().st_size),
        "notes": notes,
    }
    manifest = source_dir / MANIFEST_NAME
    with _write_lock:
        is_new = not manifest.exists()
        with open(manifest, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=COLUMNS)
            if is_new:
                writer.writeheader()
            writer.writerow(row)
    return row


def _session() -> requests.Session:
    s = requests.Session()
    retry = Retry(total=5, backoff_factor=2, status_forcelist=[429, 500, 502, 503, 504])
    s.mount("https://", HTTPAdapter(max_retries=retry))
    return s


_RESUMABLE = (
    requests.ConnectionError,
    requests.Timeout,
    requests.exceptions.ChunkedEncodingError,
    IncompleteDownload,
)


def _total_from_content_range(value: str | None) -> int | None:
    # "bytes 100-199/200" or "bytes */200"
    if value and "/" in value and not value.endswith("/*"):
        return int(value.rsplit("/", 1)[1])
    return None


def http_fetch(
    url: str,
    dest: Path,
    *,
    attempts: int = 8,
    headers: dict | None = None,
    session: requests.Session | None = None,
    sleep: Callable[[float], None] = time.sleep,
) -> None:
    """Stream url to dest, resuming from dest's current size with HTTP Range requests.

    Retries dropped connections with backoff, continuing where it stopped. If the server
    ignores the Range header (HTTP 200), the file is restarted from zero. The finished size
    must equal the total the server announced, otherwise it counts as a dropped connection.
    """
    s = session or _session()
    base = {"Accept-Encoding": "identity", **(headers or {})}
    for attempt in range(attempts):
        have = dest.stat().st_size if dest.exists() else 0
        h = dict(base)
        if have:
            h["Range"] = f"bytes={have}-"
        try:
            with s.get(url, stream=True, timeout=(30, 300), headers=h) as r:
                if r.status_code == 416:  # nothing left to send: already complete?
                    total = _total_from_content_range(r.headers.get("Content-Range"))
                    if total is not None and have == total:
                        return
                    dest.unlink(missing_ok=True)  # local part is longer than the file: restart
                    continue
                r.raise_for_status()
                if have and r.status_code == 206:
                    mode, total = "ab", _total_from_content_range(r.headers.get("Content-Range"))
                else:
                    mode, total = "wb", r.headers.get("Content-Length")
                    total = int(total) if total is not None else None
                with open(dest, mode) as f:
                    for block in r.iter_content(chunk_size=1 << 20):
                        f.write(block)
            size = dest.stat().st_size
            if total is not None and size != total:
                raise IncompleteDownload(f"{url}: got {size} of {total} bytes")
            return
        except _RESUMABLE:
            if attempt == attempts - 1:
                raise
            sleep(min(60, 2**attempt))


def _sidecar(tmp: Path) -> Path:
    return tmp.with_name(tmp.name + ".json")


def download(
    source_dir: Path,
    name: str,
    url: str,
    remote_id: str = "",
    notes: str = "",
    fetch: Callable[[str, Path], None] = http_fetch,
    expected_md5: str | None = None,
    expected_sha256: str | None = None,
) -> Path:
    """Download url to source_dir/name unless the manifest says we already have it.

    - Recorded and present: skip (checks size and upstream id, not the full hash).
    - Recorded but missing (e.g. a clean clone): re-download and require the same sha256.
    - Not recorded but present: unknown provenance, raise.
    - Upstream id changed since recording: raise; raw data is immutable.
    - Interrupted: the .part file is kept and the next call resumes it.
    - Upstream checksum given and not matched: the bytes are discarded and RawDataError raised.
    """
    dest = source_dir / name
    entry = read_manifest(source_dir).get(name)

    if entry and remote_id and entry["remote_id"] and remote_id != entry["remote_id"]:
        raise RawDataError(
            f"{name}: upstream version changed ({entry['remote_id']} -> {remote_id}). "
            "Raw data is immutable; save the new version under a new name if it is wanted."
        )
    if entry and dest.exists():
        if dest.stat().st_size != int(entry["bytes"]):
            raise RawDataError(f"{name}: size on disk differs from manifest; raw file was modified")
        return dest
    if not entry and dest.exists():
        raise RawDataError(f"{name}: file exists but is not in the manifest (unknown provenance)")

    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_name(dest.name + ".part")
    side = _sidecar(tmp)
    ident = {"url": url, "remote_id": remote_id}
    if tmp.exists():
        try:
            same = json.loads(side.read_text(encoding="utf-8")) == ident
        except (OSError, ValueError):
            same = False
        if not same:  # partial bytes from another url/version: never splice them
            tmp.unlink()
    side.write_text(json.dumps(ident), encoding="utf-8")

    fetch(url, tmp)  # on failure, tmp and its sidecar stay for the next run to resume

    def reject(msg: str) -> None:
        tmp.unlink(missing_ok=True)
        side.unlink(missing_ok=True)
        raise RawDataError(f"{name}: {msg}")

    digest = sha256_file(tmp)
    if entry and digest != entry["sha256"]:
        reject("re-downloaded bytes differ from the recorded sha256")
    if expected_sha256 and digest != expected_sha256.lower():
        reject(f"sha256 {digest} does not match the upstream checksum {expected_sha256}")
    if expected_md5 and md5_file(tmp) != expected_md5.lower():
        reject(f"md5 does not match the upstream checksum {expected_md5}")
    tmp.replace(dest)
    side.unlink(missing_ok=True)

    if not entry:
        record(source_dir, name, url, remote_id, notes, sha256=digest)
    return dest


def s3_md5(etag: str) -> str | None:
    """An S3 ETag is the object's MD5 only for single-part uploads (no '-N' suffix)."""
    etag = etag.strip('"')
    return None if "-" in etag else etag


def verify(source_dir: Path) -> list[str]:
    """Full check of a source folder: every recorded file present with the recorded hash,
    and no unrecorded files. Returns a list of problems (empty = all good)."""
    rows = read_manifest(source_dir)
    problems = []
    for name, row in rows.items():
        path = source_dir / name
        if not path.exists():
            problems.append(f"missing: {name}")
        elif sha256_file(path) != row["sha256"]:
            problems.append(f"hash mismatch: {name}")
    on_disk = {
        p.relative_to(source_dir).as_posix()
        for p in source_dir.rglob("*")
        if p.is_file() and p.name != MANIFEST_NAME and not p.name.endswith((".part", ".part.json"))
    }
    problems += [f"unrecorded: {n}" for n in sorted(on_disk - rows.keys())]
    return problems

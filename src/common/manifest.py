"""Raw-data manifest and idempotent downloads (CLAUDE.md hard rule 7).

Each source folder under data/raw/ has a MANIFEST.csv with one row per file:
where it came from, when, the upstream version id (e.g. S3 ETag) and a sha256.
Raw files are never overwritten. Anything that would silently change raw data
raises RawDataError so that a person decides what to do.

The manifests are committed to git (the data is not), so a clean clone can
re-download and prove it got byte-identical files.
"""

import csv
import hashlib
import threading
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


def sha256_file(path: Path, chunk: int = 1 << 20) -> str:
    h = hashlib.sha256()
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


def record(source_dir: Path, name: str, url: str, remote_id: str = "", notes: str = "") -> dict:
    """Append a manifest row for a file that is already on disk."""
    file = source_dir / name
    row = {
        "file": name,
        "url": url,
        "remote_id": remote_id,
        "downloaded_utc": datetime.now(UTC).isoformat(timespec="seconds"),
        "sha256": sha256_file(file),
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


def http_fetch(url: str, dest: Path) -> None:
    """Stream url to dest. Raises on HTTP errors."""
    with _session().get(url, stream=True, timeout=(30, 300)) as r:
        r.raise_for_status()
        with open(dest, "wb") as f:
            for block in r.iter_content(chunk_size=1 << 20):
                f.write(block)


def download(
    source_dir: Path,
    name: str,
    url: str,
    remote_id: str = "",
    notes: str = "",
    fetch: Callable[[str, Path], None] = http_fetch,
) -> Path:
    """Download url to source_dir/name unless the manifest says we already have it.

    - Recorded and present: skip (checks size and upstream id, not the full hash).
    - Recorded but missing (e.g. a clean clone): re-download and require the same sha256.
    - Not recorded but present: unknown provenance, raise.
    - Upstream id changed since recording: raise; raw data is immutable.
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
    try:
        fetch(url, tmp)
        if entry and sha256_file(tmp) != entry["sha256"]:
            raise RawDataError(f"{name}: re-downloaded bytes differ from the recorded sha256")
        tmp.replace(dest)
    finally:
        tmp.unlink(missing_ok=True)

    if not entry:
        record(source_dir, name, url, remote_id, notes)
    return dest


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
        if p.is_file() and p.name != MANIFEST_NAME
    }
    problems += [f"unrecorded: {n}" for n in sorted(on_disk - rows.keys())]
    return problems

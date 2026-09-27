"""Shared helpers for the acquisition modules."""

import sys
from collections.abc import Callable, Iterable
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from src.common.manifest import verify
from src.common.paths import INTERIM


def run_parallel(tasks: Iterable[Callable[[], object]], workers: int, label: str) -> list[str]:
    """Run download tasks in a thread pool. Returns the error messages (empty = all done).

    A failed task does not stop the others: its partial file stays for the next run to resume."""
    tasks = list(tasks)
    errors = []
    with ThreadPoolExecutor(workers) as pool:
        futures = [pool.submit(t) for t in tasks]
        for i, fut in enumerate(as_completed(futures), 1):
            try:
                fut.result()
            except Exception as e:  # noqa: BLE001 - collected and reported, then re-raised below
                errors.append(f"{type(e).__name__}: {e}")
            if i % max(1, len(tasks) // 20) == 0 or i == len(tasks):
                print(f"  {label}: {i}/{len(tasks)} done, {len(errors)} errors", flush=True)
    return errors


def finish(source_dir: Path, source: str, errors: list[str], flag: str | None = None) -> None:
    """Fail loudly on any error; otherwise verify the folder and write the Snakemake flag
    (`acquire_<source>.done`, or `<flag>.done` for a second rule over the same source)."""
    if errors:
        for e in errors[:20]:
            print("  ERROR", e, file=sys.stderr)
        raise SystemExit(f"{source}: {len(errors)} downloads failed; re-run to resume them")
    problems = verify(source_dir)
    if problems:
        raise SystemExit(f"{source}: manifest check failed: {problems[:10]}")
    flag_path = INTERIM / "_flags" / f"{flag or 'acquire_' + source}.done"
    flag_path.parent.mkdir(parents=True, exist_ok=True)
    flag_path.touch()
    print(f"{source}: complete and verified")


def head_id(url: str) -> tuple[str, int | None]:
    """Upstream version id for a plain HTTP file with no published checksum:
    ETag, Last-Modified and size from a HEAD request."""
    from src.common.manifest import _session

    r = _session().head(url, allow_redirects=True, timeout=(30, 60))
    r.raise_for_status()
    size = r.headers.get("Content-Length")
    parts = [
        r.headers.get("ETag", "").strip('"'),
        r.headers.get("Last-Modified", ""),
        f"{size} bytes",
    ]
    return " | ".join(p for p in parts if p), int(size) if size else None

"""Download the NCAP treatment and funding documents listed in config/ncap_sources.yaml.

Each document is saved as data/raw/ncap_docs/<id>.pdf. Internet Archive captures use
the capture timestamp as the upstream id; files from live sites use HEAD metadata
where the server allows it. The manifest records the sha256 of every document.

    python -m src.acquire.ncap_pdfs
"""

import re

from src.acquire.common import finish, head_id, run_parallel
from src.common.manifest import download
from src.common.paths import CONFIG, load_yaml, raw_dir

SOURCE = "ncap_docs"


def documents() -> list[dict]:
    return load_yaml(CONFIG / "ncap_sources.yaml")["documents"]


def upstream_id(doc: dict) -> str:
    m = re.search(r"web\.archive\.org/web/(\d{14})id_/", doc["fetch"])
    if m:
        return f"wayback {m.group(1)}"
    try:
        return head_id(doc["fetch"])[0]
    except Exception:  # noqa: BLE001 - some servers (sansad.in) refuse HEAD; sha256 still recorded
        return ""


def fetch_headers(url: str) -> dict:
    # sansad.in and some government servers reject requests without a browser user agent
    return {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}


def main() -> None:
    from src.common.manifest import http_fetch

    dest = raw_dir(SOURCE)
    tasks = []
    for d in documents():
        tasks.append(
            lambda d=d: download(
                dest,
                f"{d['id']}.pdf",
                d["fetch"],
                remote_id=upstream_id(d),
                notes=f"{d['publisher']}; {d['title'][:120]}; official url {d['url']}",
                fetch=lambda url, tmp: http_fetch(url, tmp, headers=fetch_headers(url)),
            )
        )
    finish(dest, SOURCE, run_parallel(tasks, 3, SOURCE))


if __name__ == "__main__":
    main()

"""CPCB CAAQMS 15-minute station data via the Vonter/india-cpcb-aqi mirror (DEC-037).

CPCB's own data-repository endpoints return 404 (DEC-031). The mirror publishes one
Parquet file per year as a GitHub release asset, each with a sha256 digest, which
every download must match. The mirror's README, DATA.md, LICENSE and scripts are
saved at a pinned commit as provenance (the parse script shows how timestamps were
built, which matters for the timezone check).

    python -m src.acquire.cpcb_mirror
"""

import argparse

from src.acquire.common import finish, run_parallel
from src.common.manifest import _session, download
from src.common.paths import params, raw_dir

SOURCE = "cpcb_mirror"
REPO = "Vonter/india-cpcb-aqi"
API = f"https://api.github.com/repos/{REPO}"
# Commit that produced the 2026-01-07 releases (repo head on 2026-09-26).
PINNED_COMMIT = "a58f47848e678c7cea58a69758343d08d0b49915"
PROVENANCE_FILES = ["README.md", "DATA.md", "LICENSE", "fetch.py", "parse.py", "requirements.txt"]


def release_assets(first: int, last: int) -> list[dict]:
    s = _session()
    out = []
    for year in range(first, last + 1):
        r = s.get(f"{API}/releases/tags/{year}", timeout=(30, 60))
        if r.status_code == 404:
            print(f"  no release for {year}")
            continue
        r.raise_for_status()
        rel = r.json()
        name = f"cpcb-air-quality-{year}.parquet"
        (asset,) = [a for a in rel["assets"] if a["name"] == name]
        out.append({"year": year, "release": rel, "asset": asset})
    return out


def main() -> None:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--workers", type=int, default=3)
    args = ap.parse_args()
    w = params()["windows"]
    first, last = int(w["ground_start"][:4]), int(w["ground_end"][:4])
    dest = raw_dir(SOURCE)

    tasks = []
    for f in PROVENANCE_FILES:
        url = f"https://raw.githubusercontent.com/{REPO}/{PINNED_COMMIT}/{f}"
        tasks.append(
            lambda f=f, url=url: download(
                dest, f"repo@{PINNED_COMMIT[:7]}/{f}", url, remote_id=PINNED_COMMIT
            )
        )
    items = release_assets(first, last)
    print(
        f"{SOURCE}: {len(items)} yearly files, {sum(i['asset']['size'] for i in items) / 1e9:.2f} GB"
    )
    for i in items:
        a, rel = i["asset"], i["release"]
        digest = a.get("digest") or ""
        if not digest.startswith("sha256:"):
            raise SystemExit(
                f"{a['name']}: no sha256 digest published; refusing to download unverified"
            )
        tasks.append(
            lambda a=a, rel=rel, digest=digest: download(
                dest,
                a["name"],
                a["browser_download_url"],
                remote_id=f"asset {a['id']} updated {a['updated_at']}",
                notes=f"release {rel['tag_name']} published {rel['published_at']}; {digest}",
                expected_sha256=digest.removeprefix("sha256:"),
            )
        )
    finish(dest, SOURCE, run_parallel(tasks, args.workers, SOURCE))


if __name__ == "__main__":
    main()

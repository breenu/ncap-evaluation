"""ACAG satellite PM2.5 from the public satpmdata bucket (DEC-001 to DEC-003, DEC-034).

Files keep their bucket key as their path under data/raw/acag/, so the version and
product are visible in every path. Each file is checked against its S3 MD5 ETag.

    python -m src.acquire.acag            # download (resumes, skips what is recorded)
    python -m src.acquire.acag --list     # show what would be downloaded
"""

import argparse

from src.acquire.common import finish, run_parallel
from src.acquire.s3 import list_objects, object_url
from src.common.manifest import download, s3_md5
from src.common.paths import params, raw_dir

BUCKET = "satpmdata"
SOURCE = "acag"

# (S3 folder, role). Roles follow DEC-001/002: V5GL06 primary, V6GL03 comparison,
# V6GL0204 vintage check; monthly coarse grids for seasonal analysis.
PRODUCTS = [
    ("V5GL06/GWRPM25/Annual/Asia/", "primary annual 0.01"),
    ("V5GL06/GWRPM25Uncertainty/Annual/Asia/", "primary annual uncertainty 0.01"),
    ("V5GL06/GWRPM25c0p05/Monthly/Asia/", "primary monthly 0.05"),
    ("V6GL03/CNNPM25/Annual/AS/", "comparison annual 0.01"),
    ("V6GL03/CNNPM25c0p10/Monthly/AS/", "comparison monthly 0.10"),
    ("V6GL0204/CNNPM25/Annual/AS/", "vintage annual 0.01"),
]


def year_of(key: str) -> int:
    """ACAG file names end in .YYYYMM-YYYYMM.nc"""
    return int(key.rsplit(".", 2)[-2].split("-")[0][:4])


def planned() -> list[tuple]:
    first, last = params()["windows"]["satellite_download_years"]
    out = []
    for prefix, role in PRODUCTS:
        for o in list_objects(BUCKET, prefix):
            if o.key.endswith(".nc") and first <= year_of(o.key) <= last:
                out.append((o, role))
    return out


def main() -> None:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--workers", type=int, default=4)
    args = ap.parse_args()
    items = planned()
    print(f"acag: {len(items)} files, {sum(o.size for o, _ in items) / 1e9:.2f} GB")
    if args.list:
        for o, role in items:
            print(f"  {o.key}  {o.size / 1e6:.1f} MB  ({role})")
        return
    dest = raw_dir(SOURCE)
    tasks = [
        (
            lambda o=o, role=role: download(
                dest,
                o.key,
                object_url(BUCKET, o.key),
                remote_id=o.etag,
                notes=f"{role}; s3 last_modified {o.last_modified}",
                expected_md5=s3_md5(o.etag),
            )
        )
        for o, role in items
    ]
    finish(dest, SOURCE, run_parallel(tasks, args.workers, SOURCE))


if __name__ == "__main__":
    main()

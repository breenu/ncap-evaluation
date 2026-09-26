"""GeoNames gazetteer extract for India: town points for NCAP towns that have no GHSL urban centre
(sensitivity analysis only; DEC-063), Raniganj (DEC-064), and station-locality lookups (DEC-066).

Licence: CC BY 4.0 (attribute "GeoNames, geonames.org"). GeoNames republishes the extract daily
with no version number, so the manifest pins the bytes downloaded (ETag + Last-Modified + size, and
sha256); a later re-download that differs is refused rather than silently used.

    python -m src.acquire.geonames
"""

from src.acquire.common import finish, head_id, run_parallel
from src.common.manifest import download
from src.common.paths import raw_dir

SOURCE = "geonames"
BASE = "https://download.geonames.org/export/dump"
FILES = {
    "IN.zip": f"{BASE}/IN.zip",  # all Indian features, 'geoname' table layout (readme.txt)
    "admin1CodesASCII.txt": f"{BASE}/admin1CodesASCII.txt",  # admin1 code -> state name
    "readme.txt": f"{BASE}/readme.txt",  # column definitions and licence
}


def main() -> None:
    dest = raw_dir(SOURCE)
    tasks = [
        lambda name=name, url=url: download(dest, name, url, remote_id=head_id(url)[0])
        for name, url in FILES.items()
    ]
    finish(dest, SOURCE, run_parallel(tasks, 3, SOURCE))


if __name__ == "__main__":
    main()

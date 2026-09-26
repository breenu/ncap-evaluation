"""Natural Earth 1:10m coastline: distance from each urban centre to the sea, for the 'coastal'
region (config/regions.yaml, DEC-065). Public domain (naturalearthdata.com). The file has not
changed since 2021-12-08 (Last-Modified), so the manifest pins it by ETag.

    python -m src.acquire.naturalearth
"""

from src.acquire.common import finish, head_id, run_parallel
from src.common.manifest import download
from src.common.paths import raw_dir

SOURCE = "naturalearth"
FILES = {
    "ne_10m_coastline.zip": "https://naciscdn.org/naturalearth/10m/physical/ne_10m_coastline.zip"
}


def main() -> None:
    dest = raw_dir(SOURCE)
    tasks = [
        lambda name=name, url=url: download(dest, name, url, remote_id=head_id(url)[0])
        for name, url in FILES.items()
    ]
    finish(dest, SOURCE, run_parallel(tasks, 1, SOURCE))


if __name__ == "__main__":
    main()

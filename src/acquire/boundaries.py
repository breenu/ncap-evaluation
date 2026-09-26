"""State and country boundaries from DataMeet (DEC-018), pinned to a commit.

States/Admin2 is used for region assignment (config/regions.yaml) and maps; the
country composite outline follows Survey of India depiction. Data licence CC BY 4.0
(repository code MIT): attribute "DataMeet India community".

    python -m src.acquire.boundaries
"""

from src.acquire.common import finish, run_parallel
from src.common.manifest import download
from src.common.paths import raw_dir

SOURCE = "boundaries"
REPO = "datameet/maps"
PINNED_COMMIT = "b3fbbde595310b397a55d718e0958ce249a4fa1f"  # master head, 2022-05-11
FILES = [
    *(f"States/Admin2.{ext}" for ext in ("shp", "shx", "dbf", "prj", "cpg")),
    "Country/india-composite.geojson",
    "Country/README.md",
    "README.md",
]


def main() -> None:
    dest = raw_dir(SOURCE)
    tasks = [
        lambda f=f: download(
            dest,
            f"datameet@{PINNED_COMMIT[:7]}/{f}",
            f"https://raw.githubusercontent.com/{REPO}/{PINNED_COMMIT}/{f}",
            remote_id=PINNED_COMMIT,
        )
        for f in FILES
    ]
    finish(dest, SOURCE, run_parallel(tasks, 4, SOURCE))


if __name__ == "__main__":
    main()

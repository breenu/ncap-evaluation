"""GHSL Urban Centre Database R2024A (boundaries, population by epoch) and GHS-POP 2020
(population weights for the sensitivity check). DEC-006. Licence: CC BY 4.0 (JRC).

    python -m src.acquire.ghsl
"""

from src.acquire.common import finish, head_id, run_parallel
from src.common.manifest import download
from src.common.paths import raw_dir

SOURCE = "ghsl"
BASE = "https://jeodpp.jrc.ec.europa.eu/ftp/jrc-opendata/GHSL"
FILES = {
    # Newest UCDB R2024A release (V1-2, 2026-05-19); DEC-038.
    "GHS_UCDB_GLOBE_R2024A_V1_2.zip": f"{BASE}/GHS_UCDB_GLOBE_R2024A/GHS_UCDB_GLOBE_R2024A/V1-2/GHS_UCDB_GLOBE_R2024A_V1_2.zip",
    "GHS_UCDB_copyright.txt": f"{BASE}/GHS_UCDB_GLOBE_R2024A/copyright.txt",
    # 2020 population, 30 arc-second (~1 km), WGS84: population-weighted zonal means.
    "GHS_POP_E2020_GLOBE_R2023A_4326_30ss_V1_0.zip": f"{BASE}/GHS_POP_GLOBE_R2023A/GHS_POP_E2020_GLOBE_R2023A_4326_30ss/V1-0/GHS_POP_E2020_GLOBE_R2023A_4326_30ss_V1_0.zip",
}


def main() -> None:
    dest = raw_dir(SOURCE)
    tasks = []
    for name, url in FILES.items():
        tasks.append(
            lambda name=name, url=url: download(dest, name, url, remote_id=head_id(url)[0])
        )
    finish(dest, SOURCE, run_parallel(tasks, 2, SOURCE))


if __name__ == "__main__":
    main()

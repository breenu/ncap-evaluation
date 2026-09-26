"""NASA FIRMS active fires, India: VIIRS S-NPP only, 2012 onwards (DEC-039; supersedes DEC-010).

- 2012-2024: keyless yearly country files (viirs-snpp_<year>_India.csv).
- 2025-01-01 to the end of the ground window: the country API with the MAP_KEY in .env,
  in 5-day requests; standard processing (VIIRS_SNPP_SP) where FIRMS has it, near-real-time
  (VIIRS_SNPP_NRT) after that. The source of every file is in its name and the manifest.

The key never reaches the manifest or logs: URLs are recorded with <MAP_KEY>.
Lowest-priority source (cut item #4).

    python -m src.acquire.firms
"""

import csv
import io
from datetime import date, timedelta

from dotenv import dotenv_values

from src.acquire.common import finish, head_id, run_parallel
from src.common.manifest import _session, download, http_fetch
from src.common.paths import ROOT, params, raw_dir

SOURCE = "firms"
BASE = "https://firms.modaps.eosdis.nasa.gov"
FIRST_YEAR, ARCHIVE_LAST_YEAR = 2012, 2024
DAYS = 5  # the country API returns at most a few days per request


def _key() -> str:
    key = dotenv_values(ROOT / ".env").get("FIRMS_MAP_KEY", "")
    if not key:
        raise SystemExit("FIRMS_MAP_KEY is not set in .env")
    return key


def _redacting_fetch(url: str, key: str):
    """http_fetch whose errors never carry the key (request errors quote the URL)."""

    def fetch(_placeholder_url, tmp):
        try:
            http_fetch(url, tmp)
        except Exception as e:  # noqa: BLE001 - re-raised without the key
            raise ConnectionError(str(e).replace(key, "<MAP_KEY>")) from None

    return fetch


def availability(key: str) -> dict[str, tuple[date, date]]:
    try:
        r = _session().get(f"{BASE}/api/data_availability/csv/{key}/ALL", timeout=(30, 90))
        r.raise_for_status()
    except Exception as e:  # noqa: BLE001 - re-raised without the key
        raise ConnectionError(str(e).replace(key, "<MAP_KEY>")) from None
    out = {}
    for row in csv.DictReader(io.StringIO(r.text)):
        out[row["data_id"]] = (
            date.fromisoformat(row["min_date"]),
            date.fromisoformat(row["max_date"]),
        )
    return out


def chunks(start: date, end: date, step: int = DAYS):
    d = start
    while d <= end:
        yield d, min(d + timedelta(days=step - 1), end)
        d += timedelta(days=step)


def main() -> None:
    dest = raw_dir(SOURCE)
    tasks = []
    for y in range(FIRST_YEAR, ARCHIVE_LAST_YEAR + 1):
        url = f"{BASE}/data/country/viirs-snpp/{y}/viirs-snpp_{y}_India.csv"
        tasks.append(
            lambda url=url, y=y: download(
                dest, f"archive/viirs-snpp_{y}_India.csv", url, remote_id=head_id(url)[0]
            )
        )
    key = _key()
    avail = availability(key)
    sp_end = avail.get("VIIRS_SNPP_SP", (None, date(ARCHIVE_LAST_YEAR, 12, 31)))[1]
    end = date.fromisoformat(params()["windows"]["ground_end"])
    for a, b in chunks(date(ARCHIVE_LAST_YEAR + 1, 1, 1), end):
        src = "VIIRS_SNPP_SP" if b <= sp_end else "VIIRS_SNPP_NRT"
        n = (b - a).days + 1
        path = f"/api/country/csv/{{key}}/{src}/IND/{n}/{a.isoformat()}"
        tasks.append(
            lambda path=path, src=src, a=a: download(
                dest,
                f"api/{src.lower()}_{a.isoformat()}.csv",
                BASE + path.format(key="<MAP_KEY>"),
                notes=f"{src}; FIRMS availability {avail.get(src)}",
                fetch=_redacting_fetch(BASE + path.format(key=key), key),
            )
        )
    finish(dest, SOURCE, run_parallel(tasks, 3, SOURCE))


if __name__ == "__main__":
    main()

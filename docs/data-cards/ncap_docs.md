# Data card: NCAP treatment and funding documents

**Role:** treatment definition and timing (RQ3), funding channel and dose (RQ4). DEC-043, DEC-044.

The full document list, with URLs, dates, pages and parser settings, is `config/ncap_sources.yaml`. Raw PDFs are in `data/raw/ncap_docs/<id>.pdf` with sha256 in the manifest.

| Kind | Documents |
|---|---|
| City lists (dated) | CPCB `Non-Attainment_Cities.pdf`, five versions (PDF CreationDates 2017-06-09, 2020-06-04, 2020-12-08, 2021-06-18, 2022-10-10); NCAP report, MoEFCC, Jan 2019 (Table 4); Lok Sabha AU164 (2023-12-04) and AU386 (2026-02-02) annexures |
| Allocations | XV Finance Commission report 2020-21, Annex 5.3; report 2021-26 Vol II, Annex 7.6 |
| Releases / utilisation | Lok Sabha unstarred answers AU5104 (2022-04-04), AU2467 (2022-08-01), AU164 (2023-12-04), AU307 (2024-02-05), AU2080 (2024-12-09) |

Older CPCB list versions and the 2019 NCAP report come from Internet Archive captures of the official URLs (`id_` = original bytes), because the file at the official URL has been replaced or the site is unreachable. The capture timestamp is recorded as the upstream id.

## Outputs (`python -m src.acquire.ncap_extract`, then `ncap_validate`)

| File | Content |
|---|---|
| `data/interim/ncap_city_lists.csv` | every list entry: document, page, item number, printed name |
| `data/interim/ncap_funding.csv` | long format: document, page, table, row, printed name, measure, raw cell text, parsed value, parse note |
| `data/interim/ncap_printed_totals.csv` | the "Total" figures printed in each table |
| `data/interim/ncap_cities.csv` | one row per city: membership of each list, first listing (date added) with the previous list as lower bound, channel (XV-FC if in any XV-FC table), million-plus-only flag |
| `docs/ncap_extraction_mismatches.md` | every failed check, for manual verification |

## Verified

- Every list's parsed count equals the count in its title or text (94, 102, 122, 124, 132, 131, 131, 130).
- Every Lok Sabha table's rows sum to its printed totals, apart from differences of ≤ 0.02 crore, listed as document-level rounding.
- Finance Commission UA rows sum exactly to the printed totals, and AU164's allocations equal Annex 5.3 + Annex 7.6 for every city.

## Known issues

- Names vary across documents; mapping is exact or by explicit alias (`config/ncap_city_aliases.yaml`), and combined rows (e.g. "Twin City Bhubaneshwar & Cuttack") cannot be split.
- Some utilisation figures are printed per state in merged cells (AU2467), or marked "*City wise UC not available" (AU5104). These are kept and flagged, not assigned to cities.
- Addition dates are interval-censored: between two list versions.
- Not extracted: official PM10 figures (AU386 annexure), per DEC-016.

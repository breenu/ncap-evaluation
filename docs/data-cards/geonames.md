# Data card: GeoNames gazetteer (India extract)

**Role:** town points, used only where GHSL has no urban centre. (1) The 10 NCAP towns with no GHSL centre, as buffered points, in a *sensitivity* analysis only; they are kept out of the primary satellite estimate (DEC-063). (2) Raniganj (West Bengal), joined to the Asansol unit (DEC-064). (3) Locating monitoring stations whose site name is a unique locality inside their city (DEC-066).

| | |
|---|---|
| Publisher | GeoNames (geonames.org) |
| What we download | `IN.zip` (every Indian feature, `geoname` table), `admin1CodesASCII.txt` (state codes → names), `readme.txt` (column definitions) from `download.geonames.org/export/dump/` |
| Licence | Creative Commons Attribution 4.0. Attribute "GeoNames (geonames.org)"; the data are provided "as is" without warranty (readme.txt) |
| Version | None published; the extract is regenerated daily. The manifest pins what was downloaded on 2026-09-26: ETag, Last-Modified (2026-09-26 01:53 GMT), size and sha256. A later re-download with different bytes is refused (DEC-042) |
| Size | 15.7 MB (IN.zip) |
| Fields used | name, asciiname, alternatenames, latitude, longitude, feature class (`P` = populated place), feature code, admin1 code (state), population |

## How it is used

- **Town lookup:** exact match (after the same normalisation as UCDB names) on name, ASCII name or an alternate name, restricted to populated places (`P`) in the city's state. If several match, the record with the largest population is used and the choice is recorded. Every lookup and its outcome is in `data/interim/geonames_towns.csv`.
- **No fuzzy matching.** A town that does not match exactly is reported, not guessed.

## Known issues

- Crowd-edited: points can be misplaced and populations stale. Every town point used is checked to lie in the right state, and is listed in `docs/ncap_ucdb_review.md` for review.
- Points mark a settlement's nominal centre, not its extent; the buffer rule (DEC-063) turns them into areas.

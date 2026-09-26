# Data card: GHSL Urban Centre Database R2024A and GHS-POP 2020 (JRC)

**Role:** city boundaries for zonal statistics and a reproducible control pool (RQ3 Layer A); population weights for the sensitivity check. DEC-006, DEC-038.

| File | Version | Use |
|---|---|---|
| `GHS_UCDB_GLOBE_R2024A_V1_2.zip` | UCDB R2024A V1-2 (2026-05-19) | urban-centre polygons and population by epoch |
| `GHS_POP_E2020_GLOBE_R2023A_4326_30ss_V1_0.zip` | GHS-POP R2023A, epoch 2020, 30″ | population-weighted zonal means (sensitivity only) |
| `GHS_UCDB_copyright.txt` | | licence text |

| | |
|---|---|
| Access | direct download from `jeodpp.jrc.ec.europa.eu/ftp/jrc-opendata/GHSL/` |
| Licence | CC BY 4.0, © European Union 1995–2026: credit and indicate changes |
| Upstream id | ETag, Last-Modified and size (no published checksum); sha256 in the manifest |

## Known issues

- Merged agglomerations (Delhi NCR, Kolkata) put several NCAP cities in one polygon, and small NCAP towns may have no urban centre (risk R2). The NCAP-city ↔ UCDB matching table is built in Phase 3.
- R2024A has V1-0, V1-1 and V1-2 on the server; only V1-2 is used.

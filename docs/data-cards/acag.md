# Data card: ACAG satellite-derived surface PM2.5 (WashU)

**Role:** Layer A of the causal design (RQ3), satellite trend for the composition check (RQ1). DEC-001 to DEC-003, DEC-034.

| Product | Role | Folder in `s3://satpmdata` |
|---|---|---|
| V5.GL.06 annual, 0.01°, Asia | primary | `V5GL06/GWRPM25/Annual/Asia/` |
| V5.GL.06 annual uncertainty | primary | `V5GL06/GWRPM25Uncertainty/Annual/Asia/` |
| V5.GL.06 monthly, 0.05°, Asia | seasonal | `V5GL06/GWRPM25c0p05/Monthly/Asia/` |
| V6.GL.03 annual, 0.01°, AS | version comparison | `V6GL03/CNNPM25/Annual/AS/` |
| V6.GL.03 monthly, 0.10°, AS | version comparison (seasonal) | `V6GL03/CNNPM25c0p10/Monthly/AS/` |
| V6.GL.02.04 annual, 0.01°, AS | vintage check (to 2023) | `V6GL0204/CNNPM25/Annual/AS/` |

| | |
|---|---|
| Access | anonymous HTTPS from the public AWS bucket |
| Years | 2005–2024 (`windows.satellite_download_years`); V6.GL.02.04 ends 2023 |
| Raw layout | `data/raw/acag/<bucket key>` (version and product in the path) |
| Integrity | files uploaded in one part are checked against their MD5 ETag (480 of 559); multipart uploads are checked by size; all sha256 in the manifest |
| References | van Donkelaar et al. 2021 (V5, GWR); Shen et al. 2024 (V6, CNN); V6.GL.02.04 update log in the bucket's `README.txt` |
| Licence | ACAG terms: cite the product papers |

## Verified (`docs/data-probe.md`)

- All three versions cover India at 0.01° (grids 10°S–45°N or 60°N, 65–145°E); 12 test points incl. extremes and major cities have values. V5.GL.06 masks water; V6 fills it.
- V6.GL.03 has no methods note (DEC-001), and its bucket date matches V5.GL.06's (2026-09-22), so the date says nothing about recency.

## Known issues

- Calibrated against ground monitors, so network growth can leak in (proposal threat 3): hence the version and vintage comparisons.
- Units differ between versions (`[\mug/m^3]` vs `ug/m3`); variable names differ (`GWRPM25` vs `PM25`).

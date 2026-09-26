# Data card: state and country boundaries (DataMeet)

**Role:** region assignment (`config/regions.yaml`: IGP, coastal, peninsular, north-east) and maps. DEC-018.

| | |
|---|---|
| Source | `github.com/datameet/maps`, pinned at commit `b3fbbde` (master head, 2022-05-11) |
| Files | `States/Admin2.{shp,shx,dbf,prj,cpg}`; `Country/india-composite.geojson` (Survey of India depiction); READMEs |
| Licence | data CC BY 4.0 (repository code MIT). Attribution: "India boundaries by DataMeet India community (CC BY 4.0)" |
| Raw layout | `data/raw/boundaries/datameet@b3fbbde/<path>` |

## Known issues

- Boundaries date from 2022 at the latest; state reorganisations after that are not reflected (none affect NCAP cities as far as checked).
- Chosen for Survey-of-India-consistent depiction for an Indian policy audience (DEC-018).

## Appendix B. Reproducibility {.unnumbered}

Every processed file, figure and number in this report is rebuilt from the raw downloads by one Snakemake workflow. The repository README gives the commands.

- **Raw data are immutable.** Each source's `data/raw/<source>/MANIFEST.csv` records the URL, upstream identifier, download date and SHA-256 checksum of every file. The raw files themselves are not in the repository; the downloaders fetch them again, and a file whose checksum differs is refused. Re-downloading needs free accounts for the Copernicus Climate Data Store, OpenAQ and NASA FIRMS, and a registered Google Earth Engine project for the aerosol optical depth tables.
- **Pinned environments.** The analysis environment (Python and R) and the separate report and site environment (Quarto only) are each locked with `conda-lock` for Windows and Linux. R packages not on conda-forge come from a dated CRAN snapshot or a pinned commit.
- **The pre-registration gate.** Every step that compares NCAP with non-NCAP units after 2018 checks `config/gate.yaml`, which names the registered plan's commit.
- **No typed numbers.** Every number in this report, the results summary and the policy brief is read from a file that `python -m src.report.values` writes from the pipeline's outputs, and a test fails if a result-like number appears in the text by hand. The same test runs a wording check that refuses any phrase that attributes a result to NCAP or ranks cities.
- **What is not byte-identical.** Figures rebuild byte for byte. Some tables and spatial files differ in byte order or embedded timestamps between runs but not in content. Earth Engine re-exports agree to about eight significant figures, so the aerosol tables are pinned by checksum.
- **A rebuild from a clean clone** of the public repository, with fresh environments and the raw data checked against every manifest, is recorded in `docs/DECISIONS.md` (Phase 10).

## Appendix C. Licences and attributions {.unnumbered}

- **Code** (the pipeline, tests and workflow): MIT licence.
- **Text and figures** (this report, the summary, the brief, the figures and the documentation): Creative Commons Attribution 4.0 (CC BY 4.0).
- **Ground-derived data** (any table derived from the CPCB station data): Open Database License 1.0 (ODbL), as the source's licence requires.

**Notice for figures and tables that use ground data.** Contains information from `india-cpcb-aqi`, a mirror of CPCB's data repository, which is made available under the ODbL 1.0; some contents © CPCB. The adapted station data behind these works, and the method that produced them, are available under the ODbL 1.0 in the public repository.

**Other sources** (full citations in the references):

- ACAG satellite PM2.5, Washington University in St. Louis (CC BY 4.0).
- Contains modified Copernicus Climate Change Service information (2026): ERA5 (CC BY 4.0).
- GHSL Urban Centre Database and GHS-POP, © European Union 1995–2026 (CC BY 4.0); I joined polygons into units and computed population-weighted means.
- India boundaries by the DataMeet India community (CC BY 4.0).
- GeoNames (CC BY 4.0); Natural Earth (public domain).
- NASA LANCE FIRMS and MODIS MAIAC (NASA LP DAAC), NASA open data.
- OpenAQ, and the original data providers.

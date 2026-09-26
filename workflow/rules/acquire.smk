# Stage 1: data acquisition (Phase 2). One rule per source in src/acquire/.
# Raw files land in data/raw/<source>/ with a MANIFEST.csv (src/common/manifest.py).
# Each downloader is idempotent and resumable, verifies its folder against the manifest,
# and then writes data/interim/_flags/acquire_<source>.done.
#
# Downloads never re-run on their own: the flags are the outputs, so Snakemake runs a
# downloader only when its flag is missing (e.g. a clean clone). Re-running one by hand is
# safe: recorded files are skipped and partial files resume.

FLAGS = "data/interim/_flags"
PY = "python -m"


rule acquire_acag:
    output: f"{FLAGS}/acquire_acag.done"
    shell: f"{PY} src.acquire.acag"


rule acquire_cpcb_mirror:
    output: f"{FLAGS}/acquire_cpcb_mirror.done"
    shell: f"{PY} src.acquire.cpcb_mirror"


rule acquire_openaq:
    output: f"{FLAGS}/acquire_openaq.done"
    shell: f"{PY} src.acquire.openaq"


rule acquire_ghsl:
    output: f"{FLAGS}/acquire_ghsl.done"
    shell: f"{PY} src.acquire.ghsl"


rule acquire_boundaries:
    output: f"{FLAGS}/acquire_boundaries.done"
    shell: f"{PY} src.acquire.boundaries"


rule acquire_firms:
    output: f"{FLAGS}/acquire_firms.done"
    shell: f"{PY} src.acquire.firms"


rule station_crosswalk:
    input:
        f"{FLAGS}/acquire_cpcb_mirror.done",
        f"{FLAGS}/acquire_openaq.done",
    output: "data/interim/station_crosswalk.csv"
    shell: f"{PY} src.acquire.stations"


rule acquire_era5:
    input: "data/interim/station_crosswalk.csv"
    output:
        f"{FLAGS}/acquire_era5_monthly.done",
        f"{FLAGS}/acquire_era5_timeseries.done",
    shell: f"{PY} src.acquire.era5"


rule acquire_ncap_docs:
    input: "config/ncap_sources.yaml"
    output: f"{FLAGS}/acquire_ncap_docs.done"
    shell: f"{PY} src.acquire.ncap_pdfs"


rule ncap_extract:
    input:
        f"{FLAGS}/acquire_ncap_docs.done",
        "config/ncap_sources.yaml",
        "src/acquire/ncap_extract.py",
    output:
        "data/interim/ncap_city_lists.csv",
        "data/interim/ncap_funding.csv",
        "data/interim/ncap_printed_totals.csv",
    shell: f"{PY} src.acquire.ncap_extract"


rule ncap_validate:
    input:
        "data/interim/ncap_city_lists.csv",
        "data/interim/ncap_funding.csv",
        "data/interim/ncap_printed_totals.csv",
        "config/ncap_city_aliases.yaml",
    output:
        "data/interim/ncap_cities.csv",
        "data/interim/ncap_funding_clean.csv",
        "docs/ncap_extraction_mismatches.md",
    shell: f"{PY} src.acquire.ncap_validate"


rule mirror_checks:
    input:
        f"{FLAGS}/acquire_cpcb_mirror.done",
        f"{FLAGS}/acquire_openaq.done",
        f"{FLAGS}/acquire_era5_timeseries.done",
        "data/interim/station_crosswalk.csv",
    output: "docs/mirror-checks.md"
    shell: f"{PY} src.acquire.mirror_checks"


rule acquire:
    input:
        f"{FLAGS}/acquire_acag.done",
        f"{FLAGS}/acquire_cpcb_mirror.done",
        f"{FLAGS}/acquire_openaq.done",
        f"{FLAGS}/acquire_ghsl.done",
        f"{FLAGS}/acquire_boundaries.done",
        f"{FLAGS}/acquire_era5_monthly.done",
        f"{FLAGS}/acquire_era5_timeseries.done",
        "data/interim/ncap_cities.csv",
        "docs/mirror-checks.md",
        # FIRMS (cut item #4) is built on request: snakemake data/interim/_flags/acquire_firms.done
    output:
        f"{STUB}/acquire.done",
    run:
        stub_done(output[0])

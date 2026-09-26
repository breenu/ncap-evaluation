# Stages 2-3: Parquet storage, cleaning and the station audit (Phase 3, RQ1).
#
# Part A (ingest, cross-check, station metadata, NCAP-UCDB matching) is real.
# Part B (flags, changepoints, reliability, missingness) replaces the `clean` stub after the checkpoint.

INT = "data/interim"


rule ingest_mirror:
    input:
        f"{FLAGS}/acquire_cpcb_mirror.done",
        "config/params.yaml",
        "src/clean/ingest.py",
    output:
        directory(f"{INT}/mirror_15min"),
        f"{INT}/ingest/mirror_summary.csv",
    shell: f"{PY} src.clean.ingest mirror"


rule ingest_openaq:
    input:
        f"{FLAGS}/acquire_openaq.done",
        "src/clean/ingest.py",
    output:
        directory(f"{INT}/openaq_obs"),
        f"{INT}/ingest/openaq_files.csv",
    shell: f"{PY} src.clean.ingest openaq"


rule ucdb_india:
    input:
        f"{FLAGS}/acquire_ghsl.done",
        f"{FLAGS}/acquire_boundaries.done",
        "src/clean/geo.py",
    output: f"{INT}/ghsl/ucdb_india.gpkg"
    shell: f"{PY} -c \"from src.clean.geo import build_ucdb_india; build_ucdb_india()\""


rule crosscheck:
    input:
        f"{INT}/mirror_15min",
        f"{INT}/openaq_obs",
        f"{INT}/station_crosswalk.csv",
        "src/clean/crosscheck.py",
    output:
        f"{INT}/crosscheck/pairs.csv",
        f"{INT}/crosscheck/monthly.csv",
        f"{INT}/crosscheck/anomalous_months.csv",
        "docs/mirror-openaq-crosscheck.md",
    shell: f"{PY} src.clean.crosscheck"


rule station_meta:
    input:
        f"{INT}/mirror_15min",
        f"{INT}/openaq_obs",
        f"{INT}/station_crosswalk.csv",
        f"{INT}/ghsl/ucdb_india.gpkg",
        "src/clean/station_meta.py",
    output:
        "data/processed/stations.csv",
        "docs/station_metadata_review.md",
    shell: f"{PY} src.clean.station_meta"


rule ncap_ucdb_match:
    input:
        "data/processed/stations.csv",
        f"{INT}/ghsl/ucdb_india.gpkg",
        f"{INT}/ncap_cities.csv",
        "config/ncap_ucdb_names.yaml",
        "src/clean/geo.py",
    output:
        f"{INT}/ncap_ucdb_match.csv",
        "docs/ncap_ucdb_review.md",
    shell: f"{PY} src.clean.geo"


rule clean:
    input:
        f"{STUB}/acquire.done",
        "docs/mirror-openaq-crosscheck.md",
        "docs/station_metadata_review.md",
        f"{INT}/ncap_ucdb_match.csv",
    output:
        f"{STUB}/clean.done",
    run:
        stub_done(output[0])

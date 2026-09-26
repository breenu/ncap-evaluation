# Stages 2-3: Parquet storage, cleaning and the station audit (Phase 3, RQ1).
#
# Part A: ingest, cross-check, station metadata, NCAP-UCDB matching.
# Part B: town points and satellite units, regions, station-hour/day with flags, satellite zonal
# statistics, spatial checks, changepoints, reliability, missingness, audit report.

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
    shell: f"{PY} src.clean.geo ucdb"


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
        f"{INT}/crosscheck/validation_level.csv",
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


rule towns_units:
    input:
        f"{INT}/ncap_ucdb_match.csv",
        f"{FLAGS}/acquire_geonames.done",
        "config/geonames_towns.yaml",
        "src/clean/towns.py",
    output:
        f"{INT}/geonames_towns.csv",
        f"{INT}/sat_units.gpkg",
    shell: f"{PY} src.clean.towns"


rule regions:
    input:
        f"{INT}/sat_units.gpkg",
        "data/processed/stations.csv",
        f"{FLAGS}/acquire_naturalearth.done",
        "config/regions.yaml",
        "src/clean/regions.py",
    output:
        f"{INT}/unit_regions.csv",
        f"{INT}/station_regions.csv",
    shell: f"{PY} src.clean.regions"


rule station_hour:
    input:
        f"{INT}/mirror_15min",
        f"{INT}/openaq_obs",
        "data/processed/stations.csv",
        "config/params.yaml",
        "src/clean/hourly.py",
        "src/clean/flags.py",
    output:
        directory("data/processed/station_hour"),
        "data/processed/station_day.parquet",
        f"{INT}/audit/flag_counts.csv",
        f"{INT}/audit/ceilings.csv",
    shell: f"{PY} src.clean.hourly"


rule zonal:
    input:
        f"{INT}/sat_units.gpkg",
        "data/processed/stations.csv",
        f"{FLAGS}/acquire_acag.done",
        "src/clean/zonal.py",
    output:
        "data/processed/unit_year_sat.parquet",
        "data/processed/unit_month_sat.parquet",
        "data/processed/station_year_sat.parquet",
    shell: f"{PY} src.clean.zonal"


rule spatial:
    input:
        "data/processed/station_day.parquet",
        "data/processed/station_year_sat.parquet",
        "src/clean/spatial.py",
    output:
        f"{INT}/audit/neighbour_ref.parquet",
        f"{INT}/audit/spatial_station_year.csv",
    shell: f"{PY} src.clean.spatial"


rule changepoints:
    input:
        f"{INT}/audit/neighbour_ref.parquet",
        "src/clean/changepoints.py",
    output:
        f"{INT}/audit/changepoints.csv",
        f"{INT}/audit/changepoint_calibration.csv",
    shell: f"{PY} src.clean.changepoints"


rule reliability:
    input:
        f"{INT}/audit/flag_counts.csv",
        f"{INT}/audit/spatial_station_year.csv",
        f"{INT}/audit/changepoints.csv",
        "src/clean/reliability.py",
    output:
        "data/processed/station_year_quality.parquet",
        f"{INT}/audit/valid_station_years.csv",
    shell: f"{PY} src.clean.reliability"


rule missingness:
    input:
        "data/processed/station_year_quality.parquet",
        f"{INT}/audit/neighbour_ref.parquet",
        "src/clean/missingness.py",
    output:
        f"{INT}/audit/missingness_models.csv",
        f"{INT}/audit/missingness_bias.csv",
    shell: f"{PY} src.clean.missingness"


rule clean:
    input:
        f"{STUB}/acquire.done",
        "docs/mirror-openaq-crosscheck.md",
        "docs/station_metadata_review.md",
        f"{INT}/ncap_ucdb_match.csv",
        f"{INT}/unit_regions.csv",
        "data/processed/unit_year_sat.parquet",
        f"{INT}/audit/missingness_models.csv",
    output:
        f"{STUB}/clean.done",
    run:
        stub_done(output[0])

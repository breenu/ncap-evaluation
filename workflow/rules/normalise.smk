# Stage 5: meteorological normalisation / deweathering (Phase 5, RQ2; DEC-100 to DEC-106).
# Fitted per station; never uses NCAP status and estimates no treatment effect, so it is part of
# `pregate` (DEC-025).
#
# The fit steps are long (pilot about an hour, full run several hours) and resumable per series:
# a stopped run is resumed by running the same target again (src/normalise/store.py).

NRM = "data/interim/normalise"
DW = "data/processed/deweathered"
FIG3 = ["fig3_deweathered", "fig3_deweathered_grange_carslaw", "fig3_deweathered_annual"]  # DEC-109, DEC-117
NRM_CODE = ["src/normalise/features.py", "src/normalise/resample.py", "src/normalise/lgbm.py",
            "src/normalise/gam.R", "src/normalise/run.py"]


rule era5_daily:
    input:
        f"{FLAGS}/acquire_era5_located.done",
        "src/normalise/era5_daily.py",
    output: f"{NRM}/era5_daily.parquet"
    shell: f"{PY} src.normalise.era5_daily"


rule normalise_pilot_select:
    input:
        "data/processed/station_day.parquet",
        "data/processed/stations.csv",
        f"{INT}/station_regions.csv",
    output: f"{NRM}/pilot_stations.csv"
    shell: f"{PY} src.normalise.pilot select"


rule normalise_pilot_prepare:
    input:
        f"{NRM}/pilot_stations.csv",
        f"{NRM}/era5_daily.parquet",
        "src/normalise/features.py",
    output: f"{NRM}/inputs/pilot/series.csv"
    run:
        import pandas as pd
        sids = ",".join(pd.read_csv(input[0]).sid)
        shell(f"{PY} src.normalise.run prepare --run pilot --sids {sids}")


rule normalise_pilot_fit:
    input: f"{NRM}/inputs/pilot/series.csv", NRM_CODE
    output: touch(f"{NRM}/fits/pilot/_all.done")
    shell:
        f"{PY} src.normalise.run fit --run pilot --family both && "
        f"{PY} src.normalise.run cvcheck --run pilot"


rule normalise_pilot_report:
    input:
        f"{NRM}/fits/pilot/_all.done",
        "src/normalise/pilot.py",
        "src/normalise/collect.py",
    output: "docs/deweathering_pilot.md"
    shell: f"{PY} src.normalise.pilot report"


# main: near-constant station-years left out of the fit (primary); registered: the series that have
# any, refitted with them kept (sensitivity) (DEC-110).
rule normalise_prepare:
    input:
        "data/processed/station_day.parquet",
        "data/processed/stations.csv",
        "data/processed/station_year_near_constant.parquet",
        f"{NRM}/era5_daily.parquet",
        "docs/deweathering_pilot.md",  # N comes from the pilot's convergence check (DEC-103, DEC-113)
        "src/normalise/features.py",
    output:
        f"{NRM}/inputs/main/series.csv",
        f"{NRM}/inputs/registered/series.csv",
    shell:
        f"{PY} src.normalise.run prepare --run main && "
        f"{PY} src.normalise.run prepare --run registered"


rule normalise_fit:
    input: f"{NRM}/inputs/main/series.csv", f"{NRM}/inputs/registered/series.csv", NRM_CODE
    output: touch(f"{NRM}/fits/main/_all.done")
    shell:  # lgbm + gam (one-year-knot trend, DEC-116), and gam_k4 (previous trend, sensitivity)
        f"{PY} src.normalise.run fit --run main --family both && "
        f"{PY} src.normalise.run fit --run main --family gam_k4 && "
        f"{PY} src.normalise.run fit --run registered --family both && "
        f"{PY} src.normalise.run fit --run registered --family gam_k4 && "
        f"{PY} src.normalise.run cvcheck --run main --family both && "
        f"{PY} src.normalise.run cvcheck --run main --family gam_k4 && "
        f"{PY} src.normalise.run cvcheck --run registered --family both && "
        f"{PY} src.normalise.run cvcheck --run registered --family gam_k4"


rule extrapolation_guard:
    input: f"{NRM}/fits/main/_all.done", "src/normalise/guard.py"
    output: f"{DW}/extrapolation.parquet"
    shell: f"{PY} src.normalise.guard"


# DEC-119: the pre-set lockdown smear test (GAM + lockdown indicator on the pilot stations, from the
# full-run inputs, vs the current GAM). Its result decided that the primary GAM stays as it is.
rule lockdown_test:
    input:
        f"{NRM}/fits/main/_all.done",
        f"{NRM}/pilot_stations.csv",
        "src/normalise/gam.R",
        "src/normalise/lockdown_test.py",
    output: f"{DW}/lockdown_test.json", f"{DW}/lockdown_test.csv"
    run:
        import pandas as pd
        sids = ",".join(pd.read_csv(input[1]).sid)
        shell(f"{PY} src.normalise.run fit --run main --family gam_lock --sids {sids}")
        shell(f"{PY} src.normalise.lockdown_test")


rule normalise_aggregate:
    input:
        f"{NRM}/fits/main/_all.done",
        "data/processed/station_year_quality.parquet",
        f"{INT}/station_regions.csv",
        "src/normalise/aggregate.py",
        "src/normalise/collect.py",
    output:
        f"{DW}/series_metrics.parquet",
        f"{DW}/family_choice.json",
        f"{DW}/station_day.parquet",
        f"{DW}/station_year.parquet",
        f"{DW}/station_month.parquet",
        f"{DW}/city_month.parquet",
        f"{DW}/city_year.parquet",
    shell: f"{PY} src.normalise.aggregate --run main"


# DEC-120: GAM vs LightGBM disagreement on the city-level 2018-2025 deweathered change (H4 quantity)
rule city_disagreement:
    input: f"{DW}/station_year.parquet", "src/normalise/city_disagreement.py"
    output: f"{DW}/city_disagreement.csv"
    shell: f"{PY} src.normalise.city_disagreement"


rule fig3:
    input:
        f"{DW}/city_month.parquet",
        f"{DW}/city_year.parquet",
        "src/viz/fig3_deweathered.py",
        "src/viz/style.py",
    output: expand("reports/figures/{f}.{ext}", f=FIG3, ext=["png", "svg"])
    shell:
        f"{PY} src.viz.fig3_deweathered --scheme seasonal && "
        f"{PY} src.viz.fig3_deweathered --scheme annual && "
        f"{PY} src.viz.fig3_deweathered --view annual"


rule deweathering_report:
    input:
        f"{DW}/series_metrics.parquet",
        f"{DW}/city_year.parquet",
        f"{DW}/extrapolation.parquet",
        f"{DW}/lockdown_test.json",
        f"{DW}/city_disagreement.csv",
        "docs/near_constant_check.md",
        "src/normalise/report.py",
    output: "docs/deweathering_report.md"
    shell: f"{PY} src.normalise.report"


rule normalise:
    input:
        f"{STUB}/clean.done",
        "docs/deweathering_report.md",
        expand("reports/figures/{f}.{ext}", f=FIG3, ext=["png", "svg"]),
    output:
        f"{STUB}/normalise.done",
    run:
        stub_done(output[0])

# Stage 6: network-composition correction (Phase 6, RQ1) and H4 (DEC-125 to DEC-131).
# All stations vs balanced panel vs satellite over GHSL urban-centre boundaries. H4 is the one place
# this stage uses NCAP status (a registered secondary, descriptive hypothesis over NCAP cities only);
# nothing here contrasts NCAP with non-NCAP units.

CMP = "data/processed/composition"
CMP_TABLES = [f"{CMP}/{f}" for f in ("city_changes.parquet", "summary.csv", "h4.csv", "city_boot.csv",
                                     "trends.parquet", "composition_by_year.csv", "ground_sat.csv",
                                     "ground_sat_summary.csv", "entrants.csv", "entrants_summary.csv",
                                     "coverage.csv", "station_year_fitted.parquet")]
FAMDIAG = [f"{CMP}/family_diag_{f}.csv" for f in ("cities", "contrib", "check", "era5", "attribution", "misfit_h4")]
FIG1 = ["fig1_decomposition", "fig1_decomposition_cities"]


rule composition_tables:
    input:
        f"{DW}/station_year.parquet",
        "data/processed/station_year.parquet",
        "data/processed/unit_year_sat.parquet",
        f"{INT}/pregate/units.csv",
        f"{INT}/station_regions.csv",
        f"{NRM}/fits/main/_all.done",  # fitted values for the unmodelled / modelled-weather split (DEC-136)
        "src/normalise/composition.py",
    output: CMP_TABLES
    shell: f"{PY} src.normalise.composition"


# GAM terms (R) and LightGBM SHAP on the saved Phase 5 models; about an hour on this laptop
rule family_diag:
    input:
        f"{CMP}/city_changes.parquet",
        f"{NRM}/fits/main/_all.done",
        "src/normalise/family_diag.py",
        "src/normalise/family_terms.R",
    output: FAMDIAG
    shell: f"{PY} src.normalise.family_diag"


rule fig1:
    input:
        f"{CMP}/city_changes.parquet",
        f"{CMP}/summary.csv",
        f"{CMP}/city_boot.csv",
        "src/viz/fig1_decomposition.py",
        "src/viz/style.py",
    output: expand("reports/figures/{f}.{ext}", f=FIG1, ext=["png", "svg"])
    shell: f"{PY} src.viz.fig1_decomposition"


rule composition_report:
    input:
        CMP_TABLES,
        FAMDIAG,
        f"{INT}/eda/entrants.csv",
        "src/normalise/composition_report.py",
    output: "docs/composition_report.md"
    shell: f"{PY} src.normalise.composition_report"


rule composition:
    input:
        f"{STUB}/normalise.done",
        "docs/composition_report.md",
        expand("reports/figures/{f}.{ext}", f=FIG1, ext=["png", "svg"]),
    output:
        f"{STUB}/composition.done",
    run:
        stub_done(output[0])

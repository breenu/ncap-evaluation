# Stage 4: exploratory analysis, station-entry map, data-quality heatmap (Phase 3), and the
# generated audit report. Blinding rule until the gate: nothing here compares NCAP vs non-NCAP units.

EDA_FIGS = ["fig2_station_entry", "fig8_quality_heatmap", "eda_seasonal_regions", "eda_city_trends",
            "eda_ground_vs_satellite", "eda_entrants"]


rule eda_figures:
    input:
        f"{STUB}/clean.done",
        "data/processed/station_year_quality.parquet",
        "data/processed/unit_month_sat.parquet",
        "src/viz/eda.py",
        "src/viz/style.py",
    output:
        "data/processed/station_year.parquet",
        expand("reports/figures/{f}.{ext}", f=EDA_FIGS, ext=["png", "svg"]),
    shell: f"{PY} src.viz.eda"


rule audit_report:
    input:
        "data/processed/station_year.parquet",
        f"{INT}/audit/missingness_models.csv",
        "src/clean/audit_report.py",
    output: "docs/audit_report.md"
    shell: f"{PY} src.clean.audit_report"


rule eda:
    input:
        "docs/audit_report.md",
    output:
        f"{STUB}/eda.done",
    run:
        stub_done(output[0])

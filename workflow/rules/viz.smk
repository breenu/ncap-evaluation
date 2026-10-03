# Stage 10: every report figure, its caption and alt text, and the figure catalogue (Phase 9; DEC-190 to DEC-195).
# Figure modules only read outputs already on disk; no figure is drawn by a data rule. Rules that read
# post-2018 NCAP comparisons check the gate inside their module (require_gate).

VIZ_CODE = ["src/viz/style.py", "src/viz/wording.py"]


def figs(*names):
    return [f"reports/figures/{n}.{ext}" for n in names for ext in ("png", "svg", "json")]


# ------------------------------------------------------------------ pre-gate figures (Phases 3 and 5)


rule fig2:
    input:
        f"{INT}/eda/station_first_year.csv",
        "data/processed/stations.csv",
        f"{INT}/sat_units.gpkg",
        "src/viz/fig2_station_entry.py",
        VIZ_CODE,
    output: figs("fig2_station_entry")
    shell: f"{PY} src.viz.fig2_station_entry"


rule fig8:
    input:
        "data/processed/station_year_quality.parquet",
        f"{INT}/station_regions.csv",
        f"{INT}/eda/station_first_year.csv",
        "src/viz/fig8_quality_heatmap.py",
        VIZ_CODE,
    output: figs("fig8_quality_heatmap")
    shell: f"{PY} src.viz.fig8_quality_heatmap"


rule eda_extra_figures:
    input:
        expand(f"{INT}/eda/{{f}}.csv", f=["seasonal_ground", "seasonal_satellite", "city_trends", "ground_vs_satellite",
                                            "entrants"]),
        "src/viz/eda_figures.py",
        VIZ_CODE,
    output: figs("eda_seasonal_regions", "eda_city_trends", "eda_ground_vs_satellite", "eda_entrants")
    shell: f"{PY} src.viz.eda_figures"


rule fig3:
    input:
        f"{DW}/city_month.parquet",
        f"{DW}/city_year.parquet",
        f"{DW}/station_year.parquet",
        "src/viz/fig3_deweathered.py",
        VIZ_CODE,
    output: figs("fig3_deweathered", "fig3_deweathered_grange_carslaw", "fig3_deweathered_annual")
    shell:
        f"{PY} src.viz.fig3_deweathered --scheme seasonal && "
        f"{PY} src.viz.fig3_deweathered --scheme annual && "
        f"{PY} src.viz.fig3_deweathered --view annual"


PREGATE_FIGS = ["fig2_station_entry", "fig8_quality_heatmap", "eda_seasonal_regions", "eda_city_trends",
                "eda_ground_vs_satellite", "eda_entrants", "fig3_deweathered", "fig3_deweathered_grange_carslaw",
                "fig3_deweathered_annual"]


rule viz_pregate:
    input: figs(*PREGATE_FIGS)
    output: f"{STUB}/viz_pregate.done"
    run:
        stub_done(output[0])


# ------------------------------------------------------------------ gated figures (Phases 6-8b)


rule fig1:
    input:
        f"{CMP}/city_changes.parquet",
        f"{CMP}/summary.csv",
        f"{CMP}/city_boot.csv",
        f"{CMP}/h4.csv",
        f"{CSL}/sdid_summary.csv",
        f"{CSL}/layer_b/estimates.csv",
        f"{HIER}/city_shrunken.csv",
        f"{INT}/unit_regions.csv",
        "src/viz/fig1_decomposition.py",
        VIZ_CODE,
    output: figs("fig1_decomposition", "figS3_decomposition_cities", "figS4_decomposition_pm10")
    shell: f"{PY} src.viz.fig1_decomposition"


rule fig4:
    input:
        rules.causal_summary.output,
        rules.causal_event_study.output,
        rules.causal_honest.output,
        rules.causal_cs.output,
        "src/viz/fig4_event_study.py",
        VIZ_CODE,
    output: figs("fig4_event_study")
    shell: f"{PY} src.viz.fig4_event_study"


rule fig5:
    input: f"{HIER}/city_shrunken.csv", f"{HIER}/pool_coefs.csv", "src/viz/fig5_city_map.py", VIZ_CODE
    output: figs("fig5_city_map")
    shell: f"{PY} src.viz.fig5_city_map"


rule fig6:
    input: f"{HIER}/city_shrunken.csv", f"{HIER}/pool_coefs.csv", "src/viz/fig6_shrinkage.py", VIZ_CODE
    output: figs("fig6_shrinkage")
    shell: f"{PY} src.viz.fig6_shrinkage"


rule fig7:
    input: rules.hier_mechanism.output, f"{CSL}/triangulation.csv", "src/viz/fig7_mechanism.py", VIZ_CODE
    output: figs("fig7_mechanism")
    shell: f"{PY} src.viz.fig7_mechanism"


rule figS1:
    input: f"{CSL}/levels.csv", "src/viz/figS1_levels.py", VIZ_CODE
    output: figs("figS1_levels")
    shell: f"{PY} src.viz.figS1_levels"


rule figS2:
    input: f"{MAIAC}/results.json", f"{MAIAC}/exploratory_notgained.json", "src/viz/figS2_aod_acag.py", VIZ_CODE
    output: figs("figS2_aod_acag")
    shell: f"{PY} src.viz.figS2_aod_acag"


ALL_FIGS = PREGATE_FIGS + ["fig1_decomposition", "figS3_decomposition_cities", "figS4_decomposition_pm10",
                           "fig4_event_study", "fig5_city_map", "fig6_shrinkage", "fig7_mechanism", "figS1_levels",
                           "figS2_aod_acag"]


rule figure_catalogue:
    input:
        figs(*ALL_FIGS),
        "src/viz/catalogue.py",
        VIZ_CODE,
    output: "docs/figures.md"
    shell: f"{PY} src.viz.catalogue"


rule viz:
    input:
        f"{STUB}/hierarchical.done",
        "docs/figures.md",
        "dashboard/index.qmd",
    output:
        f"{STUB}/viz.done",
    run:
        from src.common.gate import require_gate

        require_gate("viz: figures 1 and 4-7, S1-S4 (post-2018 NCAP comparisons)")
        stub_done(output[0])


# ------------------------------------------------------------------ the read-only dashboard (Part B; DEC-198 to DEC-201)


rule dashboard:
    input:
        f"{CMP}/trends.parquet",
        "data/processed/unit_year_sat.parquet",
        "data/processed/station_year_quality.parquet",
        f"{INT}/station_regions.csv",
        f"{INT}/sat_units.gpkg",
        f"{CSL}/design_units.csv",
        f"{CSL}/sdid_summary.csv",
        f"{HIER}/city_estimates.csv",
        f"{HIER}/city_shrunken.csv",
        f"{HIER}/pool_coefs.csv",
        "src/dashboard/build.py",
        VIZ_CODE,
    output:
        "dashboard/index.qmd",
        "dashboard/about.qmd",
        "dashboard/_quarto.yml",
        expand("dashboard/data/{f}.csv", f=["ground", "satellite", "city_estimates", "quality"]),
    shell: f"{PY} src.dashboard.build"


# Rendering needs the separate site environment (envs/site-lock.yml -> ncap-site), so it is not part of `all`;
# GitHub Actions renders and deploys the committed sources (.github/workflows/pages.yml).
rule dashboard_render:
    input: rules.dashboard.output
    output: "dashboard/_site/index.html"
    shell: "conda run -n ncap-site --no-capture-output quarto render dashboard"

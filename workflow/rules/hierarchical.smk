# Stage 8: heterogeneity and mechanism (Phase 8, RQ4). Rules DEC-162 to DEC-167, pushed before computing.
# GATED: every module calls require_gate() before reading post-2018 outcomes (hard rule 4, DEC-012).
# H1 is not identified (DEC-151): every per-unit number is a city-level relative change, not an NCAP effect.

HIER = "data/processed/hierarchical"


# ~40 min on 8 workers: 113 per-unit SDIDs + 923 single-unit placebos x 3 cohort years, two products
rule hier_unit_sdid:
    input:
        f"{CSL}/panel_annual.parquet",
        f"{CSL}/design_units.csv",
        "src/hierarchical/unit_sdid.R",
    output: expand(f"{HIER}/unit_sdid_{{s}}.parquet", s=["popw_V5GL06", "popw_V6GL03"])
    shell: f"{PY} src.hierarchical.city_estimates run"


rule hier_city_estimates:
    input:
        rules.hier_unit_sdid.output,
        f"{INT}/ncap_cities.csv",
        "src/hierarchical/city_estimates.py",
    output:
        f"{HIER}/city_estimates.csv",
        f"{HIER}/unit_sdid_summary.csv",
    shell: f"{PY} src.hierarchical.city_estimates table"


# PyMC, 5 models x ~2 min
rule hier_pooling:
    input:
        f"{HIER}/city_estimates.csv",
        "src/hierarchical/pooling.py",
    output:
        f"{HIER}/pool_coefs.csv",
        f"{HIER}/pool_diagnostics.csv",
        f"{HIER}/city_shrunken.csv",
        f"{HIER}/moderator_corr.csv",
        f"{HIER}/theta_draws_primary.npy",
        f"{HIER}/h5.json",
    shell: f"{PY} src.hierarchical.pooling"


rule hier_dose:
    input:
        f"{HIER}/city_estimates.csv",
        f"{INT}/ncap_funding_clean.csv",
        "src/hierarchical/dose.py",
    output:
        f"{HIER}/dose_ua.csv",
        f"{HIER}/dose_units.csv",
        f"{HIER}/dose_within_state.csv",
        f"{HIER}/dose_coefs.csv",
        f"{HIER}/dose_diagnostics.csv",
    shell: f"{PY} src.hierarchical.dose"


rule hier_mechanism:
    input:
        f"{CSL}/layer_b/estimates.csv",
        f"{CSL}/triangulation.csv",
        "src/hierarchical/mechanism.py",
    output:
        f"{HIER}/h3_betas.csv",
        f"{HIER}/h3_condition_ii.csv",
        f"{HIER}/h3_ratio.csv",
        f"{HIER}/h3.json",
    shell: f"{PY} src.hierarchical.mechanism"


rule heterogeneity_report:
    input:
        rules.hier_city_estimates.output,
        rules.hier_pooling.output,
        rules.hier_dose.output,
        rules.hier_mechanism.output,
        f"{CSL}/robustness.csv",
        f"{CSL}/sdid_summary.csv",
        "src/hierarchical/report.py",
    output: "docs/heterogeneity_report.md"
    shell: f"{PY} src.hierarchical.report"


rule hierarchical:
    input:
        f"{STUB}/causal.done",
        "docs/heterogeneity_report.md",
    output:
        f"{STUB}/hierarchical.done",
    run:
        from src.common.gate import require_gate

        require_gate("hierarchical: pooled city-level relative changes, dose-response, PM10 vs PM2.5")
        stub_done(output[0])

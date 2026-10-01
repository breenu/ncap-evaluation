"""Environment smoke tests: catch toolchain problems now, not in Phase 7.

These check that heavy dependencies import and that the R estimators actually run
(compiled code included) on the example datasets that ship with those packages.
No project data is used.
"""

import importlib
import shutil
import subprocess

import pytest

pytestmark = pytest.mark.env

PYTHON_MODULES = [
    "polars",
    "pandas",
    "pyarrow",
    "duckdb",
    "xarray",
    "netCDF4",
    "h5netcdf",
    "rioxarray",
    "geopandas",
    "shapely",
    "pyproj",
    "exactextract",
    "cdsapi",
    "pdfplumber",
    "ruptures",
    "lightgbm",
    "sklearn",
    "statsmodels",
    "pymc",
    "arviz",
    "pyfixest",
    "matplotlib",
    "streamlit",
    "snakemake",
]


@pytest.mark.parametrize("module", PYTHON_MODULES)
def test_python_module_imports(module):
    importlib.import_module(module)


def test_lightgbm_fits():
    import lightgbm as lgb
    import numpy as np

    rng = np.random.default_rng(0)
    X = rng.normal(size=(200, 3))
    y = X[:, 0] + rng.normal(scale=0.1, size=200)
    model = lgb.LGBMRegressor(n_estimators=20, verbose=-1).fit(X, y)
    assert model.predict(X).shape == (200,)


R_CHECK = r"""
suppressPackageStartupMessages({library(mgcv); library(did); library(synthdid)})
# mgcv: REML GAM on simulated data
set.seed(1); d <- gamSim(1, n = 200, verbose = FALSE)
stopifnot(inherits(gam(y ~ s(x0) + s(x1), data = d, method = "REML"), "gam"))
# did: Callaway & Sant'Anna on its bundled example (exercises DRDID / fastglm compiled code)
data(mpdta)
a <- att_gt(yname = "lemp", tname = "year", idname = "countyreal", gname = "first.treat",
            data = mpdta, bstrap = FALSE)
stopifnot(is.finite(aggte(a, type = "simple")$overall.att))
# synthdid: the California Prop 99 example from the SDID paper
data(california_prop99)
s <- panel.matrices(california_prop99)
est <- synthdid_estimate(s$Y, s$N0, s$T0)
stopifnot(is.finite(as.numeric(est)))
cat("R_OK\n")
"""


@pytest.mark.skipif(shutil.which("Rscript") is None, reason="Rscript not on PATH")
def test_r_estimators_run():
    out = subprocess.run(["Rscript", "-e", R_CHECK], capture_output=True, text=True, timeout=600)
    assert out.returncode == 0, out.stderr[-2000:]
    assert "R_OK" in out.stdout


R_HONEST = r"""
if (!requireNamespace("HonestDiD", quietly = TRUE)) { cat("R_SKIP\n"); quit(status = 0) }
suppressPackageStartupMessages(library(HonestDiD))
# HonestDiD's bundled Benzarti & Carloni event study: relative-magnitudes and smoothness bounds
data(BCdata_EventStudy)
b <- BCdata_EventStudy
npre <- length(b$prePeriodIndices); npost <- length(b$postPeriodIndices)
rm <- createSensitivityResults_relativeMagnitudes(b$betahat, b$sigma, npre, npost, Mbarvec = c(0, 1))
sm <- createSensitivityResults(b$betahat, b$sigma, npre, npost, Mvec = c(0, 0.01))
stopifnot(nrow(rm) == 2, all(is.finite(rm$lb)), nrow(sm) == 2, all(is.finite(sm$ub)))
cat("R_OK\n")
"""


@pytest.mark.skipif(shutil.which("Rscript") is None, reason="Rscript not on PATH")
def test_r_honestdid_runs():
    """HonestDiD (Phase 7, DEC-097/138). Skipped where it is not installed (Linux CI, DEC-138)."""
    out = subprocess.run(["Rscript", "-e", R_HONEST], capture_output=True, text=True, timeout=600)
    assert out.returncode == 0, out.stderr[-2000:]
    if "R_SKIP" in out.stdout:
        pytest.skip("HonestDiD not installed (NCAP_SKIP_HONESTDID=1)")
    assert "R_OK" in out.stdout

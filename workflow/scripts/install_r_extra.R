# Installs the R packages that conda-forge cannot provide, at exact versions (DEC-014, DEC-022).
# Run once after creating the conda env:  Rscript workflow/scripts/install_r_extra.R
# Their dependencies are already installed by environment.yml, so nothing else is pulled in.

# did / DRDID / fastglm: conda-forge's r-did requires an r-drdid version that does not exist there.
# mgcv: conda-forge's Windows build fails to load on some boots (MinGW "32 bit pseudo relocation out
# of range"); CRAN's build of the same version loads every time (DEC-093).
# Installed from a dated CRAN snapshot (Posit Package Manager), so versions are fixed by the date.
cran_snapshot <- "https://packagemanager.posit.co/cran/2026-09-25"
cran_pins <- c(mgcv = "1.9.4", fastglm = "0.1.2", DRDID = "1.3.0", did = "2.5.1")

# synthdid is not on CRAN; pinned to a GitHub commit (2024-01-15).
github_pins <- c(synthdid = "synth-inference/synthdid@70c1ce3eac58e28c30b67435ca377bb48baa9b8a")

type <- if (.Platform$OS.type == "windows") "binary" else "source"

# Windows only: CRAN's binaries of these packages, at the versions conda-forge has for Linux (DEC-138,
# DEC-156). conda-forge's MinGW builds can fail to load with "32 bit pseudo relocation out of range"
# whenever Windows places their DLL more than 2 GB from R.dll, and the layout can change within a boot.
# On 2026-10-01 Matrix failed on every load (taking did and mgcv with it); RcppArmadillo and RcppEigen
# did too; CRAN's builds of the same versions loaded every time. Since DEC-156 the win-64 lock no longer
# contains r-matrix, r-rcppeigen, r-bmisc or r-rcpparmadillo, so these are ordinary pins on Windows.
# In an environment built from the older lock they replace conda's files. Either way this runs before
# anything loads Matrix, and a stamp file (not loading the namespace) records that it is done.
win_cran_binaries <- c(Matrix = "1.7.6", RcppArmadillo = "15.6.0.1", RcppEigen = "0.3.4.0.2", BMisc = "1.4.10")
if (.Platform$OS.type == "windows") {
  for (pkg in names(win_cran_binaries)) {
    stamp <- file.path(.libPaths()[1], pkg, "NCAP_CRAN_BINARY")
    if (!file.exists(stamp) || readLines(stamp, warn = FALSE)[1] != win_cran_binaries[[pkg]]) {
      install.packages(pkg, lib = .libPaths()[1], repos = cran_snapshot, type = "binary",
                       dependencies = FALSE)
      got <- utils::packageDescription(pkg, lib.loc = .libPaths()[1])$Version
      if (package_version(got) != package_version(win_cran_binaries[[pkg]])) {
        stop(sprintf("%s: wanted %s, snapshot installed %s", pkg, win_cran_binaries[[pkg]], got))
      }
      writeLines(win_cran_binaries[[pkg]], stamp)
    }
  }
}

for (pkg in names(cran_pins)) {
  have <- requireNamespace(pkg, quietly = TRUE) &&
    as.character(packageVersion(pkg)) == cran_pins[[pkg]]
  if (!have) {
    install.packages(pkg, repos = cran_snapshot, type = type, dependencies = FALSE)
  }
  got <- as.character(packageVersion(pkg))
  if (got != cran_pins[[pkg]]) {
    stop(sprintf("%s: wanted %s, snapshot installed %s", pkg, cran_pins[[pkg]], got))
  }
}

for (pkg in names(github_pins)) {
  sha <- sub(".*@", "", github_pins[[pkg]])
  have <- requireNamespace(pkg, quietly = TRUE) &&
    identical(packageDescription(pkg)$RemoteSha, sha)
  if (!have) {
    remotes::install_github(github_pins[[pkg]], upgrade = "never", dependencies = FALSE)
  }
}

# HonestDiD (Rambachan & Roth 2023), Phase 7 event-study sensitivity (DEC-097, DEC-138). Unlike the
# packages above, its dependencies (CVXR, Rglpk, lpSolveAPI, TruncatedNormal, ...; 24 in all) are not
# in environment.yml, so they are installed with it from the same dated snapshot. On Linux they would
# build from source against system libraries (GLPK, GMP), so CI skips it (NCAP_SKIP_HONESTDID=1) and
# its test skips when the package is absent.
honest_pins <- c(HonestDiD = "0.2.8")
if (Sys.getenv("NCAP_SKIP_HONESTDID") != "1") {
  for (pkg in names(honest_pins)) {
    have <- requireNamespace(pkg, quietly = TRUE) &&
      as.character(packageVersion(pkg)) == honest_pins[[pkg]]
    if (!have) {
      install.packages(pkg, repos = cran_snapshot, type = type,
                       dependencies = c("Depends", "Imports", "LinkingTo"))
    }
    got <- as.character(packageVersion(pkg))
    if (got != honest_pins[[pkg]]) {
      stop(sprintf("%s: wanted %s, snapshot installed %s", pkg, honest_pins[[pkg]], got))
    }
  }
} else {
  honest_pins <- character(0)
}

for (pkg in c(names(cran_pins), names(github_pins), names(honest_pins))) {
  suppressPackageStartupMessages(library(pkg, character.only = TRUE))
  cat(sprintf("%-9s %s\n", pkg, as.character(packageVersion(pkg))))
}

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

for (pkg in c(names(cran_pins), names(github_pins))) {
  suppressPackageStartupMessages(library(pkg, character.only = TRUE))
  cat(sprintf("%-9s %s\n", pkg, as.character(packageVersion(pkg))))
}

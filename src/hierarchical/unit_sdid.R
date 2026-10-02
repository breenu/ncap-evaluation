# Per-unit SDID and single-unit placebo fits for the hierarchical model (Phase 8; DEC-162).
#
#   Rscript src/hierarchical/unit_sdid.R <series> [<series> ...]     e.g. popw_V5GL06 popw_V6GL03
#
# Inputs (written by Phase 7): <CAUSAL>/panel_annual.parquet (unit_id, year, series, value) and
# <CAUSAL>/design_units.csv (unit_id, role_a, cohort_listed). For one series:
#   real     every treated unit alone, with its listing cohort, against all controls;
#   placebo  every control in turn as the single fake treated unit, for each cohort year present among
#            the treated units, against the other controls (no random draws).
# Outcome log(value), years 2010-2024 without the dropped years (config causal.years_drop), exactly as
# the primary SDID (DEC-139). Each fit also returns the SD over pre-years of (unit - omega' donors):
# how closely the synthetic comparison tracked the unit before adoption (the pre-fit SD, DEC-162).
# Output: <OUT>/unit_sdid_<series>.parquet. A series whose output exists is skipped; fits are saved in
# chunks under <OUT>/parts_<series>/ as they finish, so a stopped run resumes (deleted when complete).
# BLAS must be single-threaded (the Snakemake rule and city_estimates.run set it).

suppressPackageStartupMessages({
  library(synthdid)
  library(arrow)
  library(yaml)
  library(parallel)
})

P <- yaml::read_yaml("config/params.yaml")
CAUSAL <- Sys.getenv("NCAP_CAUSAL_DIR", "data/processed/causal")   # tests point these at synthetic data
OUT <- Sys.getenv("NCAP_HIER_DIR", "data/processed/hierarchical")
CHUNK <- 200L  # fits per saved chunk
dir.create(OUT, recursive = TRUE, showWarnings = FALSE)

u <- read.csv(file.path(CAUSAL, "design_units.csv"), stringsAsFactors = FALSE)
treated <- u[u$role_a == "treated", c("unit_id", "cohort_listed")]
controls <- sort(u$unit_id[u$role_a == "control"])
y0 <- P$windows$satellite_analysis_years[[1]]; y1 <- P$windows$satellite_analysis_years[[2]]
drop <- as.integer(unlist(P$causal$years_drop))

matrix_for <- function(series) {
  pan <- as.data.frame(read_parquet(file.path(CAUSAL, "panel_annual.parquet")))
  ids <- c(controls, treated$unit_id)
  d <- pan[pan$series == series & pan$year >= y0 & pan$year <= y1 & !(pan$year %in% drop) & pan$unit_id %in% ids, ]
  if (anyDuplicated(d[, c("unit_id", "year")])) stop(series, ": duplicate unit-years")
  m <- tapply(d$value, list(d$unit_id, d$year), mean)[ids, , drop = FALSE]
  storage.mode(m) <- "double"
  if (anyNA(m) || any(m <= 0)) stop(series, ": unbalanced, missing or non-positive panel")
  log(m)
}

# One single-unit SDID fit: the unit's estimate and its pre-fit SD.
fit_unit <- function(job) {
  yrs <- as.integer(colnames(Y))
  T0 <- sum(yrs < job$cohort)
  donors <- setdiff(CONTROLS, job$unit)
  nwarn <- 0L
  est <- withCallingHandlers(
    synthdid_estimate(Y[c(donors, job$unit), , drop = FALSE], N0 = length(donors), T0 = T0),
    warning = function(w) { nwarn <<- nwarn + 1L; invokeRestart("muffleWarning") })
  omega <- attr(est, "weights")$omega
  gap <- Y[job$unit, seq_len(T0)] - colSums(omega * Y[donors, seq_len(T0), drop = FALSE])
  data.frame(kind = job$kind, unit_id = job$unit, cohort = job$cohort, T0 = T0, att = as.numeric(est),
             prefit_sd = sd(gap), warnings = nwarn)
}

args <- commandArgs(trailingOnly = TRUE)
if (!length(args)) stop("usage: Rscript src/hierarchical/unit_sdid.R <series> ...")
cl <- makeCluster(as.integer(Sys.getenv("NCAP_WORKERS", P$causal$workers)))
invisible(clusterEvalQ(cl, suppressPackageStartupMessages(library(synthdid))))
for (series in args) {
  f <- file.path(OUT, sprintf("unit_sdid_%s.parquet", series))
  if (file.exists(f)) { cat(series, ": exists, skipped\n"); next }
  t0 <- Sys.time()
  Y <- matrix_for(series)
  assign("Y", Y, envir = .GlobalEnv); assign("CONTROLS", controls, envir = .GlobalEnv)
  clusterExport(cl, c("Y", "CONTROLS"))
  cohorts <- sort(unique(treated$cohort_listed))
  jobs <- c(lapply(seq_len(nrow(treated)), function(i)
              list(kind = "real", unit = treated$unit_id[i], cohort = treated$cohort_listed[i])),
            unlist(lapply(cohorts, function(g) lapply(controls, function(j)
              list(kind = "placebo", unit = j, cohort = g))), recursive = FALSE))
  # chunks of jobs written as they finish, so a stopped run resumes where it left off
  part_dir <- file.path(OUT, sprintf("parts_%s", series))
  dir.create(part_dir, showWarnings = FALSE)
  starts <- seq(1L, length(jobs), by = CHUNK)
  for (s in starts) {
    pf <- file.path(part_dir, sprintf("jobs_%05d.parquet", s))
    if (file.exists(pf)) next
    e <- min(s + CHUNK - 1L, length(jobs))
    write_parquet(do.call(rbind, parLapply(cl, jobs[s:e], fit_unit)), pf)
    cat(sprintf("%s: %d of %d fits (%.1f min)\n", series, e, length(jobs),
                as.numeric(difftime(Sys.time(), t0, units = "mins"))))
  }
  res <- do.call(rbind, lapply(file.path(part_dir, sprintf("jobs_%05d.parquet", starts)),
                               function(p) as.data.frame(read_parquet(p))))
  if (nrow(res) != length(jobs)) stop(series, ": ", nrow(res), " fits, expected ", length(jobs))
  res$series <- series
  write_parquet(res, f)
  unlink(part_dir, recursive = TRUE)
  cat(sprintf("%s: %d fits in %.1f min\n", series, nrow(res), as.numeric(difftime(Sys.time(), t0, units = "mins"))))
}
stopCluster(cl)

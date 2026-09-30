# GAM term contributions for the family-disagreement diagnostic (Phase 6, DEC-130).
#
# For each task (pollutant, sid), loads the station's saved primary GAM (data/processed/models/gam/,
# one-year-knot trend, DEC-116) and writes the additive parts of its log prediction
# (predict(type = "terms"), one column per term, plus the intercept):
#   <out>/<pollutant>_<sid>_fit.parquet    every fit day (actual weather; row order of fit.parquet)
#   <out>/<pollutant>_<sid>_pool.parquet   every weather-pool day (ERA5 at the cell, 2015-2025), with
#                                          the pool day's own day of year and weekday; the trend is
#                                          fixed at the fit median (its term is not used from here)
# A resampled row's weather terms are the pool day's, because the GAM is additive: the diagnostic
# (src/normalise/family_diag.py) averages them over each day's draws in Python.
#
#   Rscript src/normalise/family_terms.R <tasks.csv> <out dir>

suppressPackageStartupMessages({
  library(mgcv)
  library(arrow)
})

args <- commandArgs(trailingOnly = TRUE)
tasks <- read.csv(args[1], stringsAsFactors = FALSE)
out_dir <- args[2]
dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)
INPUTS <- "data/interim/normalise/inputs/main"
MODELS <- "data/processed/models/gam"

prep <- function(x) {
  x$precip_l <- log1p(x$precip)
  x$weekday <- factor(x$weekday, levels = 0:6)
  x
}

terms_frame <- function(m, x) {
  p <- predict(m, prep(x), type = "terms", block.size = 50000L)
  d <- as.data.frame(unclass(p))
  d$intercept <- attr(p, "constant")
  d
}

for (i in seq_len(nrow(tasks))) {
  pol <- tasks$pollutant[i]
  sid <- tasks$sid[i]
  m <- readRDS(file.path(MODELS, pol, paste0(sid, ".rds")))
  d <- file.path(INPUTS, pol, sid)
  fit <- as.data.frame(read_parquet(file.path(d, "fit.parquet")))
  pool <- as.data.frame(read_parquet(file.path(d, "pool.parquet")))
  pool$trend <- median(fit$trend)
  write_parquet(terms_frame(m, fit), file.path(out_dir, sprintf("%s_%s_fit.parquet", pol, sid)))
  write_parquet(terms_frame(m, pool), file.path(out_dir, sprintf("%s_%s_pool.parquet", pol, sid)))
  cat(pol, sid, "\n")
}

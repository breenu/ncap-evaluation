# GAM deweathering model (mgcv), one station x pollutant per task (Phase 5, DEC-101).
#
# The same steps as src/normalise/lgbm.py, from the same input folder (src/normalise/features.py):
# blocked forward-chaining CV over the years in folds.parquet (test-year trend by the configured
# convention, DEC-107), a final fit on all fit days, and weather resampling from the same idx_<scheme>.parquet, so
# both families use identical weather draws. Output rows are in target order; metrics and smearing
# are computed later in Python (src/normalise/collect.py) by the same code for both families.
#
# Model (log PM, Gaussian, fREML, discretised covariates for speed):
#   y ~ s(trend, k) + s(doy, cyclic) + weekday + s(temp) + s(rh) + s(ws) + s(wd, cyclic)
#       + ti(ws, wd) + s(blh_mean) + s(blh_pm) + s(log1p(precip)) + s(ssrd)
#   k of the trend = trend_k_per_year x years of record, within [trend_k_min, trend_k_max].
#
#   Rscript src/normalise/gam.R <tasks.csv> <schemes, comma-separated> <checkpoints, comma-separated>
#   Rscript src/normalise/gam.R <tasks.csv> cvonly <convention>     (CV predictions only; pilot)
# tasks.csv has columns run, pollutant, sid. Done tasks (their .json exists) are skipped, and each
# output is written to a temporary name and renamed, so the run can be killed and resumed.

suppressPackageStartupMessages({
  library(mgcv)
  library(arrow)
  library(yaml)
})

args <- commandArgs(trailingOnly = TRUE)
tasks <- read.csv(args[1], stringsAsFactors = FALSE)
cfg <- read_yaml("config/params.yaml")$deweathering
cv_only <- args[2] == "cvonly"
if (cv_only) {
  convention <- args[3]
} else {
  schemes <- strsplit(args[2], ",")[[1]]
  checkpoints <- as.integer(strsplit(args[3], ",")[[1]])
  convention <- cfg$cv_trend
}

FEATURES <- c("temp", "rh", "ws", "wd", "blh_mean", "blh_pm", "precip", "ssrd")
CHUNK <- 50L
FAMILY <- "gam"
INPUTS <- "data/interim/normalise/inputs"
FITS <- "data/interim/normalise/fits"
MODELS <- "data/processed/models"

prep <- function(x) {
  x$precip_l <- log1p(x$precip)
  x$weekday <- factor(x$weekday, levels = 0:6)
  x
}

trend_k <- function(trend) {
  k <- round(cfg$gam$trend_k_per_year * diff(range(trend)))
  k <- min(cfg$gam$trend_k_max, max(cfg$gam$trend_k_min, k))
  as.integer(min(k, length(unique(trend)) - 1))
}

fit_gam <- function(d) {
  f <- as.formula(sprintf(paste(
    "y ~ s(trend, k = %d) + s(doy, bs = 'cc', k = 12) + weekday + s(temp) + s(rh) + s(ws)",
    "+ s(wd, bs = 'cc', k = 8) + ti(ws, wd, bs = c('tp', 'cc'), k = c(5, 6))",
    "+ s(blh_mean) + s(blh_pm) + s(precip_l) + s(ssrd)"
  ), trend_k(d$trend)))
  bam(f, data = prep(d), method = "fREML", discrete = TRUE, nthreads = 1,
      knots = list(doy = c(0.5, 366.5), wd = c(0, 360)))
}

predict_log <- function(m, x) as.numeric(predict(m, prep(x), block.size = 50000L))

# The trend a model sees for an unseen test year (DEC-107): last_year = the same calendar day one
# year earlier, kept inside the training range; clamp = the last training day's value.
test_trend <- function(trend, train_trend, convention) {
  if (convention == "last_year") return(pmin(pmax(trend - 1, min(train_trend)), max(train_trend)))
  if (convention == "clamp") return(pmin(trend, max(train_trend)))
  stop("unknown cv_trend ", convention)
}

cv_predict <- function(fit, folds, convention) {
  cv_pred <- rep(NA_real_, nrow(fit))
  cv_fold <- integer(nrow(fit))
  for (y in folds) {
    tr <- fit$year < y
    te <- fit$year == y
    m <- fit_gam(fit[tr, ])
    x <- fit[te, ]
    x$trend <- test_trend(x$trend, fit$trend[tr], convention)
    cv_pred[te] <- predict_log(m, x)
    cv_fold[te] <- y
  }
  list(pred = cv_pred, fold = cv_fold)
}

normalise <- function(m, target, pool, idx, scheme, checkpoints) {
  n <- max(checkpoints)
  nt <- nrow(target)
  s1 <- numeric(nt)
  s2 <- numeric(nt)
  out <- list()
  for (k0 in seq(0L, n - 1L, by = CHUNK)) {
    sub <- idx[, (k0 + 1L):(k0 + CHUNK), drop = FALSE]
    flat <- as.vector(t(sub)) + 1L # target-major; idx holds 0-based pool rows
    x <- pool[flat, FEATURES]
    if (scheme == "seasonal") {
      x$doy <- rep(target$doy, each = CHUNK)
      x$weekday <- rep(target$weekday, each = CHUNK)
    } else if (scheme == "annual") {
      x$doy <- pool$doy[flat]
      x$weekday <- pool$weekday[flat]
    } else {
      stop("unknown scheme ", scheme)
    }
    x$trend <- rep(target$trend, each = CHUNK)
    p <- matrix(exp(predict_log(m, x)), nrow = nt, byrow = TRUE)
    s1 <- s1 + rowSums(p)
    s2 <- s2 + rowSums(p^2)
    k <- k0 + CHUNK
    if (k %in% checkpoints) out[[sprintf("dw_%s_n%d", scheme, k)]] <- s1 / k
  }
  out[[sprintf("sd_%s", scheme)]] <- sqrt(pmax(s2 / n - (s1 / n)^2, 0) * n / (n - 1))
  as.data.frame(out)
}

write_atomic <- function(df, path) {
  dir.create(dirname(path), recursive = TRUE, showWarnings = FALSE)
  tmp <- paste0(path, ".tmp")
  write_parquet(df, tmp)
  file.rename(tmp, path)
}

run_task <- function(run, pollutant, sid) {
  d <- file.path(INPUTS, run, pollutant, sid)
  fit <- as.data.frame(read_parquet(file.path(d, "fit.parquet")))
  target <- as.data.frame(read_parquet(file.path(d, "target.parquet")))
  pool <- as.data.frame(read_parquet(file.path(d, "pool.parquet")))
  folds <- as.integer(read_parquet(file.path(d, "folds.parquet"))$year)

  t0 <- proc.time()[["elapsed"]]
  cv <- cv_predict(fit, folds, convention)
  cv_pred <- cv$pred
  cv_fold <- cv$fold
  t1 <- proc.time()[["elapsed"]]
  m <- fit_gam(fit)
  fitted <- predict_log(m, fit)
  t2 <- proc.time()[["elapsed"]]
  tgt <- target
  tgt$trend <- pmin(pmax(tgt$trend, min(fit$trend)), max(fit$trend))
  dws <- lapply(schemes, function(s) {
    idx <- read_parquet(file.path(d, sprintf("idx_%s.parquet", s)))$idx
    idx <- matrix(as.integer(idx), nrow = nrow(target), byrow = TRUE)
    normalise(m, tgt, pool, idx, s, checkpoints)
  })
  t3 <- proc.time()[["elapsed"]]

  out <- do.call(cbind, dws)
  rows <- fit$t_row + 1L
  out$y <- NA_real_
  out$fitted <- NA_real_
  out$cv_pred <- NA_real_
  out$cv_fold <- 0L
  out$y[rows] <- fit$y
  out$fitted[rows] <- fitted
  out$cv_pred[rows] <- cv_pred
  out$cv_fold[rows] <- cv_fold

  base <- file.path(FITS, run, FAMILY, pollutant, sid)
  write_atomic(out, paste0(base, ".parquet"))
  if (run == "main") {
    mp <- file.path(MODELS, FAMILY, pollutant, paste0(sid, ".rds"))
    dir.create(dirname(mp), recursive = TRUE, showWarnings = FALSE)
    saveRDS(m, mp, compress = "xz")
  }
  js <- sprintf(paste0(
    '{"sid": "%s", "pollutant": "%s", "family": "%s", "n_fit": %d, "n_target": %d, ',
    '"folds": [%s], "draws": %d, "schemes": [%s], "trend_k": %d, "edf": %.3f, ',
    '"secs_cv": %.3f, "secs_fit": %.3f, "secs_normalise": %.3f, "secs_total": %.3f}'),
    sid, pollutant, FAMILY, nrow(fit), nrow(target), paste(folds, collapse = ", "),
    max(checkpoints), paste0('"', schemes, '"', collapse = ", "), trend_k(fit$trend),
    sum(m$edf), t1 - t0, t2 - t1, t3 - t2, t3 - t0)
  tmp <- paste0(base, ".json.tmp")
  writeLines(js, tmp)
  file.rename(tmp, paste0(base, ".json"))
}

run_cv_only <- function(run, pollutant, sid) {
  d <- file.path(INPUTS, run, pollutant, sid)
  fit <- as.data.frame(read_parquet(file.path(d, "fit.parquet")))
  n <- nrow(read_parquet(file.path(d, "target.parquet"), col_select = "date"))
  folds <- as.integer(read_parquet(file.path(d, "folds.parquet"))$year)
  cv <- cv_predict(fit, folds, convention)
  out <- data.frame(cv_pred = rep(NA_real_, n), cv_fold = rep(0L, n))
  out$cv_pred[fit$t_row + 1L] <- cv$pred
  out$cv_fold[fit$t_row + 1L] <- cv$fold
  write_atomic(out, file.path(FITS, run, "cvcheck", paste0(FAMILY, "_", convention), pollutant,
                              paste0(sid, ".parquet")))
}

for (i in seq_len(nrow(tasks))) {
  r <- tasks[i, ]
  if (cv_only) {
    run_cv_only(r$run, r$pollutant, r$sid)
    next
  }
  if (file.exists(file.path(FITS, r$run, FAMILY, r$pollutant, paste0(r$sid, ".json")))) next
  res <- tryCatch(run_task(r$run, r$pollutant, r$sid), error = function(e) e)
  if (inherits(res, "error")) {
    message(sprintf("FAILED %s %s: %s", r$pollutant, r$sid, conditionMessage(res)))
  } else {
    message(sprintf("done %s %s", r$pollutant, r$sid))
  }
}

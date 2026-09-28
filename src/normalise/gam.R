# GAM deweathering model (mgcv), one station x pollutant per task (Phase 5, DEC-101).
#
# The same steps as src/normalise/lgbm.py, from the same input folder (src/normalise/features.py):
# blocked forward-chaining CV over the years in folds.parquet (test-year trend by the configured
# convention, DEC-107), a final fit on all fit days, and weather resampling from the same idx_<scheme>.parquet, so
# both families use identical weather draws. Output rows are in target order; metrics and smearing
# are computed later in Python (src/normalise/collect.py) by the same code for both families.
#
# Model (log PM, Gaussian, fREML, discretised covariates for speed):
#   y ~ trend term + s(doy, cyclic) + weekday + s(temp) + s(rh) + s(ws) + s(wd, cyclic)
#       + ti(ws, wd) + s(blh_mean) + s(blh_pm) + s(log1p(precip)) + s(ssrd)
# Trend term, by rule (computed on the data each model is fitted on, CV training sets included):
#   annual_knots (DEC-116, family `gam`): cubic regression spline with floor(span) + 1 knots evenly
#       spaced over the span in years, i.e. >= 1 year apart, so it cannot follow seasons or
#       episodes; a straight line if that gives < 3 knots (span < 2 years).
#   k_per_year (DEC-101, family `gam_k4` and the pilot): thin-plate smooth with 4 basis functions per
#       year of record, within [trend_k_min, trend_k_max].
#   gam_lock (DEC-119, the pre-set lockdown smear test): annual_knots plus a parametric 0/1 term
#       `lockdown` for the national lockdown days, when the fitted data hold >= lockdown_min_days of them.
#       The indicator is a calendar variable: each day keeps its own value in CV and in resampling.
# The family (output folder) comes from the environment variable NCAP_GAM_FAMILY (default `gam`).
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
FAMILY <- Sys.getenv("NCAP_GAM_FAMILY", "gam")
if (!FAMILY %in% c("gam", "gam_k4", "gam_lock")) stop("unknown GAM family ", FAMILY)
USE_LOCK <- FAMILY == "gam_lock"

# Lockdown indicator from the trend (years since 2015-01-01, exact day / 365.25), always computed on a
# day's own date, before any CV shift or clamping of the trend.
lock_days <- as.numeric(as.Date(cfg$lockdown) - as.Date("2015-01-01"))
lock_flag <- function(trend) {
  day <- round(trend * 365.25)
  as.integer(day >= lock_days[1] & day <= lock_days[2])
}

trend_rule_for <- function(run) {
  if (FAMILY == "gam_k4") return("k_per_year")  # gam and gam_lock: annual_knots
  if (run == "pilot") return(cfg$pilot$gam_trend_rule)
  cfg$gam$trend_rule
}
INPUTS <- "data/interim/normalise/inputs"
FITS <- "data/interim/normalise/fits"
MODELS <- "data/processed/models"

prep <- function(x) {
  x$precip_l <- log1p(x$precip)
  x$weekday <- factor(x$weekday, levels = 0:6)
  x
}

trend_k <- function(trend, rule) {
  if (rule == "annual_knots") return(as.integer(floor(diff(range(trend))) + 1))
  if (rule != "k_per_year") stop("unknown trend rule ", rule)
  k <- round(cfg$gam$trend_k_per_year * diff(range(trend)))
  k <- min(cfg$gam$trend_k_max, max(cfg$gam$trend_k_min, k))
  as.integer(min(k, length(unique(trend)) - 1))
}

# The trend term of the formula, and its knots (NULL for thin-plate or linear).
trend_term <- function(trend, rule) {
  k <- trend_k(trend, rule)
  if (rule == "k_per_year") return(list(term = sprintf("s(trend, k = %d)", k), knots = NULL))
  if (k < 3) return(list(term = "trend", knots = NULL))
  list(term = sprintf("s(trend, bs = 'cr', k = %d)", k),
       knots = seq(min(trend), max(trend), length.out = k))
}

fit_gam <- function(d, rule) {
  tt <- trend_term(d$trend, rule)
  lock <- if (USE_LOCK && sum(d$lockdown) >= cfg$lockdown_min_days) "+ lockdown" else ""
  f <- as.formula(paste(
    "y ~", tt$term, lock, "+ s(doy, bs = 'cc', k = 12) + weekday + s(temp) + s(rh) + s(ws)",
    "+ s(wd, bs = 'cc', k = 8) + ti(ws, wd, bs = c('tp', 'cc'), k = c(5, 6))",
    "+ s(blh_mean) + s(blh_pm) + s(precip_l) + s(ssrd)"
  ))
  knots <- list(doy = c(0.5, 366.5), wd = c(0, 360))
  if (!is.null(tt$knots)) knots$trend <- tt$knots
  bam(f, data = prep(d), method = "fREML", discrete = TRUE, nthreads = 1, knots = knots)
}

predict_log <- function(m, x) as.numeric(predict(m, prep(x), block.size = 50000L))

# The trend a model sees for an unseen test year (DEC-107): last_year = the same calendar day one
# year earlier, kept inside the training range; clamp = the last training day's value.
test_trend <- function(trend, train_trend, convention) {
  if (convention == "last_year") return(pmin(pmax(trend - 1, min(train_trend)), max(train_trend)))
  if (convention == "clamp") return(pmin(trend, max(train_trend)))
  stop("unknown cv_trend ", convention)
}

cv_predict <- function(fit, folds, convention, rule) {
  cv_pred <- rep(NA_real_, nrow(fit))
  cv_fold <- integer(nrow(fit))
  for (y in folds) {
    tr <- fit$year < y
    te <- fit$year == y
    m <- fit_gam(fit[tr, ], rule)
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
    x$lockdown <- rep(target$lockdown, each = CHUNK)
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

# Within-period blocked CV (DEC-112, a diagnostic): fold f trains on rows with w<f> TRUE and predicts
# rows with wfold == f, each with its own trend (inside the training range).
cv_within <- function(fit, w, rule) {
  pred <- rep(NA_real_, nrow(fit))
  for (f in sort(unique(w$wfold))) {
    tr <- w[[paste0("w", f)]]
    te <- w$wfold == f
    if (sum(tr) < 30 || sum(te) == 0) next
    m <- fit_gam(fit[tr, ], rule)
    pred[te] <- predict_log(m, fit[te, ])
  }
  list(pred = pred, fold = as.integer(w$wfold))
}

run_task <- function(run, pollutant, sid) {
  d <- file.path(INPUTS, run, pollutant, sid)
  fit <- as.data.frame(read_parquet(file.path(d, "fit.parquet")))
  target <- as.data.frame(read_parquet(file.path(d, "target.parquet")))
  pool <- as.data.frame(read_parquet(file.path(d, "pool.parquet")))
  folds <- as.integer(read_parquet(file.path(d, "folds.parquet"))$year)
  fit$lockdown <- lock_flag(fit$trend)
  target$lockdown <- lock_flag(target$trend)

  rule <- trend_rule_for(run)
  t0 <- proc.time()[["elapsed"]]
  cv <- cv_predict(fit, folds, convention, rule)
  cv_pred <- cv$pred
  cv_fold <- cv$fold
  cvw <- if (file.exists(file.path(d, "wfolds.parquet"))) {
    cv_within(fit, as.data.frame(read_parquet(file.path(d, "wfolds.parquet"))), rule)
  } else {
    list(pred = rep(NA_real_, nrow(fit)), fold = integer(nrow(fit)))
  }
  t1 <- proc.time()[["elapsed"]]
  m <- fit_gam(fit, rule)
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
  out$cvw_pred <- NA_real_
  out$cvw_fold <- 0L
  out$cvw_pred[rows] <- cvw$pred
  out$cvw_fold[rows] <- cvw$fold
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
    '"folds": [%s], "draws": %d, "schemes": [%s], "trend_rule": "%s", "trend_k": %d, "lockdown_term": %s, "edf": %.3f, ',
    '"secs_cv": %.3f, "secs_fit": %.3f, "secs_normalise": %.3f, "secs_total": %.3f}'),
    sid, pollutant, FAMILY, nrow(fit), nrow(target), paste(folds, collapse = ", "),
    max(checkpoints), paste0('"', schemes, '"', collapse = ", "), rule, trend_k(fit$trend, rule),
    tolower(as.character("lockdown" %in% all.vars(formula(m)))),
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
  fit$lockdown <- lock_flag(fit$trend)
  cv <- cv_predict(fit, folds, convention, trend_rule_for(run))
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

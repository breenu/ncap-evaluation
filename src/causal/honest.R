# HonestDiD (Rambachan & Roth 2023) on the Layer A event study (plan §5 item 2; DEC-097, DEC-143).
# GATED: run through `python -m src.causal.honest`, which checks the gate first.
#
#   Rscript src/causal/honest.R [<event-study dir>] [<name>]
#
# Inputs: <name>_coefs.csv and <name>_vcov.csv from src/causal/event_study.py (the interaction-weighted
# coefficients at l = -9..-2 and 0..+5 and their covariance; l = -1 is the reference).
# Target: the average post-period effect (weights 1/6 on l = 0..5).
# - relative magnitudes, Mbar in config causal.honest_mbar (method C-LF, the package default);
# - smoothness, M = 0 .. 2 x the largest pre-period SE in `honest_smooth_steps` equal steps (FLCI);
# - the original CI; and the breakdown Mbar: the largest Mbar whose robust 95% CI excludes 0, found by
#   bisection to `honest_breakdown_tol` between the grid points that bracket the change.
# Writes <name>_honest_rm.csv, <name>_honest_sm.csv, <name>_honest_summary.csv.

suppressPackageStartupMessages({
  library(HonestDiD)
  library(yaml)
})

P <- yaml::read_yaml("config/params.yaml")$causal
args <- commandArgs(trailingOnly = TRUE)
DIR <- if (length(args) >= 1) args[1] else "data/processed/causal/event_study"
NAME <- if (length(args) >= 2) args[2] else "es_primary"

co <- read.csv(file.path(DIR, paste0(NAME, "_coefs.csv")))
V <- as.matrix(read.csv(file.path(DIR, paste0(NAME, "_vcov.csv")), row.names = 1, check.names = FALSE))
win <- unlist(P$event_window)
pre <- seq(win[1], -2); post <- seq(0, win[2])
keep <- c(pre, post)
if (!all(keep %in% co$rel)) stop("event-study coefficients missing for some of ", paste(keep, collapse = ","))
b <- co$coef[match(keep, co$rel)]
S <- V[as.character(keep), as.character(keep)]
npre <- length(pre); npost <- length(post)
lvec <- rep(1 / npost, npost)

orig <- constructOriginalCS(betahat = b, sigma = S, numPrePeriods = npre, numPostPeriods = npost, l_vec = lvec)
# Warnings are recorded with each result, not just printed: an "open" CI means the robust interval
# reached the edge of the package's search grid, so its length is a lower bound.
with_warnings <- function(expr) {
  w <- character(0)
  r <- withCallingHandlers(expr, warning = function(x) { w <<- c(w, conditionMessage(x)); invokeRestart("muffleWarning") })
  r <- as.data.frame(r)
  r$warnings <- if (length(w)) paste(unique(gsub("[[:space:]]+", " ", w)), collapse = " | ") else ""
  r
}
rm_ci <- function(mbar) {
  do.call(rbind, lapply(mbar, function(m) with_warnings(
    createSensitivityResults_relativeMagnitudes(betahat = b, sigma = S, numPrePeriods = npre,
                                                numPostPeriods = npost, Mbarvec = m, l_vec = lvec))))
}
excl0 <- function(r) r$lb > 0 | r$ub < 0

grid <- unlist(P$honest_mbar)
rm <- rm_ci(grid)
sd_pre <- max(sqrt(diag(S))[seq_len(npre)])
mvec <- seq(0, 2 * sd_pre, length.out = P$honest_smooth_steps + 1)
sm <- do.call(rbind, lapply(mvec, function(m) with_warnings(
  createSensitivityResults(betahat = b, sigma = S, numPrePeriods = npre, numPostPeriods = npost, Mvec = m, l_vec = lvec))))

# breakdown: robust CIs widen as Mbar grows, so the "excludes 0" region is [0, breakdown]
ex <- excl0(rm)
if (!ex[1]) {
  breakdown <- NA_real_; note <- "none: the robust CI includes 0 at Mbar = 0"
} else if (all(ex)) {
  lo <- max(grid); hi <- P$honest_breakdown_max
  if (excl0(rm_ci(hi))) { breakdown <- Inf; note <- sprintf("> %g", hi) } else note <- ""
} else {
  k <- max(which(ex)); lo <- grid[k]; hi <- grid[k + 1]; note <- ""
}
if (note == "") {
  while (hi - lo > P$honest_breakdown_tol) {
    mid <- (lo + hi) / 2
    if (excl0(rm_ci(mid))) lo <- mid else hi <- mid
  }
  breakdown <- lo; note <- sprintf("%.2f", lo)
}

write.csv(rm, file.path(DIR, paste0(NAME, "_honest_rm.csv")), row.names = FALSE)
write.csv(sm, file.path(DIR, paste0(NAME, "_honest_sm.csv")), row.names = FALSE)
write.csv(data.frame(name = NAME, orig_lb = orig$lb, orig_ub = orig$ub,
                     direction = if (orig$lb > 0) "above 0 (an increase)" else if (orig$ub < 0) "below 0 (a reduction)" else "includes 0",
                     breakdown_mbar = breakdown,
                     breakdown_note = note, smooth_m_max = 2 * sd_pre, n_pre = npre, n_post = npost),
          file.path(DIR, paste0(NAME, "_honest_summary.csv")), row.names = FALSE)
cat("honest: done\n")

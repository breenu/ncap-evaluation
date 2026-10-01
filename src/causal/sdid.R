# Synthetic difference-in-differences engine for Layer A (Phase 7; DEC-139, DEC-145 to DEC-147, DEC-150).
#
#   Rscript src/causal/sdid.R <spec_id> [<spec_id> ...]      real fits + joint-placebo replications
#   Rscript src/causal/sdid.R --loo <spec_id>                leave-one-out donors (DEC-147 item 15)
#
# A specification is written by `python -m src.causal.layer_a specs` into data/processed/causal/specs/:
#   specs.csv          one row per spec: panel file, outcomes, years, dropped years, replications,
#                      null design, whether to keep effect curves / unit weights, a content hash
#   spec_units.parquet spec_id, unit_id, role (treated/control), cohort, cell, region
#   spec_fitsets.csv   spec_id, fitset, cohort, cells (';'), outcomes (';'): one SDID fit each
# A fit set's treated units are the spec's treated units of that cohort whose cell is listed; every
# control of the spec is a donor. Python combines fit sets into estimands (layer_a.summarise).
#
# Joint placebo (DEC-139): replication r draws, from the spec's controls, disjoint sets with exactly
# the sizes of the real (cell, cohort) groups ("random"), or region by region with the real regional
# counts ("region_matched", DEC-145). Each fit set is re-estimated on its placebo union of cells,
# with the controls not drawn in that replication as donors. All draws are made here, in the master
# process, from the config seed, so results do not depend on the number of workers.
#
# Resumable: replications are written in chunks; a spec whose stored hash differs is recomputed.
# BLAS must be single-threaded (the Snakemake rule and layer_a.run set it): workers supply parallelism.

suppressPackageStartupMessages({
  library(synthdid)
  library(arrow)
  library(yaml)
  library(parallel)
})

P <- yaml::read_yaml("config/params.yaml")
DIR <- Sys.getenv("NCAP_CAUSAL_DIR", "data/processed/causal")  # tests point this at a synthetic panel
SPEC_DIR <- file.path(DIR, "specs")
OUT_DIR <- file.path(DIR, "sdid")
CHUNK <- 50L

specs <- read.csv(file.path(SPEC_DIR, "specs.csv"), stringsAsFactors = FALSE)
units_all <- as.data.frame(read_parquet(file.path(SPEC_DIR, "spec_units.parquet")))
fitsets_all <- read.csv(file.path(SPEC_DIR, "spec_fitsets.csv"), stringsAsFactors = FALSE)

split1 <- function(x) if (is.na(x) || x == "") character(0) else strsplit(x, ";", fixed = TRUE)[[1]]

# Outcome matrices (units x years) for one spec; outcome strings are "<transform>:<series>".
outcome_matrices <- function(sp, unit_ids) {
  pan <- as.data.frame(read_parquet(file.path(DIR, sp$panel)))
  drop <- as.integer(split1(as.character(sp$drop_years)))
  pan <- pan[pan$year >= sp$year_min & pan$year <= sp$year_max & !(pan$year %in% drop) &
               pan$unit_id %in% unit_ids, ]
  out <- list()
  for (o in split1(sp$outcomes)) {
    tr <- sub(":.*", "", o); series <- sub("^[^:]*:", "", o)
    d <- pan[pan$series == series, ]
    if (anyDuplicated(d[, c("unit_id", "year")])) stop(sp$spec_id, ": duplicate unit-years in ", series)
    m <- tapply(d$value, list(d$unit_id, d$year), mean)
    m <- m[unit_ids, , drop = FALSE]
    storage.mode(m) <- "double"
    if (anyNA(m)) stop(sp$spec_id, ": unbalanced or missing panel for ", series)
    if (tr == "log") {
      if (any(m <= 0)) stop(sp$spec_id, ": non-positive values in ", series)
      m <- log(m)
    } else if (tr != "level") stop("unknown transform ", tr)
    out[[o]] <- m
  }
  out
}

# One SDID fit: rows = donors then treated; T0 = years before the cohort.
fit_one <- function(Y, treated, donors, cohort, keep_curve = FALSE, keep_weights = FALSE) {
  yrs <- as.integer(colnames(Y))
  T0 <- sum(yrs < cohort)
  if (T0 < 2 || T0 >= length(yrs)) stop("cohort ", cohort, " leaves T0 = ", T0)
  nwarn <- 0L
  est <- withCallingHandlers(
    synthdid_estimate(Y[c(donors, treated), , drop = FALSE], N0 = length(donors), T0 = T0),
    warning = function(w) { nwarn <<- nwarn + 1L; invokeRestart("muffleWarning") })
  res <- list(att = as.numeric(est), T0 = T0, nwarn = nwarn)
  if (keep_curve) res$curve <- data.frame(year = yrs[(T0 + 1):length(yrs)], effect = as.numeric(synthdid_effect_curve(est)))
  if (keep_weights) res$omega <- data.frame(unit_id = donors, omega = attr(est, "weights")$omega)
  res
}

# Real fits of one spec.
real_fits <- function(sp, U, FS, Ys, controls) {
  rows <- list(); curves <- list(); weights <- list()
  for (k in seq_len(nrow(FS))) {
    f <- FS[k, ]
    tr <- U$unit_id[U$role == "treated" & U$cohort == f$cohort & U$cell %in% split1(f$cells)]
    for (o in split1(f$outcomes)) {
      r <- fit_one(Ys[[o]], tr, controls, f$cohort, as.logical(sp$keep_curve), as.logical(sp$keep_weights))
      rows[[length(rows) + 1]] <- data.frame(fitset = f$fitset, outcome = o, cohort = f$cohort,
                                             n_treated = length(tr), n_controls = length(controls),
                                             T0 = r$T0, att = r$att, warnings = r$nwarn)
      if (!is.null(r$curve)) curves[[length(curves) + 1]] <- cbind(fitset = f$fitset, outcome = o, r$curve)
      if (!is.null(r$omega)) weights[[length(weights) + 1]] <- cbind(fitset = f$fitset, outcome = o, r$omega)
    }
  }
  list(est = do.call(rbind, rows),
       curve = if (length(curves)) do.call(rbind, curves) else NULL,
       weights = if (length(weights)) do.call(rbind, weights) else NULL)
}

# Placebo draws for all replications of a spec: a list of named vectors cell|cohort -> unit ids.
make_draws <- function(sp, U, controls) {
  tr <- U[U$role == "treated", ]
  key <- paste(tr$cell, tr$cohort, sep = "|")
  sizes <- table(key)
  set.seed(P$seed)
  ctl_region <- setNames(U$region, U$unit_id)[controls]
  lapply(seq_len(sp$reps), function(r) {
    if (sp$null_design == "random") {
      pool <- sample(controls, sum(sizes))
    } else if (sp$null_design == "region_matched") {
      need <- table(tr$region)
      pool <- unlist(lapply(names(need), function(g) sample(controls[ctl_region == g], need[[g]])))
      pool <- sample(pool)  # random order before cutting into cells
    } else stop("unknown null design ", sp$null_design)
    cuts <- rep(names(sizes), as.integer(sizes))
    split(pool, factor(cuts, levels = names(sizes)))
  })
}

placebo_rep <- function(job) {
  d <- job$draw; out <- list(); curves <- list()
  drawn <- unlist(d, use.names = FALSE)
  donors <- setdiff(CONTROLS, drawn)
  for (k in seq_len(nrow(FS))) {
    f <- FS[k, ]
    fake <- unlist(d[paste(split1(f$cells), f$cohort, sep = "|")], use.names = FALSE)
    for (o in split1(f$outcomes)) {
      r <- fit_one(YS[[o]], fake, donors, f$cohort, KEEP_CURVE)
      out[[length(out) + 1]] <- data.frame(rep = job$r, fitset = f$fitset, outcome = o, att = r$att, warnings = r$nwarn)
      if (!is.null(r$curve)) curves[[length(curves) + 1]] <- cbind(rep = job$r, fitset = f$fitset, outcome = o, r$curve)
    }
  }
  list(est = do.call(rbind, out), curve = if (length(curves)) do.call(rbind, curves) else NULL)
}

run_spec <- function(id, cl) {
  sp <- specs[specs$spec_id == id, ]
  if (nrow(sp) != 1) stop("unknown spec ", id)
  dir <- file.path(OUT_DIR, id)
  hash_file <- file.path(dir, "hash.txt")
  if (dir.exists(dir) && (!file.exists(hash_file) || readLines(hash_file)[1] != sp$spec_hash)) {
    cat(id, ": spec changed, recomputing\n"); unlink(dir, recursive = TRUE)
  }
  dir.create(dir, recursive = TRUE, showWarnings = FALSE)
  writeLines(sp$spec_hash, hash_file)

  U <- units_all[units_all$spec_id == id, ]
  FS <- fitsets_all[fitsets_all$spec_id == id, ]
  controls <- sort(U$unit_id[U$role == "control"])
  Ys <- outcome_matrices(sp, sort(U$unit_id))
  t0 <- Sys.time()

  if (!file.exists(file.path(dir, "estimates.parquet"))) {
    rf <- real_fits(sp, U, FS, Ys, controls)
    if (!is.null(rf$curve)) write_parquet(rf$curve, file.path(dir, "curve.parquet"))
    if (!is.null(rf$weights)) write_parquet(rf$weights, file.path(dir, "weights.parquet"))
    write_parquet(rf$est, file.path(dir, "estimates.parquet"))  # written last: marks the real fits done
  }

  if (sp$reps > 0) {
    draws <- make_draws(sp, U, controls)
    clusterExport(cl, c("fit_one", "split1"))
    assign("FS", FS, envir = .GlobalEnv); assign("YS", Ys, envir = .GlobalEnv)
    assign("CONTROLS", controls, envir = .GlobalEnv); assign("KEEP_CURVE", as.logical(sp$keep_curve), envir = .GlobalEnv)
    clusterExport(cl, c("FS", "YS", "CONTROLS", "KEEP_CURVE"))
    starts <- seq(1L, sp$reps, by = CHUNK)
    for (s in starts) {
      e <- min(s + CHUNK - 1L, sp$reps)
      f <- file.path(dir, sprintf("draws_%04d_%04d.parquet", s, e))
      if (file.exists(f)) next
      jobs <- lapply(s:e, function(r) list(r = r, draw = draws[[r]]))
      res <- parLapply(cl, jobs, placebo_rep)
      cur <- do.call(rbind, lapply(res, `[[`, "curve"))
      if (!is.null(cur)) write_parquet(cur, sub("draws_", "curves_", f))
      write_parquet(do.call(rbind, lapply(res, `[[`, "est")), f)
      cat(sprintf("%s: replications %d-%d of %d (%.1f min)\n", id, s, e, sp$reps,
                  as.numeric(difftime(Sys.time(), t0, units = "mins"))))
    }
  }
  writeLines(format(Sys.time(), "%Y-%m-%dT%H:%M:%S"), file.path(dir, "done.txt"))
  cat(sprintf("%s: done in %.1f min\n", id, as.numeric(difftime(Sys.time(), t0, units = "mins"))))
}

# Leave-one-out donors (DEC-147 item 15): drop each control with positive weight in any of the spec's
# real fits (first outcome only) and re-estimate every fit set of that outcome. Point estimates only.
run_loo <- function(id, cl) {
  sp <- specs[specs$spec_id == id, ]
  dir <- file.path(OUT_DIR, id)
  w <- as.data.frame(read_parquet(file.path(dir, "weights.parquet")))
  o1 <- split1(sp$outcomes)[1]
  w <- w[w$outcome == o1, ]
  donors_pos <- sort(unique(w$unit_id[w$omega > 0]))
  U <- units_all[units_all$spec_id == id, ]
  FS <- fitsets_all[fitsets_all$spec_id == id, ]
  FS <- FS[vapply(FS$outcomes, function(x) o1 %in% split1(x), logical(1)) & FS$fitset %in% unique(w$fitset), ]
  controls <- sort(U$unit_id[U$role == "control"])
  Ys <- outcome_matrices(sp, sort(U$unit_id))
  assign("FS", FS, envir = .GlobalEnv); assign("YS", Ys, envir = .GlobalEnv); assign("CONTROLS", controls, envir = .GlobalEnv)
  assign("U", U, envir = .GlobalEnv); assign("O1", o1, envir = .GlobalEnv)
  clusterExport(cl, c("fit_one", "split1", "FS", "YS", "CONTROLS", "U", "O1"))
  t0 <- Sys.time()
  res <- parLapply(cl, donors_pos, function(dropped) {
    do.call(rbind, lapply(seq_len(nrow(FS)), function(k) {
      f <- FS[k, ]
      tr <- U$unit_id[U$role == "treated" & U$cohort == f$cohort & U$cell %in% split1(f$cells)]
      data.frame(dropped = dropped, fitset = f$fitset, outcome = O1,
                 att = fit_one(YS[[O1]], tr, setdiff(CONTROLS, dropped), f$cohort)$att)
    }))
  })
  write_parquet(do.call(rbind, res), file.path(dir, "loo.parquet"))
  cat(sprintf("%s: leave-one-out over %d donors in %.1f min\n", id, length(donors_pos),
              as.numeric(difftime(Sys.time(), t0, units = "mins"))))
}

args <- commandArgs(trailingOnly = TRUE)
if (!length(args)) stop("usage: Rscript src/causal/sdid.R [--loo] <spec_id> ...")
cl <- makeCluster(as.integer(Sys.getenv("NCAP_WORKERS", P$causal$workers)))
invisible(clusterEvalQ(cl, suppressPackageStartupMessages(library(synthdid))))
if (args[1] == "--loo") {
  for (id in args[-1]) run_loo(id, cl)
} else {
  for (id in args) run_spec(id, cl)
}
stopCluster(cl)

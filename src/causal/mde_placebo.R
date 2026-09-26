# Minimum detectable effect for the primary satellite SDID estimate, by placebo-in-time on
# pre-2019 data only (docs/analysis_plan.md §6; DEC-013, DEC-087).
#
#   Rscript src/causal/mde_placebo.R
#
# Reads data/interim/pregate/panel_annual.parquet and panel_season.parquet (written by
# `python -m src.causal.pregate`, which filters to year <= 2018 while reading) and stops if any year
# after config pregate.last_year is present.
#
# 1. Null spread. For each of `placebo_draws` random sets of N1 control units (N1 = the number of
#    real treated units), those units are labelled "treated" from a fake adoption year (2014, 2015)
#    and SDID is estimated against the remaining controls. No NCAP unit is involved. Two designs:
#    "random" (any N1 controls) and "region_matched" (as many controls from each region as the real
#    treated set has), because random sets spread over India average away regional shocks that a
#    real, regionally clustered treated set would carry. The SD of these
#    placebo ATTs is the standard error of an SDID estimate of this design with no true effect;
#    MDE = 2.8 x SE (5% two-sided, 80% power). The same draws serve every outcome, so the SE of
#    winter minus non-winter is estimated jointly.
# 2. Real treated set at the fake years: a pre-period placebo on the actual NCAP units (data <= 2018).
#
# BLAS is pinned to one thread by the caller (workflow/rules/causal.smk): with multi-threaded BLAS
# each fit is ~9x slower and the parallel workers fight over cores.

suppressPackageStartupMessages({
  library(synthdid)
  library(arrow)
  library(yaml)
  library(parallel)
})

P <- yaml::read_yaml("config/params.yaml")
pg <- P$pregate
dir <- "data/interim/pregate"
last <- pg$last_year

ann <- as.data.frame(read_parquet(file.path(dir, "panel_annual.parquet")))
sea <- as.data.frame(read_parquet(file.path(dir, "panel_season.parquet")))
if (max(ann$year) > last || max(sea$season_year) > last) stop("post-2018 data in the pre-gate panel")
# winter season-year t ends in Feb t+1: it must end by Dec of `last`
if (max(sea$season_year[sea$season == "winter"]) > last - 1) stop("a winter season extends past the pre-period")

wide <- function(df, value, time) {
  if (anyDuplicated(df[, c("unit_id", time)])) stop("duplicate unit-periods for ", value)
  m <- tapply(df[[value]], list(df$unit_id, df[[time]]), mean)
  storage.mode(m) <- "double"
  if (anyNA(m)) stop("unbalanced panel for ", value)
  m
}

outcomes <- list(
  log_annual    = log(wide(ann, "pm25_popw", "year")),
  level_annual  = wide(ann, "pm25_popw", "year"),
  log_winter    = log(wide(sea[sea$season == "winter", ], "pm25_popw", "season_year")),
  log_nonwinter = log(wide(sea[sea$season == "nonwinter", ], "pm25_popw", "season_year"))
)

roles <- unique(ann[, c("unit_id", "role", "region")])
controls <- sort(roles$unit_id[roles$role == "control"])
treated <- sort(roles$unit_id[roles$role == "treated"])
N1 <- length(treated)
fake_years <- unlist(pg$fake_adoption_years)
R <- pg$placebo_draws
args <- commandArgs(trailingOnly = TRUE)
if (length(args)) R <- as.integer(args[1])  # smoke test only; the pipeline uses the config value

sdid_att <- function(Y, tr, co, fake) {
  yrs <- as.integer(colnames(Y))
  T0 <- sum(yrs < fake)
  as.numeric(synthdid_estimate(Y[c(co, tr), , drop = FALSE], N0 = length(co), T0 = T0))
}

# All random sets are drawn here, in one seeded stream, so results do not depend on worker count.
set.seed(P$seed)
draws_random <- replicate(R, sample(controls, N1))
tr_regions <- table(roles$region[roles$role == "treated"])
ctl_region <- setNames(roles$region, roles$unit_id)[controls]
draws_matched <- replicate(R, unlist(lapply(names(tr_regions), function(g)
  sample(controls[ctl_region == g], tr_regions[[g]]))))
designs <- list(random = draws_random, region_matched = draws_matched)

one_draw <- function(job) {
  d <- job$design; r <- job$r
  tr <- designs[[d]][, r]
  co <- setdiff(controls, tr)
  out <- list()
  for (o in names(outcomes)) for (f in fake_years)
    out[[length(out) + 1]] <- data.frame(design = d, draw = r, outcome = o, fake_year = f,
                                          att = sdid_att(outcomes[[o]], tr, co, f))
  do.call(rbind, out)
}
jobs <- unlist(lapply(names(designs), function(d) lapply(seq_len(R), function(r) list(design = d, r = r))),
               recursive = FALSE)

t0 <- Sys.time()
cl <- makeCluster(pg$workers)
invisible(clusterEvalQ(cl, suppressPackageStartupMessages(library(synthdid))))
clusterExport(cl, c("designs", "controls", "outcomes", "fake_years", "sdid_att"))
res <- do.call(rbind, parLapply(cl, jobs, one_draw))
stopCluster(cl)
cat(sprintf("placebo draws: %d designs x %d x %d outcomes x %d fake years in %.1f min\n",
            length(designs), R, length(outcomes), length(fake_years), as.numeric(difftime(Sys.time(), t0, units = "mins"))))

actual <- do.call(rbind, lapply(names(outcomes), function(o) do.call(rbind, lapply(fake_years, function(f)
  data.frame(outcome = o, fake_year = f, att = sdid_att(outcomes[[o]], treated, controls, f))))))

meta <- data.frame(n_treated = N1, n_controls = length(controls), draws = R, seed = P$seed,
                   first_year = min(ann$year), last_year = max(ann$year),
                   season_first = min(sea$season_year), season_last = max(sea$season_year))

write_parquet(res, file.path(dir, "mde_draws.parquet"))
write.csv(actual, file.path(dir, "placebo_actual.csv"), row.names = FALSE)
write.csv(meta, file.path(dir, "mde_meta.csv"), row.names = FALSE)

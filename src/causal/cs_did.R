# Callaway & Sant'Anna (2021) for Layer A (plan §5 item 3; DEC-144). GATED: run through
# `python -m src.causal.cs_did`, which checks the gate first.
#
#   Rscript src/causal/cs_did.R [<panel dir>]
#
# Panel: data/processed/causal/panel_annual.parquet (log population-weighted V5.GL.06), treated units
# with their listing cohort and never-treated controls (design_units.csv), 2010-2024 without 2020.
# With 2020 absent, did uses 2019 as the base year of cohorts 2020 and 2021 (checked on synthetic data
# against a hand-computed DiD, DEC-144). est_method = "dr" as registered; the registered text names no
# covariates, so xformla = ~1 (the doubly robust estimator is then the unconditional DiD).
# Never-treated controls are primary; not-yet-treated is the sensitivity check.
# Writes data/processed/causal/cs/: cs_<controls>_simple.csv, cs_<controls>_dynamic.csv, cs_<controls>_attgt.csv

suppressPackageStartupMessages({
  library(did)
  library(arrow)
  library(yaml)
})

P <- yaml::read_yaml("config/params.yaml")
args <- commandArgs(trailingOnly = TRUE)
DIR <- if (length(args)) args[1] else "data/processed/causal"
OUT <- file.path(DIR, "cs")
dir.create(OUT, showWarnings = FALSE, recursive = TRUE)

u <- read.csv(file.path(DIR, "design_units.csv"), stringsAsFactors = FALSE)
u <- u[u$role_a %in% c("treated", "control"), ]
pan <- as.data.frame(read_parquet(file.path(DIR, "panel_annual.parquet")))
drop <- unlist(P$causal$years_drop)
pan <- pan[pan$series == "popw_V5GL06" & pan$unit_id %in% u$unit_id & !(pan$year %in% drop), ]
pan$y <- log(pan$value)
pan$g <- ifelse(u$role_a[match(pan$unit_id, u$unit_id)] == "treated", u$cohort_listed[match(pan$unit_id, u$unit_id)], 0)
pan$id <- as.integer(factor(pan$unit_id))
if (anyNA(pan$g) || any(table(pan$id) != length(unique(pan$year)))) stop("CS panel is not balanced or lacks cohorts")
win <- unlist(P$causal$event_window)

for (cg in c("nevertreated", "notyettreated")) {
  set.seed(P$seed)
  a <- att_gt(yname = "y", tname = "year", idname = "id", gname = "g", data = pan,
              control_group = cg, est_method = "dr", xformla = ~1, base_period = "varying",
              bstrap = TRUE, cband = TRUE, biters = P$causal$cs_biters, clustervars = "id")
  s <- aggte(a, type = "simple", bstrap = TRUE, biters = P$causal$cs_biters)
  dy <- aggte(a, type = "dynamic", min_e = win[1], max_e = win[2], bstrap = TRUE, cband = TRUE,
              biters = P$causal$cs_biters)
  write.csv(data.frame(control_group = cg, att = s$overall.att, se = s$overall.se,
                       lo95 = s$overall.att - 1.959964 * s$overall.se, hi95 = s$overall.att + 1.959964 * s$overall.se,
                       n_units = length(unique(pan$id)), n_treated = length(unique(pan$id[pan$g > 0]))),
            file.path(OUT, sprintf("cs_%s_simple.csv", cg)), row.names = FALSE)
  crit <- dy$crit.val.egt
  write.csv(data.frame(control_group = cg, rel = dy$egt, att = dy$att.egt, se = dy$se.egt,
                       lo95 = dy$att.egt - 1.959964 * dy$se.egt, hi95 = dy$att.egt + 1.959964 * dy$se.egt,
                       ulo = dy$att.egt - crit * dy$se.egt, uhi = dy$att.egt + crit * dy$se.egt, crit_uniform = crit),
            file.path(OUT, sprintf("cs_%s_dynamic.csv", cg)), row.names = FALSE)
  write.csv(data.frame(control_group = cg, group = a$group, year = a$t, att = a$att, se = a$se),
            file.path(OUT, sprintf("cs_%s_attgt.csv", cg)), row.names = FALSE)
  cat(cg, ": done\n")
}

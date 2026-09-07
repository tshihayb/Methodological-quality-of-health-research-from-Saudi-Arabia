###############################################################################
##  DOMAIN PREVALENCES UNDER MISCLASSIFICATION, BY STUDY TASK -- the data behind
##  the corrected Supplementary Figure S13.
##
##  Project : Assessment of Healthcare Research Quality in Saudi Arabia
##  Plan    : docs/SENSITIVITY_ANALYSIS_PLAN.md sections 3 and 3b, split by task at
##            TSA's request (2026-08-29)
##  Run FROM THE REPOSITORY ROOT.
##
##  WHY THIS EXISTS, AND WHY 08_20_2026_reporting_axis_and_upward.R IS NOT ENOUGH
##  That script corrects the POOLED prevalence, over every applicable study regardless
##  of task. Figure 5 does not report pooled prevalences: panels A to C are "by domain
##  and study task", and the Abstract quotes the CAUSAL figures -- measurement bias
##  100%, confounding 87.8%, selection bias 79.9%. Pooled, those same three domains read
##  99.7%, 87.8% and 76.8%. So the pooled correction was a sensitivity analysis of
##  numbers adjacent to the paper's claims rather than of the claims themselves.
##
##  ⚠ AND POOLING IS THE OPERATION THE METHODS ALREADY REJECT. "Because the two tasks
##  are scored on different item sets, every stratification is reported within task;
##  pooling would let task mix masquerade as quality." A pooled prevalence is not even
##  a weighted average of the two task prevalences at the sample's own mix, because the
##  applicable base differs by domain: random error applies to 190 causal and 55
##  descriptive studies, not 229 and 81.
##
##  WHAT IS AND IS NOT DIFFERENT FROM 3b
##  The perturbation is IDENTICAL: both axes in one draw, the same measured and imputed
##  parameters, the same logit-normal redraw per draw. Only the denominators split. The
##  fast engine is 3b's, with a task dimension added to the cell selector, and it carries
##  3b's equivalence assertion against roll_up() unchanged.
##
##  SELF-CHECKS (keep these passing)
##   1. the fast engine reproduces roll_up() exactly, at the parameters used and at an
##      exaggerated setting, on both axes;
##   2. every by-task baseline reproduces the published scored dataset;
##   3. recombining the two task counts reproduces 3b's pooled baseline exactly, so the
##      split is a partition and not a different analysis.
##
##  OUTPUT (outputs/tables/)
##    08_29_2026_bias_analysis_by_task.csv    corrected prevalence per domain/axis/task
##    08_29_2026_tipping_point_by_task.csv    the 70/50/25 crossings per domain/task
###############################################################################

source("code/lib/score_dataset_lib.R")

PROJ  <- getwd(); STAMP <- "08_29_2026"
TBL   <- file.path(PROJ, "outputs", "tables"); stopifnot(dir.exists(TBL))
set.seed(20260829L)
M_DRAWS <- as.integer(Sys.getenv("SENS_DRAWS", "2000"))
M_SWEEP <- as.integer(Sys.getenv("SENS_SWEEP", "500"))
f    <- function(p) file.path(PROJ, p)
lgt  <- function(p) log(p / (1 - p))
ilgt <- function(x) 1 / (1 + exp(-x))
TASKS <- c("Causal", "Descriptive")

###############################################################################
## 1.  Baseline, by task
###############################################################################
d     <- read.csv(f("data/analysis/07_23_2026_ANALYSIS_DATASET_wide.csv"),
                  stringsAsFactors = FALSE, colClasses = "character", check.names = FALSE)
items <- score_items(d)
base_dom <- roll_up(items)
DOMS <- DOMS_ORDER

prev_task <- function(dom, flag) {
  a <- dom[dom$state != "NA", ]
  do.call(rbind, lapply(DOMS, function(dm) do.call(rbind, lapply(TASKS, function(tk) {
    z <- a[a$domain == dm & a$Study_Type == tk, ]
    if (!nrow(z)) return(NULL)
    data.frame(domain = dm, task = tk, applicable = nrow(z),
               n = sum(z$state == flag), prevalence = mean(z$state == flag),
               stringsAsFactors = FALSE)
  }))))
}
BV <- prev_task(base_dom, "VAL"); BR <- prev_task(base_dom, "REP")
BASE <- merge(BV[, c("domain","task","applicable","prevalence")],
              BR[, c("domain","task","prevalence")], by = c("domain","task"),
              suffixes = c("_val", "_rep"))
BASE <- BASE[order(match(BASE$domain, DOMS), BASE$task), ]
cat("=========== BASELINE BY TASK (all parameters = 0) ===========\n\n")
print(BASE, row.names = FALSE, digits = 3)

## ---- self-check 2: the by-task baselines are the published ones -------------------
SD <- read.csv(f("data/scoring/07_30_2026_scored_domain.csv"), stringsAsFactors = FALSE,
               colClasses = "character", na.strings = character(0))
for (i in seq_len(nrow(BASE))) {
  z <- SD[SD$domain == BASE$domain[i] & SD$Study_Type == BASE$task[i] & SD$state != "NA", ]
  stopifnot(nrow(z) == BASE$applicable[i],
            abs(mean(z$state == "VAL") - BASE$prevalence_val[i]) < 1e-12,
            abs(mean(z$state == "REP") - BASE$prevalence_rep[i]) < 1e-12)
}
cat("\n[self-check 2: every by-task baseline reproduces the scored dataset]\n")

## ---- self-check 3: the split is a partition of 3b's pooled baseline ---------------
POOL <- read.csv(f("outputs/tables/08_20_2026_bias_analysis_both_axes.csv"),
                 stringsAsFactors = FALSE)
for (ax in c("VAL","REP")) {
  col <- if (ax == "VAL") "prevalence_val" else "prevalence_rep"
  for (dm in DOMS) {
    b <- BASE[BASE$domain == dm, ]
    if (!nrow(b)) next
    got <- sum(b[[col]] * b$applicable) / sum(b$applicable)
    want <- POOL$baseline[POOL$axis == ax & POOL$domain == dm]
    stopifnot(length(want) == 1, abs(got - want) < 1e-12)
  }
}
cat("[self-check 3: recombining the tasks reproduces 3b's pooled baseline exactly]\n")

###############################################################################
## 2.  Parameters -- identical sourcing to 3b, re-read not re-derived
###############################################################################
FL  <- read.csv(f("outputs/tables/08_19_2026_calibration_flag_level_by_domain.csv"),
                stringsAsFactors = FALSE)
IMP <- read.csv(f("outputs/tables/08_19_2026_calibration_imputed_parameters.csv"),
                stringsAsFactors = FALSE)
IMP <- IMP[IMP$donor_pool == paste("usable", IMP$axis, "cells"), ]

getp <- function(dom, axis) {
  z <- FL[FL$domain == dom & FL$axis == axis, ]
  if (nrow(z) && !z$degenerate[1])
    return(list(e1 = z$eps1[1], e0 = z$eps0[1], e1lo = z$eps1_lo[1], e1hi = z$eps1_hi[1],
                e0lo = z$eps0_lo[1], e0hi = z$eps0_hi[1], src = "measured"))
  y <- IMP[IMP$domain == dom & IMP$axis == axis, ]
  if (nrow(y)) {
    pool <- FL[FL$axis == axis & !FL$degenerate, ]
    d1 <- pool[which.max(pool$eps1), ]; d0 <- pool[which.max(pool$eps0), ]
    return(list(e1 = y$eps1_max[1], e0 = y$eps0_max[1], e1lo = d1$eps1_lo[1],
                e1hi = d1$eps1_hi[1], e0lo = d0$eps0_lo[1], e0hi = d0$eps0_hi[1],
                src = "imputed (max)"))
  }
  list(e1 = 0, e0 = 0, e1lo = NA, e1hi = NA, e0lo = NA, e0hi = NA, src = "not applicable")
}
PAR <- do.call(rbind, lapply(DOMS, function(dm)
  do.call(rbind, lapply(c("VAL","REP"), function(ax) {
    p <- getp(dm, ax)
    data.frame(domain = dm, axis = ax, e1 = p$e1, e0 = p$e0, e1lo = p$e1lo, e1hi = p$e1hi,
               e0lo = p$e0lo, e0hi = p$e0hi, source = p$src, stringsAsFactors = FALSE) }))))
stopifnot(all(PAR$source[PAR$axis == "REP"] %in% c("measured", "not applicable")))

draw_one <- function(pt, lo, hi) {
  if (is.na(lo) || is.na(hi) || pt <= 0 || pt >= 1) return(pt)
  lo <- max(lo, 1e-3); hi <- min(hi, 1 - 1e-3)
  if (hi <= lo) return(pt)
  ilgt(rnorm(1, lgt(pt), (lgt(hi) - lgt(lo)) / (2 * 1.96)))
}
perturb_once <- function(it, par, scale_e1 = 1, scale_e0 = 1) {
  st  <- it$state; app <- st != "NA"; isV <- st == "VAL"; isR <- st == "REP"
  mV <- match(paste(it$domain, "VAL"), paste(par$domain, par$axis))
  mR <- match(paste(it$domain, "REP"), paste(par$domain, par$axis))
  e1 <- par$e1[mV] * scale_e1; e0 <- par$e0[mV] * scale_e0
  d1 <- par$e1[mR] * scale_e1; d0 <- par$e0[mR] * scale_e0
  u  <- runif(length(st)); newV <- ifelse(isV, u  > e1, u  < e0) & app
  u2 <- runif(length(st)); newR <- ifelse(isR, u2 > d1, u2 < d0) & app
  it$state <- ifelse(!app, "NA", ifelse(newV, "VAL", ifelse(newR, "REP", "OK")))
  it
}

###############################################################################
## 3.  3b's fast engine, with a TASK dimension on the cell selector
###############################################################################
NALL <- nrow(items)
pri  <- which(items$primary)
cell <- factor(paste(items$PMID[pri], items$domain[pri]))
gi   <- as.integer(cell); G <- nlevels(cell)
lev  <- levels(cell); key <- paste(items$PMID[pri], items$domain[pri])
cdom  <- items$domain[pri][match(lev, key)]
ctask <- items$Study_Type[pri][match(lev, key)]
st0  <- items$state[pri]
app0 <- st0 != "NA"; isV0 <- st0 == "VAL"; isR0 <- st0 == "REP"
nApp <- tabulate(gi[app0], nbins = G)

CELLS <- do.call(rbind, lapply(DOMS, function(dm) do.call(rbind, lapply(TASKS, function(tk) {
  s <- cdom == dm & ctask == tk & nApp > 0
  if (!any(s)) return(NULL)
  data.frame(domain = dm, task = tk, n = sum(s), stringsAsFactors = FALSE)
}))))
SEL <- lapply(seq_len(nrow(CELLS)), function(i)
  cdom == CELLS$domain[i] & ctask == CELLS$task[i] & nApp > 0)
KEYS <- paste(CELLS$domain, CELLS$task)
stopifnot(identical(sort(paste(BASE$domain, BASE$task)), sort(KEYS)))

pidx <- list(V = match(paste(items$domain[pri], "VAL"), paste(PAR$domain, PAR$axis)),
             R = match(paste(items$domain[pri], "REP"), paste(PAR$domain, PAR$axis)))

draw_stats_fast <- function(par, scale_e1 = 1, scale_e0 = 1) {
  e1 <- par$e1[pidx$V] * scale_e1; e0 <- par$e0[pidx$V] * scale_e0
  d1 <- par$e1[pidx$R] * scale_e1; d0 <- par$e0[pidx$R] * scale_e0
  u  <- runif(NALL)[pri]; newV <- ifelse(isV0, u  > e1, u  < e0) & app0
  u2 <- runif(NALL)[pri]; newR <- ifelse(isR0, u2 > d1, u2 < d0) & app0
  nV <- tabulate(gi[newV], nbins = G); nR <- tabulate(gi[newR], nbins = G)
  cV <- nV > 0
  cR <- nV == 0 & nR > 0
  c(vapply(SEL, function(s) sum(cV[s]) / sum(s), numeric(1)),
    vapply(SEL, function(s) sum(cR[s]) / sum(s), numeric(1)))
}
draw_stats_ref <- function(it) {
  a <- roll_up(it); a <- a[a$state != "NA", ]
  k <- paste(a$domain, a$task <- a$Study_Type)
  c(vapply(KEYS, function(q) mean(a$state[k == q] == "VAL"), numeric(1)),
    vapply(KEYS, function(q) mean(a$state[k == q] == "REP"), numeric(1)))
}

## ---- self-check 1: exact equivalence with roll_up(), same random stream -----------
for (tst in list(list(s1 = 1, s0 = 1), list(s1 = 0.6, s0 = 0.4))) {
  sd0 <- .Random.seed
  a <- draw_stats_fast(PAR, tst$s1, tst$s0)
  assign(".Random.seed", sd0, envir = .GlobalEnv)
  b <- draw_stats_ref(perturb_once(items, PAR, tst$s1, tst$s0))
  stopifnot(length(a) == length(b), max(abs(a - unname(b))) < 1e-12)
}
cat("[self-check 1: the by-task fast engine reproduces roll_up() exactly]\n")

###############################################################################
## 4.  Corrected prevalence by task -- probabilistic, parameters redrawn per draw
###############################################################################
cat(sprintf("\n=========== CORRECTED PREVALENCE BY TASK, %d draws ===========\n", M_DRAWS))
t0 <- Sys.time()
SP <- vapply(seq_len(M_DRAWS), function(i) {
  p <- PAR
  for (k in seq_len(nrow(p))) {
    p$e1[k] <- draw_one(PAR$e1[k], PAR$e1lo[k], PAR$e1hi[k])
    p$e0[k] <- draw_one(PAR$e0[k], PAR$e0lo[k], PAR$e0hi[k])
  }
  draw_stats_fast(p)
}, numeric(2 * nrow(CELLS)))
cat(sprintf("[%.1f min]\n", as.numeric(difftime(Sys.time(), t0, units = "mins"))))

q <- function(M, p) apply(M, 1, quantile, p, na.rm = TRUE)
NC <- nrow(CELLS)
ADJ <- do.call(rbind, lapply(c("VAL","REP"), function(ax) {
  r <- if (ax == "VAL") seq_len(NC) else NC + seq_len(NC)
  bcol <- if (ax == "VAL") "prevalence_val" else "prevalence_rep"
  b <- BASE[[bcol]][match(KEYS, paste(BASE$domain, BASE$task))]
  data.frame(axis = ax, domain = CELLS$domain, task = CELLS$task,
             applicable = CELLS$n, baseline = b,
             median = apply(SP[r, , drop = FALSE], 1, median),
             lo = q(SP[r, , drop = FALSE], .025), hi = q(SP[r, , drop = FALSE], .975),
             param_source = PAR$source[match(paste(CELLS$domain, ax),
                                             paste(PAR$domain, PAR$axis))],
             stringsAsFactors = FALSE)
}))
ADJ$shift <- ADJ$median - ADJ$baseline
ADJ$interval_contains_baseline <- ADJ$baseline >= ADJ$lo & ADJ$baseline <= ADJ$hi
print(ADJ, row.names = FALSE, digits = 3)
write.csv(ADJ, file.path(TBL, sprintf("%s_bias_analysis_by_task.csv", STAMP)), row.names = FALSE)

###############################################################################
## 5.  Tipping point by task -- epsilon_0 = 0, assumption-free
###############################################################################
GRID <- seq(0, 0.9, by = 0.05)
cat(sprintf("\n=========== TIPPING POINT BY TASK: %d draws x %d grid points ===========\n",
            M_SWEEP, length(GRID)))
t0 <- Sys.time()
SWEEP <- do.call(rbind, lapply(GRID, function(g) {
  p <- PAR; p$e1 <- g; p$e0 <- 0
  p$e1[p$source == "not applicable"] <- 0
  M <- vapply(seq_len(M_SWEEP), function(i) draw_stats_fast(p), numeric(2 * NC))
  data.frame(value = g, domain = CELLS$domain, task = CELLS$task,
             prevalence = apply(M[seq_len(NC), , drop = FALSE], 1, median),
             stringsAsFactors = FALSE)
}))
cat(sprintf("[%.1f min]\n", as.numeric(difftime(Sys.time(), t0, units = "mins"))))
write.csv(SWEEP, file.path(TBL, sprintf("%s_tipping_point_sweep_by_task.csv", STAMP)),
          row.names = FALSE)

cross <- function(z, thr) {
  z <- z[order(z$value), ]
  i <- which(z$prevalence < thr)[1]
  if (is.na(i)) return(NA_real_)
  if (i == 1) return(0)
  x1 <- z$value[i-1]; x2 <- z$value[i]; y1 <- z$prevalence[i-1]; y2 <- z$prevalence[i]
  if (y1 == y2) return(x2)
  x1 + (y1 - thr) / (y1 - y2) * (x2 - x1)
}
TP <- do.call(rbind, lapply(seq_len(NC), function(i) {
  z <- SWEEP[SWEEP$domain == CELLS$domain[i] & SWEEP$task == CELLS$task[i], ]
  b <- ADJ$baseline[ADJ$axis == "VAL" & ADJ$domain == CELLS$domain[i] &
                    ADJ$task == CELLS$task[i]]
  data.frame(domain = CELLS$domain[i], task = CELLS$task[i], baseline = b,
             rate_used = PAR$e1[PAR$domain == CELLS$domain[i] & PAR$axis == "VAL"],
             rate_source = PAR$source[PAR$domain == CELLS$domain[i] & PAR$axis == "VAL"],
             e1_to_fall_below_70 = cross(z, .70),
             e1_to_fall_below_50 = cross(z, .50),
             e1_to_fall_below_25 = cross(z, .25),
             stringsAsFactors = FALSE)
}))
print(TP, row.names = FALSE, digits = 3)
write.csv(TP, file.path(TBL, sprintf("%s_tipping_point_by_task.csv", STAMP)), row.names = FALSE)

cat("\nwrote 3 tables to outputs/tables/\n")

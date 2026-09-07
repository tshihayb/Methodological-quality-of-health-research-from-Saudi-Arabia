###############################################################################
##  SECTION 3b -- THE REPORTING AXIS AND THE UPWARD DIRECTION
##
##  Project : Assessment of Healthcare Research Quality in Saudi Arabia
##  Plan    : docs/SENSITIVITY_ANALYSIS_PLAN.md section 3b
##  Date    : 2026-08-20
##  Run FROM THE REPOSITORY ROOT.
##
##  WHY THIS EXISTS
##  08_19_2026_tipping_point.R perturbs BOTH axes in every draw -- delta is an
##  input to every result already -- but it only ever REPORTS mean(state=="VAL"),
##  so the reporting axis goes in and never comes out. And its sweep moves only
##  epsilon_1, the direction that REMOVES validity flaws, which is the wrong
##  question for a low-prevalence domain: for Missing data (19.0%) and Random
##  error (30.2%) a reviewer asks how HIGH the number could really be.
##
##  THREE DELIVERABLES
##   (1) corrected REPORTING-gap prevalences, probabilistic, 2,000 draws.
##       Four domains are REP-capable -- Random error, Selection bias, Missing
##       data, Mentioning errors -- and all four have MEASURED delta. There is
##       no imputation anywhere on this axis, unlike validity.
##   (2) epsilon_0 sweep with epsilon_1 = 0 -- the upward direction on validity.
##   (3) delta_1 and delta_0 sweeps -- the only tipping point Mentioning errors
##       can ever have, since that domain produces no VAL flag at all.
##
##  DEFINITION, stated because it is a choice and not a fact:
##  a domain's state is the weakest link over its primary items (VAL > REP > OK
##  > NA), so "REP prevalence" here means *a reporting gap and no validity flaw*.
##  Validity flaws mask reporting gaps by construction; a perturbation that adds
##  a VAL flag therefore LOWERS measured REP prevalence without any reporting
##  parameter moving. Both curves are reported side by side so that shows.
##
##  THRESHOLDS ARE NOT CHOSEN HERE. The 70/50/25% ladder was built for the
##  high-prevalence domains; at 19.0% "could missing data exceed 50%?" is a
##  straw man. Rather than pick a bar unilaterally -- the threshold IS the claim
##  being defended -- every crossing is computed over a full ladder and written
##  out, so TSA picks the headline afterwards without a re-run.
###############################################################################

source("code/lib/score_dataset_lib.R")

PROJ  <- getwd(); STAMP <- "08_20_2026"
TBL   <- file.path(PROJ, "outputs", "tables"); stopifnot(dir.exists(TBL))
set.seed(20260820L)
M_DRAWS <- 2000L   # bias analysis: tail percentiles need the draws
M_SWEEP <-  500L   # empirically settled: 200 -> 2,000 moved crossings <= 0.0033
f <- function(p) file.path(PROJ, p)
lgt  <- function(p) log(p / (1 - p))
ilgt <- function(x) 1 / (1 + exp(-x))

###############################################################################
## 1.  Baseline on BOTH axes
###############################################################################
d     <- read.csv(f("data/analysis/07_23_2026_ANALYSIS_DATASET_wide.csv"),
                  stringsAsFactors = FALSE, colClasses = "character", check.names = FALSE)
items <- score_items(d)
base_dom <- roll_up(items)

## generalised prev(): the flag is an argument now, denominator unchanged
prev <- function(dom, flag = "VAL") {
  a <- dom[dom$state != "NA", ]
  do.call(rbind, lapply(split(a, a$domain), function(z) data.frame(
    domain = z$domain[1], applicable = nrow(z), n = sum(z$state == flag),
    prevalence = mean(z$state == flag), stringsAsFactors = FALSE)))
}
BV <- prev(base_dom, "VAL"); BR <- prev(base_dom, "REP")
DOMS <- BV$domain
BASE <- data.frame(domain = DOMS, applicable = BV$applicable,
                   val_prevalence = BV$prevalence, rep_prevalence = BR$prevalence,
                   stringsAsFactors = FALSE)
cat("=========== BASELINE, BOTH AXES (published analysis: all parameters = 0) ===========\n")
cat("rep_prevalence = reporting gap AND no validity flaw (weakest-link precedence).\n\n")
print(BASE, row.names = FALSE, digits = 3)

###############################################################################
## 2.  Parameters -- identical sourcing to section 3, re-read not re-derived
###############################################################################
FL  <- read.csv(f("outputs/tables/08_19_2026_calibration_flag_level_by_domain.csv"),
                stringsAsFactors = FALSE)
IMP <- read.csv(f("outputs/tables/08_19_2026_calibration_imputed_parameters.csv"),
                stringsAsFactors = FALSE)
IMP <- IMP[IMP$donor_pool == paste("usable", IMP$axis, "cells"), ]   # axis-matched, per TSA

getp <- function(dom, axis) {
  z <- FL[FL$domain == dom & FL$axis == axis, ]
  if (nrow(z) && !z$degenerate[1])
    return(list(e1 = z$eps1[1], e0 = z$eps0[1],
                e1lo = z$eps1_lo[1], e1hi = z$eps1_hi[1],
                e0lo = z$eps0_lo[1], e0hi = z$eps0_hi[1], src = "measured"))
  y <- IMP[IMP$domain == dom & IMP$axis == axis, ]
  if (nrow(y)) {
    pool <- FL[FL$axis == axis & !FL$degenerate, ]
    d1 <- pool[which.max(pool$eps1), ]; d0 <- pool[which.max(pool$eps0), ]
    return(list(e1 = y$eps1_max[1], e0 = y$eps0_max[1],
                e1lo = d1$eps1_lo[1], e1hi = d1$eps1_hi[1],
                e0lo = d0$eps0_lo[1], e0hi = d0$eps0_hi[1], src = "imputed (max)"))
  }
  list(e1 = 0, e0 = 0, e1lo = NA, e1hi = NA, e0lo = NA, e0hi = NA,
       src = "not applicable")                          # structural: flag does not exist
}
PAR <- do.call(rbind, lapply(sort(unique(items$domain)), function(dm)
  do.call(rbind, lapply(c("VAL","REP"), function(ax) {
    p <- getp(dm, ax)
    data.frame(domain = dm, axis = ax, e1 = p$e1, e0 = p$e0,
               e1lo = p$e1lo, e1hi = p$e1hi, e0lo = p$e0lo, e0hi = p$e0hi,
               source = p$src, stringsAsFactors = FALSE) }))))
cat("\n=========== PARAMETERS APPLIED ===========\n")
cat("On the REP rows e1/e0 ARE delta_1/delta_0. Every REP row that is not structural\n")
cat("is MEASURED -- no imputation on this axis.\n\n")
print(PAR, row.names = FALSE, digits = 3)

stopifnot(all(PAR$source[PAR$axis == "REP"] %in% c("measured", "not applicable")))

draw_one <- function(pt, lo, hi) {
  if (is.na(lo) || is.na(hi) || pt <= 0 || pt >= 1) return(pt)
  lo <- max(lo, 1e-3); hi <- min(hi, 1 - 1e-3)
  if (hi <= lo) return(pt)
  ilgt(rnorm(1, lgt(pt), (lgt(hi) - lgt(lo)) / (2 * 1.96)))
}

###############################################################################
## 3.  One perturbed draw -- both axes jointly, never as two analyses
###############################################################################
perturb_once <- function(it, par, scale_e1 = 1, scale_e0 = 1) {
  st  <- it$state
  app <- st != "NA"
  isV <- st == "VAL"; isR <- st == "REP"
  mV <- match(paste(it$domain, "VAL"), paste(par$domain, par$axis))
  mR <- match(paste(it$domain, "REP"), paste(par$domain, par$axis))
  e1 <- par$e1[mV] * scale_e1; e0 <- par$e0[mV] * scale_e0
  d1 <- par$e1[mR] * scale_e1; d0 <- par$e0[mR] * scale_e0
  u  <- runif(length(st)); newV <- ifelse(isV, u  > e1, u  < e0) & app
  u2 <- runif(length(st)); newR <- ifelse(isR, u2 > d1, u2 < d0) & app
  it$state <- ifelse(!app, "NA", ifelse(newV, "VAL", ifelse(newR, "REP", "OK")))
  it
}

## both axes come out of a single roll-up, so the two curves are always the same draw
draw_stats_ref <- function(it) {                 # the readable version: roll_up(), as published
  a <- roll_up(it); a <- a[a$state != "NA", ]
  c(tapply(a$state == "VAL", a$domain, mean)[DOMS],
    tapply(a$state == "REP", a$domain, mean)[DOMS])
}

###############################################################################
##  FAST PATH. Same computation, ~500x less work per draw.
##
##  Four sweeps x 19 grid points x 500 draws + 2,000 bias-analysis draws is 40,000
##  roll-ups. Via roll_up() that is ~2 hours, nearly all of it spent rebuilding
##  things that do not change between draws: the item->cell grouping, the domain
##  of each cell, which items are applicable, and which carried a flag at
##  baseline. Perturbation always starts from the SAME baseline states, so all of
##  that is invariant and is computed once here.
##
##  What is left per draw: two runif() vectors, three tabulate() calls, and the
##  precedence. Equivalence to roll_up() is asserted below, not assumed.
###############################################################################
NALL  <- nrow(items)
pri   <- which(items$primary)
cell  <- factor(paste(items$PMID[pri], items$domain[pri]))
gi    <- as.integer(cell); G <- nlevels(cell)
cdom  <- items$domain[pri][match(levels(cell), paste(items$PMID[pri], items$domain[pri]))]
st0   <- items$state[pri]
app0  <- st0 != "NA"                       # N/A cells never move: no flag to be wrong about
isV0  <- st0 == "VAL"; isR0 <- st0 == "REP"
nApp  <- tabulate(gi[app0], nbins = G)     # applicability is fixed, so the denominator is too
dsel  <- lapply(DOMS, function(dm) cdom == dm & nApp > 0)
dn    <- vapply(dsel, sum, numeric(1))
pidx  <- list(V = match(paste(items$domain[pri], "VAL"), paste(PAR$domain, PAR$axis)),
              R = match(paste(items$domain[pri], "REP"), paste(PAR$domain, PAR$axis)))

draw_stats_fast <- function(par, scale_e1 = 1, scale_e0 = 1) {
  e1 <- par$e1[pidx$V] * scale_e1; e0 <- par$e0[pidx$V] * scale_e0
  d1 <- par$e1[pidx$R] * scale_e1; d0 <- par$e0[pidx$R] * scale_e0
  ## drawn over ALL items and then subset to the primary ones, not drawn over the
  ## primary ones directly: that keeps the random stream identical to perturb_once(),
  ## which is what makes the equivalence assertion below an exact test rather than a
  ## distributional one. Non-primary items never reach the roll-up.
  u  <- runif(NALL)[pri]; newV <- ifelse(isV0, u  > e1, u  < e0) & app0
  u2 <- runif(NALL)[pri]; newR <- ifelse(isR0, u2 > d1, u2 < d0) & app0
  nV <- tabulate(gi[newV], nbins = G)
  nR <- tabulate(gi[newR], nbins = G)
  cV <- nV > 0                       # weakest link: one flagged item flags the domain
  cR <- nV == 0 & nR > 0             # precedence: a validity flaw MASKS a reporting gap
  c(vapply(seq_along(DOMS), function(k) sum(cV[dsel[[k]]]) / dn[k], numeric(1)),
    vapply(seq_along(DOMS), function(k) sum(cR[dsel[[k]]]) / dn[k], numeric(1)))
}

## EQUIVALENCE ASSERTION. Same seed, same draw: the fast path must return exactly what
## roll_up() returns. Run at the parameters actually used and at an exaggerated setting,
## so that a precedence bug that only shows when both axes fire has somewhere to show.
for (tst in list(list(p = PAR, s1 = 1, s0 = 1), list(p = PAR, s1 = 0.6, s0 = 0.4))) {
  sd0 <- .Random.seed
  a <- draw_stats_fast(tst$p, tst$s1, tst$s0)
  assign(".Random.seed", sd0, envir = .GlobalEnv)      # same two runif() streams
  b <- draw_stats_ref(perturb_once(items, tst$p, tst$s1, tst$s0))
  stopifnot(length(a) == length(b), max(abs(a - unname(b))) < 1e-12)
}
cat("\n[fast draw engine reproduces roll_up() exactly on both axes]\n")

run_draws <- function(par, M, scale_e1 = 1, scale_e0 = 1) {
  out <- vapply(seq_len(M), function(i) draw_stats_fast(par, scale_e1, scale_e0),
                numeric(2 * length(DOMS)))
  rownames(out) <- c(paste0("VAL::", DOMS), paste0("REP::", DOMS))
  out
}
run_draws_prob <- function(par, M) {
  out <- vapply(seq_len(M), function(i) {
    p <- par
    for (k in seq_len(nrow(p))) {
      p$e1[k] <- draw_one(par$e1[k], par$e1lo[k], par$e1hi[k])
      p$e0[k] <- draw_one(par$e0[k], par$e0lo[k], par$e0hi[k])
    }
    draw_stats_fast(p)
  }, numeric(2 * length(DOMS)))
  rownames(out) <- c(paste0("VAL::", DOMS), paste0("REP::", DOMS))
  out
}

###############################################################################
## 4.  (1) CORRECTED PREVALENCES ON BOTH AXES -- probabilistic bias analysis
###############################################################################
cat("\n=========== (1) CORRECTED PREVALENCES, BOTH AXES ===========\n")
cat(sprintf("%d draws, parameters re-drawn from their intervals every draw.\n", M_DRAWS))
cat("Median and 2.5-97.5th percentile simulation intervals (Lash et al.).\n\n")
t0 <- Sys.time()
SP <- run_draws_prob(PAR, M_DRAWS)
cat(sprintf("[%.1f min]\n", as.numeric(difftime(Sys.time(), t0, units = "mins"))))

q <- function(S, p) apply(S, 1, quantile, p)
ADJ <- do.call(rbind, lapply(c("VAL", "REP"), function(ax) {
  r <- paste0(ax, "::", DOMS)
  data.frame(axis = ax, domain = DOMS,
             baseline = if (ax == "VAL") BASE$val_prevalence else BASE$rep_prevalence,
             median = apply(SP[r, , drop = FALSE], 1, median),
             lo = q(SP[r, , drop = FALSE], .025), hi = q(SP[r, , drop = FALSE], .975),
             param_source = PAR$source[match(paste(DOMS, ax), paste(PAR$domain, PAR$axis))],
             stringsAsFactors = FALSE)
}))
ADJ$shift <- ADJ$median - ADJ$baseline
ADJ$interval_contains_baseline <- ADJ$baseline >= ADJ$lo & ADJ$baseline <= ADJ$hi
print(ADJ, row.names = FALSE, digits = 3)
write.csv(ADJ, file.path(TBL, sprintf("%s_bias_analysis_both_axes.csv", STAMP)),
          row.names = FALSE)

## SELF-CHECK: the VAL half must reproduce the published 08_19 bias analysis. Different
## seed, so it is a tolerance check, not equality -- but a drift beyond 5 points would
## mean the refactored draw_stats() is not doing what run_draws_prob() did.
OLD <- read.csv(f("outputs/tables/08_19_2026_bias_analysis_corrected_prevalence.csv"),
                stringsAsFactors = FALSE)
chk <- merge(OLD[, c("domain","baseline","median")],
             ADJ[ADJ$axis == "VAL", c("domain","baseline","median")],
             by = "domain", suffixes = c("_0819", "_0820"))
chk$d_baseline <- chk$baseline_0820 - chk$baseline_0819
chk$d_median   <- chk$median_0820   - chk$median_0819
cat("\n--- self-check: validity axis vs the published 08_19 run ---\n")
print(chk, row.names = FALSE, digits = 3)
stopifnot(max(abs(chk$d_baseline)) < 1e-12)      # baseline is deterministic: must be exact
stopifnot(max(abs(chk$d_median))   < 0.05)       # medians: Monte Carlo drift only

###############################################################################
## 5.  (2) + (3) THE SWEEPS
##
##  epsilon_1  removes validity flaws   -> validity prevalence FALLS   (published)
##  epsilon_0  adds    validity flaws   -> validity prevalence RISES   <- new
##  delta_1    removes reporting gaps   -> reporting prevalence FALLS  <- new
##  delta_0    adds    reporting gaps   -> reporting prevalence RISES  <- new
##
##  Each sweep isolates ONE parameter: the other three are held at 0, which is what
##  makes the answer assumption-free ("X would have to exceed ... before ...").
##  Both axes are still read out of the same draw, because the precedence couples
##  them even when only one parameter moves.
###############################################################################
GRID <- seq(0, 0.9, by = 0.05)
unit <- function(axis, which) {                     # 1 on the target parameter, 0 elsewhere
  p <- PAR
  p$e1 <- 0; p$e0 <- 0
  hit <- p$axis == axis & p$source != "not applicable"
  p[[if (which == "e1") "e1" else "e0"]][hit] <- 1
  p
}
SWEEPS <- list(
  eps1  = list(par = unit("VAL","e1"), s = "e1",
               note = "epsilon_1: validity flaws removed (published sweep, re-run here for the REP read-out)"),
  eps0  = list(par = unit("VAL","e0"), s = "e0",
               note = "epsilon_0: spurious validity flaws added -- THE UPWARD DIRECTION"),
  delta1 = list(par = unit("REP","e1"), s = "e1",
               note = "delta_1: reporting gaps removed"),
  delta0 = list(par = unit("REP","e0"), s = "e0",
               note = "delta_0: spurious reporting gaps added")
)
cat("\n=========== (2)+(3) SWEEPS ===========\n")
cat(sprintf("%d draws per grid point, %d points, %d sweeps.\n",
            M_SWEEP, length(GRID), length(SWEEPS)))

SW <- do.call(rbind, lapply(names(SWEEPS), function(nm) {
  cfg <- SWEEPS[[nm]]; t1 <- Sys.time()
  cat(sprintf("  %-7s %s\n", nm, cfg$note))
  z <- do.call(rbind, lapply(GRID, function(g) {
    s <- run_draws(cfg$par, M_SWEEP,
                   scale_e1 = if (cfg$s == "e1") g else 0,
                   scale_e0 = if (cfg$s == "e0") g else 0)
    med <- apply(s, 1, median)
    data.frame(sweep = nm, parameter = cfg$s, value = g,
               domain = rep(DOMS, 2), axis = rep(c("VAL","REP"), each = length(DOMS)),
               prevalence = as.numeric(med), stringsAsFactors = FALSE)
  }))
  cat(sprintf("          [%.1f min]\n", as.numeric(difftime(Sys.time(), t1, units = "mins"))))
  z
}))
write.csv(SW, file.path(TBL, sprintf("%s_sweep_curves_both_axes.csv", STAMP)), row.names = FALSE)

###############################################################################
## 6.  Crossings over a FULL threshold ladder -- TSA picks the bar afterwards
###############################################################################
## ★ AUTHOR DECISION (TSA, 2026-08-20): **one ladder for every domain — 70 / 50 / 25%**,
## the same rungs already used for the high-prevalence domains in section 3. The
## alternative considered and rejected was a lower, domain-specific bar for the
## low-prevalence domains (30% for missing data, 40% for random error) on the grounds that
## "does missing data exceed 50%?" reads as a straw man. TSA chose consistency across
## domains instead. It costs nothing here: on the UPWARD sweep the standard rungs are all
## informative for the low-prevalence domains (missing data crosses 25% at eps0 = 0.04 and
## 50% at 0.24), which is exactly the direction those domains needed.
## The full 10-90% ladder is still written to the CSV, so a different bar can be read off
## without re-running anything.
HEADLINE <- c(.70, .50, .25)

## direction "down": the first grid point at which the curve falls BELOW thr
## direction "up"  : the first grid point at which it rises ABOVE thr
cross <- function(z, thr, direction) {
  z <- z[order(z$value), ]
  hit <- if (direction == "down") z$prevalence < thr else z$prevalence > thr
  i <- which(hit)[1]
  if (is.na(i)) return(NA_real_)
  if (i == 1)   return(0)                              # already past it at baseline
  x1 <- z$value[i-1]; x2 <- z$value[i]
  y1 <- z$prevalence[i-1]; y2 <- z$prevalence[i]
  if (y1 == y2) return(x2)
  x1 + (y1 - thr) / (y1 - y2) * (x2 - x1)              # linear interpolation
}
## 80 and 90 are on the ladder only because Confounding (79.9%) and Selection (76.8%)
## start above every other rung: without them the upward sweep has nothing to say about
## the two domains the manuscript leans on hardest.
LADDER <- c(.10, .15, .20, .25, .30, .40, .50, .60, .70, .80, .90)
DIRN   <- c(eps1 = "down", eps0 = "up", delta1 = "down", delta0 = "up")
READ   <- c(eps1 = "VAL",  eps0 = "VAL", delta1 = "REP", delta0 = "REP")

TP <- do.call(rbind, lapply(names(SWEEPS), function(nm) {
  ax <- READ[[nm]]; dr <- DIRN[[nm]]
  do.call(rbind, lapply(DOMS, function(dm) {
    z <- SW[SW$sweep == nm & SW$domain == dm & SW$axis == ax, ]
    b <- z$prevalence[z$value == 0]
    src <- PAR$source[PAR$domain == dm & PAR$axis == ax]
    data.frame(sweep = nm, parameter = SWEEPS[[nm]]$s, direction = dr, read_axis = ax,
               domain = dm, param_source = src, baseline = b,
               threshold = LADDER,
               crossing = vapply(LADDER, function(t) cross(z, t, dr), numeric(1)),
               ## a rung is informative only if it sits on the far side of the baseline
               ## AND the domain can produce this flag at all -- otherwise a structural
               ## zero (Mentioning errors on VAL, Confounding on REP) would advertise
               ## every rung as an unreachable finding
               informative = (if (dr == "down") LADDER < b else LADDER > b) &
                             src != "not applicable",
               stringsAsFactors = FALSE)
  }))
}))
write.csv(TP, file.path(TBL, sprintf("%s_tipping_point_ladder.csv", STAMP)), row.names = FALSE)

## SELF-CHECK: the epsilon_1 sweep is the PUBLISHED one, re-run here only so the
## reporting axis can be read out of the same draws. Its 70/50/25 crossings must
## reproduce 08_19_2026_tipping_point_thresholds.csv. This is the machinery check --
## if the four-way `unit()` construction were wrong, this is where it shows.
OTP <- read.csv(f("outputs/tables/08_19_2026_tipping_point_thresholds.csv"),
                stringsAsFactors = FALSE)
e1 <- TP[TP$sweep == "eps1" & TP$threshold %in% c(.70, .50, .25), ]
cmp <- do.call(rbind, lapply(seq_len(nrow(e1)), function(i) {
  o <- OTP[OTP$domain == e1$domain[i], ]
  old <- o[[c(`0.7` = "eps1_to_fall_below_70", `0.5` = "eps1_to_fall_below_50",
              `0.25` = "eps1_to_fall_below_25")[[as.character(e1$threshold[i])]]]]
  data.frame(domain = e1$domain[i], threshold = e1$threshold[i],
             published_0819 = old, rerun_0820 = e1$crossing[i],
             diff = e1$crossing[i] - old, stringsAsFactors = FALSE)
}))
cat("\n--- self-check: epsilon_1 crossings vs the published 08_19 sweep ---\n")
cat("(08_19 ran 2,000 draws per grid point, this runs 500 -- a small drift is expected)\n")
print(cmp[order(cmp$domain, -cmp$threshold), ], row.names = FALSE, digits = 3)
stopifnot(max(abs(cmp$diff), na.rm = TRUE) < 0.05)

###############################################################################
## 7.  Readable summary
###############################################################################
say <- function(x) if (is.na(x)) sprintf("never within %.2f", max(GRID)) else sprintf("%.2f", x)

cat("\n=========== (1) READ-OUT: the reporting axis, which never had one ===========\n")
cat("Four REP-capable domains, all with MEASURED delta. Structural cells are not shown:\n")
cat("Conflating task, Confounding bias and Measurement bias produce no reporting flag.\n\n")
for (dm in DOMS) {
  a <- ADJ[ADJ$axis == "REP" & ADJ$domain == dm, ]
  if (a$param_source == "not applicable" && a$baseline == 0) next
  cat(sprintf("%-18s baseline %5.1f%% -> corrected %5.1f%% [%.1f, %.1f]   (%s%s)\n",
              dm, 100*a$baseline, 100*a$median, 100*a$lo, 100*a$hi, a$param_source,
              if (a$interval_contains_baseline) ", interval CONTAINS the baseline" else ""))
}

cat("\n=========== (2) THE UPWARD DIRECTION: how high could validity flaws really be? ===========\n")
cat("epsilon_0 sweep, epsilon_1 = 0. The question for the LOW-prevalence domains.\n")
cat("Reported at the standard 70/50/25% rungs (TSA 2026-08-20: one ladder for every domain).\n\n")
for (dm in DOMS) {
  z <- TP[TP$sweep == "eps0" & TP$domain == dm, ]
  if (!nrow(z) || z$param_source[1] == "not applicable") next
  bars <- z[z$informative & z$threshold %in% HEADLINE, ]
  cat(sprintf("%-18s baseline %5.1f%%\n", dm, 100*z$baseline[1]))
  if (nrow(bars)) for (k in seq_len(nrow(bars)))
    cat(sprintf("%18s   exceeds %2.0f%% once eps0 > %s\n", "",
                100*bars$threshold[k], say(bars$crossing[k])))
}

cat("\n=========== (3) THE REPORTING TIPPING POINT ===========\n")
cat("delta_1 removes gaps (downward), delta_0 adds them (upward). For Mentioning errors\n")
cat("this is the ONLY tipping point that exists -- the domain produces no VAL flag.\n\n")
## The precedence puts a hard CEILING on the reporting axis: a paper carrying a validity
## flaw can never be counted as a reporting gap, so however large delta_0 grows, REP
## prevalence cannot pass 1 - (validity prevalence). Where a rung reads "never within
## 0.90" below, check this table first -- the rung may sit above the ceiling, in which
## case no value of delta_0 whatsoever reaches it and the sweep range is not the reason.
CEIL <- data.frame(domain = DOMS, val_prevalence = BASE$val_prevalence,
                   rep_ceiling = 1 - BASE$val_prevalence,
                   rep_baseline = BASE$rep_prevalence, stringsAsFactors = FALSE)
CEIL <- CEIL[CEIL$rep_ceiling < 1, ]
cat("structural ceiling on reporting-gap prevalence (delta_0 -> 1, epsilon_0 = 0):\n")
print(CEIL, row.names = FALSE, digits = 3)
cat("\n")
for (nm in c("delta1","delta0")) for (dm in DOMS) {
  z <- TP[TP$sweep == nm & TP$domain == dm, ]
  if (!nrow(z) || z$param_source[1] == "not applicable") next
  bars <- z[z$informative & z$threshold %in% HEADLINE, ]; if (!nrow(bars)) next
  cat(sprintf("%-7s %-18s baseline %5.1f%%\n", nm, dm, 100*z$baseline[1]))
  for (k in seq_len(nrow(bars)))
    cat(sprintf("%26s   %s %2.0f%% once %s %s %s\n", "",
                if (DIRN[[nm]] == "down") "falls below" else "exceeds",
                100*bars$threshold[k], if (nm == "delta1") "delta_1" else "delta_0",
                if (DIRN[[nm]] == "down") ">" else ">", say(bars$crossing[k])))
}

cat("\n=========== COUPLING CHECK: what epsilon_0 does to the REPORTING numbers ===========\n")
cat("No reporting parameter moves in this sweep. Any change is the precedence alone:\n")
cat("a spurious validity flaw MASKS a real reporting gap.\n\n")
cp <- SW[SW$sweep == "eps0" & SW$axis == "REP" & SW$value %in% c(0, 0.10, 0.30), ]
print(reshape(cp[, c("domain","value","prevalence")], idvar = "domain",
              timevar = "value", direction = "wide"), row.names = FALSE, digits = 3)

cat("\n★ THRESHOLDS: 70/50/25% for every domain (TSA, 2026-08-20). The full 10-90% ladder\n")
cat("  is still in outputs/tables/", STAMP, "_tipping_point_ladder.csv -- `informative`\n", sep = "")
cat("  marks the rows that sit on the far side of the baseline AND belong to a domain that\n")
cat("  can produce that flag at all, so another bar can be read off without a re-run.\n")
cat("\nwrote 3 tables to outputs/tables/\n")

###############################################################################
##  SECTION 3 -- BIAS ANALYSIS AND TIPPING POINT
##
##  Project : Assessment of Healthcare Research Quality in Saudi Arabia
##  Plan    : docs/SENSITIVITY_ANALYSIS_PLAN.md section 3
##  Date    : 2026-08-19
##  Run FROM THE REPOSITORY ROOT.
##
##  WHAT IT DOES
##  The published analysis assumes two agreeing reviewers are never both wrong,
##  i.e. epsilon_0 = epsilon_1 = delta_0 = delta_1 = 0. This relaxes that.
##    (a) BIAS ANALYSIS at the calibration-measured parameters -> corrected
##        domain prevalences with simulation intervals.
##    (b) TIPPING POINT -- sweep epsilon_1 and report the value at which each
##        conclusion changes. This needs NO parameter estimate at all and is the
##        primary output, because three domains (confounding among them) carry an
##        IMPUTED epsilon_1 rather than a measured one.
##
##  ⚠ THE TWO AXES MOVE TOGETHER IN ONE DRAW. The 4 states are mutually exclusive
##  and the roll-up is a precedence (VAL > REP > OK > NA), so removing a validity
##  flaw from a domain that also carries a reporting gap yields VAL -> REP, not
##  VAL -> OK. Perturbing the axes in separate analyses and combining afterwards
##  gives the wrong answer.
##
##  STATE MODEL, stated because it is an assumption:
##    1. perturb VAL membership with (epsilon_1, epsilon_0)
##    2. perturb REP membership with (delta_1, delta_0)
##    3. rebuild the state: VAL if val-flag, else REP if rep-flag, else OK.
##  N/A cells never move -- an inapplicable item has no flag to be wrong about.
###############################################################################

source("code/lib/score_dataset_lib.R")

PROJ  <- getwd(); STAMP <- "08_19_2026"
TBL   <- file.path(PROJ, "outputs", "tables"); stopifnot(dir.exists(TBL))
set.seed(20260819L)
M_DRAWS  <- 2000L      # bias analysis: tail percentiles need the draws (TSA, 2026-08-19)
M_SWEEP  <- 2000L      # sweep matched to the bias analysis (TSA, 2026-08-19). A median
                       # over ~4,800 cells converges long before this, and epsilon_1 is
                       # SET by the sweep rather than estimated, so there is no parameter
                       # uncertainty to propagate -- but the thresholds are the headline
                       # result, so they are not left resting on a convergence argument.
f <- function(p) file.path(PROJ, p)
lgt  <- function(p) log(p / (1 - p))
ilgt <- function(x) 1 / (1 + exp(-x))

###############################################################################
## 1.  Baseline
###############################################################################
d     <- read.csv(f("data/analysis/07_23_2026_ANALYSIS_DATASET_wide.csv"),
                  stringsAsFactors = FALSE, colClasses = "character", check.names = FALSE)
items <- score_items(d)
base_dom <- roll_up(items)

prev <- function(dom) {
  a <- dom[dom$state != "NA", ]
  do.call(rbind, lapply(split(a, a$domain), function(z) data.frame(
    domain = z$domain[1], applicable = nrow(z), val = sum(z$state == "VAL"),
    prevalence = mean(z$state == "VAL"), stringsAsFactors = FALSE)))
}
BASE <- prev(base_dom)
cat("=========== BASELINE (the published analysis: all parameters = 0) ===========\n")
print(BASE, row.names = FALSE, digits = 3)

###############################################################################
## 2.  Parameters, measured where possible and imputed where not
###############################################################################
FL  <- read.csv(f("outputs/tables/08_19_2026_calibration_flag_level_by_domain.csv"),
                stringsAsFactors = FALSE)
IMP <- read.csv(f("outputs/tables/08_19_2026_calibration_imputed_parameters.csv"),
                stringsAsFactors = FALSE)
IMP <- IMP[IMP$donor_pool == paste("usable", IMP$axis, "cells"), ]   # axis-matched, per TSA

## Each parameter carries its own paper-clustered interval, so the uncertainty in
## the PARAMETER can be propagated as well as the cell-level allocation. An imputed
## parameter inherits the interval of the donor it was borrowed from -- a floor on
## its uncertainty, not a fair estimate of it, since borrowing adds uncertainty
## that nothing here measures.
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

## Draw a parameter from its interval, normal on the LOGIT scale -- the family and
## the (logit hi - logit lo)/(2*1.96) spread are Lash et al.'s own recipe, applied
## here to a measured interval rather than an elicited one. It is centred on the
## point ESTIMATE rather than the interval midpoint, because unlike an elicited
## interval this one has a measurement at its centre.
## A parameter estimated as exactly 0 is held fixed: every bootstrap resample
## returned 0, so there is no spread to propagate.
draw_one <- function(pt, lo, hi) {
  if (is.na(lo) || is.na(hi) || pt <= 0 || pt >= 1) return(pt)
  lo <- max(lo, 1e-3); hi <- min(hi, 1 - 1e-3)
  if (hi <= lo) return(pt)
  ilgt(rnorm(1, lgt(pt), (lgt(hi) - lgt(lo)) / (2 * 1.96)))
}
cat("\n=========== PARAMETERS APPLIED ===========\n")
print(PAR, row.names = FALSE, digits = 3)

###############################################################################
## 3.  One perturbed draw
###############################################################################
perturb_once <- function(it, par, scale_e1 = 1, scale_e0 = 1) {
  st  <- it$state
  app <- st != "NA"
  isV <- st == "VAL"; isR <- st == "REP"
  e1 <- e0 <- d1 <- d0 <- numeric(length(st))
  mV <- match(paste(it$domain, "VAL"), paste(par$domain, par$axis))
  mR <- match(paste(it$domain, "REP"), paste(par$domain, par$axis))
  e1 <- par$e1[mV] * scale_e1; e0 <- par$e0[mV] * scale_e0
  d1 <- par$e1[mR] * scale_e1; d0 <- par$e0[mR] * scale_e0
  u <- runif(length(st))
  newV <- ifelse(isV, u > e1, u < e0) & app          # flip VAL membership
  u2 <- runif(length(st))
  newR <- ifelse(isR, u2 > d1, u2 < d0) & app        # flip REP membership
  it$state <- ifelse(!app, "NA", ifelse(newV, "VAL", ifelse(newR, "REP", "OK")))
  it
}

run_draws <- function(par, M, scale_e1 = 1, scale_e0 = 1) {
  out <- vapply(seq_len(M), function(i) {
    p <- prev(roll_up(perturb_once(items, par, scale_e1, scale_e0)))
    setNames(p$prevalence, p$domain)[BASE$domain]
  }, numeric(nrow(BASE)))
  if (is.null(dim(out))) out <- matrix(out, nrow = nrow(BASE))
  rownames(out) <- BASE$domain
  out
}

###############################################################################
## 4.  Bias analysis at the estimated parameters
###############################################################################
## PROBABILISTIC bias analysis: on every draw the parameters are themselves sampled
## from their intervals, so the simulation interval propagates BOTH the uncertainty
## in epsilon/delta and the cell-level allocation. This is what Lash et al. call
## probabilistic bias analysis; holding the parameters fixed gives an interval that
## is little more than Monte Carlo noise, because ~4,800 cells average the coin
## flips out almost completely.
run_draws_prob <- function(par, M) {
  out <- vapply(seq_len(M), function(i) {
    p <- par
    for (k in seq_len(nrow(p))) {
      p$e1[k] <- draw_one(par$e1[k], par$e1lo[k], par$e1hi[k])
      p$e0[k] <- draw_one(par$e0[k], par$e0lo[k], par$e0hi[k])
    }
    z <- prev(roll_up(perturb_once(items, p)))
    setNames(z$prevalence, z$domain)[BASE$domain]
  }, numeric(nrow(BASE)))
  rownames(out) <- BASE$domain
  out
}

cat("\n=========== (a) CORRECTED PREVALENCES ===========\n")
cat(sprintf("%d draws. Median and 2.5-97.5th percentile simulation intervals (Lash et al.).\n",
            M_DRAWS))
cat("PRIMARY = probabilistic: epsilon and delta re-drawn from their intervals each draw.\n")
cat("Shown beside it, the fixed-parameter interval -- the gap between them IS the\n")
cat("parameter uncertainty, which the fixed version omits entirely.\n\n")

SP <- run_draws_prob(PAR, M_DRAWS)
SF <- run_draws(PAR, M_DRAWS)
q <- function(S, p) apply(S, 1, quantile, p)
ADJ <- data.frame(domain = BASE$domain, baseline = BASE$prevalence,
                  median = apply(SP, 1, median), lo = q(SP, .025), hi = q(SP, .975),
                  fixed_median = apply(SF, 1, median),
                  fixed_lo = q(SF, .025), fixed_hi = q(SF, .975),
                  stringsAsFactors = FALSE)
ADJ$shift <- ADJ$median - ADJ$baseline
ADJ$width_prob  <- ADJ$hi - ADJ$lo
ADJ$width_fixed <- ADJ$fixed_hi - ADJ$fixed_lo
print(ADJ[, c("domain","baseline","median","lo","hi","shift")], row.names = FALSE, digits = 3)
cat("\ninterval width, probabilistic vs fixed-parameter:\n")
print(ADJ[, c("domain","width_prob","width_fixed")], row.names = FALSE, digits = 3)
write.csv(ADJ, file.path(TBL, sprintf("%s_bias_analysis_corrected_prevalence.csv", STAMP)),
          row.names = FALSE)

###############################################################################
## 5.  TIPPING POINT -- sweep epsilon_1 with epsilon_0 held at 0
##
##  epsilon_1 is the direction that threatens our conclusion: it REMOVES flaws.
##  Holding epsilon_0 at 0 isolates that threat and makes the answer assumption
##  free -- "epsilon_1 would have to exceed X before domain D falls below T".
###############################################################################
GRID <- seq(0, 0.9, by = 0.05)
UNIT <- transform(PAR, e1 = ifelse(source == "not applicable", 0, 1), e0 = 0)
cat("\n=========== (b) TIPPING POINT: sweeping epsilon_1, epsilon_0 = 0 ===========\n")
cat(sprintf("%d draws per grid point, %d points.\n", M_SWEEP, length(GRID)))
## The 200-draw thresholds from the first run, kept so the effect of the draw count
## on the headline numbers is visible rather than asserted.
PREV_RUN_200 <- c(`Confounding bias` = 0.126, `Selection bias` = 0.095,
                  `Measurement bias` = NA, `Conflating task` = NA)
SW <- do.call(rbind, lapply(GRID, function(g) {
  s <- run_draws(UNIT, M_SWEEP, scale_e1 = g, scale_e0 = 0)
  data.frame(eps1 = g, domain = BASE$domain, prevalence = apply(s, 1, median),
             stringsAsFactors = FALSE)
}))
write.csv(SW, file.path(TBL, sprintf("%s_tipping_point_sweep.csv", STAMP)), row.names = FALSE)

cross <- function(dm, thr) {
  z <- SW[SW$domain == dm, ]; z <- z[order(z$eps1), ]
  i <- which(z$prevalence < thr)[1]
  if (is.na(i)) return(NA_real_); if (i == 1) return(0)
  x1 <- z$eps1[i-1]; x2 <- z$eps1[i]; y1 <- z$prevalence[i-1]; y2 <- z$prevalence[i]
  x1 + (y1 - thr) / (y1 - y2) * (x2 - x1)                       # linear interpolation
}
TP <- do.call(rbind, lapply(BASE$domain, function(dm) data.frame(
  domain = dm, baseline = BASE$prevalence[BASE$domain == dm],
  eps1_to_fall_below_70 = cross(dm, .70), eps1_to_fall_below_50 = cross(dm, .50),
  eps1_to_fall_below_25 = cross(dm, .25), stringsAsFactors = FALSE)))
cat("\nepsilon_1 required for each domain's validity-flaw prevalence to fall below a threshold\n")
cat("(NA = never reached within the swept range; 0 = already below at baseline)\n\n")
print(TP, row.names = FALSE, digits = 3)
write.csv(TP, file.path(TBL, sprintf("%s_tipping_point_thresholds.csv", STAMP)), row.names = FALSE)

cat("\n--- did raising the sweep from 200 to", M_SWEEP, "draws move the headline thresholds? ---\n")
for (dm in names(PREV_RUN_200)) {
  old <- PREV_RUN_200[[dm]]; new <- TP$eps1_to_fall_below_70[TP$domain == dm]
  if (is.na(old) || !length(new) || is.na(new)) next
  cat(sprintf("  %-18s 70%% crossing: %.3f -> %.3f  (moved %.4f)\n", dm, old, new, new - old))
}

cat("\n=========== headline ===========\n")
cat("⚠ the sweep holds epsilon_0 = 0, so a threshold already met at baseline reports 0 and\n")
cat("  carries no information; only thresholds BELOW the baseline are quoted here.\n\n")
src_of <- function(dm) PAR$source[PAR$domain == dm & PAR$axis == "VAL"]
for (dm in BASE$domain) {
  b <- BASE$prevalence[BASE$domain == dm]; a <- ADJ[ADJ$domain == dm, ]
  if (b == 0) next
  thr <- c(`70%` = .70, `50%` = .50, `25%` = .25)
  thr <- thr[thr < b]
  tp  <- vapply(thr, function(t) cross(dm, t), numeric(1))
  cat(sprintf("%-18s baseline %5.1f%% -> corrected %5.1f%% [%.1f, %.1f]  (eps1 %s)\n",
              dm, 100*b, 100*a$median, 100*a$lo, 100*a$hi, src_of(dm)))
  if (length(thr)) cat(sprintf("%18s   falls below %s only if eps1 > %s\n", "",
              names(thr), ifelse(is.na(tp), "0.90 (not reached)", sprintf("%.2f", tp))),
              sep = "")
}
cat("\nwrote 3 tables to outputs/tables/\n")

###############################################################################
##  THE THREE INDICES BY GROUP, UNDER MISCLASSIFICATION -- the data behind the
##  sensitivity counterpart of FIGURE 6.
##
##  Project : Assessment of Healthcare Research Quality in Saudi Arabia
##  Plan    : docs/SENSITIVITY_ANALYSIS_PLAN.md section 3 / 3b, extended to the
##            stratified display at TSA's request (2026-08-29)
##  Run FROM THE REPOSITORY ROOT.
##
##  WHAT THIS ANSWERS
##  Figure 6 makes a HOMOGENEITY claim: across 25 groups within a task, the mean
##  validity, transparency and acknowledgement indices sit inside a narrow band.
##  The obvious reviewer objection is that reviewer misclassification manufactured
##  that homogeneity -- non-differential error blurs real between-group differences
##  toward each other, so groups that truly differ can be made to look alike.
##  ⚠ Non-differentiality is the condition under which that happens; it is NOT a
##  reason the stratified display is immune. This script measures how much of the
##  observed narrowness survives correcting for the measured error.
##
##  METHOD -- identical machinery to 08_20_2026_reporting_axis_and_upward.R
##  Item STATES are perturbed on both axes jointly in one draw (the four states are
##  mutually exclusive and the roll-up is a precedence, so they can never be moved
##  as two analyses), using the per-domain epsilon/delta measured from the
##  calibration rounds. Parameters are re-drawn from their bootstrap intervals on
##  every draw (logit-normal, Lash's spread formula) rather than held fixed: a
##  fixed-parameter run understates the interval 3-7x, because with ~4,800 cells
##  the coin flips average out and only Monte Carlo noise is left.
##
##  ⚠ GROUPS ARE READ, NEVER RE-DERIVED. The PMID -> (task, 10 stratifier levels)
##  map is taken verbatim from data/scoring/07_30_2026_stratified_paper_level.csv,
##  the file Figure 6 itself is built from, so the sensitivity display and the
##  figure it perturbs can never be grouping papers differently.
##
##  ⚠ THE COUNT-BASED INDICES ARE THE ONES PERTURBED. Figure 6 plots
##  mean_validity (not mean_validity_w), mean_transparency and mean_ack. The
##  library's own note says the count-based pair is "what prevalence, the domain
##  roll-up and the sensitivity analysis are built on"; the graded severities drive
##  the error score, which this analysis does not touch.
##
##  SELF-CHECKS (keep these passing)
##   1. the fast index engine reproduces study_indices() EXACTLY on the
##      unperturbed data, and again on three random perturbed draws;
##   2. the baseline group means reproduce 07_30_2026_stratified_summary.csv,
##      which is what Figure 6 prints.
##
##  OUTPUT (outputs/tables/)
##    08_29_2026_stratified_indices_perturbed.csv   group means, observed vs corrected
##    08_29_2026_stratified_spread_perturbed.csv    the homogeneity claim itself
###############################################################################

source("code/lib/score_dataset_lib.R")

PROJ  <- getwd(); STAMP <- "08_29_2026"
TBL   <- file.path(PROJ, "outputs", "tables"); stopifnot(dir.exists(TBL))
set.seed(20260829L)
## 2,000 is the reported run. SENS_DRAWS exists only so the self-checks can be
## exercised in seconds; anything written for the manuscript must be the default.
M_DRAWS <- as.integer(Sys.getenv("SENS_DRAWS", "2000"))
f    <- function(p) file.path(PROJ, p)
lgt  <- function(p) log(p / (1 - p))
ilgt <- function(x) 1 / (1 + exp(-x))

###############################################################################
## 1.  Score once, and read the groups
###############################################################################
d     <- read.csv(f("data/analysis/07_23_2026_ANALYSIS_DATASET_wide.csv"),
                  stringsAsFactors = FALSE, colClasses = "character", check.names = FALSE)
items <- score_items(d)
base_dom <- roll_up(items)
base_study <- study_indices(items, base_dom)

PL <- read.csv(f("data/scoring/07_30_2026_stratified_paper_level.csv"),
               stringsAsFactors = FALSE, check.names = FALSE)

## ⚠ THE GROUPS ARE FIGURE 6's, LEVEL FOR LEVEL AND IN ITS ORDER, so the sensitivity
## display is a like-for-like counterpart rather than a differently-cut version of the
## same data. Mirrors STRATS in code/figures/08_26_2026_fig6_indices_figure.py, including
## its exclusion of "JCR Q1-2 vs Q3-4" -- a coarsening of the quartile that the figure
## does not draw. 10 stratifiers, 25 levels.
STRATS <- list(
  "Saudi data used"        = c("Yes","No"),
  "Number of authors"      = c("1-2","3-10","11+"),
  "% Saudi authors"        = c(">=50%","<50%"),
  "Corresponding author"   = c("Saudi","Non-Saudi"),
  "First author"           = c("Saudi","Non-Saudi"),
  "Last author"            = c("Saudi","Non-Saudi"),
  "Sector composition"     = c("Academic-only","Health-system"),
  "Single vs multi-sector" = c("Single-sector","Multi-sector"),
  "JCR 2022 quartile"      = c("Q1","Q2","Q3","Q4","None"),
  "Funding"                = c("Funded","Declared none","Not stated"))
STRATIFIERS <- names(STRATS)
stopifnot(all(STRATIFIERS %in% names(PL)))
for (sf in STRATIFIERS) {
  have <- sort(unique(PL[[sf]][!is.na(PL[[sf]]) & nzchar(PL[[sf]])]))
  stopifnot(setequal(have, STRATS[[sf]]))          # no level silently added or dropped
}
NLEV <- sum(lengths(STRATS))
cat(sprintf("papers %d   stratifiers %d   levels %d (Figure 6 draws %d)\n",
            nrow(PL), length(STRATIFIERS), NLEV, 25L))
stopifnot(NLEV == 25L)

## papers in ONE fixed order everywhere below
PMIDS <- as.character(PL$PMID)
stopifnot(!anyDuplicated(PMIDS), setequal(PMIDS, as.character(base_study$PMID)))
TASK  <- setNames(PL$Study_Type, PMIDS)

###############################################################################
## 2.  Parameters -- same sourcing as section 3/3b, re-read not re-derived
###############################################################################
FL  <- read.csv(f("outputs/tables/08_19_2026_calibration_flag_level_by_domain.csv"),
                stringsAsFactors = FALSE)
IMP <- read.csv(f("outputs/tables/08_19_2026_calibration_imputed_parameters.csv"),
                stringsAsFactors = FALSE)
IMP <- IMP[IMP$donor_pool == paste("usable", IMP$axis, "cells"), ]   # axis-matched, per TSA

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
PAR <- do.call(rbind, lapply(sort(unique(items$domain)), function(dm)
  do.call(rbind, lapply(c("VAL","REP"), function(ax) {
    p <- getp(dm, ax)
    data.frame(domain = dm, axis = ax, e1 = p$e1, e0 = p$e0, e1lo = p$e1lo, e1hi = p$e1hi,
               e0lo = p$e0lo, e0hi = p$e0hi, source = p$src, stringsAsFactors = FALSE) }))))
cat("\n=========== PARAMETERS APPLIED ===========\n")
cat("On the REP rows e1/e0 ARE delta_1/delta_0. No imputation on the REP axis.\n\n")
print(PAR, row.names = FALSE, digits = 3)
stopifnot(all(PAR$source[PAR$axis == "REP"] %in% c("measured", "not applicable")))

draw_one <- function(pt, lo, hi) {
  if (is.na(lo) || is.na(hi) || pt <= 0 || pt >= 1) return(pt)
  lo <- max(lo, 1e-3); hi <- min(hi, 1 - 1e-3)
  if (hi <= lo) return(pt)
  ilgt(rnorm(1, lgt(pt), (lgt(hi) - lgt(lo)) / (2 * 1.96)))
}

perturb_once <- function(it, par) {
  st  <- it$state
  app <- st != "NA"
  isV <- st == "VAL"; isR <- st == "REP"
  mV <- match(paste(it$domain, "VAL"), paste(par$domain, par$axis))
  mR <- match(paste(it$domain, "REP"), paste(par$domain, par$axis))
  e1 <- par$e1[mV]; e0 <- par$e0[mV]; d1 <- par$e1[mR]; d0 <- par$e0[mR]
  u  <- runif(length(st)); newV <- ifelse(isV, u  > e1, u  < e0) & app
  u2 <- runif(length(st)); newR <- ifelse(isR, u2 > d1, u2 < d0) & app
  it$state <- ifelse(!app, "NA", ifelse(newV, "VAL", ifelse(newR, "REP", "OK")))
  it
}

###############################################################################
## 3.  Fast index engine
##
##  study_indices() splits 310 data frames and runs a per-paper scan for the
##  acknowledgement denominator; at 2,000 draws that is the whole run time. The
##  three indices Figure 6 plots are simple per-paper ratios, so they are computed
##  here with tabulate() over a fixed paper index. Everything invariant across
##  draws -- the paper index, which items are primary, the err_disc text and the
##  domains each paper NAMES -- is precomputed once.
###############################################################################
pri  <- items[items$primary, ]
pidx <- match(as.character(pri$PMID), PMIDS); stopifnot(!anyNA(pidx))
NP   <- length(PMIDS)
pdom <- pri$domain

MENTIONABLE <- c("Random error" = "random error", "Selection bias" = "selection bias",
                 "Measurement bias" = "measurement bias",
                 "Confounding bias" = "confounding bias", "Missing data" = "missing data")
ed     <- items[items$item == "err_disc", ]
ed_raw <- tolower(as.character(ed$raw)[match(PMIDS, as.character(ed$PMID))])
ed_raw[is.na(ed_raw)] <- ""
## NAMED[p, d] -- does paper p's discussion name mentionable domain d?  Constant.
NAMED <- vapply(MENTIONABLE, function(kw) grepl(kw, ed_raw, fixed = TRUE), logical(NP))
dimnames(NAMED) <- list(PMIDS, names(MENTIONABLE))

## domain index for the acknowledgement roll-up, over the five mentionable domains only
ment_ok <- pdom %in% names(MENTIONABLE)
midx    <- match(pdom[ment_ok], names(MENTIONABLE))
mpidx   <- pidx[ment_ok]
mcell   <- (midx - 1L) * NP + mpidx          # paper x mentionable-domain cell id

fast_indices <- function(st) {
  app <- st != "NA"; isV <- st == "VAL"; isR <- st == "REP"; judge <- isV | st == "OK"
  n_app   <- tabulate(pidx[app],   nbins = NP)
  n_rep   <- tabulate(pidx[isR],   nbins = NP)
  n_val   <- tabulate(pidx[isV],   nbins = NP)
  n_judge <- tabulate(pidx[judge], nbins = NP)
  ## a mentionable domain is flagged for a paper if ANY of its primary items is VAL
  flag <- matrix(tabulate(mcell[isV[ment_ok]], nbins = NP * length(MENTIONABLE)) > 0,
                 nrow = NP)
  n_flagged <- rowSums(flag)
  n_named   <- rowSums(flag & NAMED)
  list(transparency   = ifelse(n_app   > 0, 1 - n_rep / n_app,   NA_real_),
       validity       = ifelse(n_judge > 0, 1 - n_val / n_judge, NA_real_),
       acknowledgement = ifelse(n_flagged > 0, n_named / n_flagged, NA_real_))
}

## ---- self-check 1: the fast engine equals study_indices(), unperturbed and perturbed ----
chk <- function(it, lab) {
  ref <- study_indices(it, roll_up(it))
  ref <- ref[match(PMIDS, as.character(ref$PMID)), ]
  got <- fast_indices(it$state[it$primary])
  for (nmv in c("transparency","validity","acknowledgement")) {
    a <- ref[[nmv]]; b <- got[[nmv]]
    stopifnot(identical(is.na(a), is.na(b)))
    stopifnot(max(abs(a[!is.na(a)] - b[!is.na(b)])) < 1e-12)
  }
  cat(sprintf("  fast engine == study_indices()  [%s]\n", lab))
}
cat("\n--- self-check 1: fast index engine ---\n")
chk(items, "unperturbed")
for (b in 1:3) chk(perturb_once(items, PAR), sprintf("perturbed draw %d", b))

## ---- self-check 2: baseline group means reproduce the published Figure 6 inputs ----
IDX <- c(validity = "mean_validity", transparency = "mean_transparency",
         acknowledgement = "mean_ack")
group_means <- function(v3) {
  do.call(rbind, lapply(STRATIFIERS, function(sf) {
    lev <- PL[[sf]]
    do.call(rbind, lapply(names(IDX), function(ix) {
      x <- v3[[ix]]
      do.call(rbind, lapply(STRATS[[sf]], function(lv) {
        do.call(rbind, lapply(c("Causal","Descriptive"), function(tk) {
          sel <- lev == lv & PL$Study_Type == tk & !is.na(x)
          if (!any(sel)) return(NULL)
          data.frame(stratifier = sf, level = lv, task = tk, index = ix,
                     n = sum(sel), mean = mean(x[sel]), stringsAsFactors = FALSE)
        }))
      }))
    }))
  }))
}
BASE_G <- group_means(fast_indices(items$state[items$primary]))

SS <- read.csv(f("data/scoring/07_30_2026_stratified_summary.csv"),
               stringsAsFactors = FALSE, check.names = FALSE)
cat("\n--- self-check 2: baseline group means vs 07_30_2026_stratified_summary.csv ---\n")
nchk <- 0L; worst <- 0
for (i in seq_len(nrow(BASE_G))) {
  z <- SS[SS$stratifier == BASE_G$stratifier[i] & SS$level == BASE_G$level[i] &
          SS$task == BASE_G$task[i], ]
  if (!nrow(z)) next
  pubv <- z[[ IDX[[BASE_G$index[i]]] ]][1]
  if (is.na(pubv)) next
  worst <- max(worst, abs(pubv - BASE_G$mean[i])); nchk <- nchk + 1L
}
cat(sprintf("  %d group means checked, largest absolute difference %.3g\n", nchk, worst))
stopifnot(nchk > 100, worst < 1e-9)

###############################################################################
## 4.  The draws
###############################################################################
cat(sprintf("\n=========== %d PROBABILISTIC DRAWS ===========\n", M_DRAWS))
KEY <- paste(BASE_G$stratifier, BASE_G$level, BASE_G$task, BASE_G$index)
acc <- matrix(NA_real_, nrow = M_DRAWS, ncol = length(KEY))
t0 <- Sys.time()
for (b in seq_len(M_DRAWS)) {
  par <- PAR
  for (i in seq_len(nrow(par))) {
    par$e1[i] <- draw_one(par$e1[i], par$e1lo[i], par$e1hi[i])
    par$e0[i] <- draw_one(par$e0[i], par$e0lo[i], par$e0hi[i])
  }
  g <- group_means(fast_indices(perturb_once(items, par)$state[items$primary]))
  acc[b, ] <- g$mean[match(KEY, paste(g$stratifier, g$level, g$task, g$index))]
  if (b %% 250 == 0) cat(sprintf("  %4d/%d  (%.1f min elapsed)\n", b, M_DRAWS,
                                 as.numeric(difftime(Sys.time(), t0, units = "mins"))))
}

OUT <- BASE_G
OUT$observed  <- BASE_G$mean; OUT$mean <- NULL
OUT$corrected <- apply(acc, 2, median,   na.rm = TRUE)
OUT$lo        <- apply(acc, 2, quantile, .025, na.rm = TRUE)
OUT$hi        <- apply(acc, 2, quantile, .975, na.rm = TRUE)
OUT$shift     <- OUT$corrected - OUT$observed
OUT$interval_contains_observed <- OUT$lo <= OUT$observed & OUT$observed <= OUT$hi
write.csv(OUT, file.path(TBL, sprintf("%s_stratified_indices_perturbed.csv", STAMP)),
          row.names = FALSE)

###############################################################################
## 5.  The homogeneity claim itself -- the SPREAD across groups, per task
##
##  Figure 6's sentence is about how tightly the group means cluster, so the
##  quantity to correct is the spread, not any one mean. Corrected per draw and
##  summarised across draws, so the interval is on the spread itself.
###############################################################################
spread_of <- function(v) if (sum(!is.na(v)) < 2) NA_real_ else max(v, na.rm = TRUE) - min(v, na.rm = TRUE)

## ⚠ THE TASK-COMBINED ROW IS DIRECTLY STANDARDISED, NOT CRUDELY POOLED (TSA, 2026-08-29).
## The first version took the range over all 50 group means treated as 50 numbers. Most of
## that span is the gap BETWEEN tasks -- causal validity averages 0.485 against descriptive
## 0.432 -- not heterogeneity between groups, which is what the claim is about. Crude pooling
## is the operation Supplementary Figure S12 exists to remove, and the Methods say so in
## terms. So each group's two task means are weighted by the scored sample's own split, 229
## causal to 81 descriptive, and the spread is taken over the 25 standardised values.
## The crude version is still computed, and its distortion printed, so the difference between
## the two is a measured quantity rather than an assertion.
W_C <- sum(PL$Study_Type == "Causal") / nrow(PL)
W_D <- sum(PL$Study_Type == "Descriptive") / nrow(PL)
stopifnot(abs(W_C - 229 / 310) < 1e-12, abs(W_D - 81 / 310) < 1e-12)

std_by_group <- function(vals) {
  ## vals is one draw's vector over KEY; returns the 25 standardised means per index
  do.call(rbind, lapply(names(IDX), function(ix) {
    do.call(rbind, lapply(STRATIFIERS, function(sf) {
      do.call(rbind, lapply(STRATS[[sf]], function(lv) {
        gc <- vals[match(paste(sf, lv, "Causal", ix), KEY)]
        gd <- vals[match(paste(sf, lv, "Descriptive", ix), KEY)]
        data.frame(index = ix, key = paste(sf, lv),
                   m = W_C * gc + W_D * gd, stringsAsFactors = FALSE)
      }))
    }))
  }))
}
## ⚠ BOTH READINGS ARE COMPUTED. Figure 6's caption used to conflate them: it said "the 25
## group means of a task span only 0.14, 0.07 and 0.30", but those three numbers were the
## span of all FIFTY means, both tasks pooled. FIXED 2026-08-29 in
## code/figures/08_26_2026_fig6_indices_figure.py and in the legend: the caption now quotes
## the larger of the two task bands, 0.09 / 0.07 / 0.25, which is true of either task read
## alone. Per task the spans are 0.081 / 0.046 / 0.150 (causal) and 0.091 / 0.067 / 0.254
## (descriptive). The pooled row is kept so the discrepancy cannot be reintroduced silently.
## the standardised means, baseline and per draw
STD0 <- std_by_group(BASE_G$mean)
STD_DRAWS <- lapply(seq_len(M_DRAWS), function(b) std_by_group(acc[b, ]))

SPR <- do.call(rbind, lapply(names(IDX), function(ix) {
  do.call(rbind, lapply(c("Causal","Descriptive","Both (standardised)","Both (crude pooling)"),
                        function(tk) {
    if (tk == "Both (standardised)") {
      obs <- spread_of(STD0$m[STD0$index == ix])
      per_draw <- vapply(STD_DRAWS, function(z) spread_of(z$m[z$index == ix]), numeric(1))
      ng <- sum(STD0$index == ix)
    } else {
      sel <- BASE_G$index == ix & (tk == "Both (crude pooling)" | BASE_G$task == tk)
      if (sum(sel) < 2) return(NULL)
      obs <- spread_of(BASE_G$mean[sel])
      per_draw <- apply(acc[, sel, drop = FALSE], 1, spread_of)
      ng <- sum(sel)
    }
    data.frame(index = ix, task = tk, n_groups = ng,
               observed_spread = obs,
               corrected_spread = median(per_draw, na.rm = TRUE),
               lo = quantile(per_draw, .025, na.rm = TRUE),
               hi = quantile(per_draw, .975, na.rm = TRUE),
               stringsAsFactors = FALSE)
  }))
}))
row.names(SPR) <- NULL
write.csv(SPR, file.path(TBL, sprintf("%s_stratified_spread_perturbed.csv", STAMP)),
          row.names = FALSE)

cat("\n=========== SPREAD ACROSS GROUPS, observed vs corrected ===========\n")
cat("The homogeneity claim in one table. A corrected spread no larger than the\n")
cat("observed one means misclassification did not manufacture the narrowness.\n\n")
print(SPR, row.names = FALSE, digits = 3)

cat("\n=========== GROUP MEANS: how many intervals contain the observed value ===========\n")
print(table(OUT$index, OUT$interval_contains_observed))

cat(sprintf("\nwrote 2 tables to outputs/tables/ (%.1f min)\n",
            as.numeric(difftime(Sys.time(), t0, units = "mins"))))

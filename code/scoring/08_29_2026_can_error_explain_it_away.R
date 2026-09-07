###############################################################################
##  COULD REVIEWER ERROR EXPLAIN THE FINDINGS AWAY?
##
##  Project : Assessment of Healthcare Research Quality in Saudi Arabia
##  Date    : 2026-08-29 (TSA's question)
##  Run FROM THE REPOSITORY ROOT.
##
##  THE QUESTION, PUT PROPERLY
##  The domain-level sensitivity analysis answers "how far do the prevalences move".
##  It does not answer the objection a reviewer will actually raise, which is: your
##  reviewers agreed only 69% of the time, so maybe the literature is fine and you are
##  reading your own noise. That objection is about the HEADLINE claims, not about a
##  single domain:
##      (a) every one of the 310 scored studies carried at least one validity flaw;
##      (b) 229 (73.9%) were flawed in three or more domains;
##      (c) the mean validity index is 0.49 causal / 0.43 descriptive, far below 1.
##  If reviewer error could push (a) well below 100%, (b) toward zero and (c) toward 1,
##  the objection lands. This script measures whether it can.
##
##  TWO ANALYSES
##   1. PROBABILISTIC. The measured rates with their uncertainty, 2,000 draws. Reported
##      with the BEST DRAW as well as the median, because the question is not "what is
##      the expected value" but "how good could this literature be made to look".
##   2. A SWEEP that abandons the measured rates entirely and asks the assumption-free
##      question: how large would the concordant false-positive rate have to be before
##      each headline claim broke? Read against the 0.065-0.286 actually measured.
##
##  ⚠ THE SWEEP IS THE HONEST ANSWER, and it is one-sided in the sceptic's favour: eps0
##  is held at ZERO throughout, so reviewers are allowed to have invented flaws and never
##  to have missed one. Any real error process would be less favourable than this.
##
##  OUTPUT (outputs/tables/)
##    08_29_2026_explain_away_probabilistic.csv
##    08_29_2026_explain_away_sweep.csv
###############################################################################

source("code/lib/score_dataset_lib.R")

PROJ <- getwd(); STAMP <- "08_29_2026"
TBL  <- file.path(PROJ, "outputs", "tables"); stopifnot(dir.exists(TBL))
set.seed(20260829L)
M_DRAWS <- as.integer(Sys.getenv("SENS_DRAWS", "2000"))
M_SWEEP <- as.integer(Sys.getenv("SENS_SWEEP", "400"))
f    <- function(p) file.path(PROJ, p)
lgt  <- function(p) log(p / (1 - p))
ilgt <- function(x) 1 / (1 + exp(-x))

d     <- read.csv(f("data/analysis/07_23_2026_ANALYSIS_DATASET_wide.csv"),
                  stringsAsFactors = FALSE, colClasses = "character", check.names = FALSE)
items <- score_items(d)
base_dom <- roll_up(items)
base_st  <- study_indices(items, base_dom)

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
PAR <- do.call(rbind, lapply(DOMS_ORDER, function(dm)
  do.call(rbind, lapply(c("VAL","REP"), function(ax) {
    p <- getp(dm, ax)
    data.frame(domain = dm, axis = ax, e1 = p$e1, e0 = p$e0, e1lo = p$e1lo, e1hi = p$e1hi,
               e0lo = p$e0lo, e0hi = p$e0hi, source = p$src, stringsAsFactors = FALSE) }))))
draw_one <- function(pt, lo, hi) {
  if (is.na(lo) || is.na(hi) || pt <= 0 || pt >= 1) return(pt)
  lo <- max(lo, 1e-3); hi <- min(hi, 1 - 1e-3)
  if (hi <= lo) return(pt)
  ilgt(rnorm(1, lgt(pt), (lgt(hi) - lgt(lo)) / (2 * 1.96)))
}
perturb <- function(it, par, s1 = 1, s0 = 1) {
  st <- it$state; app <- st != "NA"; isV <- st == "VAL"; isR <- st == "REP"
  mV <- match(paste(it$domain, "VAL"), paste(par$domain, par$axis))
  mR <- match(paste(it$domain, "REP"), paste(par$domain, par$axis))
  u  <- runif(length(st))
  newV <- ifelse(isV, u  > par$e1[mV] * s1, u  < par$e0[mV] * s0) & app
  u2 <- runif(length(st))
  newR <- ifelse(isR, u2 > par$e1[mR] * s1, u2 < par$e0[mR] * s0) & app
  it$state <- ifelse(!app, "NA", ifelse(newV, "VAL", ifelse(newR, "REP", "OK")))
  it
}

###############################################################################
##  The five headline quantities, from one perturbed item table
###############################################################################
pri   <- items[items$primary, ]
PMIDS <- unique(as.character(pri$PMID)); NP <- length(PMIDS)
pidx  <- match(as.character(pri$PMID), PMIDS)
TASK  <- pri$Study_Type[match(PMIDS, as.character(pri$PMID))]
dcell <- factor(paste(pri$PMID, pri$domain))
dgi   <- as.integer(dcell); DG <- nlevels(dcell)
dpap  <- pidx[match(levels(dcell), paste(pri$PMID, pri$domain))]

headline <- function(st) {
  app <- st != "NA"; isV <- st == "VAL"; isR <- st == "REP"; judge <- isV | st == "OK"
  nV <- tabulate(dgi[isV], nbins = DG)
  domflag <- tabulate(dpap[nV > 0], nbins = NP)          # domains flagged per paper
  n_app <- tabulate(pidx[app], nbins = NP)
  n_rep <- tabulate(pidx[isR], nbins = NP)
  n_val <- tabulate(pidx[isV], nbins = NP)
  n_jud <- tabulate(pidx[judge], nbins = NP)
  c(pct_any_flaw   = mean(domflag >= 1),
    pct_ge3_domain = mean(domflag >= 3),
    mean_validity  = mean(ifelse(n_jud > 0, 1 - n_val / n_jud, NA), na.rm = TRUE),
    mean_transp    = mean(ifelse(n_app > 0, 1 - n_rep / n_app, NA), na.rm = TRUE),
    mean_domflag   = mean(domflag))
}

OBS <- headline(items$state[items$primary])
## the observed values must be the published ones
stopifnot(abs(OBS[["pct_any_flaw"]] - 1) < 1e-12,
          abs(OBS[["pct_ge3_domain"]] - mean(base_st$domains_flagged >= 3)) < 1e-12,
          abs(OBS[["mean_validity"]] - mean(base_st$validity, na.rm = TRUE)) < 1e-12)
cat("=========== OBSERVED (what the paper reports) ===========\n")
cat(sprintf("  studies with >=1 validity flaw   %.1f%%\n", 100 * OBS[["pct_any_flaw"]]))
cat(sprintf("  studies flawed in >=3 domains    %.1f%%\n", 100 * OBS[["pct_ge3_domain"]]))
cat(sprintf("  mean validity index              %.3f\n", OBS[["mean_validity"]]))
cat(sprintf("  mean transparency index          %.3f\n", OBS[["mean_transp"]]))
cat(sprintf("  mean domains flagged per paper   %.2f\n", OBS[["mean_domflag"]]))

###############################################################################
##  0. IS ANY ONE DOMAIN LOAD-BEARING?
##
##  The sweep below forces every domain to the same rate at once, which invites the
##  objection that the summary hides very different demands per domain: 0.79 is twelve
##  times the rate measured in measurement bias but under three times the rate measured
##  in selection bias. That objection only bites if the finding RESTS on one domain.
##  This tests it directly and without any perturbation at all: drop a domain from the
##  data entirely, as though it had never been assessed, and see what survives.
###############################################################################
dom0 <- base_dom[base_dom$state != "NA", ]
any_flaw <- function(excl = NULL, tk = NULL) {
  ## ⚠ NOT `dom0[is.null(excl) | dom0$domain != excl, ]`. With excl NULL that inner
  ## comparison is logical(0), the `|` returns logical(0), and the subset comes back
  ## EMPTY - so the baseline row printed NA instead of 100%. The dropped-domain rows
  ## were unaffected and are the ones the manuscript quotes.
  z <- if (is.null(excl)) dom0 else dom0[dom0$domain != excl, ]
  if (!is.null(tk)) z <- z[z$Study_Type == tk, ]
  p <- unique(z$PMID)
  mean(vapply(p, function(q) any(z$state[z$PMID == q] == "VAL"), logical(1)))
}
RED <- do.call(rbind, lapply(c(list(NULL), as.list(DOMS_ORDER)), function(ex)
  data.frame(dropped = if (is.null(ex)) "none" else ex,
             all_310 = any_flaw(ex), causal = any_flaw(ex, "Causal"),
             descriptive = any_flaw(ex, "Descriptive"), stringsAsFactors = FALSE)))
write.csv(RED, file.path(TBL, sprintf("%s_domain_redundancy.csv", STAMP)), row.names = FALSE)
cat("\n=========== (0) STUDIES WITH >=1 VALIDITY FLAW, DROPPING ONE DOMAIN ===========\n")
cat("No perturbation here. If one domain were load-bearing, dropping it would rescue the\n")
cat("literature. Dropping the largest one does not.\n\n")
print(RED, row.names = FALSE, digits = 3)

###############################################################################
##  1. PROBABILISTIC -- the measured rates and their uncertainty
###############################################################################
cat(sprintf("\n=========== (1) AT THE MEASURED RATES, %d draws ===========\n", M_DRAWS))
SP <- vapply(seq_len(M_DRAWS), function(i) {
  p <- PAR
  for (k in seq_len(nrow(p))) {
    p$e1[k] <- draw_one(PAR$e1[k], PAR$e1lo[k], PAR$e1hi[k])
    p$e0[k] <- draw_one(PAR$e0[k], PAR$e0lo[k], PAR$e0hi[k])
  }
  headline(perturb(items, p)$state[items$primary])
}, numeric(5))

PROB <- data.frame(quantity = rownames(SP), observed = OBS[rownames(SP)],
                   median = apply(SP, 1, median),
                   lo = apply(SP, 1, quantile, .025), hi = apply(SP, 1, quantile, .975),
                   best_draw = apply(SP, 1, function(v) NA), stringsAsFactors = FALSE)
## "best" = most favourable to the literature: fewer flaws, higher indices
PROB$best_draw <- c(min(SP[1, ]), min(SP[2, ]), max(SP[3, ]), max(SP[4, ]), min(SP[5, ]))
print(PROB, row.names = FALSE, digits = 3)
write.csv(PROB, file.path(TBL, sprintf("%s_explain_away_probabilistic.csv", STAMP)),
          row.names = FALSE)

###############################################################################
##  2. THE SWEEP -- abandon the measured rates; eps0 = 0 throughout
###############################################################################
GRID <- c(seq(0, 0.9, by = 0.05), 0.95, 0.99)
cat(sprintf("\n=========== (2) SWEEP: eps1 forced to g on EVERY domain, eps0 = 0, %d draws ===========\n",
            M_SWEEP))
cat("eps0 = 0 means reviewers may have invented flaws but never missed one: one-sided,\n")
cat("in the sceptic's favour, and still not enough. delta axis left at its measured values.\n\n")
SW <- do.call(rbind, lapply(GRID, function(g) {
  p <- PAR
  p$e1[p$axis == "VAL" & p$source != "not applicable"] <- g
  p$e0[p$axis == "VAL"] <- 0
  M <- vapply(seq_len(M_SWEEP), function(i) headline(perturb(items, p)$state[items$primary]),
              numeric(5))
  data.frame(eps1 = g, quantity = rownames(M), median = apply(M, 1, median),
             stringsAsFactors = FALSE)
}))
write.csv(SW, file.path(TBL, sprintf("%s_explain_away_sweep.csv", STAMP)), row.names = FALSE)

## ⚠ these quantities are stored as PROPORTIONS; `pct = TRUE` is what scales them for
## display. The first version passed "%.1f%%" as a format string instead, so 1.000 printed
## as "1.0%" where it means 100%. The stored CSV was never wrong, only the console.
sh <- function(qn, lab, pct = FALSE) {
  z <- SW[SW$quantity == qn, ]
  cat(sprintf("\n  %s\n", lab))
  for (g in c(0, 0.1, 0.2, 0.286, 0.4, 0.6, 0.8, 0.95, 0.99)) {
    i <- which.min(abs(z$eps1 - g))
    v <- z$median[i]
    cat(sprintf("     eps1 = %.3f  ->  %s\n", z$eps1[i],
                if (pct) sprintf("%5.1f%%", 100 * v) else sprintf("%.3f", v)))
  }
}
sh("pct_any_flaw",   "studies with >=1 validity flaw", pct = TRUE)
sh("pct_ge3_domain", "studies flawed in >=3 domains",  pct = TRUE)
sh("mean_validity",  "mean validity index (1 = no flaws at all)")

cat("\n=========== WHAT IT WOULD TAKE ===========\n")
need <- function(qn, thr, dir) {
  z <- SW[SW$quantity == qn, ]; z <- z[order(z$eps1), ]
  hit <- if (dir == "down") z$median < thr else z$median > thr
  i <- which(hit)[1]
  if (is.na(i)) return(NA_real_)
  if (i == 1) return(0)
  x1 <- z$eps1[i-1]; x2 <- z$eps1[i]; y1 <- z$median[i-1]; y2 <- z$median[i]
  x1 + (y1 - thr) / (y1 - y2) * (x2 - x1)
}
say <- function(v) if (is.na(v)) "NEVER, even at 0.99" else sprintf("eps1 > %.2f", v)
cat(sprintf("  to bring '>=1 flaw' below 90%%          : %s\n", say(need("pct_any_flaw", .90, "down"))))
cat(sprintf("  to bring '>=1 flaw' below 50%%          : %s\n", say(need("pct_any_flaw", .50, "down"))))
cat(sprintf("  to bring '>=3 domains' below 25%%       : %s\n", say(need("pct_ge3_domain", .25, "down"))))
cat(sprintf("  to raise mean validity above 0.75      : %s\n", say(need("mean_validity", .75, "up"))))
cat(sprintf("  to raise mean validity above 0.90      : %s\n", say(need("mean_validity", .90, "up"))))
## The crossings, written out so the figure READS them rather than re-deriving them.
## ⚠ mean validity moves UP under this sweep, so its rungs are 0.75 and 0.90, not 70/50/25.
THR <- do.call(rbind, lapply(
  list(list(q = "pct_any_flaw",   lab = "At least one validity flaw"),
       list(q = "pct_ge3_domain", lab = "Flawed in three or more domains")),
  function(z) data.frame(
    quantity = z$q, label = z$lab, observed = OBS[[z$q]],
    e1_to_fall_below_70 = need(z$q, .70, "down"),
    e1_to_fall_below_50 = need(z$q, .50, "down"),
    e1_to_fall_below_25 = need(z$q, .25, "down"),
    stringsAsFactors = FALSE)))
THR <- rbind(THR, data.frame(
  quantity = "mean_validity", label = "Mean validity index",
  observed = OBS[["mean_validity"]],
  e1_to_fall_below_70 = need("mean_validity", .75, "up"),   # reused columns: 0.75 rung
  e1_to_fall_below_50 = need("mean_validity", .90, "up"),   # 0.90 rung
  e1_to_fall_below_25 = NA_real_, stringsAsFactors = FALSE))
write.csv(THR, file.path(TBL, sprintf("%s_explain_away_thresholds.csv", STAMP)),
          row.names = FALSE)
print(THR, row.names = FALSE, digits = 3)

cat("\nMeasured concordant false-positive rates: 0.000 to 0.286 (imputed cells take 0.286).\n")
cat("wrote 3 tables to outputs/tables/\n")

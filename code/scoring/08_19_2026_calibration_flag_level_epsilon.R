###############################################################################
##  FLAG-LEVEL epsilon and delta, measured from the calibration rounds
##
##  Project : Assessment of Healthcare Research Quality in Saudi Arabia
##  Plan    : docs/SENSITIVITY_ANALYSIS_PLAN.md section 3
##  Date    : 2026-08-19
##  Run FROM THE REPOSITORY ROOT.
##
##  WHY THIS EXISTS
##  08_19_2026_calibration_concordant_error.R measures how often two agreeing
##  reviewers give the same WRONG ANSWER. The bias parameters are not defined on
##  answers, they are defined on the scored FLAGS:
##      epsilon_1 = P(no true VAL | both reviewers scored VAL)
##      epsilon_0 = P(true VAL    | both reviewers scored non-VAL)
##      delta_1   = P(no true REP | both reviewers scored REP)
##      delta_0   = P(true REP    | both reviewers scored non-REP)
##  Many different answers collapse onto one flag (base_conf_meth's ten methods
##  all mean "adjustment was done" -> OK), so the two rates are NOT the same and
##  neither dominates the other a priori: dropping the items that produce no flag
##  pushes the rate UP, the answer-to-flag collapse pushes it DOWN.
##
##  METHOD
##  Score every reviewer's calibration answers, and the TSA+YA adjudicated
##  reference, through the SAME scorer used on the main dataset
##  (code/lib/score_dataset_lib.R). Then, per (paper, item), form all reviewer
##  pairs that produced the SAME flag and check that flag against the reference.
##  Clustered on papers; intervals bootstrapped over papers.
##
##  SETTLED DECISIONS (TSA, 2026-08-19)
##   * reviewer 3 excluded (quit); "new reviewer 5" canonical.
##   * Sourcing rule: a variable stable across rounds is measured on round 1;
##     a variable changed at round 2 is measured on round 2 only.
##   * descriptive_val_outcome takes causal_val_outcome's round-2 rate as a proxy.
###############################################################################

suppressPackageStartupMessages({ library(readxl) })
source("code/lib/score_dataset_lib.R")

PROJ  <- getwd(); STAMP <- "08_19_2026"
TBL   <- file.path(PROJ, "outputs", "tables"); stopifnot(dir.exists(TBL))
set.seed(20260819L); B_BOOT <- 2000L
f  <- function(p) file.path(PROJ, p)
rd <- function(p) as.data.frame(suppressMessages(read_excel(f(p), sheet = 1, col_types = "text")))
base_nm <- function(x) sub("[.][0-9]+$", "", sub("[.][.][.][0-9]+$", "", x))
keyof   <- function(nm) { b <- base_nm(nm); paste0(b, "##", ave(b, b, FUN = seq_along)) }
DROP_REVIEWERS <- "3"

XW  <- read.csv(f("outputs/tables/08_19_2026_calibration_crosswalk.csv"), stringsAsFactors = FALSE)
SRC <- read.csv(f("outputs/tables/08_19_2026_calibration_parameter_source.csv"), stringsAsFactors = FALSE)

###############################################################################
## 1.  Build a WIDE frame (the shape score_items() expects) per rater
###############################################################################
## ⚠ TWO GATE QUESTIONS EXIST IN THE FINAL TOOL BUT NOT IN CALIBRATION, and the
## scorer needs them or whole item families silently score as N/A:
##   `follow`       gates ltfu_bias and ltfu_acc. Calibration asks about loss to
##                  follow-up directly, with no gate, so follow-up is implied
##                  wherever the LTFU question was answered at all.
##   `time_verying` gates tv_conf_meth. Calibration folds it into one question
##                  whose "No time-varying effect estimated" answer IS the gate.
## Both reconstructions are recorded here rather than buried, because they are
## assumptions, not data.
RECON_FOLLOW <- "answered LTFU question => follow = Yes"
RECON_TVY    <- "'No time-varying effect estimated' => time_verying = No, else Yes"

build_wide <- function(rows, xw, task_by_pmid) {
  out <- data.frame(PMID = rows[[2]], Study_Type = unname(task_by_pmid[rows[[2]]]),
                    stringsAsFactors = FALSE)
  m <- xw[xw$status != "dropped" & !grepl("^NA_", xw$variable), ]
  for (i in seq_len(nrow(m))) out[[m$variable[i]]] <- trimws(rows[[m$col[i]]])
  ## reconstruct the two gates
  lb <- out[["causal_ltfu_bias"]]
  out[["causal_follow"]] <- ifelse(!is.na(lb) & nzchar(lb), "Yes", NA_character_)
  tvcol <- xw$col[xw$variable == "causal_time_verying"]
  if (length(tvcol)) {
    tv <- trimws(rows[[tvcol]])
    out[["causal_time_verying"]] <- ifelse(is.na(tv) | !nzchar(tv), NA_character_,
      ifelse(grepl("no time-varying effect", tolower(tv)), "No", "Yes"))
  }
  out
}

score_round <- function(rev_rows, adj_rows, xw, label) {
  ## the adjudicated task is used for EVERY rater, so all are scored on the same
  ## branch of the instrument. Safe here: reviewers agreed on task in ~100% of
  ## pairs (1 discordant pair in 746 in round 1), asserted below.
  task_by_pmid <- setNames(trimws(adj_rows[[xw$col[xw$variable == "task"]]]), adj_rows[[2]])
  tv <- trimws(rev_rows[[xw$col[xw$variable == "task"]]])
  agree_task <- mean(tv == unname(task_by_pmid[rev_rows[[2]]]), na.rm = TRUE)
  cat(sprintf("[%s] reviewer-vs-reference task agreement %.1f%%\n", label, 100 * agree_task))
  stopifnot(agree_task > 0.95)

  ref <- score_items(build_wide(adj_rows, xw, task_by_pmid))
  ref$key <- paste(ref$PMID, ref$item)

  rids <- setdiff(unique(rev_rows[[1]]), DROP_REVIEWERS)
  per <- lapply(rids, function(r) {
    s <- score_items(build_wide(rev_rows[rev_rows[[1]] == r, ], xw, task_by_pmid))
    s$rid <- r; s$key <- paste(s$PMID, s$item); s
  })
  list(ref = ref, rev = do.call(rbind, per), rids = rids)
}

###############################################################################
## 2.  Agreeing-pair rates on each FLAG
###############################################################################
## A cell enters only where the rater AND the reference both found the item
## applicable (state != "NA"); an inapplicable item has no flag to be wrong about.
flag_rates <- function(sc, axis_flag) {
  ref <- sc$ref[sc$ref$state != "NA", ]
  rev <- sc$rev[sc$rev$state != "NA", ]
  refflag <- setNames(ref$state == axis_flag, ref$key)
  out <- list()
  for (k in unique(rev$key)) {
    if (is.na(refflag[k])) next
    z <- rev[rev$key == k, ]
    if (nrow(z) < 2) next
    fl <- z$state == axis_flag
    n1 <- sum(fl); n0 <- sum(!fl)
    pairs_1 <- n1 * (n1 - 1) / 2          # both flagged
    pairs_0 <- n0 * (n0 - 1) / 2          # both not flagged
    out[[length(out) + 1L]] <- data.frame(
      PMID = z$PMID[1], Study_Type = z$Study_Type[1], item = z$item[1],
      domain = z$domain[1],
      ref_flag = refflag[[k]],
      pairs_both_flag = pairs_1, wrong_both_flag = if (refflag[[k]]) 0 else pairs_1,
      pairs_both_noflag = pairs_0, wrong_both_noflag = if (refflag[[k]]) pairs_0 else 0,
      stringsAsFactors = FALSE)
  }
  d <- do.call(rbind, out)
  d$variable <- paste0(ifelse(d$Study_Type == "Causal", "causal_", "descriptive_"), d$item)
  d
}

###############################################################################
## 3.  Run both rounds
###############################################################################
X1 <- XW[XW$round == 1, ]; X2 <- XW[XW$round == 2, ]

r1 <- rd("data/calibration/round-1/Reviewer and adjudication answers with new revierwer 5.xlsx")
r1 <- r1[, setdiff(names(r1), "Title")]
a1 <- rd("data/calibration/round-1/2024_05_04_Adjudication_of_calibration.xlsx")
k1r <- keyof(names(r1)); k1a <- keyof(names(a1)); stopifnot(setequal(k1r, k1a))
a1 <- a1[, match(k1r, k1a)]                     # realign: the exports transpose two columns
sc1 <- score_round(r1[r1[[1]] != "Adjudicated", ], a1, X1, "round 1")

p2 <- read.csv(f("data/calibration/round-2/2024_11_26_Progress_round_2.csv"),
               colClasses = "character", check.names = FALSE)
p2 <- p2[order(as.POSIXct(sub(" GMT.*$", "", p2$Timestamp), format = "%Y/%m/%d %I:%M:%S %p",
                          tz = "UTC"), decreasing = TRUE), ]
p2 <- p2[!duplicated(paste(p2[[2]], p2[[3]])), ][, -1]   # keep the NEW reviewer 5
a2 <- rd("data/calibration/round-2/2024_07_13_Adjudication_of_calibration_round_2.xlsx")
k2r <- keyof(names(p2)); k2a <- keyof(names(a2)); stopifnot(setequal(k2r, k2a))
a2 <- a2[, match(k2r, k2a)]
sc2 <- score_round(p2, a2, X2, "round 2")

###############################################################################
## 4.  epsilon (VAL axis) and delta (REP axis), under the sourcing rule
###############################################################################
collect <- function(sc, axis) { d <- flag_rates(sc, axis); d$axis <- axis; d }
D1 <- rbind(collect(sc1, "VAL"), collect(sc1, "REP")); D1$round <- 1L
D2 <- rbind(collect(sc2, "VAL"), collect(sc2, "REP")); D2$round <- 2L
DD <- rbind(D1, D2)

## sourcing rule: each variable is measured in exactly one round
src_round <- setNames(SRC$source_round, SRC$variable)
src_round[SRC$variable[SRC$is_proxy == "TRUE" | SRC$is_proxy == TRUE]] <- NA  # proxies handled after
DD <- DD[!is.na(src_round[DD$variable]) & DD$round == src_round[DD$variable], ]

## ⚠ THE REFERENCE HAS TO VARY OR NEITHER PARAMETER IS ESTIMABLE.
## eps1 can only be estimated on cells the reference did NOT flag; eps0 only on
## cells it DID. If every calibration cell in a domain carries the same reference
## state, one of the two is undefined and the other is 1.0 or 0.0 by construction,
## not by measurement. `ref_flag_rate` exposes that, and `degenerate` marks it.
## A domain can also legitimately draw its variables from BOTH rounds under the
## sourcing rule, so `rounds` and `papers` are reported as the union, not a single
## round -- 13 papers means 10 from round 1 plus 3 from round 2, not a pairing bug.
agg <- function(d, by) {
  do.call(rbind, lapply(split(d, d[by]), function(z) {
    if (!nrow(z)) return(NULL)
    rf <- mean(z$ref_flag)
    data.frame(setNames(list(z[[by]][1]), by),
      axis = z$axis[1],
      rounds = paste(sort(unique(z$round)), collapse = "+"),
      papers = length(unique(z$PMID)),
      ref_flag_rate = rf,
      degenerate = rf == 0 | rf == 1,
      n_pairs_flag   = sum(z$pairs_both_flag),   n_wrong_flag   = sum(z$wrong_both_flag),
      n_pairs_noflag = sum(z$pairs_both_noflag), n_wrong_noflag = sum(z$wrong_both_noflag),
      eps1 = ifelse(sum(z$pairs_both_flag) > 0, sum(z$wrong_both_flag) / sum(z$pairs_both_flag), NA),
      eps0 = ifelse(sum(z$pairs_both_noflag) > 0, sum(z$wrong_both_noflag) / sum(z$pairs_both_noflag), NA),
      stringsAsFactors = FALSE)
  }))
}
BY_DOM <- do.call(rbind, lapply(split(DD, DD$axis), function(z) agg(z, "domain")))
BY_VAR <- do.call(rbind, lapply(split(DD, DD$axis), function(z) agg(z, "variable")))

nm <- function(d) { d$param_hi <- ifelse(d$axis == "VAL", "epsilon_1", "delta_1")
                    d$param_lo <- ifelse(d$axis == "VAL", "epsilon_0", "delta_0"); d }
BY_DOM <- nm(BY_DOM); BY_VAR <- nm(BY_VAR)

## paper-clustered bootstrap. Pairs within a paper are not independent (13
## reviewers give 78 pairs off 13 judgements), so papers are the resampling unit.
## With 5-13 papers these intervals are wide, and that width is the finding.
boot_ci <- function(z, num, den) {
  pm <- unique(z$PMID)
  if (length(pm) < 3) return(c(NA_real_, NA_real_))
  v <- vapply(seq_len(B_BOOT), function(b) {
    idx <- unlist(lapply(sample(pm, length(pm), replace = TRUE), function(p) which(z$PMID == p)))
    d <- sum(z[[den]][idx]); if (d == 0) return(NA_real_)
    sum(z[[num]][idx]) / d
  }, numeric(1))
  v <- v[is.finite(v)]
  if (length(v) < B_BOOT / 10) return(c(NA_real_, NA_real_))
  unname(quantile(v, c(.025, .975)))
}
add_ci <- function(tab, by) {
  ci1 <- ci0 <- matrix(NA_real_, nrow(tab), 2)
  for (i in seq_len(nrow(tab))) {
    z <- DD[DD$axis == tab$axis[i] & DD[[by]] == tab[[by]][i], ]
    ci1[i, ] <- boot_ci(z, "wrong_both_flag",   "pairs_both_flag")
    ci0[i, ] <- boot_ci(z, "wrong_both_noflag", "pairs_both_noflag")
  }
  tab$eps1_lo <- ci1[, 1]; tab$eps1_hi <- ci1[, 2]
  tab$eps0_lo <- ci0[, 1]; tab$eps0_hi <- ci0[, 2]
  tab
}
BY_DOM <- add_ci(BY_DOM, "domain"); BY_VAR <- add_ci(BY_VAR, "variable")

write.csv(BY_DOM, file.path(TBL, sprintf("%s_calibration_flag_level_by_domain.csv", STAMP)), row.names = FALSE)
write.csv(BY_VAR, file.path(TBL, sprintf("%s_calibration_flag_level_by_variable.csv", STAMP)), row.names = FALSE)

cat("\n=========== FLAG-LEVEL PARAMETERS BY DOMAIN ===========\n")
cat("eps1/delta1 = P(reference says NO flag | both reviewers flagged)\n")
cat("eps0/delta0 = P(reference says flag    | neither reviewer flagged)\n\n")
for (ax in c("VAL","REP")) {
  z <- BY_DOM[BY_DOM$axis == ax, ]
  if (!nrow(z)) next
  cat(sprintf("---- %s axis (%s / %s)\n", ax, z$param_hi[1], z$param_lo[1]))
  print(z[, c("domain","rounds","papers","ref_flag_rate","degenerate",
              "n_pairs_flag","n_wrong_flag","eps1",
              "n_pairs_noflag","n_wrong_noflag","eps0")], row.names = FALSE, digits = 2)
}
deg <- BY_DOM[BY_DOM$degenerate, ]
cat(sprintf("\n⚠ %d of %d domain-axis cells are DEGENERATE: the reference never varies,\n",
            nrow(deg), nrow(BY_DOM)))
cat("  so one parameter is undefined and the other is 0 or 1 by construction, not by\n")
cat("  measurement. These are NOT usable estimates:\n")
if (nrow(deg)) for (i in seq_len(nrow(deg)))
  cat(sprintf("    %-18s %s  reference flagged %.0f%% of cells\n",
              deg$domain[i], deg$axis[i], 100 * deg$ref_flag_rate[i]))
usable <- BY_DOM[!BY_DOM$degenerate, ]
cat(sprintf("\n✅ %d usable domain-axis cells, with paper-clustered 95%% intervals:\n", nrow(usable)))
if (nrow(usable)) {
  u <- usable[order(usable$axis, -usable$eps1), ]
  cat(sprintf("  %-18s %-4s %6s   %-22s   %-22s\n", "domain", "axis", "papers",
              "eps1 / delta1 (95% CI)", "eps0 / delta0 (95% CI)"))
  for (i in seq_len(nrow(u))) {
    ci <- function(v, lo, hi) if (is.na(v)) "        n/a           " else
      sprintf("%.3f [%s, %s]", v,
              if (is.na(lo)) "  . " else sprintf("%.3f", lo),
              if (is.na(hi)) "  . " else sprintf("%.3f", hi))
    cat(sprintf("  %-18s %-4s %6d   %-22s   %-22s\n", u$domain[i], u$axis[i], u$papers[i],
                ci(u$eps1[i], u$eps1_lo[i], u$eps1_hi[i]),
                ci(u$eps0[i], u$eps0_lo[i], u$eps0_hi[i])))
  }
}
###############################################################################
## 5.  IMPUTATION for the degenerate-but-real cells (TSA, 2026-08-19)
##
##  Three domain-axis cells are VAL-capable in the final instrument but cannot be
##  estimated from calibration, because the reference never varies there:
##    Conflating task VAL  - all 5 descriptive calibration papers conflated the task
##    Confounding bias VAL - all 3 round-2 papers carry a confounding flaw
##    Missing data VAL     - no calibration paper has a missing-data validity flaw
##  TSA ruled they must still be assigned a value: the HIGHEST of the measured
##  cells, with the average reported as the alternative.
##
##  The other four degenerate cells are NOT imputed: the domain produces no such
##  flag at all in the final instrument, so the parameter does not exist.
##  (VAL-capable: Random error, Selection bias, Measurement bias, Confounding bias,
##   Missing data, Conflating task. REP-capable: Random error, Selection bias,
##   Missing data, Mentioning errors. Derived from 07_30_2026_scored_items_long.csv.)
###############################################################################
VAL_CAPABLE <- c("Random error","Selection bias","Measurement bias","Confounding bias",
                 "Missing data","Conflating task")
REP_CAPABLE <- c("Random error","Selection bias","Missing data","Mentioning errors")
capable <- function(dom, ax) if (ax == "VAL") dom %in% VAL_CAPABLE else dom %in% REP_CAPABLE

BY_DOM$structural <- BY_DOM$degenerate & !mapply(capable, BY_DOM$domain, BY_DOM$axis)
BY_DOM$needs_imputation <- BY_DOM$degenerate & !BY_DOM$structural

don_all  <- BY_DOM[!BY_DOM$degenerate, ]
imp <- do.call(rbind, lapply(which(BY_DOM$needs_imputation), function(i) {
  ax  <- BY_DOM$axis[i]
  don_ax <- don_all[don_all$axis == ax, ]
  mk <- function(pool, lab) data.frame(
    domain = BY_DOM$domain[i], axis = ax, donor_pool = lab, n_donors = nrow(pool),
    eps1_max = max(pool$eps1, na.rm = TRUE), eps1_mean = mean(pool$eps1, na.rm = TRUE),
    eps0_max = max(pool$eps0, na.rm = TRUE), eps0_mean = mean(pool$eps0, na.rm = TRUE),
    stringsAsFactors = FALSE)
  rbind(mk(don_ax, sprintf("usable %s cells", ax)), mk(don_all, "all usable cells"))
}))

cat("\n\n=========== IMPUTED PARAMETERS for the 3 unmeasurable cells ===========\n")
cat("TSA rule: take the HIGHEST of the measured cells (average shown as the alternative).\n")
cat("⚠ 'Highest' is not one-directionally conservative: a high eps1 REMOVES flaws and so\n")
cat("  works against our conclusion, while a high eps0 ADDS them and works for it. Using\n")
cat("  the maximum for both widens the interval in both directions, which is the point.\n\n")
print(imp, row.names = FALSE, digits = 3)

## the values actually carried forward: TSA's rule, axis-matched donor pool
FINAL_IMP <- imp[imp$donor_pool == paste("usable", imp$axis, "cells"), ]
FINAL_IMP$eps1 <- FINAL_IMP$eps1_max; FINAL_IMP$eps0 <- FINAL_IMP$eps0_max
FINAL_IMP$basis <- sprintf("IMPUTED (TSA 2026-08-19): max over the %d measured %s cells",
                           FINAL_IMP$n_donors, FINAL_IMP$axis)
cat("\n--- carried forward (axis-matched donor pool, maximum) ---\n")
print(FINAL_IMP[, c("domain","axis","n_donors","eps1","eps0","basis")],
      row.names = FALSE, digits = 3)
write.csv(imp, file.path(TBL, sprintf("%s_calibration_imputed_parameters.csv", STAMP)),
          row.names = FALSE)

cat("\n=========== structural cells -- NOT imputed, parameter does not exist ===========\n")
s <- BY_DOM[BY_DOM$structural, c("domain","axis")]
if (nrow(s)) for (i in seq_len(nrow(s)))
  cat(sprintf("    %-18s %s\n", s$domain[i], s$axis[i]))

cat("\n=========== reconstructions applied (assumptions, not data) ===========\n")
cat("  follow       :", RECON_FOLLOW, "\n")
cat("  time_verying :", RECON_TVY, "\n")
cat("\nwrote 2 tables to outputs/tables/\n")

###############################################################################
##  THE JOURNAL-QUARTILE CONTRAST UNDER MEASUREMENT ERROR
##
##  Project : Assessment of Healthcare Research Quality in Saudi Arabia
##  Plan    : docs/SENSITIVITY_ANALYSIS_PLAN.md section 3d
##  Date    : 2026-08-20
##  Run FROM THE REPOSITORY ROOT.
##
##  WHY THIS ONE IS DIFFERENT FROM EVERY OTHER SENSITIVITY ANALYSIS HERE
##  All the others defend a HIGH prevalence against the charge that reviewer error
##  inflated it. This defends a NULL -- "journal impact-factor quartile does not
##  track methodological quality" -- which the Discussion leans on, because the
##  national KPI IS the first-quartile share. Nondifferential measurement error
##  biases a DIFFERENCE toward the null. So error works FOR the other analyses and
##  AGAINST this one: a real quartile gap could have been flattened into our null.
##
##  ⚠ THE PERTURBATION USED IN SECTIONS 3 AND 3b IS THE WRONG TOOL HERE.
##  Re-perturbing observed data adds a second layer of error to data that already
##  carries one; it attenuates an already-attenuated difference and would "confirm"
##  the null by construction. The right operation is the inverse: estimate the
##  attenuation and DIVIDE it out (the matrix / Bross correction).
##
##  ⚠⚠ BOTH TASKS ARE RUN. The manuscript sentence quotes the CAUSAL means, but the
##  descriptive studies show a visible quartile gradient (1.53 / 1.62 / 2.22 / 2.18)
##  that the causal analysis alone would hide. A claim that quartile does not track
##  quality has to survive on both tasks or be qualified to one. Tasks are never
##  pooled -- they are scored on different item sets.
###############################################################################

source("code/lib/score_dataset_lib.R")

PROJ <- getwd(); STAMP <- "08_20_2026"
TBL  <- file.path(PROJ, "outputs", "tables"); stopifnot(dir.exists(TBL))
set.seed(20260820L)
B_BOOT <- 2000L
M_PAR  <- 2000L
f <- function(p) file.path(PROJ, p)
lgt  <- function(p) log(p / (1 - p))
ilgt <- function(x) 1 / (1 + exp(-x))
CH <- function(p) read.csv(f(p), stringsAsFactors = FALSE, colClasses = "character",
                           na.strings = character(0))

###############################################################################
## 1.  Data, groups and parameters
###############################################################################
d     <- read.csv(f("data/analysis/07_23_2026_ANALYSIS_DATASET_wide.csv"),
                  stringsAsFactors = FALSE, colClasses = "character", check.names = FALSE)
items <- score_items(d)

## groups built exactly as 07_30_2026_stratified_analysis.R builds them
jcr <- CH("data/journals/07_25_2026_journal_landscape_by_paper_385_JCR.csv")[, c("PMID","jcr_2022_quartile")]
GRP <- merge(data.frame(PMID = d$PMID, Study_Type = d$Study_Type, stringsAsFactors = FALSE),
             jcr, by = "PMID", all.x = TRUE)
GRP$jcr <- ifelse(is.na(GRP$jcr_2022_quartile) | GRP$jcr_2022_quartile == "",
                  "None", GRP$jcr_2022_quartile)

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
DOMS <- sort(unique(items$domain))
PAR <- do.call(rbind, lapply(DOMS, function(dm) do.call(rbind, lapply(c("VAL","REP"), function(ax) {
  p <- getp(dm, ax)
  data.frame(domain = dm, axis = ax, e1 = p$e1, e0 = p$e0, e1lo = p$e1lo, e1hi = p$e1hi,
             e0lo = p$e0lo, e0hi = p$e0hi, source = p$src, stringsAsFactors = FALSE) }))))
PV <- PAR[PAR$axis == "VAL", ]
draw_one <- function(pt, lo, hi) {
  if (is.na(lo) || is.na(hi) || pt <= 0 || pt >= 1) return(pt)
  lo <- max(lo, 1e-3); hi <- min(hi, 1 - 1e-3); if (hi <= lo) return(pt)
  ilgt(rnorm(1, lgt(pt), (lgt(hi) - lgt(lo)) / (2 * 1.96)))
}

CONTRASTS <- list(
  list(key = "Q1_vs_Q4",       a = c("Q1"), b = c("Q4"),
       note = "the two ends of the ranked scale -- the Abstract's comparison"),
  list(key = "Q1Q2_vs_Q3Q4",   a = c("Q1","Q2"), b = c("Q3","Q4"),
       note = "the binary split the KPI implies (top half vs bottom half)"),
  list(key = "ranked_vs_none", a = c("Q1","Q2","Q3","Q4"), b = c("None"),
       note = "ranked vs unranked"))

###############################################################################
## 2.  One task, end to end
###############################################################################
analyse_task <- function(tk, run_simcheck = FALSE) {
  g <- GRP[GRP$Study_Type == tk, ]
  pri  <- which(items$primary)
  pm   <- factor(items$PMID[pri], levels = g$PMID)
  keep <- !is.na(pm)
  pmi  <- as.integer(pm)[keep]; P <- nlevels(pm)
  st0  <- items$state[pri][keep]
  dm0  <- items$domain[pri][keep]
  app0 <- st0 != "NA"; isV0 <- st0 == "VAL"

  count_val <- function(v) tabulate(pmi[v], nbins = P)
  cnt  <- count_val(isV0)
  appc <- tabulate(pmi[app0], nbins = P)
  mean_by <- function(x, by) vapply(split(x, by), mean, numeric(1))

  ## --- baseline means, checked against the published stratified analysis --------
  obs_q <- mean_by(cnt, g$jcr)
  SS  <- read.csv(f("data/scoring/07_30_2026_stratified_summary.csv"), stringsAsFactors = FALSE)
  pub <- SS[SS$stratifier == "JCR 2022 quartile" & SS$task == tk, ]
  for (lv in c("Q1","Q2","Q3","Q4","None"))
    stopifnot(abs(obs_q[[lv]] - pub$mean_val_err[pub$level == lv]) < 1e-9)

  cat(sprintf("\n############ %s (n = %d) ############\n", toupper(tk), nrow(g)))
  cat("mean validity-flaw count per paper, by quartile [reproduces the published table]:\n")
  print(round(obs_q[c("Q1","Q2","Q3","Q4","None")], 3))
  cat("applicable primary items per paper (is the count comparable across groups?):\n")
  print(round(mean_by(appc, g$jcr)[c("Q1","Q2","Q3","Q4","None")], 2))

  ## --- attenuation factor, weighted by where the items actually are -------------
  fac_dom <- vapply(DOMS, function(x) 1 - PV$e1[PV$domain == x] - PV$e0[PV$domain == x], numeric(1))
  w_dom   <- vapply(DOMS, function(x) sum(app0 & dm0 == x), numeric(1)); w_dom <- w_dom / sum(w_dom)
  fac     <- sum(fac_dom * w_dom)
  att <- data.frame(task = tk, domain = DOMS, weight = w_dom,
                    eps1 = PV$e1[match(DOMS, PV$domain)], eps0 = PV$e0[match(DOMS, PV$domain)],
                    factor = fac_dom, source = PV$source[match(DOMS, PV$domain)],
                    stringsAsFactors = FALSE)
  cat(sprintf("attenuation factor (1 - eps1 - eps0, item-weighted): %.3f\n", fac))

  ## --- contrasts: observed, rate, and de-attenuated -----------------------------
  rate <- cnt / appc
  res <- do.call(rbind, lapply(CONTRASTS, function(C) {
    A <- which(g$jcr %in% C$a); B <- which(g$jcr %in% C$b)
    bo <- vapply(seq_len(B_BOOT), function(i)
      mean(cnt[sample(A, length(A), TRUE)]) - mean(cnt[sample(B, length(B), TRUE)]), numeric(1))
    br <- vapply(seq_len(B_BOOT), function(i)
      mean(rate[sample(A, length(A), TRUE)]) - mean(rate[sample(B, length(B), TRUE)]), numeric(1))
    ## correction: resample papers AND redraw every epsilon, then divide
    cv <- vapply(seq_len(M_PAR), function(i) {
      fdraw <- sum(vapply(seq_along(DOMS), function(k) {
        p <- PV[PV$domain == DOMS[k], ]
        if (p$source[1] == "not applicable") return(w_dom[k])
        (1 - draw_one(p$e1[1], p$e1lo[1], p$e1hi[1]) -
             draw_one(p$e0[1], p$e0lo[1], p$e0hi[1])) * w_dom[k]
      }, numeric(1)))
      ia <- sample(A, length(A), TRUE); ib <- sample(B, length(B), TRUE)
      o  <- mean(cnt[ia])  - mean(cnt[ib])
      or <- mean(rate[ia]) - mean(rate[ib])
      if (fdraw <= 0.05) c(NA_real_, NA_real_) else c(o / fdraw, or / fdraw)
    }, numeric(2))
    cr <- cv[2, ][is.finite(cv[2, ])]; cv <- cv[1, ][is.finite(cv[1, ])]
    data.frame(task = tk, contrast = C$key, n_a = length(A), n_b = length(B),
               mean_a = mean(cnt[A]), mean_b = mean(cnt[B]),
               observed = mean(cnt[A]) - mean(cnt[B]),
               obs_lo = quantile(bo, .025), obs_hi = quantile(bo, .975),
               rate_diff = mean(rate[A]) - mean(rate[B]),
               rate_lo = quantile(br, .025), rate_hi = quantile(br, .975),
               corrected = median(cv), cor_lo = quantile(cv, .025), cor_hi = quantile(cv, .975),
               cor_rate = median(cr), cor_rate_lo = quantile(cr, .025),
               cor_rate_hi = quantile(cr, .975),
               attenuation = fac, note = C$note, stringsAsFactors = FALSE)
  }))

  ## --- simulation check that the analytic attenuation is the right one ----------
  sim <- NULL
  if (run_simcheck) {
    A2 <- which(g$jcr %in% c("Q1","Q2")); B2 <- which(g$jcr %in% c("Q3","Q4"))
    in_top <- g$jcr[pmi] %in% c("Q1","Q2")
    e1i <- PV$e1[match(dm0, PV$domain)]; e0i <- PV$e0[match(dm0, PV$domain)]
    sim <- do.call(rbind, lapply(seq(0, 0.5, by = 0.1), function(gg) {
      r <- vapply(seq_len(200L), function(i) {
        tV <- isV0 & !(isV0 & in_top & runif(length(isV0)) < gg)   # counterfactual truth
        u  <- runif(length(tV))
        oV <- ifelse(tV, u > e1i, u < e0i) & app0                  # then measured with error
        tc <- count_val(tV); oc <- count_val(oV)
        c(mean(tc[A2]) - mean(tc[B2]), mean(oc[A2]) - mean(oc[B2]))
      }, numeric(2))
      data.frame(task = tk, g = gg, true_gap = mean(r[1, ]), observed_gap = mean(r[2, ]))
    }))
    slope <- coef(lm(observed_gap ~ true_gap, data = sim))[2]
    cat(sprintf("simulation check: slope of observed on true = %.3f vs analytic %.3f\n",
                slope, fac))
    stopifnot(abs(slope - fac) < 0.05)
  }
  list(res = res, att = att, sim = sim)
}

cat("=========== JOURNAL-QUARTILE CONTRAST, CORRECTED FOR MEASUREMENT ERROR ===========\n")
cat("Outcome: validity flaws per paper. Positive = the better-ranked group is WORSE.\n")
CA <- analyse_task("Causal", run_simcheck = TRUE)
CD <- analyse_task("Descriptive")
RES <- rbind(CA$res, CD$res); ATT <- rbind(CA$att, CD$att)
write.csv(RES, file.path(TBL, sprintf("%s_quartile_contrast_corrected.csv", STAMP)), row.names = FALSE)
write.csv(ATT, file.path(TBL, sprintf("%s_quartile_attenuation.csv", STAMP)), row.names = FALSE)
write.csv(CA$sim, file.path(TBL, sprintf("%s_quartile_attenuation_simcheck.csv", STAMP)), row.names = FALSE)

###############################################################################
## 3.  Readable summary
###############################################################################
cat("\n=========== RESULTS ===========\n")
for (tk in c("Causal","Descriptive")) {
  cat(sprintf("\n---- %s ----\n", tk))
  for (C in CONTRASTS) {
    r <- RES[RES$task == tk & RES$contrast == C$key, ]
    cat(sprintf("\n%-16s %s\n", C$key, C$note))
    cat(sprintf("   observed  %+0.2f flaws/paper [%+0.2f, %+0.2f]   (rate %+0.3f [%+0.3f, %+0.3f])\n",
                r$observed, r$obs_lo, r$obs_hi, r$rate_diff, r$rate_lo, r$rate_hi))
    cat(sprintf("   corrected %+0.2f              [%+0.2f, %+0.2f]   (rate %+0.3f [%+0.3f, %+0.3f])\n",
                r$corrected, r$cor_lo, r$cor_hi, r$cor_rate, r$cor_rate_lo, r$cor_rate_hi))
    if ((r$cor_lo > 0 || r$cor_hi < 0) && !(r$cor_rate_lo > 0 || r$cor_rate_hi < 0))
      cat("   ⚠ clears zero on the COUNT but not on the RATE -- part of this gap is a difference\n     in how many items each group's studies are asked, not in how often they fail them.\n")
    if (r$cor_lo > 0 || r$cor_hi < 0) {
      cat(sprintf("   ★ NOT NULL — the corrected interval clears zero. The better-ranked group is\n"))
      cat(sprintf("     genuinely %s, by %.2f to %.2f flaws per paper (%.0f-%.0f%% of the %.2f comparator).\n",
                  if (r$cor_hi < 0) "cleaner" else "worse",
                  min(abs(c(r$cor_lo, r$cor_hi))), max(abs(c(r$cor_lo, r$cor_hi))),
                  100 * min(abs(c(r$cor_lo, r$cor_hi))) / r$mean_b,
                  100 * max(abs(c(r$cor_lo, r$cor_hi))) / r$mean_b, r$mean_b))
    } else {
      cat(sprintf("   NULL, and bounded: a true advantage for the better-ranked group larger than\n"))
      cat(sprintf("     %.2f flaws per paper (%.0f%% of the %.2f comparator mean) would have shown\n",
                  abs(min(r$cor_lo, 0)), 100 * abs(min(r$cor_lo, 0)) / r$mean_b, r$mean_b))
      cat(sprintf("     through the measurement error, and is excluded.\n"))
    }
  }
}
cat("\n⚠ Everything above assumes NONDIFFERENTIAL error -- reviewers no more accurate on Q1\n")
cat("  papers than on Q4 papers. Reviewers were NOT blinded to the journal, so a prestige\n")
cat("  halo would make the error differential, and differential error can bias a contrast in\n")
cat("  EITHER direction, including away from the null. Nothing here can test that: concede it.\n")
cat("\nwrote 3 tables to outputs/tables/\n")

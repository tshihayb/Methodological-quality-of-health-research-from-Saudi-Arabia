###############################################################################
##  SENSITIVITY ANALYSIS FOR LOW INTER-RATER AGREEMENT
##  Tier 1b (per-item agreement statistics + re-derived difficulty ranking)
##  and Section 2 (observed bound on CONCORDANT error)
##
##  Project : Assessment of Healthcare Research Quality in Saudi Arabia
##  Plan    : docs/SENSITIVITY_ANALYSIS_PLAN.md  (sections 1b, 1c, 1d, 1e, 2)
##  Date    : 2026-08-19
##  Run FROM THE REPOSITORY ROOT.
##
##  WHY THIS EXISTS
##  Reviewers will read our per-item agreement as low.  Cicchetti & Feinstein
##  (J Clin Epidemiol 1990;43:551-8) and Byrt, Bishop & Carlin (ibid 1993;46:
##  423-9) say that for the purpose of UNDERSTANDING an observational process
##  (as opposed to benchmarking it against other studies) no single omnibus
##  index will serve, and that kappa must always be published alongside p_pos
##  and p_neg, with the bias index and the prevalence index reported too.
##  This script produces exactly that, per item, plus the difficulty ranking
##  re-derived off kappa (the existing kappa-ranked list is a documented misuse).
##
##  WHAT IT WRITES  (all into outputs/tables/, stamp 08_19_2026)
##    1  agreement_item_level.csv        one row per tool item, native categories
##    2  agreement_option_level.csv      one row per item x option, binary 2x2
##    3  agreement_difficulty_ranking.csv  kappa-rank vs p0-rank, with movement
##    4  concordant_error_bound.csv      section 2, cell-by-cell audit trail
##    5  ../reports/..._tier1_summary.md a readable summary of all four
##    6  08_22_2026_agreement_collapsed_by_concept.csv  the same per-item statistics
##       with the tool's items pooled into concepts, i.e. NOT stratified by task.
##       Added 2026-08-22, section 8, appended after every other write so that the
##       five tables above still reproduce byte for byte (verified).
##
##  UNIT OF ANALYSIS.  Cell = (PMID x tool item).  The grid is 385 x 47 =
##  18,095, of which 10,817 are not applicable to either reviewer.  Agreement
##  is computed on BOTH-ANSWERED cells only (6,795).  The 483 applicability
##  disputes -- one reviewer answered, the other treated the item as N/A -- are
##  carried as a separate column, never pooled: they are a branch-logic failure,
##  not a judgment failure, and pooling them inflates apparent unreliability.
###############################################################################

suppressPackageStartupMessages({ library(readxl) })

PROJ  <- getwd()
STAMP <- "08_19_2026"
TBL   <- file.path(PROJ, "outputs", "tables")
REP   <- file.path(PROJ, "outputs", "reports")
stopifnot(dir.exists(TBL), dir.exists(REP))
set.seed(20260819L)
B_BOOT <- 2000L

f  <- function(p) file.path(PROJ, p)
p3 <- function(x) ifelse(is.na(x), NA_real_, round(x, 3))

###############################################################################
## 0.  INPUT
###############################################################################
cells0 <- read.csv(f("data/adjudication/process-tables/cell_level_detail.csv"),
                   colClasses = "character")
stopifnot(nrow(cells0) == 18095L, length(unique(cells0$PMID)) == 385L,
          length(unique(cells0$variable)) == 47L)

## Normalisation -- byte-for-byte the rule the build and adjudication scripts
## use, so every count here reconciles with the published 69.0%: casefold,
## collapse whitespace, and sort the parts of a ";"-multiselect.
## sort(method="radix") reproduces Python's byte-order sort; R's default locale
## collation orders differently and would silently change the comparison.
norm1 <- function(v) {
  s <- ifelse(is.na(v), "", as.character(v))
  s <- gsub("\\s+", " ", trimws(tolower(s)))
  s[s == "nan"] <- ""
  ix <- grepl(";", s, fixed = TRUE)
  if (any(ix)) s[ix] <- vapply(s[ix], function(z) {
    p <- trimws(strsplit(z, ";", fixed = TRUE)[[1]]); p <- p[nzchar(p)]
    paste(sort(p, method = "radix"), collapse = ";") }, character(1))
  s
}

## DELIMITER RULE (plan 1e, open item -- CLOSED 2026-08-19 by direct check).
## The plan proposed splitting err_disc on ";" AND ",".  Checked at reviewer
## level: NO reviewer answer to any of the five select-all items contains a
## comma at all (0/167 descriptive_err_disc, 0/453 causal_err_disc, and the one
## comma in causal_base_conf_meth is INSIDE an option label).  The
## "Random error, Selection bias;Confounding bias" string that motivated the
## proposed rule occurs only in the ADJUDICATED values, in exactly one cell.
## So ";" only is correct for every reviewer-level statistic in this script,
## and the comma exception never touches agreement.  Asserted below.
MULTI <- c("descriptive_err_disc","causal_err_disc",
           "causal_base_conf_meth","causal_tv_conf_meth","causal_conf_var_det")
OPT_WITH_COMMA <- "instrumental variable analysis besides randomization"
chk <- cells0[cells0$variable %in% MULTI, ]
chk_vals <- c(chk$r1, chk$r2); chk_vals <- chk_vals[!is.na(chk_vals)]
stopifnot(!any(grepl(",", chk_vals, fixed = TRUE) &
               !grepl(OPT_WITH_COMMA, tolower(chk_vals), fixed = TRUE)))

cells0$r1n <- norm1(cells0$r1)
cells0$r2n <- norm1(cells0$r2)

## Both-answered stratum, and the applicability disputes kept beside it.
BOTH <- c("Reviewers agreed", "Disagreed on the answer")
cells <- cells0[cells0$status %in% BOTH, ]
stopifnot(nrow(cells) == 6795L, sum(cells0$status == "Reviewers agreed") == 5021L,
          sum(cells0$status == "Disagreed on applicability") == 483L)
stopifnot(all(nzchar(cells$r1n)), all(nzchar(cells$r2n)))
## p0 must reproduce the published agreed count exactly
stopifnot(sum(cells$r1n == cells$r2n) == 5021L)

n_applic <- table(factor(cells0$variable[cells0$status == "Disagreed on applicability"],
                         levels = sort(unique(cells0$variable))))

###############################################################################
## 1.  ITEM METADATA -- labels, domains, and the tool-order used by every table
##     (identical to the CMAP block in 07_24_2026_adjudication_process_analysis.R)
###############################################################################
DOMS <- c("Recusal","Study task","Study design","Saudi population","Random error",
          "Selection bias","Measurement bias","Confounding","Missing data",
          "Mentioning errors","Conflating the task")
CMAP <- read.csv(text = paste(
"concept|dom|label|vars",
"recusal|Recusal|Reviewer recused from the study?|recusal",
"task|Study task|Study task (epidemiological paradigm)|task",
"design|Study design|Study design|descriptive_design;predictive_design;causal_design",
"pop|Saudi population|Used data from Saudi Arabia?|descriptive_pop;predictive_pop;causal_pop",
"sampling|Random error|Sampling technique|descriptive_sampling;causal_sampling",
"sample_size|Random error|Sample-size calculation done?|descriptive_sample_size;causal_sample_size",
"acc_sampl|Random error|Accounted for non-response etc. in the sample-size calculation?|descriptive_acc_sampl;causal_acc_sampl",
"sample_ach|Random error|Required sample size achieved?|descriptive_sample_ach;causal_sample_ach",
"base_sel|Selection bias|Baseline selection bias accounted for?|descriptive_base_sel;causal_base_sel",
"comp_dis|Selection bias|Compared responders vs non-responders?|causal_comp_dis",
"follow|Selection bias|Follow-up present in the study?|causal_follow",
"ltfu_bias|Selection bias|Loss-to-follow-up bias present?|causal_ltfu_bias",
"ltfu_acc|Selection bias|Loss-to-follow-up bias accounted for?|causal_ltfu_acc",
"outcome_type|Measurement bias|Nature of the outcome (objective or subjective)|descriptive_outcome_type;causal_outcome_type",
"val_outcome|Measurement bias|Validated outcome measurement?|descriptive_val_outcome;causal_val_outcome",
"diff_or_nondiff_out|Measurement bias|Outcome misclassification differential or non-differential?|causal_diff_or_nondiff_out",
"out_bias_acc|Measurement bias|Outcome measurement bias accounted for?|descriptive_out_bias_acc;causal_out_bias_acc",
"exposure_type|Measurement bias|Nature of the exposure (objective or subjective)|causal_exposure_type",
"val_exposure|Measurement bias|Validated exposure measurement?|causal_val_exposure",
"diff_or_nondiff_exp|Measurement bias|Exposure misclassification differential or non-differential?|causal_diff_or_nondiff_exp",
"exp_bias_acc|Measurement bias|Exposure measurement bias accounted for?|causal_exp_bias_acc",
"dep_or_indep_misc|Measurement bias|Exposure vs outcome measurement bias: independent or dependent?|causal_dep_or_indep_misc",
"base_conf_meth|Confounding|Baseline confounding method(s) used|causal_base_conf_meth",
"time_verying|Confounding|Time-varying effect estimated?|causal_time_verying",
"tv_conf_meth|Confounding|Time-varying confounding method(s) used|causal_tv_conf_meth",
"conf_var_det|Confounding|How confounding variables were selected|causal_conf_var_det",
"miss_outcome|Missing data|Any participant with a missing outcome?|descriptive_miss_outcome;causal_miss_outcome",
"hand_miss_outcom|Missing data|Method for handling missing outcome data|descriptive_hand_miss_outcom;causal_hand_miss_outcom",
"miss_exposure|Missing data|Any participant with a missing exposure?|causal_miss_exposure",
"hand_miss_exposure|Missing data|Method for handling missing exposure data|causal_hand_miss_exposure",
"err_disc|Mentioning errors|Errors qualitatively mentioned in the discussion|descriptive_err_disc;causal_err_disc",
"confl_task|Conflating the task|Investigated an association beyond describing the sample?|descriptive_confl_task",
sep = "\n"), sep = "|", header = TRUE, quote = "", comment.char = "", stringsAsFactors = FALSE)
CMAP$concept_ord <- seq_len(nrow(CMAP))
CMAP$dom_ord     <- match(CMAP$dom, DOMS)
stopifnot(!anyNA(CMAP$dom_ord))
V2C <- do.call(rbind, Map(function(cc, vs)
  data.frame(variable = strsplit(vs, ";", fixed = TRUE)[[1]], concept = cc,
             stringsAsFactors = FALSE), CMAP$concept, CMAP$vars))
stopifnot(nrow(V2C) == 47L, setequal(V2C$variable, unique(cells0$variable)))

cells$concept <- V2C$concept[match(cells$variable, V2C$variable)]
vtask_of <- function(v) ifelse(grepl("^descriptive_", v), "Descriptive",
                        ifelse(grepl("^predictive_",  v), "Predictive",
                        ifelse(grepl("^causal_",      v), "Causal", "All")))

## ORDINAL items (plan 1e).  The validation ladder is No < content/face <
## criterion.  The fourth option, "this type of objective measurement does not
## usually require validation", is NOT a rung on that ladder -- it is an
## applicability judgment -- so weighted kappa is computed on the on-ladder
## subset only and the off-ladder option is reported as its own one-vs-rest
## row in the option-level table.  Treating it as a rung would fabricate a
## distance that the instrument does not define.
ORD_LADDER <- c("no" = 0,
  "yes, the authors conducted content/face validity or cited the content/face validity from other studies" = 1,
  "yes, the authors conducted criterion validity or cited the criterion validity from other studies" = 2)
ORDINAL <- c("descriptive_val_outcome","causal_val_outcome","causal_val_exposure")

###############################################################################
## 2.  AGREEMENT STATISTICS
###############################################################################

## --- Cohen's kappa on a q x q table, with the Fleiss-Cohen-Everitt (1969)
##     large-sample standard error.  Returns NA when there is no variation
##     (a single category used) -- kappa is undefined there, not zero.
kappa_full <- function(x, y, w = NULL) {
  lev <- sort(union(x, y)); q <- length(lev)
  N <- length(x)
  if (q < 2L) return(list(kappa = NA_real_, se = NA_real_, q = q, N = N, pe = NA_real_))
  tab <- table(factor(x, lev), factor(y, lev))
  P   <- tab / N
  r   <- rowSums(P); s <- colSums(P)
  ## a supplied weight matrix must be named and is subset to the levels actually
  ## present, so a category unused in a subset cannot silently misalign it.
  if (is.null(w)) W <- diag(q) else {
    stopifnot(!is.null(dimnames(w)), all(lev %in% rownames(w)))
    W <- w[lev, lev, drop = FALSE]
  }
  p0  <- sum(W * P)
  pe  <- sum(W * outer(r, s))
  if (isTRUE(all.equal(pe, 1))) return(list(kappa = NA_real_, se = NA_real_, q = q, N = N, pe = pe))
  k   <- (p0 - pe) / (1 - pe)
  ## weighted-kappa variance (Fleiss, Cohen & Everitt 1969); reduces to the
  ## unweighted formula when W = I.
  wbar_i <- W %*% s          # row-wise mean weight
  wbar_j <- t(W) %*% r       # col-wise mean weight
  M <- outer(as.vector(wbar_i), as.vector(wbar_j), "+")
  v <- sum(P * (W - M * (1 - k))^2) - (k - pe * (1 - k))^2
  se <- if (is.na(v) || v <= 0) NA_real_ else sqrt(v / (N * (1 - pe)^2))
  list(kappa = k, se = se, q = q, N = N, pe = pe)
}

## --- Gwet's AC1 (Br J Math Stat Psychol 2008;61:29-48), multi-category form,
##     his equations (37)-(38): pe|g = 1/(q-1) * sum_k pk(1-pk), with pk the
##     mean of the two raters' marginal proportions.  The 2008 paper is the
##     correct citation for q > 2; the "binary only" caveat applies to the
##     2001 version, not this one.
ac1_stat <- function(x, y) {
  lev <- sort(union(x, y)); q <- length(lev); N <- length(x)
  if (q < 2L) return(NA_real_)
  pk  <- (table(factor(x, lev)) / N + table(factor(y, lev)) / N) / 2
  peg <- sum(pk * (1 - pk)) / (q - 1)
  pa  <- mean(x == y)
  if (isTRUE(all.equal(peg, 1))) return(NA_real_)
  (pa - peg) / (1 - peg)
}

## --- Brennan & Prediger's free-marginal kappa_n (Educ Psychol Meas 1981;41:
##     687-99): (n*p0 - 1)/(n - 1).  n is taken as the number of categories
##     OBSERVED in the data, not the number the instrument offers.  That is the
##     CONSERVATIVE choice: kappa_n rises with n, so using the instrument's full
##     option list would give a larger number.  This directly answers Scott's
##     objection, quoted by Brennan & Prediger, that "if non-functional
##     categories are used in a study, K_n may be artificially large."
kappa_n <- function(p0, q) if (is.na(q) || q < 2L) NA_real_ else (q * p0 - 1) / (q - 1)

## --- binary 2 x 2 statistics.  Notation is Cicchetti & Feinstein's, verified
##     against the primary (J Clin Epidemiol 1990;43:551-8, pp. 554-5):
##       table {a b ; c d},  f1 = a + c,  g1 = a + b,  f2 = b + d,  g2 = c + d
##       p_pos = 2a/(f1+g1) = 2a/(N + a - d)
##       p_neg = 2d/(f2+g2) = 2d/(N - a + d)
##     PI is Byrt et al.'s prevalence index (a - d)/N, SIGNED, range -1..+1.
##     BI is their bias index (b - c)/N.  PABAK = 2*p0 - 1 = Bennett's S =
##     kappa_n at n = 2.
binary_stats <- function(x1, x2) {
  a <- sum( x1 &  x2); b <- sum( x1 & !x2)
  c_ <- sum(!x1 &  x2); d <- sum(!x1 & !x2)
  N <- a + b + c_ + d
  p0 <- (a + d) / N
  dpos <- N + a - d; dneg <- N - a + d
  ppos <- if (dpos > 0) 2 * a / dpos else NA_real_
  pneg <- if (dneg > 0) 2 * d / dneg else NA_real_
  f1 <- a + c_; f2 <- b + d; g1 <- a + b; g2 <- c_ + d
  kk <- kappa_full(as.character(as.integer(x1)), as.character(as.integer(x2)))
  list(a = a, b = b, c = c_, d = d, N = N, p0 = p0,
       p_pos = ppos, p_neg = pneg,
       PI = (a - d) / N, BI = (b - c_) / N, PABAK = 2 * p0 - 1,
       kappa = kk$kappa, kappa_se = kk$se, AC1 = ac1_stat(x1, x2),
       f1 = f1, f2 = f2, g1 = g1, g2 = g2,
       ## Cicchetti & Feinstein's "swing" term: the paradoxes in kappa trace to
       ## the product of the marginal imbalance (f1 - f2) and the positive/
       ## negative disparity (p_pos - p_neg).  It enters their equation (6)
       ## with a MINUS sign, so a positive product depresses kappa.
       marg_imbalance = f1 - f2,
       ppos_minus_pneg = if (is.na(ppos) || is.na(pneg)) NA_real_ else ppos - pneg,
       swing = if (is.na(ppos) || is.na(pneg)) NA_real_ else (f1 - f2) * (ppos - pneg),
       ## the raw product is in counts, faithful to their worked tables (all of
       ## which have N = 100).  Our items range from N = 1 to N = 385, so a
       ## scale-free version is also carried for cross-item comparison.
       swing_scaled = if (is.na(ppos) || is.na(pneg)) NA_real_
                      else ((f1 - f2) / N) * (ppos - pneg),
       ## p0 is a weighted sum of p_pos and p_neg with weights (f1+g1)/2N and
       ## (f2+g2)/2N -- their p. 555.  w_neg says how much of the observed
       ## agreement is carried by agreement on the NEGATIVE category.
       w_pos = (f1 + g1) / (2 * N), w_neg = (f2 + g2) / (2 * N))
}

## Verification that binary_stats implements the primary correctly: rebuild
## kappa from Cicchetti & Feinstein's equation (6), which is written purely in
## terms of N, f1, f2, p_pos and p_neg, and require it to reproduce the kappa
## computed directly from the 2 x 2 table.  If this assertion ever fails the
## decomposition reported in the option-level table is not theirs.
cf_eq6 <- function(N, f1, f2, ppos, pneg) {
  if (any(is.na(c(ppos, pneg)))) return(NA_real_)
  s  <- 2 - ppos - pneg
  num <- N^2 * (ppos + pneg - 2 * ppos * pneg) - 2 * f1 * f2 * s - N * (f1 - f2) * (ppos - pneg)
  den <- N^2 * s                                - 2 * f1 * f2 * s - N * (f1 - f2) * (ppos - pneg)
  if (isTRUE(all.equal(den, 0))) return(NA_real_)
  num / den
}
local({
  set.seed(1L); ok <- 0L
  for (i in 1:400) {
    n <- sample(20:300, 1)
    x1 <- runif(n) < runif(1, .05, .95); x2 <- ifelse(runif(n) < .8, x1, !x1)
    bs <- binary_stats(x1, x2)
    if (is.na(bs$kappa)) next
    k6 <- cf_eq6(bs$N, bs$f1, bs$f2, bs$p_pos, bs$p_neg)
    stopifnot(isTRUE(all.equal(bs$kappa, k6, tolerance = 1e-8)))
    ## and p0 as the weighted sum of p_pos and p_neg
    stopifnot(isTRUE(all.equal(bs$p0, bs$w_pos * bs$p_pos + bs$w_neg * bs$p_neg,
                               tolerance = 1e-8)))
    ok <- ok + 1L
  }
  cat("[check] Cicchetti & Feinstein eq.(6) reproduced from p_pos/p_neg/f1/f2 in",
      ok, "random 2x2 tables\n")
})

## multi-select tokenisation (";" only -- see the delimiter note above)
tok <- function(z) {
  p <- trimws(strsplit(z, ";", fixed = TRUE)[[1]])
  unique(p[nzchar(p)])
}

###############################################################################
## 3.  TABLE 1 -- per item, native categories
###############################################################################
boot_ci <- function(stat_fun, n, B = B_BOOT) {
  if (n < 5L) return(c(NA_real_, NA_real_))
  v <- vapply(seq_len(B), function(i) stat_fun(sample.int(n, n, replace = TRUE)), numeric(1))
  v <- v[is.finite(v)]
  if (length(v) < B / 10) return(c(NA_real_, NA_real_))
  unname(quantile(v, c(.025, .975)))
}

item_rows <- lapply(sort(unique(cells$variable)), function(v) {
  s  <- cells[cells$variable == v, ]
  x  <- s$r1n; y <- s$r2n; N <- nrow(s)
  p0 <- mean(x == y)
  kk <- kappa_full(x, y)
  ac <- ac1_stat(x, y)
  kn <- if (v %in% MULTI) NA_real_ else kappa_n(p0, kk$q)
  ## bootstrap CIs for p0 and kappa
  ci_p0 <- boot_ci(function(ix) mean(x[ix] == y[ix]), N)
  ci_k  <- boot_ci(function(ix) kappa_full(x[ix], y[ix])$kappa, N)
  ## Weighted kappa for the ordinal items, on the on-ladder subset only.
  ## The UNWEIGHTED kappa on that same subset is reported beside it, because
  ## comparing a weighted kappa computed on 67 cells against an unweighted one
  ## computed on all 224 would confound the weighting with the subsetting.
  wk <- NA_real_; wk_u <- NA_real_; wk_n <- NA_integer_
  if (v %in% ORDINAL) {
    on <- x %in% names(ORD_LADDER) & y %in% names(ORD_LADDER)
    wk_n <- sum(on)
    if (wk_n >= 5L) {
      lv <- names(ORD_LADDER)
      sc <- ORD_LADDER[lv]
      W  <- 1 - abs(outer(sc, sc, "-")) / diff(range(sc))   # linear agreement weights
      dimnames(W) <- list(lv, lv)
      wk   <- kappa_full(x[on], y[on], w = W)$kappa
      wk_u <- kappa_full(x[on], y[on])$kappa
    }
  }
  ## modal category and its one-vs-rest prevalence index -- the multi-category
  ## analogue of Byrt's PI, and the number that says whether a low kappa is a
  ## prevalence artefact.
  allr  <- c(x, y); tb <- sort(table(allr), decreasing = TRUE)
  modal <- names(tb)[1]
  bsm   <- binary_stats(x == modal, y == modal)
  data.frame(
    variable = v, concept = V2C$concept[match(v, V2C$variable)],
    task = vtask_of(v),
    n_both = N, n_applic_dispute = as.integer(n_applic[v]),
    n_agree = sum(x == y),
    q_used = kk$q,
    p0 = p0, p0_lo = ci_p0[1], p0_hi = ci_p0[2],
    ## the denominator the 2026-07 record used: disagreement over ASSESSED
    ## cells, i.e. with the applicability disputes pooled in. Carried so the
    ## effect of that pooling on the difficulty ranking is auditable.
    dis_pct_assessed = 100 * (1 - sum(x == y) / (N + as.integer(n_applic[v]))),
    kappa = kk$kappa, kappa_se = kk$se,
    kappa_lo_asym = kk$kappa - 1.96 * kk$se, kappa_hi_asym = kk$kappa + 1.96 * kk$se,
    kappa_lo_boot = ci_k[1], kappa_hi_boot = ci_k[2],
    kappa_weighted_ordinal = wk, kappa_unweighted_ordinal_subset = wk_u,
    n_ordinal_subset = wk_n,
    kappa_n_free_marginal = kn, AC1 = ac,
    modal_category = modal, modal_share = as.numeric(tb[1]) / length(allr),
    PI_modal = bsm$PI, BI_modal = bsm$BI, PABAK_modal = bsm$PABAK,
    p_pos_modal = bsm$p_pos, p_neg_modal = bsm$p_neg,
    stringsAsFactors = FALSE)
})
ITEM <- do.call(rbind, item_rows)
ITEM$label     <- CMAP$label[match(ITEM$concept, CMAP$concept)]
ITEM$domain    <- CMAP$dom[match(ITEM$concept, CMAP$concept)]
ITEM$dom_ord   <- CMAP$dom_ord[match(ITEM$concept, CMAP$concept)]
ITEM$conc_ord  <- CMAP$concept_ord[match(ITEM$concept, CMAP$concept)]
ITEM$multiselect <- ITEM$variable %in% MULTI
ITEM <- ITEM[order(ITEM$dom_ord, ITEM$conc_ord, ITEM$task), ]
stopifnot(sum(ITEM$n_both) == 6795L, sum(ITEM$n_agree) == 5021L)

###############################################################################
## 4.  TABLE 2 -- per item x option, binary one-vs-rest
##     For single-select items each observed category is contrasted against all
##     others.  For the five select-all items each OPTION is contrasted against
##     its own absence -- the per-option binary decomposition the plan makes the
##     primary approach for those, since exact-set matching scores a cell with
##     three of four options shared as a total disagreement.
###############################################################################
opt_rows <- list()
for (v in sort(unique(cells$variable))) {
  s <- cells[cells$variable == v, ]
  x <- s$r1n; y <- s$r2n
  if (v %in% MULTI) {
    opts <- sort(unique(unlist(lapply(c(x, y), tok))))
    memb <- function(z, o) vapply(z, function(zz) o %in% tok(zz), logical(1))
  } else {
    opts <- sort(unique(c(x, y)))
    memb <- function(z, o) z == o
  }
  for (o in opts) {
    bs <- binary_stats(memb(x, o), memb(y, o))
    if (bs$a + bs$b + bs$c == 0L) next          # option never used by either rater
    opt_rows[[length(opt_rows) + 1L]] <- data.frame(
      variable = v, concept = V2C$concept[match(v, V2C$variable)],
      task = vtask_of(v), multiselect = v %in% MULTI,
      option = o, a = bs$a, b = bs$b, c = bs$c, d = bs$d, N = bs$N,
      p0 = bs$p0, p_pos = bs$p_pos, p_neg = bs$p_neg,
      PI = bs$PI, BI = bs$BI, abs_BI = abs(bs$BI), PABAK = bs$PABAK,
      kappa = bs$kappa, kappa_se = bs$kappa_se, AC1 = bs$AC1,
      f1_minus_f2 = bs$marg_imbalance, ppos_minus_pneg = bs$ppos_minus_pneg,
      swing_product = bs$swing, swing_scaled = bs$swing_scaled,
      w_pos = bs$w_pos, w_neg = bs$w_neg,
      stringsAsFactors = FALSE)
  }
}
OPT <- do.call(rbind, opt_rows)
OPT$label  <- CMAP$label[match(OPT$concept, CMAP$concept)]
OPT$domain <- CMAP$dom[match(OPT$concept, CMAP$concept)]
OPT <- OPT[order(match(OPT$domain, DOMS),
                 CMAP$concept_ord[match(OPT$concept, CMAP$concept)],
                 OPT$task, -OPT$a), ]
## every single-select item's option-level 'a' cells must sum to its agreements
chkA <- tapply(OPT$a[!OPT$multiselect], OPT$variable[!OPT$multiselect], sum)
chkB <- setNames(ITEM$n_agree, ITEM$variable)[names(chkA)]
stopifnot(all(chkA == chkB))
cat("[check] option-level agreement cells reconcile with item-level agreements\n")

###############################################################################
## 5.  TABLE 3 -- the difficulty ranking, RE-DERIVED
##     Byrt, Bishop & Carlin: "if kappa alone is reported it is misleading to
##     compare kappas for raters between situations where the average prevalence
##     is considerably different."  Our items' prevalences differ enormously
##     (modal share runs from about a half to 1.00), so the existing
##     kappa-ranked "hardest items" list is exactly the comparison they warn
##     against.  Rank on p0 instead, carry PI, and treat movement as a finding.
##
##     TWO SEPARATE CORRECTIONS ARE AT ISSUE and the table reports both.
##     (i) DENOMINATOR.  The 2026-07 record ranked items by disagreement over
##         ASSESSED cells, pooling the applicability disputes.  Checked against
##         the record's own figures (causal_err_disc 70.7, descriptive_val_
##         outcome 68.2, causal_ltfu_bias 66.3, descriptive_err_disc 62.4;
##         reproduced here as 71.2 / 68.6 / 65.6 / 61.6, the residual being
##         377 vs 385 papers), so that list was NOT kappa-ranked -- contrary to
##         what SENSITIVITY_ANALYSIS_PLAN 1c currently says.  Its defect is the
##         pooled denominator, which inflates branch-conditional items:
##         causal_ltfu_bias falls from 65.6% to 52.9% disagreement, and from
##         3rd hardest to 7th, once applicability disputes are removed.
##     (ii) INDEX.  Byrt's warning still binds any kappa-based ranking, and it
##         binds hard here: three items with kappa at or below zero have p0
##         above 0.96.  Ranking by kappa would call the instrument's three
##         EASIEST items its hardest.
###############################################################################
MIN_N <- 20L
R <- ITEM[ITEM$n_both >= MIN_N, ]
R$rank_p0    <- rank(R$p0, ties.method = "min")                 # 1 = hardest
R$rank_kappa <- rank(ifelse(is.na(R$kappa), Inf, R$kappa), ties.method = "min")
R$rank_dis_assessed <- rank(-R$dis_pct_assessed, ties.method = "min")   # the record's
R$rank_move  <- R$rank_kappa - R$rank_p0     # >0: kappa made the item look harder
R$rank_move_denom <- R$rank_dis_assessed - R$rank_p0   # effect of pooling disputes
## worst-handled option within each item: the lowest positive agreement over the
## item's options, which is where an improvement effort should actually go.
worst <- do.call(rbind, lapply(split(OPT, OPT$variable), function(z) {
  z2 <- z[!is.na(z$p_pos) & (z$a + z$b + z$c) >= 5L, ]
  if (!nrow(z2)) return(NULL)
  w <- z2[which.min(z2$p_pos), ]
  data.frame(variable = w$variable, worst_option = w$option,
             worst_p_pos = w$p_pos, worst_option_n_pos = w$a + w$b + w$c,
             stringsAsFactors = FALSE)
}))
R <- merge(R, worst, by = "variable", all.x = TRUE)
R <- R[order(R$rank_p0), ]
RANK <- R[, c("rank_p0","rank_kappa","rank_dis_assessed","rank_move","rank_move_denom",
              "variable","label","task","domain",
              "n_both","n_applic_dispute","p0","p0_lo","p0_hi","dis_pct_assessed",
              "kappa","kappa_lo_boot","kappa_hi_boot",
              "kappa_n_free_marginal","AC1","q_used","modal_category","modal_share",
              "PI_modal","BI_modal","worst_option","worst_p_pos","worst_option_n_pos")]

###############################################################################
## 6.  SECTION 2 -- the observed bound on CONCORDANT error
##
##  The design adjudicated a cell only when the two reviewers DISAGREED, so the
##  5,021 agreed cells were, by construction, never checked.  That is why the
##  plan calls pr(V+ | R1 = R2) = 0 a positivity violation.
##
##  It is not quite 0.  The 2026-08 consistency sweep flagged cells by LOGICAL
##  CONTRADICTION rather than by disagreement, and 34 of the flagged cells sit
##  in the agreed stratum.  TSA and YA ruled on every one of them against the
##  full text.  That is a genuine -- if tiny and non-randomly selected --
##  verified subsample of the stratum the design otherwise leaves dark, and it
##  is the only direct evidence we have about concordant error.
###############################################################################
cells0$key <- paste(cells0$PMID, cells0$variable)
task_of <- setNames(cells0$Study_Type[!duplicated(cells0$PMID)],
                    cells0$PMID[!duplicated(cells0$PMID)])
PREF <- c(Causal = "causal_", Descriptive = "descriptive_", Predictive = "predictive_")

wl <- as.data.frame(suppressMessages(read_excel(
  f("data/quality-control/08_08_2026_inconsistency_resolution_worklist.xlsx"),
  sheet = "resolution_worklist", col_types = "text")))
names(wl)[names(wl) == "TSA + YA decision"] <- "decision"
names(wl)[names(wl) == "Current value"]     <- "current"
wl$variable <- paste0(PREF[task_of[wl$PMID]], wl$Item)
wl$key      <- paste(wl$PMID, wl$variable)
wl$stratum  <- cells0$status[match(wl$key, cells0$key)]
wl$agreed_answer <- cells0$r1[match(wl$key, cells0$key)]
wl$final_in_data <- cells0$final[match(wl$key, cells0$key)]

## rows whose Item is not a single tool variable (project-level rulings, the
## RCT ITT/PP screen, and two composite "design/follow" rows) do not name a
## cell and are excluded from the cell-level bound; recorded for the audit.
wl$unmatched <- is.na(wl$stratum)

applied <- read.csv(f("data/quality-control/08_12_2026_worklist_apply_log.csv"),
                    colClasses = "character")
applied$key <- paste(applied$PMID, applied$variable)

VER <- wl[which(wl$stratum == "Reviewers agreed"), ]
VER$was_changed <- VER$key %in% applied$key
## "It should be skipped" = TSA+YA judged the item inapplicable, i.e. both
## reviewers answered a question the branch logic should never have asked.
## That is a concordant error whether or not the value was later edited; 16 of
## the 17 are pure-randomization papers that Table 2's N/A rule drops anyway,
## and the 17th is logged in the caveats register as C6.
VER$verdict <- ifelse(VER$was_changed, "overturned (answer replaced)",
               ifelse(grepl("should be skipped", VER$decision, ignore.case = TRUE),
                      "overturned (item should have been skipped)", "upheld"))
VER$error_type <- ifelse(VER$verdict == "upheld", "none", "judgment")

n_ver   <- nrow(VER)
n_wrong <- sum(VER$verdict != "upheld")
n_up    <- sum(VER$verdict == "upheld")
stopifnot(n_ver == n_up + n_wrong)

## concordant OMISSION is a different failure and gets its own denominator:
## a skip-logic GAP is both reviewers leaving blank an item the branch logic
## says applies, which lands in the not-applicable-to-either stratum.
gap <- wl[which(wl$Rule == "GAP" & wl$stratum == "Not applicable to either reviewer"), ]
n_na_stratum <- sum(cells0$status == "Not applicable to either reviewer")

## DETECTION COVERAGE.  A concordant WRONG ANSWER can only be caught by one of
## the 28 soft consistency rules, since those are the only checks that compare
## an answer against another answer.  Hard skip logic reaches further items but
## detects a missing or surplus answer, not a wrong one, so it does not extend
## coverage for the purpose of this bound.  Derive the covered set from the rule
## catalogue itself rather than asserting it by hand.
soft <- as.data.frame(suppressMessages(read_excel(
  f("data/quality-control/07_16_2026_soft_dependencies_catalogue.xlsx"),
  sheet = "all_rules", col_types = "text")))
rule_txt <- paste(soft$rule, collapse = " || ")
ALIAS <- c(hand_miss_outcom = "hand_miss_outcome")   # catalogue spells it in full
covered_concept <- vapply(CMAP$concept, function(cc) {
  pat <- paste0("(^|[^a-z_])", ifelse(cc %in% names(ALIAS), ALIAS[[cc]], cc), "([^a-z_]|$)")
  grepl(pat, rule_txt)
}, logical(1))
COV <- data.frame(concept = CMAP$concept, label = CMAP$label, domain = CMAP$dom,
                  rule_covered = covered_concept, stringsAsFactors = FALSE)
ITEM$rule_covered <- COV$rule_covered[match(ITEM$concept, COV$concept)]
n_agree_cov   <- sum(ITEM$n_agree[ITEM$rule_covered])
n_agree_uncov <- sum(ITEM$n_agree[!ITEM$rule_covered])
stopifnot(n_agree_cov + n_agree_uncov == 5021L)

SEC2 <- VER[, c("PMID","variable","Rule","Category","decision","agreed_answer",
                "final_in_data","was_changed","verdict","error_type")]
SEC2 <- SEC2[order(SEC2$Rule, SEC2$variable, SEC2$PMID), ]

###############################################################################
## 7.  WRITE
###############################################################################
w <- function(d, nm) {
  p <- file.path(TBL, sprintf("%s_%s.csv", STAMP, nm))
  write.csv(d, p, row.names = FALSE, na = "")
  cat(sprintf("  wrote %-42s %4d rows\n", basename(p), nrow(d)))
}
num <- function(d) { for (nm in names(d)) if (is.numeric(d[[nm]]) && !is.integer(d[[nm]]))
                       d[[nm]] <- p3(d[[nm]]); d }
cat("\n[write]\n")
w(num(ITEM[, c("domain","label","variable","task","multiselect","rule_covered",
               "n_both","n_agree","n_applic_dispute","q_used",
               "p0","p0_lo","p0_hi","dis_pct_assessed",
               "kappa","kappa_se","kappa_lo_asym","kappa_hi_asym",
               "kappa_lo_boot","kappa_hi_boot",
               "kappa_weighted_ordinal","kappa_unweighted_ordinal_subset","n_ordinal_subset",
               "kappa_n_free_marginal","AC1","modal_category","modal_share",
               "PI_modal","BI_modal","PABAK_modal","p_pos_modal","p_neg_modal")]),
  "agreement_item_level")
w(num(OPT[, c("domain","label","variable","task","multiselect","option",
              "a","b","c","d","N","p0","p_pos","p_neg","PI","BI","abs_BI","PABAK",
              "kappa","kappa_se","AC1","f1_minus_f2","ppos_minus_pneg","swing_product",
              "swing_scaled","w_pos","w_neg")]),
  "agreement_option_level")
w(num(RANK), "agreement_difficulty_ranking")
w(SEC2, "concordant_error_bound")
w(COV,  "agreement_rule_coverage")

###############################################################################
## 8.  SUMMARY
###############################################################################
pc <- function(x, y) sprintf("%.1f%%", 100 * x / y)
hard_k <- head(RANK[order(ifelse(is.na(RANK$kappa), Inf, RANK$kappa)), ], 6)
hard_p <- head(RANK, 6)

md <- c(
"# Tier 1b and Section 2 -- results",
"",
sprintf("Generated %s by `code/scoring/%s_agreement_sensitivity_tier1.R`.", STAMP, STAMP),
"Plan: `docs/SENSITIVITY_ANALYSIS_PLAN.md` sections 1b, 1c, 1d, 1e, 2.",
"",
"## Denominators",
"",
sprintf("- Grid %s cells (385 papers x 47 items); %s not applicable to either reviewer.",
        format(nrow(cells0), big.mark = ","), format(n_na_stratum, big.mark = ",")),
sprintf("- Assessed %s. Both-answered **%s** (agreement is computed on these).",
        format(7278L, big.mark = ","), format(nrow(cells), big.mark = ",")),
sprintf("- Agreed %s (%s of both-answered, %s of assessed).",
        format(5021L, big.mark = ","), pc(5021, nrow(cells)), pc(5021, 7278)),
sprintf("- Applicability disputes %d, held in their own column, never pooled.", 483L),
"",
"## Delimiter rule (plan 1e open item -- CLOSED)",
"",
"No reviewer answer to any of the five select-all items contains a comma;",
"the only comma in that column sits inside an option label. `;`-only splitting",
"is therefore correct for every reviewer-level statistic, and the",
"`\"Random error, Selection bias;Confounding bias\"` string that motivated the",
"proposed comma rule appears only among the adjudicated values, in one cell.",
"**The plan's proposed \"split err_disc on ; and ,\" rule should be withdrawn.**",
"",
"## The difficulty ranking",
"",
sprintf("Ranked over the %d items with at least %d both-answered cells.", nrow(RANK), MIN_N),
"",
"**Correction to plan section 1c.** The plan states that the current record ranks",
"hardest items by kappa. It does not. The recorded figures (causal_err_disc 70.7,",
"descriptive_val_outcome 68.2, causal_ltfu_bias 66.3, descriptive_err_disc 62.4) are",
sprintf("disagreement rates over ASSESSED cells; this script reproduces them as %.1f / %.1f / %.1f / %.1f",
        RANK$dis_pct_assessed[match("causal_err_disc", RANK$variable)],
        RANK$dis_pct_assessed[match("descriptive_val_outcome", RANK$variable)],
        RANK$dis_pct_assessed[match("causal_ltfu_bias", RANK$variable)],
        RANK$dis_pct_assessed[match("descriptive_err_disc", RANK$variable)]),
"on 385 papers against the record's 377. So the recorded list is not a kappa misuse.",
"Its actual defect is the DENOMINATOR: it pools the applicability disputes, which the",
"plan's own section 1b forbids, and that inflates branch-conditional items.",
sprintf("`causal_ltfu_bias` falls from %.1f%% to %.1f%% disagreement and from rank %d to rank %d",
        RANK$dis_pct_assessed[match("causal_ltfu_bias", RANK$variable)],
        100 * (1 - RANK$p0[match("causal_ltfu_bias", RANK$variable)]),
        RANK$rank_dis_assessed[match("causal_ltfu_bias", RANK$variable)],
        RANK$rank_p0[match("causal_ltfu_bias", RANK$variable)]),
"once the disputes are removed.",
"",
"Byrt's warning nonetheless binds any kappa-based ranking, and it binds hard here:",
"three items with kappa at or below zero have p0 above 0.96, so ranking on kappa would",
"call the instrument's easiest items its hardest. Both orderings are given below.",
"",
"Hardest by kappa (the ordering to avoid):",
"",
paste0("| item | task | n | p0 | kappa | modal share | PI |"),
paste0("|---|---|---|---|---|---|---|"),
paste(sprintf("| %s | %s | %d | %.3f | %s | %.2f | %+.2f |",
      hard_k$label, hard_k$task, hard_k$n_both, hard_k$p0,
      ifelse(is.na(hard_k$kappa), "n/a", sprintf("%.3f", hard_k$kappa)),
      hard_k$modal_share, hard_k$PI_modal), collapse = "\n"),
"",
"Hardest by p0 (the re-derived ranking):",
"",
paste0("| item | task | n | p0 | kappa | modal share | PI |"),
paste0("|---|---|---|---|---|---|---|"),
paste(sprintf("| %s | %s | %d | %.3f | %s | %.2f | %+.2f |",
      hard_p$label, hard_p$task, hard_p$n_both, hard_p$p0,
      ifelse(is.na(hard_p$kappa), "n/a", sprintf("%.3f", hard_p$kappa)),
      hard_p$modal_share, hard_p$PI_modal), collapse = "\n"),
"",
sprintf("Largest rank movements (kappa rank minus p0 rank): %s.",
        paste(sprintf("%s %+d", head(RANK[order(-abs(RANK$rank_move)), ]$label, 5),
                      head(RANK[order(-abs(RANK$rank_move)), ]$rank_move, 5)), collapse = "; ")),
"",
"## The kappa paradox, in our own data",
"",
"Three items carry a kappa at or below zero together with a p0 above 0.96:",
"",
paste0("| item | task | n | p0 | kappa | kappa_n | AC1 | PI | p_pos | p_neg |"),
paste0("|---|---|---|---|---|---|---|---|---|---|"),
paste(local({
  z <- ITEM[ITEM$n_both >= MIN_N & !is.na(ITEM$kappa) & ITEM$kappa <= 0.001 & ITEM$p0 > 0.9, ]
  z <- z[order(z$kappa), ]
  sprintf("| %s | %s | %d | %.3f | %+.3f | %.3f | %.3f | %+.3f | %.3f | %.3f |",
          z$label, z$task, z$n_both, z$p0, z$kappa, z$kappa_n_free_marginal, z$AC1,
          z$PI_modal, z$p_pos_modal, z$p_neg_modal)
}), collapse = "\n"),
"",
"These are the items where the reviewers agreed almost perfectly on the answer that",
"nearly every paper gets, and never agreed on the rare one -- p_neg is exactly 0.000 in",
"all three. Cicchetti and Feinstein tell us not to read that as good performance and not",
"to read the kappa as bad performance: it is a prevalence artefact, and the honest",
"presentation is the pair. The free-marginal bracket is correspondingly enormous,",
"kappa and kappa_n spanning roughly -0.02 to 0.93 on the same cells, which is itself the",
"argument for reporting both rather than picking the flattering one.",
"",
"## Select-all items: exact-set matching manufactures the hardest item in the instrument",
"",
sprintf("`causal_err_disc` is the worst item by p0 (%.3f) only because a cell counts as agreement",
        ITEM$p0[ITEM$variable == "causal_err_disc"]),
"only when the two reviewers tick an identical set of six options. Decomposed per option,",
"the same cells look ordinary:",
"",
paste0("| option | a | b | c | d | p0 | p_pos | p_neg | kappa | AC1 |"),
paste0("|---|---|---|---|---|---|---|---|---|---|"),
paste(local({
  z <- OPT[OPT$variable == "causal_err_disc", ]; z <- z[order(-(z$a + z$b + z$c)), ]
  sprintf("| %s | %d | %d | %d | %d | %.3f | %.3f | %.3f | %+.3f | %.3f |",
          z$option, z$a, z$b, z$c, z$d, z$p0, z$p_pos, z$p_neg, z$kappa, z$AC1)
}), collapse = "\n"),
"",
sprintf("Per-option p0 runs %.2f to %.2f against the exact-set %.2f. The item is not uniformly",
        min(OPT$p0[OPT$variable == "causal_err_disc"]),
        max(OPT$p0[OPT$variable == "causal_err_disc"]),
        ITEM$p0[ITEM$variable == "causal_err_disc"]),
"hard: it has one badly broken option. Reviewers essentially never co-identify a mention of",
sprintf("random error (a = %d against b = %d and c = %d, p_pos = %.3f), while measurement bias,",
        OPT$a[OPT$variable == "causal_err_disc" & OPT$option == "random error"],
        OPT$b[OPT$variable == "causal_err_disc" & OPT$option == "random error"],
        OPT$c[OPT$variable == "causal_err_disc" & OPT$option == "random error"],
        OPT$p_pos[OPT$variable == "causal_err_disc" & OPT$option == "random error"]),
"selection bias and none-of-the-above sit near p0 = 0.65. That is a diagnosis of one",
"option's wording, not a verdict on the construct, and it is the actionable form of the",
"finding Cicchetti and Feinstein say a study like ours should be producing.",
"",
"## The bias index: magnitude only, never sign",
"",
"Byrt et al. ask for BI to be assessed first, and if substantial bias is present, for it to",
"be investigated before any agreement index is quoted. BI is reported per option, but in",
"this design **only its magnitude carries meaning**. BI = (b - c)/N is defined relative to",
"which reviewer occupies the first column, and our first and second columns are ordered by",
"reviewer ID, so column position is confounded with reviewer identity by construction --",
"the same confound already documented for the adjudication position check. A positive BI",
"says the two reviewers applied the item asymmetrically; it does not say who was stricter.",
"",
sprintf("Largest |BI| among options with at least 50 discordant-or-positive cells: %s.",
        paste(local({
          z <- OPT[(OPT$a + OPT$b + OPT$c) >= 50, ]
          z <- z[order(-z$abs_BI), ][1:5, ]
          sprintf("%s / %s (BI %+.3f)", z$variable, substr(z$option, 1, 28), z$BI)
        }), collapse = "; ")),
"",
"## Ordinal items: weighting helps, modestly",
"",
"Linearly weighted kappa is computed on the on-ladder subset only (No < content/face <",
"criterion); the fourth option, 'does not usually require validation', is an applicability",
"judgment rather than a rung, and forcing it onto the scale would fabricate a distance the",
"instrument never defines. The unweighted kappa on that same subset is given beside it so",
"the comparison isolates weighting from subsetting:",
"",
paste0("| item | n (all) | n (on-ladder) | kappa (all) | kappa unweighted (subset) | kappa weighted (subset) |"),
paste0("|---|---|---|---|---|---|"),
paste(local({
  z <- ITEM[ITEM$variable %in% ORDINAL, ]
  sprintf("| %s (%s) | %d | %d | %.3f | %.3f | %.3f |", z$label, z$task, z$n_both,
          z$n_ordinal_subset, z$kappa, z$kappa_unweighted_ordinal_subset,
          z$kappa_weighted_ordinal)
}), collapse = "\n"),
"",
"## Section 2 -- concordant error",
"",
sprintf("- The agreed stratum is **not** entirely unverified: **%d of %s agreed cells (%s)** were",
        n_ver, format(5021L, big.mark = ","), pc(n_ver, 5021)),
"  ruled on by TSA and YA during the consistency sweep, which flagged cells by",
"  logical contradiction rather than by reviewer disagreement.",
sprintf("- Of those %d, **%d were overturned and %d upheld** (%s overturned).",
        n_ver, n_wrong, n_up, pc(n_wrong, n_ver)),
sprintf("  %d were answers replaced outright; %d were items TSA and YA judged should have been skipped.",
        sum(VER$verdict == "overturned (answer replaced)"),
        sum(VER$verdict == "overturned (item should have been skipped)")),
sprintf("- All %d overturned cells are judgment errors, not clerical: none is a transcription slip.", n_wrong),
"",
sprintf("So the observed data bracket concordant error between **%s** (the lower bound,",
        pc(n_wrong, 5021)),
sprintf("%d of all %s agreed cells) and **%s** (the rate inside the verified subsample).",
        n_wrong, format(5021L, big.mark = ","), pc(n_wrong, n_ver)),
"Neither end is an estimate. The lower bound assumes every unflagged agreed cell is",
"correct, which is false by construction. The upper figure comes from cells selected",
"precisely for being anomalous, so it is an extreme only under the assumption that",
"flagged cells are more error-prone than unflagged ones -- the same monotonicity",
"caveat the plan already attaches to the 15.4% adjudicator-override anchor.",
"",
"### Detection coverage -- why the lower bound is weak",
"",
sprintf("- %d of the %d tool concepts appear in none of the 28 soft consistency rules, and they carry",
        sum(!COV$rule_covered), nrow(COV)),
sprintf("  **%s of the %s agreed cells (%s)**. Hard skip logic touches some of them but can only",
        format(n_agree_uncov, big.mark = ","), format(5021L, big.mark = ","),
        pc(n_agree_uncov, 5021)),
"  flag a missing or surplus answer, never a wrong one, so it does not extend coverage here.",
sprintf("  Uncovered: %s.", paste(COV$label[!COV$rule_covered], collapse = "; ")),
"- `Errors qualitatively mentioned in the discussion` -- the worst-agreeing item in the",
"  instrument -- has no rule coverage at all, so Section 2 is structurally blind to it.",
"- Consistency rules detect logical incoherence, not coherent-but-wrong judgment, and",
"  two reviewers misreading an item the same way produces internally consistent output.",
"  The mechanism of concern is the one this method cannot see.",
"",
sprintf("### Concordant omission (reported separately)"),
sprintf("- %d skip-logic GAPs are cells both reviewers left blank that the branch logic says",
        nrow(gap)),
sprintf("  applied: %s of the %s not-applicable-to-either cells. This is a concordant failure",
        pc(nrow(gap), n_na_stratum), format(n_na_stratum, big.mark = ",")),
"  to answer, not a concordant wrong answer, so it is not folded into the rate above.",
"",
"## Consequence for the plan",
"",
"Section 3 says pr(V+ | R1 = R2) = 0 and calls the failure a positivity violation.",
"That is very nearly right but should be stated more precisely: positivity holds on",
sprintf("the rule-flagged subset of the agreed stratum (%d cells) and fails everywhere else.",
        n_ver),
"The design still satisfies Begg and Greenes' conditional-independence condition.",
sprintf("The %s overturn rate in that subsample is also a better-placed anchor for the", pc(n_wrong, n_ver)),
"elicited priors on epsilon_0 and epsilon_1 than the 15.4% adjudicator-override figure,",
"because it is measured in the agreed stratum rather than the disagreed one.",
"")
writeLines(md, file.path(REP, sprintf("%s_agreement_sensitivity_tier1_summary.md", STAMP)))
cat(sprintf("  wrote %s_agreement_sensitivity_tier1_summary.md\n", STAMP))

cat("\n[section 2]\n")
cat(sprintf("  verified agreed cells       : %d\n", n_ver))
cat(sprintf("  overturned / upheld         : %d / %d  (%s overturned)\n",
            n_wrong, n_up, pc(n_wrong, n_ver)))
cat(sprintf("  lower bound on epsilon      : %d / 5021 = %s\n", n_wrong, pc(n_wrong, 5021)))
cat(sprintf("  agreed cells with no rule   : %d (%s)\n", n_agree_uncov, pc(n_agree_uncov, 5021)))
cat(sprintf("  concordant omissions (GAPs) : %d / %d = %s\n", nrow(gap), n_na_stratum,
            pc(nrow(gap), n_na_stratum)))
cat("\ndone.\n")

###############################################################################
## 8.  COLLAPSED BY CONCEPT -- the same statistics, NOT stratified by task
##     Added 2026-08-22 at TSA's request, for the un-stratified variant of
##     Supplementary Figure S10 panel A.
##
##  WHY THIS IS A SEPARATE TABLE AND NOT A REPLACEMENT
##  Sections 3-7 above are the analysis; this is a presentation variant.  The
##  instrument asks several questions of more than one task, and the item-level
##  table therefore carries them twice (descriptive_sampling and
##  causal_sampling are one concept, "Sampling technique", asked of two study
##  types).  Collapsing gives one row per concept and a shorter, more readable
##  figure, at the cost of hiding that agreement on the SAME question can
##  differ by task -- and it does: "errors qualitatively mentioned in the
##  discussion" runs p0 = 0.30 on causal papers against 0.41 on descriptive.
##  The collapsed p0 is the n-weighted average of those, which is a real
##  quantity but a different one.  Both tables are published; the figure names
##  which it is showing.
##
##  ⚠ APPENDED AFTER EVERY OTHER WRITE, ON PURPOSE.  Nothing above depends on
##  anything here, so the four published tables and the summary reproduce
##  byte for byte with or without this section (verified 2026-08-22).  The seed
##  is re-set so the collapsed bootstrap does not depend on how many draws the
##  sections above happened to consume.
##
##  WRITES  outputs/tables/08_22_2026_agreement_collapsed_by_concept.csv
###############################################################################
set.seed(20260822L)
STAMP2 <- "08_22_2026"

## A concept inherits the awkward properties of its constituent items: if any
## variant is a multiselect it cannot take a free-marginal kappa_n, and if any
## is ordinal the pooled table mixes ladders, so weighted kappa is not carried
## over at all (the item-level table remains the place to read it).
conc_rows <- lapply(CMAP$concept, function(cc) {
  vs <- V2C$variable[V2C$concept == cc]
  s  <- cells[cells$concept == cc, ]
  x  <- s$r1n; y <- s$r2n; N <- nrow(s)
  if (N == 0L) return(NULL)
  p0 <- mean(x == y)
  kk <- kappa_full(x, y)
  ac <- ac1_stat(x, y)
  kn <- if (any(vs %in% MULTI)) NA_real_ else kappa_n(p0, kk$q)
  ci_p0 <- boot_ci(function(ix) mean(x[ix] == y[ix]), N)
  ci_k  <- boot_ci(function(ix) kappa_full(x[ix], y[ix])$kappa, N)
  allr  <- c(x, y); tb <- sort(table(allr), decreasing = TRUE)
  modal <- names(tb)[1]
  bsm   <- binary_stats(x == modal, y == modal)
  tsk   <- vapply(vs, vtask_of, character(1))
  ## per-task cell counts, so a reader can see what the pooling is made of
  nbt <- vapply(vs, function(v) sum(cells$variable == v), integer(1))
  data.frame(
    concept = cc,
    label   = CMAP$label[match(cc, CMAP$concept)],
    domain  = CMAP$dom[match(cc, CMAP$concept)],
    dom_ord = CMAP$dom_ord[match(cc, CMAP$concept)],
    conc_ord = CMAP$concept_ord[match(cc, CMAP$concept)],
    n_items = length(vs),
    tasks   = paste(substr(tsk[nbt > 0], 1, 1), collapse = "+"),
    n_by_task = paste(sprintf("%s:%d", substr(tsk[nbt > 0], 1, 1), nbt[nbt > 0]),
                      collapse = " "),
    n_both  = N,
    n_applic_dispute = sum(as.integer(n_applic[vs]), na.rm = TRUE),
    n_agree = sum(x == y),
    q_used  = kk$q,
    p0 = p0, p0_lo = ci_p0[1], p0_hi = ci_p0[2],
    dis_pct_assessed = 100 * (1 - sum(x == y) /
                              (N + sum(as.integer(n_applic[vs]), na.rm = TRUE))),
    kappa = kk$kappa, kappa_lo_boot = ci_k[1], kappa_hi_boot = ci_k[2],
    kappa_n_free_marginal = kn, AC1 = ac,
    modal_category = modal, modal_share = as.numeric(tb[1]) / (2 * N),
    PI_modal = bsm$PI, BI_modal = bsm$BI,
    any_multiselect = any(vs %in% MULTI), any_ordinal = any(vs %in% ORDINAL),
    stringsAsFactors = FALSE)
})
CONC <- do.call(rbind, conc_rows)

## The collapse must conserve cells: every both-answered cell lands in exactly
## one concept, and every applicability dispute is counted once.
stopifnot(sum(CONC$n_both) == sum(ITEM$n_both), sum(CONC$n_both) == 6795L,
          sum(CONC$n_agree) == 5021L,
          sum(CONC$n_applic_dispute) == 483L,
          nrow(CONC) == length(unique(V2C$concept)))
## and the collapsed p0 must be the n-weighted mean of the item-level p0s
chk_w <- vapply(CONC$concept, function(cc) {
  z <- ITEM[ITEM$concept == cc, ]; sum(z$p0 * z$n_both) / sum(z$n_both) }, numeric(1))
stopifnot(max(abs(chk_w - CONC$p0)) < 1e-9)

CONC <- CONC[order(CONC$p0, CONC$label), ]
CONC$rank_p0 <- rank(CONC$p0, ties.method = "min")
CONC$below_min_n <- CONC$n_both < MIN_N          # same threshold as the ranking table
for (cl in c("p0","p0_lo","p0_hi","kappa","kappa_lo_boot","kappa_hi_boot",
             "kappa_n_free_marginal","AC1","modal_share","PI_modal","BI_modal",
             "dis_pct_assessed"))
  CONC[[cl]] <- p3(CONC[[cl]])
write.csv(CONC, file.path(TBL, paste0(STAMP2, "_agreement_collapsed_by_concept.csv")),
          row.names = FALSE)
cat(sprintf("\n[8] collapsed by concept: %d concepts from %d items; %d below n=%d\n",
            nrow(CONC), nrow(ITEM), sum(CONC$below_min_n), MIN_N))
cat(sprintf("    p0 range %.3f to %.3f; hardest: %s (%.3f)\n",
            min(CONC$p0), max(CONC$p0), CONC$label[1], CONC$p0[1]))

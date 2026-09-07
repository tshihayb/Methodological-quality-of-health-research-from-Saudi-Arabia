###############################################################################
##  CONCORDANT REVIEWER ERROR, MEASURED FROM THE CALIBRATION ROUNDS
##
##  Project : Assessment of Healthcare Research Quality in Saudi Arabia
##  Plan    : docs/SENSITIVITY_ANALYSIS_PLAN.md section 3
##  Date    : 2026-08-19
##  Run FROM THE REPOSITORY ROOT.
##
##  WHY THIS EXISTS
##  The main study adjudicated a cell ONLY when the two reviewers disagreed, so
##  P(both wrong | both agreed) is not estimable there -- the positivity problem
##  that section 3 was going to answer with expert elicitation.  The calibration
##  rounds do not have that problem: EVERY cell was adjudicated by TSA and YA
##  regardless of whether the reviewers agreed.  Complete verification, same
##  reference standard as the main study, same instrument family.  Lash et al.
##  (Int J Epidemiol 2014;43:1969-85) rank validation data above elicitation and
##  warn that "direct expert elicitations are unlikely to provide reliably
##  accurate estimates", so this supersedes the elicitation as the primary source.
##
##  METHOD
##  For every (paper, item): form all reviewer PAIRS that gave the same answer,
##  and check that agreed answer against the adjudicated reference.  The rate of
##  agreeing-but-wrong pairs is a direct estimate of concordant error.  Pairs are
##  clustered within paper, so intervals are bootstrapped over PAPERS (10 in
##  round 1, 3 in round 2), never over pairs.
##
##  SETTLED DECISIONS (TSA, 2026-08-19)
##   * Reviewer 3 (R-withdrawn bin Hammad) EXCLUDED -- he quit; his 55 papers were
##     redistributed and his 3 pilot reviews were redone by others, so his error
##     rate cannot inform a parameter about the 13 reviewers who did the study.
##     14 IDs were issued, 3 was never reused, so the active set is 1,2,4..14.
##   * The "new reviewer 5" export is canonical for round 1.
###############################################################################

suppressPackageStartupMessages({ library(readxl) })

PROJ  <- getwd()
STAMP <- "08_19_2026"
TBL   <- file.path(PROJ, "outputs", "tables")
stopifnot(dir.exists(TBL))
set.seed(20260819L)
B_BOOT <- 2000L

f  <- function(p) file.path(PROJ, p)
rd <- function(p) as.data.frame(suppressMessages(read_excel(f(p), sheet = 1, col_types = "text")))
## ⚠ The two readers disambiguate duplicate column names DIFFERENTLY, and the
## tool repeats question text across task branches, so this matters:
##   readxl (.xlsx) appends the column position -> "What was the study design?...19"
##   read.csv (.csv) appends an occurrence index -> "What was the study design?.1"
## and read.csv does that even with check.names = FALSE. Strip both forms, or the
## round-2 progress CSV never matches the round-2 adjudication workbook.
## No tool question ends in a full stop followed by digits, so this is unambiguous.
base_nm <- function(x) sub("[.][0-9]+$", "", sub("[.][.][.][0-9]+$", "", x))
keyof   <- function(nm) { b <- base_nm(nm); paste0(b, "##", ave(b, b, FUN = seq_along)) }

DROP_REVIEWERS <- "3"

norm1 <- function(v) {
  s <- ifelse(is.na(v), "", as.character(v))
  s <- gsub("\\s+", " ", trimws(tolower(s))); s[s == "nan"] <- ""
  ix <- grepl(";", s, fixed = TRUE)
  if (any(ix)) s[ix] <- vapply(s[ix], function(z) {
    p <- trimws(strsplit(z, ";", fixed = TRUE)[[1]]); p <- p[nzchar(p)]
    paste(sort(p, method = "radix"), collapse = ";") }, character(1))
  s
}

###############################################################################
## 1.  THE CROSSWALK  (calibration column position -> final tool variable)
##
##  status:
##   direct   - same question, same option set, survives into the final tool.
##              These carry the estimate.
##   changed  - present in the final tool but the option set or wording moved
##              between calibration and the final version, per the two
##              "List of changes to the tool" documents. Reported separately;
##              a calibration-era error rate here is not transferable.
##   dropped  - the question does not exist in the final tool at all.
##   confirm  - mapping is a judgment call. NOT used in the estimate until TSA
##              confirms. Printed at the end of the run for review.
###############################################################################

## ---- ROUND 2 (tool version 6, 52 columns, closest to the final instrument) ---
XW2 <- read.csv(text = "col|variable|status
 3|recusal|direct
 4|task|direct
 5|descriptive_design|direct
 6|descriptive_pop|direct
 7|descriptive_sampling|direct
 8|descriptive_sample_size|direct
 9|descriptive_acc_sampl|direct
10|descriptive_sample_ach|direct
11|descriptive_base_sel|direct
12|descriptive_outcome_type|direct
13|descriptive_val_outcome|direct
14|descriptive_out_bias_acc|direct
15|descriptive_miss_outcome|direct
16|descriptive_hand_miss_outcom|direct
17|descriptive_err_disc|direct
18|descriptive_confl_task|direct
19|predictive_design|direct
20|predictive_pop|direct
21|causal_design|direct
22|causal_pop|direct
23|causal_sampling|direct
24|causal_sample_size|direct
25|causal_acc_sampl|direct
26|causal_sample_ach|direct
27|NA_selective_invitation|dropped
28|causal_base_sel|confirm
29|causal_comp_dis|direct
30|causal_ltfu_bias|direct
31|causal_ltfu_acc|direct
32|causal_exposure_type|direct
33|causal_val_exposure|direct
34|causal_diff_or_nondiff_exp|direct
35|causal_exp_bias_acc|direct
36|causal_outcome_type|direct
37|causal_val_outcome|direct
38|causal_diff_or_nondiff_out|direct
39|causal_out_bias_acc|direct
40|causal_dep_or_indep_misc|direct
41|causal_base_conf_meth|direct
42|NA_baseline_confounding_present|dropped
43|causal_tv_conf_meth|direct
44|causal_time_verying|confirm
45|causal_conf_var_det|direct
46|causal_miss_exposure|direct
47|causal_hand_miss_exposure|direct
48|causal_miss_outcome|direct
49|causal_hand_miss_outcom|direct
50|causal_err_disc|direct
", sep = "|", header = TRUE, strip.white = TRUE, stringsAsFactors = FALSE)

## ---- ROUND 1 (tool version 4, 60 columns after dropping Title) --------------
##  Differences from round 2, taken from round-2's "List of changes to tool":
##  complete-case questions removed; missing-confounder questions removed; the
##  causal conflating-task question removed; confounding block reordered; and
##  exposure/outcome moved to TSA+YA determination. Round 1 additionally ADDED
##  the "does not usually require validation" option to val_outcome/val_exposure
##  MID-ROUND (round-1's own change list), so those two are `changed`, not direct.
XW1 <- read.csv(text = "col|variable|status
 3|recusal|direct
 4|task|direct
 5|descriptive_design|direct
 6|descriptive_pop|direct
 7|NA_outcome_freetext|dropped
 8|descriptive_sampling|direct
 9|descriptive_sample_size|direct
10|descriptive_acc_sampl|direct
11|descriptive_sample_ach|direct
12|descriptive_base_sel|direct
13|descriptive_outcome_type|direct
14|descriptive_val_outcome|changed
15|descriptive_out_bias_acc|direct
16|descriptive_miss_outcome|direct
17|descriptive_hand_miss_outcom|direct
18|NA_complete_case_desc|dropped
19|descriptive_err_disc|changed
20|descriptive_confl_task|direct
21|predictive_design|direct
22|predictive_pop|direct
23|causal_design|direct
24|causal_pop|direct
25|NA_exposure_freetext|dropped
26|NA_outcome_freetext_causal|dropped
27|causal_sampling|direct
28|causal_sample_size|direct
29|causal_acc_sampl|direct
30|causal_sample_ach|direct
31|NA_selective_invitation|dropped
32|causal_base_sel|confirm
33|causal_comp_dis|direct
34|causal_ltfu_bias|direct
35|causal_ltfu_acc|direct
36|causal_exposure_type|direct
37|causal_val_exposure|changed
38|causal_diff_or_nondiff_exp|direct
39|causal_exp_bias_acc|direct
40|causal_outcome_type|direct
41|causal_val_outcome|changed
42|causal_diff_or_nondiff_out|direct
43|causal_out_bias_acc|direct
44|causal_dep_or_indep_misc|direct
45|NA_confounders_present|dropped
46|causal_conf_var_det|direct
47|causal_base_conf_meth|direct
48|NA_baseline_confounding_present|dropped
49|causal_tv_conf_meth|direct
50|causal_time_verying|confirm
51|causal_miss_exposure|direct
52|causal_hand_miss_exposure|direct
53|causal_miss_outcome|direct
54|causal_hand_miss_outcom|direct
55|NA_miss_confounder|dropped
56|NA_hand_miss_confounder|dropped
57|NA_complete_case_causal|dropped
58|causal_err_disc|changed
59|NA_causal_confl_task|dropped
", sep = "|", header = TRUE, strip.white = TRUE, stringsAsFactors = FALSE)

## every non-dropped mapping must name a real variable in the final instrument
FINAL_VARS <- unique(read.csv(f("data/adjudication/process-tables/cell_level_detail.csv"),
                              colClasses = "character")$variable)
chk <- function(xw, lab) {
  m <- xw$variable[xw$status != "dropped"]
  bad <- setdiff(m, FINAL_VARS)
  if (length(bad)) stop(lab, ": mapped to non-existent variable(s): ", paste(bad, collapse = ", "))
  if (any(duplicated(m))) stop(lab, ": duplicate target variable(s): ",
                               paste(unique(m[duplicated(m)]), collapse = ", "))
}
chk(XW2, "round 2"); chk(XW1, "round 1")
cat("[check] both crosswalks resolve to real, distinct final-tool variables\n")

###############################################################################
## 2.  PAIRWISE CONCORDANT ERROR
###############################################################################
pair_counts <- function(rev, adj, xw, adj_for) {
  out <- list()
  pmids <- unique(rev[[2]])
  for (i in seq_len(nrow(xw))) {
    j <- xw$col[i]
    for (pm in pmids) {
      rr  <- norm1(rev[rev[[2]] == pm, j])
      ref <- norm1(adj[adj[[2]] == pm, adj_for[j]])
      if (!length(ref) || !nzchar(ref)) next            # item N/A for this paper
      rr <- rr[nzchar(rr)]
      if (length(rr) < 2) next
      np <- nw <- 0L
      for (x in seq_len(length(rr) - 1)) for (y in (x + 1):length(rr))
        if (rr[x] == rr[y]) { np <- np + 1L; if (rr[x] != ref) nw <- nw + 1L }
      if (np == 0L) next
      out[[length(out) + 1L]] <- data.frame(PMID = pm, variable = xw$variable[i],
        status = xw$status[i], agreed_pairs = np, both_wrong = nw,
        stringsAsFactors = FALSE)
    }
  }
  do.call(rbind, out)
}

load_round <- function(rev_path, adj_path, xw, label) {
  rev <- rd(rev_path)
  rev <- rev[rev[[1]] != "Adjudicated", ]
  if ("Title" %in% names(rev)) rev <- rev[, setdiff(names(rev), "Title")]
  rev <- rev[!(rev[[1]] %in% DROP_REVIEWERS), ]
  adj <- rd(adj_path)
  k_rev <- keyof(names(rev)); k_adj <- keyof(names(adj))
  stopifnot(setequal(k_rev, k_adj))            # same question set, order may differ
  adj_for <- match(k_rev, k_adj)
  ## ⚠ the reviewer and adjudication exports TRANSPOSE acc_sampl and sample_ach
  ## relative to each other in both task blocks. Aligning by POSITION scores each
  ## against the other and manufactures a false error rate on those two items.
  ## Aligning on (question text, occurrence index) is what makes this correct.
  cat(sprintf("[%s] reviewers %d, papers %d, columns realigned %d\n", label,
              length(unique(rev[[1]])), length(unique(rev[[2]])),
              sum(adj_for != seq_along(adj_for))))
  pair_counts(rev, adj, xw, adj_for)
}

R1 <- load_round("data/calibration/round-1/Reviewer and adjudication answers with new revierwer 5.xlsx",
                 "data/calibration/round-1/2024_05_04_Adjudication_of_calibration.xlsx", XW1, "round 1")
R1$round <- 1L

## ---- ROUND 2 -------------------------------------------------------------
## The raw export is the cumulative Google-Forms progress CSV, which carries a
## leading Timestamp column the adjudication file does not have.
## ⚠ Reviewer 5 appears TWICE for every paper: the ID changed hands, and both the
## outgoing and the incoming reviewer submitted under it. June 2024 = outgoing
## (R4 Alessi), November 2024 = incoming (R14 Almeshal), which matches the
## separate "new reviewer 5" recalibration of round 1 dated 2024-09-25. TSA ruled
## the NEW reviewer 5 is canonical, so keep the LATEST submission per (reviewer,
## paper). Everyone else submitted once.
load_round2 <- function(xw) {
  p <- read.csv(f("data/calibration/round-2/2024_11_26_Progress_round_2.csv"),
                colClasses = "character", check.names = FALSE)
  stopifnot(names(p)[1] == "Timestamp")
  ord <- order(as.POSIXct(sub(" GMT.*$", "", p$Timestamp), format = "%Y/%m/%d %I:%M:%S %p",
                          tz = "UTC"), decreasing = TRUE)
  p <- p[ord, ]
  dup_key <- paste(p[[2]], p[[3]])
  n_dup <- sum(duplicated(dup_key))
  p <- p[!duplicated(dup_key), ]                       # keeps the latest
  cat(sprintf("[round 2] dropped %d superseded submission(s) (old reviewer 5)\n", n_dup))
  rev <- p[, -1]                                       # drop Timestamp
  rev <- rev[!(rev[[1]] %in% DROP_REVIEWERS), ]
  adj <- rd("data/calibration/round-2/2024_07_13_Adjudication_of_calibration_round_2.xlsx")
  k_rev <- keyof(names(rev)); k_adj <- keyof(names(adj))
  stopifnot(setequal(k_rev, k_adj))
  adj_for <- match(k_rev, k_adj)
  cat(sprintf("[round 2] reviewers %d, papers %d, columns realigned %d\n",
              length(unique(rev[[1]])), length(unique(rev[[2]])),
              sum(adj_for != seq_along(adj_for))))
  pair_counts(rev, adj, xw, adj_for)
}
R2 <- load_round2(XW2)
R2$round <- 2L

###############################################################################
## 3.  SUMMARY, with paper-clustered bootstrap intervals
###############################################################################
boot_rate <- function(d, B = B_BOOT) {
  pm <- unique(d$PMID)
  if (length(pm) < 2) return(c(NA_real_, NA_real_))
  v <- vapply(seq_len(B), function(b) {
    ## cluster bootstrap: resample PAPERS, each carrying its whole block of
    ## pairs. Pairs within a paper are not independent -- 13 reviewers give 78
    ## pairs per cell off 13 judgements -- so resampling pairs would understate
    ## the interval by roughly an order of magnitude.
    idx <- unlist(lapply(sample(pm, length(pm), replace = TRUE),
                         function(p) which(d$PMID == p)))
    sum(d$both_wrong[idx]) / sum(d$agreed_pairs[idx])
  }, numeric(1))
  unname(quantile(v[is.finite(v)], c(.025, .975)))
}

summarise <- function(d, lab) {
  ci <- boot_rate(d)
  cat(sprintf("%-46s %6d pairs %5d wrong  %5.1f%%  [%.1f, %.1f]\n", lab,
              sum(d$agreed_pairs), sum(d$both_wrong),
              100 * sum(d$both_wrong) / sum(d$agreed_pairs), 100 * ci[1], 100 * ci[2]))
  data.frame(subset = lab, agreed_pairs = sum(d$agreed_pairs),
             both_wrong = sum(d$both_wrong),
             rate = sum(d$both_wrong) / sum(d$agreed_pairs),
             lo = ci[1], hi = ci[2], stringsAsFactors = FALSE)
}

cat("\n=========== ROUND 1 (10 papers), reviewer 3 excluded, new-reviewer-5 ===========\n")
S1 <- rbind(
  summarise(R1,                                 "R1 ALL mapped columns"),
  summarise(R1[R1$status != "dropped", ],       "R1 in the final tool"),
  summarise(R1[R1$status == "direct", ],        "R1 DIRECT only"),
  summarise(R1[R1$status == "changed", ],       "R1 option set changed since calibration"),
  summarise(R1[R1$status == "dropped", ],       "R1 dropped -- not in the final tool"))

cat("\n=========== ROUND 2 (3 papers, tool v6, post-clarification) ===========\n")
cat("⚠ only 3 clusters, so the paper-bootstrap interval is barely informative\n")
S2 <- rbind(
  summarise(R2,                                 "R2 ALL mapped columns"),
  summarise(R2[R2$status != "dropped", ],       "R2 in the final tool"),
  summarise(R2[R2$status == "direct", ],        "R2 DIRECT only"),
  summarise(R2[R2$status == "dropped", ],       "R2 dropped -- not in the final tool"))

## like-for-like: the SAME direct variables measured in both rounds
common <- intersect(unique(R1$variable[R1$status == "direct"]),
                    unique(R2$variable[R2$status == "direct"]))
cat(sprintf("\n=========== LIKE-FOR-LIKE: the %d direct items measured in BOTH rounds ===========\n",
            length(common)))
S3 <- rbind(
  summarise(R1[R1$status == "direct" & R1$variable %in% common, ], "round 1, common items"),
  summarise(R2[R2$status == "direct" & R2$variable %in% common, ], "round 2, common items"))
S <- rbind(S1, S2, S3)

## per variable, direct only
D <- R1[R1$status == "direct", ]
V <- do.call(rbind, lapply(split(D, D$variable), function(z) data.frame(
  variable = z$variable[1], papers = length(unique(z$PMID)),
  agreed_pairs = sum(z$agreed_pairs), both_wrong = sum(z$both_wrong),
  rate = sum(z$both_wrong) / sum(z$agreed_pairs), stringsAsFactors = FALSE)))
V <- V[order(-V$rate), ]

write.csv(rbind(cbind(round = 1, XW1), cbind(round = 2, XW2)),
          file.path(TBL, sprintf("%s_calibration_crosswalk.csv", STAMP)), row.names = FALSE)
write.csv(S, file.path(TBL, sprintf("%s_calibration_concordant_error_summary.csv", STAMP)),
          row.names = FALSE)
write.csv(V, file.path(TBL, sprintf("%s_calibration_concordant_error_by_item.csv", STAMP)),
          row.names = FALSE)

cat("\n=========== per item, round 1 (DIRECT only), worst first ===========\n")
print(V, row.names = FALSE, digits = 2)

## per-item comparison across rounds, common items only
cmp <- merge(
  do.call(rbind, lapply(split(R1[R1$status == "direct" & R1$variable %in% common, ], ~variable),
    function(z) data.frame(variable = z$variable[1], r1_pairs = sum(z$agreed_pairs),
      r1_rate = sum(z$both_wrong)/sum(z$agreed_pairs)))),
  do.call(rbind, lapply(split(R2[R2$status == "direct" & R2$variable %in% common, ], ~variable),
    function(z) data.frame(variable = z$variable[1], r2_pairs = sum(z$agreed_pairs),
      r2_rate = sum(z$both_wrong)/sum(z$agreed_pairs)))),
  by = "variable")
cmp$change <- cmp$r2_rate - cmp$r1_rate
cmp <- cmp[order(cmp$change), ]
write.csv(cmp, file.path(TBL, sprintf("%s_calibration_round1_vs_round2.csv", STAMP)),
          row.names = FALSE)
cat("\n=========== per item, round 1 vs round 2 (common direct items) ===========\n")
print(cmp, row.names = FALSE, digits = 2)

###############################################################################
## 4.  THE PARAMETER TABLE -- TSA's sourcing rule (2026-08-19)
##
##   "Base the parameters on the exact matching variable if it was in round 1 and
##    didn't change in round 2. If it changed / was modified in round 2, base it
##    on round 2 only."
##
##  So each variable draws from ONE round: round 1 (10 papers) when the question
##  and its options are stable across rounds, round 2 (3 papers) when they are not.
##
##  ⚠ HOW "CHANGED" IS DECIDED. An option simply APPEARING in round 2 is not
##  evidence of a change -- 3 papers cannot exercise every category, and e.g.
##  `causal_base_sel` gaining "Yes" or `causal_sampling` gaining "Random" is
##  ordinary sampling. A change is recorded only on documentary or label evidence:
##  a relabelled option, an option the change lists say was added, or guidance the
##  round-2 change list explicitly records. Each is given its basis below.
###############################################################################
CHANGED_AT_R2 <- read.csv(text = "variable|basis
causal_outcome_type|option labels shortened: 'Objective (e.g., measurements...)' -> 'Objective'
causal_exposure_type|option labels shortened: 'Subjective (e.g., feelings, pain...)' -> 'Subjective'
causal_val_outcome|'does not usually require validation' category added (round-1 change list)
causal_val_exposure|'does not usually require validation' category added (round-1 change list)
causal_base_conf_meth|option relabelled 'no adjustment for BASELINE confounding' -> 'no adjustment for confounding'
causal_conf_var_det|option relabelled 'no adjustment for baseline and time-varying' -> 'no adjustment for confounding'
causal_tv_conf_meth|option relabelled 'no adjustment for BASELINE confounding' -> 'no adjustment for confounding'
causal_miss_outcome|round-2 change list: time-point guidance added for missing outcome
causal_hand_miss_outcom|round-2 change list: time-point guidance added for missing outcome
causal_ltfu_bias|round-2 change list: time-point guidance added for differential loss to follow-up
causal_ltfu_acc|round-2 change list: time-point guidance added for differential loss to follow-up
descriptive_val_outcome|'does not usually require validation' category added -- SAME change as its causal twin
", sep = "|", header = TRUE, strip.white = TRUE, stringsAsFactors = FALSE)
## ⚠ `descriptive_val_outcome` is included above on the evidence, not on the
## documents: round 1 shows only 3 options for it (No / content-face / criterion)
## and the 4th, "does not usually require validation", never appears -- exactly as
## for `causal_val_outcome` and `causal_val_exposure`. The final tool has all four.
## Round-1 rates therefore do not transfer. But round 2 has no descriptive papers,
## so the rule leaves this variable with NO usable source. It is reported as an
## orphan rather than quietly sourced from round 1.

## `causal_time_verying` is EXCLUDED, not sourced. Calibration asks "was there
## time-varying CONFOUNDING (in case of estimating a time-varying causal effect)"
## with three answers; the final tool asks whether a time-varying EFFECT was
## estimated, with two. That is a split, not a rename, so there is no exact
## matching variable. It feeds neither a VAL nor a REP flag, so nothing is lost.
EXCLUDE_NO_EXACT_MATCH <- "causal_time_verying"

per_var <- function(d, keep) {
  d <- d[d$variable %in% keep & d$status != "dropped", ]
  do.call(rbind, lapply(split(d, d$variable), function(z) data.frame(
    variable = z$variable[1], papers = length(unique(z$PMID)),
    agreed_pairs = sum(z$agreed_pairs), both_wrong = sum(z$both_wrong),
    rate = sum(z$both_wrong) / sum(z$agreed_pairs), stringsAsFactors = FALSE)))
}
all_vars <- setdiff(union(R1$variable, R2$variable), EXCLUDE_NO_EXACT_MATCH)
all_vars <- setdiff(all_vars, grep("^NA_", all_vars, value = TRUE))
stable   <- setdiff(all_vars, CHANGED_AT_R2$variable)

P <- rbind(
  transform(per_var(R1, stable),                  source_round = 1L,
            basis = "stable across rounds; round 1 has 10 papers"),
  transform(per_var(R2, CHANGED_AT_R2$variable),  source_round = 2L,
            basis = CHANGED_AT_R2$basis[match(
              per_var(R2, CHANGED_AT_R2$variable)$variable, CHANGED_AT_R2$variable)]))
P <- P[order(-P$rate), ]

## ---- the one orphan, resolved by TSA 2026-08-19 --------------------------
## `descriptive_val_outcome` changed the same way its causal twin did, but round 2
## has no descriptive papers, so the rule leaves it unsourced. TSA chose to BORROW
## the causal twin's round-2 rate: same question, same four options, differing only
## in which task branch asks it, and it is the conservative direction (0.341 vs the
## round-1 figure of 0.169). Recorded as a proxy, never as a measurement.
orphan <- setdiff(CHANGED_AT_R2$variable, P$variable)
PROXY_FROM <- c(descriptive_val_outcome = "causal_val_outcome")
for (v in intersect(orphan, names(PROXY_FROM))) {
  src <- P[P$variable == PROXY_FROM[[v]], ]
  if (!nrow(src)) next
  P <- rbind(P, data.frame(variable = v, papers = src$papers,
    agreed_pairs = src$agreed_pairs, both_wrong = src$both_wrong, rate = src$rate,
    source_round = src$source_round,
    basis = sprintf("PROXY (TSA 2026-08-19): borrowed from %s -- same question and option set, other task branch; round 2 has no descriptive papers",
                    PROXY_FROM[[v]]), stringsAsFactors = FALSE))
  orphan <- setdiff(orphan, v)
}
P$is_proxy <- grepl("^PROXY", P$basis)
P <- P[order(-P$rate), ]

write.csv(P, file.path(TBL, sprintf("%s_calibration_parameter_source.csv", STAMP)),
          row.names = FALSE)

cat("\n\n=========== PARAMETER TABLE under TSA's sourcing rule ===========\n")
cat(sprintf("stable -> round 1: %d variables | changed -> round 2: %d variables\n",
            sum(P$source_round == 1), sum(P$source_round == 2)))
print(P[, c("variable","source_round","papers","agreed_pairs","both_wrong","rate")],
      row.names = FALSE, digits = 2)
## proxies borrow another variable's pairs, so they must NOT enter the pooled total
Pm <- P[!P$is_proxy, ]
cat(sprintf("\npooled over MEASURED variables (%d; proxies excluded): %d pairs, %d wrong -> %.1f%%\n",
            nrow(Pm), sum(Pm$agreed_pairs), sum(Pm$both_wrong),
            100 * sum(Pm$both_wrong) / sum(Pm$agreed_pairs)))
if (any(P$is_proxy))
  cat(sprintf("proxy rows (rate borrowed, pairs not counted twice): %s\n",
              paste(P$variable[P$is_proxy], collapse = ", ")))
if (length(orphan))
  cat("\n⚠ changed at round 2 but NOT MEASURABLE there (round 2 has no such cells):\n  ",
      paste(orphan, collapse = ", "), "\n")
cat("\n⚠ ALL THREE ROUND-2 PAPERS ARE CAUSAL, so no descriptive_* variable can ever be",
    "\n  sourced from round 2. Any descriptive item judged 'changed' has no clean source.\n")

cat("\n=========== ⚠ MAPPINGS NEEDING TSA CONFIRMATION ===========\n")
for (nm in c("XW1", "XW2")) {
  xw <- get(nm)
  cf <- xw[xw$status == "confirm", ]
  if (nrow(cf)) for (i in seq_len(nrow(cf)))
    cat(sprintf("  %s col %2d -> %s\n", nm, cf$col[i], cf$variable[i]))
}
cat("\nwrote 3 tables to outputs/tables/\n")

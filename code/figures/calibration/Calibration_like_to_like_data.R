#######################################################################################
# Build LIKE-TO-LIKE calibration values (Reviewer 3 excluded).
# For every item we compute BOTH Krippendorff's alpha and percent agreement in each
# round (from the recoded raw answers; round 1 = NEW reviewer 5), then keep each item's
# ASSIGNED statistic for BOTH rounds so we never compare alpha vs percent across rounds.
# Also reports which items were mixed (alpha one round, percent the other) originally.
# Output: calibration_corrected_long.csv  (item, display, stat, round, reviewer, value)
#######################################################################################
suppressMessages({library(irr); library(dplyr); library(tidyr); library(readxl); library(purrr)})

SCRATCH <- "C:/Users/[USER]/AppData/Local/Temp/claude/C--Users-[USER]-OneDrive-Claude-code-projects-Applicaiton-of-LLM-to-causal-inference-topics/dc77ffcb-0bcb-4dc6-b177-52abe7d2fe3f/scratchpad"
long <- read.csv(file.path(SCRATCH, "recoded_long.csv"), stringsAsFactors = FALSE)

# --- Registry: SAS base | display | assigned statistic | round-1 & round-2 summary names ---
reg <- tibble::tribble(
  ~base, ~display, ~stat, ~r1name, ~r2name,
  # ---- Krippendorff's alpha items ----
  "design","Study design","alpha","Design","Design",
  "pop","Population from Saudi","alpha","Population","Population",
  "sampling","Sampling type","alpha","Sampling","Sampling",
  "sample_size","Sample size calculation was done","alpha","Sample size calc done","Sample size calc done",
  "acc_sampl","Accounting for other issues in calculation of sample size","alpha","Accounting for other issues in calc","Accounting for other issues in calc",
  "sample_ach","Achieving sample size calculated","alpha","Sample size achieved","Sample size achieved",
  "base_sel","Accounting for baseline selection bias","alpha","Accounted for baseline selection bias","Accounted for baseline selection bias",
  "val_outcome","Outcome validity","alpha","Outcome validity","Outcome validity",
  "miss_outcome","Presence of missing outcome","alpha","Missing outcome","Missing outcome",
  "hand_miss_outcom","Method for handling missing outcome","alpha","Method for handling missing outcome","Method for handling missing outcome",
  "err_disc","Mentioning errors in discussion","alpha","Mentioning errors in discussion","Mentioning errors in discussion",
  "inv_sel_base","Presence of baseline selection bias from investigator","alpha","Baseline selection bias from investigator","Baseline selection bias from investigator",
  "comp_dis","Comparing exposure and outcome distributions between included and non-included population in analysis","alpha","Compared exp and out distributions","Compared exp and out distributions",
  "ltfu_bias","Presence of loss to follow up bias","alpha","Loss to follow up bias*","Loss to follow up bias",
  "ltfu_acc","Accounting for loss to follow up bias","alpha","Accounting for loss to follow up bias*","Accounting for loss to follow up bias",
  "val_exposure","Exposure validity","alpha","Exposure validity*","Exposure validity",
  "diff_or_nondiff_out","Outcome measurement differential with respect to exposure","alpha","Outcome measurement diff with respect to exposure","Outcome measurement diff with respect to exposure",
  "dep_or_indep_misc","Presence of dependent or independent exposure and outcome measurement biases","alpha","Dependent or independent measurement bias","Dependent or independent measurement bias",
  "miss_exposure","Presence of missing exposure","alpha","Missing exposure","Missing exposure",
  "hand_miss_exposure","Method for handling missing exposure","alpha","Method for handling missing exposure","Method for handling missing exposure",
  # ---- Percent-agreement items ----
  "task","Study task","percent","Task","Task",
  "outcome_type","Outcome type","percent","Outcome type","Outcome type",
  "out_bias_acc","Accounting for outcome measurement bias","percent","Accounted for outcome measure bias","Accounted for outcome measure bias",
  "exposure_type","Exposure type","percent","Exposure type","Exposure type",
  "diff_or_nondiff_exp","Exposure measurement differential with respect to outcome","percent","Exposure measurement diff with respect to outcome","Exposure measurement diff with respect to outcome",
  "exp_bias_acc","Accounting for exposure measurement bias","percent","Accounted for exposure measure bias","Accounted for exposure measure bias",
  "base_conf_meth","Method of handling baseline confounding","percent","Method of handling baseline confounding","Method of handling baseline confounding",
  "base_conf","Presence of baseline confounding","percent","Baseline confounding","Baseline confounding",
  "tv_conf_meth","Method of handling time varying confounding","percent","Method of handling time varying confounding","Method of handling time varying confounding",
  "tv_conf","Presence of time varying confounding","percent","Time varying confounding","Time varying confounding",
  "conf_var_det","Determining confounding variables","percent","Determining confounding variables*","Determining confounding variables"
)
reg$order <- seq_len(nrow(reg))

# --- Compute alpha & percent (all 14 reviewers vs adjudicator) for an item/round ---
stats_for <- function(rnd, item) {
  d <- long %>% filter(round == rnd, item == !!item)
  w <- d %>% select(rater, paper, code) %>% arrange(rater, paper) %>%
    pivot_wider(names_from = paper, values_from = code)
  w <- w[order(w$rater), ]
  mat <- as.matrix(w[, setdiff(names(w), "rater")])   # rows: rater 0..14
  adj <- mat[w$rater == 0, ]
  purrr::map_dfr(1:14, function(i) {
    ri <- mat[w$rater == i, ]
    ok <- !is.na(adj) & !is.na(ri)
    pct <- if (sum(ok) > 0) mean(ri[ok] == adj[ok]) else NA_real_
    al  <- if (sum(ok) > 1) {
      lv <- unique(c(adj[ok], ri[ok]))
      tryCatch(suppressWarnings(kripp.alpha(rbind(match(adj[ok], lv), match(ri[ok], lv)), "nominal")$value),
               error = function(e) NA_real_)
    } else NA_real_
    tibble(reviewer = paste0("R", i), alpha = al, percent = pct)
  })
}

all_stats <- reg %>% select(base, display, stat, order) %>%
  crossing(round = c(1, 2)) %>%
  mutate(vals = map2(round, base, stats_for)) %>%
  unnest(vals)

# --- Which statistic did the ORIGINAL summaries use? (compare to summary per-reviewer) ---
sum1 <- read_excel("data/calibration/Calibration and agreement with new reviewer 5.xlsx", sheet = "Sheet1") %>% as.data.frame()
sum2 <- read_excel("data/calibration/Calibration and agreement_round_2_new_rev5.xlsx", sheet = "Round 2") %>% as.data.frame()
get_sumvec <- function(df, name) {
  key <- trimws(as.character(df[[1]])); i <- which(key == name)
  if (length(i) != 1) return(rep(NA_real_, 14)); as.numeric(df[i, 2:15])
}
# decide chosen stat per item/round by nearest match of the 14-vector
decide <- function(base_, rnd, sumdf, sumname) {
  sv <- get_sumvec(sumdf, sumname)
  st <- all_stats %>% filter(base == base_, round == rnd) %>%
    mutate(rn = as.integer(sub("R","",reviewer))) %>% arrange(rn)
  da <- mean(abs(st$alpha   - sv), na.rm = TRUE)
  dp <- mean(abs(st$percent - sv), na.rm = TRUE)
  if (is.nan(da) && is.nan(dp)) return(c(stat=NA_character_, dist=NA_real_))
  if (is.nan(da)) return(c(stat="percent", dist=dp))
  if (is.nan(dp)) return(c(stat="alpha",   dist=da))
  if (da <= dp) c(stat="alpha", dist=da) else c(stat="percent", dist=dp)
}
diag <- reg %>% rowwise() %>%
  mutate(d1 = list(decide(base, 1, sum1, r1name)), d2 = list(decide(base, 2, sum2, r2name)),
         orig_r1 = d1[["stat"]], orig_r2 = d2[["stat"]],
         dist_r1 = as.numeric(d1[["dist"]]), dist_r2 = as.numeric(d2[["dist"]]),
         mixed  = !is.na(orig_r1) & !is.na(orig_r2) & orig_r1 != orig_r2,
         off_class = (orig_r1 != stat & !is.na(orig_r1)) | (orig_r2 != stat & !is.na(orig_r2))) %>% ungroup()

cat("\n===== VALIDATION: max distance between my computed stat and the summary =====\n")
cat("  round1 max dist =", round(max(diag$dist_r1, na.rm=TRUE),4),
    " | round2 max dist =", round(max(diag$dist_r2, na.rm=TRUE),4), " (should be ~0)\n")
cat("\n  items with distance > 0.02 (possible mismatch):\n")
print(as.data.frame(diag %>% filter(dist_r1 > 0.02 | dist_r2 > 0.02) %>%
        transmute(display, stat, orig_r1, dist_r1=round(dist_r1,3), orig_r2, dist_r2=round(dist_r2,3))))

cat("\n===== Full per-item statistic used originally vs assigned =====\n")
print(as.data.frame(diag %>% transmute(display, assigned=stat, orig_r1, orig_r2,
                                       flag = ifelse(mixed,"MIXED", ifelse(off_class,"off-class","ok")))))
cat("\nCounts: assigned alpha =", sum(reg$stat=="alpha"), " percent =", sum(reg$stat=="percent"),
    " | mixed across rounds =", sum(diag$mixed), " | off-classification =", sum(diag$off_class), "\n")

# --- Build corrected long table: each item keeps its ASSIGNED statistic in BOTH rounds ---
corrected <- all_stats %>%
  mutate(value = ifelse(stat == "alpha", alpha, percent)) %>%
  filter(reviewer != "R3") %>%                        # drop Reviewer 3
  select(base, display, stat, order, round, reviewer, value)

# flag any assigned value that is undefined (e.g., alpha item with invariant round)
na_flags <- corrected %>% filter(is.na(value))
if (nrow(na_flags) > 0) {
  cat("\n!! WARNING: assigned statistic UNDEFINED for these item/round/reviewer cells:\n")
  print(as.data.frame(na_flags %>% count(display, stat, round, name = "n_reviewers_NA")))
}

write.csv(corrected, file.path(SCRATCH, "calibration_corrected_long.csv"), row.names = FALSE)
cat("\nwrote calibration_corrected_long.csv  (", nrow(corrected), "rows )\n")

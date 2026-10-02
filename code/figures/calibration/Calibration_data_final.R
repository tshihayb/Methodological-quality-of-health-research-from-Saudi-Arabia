#######################################################################################
# CORRECTED calibration data (Reviewer 3 excluded; LIKE-TO-LIKE across rounds).
# Single source of data for all calibration figures.
#
# For most items the two rounds already used the SAME statistic, so we keep the official
# SAS summary values. Some percent-agreement items were mixed across rounds because in one
# round the answers had NO variation, making Krippendorff's alpha undefined (0/0), so
# percent agreement was used that round while the other round used alpha:
#     * Study task  (round 2 had no variation -> alpha undefined -> percent)  -> percent both
#     * Outcome type (round 1 was reported as alpha)                          -> percent both
#     * Accounting for outcome measurement bias (round 2 has no variation)    -> percent both (r2=1.0 either way)
# Their corrected per-reviewer percent-agreement values (recomputed from the recoded raw
# answers, new reviewer 5) live in data/calibration/calibration_likeforlike_fix.csv and are patched in here.
#
# Produces: long_final (per-reviewer, 13 reviewers) ; alpha_df / perc_df (item-level).
#######################################################################################
suppressMessages({
  library(readxl); library(dplyr); library(tidyr); library(forcats)
  library(purrr); library(stringr); library(ggplot2); library(ggnewscale); library(grid)
})
setwd(".")

REVIEWERS <- paste0("R", c(1,2,4,5,6,7,8,9,10,11,12,13,14))   # 13 retained (R3 dropped)

reg <- tibble::tribble(
  ~base, ~display, ~stat, ~r1name, ~r2name,
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
) %>% mutate(order = row_number())

sum1 <- read_excel("data/calibration/Calibration and agreement with new reviewer 5.xlsx", sheet = "Sheet1")     %>% as.data.frame()
sum2 <- read_excel("data/calibration/Calibration and agreement_round_2_new_rev5.xlsx",  sheet = "Round 2")     %>% as.data.frame()
getvec <- function(df, name) {
  k <- trimws(as.character(df[[1]])); i <- which(k == name)
  if (length(i) != 1) stop(paste("summary row not found:", name)); as.numeric(df[i, 2:15])
}

# --- per-reviewer (13, excl R3) from official summaries ---
long_final <- reg %>% pmap_dfr(function(base, display, stat, r1name, r2name, order) {
  v1 <- getvec(sum1, r1name)[-3]; v2 <- getvec(sum2, r2name)[-3]
  tibble(base = base, display = display, stat = stat, order = order,
         reviewer = rep(REVIEWERS, 2), round = rep(c("1st","2nd"), each = length(REVIEWERS)),
         value = c(v1, v2))
})

# --- patch the two mixed items with recomputed percent (both rounds) ---
fix <- read.csv("data/calibration/calibration_likeforlike_fix.csv", stringsAsFactors = FALSE)
long_final <- long_final %>%
  left_join(fix, by = c("base","round","reviewer"), suffix = c("", ".fix")) %>%
  mutate(value = ifelse(!is.na(value.fix), value.fix, value)) %>% select(-value.fix)

# --- DISPLAY RE-NUMBERING (2026-08-16) -------------------------------------------------
# Fourteen reviewers were recruited; one withdrew before data collection, leaving 13.
# The source spreadsheets keep that reviewer's original slot, so the retained reviewers
# carried the labels R1,R2,R4..R14 - a sequence that runs to 14 and reads as though
# fourteen reviewers contributed. Renumber them consecutively as R1..R13 for every figure.
# This happens AFTER the like-for-like patch above, because data/calibration/calibration_likeforlike_fix.csv
# is keyed on the ORIGINAL identifiers; changing them earlier would silently break that join.
REVIEWER_RELABEL   <- setNames(paste0("R", seq_along(REVIEWERS)), REVIEWERS)
long_final         <- long_final %>% mutate(reviewer = unname(REVIEWER_RELABEL[reviewer]))
REVIEWERS_ORIGINAL <- REVIEWERS                       # kept for traceability to the source files
REVIEWERS          <- unname(REVIEWER_RELABEL)        # R1..R13, used by all downstream figures
stopifnot(length(REVIEWERS) == 13, !anyNA(long_final$reviewer))

# --- item-level frames (display, round_1, round_2, change) + Average score row ---
item_lvl <- long_final %>% group_by(base, display, stat, order, round) %>%
  summarise(m = mean(value, na.rm = TRUE), .groups = "drop") %>%
  pivot_wider(names_from = round, values_from = m)
mk_df <- function(st) {
  d <- item_lvl %>% filter(stat == st) %>% arrange(order) %>%
    transmute(display, round_1 = `1st`, round_2 = `2nd`, change = `2nd` - `1st`)
  bind_rows(d, tibble(display = "Average score", round_1 = mean(d$round_1),
                      round_2 = mean(d$round_2), change = mean(d$round_2) - mean(d$round_1)))
}
alpha_df <- mk_df("alpha")
perc_df  <- mk_df("percent")

cat(sprintf("Data ready (like-to-like, excl R3). Krippendorff's alpha mean change = %.4f ; percent = %.4f\n",
            tail(alpha_df,1)$change, tail(perc_df,1)$change))

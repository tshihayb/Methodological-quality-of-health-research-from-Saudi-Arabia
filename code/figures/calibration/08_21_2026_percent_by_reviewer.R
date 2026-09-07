#######################################################################################
# DATA MODULE — percent agreement for EVERY tool item, per reviewer, per round.
# Sourced by the two all-percent figures; draws nothing itself.
#
# Exports:
#   pct_long   base · display · tool_order · round ("1st"/"2nd") · reviewer (R1..R13) · value
#   pct_item   one row per item: display · tool_order · round_1 · round_2 · change
#   REV_LABELS the 13 retained reviewers, relabelled R1..R13
#
# WHY IT EXISTS
# Twenty of the thirty-one items are officially reported as Krippendorff's alpha, so no
# percent figure exists for them. Percent agreement is recomputed here for all thirty-one
# on one definition, from the per-paper agreement matrices that hold each rater's answer
# beside the adjudicated answer:
#     data/calibration/round-1/agreement_new_5.xlsx   (10 papers, 57 items x 15 raters)
#     data/calibration/round-2/agreement_round_2.xlsx ( 3 papers)
# For each item and reviewer: the exact-match rate against the TSA/YA adjudicated answer
# across the papers where BOTH answered. Pairwise complete, so skipped and not-applicable
# cells drop out instead of counting as disagreement.
#
# ⚠ REPLACES A BROKEN PATH. `Calibration figures_all_percent.R` recomputed the same thing
# but read it from a CSV in the scratch directory of an unrelated project, which no longer
# exists. Everything here reads from inside the repository.
#
# VALIDATION (printed, and asserted)
# Eleven items are officially reported as percent, so the recomputation is checkable.
# TEN agree within 0.02, including all three that carry a documented like-to-like patch -
# the strongest available check, since those patched values were themselves derived as
# exact-match percentages. One differs: `Presence of baseline confounding`, round 1,
# 0.304 here against 0.381 published; the gap is one reviewer whose five causal papers
# score 0 in the agreement matrix and 1 in the summary sheet. Surfaced, not hidden.
# ⚠ "within 0.02" is NOT "to two decimals", which is what this said until 2026-08-22:
# `Determining confounding variables` round 1 is 0.658 vs 0.642, inside the tolerance but
# 0.66 vs 0.64 rounded. EIGHT are identical at two decimals. Both counts are now printed,
# because Supplementary Figures S6 and S7 quote them in their legends.
#######################################################################################

source("code/figures/calibration/Calibration figures_no_reviewer3.R")  # make_fig, reg, sum1, perc_df
library(dplyr); library(tidyr); library(readxl); library(purrr)

BLANKS <- c("", "none", "nan", "na", "skipped", "should be skipped")
is_blank <- function(v) is.na(v) | tolower(trimws(v)) %in% BLANKS

read_matrix <- function(path, sheet) {
  as.data.frame(suppressMessages(
    read_excel(path, sheet = sheet, col_types = "text", .name_repair = "minimal")))
}

## One item can be asked in more than one task block (descriptive_design, causal_design)
## and only the block matching the paper's task is filled in, so pooling the blocks gives
## exactly one comparison per paper - the convention the official summaries use.
agreement_by_reviewer <- function(m, base, reviewers) {
  cols <- names(m)
  pats <- c(sprintf("^(descriptive|causal|predictive)_%s_%%s$", base),
            sprintf("^%s_%%s$", base))
  pick <- function(sfx) cols[grepl(paste(sprintf(pats, sfx), collapse = "|"), cols)]
  a_cols <- pick("a")
  if (!length(a_cols)) return(setNames(rep(NA_real_, length(reviewers)), reviewers))
  vapply(reviewers, function(rv) {
    r_cols <- pick(paste0("r", rv))
    hits <- unlist(lapply(a_cols, function(ac) {
      stem <- sub("_a$", "", ac)
      rc <- r_cols[sub(sprintf("_r%s$", rv), "", r_cols) == stem]
      if (!length(rc)) return(numeric(0))
      a <- m[[ac]]; r <- m[[rc[1]]]
      keep <- !is_blank(a) & !is_blank(r)
      as.numeric(trimws(a[keep]) == trimws(r[keep]))
    }))
    if (!length(hits)) NA_real_ else mean(hits)
  }, numeric(1))
}

M1 <- read_matrix("data/calibration/round-1/agreement_new_5.xlsx", "agreement_new_5")
M2 <- read_matrix("data/calibration/round-2/agreement_round_2.xlsx", "agreement_round_2")
cat(sprintf("\nAgreement matrices: round 1 %d papers x %d cols · round 2 %d x %d\n",
            nrow(M1), ncol(M1), nrow(M2), ncol(M2)))

## Reviewer 3 withdrew before data collection; the source files keep the empty slot, so
## the retained thirteen carry the labels 1,2,4..14 there and are renumbered R1..R13 for
## display - the same relabelling every other figure in this project applies.
REV_SRC    <- c(1, 2, 4:14)
REV_LABELS <- paste0("R", seq_along(REV_SRC))
stopifnot(length(REV_SRC) == 13)

## TOOL ORDER: the row order of the official round-1 summary sheet, which lists the
## instrument as a reviewer meets it - the items asked of every study, then the
## causal-only block. Using it needs no fresh judgement about what the tool's order is.
tool_rows <- trimws(as.character(sum1[[1]]))

pct_long <- reg %>% select(base, display, r1name) %>%
  mutate(tool_order = match(r1name, tool_rows),
         `1st` = map(base, ~agreement_by_reviewer(M1, .x, REV_SRC)),
         `2nd` = map(base, ~agreement_by_reviewer(M2, .x, REV_SRC))) %>%
  select(-r1name) %>%
  pivot_longer(c(`1st`, `2nd`), names_to = "round", values_to = "v") %>%
  mutate(value = v) %>% select(-v) %>%
  mutate(reviewer = list(REV_LABELS)) %>%
  unnest(c(value, reviewer)) %>%
  arrange(tool_order, round, match(reviewer, REV_LABELS))
stopifnot(!anyNA(pct_long$tool_order), !anyNA(pct_long$value),
          nrow(pct_long) == 31 * 2 * 13)

pct_item <- pct_long %>%
  group_by(base, display, tool_order, round) %>%
  summarise(m = mean(value), .groups = "drop") %>%
  pivot_wider(names_from = round, values_from = m) %>%
  arrange(tool_order) %>%
  transmute(display, tool_order, round_1 = `1st`, round_2 = `2nd`,
            change = `2nd` - `1st`)

#######################################################################################
# Validation against the eleven officially-percent items
#######################################################################################
## ⚠ The test is a TOLERANCE, so say "within 0.02" and never "to two decimals" - they are
## different claims and this printed the wrong one until 2026-08-22. `Determining
## confounding variables` round 1 is 0.658 vs 0.642: inside the tolerance, but 0.66 vs 0.64
## at two decimals. Both counts are reported now, because a caption quotes them.
TOL <- 0.02
chk <- perc_df %>% filter(display != "Average score") %>%
  select(display, off_1 = round_1, off_2 = round_2) %>%
  left_join(pct_item, by = "display") %>%
  mutate(ok  = abs(round_1 - off_1) < TOL & abs(round_2 - off_2) < TOL,
         eq2 = round(round_1, 2) == round(off_1, 2) & round(round_2, 2) == round(off_2, 2))
cat("--- recomputed vs officially reported, the 11 percent-agreement items ---\n")
print(as.data.frame(chk %>% transmute(item = substr(display, 1, 44),
        round_1 = sprintf("%.3f vs %.3f", round_1, off_1),
        round_2 = sprintf("%.3f vs %.3f", round_2, off_2),
        within_tol = ifelse(ok, "yes", "NO"),
        same_2dp   = ifelse(eq2, "yes", "no"))), row.names = FALSE)
cat(sprintf("%d of %d agree within %.2f; %d of %d are identical to two decimals.\n",
            sum(chk$ok), nrow(chk), TOL, sum(chk$eq2), nrow(chk)))
stopifnot(sum(chk$ok) >= 10)

write.csv(pct_long, "outputs/tables/08_21_2026_calibration_percent_by_reviewer.csv",
          row.names = FALSE)
cat(sprintf("Mean across items: round 1 %.3f · round 2 %.3f · change %+.4f\n",
            mean(pct_item$round_1), mean(pct_item$round_2),
            mean(pct_item$round_2) - mean(pct_item$round_1)))

#######################################################################################
# Gwet's AC1 for ALL 31 instrument items, each reviewer against the two adjudicators.
#
#   sourced by 08_28_2026_all_ac1_tool_order.R and 08_28_2026_ac1_heatmap.R
#
# WHY THIS EXISTS
# The published calibration figures split the instrument by statistic: 20 items read as
# Krippendorff's alpha, 11 as percent agreement. The split is not arbitrary. On those 11
# the reviewers and the adjudicators almost always chose the same response, and alpha -
# like kappa - divides by the disagreement expected from the marginal distribution. When
# one category takes nearly every answer that expected disagreement collapses toward zero,
# and alpha returns a number near zero, or negative, for items on which the raters in fact
# agreed almost perfectly. Reporting that as "poor agreement" would be wrong.
#
# Percent agreement avoids the paradox by not correcting for chance at all, which is the
# opposite problem. Gwet's AC1 is the standard repair: it is chance-corrected, but its
# chance term is built so that it does not blow up as one category comes to dominate. It
# is the same statistic Supplementary Figures S10 and S11 use for reviewer-vs-reviewer
# agreement, so the whole supplement now answers the paradox one way.
#
# AC1 for two raters over n paired answers in q observed categories:
#   p_a  = mean(rater1 == rater2)
#   pi_k = (count of k across both raters) / 2n
#   p_e  = sum_k pi_k (1 - pi_k) / (q - 1)
#   AC1  = (p_a - p_e) / (1 - p_e)
# With q = 1 every answer from both raters is the same category: they agree completely and
# no disagreement was possible, so AC1 is 1 by definition rather than undefined.
#
# ⚠ n IS SMALL. Calibration ran on 10 papers in round 1 and 3 in round 2, so a per-item,
# per-reviewer AC1 rests on at most 10 or 3 paired answers. The figures print those n.
# Chance correction is noisier at that size than raw percent agreement is, which is why
# the all-percent pair is kept alongside rather than replaced.
#######################################################################################

source("code/figures/calibration/08_21_2026_percent_by_reviewer.R")  # M1, M2, reg, sum1,
                                                                    # REV_SRC, REV_LABELS,
                                                                    # is_blank, make_fig
library(dplyr); library(purrr); library(tidyr)

gwet_ac1 <- function(a, r) {
  n <- length(a)
  if (n == 0L) return(NA_real_)
  cats <- unique(c(a, r))
  q <- length(cats)
  if (q < 2L) return(1)                       # one category, complete agreement
  pa   <- mean(a == r)
  pi_k <- vapply(cats, function(k) (sum(a == k) + sum(r == k)) / (2 * n), numeric(1))
  pe   <- sum(pi_k * (1 - pi_k)) / (q - 1)
  if (isTRUE(all.equal(pe, 1))) return(NA_real_)
  (pa - pe) / (1 - pe)
}

## Paired (adjudicated, reviewer) answers for one item and one reviewer, pooling the task
## blocks exactly as agreement_by_reviewer() does, so AC1 and percent agreement are
## computed over identical cells and differ only in the statistic.
paired_answers <- function(m, base, rv) {
  cols <- names(m)
  pats <- c(sprintf("^(descriptive|causal|predictive)_%s_%%s$", base),
            sprintf("^%s_%%s$", base))
  pick <- function(sfx) cols[grepl(paste(sprintf(pats, sfx), collapse = "|"), cols)]
  a_cols <- pick("a")
  if (!length(a_cols)) return(NULL)
  r_cols <- pick(paste0("r", rv))
  out <- lapply(a_cols, function(ac) {
    stem <- sub("_a$", "", ac)
    rc <- r_cols[sub(sprintf("_r%s$", rv), "", r_cols) == stem]
    if (!length(rc)) return(NULL)
    a <- m[[ac]]; r <- m[[rc[1]]]
    keep <- !is_blank(a) & !is_blank(r)
    data.frame(a = trimws(a[keep]), r = trimws(r[keep]), stringsAsFactors = FALSE)
  })
  out <- do.call(rbind, out[!vapply(out, is.null, logical(1))])
  if (is.null(out) || !nrow(out)) NULL else out
}

ac1_by_reviewer <- function(m, base, reviewers) {
  vapply(reviewers, function(rv) {
    d <- paired_answers(m, base, rv)
    if (is.null(d)) NA_real_ else gwet_ac1(d$a, d$r)
  }, numeric(1))
}

n_by_reviewer <- function(m, base, reviewers) {
  vapply(reviewers, function(rv) {
    d <- paired_answers(m, base, rv)
    if (is.null(d)) NA_real_ else nrow(d)
  }, numeric(1))
}

tool_rows <- trimws(as.character(sum1[[1]]))

ac1_long <- reg %>% select(base, display, r1name) %>%
  mutate(tool_order = match(r1name, tool_rows),
         `1st` = map(base, ~ac1_by_reviewer(M1, .x, REV_SRC)),
         `2nd` = map(base, ~ac1_by_reviewer(M2, .x, REV_SRC)),
         n1    = map(base, ~n_by_reviewer(M1, .x, REV_SRC)),
         n2    = map(base, ~n_by_reviewer(M2, .x, REV_SRC))) %>%
  select(-r1name) %>%
  pivot_longer(c(`1st`, `2nd`), names_to = "round", values_to = "value") %>%
  mutate(reviewer = list(REV_LABELS)) %>%
  unnest(c(value, reviewer)) %>%
  select(base, display, tool_order, round, reviewer, value) %>%
  arrange(tool_order, round, match(reviewer, REV_LABELS))

stopifnot(!anyNA(ac1_long$tool_order), nrow(ac1_long) == 31 * 2 * 13)

ac1_item <- ac1_long %>%
  group_by(base, display, tool_order, round) %>%
  summarise(m = mean(value, na.rm = TRUE), .groups = "drop") %>%
  pivot_wider(names_from = round, values_from = m) %>%
  arrange(tool_order) %>%
  transmute(display, tool_order, round_1 = `1st`, round_2 = `2nd`, change = `2nd` - `1st`)

## --- change legend bins ---------------------------------------------------------------
## ⚠ The shared bins run to +/-0.5 in 0.1 steps and bucket_change() returns NA outside that
## range, which make_fig() draws as an uncoloured grey tile rather than failing. AC1 moves
## further between rounds than percent agreement does - up to +0.65 here - so one cell would
## have gone out blank. Widen the bins to 0.2 and run them to +/-0.7: symmetric about the
## neutral band, 7 levels, still inside what the RdBu palette can colour. make_fig() resolves
## both names at call time, so redefining them here rebinds only this figure's legend.
labels_all <- c("(0.5, 0.7]", "(0.3, 0.5]", "(0.1, 0.3]", "[-0.1, 0.1]",
                "(-0.3, -0.1]", "(-0.5, -0.3]", "(-0.7, -0.5]")
bucket_change <- function(v) dplyr::case_when(
  v >= -0.1 & v <=  0.1 ~ "[-0.1, 0.1]",
  v >   0.5 & v <=  0.7 ~ "(0.5, 0.7]",
  v >   0.3 & v <=  0.5 ~ "(0.3, 0.5]",
  v >   0.1 & v <=  0.3 ~ "(0.1, 0.3]",
  v >  -0.3 & v <= -0.1 ~ "(-0.3, -0.1]",
  v >  -0.5 & v <= -0.3 ~ "(-0.5, -0.3]",
  v >  -0.7 & v <= -0.5 ~ "(-0.7, -0.5]",
  TRUE ~ NA_character_
)
stopifnot(!anyNA(bucket_change(ac1_item$change)))

## --- what the figures are allowed to assert -----------------------------------------
AC1_N <- reg %>% select(base) %>%
  mutate(n1 = map_dbl(base, ~mean(n_by_reviewer(M1, .x, REV_SRC), na.rm = TRUE)),
         n2 = map_dbl(base, ~mean(n_by_reviewer(M2, .x, REV_SRC), na.rm = TRUE)))
AC1_RANGE <- range(c(ac1_item$round_1, ac1_item$round_2), na.rm = TRUE)
AC1_CHANGE_RANGE <- range(ac1_item$change, na.rm = TRUE)
AC1_MEAN <- c(round_1 = mean(ac1_item$round_1), round_2 = mean(ac1_item$round_2))

cat(sprintf("\nGwet's AC1, all 31 items, 13 reviewers vs the two adjudicators\n"))
cat(sprintf("  item means span %.3f to %.3f ; change spans %.3f to %.3f\n",
            AC1_RANGE[1], AC1_RANGE[2], AC1_CHANGE_RANGE[1], AC1_CHANGE_RANGE[2]))
cat(sprintf("  average over the 31 items: round 1 %.3f - round 2 %.3f (change %+.4f)\n",
            AC1_MEAN[["round_1"]], AC1_MEAN[["round_2"]],
            AC1_MEAN[["round_2"]] - AC1_MEAN[["round_1"]]))
cat(sprintf("  paired answers per item-reviewer: round 1 up to %.0f, round 2 up to %.0f\n",
            max(AC1_N$n1, na.rm = TRUE), max(AC1_N$n2, na.rm = TRUE)))

## The point of the exercise: on the 11 items the tool reports as percent agreement,
## alpha collapses although the raters agreed. Quantify that rather than assert it.
alpha_pub <- perc_df %>% filter(display != "Average score") %>% select(display, a1 = round_1)
cmp <- ac1_item %>% inner_join(alpha_pub, by = "display")
cat(sprintf("  the %d officially-percent items: mean AC1 round 1 %.3f vs mean published percent %.3f\n",
            nrow(cmp), mean(cmp$round_1), mean(cmp$a1)))

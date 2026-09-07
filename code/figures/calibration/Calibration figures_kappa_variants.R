#######################################################################################
# Two Krippendorff's-alpha variants (Reviewer 3 excluded), all 31 items:
#  V2  "kappa for all items"    : mean of the 13 pairwise (each reviewer vs adjudicator)
#                                 Krippendorff alphas -- same method as the current alpha
#                                 figure, extended to every item.
#  V3  "alpha per round"        : ONE multi-rater Krippendorff alpha per round, computed
#                                 over all raters together (adjudicator + 13 reviewers).
# Undefined alpha (no variation, e.g. task round 2) is shown as a blank cell.
#######################################################################################
source("code/figures/calibration/Calibration figures_no_reviewer3.R")     # make_fig, long_final, reg, labels_all
library(irr); library(dplyr); library(tidyr); library(purrr)

SCRATCH <- "C:/Users/[USER]/AppData/Local/Temp/claude/C--Users-[USER]-OneDrive-Claude-code-projects-Applicaiton-of-LLM-to-causal-inference-topics/dc77ffcb-0bcb-4dc6-b177-52abe7d2fe3f/scratchpad"
FB <- read.csv(file.path(SCRATCH, "recoded_fallback_long.csv"))

mat_for <- function(rnd, it) {
  d <- FB %>% filter(round == rnd, item == it) %>% select(rater, paper, code) %>%
    pivot_wider(names_from = paper, values_from = code)
  d <- d[order(d$rater), ]
  list(rater = d$rater, m = as.matrix(d[, setdiff(names(d), "rater"), drop = FALSE]))
}
ka <- function(m) tryCatch(suppressWarnings(kripp.alpha(m, "nominal")$value), error = function(e) NA_real_)
apair <- function(adj, ri) { ok <- !is.na(adj) & !is.na(ri); if (sum(ok) < 2) return(NA_real_)
  ka(rbind(adj[ok], ri[ok])) }
REV <- setdiff(1:14, 3)                                       # 13 reviewers (R3 dropped)

avg_pair <- function(rnd, it) { x <- mat_for(rnd, it); adj <- x$m[x$rater == 0, ]
  mean(sapply(REV, function(i) apair(adj, x$m[x$rater == i, ])), na.rm = TRUE) }
multi <- function(rnd, it) { x <- mat_for(rnd, it)
  ka(x$m[x$rater %in% c(0, REV), , drop = FALSE]) }

# ---- assemble the two data frames ----
mk <- function(fun) {
  d <- reg %>% rowwise() %>%
    mutate(round_1 = fun(1, base), round_2 = fun(2, base)) %>% ungroup() %>%
    arrange(order) %>% transmute(display, round_1, round_2, change = round_2 - round_1)
  bind_rows(d, tibble(display = "Average score",
                      round_1 = mean(d$round_1, na.rm = TRUE), round_2 = mean(d$round_2, na.rm = TRUE),
                      change  = mean(d$change,  na.rm = TRUE)))
}
# V2: alpha items keep official values; percent items use computed pairwise-avg
official <- long_final %>% filter(stat == "alpha") %>% group_by(base, round) %>%
  summarise(m = mean(value, na.rm = TRUE), .groups = "drop") %>%
  mutate(round = ifelse(round == "1st", 1, 2))
v2 <- reg %>% rowwise() %>%
  mutate(round_1 = if (stat == "alpha") official$m[official$base == base & official$round == 1] else avg_pair(1, base),
         round_2 = if (stat == "alpha") official$m[official$base == base & official$round == 2] else avg_pair(2, base)) %>%
  ungroup() %>% arrange(order) %>% transmute(display, round_1, round_2, change = round_2 - round_1)
v2_df <- bind_rows(v2, tibble(display = "Average score",
                              round_1 = mean(v2$round_1, na.rm = TRUE), round_2 = mean(v2$round_2, na.rm = TRUE),
                              change  = mean(v2$change,  na.rm = TRUE)))
v3_df <- mk(multi)

cat("V2 change range:", round(range(v2$change, na.rm = TRUE), 2),
    " | V3 change range:", round(range(v3_df$change[-nrow(v3_df)], na.rm = TRUE), 2), "\n")
cat("V2 mean change =", round(tail(v2_df,1)$change, 3), " | V3 mean change =", round(tail(v3_df,1)$change, 3), "\n")

save_fig <- function(df, title, file) {
  p <- make_fig(df, title, cont_limits = c(-1, 1), title_hjust = 0.5,
                legend_key_cm = 0.8, legend_bar_cm = 4.5, cont_name = "Krippendorff's α\n(centre 0)",
                change_discrete = FALSE)
  ggsave(file, p, path = ".", width = 11, height = 0.44 * nrow(df) + 1.6,
         units = "in", dpi = 500, bg = "white")
  cat("Saved:", file, "\n")
}
save_fig(v2_df, "Krippendorff's α averaged over the 13 reviewers — all items",
         "outputs/figures/Krippendorff alpha_ALL items avg-pairwise_excl_R3.png")
save_fig(v3_df, "Multi-rater Krippendorff's α per round (all raters together) — all items",
         "outputs/figures/Krippendorff alpha_ALL items multirater_excl_R3.png")

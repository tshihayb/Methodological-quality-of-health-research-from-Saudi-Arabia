#######################################################################################
# ALL-PERCENT-AGREEMENT calibration heatmap (Reviewer 3 excluded).
# Every tool item is shown as PERCENT AGREEMENT in both rounds (like-to-like).
#   - the 11 items already reported as percent keep their official values (code/figures/calibration/Calibration_data_final.R)
#   - the 20 items previously reported as Krippendorff's alpha are recomputed as percent
#     agreement (exact-match proportion of calibration papers, pairwise-complete, new rev 5)
#######################################################################################

source("code/figures/calibration/Calibration figures_no_reviewer3.R")   # make_fig, labels_all, long_final, reg (+ data)
library(dplyr); library(tidyr)

SCRATCH <- "C:/Users/[USER]/AppData/Local/Temp/claude/C--Users-[USER]-OneDrive-Claude-code-projects-Applicaiton-of-LLM-to-causal-inference-topics/dc77ffcb-0bcb-4dc6-b177-52abe7d2fe3f/scratchpad"
ap <- read.csv(file.path(SCRATCH, "all_percent_long.csv"))   # base, round(1/2), reviewer(1..14), percent

alpha_bases <- reg$base[reg$stat == "alpha"]

# 20 former-alpha items: recomputed percent agreement (drop Reviewer 3, average the 13)
perc_alpha <- ap %>%
  filter(base %in% alpha_bases, reviewer != 3) %>%
  mutate(round = ifelse(round == 1, "1st", "2nd")) %>%
  group_by(base, round) %>% summarise(m = mean(percent, na.rm = TRUE), .groups = "drop")

# 11 percent items: official values already in long_final
perc_pct <- long_final %>% filter(stat == "percent") %>%
  group_by(base, round) %>% summarise(m = mean(value, na.rm = TRUE), .groups = "drop")

allm <- bind_rows(perc_alpha, perc_pct) %>%
  left_join(reg %>% select(base, display, order), by = "base")

df <- allm %>% pivot_wider(names_from = round, values_from = m) %>% arrange(order) %>%
  transmute(display, round_1 = `1st`, round_2 = `2nd`, change = `2nd` - `1st`)
all_perc_df <- bind_rows(df, tibble(display = "Average score",
  round_1 = mean(df$round_1), round_2 = mean(df$round_2),
  change  = mean(df$round_2) - mean(df$round_1)))

cat("Change range:", round(range(df$change), 3), " (bins cover -0.5..0.5)\n")
cat("All-percent mean change =", round(tail(all_perc_df, 1)$change, 4), "\n")

# Percent centred at 0.5 (limits 0..1); one panel, 31 items + Average score.
p <- make_fig(all_perc_df,
              "Percent agreement between each reviewer and the two adjudicators (all tool items)",
              cont_limits = c(0, 1), title_hjust = 0.5,
              legend_key_cm = 0.8, legend_bar_cm = 4.5,
              cont_name = "Percent\nagreement")

ny <- nrow(all_perc_df)
ggsave("outputs/figures/Percent agreement_ALL items_excl_R3.png", p, path = ".",
       width = 10.5, height = 0.44 * ny + 1.6, units = "in", dpi = 500, bg = "white")
cat("Saved: outputs/figures/Percent agreement_ALL items_excl_R3.png\n")

#######################################################################################
# ALL-PERCENT calibration figure, items in TOOL ORDER (Reviewer 3 excluded).
#
#   "C:/Program Files/R/R-4.5.2/bin/Rscript.exe" \
#     "code/figures/calibration/08_21_2026_all_percent_tool_order.R"
#
# The published two-panel figure splits the instrument by statistic: 20 items as
# Krippendorff's alpha in panel A, 11 as percent agreement in panel B. That makes the two
# halves incomparable and orders the items by statistic rather than by the order a
# reviewer meets them. This version puts every item on percent agreement, on one scale,
# in tool order.
#
# The percent values, the definition behind them and the validation against the 11
# officially-percent items all come from
# code/figures/calibration/08_21_2026_percent_by_reviewer.R.
# Its companion figure is 08_21_2026_S5a_all_percent_heatmap.R, which shows the same
# numbers per reviewer rather than averaged.
#######################################################################################

source("code/figures/calibration/08_21_2026_percent_by_reviewer.R")   # pct_item, make_fig
library(dplyr); library(ggplot2); library(cowplot)

STAMP <- "08_21_2026"
OUT   <- sprintf("outputs/figures/%s_calibration_all_percent_tool_order", STAMP)

df <- pct_item %>% select(display, round_1, round_2, change)
all_perc_df <- bind_rows(df, tibble(
  display = "Average score", round_1 = mean(df$round_1), round_2 = mean(df$round_2),
  change  = mean(df$round_2) - mean(df$round_1)))
stopifnot(nrow(all_perc_df) == 32)

cat(sprintf("Change range %.3f to %.3f (the legend bins cover -0.5 to 0.5)\n",
            min(df$change), max(df$change)))
stopifnot(max(abs(df$change)) <= 0.5)

p <- make_fig(all_perc_df, title = NULL, cont_limits = c(0, 1), title_hjust = 0,
              legend_key_cm = 0.8, legend_bar_cm = 4.5,
              cont_name = "Percent\nagreement\n(rounds 1 & 2)") +
  theme(axis.text.y = element_text(size = 11))

# Two subtitle lines rather than one: a single line overran the 11.5 in canvas.
title <- ggdraw() +
  draw_label("Inter-rater calibration across two rounds — all items on percent agreement",
             fontface = "bold", size = 16, x = 0.01, hjust = 0, y = 0.80) +
  draw_label(paste("Within each round, every cell is the average across the 13 reviewers of",
                   "that reviewer's agreement with the two adjudicators (TSA and YA)."),
             size = 12, x = 0.01, hjust = 0, y = 0.46) +
  draw_label("Items appear in the order they are asked in the tool.",
             size = 12, x = 0.01, hjust = 0, y = 0.16)
final <- plot_grid(title, p, ncol = 1, rel_heights = c(0.075, 0.925))

FIG <- list(width = 11.5, height = 0.42 * nrow(all_perc_df) + 2.2, units = "in", bg = "white")
do.call(ggsave, c(list(filename = paste0(OUT, ".png"), plot = final, dpi = 600), FIG))
do.call(ggsave, c(list(filename = paste0(OUT, ".pdf"), plot = final, device = cairo_pdf), FIG))
do.call(ggsave, c(list(filename = paste0(OUT, ".tif"), plot = final, dpi = 600,
                       device = "tiff", compression = "lzw"), FIG))
for (f in paste0(OUT, c(".png", ".pdf", ".tif")))
  cat(sprintf("Saved: %-62s %7.1f KB\n", f, file.info(f)$size / 1024))

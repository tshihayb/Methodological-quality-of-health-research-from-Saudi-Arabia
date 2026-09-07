#######################################################################################
# ALL-AC1 calibration figure, items in TOOL ORDER, averaged over the 13 reviewers.
#
#   "C:/Program Files/R/R-4.5.2/bin/Rscript.exe" \
#     "code/figures/calibration/08_28_2026_all_ac1_tool_order.R"
#
# The counterpart of 08_21_2026_all_percent_tool_order.R. That one answers the paradox by
# dropping chance correction; this one answers it by keeping chance correction and using a
# coefficient that survives an invariant item. Both are shown because they fail in
# opposite directions, and the reader should be able to see that.
#
# Every number in the subtitle and the caption is computed here, never typed.
#######################################################################################

source("code/figures/calibration/08_28_2026_ac1_by_reviewer.R")  # ac1_item, ac1_long, make_fig
library(dplyr); library(ggplot2); library(cowplot)

STAMP <- "08_28_2026"
OUT   <- sprintf("outputs/figures/%s_calibration_all_ac1_tool_order", STAMP)

df <- ac1_item %>% select(display, round_1, round_2, change)
all_ac1_df <- bind_rows(df, tibble(
  display = "Average score", round_1 = mean(df$round_1), round_2 = mean(df$round_2),
  change  = mean(df$round_2) - mean(df$round_1)))
stopifnot(nrow(all_ac1_df) == 32)

# --- asserted facts: the caption may state these and nothing else ---------------------
LIMITS   <- c(-1, 1)
VAL_RANGE <- range(c(df$round_1, df$round_2))
CH_RANGE  <- range(df$change)
AVG       <- tail(all_ac1_df, 1)
stopifnot(VAL_RANGE[1] >= LIMITS[1], VAL_RANGE[2] <= LIMITS[2],
          !anyNA(bucket_change(all_ac1_df$change)))
N_NEG <- sum(df$round_1 < 0 | df$round_2 < 0)
cat(sprintf("AC1 item values span %.3f to %.3f ; %d of 31 items are negative in a round\n",
            VAL_RANGE[1], VAL_RANGE[2], N_NEG))
cat(sprintf("Change spans %.3f to %.3f\n", CH_RANGE[1], CH_RANGE[2]))

p <- make_fig(all_ac1_df, title = NULL, cont_limits = LIMITS, title_hjust = 0,
              legend_key_cm = 0.8, legend_bar_cm = 4.5,
              cont_name = "Gwet's AC\u2081\n(rounds 1 & 2)",
              change_name = "Change (\u0394)\n(0.2 bins; center inclusive)") +
  theme(axis.text.y = element_text(size = 11))

title <- ggdraw() +
  draw_label("Inter-rater calibration across two rounds \u2014 all items on Gwet's AC\u2081",
             fontface = "bold", size = 16, x = 0.01, hjust = 0, y = 0.80) +
  draw_label(paste("Within each round, every cell is the average across the 13 reviewers of",
                   "that reviewer's agreement with the two adjudicators (TSA and YA)."),
             size = 12, x = 0.01, hjust = 0, y = 0.46) +
  draw_label("Items appear in the order they are asked in the tool.",
             size = 12, x = 0.01, hjust = 0, y = 0.16)

# \u26a0 draw_label does not wrap: a line longer than the canvas is silently cut off at the
# right edge. Every line here is broken by hand and kept under ~120 characters at 10 pt
# across 11.5 in.
caption <- ggdraw() +
  draw_label(sprintf(paste0(
    "AC\u2081 is chance-corrected, but unlike Krippendorff's alpha its chance term does not\n",
    "collapse when one response category dominates, so a near-invariant item is not scored\n",
    "as disagreement. Averaged over the 31 items, AC\u2081 rises from %.2f to %.2f. Calibration used\n",
    "10 papers in round 1 and 3 in round 2, so each cell rests on at most that many answers."),
    AVG$round_1, AVG$round_2),
    size = 10, colour = "grey30", x = 0.008, hjust = 0, vjust = 1, y = 0.98)

final <- plot_grid(title, p, caption, ncol = 1, rel_heights = c(0.070, 0.865, 0.065))

# +3.0 rather than +2.4: the caption is four lines, not two.
FIG <- list(width = 11.5, height = 0.42 * nrow(all_ac1_df) + 3.0, units = "in", bg = "white")
do.call(ggsave, c(list(filename = paste0(OUT, ".png"), plot = final, dpi = 600), FIG))
do.call(ggsave, c(list(filename = paste0(OUT, ".pdf"), plot = final, device = cairo_pdf), FIG))
do.call(ggsave, c(list(filename = paste0(OUT, ".tif"), plot = final, dpi = 600,
                       device = "tiff", compression = "lzw"), FIG))
for (f in paste0(OUT, c(".png", ".pdf", ".tif")))
  cat(sprintf("Saved: %-62s %7.1f KB\n", f, file.info(f)$size / 1024))

#######################################################################################
# ALL-AC1 calibration matrix: reviewers as columns, one metric, one scale.
#
#   "C:/Program Files/R/R-4.5.2/bin/Rscript.exe" \
#     "code/figures/calibration/08_28_2026_ac1_heatmap.R"
#
# The per-reviewer counterpart of 08_28_2026_all_ac1_tool_order.R, and the AC1 counterpart
# of 08_21_2026_S5a_all_percent_heatmap.R. Gwet's AC1 is defined and validated in
# code/figures/calibration/08_28_2026_ac1_by_reviewer.R.
#######################################################################################

source("code/figures/calibration/08_28_2026_ac1_by_reviewer.R")  # ac1_long, REV_LABELS
library(ggplot2); library(dplyr); library(forcats); library(cowplot)

STAMP <- "08_28_2026"
OUT <- sprintf("outputs/figures/%s_calibration_matrix_all_ac1", STAMP)

wrap2 <- function(x, w = 34) vapply(x, function(s) {
  if (nchar(s) <= w) return(s)
  wds <- strsplit(s, "\\s+")[[1]]
  cum <- cumsum(nchar(wds) + 1); b <- which.min(abs(cum - max(cum) / 2))
  paste(paste(wds[1:b], collapse = " "), paste(wds[(b + 1):length(wds)], collapse = " "),
        sep = "\n")
}, character(1))

avg <- ac1_long %>% group_by(display, tool_order, round) %>%
  summarise(value = mean(value, na.rm = TRUE), .groups = "drop") %>% mutate(reviewer = "Avg")

heat <- bind_rows(ac1_long %>% select(display, tool_order, round, reviewer, value), avg) %>%
  mutate(reviewer  = factor(reviewer, levels = c(REV_LABELS, "Avg")),
         round_lab = recode(round, "1st" = "Round 1", "2nd" = "Round 2"),
         item      = fct_rev(factor(wrap2(display),
                                    levels = unique(wrap2(ac1_item$display)))))

# --- asserted facts -------------------------------------------------------------------
CELL_RANGE <- range(heat$value, na.rm = TRUE)
LIMITS <- c(-1, 1)
stopifnot(CELL_RANGE[1] >= LIMITS[1], CELL_RANGE[2] <= LIMITS[2])
N_CELLS <- sum(!is.na(heat$value))
cat(sprintf("Per-reviewer AC1 cells span %.3f to %.3f over %d cells\n",
            CELL_RANGE[1], CELL_RANGE[2], N_CELLS))

p <- ggplot(heat, aes(reviewer, item, fill = value)) +
  geom_tile(colour = "white", linewidth = 0.5) +
  geom_text(aes(label = ifelse(is.na(value), "", sprintf("%.1f", value))),
            size = 2.6, colour = "black") +
  facet_wrap(~round_lab, nrow = 1) +
  scale_fill_distiller(palette = "RdBu", direction = 1, limits = LIMITS,
                       na.value = "grey92", name = "Gwet's AC\u2081\n(centre 0)") +
  scale_x_discrete(position = "top", expand = expansion(0)) +
  scale_y_discrete(expand = expansion(0)) +
  labs(x = NULL, y = NULL) +
  theme_minimal(base_size = 11) +
  theme(panel.grid = element_blank(),
        axis.text.y = element_text(size = 8.5, lineheight = 0.9),
        axis.text.x = element_text(size = 9),
        strip.text = element_text(face = "bold", size = 13),
        legend.position = "right",
        legend.key.height = unit(1.6, "cm"))

title <- ggdraw() +
  draw_label("Calibration by reviewer and item \u2014 all items on Gwet's AC\u2081",
             fontface = "bold", size = 15, x = 0.008, hjust = 0, y = 0.78) +
  draw_label(paste("Each cell is one reviewer's agreement with the two adjudicators (TSA and YA)",
                   "on that item, in that round."),
             size = 11, x = 0.008, hjust = 0, y = 0.46) +
  draw_label("Items appear in the order they are asked in the tool.",
             size = 11, x = 0.008, hjust = 0, y = 0.16)

caption <- ggdraw() +
  draw_label(paste("'Avg' is the mean across the 13 reviewers. AC\u2081 is chance-corrected but,",
                   "unlike Krippendorff's alpha, does not collapse when one response category",
                   "dominates.\nCalibration used 10 papers in round 1 and 3 in round 2, so a cell",
                   "rests on at most that many paired answers and single cells should not be read closely."),
             size = 9.5, colour = "grey30", x = 0.008, hjust = 0)

final <- plot_grid(title, p, caption, ncol = 1, rel_heights = c(0.055, 0.915, 0.03))

FIG <- list(width = 14, height = 13, units = "in", bg = "white")
do.call(ggsave, c(list(filename = paste0(OUT, ".png"), plot = final, dpi = 600), FIG))
do.call(ggsave, c(list(filename = paste0(OUT, ".pdf"), plot = final, device = cairo_pdf), FIG))
do.call(ggsave, c(list(filename = paste0(OUT, ".tif"), plot = final, dpi = 600,
                       device = "tiff", compression = "lzw"), FIG))
for (f in paste0(OUT, c(".png", ".pdf", ".tif")))
  cat(sprintf("Saved: %-62s %7.1f KB\n", f, file.info(f)$size / 1024))

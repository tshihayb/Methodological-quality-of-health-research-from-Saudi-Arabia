#######################################################################################
# Supplementary Figure S5a, ALL-PERCENT version: reviewers as columns, one metric.
#
#   "C:/Program Files/R/R-4.5.2/bin/Rscript.exe" \
#     "code/figures/calibration/08_21_2026_S5a_all_percent_heatmap.R"
#
# The published S5a splits the instrument in two - 20 items as Krippendorff's alpha in
# panel A, 11 as percent agreement in panel B - each on its own colour scale, so a cell
# in one panel cannot be read against a cell in the other. This version puts every item
# on percent agreement, one scale, one panel, in the order the tool asks them.
#
# Percent agreement is recomputed for all 31 items by
# code/figures/calibration/08_21_2026_percent_by_reviewer.R, which documents the
# definition and prints its validation against the 11 officially-percent items.
#######################################################################################

source("code/figures/calibration/08_21_2026_percent_by_reviewer.R")   # pct_long, REV_LABELS
library(ggplot2); library(dplyr); library(forcats); library(cowplot)

STAMP <- "08_21_2026"
OUT <- sprintf("outputs/figures/%s_S5a_calibration_matrix_all_percent", STAMP)

wrap2 <- function(x, w = 34) vapply(x, function(s) {
  if (nchar(s) <= w) return(s)
  wds <- strsplit(s, "\\s+")[[1]]
  cum <- cumsum(nchar(wds) + 1); b <- which.min(abs(cum - max(cum) / 2))
  paste(paste(wds[1:b], collapse = " "), paste(wds[(b + 1):length(wds)], collapse = " "),
        sep = "\n")
}, character(1))

## Reviewer columns, then the across-reviewer mean in its own column, as in the published
## figure. The mean is over the 13 reviewers, which is the number every other figure
## reports.
avg <- pct_long %>% group_by(display, tool_order, round) %>%
  summarise(value = mean(value), .groups = "drop") %>% mutate(reviewer = "Avg")

heat <- bind_rows(pct_long %>% select(display, tool_order, round, reviewer, value), avg) %>%
  mutate(reviewer  = factor(reviewer, levels = c(REV_LABELS, "Avg")),
         round_lab = recode(round, "1st" = "Round 1", "2nd" = "Round 2"),
         item      = fct_rev(factor(wrap2(display),
                                    levels = unique(wrap2(display[order(tool_order)])))))
stopifnot(nlevels(heat$item) == 31)

p <- ggplot(heat, aes(reviewer, item, fill = value)) +
  geom_tile(colour = "white", linewidth = 0.3) +
  geom_text(aes(label = sub("^0", "", sprintf("%.2f", value))), size = 2.2, colour = "grey15") +
  geom_vline(xintercept = length(REV_LABELS) + 0.5, colour = "grey40", linewidth = 0.5) +
  facet_wrap(~ round_lab, nrow = 1) +
  scale_fill_distiller(palette = "RdBu", direction = 1, limits = c(0, 1),
                       name = "Percent\nagreement\n(centre 0.5)") +
  scale_x_discrete(position = "top") +
  labs(x = NULL, y = NULL) +
  theme_minimal(base_size = 10) +
  theme(panel.grid = element_blank(),
        axis.text.x = element_text(size = 8),
        axis.text.y = element_text(size = 8),
        strip.text = element_text(face = "bold", size = 11),
        panel.spacing = unit(0.6, "lines"),
        legend.title = element_text(face = "bold"),
        legend.position = "right", legend.justification = "centre")

title <- ggdraw() +
  draw_label("Calibration by reviewer and item — all items on percent agreement",
             fontface = "bold", size = 15, x = 0.008, hjust = 0, y = 0.78) +
  draw_label(paste("Each cell is one reviewer's agreement with the two adjudicators (TSA and YA)",
                   "on that item, in that round."),
             size = 11, x = 0.008, hjust = 0, y = 0.46) +
  draw_label("Items appear in the order they are asked in the tool.",
             size = 11, x = 0.008, hjust = 0, y = 0.16)
# The recruitment note ("fourteen recruited, one withdrew") is deliberately not on the
# figure: it belongs in the Methods, not under every panel. What stays is the one thing
# the figure itself does not otherwise define - what the Avg column is.
caption <- ggdraw() +
  draw_label("'Avg' is the mean across the 13 reviewers.",
             size = 10, colour = "grey30", x = 0.008, hjust = 0)
final <- plot_grid(title, p, caption, ncol = 1, rel_heights = c(0.055, 0.925, 0.02))

FIG <- list(width = 14, height = 13, units = "in", bg = "white")
do.call(ggsave, c(list(filename = paste0(OUT, ".png"), plot = final, dpi = 600), FIG))
do.call(ggsave, c(list(filename = paste0(OUT, ".pdf"), plot = final, device = cairo_pdf), FIG))
do.call(ggsave, c(list(filename = paste0(OUT, ".tif"), plot = final, dpi = 600,
                       device = "tiff", compression = "lzw"), FIG))
for (f in paste0(OUT, c(".png", ".pdf", ".tif")))
  cat(sprintf("Saved: %-62s %7.1f KB\n", f, file.info(f)$size / 1024))

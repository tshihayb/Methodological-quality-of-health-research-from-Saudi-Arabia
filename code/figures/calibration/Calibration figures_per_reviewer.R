#######################################################################################
# Per-reviewer (pairwise) calibration figures, Reviewer 3 excluded (13 reviewers).
# Three views:
#   1) Per-item dot plot  : spread of the 13 reviewers per item + round means (dumbbell)
#   2) Per-reviewer summary: each reviewer's mean agreement, round 1 -> round 2 (dumbbell)
#   3) Expanded heatmap   : reviewers as columns within each round, next to the average
#
# ⚠ ONLY THE HEATMAP IS IN THE SUBMISSION PACKAGE, as Supplementary Figure S5 (2026-08-22,
# TSA).  The dot plot and the summary were S5b and S5c; they were taken out and moved to
# archive/retired-supplement-figures/, whose README says how to restore them.  This script
# is unchanged and still writes all three to outputs/figures/ - so a re-run recreates the
# two retired files there, and that is expected.  They simply are not collected any more:
# code/manuscript/08_16_2026_build_package.py has no put() line for them.
#######################################################################################

source("code/figures/calibration/Calibration figures_no_reviewer3.R")   # gives get_vals(), r1_raw, r2_raw, alpha_map, perc_map
library(ggplot2); library(dplyr); library(tidyr); library(forcats); library(purrr)
library(patchwork); library(RColorBrewer)

set.seed(1)                                     # stable jitter
ROUND_COL <- c("1st" = "#E69F00", "2nd" = "#0072B2")          # Okabe-Ito orange / blue

# --- Corrected per-reviewer table (13 reviewers, like-to-like) from the data module ---
# metric column re-labels reg$stat; order preserves the item ordering used elsewhere.
long <- long_final %>% rename(metric = stat)

wrap2 <- function(x, w = 32) vapply(x, function(s){
  if (nchar(s) <= w) return(s); wds <- strsplit(s, "\\s+")[[1]]
  cum <- cumsum(nchar(wds)+1); b <- which.min(abs(cum - max(cum)/2))
  paste(paste(wds[1:b], collapse=" "), paste(wds[(b+1):length(wds)], collapse=" "), sep="\n")
}, character(1))

#######################################################################################
# View 1: Per-item dot plot (13 reviewers) with round means as a dumbbell
#######################################################################################
item_mean <- long %>% group_by(metric, display, order, round) %>%
  summarise(m = mean(value), .groups = "drop")

dotplot_panel <- function(met, xlab, title) {
  dd <- long %>% filter(metric == met) %>%
    mutate(item = fct_rev(factor(display, levels = unique(display[order(order)]))),
           yi = as.integer(item),
           yoff = ifelse(round == "1st", 0.20, -0.20),
           yj = yi + yoff + runif(n(), -0.06, 0.06))
  mm <- item_mean %>% filter(metric == met) %>%
    mutate(item = fct_rev(factor(display, levels = unique(display[order(order)]))),
           yi = as.integer(item), yoff = ifelse(round == "1st", 0.20, -0.20), ypos = yi + yoff)
  mw <- mm %>% select(item, yi, round, m) %>% pivot_wider(names_from = round, values_from = m)
  ggplot() +
    geom_hline(yintercept = seq_len(nlevels(dd$item)) + 0.5, colour = "grey93") +
    geom_segment(data = mw, aes(x = `1st`, xend = `2nd`, y = yi + 0.20, yend = yi - 0.20),
                 colour = "grey60", linewidth = 0.4) +
    geom_point(data = dd, aes(value, yj, colour = round), size = 1.5, alpha = 0.45) +
    geom_point(data = mm, aes(m, ypos, fill = round), shape = 23, size = 2.6,
               colour = "black", stroke = 0.4) +
    scale_colour_manual(values = ROUND_COL, name = "Round") +
    scale_fill_manual(values = ROUND_COL, name = "Round") +
    scale_y_continuous(breaks = seq_len(nlevels(dd$item)),
                       labels = wrap2(levels(dd$item)), expand = expansion(add = 0.6)) +
    labs(title = title, x = xlab, y = NULL) +
    theme_minimal(base_size = 11) +
    theme(panel.grid = element_blank(), axis.text.y = element_text(size = 10),
          plot.title = element_text(face = "bold", size = 13))
}
pA <- dotplot_panel("alpha",  "Krippendorff's α (each reviewer vs adjudicators)", "A  Krippendorff's α items") +
  geom_vline(xintercept = 0, colour = "grey75", linetype = 2)
pB <- dotplot_panel("percent", "Percent agreement (each reviewer vs adjudicators)", "B  Percent-agreement items")
dot_fig <- pA / pB + plot_layout(heights = c(20, 11), guides = "collect") &
  theme(legend.position = "bottom")
ggsave("outputs/figures/Calibration_perreviewer_dotplot_excl_R3.png", dot_fig,
       width = 9.5, height = 13, units = "in", dpi = 600, bg = "white")

#######################################################################################
# View 2: Per-reviewer summary - mean agreement across items, round 1 -> round 2
#######################################################################################
rev_mean <- long %>% group_by(metric, reviewer, round) %>%
  summarise(m = mean(value), .groups = "drop")
overall  <- rev_mean %>% group_by(metric, round) %>% summarise(m = mean(m), .groups = "drop")

summary_panel <- function(met, xlab, title) {
  w <- rev_mean %>% filter(metric == met) %>%
    pivot_wider(names_from = round, values_from = m) %>%
    mutate(reviewer = fct_reorder(reviewer, `2nd`))
  ov <- overall %>% filter(metric == met)
  ggplot(w, aes(y = reviewer)) +
    geom_vline(data = ov, aes(xintercept = m, linetype = round), colour = "grey55") +
    geom_segment(aes(x = `1st`, xend = `2nd`, yend = reviewer), colour = "grey65", linewidth = 0.7) +
    geom_point(aes(x = `1st`, colour = "1st"), size = 3) +
    geom_point(aes(x = `2nd`, colour = "2nd"), size = 3) +
    scale_colour_manual(values = ROUND_COL, name = "Round") +
    scale_linetype_manual(values = c("1st" = 3, "2nd" = 1), name = "Overall mean") +
    labs(title = title, x = xlab, y = NULL) +
    theme_minimal(base_size = 11) +
    theme(panel.grid.major.y = element_blank(),
          plot.title = element_text(face = "bold", size = 13))
}
sA <- summary_panel("alpha",  "Mean Krippendorff's α across items", "A  Krippendorff's α")
sB <- summary_panel("percent","Mean percent agreement across items", "B  Percent agreement")
sum_fig <- sA / sB + plot_layout(guides = "collect") &
  theme(legend.position = "bottom")
ggsave("outputs/figures/Calibration_perreviewer_summary_excl_R3.png", sum_fig,
       width = 8.5, height = 8, units = "in", dpi = 600, bg = "white")

#######################################################################################
# View 3: Expanded heatmap - reviewers as columns within each round + Average column
#######################################################################################
heat <- long %>%
  bind_rows(item_mean %>% transmute(metric, display, order, round, reviewer = "Avg", value = m)) %>%
  mutate(reviewer = factor(reviewer, levels = c(REVIEWERS, "Avg")),
         round_lab = recode(round, "1st" = "Round 1", "2nd" = "Round 2"))

# Each panel gets its own RdBu scale: alpha centered at 0 (limits -1..1); percent
# centered at 0.5 (limits 0..1). Two separate legends are collected on the right.
heat_panel <- function(met, title, fill_limits, fill_name) {
  d <- heat %>% filter(metric == met) %>%
    mutate(item = fct_rev(factor(display, levels = unique(display[order(order)]))))
  ggplot(d, aes(reviewer, item, fill = value)) +
    geom_tile(colour = "white", linewidth = 0.3) +
    geom_text(aes(label = sprintf("%.1f", value)), size = 2.1, colour = "grey15") +
    geom_vline(xintercept = length(REVIEWERS) + 0.5, colour = "grey40", linewidth = 0.5) +
    facet_wrap(~ round_lab, nrow = 1) +
    scale_fill_distiller(palette = "RdBu", direction = 1, limits = fill_limits,
                         name = fill_name) +
    scale_x_discrete(position = "top") +
    labs(title = title, x = NULL, y = NULL) +
    theme_minimal(base_size = 10) +
    theme(panel.grid = element_blank(),
          axis.text.x = element_text(size = 8),
          axis.text.y = element_text(size = 8),
          strip.text = element_text(face = "bold", size = 11),
          plot.title = element_text(face = "bold", size = 13),
          panel.spacing = unit(0.6, "lines"),
          legend.title = element_text(face = "bold"))
}
hA <- heat_panel("alpha",   "A  Krippendorff's α items",   c(-1, 1), "Krippendorff's α\n(centre 0)")
hB <- heat_panel("percent", "B  Percent-agreement items",  c( 0, 1), "Percent agreement\n(centre 0.5)")
# No guide collection: each panel keeps its own legend, vertically centred in its panel.
heat_fig <- (hA / hB + plot_layout(heights = c(20, 11))) +
  plot_annotation(
    caption = paste0(
      "Agreement between each of the 13 reviewers (R1-R13) and the two adjudicators, by item and calibration round.\n",
      "Fourteen reviewers were recruited; one withdrew before data collection and is not shown. ",
      "'Avg' is the mean across the 13 reviewers."),
    theme = theme(plot.caption = element_text(hjust = 0, size = 10, colour = "grey30",
                                              margin = margin(t = 8)))) &
  theme(legend.position = "right", legend.justification = "centre")
# Supplementary Figure S5 ships in all three renditions, 2026-08-26 (TSA asked for the TIFF
# and the PDF).  Same recipe as S10/S11 in 08_21_2026_S5a_all_percent_heatmap.R: one geometry
# used for all three, PNG and TIFF at 600 dpi, PDF through cairo_pdf so the fonts embed rather
# than being drawn as outlines.  ⚠ The PNG was dpi = 500 until this change; it is 600 now so
# the three renditions cannot disagree about resolution.
S5_OUT <- "outputs/figures/Calibration_perreviewer_heatmap_excl_R3"
S5_FIG <- list(plot = heat_fig, width = 14, height = 13, units = "in", bg = "white")
do.call(ggsave, c(list(filename = paste0(S5_OUT, ".png"), dpi = 600), S5_FIG))
do.call(ggsave, c(list(filename = paste0(S5_OUT, ".pdf"), device = cairo_pdf), S5_FIG))
do.call(ggsave, c(list(filename = paste0(S5_OUT, ".tif"), dpi = 600,
                       device = "tiff", compression = "lzw"), S5_FIG))

cat("Saved 3 per-reviewer figures.\n")

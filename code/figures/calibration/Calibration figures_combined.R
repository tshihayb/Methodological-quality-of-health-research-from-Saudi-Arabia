#######################################################################################
# Combined two-panel calibration figure for publication (Reviewer 3 excluded).
# Panel A: Krippendorff's alpha items ; Panel B: Percent-agreement items.
# Legends are placed individually: the alpha colourbar is centred beside Panel A, the
# percent colourbar centred beside Panel B, and the shared Change (delta) legend sits
# between the two panels.
#######################################################################################

source("code/figures/calibration/Calibration figures_no_reviewer3.R")   # alpha_df / perc_df / make_fig / labels_all
library(patchwork); library(cowplot); library(grid)

# --- Two panels, NO legends (colours retained), tagged A / B --------------------------
pA <- make_fig(alpha_df, title = NULL, cont_limits = c(-1, 1), title_hjust = 0,
               show_change_legend = FALSE) +
  theme(axis.text.x = element_blank(), axis.ticks.x = element_blank(),
        legend.position = "none", axis.text.y = element_text(size = 11)) + labs(tag = "A")
pB <- make_fig(perc_df, title = NULL, cont_limits = c(0, 1), title_hjust = 0,
               show_change_legend = FALSE) +
  theme(legend.position = "none", axis.text.y = element_text(size = 11)) + labs(tag = "B")
panels <- pA / pB +
  plot_layout(heights = c(nrow(alpha_df) + 0.2, nrow(perc_df) + 0.2)) &
  theme(plot.tag = element_text(size = 16, face = "bold"))

# --- Three standalone legend grobs ----------------------------------------------------
theme_leg <- theme(legend.title = element_text(size = 12, face = "bold"),
                   legend.text = element_text(size = 10), legend.position = "right")
cbar <- function(lims, nm) get_legend(
  ggplot(data.frame(x = 1, y = lims), aes(x, y, fill = y)) + geom_tile() +
    scale_fill_distiller(nm, palette = "RdBu", direction = 1, limits = lims,
      guide = guide_colourbar(barheight = unit(3.2, "cm"), barwidth = unit(0.6, "cm"))) +
    theme_leg)
leg_alpha <- cbar(c(-1, 1), "Krippendorff's α\n(rounds 1 & 2)")
leg_perc  <- cbar(c(0, 1),  "Percent agreement\n(rounds 1 & 2)")
leg_change <- get_legend(
  ggplot(data.frame(f = factor(labels_all, levels = labels_all)), aes(1, f, fill = f)) + geom_tile() +
    scale_fill_brewer("Change (Δ)\n(0.1 bins; center inclusive)", palette = "RdBu", direction = -1,
      limits = labels_all, guide = guide_legend(override.aes = list(alpha = 1))) +
    theme_leg + theme(legend.key.size = unit(0.5, "cm")))

# --- Legend column: alpha centred in A-region, change at the boundary, percent in B ---
fracA <- (nrow(alpha_df) + 0.2) / (nrow(alpha_df) + nrow(perc_df) + 0.4)   # top share (~0.635)
# The change legend has a 2-line title on top, so centring the whole grob would put its
# MIDDLE bin below the boundary. Shift it up by ~half the title height so the middle bin
# [-0.1, 0.1] lands on the panel boundary.
chg_shift <- 0.032
legcol <- ggdraw() +
  draw_grob(leg_alpha,  x = 0, y = 1 - fracA,        width = 1, height = fracA)       + # centred in A
  draw_grob(leg_perc,   x = 0, y = 0,                width = 1, height = 1 - fracA)   + # centred in B
  draw_grob(leg_change, x = 0, y = (1 - fracA) - 0.15 + chg_shift, width = 1, height = 0.30)  # middle bin at boundary

# --- Assemble: panels (left) + legends (right), with title / subtitle / caption -------
body <- plot_grid(panels, legcol, ncol = 2, rel_widths = c(0.72, 0.28))
title <- ggdraw() +
  draw_label("Inter-rater calibration across two rounds", fontface = "bold", size = 16, x = 0.01, hjust = 0, y = 0.72) +
  draw_label(paste("Within each round, every cell is the average across the 13 reviewers of that",
                   "reviewer's agreement with the two adjudicators (TSA and YA)"),
             size = 12, x = 0.01, hjust = 0, y = 0.24)
# No caption row: the subtraction is stated in the column label itself.
final <- plot_grid(title, body, ncol = 1, rel_heights = c(0.055, 0.945))

# --- submission renditions: vector PDF + 600 dpi TIFF and PNG -------------------------
# cairo_pdf rather than the default pdf() device: it embeds the fonts, and a PDF with
# unembedded fonts is the usual automatic rejection at journal production.
# TIFF is written through the cairo device for the same anti-aliasing as the PNG, LZW
# compressed because uncompressed 6,900 x 7,800 RGB is ~160 MB.
OUT <- "outputs/figures/Calibration_combined_excl_R3"
FIG <- list(width = 11.5, height = 13, units = "in", bg = "white")

do.call(ggsave, c(list(filename = paste0(OUT, ".png"), plot = final, dpi = 600), FIG))
do.call(ggsave, c(list(filename = paste0(OUT, ".pdf"), plot = final, device = cairo_pdf), FIG))
do.call(ggsave, c(list(filename = paste0(OUT, ".tif"), plot = final, dpi = 600,
                       device = "tiff", compression = "lzw", type = "cairo"), FIG))

for (f in paste0(OUT, c(".png", ".pdf", ".tif")))
  cat(sprintf("Saved: %-52s %7.1f KB\n", f, file.info(f)$size / 1024))
cat(sprintf("       %.1f x %.1f in  ·  %.0f x %.0f px at 600 dpi\n",
            FIG$width, FIG$height, FIG$width * 600, FIG$height * 600))

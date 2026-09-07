#######################################################################################
# Make the Percent-agreement figure match the Krippendorff figure in tile & text size.
#
# The two figures use identical tile/text code; they differed only because both were
# saved on a 10x10 canvas while the Krippendorff figure packs 21 rows and Percent only
# 12, so Percent's auto-sized panel stretched its tiles ~2x taller and ~1.6x wider.
#
# Fix: keep the same 10 in output WIDTH (so the two match when placed at equal width in
# the document) but (a) set the output HEIGHT so each row is the same 0.375 in as the
# Krippendorff figure, and (b) add left/right margin so the 3-column tile block is the
# same 2.05 in wide as the Krippendorff figure. Tile text (size 3.7) is already identical.
#######################################################################################

source("code/figures/calibration/Calibration figures_no_reviewer3.R")   # rebuilds perc_df / make_fig etc.
library(grid)

# --- Geometry matched to outputs/figures/Krippendorff's alpha_excl_R3.png (measured) ---
# per-row tile height 0.3752 in ; 3-column tile block 2.05 in wide ; 10 in canvas.
OUT_W     <- 10.0
PERROW_IN <- 0.3752
N_ROWS    <- nrow(perc_df)                 # 12 (11 items + Average score)
EXPAND    <- 0.2                            # discrete y expansion (0.6 each side -> span n+0.2... tiles span n)
OVERHEAD_H<- 0.72                           # vertical space for title + x-axis + margins (measured)
OUT_H     <- PERROW_IN * (N_ROWS + EXPAND) + OVERHEAD_H   # -> ~5.30 in
SIDE_MARG <- 0.80                           # per-side margin so the 3-col block matches alpha (603px spacing)

p_perc_matched <- make_fig(
  perc_df,
  "Average percent agreement between each reviewer and the two adjudicators",
  cont_limits = c(0, 1), title_hjust = 0.5,
  legend_key_cm = 0.6, legend_bar_cm = 3.5) +
  theme(plot.margin = unit(c(0.08, 0.08 + SIDE_MARG, 0.08, 0.08 + SIDE_MARG), "in"))

ggsave("outputs/figures/Percent agreement_excl_R3_matched.png", p_perc_matched,
       width = OUT_W, height = OUT_H, dpi = 600, bg = "white")

cat(sprintf("Saved outputs/figures/Percent agreement_excl_R3_matched.png  (%.2f x %.2f in)\n", OUT_W, OUT_H))

#######################################################################################
# Calibration heatmaps, Reviewer 3 excluded, LIKE-TO-LIKE across rounds.
# Data (corrected) comes from code/figures/calibration/Calibration_data_final.R (alpha_df / perc_df / long_final).
# This script defines make_fig() and saves the two standalone heatmaps.
#######################################################################################

source("code/figures/calibration/Calibration_data_final.R")   # -> alpha_df, perc_df, long_final, reg, REVIEWERS (+packages)

#######################################################################################
# Plot helper (discrete change bins; consistent legend order)
#######################################################################################
wrap_two_lines <- function(x, width = 35) {
  vapply(x, function(s) {
    s <- as.character(s)
    if (nchar(s) <= width) return(s)
    words <- strsplit(s, "\\s+")[[1]]
    cum <- cumsum(nchar(words) + 1)
    brk <- which.min(abs(cum - max(cum) / 2))
    paste0(paste(words[1:brk], collapse = " "), "\n",
           paste(words[(brk + 1):length(words)], collapse = " "))
  }, character(1))
}

labels_all <- c("(0.4, 0.5]", "(0.3, 0.4]", "(0.2, 0.3]", "(0.1, 0.2]", "[-0.1, 0.1]",
                "(-0.2, -0.1]", "(-0.3, -0.2]", "(-0.4, -0.3]", "(-0.5, -0.4]")
bucket_change <- function(v) dplyr::case_when(
  v >= -0.1 & v <=  0.1 ~ "[-0.1, 0.1]",
  v >   0.4 & v <=  0.5 ~ "(0.4, 0.5]",
  v >   0.3 & v <=  0.4 ~ "(0.3, 0.4]",
  v >   0.2 & v <=  0.3 ~ "(0.2, 0.3]",
  v >   0.1 & v <=  0.2 ~ "(0.1, 0.2]",
  v >  -0.2 & v <= -0.1 ~ "(-0.2, -0.1]",
  v >  -0.3 & v <= -0.2 ~ "(-0.3, -0.2]",
  v >  -0.4 & v <= -0.3 ~ "(-0.4, -0.3]",
  v >  -0.5 & v <= -0.4 ~ "(-0.5, -0.4]",
  TRUE ~ NA_character_
)

make_fig <- function(df, title, cont_limits, title_hjust,
                     legend_key_cm = 1, legend_bar_cm = NULL,
                     cont_name = "Calibration\nrounds",
                     show_change_legend = TRUE,
                     change_discrete = TRUE,
                     # ⚠ The bin width is part of this label. A caller that rebinds
                     # bucket_change()/labels_all must pass a matching name, or the legend
                     # asserts a bin width the tiles do not use. Default: the shared 0.1 bins.
                     change_name = "Change (Δ)\n(0.1 bins; center inclusive)") {
  df_long <- df %>%
    mutate(var_id_wrap = wrap_two_lines(display, 35),
           var_id = forcats::fct_rev(factor(var_id_wrap, levels = unique(var_id_wrap)))) %>%
    select(var_id, round_1, round_2, change) %>%
    pivot_longer(c(round_1, round_2, change), names_to = "Round", values_to = "Value") %>%
    # Column labels spell out what each column is. They are set on two lines because the
    # tiles are 0.6 units wide and "Change between rounds" on one line would run under
    # its neighbours.
    mutate(Round = recode(Round, round_1 = "1st\nround", round_2 = "2nd\nround",
                          change = "Change\nbetween rounds\n(2nd − 1st)"))

  round_levels <- c("1st\nround", "2nd\nround", "Change\nbetween rounds\n(2nd − 1st)")
  df12 <- df_long %>% filter(Round %in% c("1st\nround", "2nd\nround"))
  dfch <- df_long %>% filter(Round == "Change\nbetween rounds\n(2nd − 1st)") %>%
    mutate(ChangeCat = factor(bucket_change(Value), levels = labels_all))
  legend_df <- data.frame(ChangeCat = factor(labels_all, levels = labels_all), x = 1, y = 1)
  tile_width <- 0.6
  ny <- nlevels(df_long$var_id)

  p <- ggplot() +
    geom_tile(data = df12, aes(factor(Round, levels = round_levels), var_id, fill = Value),
              color = "white", linewidth = 0.7, width = tile_width) +
    geom_text(data = df12, aes(factor(Round, levels = round_levels), var_id,
                               label = ifelse(is.na(Value), "", as.character(round(Value, 2)))),
              size = 3.7, color = "black") +
    scale_x_discrete(limits = round_levels, drop = FALSE, expand = expansion(mult = c(0.01, 0.01))) +
    scale_fill_distiller(palette = "RdBu", direction = 1, name = cont_name, limits = cont_limits,
                         na.value = "grey92",
                         guide = guide_colourbar(order = 1,
                           barheight = if (is.null(legend_bar_cm)) NULL else unit(legend_bar_cm, "cm"))) +
    ggnewscale::new_scale_fill()

  if (change_discrete) {          # 0.1-wide binned change legend (default)
    p <- p +
      geom_tile(data = dfch, aes(factor(Round, levels = round_levels), var_id, fill = ChangeCat),
                color = "white", linewidth = 0.7, width = tile_width) +
      geom_text(data = dfch, aes(factor(Round, levels = round_levels), var_id,
                                 label = ifelse(is.na(Value), "", as.character(round(Value, 2)))),
                size = 3.7, color = "black") +
      geom_tile(data = legend_df, aes(x, y, fill = ChangeCat), alpha = 0, inherit.aes = FALSE, show.legend = TRUE) +
      scale_fill_brewer(palette = "RdBu", direction = -1,
                        name = change_name,
                        limits = labels_all, breaks = labels_all, drop = FALSE, na.translate = FALSE,
                        guide = if (show_change_legend) guide_legend(order = 2, override.aes = list(alpha = 1)) else "none")
  } else {                        # continuous change colourbar (handles any range)
    clim <- max(abs(dfch$Value), na.rm = TRUE)
    p <- p +
      geom_tile(data = dfch, aes(factor(Round, levels = round_levels), var_id, fill = Value),
                color = "white", linewidth = 0.7, width = tile_width) +
      geom_text(data = dfch, aes(factor(Round, levels = round_levels), var_id,
                                 label = ifelse(is.na(Value), "", as.character(round(Value, 2)))),
                size = 3.7, color = "black") +
      scale_fill_distiller(palette = "RdBu", direction = 1, name = "Change (Δ)",
                           limits = c(-clim, clim), na.value = "grey92",
                           guide = if (show_change_legend) guide_colourbar(order = 2,
                             barheight = if (is.null(legend_bar_cm)) NULL else unit(legend_bar_cm, "cm")) else "none")
  }

  p +
    annotate("segment", x = 2.5, xend = 2.5, y = 0.5, yend = ny + 0.5, linewidth = 0.6, colour = "grey70") +
    labs(title = title, x = NULL, y = NULL) +
    theme_minimal(base_size = 12) +
    theme(panel.grid = element_blank(),
          axis.text.y = element_text(size = 12),
          axis.text.x = element_text(size = 14, face = "bold"),
          plot.title  = element_text(size = 15, hjust = title_hjust, face = "bold"),
          legend.title = element_text(size = 14, face = "bold"),
          legend.text  = element_text(size = 12),
          legend.key.height = unit(legend_key_cm, "cm"),
          legend.key.width  = unit(1, "cm"))
}

#######################################################################################
# Save the two standalone heatmaps (Percent figure sized to match the alpha tiles)
#######################################################################################
p_alpha <- make_fig(alpha_df,
                    "Average Krippendorff's Alpha between each reviewer and the two adjudicators",
                    cont_limits = c(-1, 1), title_hjust = 0.7)

PERC_HEIGHT_IN <- 0.3752 * (nrow(perc_df) + 0.2) + 0.72   # match alpha tile height
PERC_SIDE_MARG <- 0.80                                    # match alpha tile width
p_perc <- make_fig(perc_df,
                   "Average percent agreement between each reviewer and the two adjudicators",
                   cont_limits = c(0, 1), title_hjust = 0.5,
                   legend_key_cm = 0.6, legend_bar_cm = 3.5) +
  theme(plot.margin = unit(c(0.08, 0.08 + PERC_SIDE_MARG, 0.08, 0.08 + PERC_SIDE_MARG), "in"))

ggsave("outputs/figures/Krippendorff's alpha_excl_R3.png", p_alpha, path = ".",
       width = 10, height = 10, units = "in", dpi = 600, bg = "white")
ggsave("outputs/figures/Percent agreement_excl_R3.png", p_perc, path = ".",
       width = 10, height = PERC_HEIGHT_IN, units = "in", dpi = 600, bg = "white")

cat("Saved: outputs/figures/Krippendorff's alpha_excl_R3.png and outputs/figures/Percent agreement_excl_R3.png\n")

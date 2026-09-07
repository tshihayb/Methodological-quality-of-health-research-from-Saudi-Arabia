#######################################################################################
# programmer:   Talal Alshihayb
# Date:         October 14, 2025
# Purpose:      Calibration results of Assessment of Healthcare Research in Saudi
# Last updated: October 14, 2025 
#######################################################################################


###################################################
###################################################
# Section 1: Preparation before reading the dataset
###################################################
###################################################
{
  # 1.1   Cleaning global environment (remove any previously saved objects in environment)
  rm(list = ls())
  
  # 1.2   Setting the working space so objects can be saved in it without referring to it
  # again in saving functions
  # you can change the path below to a location you prefer
  # Try / or \\ or \ if you are using Mac
  setwd("C:/Users/[USER]/OneDrive/Consulting company project with Yasser/Saudi Arabia Healthcare Research Landscape/RDIA Saudi Emerging Investigator grant")
  
  # 1.3   Checking the working space location
  getwd()
  
  # 1.4   Installing the needed packages
  #required_packages <- c("tidyverse", "janitor", "haven", "labelled", "epitools",
  #"viridis", "lmtest", "performance", "ggfortify", "patchwork",
  #"see", "ggdag", "gtsummary", "rstatix", "skimr",
  #"flextable", "readxl", "stringr", "scales", "RColorBrewer",
  
  # Need for interrupted time series analysis
  #"foreign", "tsModel", "Epi", "splines", "vcd", "tseries", "forecast")
  
  # Install missing packages
  #new_packages <- required_packages[!(required_packages %in% installed.packages()
  #[, "Package"])]
  #if (length(new_packages)) install.packages(new_packages)
  
  # 1.5   Loading packages that we will use
  #lapply(required_packages, library, character.only = TRUE)
  
  # Load needed packages only
  library(tidyverse)
  library(readxl)
  library(janitor)
  library(labelled)
}

###########################################
###########################################
# Section 2: Reading in data from each team
###########################################
###########################################

  # --- Load packages ---
  library(RColorBrewer)
  library(ggnewscale)

  # --- Read and clean ---
  calib <- read_excel("data/calibration/Calibration and agreement_round_2_new_rev5.xlsx",
                      sheet = "Krippendorff's alpha") %>%
    clean_names()
  
  # --- Keep only Krippendorff's alpha ---
  calib <- calib %>%
    filter(agreement_statistic == "Krippendorff's alpha")
  
  # --- Ensure numeric columns ---
  needed <- c("round_1", "round_2", "change")
  stopifnot(all(needed %in% names(calib)))
  calib <- calib %>% mutate(across(all_of(needed), as.numeric))
  
  # --- Detect variable name column ---
  non_num_cols <- names(calib)[!map_lgl(calib, is.numeric)]
  var_col <- setdiff(non_num_cols, c(needed, "agreement_statistics"))[1]
  
  # --- Reshape for plotting ---
  calib_long <- calib %>%
    mutate(var_id = if (!is.na(var_col)) .data[[var_col]] else paste0("Var_", row_number())) %>%
    select(var_id, all_of(needed)) %>%
    pivot_longer(
      cols = all_of(needed),
      names_to = "Round",
      values_to = "Value"
    ) %>%
    mutate(
      Round = recode(Round,
                     round_1 = "1st",
                     round_2 = "2nd",
                     change  = "Change"),
      var_id = fct_rev(factor(var_id, levels = unique(var_id)))  # ✅ keep original dataset order (top→bottom)
    )
  
  # --- Add blank spacer column between rounds and change ---
  round_levels <- c("1st", "2nd", "", "Change")
  
  # --- Split for dual color scales ---
  df12 <- calib_long %>% filter(Round %in% c("1st", "2nd"))
  dfch <- calib_long %>% filter(Round == "Change")
  
  # Shared limits for Round 1 & 2
  lim12 <- range(df12$Value, na.rm = TRUE)
  # Symmetric limits for Change
  limch <- max(abs(dfch$Value), na.rm = TRUE)
  
  # --- Plot ---
  ggplot() +
    # Round 1 & 2
    geom_tile(data = df12,
              aes(x = factor(Round, levels = round_levels),
                  y = var_id, fill = Value),
              color = "white", linewidth = 0.5) +
    geom_text(data = df12,
              aes(x = factor(Round, levels = round_levels),
                  y = var_id, label = round(Value, 2)),
              size = 3.7, color = "black") +
    scale_x_discrete(limits = round_levels, drop = FALSE) +
    scale_fill_distiller(palette = "RdYlBu", direction = 1, name = "Calibration\nrounds", limits = c(-1,1)) +
    
    # New color scale
    ggnewscale::new_scale_fill() +
    
    # Change
    geom_tile(data = dfch,
              aes(x = factor(Round, levels = round_levels),
                  y = var_id, fill = Value),
              color = "white", linewidth = 0.5) +
    geom_text(data = dfch,
              aes(x = factor(Round, levels = round_levels),
                  y = var_id, label = round(Value, 2)),
              size = 3.7, color = "black") +
    scale_fill_distiller(palette = "RdYlBu", direction = 1,
                         name = "Change", limits = c(-0.5, 0.5)) +
    
    # Labels & theme
    labs(title = "Average Krippendorff's Alpha between reviewers and the two adjudicators",
         x = NULL, y = NULL) +
    theme_minimal(base_size = 12) +
    theme(panel.grid = element_blank(),
          axis.text.y = element_text(size = 12),
          axis.text.x = element_text(size=14, face = "bold"),
          plot.title = element_text(size=15, hjust = 0.8, face = "bold"),
          # --- Legend formatting ---
          legend.title = element_text(size = 14, face = "bold"),  # Title size + bold
          legend.text  = element_text(size = 12),                 # Text size
          legend.key.height = unit(1, "cm"),                    # Height of legend boxes
          legend.key.width  = unit(1, "cm")                     # Width of legend boxes
    )
  
    
  # --- Save high-quality image ---
  ggsave(
    filename = "Krippendorff's alpha.png",  # output name
    plot = last_plot(),                            # saves your most recent ggplot
    path = ".",                                    # current working directory
    width = 8, height = 10,                        # dimensions in inches
    units = "in",                                  
    dpi = 600,                                     # high resolution (600 dpi)
    bg = "white"                                  # ensure white background
  )


  
  
  # --- Packages ---
  library(readxl)
  library(dplyr)
  library(tidyr)
  library(forcats)
  library(purrr)
  library(stringr)
  library(ggplot2)
  library(ggnewscale)
  library(janitor)
  library(grid) # for unit()
  
  # --- Read and clean ---
  calib <- read_excel("data/calibration/Calibration and agreement_round_2_new_rev5.xlsx",
                      sheet = "Krippendorff's alpha") %>%
    janitor::clean_names()
  
  # --- Keep only Krippendorff's alpha ---
  calib <- calib %>%
    filter(agreement_statistic == "Krippendorff's alpha")
  
  # --- Ensure numeric columns ---
  needed <- c("round_1", "round_2", "change")
  stopifnot(all(needed %in% names(calib)))
  calib <- calib %>% mutate(across(all_of(needed), as.numeric))
  
  # --- Detect variable name column ---
  non_num_cols <- names(calib)[!purrr::map_lgl(calib, is.numeric)]
  var_col <- setdiff(non_num_cols, c(needed, "agreement_statistic"))[1]
  
  # --- Wrap long labels to TWO lines ---
  wrap_two_lines <- function(x, width = 35) {
    vapply(x, function(s) {
      s <- as.character(s)
      if (nchar(s) <= width) return(s)
      words <- strsplit(s, "\\s+")[[1]]
      cum <- cumsum(nchar(words) + 1)
      mid <- max(cum) / 2
      brk <- which.min(abs(cum - mid))
      paste0(paste(words[1:brk], collapse = " "),
             "\n",
             paste(words[(brk + 1):length(words)], collapse = " "))
    }, character(1))
  }
  
  # --- Long -> tidy for plotting ---
  calib_long <- calib %>%
    mutate(
      var_id_raw  = if (!is.na(var_col)) .data[[var_col]] else paste0("Var_", row_number()),
      var_id_wrap = wrap_two_lines(var_id_raw, width = 35)
    ) %>%
    select(var_id_raw, var_id_wrap, all_of(needed)) %>%
    pivot_longer(cols = all_of(needed), names_to = "Round", values_to = "Value") %>%
    mutate(
      Round = recode(Round, round_1 = "1st", round_2 = "2nd", change = "Change"),
      var_id = forcats::fct_rev(factor(
        var_id_wrap,
        levels = unique(var_id_wrap[match(unique(var_id_raw), var_id_raw)])
      ))
    )
  
  # --- X levels (no blank spacer) ---
  round_levels <- c("1st", "2nd", "Change")
  
  # --- Split ---
  df12 <- calib_long %>% filter(Round %in% c("1st", "2nd"))
  dfch <- calib_long %>% filter(Round == "Change")
  
  # --- Change bins: center inclusive [-0.1, 0.1], others (a, b] ---
  bucket_change <- function(v) {
    dplyr::case_when(
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
  }
  
  labels_all <- c("(0.4, 0.5]",
                  "(0.3, 0.4]",
                  "(0.2, 0.3]",
                  "(0.1, 0.2]",
                  "[-0.1, 0.1]",
                  "(-0.2, -0.1]",
                  "(-0.3, -0.2]",
                  "(-0.4, -0.3]",
                  "(-0.5, -0.4]")
  
  dfch <- dfch %>%
    mutate(ChangeCat = factor(bucket_change(Value), levels = labels_all))
  
  # --- Dummy layer to force ALL legend entries ---
  legend_df <- data.frame(
    ChangeCat = factor(labels_all, levels = labels_all),
    x = 1, y = 1
  )
  
  # --- Controls ---
  tile_width <- 0.6
  ny <- nlevels(calib_long$var_id)
  
  # --- Plot ---
  p <- ggplot() +
    # 1st & 2nd (continuous)
    geom_tile(data = df12,
              aes(x = factor(Round, levels = round_levels),
                  y = var_id, fill = Value),
              color = "white", linewidth = 0.7, width = tile_width) +
    geom_text(data = df12,
              aes(x = factor(Round, levels = round_levels),
                  y = var_id, label = round(Value, 2)),
              size = 3.7, color = "black") +
    scale_x_discrete(limits = round_levels,
                     drop = FALSE,
                     expand = expansion(mult = c(0.01, 0.01))) +
    scale_fill_distiller(palette = "RdBu", direction = 1,
                         name = "Calibration\nrounds", limits = c(-1, 1)) +
    
    ggnewscale::new_scale_fill() +
    
    # Change tiles (DISCRETE) — positives BLUE, negatives RED
    geom_tile(data = dfch,
              aes(x = factor(Round, levels = round_levels),
                  y = var_id, fill = ChangeCat),
              color = "white", linewidth = 0.7, width = tile_width) +
    geom_text(data = dfch,
              aes(x = factor(Round, levels = round_levels),
                  y = var_id, label = round(Value, 2)),
              size = 3.7, color = "black") +
    # invisible tiles carrying all levels -> forces full legend
    geom_tile(data = legend_df,
              aes(x = x, y = y, fill = ChangeCat),
              alpha = 0, inherit.aes = FALSE, show.legend = TRUE) +
    scale_fill_brewer(
      palette = "RdBu", direction = -1,   # flip: blue=positive, red=negative
      name    = "Change (Δ)\n(0.1 bins; center inclusive)",
      limits  = labels_all,
      breaks  = labels_all,
      drop    = FALSE,
      na.translate = FALSE,
      guide = guide_legend(override.aes = list(alpha = 1))
    ) +
    
    # Thin separator between 2nd and Change (x = 2.5)
    annotate("segment",
             x = 2.5, xend = 2.5,
             y = 0.5, yend = ny + 0.5,
             linewidth = 0.6, colour = "grey70") +
    
    labs(title = "Average Krippendorff's Alpha between each reviewer and the two adjudicators",
         x = NULL, y = NULL) +
    theme_minimal(base_size = 12) +
    theme(panel.grid = element_blank(),
          axis.text.y = element_text(size = 12),
          axis.text.x = element_text(size = 14, face = "bold"),
          plot.title  = element_text(size = 15, hjust = 0.7, face = "bold"),
          legend.title = element_text(size = 14, face = "bold"),
          legend.text  = element_text(size = 12),
          legend.key.height = unit(1, "cm"),
          legend.key.width  = unit(1, "cm"))
  
  print(p)
  
  # --- Save ---
  ggsave(
    filename = "Krippendorff's alpha.png",
    plot = p,
    path = ".",
    width = 10, height = 10, units = "in",
    dpi = 600, bg = "white"
  )
  
  
  
  
  
  
  
  
  
  
  
  
  
  ###################################################################
  
  
  
  
  
  # --- Read and clean ---
  calib2 <- read_excel("data/calibration/Calibration and agreement_round_2_new_rev5.xlsx",
                      sheet = "Percent agreement") %>%
    clean_names()
  
  # --- Keep only Krippendorff's alpha ---
  calib2 <- calib2 %>%
    filter(agreement_statistic == "Percent agreement")
  
  # --- Ensure numeric columns ---
  needed <- c("round_1", "round_2", "change")
  stopifnot(all(needed %in% names(calib)))
  calib2 <- calib2 %>% mutate(across(all_of(needed), as.numeric))
  
  # --- Detect variable name column ---
  non_num_cols <- names(calib)[!map_lgl(calib, is.numeric)]
  var_col <- setdiff(non_num_cols, c(needed, "agreement_statistics"))[1]
  
  # --- Reshape for plotting ---
  calib2_long <- calib2 %>%
    mutate(var_id = if (!is.na(var_col)) .data[[var_col]] else paste0("Var_", row_number())) %>%
    select(var_id, all_of(needed)) %>%
    pivot_longer(
      cols = all_of(needed),
      names_to = "Round",
      values_to = "Value"
    ) %>%
    mutate(
      Round = recode(Round,
                     round_1 = "1st",
                     round_2 = "2nd",
                     change  = "Change"),
      var_id = fct_rev(factor(var_id, levels = unique(var_id)))  # ✅ keep original dataset order (top→bottom)
    )
  
  # --- Add blank spacer column between rounds and change ---
  round_levels <- c("1st", "2nd", "", "Change")
  
  # --- Split for dual color scales ---
  df12 <- calib2_long %>% filter(Round %in% c("1st", "2nd"))
  dfch <- calib2_long %>% filter(Round == "Change")
  
  # Shared limits for Round 1 & 2
  lim12 <- range(df12$Value, na.rm = TRUE)
  # Symmetric limits for Change
  limch <- max(abs(dfch$Value), na.rm = TRUE)
  
  # --- Plot ---
  ggplot() +
    # Round 1 & 2
    geom_tile(data = df12,
              aes(x = factor(Round, levels = round_levels),
                  y = var_id, fill = Value),
              color = "white", linewidth = 0.5) +
    geom_text(data = df12,
              aes(x = factor(Round, levels = round_levels),
                  y = var_id, label = round(Value, 2)),
              size = 3.7, color = "black") +
    scale_x_discrete(limits = round_levels, drop = FALSE) +
    scale_fill_distiller(palette = "RdYlBu", direction = 1, name = "Calibration\nrounds", limits = c(0,1)) +
    
    # New color scale
    ggnewscale::new_scale_fill() +
    
    # Change
    geom_tile(data = dfch,
              aes(x = factor(Round, levels = round_levels),
                  y = var_id, fill = Value),
              color = "white", linewidth = 0.5) +
    geom_text(data = dfch,
              aes(x = factor(Round, levels = round_levels),
                  y = var_id, label = round(Value, 2)),
              size = 3.7, color = "black") +
    scale_fill_distiller(palette = "RdYlBu", direction = 1,
                         name = "Change", limits = c(-0.5, 0.5)) +
    
    # Labels & theme
    labs(title = "Average percent agreement between reviewers and the two adjudicators",
         x = NULL, y = NULL) +
    theme_minimal(base_size = 12) +
    theme(panel.grid = element_blank(),
          axis.text.y = element_text(size = 12),
          axis.text.x = element_text(size=14, face = "bold"),
          plot.title = element_text(size=15, hjust = 0.8, face = "bold"),
          # --- Legend formatting ---
          legend.title = element_text(size = 14, face = "bold"),  # Title size + bold
          legend.text  = element_text(size = 12),                 # Text size
          legend.key.height = unit(1, "cm"),                    # Height of legend boxes
          legend.key.width  = unit(1, "cm")                     # Width of legend boxes
    )
  
  
  # --- Save high-quality image ---
  ggsave(
    filename = "Percent agreement.png",  # output name
    plot = last_plot(),                            # saves your most recent ggplot
    path = ".",                                    # current working directory
    width = 8, height = 10,                        # dimensions in inches
    units = "in",                                  
    dpi = 600,                                     # high resolution (600 dpi)
    bg = "white"                                  # ensure white background
  )
  
  
  
  
  
  
  
  
  # --- Packages ---
  library(readxl)
  library(dplyr)
  library(tidyr)
  library(forcats)
  library(purrr)
  library(stringr)
  library(ggplot2)
  library(ggnewscale)
  library(janitor)
  library(grid) # for unit()
  
{
  # --- Read and clean ---
  calib2 <- read_excel("data/calibration/Calibration and agreement_round_2_new_rev5.xlsx",
                       sheet = "Percent agreement") %>%
    clean_names()
  
  # --- Column holding the statistic name (robust) ---
  stat_col2 <- if ("agreement_statistic" %in% names(calib2)) {
    "agreement_statistic"
  } else if ("agreement_statistics" %in% names(calib2)) {
    "agreement_statistics"
  } else {
    stop("Could not find 'agreement_statistic' or 'agreement_statistics' in calib2.")
  }
  
  # --- Keep only Percent agreement ---
  calib2 <- calib2 %>%
    filter(.data[[stat_col2]] == "Percent agreement")
  
  # --- Ensure numeric columns ---
  needed <- c("round_1", "round_2", "change")
  stopifnot(all(needed %in% names(calib2)))
  calib2 <- calib2 %>% mutate(across(all_of(needed), as.numeric))
  
  # --- Detect variable name column (anything non-numeric except needed/stat) ---
  non_num_cols2 <- names(calib2)[!map_lgl(calib2, is.numeric)]
  var_col2 <- setdiff(non_num_cols2, c(needed, stat_col2))[1]
  
  # --- Helper: wrap to TWO lines when too long ---
  wrap_two_lines <- function(x, width = 35) {
    vapply(x, function(s) {
      s <- as.character(s)
      if (nchar(s) <= width) return(s)
      words <- strsplit(s, "\\s+")[[1]]
      cum <- cumsum(nchar(words) + 1)
      mid <- max(cum) / 2
      brk <- which.min(abs(cum - mid))
      paste0(paste(words[1:brk], collapse = " "),
             "\n",
             paste(words[(brk + 1):length(words)], collapse = " "))
    }, character(1))
  }
  
  # --- Long -> tidy for plotting ---
  calib2_long <- calib2 %>%
    mutate(
      var_id_raw  = if (!is.na(var_col2)) .data[[var_col2]] else paste0("Var_", row_number()),
      var_id_wrap = wrap_two_lines(var_id_raw, width = 35)
    ) %>%
    select(var_id_raw, var_id_wrap, all_of(needed)) %>%
    pivot_longer(
      cols = all_of(needed),
      names_to = "Round",
      values_to = "Value"
    ) %>%
    mutate(
      Round = recode(Round, round_1 = "1st", round_2 = "2nd", change = "Change"),
      var_id = forcats::fct_rev(factor(
        var_id_wrap,
        levels = unique(var_id_wrap[match(unique(var_id_raw), var_id_raw)])
      ))
    )
  
  # --- X levels (no blank spacer) ---
  round_levels <- c("1st", "2nd", "Change")
  
  # --- Split ---
  df12 <- calib2_long %>% filter(Round %in% c("1st", "2nd"))
  dfch <- calib2_long %>% filter(Round == "Change")
  
  # --- Change bins: center inclusive [-0.1, 0.1], others (a, b] ---
  bucket_change <- function(v) {
    dplyr::case_when(
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
  }
  
  labels_all <- c("(0.4, 0.5]",
                  "(0.3, 0.4]",
                  "(0.2, 0.3]",
                  "(0.1, 0.2]",
                  "[-0.1, 0.1]",
                  "(-0.2, -0.1]",
                  "(-0.3, -0.2]",
                  "(-0.4, -0.3]",
                  "(-0.5, -0.4]")
  
  dfch <- dfch %>%
    mutate(ChangeCat = factor(bucket_change(Value), levels = labels_all))
  
  # --- Dummy layer to force ALL legend entries (with x/y) ---
  legend_df <- data.frame(
    ChangeCat = factor(labels_all, levels = labels_all),
    x = 1, y = 1
  )
  
  # --- Controls ---
  tile_width <- 0.6
  ny <- nlevels(calib2_long$var_id)
  
  # --- Plot ---
  p <- ggplot() +
    # 1st & 2nd (continuous; Percent agreement in [0,1])
    geom_tile(data = df12,
              aes(x = factor(Round, levels = round_levels),
                  y = var_id, fill = Value),
              color = "white", linewidth = 0.7, width = tile_width) +
    geom_text(data = df12,
              aes(x = factor(Round, levels = round_levels),
                  y = var_id, label = round(Value, 2)),
              size = 3.7, color = "black") +
    scale_x_discrete(limits = round_levels,
                     drop = FALSE,
                     expand = expansion(mult = c(0.01, 0.01))) +
    scale_fill_distiller(palette = "RdBu", direction = 1,
                         name = "Calibration\nrounds", limits = c(0, 1)) +
    
    ggnewscale::new_scale_fill() +
    
    # Change tiles (DISCRETE) — positives BLUE, negatives RED
    geom_tile(data = dfch,
              aes(x = factor(Round, levels = round_levels),
                  y = var_id, fill = ChangeCat),
              color = "white", linewidth = 0.7, width = tile_width) +
    geom_text(data = dfch,
              aes(x = factor(Round, levels = round_levels),
                  y = var_id, label = round(Value, 2)),
              size = 3.7, color = "black") +
    # invisible tiles carrying all levels -> forces full legend
    geom_tile(data = legend_df,
              aes(x = x, y = y, fill = ChangeCat),
              alpha = 0, inherit.aes = FALSE, show.legend = TRUE) +
    scale_fill_brewer(
      palette = "RdBu", direction = -1,   # flip: blue=positive, red=negative
      name    = "Change (Δ)\n(0.1 bins; center inclusive)",
      limits  = labels_all,
      breaks  = labels_all,
      drop    = FALSE,
      na.translate = FALSE,
      guide = guide_legend(override.aes = list(alpha = 1))
    ) +
    
    # Thin separator between 2nd and Change (x = 2.5)
    annotate("segment",
             x = 2.5, xend = 2.5,
             y = 0.5, yend = ny + 0.5,
             linewidth = 0.6, colour = "grey70") +
    
    # Labels & theme
    labs(title = "Average percent agreement between each reviewer and the two adjudicators",
         x = NULL, y = NULL) +
    theme_minimal(base_size = 12) +
    theme(panel.grid = element_blank(),
          axis.text.y = element_text(size = 12),
          axis.text.x = element_text(size = 14, face = "bold"),
          plot.title  = element_text(size = 15, hjust = 0.5, face = "bold"),
          legend.title = element_text(size = 14, face = "bold"),
          legend.text  = element_text(size = 12),
          legend.key.height = unit(1, "cm"),
          legend.key.width  = unit(1, "cm"))
  
  print(p)
  
  # --- Save high-quality image ---
  ggsave(
    filename = "Percent agreement.png",
    plot = p,
    path = ".",
    width = 10, height = 10, units = "in",
    dpi = 600, bg = "white"
  )
  }
  
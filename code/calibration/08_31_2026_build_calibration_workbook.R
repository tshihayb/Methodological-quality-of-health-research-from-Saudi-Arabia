###############################################################################
##  GENERATE the calibration summary workbook instead of typing it
##
##  This is the last hand step in the calibration stage. Both errors corrected on
##  2026-08-31 were hand-entry, and the three residual round-1 cells are
##  hand-rounding. Computing the sheet and writing it makes all four impossible,
##  and guarantees Figure 2 (which reads the summary) and Supplementary Figures
##  S6 to S9 (which recompute from the merged data) can never disagree again.
##
##  INPUT   the merged rater-by-item files, which R now reproduces exactly
##          (R_replace_sas_merge.R: 0 differing cells in both rounds)
##  OUTPUT  codes audit/output/r_generated_workbook/<name>.xlsx
##          plus a cell-by-cell diff against the corrected published workbook
##
##  The published sheet supplies only the ROW ORDER and LABELS; every number is
##  computed here.
###############################################################################
suppressPackageStartupMessages({ library(readxl); library(writexl); library(irr); library(jsonlite) })

PROJ <- getwd()
OUT  <- file.path(PROJ, "codes audit", "output", "r_generated_workbook")
dir.create(OUT, showWarnings = FALSE, recursive = TRUE)

## label -> item stem, and which items each round reports as percent agreement
MAP1 <- c("Task"="task","Design"="design","Population"="pop","Sampling"="sampling",
 "Sample size calc done"="sample_size","Accounting for other issues in calc"="acc_sampl",
 "Sample size achieved"="sample_ach","Accounted for baseline selection bias"="base_sel",
 "Outcome type"="outcome_type","Outcome validity"="val_outcome",
 "Accounted for outcome measure bias"="out_bias_acc","Missing outcome"="miss_outcome",
 "Method for handling missing outcome"="hand_miss_outcom","Complete case analysis"="comp_case",
 "Mentioning errors in discussion"="err_disc","Conflating task"="confl_task",
 "Baseline selection bias from investigator"="inv_sel_base",
 "Compared exp and out distributions"="comp_dis","Loss to follow up bias*"="ltfu_bias",
 "Accounting for loss to follow up bias*"="ltfu_acc","Exposure type"="exposure_type",
 "Exposure validity*"="val_exposure",
 "Exposure measurement diff with respect to outcome"="diff_or_nondiff_exp",
 "Accounted for exposure measure bias"="exp_bias_acc",
 "Outcome measurement diff with respect to exposure"="diff_or_nondiff_out",
 "Dependent or independent measurement bias"="dep_or_indep_misc",
 "Any confounding variables"="conf_var","Determining confounding variables*"="conf_var_det",
 "Method of handling baseline confounding"="base_conf_meth","Baseline confounding"="base_conf",
 "Method of handling time varying confounding"="tv_conf_meth",
 "Time varying confounding"="tv_conf","Missing exposure"="miss_exposure",
 "Method for handling missing exposure"="hand_miss_exposure",
 "Missing confounding variables"="miss_cov",
 "Method of handling missing confounding variables"="hand_miss_cov")

PCT1 <- c("out_bias_acc","exposure_type","diff_or_nondiff_exp","exp_bias_acc","conf_var",
          "conf_var_det","base_conf_meth","base_conf","tv_conf_meth","tv_conf",
          "miss_cov","hand_miss_cov")

## the merged file prefixes each stem with its task arm; try both, coalescing
getrow <- function(mg, stem, suffix) {
  for (p in c("", "descriptive_", "predictive_", "causal_")) {
    cl <- paste0(p, stem, suffix)
    if (cl %in% names(mg)) return(as.character(mg[[cl]]))
  }
  NULL
}
coalesce_arms <- function(mg, stem, suffix) {
  v <- NULL
  for (p in c("", "descriptive_", "predictive_", "causal_")) {
    cl <- paste0(p, stem, suffix)
    if (!cl %in% names(mg)) next
    x <- as.character(mg[[cl]]); x[trimws(x) == ""] <- NA
    v <- if (is.null(v)) x else ifelse(is.na(v), x, v)
  }
  v
}

## ⚠ The recode is not cosmetic. It harmonises label variants that alpha would otherwise
## treat as separate categories, including a real data typo ("Not reported or unknwon"
## beside the correct spelling) and two wordings of Cohort. Omitting it drops agreement
## from 99% to 85%. Keyed on the spec's `var` field, because the CSVs and the spec use
## different names for the same item (sampling.csv comes from `data samp;`).
SPEC <- jsonlite::fromJSON(file.path(PROJ, "codes audit", "output",
                                     "sas_round1_recode_spec.json"),
                           simplifyVector = FALSE)$items
recode_of <- function(stem) {
  k <- names(SPEC)[vapply(SPEC, function(s) identical(s$var, stem), logical(1))]
  if (length(k)) SPEC[[k[1]]]$recode else SPEC[[stem]]$recode
}
apply_recode <- function(v, rc) {
  if (is.null(rc) || !length(rc) || is.null(v)) return(v)
  ifelse(is.na(v), NA, ifelse(v %in% names(rc), unlist(rc)[match(v, names(rc))], v))
}

agree <- function(a, b, metric) {
  k <- !is.na(a) & !is.na(b)
  if (sum(k) < 2) return(NA_real_)
  if (metric == "percent") return(mean(a[k] == b[k]))
  v <- suppressWarnings(tryCatch(kripp.alpha(rbind(a[k], b[k]), method = "nominal")$value,
                                 error = function(e) NA_real_))
  if (is.nan(v)) NA_real_ else v
}


## ---------------------------------------------------------------------------
## Round 2 uses ITS OWN metric split, read from that workbook's own sheets: eleven
## percent items, and notably "Task" and "Outcome type" are PERCENT here where they
## are ALPHA in round 1. It needs no recode: round 2 ran on a single form version,
## so no label variants arise, which is why the raw-text port already matched exactly.
## ---------------------------------------------------------------------------
PCT2 <- c("task","outcome_type","out_bias_acc","exposure_type","diff_or_nondiff_exp",
          "exp_bias_acc","base_conf_meth","base_conf","tv_conf_meth","tv_conf","conf_var_det")

generate <- function(merged_name, pub_path, pub_sheet, pct, use_recode, out_name, label) {
  mg <- as.data.frame(read_excel(
          file.path(PROJ, "codes audit", "output", "r_replace_sas_merge", merged_name),
          col_types = "text", .name_repair = "minimal"), check.names = FALSE)
  pub <- as.data.frame(read_excel(pub_path, sheet = pub_sheet))
  names(pub)[1] <- "item"
  labs <- trimws(as.character(pub$item))
  labs <- labs[!is.na(labs) & labs != "NA" & labs != "" & labs %in% names(MAP1)]

  res <- matrix(NA_real_, length(labs), 14, dimnames = list(labs, paste0("R", 1:14)))
  for (lab in labs) {
    stem <- MAP1[[lab]]
    rc <- if (use_recode) recode_of(stem) else NULL
    a <- apply_recode(coalesce_arms(mg, stem, "_a"), rc)
    if (is.null(a)) next
    metric <- if (stem %in% pct) "percent" else "alpha"
    for (r in 1:14) {
      b <- apply_recode(coalesce_arms(mg, stem, paste0("_r", r)), rc)
      if (!is.null(b)) res[lab, r] <- agree(a, b, metric)
    }
  }
  out <- data.frame(item = labs, round(as.data.frame(res), 4), check.names = FALSE)
  out$Average <- round(rowMeans(res, na.rm = TRUE), 4)
  writexl::write_xlsx(out, file.path(OUT, out_name))

  ok <- tot <- 0; bad <- list()
  for (lab in labs) {
    i <- which(trimws(as.character(pub$item)) == lab)
    if (length(i) != 1) next
    pv <- suppressWarnings(as.numeric(pub[i, 2:15]))
    for (r in 1:14) {
      if (is.na(pv[r]) || is.na(res[lab, r])) next
      tot <- tot + 1
      if (abs(pv[r] - res[lab, r]) <= 0.005 + 1e-9) ok <- ok + 1
      else bad[[length(bad)+1]] <- sprintf("%-46s R%-2d published %6.2f  generated %7.4f",
                                           lab, r, pv[r], res[lab, r])
    }
  }
  cat(sprintf("
%s: %d cells compared | %d agree at 2 dp (%.1f%%)
",
              label, tot, ok, 100*ok/max(tot,1)))
  if (length(bad)) for (b in bad) cat("   ", b, "
")
  invisible(c(tot, ok))
}

CAL <- file.path(PROJ, "data", "calibration")
generate("agreement_new_5.xlsx",
         file.path(CAL, "Calibration and agreement with new reviewer 5.xlsx"), "Sheet1",
         PCT1, TRUE,  "Calibration and agreement GENERATED round 1.xlsx", "ROUND 1")
generate("agreement_round_2.xlsx",
         file.path(CAL, "Calibration and agreement_round_2_new_rev5.xlsx"), "Round 2",
         PCT2, FALSE, "Calibration and agreement GENERATED round 2.xlsx", "ROUND 2")

cat(sprintf("
wrote %s
", file.path("codes audit", "output", "r_generated_workbook")))

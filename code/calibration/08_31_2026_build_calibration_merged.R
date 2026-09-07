# NOTE (public repository): 2 hard-coded study identifier(s) were
# rewritten to de-identified surrogates by tools/build_public_repo.py.
# They are rulings about particular studies rather than values the data
# can supply, so they have to travel with it.
###############################################################################
##  BUILD THE CALIBRATION MERGED FILES  (replaces the SAS step, 2026-08-31)
##
##  Produces the wide rater-by-item files that SAS used to emit and that
##  Supplementary Figures S6 to S9 read:
##      agreement_new_5.xlsx     round 1, 10 papers x (PMID + 57 items x 15 raters)
##      agreement_round_2.xlsx   round 2,  3 papers x (PMID + 32 items x 15 raters + comments)
##
##  Together with R_port_calibration_round2.R and R_round1_recoded.R this removes
##  SAS from the calibration stage entirely.
##
##  METHOD.  The SAS renames each task-arm question to a canonical item stem and
##  merges the adjudicator with reviewers r1..r14 by PMID. Rather than replicate
##  SAS's name mangling, the item stems are READ FROM THE EXISTING SAS OUTPUT and
##  filled from the raw exports in column order, then the result is diffed against
##  that output cell by cell. If the alignment were wrong the diff would show it.
##
##  Per-round quirks replicated, each traceable to a line in the SAS:
##    round 1  reviewer 12 submitted an extra row in which they recused; deleted.
##    round 2  reviewer 5 was replaced mid-round; the LAST three rows are kept.
##
##  Adopted into the pipeline on 2026-08-31, replacing
##      data/calibration/round-1/2024_09_25_calibration_agreement_new_rev_5.sas
##      data/calibration/round-2/2024_07_13_calibration_agreement_round_2.sas
##  which required a SAS licence and, for round 1, did not run to completion.
##  The SAS-produced files it supersedes are archived with checksums in
##      archive/calibration-pre-R-swap-2026-08-31/
##  Verified byte-equivalent in content to those files: 0 differing cells of 8,560
##  (round 1) and 0 of 1,443 (round 2).
##
##  Run from the repository root:
##    Rscript code/calibration/08_31_2026_build_calibration_merged.R
###############################################################################
suppressPackageStartupMessages({ library(readxl); library(writexl) })

PROJ <- getwd()
## write the canonical merged files in place; the previous SAS-produced versions are
## archived under archive/calibration-pre-R-swap-2026-08-31/
OUTDIR <- function(sas_path) dirname(sas_path)

build <- function(adj_path, rev_path, sas_path, label, dedup) {
  adj <- as.data.frame(read_excel(adj_path, col_types = "text", .name_repair = "minimal"),
                       check.names = FALSE)
  rev <- as.data.frame(read_excel(rev_path, col_types = "text", .name_repair = "minimal"),
                       check.names = FALSE)
  rev <- dedup(rev)

  sas <- as.data.frame(read_excel(sas_path, col_types = "text", .name_repair = "minimal"),
                       check.names = FALSE)
  stems <- sub("_a$", "", grep("_a$", names(sas), value = TRUE))

  ## ⚠ Index by POSITION, never by name. `.name_repair = "minimal"` preserves the duplicate
  ## headers that the task arms create, so df[["What was the study design?"]] silently returns
  ## the first of three. A name-based version of this produced 22 questions where there are 32
  ## and disagreed with SAS on 80% of cells.
  adj_i <- seq(3, ncol(adj))          # adjudicator: [Reviewer ID, PMID, Q...]
  rev_i <- seq(4, ncol(rev))          # reviewers  : [Timestamp, Reviewer ID, PMID, Q...]

  ## ⚠ The two exports do NOT carry the questions in the same order. In round 1 the
  ## adjudicator file has "Was the sample size needed achieved?" before "Did the authors
  ## account for ineligibility...", and the reviewer file has them the other way round.
  ## Pairing the files by position therefore swapped acc_sampl with sample_ach in both task
  ## arms, which was 81 of the 8,560 cells. Pair them by question text instead, counting
  ## repeats so each task arm's copy of a question matches its own counterpart.
  keyof <- function(nm) {
    k <- trimws(sub("\\.\\.\\.\\d+$", "", nm))
    ave(k, k, FUN = function(x) paste0(x, "#", seq_along(x)))
  }
  adj_key <- keyof(names(adj)[adj_i])
  rev_key <- keyof(names(rev)[rev_i])
  m <- match(adj_key, rev_key)
  ok <- !is.na(m)
  if (any(!ok))
    cat(sprintf("  !! %s: %d adjudicator questions have no reviewer counterpart\n",
                label, sum(!ok)))
  adj_i <- adj_i[ok]; rev_i <- rev_i[m[ok]]
  keep <- vapply(seq_along(adj_i), function(k)
    any(!is.na(adj[[adj_i[k]]])) || any(!is.na(rev[[rev_i[k]]])), logical(1))
  adj_i <- adj_i[keep]; rev_i <- rev_i[keep]
  if (length(adj_i) != length(stems))
    cat(sprintf("  !! %s: %d non-empty questions but %d SAS stems\n",
                label, length(adj_i), length(stems)))
  n <- min(length(adj_i), length(stems))

  papers <- as.character(sas$PMID)
  out <- data.frame(PMID = papers, stringsAsFactors = FALSE)
  pick <- function(df, pidx, cidx) {
    idx <- match(papers, as.character(df[[pidx]]))
    ifelse(is.na(idx), NA_character_, as.character(df[[cidx]])[idx])
  }
  for (i in seq_len(n)) {
    out[[paste0(stems[i], "_a")]] <- pick(adj, 2, adj_i[i])
    for (r in 1:14) {
      sub <- rev[as.character(rev[[2]]) == as.character(r), ]
      out[[paste0(stems[i], "_r", r)]] <-
        if (nrow(sub)) pick(sub, 3, rev_i[i]) else NA_character_
    }
  }
  ## compare BEFORE overwriting, so the check is against what was there
  prev <- sas

  ## ---- verify against the SAS output, cell by cell ----
  common <- intersect(names(out), names(prev))
  norm <- function(x) { x <- trimws(as.character(x)); x[x == "" | x == "NA"] <- NA; x }
  bad <- 0; tot <- 0
  for (cl in common) {
    a <- norm(out[[cl]]); b <- norm(prev[[cl]])
    tot <- tot + length(a); bad <- bad + sum(xor(is.na(a), is.na(b)) |
                                             (!is.na(a) & !is.na(b) & a != b))
  }
  cat(sprintf("%-9s columns %d/%d shared | cells %d | DIFFER %d (%.2f%%)\n",
              label, length(common), ncol(prev), tot, bad, 100 * bad / max(tot, 1)))
  ## ⚠ The downstream figure scripts open these by SHEET NAME, which SAS PROC EXPORT set
  ## from the dataset name. writexl defaults to "Sheet1", which made every S6 to S9 script
  ## fail with "Sheet not found". Name the sheet after the file, as SAS did.
  sheet <- tools::file_path_sans_ext(basename(sas_path))
  writexl::write_xlsx(setNames(list(out), sheet), sas_path)
  invisible(bad)
}

D1 <- file.path(PROJ, "data", "calibration", "round-1")
D2 <- file.path(PROJ, "data", "calibration", "round-2")

b1 <- build(file.path(D1, "2024_05_04_Adjudication_of_calibration.xlsx"),
            file.path(D1, "2024_09_25_Progress.xlsx"),
            file.path(D1, "agreement_new_5.xlsx"), "ROUND 1",
            dedup = function(d) {
              ## drop reviewer 12's recusal row (SAS :203)
              rc <- grep("recuse", names(d), ignore.case = TRUE)[1]
              drop <- which(as.character(d[[2]]) == "12" &
                            grepl("^Yes, I recuse", as.character(d[[rc]])))
              if (length(drop)) d <- d[-drop, ]
              ## reviewer 8 typed STUDY-0672 twice and never STUDY-0270; SAS repairs the second
              ## by timestamp. Without this the whole of reviewer 8's row for STUDY-0270 is
              ## missing, which was the last 39 differing cells, one per item.
              i <- which(as.character(d[[2]]) == "8" &
                         grepl("^2024/04/29 11:36:20", as.character(d[[1]])))
              if (length(i) == 1) d[i, 3] <- "STUDY-0270"
              d
            })

b2 <- build(file.path(D2, "2024_07_13_Adjudication_of_calibration_round_2.xlsx"),
            file.path(D2, "2024_11_26_Progress_round_2.xlsx"),
            file.path(D2, "agreement_round_2.xlsx"), "ROUND 2",
            dedup = function(d) {                       # reviewer 5 replaced: keep the last 3
              i <- which(as.character(d[[2]]) == "5")
              if (length(i) > 3) d[-i[seq_len(length(i) - 3)], ] else d
            })

cat(sprintf("\n%s\n", if (b1 + b2 == 0)
  "R reproduces both SAS merged files exactly. SAS is not needed for this stage."
  else "differences remain; see above"))

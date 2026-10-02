###############################################################################
##  Fill the eight per-reviewer "Reviewer <n> batch 6.xlsx" worklists with the
##  papers drawn in the batch-6 random assignment.
##  Project: Assessment of Healthcare Research Quality in Saudi Arabia
##  Date   : 2026-07-24
##
##  Reads the assignment produced by code/reviewer-ops/07_23_2026_batch6_random_assignment.R --
##  it does NOT re-draw anything, so this script is safe to re-run.
##
##  Per file:
##    * DROP the `ID` and `seq` columns
##    * REPLACE PMID / title / link / Study_Type / adjudicated_exposure /
##      adjudicated_outcome with that reviewer's newly assigned papers
##    * KEEP `Link to data collection` exactly as it was (the reviewer's own
##      Google-Forms tool link) and `Completed (Yes/No)` blank
##    * KEEP the original sheet name (the reviewer's first name in caps)
##
##  The previous contents are copied to 07_24_2026_batch6_prev_versions/ first.
##  Every paper currently in those files was verified as already submitted by
##  that reviewer, so nothing outstanding is lost.
###############################################################################

suppressPackageStartupMessages({ library(readxl); library(openxlsx) })

PROJ   <- "."
BKDIR  <- file.path(PROJ, "07_24_2026_batch6_prev_versions")
AUDIT  <- file.path(PROJ, "data/provenance/07_23_2026_batch6_assignment_audit.xlsx")
BATCH6 <- file.path(PROJ, "private/reviewers/batch-6-distribution/Batch 6.xlsx")

## Final column layout of each reviewer worklist (ID and seq removed)
OUT_COLS <- c("PMID", "title", "link", "Study_Type", "adjudicated_exposure",
              "adjudicated_outcome", "Link to data collection", "Completed (Yes/No)")

## ---------------------------------------------------------------------------
## 1.  The assignment (one row per review) + the paper metadata
## ---------------------------------------------------------------------------
opr <- as.data.frame(read_excel(AUDIT, sheet = "one_row_per_review"))
opr$PMID <- as.character(opr$PMID)
meta <- as.data.frame(read_excel(BATCH6, col_types = "text"))
stopifnot(nrow(meta) == 8L, nrow(opr) == 11L, all(opr$PMID %in% meta$PMID))
meta$.order <- seq_len(nrow(meta))          # preserve the private/reviewers/batch-6-distribution/Batch 6.xlsx ordering

rev_ids <- sort(unique(opr$Reviewer_No))
cat("[assignment] ", nrow(opr), " reviews across ", length(rev_ids),
    " reviewers: ", paste(rev_ids, collapse = ", "), "\n", sep = "")

## ---------------------------------------------------------------------------
## 2.  Locate the eight worklists and sanity-check them
## ---------------------------------------------------------------------------
paths <- setNames(file.path(PROJ, sprintf("Reviewer %d batch 6.xlsx", rev_ids)), rev_ids)
stopifnot(all(file.exists(paths)))
## a worklist must exist for every reviewer drawn, and no drawn reviewer may be
## missing a file -- if the two sets ever diverge, stop rather than guess
present <- as.integer(sub("^Reviewer ([0-9]+) batch 6\\.xlsx$", "\\1",
                          basename(list.files(PROJ, pattern = "^Reviewer [0-9]+ batch 6\\.xlsx$"))))
stopifnot(setequal(present, rev_ids))

if (!dir.exists(BKDIR)) dir.create(BKDIR)

## ---------------------------------------------------------------------------
## 3.  Rewrite each worklist
## ---------------------------------------------------------------------------
log <- list()
for (r in rev_ids) {
  p     <- paths[[as.character(r)]]
  sheet <- excel_sheets(p)[1]
  old   <- as.data.frame(suppressMessages(read_excel(p, sheet = sheet, col_types = "text")))

  ## the reviewer's own tool link -- carried over untouched
  tool <- unique(na.omit(old[["Link to data collection"]]))
  stopifnot(length(tool) == 1L, grepl("^https?://", tool))

  ## back up the previous version before overwriting
  file.copy(p, file.path(BKDIR, basename(p)), overwrite = TRUE)

  ## this reviewer's newly assigned papers, in private/reviewers/batch-6-distribution/Batch 6.xlsx order
  mine <- meta[meta$PMID %in% opr$PMID[opr$Reviewer_No == r], ]
  mine <- mine[order(mine$.order), ]
  stopifnot(nrow(mine) == sum(opr$Reviewer_No == r), nrow(mine) >= 1L)

  new <- data.frame(
    PMID                      = mine$PMID,
    title                     = mine$title,
    link                      = mine$link,
    Study_Type                = mine$Study_Type,
    adjudicated_exposure      = mine$adjudicated_exposure,
    adjudicated_outcome       = mine$adjudicated_outcome,
    `Link to data collection` = tool,
    `Completed (Yes/No)`      = NA_character_,
    check.names = FALSE, stringsAsFactors = FALSE)
  stopifnot(identical(names(new), OUT_COLS))

  ## rebuild the workbook: dropping columns means the old cell styles no longer
  ## line up, so write a clean sheet rather than leave stale formatting behind
  wb <- createWorkbook()
  addWorksheet(wb, sheet)
  hdr <- createStyle(textDecoration = "bold", valign = "top")
  writeData(wb, sheet, new, headerStyle = hdr)
  ## keep the tool link clickable, exactly as it was in the original files
  writeData(wb, sheet, structure(new$`Link to data collection`, class = "hyperlink"),
            startCol = which(OUT_COLS == "Link to data collection"), startRow = 2,
            colNames = FALSE)
  setColWidths(wb, sheet, cols = seq_along(OUT_COLS),
               widths = c(11, 75, 45, 12, 34, 34, 36, 18))
  addStyle(wb, sheet, createStyle(valign = "top", wrapText = TRUE),
           rows = 2:(nrow(new) + 1), cols = 1:length(OUT_COLS), gridExpand = TRUE)
  freezePane(wb, sheet, firstRow = TRUE)
  saveWorkbook(wb, p, overwrite = TRUE)

  log[[length(log) + 1]] <- data.frame(
    Reviewer_No = r, sheet = sheet, n_old = nrow(old), n_new = nrow(new),
    PMIDs = paste(new$PMID, collapse = "; "),
    tasks = paste(new$Study_Type, collapse = "; "), tool_link = tool)
  cat(sprintf("[written] %-28s sheet=%-7s %d -> %d rows | %s\n",
              basename(p), sheet, nrow(old), nrow(new), paste(new$PMID, collapse = "; ")))
}
log <- do.call(rbind, log)

## ---------------------------------------------------------------------------
## 4.  Verify what landed on disk
## ---------------------------------------------------------------------------
cat("\n--- verification ---\n")
for (r in rev_ids) {
  p <- paths[[as.character(r)]]
  d <- as.data.frame(suppressMessages(read_excel(p, col_types = "text")))
  stopifnot(identical(names(d), OUT_COLS),                       # ID / seq gone
            setequal(d$PMID, opr$PMID[opr$Reviewer_No == r]),    # right papers
            identical(unique(d$`Link to data collection`),
                      log$tool_link[log$Reviewer_No == r]),      # tool link intact
            all(is.na(d$`Completed (Yes/No)`)))
}
cat("all 8 files: ID/seq removed, correct papers, tool link unchanged, Completed blank\n\n")
print(log[, c("Reviewer_No", "sheet", "n_new", "PMIDs", "tasks")], row.names = FALSE)
write.csv(log, file.path(PROJ, "data/provenance/07_24_2026_batch6_reviewer_worklist_log.csv"),
          row.names = FALSE, fileEncoding = "UTF-8")
cat("\n[written]", file.path(PROJ, "data/provenance/07_24_2026_batch6_reviewer_worklist_log.csv"), "\n")
cat("[backups]", BKDIR, "\n")

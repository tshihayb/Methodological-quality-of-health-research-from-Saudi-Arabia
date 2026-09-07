###############################################################################
##  Publish the batch-6 materials to each reviewer's Google Drive folder.
##  Project: Assessment of Healthcare Research Quality in Saudi Arabia
##  Date   : 2026-07-24
##
##  Source : <project>\Batch 6 rev - <n>\            (built locally, PMID-named)
##  Target : G:\My Drive\Reviewer <n> Assessment of Healthcare Research in
##           Saudi Arabia\Batch 6\
##
##  CONVENTION -- matched to the reviewers' existing Batch 1-5 folders, NOT to
##  the local staging layout:
##    * the folder is called "Batch 6" (it already sits under "Reviewer <n> ...",
##      so repeating the reviewer number would be redundant and inconsistent)
##    * PDFs are named by TITLE, truncated -- exactly how batches 1-5 look to the
##      reviewers.  Locally they stay PMID-named; only the Drive copies are
##      renamed, and the mapping is written to a manifest.
##    * the worklist keeps its own name, "Reviewer <n> batch 6.xlsx"
##
##  Titles are truncated so that the FULL destination path stays under the
##  Windows 260-char limit; Drive's own sync client is unforgiving about this.
##
##  Re-runnable.  OVERWRITE=FALSE refuses to clobber an existing file, so a
##  second run reports collisions instead of silently replacing a reviewer's work.
###############################################################################

suppressPackageStartupMessages({ library(readxl); library(openxlsx) })

PROJ      <- "."
DRIVE     <- "G:/My Drive"
DRIVE_FMT <- "Reviewer %d Assessment of Healthcare Research in Saudi Arabia"
BATCH     <- "Batch 6"
MAXPATH   <- 250L      # leave headroom under the 260 hard limit
OVERWRITE <- FALSE     # TRUE only if you intend to replace files already there

## ---------------------------------------------------------------------------
## 1.  What goes where
## ---------------------------------------------------------------------------
opr  <- as.data.frame(read_excel(file.path(PROJ, "data/provenance/07_23_2026_batch6_assignment_audit.xlsx"),
                                 sheet = "one_row_per_review"))
opr$PMID <- as.character(opr$PMID)
meta <- as.data.frame(read_excel(file.path(PROJ, "private/reviewers/batch-6-distribution/Batch 6.xlsx"), col_types = "text"))
rev_ids <- sort(unique(opr$Reviewer_No))
stopifnot(nrow(meta) == 8L, nrow(opr) == 11L, length(rev_ids) == 8L)

## title -> a legal, length-capped Windows filename
safe_name <- function(title, budget) {
  x <- gsub('[\\\\/:*?"<>|]', " ", title)     # characters Windows forbids
  x <- gsub("\\s+", " ", trimws(x))
  x <- sub("\\.$", "", x)                      # no trailing dot
  if (nchar(x) > budget) x <- trimws(substr(x, 1, budget))
  sub("[ .]+$", "", x)
}

## ---------------------------------------------------------------------------
## 2.  Build the manifest first, and validate it, before touching Drive
## ---------------------------------------------------------------------------
man <- list()
for (r in rev_ids) {
  src_dir <- file.path(PROJ, sprintf("Batch 6 rev - %d", r))
  dst_dir <- file.path(DRIVE, sprintf(DRIVE_FMT, r), BATCH)
  stopifnot(dir.exists(src_dir), dir.exists(dirname(dst_dir)))

  wl <- sprintf("Reviewer %d batch 6.xlsx", r)
  man[[length(man) + 1]] <- data.frame(Reviewer_No = r, kind = "worklist", PMID = NA_character_,
    src = file.path(src_dir, wl), dst = file.path(dst_dir, wl))

  for (p in meta$PMID[meta$PMID %in% opr$PMID[opr$Reviewer_No == r]]) {
    src <- file.path(src_dir, paste0(p, ".pdf"))
    stopifnot(file.exists(src))
    ## budget = 260 - (destination folder + backslash + ".pdf")
    budget <- MAXPATH - nchar(dst_dir) - 1L - 4L
    stopifnot(budget >= 40L)
    nm  <- paste0(safe_name(meta$title[meta$PMID == p], budget), ".pdf")
    man[[length(man) + 1]] <- data.frame(Reviewer_No = r, kind = "pdf", PMID = p,
      src = src, dst = file.path(dst_dir, nm))
  }
}
man <- do.call(rbind, man)
man$dst_len   <- nchar(man$dst)
man$exists    <- file.exists(man$dst)
man$src_bytes <- file.size(man$src)

cat("=== manifest:", nrow(man), "files to", length(rev_ids), "reviewers ===\n")
print(data.frame(Rev = man$Reviewer_No, kind = man$kind, PMID = man$PMID,
                 KB = round(man$src_bytes / 1024), path_len = man$dst_len,
                 target = basename(man$dst)), right = FALSE, row.names = FALSE)

stopifnot(all(man$dst_len < 260L), !any(duplicated(man$dst)), all(file.exists(man$src)))
if (any(man$exists) && !OVERWRITE) {
  cat("\n!! these targets already exist and OVERWRITE is FALSE:\n")
  print(man$dst[man$exists]); stop("refusing to overwrite")
}
cat("\n[check] all destination paths < 260 chars, no name collisions, nothing overwritten\n")

## ---------------------------------------------------------------------------
## 3.  Copy
## ---------------------------------------------------------------------------
for (d in unique(dirname(man$dst)))
  if (!dir.exists(d)) { dir.create(d, recursive = TRUE); cat("[mkdir]", d, "\n") }
ok <- file.copy(man$src, man$dst, overwrite = OVERWRITE, copy.date = TRUE)
stopifnot(all(ok))

## ---------------------------------------------------------------------------
## 4.  Verify what landed on Drive
## ---------------------------------------------------------------------------
man$dst_bytes <- file.size(man$dst)
stopifnot(all(file.exists(man$dst)), all(man$dst_bytes == man$src_bytes))
## every PDF must still start with the PDF magic bytes after the copy
pdfs <- man[man$kind == "pdf", ]
stopifnot(all(vapply(pdfs$dst, function(f)
  identical(rawToChar(readBin(f, "raw", 5)), "%PDF-"), logical(1))))

cat("\n=== published ===\n")
for (r in rev_ids) {
  d <- file.path(DRIVE, sprintf(DRIVE_FMT, r), BATCH)
  f <- list.files(d)
  cat(sprintf("\nReviewer %-2d  (%d files)\n", r, length(f)))
  for (x in sort(f)) cat("   ", substr(x, 1, 105), "\n")
}
cat(sprintf("\n%d files copied, all byte-identical to source, all PDFs valid\n", nrow(man)))

write.csv(man[, c("Reviewer_No","kind","PMID","src","dst","src_bytes","dst_bytes")],
          file.path(PROJ, "data/provenance/07_24_2026_batch6_drive_publish_manifest.csv"),
          row.names = FALSE, fileEncoding = "UTF-8")
cat("[written]", file.path(PROJ, "data/provenance/07_24_2026_batch6_drive_publish_manifest.csv"), "\n")

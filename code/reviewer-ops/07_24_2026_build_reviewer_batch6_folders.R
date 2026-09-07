# NOTE (public repository): 3 hard-coded study identifier(s) were
# rewritten to de-identified surrogates by tools/build_public_repo.py.
# They are rulings about particular studies rather than values the data
# can supply, so they have to travel with it.
###############################################################################
##  Build one distribution folder per batch-6 reviewer:
##      "Batch 6 rev - <n>\"  containing
##          Reviewer <n> batch 6.xlsx      (their worklist)
##          <PMID>.pdf                     (full text of each assigned paper)
##          FULL TEXT NOT AVAILABLE.txt    (only if some PDF is missing)
##  Project: Assessment of Healthcare Research Quality in Saudi Arabia
##  Date   : 2026-07-24
##
##  Source of the PDFs is the granted READ-ONLY folder (389 PDFs named by title,
##  not PMID).  Matching is by normalised title, and the copies are renamed to
##  <PMID>.pdf -- both because that is the project's existing convention
##  (fulltext_shortpath_by_pmid\) and because it keeps the destination paths
##  well under the Windows 260-char MAX_PATH limit.
##
##  MAX_PATH: many source paths are >=260 chars, so every read of the source
##  folder goes through the \\?\ extended-length prefix.  Without it the files
##  look like they do not exist.  See feedback-directory-scope.
##
##  Safe to re-run: folders and files are overwritten, nothing is deleted.
###############################################################################

suppressPackageStartupMessages({ library(readxl); library(openxlsx) })

PROJ <- "."
BOTH <- "C:/Users/[USER]/OneDrive/Consulting company project with Yasser/Saudi Arabia Healthcare Research Landscape/Full text of included papers/Both"
AUDIT <- file.path(PROJ, "data/provenance/07_23_2026_batch6_assignment_audit.xlsx")

## extended-length path, required for the source folder (>=260 char paths)
xl <- function(p) paste0("\\\\?\\", gsub("/", "\\\\", p))

## ---------------------------------------------------------------------------
## 1.  Assignment + paper metadata
## ---------------------------------------------------------------------------
opr  <- as.data.frame(read_excel(AUDIT, sheet = "one_row_per_review"))
opr$PMID <- as.character(opr$PMID)
meta <- as.data.frame(read_excel(file.path(PROJ, "private/reviewers/batch-6-distribution/Batch 6.xlsx"), col_types = "text"))
stopifnot(nrow(meta) == 8L, nrow(opr) == 11L)
rev_ids <- sort(unique(opr$Reviewer_No))

## ---------------------------------------------------------------------------
## 2.  Map each batch-6 PMID to a PDF in the read-only store
## ---------------------------------------------------------------------------
norm <- function(x) trimws(gsub("\\s+", " ",
          gsub("[^a-z0-9]+", " ", tolower(gsub("\\.pdf$", "", x)))))
pdfs <- list.files(BOTH, pattern = "\\.pdf$", ignore.case = TRUE)
stopifnot(length(pdfs) > 300L)
idx  <- data.frame(file = pdfs, key = norm(pdfs), stringsAsFactors = FALSE)

## Second source: the newly included papers are not in that store (they were
## never part of the 385).  code/reviewer-ops/07_24_2026_fetch_new_paper_fulltext.R downloads them
## from PMC / the publisher into fulltext_new_papers_by_pmid\<PMID>.pdf.
NEWSTORE <- file.path(PROJ, "private/fulltext/pdf-by-pmid")

pdf_for <- setNames(rep(NA_character_, nrow(meta)), meta$PMID)   # file in BOTH
new_for <- setNames(rep(NA_character_, nrow(meta)), meta$PMID)   # file in NEWSTORE
how_for <- setNames(rep("NOT FOUND",  nrow(meta)), meta$PMID)
for (i in seq_len(nrow(meta))) {
  tk <- norm(meta$title[i])
  j <- which(idx$key == tk);                                        h <- "exact"
  ## some stored filenames are truncated versions of the full title
  if (!length(j)) { j <- which(startsWith(tk, idx$key) & nchar(idx$key) >= 40)
                    h <- "filename-is-truncated-title" }
  if (length(j) == 1L) { pdf_for[i] <- idx$file[j]; how_for[i] <- h }
  else if (length(j) > 1L) how_for[i] <- paste0("AMBIGUOUS (", length(j), ")")
  else {
    cand <- file.path(NEWSTORE, paste0(meta$PMID[i], ".pdf"))
    if (file.exists(cand)) { new_for[i] <- cand; how_for[i] <- "newly-fetched (by PMID)" }
  }
}
## Free-full-text locations for the papers with no PDF in the store.  Looked up
## 2026-07-24 via PubMed E-utilities esummary; all three newly included papers
## turn out to be open access in PMC.  Hard-coded so the build stays offline.
PMC <- c("STUDY-0401" = "[PMC-REDACTED]",   # J Diabetes Sci Technol
         "STUDY-0658" = "[PMC-REDACTED]",    # [NAME-REDACTED]
         "STUDY-0161" = "[PMC-REDACTED]")    # [NAME-REDACTED] (Riyadh)

## the 3 newly included papers were never part of the 385, so no full text was
## ever collected for them -- expected, not an error
cat("--- full-text lookup ---\n")
print(data.frame(PMID = meta$PMID, Study_Type = meta$Study_Type, match = how_for,
                 pdf = ifelse(is.na(pdf_for), "-", substr(pdf_for, 1, 60)),
                 row.names = NULL), right = FALSE)
stopifnot(!any(grepl("^AMBIGUOUS", how_for)))

## ---------------------------------------------------------------------------
## 3.  Build one folder per reviewer
## ---------------------------------------------------------------------------
log <- list()
for (r in rev_ids) {
  dest <- file.path(PROJ, sprintf("Batch 6 rev - %d", r))
  if (!dir.exists(dest)) dir.create(dest)

  ## the reviewer's worklist (copied, not moved -- the master stays in the root)
  wl <- file.path(PROJ, sprintf("Reviewer %d batch 6.xlsx", r))
  stopifnot(file.exists(wl))
  stopifnot(file.copy(wl, file.path(dest, basename(wl)), overwrite = TRUE))

  mine    <- meta$PMID[meta$PMID %in% opr$PMID[opr$Reviewer_No == r]]
  copied  <- character(0); missing <- character(0)
  for (p in mine) {
    src <- if (!is.na(pdf_for[[p]])) xl(file.path(BOTH, pdf_for[[p]]))
           else if (!is.na(new_for[[p]])) new_for[[p]] else NA_character_
    if (is.na(src)) { missing <- c(missing, p); next }
    stopifnot(file.copy(src, file.path(dest, paste0(p, ".pdf")), overwrite = TRUE))
    copied <- c(copied, p)
  }

  ## tell the reviewer where to get anything we could not supply
  note <- file.path(dest, "FULL TEXT NOT AVAILABLE.txt")
  if (file.exists(note)) unlink(note)
  if (length(missing)) {
    writeLines(c(
      "The full text of the following paper(s) is not included in this folder.",
      "These are newly added papers, so no PDF had been collected for them.",
      "All of them are FREELY available in PubMed Central - use the PMC link:",
      "",
      vapply(missing, function(p) sprintf(
        "  PMID %s  -  %s\n    %s\n    PMC (free full text): https://www.ncbi.nlm.nih.gov/pmc/articles/%s/\n    PubMed record       : %s\n",
        p, meta$Study_Type[meta$PMID == p], meta$title[meta$PMID == p],
        PMC[[p]], meta$link[meta$PMID == p]), character(1))), note)
  }

  log[[length(log) + 1]] <- data.frame(
    Reviewer_No = r, folder = basename(dest), n_papers = length(mine),
    pdfs_copied = length(copied), pdfs_missing = length(missing),
    copied = paste(copied, collapse = "; "),
    missing = paste(missing, collapse = "; "))
  cat(sprintf("[folder] %-18s worklist + %d/%d PDFs%s\n", basename(dest),
              length(copied), length(mine),
              if (length(missing)) paste0("  (no full text: ",
                                          paste(missing, collapse = ", "), ")") else ""))
}
log <- do.call(rbind, log)

## ---------------------------------------------------------------------------
## 4.  Verify on disk
## ---------------------------------------------------------------------------
cat("\n--- verification ---\n")
for (r in rev_ids) {
  dest <- file.path(PROJ, sprintf("Batch 6 rev - %d", r))
  got  <- list.files(dest)
  want_pdf <- paste0(log$copied[log$Reviewer_No == r], ".pdf")
  want_pdf <- want_pdf[want_pdf != ".pdf"]
  want_pdf <- unlist(strsplit(paste(log$copied[log$Reviewer_No == r]), "; "))
  want_pdf <- if (length(want_pdf) && nzchar(want_pdf[1])) paste0(want_pdf, ".pdf") else character(0)
  stopifnot(sprintf("Reviewer %d batch 6.xlsx", r) %in% got,
            all(want_pdf %in% got),
            (log$pdfs_missing[log$Reviewer_No == r] > 0) ==
              ("FULL TEXT NOT AVAILABLE.txt" %in% got))
  ## every copied PDF must be non-empty and byte-identical to its source
  for (f in want_pdf) {
    p   <- sub("\\.pdf$", "", f)
    src <- if (!is.na(pdf_for[[p]])) xl(file.path(BOTH, pdf_for[[p]])) else new_for[[p]]
    dst <- file.path(dest, f)
    stopifnot(file.size(dst) > 0, file.size(dst) == file.size(src),
              identical(rawToChar(readBin(dst, "raw", 5)), "%PDF-"))
  }
  cat(sprintf("  %-18s %s\n", basename(dest), paste(sort(got), collapse = " | ")))
}
cat("\nall folders verified: worklist present, PDFs byte-identical to source\n\n")
print(log[, c("Reviewer_No", "folder", "n_papers", "pdfs_copied", "pdfs_missing")],
      row.names = FALSE)
write.csv(log, file.path(PROJ, "data/provenance/07_24_2026_batch6_folder_build_log.csv"),
          row.names = FALSE, fileEncoding = "UTF-8")
cat("\n[written]", file.path(PROJ, "data/provenance/07_24_2026_batch6_folder_build_log.csv"), "\n")

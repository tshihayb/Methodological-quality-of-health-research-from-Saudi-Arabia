# NOTE (public repository): 3 hard-coded study identifier(s) were
# rewritten to de-identified surrogates by tools/build_public_repo.py.
# They are rulings about particular studies rather than values the data
# can supply, so they have to travel with it.
###############################################################################
##  Fetch full text for the 3 NEWLY INCLUDED papers and store them by PMID.
##  Project: Assessment of Healthcare Research Quality in Saudi Arabia
##  Date   : 2026-07-24
##
##  WHY THIS EXISTS
##  The read-only store (389 PDFs, named by title) only covers the original 385
##  papers.  The papers added in 2026-07 were never collected, so their full text
##  has to be fetched once and kept somewhere the rest of the pipeline can find
##  it:  fulltext_new_papers_by_pmid\<PMID>.pdf
##
##  All three are free to read.  Licences: STUDY-0658 CC BY, STUDY-0161 CC BY-NC,
##  STUDY-0401 free-in-PMC (publisher SAGE, not in the NCBI OA subset -- fetched
##  from the Europe PMC renderer, which is the route Europe PMC itself advertises
##  as "Free" for this record).
##
##  NOTE the NCBI OA ftp paths that oa.fcgi still advertises
##  (ftp.ncbi.nlm.nih.gov/pub/pmc/oa_package/... and .../oa_pdf/...) now return
##  404 over https, and the /pmc/articles/<id>/pdf/ renderer returns an HTML
##  block page.  Europe PMC + publisher-direct links are what actually work.
##
##  Re-runnable: a PMID whose PDF is already present and valid is skipped.
###############################################################################

suppressPackageStartupMessages({ library(readxl); library(pdftools) })

PROJ  <- "."
STORE <- file.path(PROJ, "private/fulltext/pdf-by-pmid")
options(timeout = 300,
        HTTPUserAgent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")
if (!dir.exists(STORE)) dir.create(STORE)

## PMID -> (PMC id, DOI fragment used to confirm identity, candidate URLs in order)
SRC <- list(
  "STUDY-0401" = list(pmc = "[PMC-REDACTED]", doi = "19322968221085273", lic = "free in PMC (SAGE)",
    urls = c("https://europepmc.org/articles/[PMC-REDACTED]?pdf=render",
             "[ARTICLE-URL-REDACTED]")),
  "STUDY-0658" = list(pmc = "[PMC-REDACTED]",  doi = "mc.23355",          lic = "CC BY",
    urls = c("https://onlinelibrary.wiley.com/doi/pdfdirect/[DOI-REDACTED]",
             "https://europepmc.org/articles/[PMC-REDACTED]?pdf=render")),
  "STUDY-0161" = list(pmc = "[PMC-REDACTED]",  doi = "20210142",          lic = "CC BY-NC",
    urls = c("[ARTICLE-URL-REDACTED]",
             "https://europepmc.org/articles/[PMC-REDACTED]?pdf=render")))

meta <- as.data.frame(read_excel(file.path(PROJ, "private/reviewers/batch-6-distribution/Batch 6.xlsx"), col_types = "text"))
norm <- function(x) trimws(gsub("\\s+", " ", gsub("[^a-z0-9]+", " ", tolower(x))))
is_pdf <- function(f) file.exists(f) && file.size(f) > 5000 &&
                      identical(rawToChar(readBin(f, "raw", 5)), "%PDF-")

## Identity check: the paper's own DOI must appear in the text, and essentially
## all of the title's content words must appear on the opening pages.
verify <- function(f, pmid) {
  txt <- pdf_text(f)
  pg  <- norm(paste(txt[seq_len(min(2, length(txt)))], collapse = " "))
  w   <- setdiff(strsplit(norm(meta$title[meta$PMID == pmid]), " ")[[1]],
                 c("a","an","the","of","for","and","in","with","to","on","by"))
  list(pages = length(txt),
       title_hit = mean(vapply(w, function(k) grepl(k, pg, fixed = TRUE), logical(1))),
       doi_ok = grepl(norm(SRC[[pmid]]$doi), norm(paste(txt, collapse = " ")), fixed = TRUE))
}

log <- list()
for (p in names(SRC)) {
  f <- file.path(STORE, paste0(p, ".pdf")); used <- NA_character_
  if (is_pdf(f)) { used <- "(already present)"; cat("[skip]", p, "already present\n") }
  else for (u in SRC[[p]]$urls) {
    tryCatch(download.file(u, f, mode = "wb", quiet = TRUE),
             error = function(e) NULL, warning = function(w) NULL)
    if (is_pdf(f)) { used <- u; break }
    if (file.exists(f)) unlink(f)
  }
  if (!is_pdf(f)) { cat("[FAIL]", p, "- no working source\n")
                    log[[length(log)+1]] <- data.frame(PMID=p, pmc=SRC[[p]]$pmc,
                      licence=SRC[[p]]$lic, source=NA, bytes=NA, pages=NA,
                      title_match=NA, doi_confirmed=NA, md5=NA); next }
  v <- verify(f, p)
  ## refuse to keep a PDF that is not demonstrably the right paper
  stopifnot(v$doi_ok, v$title_hit >= 0.9)
  cat(sprintf("[ok]   %s  %7d bytes  %2d pages  title %3.0f%%  DOI confirmed  <- %s\n",
              p, file.size(f), v$pages, 100 * v$title_hit, used))
  log[[length(log)+1]] <- data.frame(PMID = p, pmc = SRC[[p]]$pmc,
    licence = SRC[[p]]$lic, source = used, bytes = file.size(f), pages = v$pages,
    title_match = round(v$title_hit, 3), doi_confirmed = v$doi_ok,
    md5 = unname(tools::md5sum(f)))
}
log <- do.call(rbind, log)
write.csv(log, file.path(PROJ, "data/provenance/07_24_2026_new_paper_fulltext_provenance.csv"),
          row.names = FALSE, fileEncoding = "UTF-8")
cat("\n"); print(log[, c("PMID","pmc","licence","bytes","pages","doi_confirmed")], row.names = FALSE)
cat("\n[store]", STORE, "\n[written]",
    file.path(PROJ, "data/provenance/07_24_2026_new_paper_fulltext_provenance.csv"), "\n")

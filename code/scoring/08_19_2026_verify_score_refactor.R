###############################################################################
##  ACCEPTANCE TEST for the score_dataset() refactor.
##
##  The refactor moved the scoring logic out of 07_30_2026_score_dataset.R and
##  into code/lib/score_dataset_lib.R as callable functions. The logic was copied
##  line for line, so the three published CSVs MUST be reproduced byte for byte.
##  This script proves it, and must keep passing.
##
##  Run from the repository root.
###############################################################################

source("code/lib/score_dataset_lib.R")

d <- read.csv("data/analysis/07_23_2026_ANALYSIS_DATASET_wide.csv", stringsAsFactors = FALSE,
              colClasses = "character", check.names = FALSE)

t0  <- Sys.time()
res <- score_dataset(d)
el  <- as.numeric(difftime(Sys.time(), t0, units = "secs"))
cat(sprintf("score_dataset() over %d papers in %.2f s\n", nrow(d), el))
cat(sprintf("  items %d rows | domain %d rows | study %d rows\n",
            nrow(res$items), nrow(res$domain), nrow(res$study)))

tmp <- file.path(tempdir(), "score_refactor_check"); dir.create(tmp, showWarnings = FALSE)
targets <- list(
  items  = list(new = file.path(tmp, "items.csv"),  old = "data/scoring/07_30_2026_scored_items_long.csv"),
  domain = list(new = file.path(tmp, "domain.csv"), old = "data/scoring/07_30_2026_scored_domain.csv"),
  study  = list(new = file.path(tmp, "study.csv"),  old = "data/scoring/07_30_2026_scored_study.csv"))

write.csv(res$items,  targets$items$new,  row.names = FALSE)
write.csv(res$domain, targets$domain$new, row.names = FALSE)
write.csv(res$study,  targets$study$new,  row.names = FALSE)

ok <- TRUE
for (nm in names(targets)) {
  a <- readBin(targets[[nm]]$new, "raw", file.size(targets[[nm]]$new))
  b <- readBin(targets[[nm]]$old, "raw", file.size(targets[[nm]]$old))
  same <- identical(a, b)
  ok <- ok && same
  cat(sprintf("  %-7s %s  (%d vs %d bytes)\n", nm,
              if (same) "IDENTICAL" else "*** DIFFERS ***", length(a), length(b)))
  if (!same) {
    x <- readLines(targets[[nm]]$new); y <- readLines(targets[[nm]]$old)
    n <- min(length(x), length(y)); dif <- which(x[seq_len(n)] != y[seq_len(n)])
    cat(sprintf("      %d differing lines; first 3:\n", length(dif)))
    for (i in head(dif, 3)) cat("        new:", x[i], "\n        old:", y[i], "\n")
  }
}
stopifnot(ok)
cat("\nPASS -- refactor reproduces all three published CSVs byte for byte.\n")

## The section-3 perturbation only needs roll_up(), which is the cheap half.
t1 <- Sys.time(); invisible(roll_up(res$items))
cat(sprintf("roll_up() alone: %.3f s per call -- this is what the tipping-point sweep repeats\n",
            as.numeric(difftime(Sys.time(), t1, units = "secs"))))

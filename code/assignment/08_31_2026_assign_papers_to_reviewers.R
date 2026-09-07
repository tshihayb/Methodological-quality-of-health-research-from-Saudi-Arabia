# NOTE (public repository): 6 hard-coded study identifier(s) were
# rewritten to de-identified surrogates by tools/build_public_repo.py.
# They are rulings about particular studies rather than values the data
# can supply, so they have to travel with it.
###############################################################################
##  STAGE 1b IN R: allocation of papers to reviewers, without SAS
##
##  Replaces the dependency on
##      code/sas-recovered-2026-08-31/assignment__stratified_by_task.sas
##  which is left in place, unmodified, as the historical record.
##
##  ⚠ READ THIS BEFORE EXPECTING A MATCH.  Unlike the calibration swap, this R
##  CANNOT reproduce the SAS allocation cell for cell, and no R ever will.
##  `proc surveyselect seed=100` draws from SAS's own random number stream;
##  R's generator is a different algorithm, so the same seed yields a different
##  permutation. The historical allocation is a fact, preserved in
##  private/reviewers/papers_assignment_strat{,_2}.xlsx, not something to
##  regenerate. What this script does instead is the two things that actually
##  remove the SAS dependency:
##
##    --verify  (default)  Check that the ARCHIVED allocation has the properties
##                         the procedure was supposed to give it. This is what
##                         lets the shipped pipeline run with no SAS present.
##    --draw               Perform a fresh allocation by the same procedure,
##                         seeded and reproducible in R, for anyone re-running
##                         the method on new data.
##
##  THE PROCEDURE, as read from the SAS:
##    1. sort papers into random order            (:52  streaminit(100), rand('Normal'))
##    2. split into 14 equal groups -> reviewer_1 (:81  surveyselect groups=14)
##    3. within each reviewer_1's papers, split into 13 groups -> reviewer_2,
##       the 13 being everyone except that first reviewer
##                                                (:124+ surveyselect groups=13,
##                                                 one seed per reviewer)
##
##  ⚠ There is NO `strata` statement anywhere in the 1,506-line SAS, despite the
##  filename "stratified by task". The task balance in the archived allocation is
##  what random splitting of 385 papers across 14 reviewers produces on its own,
##  not something the code enforced. This script therefore checks task balance as
##  an OUTCOME rather than imposing it, so that a real imbalance would show.
##
##  ⚠ `reviewer_2` is truncated to five characters in both archived workbooks:
##  the SAS declares `length reviewer_1 $20` (:92) and never declares
##  reviewer_2, so SAS sized it implicitly. `R13` reads as `Alhan` and
##  `R7` as `Musfe`, making 14 reviewers look like 16. Repaired on read here,
##  as `07_23_2026_batch6_random_assignment.R` already does.
##
##  Reads only data/assignment/ and private/reviewers/. Writes nothing unless
##  --draw is given, and then only into codes audit/output/.
###############################################################################
suppressPackageStartupMessages({ library(readxl); library(writexl) })

PROJ <- getwd()
ARCH <- file.path(PROJ, "private", "reviewers")
OUT  <- file.path(PROJ, "codes audit", "output", "assignment_draw")

REVIEWERS <- c("R1", "R2", "R-withdrawn", "R3", "R4", "R5", "R6",
               "R7", "R8", "R9", "R10", "R11", "R12", "R13")

## the five-character truncation, undone
fixnm <- function(x) { x[x == "Alhan"] <- "R13"; x[x == "Musfe"] <- "R7"; x }

read_arch <- function() {
  f <- function(p) as.data.frame(read_excel(file.path(ARCH, p), sheet = "assignment",
                                            col_types = "text"), check.names = FALSE)
  a <- rbind(f("papers_assignment_strat.xlsx"), f("papers_assignment_strat_2.xlsx"))
  a$reviewer_1 <- fixnm(trimws(a$reviewer_1))
  a$reviewer_2 <- fixnm(trimws(a$reviewer_2))
  a$PMID <- sub("\\.0$", "", trimws(a$PMID))
  a
}

## ---------------------------------------------------------------------------
## VERIFY the archived allocation
## ---------------------------------------------------------------------------
verify <- function() {
  a <- read_arch()
  ok <- TRUE
  say <- function(label, pass, detail) {
    cat(sprintf("  %-46s %s  %s\n", label, if (pass) "PASS" else "FAIL", detail))
    if (!pass) ok <<- FALSE
  }
  cat("VERIFY: the archived allocation, read without SAS\n")
  cat(strrep("=", 78), "\n")

  say("385 papers, no duplicate PMID",
      nrow(a) == 385 && !anyDuplicated(a$PMID),
      sprintf("%d rows, %d distinct", nrow(a), length(unique(a$PMID))))

  long <- data.frame(PMID = rep(a$PMID, 2),
                     task = rep(trimws(a$Study_Type), 2),
                     rev  = c(a$reviewer_1, a$reviewer_2), stringsAsFactors = FALSE)
  say("770 reviews, two per paper", nrow(long) == 770, sprintf("%d", nrow(long)))

  revs <- sort(unique(long$rev))
  say("exactly 14 reviewers after repairing the truncation",
      length(revs) == 14 && setequal(revs, REVIEWERS),
      paste(revs, collapse = ", "))

  ld <- table(long$rev)
  say("every reviewer carries an equal load",
      length(unique(as.integer(ld))) == 1,
      sprintf("min %d, max %d", min(ld), max(ld)))

  ## ⚠ TWO VINTAGES EXIST and they are not the same file. What SAS wrote sits in
  ## "Stratified reviewer papers/"; private/reviewers/ holds a later, corrected
  ## copy, and the two differ on seven papers of batch 2. The corrected copy is
  ## the operative one, matching what was actually reviewed. Checking only it
  ## hides the very error this stage is remembered for, so both are read here.
  self <- sum(a$reviewer_1 == a$reviewer_2)
  say("no self-pairing in the CORRECTED allocation", self == 0,
      sprintf("%d (private/reviewers, the operative copy)", self))

  raw_dir <- file.path(PROJ, "data", "assignment", "sas-outputs-2026-08-31")
  if (dir.exists(raw_dir)) {
    g <- function(p) as.data.frame(read_excel(file.path(raw_dir, p), sheet = "assignment",
                                              col_types = "text"), check.names = FALSE)
    s <- rbind(g("papers_assignment_strat.xlsx"), g("papers_assignment_strat_2.xlsx"))
    s$reviewer_1 <- fixnm(trimws(s$reviewer_1)); s$reviewer_2 <- fixnm(trimws(s$reviewer_2))
    s$PMID <- sub("\\.0$", "", trimws(s$PMID))
    sp <- which(s$reviewer_1 == s$reviewer_2)
    cat(sprintf("\n  as SAS wrote it (%d papers): %d self-pairing(s)\n", nrow(s), length(sp)))
    for (j in sp)
      cat(sprintf("     ** PMID %s, Seq %s: BOTH slots = %s. Only that reviewer ever\n"
                  , s$PMID[j], s$Seq[j], s$reviewer_1[j]),
          "        worked on it, so the paper stood one review short until batch 6.\n", sep = "")
    d <- merge(s[, c("PMID", "reviewer_1", "reviewer_2")],
               a[, c("PMID", "reviewer_1", "reviewer_2")], by = "PMID",
               suffixes = c(".sas", ".corr"))
    nd <- sum(d$reviewer_1.sas != d$reviewer_1.corr | d$reviewer_2.sas != d$reviewer_2.corr)
    cat(sprintf("  papers where the two vintages disagree: %d\n", nd))
  } else {
    cat("\n  (raw SAS outputs not present; only the corrected copy was checked)\n")
  }

  ## task balance as an OUTCOME, since nothing enforced it
  tb <- table(long$rev, long$task)
  cat("\n  task mix per reviewer (not enforced by the code; reported to be checked):\n")
  cat(sprintf("  %-10s %s\n", "reviewer",
              paste(sprintf("%12s", colnames(tb)), collapse = "")))
  for (r in rownames(tb))
    cat(sprintf("  %-10s %s\n", r, paste(sprintf("%12d", tb[r, ]), collapse = "")))
  spread <- apply(tb, 2, function(x) max(x) - min(x))
  cat(sprintf("\n  spread (max - min) per task: %s\n",
              paste(sprintf("%s %d", names(spread), spread), collapse = " | ")))

  ## how many distinct partners each reviewer had
  pr <- table(c(paste(a$reviewer_1, a$reviewer_2), paste(a$reviewer_2, a$reviewer_1)))
  cat(sprintf("  distinct reviewer pairs used: %d of the %d possible\n",
              length(pr) / 2, choose(14, 2)))

  cat("\n", strrep("=", 78), "\n", sep = "")
  cat(if (ok) "PASS: the archived allocation is intact and readable without SAS.\n"
      else "FAIL: see above.\n")
  invisible(ok)
}

## ---------------------------------------------------------------------------
## DRAW a fresh allocation by the same procedure
## ---------------------------------------------------------------------------
draw <- function(seed = 20260831) {
  src <- file.path(PROJ, "data", "assignment")
  ## ⚠ Use the round-2 file the SAS actually reads. There is a companion,
  ## "..._adjudicated_final.xlsx", which is a strict SUPERSET of 198 papers and is
  ## NOT the assignment input: 192 + 193 = 385, the target exactly, whereas
  ## 192 + 198 = 390. Reading the wrong one invents five papers that were never
  ## allocated. (:5 of assignment__stratified_by_task_round2.sas names this file.)
  f1 <- file.path(src, "Ready for data extraction with titles_adjudicated.xlsx")
  f2 <- file.path(src, "Ready for data extraction with titles round 2.xlsx")
  stopifnot(file.exists(f1), file.exists(f2))

  grab <- function(p) {
    d <- as.data.frame(read_excel(p, col_types = "text"), check.names = FALSE)
    tk <- if ("Modified study type" %in% names(d)) d[["Modified study type"]]
          else if ("Study Type_ta" %in% names(d)) d[["Study Type_ta"]]
          else d[["Study Type"]]
    data.frame(PMID = sub("\\.0$", "", trimws(d$PMID)),
               Title = d$Title, task = trimws(tk), stringsAsFactors = FALSE)
  }
  papers <- rbind(grab(f1), grab(f2))
  papers <- papers[!is.na(papers$PMID) & papers$PMID != "", ]
  papers <- papers[!duplicated(papers$PMID), ]

  ## The two files above give 192 + 193 = 385, matching the archived allocation
  ## exactly, so this guard should find nothing to drop. It stays as a tripwire:
  ## if someone points f2 at the 198-row "_adjudicated_final" companion instead,
  ## this reports the five surplus papers by name rather than silently allocating
  ## 390. Those five (STUDY-0500, STUDY-0080, STUDY-0586, STUDY-0668, STUDY-0846) were
  ## adjudicated Include but never entered the assignment list; two had no
  ## obtainable full text, and 385 was the target the study had already reached.
  arch_pmid <- read_arch()$PMID
  extra <- setdiff(papers$PMID, arch_pmid)
  if (length(extra)) {
    cat(sprintf("dropping %d paper(s) present in the extraction-ready lists but never allocated: %s\n",
                length(extra), paste(sort(extra), collapse = ", ")))
    papers <- papers[papers$PMID %in% arch_pmid, ]
  }
  cat(sprintf("drawing an allocation for %d papers, seed %d\n", nrow(papers), seed))

  ## 1. random order
  set.seed(seed)
  papers <- papers[sample(nrow(papers)), ]

  ## 2. 14 as-equal-as-possible groups -> first reviewer
  papers$reviewer_1 <- REVIEWERS[(seq_len(nrow(papers)) - 1) %% 14 + 1]

  ## 3. within each first reviewer, 13 groups over the other reviewers.
  ## ⚠ `others` must be SHUFFLED, not left in REVIEWERS order. A group of n papers
  ## over 13 reviewers leaves n mod 13 spare slots, and if `others` keeps its order
  ## those always fall to whoever sits earliest in REVIEWERS. Across all 14 groups
  ## that bias compounds: the first version of this script produced loads from 53
  ## to 67 where the archived SAS allocation is 55 for everyone. SAS avoids it
  ## because `surveyselect groups=13` randomises which group each row lands in.
  ## Shuffling alone only gets the spread to about 54-58, because chance decides
  ## who collects the spare slots. The archived SAS allocation is exactly 55 for
  ## all fourteen. Assign each second reviewer greedily to whoever currently
  ## carries the lightest total load, breaking ties at random, which reaches the
  ## same balance by construction rather than by luck.
  papers$reviewer_2 <- NA_character_
  load <- setNames(integer(length(REVIEWERS)), REVIEWERS)
  for (r in papers$reviewer_1) load[r] <- load[r] + 1L
  for (k in sample(nrow(papers))) {
    elig <- setdiff(REVIEWERS, papers$reviewer_1[k])
    cand <- elig[load[elig] == min(load[elig])]
    pick <- if (length(cand) == 1L) cand else sample(cand, 1L)
    papers$reviewer_2[k] <- pick
    load[pick] <- load[pick] + 1L
  }

  stopifnot(!any(papers$reviewer_1 == papers$reviewer_2), !anyDuplicated(papers$PMID))
  ld <- table(c(papers$reviewer_1, papers$reviewer_2))
  cat(sprintf("  loads: min %d, max %d across %d reviewers\n",
              min(ld), max(ld), length(ld)))

  dir.create(OUT, showWarnings = FALSE, recursive = TRUE)
  p <- file.path(OUT, sprintf("assignment_drawn_in_R_seed%d.xlsx", seed))
  writexl::write_xlsx(papers, p)
  cat(sprintf("  written -> %s\n", sub(PROJ, "", p, fixed = TRUE)))

  ## how far it is from the archived one, which it is NOT expected to match
  a <- read_arch()
  m <- merge(papers[, c("PMID", "reviewer_1", "reviewer_2")],
             a[, c("PMID", "reviewer_1", "reviewer_2")], by = "PMID", suffixes = c(".r", ".a"))
  same <- sum(mapply(function(a1, a2, b1, b2) setequal(c(a1, a2), c(b1, b2)),
                     m$reviewer_1.r, m$reviewer_2.r, m$reviewer_1.a, m$reviewer_2.a))
  cat(sprintf("\n  papers whose reviewer PAIR happens to match the archived draw: %d of %d\n",
              same, nrow(m)))
  cat("  (a match here is coincidence; SAS's RNG cannot be reproduced in R)\n")
  invisible(papers)
}

## ---------------------------------------------------------------------------
## REDISTRIBUTE reviewer 3's papers, and audit the lists reviewers actually got
## ---------------------------------------------------------------------------
## The SAS did this by hand: 55 lines of `if seq=N then reviewer_X="Name"`, one
## per paper, grouped by task, with no random draw at all. That is a lookup
## table, not an algorithm, so the R equivalent is to hold it as data and apply
## it. The table was extracted from the SAS into
## data/assignment/08_31_2026_reviewer3_redistribution.csv, which records the
## source line number for each row.
redistribute <- function() {
  a <- read_arch()
  a$Seq <- sub("\\.0$", "", trimws(a$Seq))
  tbl <- read.csv(file.path(PROJ, "data", "assignment",
                            "08_31_2026_reviewer3_redistribution.csv"),
                  colClasses = "character")
  cat("REDISTRIBUTE reviewer 3's papers, in R\n"); cat(strrep("=", 78), "\n")

  before <- sum(a$reviewer_1 == "R-withdrawn" | a$reviewer_2 == "R-withdrawn")
  cat(sprintf("  papers carrying reviewer 3 before : %d\n", before))
  cat(sprintf("  reassignments in the table        : %d\n", nrow(tbl)))

  hit <- 0
  for (i in seq_len(nrow(tbl))) {
    j <- which(a$Seq == tbl$Seq[i])
    if (length(j) != 1) next
    a[[if (tbl$slot[i] == "reviewer_1") "reviewer_1" else "reviewer_2"]][j] <- tbl$new_reviewer[i]
    hit <- hit + 1
  }
  cat(sprintf("  applied                           : %d\n", hit))

  after <- sum(a$reviewer_1 == "R-withdrawn" | a$reviewer_2 == "R-withdrawn")
  self  <- which(a$reviewer_1 == a$reviewer_2)
  ld <- table(c(a$reviewer_1, a$reviewer_2))
  cat(sprintf("  papers still carrying reviewer 3  : %d\n", after))
  cat(sprintf("  self-pairings introduced          : %d\n", length(self)))
  cat(sprintf("  reviewers now                     : %d, loads %d to %d\n",
              length(ld), min(ld), max(ld)))
  if (length(self)) for (j in self)
    cat(sprintf("     PMID %s both slots = %s\n", a$PMID[j], a$reviewer_1[j]))
  ok <- hit == nrow(tbl) && after == 0 && length(self) == 0
  cat(sprintf("\n  %s\n", if (ok) "PASS: reviewer 3 fully removed, no paper left with one reviewer twice."
              else "FAIL: see above."))
  invisible(list(ok = ok, assign = a))
}

## The planned allocation was clean, but the lists reviewers actually worked from
## are a separate artefact and are where a paper can appear twice for one person.
## That is the failure this checks for: it is how PMID STUDY-0449 reached one
## reviewer in two different batches, so she reviewed it twice and the other
## assigned reviewer never did.
audit_lists <- function() {
  dir <- file.path(ARCH, "assigned-lists-2026-08-31")
  fs <- list.files(dir, pattern = "_all_batches\\.xlsx$", full.names = TRUE)
  cat("\nAUDIT the lists reviewers actually received\n"); cat(strrep("=", 78), "\n")
  cat(sprintf("  workbooks: %d\n", length(fs)))
  bad <- 0
  for (f in sort(fs)) {
    who <- sub("_all_batches\\.xlsx$", "", basename(f))
    d <- suppressMessages(as.data.frame(read_excel(f, col_types = "text"),
                                        check.names = FALSE))
    if (!"PMID" %in% names(d)) next
    p <- sub("\\.0$", "", trimws(d$PMID)); p <- p[!is.na(p) & p != ""]
    tab <- table(p)
    dup <- names(tab)[tab > 1]
    if (length(dup)) {
      bad <- bad + length(dup)
      for (x in dup)
        cat(sprintf("  ** %s lists PMID %s %d times\n", who, x, tab[[x]]))
    }
  }
  cat(sprintf("\n  papers listed more than once for one reviewer: %d\n", bad))
  cat(if (bad == 0) "  PASS: no reviewer was handed the same paper twice.\n"
      else "  Each line above is a paper one reviewer was given twice.\n")
  invisible(bad)
}

args <- commandArgs(trailingOnly = TRUE)
if ("--draw" %in% args) {
  draw()
} else if ("--redistribute" %in% args) {
  r <- redistribute()
  b <- audit_lists()
  quit(status = if (isTRUE(r$ok)) 0 else 1)
} else {
  ok <- verify()
  quit(status = if (isTRUE(ok)) 0 else 1)
}

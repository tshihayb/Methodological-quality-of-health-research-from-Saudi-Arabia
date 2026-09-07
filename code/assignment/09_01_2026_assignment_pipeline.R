# NOTE (public repository): 16 hard-coded study identifier(s) were
# rewritten to de-identified surrogates by tools/build_public_repo.py.
# They are rulings about particular studies rather than values the data
# can supply, so they have to travel with it.
###############################################################################
##  THE ASSIGNMENT STAGE, END TO END, IN ONE SCRIPT
##
##  Replaces every SAS program in the assignment chain. The SAS files stay where
##  they are, unmodified, as the historical record:
##      assignment__stratified_by_task.sas        the initial allocation
##      assignment__stratified_by_task_round2.sas the same for batch 2
##      ..._Reassigning_reviewer3_papers.sas      the withdrawal, done by hand
##
##  ---------------------------------------------------------------------------
##  WHAT ACTUALLY HAPPENED, which this script encodes stage by stage
##  ---------------------------------------------------------------------------
##   1. 385 papers allocated across 14 reviewers, two each, 55 apiece.
##   2. Reviewer 3 withdrew after filing 3 reviews. Those 3 were discarded so
##      that every review in the analysis comes from one of 13 people; the 55
##      papers were redistributed.
##   3. Three papers were removed after allocation: one because YA was a
##      co-author, two because no author held a Saudi affiliation. FIVE completed
##      reviews went with them. On the co-authored paper the reviewer had already
##      recused, so the conflict was caught before the paper was excluded.
##   4. Three replacements were drawn from the 20-paper top-up pool.
##   5. Batch 6 closed the remaining gaps: 11 reviews over 8 papers, being the 3
##      replacements at two reviewers each, and 5 papers left short a second
##      review by a recusal, a withdrawal, or a double allocation.
##
##  ---------------------------------------------------------------------------
##  THREE FAULTS, PREVENTED BY CONSTRUCTION RATHER THAN CHECKED FOR
##  ---------------------------------------------------------------------------
##   A. A paper allocated to the SAME reviewer twice. Happened once, PMID
##      STUDY-0905 got R6 + R6, so only one person ever reviewed it. Here the
##      second reviewer is drawn from a pool that excludes the first.
##   B. A paper appearing TWICE on one reviewer's list. Happened once, STUDY-0449
##      reached reviewer 7 in batch 4 and again in batch 5. Here the lists are
##      derived from the allocation and asserted unique.
##   C. A replacement equal to the reviewer already on the paper. Every
##      reassignment draws from a pool excluding the sitting reviewer.
##
##  ---------------------------------------------------------------------------
##  MODES
##  ---------------------------------------------------------------------------
##    --replay   (default)  Emit the study's ACTUAL allocation, read from the
##                          archived workbooks. Deterministic, identical to SAS,
##                          and the only mode that reproduces the study.
##    --draw                Allocate afresh by the same procedure. Produces a
##                          different, equally valid allocation: SAS's generator
##                          is undocumented and no R seed reproduces it, so a
##                          re-draw agrees with the historical one on about 3 of
##                          385 papers, which is chance across 91 possible pairs.
##    --audit               Check the archived allocation and the per-reviewer
##                          lists, and reconcile planned against realised.
##
##  Add --write to save. Nothing is written otherwise, and nothing outside
##  codes audit/output/ is ever written.
###############################################################################
suppressPackageStartupMessages({ library(readxl); library(writexl) })

PROJ <- getwd()
ARCH <- file.path(PROJ, "private", "reviewers")
OUT  <- file.path(PROJ, "codes audit", "output", "assignment")

REVIEWERS <- c("R1", "R2", "R-withdrawn", "R3", "R4", "R5", "R6",
               "R7", "R8", "R9", "R10", "R11", "R12", "R13")
WITHDREW  <- "R-withdrawn"                       # reviewer 3; 3 reviews discarded

## Removed after allocation, with the reviews that were discarded with them.
REMOVED <- data.frame(
  PMID   = c("STUDY-0956", "STUDY-0136", "STUDY-0478"),
  reason = c("YA is a co-author", "no Saudi affiliation", "no Saudi affiliation"),
  lost   = c(1L, 2L, 2L),                  # completed reviews discarded: 5 in all
  note   = c("the assigned reviewer had already recused, catching the conflict", "", ""),
  stringsAsFactors = FALSE)

REPLACEMENTS <- c("STUDY-0658", "STUDY-0401", "STUDY-0161")   # from the 20-paper pool

## Papers that reached batch 6 one review short.
SHORT <- c("STUDY-0905",   # allocated R6 + R6, so only R6 ever reviewed it
           "STUDY-0449",   # listed twice for reviewer 7; the other reviewer never filed
           "STUDY-0473",   # a review existed but its PMID cell held the task answer
           "STUDY-0183")   # a reviewer recused and the slot was never refilled

args     <- commandArgs(trailingOnly = TRUE)
MODE     <- if ("--draw" %in% args) "draw" else
            if ("--audit" %in% args) "audit" else
            if ("--final" %in% args) "final" else "replay"
SEED     <- if ("--seed" %in% args) as.integer(args[which(args == "--seed") + 1]) else 20260901L
DO_WRITE <- "--write" %in% args

## `reviewer_2` was written with no length statement, so SAS sized it at five
## characters: R13 reads as Alhan and R7 as Musfe, making 14 reviewers
## look like 16. Undone on every read.
fixnm <- function(x) { x[x == "Alhan"] <- "R13"; x[x == "Musfe"] <- "R7"; x }

say <- function(...) cat(sprintf(...))
rule <- function(n = 78) cat(strrep("=", n), "\n", sep = "")


## ===========================================================================
## SHARED: loads, and the one rule that keeps everything level
## ===========================================================================

## Narrow `pool` by each load vector in turn, break the last tie at random.
## ⚠ Order matters. Balancing each task on its own counter alone leaves a
## remainder per task, and nothing stops all three landing on one person: that
## gave loads of 53 to 56 in an early version. Overall load as a second key
## spreads them. After the initial allocation the order flips, because once the
## strata exist the totals are what reviewers actually feel.
pick <- function(pool, ...) {
  stopifnot(length(pool) > 0)
  cand <- pool
  for (load in list(...)) {
    if (length(cand) == 1L) break
    cand <- cand[load[cand] == min(load[cand])]
  }
  if (length(cand) == 1L) cand else sample(cand, 1L)
}

loads_of <- function(papers, who) {
  ov <- setNames(integer(length(who)), who)
  tk <- lapply(setNames(nm = sort(unique(papers$task))),
               function(x) setNames(integer(length(who)), who))
  for (j in seq_len(nrow(papers))) {
    for (r in c(papers$reviewer_1[j], papers$reviewer_2[j])) {
      if (is.na(r) || !r %in% who) next
      ov[r] <- ov[r] + 1L
      tk[[papers$task[j]]][r] <- tk[[papers$task[j]]][r] + 1L
    }
  }
  list(overall = ov, task = tk)
}


## ===========================================================================
## REPLAY: the study's actual allocation
## ===========================================================================
read_archived <- function() {
  one <- function(p, batch) {
    d <- as.data.frame(read_excel(file.path(ARCH, p), sheet = "assignment",
                                  col_types = "text"), check.names = FALSE)
    d$PMID <- sub("[.]0$", "", trimws(d$PMID))
    d$Seq  <- sub("[.]0$", "", trimws(d$Seq))
    d$reviewer_1 <- fixnm(trimws(d$reviewer_1))
    d$reviewer_2 <- fixnm(trimws(d$reviewer_2))
    data.frame(batch = batch, Seq = d$Seq, PMID = d$PMID, Title = d$Title,
               task = trimws(d$Study_Type),
               reviewer_1 = d$reviewer_1, reviewer_2 = d$reviewer_2,
               stringsAsFactors = FALSE)
  }
  a <- rbind(one("papers_assignment_strat.xlsx", 1L),
             one("papers_assignment_strat_2.xlsx", 2L))
  a[order(as.integer(a$Seq)), ]
}


## ===========================================================================
## DRAW: allocate afresh, by the same procedure
## ===========================================================================
allocate <- function(papers, reviewers = REVIEWERS) {
  papers$reviewer_1 <- NA_character_
  papers$reviewer_2 <- NA_character_
  overall <- setNames(integer(length(reviewers)), reviewers)
  for (tk in sample(unique(papers$task))) {
    idx <- sample(which(papers$task == tk))
    tload <- setNames(integer(length(reviewers)), reviewers)
    for (i in idx) {
      r1 <- pick(reviewers, tload, overall)
      r2 <- pick(setdiff(reviewers, r1), tload, overall)   # (A) pool excludes r1
      papers$reviewer_1[i] <- r1; papers$reviewer_2[i] <- r2
      tload[c(r1, r2)]   <- tload[c(r1, r2)] + 1L
      overall[c(r1, r2)] <- overall[c(r1, r2)] + 1L
    }
  }
  papers
}

withdraw <- function(papers, who, reviewers = REVIEWERS) {
  remaining <- setdiff(reviewers, who)
  L <- loads_of(papers, reviewers)
  hit <- which(papers$reviewer_1 == who | papers$reviewer_2 == who)
  for (i in sample(hit)) {
    slot    <- if (papers$reviewer_1[i] == who) "reviewer_1" else "reviewer_2"
    partner <- if (slot == "reviewer_1") papers$reviewer_2[i] else papers$reviewer_1[i]
    tk <- papers$task[i]
    repl <- pick(setdiff(remaining, partner), L$overall, L$task[[tk]])  # (C)
    papers[[slot]][i] <- repl
    L$overall[repl] <- L$overall[repl] + 1L; L$overall[who] <- L$overall[who] - 1L
    L$task[[tk]][repl] <- L$task[[tk]][repl] + 1L
    L$task[[tk]][who]  <- L$task[[tk]][who]  - 1L
  }
  attr(papers, "n_moved") <- length(hit)
  papers
}

## Papers leave the sample after allocation. Their completed reviews are lost,
## which is a real cost and is reported rather than quietly absorbed.
remove_papers <- function(papers, removed) {
  gone <- papers[papers$PMID %in% removed$PMID, ]
  papers <- papers[!papers$PMID %in% removed$PMID, ]
  attr(papers, "removed") <- gone
  papers
}

## Batch 6: replacements need two reviewers, short papers need a second.
batch6 <- function(papers, replacements, short_pmids, reviewers = REVIEWERS) {
  active <- setdiff(reviewers, WITHDREW)
  if (length(replacements)) {
    add <- data.frame(batch = 6L, Seq = NA_character_, PMID = replacements,
                      Title = paste("replacement", replacements),
                      task = "Descriptive",
                      reviewer_1 = NA_character_, reviewer_2 = NA_character_,
                      stringsAsFactors = FALSE)
    papers <- rbind(papers, add[, names(papers)])
  }
  L <- loads_of(papers, active)
  bump <- function(r, tk) { L$overall[r] <<- L$overall[r] + 1L
                            L$task[[tk]][r] <<- L$task[[tk]][r] + 1L }

  for (i in sample(which(is.na(papers$reviewer_1)))) {
    tk <- papers$task[i]
    r1 <- pick(active, L$overall, L$task[[tk]])
    r2 <- pick(setdiff(active, r1), L$overall, L$task[[tk]])   # (A)
    papers$reviewer_1[i] <- r1; papers$reviewer_2[i] <- r2
    bump(r1, tk); bump(r2, tk)
  }

  ## ⚠ Debit the reviewer who never delivered as well as crediting the new one.
  ## Crediting alone inflates the totals and hides who has capacity.
  for (p in sample(intersect(short_pmids, papers$PMID))) {
    i <- which(papers$PMID == p)
    tk <- papers$task[i]
    keep <- papers$reviewer_1[i]
    out  <- papers$reviewer_2[i]
    if (!is.na(out) && out %in% active) {
      L$overall[out] <- L$overall[out] - 1L
      L$task[[tk]][out] <- L$task[[tk]][out] - 1L
    }
    papers$reviewer_2[i] <- pick(setdiff(active, keep), L$overall, L$task[[tk]])  # (C)
    bump(papers$reviewer_2[i], tk)
  }
  papers
}


## ===========================================================================
## LISTS AND CHECKS
## ===========================================================================
## Derived from the allocation, never assembled by hand. This is the step where
## a paper previously got onto one reviewer's list twice.
make_lists <- function(papers) {
  who <- sort(unique(c(papers$reviewer_1, papers$reviewer_2)))
  setNames(lapply(who, function(r) {
    d <- papers[papers$reviewer_1 == r | papers$reviewer_2 == r, ]
    d$role <- ifelse(d$reviewer_1 == r, "first", "second")
    d[order(d$task, d$PMID), c("PMID", "Title", "task", "role")]
  }), who)
}

check <- function(papers, lists, label, tol_load = 1L, tol_task = 2L,
                  expect_gone = TRUE) {
  say("\n%s\n%s\n", label, strrep("-", nchar(label)))
  fail <- character(0)
  ck <- function(n, ok, d = "") {
    say("  %-50s %s %s\n", n, if (ok) "ok  " else "FAIL", d)
    if (!ok) fail <<- c(fail, n)
  }
  ck("every paper has two reviewers",
     !any(is.na(papers$reviewer_1) | is.na(papers$reviewer_2)))
  ck("(A) no paper allocated to one reviewer twice",
     !any(papers$reviewer_1 == papers$reviewer_2),
     sprintf("%d", sum(papers$reviewer_1 == papers$reviewer_2)))
  ck("(B) no reviewer's list holds a paper twice",
     sum(vapply(lists, function(d) sum(duplicated(d$PMID)), integer(1))) == 0)
  ck("no duplicate PMID in the allocation", !anyDuplicated(papers$PMID))
  held <- sum(c(papers$reviewer_1, papers$reviewer_2) == WITHDREW)
  if (expect_gone) ck("the withdrawn reviewer holds nothing", held == 0, sprintf("%d", held))
  else say("  %-50s --   %d papers\n", "(withdrawn reviewer still active here)", held)
  ld <- table(c(papers$reviewer_1, papers$reviewer_2))
  ck(sprintf("loads level to within %d", tol_load), max(ld) - min(ld) <= tol_load,
     sprintf("%d to %d across %d", min(ld), max(ld), length(ld)))
  tb <- table(c(papers$reviewer_1, papers$reviewer_2), rep(papers$task, 2))
  sp <- apply(tb, 2, function(x) max(x) - min(x))
  ck(sprintf("task mix level to within %d", tol_task), all(sp <= tol_task),
     paste(sprintf("%s %d", names(sp), sp), collapse = " | "))
  ck("reviewer names not truncated", all(names(ld) %in% REVIEWERS))
  if (length(fail)) stop("FAILED: ", paste(fail, collapse = "; "))
  invisible(TRUE)
}

report_loads <- function(papers, title) {
  tb <- table(c(papers$reviewer_1, papers$reviewer_2), rep(papers$task, 2))
  say("\n%s\n", title)
  say("  %-11s %6s | %s\n", "reviewer", "total",
      paste(sprintf("%12s", colnames(tb)), collapse = ""))
  for (r in rownames(tb))
    say("  %-11s %6d | %s\n", r, sum(tb[r, ]),
        paste(sprintf("%12d", tb[r, ]), collapse = ""))
  say("  %-11s %6d\n", "TOTAL", sum(tb))
}


## ===========================================================================
## RUN
## ===========================================================================
read_papers <- function() {
  src <- file.path(PROJ, "data", "assignment")
  grab <- function(p) {
    d <- as.data.frame(read_excel(file.path(src, p), col_types = "text"),
                       check.names = FALSE)
    tk <- if ("Modified study type" %in% names(d)) d[["Modified study type"]]
          else d[["Study Type"]]
    data.frame(batch = if (grepl("round 2", p)) 2L else 1L,
               Seq = sub("[.]0$", "", trimws(d$Seq)),
               PMID = sub("[.]0$", "", trimws(d$PMID)),
               Title = d$Title, task = trimws(tk), stringsAsFactors = FALSE)
  }
  ## ⚠ Use "round 2.xlsx", not "..._adjudicated_final.xlsx". The latter is a
  ## 198-row superset sitting beside it; 192 + 193 = 385 is the target exactly,
  ## while 192 + 198 = 390 invents five papers that were never allocated.
  p <- rbind(grab("Ready for data extraction with titles_adjudicated.xlsx"),
             grab("Ready for data extraction with titles round 2.xlsx"))
  p <- p[!is.na(p$PMID) & p$PMID != "" & !duplicated(p$PMID), ]
  p$task[!p$task %in% c("Causal", "Descriptive", "Predictive")] <- "Descriptive"
  p
}

## ⚠ Must be restricted to the papers actually analysed. Counting every export
## row also counts reviews of the three papers removed after allocation, which
## were discarded, and the arithmetic against 770 then does not close.
realised_counts <- function() {
  analysed <- trimws(read.csv(file.path(PROJ, "data", "analysis",
                              "07_23_2026_ANALYSIS_DATASET_wide.csv"),
                              colClasses = "character")$PMID)
  fe <- file.path(ARCH, "form-exports")
  fs <- list.files(fe, pattern = "Reviewer_[0-9]+[.]xlsx$", full.names = TRUE)
  ids <- as.integer(sub(".*Reviewer_([0-9]+)[.]xlsx$", "\\1", fs))
  nm <- setNames(REVIEWERS, as.character(seq_along(REVIEWERS)))
  seen <- list(); out <- setNames(integer(length(REVIEWERS)), REVIEWERS)
  for (k in seq_along(fs)) {
    rid <- ids[k]
    if (rid == 3L) next                       # the withdrawn reviewer's 3 discarded
    d <- suppressMessages(as.data.frame(read_excel(fs[k], col_types = "text")))
    pm <- sub("[.]0$", "", trimws(d[[2]]))
    rec <- grepl("^Yes", trimws(d[[3]]))
    keep <- unique(pm[!rec & !is.na(pm) & pm != "" & pm %in% analysed])
    who <- nm[[as.character(rid)]]
    out[who] <- out[who] + length(keep)
  }
  out[out > 0]
}

rule(); say("ASSIGNMENT PIPELINE  |  mode: %s\n", MODE); rule()

if (MODE == "replay") {
  a <- read_archived()
  lists <- make_lists(a)
  say("the study's actual allocation, read without SAS\n")
  say("  papers %d (batch 1: %d, batch 2: %d) | reviews %d\n",
      nrow(a), sum(a$batch == 1), sum(a$batch == 2), 2 * nrow(a))
  ## tol_task is 2 here because that is what the archived allocation actually
  ## has: R4 carries 13 descriptive against a low of 11. The SAS never
  ## stratified, so its task balance is whatever the draw happened to give. The
  ## LOAD is exactly level at 55, which is checked strictly. Failing replay on a
  ## property of the historical record would be checking the past against a
  ## standard it was never held to.
  check(a, lists, "CHECKS on the archived allocation",
        tol_load = 0L, tol_task = 2L, expect_gone = FALSE)
  report_loads(a, "as allocated, all fourteen reviewers")
  say("\nNOTE  This is the allocation as first drawn, before reviewer 3 withdrew.\n")
  say("      Downstream the analysis uses the REALISED distribution, which differs\n")
  say("      because of the withdrawal, three removed papers, recusals and batch 6.\n")
  if (DO_WRITE) {
    dir.create(OUT, showWarnings = FALSE, recursive = TRUE)
    writexl::write_xlsx(a, file.path(OUT, "09_01_2026_allocation_385.xlsx"))
    writexl::write_xlsx(lists, file.path(OUT, "09_01_2026_reviewer_lists.xlsx"))
    say("\nwritten -> %s\n", sub(PROJ, "", OUT, fixed = TRUE))
  }
}

if (MODE == "draw") {
  set.seed(SEED)
  say("a fresh allocation by the same procedure, seed %d\n", SEED)
  say("⚠ this is NOT the study's allocation and cannot be: SAS's generator is\n")
  say("  undocumented, so a re-draw agrees with it on about 3 of 385 papers.\n\n")

  papers <- read_papers()
  say("stage 1  allocate %d papers across %d reviewers\n", nrow(papers), length(REVIEWERS))
  a <- allocate(papers)
  check(a, make_lists(a), "CHECKS after stage 1", 0L, 1L, expect_gone = FALSE)

  say("\nstage 2  %s withdraws; 3 filed reviews discarded\n", WITHDREW)
  a <- withdraw(a, WITHDREW)
  say("         %d papers redistributed to the other %d\n",
      attr(a, "n_moved"), length(REVIEWERS) - 1L)

  say("\nstage 3  three papers removed after allocation\n")
  a <- remove_papers(a, REMOVED)
  gone <- attr(a, "removed")
  for (j in seq_len(nrow(REMOVED)))
    say("         %s  %-22s  %d review(s) discarded%s\n", REMOVED$PMID[j],
        REMOVED$reason[j], REMOVED$lost[j],
        if (nzchar(REMOVED$note[j])) paste0("; ", REMOVED$note[j]) else "")
  say("         %d papers remain; %d completed reviews lost in total\n",
      nrow(a), sum(REMOVED$lost))

  say("\nstage 4+5  three replacements, and %d papers short a second review\n",
      length(SHORT))
  a <- batch6(a, REPLACEMENTS, SHORT)
  say("         %d papers, %d reviews\n", nrow(a), 2 * nrow(a))

  lists <- make_lists(a)
  check(a, lists, "CHECKS after the full sequence", 1L, 2L)
  report_loads(a, "final, thirteen reviewers")
  if (DO_WRITE) {
    dir.create(OUT, showWarnings = FALSE, recursive = TRUE)
    writexl::write_xlsx(a, file.path(OUT, sprintf("drawn_seed%d.xlsx", SEED)))
    writexl::write_xlsx(lists, file.path(OUT, sprintf("drawn_lists_seed%d.xlsx", SEED)))
    say("\nwritten -> %s\n", sub(PROJ, "", OUT, fixed = TRUE))
  }
}

if (MODE == "audit") {
  a <- read_archived()
  check(a, make_lists(a), "CHECKS on the archived allocation",
        tol_load = 0L, tol_task = 2L, expect_gone = FALSE)

  dir <- file.path(ARCH, "assigned-lists-2026-08-31")
  if (dir.exists(dir)) {
    fs <- list.files(dir, pattern = "_all_batches[.]xlsx$", full.names = TRUE)
    say("\nthe lists reviewers actually received (%d workbooks)\n", length(fs))
    bad <- 0L
    for (f in sort(fs)) {
      d <- suppressMessages(as.data.frame(read_excel(f, col_types = "text")))
      if (!"PMID" %in% names(d)) next
      p <- sub("[.]0$", "", trimws(d$PMID)); p <- p[!is.na(p) & p != ""]
      tb <- table(p); dup <- names(tb)[tb > 1]
      for (x in dup) {
        bad <- bad + 1L
        say("  ** %s holds PMID %s %d times\n",
            sub("_all_batches[.]xlsx$", "", basename(f)), x, tb[[x]])
      }
    }
    say("  papers listed twice for one reviewer: %d\n", bad)
  }

  say("\nplanned against realised\n")
  real <- realised_counts()
  say("  %-11s %9s %9s %7s\n", "reviewer", "REALISED", "", "")
  for (r in sort(names(real))) say("  %-11s %9d\n", r, real[[r]])
  say("  %-11s %9d  reviews filed in the main round on analysed papers\n",
      "TOTAL", sum(real))
  say("\n  The gap to 770 is closed by batch 6, which supplied 11 reviews:\n")
  say("    3 replacement papers x 2 reviewers = 6\n")
  say("    5 papers short a second review     = 5\n")
  say("  Separately, %d reviews were completed on the three removed papers and\n",
      sum(REMOVED$lost))
  say("  discarded, plus %d from the reviewer who withdrew.\n", 3L)
}

say("\n")


## ===========================================================================
## FINAL: who actually reviewed each of the 385 analysed papers
## ===========================================================================
## ⚠ THIS, not the allocation, is what the analysis rests on. The allocation is
## the plan; this is the outcome, and they differ because a reviewer withdrew,
## three papers were removed, some reviewers recused, one paper was allocated to
## the same person twice and another appeared twice on one list. No assignment
## code can produce this table, in R or SAS: it is a record of what people did.
##
## Sources: the latest export per reviewer. The eight 08_08_2026 CSVs are later
## exports of the same forms and supersede the corresponding xlsx, because they
## carry the batch-6 reviews as well as everything before them.
##
## Rules applied, matching 05_19_2025_analysis.sas:
##   drop reviewer 3 entirely                                       (:2620)
##   drop 8 duplicate submissions, keyed on PMID and timestamp      (:403 etc)
##   repair one PMID typed as the task answer                       (:1292)
##   pair the surviving reviews per paper in submission order

DUP_DROP <- rbind(
  c("STUDY-0183", "2025/02/02 7:13:59 PM GMT+3"),
  c("STUDY-0017", "2024/08/30 11:47:06 AM GMT+3"),
  c("STUDY-0171", "2025/01/14 11:00:41 AM GMT+3"),
  c("STUDY-0449", "2025/05/16 10:55:46 PM GMT+3"),
  c("STUDY-0852", "2024/12/07 9:06:59 PM GMT+3"),
  c("STUDY-0275", "2024/12/16 8:58:20 PM GMT+3"),
  c("STUDY-0228", "2024/12/22 11:58:30 AM GMT+3"),
  c("STUDY-0336", "2024/08/15 10:42:46 AM GMT+3"))
PMID_REPAIR_RID <- 7L
PMID_REPAIR_TO  <- "STUDY-0473"

read_submissions <- function() {
  fe <- file.path(ARCH, "form-exports")
  fs <- list.files(fe, full.names = TRUE)
  rid_of <- function(f) as.integer(sub(".*Reviewer_([0-9]+)[.](xlsx|csv)$", "\\1", basename(f)))
  fs <- fs[grepl("Reviewer_[0-9]+[.](xlsx|csv)$", basename(fs))]
  ## latest export per reviewer: prefer the csv when both exist
  best <- list()
  for (f in fs) {
    r <- as.character(rid_of(f))
    if (is.null(best[[r]]) || grepl("[.]csv$", f)) best[[r]] <- f
  }
  out <- NULL
  for (r in names(best)) {
    f <- best[[r]]
    d <- if (grepl("[.]csv$", f))
           read.csv(f, colClasses = "character", check.names = FALSE)
         else suppressMessages(as.data.frame(read_excel(f, col_types = "text"),
                                             check.names = FALSE))
    ts <- trimws(d[[1]]); pm <- trimws(d[[2]]); rec <- trimws(d[[3]])
    rid <- as.integer(r)
    ## the one PMID typed as the task answer
    bad <- rid == PMID_REPAIR_RID & !grepl("^[0-9]+$", pm) & nzchar(pm)
    pm[bad] <- PMID_REPAIR_TO
    keep <- grepl("^[0-9]+$", pm)
    out <- rbind(out, data.frame(rid = rid, PMID = pm[keep], ts = ts[keep],
                                 recused = grepl("^Yes", rec[keep]),
                                 stringsAsFactors = FALSE))
  }
  out$reviewer <- REVIEWERS[out$rid]
  out
}

final_pairs <- function() {
  s <- read_submissions()
  n0 <- nrow(s)
  s <- s[s$rid != 3L, ]                                   # the withdrawn reviewer
  n1 <- nrow(s)
  drop <- paste(DUP_DROP[, 1], DUP_DROP[, 2])
  s <- s[!(paste(s$PMID, s$ts) %in% drop), ]              # duplicate submissions
  n2 <- nrow(s)
  s <- s[!s$recused, ]                                    # recusals are not reviews
  n3 <- nrow(s)
  s <- s[!duplicated(paste(s$PMID, s$rid)), ]             # one review per person per paper
  n4 <- nrow(s)

  analysed <- trimws(read.csv(file.path(PROJ, "data", "analysis",
                              "07_23_2026_ANALYSIS_DATASET_wide.csv"),
                              colClasses = "character")$PMID)
  s <- s[s$PMID %in% analysed, ]
  say("  submissions read                         %5d\n", n0)
  say("  after dropping the withdrawn reviewer    %5d  (-%d)\n", n1, n0 - n1)
  say("  after dropping duplicate submissions     %5d  (-%d)\n", n2, n1 - n2)
  say("  after dropping recusals                  %5d  (-%d)\n", n3, n2 - n3)
  say("  after one review per person per paper    %5d  (-%d)\n", n4, n3 - n4)
  say("  restricted to the %d analysed papers    %5d\n", length(analysed), nrow(s))

  ## ⚠ Order by REVIEWER ID, not by timestamp. The analysis stacks the exports
  ## `set r1-r14` and sorts by PMID, and SAS's sort keeps the input order within
  ## a BY group, so first_reviewer is the LOWEST reviewer id, not the earliest
  ## submission. The two orderings disagree wherever a paper carries three valid
  ## reviews, because PROC TRANSPOSE drops COL3: sorting by timestamp would keep
  ## a different pair than the analysis kept.
  o <- s[order(s$PMID, s$rid), ]
  sp <- split(o, o$PMID)
  res <- do.call(rbind, lapply(names(sp), function(p) {
    d <- sp[[p]]
    data.frame(PMID = p, n = nrow(d),
               reviewer_1 = d$reviewer[1],
               reviewer_2 = if (nrow(d) > 1) d$reviewer[2] else NA_character_,
               stringsAsFactors = FALSE)
  }))
  missing <- setdiff(analysed, res$PMID)
  attr(res, "missing") <- missing
  res
}

if (MODE == "final") {
  say("the reviewer pairing the ANALYSIS actually used\n\n")
  res <- final_pairs()
  say("\n  papers paired                            %5d\n", nrow(res))
  say("  papers with exactly two reviewers        %5d\n", sum(res$n == 2))
  short <- res[res$n != 2, ]
  if (nrow(short)) for (j in seq_len(nrow(short)))
    say("    ** PMID %s has %d reviewer(s): %s\n", short$PMID[j], short$n[j],
        paste(na.omit(c(short$reviewer_1[j], short$reviewer_2[j])), collapse = " + "))
  if (length(attr(res, "missing")))
    say("  analysed papers with NO review found: %s\n",
        paste(attr(res, "missing"), collapse = ", "))

  ld <- table(c(res$reviewer_1, res$reviewer_2[!is.na(res$reviewer_2)]))
  say("\n  final load per reviewer (%d reviewers, %d reviews)\n",
      length(ld), sum(ld))
  for (r in sort(names(ld))) say("    %-11s %4d\n", r, ld[[r]])
  say("    %-11s %4d\n", "TOTAL", sum(ld))
  self <- sum(res$reviewer_1 == res$reviewer_2, na.rm = TRUE)
  say("\n  papers whose two reviews came from the same person: %d\n", self)

  if (DO_WRITE) {
    dir.create(OUT, showWarnings = FALSE, recursive = TRUE)
    writexl::write_xlsx(res, file.path(OUT, "09_01_2026_final_reviewer_pairs_385.xlsx"))
    write.csv(res, file.path(OUT, "09_01_2026_final_reviewer_pairs_385.csv"),
              row.names = FALSE, na = "")
    say("\nwritten -> %s\n", sub(PROJ, "", OUT, fixed = TRUE))
  }
}

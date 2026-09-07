# NOTE (public repository): 7 hard-coded study identifier(s) were
# rewritten to de-identified surrogates by tools/build_public_repo.py.
# They are rulings about particular studies rather than values the data
# can supply, so they have to travel with it.
###############################################################################
##  CLEAN PAPER-TO-REVIEWER ASSIGNMENT, IN R
##
##  Does what the SAS assignment was meant to do, with the three faults that
##  actually occurred made impossible by construction rather than caught after
##  the fact:
##
##    1. A paper allocated to the SAME reviewer in both slots.
##       Happened once: PMID STUDY-0905 got R6 + R6, so only one person ever
##       reviewed it. Here the second reviewer is drawn from the pool EXCLUDING
##       the first, so the situation cannot arise.
##
##    2. A paper appearing TWICE on one reviewer's list.
##       Happened once: STUDY-0449 reached reviewer 7 in batch 4 and again in
##       batch 5. Here the per-reviewer lists are derived from the allocation and
##       asserted unique, so a paper cannot be handed out twice.
##
##    3. A withdrawal replaced by the reviewer already on the paper.
##       When reviewer 3 left, each of the 55 papers already had a second
##       reviewer, so the replacement pool is the other TWELVE, not thirteen.
##       That exclusion is enforced, not remembered.
##
##  FAITHFUL TO THE SAS IN STRUCTURE: 14 reviewers, every paper read by two of
##  them, loads equal, and the task mix even across reviewers. One deliberate
##  difference: the SAS filename says "stratified by task" but the program has no
##  `strata` statement anywhere, and its even task mix is what random splitting of
##  385 papers happens to give. Here the stratification is real, so the balance
##  holds by design instead of by luck. The resulting per-reviewer figures are the
##  same ones the SAS reached: 55 papers each, about 33 causal, 12 descriptive and
##  11 predictive.
##
##  NOT faithful in one respect that no R can fix: `proc surveyselect seed=100`
##  draws from SAS's own generator, so this produces a different, equally valid
##  allocation rather than the historical one. The historical allocation stays
##  where it is and is never touched.
##
##  USAGE
##    Rscript code/assignment/08_31_2026_clean_assignment.R [--seed N] [--write]
##  Writes nothing unless --write, and then only into codes audit/output/.
###############################################################################
suppressPackageStartupMessages({ library(readxl); library(writexl) })

PROJ <- getwd()
OUT  <- file.path(PROJ, "codes audit", "output", "clean_assignment")

REVIEWERS <- c("R1", "R2", "R-withdrawn", "R3", "R4", "R5", "R6",
               "R7", "R8", "R9", "R10", "R11", "R12", "R13")
WITHDREW  <- "R-withdrawn"          # reviewer 3, who left after three reviews

args    <- commandArgs(trailingOnly = TRUE)
SEED    <- if ("--seed" %in% args) as.integer(args[which(args == "--seed") + 1]) else 20260831L
DO_WRITE <- "--write" %in% args


## ---------------------------------------------------------------------------
## helpers
## ---------------------------------------------------------------------------

## Pick the least-loaded reviewer from `pool`, narrowing by each load vector in
## turn and breaking the final tie at random. Every allocation decision goes
## through here, which is what keeps the loads level without a rebalancing pass.
##
## ⚠ The order of the load vectors matters. Balancing each task on its own
## counter alone is not enough: 228 causal papers over 14 reviewers leaves a
## remainder, so does each other task, and nothing stops all three remainders
## landing on the same person. That is exactly what happened on the first run,
## giving loads of 53 to 56 where every reviewer should carry the same. Passing
## the overall load as a second key spreads the remainders instead of letting
## them stack.
pick <- function(pool, ...) {
  stopifnot(length(pool) > 0)
  cand <- pool
  for (load in list(...)) {
    if (length(cand) == 1L) break
    cand <- cand[load[cand] == min(load[cand])]
  }
  if (length(cand) == 1L) cand else sample(cand, 1L)
}

new_load <- function(who = REVIEWERS) setNames(integer(length(who)), who)


## ---------------------------------------------------------------------------
## 1. INITIAL ALLOCATION, stratified by task
## ---------------------------------------------------------------------------
## Each task is allocated on its own load counter, so the mix is even within
## every reviewer as well as overall. Two distinct reviewers per paper, always.
assign_initial <- function(papers, reviewers = REVIEWERS) {
  papers$reviewer_1 <- NA_character_
  papers$reviewer_2 <- NA_character_
  overall <- new_load(reviewers)

  for (tk in sample(unique(papers$task))) {        # stratum order random too
    idx <- sample(which(papers$task == tk))        # random order within the stratum
    tload <- new_load(reviewers)
    for (i in idx) {
      r1 <- pick(reviewers, tload, overall)
      r2 <- pick(setdiff(reviewers, r1), tload, overall)   # <- pool EXCLUDES r1
      papers$reviewer_1[i] <- r1
      papers$reviewer_2[i] <- r2
      tload[c(r1, r2)] <- tload[c(r1, r2)] + 1L
      overall[c(r1, r2)] <- overall[c(r1, r2)] + 1L
    }
  }
  attr(papers, "load") <- overall
  papers
}


## ---------------------------------------------------------------------------
## 2. A REVIEWER WITHDRAWS
## ---------------------------------------------------------------------------
## The replacement may be neither the departing reviewer nor the one already
## reading that paper, so the pool is the other twelve.
## Balances on the task load first and the overall load second, exactly as the
## initial allocation does. Reassigning on overall load alone re-levels the totals
## while quietly skewing the task mix, which on the first run pushed the spread to
## four papers.
## ⚠ ORDER FLIPS AFTER STAGE 1. The initial allocation leads on task load,
## because it is building the strata. Every later stage leads on OVERALL load
## instead. Reassigning only 55 papers cannot disturb a task mix that is already
## level to one paper, but it can easily unbalance the totals: leading on task
## load there let the partner exclusion block the lightest reviewer, and seeds 1
## and 7 came out 59 to 61 where every other seed gave 59 to 60. Totals are what
## reviewers actually feel, so they take precedence once the strata exist.
loads_of <- function(papers, reviewers) {
  ov <- setNames(integer(length(reviewers)), reviewers)
  tk <- lapply(setNames(nm = sort(unique(papers$task))),
               function(x) setNames(integer(length(reviewers)), reviewers))
  for (j in seq_len(nrow(papers))) {
    for (r in c(papers$reviewer_1[j], papers$reviewer_2[j])) {
      if (is.na(r) || !r %in% reviewers) next
      ov[r] <- ov[r] + 1L
      tk[[papers$task[j]]][r] <- tk[[papers$task[j]]][r] + 1L
    }
  }
  list(overall = ov, task = tk)
}

withdraw <- function(papers, who, reviewers = REVIEWERS) {
  remaining <- setdiff(reviewers, who)
  L <- loads_of(papers, reviewers)

  hit <- which(papers$reviewer_1 == who | papers$reviewer_2 == who)
  for (i in sample(hit)) {
    slot    <- if (papers$reviewer_1[i] == who) "reviewer_1" else "reviewer_2"
    partner <- if (slot == "reviewer_1") papers$reviewer_2[i] else papers$reviewer_1[i]
    tk <- papers$task[i]
    repl <- pick(setdiff(remaining, partner), L$overall, L$task[[tk]])  # excludes partner
    papers[[slot]][i] <- repl
    L$overall[repl] <- L$overall[repl] + 1L; L$overall[who] <- L$overall[who] - 1L
    L$task[[tk]][repl] <- L$task[[tk]][repl] + 1L
    L$task[[tk]][who]  <- L$task[[tk]][who]  - 1L
  }
  attr(papers, "n_reassigned") <- length(hit)
  papers
}


## ---------------------------------------------------------------------------
## 3. A LATER BATCH: new papers, and papers left short a review
## ---------------------------------------------------------------------------
## `short` names papers that already have one valid review and need a second
## from somebody else, which is what a recusal or a withdrawn review leaves
## behind. Both kinds are placed on the same load counter so the batch levels
## the cumulative counts rather than tilting them.
add_batch <- function(papers, new_papers, short_pmids, reviewers = REVIEWERS) {
  active <- setdiff(reviewers, WITHDREW)
  if (nrow(new_papers)) papers <- rbind(papers, new_papers[, names(papers)])
  L <- loads_of(papers, active)
  bump <- function(r, tk) { L$overall[r] <<- L$overall[r] + 1L
                            L$task[[tk]][r] <<- L$task[[tk]][r] + 1L }

  for (i in sample(which(is.na(papers$reviewer_1)))) {
    tk <- papers$task[i]
    r1 <- pick(active, L$overall, L$task[[tk]])
    r2 <- pick(setdiff(active, r1), L$overall, L$task[[tk]])
    papers$reviewer_1[i] <- r1; papers$reviewer_2[i] <- r2
    bump(r1, tk); bump(r2, tk)
  }

  ## ⚠ The outgoing reviewer must be DEBITED, not just the incoming one credited.
  ## A short paper is one whose second reviewer never delivered, so that slot
  ## leaves them and lands on somebody else. Crediting alone inflates the totals
  ## and, worse, hides who now has capacity: on the first run it drove the final
  ## spread to 58-61 when stage 2 had ended level at 59-60.
  for (p in sample(short_pmids)) {
    i <- which(papers$PMID == p)
    if (length(i) != 1L) next
    tk   <- papers$task[i]
    keep <- papers$reviewer_1[i]                              # the review that stands
    out  <- papers$reviewer_2[i]                              # the one that never came
    if (!is.na(out) && out %in% active) {
      L$overall[out] <- L$overall[out] - 1L
      L$task[[tk]][out] <- L$task[[tk]][out] - 1L
    }
    repl <- pick(setdiff(active, keep), L$overall, L$task[[tk]])  # never the same person
    papers$reviewer_2[i] <- repl
    bump(repl, tk)
  }
  papers
}


## ---------------------------------------------------------------------------
## 4. THE CHECKS
## ---------------------------------------------------------------------------
## Each of these corresponds to something that actually went wrong. They stop the
## script rather than warn, because an allocation with any of these faults should
## never be handed out.
## `tol_load` / `tol_task` are the widest acceptable spread. They are 0 for the
## initial allocation, where 770 slots divide evenly and every reviewer must carry
## exactly the same. They loosen for the later batch because 10 extra slots cannot
## be shared evenly among 13 people: demanding 0 there would fail on arithmetic,
## not on a defect, and a check that cannot pass teaches nobody anything.
check <- function(papers, lists, label, tol_load = 0L, tol_task = 0L) {
  cat(sprintf("\n%s\n%s\n", label, strrep("-", nchar(label))))
  fail <- character(0)
  ck <- function(name, ok, detail = "") {
    cat(sprintf("  %-52s %s %s\n", name, if (ok) "ok  " else "FAIL", detail))
    if (!ok) fail <<- c(fail, name)
  }

  ck("every paper has two reviewers",
     !any(is.na(papers$reviewer_1) | is.na(papers$reviewer_2)))
  ck("no paper allocated to one reviewer twice",
     !any(papers$reviewer_1 == papers$reviewer_2),
     sprintf("%d violations", sum(papers$reviewer_1 == papers$reviewer_2)))
  ck("no duplicate PMID in the allocation",
     !anyDuplicated(papers$PMID))
  held <- sum(c(papers$reviewer_1, papers$reviewer_2) == WITHDREW)
  if (tol_load == 0L) {
    cat(sprintf("  %-52s %s %s
", "(withdrawn reviewer still active at this stage)", "--  ",
                sprintf("%d papers", held)))
  } else {
    ck("the withdrawn reviewer holds nothing", held == 0, sprintf("%d", held))
  }

  ld <- table(c(papers$reviewer_1, papers$reviewer_2))
  ck(sprintf("loads level to within %d", tol_load), max(ld) - min(ld) <= tol_load,
     sprintf("%d to %d across %d reviewers", min(ld), max(ld), length(ld)))

  tb <- table(c(papers$reviewer_1, papers$reviewer_2),
              rep(papers$task, 2))
  sp <- apply(tb, 2, function(x) max(x) - min(x))
  ck(sprintf("task mix level to within %d", tol_task), all(sp <= tol_task),
     paste(sprintf("%s %d", names(sp), sp), collapse = " | "))

  dup <- sum(vapply(lists, function(d) sum(duplicated(d$PMID)), integer(1)))
  ck("no reviewer's list contains a paper twice", dup == 0,
     sprintf("%d duplicated rows", dup))
  ck("reviewer names are not truncated",
     all(nchar(names(ld)) == nchar(REVIEWERS[match(names(ld), REVIEWERS)])))

  if (length(fail)) stop("allocation failed: ", paste(fail, collapse = "; "))
  invisible(TRUE)
}

## Per-reviewer lists derived from the allocation, never assembled by hand. This
## is the step where a paper previously got onto one list twice.
make_lists <- function(papers) {
  who <- sort(unique(c(papers$reviewer_1, papers$reviewer_2)))
  setNames(lapply(who, function(r) {
    d <- papers[papers$reviewer_1 == r | papers$reviewer_2 == r, ]
    d$role <- ifelse(d$reviewer_1 == r, "first", "second")
    d[order(d$task, d$PMID), c("PMID", "Title", "task", "role")]
  }), who)
}


## ---------------------------------------------------------------------------
## 5. RUN
## ---------------------------------------------------------------------------
read_papers <- function() {
  src <- file.path(PROJ, "data", "assignment")
  grab <- function(p) {
    d <- as.data.frame(read_excel(file.path(src, p), col_types = "text"),
                       check.names = FALSE)
    tk <- if ("Modified study type" %in% names(d)) d[["Modified study type"]]
          else d[["Study Type"]]
    data.frame(PMID  = sub("[.]0$", "", trimws(d$PMID)),
               Title = d$Title,
               task  = trimws(tk),
               stringsAsFactors = FALSE)
  }
  p <- rbind(grab("Ready for data extraction with titles_adjudicated.xlsx"),
             grab("Ready for data extraction with titles round 2.xlsx"))
  p <- p[!is.na(p$PMID) & p$PMID != "" & !duplicated(p$PMID), ]
  p$task[!p$task %in% c("Causal", "Descriptive", "Predictive")] <- "Descriptive"
  p
}

cat(sprintf("CLEAN ASSIGNMENT, seed %d\n%s\n", SEED, strrep("=", 78)))
set.seed(SEED)

papers <- read_papers()
cat(sprintf("papers: %d  (%s)\n", nrow(papers),
            paste(sprintf("%s %d", names(table(papers$task)), table(papers$task)),
                  collapse = ", ")))

## Stage 1: all fourteen reviewers
a1 <- assign_initial(papers)
ld <- table(c(a1$reviewer_1, a1$reviewer_2))
cat(sprintf("\nstage 1, fourteen reviewers: loads %d to %d, self-pairings %d\n",
            min(ld), max(ld), sum(a1$reviewer_1 == a1$reviewer_2)))

## Stage 2: reviewer 3 withdraws, papers go to the other twelve per paper
a2 <- withdraw(a1, WITHDREW)
ld <- table(c(a2$reviewer_1, a2$reviewer_2))
cat(sprintf("stage 2, %s withdrew: %d papers reassigned, loads %d to %d, self-pairings %d\n",
            WITHDREW, attr(a2, "n_reassigned"), min(ld), max(ld),
            sum(a2$reviewer_1 == a2$reviewer_2)))

## Stage 3: the later batch. Three papers replaced ones removed after review;
## the short list is every paper left with one valid review, whether through a
## recusal or a withdrawn one.
NEW_PMIDS   <- c("STUDY-0658", "STUDY-0401", "STUDY-0161")
SHORT_PMIDS <- c("STUDY-0905", "STUDY-0449", "STUDY-0473", "STUDY-0183")
new_rows <- data.frame(PMID = NEW_PMIDS,
                       Title = paste("replacement paper", NEW_PMIDS),
                       task = "Descriptive",
                       stringsAsFactors = FALSE)
new_rows$reviewer_1 <- NA_character_
new_rows$reviewer_2 <- NA_character_
new_rows <- new_rows[!new_rows$PMID %in% a2$PMID, ]
a3 <- add_batch(a2, new_rows, intersect(SHORT_PMIDS, a2$PMID))
ld <- table(c(a3$reviewer_1, a3$reviewer_2))
cat(sprintf("stage 3, later batch: %d papers now, loads %d to %d, self-pairings %d\n",
            nrow(a3), min(ld), max(ld), sum(a3$reviewer_1 == a3$reviewer_2)))

## Strict on the initial allocation: it must be exactly level.
## tol_task is 1, not 0, and that is the floor rather than a concession: 228
## causal papers over 14 reviewers is 32.57 each, so some carry 32 and some 33
## whatever the algorithm does. Demanding 0 fails on arithmetic. The load itself
## IS exactly level, because 770 slots over 14 divides.
check(a1, make_lists(a1), "CHECKS after stage 1, strict", tol_load = 0L, tol_task = 1L)

lists <- make_lists(a3)
check(a3, lists, "CHECKS after stage 3 (each is a fault that actually occurred)",
      tol_load = 1L, tol_task = 2L)

cat("\nper-reviewer load and task mix\n")
tb <- table(c(a3$reviewer_1, a3$reviewer_2), rep(a3$task, 2))
for (r in rownames(tb))
  cat(sprintf("  %-10s %3d  |  %s\n", r, sum(tb[r, ]),
              paste(sprintf("%s %2d", colnames(tb), tb[r, ]), collapse = "  ")))
cat(sprintf("\ndistinct reviewer pairs used: %d of %d possible\n",
            length(unique(apply(a3[, c("reviewer_1", "reviewer_2")], 1,
                                function(x) paste(sort(x), collapse = "|")))),
            choose(length(setdiff(REVIEWERS, WITHDREW)), 2)))

if (DO_WRITE) {
  dir.create(OUT, showWarnings = FALSE, recursive = TRUE)
  writexl::write_xlsx(a3, file.path(OUT, sprintf("allocation_seed%d.xlsx", SEED)))
  writexl::write_xlsx(lists, file.path(OUT, sprintf("reviewer_lists_seed%d.xlsx", SEED)))
  cat(sprintf("\nwritten -> %s\n", sub(PROJ, "", OUT, fixed = TRUE)))
} else {
  cat("\n(nothing written; pass --write to save)\n")
}

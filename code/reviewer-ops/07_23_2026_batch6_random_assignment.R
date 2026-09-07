# NOTE (public repository): 7 hard-coded study identifier(s) were
# rewritten to de-identified surrogates by tools/build_public_repo.py.
# They are rulings about particular studies rather than values the data
# can supply, so they have to travel with it.
###############################################################################
##  Batch 6 -- reproducible random assignment of 8 papers to the 13 reviewers
##  Project: Assessment of Healthcare Research Quality in Saudi Arabia
##  Date   : 2026-07-23
##
##  WHAT THIS DOES
##  --------------
##  Hands out 11 reviews across 8 papers to the 13 active reviewers:
##    * 3 NEWLY INCLUDED papers  -> 2 reviewers each          (6 reviews)
##    * 5 papers whose 2nd review was never completed, because the reviewer
##      recused or because the PI assigned the paper twice to the same person
##      -> 1 NEW reviewer each, different from the one who reviewed it (5 reviews)
##
##  The draw is RANDOM but CONSTRAINED, so that after this batch each reviewer's
##  cumulative review count -- overall, and separately within Descriptive /
##  Predictive / Causal -- is as equal as the arithmetic allows.
##
##  Everything is read from disk; no assignment fact is hand-entered.  Re-running
##  with the same SEED reproduces the identical assignment, bit for bit.
###############################################################################

suppressPackageStartupMessages({ library(readxl); library(openxlsx) })

## ---------------------------------------------------------------------------
## 0.  PARAMETERS  (the only knobs)
## ---------------------------------------------------------------------------
SEED             <- 20260723    # today's date; fixed + documented => reproducible
N_DRAWS          <- 20000L      # constrained-random restarts used to find optima
BASELINE         <- "completed" # "completed" = reviews actually submitted (default)
                                # "assigned"  = papers on the books per the Word doc
MAX_PER_REVIEWER <- Inf         # Inf = a reviewer may take >1 paper this batch when
                                #       that is what equalises the cumulative counts
                                # 1   = cap this batch at one paper per reviewer
WRITE_OUTPUT     <- TRUE        # FALSE = report only, touch no files

PROJ  <- "."
STAMP <- "07_23_2026"

## RNG pinned explicitly so the draw is stable across R versions and platforms
set.seed(SEED, kind = "Mersenne-Twister", normal.kind = "Inversion",
         sample.kind = "Rejection")

## ---------------------------------------------------------------------------
## 1.  REVIEWER ROSTER  --  reviewers are identified by NUMBER throughout
##     The project recruited 14 reviewers, numbered 1-14.  Reviewer 3 (R-withdrawn bin
##     Hammad) quit ("Out of the project", private/reviewers/Progress of Reviewers for batch 5.docx);
##     his 3 pilot reviews were redone by others and his 55 papers redistributed.
##     THE REMAINING NUMBERS DID NOT CHANGE -- the 13 active reviewers are
##     1,2,4,5,6,7,8,9,10,11,12,13,14, i.e. there is a permanent gap at 3 and the
##     highest number is 14, not 13.  Never renumber; never assume ID == row.
##     The ID -> name map is verified against the data in section 2c.
## ---------------------------------------------------------------------------
roster <- data.frame(
  rid  = c(1, 2, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14),
  name = c("R1", "R2", "R3", "R4", "R5", "R6", "R7",
           "R8", "R9", "R10", "R11", "R12", "R13"),
  full = c("R1 Alkharashi", "R2 Aldakhil", "R3 Eldaalooj",
           "R4 Alessi/R14 Almeshal", "R5 Aljaafr/R15 Samrgandi",
           "R6 Alnasser", "R7 Aldosari", "R8 Alsugair", "R9 Asiri",
           "R10 Alattas", "R11 Gazzaz", "R12 Merdad", "R13 Aburass"),
  stringsAsFactors = FALSE)
NR    <- nrow(roster)
TASKS <- c("Descriptive", "Predictive", "Causal")
stopifnot(identical(roster$rid, c(1,2,4,5,6,7,8,9,10,11,12,13,14)),   # gap at 3
          NR == 13L, !anyDuplicated(roster$name))

## Internals key on the short name (that is what the strat files hold); every
## OUTPUT is emitted as the reviewer NUMBER via these two helpers.
rid_of  <- function(nm) roster$rid[match(nm, roster$name)]
num_str <- function(nm) if (!length(nm)) NA_character_ else
                        paste(sort(rid_of(nm)), collapse = "; ")

## ---------------------------------------------------------------------------
## 2.  READ THE SOURCE DATA
## ---------------------------------------------------------------------------
## 2a. Master paper -> reviewer assignment of the 385 included papers
fixnm <- function(x) { x[x == "Alhan"] <- "R13"; x[x == "Musfe"] <- "R7"; x }
asg <- rbind(
  as.data.frame(read_excel(file.path(PROJ, "private/reviewers/papers_assignment_strat.xlsx"),
                           sheet = "assignment", col_types = "text")),
  as.data.frame(read_excel(file.path(PROJ, "private/reviewers/papers_assignment_strat_2.xlsx"),
                           sheet = "assignment", col_types = "text")))
asg$reviewer_1 <- fixnm(asg$reviewer_1); asg$reviewer_2 <- fixnm(asg$reviewer_2)
stopifnot(nrow(asg) == 385L, !anyDuplicated(asg$PMID))

## 2b. Every review actually submitted, from the 14 Google-Forms exports
rfiles <- list.files(PROJ, pattern = "^(04_15_2026|05_19_2025)_Reviewer_[0-9]+\\.xlsx$")
subs <- do.call(rbind, lapply(rfiles, function(fn) {
  d <- suppressMessages(read_excel(file.path(PROJ, fn), col_types = "text"))
  data.frame(rid    = as.integer(sub(".*_Reviewer_([0-9]+)\\.xlsx$", "\\1", fn)),
             PMID   = d[[2]],   # "What was the PMID of the research paper?"
             recuse = d[[3]],   # "Do you wish to recuse yourself ...?"
             stringsAsFactors = FALSE) }))

## KNOWN DATA FIX -- R6 (rid 7) typed the study task into the PMID field on one
## row.  That row is her review of PMID STUDY-0473 (Descriptive; strat pair =
## R6 + R13, and R13's review of it exists).  Without this fix
## STUDY-0473 looks like a 6th single-review paper, which it is not.
fix_i <- which(subs$rid == 7L & subs$PMID == "Descriptive")
stopifnot(length(fix_i) == 1L); subs$PMID[fix_i] <- "STUDY-0473"

recused  <- subs[!grepl("^No, I do not wish", subs$recuse), ]
reviewed <- unique(subs[grepl("^No, I do not wish", subs$recuse), c("rid", "PMID")])
stopifnot(all(reviewed$PMID %in% asg$PMID))

## Papers left with only ONE completed review.  Note PMID STUDY-0183: R2 recused
## from it but it was re-covered by another reviewer, so it is NOT short a review
## and her slot no longer sits with her -- that is why the recusal adjustment in
## section 3 is restricted to papers that are genuinely still short.
n_distinct <- tapply(reviewed$rid, reviewed$PMID, function(x) length(unique(x)))
single <- names(n_distinct)[n_distinct == 1L]

## 2c. Verify the reviewer-ID -> name map by PMID overlap with the strat files
chk <- sapply(roster$name, function(nm) {
  p <- asg$PMID[asg$reviewer_1 == nm | asg$reviewer_2 == nm]
  sapply(roster$rid, function(r) sum(reviewed$PMID[reviewed$rid == r] %in% p)) })
stopifnot(identical(roster$name[apply(chk, 1, which.max)], roster$name),
          all(apply(chk, 1, max) >= 50))
cat("[check] reviewer ID -> name map verified by PMID overlap (min diagonal =",
    min(apply(chk, 1, max)), "of 55)\n")

## ---------------------------------------------------------------------------
## 3.  BASELINE LOAD PER REVIEWER, BY STUDY TASK
## ---------------------------------------------------------------------------
rev_typed <- merge(merge(reviewed, asg[, c("PMID", "Study_Type")], by = "PMID"),
                   roster[, c("rid", "name")], by = "rid")
completed <- matrix(0L, NR, 3, dimnames = list(roster$name, TASKS))
tb <- table(rev_typed$name, rev_typed$Study_Type)
completed[rownames(tb), colnames(tb)] <- as.integer(tb)

## "assigned" = what the Word doc counts: completed, plus reviews that were on
## the books but never delivered (a recusal, or the 2nd slot of the double
## assignment of PMID STUDY-0449 to R6, who was already its other reviewer).
assigned <- completed
rec_open <- recused[recused$PMID %in% single, ]      # recusals never re-covered
for (i in seq_len(nrow(rec_open))) {
  nm <- roster$name[roster$rid == rec_open$rid[i]]
  ty <- asg$Study_Type[asg$PMID == rec_open$PMID[i]]
  if (length(nm) && length(ty)) assigned[nm, ty] <- assigned[nm, ty] + 1L }
ty44 <- asg$Study_Type[asg$PMID == "STUDY-0449"]
assigned["R6", ty44] <- assigned["R6", ty44] + 1L

## Cross-check against Table 1 of "private/reviewers/Paper assignment to reviewers.docx".  Its 13
## rows are in reviewer-ID order 1,2,4,5,6,7,8,9,10,11,12,13,14 -- confirmed by
## this check reproducing all 39 cells and all three column totals.
docx_tab <- matrix(c(13L,11L,36L, 13L,11L,35L, 13L,12L,35L, 14L,10L,35L,
                     12L,12L,35L, 13L,13L,34L, 13L,12L,34L, 13L,12L,34L,
                     13L,11L,35L, 13L,11L,35L, 12L,11L,36L, 12L,11L,36L,
                     12L,11L,36L), nrow = NR, byrow = TRUE,
                   dimnames = list(roster$name, TASKS))
stopifnot(identical(assigned[, TASKS], docx_tab[, TASKS]),
          identical(as.integer(colSums(docx_tab)), c(166L, 148L, 456L)),
          sum(docx_tab) == 770L)
cat("[check] derived 'assigned' load reproduces Table 1 of the Word doc exactly",
    "(770 reviews: 166 D / 148 P / 456 C)\n")

base_mat <- if (BASELINE == "completed") completed else assigned
cat("\n--- baseline (", BASELINE, ") reviews per reviewer ---\n", sep = "")
print(data.frame(Reviewer_No = roster$rid, Name = roster$name, base_mat,
                 Total = rowSums(base_mat), row.names = NULL), right = FALSE)

## ---------------------------------------------------------------------------
## 4.  THE 8 PAPERS TO ASSIGN
## ---------------------------------------------------------------------------
## 4a. The 3 newly INCLUDED papers = the first three Status=="Include" rows of the
##     TA/YA-finalised pool file (the only rows whose adjudicated exposure/outcome
##     cells TA and YA edited and highlighted).  Study task is read from the file.
pool <- as.data.frame(read_excel(file.path(PROJ,
  "data/screening/incl or excl of pool of papers to include 3 more papers_YA_TA.xlsx"),
  col_types = "text"))
new3 <- head(pool[pool$Status == "Include", ], 3L)
stopifnot(nrow(new3) == 3L,
          identical(new3$PMID, c("STUDY-0401", "STUDY-0658", "STUDY-0161")))
new3 <- data.frame(PMID = new3$PMID, title = new3$Title, link = new3$link,
                   Study_Type = new3$`Study Type`,
                   adjudicated_exposure = new3$Adjudicated_exposure,
                   adjudicated_outcome  = new3$Adjudicated_outcome,
                   n_reviewers = 2L, reason = "Newly included paper",
                   stringsAsFactors = FALSE)

## 4b. Papers left with only ONE completed review (`single`, derived in step 2b)
cat("\n[derived] papers with only one completed review:",
    paste(sort(single), collapse = ", "), "\n")
## Keep the ones caused by a recusal or by the double assignment.  STUDY-0905 is
## NOT in scope: its 2nd reviewer simply never submitted, which is neither of the
## two causes the PI listed for this batch.
redo_ids <- sort(intersect(single, c(recused$PMID, "STUDY-0449")))
stopifnot(length(redo_ids) == 5L)
redo <- asg[match(redo_ids, asg$PMID), c("PMID", "Title", "link", "Study_Type",
                                         "adjudicated_exposure", "adjudicated_outcome")]
names(redo)[2] <- "title"; redo$n_reviewers <- 1L
redo$reason <- vapply(redo$PMID, function(p) if (p %in% recused$PMID)
  "2nd reviewer recused" else "Double assignment to the same reviewer", character(1))

papers <- rbind(new3, redo)
papers$Study_Type <- factor(papers$Study_Type, levels = TASKS)
stopifnot(!is.na(papers$Study_Type))

## ---------------------------------------------------------------------------
## 5.  ELIGIBILITY -- a reviewer is barred from a paper they already reviewed,
##     and from one they already recused from (they would only recuse again).
## ---------------------------------------------------------------------------
barred <- lapply(papers$PMID, function(p)
  roster$name[roster$rid %in% c(reviewed$rid[reviewed$PMID == p],
                                recused$rid[recused$PMID  == p])])
names(barred) <- papers$PMID
cat("\n--- eligibility exclusions (reviewer numbers) ---\n")
for (i in seq_len(nrow(papers)))
  cat(sprintf("  %s (%-11s) barred: %s\n", papers$PMID[i], papers$Study_Type[i],
      if (length(barred[[i]])) num_str(barred[[i]]) else "(none)"))

## ---------------------------------------------------------------------------
## 6.  SLOTS = one row per review to be handed out
## ---------------------------------------------------------------------------
slots <- do.call(rbind, lapply(seq_len(nrow(papers)), function(i)
  data.frame(PMID = papers$PMID[i], task = as.character(papers$Study_Type[i]),
             rep = seq_len(papers$n_reviewers[i]), stringsAsFactors = FALSE)))
NS <- nrow(slots)
cat("\n[slots]", NS, "reviews to assign:", paste(sprintf("%d %s",
    table(factor(slots$task, TASKS)), TASKS), collapse = ", "), "\n")

## ---------------------------------------------------------------------------
## 7.  BALANCE CRITERION
##     Equalising counts that sum to a fixed total == minimising the sum of their
##     squares.  The four criteria the PI asked for are weighted equally: overall
##     load, and each of the three study tasks.
## ---------------------------------------------------------------------------
cost_of <- function(add) { fin <- base_mat + add
  sum(fin[, "Descriptive"]^2) + sum(fin[, "Predictive"]^2) +
  sum(fin[, "Causal"]^2)      + sum(rowSums(fin)^2) }
## Lower bound: minimise each criterion on its own by water-filling (always give
## the next review to whoever currently has the fewest).  A solution attaining
## this bound is provably optimal for the joint criterion.
wf <- function(x, k) { for (i in seq_len(k)) { j <- which.min(x); x[j] <- x[j] + 1L }
                       sum(x^2) }
LB <- wf(base_mat[, "Descriptive"], sum(slots$task == "Descriptive")) +
      wf(base_mat[, "Predictive"],  sum(slots$task == "Predictive"))  +
      wf(base_mat[, "Causal"],      sum(slots$task == "Causal"))      +
      wf(rowSums(base_mat), NS)

## ---------------------------------------------------------------------------
## 8.  CONSTRAINED RANDOM DRAW
##     Each draw: shuffle the slots, then give each slot to a reviewer picked
##     UNIFORMLY AT RANDOM among the eligible reviewers who are currently most
##     under-loaded (fewest reviews of that task; ties broken on overall load;
##     remaining ties broken at random).  Repeating with a fresh shuffle explores
##     the space of balanced assignments; we keep every draw attaining the best
##     cost and then pick one of those uniformly at random.
## ---------------------------------------------------------------------------
draw_one <- function() {
  add  <- matrix(0L, NR, 3, dimnames = list(roster$name, TASKS))
  used <- setNames(integer(NR), roster$name)
  who  <- character(NS); taken <- setNames(vector("list", nrow(papers)), papers$PMID)
  for (s in sample.int(NS)) {
    p <- slots$PMID[s]; ty <- slots$task[s]
    ok <- setdiff(roster$name, c(barred[[p]], taken[[p]]))
    ok <- ok[used[ok] < MAX_PER_REVIEWER]
    if (!length(ok)) return(NULL)
    tc   <- base_mat[ok, ty] + add[ok, ty];  cand <- ok[tc == min(tc)]
    tt   <- rowSums(base_mat[cand, , drop = FALSE]) + rowSums(add[cand, , drop = FALSE])
    cand <- cand[tt == min(tt)]
    pick <- if (length(cand) == 1L) cand else sample(cand, 1L)
    who[s] <- pick; add[pick, ty] <- add[pick, ty] + 1L; used[pick] <- used[pick] + 1L
    taken[[p]] <- c(taken[[p]], pick) }
  list(who = who, add = add, cost = cost_of(add)) }

best <- Inf; sols <- list()
for (d in seq_len(N_DRAWS)) {
  r <- draw_one(); if (is.null(r)) next
  if (r$cost < best) { best <- r$cost; sols <- list() }
  if (r$cost == best) { k <- paste(r$who, collapse = "|")
                        if (is.null(sols[[k]])) sols[[k]] <- r } }
cat(sprintf("\n[search] %d draws | best cost = %d | lower bound = %d | %s | %d distinct optimal assignments\n",
    N_DRAWS, best, LB, if (best == LB) "PROVABLY OPTIMAL" else "optimum NOT proven",
    length(sols)))
sol <- sols[[ sample.int(length(sols), 1L) ]]     # uniform pick among the optima
slots$reviewer <- sol$who

## ---------------------------------------------------------------------------
## 9.  RESULT + VERIFICATION
## ---------------------------------------------------------------------------
after <- base_mat + sol$add
nm_of <- function(nm) if (!length(nm)) NA_character_ else paste(sort(nm), collapse = "; ")
res <- data.frame(
  PMID = papers$PMID, title = papers$title, link = papers$link,
  Study_Type = as.character(papers$Study_Type),
  adjudicated_exposure = papers$adjudicated_exposure,
  adjudicated_outcome  = papers$adjudicated_outcome,
  ## REVIEWER NUMBERS (see the reviewer_key sheet / private/reviewers/07_23_2026_reviewer_key.csv)
  `Assigned reviewer` = vapply(papers$PMID, function(p)
    num_str(slots$reviewer[slots$PMID == p]), character(1)),
  assigned_reviewer_names = vapply(papers$PMID, function(p)
    nm_of(slots$reviewer[slots$PMID == p]), character(1)),
  n_reviewers = papers$n_reviewers, reason = papers$reason,
  previously_reviewed_by_no = vapply(papers$PMID, function(p)
    num_str(roster$name[roster$rid %in% reviewed$rid[reviewed$PMID == p]]), character(1)),
  recused_from_it_no = vapply(papers$PMID, function(p)
    num_str(roster$name[roster$rid %in% recused$rid[recused$PMID == p]]), character(1)),
  check.names = FALSE, stringsAsFactors = FALSE, row.names = NULL)

stopifnot(
  nrow(res) == 8L, sum(papers$n_reviewers) == NS,
  ## nobody gets a paper they already reviewed or recused from
  all(vapply(seq_len(NS), function(i)
    !(slots$reviewer[i] %in% barred[[slots$PMID[i]]]), logical(1))),
  ## the two reviewers of each new paper are different people
  all(vapply(papers$PMID[papers$n_reviewers == 2L], function(p)
    length(unique(slots$reviewer[slots$PMID == p])) == 2L, logical(1))),
  all(slots$reviewer %in% roster$name))
cat("[check] all eligibility and distinctness constraints satisfied\n")

cat("\n=====================  BATCH 6 ASSIGNMENT (reviewer numbers)  ==============\n")
print(res[, c("PMID", "Study_Type", "n_reviewers", "Assigned reviewer",
              "previously_reviewed_by_no", "recused_from_it_no", "reason")],
      right = FALSE)

cat("\n----- REVIEWER KEY (14 numbers issued; 3 retired, numbers never reused) ----\n")
key <- data.frame(Reviewer_No = c(roster$rid, 3), Name = c(roster$full, "R-withdrawn bin Hammad"),
                  Short = c(roster$name, "R-withdrawn"),
                  Status = c(rep("Active", NR), "Quit - out of the project"),
                  row.names = NULL)
key <- key[order(key$Reviewer_No), ]
print(key, right = FALSE, row.names = FALSE)

bal <- data.frame(Reviewer_No = roster$rid, Name = roster$name,
                  before = rowSums(base_mat), new = rowSums(sol$add),
                  after = rowSums(after), D = after[, "Descriptive"],
                  P = after[, "Predictive"], C = after[, "Causal"], row.names = NULL)
cat("\n----- cumulative reviews per reviewer AFTER batch 6 (baseline =",
    BASELINE, ") -----\n"); print(bal, right = FALSE)
cat("\nspread after batch 6 --  total:", paste(range(bal$after), collapse = "-"),
    "| Descriptive:", paste(range(bal$D), collapse = "-"),
    "| Predictive:",  paste(range(bal$P), collapse = "-"),
    "| Causal:",      paste(range(bal$C), collapse = "-"), "\n")

## ---------------------------------------------------------------------------
## 10.  WRITE "private/reviewers/batch-6-distribution/Batch 6.xlsx" (headers/formatting preserved) + an audit workbook
## ---------------------------------------------------------------------------
if (WRITE_OUTPUT) {
  b6 <- file.path(PROJ, "private/reviewers/batch-6-distribution/Batch 6.xlsx"); wb <- loadWorkbook(b6); sh <- names(wb)[1]
  hdr <- as.character(read.xlsx(b6, sheet = sh, colNames = FALSE, rows = 1))
  stopifnot(identical(hdr, c("PMID", "title", "link", "Study_Type",
                             "adjudicated_exposure", "adjudicated_outcome",
                             "Assigned reviewer")))
  writeData(wb, sh, res[, hdr], startRow = 2, colNames = FALSE)
  setColWidths(wb, sh, cols = 1:7, widths = c(11, 70, 45, 12, 34, 34, 20))
  saveWorkbook(wb, b6, overwrite = TRUE)
  cat("\n[written]", b6, "-- 8 rows\n")

  write.csv(key, file.path(PROJ, paste0(STAMP, "_reviewer_key.csv")),
            row.names = FALSE, fileEncoding = "UTF-8")
  cat("[written]", file.path(PROJ, paste0(STAMP, "_reviewer_key.csv")), "\n")

  aud <- createWorkbook()
  addWorksheet(aud, "reviewer_key");        writeData(aud, "reviewer_key", key)
  addWorksheet(aud, "assignment");          writeData(aud, "assignment", res)
  addWorksheet(aud, "one_row_per_review")
  opr <- merge(slots, papers[, c("PMID", "title", "reason")], by = "PMID")
  opr <- data.frame(PMID = opr$PMID, task = opr$task, rep = opr$rep,
                    Reviewer_No = rid_of(opr$reviewer), Name = opr$reviewer,
                    title = opr$title, reason = opr$reason)
  writeData(aud, "one_row_per_review", opr[order(opr$PMID, opr$rep), ])
  addWorksheet(aud, "balance_after");       writeData(aud, "balance_after", bal)
  addWorksheet(aud, "baseline_completed")
  writeData(aud, "baseline_completed",
            data.frame(Reviewer_No = roster$rid, Name = roster$name, completed,
                       Total = rowSums(completed), row.names = NULL))
  addWorksheet(aud, "baseline_assigned")
  writeData(aud, "baseline_assigned",
            data.frame(Reviewer_No = roster$rid, Name = roster$name, assigned,
                       Total = rowSums(assigned), row.names = NULL))
  addWorksheet(aud, "provenance")
  writeData(aud, "provenance", data.frame(item = c("seed", "baseline",
    "max papers per reviewer this batch", "draws", "best cost", "lower bound",
    "optimality", "distinct optimal assignments", "R version", "script"),
    value = c(SEED, BASELINE, as.character(MAX_PER_REVIEWER), N_DRAWS, best, LB,
              if (best == LB) "provably optimal" else "best found", length(sols),
              R.version.string, "code/reviewer-ops/07_23_2026_batch6_random_assignment.R")))
  saveWorkbook(aud, file.path(PROJ, paste0(STAMP, "_batch6_assignment_audit.xlsx")),
               overwrite = TRUE)
  cat("[written]", file.path(PROJ, paste0(STAMP, "_batch6_assignment_audit.xlsx")), "\n")
}

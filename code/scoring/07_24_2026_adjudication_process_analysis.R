# NOTE (public repository): 3 hard-coded study identifier(s) were
# rewritten to de-identified surrogates by tools/build_public_repo.py.
# They are rulings about particular studies rather than values the data
# can supply, so they have to travel with it.
###############################################################################
##  The reviewer-disagreement and two-phase adjudication process, quantified
##  Project: Assessment of Healthcare Research Quality in Saudi Arabia
##  Date   : 2026-07-24     N = 377 included papers x 47 tool items = 17,719 cells
##
##  WHAT IT MEASURES
##   1. how often the two independent reviewers disagreed  (overall / task / item / task x item)
##   2. how many cells therefore needed adjudication        (overall / paper / task / item)
##   3. PHASE I  - TA and YA adjudicating independently, and how often they concurred
##   4. PHASE II - the joint pass over the cells where phase I disagreed
##   5. whether the final call reproduced one of the reviewers' answers or overrode both
##
##  The adjudicators were blinded to reviewer IDENTITY but saw both ANSWERS, and did
##  not know which reviewer was assigned to which paper.  Because "first" vs "second"
##  reviewer is an arbitrary column position, a final call that lands on the first
##  reviewer as often as on the second is evidence that no positional cue leaked
##  through -- reported here as the position-neutrality check.
###############################################################################

suppressPackageStartupMessages({ library(readxl) })

PROJ  <- "."
STAMP <- "07_24_2026"
OUT   <- file.path(PROJ, "data/adjudication/process-tables")
if (!dir.exists(OUT)) dir.create(OUT)

EXCL  <- c('STUDY-0136','STUDY-0478',                              # no Saudi affiliation
           'STUDY-0956')                                         # YA co-authored (COI)
## (2026-08-08) the 5 batch-6 re-review papers + 3 new are now fully adjudicated and INCLUDED -> 385.
HOUSE <- c('Reviewer_ID','Timestamp','comments','comments_focus')
TASKS <- c("Descriptive","Predictive","Causal")

## ---------------------------------------------------------------------------
## Normalisation -- byte-for-byte the rule the build script uses:
## casefold, collapse whitespace, sort the parts of a ";"-multiselect.
## sort(method="radix") reproduces Python's byte-order sort; R's default locale
## collation would order differently and silently change the comparison.
## ---------------------------------------------------------------------------
norm1 <- function(v) {
  s <- ifelse(is.na(v), "", as.character(v))
  s <- gsub("\\s+", " ", trimws(tolower(s)))
  s[s == "nan"] <- ""
  ix <- grepl(";", s, fixed = TRUE)
  if (any(ix)) s[ix] <- vapply(s[ix], function(z) {
    p <- trimws(strsplit(z, ";", fixed = TRUE)[[1]]); p <- p[nzchar(p)]
    paste(sort(p, method = "radix"), collapse = ";") }, character(1))
  s
}
## "skipped" / "should be skipped" are the tool's way of writing NOT APPLICABLE,
## so for comparing a final call against a reviewer they must equal a blank.
NAV <- c("skipped", "should be skipped")
normNA <- function(v) { s <- norm1(v); s[s %in% NAV] <- ""; s }
isbl   <- function(s) s == ""

rd <- function(f, sheet = 1)
  as.data.frame(suppressMessages(read_excel(file.path(PROJ, f), sheet = sheet, col_types = "text")))

## ---------------------------------------------------------------------------
## 1.  Assemble one row per (PMID, item) cell for the 377 papers
## ---------------------------------------------------------------------------
ag <- rd("private/reviewers/adjudication-worklists/08_08_2026_do_not_Need_adj_385.xlsx")
ta <- rd("private/reviewers/adjudication-worklists/08_08_2026_Needs_adj_progress_TA_385.xlsx")
ya <- rd("private/reviewers/adjudication-worklists/08_08_2026_Needs_adj_progress_YA_385.xlsx")
ph <- rd("private/reviewers/adjudication-worklists/08_08_2026_TA_YA_Differed_phase_II_385.xlsx")
L  <- read.csv(file.path(PROJ, "data/analysis/07_23_2026_ANALYSIS_DATASET_long.csv"), colClasses = "character")

keep <- function(d) d[!(d$PMID %in% EXCL) & !(d$variable %in% HOUSE), ]
ag <- keep(ag); ta <- keep(ta); ya <- keep(ya); ph <- keep(ph)
stopifnot(identical(paste(ta$PMID, ta$variable), paste(ya$PMID, ya$variable)))
## the two worklists must carry the same reviewer answers; compare normalised
stopifnot(all(norm1(ta$first_reviewer)  == norm1(ya$first_reviewer)),
          all(norm1(ta$second_reviewer) == norm1(ya$second_reviewer)))

cells <- rbind(
  data.frame(PMID = ag$PMID, variable = ag$variable, r1 = ag$first_reviewer,
             r2 = ag$second_reviewer, adjTA = NA_character_, adjYA = NA_character_,
             p2 = NA_character_, adjtype = NA_character_, needs_adj = FALSE,
             stringsAsFactors = FALSE),
  data.frame(PMID = ta$PMID, variable = ta$variable, r1 = ta$first_reviewer,
             r2 = ta$second_reviewer, adjTA = ta$Adjduciation_TA, adjYA = ya$Adjduciation_YA,
             p2 = ph$adjud_final[match(paste(ta$PMID, ta$variable), paste(ph$PMID, ph$variable))],
             adjtype = ta$Adjudciation_type, needs_adj = TRUE, stringsAsFactors = FALSE))

## paper-level task = the ADJUDICATED study task, from the analysis dataset
key <- paste(L$PMID, L$variable)
cells$Study_Type <- L$Study_Type[match(cells$PMID, L$PMID)]
cells$final      <- L$final     [match(paste(cells$PMID, cells$variable), key)]
cells$source     <- L$source    [match(paste(cells$PMID, cells$variable), key)]
stopifnot(nrow(cells) == 18095L, length(unique(cells$PMID)) == 385L,
          !anyNA(cells$Study_Type), !anyNA(cells$source))
cells$Study_Type <- factor(cells$Study_Type, levels = TASKS)

## which section of the tool an item belongs to
cells$section <- ifelse(grepl("^causal_", cells$variable), "Causal",
                 ifelse(grepl("^descriptive_", cells$variable), "Descriptive",
                 ifelse(grepl("^predictive_", cells$variable), "Predictive", "Shared")))

## ---------------------------------------------------------------------------
## 2.  Classify every cell
## ---------------------------------------------------------------------------
n1 <- norm1(cells$r1); n2 <- norm1(cells$r2)
cells$status <- ifelse(isbl(n1) & isbl(n2), "Not applicable to either reviewer",
                ifelse(!isbl(n1) & !isbl(n2) & n1 == n2, "Reviewers agreed",
                ifelse(!isbl(n1) & !isbl(n2),            "Disagreed on the answer",
                                                         "Disagreed on applicability")))
DIS <- c("Disagreed on the answer", "Disagreed on applicability")
cells$assessed <- cells$status != "Not applicable to either reviewer"   # >=1 reviewer answered
cells$disagree <- cells$status %in% DIS
stopifnot(all(cells$disagree == cells$needs_adj))   # the worklist IS the disagreement set

## phase I / phase II routing
tA <- norm1(cells$adjTA); yA <- norm1(cells$adjYA)
cells$phase1 <- ifelse(!cells$needs_adj, NA_character_,
                ifelse(isbl(tA) | isbl(yA), "Only one adjudicator recorded a call",
                ifelse(tA == yA, "Phase I concordant (TA = YA)", "Phase I discordant -> phase II")))
cells$in_p2  <- cells$needs_adj & !is.na(cells$p2)

## final call vs the two reviewers (NA-aware: "skipped" counts as a blank)
fN <- normNA(cells$final); a1 <- normNA(cells$r1); a2 <- normNA(cells$r2)
cells$m1 <- fN == a1; cells$m2 <- fN == a2
cells$verdict <- ifelse(!cells$needs_adj, NA_character_,
                 ifelse(cells$source == "unresolved", "Still unresolved",
                 ifelse(cells$m1 & cells$m2, "Matched both",
                 ifelse(cells$m1, "Upheld the first reviewer",
                 ifelse(cells$m2, "Upheld the second reviewer",
                                  "Overrode both reviewers")))))

## ---------------------------------------------------------------------------
## 3.  Tables
## ---------------------------------------------------------------------------
## NB: do NOT write this with ifelse() -- ifelse returns a result the length of
## its TEST, so a scalar denominator silently collapses the whole column to its
## first value.  That produced "247.9%" everywhere before it was caught.
pct <- function(a, b) {
  n <- max(length(a), length(b))
  a <- rep_len(a, n); b <- rep_len(b, n)
  r <- rep(NA_real_, n)
  ok <- !is.na(a) & !is.na(b) & b != 0
  r[ok] <- round(100 * a[ok] / b[ok], 1)
  r
}
tab <- list()

## -- 3a. overall cell census
tab$census <- data.frame(
  Category = c("Cells in the analysis (385 papers x 47 items)",
               "  Not applicable to either reviewer",
               "  Assessed by at least one reviewer",
               "     Reviewers agreed",
               "     Disagreed on the answer (both answered, differently)",
               "     Disagreed on applicability (one answered, one N/A)"),
  n = c(nrow(cells), sum(!cells$assessed), sum(cells$assessed),
        sum(cells$status == "Reviewers agreed"),
        sum(cells$status == "Disagreed on the answer"),
        sum(cells$status == "Disagreed on applicability")))
tab$census$pct_of_assessed <- pct(tab$census$n, sum(cells$assessed))
tab$census$pct_of_assessed[1:2] <- NA

## -- 3b. by task
by_task <- function(d) {
  s <- split(d, d$Study_Type)
  do.call(rbind, lapply(names(s), function(k) { x <- s[[k]]
    data.frame(Task = k, Papers = length(unique(x$PMID)), Cells = nrow(x),
      Assessed = sum(x$assessed), Agreed = sum(x$status == "Reviewers agreed"),
      Dis_answer = sum(x$status == "Disagreed on the answer"),
      Dis_applic = sum(x$status == "Disagreed on applicability"),
      Disagreed = sum(x$disagree),
      Disagree_pct = pct(sum(x$disagree), sum(x$assessed)),
      Cells_per_paper = round(sum(x$assessed) / length(unique(x$PMID)), 1),
      Adjudicated_per_paper = round(sum(x$disagree) / length(unique(x$PMID)), 1)) }))
}
tab$task <- by_task(cells)
tab$task <- rbind(tab$task, data.frame(Task = "ALL", Papers = 385,
  Cells = nrow(cells), Assessed = sum(cells$assessed),
  Agreed = sum(cells$status == "Reviewers agreed"),
  Dis_answer = sum(cells$status == "Disagreed on the answer"),
  Dis_applic = sum(cells$status == "Disagreed on applicability"),
  Disagreed = sum(cells$disagree), Disagree_pct = pct(sum(cells$disagree), sum(cells$assessed)),
  Cells_per_paper = round(sum(cells$assessed) / 385, 1),
  Adjudicated_per_paper = round(sum(cells$disagree) / 385, 1)))

## -- 3c. by item (and Cohen's kappa where both reviewers answered)
kappa_of <- function(a, b) {
  lv <- union(a, b); if (length(lv) < 2 || length(a) < 20) return(NA_real_)
  m  <- table(factor(a, lv), factor(b, lv)); n <- sum(m)
  po <- sum(diag(m)) / n
  pe <- sum(rowSums(m) * colSums(m)) / n^2
  if (pe == 1) return(NA_real_)
  round((po - pe) / (1 - pe), 3)
}
items <- do.call(rbind, lapply(sort(unique(cells$variable)), function(v) {
  x <- cells[cells$variable == v, ]
  bo <- x[x$status %in% c("Reviewers agreed", "Disagreed on the answer"), ]
  data.frame(Item = v, Section = x$section[1], Assessed = sum(x$assessed),
    Agreed = sum(x$status == "Reviewers agreed"),
    Dis_answer = sum(x$status == "Disagreed on the answer"),
    Dis_applic = sum(x$status == "Disagreed on applicability"),
    Disagreed = sum(x$disagree),
    Disagree_pct = pct(sum(x$disagree), sum(x$assessed)),
    Both_answered = nrow(bo),
    Dis_pct_both = pct(sum(x$status == "Disagreed on the answer"), nrow(bo)),
    Kappa = kappa_of(norm1(bo$r1), norm1(bo$r2))) }))
tab$item <- items[order(-items$Disagree_pct, -items$Assessed), ]

## -- 3d. item x task  (a causal_* item can still be touched on a paper finally
##        typed Descriptive, when the reviewers disagreed about the task itself)
it <- cells[cells$assessed, ]
tab$item_task <- do.call(rbind, lapply(sort(unique(it$variable)), function(v)
  do.call(rbind, lapply(TASKS, function(k) {
    x <- it[it$variable == v & it$Study_Type == k, ]
    if (!nrow(x)) return(NULL)
    data.frame(Item = v, Task = k, Assessed = nrow(x),
      Agreed = sum(x$status == "Reviewers agreed"),
      Dis_answer = sum(x$status == "Disagreed on the answer"),
      Dis_applic = sum(x$status == "Disagreed on applicability"),
      Disagreed = sum(x$disagree), Disagree_pct = pct(sum(x$disagree), nrow(x))) }))))

## -- 3e. adjudication burden per paper
pp <- data.frame(PMID = unique(cells$PMID))
pp$Task     <- cells$Study_Type[match(pp$PMID, cells$PMID)]
pp$Assessed <- as.integer(tapply(cells$assessed, cells$PMID, sum)[pp$PMID])
pp$Adjud    <- as.integer(tapply(cells$disagree, cells$PMID, sum)[pp$PMID])
pp$Pct      <- pct(pp$Adjud, pp$Assessed)
tab$paper_dist <- do.call(rbind, lapply(c(TASKS, "ALL"), function(k) {
  x <- if (k == "ALL") pp else pp[pp$Task == k, ]
  data.frame(Task = k, Papers = nrow(x),
    Papers_with_0 = sum(x$Adjud == 0), Total_adjudicated = sum(x$Adjud),
    Min = min(x$Adjud), Q1 = quantile(x$Adjud, .25),
    Median = median(x$Adjud), Q3 = quantile(x$Adjud, .75), Max = max(x$Adjud),
    Mean = round(mean(x$Adjud), 1), Mean_pct_of_items = round(mean(x$Pct), 1)) }))
tab$paper_hist <- as.data.frame(table(cut(pp$Adjud,
  breaks = c(-1, 0, 2, 5, 10, 15, 20, 30, Inf),
  labels = c("0", "1-2", "3-5", "6-10", "11-15", "16-20", "21-30", "31+"))),
  responseName = "Papers"); names(tab$paper_hist)[1] <- "Items_adjudicated"
tab$paper_hist$Pct <- pct(tab$paper_hist$Papers, 385)

## -- 3f. PHASE I: the two adjudicators working independently
d <- cells[cells$needs_adj, ]
tab$phase1 <- data.frame(
  Measure = c("Cells routed to adjudication",
              "  TA recorded a call", "  YA recorded a call", "  both recorded a call",
              "     Phase I CONCORDANT (TA = YA)", "     Phase I DISCORDANT -> phase II",
              "  only one adjudicator recorded a call"),
  n = c(nrow(d), sum(!isbl(norm1(d$adjTA))), sum(!isbl(norm1(d$adjYA))),
        sum(!isbl(norm1(d$adjTA)) & !isbl(norm1(d$adjYA))),
        sum(d$phase1 == "Phase I concordant (TA = YA)", na.rm = TRUE),
        sum(d$phase1 == "Phase I discordant -> phase II", na.rm = TRUE),
        sum(d$phase1 == "Only one adjudicator recorded a call", na.rm = TRUE)))
tab$phase1$pct_of_routed <- pct(tab$phase1$n, nrow(d))

both <- d[d$phase1 %in% c("Phase I concordant (TA = YA)", "Phase I discordant -> phase II"), ]
tab$phase1_task <- do.call(rbind, lapply(c(TASKS, "ALL"), function(k) {
  x <- if (k == "ALL") both else both[both$Study_Type == k, ]
  data.frame(Task = k, Both_adjudicated = nrow(x),
    Concordant = sum(x$phase1 == "Phase I concordant (TA = YA)"),
    Discordant = sum(x$phase1 == "Phase I discordant -> phase II"),
    Concordance_pct = pct(sum(x$phase1 == "Phase I concordant (TA = YA)"), nrow(x))) }))
tab$phase1_item <- do.call(rbind, lapply(sort(unique(both$variable)), function(v) {
  x <- both[both$variable == v, ]
  data.frame(Item = v, Section = x$section[1], Both_adjudicated = nrow(x),
    Concordant = sum(x$phase1 == "Phase I concordant (TA = YA)"),
    Discordant = sum(x$phase1 == "Phase I discordant -> phase II"),
    Concordance_pct = pct(sum(x$phase1 == "Phase I concordant (TA = YA)"), nrow(x))) }))
tab$phase1_item <- tab$phase1_item[order(tab$phase1_item$Concordance_pct,
                                         -tab$phase1_item$Both_adjudicated), ]

## each adjudicator independently vs the two reviewers (position-neutrality check)
ind <- do.call(rbind, lapply(c("TA", "YA"), function(who) {
  a <- normNA(if (who == "TA") d$adjTA else d$adjYA)
  x <- d[!isbl(norm1(if (who == "TA") d$adjTA else d$adjYA)), ]
  ax <- normNA(if (who == "TA") x$adjTA else x$adjYA)
  data.frame(Adjudicator = who, Cells_adjudicated = nrow(x),
    Upheld_first  = sum(ax == normNA(x$r1)),
    Upheld_second = sum(ax == normNA(x$r2)),
    Overrode_both = sum(ax != normNA(x$r1) & ax != normNA(x$r2)),
    Upheld_first_pct  = pct(sum(ax == normNA(x$r1)), nrow(x)),
    Upheld_second_pct = pct(sum(ax == normNA(x$r2)), nrow(x)),
    Overrode_both_pct = pct(sum(ax != normNA(x$r1) & ax != normNA(x$r2)), nrow(x))) }))
tab$phase1_independent <- ind

## -- 3g. PHASE II
p2 <- d[d$in_p2, ]
tab$phase2 <- data.frame(
  Measure = c("Cells taken into phase II", "  papers involved",
              "  resolved (adjud_final recorded)", "  still blank",
              "Phase-II cells that came from a phase-I disagreement",
              "Phase-II cells where only one adjudicator had recorded a call"),
  n = c(nrow(p2), length(unique(p2$PMID)), sum(!isbl(norm1(p2$p2))), sum(isbl(norm1(p2$p2))),
        sum(p2$phase1 == "Phase I discordant -> phase II"),
        sum(p2$phase1 == "Only one adjudicator recorded a call")))
tab$phase2_task <- do.call(rbind, lapply(c(TASKS, "ALL"), function(k) {
  x <- if (k == "ALL") p2 else p2[p2$Study_Type == k, ]
  y <- if (k == "ALL") d  else d[d$Study_Type == k, ]
  data.frame(Task = k, Routed_to_adjudication = nrow(y), Into_phase_II = nrow(x),
    Pct_of_routed = pct(nrow(x), nrow(y)),
    Agreed_with_TA = sum(normNA(x$p2) == normNA(x$adjTA)),
    Agreed_with_YA = sum(normNA(x$p2) == normNA(x$adjYA)),
    New_answer = sum(normNA(x$p2) != normNA(x$adjTA) & normNA(x$p2) != normNA(x$adjYA))) }))

## -- 3h. the FINAL call vs the two reviewers
vd <- function(x) c("Upheld the first reviewer", "Upheld the second reviewer",
                    "Overrode both reviewers", "Matched both", "Still unresolved")
tab$verdict <- data.frame(Verdict = vd(), n = as.integer(table(factor(d$verdict, vd()))))
tab$verdict$pct_of_adjudicated <- pct(tab$verdict$n, nrow(d))
res <- d[d$verdict != "Still unresolved", ]
tab$verdict_head <- data.frame(
  Measure = c("Adjudicated cells with a final call",
              "  reproduced one of the two reviewers' answers",
              "  overrode both reviewers (a third answer)"),
  n = c(nrow(res), sum(res$verdict %in% c("Upheld the first reviewer",
                                          "Upheld the second reviewer", "Matched both")),
        sum(res$verdict == "Overrode both reviewers")))
tab$verdict_head$pct <- pct(tab$verdict_head$n, nrow(res))

vtab <- function(d0, grp) do.call(rbind, lapply(unique(d0[[grp]]), function(g) {
  x <- d0[d0[[grp]] == g, ]
  data.frame(setNames(list(g), grp), Adjudicated = nrow(x),
    Upheld_first = sum(x$verdict == "Upheld the first reviewer"),
    Upheld_second = sum(x$verdict == "Upheld the second reviewer"),
    Overrode_both = sum(x$verdict == "Overrode both reviewers"),
    Unresolved = sum(x$verdict == "Still unresolved"),
    Upheld_a_reviewer_pct = pct(sum(x$verdict %in% c("Upheld the first reviewer",
      "Upheld the second reviewer", "Matched both")), sum(x$verdict != "Still unresolved")),
    Overrode_both_pct = pct(sum(x$verdict == "Overrode both reviewers"),
                            sum(x$verdict != "Still unresolved"))) }))
tab$verdict_task <- vtab(transform(d, Task = as.character(Study_Type)), "Task")
tab$verdict_task <- tab$verdict_task[match(TASKS, tab$verdict_task$Task), ]
tab$verdict_item <- vtab(transform(d, Item = variable), "Item")
tab$verdict_item <- tab$verdict_item[order(-tab$verdict_item$Overrode_both_pct,
                                           -tab$verdict_item$Adjudicated), ]
tab$verdict_item_task <- do.call(rbind, lapply(sort(unique(d$variable)), function(v)
  do.call(rbind, lapply(TASKS, function(k) {
    x <- d[d$variable == v & d$Study_Type == k, ]; if (!nrow(x)) return(NULL)
    data.frame(Item = v, Task = k, Adjudicated = nrow(x),
      Upheld_first = sum(x$verdict == "Upheld the first reviewer"),
      Upheld_second = sum(x$verdict == "Upheld the second reviewer"),
      Overrode_both = sum(x$verdict == "Overrode both reviewers"),
      Unresolved = sum(x$verdict == "Still unresolved"),
      Overrode_both_pct = pct(sum(x$verdict == "Overrode both reviewers"),
                              sum(x$verdict != "Still unresolved"))) }))))

## -- 3h2. POSITION-NEUTRALITY, and why it cannot be read as a blinding check.
## The "first"/"second" reviewer column is NOT an arbitrary label: it is ordered
## by reviewer ID, so reviewer 1 occupies the first slot on 100% of their papers
## and reviewer 14 on 0%.  Column position and reviewer identity are therefore
## confounded, and a lean toward either column is equally well explained by a
## genuine difference between reviewers.  It is NOT evidence about blinding.
rid <- rbind(rd("private/reviewers/adjudication-worklists/08_08_2026_do_not_Need_adj_385.xlsx"), rd("private/reviewers/adjudication-worklists/08_08_2026_Needs_adj_progress_TA_385.xlsx")[, 1:9])
rid <- rid[rid$variable == "Reviewer_ID" & !(rid$PMID %in% EXCL) & !is.na(rid$first_reviewer),
           c("PMID","first_reviewer","second_reviewer")]
rid <- rid[!duplicated(rid$PMID), ]
names(rid) <- c("PMID","rid1","rid2")
stopifnot(nrow(rid) == 385L)
RIDS <- sort(as.integer(unique(c(rid$rid1, rid$rid2))))

## -- DISPLAY RE-NUMBERING, the same rule the calibration figures use since 2026-08-16.
## Fourteen reviewers were recruited; one withdrew before data collection, leaving 13.
## The source workbooks keep that reviewer's original slot, so the retained reviewers
## carry the identifiers 1,2,4..14 - a sequence that runs to 14 and reads as though
## fourteen people contributed.  Every PUBLISHED figure and table numbers them 1..13.
## The ORIGINAL identifier is what addresses a real person and is what the assignment,
## folder and publishing scripts under code/reviewer-ops/ must keep using; it is carried
## here as Reviewer_original so the display number stays traceable to the source files.
## Applied only where a table is built for display - never to the join keys above.
DISPLAY_NO <- setNames(seq_along(RIDS), as.character(RIDS))
stopifnot(length(RIDS) == 13L, identical(unname(DISPLAY_NO), 1:13))
disp <- function(k) unname(DISPLAY_NO[as.character(k)])

tab$slot <- do.call(rbind, lapply(RIDS, function(k) {
  f <- sum(rid$rid1 == as.character(k)); s <- sum(rid$rid2 == as.character(k))
  data.frame(Reviewer_No = disp(k), Reviewer_original = k, Papers = f + s,
             In_first_slot = f, In_second_slot = s, Pct_first = pct(f, f + s)) }))

bt <- function(a, b) { t <- binom.test(a, a + b, 0.5)
  data.frame(First = a, Second = b, Pct_first = round(100 * a / (a + b), 1),
             p_value = signif(t$p.value, 3),
             CI_low = round(100 * t$conf.int[1], 1), CI_high = round(100 * t$conf.int[2], 1)) }
aTA <- normNA(d$adjTA); aYA <- normNA(d$adjYA); R1 <- normNA(d$r1); R2 <- normNA(d$r2)
okTA <- !isbl(norm1(d$adjTA)); okYA <- !isbl(norm1(d$adjYA))
tab$position <- rbind(
  cbind(Stage = "Phase I - TA alone", bt(sum(aTA[okTA] == R1[okTA]), sum(aTA[okTA] == R2[okTA]))),
  cbind(Stage = "Phase I - YA alone", bt(sum(aYA[okYA] == R1[okYA]), sum(aYA[okYA] == R2[okYA]))),
  cbind(Stage = "Final call",         bt(sum(d$verdict == "Upheld the first reviewer"),
                                         sum(d$verdict == "Upheld the second reviewer"))))

## -- 3k. per-reviewer contribution and how often their answer was upheld
d$rid1 <- rid$rid1[match(d$PMID, rid$PMID)]; d$rid2 <- rid$rid2[match(d$PMID, rid$PMID)]
cells$rid1 <- rid$rid1[match(cells$PMID, rid$PMID)]
cells$rid2 <- rid$rid2[match(cells$PMID, rid$PMID)]
res2 <- d[d$verdict != "Still unresolved", ]
tab$reviewer <- do.call(rbind, lapply(RIDS, function(k) {
  k <- as.character(k)
  cc <- cells[(cells$rid1 == k | cells$rid2 == k) & cells$assessed, ]
  rr <- res2[res2$rid1 == k | res2$rid2 == k, ]
  up <- sum(rr$rid1 == k & rr$verdict == "Upheld the first reviewer") +
        sum(rr$rid2 == k & rr$verdict == "Upheld the second reviewer")
  ov <- sum(rr$verdict == "Overrode both reviewers")
  data.frame(Reviewer_No = disp(k), Reviewer_original = as.integer(k),
             Papers = length(unique(cc$PMID)),
    Cells_assessed = nrow(cc), Agreed_with_partner = sum(cc$status == "Reviewers agreed"),
    Agreement_pct = pct(sum(cc$status == "Reviewers agreed"), nrow(cc)),
    Adjudicated = nrow(rr), Upheld = up, Not_upheld = nrow(rr) - up - ov,
    Both_overridden = ov, Upheld_pct = pct(up, nrow(rr))) }))
tab$reviewer <- tab$reviewer[order(-tab$reviewer$Upheld_pct), ]

## -- 3i. resolution route of every adjudicated cell (the `source` column)
tab$route <- as.data.frame(table(cells$source), responseName = "Cells")
names(tab$route)[1] <- "Resolution route"
tab$route$pct <- pct(tab$route$Cells, nrow(cells))

## -- 3j. Full vs Partial adjudication, per paper
apap <- tapply(d$adjtype, d$PMID, function(x) {
  u <- unique(x[!is.na(x)]); if (!length(u)) "unrecorded" else if (length(u) > 1) "mixed" else u })
tab$adjtype <- as.data.frame(table(unlist(apap)), responseName = "Papers")
names(tab$adjtype)[1] <- "Adjudication type"

## ---------------------------------------------------------------------------
## 3l. ITEM MAP -- tool variable -> bias domain + collapsed concept + label
##     Domain order and labels follow the manuscript Tables 1 & 2:
##     Study task -> Study design -> Saudi population -> Random error ->
##     Selection bias -> Measurement bias -> Confounding -> Missing data ->
##     Mentioning errors -> Conflating the task.  Labels are the verbatim tool
##     questions (Google-Forms wording), lightly trimmed, matching Table 2.
##     Each concept COLLAPSES the task-specific variants of one question
##     (e.g. descriptive_/predictive_/causal_design all -> "Study design").
## ---------------------------------------------------------------------------
DOMS <- c("Recusal","Study task","Study design","Saudi population","Random error",
          "Selection bias","Measurement bias","Confounding","Missing data",
          "Mentioning errors","Conflating the task")
CMAP <- read.csv(text = paste(
"concept|dom|label|vars",
"recusal|Recusal|Reviewer recused from the study?|recusal",
"task|Study task|Study task (epidemiological paradigm)|task",
"design|Study design|Study design|descriptive_design;predictive_design;causal_design",
"pop|Saudi population|Used data from Saudi Arabia?|descriptive_pop;predictive_pop;causal_pop",
"sampling|Random error|Sampling technique|descriptive_sampling;causal_sampling",
"sample_size|Random error|Sample-size calculation done?|descriptive_sample_size;causal_sample_size",
"acc_sampl|Random error|Accounted for non-response, ineligibility, loss to follow-up, etc. in the sample-size calculation?|descriptive_acc_sampl;causal_acc_sampl",
"sample_ach|Random error|Required sample size achieved?|descriptive_sample_ach;causal_sample_ach",
"base_sel|Selection bias|Baseline selection bias accounted for?|descriptive_base_sel;causal_base_sel",
"comp_dis|Selection bias|Compared responders vs non-responders?|causal_comp_dis",
"follow|Selection bias|Follow-up present in the study?|causal_follow",
"ltfu_bias|Selection bias|Loss-to-follow-up bias present?|causal_ltfu_bias",
"ltfu_acc|Selection bias|Loss-to-follow-up bias accounted for?|causal_ltfu_acc",
"outcome_type|Measurement bias|Nature of the outcome (objective or subjective)|descriptive_outcome_type;causal_outcome_type",
"val_outcome|Measurement bias|Validated outcome measurement?|descriptive_val_outcome;causal_val_outcome",
"diff_or_nondiff_out|Measurement bias|Outcome misclassification differential or non-differential?|causal_diff_or_nondiff_out",
"out_bias_acc|Measurement bias|Outcome measurement bias accounted for?|descriptive_out_bias_acc;causal_out_bias_acc",
"exposure_type|Measurement bias|Nature of the exposure (objective or subjective)|causal_exposure_type",
"val_exposure|Measurement bias|Validated exposure measurement?|causal_val_exposure",
"diff_or_nondiff_exp|Measurement bias|Exposure misclassification differential or non-differential?|causal_diff_or_nondiff_exp",
"exp_bias_acc|Measurement bias|Exposure measurement bias accounted for?|causal_exp_bias_acc",
"dep_or_indep_misc|Measurement bias|Exposure vs outcome measurement bias: independent or dependent?|causal_dep_or_indep_misc",
"base_conf_meth|Confounding|Baseline confounding method(s) used|causal_base_conf_meth",
"time_verying|Confounding|Time-varying effect estimated?|causal_time_verying",
"tv_conf_meth|Confounding|Time-varying confounding method(s) used|causal_tv_conf_meth",
"conf_var_det|Confounding|How confounding variables were selected|causal_conf_var_det",
"miss_outcome|Missing data|Any participant with a missing outcome?|descriptive_miss_outcome;causal_miss_outcome",
"hand_miss_outcom|Missing data|Method for handling missing outcome data|descriptive_hand_miss_outcom;causal_hand_miss_outcom",
"miss_exposure|Missing data|Any participant with a missing exposure?|causal_miss_exposure",
"hand_miss_exposure|Missing data|Method for handling missing exposure data|causal_hand_miss_exposure",
"err_disc|Mentioning errors|Errors qualitatively mentioned in the discussion|descriptive_err_disc;causal_err_disc",
"confl_task|Conflating the task|Investigated an association beyond describing the sample?|descriptive_confl_task",
sep = "\n"), sep = "|", header = TRUE, quote = "", comment.char = "", stringsAsFactors = FALSE)
CMAP$concept_ord <- seq_len(nrow(CMAP))
CMAP$dom_ord     <- match(CMAP$dom, DOMS)
stopifnot(!anyNA(CMAP$dom_ord))

V2C <- do.call(rbind, Map(function(cc, vs)
  data.frame(variable = strsplit(vs, ";", fixed = TRUE)[[1]], concept = cc,
             stringsAsFactors = FALSE), CMAP$concept, CMAP$vars))
stopifnot(nrow(V2C) == 47L, setequal(V2C$variable, unique(cells$variable)))

vtask_of <- function(v) ifelse(grepl("^descriptive_", v), "Descriptive",
                        ifelse(grepl("^predictive_",  v), "Predictive",
                        ifelse(grepl("^causal_",      v), "Causal", "All")))
cov_of <- function(cc) {
  t <- unique(vtask_of(V2C$variable[V2C$concept == cc]))
  if (identical(t, "All")) return("All")
  paste(c("Descriptive","Predictive","Causal")[c("Descriptive","Predictive","Causal") %in% t],
        collapse = ", ") }

cells$concept <- V2C$concept[match(cells$variable, V2C$variable)]
cells$vtask   <- vtask_of(cells$variable)

## PARTIAL AGREEMENT -- only meaningful for the four "select all that apply"
## questions, where two reviewers can share some ticked options without ticking
## an identical set.  A single-select conflict is always a clean either/or.
## Split on ';' ONLY: several single-select OPTION texts contain commas
## ("Yes, the authors conducted criterion validity..."), so a comma split would
## fabricate shared tokens.  A partial-agreement cell was still routed to
## adjudication -- resolution required an exact match, not an overlap.
MULTI <- c("descriptive_err_disc","causal_err_disc",
           "causal_base_conf_meth","causal_tv_conf_meth","causal_conf_var_det")
overlap <- mapply(function(a, b) {
  tk <- function(z) { p <- trimws(strsplit(tolower(ifelse(is.na(z), "", z)), ";", fixed = TRUE)[[1]])
                      unique(p[nzchar(p) & p != "nan"]) }
  length(intersect(tk(a), tk(b))) > 0 }, cells$r1, cells$r2)
cells$partial <- cells$status == "Disagreed on the answer" &
                 cells$variable %in% MULTI & overlap
stopifnot(all(cells$variable[cells$partial] %in% MULTI))   # partial <=> select-all item

## builders: one frame per (metric, granularity); the report sorts + groups it
dis_frame <- function(gv) {
  k <- factor(cells[[gv]]); s <- function(x) as.integer(tapply(x, k, sum))
  o <- data.frame(key = levels(k), Assessed = s(cells$assessed),
    Agreed = s(cells$status == "Reviewers agreed"),
    Partial = s(cells$partial),
    Dis_answer = s(cells$status == "Disagreed on the answer"),
    Dis_applic = s(cells$status == "Disagreed on applicability"),
    Disagreed = s(cells$disagree), stringsAsFactors = FALSE, row.names = NULL)
  o$Conflict <- o$Dis_answer - o$Partial        # both answered, no shared option
  o$Disagreed_pct <- pct(o$Disagreed, o$Assessed); o }
ph1_frame <- function(gv) {
  sub <- cells[cells$needs_adj & cells$phase1 %in%
               c("Phase I concordant (TA = YA)", "Phase I discordant -> phase II"), ]
  k <- factor(sub[[gv]]); s <- function(x) as.integer(tapply(x, k, sum))
  o <- data.frame(key = levels(k), Both = as.integer(table(k)),
    Concordant = s(sub$phase1 == "Phase I concordant (TA = YA)"),
    Discordant = s(sub$phase1 == "Phase I discordant -> phase II"),
    stringsAsFactors = FALSE, row.names = NULL)
  o$Concordance_pct <- pct(o$Concordant, o$Both); o }
vd_frame <- function(gv) {
  sub <- cells[cells$needs_adj, ]
  k <- factor(sub[[gv]]); s <- function(x) as.integer(tapply(x, k, sum))
  o <- data.frame(key = levels(k), Adjudicated = as.integer(table(k)),
    Upheld = s(sub$verdict %in% c("Upheld the first reviewer",
              "Upheld the second reviewer", "Matched both")),
    Overrode = s(sub$verdict == "Overrode both reviewers"),
    Unresolved = s(sub$verdict == "Still unresolved"),
    stringsAsFactors = FALSE, row.names = NULL)
  o$Resolved <- o$Adjudicated - o$Unresolved
  o$Overrode_pct <- pct(o$Overrode, o$Resolved); o }

meta_collapsed <- function(df) {
  m <- match(df$key, CMAP$concept)
  df$Item <- CMAP$label[m]; df$Domain <- CMAP$dom[m]
  df$dom_ord <- CMAP$dom_ord[m]; df$concept_ord <- CMAP$concept_ord[m]
  df$Tasks <- vapply(df$key, cov_of, character(1))
  df[order(df$concept_ord), ] }
meta_strat <- function(df) {
  df$concept <- V2C$concept[match(df$key, V2C$variable)]
  m <- match(df$concept, CMAP$concept)
  df$Item <- CMAP$label[m]; df$Domain <- CMAP$dom[m]
  df$dom_ord <- CMAP$dom_ord[m]; df$concept_ord <- CMAP$concept_ord[m]
  df$Task <- vtask_of(df$key)
  df[order(df$concept_ord, c(All = 0, Descriptive = 1, Predictive = 2, Causal = 3)[df$Task]), ] }

tab$dis_collapsed <- meta_collapsed(dis_frame("concept"))
tab$dis_strat     <- meta_strat(dis_frame("variable"))
tab$ph1_collapsed <- meta_collapsed(ph1_frame("concept"))
tab$ph1_strat     <- meta_strat(ph1_frame("variable"))
tab$vd_collapsed  <- meta_collapsed(vd_frame("concept"))
tab$vd_strat      <- meta_strat(vd_frame("variable"))
## reconcile: item partition must sum back to the assessed / routed totals
stopifnot(sum(tab$dis_collapsed$Assessed) == sum(cells$assessed),
          sum(tab$dis_strat$Assessed)     == sum(cells$assessed),
          sum(tab$dis_collapsed$Disagreed) == sum(cells$disagree),
          sum(tab$vd_collapsed$Adjudicated) == sum(cells$needs_adj))

## Anonymize the adjudicators in every table that carried initials (TA -> Adjudicator 1,
## YA -> Adjudicator 2) so reviewers cannot identify which person is which.
tab$phase1_independent$Adjudicator <-
  c(TA = "Adjudicator 1", YA = "Adjudicator 2")[tab$phase1_independent$Adjudicator]
tab$position$Stage <- c("Phase I - TA alone" = "Phase I: Adjudicator 1 alone",
  "Phase I - YA alone" = "Phase I: Adjudicator 2 alone",
  "Final call" = "Final call")[tab$position$Stage]

## ---------------------------------------------------------------------------
## 4.  Report + write
## ---------------------------------------------------------------------------
for (nm in names(tab)) {
  cat("\n\n=====================", nm, "=====================\n")
  print(tab[[nm]], row.names = FALSE, right = FALSE)
  write.csv(tab[[nm]], file.path(OUT, paste0(nm, ".csv")), row.names = FALSE,
            fileEncoding = "UTF-8")
}
write.csv(cells[, c("PMID","Study_Type","variable","section","r1","r2","adjTA","adjYA",
                    "p2","final","source","status","phase1","verdict")],
          file.path(OUT, "cell_level_detail.csv"), row.names = FALSE, fileEncoding = "UTF-8")
saveRDS(tab, file.path(OUT, "tables.rds"))
cat("\n\n[written]", OUT, "\n")

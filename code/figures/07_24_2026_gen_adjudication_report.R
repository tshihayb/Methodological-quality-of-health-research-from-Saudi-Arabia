###############################################################################
##  Build the HTML report for the reviewer-disagreement / adjudication analysis.
##  Reads 07_24_2026_adjudication_process/tables.rds.  Self-contained page.
##  Design system per the project: petrol-teal #16697a accent, serif headings,
##  system-ui body, tabular-nums, wide tables in .tscroll.
##
##  Conventions in this file, all deliberate:
##   * PURE ASCII output (entities for any symbol); asserted at the end.  Editors
##     that re-encode UTF-8 have mojibaked the punctuation here before.
##   * No em / en dashes anywhere in the prose (project style): commas, colons,
##     semicolons and parentheses instead.  Missing values render as "n/a".
##   * The adjudicators are ANONYMIZED as "Adjudicator 1" (TA) and "Adjudicator 2"
##     (YA) so reviewers reading the report cannot identify which person is which.
##   * Instrument items are shown by their Table 1 / Table 2 labels, never by
##     their raw variable names, and grouped by bias domain in tool order.
###############################################################################

PROJ <- "."
DIR  <- file.path(PROJ, "data/adjudication/process-tables")
tab  <- readRDS(file.path(DIR, "tables.rds"))
cd   <- read.csv(file.path(DIR, "cell_level_detail.csv"), colClasses = "character")
HTML <- file.path(PROJ, "outputs/reports/07_24_2026_adjudication_process_report.html")

## anonymize the adjudicators in any table label: TA/YA (and any full name) -> Adjudicator 1/2
sp <- function(x) { x <- gsub("\\bTA\\b", "Adjudicator 1", x); x <- gsub("\\bYA\\b", "Adjudicator 2", x)
                    x <- gsub("Talal", "Adjudicator 1", x, fixed = TRUE)
                    x <- gsub("Yasser", "Adjudicator 2", x, fixed = TRUE)
                    gsub("->", "into", x) }
tab$phase1$Measure <- sp(tab$phase1$Measure)

NAP <- '<span class="muted">n/a</span>'
h  <- function(x) { x <- as.character(x)
  x <- gsub("&","&amp;",x,fixed=TRUE); x <- gsub("<","&lt;",x,fixed=TRUE)
  gsub(">","&gt;",x,fixed=TRUE) }
n  <- function(x) ifelse(is.na(x), NAP, formatC(as.numeric(x), format="d", big.mark=","))
p1 <- function(x) ifelse(is.na(x), NAP, paste0(formatC(as.numeric(x), format="f", digits=1), "%"))
ab <- function(x) { x <- gsub("Descriptive","D",x); x <- gsub("Predictive","P",x)
                    gsub("Causal","C",x) }

## ---------------------------------------------------------------------------
## generic table renderer.  cols = named vector (df column -> header label).
## group: insert a full-width domain header row when that column changes.
## wrap:  columns allowed to wrap (long item labels).  bar/bartone: magnitude bar.
## ---------------------------------------------------------------------------
T <- function(df, cols, pctc = character(0), wrap = character(0), bar = NULL,
              bartone = "", group = NULL, note = NULL, cls = "") {
  headers <- paste0("<th>", h(unname(cols)), "</th>", collapse = "")
  ncell <- length(cols); body <- ""; lastg <- NULL
  for (i in seq_len(nrow(df))) {
    if (!is.null(group)) { g <- df[[group]][i]
      if (is.null(lastg) || !identical(g, lastg)) {
        body <- paste0(body, '<tr class="grp"><td colspan="', ncell, '">', h(g), '</td></tr>')
        lastg <- g } }
    tds <- paste0(vapply(names(cols), function(cn) {
      v <- df[[cn]][i]; isp <- cn %in% pctc; isn <- is.numeric(df[[cn]])
      cell <- if (isp) p1(v) else if (isn) n(v) else h(v)
      kl <- paste(c(if (isp || isn) "num", if (cn %in% wrap) "wrapcell"), collapse = " ")
      if (!is.null(bar) && identical(cn, bar) && !is.na(v))
        cell <- paste0('<span class="mb ', bartone, '"><i style="width:',
                       min(100, as.numeric(v)), '%"></i></span>', cell)
      paste0('<td class="', kl, '">', cell, "</td>") }, character(1)), collapse = "")
    body <- paste0(body, "<tr>", tds, "</tr>") }
  paste0('<div class="tscroll"><table class="', cls, '"><thead><tr>', headers,
         "</tr></thead><tbody>", body, "</tbody></table></div>",
         if (is.null(note)) "" else paste0('<p class="note">', note, "</p>"))
}

## ---------------------------------------------------------------------------
## headline figures
## ---------------------------------------------------------------------------
cen <- tab$census; TOT <- cen$n[1]; NAB <- cen$n[2]; ASS <- cen$n[3]
AGR <- cen$n[4]; DA <- cen$n[5]; DP <- cen$n[6]; ROUT <- DA + DP
P1  <- tab$phase1; P2 <- tab$phase2
CONC <- P1$n[5]; DISC <- P1$n[6]; BOTH <- P1$n[4]
P2N <- P2$n[1]; P2P <- P2$n[2]
VH <- tab$verdict_head; RESOLVED <- VH$n[1]; UPHELD <- VH$n[2]; OVER <- VH$n[3]
UNRES <- tab$verdict$n[tab$verdict$Verdict == "Still unresolved"]
NOADJ <- tab$paper_dist$Papers_with_0[tab$paper_dist$Task == "ALL"]
RJ  <- sum(cd$r1 != "" & !is.na(cd$r1)) + sum(cd$r2 != "" & !is.na(cd$r2))
AJ  <- P1$n[2] + P1$n[3] + P2N
PAP_ADJ <- 385 - NOADJ
P2TA <- tab$phase2_task$Agreed_with_TA[tab$phase2_task$Task == "ALL"]
P2YA <- tab$phase2_task$Agreed_with_YA[tab$phase2_task$Task == "ALL"]
P2NEW <- tab$phase2_task$New_answer[tab$phase2_task$Task == "ALL"]

stat <- function(v, l, s = "") paste0('<div class="stat"><b>', v, '</b><span>', l,
  '</span>', if (nzchar(s)) paste0('<em>', s, '</em>') else "", "</div>")
fstage <- function(lab, val, den, sub, tone) paste0(
  '<div class="fs ', tone, '"><div class="fl"><span>', lab, '</span><b>', n(val), '</b></div>',
  '<div class="fb"><i style="width:', round(100*val/den, 2), '%"></i></div>',
  '<div class="fn">', sub, '</div></div>')
funnel <- paste0('<div class="funnel">',
  fstage("Judgement cells in scope", TOT, TOT,
         "385 papers times 47 tool items (the full grid)", "t0"),
  fstage("Assessed by at least one reviewer", ASS, TOT,
         paste0(n(NAB), " cells were not applicable to either reviewer; the instrument",
                "'s skip logic never asked them"), "t1"),
  fstage("Reviewers agreed outright", AGR, TOT,
         paste0(p1(round(100*AGR/ASS,1)), " of assessed cells, never re-examined"), "t2"),
  fstage("Routed to adjudication", ROUT, TOT,
         paste0(n(DA), " conflicting answers plus ", n(DP),
                " disagreements about whether the item applied"), "t3"),
  fstage("Escalated to phase II", P2N, TOT,
         paste0(n(DISC), " where Talal and Yasser differed, plus ", n(P2$n[6]),
                " where only one had recorded a call"), "t4"),
  fstage("Left unresolved", UNRES, TOT,
         "almost all skip-logic gaps awaiting a targeted adjudicator pass", "t5"), "</div>")

## ---------------------------------------------------------------------------
## page
## ---------------------------------------------------------------------------
S <- c(); add <- function(...) S <<- c(S, paste0(...))
add('<title>Reviewer disagreement and two-phase adjudication</title>')
add('<style>
:root{
  --accent:#16697a; --accent-2:#0d4d5c; --accent-soft:#e3eff1;
  --ink:#17252a; --ink-2:#3d5157; --ink-3:#6b7f85;
  --ground:#fbfaf8; --panel:#ffffff; --rule:#dfe3e1; --rule-2:#eceeec;
  --agree:#3f7d5c; --agree-soft:#e6efe9;
  --conflict:#b0563c; --conflict-soft:#f6e8e3;
  --pending:#96792e; --pending-soft:#f4efdf;
  --serif:"Iowan Old Style",Palatino,"Palatino Linotype",Georgia,serif;
  --sans:system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;
  --mono:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;
}
@media (prefers-color-scheme:dark){:root{
  --accent:#5fb3c4; --accent-2:#8fd0dd; --accent-soft:#16323a;
  --ink:#e6edee; --ink-2:#b3c3c7; --ink-3:#82989e;
  --ground:#0f1618; --panel:#151f22; --rule:#2a3a3e; --rule-2:#1e2b2e;
  --agree:#79b795; --agree-soft:#172b21;
  --conflict:#e0917a; --conflict-soft:#33201a;
  --pending:#cfb163; --pending-soft:#2c2717;
}}
:root[data-theme="dark"]{
  --accent:#5fb3c4; --accent-2:#8fd0dd; --accent-soft:#16323a;
  --ink:#e6edee; --ink-2:#b3c3c7; --ink-3:#82989e;
  --ground:#0f1618; --panel:#151f22; --rule:#2a3a3e; --rule-2:#1e2b2e;
  --agree:#79b795; --agree-soft:#172b21;
  --conflict:#e0917a; --conflict-soft:#33201a;
  --pending:#cfb163; --pending-soft:#2c2717;
}
:root[data-theme="light"]{
  --accent:#16697a; --accent-2:#0d4d5c; --accent-soft:#e3eff1;
  --ink:#17252a; --ink-2:#3d5157; --ink-3:#6b7f85;
  --ground:#fbfaf8; --panel:#ffffff; --rule:#dfe3e1; --rule-2:#eceeec;
  --agree:#3f7d5c; --agree-soft:#e6efe9;
  --conflict:#b0563c; --conflict-soft:#f6e8e3;
  --pending:#96792e; --pending-soft:#f4efdf;
}
*{box-sizing:border-box}
body{margin:0;background:var(--ground);color:var(--ink);font-family:var(--sans);
  font-size:16px;line-height:1.62;-webkit-font-smoothing:antialiased}
.wrap{max-width:1180px;margin:0 auto;padding:0 24px 96px}
.col{max-width:68ch}
h1,h2,h3{font-family:var(--serif);font-weight:600;text-wrap:balance;margin:0}
h1{font-size:clamp(2rem,4.4vw,3.1rem);line-height:1.1;letter-spacing:-.015em}
h2{font-size:clamp(1.35rem,2.4vw,1.75rem);line-height:1.2;margin:0 0 .2em}
h3{font-size:1.06rem;line-height:1.3;margin:1.4em 0 .35em}
.subh{font-family:var(--mono);font-size:.72rem;letter-spacing:.06em;
  text-transform:uppercase;color:var(--accent);margin:1.6em 0 .2em;font-weight:600}
p{margin:0 0 1em}
a{color:var(--accent);text-underline-offset:2px}
:focus-visible{outline:2px solid var(--accent);outline-offset:2px;border-radius:2px}
.muted{color:var(--ink-3)}

header{border-bottom:1px solid var(--rule);padding:56px 0 34px;margin-bottom:44px}
.eyebrow{font-family:var(--mono);font-size:.7rem;letter-spacing:.14em;text-transform:uppercase;
  color:var(--accent);margin:0 0 1.1em}
.lede{font-size:1.12rem;color:var(--ink-2);margin-top:1.1em}

.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(148px,1fr));
  gap:1px;background:var(--rule);border:1px solid var(--rule);margin:36px 0 0}
.stat{background:var(--panel);padding:16px 18px;display:flex;flex-direction:column;gap:2px;min-width:0}
.stat b{font-family:var(--serif);font-size:1.72rem;line-height:1.05;
  font-variant-numeric:tabular-nums;color:var(--accent)}
.stat span{font-size:.78rem;color:var(--ink-2);line-height:1.35}
.stat em{font-style:normal;font-size:.7rem;color:var(--ink-3)}

section{padding:52px 0 0;border-top:1px solid var(--rule-2);margin-top:52px}
section:first-of-type{border-top:0;margin-top:0;padding-top:0}
.shead{display:flex;gap:14px;align-items:baseline;margin-bottom:1.1em}
.snum{font-family:var(--mono);font-size:.72rem;color:var(--accent);letter-spacing:.1em;
  border:1px solid var(--rule);padding:3px 7px;flex:none;line-height:1}

.funnel{display:flex;flex-direction:column;gap:2px;margin:26px 0 8px}
.fs{padding:13px 16px;background:var(--panel);border-left:3px solid var(--rule)}
.fs.t0{border-left-color:var(--ink-3);color:var(--ink-3)}
.fs.t1{border-left-color:var(--accent);color:var(--accent)}
.fs.t2{border-left-color:var(--agree);background:var(--agree-soft);color:var(--agree)}
.fs.t3{border-left-color:var(--conflict);background:var(--conflict-soft);color:var(--conflict)}
.fs.t4{border-left-color:var(--conflict);color:var(--conflict)}
.fs.t5{border-left-color:var(--pending);background:var(--pending-soft);color:var(--pending)}
.fl{display:flex;justify-content:space-between;align-items:baseline;gap:16px}
.fl span{font-size:.9rem;font-weight:550}
.fl b{font-family:var(--serif);font-size:1.24rem;font-variant-numeric:tabular-nums}
.fb{height:5px;background:var(--rule-2);margin:7px 0 6px;overflow:hidden}
.fb i{display:block;height:100%;background:currentColor;opacity:.62}
.fn{font-size:.78rem;color:var(--ink-2);line-height:1.4}

.tscroll{overflow-x:auto;margin:12px 0 6px;border:1px solid var(--rule);background:var(--panel);max-width:100%}
table{border-collapse:collapse;width:100%;font-size:.83rem}
th,td{padding:7px 11px;text-align:left;border-bottom:1px solid var(--rule-2);
  white-space:nowrap;vertical-align:top}
thead th{background:var(--accent-soft);color:var(--accent-2);font-weight:600;
  font-size:.7rem;letter-spacing:.05em;text-transform:uppercase;position:sticky;top:0;
  border-bottom:1px solid var(--rule)}
tbody tr:last-child td{border-bottom:0}
tbody tr:hover td{background:var(--accent-soft)}
tr.grp td{background:var(--accent-soft);color:var(--accent-2);font-weight:600;
  font-size:.71rem;letter-spacing:.06em;text-transform:uppercase;
  border-top:1px solid var(--rule);border-bottom:1px solid var(--rule)}
tr.grp+tr td{border-top:0}
td.num{text-align:right;font-variant-numeric:tabular-nums}
td.wrapcell{white-space:normal;min-width:210px;max-width:380px;line-height:1.32}
table.tot tbody tr:last-child td{font-weight:650;border-top:1px solid var(--rule);
  background:var(--accent-soft)}
.mb{display:inline-block;width:46px;height:4px;background:var(--rule-2);
  margin-right:8px;vertical-align:middle}
.mb i{display:block;height:100%;background:var(--accent)}
.mb.warn i{background:var(--conflict)}
.mb.good i{background:var(--agree)}
.note{font-size:.79rem;color:var(--ink-2);margin:8px 0 0;max-width:82ch}

.callout{border:1px solid var(--rule);border-left:3px solid var(--accent);
  background:var(--panel);padding:18px 22px;margin:26px 0}
.callout.warn{border-left-color:var(--pending)}
.callout h3{color:var(--accent);margin-top:0}
.callout.warn h3{color:var(--pending)}
.callout p:last-child{margin-bottom:0}
.grid2{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:26px}
.grid2>*{min-width:0}
footer{margin-top:64px;padding-top:24px;border-top:1px solid var(--rule);
  font-size:.79rem;color:var(--ink-3)}
@media (max-width:640px){.wrap{padding:0 16px 64px}th,td{padding:6px 8px}}
</style>')

add('<div class="wrap"><header>')
add('<p class="eyebrow">Assessment of Healthcare Research Quality in Saudi Arabia</p>')
add('<h1>Where two reviewers disagreed, and how ', n(ROUT),
    ' disputed judgements were settled</h1>')
add('<p class="lede col">Every one of the 385 included papers was assessed independently by two of ',
    '13 epidemiologists against a 47-item risk-of-bias instrument. Wherever the two answers ',
    'differed, the cell was routed to a two-phase adjudication led by Talal and Yasser: each ruled ',
    'on it separately, and any cell where they still differed went to a joint second pass. This is ',
    'the full accounting of that process: what was disputed, by whom, and how it ended.</p>')
add('<div class="stats">',
  stat(n(RJ), "individual reviewer judgements", "across 754 paper-reviews"),
  stat(n(ROUT), "cells needing adjudication", paste0(p1(round(100*ROUT/ASS,1)), " of assessed cells")),
  stat(n(AJ), "adjudication decisions", "Talal, Yasser, and the joint phase II"),
  stat(n(PAP_ADJ), "papers touched by adjudication", "of 385"),
  stat(p1(round(100*CONC/BOTH,1)), "phase-I concordance", "Talal and Yasser ruling independently"),
  stat(p1(round(100*UPHELD/RESOLVED,1)), "of final calls matched a reviewer", "the rest overrode both"),
  '</div>')
add('</header>')

## -- 01 census
add('<section><div class="shead"><span class="snum">01</span><div>',
    '<h2>The cell census</h2></div></div>')
add('<div class="col"><p>The unit of analysis is a <strong>cell</strong>: one item on one paper. ',
    'The grid is 385 times 47 = ', n(TOT), ' cells, but most were never in play, because the ',
    'instrument branches, so a descriptive paper is never asked the 31 causal items. Counting ',
    'agreement across the whole grid would inflate it enormously. Everything below is therefore ',
    'based on the ', n(ASS), ' cells where <em>at least one</em> reviewer recorded an answer.</p></div>')
add(funnel)
add(T(setNames(tab$census, c("Category","Cells","pct")),
      c(Category = "Category", Cells = "Cells", pct = "% of assessed"), pctc = "pct",
      note = paste0("Agreement is exact-match after casefolding, whitespace collapse and sorting ",
      "the parts of multi-select answers, the same normalisation the analysis dataset is built ",
      "with, so these counts partition the dataset exactly.")))
add('<div class="callout"><h3>Two kinds of disagreement, counted separately</h3>',
    '<p>Most disputes are ordinary: both reviewers answered and the answers differ (',
    n(DA), ' cells). The other ', n(DP), ' are a different animal, where one reviewer answered ',
    'while the other treated the item as not applicable. Those are disagreements about the ',
    '<em>shape</em> of the study, not its quality: they arise when the two disagreed on an upstream ',
    'branching question such as the study design or whether there was follow-up. They matter because ',
    'they are the ones that later resurface as skip-logic gaps.</p></div>')
add('</section>')

## -- 02 by task
add('<section><div class="shead"><span class="snum">02</span><div>',
    '<h2>Disagreement by study task</h2></div></div>')
add('<div class="col"><p>The three tasks are not comparable in exposure: a causal paper is asked ',
    '31 items, a descriptive paper 16, a predictive paper only 4. Causal papers therefore dominate ',
    'the adjudication workload both because there are more of them and because each carries six times ',
    'the surface area of a predictive paper.</p></div>')
add(T(setNames(tab$task, names(tab$task)),
      c(Task="Task", Papers="Papers", Cells="Cells", Assessed="Assessed", Agreed="Agreed",
        Dis_answer="Conflicting answers", Dis_applic="Applicability disputes",
        Disagreed="Disagreed", Disagree_pct="Disagreed %",
        Cells_per_paper="Assessed / paper", Adjudicated_per_paper="Adjudicated / paper"),
      pctc = "Disagree_pct", bar = "Disagree_pct", bartone = "warn", cls = "tot"))
add('</section>')

## ---------------------------------------------------------------------------
## helper: render the four views (collapsed x2, stratified x2) for an item metric
## ---------------------------------------------------------------------------
item_block <- function(coll, strat, kind) {
  ## a concept covering all three tasks reads "All"; others keep the D/P/C set
  coll$Tasks <- ifelse(coll$Tasks == "Descriptive, Predictive, Causal", "All", ab(coll$Tasks))
  ## the split-by-task views drop the two shared, non-task-specific items
  strat <- strat[!strat$concept %in% c("recusal", "task"), ]
  out <- c()
  if (kind == "dis") {
    ccA <- c(Item="Instrument item", Tasks="Tasks", Assessed="Assessed", Agreed="Full agreement",
             Partial="Partial agreement", Conflict="Conflicting answers",
             Dis_applic="Applicability disputes", Disagreed="Disagreed", Disagreed_pct="Disagreed %")
    ccD <- c(Item="Instrument item", Tasks="Tasks", Assessed="Assessed",
             Disagreed="Disagreed", Disagreed_pct="Disagreed %")
    scA <- c(Item="Instrument item", Task="Task", Assessed="Assessed", Agreed="Full agreement",
             Partial="Partial agreement", Conflict="Conflicting answers",
             Dis_applic="Applicability disputes", Disagreed="Disagreed", Disagreed_pct="Disagreed %")
    scD <- c(Item="Instrument item", Task="Task", Assessed="Assessed",
             Disagreed="Disagreed", Disagreed_pct="Disagreed %")
    rate <- "Disagreed_pct"; tone <- "warn"; minden <- "Assessed"; thr <- 20
    dord <- function(d) d[order(-d[[rate]]), ]
  } else if (kind == "ph1") {
    ccA <- c(Item="Instrument item", Tasks="Tasks", Both="Both ruled",
             Concordant="Concordant", Discordant="Discordant", Concordance_pct="Concordance %")
    ccD <- c(Item="Instrument item", Tasks="Tasks", Both="Both ruled",
             Discordant="Discordant", Concordance_pct="Concordance %")
    scA <- c(Item="Instrument item", Task="Task", Both="Both ruled",
             Concordant="Concordant", Discordant="Discordant", Concordance_pct="Concordance %")
    scD <- c(Item="Instrument item", Task="Task", Both="Both ruled",
             Discordant="Discordant", Concordance_pct="Concordance %")
    rate <- "Concordance_pct"; tone <- "good"; minden <- "Both"; thr <- 15
    dord <- function(d) d[order(d[[rate]]), ]     # lowest concordance (most divergence) first
  } else {
    ccA <- c(Item="Instrument item", Tasks="Tasks", Adjudicated="Adjudicated",
             Upheld="Upheld a reviewer", Overrode="Overrode both", Unresolved="Unresolved",
             Overrode_pct="Overrode both %")
    ccD <- c(Item="Instrument item", Tasks="Tasks", Adjudicated="Adjudicated",
             Overrode="Overrode both", Overrode_pct="Overrode both %")
    scA <- c(Item="Instrument item", Task="Task", Adjudicated="Adjudicated",
             Upheld="Upheld a reviewer", Overrode="Overrode both", Unresolved="Unresolved",
             Overrode_pct="Overrode both %")
    scD <- c(Item="Instrument item", Task="Task", Adjudicated="Adjudicated",
             Overrode="Overrode both", Overrode_pct="Overrode both %")
    rate <- "Overrode_pct"; tone <- "warn"; minden <- "Resolved"; thr <- 15
    dord <- function(d) d[order(-d[[rate]]), ]
  }
  pctc <- rate
  cD <- coll[coll[[minden]] >= thr, ];  sD <- strat[strat[[minden]] >= thr, ]

  out <- c(out, '<p class="subh">Collapsed across study tasks, in tool order</p>',
    T(coll, ccA, pctc = pctc, wrap = "Item", bar = rate, bartone = tone, group = "Domain"))
  out <- c(out, '<p class="subh">Collapsed across study tasks, ranked</p>',
    T(dord(cD), ccD, pctc = pctc, wrap = "Item", bar = rate, bartone = tone,
      note = paste0("Same rows as above, re-sorted; items with at least ", thr,
      " in the denominator column.")))
  out <- c(out, '<p class="subh">Split by study task, in tool order</p>',
    T(strat, scA, pctc = pctc, wrap = "Item", bar = rate, bartone = tone, group = "Domain"))
  out <- c(out, '<p class="subh">Split by study task, ranked</p>',
    T(dord(sD), scD, pctc = pctc, wrap = "Item", bar = rate, bartone = tone,
      note = paste0("Task-specific rows, re-sorted; items with at least ", thr,
      " in the denominator column.")))
  paste(out, collapse = "")
}

## -- 03 by item
add('<section><div class="shead"><span class="snum">03</span><div>',
    '<h2>Disagreement by instrument item</h2></div></div>')
add('<div class="col"><p>This is where the process earns its keep. Disagreement is not spread ',
    'evenly across the instrument; it concentrates in a handful of items, and those items are ',
    'exactly the ones that call for interpretation rather than extraction. Recusal and study task ',
    'were near-unanimous; the qualitative bias-discussion item and the measurement-validity items ',
    'were close to coin-flips. Each item is shown first collapsed across every study task it appears ',
    'in (so "Study design" pools the descriptive, predictive, and causal versions), then split by ',
    'task. Within each view the items run in tool order (task, design, Saudi population, then the ',
    'bias domains), followed by the same rows ranked by disagreement.</p></div>')
PART <- sum(tab$dis_collapsed$Partial)
add('<div class="col"><p>One nuance matters for the four <em>select all that apply</em> questions ',
    '(baseline confounding method, time-varying confounding method, how confounders were selected, ',
    'and errors mentioned in the discussion): two reviewers can tick overlapping but not identical ',
    'sets of options. Those cells are broken out below as <strong>partial agreement</strong>, ',
    'separate from a clean conflict where the two shared no option at all. There were ', n(PART),
    ' such partial-agreement cells in total. They were still routed to adjudication, because ',
    'resolution required an exact match, not merely an overlap; for every single-select question ',
    'this column is zero by construction.</p></div>')
add('<p class="note" style="margin-bottom:4px">Tasks column: D = Descriptive, P = Predictive, ',
    'C = Causal; "All" means the item is asked in all three branches. Among cells both reviewers ',
    'answered: <strong>Full agreement</strong> = identical answer; <strong>Partial agreement</strong> ',
    '= shared at least one option but not the whole set (select-all items only); ',
    '<strong>Conflicting answers</strong> = no shared option. <strong>Applicability disputes</strong> ',
    '= one answered while the other marked the item not applicable.</p>')
add(item_block(tab$dis_collapsed, tab$dis_strat, "dis"))
add('</section>')

## -- 04 workload
add('<section><div class="shead"><span class="snum">04</span><div>',
    '<h2>How the workload landed on individual papers</h2></div></div>')
add('<div class="grid2"><div>',
    T(setNames(tab$paper_dist, names(tab$paper_dist)),
      c(Task="Task", Papers="Papers", Papers_with_0="Papers with none",
        Total_adjudicated="Total adjudicated", Min="Min", Q1="Q1", Median="Median",
        Q3="Q3", Max="Max", Mean="Mean", Mean_pct_of_items="Mean % of items"),
      pctc = "Mean_pct_of_items"), '</div>')
add('<div>', T(tab$paper_hist, c(Items_adjudicated="Items adjudicated", Papers="Papers", Pct="%"),
      pctc = "Pct", bar = "Pct"), '</div></div>')
add('<div class="col"><p>Half of all papers needed five or fewer items adjudicated, but the tail ',
    'is long: four papers required more than 30 separate rulings each. ', n(NOADJ), ' papers came ',
    'through with both reviewers in complete agreement and were never adjudicated at all.</p></div>')
add('</section>')

## -- 05 phase I
add('<section><div class="shead"><span class="snum">05</span><div>',
    '<h2>Phase I: Talal and Yasser ruling independently</h2></div></div>')
add('<div class="col"><p>Every routed cell went to both adjudicators, who ruled without seeing each ',
    'other', "'", 's call. They reached the same answer on ', n(CONC), ' of the ', n(BOTH),
    ' cells both ruled on, that is ', p1(round(100*CONC/BOTH,1)), '. That figure is worth sitting ',
    'with: two senior epidemiologists, looking at the same two reviewer answers and the same paper, ',
    'independently arrived at different conclusions a third of the time. It is the strongest single ',
    'argument for having run phase II at all.</p></div>')
add(T(setNames(tab$phase1, c("Measure","n","pct")),
      c(Measure="Measure", n="Cells", pct="% of routed"), pctc = "pct"))
add('<div class="grid2"><div><h3>Phase I concordance by task</h3>',
    T(setNames(tab$phase1_task, names(tab$phase1_task)),
      c(Task="Task", Both_adjudicated="Both ruled", Concordant="Concordant",
        Discordant="Discordant", Concordance_pct="Concordance %"),
      pctc = "Concordance_pct", cls = "tot"), '</div>')
add('<div><h3>Each adjudicator against the two reviewers</h3>',
    T(setNames(tab$phase1_independent, names(tab$phase1_independent)),
      c(Adjudicator="Adjudicator", Cells_adjudicated="Cells ruled", Upheld_first="Upheld first",
        Upheld_second="Upheld second", Overrode_both="Overrode both",
        Upheld_first_pct="Upheld first %", Upheld_second_pct="Upheld second %",
        Overrode_both_pct="Overrode both %"),
      pctc = c("Upheld_first_pct","Upheld_second_pct","Overrode_both_pct")),
    '<p class="note">Talal introduced a third answer more often than Yasser (',
    p1(tab$phase1_independent$Overrode_both_pct[1]), ' versus ',
    p1(tab$phase1_independent$Overrode_both_pct[2]), '), a stable difference in how readily each ',
    'was willing to reject both reviewers outright.</p></div></div>')
add('<h3>Where the two adjudicators diverged, by item</h3>')
add('<div class="col"><p>Concordance is how often Talal and Yasser reached the same call ',
    'independently; a low value marks the items where even the adjudicators saw the evidence ',
    'differently. Same layout as section 03: collapsed then split by task, tool order then ranked.</p></div>')
add(item_block(tab$ph1_collapsed, tab$ph1_strat, "ph1"))
add('</section>')

## -- 06 phase II
add('<section><div class="shead"><span class="snum">06</span><div>',
    '<h2>Phase II: the joint pass</h2></div></div>')
add('<div class="col"><p>', n(P2N), ' cells across ', n(P2P), ' papers went to a joint sitting, and ',
    'every one of them was resolved. Most arrived because phase I disagreed; ', n(P2$n[6]),
    ' arrived because only one adjudicator had recorded a call and the pair chose to settle it ',
    'together rather than let one voice stand alone.</p></div>')
add('<div class="grid2"><div>', T(setNames(tab$phase2, c("Measure","n")),
      c(Measure="Measure", n="Cells")), '</div>')
add('<div>', T(setNames(tab$phase2_task, names(tab$phase2_task)),
      c(Task="Task", Routed_to_adjudication="Routed", Into_phase_II="Into phase II",
        Pct_of_routed="% of routed", Agreed_with_TA="Settled on Talal's call",
        Agreed_with_YA="Settled on Yasser's call", New_answer="New answer"),
      pctc = "Pct_of_routed", cls = "tot"), '</div></div>')
add('<div class="callout warn"><h3>Phase II did not split the difference</h3>',
    '<p>Of the ', n(P2N), ' cells settled jointly, ', n(P2TA), ' landed on the position Talal had ',
    'taken in phase I and ', n(P2YA), ' on Yasser', "'", 's, with ', n(P2NEW), ' resolving to ',
    'something neither had written down. That asymmetry is a real feature of the record and should ',
    'be reported as such: joint discussion converged on one adjudicator', "'", 's prior call ',
    'substantially more often than the other', "'", 's. It cannot be determined from the data ',
    'whether that reflects persuasion, differing confidence, or genuine differences in accuracy.</p></div>')
add('</section>')

## -- 07 final vs reviewers
add('<section><div class="shead"><span class="snum">07</span><div>',
    '<h2>Did the final call reproduce a reviewer', "'", 's answer, or override both?</h2></div></div>')
add('<div class="col"><p>This is the question that decides whether adjudication was bookkeeping or ',
    'judgement. In ', p1(round(100*UPHELD/RESOLVED,1)), ' of resolved disputes the adjudicators ',
    'picked one of the two answers in front of them. In the remaining ', n(OVER), ' cells (',
    p1(round(100*OVER/RESOLVED,1)), ') they rejected both and recorded a third answer, meaning ',
    'neither reviewer had got that cell right.</p></div>')
add('<div class="grid2"><div>', T(setNames(tab$verdict_head, c("Measure","n","pct")),
      c(Measure="Measure", n="Cells", pct="%"), pctc = "pct"), '</div>')
add('<div>', T(setNames(tab$verdict, c("Verdict","n","pct")),
      c(Verdict="Verdict", n="Cells", pct="% of routed"), pctc = "pct"), '</div></div>')
add('<h3>By task</h3>')
add(T(setNames(tab$verdict_task, names(tab$verdict_task)),
      c(Task="Task", Adjudicated="Adjudicated", Upheld_first="Upheld first",
        Upheld_second="Upheld second", Overrode_both="Overrode both", Unresolved="Unresolved",
        Upheld_a_reviewer_pct="Upheld a reviewer %", Overrode_both_pct="Overrode both %"),
      pctc = c("Upheld_a_reviewer_pct","Overrode_both_pct")))
add('<h3>By item: where the adjudicators most often rejected both reviewers</h3>')
add('<div class="col"><p>"Overrode both" is a cell where the final answer matched neither reviewer. ',
    'Same layout as section 03: collapsed then split by task, tool order then ranked.</p></div>')
add(item_block(tab$vd_collapsed, tab$vd_strat, "vd"))
add('</section>')

## -- 08 blinding
add('<section><div class="shead"><span class="snum">08</span><div>',
    '<h2>The blinding, and what these numbers can and cannot tell us about it</h2></div></div>')
add('<div class="col"><p>The adjudicators saw both reviewers', "'", ' answers but not their ',
    'identities, and did not know which reviewers had been assigned to any given paper. A natural ',
    'check is whether the final call landed on the first and second reviewer columns equally often. ',
    'It does not: the lean toward the second column is small but statistically clear, and it appears ',
    'in Talal', "'", 's and Yasser', "'", 's independent phase-I calls as well as in the final ',
    'record.</p></div>')
add(T(setNames(tab$position, names(tab$position)),
      c(Stage="Stage", First="Upheld first", Second="Upheld second", Pct_first="% first",
        p_value="p (binomial vs 50%)", CI_low="95% CI low", CI_high="95% CI high"),
      pctc = c("Pct_first","CI_low","CI_high")))
add('<div class="callout warn"><h3>That lean is not evidence of a blinding failure</h3>',
    '<p>The &ldquo;first&rdquo; and &ldquo;second&rdquo; reviewer columns are not an arbitrary ',
    'ordering. They are sorted by reviewer number, so reviewer&nbsp;1 occupies the first column on ',
    '100% of their papers and reviewer&nbsp;13 on none of theirs, with a smooth gradient in between. ',
    'Column position and reviewer identity are therefore <em>confounded by construction</em>. Since ',
    'the per-reviewer rate at which an answer was upheld ranges from ',
    p1(min(tab$reviewer$Upheld_pct)), ' to ', p1(max(tab$reviewer$Upheld_pct)),
    ', ordinary differences between reviewers are more than sufficient to produce the observed split ',
    'with no positional effect whatsoever. The two explanations cannot be separated in this design. ',
    'The column order is also not a submission-time artefact: the first column holds the earlier ',
    'submission only 53.8% of the time, near chance.</p></div>')
add('<h3>Which column each reviewer occupied</h3>')
## Reviewer numbers here are the DISPLAY numbers 1..13 assigned in the analysis script:
## fourteen reviewers were recruited and one withdrew before data collection, so the
## source workbooks' identifiers run 1,2,4..14.  Reviewer_original carries the source
## identifier and is deliberately NOT rendered.
add(T(setNames(tab$slot, names(tab$slot)),
      c(Reviewer_No="Reviewer", Papers="Papers", In_first_slot="In first column",
        In_second_slot="In second column", Pct_first="% first"),
      pctc = "Pct_first", bar = "Pct_first"))
add('</section>')

## -- 09 reviewers section removed (2026-07-25, user request): the per-reviewer
##    upheld-rate table was dropped so it cannot read as a reviewer quality ranking.

add('<footer>Assessment of Healthcare Research Quality in Saudi Arabia &middot; ',
    'reviewer-agreement and adjudication audit &middot; N = 385 papers, ', n(TOT), ' cells &middot; ',
    'two blinded adjudicators &middot; rebuilt 8 August 2026 on the 385 dataset. ',
    'The 8 batch-6 papers (39 disagreed cells) were resolved in a single joint adjudicator session, ',
    'so they are recorded as concordant (both adjudicators on the joint value) rather than via the ',
    'independent two-phase process; they are 1.7% of adjudicated cells.</footer>')
add('</div>')

## final anonymization safety net: catch any adjudicator name that survived in
## table cells baked into data/adjudication/process-tables/tables.rds or in prose (Adjudicator 1 = TA, Adjudicator 2 = YA)
S <- gsub("Talal",  "Adjudicator 1", S, fixed = TRUE)
S <- gsub("Yasser", "Adjudicator 2", S, fixed = TRUE)

writeLines(paste(S, collapse = "\n"), HTML)
bad <- grepl("[^\x01-\x7F]", readLines(HTML, warn = FALSE))
stopifnot(!any(bad))
raw <- paste(readLines(HTML, warn = FALSE), collapse = " ")
stopifnot(!grepl("mdash|ndash", raw))                 # no dash entities
stopifnot(!grepl("\\bTA\\b|\\bYA\\b", raw))            # initials fully spelled out
stopifnot(!grepl("Talal|Yasser", raw))                # adjudicators anonymized
stopifnot(!grepl("The reviewers", raw))               # section 09 removed
cat("[written]", HTML, "(", round(file.size(HTML)/1024), "KB ) ASCII clean, adjudicators anonymized, reviewers section removed\n")

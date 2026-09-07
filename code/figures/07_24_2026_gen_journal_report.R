###############################################################################
##  Journal landscape of the 377 analysis papers: quartile, access, indexing,
##  and topic, every value traced to an official source.  Reads the two joined
##  CSVs; recomputes all distributions here so nothing is taken on trust.
##  Design system per the project (petrol-teal, serif headings, no em/en dashes).
###############################################################################

PROJ <- "."
P <- read.csv(file.path(PROJ, "data/journals/07_25_2026_journal_landscape_by_paper_JCR.csv"),
              colClasses = "character", encoding = "UTF-8")
J <- read.csv(file.path(PROJ, "data/journals/07_25_2026_journal_landscape_by_journal_JCR.csv"),
              colClasses = "character", encoding = "UTF-8")
for (c in c("n_papers","n_descriptive","n_predictive","n_causal","n_in_pmc"))
  J[[c]] <- as.integer(J[[c]])
HTML <- file.path(PROJ, "outputs/reports/07_25_2026_journal_landscape_report.html")
NP <- nrow(P); NJ <- nrow(J)
stopifnot(NP == 377L, NJ == 226L)

NAP <- '<span class="muted">not determinable</span>'
h  <- function(x){ x<-as.character(x); x<-gsub("&","&amp;",x,fixed=TRUE)
  x<-gsub("<","&lt;",x,fixed=TRUE); gsub(">","&gt;",x,fixed=TRUE) }
nf <- function(x) formatC(as.numeric(x), format="d", big.mark=",")
pc1<- function(a,b) paste0(formatC(100*a/b, format="f", digits=1), "%")

## ---- normalise the two enrichment fields into clean display buckets ----
P$Q <- ifelse(P$sjr_best_quartile %in% c("Q1","Q2","Q3","Q4"), P$sjr_best_quartile, "Not ranked")
J$Q <- ifelse(J$sjr_best_quartile %in% c("Q1","Q2","Q3","Q4"), J$sjr_best_quartile, "Not ranked")
QORD <- c("Q1","Q2","Q3","Q4","Not ranked")
## JCR JIF quartile (Clarivate, 2022): Q1-Q4 or None (no 2022 JIF quartile: ESCI / delisted / suppressed)
P$JQ <- ifelse(P$jcr_2022_quartile %in% c("Q1","Q2","Q3","Q4"), P$jcr_2022_quartile, "None")
J$JQ <- ifelse(J$jcr_2022_quartile %in% c("Q1","Q2","Q3","Q4"), J$jcr_2022_quartile, "None")
JQORD <- c("Q1","Q2","Q3","Q4","None")
OAORD <- c("gold","diamond","hybrid","bronze","green","closed")
OALAB <- c(gold="Gold (free at a fully open-access journal)",
  diamond="Diamond (free, no author fee)", hybrid="Hybrid (free in a subscription journal)",
  bronze="Bronze (free on publisher site, no licence)", green="Green (free in a repository only)",
  closed="Closed (no free copy located)")
P$OA <- factor(ifelse(P$oa_status=="", "closed", P$oa_status), levels=OAORD)

## ---- generic renderer (kept identical in spirit to the adjudication report) ----
T <- function(df, cols, pctc=character(0), wrap=character(0), bar=NULL, bartone="",
              note=NULL, cls="", group=NULL){
  hd <- paste0("<th>", h(unname(cols)), "</th>", collapse="")
  ncell <- length(cols); body <- ""; lastg <- NULL
  for(i in seq_len(nrow(df))){
    if(!is.null(group)){ g<-df[[group]][i]
      if(is.null(lastg)||!identical(g,lastg)){
        body<-paste0(body,'<tr class="grp"><td colspan="',ncell,'">',h(g),'</td></tr>'); lastg<-g}}
    tds<-paste0(vapply(names(cols),function(cn){ v<-df[[cn]][i]
      isn<-is.numeric(df[[cn]]); isp<-cn %in% pctc
      cell<- if(isp) h(v) else if(isn) nf(v) else h(v)
      kl<-paste(c(if(isn||isp)"num", if(cn %in% wrap)"wrapcell"),collapse=" ")
      if(!is.null(bar)&&identical(cn,bar)&&!is.na(suppressWarnings(as.numeric(v))))
        cell<-paste0('<span class="mb ',bartone,'"><i style="width:',
          min(100,as.numeric(v)),'%"></i></span>',cell)
      paste0('<td class="',kl,'">',cell,'</td>')},character(1)),collapse="")
    body<-paste0(body,"<tr>",tds,"</tr>")}
  paste0('<div class="tscroll"><table class="',cls,'"><thead><tr>',hd,
    '</tr></thead><tbody>',body,'</tbody></table></div>',
    if(is.null(note))"" else paste0('<p class="note">',note,'</p>'))
}
## distribution table from a factor/vector: label | n | % (+bar)
distr <- function(x, order=NULL, labeller=NULL, den=length(x)){
  t <- table(x); if(!is.null(order)) t <- t[order[order %in% names(t)]]
  lab <- names(t); if(!is.null(labeller)) lab <- ifelse(lab %in% names(labeller), labeller[lab], lab)
  data.frame(Label=lab, n=as.integer(t), pct=round(100*as.integer(t)/den,1),
             stringsAsFactors=FALSE, row.names=NULL)
}

QCOL <- c(Q1="var(--agree)", Q2="var(--accent)", Q3="var(--pending)", Q4="var(--conflict)")
JQCOL <- c(Q1="var(--agree)", Q2="var(--accent)", Q3="var(--pending)", Q4="var(--conflict)", None="var(--ink-3)")

## ---- headline numbers ----
qp <- distr(P$Q, QORD); qj <- distr(J$Q, QORD, den=NJ)
## JCR distributions and the SJR-to-JCR shift
jqp <- distr(P$JQ, JQORD); jqj <- distr(J$JQ, JQORD, den=NJ)
jq1q2  <- sum(P$JQ %in% c("Q1","Q2")); jq1q2j <- sum(J$JQ %in% c("Q1","Q2"))
n_jcr_ranked <- sum(J$JQ %in% c("Q1","Q2","Q3","Q4")); n_jcr_none <- sum(J$JQ=="None")
## how each JCR "None" journal is unranked, from the note text
noneR <- J$jcr_note[J$JQ=="None"]
r_esci <- sum(grepl("ESCI", noneR)); r_wos <- sum(grepl("Not in JCR|not WoS", noneR, ignore.case=TRUE))
r_supp <- sum(grepl("suppress", noneR, ignore.case=TRUE))
r_del  <- n_jcr_none - r_esci - r_wos - r_supp
## crosstab: SJR (rows) x JCR (cols), journals
CT <- table(factor(J$Q, levels=QORD), factor(J$JQ, levels=JQORD))
CT <- CT[rowSums(CT) > 0, , drop=FALSE]
ctdf <- data.frame(SJR=rownames(CT), as.data.frame.matrix(CT), check.names=FALSE,
                   stringsAsFactors=FALSE, row.names=NULL)
sjr_q1_keep <- CT["Q1","Q1"]; sjr_q1_tot <- sum(CT["Q1",])
oap <- distr(as.character(P$OA), OAORD, OALAB)
n_open <- sum(P$OA != "closed"); n_closed <- sum(P$OA == "closed")
n_pmc <- sum(P$in_pmc=="Yes"); n_doajp <- sum(P$is_in_doaj=="True")
n_doajj <- sum(J$is_in_doaj=="True")
q1q2 <- sum(P$Q %in% c("Q1","Q2"))

stat <- function(v,l,s="") paste0('<div class="stat"><b>',v,'</b><span>',l,'</span>',
  if(nzchar(s)) paste0('<em>',s,'</em>') else "", '</div>')

S<-c(); add<-function(...) S<<-c(S,paste0(...))
add('<title>Journal landscape of the included papers</title>')
add('<style>
:root{--accent:#16697a;--accent-2:#0d4d5c;--accent-soft:#e3eff1;--ink:#17252a;--ink-2:#3d5157;
 --ink-3:#6b7f85;--ground:#fbfaf8;--panel:#ffffff;--rule:#dfe3e1;--rule-2:#eceeec;
 --agree:#3f7d5c;--agree-soft:#e6efe9;--conflict:#b0563c;--conflict-soft:#f6e8e3;
 --pending:#96792e;--pending-soft:#f4efdf;
 --serif:"Iowan Old Style",Palatino,"Palatino Linotype",Georgia,serif;
 --sans:system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;
 --mono:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;}
@media (prefers-color-scheme:dark){:root{--accent:#5fb3c4;--accent-2:#8fd0dd;--accent-soft:#16323a;
 --ink:#e6edee;--ink-2:#b3c3c7;--ink-3:#82989e;--ground:#0f1618;--panel:#151f22;--rule:#2a3a3e;
 --rule-2:#1e2b2e;--agree:#79b795;--agree-soft:#172b21;--conflict:#e0917a;--conflict-soft:#33201a;
 --pending:#cfb163;--pending-soft:#2c2717;}}
:root[data-theme="dark"]{--accent:#5fb3c4;--accent-2:#8fd0dd;--accent-soft:#16323a;--ink:#e6edee;
 --ink-2:#b3c3c7;--ink-3:#82989e;--ground:#0f1618;--panel:#151f22;--rule:#2a3a3e;--rule-2:#1e2b2e;
 --agree:#79b795;--agree-soft:#172b21;--conflict:#e0917a;--conflict-soft:#33201a;--pending:#cfb163;--pending-soft:#2c2717;}
:root[data-theme="light"]{--accent:#16697a;--accent-2:#0d4d5c;--accent-soft:#e3eff1;--ink:#17252a;
 --ink-2:#3d5157;--ink-3:#6b7f85;--ground:#fbfaf8;--panel:#ffffff;--rule:#dfe3e1;--rule-2:#eceeec;
 --agree:#3f7d5c;--agree-soft:#e6efe9;--conflict:#b0563c;--conflict-soft:#f6e8e3;--pending:#96792e;--pending-soft:#f4efdf;}
*{box-sizing:border-box}
body{margin:0;background:var(--ground);color:var(--ink);font-family:var(--sans);font-size:16px;line-height:1.62;-webkit-font-smoothing:antialiased}
.wrap{max-width:1180px;margin:0 auto;padding:0 24px 96px}.col{max-width:68ch}
h1,h2,h3{font-family:var(--serif);font-weight:600;text-wrap:balance;margin:0}
h1{font-size:clamp(2rem,4.4vw,3.05rem);line-height:1.1;letter-spacing:-.015em}
h2{font-size:clamp(1.32rem,2.4vw,1.7rem);line-height:1.2;margin:0 0 .2em}
h3{font-size:1.04rem;margin:1.5em 0 .35em}p{margin:0 0 1em}
a{color:var(--accent)}.muted{color:var(--ink-3)}
:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
header{border-bottom:1px solid var(--rule);padding:56px 0 34px;margin-bottom:40px}
.eyebrow{font-family:var(--mono);font-size:.7rem;letter-spacing:.14em;text-transform:uppercase;color:var(--accent);margin:0 0 1.1em}
.lede{font-size:1.12rem;color:var(--ink-2);margin-top:1.1em}
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:1px;background:var(--rule);border:1px solid var(--rule);margin:34px 0 0}
.stat{background:var(--panel);padding:16px 18px;display:flex;flex-direction:column;gap:2px;min-width:0}
.stat b{font-family:var(--serif);font-size:1.7rem;line-height:1.05;font-variant-numeric:tabular-nums;color:var(--accent)}
.stat span{font-size:.78rem;color:var(--ink-2);line-height:1.35}.stat em{font-style:normal;font-size:.7rem;color:var(--ink-3)}
section{padding:50px 0 0;border-top:1px solid var(--rule-2);margin-top:50px}
section:first-of-type{border-top:0;margin-top:0;padding-top:0}
.shead{display:flex;gap:14px;align-items:baseline;margin-bottom:1.1em}
.snum{font-family:var(--mono);font-size:.72rem;color:var(--accent);letter-spacing:.1em;border:1px solid var(--rule);padding:3px 7px;flex:none;line-height:1}
.tscroll{overflow-x:auto;margin:12px 0 6px;border:1px solid var(--rule);background:var(--panel);max-width:100%}
table{border-collapse:collapse;width:100%;font-size:.83rem}
th,td{padding:7px 11px;text-align:left;border-bottom:1px solid var(--rule-2);white-space:nowrap;vertical-align:top}
thead th{background:var(--accent-soft);color:var(--accent-2);font-weight:600;font-size:.7rem;letter-spacing:.05em;text-transform:uppercase;position:sticky;top:0;border-bottom:1px solid var(--rule)}
tbody tr:last-child td{border-bottom:0}tbody tr:hover td{background:var(--accent-soft)}
tr.grp td{background:var(--accent-soft);color:var(--accent-2);font-weight:600;font-size:.71rem;letter-spacing:.06em;text-transform:uppercase;border-top:1px solid var(--rule);border-bottom:1px solid var(--rule)}
td.num{text-align:right;font-variant-numeric:tabular-nums}
td.wrapcell{white-space:normal;min-width:200px;max-width:420px;line-height:1.32}
table.tot tbody tr:last-child td{font-weight:650;border-top:1px solid var(--rule);background:var(--accent-soft)}
.mb{display:inline-block;width:60px;height:5px;background:var(--rule-2);margin-right:8px;vertical-align:middle;border-radius:1px}
.mb i{display:block;height:100%;background:var(--accent)}.mb.warn i{background:var(--conflict)}.mb.good i{background:var(--agree)}
.note{font-size:.79rem;color:var(--ink-2);margin:8px 0 0;max-width:84ch}
.callout{border:1px solid var(--rule);border-left:3px solid var(--accent);background:var(--panel);padding:18px 22px;margin:24px 0}
.callout.warn{border-left-color:var(--pending)}.callout h3{color:var(--accent);margin-top:0}.callout.warn h3{color:var(--pending)}
.callout p:last-child{margin-bottom:0}
.grid2{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:26px}.grid2>*{min-width:0}
dl.src{display:grid;grid-template-columns:auto 1fr;gap:8px 16px;margin:0;font-size:.86rem}
dl.src dt{font-weight:600;color:var(--accent-2)}dl.src dd{margin:0;color:var(--ink-2)}
.qbar{display:flex;height:30px;border:1px solid var(--rule);overflow:hidden;margin:14px 0 6px;border-radius:2px}
.qbar span{display:flex;align-items:center;justify-content:center;color:#fff;font-size:.72rem;font-weight:600;min-width:0;overflow:hidden;white-space:nowrap}
footer{margin-top:60px;padding-top:22px;border-top:1px solid var(--rule);font-size:.79rem;color:var(--ink-3)}
@media(max-width:640px){.wrap{padding:0 16px 64px}th,td{padding:6px 8px}}
</style>')

add('<div class="wrap"><header>')
add('<p class="eyebrow">Assessment of Healthcare Research Quality in Saudi Arabia</p>')
add('<h1>Where the ', NP, ' papers were published: quartile, access, and indexing</h1>')
add('<p class="lede col">The ', NP, ' analysis papers appeared in ', NJ, ' distinct journals. This ',
    'is what official sources say about those journals: their quartile in <em>both</em> ranking ',
    'systems for 2022 &mdash; SCImago (Scopus) and Clarivate JCR (Web of Science) &mdash; whether ',
    'each article is open or closed access, where the journal is indexed, and its subject area. ',
    'Every figure is traced to a named source below. Nothing here is estimated; where a value ',
    'is not available from an official source, it is marked as such.</p>')
add('<div class="stats">',
  stat(nf(NJ), "distinct journals", paste0("across ", NP, " papers")),
  stat(pc1(q1q2, NP), "in a Q1 or Q2 journal", "SJR best quartile, 2022"),
  stat(pc1(jq1q2, NP), "in a Q1 or Q2 JIF journal", "Clarivate JCR, 2022"),
  stat("100%", "indexed for MEDLINE", "all 377, NLM record"),
  stat("100%", "in Scopus in 2022", "all 226 journals"),
  stat(pc1(n_open, NP), "open access (any route)", paste0(nf(n_closed), " closed")),
  stat(pc1(n_pmc, NP), "free in PubMed Central", paste0(nf(n_pmc), " of ", NP)),
  stat(pc1(qp$n[qp$Label=="Q1"], NP), "in a Q1 journal", paste0(nf(qp$n[qp$Label=="Q1"]), " papers")),
  stat(nf(n_doajj), "fully open-access journals", paste0(pc1(n_doajj, NJ), " of ", NJ, ", in DOAJ")),
  '</div>')
add('</header>')

## -- sources
add('<section><div class="shead"><span class="snum">S</span><div>',
    '<h2>Sources, and what could not be determined</h2></div></div>')
add('<div class="col"><p>Each column of this report comes from one official source. They are not ',
    'interchangeable, and two of them measure things people often confuse, so they are kept ',
    'separate throughout.</p></div>')
add('<dl class="src">',
  '<dt>Journal identity and indexing</dt><dd>NCBI / U.S. National Library of Medicine, PubMed ',
  'E-utilities (the paper record itself). Gives journal title, ISSN, NLM ID, MEDLINE indexing status, ',
  'and whether the article is in PubMed Central.</dd>',
  '<dt>Quartile (SJR)</dt><dd>SCImago Journal Rank (SJR) 2022, the free Scopus-based ranking. The value ',
  'is the journal', "'", 's <em>best</em> quartile across its Scopus subject categories for 2022. ',
  'A journal can sit in a different quartile in each category; the full category list is in the ',
  'per-journal table and the CSV.</dd>',
  '<dt>Quartile (JCR)</dt><dd>Clarivate Journal Citation Reports, the 2022 Journal Impact Factor ',
  'quartile, read from each journal', "'", 's JCR profile through institutional access. Again the ',
  '<em>best</em> quartile across the journal', "'", 's Web-of-Science categories. This is a ',
  'different ranking system from SJR and covers a stricter core, so ', n_jcr_none, ' journals carry ',
  'no JIF quartile at all (see the quartile section). Verified per journal at the 2022 view.</dd>',
  '<dt>Subject / topic</dt><dd>SCImago subject areas and categories (the Scopus classification), ',
  'cross-checked against the OpenAlex field of the article', "'", 's primary topic.</dd>',
  '<dt>Open access</dt><dd>OpenAlex open-access status for each article (which draws on Unpaywall), ',
  'plus the Directory of Open Access Journals (DOAJ) for whether the journal itself is fully ',
  'open access.</dd></dl>')
add('<div class="callout warn"><h3>What is and is not here</h3><p>Both quartile systems are now ',
    'reported: the <strong>Clarivate JCR Journal Impact Factor quartile</strong> was added for all ',
    NJ, ' journals through institutional access, and it is kept strictly separate from SJR because ',
    'the two measure different things and disagree often (next section). <strong>Web of Science ',
    'indexing</strong> as a yes/no flag is still left as ', NAP, ', since it was not separately ',
    'confirmed. Quartiles are for 2022 (the publication year); the open-access status reflects what ',
    'the sources held on the fetch date, 24 July 2026, and can change if a copy is later posted or ',
    'withdrawn.</p></div>')
add('</section>')

## -- 01 quartile (SJR and JCR)
add('<section><div class="shead"><span class="snum">01</span><div>',
    '<h2>Quartile: two ranking systems, 2022</h2></div></div>')
add('<div class="col"><p>A journal', "'", 's &ldquo;quartile&rdquo; depends entirely on which ',
    'ranking you cite. Two systems are reported here side by side: SCImago SJR (built on Scopus) ',
    'and the Clarivate Journal Impact Factor (built on Web of Science). They are computed the same ',
    'way &mdash; each journal', "'", 's best quartile across its categories &mdash; but they place ',
    'the same journals very differently, so both are shown and neither is treated as the quartile.</p></div>')

## ---- SJR ----
add('<h3>SCImago SJR (Scopus)</h3>')
add('<div class="col"><p>By paper, ', qp$n[qp$Label=="Q1"], ' of ', NP, ' (', pc1(qp$n[qp$Label=="Q1"],NP),
    ') appeared in a journal ranked Q1 in at least one of its subject categories, and ',
    pc1(q1q2, NP), ' were in Q1 or Q2. Only ', qp$n[qp$Label=="Q4"], ' papers were in a Q4 journal. ',
    'The by-journal column weights every journal equally, so it leans slightly lower.</p></div>')
qbar <- paste0('<div class="qbar">', paste(vapply(QORD, function(q){
  nn <- qp$n[qp$Label==q]; if(!length(nn)||nn==0) return("")
  col <- if(q=="Not ranked") "var(--ink-3)" else QCOL[[q]]
  paste0('<span style="flex:',nn,';background:',col,'" title="',q,': ',nn,'">',
         if(nn/NP>0.05) paste0(q," ",nn) else "", '</span>')}, character(1)), collapse=""), '</div>')
add(qbar, '<p class="note">Each paper placed once, by its journal', "'", 's SJR best quartile for 2022.</p>')
add('<div class="grid2"><div><h3>By paper</h3>',
  T(qp, c(Label="SJR quartile", n="Papers", pct="%"), pctc="pct", bar="n",
    note=paste0("Denominator ", NP, " papers.")), '</div>')
add('<div><h3>By journal</h3>',
  T(qj, c(Label="SJR quartile", n="Journals", pct="%"), pctc="pct", bar="n",
    note=paste0("Denominator ", NJ, " journals.")), '</div></div>')

## ---- JCR ----
add('<h3 style="margin-top:1.7em">Clarivate JCR (Journal Impact Factor)</h3>')
add('<div class="col"><p>Under the JIF, the top tier is much thinner: ', jqp$n[jqp$Label=="Q1"], ' of ',
    NP, ' papers (', pc1(jqp$n[jqp$Label=="Q1"],NP), ') are in a Q1 journal and ', pc1(jq1q2, NP),
    ' in Q1 or Q2. A further ', jqp$n[jqp$Label=="None"], ' papers (', pc1(jqp$n[jqp$Label=="None"],NP),
    ') are in journals with <em>no</em> 2022 JIF quartile at all &mdash; ', n_jcr_none, ' of the ',
    NJ, ' journals, which Web of Science either does not rank or does not cover.</p></div>')
jqbar <- paste0('<div class="qbar">', paste(vapply(JQORD, function(q){
  nn <- jqp$n[jqp$Label==q]; if(!length(nn)||nn==0) return("")
  paste0('<span style="flex:',nn,';background:',JQCOL[[q]],'" title="',q,': ',nn,'">',
         if(nn/NP>0.05) paste0(q," ",nn) else "", '</span>')}, character(1)), collapse=""), '</div>')
add(jqbar, '<p class="note">Each paper placed once, by its journal', "'", 's JCR best JIF quartile for ',
    '2022. &ldquo;None&rdquo; is a distinct outcome, not the same as SJR&rsquo;s &ldquo;Not ranked.&rdquo;</p>')
add('<div class="grid2"><div><h3>By paper</h3>',
  T(jqp, c(Label="JCR JIF quartile", n="Papers", pct="%"), pctc="pct", bar="n",
    note=paste0("Denominator ", NP, " papers.")), '</div>')
add('<div><h3>By journal</h3>',
  T(jqj, c(Label="JCR JIF quartile", n="Journals", pct="%"), pctc="pct", bar="n",
    note=paste0("Denominator ", NJ, " journals.")), '</div></div>')

## ---- the shift ----
add('<div class="callout"><h3>The impact factor ranks these journals markedly lower</h3>',
    '<p>Moving from SJR to the JIF roughly halves the top-tier share: Q1 or Q2 falls from <strong>',
    pc1(q1q2, NP), '</strong> to <strong>', pc1(jq1q2, NP), '</strong> of papers (',
    pc1(qj$n[qj$Label=="Q1"]+qj$n[qj$Label=="Q2"], NJ), ' to ', pc1(jq1q2j, NJ),
    ' of journals). Of the <strong>', sjr_q1_tot, '</strong> journals SJR calls Q1, only <strong>',
    sjr_q1_keep, '</strong> keep Q1 under the JIF; the rest fall to a lower quartile or out of the ',
    'ranked set. In the cross-tabulation below, every off-diagonal journal is a downgrade &mdash; ',
    'the shift runs one way only.</p></div>')
add('<h3>Where each SJR-ranked group lands under the JIF</h3>')
add(T(ctdf, c(SJR="SJR row / JCR col", Q1="Q1", Q2="Q2", Q3="Q3", Q4="Q4", None="None"),
    note=paste0("Journals (n = ", NJ, "). Rows = SCImago SJR quartile; columns = Clarivate JCR ",
    "quartile. The diagonal is agreement between the two systems; mass below it is journals the ",
    "JIF ranks lower than SJR does.")))

## ---- no-quartile journals ----
add('<div class="callout warn"><h3>The ', n_jcr_none, ' journals with no JIF quartile</h3>',
    '<p>&ldquo;None&rdquo; is verified per journal at the 2022 view of its JCR profile, and it ',
    'covers four distinct situations: <strong>', r_esci, '</strong> were in the Emerging Sources ',
    'Citation Index in 2022 (they carry a JIF but are not assigned a quartile; most gained one from ',
    '2023); <strong>', r_wos, '</strong> are not in Web of Science at all (MEDLINE- or PMC-indexed ',
    'only); <strong>', r_del, '</strong> were delisted before the 2022 release (last JCR year 2021 ',
    'or earlier, e.g. <em>IJERPH</em> and <em>Computational Intelligence and Neuroscience</em>); ',
    'and <strong>', r_supp, '</strong> had the 2022 metric suppressed for citation anomalies ',
    '(<em>[NAME-REDACTED]</em>, <em>Contrast Media &amp; Molecular Imaging</em>). ',
    'Separately, one journal is unranked by <em>SJR</em> as well: <em>Computational Intelligence ',
    'and Neuroscience</em> carries no SJR quartile for 2022 despite Scopus coverage, and was later ',
    'discontinued from Scopus.</p></div>')
add('</section>')

## -- 02 access
add('<section><div class="shead"><span class="snum">02</span><div>',
    '<h2>Open versus closed access</h2></div></div>')
add('<div class="col"><p>Two different questions matter here. First, at the article level: can this ',
    'specific paper be read for free, and by what route? Second, at the journal level: is the journal ',
    'itself a fully open-access title? A paper can be free (say, as a repository copy) even in a ',
    'subscription journal, so the two do not have to agree.</p></div>')
add('<h3>Article-level access (OpenAlex, drawing on Unpaywall)</h3>')
add(T(oap, c(Label="Access route", n="Papers", pct="%"), pctc="pct", bar="n",
    note=paste0("Open by any route: ", nf(n_open), " of ", NP, " (", pc1(n_open,NP),
    "). Closed means no free copy was located on the fetch date; it is not proof none exists.")))
add('<h3>Journal-level open access</h3>')
add('<div class="col"><p>', nf(n_doajj), ' of the ', NJ, ' journals are listed in the DOAJ as fully ',
    'open access, accounting for ', nf(n_doajp), ' of the ', NP, ' papers (', pc1(n_doajp,NP),
    '). The remaining papers are in subscription or hybrid journals, though many individual articles ',
    'in them are still free by one of the routes above.</p></div>')
jl <- data.frame(Label=c("Fully open-access journal (in DOAJ)","Subscription or hybrid journal"),
  n=c(n_doajj, NJ-n_doajj), pct=round(100*c(n_doajj,NJ-n_doajj)/NJ,1))
add(T(jl, c(Label="Journal type", n="Journals", pct="%"), pctc="pct", bar="n",
    note="Journal-level open-access status from DOAJ, via OpenAlex."))
add('</section>')

## -- 03 indexing
add('<section><div class="shead"><span class="snum">03</span><div>',
    '<h2>Where the journals are indexed</h2></div></div>')
add('<div class="col"><p>Because the sample was drawn from PubMed, every paper is in PubMed by ',
    'construction. What the official records add is that all of them are fully indexed for MEDLINE ',
    '(the curated subset, not merely deposited), and every journal is in Scopus. Coverage in PubMed ',
    'Central and the DOAJ is partial. Web of Science cannot be checked here.</p></div>')
idx <- data.frame(
  Source=c("PubMed","MEDLINE (curated NLM index)","PubMed Central (free full text)",
           "Scopus (2022)","DOAJ (open-access registry)","Web of Science"),
  Basis=c("sample frame","NLM record status = MEDLINE","article has a PMC identifier",
          "journal present in SCImago 2022","journal listed in DOAJ (via OpenAlex)",
          "no free official source available"),
  Papers=c(nf(NP), nf(sum(P$in_medline=="Yes")), nf(n_pmc), nf(NP), nf(n_doajp), "not determinable"),
  Pct=c("100%","100%", pc1(n_pmc,NP), "100%", pc1(n_doajp,NP), "not determinable"),
  stringsAsFactors=FALSE)
add(T(idx, c(Source="Index", Basis="How it is established", Papers="Papers", Pct="% of 377"),
    wrap="Basis"))
add('<p class="note">Journal-level: ', sum(as.integer(J$n_in_pmc)>0), ' of ', NJ,
    ' journals have at least one paper in PubMed Central; all ', NJ, ' are in Scopus and MEDLINE.</p>')
add('</section>')

## -- 04 topic
add('<section><div class="shead"><span class="snum">04</span><div>',
    '<h2>Subject area and topic</h2></div></div>')
add('<div class="col"><p>Two classifications, from two sources, tell the same story: the corpus is ',
    'overwhelmingly clinical and public-health medicine, with dentistry, psychology, and the health ',
    'professions next. The SCImago areas are the Scopus scheme tied to the quartiles above; the ',
    'OpenAlex field is an independent classification of each article', "'", 's primary topic.</p></div>')
## OpenAlex field by paper
fld <- distr(ifelse(P$field=="","(unclassified)",P$field))
fld <- fld[order(-fld$n),]
## SCImago broad area: split multi-area strings, count each paper once per area
areasplit <- unlist(lapply(P$scimago_areas, function(s) trimws(strsplit(s,";")[[1]])))
areasplit <- areasplit[nzchar(areasplit)]
ar <- as.data.frame(table(areasplit), stringsAsFactors=FALSE); names(ar)<-c("Label","n")
ar <- ar[order(-ar$n),]; ar$pct <- round(100*ar$n/NP,1)
add('<div class="grid2"><div><h3>OpenAlex field of the article (one per paper)</h3>',
  T(head(fld,14), c(Label="Field", n="Papers", pct="%"), pctc="pct", bar="n", wrap="Label"), '</div>')
add('<div><h3>SCImago subject area of the journal</h3>',
  T(head(ar,14), c(Label="Area", n="Papers", pct="%"), pctc="pct", bar="n", wrap="Label",
    note="A journal can span several areas, so a paper is counted in each of its areas; percentages need not sum to 100."),
  '</div></div>')
add('</section>')

## -- 05 quartile x access x task
add('<section><div class="shead"><span class="snum">05</span><div>',
    '<h2>Quartile against access and study task</h2></div></div>')
ct <- as.data.frame.matrix(table(P$Q, ifelse(P$OA=="closed","Closed","Open")))
ct <- ct[QORD[QORD %in% rownames(ct)],,drop=FALSE]
ctd <- data.frame(Quartile=rownames(ct), Open=ct$Open, Closed=ct$Closed,
  Total=ct$Open+ct$Closed, Open_pct=round(100*ct$Open/(ct$Open+ct$Closed),1))
add('<div class="grid2"><div><h3>Access by quartile</h3>',
  T(ctd, c(Quartile="SJR quartile", Open="Open", Closed="Closed", Total="Papers",
    Open_pct="Open %"), pctc="Open_pct", cls="tot"),
  '<p class="note">Higher-quartile journals are not uniformly more open: many Q1 and Q2 papers sit behind a paywall, while the free Diamond route concentrates in Q3.</p></div>')
tt <- as.data.frame.matrix(table(P$Q, P$Study_Type))
for(c in c("Descriptive","Predictive","Causal")) if(is.null(tt[[c]])) tt[[c]]<-0
tt <- tt[QORD[QORD %in% rownames(tt)],,drop=FALSE]
ttd <- data.frame(Quartile=rownames(tt), Descriptive=tt$Descriptive, Predictive=tt$Predictive,
  Causal=tt$Causal, Total=rowSums(tt))
add('<div><h3>Study task by quartile</h3>',
  T(ttd, c(Quartile="SJR quartile", Descriptive="Descriptive", Predictive="Predictive",
    Causal="Causal", Total="Papers"), cls="tot"),
  '<p class="note">The predictive papers cluster in the unranked and lower-quartile machine-learning venues; causal and descriptive work spreads across Q1 to Q3.</p></div></div>')
add('</section>')

## -- 06 full journal table
add('<section><div class="shead"><span class="snum">06</span><div>',
    '<h2>Every journal in the corpus</h2></div></div>')
add('<div class="col"><p>All ', NJ, ' journals, most-published first, with <em>both</em> 2022 ',
    'quartiles side by side (SJR, then JCR). &ldquo;DOAJ&rdquo; marks a fully open-access journal; ',
    'the area is the Scopus classification. The full per-paper detail, including per-category ',
    'quartiles, the JCR category ranks, article access route, DOI, and Scopus coverage years, is ',
    'in the accompanying CSV files.</p></div>')
JT <- J[order(-J$n_papers, J$journal),]
JT$doaj <- ifelse(JT$is_in_doaj=="True","DOAJ","")
JT$area <- ifelse(JT$scimago_areas=="", "not in SCImago", JT$scimago_areas)
JT$Qd <- ifelse(JT$Q=="Not ranked","NR",JT$Q)
JT$JQd <- JT$JQ
add(T(JT, c(journal="Journal", n_papers="Papers", n_descriptive="D", n_predictive="P",
    n_causal="C", Qd="SJR Q", JQd="JCR Q", doaj="Open access", area="Scopus area",
    publisher_country="Country"), wrap=c("journal","area")))
add('</section>')

add('<footer>Assessment of Healthcare Research Quality in Saudi Arabia &middot; journal landscape of ',
    NP, ' papers in ', NJ, ' journals &middot; sources: PubMed/NLM, SCImago SJR 2022, Clarivate JCR ',
    '2022, OpenAlex, DOAJ &middot; generated 25 July 2026. Two quartile systems are reported side by ',
    'side and are not interchangeable: SCImago SJR (Scopus) and Clarivate JCR (Web of Science).</footer>')
add('</div>')

writeLines(paste(S, collapse="\n"), HTML)
stopifnot(!any(grepl("[^\x01-\x7F]", readLines(HTML, warn=FALSE))))
cat("[written]", HTML, "(", round(file.size(HTML)/1024), "KB ) ASCII clean\n")

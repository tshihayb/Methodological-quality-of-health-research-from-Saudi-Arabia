# Stratified quality analysis, SPLIT BY TASK (descriptive vs causal).
# Run: & "C:\Program Files\R\R-4.5.2\bin\x64\Rscript.exe" code/scoring/07_30_2026_stratified_analysis.R
#
# ============================================================================================
# ⚠ RE-CUT 2026-08-26 — this script now computes FIGURE 5's measures, stratified.
# ============================================================================================
# It used to emit three numbers per stratifier x level x task: N, mean n_val_flags,
# mean n_rep_gaps.  Figure 6 was built on those, BEFORE Figure 5 was finalised, so it carried
# only two of the seven things Figure 5 reports.  Everything Figure 5 shows is now computed
# here, on the same definitions, so the stratified figure is Figure 5 broken out by group
# rather than a separate analysis that happens to sit beside it.
#
# ⚠ `n_val_flags` is a FLAG COUNT; `error_weighted` is the GRADED severity.  Figure 5 moved to
# the graded quantity on 2026-08-22 because the two measurement-accounting items are scored and
# never pass, so measurement bias flags in ~100% of papers and the count can no longer separate
# anything.  `mean_err_w` is therefore the primary validity axis here; mean_val_err is kept only
# so the older artifact and the pre-re-cut numbers stay reproducible.
#
# DEFINITIONS ARE COPIED FROM code/figures/07_30_2026_gen_results_artifact.py, not re-invented:
#   panel A  four-state verdict   -> scored_domain state, denominator = APPLICABLE cells
#   panel B  additive severity    -> primary items, mean flagged ITEMS per applicable paper
#   panel C  sensitivity band     -> VAL% -> (VAL+REP)% of applicable cells
#   panel D  transparency x validity, cross-classified at the POOLED medians (not per-level
#            medians — a per-level cut-off would move the quadrant boundary with the group and
#            make the four counts incomparable across levels)
#   panel J  acknowledgement by domain -> err_disc free text contains that domain's name
#   panel K  acknowledgement index -> the scorer's own per-paper `acknowledgement`
#
# OUTPUT (data/scoring/)
#   07_30_2026_stratified_summary.csv   stratifier x level x task     (study-level measures)
#   07_30_2026_stratified_domains.csv   ... x domain                  (domain-level measures)
#   07_30_2026_stratified_spread.csv    stratifier x task             (max - min, and where)
#   07_30_2026_stratified_paper_level.csv  one row per scored paper, every measure AND every
#     stratifier level.  Any distribution-shaped display (a ridgeline, a per-level density, a
#     dot strip) needs the per-paper values, and re-deriving the group labels in the figure
#     script is exactly how a figure drifts from its own analysis - so they are exported once,
#     here, from the same merge the summary rows are computed on.
CH <- function(f) read.csv(f, stringsAsFactors=FALSE, colClasses="character", na.strings=character(0))

it  <- CH("data/scoring/07_30_2026_scored_items_long.csv")
dm4 <- CH("data/scoring/07_30_2026_scored_domain.csv")     # character: keep the literal "NA" state
st  <- read.csv("data/scoring/07_30_2026_scored_study.csv", stringsAsFactors=FALSE)
w   <- CH("data/analysis/07_23_2026_ANALYSIS_DATASET_wide.csv"); w <- w[w$Study_Type!="Predictive", ]
jcr <- CH("data/journals/07_25_2026_journal_landscape_by_paper_385_JCR.csv")[, c("PMID","jcr_2022_quartile")]
inst<- CH("data/authors/07_25_2026_saudi_paper_level.csv")[, c("PMID","health_system","multisector")]
ts  <- CH("data/scoring/07_30_2026_team_size_385.csv")[, c("PMID","team_cat")]
# Funding stratifier added 2026-08-26. Read the ADJUDICATED file, not the machine pass:
# TSA's 36 rulings of 2026-08-25 moved 13 papers, so funding_3level_machine (196/102/87)
# is superseded by funding_3level (183/103/99 over the 385).
fnd <- CH("data/analysis/08_25_2026_funding_ADJUDICATED_385.csv")[, c("PMID","funding_3level")]

# ---- stratifier labels ----
w$saudi_data <- ifelse(w$Study_Type=="Causal", w$causal_pop, w$descriptive_pop)
w <- merge(w, jcr, by="PMID", all.x=TRUE)
w$jcr    <- ifelse(is.na(w$jcr_2022_quartile) | w$jcr_2022_quartile=="", "None", w$jcr_2022_quartile)
w$jcrbin <- ifelse(w$jcr %in% c("Q1","Q2"),"Q1-Q2", ifelse(w$jcr %in% c("Q3","Q4"),"Q3-Q4","None"))
w$first_lab <- ifelse(w$first_author_saudi=="1","Saudi","Non-Saudi")
w$last_lab  <- ifelse(w$last_author_saudi=="1","Saudi","Non-Saudi")
w$corr_lab  <- ifelse(w$corresponding_author_saudi=="1","Saudi","Non-Saudi")
# ---- Saudi institution-type stratifiers (from the paper-level sector map) ----
w <- merge(w, inst, by="PMID", all.x=TRUE)
.HEALTH <- c("Hospital / medical city","Hospital & research centre","Ministry of Health","Military & security-forces medical")
w$comp_lab <- ifelse(w$health_system %in% c("True","TRUE","1"), "Health-system","Academic-only")
w$msec_lab <- ifelse(w$multisector %in% c("True","TRUE","1"), "Multi-sector","Single-sector")
w <- merge(w, ts, by="PMID", all.x=TRUE)
# ⚠ "non_funded" is a DECLARED absence of funding, not silence; "not_stated" is the residue
# after that declaration is counted, and is NOT the transparency number (the truly silent
# count is smaller). The level labels below say so, so the figure cannot be misread.
w <- merge(w, fnd, by="PMID", all.x=TRUE)
w$fund_lab <- ifelse(w$funding_3level=="funded","Funded",
               ifelse(w$funding_3level=="non_funded","Declared none",
               ifelse(w$funding_3level=="not_stated","Not stated", NA)))
stopifnot(!any(is.na(w$fund_lab)))
wl <- w[, c("PMID","saudi_data","pct_saudi_ge50","first_lab","last_lab","corr_lab","jcr","jcrbin","comp_lab","msec_lab","team_cat","fund_lab")]

# ---- per paper x domain: applicable / validity flaws / reporting gaps / graded severity ----
pri <- it[it$primary=="TRUE", ]
pri$app <- as.integer(pri$state!="NA"); pri$v <- as.integer(pri$state=="VAL"); pri$r <- as.integer(pri$state=="REP")
pri$sev <- suppressWarnings(as.numeric(pri$severity)); pri$sev[is.na(pri$sev)] <- 0
pdd <- aggregate(cbind(app,v,r,sev) ~ PMID+Study_Type+domain, data=pri, FUN=sum)
# the per-domain severities must add back to the scorer's own study-level error_weighted;
# assert it, or a domain-level severity could drift from the quantity Figure 5 panel F plots
.chk <- aggregate(sev ~ PMID, data=pdd, FUN=sum)
.chk <- merge(.chk, st[, c("PMID","error_weighted")], by="PMID")
stopifnot(max(abs(.chk$sev - .chk$error_weighted)) < 1e-6)
pdd <- merge(pdd, wl, by="PMID")

# ---- the four-state verdict, per paper x domain (panel A / C) ----
d4 <- merge(dm4, wl, by="PMID")

# ---- domains carrying a REPORTING GAP, per paper (Figure 5 panel H) ----
# The scorer exports domains_flagged (VAL domains) but not its reporting counterpart, so this
# is derived here exactly as Figure 5 derives it: count of domains in state REP, over the
# judgeable domains.  The VAL counterpart is recomputed the same way and asserted against the
# scorer's own domains_flagged, which is what pins this definition to Figure 5's.
.jd <- dm4[dm4$state!="NA", ]
.gp <- as.data.frame(table(PMID=.jd$PMID[.jd$state=="REP"]), stringsAsFactors=FALSE)
.fl <- as.data.frame(table(PMID=.jd$PMID[.jd$state=="VAL"]), stringsAsFactors=FALSE)
names(.gp)[2] <- "dom_gapped"; names(.fl)[2] <- "dom_flawed"
st$dom_gapped <- .gp$dom_gapped[match(as.character(st$PMID), .gp$PMID)]
st$dom_gapped[is.na(st$dom_gapped)] <- 0L
.chkf <- .fl$dom_flawed[match(as.character(st$PMID), .fl$PMID)]; .chkf[is.na(.chkf)] <- 0L
stopifnot(identical(as.integer(.chkf), as.integer(st$domains_flagged)))

# ---- author acknowledgement of a named domain (panel J) ----
erd <- it[it$item=="err_disc", c("PMID","raw")]
erd <- setNames(tolower(erd$raw), erd$PMID)
IMAP <- c("Selection bias"="selection bias","Measurement bias"="measurement bias",
          "Confounding bias"="confounding bias","Missing data"="missing data",
          "Random error"="random error")

# ---- study-level frame, with every Figure 5 measure ----
SCOLS <- c("PMID","Study_Type","n_applicable","n_rep_gaps","n_val_flags","error_weighted",
           "transparency","validity","validity_weighted","domains_flagged","dom_gapped",
           "ack_flagged","ack_named","acknowledgement")
st2 <- merge(st[, SCOLS], wl, by="PMID")
# POOLED medians — the Figure 5 panel D cut-offs. Held fixed across levels on purpose.
MT <- median(st$transparency, na.rm=TRUE); MV <- median(st$validity, na.rm=TRUE)

STRATS <- list(
  list(name="Saudi data used",      col="saudi_data",     lv=c("Yes","No")),
  list(name="Number of authors",    col="team_cat",       lv=c("1-2","3-10","11+")),
  list(name="% Saudi authors",      col="pct_saudi_ge50", lv=c(">=50%","<50%")),
  list(name="Corresponding author", col="corr_lab",       lv=c("Saudi","Non-Saudi")),
  list(name="First author",         col="first_lab",      lv=c("Saudi","Non-Saudi")),
  list(name="Last author",          col="last_lab",       lv=c("Saudi","Non-Saudi")),
  list(name="Sector composition",     col="comp_lab", lv=c("Academic-only","Health-system")),
  list(name="Single vs multi-sector", col="msec_lab", lv=c("Single-sector","Multi-sector")),
  list(name="JCR 2022 quartile",    col="jcr",            lv=c("Q1","Q2","Q3","Q4","None")),
  list(name="JCR Q1-2 vs Q3-4",     col="jcrbin",         lv=c("Q1-Q2","Q3-Q4","None")),
  list(name="Funding",              col="fund_lab",       lv=c("Funded","Declared none","Not stated")))
DOMS <- c("Random error","Selection bias","Measurement bias","Confounding bias","Missing data","Mentioning errors","Conflating task")

# ---- per-paper export: every measure beside every stratifier level -----------------------
SCOL <- vapply(STRATS, function(S) S$col, character(1))
pl <- st2[, c(SCOLS, SCOL)]
names(pl)[match(SCOL, names(pl))] <- vapply(STRATS, function(S) S$name, character(1))
stopifnot(nrow(pl) == nrow(st))            # every scored paper carries every stratifier
write.csv(pl, "data/scoring/07_30_2026_stratified_paper_level.csv", row.names=FALSE)

mn <- function(x) if(length(x)) mean(x) else NA_real_
summ <- list(); doms <- list()
for(S in STRATS){ ord<-0
  for(lv in S$lv){ ord<-ord+1
    for(tk in c("Descriptive","Causal")){
      pin <- st2[st2[[S$col]]==lv & st2$Study_Type==tk, ]
      N <- nrow(pin); if(N==0) next
      # panel A / C, pooled over the seven domains: the share of JUDGEABLE study x domain
      # cells that resolve to each state. Denominator = applicable cells, the project's
      # stated convention, so these reconcile with Figure 5's per-domain bars.
      cel <- d4[d4[[S$col]]==lv & d4$Study_Type==tk, ]
      app <- sum(cel$state!="NA")
      nOK <- sum(cel$state=="OK"); nREP <- sum(cel$state=="REP"); nVAL <- sum(cel$state=="VAL")
      # panel D quadrants at the pooled medians
      hiT <- pin$transparency >= MT; hiV <- pin$validity >= MV
      summ[[length(summ)+1]] <- data.frame(stratifier=S$name, level=lv, ord=ord, task=tk, N=N,
        mean_val_err=mean(pin$n_val_flags), mean_rep_gap=mean(pin$n_rep_gaps),
        # --- graded severity: the primary validity axis since 2026-08-22 ---
        mean_err_w=mean(pin$error_weighted), sd_err_w=stats::sd(pin$error_weighted),
        median_err_w=median(pin$error_weighted),
        q25_err_w=unname(quantile(pin$error_weighted,.25)), q75_err_w=unname(quantile(pin$error_weighted,.75)),
        min_err_w=min(pin$error_weighted), max_err_w=max(pin$error_weighted),
        # --- the two indices (panel D) ---
        mean_validity=mean(pin$validity), mean_validity_w=mean(pin$validity_weighted),
        mean_transparency=mean(pin$transparency),
        median_validity=median(pin$validity), median_transparency=median(pin$transparency),
        # --- domains flagged (panel E) and its reporting counterpart (panel H) ---
        mean_dom_flag=mean(pin$domains_flagged), mean_dom_gap=mean(pin$dom_gapped),
        pct_clean=100*mean(pin$domains_flagged==0), pct_ge3=100*mean(pin$domains_flagged>=3),
        # --- SDs for all seven study-level measures, so a display can draw a CI without
        #     going back to the per-paper file (sd_err_w is above, beside its mean) ---
        sd_rep_gap=stats::sd(pin$n_rep_gaps), sd_dom_flag=stats::sd(pin$domains_flagged),
        sd_dom_gap=stats::sd(pin$dom_gapped), sd_validity=stats::sd(pin$validity),
        sd_transparency=stats::sd(pin$transparency),
        sd_ack=stats::sd(pin$acknowledgement[pin$ack_flagged>0]),
        # --- four-state verdict + sensitivity band (panels A, C), pooled over domains ---
        cells_app=app, pct_ok=100*nOK/app, pct_rep=100*nREP/app, pct_val=100*nVAL/app,
        pct_worst=100*(nVAL+nREP)/app,
        # --- acknowledgement (panel K) ---
        n_ack_elig=sum(pin$ack_flagged>0), mean_ack=mn(pin$acknowledgement[pin$ack_flagged>0]),
        pct_ack_none=100*mn(as.numeric(pin$acknowledgement[pin$ack_flagged>0]==0)),
        # --- cross-classification at the pooled medians (panel D) ---
        q_hihi=sum(hiT&hiV), q_hilo=sum(hiT&!hiV), q_lohi=sum(!hiT&hiV), q_lolo=sum(!hiT&!hiV),
        stringsAsFactors=FALSE)
      for(D in DOMS){
        sub <- pdd[pdd[[S$col]]==lv & pdd$Study_Type==tk & pdd$domain==D, ]
        ap <- sub[sub$app>0, ]
        applic <- nrow(ap); vn <- sum(ap$v>0); rn <- sum(ap$r>0)
        # panel J: of the papers FLAGGED in this domain, how many named it in the discussion
        fl <- ap$PMID[ap$v>0]; an <- NA_integer_
        if(D %in% names(IMAP) && length(fl))
          an <- sum(grepl(IMAP[[D]], ifelse(is.na(erd[fl]), "", erd[fl]), fixed=TRUE))
        doms[[length(doms)+1]] <- data.frame(stratifier=S$name, level=lv, ord=ord, task=tk, domain=D,
          applic=applic, val_n=vn, rep_n=rn,
          val_pct=ifelse(applic>0,100*vn/applic,NA), rep_pct=ifelse(applic>0,100*rn/applic,NA),
          # panel B: mean flagged ITEMS per applicable paper, split by axis
          mean_v_items=ifelse(applic>0,mean(ap$v),NA), mean_r_items=ifelse(applic>0,mean(ap$r),NA),
          # graded severity carried by this domain, per applicable paper
          mean_sev=ifelse(applic>0,mean(ap$sev),NA),
          # panel J
          ack_named=an, ack_pct=ifelse(!is.na(an)&vn>0,100*an/vn,NA),
          stringsAsFactors=FALSE)
      }
    }
  }
}
summ <- do.call(rbind, summ); doms <- do.call(rbind, doms)
write.csv(summ, "data/scoring/07_30_2026_stratified_summary.csv", row.names=FALSE)
write.csv(doms, "data/scoring/07_30_2026_stratified_domains.csv", row.names=FALSE)

# ---- spread: how much does each stratifier actually separate? ---------------------------
# ★ This is the headline the per-panel design hid: the whole between-level spread is small.
# One row per stratifier x task x measure, carrying max-min AND which levels sit at the ends,
# so a figure can rank stratifiers by separation without recomputing anything.
MEAS <- c("mean_err_w","mean_val_err","mean_rep_gap","mean_validity","mean_transparency",
          "mean_dom_flag","mean_dom_gap","pct_ge3","pct_val","pct_worst","mean_ack")
sp <- list()
for(S in STRATS) for(tk in c("Descriptive","Causal")){
  s <- summ[summ$stratifier==S$name & summ$task==tk, ]
  if(nrow(s)<2) next
  for(m in MEAS){
    v <- s[[m]]; ok <- !is.na(v); if(sum(ok)<2) next
    v <- v[ok]; l <- s$level[ok]; n <- s$N[ok]
    sp[[length(sp)+1]] <- data.frame(stratifier=S$name, task=tk, measure=m,
      n_levels=length(v), spread=max(v)-min(v),
      lo_level=l[which.min(v)], lo_val=min(v), lo_n=n[which.min(v)],
      hi_level=l[which.max(v)], hi_val=max(v), hi_n=n[which.max(v)],
      task_mean=mean(rep(v,n)), stringsAsFactors=FALSE)
  }
}
sp <- do.call(rbind, sp)
write.csv(sp, "data/scoring/07_30_2026_stratified_spread.csv", row.names=FALSE)

# ---- console ----------------------------------------------------------------------------
cat("== per group x task: graded severity (error_weighted), flag count, reporting gaps ==\n")
for(S in STRATS){ cat("\n",S$name,"\n",sep="")
  s <- summ[summ$stratifier==S$name, ]
  for(i in order(s$ord, s$task)) cat(sprintf("  %-13s %-11s n=%-3d | sev %5.2f | flags %.2f | gaps %.2f | val %.2f | transp %.2f | ack %.2f\n",
      s$level[i], s$task[i], s$N[i], s$mean_err_w[i], s$mean_val_err[i], s$mean_rep_gap[i],
      s$mean_validity[i], s$mean_transparency[i], s$mean_ack[i]))
}
cat("\n== SEPARATION: stratifiers ranked by spread in graded severity (max - min) ==\n")
for(tk in c("Causal","Descriptive")){
  s <- sp[sp$task==tk & sp$measure=="mean_err_w", ]
  s <- s[order(-s$spread), ]
  cat(" ",tk,"\n",sep="")
  for(i in seq_len(nrow(s))) cat(sprintf("    %-22s %5.2f   (%s %.2f n=%d  ->  %s %.2f n=%d)\n",
      s$stratifier[i], s$spread[i], s$lo_level[i], s$lo_val[i], s$lo_n[i],
      s$hi_level[i], s$hi_val[i], s$hi_n[i]))
}
cat(sprintf("\npooled medians used as the panel-D cut-offs: transparency %.4f  validity %.4f\n", MT, MV))
cat("wrote _stratified_summary.csv (", ncol(summ), " cols) / _stratified_domains.csv (", ncol(doms),
    " cols) / _stratified_spread.csv\n", sep="")

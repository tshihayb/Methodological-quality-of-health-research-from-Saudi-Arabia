# Downstream analyses of the 4-state scored dataset: sensitivity bounds, transparency x validity 2x2,
# and the author-insight cross-tab. Reads the three 07_30 scored CSVs + the wide dataset.
# Run: & "C:\Program Files\R\R-4.5.2\bin\x64\Rscript.exe" code/scoring/07_30_2026_analyze_scored.R

# na.strings=character(0) so the literal state "NA" is kept as a string, not read as a missing value
dom <- read.csv("data/scoring/07_30_2026_scored_domain.csv",   stringsAsFactors=FALSE, colClasses="character", na.strings=character(0))
it  <- read.csv("data/scoring/07_30_2026_scored_items_long.csv",stringsAsFactors=FALSE, colClasses="character", na.strings=character(0))
stu <- read.csv("data/scoring/07_30_2026_scored_study.csv",     stringsAsFactors=FALSE)
DOMS <- c("Random error","Selection bias","Measurement bias","Confounding bias",
          "Missing data","Mentioning errors","Conflating task")
fmt <- function(n,N) sprintf("%d (%.1f%%)", n, 100*n/N)

## ---------- (b) SENSITIVITY BOUNDS: how much does the not-reported ruling move each domain? ----------
# LOWER (primary): reporting gaps are NOT validity flaws.  UPPER: every reporting gap counts as a flaw
# (the old "Not reported = bias present" convention). Truth is bracketed between the two.
cat("== sensitivity bounds: % of applicable papers with a VALIDITY problem ==\n")
cat(sprintf("%-20s %14s %14s %14s\n","domain","applicable","primary (any VAL)","upper (VAL+REP)"))
for(dm in DOMS){
  sub <- dom[dom$domain==dm & dom$state!="NA", ]
  N <- nrow(sub); if(N==0) next
  prim  <- sum(sub$state=="VAL")
  upper <- sum(sub$state %in% c("VAL","REP"))
  cat(sprintf("%-20s %14d %14s %14s\n", dm, N, sprintf("%.1f%%",100*prim/N), sprintf("%.1f%%",100*upper/N)))
}
# missing-data handling GAPs (skip-logic artifacts, not the study's fault) — extra worst-case swing
gaps_out <- sum(it$item=="hand_miss_outcom"   & it$state=="NA")
gaps_exp <- sum(it$item=="hand_miss_exposure" & it$state=="NA")
cat(sprintf("\nmissing-data handling GAPs held at N/A (worst-case -> VAL): outcome %d, exposure %d, total %d\n",
            gaps_out, gaps_exp, gaps_out+gaps_exp))
missN <- sum(dom$domain=="Missing data" & dom$state!="NA")
missV <- sum(dom$domain=="Missing data" & dom$state=="VAL")
cat(sprintf("Missing data validity flaw: primary %.1f%%  ->  +GAP worst-case %.1f%%  (of %d)\n",
            100*missV/missN, 100*(missV+gaps_out+gaps_exp)/missN, missN))

## ---------- (a) TRANSPARENCY x VALIDITY 2x2 ----------
cat("\n== transparency x validity ==\n")
tv <- stu[!is.na(stu$transparency) & !is.na(stu$validity), ]
mt <- median(tv$transparency); mv <- median(tv$validity)
cat(sprintf("median transparency %.3f | median validity %.3f | n=%d\n", mt, mv, nrow(tv)))
q <- function(tl,vl) sum((tv$transparency>=mt)==tl & (tv$validity>=mv)==vl)
cat(sprintf("  transparent & sound  (hi T, hi V): %d\n", q(TRUE ,TRUE )))
cat(sprintf("  transparent, flawed  (hi T, lo V): %d\n", q(TRUE ,FALSE)))
cat(sprintf("  opaque, sound-looking(lo T, hi V): %d\n", q(FALSE,TRUE )))
cat(sprintf("  opaque & flawed      (lo T, lo V): %d\n", q(FALSE,FALSE)))
# 5x5 density grid for the heatmap (rows = validity high->low, cols = transparency low->high)
br <- c(-0.001,0.2,0.4,0.6,0.8,1.001)
tb <- cut(tv$transparency, br, labels=FALSE); vb <- cut(tv$validity, br, labels=FALSE)
grid <- matrix(0,5,5)
for(k in seq_along(tb)) grid[vb[k],tb[k]] <- grid[vb[k],tb[k]] + 1
cat("density grid (row 5=top=validity .8-1 ; col 5=right=transparency .8-1):\n")
for(r in 5:1) cat("  ", sprintf("%3d",grid[r,]), "\n")

## ---------- (c) AUTHOR-INSIGHT CROSS-TAB: did authors mention the error they actually have? ----------
cat("\n== insight: among papers WITH a validity flaw in a domain, % that named that error in the discussion ==\n")
erd <- it[it$item=="err_disc", c("PMID","raw")]; names(erd)[2] <- "err"
map <- list("Selection bias"="selection bias","Measurement bias"="measurement bias",
            "Confounding bias"="confounding bias","Missing data"="missing data","Random error"="random error")
for(dm in names(map)){
  vpm <- dom$PMID[dom$domain==dm & dom$state=="VAL"]
  e <- erd$err[match(vpm, erd$PMID)]
  e[is.na(e)] <- ""
  mentioned <- grepl(map[[dm]], tolower(e))
  cat(sprintf("%-18s flawed %3d | acknowledged in discussion %s\n", dm, length(vpm),
              fmt(sum(mentioned), length(vpm))))
}
cat("\ndone\n")

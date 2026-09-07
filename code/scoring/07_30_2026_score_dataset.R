# Reporting-vs-validity 4-state scoring of the quality dataset (R primary).
# States: NA / OK / REP (reporting gap) / VAL (validity flaw). Conventions per project-scoring-plan (2026-07-30).
# Run from the repository root:
#   & "C:\Program Files\R\R-4.5.2\bin\Rscript.exe" code/scoring/07_30_2026_score_dataset.R
#
# 2026-08-19: the scoring LOGIC moved verbatim into code/lib/score_dataset_lib.R so the
# sensitivity analysis can call it thousands of times on perturbed data (plan sections 1f,
# 1g, 3 and tier 3). This script is now the thin caller that loads, scores, writes and
# reports. Output is unchanged and must stay so -- code/scoring/08_19_2026_verify_score_refactor.R
# asserts all three CSVs byte for byte.
#
# ⚠ Despite its 07_23 stamp, data/analysis/07_23_2026_ANALYSIS_DATASET_wide.csv holds the
#   385-paper population (overwritten in place at the 385 rebuild). 310 papers are scored;
#   the other 75 are Predictive and carry no scored items.

source("code/lib/score_dataset_lib.R")

d <- read.csv("data/analysis/07_23_2026_ANALYSIS_DATASET_wide.csv", stringsAsFactors = FALSE,
              colClasses = "character", check.names = FALSE)

res       <- score_dataset(d)
df        <- res$items
dom_state <- res$domain
studies   <- res$study
DOMS      <- DOMS_ORDER
papers    <- unique(df[, c("PMID","Study_Type")])

write.csv(df,        "data/scoring/07_30_2026_scored_items_long.csv", row.names = FALSE)
write.csv(dom_state, "data/scoring/07_30_2026_scored_domain.csv",     row.names = FALSE)
write.csv(studies,   "data/scoring/07_30_2026_scored_study.csv",      row.names = FALSE)

## ---------- report ----------
cat("\n== scored population ==\n")
print(table(papers$Study_Type))
fmt <- function(n,N) sprintf("%d (%.1f%%)", n, 100*n/N)
cat("\n== domain x task: 4-state distribution ==\n")
for(dm in DOMS){
  for(tk in c("Descriptive","Causal")){
    sub <- dom_state$state[dom_state$domain==dm & dom_state$Study_Type==tk]
    N <- length(sub); if(N==0) next
    if(all(sub=="NA")) next
    cat(sprintf("%-20s %-12s N=%d | No issue %s | Reporting %s | Validity %s | N/A %s\n",
        dm, tk, N, fmt(sum(sub=="OK"),N), fmt(sum(sub=="REP"),N),
        fmt(sum(sub=="VAL"),N), fmt(sum(sub=="NA"),N)))
  }
}
cat("\n== weakest-link: % of papers with >=1 validity flaw, by domain (denominator = applicable papers) ==\n")
for(dm in DOMS){
  sub <- dom_state[dom_state$domain==dm, ]; appl <- sub[sub$state!="NA", ]
  if(nrow(appl)==0) next
  cat(sprintf("%-20s  %s of %d applicable\n", dm, fmt(sum(appl$state=="VAL"), nrow(appl)), nrow(appl)))
}
cat("\n== validation anchors ==\n")
cat("err_disc 'None mentioned' (REP):",
    sum(df$item=="err_disc" & df$state=="REP"),
    "| by task D/C:",
    sum(df$item=="err_disc" & df$state=="REP" & df$Study_Type=="Descriptive"),
    sum(df$item=="err_disc" & df$state=="REP" & df$Study_Type=="Causal"), "\n")
cat("confounding applicable causal:", sum(dom_state$domain=="Confounding bias" & dom_state$state!="NA"),
    "| VAL:", sum(dom_state$domain=="Confounding bias" & dom_state$state=="VAL"), "\n")
cat("val_outcome 'No' (VAL):", sum(df$item=="val_outcome" & df$state=="VAL"),
    "| val_exposure 'No' (VAL):", sum(df$item=="val_exposure" & df$state=="VAL"), "\n")
cat("study indices: transparency mean", round(mean(studies$transparency,na.rm=TRUE),3),
    "| validity mean", round(mean(studies$validity,na.rm=TRUE),3), "\n")
cat("papers with 0 domains flagged:", sum(studies$domains_flagged==0),
    "| >=3 domains flagged:", sum(studies$domains_flagged>=3), "\n")
cat("\nwrote: data/scoring/07_30_2026_scored_items_long.csv / _scored_domain.csv / _scored_study.csv\n")

# Secondary (additive) severity scoring: per-domain flagged-item COUNTS, alongside the weakest-link
# "any" primary. Reads scored_items_long. Writes a per study x domain count table + prints summaries.
# Run: & "C:\Program Files\R\R-4.5.2\bin\x64\Rscript.exe" code/scoring/07_30_2026_secondary_scoring.R

it <- read.csv("data/scoring/07_30_2026_scored_items_long.csv", stringsAsFactors=FALSE,
               colClasses="character", na.strings=character(0))
pri <- it[it$primary=="TRUE", ]
pri$isVAL <- as.integer(pri$state=="VAL")
pri$isREP <- as.integer(pri$state=="REP")
pri$isAPP <- as.integer(pri$state!="NA")

DOMS <- c("Random error","Selection bias","Measurement bias","Confounding bias",
          "Missing data","Mentioning errors","Conflating task")

# ---- per study x domain additive counts ----
pd <- aggregate(cbind(isVAL,isREP,isAPP) ~ PMID+domain+Study_Type, data=pri, FUN=sum)
write.csv(pd[order(pd$PMID),], "data/scoring/07_30_2026_secondary_domain_counts.csv", row.names=FALSE)

# scored-item inventory per domain (how many primary items CAN flag) — the ceiling of the count
maxitems <- sapply(DOMS, function(dm) length(unique(pri$item[pri$domain==dm])))

cat("== SECONDARY (additive) severity per domain — validity flaws per APPLICABLE paper ==\n")
cat(sprintf("%-20s %5s %8s %8s | %-22s | %s\n","domain","items","mean D","mean C",
            "flag density D/C","count dist C (0/1/2/3+)"))
for(dm in DOMS){
  line <- sprintf("%-20s %5d ", dm, maxitems[dm])
  md <- NA; mc <- NA
  for(tk in c("Descriptive","Causal")){
    s <- pd[pd$domain==dm & pd$Study_Type==tk & pd$isAPP>0, ]
    m <- if(nrow(s)) mean(s$isVAL) else NA
    if(tk=="Descriptive") md <- m else mc <- m
  }
  # densities
  sd <- pd[pd$domain==dm & pd$Study_Type=="Descriptive" & pd$isAPP>0, ]
  sc <- pd[pd$domain==dm & pd$Study_Type=="Causal"      & pd$isAPP>0, ]
  dens_d <- if(nrow(sd)) mean(sd$isVAL/sd$isAPP) else NA
  dens_c <- if(nrow(sc)) mean(sc$isVAL/sc$isAPP) else NA
  # distribution of the causal count
  cc <- if(nrow(sc)) pmin(sc$isVAL,3) else integer(0)
  dist <- sapply(0:3, function(k) sum(cc==k))
  cat(sprintf("%-20s %5d %8s %8s | %-22s | %2d/%2d/%2d/%2d\n",
      dm, maxitems[dm],
      ifelse(is.na(md),"  -",sprintf("%.2f",md)),
      ifelse(is.na(mc),"  -",sprintf("%.2f",mc)),
      sprintf("%s / %s", ifelse(is.na(dens_d),"-",sprintf("%.0f%%",100*dens_d)),
                          ifelse(is.na(dens_c),"-",sprintf("%.0f%%",100*dens_c))),
      dist[1],dist[2],dist[3],dist[4]))
}

# ---- study-level additive error score (sum of validity flaws across all domains) ----
sl <- aggregate(cbind(isVAL,isREP,isAPP) ~ PMID+Study_Type, data=pri, FUN=sum)
cat("\n== STUDY-LEVEL additive error score (total validity flaws per paper) ==\n")
for(tk in c("Descriptive","Causal")){
  s <- sl[sl$Study_Type==tk, ]
  cat(sprintf("%-12s n=%d | mean %.2f | median %d | range %d-%d | 0:%d  1-2:%d  3-4:%d  5+:%d\n",
      tk, nrow(s), mean(s$isVAL), as.integer(median(s$isVAL)), min(s$isVAL), max(s$isVAL),
      sum(s$isVAL==0), sum(s$isVAL %in% 1:2), sum(s$isVAL %in% 3:4), sum(s$isVAL>=5)))
}
cat(sprintf("%-12s n=%d | mean %.2f | median %d | range %d-%d\n","ALL",nrow(sl),
    mean(sl$isVAL), as.integer(median(sl$isVAL)), min(sl$isVAL), max(sl$isVAL)))

# also the reporting-gap burden (secondary, transparency side)
cat("\n== STUDY-LEVEL reporting-gap count per paper ==\n")
for(tk in c("Descriptive","Causal")){
  s <- sl[sl$Study_Type==tk, ]
  cat(sprintf("%-12s mean %.2f | median %d | range %d-%d\n", tk, mean(s$isREP),
      as.integer(median(s$isREP)), min(s$isREP), max(s$isREP)))
}
cat("\nwrote data/scoring/07_30_2026_secondary_domain_counts.csv\n")

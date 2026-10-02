# NOTE (public repository): 2 hard-coded study identifier(s) were
# rewritten to de-identified surrogates by tools/build_public_repo.py.
# They are rulings about particular studies rather than values the data
# can supply, so they have to travel with it.
###############################################################################
##  SCORING LIBRARY -- the reporting-vs-validity 4-state scorer, as callable
##  functions with no file I/O and no globals.
##
##  Project : Assessment of Healthcare Research Quality in Saudi Arabia
##  Date    : 2026-08-19
##
##  WHY THIS EXISTS
##  `code/scoring/07_30_2026_score_dataset.R` was a top-level script: it read one
##  hard-coded path, accumulated rows into a global via `<<-`, and wrote three
##  hard-coded paths. The sensitivity analysis has to run the scorer thousands of
##  times on perturbed data (section 1f extreme-case bounds, 1g reviewer-resampling
##  bootstrap, section 3 tipping point, and tier 3), so it has to be a function.
##
##  ⚠⚠ 2026-08-22 -- GRADED SEVERITIES AND THREE MOVED CUTS (TSA).
##  Until today every scored item was binary: a response either flagged or it did
##  not, and the error score counted flags. Three ordinal items are now graded, and
##  their cuts moved, on the argument that a weaker attempt is not the same failure
##  as no attempt -- content/face validity is not "no validation", and selecting
##  confounders from previous literature is not "none of the above". So:
##    * STATE stays categorical and still drives prevalence, the domain roll-up and
##      the whole epsilon/delta sensitivity apparatus, which perturbs states.
##    * SEVERITY is a new per-item weight in [0,1] driving the error score and the
##      validity index. Response options are ordered best to worst and assigned
##      EQUALLY SPACED severities from 0 to 1: three rungs give 0 / 0.5 / 1, five
##      rungs give 0 / 0.25 / 0.5 / 0.75 / 1.
##  Cuts moved at the same time: content/face validity, previous literature, and any
##  imputation short of multiple imputation are now flaws rather than passes.
##  The two measurement-accounting items, previously recorded but excluded as
##  near-constant ("No" on 229 of 229 causal papers), are now SCORED -- see below.
##  ⚠ The pre-change outputs are in data/scoring/_pre_graded_backup/ with their MD5s.
##  `08_19_2026_verify_score_refactor.R` asserted the old CSVs byte for byte and will
##  now fail BY DESIGN; it is a refactor test, not a scoring test.
##
##  ⚠ TWO ENTRY POINTS, AND SECTION 3 ONLY NEEDS THE SECOND.
##  score_items()  turns raw answers into item states  (expensive; ~6,000 records)
##  roll_up()      turns item states into domain states (cheap)
##  The epsilon/delta perturbation acts on the item STATE, not the raw answer, so
##  the tipping point can score ONCE and then roll up thousands of times. Only the
##  analyses that perturb raw answers (1f, 1g) need the full re-score per draw.
###############################################################################

DOMS_ORDER <- c("Random error","Selection bias","Measurement bias","Confounding bias",
                "Missing data","Mentioning errors","Conflating task")

## unadjusted per-protocol RCTs -> confounding flaw survives the ITT exemption
PP_UNADJ_DEFAULT <- c("STUDY-0532","STUDY-0062")

## ---------------------------------------------------------------------------
## SEVERITY LADDERS.  Each is best -> worst; severities are equally spaced 0..1.
## Options sharing a quality tier share a severity. Anything not listed is binary:
## severity 1 when the state is VAL, 0 otherwise.
## ---------------------------------------------------------------------------
SEV_VALIDATION <- c(criterion = 0, `content/face` = 0.5, no = 1)          # 3 rungs
## ⚠ Confounding control is ONE ordered ladder spread across TWO items, and the rungs
## are equally spaced across the pair, not within each item.  The worst outcome -- no
## adjustment attempted at all -- is scored by `base_conf_meth` at 1, so `conf_var_det`
## stops at 2/3.  Otherwise a paper that adjusted but chose its confounders badly
## (0 + 1) scored exactly the same as one that never adjusted (1 + not applicable), and
## "at least considered it" was worth nothing.  Combined severity therefore runs
##   DAG / subject-matter 0  <  previous literature 1/3  <  statistical criteria,
##   change of estimate or none of the above 2/3  <  no adjustment 1
SEV_CONFBASIS  <- c(dag = 0, literature = 1/3, other = 2/3, no_adjustment = 1)
SEV_IMPUTE     <- c(multiple = 0, regression = 0.25, mean_locf = 0.5,     # 5 rungs
                    indicator = 0.75, none = 1)

lc      <- function(v) tolower(trimws(v))
isNAraw <- function(v) is.na(v) || v == "" || lc(v) %in% c("skipped","should be skipped")

## weakest-link precedence VAL > REP > OK > NA
worst <- function(states) {
  s <- states[!is.na(states) & states != "NA"]
  if (length(s) == 0) return("NA")
  if ("VAL" %in% s) return("VAL")
  if ("REP" %in% s) return("REP")
  if ("OK"  %in% s) return("OK")
  "NA"
}

## graded validity of a measurement instrument.
## ⚠ 2026-08-22: content/face validity now FLAGS (severity 0.5) rather than passing.
## Only criterion validity is a clean pass. "Does not usually require validation"
## remains not applicable -- an objective measure is not being let off, it is being
## asked a question that does not arise.
gradestate <- function(v) {
  if (isNAraw(v)) return("NA"); lv <- lc(v)
  if (grepl("does not usually require", lv)) return("NA")   # validation not needed
  if (grepl("criterion", lv))    return("OK")               # best
  if (grepl("content/face", lv)) return("VAL")              # weaker: half a flaw
  if (grepl("not reported", lv) || grepl("unknown", lv)) return("REP")
  if (trimws(v) == "No") return("VAL")                      # not validated
  "NA"
}
gradesev <- function(v) {
  if (isNAraw(v)) return(0); lv <- lc(v)
  if (grepl("content/face", lv)) return(unname(SEV_VALIDATION["content/face"]))
  if (trimws(v) == "No")         return(unname(SEV_VALIDATION["no"]))
  0
}

## confounder-selection basis.  ⚠ 2026-08-22: previous literature now FLAGS; only a
## DAG / subject-matter basis is a clean pass.  The severities are the middle two rungs
## of the combined ladder above -- the top rung (no adjustment) belongs to
## `base_conf_meth`, and this item is not applicable there.
confbasis_sev <- function(v) {
  lv <- lc(v)
  if (grepl("directed acyclic", lv)) return(unname(SEV_CONFBASIS["dag"]))
  if (grepl("previous literature", lv)) return(unname(SEV_CONFBASIS["literature"]))
  unname(SEV_CONFBASIS["other"])
}

## missing-data handling.  ⚠ 2026-08-22: only multiple imputation is a clean pass;
## every weaker method flags, graded down the ladder.
impute_state <- function(v) if (isNAraw(v)) "NA" else
  if (grepl("multiple imputation", lc(v))) "OK" else "VAL"
impute_sev <- function(v) {
  lv <- lc(v)
  if (grepl("multiple imputation", lv))                    return(unname(SEV_IMPUTE["multiple"]))
  if (grepl("regression", lv))                             return(unname(SEV_IMPUTE["regression"]))
  if (grepl("mean value|last value carried forward", lv))  return(unname(SEV_IMPUTE["mean_locf"]))
  if (grepl("indicator", lv))                              return(unname(SEV_IMPUTE["indicator"]))
  unname(SEV_IMPUTE["none"])
}

## differential misclassification = validity flaw
diffstate <- function(v) {
  if (isNAraw(v)) return("NA")
  if (grepl("^differential", lc(v)))     return("VAL")
  if (grepl("^non-differential", lc(v))) return("OK")
  "NA"
}

###############################################################################
##  score_items(d) -- wide analysis dataset -> one row per (paper, scored item)
##
##  `d` must carry PMID, Study_Type and the task-prefixed item columns
##  (causal_* / descriptive_*). Predictive papers are skipped, as in the original.
##  Records accumulate into a preallocated list of character vectors rather than
##  a growing list of one-row data.frames: identical output, but it stops the
##  scorer being the bottleneck once it is called a thousand times.
###############################################################################
score_items <- function(d, pp_unadj = PP_UNADJ_DEFAULT) {
  recs <- vector("list", nrow(d) * 24L)
  k <- 0L
  ## `sev` defaults to the binary rule: a flaw costs 1, anything else 0.  The three
  ## graded items pass an explicit severity instead.
  add <- function(pmid, st, domain, item, axis, state, primary = TRUE, raw = "",
                  sev = NULL) {
    k <<- k + 1L
    if (is.null(sev)) sev <- if (identical(state, "VAL")) 1 else 0
    recs[[k]] <<- c(pmid, st, domain, item, axis, state,
                    if (primary) "TRUE" else "FALSE",
                    if (is.na(raw)) "" else as.character(raw),
                    format(sev, trim = TRUE))
  }

  for (i in seq_len(nrow(d))) {
    st <- d$Study_Type[i]; if (st == "Predictive") next
    pmid <- d$PMID[i]; pref <- if (st == "Causal") "causal_" else "descriptive_"
    g <- function(stem) { col <- paste0(pref, stem); if (!col %in% names(d)) return(NA_character_)
                          v <- d[[col]][i]; if (is.na(v)) return(NA_character_); trimws(v) }
    isC <- st == "Causal"

    ## ---------- RANDOM ERROR (precision; only if a sample was drawn) ----------
    samp <- g("sampling")
    census <- !isNAraw(samp) && grepl("whole population", lc(samp))
    if (!census) {
      ss <- g("sample_size"); add(pmid, st, "Random error", "sample_size", "reporting",
          if (isNAraw(ss)) "NA" else if (ss == "Yes") "OK" else if (ss == "No") "REP" else "NA", raw = ss)
      ac <- g("acc_sampl");  add(pmid, st, "Random error", "acc_sampl", "validity",
          if (isNAraw(ac)) "NA" else if (ac == "Yes") "OK" else if (ac == "No") "VAL" else "NA", raw = ac)
      sa <- g("sample_ach"); add(pmid, st, "Random error", "sample_ach", "validity",
          if (isNAraw(sa)) "NA" else if (sa == "Yes") "OK" else if (sa == "No") "VAL" else "NA", raw = sa)
    }

    ## ---------- SELECTION BIAS (3 channels) ----------
    bs <- g("base_sel")
    bsel <- if (isNAraw(bs)) "NA" else if (grepl("no baseline selection bias", lc(bs))) "OK" else
            if (bs == "Yes") "OK" else if (bs == "No") "VAL" else "NA"
    add(pmid, st, "Selection bias", "base_sel", "validity", bsel, raw = bs)
    if (isC) {
      cd <- g("comp_dis")
      add(pmid, st, "Selection bias", "comp_dis", "reporting",
          if (isNAraw(cd)) "NA" else if (cd == "Yes") "OK" else if (cd == "No") "REP" else "NA", raw = cd)
      fl <- g("follow"); lb <- g("ltfu_bias"); la <- g("ltfu_acc")
      if (!isNAraw(fl) && fl == "Yes") {
        lbst <- if (isNAraw(lb)) "NA" else if (lb == "No") "OK" else if (grepl("not reported", lc(lb))) "REP" else "PRESENT"
        add(pmid, st, "Selection bias", "ltfu_bias", "reporting", if (lbst == "PRESENT") "OK" else lbst, raw = lb)
        if (!isNAraw(lb) && lb == "Yes")               # bias present -> accounting carries the flaw
          add(pmid, st, "Selection bias", "ltfu_acc", "validity",
              if (isNAraw(la)) "NA" else if (la == "Yes") "OK" else if (la == "No") "VAL" else "NA", raw = la)
      }
    }

    ## ---------- MEASUREMENT BIAS ----------
    add(pmid, st, "Measurement bias", "val_outcome", "validity", gradestate(g("val_outcome")),
        raw = g("val_outcome"), sev = gradesev(g("val_outcome")))
    ## ⚠ 2026-08-22: NOW SCORED.  This item is "No" on 229 of 229 causal papers and
    ## 80 of 81 descriptive, and was excluded because a constant cannot separate
    ## papers.  TSA's ruling is that a constant at total failure is a finding, not a
    ## nuisance: no study in the sample accounted for measurement bias.  Prevalence
    ## in this domain therefore saturates at 100%, and it is the graded severities
    ## above that keep the domain discriminating in the score.
    add(pmid, st, "Measurement bias", "out_bias_acc", "validity",
        { v <- g("out_bias_acc"); if (isNAraw(v)) "NA" else if (v == "Yes") "OK" else if (v == "No") "VAL" else "NA" },
        raw = g("out_bias_acc"))
    if (isC) {
      add(pmid, st, "Measurement bias", "diff_or_nondiff_out", "validity", diffstate(g("diff_or_nondiff_out")), raw = g("diff_or_nondiff_out"))
      add(pmid, st, "Measurement bias", "val_exposure", "validity", gradestate(g("val_exposure")),
          raw = g("val_exposure"), sev = gradesev(g("val_exposure")))
      add(pmid, st, "Measurement bias", "exp_bias_acc", "validity",       # now scored, as above
          { v <- g("exp_bias_acc"); if (isNAraw(v)) "NA" else if (v == "Yes") "OK" else if (v == "No") "VAL" else "NA" },
          raw = g("exp_bias_acc"))
      add(pmid, st, "Measurement bias", "diff_or_nondiff_exp", "validity", diffstate(g("diff_or_nondiff_exp")), raw = g("diff_or_nondiff_exp"))
      add(pmid, st, "Measurement bias", "dep_or_indep_misc", "validity",
          { v <- g("dep_or_indep_misc"); if (isNAraw(v)) "NA" else if (v == "Dependent") "VAL" else if (v == "Independent") "OK" else "NA" },
          raw = g("dep_or_indep_misc"))
    }

    ## ---------- CONFOUNDING (causal only; THREE items; RCT-ITT exemption) ----------
    ## 2026-08-16: split from a single composite into its three constituent
    ## components. The items are constructed to be mutually exclusive so that one
    ## underlying failing cannot be counted twice: all 88 papers whose
    ## base_conf_meth is "No adjustment" also carry "No adjustment" on
    ## conf_var_det, and 23 of the 33 randomized trials do likewise.
    if (isC) {
      bcm <- g("base_conf_meth"); cvd <- g("conf_var_det"); dsg <- g("design")
      tvy <- g("time_verying");   tvm <- g("tv_conf_meth")
      opts   <- if (isNAraw(bcm)) character(0) else trimws(strsplit(bcm, ";")[[1]])
      is_rct <- (!isNAraw(dsg) && dsg == "RCT") || any(tolower(opts) == "randomization")
      noadj  <- !isNAraw(bcm) && grepl("no adjustment", lc(bcm))

      ## (1) was any method of confounding control used at all?
      c1 <- if (is_rct) { if (pmid %in% pp_unadj) "VAL" else "OK" } else
            if (isNAraw(bcm)) "NA" else
            if (grepl("not reported", lc(bcm))) "REP" else
            if (noadj) "VAL" else "OK"
      add(pmid, st, "Confounding bias", "base_conf_meth", "validity", c1, raw = bcm)

      ## (2) on what basis were confounders selected?  NOT APPLICABLE where no
      ##     adjustment was attempted - judging the selection criterion there would
      ##     re-score the failing already captured by item (1).
      ## ⚠ 2026-08-22: the cut moved to a DAG / subject-matter basis only.  Previous
      ## literature is a real but weaker basis, so it flags at half severity rather
      ## than passing.  The not-applicable rule is unchanged and still the point:
      ## where no adjustment was attempted, judging the basis would count the same
      ## failing twice.
      c2 <- if (noadj || isNAraw(cvd) || grepl("no adjustment", lc(cvd))) "NA" else
            if (grepl("directed acyclic", lc(cvd))) "OK" else
            if (grepl("not reported", lc(cvd))) "REP" else "VAL"
      add(pmid, st, "Confounding bias", "conf_var_det", "validity", c2, raw = cvd,
          sev = if (c2 == "VAL") confbasis_sev(cvd) else 0)

      ## (3) time-varying confounding - applicable only where it is present.
      c3 <- if (isNAraw(tvy) || lc(tvy) != "yes") "NA" else
            if (isNAraw(tvm)) "VAL" else
            if (grepl("not reported", lc(tvm))) "REP" else "OK"
      add(pmid, st, "Confounding bias", "tv_conf_meth", "validity", c3, raw = paste0(tvy, " || ", tvm))
    }

    ## ---------- MISSING DATA ----------
    mo <- g("miss_outcome"); ho <- g("hand_miss_outcom")
    add(pmid, st, "Missing data", "miss_outcome", "reporting",
        if (isNAraw(mo)) "NA" else if (grepl("not reported", lc(mo))) "REP" else "OK", raw = mo)  # No/Yes both "reported"
    if (!isNAraw(mo) && mo == "Yes")
      ## ⚠ 2026-08-22: only multiple imputation passes; weaker methods flag, graded
      add(pmid, st, "Missing data", "hand_miss_outcom", "validity",
          impute_state(ho), raw = ho,
          sev = if (impute_state(ho) == "VAL") impute_sev(ho) else 0)
    if (isC) {
      me <- g("miss_exposure"); he <- g("hand_miss_exposure")
      add(pmid, st, "Missing data", "miss_exposure", "reporting",
          if (isNAraw(me)) "NA" else if (grepl("not reported", lc(me))) "REP" else "OK", raw = me)
      if (!isNAraw(me) && me == "Yes")
        add(pmid, st, "Missing data", "hand_miss_exposure", "validity",
            impute_state(he), raw = he,
            sev = if (impute_state(he) == "VAL") impute_sev(he) else 0)
    }

    ## ---------- MENTIONING ERRORS IN DISCUSSION (pure reporting) ----------
    ed <- g("err_disc")
    add(pmid, st, "Mentioning errors", "err_disc", "reporting",
        if (isNAraw(ed)) "NA" else if (grepl("none of the above", lc(ed))) "REP" else "OK", raw = ed)

    ## ---------- CONFLATING THE TASK (descriptive only; pure validity) ----------
    if (!isC) {
      ct <- g("confl_task")
      add(pmid, st, "Conflating task", "confl_task", "validity",
          if (isNAraw(ct)) "NA" else if (ct == "Yes") "VAL" else if (ct == "No") "OK" else "NA", raw = ct)
    }
  }

  m <- do.call(rbind, recs[seq_len(k)])
  data.frame(PMID = m[, 1], Study_Type = m[, 2], domain = m[, 3], item = m[, 4],
             axis = m[, 5], state = m[, 6], primary = m[, 7] == "TRUE", raw = m[, 8],
             severity = as.numeric(m[, 9]), stringsAsFactors = FALSE)
}

###############################################################################
##  roll_up(df) -- item states -> one row per (paper, domain), weakest-link over
##  the PRIMARY items only. This is the function the section-3 perturbation calls
##  repeatedly; it takes item states, so epsilon/delta can be applied to `df$state`
##  directly without re-scoring raw answers.
###############################################################################
roll_up <- function(df, doms = DOMS_ORDER) {
  pri    <- df[df$primary, ]
  papers <- unique(df[, c("PMID","Study_Type")])
  dom_state <- expand.grid(PMID = papers$PMID, domain = doms, stringsAsFactors = FALSE)
  dom_state$Study_Type <- papers$Study_Type[match(dom_state$PMID, papers$PMID)]
  key <- paste(pri$PMID, pri$domain)
  spl <- split(pri$state, key)
  dom_state$state <- vapply(paste(dom_state$PMID, dom_state$domain),
                            function(k) worst(spl[[k]]), character(1), USE.NAMES = FALSE)
  dom_state
}

###############################################################################
##  study_indices(df, dom_state) -- per-paper transparency and validity indices
###############################################################################
## ⚠ 2026-08-22: two error scores and two validity indices are reported side by side.
## `n_val_flags` / `validity` are the COUNT-based pair -- unchanged in definition, and
## what prevalence, the domain roll-up and the sensitivity analysis are built on.
## `error_weighted` / `validity_weighted` apply the graded severities, so a weaker
## attempt costs less than none. Keeping both is deliberate: the count stays
## comparable with categorical risk-of-bias tools, and dropping it would strand every
## downstream analysis that assumes an integer flag.
study_indices <- function(df, dom_state) {
  pri <- df[df$primary, ]
  studies <- do.call(rbind, lapply(split(pri, pri$PMID), function(s) {
    applic <- sum(s$state != "NA"); rep_gaps <- sum(s$state == "REP"); val_flags <- sum(s$state == "VAL")
    judge  <- sum(s$state %in% c("OK","VAL"))
    sev    <- sum(s$severity[s$state == "VAL"])
    data.frame(PMID = s$PMID[1], Study_Type = s$Study_Type[1], n_applicable = applic,
               n_rep_gaps = rep_gaps, n_val_flags = val_flags,
               error_weighted = sev,
               transparency = ifelse(applic > 0, 1 - rep_gaps / applic, NA),
               validity = ifelse(judge > 0, 1 - val_flags / judge, NA),
               validity_weighted = ifelse(judge > 0, 1 - sev / judge, NA),
               stringsAsFactors = FALSE)
  }))
  dvf <- tapply(dom_state$state, dom_state$PMID, function(x) sum(x == "VAL"))
  studies$domains_flagged <- as.integer(dvf[studies$PMID])

  ## ---------- ACKNOWLEDGEMENT INDEX (added 2026-08-22, TSA) ----------
  ## A THIRD axis, deliberately NOT folded into transparency.  Every other reporting item
  ## asks about JUDGEABILITY -- was the information there, independently of our verdict.
  ## This asks about CANDOUR -- did the authors own the flaws we actually found -- and it
  ## only exists AFTER the verdict.  Folding it into transparency would make the reporting
  ## axis a function of the validity result: more flaws mechanically create more chances to
  ## fail acknowledgement, so low-validity papers would be pushed to low transparency BY
  ## CONSTRUCTION, and the transparency x validity cross-classification would partly measure
  ## that mechanism instead of an association.  Kept separate, all three axes stay clean.
  ##
  ## acknowledgement = flagged domains NAMED in the discussion / flagged domains
  ##   1 = owned every flaw we found · 0 = owned none · NA if nothing was flagged
  ## Higher is better, matching `transparency` and `validity`.
  ##
  ## ⚠ DENOMINATOR IS THE FIVE MENTIONABLE DOMAINS ONLY.  `err_disc` offers exactly these
  ## five options, so "Conflating the task" -- a validity flaw, descriptive studies only --
  ## CANNOT be acknowledged and must not count against a paper.  Including it would penalise
  ## descriptive papers for failing to name something the instrument never offered them.
  MENTIONABLE <- c("Random error" = "random error", "Selection bias" = "selection bias",
                   "Measurement bias" = "measurement bias",
                   "Confounding bias" = "confounding bias", "Missing data" = "missing data")
  ed <- df[df$item == "err_disc", ]
  ed_raw <- setNames(as.character(ed$raw), as.character(ed$PMID))
  n_named <- n_flagged <- integer(nrow(studies))
  for (i in seq_len(nrow(studies))) {
    p  <- as.character(studies$PMID[i])
    ds <- dom_state$domain[dom_state$PMID == studies$PMID[i] & dom_state$state == "VAL"]
    ds <- ds[ds %in% names(MENTIONABLE)]
    raw <- tolower(if (is.na(ed_raw[p]) || is.null(ed_raw[p])) "" else ed_raw[p])
    n_flagged[i] <- length(ds)
    n_named[i]   <- if (length(ds)) sum(vapply(ds, function(d)
      grepl(MENTIONABLE[[d]], raw, fixed = TRUE), logical(1))) else 0L
  }
  studies$ack_flagged     <- n_flagged
  studies$ack_named       <- n_named
  studies$acknowledgement <- ifelse(n_flagged > 0, n_named / n_flagged, NA_real_)
  studies
}

###############################################################################
##  score_dataset(d) -- the whole pipeline, data in / data out.
###############################################################################
score_dataset <- function(d, pp_unadj = PP_UNADJ_DEFAULT) {
  items <- score_items(d, pp_unadj = pp_unadj)
  dom   <- roll_up(items)
  list(items = items, domain = dom, study = study_indices(items, dom))
}

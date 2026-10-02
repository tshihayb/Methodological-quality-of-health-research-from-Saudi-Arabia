# Codebook

What the columns in the main data files mean. The appraisal answers come from the instrument in
`docs/instrument/`; each is given here with its question number and its wording as the reviewers
saw it. For the other files, the scripts that read them say what each column is used for.

## Conventions

- `PMID` is the study's code in this repository (`STUDY-0001` to `STUDY-1031`), not its PubMed number.
- Appraisal columns are named for the part of the instrument they come from: `descriptive_`,
  `predictive_` or `causal_`. Only the part matching the study's aim was filled in, so the others
  are blank for that study.
- `skipped` means an earlier answer branched past the question; `should be skipped` means the
  adjudicators ruled that the question did not apply. Both are treated as not applicable, and so is
  a blank inside the part that was filled in.
- Questions marked "select all that apply" hold every option chosen, separated by `;`.
- `Not reported or unknown` is a recorded answer, not missing data.

## The study files

`data/analysis/07_23_2026_ANALYSIS_DATASET_wide.csv` has one row per study (385) and one column per
question. `data/analysis/07_23_2026_ANALYSIS_DATASET_long.csv` holds the same answers with one row
per study and question.

### Study characteristics

| Column | Meaning |
|---|---|
| `PMID` | the study's code (see Conventions) |
| `Study_Type` | the study's aim, as determined by the study team: `Descriptive`, `Predictive` or `Causal` |
| `first_author_saudi` | `1` if the first author had a Saudi affiliation, `0` if not; from the authors' affiliations, not from the reviewers |
| `last_author_saudi` | the same, for the last author |
| `corresponding_author_saudi` | the same, for the corresponding author |
| `pct_saudi_ge50` | whether at least half of the authors had a Saudi affiliation: `>=50%` or `<50%` |

### Appraisal answers

| Column | Q | Question in the instrument | Asked of | Answers in the data |
|---|---|---|---|---|
| `recusal` | 2 | Do you wish to recuse yourself from reviewing this study for any reason? | every study | No, I do not wish to recuse myself. |
| `task` | 3 | What was the study task or epidemiological paradigm? | every study | Causal / Descriptive / Predictive |
| `descriptive_design` | 4 | What was the study design? | descriptive | Cross-sectional / Cohort / Ecological |
| `descriptive_pop` | 5 | Did the study use data from Saudi Arabia or not? | descriptive | Yes / No |
| `descriptive_sampling` | 6 | What was the sampling technique? | descriptive | Non-random / Whole population was invited (no sample was taken) / Random |
| `descriptive_sample_size` | 7 | Was a sample size calculation done? | descriptive | No / Yes |
| `descriptive_acc_sampl` | 8 | Did the authors account for ineligibility, non-response, loss to follow-up, etc. in sample size calculation? | descriptive | No / Yes |
| `descriptive_sample_ach` | 9 | Was the sample size needed achieved? | descriptive | Yes / No |
| `descriptive_base_sel` | 10 | Was the baseline selection bias from the investigator accounted for? | descriptive | No / No baseline selection bias from investigator |
| `descriptive_outcome_type` | 11 | What was the nature of the outcome? | descriptive | Objective / Subjective |
| `descriptive_val_outcome` | 12 | Did the authors use validated measurement for the outcome? | descriptive | Yes, the authors conducted content/face validity or cited the content/face validity from other studies / No / Yes, the authors conducted criterion validity or cited the criterion validity from other studies / This type of objective measurement does not usually require validation (e.g., surgical intervention) |
| `descriptive_out_bias_acc` | 13 | Was the measurement bias in the outcome accounted for? | descriptive | No / Yes |
| `descriptive_miss_outcome` | 14 | Was there any participant with a missing outcome? | descriptive | No / Not reported or unknown / Yes |
| `descriptive_hand_miss_outcom` | 15 | Any methods used for handling missing data in outcome? | descriptive | No |
| `descriptive_err_disc` | 16 | Did the authors qualitatively mention the following errors in the discussion section? (select all that apply) | descriptive | one or more of: Confounding bias; Measurement bias; Missing data; None of the above; Random error; Selection bias |
| `descriptive_confl_task` | 17 | Did the authors investigate any association beyond their primary intention of describing the sample? | descriptive | Yes / No |
| `predictive_design` | 18 | What was the study design? | predictive | Diagnostic / Prognostic |
| `predictive_pop` | 19 | Did the study use data from Saudi Arabia or not? | predictive | No / Yes |
| `causal_design` | 20 | What was the study design? | causal | Cross-sectional / Cohort (including clinical trials without randomization) / Randomized clinical trial (including all types of randomized experiments) / Case-control / Pre/post / Ecological / Quasi-experimental (including instrumental variables, difference-in-difference, regression discontinuity design, and interrupted time series) |
| `causal_pop` | 21 | Did the study use data from Saudi Arabia or not? | causal | Yes / No |
| `causal_sampling` | 22 | What was the sampling technique? | causal | Non-random / Whole population was invited (no sample was taken) / Random |
| `causal_sample_size` | 23 | Was a sample size calculation done? | causal | No / Yes |
| `causal_acc_sampl` | 24 | Did the authors account for ineligibility, non-response, loss to follow-up, change in exposure status over time. etc. in sample size calculation? | causal | No / Yes |
| `causal_sample_ach` | 25 | Was the sample size needed achieved? | causal | Yes / No |
| `causal_base_sel` | 26 | Was the baseline selection bias from the investigator accounted for? | causal | No / No baseline selection bias from investigator / Yes |
| `causal_comp_dis` | 27 | Did the authors compare the distribution of the exposure and outcome between those included (responded) in the study and those not included (did not respond) in the study to check if there was selection bias due to participant' baseline non-response? | causal | No / Yes |
| `causal_follow` | 28 | Was there a follow-up in the study? | causal | No / Yes |
| `causal_ltfu_bias` | 29 | Was there loss to follow-up bias? | causal | Not reported or unknown / No / Yes |
| `causal_ltfu_acc` | 30 | Was the loss to follow-up bias accounted for? | causal | No / Yes |
| `causal_exposure_type` | 31 | What was the nature of the exposure? | causal | Objective / Subjective |
| `causal_val_exposure` | 32 | Did the authors use validated measurement for the exposure? | causal | This type of objective measurement does not usually require validation (e.g., surgical intervention) / Yes, the authors conducted content/face validity or cited the content/face validity from other studies / No / Yes, the authors conducted criterion validity or cited the criterion validity from other studies |
| `causal_diff_or_nondiff_exp` | 33 | Was the measurement bias in the exposure differential or non-differential with respect to the outcome? | causal | Non-differential with respect to the outcome / Differential with respect to the outcome |
| `causal_exp_bias_acc` | 34 | Was the measurement bias in the exposure accounted for? | causal | No |
| `causal_outcome_type` | 35 | What was the nature of the outcome? | causal | Objective / Subjective |
| `causal_val_outcome` | 36 | Did the authors use validated measurement for the outcome? | causal | Yes, the authors conducted content/face validity or cited the content/face validity from other studies / No / Yes, the authors conducted criterion validity or cited the criterion validity from other studies / This type of objective measurement does not usually require validation (e.g., surgical intervention) |
| `causal_diff_or_nondiff_out` | 37 | Was the measurement bias in the outcome differential or non-differential with respect to the exposure? | causal | Non-differential with respect to the exposure / Differential with respect to the exposure / Non-differential with respect to the outcome |
| `causal_out_bias_acc` | 38 | Was the measurement bias in the outcome accounted for? | causal | No |
| `causal_dep_or_indep_misc` | 39 | Was the exposure measurement bias independent or dependent of the outcome measurement bias? | causal | Independent / Dependent |
| `causal_base_conf_meth` | 40 | What was/were the method(s) used for handling baseline confounding? (select all that apply) | causal | one or more of: Instrumental variable analysis besides randomization (difference-in-difference, regression discontinuity design, and interrupted time series); Inverse probability of treatment weighting; Matching; No adjustment for baseline confounding was done; Propensity score; Randomization; Regression; Restriction; Stratification |
| `causal_time_verying` | 41 | Did the authors estimate a time-varying effect? | causal | No / Yes |
| `causal_tv_conf_meth` | 42 | What was/were the method(s) used for handling time-varying confounding? (select all that apply) | causal | one or more of: Inverse probability of treatment weighting; Matching; Propensity score; Regression |
| `causal_conf_var_det` | 43 | How did the authors determine the confounding variables that they have adjusted for? (select all that apply) | causal | one or more of: Based on Directed Acyclic Graphs (DAGs)/subject matter expertise; Based on change of estimate; Based on none of the above; Based on previous literature; Based on statistical criteria; No adjustment for baseline and time-varying confounding was done |
| `causal_miss_exposure` | 44 | Was there any participant with a missing exposure? | causal | No / Not reported or unknown / Yes |
| `causal_hand_miss_exposure` | 45 | Any methods used for handling missing data in exposure? | causal | No / Yes, multiple imputation / Yes, single imputation with mean value / Yes, single imputation with predicted value using regression |
| `causal_miss_outcome` | 46 | Was there any participant with a missing outcome? | causal | No / Not reported or unknown / Yes |
| `causal_hand_miss_outcom` | 47 | Any methods used for handling missing data in outcome? | causal | No / Yes, multiple imputation / Yes, single imputation with last value carried forward / Yes, single imputation with predicted value using regression |
| `causal_err_disc` | 48 | Did the authors qualitatively mention the following errors in the discussion section? (select all that apply) | causal | one or more of: Confounding bias; Measurement bias; Missing data; None of the above; Random error; Selection bias |

Question 1 (the study's identifier) is the `PMID` column. Questions 49 and 50, the reviewers'
comments, are not published.

### Columns of the long file

| Column | Meaning |
|---|---|
| `PMID`, `Study_Type` | as in the wide file |
| `variable` | the question, by its column name in the wide file |
| `final` | the settled answer |
| `source` | how the answer was settled (below) |
| `resolution_note` | where a rule set the answer, a short standard note saying which |

Values of `source`:

| Value | How the answer was settled |
|---|---|
| `agreed` | the two reviewers gave the same answer |
| `TA=YA` | the reviewers disagreed, and the two adjudicators, working independently, chose the same answer |
| `phaseII` | the reviewers disagreed and the adjudicators' independent answers differed; they settled it together |
| `phase2-normalised` | settled together, then recorded in the instrument's exact wording |
| `unresolved` | the reviewers disagreed only because one of them answered a question that the other's earlier answer had skipped; left blank and treated as not applicable |
| `skiplogic-resolved` | an answer recorded for a question that the study's earlier answers should have skipped, cleared to `skipped` |
| `batch6-agreed` | the last eight studies, reviewed after the others: the reviewers gave the same answer |
| `batch6-NA` | the last eight studies: the question applied to neither reviewer |
| `batch6-adjudicated` | the last eight studies: the adjudicators settled a disagreement together |
| `batch6-split` | the last eight studies: a combined answer (such as "Yes; not accounted") split between a question and its follow-up |
| `worklist-2026-08-12` | corrected in the study team's check of answers that contradicted each other across questions, applied on 12 August 2026 |
| `recovered-STUDY-0945` | one study whose adjudication record was shifted by one column; its settled answers were taken from the adjudicators' notes |

## The scoring files

Only the 310 descriptive and causal studies are scored; the instrument puts no bias items to
predictive studies. Every scored question takes one of four states: `NA` (not applicable), `OK`
(reported, and judged sound), `REP` (a reporting gap: not reported in enough detail to judge) or
`VAL` (a validity flaw: reported, and judged unfavourably).

`data/scoring/07_30_2026_scored_items_long.csv`, one row per scored study and question:

| Column | Meaning |
|---|---|
| `PMID`, `Study_Type` | as in the study files |
| `domain` | the source of error the question belongs to |
| `item` | the question, by its column name without the `descriptive_` or `causal_` prefix |
| `axis` | `reporting` if the question asks whether something was reported, `validity` if it asks whether it was done soundly |
| `state` | `NA`, `OK`, `REP` or `VAL` |
| `primary` | whether the question counts towards the domain and study scores |
| `raw` | the settled answer the state was derived from |
| `severity` | how much a flaw on this question costs: `1` for most questions, between 0 and 1 for the five graded ones, `0` when there is no flaw |

`data/scoring/07_30_2026_scored_domain.csv`, one row per scored study and domain: `state` is the
weakest link over the domain's questions: `VAL` if any is flawed, `REP` if none is flawed but one
cannot be judged, `OK` only when every applicable question is sound, `NA` if none applies.

`data/scoring/07_30_2026_scored_study.csv`, one row per scored study:

| Column | Meaning |
|---|---|
| `n_applicable` | questions that apply to the study |
| `n_rep_gaps` | of those, questions with a reporting gap |
| `n_val_flags` | of those, questions with a validity flaw |
| `error_weighted` | the error score: the summed severity of the flawed questions |
| `transparency` | the transparency index: 1 minus `n_rep_gaps` / `n_applicable` |
| `validity` | the validity index: 1 minus `n_val_flags` over the questions that could be judged (`OK` or `VAL`) |
| `validity_weighted` | the same, with each flaw counted at its severity |
| `domains_flagged` | the number of domains with a validity flaw |
| `ack_flagged` | flagged domains among the five a discussion can name (random error, selection bias, measurement bias, confounding, missing data) |
| `ack_named` | of those, the domains the study's own discussion names |
| `acknowledgement` | the acknowledgement index: `ack_named` / `ack_flagged`; blank when nothing was flagged |

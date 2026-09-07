# -*- coding: utf-8 -*-
"""The scoring framework: the instrument's items, what counts as a problem, and
what the score is built from.  Writes the supplementary instrument table, and
replaces the 2026-07-22 artifact that was still on N = 329.

    python code/tables/08_22_2026_scoring_framework.py

WHY THIS SCRIPT EXISTS
The 07_22 artifact was hand-authored HTML with no generator, and it had drifted:
it reported 329 analysis papers (190 causal / 71 descriptive / 68 predictive)
against the canonical 385 (229 / 81 / 75), still carried the draft line "cell
values await the pending data-cleaning fixes", and disagreed with itself about
whether the causal task has 20 items or 22.  A table describing the instrument
must be generated from the instrument and from the scorer, not typed.

⚠ THE ITEM COUNTS: 22 CAUSAL AND 10 DESCRIPTIVE (since 2026-08-22)
The manuscript's Table 1 said "20 scored items for causal and 10 for descriptive" and was
wrong in two ways at once; the primary set was then **20 causal and 9 descriptive**; and it
is now **22 and 10**, because the two measurement-accounting items were promoted to scored.
The two original errors are kept on record here because they cancelled and so hid each other:
  * Descriptive was counted as 10 by including `out_bias_acc`, which the scorer
    marks primary = FALSE.  Descriptive measurement bias rests on ONE primary item.
  * Causal totalled 20 correctly but NAMED the wrong five measurement-bias items:
    it listed `exp_bias_acc` and `out_bias_acc` (both non-primary) and omitted
    `diff_or_nondiff_exp` and `diff_or_nondiff_out` (both primary).  Two errors
    that happened to cancel in the total.
Asserted below against data/scoring/07_30_2026_scored_items_long.csv, which is the
published output of the scorer.

⚠⚠ 2026-08-22 — GRADED SEVERITIES, THREE MOVED CUTS, AND TWO ITEMS PROMOTED (TSA)
Until this date `out_bias_acc` and `exp_bias_acc` were recorded and excluded from the
score, on the ground that a near-constant item ("No" on 229 of 229 causal papers, 80 of
81 descriptive) cannot separate papers.  TSA's ruling reverses that: a constant sitting
at total failure is a finding, not a nuisance — no study in this sample accounted for
measurement bias in the exposure or the outcome — and hiding it was the only reason ten
papers appeared free of flaws.  They are now SCORED, so measurement-bias prevalence
saturates at 100% of causal papers and it is the graded severities that keep the domain
discriminating.  Three cuts moved at the same time: content/face validity, previous
literature and any imputation short of multiple imputation now flag.
⚠ Nothing here is "recorded only" any more; the role still exists in the code for any
future item, and the legend only shows roles actually in use.

VERBATIM WORDING, CHECKED AGAINST THE INSTRUMENT
Every question below is quoted from the reviewer instrument itself
(docs/instrument/...Final Reviewer Customaized Version .pdf) and asserted to
appear there, ignoring case and punctuation.  ⚠ The 07_22 artifact PARAPHRASED
several questions ("Did the authors use a validated measurement..." for the
instrument's "Did the authors use validated measurement..."), which is exactly
the drift this assertion exists to stop.  The pypdf text drops the fi/ffi
ligatures, so the normalisation strips non-alphanumerics before comparing.

OUTPUT
  outputs/tables/08_22_2026_scoring_framework_table.html
      the full instrument, one table per task -> Supplementary Table S1, and the
      replacement for artifact 55dac2ad (update that artifact in place, do not
      publish a second one).
  code/figures/08_22_2026_scoring_framework_figure.py imports ITEMS from here for
  the manuscript figure, so the two can never disagree.
"""
import csv, os, re, collections

D = r"."
os.chdir(D)
OUT = "outputs/tables/08_22_2026_scoring_framework_table.html"
SCORED = "data/scoring/07_30_2026_scored_items_long.csv"
INSTRUMENT = ("docs/instrument/Assessment of Healthcare Research in Saudi Arabia "
              "Final Reviewer Customaized Version .pdf")

# =============================================================================
# The instrument.  (item, domain, question, response counted as a problem, axis,
# role).  role: "scored" counts toward the error score; "recorded" is answered
# but excluded from the primary flag; "gate" routes skip logic and is never
# scored.  Order within a task is the order the instrument asks them.
# =============================================================================
SCORED_ROLE, RECORDED, GATE = "scored", "recorded", "gate"

_Q = {  # verbatim, asserted against the PDF below
    "sample_size":      "Was a sample size calculation done?",
    "acc_sampl_d":      "Did the authors account for ineligibility, non-response, loss to "
                        "follow-up, etc. in sample size calculation?",
    "acc_sampl_c":      "Did the authors account for ineligibility, non-response, loss to "
                        "follow-up, change in exposure status over time. etc. in sample size "
                        "calculation?",
    "sample_ach":       "Was the sample size needed achieved?",
    "base_sel":         "Was the baseline selection bias from the investigator accounted for?",
    "comp_dis":         "Did the authors compare the distribution of the exposure and outcome "
                        "between those included (responded) in the study and those not included "
                        "(did not respond) in the study to check if there was selection bias due "
                        "to participant' baseline non-response?",
    "follow":           "Was there a follow-up in the study?",
    "ltfu_bias":        "Was there loss to follow-up bias?",
    "ltfu_acc":         "Was the loss to follow-up bias accounted for?",
    "val_outcome":      "Did the authors use validated measurement for the outcome?",
    "out_bias_acc":     "Was the measurement bias in the outcome accounted for?",
    "diff_out":         "Was the measurement bias in the outcome differential or non-differential "
                        "with respect to the exposure?",
    "val_exposure":     "Did the authors use validated measurement for the exposure?",
    "exp_bias_acc":     "Was the measurement bias in the exposure accounted for?",
    "diff_exp":         "Was the measurement bias in the exposure differential or non-differential "
                        "with respect to the outcome?",
    "dep_or_indep":     "Was the exposure measurement bias independent or dependent of the outcome "
                        "measurement bias?",
    "base_conf_meth":   "What was/were the method(s) used for handling baseline confounding? "
                        "(select all that apply)",
    "conf_var_det":     "How did the authors determine the confounding variables that they have "
                        "adjusted for? (select all that apply)",
    "time_verying":     "Did the authors estimate a time-varying effect?",
    "tv_conf_meth":     "What was/were the method(s) used for handling time-varying confounding? "
                        "(select all that apply)",
    "miss_outcome":     "Was there any participant with a missing outcome?",
    "hand_miss_out":    "Any methods used for handling missing data in outcome?",
    "miss_exposure":    "Was there any participant with a missing exposure?",
    "hand_miss_exp":    "Any methods used for handling missing data in exposure?",
    "err_disc":         "Did the authors qualitatively mention the following errors in the "
                        "discussion section? (select all that apply)",
    "confl_task":       "Did the authors investigate any association beyond their primary "
                        "intention of describing the sample?",
    "design":           "What was the study design?",
    "pop":              "Did the study use data from Saudi Arabia or not?",
    "sampling":         "What was the sampling technique?",
    "outcome_type":     "What was the nature of the outcome?",
    "exposure_type":    "What was the nature of the exposure?",
    "task":             "What was the study task or epidemiological paradigm?",
    "recusal":          "Do you wish to recuse yourself from reviewing this study for any reason?",
}

# ⚠ 2026-08-22 — THE LADDERS ARE NO LONGER DISPLAY-ONLY.  Each ordinal item's options
# are ordered best to worst and carry EQUALLY SPACED severities from 0 to 1: three rungs
# give 0 / 0.5 / 1, five rungs give 0 / 0.25 / 0.5 / 0.75 / 1.  The cuts moved with them,
# so content/face validity, previous literature and any imputation short of multiple
# imputation now flag rather than pass.  STATE drives prevalence and the domain roll-up;
# SEVERITY drives the error score and the validity index.  All read off
# score_dataset_lib.R, and asserted against the scorer's own output below.
GRADED = ("criterion validity <b>passes</b> › content/face validity <b>flags at severity "
          "0.5</b> › <b>No</b> flags at 1.0. “This type of objective measurement does not "
          "usually require validation” is not applicable")
# ⚠ Unlike the other two ladders this order is NOT the instrument's, which lists
# missing-indicator, mean, regression, LOCF, multiple imputation, No.  Best-to-worst here
# is a methodological reading, and since 2026-08-22 the severities follow it.
IMPUTE = ("multiple imputation <b>passes</b> › single imputation by regression flags at "
          "<b>0.25</b> › single imputation by mean or last value carried forward <b>0.5</b> › "
          "missing-indicator modelling <b>0.75</b> › <b>No</b> 1.0")
# ⚠ Confounding control is ONE ladder across TWO items, equally spaced across the pair.
# The worst rung -- no adjustment at all -- is carried by base_conf_meth, so this item
# stops at 2/3.  Before 2026-08-22 it ran to 1 and a paper that adjusted but chose its
# confounders badly scored exactly the same on the domain as one that never adjusted.
CONF_BASIS = ("Based on Directed Acyclic Graphs (DAGs)/subject matter expertise "
              "<b>passes</b> › Based on previous literature <b>flags at severity 1/3</b> › "
              "Based on statistical criteria, change of estimate or none of the above flag at "
              "<b>2/3</b>. <b>Not applicable</b> where no adjustment was attempted, because "
              "that failing is the top rung of this ladder and is scored by the item above")

ITEMS = [
    # (item, task, domain, question key, flagged response, axis, role, condition)
    ("sample_size",        "D", "Random error",     "sample_size",    "<b>No</b>", "reporting", SCORED_ROLE, ""),
    ("acc_sampl",          "D", "Random error",     "acc_sampl_d",    "<b>No</b>", "validity",  SCORED_ROLE, "\u21b3"),
    ("sample_ach",         "D", "Random error",     "sample_ach",     "<b>No</b>", "validity",  SCORED_ROLE, "\u21b3"),
    ("base_sel",           "D", "Selection bias",   "base_sel",       "<b>No</b>", "validity",  SCORED_ROLE, ""),
    ("val_outcome",        "D", "Measurement bias", "val_outcome",    GRADED,      "validity",  SCORED_ROLE, ""),
    ("out_bias_acc",       "D", "Measurement bias", "out_bias_acc",
     "<b>No</b> — and the answer is No on 80 of the 81 descriptive papers", "validity",
     SCORED_ROLE, ""),
    ("miss_outcome",       "D", "Missing data",     "miss_outcome",   "Not reported or unknown", "reporting", SCORED_ROLE, ""),
    ("hand_miss_outcom",   "D", "Missing data",     "hand_miss_out",  IMPUTE,      "validity",  SCORED_ROLE, "\u21b3"),
    ("err_disc",           "D", "Mentioning errors", "err_disc",      "None of the above", "reporting", SCORED_ROLE, ""),
    ("confl_task",         "D", "Conflating task",  "confl_task",     "<b>Yes</b>", "validity", SCORED_ROLE, ""),

    ("sample_size",        "C", "Random error",     "sample_size",    "<b>No</b>", "reporting", SCORED_ROLE, ""),
    ("acc_sampl",          "C", "Random error",     "acc_sampl_c",    "<b>No</b>", "validity",  SCORED_ROLE, "\u21b3"),
    ("sample_ach",         "C", "Random error",     "sample_ach",     "<b>No</b>", "validity",  SCORED_ROLE, "\u21b3"),
    ("base_sel",           "C", "Selection bias",   "base_sel",       "<b>No</b>", "validity",  SCORED_ROLE, ""),
    ("comp_dis",           "C", "Selection bias",   "comp_dis",       "<b>No</b>", "reporting", SCORED_ROLE, ""),
    ("follow",             "C", "Selection bias",   "follow",         "routes the loss-to-follow-up branch", "\u2014", GATE, ""),
    ("ltfu_bias",          "C", "Selection bias",   "ltfu_bias",      "Not reported or unknown", "reporting", SCORED_ROLE, "\u21b3"),
    ("ltfu_acc",           "C", "Selection bias",   "ltfu_acc",       "<b>No</b>", "validity",  SCORED_ROLE, "\u21b3"),
    ("val_outcome",        "C", "Measurement bias", "val_outcome",    GRADED,      "validity",  SCORED_ROLE, ""),
    ("out_bias_acc",       "C", "Measurement bias", "out_bias_acc",
     "<b>No</b> — and the answer is No on 229 of 229 causal papers", "validity",
     SCORED_ROLE, ""),
    ("diff_or_nondiff_out", "C", "Measurement bias", "diff_out",      "<b>Differential</b>", "validity", SCORED_ROLE, ""),
    ("val_exposure",       "C", "Measurement bias", "val_exposure",   GRADED,      "validity",  SCORED_ROLE, ""),
    ("exp_bias_acc",       "C", "Measurement bias", "exp_bias_acc",
     "<b>No</b> — and the answer is No on 229 of 229 causal papers", "validity",
     SCORED_ROLE, ""),
    ("diff_or_nondiff_exp", "C", "Measurement bias", "diff_exp",      "<b>Differential</b>", "validity", SCORED_ROLE, ""),
    ("dep_or_indep_misc",  "C", "Measurement bias", "dep_or_indep",   "<b>Dependent</b>", "validity", SCORED_ROLE, ""),
    ("base_conf_meth",     "C", "Confounding bias", "base_conf_meth",
     "<b>No adjustment for baseline confounding was done</b> — severity 1, the top rung of the "
     "confounding ladder that continues in the next item. Any of the listed methods passes, and "
     "randomised trials analysed by intention to treat are exempt", "validity", SCORED_ROLE, ""),
    ("conf_var_det",       "C", "Confounding bias", "conf_var_det",
     CONF_BASIS, "validity", SCORED_ROLE, ""),
    ("time_verying",       "C", "Confounding bias", "time_verying",   "routes the time-varying branch", "\u2014", GATE, ""),
    ("tv_conf_meth",       "C", "Confounding bias", "tv_conf_meth",
     "a time-varying effect was estimated but no method was recorded; not applicable where none "
     "was estimated", "validity", SCORED_ROLE, "\u21b3"),
    ("miss_outcome",       "C", "Missing data",     "miss_outcome",   "Not reported or unknown", "reporting", SCORED_ROLE, ""),
    ("hand_miss_outcom",   "C", "Missing data",     "hand_miss_out",  IMPUTE,      "validity",  SCORED_ROLE, "\u21b3"),
    ("miss_exposure",      "C", "Missing data",     "miss_exposure",  "Not reported or unknown", "reporting", SCORED_ROLE, ""),
    ("hand_miss_exposure", "C", "Missing data",     "hand_miss_exp",  IMPUTE,      "validity",  SCORED_ROLE, "\u21b3"),
    ("err_disc",           "C", "Mentioning errors", "err_disc",      "None of the above", "reporting", SCORED_ROLE, ""),
]

CLASSIFIERS = [
    ("task",          "Study task (epidemiological paradigm)", "task",
     "predetermined by two study team members; routes the whole instrument"),
    ("recusal",       "Reviewer recusal",                      "recusal",
     "withdraws the reviewer from the paper"),
    ("design",        "Study design",                          "design",
     "reported as a study characteristic; also checks the follow-up gate"),
    ("pop",           "Use of Saudi data",                     "pop",
     "stratifier"),
    ("sampling",      "Sampling technique",                    "sampling",
     "whole-population sampling skips the entire random-error domain"),
    ("outcome_type",  "Nature of the outcome",                 "outcome_type",
     "objective vs subjective; sets which measurement items apply"),
    ("exposure_type", "Nature of the exposure",                "exposure_type",
     "objective vs subjective; causal only"),
]

DOM_ORDER = ["Random error", "Selection bias", "Measurement bias", "Confounding bias",
             "Missing data", "Mentioning errors", "Conflating task"]
TASKNAME = {"D": "Descriptive", "C": "Causal"}

# =============================================================================
# Checks.  These are the whole point of the file.
# =============================================================================
norm = lambda s: re.sub(r"[^a-z0-9]", "", re.sub(r"<[^>]+>", "", s).lower())

from pypdf import PdfReader
_pdf = norm("\n".join(p.extract_text() or "" for p in PdfReader(INSTRUMENT).pages))
_missing = sorted(k for k, q in _Q.items() if norm(q) not in _pdf)
assert not _missing, "not found verbatim in the instrument: %s" % _missing

_scored = list(csv.DictReader(open(SCORED, encoding="utf-8-sig")))
PAPERS = {t: len({r["PMID"] for r in _scored if r["Study_Type"] == t})
          for t in ("Causal", "Descriptive")}
_primary = collections.Counter()
for r in _scored:
    if r["primary"] in ("TRUE", "True", "1"):
        _primary[(r["Study_Type"], r["domain"], r["item"])] += 1
_from_scorer = collections.Counter((t, d) for (t, d, _i) in _primary)
_from_table = collections.Counter((TASKNAME[t], dom) for (_i, t, dom, _q, _f, _a, role, _c)
                                  in ITEMS if role == SCORED_ROLE)
assert _from_scorer == _from_table, (
    "the table disagrees with the scorer",
    {k: (_from_scorer.get(k), _from_table.get(k))
     for k in set(_from_scorer) | set(_from_table) if _from_scorer.get(k) != _from_table.get(k)})
# and the item NAMES must match, not merely the counts - the manuscript's Table 1
# reached the right causal total while naming two wrong items
_names_scorer = {(t, i) for (t, _d, i) in _primary}
_names_table = {(TASKNAME[t], i) for (i, t, _d, _q, _f, _a, role, _c) in ITEMS if role == SCORED_ROLE}
assert _names_scorer == _names_table, sorted(_names_scorer ^ _names_table)

# ⚠ The wording of the three confounding rows above asserts what the scorer can and
# cannot produce, so it is checked here.  Two coded branches never fire on these data:
# neither confounding question offers a "not reported" option, so neither can register a
# reporting gap; and both papers that estimated a time-varying effect recorded a method,
# so that item registers no flaw.  An earlier version of this table claimed a
# reporting-gap branch for base_conf_meth and a flaw for tv_conf_meth - describing code
# paths rather than the instrument.  If new data makes either fire, this fails and the
# wording has to be revisited rather than quietly becoming wrong again.
STATES = collections.defaultdict(collections.Counter)
for r in _scored:
    STATES[(r["Study_Type"][0], r["item"])][r["state"]] += 1
assert STATES[("C", "base_conf_meth")]["REP"] == 0, STATES[("C", "base_conf_meth")]
assert STATES[("C", "conf_var_det")]["REP"] == 0, STATES[("C", "conf_var_det")]
assert STATES[("C", "tv_conf_meth")]["VAL"] == 0 and STATES[("C", "tv_conf_meth")]["REP"] == 0
# gradestate() maps "not reported"/"unknown" to a reporting gap, but the two validation
# questions offer only criterion / content-face / does-not-require / No, so it never fires
for _t, _i in (("C", "val_outcome"), ("C", "val_exposure"), ("D", "val_outcome")):
    assert STATES[(_t, _i)]["REP"] == 0, (_t, _i, STATES[(_t, _i)])

assert STATES[("C", "conf_var_det")]["NA"] == 113, STATES[("C", "conf_var_det")]

# ⚠ CONF_BASIS states where the cut falls, so the cut is checked, not trusted.  The
# ladder is the instrument's option order and is DISPLAY only: the top two rungs both
# pass, exactly as criterion and content/face validity both pass on val_outcome.  TSA
# ruled on 2026-08-22 that it stays that way; moving the cut to DAG-only would take
# confounding from 79.9% to 87.8% of causal papers and the mean error score from 3.64
# to 3.72, so it is a scoring change, not a formatting one.
# Each moved cut is asserted per paper against the scorer's own output, so the wording
# above cannot drift from the code: only a DAG basis, only criterion validity and only
# multiple imputation may pass.
def _cut(item, passes, label):
    for r in _scored:
        if r["item"] != item or r["state"] == "NA":
            continue
        assert (r["state"] == "OK") == passes(r["raw"].lower()), (label, r["PMID"], r["state"], r["raw"])


_cut("conf_var_det", lambda v: "directed acyclic" in v, "confounder basis")
for _v in ("val_outcome", "val_exposure"):
    _cut(_v, lambda v: "criterion" in v, "measurement validation")
for _v in ("hand_miss_outcom", "hand_miss_exposure"):
    _cut(_v, lambda v: "multiple imputation" in v, "missing-data handling")
# and the severities really are the equally spaced ladders described above
_SEV = (0.0, 0.25, 1 / 3, 0.5, 2 / 3, 0.75, 1.0)
for r in _scored:
    if r["state"] == "VAL" and r["primary"] in ("TRUE", "True", "1"):
        assert any(abs(float(r["severity"]) - v) < 1e-6 for v in _SEV), (r["item"], r["severity"])
# ⚠ THE INVARIANT THE RESPACING EXISTS FOR: across the two confounding items, every
# causal paper must land on one of four equally spaced rungs, and a paper that adjusted
# must never score as badly as one that did not.
_rung = collections.Counter()
_conf = collections.defaultdict(dict)
for r in _scored:
    if r["Study_Type"] == "Causal" and r["item"] in ("base_conf_meth", "conf_var_det"):
        _conf[r["PMID"]][r["item"]] = r
for _p, _d in _conf.items():
    _t = sum(float(_d[i]["severity"]) for i in _d if _d[i]["state"] == "VAL")
    assert min(abs(_t - v) for v in (0.0, 1 / 3, 2 / 3, 1.0)) < 1e-6, (_p, _t)
    _rung[round(_t, 3)] += 1
assert sorted(_rung) == [0.0, 0.333, 0.667, 1.0] and sum(_rung.values()) == 229, _rung

N_SCORED = {t: sum(1 for x in ITEMS if x[1] == t and x[6] == SCORED_ROLE) for t in "DC"}
N_TOTAL = {t: sum(1 for x in ITEMS if x[1] == t and x[6] != GATE) for t in "DC"}
N_GATE = {t: sum(1 for x in ITEMS if x[1] == t and x[6] == GATE) for t in "DC"}
assert (N_SCORED["C"], N_SCORED["D"]) == (22, 10), N_SCORED
assert (N_TOTAL["C"], N_TOTAL["D"]) == (22, 10), N_TOTAL   # nothing recorded-only now

CENSUS = dict(total=385, causal=PAPERS["Causal"], descriptive=PAPERS["Descriptive"], predictive=75)
assert CENSUS["causal"] == 229 and CENSUS["descriptive"] == 81
assert CENSUS["causal"] + CENSUS["descriptive"] + CENSUS["predictive"] == CENSUS["total"]

# =============================================================================
# Render
# =============================================================================
CSS = """
:root{--ink:#111417;--mut:#4a5259;--ac:#16697a;--rule:#dfe4e7;--rule2:#eef1f3;--bg:#fff;
      --band:#f4f7f8;--grey:#8b8f94}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);
     font:15px/1.55 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;
     font-variant-numeric:tabular-nums}
.wrap{max-width:1080px;margin:0 auto;padding:40px 24px 72px}
h1{font-family:Georgia,"Times New Roman",serif;font-size:30px;line-height:1.2;margin:0 0 6px}
h2{font-family:Georgia,serif;font-size:20px;margin:38px 0 4px}
.sub{color:var(--mut);font-size:14px;margin:0 0 26px}
.lede{color:var(--mut);max-width:74ch;margin:0 0 22px}
.census{display:flex;flex-wrap:wrap;gap:10px;margin:0 0 26px}
.stat{border:1px solid var(--rule);border-radius:8px;padding:9px 14px;min-width:104px}
.stat b{display:block;font-size:21px;line-height:1.1}
.stat span{color:var(--mut);font-size:12px}
.key{display:flex;flex-wrap:wrap;gap:16px;margin:0 0 20px;font-size:12.5px;color:var(--mut)}
.key i{font-style:normal;border-radius:4px;padding:1px 7px;margin-right:5px;
       background:var(--band);color:var(--ac);font-weight:600}
table{border-collapse:collapse;width:100%;font-size:13.5px;margin:6px 0 4px}
th{text-align:left;font-weight:600;color:var(--mut);font-size:12px;text-transform:uppercase;
   letter-spacing:.04em;border-bottom:1px solid var(--rule);padding:7px 9px;vertical-align:bottom}
td{border-bottom:1px solid var(--rule2);padding:7px 9px;vertical-align:top}
tr.dom td{background:var(--band);font-weight:600;color:var(--ac);font-size:12.5px;
          letter-spacing:.02em;border-bottom:1px solid var(--rule)}
td.n{color:var(--mut);width:34px;text-align:right;white-space:nowrap}
td.ax{white-space:nowrap;color:var(--mut);font-size:12px;width:88px}
td.rl{white-space:nowrap;font-size:12px;width:118px}
tr.off td{color:var(--grey)}
tr.gate td{color:var(--grey);font-style:italic}
.tag{border-radius:4px;padding:1px 7px;font-size:11.5px;white-space:nowrap}
.t-s{background:#e6f0f2;color:#0f5c6b}.t-r{background:#f3f4f5;color:#6b7075}
.t-g{background:#faf3e6;color:#7a4d0d}
.note{color:var(--mut);font-size:13px;max-width:80ch;margin:14px 0 0}
.cond{color:var(--ac);margin-right:4px}
footer{margin-top:44px;border-top:1px solid var(--rule);padding-top:16px;
       color:var(--mut);font-size:12.5px;max-width:86ch}
footer b{color:var(--ink)}
"""


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def task_table(t):
    rows, n = [], 0
    body = ""
    for dom in DOM_ORDER:
        block = [x for x in ITEMS if x[1] == t and x[2] == dom]
        if not block:
            continue
        body += '<tr class="dom"><td colspan="5">%s</td></tr>' % dom
        for item, _t, _d, qk, flagged, axis, role, cond in block:
            cls = {SCORED_ROLE: "", RECORDED: "off", GATE: "gate"}[role]
            if role == SCORED_ROLE:
                n += 1
                num = str(n)
                tag = '<span class="tag t-s">counts</span>'
            elif role == RECORDED:
                num = "\u2013"
                tag = '<span class="tag t-r">recorded only</span>'
            else:
                num = "\u2013"
                tag = '<span class="tag t-g">gate</span>'
            q = ('<span class="cond">%s</span>' % cond if cond else "") + esc(_Q[qk])
            body += ('<tr class="%s"><td class="n">%s</td><td>%s</td><td>%s</td>'
                     '<td class="ax">%s</td><td class="rl">%s</td></tr>'
                     % (cls, num, q, flagged, axis, tag))
    assert n == N_SCORED[t], (t, n)
    return ('<table><thead><tr><th>#</th><th>Item, as the reviewer was asked it</th>'
            '<th>Response counted as a problem</th><th>Axis</th><th>In the score</th>'
            '</tr></thead><tbody>%s</tbody></table>' % body)


html = ['<!doctype html><html lang="en"><head><meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width,initial-scale=1">',
        '<title>Scoring framework by study task</title><style>%s</style></head><body><div class="wrap">' % CSS]
html.append('<h1>Risk-of-bias scoring framework, by study task</h1>')
html.append('<p class="sub">Assessment of Healthcare Research Quality &middot; Saudi Arabia &middot; '
            '2022 baseline</p>')
html.append('<p class="lede">Every included paper was appraised against its predetermined study '
            'task. Each item is a reporting question (was it reported?) or a validity question '
            '(was it done well?); the response that the scorer counts as a problem is given in the '
            'third column. Graded items run best&nbsp;&rsaquo;&nbsp;worst.</p>')
html.append('<div class="census">'
            '<div class="stat"><b>%d</b><span>papers appraised</span></div>'
            '<div class="stat"><b>%d</b><span>scored for bias</span></div>'
            '<div class="stat"><b>%d</b><span>causal</span></div>'
            '<div class="stat"><b>%d</b><span>descriptive</span></div>'
            '<div class="stat"><b>%d</b><span>predictive, not scored</span></div></div>'
            % (CENSUS["total"], CENSUS["causal"] + CENSUS["descriptive"], CENSUS["causal"],
               CENSUS["descriptive"], CENSUS["predictive"]))
html.append('<div class="key">'
            '<span><i>counts</i>contributes to the error score</span>'
            '<span><i>recorded only</i>answered, but excluded from the score</span>'
            '<span><i>gate</i>routes skip logic; never scored</span>'
            '<span><span class="cond">\u21b3</span>conditional on the item above</span></div>')

for t in ("C", "D"):
    html.append('<h2>%s &middot; %d papers</h2>' % (TASKNAME[t], CENSUS[TASKNAME[t].lower()]))
    html.append('<p class="sub"><b>%d scored items</b> across %d domains, %d further items '
                'recorded but not scored%s</p>'
                % (N_SCORED[t], len({x[2] for x in ITEMS if x[1] == t and x[6] == SCORED_ROLE}),
                   N_TOTAL[t] - N_SCORED[t],
                   ", and %d gates" % N_GATE[t] if N_GATE[t] else ""))
    html.append(task_table(t))

html.append('<h2>Predictive &middot; %d papers</h2>' % CENSUS["predictive"])
html.append('<p class="note">Predictive studies were characterised by design and population only. '
            'The instrument assigns them no reporting or validity items, so they are excluded from '
            'every bias prevalence and error score and reported as a count. That leaves '
            '<b>%d of the %d papers scored</b>.</p>'
            % (CENSUS["causal"] + CENSUS["descriptive"], CENSUS["total"]))

html.append('<h2>Items that classify rather than score</h2>')
html.append('<p class="note">These establish applicability and strata. They are unrelated to '
            'reporting or validity, so they carry no problem response and never enter the score.</p>')
html.append('<table><thead><tr><th>Item</th><th>As the reviewer was asked it</th>'
            '<th>What it does</th></tr></thead><tbody>'
            + "".join('<tr><td>%s</td><td>%s</td><td>%s</td></tr>' % (lab, esc(_Q[qk]), what)
                      for _i, lab, qk, what in CLASSIFIERS)
            + '</tbody></table>')

# Footnotes live here as PLAIN TEXT because two renderings use them: this HTML and
# the print-native PDF/TIFF/PNG built by 08_22_2026_scoring_framework_print_table.py.
# Written once, or they drift.
FOOTNOTES = [
    ("Four states, one per study × item.",
     "Not applicable where the instrument does not ask the question of that paper; no issue "
     "where it was reported and judged sound; reporting gap where it was not reported in enough "
     "detail to judge; validity flaw where it was reported and judged unfavourably. "
     "“Skipped” and “should be skipped” are not applicable; “not "
     "reported or unknown” is a reporting gap, not a pass."),
    ("Domains roll up by weakest link:",
     "a validity flaw if any constituent item is flawed, a reporting gap if none is flawed but "
     "at least one cannot be judged, and no issue only when every applicable item is sound."),
    ("Denominators are per domain,",
     "not the full sample: applicability is decided study by study, so every prevalence is "
     "computed on the studies the domain applies to."),
    ("Severities are equally spaced.",
     "Each ordinal item’s response options are ordered best to worst and assigned "
     "severities from 0 to 1 in equal steps — three rungs give 0, 0.5 and 1; the "
     "five-rung imputation ladder gives 0, 0.25, 0.5, 0.75 and 1. Every other item is "
     "binary, costing 1 when it flags. The state is what prevalence and the domain "
     "roll-up are built on; the severity is what the error score and the validity index "
     "are built on, so a weaker attempt costs less than no attempt without changing how "
     "often a domain is flagged."),
    ("The two measurement-accounting items are scored, and they never pass.",
     "“Was the measurement bias in the outcome / exposure accounted for?” is "
     "“No” on 229 of 229 causal papers and 80 of 81 descriptive. They were "
     "excluded until 2026-08-22 because a constant cannot separate papers; they are now "
     "scored because a constant sitting at total failure is a finding rather than a "
     "nuisance. Measurement-bias prevalence therefore saturates at 100% of causal papers, "
     "and it is the graded severities that keep the domain discriminating."),
    ("Randomised trials analysed by intention to treat",
     "are exempt from the confounding-control item, because randomisation addresses confounding "
     "by design; two trials reporting an unadjusted per-protocol analysis keep the flaw."),
    ("Provenance.",
     "Item wording is quoted from the reviewer instrument and asserted against it; the "
     "scored-item set is asserted by name against the scorer’s own output. Generated by "
     "code/tables/08_22_2026_scoring_framework.py."),
]

html.append("<footer>" + "".join(
    "<p><b>%s</b> %s</p>" % (esc(h).replace("&lt;b&gt;", "<b>"), esc(b)) for h, b in FOOTNOTES)
    + "</footer>")
html.append('</div></body></html>')

open(OUT, "w", encoding="utf-8").write("\n".join(html))
print("  %-58s %7.1f KB" % (OUT, os.path.getsize(OUT) / 1024))
print("  census   %d papers = %d causal + %d descriptive + %d predictive; %d scored"
      % (CENSUS["total"], CENSUS["causal"], CENSUS["descriptive"], CENSUS["predictive"],
         CENSUS["causal"] + CENSUS["descriptive"]))
print("  causal   %d scored + %d recorded-only + %d gates = %d asked"
      % (N_SCORED["C"], N_TOTAL["C"] - N_SCORED["C"], N_GATE["C"], N_TOTAL["C"] + N_GATE["C"]))
print("  descr.   %d scored + %d recorded-only = %d asked"
      % (N_SCORED["D"], N_TOTAL["D"] - N_SCORED["D"], N_TOTAL["D"]))
print("  checked  %d questions verbatim against the instrument PDF; item set matches the scorer"
      % len(_Q))

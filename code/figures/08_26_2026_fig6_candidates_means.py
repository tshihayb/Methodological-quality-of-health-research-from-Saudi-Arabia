# -*- coding: utf-8 -*-
"""Figure 6 re-cut — CANDIDATES FOR THE TWO MEASURE SETS TSA ASKED FOR (2026-08-26).

    python code/figures/08_26_2026_fig6_candidates_means.py [CODE ...]

TSA: "the figure should only compare means of the Validity error score, Transparency score,
Domains with a validity flaw, Domains with a reporting gap, Validity index, Transparency index,
and Acknowledgement index.  Alternatively, we could compare the means of Validity index,
Transparency index, and Acknowledgement index only."

Those are exactly Figure 5's study-level panels: the seven are panels D-I plus K, and the three
are the normalised ones, F, I and K.  So Figure 6 becomes "the means of Figure 5's study-level
distributions, by group" — which is a much tighter brief than the earlier A-N set, and drops the
per-domain machinery (the four-state verdict, the not-reported band) entirely.

  SEVEN-MEASURE SET   7A 7B 7C 7D 7E
  THREE-INDEX SET     3A 3B 3C 3D 3E

⚠ TWO THINGS THE DATA FORCED ON THE DESIGN, both verified at source rather than assumed:

1. FOR DESCRIPTIVE PAPERS, "Transparency score" AND "Domains with a reporting gap" ARE THE SAME
   VARIABLE — identical on 81 of 81 papers, because each descriptive domain carries at most one
   reporting item, so the count of gaps IS the count of gapped domains.  They differ on 184 of
   the 229 causal papers.  A seven-measure figure therefore draws one column twice on its
   descriptive side; the designs below say so on the figure rather than letting the reader find
   two identical columns and mistrust the rest.

2. HIGHER IS WORSE FOR FOUR OF THE SEVEN AND BETTER FOR THREE.  Any display that puts them on a
   common signed scale has to orient them, or a bar pointing right means "worse" in one column
   and "better" in the next.  7D and 7E flip the three indices so the whole figure reads
   worse-to-the-right, and mark every flipped column.

⚠ AND ONE TRAP AVOIDED: the three indices' correlations are a Simpson's paradox across tasks.
   Validity~acknowledgement is -0.32 pooled over the 50 groups but -0.11 descriptive and +0.62
   causal.  Every correlation on these figures is computed WITHIN task.

Toolkit, data and the derived-facts block are imported from 08_26_2026_fig6_candidates.py so the
two candidate sets cannot drift apart.

OUTPUT  outputs/figures/candidates/08_26_2026_fig6_<CODE>.png
"""
import os, sys, math, importlib.util
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

D = r"."
os.chdir(D)
_spec = importlib.util.spec_from_file_location("fig6", "code/figures/08_26_2026_fig6_candidates.py")
C = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(C)                       # guarded by __main__; importing draws nothing

W, L, R, MIN_PT = C.W, C.L, C.R, C.MIN_PT
INK, MUT, FAINT, AC, RULE = C.INK, C.MUT, C.FAINT, C.AC, C.RULE
VAL, REP, OK = C.VAL, C.REP, C.OK
T_TITLE, T_HEAD, T_BODY, T_SMALL = C.T_TITLE, C.T_HEAD, C.T_BODY, C.T_SMALL
line_h, Cv, HH = C.line_h, C.Cv, C.HH
TASKS, DTASK, STRATS, lab, prose = C.TASKS, C.DTASK, C.STRATS, C.lab, C.prose
su, pl, ROW, TN = C.su, C.pl, C.ROW, C.TN
OUTDIR = C.OUTDIR

# =============================================================================================
# The seven measures, in Figure 5's own order and wording.
#   key · sd key · per-paper column · short label · sub-label · higher-is-worse?
# =============================================================================================
M7 = [("mean_err_w", "sd_err_w", "error_weighted", "Validity error score",
       "weighted by severity", True),
      ("mean_rep_gap", "sd_rep_gap", "n_rep_gaps", "Transparency score",
       "reporting gaps per paper", True),
      ("mean_dom_flag", "sd_dom_flag", "domains_flagged", "Domains with a validity flaw",
       "count per paper, of 7", True),
      ("mean_dom_gap", "sd_dom_gap", "dom_gapped", "Domains with a reporting gap",
       "count per paper, of 7", True),
      ("mean_validity", "sd_validity", "validity", "Validity index",
       "1 − flaws / judgeable items", False),
      ("mean_transparency", "sd_transparency", "transparency", "Transparency index",
       "1 − gaps / applicable items", False),
      ("mean_ack", "sd_ack", "acknowledgement", "Acknowledgement index",
       "own flagged domains named", False)]
M3 = [m for m in M7 if not m[5]]                   # the three normalised indices
assert len(M3) == 3 and [m[3] for m in M3] == ["Validity index", "Transparency index",
                                               "Acknowledgement index"]
SHORT7 = {"Validity error score": "Validity\nerror score",
          "Transparency score": "Transparency\nscore",
          "Domains with a validity flaw": "Domains with a\nvalidity flaw",
          "Domains with a reporting gap": "Domains with a\nreporting gap",
          "Validity index": "Validity\nindex", "Transparency index": "Transparency\nindex",
          "Acknowledgement index": "Acknowledge-\nment index"}

# ---- paper-level reference values: the mean and SD each measure has across papers ----------
def _pv(pk, t):
    v = pl.loc[pl.Study_Type == t, pk]
    return v.dropna() if pk == "acknowledgement" else v


PM = {(m[0], t): float(_pv(m[2], t).mean()) for m in M7 for t in TASKS}
PS = {(m[0], t): float(_pv(m[2], t).std()) for m in M7 for t in TASKS}
# the 25 group means must average back to the paper mean (weighted) — assert, do not assume
for m in M7:
    for t in TASKS:
        for nm, _s, _l in STRATS:
            g = su[(su.stratifier == nm) & (su.task == t)]
            wt = g.n_ack_elig if m[0] == "mean_ack" else g.N
            assert abs((g[m[0]] * wt).sum() / wt.sum() - PM[(m[0], t)]) < 1e-6, (m[0], t, nm)
# range the 25 group means occupy, per measure and task — every scale on these pages
GR = {(m[0], t): (float(su[su.task == t][m[0]].min()), float(su[su.task == t][m[0]].max()))
      for m in M7 for t in TASKS}
SEP = {(m[0], t): (GR[(m[0], t)][1] - GR[(m[0], t)][0]) / PS[(m[0], t)] for m in M7 for t in TASKS}

# ---- ⚠ the duplicate column, established from the papers, not from the column names --------
DUP = {t: int((_pv("n_rep_gaps", t).values == _pv("dom_gapped", t).values).sum()) for t in TASKS}
NP = {t: int((pl.Study_Type == t).sum()) for t in TASKS}
assert DUP["Descriptive"] == NP["Descriptive"], "the descriptive duplicate no longer holds"
assert DUP["Causal"] < NP["Causal"]
DUPNOTE = ("For descriptive papers the transparency score and the count of gapped domains are "
           "the same variable — identical on all %d, because a descriptive domain carries at "
           "most one reporting item. They differ on %d of the %d causal papers."
           % (NP["Descriptive"], NP["Causal"] - DUP["Causal"], NP["Causal"]))

# ---- within-task correlations among the three indices (never pooled: Simpson's paradox) ----
COR = {}
for t in TASKS:
    d = su[su.task == t][[m[0] for m in M3]].dropna()
    c = d.corr()
    COR[t] = (c.iloc[0, 1], c.iloc[0, 2], c.iloc[1, 2])
_pool = su[[m[0] for m in M3]].dropna().corr().iloc[0, 2]
assert _pool < 0 < COR["Causal"][1], ("the Simpson reversal no longer holds", _pool, COR)

NLEV = len(su) // 2
SRC7 = ("310 scored studies (229 causal, 81 descriptive; predictive studies carry no bias "
        "items). The seven measures are Figure 5's study-level panels D–I and K, computed on "
        "Figure 5's own definitions. Descriptive and causal papers carry different numbers of "
        "items and are never compared to each other. All associational and unadjusted; group "
        "membership is not randomised. code/scoring/07_30_2026_stratified_analysis.R.")
SRC3 = ("310 scored studies (229 causal, 81 descriptive). The three indices are Figure 5's "
        "panels F, I and K — each a rate over that paper's own applicable items, so unlike the "
        "raw scores they share one 0–1 scale. Correlations are computed within task: pooled "
        "over both, validity–acknowledgement reverses sign (%+.2f pooled against %+.2f causal), "
        "which is an artefact of the task mix. All associational and unadjusted. "
        "code/scoring/07_30_2026_stratified_analysis.R." % (_pool, COR["Causal"][1]))
TITLE = C.TITLE
LEVELS = [(nm, lv) for nm, _s, lvs in STRATS for lv in lvs]
SE = lambda r, sk, nk="N": float(r[sk]) / math.sqrt(float(r[nk]))


def taskblock(cv, y, t, extra=""):
    cv.T(L, y, "%s studies · n=%d" % (t, TN[t]), T_HEAD, DTASK[t], "bold")
    if extra:
        cv.T(L + cv.width("%s studies · n=%d" % (t, TN[t]), T_HEAD, "bold") + 3.0, y + 0.3,
             extra, T_SMALL, FAINT)
    return y + 5.0


def zsign(r, m, t):
    """The group's distance from its task mean in paper-level SD units, ORIENTED so that
    positive always means worse quality — the three indices run the other way."""
    v = float(r[m[0]])
    z = (v - PM[(m[0], t)]) / PS[(m[0], t)]
    return z if m[5] else -z


# =============================================================================================
# 7A — the matrix: 25 groups x 7 measures, each cell spanning that measure's group-mean range
# =============================================================================================
def cand_7A():
    RH, GH, GAP, LBL = 3.4, 4.3, 1.0, 33.0
    CW = (W - L - R - LBL) / 7.0
    cv = Cv()
    y = cv.head(6.0, TITLE,
                "The seven study-level measures of Figure 5, as group means. Each cell spans the "
                "full range the %d group means occupy for that measure and task, so a dot at the "
                "left edge is the cleanest group and one at the right the worst; the tick is the "
                "task mean. Nothing here is a scale you can read a value off — the ranges are "
                "printed in the column heads, and no range exceeds %.2f of a between-paper SD."
                % (NLEV, max(SEP.values())))
    for j, m in enumerate(M7):
        cx = L + LBL + j * CW
        for q, s in enumerate(SHORT7[m[3]].split("\n")):
            cv.T(cx + CW / 2 - 0.5, y + q * line_h(T_SMALL), s, T_SMALL, INK, "bold", ha="center")
        yy = y + 2 * line_h(T_SMALL) + 0.4
        for t in TASKS:
            a, b = GR[(m[0], t)]
            cv.T(cx + CW / 2 - 0.5, yy, "%s %.2f–%.2f" % (t[0], a, b), T_SMALL, DTASK[t],
                 ha="center")
            yy += line_h(T_SMALL)
    y += 2 * line_h(T_SMALL) + 0.4 + 2 * line_h(T_SMALL) + 1.6
    cv.T(L, y - 3.0, "Group", T_HEAD, FAINT, "bold")
    cv.ln(L, y - 0.8, W - R, y - 0.8, INK, 0.7)
    for nm, short, lvs in STRATS:
        cv.T(L, y, nm, T_BODY, INK, "bold")
        y += GH
        for lv in lvs:
            r = {t: ROW(nm, lv, t) for t in TASKS}
            cv.T(L + 1.5, y + RH / 2 - 0.3, lab(lv), T_SMALL, MUT, va="center")
            cv.T(L + LBL - 2.0, y + RH / 2 - 0.3,
                 "%d|%d" % (int(r["Descriptive"].N), int(r["Causal"].N)),
                 T_SMALL, FAINT, ha="right", va="center")
            for j, m in enumerate(M7):
                cx = L + LBL + j * CW + 2.0
                pw = CW - 5.0
                cv.bar(cx, y + 0.5, pw, RH - 1.2, "#f4f6f7", z=1)
                for t in TASKS:
                    a, b = GR[(m[0], t)]
                    mk = cx + (PM[(m[0], t)] - a) / (b - a) * pw
                    cv.ln(mk, y + 0.5, mk, y + RH - 0.7, "#ffffff", 0.8, 2)
                    v = float(r[t][m[0]])
                    cv.dot(cx + (v - a) / (b - a) * pw,
                           y + (RH / 2 - 0.9 if t == "Descriptive" else RH / 2 + 0.3),
                           0.62, DTASK[t], z=5)
            y += RH
        cv.ln(L, y + GAP / 2, W - R, y + GAP / 2, "#eef1f3", 0.4, 1)
        y += GAP
    cv.T(L, y, "n shown as descriptive | causal · white tick in each cell is that task's mean "
         "over all its papers · upper dot descriptive, lower dot causal", T_SMALL, MUT)
    y += 4.0
    cv.taskkey(L, y)
    y += 5.5
    for ln in cv.wrap("⚠ " + DUPNOTE + " The two columns are drawn anyway so the two tasks stay "
                      "structurally parallel; on the descriptive row they carry one result, not "
                      "two.", W - L - R, T_SMALL):
        cv.T(L, y, ln, T_SMALL, REP)
        y += line_h(T_SMALL)
    y += 2.0
    return cv, cv.foot(y, SRC7), "7A"


# =============================================================================================
# 7B — measure-first: seven panels, ten stratifier lollipops each
# =============================================================================================
def cand_7B():
    NC, PGAP = 2, 8.0
    PW = (W - L - R - PGAP) / NC
    RH = 3.5
    LBLW = 26.0
    HW = (PW - LBLW - 8.0) / 2.0
    cv = Cv()
    y = cv.head(6.0, TITLE,
                "One panel per measure, and inside it one rule per grouping variable running "
                "from its cleanest group to its worst. This asks which variable moves which "
                "measure. Journal quartile owns the widest rule in %d of the %d panel-halves; "
                "no rule anywhere spans more than %.2f of a between-paper SD."
                % (sum(1 for m in M7 for t in TASKS
                       if max(STRATS, key=lambda s: _spread(s[0], m, t))[0] == "JCR 2022 quartile"),
                   2 * len(M7), max(SEP.values())))
    for i, m in enumerate(M7):
        r_, c_ = divmod(i, NC)
        px = L + c_ * (PW + PGAP)
        py = y + r_ * (len(STRATS) * RH + 12.0)
        cv.T(px, py, "%s  %s" % ("DEFGHIK"[i], m[3]), T_HEAD, INK, "bold")
        cv.T(px + PW, py + 0.3, m[4], T_SMALL, FAINT, ha="right")
        py += 6.6         # the per-task range strip is set at py − 3.6 and needs its own line
        for k, t in enumerate(TASKS):
            x0 = px + LBLW + k * (HW + 8.0)
            a, b = GR[(m[0], t)]
            pad = (b - a) * 0.12
            a, b = a - pad, b + pad
            sx = lambda v: x0 + (v - a) / (b - a) * HW
            cv.T(x0 + HW / 2, py - 3.6, "%s  %.2f–%.2f  ·  %.2f SD"
                 % (t[0], GR[(m[0], t)][0], GR[(m[0], t)][1], SEP[(m[0], t)]),
                 T_SMALL, DTASK[t], ha="center")
            cv.ln(sx(PM[(m[0], t)]), py - 0.8, sx(PM[(m[0], t)]), py + len(STRATS) * RH - 1.2,
                  INK, 0.6, 5, (0, (2.0, 1.4)))
            for q, (nm, short, lvs) in enumerate(STRATS):
                vs = sorted(float(ROW(nm, lv, t)[m[0]]) for lv in lvs)
                cy = py + q * RH + RH / 2 - 0.4
                cv.ln(sx(vs[0]), cy, sx(vs[-1]), cy, DTASK[t], 1.1, 4)
                for v in vs:
                    cv.dot(sx(v), cy, 0.55, DTASK[t], "white", 6, 0.3)
                if k == 0:
                    cv.T(px, cy, short, T_SMALL, MUT, va="center")
    y += ((len(M7) + NC - 1) // NC) * (len(STRATS) * RH + 12.0) - 4.0
    cv.T(L, y, "dashed rule = the task mean over all its papers · dots are the group means of "
         "that variable · left = cleaner", T_SMALL, MUT)
    y += 4.0
    cv.taskkey(L, y)
    y += 5.5
    for ln in cv.wrap("⚠ " + DUPNOTE, W - L - R, T_SMALL):
        cv.T(L, y, ln, T_SMALL, REP)
        y += line_h(T_SMALL)
    y += 2.0
    return cv, cv.foot(y, SRC7), "7B"


def _spread(nm, m, t):
    vs = [float(ROW(nm, lv, t)[m[0]]) for lv in dict((a, c) for a, _b, c in STRATS)[nm]]
    return max(vs) - min(vs)


# =============================================================================================
# 7C — the numbers themselves, shaded within measure and task
# =============================================================================================
def cand_7C():
    RH, GH, GAP, LBL = 3.6, 4.4, 1.0, 30.0
    CW = (W - L - R - LBL) / 7.0
    cv = Cv()
    y = cv.head(6.0, TITLE,
                "Every group mean printed, on all seven of Figure 5's study-level measures. Each "
                "cell is shaded by where it falls between the best and worst group mean for that "
                "measure and task, so the shading ranks within a column and never across one. "
                "The numbers are the deliverable; the shading only shows where to look.")
    for j, m in enumerate(M7):
        cx = L + LBL + j * CW
        for q, s in enumerate(SHORT7[m[3]].split("\n")):
            cv.T(cx + CW / 2, y + q * line_h(T_SMALL), s, T_SMALL, INK, "bold", ha="center")
    y += 2 * line_h(T_SMALL) + 1.0
    for j, m in enumerate(M7):
        cv.T(L + LBL + j * CW + CW / 2, y, "D      C", T_SMALL, FAINT, ha="center")
    y += line_h(T_SMALL) + 1.2
    cv.T(L, y - 8.0, "Group", T_HEAD, FAINT, "bold")
    cv.ln(L, y - 0.8, W - R, y - 0.8, INK, 0.7)
    for nm, short, lvs in STRATS:
        cv.T(L, y, nm, T_BODY, INK, "bold")
        y += GH
        for lv in lvs:
            cv.T(L + 1.5, y + RH / 2 - 0.3, lab(lv), T_SMALL, MUT, va="center")
            r = {t: ROW(nm, lv, t) for t in TASKS}
            cv.T(L + LBL - 2.0, y + RH / 2 - 0.3,
                 "%d|%d" % (int(r["Descriptive"].N), int(r["Causal"].N)),
                 T_SMALL, FAINT, ha="right", va="center")
            for j, m in enumerate(M7):
                for k, t in enumerate(TASKS):
                    a, b = GR[(m[0], t)]
                    v = float(r[t][m[0]])
                    f = (v - a) / (b - a) if b > a else 0.0
                    if not m[5]:
                        f = 1.0 - f                     # shade by WORSE, whichever way it runs
                    cx = L + LBL + j * CW + k * CW / 2
                    cv.bar(cx + 0.4, y + 0.35, CW / 2 - 0.8, RH - 0.9, VAL,
                           alpha=0.07 + 0.55 * f, z=1)
                    cv.T(cx + CW / 4, y + RH / 2 - 0.3,
                         ("%.2f" % v) if v < 10 else ("%.1f" % v),
                         T_SMALL, INK, ha="center", va="center")
            y += RH
        cv.ln(L, y + GAP / 2, W - R, y + GAP / 2, "#eef1f3", 0.4, 1)
        y += GAP
    cv.T(L, y, "D = descriptive, C = causal, with n · darker = worse within that column, which "
         "for the three indices means a LOWER number", T_SMALL, MUT)
    y += 4.6
    for ln in cv.wrap("⚠ " + DUPNOTE + " On the descriptive side those two columns therefore "
                      "print the same number twice.", W - L - R, T_SMALL):
        cv.T(L, y, ln, T_SMALL, REP)
        y += line_h(T_SMALL)
    y += 2.0
    return cv, cv.foot(y, SRC7), "7C"


# =============================================================================================
# 7D — one ruler for all seven: signed distance from the task mean, oriented worse-to-the-right
# =============================================================================================
def cand_7D():
    RH, GH, GAP, LBL = 3.4, 4.4, 1.0, 33.0
    CW = (W - L - R - LBL) / 7.0
    # ⚠ the ceiling is DERIVED from the longest bar, not set at a round number.  At ±0.75 SD a
    # third of every column was empty, which made the figure look like it had been zoomed out to
    # flatter its own result; and an assertion on a hardcoded ceiling is what the S1–S4 rebuilds
    # learned to insist on.
    ZMAX = max(abs(zsign(ROW(nm, lv, t), m, t))
               for nm, lv in LEVELS for m in M7 for t in TASKS)
    MX = math.ceil(ZMAX * 20 + 0.5) / 20.0
    assert ZMAX <= MX, ("bars clip", ZMAX, MX)
    cv = Cv()
    y = cv.head(6.0, TITLE,
                "All seven measures on ONE ruler: each group's distance from its own task mean, "
                "in between-paper standard deviations. Every column is oriented so a bar to the "
                "right is worse quality — the three index columns are flipped to make that true, "
                "and marked ↔. Of the %d bars the longest is %.2f SD (%s, %s papers); none "
                "reaches half a standard deviation."
                % (len(LEVELS) * len(M7) * 2, ZMAX,
                   max(((abs(zsign(ROW(nm, lv, t), m, t)), m[3], t) for nm, lv in LEVELS
                        for m in M7 for t in TASKS))[1].lower(),
                   max(((abs(zsign(ROW(nm, lv, t), m, t)), m[3], t) for nm, lv in LEVELS
                        for m in M7 for t in TASKS))[2].lower()))
    for j, m in enumerate(M7):
        cx = L + LBL + j * CW
        for q, s in enumerate(SHORT7[m[3]].split("\n")):
            cv.T(cx + CW / 2, y + q * line_h(T_SMALL), s, T_SMALL, INK, "bold", ha="center")
        if not m[5]:
            cv.T(cx + CW / 2, y + 2 * line_h(T_SMALL), "↔ flipped", T_SMALL, REP, ha="center")
    y += 3 * line_h(T_SMALL) + 1.4
    cv.T(L, y - 9.0, "Group", T_HEAD, FAINT, "bold")
    cv.ln(L, y - 0.8, W - R, y - 0.8, INK, 0.7)
    ytop = y
    for nm, short, lvs in STRATS:
        cv.T(L, y, nm, T_BODY, INK, "bold")
        y += GH
        for lv in lvs:
            r = {t: ROW(nm, lv, t) for t in TASKS}
            cv.T(L + 1.5, y + RH / 2 - 0.3, lab(lv), T_SMALL, MUT, va="center")
            cv.T(L + LBL - 2.0, y + RH / 2 - 0.3,
                 "%d|%d" % (int(r["Descriptive"].N), int(r["Causal"].N)),
                 T_SMALL, FAINT, ha="right", va="center")
            for j, m in enumerate(M7):
                cx = L + LBL + j * CW + 1.6
                pw = CW - 3.2
                mid = cx + pw / 2
                for t in TASKS:
                    z = zsign(r[t], m, t)
                    cy = y + (0.45 if t == "Descriptive" else RH / 2 + 0.15)
                    bh = RH / 2 - 0.65
                    cv.bar(min(mid, mid + z / MX * pw / 2), cy,
                           abs(z / MX * pw / 2), bh, DTASK[t], z=3)
            y += RH
        cv.ln(L, y + GAP / 2, W - R, y + GAP / 2, "#eef1f3", 0.4, 1)
        y += GAP
    for j, m in enumerate(M7):
        mid = L + LBL + j * CW + 1.6 + (CW - 3.2) / 2
        cv.ln(mid, ytop, mid, y - GAP, INK, 0.55, 5)
    cv.T(L, y, "vertical rule in each column = that task's own mean · bar right = worse · "
         "upper bar descriptive, lower causal · scale ±%.2f SD, identical in all seven columns"
         % MX, T_SMALL, MUT)
    y += 4.0
    cv.taskkey(L, y)
    y += 5.5
    for ln in cv.wrap("⚠ " + DUPNOTE, W - L - R, T_SMALL):
        cv.T(L, y, ln, T_SMALL, REP)
        y += line_h(T_SMALL)
    y += 2.0
    return cv, cv.foot(y, SRC7), "7D"


# =============================================================================================
# 7E — the compact answer: seven measures, the whole spread of groups on each, named at the ends
# =============================================================================================
def cand_7E():
    cv = Cv()
    y = cv.head(6.0, TITLE,
                "The question in fourteen rows. For each of Figure 5's seven study-level measures "
                "and each task, the bar spans the %d group means from cleanest to worst, with "
                "the group at each end named; the tick is the task mean over all papers. The "
                "right-hand number is the spread in between-paper standard deviations — the "
                "single number that says whether the grouping matters at all." % NLEV)
    RH, BLK = 6.2, 5.0
    LBL, NW = 46.0, 17.0
    PW = W - L - R - LBL - NW - 4.0
    for t in TASKS:
        y = taskblock(cv, y, t, "spread of the %d group means · left = cleaner" % NLEV)
        for i, m in enumerate(M7):
            a, b = GR[(m[0], t)]
            pad = (b - a) * 0.22
            lo, hi = a - pad, b + pad
            sx = lambda v: L + LBL + (v - lo) / (hi - lo) * PW
            cy = y + RH / 2 - 1.2
            cv.T(L, cy, m[3], T_BODY, INK, va="center")
            cv.ln(sx(a), cy, sx(b), cy, DTASK[t], 1.6, 4)
            # every group as a tick on the bar, so the reader sees the 25, not just the ends
            for nm, lv in LEVELS:
                v = float(ROW(nm, lv, t)[m[0]])
                cv.ln(sx(v), cy - 1.5, sx(v), cy + 1.5, "#ffffff", 0.45, 5)
            mk = sx(PM[(m[0], t)])
            cv.ln(mk, cy - 2.4, mk, cy + 2.4, INK, 0.8, 6)
            cv.T(mk, cy - 2.7, "%.2f" % PM[(m[0], t)], T_SMALL, INK, "bold", ha="center",
                 va="bottom")
            best = min(LEVELS, key=lambda x: float(ROW(x[0], x[1], t)[m[0]]) * (1 if m[5] else -1))
            worst = max(LEVELS, key=lambda x: float(ROW(x[0], x[1], t)[m[0]]) * (1 if m[5] else -1))
            for who, xv, ha, dx in ((best, sx(float(ROW(best[0], best[1], t)[m[0]])), "right", -1.6),
                                    (worst, sx(float(ROW(worst[0], worst[1], t)[m[0]])), "left", 1.6)):
                cv.T(xv + dx, cy + 3.1, "%s %s  %.2f"
                     % (dict((a2, b2) for a2, b2, _c in STRATS)[who[0]], lab(who[1]),
                        float(ROW(who[0], who[1], t)[m[0]])), T_SMALL, MUT, ha=ha)
            cv.T(W - R, cy, "%.2f SD" % SEP[(m[0], t)], T_SMALL, INK, ha="right", va="center")
            # ⚠ each row carries a caption ABOVE its bar (the task mean) and two BELOW it (the
            # named ends), so the pitch has to clear both — at RH+2.4 a row's end label ran into
            # the next row's mean label.
            y += RH + 4.8
        y += BLK
    y -= BLK - 1.0
    for ln in cv.wrap("white ticks are the %d individual group means · black tick and number = "
                      "the mean over all that task's papers · left end best, right end worst "
                      "(for the three indices that is the higher number)" % NLEV,
                      W - L - R, T_SMALL):
        cv.T(L, y, ln, T_SMALL, MUT)
        y += line_h(T_SMALL)
    y += 3.0
    for ln in cv.wrap("⚠ " + DUPNOTE, W - L - R, T_SMALL):
        cv.T(L, y, ln, T_SMALL, REP)
        y += line_h(T_SMALL)
    y += 2.0
    return cv, cv.foot(y, SRC7), "7E"


# =============================================================================================
# 3A — the three indices on one true 0–1 scale
# =============================================================================================
def cand_3A():
    RH, GH, GAP, LBL = 3.6, 4.4, 1.0, 42.0
    # the "1.00" tick is CENTRED on the right edge of each block, so half of it sits outside —
    # 6 mm of slack, measured, not guessed
    PW = (W - L - R - LBL - 16.0) / 2.0
    cv = Cv()
    y = cv.head(6.0, TITLE,
                "The three indices are rates over each paper's own applicable items, so unlike "
                "the raw scores they genuinely share one 0–1 scale — and this is that scale, "
                "undistorted. All %d group means of an index fall inside a band of %.2f, %.2f "
                "and %.2f respectively. Candidate 3C magnifies these clumps; this one shows what "
                "is being magnified."
                % (2 * NLEV, *[su[m[0]].max() - su[m[0]].min() for m in M3]))
    ICOL = {"mean_validity": VAL, "mean_transparency": REP, "mean_ack": AC}
    for k, t in enumerate(TASKS):
        cv.T(L + LBL + k * (PW + 10.0), y, "%s · n=%d" % (t, TN[t]), T_HEAD, DTASK[t], "bold")
    y += 4.6
    for k, t in enumerate(TASKS):
        x0 = L + LBL + k * (PW + 10.0)
        for v in (0.0, 0.25, 0.5, 0.75, 1.0):
            cv.T(x0 + v * PW, y, "%.2f" % v, T_SMALL, FAINT, ha="center")
    y += 3.4
    ytop = y
    for nm, short, lvs in STRATS:
        cv.T(L, y, nm, T_BODY, INK, "bold")
        y += GH
        for lv in lvs:
            cv.T(L + 1.5, y + RH / 2 - 0.3, lab(lv), T_SMALL, MUT, va="center")
            for k, t in enumerate(TASKS):
                x0 = L + LBL + k * (PW + 10.0)
                r = ROW(nm, lv, t)
                cv.T(x0 - 2.0, y + RH / 2 - 0.3, "%d" % int(r.N), T_SMALL, FAINT, ha="right",
                     va="center")
                cv.bar(x0, y + RH / 2 - 0.35, PW, 0.12, "#e9edee", z=1)
                for m in M3:
                    cv.dot(x0 + float(r[m[0]]) * PW, y + RH / 2 - 0.3, 0.75, ICOL[m[0]],
                           "white", 6, 0.3)
            y += RH
        cv.ln(L, y + GAP / 2, W - R, y + GAP / 2, "#eef1f3", 0.4, 1)
        y += GAP
    for k, t in enumerate(TASKS):
        x0 = L + LBL + k * (PW + 10.0)
        for m in M3:
            mx = x0 + PM[(m[0], t)] * PW
            cv.ln(mx, ytop - 1.0, mx, y - GAP, ICOL[m[0]], 0.5, 2, (0, (1.4, 1.4)))
    kx = L
    for m in M3:
        cv.dot(kx + 1.0, y + 1.6, 0.75, ICOL[m[0]], "white", 6, 0.3)
        s = "%s (all papers %.2f D / %.2f C)" % (m[3], PM[(m[0], "Descriptive")],
                                                 PM[(m[0], "Causal")])
        cv.T(kx + 2.6, y + 1.6, s, T_SMALL, MUT, va="center")
        kx += 2.6 + cv.width(s, T_SMALL) + 6.0
    y += 5.0
    cv.T(L, y, "dotted rules are the all-paper means for each index · n at the left of each "
         "block", T_SMALL, MUT)
    y += 4.0
    return cv, cv.foot(y, SRC3), "3A"


# =============================================================================================
# 3B — three forests, each zoomed to its own range, with the noise each group carries
# =============================================================================================
def cand_3B():
    RH, GH, GAP, LBL = 3.2, 4.3, 1.0, 40.0
    CW = (W - L - R - LBL) / 3.0
    HW = (CW - 12.0) / 2.0
    cv = Cv()
    y = cv.head(6.0, TITLE,
                "The same three indices, each zoomed to the range its own group means occupy, "
                "with the ±95%% interval each group's sample size buys. Zooming is what makes "
                "the differences visible at all — and the intervals are what stop that being "
                "misleading: %d of the %d cross their own task mean."
                % (sum(1 for nm, lv in LEVELS for m in M3 for t in TASKS
                       if abs(float(ROW(nm, lv, t)[m[0]]) - PM[(m[0], t)])
                       <= 1.96 * SE(ROW(nm, lv, t), m[1],
                                    "n_ack_elig" if m[0] == "mean_ack" else "N")),
                   len(LEVELS) * 3 * 2))
    RNG = {}
    for m in M3:
        for t in TASKS:
            nk = "n_ack_elig" if m[0] == "mean_ack" else "N"
            g = su[su.task == t]
            lo = min(g[m[0]] - 1.96 * g[m[1]] / g[nk] ** 0.5)
            hi = max(g[m[0]] + 1.96 * g[m[1]] / g[nk] ** 0.5)
            pad = (hi - lo) * 0.06
            RNG[(m[0], t)] = (lo - pad, hi + pad)
    for j, m in enumerate(M3):
        cx = L + LBL + j * CW
        cv.T(cx, y, "%s  %s" % ("FIK"[j], m[3]), T_HEAD, INK, "bold")
        cv.T(cx, y + line_h(T_HEAD), m[4], T_SMALL, FAINT)
    y += 7.4
    for j, m in enumerate(M3):
        for k, t in enumerate(TASKS):
            x0 = L + LBL + j * CW + k * (HW + 6.0)
            a, b = RNG[(m[0], t)]
            cv.T(x0 + HW / 2, y, "%s  %.2f–%.2f" % (t[0], a, b), T_SMALL, DTASK[t], ha="center")
    y += 3.6
    ytop = y
    for nm, short, lvs in STRATS:
        cv.T(L, y, nm, T_BODY, INK, "bold")
        y += GH
        for lv in lvs:
            cv.T(L + 1.5, y + RH / 2 - 0.3, lab(lv), T_SMALL, MUT, va="center")
            r = {t: ROW(nm, lv, t) for t in TASKS}
            cv.T(L + LBL - 2.0, y + RH / 2 - 0.3,
                 "%d|%d" % (int(r["Descriptive"].N), int(r["Causal"].N)),
                 T_SMALL, FAINT, ha="right", va="center")
            for j, m in enumerate(M3):
                for k, t in enumerate(TASKS):
                    x0 = L + LBL + j * CW + k * (HW + 6.0)
                    a, b = RNG[(m[0], t)]
                    sx = lambda v: x0 + (v - a) / (b - a) * HW
                    nk = "n_ack_elig" if m[0] == "mean_ack" else "N"
                    v, e = float(r[t][m[0]]), 1.96 * SE(r[t], m[1], nk)
                    crosses = abs(v - PM[(m[0], t)]) <= e
                    cv.ln(max(sx(v - e), x0), y + RH / 2 - 0.3, min(sx(v + e), x0 + HW),
                          y + RH / 2 - 0.3, DTASK[t] if crosses else VAL, 0.55, 4)
                    cv.dot(sx(v), y + RH / 2 - 0.3, 0.62, DTASK[t] if crosses else VAL, z=6)
            y += RH
        cv.ln(L, y + GAP / 2, W - R, y + GAP / 2, "#eef1f3", 0.4, 1)
        y += GAP
    for j, m in enumerate(M3):
        for k, t in enumerate(TASKS):
            x0 = L + LBL + j * CW + k * (HW + 6.0)
            a, b = RNG[(m[0], t)]
            mx = x0 + (PM[(m[0], t)] - a) / (b - a) * HW
            cv.ln(mx, ytop, mx, y - GAP, INK, 0.6, 5, (0, (2.0, 1.4)))
    cv.T(L, y, "dashed rule = the task mean · red = interval clear of it · n as descriptive | "
         "causal; for the acknowledgement index n is the papers with something to acknowledge",
         T_SMALL, MUT)
    y += 4.0
    cv.taskkey(L, y)
    y += 5.5
    return cv, cv.foot(y, SRC3), "3B"


# =============================================================================================
# 3C — the honest zoom: full 0–1, and the magnified band beneath it
# =============================================================================================
def cand_3C():
    cv = Cv()
    y = cv.head(6.0, TITLE,
                "Each index twice: on its true 0–1 scale, and then magnified onto the sliver the "
                "group means actually occupy. The magnification factor is printed, because a "
                "reader shown only the lower strip would conclude the groups differ a great deal "
                "and a reader shown only the upper one that they are identical.")
    ICOL = {"mean_validity": VAL, "mean_transparency": REP, "mean_ack": AC}
    PW = W - L - R - 30.0
    for m in M3:
        cv.T(L, y, m[3], T_HEAD, INK, "bold")
        cv.T(L + cv.width(m[3], T_HEAD, "bold") + 3.0, y + 0.3, m[4], T_SMALL, FAINT)
        y += 4.6
        for t in TASKS:
            x0 = L + 26.0
            cv.T(L, y + 1.4, t.lower(), T_SMALL, DTASK[t], "bold", va="center")
            # --- the true scale ---
            cv.bar(x0, y + 0.9, PW, 1.0, "#eef1f2", z=1)
            for v in (0.0, 0.5, 1.0):
                cv.T(x0 + v * PW, y + 2.6, "%.1f" % v, T_SMALL, FAINT, ha="center")
            a, b = GR[(m[0], t)]
            cv.bar(x0 + a * PW, y + 0.4, max((b - a) * PW, 0.5), 2.0, ICOL[m[0]], z=3)
            for nm, lv in LEVELS:
                cv.dot(x0 + float(ROW(nm, lv, t)[m[0]]) * PW, y + 1.4, 0.5, ICOL[m[0]], z=4)
            # --- the magnified band ---
            pad = (b - a) * 0.10
            lo, hi = a - pad, b + pad
            zy = y + 6.4
            sx = lambda v: x0 + (v - lo) / (hi - lo) * PW
            cv.ln(x0 + a * PW, y + 2.6, x0, zy - 0.6, "#c8ced2", 0.4, 2)
            cv.ln(x0 + b * PW, y + 2.6, x0 + PW, zy - 0.6, "#c8ced2", 0.4, 2)
            cv.ln(x0, zy + 2.4, x0 + PW, zy + 2.4, RULE, 0.5)
            for nm, lv in LEVELS:
                r = ROW(nm, lv, t)
                cv.dot(sx(float(r[m[0]])), zy + 1.0, 0.62, ICOL[m[0]], "white", 6, 0.25)
            mk = sx(PM[(m[0], t)])
            cv.ln(mk, zy - 0.4, mk, zy + 2.4, INK, 0.7, 7, (0, (2.0, 1.4)))
            cv.T(mk, zy + 3.0, "all papers %.3f" % PM[(m[0], t)], T_SMALL, INK, ha="center")
            for v, ha, dx in ((lo, "left", 0.0), (hi, "right", 0.0)):
                cv.T(sx(v) + dx, zy + 3.0, "%.3f" % v, T_SMALL, FAINT, ha=ha)
            cv.T(W - R, zy + 1.0, "×%.0f" % (1.0 / (hi - lo)), T_SMALL, INK, "bold",
                 ha="right", va="center")
            # name the two ends
            best = max(LEVELS, key=lambda x: float(ROW(x[0], x[1], t)[m[0]]))
            worst = min(LEVELS, key=lambda x: float(ROW(x[0], x[1], t)[m[0]]))
            SH = dict((a2, b2) for a2, b2, _c in STRATS)
            cv.T(sx(float(ROW(worst[0], worst[1], t)[m[0]])) + 1.5, zy - 1.4,
                 "%s %s" % (SH[worst[0]], lab(worst[1])), T_SMALL, MUT)
            cv.T(sx(float(ROW(best[0], best[1], t)[m[0]])) - 1.5, zy - 1.4,
                 "%s %s" % (SH[best[0]], lab(best[1])), T_SMALL, MUT, ha="right")
            y = zy + 7.0
        y += 2.0
    cv.T(L, y, "upper strip: the true 0–1 index, with the band the %d group means occupy · "
         "lower strip: that band magnified by the factor at the right · higher is better on "
         "all three" % NLEV, T_SMALL, MUT)
    y += 4.5
    return cv, cv.foot(y, SRC3), "3C"


# =============================================================================================
# 3D — one glyph per group: does a group good on one index do well on the others?
# =============================================================================================
def cand_3D():
    cv = Cv()
    y = cv.head(6.0, TITLE,
                "Each group as a three-point profile across the indices, all normalised to the "
                "range their own group means occupy, and sorted by validity. If the three "
                "indices ranked groups alike the lines would run flat. Within causal papers they "
                "part company: validity and acknowledgement correlate %+.2f, but validity and "
                "transparency only %+.2f." % (COR["Causal"][1], COR["Causal"][0]))
    PW = (W - L - R - 14.0) / 2.0
    PH = 3.3 * NLEV + 6.0
    for k, t in enumerate(TASKS):
        x0 = L + k * (PW + 14.0)
        cv.T(x0, y, "%s · n=%d" % (t, TN[t]), T_HEAD, DTASK[t], "bold")
        cv.T(x0, y + line_h(T_HEAD),
             "V~T %+.2f · V~A %+.2f · T~A %+.2f across the %d groups"
             % (COR[t][0], COR[t][1], COR[t][2], NLEV), T_SMALL, FAINT)
        py = y + 8.0
        AX = [x0 + 30.0 + q * ((PW - 40.0) / 2.0) for q in range(3)]
        for q, m in enumerate(M3):
            cv.T(AX[q], py - 2.0, ["Validity", "Transparency", "Acknowl."][q], T_SMALL, INK,
                 "bold", ha="center")
            cv.ln(AX[q], py, AX[q], py + PH, RULE, 0.5)
            a, b = GR[(m[0], t)]
            cv.T(AX[q], py + PH + 1.6, "%.2f–%.2f" % (a, b), T_SMALL, FAINT, ha="center")
        rows = sorted(LEVELS, key=lambda x: -float(ROW(x[0], x[1], t)["mean_validity"]))
        SH = dict((a2, b2) for a2, b2, _c in STRATS)
        for i, (nm, lv) in enumerate(rows):
            r = ROW(nm, lv, t)
            # ⚠ 2 mm of padding inside each axis: without it the top group sits exactly on the
            # axis title and its label collides with it — and the top group is the one that
            # gets named.
            PAD = 2.0
            cy = lambda q: (py + PH - PAD - (float(r[M3[q][0]]) - GR[(M3[q][0], t)][0])
                            / (GR[(M3[q][0], t)][1] - GR[(M3[q][0], t)][0]) * (PH - 2 * PAD))
            hot = nm == "JCR 2022 quartile"
            col = VAL if hot else "#b9c4c9"
            for q in range(2):
                cv.ln(AX[q], cy(q), AX[q + 1], cy(q + 1), col, 0.85 if hot else 0.5,
                      5 if hot else 3)
            for q in range(3):
                cv.dot(AX[q], cy(q), 0.5, col, z=6 if hot else 4)
            if hot:
                cv.T(AX[0] - 1.8, cy(0), "%s %s" % (SH[nm], lab(lv)), T_SMALL, VAL,
                     ha="right", va="center")
        y_end = py + PH + 5.0
    y = y_end
    for ln in cv.wrap("each axis is scaled to the range of the %d group means on that index, so "
                      "the lines show RANK agreement and not the size of any difference · "
                      "journal quartile picked out in red" % NLEV, W - L - R, T_SMALL):
        cv.T(L, y, ln, T_SMALL, MUT)
        y += line_h(T_SMALL)
    y += 2.5
    return cv, cv.foot(y, SRC3), "3D"


# =============================================================================================
# 3E — do the three indices order the groups the same way? the three pairings, per task
# =============================================================================================
def cand_3E():
    cv = Cv()
    y = cv.head(6.0, TITLE,
                "The three indices against one another, one point per group, within task. This "
                "asks whether they are three measurements or one: if a group high on validity "
                "were reliably high on the others, the clouds would be lines. They are not — the "
                "strongest of the six panels is %+.2f."
                % max(COR[t][i] for t in TASKS for i in range(3)))
    PAIRS = [(0, 1), (0, 2), (1, 2)]
    PW = (W - L - R - 2 * 9.0 - 6.0) / 3.0    # 6 mm so the last panel's right tick stays on page
    PH = 46.0
    ICOL = {"mean_validity": VAL, "mean_transparency": REP, "mean_ack": AC}
    for t in TASKS:
        cv.T(L, y, "%s studies · %d groups" % (t, NLEV), T_HEAD, DTASK[t], "bold")
        y += 5.0
        for j, (ai, bi) in enumerate(PAIRS):
            ma, mb = M3[ai], M3[bi]
            x0 = L + j * (PW + 9.0) + 13.0
            pw = PW - 13.0
            xa, xb = GR[(ma[0], t)]
            ya, yb = GR[(mb[0], t)]
            px = lambda v: x0 + (v - xa) / (xb - xa) * pw
            py = lambda v: y + PH - (v - ya) / (yb - ya) * PH
            cv.ln(x0, y + PH, x0 + pw, y + PH, RULE, 0.5)
            cv.ln(x0, y, x0, y + PH, RULE, 0.5)
            for v in (xa, xb):
                cv.T(px(v), y + PH + 1.2, "%.2f" % v, T_SMALL, FAINT, ha="center")
            for v in (ya, yb):
                cv.T(x0 - 1.2, py(v), "%.2f" % v, T_SMALL, FAINT, ha="right", va="center")
            cv.T(x0 + pw / 2, y + PH + 4.4, ma[3], T_SMALL, ICOL[ma[0]], "bold", ha="center")
            cv.T(x0 - 11.0, y + PH / 2, mb[3].replace(" ", "\n"), T_SMALL, ICOL[mb[0]], "bold",
                 ha="center", va="center")
            cv.ln(px(PM[(ma[0], t)]), y, px(PM[(ma[0], t)]), y + PH, "#e4e9ea", 0.5, 1)
            cv.ln(x0, py(PM[(mb[0], t)]), x0 + pw, py(PM[(mb[0], t)]), "#e4e9ea", 0.5, 1)
            for nm, lv in LEVELS:
                r = ROW(nm, lv, t)
                hot = nm == "JCR 2022 quartile"
                cv.dot(px(float(r[ma[0]])), py(float(r[mb[0]])),
                       0.5 + 1.4 * math.sqrt(int(r.N) / 180.0), VAL if hot else DTASK[t],
                       "white", 6, 0.3)
            cv.T(x0 + pw, y + 1.0, "r %+.2f" % COR[t][j], T_SMALL, INK, "bold", ha="right")
        y += PH + 12.0
    y -= 4.0
    for ln in cv.wrap("point area scales with n · grey rules are the all-paper means · journal "
                      "quartile levels in red · r is Pearson's across the %d groups of that "
                      "task, never pooled over both" % NLEV, W - L - R, T_SMALL):
        cv.T(L, y, ln, T_SMALL, MUT)
        y += line_h(T_SMALL)
    y += 2.5
    return cv, cv.foot(y, SRC3), "3E"


CANDS = {"7A": cand_7A, "7B": cand_7B, "7C": cand_7C, "7D": cand_7D, "7E": cand_7E,
         "3A": cand_3A, "3B": cand_3B, "3C": cand_3C, "3D": cand_3D, "3E": cand_3E}

if __name__ == "__main__":
    want = [a.upper() for a in sys.argv[1:]] or sorted(CANDS)
    print("Figure 6 measure-set candidates -> %s/" % OUTDIR)
    bad, tall = {}, []
    for k in want:
        HH[0] = 460.0
        cv, used, code = CANDS[k]()
        plt.close(cv.fig)
        HH[0] = round(used + 2.5, 1)
        cv, used, code = CANDS[k]()
        c = cv.save(code, used)
        if c:
            bad[code] = c
        if cv.H > 250.0:
            tall.append("%s %.0f" % (code, cv.H))
    print("\n  seven-measure set: %s   three-index set: %s"
          % (" ".join(sorted(k for k in want if k[0] == "7")),
             " ".join(sorted(k for k in want if k[0] == "3"))))
    print("  ⚠ descriptive transparency score == domains-with-a-gap on %d/%d papers"
          % (DUP["Descriptive"], NP["Descriptive"]))
    if bad:
        print("  ⚠ text collisions in: %s" % ", ".join(sorted(bad)))
    if tall:
        print("  ⚠ over the 250 mm page ceiling: %s" % ", ".join(tall))

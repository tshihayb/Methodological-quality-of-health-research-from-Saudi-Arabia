# -*- coding: utf-8 -*-
"""Figure 6 re-cut — CANDIDATE DESIGNS (PNG only, for selection).

    python code/figures/08_26_2026_fig6_candidates.py [LETTER ...]

Figure 6 was built before Figure 5 was finalised and stratifies only two of the seven things
Figure 5 reports (mean n_val_flags, mean n_rep_gaps).  These candidates all stratify FIGURE 5's
analysis by the same ten variables Figure 6 already uses.  They vary the ENCODING, not the
arrangement, so the choice is about what the figure argues, not about how it is laid out.

⚠ Every candidate is drawn on `error_weighted` (graded severity), not `n_val_flags`.  The two
measurement-accounting items are scored and never pass, so measurement bias flags in ~100% of
papers and the flag COUNT can no longer separate anything — which is exactly why Figure 5 moved
to the graded quantity on 2026-08-22.  A stratified figure built on flag counts would repeat the
mistake Figure 5 already corrected.

⚠ Nothing is re-derived here.  code/scoring/07_30_2026_stratified_analysis.R computes every
number on Figure 5's own definitions and exports the four CSVs this script reads.  The stratifier
levels are read per paper from that export rather than rebuilt, so a candidate cannot drift from
the analysis it displays.

These are 180 mm wide and honour the 6.5 pt type floor, so a candidate reads on screen exactly as
it would in print; the chosen one gets the full print contract (PDF + TIFF + PNG, Arial embedded,
600 dpi, spill/clash/greyscale assertions) in the final script.

OUTPUT  outputs/figures/candidates/08_26_2026_fig6_<LETTER>.png
"""
import os, sys, math
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Circle
import pandas as pd

D = r"."
os.chdir(D)
OUTDIR = "outputs/figures/candidates"
os.makedirs(OUTDIR, exist_ok=True)
matplotlib.rcParams.update({"pdf.fonttype": 42, "ps.fonttype": 42, "font.family": "Arial"})

# ---- house constants, identical to Figure 5 ------------------------------------------------
PT2MM = 25.4 / 72.0
W, MIN_PT = 180.0, 6.5
INK, MUT, FAINT, AC = "#111417", "#4a5259", "#8b8f94", "#0f5c6b"
RULE, BAND = "#c8ced2", "#f2f5f6"
OK, REP, VAL, NA_ = "#0ca30c", "#e08a12", "#d03b3b", "#b4b2a9"
T_TITLE, T_HEAD, T_BODY, T_SMALL = 10.0, 7.5, 6.8, 6.5
LEAD = 1.30
line_h = lambda pt: pt * LEAD * PT2MM
L, R = 8.0, 2.0
TASKS = ["Descriptive", "Causal"]
DTASK = {"Descriptive": "#9ec3cc", "Causal": AC}

# ---- data ----------------------------------------------------------------------------------
# ⚠ "None" is the LABEL of the not-ranked JCR level, and pandas' default na_values turns it
# into NaN — which silently drops the single worst-scoring group on the page (causal 6.40, the
# top of the one variable that separates at all).  Keep the default NA set off and let only R's
# own "NA" be missing.
KA = dict(keep_default_na=False, na_values=["NA", ""])
su = pd.read_csv("data/scoring/07_30_2026_stratified_summary.csv", **KA)
dm = pd.read_csv("data/scoring/07_30_2026_stratified_domains.csv", **KA)
sp = pd.read_csv("data/scoring/07_30_2026_stratified_spread.csv", **KA)
pl = pd.read_csv("data/scoring/07_30_2026_stratified_paper_level.csv", **KA)
st = pd.read_csv("data/scoring/07_30_2026_scored_study.csv", **KA)
assert (su.level == "None").any(), "the not-ranked JCR level was read as missing"

# the 11th stratifier (JCR Q1-2 vs Q3-4) is computed and deliberately not drawn — it is a
# coarsening of the quartile, so drawing both would double-count the one variable that moves
DROP = "JCR Q1-2 vs Q3-4"
su = su[su.stratifier != DROP].copy()
dm = dm[dm.stratifier != DROP].copy()
sp = sp[sp.stratifier != DROP].copy()

STRATS = [("Saudi data used", "Saudi data", ["Yes", "No"]),
          ("Number of authors", "Team size", ["1-2", "3-10", "11+"]),
          ("% Saudi authors", "% Saudi authors", [">=50%", "<50%"]),
          ("Corresponding author", "Corr. author", ["Saudi", "Non-Saudi"]),
          ("First author", "First author", ["Saudi", "Non-Saudi"]),
          ("Last author", "Last author", ["Saudi", "Non-Saudi"]),
          ("Sector composition", "Sector", ["Academic-only", "Health-system"]),
          ("Single vs multi-sector", "Single/multi", ["Single-sector", "Multi-sector"]),
          ("JCR 2022 quartile", "JCR quartile", ["Q1", "Q2", "Q3", "Q4", "None"]),
          ("Funding", "Funding", ["Funded", "Declared none", "Not stated"])]
assert len(STRATS) == 10 and set(s[0] for s in STRATS) == set(su.stratifier.unique())
LVLAB = {">=50%": "\u226550%", "<50%": "<50%", "None": "Not ranked",
         "Academic-only": "Academic only", "Health-system": "Health-system",
         "Single-sector": "Single-sector", "Multi-sector": "Multi-sector",
         "1-2": "1\u20132", "3-10": "3\u201310", "11+": "11+"}
lab = lambda v: LVLAB.get(v, v)


def prose(nm):
    """A stratifier's name set mid-sentence. Lower-cases the first word unless it is an
    acronym — "jcr 2022 quartile" is not a thing."""
    w = nm.split(" ")[0]
    return nm if (w.isupper() and len(w) > 1) else nm[0].lower() + nm[1:]

# task-level reference values, straight off the scored studies (not off the group means)
TMEAN = {t: float(st.loc[st.Study_Type == t, "error_weighted"].mean()) for t in TASKS}
TSD = {t: float(st.loc[st.Study_Type == t, "error_weighted"].std()) for t in TASKS}
TN = {t: int((st.Study_Type == t).sum()) for t in TASKS}
assert TN["Causal"] == 229 and TN["Descriptive"] == 81, TN
# the group means must bracket the task mean — a weighted identity, so assert it
for t in TASKS:
    for nm, _s, _lv in STRATS:
        g = su[(su.stratifier == nm) & (su.task == t)]
        w = float((g.mean_err_w * g.N).sum() / g.N.sum())
        assert abs(w - TMEAN[t]) < 1e-6, (nm, t, w, TMEAN[t])

ROW = lambda nm, lv, t: su[(su.stratifier == nm) & (su.level == lv) & (su.task == t)].iloc[0]
SE = lambda r: float(r.sd_err_w) / math.sqrt(int(r.N))          # for the noise bands


def strat_order(task="Causal", measure="mean_err_w"):
    """Stratifiers ranked by how much they separate, most first."""
    s = sp[(sp.task == task) & (sp.measure == measure)].set_index("stratifier")
    return sorted(STRATS, key=lambda x: -s.loc[x[0], "spread"])


def dsep(nm, task, measure="mean_err_w"):
    """Separation in between-paper SD units — the yardstick that makes measures comparable."""
    s = sp[(sp.stratifier == nm) & (sp.task == task) & (sp.measure == measure)]
    if not len(s):
        return float("nan")
    sd = {"mean_err_w": TSD[task],
          "mean_validity": float(st.loc[st.Study_Type == task, "validity"].std()),
          "mean_transparency": float(st.loc[st.Study_Type == task, "transparency"].std()),
          "mean_dom_flag": float(st.loc[st.Study_Type == task, "domains_flagged"].std()),
          "mean_rep_gap": float(st.loc[st.Study_Type == task, "n_rep_gaps"].std()),
          "mean_ack": float(st.loc[st.Study_Type == task, "acknowledgement"].dropna().std()),
          "pct_ge3": 100 * float((st.loc[st.Study_Type == task, "domains_flagged"] >= 3).std()),
          }.get(measure)
    return float(s.iloc[0].spread) / sd if sd else float("nan")


# ---- drawing context -----------------------------------------------------------------------
# ⚠ NO CANDIDATE GUESSES ITS OWN HEIGHT.  Each is drawn twice: once on a deliberately over-tall
# canvas purely to measure where its content ends, then again at that measured height.  Half of
# these layouts have a block that can grow — a wrapped sub-line, a legend that reflows, a
# stratifier with five levels instead of two — and a reserved round number is how the S1–S4
# rebuilds kept ending up either clipped or padded.  HH[0] is the height Cv() picks up.
HH = [400.0]


class Cv:
    """A 180 mm-wide canvas in millimetres, y increasing downward, as Figure 5 uses."""

    def __init__(self, h=None):
        h = HH[0] if h is None else h
        self.H = h
        self.fig = plt.figure(figsize=(W / 25.4, h / 25.4))
        self.ax = self.fig.add_axes([0, 0, 1, 1])
        self.ax.set_xlim(0, W); self.ax.set_ylim(h, 0); self.ax.axis("off")
        self.ax.add_patch(Rectangle((0, 0), W, h, fc="white", ec="none", zorder=0))
        self.sizes = []

    def T(self, x, y, s, pt=T_BODY, c=INK, weight="normal", ha="left", va="top", z=4, rot=0):
        self.sizes.append(pt)
        return self.ax.text(x, y, s, fontsize=pt, color=c, fontweight=weight, ha=ha, va=va,
                            zorder=z, rotation=rot, rotation_mode="anchor")

    def bar(self, x, y, w, h, fc, ec=None, lw=0, z=3, alpha=1.0):
        self.ax.add_patch(Rectangle((x, y), w, h, fc=fc, ec=ec or "none", lw=lw, zorder=z,
                                    alpha=alpha))

    def ln(self, x0, y0, x1, y1, c=RULE, lw=0.5, z=2, ls="-"):
        self.ax.add_line(plt.Line2D([x0, x1], [y0, y1], color=c, lw=lw, zorder=z, linestyle=ls))

    def dot(self, x, y, r, fc, ec="none", z=6, lw=0.0):
        self.ax.add_patch(Circle((x, y), r, fc=fc, ec=ec, lw=lw, zorder=z))

    def width(self, s, pt, weight="normal"):
        t = self.ax.text(0, 0, s, fontsize=pt, fontweight=weight, zorder=0)
        w = t.get_window_extent(self.fig.canvas.get_renderer()).width / self.fig.dpi * 25.4
        t.remove()
        return w

    def wrap(self, s, maxw, pt):
        out, cur = [], ""
        for wd in s.split(" "):
            t = wd if not cur else cur + " " + wd
            if self.width(t, pt) > maxw and cur:
                out.append(cur); cur = wd
            else:
                cur = t
        out.append(cur)
        return out

    def head(self, y, title, sub, wrapw=None):
        """Title + wrapped sub-line. Returns the y AFTER the block — never an offset guess."""
        self.T(L, y, title, T_TITLE, INK, "bold")
        y += line_h(T_TITLE) + 0.6
        for ln in self.wrap(sub, wrapw or (W - L - R), T_BODY):
            self.T(L, y, ln, T_BODY, MUT)
            y += line_h(T_BODY)
        return y + 2.4

    def foot(self, y, txt):
        self.ln(L, y, W - R, y, RULE, 0.5)
        y += 2.0
        for ln in self.wrap(txt, W - L - R, T_SMALL):
            self.T(L, y, ln, T_SMALL, FAINT)
            y += line_h(T_SMALL)
        return y + 1.5

    def taskkey(self, x, y, extra=None):
        for t in TASKS:
            self.bar(x, y, 4.0, 1.5, DTASK[t])
            self.T(x + 5.0, y + 0.75, t.lower(), T_SMALL, MUT, va="center")
            x += 5.0 + self.width(t.lower(), T_SMALL) + 6.0
        if extra:
            self.T(x, y + 0.75, extra, T_SMALL, FAINT, va="center")
        return x

    def save(self, letter, used):
        f = "%s/08_26_2026_fig6_%s.png" % (OUTDIR, letter)
        self.fig.canvas.draw()
        rend = self.fig.canvas.get_renderer()
        mm = lambda px: px / self.fig.dpi * 25.4
        assert min(self.sizes) >= MIN_PT - 1e-9, ("type floor", letter, min(self.sizes))
        assert used <= self.H + 0.5, ("content overflowed the canvas", letter, used, self.H)
        boxes, spill = [], []
        for t in self.ax.texts:
            b = t.get_window_extent(rend)
            x0, x1, y0, y1 = mm(b.x0), mm(b.x1), mm(b.y0), mm(b.y1)
            if x0 < -0.2 or x1 > W + 0.2 or y0 < -0.2 or y1 > self.H + 0.2:
                spill.append((round(x0, 1), round(x1, 1), t.get_text()[:36]))
            boxes.append((y0, y1, x0, x1, t.get_text()))
        assert not spill, ("text left the canvas", letter, spill[:6])
        clash = [(a[4][:20], b[4][:20]) for i, a in enumerate(boxes) for b in boxes[i + 1:]
                 if a[2] < b[3] - 0.25 and a[3] > b[2] + 0.25
                 and a[0] < b[1] - 0.25 and a[1] > b[0] + 0.25]
        self.fig.savefig(f, dpi=300, facecolor="white")
        plt.close(self.fig)
        print("  %s  %5.0f x %5.0f mm  filled %5.1f  %s" %
              (letter, W, self.H, used, "CLASH: %s" % (clash[:3],) if clash else "clean"))
        return clash


def declutter(ys, minsep):
    """Nudge a set of label positions apart to `minsep`, keeping their order and their centre
    of mass. Returns the adjusted positions in the ORIGINAL order."""
    idx = sorted(range(len(ys)), key=lambda i: ys[i])
    out = list(ys)
    for k in range(1, len(idx)):
        a, b = idx[k - 1], idx[k]
        if out[b] - out[a] < minsep:
            out[b] = out[a] + minsep
    shift = (sum(ys) - sum(out)) / len(ys)          # re-centre, so the block does not drift down
    return [v + shift for v in out]


def _kde(vals, xs, h):
    n, c = len(vals), 1.0 / math.sqrt(2 * math.pi)
    return [c * sum(math.exp(-0.5 * ((x - v) / h) ** 2) for v in vals) / (n * h) for x in xs]


def _silverman(v):
    n = len(v); m = sum(v) / n
    sd = math.sqrt(sum((x - m) ** 2 for x in v) / (n - 1))
    sv = sorted(v); qq = lambda p: sv[min(int(p * (n - 1)), n - 1)]
    iqr = qq(0.75) - qq(0.25)
    return 0.9 * (min(sd, iqr / 1.34) if iqr > 0 else sd) * n ** (-0.2)


# =============================================================================================
# ⚠ EVERY QUANTITATIVE CLAIM IN A CAPTION IS COMPUTED HERE, NOT WRITTEN OUT.
# The first draft of these captions asserted things I had not checked, and six of them were
# wrong: "the spread is under one graded flaw" (it is 1.10), "45 of the 50 intervals cross the
# task mean, the five that do not are journal-quartile and team-size" (47 do, and all three
# exceptions are journal-quartile), "the task moves severity by about three flaws" (2.74),
# "seven of the ten move it by less than half an SD" (eight), and a transparency claim that was
# backwards.  A caption is a finding; it gets derived and asserted like one.
# =============================================================================================
_M = sp[sp.measure == "mean_err_w"]
F_MAXSPREAD = float(_M.spread.max())
F_MAXSPREAD_WHO = (_M.loc[_M.spread.idxmax(), "stratifier"], _M.loc[_M.spread.idxmax(), "task"])
F_MAXSEP_SD = max(dsep(nm, t) for nm, _s, _l in STRATS for t in TASKS)

# intervals whose 95% CI excludes their own task mean
_CLEAR = [(r.stratifier, r.level, r.task) for r in su.itertuples()
          if not (r.mean_err_w - 1.96 * r.sd_err_w / math.sqrt(r.N) <= TMEAN[r.task]
                  <= r.mean_err_w + 1.96 * r.sd_err_w / math.sqrt(r.N))]
F_NLEVELS = len(su)
F_NCLEAR = len(_CLEAR)
F_CLEAR_VARS = sorted(set(c[0] for c in _CLEAR))

# how tight the whole set of group means is around its task mean, in SD units
_within = lambda b: sum(abs(r.mean_err_w - TMEAN[r.task]) <= b * TSD[r.task]
                        for r in su.itertuples())
F_W025, F_W050 = _within(0.25), _within(0.50)

# the separation matrix, over every measure candidate G draws
G_MEAS = ["mean_err_w", "mean_validity", "mean_dom_flag", "pct_ge3", "mean_rep_gap",
          "mean_transparency", "mean_ack"]
_CELLS = sorted(((dsep(nm, t, m), nm, t, m) for nm, _s, _l in STRATS for t in TASKS
                 for m in G_MEAS), reverse=True)
F_CELLMAX, F_CELLMAX_WHO = _CELLS[0][0], (_CELLS[0][1], _CELLS[0][2])
F_NCELLS, F_NCELL_HALF = len(_CELLS), sum(1 for c in _CELLS if c[0] >= 0.5)

# which variables clear half an SD on graded severity, on either task
F_BIG = [nm for nm, _s, _l in STRATS if max(dsep(nm, t) for t in TASKS) >= 0.5]
F_SMALL = [nm for nm, _s, _l in STRATS if nm not in F_BIG]
F_TASKGAP = TMEAN["Causal"] - TMEAN["Descriptive"]

# ⚠ group MEANS against the pooled MEDIAN is not a fair comparison — both indices are
# left-skewed, so a group's mean sits below the median even for a typical group.  Candidate I
# uses the pooled MEANS as its crosshairs for exactly this reason; the medians stay where they
# belong, on the paper-level cross-classification underneath.
MT_MED, MV_MED = float(st.transparency.median()), float(st.validity.median())
MT_MEAN, MV_MEAN = float(st.transparency.mean()), float(st.validity.mean())
F_T_ABOVE_MED = int((su.mean_transparency >= MT_MED).sum())
assert F_T_ABOVE_MED < F_NLEVELS / 2, "the median-crosshair caveat no longer applies"
assert F_NCLEAR == 3 and F_CLEAR_VARS == ["JCR 2022 quartile"], (F_NCLEAR, F_CLEAR_VARS)
assert F_MAXSPREAD > 1.0 and F_MAXSEP_SD < 0.75, (F_MAXSPREAD, F_MAXSEP_SD)
assert len(F_BIG) == 2, F_BIG

TITLE = "Figure 6. Does methodological quality differ by group?"
NOTE_N = "n beside every level; the smallest is 11 (descriptive, 1\u20132 authors)."
SRC = ("310 scored studies (229 causal, 81 descriptive; predictive studies carry no bias items). "
       "Severity is the graded validity error score of Figure 5 \u2014 items scored "
       "0/0.25/0.5/0.75/1, summed per paper \u2014 not the flag count. Descriptive and causal "
       "papers carry different numbers of items and are never compared to each other. All "
       "associational and unadjusted; group membership is not randomised. "
       "code/scoring/07_30_2026_stratified_analysis.R.")


# =============================================================================================
# A — Figure 5's shared spine, re-indexed from domain to stratifier level
# =============================================================================================
def cand_A():
    # 50 rows: the row pitch is what decides whether this design fits the page at all.
    # At 3.1/4.6 it came to 262 mm against the ~250 mm ceiling S9 and Figure 5 establish.
    RH, GH, GAP = 2.75, 4.0, 1.0
    nlev = sum(len(s[2]) for s in STRATS)
    LBL = 30.0
    COLW = (W - L - R - LBL - 2 * 3.5) / 3.0
    BARW_A, BARW_B, BARW_C = COLW - 17.0, COLW - 10.0, COLW - 15.0
    cv = Cv()
    y = cv.head(6.0, TITLE,
                "Figure 5's three verdict panels, re-indexed from domain to group: each row is one "
                "level of one grouping variable, and the three columns are the same three views of "
                "its papers. Reading a column top to bottom asks whether any group separates. Only "
                "one does: across all %d groups the widest gap column B can show is %.2f graded "
                "flaws, and it belongs to %s."
                % (F_NLEVELS, F_MAXSPREAD, prose(F_MAXSPREAD_WHO[0])))
    CX = [L + LBL + i * (COLW + 3.5) for i in range(3)]
    for i, (h1, h2) in enumerate([("A  Four-state verdict", "% of judgeable study \u00d7 domain cells"),
                                  ("B  Graded severity", "mean validity error score per paper"),
                                  ("C  \u201cNot reported\u201d sensitivity", "flaw \u2192 worst case")]):
        cv.T(CX[i], y, h1, T_HEAD, INK, "bold")
        cv.T(CX[i], y + line_h(T_HEAD), h2, T_SMALL, FAINT)
    cv.T(L, y, "Group", T_HEAD, FAINT, "bold")
    cv.ln(L, y + 7.5 - 1.2, W - R, y + 7.5 - 1.2, INK, 0.7)
    y += 7.5
    SCALE = max(su.mean_err_w) * 1.06
    for nm, short, lvs in STRATS:
        cv.T(L, y, nm, T_BODY, INK, "bold")
        cv.T(L + cv.width(nm, T_BODY, "bold") + 2.0, y + 0.25,
             "sep. %.2f SD" % dsep(nm, "Causal"), T_SMALL, FAINT)
        y += GH
        for lv in lvs:
            cv.T(L + 1.5, y + RH - 0.4, lab(lv), T_SMALL, MUT, va="center")
            for t in TASKS:
                r = ROW(nm, lv, t)
                cy, bh = y + 0.5, RH - 1.3
                cv.T(L + LBL - 1.5, y + 0.05, "%s %d" % (t[0], int(r.N)), T_SMALL, FAINT, ha="right")
                # A: four-state, on judgeable cells
                x = CX[0]
                for v, col in ((r.pct_ok, OK), (r.pct_rep, REP), (r.pct_val, VAL)):
                    seg = BARW_A * v / 100.0
                    cv.bar(x, cy, seg, bh, col); x += seg
                cv.T(CX[0] + BARW_A + 1.5, y, "%.0f%%" % r.pct_val, T_SMALL, VAL, "bold")
                # B: graded severity
                cv.bar(CX[1], cy, BARW_B * r.mean_err_w / SCALE, bh, DTASK[t])
                cv.T(CX[1] + BARW_B + 1.5, y, "%.2f" % r.mean_err_w, T_SMALL, INK)
                # C: the sensitivity band
                cv.bar(CX[2], cy, BARW_C * r.pct_val / 100.0, bh, VAL)
                cv.bar(CX[2] + BARW_C * r.pct_val / 100.0, cy,
                       BARW_C * (r.pct_worst - r.pct_val) / 100.0, bh, REP)
                cv.T(CX[2] + BARW_C + 1.5, y, "%.0f\u2192%.0f" % (r.pct_val, r.pct_worst), T_SMALL, INK)
                y += RH
        cv.ln(L, y + GAP / 2, W - R, y + GAP / 2, "#eef1f3", 0.4, 1)
        y += GAP
    kx = L
    for t, c in (("no issue", OK), ("reporting gap", REP), ("validity flaw", VAL)):
        cv.bar(kx, y + 0.6, 2.6, 2.6, c)
        cv.T(kx + 3.4, y + 1.9, t, T_SMALL, MUT, va="center")
        kx += 3.4 + cv.width(t, T_SMALL) + 5.0
    kx = cv.taskkey(kx + 4.0, y + 1.1, "\u2014 column B")
    y += 6.0
    return cv, cv.foot(y, "D = descriptive, C = causal. " + SRC), "A"


# =============================================================================================
# B — forest plot: every level against its task mean, with the noise it carries
# =============================================================================================
def cand_B():
    RH, GH, GAP = 3.0, 4.4, 1.2
    nlev = sum(len(s[2]) for s in STRATS)
    cv = Cv()
    y = cv.head(6.0, TITLE,
                "Every group's mean graded severity, with the \u00b195%% interval its own sample "
                "size buys. The vertical rule is the task mean over all papers. A group that "
                "separates would sit clear of that rule: %d of the %d intervals cross it, and "
                "all %d that do not belong to the same variable \u2014 %s."
                % (F_NLEVELS - F_NCLEAR, F_NLEVELS, F_NCLEAR, prose(F_CLEAR_VARS[0])))
    LBL = 46.0
    # 14 mm between the two blocks, 12 mm at the end of each for its n column — measured, not
    # guessed: at PW = 55 the right-hand n labels ran off the page edge.
    PW = (W - L - R - LBL - 26.0) / 2.0
    for k, t in enumerate(TASKS):
        x0 = L + LBL + k * (PW + 14.0)
        cv.T(x0, y, "%s  n=%d" % (t, TN[t]), T_HEAD, DTASK[t], "bold")
        cv.T(x0, y + line_h(T_HEAD), "graded severity, mean \u00b195%% CI \u00b7 task mean %.2f"
             % TMEAN[t], T_SMALL, FAINT)
    y += 7.6
    # one x-range per task, wide enough for every interval drawn
    RNG = {}
    for t in TASKS:
        g = su[su.task == t]
        lo = min(g.mean_err_w - 1.96 * g.sd_err_w / g.N ** 0.5)
        hi = max(g.mean_err_w + 1.96 * g.sd_err_w / g.N ** 0.5)
        pad = (hi - lo) * 0.10
        RNG[t] = (lo - pad, hi + pad)
    # ⚠ the tick strip gets its OWN band under the column headers.  Set at y - 1.0 it sat on the
    # sub-line above it, which the collision check caught and the eye would not have.
    y += 1.0
    for k, t in enumerate(TASKS):
        x0 = L + LBL + k * (PW + 14.0)
        a, b = RNG[t]
        for v in [x for x in (2, 3, 4, 5, 6, 7, 8) if a <= x <= b]:
            xv = x0 + (v - a) / (b - a) * PW
            cv.T(xv, y, str(v), T_SMALL, FAINT, ha="center")
            cv.ln(xv, y + 3.0, xv, cv.H - 22.0, "#f0f3f4", 0.4, 1)
    y += 3.0
    yy = y + 1.0
    for nm, short, lvs in STRATS:
        cv.T(L, yy, nm, T_BODY, INK, "bold")
        yy += GH
        for lv in lvs:
            cv.T(L + 2.0, yy + RH / 2 - 0.2, lab(lv), T_SMALL, MUT, va="center")
            for k, t in enumerate(TASKS):
                r = ROW(nm, lv, t); a, b = RNG[t]
                x0 = L + LBL + k * (PW + 14.0)
                sx = lambda v: x0 + (v - a) / (b - a) * PW
                lo, hi = r.mean_err_w - 1.96 * SE(r), r.mean_err_w + 1.96 * SE(r)
                cy = yy + RH / 2 - 0.2
                crosses = lo <= TMEAN[t] <= hi
                cv.ln(sx(lo), cy, sx(hi), cy, DTASK[t] if crosses else VAL, 0.7, 4)
                cv.dot(sx(r.mean_err_w), cy, 0.75, DTASK[t] if crosses else VAL, z=6)
                cv.T(x0 + PW + 1.5, yy + RH / 2 - 0.2, "%d" % int(r.N), T_SMALL, FAINT, va="center")
            yy += RH
        cv.ln(L, yy + GAP / 2, W - R, yy + GAP / 2, "#eef1f3", 0.4, 1)
        yy += GAP
    for k, t in enumerate(TASKS):
        x0 = L + LBL + k * (PW + 14.0); a, b = RNG[t]
        cv.ln(x0 + (TMEAN[t] - a) / (b - a) * PW, y, x0 + (TMEAN[t] - a) / (b - a) * PW,
              yy - GAP, INK, 0.8, 5, (0, (2.4, 1.6)))
    cv.T(L, yy, "dashed rule = task mean \u00b7 red = interval clear of it \u00b7 n at the right",
         T_SMALL, MUT)
    yy += 5.0
    return cv, cv.foot(yy, SRC), "B"


# =============================================================================================
# C — difference from the task mean, centred on zero
# =============================================================================================
def cand_C():
    RH, GH, GAP = 3.0, 4.4, 1.2
    nlev = sum(len(s[2]) for s in STRATS)
    cv = Cv()
    y = cv.head(6.0, TITLE,
                "The same %d groups as differences from their own task's mean, so the two tasks "
                "share one zero. The grey band is \u00b10.25 between-paper standard deviations: %d of "
                "the %d bars end inside it, and all %d end within half an SD. The groups differ "
                "from each other far less than the papers inside any one group do."
                % (F_NLEVELS // 2, F_W025, F_NLEVELS, F_W050))
    LBL = 46.0
    PW = W - L - R - LBL - 12.0
    MX = 0.85
    cx = L + LBL + PW / 2.0
    sx = lambda d: cx + d / MX * (PW / 2.0)
    cv.T(L + LBL, y, "worse than the task mean \u2192", T_SMALL, FAINT)
    cv.T(L + LBL + PW, y, "\u2190 better", T_SMALL, FAINT, ha="right")
    y += 6.5                          # the tick strip needs a full line of its own, not 4 mm
    for v in (-0.75, -0.5, -0.25, 0, 0.25, 0.5, 0.75):
        cv.T(sx(-v), y - 0.4, ("%+.2f" % v if v else "0"), T_SMALL, FAINT, ha="center", va="bottom")
    ytop = y + 0.6
    for nm, short, lvs in STRATS:
        cv.T(L, y, nm, T_BODY, INK, "bold")
        cv.T(L + cv.width(nm, T_BODY, "bold") + 2.0, y + 0.25,
             "\u0394 %.2f" % sp[(sp.stratifier == nm) & (sp.task == "Causal")
                               & (sp.measure == "mean_err_w")].iloc[0].spread, T_SMALL, FAINT)
        y += GH
        for lv in lvs:
            cv.T(L + 2.0, y + RH / 2 - 0.2, lab(lv), T_SMALL, MUT, va="center")
            # ⚠ ONE n per row, not one per task bar.  Two 6.5 pt labels 1.3 mm apart inside a
            # 3 mm row overlap by a millimetre; the two bars are already told apart by colour.
            cv.T(L + LBL - 1.5, y + RH / 2 - 0.2,
                 "%d | %d" % (int(ROW(nm, lv, "Descriptive").N), int(ROW(nm, lv, "Causal").N)),
                 T_SMALL, FAINT, ha="right", va="center")
            for t in TASKS:
                r = ROW(nm, lv, t)
                d = float(r.mean_err_w) - TMEAN[t]
                cy = y + (0.35 if t == "Descriptive" else RH / 2 + 0.15)
                bh = RH / 2 - 0.5
                cv.bar(min(sx(0), sx(-d)), cy, abs(sx(-d) - sx(0)), bh, DTASK[t])
            y += RH
        cv.ln(L, y + GAP / 2, W - R, y + GAP / 2, "#eef1f3", 0.4, 1)
        y += GAP
    # the SD band and the zero rule, drawn behind everything, spanning the plotted rows
    for t in TASKS:
        pass
    cv.bar(sx(0.25 * TSD["Causal"] / TSD["Causal"] * 0.25 / 0.25 * -0.25), ytop, 0, 0, "none")
    band = 0.25
    cv.bar(sx(band), ytop, sx(-band) - sx(band), y - GAP - ytop, "#f4f6f7", z=1)
    cv.ln(sx(0), ytop, sx(0), y - GAP, INK, 0.8, 5)
    cv.T(L, y, "grey band = \u00b10.25 SD of the paper-to-paper spread (causal SD %.2f, "
         "descriptive %.2f) \u00b7 \u0394 = causal spread, worst level minus best"
         % (TSD["Causal"], TSD["Descriptive"]), T_SMALL, MUT)
    y += 4.0
    cv.taskkey(L, y)
    y += 5.0
    return cv, cv.foot(y, SRC), "C"


# =============================================================================================
# D — ranked lollipop: how much does each variable separate at all?
# =============================================================================================
def cand_D():
    RH, GAP = 8.2, 2.0
    cv = Cv()
    y = cv.head(6.0, TITLE,
                "The ten grouping variables ranked by how far apart they pull their own groups. "
                "Each rule runs from that variable's cleanest group to its worst; the number is "
                "the gap in graded severity, and in brackets the same gap in between-paper "
                "standard deviations. The largest is %.2f SD; nothing reaches three-quarters."
                % F_MAXSEP_SD)
    LBL, NW = 40.0, 30.0
    PW = W - L - R - LBL - NW - 6.0
    order = strat_order("Causal")
    # one shared scale per task; drawn as two stacked blocks so the ranks are legible
    for t in TASKS:
        g = su[su.task == t]
        lo, hi = float(g.mean_err_w.min()), float(g.mean_err_w.max())
        pad = (hi - lo) * 0.08
        a, b = lo - pad, hi + pad
        cv.T(L, y, "%s studies" % t, T_HEAD, DTASK[t], "bold")
        cv.T(L + cv.width("%s studies" % t, T_HEAD, "bold") + 3.0, y + 0.3,
             "task mean %.2f \u00b7 paper-to-paper SD %.2f" % (TMEAN[t], TSD[t]), T_SMALL, FAINT)
        y += 7.4          # the tick row is set ABOVE this y; a finer step needs a clear line
        sx = lambda v: L + LBL + (v - a) / (b - a) * PW
        # ⚠ the tick STEP follows the range.  At whole numbers the descriptive block spans
        # 2.7–3.5 and gets exactly one gridline, so the axis carries no scale at all.
        step = next(s for s in (1.0, 0.5, 0.25, 0.1) if (b - a) / s >= 3)
        tv = math.ceil(a / step) * step
        while tv <= b + 1e-9:
            cv.ln(sx(tv), y - 1.0, sx(tv), y + len(order) * RH - 2.0, "#f0f3f4", 0.4, 1)
            cv.T(sx(tv), y - 1.4, ("%g" % round(tv, 2)), T_SMALL, FAINT, ha="center", va="bottom")
            tv += step
        cv.ln(sx(TMEAN[t]), y - 1.0, sx(TMEAN[t]), y + len(order) * RH - 2.0, INK, 0.7, 5,
              (0, (2.4, 1.6)))
        ordt = strat_order(t)
        for i, (nm, short, lvs) in enumerate(ordt):
            yy = y + i * RH
            cv.T(L, yy + 1.4, short, T_BODY, INK, "bold", va="center")
            rows = [ROW(nm, lv, t) for lv in lvs]
            vals = [(float(r.mean_err_w), lv, int(r.N)) for r, lv in zip(rows, lvs)]
            vals.sort()
            cv.ln(sx(vals[0][0]), yy + 1.4, sx(vals[-1][0]), yy + 1.4, DTASK[t], 1.4, 4)
            for v, lv, n in vals:
                cv.dot(sx(v), yy + 1.4, 0.85, DTASK[t], "white", 7, 0.4)
            # ⚠ Name the two ends, but MEASURE before centring them.  The whole point of this
            # design is that some variables barely separate — and for those the two end labels
            # are centred a millimetre apart and overlap ("Last author": 3.15 vs 3.19).  Where
            # they would touch, the labels fall outward instead, which also reads as "these two
            # ends are the same place".
            s_lo = "%s %d" % (lab(vals[0][1]), vals[0][2])
            s_hi = "%s %d" % (lab(vals[-1][1]), vals[-1][2])
            xlo, xhi = sx(vals[0][0]), sx(vals[-1][0])
            room = xhi - xlo - (cv.width(s_lo, T_SMALL) + cv.width(s_hi, T_SMALL)) / 2.0
            if room > 1.5:
                cv.T(xlo, yy + 3.0, s_lo, T_SMALL, MUT, ha="center")
                cv.T(xhi, yy + 3.0, s_hi, T_SMALL, MUT, ha="center")
            else:
                cv.T(xlo - 1.2, yy + 3.0, s_lo, T_SMALL, MUT, ha="right")
                cv.T(xhi + 1.2, yy + 3.0, s_hi, T_SMALL, MUT, ha="left")
            cv.T(L + LBL + PW + 3.0, yy + 1.4, "%.2f  [%.2f SD]"
                 % (vals[-1][0] - vals[0][0], dsep(nm, t)), T_SMALL, INK, va="center")
        y += len(order) * RH + GAP
    cv.T(L, y, "dashed rule = task mean \u00b7 dots are group means, labelled with n \u00b7 "
         "bracketed value is the gap in between-paper SD units", T_SMALL, MUT)
    y += 4.5
    return cv, cv.foot(y, SRC), "D"


# =============================================================================================
# E — small multiples, one shared scale per task
# =============================================================================================
def cand_E():
    # \u26a0 Panel height is a FUNCTION OF THE LEVEL COUNT, not a constant.  Two-up at a fixed 15 mm,
    # the five-level journal-quartile panel put its labels 1.2 mm apart and they overlapped \u2014
    # and it is the one panel on the page that carries a result.  One column, variable height.
    ROWH, LBLW, GAPY = 3.1, 26.0, 6.0
    PH_OF = lambda lvs: 5.0 + ROWH * len(lvs)
    cv = Cv()
    y = cv.head(6.0, TITLE,
                "One small panel per grouping variable, all ten on the same two scales \u2014 the "
                "point of a shared scale is that a panel cannot be made to look decisive by "
                "rescaling it. The dashed rule in each panel is the task mean; the flatness "
                "across all ten panels is the result.")
    RNG = {}
    for t in TASKS:
        g = su[su.task == t]
        lo = min(g.mean_err_w - 1.96 * g.sd_err_w / g.N ** 0.5)
        hi = max(g.mean_err_w + 1.96 * g.sd_err_w / g.N ** 0.5)
        pad = (hi - lo) * 0.06
        RNG[t] = (lo - pad, hi + pad)
    HW = (W - L - R - LBLW - 30.0) / 2.0      # 20 mm between blocks, 10 mm for the n column
    for k, t in enumerate(TASKS):
        x0 = L + LBLW + k * (HW + 20.0)
        cv.T(x0, y, "%s  n=%d" % (t, TN[t]), T_HEAD, DTASK[t], "bold")
        cv.T(x0, y + line_h(T_HEAD), "graded severity \u00b7 mean \u00b195%% CI \u00b7 all %.2f"
             % TMEAN[t], T_SMALL, FAINT)
    y += 7.4
    for k, t in enumerate(TASKS):
        x0 = L + LBLW + k * (HW + 20.0)
        a, b = RNG[t]
        for v in range(math.ceil(a), int(b) + 1):
            cv.T(x0 + (v - a) / (b - a) * HW, y, str(v), T_SMALL, FAINT, ha="center")
    y += 3.4
    for i, (nm, short, lvs) in enumerate(STRATS):
        PH = PH_OF(lvs)
        cv.T(L, y, nm, T_BODY, INK, "bold")
        cv.T(W - R, y, "separation %.2f SD causal \u00b7 %.2f descriptive"
             % (dsep(nm, "Causal"), dsep(nm, "Descriptive")), T_SMALL, FAINT, ha="right")
        py = y + 3.8
        for k, t in enumerate(TASKS):
            a, b = RNG[t]
            x0 = L + LBLW + k * (HW + 20.0)
            sx = lambda v: x0 + (v - a) / (b - a) * HW
            cv.bar(x0, py - 0.6, HW, PH - 3.6, "#f7f9f9", z=1)
            cv.ln(sx(TMEAN[t]), py - 0.6, sx(TMEAN[t]), py + PH - 4.2, INK, 0.6, 5, (0, (2.0, 1.4)))
            for j, lv in enumerate(lvs):
                rr = ROW(nm, lv, t)
                cy = py + j * ROWH + ROWH / 2 - 0.6
                lo_, hi_ = rr.mean_err_w - 1.96 * SE(rr), rr.mean_err_w + 1.96 * SE(rr)
                cv.ln(max(sx(lo_), x0), cy, min(sx(hi_), x0 + HW), cy, DTASK[t], 0.6, 4)
                cv.dot(sx(rr.mean_err_w), cy, 0.65, DTASK[t], z=6)
                if k == 0:
                    cv.T(L + 1.5, cy, lab(lv), T_SMALL, MUT, va="center")
                cv.T(x0 + HW + 1.5, cy, "%d" % int(rr.N), T_SMALL, FAINT, va="center")
        y += PH + GAPY
    y -= GAPY - 2.0
    cv.taskkey(L, y, "\u2014 bars are 95% confidence intervals; n at the right of each")
    y += 5.0
    return cv, cv.foot(y, SRC), "E"


# =============================================================================================
# F — the two axes against each other, one point per group
# =============================================================================================
def cand_F():
    cv = Cv()
    y = cv.head(6.0, TITLE,
                "Each group as one point: how badly its papers fail on validity against how "
                "opaque they are. If any grouping variable mattered, its levels would sit apart "
                "along one of the two axes. Instead every group of every variable lands inside a "
                "small cloud, and the only real separation on the page is between the two tasks.")
    PH = 68.0
    PW = W - L - R - 16.0
    for t in TASKS:
        g = su[su.task == t]
        xa, xb = float(g.mean_err_w.min()) - 0.25, float(g.mean_err_w.max()) + 0.25
        ya, yb = float(g.mean_rep_gap.min()) - 0.12, float(g.mean_rep_gap.max()) + 0.12
        # \u26a0 Both axis names live in the HEADER.  A y-axis label set above the plot's top-left
        # corner lands on this line \u2014 the collision check caught it on both panels.
        cv.T(L, y, "%s studies \u00b7 %d groups" % (t, len(g)), T_HEAD, DTASK[t], "bold")
        cv.T(L + cv.width("%s studies \u00b7 %d groups" % (t, len(g)), T_HEAD, "bold") + 3.0, y + 0.3,
             "vertical: reporting gaps per paper \u00b7 horizontal: graded validity severity",
             T_SMALL, FAINT)
        y += 5.0
        x0 = L + 14.0
        sx = lambda v: x0 + (v - xa) / (xb - xa) * PW
        sy = lambda v: y + PH - (v - ya) / (yb - ya) * PH
        cv.ln(x0, y + PH, x0 + PW, y + PH, RULE, 0.5)
        cv.ln(x0, y, x0, y + PH, RULE, 0.5)
        for v in range(math.ceil(xa), int(xb) + 1):
            cv.T(sx(v), y + PH + 1.2, str(v), T_SMALL, FAINT, ha="center")
        vv = ya
        for v in [x / 4 for x in range(int(ya * 4) + 1, int(yb * 4) + 1)]:
            if abs(v * 2 - round(v * 2)) < 1e-9:
                cv.T(x0 - 1.4, sy(v), "%.1f" % v, T_SMALL, FAINT, ha="right", va="center")
                cv.ln(x0, sy(v), x0 + PW, sy(v), "#f2f4f5", 0.4, 1)
        cv.dot(sx(TMEAN[t]), sy(float(st.loc[st.Study_Type == t, "n_rep_gaps"].mean())), 1.6,
               "none", INK, 5, 0.8)
        for nm, short, lvs in STRATS:
            for lv in lvs:
                r = ROW(nm, lv, t)
                rad = 0.5 + 1.6 * math.sqrt(int(r.N) / 180.0)
                cv.dot(sx(r.mean_err_w), sy(r.mean_rep_gap), rad, DTASK[t], "white", 6, 0.35)
        # name only the extremes of the one variable that separates, so the cloud stays a cloud
        for lv, ha in (("Q2", "left"), ("None", "right")):
            r = ROW("JCR 2022 quartile", lv, t)
            cv.T(sx(r.mean_err_w) + (2.4 if ha == "left" else -2.4), sy(r.mean_rep_gap),
                 "JCR %s  n=%d" % (lab(lv), int(r.N)), T_SMALL, INK,
                 ha=("left" if ha == "left" else "right"), va="center")
        y += PH + 12.0
    cv.T(L, y, "point area scales with n \u00b7 open circle = all papers of that task \u00b7 every "
         "grouping variable is plotted; only the journal quartile is labelled", T_SMALL, MUT)
    y += 4.5
    return cv, cv.foot(y, SRC), "F"


# =============================================================================================
# G — separation matrix: which variable moves which measure, in SD units
# =============================================================================================
def cand_G():
    MEAS = [("mean_err_w", "Graded\nseverity"), ("mean_validity", "Validity\nindex"),
            ("mean_dom_flag", "Domains\nflagged"), ("pct_ge3", "\u22653 domains\nflagged"),
            ("mean_rep_gap", "Reporting\ngaps"), ("mean_transparency", "Transparency\nindex"),
            ("mean_ack", "Acknowledge-\nment index")]
    CW, RH = 15.0, 7.0
    LBL = W - L - R - len(MEAS) * CW - 8.0
    cv = Cv()
    y = cv.head(6.0, TITLE,
                "Every grouping variable against every measure Figure 5 reports, scored on one "
                "common ruler: how far apart the variable pulls its groups, divided by how far "
                "apart the papers already are. A cell of 1.00 would mean the group gap equals "
                "the paper-to-paper spread. The largest of the %d cells is %.2f (%s, %s), and "
                "only %d reach 0.50."
                % (F_NCELLS, F_CELLMAX, prose(F_CELLMAX_WHO[0]), F_CELLMAX_WHO[1].lower(),
                   F_NCELL_HALF))
    for t in TASKS:
        cv.T(L, y, "%s studies" % t, T_HEAD, DTASK[t], "bold")
        y += 5.0
        for j, (mk, ml) in enumerate(MEAS):
            for q, sub in enumerate(ml.split("\n")):
                cv.T(L + LBL + j * CW + CW / 2, y + q * line_h(T_SMALL), sub, T_SMALL, MUT,
                     ha="center")
        y += 2 * line_h(T_SMALL) + 1.4
        ordt = strat_order(t)
        for i, (nm, short, lvs) in enumerate(ordt):
            cv.T(L, y + RH / 2, nm, T_BODY, INK, va="center")
            # every candidate carries n; this one summarises a whole variable per row, so the
            # row carries its level count and its smallest group
            ns = [int(ROW(nm, lv, t).N) for lv in lvs]
            cv.T(L + LBL - 3.0, y + RH / 2, "%d levels · min n %d" % (len(ns), min(ns)),
                 T_SMALL, FAINT, ha="right", va="center")
            for j, (mk, ml) in enumerate(MEAS):
                d = dsep(nm, t, mk)
                cx = L + LBL + j * CW
                a = 0.06 + 0.86 * min(d / 0.75, 1.0)
                cv.bar(cx + 0.6, y + 0.5, CW - 1.2, RH - 1.0, AC, alpha=a, z=2)
                cv.T(cx + CW / 2, y + RH / 2, "%.2f" % d, T_SMALL,
                     "white" if a > 0.55 else INK, "bold", ha="center", va="center")
            y += RH
        y += 9.0
    cv.T(L, y, "shaded by value \u00b7 rows ordered by separation in graded severity, "
         "independently within each task", T_SMALL, MUT)
    y += 4.5
    return cv, cv.foot(y, "Separation = (worst group \u2212 best group) \u00f7 the between-paper "
                       "standard deviation of that measure within that task. " + SRC), "G"


# =============================================================================================
# H — dumbbells: the task gap dwarfs every group gap
# =============================================================================================
def cand_H():
    RH, GH, GAP = 3.4, 4.4, 1.4
    nlev = sum(len(s[2]) for s in STRATS)
    cv = Cv()
    y = cv.head(6.0, TITLE,
                "One dumbbell per group, joining its descriptive papers to its causal papers on "
                "a single severity scale. The bars are long and nearly all the same length: the "
                "task a study attempts moves its severity by %.2f graded flaws, while the widest "
                "gap any grouping variable opens between its own groups is %.2f."
                % (F_TASKGAP, F_MAXSPREAD))
    LBL = 46.0
    PW = W - L - R - LBL - 14.0
    a, b = 2.2, 7.0
    sx = lambda v: L + LBL + (v - a) / (b - a) * PW
    y += 3.2               # clearance for the task-mean captions, which are set ABOVE this y
    for v in range(3, 8):
        cv.ln(sx(v), y + 2.0, sx(v), cv.H - 20.0, "#f0f3f4", 0.4, 1)
        cv.T(sx(v), y + 1.4, str(v), T_SMALL, FAINT, ha="center", va="bottom")
    for t in TASKS:
        cv.ln(sx(TMEAN[t]), y + 2.0, sx(TMEAN[t]), cv.H - 20.0, DTASK[t], 0.7, 5, (0, (2.4, 1.6)))
        # one clear line above the tick strip — at −0.4 the two overlapped by 0.6 mm
        cv.T(sx(TMEAN[t]), y - 2.2, "all %s %.2f" % (t.lower()[:4], TMEAN[t]), T_SMALL,
             DTASK[t], "bold", ha="center", va="bottom")
    y += 3.0
    for nm, short, lvs in STRATS:
        cv.T(L, y, nm, T_BODY, INK, "bold")
        y += GH
        for lv in lvs:
            cv.T(L + 2.0, y + RH / 2 - 0.2, lab(lv), T_SMALL, MUT, va="center")
            rd, rc = ROW(nm, lv, "Descriptive"), ROW(nm, lv, "Causal")
            cy = y + RH / 2 - 0.2
            cv.ln(sx(rd.mean_err_w), cy, sx(rc.mean_err_w), cy, "#d9dee1", 1.2, 3)
            cv.dot(sx(rd.mean_err_w), cy, 0.85, DTASK["Descriptive"], "white", 6, 0.4)
            cv.dot(sx(rc.mean_err_w), cy, 0.85, DTASK["Causal"], "white", 6, 0.4)
            cv.T(L + LBL - 1.5, cy, "%d\u2009|\u2009%d" % (int(rd.N), int(rc.N)), T_SMALL,
                 FAINT, ha="right", va="center")
            cv.T(L + LBL + PW + 2.0, cy, "%.2f" % (rc.mean_err_w - rd.mean_err_w), T_SMALL,
                 INK, va="center")
            y += RH
        cv.ln(L, y + GAP / 2, W - R, y + GAP / 2, "#eef1f3", 0.4, 1)
        y += GAP
    cv.T(L, y, "n shown as descriptive | causal \u00b7 right-hand number is the length of the "
         "bar, i.e. the task gap within that group", T_SMALL, MUT)
    y += 4.0
    cv.taskkey(L, y)
    y += 5.0
    return cv, cv.foot(y, SRC), "H"


# =============================================================================================
# I — Figure 5 panel D stratified: transparency against validity, per group
# =============================================================================================
def cand_I():
    cv = Cv()
    y = cv.head(6.0, TITLE,
                "Figure 5's two indices, one point per group, against the pooled means. Groups "
                "spread over %.2f of the validity index and %.2f of the transparency index — "
                "roughly a tenth and a twentieth of each scale. The strip beneath keeps Figure "
                "5's own median cut-off, where it belongs: on the papers, not on the groups."
                % (su.mean_validity.max() - su.mean_validity.min(),
                   su.mean_transparency.max() - su.mean_transparency.min()))
    PH = 74.0
    # 14 mm of y-axis gutter, 12 mm between the blocks, 4 mm of slack at the right edge —
    # at (W-L-R-18)/2 the right-hand panel ran 8 mm off the page.
    PW = (W - L - R - 30.0) / 2.0
    # ⚠ CROSSHAIRS AT THE POOLED MEANS, not the medians.  Both indices are left-skewed, so the
    # mean sits below the median — and against the medians 47 of the 50 group means fell in one
    # quadrant, which made the four-quadrant framing say nothing at all.  Figure 5's medians are
    # a cut-off for PAPERS; they are not a reference line for group means.
    MT, MV = MT_MEAN, MV_MEAN
    for k, t in enumerate(TASKS):
        x0 = L + 14.0 + k * (PW + 12.0)
        g = su[su.task == t]
        xa, xb = min(0.36, g.mean_validity.min() - .02), max(0.56, g.mean_validity.max() + .02)
        ya, yb = min(0.78, g.mean_transparency.min() - .01), max(0.88, g.mean_transparency.max() + .01)
        cv.T(x0 - 14.0 + 14.0, y, "%s studies" % t, T_HEAD, DTASK[t], "bold")
        yy = y + 5.0
        sx = lambda v: x0 + (v - xa) / (xb - xa) * PW
        sy = lambda v: yy + PH - (v - ya) / (yb - ya) * PH
        cv.ln(x0, yy + PH, x0 + PW, yy + PH, RULE, 0.5)
        cv.ln(x0, yy, x0, yy + PH, RULE, 0.5)
        for v in (0.40, 0.45, 0.50, 0.55):
            if xa <= v <= xb:
                cv.T(sx(v), yy + PH + 1.2, "%.2f" % v, T_SMALL, FAINT, ha="center")
        for v in (0.80, 0.82, 0.84, 0.86, 0.88):
            if ya <= v <= yb:
                cv.T(x0 - 1.2, sy(v), "%.2f" % v, T_SMALL, FAINT, ha="right", va="center")
        cv.ln(sx(MV), yy, sx(MV), yy + PH, VAL, 0.8, 5, (0, (2, 1.4)))
        cv.ln(x0, sy(MT), x0 + PW, sy(MT), VAL, 0.8, 5, (0, (2, 1.4)))
        cv.T(sx(MV) + 1.0, yy + 0.6, "mean validity %.2f" % MV, T_SMALL, VAL, "bold")
        cv.T(x0 + PW, sy(MT) - 1.0, "mean transparency %.2f" % MT, T_SMALL, VAL, "bold",
             ha="right", va="bottom")
        for nm, short, lvs in STRATS:
            for lv in lvs:
                r = ROW(nm, lv, t)
                rad = 0.5 + 1.5 * math.sqrt(int(r.N) / 180.0)
                cv.dot(sx(r.mean_validity), sy(r.mean_transparency), rad, DTASK[t], "white", 6, 0.35)
        for lv, dx, ha in (("Q2", 2.2, "left"), ("None", -2.2, "right")):
            r = ROW("JCR 2022 quartile", lv, t)
            cv.T(sx(r.mean_validity) + dx, sy(r.mean_transparency), "JCR %s" % lab(lv),
                 T_SMALL, INK, ha=ha, va="center")
        cv.T(x0 + PW, yy + PH + 4.4, "validity index \u2192", T_SMALL, FAINT, ha="right")
        cv.T(x0 - 1.2, yy - 1.2, "transparency index", T_SMALL, FAINT, ha="right", va="bottom")
    y += PH + 12.0
    # the quadrant counts, per group, as a compact strip
    cv.T(L, y, "Share of each group's papers in the low-validity half", T_HEAD, INK, "bold")
    y += 4.6
    CW = (W - L - R) / 5.0
    i = 0
    for nm, short, lvs in STRATS:
        for lv in lvs:
            c_, r_ = divmod(i, 5)
            px = L + r_ * CW
            py = y + c_ * 4.8
            rr = ROW(nm, lv, "Causal")
            lowv = 100.0 * (rr.q_hilo + rr.q_lolo) / rr.N
            # ⚠ the percentage sits on the BAR's line, not the label's — "Single/multi
            # Single-sector" is 28 mm wide and ran straight into a right-aligned number
            cv.T(px, py, "%s %s" % (short, lab(lv)), T_SMALL, MUT)
            cv.bar(px, py + 3.2, CW - 14.0, 0.9, "#e9ecee", z=2)
            cv.bar(px, py + 3.2, (CW - 14.0) * lowv / 100.0, 0.9, VAL, z=3)
            cv.T(px + CW - 12.5, py + 2.4, "%.0f%%" % lowv, T_SMALL, INK)
            i += 1
    y += ((i + 4) // 5) * 4.8 + 3.0
    cv.T(L, y, "point area \u221d n \u00b7 strip is causal papers only", T_SMALL, MUT)
    y += 4.5
    return cv, cv.foot(y, SRC), "I"


# =============================================================================================
# J — acknowledgement, stratified (Figure 5 panel K)
# =============================================================================================
def cand_J():
    RH, GH, GAP = 3.2, 4.4, 1.2
    nlev = sum(len(s[2]) for s in STRATS)
    cv = Cv()
    y = cv.head(6.0, TITLE,
                "Figure 5's third axis, stratified: of the flaws we found in a paper, what share "
                "did its own authors name in the discussion? Causal papers in Q1\u2013Q2 journals own "
                "%.2f of their flaws against %.2f in unranked ones \u2014 the one place a journal "
                "ranking does what it is assumed to do. It does not do it for validity."
                # weighted by n_ack_elig, the base mean_ack is actually computed on — weighting
                # by N would pool two means over the wrong denominator
                % (float(su[(su.stratifier == "JCR 2022 quartile") & (su.task == "Causal")
                            & (su.level.isin(["Q1", "Q2"]))]
                         .pipe(lambda g: (g.mean_ack * g.n_ack_elig).sum() / g.n_ack_elig.sum())),
                   float(ROW("JCR 2022 quartile", "None", "Causal").mean_ack)))
    LBL = 46.0
    PW = W - L - R - LBL - 16.0
    a, b = 0.0, 0.60
    sx = lambda v: L + LBL + (v - a) / (b - a) * PW
    y += 3.2               # clearance for the "all papers" caption, set ABOVE the tick strip
    for v in (0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6):
        cv.ln(sx(v), y + 2.2, sx(v), cv.H - 18.0, "#f0f3f4", 0.4, 1)
        cv.T(sx(v), y + 1.6, "%.1f" % v, T_SMALL, FAINT, ha="center", va="bottom")
    ALLACK = float(st.acknowledgement.dropna().mean())
    cv.ln(sx(ALLACK), y + 2.2, sx(ALLACK), cv.H - 18.0, INK, 0.8, 5, (0, (2.4, 1.6)))
    cv.T(sx(ALLACK), y - 2.2, "all papers %.2f" % ALLACK, T_SMALL, INK, "bold", ha="center",
         va="bottom")
    y += 3.2
    for nm, short, lvs in STRATS:
        cv.T(L, y, nm, T_BODY, INK, "bold")
        y += GH
        for lv in lvs:
            cv.T(L + 2.0, y + RH / 2 - 0.2, lab(lv), T_SMALL, MUT, va="center")
            cv.T(L + LBL - 1.5, y + RH / 2 - 0.2,
                 "%d | %d" % (int(ROW(nm, lv, "Descriptive").n_ack_elig),
                              int(ROW(nm, lv, "Causal").n_ack_elig)),
                 T_SMALL, FAINT, ha="right", va="center")
            for t in TASKS:
                r = ROW(nm, lv, t)
                cy = y + (0.4 if t == "Descriptive" else RH / 2 + 0.2)
                cv.bar(sx(0), cy, sx(float(r.mean_ack)) - sx(0), RH / 2 - 0.6, DTASK[t])
            # both values in ONE label at the row's end — at the bar ends they are 1.4 mm
            # apart vertically and the two 6.5 pt numbers overlap
            cv.T(L + LBL + PW + 2.0, y + RH / 2 - 0.2,
                 "%.2f | %.2f" % (ROW(nm, lv, "Descriptive").mean_ack,
                                  ROW(nm, lv, "Causal").mean_ack),
                 T_SMALL, INK, va="center")
            y += RH
        cv.ln(L, y + GAP / 2, W - R, y + GAP / 2, "#eef1f3", 0.4, 1)
        y += GAP
    cv.T(L, y, "n is the papers with at least one flagged domain, i.e. those that had something "
         "to acknowledge", T_SMALL, MUT)
    y += 4.0
    cv.taskkey(L, y)
    y += 5.0
    return cv, cv.foot(y, SRC), "J"


# =============================================================================================
# K — the distributions themselves, per group (Figure 5 panel F stratified)
# =============================================================================================
def cand_K():
    # TWO stratifiers per row, each with its own descriptive|causal pair.  One stratifier per
    # full-width row is the obvious layout and it came to 368 mm — 40 small plots simply do not
    # fit on a page stacked ten rows deep.
    NSTRAT_PER_ROW = 2
    CELLW = (W - L - R - 10.0) / NSTRAT_PER_ROW
    PW = (CELLW - 5.0) / 2.0
    PH = 9.0
    cv = Cv()
    y = cv.head(6.0, TITLE,
                "Not the group means but the whole distribution behind each one. Figure 5 shows "
                "these as two curves, one per task; here each curve is split by group. The "
                "curves inside a panel sit on top of one another \u2014 the group means differ "
                "because the distributions are shifted slightly, not because they are different "
                "distributions.")
    # \u26a0 NO descriptive/causal swatches here.  In this design the curves are coloured by LEVEL,
    # and task is carried by WHICH HALF of the cell a curve sits in \u2014 a task colour key would
    # credit an encoding the figure does not use.  The per-cell key below names the levels.
    for ln in cv.wrap("each cell: descriptive papers on the left, causal on the right \u2014 own "
                      "x-scale per task (0\u20137 and 0\u201313 graded severity) \u00b7 colours name levels, "
                      "and each cell's key gives that level's n as descriptive|causal",
                      W - L - R, T_SMALL):
        cv.T(L, y, ln, T_SMALL, MUT)
        y += line_h(T_SMALL)
    y += 2.2
    XMAX = {"Descriptive": 7.0, "Causal": 13.0}
    LSH = ["#0f5c6b", "#d03b3b", "#e08a12", "#4a7f3f", "#7a5ea8"]

    def keylines(cv_, x0, pw, levels, t, draw_at=None, nm=None):
        """Lay the per-level key out with WRAPPING; return the number of lines it takes.
        Called once to measure and once to draw, so the plot below it is never guessed at.
        The key names each level once and carries BOTH tasks' n, since one key serves both."""
        # ⚠ the colour index is the level's position in the variable's OWN level list, not its
        # position in the (possibly filtered) key — otherwise dropping one level for n < 5
        # silently reassigns every colour after it and the key stops matching the curves.
        full, keep = levels
        kx, lines = x0, 1
        for j, lv in enumerate(full):
            if lv not in keep:
                continue
            rd, rc = ROW(nm, lv, "Descriptive"), ROW(nm, lv, "Causal")
            s = "%s %d|%d" % (lab(lv), int(rd.N), int(rc.N))
            wneed = 3.0 + cv_.width(s, T_SMALL) + 3.4
            if kx + wneed > x0 + pw and kx > x0:
                kx, lines = x0, lines + 1
            if draw_at is not None:
                ky = draw_at + (lines - 1) * line_h(T_SMALL)
                cv_.bar(kx, ky + 0.6, 2.2, 0.8, LSH[j % len(LSH)])
                cv_.T(kx + 3.0, ky, s, T_SMALL, MUT)
            kx += wneed
        return lines

    for i in range(0, len(STRATS), NSTRAT_PER_ROW):
        band = STRATS[i:i + NSTRAT_PER_ROW]
        CELL, nlines = {}, 1
        for c_, (nm, short, lvs) in enumerate(band):
            cx = L + c_ * (CELLW + 10.0)
            CELL[c_] = {}
            for k, t in enumerate(TASKS):
                pw = PW - 3.0
                xs = [XMAX[t] * j / 109 for j in range(110)]
                cur = {}
                for lv in lvs:
                    vals = [float(v) for v in
                            pl.loc[(pl[nm] == lv) & (pl.Study_Type == t), "error_weighted"]]
                    if len(vals) >= 5:
                        cur[lv] = _kde(vals, xs, _silverman(vals))
                CELL[c_][t] = (cur, xs)
            # ONE key per cell, spanning the whole cell width, measured before anything is drawn
            keep = set(CELL[c_]["Causal"][0]) | set(CELL[c_]["Descriptive"][0])
            nlines = max(nlines, keylines(cv, cx, CELLW, (lvs, keep), "Causal", nm=nm))
        key_y = y + 3.6
        top_y = key_y + nlines * line_h(T_SMALL) + 1.2
        for c_, (nm, short, lvs) in enumerate(band):
            cx = L + c_ * (CELLW + 10.0)
            cv.T(cx, y, nm, T_BODY, INK, "bold")
            keep = set(CELL[c_]["Causal"][0]) | set(CELL[c_]["Descriptive"][0])
            keylines(cv, cx, CELLW, (lvs, keep), "Causal", draw_at=key_y, nm=nm)
            for k, t in enumerate(TASKS):
                x0 = cx + k * (PW + 5.0)
                pw, xm = PW - 3.0, XMAX[t]
                cur, xs = CELL[c_][t]
                if not cur:
                    continue
                base = top_y + PH
                cv.ln(x0, base, x0 + pw, base, RULE, 0.5)
                for v in range(0, int(xm) + 1, 4 if xm > 8 else 2):
                    cv.T(x0 + v / xm * pw, base + 2.2, str(v), T_SMALL, FAINT, ha="center")
                hi = max(max(c) for c in cur.values()) * 1.10
                for j, lv in enumerate(lvs):
                    if lv not in cur:
                        continue
                    col = LSH[j % len(LSH)]
                    c = cur[lv]
                    cv.ax.add_line(plt.Line2D(
                        [x0 + xs[q] / xm * pw for q in range(110)],
                        [base - c[q] / hi * PH for q in range(110)], color=col, lw=0.8, zorder=4))
                    r = ROW(nm, lv, t)
                    cv.ln(x0 + r.mean_err_w / xm * pw, base, x0 + r.mean_err_w / xm * pw,
                          base + 1.4, col, 0.8, 5)
        y = top_y + PH + 4.2 + 4.5
    y += 1.0
    for ln in cv.wrap("Gaussian kernel at Silverman's bandwidth, as Figure 5 panel F \u00b7 each "
                      "curve normalised within its own group \u00b7 tick under the axis marks the "
                      "group mean \u00b7 a level with fewer than 5 papers is not drawn",
                      W - L - R, T_SMALL):
        cv.T(L, y, ln, T_SMALL, MUT)
        y += line_h(T_SMALL)
    y += 2.5
    return cv, cv.foot(y, SRC), "K"


# =============================================================================================
# L — the existing table of bars, rebuilt print-native on the graded axis
# =============================================================================================
def cand_L():
    RH, GH, GAP = 2.8, 4.0, 1.2       # 50 rows; at 3.2/4.6 this ran to 265 mm
    nlev = sum(len(s[2]) for s in STRATS)
    cv = Cv()
    y = cv.head(6.0, TITLE,
                "The current figure's layout, rebuilt for print and moved onto the measures "
                "Figure 5 reports: graded severity, reporting gaps, and the share of papers "
                "flawed in at least three of the seven domains. Both scales are derived from "
                "the data and asserted, so a re-scoring cannot silently pin the bars.")
    LBL = 40.0
    CW = (W - L - R - LBL) / 3.0
    BW = CW - 13.0
    VMAX = math.ceil(su.mean_err_w.max() * 2 + 0.4) / 2.0
    RMAX = math.ceil(su.mean_rep_gap.max() * 2 + 0.4) / 2.0
    assert su.mean_err_w.max() <= VMAX and su.mean_rep_gap.max() <= RMAX, "bars clip"
    for j, (h, s) in enumerate([("Graded severity", "validity error score, 0\u2013%.1f" % VMAX),
                                ("Reporting gaps", "per paper, 0\u2013%.1f" % RMAX),
                                ("Flawed in \u22653 domains", "% of the group's papers")]):
        cv.T(L + LBL + j * CW, y, h, T_HEAD, INK, "bold")
        cv.T(L + LBL + j * CW, y + line_h(T_HEAD), s, T_SMALL, FAINT)
    cv.T(L, y, "Group", T_HEAD, FAINT, "bold")
    cv.ln(L, y + 7.4 - 1.2, W - R, y + 7.4 - 1.2, INK, 0.7)
    y += 7.4
    for nm, short, lvs in STRATS:
        cv.T(L, y, nm, T_BODY, INK, "bold")
        y += GH
        for lv in lvs:
            cv.T(L + 1.5, y + RH - 0.4, lab(lv), T_SMALL, MUT, va="center")
            for t in TASKS:
                r = ROW(nm, lv, t)
                cv.T(L + LBL - 1.5, y + 0.05, "%s %d" % (t[0], int(r.N)), T_SMALL, FAINT, ha="right")
                for j, (v, mx, col, fmt) in enumerate(
                        [(r.mean_err_w, VMAX, VAL, "%.2f"), (r.mean_rep_gap, RMAX, REP, "%.2f"),
                         (r.pct_ge3, 100.0, AC, "%.0f%%")]):
                    bx = L + LBL + j * CW
                    cv.bar(bx, y + 0.5, BW, RH - 1.4, "#eef1f2", z=2)
                    cv.bar(bx, y + 0.5, BW * min(v / mx, 1.0), RH - 1.4, col, z=3)
                    cv.T(bx + BW + 1.4, y, fmt % v, T_SMALL, INK)
                y += RH
        cv.ln(L, y + GAP / 2, W - R, y + GAP / 2, "#eef1f3", 0.4, 1)
        y += GAP
    cv.T(L, y, "D = descriptive, C = causal, with n \u00b7 grey track is the full scale, so a "
         "short bar reads as a low value and not as a missing one", T_SMALL, MUT)
    y += 5.0
    return cv, cv.foot(y, SRC), "L"


# =============================================================================================
# M — the compact result: only what separates, with the rest disposed of in one strip
# =============================================================================================
def cand_M():
    cv = Cv()
    y = cv.head(6.0, TITLE,
                "%d of the 10 grouping variables move graded severity by less than half a "
                "between-paper standard deviation on both tasks; they are disposed of in the "
                "strip at the foot. Only %s clear that bar, and the larger of them, journal "
                "quartile, does not run in the direction it is usually assumed to."
                % (len(F_SMALL), " and ".join(prose(n) for n in F_BIG)))
    # \u26a0 KEEP IS DERIVED, not typed.  The first draft listed journal quartile, team size and
    # sector while the caption said "less than half an SD" \u2014 and team size clears 0.47/0.43,
    # i.e. it belongs in the strip the caption sends it to.  The figure now cannot disagree
    # with its own caption.
    KEEP = list(F_BIG)
    PW = (W - L - R - 12.0) / 2.0
    PH_OF = lambda lvs: 14.0 + 4.4 * len(lvs)     # follow the level count, as candidate E does
    for k, t in enumerate(TASKS):
        cv.T(L + k * (PW + 12.0), y, "%s studies \u00b7 n=%d" % (t, TN[t]), T_HEAD, DTASK[t], "bold")
    y += 4.8
    for i, nm in enumerate(KEEP):
        lvs = dict((a, c) for a, _b, c in STRATS)[nm]
        PH = PH_OF(lvs)
        py = y
        cv.T(L, py, nm, T_BODY, INK, "bold")
        for k, t in enumerate(TASKS):
            x0 = L + k * (PW + 12.0) + 16.0
            pw = PW - 20.0
            g = su[su.task == t]
            a, b = float(g.mean_err_w.min()) - 0.2, float(g.mean_err_w.max()) + 0.2
            sx = lambda v: x0 + (v - a) / (b - a) * pw
            base = py + 4.0
            cv.ln(x0, base + PH - 8.0, x0 + pw, base + PH - 8.0, RULE, 0.5)
            for v in range(math.ceil(a), int(b) + 1):
                cv.T(sx(v), base + PH - 7.4, str(v), T_SMALL, FAINT, ha="center")
            cv.ln(sx(TMEAN[t]), base - 1.0, sx(TMEAN[t]), base + PH - 8.0, INK, 0.7, 5,
                  (0, (2.4, 1.6)))
            step = (PH - 10.0) / len(lvs)
            for j, lv in enumerate(lvs):
                r = ROW(nm, lv, t)
                cy = base + j * step + step / 2 - 1.0
                lo, hi = r.mean_err_w - 1.96 * SE(r), r.mean_err_w + 1.96 * SE(r)
                cv.ln(max(sx(lo), x0), cy, min(sx(hi), x0 + pw), cy, DTASK[t], 0.6, 4)
                cv.dot(sx(r.mean_err_w), cy, 0.75, DTASK[t], z=6)
                cv.T(x0 - 1.5, cy, "%s  %d" % (lab(lv), int(r.N)), T_SMALL, MUT, ha="right",
                     va="center")
            cv.T(x0 + pw, base + PH - 4.2, "gap %.2f = %.2f SD" % (
                sp[(sp.stratifier == nm) & (sp.task == t)
                   & (sp.measure == "mean_err_w")].iloc[0].spread, dsep(nm, t)),
                 T_SMALL, INK, ha="right")
        y += PH + 5.0
    y += 1.0
    cv.ln(L, y, W - R, y, RULE, 0.5)
    y += 2.4
    cv.T(L, y, "The %d that separate nothing" % len(F_SMALL), T_HEAD, INK, "bold")
    y += 4.4
    rest = [s for s in STRATS if s[0] not in KEEP]
    CW = (W - L - R) / 4.0
    for i, (nm, short, lvs) in enumerate(rest):
        c_, r_ = divmod(i, 4)
        px, py = L + r_ * CW, y + c_ * 8.0
        cv.T(px, py, nm, T_SMALL, INK, "bold")
        cv.T(px, py + 3.2, "causal %.2f SD \u00b7 descriptive %.2f SD"
             % (dsep(nm, "Causal"), dsep(nm, "Descriptive")), T_SMALL, MUT)
    y += ((len(rest) + 3) // 4) * 8.0 + 1.0
    return cv, cv.foot(y, "Separation = (worst group \u2212 best group) \u00f7 the between-paper "
                       "standard deviation within that task. " + SRC), "M"


# =============================================================================================
# N — the reversal: the same variable, opposite directions on the two tasks
# =============================================================================================
def cand_N():
    cv = Cv()
    y = cv.head(6.0, TITLE,
                "Each variable as a slope from its descriptive papers to its causal papers, on "
                "each task's own scale. Lines that cross carry a reversal \u2014 a group that "
                "is among the cleanest on one task and among the worst on the other. Journal "
                "quartile is the clearest: Q1 is the best descriptive band and nearly the worst "
                "causal one.")
    NC = 2
    PW = (W - L - R - 10.0) / NC
    PH = 26.0
    rows = (len(STRATS) + NC - 1) // NC
    for i, (nm, short, lvs) in enumerate(STRATS):
        r_, c_ = divmod(i, NC)
        px = L + c_ * (PW + 10.0)
        py = y + r_ * (PH + 6.0)
        cv.T(px, py, nm, T_HEAD, INK, "bold")
        base = py + 4.2
        xd, xc = px + 30.0, px + PW - 30.0
        RG = {}
        for t in TASKS:
            g = su[(su.stratifier == nm) & (su.task == t)]
            lo, hi = float(g.mean_err_w.min()), float(g.mean_err_w.max())
            m = (hi - lo)
            RG[t] = (lo - m * 0.30 - 0.02, hi + m * 0.30 + 0.02)
        sy = lambda t, v: base + PH - 6.0 - (v - RG[t][0]) / (RG[t][1] - RG[t][0]) * (PH - 8.0)
        cv.ln(xd, base - 1.0, xd, base + PH - 5.0, RULE, 0.5)
        cv.ln(xc, base - 1.0, xc, base + PH - 5.0, RULE, 0.5)
        cv.T(xd, base + PH - 4.4, "descriptive", T_SMALL, DTASK["Descriptive"], "bold", ha="center")
        cv.T(xc, base + PH - 4.4, "causal", T_SMALL, DTASK["Causal"], "bold", ha="center")
        LSH = ["#0f5c6b", "#d03b3b", "#e08a12", "#4a7f3f", "#7a5ea8"]
        YD = [sy("Descriptive", ROW(nm, lv, "Descriptive").mean_err_w) for lv in lvs]
        YC = [sy("Causal", ROW(nm, lv, "Causal").mean_err_w) for lv in lvs]
        for j, lv in enumerate(lvs):
            rd, rc = ROW(nm, lv, "Descriptive"), ROW(nm, lv, "Causal")
            col = LSH[j % len(LSH)]
            cv.ln(xd, YD[j], xc, YC[j], col, 0.9, 4)
            cv.dot(xd, YD[j], 0.6, col, z=6); cv.dot(xc, YC[j], 0.6, col, z=6)
        # ⚠ A slopegraph's end labels sit at the data values, and this figure exists BECAUSE
        # some levels share a value almost exactly (causal Q1 6.33 vs not-ranked 6.40, three
        # millimetres of panel apart).  Push the labels apart to a legible pitch and draw a
        # leader wherever a label had to move, so the label still points at its own dot.
        for side, ys, ha, dx in ((0, YD, "right", -1.8), (1, YC, "left", 1.8)):
            adj = declutter(ys, 2.55)
            for j, lv in enumerate(lvs):
                col = LSH[j % len(LSH)]
                r = ROW(nm, lv, "Descriptive" if side == 0 else "Causal")
                s = ("%s %.2f" % (lab(lv), r.mean_err_w) if side == 0
                     else "%.2f  n%d" % (r.mean_err_w, int(r.N)))
                ax_ = xd if side == 0 else xc
                if abs(adj[j] - ys[j]) > 0.35:
                    cv.ln(ax_ + dx * 0.45, ys[j], ax_ + dx * 0.95, adj[j], col, 0.35, 3)
                cv.T(ax_ + dx, adj[j], s, T_SMALL, col, ha=ha, va="center")
    y += rows * (PH + 6.0) + 1.0
    for ln in cv.wrap("⚠ Each panel has its OWN vertical scale on each side — the "
                      "slope shows the rank change between tasks, never the size of the "
                      "task gap (for that see the dumbbells).", W - L - R, T_SMALL):
        cv.T(L, y, ln, T_SMALL, MUT)
        y += line_h(T_SMALL)
    y += 2.5
    return cv, cv.foot(y, SRC), "N"


CANDS = {"A": cand_A, "B": cand_B, "C": cand_C, "D": cand_D, "E": cand_E, "F": cand_F,
         "G": cand_G, "H": cand_H, "I": cand_I, "J": cand_J, "K": cand_K, "L": cand_L,
         "M": cand_M, "N": cand_N}

if __name__ == "__main__":
    want = [a.upper() for a in sys.argv[1:]] or sorted(CANDS)
    print("Figure 6 candidates -> %s/" % OUTDIR)
    bad, tall = {}, []
    for k in want:
        HH[0] = 400.0                      # pass 1: measure where the content actually ends
        cv, used, letter = CANDS[k]()
        plt.close(cv.fig)
        HH[0] = round(used + 2.5, 1)       # pass 2: draw it at that height
        cv, used, letter = CANDS[k]()
        c = cv.save(letter, used)
        if c:
            bad[letter] = c
        if cv.H > 250.0:
            tall.append("%s %.0f" % (letter, cv.H))
    print("\n  drawn on error_weighted (graded severity), task means %.2f desc / %.2f causal"
          % (TMEAN["Descriptive"], TMEAN["Causal"]))
    if bad:
        print("  ⚠ text collisions in: %s" % ", ".join(sorted(bad)))
    if tall:
        print("  ⚠ over the 250 mm page ceiling: %s" % ", ".join(tall))

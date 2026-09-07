# -*- coding: utf-8 -*-
"""Supplementary Figures S10 and S11: the parts of the adjudication record the manuscript
figure cannot carry.  PDF, TIFF, PNG, print-native.

    python code/figures/08_22_2026_adjudication_supplement_figure.py

WHY THIS FIGURE EXISTS
The process report behind Figure 3 runs to eight sections; Figure 3 carries two of
them (the flow with its denominators, and what adjudication did to the reviewers'
answers).  Of the remaining six, three are here and three are deliberately left out:

  IN   03  disagreement by instrument item  -> S7 panel A, and S8.  The single most useful
           thing in the report: it shows WHICH items were hard, which is the only
           honest answer to "your agreement was 69%".
  IN   05  the two adjudicators compared    -> S7 panel B.  A self-criticism, de-identified.
  IN   06  the phase-II asymmetry           -> S7 panel C.  A self-criticism, and the
           one that appears nowhere else in the submission.
  OUT  02  disagreement by study task       -> one line of prose, in panel A's note.
  OUT  04  workload per paper               -> not reported.  It describes how the
           work was distributed, not how reliable it was.
  OUT  08  blinding / position confound     -> CUT 2026-08-22 (TSA).  A fourth panel
           made the page unreadable, and the confound is already conceded in the
           Discussion's limitations and stated in Supplementary Methods 5.  The full
           analysis, with its table, stays in the process report itself.

*** THE TWO SELF-CRITICISMS MUST NOT VANISH IN THE MOVE. ***  A reviewer who finds
either of them in the deposited data but not in the paper reads it as concealment.
Both are in Supplementary Methods 5 as prose as well as in panels B and C here.

*** THE ADJUDICATORS ARE NOT NAMED IN THIS FIGURE. ***  Panels B and C carry per-person
statistics, so they use "Adjudicator 1" and "Adjudicator 2", the same convention and the
same mapping as the process report (adjTA -> Adjudicator 1).  Supplementary Methods 5
was de-identified to match on 2026-08-22: naming them there while anonymising here would
have achieved nothing, because the percentages line the two up immediately.  ⚠ It is
pseudonymisation, not anonymity - the numbering follows the order the Methods names them.

*** NEVER RANK INDIVIDUAL REVIEWERS by the rate at which their answer was upheld. ***
That table exists (process-tables/reviewer.csv, 24.8% to 54.2%) and was deliberately
dropped from the report.  Nothing here is per reviewer.

*** REVIEWER NUMBERING, if a reviewer is ever shown again. ***  Fourteen reviewers were
recruited and one withdrew before data collection, so the source workbooks' identifiers
run 1,2,4..14.  Every published figure and table numbers the thirteen 1..13; the mapping
is built in code/scoring/07_24_2026_adjudication_process_analysis.R, which carries the
source identifier alongside as Reviewer_original.  Only code/reviewer-ops/ uses the
source identifiers, because those address real people.

*** ITEMS ARE RANKED ON p0, NOT ON kappa. ***  kappa is distorted by prevalence and
bias when one answer dominates (Byrt, Bishop & Carlin 1993, J Clin Epidemiol 46:423-9),
and most items here have a dominant answer, so a kappa ranking would report the answer
distribution rather than the difficulty.  AC1 (Gwet) is plotted beside p0 as the
chance-corrected reading that does not have that failure mode.

DENOMINATORS, WHICH DIFFER BETWEEN PANELS AND MUST BE LABELLED AS SUCH
  panel A  p0 is over cells BOTH reviewers answered (n_both).  Applicability disputes
           (one answered, the other judged the item not to apply) are excluded from p0
           and counted separately - they are disagreements about the shape of the
           study, not about its quality.
  panel B  each adjudicator over the cells THAT adjudicator ruled on (2,084 / 2,056),
           which is the denominator the process report uses.
  panel C  the 697 cells where BOTH adjudicators ruled and they DIFFERED.  The report
           quotes 531/195/63 over all 789 phase-II cells, but 92 of those had only one
           adjudicator's call on record, which makes "agreed with that adjudicator"
           partly structural.  The clean subset gives 471/167/59 - the asymmetry is
           73.8% either way, so it survives the stricter denominator.  Both are shown.

SOURCES
  data/adjudication/process-tables/cell_level_detail.csv   panels B and C, recomputed
       here from the raw r1/r2/adjTA/adjYA/p2 columns and asserted against the report's
       published counts (2,084/828/951/305, 2,056/857/980/219, 531/195/63).
  outputs/tables/08_19_2026_agreement_difficulty_ranking.csv   panel A (Tier 1b, p0 with
       bootstrap CI and AC1).  Its p0 is asserted against agreement counts recomputed
       from cell_level_detail.csv, so the two files are checked against each other.  It
       ranks only items with >= 20 both-answered cells, which is why 40 of 47 are shown.

READING THE SOURCE CSV: it is written by R, so a missing value is a BARE `NA` while a
recorded answer is quoted.  `raw()` applies that rule in one place.  Reading it without
it turns missing rulings into recorded "NA" answers and inverts every count.

NORMALISATION: norm1()/normNA() reproduce the R rules byte for byte (casefold, collapse
whitespace, sort the parts of a ";" multiselect, treat "skipped"/"should be skipped" as
blank).  The assertions above are what prove the reproduction is exact - if they fail,
the normalisation has drifted and nothing below can be trusted.

TWO FIGURES, BOTH WRITTEN ON EVERY RUN
  S7  the primary one.  Panel A is one row per instrument CONCEPT - a question the tool
      puts to more than one study task is one row - then panels B and C.
  S8  the same agreement statistic item by item, stratified by task, panel A alone.
      ⚠ S8 does NOT repeat panels B and C.  They are the same numbers either way, and
      printing them twice invites a reader to look for a difference that does not exist.
Both were one figure behind a COLLAPSE_TASKS environment variable until 2026-08-22.
Once both went into the submission package that became a way to ship a stale file, so
the switch is gone and the two are built together.

⚠ POOLING IS NOT FREE, WHICH IS WHY S8 EXISTS.  Agreement on the SAME question differs
by task - baseline selection bias runs p0 = 0.79 on descriptive papers against 0.64 on
causal, sampling technique 0.77 against 0.63 - and S7's collapsed p0 is the cell-weighted
average of the two.  That is a real quantity, but a different one, and S7 alone cannot
show the spread.  Both tables come from the same R script and the same statistics;
neither is derived from the other in this file.

OUTPUT (outputs/figures/)  08_22_2026_adjudication_supplement.{pdf,tif,png}  -> S7
                           08_22_2026_agreement_by_item.{pdf,tif,png}        -> S8
"""
import csv, os, re, collections
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

D = r"."
os.chdir(D)
OUTDIR = "outputs/figures"
# Panel A has two variants and BOTH are built on every run - see configure() below.
# They were behind an environment variable until 2026-08-22; once both went into the
# submission package that became a way to ship a stale file, so the switch is gone.
STEM_S7 = "08_22_2026_adjudication_supplement"      # concepts, then panels B and C
STEM_S8 = "08_22_2026_agreement_by_item"            # the same statistic, item by item
CELLS = "data/adjudication/process-tables/cell_level_detail.csv"
RANK_ITEM = "outputs/tables/08_19_2026_agreement_difficulty_ranking.csv"
RANK_CONCEPT = "outputs/tables/08_22_2026_agreement_collapsed_by_concept.csv"

# mathtext is routed through Arial as well, so "$p_0$" and "$AC_1$" render as real
# subscripts without pulling a second family into the PDF: Arial has no subscript
# glyphs of its own, and matplotlib's default mathtext font is DejaVu.  The font check
# at the foot asserts the PDF ends up carrying Arial and nothing else.
matplotlib.rcParams.update({"pdf.fonttype": 42, "ps.fonttype": 42, "font.family": "Arial",
                            "mathtext.fontset": "custom", "mathtext.rm": "Arial",
                            "mathtext.it": "Arial:italic", "mathtext.bf": "Arial:bold",
                            "mathtext.default": "regular"})
PT2MM = 25.4 / 72.0
W = 180.0
MIN_PT = 6.5                      # journal floor; asserted at the end

INK, MUT, AC = "#111417", "#4a5259", "#0f5c6b"
RULE, GRID_C = "#c8ced2", "#e6eaec"
DOM = {                            # panel A, by bias domain
    "Selection bias":    "#1b6b7a",
    "Confounding":       "#c9922f",
    "Measurement bias":  "#4f7fa8",
    "Missing data":      "#8a6ea8",
    "Random error":      "#5f9e6e",
    "Mentioning errors": "#b5563f",
    "Design and scope":  "#8b8f94",
}
# the five bias domains are the instrument's own; everything else is scaffolding
OTHER = {"Study design", "Study task", "Saudi population", "Conflating the task", "Recusal"}
VERD = {"first": "#2c7f92", "second": "#5aa8b8", "over": "#c9922f"}   # as Figure 3
# panel C uses a different family on purpose: the same colours would mean two
# different things two panels apart
JOINT = {"ta": "#3f6f52", "ya": "#9dbfa6", "new": "#b9c0c4"}

T_TITLE, T_PANEL, T_BODY, T_SMALL = 9.5, 8.0, 7.0, 6.5
LEAD = 1.30
line_h = lambda pt: pt * LEAD * PT2MM
TASK_TAG = {"Causal": "C", "Descriptive": "D", "Predictive": "P", "All": "\u2022"}


# =============================================================================
# Read and recompute.  Nothing below is typed in.
# =============================================================================
NAV = {"skipped", "should be skipped"}


def norm1(v):
    s = "" if v is None else str(v)
    s = re.sub(r"\s+", " ", s.strip().lower())
    if s == "nan":
        s = ""
    if ";" in s:
        s = ";".join(sorted(p.strip() for p in s.split(";") if p.strip()))
    return s


def normNA(v):
    s = norm1(v)
    return "" if s in NAV else s


raw = lambda x: "" if x in ("", "NA") else x       # bare NA from R == missing

cd = list(csv.DictReader(open(CELLS, encoding="utf-8-sig")))
routed = [r for r in cd if r["status"].startswith("Disagreed")]
assessed = [r for r in cd if r["status"] != "Not applicable to either reviewer"]
agreed = [r for r in cd if r["status"] == "Reviewers agreed"]
GRID, ASSESSED, AGREED, ROUTED = len(cd), len(assessed), len(agreed), len(routed)
assert (GRID, ASSESSED, AGREED, ROUTED) == (18095, 7278, 5021, 2257), (GRID, ASSESSED, AGREED, ROUTED)

# -- panel B: each adjudicator against the two reviewers, on the cells they ruled
def adjudicator(col):
    x = [r for r in routed if norm1(raw(r[col])) != ""]
    u1 = u2 = ov = 0
    for r in x:
        a, f, s = normNA(raw(r[col])), normNA(raw(r["r1"])), normNA(raw(r["r2"]))
        u1 += a == f
        u2 += a == s
        ov += a != f and a != s
    return len(x), u1, u2, ov


# ⚠ ANONYMISED IN THE FIGURE, as the process report has been since it was written.
# The two adjudicators are shown as "Adjudicator 1" and "Adjudicator 2", never by
# initials, because panels B and C carry per-person statistics and naming them puts a
# named individual's error behaviour in the published record.  The mapping below is the
# SAME one the process report uses (adjTA -> Adjudicator 1), so the two documents agree.
# ⚠ This is pseudonymisation, not anonymity: the numbering follows the order the two are
# named in the Methods, so a determined reader can infer it.  Do not claim otherwise.
ADJ = [("Adjudicator 1", adjudicator("adjTA")), ("Adjudicator 2", adjudicator("adjYA"))]
assert [a[1] for a in ADJ] == [(2084, 828, 951, 305), (2056, 857, 980, 219)], ADJ

# -- panel C: what the joint sitting settled on
p2cells = [r for r in routed if raw(r["p2"]) != ""]
both_ruled = [r for r in p2cells if r["phase1"].startswith("Phase I discordant")]
one_ruled = [r for r in p2cells if r["phase1"].startswith("Only one")]


def joint(cells):
    ta = ya = new = 0
    for r in cells:
        a, b, p = normNA(raw(r["adjTA"])), normNA(raw(r["adjYA"])), normNA(raw(r["p2"]))
        ta += p == a
        ya += p == b
        new += p != a and p != b
    return ta, ya, new


P2_ALL, P2_BOTH = joint(p2cells), joint(both_ruled)
assert len(p2cells) == 789 and len(both_ruled) == 697 and len(one_ruled) == 92
assert P2_ALL == (531, 195, 63), P2_ALL          # the report's published figures
assert P2_BOTH == (471, 167, 59), P2_BOTH        # the stricter denominator

# -- disagreement by task, for panel A's note (section 02, reduced to one line)
BYTASK = []
for t in ("Causal", "Descriptive", "Predictive"):
    a = [r for r in assessed if r["Study_Type"] == t]
    dis = [r for r in a if r["status"].startswith("Disagreed")]
    BYTASK.append((t, 100.0 * len(dis) / len(a)))

# -- panel A.  TWO VARIANTS, chosen by the COLLAPSE_TASKS environment variable:
#      unset  one row per tool ITEM, so a question put to two tasks appears twice
#      = 1    one row per tool CONCEPT, pooled across tasks
# Both come from the same R script and the same statistics; the collapsed table is
# section 8 of 08_19_2026_agreement_sensitivity_tier1.R, added 2026-08-22.
# ⚠ Pooling is not free: agreement on the SAME question differs by task (errors
# mentioned in the discussion runs p0 0.30 causal against 0.41 descriptive), and the
# collapsed p0 is the n-weighted average of the two.  The figure says which it shows,
# and the collapsed rows carry the tasks they pool.
both_by_var = collections.Counter()
agree_by_var = collections.Counter()
for r in cd:
    if r["status"] in ("Reviewers agreed", "Disagreed on the answer"):
        both_by_var[r["variable"]] += 1
        agree_by_var[r["variable"]] += r["status"] == "Reviewers agreed"
APPLIC = sum(1 for r in cd if r["status"] == "Disagreed on applicability")
assert APPLIC == 483, APPLIC

num = lambda v: None if v in ("", "NA") else float(v)      # R writes a bare NA


def configure(collapsed):
    """Select the panel-A table and the column geometry for one variant.

    Everything else on the page - panels B and C, the cell census - is identical
    between the two, so it is read once above and not touched here."""
    global COLLAPSED, STEM, PL_W, COL_TASK, COL_N, COL_P0, COL_AC
    global items, N_TOTAL, N_OMIT, APPLIC_SHOWN, OMIT_APPLIC, UNIT, UNIT_PL
    COLLAPSED = collapsed
    STEM = STEM_S7 if collapsed else STEM_S8

    if collapsed:
        rows = list(csv.DictReader(open(RANK_CONCEPT, encoding="utf-8-sig")))
        assert len(rows) == 32, len(rows)
        # the collapse must conserve cells - the R script asserts this too, but the
        # figure is published from these numbers, so it checks them against the cell
        # record itself
        assert sum(int(r["n_both"]) for r in rows) == sum(both_by_var.values()) == 6795
        assert sum(int(r["n_agree"]) for r in rows) == sum(agree_by_var.values()) == 5021
        assert sum(int(r["n_applic_dispute"]) for r in rows) == APPLIC
        items = [r for r in rows if r["below_min_n"] == "FALSE"]
        omitted = [r for r in rows if r["below_min_n"] == "TRUE"]
        for r in items:
            r["_tag"] = r["tasks"]
        UNIT, UNIT_PL = "concept", "concepts"
    else:
        rows = items = list(csv.DictReader(open(RANK_ITEM, encoding="utf-8-sig")))
        for r in items:
            v = r["variable"]
            assert int(r["n_both"]) == both_by_var[v], (v, r["n_both"], both_by_var[v])
            assert abs(float(r["p0"]) - agree_by_var[v] / both_by_var[v]) < 0.0015, v
            r["_tag"] = TASK_TAG[r["task"]]
        # Tier 1b ranks only items with >= 20 both-answered cells.  The seven it drops
        # are dropped BECAUSE the reviewers so rarely both answered them: on those items
        # the dispute was mostly about whether the item applied at all, which is the
        # branch disagreement panel A's note describes, not an agreement rate.
        shown = {r["variable"] for r in items}
        omitted = sorted({r["variable"] for r in cd} - shown)
        assert len(shown) == 40 and len(omitted) == 7
        UNIT, UNIT_PL = "item", "items"

    N_OMIT = len(omitted)
    N_TOTAL = len(items) + N_OMIT
    APPLIC_SHOWN = sum(int(r["n_applic_dispute"]) for r in items)
    OMIT_APPLIC = APPLIC - APPLIC_SHOWN
    assert N_OMIT in (4, 7) and OMIT_APPLIC > 0, (N_OMIT, OMIT_APPLIC)
    items.sort(key=lambda r: (float(r["p0"]), r["label"]))
    for r in items:
        r["_dom"] = r["domain"] if r["domain"] in DOM else "Design and scope"
        assert r["domain"] in DOM or r["domain"] in OTHER, r["domain"]
        r["_p0"], r["_lo"], r["_hi"] = float(r["p0"]), num(r["p0_lo"]), num(r["p0_hi"])
        r["_ac1"] = num(r["AC1"])
        assert r["_lo"] is not None and r["_hi"] is not None, r["label"]

    # the collapsed variant gives up 7 mm of axis to a column naming the tasks pooled
    # into each row: without it the reader cannot see that a p0 is an average over two
    # item sets
    PL_W = 59.0 if collapsed else 66.0
    COL_TASK = 155.5
    COL_N, COL_P0, COL_AC = (163.5, 171.5, 179.0) if collapsed else (158.5, 168.5, 178.0)


f = lambda n: "{:,}".format(n)
pc = lambda n, d: 100.0 * n / d


# =============================================================================
# Canvas
#
# ONE page, three panels.  With the position/confound panel it came to 322 mm and read
# as jammed; without it the three fit, but only just, so the item table's row pitch is
# 2.80 mm rather than 3.10.  The 6.5 pt floor and the full item labels are not
# negotiable - they are what the page is for - so if anything else has to be added
# here, split the figure rather than shrink the type.
#
# The page height is MEASURED, not guessed: build() lays the panels out on a running
# cursor and returns the y it finished at, so the figure is drawn twice - once
# oversized to find the bottom, once at that height.  Adding a row to any table
# therefore cannot silently push content off the page.
# =============================================================================
ROW = 2.65                                  # item table row pitch (6.5 pt line = 2.29 mm)
TOP = 15.5
LAB_X, LAB_W = 10.0, 74.0                   # item label column
PL_X = 86.0                                 # p0 axis, 0 -> 1;  PL_W and the COL_*
                                            # positions are set by configure()
TEXT_W = 178.0 - LAB_X                      # wrapping width for every prose line
BAR_X, BAR_W, BAR_H = 26.0, 118.0, 5.0      # panels B and C
GAP = 6.5                                   # between panels

f = lambda n: "{:,}".format(n)
pc = lambda n, d: 100.0 * n / d
x_of = lambda p: PL_X + PL_W * p


class Page:
    """One figure.  Every text call is recorded so the type floor and the label
    column can be checked against what was actually drawn, not what was intended."""

    def __init__(self, H):
        self.fig = plt.figure(figsize=(W / 25.4, H / 25.4))
        self.ax = self.fig.add_axes([0, 0, 1, 1])
        self.ax.set_xlim(0, W); self.ax.set_ylim(H, 0); self.ax.axis("off")
        self.ax.add_patch(Rectangle((0, 0), W, H, fc="white", ec="none", zorder=0))
        self.sizes, self.labels = [], []
        self.ymax = 0.0                       # lowest point anything has been drawn to

    def T(self, x, y, s, pt=T_BODY, c=INK, weight="normal", ha="left", va="top", z=4):
        self.sizes.append(pt)
        self.ymax = max(self.ymax, y + (line_h(pt) if va == "top" else
                                        line_h(pt) / 2 if va == "center" else 0.0))
        return self.ax.text(x, y, s, fontsize=pt, color=c, fontweight=weight, ha=ha, va=va, zorder=z)

    def width(self, s, pt):
        """Rendered width of `s` in mm.  Measured, because these strings mix mathtext
        with prose and no character-count estimate survives that."""
        t = self.ax.text(0, 0, s, fontsize=pt, zorder=0)
        w = t.get_window_extent(self.fig.canvas.get_renderer()).width / self.fig.dpi * 25.4
        t.remove()
        return w

    def wrap(self, s, pt=T_SMALL, maxw=None):
        """Greedy word wrap on measured width.  Prose is written as one paragraph and
        broken here, so a wording change cannot leave a line hanging off the page."""
        maxw = TEXT_W if maxw is None else maxw
        out, line = [], ""
        for word in s.split(" "):
            trial = word if not line else line + " " + word
            if self.width(trial, pt) > maxw and line:
                out.append(line); line = word
            else:
                line = trial
        if line:
            out.append(line)
        return out

    def title(self, main, sub):
        self.T(4.0, 4.0, main, T_TITLE, INK, "bold")
        for i, s in enumerate(self.wrap(sub, T_SMALL, W - 8.0)):
            self.T(4.0, 4.0 + line_h(T_TITLE) + i * line_h(T_SMALL), s, T_SMALL, MUT)

    def head(self, y, letter, title, sub=""):
        # A panel that starts above the previous panel's last line silently draws one on
        # top of the other - the page-bounds check below cannot see it, because nothing
        # has left the page.  Threading the cursor wrong is the easy mistake here, so
        # the invariant is asserted rather than trusted.
        assert y >= self.ymax - 0.05, (letter, round(y, 1), round(self.ymax, 1))
        if letter:
            self.T(LAB_X - 6.0, y, letter, T_PANEL, INK, "bold")
        self.T(LAB_X, y, title, T_PANEL, INK, "bold")
        self.ax.add_line(plt.Line2D([LAB_X - 6.0, W - 1.0], [y + line_h(T_PANEL) + 0.6] * 2,
                                    color=RULE, lw=0.5, zorder=2))
        return self.notes(y + line_h(T_PANEL) + 1.8, sub)

    def notes(self, y, paras):
        for s in ([paras] if isinstance(paras, str) else paras):
            for ln in self.wrap(s):
                self.T(LAB_X, y, ln, T_SMALL, MUT)
                y += line_h(T_SMALL)
        return y

    def legend(self, y, entries):
        lx = LAB_X
        for lab, col, kind in entries:
            if kind == "swatch":
                self.ax.add_patch(Rectangle((lx, y - 1.2), 2.4, 2.4, fc=col, ec="none", zorder=2))
                dx = 3.6
            else:
                self.ax.plot([lx + 0.9], [y], marker="o", ms=2.6, mfc=col, mec=col, zorder=4)
                dx = 2.8
            self.T(lx + dx, y, lab, T_SMALL, MUT, va="center")
            lx += dx + len(lab) * T_SMALL * 0.50 * PT2MM + 4.4
        assert lx < W, lx
        return y + 1.2

    def stacked(self, y, n, segs, lead, tail, bold=False):
        """One 100% bar: segs = [(value, colour, dark_text)].  `bold` marks a lead that
        names the row (an adjudicator) rather than describing it ("settled on")."""
        self.T(BAR_X - 2.0, y + BAR_H / 2, lead, T_SMALL, INK if bold else MUT,
               "bold" if bold else "normal", ha="right", va="center")
        x = BAR_X
        for val, col, dark in segs:
            w = BAR_W * val / n
            self.ax.add_patch(Rectangle((x, y), w, BAR_H, fc=col, ec="white", lw=0.5, zorder=2))
            if w > 9.0:
                self.sizes.append(T_SMALL)
                self.ax.text(x + w / 2, y + BAR_H / 2, "%s   %.1f%%" % (f(val), pc(val, n)),
                             fontsize=T_SMALL, color=INK if dark else "white", ha="center",
                             va="center", zorder=4, fontweight="bold")
            x += w
        self.T(BAR_X + BAR_W + 2.0, y + BAR_H / 2, tail, T_SMALL, MUT, va="center")
        self.ymax = max(self.ymax, y + BAR_H)
        return y + BAR_H


def two_pass(fn):
    """Draw once oversized to find the bottom, then again at exactly that height."""
    p = fn(400.0)
    plt.close(p.fig)
    H = p.bottom + 4.0
    p = fn(H)
    return p, H


# =============================================================================
# The page
# =============================================================================
def supplement_page(H):
    p = Page(H)
    lead = ("$p_0$, the share of cells the two reviewers answered identically (filled circle, with 95% "
            "bootstrap interval), and Gwet's $AC_1$ (open diamond), over the cells both reviewers "
            "answered. Ordered hardest first. ")
    if COLLAPSED:
        p.title("Where the two reviewers disagreed, and what the adjudicators did with it",
                "%s of the %s assessed cells (%.1f%%) went to adjudication. Panels A to C report the "
                "three parts of the adjudication record that Figure 3 does not carry."
                % (f(ROUTED), f(ASSESSED), pc(ROUTED, ASSESSED)))
        y = p.head(TOP, "A", "Agreement between the two reviewers, by instrument concept",
                   lead +
                   "Not stratified by study task: a question put to more than one task is one row, and "
                   "its $p_0$ is the cell-weighted average over the task-specific item sets, which are "
                   "named in the tasks column (C causal, D descriptive, P predictive, A asked of all). "
                   "Agreement on the same question can differ by task; Supplementary Figure S11 shows "
                   "each item separately.") + 1.6
    else:
        # One panel, so no panel heading: a second bold line here would only restate the
        # title.  Panels B and C are NOT repeated from S7 - they are the same numbers
        # either way, and printing them twice invites a reader to look for a difference
        # that does not exist.
        p.title("Agreement between the two reviewers, item by item",
                "Supplementary Figure S10A pools the instrument's questions into concepts. This is the "
                "same statistic for each of its %d items, so a question put to more than one study task "
                "appears once per task." % N_TOTAL)
        p.ax.add_line(plt.Line2D([LAB_X - 6.0, W - 1.0], [TOP - 3.0] * 2, color=RULE, lw=0.5, zorder=2))
        y = p.notes(TOP, lead +
                    "C, D and P mark the causal, descriptive and predictive item sets.") + 1.6
    A_H = ROW * len(items)
    for g in (0.0, 0.25, 0.5, 0.75, 1.0):
        p.ax.add_line(plt.Line2D([x_of(g)] * 2, [y + 2.2, y + 2.2 + A_H], color=GRID_C, lw=0.4, zorder=1))
        p.T(x_of(g), y, "%.2f" % g, T_SMALL, MUT, ha="center")
    p.T(LAB_X, y, "Instrument " + UNIT, T_SMALL, MUT, "bold")
    if COLLAPSED:
        p.T(COL_TASK, y, "tasks", T_SMALL, MUT, "bold", ha="right")
    p.T(COL_N, y, "n", T_SMALL, MUT, "bold", ha="right")
    p.T(COL_P0, y, "$p_0$", T_SMALL, MUT, "bold", ha="right")
    p.T(COL_AC, y, "$AC_1$", T_SMALL, MUT, "bold", ha="right")
    top = y + 2.2
    for i, r in enumerate(items):
        yc = top + ROW * (i + 0.5)
        col = DOM[r["_dom"]]
        if i % 2 == 0:
            p.ax.add_patch(Rectangle((LAB_X - 5.2, top + ROW * i), W - LAB_X + 4.8, ROW,
                                     fc="#f6f7f8", ec="none", zorder=1))
        if COLLAPSED:
            p.T(COL_TASK, yc, r["_tag"], T_SMALL, MUT, ha="right", va="center")
        else:
            p.T(LAB_X - 1.4, yc, r["_tag"], T_SMALL, MUT, "bold", ha="right", va="center")
        p.labels.append(p.T(LAB_X, yc, r["label"], T_SMALL, INK, va="center"))
        p.ax.add_line(plt.Line2D([x_of(r["_lo"]), x_of(r["_hi"])], [yc, yc], color=col,
                                 lw=0.7, alpha=0.55, zorder=3))
        if r["_ac1"] is not None:
            p.ax.plot([x_of(r["_ac1"])], [yc], marker="D", ms=2.1, mfc="white",
                      mec=col, mew=0.6, zorder=4)
        p.ax.plot([x_of(r["_p0"])], [yc], marker="o", ms=2.6, mfc=col, mec=col, zorder=5)
        p.T(COL_N, yc, r["n_both"], T_SMALL, MUT, ha="right", va="center")
        p.T(COL_P0, yc, "%.2f" % r["_p0"], T_SMALL, INK, ha="right", va="center")
        p.T(COL_AC, yc, "%.2f" % r["_ac1"] if r["_ac1"] is not None else "–",
            T_SMALL, MUT, ha="right", va="center")
    y = p.legend(top + A_H + 3.0, [(d, c, "dot") for d, c in DOM.items()])
    y = p.notes(y + 2.2, [
        "Ranked on $p_0$, not on κ: where one answer category dominates, κ reports the answer distribution "
        "rather than the difficulty (Byrt 1993), so $AC_1$ is given as the chance-corrected reading instead.",
        "$p_0$ excludes the %s applicability disputes, in which one reviewer answered and the other judged "
        "the item not to apply: those follow from an upstream disagreement about the shape of the study, "
        "not about its quality. %d of the instrument's %d %s are omitted for the same reason: fewer than "
        "20 cells were answered by both reviewers, %d of their disputes being about applicability. "
        "Disagreement rate by task: %s."
        % (f(APPLIC), N_OMIT, N_TOTAL, UNIT_PL, OMIT_APPLIC,
           ", ".join("%s %.1f%%" % (t.lower(), q) for t, q in BYTASK)),
    ])

    if not COLLAPSED:                       # S8 is panel A alone
        p.bottom = y
        return p

    y = p.head(y + GAP, "B", "The two adjudicators, ruling independently",
               "Phase I: each adjudicator saw both reviewers' answers, blinded to reviewer identity, and "
               "ruled without seeing the other's call.") + 1.6
    for who, (n, u1, u2, ov) in ADJ:
        y = p.stacked(y, n, [(u1, VERD["first"], False), (u2, VERD["second"], False),
                             (ov, VERD["over"], False)], who, "n = " + f(n), bold=True) + 1.8
    y = p.legend(y + 1.2, [("Upheld the first reviewer's answer", VERD["first"], "swatch"),
                           ("Upheld the second reviewer's answer", VERD["second"], "swatch"),
                           ("Rejected both, and wrote a third answer", VERD["over"], "swatch")])
    y = p.notes(y + 2.2,
                "%s rejected both reviewers on %.1f%% of the cells ruled, against %.1f%% for %s, a "
                "stable difference in how readily each was willing to reject both answers outright."
                % (ADJ[0][0], pc(ADJ[0][1][3], ADJ[0][1][0]),
                   pc(ADJ[1][1][3], ADJ[1][1][0]), ADJ[1][0]))

    y = p.head(y + GAP, "C", "What the joint sitting settled on",
               "Phase II: the %s cells where both adjudicators ruled in phase I and their rulings "
               "differed, resolved face to face." % f(len(both_ruled))) + 1.6
    y = p.stacked(y, sum(P2_BOTH), [(P2_BOTH[0], JOINT["ta"], False), (P2_BOTH[1], JOINT["ya"], False),
                                    (P2_BOTH[2], JOINT["new"], True)],
                  "settled on", "n = " + f(sum(P2_BOTH)))
    y = p.legend(y + 3.0, [("%s's phase-I call" % ADJ[0][0], JOINT["ta"], "swatch"),
                           ("%s's phase-I call" % ADJ[1][0], JOINT["ya"], "swatch"),
                           ("neither: a new answer", JOINT["new"], "swatch")])
    y = p.notes(y + 2.2,
                "Joint discussion converged on one adjudicator's prior call %.1f times as often as on the "
                "other's. Over all %s cells taken to phase II (including the %d where only one adjudicator "
                "had recorded a call, which makes agreement with that adjudicator partly structural), the "
                "split is %s / %s / %s, or %.1f%% either way. The asymmetry is a real feature of the "
                "record; whether it reflects persuasion, differing confidence, or a genuine difference in "
                "accuracy cannot be determined from these data."
                % (P2_BOTH[0] / float(P2_BOTH[1]), f(len(p2cells)), len(one_ruled),
                   f(P2_ALL[0]), f(P2_ALL[1]), f(P2_ALL[2]), pc(P2_ALL[0], P2_ALL[0] + P2_ALL[1])))
    p.bottom = y

    return p


# =============================================================================
# Write, then check what nothing else checks
# =============================================================================
from PIL import Image
Image.MAX_IMAGE_PIXELS = None
from pypdf import PdfReader


def emit(p, H, stem, tag):
    base = os.path.join(OUTDIR, stem)
    p.fig.canvas.draw()
    rend = p.fig.canvas.get_renderer()
    mm = lambda px: px / p.fig.dpi * 25.4
    over = [(t.get_text(), round(mm(t.get_window_extent(rend).width), 1))
            for t in p.labels if mm(t.get_window_extent(rend).width) > LAB_W]
    assert not over, over                                 # item labels inside their column
    assert min(p.sizes) >= MIN_PT, min(p.sizes)           # journal type floor
    assert H <= 245.0, H                                  # fits a page with margins
    # nothing off the page: matplotlib will happily draw text past the canvas edge and
    # neither the PDF writer nor the TIFF check would complain, so check it here
    spill, boxes = [], []
    for t in p.ax.texts:
        b = t.get_window_extent(rend)
        x0, x1 = mm(b.x0), mm(b.x1)
        y0, y1 = mm(b.y0), mm(b.y1)                       # display y is bottom-up
        if x0 < -0.2 or x1 > W + 0.2 or y0 < -0.2 or y1 > H + 0.2:
            spill.append((round(x0, 1), round(x1, 1), t.get_text()[:60]))
        boxes.append((y0, y1, x0, x1, t.get_text()))
    assert not spill, spill
    # Two labels touching is the error a rendered preview hides best: "1.00" and a
    # column header abutting read as "1.00tasks", and nothing warns.  Test the drawn
    # rectangles against each other directly - grouping them into rows first is where
    # this check goes wrong.  Boxes are shrunk 0.2 mm a side so that glyph bounding
    # boxes which merely graze on adjacent rows are not reported.
    clash = []
    for i, (ya0, ya1, xa0, xa1, sa) in enumerate(boxes):
        for yb0, yb1, xb0, xb1, sb in boxes[i + 1:]:
            if (xa0 < xb1 - 0.2 and xa1 > xb0 + 0.2
                    and ya0 < yb1 - 0.2 and ya1 > yb0 + 0.2):
                clash.append((sa[:30], sb[:30], round(xa1, 1), round(xb0, 1)))
    assert not clash, clash[:6]

    p.fig.savefig(base + ".pdf", format="pdf", facecolor="white")
    p.fig.savefig(base + ".png", dpi=600, facecolor="white")
    im = Image.open(base + ".png")
    rgb = Image.new("RGB", im.size, "white")
    rgb.paste(im, mask=im.split()[3] if im.mode == "RGBA" else None)
    rgb.save(base + ".tif", format="TIFF", compression="tiff_lzw", dpi=(600, 600))
    im.close(); plt.close(p.fig)

    for _k, _v in PdfReader(base + ".pdf").pages[0]["/Resources"]["/Font"].items():
        fo = _v.get_object(); df = fo.get("/DescendantFonts")
        d = df[0].get_object() if df else fo
        desc = d.get("/FontDescriptor")
        assert d.get("/Subtype") != "/Type3" and desc and any(
            x in desc for x in ("/FontFile", "/FontFile2", "/FontFile3")), fo.get("/BaseFont")
        assert "Arial" in str(fo.get("/BaseFont")), fo.get("/BaseFont")   # incl. mathtext runs
    t = Image.open(base + ".tif")
    assert t.mode == "RGB" and t.tag_v2[259] == 5 and t.info["dpi"] == (600.0, 600.0)
    t.close()
    print("  %s  %.0f x %.0f mm, smallest type %.1f pt" % (tag, W, H, min(p.sizes)))
    for ext in ("pdf", "tif", "png"):
        print("      %-56s %8.1f KB" % (base + "." + ext, os.path.getsize(base + "." + ext) / 1024))


for _collapsed, _tag in ((True, "S7"), (False, "S8")):
    configure(_collapsed)
    pg, HH = two_pass(supplement_page)
    emit(pg, HH, STEM, _tag)
    print("      A  %d of %d %s%s, p0 %.3f to %.3f; %s applicability disputes excluded, %d on the "
          "%d omitted" % (len(items), N_TOTAL, UNIT_PL, " (pooled across tasks)" if _collapsed else "",
                          float(items[0]["p0"]), float(items[-1]["p0"]), f(APPLIC), OMIT_APPLIC, N_OMIT))

print("  S7 panels B and C, which S8 deliberately does not repeat:")
print("      B  %s %s cells, rejected both %.1f%%; %s %s cells, %.1f%%"
      % (ADJ[0][0], f(ADJ[0][1][0]), pc(ADJ[0][1][3], ADJ[0][1][0]),
         ADJ[1][0], f(ADJ[1][1][0]), pc(ADJ[1][1][3], ADJ[1][1][0])))
print("      C  %s / %s / %s of the %s both-ruled  (all %s phase-II cells: %s / %s / %s)"
      % (f(P2_BOTH[0]), f(P2_BOTH[1]), f(P2_BOTH[2]), f(sum(P2_BOTH)), f(sum(P2_ALL)),
         f(P2_ALL[0]), f(P2_ALL[1]), f(P2_ALL[2])))

# -*- coding: utf-8 -*-
"""Remove em dashes from the text the figures DRAW (TSA, 2026-08-26).

    python code/figures/08_26_2026_figure_dash_pass.py --dry | --apply

The manuscript, the supplementary methods and the legends were done in the style pass. This
does the other place a reader meets our prose: the sub-lines, labels and footnotes set inside
the figures themselves.

⚠ ONLY DRAWN STRINGS.  Comments and docstrings keep their dashes - they are notes to whoever
maintains the script, not text a journal receives, and rewriting them would bury the real
change in noise. The list below was built by parsing each generator and walking its string
constants with the docstrings excluded, so nothing that prints is missed and nothing that
does not print is touched.

⚠ `@@` STANDS FOR THE EM DASH in the patterns below, and for nothing else. The first version
of this script used `%s` as that placeholder and substituted it everywhere, which corrupted
every pattern containing a real `%s` or `%d` format specifier - twelve of the thirty-one
replacements silently failed to match. The figures' own format strings are dense with them.

⚠ EVERY REPLACEMENT SHORTENS OR EQUALS the original, which is the direction that cannot break
these layouts: the figures assert a type floor, no text off the canvas, and no two text boxes
touching, and they wrap prose through para(..., nlines=N) with the line count as a contract.
Shorter text can only reduce width and line count. The one exception is the S3 "not ranked"
chip, where a one-character marker becomes "n/a"; that label's width is measured before its
swatch is placed, so the chip grows with it.
"""
import os, io, sys

D = r"."
os.chdir(D)

REPL = {
"code/figures/08_21_2026_prisma_print_figure.py": [
 ("Not screened @@ target met", "Not screened: target met"),
 ("Recusal reasons @@ conflict of interest", "Recusal reasons: conflict of interest"),
 ("disagreed, not adjudicated @@ language model", "disagreed, not adjudicated: language model"),
 ("one screener gave a reason @@ model as second", "one screener gave a reason: model as second"),
 ("no screener reason @@ model determined it", "no screener reason: model determined it"),
],
"code/figures/08_21_2026_adjudication_print_figure.py": [
 ("Never asked @@ the instrument branches", "Never asked: the instrument branches"),
 ("Assessed @@ at least one reviewer answered", "Assessed: at least one reviewer answered"),
 ("conflicting answers @@ both answered, the answers differ",
  "conflicting answers: both answered, the answers differ"),
 ("applicability @@ one answered, the other judged the item not to apply",
  "applicability: one answered, the other judged the item not to apply"),
 ("Phase I @@ TSA and YA ruled independently", "Phase I: TSA and YA ruled independently"),
 ("Phase II @@ joint resolution", "Phase II: joint resolution"),
 ("Not applicable @@ no ruling required", "Not applicable: no ruling required"),
 ("Overrode both @@ a third answer", "Overrode both: a third answer"),
 ("rulings @@ every applicable cell", "rulings: every applicable cell"),
],
"code/figures/08_22_2026_quality_scoring_print_figure.py": [
 ("reporting only @@ never a validity flaw", "reporting only: never a validity flaw"),
 ("judged on two axes @@ whether the study reported enough",
  "judged on two axes: whether the study reported enough"),
 ("index panels are means @@ the two task means", "index panels are means: the two task means"),
 ("weighted by severity @@ density", "weighted by severity: density"),
 ("count per paper @@ too opaque to judge", "count per paper: too opaque to judge"),
],
"code/figures/08_26_2026_fig6_indices_figure.py": [
 ("confidence intervals @@ ", "confidence intervals; "),
 ("associational and unadjusted @@ ", "associational and unadjusted: "),
],
"code/figures/08_25_2026_S1_author_countries_figure.py": [
 ("By country @@ all ", "By country: all "),
 ("By country @@ the ", "By country: the "),
 ("%s @@ continued", "%s (continued)"),
 ("%s @@ %s positions, %d countries, %d papers", "%s: %s positions, %d countries, %d papers"),
],
"code/figures/08_25_2026_S2_saudi_institutions_figure.py": [
 ("Across the Kingdom @@ positions by city", "Across the Kingdom: positions by city"),
 ("Concentration @@ cumulative share", "Concentration: cumulative share"),
 ("grouped within type @@ all ", "grouped within type: all "),
 ("Every institution, ranked @@ all ", "Every institution, ranked: all "),
 ("%s @@ %d positions, %d inst., %d papers", "%s: %d positions, %d inst., %d papers"),
 ("%s @@ continued", "%s (continued)"),
],
"code/figures/08_25_2026_S3_journal_landscape_figure.py": [
 ("Delisted from WoS @@ no 2022 edition entry", "Delisted from WoS: no 2022 edition entry"),
 ("Emerging Sources index in 2022 @@ a JIF, but no quartile",
  "Emerging Sources index in 2022: a JIF, but no quartile"),
 ("Both quartiles are 2022 editions @@ SCImago SJR",
  "Both quartiles are 2022 editions: SCImago SJR"),
 # ⚠ line-local patterns: these literals are split across source lines by implicit string
 # concatenation, so a pattern spanning the join can never match the file.
 ("@@ = that ranking does not place the journal",
  "n/a = that ranking does not place the journal"),
 ("keyed in panel A; @@ = that ranking does not place it",
  "keyed in panel A; n/a = that ranking does not place it"),
 ("largest journals @@ bar colour: SJR quartile",
  "largest journals, bar colour: SJR quartile"),
 ("of the papers @@ too many to name", "of the papers: too many to name"),
 ("Every journal, largest first @@ all ", "Every journal, largest first: all "),
 ('"@@" if t == "Not ranked" else t', '"n/a" if t == "Not ranked" else t'),
],
"code/figures/08_22_2026_adjudication_supplement_figure.py": [
 ("for %s @@ a ", "for %s, a "),
 ("taken to phase II @@ including the", "taken to phase II (including the"),
 ("partly structural @@ the ", "partly structural), the "),
 ("omitted for the same reason @@ fewer than ",
  "omitted for the same reason: fewer than "),
],
}

if __name__ == "__main__":
    apply = "--apply" in sys.argv
    total, miss = 0, []
    for f, pairs in REPL.items():
        t = io.open(f, encoding="utf-8").read()
        before = t
        for old, new in pairs:
            hit = False
            for dash in ("\u2014", "\\u2014"):
                cand = old.replace("@@", dash)
                if cand in t:
                    t = t.replace(cand, new)
                    hit, total = True, total + 1
                    break
            if not hit:
                miss.append((f, old[:66]))
        if apply and t != before:
            io.open(f, "w", encoding="utf-8").write(t)
    print("%d replacement%s %s" % (total, "" if total == 1 else "s",
                                   "applied" if apply else "would apply (dry run)"))
    if miss:
        print("\n  !! %d did not match:" % len(miss))
        for f, o in miss:
            print("     %-50s %s" % (f.split("/")[-1], o))

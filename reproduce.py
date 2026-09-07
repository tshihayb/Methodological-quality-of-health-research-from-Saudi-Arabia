"""
Reproduce every figure and table in the manuscript and supplement.

    python reproduce.py            run everything
    python reproduce.py --list     show the plan without running it

ORDER MATTERS, which is why this exists rather than a loop over the scripts.
The displays are not independent: the scorer must run before anything that reads
a score, the stratified analysis before Figure 6, and several supplementary
figures read intermediate tables that an earlier script writes. Running the
scripts alphabetically, as an obvious runner would, fails on about a third of
them for no reason but sequence.

Only canonical displays are here. The repository also holds variant and
exploratory scripts, candidate sweeps and contact sheets kept from the analysis;
none of them produces anything the paper ships, and they are not run.
"""
import os, shutil, subprocess, sys, time

R = r"C:\Program Files\R\R-4.5.2\bin\x64\Rscript.exe"

# (stage, script, what it produces)  in dependency order
PLAN = [
    ("prepare", "code/scoring/07_30_2026_score_dataset.R",
     "item, domain and study-level scores"),
    ("prepare", "code/scoring/07_30_2026_secondary_scoring.R",
     "secondary domain counts"),
    ("prepare", "code/scoring/07_30_2026_stratified_analysis.R",
     "stratified summary, domains and spread"),
    ("prepare", "code/tables/08_22_2026_scoring_framework.py",
     "the scoring-framework table Figure 4 and Table S2 both read"),

    # The sensitivity analyses are not displays themselves, but Figures S10, S11,
    # S13 and S14 all read tables they write. Omitting them made three figures
    # fail on FileNotFoundError, which reads like a broken repository rather than
    # a missing step. They are slow; that is why they sit in `prepare`.
    ("prepare", "code/scoring/08_19_2026_agreement_sensitivity_tier1.R",
     "agreement collapsed by concept, and the difficulty ranking"),
    # This one first: both the tipping point and the perturbed indices read the
    # flag-level table it writes. Omitting it made four scripts fail on the same
    # missing file, which looked like four problems and was one.
    ("prepare", "code/scoring/08_19_2026_calibration_flag_level_epsilon.R",
     "calibration flag levels by domain"),
    ("prepare", "code/scoring/08_19_2026_calibration_concordant_error.R",
     "concordant-error parameters"),
    ("prepare", "code/scoring/08_19_2026_tipping_point.R",
     "tipping points and imputed parameters"),
    ("prepare", "code/scoring/08_29_2026_bias_analysis_by_task.R",
     "bias analysis and tipping points by task"),
    ("prepare", "code/scoring/08_29_2026_stratified_indices_perturbed.R",
     "perturbed stratified indices and spreads"),

    ("main", "code/figures/08_21_2026_prisma_print_figure.py",        "Figure 1, PRISMA"),
    ("main", "code/figures/calibration/Calibration_data_final.R",     "calibration data prep"),
    ("main", "code/figures/calibration/Calibration figures_combined.R", "Figure 2, calibration"),
    ("main", "code/figures/08_21_2026_adjudication_print_figure.py",  "Figure 3, adjudication"),
    ("main", "code/figures/08_22_2026_scoring_framework_figure.py",   "Figure 4, scoring framework"),
    ("main", "code/figures/08_22_2026_quality_scoring_print_figure.py", "Figure 5, quality scoring"),
    ("main", "code/figures/08_26_2026_fig6_indices_figure.py",        "Figure 6, indices by group"),
    ("main", "code/tables/08_22_2026_table1_word.py",                 "Table 1, study characteristics"),
    ("main", "code/tables/08_22_2026_table2_word.py",                 "Table 2, item distribution"),

    ("supp", "code/figures/08_26_2026_S4_outcomes_figure.py",         "Figure S1, outcomes"),
    ("supp", "code/figures/08_25_2026_S1_author_countries_figure.py", "Figure S2, author countries"),
    ("supp", "code/figures/08_25_2026_S2_saudi_institutions_figure.py", "Figure S3, Saudi institutions"),
    ("supp", "code/figures/08_25_2026_S3_journal_landscape_figure.py", "Figure S4, journal landscape"),
    ("supp", "code/figures/calibration/Calibration figures_per_reviewer.R", "Figure S5, calibration matrix"),
    ("supp", "code/figures/calibration/08_21_2026_all_percent_tool_order.R", "Figure S6, all percent"),
    ("supp", "code/figures/calibration/08_21_2026_S5a_all_percent_heatmap.R", "Figure S7, percent matrix"),
    ("supp", "code/figures/calibration/08_28_2026_all_ac1_tool_order.R", "Figure S8, all AC1"),
    ("supp", "code/figures/calibration/08_28_2026_ac1_heatmap.R",     "Figure S9, AC1 matrix"),
    ("supp", "code/figures/08_22_2026_adjudication_supplement_figure.py",
     "Figures S10 and S11, agreement and adjudication"),
    ("supp", "code/figures/08_28_2026_S12_standardised_indices_figure.py", "Figure S12, standardised indices"),
    ("supp", "code/figures/08_29_2026_S13_misclassification_overall_figure.py",
     "Figure S13, misclassification overall"),
    ("supp", "code/figures/08_29_2026_S14_misclassification_stratified_figure.py",
     "Figure S14, misclassification stratified"),
    ("supp", "code/tables/09_01_2026_reviewer_load_table.py",         "Table S1, reviewer load"),
    ("supp", "code/tables/08_22_2026_scoring_framework_print_table.py", "Table S2, the instrument"),
    # ⚠ This was listed as unbuildable, on the grounds that the caveat register
    # is curated rather than computed. It is computed: the script derives all
    # six caveats and their 19 studies from the wide dataset, which ships. The
    # public build reproduces the private workbook cell for cell, differing only
    # where an identifier becomes its surrogate, and in the order of the id
    # lists, because a surrogate does not sort where the identifier did.
    # ⚠ An earlier version of this comment gave the two ids to illustrate that,
    # which put a real study identifier in a file the builder does not scrub.
    # reproduce.py, the README and tools/ are hand-written and only gate 1 sees
    # them; it caught this.
    ("supp", "code/pipeline/08_12_2026_build_caveats_register.py",
     "Table S3, caveat register"),
]

# Displays that cannot be rebuilt here, and why. Stated rather than silently
# absent, because a missing figure with no explanation reads as a broken repo.
#
# ⚠ EMPTY, AS OF 2026-09-02, AND THAT TOOK THREE CORRECTIONS. Table S3 was
# listed here as a curated register; it is computed, from data that ships.
# Figure S2 was listed as needing author names; it needs four aggregates.
# Figure S4 was listed as needing per-paper journal attributes, and it does, but
# it never needs to know WHICH paper: unkeyed and shuffled, those rows carry no
# linkage and every count over them is unchanged. All three now build here, and
# S2, S3, S4 and Table S3 were each checked byte for byte against the private
# build. Anything added to this list should be doubted the same way.
BLOCKED = []

# ---------------------------------------------------------------------------
# The 26 displays the paper ships, under the names and in the formats the
# submission package uses. Figures are PNG; the two Results tables are Word;
# Supplementary Tables S1 and S3 are workbooks; Supplementary Table S2 is the
# instrument rendered as two page images.
#
# ⚠ The name on the left is what a reader of the paper is looking for, and the
# path on the right is what this repository actually writes. Without the map
# they are unrelatable: `08_26_2026_S4_outcomes_designC.png` is Supplementary
# Figure S1, and nothing about the filename says so.
DISPLAYS = [
    ("Figure_1_PRISMA.png", "outputs/figures/08_21_2026_PRISMA_flow.png"),
    ("Figure_2_calibration.png", "outputs/figures/Calibration_combined_excl_R3.png"),
    ("Figure_3_adjudication_process.png", "outputs/figures/08_21_2026_adjudication_flow.png"),
    ("Figure_4_scoring_framework.png", "outputs/figures/08_22_2026_scoring_framework.png"),
    ("Figure_5_quality_scoring.png", "outputs/figures/08_22_2026_quality_scoring.png"),
    ("Figure_6_quality_indices_by_group.png", "outputs/figures/08_26_2026_fig6_indices.png"),
    ("Table_1_study_characteristics.docx",
     "outputs/tables/08_22_2026_table1_study_characteristics.docx"),
    ("Table_2_item_distribution.docx",
     "outputs/tables/08_22_2026_table2_item_distribution.docx"),
    ("Supplementary_Figure_S1_outcomes.png",
     "outputs/figures/08_26_2026_S4_outcomes_designC.png"),
    ("Supplementary_Figure_S2_author_countries.png",
     "outputs/figures/08_25_2026_S1_author_countries_designB.png"),
    ("Supplementary_Figure_S3_saudi_institutions.png",
     "outputs/figures/08_25_2026_S2_saudi_institutions_designC.png"),
    ("Supplementary_Figure_S4_journal_landscape.png",
     "outputs/figures/08_25_2026_S3_journal_landscape_designE.png"),
    ("Supplementary_Figure_S5_calibration_matrix.png",
     "outputs/figures/Calibration_perreviewer_heatmap_excl_R3.png"),
    ("Supplementary_Figure_S6_calibration_all_percent.png",
     "outputs/figures/08_21_2026_calibration_all_percent_tool_order.png"),
    ("Supplementary_Figure_S7_calibration_matrix_all_percent.png",
     "outputs/figures/08_21_2026_S5a_calibration_matrix_all_percent.png"),
    ("Supplementary_Figure_S8_calibration_all_ac1.png",
     "outputs/figures/08_28_2026_calibration_all_ac1_tool_order.png"),
    ("Supplementary_Figure_S9_calibration_matrix_all_ac1.png",
     "outputs/figures/08_28_2026_calibration_matrix_all_ac1.png"),
    ("Supplementary_Figure_S10_agreement_and_adjudication.png",
     "outputs/figures/08_22_2026_adjudication_supplement.png"),
    ("Supplementary_Figure_S11_agreement_by_item.png",
     "outputs/figures/08_22_2026_agreement_by_item.png"),
    ("Supplementary_Figure_S12_standardised_indices.png",
     "outputs/figures/08_28_2026_S12_standardised_indices.png"),
    ("Supplementary_Figure_S13_misclassification_overall.png",
     "outputs/figures/08_29_2026_S13_misclassification_overall.png"),
    ("Supplementary_Figure_S14_misclassification_stratified.png",
     "outputs/figures/08_29_2026_S14_misclassification_stratified.png"),
    ("Supplementary_Table_S1_reviewer_load.xlsx",
     "outputs/tables/09_01_2026_reviewer_load.xlsx"),
    ("Supplementary_Table_S2_instrument_p1.png",
     "outputs/tables/08_22_2026_instrument_table_p1.png"),
    ("Supplementary_Table_S2_instrument_p2.png",
     "outputs/tables/08_22_2026_instrument_table_p2.png"),
    ("Supplementary_Table_S3_caveat_register.xlsx",
     "outputs/tables/08_12_2026_known_data_caveats.xlsx"),
]


def collect_displays():
    """Gather the 26 shipped displays into displays/ under the paper's names."""
    dest = "displays"
    if os.path.isdir(dest):
        for f in os.listdir(dest):
            os.remove(os.path.join(dest, f))
    os.makedirs(dest, exist_ok=True)
    got, missing = 0, []
    for name, src in DISPLAYS:
        if os.path.exists(src):
            shutil.copy2(src, os.path.join(dest, name))
            got += 1
        else:
            missing.append((name, src))
    print("\ndisplays/  %d of %d collected under the names the paper uses"
          % (got, len(DISPLAYS)))
    for name, src in missing:
        print("   MISSING  %-52s expected %s" % (name[:52], src))
    return missing

# Evidence that the prepare stage has already run in this tree, checked before
# --reuse-prepare is honoured.
SEED_EVIDENCE = ["outputs/tables/08_19_2026_tipping_point_thresholds.csv",
                 "outputs/tables/08_29_2026_stratified_indices_perturbed.csv",
                 "data/scoring/07_30_2026_stratified_summary.csv"]


def main():
    if "--list" in sys.argv:
        for stage in ("prepare", "main", "supp"):
            print("\n%s" % stage.upper())
            for s, f, what in PLAN:
                if s == stage:
                    print("   %-62s %s" % (f, what))
        print("\nNOT REBUILT HERE")
        for name, why in BLOCKED:
            print("   %-30s %s" % (name, why))
        if not BLOCKED:
            print("   nothing: every display in the paper is rebuilt from what "
                  "this repository ships")
        return 0

    for d in ("outputs/figures", "outputs/tables", "outputs/reports"):
        os.makedirs(d, exist_ok=True)

    # ⚠ FOR ITERATION ONLY, and it says so out loud. The prepare stage is
    # dominated by 08_19_2026_tipping_point.R, which is about 55 minutes, and
    # its outputs do not change when a figure script does. Re-running it after
    # every small fix turned an afternoon of edits into a day of waiting. A run
    # that is meant to VERIFY the repository must not pass this flag.
    reuse = "--reuse-prepare" in sys.argv
    if reuse:
        missing = [t for t in SEED_EVIDENCE if not os.path.exists(t)]
        if missing:
            print("--reuse-prepare ignored: the prepare stage has not run here "
                  "(%s absent)" % missing[0])
            reuse = False
        else:
            print("--reuse-prepare: skipping the prepare stage and reusing its "
                  "outputs.\n  THIS IS NOT A VERIFICATION RUN. Omit the flag "
                  "for that.\n")

    ok, bad = 0, []
    for stage, f, what in PLAN:
        if reuse and stage == "prepare":
            print("  reused   %-58s %s" % (f.split("/")[-1][:58], what))
            continue
        if not os.path.exists(f):
            bad.append((f, "script not present"))
            print("  MISSING  %-58s %s" % (f.split("/")[-1][:58], what))
            continue
        cmd = [R, f] if f.lower().endswith(".r") else [sys.executable, f]
        t0 = time.time()
        # ⚠ UTF-8 for the child. Several scripts print a "≥" in their summary
        # line, and on Windows a redirected Python process defaults to the
        # ANSI codepage, where that character raises UnicodeEncodeError and the
        # script dies AFTER doing its work. Table 1 failed that way on a machine
        # where it had already run correctly at an interactive prompt.
        env = dict(os.environ, PYTHONIOENCODING="utf-8")
        r = subprocess.run(cmd, capture_output=True, text=True, env=env)
        dt = time.time() - t0
        if r.returncode == 0:
            ok += 1
            print("  ok       %-58s %5.1fs  %s" % (f.split("/")[-1][:58], dt, what))
        else:
            err = (r.stderr or r.stdout or "").strip().splitlines()
            why = next((l for l in err if "Error" in l or "No such file" in l), "")[:80]
            bad.append((f, why))
            print("  FAILED   %-58s %s" % (f.split("/")[-1][:58], why))

    print("\n%d of %d ran" % (ok, len(PLAN)))
    if bad:
        print("\nfailed:")
        for f, why in bad:
            print("   %-58s %s" % (f, why))
    if BLOCKED:
        print("\nnot rebuilt here:")
        for name, why in BLOCKED:
            print("   %-30s %s" % (name, why[:70]))
    else:
        print("\nevery display in the paper is rebuilt from what this "
              "repository ships")
    missing = collect_displays()
    return 1 if (bad or missing) else 0


if __name__ == "__main__":
    sys.exit(main())

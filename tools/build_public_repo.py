"""
Build the public repository: the ANALYSIS LAYER of the study, de-identified.

WHY THIS WAS REWRITTEN ON 2026-09-01
The previous builder published everything the pipeline touched and removed what
it recognised as identifying. That is a denylist, and a denylist fails silently:
twelve leak classes were found in it, each after the release gate had already
passed. The last three were not patterns anyone could have listed in advance.

  * a column called `corr_author` holding 366 corresponding-author surnames
  * 116 institutions by name, 56 of them carrying exactly one paper, printed in
    a figure PNG where no text scanner could ever see them
  * the journal fingerprint: publisher country, exact SJR, SCImago coverage span,
    subfield, topic and host organisation. The journal NAME was dropped and the
    journal was still recoverable, because SCImago is public. On that tuple alone
    304 of the 385 studies were unique; with institution sector and author
    countries added, 383 of 385 were.

So the default is inverted. Nothing ships unless it is named here, and what
ships is the layer the analysis actually consumes rather than the layer the
study collected. That is not a compromise: on the attributes the analysis needs
(task, design, sector, quartile band) the smallest group of studies sharing a
profile is 17, and no study is unique. Reproducibility and non-identifiability
were never in tension; the source metadata travelling alongside was the problem.

THREE RULES, IN THE ORDER THEY APPLY

  1 FILE ALLOWLIST     only the files the reproduction reads (SHIP below)
  2 COLUMN ALLOWLIST   within a file, only the columns some shipped script names
  3 k = 5              no published category may carry fewer than 5 papers, and
                       no aggregate row may count fewer than 5. Rarer values are
                       merged into an explicit "Other" rather than deleted, so
                       totals still reconcile.

⚠ RULE 3 APPLIES TO QUASI-IDENTIFIERS ONLY: attributes a reader can also observe
from PubMed, SCImago or the paper's own front matter. It must NEVER be applied to
item responses or derived scores. A rare answer option is a finding, not a leak,
and suppressing it would change the study's results. `kind` below draws that line.

WHAT NO LONGER SHIPS
The screening ledgers, assignment workbooks, author-position files, journal
landscape tables and adjudication worklists. tools/ writes MANIFEST_WITHHELD.md
naming each one and why, so their absence is a statement rather than a gap.

    python public-repo/tools/build_public_repo.py
"""
import csv, io, json, os, random, re, shutil, sys
from collections import Counter, OrderedDict

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
PUB = os.path.join(ROOT, "public-repo")
MAP_OUT = os.path.join(ROOT, "private", "public_repo_id_map_DO_NOT_COMMIT.json")
SEED = 20260901
K = 5                                  # minimum papers behind any published category

# ---------------------------------------------------------------------------
# 1. THE FILE ALLOWLIST
#
# kind:
#   items    instrument responses and reviewer answers. Closed vocabulary, no
#            bibliographic metadata. Ships whole, minus `drop`.
#   derived  computed by the study: scores, agreement statistics, sensitivity
#            tables. Not observable outside the dataset, so not a linkage key.
#   qi       carries something a reader can also see elsewhere: a journal, an
#            institution, a city, a count of authors. Allowlisted and collapsed.
#
# `keep`             column allowlist (qi files only; absent means every column)
# `collapse_values`  {column: weight-column} - a value behind fewer than K papers
#                    is rewritten to "Other ...". Row count is unchanged.
# `collapse_rows`    the same test on a table with ONE ROW PER CATEGORY: the rare
#                    rows are summed into a single Other row instead, and it
#                    carries n_categories so a figure can say how many it stands
#                    for without naming any of them.
# A weight-column of None means count distinct papers (PMID) if the file has
# them, otherwise count rows.
# ---------------------------------------------------------------------------
SHIP = OrderedDict([
    # ---- the scorer's own inputs and outputs ------------------------------
    ("data/analysis/07_23_2026_ANALYSIS_DATASET_wide.csv", dict(kind="items",
     drop=["pct_saudi_authors", "pct_saudi_cat3", "pct_saudi_cat4",
           "n_authors", "n_saudi_authors", "pct_saudi_reliable"])),
    # ⚠ The LONG dataset as well as the wide one. Table 2 is built from it, and
    # the column-demand scan missed it because `_gen_table2.py` is loaded through
    # importlib rather than imported, so scanning the canonical scripts' own text
    # never saw the path. Two displays failed on that.
    ("data/analysis/07_23_2026_ANALYSIS_DATASET_long.csv", dict(kind="items")),
    ("data/analysis/08_25_2026_funding_ADJUDICATED_385.csv", dict(kind="items",
     drop=["adjudication_reason", "adjudication_rule"])),
    ("data/scoring/07_30_2026_scored_items_long.csv", dict(kind="derived")),
    ("data/scoring/07_30_2026_scored_domain.csv", dict(kind="derived")),
    ("data/scoring/07_30_2026_scored_study.csv", dict(kind="derived")),
    ("data/scoring/07_30_2026_secondary_domain_counts.csv", dict(kind="derived")),
    ("data/scoring/07_30_2026_stratified_domains.csv", dict(kind="derived")),
    ("data/scoring/07_30_2026_stratified_paper_level.csv", dict(kind="derived")),
    ("data/scoring/07_30_2026_stratified_spread.csv", dict(kind="derived")),
    ("data/scoring/07_30_2026_stratified_summary.csv", dict(kind="derived")),
    # team_cat is banded (1-2 / 3-10 / 11+); n_auth is the raw count and is a
    # quasi-identifier, so it goes even though it is one number.
    ("data/scoring/07_30_2026_team_size_385.csv", dict(kind="qi",
     keep=["PMID", "team_cat"])),

    # ---- outcomes: the CATEGORY ships, the measured outcome does not ------
    # ⚠ `outcome` holds what each paper measured ("Crestal bone loss (CBL)").
    # It is unique per paper and it is a search query. The Figure S1 script
    # never reads it; it counts `category`, `domain`, `Study_Type`, `source`.
    # ⚠ PMID goes too. Figure S1 counts categories by task and by provenance and
    # never looks at which paper an outcome belongs to, so the link buys the
    # reader nothing and costs a quasi-identifier: "the one paper in the sample
    # whose outcome is an oral-health measure" is a sentence about one paper.
    ("data/outcomes/08_08_2026_all_outcomes_classified.csv", dict(kind="qi",
     keep=["Study_Type", "category", "domain", "source"])),

    # ---- author countries: the counts, collapsed within region --------------
    # ⚠ 25 of the 104 countries carry one paper. Collapsed WITHIN region, so a
    # region's subtotal still adds up: one global Other row would move an Asian
    # country's authorships into a European subtotal.
    ("data/analysis/08_25_2026_author_countries_S1.csv", dict(kind="qi",
     keep=["rank", "country", "region", "authors", "share", "first", "last",
           "corr", "papers"],
     collapse_rows={"country": "papers"}, collapse_within="region")),

    # ---- journals: the quartile band, and nothing else --------------------
    # ⚠ THE FINGERPRINT. Everything dropped here is public in SCImago or JCR,
    # which is exactly why it identifies: an exact SJR of 1,043 with a coverage
    # span of 1986-2026 and a subfield names one journal, and a journal plus
    # 2022 plus a Saudi author often names one paper. stratified_analysis.R
    # reads two columns from this file. Two columns ship.
    ("data/journals/07_25_2026_journal_landscape_by_paper_385_JCR.csv",
     dict(kind="qi", keep=["PMID", "Study_Type", "jcr_2022_quartile"])),

    # ---- Saudi affiliations: sector, never identity ----------------------
    # The paper-level file loses `sectors_present`, a semicolon list of sector
    # types with 43 distinct combinations, 28 of them carried by one paper. The
    # two things the analysis derives from it ship instead, already computed.
    ("data/authors/07_25_2026_saudi_paper_level.csv", dict(kind="qi",
     keep=["PMID", "n_sectors", "multisector", "multisector_union",
           "lead_saudi_type"],
     derive="sector_flags",
     collapse_values={"lead_saudi_type": None})),
    # Author-position level. PMID is dropped outright: the figure that reads
    # this file uses it only to total first and last authorships per
    # institution, so the paper-to-institution link buys nothing and is the
    # single most identifying relation in the study.
    ("data/authors/07_25_2026_saudi_affiliation_long.csv", dict(kind="qi",
     keep=["is_first", "is_last", "inst_type", "institution", "city"],
     collapse_values={"institution": None, "city": None, "inst_type": None})),
    # ⚠ The institution VALUES here and the institution ROWS in the counts table
    # must collapse to the same set, or the figure's merge on institution loses
    # its first and last authorships. Both count distinct papers, so they do.
    ("data/authors/07_25_2026_saudi_institution_counts.csv", dict(kind="qi",
     keep=["institution", "inst_type", "author_appearances", "papers"],
     collapse_rows={"institution": "papers"},
     collapse_values={"inst_type": "papers"})),
    ("data/authors/07_25_2026_saudi_city_counts.csv", dict(kind="qi",
     keep=["city", "author_appearances"],
     collapse_rows={"city": "author_appearances"})),
    ("data/authors/07_25_2026_saudi_institution_type_counts.csv", dict(kind="qi",
     keep=["inst_type", "author_appearances", "pct_authors",
           "distinct_institutions", "papers_involving"],
     collapse_rows={"inst_type": "papers_involving"})),

    # ---- adjudication process, calibration, quality control ---------------
    ("data/adjudication/process-tables/cell_level_detail.csv", dict(kind="items")),
    ("data/calibration/Calibration and agreement with new reviewer 5.xlsx",
     dict(kind="derived")),
    ("data/calibration/Calibration and agreement_round_2_new_rev5.xlsx",
     dict(kind="derived")),
    ("data/calibration/calibration_likeforlike_fix.csv", dict(kind="derived")),
    ("data/calibration/round-1/2024_05_04_Adjudication_of_calibration.xlsx",
     dict(kind="items")),
    # ⚠ "revierwer" is the real spelling on disk, and the calibration script
    # opens it by that name. Correcting it here would only make the file missing.
    ("data/calibration/round-1/Reviewer and adjudication answers with new revierwer 5.xlsx",
     dict(kind="items")),
    ("data/calibration/round-1/agreement_new_5.xlsx", dict(kind="items")),
    ("data/calibration/round-2/2024_07_13_Adjudication_of_calibration_round_2.xlsx",
     dict(kind="items")),
    ("data/calibration/round-2/2024_11_26_Progress_round_2.csv", dict(kind="items")),
    ("data/calibration/round-2/agreement_round_2.xlsx", dict(kind="items")),
    ("data/quality-control/07_16_2026_soft_dependencies_catalogue.xlsx",
     dict(kind="items", drop=["pmids_str"])),
    ("data/quality-control/08_08_2026_inconsistency_resolution_worklist.xlsx",
     dict(kind="items")),
    ("data/quality-control/08_12_2026_worklist_apply_log.csv", dict(kind="items")),
    # Five aggregate counts over the 385 and the name of the script that made
    # them. Table 1 asserts against it, so without it the table does not build.
    ("data/provenance/08_25_2026_funding_quantities.json", dict(kind="derived")),
])

# Files whose source path is not their destination path.
RELOCATED = [
    ("codes audit/output/assignment/09_01_2026_final_reviewer_pairs_385.csv",
     "data/tables/09_01_2026_final_reviewer_pairs_385.csv", dict(kind="items")),
]

# SEED INTERMEDIATES. The sensitivity analyses read these tables and, between
# them, also write several: the chain is circular, so a clean checkout cannot
# bootstrap it. Shipping them as data breaks the cycle. All are derived.
SEED_TABLES = [
    "08_19_2026_agreement_difficulty_ranking.csv",
    "08_19_2026_bias_analysis_corrected_prevalence.csv",
    "08_19_2026_calibration_crosswalk.csv",
    "08_19_2026_calibration_flag_level_by_domain.csv",
    "08_19_2026_calibration_imputed_parameters.csv",
    "08_19_2026_calibration_parameter_source.csv",
    "08_19_2026_tipping_point_thresholds.csv",
    "08_20_2026_bias_analysis_both_axes.csv",
    "08_21_2026_calibration_percent_by_reviewer.csv",
    "08_22_2026_agreement_collapsed_by_concept.csv",
    "08_29_2026_bias_analysis_by_task.csv",
    "08_29_2026_explain_away_thresholds.csv",
    "08_29_2026_stratified_indices_perturbed.csv",
    "08_29_2026_stratified_spread_perturbed.csv",
    "08_29_2026_tipping_point_by_task.csv",
]

# The instrument PDF is the study's own data-collection tool. It names no paper
# and no person, it is already public on OSF, and Figure 4 and the instrument
# table are both built by reading it.
EXTRA_COPY = ["docs/instrument"]

# Dropped from EVERY shipped file, whatever its kind, by column name.
# ⚠ Each of these was found by the k-anonymity gate after this rewrite had
# already been reviewed once. `local_funders` held 45 funders, singletons
# included: a funder named on one paper names the paper. The calibration
# workbooks describe what each pilot paper measured, in the reviewer's own
# words, and a phrase like "recurrence of otitis media with effusion" is a
# search query. None of them is read by any published display.
ALWAYS_DROP = re.compile(
    r"(local_funders|intl_funders|funder|sponsor|funding_statement|"
    r"exposure of the study|outcome of the study|"
    r"do you have any comments|comment/comments related to|"
    r"^comments?$)", re.I)

CODE_DIRS = ["code"]
CODE_EXT = {".r", ".py"}
# ⚠⚠ `manuscript` EXCLUDED 2026-09-02, on the author's instruction. Publishing
# the pipeline does not mean publishing the paper. code/manuscript holds the
# assembler, the citation audit, the renumbering tools and the package builder,
# and two of its scripts carry entire internal documents as string literals: the
# journal-target comparison, with the submission ladder and acceptance rates,
# and the conference-target list. None of it is read by any published display,
# and only one shipped file even mentions the directory, in a comment.
CODE_EXCLUDE_PARTS = {"private", "public-repo", "codes audit", "archive",
                      ".git", "__pycache__", "_superseded", "manuscript",
                      "sas-recovered-2026-08-31", "sas"}

# ⚠⚠ THE SAMPLING PROVENANCE SCRIPTS ARE A RE-IDENTIFICATION RECIPE.
# Excluded 2026-09-07 on the author's instruction, the same call as `manuscript`.
#
# Redacting `set.seed(123)` is not enough on its own if these ship beside it.
# Between them they publish the mechanism (random sort, then a random draw), the
# exact frame size (N = 5,530 on 2026-07-21, 5,528 today), the window the two
# departed records sit in, and a worked inversion that recovers a frame from a
# draw. With all of that public the only missing input is a seed, and
# `set.seed(123)` is the most guessable value in R. That is a short brute force,
# not a barrier. It matters because the 2026-07-21 top-up of 20 IS exactly
# reproducible (rank correlation 1.0000) and three of those twenty are in the
# analysed 385.
#
# ⚠ `2023_12_21_Final_Query_211223.R` is deliberately NOT here. It documents how
# the sample was drawn, which is the method the paper rests on, and its draw is
# unrecoverable regardless: the frame and the hit count were never saved. It
# ships with its seed redacted.
#
# One filename per line so that removing one is a one-line reversal.
CODE_EXCLUDE_FILES = {
    "2026_07_21_Final_Query_topup20.R",        # the draw that IS reproducible
    "09_05_2026_recover_topup_frame.R",        # the inversion, worked end to end
    "09_05_2026_invert_1000_search.R",
    "09_05_2026_frame_reproduction_check.R",
    "09_05_2026_make_topup_script.py",
    "09_07_2026_rng_state_sweep.R",            # names N = 5,530 and the mechanism
    "09_07_2026_sample_uniformity_test.R",
    "09_07_2026_rebuild_study_sample.R",
    "09_07_2026_retraction_check.py",
    "09_07_2026_absentee_eligibility_check.py",
    "09_07_2026_resolve_absent_frame_paper.py",
    # ⚠ Calibration provenance, withheld 2026-09-07 for a different reason: these
    # invoke SAS and read from `codes audit/`, neither of which ships, so in the
    # public tree they are dangling references. They supported two figures that
    # have since been removed from the Methods, so nothing published depends on
    # them. They stay in the private tree as the record of why R and SAS disagree
    # on Krippendorff's alpha for an invariant matrix.
    "09_07_2026_sas_kalpha_assemble.py",
    "09_07_2026_sas_kalpha_parse.py",
    "09_07_2026_rebuild_recoded_long.R",
}

# ---------------------------------------------------------------------------
# Public-repository patches, applied AFTER a file is copied.
#
# ⚠ The repository is REBUILT, never maintained in place. Editing a file inside
# public-repo/ is silently undone by the next build, which is how the reviewer
# load table regressed to reading a path outside the repository. Any change that
# must survive belongs here, keyed by the file it applies to.
PATCHES = {
    "code/tables/09_01_2026_reviewer_load_table.py": [
        # the private script reads the audit scratch folder, which does not ship
        ('"codes audit", "output", "assignment"', '"data", "tables"'),
        # ⚠ Second script found writing an OUTPUT into data/, after the caveat
        # register. data/ is the shipped inputs; anything a run produces belongs
        # in outputs/, or it sits among the inputs as an orphan the next build
        # cannot account for and the gates read it as published data.
        ('OUTD = os.path.join("data", "tables")',
         'OUTD = os.path.join("outputs", "tables")'),
    ],
    "code/scoring/07_30_2026_stratified_analysis.R": [
        # `sectors_present` does not ship: 43 combinations, 28 of them carried by
        # a single paper. The health-system flag it was used to compute ships
        # instead, computed identically, so the stratifier is unchanged.
        ('inst<- CH("data/authors/07_25_2026_saudi_paper_level.csv")[, c("PMID","sectors_present","multisector")]',
         'inst<- CH("data/authors/07_25_2026_saudi_paper_level.csv")[, c("PMID","health_system","multisector")]'),
        ('w$comp_lab <- ifelse(vapply(strsplit(ifelse(is.na(w$sectors_present),"",w$sectors_present), ";\\\\s*"),\n'
         '                            function(v) any(trimws(v) %in% .HEALTH), logical(1)), "Health-system","Academic-only")',
         'w$comp_lab <- ifelse(w$health_system %in% c("True","TRUE","1"), "Health-system","Academic-only")'),
    ],
    "code/figures/08_25_2026_S2_saudi_institutions_figure.py": [
        ('HS_LO, HS_HI = int(pap.sectors_present.map(_ish).sum()), int(pap.sectors_present_union.map(_ish).sum())',
         'HS_LO, HS_HI = int(pap.health_system.isin(["True", "TRUE", "1"]).sum()), '
         'int(pap.health_system_union.isin(["True", "TRUE", "1"]).sum())'),
        ('args = [a.upper() for a in sys.argv[1:] if a.upper() in BUILD] or sorted(BUILD)',
         'args = [a.upper() for a in sys.argv[1:] if a.upper() in BUILD] or ["C"]'),
    ],
    # ⚠ THE CANDIDATE SWEEPS DO NOT SHIP. Four scripts build every design they
    # were compared on, and the supplement uses one of each: S1 outcomes C,
    # S2 countries B, S3 institutions C, S4 journals E, each confirmed by
    # matching the package PNG's checksum against the variants. Building the
    # other seventeen costs about eight minutes a run and publishes layouts the
    # paper does not use. The sweeps are the author's design record and stay in
    # the private tree.
    "code/figures/08_26_2026_S4_outcomes_figure.py": [
        ('args = [a.upper() for a in sys.argv[1:] if a.upper() in BUILD] or list(BUILD)',
         'args = [a.upper() for a in sys.argv[1:] if a.upper() in BUILD] or ["C"]'),
    ],
    # Table 1 counted authors out of the PubMed author cache, which is a file of
    # 385 author lists with surnames and does not ship. It used the count only to
    # band papers into 1-2, 3-10 and 11+, and data/scoring/07_30_2026_team_size_385.csv
    # already carries exactly that band for all 385, so the band is read instead
    # of the names being recounted. The sector derivations move to the shipped
    # booleans for the same reason they did in the R.
    # ⚠ Table S3 is an OUTPUT, so it belongs in outputs/. Privately it is written
    # into data/scoring/ and the package builder copies it from there. Left that
    # way here it lands among the shipped inputs, survives as an orphan the next
    # build cannot account for, and, being one row per study, joins the profile:
    # the k gate's ratchet caught it immediately, 74 unique to 90.
    # Figure S4 counts over the two journal tables and never looks at which
    # paper, so it reads the unkeyed, shuffled copies. It also builds all five
    # candidate designs when given no argument; here it builds the one the
    # supplement ships, because the others print journal names down the tail and
    # the tail no longer carries names.
    "code/figures/08_25_2026_S3_journal_landscape_figure.py": [
        ('P = pd.read_csv("data/journals/07_25_2026_journal_landscape_by_paper_385_JCR.csv",\n'
         '                keep_default_na=False)\n'
         'J = pd.read_csv("data/journals/07_25_2026_journal_landscape_by_journal_385_JCR.csv",\n'
         '                keep_default_na=False)',
         'P = pd.read_csv("data/journals/08_25_2026_journal_landscape_by_paper_385_public.csv",\n'
         '                keep_default_na=False)\n'
         'J = pd.read_csv("data/journals/08_25_2026_journal_landscape_by_journal_385_public.csv",\n'
         '                keep_default_na=False)'),
        ('args = [a.upper() for a in sys.argv[1:] if a.upper() in BUILD] or list(BUILD)',
         'args = [a.upper() for a in sys.argv[1:] if a.upper() in BUILD] or ["E"]'),
    ],
    # Figure S2 reads two per-paper country files for four aggregates and never
    # looks at which paper. The aggregates ship instead; the files do not.
    "code/figures/08_25_2026_S1_author_countries_figure.py": [
        ('ps = pd.read_csv(PS, dtype=str).fillna("")\n'
         'al = pd.read_csv(AL, dtype=str).fillna("")',
         'import json as _json\n'
         '_agg = _json.load(open("data/analysis/08_25_2026_author_countries_aggregates.json",\n'
         '                       encoding="utf-8"))'),
        ('UNIQ = len(al)\n'
         'NPAP = len(ps)\n'
         'NDUAL = int((al.dual_affiliation == "True").sum())',
         'UNIQ = _agg["n_author_positions"]\n'
         'NPAP = _agg["n_papers"]\n'
         'NDUAL = _agg["n_dual_country"]'),
        ('_rp = Counter()\n'
         'for _, r in ps.iterrows():\n'
         '    for g in {REGOF.get(x.strip()) for x in r.countries.split(";") if x.strip()}:\n'
         '        if g:\n'
         '            _rp[g] += 1',
         '_rp = Counter(_agg["region_papers"])'),
        # ⚠ Build only the design the supplement ships, as for Figure S4. The
        # candidate variants lay out a fixed number of country rows, and the k=5
        # collapse changed that count, so one of them now overflows the page and
        # its own spill assertion stops the whole run.
        ('args = [a.upper() for a in sys.argv[1:] if a.upper() in BUILD] or ["A", "B", "C"]',
         'args = [a.upper() for a in sys.argv[1:] if a.upper() in BUILD] or ["B"]'),
    ],
    "code/pipeline/08_12_2026_build_caveats_register.py": [
        ("out='data/scoring/08_12_2026_known_data_caveats.xlsx'",
         "out='outputs/tables/08_12_2026_known_data_caveats.xlsx'"),
    ],
    "code/tables/_gen_table1.py": [
        ("_cache = json.load(open('data/authors/07_25_2026_authors_cache_385.json', encoding='utf-8'))\n"
         "w['n_auth'] = [len([a for a in _cache.get(str(p), []) if str(a.get('last', '')).strip()]) for p in w.PMID]",
         "_ts = pd.read_csv('data/scoring/07_30_2026_team_size_385.csv', dtype=str)[['PMID', 'team_cat']]\n"
         "w = w.merge(_ts, on='PMID', how='left')"),
        ("_inst = pd.read_csv('data/authors/07_25_2026_saudi_paper_level.csv', dtype=str, keep_default_na=False)"
         "[['PMID','sectors_present','multisector','sectors_present_union','multisector_union']]",
         "_inst = pd.read_csv('data/authors/07_25_2026_saudi_paper_level.csv', dtype=str, keep_default_na=False)"
         "[['PMID','health_system','multisector','health_system_union','multisector_union']]"),
        ("_inst['comp_lab'] = _inst['sectors_present'].map(\n"
         "    lambda s: 'Health-system' if any(p.strip() in _HEALTH for p in str(s).split(';')) else 'Academic-only')",
         "_inst['comp_lab'] = _inst['health_system'].map(\n"
         "    lambda v: 'Health-system' if str(v) in ('True','TRUE','1') else 'Academic-only')"),
        ("_inst['comp_lab_u'] = _inst['sectors_present_union'].map(\n"
         "    lambda s: 'Health-system' if any(p.strip() in _HEALTH for p in str(s).split(';')) else 'Academic-only')",
         "_inst['comp_lab_u'] = _inst['health_system_union'].map(\n"
         "    lambda v: 'Health-system' if str(v) in ('True','TRUE','1') else 'Academic-only')"),
        (" ('Number of authors', '1–2', w.n_auth<=2),\n"
         " ('Number of authors', '3–10', (w.n_auth>=3)&(w.n_auth<=10)), "
         "('Number of authors', '11+', w.n_auth>=11),",
         " ('Number of authors', '1–2', w.team_cat=='1-2'),\n"
         " ('Number of authors', '3–10', w.team_cat=='3-10'), "
         "('Number of authors', '11+', w.team_cat=='11+'),"),
    ],
}


def apply_patches(rel, dst):
    """Return the number of patches applied to a just-written file."""
    key = rel.replace(os.sep, "/")
    if key not in PATCHES:
        return 0
    t = open(dst, encoding="utf-8", errors="replace").read()
    n = 0
    for old, new in PATCHES[key]:
        if old in t:
            t = t.replace(old, new)
            n += 1
        else:
            print("  !! patch no longer matches in %s" % key)
    if n:
        open(dst, "w", encoding="utf-8", newline="").write(t)
    return n


REVIEWER_NAMES = ["Tala", "Reham", "Turki", "Esraa", "Saleh", "Rami", "Lubna",
                  "Musfer", "Dana", "Ali", "Maha", "Arwa", "Roah", "Alhanouf",
                  "Nouf", "Saad"]
WITHDREW_IDX = 3                      # recruitment id of the reviewer who left

HEALTH_SECTORS = ("Hospital / medical city", "Hospital & research centre",
                  "Ministry of Health", "Military & security-forces medical")


def reviewer_label(name):
    """Name -> R1..R13, contiguous, matching the calibration displays."""
    try:
        i = REVIEWER_NAMES.index(name) + 1
    except ValueError:
        return None
    if i == WITHDREW_IDX:
        return "R-withdrawn"
    return "R%d" % (i if i < WITHDREW_IDX else i - 1)


def build_map():
    """Surrogates over the whole study universe, in a seeded random order."""
    uni = os.path.join(ROOT, "private", "_study_pmid_universe.json")
    ids = sorted(json.load(open(uni, encoding="utf-8")))
    rng = random.Random(SEED)
    rng.shuffle(ids)
    return {p: "STUDY-%04d" % (i + 1) for i, p in enumerate(ids)}


def load_named_entities():
    """Journal names, journal abbreviations and institution names, from the
    private reference tables.

    ⚠ A REGEX CANNOT FIND A PROPER NOUN. Three papers were named in shipped code
    by a trailing comment - `PMC10563532,   # J Diabetes Sci Technol` - and no
    pattern would ever have matched "J Diabetes Sci Technol". The study already
    holds the list of every journal and institution it touched, so the scrub is
    driven by that list instead of by guesswork. Short names are left alone:
    below eight characters the risk of mangling ordinary prose outweighs it."""
    out = set()
    for path, cols in (
            ("data/journals/07_25_2026_journal_landscape_by_journal_385_JCR.csv",
             ("journal", "jcr_abbr", "scimago_title", "scimago_publisher")),
            ("data/journals/07_25_2026_journal_landscape_by_journal_JCR.csv",
             ("journal", "jcr_abbr")),
            ("data/authors/07_25_2026_saudi_institution_counts.csv",
             ("institution",))):
        p = os.path.join(ROOT, path)
        if not os.path.exists(p):
            continue
        try:
            with open(p, encoding="utf-8-sig", newline="") as f:
                for r in csv.DictReader(f):
                    for c in cols:
                        v = (r.get(c) or "").strip()
                        if len(v) >= 8:
                            out.add(v)
        except Exception as e:
            print("  !! entity list unreadable: %s (%s)" % (path, str(e)[:40]))
    return sorted(out, key=len, reverse=True)      # longest first, so a title is
                                                   # not half-eaten by its own abbreviation


ENTITY_RX = None
ENTITY_HITS = Counter()
ENTITY_FILES = Counter()
# Every value this repository deliberately publishes. An entity name that is
# also a published value must NOT be cut out of the code.
# ⚠ "Ministry of Health" is a journal-list institution AND the sector label the
# analysis tests against: .HEALTH in the R and HEALTH in the figure are literal
# sets of these strings. Redacting them turned every health-system paper into an
# academic-only one, silently, and the totals still summed to 385.
PUBLISHED_VALUES = set()


def scrub_text(s, id_map, name_rx):
    """Rewrite any study identifier or reviewer name inside a free-text value."""
    if not s:
        return s
    out = s
    # ⚠ Found by the identifier gate's WARNINGS, not its failures, on 2026-09-01.
    # A PMC accession names a paper as exactly as a PMID does; a trial
    # registration names the trial and therefore the paper; and a publisher's
    # own article URL needs no lookup at all. None of the three was a pattern
    # this scrubber knew, and all three sat in shipped code.
    out = re.sub(r"\bPMC\d{5,}\b", "[PMC-REDACTED]", out)
    out = re.sub(r"\b(NCT|ISRCTN|ACTRN|CTRI|IRCT|ChiCTR|PACTR)[\w/-]*\d{6,}\b",
                 "[TRIAL-REG-REDACTED]", out)
    # a URL whose path carries an article number or ends at a pdf. An API
    # endpoint (esummary.fcgi, /entrez/eutils/) has neither and is left alone,
    # because redacting it would break code that is published to be read.
    out = re.sub(r"https?://[^\s\"',;)\]]*?(?:/\d{3,}[^\s\"',;)\]]*|\.pdf)",
                 "[ARTICLE-URL-REDACTED]", out)
    for m in set(re.findall(r"(?<!\d)\d{8}(?!\d)", out)):
        if m in id_map:
            out = out.replace(m, id_map[m])
    out = name_rx.sub(lambda m: reviewer_label(m.group(0)) or m.group(0), out)
    # A DOI names a paper as precisely as a PMID and there is no surrogate for it,
    # so it is redacted rather than mapped. Same for the analyst's home directory,
    # which carries a real username.
    out = re.sub(r"10\.\d{4,9}/[^\s\"',;)\]]+", "[DOI-REDACTED]", out)
    # An ISSN names a venue and has no surrogate, so it is redacted like a DOI.
    # Free-text notes carry them mid-sentence ("JCR lists it under ISSN ..."),
    # which dropping identifying COLUMNS never catches. Year ranges take the same
    # shape and are left alone.
    out = re.sub(r"(?<!\d)(\d{4})-(\d{3}[\dXx])(?!\d)",
                 lambda m: m.group(0) if (m.group(1)[:2] in ("19", "20")
                                          and m.group(2)[:2] in ("19", "20"))
                 else "[ISSN-REDACTED]", out)
    # The project root is hard-coded as an absolute path in many scripts, as an
    # os.chdir to a Windows home directory. Redacting only the username leaves a
    # path that does not exist and the script dies on chdir. Replace the WHOLE
    # path with ".", which is what running from the repository root means anyway.
    out = re.sub(r"[A-Za-z]:[\\/][^\"'\n]*?Assessment of healthcare research in saudi",
                 lambda m: ".", out)
    out = re.sub(r"/Users/[A-Za-z0-9._-]+/", "/Users/[USER]/", out)
    # Scratch paths encode the home directory with dashes rather than slashes,
    # e.g. C--Users-<name>-OneDrive-... . The slash rules above cannot see it, so
    # the username survived in three calibration scripts.
    out = re.sub(r"C--Users-[A-Za-z0-9._]+-", "C--Users-[USER]-", out)
    # a europepmc / pubmed URL with an article id on the end is an identifier
    out = re.sub(r"(https?://[^\s\"',;)\]]*(?:europepmc\.org|pubmed\.ncbi\.nlm\.nih\.gov)"
                 r"[^\s\"',;)\]]*\d{5,}[^\s\"',;)\]]*)",
                 "[ARTICLE-URL-REDACTED]", out)
    # a lambda, because backslashes in an re.sub replacement are themselves
    # escape sequences and "\U" is not a valid one
    out = re.sub(r"[A-Za-z]:\\Users\\[A-Za-z0-9._-]+",
                 lambda m: "C:\\Users\\[USER]", out)
    return out


def read_text(path):
    """Some SAS-era exports are cp1252, not utf-8. Refusing them would silently
    drop calibration data from the repository, so fall back rather than fail."""
    for enc in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            with open(path, encoding=enc, newline="") as f:
                return f.read(), enc
        except UnicodeDecodeError:
            continue
    return open(path, encoding="utf-8", errors="replace", newline="").read(), "replace"


# ---------------------------------------------------------------------------
# k = 5
# ---------------------------------------------------------------------------
def papers_behind(rows, col, weight_col):
    """How many papers stand behind each value of `col`.

    Three cases, and getting them confused is how a threshold silently stops
    biting. A counts table states the number itself (`papers`). A table with one
    row per paper is counted by DISTINCT PMID, never by row: the author-level
    file has 1,520 rows over 385 papers, so counting rows would credit an
    institution with four author positions on one paper as four papers. With
    neither, a row is a paper."""
    if weight_col:
        tally = Counter()
        for r in rows:
            v = (r.get(col) or "").strip()
            if not v:
                continue
            try:
                tally[v] += int(float(r.get(weight_col) or 0))
            except ValueError:
                pass
        return tally
    if rows and "PMID" in rows[0]:
        seen = {}
        for r in rows:
            v = (r.get(col) or "").strip()
            if v:
                seen.setdefault(v, set()).add(r.get("PMID"))
        return Counter({v: len(s) for v, s in seen.items()})
    return Counter((r.get(col) or "").strip() for r in rows if (r.get(col) or "").strip())


def rare_values(rows, col, weight_col, k=K):
    tally = papers_behind(rows, col, weight_col)
    return {v for v, n in tally.items() if n < k}, tally


# ⚠ These labels are shared with code/figures/08_25_2026_S2_saudi_institutions_
# figure.py, which applies the same threshold so that the private figure and the
# public one are the same figure. If a label changes here it must change there,
# or the figure's merge on institution silently loses the aggregate row.
OTHER = {
    "institution": "Other institutions (fewer than %d papers each)" % K,
    "city": "Other cities (fewer than %d appearances each)" % K,
    "inst_type": "Other sectors",
    "lead_saudi_type": "Other sectors",
    "country": "Other countries",
}


def collapse_column(rows, col, weight_col, stats):
    """Replace every value behind fewer than K papers with one explicit Other."""
    rare, tally = rare_values(rows, col, weight_col)
    if not rare:
        return 0
    label = OTHER.get(col, "Other (fewer than %d papers each)" % K)
    for r in rows:
        if (r.get(col) or "").strip() in rare:
            r[col] = label
    stats["collapsed_values"] += len(rare)
    return len(rare)


def collapse_counts_table(rows, col, weight_col, stats, within=None):
    """A counts table has one row per category. Collapsing the values would
    leave many rows all called Other, so they are summed into one instead.

    ⚠ The Other row carries n_categories, so a figure can still say how many
    categories it stands for without any of them being named.

    `within` keeps the collapse inside a grouping column: the countries table is
    drawn grouped by region with region subtotals, so one global Other row would
    put an Asian country's authorships into a European subtotal. One Other row
    per region instead."""
    rare, tally = rare_values(rows, col, weight_col)
    if not rare:
        return rows, 0
    label = OTHER.get(col, "Other (fewer than %d papers each)" % K)
    kept = [r for r in rows if (r.get(col) or "").strip() not in rare]
    merged = [r for r in rows if (r.get(col) or "").strip() in rare]
    groups = {}
    for r in merged:
        groups.setdefault((r.get(within) or "") if within else "", []).append(r)
    for gval, grp in groups.items():
        agg = {c: "" for c in rows[0]}
        agg[col] = label
        if within:
            agg[within] = gval
        for c in rows[0]:
            if c == col or (within and c == within):
                continue
            tot, numeric = 0.0, True
            for r in grp:
                v = (r.get(c) or "").strip()
                if not v:
                    continue
                try:
                    tot += float(v)
                except ValueError:
                    numeric = False
                    break
            agg[c] = ("%g" % tot) if numeric else ""
        agg["n_categories"] = str(len(grp))
        kept.append(agg)
    for r in kept:
        r.setdefault("n_categories", "1")
    stats["collapsed_rows"] += len(merged)
    return kept, len(merged)


def derive_sector_flags(rows, stats):
    """Ship the two booleans the analysis derives from `sectors_present`, so the
    43-way combination itself never has to."""
    def ish(s):
        return any(p.strip() in HEALTH_SECTORS for p in str(s or "").split(";"))
    for r in rows:
        r["health_system"] = str(ish(r.get("sectors_present")))
        r["health_system_union"] = str(ish(r.get("sectors_present_union")))
    stats["derived_cols"] += 2
    return ["health_system", "health_system_union"]


DERIVERS = {"sector_flags": derive_sector_flags}


# ---------------------------------------------------------------------------
# writers
# ---------------------------------------------------------------------------
def apply_spec(rows, cols, spec, id_map, name_rx, stats):
    """Column allowlist, derivations and k-collapse, in that order.

    ⚠ ORDER. Values collapse before rows: on the institution counts table the
    rare TYPES are relabelled first, so the Other row that follows carries a
    sector label rather than a blank the figure would have to colour."""
    extra = []
    if spec.get("derive"):
        extra = DERIVERS[spec["derive"]](rows, stats)
    keep = spec.get("keep")
    if keep is not None:
        dropped = [c for c in cols if c not in keep]
        stats["cols_dropped"] += len(dropped)
        cols = [c for c in cols if c in keep] + [c for c in extra if c not in cols]
    else:
        drop = set(spec.get("drop") or [])
        stats["cols_dropped"] += len([c for c in cols if c in drop])
        cols = [c for c in cols if c not in drop] + extra
    gone = [c for c in cols if ALWAYS_DROP.search(c or "")]
    if gone:
        stats["cols_dropped"] += len(gone)
        cols = [c for c in cols if c not in gone]
    for col, weight in (spec.get("collapse_values") or {}).items():
        if col in cols:
            collapse_column(rows, col, weight, stats)
    for col, weight in (spec.get("collapse_rows") or {}).items():
        if col in cols:
            rows, merged = collapse_counts_table(rows, col, weight, stats,
                                                 within=spec.get("collapse_within"))
            if merged and "n_categories" not in cols:
                cols = cols + ["n_categories"]
    return rows, cols


def do_csv(src, dst, spec, id_map, name_rx, stats):
    text, _ = read_text(src)
    rd = csv.DictReader(io.StringIO(text))
    cols = [c for c in (rd.fieldnames or []) if c]
    rows = [dict(r) for r in rd]
    rows, cols = apply_spec(rows, cols, spec, id_map, name_rx, stats)
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    hdr = {c: scrub_text(c, id_map, name_rx) for c in cols}
    with open(dst, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=[hdr[c] for c in cols])
        w.writeheader()
        for r in rows:
            out = {hdr[c]: scrub_text(r.get(c) or "", id_map, name_rx) for c in cols}
            for v in out.values():
                if isinstance(v, str) and 4 <= len(v) <= 80:
                    PUBLISHED_VALUES.add(v.strip().lower())
            w.writerow(out)
    return len(rows)


def do_xlsx(src, dst, spec, id_map, name_rx, stats):
    """xlsx keeps its sheets and formatting, so it is edited in place rather
    than rewritten. Only the column allowlist and the scrub apply; the k-collapse
    is for the csv layer, and every xlsx that ships is `items` or `derived`."""
    import openpyxl
    wb = openpyxl.load_workbook(src, data_only=True)
    drop_names = set(spec.get("drop") or [])
    keep = spec.get("keep")
    n = 0
    for ws in wb.worksheets:
        rows = list(ws.iter_rows())
        if not rows:
            continue
        hdr = [(c.value if c.value is not None else "") for c in rows[0]]
        drop_idx = {i for i, h in enumerate(hdr)
                    if str(h).strip() in drop_names
                    or ALWAYS_DROP.search(str(h))
                    or (keep is not None and str(h).strip() and str(h).strip() not in keep)}
        stats["cols_dropped"] += len(drop_idx)
        for r in rows:
            for i, c in enumerate(r):
                try:
                    if i in drop_idx:
                        c.value = None
                    elif isinstance(c.value, str):
                        c.value = scrub_text(c.value, id_map, name_rx)
                    elif isinstance(c.value, (int, float)):
                        s = str(c.value).split(".")[0]
                        if s in id_map:
                            c.value = id_map[s]
                except AttributeError:
                    # a merged cell is read-only in openpyxl. It mirrors its
                    # anchor, which IS written, so nothing is left un-scrubbed.
                    stats["merged_skipped"] = stats.get("merged_skipped", 0) + 1
            n += 1
        # headers can name a reviewer, e.g. "R5 vs. adj", or a calibration paper
        for c in rows[0]:
            if isinstance(c.value, str):
                c.value = scrub_text(c.value, id_map, name_rx)
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    wb.save(dst)
    return n


def do_json(src, dst, id_map, name_rx):
    """A json file is scrubbed as text: there is no column structure to
    allowlist, so only files whose whole content is aggregate may be listed."""
    raw, _ = read_text(src)
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    open(dst, "w", encoding="utf-8").write(scrub_text(raw, id_map, name_rx))


def redact_sampling_seed(out, src):
    """⚠ THE SAMPLING SEED IS A KEY, NOT A PARAMETER, and only inside code/sampling.

    Published together, the query and `set.seed(123)` regenerate the drawn PMIDs.
    That is not theoretical: on 2026-09-07 the 2026-07-21 top-up of 20 was
    re-derived exactly this way (rank correlation 1.0000 at N = 5,530), and three
    of those twenty are in the analysed 385. Surrogating the PMIDs written *in*
    the script does not help, because the seed lets a reader recompute the real
    ones from PubMed. So the seed value itself is redacted.

    Scoped to code/sampling deliberately. Every other seed in this repository
    (bootstrap resamples, jitter, reviewer assignment) keys an analysis rather
    than the identity of a paper, and stripping those would destroy the
    reproducibility the repository exists to provide.
    """
    rel = os.path.relpath(src, ROOT).replace(os.sep, "/")
    if "/sampling/" not in "/" + rel:
        return out, 0
    n = [0]

    def _sub(m):
        n[0] += 1
        # Inside a comment or a prose line, swap the value and stop. Appending a
        # second "#" there would nest one comment inside another and read as noise.
        line_start = out.rfind("\n", 0, m.start()) + 1
        in_prose = "#" in out[line_start:m.start()]
        if in_prose:
            return "set.seed(SAMPLING_SEED)"
        return ("set.seed(SAMPLING_SEED)  # value withheld: the seed plus the query "
                "would regenerate the sampled PMIDs")
    out = re.sub(r"set\.seed\(\s*\d+L?\s*\)(?:[ \t]*#[^\n]*)?", _sub, out)
    if n[0]:
        out = ("# NOTE (public repository): the sampling seed is withheld. With the query\n"
               "# above it would regenerate the drawn PMIDs, so it is a re-identification\n"
               "# key rather than a reproducibility parameter. The realised sample is\n"
               "# published as data; see the Data Availability statement.\n") + out
    return out, n[0]


def do_code(src, dst, id_map, name_rx, stats):
    t = open(src, encoding="utf-8", errors="replace").read()
    found = sorted({x for x in re.findall(r"(?<!\d)\d{8}(?!\d)", t) if x in id_map})
    out = scrub_text(t, id_map, name_rx)     # same rules as the data, not a subset
    out, n_seed = redact_sampling_seed(out, src)
    if n_seed:
        stats["sampling_seeds"] = stats.get("sampling_seeds", 0) + n_seed
    # ⚠ THE ENTITY SCRUB IS FOR CODE ONLY. In data, `institution` is a column
    # this repository deliberately publishes for the 33 institutions with five
    # or more papers; redacting it there would delete the very thing the k=5
    # rule was designed to make publishable. In code a journal or institution
    # name is only ever a comment or a hard-coded ruling, and it names a paper.
    if ENTITY_RX is not None:
        def _ent(m):
            ENTITY_HITS[m.group(0)] += 1
            ENTITY_FILES[os.path.relpath(src, ROOT).replace(os.sep, "/")] += 1
            return "[NAME-REDACTED]"
        out = ENTITY_RX.sub(_ent, out)
    if found:
        stats["code_ids"] += len(found)
        out = ("# NOTE (public repository): %d hard-coded study identifier(s) were\n"
               "# rewritten to de-identified surrogates by tools/build_public_repo.py.\n"
               "# They are rulings about particular studies rather than values the data\n"
               "# can supply, so they have to travel with it.\n" % len(found)) + out
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    open(dst, "w", encoding="utf-8", newline="").write(out)
    return len(found)


def code_excluded(path):
    parts = path.replace("\\", "/").split("/")
    # a directory anywhere on the path, or the file itself by name
    return bool(set(parts) & CODE_EXCLUDE_PARTS) or parts[-1] in CODE_EXCLUDE_FILES


GITIGNORE_HEAD = """\
# NEVER commit anything that can map a surrogate back to a real paper.
# ⚠ `*public_repo_id_map*`, not `*id_map*`. The broader pattern also matched
# code/enrichment/08_23_2026_build_pdf_pmid_map.py, because "pmid_map" contains
# "id_map", and quietly dropped a pipeline script from the release. An ignore
# rule that is too wide removes things nobody notices are missing.
*public_repo_id_map*
*DO_NOT_COMMIT*
private/
../private/

# Generated outputs. The repository ships inputs and code; results are rebuilt.
# ⚠ `outputs/*`, not `outputs/`: git cannot re-include a file whose PARENT
# directory is excluded, so the seed-table exceptions below would silently do
# nothing and a clean clone would be missing them.
outputs/*

# The 26 displays, collected under the submission's names by reproduce.py. They
# are the paper's own figures and tables, the journal publishes them, and this
# repository has been shown to regenerate all 26 from the data it ships: the
# images byte for byte, the Word and Excel documents by content. Committing 28 MB
# of copies would add nothing but weight, and a copy can go stale against the
# code beside it in a way a rebuild cannot.
displays/

*.Rhistory
.RData
__pycache__/
*.pyc

# OS and editor noise
.DS_Store
Thumbs.db

# ---------------------------------------------------------------------------
# GENERATED BY tools/build_public_repo.py - do not edit below this line.
#
# ⚠ `outputs/` above would take the seed tables with it. The sensitivity
# analyses read these and, between them, also write several: the chain is
# circular, so a clean clone cannot bootstrap it. Ignoring them would mean four
# supplementary figures failing on a missing file in any fresh checkout, which
# reads as a broken repository. They are inputs that happen to live in an output
# folder, and the list is written from the builder's own SEED_TABLES so it
# cannot drift from what the build puts there.
"""


def write_country_aggregates():
    """The four numbers Figure S2 takes from the two per-paper country files.

    ⚠ WHY A DERIVED FILE RATHER THAN THE FILES THEMSELVES. The figure reads
    07_25_2026_paper_country_summary.csv and 07_25_2026_author_country_long.csv
    and uses them for exactly four aggregates: the paper count, the distinct
    author-position count, how many authors hold affiliations in more than one
    country, and the number of papers per world region. It never looks at which
    paper. Publishing those files would put first, last and corresponding author
    country on every row, which are the cheapest quasi-identifiers in the study
    and would push the joint profile past its baseline. Publishing the four
    aggregates costs nothing: the smallest is a region carrying 22 papers."""
    ps_p = os.path.join(ROOT, "data/authors/07_25_2026_paper_country_summary.csv")
    al_p = os.path.join(ROOT, "data/authors/07_25_2026_author_country_long.csv")
    cc_p = os.path.join(ROOT, "data/analysis/08_25_2026_author_countries_S1.csv")
    for p in (ps_p, al_p, cc_p):
        if not os.path.exists(p):
            print("  !! country aggregates skipped, missing %s" % os.path.basename(p))
            return None
    with open(cc_p, encoding="utf-8-sig", newline="") as f:
        regof = {(r["country"] or "").strip(): (r["region"] or "").strip()
                 for r in csv.DictReader(f)}
    with open(ps_p, encoding="utf-8-sig", newline="") as f:
        ps = list(csv.DictReader(f))
    with open(al_p, encoding="utf-8-sig", newline="") as f:
        al = list(csv.DictReader(f))
    region_papers = Counter()
    for r in ps:
        for g in {regof.get(x.strip()) for x in (r.get("countries") or "").split(";")
                  if x.strip()}:
            if g:
                region_papers[g] += 1
    out = {"n_papers": len(ps),
           "n_author_positions": len(al),
           "n_dual_country": sum(1 for r in al
                                 if (r.get("dual_affiliation") or "") == "True"),
           "region_papers": dict(sorted(region_papers.items()))}
    thin = [g for g, n in region_papers.items() if n < K]
    if thin:
        print("  !! a region carries fewer than %d papers: %s" % (K, thin))
    dst = os.path.join(PUB, "data/analysis/08_25_2026_author_countries_aggregates.json")
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    json.dump(out, open(dst, "w", encoding="utf-8"), indent=1)
    return out


# Files this builder writes itself, unkeyed: no study id, rows shuffled. The
# k-anonymity gate exempts them from the cell rule, because that rule asks
# whether a category isolates a PAPER and these tables have no paper to isolate.
# What they may still not do is carry free text or name a rare entity, which is
# handled where they are written.
UNKEYED = ["data/journals/08_25_2026_journal_landscape_by_paper_385_public.csv",
           "data/journals/08_25_2026_journal_landscape_by_journal_385_public.csv",
           "data/analysis/08_25_2026_author_countries_aggregates.json"]


def canonical_jcr_note(note):
    """One of four phrases, or nothing.

    ⚠ The raw note reads "Not in JCR by eISSN 1234-5678; ESCI-only" and varies
    per journal, which is free text about a venue. The figure parses it only to
    decide which of four reasons a journal has no 2022 quartile, in a fixed
    precedence, so the note is reduced to a phrase that lands in the same branch.
    The precedence is the figure's, not this file's: getting it wrong moves two
    journals and breaks the "54 of 87 delisted or suppressed" the Results quote."""
    s = (note or "").lower()
    if "suppress" in s:
        return "JIF suppressed"
    if "not in jcr by" in s:
        # ⚠ must still CONTAIN "not in jcr by": the figure matches that
        # substring, and "Not in JCR at all" fell through every branch and put
        # six papers in an unclassified bucket. Its assertion caught it.
        return "Not in JCR by ISSN or name"
    if "esci" in s:
        return "ESCI in 2022"
    if "delist" in s:
        return "Delisted from WoS"
    return note


def write_journal_landscape_unkeyed(id_map, name_rx, stats):
    """The two tables Figure S4 counts over, with the linkage removed.

    ⚠ WHY UNKEYED AND SHUFFLED RATHER THAN WITHHELD. Every panel of that figure
    is an aggregate: quartile counts, task by quartile, access route by task,
    why 87 papers carry no JCR quartile, and the journals with five or more
    papers. None of it looks at WHICH paper. The identifying power was never in
    the attributes, it was in attaching them to a study id: with the id present,
    SJR quartile, access route and subject field take the joint profile from 159
    unique of 310 to 274. Dropping the id and shuffling the rows removes the
    join, and every count the figure makes is order-independent, so the figure
    is unchanged. Row ORDER is a key too, which is why the shuffle matters: left
    in the source order, position alone would re-link these rows to any other
    per-paper file that ships.

    The journal table keeps a name only where five or more papers stand behind
    it, which is the same rule the shipped design already applies."""
    src_p = os.path.join(ROOT, "data/journals/07_25_2026_journal_landscape_by_paper_385_JCR.csv")
    src_j = os.path.join(ROOT, "data/journals/07_25_2026_journal_landscape_by_journal_385_JCR.csv")
    if not (os.path.exists(src_p) and os.path.exists(src_j)):
        print("  !! journal landscape sources missing; Figure S4 will not build")
        return None
    P_KEEP = ["Study_Type", "sjr_best_quartile", "jcr_2022_quartile", "oa_status",
              "scimago_open_access", "is_in_doaj", "in_pmc", "field", "domain",
              "publisher_country", "pub_year"]
    # n_causal / n_descriptive / n_predictive are the task mix panel E prints
    # beside each named journal. On an unnamed row they say only that some
    # journal in the sample carries that mix.
    J_KEEP = ["journal", "n_papers", "n_descriptive", "n_predictive", "n_causal",
              "sjr_best_quartile", "jcr_2022_quartile", "jcr_note",
              "scimago_open_access", "is_in_doaj"]
    rng = random.Random(SEED)
    out = {}
    for src, keep, dst_rel in (
            (src_p, P_KEEP, "data/journals/08_25_2026_journal_landscape_by_paper_385_public.csv"),
            (src_j, J_KEEP, "data/journals/08_25_2026_journal_landscape_by_journal_385_public.csv")):
        text, _ = read_text(src)
        rows = [dict(r) for r in csv.DictReader(io.StringIO(text))]
        keep = [c for c in keep if c in (rows[0] if rows else {})]
        recs = []
        for r in rows:
            o = {}
            for c in keep:
                v = r.get(c) or ""
                if c == "journal":
                    try:
                        if int(float(r.get("n_papers") or 0)) < K:
                            v = ""
                    except ValueError:
                        v = ""
                # ⚠ jcr_note reads "Oncology 109/241 Q2; Public..." for a ranked
                # journal: a category-and-rank string that fingerprints the
                # venue. The figure parses it only to say why a journal has no
                # 2022 quartile, so it survives only on those rows.
                if c == "jcr_note":
                    v = "" if (r.get("jcr_2022_quartile") or "") != "None" \
                        else canonical_jcr_note(v)
                o[c] = scrub_text(v, id_map, name_rx)
            recs.append(o)
        # ⚠ A subject field or a publisher country carried by one paper narrows
        # the same way a single-paper country does: SCImago lists which journals
        # sit in a field, and PubMed lists the 2022 Saudi papers in them.
        for col in ("field", "domain", "publisher_country"):
            if col in keep:
                collapse_column(recs, col, None, stats)
        rng.shuffle(recs)
        dst = os.path.join(PUB, dst_rel)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        with open(dst, "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=keep)
            w.writeheader()
            w.writerows(recs)
        # ⚠ These are published values, so the entity scrub must leave them in
        # the code. "Medicine" is both a subject field this table publishes and
        # a journal in the reference list; redacted from the code, the figure's
        # own assertion compared "[NAME-REDACTED]" against a real field value
        # and failed. Written before the entity list is built, for that reason.
        for r in recs:
            for v in r.values():
                if isinstance(v, str) and 4 <= len(v) <= 80:
                    PUBLISHED_VALUES.add(v.strip().lower())
        out[dst_rel] = len(recs)
        named = sum(1 for r in recs if r.get("journal"))
        if "by_journal" in dst_rel:
            out["named_journals"] = named
    return out


def write_gitignore():
    lines = [GITIGNORE_HEAD, "!outputs/tables/", "outputs/tables/*"]
    lines += ["!outputs/tables/%s" % f for f in SEED_TABLES]
    open(os.path.join(PUB, ".gitignore"), "w", encoding="utf-8",
         newline="\n").write("\n".join(lines) + "\n")
    return len(SEED_TABLES)


def write_withheld_manifest(shipped):
    """Name every data file that exists privately and does not ship, so its
    absence is a statement rather than a gap a reader has to notice."""
    lines = ["# Data held back from this repository", "",
             "Every file below exists in the private tree and is not published.",
             "The reason is the same in most cases: it records something about a",
             "particular paper, a particular institution or a particular person,",
             "and no analysis in the manuscript reads it.", "",
             "| file | rows | why |", "|---|---|---|"]
    reasons = [
        ("data/screening", "screening ledger: which papers were looked at and excluded, with reasons quoting the paper"),
        ("data/assignment", "reviewer assignment workbooks: exposure and outcome descriptions, one per paper"),
        ("data/adjudication", "adjudication worklists: verbatim quotes and rationales about named papers"),
        ("data/authors", "author-position records: names, affiliation strings, cities, countries"),
        ("data/journals", "journal reference tables: SCImago and JCR metadata that identifies the venue"),
        ("data/outcomes", "measured-outcome text, one phrase per paper"),
        ("data/calibration", "reviewer worksheets not read by any published display"),
        ("data/analysis", "intermediate analysis vintages superseded by the shipped dataset"),
        ("data/provenance", "build logs naming source files and paths"),
        ("data/quality-control", "working scratch"),
        ("data/tables", "intermediate tables not read by any published display"),
    ]
    n = 0
    for base, dirs, files in os.walk(os.path.join(ROOT, "data")):
        dirs[:] = [d for d in dirs if d not in {"__pycache__", "_superseded"}]
        for fn in sorted(files):
            if os.path.splitext(fn)[1].lower() not in (".csv", ".xlsx", ".json"):
                continue
            rel = os.path.relpath(os.path.join(base, fn), ROOT).replace(os.sep, "/")
            if rel in shipped:
                continue
            why = next((w for p, w in reasons if rel.startswith(p)), "not read by any published display")
            rows = ""
            if fn.lower().endswith(".csv"):
                try:
                    rows = sum(1 for _ in open(os.path.join(base, fn),
                                               encoding="utf-8", errors="replace")) - 1
                except Exception:
                    rows = ""
            lines.append("| `%s` | %s | %s |" % (rel, rows, why))
            n += 1
    lines += ["", "%d files. The complete dataset, identifiers included, goes to the" % n,
              "journal's editors and peer reviewers as supplementary material."]

    # ⚠ Code is withheld by name in exactly one place, and silently dropping it
    # would be the kind of gap this manifest exists to prevent. Described by what
    # the scripts are for, not by what they contain: spelling out the method here
    # would restore most of the disclosure risk the exclusion is there to remove.
    lines += ["", "## Analysis code held back", "",
              "The sampling-provenance and inversion scripts are not published.",
              "They were written to audit how the 2023 and 2026 draws were made,",
              "and together they carry enough detail about the draw to narrow which",
              "records it returned. The sampling script the study actually ran,",
              "`code/sampling/2023_12_21_Final_Query_211223.R`, IS published, with",
              "its random seed withheld for the same reason. Their findings are",
              "reported in the supplementary methods.", "",
              "| file | why |", "|---|---|"]
    for fn in sorted(CODE_EXCLUDE_FILES):
        lines.append("| `code/sampling/%s` | sampling provenance and inversion |" % fn)
    open(os.path.join(PUB, "MANIFEST_WITHHELD.md"), "w", encoding="utf-8").write(
        "\n".join(lines) + "\n")
    return n


def main():
    global ENTITY_RX
    os.chdir(ROOT)
    id_map = build_map()
    name_rx = re.compile(r"(?<![A-Za-z])(%s)(?![A-Za-z])" % "|".join(REVIEWER_NAMES))
    print("surrogates: %d papers  (STUDY-0001 .. STUDY-%04d)"
          % (len(id_map), len(id_map)))
    json.dump({"seed": SEED, "map": id_map},
              open(MAP_OUT, "w", encoding="utf-8"), indent=1, sort_keys=True)
    print("id map -> private/  (never commit)\n")

    # A clean data tree. Anything left over from the old, wider build would
    # otherwise survive as an orphan that nothing here is accountable for, and
    # the worst of those orphans was a figure PNG naming 116 institutions.
    # ⚠ OneDrive marks synced directories read-only often enough that a plain
    # rmtree fails halfway, which would leave exactly the mixture of old and new
    # files this is meant to prevent.
    def _force(fn, path, exc):
        try:
            os.chmod(path, 0o700)
            fn(path)
        except Exception:
            print("  !! could not remove %s" % os.path.relpath(path, PUB))
    # ⚠⚠ `code` AND `docs` TOO. Only data and outputs were cleared until
    # 2026-09-02, so a file that stopped being shipped stayed in the tree for
    # ever: excluding code/manuscript removed 18 files from the build and left
    # all 18 sitting in the repository, which is precisely the leak the clean
    # was meant to prevent. Removal has to be a rebuild operation like any other.
    # ⚠⚠ NOT `outputs`. It used to be wiped here as well, on the same
    # stale-artefact argument, and that was wrong twice over: outputs/ is
    # gitignored apart from the 15 seed tables, so nothing stale in it can ever
    # reach the repository, and wiping it means every builder change forces the
    # whole sensitivity chain to recompute. That is 55 minutes for the tipping
    # point alone, and it turned five small fixes into five hours of waiting.
    # The seed tables are rewritten below in any case.
    for d in ("data", "code", "docs"):
        p = os.path.join(PUB, d)
        if os.path.isdir(p):
            shutil.rmtree(p, onexc=_force)

    stats = {"cols_dropped": 0, "code_ids": 0, "collapsed_values": 0,
             "collapsed_rows": 0, "derived_cols": 0}
    counts = {"csv": 0, "xlsx": 0, "code": 0, "failed": 0}
    shipped = set()

    jobs = [(rel, rel, spec) for rel, spec in SHIP.items()]
    jobs += [(s, d, spec) for s, d, spec in RELOCATED]
    jobs += [("outputs/tables/" + f, "outputs/tables/" + f, dict(kind="derived"))
             for f in SEED_TABLES]

    for src, dstrel, spec in jobs:
        if not os.path.exists(src):
            print("  !! source missing: %s" % src)
            counts["failed"] += 1
            continue
        dst = os.path.join(PUB, dstrel)
        try:
            if src.lower().endswith(".xlsx"):
                do_xlsx(src, dst, spec, id_map, name_rx, stats)
                counts["xlsx"] += 1
            elif src.lower().endswith(".json"):
                do_json(src, dst, id_map, name_rx)
                counts["json"] = counts.get("json", 0) + 1
            else:
                do_csv(src, dst, spec, id_map, name_rx, stats)
                counts["csv"] += 1
            shipped.add(src.replace(os.sep, "/"))
        except Exception as e:
            counts["failed"] += 1
            # never fall back to copying the original: it would put an
            # un-scrubbed file into the public tree
            if os.path.exists(dst):
                os.remove(dst)
            print("  !! %-58s %s" % (dstrel[:58], str(e)[:70]))

    # ⚠ Derived tables BEFORE the entity list, for the same reason the entity
    # list comes after the data: what the repository publishes as a value is
    # what its code is allowed to keep saying.
    jl = write_journal_landscape_unkeyed(id_map, name_rx, stats)
    if jl:
        print("journal landscape, unkeyed and shuffled: %d papers, %d journals, "
              "%d named"
              % (jl.get("data/journals/08_25_2026_journal_landscape_by_paper_385_public.csv", 0),
                 jl.get("data/journals/08_25_2026_journal_landscape_by_journal_385_public.csv", 0),
                 jl.get("named_journals", 0)))
    agg = write_country_aggregates()
    if agg:
        print("country aggregates written: %d papers, %d author positions, "
              "%d regions" % (agg["n_papers"], agg["n_author_positions"],
                              len(agg["region_papers"])))

    # The entity list is built only once the data is written, because what the
    # data publishes is exactly what the code is allowed to keep saying.
    ents = [e for e in load_named_entities()
            if e.strip().lower() not in PUBLISHED_VALUES]
    if ents:
        ENTITY_RX = re.compile(r"(?<![\w])(%s)(?![\w])"
                               % "|".join(re.escape(e) for e in ents), re.I)
        print("named entities scrubbed from code : %d of %d (the rest are "
              "published values)" % (len(ents), len(load_named_entities())))

    for d in CODE_DIRS:
        for base, subs, files in os.walk(d):
            subs[:] = [s for s in subs if not code_excluded(os.path.join(base, s))]
            if code_excluded(base):
                continue
            for fn in sorted(files):
                if os.path.splitext(fn)[1].lower() not in CODE_EXT:
                    continue
                if fn in CODE_EXCLUDE_FILES:
                    stats["code_files_withheld"] = stats.get("code_files_withheld", 0) + 1
                    continue
                src = os.path.join(base, fn)
                rel = os.path.relpath(src, ROOT)
                dst = os.path.join(PUB, rel)
                try:
                    do_code(src, dst, id_map, name_rx, stats)
                    stats["patched"] = stats.get("patched", 0) + apply_patches(rel, dst)
                    counts["code"] += 1
                except Exception as e:
                    counts["failed"] += 1
                    print("  !! %-58s %s" % (rel[:58], str(e)[:70]))

    for d in EXTRA_COPY:
        if os.path.isdir(d):
            for base, _, fs in os.walk(d):
                for fn in fs:
                    src = os.path.join(base, fn)
                    dst = os.path.join(PUB, os.path.relpath(src, ROOT))
                    os.makedirs(os.path.dirname(dst), exist_ok=True)
                    shutil.copy2(src, dst)
                    counts["copied"] = counts.get("copied", 0) + 1
            print("copied verbatim (contains no identifier): %s" % d)

    withheld = write_withheld_manifest(shipped)
    seeds = write_gitignore()

    print("\nshipped: %d csv, %d xlsx, %d code   (failed %d)"
          % (counts["csv"], counts["xlsx"], counts["code"], counts["failed"]))
    print("columns dropped by allowlist : %d" % stats["cols_dropped"])
    print("sampling seeds withheld      : %d" % stats.get("sampling_seeds", 0))
    print("code files withheld by name  : %d of %d listed"
          % (stats.get("code_files_withheld", 0), len(CODE_EXCLUDE_FILES)))
    print("values collapsed below k=%d   : %d" % (K, stats["collapsed_values"]))
    print("count rows merged into Other : %d" % stats["collapsed_rows"])
    print("derived columns added        : %d" % stats["derived_cols"])
    print("hard-coded ids rewritten     : %d" % stats["code_ids"])
    print("journal/institution names cut from code : %d occurrence(s) of %d name(s)"
          % (sum(ENTITY_HITS.values()), len(ENTITY_HITS)))
    for nm, n in ENTITY_HITS.most_common(5):
        print("     %-52s x%d" % (nm[:52], n))
    for fp, n in ENTITY_FILES.most_common(5):
        print("     in %-49s x%d" % (fp[-49:], n))
    print("public-repo patches applied  : %d" % stats.get("patched", 0))
    print("data files held back         : %d  (MANIFEST_WITHHELD.md)" % withheld)
    print(".gitignore written, %d seed tables kept out of the outputs/ rule" % seeds)
    print("\nnow run all three gates:")
    print("  python public-repo/tools/verify_no_identifiers.py")
    print("  python public-repo/tools/verify_k_anonymity.py")
    print("  python public-repo/tools/verify_reproduces.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())

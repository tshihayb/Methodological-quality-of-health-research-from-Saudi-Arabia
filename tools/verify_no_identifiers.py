"""
Scan the public repository for anything that could identify an appraised paper.

This is the release gate. It walks EVERY file the repository would publish, not
only the ones the de-identification tool touched, because a leak is as likely to
sit in a stray CSV, a cached JSON or a committed output as in the datasets.

FAILS on
  * a real PMID from this study, checked against the id map
  * a DOI, or a pubmed / doi.org / europepmc URL
  * an ISSN
  * a reviewer's given name, which must never leave the private tree
  * a literal random seed inside code/sampling. Beside the query a seed
    regenerates the drawn PMIDs, so it is a re-identification key rather than a
    reproducibility parameter. Seeds elsewhere key an analysis and are required.
  * any of the sampling-provenance scripts withheld by name. They carry the draw
    mechanism, the exact frame size and a worked inversion, which together make
    even a redacted seed guessable.

WARNS on
  * any other 8-digit number. Dates such as 20200829 take the shape of a PMID
    without being one. These are surfaced rather than failed, because a rule that
    cries wolf on every date gets switched off, and then it catches nothing.

A pass proves no DIRECT identifier is present. It does NOT prove anonymity: a
reader holding the 2022 Saudi PubMed frame could narrow some rows by combining
task, quartile and author count. That limit is stated in the README rather than
defended against here, because defending against it would mean deleting the
stratifiers the data exist to support.

    python public-repo/tools/verify_no_identifiers.py
Exit 0 clean, 1 if anything fails.
"""
import os, re, sys, json

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
PUB = os.path.join(ROOT, "public-repo")
MAP = os.path.join(ROOT, "private", "public_repo_id_map_DO_NOT_COMMIT.json")

REVIEWERS = ["Tala", "Reham", "Turki", "Esraa", "Saleh", "Rami", "Lubna",
             "Musfer", "Dana", "Ali", "Maha", "Arwa", "Roah", "Alhanouf",
             "Nouf", "Saad", "yalbogami",
             # ⚠ the repository owner's own username. Absent from this list,
             # the gate passed a scratch path that carried it in three scripts
             # and in four compiled .pyc files.
             "Tshih"]

TEXT_EXT = {".csv", ".json", ".md", ".txt", ".r", ".py", ".yml", ".yaml",
            ".tsv", ".html", ".xml", ".gitignore", "",
            # compiled Python embeds the absolute source path it was built from
            ".pyc"}

# ⚠ A WORKBOOK IS NOT A BINARY BLOB. Until 2026-09-01 every .xlsx and .docx was
# counted as "skipped binary", which meant the two supplementary tables and both
# Word tables shipped without ever being scanned. They turned out clean; that was
# luck, not a check. Their text is extracted and scanned like everything else.
OFFICE_EXT = {".xlsx", ".docx"}


def office_text(path):
    """The visible strings inside a workbook or a Word document."""
    ext = os.path.splitext(path)[1].lower()
    try:
        if ext == ".xlsx":
            import openpyxl
            wb = openpyxl.load_workbook(path, data_only=True, read_only=True)
            out = []
            for ws in wb.worksheets:
                for row in ws.iter_rows(values_only=True):
                    out += [v for v in row if isinstance(v, str)]
            return "\n".join(out)
        import zipfile
        with zipfile.ZipFile(path) as z:
            xml = z.read("word/document.xml").decode("utf-8", "replace")
        return re.sub(r"<[^>]+>", " ", xml)
    except Exception:
        return None

DOI = re.compile(r"10\.\d{4,9}/\S+")
URL = re.compile(r"(pubmed\.ncbi\.nlm\.nih\.gov|doi\.org|europepmc\.org)", re.I)
ISSN = re.compile(r"(?<!\d)\d{4}-\d{3}[\dXx](?!\d)")
YEARS = re.compile(r"^(19|20)\d{2}-(19|20)\d{2}$")     # 2014-2020 is a range
EIGHT = re.compile(r"(?<!\d)\d{8}(?!\d)")
# a literal seed inside code/sampling. `set.seed(SAMPLING_SEED)`, the redacted
# form the builder writes, is a name rather than a number and does not match.
SAMPLING_SEED = re.compile(r"set\.seed\(\s*\d+L?\s*\)|"
                           r"(?:np\.random\.)?(?:random\.)?seed\(\s*\d+\s*\)|"
                           r"default_rng\(\s*\d+\s*\)")

# ⚠⚠ WITHHELD BY NAME. Kept in step with CODE_EXCLUDE_FILES in
# build_public_repo.py, and checked here as well so that a file copied in by
# hand, or left behind by an older build, is still caught. Between them these
# publish the draw mechanism, the exact frame size and a worked inversion that
# recovers a frame from a draw, which together make a redacted seed guessable.
WITHHELD_FILES = {
    "2026_07_21_Final_Query_topup20.R",
    "09_05_2026_recover_topup_frame.R",
    "09_05_2026_invert_1000_search.R",
    "09_05_2026_frame_reproduction_check.R",
    "09_05_2026_make_topup_script.py",
    "09_07_2026_rng_state_sweep.R",
    "09_07_2026_sample_uniformity_test.R",
    "09_07_2026_rebuild_study_sample.R",
    "09_07_2026_retraction_check.py",
    "09_07_2026_absentee_eligibility_check.py",
    "09_07_2026_resolve_absent_frame_paper.py",
    # calibration provenance: invoke SAS and read from `codes audit/`, neither of
    # which ships, so they would be dangling references in the public tree
    "09_07_2026_sas_kalpha_assemble.py",
    "09_07_2026_sas_kalpha_parse.py",
    "09_07_2026_rebuild_recoded_long.R",
}
NAME = re.compile(r"(?<![A-Za-z])(%s)(?![A-Za-z])" % "|".join(REVIEWERS))


# ⚠⚠ The gate could not see personal names until 2026-09-01. Columns called
# `last` and `fore` held a real surname and given name per author, and no pattern
# here matched them, so the repository passed while naming people. Structural
# rules catch structural identifiers; a human name has no structure. This checks
# for the SHAPE of a name table instead: a column whose name suggests a person
# and whose values are short alphabetic tokens.
NAME_COLS = ("last", "fore", "forename", "given", "surname", "initials",
             "author_name", "authorname", "first_name", "lastname")


def name_like_columns(path):
    import csv as _csv
    try:
        with open(path, encoding="utf-8-sig", newline="") as f:
            rd = _csv.DictReader(f)
            cols = rd.fieldnames or []
            rows = [r for _, r in zip(range(40), rd)]
    except Exception:
        return []
    out = []
    for c in cols:
        if not c or c.strip().lower() not in NAME_COLS:
            continue
        vals = [(r.get(c) or "").strip() for r in rows]
        vals = [v for v in vals if v]
        if not vals:
            continue
        alpha = sum(1 for v in vals
                    if re.fullmatch(r"[A-Za-z][A-Za-z'.\- ]{1,40}", v))
        if alpha >= 0.7 * len(vals):
            out.append((c, vals[0][:24]))
    return out


def real_pmids():
    if not os.path.exists(MAP):
        print("!! no id map at %s" % MAP.replace(ROOT, "").lstrip("\\/"))
        print("   real PMIDs cannot be checked; run build_public_repo.py first.")
        return None
    with open(MAP, encoding="utf-8") as f:
        return set(json.load(f)["map"].keys())


def main():
    if not os.path.isdir(PUB):
        print("no public-repo directory")
        return 1
    pm = real_pmids()
    if pm is None:
        return 1
    print("scanning public-repo/  against %d known study PMIDs\n" % len(pm))

    fails, warns, scanned, skipped = [], [], 0, 0
    for base, dirs, files in os.walk(PUB):
        dirs[:] = [d for d in dirs if d not in {".git", "__pycache__", "outputs"}]
        for fn in sorted(files):
            p = os.path.join(base, fn)
            rel = os.path.relpath(p, PUB).replace(os.sep, "/")
            ext = os.path.splitext(fn)[1].lower()
            if ext in OFFICE_EXT:
                t = office_text(p)
                if t is None:
                    print("   !! unreadable, so unscanned: %s" % rel)
                    fails.append((rel, 1, "could not be scanned", ext))
                    continue
            elif ext not in TEXT_EXT:
                skipped += 1
                continue
            else:
                try:
                    t = open(p, encoding="utf-8", errors="replace").read()
                except Exception:
                    skipped += 1
                    continue
            scanned += 1

            def add(dst, ln, label, s):
                dst.append((rel, ln, label, s))

            def lineno(i):
                return t[:i].count("\n") + 1

            # The tools and the README describe these patterns in order to guard
            # against them, so they must not trip over their own documentation.
            # ⚠⚠ BUT THEY SHIP, and exempting them WHOLESALE is a hole the exact
            # size of the folder that holds this gate. On 2026-09-08 a real study
            # PMID sat in a withheld-file list inside two of these tools and this
            # gate saw only the fourth copy, in MANIFEST_WITHHELD.md, which is
            # outside the exemption. Had the manifest not happened to name the same
            # file, the leak would have shipped behind three green gates.
            # A real study PMID is never legitimate documentation, so that one
            # check runs here too. The pattern-shaped checks (DOI, ISSN, URL,
            # reviewer names, and the 8-digit warning) stay exempt, because those
            # are what the rulebook is made of.
            if rel.startswith("tools/") or rel.endswith("README.md"):
                for m in EIGHT.finditer(t):
                    if m.group(0) in pm:
                        add(fails, lineno(m.start()), "REAL PMID from the study",
                            m.group(0))
                continue

            for m in DOI.finditer(t):
                add(fails, lineno(m.start()), "DOI", m.group(0)[:50])
            for m in URL.finditer(t):
                # a bare API hostname in fetch code is not an identifier; a URL
                # with an id hanging off it is. Judge by what follows.
                tail = t[m.end():m.end() + 40]
                if not re.match(r"[/=]?\s*[\w./-]*\d{6}", tail):
                    continue
                add(fails, lineno(m.start()), "URL carrying an identifier", m.group(0))
            for m in ISSN.finditer(t):
                if YEARS.match(m.group(0)):
                    continue                      # 2014-2020 is a year range
                # ".sas:2608-2925" is a source line range, not a journal ISSN
                if m.start() and t[m.start() - 1] == ":":
                    continue
                add(fails, lineno(m.start()), "ISSN", m.group(0))
            for m in NAME.finditer(t):
                add(fails, lineno(m.start()), "reviewer given name", m.group(0))
            # ⚠ THE SAMPLING SEED IS A KEY. Added 2026-09-07. Published beside the
            # query, a literal seed regenerates the drawn PMIDs, so surrogating
            # the identifiers written in the script does not contain it. This is
            # not hypothetical: the 2026-07-21 top-up of 20 was re-derived exactly
            # that way (rank correlation 1.0000 at N = 5,530) and three of those
            # twenty are in the analysed 385. Scoped to code/sampling, because
            # every other seed here keys an analysis, not the identity of a paper.
            if "/sampling/" in "/" + rel:
                for m in SAMPLING_SEED.finditer(t):
                    add(fails, lineno(m.start()), "literal sampling seed", m.group(0))
            if os.path.basename(rel) in WITHHELD_FILES:
                add(fails, 1, "file withheld by name is present", os.path.basename(rel))
            if rel.lower().endswith(".csv"):
                for col, ex in name_like_columns(p):
                    add(fails, 1, "column of personal names", "%s = %r" % (col, ex))
            for m in EIGHT.finditer(t):
                if m.group(0) in pm:
                    add(fails, lineno(m.start()), "REAL PMID from the study", m.group(0))
                else:
                    add(warns, lineno(m.start()), "8-digit, not a study PMID", m.group(0))

    print("scanned %d text files, skipped %d binary\n" % (scanned, skipped))
    # ⚠ What is left unscanned is images, and an image is where the worst leak
    # of 2026-09-01 lived: a supplementary figure that named 116 institutions,
    # 56 of them with a single paper. No scanner here will ever read that. The
    # defence has to sit upstream, in the data the figure is drawn from, which
    # is what verify_k_anonymity.py checks.
    if skipped:
        print("   %d image or PDF file(s) cannot be scanned for text. What a figure\n"
              "   DRAWS is controlled at the data layer and by gate 2, not here.\n"
              % skipped)

    if warns:
        seen = set()
        uniq = [(r, l, k, s) for r, l, k, s in warns
                if not ((r, s) in seen or seen.add((r, s)))]
        print("%d warning(s) over %d distinct value(s):" % (len(warns), len(uniq)))
        for rel, ln, label, s in uniq[:12]:
            print("   %-52s line %-6s %s  %s" % (rel, ln, label, s))
        if len(uniq) > 12:
            print("   ... %d more" % (len(uniq) - 12))
        print()

    if not fails:
        print("PASS: no direct identifier in anything the repository would publish.")
        print("      Not a claim of anonymity; see the README on re-identification.")
        return 0

    seen = set()
    uniq = [(r, l, k, s) for r, l, k, s in fails
            if not ((r, k) in seen or seen.add((r, k)))]
    print("FAIL: %d occurrence(s) of %d kind(s)\n" % (len(fails), len(uniq)))
    for rel, ln, label, s in uniq[:40]:
        print("   %-52s line %-6s %-26s %s" % (rel, ln, label, s))
    return 1


if __name__ == "__main__":
    sys.exit(main())

"""
Scan the public repository for anything that could identify an appraised paper.

This is the release gate. It walks EVERY file the repository would publish, not
only the ones the de-identification tool touched, because a leak is as likely to
sit in a stray CSV, a cached JSON or a committed output as in the datasets.

FAILS on
  * a real PMID from this study, checked against the id map, in a file's text or
    in its PATH: a file name is content too
  * a DOI, or a pubmed / doi.org / europepmc URL
  * a `doi` or `pii` key given a literal value. A DOI suffix names the paper as
    exactly as the whole DOI does and has no shape a pattern can match, so the
    DOI rule passes it. What gives it away is the key it is assigned to.
  * a PMC accession or a trial registration number. The builder redacts both;
    this checks that it did, and it checks the tools as well
  * an ISSN
  * a reviewer's given name or surname, which must never leave the private tree.
    They are read from the private key when the gate runs, so that this file,
    which ships, names no one
  * a literal random seed inside code/sampling. Beside the query a seed
    regenerates the drawn PMIDs, so it is a re-identification key rather than a
    reproducibility parameter. Seeds elsewhere key an analysis and are required.
  * any of the code files withheld by name, or a list of them here that has
    drifted from the builder's. The sampling-provenance scripts carry enough
    about the draw to narrow which records it returned.
  * a study surrogate in a code file that no published display needs, that is,
    one off the display chain the builder declares, or in a code file's name;
    and a display-chain script that is missing. A script that names a paper
    records something about it, and ships only if a figure or table needs it.

WARNS on
  * any other 8-digit number. Dates such as 20200829 take the shape of a PMID
    without being one. These are surfaced rather than failed, because a rule that
    cries wolf on every date gets switched off, and then it catches nothing.
    EVERY one is printed, the ones that are neither a date nor part of a decimal
    number first and one to a line. A list cut short hides exactly the entry
    worth reading.

A pass proves no DIRECT identifier is present. It does NOT prove anonymity: a
reader holding the 2022 Saudi PubMed frame could narrow some rows by combining
task, quartile and author count. That limit is stated in the README rather than
defended against here, because defending against it would mean deleting the
stratifiers the data exist to support.

    python public-repo/tools/verify_no_identifiers.py
Exit 0 clean, 1 if anything fails.
"""
import datetime, os, re, sys, json

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
PUB = os.path.join(ROOT, "public-repo")
MAP = os.path.join(ROOT, "private", "public_repo_id_map_DO_NOT_COMMIT.json")

# ⚠ NO REVIEWER IS NAMED IN THIS FILE, because this file ships. Given names and
# surnames are read from the private key, through the builder, when the gate
# runs. What stays here is two home-directory usernames, which are not
# reviewers, so that a scratch path carrying one of them does not pass.
USERNAMES = ["yalbogami", "Tshih"]

TEXT_EXT = {".csv", ".json", ".md", ".txt", ".r", ".py", ".yml", ".yaml",
            ".tsv", ".html", ".xml", ".gitignore", "", ".cff",
            # compiled Python embeds the absolute source path it was built from
            ".pyc"}

# ⚠ A WORKBOOK IS NOT A BINARY BLOB. The text of every .xlsx and .docx is
# extracted and scanned like everything else.
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

# ⚠⚠ A FRAGMENT HAS NO SHAPE. The DOI rule above needs the
# `10.xxxx/` prefix, so a DOI suffix written on its own passes it, and a suffix
# can be anything: a long number, a short code of letters and digits, an article
# number. It still names the paper, because the prefix is the publisher's. The
# one thing such a value does have is the key it is assigned to, so that is what
# this matches: `doi = "..."`, `"doi": "..."`, `doi <- c("...", "...")`,
# `pii == "..."`. Any literal fails unless it is made only of the builder's
# redaction tokens, or is one of the three things below that cannot be a
# fragment of anything: nothing at all, a word for "missing", or the key's own
# name used as a column label.
KEY_NAME = r"(?:[a-z0-9]+_)*(?:doi|pii)s?(?:_[a-z0-9]+)*"
KEYED_ID = re.compile(
    r"(?i)(?<![A-Za-z0-9_])([\"']?)(%s)([\"']?)[\])]{0,2}\s*(?:==?|!=|<-|:|%%in%%)\s*" % KEY_NAME)
LITERAL = re.compile(r"\"([^\"\n]*)\"|'([^'\n]*)'")
NOT_A_VALUE = re.compile(r"\[[A-Z-]+-REDACTED\]|https?://(?:dx\.)?doi\.org/?|\s+")
NO_VALUE = re.compile(r"(?i)^(?:na|n/a|nan|none|null|nil|missing|unknown|%s)$" % KEY_NAME)
# the same key in a YAML file, where a value needs no quotes
KEYED_ID_YAML = re.compile(r"(?im)^\s*(?:-\s*)?((?:doi|pii))\s*:[ \t]*([^\s\"'].*?)[ \t]*$")
YAML_EXT = {".cff", ".yml", ".yaml"}

# What the builder redacts, verified here as well. A PMC accession
# names a paper as exactly as a PMID; a trial registration names the trial and
# therefore the paper. Neither is ever documentation, so both are checked in
# the tools and the README too.
PMC = re.compile(r"\bPMC\d{5,}\b")
TRIAL = re.compile(r"\b(?:NCT|ISRCTN|ACTRN|CTRI|IRCT|ChiCTR|PACTR)[\w/-]*\d{6,}\b")
# A paper's public code. Fine in data, where it keys the rows; in code it is a
# ruling about that paper, allowed only where a published display needs it.
SURROGATE = re.compile(r"STUDY-\d{4}")

# ⚠⚠ WITHHELD BY NAME. Kept in step with CODE_EXCLUDE_FILES in
# build_public_repo.py, and checked here as well so that a file copied in by
# hand, or left behind by an older build, is still caught. Between them the
# sampling-provenance scripts carry enough about the draw to narrow which
# records it returned.
# ⚠ "In step" is enforced, not trusted: the run fails if this set and the
# builder's differ in either direction. The two are kept apart on purpose, so
# that deleting a line from one of them is noticed by the other.
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
    # exploratory calibration scripts that open folders outside the repository
    "Calibration figures.R",
    "Calibration figures_all_percent.R",
    "Calibration figures_kappa_variants.R",
    "Calibration_like_to_like_data.R",
    # full-text retrieval: works on the private document store, which does not
    # ship, and records where individual papers were obtained
    "07_24_2026_fetch_new_paper_fulltext.R",
    # the outcome classifier: a lookup from each paper's outcome, verbatim, to
    # its category, so it names papers by their own words
    "08_08_2026_classify_outcomes.py",
    # an early summary page of the outcomes, whose prose describes some papers
    # singly, by what they measured
    "08_08_2026_gen_outcomes_artifact.py",
    # the merge of JCR quartiles, which names journals that carry a single paper
    "07_25_2026_jcr_merge_385.py",
}


def whole_word(words):
    return re.compile(r"(?<![A-Za-z])(%s)(?![A-Za-z])" % "|".join(
        sorted((re.escape(w) for w in words), key=len, reverse=True)))

# ⚠ CITATION METADATA NAMES PEOPLE ON PURPOSE. `.zenodo.json`
# and `CITATION.cff` exist to list the authors, their ORCID iDs and the archive's
# own Zenodo DOI, so three pattern checks cannot apply to them as written: the
# reviewer given names (the appraisers are authors), the ISSN shape (every ORCID
# iD contains two) and the DOI shape. Each is relaxed only as far as that: names
# are allowed, ISSN-shaped hits are allowed only INSIDE a full ORCID iD, and a DOI
# only if it is this project's own 10.5281/zenodo. DOI. The PMID check and every
# other rule still run. Listing the authors cannot tie a person to an appraisal:
# the public reviewer codes R1-R13 are not in alphabetical order.
# Exact root paths only, never a pattern, so no other file can borrow this.
CITATION_FILES = {".zenodo.json", "CITATION.cff"}
# ⚠ A SURNAME IS CHECKED AS WELL AS A GIVEN NAME. Replacing a
# given name with its public code leaves "R4 <surname>" wherever the private
# text had the full name, which is the code and the person on one line. The
# three root files that give the reference to cite list the authors' surnames on
# purpose, and only they may.
AUTHOR_LISTS = CITATION_FILES | {"LICENSE-DATA"}
ORCID = re.compile(r"\d{4}-\d{4}-\d{4}-\d{3}[\dXx]")
OWN_DOI = re.compile(r"10\.5281/zenodo\.\d+")


# ⚠⚠ Structural rules catch structural identifiers; a human name has no
# structure. This checks for the SHAPE of a name table instead: a column whose
# name suggests a person and whose values are short alphabetic tokens.
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


def builder_declarations():
    """What the builder itself declares: the code it withholds by name, the seed
    tables it commits under outputs/, who the reviewers are, and the display
    chain (the scripts a published display needs).

    The first is COMPARED with the copy kept here. The others are read rather
    than restated, as gate 2 reads the builder's `kind`: two lists drift, and
    the reviewers must not be written in a file that ships at all."""
    # no __pycache__ in a published tree: a .pyc embeds the absolute path it was
    # compiled from, which carries the analyst's home directory and username
    sys.dont_write_bytecode = True
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    try:
        import build_public_repo as B
    except Exception as e:                       # a gate that cannot read the
        print("!! cannot import the builder: %s" % e)   # declaration must fail
        return None
    given, _withdrew, surnames = B.load_reviewers()     # stops without the key
    return (set(B.CODE_EXCLUDE_FILES), list(B.SEED_TABLES), given, surnames,
            B.display_chain())


def publishable_dirs(seed_tables):
    """(directory, file names) for everything the repository would publish."""
    for base, dirs, files in os.walk(PUB):
        dirs[:] = [d for d in dirs if d not in {".git", "__pycache__", "outputs"}]
        yield base, files
    # ⚠ outputs/ is left out of the walk because what a run writes there is
    # generated and ignored. The seed tables are the exception: they are
    # committed, so they are published, and so they are read.
    tables = os.path.join(PUB, "outputs", "tables")
    yield tables, [f for f in seed_tables if os.path.exists(os.path.join(tables, f))]


def open_quote(s):
    """The quote character a line is still inside at its end, or None.

    An apostrophe between two letters is part of a word, not a quote: without
    that, "the paper's" would swallow the rest of a comment line."""
    q, i = None, 0
    while i < len(s):
        ch = s[i]
        if q:
            if ch == "\\":
                i += 1
            elif ch == q:
                q = None
        elif ch == '"' or (ch == "'" and not (s[i - 1:i].isalpha() and s[i + 1:i + 2].isalpha())):
            q = ch
        i += 1
    return q


def keyed_literals(t, citation):
    """(position, key, value) for every literal given to a `doi` or `pii` key
    that is a value rather than a redaction."""
    out = []
    for m in KEYED_ID.finditer(t):
        # ⚠ The key has to be a key. In `print("has DOI:", n)` the word sits
        # INSIDE a string and the quote after the colon closes that string
        # rather than opening a value. So: either the key is bare and outside
        # any string, or it is quoted on both sides as a dictionary key is.
        if m.group(1) != m.group(3):
            continue
        if open_quote(t[t.rfind("\n", 0, m.start()) + 1:m.start()]):
            continue
        eol = t.find("\n", m.end())
        rest = t[m.end():eol if eol != -1 else len(t)]
        head = rest.lstrip()
        if head[:1] and head[:1] in "\"'":
            lits = list(LITERAL.finditer(rest))[:1]
        elif re.match(r"(?:\w+\s*)?[(\[{]", head):
            # a vector, a list or a call: every literal up to the bracket that
            # closes it, which may be several lines down
            rest = t[m.end():m.end() + 4000]
            depth, end = 0, len(rest)
            for i, ch in enumerate(rest):
                if ch in "([{":
                    depth += 1
                elif ch in ")]}":
                    depth -= 1
                    if depth == 0:
                        end = i
                        break
            lits = [x for x in LITERAL.finditer(rest) if x.start() < end]
        else:
            continue                               # a name, not a literal
        for x in lits:
            v = x.group(1) if x.group(1) is not None else x.group(2)
            if not NOT_A_VALUE.sub("", v) or NO_VALUE.match(v.strip()):
                continue
            if citation and OWN_DOI.fullmatch(re.sub(r"^https?://(?:dx\.)?doi\.org/", "", v)):
                continue
            out.append((m.start(), m.group(2), v))
    return out


def date_shaped(s):
    """20260829, 08292026 or 29082026: a calendar date between 1900 and 2099."""
    for fmt in ("%Y%m%d", "%m%d%Y", "%d%m%Y"):
        try:
            d = datetime.datetime.strptime(s, fmt)
        except ValueError:
            continue
        if 1900 <= d.year <= 2099:
            return True
    return False


def eight_kind(t, m):
    """Sort an 8-digit run that is not a study PMID: a date, the fractional part
    of a decimal number, or neither. Only the last kind is worth a line each.

    ⚠ "Decimal" means ONE dot: 0.58333333 is a number, while the tail of
    12.3.45678901 is an identifier with dots in it, and stays in the group that
    is read."""
    if date_shaped(m.group(0)):
        return "date"
    a, b = m.start(), m.end()
    while a > 0 and (t[a - 1].isdigit() or t[a - 1] == "."):
        a -= 1
    while b < len(t) and (t[b].isdigit() or t[b] == "."):
        b += 1
    if t[m.start() - 1:m.start()] == "." and re.fullmatch(r"\d+\.\d+", t[a:b].strip(".")):
        return "decimal"
    return "other"


def main():
    if not os.path.isdir(PUB):
        print("no public-repo directory")
        return 1
    pm = real_pmids()
    if pm is None:
        return 1
    decl = builder_declarations()
    if decl is None:
        return 1
    builder_withheld, seed_tables, given, surnames, chain = decl
    NAME = whole_word(given + USERNAMES)
    SURNAME = whole_word(surnames)
    PERSON = whole_word(given + surnames)
    print("scanning public-repo/  against %d known study PMIDs\n" % len(pm))

    fails, warns, scanned, skipped = [], [], 0, 0
    for fn in sorted(builder_withheld ^ WITHHELD_FILES):
        fails.append(("tools/", "-", "withheld list out of step with the builder",
                      "%s is listed in %s only" % (
                          fn, "the builder" if fn in builder_withheld else "this gate")))
    # A display-chain script that is missing means a display that cannot be rebuilt.
    for c in sorted(chain):
        if not os.path.exists(os.path.join(PUB, c)):
            fails.append((c, "-", "display-chain script missing", os.path.basename(c)))

    for base, files in publishable_dirs(seed_tables):
        for fn in sorted(files):
            p = os.path.join(base, fn)
            rel = os.path.relpath(p, PUB).replace(os.sep, "/")
            ext = os.path.splitext(fn)[1].lower()
            # ⚠ THE PATH IS SCANNED BEFORE THE FILE IS, and whatever the file
            # is: an image named after a paper names the paper as well as a
            # script does.
            for m in EIGHT.finditer(rel):
                if m.group(0) in pm:
                    fails.append((rel, "-", "REAL PMID in a file path", m.group(0)))
            # ⚠ THE PAPER RULE. A ruling about a paper tends to
            # carry the paper's own author names or title words beside its
            # surrogate, and names and titles have no shape this gate could list.
            # So a surrogate may sit in code only where a published display needs
            # it, and nowhere in a code file's name.
            if rel.startswith("code/") and ext in (".py", ".r"):
                for m in SURROGATE.finditer(rel):
                    fails.append((rel, "-", "surrogate in a code file name", m.group(0)))
                if rel not in chain:
                    try:
                        body = open(p, encoding="utf-8", errors="replace").read()
                    except Exception:
                        body = ""
                    for m in SURROGATE.finditer(body):
                        fails.append((rel, body[:m.start()].count("\n") + 1,
                                      "surrogate in code off the display chain", m.group(0)))
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

            # accessions and trial registrations: everywhere, the tools included
            for m in PMC.finditer(t):
                add(fails, lineno(m.start()), "PMC accession", m.group(0))
            for m in TRIAL.finditer(t):
                add(fails, lineno(m.start()), "trial registration", m.group(0))

            # The tools and the README describe these patterns in order to guard
            # against them, so they must not trip over their own documentation.
            # ⚠⚠ BUT THEY SHIP, and exempting them WHOLESALE would leave a hole the
            # exact size of the folder that holds this gate.
            # A real study PMID is never legitimate documentation, so that one
            # check runs here too, and so do the two above. The pattern-shaped
            # checks (DOI, ISSN, URL, and the 8-digit warning) stay exempt,
            # because those are what the rulebook is made of.
            # ⚠ A reviewer's name is not a pattern, and the tools no longer hold
            # one, so it is checked in them as well. The README is left out only
            # because its reference to cite lists the authors.
            if rel.startswith("tools/") or rel.endswith("README.md"):
                for m in EIGHT.finditer(t):
                    if m.group(0) in pm:
                        add(fails, lineno(m.start()), "REAL PMID from the study",
                            m.group(0))
                if rel.startswith("tools/"):
                    for m in PERSON.finditer(t):
                        add(fails, lineno(m.start()), "reviewer named in a tool",
                            m.group(0))
                continue

            citation = rel in CITATION_FILES
            orcid_spans = [o.span() for o in ORCID.finditer(t)] if citation else []
            own_spans = [o.span() for o in OWN_DOI.finditer(t)] if citation else []
            for m in DOI.finditer(t):
                if citation and OWN_DOI.match(m.group(0)):
                    continue
                add(fails, lineno(m.start()), "DOI", m.group(0)[:50])
            for pos, key, val in keyed_literals(t, citation):
                add(fails, lineno(pos), "%s key given a literal" % key.lower(),
                    val[:50])
            if ext in YAML_EXT:
                for m in KEYED_ID_YAML.finditer(t):
                    if citation and OWN_DOI.fullmatch(m.group(2)):
                        continue
                    add(fails, lineno(m.start(1)),
                        "%s key given a literal" % m.group(1).lower(), m.group(2)[:50])
            for m in URL.finditer(t):
                # a bare API hostname in fetch code is not an identifier; a URL
                # with an id hanging off it is. Judge by what follows.
                tail = t[m.end():m.end() + 40]
                if not re.match(r"[/=]?\s*[\w./-]*\d{6}", tail):
                    continue
                if citation and OWN_DOI.match(tail.lstrip("/")):
                    continue
                add(fails, lineno(m.start()), "URL carrying an identifier", m.group(0))
            for m in ISSN.finditer(t):
                if YEARS.match(m.group(0)):
                    continue                      # 2014-2020 is a year range
                # ".sas:2608-2925" is a source line range, not a journal ISSN
                if m.start() and t[m.start() - 1] == ":":
                    continue
                if any(a <= m.start() and m.end() <= b for a, b in orcid_spans):
                    continue                      # half of an author's ORCID iD
                add(fails, lineno(m.start()), "ISSN", m.group(0))
            if not citation:
                for m in NAME.finditer(t):
                    add(fails, lineno(m.start()), "reviewer given name", m.group(0))
            if rel not in AUTHOR_LISTS:
                for m in SURNAME.finditer(t):
                    add(fails, lineno(m.start()), "reviewer surname", m.group(0))
            # ⚠ THE SAMPLING SEED IS A KEY. Published beside the query, a literal
            # seed can regenerate drawn PMIDs, so surrogating the identifiers
            # written in the script does not contain it. Scoped to code/sampling,
            # because every other seed here keys an analysis, not the identity of
            # a paper.
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
                elif any(a <= m.start() and m.end() <= b for a, b in own_spans):
                    continue                      # the archive's own Zenodo DOI
                else:
                    add(warns, lineno(m.start()), eight_kind(t, m), m.group(0))

    print("scanned %d text files, skipped %d binary\n" % (scanned, skipped))
    # ⚠ What is left unscanned is images, and a figure can print names that no
    # text scanner reads. The defence has to sit upstream, in the data the figure
    # is drawn from, which is what verify_k_anonymity.py checks.
    if skipped:
        print("   %d image or PDF file(s) cannot be scanned for text. What a figure\n"
              "   DRAWS is controlled at the data layer and by gate 2, not here.\n"
              % skipped)

    if warns:
        seen = set()
        uniq = [(r, l, k, s) for r, l, k, s in warns
                if not ((r, s) in seen or seen.add((r, s)))]
        # ⚠ ALL OF THEM: a list cut short hides exactly the entry worth reading.
        # The entry that matters is the one that is neither a date nor a number, so those come
        # first and get a line each; the other two groups are listed whole but
        # packed, because they are long and nearly always harmless.
        print("%d warning(s) over %d distinct value(s): 8-digit numbers that are not a\n"
              "study PMID. Every one is listed. Read the first group." % (len(warns), len(uniq)))
        other = [w for w in uniq if w[2] == "other"]
        print("\n   neither a date nor part of a decimal number: %d" % len(other))
        for rel, ln, _, s in other:
            print("      %-52s line %-6s %s" % (rel, ln, s))
        for kind, title in (("decimal", "the fractional part of a decimal number"),
                            ("date", "date-shaped")):
            per = {}
            for rel, ln, k, s in uniq:
                if k == kind:
                    per.setdefault(rel, []).append(s)
            print("\n   %s: %d" % (title, sum(len(v) for v in per.values())))
            for rel in sorted(per):
                for i in range(0, len(per[rel]), 6):
                    print("      %-52s %s" % (rel if i == 0 else "",
                                              " ".join(per[rel][i:i + 6])))
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
    if len(uniq) > 40:
        print("   ... %d more" % (len(uniq) - 40))
    return 1


if __name__ == "__main__":
    sys.exit(main())

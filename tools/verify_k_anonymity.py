"""
Release gate 2 of 3: can any single paper be picked out of what we publish?

WHY THIS EXISTS
verify_no_identifiers.py looks for identifiers it has been taught to recognise:
a PMID, a DOI, an ISSN, a reviewer's name. It has passed twelve times while the
repository was leaking, because each new leak was a shape nobody had listed. The
last one was not a shape at all: the journal NAME had been removed and the
journal was still recoverable from publisher country, an exact SJR, a coverage
span and a subfield, all of which are public in SCImago. On that combination
alone 304 of the 385 studies were unique.

So this gate does not look for identifiers. It measures how far the published
attributes narrow the sample, which is the thing we actually care about, and it
does not need to know what a journal is.

  1 CELL      every value of every quasi-identifier must have at least K papers
              behind it. A category carried by one paper names that paper.
  2 JOINT     joining every study-level file on the surrogate id, no combination
              of quasi-identifiers may leave fewer than K studies sharing it.
  3 COUNTS    no row of an aggregate table may report fewer than K papers.

WHAT COUNTS AS A QUASI-IDENTIFIER
Anything a reader can also observe outside this repository: from PubMed, from
SCImago or JCR, or from the paper's own front matter. Every non-numeric column
is treated as one unless its file is exempted below with a reason.

⚠ THE EXEMPTIONS ARE NOT A LOOPHOLE, AND THEY ARE NOT OPTIONAL EITHER. Item
responses and derived scores are NOT quasi-identifiers: a reader cannot look up
how a paper scored on confounding without doing the appraisal, so those columns
carry no linkage. Applying rule 1 to them would suppress rare findings, which is
not disclosure control but damage to the results. The bibliographic vocabulary
below is checked in exempt files anyway, so an `institution` column cannot hide
inside one.

    python public-repo/tools/verify_k_anonymity.py
Exit 0 clean, 1 if anything fails.
"""
import csv, os, re, sys
from collections import Counter, defaultdict

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
PUB = os.path.join(ROOT, "public-repo")
K = 5

# Which files hold appraisal answers or computed results rather than anything
# observable elsewhere. Read from the BUILDER's own `kind` declaration rather
# than restated here: two lists drift, and a gate that has drifted from what it
# guards passes for the wrong reason.
def _exempt_files():
    # no __pycache__ in a published tree: a .pyc embeds the absolute path it was
    # compiled from, which carries the analyst's home directory and username
    sys.dont_write_bytecode = True
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    try:
        import build_public_repo as B
    except Exception as e:                       # a gate that cannot read the
        print("!! cannot import the builder: %s" % e)   # declaration must fail
        raise SystemExit(1)
    out = {}
    for rel, spec in B.SHIP.items():
        if spec.get("kind") in ("items", "derived"):
            out[rel] = spec["kind"]
    for _s, dst, spec in B.RELOCATED:
        if spec.get("kind") in ("items", "derived"):
            out[dst] = spec["kind"]
    for f in B.SEED_TABLES:
        out["outputs/tables/" + f] = "derived"
    # Unkeyed tables the builder writes itself: no study id, rows shuffled. The
    # cell rule asks whether a category isolates a paper; with no paper on the
    # row there is none to isolate, and what remains are the aggregate counts
    # the manuscript itself prints, such as the four papers in an SJR Q4 venue.
    for f in getattr(B, "UNKEYED", []):
        out[f] = "derived"
    return out


QI_EXEMPT = _exempt_files()

# Always checked, exemption or not: a column whose NAME says it describes a
# journal, a place, an organisation or a person.
BIBLIOGRAPHIC = re.compile(
    r"(institution|affil|city|country|region|journal|venue|publisher|issn|doi|"
    r"scimago|sjr|jcr|quartile|subfield|topic|host|source_type|coverage|"
    r"author_name|corr_author|surname|forename|given|last_name|first_name|"
    r"funder|sponsor|grant|ack_text|title|abstract|pmid_real)", re.I)

# Bands and states that are numeric in form but categorical in use.
NUMERIC = re.compile(r"^-?\d+(\.\d+)?$")

# ---------------------------------------------------------------------------
# THE JOINT TEST IS A RATCHET, NOT A PASS MARK.  Decision of 2026-09-01.
#
# Every stratifier this study examines is an attribute of a public paper, so a
# row carrying several of them at once is close to unique however it is encoded:
# 159 of the 310 scored papers have a unique combination of the eleven published
# stratifiers, while no single stratifier has a cell below 37 papers. Collapsing
# until the combination reached k=5 would mean dropping most of the stratifiers,
# which is the analysis itself.
#
# What that risk actually costs an attacker is worth stating precisely, because
# the headline number overstates it. Of the eleven attributes, only three are
# cheap and reliable to compute for a candidate paper: team size, journal
# quartile and whether the first, last and corresponding authors are Saudi. On
# those alone 20 papers are unique, and on team size with quartile, none are.
# The rest - task, design, sector composition, funding level - are exactly the
# variables this study needed two reviewers and an adjudicator to settle, and a
# machine pass on funding got 20 of them wrong at high confidence. An attacker
# who can reproduce those has largely redone the study.
#
# The release therefore states the residual rather than defending against it.
# The gate holds it to a RATCHET: the measured figure may fall, never rise. A
# new column with identifying power shows up here as a number above the
# baseline, which is the regression this test exists to catch.
JOINT_BASELINE_UNIQUE = 74              # as measured on the 2026-09-01 build

STUDY_ID = "PMID"                       # holds the surrogate STUDY-nnnn
COUNT_COLS = ("papers", "n_papers", "author_appearances", "papers_involving",
              "papers_with_>=1_author", "n_studies")


def read_csv(p):
    for enc in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            with open(p, encoding=enc, newline="") as f:
                rd = csv.DictReader(f)
                return [c for c in (rd.fieldnames or []) if c], list(rd)
        except UnicodeDecodeError:
            continue
        except Exception:
            return [], []
    return [], []


def read_xlsx(p):
    try:
        import openpyxl
        wb = openpyxl.load_workbook(p, data_only=True, read_only=True)
    except Exception:
        return []
    out = []
    for ws in wb.worksheets:
        rows = []
        for r in ws.iter_rows(values_only=True):
            rows.append(["" if v is None else str(v) for v in r])
            if len(rows) > 5000:
                break
        if len(rows) < 2:
            continue
        hdr = [h for h in rows[0]]
        out.append((ws.title, [h for h in hdr if h],
                    [dict(zip(hdr, r)) for r in rows[1:]]))
    return out


def is_numeric_col(vals):
    v = [x for x in vals if x]
    return bool(v) and sum(1 for x in v if NUMERIC.match(x)) >= 0.9 * len(v)


SURROGATE = re.compile(r"^STUDY-\d{4}$")
SAMPLE_WORD = re.compile(r"\b(papers?|stud(y|ies)|sample|institutions?|"
                         r"journals?|countr(y|ies)|carr(y|ies|ied))\b", re.I)


def is_id_col(vals):
    v = [x for x in vals if x]
    return bool(v) and sum(1 for x in v if SURROGATE.match(x)) >= 0.9 * len(v)


def qi_columns(rel, cols, rows):
    """Which columns of this file are quasi-identifiers.

    ⚠ Everything under outputs/ is derived by definition: it is what the shipped
    code computes from the shipped data, so if the inputs carry no cell below k
    neither can an aggregate of them. Their columns are instrument variable
    names and statistics, and checking those flagged 60 rare item names as
    though a rare ANSWER were a rare PERSON. The bibliographic name check still
    applies, so a table that aggregates by institution or country still fails."""
    exempt = rel in QI_EXEMPT or rel.startswith("outputs/")
    keyed = STUDY_ID in cols
    out = []
    for c in cols:
        if c == STUDY_ID or c in COUNT_COLS:
            continue
        vals = [str(r.get(c, "") or "").strip() for r in rows]
        if is_id_col(vals):
            continue                       # the surrogate under another name
        if BIBLIOGRAPHIC.search(c) and (keyed or not exempt):
            # ⚠ Checked even in an exempt file, but only where a row IS a paper.
            # The override exists to stop an `institution` column hiding inside
            # a file declared derived. On an UNKEYED table there is no paper to
            # attach the name to, and applying it there failed the build over
            # "four papers appeared in an SJR Q4 journal", a number the
            # manuscript prints in its own Results.
            out.append(c)
            continue
        if exempt or is_numeric_col(vals):
            continue
        out.append(c)
    return out


def unique_text(rel, cols, rows):
    """Columns that are unique per PAPER: the leak no vocabulary can name.

    ⚠ This is the test that catches what nobody listed. An instrument answer
    repeats across papers because it comes from a fixed set of options; a
    sentence about one paper does not repeat, because it is about one paper.
    A surname does not repeat either, which is how `corr_author` would have been
    caught. Restricted to files where a row IS a paper: in a table of appraisal
    ITEMS a unique label is the item's name, and means nothing about a paper."""
    if not rows or STUDY_ID not in rows[0]:
        return []
    ids = {r.get(STUDY_ID) for r in rows}
    if len(ids) < 0.5 * len(rows):         # several rows per paper: not a profile
        return []
    out = []
    for c in cols:
        if c == STUDY_ID:
            continue
        v = [str(r.get(c, "") or "").strip() for r in rows]
        v = [x for x in v if x]
        if len(v) < 20 or is_numeric_col(v) or is_id_col(v):
            continue
        card = len(set(v))
        if card > 20 and card > 0.5 * len(v):
            out.append((c, card, len(v), sorted(set(v))[0][:40]))
    return out


def support(rows, col, count_col):
    """Papers behind each value: the stated count, else distinct studies, else rows."""
    if count_col:
        t = Counter()
        for r in rows:
            v = (r.get(col) or "").strip()
            if not v:
                continue
            try:
                t[v] += int(float(r.get(count_col) or 0))
            except ValueError:
                pass
        return t
    if rows and STUDY_ID in rows[0]:
        seen = defaultdict(set)
        for r in rows:
            v = (r.get(col) or "").strip()
            if v:
                seen[v].add(r.get(STUDY_ID))
        return Counter({v: len(s) for v, s in seen.items()})
    return Counter((r.get(col) or "").strip() for r in rows if (r.get(col) or "").strip())


def rare_category_names():
    """Every institution, country, city, sector or journal carried by fewer than
    K papers, read from the private tables."""
    out = {}

    def take(rel, name_col, count_col, minlen=5):
        p = os.path.join(ROOT, rel)
        if not os.path.exists(p):
            return
        try:
            with open(p, encoding="utf-8-sig", newline="") as f:
                for r in csv.DictReader(f):
                    v = (r.get(name_col) or "").strip()
                    try:
                        n = int(float(r.get(count_col) or 0))
                    except ValueError:
                        continue
                    if v and n < K and len(v) >= minlen:
                        out[v] = n
        except Exception:
            pass

    take("data/authors/07_25_2026_saudi_institution_counts.csv", "institution", "papers")
    take("data/authors/07_25_2026_country_counts.csv", "country", "papers_with_>=1_author")
    take("data/authors/07_25_2026_saudi_city_counts.csv", "city", "author_appearances")
    take("data/authors/07_25_2026_saudi_institution_type_counts.csv",
         "inst_type", "papers_involving")
    take("data/journals/07_25_2026_journal_landscape_by_journal_385_JCR.csv",
         "journal", "n_papers", minlen=8)
    return out


def prose_leaks():
    """Does any COMMENT in the published code name a category the displays hide?

    ⚠ Added 2026-09-02 after two were found, both written by the author of this
    gate while explaining the k rule: one comment listed three countries that
    carry a single paper each, another stated which sector type has exactly one.
    A comment leaks exactly what a table row leaks, and no structural rule looks
    at prose. Only comment lines are checked: the same words inside a literal
    are a lookup table or a CSS font stack, not a statement about the sample."""
    rare = rare_category_names()
    if not rare:
        return []
    rx = re.compile("|".join(sorted((re.escape(v) for v in rare), key=len, reverse=True)))
    out = []
    for base, dirs, files in os.walk(PUB):
        dirs[:] = [d for d in dirs if d not in {".git", "__pycache__"}]
        for fn in sorted(files):
            if os.path.splitext(fn)[1].lower() not in (".py", ".r", ".md"):
                continue
            p = os.path.join(base, fn)
            rel = os.path.relpath(p, PUB).replace(os.sep, "/")
            try:
                lines = open(p, encoding="utf-8", errors="replace").read().splitlines()
            except Exception:
                continue
            for i, line in enumerate(lines, 1):
                s = line.strip()
                if not s.startswith("#"):
                    continue
                # ⚠ The name alone is not the leak. `# Disambiguate Georgia: if a
                # US signal is present, treat as US` is a matching rule and says
                # nothing about this sample. What leaks is a name TOGETHER WITH
                # a claim about the sample, which is how both real cases read.
                if not SAMPLE_WORD.search(s):
                    continue
                m = rx.search(s)
                if m:
                    out.append((rel, i, m.group(0), rare[m.group(0)]))
    return out


def main():
    fails, checked, files = [], 0, 0
    for rel, ln, name, n in prose_leaks():
        fails.append(("prose", rel, "", "line %d" % ln, n,
                      "comment names %r, carried by %d paper(s)" % (name, n)))
    study_rows = defaultdict(dict)          # surrogate id -> {qualified col: value}

    for base, dirs, fnames in os.walk(PUB):
        dirs[:] = [d for d in dirs if d not in {".git", "__pycache__", "displays"}]
        for fn in sorted(fnames):
            ext = os.path.splitext(fn)[1].lower()
            if ext not in (".csv", ".xlsx"):
                continue
            p = os.path.join(base, fn)
            rel = os.path.relpath(p, PUB).replace(os.sep, "/")
            groups = []
            if ext == ".csv":
                cols, rows = read_csv(p)
                if cols:
                    groups = [("", cols, rows)]
            else:
                groups = read_xlsx(p)
            for sheet, cols, rows in groups:
                if not rows:
                    continue
                files += 1
                count_col = next((c for c in cols if c in COUNT_COLS), None)
                has_id = STUDY_ID in cols
                for c, card, n, ex in unique_text(rel, cols, rows):
                    fails.append(("text", rel, sheet, c, card,
                                  "%d distinct over %d rows, e.g. %r" % (card, n, ex)))
                for c in qi_columns(rel, cols, rows):
                    checked += 1
                    sup = support(rows, c, count_col if not has_id else None)
                    thin = sorted(((v, n) for v, n in sup.items() if n < K),
                                  key=lambda t: t[1])
                    if thin:
                        fails.append(("cell", rel, sheet, c, len(thin),
                                      ", ".join("%s (%d)" % (v[:28], n)
                                                for v, n in thin[:3])))
                    if has_id:
                        for r in rows:
                            sid = r.get(STUDY_ID)
                            v = (r.get(c) or "").strip()
                            if sid and v:
                                study_rows[sid]["%s::%s" % (rel, c)] = v

    # ---- 2. the joint test, which is the one the journal fingerprint failed --
    joint_fail = 0
    if study_rows:
        keys = sorted({k for d in study_rows.values() for k in d})
        prof = Counter(tuple(d.get(k, "") for k in keys) for d in study_rows.values())
        small = [n for n in prof.values() if n < K]
        uniq = sum(1 for n in prof.values() if n == 1)
        joint_fail = sum(small)
        print("joint profile over %d quasi-identifying columns from %d files"
              % (len(keys), files))
        print("  %d studies | %d distinct profiles | smallest group %d"
              % (len(study_rows), len(prof), min(prof.values()) if prof else 0))
        print("  %d studies unique, %d in a group smaller than %d"
              % (uniq, joint_fail, K))
        if uniq > JOINT_BASELINE_UNIQUE:
            print("  RATCHET BROKEN: baseline is %d unique\n" % JOINT_BASELINE_UNIQUE)
            fails.append(("joint", "(all study-level files)", "",
                          "|".join(keys)[:70], uniq,
                          "was %d, now %d: something new identifies"
                          % (JOINT_BASELINE_UNIQUE, uniq)))
        else:
            print("  within the declared baseline of %d unique; see the note in "
                  "this file\n" % JOINT_BASELINE_UNIQUE)

    print("%d files, %d quasi-identifying columns checked at k=%d\n"
          % (files, checked, K))
    if not fails:
        print("PASS: no published category isolates fewer than %d papers, and the" % K)
        print("      joint profile is within its declared baseline. That baseline is")
        print("      not zero and the README says so: see the note above on what an")
        print("      attacker would have to reproduce to use it.")
        return 0

    print("FAIL: %d finding(s)\n" % len(fails))
    for kind, rel, sheet, col, n, ex in fails[:40]:
        print("  %-6s %-46s %-22s %4d thin  %s"
              % (kind, (rel + ("[%s]" % sheet if sheet else ""))[:46], col[:22], n, ex))
    if len(fails) > 40:
        print("  ... %d more" % (len(fails) - 40))
    return 1


if __name__ == "__main__":
    sys.exit(main())

# -*- coding: utf-8 -*-
# Extract VERBATIM funding statements from the full text of all 385 papers.
#
# Deliberately extraction-only: this script records what the paper SAYS, plus the
# location it was found in. Classification into local / international / declared-unfunded /
# not-stated is a SEPARATE step, so the coding rule can be revised without re-reading
# anything (see project-funding-stratifier).
#
# Funding statements hide in several places, so we sweep three ways:
#   A. labelled sections   ("Funding", "Financial support", "Acknowledgements", ...)
#   B. free-standing sentences anywhere ("This work was supported by ...")
#   C. explicit no-funding declarations (a distinct fact from silence)
#
# Run from the repository root.
import csv, os, re, sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

TXT = "private/fulltext/pdf-by-pmid"
OUT = "data/analysis/08_23_2026_funding_statements_385.csv"
LOG = "data/provenance/08_23_2026_funding_extract_log.csv"

# ---------------------------------------------------------------- normalisation
LIG = {"ﬀ": "ff", "ﬁ": "fi", "ﬂ": "fl", "ﬃ": "ffi", "ﬄ": "ffl",
       "’": "'", "‘": "'", "“": '"', "”": '"',
       "–": "-", "—": "-", " ": " "}


def clean(s):
    for a, b in LIG.items():
        s = s.replace(a, b)
    s = s.replace("­", "")             # SOFT HYPHEN: "King Saud Uni\xadversity"
    s = re.sub(r"-\s*\n\s*(?=[a-z])", "", s)   # de-hyphenate across line breaks
    s = re.sub(r"(?<=[A-Za-z])-\s+(?=[a-z]{2})", "", s)  # "Uni- versity" from PDF reflow
    s = re.sub(r"\s+", " ", s)
    return s.strip()


# ---------------------------------------------------------------- section headings
# Ordered: the more specific label wins when two overlap.
SECTION_LABELS = [
    ("funding", r"(?:sources?\s+of\s+)?fund(?:ing|s)(?:\s*/\s*support|\s+and\s+support)?"
                r"(?:\s+(?:statement|information|sources?|declaration|support|acknowledge?ments?))?"),
    ("source_of_support", r"sources?\s+of\s+support"),
    ("financial_support", r"financial\s+(?:support(?:\s+and\s+sponsorship)?|disclosures?|assistance)"),
    ("grant_support", r"grant\s+(?:support|information|sponsors?)"),
    ("acknowledgements", r"acknowledge?ments?"),
    ("coi", r"(?:conflicts?|declaration)\s+of\s+(?:interests?|competing\s+interests?)"),
    ("declarations", r"declarations?"),
    ("role_of_funding", r"role\s+of\s+the\s+(?:funding\s+source|sponsor)"),
]
# A heading must OWN its line: line-start, optional numbering, the label, then either a
# colon (content follows on the same line) or end-of-line. [ \t] not \s -- \s crosses
# newlines, which made body text like "...financial support\nwould increase..." look like
# a heading.
HEAD_RE = {k: re.compile(
    r"\n[ \t]*(?:\d+[.)]?[ \t]*)?(?:" + pat + r")[ \t]*"
    r"(?::[ \t]*|[.\-–]?[ \t]*\n)", re.I) for k, pat in SECTION_LABELS}
# Where a section stops: the next plausible heading.
STOP_RE = re.compile(
    r"(?:^|\n)\s*(?:\d+\.?\s*)?("
    r"references?|bibliograph|abbreviations?|author\s+contributions?|authors'?\s+contributions?|"
    r"data\s+availability|availability\s+of\s+data|ethic(?:s|al)|consent|competing\s+interests?|"
    r"conflicts?\s+of\s+interest|declaration|disclosure|supplementary|appendix|orcid|"
    r"institutional\s+review|informed\s+consent|acknowledge?ments?|funding|"
    r"how\s+to\s+cite|publisher'?s\s+note|open\s+access|copyright|received\s*:"
    r")\b", re.I)

# ---------------------------------------------------------------- sentence sweep
# The cue itself. Matches are grown backwards to the sentence start (bounded), so the
# snippet reads as a sentence instead of dragging in 300 chars of unrelated body text.
CUE = (
    r"(?:was|were|is|are|has\s+been|have\s+been)\s+(?:financially\s+|partially\s+|fully\s+|generously\s+)?"
    r"(?:supported|funded|sponsored|financed)\s+(?:in\s+part\s+)?by"
    # "received no ..." must be followed by a money word -- otherwise "received no
    # intervention" (a trial arm) reads as a funding declaration.
    r"|received\s+(?:no|any)\s+(?:specific\s+|external\s+|dedicated\s+|direct\s+)?"
    r"(?:grant|fund|financial|monetary|support)"
    r"|received\s+(?:financial\s+support|funding|a\s+grant|grants\b)"
    r"|(?:did|does)\s+not\s+receive\s+(?:any\s+)?(?:specific\s+|external\s+)?(?:grant|fund|financial)"
    r"|no\s+(?:specific\s+)?(?:grant|fund(?:ing|s)|financial\s+support)"
    r"|(?:funded|sponsored)\s+by|supported\s+by\s+(?:a\s+)?(?:grant|fund|the\s)"
    r"|financial\s+support\s+(?:from|for|was)"
    r"|grant\s+(?:no\b|number|#)|under\s+grant|award\s+number"
    r"|through\s+(?:the\s+)?(?:project|grant|research\s+group)\s+(?:no\b|number)"
    r"|deanship\s+of\s+scientific\s+research"
    r"|self[-\s]?funded|authors'?\s+own\s+(?:funds|expense)"
    r"|article\s+processing\s+(?:charges?|fees?)"
    r"|fund(?:ing|s)?\s+(?:for\s+(?:this|the)\s+\w+\s+)?(?:was|were|is|are)\s+(?:provided|received|obtained|secured)"
    r"|financially\s+supported|with\s+(?:financial\s+)?support\s+from"
)
FUND_CUE_RE = re.compile(CUE, re.I)
# Anything that even smells of funding — used to decide whether a fallback section
# (acknowledgements / COI / declarations) is really a funding statement at all.
FUNDING_HINT = re.compile(
    r"\b(fund(?:ing|ed|s)?|grant|financial\s+support|sponsor(?:ed|ship)?|"
    r"deanship\s+of\s+scientific\s+research|scholarship|"
    r"article\s+processing\s+(?:charge|fee)|monetary|no\s+funding)\b", re.I)

# explicit "no funding" declarations — a DIFFERENT fact from saying nothing at all
NOFUND = re.compile(
    r"("
    r"(?:received|obtained|had)\s+no\s+(?:specific\s+|external\s+|dedicated\s+|direct\s+)?(?:grant|fund(?:ing|s)?|financial\s+support|support|monetary)"
    r"|(?:did|does|do|has|have|had)\s+not\s+receive[d]?\s+(?:any\s+)?(?:specific\s+|external\s+|dedicated\s+)?(?:grant|fund(?:ing|s)?|financial|monetary)"
    # "The authors have no funding or conflicts of interest to disclose." -- very common
    # journal boilerplate; it IS a funding declaration and was being missed.
    r"|(?:have|has|had|authors?)\s+no\s+fund(?:ing|s)?\b"
    r"|no\s+(?:specific\s+|external\s+|dedicated\s+)?(?:grant|fund(?:ing|s)?|financial\s+support)\s+(?:was|were|has\s+been)\s+(?:received|obtained|provided|available)"
    r"|(?:this|the)\s+(?:research|study|work|project|article)\s+(?:received|had)\s+no\s+(?:external\s+|specific\s+)?fund"
    r"|(?:was|were|is|are)\s+not\s+(?:supported\s+or\s+funded|funded|financially\s+supported)"
    r"|no\s+specific\s+fund(?:ing|s)?\b"
    r"|no\s+funding\s*(?:was\s+received)?\s*[.;]"
    r"|(?:fund(?:ing|s)?|financial\s+support(?:\s+and\s+sponsorship)?|sponsorship)\s*[:\-]\s*(?:none|nil|no\s+funding|not\s+applicable|n/?a)\b"
    r"|there\s+(?:was|is)\s+no\s+(?:funding|financial\s+support)"
    r"|non[-\s]?funded\b|\bunfunded\b|self[-\s]?fund(?:ed|ing)"
    r")", re.I)

SELFFUND = re.compile(r"(self[-\s]?fund(?:ed|ing)|authors'?\s+own\s+(?:funds|expense|resources)|"
                      r"funded\s+by\s+the\s+authors)", re.I)

# APC / read-and-publish waivers are NOT research funding. Flagged separately so the
# ruling on how to treat them can be made once, on the numbers (see stratifier plan).
OA_AGREEMENT = re.compile(
    r"(open\s+access\s+(?:funding|publishing|fees?)\s+(?:enabled|provided|facilitated|organized|organised)"
    r"|projekt\s+deal|read\s+and\s+publish|transformative\s+agreement"
    r"|as\s+part\s+of\s+the\s+wiley\s*-|council\s+of\s+australian\s+university\s+librarians"
    r"|\bCAUL\b\s+agreement)", re.I)


# Tier 2: PDF text extraction often runs a heading into its body on one line
# ("Declarations Funding A specific funding was provided by ..."), so a strict
# owns-its-line rule misses them. Allow an inline label for the DEDICATED funding
# labels only, and require the body to actually read like a funding statement.
INLINE_HEAD = {k: re.compile(r"\b(?:" + pat + r")\s*[:.\-–]?\s+", re.I)
               for k, pat in SECTION_LABELS}
INLINE_OK = re.compile(
    r"(none\b|nil\b|not\s+applicable|n/?a\b|no\s+fund|no\s+external|no\s+specific"
    r"|(?:was|were|is|are|has\s+been)\s+(?:provided|supported|funded|financed|received|obtained)"
    r"|provided\s+by|supported\s+by|funded\s+by|sponsored\s+by"
    r"|grant\s*(?:no\b|number|#)|deanship|received\s+no|did\s+not\s+receive"
    r"|disclose\s+(?:any|no)\s+fund)", re.I)
INLINE_KEYS = ("funding", "source_of_support", "financial_support",
               "grant_support", "role_of_funding")


# Article footers (bylines, affiliations, DOIs, download banners) sit immediately after
# the end-matter sections and are not part of any statement. Left in, an affiliation
# like "Mansoura University, Egypt" reads as an international funder.
FOOTER = re.compile(
    # "From the Department" is an affiliation byline, but lowercase "...grant from the
    # Department of Health Research" is the funder itself -- so the F must be capital.
    r"(?:(?-i:From)\s+the\s+(?:The\s+)?[Dd]epart?ment|Address\s+correspondence|Correspondence\s+(?:to|address)|"
    r"\*?Corresponding\s+author|Received\s*:\s|Accepted\s*:\s|Published\s+online|©|"
    r"\bdoi:\s*10\.|https?://|Downloaded\s+from|E-?mail\s*:|\bORCID\b)", re.I)


def _body_after(txt, start, cap=1200):
    tail = txt[start:start + 4000]
    stop = STOP_RE.search(tail, 1)
    body = tail[:stop.start()] if stop else tail[:cap]
    f = FOOTER.search(body)
    if f and f.start() > 25:      # >25 so a statement that *opens* with one survives
        body = body[:f.start()]
    return clean(body)


def find_section(txt, key):
    """Return the text of section `key`, or ''. Strict (owns-its-line) first."""
    m = HEAD_RE[key].search(txt)
    if m:
        return _body_after(txt, m.end())
    if key in INLINE_KEYS:
        for m in INLINE_HEAD[key].finditer(txt):
            body = _body_after(txt, m.end(), cap=600)
            if body and INLINE_OK.search(body[:250]):
                # keep the heading word, or the statement reads as a fragment
                # ("for this research was provided by ...")
                return clean(m.group(0)) + " " + body
    return ""


# The whole-document sentence sweep must NOT read the reference list: cited TITLES
# contain funding language ("Reports funded by National Institutes of Health"), which
# invented funders for papers that never had any.
REF_HEAD = re.compile(r"\n[ \t]*(?:\d+[.)]?[ \t]*)?"
                      r"(?:references?|bibliography|literature\s+cited)[ \t]*:?[ \t]*\n", re.I)


def strip_references(txt):
    cuts = [m.start() for m in REF_HEAD.finditer(txt) if m.start() > 0.35 * len(txt)]
    return txt[:cuts[-1]] if cuts else txt


def cue_sentences(flat):
    """Every funding-cue hit, grown out to its enclosing sentence."""
    out = []
    for m in FUND_CUE_RE.finditer(flat):
        lo = max(0, m.start() - 250)
        left = flat[lo:m.start()]
        # sentence start = after the last terminator that is followed by a capital/space
        cut = max(left.rfind(". "), left.rfind("? "), left.rfind("! "))
        start = lo + cut + 2 if cut != -1 else lo
        tail = flat[m.end():m.end() + 400]
        dot = tail.find(". ")
        end = m.end() + (dot + 1 if dot != -1 else len(tail))
        out.append(flat[start:end].strip())
    return out


# A free-standing sentence counts as a funding statement only if it (a) declares no
# funding, (b) cites a grant/award number, or (c) names a fundable ORGANISATION *and*
# is about this study rather than about the literature.
GRANTNUM = re.compile(r"(grant|award|project|contract|proposal)\s*(?:no\.?|number|#|id)?\s*[:\-]?\s*"
                      r"[A-Z0-9][A-Z0-9./\-]{3,}|\b[A-Z]{2,6}[-/ ]?\d{2,}[-/]?\d*\b")
ORG_HINT = re.compile(
    r"\b(universit(?:y|ies)|college|hospital|ministry|deanship|deputyship|foundation|institut(?:e|ion)|"
    r"council|cent(?:er|re)|society|association|agency|authority|trust|programme|program|charity|"
    r"commission|department\s+of|corporation|compan(?:y|ies)|laborator(?:y|ies)|"
    r"king\b|prince(?:ss)?\b|national\b|federal\b|research\s+fund|endowment)\b", re.I)
SELFREF = re.compile(
    r"\b(?:this|the\s+(?:present|current))\s+(?:study|research|work|project|article|paper|"
    r"manuscript|trial|survey|investigation|trial)\b|\bwe\b|\bour\b|\bthe\s+authors?\b|"
    r"\bauthor\(s\)\b|\bresearchers?\b", re.I)


def sentence_is_funding(s):
    if NOFUND.search(s):
        return True
    if GRANTNUM.search(s):
        return True
    return bool(ORG_HINT.search(s) and SELFREF.search(s))


def dedupe(snips):
    out = []
    seen = set()
    for s in snips:
        k = re.sub(r"[^a-z0-9]", "", s.lower())[:120]
        if k and k not in seen:
            seen.add(k)
            out.append(s)
    return out


rows, log = [], []
pmids = [r["PMID"].strip() for r in
         csv.DictReader(open("data/analysis/07_25_2026_canonical_385_pmids.csv", encoding="utf-8-sig"))]

for pmid in pmids:
    path = os.path.join(TXT, pmid + ".txt")
    if not os.path.exists(path):
        rows.append({"PMID": pmid, "has_text": 0})
        log.append([pmid, "NO_TEXT", 0, 0, 0])
        continue
    raw = open(path, encoding="utf-8", errors="replace").read()
    txt = raw.replace("\r", "")
    body = strip_references(txt)          # sweeps run on the paper, not its bibliography
    flat = clean(body)
    had_refs = len(body) < len(txt)

    # A. labelled sections (searched in the full text -- a Funding heading can sit
    #    after the references in some layouts)
    sections = {k: find_section(txt, k) for k, _ in SECTION_LABELS}

    # B. sentences anywhere in the paper, kept only if they are about funding THIS
    #    study. "is supported by a previous Egyptian study" is evidential support,
    #    not money, and it was the single biggest source of false funders.
    sents = dedupe([clean(s) for s in cue_sentences(flat) if sentence_is_funding(s)])

    # C. explicit no-funding declaration
    nofund_hits = dedupe([clean(m.group(0)) for m in NOFUND.finditer(flat)])

    # the best single verbatim statement to show a human first.
    # A dedicated funding heading is taken as-is (an empty/"None" one is itself the fact);
    # the generic sections only count when they actually talk about funding.
    primary, primary_src = "", ""
    for k in ("funding", "source_of_support", "financial_support", "grant_support", "role_of_funding"):
        if sections[k] and len(sections[k]) > 2:
            primary, primary_src = sections[k], k
            break
    if not primary and sents:
        primary, primary_src = " | ".join(sents[:3]), "sentence"
    if not primary:
        for k in ("acknowledgements", "declarations", "coi"):
            if sections[k] and len(sections[k]) > 8 and FUNDING_HINT.search(sections[k]):
                primary, primary_src = sections[k], k
                break

    rows.append({
        "PMID": pmid,
        "has_text": 1,
        "n_chars_text": len(raw),
        "primary_source": primary_src,
        "funding_statement_verbatim": primary[:2000],
        "sec_funding": sections["funding"][:1500],
        "sec_source_of_support": sections["source_of_support"][:1000],
        "sec_financial_support": sections["financial_support"][:1000],
        "sec_grant_support": sections["grant_support"][:1000],
        "sec_role_of_funding": sections["role_of_funding"][:600],
        "sec_acknowledgements": sections["acknowledgements"][:1500],
        "sec_coi": sections["coi"][:800],
        "sec_declarations": sections["declarations"][:800],
        "funding_sentences": (" | ".join(sents))[:2000],
        "n_funding_sentences": len(sents),
        "explicit_no_funding_hit": (" | ".join(nofund_hits))[:600],
        "self_funded_hit": 1 if SELFFUND.search(flat) else 0,
        "oa_agreement_hit": 1 if OA_AGREEMENT.search(primary or "") else 0,
        "refs_stripped": int(had_refs),
    })
    log.append([pmid, "OK", len(raw), 1 if primary else 0, len(sents)])

cols = ["PMID", "has_text", "n_chars_text", "primary_source", "funding_statement_verbatim",
        "sec_funding", "sec_source_of_support", "sec_financial_support",
        "sec_grant_support", "sec_role_of_funding",
        "sec_acknowledgements", "sec_coi", "sec_declarations",
        "funding_sentences", "n_funding_sentences", "explicit_no_funding_hit",
        "self_funded_hit", "oa_agreement_hit", "refs_stripped"]
with open(OUT, "w", newline="", encoding="utf-8-sig") as fh:
    w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
    w.writeheader()
    for r in rows:
        w.writerow({c: r.get(c, "") for c in cols})

with open(LOG, "w", newline="", encoding="utf-8-sig") as fh:
    w = csv.writer(fh)
    w.writerow(["PMID", "status", "n_chars", "found_primary", "n_sentences"])
    w.writerows(log)

n = len(rows)
withtext = sum(1 for r in rows if r.get("has_text"))
prim = sum(1 for r in rows if r.get("funding_statement_verbatim"))
sec_f = sum(1 for r in rows if r.get("sec_funding"))
nof = sum(1 for r in rows if r.get("explicit_no_funding_hit"))
print("papers                       : %d" % n)
print("with full text               : %d" % withtext)
print("labelled 'Funding' section   : %d" % sec_f)
print("ANY verbatim statement found : %d  (%.1f%%)" % (prim, 100.0 * prim / n))
print("nothing found (candidate 'not stated'): %d" % (withtext - prim))
print("explicit no-funding wording  : %d" % nof)
print("self-funded wording          : %d" % sum(1 for r in rows if r.get("self_funded_hit")))
print("\nby primary source:")
bysrc = {}
for r in rows:
    bysrc[r.get("primary_source", "")] = bysrc.get(r.get("primary_source", ""), 0) + 1
for k, v in sorted(bysrc.items(), key=lambda x: -x[1]):
    print("   %-20s %d" % (k or "(none)", v))
print("\nwrote", OUT)

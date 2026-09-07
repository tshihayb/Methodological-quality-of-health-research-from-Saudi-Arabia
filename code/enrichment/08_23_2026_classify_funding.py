# NOTE (public repository): 3 hard-coded study identifier(s) were
# rewritten to de-identified surrogates by tools/build_public_repo.py.
# They are rulings about particular studies rather than values the data
# can supply, so they have to travel with it.
# -*- coding: utf-8 -*-
# FIRST-PASS classification of the extracted funding statements into the four-state
# stratifier. Reads only the verbatim text produced by 08_23_2026_extract_funding.py,
# so the rule below can be revised and re-run WITHOUT re-reading any PDF.
#
# States (four, deliberately -- see project-funding-stratifier):
#   local            funder(s) all Saudi
#   international    funder(s) all non-Saudi
#   both             at least one of each          [pending TSA ruling #2]
#   declared_none    the paper explicitly says it received no funding
#   not_stated       the paper says nothing at all about funding   [a transparency fact,
#                                                                   NOT a funding fact]
#   needs_review     a statement exists but no funder could be resolved
#
# Run from the repository root.
import csv, re, sys
from collections import Counter

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SRC = "data/analysis/08_23_2026_funding_statements_385.csv"
OUT = "data/analysis/08_23_2026_funding_classified_385.csv"
REVIEW = "data/analysis/08_23_2026_funding_review_worklist.csv"

# ---------------------------------------------------------------- funder lexicons
# Saudi / domestic funders. Grant-code prefixes are included because Saudi deanship
# awards are frequently cited by code only (IFKSURG-303, RGP.2/45/43, NSTIP ...).
LOCAL = [
    ("KACST", r"king\s+abdul\s?aziz\s+city\s+for\s+science|\bKACST\b"),
    ("RDIA", r"research,?\s+development\s+and\s+innovation\s+authority|\bRDIA\b"),
    ("NSTIP/NPST", r"national\s+(?:plan|science,?\s+technology)\s+for\s+science|\bNSTIP\b|\bNPST\b"),
    # "Research" is dropped: PDF reflow truncates it ("Deanship of Scientific 2.11")
    ("Deanship of Scientific Research", r"deanship\s+of\s+(?:scientific|graduate\s+studies)"),
    # "...[NAME-REDACTED] of the Kingdom of Saudi Arabia" -- the comma form alone missed it
    ("[NAME-REDACTED] (SA)", r"deputyship\s+for\s+research|ministry\s+of\s+education[^.]{0,40}saudi"),
    ("Ministry of Health (SA)", r"(?:saudi\s+)?ministry\s+of\s+health[^.]{0,40}saudi|saudi[^.]{0,30}ministry\s+of\s+health"),
    # KSU awards are usually cited as "Researchers Supporting Project RSP-2021/77"
    ("King Saud University", r"king\s+saud\s+univ|\bKSU\b|researchers?\s+support(?:ing|ed)\s+project|\bRSP\b|\bRSPD\b|\bRSP[-/]"),
    ("AlMaarefa University", r"al[\s-]?maarefa|\bMAAREFA\b"),
    # "Mohammad" / "Mohammed" / "Mohamed"; the earlier moham+ed? required a literal 'e'
    ("Mohammed bin Naif Medical Centre", r"moh?amm?[ae]d\s+bin\s+na[iy]f"),
    ("King Fahad Security College", r"king\s+fahad?\s+security\s+college"),
    ("KSAU-HS / KAIMRC", r"king\s+saud\s+bin\s+abdulaziz\s+university|king\s+abdullah\s+international\s+medical\s+research|\bKAIMRC\b"),
    ("King Abdulaziz University", r"king\s+abdulaziz\s+university|\bKAU\b"),
    ("KAUST", r"king\s+abdullah\s+university\s+of\s+science|\bKAUST\b"),
    ("KFSHRC", r"king\s+faisal\s+specialist\s+hospital|\bKFSHRC\b"),
    ("King Faisal University", r"king\s+faisal\s+university"),
    ("King Khalid University", r"king\s+khalid\s+university"),
    ("KFUPM", r"king\s+fahd\s+university\s+of\s+petroleum|\bKFUPM\b"),
    ("King Fahd / KFMC", r"king\s+fahd\s+(?:medical|specialist|central)|king\s+fahad\s+medical|\bKFMC\b"),
    ("IAU (Dammam)", r"imam\s+abdulrahman\s+bin\s+faisal|university\s+of\s+dammam"),
    ("IMSIU", r"imam\s+mohamm?ad\s+ibn\s+saud|\bIMSIU\b"),
    ("PNU", r"princess\s+nourah|\bPNU\b"),
    ("Prince Sattam", r"prince\s+sattam"),
    ("Prince Sultan", r"prince\s+sultan"),
    ("King Salman Center", r"king\s+salman\s+cent(?:er|re)\s+for\s+disability"),
    ("Taif University", r"taif\s+university"),
    ("Taibah University", r"taibah\s+university"),
    ("Jazan University", r"jazan\s+university|jizan\s+university"),
    ("Qassim University", r"qassim\s+university"),
    ("Umm Al-Qura University", r"umm\s+al[\s-]?qura"),
    ("[NAME-REDACTED]", r"najran\s+university"),
    ("University of Hail", r"university\s+of\s+ha'?il|ha'?il\s+university"),
    ("University of Tabuk", r"university\s+of\s+tabuk|tabuk\s+university"),
    ("[NAME-REDACTED]", r"al[\s-]?baha\s+university"),
    ("University of Bisha", r"university\s+of\s+bisha|bisha\s+university"),
    ("[NAME-REDACTED]", r"shaqra\s+university"),
    ("Majmaah University", r"majmaah\s+university"),
    ("Jouf University", r"jouf\s+university|al[\s-]?jouf"),
    ("Northern Border University", r"northern\s+border\s+university"),
    ("Alfaisal University", r"alfaisal\s+university|al[\s-]?faisal\s+university"),
    ("Saudi Aramco / SABIC", r"\baramco\b|\bSABIC\b"),
    ("Saudi society / association", r"saudi\s+(?:diabetes|society|association|commission|heart|thoracic)"),
    ("SFDA", r"saudi\s+food\s+and\s+drug|\bSFDA\b"),
    ("Saudi grant code", r"\bIFKSURG\b|\bIFPRC\b|\bIFP[-\s]?\d|\bRGP[\s./-]|\bNU/|\bKSRG\b|\bGRP[-\s]?\d|\bTURSP\b|\bIFPIP\b|\bDSR\b"),
    ("generic Saudi funder", r"(?:funded|supported|sponsored|grant)[^.]{0,80}\bsaudi\s+arabia\b"),
]

# Non-Saudi funders.
INTL = [
    # T32/K01/R01/R56 are NIH award prefixes and are often the only funder named
    ("NIH / US federal", r"\bNIH\b|national\s+institutes?\s+of\s+health|\bNIAID\b|\bNIDDK\b|\bNHLBI\b|\bNCI\b|\bNSF\b|\bCDC\b|\bPCORI\b|\bAHRQ\b"
                        r"|\bT32\s?[A-Z]{2}\d|\bR01\s?[A-Z]{2}\d|\bK\d{2}\s?[A-Z]{2}\d"),
    ("Wellcome Trust", r"wellcome\s+trust"),
    ("MRC / NIHR (UK)", r"medical\s+research\s+council|\bNIHR\b|national\s+institute\s+for\s+health\s+research"),
    ("Cancer Research UK", r"cancer\s+research\s+uk|\bCRUK\b"),
    ("EU / ERC / Horizon", r"european\s+research\s+council|\bERC\b|horizon\s+(?:2020|europe)|marie\s+sk|european\s+commission|\bFP7\b"
                           r"|european\s+(?:social|regional\s+development|structural)\s+fund|operational\s+program(?:me)?\s+knowledge"),
    ("DFG / BMBF (DE)", r"deutsche\s+forschungsgemeinschaft|\bDFG\b|\bBMBF\b|max\s+planck"),
    ("JSPS / AMED (JP)", r"\bJSPS\b|japan\s+society\s+for\s+the\s+promotion|\bAMED\b|uehara\s+memorial"),
    ("NSFC (CN)", r"national\s+natural\s+science\s+foundation\s+of\s+china|\bNSFC\b"),
    ("CIHR (CA)", r"canadian\s+institutes?\s+of\s+health\s+research|\bCIHR\b"),
    ("NHMRC / ARC (AU)", r"\bNHMRC\b|national\s+health\s+and\s+medical\s+research\s+council|australian\s+research\s+council"),
    ("Gates Foundation", r"bill\s+(?:and|&)\s+melinda\s+gates|gates\s+foundation"),
    ("WHO / UN", r"world\s+health\s+organi[sz]ation|\bWHO\b|\bUNICEF\b|\bUNDP\b|\bUNHCR\b"),
    ("European societies", r"european\s+association\s+of\s+urology|\bEAU\b|european\s+society\s+for\s+blood|\bEBMT\b|european\s+society\s+of"),
    ("TUBITAK (TR)", r"\bTUB[İI]TAK\b|scientific\s+and\s+technological\s+research\s+council\s+of\s+turkey"),
    ("STDF (EG)", r"science,?\s+technology\s+(?:and\s+innovation\s+)?funding\s+authority|\bSTDF\b"),
    ("ICMR / DST (IN)", r"indian\s+council\s+of\s+medical\s+research|\bICMR\b|department\s+of\s+science\s+and\s+technology,?\s+india"),
    ("Malaysia", r"national\s+sports\s+institute\s+of\s+malaysia|universiti\b|malaysian?\s+ministry"),
    ("Kuwait / Qatar / UAE / Oman", r"kuwait\s+(?:university|foundation)|qatar\s+(?:national\s+research|foundation|university)|\bQNRF\b|united\s+arab\s+emirates\s+university|sultan\s+qaboos"),
    ("Egypt / Jordan / Lebanon", r"cairo\s+university|mansoura\s+university|ain\s+shams|university\s+of\s+jordan|american\s+university\s+of\s+beirut"),
    ("industry / pharma", r"\bpfizer\b|\bnovartis\b|astra\s?zeneca|\bsanofi\b|\bGSK\b|glaxo|\bmerck\b|\broche\b|novo\s+nordisk|boehringer|\btakeda\b|\bamgen\b|\bgilead\b|\bjanssen\b|eli\s+lilly|\bbayer\b|\babbvie\b|\bmedtronic\b"),
    ("China provincial", r"provincial\s+(?:department|bureau|key\s+research)|natural\s+(?:science\s+)?foundation\s+of\s+\w+\s+province"
                         r"|fujian|guangdong|zhejiang|jiangsu|shandong|liaoning|shenyang|gansu|hubei|hunan|sichuan|henan|hebei|anhui|yunnan"),
    ("WBMT / transplant networks", r"\bWBMT\b|worldwide\s+network\s+for\s+blood"),
    ("Iran universities", r"(?:mashhad|shiraz|tehran|isfahan|tabriz)\s+university|university\s+of\s+medical\s+sciences,?\s+iran"),
    ("India government", r"department\s+of\s+health\s+research|government\s+of\s+india|\bDBT\b\s+india"),
    ("Pakistan", r"higher\s+education\s+commission,?\s+pakistan|pakistan\s+[NAME-REDACTED]\s+society"),
    ("Australia universities", r"university\s+of\s+new\s+south\s+wales|\bUNSW\b|monash\s+university|university\s+of\s+adelaide|australian\s+government\s+research\s+training"),
    ("Canada", r"mcgill\s+university|montreal\s+general\s+hospital|stollery\s+children"),
    ("Nordic", r"turku\s+university\s+hospital|helsinki\s+university\s+hospital|finnish\s+(?:dental|cancer)"),
    ("UK DFID / FCDO", r"department\s+for\s+international\s+development|\bDFID\b|\bFCDO\b"),
    ("UK charity / trust", r"evelyn\s+trust|british\s+heart\s+foundation|\bBHF\b|diabetes\s+uk|kidney\s+research\s+uk|royal\s+society"),
    ("US VA", r"veterans\s+(?:health\s+administration|affairs)"),
    ("nutrition industry", r"nest(?:l[eé]|ec)\b|\bdanone\b|mead\s+johnson|\babbott\b"),
    ("other intl foundation", r"clara\s+mayo|zurich\s+cancer\s+league|fulbright|\bNATO\b|fogarty|"
                              r"\bDAAD\b|swiss\s+national\s+science|\bFAPESP\b|\bCNPq\b|\bCONACYT\b"),
]

# Funder NAMES must match case-insensitively, but ACRONYMS must not: with re.I,
# \bWHO\b matches the English word "who" (it hit 48 papers), \bNO\b, \bEAU\b and
# friends are the same trap. Wrap every uppercase token in a scoped (?-i:...) so the
# acronym stays case-sensitive while the surrounding prose does not.
_ACR = re.compile(r"\\b([A-Z][A-Z0-9]{1,9})(\\b)?(?![?*+{])")   # a trailing quantifier
#   would bind to the wrapping group instead of the last letter and make the whole
#   acronym optional -- \bRSPD?\d became (?-i:\bRSPD)?\d, i.e. "any digit".


def case_fix(p):
    return _ACR.sub(lambda m: "(?-i:\\b" + m.group(1) + (m.group(2) or "") + ")", p)


LOCAL_RE = [(n, re.compile(case_fix(p), re.I)) for n, p in LOCAL]
INTL_RE = [(n, re.compile(case_fix(p), re.I)) for n, p in INTL]

# A dedicated Funding heading whose content OPENS with "None" is a declaration, even
# when unrelated boilerplate follows it ("None. Conflict of Interest None declared.").
NONE_LEAD = re.compile(r"^\s*(?:none|nil|not\s+applicable|n/?a|no\s+funding|no\s+fund)\b", re.I)
DEDICATED_SRC = {"funding", "source_of_support", "financial_support",
                 "grant_support", "role_of_funding"}
NOFUND_STRONG = re.compile(
    r"((?:received|receive)\s+no\s+(?:specific\s+|external\s+|dedicated\s+|direct\s+)?(?:grant|fund|financial|support|monetary)"
    r"|(?:did|does|do|has|have|had)\s+not\s+receive[d]?\s+(?:any\s+)?(?:specific\s+|external\s+)?(?:grant|fund|financial|monetary)"
    r"|no\s+(?:specific\s+|external\s+|dedicated\s+)?(?:grant|fund(?:ing|s)?|financial\s+support)\s+"
    r"(?:was|were|has\s+been)\s+(?:received|obtained|provided|available)"
    r"|no\s+fund(?:ing|s)\b|nofunding"
    r"|there\s+(?:was|is)\s+no\s+(?:funding|financial\s+support)"
    r"|(?:have|has)\s+no\s+funding\b"
    r"|non[-\s]?funded\b|\bunfunded\b|self[-\s]?fund(?:ed|ing)"
    r"|no\s+specific\s+fund(?:ing|s)?\b"
    r"|(?:was|were|is|are)\s+not\s+funded\b"
    r"|(?:fund(?:ing|s)?|financial\s+support(?:\s+and\s+sponsorship)?|sponsorship|"
    r"source\s+of\s+support)\s*[:\-]?\s*(?:none|nil|not\s+applicable|n/?a)\b)", re.I)

# Where an acknowledgement stops being an acknowledgement and becomes the article
# footer -- everything past this is bylines, affiliations and DOIs.
ACK_FOOTER = re.compile(
    r"(?:\bFrom\s+the\s+(?:The\s+)?Department|Address\s+correspondence|Correspondence\s+to|"
    r"\*?Corresponding\s+author|Received\s*:|Accepted\s*:|Published\s+online|©|"
    r"doi:\s*10\.|https?://|E-?mail\s*:)", re.I)
# An acknowledgement is mined for funders only if it mentions money at all.
ACK_MONEY = re.compile(
    r"\b(fund(?:ing|ed|s)?|grant|financial|sponsor(?:ed|ship)?|scholarship|"
    r"support(?:ed|ing)?|deanship|deputyship)\b", re.I)
# A STRICTER bar, used only where the acknowledgement is the ONLY evidence there is (no
# funding section at all). ACK_MONEY includes the bare word "support", which is fine as a
# filter when a funding statement also exists, but on its own it reads "we thank the Faculty
# for their immense support" as funding. This demands a money word or a named grant scheme.
ACK_STRONG = re.compile(
    r"\b(fund(?:ing|ed|s)?|grant(?:s)?|financial|sponsor(?:ed|ship)?|scholarship|"
    r"deanship|deputyship|monetary)\b"
    r"|researchers?\s+support(?:ing|ed)\s+project|research\s+group\s+(?:no|number)"
    r"|\b(?:RSP|RGP)\s*[-/D]?\s*\d", re.I)

THREE_LEVEL = {
    "local": "funded", "international": "funded", "both": "funded",
    "declared_none": "non_funded",
    "not_stated": "not_stated",
    # "needs_review" is resolved in the loop, with a reason recorded per row.
}

rows = list(csv.DictReader(open(SRC, encoding="utf-8-sig")))
out, review = [], []

for r in rows:
    stmt = r.get("funding_statement_verbatim", "") or ""
    # search the dedicated fields too -- a funder can be named in the acknowledgement
    # even when the Funding heading itself says nothing useful.
    # CORE = the paper's own funding declaration. WIDE adds weaker evidence
    # (acknowledgements, loose sentences) used only when CORE resolves nothing.
    # Precedence matters: a paper stating "received no financial support" is unfunded
    # even though its acknowledgement names the university the authors work at.
    core = " ".join([stmt, r.get("sec_funding", ""), r.get("sec_source_of_support", ""),
                     r.get("sec_financial_support", ""), r.get("sec_grant_support", ""),
                     r.get("sec_role_of_funding", "")])
    # Acknowledgement blocks run into the article footer, where AFFILIATIONS live --
    # "Mansoura University, Egypt" in a byline was read as an international funder.
    # Only mine the acknowledgement when it actually talks about money.
    ack = ACK_FOOTER.split(r.get("sec_acknowledgements", ""), 1)[0]
    wide = core + " " + r.get("funding_sentences", "") + " " + r.get("explicit_no_funding_hit", "")
    if ack and ACK_MONEY.search(ack):
        wide += " " + ack

    core_loc = sorted({n for n, rx in LOCAL_RE if rx.search(core)})
    core_itl = sorted({n for n, rx in INTL_RE if rx.search(core)})
    wide_loc = sorted({n for n, rx in LOCAL_RE if rx.search(wide)})
    wide_itl = sorted({n for n, rx in INTL_RE if rx.search(wide)})
    core_none = bool(NOFUND_STRONG.search(core)) or (
        r.get("primary_source", "") in DEDICATED_SRC and bool(NONE_LEAD.match(stmt)))
    declared_none = core_none or bool(NOFUND_STRONG.search(wide))

    def level_of(l, i):
        return "both" if (l and i) else "local" if l else "international"

    conf = "high"
    if not stmt.strip():
        # ⚠ FIXED 2026-08-24. This branch used to return not_stated at confidence HIGH
        # unconditionally, which discarded the `wide` evidence assembled just above -- so a
        # paper with no *Funding* heading never had its acknowledgement read, and was filed as
        # saying nothing about funding. Five papers naming King Saud University's "Researchers
        # Supporting Project" (RSP) scheme and Taif's equivalent were mislabelled that way, at
        # high confidence, so no review queue ever surfaced them
        # (docs/provenance/08_24_2026_funding_verification.md).
        #
        # The evidence bar here is HIGHER than for `wide` elsewhere: with no funding section,
        # the acknowledgement is all there is, and ACK_MONEY alone admits "we thank X for
        # their immense support", which is not a claim about money. ACK_STRONG demands an
        # actual money word or a named grant scheme, which keeps STUDY-0402 and STUDY-0808 out.
        if (wide_loc or wide_itl) and ACK_STRONG.search(wide):
            loc, itl = wide_loc, wide_itl
            level = level_of(wide_loc, wide_itl)
            why = "no funding section; funder named in the acknowledgement"
            conf = "medium"
        elif declared_none:
            # A paper with no funding section whose only money-related evidence is an
            # out-of-section no-funding phrase. Route it to the review queue rather than
            # call it unfunded; it still lands in not_stated at the 3-level either way.
            # ⚠ NOT the home of STUDY-0945 ("this work was not supported by the Veterans
            # Health Administration"): NOFUND_STRONG deliberately does not match a
            # BODY-SPECIFIC disclaimer, so that paper never reaches here and stays
            # not_stated. It is carried on the human worklist instead, with the [NAME-REDACTED]
            # drug-company sentence it resembles. Verified 2026-08-24 -- do not "fix" the
            # comment by loosening NOFUND_STRONG.
            loc, itl = [], []
            level, why = "needs_review", ("no funding section; only a body-specific or "
                                          "out-of-section no-funding phrase")
            conf = "low"
        else:
            loc, itl = [], []
            level, why = "not_stated", "no funding statement anywhere in the full text"
    elif core_loc or core_itl:
        loc, itl = core_loc, core_itl
        level = level_of(core_loc, core_itl)
        why = "funder(s) named in the paper's own funding statement"
        if core_none:
            why += "; statement ALSO carries a no-funding phrase -- check"
            conf = "low"
    elif core_none:
        loc, itl = [], []
        level, why = "declared_none", "funding statement explicitly declares no funding"
        if wide_loc or wide_itl:
            why += "; a funder name appears elsewhere in the paper -- check"
            conf = "low"
    elif wide_loc or wide_itl:
        loc, itl = wide_loc, wide_itl
        level = level_of(wide_loc, wide_itl)
        why = "funder(s) named only outside a funding statement (acknowledgement/sentence)"
        conf = "medium"
    elif declared_none:
        loc, itl = [], []
        level, why = "declared_none", "no-funding declaration outside a funding heading"
        conf = "medium"
    else:
        loc, itl = [], []
        level, why = "needs_review", "statement present but no funder resolved"
        conf = "low"

    # ---- the collapsed 3-level stratifier (TSA, 2026-08-23) ----
    # funded / non_funded / not_stated. Derived from the 6-level variable, never
    # measured separately, so the two can never disagree.
    three = THREE_LEVEL.get(level)
    if three is None:                       # needs_review
        # These papers DO carry text, but none of it states research funding: 11 are
        # the Saudi Medical Journal industry disclaimer ("not funded by any drug
        # company"), which is silent on non-commercial funding; the rest are a COI
        # line, an APC waiver, and one garbled sentence. Substantively not_stated --
        # not a parser fallback.
        three, three_note = "not_stated", "from needs_review: statement present but states no research funding"
    else:
        three_note = "from " + level

    rec = {
        "PMID": r["PMID"],
        "funding_level_firstpass": level,
        "funding_3level": three,
        "three_level_basis": three_note,
        "confidence": conf,
        "basis": why,
        "local_funders": "; ".join(loc),
        "intl_funders": "; ".join(itl),
        "declared_no_funding": int(declared_none),
        "self_funded": r.get("self_funded_hit", "0"),
        "oa_agreement_only": r.get("oa_agreement_hit", "0"),
        "statement_source": r.get("primary_source", ""),
        "funding_statement_verbatim": stmt,
    }
    out.append(rec)
    if conf in ("low", "medium"):
        review.append(rec)

cols = ["PMID", "funding_3level", "funding_level_firstpass", "three_level_basis",
        "confidence", "basis", "local_funders", "intl_funders",
        "declared_no_funding", "self_funded", "oa_agreement_only", "statement_source",
        "funding_statement_verbatim"]
for path, data in ((OUT, out), (REVIEW, review)):
    with open(path, "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        w.writerows(data)

n = len(out)
print("THREE-LEVEL stratifier, N = %d\n" % n)
c3 = Counter(r["funding_3level"] for r in out)
for k in ["funded", "non_funded", "not_stated"]:
    print("  %-12s %4d  %5.1f%%" % (k, c3.get(k, 0), 100.0 * c3.get(k, 0) / n))
print("\nSIX-LEVEL detail\n")
c = Counter(r["funding_level_firstpass"] for r in out)
for k in ["local", "international", "both", "declared_none", "not_stated", "needs_review"]:
    print("  %-15s %4d  %5.1f%%" % (k, c.get(k, 0), 100.0 * c.get(k, 0) / n))
print("\ntop Saudi funders named:")
cl = Counter(f for r in out for f in r["local_funders"].split("; ") if f)
for k, v in cl.most_common(12):
    print("   %-34s %d" % (k, v))
print("\ntop non-Saudi funders named:")
ci = Counter(f for r in out for f in r["intl_funders"].split("; ") if f)
for k, v in ci.most_common(10):
    print("   %-34s %d" % (k, v))
print("\nconfidence:")
cc = Counter(r["confidence"] for r in out)
for k in ("high", "medium", "low"):
    print("  %-8s %4d  %5.1f%%" % (k, cc.get(k, 0), 100.0 * cc.get(k, 0) / n))
print("\nreview worklist (medium+low): %d  ->  %s" % (len(review), REVIEW))
print("wrote", OUT)

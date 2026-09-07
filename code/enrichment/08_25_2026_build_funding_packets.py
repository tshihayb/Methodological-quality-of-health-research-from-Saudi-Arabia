# NOTE (public repository): 4 hard-coded study identifier(s) were
# rewritten to de-identified surrogates by tools/build_public_repo.py.
# They are rulings about particular studies rather than values the data
# can supply, so they have to travel with it.
# -*- coding: utf-8 -*-
"""Build one blind "funding reading packet" per paper, for the hand-read of the funding
stratifier (all 385 papers).

WHY A SECOND PACKET BUILDER
---------------------------
`08_23_2026_build_reading_packets.py` renders the FRONT pages, because that is where
bylines and affiliations live. **Funding does not live there.** It sits in a labelled
Funding / Financial support / Acknowledgements / Declarations block, almost always at the
END of the article -- and in some journals only in a boxed footnote on page 1. A reader
handed the author-linkage packets would be reading the wrong end of the paper.

WHAT EACH PACKET CONTAINS
-------------------------
  A. every labelled section the heading search can locate (the extractor's own
     `find_section`, so the reader sees exactly the text the machine had available);
  B. page 1 -- head (title/byline, for identification) and FOOT (the boxed funding
     footnote some journals print there);
  C. the END MATTER -- the last pages carrying real content, with the reference list
     elided. Walking backwards past reference-only pages matters: in several layouts the
     bibliography is the last three pages and the Funding block sits before it, while in
     others the Funding block sits AFTER it.
  D. a KEYWORD SWEEP over the whole reference-stripped paper: every occurrence of a
     money word with surrounding context. This is the part that lets a reader *prove the
     negative*. `not_stated` is a claim about the absence of evidence across ~40,000
     characters, and it is the label most likely to be wrong.

⚠ The reference list is stripped everywhere. Cited TITLES carry funding language
("Reports funded by the National Institutes of Health") and that trap has already fired
once in this project.

⚠ The packet is BLIND: it contains no machine label, no confidence, and no prior
adjudication. The hand-read is only worth running if it is an independent source.

⚠ Definitions are pulled from the pipeline by AST-filtering, never by importing: neither
funding script has an `if __name__ == "__main__"` guard, so a plain import RE-RUNS the
pipeline over its own outputs.

Output: data/quality-control/08_25_2026_funding_packets/<PMID>.txt
Run from the repository root.
"""
import ast
import io
import os
import re
import sys
import unicodedata
import warnings

warnings.simplefilter('ignore')
import fitz
import pandas as pd

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

MAP = 'data/provenance/08_23_2026_pdf_pmid_map_385.csv'
TXT = 'private/fulltext/pdf-by-pmid'
OUTDIR = 'data/quality-control/08_25_2026_funding_packets'

PAGE1_HEAD = 900          # enough to identify the paper; the reader is not judging authorship
PAGE1_FOOT = 2200         # the boxed funding/ethics footnote lives here
N_CONTENT_PAGES = 3       # content-bearing end pages to keep
LOOKBACK_PAGES = 8        # how far back to walk past reference-only pages
PAGE_CAP = 6000           # per-page cap in the end matter
SWEEP_CTX = 220           # characters either side of a money-word hit
SWEEP_MAX = 45            # hits per paper (a long paper can say "funding" 60 times)
WEAK_CTX = 130            # weak cues get a tighter window -- there are many more of them
WEAK_MAX = 25


def load_defs(path):
    """Load ONLY the definitions from a pipeline script -- no top-level work.
    (See the note in 08_24_2026_verify_funding_against_pdfs.py: importing either funding
    script runs it and rewrites its own output.)"""
    src = io.open(path, encoding='utf-8').read()
    tree = ast.parse(src, filename=path)
    keep = (ast.Import, ast.ImportFrom, ast.Assign, ast.AnnAssign,
            ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
    tree.body = [n for n in tree.body if isinstance(n, keep)]
    ns = {'__name__': 'pipeline_defs', '__file__': path}
    exec(compile(tree, path, 'exec'), ns)
    return ns


_ex = load_defs('code/enrichment/08_23_2026_extract_funding.py')
clean = _ex['clean']
find_section = _ex['find_section']
SECTION_LABELS = _ex['SECTION_LABELS']
REF_HEAD = _ex['REF_HEAD']

SECTION_TITLE = {
    'funding': 'Funding',
    'source_of_support': 'Source of support',
    'financial_support': 'Financial support',
    'grant_support': 'Grant support',
    'role_of_funding': 'Role of the funding source',
    'acknowledgements': 'Acknowledgements',
    'coi': 'Conflicts of interest',
    'declarations': 'Declarations',
}

# ---- the sweep runs in two tiers.
#
# STRONG: words that can only be about money, plus the NAMED SCHEMES that carry money
# without ever using a money word. That last group is not optional: "We deeply acknowledge
# Taif University for supporting this study through Taif University Researchers Supporting
# Project Number TURSP-2020/xxx" (STUDY-0137) contains no money word at all, and a first cut
# of this builder printed "NO MONEY WORD ANYWHERE" over a genuinely funded paper -- which
# would have walked the reader straight into `not_stated`.
STRONG = re.compile(
    r'\bfund(?:ing|ed|s|er|ers)?\b|\bgrant(?:s|ed)?\b|\bsponsor(?:ed|ship|s)?\b'
    r'|\bfinanc(?:e|ed|ial|ially)\b|\bdeanship\b|\bdeputyship\b|\bscholarship\b'
    r'|\bmonetary\b|\bsubsid(?:y|ies|ised|ized)\b|\bdonat(?:ion|ed|or)\w*\b'
    r'|\bendowment\b|\bbursary\b|\bstipend\b|\bremunerat\w*\b'
    r'|\barticle\s+processing\s+(?:charge|fee)\w*\b|\bopen\s+access\s+(?:fee|funding)\w*\b'
    # "supported IN PART by T32 HD049303" (STUDY-0853) -- the adverbial is not optional in
    # practice, and a strict "supported by" missed a genuinely NIH-funded paper.
    r'|\bsupport(?:ed|ing|s)?\s+(?:\w+\s+){0,3}(?:by|from)\b'
    # "Source of support: Nil" (STUDY-0976) is a funding DECLARATION with no money word in it.
    r'|sources?\s+of\s+support|support\s*[:\-]\s*(?:nil|none|no\b|n/?a|not\s+applicable)'
    r'|researchers?\s+supporting\s+project|research\s+group(?:s)?\s*(?:no\b|number|#)'
    r'|(?-i:\bRSPD?\b|\bRGP\b|\bTURSP\b|\bIFP\w*\b|\bAPC\b)'
    r'|(?:project|award|proposal|contract)\s*(?:no\.?|number|#)'
    r'|\bno\s+external\b|\breceived\s+no\b|\bin[-\s]kind\b',
    re.I)

# WEAK: the acknowledgement vocabulary. Bare "support"/"thank" is the commonest word in a
# discussion ("supported by the data", "supported by a greater t-value"), so these are
# shown separately, in a tighter window, and are NEVER by themselves evidence of money.
WEAK = re.compile(
    r'\bsupport\w*\b|\bthank\w*\b|\bappreciat\w*\b|\backnowledg\w*\b|\bgrateful\w*\b'
    r'|\bindebted\b|\bcourtesy\s+of\b|\bprovided\s+(?:by|the)\b', re.I)

# Where the reference list ends: some layouts print Funding / Author details AFTER it.
POST_REF = re.compile(
    r'\n[ \t]*(?:\d+[.)]?[ \t]*)?('
    r'fund(?:ing|s)\b|financial\s+support|acknowledge?ments?|author\s+(?:details|information|'
    r'contributions?)|declarations?|competing\s+interests?|conflicts?\s+of\s+interest|'
    r'data\s+availability|publisher\'?s\s+note|how\s+to\s+cite|supplementary|appendix'
    r')', re.I)


def longpath(p):
    """Windows MAX_PATH escape -- the granted PDF folder path is 139 chars, so long
    titles push past 260 and fitz.open() fails with FileNotFoundError."""
    p = os.path.abspath(str(p)).replace('/', '\\')
    return '\\\\?\\' + p if not p.startswith('\\\\?\\') else p


def deacc(s):
    s = unicodedata.normalize('NFKD', s)
    return ''.join(c for c in s if not unicodedata.combining(c))


def render_page(page):
    """Rebuild the page's visual lines, grouping spans by y coordinate. (Same approach as
    the linkage packets: some producers emit one word per line object.) Superscript is NOT
    marked here -- this read does not depend on it, and ^{} noise would bury the prose."""
    rows = {}
    for blk in page.get_text('dict').get('blocks', []):
        for line in blk.get('lines', []):
            for sp in line.get('spans', []):
                if not sp['text'].strip():
                    continue
                rows.setdefault(round(sp['bbox'][1] / 3.0), []).append(
                    (sp['bbox'][0], sp['text']))
    out = []
    for y in sorted(rows):
        line = re.sub(r'[ \t]+', ' ',
                      ''.join(deacc(t) for _, t in sorted(rows[y]))).strip()
        if line:
            out.append(line)
    return '\n'.join(out)


def ref_span(doc_text):
    """(start, end) of the reference list in the concatenated page text, or None.

    Start: the extractor's own REF_HEAD, last match past 35% of the document -- the same
    rule `strip_references` uses, so the packet and the pipeline agree on what a
    bibliography is. End: the next end-matter heading, because Funding is printed after
    the references in several layouts and must not be elided with them."""
    cuts = [m for m in REF_HEAD.finditer(doc_text) if m.start() > 0.35 * len(doc_text)]
    if not cuts:
        return None
    start = cuts[-1].start()
    nxt = POST_REF.search(doc_text, cuts[-1].end() + 200)
    return (start, nxt.start() if nxt else len(doc_text))


def elide(text, lo, hi, span):
    """Blank out whatever part of page [lo, hi) falls inside the reference span."""
    if not span:
        return text
    a, b = span
    if b <= lo or a >= hi:
        return text
    head = text[:max(0, a - lo)]
    tail = text[max(0, b - lo):] if b < hi else ''
    marker = '\n[... reference list elided ...]\n'
    return (head + marker + tail).strip()


def sweep(flat, rx, ctx):
    """Every hit of `rx`, grown to +/- ctx characters, with overlapping hits merged into
    one quotation so a Funding paragraph is printed once rather than six times."""
    spans = []
    for m in rx.finditer(flat):
        lo, hi = max(0, m.start() - ctx), min(len(flat), m.end() + ctx)
        if spans and lo <= spans[-1][1]:
            spans[-1][1] = max(spans[-1][1], hi)
            spans[-1][2] += 1
        else:
            spans.append([lo, hi, 1])
    return spans


def split_at_references(t):
    """(body-before-references, end-matter-after-references).

    ⚠ `strip_references` TRUNCATES at the bibliography, and several layouts print the
    Funding block AFTER it -- STUDY-0972's only funding statement sits 14,000 characters past
    the reference heading. Truncating there hides it completely. So the bibliography is cut
    out as a SPAN and the tail is kept, labelled, so the reader knows the text came from
    after the reference list."""
    cuts = [m for m in REF_HEAD.finditer(t) if m.start() > 0.35 * len(t)]
    if not cuts:
        return t, ''
    start = cuts[-1].start()
    nxt = POST_REF.search(t, cuts[-1].end() + 200)
    return t[:start], (t[nxt.start():] if nxt else '')


def main():
    os.makedirs(OUTDIR, exist_ok=True)
    m = pd.read_csv(MAP, encoding='utf-8-sig')
    ok = fail = 0
    sizes = []
    for _, r in m.iterrows():
        pmid = int(r['PMID'])
        try:
            doc = fitz.open(longpath(r['pdf_path']))
            pages = [render_page(doc[i]) for i in range(doc.page_count)]
            npages = doc.page_count
            doc.close()
        except Exception as e:
            print('  !! %s: cannot open -- %s' % (pmid, e))
            fail += 1
            continue

        # page offsets in the concatenated document
        SEP = '\n'
        offs, pos = [], 0
        for p in pages:
            offs.append((pos, pos + len(p)))
            pos += len(p) + len(SEP)
        doc_text = SEP.join(pages)
        span = ref_span(doc_text)

        chunks = ['# FUNDING READING PACKET -- PMID %d' % pmid,
                  '# source PDF: %s' % os.path.basename(str(r['pdf_path'])),
                  '# pages in PDF: %d' % npages,
                  '# Record what THIS PAPER PRINTS. No machine label is shown anywhere in '
                  'this packet, by design.',
                  '# Full text if the packet is not enough: %s/%d.txt' % (TXT, pmid),
                  '']

        # ---- A. labelled sections, from the pipeline's own heading search
        txt = ''
        tp = os.path.join(TXT, '%d.txt' % pmid)
        if os.path.exists(tp):
            txt = io.open(tp, encoding='utf-8', errors='replace').read().replace('\r', '')
        chunks.append('===== A. LABELLED SECTIONS LOCATED BY HEADING SEARCH =====')
        chunks.append('(located mechanically; a heading can be missed or over-run. '
                      'Treat as a pointer, not as an answer.)')
        found_any = False
        for k, _ in SECTION_LABELS:
            body = find_section(txt, k) if txt else ''
            if body and len(body) > 2:
                found_any = True
                chunks.append('--- [%s] ---' % SECTION_TITLE.get(k, k))
                chunks.append(body[:2500])
        if not found_any:
            chunks.append('(no labelled section found by heading search)')
        chunks.append('')

        # ---- B. page 1 head + foot
        p1 = pages[0] if pages else ''
        chunks.append('===== B. PAGE 1 (head, then FOOT -- boxed funding footnotes live '
                      'at the foot) =====')
        if len(p1) <= PAGE1_HEAD + PAGE1_FOOT + 80:
            chunks.append(p1)
        else:
            chunks.append(p1[:PAGE1_HEAD]
                          + '\n[... middle of page 1 elided -- abstract / body prose ...]\n'
                          + p1[-PAGE1_FOOT:])
        chunks.append('')

        # ---- C. end matter: content-bearing final pages, references elided
        chunks.append('===== C. END MATTER (final content-bearing pages, reference list '
                      'elided) =====')
        kept, content_pages = [], 0
        for i in range(npages - 1, max(-1, npages - 1 - LOOKBACK_PAGES), -1):
            body = elide(pages[i], offs[i][0], offs[i][1], span)
            real = body.replace('[... reference list elided ...]', '').strip()
            if len(real) >= 60:
                content_pages += 1
                kept.append((i, body[:PAGE_CAP]))
            elif i == npages - 1:          # always show the literal last page
                kept.append((i, body[:PAGE_CAP]))
            if content_pages >= N_CONTENT_PAGES:
                break
        for i, body in sorted(kept):
            chunks.append('----- page %d of %d -----' % (i + 1, npages))
            chunks.append(body if body.strip() else '(page is reference list only)')
        chunks.append('')

        # ---- D. keyword sweep over the whole paper
        src = txt if txt else doc_text
        pre, post = split_at_references(src)
        flat_pre, flat_post = clean(pre), clean(post)

        chunks.append('===== D. MONEY-WORD SWEEP OVER THE WHOLE PAPER (reference list '
                      'excluded) =====')
        chunks.append('(fund / grant / sponsor / financial / deanship / scholarship / APC '
                      '/ "supported by" / named schemes such as RSP, RGP, TURSP, '
                      '"Researchers Supporting Project". If nothing here commits the paper '
                      'to a funding claim, the paper is silent.)')
        n_strong = 0
        for tag, flat in (('', flat_pre), (' [AFTER THE REFERENCE LIST]', flat_post)):
            spans = sweep(flat, STRONG, SWEEP_CTX)
            n_strong += len(spans)
            for j, (lo, hi, _n) in enumerate(spans[:SWEEP_MAX], 1):
                chunks.append('[S%d]%s ...%s...' % (j, tag, flat[lo:hi]))
            if len(spans) > SWEEP_MAX:
                chunks.append('[... %d further hits not shown -- open the full text if the '
                              'call is still unclear ...]' % (len(spans) - SWEEP_MAX))
        if not n_strong:
            chunks.append('*** NO MONEY WORD ANYWHERE IN THIS PAPER ***')
        chunks.append('')

        # ---- E. acknowledgement vocabulary, kept apart from the money words on purpose
        chunks.append('===== E. THANKS / SUPPORT VOCABULARY (weak cues -- NOT evidence of '
                      'money on their own) =====')
        chunks.append('("thank", "support", "appreciation", "acknowledge", "grateful". '
                      'Thanks are not money: "we thank the School of Dental Sciences" is '
                      'not funding. But this is where an unlabelled funding sentence hides '
                      'when a paper has no Funding heading.)')
        n_weak = 0
        for tag, flat in (('', flat_pre), (' [AFTER THE REFERENCE LIST]', flat_post)):
            spans = sweep(flat, WEAK, WEAK_CTX)
            n_weak += len(spans)
            for j, (lo, hi, _n) in enumerate(spans[:WEAK_MAX], 1):
                chunks.append('[W%d]%s ...%s...' % (j, tag, flat[lo:hi]))
            if len(spans) > WEAK_MAX:
                chunks.append('[... %d further weak hits not shown ...]'
                              % (len(spans) - WEAK_MAX))
        if not n_weak:
            chunks.append('(none)')
        if not n_strong and not n_weak:
            chunks.append('*** THIS PAPER CONTAINS NO FUNDING VOCABULARY OF ANY KIND ***')
        chunks.append('')

        out = '\n'.join(chunks)
        with io.open(os.path.join(OUTDIR, '%d.txt' % pmid), 'w', encoding='utf-8') as f:
            f.write(out)
        sizes.append(len(out))
        ok += 1

    print('wrote %d packets to %s  (%d failed)' % (ok, OUTDIR, fail))
    if sizes:
        sizes.sort()
        print('packet size: median %d  p90 %d  max %d chars'
              % (sizes[len(sizes) // 2], sizes[int(len(sizes) * 0.9)], sizes[-1]))


if __name__ == '__main__':
    main()

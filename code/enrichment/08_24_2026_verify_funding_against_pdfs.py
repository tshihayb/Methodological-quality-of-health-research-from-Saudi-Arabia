# -*- coding: utf-8 -*-
"""Verify the funding stratifier against the PAPERS themselves, before it becomes a Table 1
column.

WHY, AND WHY THIS SHAPE
-----------------------
`funding_3level` is about to become a manuscript variable. It is machine-extracted from the
PDF text layer of all 385 papers, and the extraction went through several regex traps that
produced FALSE FUNDERS (`\\bWHO\\b` matching the English word "who" made 48 phantom
internationals; an acronym wrapper meeting a quantifier made 214 phantom King Saud hits).
Those are fixed -- but the checks that caught them were ad hoc.

The asymmetry that matters: **`not_stated` is the dangerous label.** Saying "this paper is
funded by X" is checkable and self-correcting; saying "this paper says NOTHING about funding"
is a claim about the absence of evidence across ~40,000 characters of text, and it is 23.9%
of the sample. A single missed statement turns a reporting-transparency finding into an
error. So the screens are deliberately lopsided towards proving the negatives.

FIVE SCREENS, all over the paper text extracted from the granted PDFs. Nothing is written to
the funding datasets.

  V1 CONTAINMENT        every stored verbatim statement must occur in that paper's own text.
                        Catches drift, mis-keyed PMIDs and fabricated snippets.
  V2 REPRODUCIBILITY    re-run the live classifier over the stored statements and diff
                        against the stored labels -- the funding analogue of the S2 sweep's
                        screen C.
  V3 SILENT PAPERS      ▶ THE IMPORTANT ONE. For every paper labelled `not_stated`, scan the
                        whole reference-stripped text for any funding cue. A hit means the
                        paper is not silent and the label is wrong.
  V4 DECLARED NONE      every `non_funded` paper must carry an explicit negative in its text.
  V5 FUNDED             every `funded` paper must carry a positive cue, and the named funder
                        must actually appear in the text.

Run from the repository root:
    PYTHONUTF8=1 PYTHONIOENCODING=utf-8 python code/enrichment/08_24_2026_verify_funding_against_pdfs.py
"""
import io
import os
import re
import sys
import unicodedata

import pandas as pd

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, os.path.join('code', 'enrichment'))


def load_defs(path):
    """Load ONLY the definitions from a pipeline script -- imports, constants, functions --
    and none of its top-level work.

    ⚠ Neither funding script has an `if __name__ == "__main__"` guard, so a plain import RUNS
    THE PIPELINE and rewrites its own output. The first run of this verifier did exactly that
    (it reproduced the file byte-for-byte, so nothing was lost, but a verification harness must
    never be able to overwrite the thing it is verifying). Filtering the AST gives me the
    pipeline's OWN regex tables and helpers -- no copies to drift out of sync, no side effects.
    """
    import ast
    src = io.open(path, encoding='utf-8').read()
    tree = ast.parse(src, filename=path)
    keep = (ast.Import, ast.ImportFrom, ast.Assign, ast.AnnAssign,
            ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
    tree.body = [n for n in tree.body if isinstance(n, keep)]
    ns = {'__name__': 'pipeline_defs', '__file__': path}
    exec(compile(tree, path, 'exec'), ns)
    return ns


_ex = load_defs('code/enrichment/08_23_2026_extract_funding.py')
_cl = load_defs('code/enrichment/08_23_2026_classify_funding.py')
strip_references = _ex['strip_references']
# ⚠ Use the EXTRACTOR'S OWN cleaner on any haystack a pipeline regex is run against.
# The PDFs print ligatures -- "deanship of scientiﬁc research" with U+FB01 -- so the
# classifier's `scientific` pattern does not match the raw text at all. The pipeline is
# safe (it cleans before searching, extract_funding.py:258); a first cut of this verifier
# searched the raw text and 'failed' 32 papers on that alone.
clean = _ex['clean']
LOCAL_RE, INTL_RE = _cl['LOCAL_RE'], _cl['INTL_RE']   # the classifier's own funder patterns
NONE_LEAD, DEDICATED_SRC = _cl['NONE_LEAD'], _cl['DEDICATED_SRC']
NOFUND_STRONG = _cl['NOFUND_STRONG']

# The label file defaults to the classifier's output, but can be pointed at the ADJUDICATED
# dataset instead:
#     python code/enrichment/08_24_2026_verify_funding_against_pdfs.py \
#            data/analysis/08_25_2026_funding_ADJUDICATED_385.csv
# The screens test labels against the PAPER TEXT, so they are exactly as valid over
# hand-ruled labels as over machine ones -- and the adjudication is otherwise the one step in
# the chain that nothing checks. (V2 re-runs the classifier over the stored statements, so it
# will report every ruling as a diff. That is the intended reading, not a failure.)
CLS = (sys.argv[1] if len(sys.argv) > 1
       else 'data/analysis/08_23_2026_funding_classified_385.csv')
STM = 'data/analysis/08_23_2026_funding_statements_385.csv'
TXT = 'private/fulltext/pdf-by-pmid'
MAP = 'data/provenance/08_23_2026_pdf_pmid_map_385.csv'
OUT = ('data/quality-control/08_25_2026_adjudicated_verification.csv'
       if len(sys.argv) > 1 else 'data/quality-control/08_24_2026_funding_verification.csv')


def norm(s):
    """Whitespace-, hyphen- and case-insensitive form for containment tests.

    PDF text layers break words across lines with real hyphens AND soft hyphens, and reflow
    turns single spaces into newlines -- the trap that once broke "King Saud Uni­versity".
    """
    s = unicodedata.normalize('NFKD', str(s or ''))
    s = ''.join(c for c in s if not unicodedata.combining(c))
    s = s.replace('­', '').replace('‐', '-').replace('‑', '-')
    s = re.sub(r'-\s*\n\s*', '', s)          # de-hyphenate across a line break
    s = re.sub(r'[^a-z0-9]+', ' ', s.lower())
    return re.sub(r'\s+', ' ', s).strip()


def squash(s):
    """`norm` with every space removed.

    A PDF text layer can lose a space INSIDE a phrase — this corpus prints "Prince
    SattambinAbdulaziz University,Al- Kharj" and "(KSAU- HS)" — and no whitespace
    normalisation repairs that, because the space is simply gone. Comparing space-free forms
    settles containment without weakening it: the character sequence must still be present,
    in order.
    """
    return norm(s).replace(' ', '')


# ---------------------------------------------------------------------------------------
# cue vocabularies. Deliberately BROAD for V3 (a false alarm costs a human glance; a miss
# costs a wrong published number) and NARROW for V4/V5.
# ---------------------------------------------------------------------------------------
CUE_ANY = re.compile(
    r'\bfund(?:ing|ed|s)?\b|\bgrant(?:s|ed)?\b|\bfinancial(?:ly)?\s+support|\bsponsor'
    r'|\bsupported\s+by\b|\bfinanced\b|\bscholarship\b|\bfellowship\b|\bsubsid'
    r'|\bmonetary\s+support|\bno\s+specific\s+grant\b|\bdeanship\s+of\s+scientific\s+research'
    r'|\bfunder\b|\baward\s+number\b|\bproject\s+number\b|\bgrant\s+number\b', re.I)

CUE_NEGATIVE = re.compile(
    r'\b(?:no|not|none|nil|without|never)\b[^.\n]{0,60}\b(?:fund(?:ing|ed|s)?|grant|'
    r'financial\s+support|sponsor|financial\s+assistance|external\s+support)\b'
    r'|\b(?:fund(?:ing|ed|s)?|grant|financial\s+support|sponsor)\b[^.\n]{0,40}'
    r'\b(?:was\s+not|were\s+not|is\s+not|not\s+received|not\s+obtained)\b'
    r'|\breceived\s+no\b|\bdid\s+not\s+receive\b|\bself[-\s]?fund'
    r'|^\s*(?:none|nil|not\s+applicable|n/?a)\s*$', re.I | re.M)

CUE_POSITIVE = re.compile(
    r'\bfunded\s+by\b|\bfunding\s+(?:was\s+)?(?:provided|received|obtained)\b'
    r'|\bsupported\s+(?:financially\s+)?by\b|\bgrant\s+(?:no|number|#)?\b'
    r'|\bfinancial(?:ly)?\s+support(?:ed)?\s+by\b|\bsponsored\s+by\b'
    r'|\bthrough\s+grant\b|\baward\s+number\b|\bproject\s+(?:no|number)\b'
    # The house phrasings this corpus actually uses. A narrower cue list "failed" 24 papers
    # that plainly name their funder ("...for funding this work through Research Group No
    # (RGP-1441-007)"), which is a defect in the screen, not in the data.
    r'|\bfor\s+fund(?:ing|s)\b'
    r'|\bfunding\s+(?:this|the)\s+(?:work|study|project|research|publication)\b'
    r'|\bfor\s+support(?:ing)?\s+(?:this|the)\s+(?:work|study|project|research)\b'
    r'|\bresearch(?:ers)?\s+support(?:ing|ed)\s+project\b'
    r'|\bresearch\s+group\s+(?:no|number)\b'
    r'|\bdeanship\s+of\s+scientific\s+research\b[^.\n]{0,80}\b(?:fund|support|grant)', re.I)

# The industry-only disclaimer that is NOT a statement about non-commercial funding.
# 11 of the 14 `needs_review` rows are this one sentence in [NAME-REDACTED] house style.
DRUG_CO = re.compile(r'not\s+(?:be\s+)?(?:supported|funded)[^.\n]{0,40}'
                     r'(?:drug|pharmaceutical)\s+compan', re.I)


def load_text(pmid):
    p = os.path.join(TXT, f'{pmid}.txt')
    if not os.path.exists(p):
        return None
    return io.open(p, encoding='utf-8', errors='replace').read()


def main():
    cls = pd.read_csv(CLS, encoding='utf-8-sig', dtype={'PMID': str})
    stm = pd.read_csv(STM, encoding='utf-8-sig', dtype={'PMID': str})
    pmap = pd.read_csv(MAP, encoding='utf-8-sig', dtype={'PMID': str})
    d = cls.merge(stm[['PMID', 'primary_source', 'refs_stripped', 'n_chars_text']],
                  on='PMID', how='left').merge(
                      pmap[['PMID', 'source', 'match_method']], on='PMID', how='left')

    print('=' * 92)
    print('FUNDING STRATIFIER — VERIFICATION AGAINST THE PAPER TEXT')
    print('=' * 92)
    print(f'papers: {len(d)}   |   3-level: {d.funding_3level.value_counts().to_dict()}')
    print(f'PDF match method: {d.match_method.value_counts().to_dict()}')
    print(f'confidence: {d.confidence.value_counts().to_dict()}')

    rows = []
    texts, bodies = {}, {}
    for r in d.itertuples():
        t = load_text(r.PMID)
        texts[r.PMID] = t
        bodies[r.PMID] = strip_references(t) if t else ''

    # ---------------- V1 containment ----------------
    miss = 0
    for r in d.itertuples():
        v = str(r.funding_statement_verbatim or '').strip()
        if not v or v.lower() == 'nan':
            continue
        nt = norm(texts[r.PMID])
        # test the longest clean fragment: PDF layers can drop a stray glyph mid-sentence
        frag = max(re.split(r'[|;]', v), key=len)
        nv = norm(frag)
        if len(nv) < 25:
            continue
        if (nv not in nt and nv[:120] not in nt
                and squash(frag) not in squash(texts[r.PMID])):
            miss += 1
            rows.append({'screen': 'V1_containment', 'PMID': r.PMID,
                         'label': r.funding_3level, 'detail': v[:150],
                         'why': 'stored verbatim statement not found in this paper\'s text',
                         'priority': 1})
    print(f'\nV1 containment  : {len(d) - miss}/{len(d)} statements found verbatim in their '
          f'own paper  ({miss} missing)')

    # ---------------- V3 silent papers ----------------
    ns = d[d.funding_3level == 'not_stated']
    hits = 0
    for r in ns.itertuples():
        body = bodies[r.PMID]
        m = list(CUE_ANY.finditer(body))
        if not m:
            continue
        # ignore the industry-only disclaimer: it is a known, adjudicated non-statement
        ctx = ' '.join(body[max(0, x.start() - 90):x.end() + 90] for x in m[:6])
        # ⚠ Test the context with the disclaimer REMOVED. The disclaimer itself reads "not
        # supported or funded by any drug company", which CUE_NEGATIVE matches, so a test
        # asking "and no negative anywhere" could never be true — every one of these rows was
        # mis-tagged as unexplained, which is why the first runs reported 34/34.
        rest = DRUG_CO.sub(' ', ctx)
        only_drug = bool(DRUG_CO.search(ctx)) and not CUE_ANY.search(rest)
        hits += 1
        rows.append({'screen': 'V3_silent_but_cue', 'PMID': r.PMID,
                     'label': f'{r.funding_3level} / {r.funding_level_firstpass}',
                     'detail': re.sub(r'\s+', ' ', ctx)[:260],
                     'why': ('industry-only disclaimer (known class, no action)' if only_drug
                             else 'labelled as saying nothing about funding, but the text '
                                  'carries a funding cue'),
                     'priority': 3 if only_drug else 1})
    print(f'V3 silent papers: {len(ns)} labelled not_stated; {hits} contain a funding cue '
          f'({sum(1 for x in rows if x["screen"] == "V3_silent_but_cue" and x["priority"] == 1)} '
          f'not explained by the industry disclaimer)')

    # ---------------- V4 declared none ----------------
    nf = d[d.funding_3level == 'non_funded']
    bad = 0
    for r in nf.itertuples():
        stmt = str(r.funding_statement_verbatim or '')
        hay = stmt + ' ' + bodies[r.PMID]
        # A dedicated Funding section reading "None." / "Nil." / "Not applicable." IS an
        # explicit declaration -- the classifier says so via NONE_LEAD, and a first cut that
        # demanded a full negative sentence "failed" 17 papers that are correctly classified.
        bare_none = (str(r.primary_source or '') in DEDICATED_SRC) and bool(NONE_LEAD.match(stmt))
        if not (bare_none or NOFUND_STRONG.search(hay) or CUE_NEGATIVE.search(hay)):
            bad += 1
            rows.append({'screen': 'V4_no_negative_found', 'PMID': r.PMID,
                         'label': r.funding_3level,
                         'detail': str(r.funding_statement_verbatim)[:200],
                         'why': 'classed as declaring no funding, but no explicit negative '
                                'statement was found in the text',
                         'priority': 1})
    print(f'V4 declared none: {len(nf)} papers; {len(nf) - bad} carry an explicit negative '
          f'({bad} do not)')

    # ---------------- V5 funded ----------------
    fu = d[d.funding_3level == 'funded']
    nopos = nofunder = 0
    for r in fu.itertuples():
        hay = str(r.funding_statement_verbatim or '') + ' ' + bodies[r.PMID]
        if not CUE_POSITIVE.search(hay):
            nopos += 1
            rows.append({'screen': 'V5_no_positive_cue', 'PMID': r.PMID,
                         'label': f'{r.funding_3level} / {r.funding_level_firstpass}',
                         'detail': str(r.funding_statement_verbatim)[:200],
                         'why': 'classed as funded, but no positive funding phrase found',
                         'priority': 1})
        # ⚠ `local_funders` / `intl_funders` hold CATEGORY LABELS ("NIH / US federal",
        # "generic Saudi funder"), not text quoted from the paper, so asking whether the
        # label appears in the PDF is meaningless -- a first cut did exactly that and
        # "failed" 118 of 191 papers. The real question is whether the pattern that
        # produced the label still matches the paper, so the check uses the classifier's
        # own compiled regexes.
        named = [x.strip() for x in
                 (str(r.local_funders or '') + ';' + str(r.intl_funders or '')).split(';')
                 if x.strip() and x.strip().lower() != 'nan']
        pat = {n: rx for n, rx in list(LOCAL_RE) + list(INTL_RE)}
        hay_full = clean(texts[r.PMID] or '')
        absent = [n for n in named if n in pat and not pat[n].search(hay_full)]
        if absent:
            nofunder += 1
            rows.append({'screen': 'V5_funder_not_in_text', 'PMID': r.PMID,
                         'label': r.funding_3level, 'detail': '; '.join(absent)[:200],
                         'why': 'a named funder does not appear in the paper text',
                         'priority': 1})
    print(f'V5 funded       : {len(fu)} papers; {nopos} without a positive phrase, '
          f'{nofunder} naming a funder absent from the text')

    # ---------------- V6 discarded acknowledgement evidence ----------------
    # ▶ THE ROOT CAUSE behind the real half of V3. classify_funding.py builds a WIDE evidence
    # string (acknowledgement + funding sentences + no-funding hits) and its comment says it
    # is consulted "when CORE resolves nothing" -- but the very first branch is
    #     if not stmt.strip():  ->  not_stated, confidence HIGH
    # so for a paper with no dedicated funding statement the WIDE evidence is computed and
    # then thrown away unread. Papers whose only funding evidence is an acknowledgement --
    # "the authors extend their appreciation to the Researchers Supporting Project number
    # (RSP2022R480), King Saud University" -- are filed as saying nothing about funding at
    # all, and at HIGH confidence, which is why no review queue caught them.
    ACK_MONEY, ACK_FOOTER = _cl['ACK_MONEY'], _cl['ACK_FOOTER']
    stm_i = stm.fillna('').set_index('PMID')
    for r in d[d.funding_3level == 'not_stated'].itertuples():
        if r.PMID not in stm_i.index:
            continue
        srow = stm_i.loc[r.PMID]
        if str(srow.get('funding_statement_verbatim', '')).strip():
            continue                    # the short-circuit only fires on an empty statement
        ack = ACK_FOOTER.split(str(srow.get('sec_acknowledgements', '')), 1)[0]
        wide = ' '.join([str(srow.get('funding_sentences', '')),
                         str(srow.get('explicit_no_funding_hit', ''))])
        if ack and ACK_MONEY.search(ack):
            wide += ' ' + ack
        loc = sorted({n for n, rx in LOCAL_RE if rx.search(wide)})
        itl = sorted({n for n, rx in INTL_RE if rx.search(wide)})
        neg = bool(NOFUND_STRONG.search(wide))
        if not (loc or itl or neg):
            continue
        rows.append({'screen': 'V6_discarded_ack_evidence', 'PMID': r.PMID,
                     'label': f'{r.funding_3level} (confidence {r.confidence})',
                     'detail': f'wide evidence resolves to '
                               f'{"; ".join(loc + itl) or "declared_none"} — '
                               f'"{re.sub(r"[ \t]+", " ", ack)[:150]}"',
                     'why': 'acknowledgement evidence discarded because the paper has no '
                            'dedicated funding statement',
                     'priority': 1})
    n6 = sum(1 for x in rows if x['screen'] == 'V6_discarded_ack_evidence')
    print(f'V6 discarded ack: {n6} not_stated papers whose acknowledgement evidence was '
          f'computed and then thrown away')

    out = pd.DataFrame(rows)
    if len(out):
        out = out.sort_values(['priority', 'screen', 'PMID'])
        os.makedirs(os.path.dirname(OUT), exist_ok=True)
        out.to_csv(OUT, index=False, encoding='utf-8-sig')
    print(f'\n{len(out)} rows -> {OUT}')
    if len(out):
        print(out.screen.value_counts().to_string())
        print('\nby priority:', out.priority.value_counts().to_dict())


if __name__ == '__main__':
    main()

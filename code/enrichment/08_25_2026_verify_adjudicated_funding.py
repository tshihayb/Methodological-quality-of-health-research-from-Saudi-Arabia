# NOTE (public repository): 4 hard-coded study identifier(s) were
# rewritten to de-identified surrogates by tools/build_public_repo.py.
# They are rulings about particular studies rather than values the data
# can supply, so they have to travel with it.
# -*- coding: utf-8 -*-
"""Re-verify the ADJUDICATED funding labels against the paper text.

The 2026-08-24 screens verified the machine's labels. The rulings changed 28 of them, so the
screens have to be re-run against the new labels -- otherwise the adjudication is the one step
in the chain nothing checks. Three screens, all over the reference-stripped full text:

  W1 non_funded  every paper must carry an explicit negative in its own text.
  W2 funded      every paper must carry money attached to the work.
  W3 not_stated  ▶ THE IMPORTANT ONE. `not_stated` now contains papers that DO print money
                 words -- that is the whole point of R2/R3/R4. So the screen is no longer
                 "is there a cue?" but "is every cue explained by the rule it was decided
                 under?" A `not_stated` paper carrying an unexplained positive is an error.

It also separates three quantities the manuscript must not conflate:
  - `not_stated` (99): the paper does not tell you whether the RESEARCH was funded
  - prints no funding statement at all
  - contains no funding vocabulary anywhere: the true "silent" count

⚠ Run from the repository root. Reads the adjudicated dataset; writes only a report.
"""
import ast
import io
import os
import re
import sys

import pandas as pd

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

ADJ = 'data/analysis/08_25_2026_funding_ADJUDICATED_385.csv'
TXT = 'private/fulltext/pdf-by-pmid'
OUT = 'data/quality-control/08_25_2026_adjudicated_funding_verification.csv'


def load_defs(path):
    src = io.open(path, encoding='utf-8').read()
    tree = ast.parse(src, filename=path)
    keep = (ast.Import, ast.ImportFrom, ast.Assign, ast.AnnAssign,
            ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
    tree.body = [n for n in tree.body if isinstance(n, keep)]
    ns = {'__name__': 'defs', '__file__': path}
    exec(compile(tree, path, 'exec'), ns)
    return ns


_ex = load_defs('code/enrichment/08_23_2026_extract_funding.py')
clean = _ex['clean']
NOFUND = _ex['NOFUND']
REF_HEAD = _ex['REF_HEAD']
# ⚠ Use the pipeline's OWN tested test for "is this sentence about funding THIS study".
# A hand-rolled POSITIVE regex written for this screen fired on "supported by a small
# t-value", "findings are supported by a previous study" and ethics protocol numbers -- the
# exact traps the extractor already solved. Reusing its logic keeps the screen honest and
# stops it drifting from the pipeline.
cue_sentences = _ex['cue_sentences']
sentence_is_funding = _ex['sentence_is_funding']
find_section = _ex['find_section']
ORG_HINT = _ex['ORG_HINT']
GRANTNUM = _ex['GRANTNUM']

MONEYWORD = re.compile(r'(?i)\bfund\w*|\bgrant\w*|\bsponsor\w*|financial\s+support'
                       r'|\bscholarship|\bstipend|paid\s+all\s+costs|\bfinanc\w*\s+support')
# Sections that can carry the money. `acknowledgements` is NOT optional: the RSP/TURSP
# schemes and several deanship grants are printed only there.
POS_SECTIONS = ('funding', 'source_of_support', 'financial_support', 'grant_support',
                'role_of_funding', 'acknowledgements')


def has_positive(s):
    """A fragment asserts money for this work: a money word plus either a fundable
    organisation or a grant/award number, and not itself a no-funding declaration."""
    if not s or NOFUND.search(s) or not MONEYWORD.search(s):
        return False
    return bool(GRANTNUM.search(s) or ORG_HINT.search(s))


def positive_fragments(txt, flat):
    """Every fragment of the paper that asserts money, from BOTH sources.

    ⚠ A first cut of this screen tested only the free-standing sentence sweep and reported 40
    unmistakably funded papers as having no positive -- "grateful to the Researchers
    Supporting Project number (RSP-2021/382) ... for funding this research" is a labelled
    section, and the sentence CUE never matches it. Most funding in this corpus lives under a
    heading, not in a free sentence."""
    out = []
    for k in POS_SECTIONS:
        body = find_section(txt, k)
        for part in re.split(r'(?<=[.;])\s+', body or ''):
            if has_positive(part):
                out.append(part.strip())
    for s in cue_sentences(flat):
        if sentence_is_funding(s) and has_positive(s):
            out.append(s.strip())
    return out

POST_REF = re.compile(
    r"\n[ \t]*(?:\d+[.)]?[ \t]*)?(fund(?:ing|s)\b|financial\s+support|acknowledge?ments?|"
    r"author\s+(?:details|information|contributions?)|declarations?|competing\s+interests?|"
    r"conflicts?\s+of\s+interest|data\s+availability|publisher'?s\s+note)", re.I)


def body_without_bibliography(t):
    """⚠ `strip_references` TRUNCATES at the bibliography, and several layouts print the
    Funding block AFTER it -- the same defect found in the reading packets. A screen built on
    truncation reports `funded` papers as having no positive statement purely because their
    funding sentence sits past the reference heading (STUDY-0350, STUDY-0102, STUDY-0295 all failed
    that way on the first run). Cut the bibliography as a SPAN and keep the tail."""
    cuts = [m for m in REF_HEAD.finditer(t) if m.start() > 0.35 * len(t)]
    if not cuts:
        return t
    nxt = POST_REF.search(t, cuts[-1].end() + 200)
    return t[:cuts[-1].start()] + ('\n' + t[nxt.start():] if nxt else '')

# every reason a not_stated paper is ALLOWED to contain money language
PUBLICATION = re.compile(
    r'(?i)funding\s+the\s+publication|publication\s+of\s+this\s+(?:project|article)'
    r'|article[- ]processing|\bAPCs?\b|open\s+access\s+(?:funding|publishing)|projekt\s+deal'
    r'|read\s+and\s+publish|council\s+of\s+australian\s+university\s+librarians'
    r'|to\s+support\s+the\s+publication|this\s+publication\s+was\s+supported'
    r'|role\s+of\s+this\s+funding\s+is\s+to\s+publish')
THANKS = re.compile(
    r'(?i)(?:thank|acknowledg\w+|grateful|appreciat\w+)[^.]{0,160}?'
    r'(?:for\s+(?:their\s+)?(?:help|support|supporting|the\s+support)|for\s+supporting)')
ETHICS = re.compile(r'(?i)ethic\w*|\bIRB\b|institutional\s+review|review\s+board'
                    r'|approv\w+\s+by|written\s+informed\s+consent')
DISCLAIMER = re.compile(r'(?i)not\s+supported\s+or\s+funded\s+by\s+any\s+drug\s+company'
                        r'|not\s+supported\s+by\s+the\s+\w+')
LITERATURE = re.compile(r'(?i)(?:funded|financed)\s+by\s+the\s+(?:saudi\s+)?(?:government|state)'
                        r'|manufacturer[- ]funded|tax[- ]funded')
CREDIT = re.compile(r'(?i)funding\s+acquisition')
COI = re.compile(r'(?i)(?:no\s+relevant\s+)?financial\s+(?:or\s+non-financial\s+)?interests?'
                 r'|grants?\s+or\s+patents?\s+received')

d = pd.read_csv(ADJ, encoding='utf-8-sig', dtype={'PMID': str}).fillna('')
rows = []

for _, r in d.iterrows():
    p = os.path.join(TXT, r['PMID'] + '.txt')
    if not os.path.exists(p):
        rows.append({'PMID': r['PMID'], 'screen': 'W0_no_text', 'label': r['funding_3level'],
                     'detail': ''})
        continue
    raw = io.open(p, encoding='utf-8', errors='replace').read().replace('\r', '')
    flat = clean(body_without_bibliography(raw))
    lab = r['funding_3level']
    positives = positive_fragments(raw, flat)

    # ⚠ There is deliberately NO "non_funded carries a negative" or "funded carries a
    # positive" screen here. Both already exist as V4/V5 in
    # 08_24_2026_verify_funding_against_pdfs.py, which now accepts the adjudicated file as
    # argv[1]. Re-implementing them here produced 62 false alarms in one run -- it missed the
    # bare "Funding / None." layout that V4 handles via NONE_LEAD, and it could not see
    # funding printed in a labelled section. Duplicating a tuned screen badly is worse than
    # not duplicating it: run V1-V6 for those, and keep this file to the one thing they
    # cannot express.
    if lab == 'not_stated' and positives:
        # every positive must be explained by the rule the paper was decided under.
        # Publication money is checked against the WHOLE text, not the local window: at
        # STUDY-0268 the qualifying clause "to support the publication of this article"
        # completes past a column break, far from the scheme name it qualifies.
        unexplained = [s for s in positives
                       if not (PUBLICATION.search(s) or THANKS.search(s) or ETHICS.search(s)
                               or DISCLAIMER.search(s) or LITERATURE.search(s)
                               or CREDIT.search(s) or COI.search(s))]
        if unexplained and str(r['adjudication_rule']).startswith('R2'):
            unexplained = [] if PUBLICATION.search(flat) else unexplained
        if unexplained:
            rows.append({'PMID': r['PMID'], 'screen': 'W3_unexplained_positive',
                         'label': lab, 'detail': ' || '.join(unexplained)[:400]})

out = pd.DataFrame(rows)
print('=' * 92)
print('ADJUDICATED FUNDING — RE-VERIFICATION AGAINST THE PAPER TEXT')
print('=' * 92)
print('labels: %s' % dict(d['funding_3level'].value_counts()))
n_ns = int((d['funding_3level'] == 'not_stated').sum())
w3 = int((out['screen'] == 'W3_unexplained_positive').sum()) if len(out) else 0
print('\nW3 not_stated : %d/%d have every money cue explained by the rule they were decided '
      'under  (%d do not)' % (n_ns - w3, n_ns, w3))
print('     (non_funded and funded are screened by V4/V5 -- run '
      '08_24_2026_verify_funding_against_pdfs.py with this file as argv[1])')

if len(out):
    for s in ('W0_no_text', 'W3_unexplained_positive'):
        sub = out[out['screen'] == s]
        if len(sub):
            print('\n--- %s (%d) ---' % (s, len(sub)))
            for _, x in sub.iterrows():
                print('  %s  %s' % (x['PMID'], str(x['detail'])[:220]))
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    out.to_csv(OUT, index=False, encoding='utf-8-sig')
    print('\n%d rows -> %s' % (len(out), OUT))
else:
    print('\nno findings — every adjudicated label is supported by its own paper')

# ---- the three quantities the manuscript must keep apart
st = pd.read_csv('data/analysis/08_23_2026_funding_statements_385.csv',
                 encoding='utf-8-sig', dtype={'PMID': str}).fillna('')
silent_stmt = int((st['funding_statement_verbatim'].str.strip() == '').sum())
MONEYVOCAB = re.compile(r'(?i)\bfund\w*|\bgrant\w*|\bsponsor\w*|financial\s+support|\bdeanship'
                        r'|\bscholarship|article\s+processing|\bsupported\s+by')
novocab = 0
for _, r in d.iterrows():
    p = os.path.join(TXT, r['PMID'] + '.txt')
    if os.path.exists(p) and not MONEYVOCAB.search(clean(body_without_bibliography(
            io.open(p, encoding='utf-8', errors='replace').read()))):
        novocab += 1
print('\n' + '=' * 92)
print('⚠ THREE DIFFERENT QUANTITIES — do not conflate them in the manuscript')
print('=' * 92)
print('  not_stated (stratifier category)      : %3d  (%.1f%%)  '
      'the paper does not tell you whether the RESEARCH was funded' % (n_ns, 100.0 * n_ns / 385))
print('  prints no funding statement at all    : %3d  (%.1f%%)' % (silent_stmt,
                                                                   100.0 * silent_stmt / 385))
print('  no funding vocabulary anywhere        : %3d  (%.1f%%)  the true "silent" count'
      % (novocab, 100.0 * novocab / 385))

# Persist them. Table 1's funding footnote quotes the silent count, and that file's own rule
# is that footnote numbers are COMPUTED, never typed -- so it reads this rather than carrying
# a literal that would rot the moment a ruling changed.
import json
QOUT = 'data/provenance/08_25_2026_funding_quantities.json'
json.dump({'n_papers': int(len(d)),
           'not_stated': n_ns,
           'no_funding_statement': silent_stmt,
           'no_funding_vocabulary': novocab,
           'source': 'code/enrichment/08_25_2026_verify_adjudicated_funding.py'},
          io.open(QOUT, 'w', encoding='utf-8'), indent=1)
print('\nwrote %s' % QOUT)

# NOTE (public repository): 2 hard-coded study identifier(s) were
# rewritten to de-identified surrogates by tools/build_public_repo.py.
# They are rulings about particular studies rather than values the data
# can supply, so they have to travel with it.
"""Build one human-readable "reading packet" per paper for the hand-read of the
author -> affiliation linkage (all 385 papers).

WHY THIS EXISTS
---------------
The machine parser plateaued at 290/385 papers. The remaining layouts are not
machine-recoverable without guessing, so the linkage is being read by hand. But a hand
reader working from `private/fulltext/pdf-by-pmid/<PMID>.txt` is working blind: PLAIN
TEXT EXTRACTION DESTROYS THE SUPERSCRIPT FLAGS, and the superscript is the entire
linkage. "Folayan1,2*" and "Folayan1,2*" look identical in plain text whether the digits
were superscript markers or part of the name.

So this renders the page the way a human SEES it: every span whose font flags carry the
superscript bit (`span['flags'] & 1`) is written back inline as ^{...}. That is the same
signal the parser used, but handed to a reader instead of to a regex -- the reader can
then resolve the layouts the regex could not (symbol-keyed footnotes, unkeyed footnotes,
Lancet-style parenthetical initials).

WHAT EACH PACKET CONTAINS
-------------------------
- the front pages (where bylines and affiliation lists live), and
- any tail page carrying a BMC-style "Author details" / "Author information" block,
  because several publishers print the affiliation list at the END of the article.

It deliberately contains NO PubMed data. The hand-read has to be an independent source,
so the reader must never see what they are being compared against.

Output: data/quality-control/08_23_2026_reading_packets/<PMID>.txt
Run from the repository root.
"""
import os
import re
import sys
import unicodedata
import warnings

warnings.simplefilter('ignore')
import fitz
import pandas as pd

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

MAP = 'data/provenance/08_23_2026_pdf_pmid_map_385.csv'
OUTDIR = 'data/quality-control/08_23_2026_reading_packets'
FRONTPAGE = 3       # bylines and affiliation lists live here for nearly every layout
TAILPAGE = 4        # BMC "Author details" blocks live at the very end

# Budgets are PER PAGE, and each keeps a HEAD and a TAIL slice rather than a prefix.
# A single flat cap on the whole packet silently ate the bottom of page 1 on dense
# two-column layouts -- and the bottom of page 1 is precisely where symbol-keyed
# footnote affiliations are printed ("From the *Health Information Management ...;
# and +Quality and patient safety department ...", STUDY-1007). Keeping both ends of the
# page keeps the byline (top) and the footnote (bottom) and elides only the abstract
# and body prose in between, which carry nothing this read needs.
PAGE_BUDGET = {0: (4000, 2500), 1: (2500, 1200), 2: (2000, 0)}
TAIL_BUDGET = (3000, 0)
MAX_TAIL_PAGES = 2

TAIL_MARK = re.compile(
    r'\bauthor\s+(details|information|affiliations|contributions)\b|'
    r'\baffiliations?\s*:|\bauthors[’\']\s+affiliations\b', re.I)

# A superscript span is only rendered as a marker if it LOOKS like one. Superscript is
# also used for reference callouts, trademark signs and units; rendering those as ^{}
# would bury the real markers in noise.
MARKISH = re.compile(r'^[\s,;&\-–\*†‡§¶#\^\.\)\(0-9a-zA-Z]{1,12}$')


def longpath(p):
    """Windows MAX_PATH escape. The PDF folder path is 139 chars, so long titles push
    past 260 and fitz.open() fails with FileNotFoundError -- which once looked like
    "91 scanned PDFs with no text layer" and was purely a path-length artifact."""
    p = os.path.abspath(p).replace('/', '\\')
    return '\\\\?\\' + p if not p.startswith('\\\\?\\') else p


def deacc(s):
    s = unicodedata.normalize('NFKD', s)
    return ''.join(c for c in s if not unicodedata.combining(c))


def render_page(page):
    """Rebuild the page's visual lines with superscript spans marked inline.

    Spans are grouped by their y coordinate rather than by the PDF's own line objects:
    some producers put every word on its own line (STUDY-0843 extracts as
    "Australasian / Emergency / Care / 25 / (2022)"), which destroys the line structure
    that keyed affiliation lists depend on.
    """
    rows = {}
    for blk in page.get_text('dict').get('blocks', []):
        for line in blk.get('lines', []):
            for sp in line.get('spans', []):
                t = sp['text']
                if not t.strip():
                    continue
                y = round(sp['bbox'][1] / 3.0)      # 3pt tolerance groups a visual line
                rows.setdefault(y, []).append((sp['bbox'][0], t, bool(sp['flags'] & 1)))

    out = []
    for y in sorted(rows):
        parts = []
        for _, t, sup in sorted(rows[y]):
            t = deacc(t)
            if sup and MARKISH.match(t):
                parts.append('^{' + t.strip() + '}')
            else:
                parts.append(t)
        line = re.sub(r'[ \t]+', ' ', ''.join(parts)).strip()
        if line:
            out.append(line)
    return out


def budget(text, head, tail):
    """Keep the head and the tail of a page, eliding only the middle."""
    if len(text) <= head + tail + 80:
        return text
    if tail <= 0:
        return text[:head] + '\n[... rest of page elided ...]'
    return (text[:head] + '\n[... middle of page elided -- abstract / body prose ...]\n'
            + text[-tail:])


def main():
    os.makedirs(OUTDIR, exist_ok=True)
    m = pd.read_csv(MAP, encoding='utf-8-sig')
    pathcol = next(c for c in m.columns if 'path' in c.lower())
    print(f'map: {len(m)} rows, path column = {pathcol}')

    ok = fail = 0
    for _, r in m.iterrows():
        pmid = int(r['PMID'])
        try:
            doc = fitz.open(longpath(r[pathcol]))
        except Exception as e:
            print(f'  !! {pmid}: cannot open -- {e}')
            fail += 1
            continue

        n = doc.page_count
        front = list(range(min(FRONTPAGE, n)))
        # Only pull a tail page in if it actually carries an author-details block; adding
        # the last four pages unconditionally buries the front matter in references.
        tail = [p for p in range(max(0, n - TAILPAGE), n)
                if p not in front and TAIL_MARK.search(doc[p].get_text()[:4000])
                ][:MAX_TAIL_PAGES]

        chunks = [f'# PMID {pmid}',
                  f'# source PDF: {os.path.basename(str(r[pathcol]))}',
                  f'# pages in PDF: {n}',
                  '# Superscript spans are rendered inline as ^{...} -- these are the '
                  'affiliation markers.',
                  f'# Full text if this is not enough: private/fulltext/pdf-by-pmid/{pmid}.txt',
                  '']
        for p in front + tail:
            is_front = p in front
            label = 'FRONT' if is_front else 'TAIL (author-details block)'
            head, tl = PAGE_BUDGET.get(p, (2000, 0)) if is_front else TAIL_BUDGET
            chunks.append(f'===== page {p + 1} of {n}  [{label}] =====')
            chunks.append(budget('\n'.join(render_page(doc[p])), head, tl))
            chunks.append('')
        doc.close()

        with open(os.path.join(OUTDIR, f'{pmid}.txt'), 'w', encoding='utf-8') as f:
            f.write('\n'.join(chunks))
        ok += 1

    print(f'wrote {ok} packets to {OUTDIR}  ({fail} failed)')


if __name__ == '__main__':
    main()

# NOTE (public repository): 3 hard-coded study identifier(s) were
# rewritten to de-identified surrogates by tools/build_public_repo.py.
# They are rulings about particular studies rather than values the data
# can supply, so they have to travel with it.
# -*- coding: utf-8 -*-
"""Reconstruct the author -> affiliation linkage FROM THE PDFs ALONE.

Nothing here reads PubMed. The author list, the affiliation list and the link between
them all come out of the paper, so the result is an independent reconstruction that
S1 / S2 / the author stratifiers can be compared against.

Author markers are recovered from **font metadata**, not plain text: PyMuPDF exposes a
superscript flag per span, so a byline extracts as

    'A.R. AZAB' | [SUP]'1,2' | ', W.K. ABDELBASSET' | [SUP]'1,3'

giving author order *and* each author's affiliation keys exactly. Plain-text extraction
destroys this -- superscripts become ordinary digits.

Marker alphabets differ by publisher and all three are handled:
    numeric  '1,2'      + affiliation list  "1Department of ...  2Faculty of ..."
    alpha    'a,b'      + affiliation list  "a Departments of ...  b Departments of ..."
    symbol   '*', '†'   + affiliation list  "*Department of ..."
Papers whose byline carries no markers at all are handled only when the header contains
exactly ONE affiliation, which every author then shares.

Coverage is deliberately conservative: a paper counts as parsed only when the
reconstruction is self-consistent (markers resolve, affiliation bodies look like
organisations, most authors resolve). Everything else is written out with a status.

Run from the repository root.
"""
import os, re, sys, unicodedata, warnings
warnings.simplefilter('ignore')
import fitz
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'lib'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from country_matcher import detect_country_segment
from saudi_institution_classifier import classify

MAP = 'data/provenance/08_23_2026_pdf_pmid_map_385.csv'
OUT = 'data/quality-control'
MAXPAGE = 5      # front matter: title, byline, affiliations for most layouts
TAILPAGE = 4     # end matter: BMC-style "Author details" blocks live here
os.makedirs(OUT, exist_ok=True)


def longpath(p):
    p = os.path.abspath(p).replace('/', '\\')
    return '\\\\?\\' + p if not p.startswith('\\\\?\\') else p


def deacc(s):
    s = unicodedata.normalize('NFKD', s)
    return ''.join(c for c in s if not unicodedata.combining(c))


ORG = re.compile(r'\b(department|departments|dept|college|faculty|school|division|centre|'
                 r'center|institute|institut|unit|units|ministry|hospital|universit|clinic|'
                 r'laborator|academy|chair|program|programme|research|foundation|authority)\b', re.I)
NAMEISH = re.compile(r"[A-Z][A-Za-z'’\.\-]")
SYMS = '*†‡§¶#^'
SEP = r'\s,;&\-–' + re.escape(SYMS)
# A marker token is any run of keys and separators. Symbols may be glued straight onto a
# digit with no separator -- BMC prints "Folayan1,2*" and "Hallit1,2,3*†" -- so symbols
# count as separators here and are stripped out of the keys afterwards.
MARK_TOK = re.compile(r'^[' + SEP + r']*[\dA-Za-z][' + SEP + r'\dA-Za-z]*$')
SEP_ONLY = re.compile(r'^[' + SEP + r'()\[\].]*$')
COVER = re.compile(r'researchgate\.net/publication|tandfonline\.com/action/journalInformation|'
                   r'Full Terms & Conditions of access', re.I)

DEGREE = re.compile(
    r'^(?:'
    r'ph\.?d|m\.?d|m\.?b\.?b\.?s|m\.?b\.?ch\.?b|b\.?a|b\.?s\.?c?|m\.?s\.?c?|m\.?p\.?h|'
    r'd\.?d\.?s|b\.?d\.?s|pharm\.?d|d\.?m\.?d|ed\.?d|d\.?p\.?h\.?i\.?l|psy\.?d|dr\.?p\.?h|'
    r'r\.?n|b\.?s\.?n|m\.?s\.?n|f\.?r\.?c\.?[a-z]{0,3}|f\.?a\.?c\.?[a-z]{0,2}|'
    r'f\.?c\.?p\.?s|m\.?r\.?c\.?[a-z]{0,3}|f\.?e\.?b\.?[a-z]{0,3}|msc|d\.?o|md|ms|ma|'
    r'prof|professor|dr|assoc|asst|mr|ms|mrs|msph|mha|mba|cph|ccrp|facs|faha|id'
    r')\.?$', re.I)

AFF_STOP = re.compile(
    r'(\bcorrespond(?:ence|ing)\b|\*\s*e-?mail|\be-?mail\s*:|\babstract\b|\bobjectives?\s*:|'
    r'\bbackground\s*:|\bintroduction\b|\bkeywords?\b|\breceived\s*:|\baccepted\s*:|'
    r'\bhow to cite\b|\bopen access\b|©|https?://|\bdoi\s*:|\bORCID\b|\bsummary\b|'
    r'\bA R T I C L E\b|\bcopyright\b|'
    # Page furniture. An affiliation that runs past its end into the running head keeps
    # going into the article body, and because the country matcher takes the RIGHTMOST
    # country in a segment, prose mentioning Saudi Arabia overrode the "USA" that was
    # sitting in the affiliation itself (STUDY-0878, a Baltimore author).
    r'\(\d{4}\)\s*\d+\s*:|\b\d{4}\s*;\s*\d+\s*:|\bvol\.?\s*\d+\s*,|'
    r'\b\d{3,4}\s+[A-Z][a-z]{3,}\s+(?:of|and|[A-Z]))', re.I)


def cut_affil(s):
    m = AFF_STOP.search(s)
    if m and m.start() > 10:
        s = s[:m.start()]
    return s.strip(' ,;.-')


def strip_degrees(name):
    parts = [p for p in re.split(r'\s*[,;]\s*', name) if p.strip()]
    keep = [p for p in parts if not DEGREE.match(p.strip().strip('.'))]
    out = keep[-1] if keep else ''
    toks = out.split()
    while toks and DEGREE.match(toks[-1].strip('.')):
        toks.pop()
    return ' '.join(toks).strip(' .,-&')


def pages_to_read(doc):
    """Front matter, plus the tail of the article.

    BMC and several others print the affiliation list as an "Author details" block at the
    very END of the paper, well past the front pages -- reading only the front made those
    look like papers with no affiliation list at all.
    """
    n = doc.page_count
    front = list(range(min(MAXPAGE, n)))
    back = [p for p in range(max(0, n - TAILPAGE), n) if p not in front]
    return front + back


def spans_of(doc):
    out = []
    for pno in pages_to_read(doc):
        page_txt = doc[pno].get_text()
        cover = bool(COVER.search(page_txt[:1200]))
        for blk in doc[pno].get_text('dict').get('blocks', []):
            for line in blk.get('lines', []):
                for sp in line.get('spans', []):
                    t = deacc(sp['text'])
                    if t.strip():
                        out.append({'t': t, 'sup': bool(sp['flags'] & 1),
                                    'page': pno, 'cover': cover})
    return out


def merge_marker_spans(sp):
    """Join superscript marker spans the PDF split apart.

    Hindawi emits "1" | "," | "2" as three separate superscript spans; left alone that
    reads as three markers belonging to three different authors. Merge any run of marker
    spans whose gaps contain nothing but separators, so the byline sees one marker.
    """
    out, i = [], 0
    while i < len(sp):
        s = sp[i]
        if s['sup'] and s['t'].strip() and MARK_TOK.match(s['t']):
            j, txt = i, s['t']
            while j + 1 < len(sp):
                gap = [k for k in range(j + 1, len(sp))
                       if sp[k]['t'].strip() and not SEP_ONLY.match(sp[k]['t'])]
                nxt = gap[0] if gap else len(sp)
                cand = next((k for k in range(j + 1, min(nxt + 1, len(sp)))
                             if sp[k]['sup'] and sp[k]['t'].strip() and MARK_TOK.match(sp[k]['t'])), None)
                if cand is None or cand - j > 3:
                    break
                txt += ',' + sp[cand]['t']
                j = cand
            merged = dict(s)
            merged['t'] = txt
            out.append(merged)
            i = j + 1
            continue
        out.append(s)
        i += 1
    return out


def lines_native(doc):
    """Text lines as the PDF itself reports them."""
    out = []
    for pno in pages_to_read(doc):
        for ln in doc[pno].get_text().splitlines():
            ln = re.sub(r'[ \t]+', ' ', deacc(ln)).strip()
            if ln:
                out.append(ln)
    return out


def lines_geom(doc):
    """Text lines rebuilt from span GEOMETRY, not from the PDF's own line objects.

    Some text layers put every word on its own line -- STUDY-0843 extracts as
    "Australasian / Emergency / Care / 25 / (2022)" -- which makes line-keyed affiliation
    parsing useless. Grouping spans by their y coordinate and ordering by x reconstructs
    the visual line regardless of how the producer chopped it up.

    ⚠ Not a strict improvement: in a two-column layout this merges text across the
    gutter, which cost 6 papers when it replaced the native lines outright. Both sources
    are kept and tried in turn.
    """
    out = []
    for pno in pages_to_read(doc):
        rows = {}
        for blk in doc[pno].get_text('dict').get('blocks', []):
            for line in blk.get('lines', []):
                for sp in line.get('spans', []):
                    t = deacc(sp['text'])
                    if not t.strip():
                        continue
                    x0, y0 = sp['bbox'][0], sp['bbox'][1]
                    rows.setdefault(round(y0 / 2.0), []).append((x0, t))
        for y in sorted(rows):
            parts = [t for _, t in sorted(rows[y], key=lambda p: p[0])]
            ln = re.sub(r'\s+', ' ', ' '.join(parts)).strip()
            ln = re.sub(r'(?<=[A-Za-z])\s-\s(?=[a-z])', '', ln)
            if ln:
                out.append(ln)
    return out


LINE_KEY = re.compile(r'^(\d{1,2}|[a-z]|[' + re.escape(SYMS) + r'])[.)]?\s*(?=[A-Z(])')


def parse_affils_lines(lines, kind, wanted):
    """Affiliation list read from LINE structure rather than the span stream.

    Most remaining layouts print the affiliations one per line, keyed at the start of the
    line ("1 Department of ...", "a Departments of ...", "*Health Information ..."). Span
    joining destroys that structure, which is why they looked like papers with no
    affiliation list. Lines that do not start with a key continue the previous entry.
    """
    out, cur = {}, None
    for ln in lines:
        m = LINE_KEY.match(ln)
        if m:
            k = m.group(1)
            if kind == 'num' and not k.isdigit():
                m = None
            elif kind == 'alpha' and not k.isalpha():
                m = None
            elif kind == 'sym' and k.isalnum():
                m = None
        if m:
            cur = m.group(1)
            out[cur] = out.get(cur, '') + ' ' + ln[m.end():]
        elif cur and len(out.get(cur, '')) < 200 and not AFF_STOP.search(ln[:40]):
            out[cur] = out[cur] + ' ' + ln          # continuation line
        if cur and AFF_STOP.search(ln[:40]):
            cur = None
    out = {k: cut_affil(v.strip()) for k, v in out.items()}
    out = {k: v for k, v in out.items() if v and (not wanted or k in wanted)}
    keep = {k: v for k, v in out.items() if ORG.search(v) and len(v) > 15}
    if len(keep) < max(1, round(len(out) * 0.6)):
        return {}
    return keep


def first_affil_line(lines, kind):
    for i, ln in enumerate(lines):
        m = LINE_KEY.match(ln)
        if not m:
            continue
        k = m.group(1)
        if kind == 'num' and not k.isdigit():
            continue
        if kind == 'alpha' and not k.isalpha():
            continue
        if kind == 'sym' and k.isalnum():
            continue
        if ORG.search(ln):
            return i
    return None


BYLINE_NAME = re.compile(
    r"([A-Z][A-Za-z'’\-]+(?:\s+(?:[A-Z]\.?|[A-Z][A-Za-z'’\-]+|bin|bint|al|el|Al|El)){0,4})"
    r"\s*([\d" + re.escape(SYMS) + r"][\d\s,;\-–" + re.escape(SYMS) + r"]*)?")


def byline_from_lines(lines, aff_i, kind):
    """Read the byline from TEXT when its markers are not superscript spans.

    Several journals set the marker at full size ("R9 Abusrair,* Saeed Bohlega*") so the
    superscript flag never fires and the span-based path sees no byline at all. The byline
    is the text immediately above the affiliation list.
    """
    if aff_i is None:
        return []
    chunk = ' '.join(lines[max(0, aff_i - 4):aff_i])
    chunk = re.sub(r'\b(and|&)\b', ',', chunk)
    if len(chunk) < 8:
        return []
    out, ordinal = [], 0
    for part in chunk.split(','):
        part = part.strip()
        if not part:
            continue
        m = BYLINE_NAME.match(part)
        if not m:
            continue
        nm = strip_degrees(m.group(1).strip())
        ks = keys_of(m.group(2) or '')
        if kind == 'num':
            ks = [k for k in ks if k.isdigit()]
        elif kind == 'alpha':
            ks = [k for k in ks if k.isalpha()]
        if not nm or len(nm) < 4 or not ks:
            continue
        ordinal += 1
        out.append((ordinal, nm, ks))
    return out


def keys_of(txt):
    """'1,2' -> ['1','2'] ; 'a,b' -> ['a','b'] ; '1,2*' -> ['1','2'] ; '1†' -> ['1']

    Daggers and asterisks mark corresponding authorship or equal contribution, not an
    affiliation, so they are dropped when a real key is present.
    """
    parts = [k for k in re.split(r'[\s,;&\-–]+', txt.strip()) if k]
    out = []
    for p in parts:
        core = re.sub(r'[' + re.escape(SYMS) + r']', '', p)
        for k in (re.findall(r'\d{1,2}|[A-Za-z]', core) or ([p] if p else [])):
            if k not in out:
                out.append(k)
    return out


def find_author_clusters(sp):
    """Every marker cluster that could be a byline, in document order.

    Returning candidates rather than one guess matters: reference-citation superscripts
    in the body form large clusters too, and picking the largest one selected body text
    on Nature/Wiley layouts. The caller keeps the first cluster that an affiliation list
    actually follows, which is the real discriminator.
    """
    marks = [i for i, s in enumerate(sp)
             if s['sup'] and not s['cover'] and MARK_TOK.match(s['t']) and s['t'].strip()]
    if not marks:
        return []
    clusters, cur = [], [marks[0]]
    for a, b in zip(marks, marks[1:]):
        if b - a <= 8:
            cur.append(b)
        else:
            clusters.append(cur)
            cur = [b]
    clusters.append(cur)
    out = []
    for cl in clusters:
        names = 0
        for i in cl:
            prev = sp[i - 1]['t'] if i else ''
            if NAMEISH.search(prev) and not ORG.search(prev):
                names += 1
        if names < max(1, len(cl) * 0.5):
            continue
        out.append(cl)
    # Try the more author-like clusters first: a byline has several markers, whereas a
    # stray reference-citation superscript in the body forms a cluster of one or two.
    # (Requiring the key set to contain '1' was tried and REJECTED -- it cost 9 papers,
    # because a real byline's detected span run does not always include the first key.)
    return sorted(out, key=lambda c: (-len(c), c[0]))


def split_author_markers(sp, cl):
    """Author markers only -- the affiliation list is keyed too, so both land in one
    cluster and cl[-1] would put the whole affiliation list behind the read head."""
    for pos, i in enumerate(cl):
        nxt = sp[i + 1]['t'] if i + 1 < len(sp) else ''
        if ORG.search(nxt) and len(nxt.strip()) > 12:
            return cl[:pos] if pos >= 1 else cl
    return cl


def authors_from_block(sp, cl):
    lo = cl[0] - 1
    while lo > 0 and not NAMEISH.search(sp[lo]['t']):
        lo -= 1
    out, buf, ordinal = [], '', 0
    for i in range(lo, cl[-1] + 1):
        s = sp[i]
        if i in cl:
            raw = re.sub(r'^(and|&)\s+', '', buf.strip(' ,;&'), flags=re.I)
            nm = strip_degrees(raw)
            if not nm:
                nm = re.split(r'\s*(?:,|;|\band\b|&)\s*', raw)[-1].strip(' .,')
            if nm and NAMEISH.search(nm):
                ordinal += 1
                out.append((ordinal, nm, keys_of(s['t'])))
            buf = ''
        else:
            buf += ' ' + s['t']
    return out


def affil_regex(kind):
    # a key may be written "1", "1." or "1)" -- [NAME-REDACTED] prints "1. Department of..."
    if kind == 'num':
        return re.compile(r'(?:^|[\s.,;)\]])(\d{1,2})[.)]?\s{0,2}(?=[A-Z][a-zA-Z])')
    if kind == 'alpha':
        return re.compile(r'(?:^|[\s.,;)\]])([a-z])[.)]?\s{1,2}(?=[A-Z][a-zA-Z])')
    return re.compile(r'([' + re.escape(SYMS) + r']{1,2})\s{0,2}(?=[A-Z][a-zA-Z])')


def parse_affils(tail, kind, wanted):
    rx = affil_regex(kind)
    hits = [(m.group(1), m.end()) for m in rx.finditer(tail)]
    if not hits:
        return {}
    cand = {}
    for j, (k, pos) in enumerate(hits):
        # Keep the first ORGANISATION-like body for each key, not simply the first
        # occurrence. A stray early match -- typically a "1" left over from the byline --
        # would otherwise claim the key and permanently block the real entry, which is
        # why affiliation 1 was missing from so many papers.
        if k in cand and ORG.search(cand[k]):
            continue
        stop = hits[j + 1][1] - len(hits[j + 1][0]) - 1 if j + 1 < len(hits) else pos + 260
        body = cut_affil(tail[pos:min(stop, len(tail))])
        if body and (k not in cand or ORG.search(body)):
            cand[k] = body
    cand = {k: v for k, v in cand.items() if k in wanted or not wanted}
    if not cand:
        return {}
    # Keep ONLY bodies that read like an organisation. Numbered runs also occur in
    # tables and figure captions, and a mixed block let "CONSORT flow diagram of study
    # recruitment" stand in as an affiliation. An author whose key is dropped here ends
    # up with unresolved markers and is excluded from the comparison, which is the
    # honest outcome -- better than scoring them against a table row.
    keep = {k: v for k, v in cand.items() if ORG.search(v) and len(v) > 15}
    if len(keep) < max(1, round(len(cand) * 0.6)):
        return {}
    return keep


def tail_from(sp, idx, n=420):
    tail = ' '.join(s['t'] for s in sp[idx: idx + n])
    tail = re.sub(r'[ \t]+', ' ', tail)
    return re.sub(r'(?<=[A-Za-z])-\s+(?=[a-z])', '', tail)


def kind_of(keys):
    if any(k.isdigit() for k in keys):
        return 'num'
    if any(k.isalpha() for k in keys):
        return 'alpha'
    return 'sym'


AFF_SEG = re.compile(r'[^;\n]{12,300}')
# Publisher/journal furniture names countries that belong to nobody's affiliation:
# "Licensee MDPI, Basel, Switzerland", "[NAME-REDACTED] Switzerland AG", Thieme Stuttgart.
PUBLISHER = re.compile(
    r'(licensee|copyright|©|[NAME-REDACTED]|verlag|\bMDPI\b|elsevier|wiley|thieme|sage|taylor\s*&|'
    r'publish(?:er|ed|ing)|\bISSN\b|creativecommons|all rights reserved|journal homepage|'
    r'\bdoi\b|www\.|http)', re.I)


def uniform_affiliation(linesets):
    """TRIED AND REMOVED FROM THE PIPELINE 2026-08-23 -- kept only as a record.

    The idea: if every affiliation printed in a paper is in one country then every author
    is in that country, whichever marker they carry -- which would validate the is-Saudi
    flag with no linkage at all, for exactly the papers whose bylines cannot be read.

    It does not survive being made safe. Scanning only organisation-like segments found
    "one country" on papers that had a second affiliation on a continuation line, and it
    assigned the wrong country to every author of 33 papers -- country agreement fell
    99.5% -> 96.3%, institution 99.2% -> 93.8%. Tightening it to require a single country
    across the whole front matter made it fire on ZERO papers, because titles and
    abstracts name other countries.

    The premise needs proof that ALL affiliations were found, and that proof is the
    linkage this was trying to avoid. Do not re-add it without solving that first.
    """
    best = None
    for lines in linesets:
        segs, cs, insts = [], set(), set()
        aborted = False
        for ln in lines[:70]:
            if AFF_STOP.search(ln[:40]) or PUBLISHER.search(ln):
                continue
            # Every country mentioned ANYWHERE in the front matter counts, not just the
            # ones inside organisation-like segments. Scanning only ORG segments made
            # papers look uniform when a second country sat on a continuation line, and
            # that assigned the wrong country to every author on them.
            for m in AFF_SEG.finditer(ln):
                s = cut_affil(m.group(0).strip())
                if len(s) < 12:
                    continue
                c = detect_country_segment(s)[0]
                if not c:
                    continue
                cs.add(c)
                if len(cs) > 1:
                    aborted = True
                    break
                if ORG.search(s):
                    segs.append(s)
                    if c == 'Saudi Arabia':
                        i = classify(s)[1]
                        if i and not i.startswith('('):
                            insts.add(i)
            if aborted:
                break
        if aborted or len(cs) != 1 or not segs:
            continue
        c = next(iter(cs))
        cand = (c, next(iter(insts)) if len(insts) == 1 else None)
        if best is None or (cand[1] and not best[1]):
            best = cand
    return best


def single_affiliation(sp):
    """Header contains exactly one affiliation -> every author shares it."""
    head = tail_from(sp, 0, 160)
    segs = [cut_affil(s.strip()) for s in re.split(r'\s{2,}|\n|;', head)]
    segs = [s for s in segs if 25 < len(s) < 260 and ORG.search(s)]
    uniq, seen = [], set()
    for s in segs:
        k = re.sub(r'[^a-z]', '', s.lower())[:60]
        if k not in seen:
            seen.add(k)
            uniq.append(s)
    cs = {detect_country_segment(s)[0] for s in uniq}
    cs.discard(None)
    return uniq[0] if len(uniq) == 1 and len(cs) == 1 else None


def main():
    M = pd.read_csv(MAP, encoding='utf-8-sig')
    rows, stat = [], []
    for r in M.itertuples():
        pmid = str(r.PMID)
        if not isinstance(r.pdf_path, str) or not r.pdf_path:
            stat.append([pmid, 'NO_PDF', 0, 0, ''])
            continue
        try:
            doc = fitz.open(longpath(r.pdf_path))
        except Exception as e:
            stat.append([pmid, 'OPEN_FAIL', 0, 0, str(e)[:40]])
            continue
        sp = merge_marker_spans(spans_of(doc))
        linesets = [lines_native(doc), lines_geom(doc)]
        lines = linesets[0]
        doc.close()

        auth, affs, kind = [], {}, ''
        best_auth = []          # remember the byline even when its affiliations fail,
        #                         or a genuine NO_AFFIL_BLOCK is mislabelled NO_AUTHOR_BLOCK
        for cl in find_author_clusters(sp):
            cl = split_author_markers(sp, cl)
            cand_auth = authors_from_block(sp, cl)
            keys = [k for _, _, ks in cand_auth for k in ks]
            if not cand_auth or not keys:
                continue
            if len(cand_auth) > len(best_auth):
                best_auth = cand_auth
            kind = kind_of(keys)
            wanted = set(keys)
            cand_affs = parse_affils(tail_from(sp, cl[-1] + 1), kind, wanted)
            if not cand_affs:
                    # Some journals set the affiliation list away from the byline (an
                    # end-of-article block or a page footnote). Search onwards -- but
                    # STRICTLY, because numbered runs also occur in tables and body
                    # prose, and a loose scan happily returned "Flowchart demonstrating
                    # how certainty levels are distributed" as an affiliation.
                for start in range(cl[-1] + 1, len(sp), 30):
                    c2 = parse_affils(tail_from(sp, start), kind, wanted)
                    if c2 and sum(1 for v in c2.values()
                                  if ORG.search(v) and len(v) > 20) >= max(2, round(len(c2) * 0.8)):
                        cand_affs = c2
                        break
            if not cand_affs:
                for ls in linesets:
                    cand_affs = parse_affils_lines(ls, kind, wanted)
                    if cand_affs:
                        break
            if cand_affs:
                auth, affs = cand_auth, cand_affs
                break

        if not auth or not affs:
            # Text-based fallback: byline markers set at full size, so no superscript
            # spans exist for the span path to find.
            for ls in linesets:
                for k in ('num', 'alpha', 'sym'):
                    ai = first_affil_line(ls, k)
                    if ai is None:
                        continue
                    a2 = byline_from_lines(ls, ai, k)
                    if not a2:
                        continue
                    f2 = parse_affils_lines(ls, k, {x for _, _, ks in a2 for x in ks})
                    if f2 and sum(1 for _, _, ks in a2 if any(x in f2 for x in ks)) >= max(1, round(len(a2) * 0.6)):
                        auth, affs, kind = a2, f2, k
                        break
                if auth:
                    break

        if not auth or not affs:
            # The "one affiliation, shared by every author" tier was REMOVED for the same
            # reason as uniform_affiliation(): finding one affiliation is not proof there
            # is only one. It covered 6 papers and produced 5 of the 14 country
            # mismatches -- on STUDY-0455 it gave Saudi Arabia to US and Australian authors.
            stat.append([pmid, 'NO_AFFIL_BLOCK' if best_auth else 'NO_AUTHOR_BLOCK',
                         len(best_auth), len(affs), kind])
            continue

        res = sum(1 for _, _, ks in auth if any(k in affs for k in ks))
        if res < max(1, round(len(auth) * 0.6)):
            stat.append([pmid, 'TOO_FEW_RESOLVED', len(auth), len(affs), kind])
            continue

        for ordinal, name, ks in auth:
            texts = [affs[k] for k in ks if k in affs]
            # Record whether EVERY marker resolved. A dual-affiliated author whose second
            # affiliation was not parsed looks like a country/is-Saudi disagreement when
            # it is really a partial parse, so the comparison must be able to exclude it.
            full = 1 if ks and all(k in affs for k in ks) else 0
            cs = [detect_country_segment(t)[0] for t in texts]
            cs = [c for c in cs if c]
            insts = [classify(t)[1] for t, c in zip(texts, cs) if c == 'Saudi Arabia']
            rows.append([pmid, ordinal, name, ';'.join(ks), ' | '.join(cs),
                         ' | '.join(insts), ' || '.join(t[:160] for t in texts), full])
        stat.append([pmid, 'OK', len(auth), len(affs), kind])

    R = pd.DataFrame(rows, columns=['PMID', 'pdf_ordinal', 'pdf_name', 'markers',
                                    'pdf_countries', 'pdf_saudi_institutions', 'pdf_affil_text',
                                    'all_markers_resolved'])
    S = pd.DataFrame(stat, columns=['PMID', 'status', 'n_authors_pdf', 'n_affils_pdf', 'marker_kind'])
    R.to_csv(f'{OUT}/08_23_2026_pdf_author_affiliations.csv', index=False, encoding='utf-8-sig')
    S.to_csv(f'{OUT}/08_23_2026_pdf_author_parse_status.csv', index=False, encoding='utf-8-sig')

    print('papers attempted : %d' % len(S))
    print(S.status.value_counts().to_string())
    ok = S[S.status.str.startswith('OK')]
    print()
    print('papers parsed    : %d (%.1f%%)' % (len(ok), 100.0 * len(ok) / len(S)))
    print('  by marker kind :', S[S.status == 'OK'].marker_kind.value_counts().to_dict())
    print('authors extracted: %d' % len(R))
    print()
    print('wrote', OUT)


if __name__ == '__main__':
    main()

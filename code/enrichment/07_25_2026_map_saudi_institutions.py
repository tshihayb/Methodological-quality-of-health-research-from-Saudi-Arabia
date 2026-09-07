# NOTE (public repository): 14 hard-coded study identifier(s) were
# rewritten to de-identified surrogates by tools/build_public_repo.py.
# They are rulings about particular studies rather than values the data
# can supply, so they have to travel with it.
# -*- coding: utf-8 -*-
"""Map & classify the SAUDI affiliations by institution type — overall and per paper.

Anchored to the validated author-country map (data/authors/07_25_2026_author_country_long.csv): a Saudi
author-appearance = any author with 'Saudi Arabia' among their affiliation countries (1,514
across 383 papers). Each author's Saudi institution is taken from their first Saudi affiliation
block and classified by saudi_institution_classifier.classify(). The 49 authors PubMed left
without affiliation text (47 gold-note + 2 truncated-fragment) are enriched from the study's
PDF-verified notes.

Outputs (project dir):
  data/authors/07_25_2026_saudi_affiliation_long.csv        one row per Saudi author-appearance
  data/authors/07_25_2026_saudi_institution_type_counts.csv type x {authors, distinct institutions, papers}
  data/authors/07_25_2026_saudi_institution_counts.csv      specific institution x {type, authors, papers}
  data/authors/07_25_2026_saudi_paper_level.csv             one row per paper: sectors present, lead institution
"""
import json, os, re, sys
import pandas as pd
# Run from the repository root; the shared modules live in code/lib. Without this the
# script only imported when code/lib happened to be on PYTHONPATH.
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'lib'))
from country_matcher import detect_country_segment, SAUDI_CITIES
from saudi_institution_classifier import classify, TYPE_ORDER, UNIV, HOSP, HOSPRES
sys.path.insert(0, os.path.join('code', 'enrichment'))
_pp = __import__('08_24_2026_parse_parenthetical_affiliations')
parse_blocks, keys_of = _pp.parse_blocks, _pp.keys_of
import re as _re, unicodedata as _ud

# canonical city display + merge of spelling variants
_CITY_CANON={'jiddah':'Jeddah','makkah':'Makkah','mecca':'Makkah','madinah':'Madinah','medina':'Madinah',
 'al khobar':'Khobar','khobar':'Khobar','buraydah':'Buraidah','buraidah':'Buraidah','jizan':'Jazan',
 'jazan':'Jazan',"ha'il":'Hail','hail':'Hail','al-ahsa':'Al-Ahsa','alahsa':'Al-Ahsa','al-hasa':'Al-Ahsa',
 'al ahsa':'Al-Ahsa','hofuf':'Al-Ahsa','skaka':'Sakaka','sakaka':'Sakaka','aljouf':'Sakaka','al-jouf':'Sakaka',
 'onaizah':'Unaizah','unaizah':'Unaizah','al-kharj':'Al-Kharj','kharj':'Al-Kharj','alharj':'Al-Kharj',
 'khamis mushait':'Khamis Mushait','al-baha':'Al-Baha','baha':'Al-Baha','al-qassim':'Qassim','qassim':'Qassim'}
def extract_city(block):
    # ⚠ STRIP EMAIL ADDRESSES FIRST. The scan below takes the RIGHTMOST city name in the
    # block, and an address is usually the rightmost thing in it -- so a city occurring
    # inside one wins. STUDY-0046 was recorded in ARAR because "arar" sits inside
    # "momarar@cu.edu.eg", on a block whose Saudi half (King Saud University) prints no city
    # at all. Same substring trap as "Arabi" inside drarabie@ksmc.med.sa. An address is not
    # an affiliation; found by the S2 sweep (screen F2, 2026-08-24), 1 of 1,520 rows.
    block=_re.sub(r'\S+@\S+', ' ', block or '')
    n=''.join(c for c in _ud.normalize('NFKD',block or '') if not _ud.combining(c)).lower()
    best=None;pos=-1
    for c in SAUDI_CITIES:
        i=n.rfind(c)
        if i>pos: pos=i;best=c
    if best is None: return 'Unspecified'
    return _CITY_CANON.get(best, best.title())

CACHE='data/authors/07_25_2026_authors_cache_385.json'   # canonical 385
LONG='data/authors/07_25_2026_author_country_long.csv'

# Enrichment for Saudi authors with NO PubMed affiliation text.
# Until 2026-08-23 this was a set of 7 PMIDs all typed '(University - PDF-verified)',
# which printed 47 authors with no institution name in Suppl. Fig. S2 -- and the blanket
# "all universities" assumption was wrong for four of them (two Hail hospitals and a
# Ministry of Health post). The affiliations are now read from the papers themselves and
# run through the same classifier as everything else.
PDF_AFFIL_CSV='data/authors/08_23_2026_pdf_affiliations_gold.csv'
PDF_AFFIL={}
for _r in pd.read_csv(PDF_AFFIL_CSV, encoding='utf-8-sig').itertuples():
    PDF_AFFIL[(str(_r.PMID), int(_r.author_index))]=str(_r.affiliation_verbatim)
MANUAL={('STUDY-0531','Abusrair'):('King Faisal Specialist Hospital & Research Centre',HOSPRES),
        ('STUDY-0531','Bohlega'):('King Faisal Specialist Hospital & Research Centre',HOSPRES)}

# Last-resort affiliation text from the 385-paper hand-read, for Saudi authors PubMed
# leaves with no Saudi block at all. Added 2026-08-24: the S1 corrections made Al-Tawfiq
# (STUDY-0715) and Jafer (STUDY-0094) Saudi via MANUAL_AUTHOR_COUNTRY, which carries a country
# but no institution, so both arrived here as '(unspecified)'. Reading the paper's own text
# and running it through the SAME classifier is better than hardcoding an institution.
HANDREAD_CSV='data/authors/08_23_2026_handread_author_affiliations.csv'
HANDREAD_AFFIL={}
if os.path.exists(HANDREAD_CSV):
    for _r in pd.read_csv(HANDREAD_CSV, encoding='utf-8-sig').itertuples():
        v=str(getattr(_r,'verbatim','') or '')
        if not v.strip() or v=='nan': continue
        c,_=detect_country_segment(v)
        if c!='Saudi Arabia': continue
        HANDREAD_AFFIL.setdefault((str(_r.PMID), int(_r.author_index)), v)

# A THIRD evidence tier: the paper names the institution, but somewhere other than the
# affiliation footnote. Added 2026-08-24 for STUDY-0161. Its footnote reads only
# "From Administration of mental health (Almwled), Makkah" -- a department with no parent --
# so Almwled classified as '(unspecified)', reintroducing a placeholder into Fig. S2. The
# CORRESPONDENCE BLOCK on the same page supplies it: "Address correspondence and reprint
# request to: Dr. Amani S. ALmwled, Administration of Mental Health, King Abdullah Medical
# City. Makkah, Kingdom of Saudi Arabia." (verified against the PDF by TSA, 2026-08-24).
# The text is fed through the SAME classifier as everything else -- nothing is hardcoded.
# ⚠ King Abdullah Medical City (Makkah, MoH) is a DIFFERENT institution from King Abdulaziz
# Medical City (Riyadh, National Guard); the classifier already distinguishes them.
CORRESPONDENCE_AFFIL={
    ('STUDY-0161',1):'Administration of Mental Health, King Abdullah Medical City, Makkah, Kingdom of Saudi Arabia',
}

# CITY-only gap-fills from the correspondence block, for rows where the affiliation prints
# no city at all. Found by `08_24_2026_mine_correspondence_blocks.py` (2026-08-24) and each
# verified twice: the block NAMES the author at its start (so it is not another author's
# address), and the city is consistent with the institution S2 already records.
# ⚠ City only, deliberately. Some of these blocks also name a different institution -- a
# correspondence address is a MAILING address and may differ legitimately -- so letting them
# set the institution would be an unadjudicated change. They only fill an empty city.
CORRESPONDENCE_CITY={
    ('STUDY-1007',1):'Dammam',   # R-withdrawn Alanzi ... Imam Abdulrahman Bin Faisal University, Dammam
    ('STUDY-0149',1):'Makkah',   # Dr. Wesam A. Nasif ... Umm Al-Qura University, Makkah
    ('STUDY-1021',1):'Riyadh',   # Dr. EI AlShayea, P.O. Box 15158, Riyadh (King Saud University)
    ('STUDY-0312',13):'Riyadh',  # Dr. Giamal E. Gmati ... Riyadh
    ('STUDY-0677',5):'Riyadh',   # Shaista Arzoo ... King Saud University, Riyadh
    ('STUDY-0241',1):'Hofuf',    # Fatimah Alhamad ... Maternity and Children Hospital, Hofuf-Al-Hasa
}

import saudi_institution_classifier as _SIC

def names_institution(text, canon):
    """Is `canon` actually named inside `text`? Uses the classifier's own aliases, so this
    asks the same question `classify()` would, not a looser string match."""
    if not text or not canon: return False
    c=_SIC._compact(text)
    return any(k in c for typ,name,keys in list(_SIC.TIER1)+list(_SIC.TIER2)
               if name==canon for k in keys)

def named_institutions(text):
    """[(start, type, canon)] for EVERY curated Tier-1/2 institution named in `text`.

    `names_institution()` above asks "is this one institution named?"; this asks "which ones
    are named?", which is what the paper-level UNION needs. Aliases contained inside a longer
    match are dropped -- 'ministryof' sits inside 'ministryofhealth' and 'shaqra' inside
    'shaqrauniversity', and without the filter one institution counts as two.
    """
    c=_SIC._compact(text or ''); raw=[]
    for tier in (_SIC.TIER1,_SIC.TIER2):
        for typ,canon,keys in tier:
            for k in keys:
                i=c.find(k)
                while i>=0:
                    raw.append((i,i+len(k),typ,canon)); i=c.find(k,i+1)
    out=set()
    for h in raw:
        if any(g is not h and g[0]<=h[0] and g[1]>=h[1] and (g[1]-g[0])>(h[1]-h[0]) for g in raw):
            continue
        if h[3]=='General government / ministry':   # a catch-all, never an institution NAME
            continue
        out.add((h[0],h[2],h[3]))
    return sorted(out)

def all_saudi_text(aff):
    """Every Saudi block of an affiliation, not just the first one S2 keeps."""
    return ' | '.join(b.strip() for b in re.split(r'\s*[|;]\s*', aff or '')
                      if detect_country_segment(b)[0]=='Saudi Arabia')

def first_saudi_block(aff):
    for b in re.split(r'\s*[|;]\s*', aff or ''):
        c,_=detect_country_segment(b)
        if c=='Saudi Arabia': return b.strip()
    return None

def main():
    d=json.load(open(CACHE,'r',encoding='utf-8'))
    L=pd.read_csv(LONG)
    L['is_saudi']=L['all_countries'].fillna('').str.contains('Saudi Arabia')
    reals={str(pmid):[a for a in auth if a.get('last','').strip()] for pmid,auth in d.items()}

    # ---- parenthetical surname keys ([NAME-REDACTED] / [NAME-REDACTED] house style) ----
    # These journals print ONE affiliation sentence for the whole byline and key each
    # author by surname in parentheses. PubMed hands the identical string to every author,
    # so classifying it whole put 12 authors across 5 papers on the wrong institution
    # (docs/provenance/08_23_2026_handread_linkage.md). The parser returns each author's
    # own SLICE of that sentence; classify() then decides the institution exactly as
    # before, so nothing changes for papers where a group genuinely names several.
    # Validated against the 385-paper hand-read: 73/73 authors agree, 0 conflicts.
    paren={}
    for pmid,auth in reals.items():
        affs={(a.get('aff') or '') for a in auth if (a.get('aff') or '').strip()}
        if len(affs)!=1: continue
        got=parse_blocks(next(iter(affs)), [a.get('last','') for a in auth])
        if got: paren[str(pmid)]=got

    rows=[]; UNION_TYPES={}
    for _,r in L[L.is_saudi].iterrows():
        pmid=str(r['PMID']); idx=int(r['author_index']); last=str(r['last'])
        a=reals[pmid][idx-1]
        pblock=next((paren[pmid][k] for k in keys_of(last) if k in paren.get(pmid,{})), None)
        block=first_saudi_block(a.get('aff',''))
        cblock=CORRESPONDENCE_AFFIL.get((pmid,idx))
        if cblock:
            # Highest precedence: the paper names the institution explicitly, just not in
            # the affiliation footnote. Beats the parenthetical slice, which is incomplete.
            typ,inst,tier=classify(cblock); src='paper-correspondence'; block=cblock
        elif pblock:
            typ,inst,tier=classify(pblock); src='paper-parenthetical'
            # MINIMAL CHANGE: the parser strips attributions an author is not entitled to,
            # it does not re-pick among ones they are. Where a clause names several
            # institutions the author holds all of them (the National Guard trio KAMC +
            # KAIMRC + KSAU-HS). Re-classifying the narrowed slice would flip 5 authors of
            # STUDY-0320 from Hospital to University for no reason, and STUDY-0736's Braiji
            # between two real affiliations on a coin flip. So if the institution the
            # whole-string classifier already chose is still named inside this author's own
            # slice, keep it.
            if block:
                o_typ,o_inst,o_tier=classify(block)
                if o_inst!=inst and names_institution(pblock,o_inst):
                    typ,inst,tier=o_typ,o_inst,o_tier
            block=pblock
        elif block:
            typ,inst,tier=classify(block); src='pubmed-affil'
        elif classify(a.get('aff','') or '')[2] in (1,2) and not str(classify(a.get('aff','') or '')[1]).startswith('('):
            # COMPOUND BLOCK: one affiliation naming a Saudi institution AND a foreign one,
            # with no '|' or ';' between them, so first_saudi_block() never sees a Saudi
            # block and the author arrives here with nothing. STUDY-0519 Abdelwahid:
            # "[NAME-REDACTED] (JAFH), Suez Canal University, Ismailia, Egypt."
            # -- the rightmost-country rule calls the whole thing Egypt, yet the paper says
            # three times (authors 2-4) that JAFH is in Jazan, Saudi Arabia.
            # Only a TIER-1/2 NAMED institution is accepted; a tier-3 generic ("university,
            # unnamed") could be matched off foreign text and would invent an attribution.
            # Reached only for authors S1 already established as Saudi, so it cannot add one.
            block=a.get('aff','') or ''
            typ,inst,tier=classify(block); src='pubmed-affil-compound'
        elif (pmid,last) in MANUAL:
            inst,typ=MANUAL[(pmid,last)]; tier=0; src='manual-context'; block=''
        elif (pmid,idx) in PDF_AFFIL:
            block=PDF_AFFIL[(pmid,idx)]
            typ,inst,tier=classify(block); src='pdf-affiliation'
        elif (pmid,idx) in HANDREAD_AFFIL:
            block=HANDREAD_AFFIL[(pmid,idx)]
            typ,inst,tier=classify(block); src='paper-handread'
        else:
            typ,inst,tier=classify(''); src='unknown'; block=''
        # City: prefer one printed inside the author's OWN slice, else fall back to the full
        # affiliation string. In the parenthetical house style the city is printed ONCE at
        # the end of the whole sentence ("..., Riyadh, Kingdom of Saudi Arabia.") outside any
        # group, so slicing to a group loses it -- that silently cost 13 rows their city on
        # the first run. Where a group does print its own city (STUDY-0149 prints "Makkah"
        # inside Khogeer's clause) the slice wins, which is the correct precedence.
        city=extract_city(block) if block else 'Unspecified'
        if city=='Unspecified' and src=='paper-parenthetical':
            city=extract_city(first_saudi_block(a.get('aff','')) or a.get('aff','') or '')
        if city in ('Unspecified','',None) and (pmid,idx) in CORRESPONDENCE_CITY:
            city=CORRESPONDENCE_CITY[(pmid,idx)]
        # Every sector this author is on record for, for the paper-level UNION bound. Starts
        # from the RECORDED type -- for the correspondence/PDF/manual sources the institution
        # is not in the affiliation text at all, and a names-only union would drop it.
        UNION_TYPES[(pmid,idx)]={typ} | {t for _,t,_ in
                                         named_institutions(all_saudi_text(a.get('aff','')) or block)}
        rows.append(dict(PMID=int(pmid),author_index=idx,last=last,fore=str(r['fore']),
            is_first=bool(r['is_first']),is_last=bool(r['is_last']),
            inst_type=typ,institution=inst,city=city or 'Unspecified',
            tier=tier,source=src,saudi_block=block))
    A=pd.DataFrame(rows)
    A.to_csv('data/authors/07_25_2026_saudi_affiliation_long.csv',index=False,encoding='utf-8-sig')
    N=len(A); NP=A.PMID.nunique()

    # ---- overall: type counts ----
    tc=[]
    for t in TYPE_ORDER:
        sub=A[A.inst_type==t]
        if len(sub)==0: continue
        tc.append(dict(inst_type=t,author_appearances=len(sub),pct_authors=round(len(sub)/N*100,1),
            distinct_institutions=sub['institution'].nunique(),
            papers_involving=sub['PMID'].nunique(),pct_papers=round(sub['PMID'].nunique()/NP*100,1)))
    T=pd.DataFrame(tc)
    T.to_csv('data/authors/07_25_2026_saudi_institution_type_counts.csv',index=False,encoding='utf-8-sig')

    # ---- overall: specific institution counts ----
    ic=(A.groupby(['institution','inst_type'])
          .agg(author_appearances=('PMID','size'),papers=('PMID','nunique'))
          .reset_index().sort_values('author_appearances',ascending=False))
    ic.to_csv('data/authors/07_25_2026_saudi_institution_counts.csv',index=False,encoding='utf-8-sig')

    # ---- paper level ----
    # TWO sector variables, deliberately, because S2 answers a question the paper-level
    # variable does not ask. S2 must give each author ONE institution, so where an author
    # names several (176 of 1,520 rows, 11.6% -- 08_24_2026_institution_choice_sensitivity.py)
    # the first-Saudi-block + rightmost-alias rules pick one and the rest are dropped.
    # `sectors_present` unions those single picks, so collapsing happens BEFORE the union and
    # a sector can only be lost, never gained -- a one-directional under-count.
    # `sectors_present_union` unions every institution the author is on record for, which is
    # what "do this paper's Saudi authors span more than one sector?" actually asks.
    # TSA's ruling (2026-08-24): report the two as BOUNDS rather than choosing between them.
    # Health-system 115 (present) .. 129 (union); Multi-sector 80 .. 101.
    # NOTE the union starts from the author's RECORDED institution and adds the named ones.
    # Starting from the names alone is wrong and was caught by the A-subset-of-C invariant:
    # STUDY-0161 Almwled's institution comes from the paper's correspondence block, not from
    # her affiliation text, so a names-only union silently DROPPED her Hospital sector.
    pl=[]
    for pmid,g in A.groupby('PMID'):
        types=[]
        for t in g['inst_type']:
            if t not in types: types.append(t)
        utypes=[]
        for _,row in g.sort_values('author_index').iterrows():
            for t in sorted(UNION_TYPES[(str(row['PMID']),int(row['author_index']))]):
                if t not in utypes: utypes.append(t)
        lead=g.sort_values('author_index').iloc[0]
        insts=[]
        for i in g.sort_values('author_index')['institution']:
            if i not in insts: insts.append(i)
        pl.append(dict(PMID=pmid,n_saudi_authors=len(g),
            n_sectors=len(types),sectors_present='; '.join(types),
            lead_saudi_institution=lead['institution'],lead_saudi_type=lead['inst_type'],
            multisector=len(types)>1,saudi_institutions='; '.join(insts),
            n_sectors_union=len(utypes),sectors_present_union='; '.join(utypes),
            multisector_union=len(utypes)>1))
    P=pd.DataFrame(pl)
    P.to_csv('data/authors/07_25_2026_saudi_paper_level.csv',index=False,encoding='utf-8-sig')

    # ---- console report ----
    print(f'Saudi author-appearances: {N}  across {NP} papers')
    print(f'source mix: {A.source.value_counts().to_dict()}')
    tiermix=A[A.source=='pubmed-affil'].tier.value_counts().to_dict()
    print(f'tier mix (pubmed only): {tiermix}')
    print('\n===== INSTITUTION TYPE — overall =====')
    print(T.to_string(index=False))
    print('\n===== paper-level sector involvement (# papers with >=1 Saudi author of type) =====')
    for t in TYPE_ORDER:
        n=A[A.inst_type==t]['PMID'].nunique()
        if n: print(f'  {n:4d} papers ({n/NP*100:4.1f}%)  {t}')
    print(f'\n multisector papers (Saudi authors span >1 type): {P.multisector.sum()} ({P.multisector.mean()*100:.1f}%)')
    print(f' single-sector papers: {(~P.multisector).sum()}')
    print('\n===== TOP 20 specific Saudi institutions =====')
    top=ic[~ic.institution.str.startswith('(')].head(20)
    for _,r in top.iterrows():
        print(f'  {r.author_appearances:4d} auth · {r.papers:3d} papers  {r.institution}  [{r.inst_type}]')
    print('\n lead-institution type distribution (paper level):')
    print(P['lead_saudi_type'].value_counts().to_string())
    print('\n===== TOP Saudi cities (author-appearances) =====')
    cc=A[A.city!='Unspecified']['city'].value_counts()
    nres=len(A)-int((A.city=='Unspecified').sum())
    print(f' resolved city: {nres}/{len(A)}')
    for c,n in cc.head(15).items(): print(f'  {n:4d}  {c}')
    A[['city']].value_counts().to_frame('author_appearances').to_csv('data/authors/07_25_2026_saudi_city_counts.csv',encoding='utf-8-sig')

if __name__=='__main__':
    main()

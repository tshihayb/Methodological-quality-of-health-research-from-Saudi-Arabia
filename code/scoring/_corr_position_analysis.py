# -*- coding: utf-8 -*-
"""Is the corresponding-author stratifier just a blend of the first- and last-author ones?
   (a) how often is the corresponding author the FIRST / LAST / neither, and
   (b) does corresponding_author_saudi behave like a mixture of first_ and last_author_saudi."""
import json, re, unicodedata
import pandas as pd

d = pd.read_excel('data/authors/07_16_2026_saudi_affiliation_variables.xlsx')
d = d[d.in_analysis_329 == True].copy()
cache = json.load(open('data/authors/pubmed_authors_cache.json', encoding='utf-8'))

def norm(s):
    s = unicodedata.normalize('NFKD', str(s))
    s = ''.join(ch for ch in s if not unicodedata.combining(ch))
    return re.sub(r'[^a-z ]', ' ', s.lower()).strip()

def authors_of(pmid):
    # convention: collective/group entries are NOT authors -> require a real surname
    return [a for a in cache.get(str(pmid), []) if str(a.get('last', '')).strip()]

def match_positions(corr, email, auth):
    """indices of authors matching the recorded corresponding author"""
    lasts = [norm(a['last']) for a in auth]
    hits = set()
    c = str(corr).strip() if pd.notna(corr) else ''
    # 1) name-based
    if c and '@' not in c:
        toks = [t for t in norm(c).split() if len(t) > 1]
        full = norm(c)
        for i, L in enumerate(lasts):
            if not L: continue
            if L == full or L in toks:      # surname equals whole string, or is one of its tokens
                hits.add(i)
        if not hits and toks:               # fall back: surname is a token of a multi-word entry
            for i, L in enumerate(lasts):
                if L and any(L == t for t in toks): hits.add(i)
        # disambiguate same-surname authors using the given name, when one was recorded
        if len(hits) > 1 and len(toks) > 1:
            given = [t for t in toks if not any(t == lasts[i] for i in hits)]
            if given:
                refined = {i for i in hits
                           if any(g == norm(auth[i].get('fore', '')) or
                                  norm(auth[i].get('fore', '')).split()[:1] == [g] or
                                  g[:1] == norm(auth[i].get('init', ''))[:1] for g in given)}
                if len(refined) == 1: hits = refined
    # 2) email-based (local part vs surname / initial+surname / given+surname)
    src = c if '@' in c else (str(email) if pd.notna(email) else '')
    if not hits and '@' in src:
        for local in re.findall(r'([A-Za-z0-9._\-]+)@', src):
            lo = norm(local).replace(' ', '')
            for i, a in enumerate(auth):
                L = norm(a['last']).replace(' ', '')
                F = norm(a.get('fore', '')).replace(' ', '')
                if not L: continue
                if lo == L or lo == F + L or (F and lo == F[0] + L) or (len(L) > 3 and lo.endswith(L)):
                    hits.add(i)
    return sorted(hits)

rows = []
for _, r in d.iterrows():
    auth = authors_of(r.PMID)
    n = len(auth)
    hits = match_positions(r.corr_author, r.corr_email, auth)
    if n == 0:
        cls = 'no author list'
    elif n == 1:
        cls = 'sole author (first = last)'   # knowable without a name match
    elif not hits:
        cls = 'unresolved'
    elif len(hits) > 1:
        cls = 'ambiguous (surname shared)'
    else:
        i = hits[0]
        if n == 1:                cls = 'sole author (first = last)'
        elif i == 0:              cls = 'FIRST author'
        elif i == n - 1:          cls = 'LAST author'
        else:                     cls = 'middle author'
    rows.append(dict(PMID=r.PMID, n_authors=n, cls=cls,
                     corr_saudi=r.corresponding_author_saudi,
                     first_saudi=r.first_author_saudi, last_saudi=r.last_author_saudi))
res = pd.DataFrame(rows)

print('=' * 72)
print('(a) POSITION OF THE CORRESPONDING AUTHOR  (n = %d analysis papers)' % len(res))
print('=' * 72)
vc = res.cls.value_counts()
for k, v in vc.items(): print(f'   {k:28s} {v:4d}   {100*v/len(res):5.1f}%')
resolved = res[~res.cls.isin(['unresolved', 'ambiguous (surname shared)', 'no author list'])]
nres = len(resolved)
firstish = resolved.cls.isin(['FIRST author', 'sole author (first = last)']).sum()
lastish  = resolved.cls.isin(['LAST author', 'sole author (first = last)']).sum()
mid      = (resolved.cls == 'middle author').sum()
print(f'\n   Among the {nres} papers with an unambiguous match:')
print(f'      corresponding = FIRST            {firstish:4d}   {100*firstish/nres:5.1f}%')
print(f'      corresponding = LAST             {lastish:4d}   {100*lastish/nres:5.1f}%')
print(f'      corresponding = first OR last    {firstish+lastish-(resolved.cls=="sole author (first = last)").sum():4d}   '
      f'{100*(firstish+lastish-(resolved.cls=="sole author (first = last)").sum())/nres:5.1f}%')
print(f'      corresponding = NEITHER (middle) {mid:4d}   {100*mid/nres:5.1f}%')

print('\n' + '=' * 72)
print('(b) DOES corresponding_author_saudi BEHAVE LIKE A BLEND OF first/last?')
print('=' * 72)
f = pd.to_numeric(res.first_saudi); l = pd.to_numeric(res.last_saudi); c = pd.to_numeric(res.corr_saudi)
print(f'   Saudi counts (n=329):  first {int(f.sum())} ({100*f.mean():.1f}%) | '
      f'last {int(l.sum())} ({100*l.mean():.1f}%) | corresponding {int(c.sum())} ({100*c.mean():.1f}%)')
print(f'   Simple average of first & last = {(f.sum()+l.sum())/2:.1f}  vs actual corresponding {int(c.sum())}')
print(f'\n   Agreement of corresponding with:  first {100*(c==f).mean():5.1f}%   last {100*(c==l).mean():5.1f}%')
print(f'   first vs last agree with each other: {100*(f==l).mean():5.1f}%')
print('\n   Cross-tab first x last, with corresponding Saudi-rate inside each cell:')
for fv in [1, 0]:
    for lv in [1, 0]:
        m = (f == fv) & (l == lv)
        if m.sum(): print(f'      first={fv} last={lv}: n={int(m.sum()):4d}   corresponding Saudi = '
                          f'{int(c[m].sum()):4d} ({100*c[m].mean():5.1f}%)')
print('\n   Corresponding Saudi-rate BY the position it occupies:')
for k in ['FIRST author', 'LAST author', 'middle author', 'sole author (first = last)']:
    m = res.cls == k
    if m.sum(): print(f'      {k:28s} n={int(m.sum()):4d}   corresponding Saudi = {100*pd.to_numeric(res.corr_saudi[m]).mean():5.1f}%')
res.to_csv('data/authors/07_23_2026_corr_author_position.csv', index=False)
print('\n   wrote data/authors/07_23_2026_corr_author_position.csv')

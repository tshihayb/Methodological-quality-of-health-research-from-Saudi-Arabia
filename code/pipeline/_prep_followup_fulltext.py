# NOTE (public repository): 17 hard-coded study identifier(s) were
# rewritten to de-identified surrogates by tools/build_public_repo.py.
# They are rulings about particular studies rather than values the data
# can supply, so they have to travel with it.
import json, os, re, subprocess
import pandas as pd

PMIDS = {
    "case-control": ["STUDY-0149","STUDY-0589","STUDY-0119","STUDY-0590","STUDY-0991","STUDY-0017","STUDY-0911","STUDY-0460"],
    "cohort_followNo": ["STUDY-0845","STUDY-0326","STUDY-0306","STUDY-0878","STUDY-0676"],
    "xsec_followYes": ["STUDY-0093","STUDY-0331","STUDY-0202"],
    "prepost_followNo": ["STUDY-0471"],
}
allp = [p for v in PMIDS.values() for p in v]
json.dump(PMIDS, open('data/adjudication/followup_pmids.json','w'))

aff = pd.read_excel('data/authors/06_18_2026_saudi_affiliation_status_of_included_papers.xlsx', dtype=str)
aff['PMID'] = aff['PMID'].str.strip()
tit = aff.set_index('PMID')['Title'].to_dict()

BOTH = r'C:\Users\[USER]\OneDrive\Consulting company project with Yasser\Saudi Arabia Healthcare Research Landscape\Full text of included papers\Both'
pdfs = [f for f in os.listdir(BOTH) if f.lower().endswith('.pdf')]
def norm(s):
    s = str(s).lower(); s = re.sub(r'[^a-z0-9]+',' ',s); return re.sub(r'\s+',' ',s).strip()
npdf = {norm(os.path.splitext(f)[0]): f for f in pdfs}
mirdir = 'private/fulltext/pdf-by-pmid'
mir = set(f[:-4] for f in os.listdir(mirdir) if f.endswith('.pdf'))

os.makedirs('private/fulltext/pdf-by-pmid', exist_ok=True)
os.makedirs('private/fulltext/extracted-text', exist_ok=True)
EXT = '\\\\?\\'

report = []
for p in allp:
    t = tit.get(p,''); nt = norm(t); src = None
    if p in mir:
        src = os.path.abspath(os.path.join(mirdir, p+'.pdf'))
    elif nt in npdf:
        src = os.path.join(BOTH, npdf[nt])
    else:
        cands = sorted({f for k,f in npdf.items() if k and (k.startswith(nt[:45]) or nt.startswith(k[:45]))})
        if len(cands) == 1:
            src = os.path.join(BOTH, cands[0])
        else:
            report.append((p,'UNRESOLVED',str(len(cands)),(t or '')[:50])); continue
    dst = os.path.join('private/fulltext/pdf-by-pmid', p+'.pdf')
    rp = src if src.startswith(EXT) else (EXT+src)
    try:
        with open(rp,'rb') as fi, open(dst,'wb') as fo: fo.write(fi.read())
    except Exception as e:
        report.append((p,'COPYFAIL',str(e)[:50],(t or '')[:50])); continue
    txt = os.path.join('private/fulltext/extracted-text', p+'.txt')
    subprocess.run(['pdftotext','-layout',dst,txt], capture_output=True, text=True)
    n = os.path.getsize(txt) if os.path.exists(txt) else 0
    report.append((p,'ok','%d'%n,os.path.basename(src)[:50]))

print('%-9s %-10s %-8s %s' % ('PMID','status','chars','src'))
bad=[]
for r in report:
    print('%-9s %-10s %-8s %s' % r)
    if r[1]!='ok' or (r[1]=='ok' and int(r[2])<3000): bad.append(r[0])
print()
print('problem papers:', bad if bad else 'none')

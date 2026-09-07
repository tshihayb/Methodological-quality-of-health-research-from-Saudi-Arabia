# NOTE (public repository): 1 hard-coded study identifier(s) were
# rewritten to de-identified surrogates by tools/build_public_repo.py.
# They are rulings about particular studies rather than values the data
# can supply, so they have to travel with it.
import json, os, subprocess

rct = json.load(open('data/adjudication/rct_pmids.json'))
m = json.load(open('data/adjudication/rct_pdf_map.json'))
m['STUDY-0710'] = 'Comparative_efficacy_of_coronally_advanced_flap.18.pdf'

BOTH = r'C:\Users\[USER]\OneDrive\Consulting company project with Yasser\Saudi Arabia Healthcare Research Landscape\Full text of included papers\Both'
os.makedirs('private/fulltext/pdf-by-pmid', exist_ok=True)
os.makedirs('private/fulltext/extracted-text', exist_ok=True)

def srcpath(val):
    if val.startswith('private/fulltext/pdf-by-pmid/'):
        return os.path.abspath(val.replace('/', os.sep))
    return os.path.join(BOTH, val)

EXT = '\\\\?\\'  # \\?\ extended-length prefix

report = []
for p in rct:
    val = m[p]
    sp = srcpath(val)
    dst = os.path.join('private/fulltext/pdf-by-pmid', p + '.pdf')
    rp = sp if sp.startswith(EXT) else (EXT + sp)
    try:
        with open(rp, 'rb') as fi, open(dst, 'wb') as fo:
            fo.write(fi.read())
    except Exception as e:
        report.append((p, 'COPY_FAIL', str(e)[:60], val[:50]))
        continue
    txt = os.path.join('private/fulltext/extracted-text', p + '.txt')
    subprocess.run(['pdftotext', '-layout', dst, txt], capture_output=True, text=True)
    n = os.path.getsize(txt) if os.path.exists(txt) else 0
    report.append((p, 'ok', '%d chars' % n, val[:50]))

json.dump(m, open('data/adjudication/rct_pdf_map.json', 'w'))
print('%-9s %-9s %-12s %s' % ('PMID', 'status', 'txtsize', 'pdf'))
short = []
for r in report:
    print('%-9s %-9s %-12s %s' % r)
    if 'chars' in r[2] and int(r[2].split()[0]) < 3000:
        short.append(r[0])
print()
print('SHORT/suspect text (<3000 chars):', short if short else 'none')

# -*- coding: utf-8 -*-
# Extract full text of the 75 predictive PDFs (385-set) for SEIG outcome determination.
# PDF resolution order: by-PMID mirror -> new-papers folder -> external "Both" folder by normalized-title match (\\?\ long-path).
import csv, glob, json, os, re, warnings
warnings.simplefilter("ignore")
import fitz  # PyMuPDF

HERE=os.path.abspath(".")
OUT=os.path.join(HERE,"private/fulltext/pdf-by-pmid"); os.makedirs(OUT,exist_ok=True)
EXT=r"C:\Users\[USER]\OneDrive\Consulting company project with Yasser\Saudi Arabia Healthcare Research Landscape\Full text of included papers\Both"

# ---- 385 + task ----
land=list(csv.DictReader(open("data/journals/07_25_2026_journal_landscape_by_paper_385_JCR.csv",encoding="utf-8-sig")))
pred=[str(r["PMID"]).strip() for r in land if r["Study_Type"]=="Predictive"]

# ---- titles (try several json shapes) ----
def load_titles():
    tm={}
    for j in ["data/authors/07_25_2026_authors_cache_385.json","data/authors/pubmed_authors_cache.json","data/journals/07_24_2026_openalex_works_raw.json"]:
        if not os.path.exists(j): continue
        try: d=json.load(open(j,encoding="utf-8"))
        except: continue
        items = d.items() if isinstance(d,dict) else enumerate(d)
        for k,v in items:
            if not isinstance(v,dict): continue
            pmid=str(v.get("pmid") or v.get("PMID") or k).strip()
            title=v.get("title") or v.get("Title") or v.get("ArticleTitle")
            if title and pmid and pmid not in tm:
                tm[pmid]=str(title)
    return tm
titles=load_titles()

def norm(s):
    return re.sub(r'[^a-z0-9]','', (s or '').lower())

# ---- external folder index ----
extfiles=[f for f in os.listdir(EXT) if f.lower().endswith(".pdf")]
extnorm={norm(os.path.splitext(f)[0]):f for f in extfiles}
extnorm_items=list(extnorm.items())

def find_ext(pmid):
    t=titles.get(pmid)
    if not t: return None
    nt=norm(t)
    if len(nt)<12: return None
    # exact
    if nt in extnorm: return extnorm[nt]
    # filename is a truncated prefix of the title, or title prefix of filename
    for fn_norm,fn in extnorm_items:
        if len(fn_norm)>=25 and (nt.startswith(fn_norm) or fn_norm.startswith(nt[:min(len(nt),60)])):
            return fn
    return None

def longpath(p):
    return "\\\\?\\"+os.path.abspath(p).replace("/","\\")

def resolve(pmid):
    m=os.path.join("private/fulltext/pdf-by-pmid",pmid+".pdf")
    if os.path.exists(m): return m,"mirror"
    n=os.path.join("private/fulltext/pdf-by-pmid",pmid+".pdf")
    if os.path.exists(n): return n,"new"
    fn=find_ext(pmid)
    if fn: return os.path.join(EXT,fn),"external"
    return None,"UNMATCHED"

def extract(path):
    doc=fitz.open(longpath(path) if os.path.isabs(path) and len(os.path.abspath(path))>250 else path)
    txt=[]
    for pg in doc:
        txt.append(pg.get_text())
    doc.close()
    return "\n".join(txt)

rows=[]
for p in pred:
    path,how=resolve(p)
    ok=False; nchar=0; err=""
    if path:
        try:
            t=extract(path); nchar=len(t)
            if nchar>500:
                open(os.path.join(OUT,p+".txt"),"w",encoding="utf-8").write(t); ok=True
            else: err="too_short(%d)"%nchar
        except Exception as e:
            err=str(e)[:80]
    rows.append((p,how,ok,nchar,os.path.basename(path) if path else "",err))

with open("data/provenance/08_08_2026_predictive_pdf_extract_log.csv","w",newline="",encoding="utf-8-sig") as f:
    w=csv.writer(f); w.writerow(["PMID","source","extracted_ok","n_chars","pdf_file","error"])
    for r in rows: w.writerow(r)

nok=sum(1 for r in rows if r[2])
print("predictive:",len(pred),"| extracted OK:",nok,"| FAILED:",len(pred)-nok)
print("by source:", {s:sum(1 for r in rows if r[1]==s) for s in set(r[1] for r in rows)})
print("\nFAILURES:")
for r in rows:
    if not r[2]: print("  ",r[0],r[1],r[5])

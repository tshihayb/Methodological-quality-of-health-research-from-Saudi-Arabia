# -*- coding: utf-8 -*-
"""Download the two remaining OFFICIAL enrichment sources:
  1. SCImago Journal Rank 2022 full table (SJR quartile, subject categories/areas,
     open-access flag, Scopus coverage).  Semicolon-CSV, decimal comma.
  2. OpenAlex works for each PMID (primary_topic domain/field/subfield, work-level
     open_access is_oa/oa_status, and the source's is_in_doaj + host organisation).
Raw dumps are saved so the join step is reproducible without re-hitting the network.
"""
import urllib.request, urllib.parse, json, time, io
import pandas as pd

PROJ = r"."
BR = {"User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                     "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"),
      "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
      "Referer": "https://www.scimagojr.com/journalrank.php"}
OA_HDR = {"User-Agent": "mailto:tshihayb@gmail.com"}

def get(url, headers, timeout=120):
    req = urllib.request.Request(url, headers=headers)
    for a in range(4):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read()
        except Exception as e:
            print("  retry", a, type(e).__name__, e); time.sleep(3)
    raise RuntimeError("failed: " + url)

# ---- 1. SCImago 2022 ----
print("downloading SCImago 2022 ...")
raw = get("https://www.scimagojr.com/journalrank.php?out=xls&year=2022", BR)
sj = pd.read_csv(io.BytesIO(raw), sep=";", dtype=str, encoding="utf-8")
sj.columns = [c.strip() for c in sj.columns]
sj.to_csv(PROJ + r"\07_24_2026_scimago_2022_raw.csv", index=False, encoding="utf-8")
print("  SCImago rows:", len(sj), "| cols:", list(sj.columns))

# ---- 2. OpenAlex works by PMID, batched ----
meta = pd.read_csv(PROJ + r"\07_24_2026_journal_pubmed_metadata.csv", dtype=str)
pmids = meta["PMID"].astype(str).tolist()
FIELDS = ("id,doi,ids,title,publication_year,open_access,primary_location,"
          "primary_topic,topics,type,language")
recs = {}
B = 50
for i in range(0, len(pmids), B):
    batch = pmids[i:i+B]
    filt = "pmid:" + "|".join(batch)
    url = ("https://api.openalex.org/works?filter=" + urllib.parse.quote(filt)
           + "&select=" + FIELDS + "&per-page=" + str(B) + "&mailto=tshihayb@gmail.com")
    data = json.loads(get(url, OA_HDR))
    for w in data.get("results", []):
        pm = ""
        ids = w.get("ids", {})
        if ids.get("pmid"):
            pm = ids["pmid"].rsplit("/", 1)[-1]
        if pm:
            recs[pm] = w
    print(f"  OpenAlex batch {i//B+1}: matched {len(data.get('results', []))}/{len(batch)}")
    time.sleep(0.4)

with open(PROJ + r"\07_24_2026_openalex_works_raw.json", "w", encoding="utf-8") as f:
    json.dump(recs, f, ensure_ascii=False)
print("OpenAlex works matched:", len(recs), "of", len(pmids))
miss = [p for p in pmids if p not in recs]
if miss: print("  not found in OpenAlex:", miss)

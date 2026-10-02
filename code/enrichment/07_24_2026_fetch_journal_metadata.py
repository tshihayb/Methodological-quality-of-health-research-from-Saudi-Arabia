# -*- coding: utf-8 -*-
"""Fetch the OFFICIAL PubMed/NLM journal metadata for every analysis paper.
Source: NCBI E-utilities EFetch (db=pubmed).  Nothing here is invented; every
field is parsed straight from the NLM record.  Downstream enrichment (SJR
quartile, open-access status, topic) is done in separate scripts against their
own official sources so provenance stays clean.

Output: data/journals/07_24_2026_journal_pubmed_metadata.csv (one row per PMID).
"""
import urllib.request, time, csv, io
import xml.etree.ElementTree as ET
import pandas as pd

PROJ = r"."
UA = "Mozilla/5.0 (healthcare research journal audit; tshihayb@gmail.com)"

wide = pd.read_csv(PROJ + r"\07_23_2026_ANALYSIS_DATASET_wide.csv", dtype=str)
pmids = wide["PMID"].astype(str).tolist()
stype = dict(zip(wide["PMID"].astype(str), wide["Study_Type"]))
print("analysis papers:", len(pmids))

def efetch(ids):
    url = ("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pubmed&id="
           + ",".join(ids) + "&retmode=xml")
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=90) as r:
                return r.read()
        except Exception as e:
            print("  retry", attempt, type(e).__name__, e); time.sleep(3)
    raise RuntimeError("efetch failed for batch")

def txt(node, path):
    e = node.find(path); return e.text.strip() if e is not None and e.text else ""

rows = []
B = 150
for i in range(0, len(pmids), B):
    batch = pmids[i:i+B]
    root = ET.fromstring(efetch(batch))
    got = set()
    for art in root.findall(".//PubmedArticle"):
        mc = art.find("MedlineCitation")
        pmid = txt(mc, "PMID")
        got.add(pmid)
        status = mc.get("Status", "")
        indexing = mc.get("IndexingMethod", "")
        jr = mc.find("Article/Journal")
        jtitle = txt(jr, "Title")
        iso = txt(jr, "ISOAbbreviation")
        issn_p = issn_e = ""
        for issn in jr.findall("ISSN"):
            if issn.get("IssnType") == "Print": issn_p = (issn.text or "").strip()
            elif issn.get("IssnType") == "Electronic": issn_e = (issn.text or "").strip()
        mji = mc.find("MedlineJournalInfo")
        issn_link = txt(mji, "ISSNLinking")
        nlm_id = txt(mji, "NlmUniqueID")
        medline_ta = txt(mji, "MedlineTA")
        country = txt(mji, "Country")
        subsets = ";".join(cs.text for cs in mc.findall("CitationSubset") if cs.text)
        ptypes = ";".join(pt.text for pt in mc.findall("Article/PublicationTypeList/PublicationType") if pt.text)
        year = (txt(jr, "JournalIssue/PubDate/Year")
                or txt(jr, "JournalIssue/PubDate/MedlineDate")[:4])
        doi = pmc = ""
        for aid in art.findall(".//ArticleIdList/ArticleId"):
            if aid.get("IdType") == "doi": doi = (aid.text or "").strip()
            elif aid.get("IdType") == "pmc": pmc = (aid.text or "").strip()
        rows.append(dict(PMID=pmid, Study_Type=stype.get(pmid, ""), journal=jtitle,
            iso_abbrev=iso, medline_ta=medline_ta, issn_print=issn_p, issn_electronic=issn_e,
            issn_linking=issn_link, nlm_id=nlm_id, country=country,
            medline_status=status, indexing_method=indexing, citation_subsets=subsets,
            pub_types=ptypes, pub_year=year, doi=doi, pmcid=pmc))
    missing = set(batch) - got
    if missing: print("  WARN missing from efetch:", missing)
    print(f"  batch {i//B+1}: {len(got)} parsed")
    time.sleep(0.5)

df = pd.DataFrame(rows)
assert df.PMID.nunique() == len(df), "duplicate PMIDs"
print("\nparsed rows:", len(df), " unique journals (NlmUniqueID):", df.nlm_id.nunique())
print("MEDLINE status counts:"); print(df.medline_status.value_counts().to_string())
print("has PMC id:", (df.pmcid != "").sum(), " has DOI:", (df.doi != "").sum())
out = PROJ + r"\07_24_2026_journal_pubmed_metadata.csv"
df.to_csv(out, index=False, encoding="utf-8")
print("[written]", out)

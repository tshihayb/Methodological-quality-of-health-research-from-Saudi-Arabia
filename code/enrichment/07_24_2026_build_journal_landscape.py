# -*- coding: utf-8 -*-
"""Join the three OFFICIAL sources into a journal landscape, per paper and per
journal.  NOTHING is invented: every enriched field is tagged with where it came
from, and a journal that cannot be matched to a source is marked as such rather
than guessed.

  identity + indexing (PubMed/NLM) : data/journals/07_24_2026_journal_pubmed_metadata.csv
  SJR quartile + categories (SCImago 2022) : data/journals/07_24_2026_scimago_2022_raw.csv
  topic + open-access + DOAJ (OpenAlex) : data/journals/07_24_2026_openalex_works_raw.json

Quartiles are SJR (SCImago / Scopus) for 2022.  The other common system, the
Clarivate JCR Journal Impact Factor quartile, is subscription-only and is NOT
reported here; we do not have an official source for it in this environment.
"""
import json, re
import pandas as pd

PROJ = r"."
digits = lambda s: re.sub(r"[^0-9Xx]", "", str(s)).upper()

meta = pd.read_csv(PROJ + r"\07_24_2026_journal_pubmed_metadata.csv", dtype=str).fillna("")
sj   = pd.read_csv(PROJ + r"\07_24_2026_scimago_2022_raw.csv", dtype=str).fillna("")
oa   = json.load(open(PROJ + r"\07_24_2026_openalex_works_raw.json", encoding="utf-8"))

# ---- SCImago ISSN index -> row ----
sj_issn = {}
for idx, row in sj.iterrows():
    for tok in str(row["Issn"]).split(","):
        t = digits(tok)
        if len(t) == 8:
            sj_issn.setdefault(t, []).append(idx)
def norm_title(s): return re.sub(r"[^a-z0-9]", "", str(s).lower())
sj_title = {}
for idx, row in sj.iterrows():
    sj_title.setdefault(norm_title(row["Title"]), idx)

def match_scimago(r):
    issns = [digits(x) for x in (r["issn_print"], r["issn_electronic"], r["issn_linking"])]
    issns = [x for x in issns if len(x) == 8]
    hits = []
    for x in issns:
        hits += sj_issn.get(x, [])
    if hits:
        # prefer a journal-type row; else highest SJR
        cand = sj.loc[sorted(set(hits))]
        j = cand[cand["Type"].str.lower() == "journal"]
        cand = j if len(j) else cand
        return cand.index[0], "issn"
    ti = norm_title(r["journal"])
    if ti in sj_title:
        return sj_title[ti], "title"
    ta = norm_title(r["medline_ta"])
    if ta in sj_title:
        return sj_title[ta], "title(abbrev)"
    return None, "not-in-scimago-2022"

# ---- OpenAlex per-PMID extraction ----
def oa_fields(pm):
    w = oa.get(str(pm))
    if not w: return {}
    pt = w.get("primary_topic") or {}
    src = (w.get("primary_location") or {}).get("source") or {}
    oaj = w.get("open_access") or {}
    return dict(
        oa_status=oaj.get("oa_status", ""), oa_is_oa=oaj.get("is_oa", ""),
        topic=(pt.get("display_name") or ""),
        subfield=((pt.get("subfield") or {}).get("display_name") or ""),
        field=((pt.get("field") or {}).get("display_name") or ""),
        domain=((pt.get("domain") or {}).get("display_name") or ""),
        oa_source_name=(src.get("display_name") or ""),
        is_in_doaj=src.get("is_in_doaj", ""),
        host_org=(src.get("host_organization_name") or ""),
        source_type=(src.get("type") or ""))

rows = []
for _, r in meta.iterrows():
    idx, how = match_scimago(r)
    s = sj.loc[idx] if idx is not None else None
    o = oa_fields(r["PMID"])
    def sv(col): return (s[col] if s is not None else "")
    rows.append(dict(
        PMID=r["PMID"], Study_Type=r["Study_Type"], journal=r["journal"],
        iso_abbrev=r["iso_abbrev"], issn_linking=r["issn_linking"],
        publisher_country=r["country"], pub_year=r["pub_year"], doi=r["doi"],
        # --- indexing (PubMed / NLM, official) ---
        medline_status=r["medline_status"], citation_subsets=r["citation_subsets"],
        in_pubmed="Yes", in_medline=("Yes" if r["medline_status"] == "MEDLINE" else "No/partial"),
        in_pmc=("Yes" if r["pmcid"] else "No"),
        # --- SJR (SCImago 2022, official) ---
        sjr_match=how, sjr_best_quartile=sv("SJR Best Quartile"), sjr=sv("SJR"),
        scimago_title=sv("Title"), scimago_type=sv("Type"),
        scimago_categories=sv("Categories"), scimago_areas=sv("Areas"),
        scimago_coverage=sv("Coverage"), scimago_open_access=sv("Open Access"),
        scimago_publisher=sv("Publisher"), scimago_country=sv("Country"),
        in_scopus_2022=("Yes" if idx is not None else "unknown (not in SCImago 2022)"),
        # --- topic + open access (OpenAlex, official-community) ---
        oa_status=o.get("oa_status", ""), oa_is_oa=o.get("oa_is_oa", ""),
        topic=o.get("topic", ""), subfield=o.get("subfield", ""),
        field=o.get("field", ""), domain=o.get("domain", ""),
        is_in_doaj=o.get("is_in_doaj", ""), oa_source_name=o.get("oa_source_name", ""),
        host_org=o.get("host_org", ""), source_type=o.get("source_type", "")))

paper = pd.DataFrame(rows)
paper.to_csv(PROJ + r"\07_24_2026_journal_landscape_by_paper.csv", index=False, encoding="utf-8")

# ---- collapse to unique journals (by NLM id via issn_linking + title) ----
meta_key = meta.set_index("PMID")
paper["jkey"] = [meta_key.loc[p, "nlm_id"] or paper.loc[i, "issn_linking"] or paper.loc[i, "journal"]
                 for i, p in enumerate(paper["PMID"])]
agg = []
for k, g in paper.groupby("jkey"):
    g0 = g.iloc[0]
    agg.append(dict(
        journal=g0["journal"], n_papers=len(g),
        n_descriptive=(g.Study_Type == "Descriptive").sum(),
        n_predictive=(g.Study_Type == "Predictive").sum(),
        n_causal=(g.Study_Type == "Causal").sum(),
        issn_linking=g0["issn_linking"], publisher_country=g0["publisher_country"],
        in_medline=g0["in_medline"],
        n_in_pmc=(g.in_pmc == "Yes").sum(),
        sjr_best_quartile=g0["sjr_best_quartile"], sjr=g0["sjr"], sjr_match=g0["sjr_match"],
        in_scopus_2022=g0["in_scopus_2022"], scimago_areas=g0["scimago_areas"],
        scimago_categories=g0["scimago_categories"], scimago_coverage=g0["scimago_coverage"],
        scimago_open_access=g0["scimago_open_access"],
        is_in_doaj=g0["is_in_doaj"], field=g0["field"], subfield=g0["subfield"],
        domain=g0["domain"], scimago_publisher=g0["scimago_publisher"]))
jour = pd.DataFrame(agg).sort_values("n_papers", ascending=False)
jour.to_csv(PROJ + r"\07_24_2026_journal_landscape_by_journal.csv", index=False, encoding="utf-8")

# ---- summaries ----
def show(title, s):
    print("\n==", title, "==")
    print(s.to_string())

print("papers:", len(paper), "| unique journals:", len(jour))
print("\nSJR quartile match method (papers):"); print(paper.sjr_match.value_counts().to_string())
q_paper = paper.sjr_best_quartile.replace("", "not ranked / not in SCImago 2022").value_counts()
q_jour  = jour.sjr_best_quartile.replace("", "not ranked / not in SCImago 2022").value_counts()
show("SJR best quartile - by PAPER", q_paper)
show("SJR best quartile - by JOURNAL", q_jour)
show("OpenAlex open-access status - by PAPER", paper.oa_status.replace("", "unknown").value_counts())
show("Journal is a DOAJ open-access journal - by PAPER", paper.is_in_doaj.astype(str).value_counts())
show("In PubMed Central (free full text) - by PAPER", paper.in_pmc.value_counts())
show("Indexed for MEDLINE - by PAPER", paper.in_medline.value_counts())
show("In Scopus 2022 (SCImago) - by JOURNAL", jour.in_scopus_2022.value_counts())
show("Topic FIELD (OpenAlex) - by PAPER (top 15)", paper.field.replace("", "unknown").value_counts().head(15))
show("SCImago broad AREA - by PAPER (top 15)",
     paper.scimago_areas.replace("", "not in SCImago 2022").value_counts().head(15))
print("\n[written] by_paper + by_journal CSVs")

# Merge JCR-2022 JIF quartile into the journal landscape (by_journal + by_paper), beside SJR.
# Robust join: landscape<->worklist by normalized PubMed journal name (both share it);
# worklist<->jcr by ANY ISSN (found_via_issn vs the worklist's print/electronic/linking/search).
# (issn_linking is EMPTY for 8 journals in both files, so name is the reliable bridge.)
import pandas as pd, re

jcr = pd.read_csv("data/journals/07_24_2026_jcr_2022_results.csv", dtype=str, keep_default_na=False, na_filter=False)
w   = pd.read_csv("data/journals/07_24_2026_jcr_worklist.csv",       dtype=str, keep_default_na=False, na_filter=False)
bj  = pd.read_csv("data/journals/07_25_2026_journal_landscape_by_journal_385.csv", dtype=str, keep_default_na=False, na_filter=False)
bp  = pd.read_csv("data/journals/07_25_2026_journal_landscape_by_paper_385.csv",   dtype=str, keep_default_na=False, na_filter=False)

def ni(s): return re.sub(r"[^0-9Xx]", "", str(s)).upper()
def nn(s): return re.sub(r"[^a-z0-9]", "", str(s).lower())

# jcr: ISSN -> quartile/note  (found_via_issn is the study ISSN we recorded)
issn2q = {ni(r.found_via_issn): (r.jcr_2022_quartile, r.jcr_abbr, r.jcr_note)
          for _, r in jcr.iterrows() if ni(r.found_via_issn)}

# worklist: normalized name -> quartile, by matching ANY of its ISSNs to a jcr result
wl_name2q = {}
for _, r in w.iterrows():
    q = None
    for col in ("search_issn", "issn_electronic", "issn_print", "issn_linking"):
        v = ni(r[col])
        if v in issn2q:
            q = issn2q[v]; break
    if q is not None:
        wl_name2q[nn(r["journal"])] = q

# landscape by_journal: attach via normalized name
def get_q(name):
    return wl_name2q.get(nn(name), (None, None, None))
bj["jcr_2022_quartile"] = bj.journal.map(lambda n: get_q(n)[0])
bj["jcr_abbr"]          = bj.journal.map(lambda n: get_q(n)[1])
bj["jcr_note"]          = bj.journal.map(lambda n: get_q(n)[2])

miss = bj[bj.jcr_2022_quartile.isna()]
print("by_journal matched:", bj.jcr_2022_quartile.notna().sum(), "/", len(bj))
if len(miss): print("  MISSES:", miss.journal.tolist())

for c in ("jcr_2022_quartile", "jcr_abbr", "jcr_note"):
    bj[c] = bj[c].fillna("")


# 3 journals new to the 385 set: JCR 2022 quartile filled from WEB-SECONDARY sources
# (2026-07-25), flagged for confirmation against the user's Clarivate JCR pass.
# JDST is an ESCI journal -> received a JIF but no quartile until JCR 2023, so 2022 = None.
_NEW_JCR={
 "[NAME-REDACTED]":("Q2","web-secondary 2026-07-25 (Oncology / Biochem & Mol Biol); confirm vs Clarivate"),
 "[NAME-REDACTED]":("Q3","web-secondary 2026-07-25 (Medical Informatics / Health Care Sci & Services); confirm vs Clarivate"),
 "[NAME-REDACTED]":("None","ESCI in 2022: JIF but no quartile until JCR 2023 (web-secondary 2026-07-25); confirm vs Clarivate"),
}
for _jn,(_q,_note) in _NEW_JCR.items():
    _mm = bj.journal.str.lower()==_jn
    bj.loc[_mm,"jcr_2022_quartile"]=_q
    bj.loc[_mm,"jcr_note"]=_note

# reorder: jcr cols right after sjr_match
cols = [c for c in bj.columns if c not in ("jcr_2022_quartile", "jcr_abbr", "jcr_note")]
i = cols.index("sjr_match") + 1
cols = cols[:i] + ["jcr_2022_quartile", "jcr_abbr", "jcr_note"] + cols[i:]
bj = bj[cols]
bj.to_csv("data/journals/07_25_2026_journal_landscape_by_journal_385_JCR.csv", index=False)

# by_paper: attach via its journal name too
bp["jcr_2022_quartile"] = bp.journal.map(lambda n: get_q(n)[0]).fillna("")
# propagate the 3 web-secondary new-journal quartiles to their papers
for _jn,(_q,_note) in _NEW_JCR.items():
    bp.loc[bp.journal.str.lower()==_jn,"jcr_2022_quartile"]=_q
print("by_paper matched:", (bp.jcr_2022_quartile != "").sum(), "/", len(bp))
bp.to_csv("data/journals/07_25_2026_journal_landscape_by_paper_385_JCR.csv", index=False)

# headlines
order = ["Q1", "Q2", "Q3", "Q4", "None"]
def dist(s):
    vc = s.value_counts().to_dict(); return {k: int(vc.get(k, 0)) for k in order}
print("\nJCR-2022 by JOURNAL:", dist(bj.jcr_2022_quartile))
print("JCR-2022 by PAPER:  ", dist(bp.jcr_2022_quartile))
print("\nSJR (rows) x JCR (cols), by JOURNAL (NR=SJR not-ranked; None=no 2022 JIF quartile):")
ct = pd.crosstab(bj.sjr_best_quartile.replace({"": "NR", "-": "NR"}),
                 bj.jcr_2022_quartile, dropna=False)
ct = ct.reindex(columns=[c for c in order if c in ct.columns])
print(ct.to_string())

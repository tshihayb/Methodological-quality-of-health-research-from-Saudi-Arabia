# NOTE (public repository): 3 hard-coded study identifier(s) were
# rewritten to de-identified surrogates by tools/build_public_repo.py.
# They are rulings about particular studies rather than values the data
# can supply, so they have to travel with it.
# -*- coding: utf-8 -*-
# Apply the completed inconsistency-resolution worklist (data/quality-control/08_08_2026_inconsistency_resolution_worklist.xlsx)
# to the 385 analysis dataset.
#   - Cat 1 (45 GAP fills): set final = TSA/YA decision (mostly "No").
#   - Cat 5 (confounder basis): write ONLY the 6 genuine adjudications ("Based on ..."); the 25
#     "It should be skipped" rows keep their raw value (randomization-containing -> already exempt via
#     is_rct in the scorer; keeps the LLM gold standard per RCT Ruling 1).
#   - Cat 2-4 (18 rows) keep the ORIGINAL reviewer/adjudicator coding (user decision 2026-08-12); #104 no-op.
# Writes 08_12 long/wide + overwrites canonical 07_23 long/wide (both backed up first), with a change log
# and a cell-by-cell wide diff proving only the intended cells changed.
import pandas as pd, os, shutil, warnings
warnings.simplefilter("ignore")

BK = "archive/dataset-snapshots/pre-worklist"; os.makedirs(BK, exist_ok=True)
for f in ["data/analysis/07_23_2026_ANALYSIS_DATASET_long.csv","data/analysis/07_23_2026_ANALYSIS_DATASET_wide.csv",
          "data/analysis/08_08_2026_ANALYSIS_DATASET_long_385.csv","data/analysis/08_08_2026_ANALYSIS_DATASET_wide_385.csv"]:
    if os.path.exists(f) and not os.path.exists(os.path.join(BK,f)): shutil.copy(f, os.path.join(BK,f))

def s(x): return "" if pd.isna(x) else str(x).strip()

# ---------- load 385 long ----------
long = pd.read_csv("data/analysis/08_08_2026_ANALYSIS_DATASET_long_385.csv", dtype=str, encoding="utf-8-sig")
long["PMID"] = long.PMID.astype(str)
st_map = long.drop_duplicates("PMID").set_index("PMID").Study_Type.to_dict()
def pref(pmid): return {"Causal":"causal_","Descriptive":"descriptive_","Predictive":"predictive_"}[st_map[str(pmid)]]

# ---------- worklist -> apply map ----------
wl = pd.read_excel("data/quality-control/08_08_2026_inconsistency_resolution_worklist.xlsx", sheet_name="resolution_worklist")
apply_map = {}
for _, r in wl.iterrows():
    cat=s(r["Category"]); pmid=s(r["PMID"]); item=s(r["Item"]); dec=s(r["TSA + YA decision"])
    if cat.startswith("1."):
        apply_map[(pmid, pref(pmid)+item)] = (dec, "worklist GAP fill")
    elif cat.startswith("5.") and dec.lower().startswith("based on"):
        apply_map[(pmid, pref(pmid)+"conf_var_det")] = (dec, "worklist S5 confounder-basis adjudication")
print("apply_map cells:", len(apply_map), "(expect 45 GAP + 6 conf =", 45+6, ")")

# ---------- upsert ----------
idx = {(r.PMID, r.variable): i for i, r in long.iterrows()}
log = []
for (pmid, var), (val, note) in apply_map.items():
    if (pmid, var) in idx:
        i = idx[(pmid, var)]; before = s(long.at[i,"final"])
        long.at[i,"final"]=val; long.at[i,"source"]="worklist-2026-08-12"; long.at[i,"resolution_note"]=note
        log.append((pmid, var, before, val, "update"))
    else:
        long.loc[len(long)] = {"PMID":pmid,"Study_Type":st_map[pmid],"variable":var,"final":val,
                               "source":"worklist-2026-08-12","resolution_note":note}
        log.append((pmid, var, "<absent>", val, "add"))
logdf = pd.DataFrame(log, columns=["PMID","variable","before","after","op"])
logdf.to_csv("data/quality-control/08_12_2026_worklist_apply_log.csv", index=False, encoding="utf-8-sig")
print(f"applied {len(log)} cells | {(logdf.op=='update').sum()} update, {(logdf.op=='add').sum()} add")
chg = logdf[logdf.before != logdf.after]
print(f"\nvalue actually changed in {len(chg)} cells; the {len(logdf)-len(chg)} others already held the value.")
# guard: GAP cells (non conf_var_det) should have been blank before
bad = logdf[(logdf.op=="update") & (logdf.before!="") & (~logdf.variable.str.contains("conf_var_det"))]
print("GAP cells NOT blank before (should be 0):", len(bad))
if len(bad): print(bad.to_string(index=False))

# ---------- write long ----------
long.to_csv("data/analysis/08_12_2026_ANALYSIS_DATASET_long_385.csv", index=False, encoding="utf-8-sig")
long.to_csv("data/analysis/07_23_2026_ANALYSIS_DATASET_long.csv", index=False, encoding="utf-8-sig")

# ---------- rebuild WIDE (affiliation merge verbatim from code/pipeline/08_08_2026_build_385_wide.py) ----------
AFF=['first_author_saudi','last_author_saudi','corresponding_author_saudi','pct_saudi_authors',
     'pct_saudi_ge50','pct_saudi_cat3','pct_saudi_cat4','n_authors','n_saudi_authors','pct_saudi_reliable']
wide = long.pivot_table(index="PMID", columns="variable", values="final", aggfunc="first").reset_index()
wide["Study_Type"] = wide.PMID.map(long.drop_duplicates("PMID").set_index("PMID").Study_Type)
aff = pd.read_excel("data/authors/07_16_2026_saudi_affiliation_variables.xlsx"); aff["PMID"]=aff.PMID.astype(str); aff=aff[["PMID"]+AFF]
new = pd.DataFrame([
 {"PMID":"STUDY-0658","first_author_saudi":0,"last_author_saudi":0,"corresponding_author_saudi":0,
  "pct_saudi_authors":round(100*1/23,1),"pct_saudi_ge50":"<50%","pct_saudi_cat3":"<33%","pct_saudi_cat4":"<25%",
  "n_authors":23,"n_saudi_authors":1,"pct_saudi_reliable":True},
 {"PMID":"STUDY-0401","first_author_saudi":0,"last_author_saudi":0,"corresponding_author_saudi":0,
  "pct_saudi_authors":round(100*1/94,1),"pct_saudi_ge50":"<50%","pct_saudi_cat3":"<33%","pct_saudi_cat4":"<25%",
  "n_authors":94,"n_saudi_authors":1,"pct_saudi_reliable":True},
 {"PMID":"STUDY-0161","first_author_saudi":1,"last_author_saudi":1,"corresponding_author_saudi":1,
  "pct_saudi_authors":100.0,"pct_saudi_ge50":">=50%","pct_saudi_cat3":">67%","pct_saudi_cat4":">75%",
  "n_authors":8,"n_saudi_authors":8,"pct_saudi_reliable":True},
])
aff = pd.concat([aff[~aff.PMID.isin(new.PMID)], new], ignore_index=True)
wide = wide.merge(aff, on="PMID", how="left")
front = ["PMID","Study_Type"]+AFF
wide = wide[front+[c for c in wide.columns if c not in front]]
wide.to_csv("data/analysis/08_12_2026_ANALYSIS_DATASET_wide_385.csv", index=False, encoding="utf-8")
wide.to_csv("data/analysis/07_23_2026_ANALYSIS_DATASET_wide.csv", index=False, encoding="utf-8")
print("wrote long 385 (%d rows) + wide 385 (%d x %d)" % (len(long), len(wide), len(wide.columns)))

# ---------- integrity: diff new wide vs pre-worklist backup ----------
pre = pd.read_csv(os.path.join(BK,"07_23_2026_ANALYSIS_DATASET_wide.csv"), dtype=str, keep_default_na=False).set_index("PMID")
now = pd.read_csv("data/analysis/07_23_2026_ANALYSIS_DATASET_wide.csv", dtype=str, keep_default_na=False).set_index("PMID")
assert set(pre.index)==set(now.index), "PMID set changed!"
common = [c for c in pre.columns if c in now.columns]
diffs=[]
for pmid in pre.index:
    for c in common:
        a=s(pre.at[pmid,c]); b=s(now.at[pmid,c])
        if a!=b: diffs.append((pmid,c,a,b))
dd=pd.DataFrame(diffs, columns=["PMID","column","before","after"])
print(f"\n=== WIDE DIFF vs pre-worklist backup: {len(dd)} cells changed ===")
print(dd.to_string(index=False, max_colwidth=42))
exp = {(p,v) for (p,v) in apply_map}
got = {(p,c) for p,c in zip(dd.PMID, dd.column)}
print("\nunexpected changed cells (not in apply_map):", sorted(got-exp))
print("apply_map cells with NO wide change (value already equal):", len(exp-got), sorted(exp-got)[:8])

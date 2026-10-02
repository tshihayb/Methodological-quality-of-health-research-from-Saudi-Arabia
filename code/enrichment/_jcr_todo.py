# Print journals not yet in the JCR results (worklist order). Run: python code/enrichment/_jcr_todo.py
import pandas as pd, re
df = pd.read_csv("data/journals/07_24_2026_jcr_2022_results.csv", dtype=str, keep_default_na=False, na_filter=False)
w = pd.read_csv("data/journals/07_24_2026_jcr_worklist.csv", dtype=str, keep_default_na=False, na_filter=False)
w["idx"] = range(1, len(w) + 1)

def norm(s):
    return re.sub(r"[^a-z0-9]", "", str(s).lower())

# A worklist journal is DONE if either (a) any of its ISSNs appears in found_via_issn,
# or (b) its normalized name matches a result row's journal name (found via print-ISSN or name).
done_issns = set(df.found_via_issn)
done_names = set(df.journal.map(norm))

def is_done(r):
    if any(x and x in done_issns for x in (r["search_issn"], r["issn_print"], r["issn_electronic"])):
        return True
    return norm(r["journal"]) in done_names

rem = w[~w.apply(is_done, axis=1)]
print("done", len(w) - len(rem), "of", len(w), "| remaining", len(rem))
for _, r in rem.head(45).iterrows():
    print(f"{r['idx']:>3}|{r['n_papers']:>2}|P:{r['issn_print'] or '-'}|E:{r['issn_electronic'] or '-'}|{r['journal'][:44]}")

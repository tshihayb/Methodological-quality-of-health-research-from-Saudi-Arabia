# Merge data/journals/_jcr_new.csv into the JCR results, dedupe, report. Run: python code/enrichment/_jcr_append.py
import pandas as pd
R = "data/journals/07_24_2026_jcr_2022_results.csv"; N = "data/journals/_jcr_new.csv"
df = pd.read_csv(R, dtype=str, keep_default_na=False, na_filter=False)
nw = pd.read_csv(N, dtype=str, keep_default_na=False, na_filter=False)
df = pd.concat([df, nw], ignore_index=True).drop_duplicates("found_via_issn", keep="last")
df.to_csv(R, index=False)
w = pd.read_csv("data/journals/07_24_2026_jcr_worklist.csv", dtype=str, keep_default_na=False, na_filter=False)
done = set(df.found_via_issn) | set(df.journal.str.lower())
rem = w[~w.search_issn.isin(df.found_via_issn)]
print("total saved", len(df), "/ 226  | remaining ~", len(rem))
print(dict(df.jcr_2022_quartile.value_counts()))

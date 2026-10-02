# -*- coding: utf-8 -*-
# Extract the text layer of all 385 analysis papers to private/fulltext/pdf-by-pmid/<PMID>.txt
# using the persisted map from 08_23_2026_build_pdf_pmid_map.py.
# Existing .txt files are kept unless --force.
# Run from the repository root.
import csv, os, sys, warnings
warnings.simplefilter("ignore")
import fitz

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

MAP = "data/provenance/08_23_2026_pdf_pmid_map_385.csv"
OUT = "private/fulltext/pdf-by-pmid"
LOG = "data/provenance/08_23_2026_fulltext_extract_log_385.csv"
FORCE = "--force" in sys.argv
os.makedirs(OUT, exist_ok=True)


def longpath(p):
    p = os.path.abspath(p).replace("/", "\\")
    return "\\\\?\\" + p if not p.startswith("\\\\?\\") else p


rows = []
rebuilt = kept = failed = 0
for r in csv.DictReader(open(MAP, encoding="utf-8-sig")):
    pmid, path = r["PMID"], r["pdf_path"]
    dst = os.path.join(OUT, pmid + ".txt")

    if os.path.exists(dst) and not FORCE:
        n = os.path.getsize(dst)
        rows.append([pmid, "kept", n, 0, ""])
        kept += 1
        continue
    if not path:
        rows.append([pmid, "no_pdf", 0, 0, "unmapped"])
        failed += 1
        continue
    try:
        doc = fitz.open(longpath(path))
        npg = doc.page_count
        txt = "\n".join(doc[i].get_text() for i in range(npg))
        doc.close()
        if len(txt) < 500:
            rows.append([pmid, "no_text_layer", len(txt), npg, "likely scanned"])
            failed += 1
            continue
        open(dst, "w", encoding="utf-8").write(txt)
        rows.append([pmid, "extracted", len(txt), npg, ""])
        rebuilt += 1
    except Exception as e:
        rows.append([pmid, "error", 0, 0, str(e)[:120]])
        failed += 1

with open(LOG, "w", newline="", encoding="utf-8-sig") as fh:
    w = csv.writer(fh)
    w.writerow(["PMID", "status", "n_chars", "n_pages", "note"])
    w.writerows(rows)

print("extracted %d | kept %d | failed %d | total %d" % (rebuilt, kept, failed, len(rows)))
have = sum(1 for r in rows if r[1] in ("extracted", "kept"))
print("text available for %d / %d" % (have, len(rows)))
for r in rows:
    if r[1] not in ("extracted", "kept"):
        print("  !", r[0], r[1], r[4])
print("wrote", LOG)

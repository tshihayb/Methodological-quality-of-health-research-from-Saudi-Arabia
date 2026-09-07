# -*- coding: utf-8 -*-
# Build and PERSIST a PMID -> PDF-path map for all 385 analysis papers.
# Prior sessions rebuilt this map in memory each time; this writes it down.
#
# Sources, in preference order:
#   1. project mirror  private/fulltext/pdf-by-pmid/<PMID>.pdf   (short paths, already by PMID)
#   2. granted read-only folder "...\Full text of included papers\Both" (389 PDFs, named by title)
#
# CRITICAL: the granted folder path is 139 chars, so long titles blow past Windows MAX_PATH.
# Every absolute open MUST be prefixed with \\?\ (see feedback-directory-scope).
#
# Run from the repository root.
import csv, difflib, json, os, re, sys, warnings
warnings.simplefilter("ignore")
import fitz  # PyMuPDF

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

EXT = r"C:\Users\[USER]\OneDrive\Consulting company project with Yasser\Saudi Arabia Healthcare Research Landscape\Full text of included papers\Both"
MIRROR = "private/fulltext/pdf-by-pmid"
OUTMAP = "data/provenance/08_23_2026_pdf_pmid_map_385.csv"


def longpath(p):
    p = os.path.abspath(p).replace("/", "\\")
    return "\\\\?\\" + p if not p.startswith("\\\\?\\") else p


def norm(s):
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())


# ---------------- the 385 + titles + DOIs ----------------
pmids = [r["PMID"].strip() for r in
         csv.DictReader(open("data/analysis/07_25_2026_canonical_385_pmids.csv", encoding="utf-8-sig"))]
oa = json.load(open("data/journals/07_25_2026_openalex_works_385.json", encoding="utf-8"))

titles, dois = {}, {}
for p in pmids:
    rec = oa.get(p) or {}
    titles[p] = rec.get("title") or ""
    d = rec.get("doi") or ""
    dois[p] = d.replace("https://doi.org/", "").lower().strip()

print("PMIDs: %d | with title: %d | with DOI: %d"
      % (len(pmids), sum(1 for p in pmids if titles[p]), sum(1 for p in pmids if dois[p])))

# ---------------- candidate PDFs ----------------
mirror = {}
if os.path.isdir(MIRROR):
    for f in os.listdir(MIRROR):
        if f.lower().endswith(".pdf"):
            mirror[os.path.splitext(f)[0]] = os.path.join(MIRROR, f)

extfiles = [f for f in os.listdir(EXT) if f.lower().endswith(".pdf")]
extnorm = {}
for f in extfiles:
    extnorm.setdefault(norm(os.path.splitext(f)[0]), []).append(f)
print("mirror PDFs: %d | external PDFs: %d" % (len(mirror), len(extfiles)))

used = set()          # external filenames already claimed
result = {}           # pmid -> (path, source, method, detail)


def claim(pmid, fn, method, detail=""):
    used.add(fn)
    result[pmid] = (os.path.join(EXT, fn), "external", method, detail)


# ---- pass 0: project mirror (exact PMID filename) ----
for p in pmids:
    if p in mirror:
        result[p] = (mirror[p], "mirror", "pmid_filename", "")
print("pass0 mirror: %d" % len(result))

# ---- pass 1: exact normalized-title match ----
for p in pmids:
    if p in result or not titles[p]:
        continue
    cands = [f for f in extnorm.get(norm(titles[p]), []) if f not in used]
    if len(cands) == 1:
        claim(p, cands[0], "exact_norm")
print("after pass1 exact_norm: %d" % len(result))

# ---- pass 2: prefix match (filenames get truncated by the OS / by hand) ----
ext_items = [(norm(os.path.splitext(f)[0]), f) for f in extfiles]
for p in pmids:
    if p in result or not titles[p]:
        continue
    nt = norm(titles[p])
    if len(nt) < 20:
        continue
    hits = [f for fnorm, f in ext_items
            if f not in used and len(fnorm) >= 25
            and (nt.startswith(fnorm) or fnorm.startswith(nt[:min(len(nt), 60)]))]
    if len(set(hits)) == 1:
        claim(p, hits[0], "prefix")
print("after pass2 prefix: %d" % len(result))

# ---- pass 3: fuzzy, high threshold, mutually best ----
for p in pmids:
    if p in result or not titles[p]:
        continue
    nt = norm(titles[p])
    best, best_r = None, 0.0
    for fnorm, f in ext_items:
        if f in used:
            continue
        r = difflib.SequenceMatcher(None, nt, fnorm).ratio()
        if r > best_r:
            best, best_r = f, r
    if best and best_r >= 0.90:
        claim(p, best, "fuzzy", "%.3f" % best_r)
print("after pass3 fuzzy>=0.90: %d" % len(result))

# ---- pass 4: content match — read page 1-2 of every still-unclaimed PDF, look for the DOI ----
unmatched = [p for p in pmids if p not in result]
if unmatched:
    free = [f for f in extfiles if f not in used]
    print("pass4 content match: %d PMIDs vs %d free PDFs" % (len(unmatched), len(free)))
    head = {}
    for f in free:
        try:
            doc = fitz.open(longpath(os.path.join(EXT, f)))
            t = "".join(doc[i].get_text() for i in range(min(2, doc.page_count)))
            doc.close()
            head[f] = t
        except Exception as e:
            head[f] = ""
            print("   ! unreadable: %s (%s)" % (f[:60], str(e)[:60]))
    for p in list(unmatched):
        d = dois[p]
        if not d:
            continue
        hits = [f for f in free if f not in used and d in head.get(f, "").lower()]
        if len(hits) == 1:
            claim(p, hits[0], "content_doi")
    # title-in-text fallback
    for p in [q for q in unmatched if q not in result]:
        nt = norm(titles[p])[:70]
        if len(nt) < 30:
            continue
        hits = [f for f in free if f not in used and nt in norm(head.get(f, ""))]
        if len(hits) == 1:
            claim(p, hits[0], "content_title")
print("after pass4 content: %d" % len(result))

# ---------------- write the map ----------------
os.makedirs("data/provenance", exist_ok=True)
with open(OUTMAP, "w", newline="", encoding="utf-8-sig") as fh:
    w = csv.writer(fh)
    w.writerow(["PMID", "source", "match_method", "match_detail", "pdf_path", "path_len", "title"])
    for p in pmids:
        if p in result:
            path, src, meth, det = result[p]
            w.writerow([p, src, meth, det, path, len(os.path.abspath(path)), titles[p]])
        else:
            w.writerow([p, "", "UNMATCHED", "", "", "", titles[p]])

missing = [p for p in pmids if p not in result]
print("\nMAPPED %d / %d   UNMATCHED %d" % (len(result), len(pmids), len(missing)))
by = {}
for p in result:
    by[result[p][2]] = by.get(result[p][2], 0) + 1
print("by method:", by)
print("long paths (>=260 chars, need \\\\?\\):",
      sum(1 for p in result if len(os.path.abspath(result[p][0])) >= 260))
if missing:
    print("\nUNMATCHED PMIDs:")
    for p in missing:
        print("  ", p, titles[p][:90])
print("\nwrote", OUTMAP)

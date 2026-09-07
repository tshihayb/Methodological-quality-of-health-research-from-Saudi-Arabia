"""
Prove the public repository lands on the same answers as the private analysis.

De-identification is only safe if it changes nothing but the labels. This runs
the scorer inside public-repo/ against the de-identified data, maps the private
outputs through the id map, and compares row for row. Any difference is a defect
in the de-identification, not an acceptable cost of it.

It exists because the first attempt DID differ: the scorer hard-codes two PMIDs
and, with surrogate ids in the data but real ones in the code, those two studies
silently lost a validity flag. Nothing errored. Only a comparison catches that.

    python public-repo/tools/verify_reproduces.py
Exit 0 if identical, 1 otherwise.
"""
import csv, json, os, subprocess, sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
PUB = os.path.join(ROOT, "public-repo")
MAP = os.path.join(ROOT, "private", "public_repo_id_map_DO_NOT_COMMIT.json")
RSCRIPT = r"C:\Program Files\R\R-4.5.2\bin\x64\Rscript.exe"

OUTPUTS = ["07_30_2026_scored_study.csv",
           "07_30_2026_scored_domain.csv",
           "07_30_2026_scored_items_long.csv"]


def rows(path, id_map=None):
    with open(path, encoding="utf-8-sig", newline="") as f:
        out = []
        for r in csv.DictReader(f):
            d = dict(r)
            if id_map is not None and "PMID" in d:
                d["PMID"] = id_map.get(d["PMID"], d["PMID"])
            out.append(tuple(sorted(d.items())))
        return out


def main():
    if not os.path.exists(MAP):
        print("no id map; run build_public_repo.py first")
        return 1
    id_map = json.load(open(MAP, encoding="utf-8"))["map"]

    print("running the scorer inside public-repo/ ...")
    r = subprocess.run([RSCRIPT, "code/scoring/07_30_2026_score_dataset.R"],
                       cwd=PUB, capture_output=True, text=True)
    if r.returncode != 0:
        print("scorer failed:\n%s" % (r.stderr or r.stdout)[-1500:])
        return 1
    tail = [l for l in (r.stdout or "").splitlines() if l.strip()][-4:]
    for l in tail:
        print("   %s" % l)

    print()
    ok = True
    for name in OUTPUTS:
        priv = rows(os.path.join(ROOT, "data", "scoring", name), id_map)
        pub = rows(os.path.join(PUB, "data", "scoring", name))
        same = sorted(priv) == sorted(pub)
        only_p = len(set(priv) - set(pub))
        only_q = len(set(pub) - set(priv))
        print("   %-34s private %5d | public %5d | %s"
              % (name, len(priv), len(pub),
                 "IDENTICAL" if same else "DIFFERS  (%d private-only, %d public-only)"
                 % (only_p, only_q)))
        if not same:
            ok = False
            for t in list(set(priv) - set(pub))[:2]:
                d = dict(t)
                print("      private row %s" % d.get("PMID"))
                q = {dict(x).get("PMID"): dict(x) for x in pub}.get(d.get("PMID"))
                if q:
                    for k in d:
                        if d[k] != q.get(k):
                            print("         %-20s private=%-14s public=%s" % (k, d[k], q.get(k)))

    print()
    if ok:
        print("PASS: the de-identified build reproduces the private scoring exactly.")
        return 0
    print("FAIL: de-identification changed the results. Do not publish.")
    return 1


if __name__ == "__main__":
    sys.exit(main())

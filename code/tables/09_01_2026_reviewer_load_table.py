"""
Supplementary Table: how the 385 analysed papers were distributed across the
thirteen reviewers, in total and by task.

Counts REVIEWS, not papers: every paper was read by two reviewers, so the column
totals are 770, not 385. Each paper therefore contributes to two rows.

Input  codes audit/output/assignment/09_01_2026_final_reviewer_pairs_385.csv
         the realised pairing, produced by
         code/assignment/09_01_2026_assignment_pipeline.R --final, and verified
         against the study's own Reviewer_ID record on all 377 papers for which
         such a record exists.
       data/analysis/07_23_2026_ANALYSIS_DATASET_wide.csv  for the task.
Output data/tables/09_01_2026_reviewer_load.csv  and a markdown block.
"""
import csv, os, collections

## Fourteen identifiers were issued during recruitment. Reviewer 3 completed both
## calibration rounds and then withdrew before the main review, so thirteen people
## did the reviewing.
##
## The main-review table numbers those thirteen CONTIGUOUSLY, 1 to 13: reviewers 1
## and 2 keep their numbers and everyone above 3 shifts down one, so the original
## 4 becomes 3 and the original 14 becomes 13. That leaves no gap in a table of
## thirteen rows.
##
## These numbers are NOT the recruitment identifiers, but they ARE the numbering
## already used by the calibration displays: Calibration_data_final.R:87 applies
## the identical map, setNames(paste0("R", seq_along(REVIEWERS)), REVIEWERS) over
## R1,R2,R4..R14. A reviewer therefore carries one number across every display.
RECRUITED_ID = {"R1": 1, "R2": 2, "R-withdrawn": 3, "R3": 4, "R4": 5,
                "R5": 6, "R6": 7, "R7": 8, "R8": 9, "R9": 10,
                "R10": 11, "R11": 12, "R12": 13, "R13": 14}
WITHDREW_ID = 3
def review_number(name):
    """Recruitment identifier -> contiguous 1..13 for the thirteen who reviewed."""
    i = RECRUITED_ID[name]
    assert i != WITHDREW_ID, "reviewer %d withdrew and files no reviews" % i
    return i if i < WITHDREW_ID else i - 1
REVIEWER_ID = RECRUITED_ID

PAIRS = os.path.join("data", "tables",
                     "09_01_2026_final_reviewer_pairs_385.csv")
WIDE = os.path.join("data", "analysis", "07_23_2026_ANALYSIS_DATASET_wide.csv")
OUTD = os.path.join("outputs", "tables")
TASKS = ["Descriptive", "Predictive", "Causal"]


def main():
    with open(WIDE, encoding="utf-8-sig") as f:
        task = {r["PMID"].strip(): r.get("Study_Type", "").strip()
                for r in csv.DictReader(f)}

    with open(PAIRS, encoding="utf-8-sig") as f:
        pairs = list(csv.DictReader(f))

    load = collections.defaultdict(lambda: collections.Counter())
    papers = 0
    unknown = collections.Counter()
    for r in pairs:
        p = r["PMID"].strip()
        t = task.get(p, "")
        if t not in TASKS:
            unknown[t] += 1
            continue
        papers += 1
        for who in (r["reviewer_1"].strip(), r["reviewer_2"].strip()):
            if who:
                load[who][t] += 1
                load[who]["Total"] += 1

    if unknown:
        print("!! papers with an unrecognised task: %s" % dict(unknown))

    unknown_names = [w for w in load if w not in REVIEWER_ID]
    assert not unknown_names, "reviewer not in the identifier map: %s" % unknown_names
    rows = []
    for who in sorted(load, key=lambda w: RECRUITED_ID[w]):    # by identifier, not by load
        rows.append({"Reviewer": "R%d" % review_number(who),
                     "Total": load[who]["Total"],
                     **{t: load[who][t] for t in TASKS}})
    tot = {"Reviewer": "All reviewers",
           "Total": sum(r["Total"] for r in rows),
           **{t: sum(r[t] for r in rows) for t in TASKS}}

    os.makedirs(OUTD, exist_ok=True)
    out = os.path.join(OUTD, "09_01_2026_reviewer_load.csv")
    cols = ["Reviewer", "Total"] + TASKS
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)
        w.writerow(tot)

    # ⚠ The workbook as well. Supplementary Table S1 ships as .xlsx and until
    # 2026-09-02 NO SCRIPT PRODUCED IT: the shipped file had been made by hand
    # from this csv, so the table was the one display in the paper that could
    # not be rebuilt, and nothing said so.
    try:
        import openpyxl
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "reviewer_load"
        ws.append(cols)
        for r in rows + [tot]:
            ws.append([r[c] for c in cols])
        for i, c in enumerate(cols, 1):
            ws.column_dimensions[chr(64 + i)].width = max(
                12, len(c) + 2, max(len(str(r[c])) for r in rows + [tot]) + 2)
        for cell in ws[1]:
            cell.font = openpyxl.styles.Font(bold=True)
        xl = os.path.splitext(out)[0] + ".xlsx"
        wb.save(xl)
        print("wrote %s" % xl)
    except ImportError:
        print("  ! openpyxl absent: the .xlsx rendition was not written")

    print("papers counted : %d" % papers)
    print("reviews counted: %d  (2 per paper)" % tot["Total"])
    print("reviewers      : %d" % len(rows))
    print("\n| Reviewer | Reviews | Descriptive | Predictive | Causal |")
    print("|---|---|---|---|---|")
    for r in rows:
        print("| %s | %d | %d | %d | %d |"
              % (r["Reviewer"], r["Total"], r["Descriptive"], r["Predictive"],
                 r["Causal"]))
    print("| **All reviewers** | **%d** | **%d** | **%d** | **%d** |"
          % (tot["Total"], tot["Descriptive"], tot["Predictive"], tot["Causal"]))
    print("\nrange: %d to %d reviews" % (min(r["Total"] for r in rows),
                                         max(r["Total"] for r in rows)))
    print("wrote %s" % out.replace(os.sep, "/"))


if __name__ == "__main__":
    main()

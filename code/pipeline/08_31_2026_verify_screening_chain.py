# NOTE (public repository): 3 hard-coded study identifier(s) were
# rewritten to de-identified surrogates by tools/build_public_repo.py.
# They are rulings about particular studies rather than values the data
# can supply, so they have to travel with it.
"""
VERIFY the screening chain: 1,000 sampled -> 621 screened -> 385 included.

This is the last unverified link before dual review. It checks that the analysed
385 follows from the ordered sampling frame plus the two screening batch files,
rather than only from the ledger that was built out of them.

  frame    data/screening/first1000sample_21-12-23.xlsx      Seq 1..1000, the drawn order
  batch 1  data/screening/f300_ta_ya_TA.xlsx                 Seq 1..300,  Included / Excluded sheets
  batch 2  data/screening/s300_adjudicated.xlsx              Seq 301..621, All + disagreement sheets

Batch 2 records both screeners' calls in one sheet, with the two directions of
disagreement resolved in their own sheets, so inclusion there is: both said Include,
plus those adjudicated to Include, minus those adjudicated to Exclude.

Three papers were removed after inclusion and replaced from a pool outside the 1,000
(deviation D3), so the reproduced set is compared to the analysed 385 both before and
after that substitution.

Run:  python code/pipeline/08_31_2026_verify_screening_chain.py
Exits 0 on pass, 1 on failure. Read-only; writes nothing.
"""
import openpyxl, os, sys, csv, collections

FRAME = 'data/screening/first1000sample_21-12-23.xlsx'
B1 = 'data/screening/f300_ta_ya_TA.xlsx'
B2 = 'data/screening/s300_adjudicated.xlsx'
ANALYSED = 'data/analysis/07_23_2026_ANALYSIS_DATASET_wide.csv'

# Removed after inclusion and replaced from the supplementary pool (D3).
LATE_REMOVED = {'STUDY-0956': 'co-authored by YA',
                'STUDY-0136': 'no Saudi affiliation',
                'STUDY-0478': 'no Saudi affiliation'}


def s(v):
    return '' if v is None else str(v).strip()


def pm(v):
    t = s(v)
    return t.split('.')[0] if t.replace('.', '', 1).isdigit() else t


def sheets(path):
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    out = {}
    for ws in wb.worksheets:
        it = ws.iter_rows(values_only=True)
        try:
            hdr = [s(c) for c in next(it)]
        except StopIteration:
            continue
        rows = [r for r in it if r and any(x is not None for x in r)]
        out[ws.title.strip()] = (hdr, rows)
    wb.close()
    return out


def col(hdr, *names):
    """Match a column by exact name first, then by prefix, tolerating stray spaces."""
    for n in names:
        if n in hdr:
            return hdr.index(n)
    for n in names:
        for i, h in enumerate(hdr):
            if h.strip().lower().startswith(n.strip().lower()):
                return i
    return None


def main():
    frame = sheets(FRAME)
    fh, fr = list(frame.values())[0]
    fi_seq, fi_pmid = col(fh, 'Seq'), col(fh, 'PMID')
    order = {}
    for r in fr:
        seq = s(r[fi_seq])
        if seq:
            order[int(float(seq))] = pm(r[fi_pmid])
    print('frame: %d rows, Seq %d..%d' % (len(order), min(order), max(order)))

    # ---------- batch 1 ----------
    b1 = sheets(B1)
    inc1 = {pm(r[col(b1['Included'][0], 'PMID')]) for r in b1['Included'][1]}
    exc1 = {pm(r[col(b1['Excluded'][0], 'PMID')]) for r in b1['Excluded'][1]}
    print('\nbatch 1 (Seq 1-300): Included %d | Excluded %d | total %d'
          % (len(inc1), len(exc1), len(inc1 | exc1)))

    # ---------- batch 2 ----------
    b2 = sheets(B2)
    ah, ar = b2['All']
    a_pmid, a_seq = col(ah, 'PMID'), col(ah, 'Seq')
    a_ta, a_ya = col(ah, 'Status_ta'), col(ah, 'Status_ya')

    both_in, both_out, disagree = set(), set(), set()
    for r in ar:
        p = pm(r[a_pmid])
        ta, ya = s(r[a_ta]).lower(), s(r[a_ya]).lower()
        if ta == 'include' and ya == 'include':
            both_in.add(p)
        elif ta == 'exclude' and ya == 'exclude':
            both_out.add(p)
        else:
            disagree.add(p)
    print('batch 2 (Seq 301-621): both Include %d | both Exclude %d | discordant or blank %d | total %d'
          % (len(both_in), len(both_out), len(disagree), len(ar)))

    # disagreement sheets carry the adjudicated call
    adj_in, adj_out, adj_seen = set(), set(), set()
    for name, (h, rows) in b2.items():
        if name == 'All':
            continue
        ci_p = col(h, 'PMID')
        ci_a = col(h, 'Adjudicated', 'adjud')
        if ci_p is None or ci_a is None:
            continue
        for r in rows:
            p = pm(r[ci_p])
            v = s(r[ci_a]).lower() if ci_a < len(r) else ''
            if not v:
                continue
            adj_seen.add(p)
            (adj_in if v.startswith('incl') else adj_out).add(p)
        print('   [%s] %d rows, adjudication column "%s"' % (name, len(rows), h[ci_a]))
    print('   adjudicated to Include %d | to Exclude %d' % (len(adj_in), len(adj_out)))

    inc2 = (both_in | adj_in) - adj_out
    exc2 = (both_out | adj_out) - adj_in
    unresolved = disagree - adj_seen
    print('batch 2 resolved: Included %d | Excluded %d | unresolved %d'
          % (len(inc2), len(exc2), len(unresolved)))
    if unresolved:
        for p in sorted(unresolved)[:10]:
            print('      unresolved %s' % p)

    included = inc1 | inc2
    excluded = exc1 | exc2
    print('\nTOTAL screened %d | included %d | excluded %d'
          % (len(included | excluded), len(included), len(excluded)))

    # ---------- compare to the analysed set ----------
    with open(ANALYSED, encoding='utf-8-sig') as f:
        analysed = {str(row['PMID']).strip() for row in csv.DictReader(f)}
    print('analysed dataset: %d papers' % len(analysed))

    reproduced_after_swap = (included - set(LATE_REMOVED))
    replacements = analysed - reproduced_after_swap
    lost = reproduced_after_swap - analysed

    print('\n---- reproduced screening set vs the analysed 385 ----')
    print('  reproduced as included          : %d' % len(included))
    print('  minus the 3 removed after review: %d' % len(reproduced_after_swap))
    print('  in analysed but not reproduced  : %d  (expect the replacements)' % len(replacements))
    print('  in reproduced but not analysed  : %d  (expect 0)' % len(lost))
    for p in sorted(replacements)[:12]:
        print('     replacement  %s  %s' % (p, 'in the 1,000' if p in order.values() else 'from the pool'))
    for p in sorted(lost)[:12]:
        print('     LOST         %s' % p)
    for p, why in LATE_REMOVED.items():
        print('     removed      %s  (%s)  reproduced-as-included: %s'
              % (p, why, p in included))

    ok = (len(included | excluded) == 621 and len(included) == 385
          and not lost and not unresolved)
    print('\n' + '=' * 78)
    if ok:
        print('PASS: 1,000 sampled -> 621 screened -> 385 included reproduces from the')
        print('      frame and the two batch files, and the analysed set matches once the')
        print('      three post-inclusion replacements are applied.')
    else:
        print('REVIEW: the reproduced screening set does not match. See the counts above.')
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())

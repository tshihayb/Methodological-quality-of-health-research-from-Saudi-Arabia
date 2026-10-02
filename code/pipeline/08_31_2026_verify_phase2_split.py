"""
VERIFY that the phase II adjudication list follows from the two adjudicator worklists.

code/sas/06_04_2026_adjud_comp.sas compared TSA's and YA's independent phase-I
adjudications and emitted the cells on which they differed. That list decided which
cells went to a joint sitting, and it is what separates `TA=YA` from `phaseII` in the
resolution rules of the canonical long dataset. Nothing downstream regenerates it: the
chain runs 06_10_2026 (SAS) -> 07_22 -> 07_23 -> 08_08_385, and the only Python step
in it drops batch-6 rows.

Rule replicated (06_04_2026_adjud_comp.sas:52-78):
  1. inner join the TA and YA worklists on PMID x variable
  2. drop variable in ("Reviewer_ID", "Timestamp")
  3. keep upcase(strip(Adjudciation_type)) == "PARTIAL"     <- YA's copy wins the merge
  4. keep Adjudciation_done_TA == 1 and Adjudciation_done_YA == 1
  5. differ when upcase(strip(Adjduciation_TA)) != upcase(strip(Adjduciation_YA))

Note the comparison is CASE-INSENSITIVE and whitespace-stripped, unlike the reviewer
comparison in 05_19_2025_analysis.sas, which is raw.

Run:  python code/pipeline/08_31_2026_verify_phase2_split.py
Exits 0 on pass, 1 on failure. Read-only; writes nothing.
"""
import openpyxl, os, sys, collections

WL = 'private/reviewers/adjudication-worklists'
TA = '04_17_2026_Needs_adj_raw_progress_TA.xlsx'
YA = '04_17_2026_Needs_adj_raw_progress_YA.xlsx'
SAS_OUT = '06_10_2026_TA_YA_Differed_phase_II.xlsx'

DROP_VARS = {'Reviewer_ID', 'Timestamp'}


def s(v):
    return '' if v is None else str(v).strip()


def key_pmid(v):
    t = s(v)
    return t.split('.')[0] if t.replace('.', '', 1).isdigit() else t


def done(v):
    """SAS tests `ne 1` on a numeric; the cell may arrive as 1, 1.0 or '1'."""
    t = s(v)
    try:
        return float(t) == 1.0
    except ValueError:
        return False


def load(path):
    wb = openpyxl.load_workbook(os.path.join(WL, path), read_only=True, data_only=True)
    ws = wb.worksheets[0]
    it = ws.iter_rows(values_only=True)
    hdr = [s(c) for c in next(it)]
    ci = {c: i for i, c in enumerate(hdr)}
    out, dups = {}, 0
    for r in it:
        if r is None or ci.get('PMID') is None or r[ci['PMID']] is None:
            continue
        k = (key_pmid(r[ci['PMID']]), s(r[ci['variable']]))
        if k in out:
            dups += 1
        out[k] = {c: r[i] for c, i in ci.items() if i < len(r)}
    wb.close()
    return out, dups, hdr


def main():
    ta, dta, _ = load(TA)
    ya, dya, _ = load(YA)
    print('TA worklist rows: %d (duplicate PMID x variable keys: %d)' % (len(ta), dta))
    print('YA worklist rows: %d (duplicate PMID x variable keys: %d)' % (len(ya), dya))

    matched = set(ta) & set(ya)
    print('matched on PMID x variable: %d | TA only: %d | YA only: %d'
          % (len(matched), len(set(ta) - set(ya)), len(set(ya) - set(ta))))

    kept, differ, reasons = 0, set(), collections.Counter()
    type_conflict = 0
    for k in matched:
        t, y = ta[k], ya[k]
        if k[1] in DROP_VARS:
            reasons['dropped housekeeping variable'] += 1
            continue
        if s(t.get('Adjudciation_type')).upper() != s(y.get('Adjudciation_type')).upper():
            type_conflict += 1
        if s(y.get('Adjudciation_type')).upper() != 'PARTIAL':
            reasons['adjudication type not Partial'] += 1
            continue
        if not done(t.get('Adjudciation_done_TA')):
            reasons['TA not marked done'] += 1
            continue
        if not done(y.get('Adjudciation_done_YA')):
            reasons['YA not marked done'] += 1
            continue
        kept += 1
        if s(t.get('Adjduciation_TA')).upper() != s(y.get('Adjduciation_YA')).upper():
            differ.add(k)

    print('\nexcluded before comparison:')
    for r, n in reasons.most_common():
        print('   %-34s %d' % (r, n))
    print('rows compared : %d' % kept)
    print('rows differing: %d  (%.1f%%)' % (len(differ), 100.0 * len(differ) / max(kept, 1)))
    if type_conflict:
        print('note: %d rows where TA and YA disagree on Adjudciation_type;'
              " YA's copy wins the SAS merge" % type_conflict)

    sas, dsas, hdr = load(SAS_OUT)
    sas_keys = {k for k in sas if k[1] not in DROP_VARS}
    print('\nSAS phase II export: %d rows (duplicate keys: %d)' % (len(sas), dsas))

    only_mine, only_sas = differ - sas_keys, sas_keys - differ
    print('\n---- re-derived vs %s ----' % SAS_OUT)
    print('  re-derived differing : %d' % len(differ))
    print('  SAS rows             : %d' % len(sas_keys))
    print('  in both              : %d' % len(differ & sas_keys))
    print('  ONLY re-derived      : %d' % len(only_mine))
    print('  ONLY SAS             : %d' % len(only_sas))
    for k in sorted(only_mine)[:12]:
        t, y = ta[k], ya[k]
        print('     only mine %s / %s  TA=%r YA=%r'
              % (k[0], k[1], s(t.get('Adjduciation_TA'))[:26], s(y.get('Adjduciation_YA'))[:26]))
    for k in sorted(only_sas)[:12]:
        print('     only SAS  %s / %s' % k)

    passed = not only_mine and not only_sas
    print('\n' + '=' * 78)
    if passed:
        print('PASS: the phase II list follows from the two adjudicator worklists.')
    else:
        print('FAIL: the archived phase II list no longer follows from the worklists.')
    return 0 if passed else 1


if __name__ == '__main__':
    sys.exit(main())

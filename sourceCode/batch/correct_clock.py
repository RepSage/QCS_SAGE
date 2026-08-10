# -*- coding: utf-8 -*-
r"""Repairs, IN PLACE, the raw HOBO exports whose logger was launched with
AM/PM swapped - and records the operation in the raw manifest.

History of where this fix lives (both were the archive owner's decisions):
2026-08-06 it was moved out of the app into corrected\ twin copies ("a wrong
timestamp is wrong for every tool, not just QCS"); 2026-08-07 the owner chose
to apply it IN PLACE to the raw CSVs and drop the twin folder - one archive,
one truth. The loggers' own binary exports (raw\<SITE>\<camp>\bruto\*.hobo)
are NOT touched, so the original uncorrected export remains recoverable.

The evidence (changelog v9.1): a submerged light sensor must peak near local
noon. These loggers peaked at 23.2-23.6 h with 0-0.8% of their light energy in
daylight hours; the raw rows read e.g. '08/20/21 11:08:39 PM,25.222,31689.1' -
31 thousand lux at 23 h. Shifted by -12 h they land at 11.2-11.6 h and
99-100% daylight, matching the sound loggers of the same semester. The shift
is EXACTLY 12 h: an AM/PM mistake is exact antiphase.

The shift edits the TEXT of the export - each datetime field is parsed and
re-rendered in the same format - so everything else stays byte-identical and
any HOBO-reading tool parses the repaired file exactly like the original.

Safety gates, all BEFORE the raw file is replaced:
  - the file must be ACCUSED by QCS_Tests.light_clock_phase (a file already
    in phase is reported 'already corrected' and skipped - re-running this
    script can never double-shift);
  - the shifted copy, staged in a LOCAL scratch dir, must come out clean
    (peak near noon, >=90% daylight energy, same row count);
  - only then is the raw file replaced, and its manifest row updated
    (new md5/size, status 'clock_corrected_-12h', dated note).

Usage:  python correct_clock.py
"""
import csv
import datetime as _dt
import hashlib
import os
import re
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import QCS_DataHandler as dh
import QCS_Tests as QC

ROOT = r"\\Abrolhos\Projetos\Seaguard & HOBO\CLAUDE\HOBO"
H_RAW = os.path.join(ROOT, 'raw')
MANIFEST = os.path.join(H_RAW, 'manifest.csv')

# (site, campaign, file) -> hours ADDED to every timestamp.
# All three loggers belong to campaign RRDM 14a MAR 2022, but only 3 of its 7
# sites are affected - individual launch mistakes, not a campaign procedure.
CLOCK_CORRECTIONS = {
    ('PLES', 'RRDM 14a MAR 2022', 'HOBO1_PLeste_210821.csv'):     -12,
    ('PLES', 'RRDM 14a MAR 2022', 'HOBO1_PLeste_210821_0.csv'):   -12,
    ('PLES', 'RRDM 14a MAR 2022', 'HOBO2_PLeste_210821_0.csv'):   -12,
    ('SGOM', 'RRDM 14a MAR 2022', 'HOBO1_SGomes_200821_0.csv'):   -12,
    ('SGOM', 'RRDM 14a MAR 2022', 'HOBO1_SGomes_200821_0_0.csv'): -12,
    ('SGOM', 'RRDM 14a MAR 2022', 'HOBO2_SGomes_200821.csv'):     -12,
    ('TIM2', 'RRDM 14a MAR 2022', 'HOBO1_TIM2_250821.csv'):       -12,
    ('TIM2', 'RRDM 14a MAR 2022', 'HOBO2_TIM2_250821.csv'):       -12,
}

# the HOBOware US-locale datetime field: '08/20/21 11:08:39 PM'
_DT_RE = re.compile(r'\b(\d\d/\d\d/\d\d \d\d:\d\d:\d\d [AP]M)\b')
_DT_FMT = '%m/%d/%y %I:%M:%S %p'


def shift_text(text, hours):
    """Every datetime field in `text` shifted by `hours`, format preserved.
    Returns (new_text, n_shifted)."""
    n = 0

    def _sub(m):
        nonlocal n
        n += 1
        t = _dt.datetime.strptime(m.group(1), _DT_FMT) + _dt.timedelta(hours=hours)
        return t.strftime(_DT_FMT)

    return _DT_RE.sub(_sub, text), n


def _phase(path):
    df, _ = dh.read_hobo({'raw_data_path': os.path.dirname(path),
                          'file_name': os.path.basename(path),
                          'input_type': 'HOBO', 'correct_gmt3h': False}, {})
    return QC.light_clock_phase(df['Datetime'], df['Luminosity (lux)']), len(df)


def _md5(path):
    h = hashlib.md5()
    with open(path, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def update_manifest(repaired):
    """Rewrites the manifest rows of the repaired files: new md5/size, status
    'clock_corrected_-12h' and a dated note. The manifest is the archive's
    integrity record - an edited file with a stale md5 would read as
    corruption, when it is a documented repair."""
    with open(MANIFEST, newline='', encoding='utf-8-sig') as f:
        rows = list(csv.DictReader(f))
        fields = rows and list(rows[0].keys())
    by_dest_name = {os.path.basename(r['dest']): r for r in rows}
    for path in repaired:
        row = by_dest_name.get(os.path.basename(path))
        if row is None:
            print('   WARNING: %s has no manifest row - nothing updated for it'
                  % os.path.basename(path))
            continue
        row['md5'] = _md5(path)
        row['size_bytes'] = str(os.path.getsize(path))
        row['status'] = 'clock_corrected_-12h'
        row['note'] = ('logger launched with AM/PM swapped; -12h applied in place '
                       'on 2026-08-07 by correct_clock.py (owner decision); the '
                       'original export remains in bruto\\*.hobo')
    with open(MANIFEST, 'w', newline='', encoding='utf-8-sig') as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    print('manifest updated for %d file(s)' % len(repaired))


def main():
    scratch = tempfile.mkdtemp(prefix='clockfix_')
    repaired, already = [], []
    try:
        for (site, camp, fname), hours in sorted(CLOCK_CORRECTIONS.items()):
            raw = os.path.join(H_RAW, site, camp, 'planilha', fname)
            if not os.path.isfile(raw):
                raise SystemExit('MISSING raw file: %s' % raw)

            pr, nr = _phase(raw)
            if pr['suspect_shift_h'] is None:
                if pr['evaluable'] and pr['daylight_frac'] > 0.9:
                    already.append(fname)
                    print('%-8s %-32s already corrected (peak %.1f h, daylight %.0f%%) - skipped'
                          % (site, fname, pr['peak_hour'], 100 * pr['daylight_frac']))
                    continue
                raise SystemExit('%s: neither accused nor clearly in phase '
                                 '(peak %.1f h, daylight %.0f%%) - refusing to guess'
                                 % (fname, pr['peak_hour'], 100 * pr['daylight_frac']))

            with open(raw, 'r', encoding='latin-1', newline='') as f:
                text = f.read()
            new, n = shift_text(text, hours)
            if n < 100:
                raise SystemExit('%s: only %d datetime fields matched - wrong format?' % (fname, n))
            tmp = os.path.join(scratch, fname)
            with open(tmp, 'w', encoding='latin-1', newline='') as f:
                f.write(new)

            pc, nc = _phase(tmp)
            if pc['suspect_shift_h'] is not None or pc['collapsed'] or pc['daylight_frac'] < 0.9:
                raise SystemExit('%s: still wrong after %+d h (peak %.1f h, daylight %.0f%%)'
                                 % (fname, hours, pc['peak_hour'], 100 * pc['daylight_frac']))
            if nr != nc:
                raise SystemExit('%s: row count changed (%d -> %d)' % (fname, nr, nc))

            shutil.copy2(tmp, raw)          # all gates passed - replace in place
            repaired.append(raw)
            print('%-8s %-32s %5d timestamps %+d h | peak %5.1f h -> %5.1f h | daylight %3.0f%% -> %3.0f%%'
                  % (site, fname, n, hours, pr['peak_hour'], pc['peak_hour'],
                     100 * pr['daylight_frac'], 100 * pc['daylight_frac']))
    finally:
        shutil.rmtree(scratch, ignore_errors=True)

    if repaired:
        update_manifest(repaired)
    print('\n%d repaired, %d already corrected' % (len(repaired), len(already)))


if __name__ == '__main__':
    main()

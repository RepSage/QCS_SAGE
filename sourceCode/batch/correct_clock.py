# -*- coding: utf-8 -*-
r"""Generates the clock-corrected copies of the raw HOBO exports whose logger
was launched with AM/PM swapped.

This is a DATA repair, not an app feature: a timestamp that is wrong in the
export is wrong for every tool that reads the file, not just QCS. The repair
therefore lives beside the data - corrected copies under
CLAUDE\HOBO\corrected\, mirroring the raw layout - and the raw files are never
touched. This script is the reproducible recipe for that folder: delete
corrected\ and re-run it, and you get the same bytes back.

The evidence (2026-08, see changelog v9.1): a submerged light sensor must peak
near local noon. These loggers peaked at 23.2-23.6 h with 0-0.8% of their light
energy in daylight hours; the raw rows themselves read e.g.
'08/20/21 11:08:39 PM,25.222,31689.1' - 31 thousand lux at 23 h. Shifted by
-12 h they land at 11.2-11.6 h and 99-100% daylight, matching the sound
loggers of the same semester (PAB3 11.6 h / 99.9%, PNOR 11.8 h, ESQRODO
11.7 h). The shift is EXACTLY 12 h, never the measured centroid offset: an
AM/PM mistake is exact antiphase, and the centroid sits slightly off noon only
because cloud and fouling are not symmetric about it.

The shift is applied to the TEXT of the export - each datetime field is parsed
and re-rendered in the same format - so everything else in the file
(readings, serial numbers, event rows like 'Logged') stays byte-identical, and
any HOBO-reading tool parses the corrected copy exactly like the raw one.

Every corrected file is validated before being accepted: the raw file must be
ACCUSED by QCS_Tests.light_clock_phase (the detector shipped in v9.1) and the
corrected one must be CLEAN, with the same number of rows. The script fails
loudly otherwise.

Usage:  python correct_clock.py          (writes CLAUDE\HOBO\corrected\)
"""
import os
import re
import shutil
import sys
import tempfile
import datetime as _dt

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import QCS_DataHandler as dh
import QCS_Tests as QC

ROOT = r"\\Abrolhos\Projetos\Seaguard & HOBO\CLAUDE\HOBO"
H_RAW = os.path.join(ROOT, 'raw')
H_COR = os.path.join(ROOT, 'corrected')

# (site, campaign, file) -> hours ADDED to every timestamp.
# All three loggers belong to campaign RRDM 14a MAR 2022, but only 3 of its 7
# sites are affected - these were individual launch mistakes, not a campaign
# procedure.
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


def main():
    # every candidate is written and VALIDATED in a local scratch dir first;
    # the share is only touched after its file passes all gates. Writing to the
    # share before validating would strand an invalid twin there on failure -
    # and qualify_site prefers any twin it finds, silently.
    scratch = tempfile.mkdtemp(prefix='clockfix_')
    done, staged = [], []
    try:
        for (site, camp, fname), hours in sorted(CLOCK_CORRECTIONS.items()):
            raw = os.path.join(H_RAW, site, camp, 'planilha', fname)
            cor = os.path.join(H_COR, site, camp, 'planilha', fname)
            if not os.path.isfile(raw):
                raise SystemExit('MISSING raw file: %s' % raw)

            with open(raw, 'r', encoding='latin-1', newline='') as f:
                text = f.read()
            new, n = shift_text(text, hours)
            if n < 100:
                raise SystemExit('%s: only %d datetime fields matched - wrong format?' % (fname, n))
            tmp = os.path.join(scratch, fname)
            with open(tmp, 'w', encoding='latin-1', newline='') as f:
                f.write(new)

            # validation gates: the raw must be accused, the corrected must be clean
            pr, nr = _phase(raw)
            pc, nc = _phase(tmp)
            if pr['suspect_shift_h'] is None:
                raise SystemExit('%s: the RAW file is not accused by the detector - '
                                 'why is it in CLOCK_CORRECTIONS?' % fname)
            if pc['suspect_shift_h'] is not None or pc['collapsed'] or pc['daylight_frac'] < 0.9:
                raise SystemExit('%s: still wrong after %+d h (peak %.1f h, daylight %.0f%%)'
                                 % (fname, hours, pc['peak_hour'], 100 * pc['daylight_frac']))
            if nr != nc:
                raise SystemExit('%s: row count changed (%d -> %d)' % (fname, nr, nc))
            staged.append((tmp, cor))
            done.append((site, fname, n, pr, pc))
            print('%-8s %-32s %5d timestamps %+d h | peak %5.1f h -> %5.1f h | daylight %3.0f%% -> %3.0f%%'
                  % (site, fname, n, hours, pr['peak_hour'], pc['peak_hour'],
                     100 * pr['daylight_frac'], 100 * pc['daylight_frac']))

        # every file validated - only now touch the share
        for tmp, cor in staged:
            os.makedirs(os.path.dirname(cor), exist_ok=True)
            shutil.copy2(tmp, cor)
    finally:
        shutil.rmtree(scratch, ignore_errors=True)

    with open(os.path.join(H_COR, 'README.txt'), 'w', encoding='utf-8') as f:
        f.write(
            'Clock-corrected copies of raw HOBO exports. Generated by\n'
            'sourceCode/batch/correct_clock.py (QCS repo) - re-running it rebuilds\n'
            'this folder from raw/; nothing in raw/ is ever modified.\n\n'
            'These loggers were launched with AM/PM swapped, so the whole series\n'
            '(light AND temperature) sat 12 h out of phase. Diagnostic: light\n'
            'peaked at 23.2-23.6 h with 0-0.8%% of its energy in daylight hours;\n'
            'corrected, it peaks at 11.2-11.6 h with 99-100%%, matching the sound\n'
            'loggers of the same semester. See changelog v9.1 of the QCS repo.\n\n'
            'Files (%d, all -12 h):\n%s\n'
            % (len(done), '\n'.join('  %s\\%s' % (s, f) for s, f, *_ in done)))
    print('\n%d corrected file(s) under %s' % (len(done), H_COR))


if __name__ == '__main__':
    main()

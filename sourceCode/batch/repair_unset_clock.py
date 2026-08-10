# -*- coding: utf-8 -*-
r"""Repairs raw HOBO exports whose logger clock was NEVER SET.

These loggers recorded from a factory epoch: the right DURATION on the wrong
DATE, and the wrong time of day too. `HOBO1_PNorte_090521_210821.csv` is a
May-August 2021 deployment stamped 31/12/2017 to 16/04/2018.

Only the six exports whose evidence is unambiguous are listed below - the data
duration matches the archived deployment dates to within a day or two, and the
offset is a single clean constant. The other five wrong-clock files need field
information (see report_unset_clocks.py) and are deliberately absent.

WHY THIS IS NOT CIRCULAR. The correction has two components taken from two
independent sources, and is checked by a third:

  * the DAY offset comes from the deployment dates the team archived in the
    file name - a human record, not the data;
  * the HOUR comes from the light phase: a submerged sensor peaks at local
    noon. This is a MEASUREMENT here, not a test;
  * the CHECK is the TEMPERATURE, correlated against contemporaneous loggers at
    OTHER sites over the corrected window. Temperature is independent of the
    light, so this check is not guaranteed to pass by construction - if the
    epoch were still wrong by months or a year, the seasonal signal would not
    line up. A file whose corrected temperature does not track the region is
    REFUSED.

These exports also carry the collapsed 12-hour clock, so the afternoon half is
reconstructed first (see repair_collapsed_clock.py) and the constant offset is
applied on top. Unlike that repair, this one rewrites the DATE field as well,
so the day-first/month-first order is resolved per file from the file's own
evidence and refused when the file does not prove it.

The .hobo binaries under bruto\ are untouched; where none exists a
`<stem>.original.csv` backup is written there first.

Usage:  repair_unset_clock.py --dry-run   (reports)
        repair_unset_clock.py             (repairs)
"""
import datetime as _dt
import glob
import os
import shutil
import sys
import warnings

warnings.filterwarnings('ignore')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pandas as pd                                                  # noqa: E402
import QCS_DataHandler as dh                                         # noqa: E402
import QCS_Tests as QC                                               # noqa: E402
from repair_collapsed_clock import (_STAMP, parse_stamps,            # noqa: E402
                                    reconstruct, rewrite)

ROOT = r"\\Abrolhos\Projetos\Seaguard & HOBO\CLAUDE\HOBO"
H_RAW = os.path.join(ROOT, 'raw')
H_QLF = os.path.join(ROOT, 'qualified')

# file -> (site, archived start date). Only the six with matching durations.
TARGETS = {
    'Hobo1_RRDM_RecEsqSul2_050320_210221.csv':   ('ESQSUL2', _dt.date(2020, 3, 5)),
    'Hobo_RRDM_RecEsqSul2(B5)_050320_230221.csv': ('ESQSUL2', _dt.date(2020, 3, 5)),
    'HOBO1_PAB3_110521_220821.csv':              ('PAB3', _dt.date(2021, 5, 11)),
    'HOBO2_PAB3_110521_220821.csv':              ('PAB3', _dt.date(2021, 5, 11)),
    'HOBO1_PNorte_090521_210821.csv':            ('PNOR', _dt.date(2021, 5, 9)),
    'HOBO2_PNorte_090521_210821.csv':            ('PNOR', _dt.date(2021, 5, 9)),
}

MIN_REF_CORR = 0.50      # corrected temperature must track the region this well
MIN_REF_DAYS = 60        # ...over at least this many overlapping days


def date_order(text):
    """'month-first' / 'day-first' / None when the file does not prove it."""
    first = second = set()
    first = {int(m.group(1)) for m in _STAMP.finditer(text)}
    second = {int(m.group(2)) for m in _STAMP.finditer(text)}
    if max(first) > 12:
        return 'day-first'
    if max(second) > 12:
        return 'month-first'
    return None


def shift_text(text, order, delta):
    """Every stamp shifted by `delta`, dates rewritten in the file's own order."""
    fmt = '%m/%d/%y' if order == 'month-first' else '%d/%m/%y'

    def _sub(m):
        a, b, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
        mo, dd = (a, b) if order == 'month-first' else (b, a)
        t = _dt.datetime(2000 + y, mo, dd, int(m.group(5)), int(m.group(6)),
                         int(m.group(7))) + delta
        return '%s%s%dh%dmin%ds' % (t.strftime(fmt), m.group(4),
                                    t.hour, t.minute, t.second)

    return _STAMP.sub(_sub, text)


def _read(path):
    df, _ = dh.read_hobo({'raw_data_path': os.path.dirname(path),
                          'file_name': os.path.basename(path),
                          'input_type': 'HOBO', 'correct_gmt3h': False}, {})
    return df


def regional_reference(site, t0, t1):
    """Mean daily temperature of already-qualified HOBO products at OTHER
    sites over [t0, t1] - the independent witness for the corrected epoch."""
    cols = []
    for p in glob.glob(os.path.join(H_QLF, '*', '**', '*_HOBO*_QLF.csv'), recursive=True):
        if os.path.basename(p).startswith(site + '_'):
            continue
        try:
            d = pd.read_csv(p, usecols=lambda c: c in ('Datetime', 'Temperature (degC)', 'Flag_T'))
        except Exception:
            continue
        d['Datetime'] = pd.to_datetime(d['Datetime'], errors='coerce')
        d = d[(d['Datetime'] >= t0) & (d['Datetime'] <= t1)]
        if 'Flag_T' in d.columns:
            d = d[pd.to_numeric(d['Flag_T'], errors='coerce') <= 2]
        if len(d) < 100:
            continue
        cols.append(d.set_index('Datetime')['Temperature (degC)'].resample('D').mean())
    return pd.concat(cols, axis=1).mean(axis=1) if cols else None


def main(dry):
    scratch = os.path.join(os.environ.get('TEMP', '.'), 'unsetclock')
    os.makedirs(scratch, exist_ok=True)
    done, refused = [], []
    for name, (site, archived) in sorted(TARGETS.items()):
        hits = glob.glob(os.path.join(H_RAW, '**', name), recursive=True)
        if not hits:
            refused.append((name, 'not found')); continue
        path = hits[0]
        with open(path, 'r', encoding='latin-1', newline='') as f:
            text = f.read()
        order = date_order(text)
        if order is None:
            refused.append((name, 'the file never shows a day above 12, so it does not '
                                  'prove day-first vs month-first'))
            continue

        # 1. the collapsed 12-hour clock, first
        stamps = parse_stamps(text)
        rec = reconstruct(stamps)
        if rec is None:
            refused.append((name, 'collapsed clock could not be reconstructed')); continue
        tmp = os.path.join(scratch, name)
        # the reconstructed text is what the shift is applied to: shifting the
        # ORIGINAL would move hours that are still collapsed onto 1-12
        recon = rewrite(text, stamps, rec['times'])
        with open(tmp, 'w', encoding='latin-1', newline='') as f:
            f.write(recon)
        df = _read(tmp)
        ph = QC.light_clock_phase(pd.to_datetime(df['Datetime']), df['Luminosity (lux)'])
        if not ph['evaluable']:
            refused.append((name, 'no usable light to set the hour')); continue

        # 2. the HOUR, from the light; 3. the DAY, from the archived date
        hour_shift = int(round(12.0 - ph['peak_hour']))
        provisional = pd.to_datetime(df['Datetime']).min() + pd.Timedelta(hours=hour_shift)
        day_shift = (archived - provisional.date()).days
        delta = pd.Timedelta(days=day_shift, hours=hour_shift)

        out = shift_text(recon, order, delta)
        with open(tmp, 'w', encoding='latin-1', newline='') as f:
            f.write(out)
        df2 = _read(tmp)
        t2 = pd.to_datetime(df2['Datetime'])
        ph2 = QC.light_clock_phase(t2, df2['Luminosity (lux)'])

        # 4. the CHECK: temperature against other sites, independent of light
        ref = regional_reference(site, t2.min(), t2.max())
        own = pd.Series(pd.to_numeric(df2['Temperature (degC)'], errors='coerce').values,
                        index=t2).resample('D').mean()
        if ref is None:
            refused.append((name, 'no contemporaneous other-site data to check the epoch'))
            continue
        both = pd.concat([own, ref], axis=1).dropna()
        both.columns = ['own', 'ref']
        if len(both) < MIN_REF_DAYS:
            refused.append((name, 'only %d overlapping days with other sites - too few '
                                  'to check the epoch' % len(both)))
            continue
        corr = float(both['own'].corr(both['ref']))
        if corr < MIN_REF_CORR:
            refused.append((name, 'corrected temperature does not track the region '
                                  '(r=%+.2f over %d days) - the epoch is still wrong'
                            % (corr, len(both))))
            continue

        if not dry:
            stem = os.path.splitext(name)[0]
            bruto = os.path.join(os.path.dirname(os.path.dirname(path)), 'bruto')
            if not os.path.isfile(os.path.join(bruto, stem + '.hobo')):
                os.makedirs(bruto, exist_ok=True)
                bak = os.path.join(bruto, stem + '.original.csv')
                if not os.path.isfile(bak):
                    shutil.copy2(path, bak)
            shutil.copy2(tmp, path)
        done.append(name)
        print('%-44s %+5d d %+3d h | %s -> %s | luz %4.1f h | T vs regiao r=%+.2f (%d d)'
              % (name[:44], day_shift, hour_shift,
                 pd.to_datetime(df['Datetime']).min().strftime('%d/%m/%Y'),
                 t2.min().strftime('%d/%m/%Y'), ph2['peak_hour'], corr, len(both)))
        os.remove(tmp)

    shutil.rmtree(scratch, ignore_errors=True)
    print('\nrepaired: %d | refused: %d' % (len(done), len(refused)))
    for n, why in refused:
        print('   %-44s %s' % (n[:44], why))
    if dry:
        print('\n(dry run - nothing written)')


if __name__ == '__main__':
    main('--dry-run' in sys.argv)

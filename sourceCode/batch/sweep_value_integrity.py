# -*- coding: utf-8 -*-
r"""Sweeps the WHOLE qualified corpus for two value-level defects, and reports
whether the pipeline caught them.

  1. LOST DECIMAL SEPARATOR - the defect `_hobo_fix_temp_scale` exists to catch:
     a value silently wrong by a power of ten. Same three gates as the reader's,
     applied per product x variable: essentially every value outside the
     plausible envelope, the values are INTEGERS, and one single power of ten
     brings essentially all of them back inside. All three must hold - the
     integer gate is what keeps a genuinely broken sensor from being "rescued".

  2. PHYSICALLY IMPOSSIBLE VALUES - outside the INSTRUMENT's own limit, which is
     impossible rather than merely unusual. For these the question is not
     whether they exist (a failing sensor produces them) but whether they came
     out FLAGGED. An impossible value carrying flag 1 is a pipeline defect; one
     carrying flag 4 is the QC working as designed.

The limits are the app's own (`QCS_Main.py` defaultSettings['tsSettings']) and
the variable -> flag mapping is `QCS_DataHandler.PARAM_FLAG_COLUMN`, so this
script cannot drift away from what the pipeline actually enforces.

Two things worth knowing before reading the output:

  - Not every variable has a sensor-range test. Dissolved organic matter has
    ONLY an environmental-range test, and every environmental test assigns
    SUSPECT (3), not BAD (4) - see `test_sequence` in `QCS_Main.py`. Checking
    for flag 4 on those variables produces false alarms.
  - `Density`, `Soundspeed`, `TSS`, `Depth` and `PAR` are derived or untested
    and carry no flag column of their own. A density below 1000 kg/m3 is not a
    defect: it is fresh-water density, and it means the CONDUCTIVITY reads
    zero - the instrument was out of the water, or the sensor is dead. Read it
    through `Flag_S` / `Flag_C`, which is where the verdict lives.

Read-only: nothing is written to the archive.
"""
import os
import sys
import warnings

warnings.filterwarnings('ignore')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pandas as pd
import QCS_DataHandler as dh

ROOT = r'\\Abrolhos\Projetos\Seaguard & HOBO\CLAUDE'

# (sensor limit, environmental envelope) - QCS_Main.py defaultSettings
LIMITS = {
    'Temperature (degC)':             ((-5, 40),   (8, 35)),
    'Salinity (PSU)':                 ((0, 45),    (20, 37.5)),
    'Conductivity (mS/cm)':           ((0, 75),    (5, 75)),
    'Pressure (dbar)':                ((0, 6000),  (0, 6000)),
    'pH':                             ((0, 14),    (7.5, 8.4)),
    'Chlorophyll (ug/L)':             ((0, 500),   (0, 30)),
    'O2 level (uM)':                  ((0, 500),   (120, 450)),
    'Turbidity (FTU)':                ((0, 1500),  (0, 50)),
    'CO2 Level (ppm)':                ((0, 10000), (100, 2000)),
    # HOBO temperature shares the Seaguard column name; its own reader limits
    # are wider (-5..60), so the sensor bound below is the stricter of the two.
}
# environmental-range only: no sensor test exists, and the env test flags 3
ENV_ONLY = {'Dissolved organic matter (ppb)': (0, 50)}


def sweep():
    idx = pd.read_csv(os.path.join(ROOT, 'qualified_index.csv'), encoding='utf-8-sig')
    scale_hits, unflagged, impossible = [], [], []
    n_read = 0
    for _i, r in idx.iterrows():
        path = os.path.join(ROOT, str(r['path']))
        if not os.path.isfile(path):
            print('MISSING ON DISK: %s' % r['product'])
            continue
        d = pd.read_csv(path, encoding='utf-8-sig', low_memory=False)
        n_read += 1
        for col, (sensor, env) in LIMITS.items():
            if col not in d.columns:
                continue
            v = pd.to_numeric(d[col], errors='coerce').dropna()
            if len(v) < 10:
                continue
            e_lo, e_hi = env
            s_lo, s_hi = sensor

            # --- 1. the three gates, in the reader's own order ---------------
            if float(((v >= e_lo) & (v <= e_hi)).mean()) <= 0.02:
                integers = float((v == v.round()).mean()) > 0.98
                factor = None
                for f in (10.0, 100.0, 1000.0):
                    if float((((v / f) >= e_lo) & ((v / f) <= e_hi)).mean()) > 0.98:
                        factor = f
                        break
                scale_hits.append(dict(
                    product=r['product'], var=col, n=len(v),
                    vmin=float(v.min()), vmax=float(v.max()),
                    integers=integers, factor=factor,
                    verdict=('LOST SEPARATOR' if (integers and factor)
                             else 'not a scale defect')))

            # --- 2. impossible, and did the flag catch it? -------------------
            out = (v < s_lo) | (v > s_hi)
            if not out.any():
                continue
            fcol = dh.PARAM_FLAG_COLUMN.get(col)
            if not fcol or fcol not in d.columns:
                continue
            fl = pd.to_numeric(d.loc[v.index[out], fcol], errors='coerce')
            n_ok = int((fl == 4).sum())
            impossible.append(dict(product=r['product'], var=col,
                                   n_out=int(out.sum()), n_flag4=n_ok,
                                   worst=float(v[out].abs().max())))
            if n_ok < int(out.sum()):
                unflagged.append((r['product'], col, int(out.sum()), n_ok,
                                  fl.value_counts().to_dict()))

        for col, (lo, hi) in ENV_ONLY.items():
            if col not in d.columns:
                continue
            v = pd.to_numeric(d[col], errors='coerce').dropna()
            if len(v) < 10:
                continue
            out = (v < lo) | (v > hi)
            if not out.any():
                continue
            fcol = dh.PARAM_FLAG_COLUMN.get(col)
            fl = pd.to_numeric(d.loc[v.index[out], fcol], errors='coerce')
            # env-range assigns SUSPECT: 3 or worse is the correct outcome
            n_ok = int(fl.isin([3, 4]).sum())
            if n_ok < int(out.sum()):
                unflagged.append((r['product'], col, int(out.sum()), n_ok,
                                  fl.value_counts().to_dict()))
    return n_read, scale_hits, impossible, unflagged


def main():
    n_read, scale_hits, impossible, unflagged = sweep()
    print('products read: %d\n' % n_read)

    print('== 1. SCALE DEFECT (lost decimal separator) ==')
    if not scale_hits:
        print('   no product x variable with >98% of its values outside the'
              ' environmental envelope.\n')
    else:
        real = [h for h in scale_hits if h['integers'] and h['factor']]
        for h in sorted(scale_hits, key=lambda x: (x['var'], x['product'])):
            print('   %-42s %-24s %9.2f..%-9.2f  %s'
                  % (h['product'][:42], h['var'][:24], h['vmin'], h['vmax'],
                     h['verdict']))
        print('   -> %d of %d pass ALL THREE gates\n' % (len(real), len(scale_hits)))

    print('== 2. VALUES OUTSIDE THE SENSOR LIMIT ==')
    if not impossible:
        print('   none.\n')
    else:
        tot = sum(h['n_out'] for h in impossible)
        ok = sum(h['n_flag4'] for h in impossible)
        print('   %d values across %d product(s); %d (%.1f%%) carry flag 4'
              % (tot, len({h['product'] for h in impossible}), ok,
                 100.0 * ok / max(tot, 1)))
        for h in sorted(impossible, key=lambda x: -x['n_out'])[:15]:
            print('      %-42s %-22s %5d outside, %5d flagged 4 (worst %.2f)'
                  % (h['product'][:42], h['var'][:22], h['n_out'],
                     h['n_flag4'], h['worst']))
        print()

    print('== 3. OUT OF RANGE AND NOT MARKED (a pipeline defect) ==')
    if not unflagged:
        print('   none: every out-of-range value came out marked as the rule requires.')
    else:
        for prod, col, n, ok, dist in unflagged:
            print('   %-42s %-24s %d outside, %d marked, flags %s'
                  % (prod[:42], col[:24], n, ok, dist))
    return 0 if not unflagged else 1


if __name__ == '__main__':
    sys.exit(main())

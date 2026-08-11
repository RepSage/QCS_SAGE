# -*- coding: utf-8 -*-
r"""Builds the master index of the qualified corpus.

Walks CLAUDE\{SEAGUARD|HOBO}\qualified\, reads every <NAME>_QLF.csv and its
provenance.txt entry, and writes ONE row per product to
CLAUDE\qualified_index.csv: what it is (instrument/semester/site/tipo), where
it came from (campaign, cast, input sessions, CO2 file, C/D stations), what it
holds (rows, time span, CO2 points, panel count) and where it lives.

Usage:  python build_index.py            (writes CLAUDE\qualified_index.csv)
        python build_index.py <out.csv>  (writes elsewhere)
Read-only over the products; safe to re-run at any time.
"""
import os
import re
import sys
import glob
import warnings
warnings.filterwarnings('ignore')
import pandas as pd

ROOT = r"\\Abrolhos\Projetos\Seaguard & HOBO\CLAUDE"


def parse_provenance(path):
    """{product name: {field: value}} for one provenance.txt."""
    out = {}
    if not os.path.exists(path):
        return out
    for block in open(path, encoding='utf-8').read().split('\n\n'):
        lines = [ln for ln in block.splitlines() if ln.strip()]
        if not lines or lines[0].startswith(' '):
            continue
        e = {}
        for ln in lines[1:]:
            m = re.match(r'\s*(\w+)\s*:\s*(.*)', ln)
            if m:
                e[m.group(1)] = m.group(2).strip()
        out[lines[0].strip()] = e
    return out


def main(out_csv):
    rows = []
    pattern = os.path.join(ROOT, '*', 'qualified', '*', '**', '*_QLF.csv')
    for p in sorted(glob.glob(pattern, recursive=True)):
        name = os.path.basename(p)[:-4]
        parts = os.path.relpath(p, ROOT).split(os.sep)
        semester = parts[2]
        bucket = parts[3] if parts[3].startswith('_') and len(parts) > 5 else ''
        site = parts[4] if bucket else parts[3]
        kind = ('DOPPLER' if '_DOPPLER_' in name
                else 'HOBO' if '_HOBO' in name else 'SEAGUARD')
        prov = parse_provenance(os.path.join(os.path.dirname(p), 'provenance.txt')
                                ).get(name, {})
        try:
            d = pd.read_csv(p, usecols=lambda c: c in ('Datetime', 'CO2 Level (ppm)'))
            t = pd.to_datetime(d['Datetime'], errors='coerce')
            n_rows = len(d)
            t0, t1 = t.min(), t.max()
            co2_pts = (int(d['CO2 Level (ppm)'].notna().sum())
                       if 'CO2 Level (ppm)' in d.columns else 0)
        except Exception as e:
            n_rows, t0, t1, co2_pts = -1, None, None, 0
            print('Warning: unreadable product %s (%s)' % (name, str(e)[:50]))
        n_panels = len(glob.glob(os.path.join(os.path.dirname(p), 'DataView',
                                              name, '*.svg')))
        rows.append({
            'product': name, 'instrument': kind, 'semester': semester,
            'site': site, 'bucket': bucket, 'tipo': prov.get('tipo', ''),
            'campaign': prov.get('campaign', ''), 'cast_start': prov.get('cast', ''),
            'n_rows': n_rows,
            't_start': t0.strftime('%Y-%m-%d %H:%M') if t0 is not pd.NaT and t0 else '',
            't_end': t1.strftime('%Y-%m-%d %H:%M') if t1 is not pd.NaT and t1 else '',
            'co2_file': prov.get('co2', '-'), 'co2_points': co2_pts,
            'stations': prov.get('stations', ''),
            'inputs': prov.get('inputs', ''), 'n_panels': n_panels,
            'path': os.path.relpath(p, ROOT),
        })
    df = pd.DataFrame(rows)
    df.to_csv(out_csv, index=False, encoding='utf-8-sig')
    print('index: %d product(s) -> %s' % (len(df), out_csv))
    print(df.groupby(['instrument']).size().to_string())
    print('with CO2 merged: %d' % int((df['co2_points'] > 0).sum()))

    # STALE PRODUCTS: a raw export must feed exactly one product. When it feeds
    # two, an earlier run's product was left behind under a name the current
    # run no longer produces - which happens whenever replicate GROUPING
    # changes (repairing the collapsed clock regrouped several deployments,
    # both splitting and merging them). The old file stays indexed and carries
    # the un-repaired data, so the corpus would double-count the deployment.
    owners = {}
    for _i, r in df.iterrows():
        for src in str(r.get('inputs') or '').split('|'):
            src = src.strip()
            if src and src != '-':
                owners.setdefault(src, []).append(r['product'])
    shared = {s: p for s, p in owners.items() if len(set(p)) > 1}
    if shared:
        stale = sorted({p for ps in shared.values() for p in ps})
        print('\nWARNING: %d raw export(s) feed more than one product - likely a stale\n'
              'product from an earlier run (see STATUS.md). Products involved:' % len(shared))
        for p in stale:
            print('   %s' % p)
    return df


if __name__ == '__main__':
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, 'qualified_index.csv')
    main(out)
    # A corpus round ends here, and that is exactly when the value-level
    # integrity questions should be asked - the lost-separator gates and the
    # "impossible value not flagged" check (see sweep_value_integrity.py).
    # Running it by hand was one forgotten step away from never running: wired
    # in since 2026-08-11. A failing sweep makes this script exit non-zero.
    print('\n' + '=' * 70)
    print('value-integrity sweep over the indexed products')
    print('=' * 70)
    import sweep_value_integrity
    sys.exit(sweep_value_integrity.main())

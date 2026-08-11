# -*- coding: utf-8 -*-
r"""Packages qualified data for delivery: one unified spreadsheet plus every
DataView panel of the selected products, archived on the Desktop.

Grew out of the one-off that shipped the 2019-2024 HOBO bundle (August 2026);
promoted here because "a spreadsheet with these sites and years, plus panels"
is a recurring lab request, and every ad-hoc copy of the script is a chance to
diverge from the corpus rules.

The unification goes through QCS_DataHandler.build_database - the project's
single merge engine - rather than a concat here, so the result follows the same
rules (layout detection, exact-duplicate removal, Site+Datetime overlap
warnings) as anything else that merges qualified files.

Usage (from sourceCode\):
  build_data_package.py --sites ESQSUL,SGOM,PLES --years 2019-2024
  build_data_package.py --instrument HOBO --sites PAB3 --years 2021-2023 --name my_bundle

--instrument   HOBO (default) or SEAGUARD
--sites        comma-separated site codes, as named in the index
--years        first-last, by CALENDAR date: the semester tags when a logger
               was RECOVERED, so deployments that started earlier are trimmed
               to the window rather than dropped
--name         archive name (default: built from instrument/sites/years)

The archive is .rar when WinRAR is installed (the lab standard), .zip otherwise.
"""
import argparse
import glob
import os
import shutil
import subprocess
import sys
import warnings

warnings.filterwarnings('ignore')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pandas as pd

import QCS_DataHandler as dh

ROOT = r'\\Abrolhos\Projetos\Seaguard & HOBO\CLAUDE'
DESKTOP = os.path.join(os.path.expanduser('~'), 'Desktop')
RAR = r'C:\Program Files\WinRAR\Rar.exe'


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--instrument', default='HOBO', choices=['HOBO', 'SEAGUARD'])
    ap.add_argument('--sites', required=True, help='comma-separated site codes')
    ap.add_argument('--years', required=True, help='first-last, e.g. 2019-2024')
    ap.add_argument('--name', default=None)
    args = ap.parse_args()

    sites = [s.strip() for s in args.sites.split(',') if s.strip()]
    y0, y1 = (int(p) for p in args.years.split('-'))
    name = args.name or ('%s_qualified_%s_%d-%d'
                         % (args.instrument, '-'.join(sites), y0, y1))
    stage = os.path.join(os.environ['TEMP'], 'QCS_package')

    idx = pd.read_csv(os.path.join(ROOT, 'qualified_index.csv'), encoding='utf-8-sig')
    sel = idx[(idx['instrument'].astype(str).str.upper() == args.instrument)
              & idx['site'].astype(str).isin(sites)
              & idx['semester'].astype(str).str[:4].astype(int).between(y0, y1)]
    sel = sel.sort_values(['site', 'semester', 'product'])
    print('products selected: %d' % len(sel))
    if not len(sel):
        print('nothing matches - check the site codes against the index.')
        return 1

    if os.path.isdir(stage):
        shutil.rmtree(stage)
    os.makedirs(stage)

    # ---- 1. the unified spreadsheet, through the project's own merge engine --
    files = [os.path.join(ROOT, str(p)) for p in sel['path']]
    db, msgs = dh.build_database(args.instrument, file_list=files)
    for m in msgs:
        print('   %s' % str(m)[:150])
    db['Datetime'] = pd.to_datetime(db['Datetime'], errors='coerce')
    n_before = len(db)
    db = db[(db['Datetime'] >= '%d-01-01' % y0)
            & (db['Datetime'] <= '%d-12-31 23:59:59' % y1)]
    print('calendar window %d-%d: %d -> %d rows (%d outside)'
          % (y0, y1, n_before, len(db), n_before - len(db)))
    db = db.sort_values(['Site', 'Datetime'])
    print('unified sheet: %d rows x %d columns | %s to %s'
          % (len(db), len(db.columns), db['Datetime'].min(), db['Datetime'].max()))

    xls = os.path.join(stage, name + '.xlsx')
    with pd.ExcelWriter(xls, engine='openpyxl') as w:
        db.to_excel(w, sheet_name='qualified_data', index=False)
        # a second sheet naming exactly which products went in, so the sheet is
        # traceable back to the corpus without opening the index
        sel[['product', 'site', 'semester', 'campaign', 'n_rows', 't_start',
             't_end', 'inputs']].to_excel(w, sheet_name='included_products',
                                          index=False)
    print('written: %s' % os.path.basename(xls))

    # ---- 2. the DataView panels, one folder per product ---------------------
    dv_root = os.path.join(stage, 'DataView')
    os.makedirs(dv_root)
    n_panels = 0
    for _i, r in sel.iterrows():
        src = os.path.join(os.path.dirname(os.path.join(ROOT, str(r['path']))),
                           'DataView', str(r['product']))
        if os.path.isdir(src):
            dst = os.path.join(dv_root, str(r['product']))
            shutil.copytree(src, dst)
            n_panels += len(glob.glob(os.path.join(dst, '*.svg')))
    print('DataView: %d panel(s) in %d folder(s)' % (n_panels, len(os.listdir(dv_root))))

    # ---- 3. a README so the package explains itself -------------------------
    with open(os.path.join(stage, 'README.txt'), 'w', encoding='utf-8') as f:
        f.write(
            'Qualified %s data - %s, %d to %d\n'
            'Generated on %s by QCS %s\n\n'
            'CONTENTS\n'
            '  %s.xlsx\n'
            '     sheet "qualified_data"     - every product unified by\n'
            '        QCS_DataHandler.build_database (the project\'s single merge engine)\n'
            '     sheet "included_products"  - which products went in, with campaign,\n'
            '        period and raw source files\n'
            '  DataView\\<product>\\  - each product\'s panels\n\n'
            'FLAGS (Flag_* columns)\n'
            '  1 = good | 2 = not evaluated | 3 = suspect | 4 = bad | 5 = dismissed | 9 = missing\n\n'
            'NOTES\n'
            '  - The semester is the CAMPAIGN label, not the data\'s: some deployments\n'
            '    start before the semester they were recovered in. Each product\'s real\n'
            '    period is on the "included_products" sheet.\n'
            '  - Products suffixed _TEMP_ONLY come from loggers with no light sensor:\n'
            '    the light column is empty by nature, not by failure.\n'
            '  - The corpus light window is FIXED at 60 days after deployment;\n'
            '    beyond it Flag_lux = 4 (fouling presumed).\n'
            % (args.instrument, '/'.join(sites), y0, y1,
               pd.Timestamp.now().strftime('%d/%m/%Y %H:%M'), dh.QCS_VERSION, name))

    # ---- 4. the archive -----------------------------------------------------
    if os.path.isfile(RAR):
        out = os.path.join(DESKTOP, name + '.rar')
        if os.path.exists(out):
            os.remove(out)
        p = subprocess.run([RAR, 'a', '-r', '-ep1', out, os.path.join(stage, '*')],
                           capture_output=True, text=True)
        if p.returncode:
            print('rar FAILED rc=%d\n%s' % (p.returncode, (p.stderr or '')[-400:]))
            return 1
    else:
        # no WinRAR on this machine: fall back to zip rather than failing
        out = shutil.make_archive(os.path.join(DESKTOP, name), 'zip', stage)
    print('archive: %s  (%.1f MB)' % (out, os.path.getsize(out) / 1e6))
    shutil.rmtree(stage, ignore_errors=True)
    return 0


if __name__ == '__main__':
    sys.exit(main())

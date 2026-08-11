# -*- coding: utf-8 -*-
r"""The exports whose logger clock looks WRONG in absolute terms.

For each, puts side by side what the file NAME claims (the deployment dates the
team wrote when archiving) and what the DATA says, plus where the light peaks.
A logger whose clock was never set keeps the right DURATION on the wrong EPOCH.

Read-only - this only reports, so the operator can check against field records.
"""
import glob
import os
import re
import sys
import warnings

warnings.filterwarnings('ignore')
sys.path.insert(0, r'C:\Users\LAMB\Desktop\qcs_sage\sourceCode')
import pandas as pd
import QCS_DataHandler as dh
import QCS_Tests as QC

RAW = r'\\Abrolhos\Projetos\Seaguard & HOBO\CLAUDE\HOBO\raw'
SUSPECT = [
    'Hobo1_RRDM_RecEsqSul2_050320_210221.csv',
    'Hobo_RRDM_RecEsqSul2(B5)_050320_230221.csv',
    'HOBO#02_Ref.EsquecidoSul_RRDM_04022020_240221.csv',
    'HOBO_PAB3_160320_110521.csv',
    'HOBO_Parede_PAB3_160320_110521.csv',
    'HOBO1_PAB3_110521_220821.csv',
    'HOBO2_PAB3_110521_220821.csv',
    'HOBO1_PNorte_090521_210821.csv',
    'HOBO2_PNorte_090521_210821.csv',
    'HOBO1_RodoRaso_17022_200521.csv',
    'HOBO1_ESQRODO_B1_050424_160325.xlsx',
]
DATES = re.compile(r'(\d{6})[_\-](\d{6})')


def named_dates(name):
    m = DATES.search(name)
    if not m:
        return None
    out = []
    for g in m.groups():
        d, mo, y = int(g[:2]), int(g[2:4]), int(g[4:])
        try:
            out.append(pd.Timestamp(2000 + y, mo, d))
        except ValueError:
            return None
    return out


rows = []
for name in SUSPECT:
    hits = glob.glob(os.path.join(RAW, '**', name), recursive=True)
    if not hits:
        print('NAO ENCONTRADO: %s' % name)
        continue
    path = hits[0]
    df, _ = dh.read_hobo({'raw_data_path': os.path.dirname(path),
                          'file_name': os.path.basename(path),
                          'input_type': 'HOBO', 'correct_gmt3h': False}, {})
    t = pd.to_datetime(df['Datetime'])
    ph = QC.light_clock_phase(t, df['Luminosity (lux)'])
    nd = named_dates(name)
    dur_data = (t.max() - t.min()).days
    dur_name = (nd[1] - nd[0]).days if nd else None
    rows.append(dict(
        file=name, folder=os.path.relpath(os.path.dirname(path), RAW),
        data_from=t.min().strftime('%d/%m/%Y'), data_to=t.max().strftime('%d/%m/%Y'),
        data_days=dur_data,
        name_from=nd[0].strftime('%d/%m/%Y') if nd else '?',
        name_to=nd[1].strftime('%d/%m/%Y') if nd else '?',
        name_days=dur_name if dur_name is not None else '?',
        light_peak_h=round(ph['peak_hour'], 1) if ph['evaluable'] else None,
        offset_days=(nd[0] - t.min()).days if nd else None))

r = pd.DataFrame(rows)
pd.set_option('display.width', 200)
print(r[['file', 'data_from', 'data_to', 'data_days', 'name_from', 'name_to',
         'name_days', 'light_peak_h', 'offset_days']].to_string(index=False))
print('\nfull paths:')
for _i, x in r.iterrows():
    print('   %s\\%s' % (x['folder'], x['file']))
out = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'wrong_clocks.csv')
r.to_csv(out, index=False, encoding='utf-8-sig')
print('\ntable written to %s' % out)

# -*- coding: utf-8 -*-
r"""Removes the qualified products superseded by the replicate regrouping.

Each product is deleted in full - the CSV, its DataView panel folder, its
reports files and its provenance block - so nothing is left half-removed and
the index cannot pick up an orphan.

Every name is re-verified against the live index before anything is touched:
its replacement must exist, must be newer, and must list the same raw inputs.
A name that fails the check is skipped, not forced.

Usage:  drop_stale.py --dry-run   (lists)
        drop_stale.py             (deletes)
"""
import datetime
import glob
import os
import shutil
import sys
import warnings

warnings.filterwarnings('ignore')
import pandas as pd

ROOT = r'\\Abrolhos\Projetos\Seaguard & HOBO\CLAUDE'
INDEX = os.path.join(ROOT, 'qualified_index.csv')

# Two kinds of removal, with different evidence behind them.
#
# SUPERSEDED: an earlier run's product left behind when replicate GROUPING
# changed and the name changed with it. The replacement must be NEWER - that is
# what proves it replaced this one.
SUPERSEDED = {
    'TIM2_2019S2_HOBO_1_QLF': 'TIM2_2019S2_HOBO_QLF',
    'TIM2_2019S2_HOBO_2_QLF': 'TIM2_2019S2_HOBO_QLF',
    'PNOR_2024S1_HOBO_1_QLF': 'PNOR_2024S1_HOBO_QLF',
    'PNOR_2024S1_HOBO_2_QLF': 'PNOR_2024S1_HOBO_QLF',
    'PNOR_2026S1_HOBO_1_QLF': 'PNOR_2026S1_HOBO_QLF',
    'PNOR_2026S1_HOBO_2_QLF': 'PNOR_2026S1_HOBO_QLF',
    'PAB3_2022S2_HOBO_3_QLF': 'PAB3_2022S2_HOBO_2_QLF',
}

# REDUNDANT: two CURRENT products describing the same deployment under two
# labels, so the age test does not apply and the choice of survivor is an
# explicit decision, recorded here with its reason.
REDUNDANT = {
    # renamed when the reader learned to mark temperature-only loggers (v11.0)
    'PAB3_2019S2_HOBO_1_QLF': 'PAB3_2019S2_HOBO_1_TEMP_ONLY_QLF',
    'PLES_2024S1_HOBO_QLF': 'PLES_2024S1_HOBO_TEMP_ONLY_QLF',
    # the same raw file archived under two campaigns; the deployment ended
    # 05/04/2019, so the campaign that recovered it is RRDM 6a MAI 2019 and the
    # copy filed under RRDM 9a MAR 2020 (11 months later) is a re-file
    'ESQRODO_2020S1_HOBO_QLF': 'ESQRODO_2019S1_HOBO_QLF',
    # "o monitoramento de sitio e o controle fora da piscina sao a mesma coisa"
    # (archive owner, 2026-08-10): the _FORA pool control IS the site logger,
    # so the site product is the one that survives
    'PLES_FORA_2025S1_HOBO_QLF': 'PLES_2025S1_HOBO_QLF',
    'SGOM_FORA_2025S1_HOBO_QLF': 'SGOM_2025S1_HOBO_QLF',
}


def inputs_of(idx, name):
    r = idx[idx['product'] == name]
    if not len(r):
        return None
    return {x.strip() for x in str(r.iloc[0].get('inputs') or '').split('|') if x.strip()}


def main(dry):
    idx = pd.read_csv(INDEX, encoding='utf-8-sig')
    plan = ([(s, k, True) for s, k in SUPERSEDED.items()]
            + [(s, k, False) for s, k in REDUNDANT.items()])
    for stale, keeper, need_newer in sorted(plan):
        row = idx[idx['product'] == stale]
        krow = idx[idx['product'] == keeper]
        if not len(row):
            print('%-26s SKIP - not in the index' % stale)
            continue
        if not len(krow):
            print('%-26s SKIP - replacement %s missing' % (stale, keeper))
            continue
        csv = os.path.join(ROOT, str(row.iloc[0]['path']))
        kcsv = os.path.join(ROOT, str(krow.iloc[0]['path']))
        if not (os.path.exists(csv) and os.path.exists(kcsv)):
            print('%-26s SKIP - a file is missing on disk' % stale)
            continue
        if need_newer and os.path.getmtime(kcsv) <= os.path.getmtime(csv):
            print('%-26s SKIP - replacement is not newer' % stale)
            continue
        si, ki = inputs_of(idx, stale), inputs_of(idx, keeper)
        if not si or not si.issubset(ki):
            print('%-26s SKIP - inputs %s not covered by %s' % (stale, si, keeper))
            continue

        folder = os.path.dirname(csv)
        targets = [csv]
        dv = os.path.join(folder, 'DataView', stale)
        if os.path.isdir(dv):
            targets.append(dv)
        targets += sorted(glob.glob(os.path.join(folder, 'reports', stale + '__*')))
        mt = datetime.datetime.fromtimestamp(os.path.getmtime(csv)).strftime('%d/%m %H:%M')
        print('%-26s (%s) -> superseded by %s' % (stale, mt, keeper))
        for t in targets:
            print('      %s %s' % ('rmdir ' if os.path.isdir(t) else 'delete',
                                   os.path.relpath(t, ROOT)))
        if dry:
            continue
        for t in targets:
            shutil.rmtree(t) if os.path.isdir(t) else os.remove(t)
        # and its provenance block
        prov = os.path.join(folder, 'provenance.txt')
        if os.path.isfile(prov):
            blocks = [b for b in open(prov, encoding='utf-8').read().split('\n\n') if b.strip()]
            keep = [b for b in blocks if b.split('\n')[0].strip() != stale]
            with open(prov, 'w', encoding='utf-8') as f:
                f.write('\n\n'.join(keep) + '\n\n')
            print('      provenance block removed (%d -> %d)' % (len(blocks), len(keep)))
    print('\n(dry run)' if dry else '\ndone')


if __name__ == '__main__':
    main('--dry-run' in sys.argv)

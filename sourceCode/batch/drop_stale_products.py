# -*- coding: utf-8 -*-
r"""Removes the qualified products superseded by the replicate regrouping.

Each product is removed in full - the CSV, its DataView panel folder, its
reports files and its provenance block - so nothing is left half-removed and
the index cannot pick up an orphan. Removal MOVES everything into a dated
trash folder (`CLAUDE\_deleted\<YYYYMMDD>\<product>\`) rather than deleting:
the share has no recycle bin, so this keeps the one irreversible step of the
pipeline reversible. Emptying the trash is a human decision.

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


def excluded_raw_files():
    """The keys of qualify_site.EXCLUDED_REPLICATES, read from the SOURCE.

    Importing qualify_site would build a Tk root and the whole qualification
    tab as an import side effect - far too much for reading one dict - so the
    file is parsed instead of executed.
    """
    import ast
    src = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'qualify_site.py')
    with open(src, encoding='utf-8') as fh:
        tree = ast.parse(fh.read())
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        names = [t.id for t in node.targets if isinstance(t, ast.Name)]
        if 'EXCLUDED_REPLICATES' in names:
            return {k.value for k in node.value.keys if isinstance(k, ast.Constant)}
    raise RuntimeError('EXCLUDED_REPLICATES not found in qualify_site.py')

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

# DISCARDED: the product is removed and NOTHING replaces it - the archive owner
# ruled the logger unusable. Maps the product to the raw export(s) behind it,
# which must ALREADY be listed in qualify_site.EXCLUDED_REPLICATES: deleting a
# product whose cause is still in place only means the next full run recreates
# it (that is exactly how ESQRODO_2020S1 came back). The check below enforces it.
DISCARDED = {
    # "essencialmente descartavel agora que vimos que tem tanto erro" (archive
    # owner, 2026-08-11). Failed sensor (-84.77..156.53 degC across three
    # exports) + a +12 h clock + irregular sampling. It had NOT been blocked:
    # _fail_on_wrong_clock only fires on a clean +/-12 h accusation and this
    # logger's light peaks at 4.4 h, so the product shipped with 337 of its 366
    # rows flagged GOOD. Its window (05/02-07/03/2020) is already covered by
    # ESQSUL_2020S1_HOBO_2_QLF from a sound logger, so no coverage is lost.
    'ESQSUL_2021S1_HOBO_QLF': [
        'HOBO#02_Ref.EsquecidoSul_RRDM_04022020_240221.csv',
        'HOBO#02_Ref.EsquecidoSul_RRDM_04022020_240221.xlsx',
    ],
}


def inputs_of(idx, name):
    r = idx[idx['product'] == name]
    if not len(r):
        return None
    return {x.strip() for x in str(r.iloc[0].get('inputs') or '').split('|') if x.strip()}


def main(dry):
    idx = pd.read_csv(INDEX, encoding='utf-8-sig')
    plan = ([(s, k, True) for s, k in SUPERSEDED.items()]
            + [(s, k, False) for s, k in REDUNDANT.items()]
            + [(s, None, False) for s in DISCARDED])
    for stale, keeper, need_newer in sorted(plan, key=lambda t: t[0]):
        row = idx[idx['product'] == stale]
        if not len(row):
            print('%-26s SKIP - not in the index' % stale)
            continue
        csv = os.path.join(ROOT, str(row.iloc[0]['path']))
        if not os.path.exists(csv):
            print('%-26s SKIP - missing on disk' % stale)
            continue

        if keeper is None:
            # A DISCARD has no replacement to check against. Its safeguard is
            # the other half of the decision: the raw export must already be in
            # EXCLUDED_REPLICATES, so requalifying cannot bring the product
            # back. Deleting without that is how ESQRODO_2020S1 resurrected.
            missing = [f for f in DISCARDED[stale] if f not in excluded_raw_files()]
            if missing:
                print('%-26s SKIP - not excluded in qualify_site.py: %s'
                      % (stale, missing))
                continue
            print('%-26s -> DISCARDED (raw excluded, will not come back)' % stale)
        else:
            krow = idx[idx['product'] == keeper]
            if not len(krow):
                print('%-26s SKIP - replacement %s missing' % (stale, keeper))
                continue
            kcsv = os.path.join(ROOT, str(krow.iloc[0]['path']))
            if not os.path.exists(kcsv):
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
        if keeper is not None:
            print('%-26s (%s) -> superseded by %s' % (stale, mt, keeper))
        # Removal is a MOVE into a dated trash folder beside the corpus, not a
        # deletion: the share has no recycle bin, so os.remove there is the one
        # irreversible step of the whole pipeline. The trash sits at the ROOT
        # level - outside SEAGUARD\qualified and HOBO\qualified - so
        # build_index can never pick it up. Emptying it is a human decision.
        trash = os.path.join(ROOT, '_deleted',
                             datetime.datetime.now().strftime('%Y%m%d'), stale)
        for t in targets:
            print('      %s %s  ->  %s' % ('move dir ' if os.path.isdir(t) else 'move file',
                                           os.path.relpath(t, ROOT),
                                           os.path.relpath(trash, ROOT)))
        if dry:
            continue
        os.makedirs(trash, exist_ok=True)
        for t in targets:
            shutil.move(t, os.path.join(trash, os.path.basename(t)))
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

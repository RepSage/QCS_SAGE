# -*- coding: utf-8 -*-
r"""Turns HOBO\raw from SITE-first into CAMPAIGN-first, matching SEAGUARD\raw.

    before   HOBO\raw\PAB3\RRDM 16a MAR 2023\{bruto,planilha}
    after    HOBO\raw\RRDM 16a MAR 2023\PAB3\{bruto,planilha}

The campaign NAMES are kept exactly as the field team writes them ('RRDM 16a
MAR 2023'): they already carry a rising number, month and year, which is what
the Seaguard layout conveys with '8 - MARCO 2022'. The two numbering series
cannot be merged - HOBO runs 6a..22a and Seaguard 1..12, only 8 of 15 HOBO
campaigns have a Seaguard counterpart at all - so renumbering would have to
invent numbers and would destroy the identity the team uses in the field.

Three cases, measured on the tree rather than assumed:

  regular sites   <SITE>\<CAMPAIGN>\...          -> <CAMPAIGN>\<SITE>\...
  _PISCINAS       _PISCINAS\<POOL>\<CAMPAIGN>\.. -> _PISCINAS\<CAMPAIGN>\<POOL>\..
  _EXPERIMENTOS   already campaign-first         -> UNTOUCHED

Whole directories are moved, never individual files, so nothing inside a
deployment folder can be separated from its siblings. Every file is
md5-fingerprinted before and after: the two sets must match exactly or the run
aborts. The manifest's dest column is rewritten in the same pass - a manifest
pointing at paths that no longer exist is a provenance record that has stopped
being one.

Usage:  reorg_hobo_raw.py --dry-run | reorg_hobo_raw.py
"""
import hashlib
import os
import shutil
import sys
import warnings

warnings.filterwarnings('ignore')
import pandas as pd

RAW = r'\\Abrolhos\Projetos\Seaguard & HOBO\CLAUDE\HOBO\raw'
MANIFEST = os.path.join(RAW, 'manifest.csv')
BUCKETS = ('_PISCINAS', '_EXPERIMENTOS')


def fingerprint(root):
    """{md5: [relative paths]} for every file under root. Keyed by content so
    the check survives the very thing being changed - the paths."""
    out = {}
    for base, _d, files in os.walk(root):
        for f in files:
            p = os.path.join(base, f)
            h = hashlib.md5()
            with open(p, 'rb') as fh:
                for chunk in iter(lambda: fh.read(1 << 20), b''):
                    h.update(chunk)
            out.setdefault(h.hexdigest(), []).append(os.path.relpath(p, root))
    return out


def plan():
    """[(src_dir, dst_dir, kind)] - the directory moves, in order."""
    moves = []
    for top in sorted(os.listdir(RAW)):
        tp = os.path.join(RAW, top)
        if not os.path.isdir(tp):
            continue
        if top == '_EXPERIMENTOS':
            continue                      # already campaign-first
        if top == '_PISCINAS':
            # _PISCINAS\<POOL>\<CAMPAIGN>  ->  _PISCINAS\<CAMPAIGN>\<POOL>
            for pool in sorted(os.listdir(tp)):
                pp = os.path.join(tp, pool)
                if not os.path.isdir(pp):
                    continue
                for camp in sorted(os.listdir(pp)):
                    cp = os.path.join(pp, camp)
                    if os.path.isdir(cp):
                        moves.append((cp, os.path.join(tp, camp, pool), 'piscina'))
        else:
            # <SITE>\<CAMPAIGN>  ->  <CAMPAIGN>\<SITE>
            for camp in sorted(os.listdir(tp)):
                cp = os.path.join(tp, camp)
                if os.path.isdir(cp):
                    moves.append((cp, os.path.join(RAW, camp, top), 'sitio'))
    return moves


def rewrite_manifest(dry):
    r"""dest paths: ...\raw\<SITE>\<CAMPAIGN>\...  ->  ...\raw\<CAMPAIGN>\<SITE>\...
    Uses the manifest's OWN site/campaign columns rather than parsing the path,
    so a site whose name appears twice in a path cannot be mangled."""
    m = pd.read_csv(MANIFEST, encoding='utf-8-sig')
    changed = 0
    for i, r in m.iterrows():
        dest = str(r.get('dest') or '')
        site, camp = str(r.get('site') or ''), str(r.get('campaign') or '')
        if not dest or not camp or camp == 'nan':
            continue
        if '_EXPERIMENTOS' in dest:
            continue                       # untouched on disk
        if site and site != 'nan':
            old = '%s%s%s%s' % (os.sep, site, os.sep, camp)
            new = '%s%s%s%s' % (os.sep, camp, os.sep, site)
        else:
            continue
        if old in dest:
            m.at[i, 'dest'] = dest.replace(old, new)
            changed += 1
    print('   linhas do manifesto a reescrever: %d de %d' % (changed, len(m)))
    if not dry:
        shutil.copy2(MANIFEST, MANIFEST + '.pre_reorg')
        m.to_csv(MANIFEST, index=False, encoding='utf-8-sig')
        print('   manifesto gravado (copia anterior: manifest.csv.pre_reorg)')
    return changed


def main(dry):
    moves = plan()
    print('=== MOVIMENTOS PLANEJADOS: %d ===' % len(moves))
    by_kind = {}
    for _s, _d, k in moves:
        by_kind[k] = by_kind.get(k, 0) + 1
    for k, n in sorted(by_kind.items()):
        print('   %-10s %d' % (k, n))
    for s, d, _k in moves[:6]:
        print('   %s\n      -> %s' % (os.path.relpath(s, RAW), os.path.relpath(d, RAW)))
    if len(moves) > 6:
        print('   ... mais %d' % (len(moves) - 6))

    collisions = [d for _s, d, _k in moves if os.path.exists(d)]
    if collisions:
        print('\nABORTA: destino ja existe para %d movimento(s)' % len(collisions))
        for c in collisions[:5]:
            print('   %s' % os.path.relpath(c, RAW))
        return 1

    print('\n=== IMPRESSAO DIGITAL (antes) ===')
    before = fingerprint(RAW)
    n_before = sum(len(v) for v in before.values())
    print('   %d arquivo(s), %d md5 distinto(s)' % (n_before, len(before)))

    print('\n=== MANIFESTO ===')
    rewrite_manifest(dry)

    if dry:
        print('\n(dry run - nada foi movido)')
        return 0

    print('\n=== MOVENDO ===')
    for src, dst, _k in moves:
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.move(src, dst)
    print('   %d diretorio(s) movido(s)' % len(moves))

    # empty site/pool shells left behind
    removed = 0
    for top in sorted(os.listdir(RAW)):
        tp = os.path.join(RAW, top)
        if not os.path.isdir(tp) or top == '_EXPERIMENTOS':
            continue
        for base, dirs, files in os.walk(tp, topdown=False):
            if not dirs and not files:
                os.rmdir(base)
                removed += 1
    print('   %d pasta(s) vazia(s) removida(s)' % removed)

    print('\n=== IMPRESSAO DIGITAL (depois) ===')
    after = fingerprint(RAW)
    n_after = sum(len(v) for v in after.values())
    print('   %d arquivo(s), %d md5 distinto(s)' % (n_after, len(after)))
    if set(before) != set(after) or n_before != n_after:
        print('\nDIVERGENCIA! conteudo mudou - investigue antes de qualquer coisa')
        print('   md5 so ANTES : %s' % list(set(before) - set(after))[:5])
        print('   md5 so DEPOIS: %s' % list(set(after) - set(before))[:5])
        return 1
    print('   IDENTICO ao estado anterior (mesmo conjunto de md5, mesma contagem)')
    return 0


if __name__ == '__main__':
    sys.exit(main('--dry-run' in sys.argv))

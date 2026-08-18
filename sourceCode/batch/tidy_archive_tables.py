# -*- coding: utf-8 -*-
r"""Collects the archive's one-off and historical tables into CLAUDE\_registros\,
leaving in place only the files the pipeline actually reads.

WHAT STAYS, and why it must:
  - HOBO\raw\manifest.csv and SEAGUARD\raw\manifest.csv - the archive's
    PROVENANCE: origin, size, md5 and the repair history (clock_corrected_-12h,
    collapsed_clock_reconstructed, the dated notes). correct_clock.py,
    repair_collapsed_clock.py and repair_unset_clock.py WRITE to them. Not
    regenerable: delete them and the record of what was done to the raw archive
    is gone. They are never moved by this script.
  - qualified_index.csv - the corpus catalog, read by build_index,
    build_data_package, drop_stale_products and sweep_value_integrity. It IS
    regenerable, but four scripts expect it at the root.

WHAT MOVES: analysis outputs and the paperwork of past reorganizations. Nothing
reads them; they are kept for the record, not for the pipeline.

WHAT IS DELETED: manifest.csv.bak only - a July snapshot superseded by the live
manifest, which has since absorbed every repair of the August rounds.

Usage:  tidy_archive_tables.py --dry-run | tidy_archive_tables.py
"""
import hashlib
import os
import shutil
import sys

ROOT = r'\\Abrolhos\Projetos\Seaguard & HOBO\CLAUDE'
DEST = os.path.join(ROOT, '_registros')

# relative path -> why it is being filed away
MOVE = {
    'replicate_disagreement_sweep.csv':
        'sweep of replicate disagreement across the corpus (2026-07); the '
        'referee that grew out of it lives in qualify_site.py',
    os.path.join('HOBO', 'replicate_referee_verdicts.csv'):
        'per-deployment verdicts of the replicate referee (2026-07); the '
        'decisions that were acted on are in EXCLUDED_REPLICATES',
    os.path.join('HOBO', 'raw', 'a2_manifest.csv'):
        'partial manifest of an early staging pass (2026-07), superseded by '
        'manifest.csv',
    os.path.join('SEAGUARD', 'raw', 'a2_manifest.csv'):
        'partial manifest of an early staging pass (2026-07), superseded by '
        'manifest.csv',
    os.path.join('SEAGUARD', 'raw', 'reorg_manifest.csv'):
        'record of the Seaguard raw reorganization (2026-07): which file went '
        'where when the campaign/site layout was adopted',
    os.path.join('SEAGUARD', 'raw', 'survey_master (pre-reorg paths).csv'):
        'survey of the Seaguard archive BEFORE that reorganization - the only '
        'record of the original paths',
}
DELETE = {
    os.path.join('HOBO', 'raw', 'manifest.csv.bak'):
        'July snapshot of the HOBO manifest, superseded: the live manifest has '
        'since recorded every repair of the August rounds',
}
KEEP = ['qualified_index.csv',
        os.path.join('HOBO', 'raw', 'manifest.csv'),
        os.path.join('SEAGUARD', 'raw', 'manifest.csv')]

README = """REGISTROS - tabelas historicas do arquivo

Esta pasta guarda saidas de analises pontuais e a papelada de reorganizacoes
passadas. NADA aqui e lido pelo pipeline: esta aqui para o registro, nao para
o funcionamento. Mover ou apagar arquivos desta pasta nao quebra nenhum
script.

O QUE NAO ESTA AQUI, e por que:

  HOBO\\raw\\manifest.csv
  SEAGUARD\\raw\\manifest.csv
      A PROVENIENCIA do arquivo bruto: origem, tamanho, md5 e o historico de
      reparos (relogio colapsado, AM/PM trocado, epoch de fabrica), cada um
      com sua nota datada. Os scripts de reparo ESCREVEM neles. Nao sao
      regeneraveis - apagar significa perder o registro do que foi feito no
      arquivo. Ficam onde estao.

  qualified_index.csv
      O catalogo do corpus. E regeneravel (batch\\build_index.py), mas quatro
      scripts o esperam na raiz.

CONTEUDO
"""


def md5(path):
    h = hashlib.md5()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def main(dry):
    print('=== FICAM onde estao (o pipeline os le/escreve) ===')
    for rel in KEEP:
        p = os.path.join(ROOT, rel)
        print('   %-52s %s' % (rel, 'OK' if os.path.isfile(p) else 'AUSENTE!'))

    print('\n=== MOVEM para _registros\\ ===')
    moved = []
    for rel, why in sorted(MOVE.items()):
        src = os.path.join(ROOT, rel)
        if not os.path.isfile(src):
            print('   %-52s (nao existe - ignorado)' % rel)
            continue
        print('   %-52s %.1f KB' % (rel, os.path.getsize(src) / 1024))
        if dry:
            continue
        os.makedirs(DEST, exist_ok=True)
        # flatten the name so two a2_manifest.csv do not collide
        flat = rel.replace(os.sep, '__')
        dst = os.path.join(DEST, flat)
        before = md5(src)
        shutil.move(src, dst)
        if md5(dst) != before:
            raise SystemExit('MD5 mudou ao mover %s - PARE' % rel)
        moved.append((flat, rel, why))

    print('\n=== APAGADOS ===')
    for rel, why in sorted(DELETE.items()):
        p = os.path.join(ROOT, rel)
        if not os.path.isfile(p):
            print('   %-52s (nao existe)' % rel)
            continue
        print('   %-52s %.1f KB  - %s' % (rel, os.path.getsize(p) / 1024, why[:60]))
        if not dry:
            os.remove(p)

    if not dry and moved:
        with open(os.path.join(DEST, 'LEIA-ME.txt'), 'w', encoding='utf-8') as f:
            f.write(README)
            for flat, rel, why in moved:
                f.write('\n  %s\n      (era %s)\n      %s\n' % (flat, rel, why))
        print('\nLEIA-ME.txt escrito em _registros\\')
    print('\n(dry run)' if dry else '\nconcluido')


if __name__ == '__main__':
    main('--dry-run' in sys.argv)

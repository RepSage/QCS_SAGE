# -*- coding: utf-8 -*-
r"""Re-syncs manifest rows whose md5 no longer matches the file on disk.

WHY THIS EXISTS. The manifest is the archive's integrity record: a file whose
md5 does not match its row reads as CORRUPTION. Two of the three in-place
repair scripts update the manifest when they rewrite a raw file
(correct_clock.py, repair_collapsed_clock.py); repair_unset_clock.py never did,
and files re-exported by hand were never re-recorded either. The result was 12
rows still labeled 'copied_verified' with the pre-repair md5 AND the
pre-repair size - the record silently disagreeing with the archive since
August 2026, found only when the reorganization forced a full re-check.

This script does not repair data. It reconciles the RECORD with an archive
already known-good, and says so in the row: the note states that the content
change came from a documented in-place repair, and that the row - not the
file - is what was late.

Run it after any operation that rewrites raw files without recording itself.

Usage:  refresh_manifest_md5.py --dry-run | refresh_manifest_md5.py
"""
import csv
import datetime
import hashlib
import os
import shutil
import sys

RAW = r'\\Abrolhos\Projetos\Seaguard & HOBO\CLAUDE\HOBO\raw'
MANIFEST = os.path.join(RAW, 'manifest.csv')
# the manifest's dest carries a legacy prefix from before the HOBO/SEAGUARD
# split; map it onto the real tree rather than rewriting 407 rows for cosmetics
OLD_PREFIX = r'\\Abrolhos\Projetos\Seaguard & HOBO\CLAUDE\raw'
TODAY = datetime.date.today().isoformat()


def md5(path):
    h = hashlib.md5()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def main(dry):
    with open(MANIFEST, newline='', encoding='utf-8-sig') as f:
        rows = list(csv.DictReader(f))
        fields = list(rows[0].keys())

    stale, missing = [], []
    for row in rows:
        real = str(row.get('dest') or '').replace(OLD_PREFIX, RAW)
        if not real:
            continue
        if not os.path.isfile(real):
            missing.append(row)
            continue
        rec = str(row.get('md5') or '')
        if rec and rec != md5(real):
            stale.append((row, real))

    print('linhas: %d | md5 desatualizado: %d | arquivo ausente: %d'
          % (len(rows), len(stale), len(missing)))
    for row in missing[:5]:
        print('   AUSENTE: %s' % os.path.basename(str(row.get('dest'))))

    print('\n%-56s %10s -> %-10s' % ('arquivo', 'tam. antigo', 'tam. novo'))
    for row, real in stale:
        print('%-56s %10s -> %-10d' % (os.path.basename(real)[:56],
                                       row.get('size_bytes'), os.path.getsize(real)))
        if dry:
            continue
        row['md5'] = md5(real)
        row['size_bytes'] = str(os.path.getsize(real))
        row['status'] = 'repaired_in_place'
        prev = str(row.get('note') or '').strip()
        row['note'] = (
            ('%s | ' % prev if prev and prev != 'nan' else '')
            + 'content changed by a documented in-place raw repair (see '
              'CORPUS_LOG.md); the manifest row was not updated at the time and '
              'was refreshed on %s - the FILE was never in doubt, the record was'
            % TODAY)

    if dry:
        print('\n(dry run)')
        return 0
    if stale:
        shutil.copy2(MANIFEST, MANIFEST + '.pre_md5refresh')
        with open(MANIFEST, 'w', newline='', encoding='utf-8-sig') as f:
            w = csv.DictWriter(f, fieldnames=fields)
            w.writeheader()
            w.writerows(rows)
        print('\n%d linha(s) atualizada(s) (copia anterior: manifest.csv.pre_md5refresh)'
              % len(stale))
    else:
        print('\nnada a fazer - manifesto e arquivo ja concordam')
    return 0


if __name__ == '__main__':
    sys.exit(main('--dry-run' in sys.argv))

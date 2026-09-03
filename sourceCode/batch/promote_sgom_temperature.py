"""Promote the verified SGOM temperature decision and refresh its curated view.

Dependencies: QCS Anaconda base (Python 3.13, pandas 2.2, numpy 2.1,
openpyxl 3.1, matplotlib). Raw inputs are never modified. The operation is
restricted to SGOM_2026S1, whose changed temperatures belong to civil 2025.
"""
import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path
import shutil
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import QCS_Curated as curated
import QCS_DataView as view
from QCS_Replicates import copy_report_file
import build_index
import sweep_value_integrity as integrity

PRODUCT = 'SGOM_2026S1_HOBO_QLF'
RELATIVE = Path('HOBO/qualified/2026S1/SGOM')
TEMP = 'Temperature (degC)'
SPREAD = 'Temperature spread (degC)'


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def tree_hashes(folder):
    return {str(p.relative_to(folder)): digest(p) for p in folder.rglob('*') if p.is_file()}


def inventory(frame):
    return {'rows': len(frame), 'columns': len(frame.columns),
            'dtypes': frame.dtypes.astype(str).to_dict(),
            'missing': frame.isna().sum().astype(int).to_dict(),
            'duplicate_timestamps': int(frame.Datetime.duplicated().sum()),
            'temperature_min_degC': frame[TEMP].min(), 'temperature_max_degC': frame[TEMP].max()}


def changed(a, b):
    return ~np.isclose(pd.to_numeric(a), pd.to_numeric(b), equal_nan=True, rtol=0, atol=1e-9)


def draw_comparison(before, after, folder):
    before = before[pd.to_datetime(before.Datetime).dt.year.eq(2025)].copy()
    after = after[pd.to_datetime(after.Datetime).dt.year.eq(2025)].copy()
    assert len(before) == len(after)
    before['Datetime'] = pd.to_datetime(before.Datetime)
    after['Datetime'] = pd.to_datetime(after.Datetime)
    after.to_csv(folder / 'SGOM_2025_corrected.csv', index=False)
    cparam, bparam = view.getParamColors()
    fig, axes = plt.subplots(2, 1, figsize=(12, 7), sharex=True, sharey=True,
                             layout='constrained')
    for ax, frame, title in zip(axes, [before, after],
                                ['Before correction', 'Corrected: HOBO2 temperature retained'], strict=True):
        for _, group in frame.groupby('Source file', sort=False):
            group = group.sort_values('Datetime')
            # No line across a deployment gap or missing interval.
            gaps = group.Datetime.diff() > 3 * group.Datetime.diff().median()
            groups = gaps.cumsum()
            for _, segment in group.groupby(groups):
                ax.plot(segment.Datetime, segment[TEMP], color=bparam[TEMP], linewidth=0.8)
                spread = segment[SPREAD].where(segment[SPREAD].gt(0)) / 2
                ax.fill_between(segment.Datetime, segment[TEMP] - spread,
                                segment[TEMP] + spread, color=cparam[TEMP], alpha=0.28,
                                linewidth=0)
        ax.set_title(title, loc='left', fontsize=12)
        ax.set_ylabel('Temperature (°C)')
        ax.grid(alpha=0.2)
        ax.spines[['top', 'right']].set_visible(False)
    axes[-1].set_xlim(pd.Timestamp('2025-01-01'), pd.Timestamp('2026-01-01'))
    axes[-1].xaxis.set_major_locator(mdates.MonthLocator())
    axes[-1].xaxis.set_major_formatter(mdates.DateFormatter('%b'))
    axes[-1].set_xlabel('2025 — local time (GMT−03)')
    fig.suptitle('SGOM | 2025 temperature correction', fontsize=16, fontweight='bold')
    fig.supxlabel('%s timestamps preserved • shaded band: mean ± half the replicate range\n'
                  '481 corrected temperatures • light unchanged • gaps remain unfilled'
                  % format(len(after), ','), fontsize=10)
    fig.savefig(folder / 'SGOM_2025_before_after.png', dpi=160)
    fig.savefig(folder / 'SGOM_2025_before_after.svg')
    plt.close(fig)
    return len(after)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive', required=True, type=Path)
    parser.add_argument('--candidate', required=True, type=Path)
    parser.add_argument('--workbook', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    archive, candidate = args.archive.resolve(), args.candidate.resolve()
    workbook, output = args.workbook.resolve(), args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    active_site, staged_site = archive / RELATIVE, candidate / RELATIVE
    active_csv, staged_csv = active_site / (PRODUCT + '.csv'), staged_site / (PRODUCT + '.csv')
    if archive not in active_site.parents or candidate not in staged_site.parents or archive == candidate:
        raise ValueError('Invalid promotion roots')
    assert sorted(p.name for p in active_site.glob('*_QLF.csv')) == [PRODUCT + '.csv']
    check = json.loads((candidate / 'validation_summary.json').read_text(encoding='utf-8'))
    assert check['candidate_products'] == 1 and check['failed_runs'] == []
    before_record = json.loads((candidate / 'baseline_inventory.json').read_text(encoding='utf-8'))[active_csv.name]
    assert digest(active_csv) == before_record['sha256'], 'Active product changed since staging'
    before, after = pd.read_csv(active_csv), pd.read_csv(staged_csv)
    assert before.Datetime.equals(after.Datetime) and len(after) == 2254
    changes = changed(before[TEMP], after[TEMP])
    assert int(changes.sum()) == 481
    assert pd.to_datetime(after.loc[changes, 'Datetime']).dt.year.eq(2025).all()
    assert not changed(before['Luminosity (lux)'], after['Luminosity (lux)']).any()
    assert before.Flag_lux.equals(after.Flag_lux)
    assert after[TEMP].notna().all() and after[SPREAD].isna().all()
    sheets = pd.read_excel(workbook, sheet_name=None)
    assert set(sheets) == {'HOBO', 'Included products', 'Read me'}, 'Unexpected workbook content'
    metadata = dict(zip(sheets['Read me'].Field, sheets['Read me'].Value, strict=True))
    assert metadata['Sites'] == 'SGOM' and metadata['Instruments'] == 'HOBO'
    years = [int(x.strip()) for x in metadata['Calendar years'].split(',')]
    assert years == [2025, 2026], 'Curated selection changed; inspect it before promotion'
    old_book = sheets['HOBO']
    assert len(old_book) == 4657
    book_sha = digest(workbook)
    raw = archive / 'HOBO/raw/2026S1/SGOM/planilha'
    raw_hashes = {str(p): digest(p) for p in raw.glob('*') if p.is_file()}
    qualified_hashes = {str(p): digest(p) for p in (archive / 'HOBO/qualified').glob('*/*/*_QLF.csv')}
    report = {'before': inventory(before), 'after': inventory(after),
              'workbook_before': inventory(old_book), 'changed_temperatures': int(changes.sum()),
              'changed_flags': int(before.Flag_T.ne(after.Flag_T).sum()),
              'max_temperature_change_degC': float((before[TEMP] - after[TEMP]).abs().max()),
              'changed_temperature_years': [2025], 'light_changed': False,
              'applied': False}
    (output / 'inspection.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps({k: report[k] for k in ['changed_temperatures', 'changed_flags',
                                            'max_temperature_change_degC', 'changed_temperature_years']}), flush=True)
    if not args.apply:
        return

    # Verified backups precede every change to the active product, index and workbook.
    backup = archive / '_deleted' / ('sgom_temperature_' + datetime.now().strftime('%Y%m%dT%H%M%S'))
    backup.mkdir(parents=True)
    original = backup / 'original' / RELATIVE
    shutil.copytree(active_site, original, copy_function=copy_report_file)
    assert tree_hashes(original) == tree_hashes(active_site)
    index = archive / 'qualified_index.csv'
    copy_report_file(index, backup / 'qualified_index.before.csv')
    copy_report_file(workbook, backup / 'QCS_curated_database.before.xlsx')
    assert digest(index) == digest(backup / 'qualified_index.before.csv')
    assert book_sha == digest(backup / 'QCS_curated_database.before.xlsx')
    (output / 'backup.json').write_text(json.dumps({'backup': str(backup),
                                                  'verified': True}, indent=2), encoding='utf-8')

    prepared = backup / 'prepared' / 'SGOM'
    shutil.copytree(staged_site, prepared, copy_function=copy_report_file)
    # Preserve the field-campaign label and original input/clock provenance.
    provenance = (active_site / 'provenance.txt').read_text(encoding='utf-8').strip()
    provenance += ('\n    qualified_version : v14.0\n    qualified_on : ' + datetime.now().isoformat(timespec='seconds') +
                   '\n    temperature_decision : sgom-2026s1-temperature; HOBO1 excluded for temperature only; '
                   'HOBO2 retained; light combined independently\n    previous_product_backup : ' + str(original) + '\n\n')
    (prepared / 'provenance.txt').write_text(provenance, encoding='utf-8')
    assert digest(active_csv) == before_record['sha256']
    displaced = backup / 'displaced_SGOM'
    assert archive in active_site.parents and backup in displaced.parents and backup in prepared.parents
    active_site.rename(displaced)
    try:
        prepared.rename(active_site)
    except OSError:
        displaced.rename(active_site)
        raise
    assert digest(active_csv) == digest(staged_csv)
    report['applied'] = True
    report['backup'] = str(backup)
    (output / 'promotion.json').write_text(json.dumps(report, indent=2), encoding='utf-8')

    # Refresh the canonical index and run the mandatory full value-integrity sweep.
    build_index.ROOT = str(archive)
    rebuilt = build_index.main(str(output / 'qualified_index.after.csv'))
    old_index = pd.read_csv(backup / 'qualified_index.before.csv')
    assert set(rebuilt['product']) == set(old_index['product'])
    assert int(rebuilt.n_rows.sum()) == int(old_index.n_rows.sum())
    copy_report_file(output / 'qualified_index.after.csv', index.with_suffix('.pending.csv'))
    index.with_suffix('.pending.csv').replace(index)
    integrity.ROOT = str(archive)
    assert integrity.main() == 0, 'Value-integrity sweep failed'

    # Rebuild the workbook through the same engine as the Curated Database tab.
    catalog, catalog_messages = curated.discover_qualified_corpus(archive)
    tables, included, summary, messages = curated.build_curated_tables(catalog, ['HOBO'], ['SGOM'], years)
    current = tables['HOBO']
    assert len(current) == len(old_book) == 4657
    assert pd.to_datetime(old_book.Datetime).equals(pd.to_datetime(current.Datetime))
    assert old_book['Source file'].equals(current['Source file'])
    assert int(changed(old_book[TEMP], current[TEMP]).sum()) == 481
    assert not changed(old_book['Luminosity (lux)'], current['Luminosity (lux)']).any()
    assert digest(workbook) == book_sha, 'Workbook changed during the operation'
    curated.write_curated_workbook(workbook, archive, tables, included, summary)
    saved = pd.read_excel(workbook, sheet_name='HOBO')
    assert not changed(saved[TEMP], current[TEMP]).any()
    assert int(saved.Flag_T.eq(3).sum()) == int(current.Flag_T.eq(3).sum())
    (output / 'curated_build.log').write_text('\n'.join(catalog_messages + messages), encoding='utf-8')
    report['calendar_2025_rows'] = draw_comparison(old_book, saved, output)
    report['workbook_after_rows'] = len(saved)
    report['index_products'] = len(rebuilt)
    report['other_hobo_products_unchanged'] = all(digest(p) == sha for p, sha in qualified_hashes.items() if Path(p) != active_csv)
    report['raw_unchanged'] = all(digest(p) == sha for p, sha in raw_hashes.items())
    report['other_hobo_products_checked'] = len(qualified_hashes) - 1
    assert report['other_hobo_products_unchanged'] and report['raw_unchanged']
    (output / 'promotion.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report, indent=2), flush=True)


if __name__ == '__main__':
    main()

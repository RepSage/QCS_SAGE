"""Promote a validated HOBO replay, retaining explicitly named failed products.

Dependencies: Python 3.13, pandas 2.2, numpy 2.1, openpyxl 3.1 and QCS.
Raw data are read-only. Backups and a journal precede active-folder replacement.
The canonical index, integrity sweep and curated engine complete the operation.
"""
import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path
import shutil
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import QCS_Curated as curated
from QCS_Replicates import copy_report_file
import build_index
import sweep_value_integrity as integrity

TEMP = 'Temperature (degC)'


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def tree_hashes(folder):
    return {str(p.relative_to(folder)): digest(p) for p in folder.rglob('*') if p.is_file()}


def save_json(path, value):
    path.write_text(json.dumps(value, indent=2, default=str), encoding='utf-8')


def equal_values(left, right):
    return np.isclose(pd.to_numeric(left), pd.to_numeric(right), equal_nan=True,
                      rtol=0, atol=1e-9)


def updated_provenance(original, candidate, backup):
    """Retain original campaign/clock evidence; append the requalification record."""
    staged = build_index.parse_provenance(candidate / 'provenance.txt')
    result = []
    for block in (original / 'provenance.txt').read_text(encoding='utf-8').split('\n\n'):
        if not block.strip():
            continue
        name = block.splitlines()[0].strip()
        assert name in staged, 'Unexpected original provenance block: ' + name
        old = build_index.parse_provenance(original / 'provenance.txt')[name]
        assert old.get('inputs') == staged[name].get('inputs'), name + ': inputs changed'
        block += ('\n    requalified_version : v14.0\n    requalified_on : '
                  + datetime.now().isoformat(timespec='seconds')
                  + '\n    replicate_policy : versioned decisions; unresolved spread >0.5 degC'
                  ' for >=24 hours and >=3 eligible pairs withheld; light independent'
                  + '\n    requalification_backup : ' + str(backup))
        result.append(block)
    assert {b.splitlines()[0].strip() for b in result} == set(staged)
    return '\n\n'.join(result) + '\n\n'


def inspect_candidate(archive, candidate, retained):
    summary = json.loads((candidate / 'validation_summary.json').read_text())
    assert summary['source_unchanged'] and summary['settings_unchanged']
    for key in ['changed_raw', 'changed_active', 'scale_defects', 'unflagged_impossible']:
        assert not summary[key], (key, summary[key])
    assert set(summary['missing_products']) == retained, summary['missing_products']
    baseline = {}
    for path in (candidate / 'site_runs').glob('*/baseline_inventory.json'):
        baseline.update(json.loads(path.read_text(encoding='utf-8')))
    active = {p.name: p for p in (archive / 'HOBO/qualified').glob('*/*/*_QLF.csv')}
    products = sorted((candidate / 'HOBO/qualified').glob('*/*/*_QLF.csv'))
    assert set(active) == set(baseline)
    assert {p.name for p in products} == set(active) - retained
    assert all(digest(active[name]) == record['sha256'] for name, record in baseline.items())
    changes, combined_count = [], 0
    for product in products:
        old, new = pd.read_csv(active[product.name]), pd.read_csv(product)
        assert old.Datetime.equals(new.Datetime), product.name + ': timestamp grid changed'
        assert old.Site.equals(new.Site) and new['QCS version'].eq('v14.0').all()
        for column in ['Luminosity (lux)', 'Flag_lux', 'Flag_T']:
            assert equal_values(old[column], new[column]).all(), (product.name, column)
        change = ~equal_values(old[TEMP], new[TEMP])
        # SGOM was already corrected: this round only withholds unresolved suspect means.
        assert new.loc[change, TEMP].isna().all() and new.loc[change, 'Flag_T'].eq(3).all()
        report_dir = product.parent / 'reports'
        report = pd.read_excel(report_dir / (product.stem + '__QCS_report.xlsx')).iloc[0]
        if report.get('scope') == 'combined':
            combined_count += 1
            assert int(report.Total) == len(new)
            assert int(report.T_suspect) == int(new.Flag_T.eq(3).sum())
            assert int(report.T_withheld) == int((new[TEMP].isna() & new.Flag_T.eq(3)).sum())
            samples = pd.read_csv(report_dir / (product.stem + '__QCS_replicate_samples.csv'))
            assert len(samples) == len(new)
            assert new.loc[samples.eligible_contributors.eq(1), 'Temperature spread (degC)'].isna().all()
            assert new.Flag.isna().all()
        changes.append({'product': product.name, 'rows': len(new),
                        'changed_temperature': int(change.sum()),
                        'temperature_missing': int(new[TEMP].isna().sum()),
                        'temperature_withheld': int((new[TEMP].isna() & new.Flag_T.eq(3)).sum())})
    # Complete site folders may be replaced; a mixed failed/successful folder needs review.
    for site in {p.parent for p in products}:
        original = archive / site.relative_to(candidate)
        assert {p.name for p in original.glob('*_QLF.csv')} == {p.name for p in site.glob('*_QLF.csv')}
    return products, pd.DataFrame(changes), combined_count, baseline, summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive', type=Path, required=True)
    parser.add_argument('--candidate', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--workbook', type=Path, required=True)
    parser.add_argument('--retain-product', action='append', default=[])
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    archive, candidate, output = args.archive.resolve(), args.candidate.resolve(), args.output.resolve()
    workbook = args.workbook.resolve()
    workbook_before = digest(workbook) if workbook.exists() else None
    assert archive not in candidate.parents and candidate not in archive.parents and archive != candidate
    assert archive not in output.parents and archive not in workbook.parents
    output.mkdir(parents=True, exist_ok=True)
    products, changes, checked, baseline, summary = inspect_candidate(archive, candidate, set(args.retain_product))
    changes.to_csv(output / 'product_changes.csv', index=False)
    plan = {'candidate_products': len(products), 'candidate_rows': int(changes.rows.sum()),
            'retained_products': args.retain_product, 'failed_runs': summary['failed_runs'],
            'changed_products': int(changes.changed_temperature.gt(0).sum()),
            'changed_temperatures': int(changes.changed_temperature.sum()),
            'combined_reports_checked': checked, 'applied': False}
    save_json(output / 'promotion.json', plan)
    print(json.dumps(plan, indent=2), flush=True)
    if not args.apply:
        return

    stamp = datetime.now().strftime('%Y%m%dT%H%M%S')
    backup = archive / '_deleted' / ('hobo_v14_' + stamp)
    backup.mkdir(parents=True)
    plan['backup'] = str(backup)
    index = archive / 'qualified_index.csv'
    copy_report_file(index, backup / 'qualified_index.before.csv')
    assert digest(index) == digest(backup / 'qualified_index.before.csv')
    if workbook.exists():
        copy_report_file(workbook, backup / workbook.name)
        assert digest(workbook) == digest(backup / workbook.name)
    all_products = {str(p.relative_to(archive)): digest(p)
                    for p in archive.glob('*/qualified/**/*_QLF.csv')}
    raw_hashes = {str(p): digest(p) for p in (archive / 'HOBO/raw').rglob('*') if p.is_file()}
    save_json(output / 'before_hashes.json', {'qualified': all_products, 'raw': raw_hashes})
    sites = sorted({p.parent.relative_to(candidate) for p in products})
    prepared_hashes = {}
    for relative in sites:
        original, source = archive / relative, candidate / relative
        saved, prepared = backup / 'original' / relative, backup / 'prepared' / relative
        shutil.copytree(original, saved, copy_function=copy_report_file)
        assert tree_hashes(original) == tree_hashes(saved)
        shutil.copytree(source, prepared, copy_function=copy_report_file)
        assert tree_hashes(source) == tree_hashes(prepared)
        (prepared / 'provenance.txt').write_text(updated_provenance(original, source, saved), encoding='utf-8')
        prepared_hashes[str(relative)] = tree_hashes(prepared)
    plan['backups_verified'] = True
    save_json(output / 'promotion.json', plan)
    print('Verified backups and prepared replacements for %d site folders.' % len(sites), flush=True)
    moved = []
    try:
        for relative in sites:
            active, prepared = archive / relative, backup / 'prepared' / relative
            displaced = backup / 'displaced' / relative
            assert archive in active.parents and backup in displaced.parents and backup in prepared.parents
            # Do not replace a folder edited by the operator while preparation ran.
            assert tree_hashes(active) == tree_hashes(backup / 'original' / relative)
            displaced.parent.mkdir(parents=True, exist_ok=True)
            active.rename(displaced)
            try:
                prepared.rename(active)
            except OSError:
                displaced.rename(active)
                raise
            moved.append(relative)
            assert tree_hashes(active) == prepared_hashes[str(relative)]
            save_json(output / 'journal.json', {'replaced': [str(p) for p in moved]})
    except Exception:
        for relative in reversed(moved):
            active = archive / relative
            quarantine = backup / 'rollback_candidate' / relative
            quarantine.parent.mkdir(parents=True, exist_ok=True)
            assert archive in active.parents and backup in quarantine.parents
            active.rename(quarantine)
            (backup / 'displaced' / relative).rename(active)
        raise
    plan['applied'] = True
    save_json(output / 'promotion.json', plan)
    print('Active HOBO replacement complete; rebuilding index and checking integrity.', flush=True)
    build_index.ROOT = str(archive)
    rebuilt = build_index.main(str(output / 'qualified_index.after.csv'))
    old_index = pd.read_csv(backup / 'qualified_index.before.csv')
    assert set(rebuilt['product']) == set(old_index['product'])
    assert int(rebuilt.n_rows.sum()) == int(old_index.n_rows.sum())
    copy_report_file(output / 'qualified_index.after.csv', index.with_suffix('.pending.csv'))
    index.with_suffix('.pending.csv').replace(index)
    integrity.ROOT = str(archive)
    assert integrity.main() == 0
    changed_paths = {str(p.relative_to(candidate)) for p in products}
    untouched = {p: sha for p, sha in all_products.items() if p not in changed_paths}
    assert all(digest(archive / p) == sha for p, sha in untouched.items())
    assert all(digest(p) == sha for p, sha in raw_hashes.items())
    assert all(digest(archive / p.relative_to(candidate)) == digest(p) for p in products)
    print('Index and hashes verified; exporting the full HOBO curated workbook.', flush=True)
    catalog, catalog_messages = curated.discover_qualified_corpus(archive)
    options = curated.available_filters(catalog, ['HOBO'])
    tables, included, selection, messages = curated.build_curated_tables(
        catalog, ['HOBO'], options['sites'], options['years'])
    assert (digest(workbook) if workbook.exists() else None) == workbook_before, 'Workbook changed during promotion'
    curated.write_curated_workbook(workbook, archive, tables, included, selection)
    saved = pd.read_excel(workbook, sheet_name='HOBO')
    assert len(saved) == len(tables['HOBO'])
    assert equal_values(saved[TEMP], tables['HOBO'][TEMP]).all()
    (output / 'curated_build.log').write_text('\n'.join(catalog_messages + messages), encoding='utf-8')
    plan.update({'index_products': len(rebuilt), 'source_rows': int(rebuilt.n_rows.sum()),
                 'workbook': str(workbook), 'unified_hobo_rows': len(saved),
                 'raw_files_unchanged': len(raw_hashes), 'untouched_products_verified': len(untouched),
                 'retained_rows': sum(baseline[p]['rows'] for p in args.retain_product),
                 'completed': True})
    save_json(output / 'promotion.json', plan)
    print(json.dumps(plan, indent=2), flush=True)


if __name__ == '__main__':
    main()

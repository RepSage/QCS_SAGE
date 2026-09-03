"""Requalify HOBO into a separate tree and compare with the active archive.

Dependencies: the QCS runtime (Python 3.13, pandas 2.2, numpy 2.1, openpyxl 3.1).
The active qualified files, raw exports, and user settings are read-only inputs.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys

import numpy as np
import pandas as pd


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def inventory(path):
    frame = pd.read_csv(path)
    values = pd.to_numeric(frame['Temperature (degC)'], errors='coerce')
    return {'path': str(path), 'sha256': digest(path), 'rows': len(frame),
            'columns': len(frame.columns), 'dtypes': frame.dtypes.astype(str).to_dict(),
            'missing': frame.isna().sum().astype(int).to_dict(),
            'duplicate_timestamps': int(frame.Datetime.duplicated().sum()),
            'temperature_min_degC': values.min(), 'temperature_max_degC': values.max()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--site')
    parser.add_argument('--semester')
    args = parser.parse_args()
    archive, output = args.archive.resolve(), args.output.resolve()
    if output == archive or archive in output.parents or output in archive.parents:
        raise ValueError('Validation output must be outside the active archive')
    output.mkdir(parents=True, exist_ok=True)
    os.environ['QCS_QUALIFIED_OUTPUT_ROOT'] = str(output)
    os.environ['QCS_HOBO_ONLY'] = '1'
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    settings = Path(__file__).resolve().parents[1] / 'qcs_user_settings.json'
    settings_hash = digest(settings) if settings.exists() else None
    # qualify_site disables both preference writers before booting the hidden shell.
    import qualify_site as qs
    qs.ROOT = str(archive)
    qs.H_RAW = str(archive / 'HOBO/raw')
    qs.SG_RAW = str(archive / 'SEAGUARD/raw')
    qs.H_REFERENCE = str(archive / 'HOBO/qualified')
    active = sorted((archive / 'HOBO/qualified').glob('*/*/*_QLF.csv'))
    if args.site:
        active = [p for p in active if p.parent.name == args.site]
    if args.semester:
        active = [p for p in active if p.parent.parent.name == args.semester]
    before = {p.name: inventory(p) for p in active}
    (output / 'baseline_inventory.json').write_text(json.dumps(before, indent=2, default=str), encoding='utf-8')
    print('BASELINE: %d products; %d rows. Inventory saved before qualification.' %
          (len(before), sum(r['rows'] for r in before.values())), flush=True)
    groups = sorted({(p.parent.name, p.parent.parent.name) for p in active})
    raw_hashes = {}
    results = []
    for site, semester in groups:
        for raw in (archive / 'HOBO/raw' / semester / site / 'planilha').glob('*'):
            if raw.is_file():
                raw_hashes[str(raw)] = digest(raw)
        results.extend(qs.do_site(site, semester))
        (output / 'run_results.json').write_text(json.dumps(results, indent=2), encoding='utf-8')
    rows = []
    candidates = sorted((output / 'HOBO/qualified').glob('*/*/*_QLF.csv'))
    for candidate in candidates:
        if candidate.name not in before:
            rows.append({'product': candidate.name, 'status': 'new_product'})
            continue
        baseline = Path(before[candidate.name]['path'])
        old, new = pd.read_csv(baseline), pd.read_csv(candidate)
        same_grid = old.Datetime.equals(new.Datetime)
        row = {'product': candidate.name, 'status': 'compared', 'rows_before': len(old),
               'rows_after': len(new), 'same_grid': same_grid,
               'temperature_blank': int(new['Temperature (degC)'].isna().sum()),
               'temperature_withheld': int((new['Temperature (degC)'].isna() & new.Flag_T.eq(3)).sum())}
        if same_grid:
            for column in ['Temperature (degC)', 'Luminosity (lux)', 'Flag_T', 'Flag_lux']:
                a, b = pd.to_numeric(old[column]), pd.to_numeric(new[column])
                row[column + '_changed'] = int((~np.isclose(a, b, equal_nan=True)).sum())
            row['max_temperature_change_degC'] = (old['Temperature (degC)'] - new['Temperature (degC)']).abs().max()
        rows.append(row)
    pd.DataFrame(rows).to_csv(output / 'product_diff.csv', index=False)
    changed_inputs = [p for p, sha in raw_hashes.items() if digest(p) != sha]
    changed_active = [r['path'] for r in before.values() if digest(r['path']) != r['sha256']]
    settings_unchanged = (digest(settings) if settings.exists() else None) == settings_hash
    missing = sorted(set(before) - {p.name for p in candidates})
    import sweep_value_integrity as integrity
    integrity.ROOT = str(output)
    n_read, scale, impossible, unflagged = integrity.sweep()
    scale_defects = [h for h in scale if h['integers'] and h['factor']]
    database, messages = qs.dh.build_database('HOBO', file_list=[str(p) for p in candidates])
    (output / 'unification.log').write_text('\n'.join(messages), encoding='utf-8')
    summary = {'version': qs.dh.QCS_VERSION, 'baseline_products': len(before),
               'candidate_products': len(candidates), 'baseline_rows': sum(r['rows'] for r in before.values()),
               'candidate_rows': sum(pd.read_csv(p).shape[0] for p in candidates),
               'unified_rows': len(database), 'missing_products': missing,
               'raw_files_hashed': len(raw_hashes), 'changed_raw': changed_inputs,
               'changed_active': changed_active, 'settings_unchanged': settings_unchanged,
               'integrity_products': n_read, 'scale_defects': scale_defects,
               'unflagged_impossible': unflagged, 'failed_runs': [r for r in results if r[-1]]}
    (output / 'validation_summary.json').write_text(json.dumps(summary, indent=2, default=str), encoding='utf-8')
    print(json.dumps(summary, indent=2, default=str), flush=True)
    if missing or changed_inputs or changed_active or scale_defects or unflagged or summary['failed_runs']:
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

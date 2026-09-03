"""Summarize the candidate diff and verify report/product and provenance contracts.

Dependencies: pandas 2.2, numpy 2.1, openpyxl 3.1 (Anaconda QCS runtime).
"""
import json
from pathlib import Path
import sys

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent / 'corpus_confirmed'
diff = pd.read_csv(ROOT / 'product_diff.csv')
queue = pd.read_csv(ROOT / 'episode_review_queue.csv')
summary = {
    'diff_rows': len(diff), 'same_grid_products': int(diff.same_grid.sum()),
    'changed_temperature_products': int(diff['Temperature (degC)_changed'].gt(0).sum()),
    'changed_temperatures': int(diff['Temperature (degC)_changed'].sum()),
    'withheld_temperatures': int(diff.temperature_withheld.sum()),
    'changed_light': int(diff['Luminosity (lux)_changed'].sum()),
    'changed_light_flags': int(diff.Flag_lux_changed.sum()),
    'changed_temperature_flags': int(diff.Flag_T_changed.sum()),
    'diagnostic_episodes': len(queue), 'sustained_diagnostic_episodes': int(queue.sustained.sum()),
}
failures, reports = [], []
for product in (ROOT / 'HOBO/qualified').glob('*/*/*_QLF.csv'):
    frame = pd.read_csv(product)
    stem = product.stem
    folder = product.parent / 'reports'
    report = pd.read_excel(folder / (stem + '__QCS_report.xlsx')).iloc[0]
    audit = folder / (stem + '__QCS_replicate_samples.csv')
    if report.get('scope') == 'combined':
        reports.append(stem)
        if int(report.Total) != len(frame) or int(report.T_suspect) != int(frame.Flag_T.eq(3).sum()):
            failures.append(stem + ': combined report disagrees with CSV')
        if int(report.T_withheld) != int((frame['Temperature (degC)'].isna() & frame.Flag_T.eq(3)).sum()):
            failures.append(stem + ': incorrect withheld count')
        samples = pd.read_csv(audit)
        if len(samples) != len(frame):
            failures.append(stem + ': diagnostic rows lost')
        single = samples.eligible_contributors == 1
        if frame.loc[single, 'Temperature spread (degC)'].notna().any():
            failures.append(stem + ': spread with a single contributor')
        if frame.Flag.notna().any():
            failures.append(stem + ': individual file masquerades as combined')
    # A multi-input product must have a real combined report and empty flag string.
    blocks = (product.parent / 'provenance.txt').read_text(encoding='utf-8').split('\n\n')
    block = next(b for b in blocks if b.splitlines() and b.splitlines()[0] == stem)
    inputs = next(line for line in block.splitlines() if 'inputs   :' in line)
    if ' | ' in inputs and report.get('scope') != 'combined':
        failures.append(stem + ': multi-input product lacks combined report')
sgom = ROOT / 'HOBO/qualified/2026S1/SGOM/SGOM_2026S1_HOBO_QLF.csv'
sgom_frame = pd.read_csv(sgom)
summary['sgom'] = {'rows': len(sgom_frame), 'finite_temperature': int(sgom_frame['Temperature (degC)'].notna().sum()),
                   'spread_blank': int(sgom_frame['Temperature spread (degC)'].isna().sum()),
                   'min_degC': sgom_frame['Temperature (degC)'].min(),
                   'max_degC': sgom_frame['Temperature (degC)'].max()}
summary['combined_reports_checked'] = len(reports)
summary['failures'] = failures
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'sourceCode'))
import QCS_DataHandler as data
baseline = {}
for path in (ROOT / 'site_runs').glob('*/baseline_inventory.json'):
    baseline.update(json.loads(path.read_text(encoding='utf-8')))
old_database, old_messages = data.build_database('HOBO', file_list=[baseline[name]['path'] for name in diff['product']])
summary['baseline_matching_products_unified_rows'] = len(old_database)
(ROOT / 'baseline_unification.log').write_text('\n'.join(old_messages), encoding='utf-8')
changed = diff.loc[diff['Temperature (degC)_changed'].gt(0)]
changed.to_csv(ROOT / 'changed_temperature_products.csv', index=False)
(ROOT / 'audit_summary.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
assert diff.same_grid.all() and not failures, summary
assert np.isfinite(sgom_frame['Temperature (degC)']).all()
print(json.dumps(summary, indent=2))

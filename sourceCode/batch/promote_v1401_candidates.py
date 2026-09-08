"""Inspect or promote the bounded v14.0.1 Doppler, scalar/PAR and clock replay.

Dependencies: QCS runtime, pandas/NumPy. No qualification is performed here.
The three completed replay directories and four independently verified clock
exports are prerequisites. Dry-run builds a complete local candidate index,
runs the canonical integrity/unification checks, and inventories current inputs.
--apply additionally verifies complete backups before replacing active files.
"""
import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path
import shutil
import sys

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import QCS_DataHandler as data
from QCS_Replicates import copy_report_file
import build_index
import sweep_value_integrity as integrity


def digest(path):
    with Path(path).open('rb') as handle:
        return hashlib.file_digest(handle, 'sha256').hexdigest()


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, default=str), encoding='utf-8')


def tree_hashes(folder):
    return {str(p.relative_to(folder)): digest(p) for p in folder.rglob('*') if p.is_file()}


def contained(path, root):
    path, root = path.resolve(), root.resolve()
    assert root in path.parents, ('Path is outside its intended tree', path, root)
    return path


def copy_file(source, target):
    target.parent.mkdir(parents=True, exist_ok=True)
    copy_report_file(source, target)
    assert digest(source) == digest(target), target


def provenance(original, names, backup=None):
    """Append fields INSIDE original blocks; duplicate product blocks lose inputs."""
    blocks = []
    for block in original.read_text(encoding='utf-8').split('\n\n'):
        if not block.strip():
            continue
        name = block.splitlines()[0].strip()
        if name in names:
            block += ('\n    requalified_version : v14.0.1'
                      '\n    requalified_on : 2026-09-08'
                      '\n    requalification_policy : corrected native DCPS framing/geometry/status;'
                      ' current PAR flags; fixed-window HOBO; no new manual/source exclusion ratified')
            if '_HOBO_' in name:
                block += ('\n    clock_repair : 24-hour wall clock from matched original binary;'
                          ' all exported measurements retained, including launch-only reading;'
                          ' no GMT conversion applied')
            if backup:
                block += '\n    requalification_backup : ' + str(backup)
        blocks.append(block)
    return '\n\n'.join(blocks) + '\n\n'


def inspect_replays(archive, evidence):
    sources = {}
    for folder, count in [('full_candidate', 53), ('scalar_candidate', 113), ('clock_candidate', 2)]:
        root = evidence / folder
        summary = json.loads((root / 'summary.json').read_text())
        assert not summary['failures'] and not summary['changed_inputs']
        assert summary['settings_unchanged'] and not summary.get('changed_sources', [])
        products = list(root.glob('*/qualified/*/*/*_QLF.csv'))
        assert len(products) == count, (folder, len(products))
        for p in products:
            relative = p.relative_to(root)
            assert relative not in sources
            sources[relative] = p
        for p, sha in json.loads((root / 'before_hashes.json').read_text()).items():
            assert digest(p) == sha, ('Replay input changed', p)
        manifest = root / ('candidate_hashes.final.json' if folder == 'full_candidate'
                           else 'candidate_hashes.json')
        if manifest.exists():
            for p, sha in json.loads(manifest.read_text()).items():
                assert digest(root / p) == sha, ('Candidate changed', p)
        print('REPLAY VERIFIED', folder, count, 'products', flush=True)
    # Scalar replay is only allowed to add/update flags, version and reports.
    scalar_diff = json.loads((evidence / 'scalar_candidate/product_diff.json').read_text())
    assert len(scalar_diff) == 113 and all(not r['value_changes'] for r in scalar_diff)
    doppler = json.loads((evidence / 'full_candidate/product_diff.json').read_text())
    assert sum(r['added_rows'] for r in doppler) == 24054
    assert all(r['removed_rows'] == 0 for r in doppler)
    exports = json.loads((evidence / 'clock_jobs.json').read_text())
    checks = json.loads((evidence / 'clock_candidate/export_verification.json').read_text())
    assert len(exports) == len(checks) == 4 and all(r['duplicate_times'] == 0 for r in checks)
    for row in exports:
        assert contained(Path(row['input']), archive).suffix == '.xlsx'
    return sources, exports


def validate_stage(archive, stage, sources):
    original_index = pd.read_csv(archive / 'qualified_index.csv').fillna('')
    assert len(original_index) == 281
    original_paths = {Path(p) for p in original_index.path}
    assert set(sources) <= original_paths
    for relative in original_paths:
        copy_file(sources.get(relative, archive / relative), stage / relative)
    for relative, source in sources.items():
        name = source.stem
        source_panels = source.parent / 'DataView' / name
        if source_panels.exists():
            shutil.copytree(source_panels, stage / relative.parent / 'DataView' / name,
                            copy_function=copy_report_file)
        for report in (source.parent / 'reports').glob(name + '__*'):
            if report.is_file():
                copy_file(report, stage / relative.parent / 'reports' / report.name)
    sites = {p.parent for p in original_paths}
    for relative in sites:
        names = {p.stem for p in sources if p.parent == relative}
        original = archive / relative / 'provenance.txt'
        (stage / relative / 'provenance.txt').write_text(provenance(original, names), encoding='utf-8')
        before = build_index.parse_provenance(str(original))
        after = build_index.parse_provenance(str(stage / relative / 'provenance.txt'))
        for name, fields in before.items():
            assert all(after[name].get(k) == v for k, v in fields.items())
    build_index.ROOT = str(stage)
    current = build_index.main(str(stage / 'qualified_index.csv')).fillna('')
    assert set(current['product']) == set(original_index['product'])
    assert int(current.n_rows.sum()) == int(original_index.n_rows.sum()) + 24054
    for field in ['instrument', 'semester', 'site', 'bucket', 'tipo', 'campaign',
                  'cast_start', 'inputs', 'co2_file', 'co2_points', 'stations']:
        old = original_index.set_index('product')[field].sort_index()
        new = current.set_index('product')[field].sort_index()
        assert old.equals(new), ('Index provenance changed', field)
    integrity.ROOT = str(stage)
    read, scale, impossible, unflagged = integrity.sweep()
    defects = [r for r in scale if r['integers'] and r['factor']]
    assert read == 281 and not defects and not unflagged
    unified = {}
    for instrument, layout in [('DOPPLER', 'Doppler'), ('SEAGUARD', 'Seaguard'), ('HOBO', 'HOBO')]:
        selected = current[current.instrument == instrument]
        frame, messages = data.build_database(layout, file_list=[str(stage / p) for p in selected.path])
        assert not frame.empty
        unified[instrument] = {'products': len(selected), 'source_rows': int(selected.n_rows.sum()),
                               'unified_rows': len(frame), 'messages': messages}
    return {'products': read, 'source_rows': int(current.n_rows.sum()),
            'scale_defects': defects, 'unflagged_impossible': unflagged,
            'flagged_impossible': impossible, 'unification': unified}


def apply(archive, stage, output, sources, exports, baseline):
    stamp = datetime.now().strftime('%Y%m%dT%H%M%S')
    backup = archive / '_deleted' / ('qcs_v1401_' + stamp)
    backup.mkdir(parents=True, exist_ok=False)
    index = archive / 'qualified_index.csv'
    copy_file(index, backup / 'qualified_index.before.csv')
    sites = sorted({p.parent for p in sources})
    expected = {}
    for relative in sites:
        print('BACKUP/PREPARE', relative, flush=True)
        active = contained(archive / relative, archive)
        saved = contained(backup / 'original' / relative, backup)
        prepared = contained(backup / 'prepared' / relative, backup)
        shutil.copytree(active, saved, copy_function=copy_report_file)
        assert tree_hashes(active) == tree_hashes(saved)
        shutil.copytree(saved, prepared, copy_function=copy_report_file)
        for product in [p for p in sources if p.parent == relative]:
            name = product.stem
            copy_file(stage / product, prepared / product.name)
            panel = contained(prepared / 'DataView' / name, prepared)
            if panel.exists():
                shutil.rmtree(panel)  # Only the verified copy inside backup/prepared.
            candidate_panels = stage / relative / 'DataView' / name
            if candidate_panels.exists():
                shutil.copytree(candidate_panels, panel, copy_function=copy_report_file)
            # Keep displaced report identities inspectable, without presenting stale
            # legends or summaries as the current product's reports.
            reports = prepared / 'reports'
            for old in list(reports.glob(name + '__*')):
                if old.is_file():
                    destination = contained(reports / 'previous' / stamp / old.name, prepared)
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    old.rename(destination)
            for report in (stage / relative / 'reports').glob(name + '__*'):
                if report.is_file():
                    copy_file(report, reports / report.name)
        names = {p.stem for p in sources if p.parent == relative}
        (prepared / 'provenance.txt').write_text(provenance(active / 'provenance.txt', names, saved), encoding='utf-8')
        expected[str(relative)] = tree_hashes(prepared)
    raw_jobs = []
    clock_manifest = []
    for export in exports:
        active = contained(Path(export['input']), archive)
        relative = active.relative_to(archive)
        copy_file(active, backup / 'original' / relative)
        prepared = backup / 'prepared' / relative
        copy_file(Path(export['output']), prepared)
        raw_jobs.append(relative)
        clock_manifest.append({
            'path': str(relative), 'binary': export['binary'],
            'binary_sha256': digest(export['binary']),
            'before_sha256': digest(active), 'after_sha256': digest(prepared),
            'before_bytes': active.stat().st_size, 'after_bytes': prepared.stat().st_size,
            'exported_rows': export['rows'],
            'repair': 'Recover 24-hour wall clock from matched original binary; no GMT conversion',
            'measurement_policy': 'All exported measurements retained, including launch-only reading',
        })
    save(backup / 'clock_export_manifest.json', clock_manifest)
    copy_file(backup / 'clock_export_manifest.json', output / 'clock_export_manifest.json')
    save(output / 'backup_manifest.json', {'backup': str(backup), 'prepared_sites': expected})
    assert digest(index) == baseline['index']
    for p, sha in baseline['raw'].items():
        assert digest(archive / p) == sha
    for p, sha in baseline['qualified'].items():
        assert digest(archive / p) == sha
    moved = []
    try:
        for relative in raw_jobs + sites:
            active = contained(archive / relative, archive)
            prepared = contained(backup / 'prepared' / relative, backup)
            displaced = contained(backup / 'displaced' / relative, backup)
            if relative in sites:
                assert tree_hashes(active) == tree_hashes(backup / 'original' / relative)
            else:
                assert digest(active) == digest(backup / 'original' / relative)
            displaced.parent.mkdir(parents=True, exist_ok=True)
            active.rename(displaced)
            try:
                prepared.rename(active)
            except OSError:
                displaced.rename(active)
                raise
            moved.append(relative)
            save(output / 'journal.json', {'backup': str(backup), 'moved': list(map(str, moved))})
        for relative in sites:
            assert tree_hashes(archive / relative) == expected[str(relative)]
        for relative, source in sources.items():
            assert digest(archive / relative) == digest(source)
        changed_raw = {str(Path(j['input']).relative_to(archive)): digest(Path(j['output'])) for j in exports}
        for relative, sha in baseline['raw'].items():
            assert digest(archive / relative) == changed_raw.get(relative, sha)
        for relative, sha in baseline['qualified'].items():
            if Path(relative) not in sources:
                assert digest(archive / relative) == sha
        build_index.ROOT = str(archive)
        final_index = build_index.main(str(index))
        integrity.ROOT = str(archive)
        assert integrity.main() == 0
        assert int(final_index.n_rows.sum()) == 664861 and len(final_index) == 281
        copy_file(index, output / 'qualified_index.after.csv')
    except Exception:
        # All displaced originals remain recoverable, including on partial failure.
        for relative in reversed(moved):
            active = contained(archive / relative, archive)
            failed = contained(backup / 'rolled_back' / relative, backup)
            failed.parent.mkdir(parents=True, exist_ok=True)
            active.rename(failed)
            (backup / 'displaced' / relative).rename(active)
        copy_file(backup / 'qualified_index.before.csv', index)
        save(output / 'rollback.json', {'restored': list(map(str, moved)), 'backup': str(backup)})
        raise
    return {'applied': True, 'backup': str(backup), 'site_folders': len(sites),
            'qualified_products': len(sources), 'clock_exports': len(raw_jobs),
            'all_raw_hashes_verified': len(baseline['raw']), 'all_qualified_hashes_verified': len(baseline['qualified'])}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive', type=Path, required=True)
    parser.add_argument('--evidence', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    archive, evidence, output = args.archive.resolve(), args.evidence.resolve(), args.output.resolve()
    assert archive not in output.parents and output not in archive.parents and output != archive
    output.mkdir(parents=True, exist_ok=False)
    sources, exports = inspect_replays(archive, evidence)
    baseline = {'index': digest(archive / 'qualified_index.csv'),
                'qualified': {str(p.relative_to(archive)): digest(p) for p in archive.glob('*/qualified/**/*_QLF.csv')},
                'raw': {str(p.relative_to(archive)): digest(p) for family in ['SEAGUARD', 'HOBO']
                        for p in (archive / family / 'raw').rglob('*') if p.is_file()}}
    save(output / 'before_hashes.json', baseline)
    print('INVENTORY', len(baseline['raw']), 'raw files;', len(baseline['qualified']), 'products', flush=True)
    stage = output / 'candidate_database'
    result = validate_stage(archive, stage, sources)
    result['applied'] = False
    save(output / 'validation.json', result)
    if args.apply:
        result.update(apply(archive, stage, output, sources, exports, baseline))
    save(output / 'result.json', result)
    print(json.dumps({k: v for k, v in result.items() if k not in ['unification', 'flagged_impossible']}, indent=2), flush=True)


if __name__ == '__main__':
    main()

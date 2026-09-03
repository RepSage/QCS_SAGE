"""Run isolated per-site candidate replays concurrently, then assemble one corpus.

Dependencies: QCS runtime; stdlib subprocess/concurrent.futures. Every worker
has a private output tree and disables GUI preference writes before shell boot.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

import pandas as pd


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    archive, output = args.archive.resolve(), args.output.resolve()
    if output == archive or archive in output.parents or output in archive.parents:
        raise ValueError('Output must be outside the archive')
    if output.exists():
        raise ValueError('Use a fresh validation output directory')
    output.mkdir(parents=True)
    sources = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(sources))
    from QCS_Replicates import copy_report_file
    tracked = list(sources.glob('QCS_*.py')) + [Path(__file__).with_name('qualify_site.py'),
                                               Path(__file__).with_name('replicate_decisions.csv')]
    hashes = {str(p.relative_to(sources)): hashlib.sha256(p.read_bytes()).hexdigest() for p in tracked}
    (output / 'source_hashes.json').write_text(json.dumps(hashes, indent=2), encoding='utf-8')
    sites = sorted({p.parent.name for p in (archive / 'HOBO/qualified').glob('*/*/*_QLF.csv')})
    driver = Path(__file__).with_name('validate_hobo_candidate.py')

    def replay(site):
        lane = output / 'site_runs' / site
        logfile = output / (site + '.log')
        with logfile.open('w', encoding='utf-8') as stream:
            result = subprocess.run([sys.executable, str(driver), '--archive', str(archive),
                                     '--output', str(lane), '--site', site], stdout=stream,
                                    stderr=subprocess.STDOUT, check=False,
                                    creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        return site, result.returncode

    failures = []
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = [executor.submit(replay, site) for site in sites]
        for future in as_completed(futures):
            site, code = future.result()
            print('%s finished: exit %d' % (site, code), flush=True)
            if code:
                failures.append(site)
    summaries, diffs, episodes = [], [], []
    for site in sites:
        lane = output / 'site_runs' / site
        summary_path = lane / 'validation_summary.json'
        if not summary_path.exists():
            failures.append(site)
            continue
        summaries.append(json.loads(summary_path.read_text(encoding='utf-8')))
        diffs.append(pd.read_csv(lane / 'product_diff.csv'))
        for folder in (lane / 'HOBO/qualified').glob('*/*'):
            target = output / 'HOBO/qualified' / folder.parent.name / folder.name
            shutil.copytree(folder, target, copy_function=copy_report_file)
        for path in (lane / 'HOBO/qualified').glob('*/*/reports/*__QCS_replicate_episodes.csv'):
            frame = pd.read_csv(path)
            frame.insert(0, 'product', path.name.split('__QCS_')[0])
            episodes.append(frame)
    if diffs:
        pd.concat(diffs, ignore_index=True).to_csv(output / 'product_diff.csv', index=False)
    if episodes:
        pd.concat(episodes, ignore_index=True).to_csv(output / 'episode_review_queue.csv', index=False)
    final = {'site_runs': len(sites), 'failed_sites': sorted(set(failures))}
    for key in ['baseline_products', 'candidate_products', 'baseline_rows', 'candidate_rows',
                'raw_files_hashed', 'integrity_products']:
        final[key] = sum(s[key] for s in summaries)
    for key in ['missing_products', 'changed_raw', 'changed_active', 'scale_defects',
                'unflagged_impossible', 'failed_runs']:
        final[key] = [item for s in summaries for item in s[key]]
    final['settings_unchanged'] = all(s['settings_unchanged'] for s in summaries)
    final['source_unchanged'] = all(hashlib.sha256((sources / p).read_bytes()).hexdigest() == sha
                                    for p, sha in hashes.items())
    sys.path.insert(0, str(sources))
    import QCS_DataHandler as data
    products = sorted((output / 'HOBO/qualified').glob('*/*/*_QLF.csv'))
    database, messages = data.build_database('HOBO', file_list=[str(p) for p in products])
    final['unified_rows'] = len(database)
    (output / 'unification.log').write_text('\n'.join(messages), encoding='utf-8')
    (output / 'validation_summary.json').write_text(json.dumps(final, indent=2), encoding='utf-8')
    print(json.dumps(final, indent=2), flush=True)
    return int(bool(failures) or not final['source_unchanged'])


if __name__ == '__main__':
    raise SystemExit(main())

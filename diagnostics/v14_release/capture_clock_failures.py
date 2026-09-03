"""Replay the two retained products with complete dialogs, outside the archive."""
import argparse
import json
import os
from pathlib import Path
import sys

parser = argparse.ArgumentParser()
parser.add_argument('--archive', type=Path, required=True)
args = parser.parse_args()
ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent / 'clock_replay'
assert not OUT.exists()
os.environ['QCS_HOBO_ONLY'] = '1'
os.environ['QCS_QUALIFIED_OUTPUT_ROOT'] = str(OUT)
sys.path.insert(0, str(ROOT / 'sourceCode/batch'))
# The official driver disables both preference writers before hidden-shell boot.
import qualify_site as qs
qs.ROOT = str(args.archive)
qs.H_RAW = str(args.archive / 'HOBO/raw')
qs.SG_RAW = str(args.archive / 'SEAGUARD/raw')
qs.H_REFERENCE = str(args.archive / 'HOBO/qualified')
results = []
for site in ['ESQNORTE', 'ESQSUL']:
    logs = []
    qs.qm.log_line = logs.append
    run = qs.do_site(site, '2024S2')
    results.append({'site': site, 'results': run, 'dialogs': list(qs.DIALOGS), 'log': logs})
    Path(__file__).with_name('clock_failures.json').write_text(json.dumps(results, indent=2), encoding='utf-8')
    print(site, json.dumps(run), flush=True)
assert all(any(dialog[0] == 'error' for dialog in record['dialogs']) for record in results)
assert not list(OUT.glob('HOBO/qualified/*/*/*_QLF.csv'))

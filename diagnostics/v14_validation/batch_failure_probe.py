"""Verify that a completed first replica cannot disguise a failed second input.

Dependencies: the QCS Anaconda base runtime. Only local temporary outputs.
"""
import argparse
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[2]
parser = argparse.ArgumentParser()
parser.add_argument('--archive', required=True, type=Path)
args = parser.parse_args()
sys.path.insert(0, str(ROOT / 'sourceCode/batch'))
import qualify_site as qs

sound = args.archive / 'HOBO/raw/2026S1/SGOM/planilha/HOBO2_SGOM_A2_110925.xlsx'
with TemporaryDirectory() as directory:
    broken = Path(directory) / 'incomplete_export.csv'
    broken.write_text('Not a logger export\nmissing channels\n', encoding='utf-8')
    csv, folder, error = qs.run_qualification([str(sound), str(broken)], 'HOBO', None,
                                             'SGOM', 'PARTIAL_MUST_NOT_SHIP')
    result = {'returned_file': csv, 'returned_folder': folder, 'error': error,
              'error_dialog_recorded': any(kind == 'error' for kind, _ in qs.DIALOGS)}
    assert csv is None and folder is None and error and result['error_dialog_recorded'], result
    Path(__file__).with_name('batch_failure_result.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps(result))

"""Run the real single-input pipeline for the owner-excluded SGOM logger.

Dependencies: QCS Anaconda base runtime. Archive and settings are read-only.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[2]
parser = argparse.ArgumentParser()
parser.add_argument('--archive', required=True, type=Path)
args = parser.parse_args()
source = args.archive / 'HOBO/raw/2026S1/SGOM/planilha/HOBO1_SGOM_A2_110925_ERRO.xlsx'
settings = ROOT / 'sourceCode/qcs_user_settings.json'
before = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in (source, settings)}
sys.path.insert(0, str(ROOT / 'sourceCode/batch'))
import qualify_site as qs
import pandas as pd
csv, run_root, error = qs.run_qualification([str(source)], 'HOBO', None, 'SGOM', 'SGOM_SINGLE_LEDGER_CHECK')
assert csv and not error, error
frame = pd.read_csv(csv)
result = {'rows': len(frame), 'temperature_blank': int(frame['Temperature (degC)'].isna().sum()),
          'temperature_dismissed': int(frame.Flag_T.eq(5).sum()),
          'finite_light': int(frame['Luminosity (lux)'].notna().sum()),
          'raw_and_settings_unchanged': all(hashlib.sha256(Path(p).read_bytes()).hexdigest() == sha
                                           for p, sha in before.items())}
out = Path(__file__).resolve().parent / 'single_sgom_verified'
shutil.copytree(run_root, out)
(out / 'result.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
# The existing reader trims six leading and three trailing out-of-water values
# from this logger's 2256 raw rows; its own grid differs from the combined grid.
assert result['rows'] == result['temperature_blank'] == result['temperature_dismissed'] == 2247
assert result['finite_light'] > 0 and result['raw_and_settings_unchanged']
print(json.dumps(result))

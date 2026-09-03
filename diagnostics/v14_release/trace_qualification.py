"""Trace lazy imports during a real isolated qualification using the build runtime."""
import json
from pathlib import Path
import runpy
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'sourceCode'))
import QCS_Main as qm
import QCS_DatabaseView as dbv
qm.save_user_prefs = lambda *args, **kwargs: None
dbv.save_user_prefs = lambda *args, **kwargs: None
driver = ROOT / 'sourceCode/batch/validate_hobo_candidate.py'
sys.argv[0] = str(driver)
try:
    runpy.run_path(str(driver), run_name='__main__')
finally:
    modules = {name: getattr(module, '__file__', None) for name, module in sys.modules.items()}
    Path(__file__).with_name('qualification_modules.json').write_text(json.dumps(modules, indent=2))

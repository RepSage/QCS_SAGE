"""Compare real qualification imports with the frozen bundle's dependency manifest."""
import ast
import hashlib
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
manifest = Path(os.environ['TEMP']) / 'qcs_build_work_v14/QCS/Analysis-00.toc'
toc = ast.literal_eval(manifest.read_text(encoding='utf-8'))
packaged = set()
packaged_paths = set()


def collect(value):
    if isinstance(value, (list, tuple)):
        if len(value) == 3 and isinstance(value[2], str) and value[2] in {
                'PYMODULE', 'PYMODULE-1', 'PYMODULE-2', 'PYSOURCE', 'EXTENSION'}:
            packaged.add(value[0].replace('\\', '.').replace('/', '.').removesuffix('.pyd'))
            packaged_paths.add(str(Path(value[1]).resolve()).lower())
        else:
            for item in value:
                collect(item)


collect(toc)
imports = json.loads((OUT / 'qualification_modules.json').read_text())
external = {name.split('.')[0] for name, path in imports.items()
            if path and 'site-packages' in path and name.split('.')[0] not in sys.stdlib_module_names}
qcs = {name for name in imports if name.startswith('QCS_')}
packed_top = {name.split('.')[0] for name in packaged}
# scipy exposes three extension modules under both qualified and short aliases.
# Compare their actual files, not just the alias recorded in sys.modules.
aliases = {name: imports[name] for name in external - packed_top
           if name in imports and str(Path(imports[name]).resolve()).lower() in packaged_paths}
# This venv startup hook comes from setuptools' distutils-precedence.pth;
# the frozen application has no site-packages .pth startup and does not use it.
startup_only = {'_distutils_hack'}
missing = sorted((external - packed_top - set(aliases) - startup_only) | (qcs - packaged))
critical = {'QCS_Replicates', 'matplotlib.backends.backend_svg',
            'matplotlib.backends.backend_mixed', 'openpyxl.cell._writer'}
assert critical <= packaged, sorted(critical - packaged)
assert not missing, missing
ledger = ROOT / 'sourceCode/batch/replicate_decisions.csv'
bundled = ROOT / 'packaging/dist/QCS/_internal/batch/replicate_decisions.csv'
assert ledger.read_bytes() == bundled.read_bytes()
result = {'real_qualification_external_packages': sorted(external),
          'qcs_modules': sorted(qcs), 'missing_packages_or_qcs_modules': missing,
          'extension_aliases_verified_by_file': aliases,
          'interpreter_startup_only': sorted(startup_only),
          'critical_lazy_modules_verified': sorted(critical),
          'ledger_sha256': hashlib.sha256(bundled.read_bytes()).hexdigest()}
(OUT / 'bundle_audit.json').write_text(json.dumps(result, indent=2))
print(json.dumps(result, indent=2))

# v14.0 release verification — 2026-09-03

The final source gate is `final_selftest.log` (78 tests passed) and
`final_ruff.log` (clean). The final edit to qualification source after the full
replay was the accepted-review banner's explicit `TEMPERATURE DECISION` label;
the real SGOM pipeline was then replayed with the final source and build runtime.
The later batch-only reporting change prioritizes the stopping error over an
earlier warning. `capture_clock_failures.py` reproduced both retained failures;
`clock_failures.json` preserves their complete dialogs and tracebacks. This batch
module is outside the frozen application; its change does not alter the payload.

`build.log` records the clean PyInstaller build; `installer.log` records the
Inno Setup compile. The retained old build environment had incomplete packages,
so a fresh `%TEMP%/qcs_build_v14` environment used the direct versions recovered
from its metadata in `build_requirements.txt`. The matching work directory is
`%TEMP%/qcs_build_work_v14`. No application dependency was upgraded deliberately.

`frozen_smoke.py` invokes the built executable's screenshot mode and its normal
window, checks only its own process, then closes it. `frozen_smoke.json` and
`frozen_ui.png` preserve the result. The writable build folder isolates test
preferences from the operator; the installer excludes those generated files.

`trace_qualification.py` no-ops both preference writers before the hidden source
shell is booted and runs the real candidate driver. Its local
`qualification_modules.json` is compared with PyInstaller's Analysis manifest
by `audit_bundle.py`; `bundle_audit.json` records the packaged QCS/lazy modules,
SciPy extension aliases and byte-identical ledger. `_distutils_hack` belongs to
the pip interpreter's setuptools `.pth` startup, not the frozen application.
These checks do not constitute a full qualification inside the frozen exe.

The full replay and promotion evidence lives in `../v14_corpus_rollout/` and
`../v14_corpus_promotion/`; archived-data dispositions belong to
`sourceCode/batch/CORPUS_LOG.md`. Generated candidate trees, backup copies,
operator datasets and publication credentials are not release assets.

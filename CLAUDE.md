# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

QCS (Quality Control System — SAGE): Tkinter GUI application for qualification and visualization of oceanographic sensor data. Two instrument families: Seaguard/TSCP loggers (T, S, C, P, O2, pH, chlorophyll, turbidity) and HOBO Pendant loggers (temperature + light, added in v4.0).

**Language: English, everywhere.** The user wants the entire project in English — code comments, docstrings, UI text, error/log messages, docs, commits and branches. The codebase originated in Portuguese (pt-BR) and is being migrated; a lot of pt-BR still remains. Write all new/edited content in English, and translate nearby pt-BR strings when you touch a file. Caution: some UI string literals are compared in logic (e.g. combobox values like `'TSCP Profile'`, `'HOBO'`, `'Seaguard'`) — those are already English; keep behavior identical when translating (translate the *display* text, not the compared value, unless you update every comparison too).

## Running

- Windows-only. Uses Anaconda's Python: `%USERPROFILE%\anaconda3\python.exe` (do not rely on `python` from PATH — it may resolve to a wrong interpreter, e.g. Inkscape's).
- Two entry points, launched via the `.bat` files at repo root:
  - `QCS - Data Qualification.bat` → `sourceCode/QCS_Main.py` (qualification pipeline)
  - `QCS - Data Visualization.bat` → `sourceCode/QCS_DatabaseView.py` (database viewer/plots)
- Dependencies: `python -m pip install -r sourceCode/requirements.txt`. `sv-ttk` is optional (falls back to the clam theme).

## Verification (mandatory)

After ANY change to `QCS_Tests.py`, `QCS_DataHandler.py`, or the qualification pipeline in `QCS_Main.py`, run the self-test suite and report the result:

```
cd sourceCode
python QCS_SelfTest.py
```

Lint (ruff, conservative rules — real errors only, config in `ruff.toml`):

```
python -m ruff check .
```

## Architecture — easy to get wrong

- **Flag strings**: each data row gets a flag string with exactly one character per test, in `test_sequence` order (built in `QCS_Main.py`). Per-variable columns (`Flag_T`, `Flag_S`, `Flag_lux`, …) are derived via `FLAG_BUCKET_MAP` in `QCS_DataHandler.py`. Adding/removing/reordering a test requires keeping `FLAG_BUCKET_MAP` in sync. Flag codes: 1=good, 2=not evaluated, 3=suspect, 4=bad, 5=dismissed, 9=missing.
- **Values <= 0 are discarded by design** for physically positive variables — this is intentional, not a bug.
- **`build_database()`** (`QCS_DataHandler.py`) is the single unification engine for merging qualified files. It detects HOBO vs. Seaguard layouts and refuses to mix them; it deduplicates exact rows and warns on Site+Datetime overlaps. Do not write ad-hoc merge logic elsewhere.
- **HOBO vs. Seaguard**: HOBO files run only the temperature tests plus the light fouling-window test (`light_cutoff_window`); they have their own output column layout. Layout detection: `detect_qualified_layout()` in `QCS_DataHandler.py`.
- **Theming/DPI** is centralized in `QCS_Theme.py` (sv-ttk, dark mode, DPI awareness). Plot colors are centralized in `getParamColors()` / `getSiteColors()` in `QCS_DataView.py`. Don't hardcode colors or fonts in windows/plots.
- **User settings** live in `sourceCode/qcs_user_settings.json` (auto-generated, gitignored, version-gated: a version bump may intentionally reset QC criteria to new defaults while preserving file paths).
- **Version**: `QCS_VERSION` in `QCS_DataHandler.py` is the single source of truth for the app version.

## Releases and commits

- Commit messages in English, prefixed with the version, e.g. `v4.0: short description`.
- Propose the next SemVer number for each change set. Any change that alters QC results (flags, thresholds, test logic) is a MAJOR bump.
- On each release: create a new file in `changelog/` listing all changes for the version, update the HTML user manual (`Quality Control System (SAGE) - User Manual.html`) with the version and changes, and tag the version in Git.

## Pending work

- v4.0 is unreleased, on branch `improvements-v4.0` (nothing pushed to GitHub yet). Before release: finish the pt-BR → English migration of the code, complete the GUI end-to-end test with real files, then tag and open the PR to `master`.

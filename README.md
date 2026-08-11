# QCS — Quality Control System (SAGE)

Tool for qualification and visualization of oceanographic physico-chemical data
(profiles and moorings), developed for the SAGE project data.

## How to run

The program runs directly from the Python scripts, using Anaconda's Python.
Since v5.0 both tools live in a single window; double-click one shortcut in the
main folder:

- **`QCS.bat`** — the unified app (`sourceCode/QCS_App.py`): a menu bar plus two
  tabs, **Data Qualification** and **Data Visualization**.

The app runs with no terminal window; progress and any errors are shown in the
in-app Execution log. (The two tool modules `QCS_Main.py` and
`QCS_DatabaseView.py` can still be launched on their own for development.)

## Dependencies

Python (Anaconda) with the packages listed in [`sourceCode/requirements.txt`](sourceCode/requirements.txt):
`numpy`, `pandas`, `matplotlib`, `scipy`, `openpyxl` and `gsw`. To install:

```
python -m pip install -r sourceCode/requirements.txt
```

## Structure

- `sourceCode/` — source code:
  - `QCS_App.py` — unified app shell (menu bar + Qualification/Visualization tabs); the entry point.
  - `QCS_Main.py` — qualification tool (interface + QC test pipeline).
  - `QCS_DatabaseView.py` — database visualization tool.
  - `QCS_DataHandler.py` — data reading, conversion and formatting; the `QCS_VERSION` constant.
  - `QCS_DataView.py` — plot and panel generation.
  - `QCS_Tests.py` — quality control tests.
  - `QCS_Theme.py` — theming, DPI awareness and the crash handler.
  - `QCS_SelfTest.py` — self-tests with synthetic data (`python QCS_SelfTest.py`).
  - `qcs_headless_harness.py` — drives the real pipeline with no GUI.
  - `batch/` — reproducible drivers that qualify the whole staged archive, plus
    `CORPUS_LOG.md` (what was done to the data itself) and a `README.md` with
    the corpus rules.
  - `requirements.txt` — dependencies.
  - `qcs_user_settings.json` — user preferences (auto-generated).
- `changelog/` — change history, one file per version.
- `Quality Control System (SAGE) - User Manual.html` — user manual.
- `CLAUDE.md` — durable rules and architecture gotchas.
- `STATUS.md` — current state, dated; read it before starting work.
- `ruff.toml` — lint configuration.

## Version

The version is defined in a single place: `QCS_VERSION`, in `sourceCode/QCS_DataHandler.py`.

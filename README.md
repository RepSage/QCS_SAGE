# QCS — Quality Control System (SAGE)

Tool for qualification and visualization of oceanographic physico-chemical data
(profiles and moorings), developed for the SAGE project data.

## How to run

The program runs directly from the Python scripts, using Anaconda's Python. Two
ready-made shortcuts sit in the main folder (double-click to open):

- **`QCS - Data Qualification.bat`** — qualification tool (`sourceCode/QCS_Main.py`).
- **`QCS - Data Visualization.bat`** — visualization tool (`sourceCode/QCS_DatabaseView.py`).

The app runs with no terminal window; progress and any errors are shown in the
in-app Execution log.

## Dependencies

Python (Anaconda) with the packages listed in [`sourceCode/requirements.txt`](sourceCode/requirements.txt):
`numpy`, `pandas`, `matplotlib`, `scipy`, `openpyxl` and `gsw`. To install:

```
python -m pip install -r sourceCode/requirements.txt
```

## Structure

- `sourceCode/` — source code:
  - `QCS_Main.py` — qualification tool (interface + QC test pipeline).
  - `QCS_DatabaseView.py` — database visualization tool.
  - `QCS_DataHandler.py` — data reading, conversion and formatting; the `QCS_VERSION` constant.
  - `QCS_DataView.py` — plot and panel generation.
  - `QCS_Tests.py` — quality control tests.
  - `QCS_SelfTest.py` — self-tests with synthetic data (`python QCS_SelfTest.py`).
  - `qcs_user_settings.json` — user preferences (auto-generated).
- `changelog/` — change history, one file per version.
- `Quality Control System (SAGE) - User Manual.html` — user manual.

## Version

The version is defined in a single place: `QCS_VERSION`, in `sourceCode/QCS_DataHandler.py`.

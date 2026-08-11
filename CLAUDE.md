# QCS (Quality Control System — SAGE)

Tkinter application for qualification and visualization of oceanographic sensor
data. Two instrument families: Seaguard/TSCP loggers (T, S, C, P, O2, pH,
chlorophyll, turbidity) and HOBO Pendant loggers (temperature + light).

**Language: English, everywhere** — code, docstrings, UI text, error and log
messages, docs, commits, branches. The pt-BR → English migration is complete
(verified 2026-08-06: no Portuguese strings remain under `sourceCode/`). Some UI
strings are compared in logic — combobox values such as `'TSCP Profile'`,
`'HOBO'`, `'Seaguard'`. If you ever reword one, update every comparison too.

## Running

Windows-only. Use the Anaconda **base** interpreter by absolute path. The
`QCS_SAGE` conda env is legacy and **cannot run this code**: it is Python 3.8.17
and the code calls `zip(..., strict=True)`, which needs ≥ 3.10 — the suite dies
on it (verified 2026-08-06).

- **`QCS.bat`** at the repo root is the launcher: a single window with the Data
  Qualification and Data Visualization tabs (`sourceCode/QCS_App.py`, started
  through `pythonw.exe`, so there is no console). Progress and errors go to the
  app's Execution log; a fatal crash writes `sourceCode/QCS_crash.log` and pops a
  message box (`install_crash_handler` in `QCS_Theme.py`).
- Dependencies: `sourceCode/requirements.txt`. `sv-ttk` is optional (falls back
  to the clam theme).
- **`sourceCode/qcs_headless_harness.py`** drives the real qualification pipeline
  with no GUI over a list of Seaguard `.bin` deployments, rotating settings and
  writing structured findings as JSON. This is how to exercise the pipeline
  autonomously.
- **`sourceCode/batch/`** holds the reproducible drivers that qualify the whole
  staged archive through the real pipeline (`run_semester.py`, `qualify_site.py`,
  `build_index.py`). Its `README.md` documents the hard-won corpus rules —
  semester naming, cast clustering, HOBO replicate grouping by data rather than
  by name, CO2 pairing by time overlap, provenance blocks. Read it before
  touching anything that writes to the corpus.

## Verification (mandatory)

After ANY change to `QCS_Tests.py`, `QCS_DataHandler.py`, or the qualification
pipeline in `QCS_Main.py`, run the suite and report the result:

```powershell
Push-Location sourceCode; & "C:\Users\LAMB\anaconda3\python.exe" QCS_SelfTest.py; Pop-Location
```

Lint (ruff, conservative rules — real errors only). `ruff.toml` sits at the repo
root, so run it from there:

```powershell
& "C:\Users\LAMB\anaconda3\python.exe" -m ruff check .
```

**Passing the suite is necessary, not sufficient** — the global rule, with
force here: every non-trivial defect in new analysis code was found by sweeping
the **real corpus**, never by the synthetic tests (one export alone carries
8,833 duplicated timestamps). After the tests pass, run the routine over the
archive and diff the counts against the previous `qualified_index.csv`.

## Architecture — easy to get wrong

- **Flag strings**: each data row gets a flag string with exactly one character
  per test, in `test_sequence` order (built in `QCS_Main.py`). Per-variable
  columns (`Flag_T`, `Flag_S`, `Flag_lux`, …) are derived via `FLAG_BUCKET_MAP`
  in `QCS_DataHandler.py`. Adding, removing or reordering a test requires keeping
  `FLAG_BUCKET_MAP` in sync. Flag codes: 1=good, 2=not evaluated, 3=suspect,
  4=bad, 5=dismissed, 9=missing.
- **Values ≤ 0 are discarded by design** for physically positive variables — this
  is intentional, not a bug.
- **`build_database()`** (`QCS_DataHandler.py`) is the single unification engine
  for merging qualified files. It detects HOBO vs. Seaguard layouts and refuses
  to mix them; it deduplicates exact rows and warns on Site+Datetime overlaps.
  Do not write ad-hoc merge logic elsewhere.
- **HOBO vs. Seaguard**: HOBO files run only the temperature tests plus the light
  fouling-window test (`light_cutoff_window`), and have their own output column
  layout. Layout detection: `detect_qualified_layout()` in `QCS_DataHandler.py`.
- **Theming/DPI** is centralized in `QCS_Theme.py` (sv-ttk, dark mode, DPI
  awareness). Plot colors are centralized in `getParamColors()` /
  `getSiteColors()` in `QCS_DataView.py`. Never hardcode colors or fonts in
  windows or plots.
- **User settings** live in `sourceCode/qcs_user_settings.json` (auto-generated,
  gitignored, version-gated: a version bump may intentionally reset QC criteria
  to new defaults while preserving file paths).
- **Version**: `QCS_VERSION` in `QCS_DataHandler.py` is the single source of
  truth for the app version.

## Timebase — getting this wrong corrupts the whole corpus

- **Seaguard (scalar or DCPS) records GMT → "Correct GMT-3" must ALWAYS be ON.**
  Switching the input type back to Seaguard re-enables it unconditionally;
  running with it off logs a warning.
- **HOBO exports are already local** (GMT-03 in the header) → never corrected;
  switching to HOBO auto-unchecks the option.
- **The CO2 logger clock is local**, and the CO2 file is an *addition* to a
  Seaguard run: `merge_co2_data` uses its timestamps as-is, so the GMT-3
  correction must **bypass** the CO2 even while enabled for the Seaguard side.
- Batch drivers must follow the same rule (`correct_gmt3h = (input_type ==
  'Seaguard')`). Getting it wrong once shifted the entire first qualified corpus
  by 3 h and misaligned every CO2 merge.

## Releases and commits

- Commit messages in English. The **subject line carries no version**; the
  version goes on the first line of the body:

  ```
  short description of the change

  Version: v11.0
  <the rest of the body>
  ```

  GitHub's file listing shows the subject of the last commit that touched each
  path, so a `v4.0:` prefix there reads as a version label ON THE FILE — the
  `.gitignore` row still showed `v4.0:` in August 2026 simply because nothing
  had needed to change it since. Which release a commit belongs to is recorded
  by the tags, exactly, and `git describe` answers it. Changed 2026-08-11;
  **commits before that date keep the old `vX.Y: description` prefix and must
  not be rewritten** — rewriting them changes every SHA and breaks the 21 tags
  and the 21 GitHub Releases that point at them.
- Propose the next SemVer number for each change set. Any change that alters QC
  results (flags, thresholds, test logic) is a MAJOR bump.
- On each release: add a file to `changelog/` listing the version's changes,
  update the HTML user manual (`Quality Control System (SAGE) - User Manual.html`)
  with the version and changes, and tag the version in Git.
- After a PR merges, delete the feature branch (local and remote) and return to
  an updated `master` before branching again.

Current phase, unreleased work and known-bad artifacts: see `STATUS.md`.

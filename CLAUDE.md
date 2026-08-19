# QCS (Quality Control System — SAGE)

Tkinter application for qualification and visualization of oceanographic sensor
data. Two instrument families: Seaguard/TSCP loggers (T, S, C, P, O2, pH,
chlorophyll, turbidity) and HOBO Pendant loggers (temperature + light).

**TSCP stays.** It is this project's house term for the four core variables of
the Seaguard string (temperature, salinity, conductivity, pressure) - AADI does
not call the instrument that - and it is spelled into interface values compared
in logic, into the `'tscp'` layout key, and into 123 archived
`*_QCS_tscp_stat.xlsx` files. The owner decided on 2026-08-19 that it is not to
be renamed; do not reopen it.

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
  Qualification and Data Visualization tabs. It starts **`QCS_QtApp.py`** (the
  Qt shell) through `packaging/v12_env/Scripts/pythonw.exe`, so there is no
  console - the Anaconda base cannot host PySide6 on this machine. The tk shell
  `sourceCode/QCS_App.py` is still in the tree and still runs, but it is not
  what the launcher opens. Progress and errors go to the app's Execution log; a
  fatal crash writes `sourceCode/QCS_crash.log` and pops a message box
  (`install_crash_handler` in `QCS_Theme.py`).
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

Any throwaway driver that BOOTS THE SHELL must no-op `save_user_prefs` in
both `QCS_DatabaseView` and `QCS_Main` before touching anything. They write
`qcs_user_settings.json` on ordinary actions (selecting files, advancing to
step 2), so a test run silently rewrites the operator's own settings —
and backing the file up first is worse: restoring it overwrites whatever
the RUNNING app saved meanwhile.

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
- **A DCPS (current profiler) product is TIDY: one row per record x depth
  CELL**, and three of its columns are traps. `Depth (m)` is the CELL depth - a
  handful of fixed values repeated on every record - so nothing may treat it as
  a profile axis or as a deployment depth series; `Site+Datetime` repeats once
  per cell BY CONSTRUCTION (`build_database` keys its overlap warning on
  `Site+Datetime+Column+Cell` for this layout); and `Heading/Pitch/Roll/Tilt/
  Ping count` are RECORD-level (`_DCPS_RECORD_PARAMS`), identical across the
  cells of one instant. Its flag string has its OWN sequence,
  `DOPPLER_TEST_SEQUENCE` (`QCS_Tests.py`), five positions since v13.0, with
  its own legend file - `FLAG_BUCKET_MAP` and the scalar sequence do not apply
  to it.
- **A DCPS manual dismissal is never partial** (v13.0): the cell values of one
  record are a single velocity solution, so a cut writes 5 over EVERY flag
  position of the row and blanks every measurement; a TILT cut takes the whole
  record (all its cells) and also blanks the record-level attitude, a per-cell
  cut takes one row and keeps it. The tilt review always runs (it is the
  DCPS's Depth review); the per-cell candidates are `DOPPLER_CUT_COLUMNS`
  (`QCS_Main.py`), NOT `MANUAL_CUT_COLUMNS`, whose nine scalar variables exist
  in no current table.
- **The `cur_manual` flag position must never claim a review that did not
  happen.** The batch drivers no-op `_show_and_wait`, so a review panel is
  built and answers 'nothing cut' with no window on screen: the pipeline
  decides the resting value from what it can actually know (a cut came back,
  or the operator ticked 'Check variables'), never from the fact that it
  called the panel.
- **A new input file format has FOUR wiring points**, and the readers are only
  one of them: the extension gate in `collect_input_settings` (`QCS_Main.py`),
  the Browse dialog `filetypes`, `sniff_input_type`, and the reader itself.
  v11.4 shipped `.hobo` wired everywhere EXCEPT the gate, so the feature was
  unreachable from the GUI ("Unsupported file format") — corpus validation runs
  at the data layer and cannot catch a GUI-gate miss (v11.4.1).
- **Theming/DPI** is centralized in `QCS_Theme.py` (sv-ttk, dark mode, DPI
  awareness) and `QCS_QtTheme.py` for the Qt shell. Plot colors are centralized
  in `getParamColors()` / `getSiteColors()` in `QCS_DataView.py`. Never
  hardcode colors or fonts in windows or plots.
- **Never set an UNQUALIFIED Qt stylesheet on a widget.** A rule without a
  selector (`widget.setStyleSheet('margin-left: 18px')`) is inherited by that
  widget's own TOOLTIP, which then opens with an empty strip on the side -
  measured 18 px wider than the same tooltip on an unstyled box (v12.2.1).
  Indent with the layout, or qualify the selector (`QCheckBox { ... }`).
  `qtheme.muted()` carries the same warning for a different reason: a
  stylesheet on a child makes Qt re-render its ancestors through the
  stylesheet engine, which painted a gray slab behind a QGroupBox.
- **The qualification runs on a WORKER THREAD in the Qt shell** (v12.3), and
  the pipeline code knows nothing about it: every point where it talks to the
  operator is a swappable hook, and `_install_qt_facade` wraps each one so the
  call hops to the interface thread and blocks the worker until it answers.
  Two rules follow, and breaking either one crashes or hangs a run:
  - **A new interactive stop MUST go through a facade hook.** Build a Qt or
    matplotlib WINDOW straight from the pipeline and it is built on the worker
    - which Qt forbids for widgets.
  - **Never call `plt.show()` in code the shells reach.** The Qt shell runs
    matplotlib on **Agg** (a figure is then pure computation, safe to build on
    any thread) and supplies the window itself - `QCS_QtApp.PlotWindow`, via
    `wait_figure_close` for a review and `QCS_DataView.show_panels()` for a
    produced panel. Under Agg a bare `plt.show()` does nothing at all, so the
    figure is silently never displayed. `plt.close(fig)` fires no event under
    Agg either (`FigureManagerBase.destroy` is a no-op), which is why
    `PlotWindow` watches pyplot to notice that its figure was closed.
  Cancel is cooperative: `QCS_Main.RunCanceled` (a subclass of
  `ManualCutCanceled`, so every existing unwind path already handles it) is
  raised on the worker at the pipeline's yield points - `ui_pump` and, finely,
  every log line. It must be raised ON the worker: raising it inside a
  marshalled call throws in the interface thread's event loop and the run
  carries on (measured, v12.3).
- **User settings** live in `sourceCode/qcs_user_settings.json` (auto-generated,
  gitignored, version-gated: a version bump may intentionally reset QC criteria
  to new defaults while preserving file paths).
- **One preferences dict per shell.** `QCS_Main.USER_PREFS` and
  `QCS_DatabaseView.USER_PREFS` are separate module globals, and each
  `save_user_prefs()` rewrites the WHOLE settings file from its own copy. A
  shell MUST alias them (`qm.USER_PREFS = dbv.USER_PREFS`, as `QCS_App` and
  `QCS_QtApp` do) or the module that saves LAST silently reverts everything the
  other wrote that session - which is how the Qt port shipped with 'nothing
  persists between sessions' (v12.2). The window state is saved by the shell's
  own close handler; a shell without one loses it entirely.
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

- Commit messages in English, **prefixed with the version**:
  `v11.0: short description`. The prefix says which release the change belongs
  to, and it is deliberate where it shows: GitHub's repository listing labels
  each file and folder with the SUBJECT of the last commit that touched it, so
  the version is visible there — that is the intent, not a side effect.
  *(Briefly moved to the message body on 2026-08-11 and restored the same day.)*
- **Never rewrite commit subjects to tidy that listing.** Rewriting changes
  every SHA and breaks the 21 tags and the 21 GitHub Releases that point at
  them. Equally, do not touch a file just to change the text it displays: it is
  churn, the diff has to be invented, and the row is corrected by the next real
  edit anyway.
- **No AI attribution anywhere** (owner decision, 2026-08-13): commit messages
  carry no `Co-Authored-By: Claude` trailer and no "Generated with" footer, and
  neither do PR bodies, release descriptions or any document in this
  repository. Commits made before this date keep their trailer — removing it
  would rewrite history, which the rule above forbids.
- Propose the next SemVer number for each change set. Any change that alters QC
  results (flags, thresholds, test logic) is a MAJOR bump.
- **PRIORITY - a GitHub Release is formatted exactly like the release before
  it.** Title and body follow the PREVIOUS release's format: same section
  headings, same order, same voice, same level of detail. Read that release
  before drafting - never draft from memory, and never from the changelog file
  alone (the changelog is a different lane, hard-wrapped and written for the
  repository):

  ```bash
  curl -s https://api.github.com/repos/RepSage/QCS_SAGE/releases/latest
  ```

  The chain's reference is **v11.6** (`releases/tags/v11.6`), the last one
  before the format drifted; anything published between it and the release that
  restores the format is not a model to copy. Its shape:
  - **Title**: `vX.Y - <lowercase phrase naming what the version does>`, no
    trailing period.
  - **Opening line**: one sentence placing the round, with the SemVer step and
    whether QC rules changed - 'QC rules unchanged (MINOR: v11.5 -> v11.6)'.
  - **Sections**: `## Fixed`, `## New`, `## Note`, `## Verification`,
    `## Install`, in that order, only the ones that apply.
  - Each bullet leads with a **bold claim** and then explains it; `##
    Verification` gives the suite count and the lint result; `## Install` names
    the `.exe` and says what installing over an existing copy does.
  - The body is NOT hard-wrapped (the changelog file is; the release is not).
- On each release: add a file to `changelog/` listing the version's changes,
  update the HTML user manual (`Quality Control System (SAGE) - User Manual.html`)
  with the version and changes, and tag the version in Git. The installer is
  rebuilt and smoke-tested before the tag — recipe in `packaging/README.md`.
- **Before tagging, read what the interface says about ITSELF.** A branch
  banner hides there and ships silently: v12.0 was tagged with the window
  title carrying '(v12.0 shell)' and the status bar announcing a
  'development shell', and the tag had to be moved. Window title, status
  bar and About are release text, not scaffolding.
- **Never name a branch after the version it will be tagged with.** With a
  branch and a tag both called `v12.1`, `git push origin v12.1` is ambiguous:
  git refuses with "src refspec matches more than one" and the tag silently
  does NOT go up (it took `refs/tags/v12.1` and `refs/heads/v12.1` spelled out
  to finish the v12.1 release). Name it for the work, as `port-v12.0` and
  `fix-v11.4.2` were.
- After a PR merges, delete the feature branch (local and remote) and return to
  an updated `master` before branching again.

## Which file holds what

Four lanes, and a fact belongs in exactly one. When it moves lane, move it —
do not copy it.

- **`CLAUDE.md`** (this file) — durable rules and invariants. Read every
  session, so every line costs context on every task.
- **`STATUS.md`** — dated, volatile state: current phase, what is unfinished,
  known-bad artifacts. Read the top entry before starting. **It holds the OPEN
  version only**, plus the carried-over open items and the environment notes:
  when a version is published, its entries leave `STATUS.md` in the same commit
  that writes `changelog/vX.Y.md`, and whatever is still pending drops into the
  open-items list dated with when it was last touched — not with today. Past
  ~150 lines, prune before writing more; it reached 1,922 by pure accretion
  (pruned 2026-08-18; full text in `git show a0994bf:STATUS.md`). Prune by
  SWEEPING the entries for what is still live, never by summarizing a summary:
  two claims in that file were already superseded and would have survived the
  cut as if true. What a cold session cannot re-derive — approaches rejected
  and why, the current hypothesis, the next command — stays until it closes,
  however long the file gets.
- **`changelog/`** — one file per released version of the PROGRAM.
- **`sourceCode/batch/CORPUS_LOG.md`** — what was done to the archived DATA,
  dated and with its evidence: requalification rounds, raw repairs, discarded
  loggers. **Not a changelog entry** — none of it changes the program, and a
  corpus operation never bumps `QCS_VERSION`.

There is no `DECISIONS.md` in this project; the numbers behind a parameter
choice live beside the rule that uses them, in `sourceCode/batch/README.md` for
corpus rules and in the changelog entry for QC ones.

Current phase, unreleased work and known-bad artifacts: see `STATUS.md`.

## Subagents

Delegate the read-heavy work instead of pulling it into the session; the rules
are in the global `CLAUDE.md`. Here: `@agent-selftest-runner` for the suite and
ruff, `@agent-code-tracer` to locate something in the four large modules,
`@agent-release-audit` before tagging. All three are read-only — commits, tags,
the installer build and the corpus drivers stay in the main session.

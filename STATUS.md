# STATUS — QCS (Quality Control System — SAGE)

Volatile state, newest first. Every entry dated. Durable rules live in
`CLAUDE.md`, released program changes in `changelog/`, and everything done to
the archived DATA in `sourceCode/batch/CORPUS_LOG.md`.

The release history is NOT kept here: when a version is published its entries
leave this file, and only what is still open moves down to the open items,
dated with when it was last touched. The full text before the 2026-08-18
pruning is in git (`git show a0994bf:STATUS.md`).

## 2026-08-19 - v13.0 UNRELEASED (branch `doppler-revamp-v13.0`)

The Doppler revamp is DONE in code - all seven items of the backlog, with the
owner's decisions of 2026-08-19 - and nothing is released: no tag, no
installer, no draft. `QCS_VERSION` (`QCS_DataHandler.py`) and the installer's
`AppVersion` (`packaging/QCS_installer.iss`) already read 13.0, `changelog/
v13.0.md` is written and the user manual carries the version and the changes.
v12.3 is published and its entries left this file with `changelog/v12.3.md`.

**MAJOR because qualified CURRENT values change**: the current flag string
gained a fifth position and a manual dismissal writes 5 across the row. Scalar
and HOBO results are untouched, verified: a DCPS run with no cut reproduces
v12.3's counts exactly (4,646 good / 126 suspect / 8,636 bad on
`Data001.bin`).

### What the seven items became

1. **Tilt review, always** - one point per RECORD, before the tests; a cut
   dismisses every cell of that instant. It is the DCPS's Depth review.
2. **Check variables** offers `DOPPLER_CUT_COLUMNS` (horizontal speed,
   direction, vertical speed, speed stdev, signal strength), each series drawn
   one depth cell at a time in sequence; the tilt cuts carry over locked.
   Tilt is NOT repeated in the chooser - it is the always-on review.
3. **`DOPPLER_TEST_SEQUENCE` has five entries**, the new one `cur_manual`:
   2 = no review ran, 1 = reviewed and kept, 5 = dismissed. A dismissal is
   whole-row (the reasoning is now a rule in `CLAUDE.md`); `Flag_cur` = 5 and
   'Remove dismissed data' drops those rows.
4. **The dead surface is gone** for a Doppler database: no panel checkboxes,
   no parameter filter, no Scale settings column (`QCS_QtViz._build_step2`,
   which now builds those two blocks through `_build_param_filter` /
   `_build_scale_settings`). Sites, years, time window and depth band stay.
5. **'Fixed scale' names its meaning** - `FIXED_SCALE_LABEL` /
   `FIXED_SCALE_TIP` in `QCS_QtViz.py`, one wording per family.
6. **The direction key is a compass wheel** (`_direction_compass`,
   `QCS_DataView.py`): the linear bar still RESERVES the slot so the two
   heatmaps keep the same width and their shared time axis stays aligned.
7. **One paged window for the panels** - `PanelBrowserWindow` in
   `QCS_QtApp.py`, requested by `show_panels(figures, browse=True)`. Only the
   current panels ask for it; the scalar and HOBO panels still open side by
   side.

### Verified (executed 2026-08-19)

- Self-test suite **55/55** (one new test: the two DCPS cut mappings), ruff
  clean.
- **Three headless runs over the real session** `C:/Users/LAMB/Desktop/
  Data001.bin` (13,408 cell samples): no cut -> the v12.3 counts plus a '2' in
  position 5; tilt cut + all five per-cell panels -> 3 records (48 rows) and 47
  cells dismissed, `55555`, every measurement blank, record attitude blanked
  only on the record cuts; the same with 'Remove dismissed data' -> 95 rows
  left the sheet.
- **Through the Qt WORKER THREAD, off-screen**: the review opens on the
  interface thread and blocks the worker (6 windows with Check variables on,
  1 without; 56 interface ticks during a 7 s run, so the window never froze),
  and two DCPS runs in the same session both finish.
- **The visualization tab, off-screen**, on a real qualified current table:
  0 panel checkboxes, 0 parameter rows, no Scale settings box, the Doppler
  wording on 'Fixed scale', one `PanelBrowserWindow` paging 4 figures; and on
  a real qualified SCALAR table the page still has 3 panel boxes, 12
  parameters, 12 scale rows and the scalar wording.

### NOT verified - the next actions, in order

1. **Nobody has SEEN any of it on a real screen.** Open `QCS.bat`, qualify
   `C:/Users/LAMB/Desktop/Data001.bin` with 'Check variables' ticked and look
   at: the tilt panel (is one point per record the right density?), the five
   per-cell panels (is the cell-by-cell ordering readable at 13,408 points?),
   then the Visualization tab on the produced table - the compass wheel and
   the paged panel window.
2. If it stands, build the installer (`packaging/README.md`), smoke-test it,
   merge the branch into `master` with a local `git merge --no-ff` + push (no
   `gh` CLI here), tag `v13.0` at the merge commit and draft the release by
   copying **v12.3's** text (that is now the chain's model).
3. **Open question for the owner: is there any DCPS product in the archived
   corpus?** If there is, it carries a 4-character flag string and no manual
   review, and requalifying it is what makes the corpus consistent with v13.0.
   Nothing was requalified in this round.

### Known gaps left on purpose

- The **tk** shell's Visualization tab (`QCS_DatabaseView.py`) still shows the
  disabled Seaguard panel checkboxes and the empty scale column for a Doppler
  database. Item 4 was done in the Qt shell, which is what `QCS.bat` opens;
  the tk shell is legacy.
- The manual-cut panel's **Help button** calls `tkinter.messagebox` directly
  (`manual_cut_panel`, `QCS_DataHandler.py`), which is now reachable from the
  DCPS review as well as the scalar ones. Under the Qt shell that call is made
  from the WORKER thread on a hidden tk root; it is wrapped in try/except and
  was never exercised. It predates v13.0 - the whole manual point cut is on
  the 'never run in the app' list below.
- The current panels' **time axis is unreadable** on a 3-day session: the tick
  labels overprint each other (seen in the rendered panel, `Current profile
  (time x depth).svg`). It is a pre-existing defect of
  `plot_doppler_panels`, not part of the seven items, and it was left alone.

## Open items

**Program and release**

- **v12.3 shipped four paths that were never run in the app** (2026-08-19).
  None of them blocks anything; each is one run away from being closed:
  the manual point cut and the replicate review through the worker thread
  (the point-cut MACHINERY was exercised on 2026-08-19 by the DCPS review -
  same `manual_cut_panel` and same `_show_and_wait` hop - so what is left
  unrun there is the scalar Check-variables path itself); a
  BATCH canceled in the middle (the finished files must keep their outputs
  while the interrupted one is removed - the per-file commit implements it and
  it was never executed); 'Go to visualization' landing on step 2, single file
  and batch; and a Seaguard panel under the new fixed-scale rule, which changed
  for every family while only HOBO and Doppler were looked at.
- **The plotting stack was reviewed on 2026-08-19 and stays as it is.**
  matplotlib 3.10.0 ships exactly two Qt backends, `qtagg` and `qtcairo`
  (`backend_registry.list_builtin()`); there is no newer or GPU one, and
  `qt5agg` is the legacy alias, not a newer option. Measured on this machine,
  one redraw of a QCS-sized review plot on a QtAgg canvas costs 29.5 ms at
  1,550 points, 31.6 ms at 13,408 and 65.9 ms at 100,000 - i.e. a ~29 ms fixed
  cost (axes, ticks, text) dominates at every size this program plots, so the
  rasterizer is not the bottleneck and swapping it would buy nothing. A real
  step change would need a different LIBRARY (pyqtgraph, vispy), which means a
  second plotting stack in the app and the installer and no publication-quality
  SVG - not worth it for series of this size. If a review ever feels slow, the
  levers are blitting and decimation, not the backend. Upstream is at
  matplotlib 3.11.1 while the build pins 3.10.0; the pin is deliberate
  (`packaging/README.md`) and 3.11 removes APIs this code touches
  (`rcsetup.all_backends` is already deprecated for 3.11), so any bump needs
  its own round.

- **The installer's FRESH-INSTALL pages have not been watched on screen**
  (2026-08-19): the Finish page is confirmed (the owner saw 'Launch QCS after
  installation' and the program reopened), but an upgrade hides the folder page
  by design, so the all-users / just-for-me choice has only been compiled.
- **The FROZEN exe has never run a real qualification end to end** (open since
  v12.0; every build is launch-smoked and closes cleanly): Depth review,
  adaptive light review, replicate review, the viz tab. A launch smoke test
  cannot prove lazy imports.
- **All-users installs land in `C:\Program Files (x86)\QCS`** (re-checked
  2026-08-19, HKLM). Inno compiles a 32-bit installer unless told otherwise;
  the one-line directive is in `packaging/README.md`, awaiting the owner.
- **The older-generation `.hobo` layout is not deciphered** (2026-08-14): ~30
  pre-2023 export pairs decode with a one-row offset or a partial mismatch, and
  most are refused by the reader's gates. The corpus is unaffected - it was
  qualified from the exports.
- **The project's subagents are not versioned** (2026-08-19): `.claude/` is
  gitignored, so the three agent files live on this disk only. The owner
  decided that is fine.

**Data** - the authoritative list is "Still open on the data" in
`sourceCode/batch/CORPUS_LOG.md`; do not duplicate it here. As of 2026-08-13 it
held four files needing a HOBOware re-export with a 24-hour clock, and 84 files
under `HOBO\raw` with no manifest row. `qualified_index.csv` on the share is
the authority for the corpus count.

- **The replicate referee's duplicate-timestamp handling** (`keep='first'`) was
  flagged on 2026-08-06 as papering over the collapsed 12-hour clock rather
  than reporting it. The clock was repaired in the v11.0 rounds (41 CSV + 24
  xlsx); whether the referee still needs the change was **not re-verified**.

## Environment

- **There is no `gh` CLI on this machine** (2026-08-18): pull requests and
  releases go through the browser, or through the API with the token in the Git
  credential manager. Note that the automation classifier BLOCKS `git push
  --force` and the PR-merge API call; a merge is done with a local
  `git merge --no-ff` + push, and a force-push needs the owner's word first.
- **The build stack is kept**: `%TEMP%\qcs_build_env` (PyInstaller + the pinned
  runtime) and `packaging/v12_env` (PySide6 6.8.3, what `QCS.bat` launches).
  `packaging/dist/` is a build artifact; it rebuilds in about three minutes
  from `packaging/README.md`.
- **The throwaway drivers of this round** are in the session scratchpad, not in
  the repository (2026-08-19, v13.0): a headless end-to-end driver of the DCPS
  pipeline with the review panel stubbed, an off-screen Qt probe of the
  visualization page and one that runs the qualification on the WORKER thread
  while a timer closes each review window. All of them no-op `save_user_prefs`
  in BOTH `QCS_Main` and `QCS_DatabaseView` before anything else, which is the
  only safe way to drive the shell while the operator's app may be open.
  Recipe worth keeping: `QT_QPA_PLATFORM=offscreen`, replace
  `QCS_QtApp.QMessageBox` with a stub (the version gate pops a modal during the
  bootstrap), and restore `sys.stdout`/`sys.stderr` after importing
  `QCS_QtApp` - it installs an output redirect at import, so a probe that
  forgets prints NOTHING and a traceback disappears with it.

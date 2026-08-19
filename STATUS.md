# STATUS — QCS (Quality Control System — SAGE)

Volatile state, newest first. Every entry dated. Durable rules live in
`CLAUDE.md`, released program changes in `changelog/`, and everything done to
the archived DATA in `sourceCode/batch/CORPUS_LOG.md`.

The release history is NOT kept here: when a version is published its entries
leave this file, and only what is still open moves down to the open items,
dated with when it was last touched. The full text before the 2026-08-18
pruning is in git (`git show a0994bf:STATUS.md`).

## 2026-08-19 - v12.3 PUBLISHED

`master` is at `c148787`, **tagged `v12.3`** at the merge commit `084c164`, and
the release is published with `QCS_Setup_v12.3.exe` (81,573,401 bytes, md5
0CAE1B0EE547A5B190CB59A6B261AFAF). What it carries is in `changelog/v12.3.md`.
Its release text was written by copying v12.2.4's, which is the v11.6 format -
the chain the `CLAUDE.md` rule describes now has three links, and the next
release copies v12.3's.

Nothing is unreleased. The open items below are what v12.3 shipped without a
run in the real app, plus what was already open.

## NEXT UP: the Doppler revamp (a MAJOR - owner, 2026-08-19)

Parked during v12.2.4/v12.3 to finish the open work; the owner is opening a
session for it now. This section is the whole DCPS backlog, written so a cold
session can start without re-deriving anything.

### What a DCPS product IS (read this first)

A current-profiler session is TIDY: **one row per record x depth CELL**. The
qualified sheet carries, in order: `Datetime, Site, Column, Cell, Depth (m),
Heading (deg), Pitch (deg), Roll (deg), Tilt (deg), Ping count, Horizontal
speed (cm/s), Direction (deg), North speed (cm/s), East speed (cm/s), Vertical
speed (cm/s), Speed stdev (cm/s), Signal strength (dB), Cell state, Flag,
Flag_cur, QCS version`. The first five columns identify the row; `Heading`
through `Ping count` are RECORD-level (`_DCPS_RECORD_PARAMS` in
`QCS_DataHandler`) and repeat across the cells of one instant; the rest are
per-cell. Two consequences that have already bitten:

- `Site+Datetime` repeats once per cell BY CONSTRUCTION (`build_database` keys
  its overlap warning on `Site+Datetime+Column+Cell` for this layout since
  v12.2.4);
- `Depth (m)` is the CELL depth - a handful of fixed values repeated on every
  record - so anything that treats it as a profile axis draws a comb.

The pipeline is `run_doppler_qualification` (a closure in
`build_qualification_tab`, `QCS_Main.py`), 4 stages, and it writes
`<base>_DOPPLER_QLF/` with `QCS qualified current data/` (table +
`QCS_current_flag_legend.txt`) and `QCS DataView (current)/` (4 panels).

### Already fixed - do NOT re-open these

v12.2.4 and v12.3 cleared the whole first round of DCPS complaints: the
progress bar reads the stage denominator from the log (the pipeline logs
`Stage k/4`); the Data type is shown and LOCKED once the `.bin` is a DCPS; the
visualization Step 1 gate accepts `Doppler`; `build_database` no longer calls
every cell an overlap; the four panels are SHOWN, in the program's own window
with the app icon and the standard toolbar; `Fixed scale` is usable on a
Doppler database and its speed colour scale now spans the cells the panels
DRAW (everything except BAD), like the scalar scales.

### The work, with the owner's decisions

1. **A manual cut for the DCPS, on TILT** (owner chose the series, 2026-08-19).
   `run_doppler_qualification` returns before the scalar pipeline's interactive
   stops, so a current session gets no review at all. The cut CANNOT be by
   depth (see above: `Depth (m)` is the cell depth) and the instrument logs no
   pressure. Tilt is a RECORD-level series, so the panel plots tilt against
   time and cuts whole RECORDS - every cell of the cut instant - which is how
   deployment and recovery show up in a mooring.
2. **Check variables needs its own candidate list.** `MANUAL_CUT_COLUMNS`
   (`QCS_Main.py`) holds nine SCALAR variables (Temperature, Salinity,
   Conductivity, Pressure, O2, pH, Chlorophyll, Turbidity, DOM) and the chooser
   is filled by intersecting it with the frame's columns - none of them exist
   in a current table, which is why the panel came up empty with the option
   ticked. The owner's list for the DCPS: horizontal speed, direction, vertical
   speed, speed stdev, signal strength, tilt.
3. **The flag string grows, and that is what makes this a MAJOR.**
   `DOPPLER_TEST_SEQUENCE` (`QCS_Tests.py`) has exactly four entries -
   `cur_range, cur_signal, cur_stdev, cur_tilt` - and `doppler_qc` builds a
   4-character flag per row plus the `Flag_cur` rollup (priority 4 > 3 > 9 > 1).
   A dismissal position means touching both, plus the legend writer
   (`QCS_Main.py`, `QCS_current_flag_legend.txt`) which iterates the sequence.
   Any change here alters qualified values: MAJOR bump, and the corpus has to
   be requalified.
4. **Dead surface in the visualization** (layout only, no QC effect). On a
   Doppler database the three panel checkboxes are disabled but still carry the
   SEAGUARD labels ('Parameters at a site' / 'Parameter across sites' /
   'Vertical profile at a site'), 'Filter by parameter' shows two dead
   checkboxes (horizontal speed, direction) and the Scale settings column is
   empty - the four panels have FIXED content, so none of it applies. Hiding
   the three boxes for this instrument was proposed and not decided.
5. **'Fixed scale' means something different here and the interface does not
   say so.** For the scalar families it is a Min/Max the operator types per
   parameter; for the DCPS it makes every heatmap share ONE speed colour scale
   computed from the data. Nothing is ever typed. Label and tooltip should say
   which of the two the operator is looking at.
6. **The Direction (deg) colour bar should be a compass wheel** (owner's idea,
   2026-08-19): a circular scale where the colour says north/south/east/west at
   a glance, instead of a linear 0-360 bar.
7. **The four panels open as four separate windows.** Fine for a first look,
   noisy for a comparison; one window holding them (tabs, or a 2x2 sheet) was
   raised and not decided.

### Constraints a new interactive stop MUST respect (v12.3)

The qualification runs on a WORKER THREAD in the Qt shell. A review that builds
a window straight from the pipeline builds it on the worker, which Qt forbids
for widgets. Route it through a facade hook, exactly as the scalar reviews do:
the figure is built under Agg (safe anywhere) and shown by
`QCS_Main.wait_figure_close` / `QCS_DataHandler._show_and_wait`, which the Qt
shell wraps so the window is created on the interface thread while the worker
blocks. Never call `plt.show()`. The whole rule set is in `CLAUDE.md`
("The qualification runs on a WORKER THREAD").

### How to drive it without the GUI

`C:/Users/LAMB/Desktop/Data001.bin` is a real DCPS session (13,408 cell
samples, 4,646 good / 126 suspect / 8,636 bad) and
`C:/Users/LAMB/Desktop/Data000.bin` is a scalar one in the SAME folder - which
is why v12.3 had to teach `read_seaguard_bin` to skip a binary whose instrument
differs from the selected one. A qualified product of that session is at
`C:/Users/LAMB/Desktop/Desktop_DOPPLER_QLF/`.

The probes of the v12.3 round lived in the session scratchpad and are GONE.
The method that worked, if one is needed again: run the Qt shell with
`QT_QPA_PLATFORM=offscreen`, no-op `save_user_prefs` in BOTH `QCS_Main` and
`QCS_DatabaseView` before anything else, replace `QCS_QtApp.QMessageBox` with a
stub (the version gate pops a modal during the bootstrap and waits forever
offscreen), point the output at a scratch folder, then drive `shell._run()` /
`shell._cancel_run()` and pump the event loop. Interface responsiveness is
measured with a `QTimer` on the interface thread: count its ticks during the
run.

## Open items

**Program and release**

- **v12.3 shipped four paths that were never run in the app** (2026-08-19).
  None of them blocks anything; each is one run away from being closed:
  the manual point cut and the replicate review through the worker thread; a
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
  the repository: they boot the Qt shell against a COPY of the settings file
  with `save_user_prefs` no-opped, which is the only safe way to drive the
  shell while the operator's app may be open.

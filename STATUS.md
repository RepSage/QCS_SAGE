# STATUS — QCS (Quality Control System — SAGE)

Volatile state, newest first. Every entry dated. Durable rules live in
`CLAUDE.md`, released program changes in `changelog/`, and everything done to
the archived DATA in `sourceCode/batch/CORPUS_LOG.md`.

The release history is NOT kept here: when a version is published its entries
leave this file, and only what is still open moves down to the open items,
dated with when it was last touched. The full text before the 2026-08-18
pruning is in git (`git show a0994bf:STATUS.md`).

## 2026-08-19 - v12.2.4 RELEASED; draft waiting for Publish

`master` is at `77689eb`, **tagged `v12.2.4` there** and pushed (78 tag refs on
the remote). What the version carries is in `changelog/v12.2.4.md`; v12.2.3 and
everything before it is published.

The GitHub release is a **DRAFT waiting for the owner to press Publish** -
release id **373305022**, name 'v12.2.4 - the Doppler run says where it is, and
its database opens', asset `QCS_Setup_v12.2.4.exe` uploaded (81,566,595 bytes,
md5 DC9463807663DB4D901BAEE76D221869; body also on the Desktop as
`RELEASE_v12.2.4.md`). It is the FIRST release written to the restored v11.6
format - `## Fixed / ## Note / ## Verification / ## Install`, unwrapped - which
`CLAUDE.md` now requires; the next release copies THIS one.

Built and gated before the tag: suite 54/54, ruff clean, PyInstaller bundle
rebuilt with `--clean` (287 MB onedir), installer compiled, and the frozen exe
launch-smoked - window title read 'QCS - Quality Control System (SAGE) -
v12.2.4', closed cleanly, no crash log.

**Still unproven on screen**: the three interface fixes (progress bar on a DCPS
run, the locked Data type, the panels appearing) were verified in code and, for
the visualization, on the real qualified DCPS file outside the interface - the
owner's own end-to-end run is what closes them.

## PARKED: the Doppler revamp (a later MAJOR - owner, 2026-08-19)

Not next. The owner chose to finish the open work first; this section is
the whole DCPS backlog, kept because a cold session cannot re-derive it.

The same DCPS test showed two ABSENCES, not bugs: `run_doppler_qualification`
(`QCS_Main.py`) returns before everything the scalar pipeline does, so a
current session gets no Depth review and no Check variables panels. Both are
v13.0, together with the worker thread, because they add a manual dismissal to
the Doppler flag string - that is a QC-result change, hence MAJOR.

What a session picking this up must know:

- **The cut cannot be by depth.** The Doppler frame's `Depth (m)` is the CELL
  depth: N fixed values repeated on every record, so `trim_by_depth` would plot
  a comb, not a deployment profile. And the DCPS logs no pressure - its
  record-level parameters are heading, pitch, roll, tilt and ping count
  (`_DCPS_RECORD_PARAMS`, `QCS_DataHandler.py`).
- **The owner chose TILT as the series** for the time-based review (2026-08-19):
  the panel plots tilt against time and cuts whole RECORDS - every cell of the
  cut instant - which is how deployment and recovery show up in a mooring.
- **Check variables gets its own candidate list** for the Doppler (owner,
  2026-08-19): horizontal speed, direction, vertical speed, speed stdev, signal
  strength, tilt. `MANUAL_CUT_COLUMNS` (`QCS_Main.py:1556`) holds scalar
  variables only, none of which exist in a current table - which is why the
  chooser came up empty even with the option ticked.

The owner parked the whole Doppler revamp on 2026-08-19 ("deixar pra MAJOR
posterior") to finish what is already open. What the DCPS test found, all
still true, none of it started:

- **Dead surface on a Doppler database.** The three panel checkboxes carry the
  SEAGUARD labels ('Parameters at a site' / 'Parameter across sites' /
  'Vertical profile at a site', the `else` branch of the label block in
  `build_step2`) and are all disabled: the four current panels are implicit, so
  no panel is a choice. Same for 'Filter by parameter' (two dead checkboxes,
  horizontal speed and direction) and the whole Scale settings column. Hiding
  the three boxes for the Doppler is layout only, no QC effect.
- **'Fixed scale' means something else here** and the interface does not say
  so: for the scalar families it is a Min/Max the operator types per parameter;
  for the Doppler it makes every heatmap share ONE speed color scale, computed
  from the data (`max GOOD speed x 1.05` in `generatePanels`). Nothing is ever
  typed, which is why Scale settings stays empty with it ticked -
  `toggle_scale_controls` also gates on a panel being selected, and a Doppler
  has none. Label and tooltip should say which of the two it is.
- **The panels open as separate matplotlib windows with no app icon** (owner
  noticed once they became visible, 2026-08-19). That is matplotlib's own
  window, not a QCS one - it affects every panel family, not just the Doppler.
- **The Direction (deg) color bar should be a compass wheel** (owner's idea,
  2026-08-19): a circular scale where the color says north/south/east/west at a
  glance, instead of a linear 0-360 bar.
- **The flag string grows**: `DOPPLER_TEST_SEQUENCE` (`QCS_Tests.py`) has four
  entries and `doppler_qc` builds a 4-character flag per row. A dismissal
  position means touching both, plus the legend writer (it already iterates the
  sequence) and `Flag_cur`.

## Also on the table: 'Go to visualization' landing on Step 2 (owner, 2026-08-19)

Today the post-run button only switches tab and `apply_prefill` forces Step 1
(deliberately: landing on the Step 2 of an OLDER database was the v12.0 bug).
Making it advance means calling `_next()` after the prefill. The owner's answer
to the batch case is to hand the WHOLE batch over and let Step 1 build one
unified database from it - which needs the batch loop to accumulate the output
paths (today `OUTPUT['last_qualified_file']` is reset per file,
`QCS_Main.py:978`, so only the last survives), `PENDING_VIZ_PREFILL` to carry
the list plus a default database name (validation demands a name when more than
one file is selected), and the knowledge that this WRITES the unified xlsx to
`<output>/DatabaseView/`. Do it after the worker thread: building N databases
on the interface thread is exactly the freeze the thread is meant to remove.

## 2026-08-19 - v12.3 RELEASED; draft waiting for Publish

PR #36 merged by the owner; `master` is at `084c164`, **tagged `v12.3` there**
and pushed. What the version carries is in `changelog/v12.3.md`; v12.2.4 and
everything before it is published.

The GitHub release is a **DRAFT waiting for the owner to press Publish** -
release id **373358963**, name 'v12.3 - the window stays alive while it
qualifies', asset `QCS_Setup_v12.3.exe` uploaded (81,573,401 bytes, md5
0CAE1B0EE547A5B190CB59A6B261AFAF; body also on the Desktop as
`RELEASE_v12.3.md`). Written in the v12.2.4 format, which is the v11.6 one -
the rule in `CLAUDE.md` is now a chain, and the next release copies THIS one.

Built and gated before the tag: suite 54/54, ruff clean, version reading v12.3
in all three places (`QCS_VERSION`, the installer's `AppVersion`, the manual),
no development banner in the interface, no AI attribution, bundle rebuilt with
`--clean`, and the frozen exe launch-smoked - window title read 'QCS - Quality
Control System (SAGE) - v12.3', closed cleanly, no crash log.

**What v12.3 still owes a real run** (none of it blocks the release; all of it
is in the app, not in the code):

- the manual point cut and the replicate review through the worker thread;
- a batch canceled in the middle - the finished files must keep their outputs
  while the interrupted one is removed (the per-file commit implements it, it
  was never executed);
- 'Go to visualization' landing on step 2, single file and batch;
- a Seaguard panel under the new fixed-scale rule (it changes every family,
  and only HOBO and Doppler were looked at).

## PARKED: the Doppler revamp (a later MAJOR - owner, 2026-08-19)

Not next. The owner chose to finish the open work first; this section is
the whole DCPS backlog, kept because a cold session cannot re-derive it.

The same DCPS test showed two ABSENCES, not bugs: `run_doppler_qualification`
(`QCS_Main.py`) returns before everything the scalar pipeline does, so a
current session gets no Depth review and no Check variables panels. Both are
v13.0, together with the worker thread, because they add a manual dismissal to
the Doppler flag string - that is a QC-result change, hence MAJOR.

What a session picking this up must know:

- **The cut cannot be by depth.** The Doppler frame's `Depth (m)` is the CELL
  depth: N fixed values repeated on every record, so `trim_by_depth` would plot
  a comb, not a deployment profile. And the DCPS logs no pressure - its
  record-level parameters are heading, pitch, roll, tilt and ping count
  (`_DCPS_RECORD_PARAMS`, `QCS_DataHandler.py`).
- **The owner chose TILT as the series** for the time-based review (2026-08-19):
  the panel plots tilt against time and cuts whole RECORDS - every cell of the
  cut instant - which is how deployment and recovery show up in a mooring.
- **Check variables gets its own candidate list** for the Doppler (owner,
  2026-08-19): horizontal speed, direction, vertical speed, speed stdev, signal
  strength, tilt. `MANUAL_CUT_COLUMNS` (`QCS_Main.py:1556`) holds scalar
  variables only, none of which exist in a current table - which is why the
  chooser came up empty even with the option ticked.

The owner parked the whole Doppler revamp on 2026-08-19 ("deixar pra MAJOR
posterior") to finish what is already open. What the DCPS test found, all
still true, none of it started:

- **Dead surface on a Doppler database.** The three panel checkboxes carry the
  SEAGUARD labels ('Parameters at a site' / 'Parameter across sites' /
  'Vertical profile at a site', the `else` branch of the label block in
  `build_step2`) and are all disabled: the four current panels are implicit, so
  no panel is a choice. Same for 'Filter by parameter' (two dead checkboxes,
  horizontal speed and direction) and the whole Scale settings column. Hiding
  the three boxes for the Doppler is layout only, no QC effect.
- **'Fixed scale' means something else here** and the interface does not say
  so: for the scalar families it is a Min/Max the operator types per parameter;
  for the Doppler it makes every heatmap share ONE speed color scale, computed
  from the data (`max GOOD speed x 1.05` in `generatePanels`). Nothing is ever
  typed, which is why Scale settings stays empty with it ticked -
  `toggle_scale_controls` also gates on a panel being selected, and a Doppler
  has none. Label and tooltip should say which of the two it is.
- **The panels open as separate matplotlib windows with no app icon** (owner
  noticed once they became visible, 2026-08-19). That is matplotlib's own
  window, not a QCS one - it affects every panel family, not just the Doppler.
- **The Direction (deg) color bar should be a compass wheel** (owner's idea,
  2026-08-19): a circular scale where the color says north/south/east/west at a
  glance, instead of a linear 0-360 bar.
- **The flag string grows**: `DOPPLER_TEST_SEQUENCE` (`QCS_Tests.py`) has four
  entries and `doppler_qc` builds a 4-character flag per row. A dismissal
  position means touching both, plus the legend writer (it already iterates the
  sequence) and `Flag_cur`.

## Also on the table: 'Go to visualization' landing on Step 2 (owner, 2026-08-19)

Today the post-run button only switches tab and `apply_prefill` forces Step 1
(deliberately: landing on the Step 2 of an OLDER database was the v12.0 bug).
Making it advance means calling `_next()` after the prefill. The owner's answer
to the batch case is to hand the WHOLE batch over and let Step 1 build one
unified database from it - which needs the batch loop to accumulate the output
paths (today `OUTPUT['last_qualified_file']` is reset per file,
`QCS_Main.py:978`, so only the last survives), `PENDING_VIZ_PREFILL` to carry
the list plus a default database name (validation demands a name when more than
one file is selected), and the knowledge that this WRITES the unified xlsx to
`<output>/DatabaseView/`. Do it after the worker thread: building N databases
on the interface thread is exactly the freeze the thread is meant to remove.

## 2026-08-19 - v12.3 ON A BRANCH: the worker thread, in review

Branch `worker-thread-v12.3`, pull request open, **not merged, not tagged, no
installer, no release**. `QCS_VERSION`, the installer's `AppVersion` and the
manual all read v12.3; the changes are listed in `changelog/v12.3.md`. Suite
54/54, ruff clean. What it carries:

- **The qualification runs off the interface thread** (`_RunThread` in
  `QCS_QtApp`), and the pipeline was NOT rewritten for it: every hook in
  `_install_qt_facade` is wrapped by `_on_gui`, which hops the call to the
  interface thread through `_GuiBridge` (a queued signal plus a semaphore the
  worker blocks on) and re-raises there whatever the call raised. That is why
  a canceled dialog still raises INSIDE the pipeline, as before.
- **matplotlib moved to Agg** in the Qt shell, because under QtAgg every figure
  is a QWidget and Qt forbids building one off the interface thread - the
  pipeline builds figures constantly, not only at the interactive stops. The
  shell now supplies the window itself: `PlotWindow` (canvas + navigation
  toolbar + app icon + the title `style_plot_window` already passed).
- **`plt.show()` is gone from the reachable code**: `QCS_DataView.show_panels()`
  is the hook, `plt.show()` for the tk shell and the batch drivers, PlotWindow
  for the Qt one. This is also what puts the app icon on the visualization
  panels, which never had it.
- **Cancel** (`QCS_Main.RunCanceled`, subclass of `ManualCutCanceled` so every
  existing unwind path takes it) raised at `ui_pump` and at every log line.

Measured, offscreen, with the operator's own `Data001.bin` (probes in the
session scratchpad, `save_user_prefs` no-oped, output to the scratchpad):

- a full DCPS qualification on the worker: 15.4 s, **219 interface-thread timer
  ticks during it** (a frozen window shows ~0), all six output files written,
  `collect_input_settings` confirmed to have executed on the interface thread;
- Cancel pressed 2 s in: the run stopped at **2.1 s** instead of 15.4 s, logged
  'Qualification canceled by the user (Cancel).', and wrote **no files**;
- the interactive mechanism in isolation: a figure built ON the worker, its
  window created on the interface thread, the worker blocked exactly as long as
  the window stayed open (1.59 s), and `ui_ask_yes_no` answered back.

Second round on the owner's HOBO test (2026-08-19), all in the same tree:

- **No wait cursor while a run is on the worker.** It said the opposite of what
  is true now - the window is live and Cancel is there to be clicked - so it is
  set only when `qm.THREADED` is False (the tk shell).
- **'Reset view' came back.** Regression of the Agg move: `enable_scroll_zoom`
  customizes `fig.canvas.manager.toolbar`, which under Agg is None, so the
  whole v12.1 Qt branch was silently skipped and the panels lost the button.
  The figure now carries the reset closure and `PlotWindow` applies the same
  customization to the toolbar it builds.
- **'Go to visualization' lands on Step 2.** Only that button does it (the tab
  bar still lands on Step 1); a batch hands over ALL its qualified files plus a
  default database name, so Step 1 can build one unified database from the run
  instead of opening its last file.
- **The fixed-scale default now spans every value the panel DRAWS**
  (`_param_data_extreme`), not only the approved ones. Measured on the owner's
  HOBO file: the old rule (flags 1/2 plus 20%) gave 25.072-30.884 degC and left
  6 SUSPECT points between 24.690 and 25.029 outside the axis, drawn nowhere;
  the new one gives 23.617-31.127 and **0 points outside**. The owner's
  reasoning decided it: the qualified sheet already reflects what he chose to
  remove, so a scale that hides what survived is wrong. The trade the old rule
  protected is real and now falls to the operator - a kept extreme (the DOM
  spike of 550 ppb against a good range of 0-6, cited in the old docstring)
  will stretch the scale until Min/Max are typed by hand. This changes PLOTS,
  never a flag or a criterion.
- **Points outside the plotted scale are reported** even so: every panel logs
  how many were not drawn and what to do about it (that series carries 881
  suspect points out of 2127, so a hand-typed scale can still hide many).
- **The scale rule is global, with one exception found and fixed.**
  `_param_data_extreme` is the single source of the Min/Max defaults for every
  scalar parameter of both instruments, so the change reaches all of them. The
  Doppler heatmap colour scale is computed separately
  (`generatePanels`) and still used the GOOD cells only while the panels draw
  everything except BAD - it now uses the same rows they draw.
- **During a run only Cancel is live** (owner, v12.3). `set_busy` disables the
  Input and Output boxes, the settings button, the menu bar and the
  Visualization tab, and puts them all back afterwards. Measured: during the
  run `run=False form=False settings=False menus=False viz=False cancel=True`;
  after it, everything True again. The Visualization tab is in that list for a
  reason - its Generate panels runs on the interface thread and would compete
  with the run.
- **Cancel removes what the interrupted file wrote** (owner asked, v12.3):
  `_claim_output_root` records whether the RUN created the `<name>_QLF` root,
  each finished file commits its own (`_commit_output_root`), and the canceled
  path removes only what is still pending. Two guards, both measured:
  - a root the run CREATED is deleted - canceling a fresh DCPS run left 0 files
    and logged 'Canceled: partial output removed (Desktop_DOPPLER_QLF)';
  - a root that ALREADY EXISTED is never touched - re-qualifying into the
    folder of a previous product and canceling left its 6 files intact, with a
    note saying the folder pre-existed and may now hold files from the canceled
    run. Deleting there would destroy the earlier product.
  The BATCH case (cancel during file 3 keeps files 1-2) follows from the
  per-file commit but was **not executed**. The ERROR path still leaves partial
  files on purpose - its dialog says so, and they are evidence for diagnosis.
- **How fast Cancel bites depends on the logging.** Measured twice on the same
  DCPS session: pressed during a quiet stretch of Stage 3 (writing the xlsx) it
  took effect 10 s later, at the Stage 4 line, with the qualified table already
  written; pressed just before a log line it stopped in 0.1 s. That is what the
  button's tooltip promises ('stops at the next step; what is already written
  stays'), and a finer cancel would need checkpoints inside the writers.
- **One toolbar for every plot window: matplotlib's OWN.** The manual cut
  showed the full default bar and the visualization panels a trimmed one with a
  'Reset view' text button; the owner chose the default bar as the standard
  (2026-08-19) - `Home, Back, Forward, Pan, Zoom, Subplots, Customize, Save`,
  measured identical on both window kinds. The trimming and the text button are
  gone from `enable_scroll_zoom`. What the window adds is one line:
  `toolbar.push_current()` at build time, so the HOUSE button has the opening
  view to return to. Without it Home did nothing after a wheel zoom - the
  navigation stack is filled only by the toolbar's own pan/zoom, and this
  program zooms with the wheel (measured: home after a wheel zoom restores the
  opening view, on a review window and on a panel).

- **A folder holding binaries of DIFFERENT sessions no longer kills the run.**
  `read_seaguard_bin` treats every `DataNNN.bin` of a folder as a part of the
  same session, which is right for a session folder and wrong for a Desktop:
  the owner's `Data000.bin` (scalar) and `Data001.bin` (DCPS) sit together, so
  qualifying the scalar one aborted with 'AADI reader (Data001.bin): ...
  unsupported layout variant', naming a file he never selected. A binary whose
  instrument type differs from the selected one is now skipped with a warning
  that says what to do. Measured: `Data000.bin` decodes 1550 records and the
  full 5-stage qualification finishes.
- **A real interactive review DID run through the worker thread** in that same
  run (the Depth review): one window, built on the interface thread, with the
  worker blocked until it closed. That was the biggest unverified risk.

**Not verified, and this is what a session picking it up must do:**

- **The manual point cut and the replicate review** are still unexercised
  through the thread (the HOBO run covered the light window, the scalar probe
  covered the Depth review).
- **The direct jump to Step 2 has not been run**, single-file or batch.
- **No real interactive review has been driven by a probe.** The Depth review,
  the manual cut, the light-window and replicate reviews were never exercised
  end to end - the Desktop has no valid scalar Seaguard deployment
  (`Data000.bin` and `Data001.bin` share a folder and the reader refuses to mix
  a DCPS sibling into a scalar session), and no HOBO raw file was at hand. Run
  one from the archive: it is the highest-risk path left.
- **Nothing was seen on screen.** Every probe ran on the offscreen Qt platform;
  PlotWindow's appearance, the toolbar and the Cancel button have not been
  looked at.
- The tk shell (`QCS_App.py`) is untouched and still single-threaded; the batch
  drivers and the headless harness never enter the Qt facade.
- A run in progress does not block closing the window yet.

## Open items

**Program and release**

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

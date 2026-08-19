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

## Next: the worker thread (owner asked to try it, 2026-08-19)

The pipeline runs on the interface thread. The window stops repainting during
the heavy stages and a batch started by mistake cannot be aborted; today that
is papered over with `ui_pump()` (`QCS_Main.ui_pump`, `QApplication.
processEvents`) sprinkled through the run. **This item is mine, not a fault the
owner reported** - proposed on 2026-08-17 during the Qt port and deferred then.

What a session picking this up has to know:

- **Entry point**: `QCS_Main.start_qualification()` (validates, then loops over
  the files). The per-file work is `run_full_qualification()`, which today is a
  CLOSURE built inside `build_qualification_tab` - moving it to module level is
  the first step and is useful on its own (it would also let the Qt shell drop
  the hidden-tk bootstrap in `QCS_QtApp._bootstrap_tk_pipeline`).
- **The interactive stops inside a run**, all of which must stay on the GUI
  thread because they build Qt/matplotlib windows: `choose_variables_to_check`,
  the manual point cut panels (`QCS_DataHandler.manual_point_cut` through
  `data._show_and_wait`), the Depth review, `review_light_window`,
  `review_replicates`, and `ui_ask_yes_no` (peak validation). The pattern is:
  the worker emits a signal with the data, blocks on a `QEventLoop` or a
  `QWaitCondition`, the GUI thread shows the window and posts the answer back.
- **Cancel** has to be cooperative: a flag the worker checks between files and
  between stages, raising a `RunCanceled` handled like the existing
  `data.ManualCutCanceled` (which already unwinds a run cleanly).
- **Do not break the headless paths**: `sourceCode/batch/*` and
  `qcs_headless_harness.py` call the same functions with their own facades and
  must keep running on one thread. The threading belongs in the Qt shell only.
- **Verification**: the suite does not cover the GUI. Prove it with a real
  batch of two Seaguard files - the window must stay responsive and Cancel must
  stop it between files - and then a HOBO replicate run, which is the path with
  the most interactive stops.

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

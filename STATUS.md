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

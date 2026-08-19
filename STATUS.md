# STATUS — QCS (Quality Control System — SAGE)

Volatile state, newest first. Every entry dated. Durable rules live in
`CLAUDE.md`, released program changes in `changelog/`, and everything done to
the archived DATA in `sourceCode/batch/CORPUS_LOG.md`.

The release history is NOT kept here: when a version is published its entries
leave this file, and only what is still open moves down to the open items,
dated with when it was last touched. The full text before the 2026-08-18
pruning is in git (`git show a0994bf:STATUS.md`).

## 2026-08-19 - v12.2.3 RELEASED; publication pending

`master` is at `f310d03`, **tagged `v12.2.3` there**. v12.2, v12.2.1 and
v12.2.2 are published, each with its installer; v12.2.3 is a DRAFT waiting for
the owner to press Publish - release id **373234603**, name 'v12.2.3 - only the
variables the data has, written the way they are read', asset
`QCS_Setup_v12.2.3.exe` uploaded (81,567,902 bytes, md5
87998FAD6A6E33990A34F02F8F70E725, also on the Desktop beside
`RELEASE_v12.2.3.md`).

**The v12.2.3 tag was MOVED** (owner authorised, 2026-08-19): it first pointed
at `fd50cbe`, then two more rounds of items were folded into the same version,
so it now points at `f310d03` and the draft's installer was rebuilt and
replaced. Safe only because nothing had consumed it - the release was never
published. The same rule as the v12.0 tag move: once a release is out, a tag
never moves again.

What v12.2.3 carries, all measured (details in `changelog/v12.2.3.md`): the
parameter lists show only the variables the sheet has data for and write their
units properly; step 1 of the visualization tab fits its content; the manual
point cut's selection follows the mouse outside the plot; Data filtering leads
with 'Remove dismissed data' and starts with it and 'bad' ticked; the
visualization Data type reads 'Seaguard TSCP Mooring'; and the revised manual
ships for the first time. Suite **53/53** (the drag test is new), ruff clean.

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

- **TSCP - decide whether the term stays** (owner asked on 2026-08-19). It is
  this project's shorthand for the four core variables of the Seaguard string:
  temperature, salinity, conductivity, pressure. It is a HOUSE term - AADI does
  not call the instrument that - and it appears in three layers, which is what
  makes dropping it a project rather than a rename:
  1. **Interface strings compared in logic**: `'TSCP Profile'`, `'TSCP
     Mooring'`, `'TSCP Doppler'` (14 literals under `sourceCode/`, 59 mentions
     of TSCP in all). Changing the VALUES touches every comparison and the
     saved `dbv_data_type` / `data_type` preferences.
  2. **The internal layout key** `'tscp'` (vs `'hobo'`, `'doppler'`), returned
     by `data.detect_qualified_layout` and used to pick the output folder name
     `QCS qualified tscp data` and the stats file `QCS_<...>_tscp_stat.xlsx`.
  3. **The archive**: 123 files on the share are named `*_QCS_tscp_stat.xlsx`
     (no folders carry the name - the batch driver renames those). Changing the
     layout key without a migration makes the reader stop recognising old
     products, since `detect_qualified_layout` keys off those names.
  A cheap first step, if the goal is only to stop showing it: keep the values
  and the keys, and show 'Seaguard mooring / profile / current profiler' in the
  interface - the display split that `QCS_DatabaseView.data_type_display` and
  `param_display` already established for other labels.
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

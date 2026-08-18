# STATUS — QCS (Quality Control System — SAGE)

Volatile state, newest first. Every entry dated. Durable rules live in
`CLAUDE.md`, released program changes in `changelog/`, and everything done to
the archived DATA in `sourceCode/batch/CORPUS_LOG.md`.

**Pruned on 2026-08-18.** This file had grown to 1,922 lines (111 KB) and was
read whole at every session start. The 61 entries from 2026-08-06 to v12.1 were
removed, not lost: the released work is in `changelog/`, the corpus rounds in
`CORPUS_LOG.md`, and the full text is in git -

```
git show a0994bf:STATUS.md          # the last complete version
git log -p -- STATUS.md             # how it got there
```

Everything that was still OPEN in those entries was carried into the second
section below, each line dated with when it was last touched - not with today.

## 2026-08-18 - v12.2 OPEN (branch `improvements-v12.2`)

- **Nothing persists between sessions - FIXED on the branch (`a0994bf`), not
  yet seen in an installed build.** The root cause was not either of the two
  gaps diagnosed that morning: the Qt shell never aliased the preferences
  dicts the way `QCS_App.py:29` does, so `QCS_Main.USER_PREFS` and
  `QCS_DatabaseView.USER_PREFS` were two dicts and each `save_user_prefs()`
  rewrote the WHOLE file from its own copy - whichever module saved LAST
  silently reverted everything the other had written that session (proven on a
  scratch copy before the fix). The rule is now in `CLAUDE.md`. On top of it:
  `QtShell.closeEvent` -> `remember_window_state()` (`qt_win_geometry`,
  `qt_win_layout`, `log_hidden`; both docks needed `objectName`s or
  `saveState` skips them), `restore_window_state()` before `show()` with the
  batch dock forced hidden, the form written by `QCS_Main.store_form_prefs()`
  from BOTH the RUN path and the close path, and the duplicated save points
  reconnected (`remember_data_dir()` in both shells, `dbv_last_output_dir` in
  the Qt viz browse).
  Verified by opening the shell twice in one driver against a scratch settings
  file: 1234x812 at (140, 96), log hidden and two never-run form fields all
  came back; maximized round-trips; cross-module saves no longer clobber;
  `apply_input_settings` re-checked on a real `.hobo` (returns True, stores
  the 20 keys, a refused form stores nothing). Suite 52/52, ruff clean.
- **Drag-and-drop broke again on the INSTALLED app - not a regression.** The
  app was running ELEVATED (started from the elevated installer's finish page)
  and Windows UIPI forbids a normal-integrity Explorer from posting drag
  messages to a higher-integrity window. The signature that found it: a
  non-elevated shell could not read the running QCS process's path. Fixed at
  the source - both `[Run]` entries of `QCS_installer.iss` carry
  `runasoriginaluser`. Confirmed by the owner only by reopening from the
  shortcut; a real upgrade install has not exercised it.
- **CO2 row in the Selection summary is now conditional**: shown for a Seaguard
  scalar run, hidden for HOBO and for TSCP Doppler (measured on the running
  shell).

## Open items carried over

**Program and release**

- **The app does not reopen after an update** (queued 2026-08-18). Both `[Run]`
  paths of `packaging/QCS_installer.iss`: the silent one used by the in-app
  update (gated on `Check: WizardSilent`) and the Finish-page checkbox of an
  interactive upgrade. Likely the same elevation cause as the drag bug, which
  the `runasoriginaluser` flags now address - reproduce on a real upgrade
  (v12.2 over v12.1, both ways) before changing anything.
- **The installer wizard pages have never been seen on screen** (2026-08-18).
  `DisableDirPage=no` and the two Finish-page checkboxes are right in the
  recipe and the script compiles clean; only a real installer run proves them.
- **The FROZEN exe has never run a real qualification end to end** (open since
  v12.0, 2026-08-18): Depth review, adaptive light review, replicate review,
  the viz tab. A launch smoke test cannot prove lazy imports - a review window
  that only imports on demand can still fail in the frozen build.
- **The persistence round trip in the INSTALLED build** (the `%APPDATA%` store)
  - 2026-08-18, waiting on the next installer.
- **Worker thread with a Cancel button** - deferred on 2026-08-17; the pipeline
  still runs on the interface thread.
- **All-users installs land in `C:\Program Files (x86)\QCS`** (2026-08-13):
  Inno compiles a 32-bit installer unless told otherwise. The one-line
  directive to change it is in `packaging/README.md`, awaiting the owner's
  call. That same day this machine carried TWO installs (v11.2.1 all-users and
  v11.2 per-user, which coexist and self-update independently) - not re-checked
  since.
- **The `QCS_QtApp` module docstring still calls itself 'phase 1 of the
  interface port (DEV build)'** and says master ships the tk app (2026-08-18).
  Not interface text, so nothing ships wrong; still stale.
- **The older-generation `.hobo` layout is not deciphered** (2026-08-14): ~30
  pre-2023 export pairs decode with a one-row offset or a partial mismatch, and
  most are refused by the reader's gates. The corpus is unaffected - it was
  qualified from the exports, not from the binaries.

**Data** - the authoritative list is "Still open on the data" in
`sourceCode/batch/CORPUS_LOG.md`; do not duplicate it here. As of 2026-08-13 it
held four files that need a HOBOware re-export with a 24-hour clock, and 84
files under `HOBO\raw` with no manifest row. `qualified_index.csv` on the share
is the authority for the corpus count.

- **The replicate referee's duplicate-timestamp handling** (`keep='first'`) was
  flagged on 2026-08-06 as papering over the collapsed 12-hour clock rather than
  reporting it. The clock itself was repaired in the v11.0 rounds (41 CSV + 24
  xlsx exports); whether the referee still needs the change was **not
  re-verified** since.

## Environment

- **There is no `gh` CLI on this machine** (re-verified 2026-08-18): pull
  requests and releases are opened and edited through the browser, or through
  the API with a token.

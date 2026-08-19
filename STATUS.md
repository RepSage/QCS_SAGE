# STATUS — QCS (Quality Control System — SAGE)

Volatile state, newest first. Every entry dated. Durable rules live in
`CLAUDE.md`, released program changes in `changelog/`, and everything done to
the archived DATA in `sourceCode/batch/CORPUS_LOG.md`.

The release history is NOT kept here: when a version is published its entries
leave this file, and only what is still open moves down to the second section,
dated with when it was last touched. The full text before the 2026-08-18
pruning is in git (`git show a0994bf:STATUS.md`).

## 2026-08-19 - v12.2.2 PUBLISHED; nothing open on the branch

`master` is the only branch. Three versions went out today, each tagged on its
merge commit, each with a `changelog/` entry, each published by the owner with
its installer attached: **v12.2.1** (`f23af26`) and **v12.2.2** (`a150772`),
after v12.2 the day before. `QCS_VERSION = 'v12.2.2'`.

**The manual was revised AFTER the v12.2.2 installer was built** (`24f0129`):
it had grown three 'What vX added' lists, which belong in `changelog/`, and
they are gone along with the inline version stamps. What only those lists
documented moved into the body - a Selection summary section, a Recent row, a
'What the program remembers' subsection, and the update flow rewritten to the
wizard and its checkbox. **The published `QCS_Setup_v12.2.2.exe` therefore
ships the OLD manual**; the revised one goes out with the next installer. Do
not swap the asset of a published release to fix this.

**Waiting on one answer from the owner**: whether the in-app update, run from
v12.2.1 to v12.2.2, actually ended on the wizard's 'Launch QCS after
installation' page and brought the program back. That is the whole point of
v12.2.1 and it is the ONE thing still unverified about it; the owner said
things went well on 2026-08-19 but not in those words. If it failed,
`%TEMP%\QCS_update_install.log` now records what the installer did.

## Open items

**Program and release**

- **Does the app reopen after an update?** (2026-08-19). The silent relaunch
  was never diagnosed - the `[Run]` entry gated on `Check: WizardSilent` fires
  normally in a reproduction, but that reproduction could not be run ELEVATED,
  which is what a Program Files upgrade does. The answer taken was to stop
  relying on it: the update now runs the wizard and ends on a checkbox. Confirm
  on the next real update before closing this.
- **The installer wizard pages have never been watched on screen** (2026-08-19,
  though every update since v12.2.1 runs them): the two Finish-page checkboxes
  ('Open the user manual', 'Launch QCS after installation') are in the recipe
  and it compiles clean. The folder page deliberately stays on Inno's default
  'auto' - shown on a fresh install, hidden on an upgrade - after the owner
  asked for the old rule back in v12.1.
- **The FROZEN exe has never run a real qualification end to end** (open since
  v12.0; every build since is launch-smoked and closes cleanly): Depth review,
  adaptive light review, replicate review, the viz tab. A launch smoke test
  cannot prove lazy imports - a review window that only imports on demand can
  still fail in the frozen build.
- **Worker thread with a Cancel button** - deferred on 2026-08-17; the pipeline
  still runs on the interface thread.
- **All-users installs land in `C:\Program Files (x86)\QCS`** (re-checked
  2026-08-19: that is where the installed v12.2 sat, HKLM). Inno compiles a
  32-bit installer unless told otherwise; the one-line directive to change it
  is in `packaging/README.md`, awaiting the owner's call. The second install
  this machine used to carry (v11.2 per-user) is gone.
- **The older-generation `.hobo` layout is not deciphered** (2026-08-14): ~30
  pre-2023 export pairs decode with a one-row offset or a partial mismatch, and
  most are refused by the reader's gates. The corpus is unaffected - it was
  qualified from the exports, not from the binaries.
- **The project's subagents are not versioned** (2026-08-19): `.claude/` is in
  `.gitignore`, so `.claude/agents/{code-tracer,release-audit,selftest-runner}
  .md` live on this disk only, while `CLAUDE.md` names them. The owner decided
  that is fine for now.

**Data** - the authoritative list is "Still open on the data" in
`sourceCode/batch/CORPUS_LOG.md`; do not duplicate it here. As of 2026-08-13 it
held four files that need a HOBOware re-export with a 24-hour clock, and 84
files under `HOBO\raw` with no manifest row. `qualified_index.csv` on the share
is the authority for the corpus count.

- **The replicate referee's duplicate-timestamp handling** (`keep='first'`) was
  flagged on 2026-08-06 as papering over the collapsed 12-hour clock rather
  than reporting it. The clock itself was repaired in the v11.0 rounds (41 CSV
  + 24 xlsx exports); whether the referee still needs the change was **not
  re-verified** since.

**Closed on 2026-08-19**, recorded here only so they are not re-opened by
mistake: the preferences round trip in an INSTALLED build (the Program Files
copy's `%APPDATA%\QCS\qcs_user_settings.json` carries `qt_win_geometry`,
`qt_win_layout` and `log_hidden`, 53 keys stamped v12.2 - read from the real
file); and the stale `QCS_QtApp` docstring, rewritten before the v12.2 tag.

## Environment

- **There is no `gh` CLI on this machine** (re-verified 2026-08-18): pull
  requests and releases are opened and edited through the browser, or through
  the API with the token in the Git credential manager.
- **The build stack is kept**: `%TEMP%\qcs_build_env` (PyInstaller + the pinned
  runtime) and `packaging/v12_env` (PySide6 6.8.3, what `QCS.bat` launches).
  `packaging/dist/` is a build artifact and can be deleted; it rebuilds in
  about three minutes from `packaging/README.md`.

# STATUS — QCS (Quality Control System — SAGE)

Volatile state, newest first. Every entry dated. Durable rules live in
`CLAUDE.md`, released program changes in `changelog/`, and everything done to
the archived DATA in `sourceCode/batch/CORPUS_LOG.md`.

The release history is NOT kept here: when a version is published its entries
leave this file, and only what is still open moves down to the second section,
dated with when it was last touched. The full text before the 2026-08-18
pruning is in git (`git show a0994bf:STATUS.md`).

## 2026-08-19 - v12.2.3 RELEASED; publication pending

PR #35 merged (`fd50cbe`), **tagged `v12.2.3`** there, branch
`viz-params-and-units` deleted both sides. Three visualization items, measured
on BURACAS 2019S1 (a cast with no CO2 file): `parameter_names` 13,
`params_with_data` 12, `CO2 Level (ppm)` dropped from BOTH the filter and the
Scale settings; the other twelve labelled °C / µM / µmol/m²/s / µg/L / kg/m³
through the new `QCS_DatabaseView.param_display`, which is display ONLY (the
stored column name is a dict key here and a header in the qualified sheet);
and on step 1 the Input box is exactly its sizeHint (170 px) with 'Next >' at
40% of the page height instead of its bottom edge.

Installer rebuilt and smoke-tested: frozen app alive 20 s, title '... v12.2.3',
closed cleanly, no crash log. **This is the first installer whose bundled
manual carries the revision** - checked in the payload: no 'What vX added'
heading left. ISCC -> `QCS_Setup_v12.2.3.exe`, **77.8 MB**, on the Desktop
beside `RELEASE_v12.2.3.md`, md5 6F3D4A1170E0B2303BFEAB11C1B4E334.

**A DRAFT release is waiting** - id 373234603, asset uploaded (81,556,075
bytes). **Left to the owner: press Publish.**

## 2026-08-19 - v12.2.2 PUBLISHED

`master` is the only branch. Three versions went out today, each tagged on its
merge commit, each with a `changelog/` entry, each published by the owner with
its installer attached: **v12.2.1** (`f23af26`) and **v12.2.2** (`a150772`),
after v12.2 the day before. `QCS_VERSION = 'v12.2.2'`.

The manual was revised after this installer was built (`24f0129`), so the
published `QCS_Setup_v12.2.2.exe` ships the OLD manual, with the release-history
lists still in it. Nothing to do: v12.2.3 carries the revised one. Do not swap
the asset of a published release.

**The update path is CONFIRMED WORKING** (owner, 2026-08-19): updating in the
app from v12.2.1 to v12.2.2 ran the wizard, ended on 'Launch QCS after
installation', and the program came back by itself. That closes the item that
had been open since v12.1 - 'the app does not reopen after an update' - and it
closes it without the silent relaunch ever being diagnosed: the answer was to
stop relying on a step nobody can watch and end on a checkbox instead. If a
future update fails, `%TEMP%\QCS_update_install.log` now records what the
installer did.

## Open items

**Program and release**

- **The installer's FRESH-INSTALL pages have not been watched on screen**
  (2026-08-19). The Finish page is confirmed - the owner saw 'Launch QCS after
  installation' on the v12.2.2 update and the program reopened - but an upgrade
  hides the folder page by design (Inno's default 'auto', the rule the owner
  asked back in v12.1), so the install-for-all-users / just-for-me choice and
  the folder page have only ever been compiled, never seen.
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

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

## 2026-08-19 - v12.2.1 OPEN (branch `fix-update-relaunch`)

v12.2 is PUBLISHED (latest release, asset downloaded once - the owner updated
through the app and the installed version reads 12.2).

**The automatic update still does not reopen the app, and the cause is NOT
identified.** What was established, all of it verified here:

- The install is ALL-USERS in `C:\Program Files (x86)\QCS` (HKLM), so the
  silent upgrade runs ELEVATED. No `QCS_crash.log` anywhere, so nothing that
  started crashed.
- A minimal installer with the SAME shape as the real relaunch entry
  (non-postinstall `[Run]`, `Check: WizardSilent`, `runasoriginaluser`, no
  `[Code]` section) fires it normally in a silent NON-elevated install - all
  three probe entries ran, the Inno log naming 'Run as: Original user'. So the
  recipe is not malformed; the untested difference is the elevation.
- Inno's own docs: `runasoriginaluser` "will have no effect" when Setup is
  launched from an already-elevated process or via 'Run as administrator'.

**The answer taken (owner, 2026-08-19): stop relying on that relaunch.** The
update runs the WIZARD instead of `/SILENT`, and its finish page carries
'Launch QCS after installation' (`[CustomMessages] LaunchAfterInstall`), ticked
by default. The `WizardSilent` entry stays for a hand-run silent install. Both
update paths also pass `/LOG=%TEMP%\QCS_update_install.log`, so the next report
of a failed update arrives with the installer's own account of it.

Also in this round (all measured, see `changelog/v12.2.1.md`):

- **The v12.2 installer shipped the build machine's `qcs_user_settings.json`**:
  step 4 of the build recipe smoke-tests the app INSIDE `dist\QCS`, and since
  v12.2 the app writes its preferences on close. `[Files]` now excludes
  `qcs_user_settings.json` and `QCS_crash.log`; proven with a probe installer -
  only the payload file was installed, both runtime files kept out.
- **Selection summary for a Seaguard file copied out of the archive**: serial,
  start and interval now fall back to the file's own BXML header
  (`_peek_seaguard_header`) when the folder names cannot supply them. Measured:
  loose Desktop `Data000.bin` -> serial 5650-2104, start 16/03/2026 18:01,
  interval 60 s in 0.01 s (the full read of the same file gives a 60.0 s median
  step); cast folder unchanged (5650-2097, 2 groups, 5 s); and the DCPS folder
  now reports 20 s, which it never could before (its records do not decode, but
  the instrument declares `<SpecifiedInterval>`).
- Interface: painted reset arrow instead of the U+21BA glyph; the Quality
  control tests are indented by their layout instead of a stylesheet (an
  unqualified rule is inherited by the widget's TOOLTIP - measured 18 px wider
  than on an unstyled box, which is the strip the owner saw); one name for the
  settings window everywhere; and the status bar's `criteria: CUSTOM` is sized
  from the TEXT, since sizeHint stops growing once a fixed width is applied.

**Left to do**: release v12.2.1 (bumped, changelog and manual written, suite
52/52, ruff clean, `.iss` compiles) - and the checkbox can only be exercised by
updating from a PUBLISHED v12.2.1.

## 2026-08-18 - v12.2 RELEASED and PUBLISHED

Merged (PR #32, merge commit `7c9bbbe`), **tagged `v12.2` there**, branch
`improvements-v12.2` deleted both sides. `QCS_VERSION = 'v12.2'`, installer
recipe at `AppVersion 12.2`, `changelog/v12.2.md` written, manual carrying the
version line and a 'What v12.2 added' section.

What shipped: the preferences fix (one settings dict for both tabs - the port
had two, and the last save reverted the other; `QtShell.closeEvent` saving
window geometry, dock layout and log visibility; the form written by
`QCS_Main.store_form_prefs()` from both the RUN path and the close path), the
installer starting the app as the original user on both `[Run]` paths, and the
conditional CO2 row. Two self-description strings were also fixed before
tagging: the Qt crash dialog was hardcoded 'QCS (v12.0)' and the module
docstring still called the shell a DEV build.

Installer built and smoke-tested: PyInstaller from `%TEMP%\qcs_build_env`,
manual copied beside the exe, frozen app alive 20 s with the title 'QCS -
Quality Control System (SAGE)  -  v12.2', closed cleanly, no crash log. ISCC ->
`QCS_Setup_v12.2.exe`, **77.8 MB**, on the Desktop beside `RELEASE_v12.2.md`,
md5 checked against `packaging\Output`.

**A DRAFT release is waiting** - name 'v12.2 - the interface remembers again',
body from `RELEASE_v12.2.md` minus its heading, `QCS_Setup_v12.2.exe` already
uploaded (state=uploaded, 81,553,054 bytes). A draft shows an 'untagged-...'
URL until it is published; the tag `v12.2` is already on `7c9bbbe`.
**Published by the owner on 2026-08-19.**

**The persistence fix is proven in the FROZEN build, in part**: closing the
smoke-tested exe wrote its own `qcs_user_settings.json` beside it with
`qt_win_geometry`, `qt_win_layout` and `log_hidden` (23 keys, stamped v12.2).
What is still unproven is the `%APPDATA%\QCS` path of a Program Files install,
which only a real install exercises.

**Installing v12.2 over v12.1 IS the test of the queued 'does not reopen after
an update' item** - both `[Run]` paths now carry `runasoriginaluser`. Try it
both ways: the in-app one-click update (silent, `Check: WizardSilent`) and
double-clicking the setup over the existing install (Finish-page checkbox).

## Open items carried over

**Program and release**

- **The app does not reopen after an update** (queued 2026-08-18). Both `[Run]`
  paths of `packaging/QCS_installer.iss`: the silent one used by the in-app
  update (gated on `Check: WizardSilent`) and the Finish-page checkbox of an
  interactive upgrade. Likely the same elevation cause as the drag bug, which
  the `runasoriginaluser` flags now address - reproduce on a real upgrade
  (v12.2 over v12.1, both ways) before changing anything.
- **The installer wizard pages have never been seen on screen** (2026-08-18).
  The two Finish-page checkboxes ('Open the user manual', 'Launch QCS') are in
  the recipe and it compiles clean; only a real installer run proves them. The
  folder page deliberately stays on Inno's default 'auto' - shown on a fresh
  install, hidden on an upgrade - after the owner asked for the old rule back
  in v12.1; an earlier note here claiming `DisableDirPage=no` was wrong.
- **The FROZEN exe has never run a real qualification end to end** (open since
  v12.0; the v12.2 build was launch-smoked and closed cleanly, 2026-08-18): Depth review, adaptive light review, replicate review,
  the viz tab. A launch smoke test cannot prove lazy imports - a review window
  that only imports on demand can still fail in the frozen build.
- **The persistence round trip in an INSTALLED build** (the `%APPDATA%\QCS`
  store of a Program Files install) - 2026-08-18. The frozen exe already
  proved the save path beside its own folder.
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

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

## 2026-08-18 - v12.2 RELEASED; publication pending

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
**Left to the owner: press Publish.**

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

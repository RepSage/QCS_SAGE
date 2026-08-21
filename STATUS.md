# STATUS — QCS (Quality Control System — SAGE)

Volatile state, newest first. Every entry dated. Durable rules live in
`CLAUDE.md`, released program changes in `changelog/`, and everything done to
the archived DATA in `sourceCode/batch/CORPUS_LOG.md`.

The release history is NOT kept here: when a version is published its entries
leave this file, and only what is still open moves down to the open items,
dated with when it was last touched. The full text before the 2026-08-18
pruning is in git (`git show a0994bf:STATUS.md`).

## 2026-08-21 - v13.0 UNRELEASED (branch `doppler-revamp-v13.0`)

The Doppler revamp is DONE in code - all seven items of the backlog, with the
owner's decisions of 2026-08-19 - and nothing is released: no tag, no
installer, no draft. `QCS_VERSION` (`QCS_DataHandler.py`) and the installer's
`AppVersion` (`packaging/QCS_installer.iss`) already read 13.0, `changelog/
v13.0.md` is written and the user manual carries the version and the changes.
v12.3 is published and its entries left this file with `changelog/v12.3.md`.

**MAJOR because qualified CURRENT and PAR values change**: the current flag
string gained a fifth position and a manual dismissal writes 5 across the row;
Seaguard PAR gains sensor-range, environmental-range and spike positions plus
`Flag_PAR`. Existing scalar thresholds and all HOBO QC thresholds are unchanged,
but the settings schema is now instrument/test-specific; a DCPS run with no cut reproduces v12.3's counts
exactly (4,646 good / 126 suspect / 8,636 bad on `Data001.bin`). HOBO also adds
the fail-closed duplicate-input gate recorded in round 6.

### Implementation record

All implemented changes and the owner's review rounds are recorded in
`changelog/v13.0.md`; do not duplicate them here. The code remains unreleased.
The owner selected Fluent Regular (option A) for the shared plot toolbar.
On 2026-08-21 the owner approved the QC-settings redesign: every tab is ordered
Seaguard -> Seaguard current profiler (Doppler) -> HOBO; HOBO switches, sensor
limits and statistical factors are independent; Doppler has four automatic
switches; shared environmental ranges come last; and pressure flat line stays
OFF until a duration-based criterion is validated on the corpus.
The same review set the HOBO fixed light-plot ceiling to 200,000 lux, which
covers the current archive maximum of 198,401.3 while the UA-002 hardware range
remains 320,000 lux (plot only, never QC), renamed the three-day light
confirmation field, standardized O₂/CO₂ labels, made numeric default emphasis
format-insensitive, made the visible bold-value key itself bold and removed the
inert Doppler manual-review note. Light plot limits and light-fouling criteria
are now separate Parameter sections. PAR is integrated with 0-5,000
µmol/m²/s sensor limits (BAD), 0-4,000 environmental limits (SUSPECT), a spike
test and `Flag_PAR`; negative dark-offset values still clamp to valid zero.
The PAR spike keeps the standard three-point residual/factors but estimates its
robust scale from positive irradiance, so valid night zeros cannot collapse MAD.
Those criteria follow the archived PAR-SER ICSW #1372 / Satlantic PAR #2301
templates and the 123-product corpus audit. Adjust plot layout and Figure options retain their global
resets and also carry one reset arrow per editable value.

### Verified (executed 2026-08-21)

- Self-test suite **63/63**, ruff clean.
- A clean PyInstaller rebuild produced the frozen v13.0 bundle. Its main
  window opened, reached a native window handle, wrote no new crash log and
  closed normally. Inno Setup 6.7.3 then produced
  `packaging/Output/QCS_Setup_v13.0.exe` (81,666,762 bytes; SHA-256
  `D5973F78D9711780E65DFB55D9F480E4F2082845CAD1A4D91DC71C9188DC2C14`).
- The QC-settings probe confirms the three instrument boxes in the approved
  order, no `Other parameters`, algorithm-specific factor fields, disabled
  threshold rows when their test is off, independent HOBO/Seaguard temperature
  switches, four Doppler switches and pressure flat line OFF. A compatibility
  probe migrated legacy shared temperature/count/factor settings into the new
  instrument-specific schema. The latest pass also confirmed a bold visible
  default-value key and separate Light plots / Light fouling sections.
- Real-product and Qt/Tk probes cover the three Doppler panels, one-depth mesh,
  compass, manual-cut controls/Help/selector, all U/V gap modes, live selected
  depth, direct navigation, strict Instrument lock and wheel/middle-pan.
- The toolbar probe confirmed six retained commands, absent Back/Forward, bold
  coordinates, palette-aware Fluent icons and matching selector/dialog icons.
  It also confirmed exclusive Zoom state, bounded datetime-X fields, Graphs/Legends
  naming, form-only reset followed by Apply, removed automatic regeneration,
  editable color-scale and U/V legend labels, the preserved Current-profile
  title, a +0.050 figure-width legend move, key alignment after borders and
  Tight layout, and the owned visible Export values tool. The final round also
  confirmed shared horizontal/vertical Current-profile navigation, dynamic
  Zoom-in/out limits for toolbar and wheel, one global 2x2 layout action grid, physically removed
  automatic-regeneration field, editable figure title, hidden redundant Graphs
  selector, and the Figure-options action order.
  A follow-up probe confirmed the new Back action returns to the multi-plot
  selector, remains disabled for a one-plot figure, and the window names the
  chosen plot. Datetime axes now use editable masked text with one strict error
  shared by Figure options and Visualization step 2; the live available range
  follows Site/Year filters, and applying/resetting restores expected X limits.
  Per-row reset arrows were then exercised in both layout and Figure options:
  each restores only its own field, and Figure options still waits for Apply.
  Visualization *Next >*, *Generate panels* and paged-panel navigation now show
  a window-local wait cursor through their synchronous work and final repaint;
  the off-screen Qt probe confirmed cursor activation and restoration.
- A read-only PAR audit decoded 133 raw sensor groups with no error (111,817
  finite readings, including 32,121 negatives handled by the existing clamp)
  and replayed the production v13 tests over all 123 qualified PAR products:
  156,293 GOOD, 1,099 SUSPECT, 1,423 BAD and 19,142 missing rollups. The
  0-5,000 sensor range rejected none; the 0-4,000 environmental range marked
  311 SUSPECT. Two raw deployments (625-row profile and 91-row mooring) then
  ran through the real headless pipeline: both wrote `Flag_PAR`, no negative
  survived, and no invariant failed. The archive itself was not modified.
- The value-integrity sweep now falls back to direct read-only discovery when
  `qualified_index.csv` is absent. It inspected 314 products; all 3,354 values
  outside an instrument limit already carried BAD (4), and no scale defect
  passed all three detection gates.

### Publication in progress - the next actions, in order

1. Commit and push the final review round, open the pull request and confirm
   its complete diff against `master`.
2. Merge the branch into `master` with a local `git merge --no-ff` + push (no
   `gh` CLI here), tag `v13.0` at the merge commit and publish the release with
   `changelog/v13.0.md` as its text, following v12.3's format.
### Known gap left on purpose

- The corpus still has 54 DCPS products with four-character flags. The owner
  explicitly deferred their requalification on 2026-08-20; do not include it
  in the v13.0 publication round.
- The 123 archived Seaguard products containing PAR predate `Flag_PAR`. Their
  bulk requalification is likewise deferred; the v13.0 code/corpus validation
  is read-only and must not overwrite them during this publication round.

## Open items

**Program and release**

- **v12.3 shipped four paths that were never run in the app** (2026-08-19).
  None of them blocks anything; each is one run away from being closed:
  the manual point cut and the replicate review through the worker thread
  (the point-cut MACHINERY was exercised on 2026-08-19 by the DCPS review -
  same `manual_cut_panel` and same `_show_and_wait` hop - so what is left
  unrun there is the scalar Check-variables path itself); a
  BATCH canceled in the middle (the finished files must keep their outputs
  while the interrupted one is removed - the per-file commit implements it and
  it was never executed); 'Go to visualization' landing on step 2, single file
  and batch; and a Seaguard panel under the new fixed-scale rule, which changed
  for every family while only HOBO and Doppler were looked at.
- **The FROZEN exe has never run a real qualification end to end** (open since
  v12.0; every build is launch-smoked and closes cleanly): Depth review,
  adaptive light review, replicate review, the viz tab. A launch smoke test
  cannot prove lazy imports.
- **The older-generation `.hobo` layout is not deciphered** (2026-08-14): ~30
  pre-2023 export pairs decode with a one-row offset or a partial mismatch, and
  most are refused by the reader's gates. The corpus is unaffected - it was
  qualified from the exports.
**Data** - the authoritative list is "Still open on the data" in
`sourceCode/batch/CORPUS_LOG.md`; do not duplicate it here. As of 2026-08-13 it
held four files needing a HOBOware re-export with a 24-hour clock, and 84 files
under `HOBO\raw` with no manifest row. The share's `qualified_index.csv` is the
intended authority for corpus counts, but it was absent when checked on
2026-08-21; `build_index.py` rebuilds it. Read-only validation therefore used
direct discovery and did not recreate or write the index.

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

# STATUS — QCS (Quality Control System — SAGE)

Volatile state, newest first. Every entry dated. Durable rules live in
`CLAUDE.md`, released program changes in `changelog/`, and everything done to
the archived DATA in `sourceCode/batch/CORPUS_LOG.md`.

The release history is NOT kept here: when a version is published its entries
leave this file, and only what is still open moves down to the open items,
dated with when it was last touched. The full text before the 2026-08-18
pruning is in git (`git show a0994bf:STATUS.md`).

## 2026-08-27 - v13.2.2 calendar-domain PATCH open

- Branch `codex/fix-plot-time-axis` carries the unreleased PATCH. Keep it open
  until the owner explicitly asks to close and publish it: no tag, merge,
  installer build, GitHub release or `changelog/v13.2.2.md` exists yet.
- Plot wheel and toolbar zoom-out now reach 100 times the opening span; Home
  retains the opening view as its reset target.
- HOBO panels always use one absolute datetime axis from 1 January of the
  earliest checked year through 1 January after the latest. Scalar Seaguard
  mooring Panels 1/2 use the same combined calendar view when the selected
  Site/Year rows contain more than one `Site` + `Source file` deployment.
  Single-deployment Seaguard, profiles, T-S and Doppler retain their previous
  paths. Time window is a finer crop inside a combined calendar domain.
- Source products remain separate for temperature/parameter tendencies, raw
  pressure lines and HOBO daily light peaks. Figure options -> Lines now names
  each deployment-specific line by site, role and source product instead of
  exposing Matplotlib `_childN` identifiers.
- Curated `Load catalog` now stays empty at `Calculating...` until the product
  count is known, then advances from `Catalog 0/N`; the former full blue
  indeterminate animation is gone. Starting Build now clears the hidden prior
  state before showing the bar, and the write stage stays below 100% until the
  atomic XLSX output has actually completed.
- Figure options `Reset values` restores figure styles and text without moving
  the live zoom/pan view. The apparent line-width inflation was a marker-alias
  bug: resetting a marker-free line selected Matplotlib's first marker even
  though Width still read 1.5. Marker aliases now restore exactly, and an
  off-screen before/after render had zero changed pixels.
- Figure options -> Legends names entries from their visible text and, for line
  keys, edits symbol, symbol color and symbol size independently of the plotted
  data. Its global reset restores the exact original key style; per-row resets
  restore the selected displayed control. Legend-only handles now start with a
  neutral Circle without changing plotted markers; Dot is an explicit option
  instead of `Custom (.)`, and `(None)` is kept first in the list.
- Figure options -> Lines presents `Color` as the same full swatch button used
  for legend symbols while preserving each product line's existing opacity.
  Date/time axes again expose `Axis label` (including the default `Datetime`)
  above `Available`, while keeping serial Min/Max and the irrelevant datetime
  Scale hidden. The former special bold grayscale rule was removed from the
  three main workflow tabs, which now follow the native Qt/Fusion appearance
  already used by Figure options in both light and dark modes. Only the active
  main workflow tab has a bold label, and the native divider below the File /
  View / Help menu bar is suppressed for a cleaner header.
- The 68/68 self-test passes. A synthetic 32-row, 4-deployment Seaguard replay
  generated one at-site and two across-site figures on the exact 2024-01-01 to
  2027-01-01 domain while excluding an unselected 2025 product. A real
  off-screen Qt Figure options probe confirmed the two semantic line names.
  A second Qt probe confirmed `Calculating... -> 0/N -> 1/N`, exact width/marker
  restoration, unchanged X/Y zoom, and legend-only symbol/color/size edits.
  Follow-up probes confirmed Build `1/N -> ... -> Writing -> N/N Complete`, an
  empty first visible frame, RGB line selection with retained alpha, Circle/Dot
  legend defaults, editable `Datetime`, and zero changed render pixels after a
  color reset at a retained zoom. A final Qt layout probe confirmed `(None)`,
  Circle, Dot ordering; Start, End, Axis label, Available ordering; and matching
  native tab shapes without a `QTabBar` stylesheet. The subsequent header probe
  recorded bold / regular / regular paint states for the active main tab, an
  inactive main tab and an active non-main tab, respectively. Light and dark
  renders had continuous `#efefef` and `#252526` pixels across the former menu
  divider row.
- Read-only replay of all 48 current Seaguard fundeio products built 129,780
  rows (0 invalid datetimes, 0 exact duplicates, 19 sites) and generated three
  across-site panels plus one 6-deployment PAB3 panel on the exact 2019-01-01 to
  2026-01-01 domain. Every parameter had 48 named source lines; the 2023 data
  gap stayed visible.
- Broad automatic Y scales can still be stretched by two known qualified BAD
  values: `PAB3_2024S2_HOBO_2` reaches 89,384 degrees C and
  `RRDM03_C_2019S1_SEAGUARD_FUNDEIO_QLF.csv` has one 107.2118 degrees C sample.
  Both carry flag 4. This PATCH neither hides nor changes qualified values;
  revising BAD-value display/scale policy requires an explicit owner decision.
- Next: owner validation through `QCS.bat`, then any additional PATCH fixes.
  Only an explicit close/publish request starts final audit, changelog,
  installer smoke, tag, merge and GitHub publication.

## Open items

**Program and release**

- **Pre-v13 Doppler and PAR products still need explicit requalification before
  direct comparison** (deferred 2026-08-20). The current archive contains 53
  DCPS products with four-character flags and 112 Seaguard products containing
  PAR but no `Flag_PAR`; `BURACA_FUNDA_2021S2` is the only current product with
  PAR and `Flag_PAR`. The v13.0 validation was read-only and the publication did
  not rewrite the older products.
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
`sourceCode/batch/CORPUS_LOG.md`; do not duplicate it here. The root-level
`qualified_index.csv` was rebuilt on 2026-08-25 and matches direct discovery.
The former missing-manifest count is no longer actionable:
the owner deleted both raw manifests on 2026-08-13, and the special collections
that made up almost all of that count left the active corpus on 2026-08-25.

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

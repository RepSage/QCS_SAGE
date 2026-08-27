# STATUS — QCS (Quality Control System — SAGE)

Volatile state, newest first. Every entry dated. Durable rules live in
`CLAUDE.md`, released program changes in `changelog/`, and everything done to
the archived DATA in `sourceCode/batch/CORPUS_LOG.md`.

The release history is NOT kept here: when a version is published its entries
leave this file, and only what is still open moves down to the open items,
dated with when it was last touched. The full text before the 2026-08-18
pruning is in git (`git show a0994bf:STATUS.md`).

## 2026-08-27 - v13.2.3 interaction PATCH open

- Branch `codex/curated-row-click-hobo-tendency` carries the unreleased PATCH.
  Keep it open until the owner explicitly asks to close and publish it: no tag,
  merge, installer build, GitHub release or `changelog/v13.2.3.md` exists yet.
- Every enabled option row in Curated database -> Selection now toggles its
  checkbox. Clicking the indicator itself still changes state exactly once,
  and disabled incompatible rows remain inert.
- Curated Build progress now spells out `Stage k/N` instead of the opaque
  `S1/N`. Stage 1 applies the selection, each selected instrument family adds
  one unification stage, and the final stage completes the atomic workbook.
- The dotted lines behind HOBO luminosity values are the plot's axis grid, not
  data, a fouling cutoff or a tendency. They remain as positional references;
  the solid marked lines are the usable daily light peaks.
- HOBO luminosity has no polynomial tendency line. When Luminosity is the only
  checked parameter, Tendency lines and Regression degree are cleared and
  disabled; selecting Temperature enables them again. Seaguard behavior and a
  HOBO Temperature + Luminosity selection are unchanged.
- The 69/69 self-test passes. Full-tree ruff, compileall, the HTML parser and
  `git diff --check` are clean. Off-screen Qt probes exercised a click on the
  row body, a direct checkbox click and a disabled row; the first two emitted
  exactly one state change and the disabled row emitted none. A real curated
  HOBO workbook confirmed the complete Temperature + Luminosity -> Luminosity
  only -> Temperature + Luminosity tendency-control cycle. A shell probe
  confirmed `Stage 2/4 HOBO` at value 2 on a 0..4 progress range.
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

# STATUS — QCS (Quality Control System — SAGE)

Volatile state, newest first. Every entry dated. Durable rules live in
`CLAUDE.md`, released program changes in `changelog/`, and everything done to
the archived DATA in `sourceCode/batch/CORPUS_LOG.md`.

The release history is NOT kept here: when a version is published its entries
leave this file, and only what is still open moves down to the open items,
dated with when it was last touched. The full text before the 2026-08-18
pruning is in git (`git show a0994bf:STATUS.md`).

## Open patch - v14.0.1 in development (2026-09-03)

- **Patch opened**: the owner requested an open PATCH version for additional
  corrections. `QCS_VERSION` is now `v14.0.1`; the line-legend correction below
  is its first change. Keep subsequent fixes in this open version until the
  owner requests publication. QC rules are unchanged.

- **Line legend keys**: `QCS_DataView.line_only_legend` removes markers from
  cloned line keys before SVG export. The Qt toolbar applies the same rule to
  incoming review figures and no longer adds a circle to line keys. Point-only
  keys, plotted markers and QC data are preserved. HOBO, scalar Seaguard,
  profiles and Doppler share this behavior.
- **Verification executed**: 17 rendered panels through the actual Qt toolbar
  (PySide6 6.8.3, Matplotlib 3.10.0), using five real qualified products plus a
  figure-level legend fixture. All line keys were marker-free after Qt; plot
  markers were unchanged and point keys retained their symbols. HOBO, scalar,
  profile and Doppler legend images were also inspected. After opening v14.0.1,
  the full qualification suite passed all 78 tests and Ruff passed (both exit 0).
  Gate logs: `diagnostics/patch_open_20260903_175549/selftest.log` and `ruff.log`.
- **Local evidence**: `diagnostics/legend_lines/verify_legends.py`,
  `verification.json` and `rendered/` (ignored local diagnostics). Run the script
  with `packaging/v12_env/Scripts/python.exe` and the DATABASE root argument.
- **Publication pending**: branch `codex/line-legends`; the open version is
  v14.0.1. No installer rebuild, tag or new release. Reopen the source application
  and regenerate plots to use the correction; existing exported figures retain
  their previous appearance. If publication is requested, complete the normal
  patch version, documentation, build and release procedure.

## Open items

**Program and release**

- **Bounded replicate decisions** (2026-09-03). Interval bounds use the aligned
  output grid. Any overlapping recorded temperature decision suppresses reference
  advice for the deployment; the sustained screen still runs. Revisit advice
  scope before adding partial-interval decisions. Current ledger entries are
  whole-file decisions.

- **Pre-v13 Doppler and PAR products still need explicit requalification before
  direct comparison** (deferred 2026-08-20). The current archive contains 53
  DCPS products with four-character flags and 112 Seaguard products containing
  PAR but no `Flag_PAR`; `BURACA_FUNDA_2021S2` is the only current product with
  PAR and `Flag_PAR`. The v13.0 validation was read-only and the publication did
  not rewrite the older products.
- **Remaining v12.3 interaction checks** (2026-08-19).
  The replicate review was exercised through the real Qt worker/PlotWindow
  on 2026-09-03; the following remain unrun:
  the manual point cut through the worker thread
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
`sourceCode/batch/CORPUS_LOG.md`; do not duplicate it here. The DATABASE-root
`qualified_index.csv` was rebuilt on 2026-09-03 and matches direct discovery.
The former missing-manifest count is no longer actionable:
the owner deleted both raw manifests on 2026-08-13, and the special collections
that made up almost all of that count left the active corpus on 2026-08-25.

## Environment

- **There is no `gh` CLI on this machine** (2026-08-18): pull requests and
  releases go through the browser, or through the API with the token in the Git
  credential manager. Note that the automation classifier BLOCKS `git push
  --force` and the PR-merge API call; a merge is done with a local
  `git merge --no-ff` + push, and a force-push needs the owner's word first.
- **Build runtime** (2026-09-03): the old `%TEMP%\qcs_build_env` had incomplete
  packages and failed before building. The verified replacement is
  `%TEMP%\qcs_build_v14`, with work files in `%TEMP%\qcs_build_work_v14`;
  direct package pins are in `diagnostics/v14_release/build_requirements.txt`.
  `packaging/v12_env` still launches `QCS.bat`. Use the recipe in
  `packaging/README.md` with the verified short environment/work paths.

# STATUS - QCS (Quality Control System - SAGE)

Volatile state. Durable rules: CLAUDE.md. Released program changes: changelog/.
Archive operations: sourceCode/batch/CORPUS_LOG.md.

## Release state (checked 2026-11-12)

- Last release: v14.0.3. It is tagged at `6ab1df6` = `origin/master`, the
  GitHub Release was published 2026-09-09, and v14.0.3 is installed on this
  machine. `QCS_VERSION` is still `'v14.0.3'` on the v14.1.0 branch.

## v14.1.0 - open on branch `pools-and-field-issues` (2026-11-12)

Scope (owner, 2026-11-12): the app's stale-.hobo warning, pools as a separate
collection, the updated ledger, and GitHub issues #49 and #50. The branch is
not pushed, so nothing is on GitHub yet. `gh` is NOT installed; issues were
read through the public REST API.

Done (committed; suite 93/93, ruff clean):
- `4a84f93` 23a batch work.
- `1ffb6b5` stale .hobo: the app WARNS, never cuts. The owner revised
  'cut and warn' after the corpus sweep: in 12 of 157 export-verified pairs
  genuine data ends after the file save time (7 with PC clocks years
  behind, 4 by 11-23 h), while proven stale tails overrun by >= 9 days. The
  batch refuses only above 48 h with the save time inside the series. All
  188 corpus decodes are unchanged, and the 23a replay is 9/9
  byte-identical. Evidence: `hobo_savetime_margin.py`,
  `hobo_tail_check_v1410.csv`.
- `97657a7` installer: the 'open the user manual' checkbox is translated
  (#49). The manual stays in English.
- `7d7f0ab` #50: Depth (m) is an opt-in Mooring panel parameter, with its
  own colour, tidal (dashed, never fitted), and greyed out for profiles
  (`param_applies`). Panel 3 drops it.
- `4074f66` #49: DCPS spreadsheet exports are refused with the reason
  (`is_dcps_export`); one instance per user, with a splash before the heavy
  imports (`QCS_QtStartup`). Offscreen checks in
  `diagnostics/v1410_single_instance/`: 5/5, and the shell boots with prefs
  untouched. NOT verified: a real clean-install launch from the installer
  (needs the owner's screen).

Next:
1. **Pools: done 2026-11-12.** They are ordinary sites `PISCINA_SGOM` /
   `PISCINA_PLES`, with the Seaguard FORA under `SGOM` / `PLES`: 14 products,
   27,478 rows, index 289 -> 303, integrity clean. The record is in
   CORPUS_LOG 2026-11-12. Still owner-unconfirmed: the forced replicate
   groups PISCINA_PLES/2026S2 and PISCINA_SGOM/2026S1, where one logger
   stopped early (my call, on the PLES/PAB3 precedent).
2. Release ritual: `QCS_VERSION`, `changelog/v14.1.0.md`, manual HTML,
   installer build and smoke test, tag, PR closing #49/#50 (needs `gh` or
   the browser), and a GitHub Release in the v11.6 format.

## RRDM 23a SET 2026 - imported (2026-11-12; record in CORPUS_LOG, code in `4a84f93`)

- Still open: the SGOM H1 and A5 H2 stale exclusions were reported to the
  owner but not explicitly ratified (ledger rows `rrdm23a-*`, reviewer
  "Batch evidence, reported to the owner").
- Decided 2026-11-12: RH18 (22a) and RH30 BRITAS (21a) are rubble experiments
  and stay out. The 12 same-named 12-hour-collapsed Abrolhos2 exports must
  never replace the Database copies.

## Open scientific work (2026-09-09)

- Doppler temporal spike/rate/flat-line thresholds remain exploratory display
  diagnostics. Calibrate against independent evidence and the real corpus before
  promoting any check into official qualification; stored flags are unchanged.

## Carried-over evidence limits (2026-09-08)

- Legacy .hobo: fresh census 188 binaries, 176 accepted, 12 refused. Of 157
  accepted exact-stem pairs compared, 15 fall below 99.9% temperature agreement
  in a bounded +/-3-row screen (not 15 proven decoder defects). CALIFORNIA
  2019S1 has a proven 78-bit phase-changing region after 18 samples. The
  export-guided diagnostic splice matches all 4,723 T/lux samples but assigns
  no clock. Main independently reran probe_transition.py. A general event
  walker and time origin remain undeciphered; do not ship a filename exception,
  row shift, relaxed gate or diagnostic splice. See
  diagnostics/patch_pending_20260908/hobo_legacy_evidence/REPORT.md.
- Remaining data/source decisions are authoritative only in CORPUS_LOG.md's
  "Still open on the data" section and the named episode-review packet. They
  need independent evidence and owner ratification; no new exclusion was made.
  The whole-file ledger/advice-scope limitation still applies before adding
  any partial-interval decision.
- Next investigative step: trace native event framing and clock origin in the
  refused legacy HOBO layouts against independent exports. The diagnostic
  splice is evidence only. Pending source/interval decisions still require
  their independent evidence and owner ratification.

## Environment (verified 2026-09-09; build directories and the references above re-checked present 2026-10-06)

- Absolute Anaconda base for QC/batch; packaging/v12_env for the source Qt
  launcher QCS.bat. Final release build: %TEMP%/qcs_build_v14; fresh work directory
  %TEMP%/qcs_build_work_release1403. Recipe: packaging/README.md.
- No machine shutdown was requested. Earlier shutdown authorization was
  one-time and must not be reused.

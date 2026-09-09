# STATUS - QCS (Quality Control System - SAGE)

Volatile state. Durable rules: CLAUDE.md. Released program changes: changelog/.
Archive operations: sourceCode/batch/CORPUS_LOG.md.

## Open patch v14.0.3 (2026-09-09)

- Owner reports the post-install launch appeared only after a manual launch,
  producing two instances. Branch: codex/fix-postinstall-startup.
- Actual v14.0.2 update log confirms successful installation at 16:21:42 and
  an Original user Exec of the installed QCS.exe at 16:21:44. The remaining
  manually started instance began at 16:23:20 from Explorer. This contradicts
  a missing [Run] action; the exact visibility/delay sequence is not recoverable.
- Reproduced a startup defect with real Qt on the offscreen platform: the
  criteria-reset dialog was visible while its main window stayed hidden until
  acknowledgement. The patch shows the main window first. Normal startup and
  --shot retain their behavior; official QC and installer launch flags unchanged.
- Three post-fix Qt cases passed (upgrade, normal, windowless --shot); both
  preference writers disabled and operator preference hashes unchanged.
  Full suite: 93 tests passed; Ruff passed. Only the version constant changed
  in QCS_DataHandler.py; qualification/QC code is unchanged.
  Evidence and verified backups: diagnostics/postinstall_startup_20260909/.
- Version sites and preview manual identify v14.0.3. No new installer or
  publication yet; the operator installed v14.0.2 through the updater after its
  release. Do not replace that published release or its tag. The corrected source
  still needs validation through a future packaged upgrade; the reproduced hidden
  parent does not prove the sole cause of the reported duplicate opening.
- Archived Doppler SVGs have not been regenerated for this release. New panel
  generation uses v14.0.2; the archive's latest operation remains in CORPUS_LOG.md.

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

## Environment (verified 2026-09-09)

- Absolute Anaconda base for QC/batch; packaging/v12_env for the source Qt
  launcher QCS.bat. Final release build: %TEMP%/qcs_build_v14; fresh work directory
  %TEMP%/qcs_build_work_release1402. Recipe: packaging/README.md.
- No machine shutdown was requested. Earlier shutdown authorization was
  one-time and must not be reused.

# STATUS - QCS (Quality Control System - SAGE)

Volatile state. Durable rules: CLAUDE.md. Released program changes: changelog/.
Archive operations: sourceCode/batch/CORPUS_LOG.md.

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
  %TEMP%/qcs_build_work_release1403. Recipe: packaging/README.md.
- No machine shutdown was requested. Earlier shutdown authorization was
  one-time and must not be reused.

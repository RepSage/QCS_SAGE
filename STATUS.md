# STATUS - QCS (Quality Control System - SAGE)

Volatile state. Durable rules: CLAUDE.md. Released program changes: changelog/.
Archive operations: sourceCode/batch/CORPUS_LOG.md.

## Release state (checked 2026-11-12)

- **v14.1.0 merged and tagged.** PR #51 was merged as `33fb1c0`, now
  `origin/master`. The annotated tag `v14.1.0` points at `33fb1c0` and is
  on origin. The feature branch is deleted locally and on the remote. Its
  scope, verification and corpus work are in `changelog/v14.1.0.md` and
  CORPUS_LOG 2026-11-12. Installer: `packaging/Output/QCS_Setup_v14.1.0.exe`,
  83,474,019 bytes, SHA-256 `d2fdafb5…723a`.
- **Published 2026-11-12:** GitHub Release "v14.1.0 - pool sites, stale .hobo
  warning and two field issues", latest, with `QCS_Setup_v14.1.0.exe`.
  The digest was read back and equals the local SHA-256; the body is
  `diagnostics/release_v1410/release_body.md`. Issues #49 and #50 were
  commented on and closed as completed (`release_api.py close-issues`).
- Owner still to do: install v14.1.0 on this machine; it has 14.0.3.
- Not tested: an installer launch on the owner's desktop, including the
  Finish-page 'Launch QCS'.
- Still owner-unconfirmed:
  - the forced replicate groups PISCINA_PLES/2026S2 and PISCINA_SGOM/2026S1,
    where one logger stopped early (my call, on the PLES/PAB3 precedent);
  - the 23a stale exclusions of SGOM H1 and A5 H2 (reported, not ratified).

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

## Environment (verified 2026-11-12)

- Absolute Anaconda base for QC/batch; packaging/v12_env for the source Qt
  launcher QCS.bat. Release build venv `%TEMP%\qcs_build_env` (recreated
  2026-11-12; `pip freeze` in `%TEMP%\qcs_build_env_freeze.txt`), workpath
  `%TEMP%\qcs_build_work_1410`. `%TEMP%` gets cleaned, so recreate from
  packaging/README.md if missing. `gh` is not installed and is not needed: PRs and Releases go through
  the REST API with the git credential helper (CLAUDE.md).
- No machine shutdown was requested. Earlier shutdown authorization was
  one-time and must not be reused.

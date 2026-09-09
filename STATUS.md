# STATUS - QCS (Quality Control System - SAGE)

Volatile state. Durable rules: CLAUDE.md. Released program changes: changelog/.
Archive operations: sourceCode/batch/CORPUS_LOG.md.

## Open patch v14.0.2 (2026-09-09)

- Owner authorized branch `codex/doppler-visual-review` and the assessment's
  suggestions. Implementation uses one polar-derived display velocity solution,
  explicit cell rows/gaps, native/15/30-minute means, quality/coverage and hover
  reasons, linear/sqrt contrast, and proven/unknown north references.
- Temporal spike/rate/flat-line diagnostics are an experimental, editable
  preview; official five-position flags remain unchanged. No release requested.
- Full suite: 88 checks passed; Ruff passed. Read-only replay: all 53 indexed
  Doppler products / 153,436 observations loaded with matching row counts,
  consistent display vectors and coverage, unchanged input/index hashes, and
  no errors. All 53 north labels resolve to magnetic through exact provenance.
- Real Qt controls, settings round-trip and masked-cell QC hover passed with
  both preference writers disabled; source/preferences hashes stayed unchanged.
  RH30 2025 and RH30 2022S2 were rendered for visual inspection. Evidence,
  reproducible scripts, plan and verified backups:
  diagnostics/patch_doppler_visual_20260909/REPORT.md.
- Remaining owner review: compare the patch appearance and choose preferred
  aggregation/contrast. Temporal limits require calibration before changing
  qualification. No archive regeneration, installer or release was requested.

## Release baseline (2026-09-08)

- The owner accepted the v14.0 Doppler display and
  requested closure of v14.0.1. Changes and release checks belong in
  changelog/v14.0.1.md; full pre-closure status is retained under
  diagnostics/release_v1401_20260908/before/STATUS.md and in Git history.
- Release evidence: diagnostics/release_v1401_20260908/. The final frozen
  executable and installer supersede the earlier development bundles under
  diagnostics/patch_pending_20260908/. The installed operator copy was not
  upgraded as part of release verification.
- The active archive's Doppler SVGs still reflect the preceding partial visual
  restoration. New generation uses the accepted v14.0 display; publication
  does not regenerate archived figures. The latest archive operation and its
  backups are recorded in CORPUS_LOG.md.

## Assessment informing this patch (2026-09-09)

- RH30 2025: the same v14.0 renderer gives ordinary depth bands 29.4% less
  height on the corrected table, because its plotting span now includes the
  surface and deeper usable cells. Time cells remain about 1.28 px wide at
  the default 1,100 x 700 px canvas. Surface speeds raise the shared maximum
  from 60.09 to 125.21 cm/s, reducing contrast in the regular column.
- The earlier assessment and local height/6-hour zoom previews are retained in
  diagnostics/rh30_2025_visual_assessment_20260909/REPORT.md. That assessment
  preceded the owner's authorization of the open patch above.
- Follow-up confirmed native surface size 5 m versus ordinary 2 m, while the
  display draws the first two bands as 6 and 4 m because all 2/4 m cells are
  BAD and disappear before edge calculation. `current_wider.png` tests +31.8%
  canvas width without resampling; time cells grow from 1.277 to 1.684 px.
  Evidence: the same report and width_and_edges.json.
- The owner found width enlargement unhelpful. The next priority is velocity
  consistency: read-only `inspect_quality.py` found 1,325 of 6,557 drawable
  RH30 rows where native speed/direction match a three-beam solution but the
  named North/East fields used by arrows differ. All 1,325 are already SUSPECT;
  all 1,462 GOOD rows are consistent. No native field was replaced. Evidence:
  quality_inspection.json plus the report's QC/representation review.
- All 13,408 stored QC strings/rollups reproduce exactly. The display contains
  5,095 SUSPECT rows (77.70% of drawable rows). Native invalidity explains every
  BAD row. The discarded tail includes 294 records with sensor-in-air/BAD tilt.
  RH30 Config.xml has declination disabled (native Deg.M); clarify magnetic north.
- These observations motivated the open patch above. The surface's 5 m
  acquisition window does not represent a 5 m layer average (TD304 June 2024).
  The patch's equal-height rows identify cells, not sampled layer thickness.

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

## Environment (verified 2026-09-08)

- Absolute Anaconda base for QC/batch; packaging/v12_env for the source Qt
  launcher QCS.bat. The final build used %TEMP%/qcs_build_v14 and the fresh work
  directory %TEMP%/qcs_build_work_release1401. Recipe: packaging/README.md.
- No machine shutdown was requested. Earlier shutdown authorization was
  one-time and must not be reused.

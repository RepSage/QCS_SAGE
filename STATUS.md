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
1. Pools as a separate collection. Owner decisions are needed before any
   write: naming, and which source for 18a/19a, whose csv starts 8-12 h off
   the .hobo.
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

## Pool data (piscinas) re-inclusion - design agreed, after 23a (2026-11-12)

Owner agreed (2026-11-12): a separate collection, part of v14.1.0. Nothing
is implemented yet. The data has been excluded since
2026-08-25, and it is still refused in code: `QCS_Curated.py`
(`_EXCLUDED_*`, app code, so a release), `build_index.py`, `qualify_site.py`
`plan`/`plan_buckets`, `run_semester.py` and the self-tests near
`QCS_SelfTest.py:2013`. **Discrepancy:** CORPUS_LOG cites recovery backups
under `_deleted\20260825\{special_collections,seaguard_pool_sites}` and the
2026-09-03 SGOM/HOBO backups; none of them exists any more
(`DATABASE\_deleted` holds only three 2026-09-08 folders, and `CLAUDE\` no
longer exists). The field archive is the only source.

Inventory (`diagnostics/abrolhos2_sweep_20261112/`: `sweep_pools.py` ->
`pool_files.csv`, `pool_vs_db.py` -> `pool_vs_db.csv`, `probe_pool_hobo.py`
-> `probe_pool_hobo.csv`): 1.2 M files walked on both servers (Abrolhos2
is a superset for pools), 70 distinct pool data files. **The 7 FORA HOBOs
(19a/20a, PLES + SGOM) are byte-identical to the site loggers already in
2024S2/2025S1**, so they stay where they are. Pool-only data:
- HOBO DENTRO, SGOM: 18a (Oct 2023-Mar 2024, HOBO1 only; HOBO2 3 rows,
  .hobo refused), 19a Pis1/Pis2, 20a (CLARA folder), 22a (HOBO1 82 rows,
  HOBO2 ends 2025-05-26), 23a HOBO1/2 (Mar-Sep 2026, .hobo only).
- HOBO DENTRO, PLES: none in 18a; 19a (files misnamed `*_SGOM_PISCINA_*`
  in `PLES\DENTRO`), 20a (FERNANDO), 22a HOBO1 xlsx only (Mar 2025-Mar 2026),
  23a HOBO1/2 (both stop in May 2026).
- Seaguard: 19a PLES DENTRO session (Sep 2024); 22a PLES/SGOM DENTRO/FORA
  sessions + 2 CO2 txt (DENTRO). This matches the 5 removed products.
- **The 18a/19a pool exports are csv whose start differs from the .hobo by
  8-12 h**; the 20a+ xlsx agree with the .hobo. Run the clock check before using them.
- Only paths containing PISCIN* were swept; pool data stored under another
  folder name would be missed.
- The 64 KB pool dumps need the same stale-memory guard as 23a. Their
  boundaries agree with the decode ends: SGOM 22a HOBO1/HOBO2 and PLES 23a
  HOBO2.
Agreed design: restore
`_PISCINAS` (HOBO) and `PISCINA_*` (Seaguard) as a separate collection type
in the Curated Database, never mixed into the monitoring sheets. Then a MINOR
release (QC unchanged), staging from Abrolhos2, and qualification (23a
done 2026-11-12). Pool binaries without an export can use the native path:
add their scope to `NATIVE_BINARY_SCOPES`. Staging the pool dumps also puts
in the raw tree the predecessor the stale guard needs for RODORASO 23a
(`HOBO1_SGOM_PISCINA_210325`).

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

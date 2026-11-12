# STATUS - QCS (Quality Control System - SAGE)

Volatile state. Durable rules: CLAUDE.md. Released program changes: changelog/.
Archive operations: sourceCode/batch/CORPUS_LOG.md.

## Release state (checked 2026-10-06)

- **No open program version.** v14.0.3 is released and nothing has changed
  since:
  - `QCS_VERSION = 'v14.0.3'`, and `changelog/v14.0.3.md` exists.
  - The local tag `v14.0.3` matches the one on `origin`, and local `master` =
    `origin/master` (`6ab1df6`).
  - The GitHub Release "v14.0.3 - startup visibility and per-database depth
    limits" was published 2026-09-09 with `QCS_Setup_v14.0.3.exe`.
  - This machine has 14.0.3 installed (uninstall registry, install date
    2026-09-09, `C:\Program Files (x86)\QCS\`).
- **Uncommitted in the working tree:** the `AGENTS.md` deletion below and this
  file's edits of 2026-10-06. Nothing was committed.

## Codex bridge (2026-10-06)

- `AGENTS.md` deleted at the owner's request (uncommitted deletion of a tracked
  file). Codex now reaches `CLAUDE.md` through the global bridge
  (`~/.codex/AGENTS.md`), which makes every project's `CLAUDE.md` canonical
  unconditionally. Nothing else in the repo referenced `AGENTS.md`.

## RRDM 23a SET 2026 - imported into DATABASE, uncommitted (2026-11-12)

- **Done 2026-11-12:** 23a is staged and qualified as 2026S2: 7 HOBO
  products and CENTROIDE13 Seaguard (scalar CSV + CO2). `PLES_2025S2` was
  requalified with HOBO3. The index went 281 -> 289 and the integrity sweep
  is clean. Operation, numbers and the backup path
  (`_deleted\rrdm23a_20261112T133924`) are in CORPUS_LOG 2026-11-12.
  Evidence: `diagnostics/abrolhos2_sweep_20261112/`.
- **Uncommitted repo changes:** `qualify_site.py` (native-binary path with
  stale guards, `EXPORT\SENSORES` CSV route, forced groups PLES/2025S2 and
  PLES/2026S2), new `stage_rrdm_23a.py` and `promote_rrdm_23a.py`, 4
  `rrdm23a-*` ledger rows, `QCS_ReplicateSelfTest` (pins the 8 `legacy-*`
  rows instead of the total), and the batch README, CORPUS_LOG and
  CLAUDE.md gotcha. Suite 93/93; ruff clean. Proposed commit prefix: none of
  this changes the app, so no version bump. Use `v14.0.3:` per the subject
  rule, or ask the owner.
- **Owner confirmed (2026-11-12)** the PLES/2026S2 forced group. The SGOM H1
  and A5 H2 stale exclusions were reported to the owner, not explicitly
  ratified.
- **Owner decisions 2026-11-12:**
  - No curated workbook is generated after a corpus round. The qualified
    products on the server are the archive, and the app builds the workbook
    when asked. The test export was moved to the Recycle Bin, together with
    its script.
  - **No Doppler CSV reader:** DCPS is read only from the session (`.bin` +
    `Config.xml` + `Layout.xml`). The `.bin` carries the cell geometry;
    without `Config.xml` native quality is unmapped, so no cell can be GOOD.
    The CSV export lacks both. CENTROIDE13's ADCP CSV stays archived only.
- **Release question (answered 2026-11-12):** no app code changed; only a
  self-test assertion did. However, `replicate_decisions.csv` is bundled by
  `QCS.spec`, so the installed 14.0.3 lacks the 4 `rrdm23a-*` rows, which
  matters only for a manual GUI qualification of those files. Recommended:
  commit now with no tag. Ship the ledger with the next version, together
  with the app's stale-dump guard and the pools.
- **Program defect, not fixed:** the app reads a stale 64 KB dump silently.
  Candidate for v14.1.0: warn or cut past the file save time (this alone does
  not catch a dump that is stale from the start, like SGOM H1).
- **Decided 2026-11-12:** RH18 (22a) and RH30 BRITAS (21a) are rubble
  experiments and stay out. The 12 same-named 12-hour-collapsed server
  exports must never replace the Database copies. Also done that day: the
  `SGOM_Fora` QCS folder was deleted from Abrolhos2, with a backup in the
  diagnostics folder.

## Pool data (piscinas) re-inclusion - design agreed, after 23a (2026-11-12)

Owner agreed (2026-11-12) to the recommendation below: a separate collection,
a MINOR release, after 23a. Nothing is implemented. The data has been excluded since
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

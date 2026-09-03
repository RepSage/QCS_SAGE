# Batch qualification of the DATABASE corpus

Reproducible drivers for qualifying the whole staged archive
(`\\Abrolhos\Projetos\Seaguard & HOBO\DATABASE\{SEAGUARD|HOBO}\raw`) through the
REAL QCS pipeline (no GUI), organizing the products under
`DATABASE\{SEAGUARD|HOBO}\qualified\<YEAR>S<1|2>\<SITE>\`. These scripts produced
the qualified corpus first assembled in 2026-07 (v8.0/v8.1 era).

Run them from this folder's parent (`sourceCode\`), calling Anaconda's Python by
absolute path — a bare `python` resolves to the Microsoft Store stub and fails:

```
& "C:\Users\LAMB\anaconda3\python.exe" batch\run_semester.py 2019S1        # one whole semester (all sites + buckets)
& "C:\Users\LAMB\anaconda3\python.exe" batch\qualify_site.py PAB3 --sem 2019S1   # one site of one semester
& "C:\Users\LAMB\anaconda3\python.exe" batch\build_index.py                # rebuild DATABASE\qualified_index.csv
& "C:\Users\LAMB\anaconda3\python.exe" batch\build_data_package.py --sites ESQSUL,SGOM --years 2019-2024   # delivery bundle on the Desktop
& "C:\Users\LAMB\anaconda3\python.exe" batch\reorganize_raw_semesters.py --verify-existing  # recheck the 2026-08-25 move manifest
& "C:\Users\LAMB\anaconda3\python.exe" batch\remove_seaguard_pool_sites.py --verify-existing # recheck the pool-site removal
& "C:\Users\LAMB\anaconda3\python.exe" batch\resolve_sem_sitio.py --verify-existing           # recheck unknown-site removal/reassignment
& "C:\Users\LAMB\anaconda3\python.exe" batch\normalize_buraca_funda_session.py --verify-existing # recheck the BXML session-name move
```

`build_index.py` ends by running **`sweep_value_integrity.py`** over the indexed
products (the lost-separator gates and the "impossible value not flagged" check)
and exits non-zero if the sweep finds a pipeline defect — a corpus round is not
done until that sweep is clean.

Three of the scripts here repair the RAW archive rather than qualify it —
`correct_clock.py`, `repair_collapsed_clock.py` and `repair_unset_clock.py` —
and `drop_stale_products.py` removes superseded products, by MOVING them into
`DATABASE\_deleted\<YYYYMMDD>\` (the share has no recycle bin; emptying that
folder is a human decision). Everything they have done to the archive is
recorded, dated and with its evidence, in **`CORPUS_LOG.md`** beside this file.
That log is not a `changelog/` entry: the app has its own version and none of
this changes the program.

`QCS_SG_ONLY=1` (environment variable) restricts a run to the Seaguard side
(scalar + Doppler), leaving HOBO products untouched — used for timebase reruns.
`QCS_HOBO_ONLY=1` is the mirror image: HOBO products only, Seaguard/Doppler
untouched — used for light-mode reruns.

## What the drivers encode (the hard-won rules)

- **Both raw trees are semester-first** (since 2026-08-25, matching the
  qualified trees): `SEAGUARD\raw\<YEAR>S<1|2>\<SITE>\` and
  `HOBO\raw\<YEAR>S<1|2>\<SITE>\{bruto,planilha}`. Multiple field campaigns
  in one semester share that semester folder; their files were proven
  collision-free before the merge. The previous campaign-to-semester mapping
  and every moved file's SHA-256 are recorded by
  `reorganize_raw_semesters.py` and in `CORPUS_LOG.md`.
- **`_PISCINAS`, `_EXPERIMENTOS`, `_SEM_SITIO`, and direct `PISCINA_*` sites are
  excluded**,
  not monitoring corpus inputs. Their raw and qualified trees were removed
  from the active lanes on 2026-08-25, and the batch and catalog code explicitly
  refuse to ingest those folders if they are restored later.

- **Semester naming** `<SITE>_<YEAR>S<n>_<INSTRUMENT>[_<TIPO>][_k]_QLF` — the
  semester tag unifies the two corpora (the same expedition is labeled
  "ABRIL 2019" by Seaguard and "MAI 2019" by HOBO). `_k` numbers multiple
  casts chronologically; a semester can span two expeditions.
- **Timebase** (see the tooltip of "Correct GMT-3" and the Timebase section of
  the repo's `CLAUDE.md`):
  Seaguard clocks record GMT → the correction is ALWAYS applied
  (`correct_gmt3h = input_type == 'Seaguard'`); HOBO exports and the CO2
  logger are already local. Getting this wrong once shifted the whole corpus
  by 3 h and misaligned every CO2 merge.
- **Casts** are clusters of sibling `-N-` sessions whose starts are ≤ 15 min
  apart (the reader's own rule); the QCS merges a cast's sensor groups itself,
  so only the first session of a cluster is passed in.
- **HOBO replicates are grouped by DATA, not names**: replicates are deployed
  and recovered together (both ends within 1 day). One folder can hold several
  deployments (PAB3 8a = reef-top AND wall loggers) and names lie
  ('ExpIncubacaoMacroalgas' vs 'Expincubacaorodolito'). Rare owner-confirmed
  exceptions live in `FORCED_REPLICATE_GROUPS`, scoped to one site+semester and
  ordered with the longest sound time grid first; a missing member fails loudly.
- **CO2 pairs by time overlap**: each cast attaches the CO2 txt whose own time
  range (local, read from its Year..Second columns) covers the cast's local
  start (±1 h); among several covering exports the SHORTEST wins (the per-cast
  trim, not the overnight file); no match → no CO2, never guessed.
- **Sheets rule** (`_sheets`): one export per logger — `.xlsx`, falling back
  to `.csv` only when that logger has no xlsx (exact-stem grouping so
  HOBO1/HOBO2 stay apart).
- **Clock repairs live in the raw itself** (owner decision, 2026-08-07):
  `correct_clock.py` applies the −12 h AM/PM repair IN PLACE to the affected
  raw CSVs — gated (a file must be accused by `light_clock_phase` first, so
  re-running never double-shifts), validated locally before replacing, and
  recorded in the raw `manifest.csv`; the original `.hobo` binaries under
  `bruto\` are never touched. The driver's `_fail_on_wrong_clock` makes any
  HOBO product whose input is 12 h out of phase FAIL instead of shipping.
- **Light cutoff mode** (`LIGHT_MODE`, since 2026-08): the corpus standard is
  the FIXED 60-day window (`light : fixed-60d window` in provenance) — the
  adaptive threshold is entangled with season. The replicate-review
  recommendation is DECLINED in batch (nobody is present to ratify it);
  ratified exclusions live in `replicate_decisions.csv`.
  Each product's provenance also carries a per-file `clock :` verdict from
  `light_clock_phase`.
- **Byte-identical re-archives are skipped** (the field archive stores some
  pool exports twice, in per-person folders): MD5 over each product's inputs,
  the explicit DENTRO/FORA copy wins over `_NA`.
- **Provenance**: every product appends an idempotent block to its folder's
  `provenance.txt` — raw semester (legacy products retain their original field
  campaign label), cast start,
  exact input sessions, CO2 file, and (C/D transect legs) the per-station
  time slices from `FASE_1_PLANILHA_SEAGUARD_PERFIS.xlsx`.

## Layout per product

```
qualified\<YEAR>S<n>\[<bucket>\]<SITE>\
    <NAME>_QLF.csv          qualified table
    DataView\<NAME>\        every applicable panel (one folder PER product -
                            panels are auto-named by site/semester/year and
                            several casts would overwrite each other)
    reports\<NAME>__QCS_*   the QCS report files
    provenance.txt          one block per product
```

Panels by product type: FUNDEIO → panel1 + panel2 (per parameter) + T-S;
PERFIL → panel3 + T-S (when T/S exist); DOPPLER → the 3 current panels;
HOBO → the temperature/light panel.

## Known limits

- Failures are printed per product and never abort a site; the known
  non-qualifying deployments are raw-data realities (single-record casts,
  empty/attitude-only DCPS sessions, malformed HOBO exports).
- The drivers monkeypatch the GUI layer (messageboxes, the light-window
  review accepts the proposed cutoff, prefs are not saved) — the QC itself is
  the real pipeline.

## Candidate requalification and replicate decisions (v14.0)

`QCS_QUALIFIED_OUTPUT_ROOT` redirects qualified outputs while raw inputs and
regional reference products remain in the active archive. Validation runs must
use an external candidate directory; the reference baseline stays fixed so
processing order cannot change recommendations. Both GUI preference writers are
disabled before the headless shell is built.

`validate_hobo_candidate.py --archive <DATABASE> --output <candidate-directory>`
replays the active HOBO products, inventories the baseline, records raw and
qualified hashes, and writes product differences, the integrity sweep result,
and unification messages. `--site SGOM --semester 2026S1` selects the pilot.
It does not promote files or rebuild the active index.

The ledger records source filename, variable, inclusive local-time interval,
action, reason, reviewer and review date. Blank bounds mean the whole file;
`*` means all variables. Historical all-file exclusions still apply during
archive discovery; temperature-only decisions apply to single-file qualification and combination. The
legacy rows were migrated on 2026-09-03; their evidence predates that migration.
Individual reports receive compact, stable source identities in their names;
`<product>__QCS_report_sources.csv` maps them to full source-relative paths.
Obsolete unscoped individual reports are retained under `reports/previous/`. The unqualified
`<product>__QCS_report.xlsx` always describes the exported product, including
separate counts of suspect flags, blank values, and withheld temperatures.

The initial sustained screen is >0.5 degC for >=24 elapsed hours and >=3
consecutive eligible pairs. Missing pairs, agreement and gaps >1.5 median
sampling intervals split episodes. This one-diurnal-cycle review threshold is
an explicit provisional policy, not a calibrated sensor-failure criterion.
The diagnostic episode queue also uses pre-cleaning values, but suspect/bad
values are never restored as contributors. Excluding a temperature variable
does not decide light quality. Unresolved episodes preserve originals in the
sample audit and produce NaN temperature with Flag_T=3. Isolated disagreements
retain the existing suspect mean. No automatic reference recommendation is
ratified in batch.

`validate_hobo_corpus.py --archive <DATABASE> --output <fresh-candidate-directory>`
executes four isolated per-site workers, then assembles their products and review
queue. It reports incomplete active products separately from invalid extra raw
inputs; any failed run remains explicit and the process exits nonzero. The
integrity fallback discovers only `*_QLF.csv`, excluding diagnostic report CSVs.

`promote_hobo_corpus.py --archive <DATABASE> --candidate <validated-replay>
--output <audit-directory> --workbook <new-HOBO-workbook>` inspects a replay
without changing the archive. `--apply` verifies full site-folder backups,
replaces complete validated folders, rebuilds the index, runs the mandatory
integrity sweep and exports through the canonical curated engine. Any failed
active product must be named explicitly with `--retain-product <filename>`;
it stays unchanged and is recorded as unreprocessed, never silently dropped.
Unexpected product membership, timestamp/flag/light changes, report mismatches
or concurrent edits stop promotion. This driver is scoped to the v14 sustained
temperature screen after the separate SGOM correction. The dated operation and
its exact retained-product list are recorded in `CORPUS_LOG.md`.

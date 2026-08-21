# Batch qualification of the CLAUDE corpus

Reproducible drivers for qualifying the whole staged archive
(`\\Abrolhos\Projetos\Seaguard & HOBO\CLAUDE\{SEAGUARD|HOBO}\raw`) through the
REAL QCS pipeline (no GUI), organizing the products under
`CLAUDE\{SEAGUARD|HOBO}\qualified\<YEAR>S<1|2>\<SITE>\`. These scripts produced
the 315-product corpus of 2026-07 (v8.0/v8.1 era).

Run them from this folder's parent (`sourceCode\`), calling Anaconda's Python by
absolute path — a bare `python` resolves to the Microsoft Store stub and fails:

```
& "C:\Users\LAMB\anaconda3\python.exe" batch\run_semester.py 2019S1        # one whole semester (all sites + buckets)
& "C:\Users\LAMB\anaconda3\python.exe" batch\qualify_site.py PAB3 --sem 2019S1   # one site of one semester
& "C:\Users\LAMB\anaconda3\python.exe" batch\build_index.py                # rebuild CLAUDE\qualified_index.csv
& "C:\Users\LAMB\anaconda3\python.exe" batch\build_data_package.py --sites ESQSUL,SGOM --years 2019-2024   # delivery bundle on the Desktop
```

`build_index.py` ends by running **`sweep_value_integrity.py`** over the indexed
products (the lost-separator gates and the "impossible value not flagged" check)
and exits non-zero if the sweep finds a pipeline defect — a corpus round is not
done until that sweep is clean.

Three of the scripts here repair the RAW archive rather than qualify it —
`correct_clock.py`, `repair_collapsed_clock.py` and `repair_unset_clock.py` —
and `drop_stale_products.py` removes superseded products, by MOVING them into
`CLAUDE\_deleted\<YYYYMMDD>\` (the share has no recycle bin; emptying that
folder is a human decision). Everything they have done to the archive is
recorded, dated and with its evidence, in **`CORPUS_LOG.md`** beside this file.
That log is not a `changelog/` entry: the app has its own version and none of
this changes the program.

`QCS_SG_ONLY=1` (environment variable) restricts a run to the Seaguard side
(scalar + Doppler), leaving HOBO products untouched — used for timebase reruns.
`QCS_HOBO_ONLY=1` is the mirror image: HOBO products only, Seaguard/Doppler
untouched — used for light-mode reruns.

## What the drivers encode (the hard-won rules)

- **Both raw trees are campaign-first** (HOBO since 2026-08-13, matching
  Seaguard): `SEAGUARD\raw\<N - MES ANO>\<SITE>\` and
  `HOBO\raw\<RRDM Na MES ANO>\<SITE>\{bruto,planilha}`;
  `_PISCINAS\<campaign>\<pool>\`, `_EXPERIMENTOS\<campaign>\<subpath>\`. The
  two campaign numberings are DIFFERENT series and must never be merged — only
  8 of 15 HOBO campaigns have a Seaguard counterpart.

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
  ('ExpIncubacaoMacroalgas' vs 'Expincubacaorodolito').
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
  replicates the corpus has decided to drop go through `EXCLUDED_REPLICATES`.
  Each product's provenance also carries a per-file `clock :` verdict from
  `light_clock_phase`.
- **Byte-identical re-archives are skipped** (the field archive stores some
  pool exports twice, in per-person folders): MD5 over each product's inputs,
  the explicit DENTRO/FORA copy wins over `_NA`.
- **Provenance**: every product appends an idempotent block to its folder's
  `provenance.txt` — campaign label (the semester tag drops it), cast start,
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

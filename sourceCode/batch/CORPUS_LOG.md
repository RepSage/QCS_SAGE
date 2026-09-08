# CORPUS LOG — operations performed on the archive itself

What was done to the DATA under the `DATABASE\HOBO` and `DATABASE\SEAGUARD` raw
and qualified lanes, when, and why. This is not a `changelog/` entry: the app
has its own version and its own release notes, and nothing here changes the
program. It is kept beside the scripts that did the work, because re-running
them is how any of it is reproduced.

Lane check, so this file does not compete with the other three: `CLAUDE.md`
holds durable rules, `STATUS.md` volatile program state, this batch README the
corpus procedure, and `changelog/` the app releases. This file holds
**operations on the archive** — dated, with their evidence and recovery paths.

---

## 2026-09-08 — Original Doppler presentation restored

The owner rejected the general appearance introduced during the corrections.
The plotter now uses its pre-correction heatmap time framing, numeric depth
labels and compact titles. The native reader, coordinates, QC, source/cell
identity protections and compatible surface grouping remain corrected. This
operation changes presentation only; it does not restore the old qualified data.

The actual pre-correction plotter was loaded from the retained source backup
and compared on identical current inputs. All nine panels matched pixel for
pixel for RH30 2022, RH30 2025 and PLES Column 1 plus Surface; PLES's other
columns were deliberately outside this appearance comparison to avoid the
old cross-column averaging defect. RH30's three restored panels were also
checked in the Qt browser. The heatmap fits drawable-cell timestamps again;
the U/V series still uses the full selected timeline for its gap treatment.

The replay checked **53 Doppler products / 153,436 rows** and **155,240 plotted
speed/direction values** against the original cells. All **174 SVGs** in the
**50 nonempty DataView product folders** were replaced after complete verified
original/prepared backups. Three products with no drawable cells retain zero
panels. Recovery copies, displaced folders and the index are preserved under:

```
\\Abrolhos\Projetos\Seaguard & HOBO\DATABASE\_deleted\doppler_visual_restore_20260908T192658
```

All **281 qualified CSVs / 664,861 rows** remain byte-identical. The canonical
index/integrity gate passed; the archive still has **1,106 panels** (174 Doppler,
817 scalar, 115 HOBO). No raw, report, provenance or operator preference file
was written. Evidence: `diagnostics/doppler_visual_revert_20260908/`, especially
`comparison.json`, `validation.json`, `qt_verification.json`, `promotion.json`
and `index_integrity.log`. Source and presentation backups precede every edit.

## 2026-09-08 — Surface cells restored to shared Doppler panels

The owner's RH30 2022 review identified an excessive split: its native Surface
cell and Column 1 both use the surface reference and have distinct coordinates.
The surface cell now accompanies compatible columns in the same three panels.
Distinct regular columns retain their identities; instrument-referenced columns
remain separate from surface cells. No coordinate conversion or cell averaging
was performed.

Plotting was replayed over all **53 Doppler tables / 153,436 rows**. All
**155,240 plotted speed/direction values** matched their original cells. RH30
2022's three panels were inspected in the real Qt browser; PLES's compatible
columns and TIM2's different references were also visually checked. The
resulting **174 SVGs replace 321**: 49 products lose the redundant standalone
surface group. All **50 nonempty DataView product folders** were replaced;
three products with no drawable current cells still have zero panels.

Every original folder and prepared replacement was verified by SHA-256 before
the first swap. Original/displaced graphs and the previous index are retained at:

```
\\Abrolhos\Projetos\Seaguard & HOBO\DATABASE\_deleted\doppler_surface_20260908T190646
```

All **281 qualified CSVs remain byte-identical**, retaining **664,861 rows**.
The operation writes only Doppler DataView folders and the checked index;
raw inputs, reports, provenance and operator preferences are unchanged. The
rebuilt index has **1,106 panels** (174 Doppler, 817 scalar, 115 HOBO). Canonical
integrity passed: zero scale defects and all 3,354 preexisting out-of-range
values remain flagged 4. No requalification or additional data exclusion ran.

Evidence and reproducible drivers: `diagnostics/doppler_surface_20260908/`
(`validation.json`, `qt_verification.json`, `promotion.json`,
`index_integrity.log`, `validate_panels.py`, `promote_panels.py`). An initial
diagnostic timestamp parse was corrected to accept mixed timestamp precision;
a promotion preflight stopped on legitimate zero-panel folders before any
archive mutation. Both initial logs are retained separately.

## 2026-09-08 — v14.0.1 Doppler, scalar/PAR and native-clock corrections promoted

The owner requested the pending corrections within the open v14.0.1 patch.
`promote_v1401_candidates.py` validated isolated replays, prepared and verified
**62 complete site-folder backups**, then replaced **168 qualified products**:
53 Doppler, 113 scalar Seaguard and the two HOBO products retained in September's
earlier rollout. This operation also replaced four independently verified
clock-corrected XLSX exports; all original native binaries remain untouched.
The backup, original index, displaced site folders and clock manifest are under:

```
\\Abrolhos\Projetos\Seaguard & HOBO\DATABASE\_deleted\qcs_v1401_20260908T114504
```

The Doppler replay recovered **24,054 cell-time rows**: 129,382 became 153,436,
with no old rows removed and no matched velocity measurements changed. Native
configured coordinates changed in 112,170 matched rows and Flag_cur changed in
50,130. All 53 products now carry five-position flags, both native cell states
and coordinate-reference metadata. The corrected framing was checked against
7,740 native records, including 88 legitimate partial records, with 6,493,622
independent Point comparisons; vendor CSV subsets matched 19,099 numeric values.
There are 321 regenerated current panels, separated by source/column/reference.

All **113 scalar products / 163,152 rows** retain their measurement values and
timestamp grids, with current flags including Flag_PAR. Original sessions, CO2
pairing and local timebase were preserved. There are 817 scalar panels. The
three-row RH2 2020S1 PERFIL_2 table has no finite depth; it was retained after
fixing a plotting-only NaN-limit failure, without inventing a vertical panel.

The ESQNORTE/ESQSUL 2024S2 repairs disambiguated **3,504 AM/PM cells across four
XLSX exports** from their matched native clocks. All 21,086 nonclock cells were
verified unchanged. Export-only launch readings were retained; no GMT conversion
or new source exclusion was applied. The resulting products retain 1,766 and
1,742 rows, respectively, with no sustained mean withheld. This validates the
stored clock reconstruction, not synchronization to an external clock.
`clock_export_manifest.json` records original/new hashes and sizes, immutable
binary hashes and row counts. The legacy raw manifests are absent from the
current archive and were not recreated. Original clock/provenance fields remain
historical evidence; the appended clock_repair field states the correction.

After replacement, all **1,098 raw-file hashes** matched their original values
except the four expected XLSX changes; every promoted CSV matched its candidate,
and the other **113 HOBO CSVs** were unchanged. Obsolete product reports were
retained under reports/previous; original campaign, ordered input, cast, CO2
and station fields were preserved. Complete prepared trees also passed readback.

The rebuilt active index and independent CSV readback agree on **281 products /
664,861 source rows / 1,253 SVGs**. All 33 products with CO2 retain their pairing
and point counts. The mandatory integrity sweep read all 281: zero scale defects,
and all 3,354 pre-existing out-of-sensor-limit values in five products carry BAD
flag 4. Canonical unification retained all 153,436 Doppler and 163,152 scalar
rows; HOBO's 348,273 source rows became 348,183 after removing 90 exact duplicates.
The 7,162 HOBO rows sharing Site+Datetime with different values remain warned and
retained. No curated workbook was overwritten by this operation.

Evidence root: `diagnostics/patch_pending_20260908/`. Replays and comparisons:
`full_candidate/`, `scalar_candidate/`, `clock_candidate/`, `native_reference/`,
`clock_binaries/` and `clock_exports_qa/`. Transaction evidence:
`promotion_applied/{result.json,before_hashes.json,backup_manifest.json,journal.json,
clock_export_manifest.json,qualified_index.after.csv,active_readback.json}` and
`promotion_applied.log`. The complete dry-run passed before applying; two injected
local failures independently verified rollback (`promotion_rollback_verification.json`).
The program patch and executable verification remain in STATUS.md; no release
was published by this data operation.

---

## 2026-09-03 — v14 sustained-disagreement policy applied across HOBO

After inspecting corrected SGOM, the owner authorized the same v14 policy
throughout the corpus. The scope is all 115 active HOBO products; the parameter
does not apply to Seaguard or Doppler. A fresh isolated replay inventoried
348,273 source rows and produced **113 products / 344,765 rows**, with unchanged
source code during the replay and no raw, active-product or preference changes.

Exactly **18,120 previously finite suspect temperatures in 16 products** became
empty under the >0.5 degC, >=24 elapsed hours, >=3 consecutive eligible-pair
screen. Every matched timestamp, light value, Flag_lux and Flag_T was unchanged.
The original readings remain in the per-replicate diagnostics. No additional
logger was selected automatically: unresolved means were withheld with Flag_T=3.
SGOM's prior temperature correction was retained. All **55 combined reports**
matched their CSV row, suspect and withheld counts; single-contributor spread
was empty and no individual file masqueraded as a combined product.

Two active products failed the existing collapsed-clock gate and were explicitly
retained unchanged: `ESQNORTE_2024S2_HOBO_QLF.csv` (1,766 rows) and
`ESQSUL_2024S2_HOBO_QLF.csv` (1,742 rows). Their 3,508 rows explain the entire
replay shortfall. Extra unindexed attempts also failed for PAB3 2019S2 HOBO_2
(fewer than two valid timestamps) and RODORASO 2023S2 HOBO_2 (no recognized
temperature column). No replacement product was invented for those inputs.
The replay exited nonzero and kept all four failures explicit; promotion then
required the two retained active filenames to be supplied explicitly.

A focused replay with complete dialogs confirmed the precise stop in
`QCS_Replicates.align_replicates`: replica 1 has **661 conflicting repeated
timestamps at ESQNORTE** and **778 at ESQSUL**. The earlier log had displayed
the first clock warning instead of the later error. Batch error reporting now
prioritizes an error dialog; this changes the reported reason, not qualification.
The original XLSX inputs are `HOBO1_ESQNORTE_B2_040424_290824.xlsx`,
`HOBO2_ESQNORTE_B2_04042024-290824.xlsx`,
`HOBO1_ESQSUL_B4_070424_300824.xlsx` and
`HOBO2_ESQSUL_B4_070424_300824.xlsx`. Their archived `.hobo` originals exist;
valid 24-hour replacement exports were not verified. The full errors are in
`diagnostics/v14_release/clock_failures.json`.

`promote_hobo_corpus.py` inspected every replacement, backed up and verified
**99 complete site folders**, and prepared every replacement before moving
the first active folder. The recoverable backup, original index and displaced
site trees are under:

```
\\Abrolhos\Projetos\Seaguard & HOBO\DATABASE\_deleted\hobo_v14_20260903T164826
```

The active site folders now contain fresh v14 CSVs, panels and reports. Original
campaign labels, ordered raw inputs and clock evidence were preserved in
provenance, with the requalification policy and backup appended. The journal
records each replaced folder. All **380 files in the HOBO raw tree** and
**168 untouched qualified CSVs** (166 Seaguard/Doppler plus the two retained
HOBO products) passed the before/after hash check. All 113 promoted CSVs match
their validated candidates byte for byte.

The rebuilt index retains **281 products / 640,807 source rows**, including all
115 HOBO products / 348,273 source rows. The mandatory full integrity sweep
read all 281 products, found no scale defect, and confirmed that all 3,354
out-of-sensor-limit values in five products carry BAD flag 4; no violation was
unmarked. Those pre-existing values were not silently discarded by this round.

The canonical curated engine exported and reread
`C:\Users\LAMB\Desktop\QCS_HOBO_v14.0.xlsx`: **348,273 source rows became
348,183 workbook rows** after removing 90 exact duplicates. All 10,654 rows
sharing Site+Datetime with different values were retained and warned, including
the two unreprocessed products. The all-site/all-year filter removed zero rows.
The workbook includes all 115 active HOBO products, with source identities and
their individual QCS versions; it does not relabel the two retained products
as successfully requalified. The existing SGOM-only workbook remains available.

Evidence: `diagnostics/v14_corpus_rollout/validation_summary.json`,
`product_diff.csv`, `source_hashes.json`, `episode_review_queue.csv`, and
`diagnostics/v14_corpus_promotion/promotion.json`, `product_changes.csv`,
`before_hashes.json`, `journal.json`, `qualified_index.after.csv`; the complete
operation log is `diagnostics/v14_corpus_promotion.log`. Source code, release
verification and installer records remain in the program's separate lanes.

---

## 2026-09-03 — SGOM civil-2025 temperature correction promoted

Owner instruction: correct SGOM 2025 in the active corpus so the corrected
series can be inspected. The affected recovery product is
`HOBO/qualified/2026S1/SGOM/SGOM_2026S1_HOBO_QLF.csv`, spanning September 2025
through March 2026. A fresh v14.0 pipeline replay applied the recorded
`sgom-2026s1-temperature` decision: exclude HOBO1 temperature throughout its
source file, retain eligible HOBO2 temperature, and qualify light independently.

`promote_sgom_temperature.py` checked the candidate against the active product
and verified complete backups before replacing the site folder, index and
curated workbook. The recoverable backup is:

```
\\Abrolhos\Projetos\Seaguard & HOBO\DATABASE\_deleted\sgom_temperature_20260903T162615
```

It contains the original site tree under `original/HOBO/qualified/2026S1/SGOM`,
the displaced original folder, `qualified_index.before.csv` and
`QCS_curated_database.before.xlsx`. The active product now has the fresh CSV,
panels, combined and individual reports, and decision audit. Provenance retains
the original field-campaign label (`RRDM 22a MAR 2026`), inputs and clock records,
with the v14.0 decision and backup location appended.

Verified result: **2,254 rows and every timestamp preserved; 481 temperatures
changed, all dated 2025; 463 Flag_T values changed from 3 to 1; zero changes to
light or Flag_lux**. Temperatures dated 2026 are numerically unchanged. All
2,254 temperatures are finite (24.062–29.452 degC), and spread is empty because
only one eligible temperature source contributes. This also replaces the old
zero-spread metadata on the already single-source rows, including 2026.
At 2025-10-30 03:36:05 local, the old 29.710 degC / 9.750 degC spread / Flag_T=3
is now 24.835 degC / no replicate spread / Flag_T=1. No interpolation was used.

The rebuilt index retains **281 products and 640,807 source rows** (115 HOBO,
113 Seaguard, 53 Doppler). The mandatory full value-integrity sweep reopened
all 281 products: no scale defect; all 3,354 out-of-sensor-limit values in five
other products carry BAD flag 4, with no unmarked violation. Hashes confirmed
that both SGOM raw exports and the other **114 active HOBO CSVs** were unchanged.

The workbook actually selected in the program,
`C:\Users\LAMB\Desktop\QCS_curated_database.xlsx`, was rebuilt through the
canonical curated/database engine and reread from disk. Its existing SGOM,
HOBO, civil-2025/2026 selection remains **4,657 rows from three products**, with
the same timestamps and source-file identities; exactly 481 temperatures
changed. The annual comparison uses all **3,737 civil-2025 rows** and excludes
920 rows dated 2026. Existing deployment gaps remain unfilled. An already
open visualization must reload the workbook to consume the replacement.

Evidence: `diagnostics/sgom_2025_promotion/staging/validation_summary.json`,
`promotion.log`, `result/promotion.json`, `result/backup.json`,
`result/curated_build.log`, `result/qualified_index.after.csv`, and the
`result/SGOM_2025_before_after.png` / `.svg` comparison. The annual corrected
table is `result/SGOM_2025_corrected.csv`. Other v14 candidate products remain
staged; this operation did not promote the full replay or repair other raw data.

---

## 2026-08-26 — PAB3 2026S1 HOBO exports qualified as replicates

Owner decision: `HOBO1_PAB3_180925_110326.xlsx` and
`HOBO2_PAB3_180925_110326.xlsx` are replicate loggers from one deployment; the
filenames made them look like separate deployments. The automatic data-span
rule had split them because HOBO1 stopped about 28 days before HOBO2. This is
now an exact, ordered exception scoped only to `PAB3/2026S1`: HOBO2 comes first
because `combine_hobo_replicates` uses the first logger's timestamps as the
output grid. A missing forced-group member fails loudly rather than silently
recreating two products.

The two raw inputs were not modified:

| raw export | bytes | SHA-256 |
|---|---:|---|
| `HOBO2_PAB3_180925_110326.xlsx` | 107,161 | `EFB91AECDCF6501C37D68FC25EBD003BA3BBE69B7EE43DFA9A1BFAC3FE60E1A6` |
| `HOBO1_PAB3_180925_110326.xlsx` | 91,049 | `469459B50ABCB982EB99BA9A044114D994A48D95CE427DFBBFC2BD42032F1C54` |

The official HOBO-only qualification wrote `PAB3_2026S1_HOBO_QLF`: **4,269
rows**, 2025-09-18 05:24:49 through 2026-03-15 13:24:49, all stamped v13.2.1,
with no invalid or duplicated timestamp and no exact duplicate row. The
ordered provenance block names HOBO2 then HOBO1. Temperature spread is present
on **3,559 paired rows**; `Flag_T` is 4,245 GOOD / 24 NOT_EVALUATED and
`Flag_lux` is 1,440 GOOD / 2,829 BAD under the unchanged fixed-60-day light
rule. Both clock verdicts are OK. The product has one panel and eight reports.

Only after the replacement passed those checks, `drop_stale_products.py`
moved both superseded products, their DataView directories and five reports
each — **14 files / 2,905,576 bytes** — to the recoverable destinations:

```
DATABASE\_deleted\20260826\PAB3_2026S1_HOBO_1_QLF
DATABASE\_deleted\20260826\PAB3_2026S1_HOBO_2_QLF
```

No file was permanently deleted. Their provenance blocks were removed only
after the replacement's ordered inputs were verified.

The final rebuilt index contains **281 products**: 113 Seaguard, 53 Doppler and
115 HOBO. Its value-integrity sweep found 3,354 out-of-sensor-limit values
across five products and confirmed that all 3,354 carry BAD flag 4. Independent
direct discovery and read-only build reopened all 281 products: **640,807
source rows became 640,717 unified rows** (Seaguard 163,152; Doppler 129,382;
HOBO 348,183). The same 90 exact duplicate rows were removed and the same
10,654 non-identical Site+Datetime overlaps were retained; neither count changed
because of the replicate correction. A full HOBO replay found 115 products,
348,183 rows, zero finite light bridges across missing days, and one PAB3
deployment with one temperature tendency. Its light plot has separate solid
and dotted portions for usable versus recorded-BAD data, not a second logger.

---

## 2026-08-25 — `_SEM_SITIO` resolved; BURACA_FUNDA 2021S2 qualified

Owner decision: the anonymous raw 2021S2 deployment belongs to
`BURACA_FUNDA`; the 2019S1, 2019S2 and 2020S1 `_SEM_SITIO` raw/qualified trees
have no recoverable site identity and must leave the monitoring corpus.

`resolve_sem_sitio.py` fingerprinted all **7 active `_SEM_SITIO` directories,
110 files and 7,425,270 bytes** before moving anything. The 2021S2 raw
directory (**2 files / 150,438 bytes**) moved to
`SEAGUARD\raw\2021S2\BURACA_FUNDA`; the other **6 directories, 108 files and
7,274,832 bytes** moved intact to
`DATABASE\_deleted\20260825\sem_sitio_unknown_origin\<original relative path>`.
Those removed trees held **7 qualified products / 8,428 source rows** (6
Seaguard and 1 Doppler). `sem_sitio_resolution.csv` records every original and
destination path, size and SHA-256. All **110/110** final destinations passed
the chained verifier after the session normalization below.

The recovered binary had been archived under the anonymous folder `Sensores`.
Its own BXML template identifies it as
`5650-2097-0-2021-10-01T18-35-10.047Z`; the **253 records** run from
2021-10-01 18:35:20 to 19:17:20 GMT at a 10 s interval, with no missing or
duplicated timestamp. `normalize_buraca_funda_session.py` moved the 44,902-byte
binary to that canonical session folder and independently verified its size,
SHA-256 and BXML SessionID through
`buraca_funda_session_normalization.csv`. The calibrated scalar detector returns
`TSCP Profile` (0.7 h at 10 s), agreeing with the archived `PERFIL` lane even
though the instrument template's generic `GroupDescr` says `FUNDEIO`.

The paired `BURACA FUNDA MINI CO2.txt` has 1,369 complete rows, no invalid or
duplicated timestamp, and spans 15:23:50 to 16:11:54 local time, covering the
cast start after the mandatory GMT-3 correction. The real batch pipeline wrote
`BURACA_FUNDA_2021S2_SEAGUARD_PERFIL_QLF`: **253 rows**, `Site=BURACA_FUNDA`,
15:35:20 to 16:17:20 local, **165 CO2 values**, no invalid/duplicated timestamp
or duplicated row, plus two panels, four reports and a complete provenance
block. No input row was dropped; QC blanked values in dismissed/not-evaluable
rows as encoded by their flags.

The rebuilt `qualified_index.csv` and an independent direct Curated Database
scan agree on the current corpus: **282 products, 644,411 source rows, 34 sites,
zero invalid timestamps and zero `_SEM_SITIO` product**, split as **113
Seaguard, 53 Doppler and 116 HOBO**. The index has no duplicate product/path and
all 282 paths exist. Its value-integrity sweep found 3,354 out-of-sensor-limit
values across five products and confirmed that all 3,354 carry BAD flag 4;
there is no unmarked violation. Self-test 66/66, full ruff/compile and
`git diff --check` passed. The full curated workbook was not regenerated; the
previous 288-product workbook is now explicitly stale.

---

## 2026-08-25 — pool/experiment data removed; raw trees normalized by semester

Owner decision: `_EXPERIMENTOS` and `_PISCINAS` are experiment/pool-specific
collections, not the long-term monitoring corpus. They must not contribute to a
curated database. Both their raw source trees and every qualified subtree were
removed from the active `HOBO` lanes. No such directory existed on the
Seaguard side.

The share has no recycle bin, so removal followed the corpus's established
recoverable-delete rule: **9 directories, 320 files and 23,386,788 bytes** were
moved intact to
`CLAUDE\_deleted\20260825\special_collections\<original relative path>`.
They include **21 qualified products**: 1 in 2024S1, 4 in 2024S2, 7 in 2025S1,
3 in 2025S2 and 6 in 2026S1. `SGOM_NA_2024S1_HOBO_QLF` was among them.
The active corpus consequently changed as follows:

| | before | after | difference |
|---|---:|---:|---:|
| qualified products | 314 | **293** | -21 |
| source rows | 694,803 | **659,261** | -35,542 |
| sites represented | 44 | **38** | -6 |
| Seaguard / Doppler / HOBO products | 123 / 54 / 137 | **123 / 54 / 116** | 0 / 0 / -21 |

The owner then confirmed that five ordinary Seaguard site folders beginning
with `PISCINA_` were also pool-specific and must leave the monitoring corpus.
They comprised one product in 2024S2 and four in 2026S1: **10 raw/qualified
directories, 120 files, 25,297,340 bytes, 5 qualified products and 6,675 source
rows**. They were moved intact to
`CLAUDE\_deleted\20260825\seaguard_pool_sites\<original relative path>`.
`seaguard_pool_sites_removal.csv` records every original/recovery path, size
and SHA-256, and all **120/120** recovery files passed the post-move check.

After both owner decisions, the active monitoring corpus contains **288
products, 652,586 source rows and 34 sites**, split as 118 Seaguard, 54 Doppler
and 116 HOBO products. Fourteen pool products left the active corpus in total:
the nine HOBO products formerly below `_PISCINAS` and these five Seaguard
products.

The raw layout was normalized in the same operation. The 18 Seaguard campaign
folders merged without collision into 10 semester folders; the 15 HOBO
campaign folders merged into 14. Both active trees now have the same shape as
the qualified tree:

```
<FAMILY>\raw\<YEAR>S<1|2>\<SITE>\...
```

This was a path-only operation: **1,177 active raw files / 137,944,422 bytes**
remain (Seaguard 797 / 114,295,531 bytes; HOBO 380 / 23,648,891 bytes). Before
the first move, `reorganize_raw_semesters.py` wrote source path, destination,
size and SHA-256 for every active and excluded file to
`CLAUDE\_deleted\20260825\semester_raw_reorganization.csv`. After the move,
all **1,497/1,497** destinations matched that record byte-for-byte. The first
verification pass stopped at a 260-character recovery path because Python used
the legacy Windows path form; the file was present, the verifier was changed to
the extended UNC form, and the manifest audit then completed in full. No move
was repeated.

The batch drivers now read semester-first raw folders and no longer run the
special-collection branch. `build_index.py` and the Curated Database catalog
also reject those two folder names and direct `PISCINA_*` sites defensively.
Real-corpus discovery through the updated planner covered 151 semester/site
combinations and rediscovered **288/288 current qualified products** from the
reorganized raw inputs. It also listed 14 raw deployment plans with no
qualified product; all remain explicit raw-only/nonqualifying cases rather
than fabricated outputs. The Curated Database catalog independently reopened
all 288 products, found 652,586 source rows, and contained neither a special
path nor a `PISCINA_*` site.

The full active-corpus build was then executed, not inferred from the catalog:
all **288/288 products contributed**, producing **652,496 selected rows**
(Seaguard 171,282; Doppler 129,427; HOBO 351,787). The 90-row difference from
the source total is exactly the engine's known identical-HOBO-row
deduplication; 10,654 rows that share Site+Datetime but carry different values
were retained. The workbook reopened with all five expected sheets at
`packaging\Output\QCS_curated_monitoring_corpus_test.xlsx` (60,481,487 bytes;
SHA-256
`D926F5E239828CA81846C10CFA8C5FB442AC411B9797FB4C3720001FD5A70D75`).
An independent `build_index.py` run also returned 288 products and the same
118/54/116 instrument split; its integrity sweep found no unflagged value
outside a sensor limit.

---

## 2026-08-13 — the archive tables deleted by the owner

The owner deleted, by hand and by their own decision, everything at the share
root except the two data trees: `_registros\` (the historical tables filed
there earlier the same day), `qualified_index.csv`, and both raw
`manifest.csv`. Verified right after: `HOBO\` and `SEAGUARD\` are intact
(137 + 177 = 314 qualified products; all raw campaigns present).

What this costs, recorded so the next round is not surprised by it:

- `qualified_index.csv` is regenerable (`build_index.py`) — the sweep scripts
  and the package builder need it regenerated before they can run again.
- The two `manifest.csv` are NOT regenerable: they were the file-level
  provenance of the raw staging (source path, md5, every in-place clock
  repair). From here on, this log's prose entries are the only record of
  those operations.

The folder structure remains under the owner's review; no tooling should be
rebuilt around the current layout until that settles.

---

## 2026-08-10 — the collapsed 12-hour clock reconstructed

> No QC rule changed — the *data* did. 65 raw HOBO exports had half their
> samples on the wrong timestamp; after the repair those deployments carry twice
> the usable temporal resolution, and every product built from them is
> different. **The app was not touched**: running the same v10.0 program over
> the repaired raw is what produced the new products.

## The defect

HOBOware in pt-BR locale writes the time as `04h0min0s` — a **12-hour clock
with no AM/PM marker**. Every afternoon reading therefore lands on top of its
morning twin:

```
1,03/17/18 04h0min0s,21.473      <-  04:00
3,03/17/18 10h0min0s,28.953      <-  10:00
4,03/17/18 01h0min0s,28.555      <-  13:00, written as 01h
```

Signature: no sample after 12:59 and about half the timestamps duplicated,
carrying *conflicting* values (`04:00 → 21.47 °C` and `04:00 → 29.35 °C`).
Detected and named since v9.1 by `light_clock_phase`; now repaired.

## Why the reconstruction is determined, not guessed

Measured over the 62 affected exports **before** the repair was written:

- the **date field is intact** — only the hour collapsed, and the date rolls
  over correctly at midnight, so each row has exactly two candidate times:
  `date + h%12` and that + 12 h;
- inside one calendar date the true times rise with a **single noon crossing** —
  61 of the 62 exports satisfy this (the exception is a hand-assembled
  multi-site incubation sheet, excluded);
- **sampling is regular** (mode 2 h; also 10 s, 1 min, 30 min, 1 h, 3 h), so a
  wrong choice breaks the step.

The walk picks, for each row, the candidate strictly after the previous one and
closest to `previous + interval`. It turns out to be **self-correcting**: at
each date boundary the interval rule forces the morning half again, so the
reconstruction is essentially forced by the data rather than chosen.

The decisive check is physical: a submerged sensor must peak near local noon.
All 41 repaired files land at **11.5–12.9 h with 89–100% of the light energy in
daylight hours**. Nothing is written until every gate passes — strictly
increasing times *in the written file*, no duplicates left, ≥95% of steps on the
sampling interval, a noon-centered light phase, and the strongest one: **only
clock fields may differ**, checked by blanking every clock field in both texts
and requiring the remainder to be byte-identical.

Two traps found while building it, both worth remembering:

- **The reader sorts its output**, so validating monotonicity through the reader
  hides exactly the corruption the gate exists to catch. Monotonicity is now
  checked on the written text, re-parsed independently.
- **Row counts cannot be compared** before and after: the reader trims
  out-of-water edges by a temperature heuristic, so a correctly repaired file
  legitimately keeps a different number of rows.

## What was repaired, skipped and refused

| outcome | files | |
|---|---|---|
| repaired | **41** | light now peaks at 11.5–12.9 h |
| already fine | 9 | no duplicated timestamps to begin with |
| **refused** | **12** | listed below, left untouched |

Refusals are deliberate and reported per file:

- **9 files: the clock was never set.** The reconstruction is forced and
  correct, yet the light still peaks at 19–23 h and the dates are years off —
  e.g. `HOBO1_PNorte_090521_210821.csv` (a May–August **2021** deployment) is
  stamped 31/12/2017 → 16/04/2018, the right *duration* on the wrong *epoch*.
  This is a **third, separate defect class**, newly identified, and this release
  does not fix it: it needs the deployment's own dates, not an inference.
- **1 file: the sensor is dark from the start**, so the light cannot tell
  morning from afternoon (`PAB3_30062016_PAREDE.csv` — the 8,833-duplicate file
  that first exposed the referee's dedup problem in v9.0).
- **2 files: irregular or hand-assembled**, where the premise does not hold.

For every refusal the loggers' own `.hobo` binaries under `bruto\` are
untouched: **re-exporting from HOBOware with a 24-hour clock remains the
inference-free fix** and is the recommended route.

## The same defect in the `.xlsx` exports

The corpus rule prefers `.xlsx` over `.csv` for the same logger, so the CSV
sweep alone left 33 of 142 products still carrying ~50% duplicated timestamps.
A second pass covers the workbooks, where the collapsed clock sits as **cell
text** in a single-sheet, no-merged-cells export: **24 repaired**, all landing
the light peak at **10.8–12.0 h**.

Because saving a workbook rewrites the whole file rather than the cells that
changed, the xlsx path adds one gate the CSV path does not need: **the repair
is refused unless the logger's own `.hobo` binary sits beside it**, so the
inference-free original always survives. Two workbooks were refused on exactly
that ground, and one more because neither half puts its light near noon.

The "nothing but the clock changed" proof is adapted rather than dropped: every
cell value except the clock column is fingerprinted before and after and must
match exactly.

## Where the repair lives

`sourceCode/batch/repair_collapsed_clock.py`, applied **in place to the raw
CSVs** (the archive owner's standing decision since v9.1: one archive, one
truth). It stages and validates every candidate in a local scratch dir before
the share is touched, is idempotent (a second pass repairs 0 and reports 50
already fine), and records each repair in the raw `manifest.csv` with a new
checksum, status `collapsed_clock_reconstructed` and a dated note.

## The seasonal residual: measured, and deliberately NOT pursued

v10.0 removed the deterministic half of the seasonal confound and the residual
— winter cloud and turbidity — was left open. The obvious next idea was the one
that already worked for temperature in v9.0: use **contemporaneous loggers at
other sites** as an independent witness, since cloud is regional while fouling
is per-logger. It was tested before being built, and it fails twice over:

- **coverage**: only **11 of 111** series have ≥50% contemporaneous coverage
  from other sites still inside their own clean window — deployments are
  staggered, so the witnesses are rarely there;
- **effect**: on those 11 it is no better than the astronomical curve (better on
  5, worse on 6; median log-scatter 1.01 vs 1.00).

The recommendation is therefore to **stop optimizing the adaptive threshold**.
The fixed 60-day window remains the corpus standard for exactly this reason.

## Also done in this round

- **9 factory-epoch clocks repaired** (`repair_unset_clock.py`): loggers
  deployed with the clock never set — right duration, wrong epoch. The DAY
  offset comes from the archived/field launch dates, the HOUR from the light
  phase, and the check is the TEMPERATURE against contemporaneous loggers at
  other sites (independent of light, so it cannot pass by construction):
  r = +0.78 to +0.99 over 104–460 days. Recovered `PAB3_2021S2` and
  `PNOR_2021S2`, which had been failing outright.
- **10 stale/redundant products deleted** (`drop_stale_products.py`): 7 left
  behind when replicate grouping changed, plus `ESQRODO_2020S1` (a re-file
  under the wrong campaign) and the `PLES_FORA` / `SGOM_FORA` pool products
  (the owner confirmed the FORA control IS the site logger).
- **The replicate rule was widened**: both ends within 3 days now also count
  when the two durations differ by less than 5%. Pairs are started and stopped
  by hand and the collapsed clock had been hiding it.

## Verification

44 self-tests pass, ruff clean — unchanged, because the app was not modified.
Every repair is gated per file (see each script's header). Final state:
**315 products** — HOBO 138, Seaguard 123, Doppler 54, 34 with CO2; the 60-day
light validation reports 0 inconsistent, and the index's duplicate-input
warning is silent.

## Still open on the data (verified 2026-09-08)

**Unresolved HOBO source choices.** The sustained-disagreement review packet
identifies 104 eligible sustained subepisodes and 18,120 withheld temperatures
in 16 products. The corresponding temperatures remain missing with Flag_T=3;
diagnostic BAD/SUSPECT values cannot become contributors. No additional source
or interval exclusion was ratified in this round. Historical recommendations
lack an archived independent-reference lineage and coverage record. The next
scientific action is to supply that evidence and ratify a source/interval
decision for a named episode, then replay that bounded product. The ledger is
currently whole-file; partial decisions first require revisiting advice scope.

Evidence: diagnostics/patch_pending_20260908/episode_review/REVIEW.md,
review_packet.json and the per-product/episode/source tables. The packet
reconciled 39 report sets and 401 protected inputs without inconsistency.
The native-clock quartet above introduces no further sustained withheld mean.

**Retired items in the former open list.** The old table mixed resolved,
excluded and inactive sources. It was reconciled using the current canonical
reader, export selection, ledger, active index and native comparisons:

- ESQSUL 2021S1 / HOBO#02 remains excluded by legacy-07/08; neither export is
  selected and there is no active product. Its old re-export request is closed.
- ESQRODO 2025S1 / HOBO1 uses the clean XLSX: all 4,138 exported timestamps
  and temperatures match its binary, and light matches within 0.11 lux.
  The collapsed CSV is unselected. A light-phase anomaly remains (16.8497 h);
  the diagnostic prescribes no shift. The historical provenance's 'OK' wording
  is not a current clock diagnostic and must not justify a new correction.
- PAB3 PAREDE's selected CSV now has zero duplicate timestamps; its active
  TEMP_ONLY product has 17,670 rows. The former 8,833-duplicate claim is obsolete.
  There is no light channel or same-stem binary to independently certify clock
  phase; that absence does not authorize another reconstruction.
- HOBO-incubacao_rodolito.csv is absent from the active raw inventory; its
  special-collection history is outside the active qualification scope.

These are read-only reconciliations, not newly performed repairs or exclusions.
See diagnostics/patch_pending_20260908/remaining_clock_audit/REPORT.md,
findings.json and main_confirmation/ (independent rerun, 20 hashes unchanged).
The two ESQNORTE/ESQSUL 2024S2 products formerly retained are now repaired and
requalified by the dated operation above. Legacy binary-decoder work remains
a program limitation in STATUS.md; it is not a reason to rewrite sound exports.

---

## 2026-08-11 — re-exports from the .hobo binaries

The archive owner re-exported the two loggers that no inference could settle.
The result closed one and diagnosed the other.

**`HOBO1_ESQRODO_B1_050424_160325`** — resolved. The clean export carries a
24-hour clock and a dot decimal: 0 duplicated timestamps (was 2,065) and
temperature natively 24.74–28.06 degC, so the product no longer depends on
`_hobo_fix_temp_scale` at all. Staged and requalified. Its light still peaks at
16.8 h, identical across three independent exports — that is what the logger
recorded, not an export artifact, and it does not affect QC because the corpus
light window is the fixed 60 days.

**`HOBO#02_Ref.EsquecidoSul_RRDM_04022020_240221`** — three defects, one on top
of the other, and the re-export was what made the second visible:

1. collapsed 12-hour export — fixed by the re-export;
2. clock launched +12 h out of phase — INVISIBLE until now, because phase
   cannot be measured on a collapsed clock. `_fail_on_wrong_clock` blocks its
   qualification, which is the intended behavior;
3. temperature reading −84.77…156.53 degC — confirmed across three independent
   exports. The sensor failed in the field; nothing recovers it.

Left unqualified on purpose. Repairing defect 2 would only rescue 30 days of
light on a logger whose temperature is lost, and the antiphase script currently
handles CSV only.

A note for future exports: the 24-hour clock lives in HOBOware under
*Preferences → General → Date/Time*, not in the export dialog — which is why
the first attempt came back still collapsed.

---

## 2026-08-11 — the Seaguard side swept for the lost decimal separator: it is not there, and it cannot be

Nothing was changed. This entry records a **negative result** so the question
does not have to be re-opened: `_hobo_fix_temp_scale` was written for the HOBO
side, and the obvious next question was whether the Seaguard corpus carries the
same defect. It does not, for a structural reason plus a measured one.

**The structural reason.** The Seaguard raw archive is **255 `.bin` AADI binary
sessions and no text data at all** — the 4 `.csv` in the tree are manifests and
the 40 `.txt` are MiniCO2 files. A lost decimal separator is a *text* accident:
it needs a locale that writes `25.125` as `25125`. In an AADI session the
measurements are `float32` payloads read by `struct.unpack`, so there is no
separator to lose. Verified rather than asserted, by decoding a real session
(`5650-2097-1-2019-05-03T…`): 8 of its 9 numeric columns carry a decimal part
on **100%** of their values, and the single all-integer column is `Record
Number`, which is an integer by definition.

The one text input on this side is the MiniCO2 `.txt`, and it is safe by
construction: it carries its own C format line (`%07.2f,%03.2f,…`) with dot
decimals and comma field separators. All 39 data files parse; the 40th is a
field note whose filename *is* the note.

**The measured reason.** `sweep_value_integrity.py` (new, beside this file) ran
the reader's own three gates over **all 315 products of both families**:

| | |
|---|---|
| product × variable combinations flagged as scale suspects | **3** |
| of those, passing all three gates | **0** |

The three suspects are all genuine data, not scale errors: two RRDM03 2019S2 pH
profiles reading 8.35–10.62 (alkaline, no power of ten fixes them, no integers),
and `PAB3_2024S2_HOBO_2` at 68,934–89,384 °C — the file the team had already
named `(ERRO)`, which the reader **correctly refuses** to rescale because ÷1000
still leaves 68–89 °C. The sweep reproduces that refusal from the other
direction, which is the useful part.

**And the QC is doing its job.** 3,361 values across 6 products fall outside the
instrument's physical limit — **100% of them carry flag 4**. Zero values escaped
unflagged, in either family.

### Two traps in the sweep itself, worth remembering

- **Guessing column names silently skips variables.** The first pass used
  `Pressure (kPa)`, `Turbidity (NTU)`, `Dissolved Oxygen (uM)` and
  `Chlorophyll (ug/l)`; the corpus writes `(dbar)`, `(FTU)`, `O2 level (uM)` and
  `(ug/L)`. Four of ten variables were not swept and the run reported success.
  The script now takes its mapping from `QCS_DataHandler.PARAM_FLAG_COLUMN`.
- **Not every variable has a sensor-range test, and no environmental test flags
  4.** Dissolved organic matter has *only* an environmental range test and every
  environmental test assigns SUSPECT (3) — see `test_sequence` in `QCS_Main.py`.
  Checking DOM for flag 4 against an invented sensor limit produced three
  "pipeline defects" that did not exist; with the correct expectation, **137 of
  137** out-of-envelope DOM values are marked.

### What the sweep did find, and it is not a defect

`Density (kg/m3)` falls below 1000 in many products — fresh-water density, which
means the **conductivity reads zero**. On `RRDM03_C_2019S1` and
`RRDM03_D_2019S1_2` that is **90% of the deployment** (conductivity median
0.017 mS/cm against a corpus median of 56), so those two moorings have no usable
salinity or conductivity — their temperature is fine. The pipeline marks the
rows `Flag_S`/`Flag_C` = 3. Elsewhere the same signature is brief and is simply
the instrument out of the water at deployment and recovery.

Density, Soundspeed, TSS, Depth and PAR are derived and carry **no flag column
of their own**: a reader taking Density at face value gets 996 kg/m³ with no
warning attached. The verdict lives in `Flag_S`/`Flag_C`, which is where it
should be read.

On the Doppler side (54 products), `Speed stdev (cm/s)` uses **−1 as a no-data
sentinel** — 35,471 occurrences, **all 35,471 flagged 4**, as are 1,171 of the
1,178 values above the instrument's speed range (the other 7 are flagged 3).

---

## 2026-08-11 — the Seaguard side requalified onto v11.0, and one logger discarded

Two operations, both on the archive; the app was not touched and `QCS_VERSION`
did not move.

### The 177 Seaguard/Doppler products were still stamped v8.1

They had never been run through v9.0–v11.0, because every release in that range
was HOBO-side. **Requalifying them changes only the stamp — measured, not
assumed**, in two steps:

- the code diff v8.1→v11.0 names `doppler_qc` and `vertical_gradient_test`,
  which *would* matter here — but they are only the enclosing functions of code
  added below them, and all 12 REMOVED lines sit in `light_fouling_baseline`;
- `qualify_site.py` nevertheless gained ~400 lines that touch naming and
  grouping for every instrument, so **RH3/2019S2 was backed up, requalified and
  diffed first**: Seaguard + Doppler + CO2 (the GMT-3 bypass path), same three
  products, **data identical, only the stamp changed**.

The full run then covered 9 semesters with `QCS_SG_ONLY=1`, leaving HOBO alone.
Against the previous index: **0 products appeared, 1 disappeared** (the discard
below), and every row count matched except one stale index entry. **8 products
failed to build; all 8 never existed in the index** — pre-existing raw-data
problems ("no data records found", "fewer than 2 valid timestamps"), verified
name by name against the old index before accepting them.

Row accounting, because the totals must add up: 695,173 → 694,803 = **−370**
= −366 (the discarded product) −4 (`ESQRODO_2025S1_HOBO_2_QLF`, regenerated at
11:28 during the `.hobo` re-export work while the index had not been rebuilt
since; the Seaguard round started at 14:14 and never touched it).

**Corpus: 314 products — HOBO 137, Seaguard 123, Doppler 54, 34 with CO2. All
314 stamped v11.0.**

### `HOBO#02_Ref.EsquecidoSul` discarded — and the notes about it were wrong

The archive owner ruled it unusable ("essencialmente descartável agora que vimos
que tem tanto erro"). Acting on that exposed a defect in this very log: the
entry of 2026-08-11 above says it was "left unqualified on purpose" and that
`_fail_on_wrong_clock` "blocks its qualification". **It did not.** The product
`ESQSUL_2021S1_HOBO_QLF` existed, regenerated that same morning and stamped
v11.0, with **337 of its 366 rows flagged GOOD** — from the sensor that reads to
156 °C.

The guard fires only on a clean ±12 h accusation from `light_clock_phase`. This
logger's light peaks at **4.4 h**, which raises no accusation at all, so nothing
stopped it. Worth remembering as a general lesson: *a guard that keys on a
specific diagnosis does not cover a logger broken in a different way.*

Removed **cause first**, because deleting a product whose cause is still live is
exactly how `ESQRODO_2020S1` resurrected:

1. both exports (`.csv` and `.xlsx` — the re-export carries the same failed
   sensor) added to `EXCLUDED_REPLICATES` in `qualify_site.py`, with the
   evidence. `_sheets` drops them, so every path that lists sheets honours it;
2. `drop_stale_products.py` gained a **`DISCARDED`** mode: a removal with no
   replacement, **gated on the raw already being excluded** — it refuses to
   delete otherwise. The gate reads `EXCLUDED_REPLICATES` by parsing
   `qualify_site.py` with `ast` rather than importing it, since importing builds
   a Tk root as a side effect;
3. the folder was backed up, then the product removed in full — CSV, DataView,
   5 report files, provenance block;
4. **verified**: requalifying ESQSUL 2021S1 now reports *"nothing to qualify",
   0 products*.

No coverage is lost: its window (05/02–07/03/2020) is already covered by
`ESQSUL_2020S1_HOBO_2_QLF` from a sound logger. The `.hobo` binary under
`bruto\` is untouched, so the decision is reversible by removing the two
exclusion entries.

### `HOBO1_ESQRODO_B1` — closed, and it had been closed for a while

Listed as open in `STATUS.md` while the entry above already recorded it
resolved. The corpus settles it: `ESQRODO_2025S1_HOBO_2_QLF`, 4,138 rows,
24.74–27.86 °C, 3,485 rows good. Its 16.8 h light peak is real and reproduced
across three exports, and it **drives no QC decision** — the corpus light window
is the fixed 60 days.

### `HOBO-incubacao_rodolito.csv` filed with the experiments it consolidates

The last item on the open list, and it was never a data problem — it was a
FILING problem. The sheet consolidates, by hand, the five rodolith incubation
experiments of RRDM 16a MAR 2023, stacked in one file under a `Sitio` column:

| RH50 | B1 | A5 | RH30 | RH18 | total |
|---|---|---|---|---|---|
| 542 | 484 | 481 | 422 | 361 | **2,290 rows**, 19–30/03/2023, 24.93–30.15 °C |

Those are exactly the five `Experimento ... INCUB RODOLITO` folders that sit in
the same campaign, each with its own `bruto\*.hobo`. So the sheet is a DERIVED
consolidation of data that already exists, per experiment, in its own folder.

It could never be qualified: the qualifier writes one product per deployment,
and this is five deployments overlapping in time in a single file — a product
structure would have to be invented. It yielded **0 products**.

The reason it kept coming back is that it sat in
`_EXPERIMENTOS\RRDM 16a MAR 2023\planilha\`, and **`planilha` is precisely the
folder name the driver walks for** (`qualify_site.py`, the `_EXPERIMENTOS`
branch: `if os.path.basename(root) != 'planilha': continue`). It came from the
CAMPAIGN ROOT of the field archive rather than from inside `HOBO\`, which is how
it landed there. Moved (owner decision, 2026-08-11) to:

```
HOBO\raw\_EXPERIMENTOS\RRDM 16a MAR 2023\HOBO\CONSOLIDADO INCUB RODOLITO\
```

beside the five experiment folders, with a `LEIA-ME.txt` explaining what it is,
why it is not qualified and where the per-experiment originals are. Content
untouched — MD5 `180440705a8924e0784731630959d1b5` verified before and after —
the manifest row updated with a dated note, and the emptied `planilha\` folder
removed. Verified after the move: the driver's own discovery walk now finds
**0 files** in that campaign.

One trap worth recording: the first manifest update **silently did nothing**.
The search string was `r'...\planilha\\'`, and in a raw string that trailing
`\\` is two characters, so it never matched the single backslash in the path.
The replacement reported success because a no-match replace is not an error —
it was caught only because the script printed the resulting value.

### Verification

45/45 self-tests, ruff clean — the app was not modified. Every count above was
read from the rebuilt index and the products themselves, not from the run log.

---

## 2026-08-13 — HOBO\raw inverted to campaign-first; the archive tidied

Owner request: make the two raw trees read the same way. The Seaguard layout
(campaign → site) is the standard; HOBO was site → campaign.

### The layout inversion

`reorg_hobo_raw.py` moved **123 directories** (111 site campaigns, 12
`_PISCINAS` pool campaigns; `_EXPERIMENTOS` was already campaign-first and was
not touched):

```
before   HOBO\raw\PAB3\RRDM 16a MAR 2023\{bruto,planilha}
after    HOBO\raw\RRDM 16a MAR 2023\PAB3\{bruto,planilha}
```

**The RRDM campaign names were kept.** The two numbering series cannot be
merged: HOBO runs `6a..22a`, Seaguard `1..12`, and only 8 of 15 HOBO campaigns
have a Seaguard counterpart at all (HOBOs are recovered on more expeditions).
Renumbering would invent numbers and destroy the identity the field team uses.

Whole directories were moved, never individual files. Verification, in
layers: content fingerprint before/after (489 files, identical md5 multiset);
then, independently, **every one of the manifest's 407 rows checked against
the file at its new path — 407/407 md5-identical, 0 missing**; the manifest's
`dest` column rewritten in the same pass (367 rows; the 40 untouched are all
`_EXPERIMENTOS`, accounted for by name).

### A latent record defect the re-check exposed

12 manifest rows still said `copied_verified` with pre-repair md5 AND size.
Cause: **`repair_unset_clock.py` never updated the manifest** (its two sibling
repair scripts do), and the two hand re-exports were never re-recorded either.
The record had been silently disagreeing with the archive since the August
repairs — found only because the reorganization forced a full re-check. Fixed
by the new `refresh_manifest_md5.py`: the 12 rows now carry the current
md5/size, status `repaired_in_place`, and a note stating the FILE was never in
doubt — the row was late. A gotcha note went into `repair_unset_clock.py`.

### The driver adapted, and proven equivalent

`qualify_site.py` (three walks: `plan`, `_owning_campaign`, `plan_buckets`
`_PISCINAS`, plus the FORA-skip glob) and `run_semester.py` (site enumeration)
now read campaign-first. Proof, strongest available:

- **discovery parity**: for all **137 HOBO products** in the index, the
  rewritten discovery re-finds a group with exactly the same input files —
  137/137, including the FORA/NA skip guards firing correctly;
- **full-stack controls** (tempdir, corpus untouched): `ESQSUL_2026S1`
  (4,285 rows) and `PLES_DENTRO_2026S1` (4,307 rows, the `_PISCINAS` branch)
  requalified from the new layout — every column identical to the corpus
  product, stamp aside;
- the ESQRODO 2020S1 re-file guard still plans **nothing**, as it must.

### The tables tidied

Owner request: the archive as clean as possible. `tidy_archive_tables.py`
moved the one-off analysis outputs and old reorganization paperwork
(`replicate_disagreement_sweep`, `replicate_referee_verdicts`, two
`a2_manifest`, `reorg_manifest`, `survey_master`) into **`CLAUDE\_registros\`**
with a LEIA-ME; deleted `manifest.csv.bak` (superseded). **The two
`manifest.csv` (provenance, written by the repair scripts) and
`qualified_index.csv` (read by four scripts) stay where the pipeline expects
them.** Today's operation backups of the HOBO manifest were also filed into
`_registros`. The root now holds exactly: `HOBO`, `SEAGUARD`, `_registros`,
`qualified_index.csv`.

### Still open (pre-existing, observed while verifying)

84 files under `HOBO\raw` have no manifest row — almost all `_EXPERIMENTOS`
campaigns staged after the original manifest sweep (RRDM 20a/21a/22a), plus
the two LEIA-ME notes. Not caused by this round; extending the manifest to
cover them is a separate decision.

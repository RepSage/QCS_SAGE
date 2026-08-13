# STATUS — QCS (Quality Control System — SAGE)

Volatile state. Every entry dated. Durable rules live in `CLAUDE.md`.

## 2026-08-13 — v11.2 MERGED and TAGGED; installer rebuilt; release publication pending

PR #20 merged (merge `e67b4a5`, which also carries the no-AI-attribution rule
committed to master in parallel). **Tagged `v11.2` → `e67b4a5`; branch deleted
local and remote; 50/50 self-tests and ruff clean re-verified on the merged
master before tagging.** The repository is PUBLIC (API answers 200 anonymously
— verified, and that is the call the updater makes).

Remaining, in order:
1. installer rebuilt from the tagged master → `QCS_Setup_v11.2.exe` on the
   Desktop (in progress at the time of this entry);
2. owner publishes the v11.2 Release (`RELEASE_v11.2_para_colar.md` on the
   Desktop) **with the setup attached as an asset** — the updater looks for a
   `QCS_Setup_*.exe` asset;
3. the live loop test: install the v11.1 setup, open QCS, accept the v11.2
   offer, watch it reopen updated.

## 2026-08-11 — v11.2 on branch `improvements-v11.2` (superseded by the entry above)

Self-update + Program Files support. `QCS_VERSION = 'v11.2'`,
`changelog/v11.2.md`, manual updated. **50/50 self-tests (2 new), ruff clean**,
source app opens under the new wiring. MINOR — the qualification path is
untouched.

- **`QCS_Update.py`**: startup check of GitHub releases/latest in a daemon
  thread (silent offline — the field notebook's normal state), one-click
  download + silent in-place upgrade + relaunch; *Help → Check for updates…*
  for the manual path. Batch/headless never import it, so corpus runs never
  touch the network. Never offers a downgrade; junk tags ignored (tested).
- **`writable_app_dir()`** (`QCS_Theme`): settings and crash log go beside the
  exe when writable (per-user installs — unchanged), else `%APPDATA%\QCS` —
  which is what makes Program Files installs work. Both tabs and the crash
  handler route through it; from source the path is byte-identical (tested).
- **Dual-mode installer** (`.iss`): one setup asks all-users (Program Files,
  admin) or just-me (no admin); `CloseApplications` + silent-upgrade relaunch
  for the self-update loop. `AppVersion` 11.2.

**The update check needs the repository PUBLIC** (owner decided to flip it):
while private, the API 404s and the check is silently idle — safe either way.

**Live end-to-end test, pending the release** (the honest proof, in order):
1. owner makes the repo public (Settings → General → Danger Zone → Change
   visibility) — then `curl api.github.com/repos/RepSage/QCS_SAGE/releases/latest`
   must answer 200 anonymously;
2. merge the PR; tag v11.2; rebuild the bundle + installer per
   `packaging/README.md` (AppVersion already 11.2);
3. publish the v11.2 Release **with `QCS_Setup_v11.2.exe` attached as an
   asset** (the checker looks for a `QCS_Setup_*.exe` asset);
4. install the OLD `QCS_Setup_v11.1.exe` (Desktop), open QCS → it must offer
   v11.2 → one click → app reopens as v11.2. That closes the loop.

## 2026-08-11 — a self-contained installer exists: QCS_Setup_v11.1.exe

Built for the field notebook (no Python, no Anaconda, no dependencies needed).
**54 MB installer** wrapping a 195 MB PyInstaller onedir bundle; recipes
versioned under `packaging/` (spec + iss + README), build artifacts gitignored.
No source change — the frozen-aware paths from the v2.0 era still work — so
**`QCS_VERSION` did not move**.

Measured, end to end, on this machine: silent install to `%LOCALAPPDATA%\QCS`
(no admin), the installed app opens in **~3–4 s warm** (first-ever launch
~15–20 s while matplotlib builds its font cache, one time), Start Menu
shortcuts created, silent uninstall removes everything. 48/48 self-tests also
pass on the pinned build venv itself.

Three traps the recipe now documents, all hit while building:
- **onedir, never onefile** (onefile unpacks everything per launch = the
  30–60 s startup);
- **the venv sits on Anaconda's Python**, whose `_ctypes`/`_ssl`/tkinter load
  DLLs from `anaconda3\Library\bin` — that folder must be on PATH during the
  build or the bundle dies at startup with "DLL load failed importing _ctypes";
- **always `--clean`**: a cached analysis silently reuses the old dependency
  scan, which made the DLL fix look like it had failed.

Deliverable on the Desktop: `QCS_Setup_v11.1.exe`. Deps pinned to the base
env's exact versions (pandas 2.2.3, numpy 2.1.3, matplotlib 3.10.0, scipy
1.15.3, gsw 3.6.21) — the venv's default resolution had picked pandas 3.x,
which would have frozen an app on library versions the corpus was never
validated against.

## 2026-08-11 — v11.1 RELEASED

PR #19 merged (merge commit `61bc6a4`, message customized to the PR title —
not the GitHub default). **Tagged `v11.1` → `61bc6a4`, pushed; branch
`improvements-v11.1` deleted local and remote; `master` up to date.** 22 tags
now. The GitHub Release text is ready on the Desktop
(`RELEASE_v11.1_para_colar.md`) — publishing it is the one step left, manual.

`QCS_VERSION = 'v11.1'`, `changelog/v11.1.md`, manual updated to v11.1.
**48/48 self-tests, ruff clean.** MINOR — no QC result changes, verified on
real corpus inputs (see below).

The four app changes, each born from a measured incident of this week:

- **`Flag_dens` / `Flag_depth`** (TSCP layout): derived flags for the computed
  columns — dens = worst(Flag_T, Flag_S), depth = Flag_P. Motivated by RRDM03
  reading 996 kg/m³ for 90% of a deployment with no warning on the Density
  column. Additive only; HOBO layout untouched; old+new files stack in
  `build_database` (old rows get NaN).
- **`anomalous` verdict** in `light_clock_phase`: the "off-noon but no clock
  accusation" middle ground (shading / fouled channel) was free text nothing
  could read — the EsquecidoSul product shipped GOOD because the guard only
  fires on clean ±12 h. Now structured, in the log and in batch provenance
  (`ANOMALOUS PHASE`). Warning only: no shift, no flags.
- **Settings-reset dialog** in `QCS_App` on first launch after a version
  change (the reset is old v3.2 behaviour; only the announcement is new).
  Lives in the shell, so headless/batch can never block on it — verified.
- **Once-per-run warning dedup** (`QC.reset_run_warnings()` at RUN start): the
  window-span warning used to repeat up to 9× per file.

**Real-data verification (corpus untouched, tempdir output)**: RH3 2019S2
Seaguard mooring — 97 rows, every pre-existing column identical to the corpus
product, new columns correct row by row; ESQRODO_B1 → `anomalous`, peak 16.8 h,
flags identical to its corpus product; healthy ESQSUL B4 → not anomalous,
peak 11.7 h.

**Batch lane in the same change set (no version impact)**:
`build_data_package.py` (site/period delivery bundle, promoted from the August
one-off; run against RH18 2025 and verified); `drop_stale_products.py` now
MOVES into `CLAUDE\_deleted\<date>\` instead of deleting; `build_index.py` ends
every corpus round by running `sweep_value_integrity.py` (exit non-zero on a
pipeline defect); the sweep speaks English now.

**Pending**: only the GitHub Release (manual, text on the Desktop). The corpus
does NOT need requalifying (results unchanged); the next natural corpus round
will add the two derived columns and re-stamp.

## 2026-08-11 — the whole corpus is on v11.0; one logger discarded

**Corpus: 314 products** — HOBO 137, Seaguard 123, Doppler 54, 34 with CO2.
**All 314 carry the v11.0 stamp** (was: 138 at v11.0, 169 at v8.1, 4 at v9.0,
4 at v9.1 — the Seaguard side had never been run through v9.0–v11.0).

### The version question, and what it actually was

The repository was already correct. It holds exactly **two** version STAMPS —
`QCS_VERSION` and the manual's header — and both already read v11.0. Every other
mention is a HISTORICAL reference ("added in v8.0", "the pre-v9.0 behaviour",
"Per-variable Flag_ columns (v4.0)"), which is a fact about the past: rewriting
those to v11.0 would make them false. 38 of the manual's 39 mentions are of this
kind. **What was stale was the DATA**, and that is now fixed.

### Requalifying the Seaguard side changed nothing but the stamp — verified

The diff v8.1→v11.0 names `doppler_qc` and `vertical_gradient_test`, which WOULD
affect this side; they are only the enclosing functions of code added below
them, and all 12 removed lines sit in `light_fouling_baseline` (HOBO). But
`qualify_site.py` gained ~400 lines that touch naming and grouping for every
instrument, so it was measured before the full run: RH3/2019S2 (Seaguard +
Doppler + CO2, exercising the GMT-3 bypass) was backed up, requalified and
diffed — **same 3 products, data identical, only the stamp changed**.

After the full run, against the previous index: **0 products appeared, 1
disappeared** (the discard below), and only one row count moved — a stale index
entry, not a data change (see below). 8 products FAILED to build; all 8 are
pre-existing raw-data failures that **never existed in the index** (verified
name by name), so nothing was lost.

Row accounting: 695,173 → 694,803 = **−370 = −366** (the discarded product)
**−4** (`ESQRODO_2025S1_HOBO_2_QLF`, whose file was regenerated at 11:28 during
the earlier `.hobo` re-export work while the index had not been rebuilt since;
the Seaguard round started at 14:14 and never touched it).

### `HOBO#02_Ref.EsquecidoSul` DISCARDED — and it was not blocked as claimed

Owner decision: "essencialmente descartável agora que vimos que tem tanto erro".
Acting on it exposed a real defect in this file's own notes: **the product
existed**. `ESQSUL_2021S1_HOBO_QLF` had been regenerated the same morning,
stamped v11.0, carrying **337 of its 366 rows flagged GOOD** from a sensor that
reads to 156 °C. `_fail_on_wrong_clock` never fired — it only triggers on a
clean ±12 h accusation, and this logger's light peaks at 4.4 h, which raises
none. The earlier claim that it was "left unqualified on purpose, blocked by the
guard" was simply wrong.

Removed cause-first, because deleting alone is how `ESQRODO_2020S1` came back:
both exports (`.csv` and `.xlsx`) are now in `EXCLUDED_REPLICATES` with the
evidence, and `drop_stale_products.py` gained a **`DISCARDED`** mode — a removal
with no replacement, gated on the raw already being excluded, so it refuses to
delete a product whose cause is still live. Verified after the fact:
requalifying ESQSUL 2021S1 reports *"nothing to qualify", 0 products*. No
coverage lost — 05/02–07/03/2020 is already covered by `ESQSUL_2020S1_HOBO_2_QLF`
from a sound logger. The `.hobo` binary in `bruto\` is untouched.

### `HOBO1_ESQRODO_B1` is CLOSED, not open

*(Corrects the "Still open on the data" list below, which was stale.)* The
re-export resolved it: `ESQRODO_2025S1_HOBO_2_QLF`, 4,138 rows, 24.74–27.86 °C,
3,485 rows good. Its light peaks at 16.8 h across three independent exports —
that is what the logger recorded, and it **drives no QC decision**, because the
corpus light window is the fixed 60 days. Nothing to fix.

45/45 self-tests, ruff clean.

## 2026-08-11 — the release history is complete on GitHub: 21 tags, 21 releases

Verified on the releases page, not assumed: **21 published releases against 21
tags, a 1:1 match with no version missing and none duplicated.** The owner
published them by hand.

- **Three tags were created retroactively** in this round: `v1.0` → `0932f32`
  (the commit that names itself "QCS_SAGEv1.0"; corroborated by the v1.0 manual
  PDF, whose cover reads the same), and `v2.0` and `v2.1` → **both at
  `02d3983`**.
- **v2.0 and v2.1 share a commit because they have to.** The repository has **no
  commits at all between 19 Dec 2024 and 11 Jun 2026** — both versions happened
  inside that hole, when the project was versioned by renaming the working
  folder instead of committing. The tags record the ORDER, which is known, not
  the commit, which was never made.
- **What v2.0 was, inferred from evidence** (`RELEASE_v2.0_para_colar.md` on the
  Desktop keeps the full reasoning): the release that turned QCS from scripts
  into a packaged Windows application. `resource_path`/`_MEIPASS` exist nowhere
  in the Dec 2024 code yet are being bug-fixed by v2.1, and the buggy line names
  the `QCS_SAGE_v2.0` folder — which also already contains `sourceCode\`. So the
  **`sourceCode/` reorganization belongs to v2.0, not v2.2**: the v2.2 changelog
  claims it only because it was written against an 18-month-old baseline.
- Release texts from v3.2.1 down were **rewritten in English** from the original
  changelogs (they had been pt-BR).

Nothing is pending on releases. Note for next time: `.pyc` files committed in the
early history embed the compile-time source path, which is how the folder-name
versioning was dated — a useful forensic trick when the git record is silent.

## 2026-08-11 — Seaguard swept for the scale defect: nothing there, and nothing can be

Read-only sweep, no data changed and **no version bump** (nothing under
`sourceCode/` outside `batch/` was touched). Closes the last item that was open
from the v11.0 round.

- **The defect cannot occur on the Seaguard side.** Its raw archive is 255 AADI
  `.bin` sessions and no text data; a lost decimal separator is a text accident.
  Verified by decoding a real session: 8 of 9 numeric columns carry decimals on
  100% of values, the one all-integer column being `Record Number`. The only
  text input, the MiniCO2 `.txt`, carries its own `%07.2f` format line.
- **Measured anyway, over both families**: new `batch/sweep_value_integrity.py`
  ran the reader's three gates over all **315 products** — 3 scale suspects,
  **0 passing all three gates**, all three explained (two alkaline pH profiles;
  `PAB3_2024S2_HOBO_2`, the known `(ERRO)` file the reader correctly refuses).
- **The QC is catching what it should**: 3,361 values outside the instrument's
  physical limit across 6 products, **100% flagged 4**; 137 of 137 out-of-range
  DOM values marked. Zero unflagged, either family.
- **Not a defect, but worth knowing**: `RRDM03_C_2019S1` and
  `RRDM03_D_2019S1_2` have conductivity ≈ 0.017 mS/cm for **90% of the
  deployment** — no usable salinity or conductivity, temperature fine, rows
  already flagged 3. Details and the two traps the sweep itself fell into are in
  `sourceCode/batch/CORPUS_LOG.md`.

45/45 self-tests, ruff clean.

## 2026-08-10 — v11.0 (the real one): reader fixes

`QCS_VERSION = 'v11.0'`, `changelog/v11.0.md`, manual updated. **Tagged `v11.0`
at `2d0adb3`, which is `master`.** No PR — this round went straight to `master`.
45/45 self-tests, ruff clean. This one does change `sourceCode/*.py` outside
`batch/`, which is what a version bump is for.

*(Corrected 2026-08-11: this entry read "not tagged, no PR yet", which was
already false — `git log -1 v11.0` resolves to `2d0adb3`.)*

- **Lost decimal separator**: some HOBOware xlsx wrote `25.125 degC` as the
  integer `25125`. Five products carried temperatures in the tens of thousands.
  `_hobo_fix_temp_scale` recovers them, gated three ways — everything out of
  −5…60 °C, values must be INTEGERS, and one power of ten must fix all of them.
  The integer rule is load-bearing: without it a sensor genuinely reading
  −84.77…156.53 °C gets "recovered" into −0.85…1.57 °C. That false positive was
  in the first draft and is now self-test #27.
  - 4 of the 5 rescaled. `PAB3_2024S2_HOBO_2` was correctly REFUSED (÷1000 still
    gives 68–89 °C) — it comes from the file the team already named `(ERRO)`.
  - 3 products keep out-of-range temperatures (156.5, 78.8, 49.2 °C) and are
    left alone: genuinely bad sensors, which QC should flag, not rescale.
- **Temperature-only loggers**: products are named `..._TEMP_ONLY_QLF`, and the
  collapsed-clock repair now sends them to the temperature fallback instead of
  refusing them for lacking light. That recovered `PAB3_30062016_PAREDE.csv`
  (17,668 rows, 8,833 duplicated timestamps) — the file that first exposed the
  referee's dedup problem in v9.0.

**Corpus: 315 products** — HOBO 138, Seaguard 123, Doppler 54, 34 with CO2.
Index duplicate-input warning silent.

### Still open on the data

*(Superseded 2026-08-11 — see the top entry. The first two are CLOSED: ESQRODO
B1 was resolved by the re-export, and Ref.EsquecidoSul was discarded by owner
decision. Only the third remains.)*

- ~~`HOBO1_ESQRODO_B1_050424_160325.xlsx`~~ — **closed**: re-export resolved it.
- ~~`HOBO#02_Ref.EsquecidoSul_RRDM_04022020_240221.csv`~~ — **discarded** by
  owner decision, raw excluded so it cannot be requalified.
- ~~`HOBO-incubacao_rodolito.csv`~~ — **filed, 2026-08-11.** Never a data
  problem: it consolidates by hand the five rodolith incubation experiments of
  RRDM 16a MAR 2023 (2,290 rows, 5 sites in one file), all of which already
  exist separately with their own `.hobo`. It kept reappearing only because it
  sat in a `planilha\` folder, which is what the driver walks for. Moved to
  `_EXPERIMENTOS\RRDM 16a MAR 2023\HOBO\CONSOLIDADO INCUB RODOLITO\` with a
  `LEIA-ME.txt`; MD5 verified, manifest updated, driver now finds 0 files there.

**Nothing is open on the data.**

## 2026-08-10 — there is NO v11.0; the app is still v10.0

The whole clock-repair round touched the **data and the batch drivers**, never
the program. Verified: `git diff v10.0..HEAD -- sourceCode/*.py` is one line,
the version constant itself. Bumping `QCS_VERSION` was a mistake and had a real
cost — the constant is version-gated for user settings, so a bump resets saved
QC criteria on next launch for a release that changed no criterion.

- `QCS_VERSION` back to **v10.0**; the manual back to v10.0; the 138 HOBO
  products re-stamped by requalifying (they carried a phantom `v11.0`).
- `changelog/v11.0.md` moved to **`sourceCode/batch/CORPUS_LOG.md`** — a dated
  record of irreversible operations on the ARCHIVE, kept beside the scripts
  that perform them. It is not a `changelog/` entry: the changelog is for app
  releases, and none of this is one.
- **Rule for next time**: `QCS_VERSION` changes only when `sourceCode/*.py`
  outside `batch/` changes. Corpus work goes in `CORPUS_LOG.md`.

### Re-file rule (the ESQRODO duplicate, fixed at the source)

Deleting `ESQRODO_2020S1` was not enough — the next full run recreated it,
because the same export is filed under two campaigns and the cause was still
there. `_owning_campaign` now resolves this across ALL campaigns of a site
(a re-file is by definition in a different SEMESTER, so a per-semester check
could never see it): the owner is the earliest campaign whose month falls on
or after the end of the data — the one that recovered the logger. `ESQRODO
2020S1` now qualifies nothing, and the index's duplicate-input warning is
silent.

**Corpus: 315 products** — HOBO 138, Seaguard 123, Doppler 54, 34 with CO2.
60-day validation 0 inconsistent. 11 of 138 HOBO products still carry
duplicated timestamps, all traceable to the four exports listed as open in
`CORPUS_LOG.md`.

## 2026-08-10 — v11.0 (cont.): xlsx side repaired too; 4 stale products to delete

- **24 `.xlsx` exports repaired** as well (the collapsed clock sits as cell
  text). Light peaks at 10.8–12.0 h on all of them. Because saving a workbook
  rewrites the whole file, the xlsx path refuses unless the logger's `.hobo`
  binary sits beside it — 2 refused on that ground, 1 more for light phase.
  Total: **65 exports repaired, 15 refused**, idempotent (2nd pass: 0).
- Corpus requalified again: index **323 products**, HOBO **146**, 60-day
  validation **0 inconsistent**. Products still carrying duplicated timestamps:
  33 → **21** (the rest are the refused files and their products).
- **The replicate rule was too tight, and the repair exposed it.** Grouping
  required both ends within 1 day; with the collapsed clock, spans were
  compressed and that always held. With real timestamps, TIM2 2019S2 ends 26 h
  apart and PNOR 2024S1 starts 34 h apart — pairs are started and stopped by
  hand, and one logger often records past its twin — so genuine replicates
  split into two products each. `_same_deployment` now also accepts both ends
  within 3 days **when the two durations differ by less than 5%**: that is what
  separates a hand-offset pair from different deployments (BRITAS vs incubation
  differ by 150×, not 5%). Measured over the whole archive before applying:
  exactly **3 folders regroup, all correct merges, no spurious ones**.
- **7 stale products DELETED** (owner authorised, 2026-08-10), each in full —
  CSV, DataView folder, reports files and provenance block: `TIM2_2019S2_HOBO_1/_2`,
  `PNOR_2024S1_HOBO_1/_2`, `PNOR_2026S1_HOBO_1/_2`, `PAB3_2022S2_HOBO_3`. Every
  one was re-verified against the live index first (replacement exists, is
  newer, covers the same raw inputs); none was skipped. **Final corpus: 316
  products — HOBO 139, Seaguard 123, Doppler 54, 34 with CO2.** 60-day
  validation 0 inconsistent, 0 orphan DataView folders, and the index's
  duplicate-input warning now reports only the three pre-existing pairs.
- **The three PRE-EXISTING duplicate pairs are RESOLVED** (2026-08-10):
  - `ESQRODO_2020S1` dropped. The same byte-identical raw file was archived
    under two campaigns; the deployment ended 05/04/2019, so the campaign that
    recovered it is `RRDM 6a MAI 2019` and the copy filed under `RRDM 9a MAR
    2020` is a re-file. `ESQRODO_2019S1` survives.
  - `PLES_FORA_2025S1` and `SGOM_FORA_2025S1` dropped. Owner: "o monitoramento
    de sítio e o controle fora da piscina são a mesma coisa" — the `_FORA` pool
    control IS the site logger, so the site product survives. `plan_buckets`
    now skips a `<SITE>_FORA` bucket whose files also live under that site, by
    FILE NAME (the MD5 rule could not catch it: the two copies are re-exports,
    not byte-identical). `_DENTRO` buckets are untouched — inside the pool is a
    genuinely different measurement.
- **2 more xlsx repaired** (`HOBO2_-_ESQNORTE_(B2)_-_19092022_UMIDADE...` and
  `HOBO2_PAB3_A3_220324_130924 (ERRO)`), which had been refused for lacking a
  `.hobo` original: the script now writes a `<stem>.original.xlsx` backup into
  `bruto\` first, so the repair is never the only copy in existence. Total
  **67 exports repaired, 13 refused**.
- **Corpus after all of it: 313 products** — HOBO 136, Seaguard 123, Doppler
  54, 34 with CO2. 60-day validation **0 inconsistent**, and the index's
  duplicate-input warning is now **silent**.
- `build_index.py` now **warns when one raw export feeds two products**, which
  is exactly this failure; it also flags some pre-existing DENTRO/FORA bucket
  overlaps worth a look (ESQRODO 2020S1, PLES/PLES_FORA 2025S1, SGOM/SGOM_FORA
  2025S1).

## 2026-08-10 — v11.0: collapsed clock repaired on the CSV side

`QCS_VERSION = 'v11.0'`, `changelog/v11.0.md`. **Unreleased** — committed on
`master`, not tagged. 44/44 self-tests, ruff clean.

- **41 raw CSV exports repaired in place** by the new
  `batch/repair_collapsed_clock.py`; light now peaks at 11.5–12.9 h on all of
  them. Idempotent (second pass repairs 0). Manifest updated.
- **Corpus requalified**: index 316 → **319 products** (HOBO 139 → 142); the
  60-day validation still reports **0 inconsistent**.
- **STILL OPEN — the same defect in 34 `.xlsx` exports.** The repair scans
  `.csv` only, and `_sheets` prefers `.xlsx`, so **33 of 142 HOBO products still
  carry ~50% duplicated timestamps**. Rewriting workbooks in place is a
  different risk (whole-file rewrite) and was left for an explicit decision.
  The algorithm carries over unchanged.
- **NEW defect class: loggers whose clock was never set — 11 files, OPEN.**
  Listed with full paths and evidence in
  `sourceCode/batch/wrong_clocks.csv` (regenerate with `batch/report_unset_clocks.py`;
  the file was `relogios_errados.csv` and the script name here was wrong). They
  are NOT one problem:
  - **6 files** have the data duration matching the archived deployment dates
    almost exactly (353 vs 353, 102 vs 103, 104 vs 104) with a clean constant
    offset (700, 1223, 1225 days) — a factory-epoch clock:
    `Hobo1_RRDM_RecEsqSul2_050320_210221`, `Hobo_RRDM_RecEsqSul2(B5)_...`,
    `HOBO1/2_PAB3_110521_220821`, `HOBO1/2_PNorte_090521_210821`.
  - **2 files** (`HOBO_PAB3_160320_110521`, `HOBO_Parede_PAB3_...`) have the
    same ~699-day offset but durations that do NOT match the name (364/344 vs
    421) — something else is also wrong.
  - **2 files** carry no dates in the name at all.
  - **1 file** (`HOBO1_ESQRODO_B1_050424_160325.xlsx`) has CORRECT dates
    (−2 days) and only the time of day off — a different defect entirely.
  **The 6 unambiguous ones are now REPAIRED** by
  `batch/repair_unset_clock.py`: DAY offset from the archived dates, HOUR from
  the light phase, and the result checked against the TEMPERATURE of
  contemporaneous loggers at other sites — independent of the light, so the
  check cannot pass by construction. Results: light lands at 11.5–12.3 h and
  temperature correlates **+0.88 to +0.99** with the region over 104–355
  overlapping days. Offsets were clean constants (+702 d −8 h; +1225 d −11 h;
  +1227 d −11 h). Requalifying recovered **PAB3_2021S2 and PNOR_2021S2**, which
  had been failing outright with "fewer than 2 valid timestamps".
  **Corpus: 315 products** — HOBO 138, Seaguard 123, Doppler 54. 60-day
  validation 0 inconsistent.

### The wrong-clock files after the field records (2026-08-10)

The owner supplied the field launch/retrieval dates. **Three more were repaired**
with them (`repair_unset_clock.py`, now 9 files): `HOBO_PAB3_160320_110521` and
`HOBO_Parede_PAB3_...` (+701 d, launch 16/03/2020) and `HOBO1_RodoRaso_17022_200521`
(+702 d, launch 17/02/2020). Their data is shorter than the time in the water
because the loggers stopped before retrieval — only the LAUNCH date anchors the
epoch, which is why the field record was needed. Temperature against the region:
r = +0.78 to +0.85 over 345–460 days.

**Independent corroboration on RodoRaso**: the repaired series ends 21/05/2021,
one day after the retrieval date the owner gave (20/05/2021) — and the end was
never used in the fit. The file name `..._17022_200521` encodes the same pair;
the date parser had missed it because the first field has 5 digits, not 6.

**Two remain, and neither is a plain clock error** — measured on their
reconstructed versions, the light and the temperature disagree about what the
correction should be, so no single rotation fixes both:

| file | light | temperature | reading |
|---|---|---|---|
| `HOBO#02_Ref.EsquecidoSul_RRDM_04022020_240221.csv` | 4.4 h | **12.0 h** | temperature is already near the corpus median (13.7 h), so the CLOCK is roughly right and the LIGHT channel is anomalous (shading). It also fails the sampling-regularity gate: only 67% of steps land on the interval |
| `HOBO1_ESQRODO_B1_050424_160325.xlsx` | 16.6 h | 0.4 h | the two channels disagree by ~8 h; dates are correct (−2 d). Its second half-day candidate is not reconstructible, so the temperature fallback has nothing to compare against |

Neither should be rotated: aligning the light would break the temperature and
vice versa. Both need a HOBOware re-export from the `.hobo` binary, which is the
inference-free route. **Note this does not block their use**: the corpus light
cutoff is the FIXED 60-day window, so light phase drives no QC decision.

A new fallback was added to `repair_collapsed_clock.py` for the general case:
when the light cannot choose the absolute half (shaded or fouled channel), the
half whose **temperature** peaks nearer the corpus median 13.7 h wins, within a
5 h tolerance. It did not rescue these two, but it is the right rule.
- **The clock guard was too broad**: `_fail_on_wrong_clock` now skips the
  `_EXPERIMENTOS` bucket. Macroalgae incubations run in tanks, where "light
  must peak at noon" is simply false; it was failing two RH products and
  leaving their stale 06/08 files indexed.
- **Seasonal residual: closed as "do not pursue".** The regional-witness idea
  (other sites as an independent light reference, the v9.0 referee pattern) was
  measured before being built and fails twice: only **11 of 111** series have
  ≥50% contemporaneous coverage, and on those it is no better than the
  astronomical curve (better on 5, worse on 6). Fixed-60d stays the standard.

## 2026-08-10 — v9.1 and v10.0 RELEASED; nothing pending

The light round is closed. `master` is at `f37e39c`, working tree clean,
**44/44 self-tests pass and `ruff check .` is clean** on it (verified today).

- **Merged in two PRs from the same branch**: [#17] carried the first five
  commits (`4a0f2db`), [#18] the last one (`f37e39c`). Two PRs because commits
  landed after the first was opened — not a split of the work; `master` holds
  all six.
- **Tagged and pushed**: `v9.1` → `b497c7e`, `v10.0` → `f37e39c`. Tags now run
  v5.1, v6.0, v7.0, v8.0, v8.1, v9.0, v9.1, v10.0.
- `improvements-v9.1` deleted local and remote; `origin` holds only `master`.
- PR #18's auto-filled title/body (truncated at `(owner deci…`, body opening
  with the orphan `…sion)`) were edited on GitHub after the merge — cosmetic
  only, the code and history were never affected.

**No release work is pending.** The next round starts from an updated `master`.

## 2026-08-10 — clock repair applied IN PLACE to raw; corrected\ deleted

Owner decision, explicit: "nesse caso específico pode editar o raw". The eight
AM/PM-swapped 2022S1 CSVs (PLES/SGOM/TIM2) now carry the −12 h repair in the
raw tree itself; `HOBO\corrected\` is gone. `correct_clock.py` became the
in-place repair recipe (gated: only an ACCUSED file is shifted, so re-running
never double-shifts; validated locally before replacing; idempotence verified —
second run reports 8/8 "already corrected"). The raw `manifest.csv` rows carry
new checksums, status `clock_corrected_-12h` and a dated note; the original
`.hobo` binaries under `bruto\` are untouched. The three products requalified
from the repaired raw are data-identical to the corrected-twin era (verified).
Driver: `_prefer_corrected`/`_require_corrected` removed; `_fail_on_wrong_clock`
now fails any batch HOBO product whose input is accused of a 12 h phase error.

## 2026-08-07 — v10.0: seasonal normalization of the adaptive light rule

*(Released 2026-08-10 — see the entry at the top.)* Written stacked on v9.1 on
the same branch. **MAJOR**: adaptive-mode `Flag_lux` can change; the corpus
(fixed-60d mode) is unaffected — one product requalified under v10.0 came out
byte-identical (verified).

- `clear_sky_factor(dates, latitude)` in `QCS_Tests.py`: noon solar elevation
  with standard atmospheric attenuation (T=0.75), normalized to the annual max.
  `light_fouling_baseline(..., latitude=...)` divides each daily peak by it, so
  the adaptive decision runs on "fraction of the seasonal ceiling";
  `latitude=None` = the old rule exactly. Latitude comes from the region
  selection, now ENABLED for HOBO. The review plot draws baseline/threshold as
  seasonal CURVES.
- **The curve was chosen against the corpus** (111 series): noon+airmass beats
  raw noon and ties daily-H0 on numbers (asymmetry 25 → 19 p.p., over-cut on
  falling-light installs 37% → 34%, spurious keeps 20% → 15%) and wins on
  physics (the daily peak is a noon quantity). T is textbook 0.75, deliberately
  NOT tuned — results are flat T=0.75–0.55, and tuning would be circular.
- **Honest limit, measured**: the correction removes only the deterministic
  part of the seasonal confound; winter cloud/turbidity dominate the deep
  declines. The fixed-60d window remains the corpus standard.
- 44/44 self-tests (new #26), ruff clean. `QCS_VERSION = 'v10.0'`,
  `changelog/v10.0.md`, manual updated to v10.0.

*(Released 2026-08-10 — see the entry at the top.)*

## 2026-08-07 — v9.1 grew into "the light release"; corpus on the fixed 60-day window

*(Released 2026-08-10 — see the entry at the top.)* 43/43 self-tests passed at
the time of this entry; 44/44 after v10.0's test #26.

- **Fixed light-cutoff mode shipped** (user decision): `Light cutoff:
  Reviewed (adaptive) / Fixed window` in the Qualification tab, HOBO-only,
  adaptive still the app default. Fixed = light BAD from `lux_fixed_days` (60)
  after deployment, no review. Motivation measured, not assumed: at 18 °S the
  clear-sky ceiling falls to 60% of summer in winter, and with the adaptive rule
  deployments walking into falling light were over-cut (>90% of light discarded)
  in 37% of cases vs 12% walking into rising light.
- **The whole HOBO corpus is requalified with fixed-60d** (14 semesters, sites +
  buckets, `QCS_HOBO_ONLY=1`). Validation: 139 products — 120 split exactly at
  start+60 d, 16 shorter than the window (nothing cut), 3 without usable light,
  **0 inconsistent**. Index rebuilt: still 316 products. Corpus-wide, 70.7% of
  the light samples are now BAD (the fixed window discards more than the
  adaptive rule's ~37% — uniformity was chosen over volume). Every product's
  provenance records `light : fixed-60d window` and a per-file `clock :`
  verdict.
- **The clock repair moved to the data side** (user decision) — *this step was
  itself superseded on 2026-08-10, when the repair went in place into the raw
  and `corrected\` was deleted*: corrected copies
  under `CLAUDE\HOBO\corrected\` generated by `batch/correct_clock.py`
  (validated locally before touching the share); the driver prefers the
  corrected twin, labels it `[clock-corrected]`, and `_require_corrected`
  refuses to qualify a known-bad file from raw. The in-driver
  `CLOCK_CORRECTIONS` patch is gone. Requalifying the 3 products via the
  corrected files reproduced the patched output byte-for-byte (version stamp
  aside).
- **Adversarial review before the corpus run confirmed 6 defects, all fixed**:
  fixed mode dropped the data-integrity warnings; the light-window SVG was
  skipped exactly when the cut had no data explanation; batch swallowed clock
  accusations on successful products (now in provenance); `correct_clock` wrote
  to the share before validating; `light_plots` could hand the kept replicate a
  different logger's plot; an xlsx re-export would outrank a corrected csv twin.
  Plus one found by the corpus run itself: the batch driver now DECLINES the
  replicate-review recommendation (`review_replicates -> None`) instead of
  crashing headless — ESQCENTRAL 2024S1 keeps both replicates, as decided.
- Batch FAILs in the full run: PAB3_2019S2_HOBO_2, PAB3_2021S2, PNOR_2021S2,
  SGOM_2023S1 — all pre-existing raw-data failures ("fewer than 2 valid
  timestamps"); none ever existed in the index.
- **Open question (seasonal)**: over-cutting is strongly seasonal and
  understood; under-cutting associates with autumn installs (22% vs 8%) but the
  end-of-deployment trend does NOT explain it (16/14/17% flat) — mechanism
  unresolved. The principled adaptive-mode fix (normalize daily peaks by the
  astronomical clear-sky curve) is proposed, not implemented.

## 2026-08-06 — where the repository is

*(Superseded: v9.1 and v10.0 were released on 2026-08-10 — see the top entry.
The state below is kept for the reasoning, not for its status claims.)*

- Health check that day: **42/42 self-tests pass**, `ruff check .` clean, on the
  Anaconda base interpreter (3.13.5).
- **There is no `gh` CLI on this machine** — pull requests are opened and edited
  through the browser. (Still true.)

## 2026-08-06 — known-bad artifacts and open questions

### Collapsed 12-hour clock: 53 of 116 qualified HOBO products — NOT repaired

Some HOBOware exports in pt-BR locale write times as `04h0min0s` with **no AM/PM
marker**, so every afternoon reading lands on top of its morning twin. Signature:
no sample after 12:59, ~50% duplicated timestamps carrying conflicting values.

- **Detected and named** since v9.1 by `QCS_Tests.light_clock_phase`, which
  reports it as `collapsed` and deliberately prescribes **no shift** — the remedy
  is not to move the series.
- **Repair is possible and not implemented**: raw rows are in chronological
  order, so walking them and adding 12 h whenever the parsed time goes backwards
  reconstructs the afternoon half. That would recover **46% of the HOBO archive**
  and double its effective resolution. **Awaiting a decision.**
- **This retro-invalidates a v9.0 choice.** The replicate referee's
  duplicate-timestamp handling (`x[~x.index.duplicated(keep='first')]`) silently
  keeps the AM reading and discards the PM one on exactly these files — it papers
  over the failure instead of reporting it. Revisit it together with the repair.

### The fouling cutoff that started the v9.1 hunt — partly answered

Correcting the three antiphase clocks left the fouling verdicts essentially
unchanged (PLES: 5 of 209 days reach the threshold before and after; SGOM: 9 of
213, last one on the same date). The daily peak is a per-calendar-day maximum, so
a uniform 12 h shift regroups samples without moving it. The clock defect was
real but was not the cause.

**v10.0 answered the deterministic half**: the cutoff was entangled with season
(over-cut on falling-light installs 37% vs 12% on rising-light ones), and the
clear-sky normalization removes that part — asymmetry 25 → 19 p.p. **The
residual is not explained**: winter cloud and turbidity dominate the deep
declines and no deterministic curve removes them. Under-cutting still
associates with autumn installs (22% vs 8%) with no mechanism found — the
end-of-deployment light trend does NOT explain it (16/14/17%, flat).

### Failure A (antiphase) — fixed; the fix moved twice, now lives in the raw

Three products launched with AM/PM swapped — PLES, SGOM and TIM2 2022S1
(campaign RRDM 14a MAR 2022). After a −12 h shift all three land on the phase of
the sound loggers of the same semester (11.2–11.6 h, 99–100% daylight energy).

**The fix migrated twice, both times by owner decision**, so beware of older
descriptions: v9.1's changelog first recorded it as `CLOCK_CORRECTIONS` inside
`qualify_site.py`; on 2026-08-06 it became corrected twin copies under
`HOBO\corrected\`; on 2026-08-10 it was **applied in place to the raw CSVs** and
`corrected\` was deleted. Current state is the top entry of this file.

It repairs **Failure A only**. It checks that its output is not `collapsed`, but
does not reconstruct Failure B.

## 2026-08-06 — housekeeping

- `AGENTS.md` deleted. It was an untracked byte-for-byte copy of `CLAUDE.md`
  differing only in its header line, kept in sync by hand.
- `CLAUDE.md` rewritten: it had been stale since v4.0 — it claimed v4.0 was
  unreleased with nothing pushed, described two launcher `.bat` files that no
  longer exist (there is one, `QCS.bat` → `QCS_App.py`), told the reader to run
  bare `python`, and said the pt-BR → English migration was still in progress
  (it is complete; no Portuguese strings remain under `sourceCode/`).

## Corpus size — verified 2026-08-10

`qualified_index.csv` holds **316 products** (139 HOBO, 123 Seaguard, 54
Doppler; 34 with CO2 merged), rebuilt after the fixed-60d requalification. The
count went 315 → 316 in the v9.0 round, when excluding a faulty replicate
recovered a deployment that the broken export had been aborting.

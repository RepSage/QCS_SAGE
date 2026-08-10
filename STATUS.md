# STATUS — QCS (Quality Control System — SAGE)

Volatile state. Every entry dated. Durable rules live in `CLAUDE.md`.

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
  `scratchpad/relogios_errados.csv` (regenerate with `unset_clocks.py`). They
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

# CORPUS LOG — operations performed on the archive itself

What was done to the DATA under `CLAUDE\HOBO\raw` and `\qualified`, when, and
why. This is not a `changelog/` entry: the app has its own version and its own
release notes, and nothing here changes the program. It is kept beside the
scripts that did the work, because re-running them is how any of it is
reproduced.

Lane check, so this file does not compete with the other three: `CLAUDE.md`
holds durable rules, `STATUS.md` volatile dated state, `DECISIONS.md` the
numbers behind a parameter choice, and `changelog/` the app releases. This file
holds **irreversible operations on the archive** — dated, with their evidence.

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
sampling interval, a noon-centred light phase, and the strongest one: **only
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

## Still open on the data

| what | files | why it is not automatic |
|---|---|---|
| light channel anomalous, clock roughly right | `HOBO#02_Ref.EsquecidoSul_RRDM_04022020_240221.csv` | light peaks 4.4 h but TEMPERATURE peaks 12.0 h (corpus median 13.7 h); also fails the sampling-regularity gate (67% of steps on the interval) |
| light and temperature disagree by ~8 h | `HOBO1_ESQRODO_B1_050424_160325.xlsx` | dates are correct; no single rotation fixes both channels |
| sensor dark from the start | `PAB3_30062016_PAREDE.csv` | nothing decides morning from afternoon; 8,833 duplicated timestamps remain |
| several sites stacked in one hand-made sheet | `HOBO-incubacao_rodolito.csv` | the product structure would have to be invented |

The inference-free route for all four is a **HOBOware re-export from the
`.hobo` binary** with a 24-hour clock.

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
   qualification, which is the intended behaviour;
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

### Verification

45/45 self-tests, ruff clean — the app was not modified. Every count above was
read from the rebuilt index and the products themselves, not from the run log.

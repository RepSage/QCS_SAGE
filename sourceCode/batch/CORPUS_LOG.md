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

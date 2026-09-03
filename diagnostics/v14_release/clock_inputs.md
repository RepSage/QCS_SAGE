# Retained 2024S2 HOBO products: clock evidence (2026-09-03)

Read-only inspection; no qualification driver, binary reader, GUI or timestamp repair was run.

## Exact archived inputs

Root: `\\Abrolhos\Projetos\Seaguard & HOBO\DATABASE\HOBO\raw\2024S2`.

- ESQNORTE: `ESQNORTE\planilha\HOBO1_ESQNORTE_B2_040424_290824.xlsx` and `ESQNORTE\planilha\HOBO2_ESQNORTE_B2_04042024-290824.xlsx`.
- ESQSUL: `ESQSUL\planilha\HOBO1_ESQSUL_B4_070424_300824.xlsx` and `ESQSUL\planilha\HOBO2_ESQSUL_B4_070424_300824.xlsx`.
- Primary provenance: `DATABASE\HOBO\qualified\2024S2\{ESQNORTE,ESQSUL}\provenance.txt`; each names its two inputs and labels both `COLLAPSED 12-h EXPORT (no AM/PM marker; half the rows share a timestamp)`.
- Matching original `.hobo` files exist, with the same stems, under each site's `bruto` folder. Their decoding and validity were **not tested**.
- Recursive filename enumeration of DATABASE found no additional XLSX/CSV with those site/date stems. No existing valid 24-hour export was verified; differently named alternatives cannot be excluded by this search.

## Source distinction and missing evidence

- `sourceCode/QCS_DataHandler.py:1234` (`_hobo_datetimes`) normalizes Portuguese clock strings to `HH:MM:SS` and infers date order; it does not restore missing AM/PM. `read_hobo` calls it at line 1748. HOBO timestamps remain local; no GMT-3 subtraction belongs here.
- `sourceCode/QCS_Tests.py:327` (`light_clock_phase`) labels a clock collapsed when at least 50 valid timestamps have maximum hour <=12 and duplicate fraction >0.10. It returns a diagnosis and warning, not a rejection.
- `sourceCode/QCS_Main.py:3292` forwards that warning through `ui_warn`; `ui_warn` calls `messagebox.showwarning` at line 847.
- `sourceCode/QCS_Replicates.py:185` (`align_replicates`) **does reject** repeated timestamps whose temperature, light or per-variable flags conflict (ValueError at lines 206-211). `sourceCode/QCS_DataHandler.py:3129` calls this alignment; line 3176 also aligns diagnostic replicas.
- `sourceCode/batch/qualify_site.py:230-237` rejects a run with any captured error or missing completed combined CSV. However, `_dialog_reason` at lines 269-285 reports **the first captured dialog**, which may be an earlier warning.
- Saved failures: `diagnostics/v14_corpus_rollout/site_runs/ESQNORTE/run_results.json:51-54`, ESQSUL equivalent `:45-48`; logs `diagnostics/v14_corpus_rollout/ESQNORTE.log:173-179` and `ESQSUL.log:106-112`. All retain only the collapsed-clock warning text, not the later error or full dialog list.
- Therefore the exported clocks are documented as collapsed and the combination gate is a plausible cause, but the **actual later exception from these runs is not established by the saved artifacts**. A bounded replay with full `DIALOGS` capture is needed to establish it. The inspection did not perform that replay.

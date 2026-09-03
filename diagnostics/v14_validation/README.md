# v14.0 qualification validation - 2026-09-03

The active archive was read-only. Candidate products are local and are not a
replacement corpus: two active products could not pass the existing clock gate.
Scientific/data disposition is recorded in `sourceCode/batch/CORPUS_LOG.md`.

## Executed evidence

- `verified_selftest.log`, `verified_ruff.log`: the final complete suite and lint.
- `corpus_confirmed/validation_summary.json`: all 115 active HOBO products
  inventoried; 113 generated, 344,765 rows. Four failed raw attempts are explicit;
  two correspond to active products and two are extra unindexed inputs.
- `corpus_confirmed/product_diff.csv`: before/after comparison for every generated
  product, with 113 unchanged time grids. `changed_temperature_products.csv`
  contains the 17 changed products; 16 contain unresolved means withheld for review.
- `corpus_confirmed/episode_review_queue.csv`: 932 diagnostic episodes, 85
  sustained. The provisional threshold is a review screen, not fault attribution.
- `corpus_confirmed/audit_summary.json`: 55 combined summaries match their CSVs,
  no single-contributor spread, no individual CSV disguised as combined.
- `corpus_confirmed/source_hashes.json`: exact source snapshot of the full replay.
  The qualification/combination code was stable during that run. Afterwards the
  review's matplotlib Button import/text/overlap guard and batch error-return
  handling were corrected. These do not change a successful unattended
  combination; `sgom_final` replays the final driver, and the specific error and
  GUI paths below exercise the final changes.
- `qt_review_result.json`, `replicate_review.png`: actual offscreen Qt PlotWindow
  review invoked from a worker. Window closing yields no exclusion; pressing
  Accept yields the recommended temperature. Both windows ran on the GUI thread.
- `batch_failure_result.json`: an incomplete second export after a valid first
  replica returns an error and no candidate file.
- Local `single_sgom_verified/result.json`: the ledger also excludes HOBO1
  temperature when opened alone (2,247 rows after the reader's 6+3 edge trims).
- Local `sgom_final/`: final full-pipeline SGOM pilot; 2,254 rows, 481 temperature
  replacements, 463 flag changes, no light changes, all spread cells empty.

Generated data trees, intermediate runs and backup copies are gitignored. They
remain on disk. `candidate`, `corpus_final` and `corpus_verified` are incomplete
development runs, superseded by `corpus_confirmed`; do not promote them. Early
long-path and test-harness failures are preserved in their logs. `implement.py`
is the one-time source migration record, not a recurring driver.

## Reproduce

Use the absolute Anaconda base interpreter required by `CLAUDE.md`. From the repo
root, execute `sourceCode/batch/validate_hobo_corpus.py --archive <DATABASE>
--output <fresh-directory>`. It runs four isolated workers and exits nonzero on
failed inputs. The result must be read with its missing-products list; a nonzero
exit is not waived just because 113 products completed.

`sourceCode/batch/validate_hobo_candidate.py --archive <DATABASE> --output
<directory> --site SGOM --semester 2026S1` runs the final pilot. Run
`audit_candidate.py` here to recheck the saved `corpus_confirmed` comparison and
the canonical baseline unification. `single_sgom_probe.py` and
`batch_failure_probe.py` take `--archive <DATABASE>`; the former requires its
local output folder to be absent on a new run.

`qt_review_smoke.py` requires `packaging/v12_env/Scripts/python.exe` (PySide6
6.8.3); it uses the offscreen platform and disables both preference writers
before building the hidden shell. All other scripts use the QCS Anaconda base
runtime (Python 3.13.5, pandas 2.2.3, numpy 2.1.3, openpyxl 3.1.5).

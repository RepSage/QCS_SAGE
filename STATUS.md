# STATUS — QCS (Quality Control System — SAGE)

Volatile state. Every entry dated. Durable rules live in `CLAUDE.md`.

## 2026-08-17 (v12.0 field test, round 6) — summary persists; plain scale numbers

`1c3f4cd`: Selection summary refills on prefs restore; Recent gets
placeholder+tooltip; Next bold; HOBO panel tooltips drop the 'HOBO only:'
prefix (context makes it noise); **shared-toggle bug fixed** — unchecking
Tendency lines never re-greyed the degree entry (latent in tk too);
scale defaults are plain numbers (>=100 rounds to integers — '51254',
not '5.125e+04'; the light plot itself is linear, only the text was
scientific). E2E-proven; suite 52/52; ruff clean.

## 2026-08-17 (v12.0 field test, round 5) — plots carry the year; step 2 polish

`7d328ee`: panel X axes carry the year (mooring panel1 `%d/%m/%y %H:%M`,
HOBO at-site `%d/%m/%y`) and titles drop the redundant year; years moved
into Filter settings under Sites (2 columns); scale parameter names bold;
**T-S rows only exist for TSCP Profile** (hidden + auto-unchecked
otherwise); panel checkboxes + Generate got their missing tooltips;
Generate panels centered and styled like Run qualification. E2E-proven
on the PLES pair; suite 52/52; ruff clean.

## 2026-08-17 (v12.0 field test, round 4) — 7 findings applied; viz Step 1 redesigned

`521ddf1` (+ styling rounds `4fd3880`/`8ba79c1`: bold field labels,
two-column viz Step 1, tabs bold with greyscale active/inactive — pastel
tried and dropped). Round 4: continuous progress ((k-1)*5+s of n*5),
busy cursor on the main window only (the app-wide override span over the
review windows read as a hang), Recent combo restored, Output folder
above name, **'Build database from a folder' removed from the Qt shell**
(several dropped files build the database; tk folder-scan logic kept for
batch), single file auto-fills its _QLF root (DataView lands beside the
qualification plots), and — behavior change — **a multi-file build now
WRITES the unified database** (before, only folder mode saved it): empty
output fields with instructive placeholders + name required. All proven
E2E on the PLES pair (progress 10/10; database written; panel made).

## 2026-08-17 (v12.0 PORT COMPLETE — phases 3+4) — awaiting owner field test + merge

Phase 3 (`4b2df34`): `QCS_QtViz.py` — the Data visualization tab as a
remote control over the real DatabaseView wizard (hidden tk = authoritative
state, zero duplicated logic); DatabaseView gained the ui facade and
`_go_step2` returns success; DnD routes to the active tab; the
qualification→visualization prefill handoff works. E2E-proven: database
built from a folder join through the Qt tab, panels generated.

Phase 4: entry point swapped to `QCS_QtApp` (spec + `QCS.bat` →
`packaging/v12_env`), `requirements.txt` gains `PySide6==6.8.3` and
`pandas<3`, build venv recipe updated (SHORT PATH — PySide6 qml assets
overflow MAX_PATH in deep folders; that killed the first install).
`QCS_VERSION = 'v12.0'`, `.iss` 12.0, `changelog/v12.0.md`, manual
updated (Qt interface, Instrument, corrected Remove bad/suspect wording,
Remove dismissed row, spread bars). Test build: bundle verified (PySide6,
backend_qtagg, backend_svg, QCS_QtViz/QtSettings, HoboCal, tkinter+tcl),
frozen app alive 15 s, no crash log. Suite 52/52; ruff clean.

**NOT yet done:** owner field test of the full Qt app (esp. Depth review,
adaptive light review, replicate review, the viz tab and the frozen exe
running a REAL qualification — the launch smoke can't prove lazy imports;
the release ritual after merge rebuilds and re-verifies). PR link handed
to the owner. After merge: v12.0 ritual (tag on merge commit, rebuild,
ISCC, Desktop copy, release text). Post-release cleanup candidates: strip
the hidden-tk bootstrap (extract run_full_qualification to module level),
retire the tk shells, pandas-3 migration.

## 2026-08-17 (v12.0 phase 2 COMPLETE) — every interactive review runs under Qt

`fdd9b08`: replicate review (pure mpl + facade wait/help, keep-all stub
removed), profile phase picking (tk Peak Toplevel → `ui_ask_yes_no`;
curve pick closes-on-pick + `wait_figure_close`), Check variables
(`ChooseVariablesDialog` in Qt via facade; same None/[]/list contract).
Both checkboxes enabled in the Qt shell, profile gated to TSCP Profile.
Proven headless on the BURACAS cast through both refactored paths; suite
52/52, ruff clean. The Desktop shortcut was recreated (owner deleted it).
**The Qt shell now covers the whole qualification workflow.** Remaining:
phase 3 = Data visualization tab (`QCS_DatabaseView` port — the big one),
phase 4 = packaging swap. Interactive owner pass still pending for:
replicate review window (needs a reference series), Depth review,
adaptive light review under Qt.

## 2026-08-17 (v12.0 round 3 + Settings window) — phase 2 opened

Round 3 applied (`6613d1c`): 'Remove dismissed data' unchecked+greyed for
HOBO in both shells (no Depth column → no whole-row dismissals; re-enables
for Seaguard), and the Qt progress bar now follows the pipeline's own
'Stage k/5' lines, prefixed with the batch/replicate scope ('Replicate
2/2 - Stage 3/5'); a single Seaguard run shows plain stages.

**Phase 2 opened with the Settings window** (`6ab675d`):
`QCS_QtSettings.py`, three tabs mirroring tk, same CONFIG. Validation and
persistence extracted to toolkit-free cores in `QCS_Main`
(`apply_settings_values` / `persist_quality_criteria`; `TEST_CATEGORIES`
now module-level) — the tk window goes through them too. E2E-proven:
sensor_max_temp=10 typed in the dialog flags 397/625 rows of the BURACAS
cast BAD in a real run; invalid entries rejected; Reset restores
defaults. The first driver run HUNG at the Depth review — the real Qt
figure wait engaging, which is the desired interactive behavior.

Phase 2 remaining: profile phase picking + Check variables (tk Toplevels),
replicate-review window. Then phase 3 (Visualization tab), phase 4
(packaging swap: PySide6 6.8.3 pinned).

## 2026-08-17 (v12.0 field test, round 2) — Instrument empty state; Remove dismissed

Round 2 applied (`35f62d7` + `591b2b3`): the combo is now **Instrument**
with a 'Select instrument' placeholder — clearing Data file(s) resets it,
hides the Replicates row and clears the summary. New **Remove dismissed
data** in Data filtering (both shells, persisted): dismissed VALUES were
already blanked at the manual cut, so the option (semantics decided with
the owner) drops the rows where EVERY variable was dismissed — the Depth
review's whole-row cuts — leaving a gap in the original Sample numbers;
always selectable, like the other two filters. Proven on a real BURACAS
cast: 625 → 622 rows, sheet starts at Sample number 4. Also fixed a
v11.6.1 tooltip erratum found on the way: remove_bad/suspect said "Drops
rows" but the implementation BLANKS values and keeps every row (both
tooltip copies corrected). **The tk shell on master still says "Drops
rows" in its shipped v11.6.1 build** — carried by the next release.

## 2026-08-17 (v12.0 field test, round 1) — owner tested; 4 findings applied

Owner field-tested the phase-1 shell: the adaptive light review works under
Qt. Findings, all applied (`acb8b2c`): Input type locks on auto-detect
(unlocks when the selection is cleared), app icon on the matplotlib windows
(Qt `style_plot_window` in the facade) and on the new Desktop shortcut
("QCS v12 dev" .lnk, replacing the .bat), status-bar progress bar
(indeterminate + File/Replicate k/n fractions from the pipeline markers),
and `plot_variable` now draws the replicate-disagreement bars on the
combined `Temperature series.svg` (same visual as the DataView HOBO panel;
this one also improves the tk app). Suite 52/52, ruff clean, SVG verified
with bars + legend. Note: on the PLES test pair the bars are LARGE — the
replicates run at different intervals (1 h vs 2 h), so nearest-match
pairing shows the diurnal swing as disagreement; expected, not a bug.

## 2026-08-17 (v12.0 port, phase 1 done) — the Qt shell runs the real pipeline

`sourceCode/QCS_QtApp.py` + `QCS_QtTheme.py` on `port-v12.0` (`c549778`):
the approved design wired to the real pipeline via the phase-0 facade, tk
closures materialized on a hidden root (batch-driver pattern), matplotlib
on QtAgg, figure waits via `canvas.start_event_loop`. Launcher:
`QCS_v12_dev.bat` on the Desktop (`packaging/v12_env`).

- **Proof:** PLES 2-replicate `.hobo`, fixed mode, driven through the Qt
  widgets vs the tk widgets — combined sheets identical cell by cell
  (1902×11). Suite 52/52; ruff clean.
- **Gotcha (cost a debug round):** pip-latest pandas 3.0.5 breaks
  `save_excel_autofit` (`astype(str)` keeps NaN as float → `len()` dies).
  `v12_env` is now PINNED to the shipping stack (pandas 2.2.3, numpy
  2.1.3, matplotlib 3.10.0, scipy 1.15.3, gsw 3.6.21). The pandas-3
  migration is a separate future task, not part of the port.
- **Owner has NOT field-tested this build yet.** The interactive pieces
  (adaptive light review window, Depth review, dialogs) run under Qt by
  design but were not exercised interactively — automated proof covers
  the fixed-mode path only.
- Phase 2 next: Settings window (QDialog, 3 tabs), profile phase picking
  and Check variables (tk Toplevels at ~2470/2530 in `QCS_Main.py`),
  replicate-review window (the Qt stub keeps all replicates, logged),
  then phase 3 = Visualization tab, phase 4 = packaging swap.

## 2026-08-14 (v12.0 port, phase 0 done) — pipeline is toolkit-neutral

Branch **`port-v12.0`** (long-lived; master stays the working tk app until
the port completes). Phase 0 landed (`0bb8d91`): the qualification pipeline
no longer touches tk directly.

- `collect_input_settings` = `read_input_widgets()` (tk) +
  `apply_input_settings(vals)` (toolkit-free). The Qt shell fills the same
  `vals` dict from its own widgets.
- Facade: `ui_info/ui_warn/ui_error` (defaults call `messagebox.*` so the
  batch drivers' monkeypatches still intercept), `ui_busy`, `ui_pump`.
  Already-replaceable hooks stay: `log_line`, `review_light_window`,
  `review_replicates`, `data._show_and_wait`.
- `light_cutoff_mode` now travels in `INPUT` (was read from a widget
  mid-run at the fixed-window branch).
- Proof: suite 52/52, ruff clean, and a real 2-replicate `.hobo`
  qualification (the Desktop PLES pair) driven batch-style on this branch
  vs. master — combined sheets **identical cell by cell** (1902 rows;
  fixed cutoff exactly 60 days after start). Driver script pattern:
  scratchpad `drive_real_run.py` (mimics `qualify_site.py`).

**Phase plan** (each phase = working increment, committed on the branch):
1. `QCS_QtTheme.py` (Fusion light/dark from `packaging/v12_preview.py`,
   log dock, Qt crash dialog) + `QCS_QtApp.py` shell with the qualification
   tab wired: prefs, browse/sniff, DnD (Qt native), regions, RUN →
   `apply_input_settings` + `start_qualification` with a Qt facade;
   matplotlib backend QtAgg (the `plt.show()` review windows work as-is —
   there is NO FigureCanvasTkAgg anywhere).
2. Settings dialog + the tk-Toplevel review windows (variable check,
   peak review ~line 2400, replicate review, `QCS_Update` dialog).
3. Data Visualization tab (`QCS_DatabaseView`).
4. Packaging swap: spec/bat/requirements gain PySide6 **6.8.3 pinned**
   (6.11 does not load on this machine's MSVC runtime), retire sv-ttk.

Known non-issue found while proving: in the combine branch,
`OUTPUT['last_qualified_df']` keeps the LAST replicate's df (the combined
sheet on disk is the truth; `last_qualified_file` points at it correctly).
Pre-existing, only worth fixing if something starts consuming it.

## 2026-08-14 (v11.6.1 released) — ritual done; NEXT: the real v12.0 port

PR #29 merged, tagged `v11.6.1` on `106632c`, branch deleted, `.iss` bumped
(`7b9a40c`). Installer rebuilt `--clean` and verified: backend_svg /
QCS_HoboCal / tkinterdnd2+tcl in the bundle, 12 s smoke run alive with no
crash log. `QCS_Setup_v11.6.1.exe` (54.6 MB) + `RELEASE_v11.6.1_para_colar.md`
on the Desktop; publication pending (owner pastes the release).

**Next: the real v12.0 Qt port** — design approved through preview rev6
(`packaging/v12_preview.py`), tooltips now standardized and worth porting.
Start from the preview's structure; same QC pipeline, matplotlib embeds via
FigureCanvasQTAgg; PySide6 pinned at 6.8.3 (see the v12.0 entry below).

## 2026-08-14 (v11.6.1 on PR) — all tooltips standardized; awaiting merge

Branch `fix-v11.6.1` pushed (commit `05ebbfa`), prefilled PR link handed to
the owner. All ~150 tooltips rewritten to the documented editorial standard
(comment above `TOOLTIPS` in `QCS_Main.py`); per-variable entries now
loop-built from the variable tables; key-coverage check proved identical
key sets (22+54+3+42). Execution log buttons got tooltips (tk app +
preview dock); `SeaGuard` spellings normalized to `Seaguard` everywhere
except the self-test XML fixtures (`ProdName="SeaGuard II"` is device
data). The user manual — found stuck at v11.4.2, the v11.5/v11.6 rituals
skipped it — was caught up to v11.6.1. Suite 52/52, ruff clean, preview
renders.

**Next after merge: the v11.6.1 ritual** (tag, branch cleanup, .iss bump
to 11.6.1, PyInstaller build, bundle verify, smoke, ISCC, Desktop copy,
release text). Then the real v12.0 Qt port begins — the design is
approved through preview rev6 and the tooltips are now worth porting.

## 2026-08-14 (v12.0 opened) — Qt preview delivered; owner choosing the style

The v12.0 (Qt/PySide6 interface port) round is open. Delivered today:

- **`packaging/v12_preview.py`** — a PySide6 mock of the Data Qualification
  tab with live style switching (View > Interface style): Windows 11
  native / Fusion light / Fusion dark; Execution log as a dockable panel.
  `QCS_v12_preview.bat` on the Desktop launches it
  (`packaging/v12_env` venv, gitignored).
- Screenshots of the three variants rendered WITHOUT showing a window
  (QWidget.grab() on an unshown window; the offscreen platform renders
  tofu - no fonts) and sent to the owner in chat.
- **Environment gotchas, hard-won:** PySide6 does NOT import in the
  Anaconda base (Qt5 DLL conflict) NOR at 6.11.x even in a clean venv on
  this machine ("specified procedure not found" - needs a newer MSVC
  runtime than the installed 14.44). **PySide6 6.8.3 works** in the venv;
  pin it. Qt 6.8 follows the Windows dark mode via styleHints
  colorScheme - pin the scheme per variant, and v12 gets automatic
  dark/light for free.

Awaiting the owner's style choice; then the real port begins (same QC
pipeline, new shell; matplotlib embeds via FigureCanvasQTAgg).

## 2026-08-14 (v11.6 released) — ritual done; NEXT: v12.0 Qt interface

PR #28 merged, tagged `v11.6` on `b80fe72`, branch deleted, installer
rebuilt and verified (backend_svg / HoboCal / tkinterdnd2+tcl in the
bundle; smoke clean); `QCS_Setup_v11.6.exe` + release text on the Desktop,
publication pending. The v11.6 round fixed: drag-and-drop registered on
EVERY widget (tkdnd does not propagate to children - the v11.5 gotcha),
light-cutoff persistence, combined-folder temperature plot, combine-note
explanation of the empty Flag column; working DnD logs nothing (owner:
the Execution log is for pipeline messages).

**Next agreed with the owner: v12.0 — the Qt (PySide6) interface port.**
Start by building 2-3 working visual variants for the owner to choose from
(measured basis: the ~300 ms tab switch is sv-ttk's rendering; clam does
60 ms; Qt renders natively). The QC pipeline does not change.

## 2026-08-14 (v11.5 released) — ritual done; publication pending

PR #27 merged, tagged `v11.5` on `cc25365`, branch deleted, installer
rebuilt and verified (bundle carries backend_svg, QCS_HoboCal, tkinterdnd2
incl. the tkdnd Tcl files; smoke test clean); `QCS_Setup_v11.5.exe` +
release text on the Desktop, publication pending. Next planned release:
**v12.0, the Qt interface port** (owner decision; measured basis: the
~300 ms tab switch is the sv-ttk theme - clam does it in 60 ms).

## 2026-08-14 (v11.5, session 3) — anchor SHIPPED; round complete, PR pending

The delimiter anchor is in the reader (primary path; content scan is the
fallback), the walk skips event markers, and the calibration tables were
rebuilt from the 185 proven alignments (pooled modal, 462k light readings,
temp 177 codes / zero conflicts / monotone; light 227 observed + 28 law).

**Definitive blind validation: 124 files at exactly 100.0% temperature and
120 at ≥ 99.9% light** (v11.4.2: 46). The owner's PLES pair: both decode
blind - HOBO1 1.0000/0.9989, HOBO2 1.0000/0.9962 WITH the clock warning
(its clock is genuinely wrong). Sub-0.1% light residuals are HOBOware's own
±0.1 rounding wobble, visible between rows of its own exports.

Also done this session: drag-and-drop shipped (tkinterdnd2 required into
the app shell; drops land in the active tab's field; 4/4 GUI checks; dep in
requirements + spec + build venv), 'Data file(s):' label, suite 52/52 with
the delimiter in the synthetic fixture. Remaining before the PR: nothing -
open it.

## 2026-08-14 (v11.5, session 2) — 185/200 proven; the preamble DELIMITER found

Owner approved the mixed-interval spread solution. Session results, all on
branch `improvements-v11.5` (still NOT shippable until the anchor lands):

- **With the event-skipping walk, 185 of ~200 paired files align at
  exact_T ≥ 99.9%** (export-guided; was 97). The walk is the format's
  missing piece confirmed at scale (`pointer_test.csv` in this session's
  scratchpad has每 file's proven `s0_bit`).
- **Tag 0x0D is only an approximate pointer** (predicted-vs-true diff
  clusters: −24×102, −42×47, −46×16, −38×10, −20×6 — i.e. 1-2 metadata
  tokens after the pointed spot, in two bit-jitter families). Use it as a
  narrow search WINDOW, not an address.
- **The real anchor: the LAST preamble token has a signature** — census over
  the 185 proven files: values `03FF0/0FFF0/13FF0/07FF0/0BFF0/17FF0/...`,
  i.e. `(token & 0x03FF0) == 0x03FF0 and (token & 0xF) == 0` (bits 4-13
  set, low nibble clear, high bits vary — likely the launch-reading light
  code). Minority family `3FF02/3FE00/...` = the −46/−38/−20 jitter files,
  delimiter shifted by 2-4 bits. **Next action: sample0 = first token after
  the LAST delimiter-signature match inside the pointer window (8·tag0x0D +
  {10..56} bits); fall back to the count+darkness scan when no signature
  matches; then re-run the blind validation** (expect ~185 exact) and only
  then ship.
- Drag-and-drop state: `apply_selected_files()` extracted in BOTH modules
  (QCS_Main + QCS_DatabaseView, done, committed); STILL PENDING: the drop
  wiring in QCS_App (tkinterdnd2._require(root) + drop_target_register on
  notebook/content/log frames, active-tab dispatch), the 'Data file(s):'
  label, tkinterdnd2 in requirements.txt + collect_all in QCS.spec.
- Also pending: light-table refinement for high companded codes (law-filled
  codes ≥ ~200 carry law rounding, not HOBOware's - collect from the newly
  aligned 185), changelog v11.5, manual, PR.

## 2026-08-14 (v11.5 round OPEN — branch `improvements-v11.5`, NOT shippable yet)

Owner's five requests after testing v11.4.2 with the PLES pair (the pair sits
on the Desktop: `HOBO[12]_PLES_A1_200925_160326.hobo` + `.xlsx`).

**BREAKTHROUGH — mid-stream event markers were the ~50-75% families.** An
isolated temp==0x3FF token inside the stream is a logger EVENT (does not
consume a time slot); un-skipped, each one slid the alignment by one from
there on. With the greedy event-skipping walk (now in `_read_hobo_binary`),
HOBO2_PLES goes 0.74 → **1.0000 exact** (guided; 1 event + old tail) and
HOBO1_PLES stays 1.0000. The night-light hard gate is now: darkness ranks
candidate SELECTION; bright-but-coherent daily peak (≤14 lit hours) decodes
WITH a clock warning (HOBO2's clock is genuinely wrong - its EXPORT shows
99,200 lux at "23:41", noon sun; replicates even configured at different
intervals, 1 h vs 2 h); bright-and-incoherent refuses.

**REMAINING BLOCKER (why the branch must not ship):** the blind reader still
drops/adds the FIRST sample on some files (PLES1 blind = 0.36 exact by a
1-slot shift, a silent regression vs refusal). Cause: the head guard kills
real hot-deck first readings; without it, phantom preamble tokens win by
count. **The clean fix is probably the header pointer: tags 0x0D/0x1D look
like the first-sample address — for ESQRODO and SGOM2 (proven alignments),
`sample0_bit = 8*(tag0x0D + 4) + 6` holds EXACTLY** (derive against more
proven files; PNOR gave the slot one BEFORE sample0 — the formula may point
at the last preamble token, i.e. sample0 = pointer + 18 bits). If it holds,
every alignment heuristic collapses into reading the pointer.

Done in the branch, tested: event-skip walk + gate redesign (suite 52/52);
**spread fix** — single-replicate rows now carry EMPTY spread, not 0 (the
owner's alternating zeros were replicates configured at DIFFERENT intervals;
warning added + self-test); **conclusion dialogs trimmed** (no more "you can
qualify another file..."). Pending: drag-and-drop of files onto the window
(tkinterdnd2 installed in base for dev; needs GUI wiring + spec/requirements
+ 'Data file(s)' label), light-table refinement for high companded codes
(PLES2 residual 2.3% light mismatches = law-filled codes above ~200).

Owner's question 5 (which replicate anchors the fixed 60-day light cut):
each replicate is qualified INDEPENDENTLY - the fixed window cuts each one
60 days after ITS OWN first sample; the combined series then keeps light
while at least one replicate is uncut (max of non-fouled). With replicates
launched minutes apart the two cutoffs fall on the same day, so in practice
the combined light window ends 60 days after deployment - no single logger
is "chosen".

## 2026-08-14 (v11.4.2 released) — ritual done; replicate outputs proven

PR #26 merged, tagged on `077fc49`, branch deleted, installer rebuilt with
the NEW check (bundle verified against the 1,266-module set of a real
qualification - all present, backend_svg included), smoke-tested;
`QCS_Setup_v11.4.2.exe` + release text on the Desktop, publication pending.

**Replicates question (owner): already the behavior, now PROVEN by running
two real `.hobo` replicates through the pipeline** - the output carries one
full `<replicate>_QLF` product per file (sheet, reports, DataView plots,
light window) PLUS the combined product (sheet, method note, per-replicate
light plots). Nothing to change.

## 2026-08-14 (v11.4.2 pending) — the owner's test round caught three more

The installed-copy path had never been walked end to end; the owner's test
kept finding what the layered validations could not (each documented in
`changelog/v11.4.2.md`): the frozen bundle lacked matplotlib's lazily-
imported SVG renderer (every plot is .svg → first real qualification died);
the Output format box had no factory default (now `.xlsx`, owner's choice);
the `.hobo` alignment guard refused POOL loggers (step limit now scales
with the sampling interval). New method in the packaging README: dump
`sys.modules` from a REAL qualification and check the bundle's PYZ toc
against it — the launch smoke test cannot see lazy imports. Blind corpus
validation after the guard fix: 101 decoded, 46 at 100.0% exact (pools in).
Branch `fix-v11.4.2` pushed; PR pending; owner still testing.

## 2026-08-14 (v11.4.1) — GUI gate fixed; release ready to publish

The owner's first real `.hobo` attempt hit "Unsupported file format": the
extension gate in `collect_input_settings` predates the feature and was never
wired (the corpus validation runs at the data layer, below it — gotcha now in
`CLAUDE.md`, "four wiring points"). Fixed in v11.4.1 (PR #25, merged, tagged
on `dd26ae5`), installer rebuilt and smoke-tested. **Correction (owner,
2026-08-14): v11.4 HAD been published as a Release** — that is how the bug
was found on a real install — and **v11.4.1 is now published too** and is
`latest`, so the in-app updater offers it over v11.4. Owner's real-file
`.hobo` test on the fixed build in progress.

## 2026-08-14 (v11.4 closing) — .hobo reader SHIPPED (experimental); units auto-detected

Owner decisions this round: close v11.4 so they can test raw-`.hobo` reading;
v12.0 will be the professional-interface (Qt) release; units auto-detection
confirmed for v11.4.

**Shipped in v11.4** (branch pushed, PR pending; suite 52/52, ruff clean):
- `read_hobo` accepts `.hobo` directly (`_read_hobo_binary` +
  `QCS_HoboCal.py` tables). Blind corpus validation: **42 files reproduce
  their export 100.0% exactly in both channels** (all current-generation
  families); older-generation files are REFUSED (layout mismatch, or the
  night-light gate: decoded light glowing in the dark = wrong decode).
  Timebase settled: export row0 = a launch-time in-air reading that is NOT
  in the memory; stored sample i = launch + 1 s + (i+1)·interval.
- Units read from the source (`read_ctd` detects `Descr[Unit]`, converts,
  refuses unit-less text exports); the GUI Units section removed.
- Window state persistence; Site code above Data filtering.

**Known imperfect tail, documented not hidden:** ~30 pre-2023 pairs decode
with partial mismatch or one-row offset (some older HOBOware generations DO
store the launch reading, shifting the series by one slot) — most are
refused by the gates; a few silent one-row-offset families remain in the
2021-2022 range (exact_T ~0.5 in blind CSV). The corpus itself is
unaffected (qualified from exports). Deciphering the old variant remains
open work (blind CSV: scratchpad `blind_reader_validation.csv`).

**v12.0 (next): Qt port of the GUI** — owner asked for examples; measured
basis in the previous entry (sv-ttk theme is the 300 ms tab-switch cost).

## 2026-08-14 (v11.4 round open) — light law SOLVED; GUI perf measured; window state persists

Branch `improvements-v11.4` open. Owner confirmed: automatic unit detection
ships in v11.4.

**The light law is fully deciphered** (owner commissioned "decifre o problema
da luz"). From 230,007 readings across 89 verified clean-export files, the
code→lux map is single-valued at 99.96% and closes exactly:

- code ≤ 128: `raw = code`
- code > 128: `e = (code−129)//16`, `m = (code−129)%16`,
  `raw = (136 + 8·m) · 2^e`  (verified exactly through every observed
  segment, steps 8/16/32/64/128/256/512/1024, up to 198,401 lux)
- `lux = raw × 10.7639`, rounded to 1 decimal (lumen/ft² → lux).
- Reminder: the light byte of record *i* belongs to row *i−1*.
- Code 255 looks like a saturation/invalid marker (7 junk rows); treat like
  temp's 0x3FF.

**GUI responsiveness, MEASURED (perf scripts in session scratchpad):**
imports 2.6 s; first paint 1.1 s; **tab switch ≈ 300 ms — and the cause is
the sv-ttk theme itself**: an identical synthetic ttk tree raises in ~330 ms
under sv-ttk and **~60 ms under clam** (5.5×). The v11.3 scroll canvas adds
only ~20 ms; a place()-offscreen swap does NOT help (Tk repaints on expose
regardless). Options for the owner: a "fast theme" toggle (clam,styled), or
accept, or a Qt port as a future MAJOR (full GUI rewrite, weeks). Startup
could be cut by lazy-importing matplotlib. Resize costs ~1.5 s (sv-ttk).

**Done on the branch (tested, 5/5 UI checks + suite 51/51 + ruff):**
- Window remembers maximized/normal state and geometry across sessions
  (`win_state`/`win_geometry` prefs; restore applied twice — the first pass
  races the WM and lands ~20 px short; close goes through on_app_close).
- Site code moved ABOVE Data filtering in Output settings (owner request).

**Next in v11.4:** light-law validation sweep (corpus exactness with the
−1 shift), the older-variant .hobo layout (105 files), automatic unit
detection (drop the Units section; refuse unit-less text exports), then
`read_hobo_bin` + GUI wiring + docs.

## 2026-08-14 (later) — .hobo: 97 files decode EXACTLY; light law found; 105 older files pending

v11.3 published by the owner. The reverse-engineering round continued and the
prototype reader now stands at, corpus-wide (209 paired files):

- **97 files VERIFIED: temperature decodes ≥ 99.9% exactly** (most 100.0%)
  against their exports, with a poisoning-proof bootstrap (seeds = ESQRODO
  28/10/23 + PNOR_A4 19/09/25 at phase 0 / sample0 = token 3; growth only
  from already-verified alignments; contribution rejected on any conflict).
- **Temp LUT: 174 codes (367..543), ZERO monotonicity violations, ZERO
  cross-logger conflicts**, adjacent steps 0.095..0.114 °C. Universal.
- **The light byte belongs to the PREVIOUS row**: record i = [light of
  sample i−1, 8 bits][temp of sample i, 10 bits]. Proven on PNOR_A4: at row
  shift −1 the code→lux table collapses from 176 ambiguous codes to ONE
  (99.98% agreement). Low codes: lux = code × 10.7639 exactly (lumen/ft² →
  lux); higher codes compand (~×8 steps observed around code 122+); derive
  the full table from verified bright files — NOT YET DONE with the shift.
- **105 files not verified yet**, heavily skewed to 2019–2022 campaigns —
  working hypothesis: older HOBOware/firmware wrote a layout variant (header
  tag 0x34 = HOBOware version string; correlate it with verified/failed and
  hunt the variant's bit layout). Also among them: exports with pt-BR
  decimal mangling on the LUX column too (repair before validating — the
  temp-side crude repair `>1000 ⇒ /1000` is NOT enough; use read_hobo-grade
  repair), and 2 unreadable exports (TIM2_0120 7 rows; SGOM out2023 3 rows).
- **Bootstrap-poisoning lesson (cost one full sweep):** growing the LUT from
  merely "single-valued" alignments lets wrong-phase files inject shifted
  codes, which then steer later selections wrong. Only verified-exact files
  may teach the LUT, and every contribution must be conflict-checked.
- Prototype + per-file results: session scratchpad
  `hobo_reader_proto3.py` / `hobo_reader_validation3.csv` (v1/v2 kept for
  the record). Probes 19–25 document the write-pointer/phase/light-shift
  hunt: session sits at the FRONT of memory at a per-file BIT PHASE
  (preamble length varies, 2–5 tokens observed); terminator token has temp
  bits all ones (0x3FF); old sessions REMAIN in memory after the terminator.

**Units question (owner asked, 2026-08-14, answered with evidence):** all
255 Seaguard raw `.bin` sessions carry their units internally; the 134 that
measure pressure/conductivity declare **kPa and mS/cm, no exception** (the
GUI reader also standardizes .bin columns to kPa by construction). The raw
archive holds NO Seaguard text exports at all. So the Units section of the
GUI only matters for hand-loaded text exports, whose AADI headers also name
the unit (`Descr[Unit]` columns) — but today's reader DISCARDS the original
header name before converting by the combobox. Plan (next release): parse
the unit from the source itself, drop the Units section, and refuse loudly
a text export whose header names no unit. Not implemented yet.

**Next actions:** (1) rebuild the light table with the −1 row shift from
verified files with CLEAN exports; (2) split the 105 pending files by
HOBOware version (tag 0x34) and crack the older variant the same way
(seed candidates: any 2019 file whose export is clean); (3) lux-repair
mangled exports before scoring; (4) only when ~all pairs verify, implement
`read_hobo_bin` in the app (v11.4) with suite tests + manual + changelog.

## 2026-08-14 — the .hobo sample stream is CRACKED (owner commissioned direct reading)

v11.3 released (tag on `42e9c72`, installer rebuilt and smoke-tested, release
text on the Desktop). The owner then commissioned direct `.hobo` reading, and
the reverse engineering broke through. **What is proven, with the evidence:**

- **File = 64 KB logger-memory dump, 0xFF-padded.** Header is TLV
  (`88 tag len payload`): 0x04 maker, 0x05 model, 0x06 serial, **0x07 launch
  datetime** (`? yy mm dd HH MM SS ?`), **0x08 logging interval in seconds**,
  0x0A deployment name, 0x12 UTC offset in seconds (int32 BE, −10800), 0x14
  timezone name, 0x1E battery V (float32 BE), 0x34 HOBOware version, channel
  definition blocks (`0x0B` index, `0xB5` name). Tag **0x0D ≈ data-region
  file offset** (matches within a byte or two; confirm before relying).
  Data begins after the last `88 11 00`.
- **Sample record = 18 bits, MSB-first: [light 8 bits][temp 10 bits].**
  Preamble before sample 0 (ESQRODO: `3FFFF 3FFFF 3DDC0 03FF0` = 4 tokens;
  per-file delta observed 2..5 — the decoder must detect the preamble length,
  not hardcode it). ~12 stray bits at the very end.
- **Temp: universal calibration.** Two loggers (serials 20063739, 22178335),
  34 shared codes, **max disagreement 0.000 °C**. Locally ~−0.0977 °C/code
  around code 500 ≈ 26 °C (thermistor curve; build the full 1024-entry LUT
  from the 209 paired files, values are °C rounded to 3 decimals).
- **Light: lux = raw × 10.7639** (lumen/ft² → lux) where raw = code for
  code ≤ 127, and **raw = (code−128)×8 + 128 for code ≥ 128** (µ-law-style
  companding; higher segments — codes far above 137 — not yet observed, map
  them from bright-site files before trusting).
- **Validation state:** PNOR_A4 (`HOBO2_PNOR_A4_190925_150326`, 4258 rows,
  interval 3600 s) decodes with **0 temp deviations over the whole file**.
  ESQRODO's 405 deviations are EXPORT-side (pt-BR Excel ate decimals; my
  probe repair was cruder than read_hobo's). ESQNORTE_B2 14032022 misaligns
  (agreement 0.43) — likely early event tokens (launch handling); unsolved.
  Old-memory files (e.g. HOBO1_SGOM 47 B/row) retain PREVIOUS deployments —
  the write-pointer / current-session-start rule is still unknown (candidate
  fields: the 0x22 block words, tags 0x0D/0x1D).
- Probe scripts `hobo_probe1..18.py` in the 2026-08-13/14 session scratchpad.
- **Traps for the next session:** rank correlation lies in flat/night
  stretches (use value-exact matching against a learned LUT); read_hobo's
  dedup shifts alignment (align against the RAW export, repair the decimal
  scale first); light code 0 dominates fouled deployments.

**Next actions:** (1) resolve preamble/event tokens and the multi-deployment
write pointer; (2) build the corpus-wide temp LUT + light companding table
and validate DECODE-EXACT against all 209 paired exports; (3) only then
implement `read_hobo_bin` in `QCS_DataHandler.py` (mirror `read_hobo`'s
output frame; timestamps = launch + i·interval, local time, never
GMT-corrected), wire `.hobo` into the HOBO input path, suite tests, docs —
that release is the next MINOR (v11.4 — QC rules unchanged).

## 2026-08-13 — Owner DELETED the archive tables; v11.3 in progress; .hobo verdict

**The owner deleted `_registros\`, `qualified_index.csv` and both raw
`manifest.csv` from the CLAUDE share and wants none of them back** ("Não quero
nada daquilo"); the folder structure itself is still under the owner's review,
so nothing should be built that depends on the current layout. Verified after
the deletion: the two trees are intact (137 + 177 = 314 qualified products,
all raw campaigns present). Consequences, stated not fixed:

- `build_index.py` can REGENERATE `qualified_index.csv` at any time — but only
  if asked; `build_data_package.py`, `drop_stale_products.py` and
  `sweep_value_integrity.py` need that regeneration first.
- The two `manifest.csv` were the only NON-regenerable record (raw provenance
  + md5 of every staged file, incl. the in-place clock repairs). Their content
  survives only as prose in `sourceCode/batch/CORPUS_LOG.md`.

**v11.3 (branch `improvements-v11.3`, in progress)** — owner request, done and
verified, PR pending: qualification tab scrolls when the window is too short
(the field-notebook fullscreen bug: Check variables / Light cutoff row was
unreachable), and a **Hide log / Show log** button left of *Clear log*
collapses the Execution log (persisted as `log_hidden`). 16 live-GUI checks +
51/51 suite + ruff clean. Gotcha for GUI tests, twice bitten today: the
version-reset dialog is scheduled INSIDE `QCS_App.main()` from the UI-restore
path, so neutralizing `SETTINGS_RESET_FROM` before `main()` is useless — set
`USER_PREFS['qcs_version'] = data.QCS_VERSION` instead, or `update()` blocks
forever on an invisible modal.

**Direct `.hobo` reading (owner asked "é possível?") — investigated, verdict:
possible in principle, not a quick win.** Evidence from real files (250
`.hobo` in the archive, every one with a paired export as ground truth):
header is a clean TLV (`88 tag len payload`) and already decoded — magic
`HOBO`, model, serial, launch datetime (tag 0x07), logging interval in
seconds (tag 0x08), timezone, battery V (tag 0x1E, float32 BE), channel defs
TEMP/LUZ; files are 64 KB memory dumps padded with 0xFF. The SAMPLE stream is
the hard part: bit-packed (16-bit windows at +2 bytes show an exact ÷4 ladder
→ 18-bit periodicity), no public documentation exists (searched), the
[2-bit tag][16-bit value] hypothesis does NOT close cleanly, and one file
shows 47 bytes/exported-row (memory likely retains PREVIOUS deployments'
data). On top of the stream grammar, HOBOware's ADC→°C and →lux calibration
curves would need to be reproduced EXACTLY to match the exports. Estimate: a
dedicated round with real risk of partial success. Probe scripts in the
2026-08-13 session scratchpad (`hobo_probe1..5.py`). Practical note: a direct
reader would mainly serve future downloads and recovery when an export is
missing — every archived `.hobo` already has its export.

## 2026-08-13 — HOBO\raw campaign-first; archive tidied; duplicate install removed

Owner requests, all done and verified (full record in
`sourceCode/batch/CORPUS_LOG.md`):

- **HOBO\raw inverted to campaign-first** (123 directories moved, RRDM names
  kept — the two campaign numberings are not convertible). Verified in layers:
  identical md5 multiset (489 files), then **407/407 manifest rows checked
  against the files at their new paths**, manifest `dest` rewritten (367 rows,
  40 `_EXPERIMENTOS` untouched by design).
- The re-check exposed a latent defect: **12 manifest rows stale since August**
  (`repair_unset_clock.py` never updated the manifest; two hand re-exports
  never re-recorded). Reconciled by the new `refresh_manifest_md5.py`; gotcha
  note added to the script.
- **Driver adapted** (`qualify_site.py`, `run_semester.py`) and proven:
  discovery parity **137/137** HOBO products; full-stack tempdir controls
  ESQSUL_2026S1 and PLES_DENTRO_2026S1 column-identical to their corpus
  products; ESQRODO 2020S1 re-file guard still plans nothing.
- **Archive root tidied** to `HOBO / SEAGUARD / _registros /
  qualified_index.csv`; historical tables filed in `_registros\` with a
  LEIA-ME; `manifest.csv.bak` deleted. The two `manifest.csv` and the index
  stay — the pipeline reads/writes them.
- **Duplicate install removed** on this machine: the per-user copy was already
  gone from disk; its orphaned HKCU uninstall entry (backed up to a .reg in the
  session scratchpad) was deleted. One QCS remains: v11.2.1 all-users in
  `Program Files (x86)` — kept there by owner decision ("(x86) mesmo").
- Pre-existing observation: 84 files under HOBO\raw (mostly newer
  `_EXPERIMENTOS` campaigns) have no manifest row; separate decision.

The corpus itself was NOT requalified — nothing about the data changed, only
where the raw files live and how the drivers find them.

## 2026-08-13 — v11.2.2 MERGED and TAGGED; installer rebuilt; two install findings

PR #22 merged (`7fcc7a6`); **tagged `v11.2.2` after re-verifying 51/51 + ruff on
the merged master; branch deleted local and remote; installer rebuilt** and on
the Desktop. Release publication pending (text on the Desktop).

**The field notebook ran the diagnostic and NOTHING appeared** — the .ps1 was
never executed: Windows opens a double-clicked `.ps1` in Notepad. Fixed by
shipping `QCS_diagnostico.bat` beside it (double-click runs it, `Unblock-File`
first for files that arrived by e-mail, output teed to
`QCS_diagnostico_resultado.txt` so the evidence survives a window that closes).
Tested end to end from a cmd double-click.

**The diagnosis is nonetheless settled, by a fact the owner supplied: that
notebook cannot install Windows updates at all** (it reports its build as
end-of-service though it is Windows 11 Pro 22H2). Root-certificate updates
arrive through Windows Update, so its root store is frozen at whenever it last
succeeded — and the root `api.github.com` chains to is recent. Browser works
(.NET fetches a missing root on demand), QCS did not (Python reads only what is
installed). The chain is complete without running the diagnostic; the files
remain on the Desktop should formal confirmation ever be wanted.

**Consequence worth keeping:** on that machine the workaround the error message
suggests — install the pending Windows updates — is a dead end, so **v11.2.2 is
not merely the fix but the only route**. Install it there BY HAND (the old
version cannot self-update; that is the defect). The owner has decided not to
pursue the machine's Windows problem, which is fine for QCS: from v11.2.2 the
app depends on that machine for nothing.

**Two findings from testing the diagnostic here, both real:**

1. **All-users installs land in `C:\Program Files (x86)\QCS`, not
   `C:\Program Files\QCS`** (registry: WOW6432Node, InstallLocation
   `...(x86)\QCS\`). Inno compiles a 32-bit installer unless told otherwise,
   and `{autopf}` then resolves to the 32-bit folder. My earlier claim that it
   goes to the 64-bit Program Files was **wrong and never verified**. It is
   also, by accident, exactly what the owner originally asked for. The one-line
   directive to change it is documented in `packaging/README.md`; awaiting the
   owner's call.
2. **This machine carries TWO installs**: v11.2.1 all-users in
   `Program Files (x86)`, and v11.2 per-user in `%LOCALAPPDATA%\Programs\QCS`.
   Inno tracks per-user and per-machine installs separately even with the same
   AppId, so they coexist, each with its own Start Menu entry and its own
   self-update. Whichever one is opened is the one that updates. Worth cleaning
   up to one.

## 2026-08-13 — v11.2.2 on branch `improvements-v11.2.2` (superseded by the entry above)

**The v11.2.1 self-update worked on this machine and FAILED on the field
notebook** ("could not be reached", with working internet). Root cause found:
`api.github.com` chains to *Sectigo Public Server Authentication Root E46*, a
recent root; Windows fetches a missing root on demand for the browser and
PowerShell, but **Python validates only against roots already installed**. A
rarely-online notebook does not have it — the exact machine class this
installer exists for.

Two defects, both mine, both fixed:
- **`fetch_latest` swallowed every exception** (`except Exception: return
  None`), so DNS, proxy, timeout and certificate all read as "no connection".
  It now RAISES; the silent-on-startup policy moved to the call site (startup
  silent + logs the reason, manual check names the cause).
- **The app trusted the machine's certificate store.** It now ships `certifi`
  (118 roots) and uses it for the check and the download, falling back to the
  system context when certifi is absent (source runs). Timeout 6 s → 15 s.

**Verified against the live API with the Windows store EXCLUDED**: trusting
only the shipped bundle the connection succeeds; with no trust anchors it is
refused (so the success is the bundle's, not an ambient default). 51/51
self-tests, ruff clean.

`QCS_diagnostico_update.ps1` (Desktop) is a standalone diagnostic for the field
notebook — DNS, port 443, proxy, .NET call, presence of the required root,
firewall rules, plus a verdict. It has NOT been run there yet; it will confirm
or refute the diagnosis above.

**Lesson worth keeping**: the v11.2 live update test passed on the development
machine, which is the one machine guaranteed to have every dependency. A
feature whose whole purpose is clean machines has to be tested on one.

## 2026-08-13 — v11.2.1 MERGED and TAGGED; installer rebuilt; release published

PR #21 merged (`d67ab9c`, carrying the message fix AND the user-manual deep
revision — title now "User Manual of…", zero version mentions in the body,
Installation rewritten installer-first, six staleness fixes). **Tagged
`v11.2.1` → `d67ab9c` after re-verifying 50/50 + ruff on the merged master;
branch deleted local and remote.** Installer rebuilt from the tagged master.

Remaining: owner publishes the v11.2.1 Release with `QCS_Setup_v11.2.1.exe`
attached (`RELEASE_v11.2.1_para_colar.md` on the Desktop) — and then opens the
installed QCS v11.2, which should offer this update by itself: the owner's own
live test of the self-update, on a real release.

*(GitHub served two transient 500s this round — one on a branch push, one on
the remote branch delete; both succeeded on retry. Retry before diagnosing.)*

## 2026-08-13 — v11.2.1 on branch `improvements-v11.2.1`, PR opened (superseded)

The virgin-install message fix (the nit below), released as a PATCH at the
owner's request — deliberately doubling as **the owner's own live test of the
self-update**: the installed v11.2 on this machine must offer v11.2.1 at
startup once the release is published with its setup asset.

- `QCS_Main`: the version gate now separates "no settings at all" (new
  message: *"Info: no saved settings; using the default quality criteria."*,
  no reset flag) from "settings from another version" (unchanged message +
  dialog). **All three cases exercised through the real UI-build path**
  (harness with a withdrawn Tk root): virgin → new message, flag None;
  v8.0 file → old message, flag 'v8.0'; same version → silent.
- `QCS_VERSION = 'v11.2.1'`; `changelog/v11.2.1.md`; manual bumped;
  `.iss` AppVersion 11.2.1. 50/50 self-tests, ruff clean.
- Two harness quirks worth remembering when testing this area: importing
  `QCS_Main` installs the app's stdout redirect (your own prints vanish —
  restore `sys.__stdout__`), and with a sink set but NO mainloop the redirect
  queues forever (the batch harness sees prints only because it never sets a
  sink).

After the merge: tag, rebuild bundle+installer, Release with the asset —
then the owner's v11.2 updates itself to v11.2.1, which is the point.

*(The nit, as recorded when found:)* on a **virgin install** the startup log
printed *"saved settings are from a different version (None != v11.2)"* —
misleading: nothing was saved and nothing was reset. Found by the owner on the
first fresh-install launch; installers make virgin environments common, which
is why a wording flaw dating from the v3.2 version gate only surfaced now.

## 2026-08-13 — v11.2 RELEASED, and the self-update loop CLOSED LIVE

The full chain ran on this machine against the real release:

- PR #20 merged (`e67b4a5`, also carrying the no-AI-attribution rule); tagged
  `v11.2`; branch deleted; 50/50 + ruff re-verified on the merged master
  before tagging. Repo PUBLIC (API answers 200 anonymously).
- Installer rebuilt from the tagged master; owner published the Release with
  **`QCS_Setup_v11.2.exe` attached** — confirmed via the anonymous API (the
  updater's own view).
- **Live loop, machine-verified end to end**: an install stamped v11.1.9
  (see the correction below) found the release at startup, offered the update,
  and on Yes: downloaded the real asset to `%TEMP%\QCS_Setup_v11.2.exe`
  (54.0 MB, 10:35:28), upgraded silently in place (registry DisplayVersion
  11.1.9 → **11.2**) and relaunched itself titled v11.2 at 10:36:29 — 61 s
  after the download. Three independent artifacts, one timeline. QCS v11.2
  remains installed at `%LOCALAPPDATA%\Programs\QCS`.

**Correction to the recipe this file used to carry**: "install v11.1 and watch
it update" was impossible — v11.1 HAS no updater; the feature ships in v11.2,
so the first version able to self-update is v11.2 itself. The live test used a
throwaway installer built from the v11.2 code stamped `v11.1.9` (never
committed, never shipped; working tree restored and verified clean). Real in
every leg that matters: real API, real release, real asset, real silent
upgrade, real relaunch.

**Path note for future tests**: since the dual-mode `.iss`, fresh per-user
installs land in `%LOCALAPPDATA%\Programs\QCS` (`{autopf}` per-user), not
`%LOCALAPPDATA%\QCS` (the v11.1-era default) — an upgrade over an existing
install keeps the old folder (`UsePreviousAppDir`). The first run of the live
test failed by looking at the old path.

Nothing is pending on v11.2. 23 tags, 23 releases.

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

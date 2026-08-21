# -*- coding: utf-8 -*-
"""Headless qualification harness for autonomous bug-hunting.

Drives the REAL QCS qualification pipeline (no GUI) over a list of Seaguard .bin
deployments with rotated settings, then checks invariants on each qualified sheet
and writes structured findings as JSON.

Usage:
    python qcs_headless_harness.py <bin_list.txt> <out_dir>
      <bin_list.txt> : one Data000.bin path per line (a deployment representative)
      <out_dir>      : where per-deployment outputs + findings.json are written

NOTE: this is a TEST harness, not part of the shipped app. It neutralises the
GUI-only pieces (stdout redirect, crash-handler dialog, interactive matplotlib
panels) so the pipeline runs unattended.
"""
import sys, os, json, tempfile, traceback

if len(sys.argv) < 3:
    print("usage: python qcs_headless_harness.py <bin_list.txt> <out_dir>")
    raise SystemExit(2)
LIST_FILE, OUT_DIR = sys.argv[1], sys.argv[2]
os.makedirs(OUT_DIR, exist_ok=True)

import matplotlib; matplotlib.use('Agg')
import QCS_Theme as _theme
class _StubStream:
    history = []
    def set_sink(self, *a, **k): pass
    def write(self, *a, **k): pass
    def flush(self): pass
_theme.install_output_redirect = lambda *a, **k: _StubStream()
_theme.install_crash_handler = lambda *a, **k: None
import QCS_Main as qm
import matplotlib.pyplot as plt

# hidden root + build the qualification tab once (creates the widget globals)
root = qm.Tk(); root.withdraw()
frame = qm.ttk.Frame(root); frame.pack()
qm.build_qualification_tab(frame, root)

# neutralise every interactive / blocking path
qm.messagebox.showinfo = lambda *a, **k: None
qm.messagebox.showwarning = lambda *a, **k: None
qm.messagebox.showerror = lambda *a, **k: None
qm.messagebox.askyesno = lambda *a, **k: True
qm.review_light_window = lambda lux_result, label: lux_result.get('proposed_cutoff')
qm.data._show_and_wait = lambda *a, **k: None
qm.log_line = lambda msg: None
# do NOT persist prefs: the qualification writes the shared qcs_user_settings.json,
# which would corrupt under parallel harness runs (and must not touch the user's file)
qm.save_user_prefs = lambda *a, **k: None

def set_entry(w, val):
    w.delete(0, 'end'); w.insert(0, val)

# Physically non-negative variables: a negative value surviving in a GOOD row
# is a bug. PAR/light negatives are clamped to valid zero; other listed sensors
# discard nonphysical values according to clean_below_zero.
NONNEG = ['pH', 'Turbidity (FTU)', 'Chlorophyll (ug/L)', 'PAR (umol/m2/s)',
          'O2 level (uM)', 'Dissolved organic matter (ppb)', 'CO2 Level (ppm)']
PLAUS = {'pH': (0, 14), 'Temperature (degC)': (-5, 45), 'Salinity (PSU)': (0, 45)}
VALID_FLAGS = {1, 2, 3, 4, 5, 9}

def check_sheet(df, meta):
    """Return a list of finding dicts for one qualified sheet."""
    out = []
    flag_cols = [c for c in df.columns if c.startswith('Flag_')]
    # 1) flag codes must be in the allowed set
    for c in flag_cols:
        bad = set(pd.unique(df[c].dropna())) - VALID_FLAGS
        if bad:
            out.append({'kind': 'invalid_flag_code', 'col': c, 'values': sorted(map(int, bad))})
    # 2) a physically non-negative variable must not be negative where flagged GOOD
    for var in NONNEG:
        fcol = 'Flag_' + {'pH': 'pH', 'Turbidity (FTU)': 'tur', 'Chlorophyll (ug/L)': 'chl',
                          'PAR (umol/m2/s)': 'PAR', 'O2 level (uM)': 'O2',
                          'Dissolved organic matter (ppb)': 'org', 'CO2 Level (ppm)': 'CO2'}[var]
        if var in df.columns and fcol in df.columns:
            good = df[df[fcol] == 1]
            neg = good[good[var] < 0]
            if len(neg):
                out.append({'kind': 'negative_in_good', 'var': var, 'n': int(len(neg)),
                            'min': float(neg[var].min())})
    # 3) plausibility bounds for good rows
    for var, (lo, hi) in PLAUS.items():
        fcol = 'Flag_' + {'pH': 'pH', 'Temperature (degC)': 'T', 'Salinity (PSU)': 'S'}[var]
        if var in df.columns and fcol in df.columns:
            good = df[df[fcol] == 1]
            oob = good[(good[var] < lo) | (good[var] > hi)]
            if len(oob):
                out.append({'kind': 'implausible_good', 'var': var, 'n': int(len(oob)),
                            'min': float(good[var].min()), 'max': float(good[var].max())})
    # 4) datetime monotonic
    if 'Datetime' in df.columns:
        dt = pd.to_datetime(df['Datetime'], errors='coerce')
        back = int((dt.diff() < pd.Timedelta(0)).sum())
        if back:
            out.append({'kind': 'datetime_backwards', 'n': back})
    # 5) fraction of rows blanked (flag 9) across the core vars - reported for context
    if 'Flag_T' in df.columns:
        miss = float((df['Flag_T'] == 9).mean())
        out.append({'kind': 'blanked_fraction', 'flag9_frac_T': round(miss, 3),
                    'rows': int(len(df))})
    return out

import pandas as pd
with open(LIST_FILE, encoding='utf-8') as f:
    bins = [ln.strip() for ln in f if ln.strip()]

results = []
for i, bpath in enumerate(bins):
    rec = {'bin': bpath, 'ok': False, 'findings': [], 'error': None}
    # rotate settings to cover the space across deployments
    profile = (i % 2 == 0)
    gmt = (i % 2 == 0)
    rem_bad = (i % 3 == 0)
    rem_susp = (i % 4 == 0)
    rec['settings'] = {'type': 'TSCP Profile' if profile else 'TSCP Mooring',
                       'gmt3': gmt, 'remove_bad': rem_bad, 'remove_suspect': rem_susp}
    try:
        outdir = tempfile.mkdtemp(prefix='qcs_h_', dir=OUT_DIR)
        set_entry(qm.fileNames_entry, bpath)
        qm.inputType_combobox.set('Seaguard')
        qm.dType_combobox.set(rec['settings']['type'])
        set_entry(qm.outputPath_entry, outdir)
        set_entry(qm.outputName_entry, 'QLF')
        qm.outputFilesFormat_combobox.set('.csv')
        qm.correct_gmt3h.set(gmt)
        qm.remove_bad.set(rem_bad); qm.remove_suspect.set(rem_susp)
        qm.select_profile_data.set(False)
        qm.check_variables.set(False)
        set_entry(qm.siteSelect_entry, 'TEST')
        qm.start_qualification()
        qf = qm.OUTPUT.get('last_qualified_file')
        if not qf or not os.path.exists(qf):
            rec['error'] = 'no qualified file produced'
        else:
            df = pd.read_csv(qf, sep=None, engine='python')
            rec['ok'] = True
            rec['shape'] = list(df.shape)
            rec['findings'] = check_sheet(df, rec)
    except Exception as e:
        rec['error'] = repr(e)
        rec['traceback'] = traceback.format_exc()[-1500:]
    finally:
        plt.close('all')
    results.append(rec)
    print("[%d/%d] %s -> %s (%d findings)" % (
        i + 1, len(bins), os.path.basename(os.path.dirname(bpath)),
        'OK' if rec['ok'] else 'ERROR', len(rec['findings'])), flush=True)

with open(os.path.join(OUT_DIR, 'findings.json'), 'w', encoding='utf-8') as f:
    json.dump(results, f, indent=1, default=str)

n_ok = sum(r['ok'] for r in results)
n_err = len(results) - n_ok
n_find = sum(len(r['findings']) for r in results)
print("\n==== DONE: %d deployments, %d ok, %d errored, %d raw findings ===="
      % (len(results), n_ok, n_err, n_find))
print("findings.json ->", os.path.join(OUT_DIR, 'findings.json'))

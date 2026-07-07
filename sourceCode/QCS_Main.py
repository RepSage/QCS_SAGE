# system modules
import os
import re
import sys
import time
import json
import shutil
import traceback
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from datetime import timedelta
from tkinter import *
from tkinter import ttk
from tkinter import filedialog
from tkinter import messagebox
from scipy import signal

# software modules
import QCS_DataHandler as data
import QCS_DataView as view
import QCS_Tests as QC
import QCS_Theme as theme
from QCS_Theme import ToolTip

# Run with no console window (launched via pythonw): send everything that would
# have gone to the terminal into the in-app Execution log instead, and never let
# a crash be silent. The log panel is attached later, once it exists.
_out = theme.install_output_redirect()
theme.install_crash_handler('QCS Data Qualification', _out)

# Global configuration
CONFIG = {
    'tsQualityTests': {
        'temperature sensor range': 'ON',
        'salinity sensor range': 'ON',
        'conductivity sensor range': 'ON',
        'pressure sensor range': 'ON',
        'dissolved oxygen sensor range': 'ON',
        'pH sensor range': 'ON',
        'chlorophyll sensor range': 'ON',
        'turbidity sensor range': 'ON',
        'temperature environmental range': 'ON',
        'salinity environmental range': 'ON',
        'conductivity environmental range': 'ON',
        'pressure environmental range': 'ON',
        'pH environmental range': 'ON',
        'chlorophyll environmental range': 'ON',
        'dissolved oxygen environmental range': 'ON',
        'dissolved organic matter environmental range': 'ON',
        'turbidity environmental range': 'ON',
        'temperature spikes': 'ON',
        'salinity spikes': 'ON',
        'conductivity spikes': 'ON',
        'pressure spikes': 'ON',
        'pH spikes': 'ON',
        'chlorophyll spikes': 'ON',
        'dissolved oxygen spikes': 'ON',
        'dissolved organic matter spikes': 'ON',
        'turbidity spikes': 'ON',
        'temperature rate of change': 'ON',
        'salinity rate of change': 'ON',
        'conductivity rate of change': 'ON',
        'pressure rate of change': 'ON',
        'temperature flat line': 'ON',
        'salinity flat line': 'ON',
        'conductivity flat line': 'ON',
        'pressure flat line': 'OFF',
        'temperature vertical gradient': 'ON',
        'salinity vertical gradient': 'ON',
        'conductivity vertical gradient': 'ON',
        'density inversion': 'ON',
        'light fouling window': 'ON'
    },
    'tsSettings': {
        #'depth_range': 1.55,
        # Sensor ranges (instrument limit - Aanderaa SeaGuard II default)
        'sensor_min_temp': -5,
        'sensor_max_temp': 40,
        'sensor_min_sal': 0,
        'sensor_max_sal': 45,
        'sensor_min_cond': 0,
        'sensor_max_cond': 75,
        'sensor_min_pres': 0,
        'sensor_max_pres': 6000,
        'sensor_min_O2': 0,
        'sensor_max_O2': 500,
        'sensor_min_pH': 0,
        'sensor_max_pH': 14,
        'sensor_min_chl': 0,
        'sensor_max_chl': 500,
        'sensor_min_tur': 0,
        'sensor_max_tur': 1500,
        # Environmental ranges (broad climatological envelope - entire Brazilian coast, v3.0)
        'env_min_temp': 8,
        'env_max_temp': 35,
        'env_min_sal': 20,
        'env_max_sal': 37.5,
        'env_min_cond': 5,
        'env_max_cond': 75,
        'env_min_pres': 0,
        'env_max_pres': 6000,
        'env_min_pH': 7.5,
        'env_max_pH': 8.4,
        'env_min_chl': 0,
        'env_max_chl': 30,
        'env_min_O2': 120,
        'env_max_O2': 450,
        'env_min_org': 0,
        'env_max_org': 50,
        'env_min_tur': 0,
        'env_max_tur': 50,
        # Light range: NOT a QC test (light uses the fouling window);
        # only sets the Y axis of the fixed-scale luminosity plot (HOBO).
        'env_min_lux': 0,
        'env_max_lux': 20000,
        'rep_cnt_fail': 20,
        'rep_cnt_susp': 15,
        # potential density may decrease with depth up to this
        # tolerance (kg/m3) without flagging inversion (profiles test)
        'dens_inv_tolerance': 0.03,
        # ---- HOBO light usage window (fouling test) ----
        # clean-sensor baseline = highest daily peak of the first N days;
        # light becomes BAD (unusable) from the final sustained decline where the
        # daily peak stays below lux_cutoff_frac x baseline and never recovers
        'lux_baseline_days': 7,
        'lux_cutoff_frac': 0.5,
        'lux_sustain_days': 3,
        # out-of-water readings at the ends of the HOBO file: trim while the
        # temperature deviates more than this (degC) from the neighboring stable segment
        'hobo_edge_temp_tol': 1.5,
        #'eps': 'AUTO',
    },
    # Per-variable factors for the spike, rate-of-change and vertical-gradient tests
    # (fail/susp = std multipliers; window = time window). One row per variable.
    'tsFactors': {
        'T':   {'fail': 3, 'susp': 2.5, 'window': '30M'},
        'S':   {'fail': 3, 'susp': 2.5, 'window': '30M'},
        'C':   {'fail': 3, 'susp': 2.5, 'window': '30M'},
        'P':   {'fail': 3, 'susp': 2.5, 'window': '30M'},
        'pH':  {'fail': 3, 'susp': 2.5, 'window': '30M'},
        'chl': {'fail': 3, 'susp': 2.5, 'window': '30M'},
        'O2':  {'fail': 3, 'susp': 2.5, 'window': '30M'},
        'org': {'fail': 3, 'susp': 2.5, 'window': '30M'},
        'tur': {'fail': 3, 'susp': 2.5, 'window': '30M'},
    },
    'tsQualityTests_vars': {},
    'tsSettings_entries': {},
    'tsFactors_entries': {}
}

# immutable copy of the default criteria, used by the 'Reset to Defaults' button
# (captured here, before restore_user_prefs/config can modify CONFIG)
import copy
DEFAULT_QUALITY_CONFIG = {
    'tsQualityTests': dict(CONFIG['tsQualityTests']),
    'tsSettings': dict(CONFIG['tsSettings']),
    'tsFactors': copy.deepcopy(CONFIG['tsFactors']),
}

# variables that have per-variable factors, with display names for the Settings table
FACTOR_VARS = [
    ('T', 'Temperature'), ('S', 'Salinity'), ('C', 'Conductivity'), ('P', 'Pressure'),
    ('pH', 'pH'), ('chl', 'Chlorophyll'), ('O2', 'Dissolved oxygen'),
    ('org', 'Organic matter'), ('tur', 'Turbidity'),
]

# Tooltips dictionary
TOOLTIPS = {
    'data_file': "Select the raw data file to be qualified\nSupported formats: .csv, .xlsx",
    'latitude': "Latitude of the collection site (decimal degrees, -90 to 90)\nSouthern hemisphere is negative (e.g. -17.5)\nUsed to convert pressure to depth",
    'longitude': "Longitude of the collection site (decimal degrees, -180 to 180)\nWestern hemisphere is negative (e.g. -40.0)\nUsed by the density inversion test",
    'macroregion': "Broad region of the world (currently only Brazil).\nStructured to add other regions in the future.",
    'region': "Region within the selected macroregion.\nSets a representative latitude/longitude used only to run the\nqualification (pressure->depth and density inversion). Small\nvariations do not change the results. Not used for HOBO.",
    'config_file': "OPTIONAL: Select the configuration file (.json)\ncontaining quality test parameters",
    'input_type': "Type of instrument that generated the data\nSeaguard: Standard CTD\nHOBO: Autonomous logger",
    'data_type': "Data collection type\nProfile: Vertical data (cast)\nMooring: Fixed-point temporal data",
    'pressure_unit': "Pressure unit of raw data\nAutomatic conversion to decibar",
    'conductivity_unit': "Conductivity unit of raw data\nAutomatic conversion to mS/cm",
    'gmt_correction': "Applies GMT-3 hour correction for data\ncollected in Brazilian timezone",
    'profile_selection': "Allows selecting only descent or ascent\nfor profile data (removes inversion)",
    'variable_check': "Opens interactive point-cut panels to manually DISMISS\nspurious points, one per chosen variable (you pick which).\nDismissed points get flag 5 and are kept for traceability.\nWithout this, only the mooring Depth review opens.",
    'output_folder': "Folder where qualification results\nwill be saved",
    'output_name': "Base name for output files\n(without extension)",
    'output_format': "Output format for the qualified data\n.csv: Delimited text\n.xlsx: Excel\n(the automatic report files are always .xlsx)",
    'remove_bad': "Automatically removes data flagged\nas BAD (flag 4) in output",
    'remove_suspect': "Automatically removes data flagged\nas SUSPECT (flag 3) in output",
    'site_code': "Identification code for the\ncollection site (max 10 characters)",
    'run_button': "Runs the qualification process\nwith configured parameters",
    'settings_button': "Opens test configuration window\nand quality parameters",
    'export_button': "Exports current settings\nto a JSON file"
}

TS_SETTINGS_TOOLTIPS = {
    'depth_range': "Maximum allowed depth range variation (meters)\nUsed in depth range test",
    'sensor_min_temp': "Minimum valid temperature for sensor range (°C)\nValues below will be flagged",
    'sensor_max_temp': "Maximum valid temperature for sensor range (°C)\nValues above will be flagged",
    'sensor_min_sal': "Minimum valid salinity for sensor range (PSU)\nValues below will be flagged",
    'sensor_max_sal': "Maximum valid salinity for sensor range (PSU)\nValues above will be flagged",
    'sensor_min_cond': "Minimum valid conductivity for sensor range (mS/cm)\nValues below will be flagged",
    'sensor_max_cond': "Maximum valid conductivity for sensor range (mS/cm)\nValues above will be flagged",
    'sensor_min_pres': "Minimum valid pressure for sensor range (dbar)\nValues below will be flagged",
    'sensor_max_pres': "Maximum valid pressure for sensor range (dbar)\nValues above will be flagged",
    'sensor_min_O2': "Minimum valid dissolved oxygen for sensor range (μM)\nValues below will be flagged",
    'sensor_max_O2': "Maximum valid dissolved oxygen for sensor range (μM)\nValues above will be flagged",
    'sensor_min_pH': "Minimum valid pH for sensor range\nValues below will be flagged",
    'sensor_max_pH': "Maximum valid pH for sensor range\nValues above will be flagged",
    'sensor_min_chl': "Minimum valid chlorophyll for sensor range (μg/L)\nValues below will be flagged",
    'sensor_max_chl': "Maximum valid chlorophyll for sensor range (μg/L)\nValues above will be flagged",
    'sensor_min_tur': "Minimum valid turbidity for sensor range (FTU)\nValues below will be flagged",
    'sensor_max_tur': "Maximum valid turbidity for sensor range (FTU)\nValues above will be flagged",
    'env_min_temp': "Minimum expected environmental temperature (°C)\nValues below will be flagged",
    'env_max_temp': "Maximum expected environmental temperature (°C)\nValues above will be flagged",
    'env_min_sal': "Minimum expected environmental salinity (PSU)\nValues below will be flagged",
    'env_max_sal': "Maximum expected environmental salinity (PSU)\nValues above will be flagged",
    'env_min_cond': "Minimum expected environmental conductivity (mS/cm)\nValues below will be flagged",
    'env_max_cond': "Maximum expected environmental conductivity (mS/cm)\nValues above will be flagged",
    'env_min_pres': "Minimum expected environmental pressure (dbar)\nValues below will be flagged",
    'env_max_pres': "Maximum expected environmental pressure (dbar)\nValues above will be flagged",
    'env_min_pH': "Minimum expected environmental pH\nValues below will be flagged",
    'env_max_pH': "Maximum expected environmental pH\nValues above will be flagged",
    'env_min_chl': "Minimum expected chlorophyll (μg/L)\nValues below will be flagged",
    'env_max_chl': "Maximum expected chlorophyll (μg/L)\nValues above will be flagged",
    'env_min_O2': "Minimum expected dissolved oxygen (μM)\nValues below will be flagged",
    'env_max_O2': "Maximum expected dissolved oxygen (μM)\nValues above will be flagged",
    'env_min_org': "Minimum expected organic matter (ppb)\nValues below will be flagged",
    'env_max_org': "Maximum expected organic matter (ppb)\nValues above will be flagged",
    'env_min_tur': "Minimum expected turbidity (FTU)\nValues below will be flagged",
    'env_max_tur': "Maximum expected turbidity (FTU)\nValues above will be flagged",
    'env_min_lux': "Minimum luminosity (lux) for the FIXED-SCALE light plot.\nNot a QC test - only sets the plot's y-axis (HOBO).",
    'env_max_lux': "Maximum luminosity (lux) for the FIXED-SCALE light plot.\nNot a QC test - only sets the plot's y-axis (HOBO).",
    'rep_cnt_fail': "Number of repeated values to flag as FAIL\nFor flat line test",
    'rep_cnt_susp': "Number of repeated values to flag as SUSPECT\nFor flat line test",
    'dens_inv_tolerance': "Density inversion tolerance (kg/m3)\nPotential density may decrease with depth up to this\nvalue before the pair is flagged as SUSPECT",
    'lux_baseline_days': "HOBO light fouling: clean-sensor baseline =\nmax daily light peak of the FIRST N days after deployment\n(max, so a cloudy install day does not lower it)",
    'lux_cutoff_frac': "HOBO light fouling: fraction of the clean-sensor baseline\nbelow which light becomes BAD (0.5 = 50%)\nThe applied cutoff is shown in the review plot and saved with the results",
    'lux_sustain_days': "HOBO light fouling: the daily peak must stay below the\nthreshold for this many CONSECUTIVE days before cutting\n(avoids cutting on a cloudy spell)",
    'hobo_edge_temp_tol': "HOBO edge trim: leading/trailing samples are discarded while\ntemperature deviates more than this (degC) from the nearby\nstable segment (out-of-water readings at deployment/recovery)",
    #'eps': "Epsilon value for flat line detection\nMinimum difference to consider values different",
}

# tooltips for the per-variable factor columns (Factors per Variable tab)
TS_FACTORS_TOOLTIPS = {
    'fail': "Robust-sigma multiplier to flag as FAIL\nSpike and vertical-gradient tests\n(rate of change is capped at SUSPECT per QARTOD)",
    'susp': "Robust-sigma multiplier to flag as SUSPECT\nUsed in spike, rate-of-change and vertical-gradient tests",
    'window': "Time window for the local sigma (spike and rate-of-change tests)\nFormat: '2D' (days), '3H' (hours), '30M' (minutes), '45S' (seconds) or 'WHOLE'\nMust cover at least 3 samples at the data's sampling interval",
}

TS_QUALITY_TESTS_TOOLTIPS = {
    'temperature sensor range': "Check if temperature values are within sensor specifications",
    'salinity sensor range': "Check if salinity values are within sensor specifications",
    'conductivity sensor range': "Check if conductivity values are within sensor specifications",
    'pressure sensor range': "Check if pressure values are within sensor specifications",
    'dissolved oxygen sensor range': "Check if dissolved oxygen values are within sensor specifications",
    'pH sensor range': "Check if pH values are within sensor specifications",
    'chlorophyll sensor range': "Check if chlorophyll values are within sensor specifications",
    'turbidity sensor range': "Check if turbidity values are within sensor specifications",
    'temperature environmental range': "Check if temperature values are environmentally plausible",
    'salinity environmental range': "Check if salinity values are environmentally plausible",
    'conductivity environmental range': "Check if conductivity values are environmentally plausible",
    'pressure environmental range': "Check if pressure values are environmentally plausible",
    'pH environmental range': "Check if pH values are environmentally plausible",
    'chlorophyll environmental range': "Check if chlorophyll values are environmentally plausible",
    'dissolved oxygen environmental range': "Check if dissolved oxygen values are environmentally plausible",
    'dissolved organic matter environmental range': "Check if organic matter values are environmentally plausible",
    'turbidity environmental range': "Check if turbidity values are environmentally plausible",
    'temperature spikes': "Detect abnormal spikes in temperature values",
    'salinity spikes': "Detect abnormal spikes in salinity values",
    'conductivity spikes': "Detect abnormal spikes in conductivity values",
    'pressure spikes': "Detect abnormal spikes in pressure values",
    'pH spikes': "Detect abnormal spikes in pH values",
    'chlorophyll spikes': "Detect abnormal spikes in chlorophyll values",
    'dissolved oxygen spikes': "Detect abnormal spikes in dissolved oxygen values",
    'dissolved organic matter spikes': "Detect abnormal spikes in organic matter values",
    'turbidity spikes': "Detect abnormal spikes in turbidity values",
    'temperature rate of change': "Check for unrealistic temperature changes over time",
    'salinity rate of change': "Check for unrealistic salinity changes over time",
    'conductivity rate of change': "Check for unrealistic conductivity changes over time",
    'pressure rate of change': "Check for unrealistic pressure changes over time",
    'temperature flat line': "Detect unchanging temperature values (sensor stuck)",
    'salinity flat line': "Detect unchanging salinity values (sensor stuck)",
    'conductivity flat line': "Detect unchanging conductivity values (sensor stuck)",
    'pressure flat line': "Detect unchanging pressure values (sensor stuck)",
    'temperature vertical gradient': "Check for unrealistic temperature changes with depth",
    'salinity vertical gradient': "Check for unrealistic salinity changes with depth",
    'conductivity vertical gradient': "Check for unrealistic conductivity changes with depth",
    'density inversion': "Check water column stability: potential density must not decrease with depth (profiles only)",
    'light fouling window': "HOBO only: flag light as BAD after the daily peak decays\nbelow a fraction of the clean-sensor baseline (sensor fouling).\nParameters in the Parameters tab (lux_*); cutoff reviewed on a plot before applying"
}

# ----- user preferences: last folders and last choices, kept between sessions -----
def settings_store_path():
    # the settings file lives next to the script (or next to the .exe when frozen),
    # NOT in _MEIPASS, which is recreated at every run
    if getattr(sys, 'frozen', False):
        base = os.path.dirname(sys.executable)
    else:
        base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, 'qcs_user_settings.json')

USER_PREFS = {}

def load_user_prefs():
    global USER_PREFS
    try:
        with open(settings_store_path(), 'r', encoding='utf-8') as f:
            USER_PREFS = json.load(f)
    except Exception:
        USER_PREFS = {}

def save_user_prefs():
    try:
        with open(settings_store_path(), 'w', encoding='utf-8') as f:
            json.dump(USER_PREFS, f, indent=4)
    except Exception as e:
        print('Warning: could not save user preferences: %s' % e)

load_user_prefs()

def selectFiles():
    # HOBO with N>1 replicates: pick the N files at once (multi-select);
    # otherwise a single file.
    n_rep = int(replicate_combobox.get()) if inputType_combobox.get() == 'HOBO' else 1
    if n_rep > 1:
        names = filedialog.askopenfilenames(
            initialdir=USER_PREFS.get('last_data_dir', '/'),
            title="Select the %d HOBO replicate files" % n_rep,
            filetypes=(("Data files", "*.csv *.xlsx"), ("All files", "*.*")))
        names = list(names)
        if not names:
            return
        first = names[0]
        fileNames_entry.delete(0, END)
        fileNames_entry.insert(0, ';'.join(names))
    else:
        first = filedialog.askopenfilename(
            initialdir=USER_PREFS.get('last_data_dir', '/'),
            title="Select data file",
            filetypes=(("Data files", "*.csv *.xlsx"), ("All files", "*.*")))
        if not first:
            return
        fileNames_entry.delete(0, END)
        fileNames_entry.insert(0, first)
    USER_PREFS['last_data_dir'] = os.path.dirname(first)
    save_user_prefs()
    # auto-fill the output folder from the first file; the name follows the
    # replicate count (single vs combined)
    outputPath_entry.delete(0, END)
    outputPath_entry.insert(0, os.path.dirname(first))
    apply_output_name()

def apply_output_name():
    """Auto-fills 'Output File Name' from the selected file(s) and the replicate
    count (the user can still edit it): a single file -> '<file>_QLF'; N>1 HOBO
    replicates -> the COMBINED name (leading device token like 'HOBO1_' dropped)
    + '_combined_QLF'. The individual replicate files keep their own '<file>_QLF'
    names regardless."""
    paths = [p.strip() for p in fileNames_entry.get().split(';') if p.strip()]
    if not paths:
        return
    base = os.path.splitext(os.path.basename(paths[0]))[0]
    n_rep = int(replicate_combobox.get()) if inputType_combobox.get() == 'HOBO' else 1
    if n_rep > 1:
        stripped = re.sub(r'(?i)^hobo\s*\d+[ _-]*', '', base)   # drop 'HOBO1_' device token
        name = (stripped or base) + '_combined_QLF'
    else:
        name = base + '_QLF'
    outputName_entry.delete(0, END)
    outputName_entry.insert(0, name)

def selectOutputFolder():
    folderPath = filedialog.askdirectory(
        initialdir=USER_PREFS.get('last_output_dir', '/'),
        title="Select output folder"
    )
    if folderPath:
        outputPath_entry.delete(0, END)
        outputPath_entry.insert(0, folderPath)
        USER_PREFS['last_output_dir'] = folderPath
        save_user_prefs()

def apply_config_file(config_path):
    """Loads a JSON configuration file into CONFIG.
    Returns None on success or the error message."""
    try:
        with open(config_path, 'r') as f:
            config_data = json.load(f)
        if 'tsQualityTests' in config_data:
            CONFIG['tsQualityTests'].update(config_data['tsQualityTests'])
        if 'tsSettings' in config_data:
            CONFIG['tsSettings'].update(config_data['tsSettings'])
        if 'tsFactors' in config_data:
            for k, v in config_data['tsFactors'].items():
                if k in CONFIG['tsFactors']:
                    CONFIG['tsFactors'][k].update(v)
        return None
    except Exception as e:
        return str(e)

# NOTE: the 'Config File' field (import .json) and the 'Export Settings' button were
# removed from the interface at the user's request (they duplicated the Settings tab).
# The selectConfigFile function was removed because it referenced the removed widget;
# apply_config_file (above) and export_config (below) remain defined for easy
# reactivation in the future (just recreate the widgets and rewire the commands).

def export_config():
    # Updates the current settings before exporting
    invalid = save_settings_values()
    if invalid:
        messagebox.showwarning("Invalid values",
                               "Fix these fields before exporting (not valid numbers/format):\n\n- "
                               + "\n- ".join(invalid))
        return

    filepath = filedialog.asksaveasfilename(
        defaultextension=".json",
        filetypes=(("JSON files", "*.json"), ("All files", "*.*")),
        title="Export settings"
    )
    
    if filepath:
        try:
            config_to_export = {
                "tsQualityTests": CONFIG['tsQualityTests'],
                "tsSettings": CONFIG['tsSettings'],
                "tsFactors": CONFIG['tsFactors']
            }
            
            with open(filepath, 'w') as f:
                json.dump(config_to_export, f, indent=4)
            
            messagebox.showinfo("Success", f"Success exporting settings:\n{filepath}")
        except Exception as e:
            messagebox.showerror("Error", f"Fail exporting settings:\n{str(e)}")

def save_settings_values():
    """Updates CONFIG with the current interface values.
    Returns the list of invalid fields (kept with their previous value),
    so the caller can warn the user instead of ignoring them silently."""
    invalid = []

    # Update tsQualityTests
    for test, var in CONFIG['tsQualityTests_vars'].items():
        CONFIG['tsQualityTests'][test] = var.get()

    # Update tsSettings (all numeric: int or float)
    for param, entry in CONFIG['tsSettings_entries'].items():
        value = entry.get().strip()
        try:
            CONFIG['tsSettings'][param] = float(value) if '.' in value else int(value)
        except ValueError:
            invalid.append(param.replace('_', ' '))

    # Update per-variable factors (fail/susp numeric, window '2D/3H/30M/45S/WHOLE')
    window_format = re.compile(r'^\d+\s*[DHMS]$|^WHOLE$', re.IGNORECASE)
    for key, entries in CONFIG['tsFactors_entries'].items():
        try:
            CONFIG['tsFactors'][key]['fail'] = float(entries['fail'].get())
        except ValueError:
            invalid.append('%s fail factor' % key)
        try:
            CONFIG['tsFactors'][key]['susp'] = float(entries['susp'].get())
        except ValueError:
            invalid.append('%s susp factor' % key)
        window_val = entries['window'].get().strip()
        if window_format.match(window_val):
            CONFIG['tsFactors'][key]['window'] = window_val
        else:
            invalid.append('%s time window' % key)
    return invalid

def collect_input_settings():
    """Validates and collects the interface settings. Returns True if all is ok."""
    if not fileNames_entry.get().strip():
        messagebox.showwarning("Warning", "Select the data file to be qualified\n('Data File' field).")
        return False
    # HOBO redundant replicates: N spreadsheets chosen at once (';'-separated);
    # for Seaguard or 1 replicate this is just the single file.
    n_rep = int(replicate_combobox.get()) if inputType_combobox.get() == 'HOBO' else 1
    replicate_files = [p.strip() for p in fileNames_entry.get().split(';') if p.strip()]
    if len(replicate_files) != n_rep:
        messagebox.showwarning("Warning",
                               "Replicates = %d, but %d file(s) are selected.\nSelect exactly %d "
                               "file(s) (Browse allows multi-select for HOBO replicates)."
                               % (n_rep, len(replicate_files), n_rep))
        return False
    for f in replicate_files:
        if not os.path.isfile(f):
            messagebox.showerror("Error", "Data file not found:\n%s" % f)
            return False
        if not re.search(r'\.(csv|xlsx)$', f, re.IGNORECASE):
            messagebox.showwarning("Warning", "Unsupported file format (use .csv or .xlsx):\n%s" % f)
            return False
    INPUT['replicate_files'] = replicate_files
    INPUT['n_replicates'] = n_rep
    data_path = replicate_files[0]   # drives file_name/raw_data_path below
    if inputType_combobox.get() not in ('Seaguard', 'HOBO'):
        messagebox.showwarning("Warning", "Select the instrument type\n('Input Type' field).")
        return False
    # HOBO has no TSCP collection type (it is a time series): Data Type stays empty
    if inputType_combobox.get() != 'HOBO' and dType_combobox.get() not in ('TSCP Profile', 'TSCP Mooring'):
        messagebox.showwarning("Warning", "Select the data collection type\n('Data Type' field).")
        return False
    out_dir = outputPath_entry.get().strip()
    if not out_dir:
        messagebox.showwarning("Warning", "Select the folder where results will be saved\n('Output Folder' field).")
        return False
    if not os.path.isdir(out_dir):
        messagebox.showerror("Error", "The output folder does not exist:\n%s" % out_dir)
        return False
    if not outputName_entry.get().strip():
        messagebox.showwarning("Warning", "Define a name for the output files\n('Output File Name' field).")
        return False
    if outputFilesFormat_combobox.get() not in ('.csv', '.xlsx'):
        messagebox.showwarning("Warning", "Select the output format\n(.csv or .xlsx).")
        return False

    file_name_match = re.search(r'[^\\/]+$', data_path, re.IGNORECASE)
    INPUT['file_name'] = file_name_match.group() if file_name_match else ""
    INPUT['raw_data_path'] = os.path.dirname(data_path)

    INPUT['pressure_unit'] = pressure_unit_combobox.get() or 'kPa'
    INPUT['conductivity_unit'] = conductivity_unit_combobox.get() or 'mS/cm'
    INPUT['correct_gmt3h'] = correct_gmt3h.get()
    INPUT['select_profile_data'] = select_profile_data.get()
    INPUT['check_variables'] = check_variables.get()
    INPUT['input_type'] = inputType_combobox.get()
    INPUT['data_type'] = dType_combobox.get()

    OUTPUT['output_file_path'] = out_dir
    OUTPUT['output_data_format'] = outputFilesFormat_combobox.get()
    OUTPUT['output_file_name'] = outputName_entry.get() + OUTPUT['output_data_format']
    OUTPUT['remove_bad'] = remove_bad.get()
    OUTPUT['remove_suspect'] = remove_suspect.get()

    INPUT['site'] = siteSelect_entry.get().strip().upper()
    if len(INPUT['site']) > 10:
        messagebox.showwarning("Warning", "Site Code must have at most 10 characters\n('Site Code' field).")
        return False

    # The selected coastal region provides a representative latitude/longitude,
    # used ONLY to run the qualification (pressure->depth and the density
    # inversion test) and never written to the output. Small lat/long variations
    # do not affect these results meaningfully. Irrelevant for HOBO (no pressure).
    macroregion = macroregion_combobox.get()
    region = region_combobox.get()
    INPUT['macroregion'] = macroregion
    INPUT['region'] = region
    INPUT['latitude'], INPUT['longitude'] = REGION_COORDS.get(macroregion, {}).get(
        region, REGION_COORDS[DEFAULT_MACROREGION][DEFAULT_REGION])
    if INPUT['input_type'] == 'Seaguard':
        INPUT['coord_msgs'] = ["region '%s / %s' -> lat %.1f, lon %.1f (used for depth "
                               "conversion and density inversion)"
                               % (macroregion, region, INPUT['latitude'], INPUT['longitude'])]
    else:
        INPUT['coord_msgs'] = []

    if INPUT['data_type'] == 'TSCP Profile':
        INPUT['profile'] = True
    else:
        INPUT['profile'] = False

    # stores the user's last choices for the next session
    USER_PREFS.update({
        'data_file': data_path,
        'input_type': INPUT['input_type'],
        'data_type': INPUT['data_type'],
        'pressure_unit': INPUT['pressure_unit'],
        'conductivity_unit': INPUT['conductivity_unit'],
        'correct_gmt3h': INPUT['correct_gmt3h'],
        'select_profile_data': INPUT['select_profile_data'],
        'check_variables': INPUT['check_variables'],
        'output_folder': out_dir,
        'output_name': outputName_entry.get(),
        'output_format': OUTPUT['output_data_format'],
        'remove_bad': OUTPUT['remove_bad'],
        'remove_suspect': OUTPUT['remove_suspect'],
        'site_code': INPUT['site'],
        'macroregion': INPUT['macroregion'],
        'region': INPUT['region'],
        'qcs_version': data.QCS_VERSION,
        'tsQualityTests': dict(CONFIG['tsQualityTests']),
        'tsSettings': dict(CONFIG['tsSettings']),
        'tsFactors': {k: dict(v) for k, v in CONFIG['tsFactors'].items()},
    })
    save_user_prefs()
    return True

# permanent documentation of the replicate-combination method, written into the
# combined folder (parallel to the light-window plot documenting the cutoff)
COMBINE_METHOD_TEXT = """QCS - HOBO redundant replicates: combination method
====================================================

%d HOBO replicates of the same deployment were qualified INDEPENDENTLY (each with
its own light-window review) and then combined into this single series.

TEMPERATURE
  Combined value = the MEAN of the replicates that are acceptable (Flag_T <= 2) at
  each timestamp. Replicates are aligned to the FIRST replicate's timestamps by
  NEAREST match within half the sampling interval (redundant HOBOs are never
  started at the exact same second, but that offset is tiny compared with the
  sampling step, so paired readings are effectively simultaneous - it is a nearest
  match, not interpolation). The between-replicate spread (max - min) is kept in
  the 'Temperature spread (degC)' column; when it exceeds 0.5 degC the combined
  Flag_T is set to SUSPECT (3) - the replicates disagree, which is itself a QC
  signal. The combined series has the same timestamps (and row count) as the first
  replicate.

LIGHT
  Combined value = the per-timestamp MAX of the NON-fouled readings (Flag_lux != 4).
  Fouling only attenuates light, so the brightest unfouled sensor is the most
  reliable. The combined light stays good (Flag_lux 1) while AT LEAST ONE replicate
  is unfouled, and becomes BAD (4) only once EVERY replicate is fouled - so the
  usable window is extended to the last replicate to foul. Light is NOT averaged
  (that would mix clean and fouled sensors). Each replicate's own light-window plot
  (QCS_light_window_<replicate>.svg) is included here so you can see WHERE the
  combined window ends and WHY.
"""

def write_combined_replicates(combined, light_plots=()):
    """Writes the combined HOBO replicates sheet to a
    '<site>_<ddmmyy start>_<ddmmyy end>_combined_QLF' folder (reference dates
    taken from the combined data, matching the user's file naming convention,
    e.g. A2_070924_200325_combined_QLF). Each replicate's light-window plot is
    copied in, renamed by replicate - the documentation of WHY the combined
    usable window ends where it ends. Returns the folder path."""
    combined = combined.copy()
    combined.insert(0, 'Sample number', range(1, len(combined) + 1))
    combined['QCS version'] = data.QCS_VERSION
    ordered = data.order_var(combined, 1, data_type='hobo')
    # the combined name comes from the 'Output File Name' field (auto-filled to
    # '<...>_combined_QLF' and editable); falls back to '<site>_<start>_<end>_
    # combined_QLF' from the data if the field is empty
    base = re.sub(r'\.(csv|xlsx)$', '', OUTPUT.get('output_file_name', ''), flags=re.IGNORECASE).strip()
    if not base:
        site = str(INPUT.get('site') or 'HOBO') or 'HOBO'
        t0 = pd.Timestamp(ordered['Datetime'].iloc[0])
        t1 = pd.Timestamp(ordered['Datetime'].iloc[-1])
        base = '%s_%s_%s_combined_QLF' % (site, t0.strftime('%d%m%y'), t1.strftime('%d%m%y'))
    root = os.path.join(OUTPUT['output_file_path'], base)
    folder = os.path.join(root, 'QCS qualified hobo data')
    os.makedirs(folder, exist_ok=True)
    if 'csv' in OUTPUT.get('output_data_format', '.xlsx').lower():
        ordered.to_csv(os.path.join(folder, base + '.csv'), index=False)
    else:
        data.save_excel_autofit(ordered, os.path.join(folder, base + '.xlsx'))
    # copy each replicate's light-window plot (kept with the 'QCS_' prefix so
    # build_database keeps ignoring them when scanning folders)
    for plot in light_plots:
        rep_folder = os.path.basename(os.path.dirname(os.path.dirname(plot)))  # '<replicate>_QLF'
        rep_base = re.sub(r'_QLF$', '', rep_folder)
        try:
            shutil.copy(plot, os.path.join(folder, 'QCS_light_window_%s.svg' % rep_base))
        except Exception as e:
            log_line('WARNING: could not copy the light window plot of %s: %s' % (rep_base, e))
    # method note: permanent documentation of HOW the replicates were combined
    with open(os.path.join(folder, 'QCS_combine_method.txt'), 'w', encoding='utf-8') as f:
        f.write(COMBINE_METHOD_TEXT % INPUT.get('n_replicates', len(light_plots) or 2))
    return root

def start_qualification():
    """Runs the qualification without closing the main window, allowing new runs.
    For HOBO with N>1 replicates, each file is qualified independently (its own
    light-window review) and then combined into one series."""
    if not collect_input_settings():
        return
    run_button.config(state='disabled')
    window.config(cursor='watch')
    files = INPUT.get('replicate_files') or [None]
    n = len(files)
    try:
        qualified_dfs = []
        light_plots = []
        for idx, fpath in enumerate(files, start=1):
            INPUT['file_name'] = os.path.basename(fpath)
            INPUT['raw_data_path'] = os.path.dirname(fpath)
            if n > 1:
                status_var.set("Qualifying replicate %d of %d..." % (idx, n))
                log_line('=== Replicate %d/%d: %s ===' % (idx, n, INPUT['file_name']))
            else:
                status_var.set("Running qualification... the window may not respond while processing.")
                log_line('=== Qualification started: %s ===' % INPUT['file_name'])
            window.update_idletasks()
            run_full_qualification()
            qualified_dfs.append(OUTPUT['last_qualified_df'])
            if OUTPUT.get('last_light_plot'):
                light_plots.append(OUTPUT['last_light_plot'])
        if n > 1:
            status_var.set("Combining %d replicates..." % n)
            window.update_idletasks()
            combined, cmsgs = data.combine_hobo_replicates(qualified_dfs)
            for m in cmsgs:
                log_line(m)
            OUTPUT['last_output_root'] = write_combined_replicates(combined, light_plots)
            log_line('Combined replicates saved to: %s' % OUTPUT['last_output_root'])
        status_var.set("Done - results saved to %s" % OUTPUT.get('last_output_root', ''))
        messagebox.showinfo("Done",
                            "Qualification completed successfully!\n\n"
                            "Results saved to:\n%s\n\n"
                            "You can select another file and run a new qualification "
                            "without closing the program." % OUTPUT.get('last_output_root', ''))
    except Exception as e:
        # the full traceback goes to the log; the dialog points to file/line
        for line in traceback.format_exc().strip().splitlines():
            log_line('ERROR: %s' % line)
        status_var.set("Qualification interrupted by an error - see the execution log.")
        messagebox.showerror("Qualification error",
                             "The qualification was interrupted by an error:\n\n%s\n\n"
                             "Location: %s\n(full traceback in the Execution log)\n\n"
                             "Some files may have been partially generated in the output "
                             "folder before the error. Check the input file and the "
                             "settings and try again." % (e, _error_location(e)))
    finally:
        plt.close('all')
        os.chdir(rootPath)
        run_button.config(state='normal')
        window.config(cursor='')

def restore_user_prefs():
    """Restores the user's last choices in the interface."""
    p = USER_PREFS

    def set_entry(entry, key):
        if p.get(key):
            entry.delete(0, END)
            entry.insert(0, p[key])

    set_entry(fileNames_entry, 'data_file')
    set_entry(outputPath_entry, 'output_folder')
    set_entry(outputName_entry, 'output_name')
    set_entry(siteSelect_entry, 'site_code')
    if p.get('macroregion') in REGIONS:
        macroregion_combobox.set(p['macroregion'])
        update_regions()
    if p.get('region') in REGION_COORDS.get(macroregion_combobox.get(), {}):
        region_combobox.set(p['region'])
    if p.get('input_type'):
        inputType_combobox.set(p['input_type'])
    if p.get('data_type'):
        dType_combobox.set(p['data_type'])
    if p.get('pressure_unit'):
        pressure_unit_combobox.set(p['pressure_unit'])
    if p.get('conductivity_unit'):
        conductivity_unit_combobox.set(p['conductivity_unit'])
    if p.get('output_format'):
        outputFilesFormat_combobox.set(p['output_format'])
    correct_gmt3h.set(p.get('correct_gmt3h', False))
    select_profile_data.set(p.get('select_profile_data', False))
    check_variables.set(p.get('check_variables', False))
    remove_bad.set(p.get('remove_bad', False))
    remove_suspect.set(p.get('remove_suspect', False))
    update_profile_checkbox_state()
    update_inputtype_state()  # reapplies the HOBO state (disables fields) if applicable
    # Restore the quality CRITERIA only if they were saved by the SAME program
    # version. On a version change, keep the new code defaults (so criteria
    # improvements take effect) instead of the user's old saved criteria.
    if p.get('qcs_version') != data.QCS_VERSION:
        print("MESSAGE: saved settings are from a different version (%s != %s); "
              "using the current default quality criteria." % (p.get('qcs_version'), data.QCS_VERSION))
        return
    if isinstance(p.get('tsQualityTests'), dict):
        for k, v in p['tsQualityTests'].items():
            if k in CONFIG['tsQualityTests']:
                CONFIG['tsQualityTests'][k] = v
    if isinstance(p.get('tsSettings'), dict):
        for k, v in p['tsSettings'].items():
            if k in CONFIG['tsSettings']:
                CONFIG['tsSettings'][k] = v
    if isinstance(p.get('tsFactors'), dict):
        for k, v in p['tsFactors'].items():
            if k in CONFIG['tsFactors'] and isinstance(v, dict):
                CONFIG['tsFactors'][k].update(v)

def show_help():
    help_text = """
    QCS - QUALITY CONTROL SYSTEM

    INSTRUCTIONS:
    1. Configure input parameters (left side)
    2. Set output parameters (right side)
    3. Adjust tests in the Settings menu
    4. Click RUN QUALIFICATION to process

    TIPS:
    - Hover over fields to see tooltips
    - Use the settings window for fine adjustments
    - Results are saved in automatic subfolders

    QCS - Quality Control System %s
    Developed for automatic data qualification
    """ % data.QCS_VERSION
    messagebox.showinfo("QCS Help", help_text)

def open_settings_window():
    settings_win = Toplevel()
    settings_win.title(" Quality Control Settings")
    theme.set_scaled_geometry(settings_win, 900, 700, min_width=720, min_height=520)
    settings_win.configure(bg=theme.surface_color())

    notebook = ttk.Notebook(settings_win)
    notebook.pack(fill='both', expand=True, padx=8, pady=8)
    
    # Tests Tab
    tests_frame = ttk.Frame(notebook)
    notebook.add(tests_frame, text="Quality Control Tests")
    create_tests_tab(tests_frame)
    
    # Parameters Tab
    params_frame = ttk.Frame(notebook)
    notebook.add(params_frame, text="Parameters")
    create_params_tab(params_frame)

    # Per-variable factors Tab
    factors_frame = ttk.Frame(notebook)
    notebook.add(factors_frame, text="Factors per Variable")
    create_factors_tab(factors_frame)

    # remove the dashed focus ring from the selected tab's label
    theme.suppress_notebook_focus_ring(notebook)

    # Button frame
    button_frame = ttk.Frame(settings_win)
    button_frame.pack(fill='x', pady=10)

    # 'Export Settings' and the 'Config File' field (import) were removed from the
    # interface at the user's request (they duplicated the Settings tab). The functions
    # export_config / selectConfigFile remain defined for easy reactivation.
    ttk.Button(button_frame, text="Reset to Defaults",
              command=reset_settings_to_defaults, width=20).pack(side='left', padx=5)

    ttk.Button(button_frame, text="Save Settings",
              command=lambda: save_settings(settings_win),
              style='Accent.TButton').pack(side='right', padx=5)

def create_tests_tab(parent):
    canvas = Canvas(parent, bg=theme.surface_color(), highlightthickness=0)
    scrollbar = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
    scrollable_frame = ttk.Frame(canvas)

    scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
    canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)

    canvas.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")
    theme.enable_mousewheel(canvas)

    # Organize tests into categories
    test_categories = {
        "Sensor Range Tests": [
            'temperature sensor range',
            'salinity sensor range',
            'conductivity sensor range',
            'pressure sensor range',
            'dissolved oxygen sensor range',
            'pH sensor range',
            'chlorophyll sensor range',
            'turbidity sensor range'
        ],
        "Environmental Range Tests": [
            'temperature environmental range',
            'salinity environmental range',
            'conductivity environmental range',
            'pressure environmental range',
            'pH environmental range',
            'chlorophyll environmental range',
            'dissolved oxygen environmental range',
            'dissolved organic matter environmental range',
            'turbidity environmental range'
        ],
        "Spike Tests": [
            'temperature spikes',
            'salinity spikes',
            'conductivity spikes',
            'pressure spikes',
            'pH spikes',
            'chlorophyll spikes',
            'dissolved oxygen spikes',
            'dissolved organic matter spikes',
            'turbidity spikes'
        ],
        "Rate of Change Tests": [
            'temperature rate of change',
            'salinity rate of change',
            'conductivity rate of change',
            'pressure rate of change'
        ],
        "Flat Line Tests": [
            'temperature flat line',
            'salinity flat line',
            'conductivity flat line',
            'pressure flat line'
        ],
        "Vertical Gradient & Density Inversion Tests (profiles)": [
            'temperature vertical gradient',
            'salinity vertical gradient',
            'conductivity vertical gradient',
            'density inversion'
        ],
        "Light Tests (HOBO)": [
            'light fouling window'
        ]
    }
    
    row = 0
    for category, tests in test_categories.items():
        lbl = ttk.Label(scrollable_frame, text=category, font=theme.FONT_BOLD)
        lbl.grid(row=row, column=0, sticky='w', pady=(10,5), columnspan=2)
        row += 1
        
        for test in tests:
            var = StringVar(value=CONFIG['tsQualityTests'][test])
            CONFIG['tsQualityTests_vars'][test] = var
            
            cb = ttk.Checkbutton(scrollable_frame, text=test, variable=var,
                               onvalue="ON", offvalue="OFF")
            cb.grid(row=row, column=0, sticky='w', padx=20, pady=2)
            
            # Add tooltip for each test
            ToolTip(cb, TS_QUALITY_TESTS_TOOLTIPS[test])
            
            row += 1

# Parameters tab: variable code -> display name and unit (Min/Max share a row)
_PARAM_NAME = {'temp': 'Temperature', 'sal': 'Salinity', 'cond': 'Conductivity',
               'pres': 'Pressure', 'pH': 'pH', 'chl': 'Chlorophyll',
               'O2': 'Dissolved oxygen', 'org': 'Organic matter', 'tur': 'Turbidity',
               'lux': 'Luminosity'}
_PARAM_UNIT = {'temp': '°C', 'sal': 'PSU', 'cond': 'mS/cm', 'pres': 'dbar', 'pH': '',
               'chl': 'µg/L', 'O2': 'µM', 'org': 'ppb', 'tur': 'FTU', 'lux': 'lux'}
# units for the single-value 'Other Parameters'
_OTHER_UNIT = {'rep_cnt_fail': 'samples', 'rep_cnt_susp': 'samples',
               'dens_inv_tolerance': 'kg/m³', 'hobo_edge_temp_tol': '°C',
               'lux_baseline_days': 'days', 'lux_sustain_days': 'days',
               'lux_cutoff_frac': 'fraction'}

def create_params_tab(parent):
    canvas = Canvas(parent, bg=theme.surface_color(), highlightthickness=0)
    scrollbar = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
    scrollable_frame = ttk.Frame(canvas)

    scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
    canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)

    canvas.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")
    theme.enable_mousewheel(canvas)

    def add_entry(key, r, col):
        ent = ttk.Entry(scrollable_frame, width=10)
        ent.insert(0, str(CONFIG['tsSettings'][key]))
        ent.grid(row=r, column=col, sticky='w', padx=5, pady=2)
        ToolTip(ent, TS_SETTINGS_TOOLTIPS[key])
        CONFIG['tsSettings_entries'][key] = ent

    row = 0
    # Range categories: one row per variable, with Min and Max side by side
    for prefix, title in (('sensor', 'Sensor Range'), ('env', 'Environmental Range')):
        ttk.Label(scrollable_frame, text=title, font=theme.FONT_BOLD).grid(
            row=row, column=0, sticky='w', pady=(10, 3), columnspan=4)
        row += 1
        ttk.Label(scrollable_frame, text='Min', font=theme.FONT_SMALL_BOLD).grid(row=row, column=1, sticky='w', padx=5)
        ttk.Label(scrollable_frame, text='Max', font=theme.FONT_SMALL_BOLD).grid(row=row, column=2, sticky='w', padx=5)
        row += 1
        # variables in order of first appearance for this prefix
        variables = []
        for k in CONFIG['tsSettings']:
            if k.startswith(prefix + '_min_'):
                var = k[len(prefix + '_min_'):]
                if var not in variables:
                    variables.append(var)
        for var in variables:
            ttk.Label(scrollable_frame, text=_PARAM_NAME.get(var, var) + ':').grid(
                row=row, column=0, sticky='e', padx=5, pady=2)
            add_entry('%s_min_%s' % (prefix, var), row, 1)
            max_key = '%s_max_%s' % (prefix, var)
            if max_key in CONFIG['tsSettings']:
                add_entry(max_key, row, 2)
            unit = _PARAM_UNIT.get(var, '')
            if unit:
                ttk.Label(scrollable_frame, text=unit).grid(row=row, column=3, sticky='w', padx=5)
            row += 1

    # Other parameters: a single value each
    ttk.Label(scrollable_frame, text='Other Parameters', font=theme.FONT_BOLD).grid(
        row=row, column=0, sticky='w', pady=(10, 3), columnspan=4)
    row += 1
    for key in CONFIG['tsSettings']:
        if 'sensor_' in key or 'env_' in key:
            continue
        ttk.Label(scrollable_frame, text=key.replace('_', ' ').title() + ':').grid(
            row=row, column=0, sticky='e', padx=5, pady=2)
        add_entry(key, row, 1)
        unit = _OTHER_UNIT.get(key, '')
        if unit:
            ttk.Label(scrollable_frame, text=unit).grid(row=row, column=2, sticky='w', padx=5)
        row += 1

def create_factors_tab(parent):
    canvas = Canvas(parent, bg=theme.surface_color(), highlightthickness=0)
    scrollbar = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
    scrollable_frame = ttk.Frame(canvas)

    scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
    canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)

    canvas.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")
    theme.enable_mousewheel(canvas)

    ttk.Label(scrollable_frame, text="Spike / Rate of change / Vertical gradient thresholds",
              font=theme.FONT_BOLD).grid(row=0, column=0, columnspan=4, sticky='w', pady=(10, 5), padx=5)

    # header row
    for col, title in enumerate(["Variable", "Fail factor", "Susp factor", "Time window"]):
        ttk.Label(scrollable_frame, text=title, font=theme.FONT_SMALL_BOLD).grid(
            row=1, column=col, sticky='w', padx=5, pady=2)

    CONFIG['tsFactors_entries'] = {}
    for i, (key, display) in enumerate(FACTOR_VARS):
        r = i + 2
        ttk.Label(scrollable_frame, text=display).grid(row=r, column=0, sticky='w', padx=5, pady=2)
        cfg = CONFIG['tsFactors'][key]
        fail_e = ttk.Entry(scrollable_frame, width=8); fail_e.insert(0, str(cfg['fail']))
        fail_e.grid(row=r, column=1, sticky='w', padx=5, pady=2)
        susp_e = ttk.Entry(scrollable_frame, width=8); susp_e.insert(0, str(cfg['susp']))
        susp_e.grid(row=r, column=2, sticky='w', padx=5, pady=2)
        win_e = ttk.Entry(scrollable_frame, width=10); win_e.insert(0, str(cfg['window']))
        win_e.grid(row=r, column=3, sticky='w', padx=5, pady=2)
        ToolTip(fail_e, TS_FACTORS_TOOLTIPS['fail'])
        ToolTip(susp_e, TS_FACTORS_TOOLTIPS['susp'])
        ToolTip(win_e, TS_FACTORS_TOOLTIPS['window'])
        CONFIG['tsFactors_entries'][key] = {'fail': fail_e, 'susp': susp_e, 'window': win_e}

def save_settings(window):
    invalid = save_settings_values()
    if invalid:
        # keeps the window open so the user can fix the rejected fields
        messagebox.showwarning("Invalid values",
                               "These fields are not valid and kept their previous value:\n\n- "
                               + "\n- ".join(invalid)
                               + "\n\nFix them and click Save Settings again.")
        return
    # Persist the quality criteria to disk right away. Before, "Save Settings"
    # only updated the in-memory CONFIG and the values were written to
    # qcs_user_settings.json only on a RUN. Version-stamped so the load-time
    # version gate still applies; a fresh machine (no json) still gets the code
    # defaults, and "Reset to Defaults" keeps working.
    USER_PREFS.update({
        'qcs_version': data.QCS_VERSION,
        'tsQualityTests': dict(CONFIG['tsQualityTests']),
        'tsSettings': dict(CONFIG['tsSettings']),
        'tsFactors': {k: dict(v) for k, v in CONFIG['tsFactors'].items()},
    })
    save_user_prefs()
    messagebox.showinfo("Success", "Success saving settings!")
    window.destroy()

def reset_settings_to_defaults():
    """Restores the code's default quality criteria in the Settings window."""
    if not messagebox.askyesno("Reset to defaults",
                               "Replace ALL quality tests, parameters and factors\n"
                               "with the software defaults?"):
        return
    CONFIG['tsQualityTests'].update(DEFAULT_QUALITY_CONFIG['tsQualityTests'])
    CONFIG['tsSettings'].update(DEFAULT_QUALITY_CONFIG['tsSettings'])
    for k, v in DEFAULT_QUALITY_CONFIG['tsFactors'].items():
        CONFIG['tsFactors'][k].update(v)
    # reflect the defaults in the open widgets
    for test, var in CONFIG['tsQualityTests_vars'].items():
        var.set(CONFIG['tsQualityTests'][test])
    for param, entry in CONFIG['tsSettings_entries'].items():
        entry.delete(0, END)
        entry.insert(0, str(CONFIG['tsSettings'][param]))
    for key, entries in CONFIG['tsFactors_entries'].items():
        for field in ('fail', 'susp', 'window'):
            entries[field].delete(0, END)
            entries[field].insert(0, str(CONFIG['tsFactors'][key][field]))

# Main application
INPUT = {}
OUTPUT = {}
rootPath = os.getcwd()

# Manual point-cut: map each reviewable column to its flag key, so a manual
# dismissal can be written as flag 5 at that variable's positions (traceable).
# Only variables that HAVE a QC flag column are offered (a cut must be flaggable).
MANUAL_CUT_COLUMNS = [
    ('Temperature (degC)', 'T'), ('Salinity (PSU)', 'S'),
    ('Conductivity (mS/cm)', 'C'), ('Pressure (dbar)', 'P'),
    ('O2 level (uM)', 'O2'), ('pH', 'pH'), ('Chlorophyll (ug/L)', 'chl'),
    ('Turbidity (FTU)', 'tur'), ('Dissolved organic matter (ppb)', 'org'),
]

def choose_variables_to_check(candidates, root):
    """Modal list to pick WHICH variables to review in the manual point-cut
    panels (instead of stepping through all of them). Returns the chosen column
    names, or [] if the user cancels. 'All'/'None' toggle every checkbox."""
    win = Toplevel(root)
    win.title("Check Variables - choose which to review")
    win.transient(root)
    theme.set_scaled_geometry(win, 380, 420, min_width=320, min_height=300)
    frame = ttk.Frame(win, padding=14)
    frame.pack(fill='both', expand=True)
    ttk.Label(frame, text="Select the variables to review and cut manually:",
              style='Header.TLabel').pack(anchor='w', pady=(0, 8))
    vars_map = {}
    box = ttk.Frame(frame)
    box.pack(fill='both', expand=True)
    for name in candidates:
        v = BooleanVar(value=True)
        ttk.Checkbutton(box, text=name, variable=v).pack(anchor='w', pady=1)
        vars_map[name] = v

    btns = ttk.Frame(frame)
    btns.pack(fill='x', pady=(10, 0))
    ttk.Button(btns, text="All variables",
               command=lambda: [v.set(True) for v in vars_map.values()]).pack(side='left')
    ttk.Button(btns, text="None",
               command=lambda: [v.set(False) for v in vars_map.values()]).pack(side='left', padx=6)

    result = {'chosen': []}
    def confirm():
        result['chosen'] = [n for n, v in vars_map.items() if v.get()]
        win.destroy()
    action = ttk.Frame(frame)
    action.pack(fill='x', pady=(12, 0))
    ttk.Button(action, text="Cancel", command=win.destroy).pack(side='right')
    ttk.Button(action, text="Review selected", command=confirm,
               style='Accent.TButton').pack(side='right', padx=6)
    win.grab_set()
    root.wait_window(win)
    return result['chosen']


# --- Collection regions (module-level constants; used by the qualification UI) ---
# Macroregions -> regions -> representative (lat, lon), used only to RUN the
# qualification (pressure->depth conversion and density inversion).
# Small lat/long variations do not meaningfully affect these calculations,
# so one value per region is enough. Structured by macroregion to accommodate
# other parts of the world in the future. Freely editable.
REGIONS = {
    'Brazil': [
        ('Amazonian Reefs / North (AP-MA)',  -1.0, -46.0),
        ('Northeast - northern (CE-RN)',      -4.5, -37.5),
        ('Northeast - eastern (PB-AL)',       -8.5, -35.0),
        ('East / Abrolhos (BA-ES)',          -17.5, -39.0),
        ('Southeast (RJ-SP)',                -23.5, -43.0),
        ('South (PR-RS)',                    -30.0, -49.0),
    ],
}
# {macroregion: {region_label: (lat, lon)}}
REGION_COORDS = {macro: {label: (lat, lon) for label, lat, lon in regions}
                 for macro, regions in REGIONS.items()}
DEFAULT_MACROREGION = 'Brazil'
DEFAULT_REGION = 'East / Abrolhos (BA-ES)'

def build_qualification_tab(container, root, shared_log=None):
    """Builds the Data Qualification UI inside `container` (a frame in the
    unified app's notebook). `root` is the shared Tk root used for dialogs,
    the watch cursor and modal reviews. `shared_log` is the app-wide Execution
    log owned by the QCS_App shell (one log, fixed at the bottom, for every
    pipeline stage); without it (standalone dev launch) the tab creates its
    own. All pipeline logic is unchanged."""
    global window, main_frame, input_frame, output_frame, fileNames_entry, browse_file_btn
    global inputType_combobox, dType_combobox, replicate_label, replicate_combobox, update_profile_checkbox_state, units_frame
    global pressure_unit_combobox, conductivity_unit_combobox, options_frame, correct_gmt3h, gmt_check, select_profile_data
    global profile_check, check_variables, var_check, outputPath_entry, browse_output_btn, outputName_entry
    global outputFilesFormat_combobox, filter_frame, remove_bad, bad_check, remove_suspect, suspect_check
    global siteSelect_entry, macroregion_label, macroregion_combobox, region_label, region_combobox, update_regions
    global _last_seaguard, update_inputtype_state, action_frame, settings_btn, run_button
    global log_console, log_line, status_var, status_label, _error_location, review_light_window
    global run_full_qualification
    window = root
    # Main container
    main_frame = ttk.Frame(container, padding="16")
    main_frame.pack(fill='both', expand=True)


    # Input settings frame
    input_frame = ttk.LabelFrame(main_frame, text=" Input settings ", padding=12)
    input_frame.grid(row=1, column=0, padx=5, pady=5, sticky="nsew")

    # Output settings frame
    output_frame = ttk.LabelFrame(main_frame, text=" Output settings ", padding=12)
    output_frame.grid(row=1, column=1, padx=5, pady=5, sticky="nsew")

    # Configure grid weights
    main_frame.columnconfigure(0, weight=1)
    main_frame.columnconfigure(1, weight=1)
    main_frame.rowconfigure(1, weight=1)
    # entries stretch, Browse buttons keep their natural width
    input_frame.columnconfigure(0, weight=1)
    output_frame.columnconfigure(0, weight=1)


    # --- Input Section ---
    # File selection
    ttk.Label(input_frame, text="Data File:", style='Header.TLabel').grid(row=0, column=0, sticky='w', pady=(0,2))
    fileNames_entry = ttk.Entry(input_frame, width=24)
    fileNames_entry.grid(row=1, column=0, columnspan=2, sticky='ew', pady=(0,5))
    ToolTip(fileNames_entry, TOOLTIPS['data_file'])

    browse_file_btn = ttk.Button(input_frame, text="Browse...", command=selectFiles, width=10)
    browse_file_btn.grid(row=1, column=2, padx=(5,0))
    ToolTip(browse_file_btn, TOOLTIPS['data_file'])

    # Data type selection: Input Type -> Data Type -> Replicates side by side,
    # left-aligned in a compact sub-row (independent of the stretchy columns above)
    type_row = ttk.Frame(input_frame)
    type_row.grid(row=2, column=0, columnspan=3, sticky='w', pady=(0, 5))

    ttk.Label(type_row, text="Input Type:", style='Header.TLabel').grid(row=0, column=0, sticky='w', pady=(0,2))
    inputType_combobox = ttk.Combobox(type_row, values=["Seaguard", "HOBO"], width=15, state='readonly')
    inputType_combobox.grid(row=1, column=0, sticky='w')
    ToolTip(inputType_combobox, TOOLTIPS['input_type'])

    ttk.Label(type_row, text="Data Type:", style='Header.TLabel').grid(row=0, column=1, sticky='w', padx=(12, 0), pady=(0,2))
    dType_combobox = ttk.Combobox(type_row, values=["TSCP Profile", "TSCP Mooring"], width=15, state='readonly')
    dType_combobox.grid(row=1, column=1, sticky='w', padx=(12, 0))
    ToolTip(dType_combobox, TOOLTIPS['data_type'])

    # Replicates (HOBO only): how many redundant HOBO spreadsheets to qualify and
    # combine into one series (temperature mean + spread, light max-of-clean).
    replicate_label = ttk.Label(type_row, text="Replicates:", style='Header.TLabel')
    replicate_label.grid(row=0, column=2, sticky='w', padx=(12, 0), pady=(0, 2))
    replicate_combobox = ttk.Combobox(type_row, values=["1", "2", "3", "4"], width=4, state='disabled')
    replicate_combobox.set("1")
    replicate_combobox.grid(row=1, column=2, sticky='w', padx=(12, 0))
    ToolTip(replicate_combobox,
            "HOBO only: number of redundant HOBO files (2-4) to qualify together and\n"
            "combine into one series. Select all N files at once with 'Browse'.")
    # re-derive the Output File Name when the replicate count changes (single vs combined)
    replicate_combobox.bind("<<ComboboxSelected>>", lambda e: apply_output_name())

    # update profile checkbox
    def update_profile_checkbox_state(event=None):
        if dType_combobox.get() == "TSCP Profile":
            profile_check.config(state="normal")
        else:
            profile_check.config(state="disabled")
            select_profile_data.set(False)  # Unchecks the checkbox if it is not a profile

    # bind to combobox selection
    dType_combobox.bind("<<ComboboxSelected>>", update_profile_checkbox_state)

    # Units selection
    units_frame = ttk.LabelFrame(input_frame, text=" Units ", padding=5)
    units_frame.grid(row=4, column=0, columnspan=2, sticky='ew', pady=5)

    ttk.Label(units_frame, text="Pressure:").grid(row=0, column=0, sticky='w')
    pressure_unit_combobox = ttk.Combobox(units_frame, values=["decibar", "bar", "kPa"], width=10, state='readonly')
    pressure_unit_combobox.set('kPa')  # default input unit (auto-converted to decibar internally)
    pressure_unit_combobox.grid(row=0, column=1, padx=5, pady=2)
    ToolTip(pressure_unit_combobox, TOOLTIPS['pressure_unit'])

    ttk.Label(units_frame, text="Conductivity:").grid(row=1, column=0, sticky='w')
    conductivity_unit_combobox = ttk.Combobox(units_frame, values=["mS/cm", "S/m"], width=10, state='readonly')
    conductivity_unit_combobox.grid(row=1, column=1, padx=5, pady=2)
    ToolTip(conductivity_unit_combobox, TOOLTIPS['conductivity_unit'])

    # Options checkboxes
    options_frame = ttk.Frame(input_frame)
    options_frame.grid(row=5, column=0, columnspan=2, sticky='ew', pady=5)

    correct_gmt3h = BooleanVar(value=False)
    gmt_check = ttk.Checkbutton(options_frame, text="Correct GMT-3", variable=correct_gmt3h)
    gmt_check.pack(anchor='w', pady=2)
    ToolTip(gmt_check, TOOLTIPS['gmt_correction'])

    select_profile_data = BooleanVar(value=False)
    profile_check = ttk.Checkbutton(options_frame, text="Select Profile Data", variable=select_profile_data)
    profile_check.pack(anchor='w', pady=2)
    profile_check.config(state="disabled")  # Starts disabled
    ToolTip(profile_check, TOOLTIPS['profile_selection'])

    check_variables = BooleanVar(value=False)
    var_check = ttk.Checkbutton(options_frame, text="Check Variables (manual point cut)", variable=check_variables)
    var_check.pack(anchor='w', pady=2)
    ToolTip(var_check, TOOLTIPS['variable_check'])

    # --- Output Section ---
    # Output folder
    ttk.Label(output_frame, text="Output Folder:", style='Header.TLabel').grid(row=0, column=0, sticky='w', pady=(0,2))
    outputPath_entry = ttk.Entry(output_frame, width=24)
    outputPath_entry.grid(row=1, column=0, sticky='ew', pady=(0,5))
    ToolTip(outputPath_entry, TOOLTIPS['output_folder'])

    browse_output_btn = ttk.Button(output_frame, text="Browse...", command=selectOutputFolder, width=10)
    browse_output_btn.grid(row=1, column=1, padx=5)
    ToolTip(browse_output_btn, TOOLTIPS['output_folder'])

    # File naming
    ttk.Label(output_frame, text="Output File Name:", style='Header.TLabel').grid(row=2, column=0, sticky='w', pady=(0,2))
    outputName_entry = ttk.Entry(output_frame, width=24)
    outputName_entry.grid(row=3, column=0, columnspan=2, sticky='ew', pady=(0,5))
    ToolTip(outputName_entry, TOOLTIPS['output_name'])

    # Output format
    ttk.Label(output_frame, text="Output Format:", style='Header.TLabel').grid(row=4, column=0, sticky='w', pady=(0,2))
    outputFilesFormat_combobox = ttk.Combobox(output_frame, values=[".csv", ".xlsx"], width=8, state='readonly')
    outputFilesFormat_combobox.grid(row=5, column=0, sticky='w', pady=(0,5))
    ToolTip(outputFilesFormat_combobox, TOOLTIPS['output_format'])

    # Data filtering
    filter_frame = ttk.LabelFrame(output_frame, text=" Data Filtering ", padding=5)
    filter_frame.grid(row=6, column=0, columnspan=2, sticky='ew', pady=5)

    remove_bad = BooleanVar(value=False)
    bad_check = ttk.Checkbutton(filter_frame, text="Remove Bad Data", variable=remove_bad)
    bad_check.pack(anchor='w', pady=2)
    ToolTip(bad_check, TOOLTIPS['remove_bad'])

    remove_suspect = BooleanVar(value=False)
    suspect_check = ttk.Checkbutton(filter_frame, text="Remove Suspect Data", variable=remove_suspect)
    suspect_check.pack(anchor='w', pady=2)
    ToolTip(suspect_check, TOOLTIPS['remove_suspect'])

    # Site selection
    ttk.Label(output_frame, text="Site Code:", style='Header.TLabel').grid(row=7, column=0, sticky='w', pady=(5,2))
    siteSelect_entry = ttk.Entry(output_frame, width=12)
    siteSelect_entry.grid(row=8, column=0, sticky='w', pady=(0,5))
    ToolTip(siteSelect_entry, TOOLTIPS['site_code'])

    # Macroregion + region of collection: provide a representative latitude/longitude
    # used only to RUN the qualification (pressure->depth and density inversion). More
    # intuitive than typing coordinates and enough given the low sensitivity to small
    # lat/long changes. The macroregion box is structured to add other parts of the
    # world in the future. Both are disabled for HOBO (no pressure).
    macroregion_label = ttk.Label(input_frame, text="Macroregion:", style='Header.TLabel')
    macroregion_label.grid(row=6, column=0, columnspan=2, sticky='w', pady=(5,2))
    macroregion_combobox = ttk.Combobox(input_frame, values=list(REGIONS.keys()),
                                        width=20, state='readonly')
    macroregion_combobox.grid(row=7, column=0, columnspan=2, sticky='w', pady=(0,5))
    macroregion_combobox.set(DEFAULT_MACROREGION)
    ToolTip(macroregion_combobox, TOOLTIPS['macroregion'])

    region_label = ttk.Label(input_frame, text="Region:", style='Header.TLabel')
    region_label.grid(row=8, column=0, columnspan=2, sticky='w', pady=(5,2))
    region_combobox = ttk.Combobox(input_frame, values=[r[0] for r in REGIONS[DEFAULT_MACROREGION]],
                                   width=32, state='readonly')
    region_combobox.grid(row=9, column=0, columnspan=2, sticky='w', pady=(0,5))
    region_combobox.set(DEFAULT_REGION)
    ToolTip(region_combobox, TOOLTIPS['region'])

    def update_regions(event=None):
        """Repopulates the regions according to the chosen macroregion (keeps the current
        selection if it still exists; otherwise falls back to the macroregion's first region)."""
        macro = macroregion_combobox.get()
        regions = [r[0] for r in REGIONS.get(macro, [])]
        region_combobox.config(values=regions)
        if region_combobox.get() not in regions:
            region_combobox.set(regions[0] if regions else '')

    macroregion_combobox.bind("<<ComboboxSelected>>", update_regions)

    # stores the last Seaguard selection of Data Type/Units, to restore when coming back
    # from HOBO (which empties those fields because they do not apply to a temp/light logger)
    _last_seaguard = {}

    def update_inputtype_state(event=None):
        """HOBO only measures temperature and light: Data Type, units (pressure/conductivity),
        GMT-3 correction, profile selection and the region (macro + region) do not apply and
        stay disabled and empty. Data Type and the units keep the last Seaguard selection
        and restore it when coming back. HOBO is a time series (treated as non-profile)."""
        if inputType_combobox.get() == 'HOBO':
            # store the non-empty values before clearing
            if dType_combobox.get():
                _last_seaguard['data_type'] = dType_combobox.get()
            if pressure_unit_combobox.get():
                _last_seaguard['pressure'] = pressure_unit_combobox.get()
            if conductivity_unit_combobox.get():
                _last_seaguard['conductivity'] = conductivity_unit_combobox.get()
            dType_combobox.set('')            # HOBO is neither TSCP profile nor mooring
            pressure_unit_combobox.set('')    # no pressure
            conductivity_unit_combobox.set('')
            dType_combobox.config(state='disabled')
            pressure_unit_combobox.config(state='disabled')
            conductivity_unit_combobox.config(state='disabled')
            gmt_check.config(state='disabled')
            select_profile_data.set(False)
            profile_check.config(state='disabled')
            macroregion_label.config(state='disabled')
            macroregion_combobox.config(state='disabled')
            region_label.config(state='disabled')
            region_combobox.config(state='disabled')
            if not replicate_combobox.get():               # restore a usable value when returning from Seaguard
                replicate_combobox.set('1')
            replicate_combobox.config(state='readonly')    # replicates apply to HOBO
        else:
            # restore the last stored Seaguard selection (if any)
            if _last_seaguard.get('data_type'):
                dType_combobox.set(_last_seaguard['data_type'])
            if _last_seaguard.get('pressure'):
                pressure_unit_combobox.set(_last_seaguard['pressure'])
            if _last_seaguard.get('conductivity'):
                conductivity_unit_combobox.set(_last_seaguard['conductivity'])
            dType_combobox.config(state='readonly')
            pressure_unit_combobox.config(state='readonly')
            conductivity_unit_combobox.config(state='readonly')
            gmt_check.config(state='normal')
            macroregion_label.config(state='normal')
            macroregion_combobox.config(state='readonly')
            region_label.config(state='normal')
            region_combobox.config(state='readonly')
            replicate_combobox.set('')                     # replicates are HOBO-only: leave empty for Seaguard
            replicate_combobox.config(state='disabled')
            update_profile_checkbox_state()
        apply_output_name()  # keep the Output File Name in sync (single vs combined)

    inputType_combobox.bind("<<ComboboxSelected>>", update_inputtype_state)
    update_inputtype_state()

    # Action buttons
    action_frame = ttk.Frame(main_frame)
    action_frame.grid(row=2, column=0, columnspan=2, pady=(14, 4))

    # (the Help button moved to the app's Help menu in v4.1)
    settings_btn = ttk.Button(action_frame, text="Settings", command=open_settings_window, width=12)
    settings_btn.pack(side='left', padx=5)
    ToolTip(settings_btn, TOOLTIPS['settings_button'])

    run_button = ttk.Button(action_frame, text="Run Qualification", command=start_qualification, style='Accent.TButton')
    run_button.pack(side='left', padx=5, ipadx=20, ipady=2)
    ToolTip(run_button, TOOLTIPS['run_button'])

    # Execution log: progress, warnings and the per-test summary during RUN.
    # In the unified app the log is ONE shell-owned panel fixed at the bottom of
    # the window (consistent position/styling across all pipeline stages);
    # standalone dev launches create their own.
    if shared_log is not None:
        log_console = shared_log
    else:
        log_console = theme.LogConsole(main_frame, title=" Execution log ", height=6)
        log_console.frame.grid(row=3, column=0, columnspan=2, sticky='nsew', padx=5, pady=(4, 0))
        # from here on, everything printed (including buffered startup messages)
        # shows in this panel instead of a terminal
        _out.set_sink(log_console.log)

    def log_line(message):
        """Prints the message (redirected to the log panel) and redraws, so progress
        appears even with the pipeline running on the interface thread."""
        print(message)
        try:
            window.update_idletasks()
        except Exception:
            pass

    # Status bar
    status_var = StringVar(value="Ready")
    status_label = ttk.Label(main_frame, textvariable=status_var, style='Small.TLabel', anchor='w')
    status_label.grid(row=4, column=0, columnspan=2, sticky='ew', padx=5, pady=(6, 0))

    def _error_location(exc):
        """Points to the deepest QCS file/line in the traceback: direct debugging."""
        frames = traceback.extract_tb(exc.__traceback__)
        qcs_frames = [f for f in frames if os.path.basename(f.filename).startswith('QCS_')]
        f = (qcs_frames or frames)[-1]
        return '%s, line %d, in %s()' % (os.path.basename(f.filename), f.lineno, f.name)

    def review_light_window(lux_info, site):
        """Interactive review of the light usage window (HOBO): clicking the plot
        sets the cutoff (date and time), key 'n' removes the cutoff, the 'Suggested
        cutoff' button (or key 'r') restores the software's proposal, Enter/close
        confirms. Returns the final cutoff (Timestamp or None)."""
        import matplotlib.dates as mdates
        from matplotlib.widgets import Button
        fig, ax = view.plot_light_window(lux_info, site)
        ax.set_title(ax.get_title() +
                     '\nClick = move cutoff  |  buttons below (or keys R / S / Enter)  |  Help explains it')
        fig.subplots_adjust(bottom=0.30)  # room for the button row above the rule text
        state = {'cutoff': lux_info['proposed_cutoff'], 'artists': []}

        def redraw():
            for artist in state['artists']:
                try:
                    artist.remove()
                except Exception:
                    pass
            state['artists'] = view.mark_light_cutoff(ax, state['cutoff'], lux_info)
            fig.canvas.draw_idle()

        def reset_to_suggested(*_event):
            state['cutoff'] = lux_info['proposed_cutoff']
            redraw()

        def remove_cutoff(*_event):
            state['cutoff'] = None
            redraw()

        def show_review_help(*_event):
            p = lux_info['params']
            messagebox.showinfo(
                "Light window - help",
                "LIGHT USABLE WINDOW (HOBO fouling review)\n\n"
                "Controls:\n"
                "  - Click on the plot: set the cutoff at that date/time\n"
                "  - 'Suggested cutoff' (key S): restore the software's proposal\n"
                "  - 'Remove cutoff' (key R): no cutoff (light usable all deployment)\n"
                "  - Enter, or close the window: confirm the current cutoff\n\n"
                "Method:\n"
                "  - Baseline = highest daily light peak of the first %d day(s)\n"
                "    (the unfouled sensor's clean-state light).\n"
                "  - Fouling threshold = %.0f%% of the baseline.\n"
                "  - Proposed cutoff = start of the FINAL run of >= %d day(s) where the\n"
                "    daily peak stays below the threshold and never recovers to it;\n"
                "    light that recovers above the threshold is kept.\n"
                "  - From the cutoff on, light is flagged BAD (Flag_lux = 4, unusable);\n"
                "    the values stay in the sheet until removed with 'Remove Bad Data'.\n\n"
                "Parameters (lux_baseline_days / lux_cutoff_frac / lux_sustain_days) live in\n"
                "Settings > Parameters, and are printed on the saved QCS_light_window.svg."
                % (p['baseline_days'], 100 * p['cutoff_frac'], p['sustain_days']),
                parent=window)

        def on_click(event):
            # clicks on the reset button (a different axes) must not move the cutoff;
            # keep the FULL clicked timestamp (date and time), not just the date
            if event.inaxes is ax and event.xdata is not None:
                state['cutoff'] = pd.Timestamp(mdates.num2date(event.xdata).replace(tzinfo=None))
                redraw()

        def on_key(event):
            if event.key in ('r', 'R', 'n', 'N'):   # R (or N) = remove the cutoff
                remove_cutoff()
            elif event.key in ('s', 'S'):            # S = restore the suggested cutoff
                reset_to_suggested()
            elif event.key == 'enter':
                plt.close(fig)

        # button row (kept referenced so matplotlib does not garbage-collect them)
        reset_btn = Button(fig.add_axes([0.30, 0.175, 0.19, 0.055]), 'Suggested cutoff')
        remove_btn = Button(fig.add_axes([0.51, 0.175, 0.17, 0.055]), 'Remove cutoff')
        help_btn = Button(fig.add_axes([0.70, 0.175, 0.11, 0.055]), 'Help')
        reset_btn.on_clicked(reset_to_suggested)
        remove_btn.on_clicked(remove_cutoff)
        help_btn.on_clicked(show_review_help)
        state['buttons'] = (reset_btn, remove_btn, help_btn)

        fig.canvas.mpl_connect('button_press_event', on_click)
        fig.canvas.mpl_connect('key_press_event', on_key)
        redraw()
        # waits on the Tk loop (never plt.show(block=True) inside the RUN callback)
        done = BooleanVar(window, value=False)
        fig.canvas.mpl_connect('close_event', lambda event: done.set(True))
        fig.show()
        window.wait_variable(done)
        return state['cutoff']

    # The whole qualification pipeline runs inside this function so the main
    # window stays open and the user can qualify several files in sequence.
    def run_full_qualification():
        tsSettings = CONFIG['tsSettings']
        tsQualityTests = CONFIG['tsQualityTests']
        tsFactors = CONFIG['tsFactors']

        # change to folder containing raw data
        os.chdir(INPUT['raw_data_path'])
        log_line('Stage 1/5: reading input file (%s)...' % INPUT['input_type'])
        for message in INPUT.get('coord_msgs', []):
            log_line('MESSAGE: %s' % message)

        # opening raw files according to selected data type
        if INPUT['input_type'] == 'Seaguard':
            if INPUT['profile'] == True:
                raw_data = data.read_ctd(INPUT)
            else:
                raw_data = data.read_ctd(INPUT)
            for name in raw_data.columns:
                if re.search('time', name, re.IGNORECASE):
                    if re.search('timer', name, re.IGNORECASE):
                        pass
                    else:
                        raw_data = raw_data.rename(columns={name:'Datetime'})
                if re.search('prof', name, re.IGNORECASE):
                        raw_data = raw_data.rename(columns={name:'Depth (m)'})
        elif INPUT['input_type'] == 'HOBO':
            raw_data, hobo_info = data.read_hobo(INPUT, tsSettings)
            for message in hobo_info['messages']:
                log_line(message)
        # getting start and end time and measurement interval
        start_time = raw_data['Datetime'].iloc[0]
        end_time = raw_data['Datetime'].iloc[-1]
        # median interval in microseconds: keeps sub-second precision (some sensors log at 8 Hz)
        # and is robust to occasional gaps between records
        ms_interval = np.timedelta64(raw_data['Datetime'].diff().median(), 'us')
        if ms_interval <= np.timedelta64(0, 'us'):
            raise ValueError('Could not determine the sampling interval from the Datetime column.')
        INPUT['start_time'] = start_time
        INPUT['end_time'] = end_time

        # timestamp sanity checks (gap/monotonicity): reported, not flagged per sample
        dt_diff = raw_data['Datetime'].diff()
        ts_backwards = int((dt_diff < pd.Timedelta(0)).sum())
        ts_duplicates = int(raw_data['Datetime'].duplicated().sum())
        median_interval = pd.Timedelta(ms_interval.item())
        gap_mask = dt_diff > 3 * median_interval
        ts_gaps = int(gap_mask.sum())
        ts_max_gap = str(dt_diff.max()) if ts_gaps else ''
        if ts_backwards:
            log_line("WARNING: %d timestamp(s) go BACKWARDS in time - check the raw file "
                     "or use 'Sort by Time' before interpreting time-based tests." % ts_backwards)
        if ts_duplicates:
            log_line("WARNING: %d duplicated timestamp(s) found in the raw file." % ts_duplicates)
        if ts_gaps:
            log_line("MESSAGE: %d sampling gap(s) longer than 3x the median interval "
                     "(largest: %s)." % (ts_gaps, ts_max_gap))

        log_line('Stage 2/5: preprocessing (units, depth, non-physical values)...')
        # adjusting for GMT-3 hours
        if INPUT['correct_gmt3h'] == True:
            raw_data['Datetime'] = raw_data['Datetime'] - timedelta(hours=3)
            start_time = start_time - timedelta(hours=3)
            end_time = end_time - timedelta(hours=3)

        # excluding other than main temperature sensors
        for name in raw_data.keys():
            if re.search('internal temperature', name, re.IGNORECASE):
                raw_data = raw_data.drop(columns={name})
            elif re.search(r'(?i)\btemperature\b.*\d', name, re.IGNORECASE):
                raw_data = raw_data.drop(columns={name})
        # converting units to software standards and calculating depth from pressure
        check = list()
        for var in raw_data.columns:
            if re.search('conductivity|pressure', var, re.IGNORECASE):
                check.append(var)
        if len(check) >= 1:
            raw_data = data.convert_tscp_units (raw_data, pressure_unit=INPUT['pressure_unit'], conductivity_unit=INPUT['conductivity_unit'])
            for name in raw_data.columns:
                if re.search('pressure', name, re.IGNORECASE):
                    raw_data = raw_data.rename(columns={name:'Pressure (dbar)'})

        dep, press = (0,0)
        for name in raw_data.columns:
            if re.search('depth', name, re.IGNORECASE) and not re.search('pressure', name, re.IGNORECASE):
                dep += 1
            elif re.search('pressure', name, re.IGNORECASE):
                press += 1
        if dep == 0 and press == 1:
            raw_data = data.pressure_to_depth(raw_data, latitude=INPUT.get('latitude', 17.5), adjust_for_atm=True)

        # add Sample number column
        raw_data['Sample number'] = raw_data.index + 1

        # handle non-physical values <= 0 (optical sensors keep small negatives as ~0);
        # every changed value is counted and reported, never dropped silently
        raw_data, zero_report = data.clean_below_zero(raw_data, tsSettings)
        for col, counts in zero_report.items():
            if counts['clamped']:
                log_line("MESSAGE: %s: %d negative value(s) clamped to 0 (sensor noise around zero)"
                         % (col, counts['clamped']))
            if counts['discarded']:
                log_line("WARNING: %s: %d non-physical value(s) <= 0 discarded (set to missing)"
                         % (col, counts['discarded']))

        #removing data where depth is under 0.5 for profile data
        if INPUT['profile'] == True:
            exceptions = ['Datetime', 'Sample number', 'Pitch[Deg]', 'Roll[Deg]', 'Timer[s]', 'Site']
            for name in raw_data.columns:
                if name not in exceptions:
                    raw_data.loc[raw_data['Depth (m)'] < 0.5, name] = np.nan

        #removing data reproved in depth range test
        #if auxTests['depth range test'] == 'ON':
        #    for name in raw_data.columns:
        #        if re.search('depth', name, re.IGNORECASE):
        #            #first round
        #            raw_data = QC.depth_range_test (raw_data, tsSettings['depth_range'])
        #            #second round
        #            raw_data = QC.depth_range_test (raw_data, tsSettings['depth_range'])

        #selecting samples based on descending or ascendig equipment
        if INPUT['select_profile_data'] == True:
            for name in raw_data.columns:
                if re.search('pressure', name, re.IGNORECASE):
                    try:
                        # Try width=100
                        peaks = signal.find_peaks(raw_data[name], width=100)[0]
                
                        # Try width=50
                        if len(peaks) == 0:
                            peaks = signal.find_peaks(raw_data[name], width=50)[0]
                
                        # exception if no peak found
                        if len(peaks) == 0:
                            raise ValueError("No peak found for the given conditions.")
                        # Select first peak
                        peak = int(peaks[0])

                        fig1 = plt.figure()
                        ax1 = fig1.gca()
                        ax1.plot(raw_data[name], label='Pressure (dbar)')
                        ax1.plot(peak, raw_data[name].loc[peak], '.', c='red', linestyle='none')
                        ax1.set_ylabel('Pressure (dbar)')
                        fig1.show()
                        #plt.show(block=True)
                        ans = []
                        # Peak validation window: child of the main window (a second
                        # Tk() root would conflict with the already running interface)
                        peak_window = Toplevel(window)

                        # ans/fig1/peak_window are passed as default arguments: a callback
                        # defined inside a loop captures the variable by late binding
                        # (it would use the value of the LAST iteration, not this one)
                        def acceptPeak(ans=ans, fig1=fig1, peak_window=peak_window):
                            print('MESSAGE: Peak accepted, proceding to profile selection')
                            ans.append('y')
                            plt.close(fig1)
                            peak_window.destroy()

                        def doNotAcceptPeak(fig1=fig1, peak_window=peak_window):
                            print('MESSAGE: Ignoring data peak, data qualification will continue with the whole dataset')
                            plt.close(fig1)
                            peak_window.destroy()

                        peak_window.title("Peak Validation")
                        theme.set_scaled_geometry(peak_window, 280, 110)
                        peak_window.resizable(False, False)
                        peak_window.configure(bg=theme.surface_color())
                        peak_frame = ttk.Frame(peak_window, padding=12)
                        peak_frame.pack(fill='both', expand=True)
                        ttk.Label(peak_frame, text="Do you accept the data peak?").pack(anchor='w', pady=(0, 8))
                        btn_row = ttk.Frame(peak_frame)
                        btn_row.pack(anchor='e')
                        ttk.Button(btn_row, text="Yes", command=acceptPeak,
                                   style='Accent.TButton', width=8).pack(side='left', padx=(0, 6))
                        ttk.Button(btn_row, text="No", command=doNotAcceptPeak, width=8).pack(side='left')
                        # block here until the user answers Yes or No
                        peak_window.grab_set()
                        window.wait_window(peak_window)

                        if len(ans) > 0 and ans[0] == 'y':
                            for subname in raw_data.columns:
                                if re.search('temperature', subname, re.IGNORECASE):
                                    temp = subname
                                if re.search('depth', subname, re.IGNORECASE):
                                    dep = subname
                            desc = raw_data.loc[:peak]
                            asc = raw_data.loc[peak:]

                            #fig2 = plt.figure()
                            #ax2 = fig2.gca()
                            fig2, ax2 = plt.subplots()
                            line1, = ax2.plot(desc[temp], desc[dep], linestyle='None', marker='o', markersize=3, markerfacecolor='#1f77b4ff', markeredgecolor='#1f77b4ff', label='descending data')
                            line2, = ax2.plot(asc[temp], asc[dep], linestyle='None', marker='o', markersize=3, markerfacecolor='red', markeredgecolor='red', c='red', label='ascending data')
                            ax2.set_title('Click a curve to select it (descending/ascending).\nClose this window to keep the whole dataset.')
                            ax2.set_xlabel('Temperature (degC)')
                            ax2.set_ylabel('Depth (m)')
                            ax2.legend()
                            ax2.invert_yaxis()
                            ax2.grid()

                            selected = None
                            pick_done = BooleanVar(window, value=False)
                            # pick_done as a default argument: same reason as
                            # acceptPeak above (late binding in a loop callback)
                            def on_pick(event, pick_done=pick_done):
                                nonlocal selected
                                selected = event.artist.get_label()
                                pick_done.set(True)
                            def on_close(event, pick_done=pick_done):
                                pick_done.set(True)

                            line1.set_picker(True)
                            line2.set_picker(True)
                            fig2.canvas.mpl_connect('pick_event', on_pick)
                            fig2.canvas.mpl_connect('close_event', on_close)
                            fig2.canvas.mpl_connect('motion_notify_event', data.on_motion)
                            # show non-blocking and wait on the Tk loop. plt.show(block=True)
                            # inside the running Tk app starts a nested loop and freezes the UI.
                            fig2.show()
                            window.wait_variable(pick_done)

                            if selected is None:
                                print('MESSAGE: No dataset selected, keeping the whole dataset')
                            elif selected == 'descending data':
                                raw_data = desc.copy()
                            elif selected == 'ascending data':
                                raw_data = asc.copy()
                            plt.close(fig2)
                            raw_data.index =  np.arange(len(raw_data))
                    except TypeError:
                        print("Could not find turning point")
                        pass


        # Manual point-cut panels record DISMISSALS (flag 5), applied to the flag
        # string + values just before handle_output_file - nothing is deleted here.
        manual_dismiss_rows = set()       # whole-row dismissals (depth review)
        manual_dismiss_cols = {}          # {column_name: set of row positions}

        if INPUT['profile'] == False and 'Depth (m)' in raw_data.columns:
            manual_dismiss_rows |= data.trim_by_depth(raw_data, tk_root=window)

        # number of lines and cells
        n_cel = 1
        n_samples = len(raw_data)

        if INPUT['check_variables'] == True:
            candidates = [name for name, _key in MANUAL_CUT_COLUMNS if name in raw_data.columns]
            for name in choose_variables_to_check(candidates, window):
                rows = data.trim_selected_variable(raw_data, name, tk_root=window)
                if rows:
                    manual_dismiss_cols[name] = rows
        #create list for flag codes
        flags = ['' for n in range(len(raw_data))]

        log_line('Stage 3/5: running quality tests (%d samples)...' % n_samples)
        start = time.time()

        # (pattern, ignore_case) used to locate the column of each parameter;
        # 'pH' must be case sensitive, otherwise it also matches 'Chlorophyll'
        PARAM_PATTERNS = {
            'T':   ('temperature', True),
            'S':   ('salinity', True),
            'C':   ('conductivity', True),
            'P':   ('pressure', True),
            'pH':  ('pH', False),
            'chl': (r'chlorophyll \(ug/L\)', True),
            'O2':  (r'^(?=.*O2)(?=.*uM).*$', True),
            'org': ('organic matter', True),
            'tur': (r'turbidity \(ftu\)', True),
        }

        # all runners take (column, flags, param_key); range/flat ignore param_key,
        # spike/rate/gradient use the per-variable factors from tsFactors[param_key]
        def run_range_test(min_key, max_key, fail_flag=QC.QC_flags.BAD_DATA):
            # sensor range -> BAD (physically impossible); environmental range ->
            # SUSPECT (QARTOD: outside the regional envelope is suspect, not bad)
            return lambda column, flags, param_key: QC.range_test(raw_data[column], flags,
                                                                  range_min=tsSettings[min_key],
                                                                  range_max=tsSettings[max_key],
                                                                  fail_flag=fail_flag)

        def run_spike_test(column, flags, param_key):
            f = tsFactors[param_key]
            return QC.outlier_test(raw_data, column, n_cel, flags, f['window'],
                                   ms_interval, f['fail'], f['susp'])

        def run_rate_of_change_test(column, flags, param_key):
            f = tsFactors[param_key]
            # positions of THIS variable's previous flags: keeps the 'previous value
            # was bad/missing' propagation from being contaminated by other variables
            done = len(flags[0]) if flags else 0
            var_positions = [i for i in range(done) if flag_layout[i] == param_key]
            return QC.sigma_rate_of_change_test(n_samples, raw_data[column], n_cel, flags,
                                                ms_interval=ms_interval, time_window=f['window'],
                                                rc_fail=f['fail'], rc_susp=f['susp'],
                                                DIR=False, var_positions=var_positions)

        def run_flat_line_test(column, flags, param_key):
            return QC.single_flat_line_test(n_samples, n_cel, raw_data[column], flags,
                                            rep_cnt_fail=tsSettings['rep_cnt_fail'],
                                            rep_cnt_suspect=tsSettings['rep_cnt_susp'])

        def run_vertical_gradient_test(column, flags, param_key):
            f = tsFactors[param_key]
            if 'Depth (m)' not in raw_data.columns:
                return [flags[n] + '%d' % QC.QC_flags.UNKNOWN for n in range(n_samples)]
            return QC.vertical_gradient_test(raw_data[column], raw_data['Depth (m)'], flags,
                                             grad_fail=f['fail'], grad_susp=f['susp'])

        qc_report_rows = []  # one row per executed test -> QCS_test_report.xlsx

        def count_last_flags(flags):
            last = [fl[-1] for fl in flags]
            return {c: last.count(c) for c in '123459'}

        def report_test(test_label, param_key, flags, elapsed):
            counts = count_last_flags(flags)
            qc_report_rows.append({
                'Test': test_label, 'Variable': param_key,
                'Good': counts['1'], 'Not evaluated': counts['2'],
                'Suspect': counts['3'], 'Bad': counts['4'],
                'Test off': counts['5'], 'Missing': counts['9'],
                'Time (s)': round(elapsed, 3)})
            if counts['5'] == n_samples:
                log_line('%s: test off' % test_label)
            else:
                log_line('%s: bad %d, suspect %d (%.1f%% flagged) [%.2f s]'
                         % (test_label, counts['4'], counts['3'],
                            100.0 * (counts['4'] + counts['3']) / n_samples, elapsed))

        def apply_quality_test(flags, param_key, test_label, test_switch, test_runner):
            # runs one quality test, appending exactly one flag character per sample;
            # the execution order defines the character position read by data.handle_output_file
            ti = time.time()
            pattern, ignore_case = PARAM_PATTERNS[param_key]
            matched_column = None
            for name in raw_data.columns:
                if re.search(pattern, name, re.IGNORECASE if ignore_case else 0):
                    matched_column = name
                    break
            if matched_column is None:
                flags = [flags[n] + '%d' % QC.QC_flags.UNKNOWN for n in range(n_samples)]
            elif tsQualityTests[test_switch] == 'ON':
                flags = test_runner(matched_column, flags, param_key)
            else:
                flags = [flags[n] + '%d' % QC.QC_flags.DISMISSED for n in range(n_samples)]
            report_test(test_label, param_key, flags, time.time() - ti)
            return flags

        # The param key (1st item) of each test feeds flag_layout below, which maps every
        # flag character to its variable in data.handle_output_file — positions are no
        # longer hardcoded, so the mapping follows whatever order is used here.
        test_sequence = [
            ('T',   'Temperature sensor range',  'temperature sensor range',  run_range_test('sensor_min_temp', 'sensor_max_temp')),
            ('S',   'Salinity sensor range',     'salinity sensor range',     run_range_test('sensor_min_sal', 'sensor_max_sal')),
            ('C',   'Conductivity sensor range', 'conductivity sensor range', run_range_test('sensor_min_cond', 'sensor_max_cond')),
            ('P',   'Pressure sensor range',     'pressure sensor range',     run_range_test('sensor_min_pres', 'sensor_max_pres')),
            ('O2',  'Dissolved oxygen sensor range', 'dissolved oxygen sensor range', run_range_test('sensor_min_O2', 'sensor_max_O2')),
            ('pH',  'pH sensor range',           'pH sensor range',           run_range_test('sensor_min_pH', 'sensor_max_pH')),
            ('chl', 'Chlorophyll sensor range',  'chlorophyll sensor range',  run_range_test('sensor_min_chl', 'sensor_max_chl')),
            ('tur', 'Turbidity sensor range',    'turbidity sensor range',    run_range_test('sensor_min_tur', 'sensor_max_tur')),
            ('T',   'Temperature environmental range',  'temperature environmental range',  run_range_test('env_min_temp', 'env_max_temp', QC.QC_flags.SUSPECT)),
            ('S',   'Salinity environmental range',     'salinity environmental range',     run_range_test('env_min_sal', 'env_max_sal', QC.QC_flags.SUSPECT)),
            ('C',   'Conductivity environmental range', 'conductivity environmental range', run_range_test('env_min_cond', 'env_max_cond', QC.QC_flags.SUSPECT)),
            ('P',   'Pressure environmental range',     'pressure environmental range',     run_range_test('env_min_pres', 'env_max_pres', QC.QC_flags.SUSPECT)),
            ('pH',  'pH environmental range',           'pH environmental range',           run_range_test('env_min_pH', 'env_max_pH', QC.QC_flags.SUSPECT)),
            ('chl', 'Chlorophyll environmental range',  'chlorophyll environmental range',  run_range_test('env_min_chl', 'env_max_chl', QC.QC_flags.SUSPECT)),
            ('O2',  'Dissolved oxygen environmental range', 'dissolved oxygen environmental range', run_range_test('env_min_O2', 'env_max_O2', QC.QC_flags.SUSPECT)),
            ('org', 'Dissolved organic matter environmental range', 'dissolved organic matter environmental range', run_range_test('env_min_org', 'env_max_org', QC.QC_flags.SUSPECT)),
            ('tur', 'Turbidity environmental range',    'turbidity environmental range',    run_range_test('env_min_tur', 'env_max_tur', QC.QC_flags.SUSPECT)),
            ('T',   'Temperature spikes',  'temperature spikes',  run_spike_test),
            ('S',   'Salinity spikes',     'salinity spikes',     run_spike_test),
            ('C',   'Conductivity spikes', 'conductivity spikes', run_spike_test),
            ('P',   'Pressure spikes',     'pressure spikes',     run_spike_test),
            ('pH',  'pH spikes',           'pH spikes',           run_spike_test),
            ('chl', 'Chlorophyll spikes',  'chlorophyll spikes',  run_spike_test),
            ('O2',  'Dissolved oxygen spikes', 'dissolved oxygen spikes', run_spike_test),
            ('org', 'Dissolved organic matter spikes', 'dissolved organic matter spikes', run_spike_test),
            ('tur', 'Turbidity spikes',    'turbidity spikes',    run_spike_test),
            ('T',   'Temperature rate of change',  'temperature rate of change',  run_rate_of_change_test),
            ('S',   'Salinity rate of change',     'salinity rate of change',     run_rate_of_change_test),
            ('C',   'Conductivity rate of change', 'conductivity rate of change', run_rate_of_change_test),
            ('P',   'Pressure rate of change',     'pressure rate of change',     run_rate_of_change_test),
            ('T',   'Temperature flat line',  'temperature flat line',  run_flat_line_test),
            ('S',   'Salinity flat line',     'salinity flat line',     run_flat_line_test),
            ('C',   'Conductivity flat line', 'conductivity flat line', run_flat_line_test),
            ('P',   'Pressure flat line',     'pressure flat line',     run_flat_line_test),
        ]

        if INPUT['profile'] == True:
            test_sequence += [
                ('T', 'Temperature vertical gradient',  'temperature vertical gradient',  run_vertical_gradient_test),
                ('S', 'Salinity vertical gradient',     'salinity vertical gradient',     run_vertical_gradient_test),
                ('C', 'Conductivity vertical gradient', 'conductivity vertical gradient', run_vertical_gradient_test),
            ]

        # HOBO Pendant only measures temperature (+ light, tested separately below),
        # so only the temperature tests apply - avoids a flag string full of
        # 'not evaluated' positions and empty Flag_S/Flag_C/... columns in the output
        if INPUT['input_type'] == 'HOBO':
            test_sequence = [entry for entry in test_sequence if entry[0] == 'T']

        # records which variable each appended flag character belongs to, so
        # handle_output_file maps flag positions to variables without hardcoding them
        flag_layout = [entry[0] for entry in test_sequence]

        for param_key, test_label, test_switch, test_runner in test_sequence:
            flags = apply_quality_test(flags, param_key, test_label, test_switch, test_runner)

        # Density inversion test (profiles only) -> last flag position.
        # Always appends one character for profiles so the flag layout stays fixed.
        if INPUT['profile'] == True:
            ti = time.time()
            if tsQualityTests.get('density inversion', 'OFF') == 'ON':
                flags = QC.density_inversion_test(raw_data, flags,
                                                  tolerance=tsSettings.get('dens_inv_tolerance', 0.03),
                                                  lat=INPUT.get('latitude', 17.5),
                                                  lon=INPUT.get('longitude', -40.0))
            else:
                flags = [flags[n] + '%d' % QC.QC_flags.DISMISSED for n in range(n_samples)]
            flag_layout.append('dens')
            test_sequence.append(('dens', 'Density inversion', 'density inversion', None))
            report_test('Density inversion', 'dens', flags, time.time() - ti)

        # Light fouling window (HOBO only) -> appends one 'lux' flag position.
        # Parameters (lux_baseline_days / lux_cutoff_frac / lux_sustain_days) live in
        # Settings > Parameters; the applied cutoff is reviewed on a plot and saved.
        lux_result = None
        if INPUT['input_type'] == 'HOBO':
            ti = time.time()
            lux_col = 'Luminosity (lux)'
            if tsQualityTests.get('light fouling window', 'OFF') == 'ON' and lux_col in raw_data.columns:
                lux_result = QC.light_fouling_baseline(
                    raw_data['Datetime'], raw_data[lux_col],
                    baseline_days=int(tsSettings.get('lux_baseline_days', 7)),
                    cutoff_frac=float(tsSettings.get('lux_cutoff_frac', 0.5)),
                    sustain_days=int(tsSettings.get('lux_sustain_days', 3)))
                for message in lux_result['warnings']:
                    log_line(message)
                if lux_result['evaluable']:
                    log_line('Light fouling: clean-sensor baseline %.0f lux (first %d days); '
                             'threshold %.0f lux (%.0f%% sustained %d days); proposed cutoff: %s'
                             % (lux_result['baseline'], lux_result['params']['baseline_days'],
                                lux_result['threshold'], 100 * lux_result['params']['cutoff_frac'],
                                lux_result['params']['sustain_days'],
                                lux_result['proposed_cutoff'].date() if lux_result['proposed_cutoff'] is not None else 'none'))
                    # label carries the FILE NAME so the user knows which device
                    # (replicate) is being reviewed
                    plot_label = ('%s (%s)' % (INPUT['site'], INPUT['file_name'])
                                  if INPUT.get('site') else INPUT['file_name'])
                    final_cutoff = review_light_window(lux_result, plot_label)
                    lux_result['final_cutoff'] = final_cutoff
                    log_line('Light fouling: cutoff APPLIED: %s'
                             % (pd.Timestamp(final_cutoff).date() if final_cutoff is not None else 'none (light kept good)'))
                    flags = QC.apply_light_window(raw_data['Datetime'], raw_data[lux_col], flags,
                                                  final_cutoff, evaluable=True)
                else:
                    lux_result['final_cutoff'] = None
                    flags = QC.apply_light_window(raw_data['Datetime'], raw_data[lux_col], flags,
                                                  None, evaluable=False)
            else:
                flags = [flags[n] + '%d' % QC.QC_flags.DISMISSED for n in range(n_samples)]
            flag_layout.append('lux')
            test_sequence.append(('lux', 'Light fouling window', 'light fouling window', None))
            report_test('Light fouling window', 'lux', flags, time.time() - ti)

        end = time.time()
        log_line('Processing time: %.2f s' % (end - start))

        # Apply the manual point-cut dismissals recorded during the interactive
        # panels: mark the chosen points DISMISSED (flag 5) in the flag string and
        # blank their value, keeping the row/timestamp for traceability instead of
        # deleting it. Setting all of a variable's flag positions to '5' rolls up to
        # Flag_<var> = 5 (worst_flag treats 5 as the lowest priority, so a stray 5
        # on a shared position, e.g. density, never corrupts another variable).
        if manual_dismiss_rows or manual_dismiss_cols:
            col_key = dict(MANUAL_CUT_COLUMNS)

            def _dismiss(row, positions):
                s = flags[row]
                for pos in positions:
                    if pos < len(s):
                        s = s[:pos] + '5' + s[pos + 1:]
                flags[row] = s

            all_positions = range(len(flag_layout))
            n_val = 0
            # whole-row dismissals (depth review): every position + every value column
            value_cols = [c for c in raw_data.columns
                          if c not in ('Datetime', 'Site', 'Sample number', 'Expedition')]
            for row in manual_dismiss_rows:
                _dismiss(row, all_positions)
                for c in value_cols:
                    raw_data.iat[row, raw_data.columns.get_loc(c)] = np.nan
            # per-variable dismissals
            for col, rows in manual_dismiss_cols.items():
                key = col_key.get(col)
                positions = [p for p in all_positions
                             if key in data.FLAG_BUCKET_MAP.get(flag_layout[p], [])]
                cidx = raw_data.columns.get_loc(col)
                for row in rows:
                    _dismiss(row, positions)
                    raw_data.iat[row, cidx] = np.nan
                    n_val += 1
            log_line('Manual cut: %d whole-row and %d per-variable point(s) dismissed (flag 5).'
                     % (len(manual_dismiss_rows), n_val))

        log_line('Stage 4/5: creating output table and reports...')
        qualified_data, raw_data, T_bdata, S_bdata, C_bdata, P_bdata, pH_bdata, chl_bdata, O2_bdata, org_bdata, tur_bdata, T_sdata, S_sdata, C_sdata, P_sdata, pH_sdata, chl_sdata, O2_sdata, org_sdata, tur_sdata, T_mdata, S_mdata, C_mdata, P_mdata, pH_mdata, chl_mdata, O2_mdata, org_mdata, tur_mdata = data.handle_output_file (raw_data, flags, flag_layout, remove_suspect=OUTPUT['remove_suspect'], remove_bad=OUTPUT['remove_bad'])

        # site metadata (filled before order_var so it is positioned and populated).
        # Coordinates are intentionally NOT written: keeping the column layout
        # identical across every qualified file (lat/long are only used to RUN the
        # qualification and, in the DatabaseView, the T-S diagram).
        qualified_data['Site'] = INPUT['site']
        qualified_data['QCS version'] = data.QCS_VERSION

        # HOBO gets its own output layout (temperature + light only, same metadata
        # block); Seaguard keeps the full TSCP layout. The two are never stackable.
        layout_type = 'hobo' if INPUT['input_type'] == 'HOBO' else 'tscp'
        qualified_data = data.order_var (qualified_data, n_cel, data_type=layout_type)

        # Export qualified data to .csv/.xlsx file (user's choice; reports are always .xlsx)
        os.chdir(OUTPUT['output_file_path'])
        # the qualification output folder is named after the input file + '_QLF'
        # (same for every workflow: Seaguard profile/mooring and HOBO)
        root_path = OUTPUT['output_file_path'] + '/' + re.search(r'^[^\.]+',INPUT['file_name']).group() + '_QLF'
        os.makedirs(root_path, exist_ok=True)
        data_folder = 'QCS qualified hobo data' if layout_type == 'hobo' else 'QCS qualified tscp data'
        path = root_path + '/' + data_folder + '/'
        os.makedirs(path, exist_ok=True)
        dataview_path =  root_path + '/QCS DataView (fixed scale)/'
        dataview_path2 = root_path + '/QCS DataView (unfixed scale)/'
        os.makedirs(dataview_path, exist_ok=True)
        os.makedirs(dataview_path2, exist_ok=True)

        # each per-file qualified sheet is named '<input name>_QLF'. With replicates
        # (N>1) this is ALWAYS used (the 'Output File Name' field holds the combined
        # name, not the individual ones); for a single file the typed field wins,
        # falling back to '<input name>_QLF' when it resolves empty.
        input_qlf = re.search(r'^[^\.]+', INPUT['file_name']).group() + '_QLF'
        if INPUT.get('n_replicates', 1) > 1:
            output_base = input_qlf
        else:
            output_base = re.sub(r'\.(csv|xlsx)$', '', OUTPUT['output_file_name'],
                                 flags=re.IGNORECASE).strip() or input_qlf
        if re.search('xlsx', OUTPUT['output_data_format'], re.IGNORECASE):
            data.save_excel_autofit(qualified_data, os.path.join(path, output_base + '.xlsx'))  ##create excel
        if re.search('csv', OUTPUT['output_data_format'], re.IGNORECASE):
            qualified_data.to_csv(os.path.join(path, output_base + '.csv'), index=False) ##create csv
        log_line('Exported data to: %s' % path)

        log_line('Exporting statistics table, reports and flag legend to: %s' % path)
        stat_table = data.tscp_stats_table (qualified_data)
        data.save_excel_autofit(stat_table, path + '/QCS_tscp_stat.xlsx')

        # per-test summary (the numbers previously printed only to the console)
        data.save_excel_autofit(pd.DataFrame(qc_report_rows), path + '/QCS_test_report.xlsx')

        # flag legend: which test/variable sits at each position of the flag string,
        # plus the meaning of each flag code (mapping used to live only in the code)
        legend_positions = pd.DataFrame([(pos, entry[1], entry[0]) for pos, entry in enumerate(test_sequence, start=1)],
                                        columns=['flag_position', 'test', 'variable'])
        legend_codes = pd.DataFrame([(1, 'good data'), (2, 'not evaluated'), (3, 'suspect'),
                                     (4, 'bad data'), (5, 'dismissed (manual cut) / test switched off'),
                                     (9, 'missing value')],
                                    columns=['flag_code', 'meaning'])
        data.save_excel_sheets({'flag_positions': legend_positions, 'flag_codes': legend_codes},
                               path + '/QCS_flag_legend.xlsx')

        # overall report: totals + per-variable bad/suspect/missing counts,
        # 'Valid' discounts rows with bad data in ANY of the nine variables
        bad_arrays = [T_bdata, S_bdata, C_bdata, P_bdata, pH_bdata, chl_bdata, O2_bdata, org_bdata, tur_bdata]
        all_bad = np.unique(np.concatenate([np.asarray(a, dtype=int) for a in bad_arrays])) if any(len(a) for a in bad_arrays) else np.array([])
        report_cols = {'start': start_time,
                       'end': end_time,
                       'Total': len(qualified_data),
                       'Valid': len(qualified_data) - len(all_bad),
                       'timestamp_backwards': ts_backwards,
                       'timestamp_duplicates': ts_duplicates,
                       'gaps_gt_3x_interval': ts_gaps,
                       'max_gap': ts_max_gap}
        per_var = {'T': (T_bdata, T_sdata, T_mdata), 'S': (S_bdata, S_sdata, S_mdata),
                   'C': (C_bdata, C_sdata, C_mdata), 'P': (P_bdata, P_sdata, P_mdata),
                   'pH': (pH_bdata, pH_sdata, pH_mdata), 'chl': (chl_bdata, chl_sdata, chl_mdata),
                   'O2': (O2_bdata, O2_sdata, O2_mdata), 'org': (org_bdata, org_sdata, org_mdata),
                   'tur': (tur_bdata, tur_sdata, tur_mdata)}
        for k, (b, s, m) in per_var.items():
            report_cols['%s_bad' % k] = len(b)
            report_cols['%s_suspect' % k] = len(s)
            report_cols['%s_missing' % k] = len(m)
        if 'Flag_lux' in qualified_data.columns:
            report_cols['lux_bad'] = int((qualified_data['Flag_lux'] == 4).sum())
            report_cols['lux_suspect'] = int((qualified_data['Flag_lux'] == 3).sum())
            report_cols['lux_missing'] = int((qualified_data['Flag_lux'] == 9).sum())
        QCS_report = pd.DataFrame(report_cols, index=[0])
        data.save_excel_autofit(QCS_report, path + '/QCS_report.xlsx')

        # HOBO: saves the light usage window plot with the applied cutoff and parameters
        # - the permanent documentation of WHERE and WHY the light was cut
        OUTPUT['last_light_plot'] = None
        if lux_result is not None and lux_result['evaluable']:
            plot_label = ('%s (%s)' % (INPUT['site'], INPUT['file_name'])
                          if INPUT.get('site') else INPUT['file_name'])
            fig_lux, ax_lux = view.plot_light_window(lux_result, plot_label)
            view.mark_light_cutoff(ax_lux, lux_result['final_cutoff'], lux_result)
            light_plot_path = os.path.join(path, 'QCS_light_window.svg')
            fig_lux.savefig(light_plot_path, bbox_inches='tight')
            plt.close(fig_lux)
            OUTPUT['last_light_plot'] = light_plot_path  # copied into the combined folder for replicates
            log_line('Light window plot saved to: %s' % light_plot_path)

        log_line('Stage 5/5: generating DataView plots...')
        # flag columns and administrative columns are never plotted as variables
        if INPUT['profile'] == True:
            plot_exceptions = ['Datetime', 'Expedition', 'Pressure (dbar)',
                               'Site', 'Longitude', 'Latitude', 'Depth (m)',
                               'Battery voltage (V)', 'Flag', 'Sample number', 'QCS version']
        else:
            plot_exceptions = ['Datetime', 'Expedition',
                               'Site', 'Longitude', 'Latitude',
                               'Battery voltage (V)', 'Flag', 'Sample number', 'QCS version']

        def plottable_variables():
            # ignores administrative columns, flag columns and completely empty
            # variables (e.g. the TSCP columns created as NaN for a HOBO file)
            return [v for v in qualified_data.keys()
                    if v not in plot_exceptions and not str(v).startswith('Flag')
                    and not qualified_data[v].isna().all()]

        for out_dir, fixed in ((dataview_path, True), (dataview_path2, False)):
            for variable in plottable_variables():
                if INPUT['profile'] == True:
                    view.plot_variable_profile(qualified_data, raw_data, variable, out_dir, tsSettings, fixed_scale=fixed)
                else:
                    view.plot_variable(qualified_data, raw_data, variable, out_dir, tsSettings, fixed_scale=fixed)
        OUTPUT['last_output_root'] = root_path
        OUTPUT['last_qualified_df'] = qualified_data.copy()  # kept for replicate combination
        plt.close('all')
        os.chdir(rootPath)
        log_line('Done: qualification finished.')

    # restore last user choices and start the interface
    restore_user_prefs()

if __name__ == '__main__':
    # Standalone dev launch (the shipped entry point is QCS_App.py).
    theme.enable_high_dpi()
    _root = Tk()
    _root.title("QCS - Data Qualification Tool %s" % data.QCS_VERSION)
    theme.set_scaled_geometry(_root, 840, 830, min_width=760, min_height=720)
    theme.apply_theme(_root, USER_PREFS.get('ui_theme', 'light'))
    theme.set_window_icon(_root)
    _frame = ttk.Frame(_root)
    _frame.pack(fill='both', expand=True)
    build_qualification_tab(_frame, _root)
    _root.mainloop()

import os
import sys
import json
import pandas as pd
import QCS_DataHandler as data
import QCS_DataView as view
import QCS_Theme as theme
from QCS_Theme import ToolTip

# Run with no console window (launched via pythonw): route everything that would
# have gone to the terminal into the in-app Execution log, and never let a crash
# be silent. The log panel is attached later in build_step2.
_out = theme.install_output_redirect()
theme.install_crash_handler('QCS Data Visualization', _out)
from tkinter import *
import tkinter as tk
from tkinter import ttk
from tkinter import filedialog
from tkinter import messagebox

# Tooltips dictionary
TOOLTIPS = {
    'database_files': "Select database or qualified file(s) to visualize\nMultiple files can be selected (they are combined,\nvalidated and deduplicated automatically)",
    'join_files': "Instead of picking files one by one: scan a parent folder,\nfind every 'QCS qualified ... data' subfolder of the QCS outputs,\nskip report files and combine everything found into one database.\n(Selecting multiple files above already joins them - this mode is\nfor sweeping a whole folder tree.)",
    'sort_time': "Sort data chronologically by datetime",
    'instrument': "Which instrument produced the qualified files\nSeaguard (TSCP) and HOBO spreadsheets are never\nstackable - build separate databases",
    'output_name': "Name for processed database file",
    'input_path': "Folder containing input files",
    'output_path': "Folder where results will be saved",
    'data_type': "Type of data (profile or mooring)",
    'filter_year': "Check the year(s) to visualize\nPanels are generated once per selected year",
    'time_start': "OPTIONAL: start of the X axis in mooring plots\nFormat: DD/MM/YYYY HH:MM (e.g. 15/04/2019 09:00)\nLeave empty to fit the data automatically\nCross-site panels standardize the TIME OF DAY: the window's\nday offset + clock time apply to each site's own days",
    'time_end': "OPTIONAL: end of the X axis in mooring plots\nFormat: DD/MM/YYYY HH:MM (e.g. 16/04/2019 09:00)\nLeave empty to fit the data automatically\nCross-site panels standardize the TIME OF DAY: the window's\nday offset + clock time apply to each site's own days",
    'depth_min': "OPTIONAL: minimum depth (m) for the depth axis in profile plots\nLeave empty to fit the data automatically",
    'depth_max': "OPTIONAL: maximum depth (m) for the depth axis in profile plots\nLeave empty to fit the data automatically",
    'panel1': "Panel 1: Comparison between parameters at the same site",
    'panel2': "Panel 2: Comparison of the same parameter between sites",
    'panel3': "Panel 3: Comparison between parameters at the same site (vertical profile)",
    'hobo_temp': "HOBO panel: temperature over time, one plot per selected site\nSuspect/bad points (Flag_T >= 3) are highlighted",
    'hobo_light': "HOBO panel: light over time (log scale), one plot per selected site\nThe fouling window (Flag_lux == 4) is shaded from the cutoff on",
    'hobo_light_multi': "HOBO panel: light (log scale) with all selected sites together\nEach site's fouling cutoff is marked to compare fouling onset",
    'ts_diagram': "Generate a Temperature-Salinity (T-S) diagram: temperature vs\nsalinity with depth as the colour, to identify water masses.",
    'latitude': "Latitude used by the T-S diagram (gsw). Pre-filled from the\nqualification region and locked; editable only for a\nstandalone file (which stores no coordinates).",
    'longitude': "Longitude used by the T-S diagram (gsw). Pre-filled from the\nqualification region and locked; editable only for a\nstandalone file (which stores no coordinates).",
    'ts_params': "Which temperature & salinity to plot on the T-S diagram:\n- Conservative T & Absolute S (TEOS-10, uses lat/long)\n- Potential T & Practical S (classic EOS-80)",
    'tendency': "Add linear regression lines to plots",
    'tendency_degree': "Degree of polynomial for linear regression lines",
    'data_points': "Show individual data points on plots",
    'site_filter': "Select sites to include in visualization",
    'param_filter': "Select parameters to include in visualization",
    'param_secondary': "Rarely-used variables: always start unchecked\n(check manually when needed)",
    'fixed_scale': "Use fixed scales for all plots to allow direct comparison",
    'min_scale': "Minimum value for parameter scale",
    'max_scale': "Maximum value for parameter scale"
}

class ErrorLogger(theme.LogConsole):
    """Execution log (shared theme console), positioned via pack."""

    def __init__(self, parent):
        super().__init__(parent, title=" Execution log ", height=8)
        self.frame.pack(fill='both', expand=True, padx=5, pady=5)


# ----- user preferences: shared with QCS_Main (same json file) -----
def settings_store_path():
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

def restore_entry(entry, value):
    # fills a field even if it is currently disabled
    if not value:
        return
    prev = entry.cget('state')
    entry.config(state='normal')
    entry.delete(0, END)
    entry.insert(0, value)
    entry.config(state=prev)

def set_disabled_style(widget):
    # the theme (sv-ttk or clam) already draws the 'disabled' state properly
    widget.config(state='disabled')

def set_enabled_style(widget):
    if isinstance(widget, ttk.Combobox):
        widget.config(state='readonly')
    else:
        widget.config(state='normal')

def is_hobo_input():
    """The Step 2 window panels change according to the Step 1 instrument."""
    return inputSettings.get('instrument', 'Seaguard') == 'HOBO'

def toggle_all_controls(enabled=False):
    """Enables or disables all controls depending on the selected Data Type"""
    # Panels
    panel1_cb.config(state='normal' if enabled else 'disabled')
    panel2_cb.config(state='normal' if enabled else 'disabled')
    panel3_cb.config(state='normal' if enabled else 'disabled')

    # Display options
    tendency_cb.config(state='normal' if enabled else 'disabled')
    tendency_entry.config(state='normal' if enabled and tendency.get() else 'disabled')
    points_cb.config(state='normal' if enabled else 'disabled')
    fixed_scale_cb.config(state='normal' if enabled else 'disabled')
    
    # TS Diagram
    ts_cb.config(state='normal' if enabled else 'disabled')
    latitude_entry.config(state='normal' if enabled and tsDiagram.get() else 'disabled')
    longitude_entry.config(state='normal' if enabled and tsDiagram.get() else 'disabled')
    tsParam_combobox.config(state='readonly' if enabled and tsDiagram.get() else 'disabled')
    
    # Filters
    for cb in year_widgets.values():
        cb.config(state='normal' if enabled else 'disabled')
    for cb in site_widgets.values():
        cb.config(state='normal' if enabled else 'disabled')
    for cb in parameter_widgets.values():
        cb.config(state='normal' if enabled else 'disabled')

    # X-axis time window (mooring)
    time_start_entry.config(state='normal' if enabled else 'disabled')
    time_end_entry.config(state='normal' if enabled else 'disabled')
    # Depth-axis range (profile)
    depth_min_entry.config(state='normal' if enabled else 'disabled')
    depth_max_entry.config(state='normal' if enabled else 'disabled')

    # Scales
    toggle_scale_controls()

def toggle_input_mode():
    if join.get():  # If 'Build database from a folder' is checked
        # folder-scan mode: Database File(s) does not apply -> stash and clear it
        _input_mode_cache['files'] = fileNames_entry.get()
        fileNames_entry.delete(0, END)
        set_disabled_style(fileNames_entry)
        set_disabled_style(browse_file_btn)
        set_enabled_style(inputPath_entry)
        set_enabled_style(browse_input_btn)
        set_enabled_style(outputName_entry)
        # the output name is only used to name the built database - restore the
        # remembered name when the field becomes active
        if not outputName_entry.get().strip():
            restore_entry(outputName_entry, USER_PREFS.get('dbv_output_name', ''))
    else:  # unchecked: pick files one by one (multi-select already joins them)
        set_enabled_style(fileNames_entry)
        set_enabled_style(browse_file_btn)
        # restore the file selection stashed when folder mode was turned on
        if _input_mode_cache.get('files') and not fileNames_entry.get().strip():
            fileNames_entry.insert(0, _input_mode_cache['files'])
        set_disabled_style(inputPath_entry)
        set_disabled_style(browse_input_btn)
        # single-file mode does not use an output name: leave it blank + disabled
        outputName_entry.config(state='normal')
        outputName_entry.delete(0, END)
        set_disabled_style(outputName_entry)

def toggle_panel_dependent_controls():
    any_panel_selected = panel1.get() or panel2.get() or panel3.get()

    if any_panel_selected and is_hobo_input():
        # HOBO panels already define the presentation (points, log scale):
        # trend lines and 'show points' do not apply
        set_disabled_style(tendency_cb)
        set_disabled_style(tendency_entry)
        set_disabled_style(points_cb)
        set_enabled_style(fixed_scale_cb)
    elif any_panel_selected:
        set_enabled_style(tendency_cb)
        if tendency.get():
            set_enabled_style(tendency_entry)
        set_enabled_style(points_cb)
        set_enabled_style(fixed_scale_cb)
    else:
        set_disabled_style(tendency_cb)
        set_disabled_style(tendency_entry)
        set_disabled_style(points_cb)
        set_disabled_style(fixed_scale_cb)
    
    toggle_scale_controls()

def toggle_parameter_checkboxes():
    # in HOBO panels each panel already states which variable it plots
    # (temperature or light), so the parameter filter does not apply and stays disabled
    if (panel1.get() or panel2.get() or panel3.get()) and not is_hobo_input():
        for cb in parameter_widgets.values():
            set_enabled_style(cb)
    else:
        for cb in parameter_widgets.values():
            set_disabled_style(cb)

    toggle_scale_controls()

def toggle_ts_controls():
    if tsDiagram.get():
        # coordinates from the qualification region stay LOCKED (read-only): the
        # value is still used for the diagram but cannot be edited. When the
        # database was opened as a standalone file (no region handoff), the file
        # has no coordinates, so the fields must be editable for the user to type.
        if _coords_from_handoff:
            set_disabled_style(latitude_entry)
            set_disabled_style(longitude_entry)
        else:
            set_enabled_style(latitude_entry)
            set_enabled_style(longitude_entry)
        set_enabled_style(tsParam_combobox)
    else:
        set_disabled_style(latitude_entry)
        set_disabled_style(longitude_entry)
        set_disabled_style(tsParam_combobox)

def toggle_scale_controls():
    """Per-parameter scale controls: the Min/Max of a parameter are editable only
    when Fixed scale is on, a panel is selected AND that parameter is checked.
    Enabling pre-fills the data's own min/max (once, if empty); disabling clears
    the fields. Scale values are per-imported-sheet and are not persisted."""
    active = fixedScale.get() and (panel1.get() or panel2.get() or panel3.get())
    for param, min_e in min_scale_entries.items():
        max_e = max_scale_entries[param]
        on = active and param in parameter_vars and parameter_vars[param].get()
        if on:
            if not (min_e.get().strip() or max_e.get().strip()):
                _fill_scale(param)   # first activation -> auto default from data
            set_enabled_style(min_e)
            set_enabled_style(max_e)
        else:
            for entry in (min_e, max_e):
                entry.config(state='normal')
                entry.delete(0, END)
                set_disabled_style(entry)
            _auto_scale.discard(param)

def _fill_scale(param):
    """Fill a parameter's Min/Max with the data default and mark it auto-filled."""
    for entry, kind in ((min_scale_entries[param], 'min'), (max_scale_entries[param], 'max')):
        val = _param_data_extreme(param, kind)
        entry.config(state='normal')
        entry.delete(0, END)
        if val:
            entry.insert(0, val)
    _auto_scale.add(param)

def _refresh_scale_defaults():
    """Re-fill the still-auto scale fields from the current Site/Year selection
    (called when those filters change); user-edited fields are left untouched."""
    for param in list(_auto_scale):
        if param in parameter_vars and parameter_vars[param].get():
            _fill_scale(param)

def _param_data_extreme(param, kind):
    """Formatted Min/Max of a parameter over the SELECTED sites/years, with 20%
    breathing room added to each side so the plot is not cramped ('' if
    unavailable). With several sites/years selected this spans them all.

    Only APPROVED data (flag 1 good / 2 not evaluated) drives the default: the
    qualified sheet may retain the values of suspect/bad/dismissed rows (the
    operator's choice at qualification), and letting those extremes set the
    scale would produce absurd defaults (e.g. a suspect DOM spike of 550 ppb
    against a good range of 0-6)."""
    if database is None or param not in database.columns:
        return ''
    df = database
    sites = [s for s, v in site_vars.items() if v.get()] if site_vars else []
    years = [y for y, v in year_vars.items() if v.get()] if year_vars else []
    if sites:
        df = df[df['Site'].isin(sites)]
    if years and 'Datetime' in df.columns:
        df = df[df['Datetime'].dt.year.isin(years)]
    col = df[param]
    flag_col = data.PARAM_FLAG_COLUMN.get(param)
    if flag_col and flag_col in df.columns:
        flags = pd.to_numeric(df[flag_col], errors='coerce')
        col = col[flags.isin([1, 2])]
    col = col.dropna()
    if col.empty:
        return ''
    lo, hi = float(col.min()), float(col.max())
    pad = 0.2 * (hi - lo)
    if pad == 0:                      # constant series: pad by 20% of |value| (or 1)
        pad = 0.2 * abs(hi) if hi != 0 else 1.0
    value = (lo - pad) if kind == 'min' else (hi + pad)
    return '%.4g' % value

def toggle_data_type():
    data_type = dType_combobox.get()
    
    if not data_type:  # If no Data Type is selected
        toggle_all_controls(enabled=False)
        return

    toggle_all_controls(enabled=True)  # Enable everything

    def _stash_disable(entry, key):
        # a field that does not apply in this mode: remember its value, blank it
        # and grey it out (so it is not selectable)
        val = entry.get().strip()
        if val:
            _field_cache[key] = val
        entry.config(state='normal')
        entry.delete(0, END)
        set_disabled_style(entry)

    def _restore_enable(entry, key):
        # a field that applies again: enable it and bring back the last value
        set_enabled_style(entry)
        if not entry.get().strip() and _field_cache.get(key):
            entry.delete(0, END)
            entry.insert(0, _field_cache[key])

    def _restore_or_default_depth(entry, key, which):
        # Depth range applies again: enable it, keep the user's previous value if
        # there was one, otherwise pre-fill the depths available in the data (the
        # "Depth available" range) - mirroring what the X-axis datetime does.
        set_enabled_style(entry)
        if entry.get().strip():
            return
        if _field_cache.get(key):
            entry.insert(0, _field_cache[key])
            return
        if database is not None and 'Depth (m)' in database.columns:
            col = database['Depth (m)'].dropna()
            if not col.empty:
                val = col.min() if which == 'min' else col.max()
                entry.insert(0, '%.2f' % val)

    def _reset_time_default(entry, which):
        # The X-axis time window is NOT persisted across data-type switches: when it
        # applies again it returns to the DEFAULT (the full range shown in "Data
        # available"), never the previously chosen value.
        set_enabled_style(entry)
        entry.delete(0, END)
        if database is not None and 'Datetime' in database.columns:
            dt = database['Datetime'].min() if which == 'start' else database['Datetime'].max()
            if pd.notna(dt):
                entry.insert(0, dt.strftime('%d/%m/%Y %H:%M'))

    # Specific logic for each data type. A control that does not apply is
    # UNCHECKED/blanked and greyed out; one that applies again is re-enabled and
    # its previous value restored.
    if is_hobo_input():
        # HOBO: no T-S (no salinity) and no profile (no depth); the X-axis time
        # window still applies (time series)
        tsDiagram.set(False)
        set_disabled_style(ts_cb)
        _stash_disable(depth_min_entry, 'depth_min')
        _stash_disable(depth_max_entry, 'depth_max')
        _reset_time_default(time_start_entry, 'start')
        _reset_time_default(time_end_entry, 'end')
    elif data_type == 'mooring':
        panel3.set(False)
        set_disabled_style(panel3_cb)
        tsDiagram.set(False)            # T-S is profile-only -> uncheck it here
        set_disabled_style(ts_cb)
        # default panel so the selection is never empty when switching here
        if not (panel1.get() or panel2.get()):
            panel1.set(True)
        _stash_disable(depth_min_entry, 'depth_min')     # depth range = profile only
        _stash_disable(depth_max_entry, 'depth_max')
        _reset_time_default(time_start_entry, 'start')   # X-axis window applies (default range)
        _reset_time_default(time_end_entry, 'end')
    elif data_type == 'profile':
        panel1.set(False)
        panel2.set(False)
        set_disabled_style(panel1_cb)
        set_disabled_style(panel2_cb)
        # default panel so the selection is never empty when switching here
        if not panel3.get():
            panel3.set(True)
        _stash_disable(time_start_entry, 'time_start')   # X-axis window = mooring only
        _stash_disable(time_end_entry, 'time_end')
        _restore_or_default_depth(depth_min_entry, 'depth_min', 'min')   # depth range applies
        _restore_or_default_depth(depth_max_entry, 'depth_max', 'max')

    toggle_panel_dependent_controls()
    toggle_parameter_checkboxes()
    toggle_ts_controls()

def _default_output_root(file_path):
    """Where DataView outputs should go by default for a selected qualified file:
    the qualification output root (the '..._QLF' folder that holds the
    'QCS qualified ... data' subfolder), or the file's own folder otherwise."""
    folder = os.path.dirname(file_path)
    parent, name = os.path.split(folder)
    if name in ('QCS qualified tscp data', 'QCS qualified hobo data'):
        return parent
    return folder

def selectFiles():
    start = USER_PREFS.get('dbv_last_db_dir') or USER_PREFS.get('last_output_dir', '')
    if not os.path.isdir(start):
        start = ''
    filenames = filedialog.askopenfilenames(initialdir=start, title="Select files")
    if filenames:
        fileNames_entry.delete(0, END)
        fileNames_entry.insert(0, ";".join(filenames))
        join.set(False)
        toggle_input_mode()
        USER_PREFS['dbv_last_db_dir'] = os.path.dirname(filenames[0])
        # auto-fill Output Path with the qualification output root of the file
        out_root = _default_output_root(filenames[0])
        outputPath_entry.delete(0, END)
        outputPath_entry.insert(0, out_root)
        # remember an output name (used only if the user later switches to
        # 'Build database from a folder'); the field itself stays blank/disabled
        # in single-file mode
        out_name = os.path.splitext(os.path.basename(filenames[0]))[0]
        USER_PREFS['dbv_output_path'] = out_root
        USER_PREFS['dbv_output_name'] = out_name
        USER_PREFS['dbv_last_output_dir'] = out_root
        save_user_prefs()
        autodetect_instrument(filenames[0])

def autodetect_instrument(path):
    """Sets the Instrument combobox from the first selected file's columns
    (detect_qualified_layout). Just a convenience: the combobox stays editable,
    and any failure only leaves the current selection with a log warning."""
    try:
        if path.lower().endswith('.csv'):
            head = pd.read_csv(path, nrows=1)
        else:
            head = pd.read_excel(path, nrows=1)
        layout = data.detect_qualified_layout(head)
        detected = 'HOBO' if layout == 'hobo' else 'Seaguard'
        instrument_combobox.set(detected)
        print('Info: instrument auto-detected as %s (from %s).'
              % (detected, os.path.basename(path)))
    except Exception as e:
        print('Warning: could not auto-detect the instrument from %s: %s'
              % (os.path.basename(path), e))

def selectOutputFolder():
    # start at the current field value (or last used) to avoid the drive-root
    # scan that makes the native folder picker hang for a few seconds
    start = (outputPath_entry.get().strip()
             or USER_PREFS.get('dbv_last_output_dir')
             or USER_PREFS.get('dbv_last_db_dir', ''))
    if not os.path.isdir(start):
        start = ''
    folderPath = filedialog.askdirectory(initialdir=start, title="Select output folder")
    if folderPath:
        outputPath_entry.delete(0, END)
        outputPath_entry.insert(0, folderPath)
        USER_PREFS['dbv_last_output_dir'] = folderPath
        save_user_prefs()

def selectInputFolder():
    start = inputPath_entry.get().strip() or USER_PREFS.get('dbv_last_input_dir', '')
    if not os.path.isdir(start):
        start = ''
    folderPath = filedialog.askdirectory(initialdir=start, title="Select input folder")
    if folderPath:
        inputPath_entry.delete(0, END)
        inputPath_entry.insert(0, folderPath)
        USER_PREFS['dbv_last_input_dir'] = folderPath
        save_user_prefs()

def saveInputSettings():
    # validation with clear warnings before closing the window
    if instrument_combobox.get() not in ('Seaguard', 'HOBO'):
        messagebox.showwarning("Warning", "Select the instrument that produced the files\n('Instrument' field).")
        return
    if join.get():
        if not inputPath_entry.get().strip() or not os.path.isdir(inputPath_entry.get().strip()):
            messagebox.showwarning("Warning", "To build the database from a folder, select a valid\ninput folder ('Input Path' field).")
            return
        if not outputName_entry.get().strip():
            messagebox.showwarning("Warning", "Define a name for the generated database\n('Output Name' field).")
            return
    else:
        db_file = fileNames_entry.get().strip()
        if not db_file:
            messagebox.showwarning("Warning", "Select the database file (.xlsx) or check\n'Build database from a folder' to create a new one.")
            return
        first_file = db_file.split(';')[0]
        if not os.path.isfile(first_file):
            messagebox.showerror("Error", "File not found:\n%s" % first_file)
            return
    if not outputPath_entry.get().strip() or not os.path.isdir(outputPath_entry.get().strip()):
        messagebox.showwarning("Warning", "Select a valid output folder\n('Output Path' field).")
        return

    inputSettings['databaseFileName'] = fileNames_entry.get()
    inputSettings['joinFiles'] = join.get()
    inputSettings['outputFileName'] = outputName_entry.get()
    inputSettings['outputPath'] = outputPath_entry.get()
    inputSettings['inputPath'] = inputPath_entry.get()
    inputSettings['sortByTime'] = sort.get()
    inputSettings['instrument'] = instrument_combobox.get()

    # store the latest choices
    USER_PREFS.update({
        'dbv_database_file': fileNames_entry.get(),
        'dbv_output_name': outputName_entry.get(),
        'dbv_output_path': outputPath_entry.get(),
        'dbv_input_path': inputPath_entry.get(),
        'dbv_sort_by_time': sort.get(),
        'dbv_instrument': instrument_combobox.get(),
    })
    save_user_prefs()
    return True  # validation passed and settings stored -> Step 2 may proceed

def saveDataViewSettings():
    try:
        dataViewSettings['dataType'] = dType_combobox.get()
        selectedYears = [y for y in year_vars.keys() if year_vars[y].get() == True]
        dataViewSettings['filterByYears'] = selectedYears
        dataViewSettings['panel1'] = panel1.get()
        dataViewSettings['panel2'] = panel2.get()
        dataViewSettings['panel3'] = panel3.get()
        dataViewSettings['fixedScale'] = fixedScale.get()
        
        dataViewSettings['tsDiagram'] = tsDiagram.get()
        if dataViewSettings['tsDiagram'] == True:
            # the T-S diagram is the ONE place coordinates are mandatory: they
            # enter gsw's absolute salinity / conservative temperature and do NOT
            # cancel out. Refuse to run it without valid lat/long (clear message).
            try:
                lat_ts = float(latitude_entry.get())
                lon_ts = float(longitude_entry.get())
                if not (-90 <= lat_ts <= 90 and -180 <= lon_ts <= 180):
                    raise ValueError
                dataViewSettings['latitude'] = lat_ts
                dataViewSettings['longitude'] = lon_ts
                dataViewSettings['tsParam'] = tsParam_combobox.get()
            except ValueError:
                messagebox.showwarning("Warning",
                                       "The T-S Diagram needs a valid Latitude and Longitude.\n\n"
                                       "Fill both (decimal degrees, e.g. -17.5 and -40.0) or uncheck\n"
                                       "'T-S Diagram'. The diagram will be skipped this run.")
                error_logger.log("Warning: T-S Diagram skipped - missing/invalid Latitude/Longitude")
                dataViewSettings['tsDiagram'] = False

        dataViewSettings['tendencyLines'] = tendency.get()
        if dataViewSettings['tendencyLines'] == True:
            dataViewSettings['linearRegressionDegree'] = int(tendency_entry.get()) if tendency_entry.get() else None
        else:
            dataViewSettings['linearRegressionDegree'] = None
        dataViewSettings['viewDataPoints'] = dataPoints.get()

        # optional fixed time window for the X axis of mooring plots
        dataViewSettings['xAxisStart'] = None
        dataViewSettings['xAxisEnd'] = None
        start_text = time_start_entry.get().strip()
        end_text = time_end_entry.get().strip()
        if start_text or end_text:
            try:
                x_start = pd.to_datetime(start_text, dayfirst=True)
                x_end = pd.to_datetime(end_text, dayfirst=True)
                if pd.isna(x_start) or pd.isna(x_end) or x_end <= x_start:
                    raise ValueError('invalid interval')
                dataViewSettings['xAxisStart'] = x_start
                dataViewSettings['xAxisEnd'] = x_end
            except Exception:
                messagebox.showwarning("Warning",
                                       "Invalid X-axis time window.\n\n"
                                       "Fill BOTH fields using DD/MM/YYYY HH:MM\n"
                                       "(end after start), e.g. 15/04/2019 09:00,\n"
                                       "or leave both empty to fit the data automatically.")
                error_logger.log("Warning: invalid X-axis time window - ignored")

        # optional fixed depth range for the depth axis of profile plots
        dataViewSettings['depthAxisMin'] = None
        dataViewSettings['depthAxisMax'] = None
        dmin_text = depth_min_entry.get().strip()
        dmax_text = depth_max_entry.get().strip()
        if dmin_text or dmax_text:
            try:
                d_min = float(dmin_text)
                d_max = float(dmax_text)
                if d_max <= d_min:
                    raise ValueError('invalid interval')
                dataViewSettings['depthAxisMin'] = d_min
                dataViewSettings['depthAxisMax'] = d_max
            except Exception:
                messagebox.showwarning("Warning",
                                       "Invalid depth-axis range.\n\n"
                                       "Fill BOTH fields with numbers (max > min), e.g. 0 and 50,\n"
                                       "or leave both empty to fit the data automatically.")
                error_logger.log("Warning: invalid depth-axis range - ignored")

        selectedSites = []
        for site in site_vars.keys():
            if site_vars[site].get() == True and site not in selectedSites:
                selectedSites.append(site)
        
        selectedParameters = []
        for param in parameter_vars.keys():
            if parameter_vars[param].get() == True and param not in selectedParameters:
                selectedParameters.append(param)
        
        # Save the defined scales
        scale_settings = {}
        for param in parameter_names:
            min_val = min_scale_entries[param].get()
            max_val = max_scale_entries[param].get()
            if min_val and max_val:
                try:
                    scale_settings[param] = {
                        'min': float(min_val),
                        'max': float(max_val)
                    }
                except ValueError:
                    error_logger.log(f"Warning: Invalid scale values for {param} - using defaults")
        
        dataViewSettings['scaleSettings'] = scale_settings
        dataViewSettings['siteList'] = selectedSites
        dataViewSettings['parameterList'] = selectedParameters

        # store the latest visualization choices
        USER_PREFS.update({
            'dbv_data_type': dType_combobox.get(),
            'dbv_selected_years': selectedYears,
            'dbv_time_start': time_start_entry.get(),
            'dbv_time_end': time_end_entry.get(),
            'dbv_depth_min': depth_min_entry.get(),
            'dbv_depth_max': depth_max_entry.get(),
            'dbv_latitude': latitude_entry.get(),
            'dbv_longitude': longitude_entry.get(),
            'dbv_degree': tendency_entry.get(),
            'dbv_ts_param': tsParam_combobox.get(),
            'dbv_panel1': panel1.get(),
            'dbv_panel2': panel2.get(),
            'dbv_panel3': panel3.get(),
            'dbv_ts_diagram': tsDiagram.get(),
            'dbv_tendency': tendency.get(),
            'dbv_data_points': dataPoints.get(),
            'dbv_fixed_scale': fixedScale.get(),
            'dbv_selected_sites': selectedSites,
            # NOTE: parameter selection and scale values are per-imported-sheet
            # (defaults recomputed from the data each time) and are NOT persisted.
        })
        save_user_prefs()

        error_logger.log("Info: view settings saved.")
    except Exception as e:
        error_logger.log(f"Error saving view settings: {str(e)}")

def generatePanels():
    error_logger.clear()  # Clear the log before generating new panels
    # close panels from a previous run so the new ones (with the new settings,
    # e.g. an edited X-axis window) replace them instead of opening behind and
    # looking like nothing changed
    view.plt.close('all')

    # implicitly saves the current interface choices: generating panels with
    # stale settings was a pitfall of the 2-click save->generate flow
    saveDataViewSettings()

    if not dataViewSettings.get('dataType'):
        error_logger.log("Error: nothing to plot - configure the options and click 'Generate panels'")
        return

    # the year checkboxes only list years present in the database,
    # so the only possible mistake left is selecting none
    available_years = sorted(set(int(y) for y in database['Datetime'].dt.year.dropna().unique()))
    years_str = ', '.join(str(y) for y in available_years)
    selected_years = [y for y in dataViewSettings.get('filterByYears', []) if y in available_years]
    if not selected_years:
        messagebox.showwarning("No year selected",
                               "Check at least one year in 'Filter by year' and click "
                               "'Generate panels' again.\n\n"
                               "Years available in this database:\n%s" % years_str)
        error_logger.log("Error: no year selected (available: %s)" % years_str)
        return

    try:
        # each plot logs one 'Info:' progress line; the ONE 'Done:' summary at the
        # end reports how many panels were produced (no per-panel green lines, so
        # the log is not a wall of redundant "generated successfully" messages)
        n_ok = 0
        # panels are generated once for each selected year
        for year in selected_years:
            dataViewSettings['filterByYear'] = year
            if is_hobo_input():
                # HOBO: dedicated panels (temperature / light+window / light
                # multi-site); T-S does not apply (no salinity)
                selected_sites = dataViewSettings.get('siteList', [])
                any_hobo_panel = (dataViewSettings.get('panel1', False)
                                  or dataViewSettings.get('panel2', False)
                                  or dataViewSettings.get('panel3', False))
                if any_hobo_panel and not selected_sites:
                    error_logger.log("Error: no site selected - check at least one site in 'Filter by Site'")
                    continue

                if dataViewSettings.get('panel1', False):
                    for site in selected_sites:
                        try:
                            view.plot_hobo_temperature(database, dataViewSettings, site)
                            error_logger.log("Info: HOBO temperature panel for %s (%d) generated." % (site, year))
                            n_ok += 1
                        except Exception as e:
                            error_logger.log("Error generating HOBO temperature for %s (%d): %s" % (site, year, e))

                if dataViewSettings.get('panel2', False):
                    for site in selected_sites:
                        try:
                            view.plot_hobo_light(database, dataViewSettings, site)
                            error_logger.log("Info: HOBO light panel for %s (%d) generated." % (site, year))
                            n_ok += 1
                        except Exception as e:
                            error_logger.log("Error generating HOBO light for %s (%d): %s" % (site, year, e))

                if dataViewSettings.get('panel3', False):
                    try:
                        view.plot_hobo_light_multisite(database, dataViewSettings)
                        error_logger.log("Info: HOBO light multi-site panel (%d) generated." % year)
                        n_ok += 1
                    except Exception as e:
                        error_logger.log("Error generating HOBO light multi-site (%d): %s" % (year, e))
                continue

            if dataViewSettings['dataType'] == 'mooring':
                if dataViewSettings.get('panel1', False):
                    try:
                        view.plot_database_panel1(database, dataViewSettings)
                        error_logger.log("Info: Panel 1 (%d) generated." % year)
                        n_ok += 1
                    except Exception as e:
                        error_logger.log(f"Error generating Panel 1 ({year}): {str(e)}")

                if dataViewSettings.get('panel2', False):
                    try:
                        view.plot_database_panel2(database, dataViewSettings)
                        error_logger.log("Info: Panel 2 (%d) generated." % year)
                        n_ok += 1
                    except Exception as e:
                        error_logger.log(f"Error generating Panel 2 ({year}): {str(e)}")

                if dataViewSettings.get('panel3', False):
                    error_logger.log("Warning: Panel 3 is not suited for mooring data")

            elif dataViewSettings['dataType'] == 'profile':
                if dataViewSettings.get('panel3', False):
                    try:
                        view.plot_database_panel3(database, dataViewSettings)
                        error_logger.log("Info: Panel 3 (%d) generated." % year)
                        n_ok += 1
                    except Exception as e:
                        error_logger.log(f"Error generating Panel 3 ({year}): {str(e)}")

                if dataViewSettings.get('panel1', False) or dataViewSettings.get('panel2', False):
                    error_logger.log("Warning: Panels 1/2 are not suited for profile data")

            if dataViewSettings.get('tsDiagram', False):
                try:
                    view.plot_TS_diagram(database, dataViewSettings)
                    error_logger.log("Info: T-S diagram (%d) generated." % year)
                    n_ok += 1
                except Exception as e:
                    error_logger.log(f"Error generating TS Diagram ({year}): {str(e)}")

        # single completion summary (green). If nothing was produced, say so
        # instead of claiming success.
        if n_ok:
            out_dir = os.path.join(inputSettings.get('outputPath', ''), 'DatabaseView')
            error_logger.log("Done: %d panel(s) generated in %s" % (n_ok, out_dir))
        else:
            error_logger.log("Warning: no panel was generated - check the selected options.")
    except Exception as e:
        error_logger.log(f"Critical error: {str(e)}")

def show_help():
    help_text = """
    QCS Database View Tool
    
    INSTRUCTIONS:
    1. INPUT SETTINGS:
       - Select either:
         * Database file (xlsx) - for existing database
         OR
         * Input folder + 'Build database from a folder' - to create a new database
       - Choose output location
       - Configure processing options
    
    2. VIEW SETTINGS:
       - Select data type (profile/mooring)
       - Choose visualization panels
       - Filter by sites and parameters
       - Configure display options
       - Save data view settings
    
    3. Click 'Generate Panels' to create plots
    
    TIPS:
    - Use either file selection OR folder input (mutually exclusive)
    - Different panels are suited for different data types
    - Use filters to focus on specific data subsets
    - Saving settings again after generating panels allows for multiple plots with different settings
    - Use fixed scales to maintain consistent axis ranges across plots
    """
    messagebox.showinfo("Database View Help", help_text)

# Main application
rootPath = os.getcwd()
inputSettings = {}
dataViewSettings = {}

def build_step1(parent):
    """Builds Step 1 (choose or build the database) inside `parent`, a frame in
    the unified app's Visualization tab. The root window, header and dark-mode
    switch are owned by the QCS_App shell."""
    global fileNames_entry, inputPath_entry, browse_file_btn, browse_input_btn
    global join, sort, instrument_combobox, outputName_entry, outputPath_entry

    # Main container
    main_frame = ttk.Frame(parent, padding="16")
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
    input_frame.columnconfigure(0, weight=1)
    output_frame.columnconfigure(0, weight=1)

    # --- Input Section ---
    # File selection
    ttk.Label(input_frame, text="Database file(s):", style='Header.TLabel').grid(row=0, column=0, sticky='w', pady=(0,2))
    fileNames_entry = ttk.Entry(input_frame, width=24)
    fileNames_entry.grid(row=1, column=0, sticky='ew', pady=(0,5))
    ToolTip(fileNames_entry, TOOLTIPS['database_files'])

    browse_file_btn = ttk.Button(input_frame, text="Browse...", command=selectFiles, width=10)
    browse_file_btn.grid(row=1, column=1, padx=5)
    ToolTip(browse_file_btn, TOOLTIPS['database_files'])

    # Input path
    ttk.Label(input_frame, text="Input path:", style='Header.TLabel').grid(row=2, column=0, sticky='w', pady=(5,2))
    inputPath_entry = ttk.Entry(input_frame, width=24)
    inputPath_entry.grid(row=3, column=0, sticky='ew', pady=(0,5))
    set_disabled_style(inputPath_entry)
    ToolTip(inputPath_entry, TOOLTIPS['input_path'])

    browse_input_btn = ttk.Button(input_frame, text="Browse...", command=selectInputFolder, width=10)
    set_disabled_style(browse_input_btn)
    browse_input_btn.grid(row=3, column=1, padx=5)
    ToolTip(browse_input_btn, TOOLTIPS['input_path'])

    # Options
    join = BooleanVar(value=False)
    join_cb = ttk.Checkbutton(input_frame, text="Build database from a folder", variable=join, command=toggle_input_mode)
    join_cb.grid(row=4, column=0, sticky='w', pady=2)
    ToolTip(join_cb, TOOLTIPS['join_files'])

    sort = BooleanVar(value=False)
    sort_cb = ttk.Checkbutton(input_frame, text="Sort by time", variable=sort)
    sort_cb.grid(row=5, column=0, sticky='w', pady=2)
    ToolTip(sort_cb, TOOLTIPS['sort_time'])

    # Instrument (Seaguard/TSCP or HOBO): the two are never stackable, so the
    # database is built for one instrument at a time (.csv and .xlsx both read).
    # Auto-set from the selected files (detect_qualified_layout); still editable.
    ttk.Label(input_frame, text="Instrument:", style='Header.TLabel').grid(row=6, column=0, sticky='w', pady=(5,2))
    instrument_combobox = ttk.Combobox(input_frame, values=["Seaguard", "HOBO"], width=15, state='readonly')
    instrument_combobox.set("Seaguard")
    instrument_combobox.grid(row=7, column=0, sticky='w', pady=(0,5))
    ToolTip(instrument_combobox, TOOLTIPS['instrument'])

    # Recent selections: one click reopens the last database file choices
    global _recent_combobox
    ttk.Label(input_frame, text="Recent:", style='Header.TLabel').grid(row=8, column=0, sticky='w', pady=(5,2))
    _recent_combobox = ttk.Combobox(input_frame, state='readonly', width=45)
    _recent_combobox.grid(row=9, column=0, columnspan=2, sticky='ew', pady=(0,5))
    _recent_combobox.bind('<<ComboboxSelected>>', _apply_recent)
    ToolTip(_recent_combobox, "Recently used database file selections\n(pick one to fill the fields above)")
    _refresh_recent_combobox()

    # --- Output Section ---
    # Output naming
    ttk.Label(output_frame, text="Output name:", style='Header.TLabel').grid(row=0, column=0, sticky='w', pady=(0,2))
    outputName_entry = ttk.Entry(output_frame, width=24)
    outputName_entry.grid(row=1, column=0, sticky='ew', pady=(0,5))
    set_disabled_style(outputName_entry)
    ToolTip(outputName_entry, TOOLTIPS['output_name'])

    # Output path
    ttk.Label(output_frame, text="Output path:", style='Header.TLabel').grid(row=2, column=0, sticky='w', pady=(5,2))
    outputPath_entry = ttk.Entry(output_frame, width=24)
    outputPath_entry.grid(row=3, column=0, sticky='ew', pady=(0,5))
    ToolTip(outputPath_entry, TOOLTIPS['output_path'])

    browse_output_btn = ttk.Button(output_frame, text="Browse...", command=selectOutputFolder, width=10)
    browse_output_btn.grid(row=3, column=1, padx=5)
    ToolTip(browse_output_btn, TOOLTIPS['output_path'])

    # Database preview: build now and summarize (sites, period, rows) so the
    # user can confirm the selection BEFORE moving on; Next reuses the result
    global _preview_var
    preview_frame = ttk.LabelFrame(main_frame, text=" Database preview ", padding=12)
    preview_frame.grid(row=2, column=0, columnspan=2, padx=5, pady=5, sticky='ew')
    preview_frame.columnconfigure(1, weight=1)
    preview_btn = ttk.Button(preview_frame, text="Preview", command=preview_database, width=12)
    preview_btn.grid(row=0, column=0, sticky='nw', padx=(0, 12))
    ToolTip(preview_btn, "Builds the database now and shows a summary below\n"
                         "(sites, period, rows). 'Next >' reuses this build -\n"
                         "nothing is read twice.")
    _preview_var = StringVar(value="No preview yet - choose the files (or folder) and click Preview.")
    ttk.Label(preview_frame, textvariable=_preview_var, justify='left',
              style='Small.TLabel').grid(row=0, column=1, sticky='w')

    # Next button: validate + store, then advance to Step 2 in the same tab
    ttk.Button(main_frame, text="Next  >", command=_go_step2, style='Accent.TButton').grid(row=3, column=0, columnspan=2, pady=12, ipadx=12)

    # restore the user's latest choices
    restore_entry(fileNames_entry, USER_PREFS.get('dbv_database_file', ''))
    restore_entry(outputPath_entry, USER_PREFS.get('dbv_output_path', ''))
    restore_entry(inputPath_entry, USER_PREFS.get('dbv_input_path', ''))
    restore_entry(outputName_entry, USER_PREFS.get('dbv_output_name', ''))
    if USER_PREFS.get('dbv_instrument') in ('Seaguard', 'HOBO'):
        instrument_combobox.set(USER_PREFS['dbv_instrument'])
    sort.set(USER_PREFS.get('dbv_sort_by_time', False))
    toggle_input_mode()  # set the initial enabled/blank state (Output Name off)


db_build_messages = []  # unification messages, shown in the visualization log

def load_database():
    """Loads or builds the database via build_database (single unification
    engine); returns None (with a clear warning) on error."""
    global db_build_messages
    db_build_messages = []
    instrument = inputSettings.get('instrument', 'Seaguard')

    try:
        if inputSettings.get('joinFiles', False) == True:
            database, db_build_messages = data.build_database(instrument,
                                                              input_path=inputSettings['inputPath'])
        else:
            file_paths = [p.strip() for p in inputSettings.get('databaseFileName', '').split(';') if p.strip()]
            if not file_paths:
                messagebox.showerror("Error", "Select a database file or provide a valid input folder.")
                return None
            database, db_build_messages = data.build_database(instrument, file_list=file_paths)
    except ValueError as e:
        # the engine messages are already self-labeled ('build_database: ...')
        messagebox.showerror("Error", str(e))
        return None
    except Exception as e:
        messagebox.showerror("Error", "Could not build the database:\n%s" % e)
        return None
    # db_build_messages are shown in the Execution log by build_step2 (below),
    # so they are not printed here (that would duplicate them via the log redirect)

    if inputSettings.get('sortByTime', False) == True:
        # purely chronological order (the engine sorts by Site+Datetime)
        database = database.sort_values('Datetime', kind='stable')
        database.index = range(len(database))

    try:
        databaseViewPath = os.path.join(inputSettings['outputPath'], 'DatabaseView')
        os.makedirs(databaseViewPath, exist_ok=True)
        os.chdir(databaseViewPath)
    except Exception as e:
        messagebox.showerror("Error", "Could not create the output folder:\n%s\n\nDetails: %s" % (inputSettings.get('outputPath', ''), e))
        return None

    if inputSettings.get('joinFiles', False) == True:
        try:
            data.save_excel_autofit(database, inputSettings['outputFileName'] + '.xlsx')
            print('Info: unified database saved to %s.xlsx'
                  % os.path.join(databaseViewPath, inputSettings['outputFileName']))
        except Exception as e:
            print(f"Error saving database: {str(e)}")
    return database

def _current_source_label():
    """Human-readable description of the spreadsheet(s) the current database was
    read from, shown on the Generate-panels screen so the user knows exactly which
    data is loaded."""
    if inputSettings.get('joinFiles', False):
        name = (inputSettings.get('outputFileName', '') or '').strip()
        folder = os.path.basename(inputSettings.get('inputPath', '').rstrip('/\\'))
        if name and folder:
            return '%s.xlsx  (built from folder "%s")' % (name, folder)
        if name:
            return '%s.xlsx' % name
        return 'built from folder "%s"' % folder if folder else '(built database)'
    paths = [p.strip() for p in inputSettings.get('databaseFileName', '').split(';') if p.strip()]
    if len(paths) == 1:
        return os.path.basename(paths[0])
    if len(paths) > 1:
        return '%d files (%s, ...)' % (len(paths), os.path.basename(paths[0]))
    return '(unknown)'

def build_step2(parent):
    """Builds Step 2 (visualization settings) inside `parent`, a frame in the
    unified app's Visualization tab. Rebuilt fresh each time the user advances
    from Step 1. The root window and header are owned by the QCS_App shell."""
    global dType_combobox, panel1, panel2, panel3, panel1_cb, panel2_cb, panel3_cb
    global tsDiagram, ts_cb, latitude_entry, longitude_entry, tsParam_combobox
    global tendency, tendency_cb, tendency_entry, dataPoints, points_cb, fixedScale, fixed_scale_cb
    global year_vars, year_widgets, time_start_entry, time_end_entry, depth_min_entry, depth_max_entry
    global site_names, site_vars, site_widgets, parameter_names, parameter_vars, parameter_widgets
    global min_scale_entries, max_scale_entries, error_logger

    # Create main container with scrollbar
    container = ttk.Frame(parent)
    canvas = tk.Canvas(container, bg=theme.surface_color(), highlightthickness=0)
    scrollbar = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
    scrollable_frame = ttk.Frame(canvas)

    scrollable_frame.bind(
        "<Configure>",
        lambda e: canvas.configure(
            scrollregion=canvas.bbox("all")
        )
    )

    canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)

    container.pack(fill="both", expand=True)
    canvas.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")

    # Main frame inside scrollable area
    main_content_frame = ttk.Frame(scrollable_frame, padding=(12, 8))
    main_content_frame.pack(fill='both', expand=True)

    # Data settings frame
    data_frame = ttk.LabelFrame(main_content_frame, text=" Data settings ", padding=12)
    data_frame.grid(row=1, column=0, padx=5, pady=5, sticky="nsew")

    # Visualization frame
    vis_frame = ttk.LabelFrame(main_content_frame, text=" Visualization settings ", padding=12)
    vis_frame.grid(row=2, column=0, padx=5, pady=5, sticky="nsew")

    # Filter frame
    filter_frame = ttk.LabelFrame(main_content_frame, text=" Filter settings ", padding=12)
    filter_frame.grid(row=2, column=1, padx=5, pady=5, sticky="nsew")

    # Scale frame
    scale_frame = ttk.LabelFrame(main_content_frame, text=" Scale settings ", padding=12)
    scale_frame.grid(row=2, column=2, padx=5, pady=5, sticky="nsew")

    # Configure grid weights
    main_content_frame.columnconfigure(0, weight=1)
    main_content_frame.columnconfigure(1, weight=1)
    main_content_frame.columnconfigure(2, weight=1)
    main_content_frame.rowconfigure(1, weight=1)
    main_content_frame.rowconfigure(2, weight=1)

    # --- Data Settings ---
    # Data type (HOBO only has a time series: profile does not apply)
    ttk.Label(data_frame, text="Data type:").grid(row=0, column=0, sticky='w', pady=2)
    dType_values = ["mooring"] if is_hobo_input() else ["mooring", "profile"]
    dType_combobox = ttk.Combobox(data_frame, values=dType_values, width=25, state='readonly')
    dType_combobox.grid(row=1, column=0, sticky='w', pady=2)
    dType_combobox.bind("<<ComboboxSelected>>", lambda e: toggle_data_type())
    ToolTip(dType_combobox, TOOLTIPS['data_type'])

    # In the empty space to the right: which spreadsheet(s) this database was read
    # from, so the loaded source is always visible on the Generate-panels screen.
    ttk.Label(data_frame, text="Reading:").grid(row=0, column=1, sticky='w', padx=(28, 4), pady=2)
    ttk.Label(data_frame, text=_current_source_label(), style='Small.TLabel',
              wraplength=340, justify='left').grid(row=1, column=1, sticky='nw', padx=(28, 4), pady=2)

    # --- Visualization Settings ---
    # Panels: for HOBO the three checkboxes become the dedicated panels
    # (temperature / light+window / light multi-site) instead of Panel 1/2/3
    if is_hobo_input():
        panel_labels = ("HOBO Temperature (per site)",
                        "HOBO Light + fouling window (per site)",
                        "HOBO Light multi-site")
        panel_tips = (TOOLTIPS['hobo_temp'], TOOLTIPS['hobo_light'], TOOLTIPS['hobo_light_multi'])
    else:
        panel_labels = ("Parameters at a site",
                        "Parameter across sites",
                        "Vertical profile at a site")
        panel_tips = (TOOLTIPS['panel1'], TOOLTIPS['panel2'], TOOLTIPS['panel3'])

    ttk.Label(vis_frame, text="Select panels:").grid(row=0, column=0, sticky='w', pady=5)
    panel1 = BooleanVar(value=False)
    panel1_cb = ttk.Checkbutton(vis_frame, text=panel_labels[0], variable=panel1,
                               command=lambda: [toggle_panel_dependent_controls(), toggle_parameter_checkboxes()])
    panel1_cb.grid(row=1, column=0, sticky='w', pady=2)
    ToolTip(panel1_cb, panel_tips[0])

    panel2 = BooleanVar(value=False)
    panel2_cb = ttk.Checkbutton(vis_frame, text=panel_labels[1], variable=panel2,
                               command=lambda: [toggle_panel_dependent_controls(), toggle_parameter_checkboxes()])
    panel2_cb.grid(row=2, column=0, sticky='w', pady=2)
    ToolTip(panel2_cb, panel_tips[1])

    panel3 = BooleanVar(value=False)
    panel3_cb = ttk.Checkbutton(vis_frame, text=panel_labels[2], variable=panel3,
                               command=lambda: [toggle_panel_dependent_controls(), toggle_parameter_checkboxes()])
    panel3_cb.grid(row=3, column=0, sticky='w', pady=2)
    ToolTip(panel3_cb, panel_tips[2])

    # TS Diagram
    tsDiagram = BooleanVar(value=False)
    ts_cb = ttk.Checkbutton(vis_frame, text="T-S diagram", variable=tsDiagram, command=toggle_ts_controls)
    ts_cb.grid(row=4, column=0, sticky='w', pady=5)
    ToolTip(ts_cb, TOOLTIPS['ts_diagram'])

    # Coordinates
    _FIELD_W = 18   # compact width for the coordinate boxes (short values)
    ttk.Label(vis_frame, text="Latitude:").grid(row=5, column=0, sticky='w', pady=2)
    latitude_entry = ttk.Entry(vis_frame, width=_FIELD_W)
    latitude_entry.grid(row=6, column=0, sticky='w', pady=2)
    set_disabled_style(latitude_entry)
    ToolTip(latitude_entry, TOOLTIPS['latitude'])

    ttk.Label(vis_frame, text="Longitude:").grid(row=7, column=0, sticky='w', pady=2)
    longitude_entry = ttk.Entry(vis_frame, width=_FIELD_W)
    longitude_entry.grid(row=8, column=0, sticky='w', pady=2)
    set_disabled_style(longitude_entry)
    ToolTip(longitude_entry, TOOLTIPS['longitude'])

    # TS Parameters
    ttk.Label(vis_frame, text="T-S parameters:").grid(row=9, column=0, sticky='w', pady=2)
    tsParam_combobox = ttk.Combobox(vis_frame, values=["Conservative T & Absolute S", "Potential T & Practical S"], width=_FIELD_W, state='readonly')
    tsParam_combobox.grid(row=10, column=0, sticky='w', pady=2)
    set_disabled_style(tsParam_combobox)
    ToolTip(tsParam_combobox, TOOLTIPS['ts_params'])
    # Match the combobox to the SMALLER lat/long boxes (the arrow otherwise makes
    # it wider). Shrink its char width until its requested pixel width fits the
    # entry's - DPI-independent, no guessing.
    latitude_entry.update_idletasks()
    _target = latitude_entry.winfo_reqwidth()
    _w = _FIELD_W
    while _w > 6:
        tsParam_combobox.configure(width=_w)
        tsParam_combobox.update_idletasks()
        if tsParam_combobox.winfo_reqwidth() <= _target:
            break
        _w -= 1
    # close the last few pixels (char widths are discrete) so it matches exactly
    _gap = _target - tsParam_combobox.winfo_reqwidth()
    if _gap > 0:
        tsParam_combobox.grid_configure(ipadx=_gap // 2)

    # The box itself stays narrow (matched to lat/long above), but its narrow
    # char width would also clip the DROP-DOWN list. Widen only the popdown
    # listbox to fit the longest option so the choices are fully readable.
    def _widen_ts_popup(_event=None):
        try:
            popdown = tsParam_combobox.tk.call(
                'ttk::combobox::PopdownWindow', str(tsParam_combobox))
            longest = max((len(v) for v in tsParam_combobox.cget('values')), default=20)
            tsParam_combobox.tk.call('%s.f.l' % popdown, 'configure', '-width', longest + 2)
        except Exception:
            pass
    # re-apply after ttk's own post handler runs (after_idle wins the ordering)
    tsParam_combobox.bind('<Button-1>',
                          lambda e: tsParam_combobox.after_idle(_widen_ts_popup), add='+')
    _widen_ts_popup()

    # Display options
    ttk.Label(vis_frame, text="Display options:").grid(row=0, column=1, sticky='w', pady=5)

    tendency = BooleanVar(value=False)
    tendency_cb = ttk.Checkbutton(vis_frame, text="Trend lines", variable=tendency, 
                                 command=lambda: [set_enabled_style(tendency_entry) if tendency.get() else set_disabled_style(tendency_entry)])
    tendency_cb.grid(row=1, column=1, sticky='w', pady=2)
    ToolTip(tendency_cb, TOOLTIPS['tendency'])

    ttk.Label(vis_frame, text="Degree:").grid(row=2, column=1, sticky='w', pady=2)
    tendency_entry = ttk.Entry(vis_frame, width=28)
    tendency_entry.grid(row=3, column=1, sticky='w', pady=2)
    set_disabled_style(tendency_entry)
    ToolTip(tendency_entry, TOOLTIPS['tendency_degree'])

    dataPoints = BooleanVar(value=False)
    points_cb = ttk.Checkbutton(vis_frame, text="Show data points", variable=dataPoints)
    points_cb.grid(row=4, column=1, sticky='w', pady=5)
    ToolTip(points_cb, TOOLTIPS['data_points'])

    fixedScale = BooleanVar(value=False)
    fixed_scale_cb = ttk.Checkbutton(vis_frame, text="Fixed scale", variable=fixedScale, command=toggle_scale_controls)
    fixed_scale_cb.grid(row=5, column=1, sticky='w', pady=5)
    ToolTip(fixed_scale_cb, TOOLTIPS['fixed_scale'])

    # X-axis time window (mooring plots)
    ttk.Label(vis_frame, text="X-axis start (mooring):").grid(row=6, column=1, sticky='w', pady=(8,2))
    time_start_entry = ttk.Entry(vis_frame, width=28)
    time_start_entry.grid(row=7, column=1, sticky='w', pady=2)
    ToolTip(time_start_entry, TOOLTIPS['time_start'])

    ttk.Label(vis_frame, text="X-axis end (mooring):").grid(row=8, column=1, sticky='w', pady=2)
    time_end_entry = ttk.Entry(vis_frame, width=28)
    time_end_entry.grid(row=9, column=1, sticky='w', pady=2)
    ToolTip(time_end_entry, TOOLTIPS['time_end'])

    # shows the period covered by the loaded database, so the user does not
    # need to open the spreadsheet to know which days were sampled
    data_start = database['Datetime'].min()
    data_end = database['Datetime'].max()
    if pd.notna(data_start) and pd.notna(data_end):
        coverage_text = "Data available: %s to %s" % (data_start.strftime('%d/%m/%Y %H:%M'),
                                                      data_end.strftime('%d/%m/%Y %H:%M'))
    else:
        coverage_text = "Data available: unknown (invalid dates)"
    ttk.Label(vis_frame, text=coverage_text, style='Small.TLabel').grid(
        row=10, column=1, sticky='w', pady=(0,2))

    # Depth-axis range (profile plots) - analogous to the time window above
    ttk.Label(vis_frame, text="Depth-axis min (profile):").grid(row=11, column=1, sticky='w', pady=(10,2))
    depth_min_entry = ttk.Entry(vis_frame, width=28)
    depth_min_entry.grid(row=12, column=1, sticky='w', pady=2)
    ToolTip(depth_min_entry, TOOLTIPS['depth_min'])

    ttk.Label(vis_frame, text="Depth-axis max (profile):").grid(row=13, column=1, sticky='w', pady=2)
    depth_max_entry = ttk.Entry(vis_frame, width=28)
    depth_max_entry.grid(row=14, column=1, sticky='w', pady=2)
    ToolTip(depth_max_entry, TOOLTIPS['depth_max'])

    # shows the depth range covered by the loaded database (same single-line
    # format as the "Data available" label above)
    if 'Depth (m)' in database.columns and database['Depth (m)'].notna().any():
        depth_text = "Depth available: %.2f to %.2f m" % (database['Depth (m)'].min(),
                                                          database['Depth (m)'].max())
    else:
        depth_text = "Depth available: no depth column"
    ttk.Label(vis_frame, text=depth_text, style='Small.TLabel').grid(
        row=15, column=1, sticky='w', pady=(2,5))

    # --- Filter Settings ---
    # Year filter: one checkbox per year actually present in the database
    ttk.Label(filter_frame, text="Filter by year:").grid(row=0, column=0, sticky='w', pady=(5,2))
    available_years = sorted(set(int(y) for y in database['Datetime'].dt.year.dropna().unique()))
    year_vars = {}    # BooleanVar for each year
    year_widgets = {} # Checkbutton for each year
    row_n = 1
    for db_year in available_years:
        var = BooleanVar(value=False)
        # changing the Year filter re-computes the auto scale defaults (their
        # range spans the selected years)
        cb = ttk.Checkbutton(filter_frame, text=str(db_year), variable=var,
                             command=_refresh_scale_defaults)
        cb.grid(row=row_n, column=0, sticky='w', pady=2)
        ToolTip(cb, TOOLTIPS['filter_year'])
        year_vars[db_year] = var
        year_widgets[db_year] = cb
        row_n += 1

    # Site selection
    site_lbl = ttk.Label(filter_frame, text="Filter by site:")
    site_lbl.grid(row=row_n, column=0, sticky='w', pady=(10,2))
    ToolTip(site_lbl, TOOLTIPS['site_filter'])
    row_n += 1

    site_names = sorted(set(database['Site']))
    site_vars = {}  # Stores the BooleanVar
    site_widgets = {}  # Stores the Checkbutton widgets

    for site in site_names:
        var = BooleanVar(value=False)
        # changing the Site filter re-computes the auto scale defaults
        cb = ttk.Checkbutton(filter_frame, text=site, variable=var,
                             command=_refresh_scale_defaults)
        cb.grid(row=row_n, column=0, sticky='w', pady=2)
        site_vars[site] = var
        site_widgets[site] = cb
        row_n += 1

    # Parameter selection lives in its OWN sub-frame, so its rows are independent
    # of the Year/Site rows in column 0 (whose section labels have their own
    # spacing) and can be height-matched 1:1 with the Scale-settings rows.
    param_col = ttk.Frame(filter_frame)
    param_col.grid(row=0, column=1, rowspan=99, sticky='nw')
    param_lbl = ttk.Label(param_col, text="Select parameters:")
    param_lbl.grid(row=0, column=0, sticky='w', pady=(5,2), padx=10)
    ToolTip(param_lbl, TOOLTIPS['param_filter'])

    # Parameters come in TWO groups: the MAIN group (checked by default on every
    # new import, whenever the data carries them) and a SECONDARY group of
    # rarely-used variables that ALWAYS start unchecked (still available manually).
    if inputSettings.get('instrument', 'Seaguard') == 'HOBO':
        # HOBO only measures temperature and light
        main_params = ['Temperature (degC)', 'Luminosity (lux)']
        secondary_params = []
    else:
        main_params = ['Temperature (degC)', 'Salinity (PSU)', 'CO2 level (ppm)',
                       'O2 level (uM)', 'PAR (umol/m2/s)', 'Turbidity (FTU)',
                       'Chlorophyll (ug/L)', 'pH', 'Dissolved organic matter (ppb)']
        secondary_params = ['Conductivity (mS/cm)', 'Density (kg/m3)',
                            'Soundspeed (m/s)', 'Pressure (dbar)']
    parameter_names = main_params + secondary_params
    parameter_vars = {}  # Stores the BooleanVar
    parameter_widgets = {}  # Stores the Checkbutton widgets

    def _param_display(param):
        # GUI label only - the data column keeps its original name
        return param.replace(' level', '')

    # parameters this database actually carries data for (a column present with at
    # least one non-null value) - used as the default selection and for defaults
    params_with_data = [p for p in parameter_names
                        if p in database.columns and database[p].notna().any()]

    # the checkboxes and the Scale-settings rows are built with the SAME row
    # numbering (including the group separator), so each Min/Max line can sit
    # exactly beside its parameter
    prow = 1
    for param in parameter_names:
        if secondary_params and param == secondary_params[0]:
            sep_lbl = ttk.Label(param_col, text="Rarely used:", style='Small.TLabel')
            sep_lbl.grid(row=prow, column=0, sticky='w', pady=(8, 2), padx=10)
            ToolTip(sep_lbl, TOOLTIPS['param_secondary'])
            prow += 1
        var = BooleanVar(value=False)
        # toggling a parameter updates its per-parameter scale row (enable/fill/clear)
        cb = ttk.Checkbutton(param_col, text=_param_display(param), variable=var,
                             command=toggle_scale_controls)
        cb.grid(row=prow, column=0, sticky='w', pady=2, padx=10)
        parameter_vars[param] = var
        parameter_widgets[param] = cb
        set_disabled_style(cb)  # Initially disabled
        prow += 1

    # --- Scale Settings ---
    # Headers for the scale columns
    scale_hdr = ttk.Label(scale_frame, text="Parameter")
    scale_hdr.grid(row=0, column=0, sticky='w', padx=5)
    ttk.Label(scale_frame, text="Min").grid(row=0, column=1, sticky='w', padx=5)
    ttk.Label(scale_frame, text="Max").grid(row=0, column=2, sticky='w', padx=5)

    # Dictionaries to store the scale entry widgets
    min_scale_entries = {}
    max_scale_entries = {}

    # Create entries for each parameter - SAME row numbering as the parameter
    # checkboxes (including the "Rarely used:" separator), so the two frames can
    # be aligned line by line
    srow = 1
    for param in parameter_names:
        if secondary_params and param == secondary_params[0]:
            ttk.Label(scale_frame, text="Rarely used:", style='Small.TLabel').grid(
                row=srow, column=0, sticky='w', pady=(8, 2), padx=5)
            srow += 1
        # Parameter label
        ttk.Label(scale_frame, text=_param_display(param)).grid(row=srow, column=0, sticky='w', pady=2, padx=5)

        # editing a scale field marks it user-owned, so a later Site/Year change
        # does not overwrite it with a recomputed default
        _untrack = (lambda p: (lambda e: _auto_scale.discard(p)))(param)

        # Entry for minimum value
        min_entry = ttk.Entry(scale_frame, width=10)
        min_entry.grid(row=srow, column=1, sticky='w', pady=2, padx=5)
        min_entry.bind('<KeyRelease>', _untrack)
        min_scale_entries[param] = min_entry
        set_disabled_style(min_entry)
        ToolTip(min_entry, TOOLTIPS['min_scale'])

        # Entry for maximum value
        max_entry = ttk.Entry(scale_frame, width=10)
        max_entry.grid(row=srow, column=2, sticky='w', pady=2, padx=5)
        max_entry.bind('<KeyRelease>', _untrack)
        max_scale_entries[param] = max_entry
        set_disabled_style(max_entry)
        ToolTip(max_entry, TOOLTIPS['max_scale'])
        srow += 1

    # Align the two frames line by line: a Checkbutton and an Entry have different
    # natural heights, which otherwise accumulates a visible offset down the list.
    # Force every parameter row (and the header row) to the SAME height in the
    # checkbox column and in the Scale frame, so each Min/Max sits beside its
    # parameter checkbox.
    param_col.update_idletasks()
    row_h = max(next(iter(parameter_widgets.values())).winfo_reqheight(),
                next(iter(min_scale_entries.values())).winfo_reqheight()) + 4  # + 2*pady
    hdr_h = max(param_lbl.winfo_reqheight() + 7,   # pady=(5,2)
                scale_hdr.winfo_reqheight())
    param_col.grid_rowconfigure(0, minsize=hdr_h)
    scale_frame.grid_rowconfigure(0, minsize=hdr_h)
    for r in range(1, srow):
        param_col.grid_rowconfigure(r, minsize=row_h)
        scale_frame.grid_rowconfigure(r, minsize=row_h)

    # Configure grid weights for filter frame
    filter_frame.columnconfigure(0, weight=1)
    filter_frame.columnconfigure(1, weight=1)

    # Configure grid weights for scale frame
    scale_frame.columnconfigure(0, weight=1)
    scale_frame.columnconfigure(1, weight=1)
    scale_frame.columnconfigure(2, weight=1)

    # Action buttons
    action_frame = ttk.Frame(scrollable_frame)
    action_frame.pack(pady=10)

    ttk.Button(action_frame, text="<  Back", command=_go_step1).pack(side='left', padx=5)
    # 'Generate panels' already saves the current choices, so no separate Save button
    ttk.Button(action_frame, text="Generate panels", command=generatePanels, style='Accent.TButton').pack(side='left', padx=5)

    # Initialize UI state
    toggle_all_controls(enabled=False)  # Everything disabled initially
    toggle_data_type()
    toggle_panel_dependent_controls()
    toggle_parameter_checkboxes()
    toggle_ts_controls()

    # restore the last visualization choices (checkboxes, selections and scales)
    panel1.set(USER_PREFS.get('dbv_panel1', False))
    panel2.set(USER_PREFS.get('dbv_panel2', False))
    panel3.set(USER_PREFS.get('dbv_panel3', False))
    # T-S does not exist for HOBO (no salinity): never restore it checked
    tsDiagram.set(False if is_hobo_input() else USER_PREFS.get('dbv_ts_diagram', False))
    tendency.set(USER_PREFS.get('dbv_tendency', False))
    dataPoints.set(USER_PREFS.get('dbv_data_points', False))
    fixedScale.set(USER_PREFS.get('dbv_fixed_scale', False))
    for site in USER_PREFS.get('dbv_selected_sites', []):
        if site in site_vars:
            site_vars[site].set(True)
    for y in USER_PREFS.get('dbv_selected_years', []):
        if y in year_vars:
            year_vars[y].set(True)
    # Year/Site: default to the FIRST available (and, if there is only one, it is
    # selected by definition) when nothing valid was restored for this database.
    if not any(v.get() for v in year_vars.values()) and available_years:
        year_vars[available_years[0]].set(True)
    if not any(v.get() for v in site_vars.values()) and site_names:
        site_vars[site_names[0]].set(True)
    # Parameters: default to the MAIN-group ones that actually HAVE data in this
    # database (recomputed per imported sheet; NOT persisted between sessions).
    # SECONDARY parameters (rarely used) always start unchecked.
    for param, var in parameter_vars.items():
        var.set(param in params_with_data and param not in secondary_params)
    # Scale settings are per-sheet too: not restored from preferences.
    restore_entry(time_start_entry, USER_PREFS.get('dbv_time_start', ''))
    restore_entry(time_end_entry, USER_PREFS.get('dbv_time_end', ''))
    restore_entry(depth_min_entry, USER_PREFS.get('dbv_depth_min', ''))
    restore_entry(depth_max_entry, USER_PREFS.get('dbv_depth_max', ''))
    restore_entry(latitude_entry, USER_PREFS.get('dbv_latitude', ''))
    restore_entry(longitude_entry, USER_PREFS.get('dbv_longitude', ''))
    restore_entry(tendency_entry, USER_PREFS.get('dbv_degree', ''))
    if USER_PREFS.get('dbv_ts_param'):
        tsParam_combobox.set(USER_PREFS['dbv_ts_param'])
    # Data type: if a qualification handed it over, use it and LOCK the field
    # (the qualified file already IS a profile / mooring / HOBO, so choosing the
    # wrong one would only cause errors); otherwise restore the last choice.
    global _pending_step2
    handoff_type = _pending_step2.get('data_type')
    if is_hobo_input():
        dType_combobox.set('mooring')
        dType_combobox.config(state='disabled')  # HOBO has only one option
        toggle_data_type()
    elif handoff_type in dType_values:
        dType_combobox.set(handoff_type)
        dType_combobox.config(state='disabled')  # locked: comes from the file
        toggle_data_type()
    elif USER_PREFS.get('dbv_data_type') in dType_values:
        dType_combobox.set(USER_PREFS['dbv_data_type'])
        toggle_data_type()

    # coordinates from the qualification region (the file does not store them);
    # when present they LOCK the lat/long fields (read-only) - see toggle_ts_controls
    global _coords_from_handoff
    _coords_from_handoff = (_pending_step2.get('latitude') is not None
                            or _pending_step2.get('longitude') is not None)
    if _pending_step2.get('latitude') is not None:
        restore_entry(latitude_entry, str(_pending_step2['latitude']))
    if _pending_step2.get('longitude') is not None:
        restore_entry(longitude_entry, str(_pending_step2['longitude']))

    # X-axis start/end default to the first/last available date (mooring plots).
    # A saved value is kept only if it falls inside this database's range (a value
    # left over from another database would plot an empty window).
    def _default_time(entry, default_dt):
        if pd.isna(default_dt) or str(entry.cget('state')) == 'disabled':
            return
        cur = entry.get().strip()
        keep = False
        if cur:
            try:
                cv = pd.to_datetime(cur, dayfirst=True)
                keep = pd.notna(cv) and data_start <= cv <= data_end
            except Exception:
                keep = False
        if not keep:
            entry.delete(0, END)
            entry.insert(0, default_dt.strftime('%d/%m/%Y %H:%M'))

    _default_time(time_start_entry, data_start)
    _default_time(time_end_entry, data_end)

    _pending_step2 = {}  # consumed

    # Execution log: in the unified app this is the ONE shell-owned panel at the
    # bottom of the window (same position/styling in every pipeline stage);
    # standalone dev launches create their own inside the scroll area.
    global _db_msgs_logged
    if _shared_log is not None:
        error_logger = _shared_log
    else:
        error_logger = ErrorLogger(scrollable_frame)
        # route printed output into this window's log (flushes any buffered
        # startup messages)
        _out.set_sink(error_logger.log)
    if not _db_msgs_logged:  # skip if the Step 1 preview already logged them
        for message in db_build_messages:
            error_logger.log(message)
        _db_msgs_logged = True

    # Configure canvas scrolling: only while the cursor is over this canvas
    # (a raw bind_all would also capture the wheel on the Qualification tab,
    # since in the unified app both tabs stay mapped)
    theme.enable_mousewheel(canvas)


# --- Two-step wizard inside a single tab (Step 1 <-> Step 2 swap) ---
_viz_root = None
_step1_frame = None
_step2_frame = None
_shared_log = None        # app-wide Execution log (owned by the QCS_App shell)
_db_msgs_logged = False   # True once db_build_messages went to the log (no dupes)
_recent_combobox = None   # Step 1 'Recent' picker (created in build_step1)
_preview_var = None       # Step 1 preview summary text (created in build_step1)
_input_mode_cache = {}    # stashes Database File(s) while folder-scan mode is on
_auto_scale = set()       # params whose Min/Max still hold auto-computed defaults
_field_cache = {}         # stashes X-axis / depth values while their mode is off,
                          # so they come back when that data type is selected again
_coords_from_handoff = False  # True when lat/long came from a qualification region
                              # (then they stay locked/read-only; editable otherwise)
# handed over from a qualification run (via apply_pending_prefill) and consumed
# by build_step2: the data type (profile/mooring/hobo) and the region coordinates,
# which the qualified file does not store. Locks Data type and fills lat/long.
_pending_step2 = {}

# database built by 'Preview' on Step 1, reused by Next if the settings match
_preview_cache = {'key': None, 'database': None}

def _settings_key():
    """Snapshot of the Step 1 settings that define the database content."""
    return (inputSettings.get('databaseFileName', ''),
            inputSettings.get('joinFiles', False),
            inputSettings.get('inputPath', ''),
            inputSettings.get('sortByTime', False),
            inputSettings.get('instrument', ''))

def _summarize_database(db):
    """One-paragraph summary shown in the Step 1 preview panel."""
    sites = sorted(set(db['Site'].dropna().astype(str))) if 'Site' in db.columns else []
    shown = ', '.join(sites[:8]) + ('…' if len(sites) > 8 else '')
    t0, t1 = db['Datetime'].min(), db['Datetime'].max()
    n_src = db['Source file'].nunique() if 'Source file' in db.columns else '-'
    return ("Rows: %s    Sites: %d (%s)\n"
            "Period: %s  to  %s    Source files: %s    Messages: %d (Execution log)"
            % ('{:,}'.format(len(db)), len(sites), shown,
               t0.strftime('%d/%m/%Y %H:%M'), t1.strftime('%d/%m/%Y %H:%M'),
               n_src, len(db_build_messages)))

def preview_database():
    """Builds the database now and shows its summary WITHOUT leaving Step 1, so
    the user can confirm the right files were picked. The result is cached and
    reused by Next (no double build) while the settings stay the same."""
    global _db_msgs_logged
    inputSettings.clear()
    if not saveInputSettings():
        return  # validation failed (a warning was already shown)
    db = load_database()
    if db is None:
        _preview_var.set("Preview failed - see the message.")
        return
    _preview_cache['key'] = _settings_key()
    _preview_cache['database'] = db
    for message in db_build_messages:
        print(message)  # goes to the shared Execution log
    _db_msgs_logged = True
    _preview_var.set(_summarize_database(db))

def _update_recents():
    """Keeps the last file selections in USER_PREFS for one-click reopening."""
    if inputSettings.get('joinFiles', False):
        return  # folder-scan mode: nothing file-based to remember
    files = inputSettings.get('databaseFileName', '').strip()
    if not files:
        return
    entry = {'files': files, 'instrument': inputSettings.get('instrument', 'Seaguard')}
    recents = [r for r in USER_PREFS.get('dbv_recent', []) if r.get('files') != files]
    recents.insert(0, entry)
    USER_PREFS['dbv_recent'] = recents[:8]
    save_user_prefs()
    _refresh_recent_combobox()

def _recent_display(entry):
    names = ', '.join(os.path.basename(f) for f in entry['files'].split(';') if f)
    if len(names) > 70:
        names = names[:67] + '…'
    return '%s   [%s]' % (names, entry.get('instrument', '?'))

def _refresh_recent_combobox():
    if _recent_combobox is None:
        return
    _recent_combobox['values'] = [_recent_display(r) for r in USER_PREFS.get('dbv_recent', [])]

def _apply_recent(event=None):
    """Fills Step 1 from the picked recent selection."""
    idx = _recent_combobox.current()
    recents = USER_PREFS.get('dbv_recent', [])
    if idx < 0 or idx >= len(recents):
        return
    entry = recents[idx]
    join.set(False)
    toggle_input_mode()
    restore_entry(fileNames_entry, entry['files'])
    if entry.get('instrument') in ('Seaguard', 'HOBO'):
        instrument_combobox.set(entry['instrument'])

def apply_pending_prefill(info):
    """Pre-fill Step 1 from a just-finished qualification (called by the QCS_App
    shell when the user switches to the Visualization tab). info holds
    {'file', 'out_root', 'instrument'}. Ensures Step 1 is showing."""
    if not info or globals().get('fileNames_entry') is None:
        return
    try:
        if _step2_frame is not None and _step2_frame.winfo_ismapped():
            _go_step1()   # come back from Step 2 so the fields are visible
    except Exception:
        pass
    restore_entry(fileNames_entry, info.get('file', ''))
    restore_entry(outputPath_entry, info.get('out_root', ''))
    # remember an output name for the folder-build mode; the visible field stays
    # blank/disabled in single-file mode (handled by toggle_input_mode)
    USER_PREFS['dbv_output_name'] = os.path.splitext(os.path.basename(info.get('file', '')))[0]
    if info.get('instrument') in ('Seaguard', 'HOBO'):
        instrument_combobox.set(info['instrument'])
    # stash the data type + coordinates for build_step2 (the file lacks them)
    global _pending_step2
    _pending_step2 = {'data_type': info.get('data_type'),
                      'latitude': info.get('latitude'),
                      'longitude': info.get('longitude')}
    join.set(False)
    toggle_input_mode()
    _preview_cache['key'] = None   # force a rebuild for the new selection
    print('Info: Visualization pre-selected the just-qualified file: %s'
          % os.path.basename(info.get('file', '')))

def _go_step2():
    """Next: validate Step 1, build the database (or reuse the previewed one),
    then show Step 2 in place."""
    global database, _db_msgs_logged
    inputSettings.clear()
    if not saveInputSettings():
        return  # validation failed (a warning was already shown)
    if (_preview_cache['database'] is not None
            and _preview_cache['key'] == _settings_key()):
        database = _preview_cache['database']  # already built by Preview
    else:
        _db_msgs_logged = False
        database = load_database()
    if database is None:
        return  # error already shown; stay on Step 1
    _update_recents()
    dataViewSettings.clear()
    for child in _step2_frame.winfo_children():
        child.destroy()  # rebuild Step 2 fresh for the new database
    build_step2(_step2_frame)
    _step1_frame.pack_forget()
    _step2_frame.pack(fill='both', expand=True)

def _go_step1():
    """Back: return to Step 1 to pick another database."""
    for child in _step2_frame.winfo_children():
        child.destroy()
    _step2_frame.pack_forget()
    _step1_frame.pack(fill='both', expand=True)

def build_visualization_tab(container, root, shared_log=None):
    """Builds the Data Visualization UI inside `container` (a frame in the
    unified app's notebook). Hosts the Step 1 <-> Step 2 wizard as two stacked
    frames swapped by the Next/Back buttons. `root` is the shared Tk root;
    `shared_log` is the app-wide Execution log owned by the QCS_App shell."""
    global _viz_root, _step1_frame, _step2_frame, _shared_log
    _viz_root = root
    _shared_log = shared_log
    _step1_frame = ttk.Frame(container)
    _step2_frame = ttk.Frame(container)
    _step1_frame.pack(fill='both', expand=True)  # start on Step 1
    build_step1(_step1_frame)


if __name__ == '__main__':
    # Standalone dev launch (the shipped entry point is QCS_App.py).
    theme.enable_high_dpi()
    _root = Tk()
    _root.title("QCS - Data Visualization %s" % data.QCS_VERSION)
    theme.set_scaled_geometry(_root, 1380, 800, min_width=1150, min_height=650)
    theme.apply_theme(_root, USER_PREFS.get('ui_theme', 'light'))
    theme.set_window_icon(_root)
    _frame = ttk.Frame(_root)
    _frame.pack(fill='both', expand=True)
    build_visualization_tab(_frame, _root)
    _root.mainloop()
    os.chdir(rootPath)

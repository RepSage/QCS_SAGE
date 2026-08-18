import os
import re
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

# Tooltips dictionary - editorial standard in QCS_Main.py (v11.6.1)
TOOLTIPS = {
    'database_files': "Qualified file(s) or database(s) to visualize\nSeveral files are combined, validated and deduplicated",
    'join_files': "Sweeps a whole folder tree instead of picking files one by one:\nfinds every 'QCS qualified ... data' subfolder, skips report files\nand combines everything into one database\n(selecting several files above already joins them)",
    'sort_time': "Order of the site blocks in the database built from several\n"
                 "files: by each site's first sample instead of alphabetically\n"
                 "Sites are never interleaved and rows stay chronological\n"
                 "within each site",
    'instrument': "Instrument family of the qualified files\nSeaguard (TSCP) and HOBO tables are never stackable -\nbuild separate databases",
    'output_name': "Base name of the database file",
    'input_path': "Folder with the input files",
    'output_path': "Folder for the outputs",
    'data_type': "Collection type: TSCP Mooring, TSCP Profile or TSCP Doppler\n(same naming as the qualification Data type)\nA HOBO database is shown as HOBO",
    'filter_year': "Year(s) to visualize\nPanels are generated once per selected year",
    'time_start': "Optional: start of the time axis in mooring plots\n(DD/MM/YYYY HH:MM, e.g. 15/04/2019 09:00); empty = fit the data\nCross-site panels keep the time of day: day offset + clock time\napply to each site's own days",
    'time_end': "Optional: end of the time axis in mooring plots\n(DD/MM/YYYY HH:MM, e.g. 16/04/2019 09:00); empty = fit the data\nCross-site panels keep the time of day: day offset + clock time\napply to each site's own days",
    'depth_min': "Optional: upper limit of the depth axis in profile plots (m)\nEmpty = fit the data",
    'depth_max': "Optional: lower limit of the depth axis in profile plots (m)\nEmpty = fit the data",
    'panel1': "Panel 1: parameters compared at the same site",
    'panel2': "Panel 2: one parameter compared between sites",
    'panel3': "Panel 3: parameters compared at the same site (vertical profile)",
    'hobo_params_site': "Temperature/light at one site, one figure per site,\nall selected years in a single plot\nLight is drawn as its daily-peak envelope with the fouling window\nshaded; SUSPECT/BAD temperature is highlighted",
    'hobo_params_across': "One figure per parameter, all sites together,\naligned by time of day (hours since each site's first midnight)\nLight uses the daily-peak envelope; each site's fouling cutoff\nis marked",
    'ts_diagram': "Temperature-Salinity (T-S) diagram: temperature vs salinity with\ndepth as the color, to identify water masses",
    'latitude': "Latitude for the T-S diagram (gsw)\nPre-filled from the qualification region and locked; editable only\nfor a standalone file (which stores no coordinates)",
    'longitude': "Longitude for the T-S diagram (gsw)\nPre-filled from the qualification region and locked; editable only\nfor a standalone file (which stores no coordinates)",
    'ts_params': "Temperature & salinity pair for the T-S diagram:\nConservative T & Absolute S (TEOS-10, uses lat/long) or\nPotential T & Practical S (classic EOS-80)",
    'tendency': "Adds regression lines to the plots",
    'tendency_degree': "Degree of the regression polynomial (1 = straight line)",
    'data_points': "Draws the individual data points on the plots",
    'disagreement_bars': "HOBO only: one vertical bar per sample on the temperature\n"
                         "series, showing how far the replicates disagreed\n"
                         "(bar = max - min, centered on the plotted mean)\n"
                         "Only combined-replicate databases carry that spread",
    'site_filter': "Sites to include in the plots",
    'param_filter': "Parameters to include in the plots",
    'param_secondary': "Rarely-used variables, always start unchecked\n(check manually when needed)",
    'fixed_scale': "Same y-axis scale on every plot, for direct comparison",
    'min_scale': "Lower limit of this parameter's fixed scale\nDefault: smallest approved value (flags 1/2) of the current\nSite/Year selection, minus 20% - floored at 0",
    'max_scale': "Upper limit of this parameter's fixed scale\nDefault: largest approved value (flags 1/2) of the current\nSite/Year selection, plus 20%"
}

class ErrorLogger(theme.LogConsole):
    """Execution log (shared theme console), positioned via pack."""

    def __init__(self, parent):
        super().__init__(parent, title=" Execution log ", height=8)
        self.frame.pack(fill='both', expand=True, padx=5, pady=5)


# ----- user preferences: shared with QCS_Main (same json file) -----
# ----- UI facade (v12.0 Qt port): the WORKFLOW functions talk to the user
# only through these hooks; the Qt shell assigns its own implementations.
# GUI-side callbacks (browse, help) keep calling messagebox directly.
def ui_info(title, message):
    messagebox.showinfo(title, message)

def ui_warn(title, message):
    messagebox.showwarning(title, message)

def ui_error(title, message):
    messagebox.showerror(title, message)

def settings_store_path():
    # must resolve IDENTICALLY to QCS_Main.settings_store_path - both tabs
    # write the same json - so both delegate to theme.writable_app_dir (v11.2:
    # falls back to %APPDATA%\QCS when the install dir is read-only)
    return os.path.join(theme.writable_app_dir(), 'qcs_user_settings.json')

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
# operator plot colors, saved per parameter (v12.0): every plot reads them
# through view.getParamColors
view.PARAM_COLOR_OVERRIDES.update(USER_PREFS.get('dbv_param_colors', {}))

def set_param_color(param, color):
    """Sets (or clears, with color=None) a parameter's plot color and
    persists it. Toolkit-free: both shells call this."""
    if color:
        view.PARAM_COLOR_OVERRIDES[param] = color
    else:
        view.PARAM_COLOR_OVERRIDES.pop(param, None)
    USER_PREFS['dbv_param_colors'] = dict(view.PARAM_COLOR_OVERRIDES)
    save_user_prefs()

def reset_param_colors():
    """Drops EVERY operator color override, so all parameters go back to the
    program defaults. Toolkit-free: both shells call this."""
    view.PARAM_COLOR_OVERRIDES.clear()
    USER_PREFS['dbv_param_colors'] = {}
    save_user_prefs()

def param_color(param):
    """The color a parameter is currently plotted with (override or default)."""
    cParam, _bc = view.getParamColors()
    return view.PARAM_COLOR_OVERRIDES.get(param) or cParam.get(param, '#1f77b4')

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

def is_doppler_input():
    """Doppler current-profiler database: Step 2 renders the 4 current panels."""
    return inputSettings.get('instrument', 'Seaguard') == 'Doppler'

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
        n_files = len([p for p in fileNames_entry.get().split(';') if p.strip()])
        if n_files > 1:
            # several qualified files build a NEW unified database (v12.0):
            # the user names it (and picks where it is saved)
            set_enabled_style(outputName_entry)
        else:
            # a single file needs no output name: blank + disabled
            outputName_entry.config(state='normal')
            outputName_entry.delete(0, END)
            set_disabled_style(outputName_entry)
        # the site-block order only means something in a database built from
        # SEVERAL files (v12.0)
        if sort_cb is not None:
            if n_files > 1:
                set_enabled_style(sort_cb)
            else:
                sort.set(False)
                set_disabled_style(sort_cb)
    # the Preview button applies to FOLDER mode only (it scans/builds a folder)
    if preview_btn is not None:
        if join.get():
            set_enabled_style(preview_btn)
        else:
            set_disabled_style(preview_btn)

def toggle_panel_dependent_controls():
    # trend lines, points and fixed scale apply to every panel family,
    # HOBO included (its panels honor them like the Seaguard ones)
    any_panel_selected = panel1.get() or panel2.get() or panel3.get()

    if any_panel_selected:
        set_enabled_style(tendency_cb)
        if tendency.get():
            set_enabled_style(tendency_entry)
        else:
            # unchecking Tendency lines must gray the degree again (the old
            # code only ever enabled it)
            set_disabled_style(tendency_entry)
        set_enabled_style(points_cb)
        set_enabled_style(fixed_scale_cb)
    else:
        set_disabled_style(tendency_cb)
        set_disabled_style(tendency_entry)
        set_disabled_style(points_cb)
        set_disabled_style(fixed_scale_cb)

    toggle_scale_controls()

def toggle_parameter_checkboxes():
    # the parameter filter applies to every family (for HOBO it selects between
    # temperature and light); active whenever a panel is selected
    if panel1.get() or panel2.get() or panel3.get():
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
    when Fixed scale is on, a panel is selected, that parameter is checked AND
    the current Site/Year selection actually carries data for it (no data means
    there is nothing to scale - the row stays gray to reflect that).
    Enabling pre-fills the data's own min/max (once, if empty); disabling clears
    the fields. Scale values are per-imported-sheet and are not persisted."""
    active = fixedScale.get() and (panel1.get() or panel2.get() or panel3.get())
    for param, min_e in min_scale_entries.items():
        max_e = max_scale_entries[param]
        on = active and param in parameter_vars and parameter_vars[param].get()
        if on and _param_data_extreme(param, 'min') == '':
            on = False   # parameter without data in the selected sites/years
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
    (called when those filters change); user-edited fields are left untouched.
    Also re-evaluates which rows are available: a parameter without data in the
    new selection goes gray (see toggle_scale_controls)."""
    toggle_scale_controls()
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
    if kind == 'min' and value < 0:
        # every variable is physically >= 0 in this software (values <= 0 are
        # discarded/clamped at qualification), so the breathing room must not
        # push the default below zero (e.g. PAR spanning 0..4500 gave -900)
        value = 0.0
    # plain numbers, never scientific notation (owner: '3.803e+04' reads
    # badly): large values round to whole numbers, small ones keep up to
    # three decimals
    if abs(value) >= 100:
        return '%d' % round(value)
    return ('%.3f' % value).rstrip('0').rstrip('.')

def toggle_data_type():
    data_type = dType_combobox.get()
    
    if not data_type:  # If no Data Type is selected
        toggle_all_controls(enabled=False)
        return

    toggle_all_controls(enabled=True)  # Enable everything

    def _stash_disable(entry, key):
        # a field that does not apply in this mode: remember its value, blank it
        # and gray it out (so it is not selectable)
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

    # a cross-site comparison panel is pointless with a single site in the
    # database: 'Parameter across sites' (Seaguard panel 2) / 'HOBO Light
    # multi-site' (HOBO panel 3) stay unavailable in that case
    single_site = len(site_names) < 2 if site_names else True

    # Specific logic for each data type. A control that does not apply is
    # UNCHECKED/blanked and grayed out; one that applies again is re-enabled and
    # its previous value restored.
    if is_hobo_input():
        # HOBO: two panels only (at a site / across sites); T-S, profile panel
        # and the depth range do not exist for a temp/light logger (their
        # widgets are removed from the window); X-axis time window applies
        tsDiagram.set(False)
        panel3.set(False)
        if single_site:
            panel2.set(False)           # 'Parameters across sites' needs >= 2 sites
            set_disabled_style(panel2_cb)
        if not (panel1.get() or panel2.get()):
            panel1.set(True)            # default panel: never an empty selection
        _stash_disable(depth_min_entry, 'depth_min')
        _stash_disable(depth_max_entry, 'depth_max')
        _reset_time_default(time_start_entry, 'start')
        _reset_time_default(time_end_entry, 'end')
    elif data_type == 'TSCP Mooring':
        panel3.set(False)
        set_disabled_style(panel3_cb)
        tsDiagram.set(False)            # T-S is profile-only -> uncheck it here
        set_disabled_style(ts_cb)
        if single_site:
            panel2.set(False)           # 'Parameter across sites' needs >= 2 sites
            set_disabled_style(panel2_cb)
        # default panel so the selection is never empty when switching here
        if not (panel1.get() or panel2.get()):
            panel1.set(True)
        _stash_disable(depth_min_entry, 'depth_min')     # depth range = profile only
        _stash_disable(depth_max_entry, 'depth_max')
        _reset_time_default(time_start_entry, 'start')   # X-axis window applies (default range)
        _reset_time_default(time_end_entry, 'end')
    elif data_type == 'TSCP Profile':
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
    elif data_type == 'TSCP Doppler':
        # Doppler current profiler: the 4 current panels are fixed (time x depth
        # heatmaps, stick plot, U/V components, progressive vector), so the
        # panel/parameter/tendency choices do not apply - but the TIME WINDOW
        # and the DEPTH BAND both crop the current data, and 'fixed scale' fixes
        # the heatmap speed color scale so sites/years compare 1:1.
        panel1.set(False)
        panel2.set(False)
        panel3.set(False)
        set_disabled_style(panel1_cb)
        set_disabled_style(panel2_cb)
        set_disabled_style(panel3_cb)
        tsDiagram.set(False)
        set_disabled_style(ts_cb)
        tendency.set(False)
        tendency_cb.config(state='disabled')
        points_cb.config(state='disabled')
        fixed_scale_cb.config(state='normal')            # -> heatmap speed scale
        _restore_or_default_depth(depth_min_entry, 'depth_min', 'min')  # depth band applies
        _restore_or_default_depth(depth_max_entry, 'depth_max', 'max')
        _reset_time_default(time_start_entry, 'start')   # X-axis window applies
        _reset_time_default(time_end_entry, 'end')

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
        apply_selected_files(list(filenames))

def apply_selected_files(filenames):
    """Shared tail of the database-file selection (Browse or drag-and-drop,
    v11.5): fills the entry, switches to single-file mode and auto-detects
    the instrument."""
    fileNames_entry.delete(0, END)
    fileNames_entry.insert(0, ";".join(filenames))
    join.set(False)
    toggle_input_mode()
    USER_PREFS['dbv_last_db_dir'] = os.path.dirname(filenames[0])
    if len(filenames) > 1:
        # several files build a NEW unified database (v12.0): the output
        # fields start EMPTY on purpose - the user picks where it is saved
        # and names it (the Qt shell shows instructive placeholders there)
        outputPath_entry.delete(0, END)
        outputName_entry.config(state='normal')
        outputName_entry.delete(0, END)
    else:
        # auto-fill Output Path with the qualification output root of the
        # file: the DataView generated HERE lands beside the qualification's
        # own plots ('DatabaseView' vs 'QCS DataView ...' subfolders)
        out_root = _default_output_root(filenames[0])
        outputPath_entry.delete(0, END)
        outputPath_entry.insert(0, out_root)
        USER_PREFS['dbv_output_path'] = out_root
        USER_PREFS['dbv_last_output_dir'] = out_root
        USER_PREFS['dbv_output_name'] = os.path.splitext(os.path.basename(filenames[0]))[0]
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
        detected = ('HOBO' if layout == 'hobo'
                    else 'Doppler' if layout == 'doppler' else 'Seaguard')
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
        ui_warn("Warning", "Select the instrument that produced the files\n('Instrument' field).")
        return
    if join.get():
        if not inputPath_entry.get().strip() or not os.path.isdir(inputPath_entry.get().strip()):
            ui_warn("Warning", "To build the database from a folder, select a valid\ninput folder ('Input Path' field).")
            return
        if not outputName_entry.get().strip():
            ui_warn("Warning", "Define a name for the generated database\n('Output Name' field).")
            return
    else:
        db_file = fileNames_entry.get().strip()
        if not db_file:
            ui_warn("Warning", "Select the database file (.xlsx) or check\n'Build database from a folder' to create a new one.")
            return
        first_file = db_file.split(';')[0]
        if not os.path.isfile(first_file):
            ui_error("Error", "File not found:\n%s" % first_file)
            return
        if (len([p for p in db_file.split(';') if p.strip()]) > 1
                and not outputName_entry.get().strip()):
            ui_warn("Warning", "Several files build a NEW unified database -\n"
                    "name it ('Output name' field).")
            return
    if not outputPath_entry.get().strip() or not os.path.isdir(outputPath_entry.get().strip()):
        ui_warn("Warning", "Select a valid output folder\n('Output Path' field).")
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
                ui_warn("Warning",
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
        dataViewSettings['showDisagreementBars'] = disagreement.get()

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
                ui_warn("Warning",
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
                ui_warn("Warning",
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
            'dbv_disagreement': disagreement.get(),
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
        ui_warn("No year selected",
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
        if is_hobo_input():
            # HOBO: two panels, each spanning EVERY selected year in one figure
            # (a deployment crossing the new year is never split into truncated
            # per-year plots); T-S does not apply (no salinity)
            selected_sites = dataViewSettings.get('siteList', [])
            any_hobo_panel = (dataViewSettings.get('panel1', False)
                              or dataViewSettings.get('panel2', False))
            if any_hobo_panel and not selected_sites:
                error_logger.log("Error: no site selected - check at least one site in 'Filter by Site'")

            elif dataViewSettings.get('panel1', False) or dataViewSettings.get('panel2', False):
                if dataViewSettings.get('panel1', False):
                    for site in selected_sites:
                        try:
                            n = view.plot_hobo_params_at_site(database, dataViewSettings, site)
                            if n:
                                error_logger.log("Info: HOBO parameters panel for %s generated." % site)
                                n_ok += n
                        except Exception as e:
                            error_logger.log("Error generating HOBO parameters for %s: %s" % (site, e))

                if dataViewSettings.get('panel2', False):
                    try:
                        n = view.plot_hobo_params_across_sites(database, dataViewSettings)
                        if n:
                            error_logger.log("Info: HOBO across-sites panel(s) generated (%d figure(s))." % n)
                            n_ok += n
                    except Exception as e:
                        error_logger.log("Error generating HOBO across-sites panel: %s" % e)

        if is_doppler_input():
            # Doppler: the 4 current panels per selected site, spanning every
            # selected year in one set (like HOBO, deployments are not split)
            selected_sites = dataViewSettings.get('siteList', [])
            if not selected_sites:
                error_logger.log("Error: no site selected - check at least one site in 'Filter by Site'")
            else:
                sub = database[database['Datetime'].dt.year.isin(selected_years)]
                out_dir = os.path.join(inputSettings.get('outputPath', ''), 'DatabaseView')
                # the current panels honour the time window and the depth band.
                # 'Fixed scale' ON = every heatmap shares one speed color scale
                # (the max GOOD speed over the whole selection) so different
                # sites/years compare 1:1; OFF = each panel autoscales.
                speed_max = None
                if dataViewSettings.get('fixedScale') and 'Horizontal speed (cm/s)' in sub.columns:
                    good = sub[sub.get('Flag_cur', 1) == 1]['Horizontal speed (cm/s)']
                    good = pd.to_numeric(good, errors='coerce').dropna()
                    if len(good):
                        speed_max = float(good.max()) * 1.05
                dop_settings = {
                    'xAxisStart': dataViewSettings.get('xAxisStart'),
                    'xAxisEnd': dataViewSettings.get('xAxisEnd'),
                    'depthAxisMin': dataViewSettings.get('depthAxisMin'),
                    'depthAxisMax': dataViewSettings.get('depthAxisMax'),
                    'currentSpeedMax': speed_max,
                }
                for site in selected_sites:
                    site_df = sub[sub['Site'] == site]
                    if not len(site_df):
                        error_logger.log("Warning: no rows for site %s in the selected years." % site)
                        continue
                    try:
                        files = view.plot_doppler_panels(
                            site_df, os.path.join(out_dir, '%s (current)' % site),
                            label=site, settings=dop_settings)
                        if files:
                            error_logger.log("Info: %d current panel(s) generated for %s." % (len(files), site))
                            n_ok += len(files)
                        else:
                            error_logger.log("Warning: %s has no non-BAD current rows - nothing to plot." % site)
                    except Exception as e:
                        error_logger.log("Error generating current panels for %s: %s" % (site, e))
                # cross-site comparison (mean speed by depth) when >= 2 sites
                if len(selected_sites) > 1:
                    try:
                        xfiles = view.plot_doppler_across_sites(
                            sub, out_dir, selected_sites, settings=dop_settings)
                        if xfiles:
                            error_logger.log("Info: cross-site current comparison generated "
                                             "(%d site(s))." % len(selected_sites))
                            n_ok += len(xfiles)
                        else:
                            error_logger.log("Warning: cross-site current panel needs 2+ sites "
                                             "with data - skipped.")
                    except Exception as e:
                        error_logger.log("Error generating cross-site current panel: %s" % e)

        # Seaguard panels are generated once for each selected year
        for year in (selected_years if not (is_hobo_input() or is_doppler_input()) else []):
            dataViewSettings['filterByYear'] = year

            if dataViewSettings['dataType'] == 'TSCP Mooring':
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

            elif dataViewSettings['dataType'] == 'TSCP Profile':
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
    global join, sort, sort_cb, instrument_combobox, outputName_entry, outputPath_entry

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
    join_cb.grid(row=5, column=0, sticky='w', pady=2)
    ToolTip(join_cb, TOOLTIPS['join_files'])

    sort = BooleanVar(value=False)
    sort_cb = ttk.Checkbutton(input_frame, text="Sort by time", variable=sort)
    sort_cb.grid(row=4, column=0, sticky='w', pady=2)
    ToolTip(sort_cb, TOOLTIPS['sort_time'])

    # Instrument (Seaguard/TSCP or HOBO): the two are never stackable, so the
    # database is built for one instrument at a time (.csv and .xlsx both read).
    # Auto-set from the selected files (detect_qualified_layout); still editable.
    ttk.Label(input_frame, text="Instrument:", style='Header.TLabel').grid(row=6, column=0, sticky='w', pady=(5,2))
    instrument_combobox = ttk.Combobox(input_frame, values=["Seaguard", "HOBO", "Doppler"], width=15, state='readonly')
    instrument_combobox.set("Seaguard")
    instrument_combobox.grid(row=7, column=0, sticky='w', pady=(0,5))
    ToolTip(instrument_combobox, TOOLTIPS['instrument'])

    # Recent selections: one click reopens the last database file choices
    global _recent_combobox
    ttk.Label(input_frame, text="Recent:", style='Header.TLabel').grid(row=8, column=0, sticky='w', pady=(5,2))
    _recent_combobox = ttk.Combobox(input_frame, state='readonly', width=45)
    _recent_combobox.grid(row=9, column=0, columnspan=2, sticky='ew', pady=(0,5))
    _recent_combobox.bind('<<ComboboxSelected>>', _apply_recent)
    ToolTip(_recent_combobox, "Recent file selections\n(pick one to fill the fields above)")
    _refresh_recent_combobox()

    # --- Output Section ---
    # Output path first (it always applies; the name only names a built database)
    ttk.Label(output_frame, text="Output path:", style='Header.TLabel').grid(row=0, column=0, sticky='w', pady=(0,2))
    outputPath_entry = ttk.Entry(output_frame, width=24)
    outputPath_entry.grid(row=1, column=0, sticky='ew', pady=(0,5))
    ToolTip(outputPath_entry, TOOLTIPS['output_path'])

    browse_output_btn = ttk.Button(output_frame, text="Browse...", command=selectOutputFolder, width=10)
    browse_output_btn.grid(row=1, column=1, padx=5)
    ToolTip(browse_output_btn, TOOLTIPS['output_path'])

    # Output naming
    ttk.Label(output_frame, text="Output name:", style='Header.TLabel').grid(row=2, column=0, sticky='w', pady=(5,2))
    outputName_entry = ttk.Entry(output_frame, width=24)
    outputName_entry.grid(row=3, column=0, sticky='ew', pady=(0,5))
    set_disabled_style(outputName_entry)
    ToolTip(outputName_entry, TOOLTIPS['output_name'])

    # Database preview: build now and summarize (sites, period, rows) so the
    # user can confirm the selection BEFORE moving on; Next reuses the result
    global _preview_var, preview_btn
    preview_frame = ttk.LabelFrame(main_frame, text=" Database preview ", padding=12)
    preview_frame.grid(row=2, column=0, columnspan=2, padx=5, pady=5, sticky='ew')
    preview_frame.columnconfigure(1, weight=1)
    preview_btn = ttk.Button(preview_frame, text="Preview", command=preview_database, width=12)
    preview_btn.grid(row=0, column=0, sticky='nw', padx=(0, 12))
    ToolTip(preview_btn, "Builds the database now and shows a summary below\n"
                         "(sites, period, rows); 'Next >' reuses this build")
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
    if USER_PREFS.get('dbv_instrument') in ('Seaguard', 'HOBO', 'Doppler'):
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
            # Folder mode gets the same the-data-is-the-truth treatment as the
            # file picker: the scan looks for the instrument's own 'QCS
            # qualified ... data' subfolders, so a stale Instrument selection
            # finds nothing (or the wrong layout). When the folder holds
            # exactly ONE instrument's subfolders, correct the selection to it.
            found = set()
            for _root, _dirs, _names in os.walk(inputSettings['inputPath']):
                for lay, subs in data.QUALIFIED_SUBFOLDERS.items():
                    if os.path.basename(_root) in subs:
                        found.add(lay)
            lay2inst = {'hobo': 'HOBO', 'doppler': 'Doppler', 'tscp': 'Seaguard'}
            if len(found) == 1:
                inst_for_layout = lay2inst[next(iter(found))]
                if inst_for_layout != instrument:
                    print('Info: instrument auto-corrected to %s (the folder holds '
                          '%s qualified data).' % (inst_for_layout, next(iter(found)).upper()))
                    instrument = inst_for_layout
                    inputSettings['instrument'] = instrument
                    try:
                        instrument_combobox.set(instrument)
                    except Exception:
                        pass
            database, db_build_messages = data.build_database(instrument,
                                                              input_path=inputSettings['inputPath'])
        else:
            file_paths = [p.strip() for p in inputSettings.get('databaseFileName', '').split(';') if p.strip()]
            if not file_paths:
                ui_error("Error", "Select a database file or provide a valid input folder.")
                return None
            # the FILE is the truth: if the selected instrument does not match
            # the first file's layout, auto-correct it instead of refusing
            # (the mix-refusal inside build_database still guards mixed lists)
            try:
                if file_paths[0].lower().endswith('.csv'):
                    head = pd.read_csv(file_paths[0], nrows=1)
                else:
                    head = pd.read_excel(file_paths[0], nrows=1)
                lay = data.detect_qualified_layout(head)
                inst_for_layout = {'hobo': 'HOBO', 'doppler': 'Doppler', 'tscp': 'Seaguard'}[lay]
                if inst_for_layout != instrument:
                    print('Info: instrument auto-corrected to %s (the selected file is a '
                          '%s spreadsheet).' % (inst_for_layout, lay.upper()))
                    instrument = inst_for_layout
                    inputSettings['instrument'] = instrument
                    try:
                        instrument_combobox.set(instrument)
                    except Exception:
                        pass
            except Exception:
                pass          # unreadable head: let build_database report it
            database, db_build_messages = data.build_database(instrument, file_list=file_paths)
            # several files = a NEW unified database: SAVE it, like the
            # folder-scan mode always did (v12.0 - before, the combination
            # existed only in memory)
            inputSettings['writeUnified'] = len(file_paths) > 1
    except ValueError as e:
        # the engine messages are already self-labeled ('build_database: ...')
        ui_error("Error", str(e))
        return None
    except Exception as e:
        ui_error("Error", "Could not build the database:\n%s" % e)
        return None
    # db_build_messages are shown in the Execution log by build_step2 (below),
    # so they are not printed here (that would duplicate them via the log redirect)

    # Sites are NEVER interleaved (v12.0): the option only decides the order of
    # the site BLOCKS - alphabetical (build_database's own Site+Datetime order)
    # or by each site's first sample. Rows stay chronological within a site.
    if inputSettings.get('sortByTime', False) == True:
        first_sample = database.groupby('Site')['Datetime'].min().sort_values()
        rank = {site: i for i, site in enumerate(first_sample.index)}
        database = database.assign(_site_rank=database['Site'].map(rank))
        database = database.sort_values(['_site_rank', 'Datetime'], kind='stable')
        database = database.drop(columns='_site_rank')
        database.index = range(len(database))
        print('Info: site blocks ordered by first sample: %s'
              % ', '.join(str(s) for s in first_sample.index))

    try:
        databaseViewPath = os.path.join(inputSettings['outputPath'], 'DatabaseView')
        os.makedirs(databaseViewPath, exist_ok=True)
        os.chdir(databaseViewPath)
    except Exception as e:
        ui_error("Error", "Could not create the output folder:\n%s\n\nDetails: %s" % (inputSettings.get('outputPath', ''), e))
        return None

    if (inputSettings.get('joinFiles', False) == True
            or inputSettings.get('writeUnified', False)):
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
    global disagreement
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
    # same names and order as the qualification Data Type, for consistency
    dType_values = (["HOBO"] if is_hobo_input()
                    else ["TSCP Doppler"] if is_doppler_input()
                    else ["TSCP Mooring", "TSCP Profile"])
    dType_combobox = ttk.Combobox(data_frame, values=dType_values, width=25, state='readonly')
    dType_combobox.grid(row=1, column=0, sticky='w', pady=2)
    dType_combobox.bind("<<ComboboxSelected>>", lambda e: toggle_data_type())
    ToolTip(dType_combobox, TOOLTIPS['data_type'])

    # In the empty space to the right: which spreadsheet(s) this database was read
    # from, so the loaded source is always visible on the Generate-panels screen.
    # The value sits on the SAME row as the Data type combobox (vertically
    # centered), with its header on the label row above.
    ttk.Label(data_frame, text="Reading:").grid(row=0, column=1, sticky='w', padx=(28, 4), pady=2)
    ttk.Label(data_frame, text=_current_source_label(), style='Small.TLabel',
              wraplength=340, justify='left').grid(row=1, column=1, sticky='w', padx=(28, 4), pady=2)

    # --- Visualization Settings ---
    # Panels: HOBO has only TWO panels (parameters at a site / across sites);
    # the profile panel and the T-S diagram do not exist for a temp/light logger
    if is_hobo_input():
        panel_labels = ("Parameters at a site",
                        "Parameters across sites",
                        "(unused)")
        panel_tips = (TOOLTIPS['hobo_params_site'], TOOLTIPS['hobo_params_across'], '')
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
    if is_hobo_input():
        panel3_cb.grid_remove()          # HOBO has no third panel at all

    # TS Diagram
    tsDiagram = BooleanVar(value=False)
    ts_cb = ttk.Checkbutton(vis_frame, text="T-S diagram", variable=tsDiagram, command=toggle_ts_controls)
    ts_cb.grid(row=4, column=0, sticky='w', pady=5)
    ToolTip(ts_cb, TOOLTIPS['ts_diagram'])

    # Coordinates
    _FIELD_W = 18   # compact width for the coordinate boxes (short values)
    lat_lbl = ttk.Label(vis_frame, text="Latitude:")
    lat_lbl.grid(row=5, column=0, sticky='w', pady=2)
    latitude_entry = ttk.Entry(vis_frame, width=_FIELD_W)
    latitude_entry.grid(row=6, column=0, sticky='w', pady=2)
    set_disabled_style(latitude_entry)
    ToolTip(latitude_entry, TOOLTIPS['latitude'])

    long_lbl = ttk.Label(vis_frame, text="Longitude:")
    long_lbl.grid(row=7, column=0, sticky='w', pady=2)
    longitude_entry = ttk.Entry(vis_frame, width=_FIELD_W)
    longitude_entry.grid(row=8, column=0, sticky='w', pady=2)
    set_disabled_style(longitude_entry)
    ToolTip(longitude_entry, TOOLTIPS['longitude'])

    # TS Parameters
    tsp_lbl = ttk.Label(vis_frame, text="T-S parameters:")
    tsp_lbl.grid(row=9, column=0, sticky='w', pady=2)
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

    if is_hobo_input():
        # a temp/light logger has no salinity: the whole T-S section (checkbox,
        # coordinates and parameter choice) is removed, not just grayed out
        for w in (ts_cb, lat_lbl, latitude_entry, long_lbl, longitude_entry,
                  tsp_lbl, tsParam_combobox):
            w.grid_remove()

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

    # HOBO replicate-disagreement bars. v12.0 option, so it has a VARIABLE
    # here (the authoritative state both shells read) but no tk widget: the
    # tk Step 2 is the hidden pipeline host, not an interface any more.
    disagreement = BooleanVar(value=True)

    fixedScale = BooleanVar(value=False)
    fixed_scale_cb = ttk.Checkbutton(vis_frame, text="Fixed scale", variable=fixedScale, command=toggle_scale_controls)
    fixed_scale_cb.grid(row=5, column=1, sticky='w', pady=5)
    ToolTip(fixed_scale_cb, TOOLTIPS['fixed_scale'])

    # X-axis time window (time-series plots; label says which family applies)
    _x_kind = ('HOBO' if is_hobo_input()
               else 'current' if is_doppler_input() else 'mooring')
    ttk.Label(vis_frame, text="X-axis start (%s):" % _x_kind).grid(row=6, column=1, sticky='w', pady=(8,2))
    time_start_entry = ttk.Entry(vis_frame, width=28)
    time_start_entry.grid(row=7, column=1, sticky='w', pady=2)
    ToolTip(time_start_entry, TOOLTIPS['time_start'])

    ttk.Label(vis_frame, text="X-axis end (%s):" % _x_kind).grid(row=8, column=1, sticky='w', pady=2)
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
    dmin_lbl = ttk.Label(vis_frame, text="Depth-axis min (profile):")
    dmin_lbl.grid(row=11, column=1, sticky='w', pady=(10,2))
    depth_min_entry = ttk.Entry(vis_frame, width=28)
    depth_min_entry.grid(row=12, column=1, sticky='w', pady=2)
    ToolTip(depth_min_entry, TOOLTIPS['depth_min'])

    dmax_lbl = ttk.Label(vis_frame, text="Depth-axis max (profile):")
    dmax_lbl.grid(row=13, column=1, sticky='w', pady=2)
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
    depth_avail_lbl = ttk.Label(vis_frame, text=depth_text, style='Small.TLabel')
    depth_avail_lbl.grid(row=15, column=1, sticky='w', pady=(2,5))
    if is_hobo_input():
        # HOBO has no depth at all: remove the whole depth block, not just gray it
        for w in (dmin_lbl, depth_min_entry, dmax_lbl, depth_max_entry, depth_avail_lbl):
            w.grid_remove()

    # --- Filter Settings ---
    # Year filter: one checkbox per year actually present in the database
    year_lbl = ttk.Label(filter_frame, text="Filter by year:")
    year_lbl.grid(row=0, column=0, sticky='w', pady=(5,2))
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
    # header row = label + the main group's All/None buttons (added below, after
    # the groups are defined), all inside ONE grid row to keep the alignment
    param_hdr_row = ttk.Frame(param_col)
    param_hdr_row.grid(row=0, column=0, sticky='w', pady=(5,2), padx=10)
    param_lbl = ttk.Label(param_hdr_row, text="Select parameters:")
    param_lbl.pack(side='left')
    ToolTip(param_lbl, TOOLTIPS['param_filter'])

    # Parameters come in TWO groups: the MAIN group (checked by default on every
    # new import, whenever the data carries them) and a SECONDARY group of
    # rarely-used variables that ALWAYS start unchecked (still available manually).
    if inputSettings.get('instrument', 'Seaguard') == 'HOBO':
        # HOBO only measures temperature and light
        main_params = ['Temperature (degC)', 'Luminosity (lux)']
        secondary_params = []
    elif is_doppler_input():
        # the 4 current panels have a fixed content - the parameter selection
        # does not apply (kept for the row-height/layout machinery only)
        main_params = ['Horizontal speed (cm/s)', 'Direction (deg)']
        secondary_params = []
    else:
        # NOTE: 'CO2 Level (ppm)' (capital L) is the qualified sheet's column name
        main_params = ['Temperature (degC)', 'Salinity (PSU)', 'CO2 Level (ppm)',
                       'O2 level (uM)', 'PAR (umol/m2/s)', 'Turbidity (FTU)',
                       'Chlorophyll (ug/L)', 'pH', 'Dissolved organic matter (ppb)']
        secondary_params = ['Conductivity (mS/cm)', 'Density (kg/m3)',
                            'Soundspeed (m/s)', 'Pressure (dbar)']
    parameter_names = main_params + secondary_params
    parameter_vars = {}  # Stores the BooleanVar
    parameter_widgets = {}  # Stores the Checkbutton widgets

    def _param_display(param):
        # GUI label only - the data column keeps its original name
        return re.sub(r'(?i)\s+level', '', param)

    # parameters this database actually carries data for (a column present with at
    # least one non-null value) - used as the default selection and for defaults
    params_with_data = [p for p in parameter_names
                        if p in database.columns and database[p].notna().any()]

    def _set_group(group, value):
        # All/None for a parameter group; only meaningful while the checkboxes
        # are active (a panel is selected), like clicking them one by one
        if str(next(iter(parameter_widgets.values())).cget('state')) == 'disabled':
            return
        for p in group:
            parameter_vars[p].set(value)
        toggle_scale_controls()

    def _group_buttons(parent, group):
        # small All/None pair placed INSIDE the group's header row, so the row
        # numbering (and the 1:1 alignment with Scale settings) is unchanged
        btns = ttk.Frame(parent)
        ttk.Button(btns, text='All', width=4,
                   command=lambda: _set_group(group, True)).pack(side='left', padx=(8, 2))
        ttk.Button(btns, text='None', width=5,
                   command=lambda: _set_group(group, False)).pack(side='left')
        return btns

    # the checkboxes and the Scale-settings rows are built with the SAME row
    # numbering (including the group separator), so each Min/Max line can sit
    # exactly beside its parameter
    _group_buttons(param_hdr_row, main_params).pack(side='left')
    prow = 1
    for param in parameter_names:
        if secondary_params and param == secondary_params[0]:
            sep_row = ttk.Frame(param_col)
            sep_row.grid(row=prow, column=0, sticky='w', pady=(8, 2), padx=10)
            sep_lbl = ttk.Label(sep_row, text="Rarely used:", style='Small.TLabel')
            sep_lbl.pack(side='left')
            ToolTip(sep_lbl, TOOLTIPS['param_secondary'])
            _group_buttons(sep_row, secondary_params).pack(side='left')
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
    # Headers for the scale columns; the default-rule tooltips live HERE (one
    # hover explains the whole column) instead of on every entry
    scale_hdr = ttk.Label(scale_frame, text="Parameter")
    scale_hdr.grid(row=0, column=0, sticky='w', padx=5)
    min_hdr = ttk.Label(scale_frame, text="Min")
    min_hdr.grid(row=0, column=1, sticky='w', padx=5)
    ToolTip(min_hdr, TOOLTIPS['min_scale'])
    max_hdr = ttk.Label(scale_frame, text="Max")
    max_hdr.grid(row=0, column=2, sticky='w', padx=5)
    ToolTip(max_hdr, TOOLTIPS['max_scale'])

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

        # Entry for maximum value
        max_entry = ttk.Entry(scale_frame, width=10)
        max_entry.grid(row=srow, column=2, sticky='w', pady=2, padx=5)
        max_entry.bind('<KeyRelease>', _untrack)
        max_scale_entries[param] = max_entry
        set_disabled_style(max_entry)
        srow += 1

    # Align the two frames line by line: a Checkbutton, an Entry and a header
    # with buttons all have different natural heights, which otherwise
    # accumulates a visible offset down the list. Measure each row's REAL
    # content (widget height + its pady) on both sides and give both frames the
    # same row minsize, so each Min/Max sits beside its parameter checkbox.
    param_col.update_idletasks()

    def _row_content_h(frame, r):
        h = 0
        for w in frame.grid_slaves(row=r):
            # pady may come back as an int, '8 2' or '(8, 2)' depending on Tk
            pads = [int(p) for p in re.findall(r'\d+', str(w.grid_info().get('pady', 0)))]
            pad = sum(pads) * (2 if len(pads) == 1 else 1)
            h = max(h, w.winfo_reqheight() + pad)
        return h

    for r in range(0, srow):
        h = max(_row_content_h(param_col, r), _row_content_h(scale_frame, r))
        if h:
            param_col.grid_rowconfigure(r, minsize=h)
            scale_frame.grid_rowconfigure(r, minsize=h)

    # 'Filter by year:' sits beside the parameters header (which is taller now,
    # holding the All/None buttons): pad it down so the two headers align
    dy = max(0, (param_hdr_row.winfo_reqheight() - year_lbl.winfo_reqheight()) // 2)
    year_lbl.grid_configure(pady=(5 + dy, 2))

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
    tsDiagram.set(False if (is_hobo_input() or is_doppler_input())
                  else USER_PREFS.get('dbv_ts_diagram', False))
    tendency.set(USER_PREFS.get('dbv_tendency', False))
    dataPoints.set(USER_PREFS.get('dbv_data_points', False))
    disagreement.set(USER_PREFS.get('dbv_disagreement', True))
    fixedScale.set(USER_PREFS.get('dbv_fixed_scale', False))
    # Year/Site: ALL checked by default on every import (like the parameters,
    # these are per-imported-sheet and NOT restored from preferences): with
    # several years/sites the user usually wants everything, and unchecking is
    # easier than hunting for what is missing.
    for v in year_vars.values():
        v.set(True)
    for v in site_vars.values():
        v.set(True)
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
        dType_combobox.set('HOBO')
        dType_combobox.config(state='disabled')  # HOBO has only one option
        toggle_data_type()
    elif handoff_type in dType_values:
        dType_combobox.set(handoff_type)
        dType_combobox.config(state='disabled')  # locked: comes from the file
        toggle_data_type()
    elif USER_PREFS.get('dbv_data_type') in dType_values:
        dType_combobox.set(USER_PREFS['dbv_data_type'])
        toggle_data_type()
    else:
        # opened a file directly (no qualification handoff, no valid saved
        # choice): default to TSCP Mooring instead of leaving the field blank
        dType_combobox.set(dType_values[0])
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
preview_btn = None        # Step 1 'Preview' button (folder mode only)
sort_cb = None            # Step 1 site-order checkbox (created in build_step1)
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

def _push_recent(files, instrument):
    """Puts a file selection on top of the Recent list and SHOWS it in the
    combobox (the display must always reflect the current selection)."""
    entry = {'files': files, 'instrument': instrument}
    recents = [r for r in USER_PREFS.get('dbv_recent', []) if r.get('files') != files]
    recents.insert(0, entry)
    USER_PREFS['dbv_recent'] = recents[:8]
    save_user_prefs()
    _refresh_recent_combobox()
    if _recent_combobox is not None:
        _recent_combobox.set(_recent_display(entry))

def _update_recents():
    """Keeps the last file selections in USER_PREFS for one-click reopening."""
    if inputSettings.get('joinFiles', False):
        return  # folder-scan mode: nothing file-based to remember
    files = inputSettings.get('databaseFileName', '').strip()
    if not files:
        return
    _push_recent(files, inputSettings.get('instrument', 'Seaguard'))

def _recent_display(entry):
    names = ', '.join(os.path.basename(f) for f in entry['files'].split(';') if f)
    if len(names) > 70:
        names = names[:67] + '…'
    return '%s   [%s]' % (names, entry.get('instrument', '?'))

def _refresh_recent_combobox():
    if _recent_combobox is None:
        return
    values = [_recent_display(r) for r in USER_PREFS.get('dbv_recent', [])]
    _recent_combobox['values'] = values
    # show the most recently USED selection instead of an easy-to-miss blank box
    if values and not _recent_combobox.get():
        _recent_combobox.set(values[0])

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
    if entry.get('instrument') in ('Seaguard', 'HOBO', 'Doppler'):
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
    if info.get('instrument') in ('Seaguard', 'HOBO', 'Doppler'):
        instrument_combobox.set(info['instrument'])
    # stash the data type + coordinates for build_step2 (the file lacks them)
    global _pending_step2
    _pending_step2 = {'data_type': info.get('data_type'),
                      'latitude': info.get('latitude'),
                      'longitude': info.get('longitude')}
    join.set(False)
    toggle_input_mode()
    _preview_cache['key'] = None   # force a rebuild for the new selection
    # the just-qualified file IS the current selection: Recent must show it
    # (not the previous session's file)
    if info.get('file'):
        _push_recent(info['file'], info.get('instrument', 'Seaguard'))
    print('Info: Visualization pre-selected the just-qualified file: %s'
          % os.path.basename(info.get('file', '')))

def _go_step2():
    """Next: validate Step 1, build the database (or reuse the previewed one),
    then show Step 2 in place."""
    global database, _db_msgs_logged
    inputSettings.clear()
    if not saveInputSettings():
        return False  # validation failed (a warning was already shown)
    if (_preview_cache['database'] is not None
            and _preview_cache['key'] == _settings_key()):
        database = _preview_cache['database']  # already built by Preview
    else:
        _db_msgs_logged = False
        database = load_database()
    if database is None:
        return False  # error already shown; stay on Step 1
    _update_recents()
    dataViewSettings.clear()
    for child in _step2_frame.winfo_children():
        child.destroy()  # rebuild Step 2 fresh for the new database
    build_step2(_step2_frame)
    _step1_frame.pack_forget()
    _step2_frame.pack(fill='both', expand=True)
    return True   # the Qt shell mirrors Step 2 from the module state on True

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

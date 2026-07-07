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
    'time_start': "OPTIONAL: start of the X axis in mooring plots\nFormat: DD/MM/YYYY HH:MM (e.g. 15/04/2019 09:00)\nLeave empty to fit the data automatically",
    'time_end': "OPTIONAL: end of the X axis in mooring plots\nFormat: DD/MM/YYYY HH:MM (e.g. 16/04/2019 09:00)\nLeave empty to fit the data automatically",
    'depth_min': "OPTIONAL: minimum depth (m) for the depth axis in profile plots\nLeave empty to fit the data automatically",
    'depth_max': "OPTIONAL: maximum depth (m) for the depth axis in profile plots\nLeave empty to fit the data automatically",
    'panel1': "Panel 1: Comparison between parameters at the same site",
    'panel2': "Panel 2: Comparison of the same parameter between sites",
    'panel3': "Panel 3: Comparison between parameters at the same site (vertical profile)",
    'hobo_temp': "HOBO panel: temperature over time, one plot per selected site\nSuspect/bad points (Flag_T >= 3) are highlighted",
    'hobo_light': "HOBO panel: light over time (log scale), one plot per selected site\nThe fouling window (Flag_lux == 4) is shaded from the cutoff on",
    'hobo_light_multi': "HOBO panel: light (log scale) with all selected sites together\nEach site's fouling cutoff is marked to compare fouling onset",
    'ts_diagram': "Generate Temperature-Salinity diagram",
    'latitude': "Latitude for TS diagram reference",
    'longitude': "Longitude for TS diagram reference",
    'ts_params': "Parameters to use for TS diagram",
    'tendency': "Add linear regression lines to plots",
    'tendency_degree': "Degree of polynomial for linear regression lines",
    'data_points': "Show individual data points on plots",
    'site_filter': "Select sites to include in visualization",
    'param_filter': "Select parameters to include in visualization",
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
        set_disabled_style(fileNames_entry)
        set_disabled_style(browse_file_btn)
        set_enabled_style(inputPath_entry)
        set_enabled_style(browse_input_btn)
        set_enabled_style(outputName_entry)
    else:  # unchecked: pick files one by one (multi-select already joins them)
        set_enabled_style(fileNames_entry)
        set_enabled_style(browse_file_btn)
        set_disabled_style(inputPath_entry)
        set_disabled_style(browse_input_btn)
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
        set_enabled_style(latitude_entry)
        set_enabled_style(longitude_entry)
        set_enabled_style(tsParam_combobox)
    else:
        set_disabled_style(latitude_entry)
        set_disabled_style(longitude_entry)
        set_disabled_style(tsParam_combobox)

def toggle_scale_controls():
    """Enables or disables the scale controls based on fixed_scale and the selected panels"""
    if fixedScale.get() and (panel1.get() or panel2.get() or panel3.get()):
        for entry in min_scale_entries.values():
            set_enabled_style(entry)
        for entry in max_scale_entries.values():
            set_enabled_style(entry)
    else:
        for entry in min_scale_entries.values():
            set_disabled_style(entry)
        for entry in max_scale_entries.values():
            set_disabled_style(entry)

def toggle_data_type():
    data_type = dType_combobox.get()
    
    if not data_type:  # If no Data Type is selected
        toggle_all_controls(enabled=False)
        return

    toggle_all_controls(enabled=True)  # Enable everything

    # Specific logic for each data type
    if is_hobo_input():
        # HOBO: the three checkboxes become their own panels (temperature/light);
        # no T-S (there is no salinity) and no profile (there is no depth)
        set_disabled_style(ts_cb)
        set_disabled_style(depth_min_entry)
        set_disabled_style(depth_max_entry)
    elif data_type == 'mooring':
        set_disabled_style(panel3_cb)
        set_disabled_style(ts_cb)
        # the depth range only applies to profile plots
        set_disabled_style(depth_min_entry)
        set_disabled_style(depth_max_entry)
    elif data_type == 'tscp profile':
        set_disabled_style(panel1_cb)
        set_disabled_style(panel2_cb)
        # the X-axis time window only applies to mooring plots
        set_disabled_style(time_start_entry)
        set_disabled_style(time_end_entry)
    
    toggle_panel_dependent_controls()
    toggle_parameter_checkboxes()
    toggle_ts_controls()

def selectFiles():
    filenames = filedialog.askopenfilenames(initialdir=USER_PREFS.get('dbv_last_db_dir', USER_PREFS.get('last_output_dir', '/')),
                                            title="Select files")
    if filenames:
        fileNames_entry.delete(0, END)
        fileNames_entry.insert(0, ";".join(filenames))
        join.set(False)
        toggle_input_mode()
        USER_PREFS['dbv_last_db_dir'] = os.path.dirname(filenames[0])
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
        print('MESSAGE: instrument auto-detected as %s (from %s).'
              % (detected, os.path.basename(path)))
    except Exception as e:
        print('WARNING: could not auto-detect the instrument from %s: %s'
              % (os.path.basename(path), e))

def selectOutputFolder():
    folderPath = filedialog.askdirectory(initialdir=USER_PREFS.get('dbv_last_output_dir', '/'), title="Select output folder")
    if folderPath:
        outputPath_entry.delete(0, END)
        outputPath_entry.insert(0, folderPath)
        USER_PREFS['dbv_last_output_dir'] = folderPath
        save_user_prefs()

def selectInputFolder():
    folderPath = filedialog.askdirectory(initialdir=USER_PREFS.get('dbv_last_input_dir', '/'), title="Select input folder")
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
                error_logger.log("WARNING: T-S Diagram skipped - missing/invalid Latitude/Longitude")
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
                error_logger.log("WARNING: invalid X-axis time window - ignored")

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
                error_logger.log("WARNING: invalid depth-axis range - ignored")

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
                    error_logger.log(f"WARNING: Invalid scale values for {param} - using defaults")
        
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
            'dbv_selected_params': selectedParameters,
            'dbv_scale_settings': scale_settings,
        })
        save_user_prefs()

        error_logger.log("SUCCESS: View settings saved successfully")
    except Exception as e:
        error_logger.log(f"ERROR saving view settings: {str(e)}")

def generatePanels():
    error_logger.clear()  # Clear the log before generating new panels

    # implicitly saves the current interface choices: generating panels with
    # stale settings was a pitfall of the 2-click save->generate flow
    saveDataViewSettings()

    if not dataViewSettings.get('dataType'):
        error_logger.log("ERROR: No settings saved yet - configure the options and click 'Save View Settings' first")
        return

    # the year checkboxes only list years present in the database,
    # so the only possible mistake left is selecting none
    available_years = sorted(set(int(y) for y in database['Datetime'].dt.year.dropna().unique()))
    years_str = ', '.join(str(y) for y in available_years)
    selected_years = [y for y in dataViewSettings.get('filterByYears', []) if y in available_years]
    if not selected_years:
        messagebox.showwarning("No year selected",
                               "Check at least one year in 'Filter by Year' and click "
                               "'Save View Settings' again.\n\n"
                               "Years available in this database:\n%s" % years_str)
        error_logger.log("ERROR: no year selected (available: %s)" % years_str)
        return

    try:
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
                    error_logger.log("ERROR: no site selected - check at least one site in 'Filter by Site'")
                    continue

                if dataViewSettings.get('panel1', False):
                    for site in selected_sites:
                        try:
                            view.plot_hobo_temperature(database, dataViewSettings, site)
                            error_logger.log("SUCCESS: HOBO temperature for %s (%d) generated successfully" % (site, year))
                        except Exception as e:
                            error_logger.log("ERROR generating HOBO temperature for %s (%d): %s" % (site, year, e))

                if dataViewSettings.get('panel2', False):
                    for site in selected_sites:
                        try:
                            view.plot_hobo_light(database, dataViewSettings, site)
                            error_logger.log("SUCCESS: HOBO light for %s (%d) generated successfully" % (site, year))
                        except Exception as e:
                            error_logger.log("ERROR generating HOBO light for %s (%d): %s" % (site, year, e))

                if dataViewSettings.get('panel3', False):
                    try:
                        view.plot_hobo_light_multisite(database, dataViewSettings)
                        error_logger.log("SUCCESS: HOBO light multi-site (%d) generated successfully" % year)
                    except Exception as e:
                        error_logger.log("ERROR generating HOBO light multi-site (%d): %s" % (year, e))
                continue

            if dataViewSettings['dataType'] == 'mooring':
                if dataViewSettings.get('panel1', False):
                    try:
                        view.plot_database_panel1(database, dataViewSettings)
                        error_logger.log("SUCCESS: Panel 1 (%d) generated successfully" % year)
                    except Exception as e:
                        error_logger.log(f"ERROR generating Panel 1 ({year}): {str(e)}")

                if dataViewSettings.get('panel2', False):
                    try:
                        view.plot_database_panel2(database, dataViewSettings)
                        error_logger.log("SUCCESS: Panel 2 (%d) generated successfully" % year)
                    except Exception as e:
                        error_logger.log(f"ERROR generating Panel 2 ({year}): {str(e)}")

                if dataViewSettings.get('panel3', False):
                    error_logger.log("WARNING: Panel 3 is not suited for mooring data")

            elif dataViewSettings['dataType'] == 'tscp profile':
                if dataViewSettings.get('panel3', False):
                    try:
                        view.plot_database_panel3(database, dataViewSettings)
                        error_logger.log("SUCCESS: Panel 3 (%d) generated successfully" % year)
                    except Exception as e:
                        error_logger.log(f"ERROR generating Panel 3 ({year}): {str(e)}")

                if dataViewSettings.get('panel1', False) or dataViewSettings.get('panel2', False):
                    error_logger.log("WARNING: Panels 1/2 are not suited for profile data")

            if dataViewSettings.get('tsDiagram', False):
                try:
                    view.plot_TS_diagram(database, dataViewSettings)
                    error_logger.log("SUCCESS: TS Diagram (%d) generated successfully" % year)
                except Exception as e:
                    error_logger.log(f"ERROR generating TS Diagram ({year}): {str(e)}")

    except Exception as e:
        error_logger.log(f"CRITICAL ERROR: {str(e)}")

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
    ttk.Label(input_frame, text="Database File(s):", style='Header.TLabel').grid(row=0, column=0, sticky='w', pady=(0,2))
    fileNames_entry = ttk.Entry(input_frame, width=24)
    fileNames_entry.grid(row=1, column=0, sticky='ew', pady=(0,5))
    ToolTip(fileNames_entry, TOOLTIPS['database_files'])

    browse_file_btn = ttk.Button(input_frame, text="Browse...", command=selectFiles, width=10)
    browse_file_btn.grid(row=1, column=1, padx=5)
    ToolTip(browse_file_btn, TOOLTIPS['database_files'])

    # Input path
    ttk.Label(input_frame, text="Input Path:", style='Header.TLabel').grid(row=2, column=0, sticky='w', pady=(5,2))
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
    sort_cb = ttk.Checkbutton(input_frame, text="Sort by Time", variable=sort)
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
    ttk.Label(output_frame, text="Output Name:", style='Header.TLabel').grid(row=0, column=0, sticky='w', pady=(0,2))
    outputName_entry = ttk.Entry(output_frame, width=24)
    outputName_entry.grid(row=1, column=0, sticky='ew', pady=(0,5))
    set_disabled_style(outputName_entry)
    ToolTip(outputName_entry, TOOLTIPS['output_name'])

    # Output path
    ttk.Label(output_frame, text="Output Path:", style='Header.TLabel').grid(row=2, column=0, sticky='w', pady=(5,2))
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
            print('MESSAGE: unified database saved to %s.xlsx'
                  % os.path.join(databaseViewPath, inputSettings['outputFileName']))
        except Exception as e:
            print(f"ERROR saving database: {str(e)}")
    return database

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
    ttk.Label(data_frame, text="Data Type:").grid(row=0, column=0, sticky='w', pady=2)
    dType_values = ["mooring"] if is_hobo_input() else ["tscp profile", "mooring"]
    dType_combobox = ttk.Combobox(data_frame, values=dType_values, width=25, state='readonly')
    dType_combobox.grid(row=1, column=0, sticky='w', pady=2)
    dType_combobox.bind("<<ComboboxSelected>>", lambda e: toggle_data_type())
    ToolTip(dType_combobox, TOOLTIPS['data_type'])

    # --- Visualization Settings ---
    # Panels: for HOBO the three checkboxes become the dedicated panels
    # (temperature / light+window / light multi-site) instead of Panel 1/2/3
    if is_hobo_input():
        panel_labels = ("HOBO Temperature (per site)",
                        "HOBO Light + fouling window (per site)",
                        "HOBO Light multi-site")
        panel_tips = (TOOLTIPS['hobo_temp'], TOOLTIPS['hobo_light'], TOOLTIPS['hobo_light_multi'])
    else:
        panel_labels = ("Panel 1 (mooring)", "Panel 2 (mooring)", "Panel 3 (profile)")
        panel_tips = (TOOLTIPS['panel1'], TOOLTIPS['panel2'], TOOLTIPS['panel3'])

    ttk.Label(vis_frame, text="Select Panels:").grid(row=0, column=0, sticky='w', pady=5)
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
    ts_cb = ttk.Checkbutton(vis_frame, text="T-S Diagram", variable=tsDiagram, command=toggle_ts_controls)
    ts_cb.grid(row=4, column=0, sticky='w', pady=5)
    ToolTip(ts_cb, TOOLTIPS['ts_diagram'])

    # Coordinates
    ttk.Label(vis_frame, text="Latitude:").grid(row=5, column=0, sticky='w', pady=2)
    latitude_entry = ttk.Entry(vis_frame, width=28)
    latitude_entry.grid(row=6, column=0, sticky='w', pady=2)
    set_disabled_style(latitude_entry)
    ToolTip(latitude_entry, TOOLTIPS['latitude'])

    ttk.Label(vis_frame, text="Longitude:").grid(row=7, column=0, sticky='w', pady=2)
    longitude_entry = ttk.Entry(vis_frame, width=28)
    longitude_entry.grid(row=8, column=0, sticky='w', pady=2)
    set_disabled_style(longitude_entry)
    ToolTip(longitude_entry, TOOLTIPS['longitude'])

    # TS Parameters
    ttk.Label(vis_frame, text="T-S Parameters:").grid(row=9, column=0, sticky='w', pady=2)
    tsParam_combobox = ttk.Combobox(vis_frame, values=["Conservative T & Absolute S", "Potential T & Pratical S"], width=28)
    tsParam_combobox.grid(row=10, column=0, sticky='w', pady=2)
    set_disabled_style(tsParam_combobox)
    ToolTip(tsParam_combobox, TOOLTIPS['ts_params'])

    # Display options
    ttk.Label(vis_frame, text="Display Options:").grid(row=0, column=1, sticky='w', pady=5)

    tendency = BooleanVar(value=False)
    tendency_cb = ttk.Checkbutton(vis_frame, text="Trend Lines", variable=tendency, 
                                 command=lambda: [set_enabled_style(tendency_entry) if tendency.get() else set_disabled_style(tendency_entry)])
    tendency_cb.grid(row=1, column=1, sticky='w', pady=2)
    ToolTip(tendency_cb, TOOLTIPS['tendency'])

    ttk.Label(vis_frame, text="Degree:").grid(row=2, column=1, sticky='w', pady=2)
    tendency_entry = ttk.Entry(vis_frame, width=28)
    tendency_entry.grid(row=3, column=1, sticky='w', pady=2)
    set_disabled_style(tendency_entry)
    ToolTip(tendency_entry, TOOLTIPS['tendency_degree'])

    dataPoints = BooleanVar(value=False)
    points_cb = ttk.Checkbutton(vis_frame, text="Show Data Points", variable=dataPoints)
    points_cb.grid(row=4, column=1, sticky='w', pady=5)
    ToolTip(points_cb, TOOLTIPS['data_points'])

    fixedScale = BooleanVar(value=False)
    fixed_scale_cb = ttk.Checkbutton(vis_frame, text="Fixed Scale", variable=fixedScale, command=toggle_scale_controls)
    fixed_scale_cb.grid(row=5, column=1, sticky='w', pady=5)
    ToolTip(fixed_scale_cb, TOOLTIPS['fixed_scale'])

    # X-axis time window (mooring plots)
    ttk.Label(vis_frame, text="X-Axis Start (mooring):").grid(row=6, column=1, sticky='w', pady=(10,2))
    time_start_entry = ttk.Entry(vis_frame, width=28)
    time_start_entry.grid(row=7, column=1, sticky='w', pady=2)
    ToolTip(time_start_entry, TOOLTIPS['time_start'])

    ttk.Label(vis_frame, text="X-Axis End (mooring):").grid(row=8, column=1, sticky='w', pady=2)
    time_end_entry = ttk.Entry(vis_frame, width=28)
    time_end_entry.grid(row=9, column=1, sticky='w', pady=2)
    ToolTip(time_end_entry, TOOLTIPS['time_end'])

    # shows the period covered by the loaded database, so the user does not
    # need to open the spreadsheet to know which days were sampled
    data_start = database['Datetime'].min()
    data_end = database['Datetime'].max()
    if pd.notna(data_start) and pd.notna(data_end):
        coverage_text = "Data available:\n%s  to  %s" % (data_start.strftime('%d/%m/%Y %H:%M'),
                                                         data_end.strftime('%d/%m/%Y %H:%M'))
    else:
        coverage_text = "Data available: unknown (invalid dates)"
    ttk.Label(vis_frame, text=coverage_text, style='Small.TLabel').grid(
        row=10, column=1, sticky='w', pady=(2,5))

    # Depth-axis range (profile plots) - analogous to the time window above
    ttk.Label(vis_frame, text="Depth-Axis Min (profile):").grid(row=11, column=1, sticky='w', pady=(10,2))
    depth_min_entry = ttk.Entry(vis_frame, width=28)
    depth_min_entry.grid(row=12, column=1, sticky='w', pady=2)
    ToolTip(depth_min_entry, TOOLTIPS['depth_min'])

    ttk.Label(vis_frame, text="Depth-Axis Max (profile):").grid(row=13, column=1, sticky='w', pady=2)
    depth_max_entry = ttk.Entry(vis_frame, width=28)
    depth_max_entry.grid(row=14, column=1, sticky='w', pady=2)
    ToolTip(depth_max_entry, TOOLTIPS['depth_max'])

    # shows the depth range covered by the loaded database
    if 'Depth (m)' in database.columns and database['Depth (m)'].notna().any():
        depth_text = "Depth available:\n%.2f  to  %.2f m" % (database['Depth (m)'].min(),
                                                             database['Depth (m)'].max())
    else:
        depth_text = "Depth available: no depth column"
    ttk.Label(vis_frame, text=depth_text, style='Small.TLabel').grid(
        row=15, column=1, sticky='w', pady=(2,5))

    # --- Filter Settings ---
    # Year filter: one checkbox per year actually present in the database
    ttk.Label(filter_frame, text="Filter by Year:").grid(row=0, column=0, sticky='w', pady=(5,2))
    available_years = sorted(set(int(y) for y in database['Datetime'].dt.year.dropna().unique()))
    year_vars = {}    # BooleanVar for each year
    year_widgets = {} # Checkbutton for each year
    row_n = 1
    for db_year in available_years:
        var = BooleanVar(value=False)
        cb = ttk.Checkbutton(filter_frame, text=str(db_year), variable=var)
        cb.grid(row=row_n, column=0, sticky='w', pady=2)
        ToolTip(cb, TOOLTIPS['filter_year'])
        year_vars[db_year] = var
        year_widgets[db_year] = cb
        row_n += 1

    # Site selection
    site_lbl = ttk.Label(filter_frame, text="Filter by Site:")
    site_lbl.grid(row=row_n, column=0, sticky='w', pady=(10,2))
    ToolTip(site_lbl, TOOLTIPS['site_filter'])
    row_n += 1

    site_names = sorted(set(database['Site']))
    site_vars = {}  # Stores the BooleanVar
    site_widgets = {}  # Stores the Checkbutton widgets

    for site in site_names:
        var = BooleanVar(value=False)
        cb = ttk.Checkbutton(filter_frame, text=site, variable=var)
        cb.grid(row=row_n, column=0, sticky='w', pady=2)
        site_vars[site] = var
        site_widgets[site] = cb
        row_n += 1

    # Parameter selection
    param_lbl = ttk.Label(filter_frame, text="Select Parameters:")
    param_lbl.grid(row=0, column=1, sticky='w', pady=(5,2), padx=10)
    ToolTip(param_lbl, TOOLTIPS['param_filter'])

    if inputSettings.get('instrument', 'Seaguard') == 'HOBO':
        # HOBO only measures temperature and light
        parameter_names = ['Temperature (degC)', 'Luminosity (lux)']
    else:
        parameter_names = ['Temperature (degC)', 'Salinity (PSU)', 'Conductivity (mS/cm)',
                          'Density (kg/m3)', 'CO2 level (ppm)', 'O2 level (uM)',
                          'PAR (umol/m2/s)', 'Turbidity (FTU)', 'Chlorophyll (ug/L)',
                          'pH', 'Dissolved organic matter (ppb)', 'Soundspeed (m/s)',
                          'Pressure (dbar)']
    parameter_vars = {}  # Stores the BooleanVar
    parameter_widgets = {}  # Stores the Checkbutton widgets

    for i, param in enumerate(parameter_names):
        var = BooleanVar(value=False)
        cb = ttk.Checkbutton(filter_frame, text=param, variable=var)
        cb.grid(row=i+1, column=1, sticky='w', pady=2, padx=10)
        parameter_vars[param] = var
        parameter_widgets[param] = cb
        set_disabled_style(cb)  # Initially disabled

    # --- Scale Settings ---
    # Headers for the scale columns
    ttk.Label(scale_frame, text="Parameter").grid(row=0, column=0, sticky='w', padx=5)
    ttk.Label(scale_frame, text="Min").grid(row=0, column=1, sticky='w', padx=5)
    ttk.Label(scale_frame, text="Max").grid(row=0, column=2, sticky='w', padx=5)

    # Dictionaries to store the scale entry widgets
    min_scale_entries = {}
    max_scale_entries = {}

    # Create entries for each parameter
    for i, param in enumerate(parameter_names):
        # Parameter label
        ttk.Label(scale_frame, text=param).grid(row=i+1, column=0, sticky='w', pady=2, padx=5)

        # Entry for minimum value
        min_entry = ttk.Entry(scale_frame, width=10)
        min_entry.grid(row=i+1, column=1, sticky='w', pady=2, padx=5)
        min_scale_entries[param] = min_entry
        set_disabled_style(min_entry)
        ToolTip(min_entry, TOOLTIPS['min_scale'])

        # Entry for maximum value
        max_entry = ttk.Entry(scale_frame, width=10)
        max_entry.grid(row=i+1, column=2, sticky='w', pady=2, padx=5)
        max_scale_entries[param] = max_entry
        set_disabled_style(max_entry)
        ToolTip(max_entry, TOOLTIPS['max_scale'])

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
    ttk.Button(action_frame, text="Save View Settings", command=saveDataViewSettings).pack(side='left', padx=5)
    ttk.Button(action_frame, text="Generate Panels", command=generatePanels, style='Accent.TButton').pack(side='left', padx=5)

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
    for param in USER_PREFS.get('dbv_selected_params', []):
        if param in parameter_vars:
            parameter_vars[param].set(True)
    for param, limits in USER_PREFS.get('dbv_scale_settings', {}).items():
        if param in min_scale_entries:
            restore_entry(min_scale_entries[param], str(limits.get('min', '')))
            restore_entry(max_scale_entries[param], str(limits.get('max', '')))
    for y in USER_PREFS.get('dbv_selected_years', []):
        if y in year_vars:
            year_vars[y].set(True)
    restore_entry(time_start_entry, USER_PREFS.get('dbv_time_start', ''))
    restore_entry(time_end_entry, USER_PREFS.get('dbv_time_end', ''))
    restore_entry(depth_min_entry, USER_PREFS.get('dbv_depth_min', ''))
    restore_entry(depth_max_entry, USER_PREFS.get('dbv_depth_max', ''))
    restore_entry(latitude_entry, USER_PREFS.get('dbv_latitude', ''))
    restore_entry(longitude_entry, USER_PREFS.get('dbv_longitude', ''))
    restore_entry(tendency_entry, USER_PREFS.get('dbv_degree', ''))
    if USER_PREFS.get('dbv_ts_param'):
        tsParam_combobox.set(USER_PREFS['dbv_ts_param'])
    # re-apply enable/disable rules with the restored values
    if is_hobo_input():
        # the only valid option for HOBO: select it and enable the controls
        dType_combobox.set('mooring')
        toggle_data_type()
    elif USER_PREFS.get('dbv_data_type') in dType_values:
        dType_combobox.set(USER_PREFS['dbv_data_type'])
        toggle_data_type()

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

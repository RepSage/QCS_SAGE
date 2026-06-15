import os
import sys
import json
import pandas as pd
import QCS_DataHandler as data
import QCS_DataView as view
from tkinter import *
import tkinter as tk
from tkinter import ttk
from tkinter import filedialog
from tkinter import messagebox

# Configurações de estilo para campos desabilitados
DISABLED_BG = '#f0f0f0'
DISABLED_FG = '#a0a0a0'

# Tooltips dictionary
TOOLTIPS = {
    'database_files': "Select database file (xlsx) to visualize\nMultiple files can be selected",
    'join_files': "Combine multiple files into a single database",
    'sort_time': "Sort data chronologically by datetime",
    'input_format': "Format of input files (CSV or Excel)",
    'output_name': "Name for processed database file",
    'input_path': "Folder containing input files",
    'output_path': "Folder where results will be saved",
    'data_type': "Type of data (profile or mooring)",
    'filter_year': "Check the year(s) to visualize\nPanels are generated once per selected year",
    'time_start': "OPTIONAL: start of the X axis in mooring plots\nFormat: DD/MM/YYYY HH:MM (e.g. 15/04/2019 09:00)\nLeave empty to fit the data automatically",
    'time_end': "OPTIONAL: end of the X axis in mooring plots\nFormat: DD/MM/YYYY HH:MM (e.g. 16/04/2019 09:00)\nLeave empty to fit the data automatically",
    'panel1': "Panel 1: Comparison between parameters at the same site",
    'panel2': "Panel 2: Comparison of the same parameter between sites",
    'panel3': "Panel 3: Comparison between parameters at the same site (vertical profile)",
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

class ToolTip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tooltip = None
        self.widget.bind("<Enter>", self.show)
        self.widget.bind("<Leave>", self.hide)

    def show(self, event=None):
        x, y, _, _ = self.widget.bbox("insert")
        x += self.widget.winfo_rootx() + 25
        y += self.widget.winfo_rooty() + 25

        self.tooltip = tk.Toplevel(self.widget)
        self.tooltip.wm_overrideredirect(True)
        self.tooltip.wm_geometry(f"+{x}+{y}")
        
        label = tk.Label(self.tooltip, text=self.text, justify='left',
                        background="#ffffe0", relief='solid', borderwidth=1,
                        font=('Arial', 10), padx=5, pady=5)
        label.pack()

    def hide(self, event=None):
        if self.tooltip:
            self.tooltip.destroy()
            self.tooltip = None

class ErrorLogger:
    def __init__(self, parent):
        self.frame = ttk.LabelFrame(parent, text=" ERROR LOG ", padding=10)
        self.frame.pack(fill='both', expand=True, padx=5, pady=5)
        
        self.text = tk.Text(self.frame, height=8, wrap='word', state='disabled',
                           bg='#f0f0f0', fg='red', font=('Consolas', 9))
        self.text.pack(fill='both', expand=True)
        
        scrollbar = ttk.Scrollbar(self.text)
        scrollbar.pack(side='right', fill='y')
        self.text.config(yscrollcommand=scrollbar.set)
        scrollbar.config(command=self.text.yview)
        
        self.clear_button = ttk.Button(self.frame, text="Clear Log", command=self.clear)
        self.clear_button.pack(side='right', padx=5, pady=5)
    
    def log(self, message):
        self.text.config(state='normal')
        self.text.insert('end', message + '\n')
        self.text.see('end')
        self.text.config(state='disabled')
    
    def clear(self):
        self.text.config(state='normal')
        self.text.delete('1.0', 'end')
        self.text.config(state='disabled')


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
    # preenche um campo mesmo que ele esteja desabilitado no momento
    if not value:
        return
    prev = entry.cget('state')
    entry.config(state='normal')
    entry.delete(0, END)
    entry.insert(0, value)
    entry.config(state=prev)

def set_disabled_style(widget):
    if isinstance(widget, (ttk.Entry, ttk.Combobox)):
        widget.config(state='disabled', foreground=DISABLED_FG)
        widget.configure(style='Disabled.TEntry')
    elif isinstance(widget, ttk.Button):
        widget.config(state='disabled')
    elif isinstance(widget, ttk.Checkbutton):
        widget.config(state='disabled')

def set_enabled_style(widget):
    if isinstance(widget, ttk.Entry):
        widget.config(state='normal', foreground='black')
        widget.configure(style='TEntry')
    elif isinstance(widget, ttk.Combobox):
        widget.config(state='readonly', foreground='black')
        widget.configure(style='TCombobox')
    elif isinstance(widget, ttk.Button):
        widget.config(state='normal')
    elif isinstance(widget, ttk.Checkbutton):
        widget.config(state='normal')

def toggle_all_controls(enabled=False):
    """Habilita ou desabilita todos os controles dependendo do Data Type selecionado"""
    # Painéis
    panel1_cb.config(state='normal' if enabled else 'disabled')
    panel2_cb.config(state='normal' if enabled else 'disabled')
    panel3_cb.config(state='normal' if enabled else 'disabled')
    
    # Opções de exibição
    tendency_cb.config(state='normal' if enabled else 'disabled')
    tendency_entry.config(state='normal' if enabled and tendency.get() else 'disabled')
    points_cb.config(state='normal' if enabled else 'disabled')
    fixed_scale_cb.config(state='normal' if enabled else 'disabled')
    
    # TS Diagram
    ts_cb.config(state='normal' if enabled else 'disabled')
    latitude_entry.config(state='normal' if enabled and tsDiagram.get() else 'disabled')
    longitude_entry.config(state='normal' if enabled and tsDiagram.get() else 'disabled')
    tsParam_combobox.config(state='readonly' if enabled and tsDiagram.get() else 'disabled')
    
    # Filtros
    for cb in year_widgets.values():
        cb.config(state='normal' if enabled else 'disabled')
    for cb in site_widgets.values():
        cb.config(state='normal' if enabled else 'disabled')
    for cb in parameter_widgets.values():
        cb.config(state='normal' if enabled else 'disabled')

    # Janela de tempo do eixo X (fundeio)
    time_start_entry.config(state='normal' if enabled else 'disabled')
    time_end_entry.config(state='normal' if enabled else 'disabled')
    
    # Escalas
    toggle_scale_controls()

def toggle_input_mode():
    if join.get():  # If Join Files is checked
        set_disabled_style(fileNames_entry)
        set_disabled_style(browse_file_btn)
        set_enabled_style(inputPath_entry)
        set_enabled_style(browse_input_btn)
        inputFilesFormat_combobox.config(state='readonly')
        inputFilesFormat_combobox.configure(style='TCombobox')
        set_enabled_style(outputName_entry)
    else:  # If Join Files is unchecked
        set_enabled_style(fileNames_entry)
        set_enabled_style(browse_file_btn)
        set_disabled_style(inputPath_entry)
        set_disabled_style(browse_input_btn)
        inputFilesFormat_combobox.config(state='disabled')
        inputFilesFormat_combobox.configure(style='Disabled.TEntry')
        set_disabled_style(outputName_entry)

def toggle_panel_dependent_controls():
    any_panel_selected = panel1.get() or panel2.get() or panel3.get()
    
    if any_panel_selected:
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
    if panel1.get() or panel2.get() or panel3.get():
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
        tsParam_combobox.config(state='readonly')
        tsParam_combobox.configure(style='TCombobox')
    else:
        set_disabled_style(latitude_entry)
        set_disabled_style(longitude_entry)
        tsParam_combobox.config(state='disabled')
        tsParam_combobox.configure(style='Disabled.TEntry')

def toggle_scale_controls():
    """Habilita ou desabilita os controles de escala com base no fixed_scale e painéis selecionados"""
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
    
    if not data_type:  # Se nenhum Data Type estiver selecionado
        toggle_all_controls(enabled=False)
        return
    
    toggle_all_controls(enabled=True)  # Habilita tudo
    
    # Lógica específica para cada tipo de dado
    if data_type == 'mooring':
        set_disabled_style(panel3_cb)
        set_disabled_style(ts_cb)
    elif data_type == 'tscp profile':
        set_disabled_style(panel1_cb)
        set_disabled_style(panel2_cb)
        # a janela de tempo do eixo X so se aplica a graficos de fundeio
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
    # validacao com avisos claros antes de fechar a janela
    if join.get():
        if not inputPath_entry.get().strip() or not os.path.isdir(inputPath_entry.get().strip()):
            messagebox.showwarning("Warning", "To join files, select a valid input folder\n('Input Path' field).")
            return
        if inputFilesFormat_combobox.get() not in ('csv', 'xlsx'):
            messagebox.showwarning("Warning", "Select the input files format\n(csv or xlsx).")
            return
        if not outputName_entry.get().strip():
            messagebox.showwarning("Warning", "Define a name for the generated database\n('Output Name' field).")
            return
    else:
        db_file = fileNames_entry.get().strip()
        if not db_file:
            messagebox.showwarning("Warning", "Select the database file (.xlsx)\nor check 'Join Data Files' to create a new one.")
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
    inputSettings['inputFilesFormat'] = inputFilesFormat_combobox.get()

    # guarda as ultimas escolhas
    USER_PREFS.update({
        'dbv_database_file': fileNames_entry.get(),
        'dbv_output_name': outputName_entry.get(),
        'dbv_output_path': outputPath_entry.get(),
        'dbv_input_path': inputPath_entry.get(),
        'dbv_sort_by_time': sort.get(),
        'dbv_input_format': inputFilesFormat_combobox.get(),
    })
    save_user_prefs()
    input_window.destroy()

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
            dataViewSettings['latitude'] = float(latitude_entry.get()) if latitude_entry.get() else None
            dataViewSettings['longitude'] = float(longitude_entry.get()) if longitude_entry.get() else None
            dataViewSettings['tsParam'] = tsParam_combobox.get()

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

        selectedSites = []
        for site in site_vars.keys():
            if site_vars[site].get() == True and site not in selectedSites:
                selectedSites.append(site)
        
        selectedParameters = []
        for param in parameter_vars.keys():
            if parameter_vars[param].get() == True and param not in selectedParameters:
                selectedParameters.append(param)
        
        # Salvar as escalas definidas
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

        # guarda as ultimas escolhas da visualizacao
        USER_PREFS.update({
            'dbv_data_type': dType_combobox.get(),
            'dbv_selected_years': selectedYears,
            'dbv_time_start': time_start_entry.get(),
            'dbv_time_end': time_end_entry.get(),
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
    error_logger.clear()  # Limpa o log antes de gerar novos painéis

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
         * Input folder + Join Files option - to create new database
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

def show_input_window():
    """Janela de selecao do banco de dados; preenche inputSettings ao salvar."""
    global input_window, fileNames_entry, inputPath_entry, browse_file_btn, browse_input_btn
    global join, sort, inputFilesFormat_combobox, outputName_entry, outputPath_entry
    input_window = Tk()
    input_window.title("Database Input Settings - QCS %s" % data.QCS_VERSION)

    input_window.geometry("650x450")
    input_window.resizable(False, False)

    # Configure styles
    style = ttk.Style()
    style.theme_use('clam')

    # Configure disabled style
    style.configure('Disabled.TEntry', fieldbackground=DISABLED_BG, foreground=DISABLED_FG)
    style.map('Disabled.TEntry',
              fieldbackground=[('disabled', DISABLED_BG)],
              foreground=[('disabled', DISABLED_FG)])

    style.configure('TFrame', background='#f0f0f0')
    style.configure('TLabel', background='#f0f0f0', font=('Arial', 10))
    style.configure('TLabelframe', background='#f0f0f0')
    style.configure('TLabelframe.Label', background='#f0f0f0')
    style.configure('Header.TLabel', font=('Arial', 10, 'bold'))
    style.configure('TButton', padding=5)
    style.configure('Accent.TButton', foreground='white', background='#4a90e2', font=('Arial', 10, 'bold'))
    style.configure('Help.TButton', foreground='white', background='#666666', font=('Arial', 9))
    style.map('Accent.TButton', background=[('active', '#544ae2')])

    style.configure('TCombobox', arrowsize=12)
    style.map('TCombobox', 
              fieldbackground=[('readonly', 'white')],
              foreground=[('readonly', 'black')])

    # Add menu bar
    menubar = Menu(input_window)
    helpmenu = Menu(menubar, tearoff=0)
    helpmenu.add_command(label="Help", command=show_help)
    helpmenu.add_command(label="About", command=lambda: messagebox.showinfo("About", "QCS Database View Tool\nVersion %s" % data.QCS_VERSION))
    menubar.add_cascade(label="Menu", menu=helpmenu)
    input_window.config(menu=menubar)

    # Main container
    main_frame = ttk.Frame(input_window, padding="10")
    main_frame.pack(fill='both', expand=True)

    # Input settings frame
    input_frame = ttk.LabelFrame(main_frame, text=" INPUT SETTINGS ", padding=10)
    input_frame.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")

    # Output settings frame
    output_frame = ttk.LabelFrame(main_frame, text=" OUTPUT SETTINGS ", padding=10)
    output_frame.grid(row=0, column=1, padx=5, pady=5, sticky="nsew")

    # Configure grid weights
    main_frame.columnconfigure(0, weight=1)
    main_frame.columnconfigure(1, weight=1)
    main_frame.rowconfigure(0, weight=1)

    # --- Input Section ---
    # File selection
    ttk.Label(input_frame, text="Database File(s):", style='Header.TLabel').grid(row=0, column=0, sticky='w', pady=(0,2))
    fileNames_entry = ttk.Entry(input_frame, width=30)
    fileNames_entry.grid(row=1, column=0, sticky='ew', pady=(0,5))
    ToolTip(fileNames_entry, TOOLTIPS['database_files'])

    browse_file_btn = ttk.Button(input_frame, text="Browse...", command=selectFiles, width=10)
    browse_file_btn.grid(row=1, column=1, padx=5)
    ToolTip(browse_file_btn, TOOLTIPS['database_files'])

    # Input path
    ttk.Label(input_frame, text="Input Path:", style='Header.TLabel').grid(row=2, column=0, sticky='w', pady=(5,2))
    inputPath_entry = ttk.Entry(input_frame, width=30)
    inputPath_entry.grid(row=3, column=0, sticky='ew', pady=(0,5))
    set_disabled_style(inputPath_entry)
    ToolTip(inputPath_entry, TOOLTIPS['input_path'])

    browse_input_btn = ttk.Button(input_frame, text="Browse...", command=selectInputFolder, width=10)
    set_disabled_style(browse_input_btn)
    browse_input_btn.grid(row=3, column=1, padx=5)
    ToolTip(browse_input_btn, TOOLTIPS['input_path'])

    # Options
    join = BooleanVar(value=False)
    join_cb = ttk.Checkbutton(input_frame, text="Join Data Files", variable=join, command=toggle_input_mode)
    join_cb.grid(row=4, column=0, sticky='w', pady=2)
    ToolTip(join_cb, TOOLTIPS['join_files'])

    sort = BooleanVar(value=False)
    sort_cb = ttk.Checkbutton(input_frame, text="Sort by Time", variable=sort)
    sort_cb.grid(row=5, column=0, sticky='w', pady=2)
    ToolTip(sort_cb, TOOLTIPS['sort_time'])

    # File format
    ttk.Label(input_frame, text="Input Format:", style='Header.TLabel').grid(row=6, column=0, sticky='w', pady=(5,2))
    inputFilesFormat_combobox = ttk.Combobox(input_frame, values=["csv", "xlsx"], width=28)
    inputFilesFormat_combobox.grid(row=7, column=0, sticky='w', pady=(0,5))
    set_disabled_style(inputFilesFormat_combobox)
    ToolTip(inputFilesFormat_combobox, TOOLTIPS['input_format'])

    # --- Output Section ---
    # Output naming
    ttk.Label(output_frame, text="Output Name:", style='Header.TLabel').grid(row=0, column=0, sticky='w', pady=(0,2))
    outputName_entry = ttk.Entry(output_frame, width=30)
    outputName_entry.grid(row=1, column=0, sticky='ew', pady=(0,5))
    set_disabled_style(outputName_entry)
    ToolTip(outputName_entry, TOOLTIPS['output_name'])

    # Output path
    ttk.Label(output_frame, text="Output Path:", style='Header.TLabel').grid(row=2, column=0, sticky='w', pady=(5,2))
    outputPath_entry = ttk.Entry(output_frame, width=30)
    outputPath_entry.grid(row=3, column=0, sticky='ew', pady=(0,5))
    ToolTip(outputPath_entry, TOOLTIPS['output_path'])

    browse_output_btn = ttk.Button(output_frame, text="Browse...", command=selectOutputFolder, width=10)
    browse_output_btn.grid(row=3, column=1, padx=5)
    ToolTip(browse_output_btn, TOOLTIPS['output_path'])

    # Save button
    ttk.Button(main_frame, text="Save Input Settings", command=saveInputSettings, style='Accent.TButton').grid(row=1, column=0, columnspan=2, pady=10)

    # restaura as ultimas escolhas do usuario
    restore_entry(fileNames_entry, USER_PREFS.get('dbv_database_file', ''))
    restore_entry(outputPath_entry, USER_PREFS.get('dbv_output_path', ''))
    restore_entry(inputPath_entry, USER_PREFS.get('dbv_input_path', ''))
    restore_entry(outputName_entry, USER_PREFS.get('dbv_output_name', ''))
    if USER_PREFS.get('dbv_input_format'):
        inputFilesFormat_combobox.set(USER_PREFS['dbv_input_format'])
    sort.set(USER_PREFS.get('dbv_sort_by_time', False))

    input_window.mainloop()


def load_database():
    """Carrega ou monta o banco de dados; retorna None (com aviso) em caso de erro."""

    # Prepare data

    if inputSettings.get('joinFiles', False) == True:
        try:
            database = data.join_files_to_database(inputSettings['inputPath'], inputSettings['inputFilesFormat'])
        except Exception as e:
            messagebox.showerror("Error", "Could not join the files from folder:\n%s\n\nDetails: %s" % (inputSettings.get('inputPath', ''), e))
            return None
    else:
        if inputSettings.get('databaseFileName', '') != '':
            try:
                database = pd.read_excel(inputSettings['databaseFileName'])
            except Exception as e:
                messagebox.showerror("Error", "Could not read the database file:\n%s\n\nDetails: %s" % (inputSettings['databaseFileName'], e))
                return None
        else:
            messagebox.showerror("Error", "Select a database file or provide a valid input folder.")
            return None

    if inputSettings.get('sortByTime', False) == True:
        try:
            database.index = database['Datetime']
            database = database.rename_axis('dt_index')
            database = database.sort_values(by='dt_index')
            database.index = range(len(database))
        except Exception as e:
            print(f"ERROR sorting by time: {str(e)}")

    try:
        database['Datetime'] = pd.to_datetime(database['Datetime'])
    except Exception as e:
        messagebox.showerror("Error", "Could not parse the 'Datetime' column of the database.\n\nDetails: %s" % e)
        return None

    try:
        databaseViewPath = os.path.join(inputSettings['outputPath'], 'DatabaseView')
        os.makedirs(databaseViewPath, exist_ok=True)
        os.chdir(databaseViewPath)
    except Exception as e:
        messagebox.showerror("Error", "Could not create the output folder:\n%s\n\nDetails: %s" % (inputSettings.get('outputPath', ''), e))
        return None

    if inputSettings.get('databaseFileName', '') == '':
        try:
            database.to_excel(inputSettings['outputFileName']+'.xlsx')
        except Exception as e:
            print(f"ERROR saving database: {str(e)}")
    return database

def show_view_window():
    """Janela de visualizacao; retorna True se o usuario pediu para trocar de arquivo."""
    global view_window, dType_combobox, panel1, panel2, panel3, panel1_cb, panel2_cb, panel3_cb
    global tsDiagram, ts_cb, latitude_entry, longitude_entry, tsParam_combobox
    global tendency, tendency_cb, tendency_entry, dataPoints, points_cb, fixedScale, fixed_scale_cb
    global year_vars, year_widgets, time_start_entry, time_end_entry
    global site_names, site_vars, site_widgets, parameter_names, parameter_vars, parameter_widgets
    global min_scale_entries, max_scale_entries, error_logger, back_requested
    back_requested = False
    # Create data view settings window
    view_window = Tk()
    view_window.title("Data View Settings - QCS %s" % data.QCS_VERSION)

    view_window.geometry("1300x750")  # Aumentado para acomodar o log
    view_window.resizable(False, False)

    # Add menu bar
    menubar = Menu(view_window)
    helpmenu = Menu(menubar, tearoff=0)
    helpmenu.add_command(label="Help", command=show_help)
    helpmenu.add_command(label="About", command=lambda: messagebox.showinfo("About", "QCS Database View Tool\nVersion %s" % data.QCS_VERSION))
    menubar.add_cascade(label="Menu", menu=helpmenu)
    view_window.config(menu=menubar)

    # Create main container with scrollbar
    container = ttk.Frame(view_window)
    canvas = tk.Canvas(container)
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
    main_content_frame = ttk.Frame(scrollable_frame)
    main_content_frame.pack(fill='both', expand=True)

    # Data settings frame
    data_frame = ttk.LabelFrame(main_content_frame, text=" DATA SETTINGS ", padding=10)
    data_frame.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")

    # Visualization frame
    vis_frame = ttk.LabelFrame(main_content_frame, text=" VISUALIZATION SETTINGS ", padding=10)
    vis_frame.grid(row=1, column=0, padx=5, pady=5, sticky="nsew")

    # Filter frame
    filter_frame = ttk.LabelFrame(main_content_frame, text=" FILTER SETTINGS ", padding=10)
    filter_frame.grid(row=1, column=1, padx=5, pady=5, sticky="nsew")

    # Scale frame
    scale_frame = ttk.LabelFrame(main_content_frame, text=" SCALE SETTINGS ", padding=10)
    scale_frame.grid(row=1, column=2, padx=5, pady=5, sticky="nsew")

    # Configure grid weights
    main_content_frame.columnconfigure(0, weight=1)
    main_content_frame.columnconfigure(1, weight=1)
    main_content_frame.columnconfigure(2, weight=1)
    main_content_frame.rowconfigure(0, weight=1)
    main_content_frame.rowconfigure(1, weight=1)

    # --- Data Settings ---
    # Data type
    ttk.Label(data_frame, text="Data Type:").grid(row=0, column=0, sticky='w', pady=2)
    dType_combobox = ttk.Combobox(data_frame, values=["tscp profile", "mooring"], width=25)
    dType_combobox.grid(row=1, column=0, sticky='w', pady=2)
    dType_combobox.bind("<<ComboboxSelected>>", lambda e: toggle_data_type())
    ToolTip(dType_combobox, TOOLTIPS['data_type'])

    # --- Visualization Settings ---
    # Panels
    ttk.Label(vis_frame, text="Select Panels:").grid(row=0, column=0, sticky='w', pady=5)
    panel1 = BooleanVar(value=False)
    panel1_cb = ttk.Checkbutton(vis_frame, text="Panel 1 (mooring)", variable=panel1, 
                               command=lambda: [toggle_panel_dependent_controls(), toggle_parameter_checkboxes()])
    panel1_cb.grid(row=1, column=0, sticky='w', pady=2)
    ToolTip(panel1_cb, TOOLTIPS['panel1'])

    panel2 = BooleanVar(value=False)
    panel2_cb = ttk.Checkbutton(vis_frame, text="Panel 2 (mooring)", variable=panel2, 
                               command=lambda: [toggle_panel_dependent_controls(), toggle_parameter_checkboxes()])
    panel2_cb.grid(row=2, column=0, sticky='w', pady=2)
    ToolTip(panel2_cb, TOOLTIPS['panel2'])

    panel3 = BooleanVar(value=False)
    panel3_cb = ttk.Checkbutton(vis_frame, text="Panel 3 (profile)", variable=panel3, 
                               command=lambda: [toggle_panel_dependent_controls(), toggle_parameter_checkboxes()])
    panel3_cb.grid(row=3, column=0, sticky='w', pady=2)
    ToolTip(panel3_cb, TOOLTIPS['panel3'])

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
    ttk.Label(vis_frame, text=coverage_text, font=('Arial', 8), foreground='#555555').grid(
        row=10, column=1, sticky='w', pady=(2,5))

    # --- Filter Settings ---
    # Year filter: one checkbox per year actually present in the database
    ttk.Label(filter_frame, text="Filter by Year:").grid(row=0, column=0, sticky='w', pady=(5,2))
    available_years = sorted(set(int(y) for y in database['Datetime'].dt.year.dropna().unique()))
    year_vars = {}    # BooleanVar de cada ano
    year_widgets = {} # Checkbutton de cada ano
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
    ttk.Label(filter_frame, text="Filter by Site:").grid(row=row_n, column=0, sticky='w', pady=(10,2))
    ToolTip(ttk.Label(filter_frame), TOOLTIPS['site_filter'])
    row_n += 1

    site_names = sorted(set(database['Site']))
    site_vars = {}  # Armazena as BooleanVar
    site_widgets = {}  # Armazena os widgets Checkbutton

    for site in site_names:
        var = BooleanVar(value=False)
        cb = ttk.Checkbutton(filter_frame, text=site, variable=var)
        cb.grid(row=row_n, column=0, sticky='w', pady=2)
        site_vars[site] = var
        site_widgets[site] = cb
        row_n += 1

    # Parameter selection
    ttk.Label(filter_frame, text="Select Parameters:").grid(row=0, column=1, sticky='w', pady=(5,2), padx=10)
    ToolTip(ttk.Label(filter_frame), TOOLTIPS['param_filter'])

    parameter_names = ['Temperature (degC)', 'Salinity (PSU)', 'Conductivity (mS/cm)', 
                      'Density (kg/m3)', 'CO2 level (ppm)', 'O2 level (uM)', 
                      'PAR (umol/m2/s)', 'Turbidity (FTU)', 'Chlorophyll (ug/L)', 
                      'pH', 'Dissolved organic matter (ppb)', 'Soundspeed (m/s)', 
                      'Pressure (dbar)']
    parameter_vars = {}  # Armazena as BooleanVar
    parameter_widgets = {}  # Armazena os widgets Checkbutton

    for i, param in enumerate(parameter_names):
        var = BooleanVar(value=False)
        cb = ttk.Checkbutton(filter_frame, text=param, variable=var)
        cb.grid(row=i+1, column=1, sticky='w', pady=2, padx=10)
        parameter_vars[param] = var
        parameter_widgets[param] = cb
        set_disabled_style(cb)  # Inicialmente desabilitado

    # --- Scale Settings ---
    # Cabeçalhos para as colunas de escala
    ttk.Label(scale_frame, text="Parameter").grid(row=0, column=0, sticky='w', padx=5)
    ttk.Label(scale_frame, text="Min").grid(row=0, column=1, sticky='w', padx=5)
    ttk.Label(scale_frame, text="Max").grid(row=0, column=2, sticky='w', padx=5)

    # Dicionários para armazenar os widgets de entrada de escala
    min_scale_entries = {}
    max_scale_entries = {}

    # Criar entradas para cada parâmetro
    for i, param in enumerate(parameter_names):
        # Label do parâmetro
        ttk.Label(scale_frame, text=param).grid(row=i+1, column=0, sticky='w', pady=2, padx=5)
    
        # Entrada para valor mínimo
        min_entry = ttk.Entry(scale_frame, width=10)
        min_entry.grid(row=i+1, column=1, sticky='w', pady=2, padx=5)
        min_scale_entries[param] = min_entry
        set_disabled_style(min_entry)
        ToolTip(min_entry, TOOLTIPS['min_scale'])
    
        # Entrada para valor máximo
        max_entry = ttk.Entry(scale_frame, width=10)
        max_entry.grid(row=i+1, column=2, sticky='w', pady=2, padx=5)
        max_scale_entries[param] = max_entry
        set_disabled_style(max_entry)
        ToolTip(max_entry, TOOLTIPS['max_scale'])

    # Configure grid weights for filter frame
    filter_frame.columnconfigure(0, weight=1)
    filter_frame.columnconfigure(1, weight=1)
    filter_frame.rowconfigure(2, weight=1)  # A linha do container de sites

    # Configure grid weights for scale frame
    scale_frame.columnconfigure(0, weight=1)
    scale_frame.columnconfigure(1, weight=1)
    scale_frame.columnconfigure(2, weight=1)

    # Action buttons
    action_frame = ttk.Frame(scrollable_frame)
    action_frame.pack(pady=10)

    ttk.Button(action_frame, text="< Change Database", command=go_back_to_input).pack(side='left', padx=5)
    ttk.Button(action_frame, text="Save View Settings", command=saveDataViewSettings).pack(side='left', padx=5)
    ttk.Button(action_frame, text="Generate Panels", command=generatePanels, style='Accent.TButton').pack(side='left', padx=5)

    # Initialize UI state
    toggle_all_controls(enabled=False)  # Tudo desabilitado inicialmente
    toggle_data_type()
    toggle_panel_dependent_controls()
    toggle_parameter_checkboxes()
    toggle_ts_controls()

    # restore the last visualization choices (checkboxes, selections and scales)
    panel1.set(USER_PREFS.get('dbv_panel1', False))
    panel2.set(USER_PREFS.get('dbv_panel2', False))
    panel3.set(USER_PREFS.get('dbv_panel3', False))
    tsDiagram.set(USER_PREFS.get('dbv_ts_diagram', False))
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
    restore_entry(latitude_entry, USER_PREFS.get('dbv_latitude', ''))
    restore_entry(longitude_entry, USER_PREFS.get('dbv_longitude', ''))
    restore_entry(tendency_entry, USER_PREFS.get('dbv_degree', ''))
    if USER_PREFS.get('dbv_ts_param'):
        tsParam_combobox.set(USER_PREFS['dbv_ts_param'])
    # re-apply enable/disable rules with the restored values
    if USER_PREFS.get('dbv_data_type'):
        dType_combobox.set(USER_PREFS['dbv_data_type'])
        toggle_data_type()

    # Create error logger
    error_logger = ErrorLogger(scrollable_frame)

    # Configure canvas scrolling
    def _on_mousewheel(event):
        canvas.yview_scroll(int(-1*(event.delta/120)), "units")

    canvas.bind_all("<MouseWheel>", _on_mousewheel)

    view_window.mainloop()

    return back_requested

back_requested = False

def go_back_to_input():
    """Fecha a visualizacao e volta para a janela de selecao de arquivo."""
    global back_requested
    back_requested = True
    view_window.destroy()

# Main flow: input window -> load data -> view window; the view window
# can send the user back to the input window to pick another database.
while True:
    inputSettings.clear()
    show_input_window()
    if not inputSettings:
        break  # janela fechada sem salvar: encerra
    database = load_database()
    if database is None:
        continue  # erro ja exibido: volta para a selecao de arquivo
    dataViewSettings.clear()
    if not show_view_window():
        break  # janela de visualizacao fechada: encerra

os.chdir(rootPath)

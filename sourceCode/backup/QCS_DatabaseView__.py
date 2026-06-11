import os
import sys
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
    'filter_year': "Filter data by specific year",
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

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

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
    year_entry.config(state='normal' if enabled else 'disabled')
    for cb in site_widgets.values():
        cb.config(state='normal' if enabled else 'disabled')
    for cb in parameter_widgets.values():
        cb.config(state='normal' if enabled else 'disabled')
    
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
    
    toggle_panel_dependent_controls()
    toggle_parameter_checkboxes()
    toggle_ts_controls()

def selectFiles():
    filenames = filedialog.askopenfilenames(initialdir="/", title="Select files")
    fileNames_entry.delete(0, END)
    if filenames:
        fileNames_entry.insert(0, ";".join(filenames))
        join.set(False)
        toggle_input_mode()

def selectOutputFolder():
    folderPath = filedialog.askdirectory(initialdir="/", title="Select output folder")
    outputPath_entry.delete(0, END)
    outputPath_entry.insert(0, folderPath)

def selectInputFolder():
    folderPath = filedialog.askdirectory(initialdir="/", title="Select input folder")
    inputPath_entry.delete(0, END)
    inputPath_entry.insert(0, folderPath)

def saveInputSettings():
    inputSettings['databaseFileName'] = fileNames_entry.get()
    inputSettings['joinFiles'] = join.get()
    inputSettings['outputFileName'] = outputName_entry.get()
    inputSettings['outputPath'] = outputPath_entry.get()
    inputSettings['inputPath'] = inputPath_entry.get()
    inputSettings['sortByTime'] = sort.get()
    inputSettings['inputFilesFormat'] = inputFilesFormat_combobox.get()
    input_window.destroy()

def saveDataViewSettings():
    dataViewSettings['dataType'] = dType_combobox.get()
    dataViewSettings['filterByYear'] = int(year_entry.get()) if year_entry.get() else None
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

    dataViewSettings['viewDataPoints'] = dataPoints.get()
    
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
                pass
    
    dataViewSettings['scaleSettings'] = scale_settings
    dataViewSettings['siteList'] = selectedSites
    dataViewSettings['parameterList'] = selectedParameters

def generatePanels():
    if dataViewSettings['dataType'] == 'mooring':
        if dataViewSettings['panel1'] == True:
            view.plot_database_panel1(database, dataViewSettings)
        if dataViewSettings['panel2'] == True:
            view.plot_database_panel2(database, dataViewSettings)
        if dataViewSettings['panel3'] == True:
            print('WARNING: Panel 3 is not suited for mooring data')
    elif dataViewSettings['dataType'] == 'tscp profile':
        if dataViewSettings['panel3'] == True:
            view.plot_database_panel3(database, dataViewSettings)
        if dataViewSettings['panel1'] == True or dataViewSettings['panel2'] == True:
            print('WARNING: Panels 1/2 are not suited for profile data')
    
    if dataViewSettings['tsDiagram'] == True:
        view.plot_TS_diagram(database, dataViewSettings)

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

# Create input settings window
input_window = Tk()
input_window.title("Database Input Settings")

try:
    # Try to load icon
    input_window.iconbitmap(resource_path(r"C:\Users\JoaoCardoso\QCS_SAGE_v2.0\sourceCode\qcsDataViewIcon.ico"))
except Exception as e:
    print(f"Não foi possível carregar o ícone: {e}")

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
helpmenu.add_command(label="About", command=lambda: messagebox.showinfo("About", "QCS Database View Tool\nVersion 2.0"))
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

input_window.mainloop()

# Prepare data
if inputSettings['joinFiles'] == True:
    database = data.join_files_to_database(inputSettings['inputPath'], inputSettings['inputFilesFormat'])
else:
    if inputSettings['databaseFileName'] != '':
        database = pd.read_excel(inputSettings['databaseFileName'])
    else:
        print('WARNING: Select a database file or provide a valid input folder')

if inputSettings['sortByTime'] == True:
    database.index = database['Datetime']
    database = database.rename_axis('dt_index')
    database = database.sort_values(by='dt_index')
    database.index = range(len(database))

database['Datetime'] = pd.to_datetime(database['Datetime'])

databaseViewPath = os.path.join(inputSettings['outputPath'], 'DatabaseView')
os.makedirs(databaseViewPath, exist_ok=True)
os.chdir(databaseViewPath)

if inputSettings['databaseFileName'] == '':
    database.to_excel(inputSettings['outputFileName']+'.xlsx')

# Create data view settings window
view_window = Tk()
view_window.title("Data View Settings")

try:
    # Try to load icon
    view_window.iconbitmap(resource_path(r"C:\Users\JoaoCardoso\QCS_SAGE_v2.0\sourceCode\qcsDataViewIcon.ico"))
except Exception as e:
    print(f"Não foi possível carregar o ícone: {e}")

view_window.geometry("1300x650")  # Aumentado para acomodar o novo frame
view_window.resizable(False, False)

# Add menu bar
menubar = Menu(view_window)
helpmenu = Menu(menubar, tearoff=0)
helpmenu.add_command(label="Help", command=show_help)
helpmenu.add_command(label="About", command=lambda: messagebox.showinfo("About", "QCS Database View Tool\nVersion 2.0"))
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
main_frame = ttk.Frame(scrollable_frame, padding="10")
main_frame.pack(fill='both', expand=True)

# Data settings frame
data_frame = ttk.LabelFrame(main_frame, text=" DATA SETTINGS ", padding=10)
data_frame.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")

# Visualization frame
vis_frame = ttk.LabelFrame(main_frame, text=" VISUALIZATION SETTINGS ", padding=10)
vis_frame.grid(row=1, column=0, padx=5, pady=5, sticky="nsew")

# Filter frame
filter_frame = ttk.LabelFrame(main_frame, text=" FILTER SETTINGS ", padding=10)
filter_frame.grid(row=1, column=1, padx=5, pady=5, sticky="nsew")

# Scale frame - Novo frame para definição de escalas
scale_frame = ttk.LabelFrame(main_frame, text=" SCALE SETTINGS ", padding=10)
scale_frame.grid(row=1, column=2, padx=5, pady=5, sticky="nsew")

# Configure grid weights
main_frame.columnconfigure(0, weight=1)
main_frame.columnconfigure(1, weight=1)
main_frame.columnconfigure(2, weight=1)
main_frame.rowconfigure(0, weight=1)
main_frame.rowconfigure(1, weight=1)

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

# --- Filter Settings ---
# Year filter
ttk.Label(filter_frame, text="Filter by Year:").grid(row=0, column=0, sticky='w', pady=(5,2))
year_entry = ttk.Entry(filter_frame, width=25)
year_entry.grid(row=1, column=0, sticky='w', pady=2)
ToolTip(year_entry, TOOLTIPS['filter_year'])

# Site selection
ttk.Label(filter_frame, text="Filter by Site:").grid(row=2, column=0, sticky='w', pady=(10,2))
ToolTip(ttk.Label(filter_frame), TOOLTIPS['site_filter'])

site_names = sorted(set(database['Site']))
site_vars = {}  # Armazena as BooleanVar
site_widgets = {}  # Armazena os widgets Checkbutton

for i, site in enumerate(site_names):
    var = BooleanVar(value=False)
    cb = ttk.Checkbutton(filter_frame, text=site, variable=var)
    cb.grid(row=i+3, column=0, sticky='w', pady=2)
    site_vars[site] = var
    site_widgets[site] = cb

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

ttk.Button(action_frame, text="Save View Settings", command=saveDataViewSettings).pack(side='left', padx=5)
ttk.Button(action_frame, text="Generate Panels", command=generatePanels, style='Accent.TButton').pack(side='left', padx=5)

# Initialize UI state
toggle_all_controls(enabled=False)  # Tudo desabilitado inicialmente
toggle_data_type()
toggle_panel_dependent_controls()
toggle_parameter_checkboxes()
toggle_ts_controls()

# Configure canvas scrolling
def _on_mousewheel(event):
    canvas.yview_scroll(int(-1*(event.delta/120)), "units")

canvas.bind_all("<MouseWheel>", _on_mousewheel)

view_window.mainloop()

os.chdir(rootPath)
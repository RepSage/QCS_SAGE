# system modules
import os
import re
import sys
import time
import json
import traceback
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from datetime import timedelta
from tkinter import *
import tkinter as tk
from tkinter import ttk
from tkinter import filedialog
from tkinter import messagebox
from scipy import signal

# software modules
import QCS_DataHandler as data
import QCS_DataView as view
import QCS_Tests as QC

# Global configuration
CONFIG = {
    'tsQualityTests': {
        'temperature sensor range': 'ON',
        'salinity sensor range': 'ON',
        'conductivity sensor range': 'ON',
        'pressure sensor range': 'ON',
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
        'density inversion': 'ON'
    },
    'tsSettings': {
        #'depth_range': 1.55,
        # Faixas de sensor (limite do instrumento - padrao Aanderaa SeaGuard II)
        'sensor_min_temp': -5,
        'sensor_max_temp': 40,
        'sensor_min_sal': 0,
        'sensor_max_sal': 45,
        'sensor_min_cond': 0,
        'sensor_max_cond': 75,
        'sensor_min_pres': 0,
        'sensor_max_pres': 6000,
        # Faixas ambientais (envelope climatologico amplo - toda a costa brasileira, v3.0)
        'env_min_temp': 8,
        'env_max_temp': 32,
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
        'rep_cnt_fail': 20,
        'rep_cnt_susp': 15,
        #'eps': 'AUTO',
        'time_window': '30M',
        'fail_factor': 3,
        'susp_factor': 2.5
    },
    'tsQualityTests_vars': {},
    'tsSettings_entries': {}
}

# Tooltips dictionary
TOOLTIPS = {
    'data_file': "Select the raw data file to be qualified\nSupported formats: .csv, .xlsx",
    'latitude': "Latitude of the collection site (degrees)\nUsed to convert pressure to depth",
    'config_file': "OPTIONAL: Select the configuration file (.json)\ncontaining quality test parameters",
    'input_type': "Type of instrument that generated the data\nSeaguard: Standard CTD\nHOBO: Autonomous logger",
    'data_type': "Data collection type\nProfile: Vertical data (cast)\nMooring: Fixed-point temporal data",
    'pressure_unit': "Pressure unit of raw data\nAutomatic conversion to decibar",
    'conductivity_unit': "Conductivity unit of raw data\nAutomatic conversion to mS/cm",
    'gmt_correction': "Applies GMT-3 hour correction for data\ncollected in Brazilian timezone",
    'profile_selection': "Allows selecting only descent or ascent\nfor profile data (removes inversion)",
    'variable_check': "Activates manual limit verification\nfor each variable before processing",
    'output_folder': "Folder where qualification results\nwill be saved",
    'output_name': "Base name for output files\n(without extension)",
    'output_format': "Output file format\n.csv: Delimited text\n.xlsx: Excel",
    'remove_bad': "Automatically removes data flagged\nas BAD (flag 4) in output",
    'remove_suspect': "Automatically removes data flagged\nas SUSPECT (flag 3) in output",
    'site_code': "Identification code for the\ncollection site (max 5 characters)",
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
    'rep_cnt_fail': "Number of repeated values to flag as FAIL\nFor flat line test",
    'rep_cnt_susp': "Number of repeated values to flag as SUSPECT\nFor flat line test",
    #'eps': "Epsilon value for flat line detection\nMinimum difference to consider values different",
    'time_window': "Time window for rate of change calculations\nFormat: '2D' (days), '3H' (hours), '30M' (minutes), '45S' (seconds) or 'WHOLE'",
    'fail_factor': "Multiplier for standard deviation to flag as FAIL\nUsed in spike and rate tests",
    'susp_factor': "Multiplier for standard deviation to flag as SUSPECT\nUsed in spike and rate tests"
}

TS_QUALITY_TESTS_TOOLTIPS = {
    'temperature sensor range': "Check if temperature values are within sensor specifications",
    'salinity sensor range': "Check if salinity values are within sensor specifications",
    'conductivity sensor range': "Check if conductivity values are within sensor specifications",
    'pressure sensor range': "Check if pressure values are within sensor specifications",
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
    'density inversion': "Check water column stability: potential density must not decrease with depth (profiles only)"
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
    filename = filedialog.askopenfilename(
        initialdir=USER_PREFS.get('last_data_dir', '/'),
        title="Select data file",
        filetypes=(("Data files", "*.csv *.xlsx"), ("All files", "*.*"))
    )
    if filename:
        fileNames_entry.delete(0, END)
        fileNames_entry.insert(0, filename)
        USER_PREFS['last_data_dir'] = os.path.dirname(filename)
        save_user_prefs()

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

def selectConfigFile():
    filepath = filedialog.askopenfilename(
        initialdir=USER_PREFS.get('last_config_dir', '/'),
        title="Select configuration file",
        filetypes=(("JSON files", "*.json"), ("All files", "*.*"))
    )
    if filepath:
        inputConfigPath_entry.delete(0, END)
        inputConfigPath_entry.insert(0, filepath)
        USER_PREFS['last_config_dir'] = os.path.dirname(filepath)
        save_user_prefs()

def export_config():
    # Atualiza as configurações atuais antes de exportar
    save_settings_values()
    
    filepath = filedialog.asksaveasfilename(
        defaultextension=".json",
        filetypes=(("JSON files", "*.json"), ("All files", "*.*")),
        title="Export settings"
    )
    
    if filepath:
        try:
            config_to_export = {
                "tsQualityTests": CONFIG['tsQualityTests'],
                "tsSettings": CONFIG['tsSettings']
            }
            
            with open(filepath, 'w') as f:
                json.dump(config_to_export, f, indent=4)
            
            messagebox.showinfo("Success", f"Success exporting settings:\n{filepath}")
        except Exception as e:
            messagebox.showerror("Error", f"Fail exporting settings:\n{str(e)}")

def save_settings_values():
    """Atualiza CONFIG com os valores atuais da interface"""
    # Update tsQualityTests
    for test, var in CONFIG['tsQualityTests_vars'].items():
        CONFIG['tsQualityTests'][test] = var.get()
    
    # Update tsSettings
    for param, entry in CONFIG['tsSettings_entries'].items():
        value = entry.get()
        
        if param == 'time_window':
            CONFIG['tsSettings'][param] = value
        elif '.' in value:
            try:
                CONFIG['tsSettings'][param] = float(value)
            except ValueError:
                pass
        else:
            try:
                CONFIG['tsSettings'][param] = int(value)
            except ValueError:
                pass

def collect_input_settings():
    """Valida e coleta as configuracoes da interface. Retorna True se tudo ok."""
    data_path = fileNames_entry.get().strip()
    if not data_path:
        messagebox.showwarning("Warning", "Select the data file to be qualified\n('Data File' field).")
        return False
    if not os.path.isfile(data_path):
        messagebox.showerror("Error", "Data file not found:\n%s" % data_path)
        return False
    if not re.search(r'\.(csv|xlsx)$', data_path, re.IGNORECASE):
        messagebox.showwarning("Warning", "Unsupported file format.\nUse .csv or .xlsx files.")
        return False
    if inputType_combobox.get() not in ('Seaguard', 'HOBO'):
        messagebox.showwarning("Warning", "Select the instrument type\n('Input Type' field).")
        return False
    if dType_combobox.get() not in ('TSCP Profile', 'TSCP Mooring'):
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

    INPUT['pressure_unit'] = pressure_unit_combobox.get() or 'decibar'
    INPUT['conductivity_unit'] = conductivity_unit_combobox.get() or 'mS/cm'
    INPUT['correct_gmt3h'] = correct_gmt3h.get()
    INPUT['select_profile_data'] = select_profile_data.get()
    INPUT['check_variables'] = check_variables.get()
    INPUT['input_config_path'] = inputConfigPath_entry.get()
    INPUT['input_type'] = inputType_combobox.get()
    INPUT['data_type'] = dType_combobox.get()

    # Carrega o arquivo de configuração JSON se foi especificado
    config_path = INPUT.get('input_config_path', '')
    if config_path and os.path.exists(config_path):
        try:
            with open(config_path, 'r') as f:
                config_data = json.load(f)

            # Atualiza apenas as configurações que existem no arquivo
            if 'tsQualityTests' in config_data:
                CONFIG['tsQualityTests'].update(config_data['tsQualityTests'])
            if 'tsSettings' in config_data:
                CONFIG['tsSettings'].update(config_data['tsSettings'])

        except Exception as e:
            messagebox.showerror("Error", f"Could not load the configuration file:\n{str(e)}")
            return False

    OUTPUT['output_file_path'] = out_dir
    OUTPUT['output_data_format'] = outputFilesFormat_combobox.get()
    OUTPUT['output_file_name'] = outputName_entry.get() + OUTPUT['output_data_format']
    OUTPUT['remove_bad'] = remove_bad.get()
    OUTPUT['remove_suspect'] = remove_suspect.get()

    INPUT['site'] = siteSelect_entry.get().upper()

    try:
        INPUT['latitude'] = float(latitude_entry.get())
    except ValueError:
        INPUT['latitude'] = 17.5

    if INPUT['data_type'] == 'TSCP Profile':
        INPUT['profile'] = True
    else:
        INPUT['profile'] = False

    # guarda as ultimas escolhas do usuario para a proxima sessao
    USER_PREFS.update({
        'data_file': data_path,
        'config_file': inputConfigPath_entry.get(),
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
        'latitude': latitude_entry.get(),
        'tsQualityTests': dict(CONFIG['tsQualityTests']),
        'tsSettings': dict(CONFIG['tsSettings']),
    })
    save_user_prefs()
    return True

def start_qualification():
    """Executa a qualificacao sem fechar a janela principal, permitindo novas execucoes."""
    if not collect_input_settings():
        return
    run_button.config(state='disabled')
    window.config(cursor='watch')
    window.update_idletasks()
    try:
        run_full_qualification()
        messagebox.showinfo("Done",
                            "Qualification completed successfully!\n\n"
                            "Results saved to:\n%s\n\n"
                            "You can select another file and run a new qualification "
                            "without closing the program." % OUTPUT.get('last_output_root', ''))
    except Exception as e:
        traceback.print_exc()
        messagebox.showerror("Qualification error",
                             "The qualification was interrupted by an error:\n\n%s\n\n"
                             "Some files may have been partially generated in the output "
                             "folder before the error. Check the input file and the "
                             "settings and try again." % e)
    finally:
        plt.close('all')
        os.chdir(rootPath)
        run_button.config(state='normal')
        window.config(cursor='')

def restore_user_prefs():
    """Restaura na interface as ultimas escolhas do usuario."""
    p = USER_PREFS

    def set_entry(entry, key):
        if p.get(key):
            entry.delete(0, END)
            entry.insert(0, p[key])

    set_entry(fileNames_entry, 'data_file')
    set_entry(inputConfigPath_entry, 'config_file')
    set_entry(outputPath_entry, 'output_folder')
    set_entry(outputName_entry, 'output_name')
    set_entry(siteSelect_entry, 'site_code')
    set_entry(latitude_entry, 'latitude')
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
    if isinstance(p.get('tsQualityTests'), dict):
        for k, v in p['tsQualityTests'].items():
            if k in CONFIG['tsQualityTests']:
                CONFIG['tsQualityTests'][k] = v
    if isinstance(p.get('tsSettings'), dict):
        for k, v in p['tsSettings'].items():
            if k in CONFIG['tsSettings']:
                CONFIG['tsSettings'][k] = v

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
    """
    messagebox.showinfo("QCS Help", help_text)

def open_settings_window():
    settings_win = Toplevel()
    settings_win.title(" Quality Control Settings")
    settings_win.geometry("900x700")

    notebook = ttk.Notebook(settings_win)
    notebook.pack(fill='both', expand=True)
    
    # Tests Tab
    tests_frame = ttk.Frame(notebook)
    notebook.add(tests_frame, text="Quality Control Tests")
    create_tests_tab(tests_frame)
    
    # Parameters Tab
    params_frame = ttk.Frame(notebook)
    notebook.add(params_frame, text="Parameters")
    create_params_tab(params_frame)
    
    # Button frame
    button_frame = ttk.Frame(settings_win)
    button_frame.pack(fill='x', pady=10)
    
    ttk.Button(button_frame, text="Export Settings", 
              command=export_config, width=20).pack(side='left', padx=5)
    
    ttk.Button(button_frame, text="Save Settings", 
              command=lambda: save_settings(settings_win),
              style='Accent.TButton').pack(side='right', padx=5)

def create_tests_tab(parent):
    canvas = Canvas(parent)
    scrollbar = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
    scrollable_frame = ttk.Frame(canvas)
    
    scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
    canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)
    
    canvas.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")
    
    # Organize tests into categories
    test_categories = {
        "Sensor Range Tests": [
            'temperature sensor range',
            'salinity sensor range',
            'conductivity sensor range',
            'pressure sensor range'
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
        "Vertical Gradient Tests": [
            'temperature vertical gradient',
            'salinity vertical gradient',
            'conductivity vertical gradient'
        ],
        "Profile Stability Tests": [
            'density inversion'
        ]
    }
    
    row = 0
    for category, tests in test_categories.items():
        lbl = ttk.Label(scrollable_frame, text=category, font=('Arial', 10, 'bold'))
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

def create_params_tab(parent):
    canvas = Canvas(parent)
    scrollbar = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
    scrollable_frame = ttk.Frame(canvas)
    
    scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
    canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)
    
    canvas.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")
    
    categories = {
        "Sensor Range": [k for k in CONFIG['tsSettings'] if 'sensor_' in k],
        "Environmental Range": [k for k in CONFIG['tsSettings'] if 'env_' in k],
        "Other Parameters": [k for k in CONFIG['tsSettings'] if not ('sensor_' in k or 'env_' in k)]
    }
    
    row = 0
    for category, params in categories.items():
        lbl = ttk.Label(scrollable_frame, text=category, font=('Arial', 10, 'bold'))
        lbl.grid(row=row, column=0, sticky='w', pady=(10,5), columnspan=3)
        row += 1
        
        for param in params:
            lbl = ttk.Label(scrollable_frame, text=param.replace('_', ' ').title() + ":")
            lbl.grid(row=row, column=0, sticky='e', padx=5, pady=2)
            
            ent = ttk.Entry(scrollable_frame, width=12)
            ent.insert(0, str(CONFIG['tsSettings'][param]))
            ent.grid(row=row, column=1, sticky='w', pady=2)
            
            # Add tooltips for each parameter
            ToolTip(lbl, TS_SETTINGS_TOOLTIPS[param])
            ToolTip(ent, TS_SETTINGS_TOOLTIPS[param])
            
            unit = ""
            if 'temp' in param:
                unit = "°C"
            elif 'sal' in param:
                unit = "PSU"
            elif 'cond' in param:
                unit = "mS/cm"
            elif 'pres' in param:
                unit = "dbar"
            elif 'chl' in param:
                unit = "μg/L"
            elif 'O2' in param:
                unit = "μM"
            
            if unit:
                ttk.Label(scrollable_frame, text=unit).grid(row=row, column=2, sticky='w', padx=5)
            
            CONFIG['tsSettings_entries'][param] = ent
            row += 1

def save_settings(window):
    save_settings_values()
    messagebox.showinfo("Success", "Success saving settings!")
    window.destroy()

# Main application
INPUT = {}
OUTPUT = {}
rootPath = os.getcwd()

# Create main window
window = Tk()
window.title("QCS - Data Qualification Tool %s" % data.QCS_VERSION)

window.geometry("750x650")
window.resizable(True, True)

# Configure styles
style = ttk.Style()
style.theme_use('clam')
style.configure('TFrame', background='#f0f0f0')
style.configure('TLabel', background='#f0f0f0', font=('Arial', 10))
style.configure('Header.TLabel', font=('Arial', 10, 'bold'))
style.configure('TButton', padding=5)
style.configure('Accent.TButton', foreground='white', background='#4a90e2', font=('Arial', 10, 'bold'))
style.configure('Help.TButton', foreground='white', background='#666666', font=('Arial', 9))
style.map('Accent.TButton', background=[('active', '#3a7bc8')])

style.configure('TLabel', background='#f0f0f0', font=('Arial', 10))
style.configure('TFrame', background='#f0f0f0')
style.configure('TLabelframe', background='#f0f0f0')
style.configure('TLabelframe.Label', background='#f0f0f0')
style.configure('TEntry', fieldbackground='white')
style.configure('TCombobox', fieldbackground='white')

style.configure('Help.TButton', foreground='white', background='#666666', 
               font=('Arial', 9), borderwidth=0)
style.map('Help.TButton', 
         background=[('active', '#666666')],
         foreground=[('active', 'white')])

# Add menu bar
menubar = Menu(window)
helpmenu = Menu(menubar, tearoff=0)
helpmenu.add_command(label="Help", command=show_help)
helpmenu.add_command(label="About QCS", command=lambda: messagebox.showinfo("About",
                       "QCS - Quality Control System\nVersion %s\nDeveloped for automatic data qualification\n" % data.QCS_VERSION))
menubar.add_cascade(label="Menu", menu=helpmenu)
window.config(menu=menubar)

# Main container
main_frame = ttk.Frame(window, padding="10")
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
ttk.Label(input_frame, text="Data File:", style='Header.TLabel').grid(row=0, column=0, sticky='w', pady=(0,2))
fileNames_entry = ttk.Entry(input_frame, width=30)
fileNames_entry.grid(row=1, column=0, sticky='ew', pady=(0,5))
ToolTip(fileNames_entry, TOOLTIPS['data_file'])

browse_file_btn = ttk.Button(input_frame, text="Browse...", command=selectFiles, width=10)
browse_file_btn.grid(row=1, column=1, padx=5)
ToolTip(browse_file_btn, TOOLTIPS['data_file'])

# Config file
ttk.Label(input_frame, text="Config File:", style='Header.TLabel').grid(row=2, column=0, sticky='w', pady=(0,2))
inputConfigPath_entry = ttk.Entry(input_frame, width=30)
inputConfigPath_entry.grid(row=3, column=0, sticky='ew', pady=(0,5))
ToolTip(inputConfigPath_entry, TOOLTIPS['config_file'])

browse_config_btn = ttk.Button(input_frame, text="Browse...", command=selectConfigFile, width=10)
browse_config_btn.grid(row=3, column=1, padx=5)
ToolTip(browse_config_btn, TOOLTIPS['config_file'])

# Data type selection
ttk.Label(input_frame, text="Input Type:", style='Header.TLabel').grid(row=4, column=0, sticky='w', pady=(0,2))
inputType_combobox = ttk.Combobox(input_frame, values=["Seaguard", "HOBO"], width=15)
inputType_combobox.grid(row=5, column=0, sticky='w', pady=(0,5))
ToolTip(inputType_combobox, TOOLTIPS['input_type'])

ttk.Label(input_frame, text="Data Type:", style='Header.TLabel').grid(row=4, column=1, sticky='w', pady=(0,2))
dType_combobox = ttk.Combobox(input_frame, values=["TSCP Profile", "TSCP Mooring"], width=15)
dType_combobox.grid(row=5, column=1, sticky='w', pady=(0,5))
ToolTip(dType_combobox, TOOLTIPS['data_type'])

# update profile checkbox
def update_profile_checkbox_state(event=None):
    if dType_combobox.get() == "TSCP Profile":
        profile_check.config(state="normal")
    else:
        profile_check.config(state="disabled")
        select_profile_data.set(False)  # Desmarca o checkbox se não for perfil

# bind to combobox selection
dType_combobox.bind("<<ComboboxSelected>>", update_profile_checkbox_state)

# Units selection
units_frame = ttk.LabelFrame(input_frame, text=" Units ", padding=5)
units_frame.grid(row=6, column=0, columnspan=2, sticky='ew', pady=5)

ttk.Label(units_frame, text="Pressure:").grid(row=0, column=0, sticky='w')
pressure_unit_combobox = ttk.Combobox(units_frame, values=["decibar", "bar", "kPa"], width=10)
pressure_unit_combobox.grid(row=0, column=1, padx=5, pady=2)
ToolTip(pressure_unit_combobox, TOOLTIPS['pressure_unit'])

ttk.Label(units_frame, text="Conductivity:").grid(row=1, column=0, sticky='w')
conductivity_unit_combobox = ttk.Combobox(units_frame, values=["mS/cm", "S/m"], width=10)
conductivity_unit_combobox.grid(row=1, column=1, padx=5, pady=2)
ToolTip(conductivity_unit_combobox, TOOLTIPS['conductivity_unit'])

# Options checkboxes
options_frame = ttk.Frame(input_frame)
options_frame.grid(row=7, column=0, columnspan=2, sticky='ew', pady=5)

correct_gmt3h = BooleanVar(value=False)
gmt_check = ttk.Checkbutton(options_frame, text="Correct GMT-3", variable=correct_gmt3h)
gmt_check.pack(anchor='w', pady=2)
ToolTip(gmt_check, TOOLTIPS['gmt_correction'])

select_profile_data = BooleanVar(value=False)
profile_check = ttk.Checkbutton(options_frame, text="Select Profile Data", variable=select_profile_data)
profile_check.pack(anchor='w', pady=2)
profile_check.config(state="disabled")  # Começa desabilitado
ToolTip(profile_check, TOOLTIPS['profile_selection'])

check_variables = BooleanVar(value=False)
var_check = ttk.Checkbutton(options_frame, text="Check Variables", variable=check_variables)
var_check.pack(anchor='w', pady=2)
ToolTip(var_check, TOOLTIPS['variable_check'])

# --- Output Section ---
# Output folder
ttk.Label(output_frame, text="Output Folder:", style='Header.TLabel').grid(row=0, column=0, sticky='w', pady=(0,2))
outputPath_entry = ttk.Entry(output_frame, width=30)
outputPath_entry.grid(row=1, column=0, sticky='ew', pady=(0,5))
ToolTip(outputPath_entry, TOOLTIPS['output_folder'])

browse_output_btn = ttk.Button(output_frame, text="Browse...", command=selectOutputFolder, width=10)
browse_output_btn.grid(row=1, column=1, padx=5)
ToolTip(browse_output_btn, TOOLTIPS['output_folder'])

# File naming
ttk.Label(output_frame, text="Output File Name:", style='Header.TLabel').grid(row=2, column=0, sticky='w', pady=(0,2))
outputName_entry = ttk.Entry(output_frame, width=30)
outputName_entry.grid(row=3, column=0, sticky='ew', pady=(0,5))
ToolTip(outputName_entry, TOOLTIPS['output_name'])

# Output format
ttk.Label(output_frame, text="Output Format:", style='Header.TLabel').grid(row=4, column=0, sticky='w', pady=(0,2))
outputFilesFormat_combobox = ttk.Combobox(output_frame, values=[".csv", ".xlsx"], width=8)
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

# Latitude (used to convert pressure to depth)
ttk.Label(input_frame, text="Latitude (deg):", style='Header.TLabel').grid(row=8, column=0, sticky='w', pady=(5,2))
latitude_entry = ttk.Entry(input_frame, width=12)
latitude_entry.insert(0, "17.5")
latitude_entry.grid(row=9, column=0, sticky='w', pady=(0,5))
ToolTip(latitude_entry, TOOLTIPS['latitude'])

# Action buttons
action_frame = ttk.Frame(main_frame)
action_frame.grid(row=1, column=0, columnspan=2, pady=10)

help_btn = ttk.Button(action_frame, text="Help", command=show_help, style='Help.TButton', width=10)
help_btn.pack(side='left', padx=5)

settings_btn = ttk.Button(action_frame, text="Settings", command=open_settings_window, style='Help.TButton', width=12)
settings_btn.pack(side='left', padx=5)
ToolTip(settings_btn, TOOLTIPS['settings_button'])

run_button = ttk.Button(action_frame, text="RUN QUALIFICATION", command=start_qualification, style='Accent.TButton')
run_button.pack(side='left', padx=5, ipadx=20, ipady=5)
ToolTip(run_button, TOOLTIPS['run_button'])

# The whole qualification pipeline runs inside this function so the main
# window stays open and the user can qualify several files in sequence.
def run_full_qualification():
    tsSettings = CONFIG['tsSettings']
    tsQualityTests = CONFIG['tsQualityTests']

    # change to folder containing raw data
    os.chdir(INPUT['raw_data_path'])

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
        fullFrame, tempFrame, lumiFrame = data.read_unified_hobo(INPUT['file_name'])
        raw_data = tempFrame
        for test in tsQualityTests:
            if re.search('spikes', test, re.IGNORECASE):
                tsQualityTests[test] = 'OFF'
            if re.search('rate of change', test, re.IGNORECASE):
                tsQualityTests[test] = 'OFF'
            if re.search('vertical gradient', test, re.IGNORECASE):
                tsQualityTests[test] = 'OFF'
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

    # handle non-physical values <= 0 (optical sensors keep small negatives as ~0)
    raw_data = data.clean_below_zero(raw_data, tsSettings)

    #removing data where depth is under 0.5 for profile data
    if INPUT['profile'] == True:
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
                        raise ValueError("Nenhum pico encontrado para as condições fornecidas.")
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

                    def acceptPeak():
                        print('MESSAGE: Peak accepted, proceding to profile selection')
                        ans.append('y')
                        plt.close(fig1)
                        peak_window.destroy()

                    def doNotAcceptPeak():
                        print('MESSAGE: Ignoring data peak, data qualification will continue with the whole dataset')
                        plt.close(fig1)
                        peak_window.destroy()

                    peak_window.title("Peak Validation")
                    peak_window.geometry("225x80")
                    peak_window.resizable(True, True)
                    peak_window.configure(bg="#f0f0f0")
                    # upper label
                    dPeak_label = Label(peak_window, text="       Do you accept data peak?", bg=peak_window["bg"])
                    dPeak_label.grid(row=0, column=0, sticky='w', padx=15, pady=5)
                    # buttons for yeas and no
                    yesButton = Button(peak_window, text="Yes", command=acceptPeak)
                    yesButton.configure(bg="lightgray")
                    yesButton.grid(row=1, column=0, sticky='w', padx=5, pady=5)
                    noButton = Button(peak_window, text="No", command=doNotAcceptPeak)
                    noButton.configure(bg="lightgray")
                    noButton.grid(row=1, column=1, sticky='w', padx=0, pady=5)
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
                        ax2.set_title('click on the dataset to select it:')
                        ax2.set_xlabel('Temperature (degC)')
                        ax2.set_ylabel('Depth (m)')
                        ax2.legend()
                        ax2.invert_yaxis()
                        ax2.grid()

                        selected = None
                        def on_pick(event):
                            nonlocal selected
                            selected = event.artist.get_label()
                            plt.close(fig2)

                        line1.set_picker(True)
                        line2.set_picker(True)
                        fig2.canvas.mpl_connect('pick_event', on_pick)
                        fig2.canvas.mpl_connect('motion_notify_event', data.on_motion)
                        plt.show(block=True)

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


    if INPUT['profile'] == False and 'Depth (m)' in raw_data.columns:
        raw_data = data.trim_by_depth(raw_data)
    
    # number of lines and cells
    n_cel = 1
    n_samples = len(raw_data)

    if INPUT['check_variables'] == True:
        check_variables = ['O2 level (uM)', 'Temperature (degC)','Conductivity (mS/cm)', 'Salinity (PSU)', 'Density (kg/m3)',
                            'PAR (umol/m2/s)', 'Turbidity (FTU)', 'Chlorophyll (ug/L)', 'pH', 'Dissolved organic matter (ppb)']
        for name in check_variables:
            if name in raw_data.columns:
                raw_data = data.trim_selected_variable(raw_data, name)
    #create list for flag codes
    flags = ['' for n in range(len(raw_data))]

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

    def run_range_test(min_key, max_key):
        return lambda column, flags: QC.range_test(raw_data[column], flags,
                                                   range_min=tsSettings[min_key],
                                                   range_max=tsSettings[max_key])

    def run_spike_test(column, flags):
        return QC.outlier_test(raw_data, column, n_cel, flags, tsSettings['time_window'],
                               ms_interval, tsSettings['fail_factor'], tsSettings['susp_factor'])

    def run_rate_of_change_test(column, flags):
        return QC.sigma_rate_of_change_test(n_samples, raw_data[column], n_cel, flags,
                                            ms_interval=ms_interval, time_window=tsSettings['time_window'],
                                            rc_fail=tsSettings['fail_factor'], rc_susp=tsSettings['susp_factor'],
                                            DIR=False)

    def run_flat_line_test(column, flags):
        return QC.single_flat_line_test(n_samples, n_cel, raw_data[column], flags,
                                        rep_cnt_fail=tsSettings['rep_cnt_fail'],
                                        rep_cnt_suspect=tsSettings['rep_cnt_susp'])

    def run_vertical_gradient_test(column, flags):
        return QC.vertical_gradient_test(n_samples, raw_data[column], n_cel, flags,
                                         ms_interval=ms_interval, time_window=tsSettings['time_window'],
                                         rc_fail=tsSettings['fail_factor'], rc_susp=tsSettings['susp_factor'],
                                         DIR=False)

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
            flags = test_runner(matched_column, flags)
        else:
            flags = [flags[n] + '%d' % QC.QC_flags.DISMISSED for n in range(n_samples)]
        tf = time.time()
        N = data.count_test_bdata(flags)
        print('%s test: %f s\nReproved: %i (%f%%)\n' % (test_label, (tf - ti), N, (N / n_samples) * 100))
        return flags

    # The param key (1st item) of each test feeds flag_layout below, which maps every
    # flag character to its variable in data.handle_output_file — positions are no
    # longer hardcoded, so the mapping follows whatever order is used here.
    test_sequence = [
        ('T',   'Temperature sensor range',  'temperature sensor range',  run_range_test('sensor_min_temp', 'sensor_max_temp')),
        ('S',   'Salinity sensor range',     'salinity sensor range',     run_range_test('sensor_min_sal', 'sensor_max_sal')),
        ('C',   'Conductivity sensor range', 'conductivity sensor range', run_range_test('sensor_min_cond', 'sensor_max_cond')),
        ('P',   'Pressure sensor range',     'pressure sensor range',     run_range_test('sensor_min_pres', 'sensor_max_pres')),
        ('T',   'Temperature environmental range',  'temperature environmental range',  run_range_test('env_min_temp', 'env_max_temp')),
        ('S',   'Salinity environmental range',     'salinity environmental range',     run_range_test('env_min_sal', 'env_max_sal')),
        ('C',   'Conductivity environmental range', 'conductivity environmental range', run_range_test('env_min_cond', 'env_max_cond')),
        ('P',   'Pressure environmental range',     'pressure environmental range',     run_range_test('env_min_pres', 'env_max_pres')),
        ('pH',  'pH environmental range',           'pH environmental range',           run_range_test('env_min_pH', 'env_max_pH')),
        ('chl', 'Chlorophyll environmental range',  'chlorophyll environmental range',  run_range_test('env_min_chl', 'env_max_chl')),
        ('O2',  'Dissolved oxygen environmental range', 'dissolved oxygen environmental range', run_range_test('env_min_O2', 'env_max_O2')),
        ('org', 'Dissolved organic matter environmental range', 'dissolved organic matter environmental range', run_range_test('env_min_org', 'env_max_org')),
        ('tur', 'Turbidity environmental range',    'turbidity environmental range',    run_range_test('env_min_tur', 'env_max_tur')),
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

    # records which variable each appended flag character belongs to, so
    # handle_output_file maps flag positions to variables without hardcoding them
    flag_layout = [entry[0] for entry in test_sequence]

    for param_key, test_label, test_switch, test_runner in test_sequence:
        flags = apply_quality_test(flags, param_key, test_label, test_switch, test_runner)

    # Density inversion test (profiles only) -> flag position 33.
    # Always appends one character for profiles so the flag layout stays fixed.
    if INPUT['profile'] == True:
        ti = time.time()
        if tsQualityTests.get('density inversion', 'OFF') == 'ON':
            flags = QC.density_inversion_test(raw_data, flags, tolerance=0.03,
                                              lat=INPUT.get('latitude', 17.5), lon=-40.0)
        else:
            flags = [flags[n] + '%d' % QC.QC_flags.DISMISSED for n in range(n_samples)]
        flag_layout.append('dens')
        tf = time.time()
        N = data.count_test_bdata(flags)
        print('Density inversion test: %f s\nReproved: %i (%f%%)\n' % ((tf - ti), N, (N / n_samples) * 100))

    end = time.time()
    print('\nProcessing time: %f s\n' %(end - start))

    print('\nCreating output table\n')
    qualified_data, raw_data, T_bdata, S_bdata, C_bdata, P_bdata, pH_bdata, chl_bdata, O2_bdata, org_bdata, tur_bdata, T_sdata, S_sdata, C_sdata, P_sdata, pH_sdata, chl_sdata, O2_sdata, org_sdata, tur_sdata, T_mdata, S_mdata, C_mdata, P_mdata, pH_mdata, chl_mdata, O2_mdata, org_mdata, tur_mdata = data.handle_output_file (raw_data, flags, flag_layout, remove_suspect=OUTPUT['remove_suspect'], remove_bad=OUTPUT['remove_bad'])

    # add luminosity data to dataframe if input is hobo
    if INPUT['input_type'] == 'HOBO':
        qualified_data['Luminosity (lux)'] = lumiFrame['Luminosity (lux)']

    qualified_data = data.order_var (qualified_data, n_cel, data_type='tscp')
    # Fill column with site information
    qualified_data['Site'] = INPUT['site']
    # Fill column with site information
    qualified_data['QCS version'] = data.QCS_VERSION
    # Export qualified data to .csv/.xlsx file
    os.chdir(OUTPUT['output_file_path'])
    root_path = OUTPUT['output_file_path'] + '/' + re.search(r'^[^\.]+',INPUT['file_name']).group()
    os.makedirs(root_path, exist_ok=True)
    path = root_path + '/QCS qualified tscp data/'
    os.makedirs(path, exist_ok=True)
    dataview_path =  root_path + '/QCS DataView (fixed scale)/'
    dataview_path2 = root_path + '/QCS DataView (unfixed scale)/'
    if INPUT['input_type'] != 'HOBO':
        os.makedirs(dataview_path, exist_ok=True)
        os.makedirs(dataview_path2, exist_ok=True)

    # the qualified file uses the name typed in 'Output File Name';
    # falls back to '<input name>_QLF' when the field resolves empty
    output_base = re.sub(r'\.(csv|xlsx)$', '', OUTPUT['output_file_name'], flags=re.IGNORECASE).strip()
    if not output_base:
        output_base = re.search(r'^[^\.]+', INPUT['file_name']).group() + '_QLF'
    if re.search('xlsx', OUTPUT['output_data_format'], re.IGNORECASE):
        qualified_data.to_excel(os.path.join(path, output_base + '.xlsx'), index=False) ##cria excel
    if re.search('csv', OUTPUT['output_data_format'], re.IGNORECASE):
        qualified_data.to_csv(os.path.join(path, output_base + '.csv'), index=False) ##cria csv
    print('\nExported data to: %s\n' %path)

    print('\nExporting statistics table to: %s\n' %path)
    stat_table = data.tscp_stats_table (qualified_data)
    stat_table.to_csv(path + '/QCS_tscp_stat.csv', index=False)
    print('\nExporting report to: %s\n' %path)
    all_bad = np.union1d(np.union1d(T_bdata, S_bdata), np.union1d(C_bdata, P_bdata))
    QCS_report = pd.DataFrame({'start': start_time,
                                'end': end_time,
                                'Total': len(qualified_data),
                                'Valid': len(qualified_data) - len(all_bad),
                                'T_bdata': len(T_bdata),
                                'S_bdata': len(S_bdata),
                                'C_bdata': len(C_bdata),
                                'P_bdata': len(P_bdata)}, index=[0])
    QCS_report.to_csv(path + '/QCS_report.csv')

    if INPUT['input_type'] != 'HOBO':
        if INPUT['profile'] == True:
            exceptions = ['Datetime', 'Expedition', 'Pressure (dbar)',
                            'Site', 'Longitude', 'Latitude', 'Depth (m)',
                            'Battery voltage (V)', 'Flag', 'Sample number', 'QCS version']
            for variable in qualified_data.keys():
                if variable not in exceptions:
                    view.plot_variable_profile(qualified_data, raw_data, variable, dataview_path, tsSettings, fixed_scale=True)
        else:
            for variable in qualified_data.keys():
                exceptions = ['Datetime', 'Expedition',
                                'Site', 'Longitude', 'Latitude',
                                'Battery voltage (V)', 'Flag', 'Sample number', 'QCS version']
                if variable not in exceptions:
                    view.plot_variable(qualified_data, raw_data, variable, dataview_path, tsSettings, fixed_scale=True)

        if INPUT['profile'] == True:
            exceptions = ['Datetime', 'Expedition', 'Pressure (dbar)',
                            'Site', 'Longitude', 'Latitude', 'Depth (m)',
                            'Battery voltage (V)', 'Flag', 'Sample number', 'QCS version']
            for variable in qualified_data.keys():
                if variable not in exceptions:
                    view.plot_variable_profile(qualified_data, raw_data, variable, dataview_path2, tsSettings, fixed_scale=False)
        else:
            for variable in qualified_data.keys():
                exceptions = ['Datetime', 'Expedition',
                                'Site', 'Longitude', 'Latitude',
                                'Battery voltage (V)', 'Flag', 'Sample number', 'QCS version']
                if variable not in exceptions:
                    view.plot_variable(qualified_data, raw_data, variable, dataview_path2, tsSettings, fixed_scale=False)
    #elif INPUT['input_type'] == 'HOBO':
    #    view.plot_hobo_split_site (database, dataview_path2)
    OUTPUT['last_output_root'] = root_path
    plt.close('all')
    os.chdir(rootPath)
    print('\nQualification finished.\n')

# restore last user choices and start the interface
restore_user_prefs()
window.mainloop()

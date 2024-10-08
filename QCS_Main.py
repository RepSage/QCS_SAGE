#system modules
import os
import re
import time
import numpy as np # type: ignore
import pandas as pd # type: ignore
import matplotlib.pyplot as plt # type: ignore
from io import StringIO
from string import Template
from datetime import datetime as dt
from datetime import timedelta
from tkinter import *
import tkinter as tk
from tkinter import ttk
from tkinter import filedialog
import warnings
#software modules
import QCS_DataHandler as data
import QCS_DataView as view
import QCS_Tests as QC

rootPath = os.getcwd()
# define functions
def selectFiles ():
    # Open a file dialog to select multiple files
    filenames = filedialog.askopenfilenames(initialdir="/", title="Select files")
    # Clear the entry widget for file names
    fileNames_entry.delete(0, END)
    # Insert the selected file names into the entry widget separated by semicolons
    fileNames_entry.insert(0, ";".join(filenames))

def selectOutputFolder ():
    # Open a file dialog to select the output folder
    folderPath = filedialog.askdirectory(initialdir="/", title="Select output folder")
    # Clear the entry widget for the output path
    outputPath_entry.delete(0, END)
    # Insert the selected folder path into the entry widget
    outputPath_entry.insert(0, folderPath)

def selectInputConfigFolder ():
    # Open a file dialog to select the output folder
    folderPath = filedialog.askdirectory(initialdir="/", title="Select output folder")
    # Clear the entry widget for the output path
    inputConfigPath_entry.delete(0, END)
    # Insert the selected folder path into the entry widget
    inputConfigPath_entry.insert(0, folderPath)

def doNotAcceptPeak ():
    print('MESSAGE: Ignoring data peak, data qualification will continue with the whole dataset')
    plt.close(fig1)
    window.destroy()

def acceptPeak ():
    print('MESSAGE: Peak accepted, proceding to profile selection')
    ans.append('y')
    plt.close(fig1)
    window.destroy()

def saveInputSettings():
    # reset inputSettings dictionary
    #inputSettings = {}
    # Save the settings into the inputSettings dictionary
    INPUT['file_name'] = re.search(r'[^\\/]+$', fileNames_entry.get(), re.IGNORECASE).group()
    INPUT['raw_data_path'] = fileNames_entry.get()
    INPUT['raw_data_path'] = INPUT['raw_data_path'][:-len(INPUT['file_name'])]
    INPUT['pressure_unit'] = pressure_unit_combobox.get()
    INPUT['conductivity_unit'] = conductivity_unit_combobox.get()
    INPUT['correct_gmt3h'] = correct_gmt3h.get()
    INPUT['select_profile_data'] = select_profile_data.get()
    INPUT['check_variables'] = check_variables.get()
    INPUT['input_config_path'] = inputConfigPath_entry.get()
    INPUT['input_type'] = inputType_combobox.get()
    INPUT['data_type'] = dType_combobox.get()

    OUTPUT['output_file_path'] = outputPath_entry.get()
    OUTPUT['output_data_format'] = outputFilesFormat_combobox.get()
    OUTPUT['output_file_name'] = outputName_entry.get() + OUTPUT['output_data_format']
    OUTPUT['remove_bad'] = remove_bad.get()
    OUTPUT['remove_suspect'] = remove_suspect.get()
    # get site list from markers
    selectedSites = []
    for site in siteMarkers.keys():
        if siteMarkers[site].get() == True:
            if site in selectedSites:
                pass
            else:
                selectedSites.append(site)
    INPUT['site'] = selectedSites[0]
    if INPUT['data_type'] == 'TSCP Profile':
        INPUT['profile'] = True
    else:
        INPUT['profile'] = False
    # Close the window
    window.destroy()


INPUT = {}
OUTPUT = {}
############################## interactive tools ###############################
# Create window 1
window = Tk()
window.title("Input and Output Settings")
window.geometry("1000x640")
window.resizable(True, True)
window.configure(bg="lightblue")
font_style = ("Arial", 12, "bold")
################################################################################
###################### Create the components of the window #####################
################################# column 1
#### fileDialog
# fileDialog upper label
fileNames_label = Label(window, text="Select Data File:", bg=window["bg"])
fileNames_label.grid(row=0, column=0, sticky='w', padx=15, pady=5)
# fileDialog entry space
fileNames_entry = Entry(window, width=25)
fileNames_entry.grid(row=1, column=0, sticky='w', padx=15, pady=5)
# fileDialog button
search_button = Button(window, text="Search File", command=selectFiles)
search_button.configure(bg="lightgray")
search_button.grid(row=2, column=0, sticky='w', padx=15, pady=5)
#### Input config folderDialog
# Input folderDialog label
inputConfigPath_label = Label(window, text="Configuration File Path:", bg=window["bg"])
inputConfigPath_label.grid(row=3, column=0, sticky='w', padx=15, pady=5)
# Input folderDialog entry space
inputConfigPath_entry = Entry(window, width=40)
inputConfigPath_entry.grid(row=4, column=0, sticky='w', padx=15, pady=5)
# Input folderDialog button
inputConfigPath_button = Button(window, text="Search Folder", command=selectInputConfigFolder)
inputConfigPath_button.configure(bg="lightgray")
inputConfigPath_button.grid(row=5, column=0, sticky='w', padx=15, pady=5)
#### dataType drop-down list
inputType_label = Label(window, text="Input Type:", bg=window["bg"])
inputType_label.grid(row=6, column=0, sticky='w', padx=15, pady=5)

inputType_combobox = ttk.Combobox(window, values=["Seaguard", "HOBO"])
inputType_combobox.configure(width=25)
inputType_combobox.grid(row=7, column=0, sticky='w', padx=15, pady=5)
#### dataType drop-down list
dType_label = Label(window, text="Data Type:", bg=window["bg"])
dType_label.grid(row=8, column=0, sticky='w', padx=15, pady=5)

dType_combobox = ttk.Combobox(window, values=["TSCP Profile", "TSCP Mooring"])
dType_combobox.configure(width=25)
dType_combobox.grid(row=9, column=0, sticky='w', padx=15, pady=5)
#### marker for correcting time
correct_gmt3h = BooleanVar(value=False)
correct_gmt3hButton = Checkbutton(window, text="Correct GMT 3H", variable=correct_gmt3h, bg="lightblue")
correct_gmt3hButton.grid(row=10, column=0, sticky='w', padx=15, pady=5)
#### marker for selecting profile
select_profile_data = BooleanVar(value=False)
select_profile_dataButton = Checkbutton(window, text="Choose Ascending/ Descending Profile", variable=select_profile_data, bg="lightblue")
select_profile_dataButton.grid(row=11, column=0, sticky='w', padx=15, pady=5)
#### marker for checking variables
check_variables = BooleanVar(value=False)
check_variablesButton = Checkbutton(window, text="Check Variables", variable=check_variables, bg="lightblue")
check_variablesButton.grid(row=12, column=0, sticky='w', padx=15, pady=5)
#### dataType drop-down list
pressure_unit_label = Label(window, text="Pressure Unit:", bg=window["bg"])
pressure_unit_label.grid(row=13, column=0, sticky='w', padx=15, pady=5)

pressure_unit_combobox = ttk.Combobox(window, values=["decibar", "bar", "kPa"])
pressure_unit_combobox.configure(width=25)
pressure_unit_combobox.grid(row=14, column=0, sticky='w', padx=15, pady=5)
#### dataType drop-down list
conductivity_unit_label = Label(window, text="Conductivity Unit:", bg=window["bg"])
conductivity_unit_label.grid(row=15, column=0, sticky='w', padx=15, pady=5)

conductivity_unit_combobox = ttk.Combobox(window, values=["mS/cm", "S/m"])
conductivity_unit_combobox.configure(width=25)
conductivity_unit_combobox.grid(row=16, column=0, sticky='w', padx=15, pady=5)
################################# column 2
#### Ouput folderDialog
# Ouput folderDialog label
outputPath_label = Label(window, text="Output Path:", bg=window["bg"])
outputPath_label.grid(row=0, column=1, sticky='w', padx=15, pady=5)
# Ouput folderDialog entry space
outputPath_entry = Entry(window, width=40)
outputPath_entry.grid(row=1, column=1, sticky='w', padx=15, pady=5)
# Ouput folderDialog button
outputPath_button = Button(window, text="Search Folder", command=selectOutputFolder)
outputPath_button.configure(bg="lightgray")
outputPath_button.grid(row=2, column=1, sticky='w', padx=15, pady=5)
#### Output naming
# Output naming upper label
output_label = Label(window, text="Output File Name:", bg=window["bg"])
output_label.grid(row=3, column=1, sticky='w', padx=15, pady=5)
# Output naming entry space
outputName_entry = Entry(window, width=40)
outputName_entry.grid(row=4, column=1, sticky='w', padx=15, pady=5)
#### Output format drop-down list
outputFilesFormat_label = Label(window, text="Output Files Format:", bg=window["bg"])
outputFilesFormat_label.grid(row=5, column=1, sticky='w', padx=15, pady=5)

outputFilesFormat_combobox = ttk.Combobox(window, values=[".csv", ".xlsx"])
outputFilesFormat_combobox.configure(width=25)
outputFilesFormat_combobox.grid(row=6, column=1, sticky='w', padx=15, pady=5)
#### marker for removing suspect data
remove_bad = BooleanVar(value=False)
remove_badButton = Checkbutton(window, text="Remove Bad Data", variable=remove_bad, bg="lightblue")
remove_badButton.grid(row=7, column=1, sticky='w', padx=15, pady=5)
#### marker for removing bad data
remove_suspect = BooleanVar(value=False)
remove_suspectButton = Checkbutton(window, text="Remove Suspect Data", variable=remove_suspect, bg="lightblue")
remove_suspectButton.grid(row=8, column=1, sticky='w', padx=15, pady=5)
####### column 3-->
#### site selection
#site selection label
siteSelect_label = Label(window, text="Site:", bg=window["bg"])
siteSelect_label.grid(row=0, column=3, sticky='w', padx=15, pady=5)
# list with site names for markers
site_names = ["A01", "A02", "A03", "A05", "A06", "B02", "B04", "B06", "BUR", "C01", "C02",
              "C03", "C04", "C05", "C06", "C07", "C08", "C09", "CAL", "CBD", "CFD", "CFR",
              "CFRIO1", "CBD",  "D01", "D02", "D03", "D04", "D05", "D06", "D07", "D08",
              "D09", "D10", "D11", "D12", "D13", "PAB1", "PAB4", "PAB5", "RH18", "RH30",
              "RH50", "VAC", "VAL"]
selectedSites = []
# dictionary to store boolean variables
siteMarkers = {}
for i, site in enumerate(site_names):
    var = BooleanVar(value=False)
    checkbutton = Checkbutton(window, text=site, variable=var, bg="lightblue")
    if i+1 <= 12:
        checkbutton.grid(row=i+1, column=2, sticky='w', padx=15, pady=5)
    elif 12 < i+1 <= 24 :
        checkbutton.grid(row=(i-12)+1, column=3, sticky='w', padx=15, pady=5)
    elif 24 < i+1 <= 36:
        checkbutton.grid(row=(i-24)+1, column=4, sticky='w', padx=15, pady=5)
    elif 36 < i+1:
        checkbutton.grid(row=(i-36)+1, column=5, sticky='w', padx=15, pady=5)
    siteMarkers[site] = var


#### button for saving settings
run_button = Button(window, text="Save input Settings", command=saveInputSettings)
run_button.configure(bg="lightgray")
run_button.grid(row=17, column=0, sticky='w', padx=15, pady=25)
#### Start the window
window.mainloop()

# ignore RuntimeWarning
warnings.filterwarnings("ignore", category=RuntimeWarning)
################################# Description ##################################
# Workflow for processing data which puts together the other scripts.
################################################################################

# input folder path
input_folder_path = INPUT['input_config_path']

if INPUT['input_type'] == 'Seaguard':
    e = 1
elif INPUT['input_type'] == 'HOBO':
    e = 2
################################################################################

os.chdir(input_folder_path)
#loading input
from config_file import tsQualityTests, tsSettings, auxTests # type: ignore

################ QUALITY CONTROL FOR CTD AND AUXILIAR SENSORS ##################


# change to folder containing raw data
os.chdir(INPUT['raw_data_path'])

# opening raw files according to selected data type
if e == 1:
    if INPUT['profile'] == True:
        raw_data = data.read_ctd_profile_csv(INPUT['file_name'])
    else:
        raw_data = data.read_ctd_csv(INPUT['file_name'])
    for name in raw_data.columns:
        if re.search('time', name, re.IGNORECASE):
            if re.search('timer', name, re.IGNORECASE):
                pass
            else:
                raw_data = raw_data.rename(columns={name:'Datetime'})
        if re.search('prof', name, re.IGNORECASE):
                raw_data = raw_data.rename(columns={name:'Depth(m)'})
elif e == 2:
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
ms_interval = np.timedelta64(raw_data['Datetime'].iloc[1] - raw_data['Datetime'].iloc[0], 's')
INPUT['start_time'] = start_time
INPUT['end_time'] = end_time

# adjusting for GMT-3 hours
if INPUT['correct_gmt3h'] == True:
    raw_data['Datetime'] = raw_data['Datetime'] - timedelta(hours=3)
    start_time = start_time - timedelta(hours=3)
    end_time = end_time - timedelta(hours=3)

# excluding other than main temperature sensors
t = 0
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
            raw_data = raw_data.rename(columns={name:'Pressure(dbar)'})

dep, press = (0,0)
for name in raw_data.columns:
    if re.search('depth', name, re.IGNORECASE) and not re.search('pressure', name, re.IGNORECASE):
        dep += 1
    elif re.search('pressure', name, re.IGNORECASE):
        press += 1
if dep == 0 and press == 1:
    raw_data = data.pressure_to_depth(raw_data, latitude=17.5, adjust_for_atm=True)


# add sample number column
raw_data['Sample Number'] = raw_data.index + 1

#removing data equal (except for PAR) and under 0
exceptions = ['Datetime', 'Sample Number', 'Pitch[Deg]', 'Roll[Deg]', 'Timer[s]', 'Site']
for name in raw_data.columns:
    if re.search('par', name, re.IGNORECASE):
        raw_data.loc[raw_data[name]<0, name] = np.nan
    else:
        if name not in exceptions:
            raw_data.loc[raw_data[name]<=0, name] = np.nan

#removing data where depth is under 0.5 for profile data
if INPUT['profile'] == True:
    for name in raw_data.columns:
        if name not in exceptions:
            raw_data.loc[raw_data['Depth(m)'] < 0.5, name] = np.nan

#removing data reproved in depth range test
if auxTests['depth range test'] == 'ON':
    for name in raw_data.columns:
        if re.search('depth', name, re.IGNORECASE):
            #first round
            raw_data = QC.depth_range_test (raw_data, tsSettings['depth_range'])
            #second round
            raw_data = QC.depth_range_test (raw_data, tsSettings['depth_range'])

#selecting samples based on descending or ascendig equipment
from scipy import signal # type: ignore
if INPUT['select_profile_data'] == True:
    for name in raw_data.columns:
        if re.search('pressure', name, re.IGNORECASE):
            try:
                peak = int(signal.find_peaks(raw_data[name], width=100)[0])
                fig1 = plt.figure()
                ax1 = fig1.gca()
                ax1.plot(raw_data[name], label='Pressure (dbar)')
                ax1.plot(peak, raw_data[name].loc[peak], '.', c='red', linestyle='none')
                ax1.set_ylabel('Pressure (dbar)')
                fig1.show()
                #plt.show(block=True)
                ans = []
                # Create window 1
                window = Tk()
                window.title("Peak Validation")
                window.geometry("225x80")
                window.resizable(True, True)
                window.configure(bg="lightblue")
                font_style = ("Arial", 12, "bold")
                # upper label
                dPeak_label = Label(window, text="       Do you accept data peak?", bg=window["bg"])
                dPeak_label.grid(row=0, column=0, sticky='w', padx=15, pady=5)
                # buttons for yeas and no
                yesButton = Button(window, text="Yes", command=acceptPeak)
                yesButton.configure(bg="lightgray")
                yesButton.grid(row=1, column=0, sticky='w', padx=5, pady=5)
                noButton = Button(window, text="No", command=doNotAcceptPeak)
                noButton.configure(bg="lightgray")
                noButton.grid(row=1, column=1, sticky='w', padx=0, pady=5)
                #### Start the window
                window.mainloop()

                if ans[0] == 'y':
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
                    ax2.set_xlabel('Temperature(degC)')
                    ax2.set_ylabel('Depth(m)')
                    ax2.legend()
                    ax2.invert_yaxis()
                    ax2.grid()

                    selected = None
                    def on_pick(event):
                        global selected
                        selected = event.artist.get_label()
                        plt.close(fig2)

                    line1.set_picker(True)
                    line2.set_picker(True)
                    fig2.canvas.mpl_connect('pick_event', on_pick)
                    fig2.canvas.mpl_connect('motion_notify_event', data.on_motion)
                    plt.show()
                    while selected is None:
                        plt.pause(0.1)

                    if selected == 'descending data':
                        raw_data = desc.copy()
                        
                    elif selected == 'ascending data':
                        raw_data = asc.copy()
                    plt.close(fig2)
                    raw_data.index =  np.arange(len(raw_data))
            except TypeError:
                print("Could not find turning point")
                pass

# number of lines and cells
n_cel = 1
n_samples = len(raw_data)

if INPUT['check_variables'] == True:
    check_variables = ['O2 Level(uM)', 'Temperature(degC)','Conductivity(mS/cm)', 'Salinity(PSU)', 'Density(kg/m3)',
                       'PAR(umol/m2/s)', 'Turbidity(FTU)', 'Chlorophyll(ug/L)', 'Hydrogen Potential(pH)', 'Dissolved Organic Matter(ppb)']
    for name in check_variables:
        if name in raw_data.columns:
            raw_data = data.trim_selected_variable(raw_data, name)
#create list for flag codes
flags = ['' for n in range(len(raw_data))]

start = time.time()
# Range tests
ti = time.time()
a = 0
for name in raw_data.columns:
    if re.search('temperature', name, re.IGNORECASE):
        a = 1
        flags = QC.range_test (raw_data[name], flags, range_min=tsSettings['sensor_min_temp'], range_max=tsSettings['sensor_max_temp']) if tsQualityTests['temperature sensor range'] == 'ON' else [flags[n]+'%d'%QC.QC_flags.DISMISSED for n in range(n_samples)]
if a == 0:
    flags = [flags[n]+'%d'%QC.QC_flags.UNKNOWN for n in range(n_samples)]
tf = time.time()
N = data.count_test_bdata(flags)
print('Temperature sensor range test: %f s\nReproved: %i (%f%%)\n' %((tf - ti), N, (N/n_samples)*100))

ti = time.time()
a = 0
for name in raw_data.columns:
    if re.search('salinity', name, re.IGNORECASE):
        a = 1
        flags = QC.range_test (raw_data[name], flags, range_min=tsSettings['sensor_min_sal'], range_max=tsSettings['sensor_max_sal']) if tsQualityTests['salinity sensor range'] == 'ON' else [flags[n]+'%d'%QC.QC_flags.DISMISSED for n in range(n_samples)]
if a == 0:
    flags = [flags[n]+'%d'%QC.QC_flags.UNKNOWN for n in range(n_samples)]
tf = time.time()
N = data.count_test_bdata(flags)
print('Salinity sensor range test: %f s\nReproved: %i (%f%%)\n' %((tf - ti), N, (N/n_samples)*100))

ti = time.time()
a = 0
for name in raw_data.columns:
    if re.search('conductivity', name, re.IGNORECASE):
        a = 1
        flags = QC.range_test (raw_data[name], flags, range_min=tsSettings['sensor_min_cond'], range_max=tsSettings['sensor_max_cond']) if tsQualityTests['conductivity sensor range'] == 'ON' else [flags[n]+'%d'%QC.QC_flags.DISMISSED for n in range(n_samples)]
if a == 0:
    flags = [flags[n]+'%d'%QC.QC_flags.UNKNOWN for n in range(n_samples)]
tf = time.time()
N = data.count_test_bdata(flags)
print('Conductivity sensor range test: %f s\nReproved: %i (%f%%)\n' %((tf - ti), N, (N/n_samples)*100))

ti = time.time()
a = 0
for name in raw_data.columns:
    if re.search('pressure', name, re.IGNORECASE):
        a = 1
        flags = QC.range_test (raw_data[name], flags, range_min=tsSettings['sensor_min_pres'], range_max=tsSettings['sensor_max_pres']) if tsQualityTests['pressure sensor range'] == 'ON' else [flags[n]+'%d'%QC.QC_flags.DISMISSED for n in range(n_samples)]
if a == 0:
    flags = [flags[n]+'%d'%QC.QC_flags.UNKNOWN for n in range(n_samples)]
tf = time.time()
N = data.count_test_bdata(flags)
print('Pressure sensor range test: %f s\nReproved: %i (%f%%)\n' %((tf - ti), N, (N/n_samples)*100))

##Environmental range tests
ti = time.time()
a = 0
for name in raw_data.columns:
    if re.search('temperature', name, re.IGNORECASE):
        a = 1
        flags = QC.range_test (raw_data[name], flags, range_min=tsSettings['env_min_temp'], range_max=tsSettings['env_max_temp']) if tsQualityTests['temperature environmental range'] == 'ON' else [flags[n]+'%d'%QC.QC_flags.DISMISSED for n in range(n_samples)]
if a == 0:
    flags = [flags[n]+'%d'%QC.QC_flags.UNKNOWN for n in range(n_samples)]
tf = time.time()
N = data.count_test_bdata(flags)
print('Temperature environmental range test: %f s\nReproved: %i (%f%%)\n' %((tf - ti), N, (N/n_samples)*100))

ti = time.time()
a = 0
for name in raw_data.columns:
    if re.search('salinity', name, re.IGNORECASE):
        a = 1
        flags = QC.range_test (raw_data[name], flags, range_min=tsSettings['env_min_sal'], range_max=tsSettings['env_max_sal']) if tsQualityTests['salinity environmental range'] == 'ON' else [flags[n]+'%d'%QC.QC_flags.DISMISSED for n in range(n_samples)]
if a == 0:
    flags = [flags[n]+'%d'%QC.QC_flags.UNKNOWN for n in range(n_samples)]
tf = time.time()
N = data.count_test_bdata(flags)
print('Salinity environmental range test: %f s\nReproved: %i (%f%%)\n' %((tf - ti), N, (N/n_samples)*100))

ti = time.time()
a = 0
for name in raw_data.columns:
    if re.search('conductivity', name, re.IGNORECASE):
        a = 1
        flags = QC.range_test (raw_data[name], flags, range_min=tsSettings['env_min_cond'], range_max=tsSettings['env_max_cond']) if tsQualityTests['conductivity environmental range'] == 'ON' else [flags[n]+'%d'%QC.QC_flags.DISMISSED for n in range(n_samples)]
if a == 0:
    flags = [flags[n]+'%d'%QC.QC_flags.UNKNOWN for n in range(n_samples)]
tf = time.time()
N = data.count_test_bdata(flags)
print('Conductivity environmental range test: %f s\nReproved: %i (%f%%)\n' %((tf - ti), N, (N/n_samples)*100))

ti = time.time()
a = 0
for name in raw_data.columns:
    if re.search('pressure', name, re.IGNORECASE):
        a = 1
        flags = QC.range_test (raw_data[name], flags, range_min=tsSettings['env_min_pres'], range_max=tsSettings['env_max_pres']) if tsQualityTests['pressure environmental range'] == 'ON' else [flags[n]+'%d'%QC.QC_flags.DISMISSED for n in range(n_samples)]
if a == 0:
    flags = [flags[n]+'%d'%QC.QC_flags.UNKNOWN for n in range(n_samples)]
tf = time.time()
N = data.count_test_bdata(flags)
print('Pressure environmental range test: %f s\nReproved: %i (%f%%)\n' %((tf - ti), N, (N/n_samples)*100))

ti = time.time()
a = 0
for name in raw_data.columns:
    if re.search('hydrogen potential\(pH\)', name, re.IGNORECASE):
        a = 1
        flags = QC.range_test (raw_data[name], flags, range_min=tsSettings['env_min_pH'], range_max=tsSettings['env_max_pH']) if tsQualityTests['pH environmental range'] == 'ON' else [flags[n]+'%d'%QC.QC_flags.DISMISSED for n in range(n_samples)]
if a == 0:
    flags = [flags[n]+'%d'%QC.QC_flags.UNKNOWN for n in range(n_samples)]
tf = time.time()
N = data.count_test_bdata(flags)
print('pH environmental range test: %f s\nReproved: %i (%f%%)\n' %((tf - ti), N, (N/n_samples)*100))

ti = time.time()
a = 0
for name in raw_data.columns:
    if re.search('chlorophyll\(ug/L\)', name, re.IGNORECASE):
        a = 1
        flags = QC.range_test (raw_data[name], flags, range_min=tsSettings['env_min_chl'], range_max=tsSettings['env_max_chl']) if tsQualityTests['chlorophyll environmental range'] == 'ON' else [flags[n]+'%d'%QC.QC_flags.DISMISSED for n in range(n_samples)]
if a == 0:
    flags = [flags[n]+'%d'%QC.QC_flags.UNKNOWN for n in range(n_samples)]
tf = time.time()
N = data.count_test_bdata(flags)
print('Chlorophyll environmental range test: %f s\nReproved: %i (%f%%)\n' %((tf - ti), N, (N/n_samples)*100))

ti = time.time()
a = 0
for name in raw_data.columns:
    if re.search('o2 level', name, re.IGNORECASE):
        a = 1
        flags = QC.range_test (raw_data[name], flags, range_min=tsSettings['env_min_O2'], range_max=tsSettings['env_max_O2']) if tsQualityTests['dissolved oxygen environmental range'] == 'ON' else [flags[n]+'%d'%QC.QC_flags.DISMISSED for n in range(n_samples)]
if a == 0:
    flags = [flags[n]+'%d'%QC.QC_flags.UNKNOWN for n in range(n_samples)]
tf = time.time()
N = data.count_test_bdata(flags)
print('Dissolved oxygen (O2) environmental range test: %f s\nReproved: %i (%f%%)\n' %((tf - ti), N, (N/n_samples)*100))

ti = time.time()
a = 0
for name in raw_data.columns:
    if re.search('organic matter', name, re.IGNORECASE):
        a = 1
        flags = QC.range_test (raw_data[name], flags, range_min=tsSettings['env_min_org'], range_max=tsSettings['env_max_org']) if tsQualityTests['dissolved organic matter environmental range'] == 'ON' else [flags[n]+'%d'%QC.QC_flags.DISMISSED for n in range(n_samples)]
if a == 0:
    flags = [flags[n]+'%d'%QC.QC_flags.UNKNOWN for n in range(n_samples)]
tf = time.time()
N = data.count_test_bdata(flags)
print('Dissolved organic matter environmental range test: %f s\nReproved: %i (%f%%)\n' %((tf - ti), N, (N/n_samples)*100))

ti = time.time()
a = 0
for name in raw_data.columns:
    if re.search('turbidity\(ftu\)', name, re.IGNORECASE):
        print(name)
        a = 1
        flags = QC.range_test (raw_data[name], flags, range_min=tsSettings['env_min_tur'], range_max=tsSettings['env_max_tur']) if tsQualityTests['turbidity environmental range'] == 'ON' else [flags[n]+'%d'%QC.QC_flags.DISMISSED for n in range(n_samples)]
if a == 0:
    flags = [flags[n]+'%d'%QC.QC_flags.UNKNOWN for n in range(n_samples)]
tf = time.time()
N = data.count_test_bdata(flags)
print('Turbidity environmental range test: %f s\nReproved: %i (%f%%)\n' %((tf - ti), N, (N/n_samples)*100))

##testes de spikes (valores espurios)
ti = time.time()
a = 0
for name in raw_data.columns:
    if re.search('temperature', name, re.IGNORECASE):
        a = 1
        flags = QC.z_score_spike_test(raw_data, name, n_cel, flags, tsSettings['time_window'], ms_interval, tsSettings['fail_factor'], tsSettings['susp_factor']) if tsQualityTests['temperature spikes'] == 'ON' else [flags[n]+'%d'%QC.QC_flags.DISMISSED for n in range(n_samples)]
if a == 0:
    flags = [flags[n]+'%d'%QC.QC_flags.UNKNOWN for n in range(n_samples)]
tf = time.time()
N = data.count_test_bdata(flags)
print('Temperature spikes test: %f s\nReproved: %i (%f%%)\n' %((tf - ti), N, (N/n_samples)*100))

ti = time.time()
a = 0
for name in raw_data.columns:
    if re.search('salinity', name, re.IGNORECASE):
        a = 1
        flags = QC.z_score_spike_test(raw_data, name, n_cel, flags, tsSettings['time_window'], ms_interval, tsSettings['fail_factor'], tsSettings['susp_factor']) if tsQualityTests['salinity spikes'] == 'ON' else [flags[n]+'%d'%QC.QC_flags.DISMISSED for n in range(n_samples)]
if a == 0:
    flags = [flags[n]+'%d'%QC.QC_flags.UNKNOWN for n in range(n_samples)]
tf = time.time()
N = data.count_test_bdata(flags)
print('Salinity spikes test: %f s\nReproved: %i (%f%%)\n' %((tf - ti), N, (N/n_samples)*100))

ti = time.time()
a = 0
for name in raw_data.columns:
    if re.search('conductivity', name, re.IGNORECASE):
        a = 1
        flags = QC.z_score_spike_test(raw_data, name, n_cel, flags, tsSettings['time_window'], ms_interval, tsSettings['fail_factor'], tsSettings['susp_factor']) if tsQualityTests['conductivity spikes'] == 'ON' else [flags[n]+'%d'%QC.QC_flags.DISMISSED for n in range(n_samples)]
if a == 0:
    flags = [flags[n]+'%d'%QC.QC_flags.UNKNOWN for n in range(n_samples)]
tf = time.time()
N = data.count_test_bdata(flags)
print('Conductivity spikes test: %f s\nReproved: %i (%f%%)\n' %((tf - ti), N, (N/n_samples)*100))

ti = time.time()
a = 0
for name in raw_data.columns:
    if re.search('pressure', name, re.IGNORECASE):
        a = 1
        flags = QC.z_score_spike_test(raw_data, name, n_cel, flags, tsSettings['time_window'], ms_interval, tsSettings['fail_factor'], tsSettings['susp_factor']) if tsQualityTests['pressure spikes'] == 'ON' else [flags[n]+'%d'%QC.QC_flags.DISMISSED for n in range(n_samples)]
if a == 0:
    flags = [flags[n]+'%d'%QC.QC_flags.UNKNOWN for n in range(n_samples)]
tf = time.time()
N = data.count_test_bdata(flags)
print('Pressure spikes test: %f s\nReproved: %i (%f%%)\n' %((tf - ti), N, (N/n_samples)*100))

ti = time.time()
a = 0
for name in raw_data.columns:
    if re.search('hydrogen potential\(pH\)', name, re.IGNORECASE):
        a = 1
        flags = QC.z_score_spike_test(raw_data, name, n_cel, flags, tsSettings['time_window'], ms_interval, tsSettings['fail_factor'], tsSettings['susp_factor']) if tsQualityTests['pH spikes'] == 'ON' else [flags[n]+'%d'%QC.QC_flags.DISMISSED for n in range(n_samples)]
if a == 0:
    flags = [flags[n]+'%d'%QC.QC_flags.UNKNOWN for n in range(n_samples)]
tf = time.time()
N = data.count_test_bdata(flags)
print('pH spikes test: %f s\nReproved: %i (%f%%)\n' %((tf - ti), N, (N/n_samples)*100))

ti = time.time()
a = 0
for name in raw_data.columns:
    if re.search('chlorophyll\(ug/L\)', name, re.IGNORECASE):
        a = 1
        flags = QC.z_score_spike_test(raw_data, name, n_cel, flags, tsSettings['time_window'], ms_interval, tsSettings['fail_factor'], tsSettings['susp_factor']) if tsQualityTests['chlorophyll spikes'] == 'ON' else [flags[n]+'%d'%QC.QC_flags.DISMISSED for n in range(n_samples)]
if a == 0:
    flags = [flags[n]+'%d'%QC.QC_flags.UNKNOWN for n in range(n_samples)]
tf = time.time()
N = data.count_test_bdata(flags)
print('Chlorophyll spikes test: %f s\nReproved: %i (%f%%)\n' %((tf - ti), N, (N/n_samples)*100))

ti = time.time()
a = 0
for name in raw_data.columns:
    if re.search('O2', name, re.IGNORECASE):
        a = 1
        flags = QC.z_score_spike_test(raw_data, name, n_cel, flags, tsSettings['time_window'], ms_interval, tsSettings['fail_factor'], tsSettings['susp_factor']) if tsQualityTests['dissolved oxygen spikes'] == 'ON' else [flags[n]+'%d'%QC.QC_flags.DISMISSED for n in range(n_samples)]
if a == 0:
    flags = [flags[n]+'%d'%QC.QC_flags.UNKNOWN for n in range(n_samples)]
tf = time.time()
N = data.count_test_bdata(flags)
print('Dissolved oxygen spikes test: %f s\nReproved: %i (%f%%)\n' %((tf - ti), N, (N/n_samples)*100))

ti = time.time()
a = 0
for name in raw_data.columns:
    if re.search('organic matter', name, re.IGNORECASE):
        a = 1
        flags = QC.z_score_spike_test(raw_data, name, n_cel, flags, tsSettings['time_window'], ms_interval, tsSettings['fail_factor'], tsSettings['susp_factor']) if tsQualityTests['dissolved organic matter spikes'] == 'ON' else [flags[n]+'%d'%QC.QC_flags.DISMISSED for n in range(n_samples)]
if a == 0:
    flags = [flags[n]+'%d'%QC.QC_flags.UNKNOWN for n in range(n_samples)]
tf = time.time()
N = data.count_test_bdata(flags)
print('Dissolved organic matter spikes test: %f s\nReproved: %i (%f%%)\n' %((tf - ti), N, (N/n_samples)*100))

ti = time.time()
a = 0
for name in raw_data.columns:
    if re.search('turbidity\(ftu\)', name, re.IGNORECASE):
        a = 1
        flags = QC.z_score_spike_test(raw_data, name, n_cel, flags, tsSettings['time_window'], ms_interval, tsSettings['fail_factor'], tsSettings['susp_factor']) if tsQualityTests['turbidity spikes'] == 'ON' else [flags[n]+'%d'%QC.QC_flags.DISMISSED for n in range(n_samples)]
if a == 0:
    flags = [flags[n]+'%d'%QC.QC_flags.UNKNOWN for n in range(n_samples)]
tf = time.time()
N = data.count_test_bdata(flags)
print('Turbidity spikes test: %f s\nReproved: %i (%f%%)\n' %((tf - ti), N, (N/n_samples)*100))

##teste de taxa de variacao
ti = time.time()
a = 0
for name in raw_data.columns:
    if re.search('temperature', name, re.IGNORECASE):
        a = 1
        flags = QC.sigma_rate_of_change_test (n_samples, raw_data[name], n_cel, flags, ms_interval=ms_interval, time_window=tsSettings['time_window'], rc_fail=tsSettings['fail_factor'], rc_susp=tsSettings['susp_factor'], DIR=False) if tsQualityTests['temperature rate of change'] == 'ON' else [flags[n]+'%d'%QC.QC_flags.DISMISSED for n in range(n_samples)]
if a == 0:
    flags = [flags[n]+'%d'%QC.QC_flags.UNKNOWN for n in range(n_samples)]
tf = time.time()
N = data.count_test_bdata(flags)
print('Temperature rate of change test: %f s\nReproved: %i (%f%%)\n' %((tf - ti), N, (N/n_samples)*100))

ti = time.time()
a = 0
for name in raw_data.columns:
    if re.search('salinity', name, re.IGNORECASE):
        a = 1
        flags = QC.sigma_rate_of_change_test (n_samples, raw_data[name], n_cel, flags, ms_interval=ms_interval, time_window=tsSettings['time_window'], rc_fail=tsSettings['fail_factor'], rc_susp=tsSettings['susp_factor'], DIR=False) if tsQualityTests['salinity rate of change'] == 'ON' else [flags[n]+'%d'%QC.QC_flags.DISMISSED for n in range(n_samples)]
if a == 0:
    flags = [flags[n]+'%d'%QC.QC_flags.UNKNOWN for n in range(n_samples)]
tf = time.time()
N = data.count_test_bdata(flags)
print('Salinity rate of change test: %f s\nReproved: %i (%f%%)\n' %((tf - ti), N, (N/n_samples)*100))

ti = time.time()
a = 0
for name in raw_data.columns:
    if re.search('conductivity', name, re.IGNORECASE):
        a = 1
        flags = QC.sigma_rate_of_change_test (n_samples, raw_data[name], n_cel, flags, ms_interval=ms_interval, time_window=tsSettings['time_window'], rc_fail=tsSettings['fail_factor'], rc_susp=tsSettings['susp_factor'], DIR=False) if tsQualityTests['conductivity rate of change'] == 'ON' else [flags[n]+'%d'%QC.QC_flags.DISMISSED for n in range(n_samples)]
if a == 0:
    flags = [flags[n]+'%d'%QC.QC_flags.UNKNOWN for n in range(n_samples)]
tf = time.time()
N = data.count_test_bdata(flags)
print('Conductivity rate of change test: %f s\nReproved: %i (%f%%)\n' %((tf - ti), N, (N/n_samples)*100))

ti = time.time()
a = 0
for name in raw_data.columns:
    if re.search('pressure', name, re.IGNORECASE):
        a = 1
        flags = QC.sigma_rate_of_change_test (n_samples, raw_data[name], n_cel, flags, ms_interval=ms_interval, time_window=tsSettings['time_window'], rc_fail=tsSettings['fail_factor'], rc_susp=tsSettings['susp_factor'], DIR=False) if tsQualityTests['pressure rate of change'] == 'ON' else [flags[n]+'%d'%QC.QC_flags.DISMISSED for n in range(n_samples)]
if a == 0:
    flags = [flags[n]+'%d'%QC.QC_flags.UNKNOWN for n in range(n_samples)]
tf = time.time()
N = data.count_test_bdata(flags)
print('Pressure rate of change test: %f s\nReproved: %i (%f%%)\n' %((tf - ti), N, (N/n_samples)*100))

##testes de travemento do sensor/ sucessivos iguais
ti = time.time()
a = 0
for name in raw_data.columns:
    if re.search('temperature', name, re.IGNORECASE):
        a = 1
        flags = QC.single_flat_line_test (n_samples, n_cel, raw_data[name], flags, rep_cnt_fail=tsSettings['rep_cnt_fail'], rep_cnt_suspect=tsSettings['rep_cnt_susp'], eps=tsSettings['eps']) if tsQualityTests['temperature flat line'] == 'ON' else [flags[n]+'%d'%QC.QC_flags.DISMISSED for n in range(n_samples)]
if a == 0:
    flags = [flags[n]+'%d'%QC.QC_flags.UNKNOWN for n in range(n_samples)]
tf = time.time()
N = data.count_test_bdata(flags)
print('Temperature flat line test: %f s\nReproved: %i (%f%%)\n' %((tf - ti), N, (N/n_samples)*100))

ti = time.time()
a = 0
for name in raw_data.columns:
    if re.search('salinity', name, re.IGNORECASE):
        a = 1
        flags = QC.single_flat_line_test (n_samples, n_cel, raw_data[name], flags, rep_cnt_fail=tsSettings['rep_cnt_fail'], rep_cnt_suspect=tsSettings['rep_cnt_susp'], eps=tsSettings['eps']) if tsQualityTests['salinity flat line'] == 'ON' else [flags[n]+'%d'%QC.QC_flags.DISMISSED for n in range(n_samples)]
if a == 0:
    flags = [flags[n]+'%d'%QC.QC_flags.UNKNOWN for n in range(n_samples)]
tf = time.time()
N = data.count_test_bdata(flags)
print('Salinity flat line test: %f s\nReproved: %i (%f%%)\n' %((tf - ti), N, (N/n_samples)*100))

ti = time.time()
a = 0
for name in raw_data.columns:
    if re.search('conductivity', name, re.IGNORECASE):
        a = 1
        flags = QC.single_flat_line_test (n_samples, n_cel, raw_data[name], flags, rep_cnt_fail=tsSettings['rep_cnt_fail'], rep_cnt_suspect=tsSettings['rep_cnt_susp'], eps=tsSettings['eps']) if tsQualityTests['conductivity flat line'] == 'ON' else [flags[n]+'%d'%QC.QC_flags.DISMISSED for n in range(n_samples)]
if a == 0:
    flags = [flags[n]+'%d'%QC.QC_flags.UNKNOWN for n in range(n_samples)]
tf = time.time()
N = data.count_test_bdata(flags)
print('Conductivity flat line test: %f s\nReproved: %i (%f%%)\n' %((tf - ti), N, (N/n_samples)*100))

ti = time.time()
a = 0
for name in raw_data.columns:
    if re.search('pressure', name, re.IGNORECASE):
        a = 1
        flags = QC.single_flat_line_test (n_samples, n_cel, raw_data[name], flags, rep_cnt_fail=tsSettings['rep_cnt_fail'], rep_cnt_suspect=tsSettings['rep_cnt_susp'], eps=tsSettings['eps']) if tsQualityTests['pressure flat line'] == 'ON' else [flags[n]+'%d'%QC.QC_flags.DISMISSED for n in range(n_samples)]
if a == 0:
    flags = [flags[n]+'%d'%QC.QC_flags.UNKNOWN for n in range(n_samples)]
tf = time.time()
N = data.count_test_bdata(flags)
print('Pressure flat line test: %f s\nReproved: %i (%f%%)\n' %((tf - ti), N, (N/n_samples)*100))

##Testes de gradiente vertical
if INPUT['profile'] == True:
    ti = time.time()
    a = 0
    for name in raw_data.columns:
        if re.search('temperature', name, re.IGNORECASE):
            a = 1
            flags = QC.vertical_gradient_test(n_samples, raw_data[name], n_cel, flags, ms_interval=ms_interval, time_window=tsSettings['time_window'], rc_fail=tsSettings['fail_factor'], rc_susp=tsSettings['susp_factor'], DIR=False) if tsQualityTests['temperature vertical gradient'] == 'ON' else [flags[n]+'%d'%QC.QC_flags.DISMISSED for n in range(n_samples)]
    if a == 0:
        flags = [flags[n]+'%d'%QC.QC_flags.UNKNOWN for n in range(n_samples)]
    tf = time.time()
    N = data.count_test_bdata(flags)
    print('Temperature vertical gradient test: %f s\nReproved: %i (%f%%)\n' %((tf - ti), N, (N/n_samples)*100))

    ti = time.time()
    a = 0
    for name in raw_data.columns:
        if re.search('salinity', name, re.IGNORECASE):
            a = 1
            flags = QC.vertical_gradient_test(n_samples, raw_data[name], n_cel, flags, ms_interval=ms_interval, time_window=tsSettings['time_window'], rc_fail=tsSettings['fail_factor'], rc_susp=tsSettings['susp_factor'], DIR=False) if tsQualityTests['salinity vertical gradient'] == 'ON' else [flags[n]+'%d'%QC.QC_flags.DISMISSED for n in range(n_samples)]
    if a == 0:
        flags = [flags[n]+'%d'%QC.QC_flags.UNKNOWN for n in range(n_samples)]
    tf = time.time()
    N = data.count_test_bdata(flags)
    print('Salinity vertical gradient test: %f s\nReproved: %i (%f%%)\n' %((tf - ti), N, (N/n_samples)*100))

    ti = time.time()
    a = 0
    for name in raw_data.columns:
        if re.search('conductivity', name, re.IGNORECASE):
            a = 1
            flags = QC.vertical_gradient_test(n_samples, raw_data[name], n_cel, flags, ms_interval=ms_interval, time_window=tsSettings['time_window'], rc_fail=tsSettings['fail_factor'], rc_susp=tsSettings['susp_factor'], DIR=False) if tsQualityTests['conductivity vertical gradient'] == 'ON' else [flags[n]+'%d'%QC.QC_flags.DISMISSED for n in range(n_samples)]
    if a == 0:
        flags = [flags[n]+'%d'%QC.QC_flags.UNKNOWN for n in range(n_samples)]
    tf = time.time()
    N = data.count_test_bdata(flags)
    print('Conductivity vertical gradient test: %f s\nReproved: %i (%f%%)\n' %((tf - ti), N, (N/n_samples)*100))

end = time.time()
print('\nProcessing time: %f s\n' %(end - start))

print('\nCreating output table\n')
qualified_data, raw_data, T_bdata, S_bdata, C_bdata, P_bdata, pH_bdata, chl_bdata, O2_bdata, org_bdata, tur_bdata, T_sdata, S_sdata, C_sdata, P_sdata, pH_sdata, chl_sdata, O2_sdata, org_sdata, tur_sdata, T_mdata, S_mdata, C_mdata, P_mdata, pH_mdata, chl_mdata, O2_mdata, org_mdata, tur_mdata = data.handle_output_file (raw_data, flags, remove_suspect=OUTPUT['remove_suspect'], remove_bad=OUTPUT['remove_bad'], Profile=INPUT['profile'])

# add luminosity data to dataframe if input is hobo
if e == 4:
    qualified_data['Luminosity(lux)'] = lumiFrame['Luminosity(lux)']

qualified_data = data.order_var (qualified_data, n_cel, data_type='tscp')
# Fill column with site information
qualified_data['Site'] = INPUT['site']
# Fill column with site information
qualified_data['QCS Version'] = 'v1.0'
# Export qualified data to .csv/.xlsx file
os.chdir(OUTPUT['output_file_path'])
root_path = OUTPUT['output_file_path'] + '/' + re.search('^[^\.]+',INPUT['file_name']).group()
os.makedirs(root_path, exist_ok=True)
path = root_path + '/QCS qualified tscp data/'
os.makedirs(path, exist_ok=True)
dataview_path =  root_path + '/QCS DataView (fixed scale)/'
dataview_path2 = root_path + '/QCS DataView (unfixed scale)/'
if e != 4:
    os.makedirs(dataview_path, exist_ok=True)
    os.makedirs(dataview_path2, exist_ok=True)

if re.search('xlsx', OUTPUT['output_data_format'], re.IGNORECASE):
    qualified_data.to_excel(os.path.join(path, re.search('^[^\.]+',INPUT['file_name']).group())+'_QLF.xlsx', index=False) ##cria excel
if re.search('csv', OUTPUT['output_data_format'], re.IGNORECASE):
    qualified_data.to_csv(os.path.join(path, re.search('^[^\.]+',INPUT['file_name']).group())+'_QLF.xlsx', index=False) ##cria csv
print('\nExported data to: %s\n' %path)

print('\nExporting statistics table to: %s\n' %path)
stat_table = data.tscp_stats_table (qualified_data)
stat_table.to_csv(path + '/QCS_tscp_stat.csv', index=False)
print('\nExporting report to: %s\n' %path)
QCS_report = pd.DataFrame({'start': start_time,
                           'end': end_time,
                           'Total': len(qualified_data),
                           'Valid': len(qualified_data) - (len(T_bdata) + len(S_bdata) + len(C_bdata) + len(P_bdata)),
                           'T_bdata': len(T_bdata),
                           'S_bdata': len(S_bdata),
                           'C_bdata': len(C_bdata),
                           'P_bdata': len(P_bdata)}, index=[0])
QCS_report.to_csv(path + '/QCS_report.csv')

if e != 4:
    if INPUT['profile'] == True:
        exceptions = ['Datetime', 'Expedition', 'Pressure(dbar)',
                      'Site', 'Longitude', 'Latitude', 'Depth(m)',
                      'Battery Voltage(V)', 'flag', 'Sample Number', 'QCS Version']
        for variable in qualified_data.keys():
            if variable not in exceptions:
                view.plot_variable_profile(qualified_data, raw_data, variable, dataview_path, tsSettings, fixed_scale=True)
    else:
        for variable in qualified_data.keys():
            exceptions = ['Datetime', 'Expedition',
                          'Site', 'Longitude', 'Latitude',
                          'Battery Voltage(V)', 'flag', 'Sample Number', 'QCS Version']
            if variable not in exceptions:
                view.plot_variable(qualified_data, raw_data, variable, dataview_path, tsSettings, fixed_scale=True)

    if INPUT['profile'] == True:
        exceptions = ['Datetime', 'Expedition', 'Pressure(dbar)',
                      'Site', 'Longitude', 'Latitude', 'Depth(m)',
                      'Battery Voltage(V)', 'flag', 'Sample Number', 'QCS Version']
        for variable in qualified_data.keys():
            if variable not in exceptions:
                view.plot_variable_profile(qualified_data, raw_data, variable, dataview_path2, tsSettings, fixed_scale=False)
    else:
        for variable in qualified_data.keys():
            exceptions = ['Datetime', 'Expedition',
                          'Site', 'Longitude', 'Latitude',
                          'Battery Voltage(V)', 'flag', 'Sample Number', 'QCS Version']
            if variable not in exceptions:
                view.plot_variable(qualified_data, raw_data, variable, dataview_path2, tsSettings, fixed_scale=False)
elif e == 4:
    view.plot_hobo_split_site (database, dataview_path2)
plt.show()
os.chdir(rootPath)

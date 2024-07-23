import os
import re
import pandas as pd
import QCS_DataHandler as data
import matplotlib.pyplot as plt
import QCS_DataView as view
from tkinter import *
import tkinter as tk
from tkinter import ttk
from tkinter import filedialog
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

def selectInputFolder ():
    # Open a file dialog to select the output folder
    folderPath = filedialog.askdirectory(initialdir="/", title="Select input folder")
    # Clear the entry widget for the output path
    inputPath_entry.delete(0, END)
    # Insert the selected folder path into the entry widget
    inputPath_entry.insert(0, folderPath)

def saveInputSettings():
    # reset inputSettings dictionary
    #inputSettings = {}
    # Save the settings into the inputSettings dictionary
    inputSettings['databaseFileName'] = fileNames_entry.get()
    inputSettings['joinFiles'] = join.get()
    inputSettings['outputFileName'] = outputName_entry.get()
    inputSettings['outputPath'] = outputPath_entry.get()
    inputSettings['inputPath'] = inputPath_entry.get()
    inputSettings['sortByTime'] = sort.get()
    inputSettings['inputFilesFormat'] = inputFilesFormat_combobox.get()
    # Close the window
    window.destroy()

def saveDataViewSettings():
    # reset dataViewSettings dictionary
    #dataViewSettings = {}
    # Save the settings into the dataViewSettings dictionary
    dataViewSettings['dataType'] = dType_combobox.get()
    dataViewSettings['filterByYear'] = int(year_entry.get())
    dataViewSettings['panel1'] = panel1.get()
    dataViewSettings['panel2'] = panel2.get()
    dataViewSettings['panel3'] = panel3.get()
    dataViewSettings['tendencyLines'] = tendency.get()
    dataViewSettings['linearRegressionDegree'] = int(tendency_entry.get())
    dataViewSettings['viewDataPoints'] = dataPoints.get()
    dataViewSettings['stackDates'] = dateStack.get()
    dataViewSettings['elapsedTime'] = False
    # get site list from markers
    selectedSites = []
    for site in siteMarkers.keys():
        if siteMarkers[site].get() == True:
            if site in selectedSites:
                pass
            else:
                selectedSites.append(site)
    # get parameter list from markers
    selectedParameters = []
    for param in parameterMarkers.keys():
        if parameterMarkers[param].get() == True:
            if param in selectedParameters:
                pass
            else:
                selectedParameters.append(param)
    dataViewSettings['siteList'] = selectedSites
    dataViewSettings['parameterList'] = selectedParameters

def generatePanels():
    if dataViewSettings['dataType'] == 'mooring':
        if dataViewSettings['panel1'] == True:
            view.plot_database_panel1 (database, dataViewSettings['siteList'], dataViewSettings['parameterList'], dataViewSettings['filterByYear'], dataViewSettings['tendencyLines'], dataViewSettings['linearRegressionDegree'], dataViewSettings['viewDataPoints'])
        elif dataViewSettings['panel2'] == True:
            view.plot_database_panel2 (database, dataViewSettings['siteList'], dataViewSettings['parameterList'], dataViewSettings['filterByYear'], dataViewSettings['tendencyLines'], dataViewSettings['linearRegressionDegree'], dataViewSettings['viewDataPoints'], dataViewSettings['elapsedTime'], dataViewSettings['stackDates'])
        elif dataViewSettings['panel3'] == True:
            print('WARNING: Panel 3 is not suited for mooring data')
    elif dataViewSettings['dataType'] == 'tscp profile':
        if dataViewSettings['panel3'] == True:
            view.plot_database_panel3 (database, dataViewSettings['siteList'], dataViewSettings['parameterList'], dataViewSettings['filterByYear'], dataViewSettings['tendencyLines'], dataViewSettings['linearRegressionDegree'], dataViewSettings['viewDataPoints'])
        elif dataViewSettings['panel1'] == True or dataViewSettings['panel2'] == True:
            print('WARNING: Panels 1/2 are not suited for mooring data')
################################################################################
# create input settings dictionary
inputSettings = {}
############################## interactive tools ###############################
# Create window 1
window = Tk()
window.title("Input Settings")
window.geometry("500x300")
window.resizable(True, True)
window.configure(bg="lightblue")
font_style = ("Arial", 12, "bold")
################################################################################
############# Create the components of the window
####### column 1
#### fileDialog
# fileDialog upper label
fileNames_label = Label(window, text="Select Database File:", bg=window["bg"])
fileNames_label.grid(row=0, column=0, sticky='w', padx=15, pady=5)
# fileDialog entry space
fileNames_entry = Entry(window, width=25)
fileNames_entry.grid(row=1, column=0, sticky='w', padx=15, pady=5)
# fileDialog button
search_button = Button(window, text="Search Database File", command=selectFiles)
search_button.configure(bg="lightgray")
search_button.grid(row=2, column=0, sticky='w', padx=15, pady=5)
#### marker to join
join = BooleanVar(value=False)
joinFilesButton = Checkbutton(window, text="Join Data Files into Database", variable=join, bg="lightblue")
joinFilesButton.grid(row=3, column=0, sticky='w', padx=15, pady=5)
#### marker to sort by time
sort = BooleanVar(value=False)
sortButton = Checkbutton(window, text="Sort Database by Time", variable=sort, bg="lightblue")
sortButton.grid(row=4, column=0, sticky='w', padx=15, pady=5)
#### dataType drop-down list
inputFilesFormat_label = Label(window, text="Input Files Extension:", bg=window["bg"])
inputFilesFormat_label.grid(row=5, column=0, sticky='w', padx=15, pady=5)

inputFilesFormat_combobox = ttk.Combobox(window, values=["csv", "xlsx"])
inputFilesFormat_combobox.configure(width=25)
inputFilesFormat_combobox.grid(row=6, column=0, sticky='w', padx=15, pady=5)
####### column 2
#### Output naming
# Output naming upper label
output_label = Label(window, text="Output Database Name:", bg=window["bg"])
output_label.grid(row=0, column=1, sticky='w', padx=15, pady=5)
# Output naming entry space
outputName_entry = Entry(window, width=40)
outputName_entry.grid(row=1, column=1, sticky='w', padx=15, pady=5)
#### Input folderDialog
# Input folderDialog label
inputPath_label = Label(window, text="Input Path:", bg=window["bg"])
inputPath_label.grid(row=2, column=1, sticky='w', padx=15, pady=5)
# Input folderDialog entry space
inputPath_entry = Entry(window, width=40)
inputPath_entry.grid(row=3, column=1, sticky='w', padx=15, pady=5)
# Input folderDialog button
inputPath_button = Button(window, text="Search Folder", command=selectInputFolder)
inputPath_button.configure(bg="lightgray")
inputPath_button.grid(row=4, column=1, sticky='w', padx=15, pady=5)
#### Ouput folderDialog
# Ouput folderDialog label
outputPath_label = Label(window, text="Output Path:", bg=window["bg"])
outputPath_label.grid(row=5, column=1, sticky='w', padx=15, pady=5)
# Ouput folderDialog entry space
outputPath_entry = Entry(window, width=40)
outputPath_entry.grid(row=6, column=1, sticky='w', padx=15, pady=5)
# Ouput folderDialog button
outputPath_button = Button(window, text="Search Folder", command=selectOutputFolder)
outputPath_button.configure(bg="lightgray")
outputPath_button.grid(row=7, column=1, sticky='w', padx=15, pady=5)
################################################################################
#### button for saving settings
run_button = Button(window, text="Save input Settings", command=saveInputSettings)
run_button.configure(bg="lightgray")
run_button.grid(row=8, column=0, sticky='w', padx=15, pady=5)
#### Start the window
window.mainloop()
################################################################################
################################# prepare data #################################

# join data
if inputSettings['joinFiles'] == True:
    database = data.join_files_to_database(inputSettings['inputPath'], inputSettings['inputFilesFormat'])
else:
    if inputSettings['databaseFileName'] != '':
        database = pd.read_excel(inputSettings['databaseFileName'])

    else:
        print('WARNING: Select a database file or provide a valid input folder')

# sort by time
if inputSettings['sortByTime'] == True:
    database.index = database['Datetime']
    database = database.rename_axis('dt_index')
    database = database.sort_values(by='dt_index')
    database.index = range(len(database))
# set datetime column as pandas datetime
database['Datetime'] = pd.to_datetime(database['Datetime'])
# create output folder
databaseViewPath = os.path.join(inputSettings['outputPath'], 'DatabaseView')
os.makedirs(databaseViewPath, exist_ok=True)
# navigate to output folder
os.chdir(databaseViewPath)
# save database file if there is no input database file
if inputSettings['databaseFileName'] == '':
    database.to_excel(inputSettings['outputFileName']+'.xlsx')

################################################################################
# create data view settings dictionary
dataViewSettings = {}
############################## interactive tools ###############################
# Create window 2
window = Tk()
window.title("Data View Settings")
window.geometry("1100x500")
window.resizable(True, True)
window.configure(bg="lightblue")
font_style = ("Arial", 12, "bold")
################################################################################
############# Create the components of the window
####### column 1
#### dataType drop-down list
dType_label = Label(window, text="Data Type:", bg=window["bg"])
dType_label.grid(row=0, column=0, sticky='w', padx=15, pady=5)

dType_combobox = ttk.Combobox(window, values=["tscp profile", "mooring"])
dType_combobox.configure(width=25)
dType_combobox.grid(row=1, column=0, sticky='w', padx=15, pady=5)
#### year filter
# year filter  upper label
year_label = Label(window, text="Filter by Year:", bg=window["bg"])
year_label.grid(row=2, column=0, sticky='w', padx=15, pady=5)
# year filter entry space
year_entry = Entry(window)
year_entry.grid(row=3, column=0, sticky='w', padx=15, pady=5)
#### marker for panel 1
panel1 = BooleanVar(value=False)
panel1Button = Checkbutton(window, text="Panel 1 (mooring)", variable=panel1, bg="lightblue")
panel1Button.grid(row=4, column=0, sticky='w', padx=15, pady=5)
#### marker for panel 2
panel2 = BooleanVar(value=False)
panel2Button = Checkbutton(window, text="Panel 2 (mooring)", variable=panel2, bg="lightblue")
panel2Button.grid(row=5, column=0, sticky='w', padx=15, pady=5)
#### marker for panel 3
panel3 = BooleanVar(value=False)
panel3Button = Checkbutton(window, text="Panel 3 (profile)", variable=panel3, bg="lightblue")
panel3Button.grid(row=6, column=0, sticky='w', padx=15, pady=5)
####### column 2
#### marker for tendency lines
tendency = BooleanVar(value=False)
tendencyButton = Checkbutton(window, text="Tendency Lines (linear regression)", variable=tendency, bg="lightblue")
tendencyButton.grid(row=1, column=1, sticky='w', padx=15, pady=5)
#### tendency lines degree
# tendency upper label
tendency_label = Label(window, text="Degree:", bg=window["bg"])
tendency_label.grid(row=2, column=1, sticky='w', padx=15, pady=5)
# tendency entry space
tendency_entry = Entry(window)
tendency_entry.grid(row=3, column=1, sticky='w', padx=15, pady=5)
#### marker for date stacking
dateStack = BooleanVar(value=False)
dateStackButton = Checkbutton(window, text="Stack Dates", variable=dateStack, bg="lightblue")
dateStackButton.grid(row=4, column=1, sticky='w', padx=15, pady=5)
#### marker for data points
dataPoints = BooleanVar(value=False)
dateStackButton = Checkbutton(window, text="View Data Points", variable=dataPoints, bg="lightblue")
dateStackButton.grid(row=5, column=1, sticky='w', padx=15, pady=5)
####### column 3 --> 6
#### site selection
#site selection label
siteSelect_label = Label(window, text="Filter by Site:", bg=window["bg"])
siteSelect_label.grid(row=0, column=4, sticky='w', padx=15, pady=5)
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
####### column 7
#### parameter selection
#parameter selection label
parameterSelect_label = Label(window, text="Select Parameters:", bg=window["bg"])
parameterSelect_label.grid(row=0, column=6, sticky='w', padx=40, pady=5)
# list with site names for markers
parameter_names = ['Temperature(degC)', 'Salinity(PSU)', 'Conductivity(mS/cm)', 'Density(kg/m3)',	'CO2 Level(ppm)', 'O2 Level(uM)', 'PAR(umol/m2/s)',
                   'Turbidity(FTU)', 'Chlorophyll(ug/L)', 'Hydrogen Potential(pH)', 'Dissolved Organic Matter(ppb)', 'Soundspeed(m/s)']
selectedParameters = []
# dictionary to store boolean variables
parameterMarkers = {}
for i, param in enumerate(parameter_names):
    var = BooleanVar(value=False)
    checkbutton = Checkbutton(window, text=param, variable=var, bg="lightblue")
    checkbutton.grid(row=i+1, column=6, sticky='w', padx=40, pady=5)
    parameterMarkers[param] = var
#### button for running code
run_button = Button(window, text="Save Data View Settings", command=saveDataViewSettings)
run_button.configure(bg="lightgray")
run_button.grid(row=13, column=0, sticky='w', padx=15, pady=5)
#### button for running code
run_button = Button(window, text="Generate Panels", command=generatePanels)
run_button.configure(bg="lightgray")
run_button.grid(row=13, column=1, sticky='w', padx=15, pady=5)
# Start the window
window.mainloop()

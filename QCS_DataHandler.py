import os
import re
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import datetime
#import geomag
from matplotlib.widgets import RectangleSelector
from io import StringIO
from string import Template
from datetime import datetime as dt
from datetime import date
from os import walk

################################# Description ##################################
# QCS_DataHandler consists in a series of function to open and handle data files
# such as exported data from sensors and excel tables (.xls/.xlsx). Everything
# related to data formats and standardization, unit conversion, input and output
# files, etc.
################################################################################

# Search functions

def search_values (whr_file, string):
    #search for values in string type data
    #whr_file: input file in .whr format
    #string: string type sentence in which to search
    for linha in open(whr_file):
        m = re.search(string + "\s*(\d+)", linha, re.IGNORECASE)
        if m:
            valor = m.group(1)
            break
            return valor

def search_times (whr_file, string):
    #search for values in string type data
    #whr_file: input file in .whr format
    #string: string type sentence in which to search
    for linha in open(whr_file):
        m = re.search(string + "\s*(\d{2}/\d{2}/\d{4} \d{2}:\d{2}:\d{2})", linha, re.IGNORECASE)
        if m:
            time = m.group(1)
            break
            time = dt.strptime(m.group(1), '%d/%m/%Y %H:%M:%S')
            time = np.array(time, dtype='datetime64[us]')
            return time

def read_ctd(INPUT):
    file_path = os.path.join(INPUT['raw_data_path'], INPUT['file_name'])

    if INPUT['file_name'][-4:] == 'xlsx':
        dataframe = pd.read_excel(file_path, header=0)
    elif INPUT['file_name'][-3:] == 'csv':
        dataframe = pd.read_csv(file_path, header=0, delimiter=';')

    column_flags = {
        'Datetime': False,
        'Pressure (kPa)': False,
        'Temperature (degC)': False,
        'Conductivity (mS/cm)': False,
        'Salinity (PSU)': False,
        'Density (kg/m3)': False,
        'Soundspeed (m/s)': False,
        'Turbidity (FTU)': False,
        'TSS (mg/L)': False,
        'Chlorophyll (ug/L)': False,
        'Dissolved organic matter (ppb)': False,
        'pH': False,
        'PAR (umol/m2/s)': False,
        'O2 level (uM)': False,
        'O2 content (mg/L)': False
    }

    renamed_columns = []

    for i in np.arange(len(dataframe.columns)):
        column = dataframe.columns[i]

        if not column_flags['Datetime'] and re.search('time', column, re.IGNORECASE):
            dataframe = dataframe.rename(columns={column: 'Datetime'})
            column_flags['Datetime'] = True
            renamed_columns.append('Datetime')

        elif not column_flags['Pressure (kPa)'] and re.search('pressure', column, re.IGNORECASE):
            dataframe = dataframe.rename(columns={column: 'Pressure (kPa)'})
            column_flags['Pressure (kPa)'] = True
            renamed_columns.append('Pressure (kPa)')

        elif not column_flags['Temperature (degC)'] and re.search('temperature', column, re.IGNORECASE):
            dataframe = dataframe.rename(columns={column: 'Temperature (degC)'})
            column_flags['Temperature (degC)'] = True
            renamed_columns.append('Temperature (degC)')

        elif not column_flags['Conductivity (mS/cm)'] and re.search('conductivity', column, re.IGNORECASE):
            dataframe = dataframe.rename(columns={column: 'Conductivity (mS/cm)'})
            column_flags['Conductivity (mS/cm)'] = True
            renamed_columns.append('Conductivity (mS/cm)')

        elif not column_flags['Salinity (PSU)'] and re.search('salinity', column, re.IGNORECASE):
            dataframe = dataframe.rename(columns={column: 'Salinity (PSU)'})
            column_flags['Salinity (PSU)'] = True
            renamed_columns.append('Salinity (PSU)')

        elif not column_flags['Density (kg/m3)'] and re.search('density', column, re.IGNORECASE):
            dataframe = dataframe.rename(columns={column: 'Density (kg/m3)'})
            column_flags['Density (kg/m3)'] = True
            renamed_columns.append('Density (kg/m3)')

        elif not column_flags['Soundspeed (m/s)'] and re.search('soundspeed|speed of sound', column, re.IGNORECASE):
            dataframe = dataframe.rename(columns={column: 'Soundspeed (m/s)'})
            column_flags['Soundspeed (m/s)'] = True
            renamed_columns.append('Soundspeed (m/s)')

        elif not column_flags['Turbidity (FTU)'] and re.search('turbidity', column, re.IGNORECASE):
            dataframe = dataframe.rename(columns={column: 'Turbidity (FTU)'})
            column_flags['Turbidity (FTU)'] = True
            renamed_columns.append('Turbidity (FTU)')

        elif not column_flags['TSS (mg/L)'] and re.search('TSS', column):
            dataframe = dataframe.rename(columns={column: 'TSS (mg/L)'})
            column_flags['TSS (mg/L)'] = True
            renamed_columns.append('TSS (mg/L)')

        elif not column_flags['Chlorophyll (ug/L)'] and re.search('chlorophyll', column, re.IGNORECASE):
            dataframe = dataframe.rename(columns={column: 'Chlorophyll (ug/L)'})
            column_flags['Chlorophyll (ug/L)'] = True
            renamed_columns.append('Chlorophyll (ug/L)')

        elif not column_flags['Dissolved organic matter (ppb)'] and re.search('organic', column, re.IGNORECASE):
            dataframe = dataframe.rename(columns={column: 'Dissolved organic matter (ppb)'})
            column_flags['Dissolved organic matter (ppb)'] = True
            renamed_columns.append('Dissolved organic matter (ppb)')

        elif not column_flags['pH'] and re.search(r'^(?!.*raw).*pH.*$', column):
            dataframe = dataframe.rename(columns={column: 'pH'})
            column_flags['pH'] = True
            renamed_columns.append('pH')

        elif not column_flags['PAR (umol/m2/s)'] and re.search('PAR', column):
            dataframe = dataframe.rename(columns={column: 'PAR (umol/m2/s)'})
            column_flags['PAR (umol/m2/s)'] = True
            renamed_columns.append('PAR (umol/m2/s)')

        elif not column_flags['O2 level (uM)'] and re.search(r'^(?=.*O2)(?=.*uM).*$', column, re.IGNORECASE):
            dataframe = dataframe.rename(columns={column: 'O2 level (uM)'})
            column_flags['O2 level (uM)'] = True
            renamed_columns.append('O2 level (uM)')

        elif not column_flags['O2 content (mg/L)'] and re.search(r'^(?=.*O2)(?=.*content).*$', column, re.IGNORECASE):
            dataframe = dataframe.rename(columns={column: 'O2 content (mg/L)'})
            column_flags['O2 content (mg/L)'] = True
            renamed_columns.append('O2 content (mg/L)')

    dataframe = dataframe[renamed_columns]
    dataframe['Datetime'] = pd.to_datetime(dataframe['Datetime'])

    return dataframe

def read_ctd_csv(file_path):
    i=0
    for line in open(file_path):
        m = re.search('record', line, re.IGNORECASE)
        if m:
            break
        else:
            i += 1
    dataframe = pd.read_csv(file_path,
                            header=0,
                            skiprows=i,
                            sep=';',
                            decimal=',')

    dataframe['Record Time'] = pd.to_datetime(dataframe['Record Time'], dayfirst=True)

    dataframe = dataframe.rename(columns={'Record Time': 'Datetime',
                                          'Record Number': 'Sample number',
                                          'O2Concentration[uM]': 'O2 level (uM)',
                                          'AirSaturation[%]': 'AirSaturation(%)',
                                          'Temperature[Deg.C]': 'Temperature (degC)',
                                          'Pressure[kPa]': 'Pressure (kPa)',
                                          'Temperature[DegC]': 'Temperature (degC)2',
                                          'Conductivity[mS/cm]': 'Conductivity (mS/cm)',
                                          'Temperature[Deg.C].1': 'Temperature (degC)3',
                                          'Salinity[PSU]': 'Salinity (PSU)',
                                          'Density[kg/m3]': 'Density (kg/m3)',
                                          'Soundspeed[m/s]': 'Soundspeed (m/s)',
                                          'PAR[umol/m2/s]': 'PAR (umol/m2/s)',
                                          'Internal Temperature[Deg.C]': 'Internal Temperature (degC)',
                                          'Turbidity#16280[FTU]': 'Turbidity (FTU)',
                                          'Cyclops-7F  Chlorophyll#21180217[ug/L]': 'Chlorophyll (ug/L)',
                                          'AMT pH#18051103[pH]': 'pH',
                                          'AMT pH#18051103 Raw data[V]': 'Hydrogen Potential Raw Data(pH)',
                                          'Cyclops-7F Colored Dissolved Organic #21180228[ppb]': 'Dissolved organic matter (ppb)'})

    if dataframe['Datetime'].iloc[0] == dataframe['Datetime'].iloc[1]:
        i = 0
        while dataframe['Datetime'].iloc[i+1] == dataframe['Datetime'].iloc[i]:
            i += 1
        dataframe = dataframe[::(i+1)*10]
        dataframe.index = np.arange(len(dataframe))

    return dataframe

def read_ctd_profile_csv(file_path):
    from pandas.tseries.offsets import DateOffset
    i=0
    for line in open(file_path):
        m = re.search('record', line, re.IGNORECASE)
        if m:
            break
        else:
            i += 1
    try:
        dataframe = pd.read_csv(file_path,
                                header=0,
                                skiprows=i,
                                sep=';',
                                decimal=',',
                                na_values='#N/D')

        dataframe['Record Time'] = pd.to_datetime(dataframe['Record Time'], dayfirst=True)

    except:
        dataframe = pd.read_csv(file_path,
                                header=0,
                                sep=';',
                                decimal=',',
                                na_values='#N/D')


        dataframe['Record Time'] = pd.to_datetime(dataframe['Data'] + ' ' + dataframe['Time'], dayfirst=True)
        dataframe = dataframe.drop(columns=['Data', 'Time'], axis=0)

    dataframe = dataframe.rename(columns={'Record Time': 'Datetime',
                                          'Record Number': 'Sample number',
                                          'O2Concentration[uM]': 'O2 level (uM)',
                                          'AirSaturation[%]': 'AirSaturation(%)',
                                          'Temperature[Deg.C]': 'Temperature (degC)',
                                          'Pressure[kPa]': 'Pressure (kPa)',
                                          'Temperature[DegC]': 'Temperature (degC)2',
                                          'Conductivity[mS/cm]': 'Conductivity (mS/cm)',
                                          'Temperature[Deg.C].1': 'Temperature (degC)3',
                                          'Salinity[PSU]': 'Salinity (PSU)',
                                          'Density[kg/m3]': 'Density (kg/m3)',
                                          'Soundspeed[m/s]': 'Soundspeed (m/s)',
                                          'PAR[umol/m2/s]': 'PAR (umol/m2/s)',
                                          'Internal Temperature[Deg.C]': 'Internal Temperature (degC)',
                                          'Turbidity#16280[FTU]': 'Turbidity (FTU)',
                                          'Cyclops-7F  Chlorophyll#21180217[ug/L]': 'Chlorophyll (ug/L)',
                                          'AMT pH#18051103[pH]': 'pH',
                                          'AMT pH#18051103 Raw data[V]': 'Hydrogen Potential Raw Data(pH)',
                                          'Cyclops-7F Colored Dissolved Organic #21180228[ppb]': 'Dissolved organic matter (ppb)'})

    if dataframe['Datetime'].iloc[0] == dataframe['Datetime'].iloc[1]:
        a = 0
        while dataframe['Datetime'].iloc[a+1] == dataframe['Datetime'].iloc[a]:
            a += 1
        b = a + 1
        while dataframe['Datetime'].iloc[b+1] == dataframe['Datetime'].iloc[b]:
            b += 1
        n = b - a
        ms_interval = 60/n
        initSeconds = 60 - ((a + 1) * ms_interval)
        for i in range(a + 1):
            #seconds = 60 - (((a + 1) * ms_interval) - (i * (a + 1)))
            dataframe.loc[i, 'Datetime'] += DateOffset(seconds=initSeconds)
            initSeconds += ms_interval
        for i in range((a+1), len(dataframe)):
            if i <= n + (a + 1):
                seconds = (i-(a+1)) * ms_interval
                if seconds == 60:
                    dataframe.loc[i, 'Datetime'] += DateOffset(seconds=0)
                else:
                    dataframe.loc[i, 'Datetime'] += DateOffset(seconds=seconds)
            else:
                rounds = int((i-(a + 1))/n)
                seconds = ((i-(a+1)) * ms_interval) - (rounds * 60)
                if seconds == 60:
                    dataframe.loc[i, 'Datetime'] += DateOffset(seconds=0)
                else:
                    dataframe.loc[i, 'Datetime'] += DateOffset(seconds=seconds)
    return dataframe


def read_unified_excel(file_path):
    #open a file in unified table format
    #file_path: path to open excel file
    dataframe = pd.read_excel(file_path,
                               header=0,
                               na_values='N/A',
                               parse_dates=[0],
                               names=['Time_ISO8601',
                                      'Expedition',
                                      'Site',
                                      'Longitude',
                                      'Latitude',
                                      'CO2 Level(ppm)',
                                      'O2 level (uM)',
                                      'Temperature (degC)',
                                      'Depth (m)',
                                      'Conductivity (mS/cm)',
                                      'Salinity (PSU)',
                                      'Density (kg/m3)',
                                      'PAR (umol/m2/s)',
                                      'Turbidity (FTU)',
                                      'Chlorophyll (ug/L)',
                                      'pH',
                                      'Dissolved organic matter (ppb)',
                                      'Sample number'])
    return dataframe

def read_unified_hobo(file_path):
    col_names = ['Site', 'Hour', 'Temperature (degC)', 'Luminosity (lux)',
                 'Luminosity(lm/ft2)', 'Hobo Units', 'Date', 'Datetime' ]

    dataframe = pd.read_csv(file_path, names=col_names, skiprows=1)
    dataframe['Datetime'] = pd.to_datetime(dataframe['Datetime'])
    dataframe = dataframe[['Site', 'Temperature (degC)', 'Luminosity (lux)',
                           'Hobo Units', 'Datetime']]

    valid_idx = np.where(dataframe['Datetime'].isna()==False)[0]
    dataframe = dataframe.iloc[valid_idx]

    dataframe.index = dataframe['Datetime']
    dataframe = dataframe.rename_axis('dt_index')
    dataframe = dataframe.sort_values(by='dt_index')
    dataframe.index = np.arange(len(dataframe))
    tempFrame = dataframe[['Site', 'Temperature (degC)', 'Hobo Units', 'Datetime']]
    lumiFrame = dataframe[['Site', 'Luminosity (lux)', 'Hobo Units', 'Datetime']]
    return dataframe, tempFrame, lumiFrame
# Conversion functions

def convert_tscp_units (data, pressure_unit, conductivity_unit):
    # convert units specified in the input files
    # to software standard ['dbar', 'mS/cm']
    #
    # supported units:
    #     -pressure[bar, kpa] --> dbar
    #     -conductivity[S/m] --> mS/cm
    #
    # does nothinh if the specified unit is already the software standard

    if re.match('bar', pressure_unit, re.IGNORECASE):
        for name in data.columns:
            if re.search('pressure', name, re.IGNORECASE):
                data[name] = data[name] * 10
    elif re.match('kpa', pressure_unit, re.IGNORECASE):
        for name in data.columns:
            if re.search('pressure', name, re.IGNORECASE):
                data[name] = data[name] / 10
    if re.match('s/m', conductivity_unit, re.IGNORECASE):
        for name in data.columns:
            if re.search('conductivity', name, re.IGNORECASE):
                data[name] = data[name] * 10
    return data

def pressure_to_depth (dataframe, latitude, adjust_for_atm):
    for name in dataframe.columns:
        if re.search('pressure', name, re.IGNORECASE):
            p = dataframe[name]
            if adjust_for_atm == True:
                p = p - 10
    x = np.square(np.sin(latitude/5.29578))
    g = 9.780318 * (1+(5.2788e-3 + 2.36e-5 * x)* x) + 1.092e-6 * p
    depth = ((((-1.82e-15 * p + 2.279e-10) * p-2.2512e-5) * p + 9.72659)*p) / g
    dataframe['Depth (m)'] = round(depth, 2)
    return dataframe

# Function for preparing output files

def handle_output_file (input_df, flags, remove_suspect, remove_bad, Profile):
    # standardize data frame to output file format and
    # classify bad, suspect and missing data for temperature,
    # salinity, conductivity or pressure parameters
    #
    # input_df: input data frame
    # flags: list conteining flag codes in string like formats
    # SUSPECT_DATA: condition for placing NaN in suspect data index
    # BAD_DATA: condition for placing NaN in bad data index
    #
    # outputs
    # output_df: output data frame
    # input_df: input data frame
    # T_bdata: : list of temperature bad data indexes
    # S_bdata: list of salinity bad data indexes
    # C_bdata: list of conductivity bad data indexes
    # P_bdata: list of pressure bad data indexes
    # T_sdata: list of temperature suspect data indexes
    # S_sdata: list of salinity suspect data indexes
    # C_sdata: list of conductivity suspect data indexes
    # P_sdata : list of pressure suspect data indexes
    # T_mdata: list of temperature missing data indexes
    # S_mdata: list of salinity missing data indexes
    # C_mdata: list of conductivity missing data indexes
    # P_mdata: list of temperapressureture missing data indexes
    # pH_bdata: list of pH bad data indexes
    # chl_bdata: list of chlorophyll bad data indexes
    # O2_bdata: list of dissolved oxygen bad data indexes
    # org_bdata: list of dissolved organic matter bad data indexes
    # tur_bdata: list of turbidity bad data indexes
    # pH_sdata: list of pH suspect data indexes
    # chl_sdata: list of chlorophyll suspect data indexes
    # O2_sdata: list of dissolved oxygen suspect data indexes
    # org_sdata: list of dissolved organic matter suspect data indexes
    # tur_sdata: list of turbidity suspect data indexes
    # pH_mdata: list of pH missing data indexes
    # chl_mdata: list of chlorophyll missing data indexes
    # O2_mdata: list of dissolved oxygen missing data indexes
    # org_mdata: list of dissolved organic matter missing data indexes
    # tur_mdata: list of turbidity missing data indexes

    output_df = input_df.copy()
    output_df['Flag'] = flags
    T_bdata, S_bdata, C_bdata, P_bdata = ([], [], [], [])
    T_sdata, S_sdata, C_sdata, P_sdata = ([], [], [], [])
    T_mdata, S_mdata, C_mdata, P_mdata = ([], [], [], [])

    pH_bdata, chl_bdata, O2_bdata, org_bdata, tur_bdata = ([], [], [], [], [])
    pH_sdata, chl_sdata, O2_sdata, org_sdata, tur_sdata = ([], [], [], [], [])
    pH_mdata, chl_mdata, O2_mdata, org_mdata, tur_mdata = ([], [], [], [], [])
    # classifying data as bad, suspect and missing based on measured paramater
    for i in range(len(flags)):
        if flags[i][0] == '4' or flags[i][4] == '4' or flags[i][13] == '4' or flags[i][22] == '4' or flags[i][26] == '4':
            T_bdata.append(i)
        elif flags[i][0] == '3' or flags[i][4] == '3' or flags[i][13] == '3' or flags[i][22] == '3' or flags[i][26] == '3':
            T_sdata.append(i)
        elif flags[i][0] == '9' or flags[i][4] == '9' or flags[i][13] == '9' or flags[i][22] == '9' or flags[i][26] == '9':
            T_mdata.append(i)
        if flags[i][1] == '4' or flags[i][5] == '4' or flags[i][14] == '4' or flags[i][23] == '4' or flags[i][27] == '4':
            S_bdata.append(i)
        elif flags[i][1] == '3' or flags[i][5] == '3' or flags[i][14] == '3' or flags[i][23] == '3' or flags[i][27] == '3':
            S_sdata.append(i)
        elif flags[i][1] == '9' or flags[i][5] == '9' or flags[i][14] == '9' or flags[i][23] == '9' or flags[i][27] == '9':
            S_mdata.append(i)
        if flags[i][2] == '4' or flags[i][6] == '4' or flags[i][15] == '4' or flags[i][24] == '4' or flags[i][28] == '4':
            C_bdata.append(i)
        elif flags[i][2] == '3' or flags[i][6] == '3' or flags[i][15] == '3' or flags[i][24] == '3' or flags[i][28] == '3':
            C_sdata.append(i)
        elif flags[i][2] == '9' or flags[i][6] == '9' or flags[i][15] == '9' or flags[i][24] == '9' or flags[i][28] == '9':
            C_mdata.append(i)
        if flags[i][3] == '4' or flags[i][7] == '4' or flags[i][16] == '4' or flags[i][25] == '4' or flags[i][29] == '4':
            P_bdata.append(i)
        elif flags[i][3] == '3' or flags[i][7] == '3' or flags[i][16] == '3' or flags[i][25] == '3' or flags[i][29] == '3':
            P_sdata.append(i)
        elif flags[i][3] == '9' or flags[i][7] == '9' or flags[i][16] == '9' or flags[i][25] == '9' or flags[i][29] == '9':
            P_mdata.append(i)
        if flags[i][8] == '4' or flags[i][17] == '4':
            pH_bdata.append(i)
        elif flags[i][8] == '3' or flags[i][17] == '3':
            pH_sdata.append(i)
        elif flags[i][8] == '9' or flags[i][17] == '9':
            pH_mdata.append(i)
        if flags[i][9] == '4' or flags[i][18] == '4':
            chl_bdata.append(i)
        elif flags[i][9] == '3' or flags[i][18] == '3':
            chl_sdata.append(i)
        elif flags[i][9] == '9' or flags[i][18] == '9':
            chl_mdata.append(i)
        if flags[i][10] == '4' or flags[i][19] == '4':
            O2_bdata.append(i)
        elif flags[i][10] == '3' or flags[i][19] == '3':
            O2_sdata.append(i)
        elif flags[i][10] == '9' or flags[i][19] == '9':
            O2_mdata.append(i)
        if flags[i][11] == '4' or flags[i][20] == '4':
            org_bdata.append(i)
        elif flags[i][11] == '3' or flags[i][20] == '3':
            org_sdata.append(i)
        elif flags[i][11] == '9' or flags[i][20] == '9':
            org_mdata.append(i)
        if flags[i][12] == '4' or flags[i][21] == '4':
            tur_bdata.append(i)
        elif flags[i][12] == '3' or flags[i][21] == '3':
            tur_sdata.append(i)
        elif flags[i][12] == '9' or flags[i][21] == '9':
            tur_mdata.append(i)

        if Profile == True:
            if flags[i][30] == '4':
                T_bdata.append(i)
            elif flags[i][30] == '3':
                T_sdata.append(i)
            elif flags[i][30] == '9':
                T_mdata.append(i)
            if flags[i][31] == '4':
                S_bdata.append(i)
            elif flags[i][31] == '3':
                S_sdata.append(i)
            elif flags[i][31] == '9':
                S_mdata.append(i)
            if flags[i][32] == '4':
                C_bdata.append(i)
            elif flags[i][32] == '3':
                C_sdata.append(i)
            elif flags[i][32] == '9':
                C_mdata.append(i)

    # converting lists to arrays
    T_bdata, S_bdata, C_bdata, P_bdata = (np.asarray(T_bdata), np.asarray(S_bdata), np.asarray(C_bdata), np.asarray(P_bdata))
    T_sdata, S_sdata, C_sdata, P_sdata = (np.asarray(T_sdata), np.asarray(S_sdata), np.asarray(C_sdata), np.asarray(P_sdata))
    T_mdata, S_mdata, C_mdata, P_mdata = (np.asarray(T_mdata), np.asarray(S_mdata), np.asarray(C_mdata), np.asarray(P_mdata))

    pH_bdata, chl_bdata, O2_bdata, org_bdata, tur_bdata = (np.asarray(pH_bdata), np.asarray(chl_bdata), np.asarray(O2_bdata), np.asarray(org_bdata), np.asarray(tur_bdata))
    pH_sdata, chl_sdata, O2_sdata, org_sdata, tur_sdata = (np.asarray(pH_sdata), np.asarray(chl_sdata), np.asarray(O2_sdata), np.asarray(org_sdata), np.asarray(tur_sdata))
    pH_mdata, chl_mdata, O2_mdata, org_mdata, tur_mdata = (np.asarray(pH_mdata), np.asarray(chl_mdata), np.asarray(O2_mdata), np.asarray(org_mdata), np.asarray(tur_mdata))

    # excluding index for suspect data which repeats for bad data index
    # and index for bad data which repeats for missing data index
    T_sdata = np.delete(T_sdata, np.where(T_sdata==np.intersect1d(T_sdata, T_bdata))[0])
    T_sdata = np.delete(T_sdata, np.where(T_sdata==np.intersect1d(T_sdata, T_mdata))[0])
    T_bdata = np.delete(T_bdata, np.where(T_bdata == np.intersect1d(T_mdata, T_bdata))[0])

    S_sdata = np.delete(S_sdata, np.where(S_sdata==np.intersect1d(S_sdata, S_bdata))[0])
    S_sdata = np.delete(S_sdata, np.where(S_sdata==np.intersect1d(S_sdata, S_mdata))[0])
    S_bdata = np.delete(S_bdata, np.where(S_bdata == np.intersect1d(S_mdata, S_bdata))[0])

    C_sdata = np.delete(C_sdata, np.where(C_sdata==np.intersect1d(C_sdata, C_bdata))[0])
    C_sdata = np.delete(C_sdata, np.where(C_sdata==np.intersect1d(C_sdata, C_mdata))[0])
    C_bdata = np.delete(C_bdata, np.where(C_bdata == np.intersect1d(C_mdata, C_bdata))[0])

    P_sdata = np.delete(P_sdata, np.where(P_sdata==np.intersect1d(P_sdata, P_bdata))[0])
    P_sdata = np.delete(P_sdata, np.where(P_sdata==np.intersect1d(P_sdata, P_mdata))[0])
    P_bdata = np.delete(P_bdata, np.where(P_bdata == np.intersect1d(P_mdata, P_bdata))[0])

    pH_sdata = np.delete(pH_sdata, np.where(pH_sdata==np.intersect1d(pH_sdata, pH_bdata))[0])
    pH_sdata = np.delete(pH_sdata, np.where(pH_sdata==np.intersect1d(pH_sdata, pH_mdata))[0])
    pH_bdata = np.delete(pH_bdata, np.where(pH_bdata == np.intersect1d(pH_mdata, pH_bdata))[0])

    chl_sdata = np.delete(chl_sdata, np.where(chl_sdata==np.intersect1d(chl_sdata, chl_bdata))[0])
    chl_sdata = np.delete(chl_sdata, np.where(chl_sdata==np.intersect1d(chl_sdata, chl_mdata))[0])
    chl_bdata = np.delete(chl_bdata, np.where(chl_bdata == np.intersect1d(chl_mdata, chl_bdata))[0])

    O2_sdata = np.delete(O2_sdata, np.where(O2_sdata==np.intersect1d(O2_sdata, O2_bdata))[0])
    O2_sdata = np.delete(O2_sdata, np.where(O2_sdata==np.intersect1d(O2_sdata, O2_mdata))[0])
    O2_bdata = np.delete(O2_bdata, np.where(O2_bdata == np.intersect1d(O2_mdata, O2_bdata))[0])

    org_sdata = np.delete(org_sdata, np.where(org_sdata==np.intersect1d(org_sdata, org_bdata))[0])
    org_sdata = np.delete(org_sdata, np.where(org_sdata==np.intersect1d(org_sdata, org_mdata))[0])
    org_bdata = np.delete(org_bdata, np.where(org_bdata == np.intersect1d(org_mdata, org_bdata))[0])

    tur_sdata = np.delete(tur_sdata, np.where(tur_sdata==np.intersect1d(tur_sdata, tur_bdata))[0])
    tur_sdata = np.delete(tur_sdata, np.where(tur_sdata==np.intersect1d(tur_sdata, tur_mdata))[0])
    tur_bdata = np.delete(tur_bdata, np.where(tur_bdata == np.intersect1d(tur_mdata, tur_bdata))[0])
    # changing bad or suspect data to NaN according from operators input
    if remove_bad == True:
        for name in output_df.columns:
            if re.search('temperature', name, re.IGNORECASE):
                output_df.loc[T_bdata, name] = np.nan
            if re.search('salinity', name, re.IGNORECASE):
                output_df.loc[S_bdata, name] = np.nan
            if re.search('conductivity', name, re.IGNORECASE):
                output_df.loc[C_bdata, name] = np.nan
            if re.search('pressure', name, re.IGNORECASE):
                output_df.loc[P_bdata, name] = np.nan
            if re.search('pH', name, re.IGNORECASE):
                output_df.loc[pH_bdata, name] = np.nan
            if re.search('chlorophyll', name, re.IGNORECASE):
                output_df.loc[chl_bdata, name] = np.nan
            if re.search('o2', name, re.IGNORECASE):
                output_df.loc[O2_bdata, name] = np.nan
            if re.search('organic matter', name, re.IGNORECASE):
                output_df.loc[org_bdata, name] = np.nan
            if re.search('turbidity|tss', name, re.IGNORECASE):
                output_df.loc[tur_bdata, name] = np.nan
    if remove_suspect == True:
        for name in output_df.columns:
            if re.search('temperature', name, re.IGNORECASE):
                output_df.loc[T_sdata, name] = np.nan
            if re.search('salinity', name, re.IGNORECASE):
                output_df.loc[S_sdata, name] = np.nan
            if re.search('conductivity', name, re.IGNORECASE):
                output_df.loc[C_sdata, name] = np.nan
            if re.search('pressure', name, re.IGNORECASE):
                output_df.loc[P_sdata, name] = np.nan
            if re.search('pH', name, re.IGNORECASE):
                output_df.loc[pH_sdata, name] = np.nan
            if re.search('chlorophyll', name, re.IGNORECASE):
                output_df.loc[chl_sdata, name] = np.nan
            if re.search('o2', name, re.IGNORECASE):
                output_df.loc[O2_sdata, name] = np.nan
            if re.search('organic matter', name, re.IGNORECASE):
                output_df.loc[org_sdata, name] = np.nan
            if re.search('turbidity|tss', name, re.IGNORECASE):
                output_df.loc[tur_sdata, name] = np.nan
    return output_df, input_df, T_bdata, S_bdata, C_bdata, P_bdata, pH_bdata, chl_bdata, O2_bdata, org_bdata, tur_bdata, T_sdata, S_sdata, C_sdata, P_sdata, pH_sdata, chl_sdata, O2_sdata, org_sdata, tur_sdata, T_mdata, S_mdata, C_mdata, P_mdata, pH_mdata, chl_mdata, O2_mdata, org_mdata, tur_mdata

def order_var (qualified_data, n_cel, data_type):
    if data_type == 'tscp':
        var_priority = {'Sample number': 0, 'Datetime': 1, 'Depth (m)': 2, 'Temperature (degC)': 3, 'Salinity (PSU)': 4,
                        'Conductivity (mS/cm)': 5, 'Pressure(dbar)': 6, 'Density (kg/m3)': 7, 'CO2 Level(ppm)': 8,
                        'O2 level (uM)': 9, 'O2 content (mg/L)': 10, 'PAR (umol/m2/s)': 11, 'Turbidity (FTU)': 12, 'TSS (mg/L)': 13, 
                        'Chlorophyll (ug/L)': 14, 'pH': 15, 'Dissolved organic matter (ppb)': 16, 'Luminosity (lux)': 17,
                        'Soundspeed (m/s)': 18, 'Expedition': 19, 'Site': 20, 'Longitude': 21, 'Latitude': 22,
                        'Battery voltage (V)': 23, 'Flag': 24}

    order = {}
    for var in var_priority.keys():
        if var in qualified_data.columns:
            order[var] = var_priority[var]
        else:
            if re.search('correlation', var, re.IGNORECASE):
                pass
            else:
                qualified_data[var] = np.nan
                order[var] = var_priority[var]
    order_l = sorted(order.items(), key=lambda x: x[1], reverse=False)
    n = 0
    for item in order_l:
        var = item[0]
        order[var] = n
        n +=1
    for var in order.keys():
        col = qualified_data.pop(var)
        qualified_data.insert(order[var], var, col)
    qualified_data = qualified_data.round(4)
    for var in qualified_data.columns:
        if var not in var_priority.keys():
            if re.search('depthlevel', var, re.IGNORECASE):
                n = int(re.search('\d{1,3}', var).group())
                if n > n_cel:
                    qualified_data = qualified_data.drop(columns=[var])
            else:
                if re.search('speed', var, re.IGNORECASE) or re.search('direction', var, re.IGNORECASE):
                    pass
                else:
                    qualified_data = qualified_data.drop(columns=[var])
    return qualified_data

def tscp_stats_table (qualified_data):
    check = []
    for var in qualified_data.columns:
        if re.match('temperature\(degC\)|salinity\(psu\)|pressure\(dbar\)', var, re.IGNORECASE):
            check.append(var)
    if len(check) == 3:
        stat = pd.DataFrame({'Variable':['Temperature (degC)','Salinity (PSU)','Pressure(dbar)'],
                              'Max':[np.nanmax(qualified_data['Temperature (degC)']),np.nanmax(qualified_data['Salinity (PSU)']),np.nanmax(qualified_data['Pressure(dbar)'])],
                              'Min':[np.nanmin(qualified_data['Temperature (degC)']),np.nanmin(qualified_data['Salinity (PSU)']),np.nanmin(qualified_data['Pressure(dbar)'])],
                              'Mean':[np.nanmean(qualified_data['Temperature (degC)']),np.nanmean(qualified_data['Salinity (PSU)']),np.nanmean(qualified_data['Pressure(dbar)'])],
                              'Median':[np.nanmedian(qualified_data['Temperature (degC)']),np.nanmedian(qualified_data['Salinity (PSU)']),np.nanmedian(qualified_data['Pressure(dbar)'])],
                              'std':[np.nanstd(qualified_data['Temperature (degC)']),np.nanstd(qualified_data['Salinity (PSU)']),np.nanstd(qualified_data['Pressure(dbar)'])]})
    elif len(check) == 1:
        stat = pd.DataFrame({'Variable':['Temperature (degC)'],
                              'Max':np.nanmax(qualified_data['Temperature (degC)']),
                              'Min':np.nanmin(qualified_data['Temperature (degC)']),
                              'Mean':np.nanmean(qualified_data['Temperature (degC)']),
                              'Median':np.nanmedian(qualified_data['Temperature (degC)']),
                              'std':np.nanstd(qualified_data['Temperature (degC)'])})

    stat = stat[['Variable','Max','Min','Mean', 'Median', 'std']]
    stat = stat.round(2)
    return stat

# other functions

def count_test_bdata(flags):
    N = 0
    for i in range(len(flags)):
        if flags[i][-1] == '4':
            N+=1
    return N

def on_motion(event):
    # verify if mouse is above a line
    if event.inaxes is not None:
        for line in event.inaxes.lines:
            if line.contains(event)[0]:
                # define buffer linestyle
                line.set_linewidth(3.0)
                line.set_alpha(1.0)
            else:
                # define no buffer linestyle
                line.set_linewidth(1.0)
                line.set_alpha(0.5)
                # update plot
                event.inaxes.figure.canvas.draw_idle()

def trim_selected_variable (data, name):
    #select x and y data
    y = data[name]
    x = data[name].index

    # Criação do gráfico
    fig, ax = plt.subplots()
    ax.plot(x, y, linestyle='-', marker='x', markeredgecolor='r', markerfacecolor='r', picker=5)  # O parâmetro picker=5 define a sensibilidade para a seleção de pontos
    ax.set_title(name)
    ax.set_ylabel(name)
    ax.set_xlabel('Sample number')
    # Função para remover pontos selecionados
    selected_points = []
    def on_select(eclick, erelease):
        #global x, y
        x0, y0 = eclick.xdata, eclick.ydata
        x1, y1 = erelease.xdata, erelease.ydata
        mask = (x > min(x0, x1)) & (x < max(x0, x1)) & \
               (y > min(y0, y1)) & (y < max(y0, y1))
        y[mask] = np.nan # Substitui pontos selecionados por NaN
        #x, y = x[~mask], y[~mask]  # Remove os pontos selecionados
        ax.clear()  # Limpa o gráfico
        ax.plot(x, y, linestyle='-', marker='x', markeredgecolor='r', markerfacecolor='r', picker=5)  # Desenha os pontos restantes
        ax.set_title(name)
        ax.set_ylabel(name)
        ax.set_xlabel('Sample number')
        fig.canvas.draw()  # Redesenha o gráfico

    def on_key_press(event):
        if event.key =='enter':
            fig.canvas.mpl_disconnect(cid)
            plt.close()

    # Criação do widget de seleção de pontos
    selector = RectangleSelector(ax, on_select,
                                 useblit=True,
                                 button=[1],  # Somente botão esquerdo do mouse
                                 minspanx=5, minspany=5,
                                 spancoords='pixels',
                                 interactive=True)

    ax.set_xlim(np.nanmin(x)-0.1,np.nanmax(x)+0.1)
    ax.set_ylim(np.nanmin(y)-0.1,np.nanmax(y)+0.1)
    plt.show()  # Exibe o gráfico

    cid = fig.canvas.mpl_connect('key_press_event', on_key_press)

    trigger = False
    while trigger == False:
        trigger = plt.waitforbuttonpress()
        if trigger == True:
            data[name] = y
            #data.to_csv(filename + '_trim.csv')
            plt.close(fig)
    return data

def join_files_to_database(path, inputFilesFormat):
    folder_names = next(walk(path), (None, None, []))[1]
    folder_names = [item for item in folder_names if '__pycache__' not in item]
    dic = {}
    for folder in folder_names:
        subfolder_names = next(walk(path + '/' + folder), (None, None, []))[1]
        subfolder_names = [item for item in subfolder_names if '__pycache__' not in item]
        for ff in subfolder_names:
            f = ff if re.search('data', ff, re.IGNORECASE) else 0
            os.chdir(path + '/' + folder + '/' + f)
            file_names = next(walk(path + '/' + folder + '/' + f), (None, None, []))[2]
            file_names = [item for item in file_names if '__pycache__' not in item]
            for file in file_names:
                if re.search('xlsx', inputFilesFormat, re.IGNORECASE):
                    if re.search('.xlsx', file, re.IGNORECASE):
                        df = pd.read_excel(file, header=0)
                        #site = file[4:8] if file[4] == 'P' or file[4] == 'R' else file[4:7]
                        #df['Site'] = site
                        dic[file] = df

                if re.search('csv', inputFilesFormat, re.IGNORECASE):
                    if re.search('.csv', file, re.IGNORECASE):
                        df = pd.read_csv(file, header=1)
                        #site = file[4:8] if file[4] == 'P' or file[4] == 'R' else file[4:7]
                        #df['Site'] = site
                        dic[file] = df

    database = pd.concat(dic, ignore_index=True)
    database.index = np.arange(len(database))
    return database

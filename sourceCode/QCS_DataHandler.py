import os
import re
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.widgets import RectangleSelector
from os import walk

# Software version: single source of truth, shown in window titles,
# 'About' dialogs and in the 'QCS version' column of qualified files.
# Update ONLY here when releasing a new version.
QCS_VERSION = 'v3.2'

################################# Description ##################################
# QCS_DataHandler consists in a series of function to open and handle data files
# such as exported data from sensors and excel tables (.xls/.xlsx). Everything
# related to data formats and standardization, unit conversion, input and output
# files, etc.
################################################################################

# Search functions

def read_ctd(INPUT):
    # define file path
    file_path = os.path.join(INPUT['raw_data_path'], INPUT['file_name'])
    
    # First determine file type and handle accordingly
    if INPUT['file_name'].lower().endswith('.xlsx'):
        # For Excel files, we need a different approach to find the header
        # Read the file line by line to find the header row
        header_row = 0
        with pd.ExcelFile(file_path) as xls:
            # Read first 20 rows to find the header
            df_sample = pd.read_excel(xls, nrows=20, header=None)
            for i, row in df_sample.iterrows():
                if row.astype(str).str.contains('record time', case=False).any():
                    header_row = i
                    break
        
        # Now read the file properly with the found header row
        dataframe = pd.read_excel(file_path, skiprows=header_row, header=0)
        
    elif INPUT['file_name'].lower().endswith('.csv'):
        # For CSV files, we can use the original approach
        i = 0
        with open(file_path) as f:
            for line in f:
                if re.search('record time', line, re.IGNORECASE):
                    break
                i += 1
        dataframe = pd.read_csv(file_path, skiprows=i, header=0, delimiter=';')
    else:
        raise ValueError("Unsupported file format. Only .xlsx and .csv files are supported.")

    # set flags for identified columns
    column_flags = {
        'Datetime': False,
        'Pressure (kPa)': False,
        'Depth (m)': False,
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
    
    # create renamed columns list
    renamed_columns = []
    
    # enter loop for finding and renaming columns
    for column in dataframe.columns:   
        column_str = str(column)  # Ensure we're working with string

        if not column_flags['Datetime'] and re.search('time', column_str, re.IGNORECASE):
            dataframe = dataframe.rename(columns={column: 'Datetime'})
            column_flags['Datetime'] = True
            renamed_columns.append('Datetime')

        elif not column_flags['Pressure (kPa)'] and re.search('pressure', column_str, re.IGNORECASE):
            dataframe = dataframe.rename(columns={column: 'Pressure (kPa)'})
            column_flags['Pressure (kPa)'] = True
            renamed_columns.append('Pressure (kPa)')

        elif not column_flags['Depth (m)'] and re.search('prof|depth', column_str, re.IGNORECASE):
            dataframe = dataframe.rename(columns={column: 'Depth (m)'})
            column_flags['Depth (m)'] = True
            renamed_columns.append('Depth (m)')

        elif not column_flags['Temperature (degC)'] and re.search('temperature', column_str, re.IGNORECASE):
            dataframe = dataframe.rename(columns={column: 'Temperature (degC)'})
            column_flags['Temperature (degC)'] = True
            renamed_columns.append('Temperature (degC)')

        elif not column_flags['Conductivity (mS/cm)'] and re.search('conductivity', column_str, re.IGNORECASE):
            dataframe = dataframe.rename(columns={column: 'Conductivity (mS/cm)'})
            column_flags['Conductivity (mS/cm)'] = True
            renamed_columns.append('Conductivity (mS/cm)')

        elif not column_flags['Salinity (PSU)'] and re.search('salinity', column_str, re.IGNORECASE):
            dataframe = dataframe.rename(columns={column: 'Salinity (PSU)'})
            column_flags['Salinity (PSU)'] = True
            renamed_columns.append('Salinity (PSU)')

        elif not column_flags['Density (kg/m3)'] and re.search('density', column_str, re.IGNORECASE):
            dataframe = dataframe.rename(columns={column: 'Density (kg/m3)'})
            column_flags['Density (kg/m3)'] = True
            renamed_columns.append('Density (kg/m3)')

        elif not column_flags['Soundspeed (m/s)'] and re.search('soundspeed|speed of sound', column_str, re.IGNORECASE):
            dataframe = dataframe.rename(columns={column: 'Soundspeed (m/s)'})
            column_flags['Soundspeed (m/s)'] = True
            renamed_columns.append('Soundspeed (m/s)')

        elif not column_flags['Turbidity (FTU)'] and re.search('turbidity', column_str, re.IGNORECASE):
            dataframe = dataframe.rename(columns={column: 'Turbidity (FTU)'})
            column_flags['Turbidity (FTU)'] = True
            renamed_columns.append('Turbidity (FTU)')

        elif not column_flags['TSS (mg/L)'] and re.search('TSS', column_str):
            dataframe = dataframe.rename(columns={column: 'TSS (mg/L)'})
            column_flags['TSS (mg/L)'] = True
            renamed_columns.append('TSS (mg/L)')

        elif not column_flags['Chlorophyll (ug/L)'] and re.search('chlorophyll', column_str, re.IGNORECASE):
            dataframe = dataframe.rename(columns={column: 'Chlorophyll (ug/L)'})
            column_flags['Chlorophyll (ug/L)'] = True
            renamed_columns.append('Chlorophyll (ug/L)')

        elif not column_flags['Dissolved organic matter (ppb)'] and re.search('organic', column_str, re.IGNORECASE):
            dataframe = dataframe.rename(columns={column: 'Dissolved organic matter (ppb)'})
            column_flags['Dissolved organic matter (ppb)'] = True
            renamed_columns.append('Dissolved organic matter (ppb)')

        elif not column_flags['pH'] and re.search(r'^(?!.*raw).*pH.*$', column_str):
            dataframe = dataframe.rename(columns={column: 'pH'})
            column_flags['pH'] = True
            renamed_columns.append('pH')

        elif not column_flags['PAR (umol/m2/s)'] and re.search('PAR', column_str):
            dataframe = dataframe.rename(columns={column: 'PAR (umol/m2/s)'})
            column_flags['PAR (umol/m2/s)'] = True
            renamed_columns.append('PAR (umol/m2/s)')

        elif not column_flags['O2 level (uM)'] and re.search(r'^(?=.*O2)(?=.*uM).*$', column_str, re.IGNORECASE):
            dataframe = dataframe.rename(columns={column: 'O2 level (uM)'})
            column_flags['O2 level (uM)'] = True
            renamed_columns.append('O2 level (uM)')

        elif not column_flags['O2 content (mg/L)'] and re.search(r'^(?=.*O2)(?=.*content).*$', column_str, re.IGNORECASE):
            dataframe = dataframe.rename(columns={column: 'O2 content (mg/L)'})
            column_flags['O2 content (mg/L)'] = True
            renamed_columns.append('O2 content (mg/L)')
    
    # keep only identified columns
    dataframe = dataframe[renamed_columns]

    if 'Datetime' not in dataframe.columns:
        raise ValueError("No time column found in input file '%s'" % INPUT['file_name'])

    # set datetime column
    dataframe['Datetime'] = pd.to_datetime(dataframe['Datetime'], dayfirst=True)

    # discard records without a valid timestamp (e.g. truncated trailing rows
    # left by interrupted sensor exports) — they cannot be qualified
    n_invalid = int(dataframe['Datetime'].isna().sum())
    if n_invalid > 0:
        print('WARNING: %d record(s) without valid timestamp discarded from %s'
              % (n_invalid, INPUT['file_name']))
        dataframe = dataframe[dataframe['Datetime'].notna()]
        dataframe.index = np.arange(len(dataframe))

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
    p = None
    for name in dataframe.columns:
        if re.search('pressure', name, re.IGNORECASE):
            p = dataframe[name]
            if adjust_for_atm == True:
                # standard atmospheric pressure = 101.325 kPa = 10.1325 dbar
                p = p - 10.1325
    if p is None:
        return dataframe
    # latitude converted from degrees to radians (UNESCO 1983 formula)
    x = np.square(np.sin(latitude/57.29578))
    g = 9.780318 * (1+(5.2788e-3 + 2.36e-5 * x)* x) + 1.092e-6 * p
    depth = ((((-1.82e-15 * p + 2.279e-10) * p-2.2512e-5) * p + 9.72659)*p) / g
    dataframe['Depth (m)'] = round(depth, 2)
    return dataframe

def clean_below_zero(data, settings):
    # Handles non-physical values <= 0 before the quality tests:
    # - PAR: irradiance is physically >= 0; small negatives at night are sensor
    #   dark-offset noise, so negatives are clamped to 0 (kept), not discarded.
    # - Optical sensors (chlorophyll, turbidity, CDOM/organic matter): the true
    #   value is physically >= 0, so a small negative reading is sensor noise
    #   around zero -> clamped to 0 (kept as valid "~0"); a gross negative is a
    #   sensor error -> NaN. The boundary is 5% of the variable's environmental
    #   span (tune via env_min/env_max if needed).
    # - All other variables: <= 0 -> NaN (sensor failure for marine data).
    exceptions = ['Datetime', 'Sample number', 'Pitch[Deg]', 'Roll[Deg]', 'Timer[s]', 'Site']
    optical = {
        'chlorophyll': ('env_min_chl', 'env_max_chl'),
        'turbidity': ('env_min_tur', 'env_max_tur'),
        'organic matter': ('env_min_org', 'env_max_org'),
    }
    for name in data.columns:
        if name in exceptions:
            continue
        if re.search('par', name, re.IGNORECASE):
            data.loc[data[name] < 0, name] = 0.0
            continue
        opt_key = next((k for k in optical if re.search(k, name, re.IGNORECASE)), None)
        if opt_key is not None:
            lo_key, hi_key = optical[opt_key]
            span = settings.get(hi_key, 0) - settings.get(lo_key, 0)
            tol = 0.05 * span if span > 0 else 0
            data.loc[(data[name] < 0) & (data[name] >= -tol), name] = 0.0
            data.loc[data[name] < -tol, name] = np.nan
        else:
            data.loc[data[name] <= 0, name] = np.nan
    return data

# Function for preparing output files

# maps each test's parameter key (from the test sequence) to the variable
# bucket(s) it affects; 'dens' (density inversion) implicates temperature and salinity
FLAG_BUCKET_MAP = {
    'T': ['T'], 'S': ['S'], 'C': ['C'], 'P': ['P'], 'pH': ['pH'],
    'chl': ['chl'], 'O2': ['O2'], 'org': ['org'], 'tur': ['tur'],
    'dens': ['T', 'S'],
}

def handle_output_file (input_df, flags, flag_layout, remove_suspect, remove_bad):
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
    # Classify each row per variable using the worst flag across that variable's
    # tests (bad > suspect > missing). flag_layout[pos] tells which variable each
    # flag character belongs to, so positions are never hardcoded here.
    var_keys = ['T', 'S', 'C', 'P', 'pH', 'chl', 'O2', 'org', 'tur']
    bdata = {k: [] for k in var_keys}
    sdata = {k: [] for k in var_keys}
    mdata = {k: [] for k in var_keys}
    for i in range(len(flags)):
        flagstr = flags[i]
        per_var = {k: '' for k in var_keys}
        for pos, pkey in enumerate(flag_layout):
            if pos < len(flagstr):
                for bucket in FLAG_BUCKET_MAP.get(pkey, []):
                    per_var[bucket] += flagstr[pos]
        for k in var_keys:
            chars = per_var[k]
            if '4' in chars:
                bdata[k].append(i)
            elif '3' in chars:
                sdata[k].append(i)
            elif '9' in chars:
                mdata[k].append(i)

    T_bdata, S_bdata, C_bdata, P_bdata = (np.asarray(bdata['T']), np.asarray(bdata['S']), np.asarray(bdata['C']), np.asarray(bdata['P']))
    pH_bdata, chl_bdata, O2_bdata, org_bdata, tur_bdata = (np.asarray(bdata['pH']), np.asarray(bdata['chl']), np.asarray(bdata['O2']), np.asarray(bdata['org']), np.asarray(bdata['tur']))
    T_sdata, S_sdata, C_sdata, P_sdata = (np.asarray(sdata['T']), np.asarray(sdata['S']), np.asarray(sdata['C']), np.asarray(sdata['P']))
    pH_sdata, chl_sdata, O2_sdata, org_sdata, tur_sdata = (np.asarray(sdata['pH']), np.asarray(sdata['chl']), np.asarray(sdata['O2']), np.asarray(sdata['org']), np.asarray(sdata['tur']))
    T_mdata, S_mdata, C_mdata, P_mdata = (np.asarray(mdata['T']), np.asarray(mdata['S']), np.asarray(mdata['C']), np.asarray(mdata['P']))
    pH_mdata, chl_mdata, O2_mdata, org_mdata, tur_mdata = (np.asarray(mdata['pH']), np.asarray(mdata['chl']), np.asarray(mdata['O2']), np.asarray(mdata['org']), np.asarray(mdata['tur']))
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
            # exact match: a case-insensitive 'pH' search would also hit 'Chlorophyll'
            if name == 'pH':
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
            if name == 'pH':
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
                        'Conductivity (mS/cm)': 5, 'Pressure (dbar)': 6, 'Density (kg/m3)': 7, 'CO2 Level (ppm)': 8,
                        'O2 level (uM)': 9, 'O2 content (mg/L)': 10, 'PAR (umol/m2/s)': 11, 'Turbidity (FTU)': 12, 'TSS (mg/L)': 13, 
                        'Chlorophyll (ug/L)': 14, 'pH': 15, 'Dissolved organic matter (ppb)': 16, 'Luminosity (lux)': 17,
                        'Soundspeed (m/s)': 18, 'Expedition': 19, 'Site': 20, 'Longitude': 21, 'Latitude': 22,
                        'Battery voltage (V)': 23, 'Flag': 24}
    else:
        raise ValueError("Unsupported data_type '%s' in order_var (only 'tscp' is supported)" % data_type)

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
                n = int(re.search(r'\d{1,3}', var).group())
                if n > n_cel:
                    qualified_data = qualified_data.drop(columns=[var])
            else:
                if re.search('speed', var, re.IGNORECASE) or re.search('direction', var, re.IGNORECASE):
                    pass
                else:
                    qualified_data = qualified_data.drop(columns=[var])
    return qualified_data

def tscp_stats_table (qualified_data):
    # builds the statistics table with whichever of the main variables
    # are present and hold at least one valid value
    expected = ['Temperature (degC)', 'Salinity (PSU)', 'Pressure (dbar)']
    present = [var for var in expected
               if var in qualified_data.columns and not qualified_data[var].isna().all()]
    stat = pd.DataFrame({'Variable': present,
                          'Max': [np.nanmax(qualified_data[var]) for var in present],
                          'Min': [np.nanmin(qualified_data[var]) for var in present],
                          'Mean': [np.nanmean(qualified_data[var]) for var in present],
                          'Median': [np.nanmedian(qualified_data[var]) for var in present],
                          'std': [np.nanstd(qualified_data[var]) for var in present]})

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

def trim_by_depth(data):
    # Cria cópia do dataframe
    trimmed_data = data.copy()
    
    # Define x e y
    y = data['Depth (m)']
    x = data['Depth (m)'].index

    # Cria o plot
    fig, ax = plt.subplots()
    ax.plot(x, y, linestyle='-', marker='x', markeredgecolor='r', markerfacecolor='r', picker=5)
    ax.set_title('Select points within rectangle to remove - Depth (m)\nPress Enter when you are done')
    ax.set_ylabel('Depth (m)')
    ax.set_xlabel('Sample number')

    # Armazena índices removidos
    removed_indices = set()
    selection_complete = False

    # Função para remover dados selecionados
    def on_select(eclick, erelease):
        nonlocal trimmed_data
        x0, y0 = eclick.xdata, eclick.ydata
        x1, y1 = erelease.xdata, erelease.ydata  

        mask = (x > min(x0, x1)) & (x < max(x0, x1)) & \
               (y > min(y0, y1)) & (y < max(y0, y1))

        current_indices = np.arange(len(y))[mask]
        removed_indices.update(current_indices)
        # errors='ignore' prevents a crash when the same points are selected twice
        trimmed_data.drop(index=current_indices, inplace=True, errors='ignore')

        # Atualiza o plot
        remaining_mask = np.isin(np.arange(len(y)), list(removed_indices), invert=True)
        new_x = x[remaining_mask]
        new_y = y[remaining_mask]
        
        ax.clear()
        ax.plot(new_x, new_y, linestyle='-', marker='x', markeredgecolor='r', markerfacecolor='r', picker=5)
        ax.set_title('Select points within rectangle to remove - Depth (m)\nPress Enter when you are done')
        ax.set_ylabel('Depth (m)')
        ax.set_xlabel('Sample number')
        fig.canvas.draw()

    def on_key_press(event):
        nonlocal selection_complete
        if event.key == 'enter':
            selection_complete = True
            plt.close(fig)

    # Configura o seletor
    selector = RectangleSelector(ax, on_select,  # manter referencia viva (widget e coletado pelo GC se nao for guardado)
                               useblit=True,
                               button=[1],
                               minspanx=5, minspany=5,
                               spancoords='pixels',
                               interactive=True)

    # Conecta os eventos
    fig.canvas.mpl_connect('key_press_event', on_key_press)

    # Configura os limites
    ax.set_xlim(np.nanmin(x) - 0.1, np.nanmax(x) + 0.1)
    ax.set_ylim(np.nanmin(y) - 0.1, np.nanmax(y) + 0.1)

    # Mostra o gráfico
    plt.show(block=True)
    
    # Reindexa antes de retornar
    trimmed_data.index = np.arange(len(trimmed_data))
    
    return trimmed_data

def trim_selected_variable(data, name):
    # Faz uma cópia explícita da coluna para evitar o alerta de SettingWithCopyWarning
    y = data[name].copy()
    x = data.index  # Usar o índice diretamente sem copiar

    # Criação do gráfico
    fig, ax = plt.subplots()
    ax.plot(x, y, linestyle='-', marker='x', markeredgecolor='r', markerfacecolor='r', picker=5)
    ax.set_title(f'Select points within rectangle to remove - {name}\nPress Enter when you are done')
    ax.set_ylabel(name)
    ax.set_xlabel('Sample number')

    # Variável para controle do loop
    selection_complete = False

    # Função para remover pontos selecionados
    def on_select(eclick, erelease):
        nonlocal y
        x0, y0 = eclick.xdata, eclick.ydata
        x1, y1 = erelease.xdata, erelease.ydata
        mask = (x > min(x0, x1)) & (x < max(x0, x1)) & \
               (y > min(y0, y1)) & (y < max(y0, y1))
        y[mask] = np.nan  # Substitui pontos selecionados por NaN

        ax.clear()
        ax.plot(x, y, linestyle='-', marker='x', markeredgecolor='r', markerfacecolor='r', picker=5)
        ax.set_title(f'Select points within rectangle to remove - {name}\nPress Enter when you are done')
        ax.set_ylabel(name)
        ax.set_xlabel('Sample number')
        fig.canvas.draw()

    def on_key_press(event):
        nonlocal selection_complete
        if event.key == 'enter':
            selection_complete = True
            plt.close(fig)

    # Configuração dos eventos
    selector = RectangleSelector(ax, on_select,  # manter referencia viva (widget e coletado pelo GC se nao for guardado)
                               useblit=True,
                               button=[1],
                               minspanx=5, minspany=5,
                               spancoords='pixels',
                               interactive=True)

    fig.canvas.mpl_connect('key_press_event', on_key_press)

    # Configuração dos limites
    ax.set_xlim(np.nanmin(x)-0.1, np.nanmax(x)+0.1)
    ax.set_ylim(np.nanmin(y)-0.1, np.nanmax(y)+0.1)

    # Exibe o gráfico e aguarda
    plt.show(block=True)
    
    # Atualiza os dados após fechar a janela
    data[name] = y
    return data

def join_files_to_database(path, inputFilesFormat):
    folder_names = next(walk(path), (None, None, []))[1]
    folder_names = [item for item in folder_names if '__pycache__' not in item]
    dic = {}
    for folder in folder_names:
        subfolder_names = next(walk(path + '/' + folder), (None, None, []))[1]
        subfolder_names = [item for item in subfolder_names if '__pycache__' not in item]
        for ff in subfolder_names:
            if not re.search('data', ff, re.IGNORECASE):
                continue
            f = ff
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

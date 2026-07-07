import os
import re
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.widgets import RectangleSelector

# Software version: single source of truth, shown in window titles,
# 'About' dialogs and in the 'QCS version' column of qualified files.
# Update ONLY here when releasing a new version.
QCS_VERSION = 'v4.0'

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

# 1 lumen/ft2 = 10.7639 lux (HOBO Pendant exported in US units)
LUMEN_FT2_TO_LUX = 10.7639

# HOBO logger event column patterns (pt/en)
_HOBO_EVENT_PATTERN = (r'acoplador|coupler|anfitri|host|parado|stopped|'
                       r'fim do ficheiro|end of file|bateria|battery')
_HOBO_DETACH_PATTERN = r'acoplador desligado|coupler detached'
_HOBO_END_PATTERN = (r'acoplador ligado|coupler attached|anfitri|host|'
                     r'parado|stopped|fim do ficheiro|end of file')


def _hobo_error(file_name, message):
    # every reader error is self-localizing: "HOBO reader (file): what was missing"
    return ValueError('HOBO reader (%s): %s' % (file_name, message))


def read_hobo(INPUT, tsSettings):
    """Reads HOBOware exports (.xlsx/.csv) from Pendant Temp/Light sensors.

    Tolerates: headers in Portuguese or English, a title line before the header,
    variable sampling frequency, light in Lux or lum/ft2 (converted to lux).
    Removes logger event-only rows, trims out-of-water readings at the edges
    (window between coupler events + temperature-jump heuristic) and
    returns (dataframe, info): dataframe with Datetime / Temperature (degC) /
    Luminosity (lux); info['messages'] documents everything that was done/discarded.
    """
    file_name = INPUT['file_name']
    file_path = os.path.join(INPUT['raw_data_path'], file_name)
    info = {'messages': []}
    say = info['messages'].append

    # ---------- raw read with header line detection ----------
    def header_line(cells):
        joined = ' '.join(str(c) for c in cells).lower()
        return (re.search(r'data\s*hora|date\s*time', joined) is not None
                and re.search(r'temp', joined) is not None)

    if file_name.lower().endswith('.xlsx'):
        sample = pd.read_excel(file_path, header=None, nrows=20)
        header_row = next((i for i, row in sample.iterrows() if header_line(row.tolist())), None)
        if header_row is None:
            raise _hobo_error(file_name, "could not find the header row: expected a line "
                              "containing 'Data Hora'/'Date Time' AND 'Temp' in the first 20 rows. "
                              "Is this a HOBOware export?")
        df = pd.read_excel(file_path, skiprows=header_row, header=0)
    elif file_name.lower().endswith('.csv'):
        raw_lines, used_encoding = None, None
        for enc in ('utf-8-sig', 'cp1252', 'latin-1'):
            try:
                with open(file_path, 'r', encoding=enc) as f:
                    raw_lines = f.readlines()
                used_encoding = enc
                break
            except UnicodeDecodeError:
                continue
        if raw_lines is None:
            raise _hobo_error(file_name, 'could not decode the file with utf-8, cp1252 or latin-1.')
        header_row = next((i for i, line in enumerate(raw_lines[:20])
                           if header_line([line])), None)
        if header_row is None:
            raise _hobo_error(file_name, "could not find the header row: expected a line "
                              "containing 'Data Hora'/'Date Time' AND 'Temp' in the first 20 lines. "
                              "Is this a HOBOware export?")
        delimiter = ';' if raw_lines[header_row].count(';') > raw_lines[header_row].count(',') else ','
        df = pd.read_csv(file_path, skiprows=header_row, header=0,
                         sep=delimiter, encoding=used_encoding, engine='python')
        say('MESSAGE: csv read with encoding %s and delimiter %r' % (used_encoding, delimiter))
    else:
        raise _hobo_error(file_name, 'unsupported format (use the .xlsx or .csv HOBOware export).')

    # ---------- column identification ----------
    time_col = temp_col = light_col = None
    event_cols = []
    for c in df.columns:
        low = str(c).lower()
        if time_col is None and re.search(r'data\s*hora|date\s*time', low):
            time_col = c
        elif temp_col is None and re.search(r'temp', low):
            temp_col = c
        elif light_col is None and re.search(r'intensidade|intensity|lux|lum', low):
            light_col = c
        elif re.search(_HOBO_EVENT_PATTERN, low):
            event_cols.append(c)
    found = 'columns found: %s' % ', '.join(repr(str(c)) for c in df.columns)
    if time_col is None:
        raise _hobo_error(file_name, 'no time column found (expected "Data Hora"/"Date Time"). ' + found)
    if temp_col is None:
        raise _hobo_error(file_name, 'no temperature column found (expected "Temp"). ' + found)
    if light_col is None:
        raise _hobo_error(file_name, 'no light column found (expected "Intensidade"/"Intensity"). ' + found)

    # light unit from the channel label
    light_label = str(light_col).lower()
    if re.search(r'lum/?\s*ft|lumen', light_label):
        light_factor = LUMEN_FT2_TO_LUX
        say('MESSAGE: light channel is in lum/ft2; converted to lux (x%.4f).' % LUMEN_FT2_TO_LUX)
    elif re.search(r'lux', light_label):
        light_factor = 1.0
    else:
        raise _hobo_error(file_name, 'light column %r has no recognizable unit '
                          '(expected Lux or lum/ft2 in the header).' % str(light_col))

    gmt = re.search(r'GMT\s*([+-]\d{1,2}):?(\d{2})?', str(time_col))
    if gmt:
        say('MESSAGE: timestamps exported as GMT%s (from the header). The "Correct GMT-3" '
            'option would subtract 3 MORE hours - only use it if the export is in GMT+00.' % gmt.group(1))

    # ---------- types ----------
    df[time_col] = pd.to_datetime(df[time_col], errors='coerce', dayfirst=True)
    n_bad_ts = int(df[time_col].isna().sum())
    if n_bad_ts:
        say('WARNING: %d row(s) without a valid timestamp discarded.' % n_bad_ts)
        df = df[df[time_col].notna()]
    if df.empty:
        raise _hobo_error(file_name, 'no rows with valid timestamps after reading.')
    df[temp_col] = pd.to_numeric(df[temp_col], errors='coerce')
    df[light_col] = pd.to_numeric(df[light_col], errors='coerce') * light_factor

    # ---------- deployment window from the logger events ----------
    if event_cols:
        ev_mask = df[event_cols].notna().any(axis=1)
        detach_cols = [c for c in event_cols if re.search(_HOBO_DETACH_PATTERN, str(c).lower())]
        end_cols = [c for c in event_cols if re.search(_HOBO_END_PATTERN, str(c).lower())]
        start_t = df.loc[df[detach_cols].notna().any(axis=1), time_col].min() if detach_cols else pd.NaT
        end_t = pd.NaT
        if end_cols:
            end_times = df.loc[df[end_cols].notna().any(axis=1), time_col]
            if pd.notna(start_t):
                end_times = end_times[end_times > start_t]
            end_t = end_times.min() if not end_times.empty else pd.NaT
        before = len(df)
        if pd.notna(start_t):
            df = df[df[time_col] >= start_t]
        if pd.notna(end_t):
            df = df[df[time_col] < end_t]
        n_window = before - len(df)
        if n_window:
            say('MESSAGE: %d sample(s) outside the logger deployment window '
                '(%s to %s) discarded.' % (n_window, start_t, end_t))
        # event-only rows (no measurement) are removed
        ev_mask = df[event_cols].notna().any(axis=1) & df[temp_col].isna()
        n_ev = int(ev_mask.sum())
        if n_ev:
            say('MESSAGE: %d logger-event row(s) (no measurement) discarded.' % n_ev)
        df = df[~ev_mask]
    else:
        say('WARNING: no logger event columns found - deployment window not applied; '
            'check the file edges for out-of-water readings.')

    if df.empty:
        raise _hobo_error(file_name, 'no measurement rows left after removing logger events. '
                          'Check the deployment window events in the file.')

    df = df[[time_col, temp_col, light_col]]
    df.columns = ['Datetime', 'Temperature (degC)', 'Luminosity (lux)']
    if not df['Datetime'].is_monotonic_increasing:
        say('WARNING: timestamps were not in chronological order; sorted by time.')
        df = df.sort_values('Datetime')
    df.index = np.arange(len(df))

    # ---------- trim of out-of-water readings at the edges (temperature jump) ----------
    tol = float(tsSettings.get('hobo_edge_temp_tol', 1.5))
    interval = df['Datetime'].diff().median()
    n_day = max(int(pd.Timedelta(days=1) / interval), 4) if pd.notna(interval) and interval > pd.Timedelta(0) else 12
    temp = df['Temperature (degC)']

    def edge_trim_count(series, reference):
        count = 0
        for value in series:
            if pd.notna(value) and abs(value - reference) > tol:
                count += 1
            else:
                break
        return count

    n_head = edge_trim_count(temp.iloc[:n_day], temp.iloc[:5 * n_day].median())
    n_tail = edge_trim_count(temp.iloc[::-1].iloc[:n_day], temp.iloc[-5 * n_day:].median())
    if n_head + n_tail > 0.1 * len(df):
        say('WARNING: edge trim would remove >10%% of the series (%d+%d samples) - '
            'NOT applied; review the temperature plot manually.' % (n_head, n_tail))
    else:
        if n_head:
            say('MESSAGE: %d leading sample(s) trimmed - temperature deviates more than '
                '%.1f degC from the deployment start (out-of-water reading).' % (n_head, tol))
        if n_tail:
            say('MESSAGE: %d trailing sample(s) trimmed - temperature deviates more than '
                '%.1f degC from the deployment end (out-of-water reading).' % (n_tail, tol))
        if n_head or n_tail:
            df = df.iloc[n_head: len(df) - n_tail]
            df.index = np.arange(len(df))

    say('MESSAGE: HOBO file read: %d samples, %s to %s, median interval %s.'
        % (len(df), df['Datetime'].iloc[0], df['Datetime'].iloc[-1], interval))
    return df, info
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
    #
    # Returns (data, report): report[column] = {'clamped': n, 'discarded': n},
    # only for columns where something was changed, so the caller can log it.
    exceptions = ['Datetime', 'Sample number', 'Pitch[Deg]', 'Roll[Deg]', 'Timer[s]', 'Site']
    optical = {
        'chlorophyll': ('env_min_chl', 'env_max_chl'),
        'turbidity': ('env_min_tur', 'env_max_tur'),
        'organic matter': ('env_min_org', 'env_max_org'),
    }
    report = {}
    for name in data.columns:
        if name in exceptions:
            continue
        clamped, discarded = 0, 0
        if re.search('par|luminosity|lux', name, re.IGNORECASE):
            # light/PAR: zero at night is a VALID value; negatives are offset noise
            clamped = int((data[name] < 0).sum())
            data.loc[data[name] < 0, name] = 0.0
        else:
            opt_key = next((k for k in optical if re.search(k, name, re.IGNORECASE)), None)
            if opt_key is not None:
                lo_key, hi_key = optical[opt_key]
                span = settings.get(hi_key, 0) - settings.get(lo_key, 0)
                tol = 0.05 * span if span > 0 else 0
                clamped = int(((data[name] < 0) & (data[name] >= -tol)).sum())
                discarded = int((data[name] < -tol).sum())
                data.loc[(data[name] < 0) & (data[name] >= -tol), name] = 0.0
                data.loc[data[name] < -tol, name] = np.nan
            else:
                discarded = int((data[name] <= 0).sum())
                data.loc[data[name] <= 0, name] = np.nan
        if clamped or discarded:
            report[name] = {'clamped': clamped, 'discarded': discarded}
    return data, report

# Function for preparing output files

# maps each test's parameter key (from the test sequence) to the variable
# bucket(s) it affects; 'dens' (density inversion) implicates temperature and salinity
FLAG_BUCKET_MAP = {
    'T': ['T'], 'S': ['S'], 'C': ['C'], 'P': ['P'], 'pH': ['pH'],
    'chl': ['chl'], 'O2': ['O2'], 'org': ['org'], 'tur': ['tur'],
    'dens': ['T', 'S'],
    'lux': ['lux'],  # HOBO light (fouling test)
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
    # extra buckets present in the layout (e.g. 'lux' in HOBO files) get their
    # own Flag_ column without changing the format of files that don't use them
    for pkey in flag_layout:
        for bucket in FLAG_BUCKET_MAP.get(pkey, []):
            if bucket not in var_keys:
                var_keys.append(bucket)
    bdata = {k: [] for k in var_keys}
    sdata = {k: [] for k in var_keys}
    mdata = {k: [] for k in var_keys}
    agg_flags = {k: [] for k in var_keys}  # rollup flag per row/variable (Flag_T etc.)

    def worst_flag(chars):
        # aggregation priority: bad > suspect > missing > good > not-evaluated > off
        for code in ('4', '3', '9', '1', '2'):
            if code in chars:
                return int(code)
        return 5

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
            agg_flags[k].append(worst_flag(chars))

    # per-variable rollup columns: downstream users read Flag_T etc. directly,
    # without having to decode the positional flag string
    for k in var_keys:
        output_df['Flag_' + k] = agg_flags[k]

    T_bdata, S_bdata, C_bdata, P_bdata = (np.asarray(bdata['T']), np.asarray(bdata['S']), np.asarray(bdata['C']), np.asarray(bdata['P']))
    pH_bdata, chl_bdata, O2_bdata, org_bdata, tur_bdata = (np.asarray(bdata['pH']), np.asarray(bdata['chl']), np.asarray(bdata['O2']), np.asarray(bdata['org']), np.asarray(bdata['tur']))
    T_sdata, S_sdata, C_sdata, P_sdata = (np.asarray(sdata['T']), np.asarray(sdata['S']), np.asarray(sdata['C']), np.asarray(sdata['P']))
    pH_sdata, chl_sdata, O2_sdata, org_sdata, tur_sdata = (np.asarray(sdata['pH']), np.asarray(sdata['chl']), np.asarray(sdata['O2']), np.asarray(sdata['org']), np.asarray(sdata['tur']))
    T_mdata, S_mdata, C_mdata, P_mdata = (np.asarray(mdata['T']), np.asarray(mdata['S']), np.asarray(mdata['C']), np.asarray(mdata['P']))
    pH_mdata, chl_mdata, O2_mdata, org_mdata, tur_mdata = (np.asarray(mdata['pH']), np.asarray(mdata['chl']), np.asarray(mdata['O2']), np.asarray(mdata['org']), np.asarray(mdata['tur']))
    # changing bad or suspect data to NaN according from operators input
    if remove_bad == True:
        for name in output_df.columns:
            if str(name).startswith('Flag'):
                continue  # flag columns are never erased (Flag_O2/Flag_lux match the patterns)
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
            if re.search('luminosity|lux', name, re.IGNORECASE) and 'lux' in bdata:
                output_df.loc[bdata['lux'], name] = np.nan
    if remove_suspect == True:
        for name in output_df.columns:
            if str(name).startswith('Flag'):
                continue  # flag columns are never erased
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
            if re.search('luminosity|lux', name, re.IGNORECASE) and 'lux' in sdata:
                output_df.loc[sdata['lux'], name] = np.nan
    return output_df, input_df, T_bdata, S_bdata, C_bdata, P_bdata, pH_bdata, chl_bdata, O2_bdata, org_bdata, tur_bdata, T_sdata, S_sdata, C_sdata, P_sdata, pH_sdata, chl_sdata, O2_sdata, org_sdata, tur_sdata, T_mdata, S_mdata, C_mdata, P_mdata, pH_mdata, chl_mdata, O2_mdata, org_mdata, tur_mdata

def order_var (qualified_data, n_cel, data_type):
    if data_type == 'tscp':
        # 'Site' right after 'Datetime' (identification comes before the measurements).
        # 'Battery voltage (V)' is kept as a placeholder (currently empty; reserved
        # for when it is extracted from the raw data). 'Expedition' was removed.
        var_priority = {'Sample number': 0, 'Datetime': 1, 'Site': 2, 'Depth (m)': 3, 'Temperature (degC)': 4,
                        'Salinity (PSU)': 5, 'Conductivity (mS/cm)': 6, 'Pressure (dbar)': 7, 'Density (kg/m3)': 8,
                        'CO2 Level (ppm)': 9, 'O2 level (uM)': 10, 'O2 content (mg/L)': 11, 'PAR (umol/m2/s)': 12,
                        'Turbidity (FTU)': 13, 'TSS (mg/L)': 14, 'Chlorophyll (ug/L)': 15, 'pH': 16,
                        'Dissolved organic matter (ppb)': 17, 'Luminosity (lux)': 18, 'Soundspeed (m/s)': 19,
                        'Battery voltage (V)': 20, 'Flag': 21,
                        'Flag_T': 22, 'Flag_S': 23, 'Flag_C': 24, 'Flag_P': 25, 'Flag_pH': 26,
                        'Flag_chl': 27, 'Flag_O2': 28, 'Flag_org': 29, 'Flag_tur': 30,
                        'Flag_lux': 31, 'QCS version': 32}
    elif data_type == 'hobo':
        # HOBO Pendant: only the measured variables (temperature in Celsius and
        # light in lux), with the same metadata block as the TSCP standard. The
        # other TSCP variables do not apply and do not appear (non-stackable sheets).
        # 'Site' right after 'Datetime'; 'Battery voltage (V)' kept as a
        # placeholder (currently empty); 'Expedition' removed.
        # 'Temperature spread (degC)' is a FIXED column: the between-replicate spread
        # when N>1 redundant HOBOs are combined; empty for single files.
        var_priority = {'Sample number': 0, 'Datetime': 1, 'Site': 2,
                        'Temperature (degC)': 3, 'Temperature spread (degC)': 4,
                        'Luminosity (lux)': 5, 'Battery voltage (V)': 6, 'Flag': 7,
                        'Flag_T': 8, 'Flag_lux': 9, 'QCS version': 10}
    else:
        raise ValueError("Unsupported data_type '%s' in order_var (use 'tscp' or 'hobo')" % data_type)

    # Latitude/Longitude are never part of the qualified output (kept out on
    # purpose so every file has the same column layout); drop them if present.
    for coord in ('Latitude', 'Longitude'):
        if coord in qualified_data.columns:
            qualified_data = qualified_data.drop(columns=[coord])

    order = {}
    for var in var_priority.keys():
        if var in qualified_data.columns:
            order[var] = var_priority[var]
        else:
            # Flag_ columns only exist when the corresponding test ran
            # (e.g. Flag_lux only in HOBO files) - do not create them empty
            if re.search('correlation', var, re.IGNORECASE) or var.startswith('Flag_'):
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

def save_excel_autofit(dataframe, path, index=False):
    """Writes a DataFrame to an .xlsx with each column widened to fit its content
    (header and values), so the sheet is readable without resizing by hand.
    Used for every qualified spreadsheet the app writes."""
    from openpyxl.utils import get_column_letter
    with pd.ExcelWriter(path, engine='openpyxl') as writer:
        dataframe.to_excel(writer, index=index)
        ws = writer.sheets[next(iter(writer.sheets))]
        offset = 1 if index else 0  # column A is the index when index=True
        for i, col in enumerate(dataframe.columns):
            value_len = int(dataframe[col].astype(str).map(len).max()) if len(dataframe) else 0
            width = min(max(len(str(col)), value_len) + 2, 60)  # +padding, capped so it stays sane
            ws.column_dimensions[get_column_letter(i + 1 + offset)].width = width

def tscp_stats_table (qualified_data):
    # builds the statistics table with whichever of the main variables
    # are present and hold at least one valid value
    expected = ['Temperature (degC)', 'Salinity (PSU)', 'Conductivity (mS/cm)',
                'Pressure (dbar)', 'Depth (m)', 'Density (kg/m3)', 'pH',
                'O2 level (uM)', 'O2 content (mg/L)', 'Chlorophyll (ug/L)',
                'Turbidity (FTU)', 'Dissolved organic matter (ppb)',
                'PAR (umol/m2/s)', 'Soundspeed (m/s)', 'Luminosity (lux)']
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

def _show_and_wait(fig, tk_root):
    # Shows the interactive figure without freezing the interface. plt.show(block=True)
    # inside a Tkinter callback creates a nested event loop that hangs the main
    # window (same problem as Select Profile Data, fixed in v3.2.1); with tk_root,
    # it waits in Tk's own loop until the figure is closed.
    if tk_root is None:
        plt.show(block=True)
        return
    import tkinter as tk
    done = tk.BooleanVar(tk_root, value=False)
    fig.canvas.mpl_connect('close_event', lambda event: done.set(True))
    fig.show()
    tk_root.wait_variable(done)


def trim_by_depth(data, tk_root=None):
    # Create a copy of the dataframe
    trimmed_data = data.copy()

    # Define x and y
    y = data['Depth (m)']
    x = data['Depth (m)'].index

    # Create the plot
    fig, ax = plt.subplots()
    ax.plot(x, y, linestyle='-', marker='x', markeredgecolor='r', markerfacecolor='r', picker=5)
    ax.set_title('Select points within rectangle to remove - Depth (m)\nPress Enter when you are done')
    ax.set_ylabel('Depth (m)')
    ax.set_xlabel('Sample number')

    # Stores removed indices
    removed_indices = set()
    selection_complete = False

    # Function to remove selected data
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

        # Update the plot
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

    # Configure the selector
    _selector = RectangleSelector(ax, on_select,  # keep the reference alive (the widget is collected by the GC if not stored)
                               useblit=True,
                               button=[1],
                               minspanx=5, minspany=5,
                               spancoords='pixels',
                               interactive=True)

    # Connect the events
    fig.canvas.mpl_connect('key_press_event', on_key_press)

    # Configure the limits
    ax.set_xlim(np.nanmin(x) - 0.1, np.nanmax(x) + 0.1)
    ax.set_ylim(np.nanmin(y) - 0.1, np.nanmax(y) + 0.1)

    # Show the plot and wait without freezing the interface
    _show_and_wait(fig, tk_root)

    # Reindex before returning
    trimmed_data.index = np.arange(len(trimmed_data))

    return trimmed_data

def trim_selected_variable(data, name, tk_root=None):
    # Make an explicit copy of the column to avoid the SettingWithCopyWarning alert
    y = data[name].copy()
    x = data.index  # Use the index directly without copying

    # Plot creation
    fig, ax = plt.subplots()
    ax.plot(x, y, linestyle='-', marker='x', markeredgecolor='r', markerfacecolor='r', picker=5)
    ax.set_title(f'Select points within rectangle to remove - {name}\nPress Enter when you are done')
    ax.set_ylabel(name)
    ax.set_xlabel('Sample number')

    # Variable for loop control
    selection_complete = False

    # Function to remove selected points
    def on_select(eclick, erelease):
        nonlocal y
        x0, y0 = eclick.xdata, eclick.ydata
        x1, y1 = erelease.xdata, erelease.ydata
        mask = (x > min(x0, x1)) & (x < max(x0, x1)) & \
               (y > min(y0, y1)) & (y < max(y0, y1))
        y[mask] = np.nan  # Replace selected points with NaN

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

    # Event configuration
    _selector = RectangleSelector(ax, on_select,  # keep the reference alive (the widget is collected by the GC if not stored)
                               useblit=True,
                               button=[1],
                               minspanx=5, minspany=5,
                               spancoords='pixels',
                               interactive=True)

    fig.canvas.mpl_connect('key_press_event', on_key_press)

    # Limit configuration
    ax.set_xlim(np.nanmin(x)-0.1, np.nanmax(x)+0.1)
    ax.set_ylim(np.nanmin(y)-0.1, np.nanmax(y)+0.1)

    # Show the plot and wait without freezing the interface
    _show_and_wait(fig, tk_root)

    # Update the data after closing the window
    data[name] = y
    return data

# QCS output subfolders where each instrument's qualified spreadsheets live
# (the tscp name is the same since the pre-v4 versions)
QUALIFIED_SUBFOLDERS = {
    'tscp': ('QCS qualified tscp data',),
    'hobo': ('QCS qualified hobo data',),
}


def detect_qualified_layout(df):
    """'hobo' = only temperature+light (has Luminosity, no Salinity);
    any other qualified spreadsheet is 'tscp' (Seaguard)."""
    cols = set(str(c) for c in df.columns)
    if 'Luminosity (lux)' in cols and 'Salinity (PSU)' not in cols:
        return 'hobo'
    return 'tscp'


def build_database(instrument, file_list=None, input_path=None):
    """Single unification engine for qualified spreadsheets (Seaguard and HOBO).

    Input (one of the two):
    - file_list: qualified files chosen by hand (multi-selection); or
    - input_path: parent folder swept recursively looking for the QCS output
      subfolders ('QCS qualified tscp data' / 'QCS qualified hobo data').

    Rules (v4.0, replaces join_files_to_database):
    - ignores the report files (name starting with 'QCS_');
    - reads .csv (header on line 0 - the old header=1 corrupted csvs) and .xlsx;
    - validates each file: needs Datetime+Site and the layout must match
      the instrument (HOBO and Seaguard are NEVER stackable);
    - adds the 'Source file' column (provenance of each row);
    - sorts by Site+Datetime; removes exact duplicates (keeping the first,
      with a warning) and reports rows with the same Site+Datetime and different values.

    Returns (database, messages). Problems raise a ValueError with a
    self-localizing message ('build_database: ...').
    """
    expected_layout = 'hobo' if str(instrument).strip().upper() == 'HOBO' else 'tscp'
    messages = []

    if file_list:
        files = [f.strip() for f in file_list if f and f.strip()]
    elif input_path:
        target_subfolders = QUALIFIED_SUBFOLDERS[expected_layout]
        files = []
        for root, _dirs, names in os.walk(input_path):
            if os.path.basename(root) in target_subfolders:
                for name in sorted(names):
                    if name.lower().endswith(('.csv', '.xlsx')) and not name.startswith('QCS_'):
                        files.append(os.path.join(root, name))
        if not files:
            raise ValueError("build_database: no qualified %s files found under:\n%s\n"
                             "(searched inside '%s' subfolders for .csv/.xlsx not named 'QCS_*')."
                             % (instrument, input_path, "'/'".join(target_subfolders)))
    else:
        raise ValueError('build_database: provide file_list or input_path.')

    frames = []
    for file_path in files:
        base = os.path.basename(file_path)
        if base.startswith('QCS_'):
            messages.append('MESSAGE: report file skipped: %s' % base)
            continue
        try:
            if file_path.lower().endswith('.xlsx'):
                df = pd.read_excel(file_path, header=0)
            else:
                df = pd.read_csv(file_path, header=0)
        except Exception as e:
            raise ValueError('build_database: could not read %s:\n%s' % (file_path, e)) from e
        missing = [c for c in ('Datetime', 'Site') if c not in df.columns]
        if missing:
            raise ValueError("build_database: %s does not look like a QCS qualified file "
                             "(missing column(s): %s).\nColumns found: %s"
                             % (base, ', '.join(missing), ', '.join(str(c) for c in df.columns[:12])))
        layout = detect_qualified_layout(df)
        if layout != expected_layout:
            raise ValueError("build_database: %s looks like a %s spreadsheet, but the selected "
                             "instrument is %s. HOBO and Seaguard qualified files are never "
                             "stackable - unify them into separate databases." % (base, layout.upper(), instrument))
        df['Source file'] = base
        frames.append(df)
        messages.append('MESSAGE: %s: %d rows' % (base, len(df)))

    if not frames:
        raise ValueError('build_database: no readable qualified files in the selection.')

    database = pd.concat(frames, ignore_index=True)
    database['Datetime'] = pd.to_datetime(database['Datetime'], errors='coerce')
    n_bad_ts = int(database['Datetime'].isna().sum())
    if n_bad_ts:
        messages.append('WARNING: %d row(s) without a valid timestamp discarded.' % n_bad_ts)
        database = database[database['Datetime'].notna()]

    database = database.sort_values(['Site', 'Datetime'], kind='stable')

    # exact duplicates (same values in all columns, except the provenance)
    value_cols = [c for c in database.columns if c != 'Source file']
    n_before = len(database)
    database = database.drop_duplicates(subset=value_cols, keep='first')
    n_exact = n_before - len(database)
    if n_exact:
        messages.append('WARNING: %d exact duplicate row(s) (same Site+Datetime+values) '
                        'discarded - kept the first occurrence.' % n_exact)

    # overlaps with DIFFERENT values: kept, but the operator needs to know
    overlap_mask = database.duplicated(subset=['Site', 'Datetime'], keep=False)
    if overlap_mask.any():
        offenders = sorted(database.loc[overlap_mask, 'Source file'].unique())
        messages.append('WARNING: %d row(s) share the same Site+Datetime with DIFFERENT values '
                        '(overlapping qualifications?) - ALL kept; check the files: %s'
                        % (int(overlap_mask.sum()), ', '.join(offenders)))

    database.index = np.arange(len(database))
    for site, group in database.groupby('Site'):
        messages.append('MESSAGE: site %s: %d rows, %s to %s'
                        % (site, len(group), group['Datetime'].min(), group['Datetime'].max()))
    messages.append('MESSAGE: database built: %d file(s), %d rows, instrument %s.'
                    % (len(frames), len(database), instrument))
    return database, messages


def combine_hobo_replicates(replicates, temp_tol=0.5):
    """Combine N (2-4) redundant HOBO replicates of the SAME site/deployment,
    each already qualified independently, into a single series.

    Temperature: the MEAN of the replicates that are acceptable (Flag_T <= 2) at
    each timestamp. The between-replicate spread (max - min) is kept in a
    'Temperature spread (degC)' column; when it exceeds `temp_tol` (with >= 2
    acceptable replicates) the combined Flag_T is SUSPECT (3) - the replicates
    disagree, which is itself a QC signal.

    Light: the per-timestamp MAX of the NON-fouled readings (Flag_lux != 4).
    Fouling only attenuates light, so the brightest unfouled sensor is the most
    reliable. The combined light stays good (Flag_lux 1) while AT LEAST ONE
    replicate is unfouled, and becomes BAD (4) only once EVERY replicate is
    fouled - i.e. the usable window is extended to the last replicate to foul.
    (No naive averaging of light: that would mix clean + fouled sensors.)

    replicates: list of qualified HOBO DataFrames (2-4), each with columns
    'Datetime', 'Temperature (degC)', 'Luminosity (lux)', 'Flag_T', 'Flag_lux'
    (and optionally 'Site'). Returns (combined_df, messages)."""
    if len(replicates) < 2:
        raise ValueError('combine_hobo_replicates: need at least 2 replicates.')
    messages = []

    # align every replicate onto the first replicate's time grid (nearest match
    # within half the sampling interval, to absorb small clock differences)
    ref_times = pd.DatetimeIndex(pd.to_datetime(replicates[0]['Datetime'])).sort_values()
    step = ref_times.to_series().diff().median()
    tol = (step / 2) if (pd.notna(step) and step > pd.Timedelta(0)) else None
    aligned = []
    for r in replicates:
        a = r.copy()
        a['Datetime'] = pd.to_datetime(a['Datetime'])
        a = a.set_index('Datetime')
        a = a[~a.index.duplicated(keep='first')].sort_index()
        aligned.append(a.reindex(ref_times, method='nearest', tolerance=tol))

    def stack(name):
        return pd.concat([a[name] for a in aligned], axis=1, ignore_index=True)

    T = stack('Temperature (degC)')
    FT = stack('Flag_T').apply(pd.to_numeric, errors='coerce')
    L = stack('Luminosity (lux)')
    FL = stack('Flag_lux').apply(pd.to_numeric, errors='coerce')

    # temperature: mean over the acceptable (Flag_T <= 2) replicates
    t_ok = (FT <= 2) & T.notna()
    T_ok = T.where(t_ok)
    n_t = t_ok.sum(axis=1)
    temp_mean = T_ok.mean(axis=1)
    temp_spread = (T_ok.max(axis=1) - T_ok.min(axis=1)).where(n_t >= 2, 0.0)
    flag_t = pd.Series(9, index=ref_times)              # none acceptable -> missing
    flag_t[n_t >= 1] = 1                                # at least one good
    flag_t[(n_t >= 2) & (temp_spread > temp_tol)] = 3   # replicates disagree -> suspect

    # light: max of the non-fouled (Flag_lux != 4) readings
    l_clean = (FL != 4) & L.notna()
    n_clean = l_clean.sum(axis=1)
    lux_comb = L.where(l_clean).max(axis=1).where(n_clean >= 1, L.max(axis=1))
    flag_lux = pd.Series(9, index=ref_times)            # all light missing
    flag_lux[L.notna().any(axis=1)] = 4                 # present but all fouled -> bad
    flag_lux[n_clean >= 1] = 1                          # at least one unfouled -> good

    out = pd.DataFrame({
        'Datetime': ref_times,
        'Temperature (degC)': temp_mean.round(4).values,
        'Temperature spread (degC)': temp_spread.round(4).values,
        'Luminosity (lux)': lux_comb.round(4).values,
        'Flag_T': flag_t.values.astype(int),
        'Flag_lux': flag_lux.values.astype(int),
    })
    if 'Site' in replicates[0].columns and len(replicates[0]):
        out.insert(1, 'Site', replicates[0]['Site'].iloc[0])

    messages.append('MESSAGE: combined %d HOBO replicates over %d aligned timestamps.'
                    % (len(replicates), len(out)))
    n_disagree = int((flag_t == 3).sum())
    if n_disagree:
        messages.append('WARNING: %d timestamp(s) where the replicate temperatures disagree by '
                        'more than %.2f degC - combined Flag_T set to SUSPECT there.'
                        % (n_disagree, temp_tol))
    all_fouled = flag_lux[flag_lux == 4]
    if len(all_fouled):
        messages.append('MESSAGE: combined light usable until %s (all replicates fouled after that).'
                        % pd.Timestamp(all_fouled.index[0]))
    return out, messages

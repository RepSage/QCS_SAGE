import numpy as np # type: ignore
import pandas as pd # type: ignore
import QCS_DataHandler as data
import QCS_Tests as QC
import re
import os
import matplotlib.pyplot as plt # type: ignore
from matplotlib.dates import date2num # type: ignore
from datetime import timedelta
import datetime
#import windrose
import matplotlib as mpl # type: ignore
from matplotlib.lines import Line2D # type: ignore
####################################################################
def renameParameters (parameter_names):
    rParam = []
    for param in parameter_names:
        if param == 'Temperature (degC)':
            rParam.append('Temperature (°C)')

        elif param == 'Salinity (PSU)':
            rParam.append('Salinity (PSU)')

        elif param == 'Conductivity (mS/cm)':
            rParam.append('Conductivity (mS/cm)')

        elif param == 'Density (kg/m3)':
            rParam.append('Density (kg/m³)')

        elif param == 'CO2 level (ppm)':
            rParam.append('CO2 (ppm)')

        elif param == 'O2 level (uM)':
            rParam.append('O2 (µM)')

        elif param == 'PAR (umol/m2/s)':
            rParam.append('PAR (µmol/m²/s)')

        elif param == 'Turbidity (FTU)':
            rParam.append('Turbidity (FTU)')

        elif param == 'Chlorophyll (ug/L)':
            rParam.append('Chlorophyll (µg/L)')

        elif param == 'pH':
            rParam.append('pH')    

        elif param == 'Dissolved organic matter (ppb)':
            rParam.append('Dissolved organic matter (ppb)')

        elif param == 'Soundspeed (m/s)':
            rParam.append('Soundspeed (m/s)')
        else:
            rParam.append(param)
    return rParam

def getParamColors (parameter_names):
    cParam =  {'Temperature (degC)': 'red',
               'Salinity (PSU)': 'magenta',
               'Conductivity (mS/cm)': 'y',
               'Density (kg/m3)': 'aquamarine',                                              
               'CO2 level (ppm)': 'yellowgreen',
               'O2 level (uM)': 'deepskyblue',
               'PAR (umol/m2/s)': 'peachpuff',
               'Turbidity (FTU)': 'forestgreen',
               'Chlorophyll (ug/L)': 'springgreen',
               'pH': 'mediumorchid',                                              
               'Dissolved organic matter (ppb)': 'peru',
               'Soundspeed (m/s)': 'navajowhite'
               }
    bcParam = {'Temperature (degC)': 'firebrick',
               'Salinity (PSU)': 'darkmagenta',
               'Conductivity (mS/cm)': 'olive',
               'Density (kg/m3)': 'mediumaquamarine',                                              
               'CO2 level (ppm)': 'olivedrab',
               'O2 level (uM)': 'dodgerblue',
               'PAR (umol/m2/s)': 'sandybrown',
               'Turbidity (FTU)': 'limegreen',
               'Chlorophyll (ug/L)': 'mediumseagreen',
               'pH': 'darkorchid',                                              
               'Dissolved organic matter (ppb)': 'sienna',
               'Soundspeed (m/s)': 'burlywood'
               }    
    
    return cParam, bcParam

def getSiteColors (site_names):
    import matplotlib.colors as mcolors # type: ignore
    import random
    everyColor = list(mcolors.CSS4_COLORS.keys())
    
    cSite = {'A01': 'firebrick',
              'A02': 'darkmagenta',
              'A03': 'olive',
              'A04': 'mediumaquamarine',
              'A05': 'olivedrab',
              'A06': 'dodgerblue',
              'A07': 'sandybrown',
              'A08': 'forestgreen',
              'B01': 'mediumseagreen',
              'B02': 'darkorchid',
              'B03': 'sienna',
              'B04': 'burlywood',
              'B05': 'mediumvioletred',
              'B06': 'teal'}
    
    availableColors = [cor for cor in everyColor if cor not in cSite.values()]   
    mainSites = list(cSite.keys())
    colors = {}
    for i in range(len(site_names)):
        if site_names[i] in mainSites:
            colors[mainSites[i]] = cSite[mainSites[i]]
        else:
            colors[site_names[i]] = random.choice(availableColors)
    return colors

def setParam (dataViewSettings, db, semester, site):
    parameterNames_original = dataViewSettings['parameterList']
    year = dataViewSettings['filterByYear']
    cParam_original, bcParam_original = getParamColors (parameterNames_original)
    
    parameter_names = parameterNames_original.copy()
    cParam = {}
    bcParam = {}
    # define list of dataframes for y axis parameters
    dataAxis_list = []
    #for i in range(n_axis):
    i = 0
    while i < len(parameter_names):
        slice = db[semester].loc[:, parameter_names[i]].copy()
        if slice.isna().all():
            print('\nNo %s data for %s during %d %s.'%(parameter_names[i], site, year, semester))
            parameter_names.pop(i)
            pass
        else:
            dataAxis_list.append(slice)
            i += 1
    for ic in range(len(cParam_original)):
        if list(cParam_original.keys())[ic] in parameter_names:
            n = list(cParam_original.keys())[ic]
            cParam[n] = cParam_original[n]
            bcParam[n] = bcParam_original[n]
    return dataAxis_list, cParam, bcParam, parameter_names
                

def plot_variable(qualified_data, raw_data, variable, dataview_path, SETTINGS, fixed_scale):
    fig = plt.figure()
    fig.set_size_inches(10,6)
    ax1 = fig.gca()
    plt.grid(axis='both', color='k', linestyle='--', linewidth=0.2)
    ax1.set_ylabel(variable)
    ax1.plot(qualified_data['Datetime'], qualified_data[variable], marker='o', linestyle='none', markersize=2, label='Approved data')

    #not_nan = np.asarray(qualified_data.index[~np.isnan(qualified_data[variable])])
    #mirror_var = raw_data.copy()
    #mirror_var.loc[not_nan, variable] = np.nan
    #ax1.plot(mirror_var['Datetime'], mirror_var[variable], marker='o', c='red', linestyle='none', markersize=2, label='Reproved data')

    year = qualified_data['Datetime'].iloc[0].year
    month_firstday = qualified_data['Datetime'].iloc[0].month
    month_finalday = qualified_data['Datetime'].iloc[-1].month
    firstday = qualified_data['Datetime'].iloc[0].day
    finalday = qualified_data['Datetime'].iloc[-1].day
    x_inflim = pd.Timestamp(datetime.datetime(year, month_firstday, firstday, 0, 0))
    x_suplim = pd.Timestamp(datetime.datetime(year, month_finalday, finalday, 23, 59))
    ax1.set_xlim(x_inflim, x_suplim)

    if fixed_scale == True:
        if re.search('hydrogen potential' ,variable, re.IGNORECASE):
            ax1.set_ylim(SETTINGS['env_min_pH'], SETTINGS['env_max_pH'])
        if re.search('chlorophyll' ,variable, re.IGNORECASE):
            ax1.set_ylim(SETTINGS['env_min_chl'], SETTINGS['env_max_chl'])
        if re.search('O2' ,variable, re.IGNORECASE):
            ax1.set_ylim(SETTINGS['env_min_O2'], SETTINGS['env_max_O2'])
        if re.search('organic matter' ,variable, re.IGNORECASE):
            ax1.set_ylim(SETTINGS['env_min_org'], SETTINGS['env_max_org'])
        if re.search('salinity' ,variable, re.IGNORECASE):
            ax1.set_ylim(SETTINGS['env_min_sal'], SETTINGS['env_max_sal'])

    if re.search('depth', variable, re.IGNORECASE):
        ax1.invert_yaxis()

    ax1.set_title('Site: %s  /   year: %s   /  month: %s'%(qualified_data['Site'].iloc[0], year, month_firstday))
    plt.savefig(dataview_path + '/' + re.search('^[^\(]+',variable, re.IGNORECASE).group() + ' series.svg', bbox_inches='tight', dpi=100)
    #plt.close('all')

def plot_variable_profile(qualified_data, raw_data, variable, dataview_path, SETTINGS, fixed_scale):
    fig = plt.figure()
    fig.set_size_inches(10,6)
    ax1 = fig.gca()
    plt.grid(axis='both', color='k', linestyle='--', linewidth=0.2)
    ax1.set_xlabel(variable)
    ax1.plot(qualified_data[variable], qualified_data['Depth(m)'], marker='o', linestyle='none', markersize=2, label='Approved data')
    ax1.set_ylabel('Depth (m)')

    year = qualified_data['Datetime'].iloc[0].year
    month = qualified_data['Datetime'].iloc[0].month

    if fixed_scale == True:
        if re.search('hydrogen potential' ,variable, re.IGNORECASE):
            ax1.set_ylim(SETTINGS['env_min_pH'], SETTINGS['env_max_pH'])
        if re.search('chlorophyll' ,variable, re.IGNORECASE):
            ax1.set_ylim(SETTINGS['env_min_chl'], SETTINGS['env_max_chl'])
        if re.search('O2' ,variable, re.IGNORECASE):
            ax1.set_ylim(SETTINGS['env_min_O2'], SETTINGS['env_max_O2'])
        if re.search('organic matter' ,variable, re.IGNORECASE):
            ax1.set_ylim(SETTINGS['env_min_org'], SETTINGS['env_max_org'])
        if re.search('salinity' ,variable, re.IGNORECASE):
            ax1.set_ylim(SETTINGS['env_min_sal'], SETTINGS['env_max_sal'])

    if qualified_data['Depth(m)'].max() <=10:
        ax1.set_ylim(0, 10)
    elif 10 < qualified_data['Depth(m)'].max() <= 20:
        ax1.set_ylim(0, 20)
    elif 20 < qualified_data['Depth(m)'].max() <= 30:
        ax1.set_ylim(0, 30)
    elif 30 < qualified_data['Depth(m)'].max() <= 40:
        ax1.set_ylim(0, 40)
    elif 40 < qualified_data['Depth(m)'].max() <= 50:
        ax1.set_ylim(0, 50)
    elif 50 < qualified_data['Depth(m)'].max() <= 60:
        ax1.set_ylim(0, 60)
    elif 60 < qualified_data['Depth(m)'].max() <= 70:
        ax1.set_ylim(0, 70)
    elif 70 < qualified_data['Depth(m)'].max() <= 80:
        ax1.set_ylim(0, 80)
    elif 80 < qualified_data['Depth(m)'].max() <= 90:
        ax1.set_ylim(0, 90)
    elif 90 < qualified_data['Depth(m)'].max() <= 100:
        ax1.set_ylim(0, 100)
    elif 100 < qualified_data['Depth(m)'].max() <= 150:
        ax1.set_ylim(0, 150)
    elif 150 < qualified_data['Depth(m)'].max() <= 200:
        ax1.set_ylim(0, 200)
    elif 200 < qualified_data['Depth(m)'].max() <= 250:
        ax1.set_ylim(0, 250)
    elif 250 < qualified_data['Depth(m)'].max() <= 300:
        ax1.set_ylim(0, 300)

    ax1.invert_yaxis()
    ax1.set_title('Site: %s  /   year: %s   /  month: %s'%(qualified_data['Site'].iloc[0], year, month))
    plt.savefig(dataview_path + '/' + re.search('^[^\(]+',variable, re.IGNORECASE).group() + ' profile.svg', bbox_inches='tight', dpi=100)
    #plt.close('all')

def identify_valid_interval (y):
    yi = y.copy()
    pn = np.isnan(yi)
    fst_id = np.argmax(~pn)
    lst_id = len(yi) - np.argmax(np.flip(~pn))
    yi = yi[fst_id:lst_id]
    xi = yi.index
    return xi, yi

def identify_valid_interval_profile (x, y):
    xi = x.copy()
    pn = np.isnan(xi)
    fst_id = np.argmax(~pn)
    lst_id = len(xi) - np.argmax(np.flip(~pn))
    xi = xi[fst_id:lst_id]
    yi = y.loc[xi.index]
    xi = xi[~xi.index.duplicated(keep='first')]
    yi = yi[~yi.index.duplicated(keep='first')]
    return xi, yi

def linear_regression (y, degree):
    xi, yi = identify_valid_interval(y)
    yi = np.asarray(yi)
    idx = np.where(np.isnan(yi))[0]
    if len(idx) > 0.25 * len(yi):
        yi = np.delete(yi, idx)
        xi = np.delete(xi, idx)
    else:
        yi[np.where(np.isnan(yi))] = np.nanmean(yi)
    # adjust linear regression
    coefficients = np.polyfit(np.arange(len(yi)), yi, degree)

    # predict values
    y_pred = np.polyval(coefficients, np.arange(len(yi)))
    #if len(idx) > 0.25 * len(yi):
    #    pass
    #else:
    #    y_pred[idx] = np.nan
    return xi, y_pred

def linear_regression_profile (x, y, degree):
    xi, yi = identify_valid_interval_profile(x, y)
    yi = np.asarray(yi)
    xi = np.asarray(xi)
    idx_xi = np.where(np.isnan(xi))[0]
    idx_yi = np.where(np.isnan(yi))[0]
    idx = np.concatenate((idx_xi,idx_yi))
    #if len(idx) > 0.25 * len(yi):
    yi = np.delete(yi, idx)
    xi = np.delete(xi, idx)
    #else:
    #    xi[np.where(np.isnan(xi))] = np.nanmean(xi)
    # adjust linear regression
    coefficients = np.polyfit(yi, xi, degree)

    # predict values
    x_pred = np.polyval(coefficients, yi)
    #if len(idx) > 0.25 * len(xi):
    #    pass
    #else:
    #    x_pred[idx] = np.nan
    return yi, x_pred

def fill_NaT_gap (y):
    x, y = identify_valid_interval (y)
    delta = pd.Timedelta(hours=1)
    gap_i = np.where(y.index.to_series().diff() > delta)[0] - 1
    gap_ids = y.iloc[gap_i].index + delta
    new_lines = pd.Series(np.nan, index=gap_ids)
    y = pd.concat([y, new_lines]).sort_index()
    return y, gap_ids

def plot_database_panel1 (database, dataViewSettings):
    site_names = dataViewSettings['siteList']
    parameter_names = dataViewSettings['parameterList']
    year = dataViewSettings['filterByYear']
    fit_lin_regression = dataViewSettings['tendencyLines']
    deg = dataViewSettings['linearRegressionDegree']
    points = dataViewSettings['viewDataPoints']
    
    db_raw = database.copy()
    # limit data to year
    db_raw = db_raw[(db_raw['Datetime'].dt.year == year)]
    db_raw.index = db_raw['Datetime']
    db_raw = db_raw.rename_axis('dt_index')
    db_raw = db_raw.sort_values(by='dt_index')
    for site in site_names:
        # spliting data by semester and site
        try:
            db = {'1stSemester': db_raw[(db_raw.loc[:,'Datetime'].dt.month >= 1) & (db_raw.loc[:,'Datetime'].dt.month <= 6) & (db_raw.loc[:,'Site'] == site)],
                  '2ndSemester': db_raw[(db_raw.loc[:,'Datetime'].dt.month >= 7) & (db_raw.loc[:,'Datetime'].dt.month <= 12) & (db_raw.loc[:,'Site'] == site)]}
            #verify which semesters are empty
            emptySemester = [key for key, value in db.items() if value.empty]
            if len(emptySemester) == len(db):
                emptySemester_str = ", ".join(emptySemester)
                raise ValueError('Empty sequence for both semesters in current combination of selected sites and year. Double check inputs or select different sites/year.')
        except ValueError as e:
            print('SelectionError:', e)
        for semester in db.keys():
            # define list of dataframes for y axis parameters
            y_list, cParam, bcParam, parameter_names = setParam (dataViewSettings, db, semester, site)
            rParam = renameParameters(parameter_names)
            if len(y_list) > 0:
                fig, ax1 = plt.subplots(figsize=(1960 / 100, 1000 / 100))
                plt.xticks(rotation=35)
                plt.subplots_adjust(left=0.030, right=0.620)
                plt.grid(True, linestyle='dotted', linewidth=0.5)
                #define x and y
                # defining y while removing datetime duplicates
                y = y_list[0].loc[~(y_list[0].index.duplicated(keep=False) & y_list[0].isna())]
                # filling gaps greater than 1 hour
                y, gap_ids = fill_NaT_gap(y)
                #defining x
                x = y.index
                if fit_lin_regression == True:
                    xp, yp = linear_regression (y, degree=deg)
                    if points == True:
                        ax1.plot(x, y, color=cParam[y_list[0].name], linestyle='none', marker='.', markersize=3, label=rParam[0])
                    ax1.plot(xp, yp, color=bcParam[y_list[0].name], linestyle='-', label=rParam[0])
                else:
                    ax1.plot(x, y, color=bcParam[y_list[0].name], linestyle='-', marker='.', label=rParam[0])
                # set y label
                ax1.set_ylabel(rParam[0], color=bcParam[y_list[0].name])
                # set title
                ax1.set_title('Parameters for %s over %s during %s'%(site, semester, year))
                # set y axis color and position
                ax1.spines['left'].set_color(bcParam[y_list[0].name])
                ax1.spines['left'].set_position(('outward', 1))
                ax1.spines['left'].set_linewidth(2.0)
                ax1.tick_params(axis='y', which='both', colors=bcParam[y_list[0].name])
                # axis list
                axes = {'y1': ax1}
                offset = 0
                for i, y in enumerate(y_list[1:], start=2):
                    # create aditional y axis
                    ax = ax1.twinx()
                    #defining y while removing datetime duplicates
                    y = y.loc[~(y.index.duplicated(keep=False) & y.isna())]
                    # filling gaps greater than 1 hour
                    y, gap_ids = fill_NaT_gap(y)
                    #defining x
                    x = y.index
                    # plot adicional axis
                    if fit_lin_regression == True:
                        xp, yp = linear_regression (y, degree=deg)
                        if points == True:
                            ax.plot(x, y, linestyle='none', marker='.', markersize=3, c=cParam[y_list[i-1].name], label=rParam[i-1])
                        ax.plot(xp, yp, linestyle='-', c=bcParam[y_list[i-1].name], label=rParam[i-1])
                    else:
                        ax.plot(x, y, linestyle='-', marker='.', c=bcParam[y_list[i-1].name], label=rParam[i-1])
                    # set axis label
                    ax.set_ylabel(rParam[i-1], c=bcParam[y_list[i-1].name])
                    # set y axis position
                    if i == 2:
                        pass
                    else:
                        ax.spines['right'].set_position(('outward', offset))
                    offset += 60
                    # set y axis colors
                    ax.spines['right'].set_color(bcParam[y_list[i-1].name])
                    ax.spines['left'].set_color('none')
                    # set y axis width
                    ax.spines['right'].set_linewidth(1.5)
                    # change tick colors
                    ax.tick_params(axis='y', colors=cParam[y_list[i-1].name])
                    # save axis name
                    axes[f'y{i}'] = ax
            #if slice.empty:
            #    pass
            #else:
                #defining data format
                plt.gca().xaxis.set_major_formatter(plt.matplotlib.dates.DateFormatter('%d/%m %H:%M'))
                plt.show()
                plt.savefig('panel1_%s_%s_%d.svg'%(site, semester, year))

def plot_database_panel2 (database, dataViewSettings):
    site_names = dataViewSettings['siteList']
    parameter_names = dataViewSettings['parameterList']
    year = dataViewSettings['filterByYear']
    fit_lin_regression = dataViewSettings['tendencyLines']
    deg = dataViewSettings['linearRegressionDegree']
    points = dataViewSettings['viewDataPoints']  
    
    n_axis = len(parameter_names)
    db_raw = database.copy()
    # limit data to year
    db_raw = db_raw[(db_raw['Datetime'].dt.year == year)]
    db_raw.index = db_raw['Datetime']
    db_raw = db_raw.rename_axis('dt_index')
    db_raw = db_raw.sort_values(by='dt_index')

    colors = getSiteColors (site_names)
    #colors = ['blue', 'red', 'chocolate', 'blueviolet', 'darkolivegreen', 'deepskyblue']
    #colors = ['royalblue', 'tomato', 'sandybrown', 'violet', 'lime', 'cyan']
    rParam = renameParameters (parameter_names)
    # spliting data by semester and site
    db = {'1stSemester': db_raw[(db_raw.loc[:,'Datetime'].dt.month >= 1) & (db_raw.loc[:,'Datetime'].dt.month <= 6)],
          '2ndSemester': db_raw[(db_raw.loc[:,'Datetime'].dt.month >= 7) & (db_raw.loc[:,'Datetime'].dt.month <= 12)]}
    for semester in db.keys():
        for parameter in parameter_names:
            i = 0
            fig, ax1 = plt.subplots(figsize=(1960 / 100, 1000 / 100))
            plt.title('%s on %s for each site for %s'%(parameter, semester, str(year)))
            plt.grid(True, linestyle='dotted', linewidth=0.5)
            ax1.set_ylabel(rParam[i])
            control = 0
            for site in site_names:
                #define x and y
                y = db[semester].copy()
                y = y[parameter][(y.loc[:,'Site'] == site)]
                # defining y while removing datetime duplicates
                y = y.loc[~(y.index.duplicated(keep=False) & y.isna())]
                if y.isna().all():
                    print('\nNo %s data for %s during %d %s.'%(parameter_names[i], site, year, semester))
                    pass
                else:
                    control += 1
                    # filling gaps greater than 1 hour
                    y, gap_ids = fill_NaT_gap(y)
                    #defining x
                    new_date = pd.to_datetime('%s-01-01'%str(year))
                    first_time = y.index[0].replace(hour=0, minute=0, second=0, microsecond=0)
                    timedelta = (y.index - first_time)
                    x = new_date + pd.Series(timedelta)
                    ax1.set_xlabel('Daytime')
                    if fit_lin_regression == True:
                        xp, yp = linear_regression (y, degree=deg)
                        if points == True:
                            ax1.plot(x, y, linestyle='none', marker='.', color= colors[site], markersize=3, label=site + ' data')
                            ax1.plot(x, yp, linestyle='-', color= colors[site], label=site + ' tendency')

                            new_date = pd.to_datetime('%s-01-01'%str(year))
                            first_time = xp[0].replace(hour=0, minute=0, second=0, microsecond=0)
                            timedelta = (xp - first_time)
                            x = new_date + pd.Series(timedelta)
                            numerical_ticks = plt.gca().get_xticks()
                            datetime_ticks = pd.to_datetime(numerical_ticks, unit='D', origin='unix')
                            new_labels = [pd.to_datetime(tick).strftime('%H:%M') for tick in datetime_ticks]
                            plt.gca().set_xticks(numerical_ticks)
                            plt.gca().set_xticklabels(new_labels)
                        else:
                            ax1.plot(xp, yp, linestyle='-', color= colors[site], label=site + ' tendency')
                    else:
                        ax1.plot(x, y, linestyle='-', color = colors[site], label=site)
                    i += 1
            if control == 0:
                plt.close(fig)
            else:
                datelist = pd.date_range(new_date, periods=9,freq='6H')
                start = int(numerical_ticks[0])
                end = int(numerical_ticks[0]) + 2
                xticks = np.arange(start, end + 0.25, 0.25)
                new_labels = [pd.to_datetime(tick).strftime('%H:%M') for tick in datelist]
                plt.gca().set_xticks(xticks)
                plt.gca().set_xticklabels(new_labels)
                ax1.legend(loc='upper left', bbox_to_anchor=(1, 1.01))
                plt.subplots_adjust(left=0.06, right=0.86, top=0.88, bottom=0.11)
                plt.show()
                if re.search(r'\([^()]*\)', parameter, re.IGNORECASE):
                    nDigits = len(re.search(r'\([^()]*\)', parameter, re.IGNORECASE).group())
                    parameter = parameter[:len(parameter)-nDigits]
                plt.savefig('panel2_%s_%s_%d.svg'%(parameter, semester, year))

def plot_database_panel3 (database, dataViewSettings):
    site_names = dataViewSettings['siteList']
    parameter_names = dataViewSettings['parameterList']
    year = dataViewSettings['filterByYear']
    fit_lin_regression = dataViewSettings['tendencyLines']
    deg = dataViewSettings['linearRegressionDegree']
    points = dataViewSettings['viewDataPoints']

    db_raw = database.copy()
    # limit data to year
    db_raw = db_raw[(db_raw['Datetime'].dt.year == year)]
    db_raw.index = db_raw['Datetime']
    db_raw = db_raw.rename_axis('dt_index')
    db_raw = db_raw.sort_values(by='dt_index')  
    for site in site_names:
        # spliting data by semester and site
        try:
            db = {'1stSemester': db_raw[(db_raw.loc[:,'Datetime'].dt.month >= 1) & (db_raw.loc[:,'Datetime'].dt.month <= 6) & (db_raw.loc[:,'Site'] == site)],
                  '2ndSemester': db_raw[(db_raw.loc[:,'Datetime'].dt.month >= 7) & (db_raw.loc[:,'Datetime'].dt.month <= 12) & (db_raw.loc[:,'Site'] == site)]}
            #verify which semesters are empty
            emptySemester = [key for key, value in db.items() if value.empty]
            if len(emptySemester) == len(db):
                emptySemester_str = ", ".join(emptySemester)
                raise ValueError('Empty sequence for both semesters in current combination of selected sites and year. Double check inputs or select different sites/year.')
        except ValueError as e:
            print('SelectionError:', e)
        for semester in db.keys():
            x_list, cParam, bcParam, parameter_names = setParam (dataViewSettings, db, semester, site)
            rParam = renameParameters(parameter_names)
            if len(x_list) > 0:
                figHeight = 1000
                fig, ax1 = plt.subplots(figsize=(1960 / 100, figHeight / 100))
                bottomAxis = - (0.325 * figHeight)
                offset = bottomAxis - 50
                plt.subplots_adjust(left=0.1, right=0.9, top=0.975, bottom=0.56)
                ax1.invert_yaxis()
                plt.grid(True, axis='y', linestyle='dotted', linewidth=0.5)
                #define x and y
                # defining x while removing datetime duplicates
                x = x_list[0].loc[~(x_list[0].index.duplicated(keep=False) & x_list[0].isna())]
                # filling gaps greater than 1 hour
                x, gap_ids = fill_NaT_gap(x)
                x.name = x_list[0].name
                #defining y
                y = (db[semester]['Depth(m)']).loc[~(x_list[0].index.duplicated(keep=False) & x_list[0].isna())]
                # sorting by depth
                sorted_df = pd.concat([x,y], axis=1).sort_values(by='Depth(m)')
                x, y = (sorted_df[x.name], sorted_df[y.name])
                if fit_lin_regression == True:
                    yp, xp = linear_regression_profile(x, y, degree=deg)
                    if points == True:
                        ax1.plot(x, y, color=cParam[x_list[0].name], linestyle='none', marker='.', markersize=3, label=x_list[0].name)
                    ax1.plot(xp, yp, color=bcParam[x_list[0].name], linestyle='-', label=x_list[0].name)
                else:
                        ax1.plot(x, y, color=cParam[x_list[0].name], linestyle='none', marker='.', markersize=3, label=x_list[0].name)
                # set x label
                ax1.set_xlabel(rParam[0], color=bcParam[x_list[0].name])
                # set x label
                ax1.set_ylabel('Depth (m)')
                # set title
                ax1.set_title('Parameters for %s over %s during %s'%(site, semester, year))
                ax1.set_ylim(ymax=0)
                marginMax = 0.01 * x.max()
                # adjust margin on the right side
                ax1.set_xlim(xmax=x.max() + marginMax)
                # set y axis color and position
                ax1.spines['bottom'].set_color(bcParam[x_list[0].name])
                ax1.spines['bottom'].set_linewidth(1.5)
                ax1.tick_params(axis='x', which='both', colors=bcParam[x_list[0].name])
                # axis list
                axes = {'y1': ax1}
                n = len(x_list)
                spineOffset = 50
                labelOffset = -0.25
                for i, x in enumerate(x_list[1:], start=2):
                    # create aditional x axis
                    ax = ax1.twiny()
                    # setting bottom axis as invisible
                    ax.tick_params(axis='x', which='both', colors=bcParam[x_list[i-1].name], top=False, bottom=True, labeltop=False, labelbottom=True, direction='out')
                    # setting top axis position and color
                    ax.spines['bottom'].set_position(('outward', spineOffset))
                    ax.spines['bottom'].set_color(bcParam[x_list[i-1].name])
                    spineOffset +=50
                    # set y axis width
                    ax.spines['bottom'].set_linewidth(1.5)
                    # set axis label
                    ax.set_xlabel(rParam[i-1], c=bcParam[x_list[i-1].name])
                    axPosition = ax.spines['bottom'].get_position()[1]
                    ax.xaxis.set_label_coords(0.5, labelOffset)
                    labelOffset += -0.17
                    #defining x while removing datetime duplicates
                    x = x.loc[~(x.index.duplicated(keep=False) & x.isna())]
                    # filling gaps greater than 1 hour
                    x, gap_ids = fill_NaT_gap(x)
                    x.name = x_list[i-1].name
                    #defining y
                    y = (db[semester]['Depth(m)']).loc[~(x_list[i-1].index.duplicated(keep=False) & x_list[i-1].isna())]
                    # sorting by depth
                    sorted_df = pd.concat([x,y], axis=1).sort_values(by='Depth(m)')
                    x, y = (sorted_df[x.name], sorted_df[y.name])
                    # plot adicional axis
                    if fit_lin_regression == True:
                        yp, xp = linear_regression_profile (x, y, degree=deg)
                        xp[np.where(xp<0)[0]] = np.nan
                        if points == True:
                            ax.plot(x, y, linestyle='none', marker='.', markersize=3, c=cParam[x_list[i-1].name], label=rParam[i-1])
                        ax.plot(xp, yp, linestyle='-', c=bcParam[x_list[i-1].name], label=rParam[i-1])
                    else:
                        ax.plot(x, y, linestyle='none', marker='.', markersize=3, c=cParam[x_list[i-1].name], label=rParam[i-1])
                    # save axis name
                    axes[f'y{i}'] = ax
                    ax.set_ylim(ymax=0)
                    #marginMin = 0.05 * x.max()
                    marginMax = 0.05 * x.max()
                    ax.set_xlim(xmax=x.max() + marginMax)
                plt.show()
            #if slice.empty:
            #    pass
            #else:
                plt.savefig('panel1_%s_%s_%d.svg'%(site, semester, year))

def plot_hobo_split_site (database, dataview_path):
    site_names = list(set(database['Site']))
    for site in site_names:
        siteDatabase = database[(database['Site'] == site)]

        fig = plt.figure()
        fig.set_size_inches(10,6)
        ax1 = fig.gca()
        plt.grid(axis='both', color='k', linestyle='--', linewidth=0.2)
        ax1.set_ylabel('Temperature (degC)')
        plt.title('%s'%site)
        plt.plot(siteDatabase['Datetime'], siteDatabase['Temperature (degC)'], linestyle='None', marker='.', markersize=3)
        plt.tight_layout()
        plt.savefig(dataview_path + '/' + 'hobo_%s_temperature.svg'%site, bbox_inches='tight', dpi=100)

        fig = plt.figure()
        fig.set_size_inches(10,6)
        ax1 = fig.gca()
        plt.grid(axis='both', color='k', linestyle='--', linewidth=0.2)
        ax1.set_ylabel('Luminosity(lux)')
        plt.title('%s'%site)
        plt.plot(siteDatabase['Datetime'], siteDatabase['Luminosity(lux)'], linestyle='None', marker='.', markersize=3)
        plt.tight_layout()
        plt.savefig(dataview_path + '/' + 'hobo_%s_luminosity.svg'%site, bbox_inches='tight', dpi=100)

def plot_TS_diagram (database, dataViewSettings):
    import gsw # type: ignore
    import matplotlib.cm as cm # type: ignore
    import matplotlib.colors as mcolors # type: ignore
    # getting input data
    site_names = dataViewSettings['siteList']
    year = dataViewSettings['filterByYear']
    lat = dataViewSettings['latitude']
    lon = dataViewSettings['longitude']
    tsParam = dataViewSettings['tsParam']
    markerList = ['o', 's', '^', 'v', 'P', 'D', '<', '>', '*', 'h', 'H', 'p', 'd', '.', ',']
    # copying dataset
    db_raw = database.copy()
    # limit data to year
    db_raw = db_raw[(db_raw['Datetime'].dt.year == year)]
    db_raw.index = db_raw['Datetime']
    db_raw = db_raw.rename_axis('dt_index')
    db_raw = db_raw.sort_values(by='dt_index')
    # spliting data by semester
    try:
        db = {'1stSemester': db_raw[(db_raw.loc[:,'Datetime'].dt.month >= 1) & (db_raw.loc[:,'Datetime'].dt.month <= 6) & (db_raw['Site'].isin(site_names))],
            '2ndSemester': db_raw[(db_raw.loc[:,'Datetime'].dt.month >= 7) & (db_raw.loc[:,'Datetime'].dt.month <= 12) & (db_raw['Site'].isin(site_names))]}
        #verify which semesters are empty
        emptySemester = [key for key, value in db.items() if value.empty]
        if len(emptySemester) == len(db):
            emptySemester_str = ", ".join(emptySemester)
            raise ValueError('Empty sequence for both semesters in current combination of selected sites and year. Double check inputs or select different sites/year.')
    except ValueError as e:
        print('SelectionError:', e)
    
    # working with one semester at a time
    for semester in db.keys():
        if semester in emptySemester:
            pass
        else:
            ###### create figure and contour lines
            fig = plt.figure(figsize=(1960 / 100, 1000 / 100))  # Create figure with specified resolution
            ax = fig.add_subplot(111)  # Create axes
            # selecting semester
            tspSemesterData = db[semester][['Pressure(dbar)', 'Depth(m)', 'Temperature (degC)', 'Salinity (PSU)', 'Site']].copy()
            # Convert temperature, salinity, and pressure data to arrays
            salt = np.asarray(tspSemesterData['Salinity (PSU)'].copy())
            temp = np.asarray(tspSemesterData['Temperature (degC)'].copy())
            p = np.asarray(tspSemesterData['Pressure(dbar)'].copy())
            depth = np.asarray(tspSemesterData['Depth(m)'].copy())
            # Calculate absolute salinity from practical salinity
            SA = gsw.SA_from_SP(salt, p, lon, lat)
            # Calculate conservative temperature from in situ temperature
            CT = gsw.CT_from_t(SA, temp, p)
            # Calculate potential temperature from conservative temperature
            pt = gsw.pt_from_CT(SA,CT)
            # save results to dataframe
            tspSemesterData['Absolute Salinity (PSU)'] = SA
            tspSemesterData['Conservative Temperature (degC)'] = CT
            tspSemesterData['Potential Temperature (degC)'] = pt
            # Figure out boundaries (mins and maxs)
            if re.search('conservative', tsParam, re.IGNORECASE):
                smin = np.nanmin(SA) - (0.01 * np.nanmin(SA)/2)
                smax = np.nanmax(SA) + (0.01 * np.nanmax(SA)/2)
                tmin = np.nanmin(CT) - (0.1 * np.nanmax(CT)/2)
                tmax = np.nanmax(CT) + (0.1 * np.nanmax(CT)/2)

            elif re.search('potential', tsParam, re.IGNORECASE):
                smin = np.nanmin(salt) - (0.01 * np.nanmin(SA)/2)
                smax = np.nanmax(salt) + (0.01 * np.nanmax(SA)/2)
                tmin = np.nanmin(pt) - (0.1 * np.nanmax(CT)/2)
                tmax = np.nanmax(pt) + (0.1 * np.nanmax(CT)/2)

            dmin = np.nanmin(depth)
            dmax = np.nanmax(depth)
            # Calculate the number of grid cells in the x and y dimensions
            xdim = int(round((smax - smin) / 0.1 + 1, 0))
            ydim = int(round((tmax - tmin) + 1, 0))
            # Create an empty grid of zeros
            rho = np.zeros((ydim, xdim))
            # Create temperature and salinity vectors of appropriate dimensions
            ti = np.linspace(1, ydim - 1, ydim) + tmin
            si = np.linspace(1, xdim - 1, xdim) * 0.1 + smin
            # Loop to fill in the grid with densities
            for j in range(0, int(ydim)):
                for i in range(0, int(xdim)):
                    rho[j, i] = gsw.rho(si[i], ti[j], 0)
            # Subtract 1000 to convert to sigma-t
            rho = rho - 1000
            # Normalize depth values
            norm = mcolors.Normalize(vmin=dmin, vmax=dmax)
            # plot contour lines
            CS = plt.contour(si, ti, rho,linestyles='dashed', colors='#767676') # comment to deactivate gray contour lines
            plt.clabel(CS, fontsize=8, inline=1, fmt='%1.2f')
            ### Create normalized colorbar
            cbar = fig.colorbar(cm.ScalarMappable(norm=norm, cmap=cm.plasma.reversed()), label='depth(m)', ax=ax, location='right')
            cbar.ax.invert_yaxis()  # Invert colorbar axis
            ax.grid(color='k', linestyle='--', linewidth=0.2)  # Draw grid
            # counting loops
            a = 0
            for site in site_names:         
                # selecting site
                tspData = tspSemesterData[tspSemesterData.loc[:,'Site'] == site]
                # check if there is data for semester and ignore semester if true
                if tspData.isna().all().any():
                    print('\nNo data for %s during %d %s.'%( site, year, semester))
                    pass
                else:
                    # plot x and y depending on selected parameters
                    if re.search('conservative', tsParam, re.IGNORECASE):
                        TS = ax.scatter(tspData['Absolute Salinity (PSU)'], tspData['Conservative Temperature (degC)'], marker=markerList[a], c=tspData['Depth(m)'], lw=0, cmap=cm.plasma.reversed(), norm=norm, label=site)
                        ax.set_xlabel('Absolute Salinity (kg/m³)')  # Label x-axis
                        ax.set_ylabel('Conservative Temperature (C°)')  # Label y-axis
                    elif re.search('potential', tsParam, re.IGNORECASE):
                        TS = ax.scatter(tspData['Salinity (PSU)'], tspData['Potential Temperature (degC)'], marker=markerList[a], c=tspData['Depth(m)'], lw=0, cmap=cm.plasma.reversed(), norm=norm, label=site)
                        ax.set_xlabel('Salinity (PSU)')  # Label x-axis
                        ax.set_ylabel('Potential Temperature (C°)')  # Label y-axis

                    plt.subplots_adjust(top=0.9, bottom=0.1, left=0.05, right=0.96)  # Adjust image spacing
                    # title
                    ax.set_title('T-S Diagram for %s over %s during %s'%(site, semester, year))
                    plt.show()
                    a += 1
            custom_handles = []
            for a in range(len(site_names)):
                custom_handles.append(Line2D([0], [0], linestyle='None', marker=markerList[a], label=site_names[a], markeredgecolor='black', markerfacecolor='black', markersize=6))
            plt.legend(handles=custom_handles)  # Draw legend



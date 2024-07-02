import numpy as np
import pandas as pd
import QCS_DataHandler as data
import QCS_Tests as QC
import re
import os
import matplotlib.pyplot as plt
from matplotlib.dates import date2num
from datetime import timedelta
import datetime
#import windrose
import matplotlib as mpl
####################################################################

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
    plt.savefig(dataview_path + '/' + re.search('^[^\(]+',variable, re.IGNORECASE).group() + ' series.png', bbox_inches='tight', dpi=100)
    #plt.close('all')

def plot_variable_profile(qualified_data, raw_data, variable, dataview_path, SETTINGS, fixed_scale):
    fig = plt.figure()
    fig.set_size_inches(10,6)
    ax1 = fig.gca()
    plt.grid(axis='both', color='k', linestyle='--', linewidth=0.2)
    ax1.set_xlabel(variable)
    ax1.plot(qualified_data[variable], qualified_data['Depth(m)'], marker='o', linestyle='none', markersize=2, label='Approved data')
    ax1.set_ylabel('Depth(m)')

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
    plt.savefig(dataview_path + '/' + re.search('^[^\(]+',variable, re.IGNORECASE).group() + ' profile.png', bbox_inches='tight', dpi=100)
    #plt.close('all')

def identify_valid_interval (y):
    yi = y.copy()
    pn = np.isnan(yi)
    fst_id = np.argmax(~pn)
    lst_id = len(yi) - np.argmax(np.flip(~pn))
    yi = yi[fst_id:lst_id]
    xi = yi.index
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
    if len(idx) > 0.25 * len(yi):
        pass
    else:
        y_pred[idx] = np.nan
    return xi, y_pred

def linear_regression_profile (x, y, degree):
    yi, xi = identify_valid_interval(x)
    yi = y.loc[yi.duplicated(keep=False)]
    xi = np.asarray(xi)
    idx = np.where(np.isnan(xi))[0]
    if len(idx) > 0.25 * len(yi):
        yi = np.delete(yi, idx)
        xi = np.delete(xi, idx)
    else:
        xi[np.where(np.isnan(xi))] = np.nanmean(xi)
    # adjust linear regression
    coefficients = np.polyfit(yi, xi, degree)

    # predict values
    x_pred = np.polyval(coefficients, yi)
    if len(idx) > 0.25 * len(xi):
        pass
    else:
        x_pred[idx] = np.nan
    return yi, x_pred

def fill_NaT_gap (y):
    x, y = identify_valid_interval (y)
    delta = pd.Timedelta(hours=1)
    gap_i = np.where(y.index.to_series().diff() > delta)[0] - 1
    gap_ids = y.iloc[gap_i].index + delta
    new_lines = pd.Series(np.nan, index=gap_ids)
    y = y.append(new_lines).sort_index()
    return y, gap_ids

def plot_database_panel1 (database, site_names, parameter_names, year, fit_lin_regression, deg, points):
    n_axis = len(parameter_names)
    db_raw = database.copy()
    # limit data to year
    db_raw = db_raw[(db_raw['Datetime'].dt.year == year)]
    db_raw.index = db_raw['Datetime']
    db_raw = db_raw.rename_axis('dt_index')
    db_raw = db_raw.sort_values(by='dt_index')
    colors_p = ['blue', 'red', 'chocolate', 'blueviolet', 'limegreen', 'deepskyblue']
    colors_l = ['royalblue', 'tomato', 'sandybrown', 'violet', 'lime', 'cyan']
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
            y_list = []
            for i in range(n_axis):
                slice = db[semester].loc[:, parameter_names[i]].copy()
                if slice.isna().all():
                    print('\nNo %s data for %s during %d %s.'%(parameter_names[i], site, year, semester))
                    pass
                else:
                    y_list.append(slice)
            if len(y_list) > 0:
                fig, ax1 = plt.subplots(figsize=(1350 / 100, 660 / 100))
                plt.xticks(rotation=35)
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
                        ax1.plot(x, y, color=colors_p[0], linestyle='none', marker='.', markersize=3, label=y_list[0].name)
                    ax1.plot(xp, yp, color=colors_l[0], linestyle='-', label=y_list[0].name)
                else:
                    ax1.plot(x, y, color=colors_l[0], linestyle='-', marker='.', label=y_list[0].name)
                # set y label
                ax1.set_ylabel(parameter_names[0], color=colors_l[0])
                # set title
                ax1.set_title('Parameters for %s over %s during %s'%(site, semester, year))
                # set y axis color and position
                ax1.spines['left'].set_color(colors_l[0])
                ax1.spines['left'].set_position(('outward', 1))
                ax1.spines['left'].set_linewidth(2.0)
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
                            ax.plot(x, y, linestyle='none', marker='.', markersize=3, c=colors_p[i-1], label=y_list[i-1].name)
                        ax.plot(xp, yp, linestyle='-', c=colors_l[i-1], label=y_list[i-1].name)
                    else:
                        ax.plot(x, y, linestyle='-', marker='.', c=colors_l[i-1], label=y_list[i-1].name)
                    # set axis label
                    ax.set_ylabel(y_list[i-1].name, c=colors_l[i-1])
                    # set y axis position
                    if i == 2:
                        pass
                    else:
                        ax.spines['right'].set_position(('outward', offset))
                    offset += 60
                    # set y axis colors
                    ax.spines['right'].set_color(colors_l[i-1])
                    ax.spines['left'].set_color('none')
                    # set y axis width
                    ax.spines['right'].set_linewidth(1.5)
                    # change tick colors
                    ax.tick_params(axis='y', colors=colors_p[i-1])
                    # save axis name
                    axes[f'y{i}'] = ax
            if slice.empty:
                pass
            else:
                #defining data format
                plt.gca().xaxis.set_major_formatter(plt.matplotlib.dates.DateFormatter('%d/%m %H:%M'))
                # fit to tight layout
                plt.tight_layout()
                plt.savefig('panel1_%s_%s_%d.png'%(site, semester, year))

def plot_database_panel2 (database, site_names, parameter_names, year, fit_lin_regression, deg, points, elapsed_time, change_date):
    n_axis = len(parameter_names)
    db_raw = database.copy()
    # limit data to year
    db_raw = db_raw[(db_raw['Datetime'].dt.year == year)]
    db_raw.index = db_raw['Datetime']
    db_raw = db_raw.rename_axis('dt_index')
    db_raw = db_raw.sort_values(by='dt_index')
    colors_p = ['blue', 'red', 'chocolate', 'blueviolet', 'darkolivegreen', 'deepskyblue']
    colors_l = ['royalblue', 'tomato', 'sandybrown', 'violet', 'lime', 'cyan']
    # spliting data by semester and site
    db = {'1stSemester': db_raw[(db_raw.loc[:,'Datetime'].dt.month >= 1) & (db_raw.loc[:,'Datetime'].dt.month <= 6)],
          '2ndSemester': db_raw[(db_raw.loc[:,'Datetime'].dt.month >= 7) & (db_raw.loc[:,'Datetime'].dt.month <= 12)]}
    for semester in db.keys():
        for parameter in parameter_names:
            fig, ax1 = plt.subplots(figsize=(1350 / 100, 660 / 100))
            plt.title('%s on %s for each site for %s'%(parameter, semester, str(year)))
            ax1.set_ylabel(parameter)
            plt.grid(True, linestyle='dotted', linewidth=0.5)
            i = 0
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
                    if elapsed_time == True:
                        first_time = y.index[0].replace(hour=0, minute=0, second=0, microsecond=0)
                        x = (y.index - first_time).total_seconds()/3600
                        ax1.set_xlabel('elapsed hours from midnight day 1')
                    elif change_date == True:
                        new_date = pd.to_datetime('%s-01-01'%str(year))
                        first_time = y.index[0].replace(hour=0, minute=0, second=0, microsecond=0)
                        timedelta = (y.index - first_time)
                        x = new_date + pd.Series(timedelta)
                        ax1.set_xlabel('Daytime')
                    else:
                        x = y.index.hours
                    if fit_lin_regression == True:
                        xp, yp = linear_regression (y, degree=deg)
                        if points == True:
                            ax1.plot(x, y, linestyle='none', marker='.', color= colors_p[i], markersize=3, label=site + ' data')
                            c = plt.gca().lines[i].get_color()
                        if elapsed_time == True:
                            ax1.plot(x, yp, linestyle='-', color= colors_l[i], label=site + ' tendency')
                        elif change_date == True:
                            new_date = pd.to_datetime('%s-01-01'%str(year))
                            first_time = xp[0].replace(hour=0, minute=0, second=0, microsecond=0)
                            timedelta = (xp - first_time)
                            x = new_date + pd.Series(timedelta)
                            ax1.plot(x, yp, linestyle='-', color= colors_l[i], label=site + ' tendency')
                            numerical_ticks = plt.gca().get_xticks()
                            datetime_ticks = pd.to_datetime(numerical_ticks, unit='D', origin='unix')
                            new_labels = [pd.to_datetime(tick).strftime('%H:%M') for tick in datetime_ticks]
                            plt.gca().set_xticks(numerical_ticks)
                            plt.gca().set_xticklabels(new_labels)
                        else:
                            ax1.plot(xp, yp, linestyle='-', color= colors_l[i], label=site + ' tendency')
                    else:
                        ax1.plot(x, y, linestyle='-', color = colors_l[i], label=site)
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
                plt.tight_layout()
                if re.search(r'\([^()]*\)', parameter, re.IGNORECASE):
                    nDigits = len(re.search(r'\([^()]*\)', parameter, re.IGNORECASE).group())
                    parameter = parameter[:len(parameter)-nDigits]
                plt.savefig('panel2_%s_%s_%d.png'%(parameter, semester, year))

def plot_database_panel3 (database, site_names, parameter_names, year, fit_lin_regression, deg, points):
    n_axis = len(parameter_names)
    db_raw = database.copy()
    # limit data to year
    db_raw = db_raw[(db_raw['Datetime'].dt.year == year)]
    db_raw.index = db_raw['Datetime']
    db_raw = db_raw.rename_axis('dt_index')
    db_raw = db_raw.sort_values(by='dt_index')
    colors_p = ['blue', 'red', 'chocolate', 'blueviolet', 'limegreen', 'deepskyblue']
    colors_l = ['royalblue', 'tomato', 'sandybrown', 'violet', 'lime', 'cyan']
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
            x_list = []
            for i in range(n_axis):
                slice = db[semester].loc[:, parameter_names[i]].copy()
                if slice.isna().all():
                    print('\nNo %s data for %s during %d %s.'%(parameter_names[i], site, year, semester))
                    pass
                else:
                    x_list.append(slice)
            if len(x_list) > 0:
                fig, ax1 = plt.subplots(figsize=(1350 / 100, 660 / 100))
                ax1.invert_yaxis()
                #plt.xticks(rotation=35)
                plt.grid(True, linestyle='dotted', linewidth=0.5)
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
                        ax1.plot(x, y, color=colors_p[0], linestyle='none', marker='.', markersize=3, label=x_list[0].name)
                    ax1.plot(xp, yp, color=colors_l[0], linestyle='-', label=x_list[0].name)
                else:
                        ax1.plot(x, y, color=colors_p[0], linestyle='none', marker='.', markersize=3, label=x_list[0].name)
                # set x label
                ax1.set_xlabel(parameter_names[0], color=colors_l[0])
                # set x label
                ax1.set_ylabel('Depth(m)')
                # set title
                ax1.set_title('Parameters for %s over %s during %s'%(site, semester, year))
                # set y axis color and position
                ax1.spines['bottom'].set_color(colors_l[0])
                ax1.spines['bottom'].set_position(('outward', 1))
                ax1.spines['bottom'].set_linewidth(1.5)
                # axis list
                axes = {'y1': ax1}
                n = len(x_list)
                offset = -310
                plt.subplots_adjust(left=0.1, right=0.9, top=0.9, bottom=0.4)
                for i, x in enumerate(x_list[1:], start=2):
                    # create aditional x axis
                    ax = ax1.twiny()
                    #defining x while removing datetime duplicates
                    x = x.loc[~(x.index.duplicated(keep=False) & x.isna())]
                    # filling gaps greater than 1 hour
                    x, gap_ids = fill_NaT_gap(x)
                    x.name = x_list[0].name
                    #defining y
                    y = (db[semester]['Depth(m)']).loc[~(x_list[i-1].index.duplicated(keep=False) & x_list[i-1].isna())]
                    # sorting by depth
                    sorted_df = pd.concat([x,y], axis=1).sort_values(by='Depth(m)')
                    x, y = (sorted_df[x.name], sorted_df[y.name])
                    # plot adicional axis
                    if fit_lin_regression == True:
                        yp, xp = linear_regression_profile (x, y, degree=deg)
                        if points == True:
                            ax.plot(x, y, linestyle='none', marker='.', markersize=3, c=colors_p[i-1], label=x_list[i-1].name)
                        ax.plot(xp, yp, linestyle='-', c=colors_l[i-1], label=x_list[i-1].name)
                    else:
                        ax.plot(x, y, linestyle='none', marker='.', markersize=3, c=colors_p[i-1], label=x_list[i-1].name)
                    # set x axis position
                    ax.spines['top'].set_position(('outward', offset))
                    offset -= 50
                    # set axis label
                    ax.set_xlabel(x_list[i-1].name, c=colors_l[i-1])
                    axPosition = ax.spines['top'].get_position()[1]
                    # set y axis colors
                    ax.spines['top'].set_color(colors_l[i-1])
                    # set y axis width
                    ax.spines['top'].set_linewidth(1.5)
                    # change tick colors
                    ax.tick_params(axis='y', colors=colors_p[i-1])
                    # save axis name
                    axes[f'y{i}'] = ax
            if slice.empty:
                pass
            else:
                # fit to tight layout
                plt.tight_layout()
                plt.savefig('panel1_%s_%s_%d.png'%(site, semester, year))

def plot_hobo_split_site (database, dataview_path):
    site_names = list(set(database['Site']))
    for site in site_names:
        siteDatabase = database[(database['Site'] == site)]

        fig = plt.figure()
        fig.set_size_inches(10,6)
        ax1 = fig.gca()
        plt.grid(axis='both', color='k', linestyle='--', linewidth=0.2)
        ax1.set_ylabel('Temperature(degC)')
        plt.title('%s'%site)
        plt.plot(siteDatabase['Datetime'], siteDatabase['Temperature(degC)'], linestyle='None', marker='.', markersize=3)
        plt.tight_layout()
        plt.savefig(dataview_path + '/' + 'hobo_%s_temperature.png'%site, bbox_inches='tight', dpi=100)

        fig = plt.figure()
        fig.set_size_inches(10,6)
        ax1 = fig.gca()
        plt.grid(axis='both', color='k', linestyle='--', linewidth=0.2)
        ax1.set_ylabel('Luminosity(lux)')
        plt.title('%s'%site)
        plt.plot(siteDatabase['Datetime'], siteDatabase['Luminosity(lux)'], linestyle='None', marker='.', markersize=3)
        plt.tight_layout()
        plt.savefig(dataview_path + '/' + 'hobo_%s_luminosity.png'%site, bbox_inches='tight', dpi=100)

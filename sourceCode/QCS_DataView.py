import re
import math
import numpy as np # type: ignore
import pandas as pd # type: ignore
import matplotlib.pyplot as plt # type: ignore
from matplotlib.lines import Line2D # type: ignore
####################################################################

def enable_scroll_zoom(fig):
    """Interaction for a shown panel: mouse-wheel zoom around the cursor,
    middle-button drag to pan, a 'Reset view' toolbar button that restores the
    original plotted limits, and removal of the redundant Zoom lens. Call it
    right before plt.show() (after all axes have their final limits)."""
    # snapshot the original plotted view for Reset
    original = [(ax, ax.get_xlim(), ax.get_ylim()) for ax in fig.axes]

    def on_scroll(event):
        ax = event.inaxes
        if ax is None:
            return
        scale = 1 / 1.2 if event.button == 'up' else 1.2   # wheel up = zoom in
        xlim, ylim = ax.get_xlim(), ax.get_ylim()
        xd, yd = event.xdata, event.ydata
        ax.set_xlim(xd - (xd - xlim[0]) * scale, xd + (xlim[1] - xd) * scale)
        ax.set_ylim(yd - (yd - ylim[0]) * scale, yd + (ylim[1] - yd) * scale)
        fig.canvas.draw_idle()

    pan = {'x': None, 'y': None, 'ax': None}

    def on_press(event):
        if event.button == 2 and event.inaxes is not None:   # 2 = middle button
            pan.update(x=event.xdata, y=event.ydata, ax=event.inaxes)

    def on_move(event):
        if pan['ax'] is None or event.inaxes is not pan['ax'] or event.xdata is None:
            return
        ax = pan['ax']
        dx, dy = event.xdata - pan['x'], event.ydata - pan['y']
        xlim, ylim = ax.get_xlim(), ax.get_ylim()
        ax.set_xlim(xlim[0] - dx, xlim[1] - dx)
        ax.set_ylim(ylim[0] - dy, ylim[1] - dy)
        fig.canvas.draw_idle()

    def on_release(event):
        if event.button == 2:
            pan['ax'] = None

    def reset_view(*_):
        for ax, xl, yl in original:
            ax.set_xlim(xl)
            ax.set_ylim(yl)
        fig.canvas.draw_idle()

    fig.canvas.mpl_connect('scroll_event', on_scroll)
    fig.canvas.mpl_connect('button_press_event', on_press)
    fig.canvas.mpl_connect('motion_notify_event', on_move)
    fig.canvas.mpl_connect('button_release_event', on_release)

    # toolbar: drop the Zoom lens and add a 'Reset view' button (best-effort,
    # backend-dependent - the interactions above work regardless)
    try:
        import tkinter as tk
        tb = fig.canvas.manager.toolbar
        zoom = getattr(tb, '_buttons', {}).get('Zoom')
        if zoom is not None:
            zoom.pack_forget()
        if not getattr(tb, '_qcs_reset_added', False):
            tk.Button(tb, text='Reset view', command=reset_view).pack(side='left', padx=4)
            tb._qcs_reset_added = True
    except Exception:
        pass

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
            rParam.append('CO₂ (ppm)')

        elif param == 'CO2 Level (ppm)':
            rParam.append('CO₂ (ppm)')

        elif param == 'O2 level (uM)':
            rParam.append('O₂ (µM)')

        elif param == 'O2 content (mg/L)':
            rParam.append('O₂ content (mg/L)')

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

def getParamColors (parameter_names=None):
    # Fixed variable -> color mapping used by EVERY plot in the software, so the
    # same variable always gets the same color in any panel or output figure.
    # cParam: light tone (data points) / bcParam: dark tone (trend lines, axes).
    # Hues were chosen to be strongly contrasting and intuitive
    # (temperature=red, chlorophyll=green, oxygen=blue, salinity=orange, etc).
    cParam =  {'Temperature (degC)': '#ff4d4d',                # red
                'Salinity (PSU)': '#ffa64d',                   # orange
                'Conductivity (mS/cm)': '#33cccc',             # teal
                'Density (kg/m3)': '#b380ff',                  # purple
                'CO2 level (ppm)': '#a6a6a6',                  # gray
                'CO2 Level (ppm)': '#a6a6a6',
                'O2 level (uM)': '#4d94ff',                    # blue
                'O2 content (mg/L)': '#4d94ff',                # blue
                'PAR (umol/m2/s)': '#ffd11a',                  # yellow
                'Turbidity (FTU)': '#bf8040',                  # brown
                'Chlorophyll (ug/L)': '#5cd65c',               # green
                'pH': '#ff66cc',                               # pink/magenta
                'Dissolved organic matter (ppb)': '#cccc29',   # olive
                'Soundspeed (m/s)': '#8585ad',                 # gray-blue
                'Pressure (dbar)': '#808080',                  # dark gray
                'Luminosity (lux)': '#f2c14e'                  # amber (HOBO light)
                }
    bcParam = {'Temperature (degC)': '#b30000',
                'Salinity (PSU)': '#cc6600',
                'Conductivity (mS/cm)': '#008080',
                'Density (kg/m3)': '#6600cc',
                'CO2 level (ppm)': '#595959',
                'CO2 Level (ppm)': '#595959',
                'O2 level (uM)': '#0047b3',
                'O2 content (mg/L)': '#0047b3',
                'PAR (umol/m2/s)': '#b38f00',
                'Turbidity (FTU)': '#734d26',
                'Chlorophyll (ug/L)': '#1f7a1f',
                'pH': '#cc0099',
                'Dissolved organic matter (ppb)': '#666614',
                'Soundspeed (m/s)': '#3d3d5c',
                'Pressure (dbar)': '#1a1a1a',
                'Luminosity (lux)': '#a3781f'
                }

    return cParam, bcParam

def getSiteColors (site_names):
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
                'B06': 'teal',
                'RH18': 'maroon',
                'RH30': 'darkslategrey'}
    
    # contrasting palette for sites without a predefined color; assignment is
    # deterministic (sorted by name), so each site keeps its color between plots
    extraColors = ['#e6194b', '#3cb44b', '#4363d8', '#f58231', '#911eb4',
                   '#42d4f4', '#f032e6', '#9a6324', '#000075', '#808000',
                   '#469990', '#aa6e28', '#800000', '#008080', '#e6beff']
    colors = {}
    n_extra = 0
    for site in sorted(site_names):
        if site in cSite:
            colors[site] = cSite[site]
        else:
            colors[site] = extraColors[n_extra % len(extraColors)]
            n_extra += 1
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
    cParam, bcParam = getParamColors()
    plot_color = bcParam.get(variable, '#1f77b4')
    display_name = renameParameters([variable])[0]
    fig = plt.figure()
    fig.set_size_inches(10,6)
    ax1 = fig.gca()
    plt.grid(axis='both', color='k', linestyle='--', linewidth=0.2)
    ax1.set_ylabel(display_name)
    ax1.plot(qualified_data['Datetime'], qualified_data[variable], marker='o', linestyle='none', markersize=2, color=plot_color, label='Approved data')

    #not_nan = np.asarray(qualified_data.index[~np.isnan(qualified_data[variable])])
    #mirror_var = raw_data.copy()
    #mirror_var.loc[not_nan, variable] = np.nan
    #ax1.plot(mirror_var['Datetime'], mirror_var[variable], marker='o', c='red', linestyle='none', markersize=2, label='Reproved data')

    # use only valid timestamps: a NaT at the edges would break the limits.
    # Limits come from the full first/last timestamps (day floor / day ceiling),
    # so deployments crossing a new year keep a valid, increasing X axis.
    valid_times = qualified_data['Datetime'].dropna()
    t_start = valid_times.iloc[0]
    t_end = valid_times.iloc[-1]
    x_inflim = t_start.normalize()
    x_suplim = t_end.normalize() + pd.Timedelta(hours=23, minutes=59)
    ax1.set_xlim(x_inflim, x_suplim)

    if fixed_scale == True:
        if re.search('temperature', variable, re.IGNORECASE):
            ax1.set_ylim(SETTINGS['env_min_temp'], SETTINGS['env_max_temp'])
        elif re.search('salinity', variable, re.IGNORECASE):
            ax1.set_ylim(SETTINGS['env_min_sal'], SETTINGS['env_max_sal'])
        elif re.search('conductivity', variable, re.IGNORECASE):
            ax1.set_ylim(SETTINGS['env_min_cond'], SETTINGS['env_max_cond'])
        elif re.search('pressure', variable, re.IGNORECASE):
            ax1.set_ylim(SETTINGS['env_min_pres'], SETTINGS['env_max_pres'])
        elif re.search('pH', variable):
            ax1.set_ylim(SETTINGS['env_min_pH'], SETTINGS['env_max_pH'])
        elif re.search('chlorophyll', variable, re.IGNORECASE):
            ax1.set_ylim(SETTINGS['env_min_chl'], SETTINGS['env_max_chl'])
        elif re.search('O2', variable, re.IGNORECASE):
            ax1.set_ylim(SETTINGS['env_min_O2'], SETTINGS['env_max_O2'])
        elif re.search('organic matter', variable, re.IGNORECASE):
            ax1.set_ylim(SETTINGS['env_min_org'], SETTINGS['env_max_org'])
        elif re.search('turbidity', variable, re.IGNORECASE):
            ax1.set_ylim(SETTINGS['env_min_tur'], SETTINGS['env_max_tur'])
        elif re.search('luminosity|lux', variable, re.IGNORECASE):
            ax1.set_ylim(SETTINGS.get('env_min_lux', 0), SETTINGS.get('env_max_lux', 20000))

    if re.search('depth', variable, re.IGNORECASE):
        ax1.invert_yaxis()

    ax1.set_title('Site: %s   /   %s  to  %s' % (qualified_data['Site'].iloc[0],
                                                 t_start.strftime('%d/%m/%Y'),
                                                 t_end.strftime('%d/%m/%Y')))
    plt.savefig(dataview_path + '/' + re.search(r'^[^\(]+',variable, re.IGNORECASE).group().strip() + ' series.svg', bbox_inches='tight', dpi=100)
    plt.close(fig)

def plot_variable_profile(qualified_data, raw_data, variable, dataview_path, SETTINGS, fixed_scale):
    cParam, bcParam = getParamColors()
    plot_color = bcParam.get(variable, '#1f77b4')
    display_name = renameParameters([variable])[0]
    fig = plt.figure()
    fig.set_size_inches(10,6)
    ax1 = fig.gca()
    plt.grid(axis='both', color='k', linestyle='--', linewidth=0.2)
    ax1.set_xlabel(display_name)
    ax1.plot(qualified_data[variable], qualified_data['Depth (m)'], marker='o', linestyle='none', markersize=2, color=plot_color, label='Approved data')
    ax1.set_ylabel('Depth (m)')

    valid_times = qualified_data['Datetime'].dropna()
    year = valid_times.iloc[0].year
    month = valid_times.iloc[0].month

    if fixed_scale == True:
        if re.search('temperature', variable, re.IGNORECASE):
            ax1.set_xlim(SETTINGS['env_min_temp'], SETTINGS['env_max_temp'])
        elif re.search('salinity', variable, re.IGNORECASE):
            ax1.set_xlim(SETTINGS['env_min_sal'], SETTINGS['env_max_sal'])
        elif re.search('conductivity', variable, re.IGNORECASE):
            ax1.set_xlim(SETTINGS['env_min_cond'], SETTINGS['env_max_cond'])
        elif re.search('pressure', variable, re.IGNORECASE):
            ax1.set_xlim(SETTINGS['env_min_pres'], SETTINGS['env_max_pres'])
        elif re.search('pH', variable):
            ax1.set_xlim(SETTINGS['env_min_pH'], SETTINGS['env_max_pH'])
        elif re.search('chlorophyll', variable, re.IGNORECASE):
            ax1.set_xlim(SETTINGS['env_min_chl'], SETTINGS['env_max_chl'])
        elif re.search('O2', variable, re.IGNORECASE):
            ax1.set_xlim(SETTINGS['env_min_O2'], SETTINGS['env_max_O2'])
        elif re.search('organic matter', variable, re.IGNORECASE):
            ax1.set_xlim(SETTINGS['env_min_org'], SETTINGS['env_max_org'])
        elif re.search('turbidity', variable, re.IGNORECASE):
            ax1.set_xlim(SETTINGS['env_min_tur'], SETTINGS['env_max_tur'])
        elif re.search('luminosity|lux', variable, re.IGNORECASE):
            ax1.set_xlim(SETTINGS.get('env_min_lux', 0), SETTINGS.get('env_max_lux', 20000))

    maxProf = qualified_data['Depth (m)'].max()
    maxY = math.ceil(maxProf / 10) * 10

    ax1.set_ylim(0, maxY)

    ax1.invert_yaxis()
    ax1.set_title('Site: %s  /   year: %s   /  month: %s'%(qualified_data['Site'].iloc[0], year, month))
    plt.savefig(dataview_path + '/' + re.search(r'^[^\(]+',variable, re.IGNORECASE).group().strip() + ' profile.svg', bbox_inches='tight', dpi=100)
    plt.close(fig)

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
                raise ValueError('Empty sequence for both semesters in current combination of selected sites and year. Double check inputs or select different sites/year.')
        except ValueError as e:
            print('SelectionError:', e)
        for semester in db.keys():
            # define list of dataframes for y axis parameters
            y_list, cParam, bcParam, parameter_names = setParam (dataViewSettings, db, semester, site)
            rParam = renameParameters(parameter_names)
            if len(y_list) > 0:
                fig, ax1 = plt.subplots(figsize=(980 / 100, 500 / 100))
                plt.xticks(rotation=35)
                plt.subplots_adjust(left=0.050, right=0.620)
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
                    ax1.set_ylim(([yp.min() - 0.05 * np.abs(yp.max()-yp.min()), yp.max() + 0.05 * np.abs(yp.max()-yp.min())]))
                else:
                    ax1.plot(x, y, color=bcParam[y_list[0].name], linestyle='None', marker='.', label=rParam[0])
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
                if dataViewSettings['fixedScale'] == True and parameter_names[0] in dataViewSettings['scaleSettings']:
                    ax1.set_ylim(dataViewSettings['scaleSettings'][parameter_names[0]]['min'], dataViewSettings['scaleSettings'][parameter_names[0]]['max'])
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
                    if fit_lin_regression == True and y_list[i-1].name != 'Pressure (dbar)':
                        xp, yp = linear_regression (y, degree=deg)
                        if points == True:
                            ax.plot(x, y, linestyle='none', marker='.', markersize=3, c=cParam[y_list[i-1].name], label=rParam[i-1])
                        ax.plot(xp, yp, linestyle='-', c=bcParam[y_list[i-1].name], label=rParam[i-1])
                        ax.set_ylim(([yp.min() - 0.05 * np.abs(yp.max()-yp.min()), yp.max() + 0.05 * np.abs(yp.max()-yp.min())]))

                    else:
                        if y_list[i-1].name == 'Pressure (dbar)':
                            ax.plot(x, y, linestyle='--', marker='None', c=bcParam[y_list[i-1].name], label=rParam[i-1])
                        else:
                            ax.plot(x, y, linestyle='None', marker='.', c=bcParam[y_list[i-1].name], label=rParam[i-1])
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
                    if dataViewSettings['fixedScale'] == True and parameter_names[i-1] in dataViewSettings['scaleSettings']:
                        ax.set_ylim(dataViewSettings['scaleSettings'][parameter_names[i-1]]['min'], dataViewSettings['scaleSettings'][parameter_names[i-1]]['max'])
            #if slice.empty:
            #    pass
            #else:
                # optional fixed time window standardizes the X axis across plots
                if dataViewSettings.get('xAxisStart') is not None and dataViewSettings.get('xAxisEnd') is not None:
                    ax1.set_xlim(pd.Timestamp(dataViewSettings['xAxisStart']),
                                 pd.Timestamp(dataViewSettings['xAxisEnd']))
                #defining data format
                plt.gca().xaxis.set_major_formatter(plt.matplotlib.dates.DateFormatter('%d/%m %H:%M'))
                plt.savefig('panel1_%s_%s_%d.svg'%(site, semester, year), bbox_inches='tight')
                enable_scroll_zoom(fig)
                plt.show()

def plot_database_panel2(database, dataViewSettings):
    """
    Generates time series plots for multiple parameters and sites, adapted for deployments of up to 48 hours.

    Parameters:
        database (DataFrame): DataFrame containing the data to be plotted
        dataViewSettings (dict): Dictionary with visualization settings containing:
            - siteList: list of sites/locations
            - parameterList: list of parameters
            - filterByYear: year to filter by
            - tendencyLines: bool for trend lines
            - linearRegressionDegree: regression degree
            - viewDataPoints: bool to show points
            - fixedScale: bool for fixed scale
            - scaleSettings: scale settings

    Returns:
        None (generates and saves plots as SVG files)
    """
    # Extract settings
    site_names = dataViewSettings['siteList']
    parameter_names = dataViewSettings['parameterList']
    year = dataViewSettings['filterByYear']
    fit_lin_regression = dataViewSettings['tendencyLines']
    deg = dataViewSettings['linearRegressionDegree']
    points = dataViewSettings['viewDataPoints']  
    
    # Data pre-processing
    db_raw = database.copy()
    db_raw = db_raw[(db_raw['Datetime'].dt.year == year)]
    db_raw.index = db_raw['Datetime']
    db_raw = db_raw.rename_axis('dt_index')
    db_raw = db_raw.sort_values(by='dt_index')

    # Color configuration
    colors = getSiteColors(site_names)
    rParam = renameParameters(parameter_names)

    # Split by semesters
    db = {
        '1stSemester': db_raw[(db_raw.loc[:,'Datetime'].dt.month >= 1) & (db_raw.loc[:,'Datetime'].dt.month <= 6)],
        '2ndSemester': db_raw[(db_raw.loc[:,'Datetime'].dt.month >= 7) & (db_raw.loc[:,'Datetime'].dt.month <= 12)]
    }

    # Main plotting loop
    for semester in db.keys():
        for parameter in parameter_names:
            display_param = rParam[parameter_names.index(parameter)]
            fig, ax1 = plt.subplots(figsize=(980/100, 500/100))
            plt.title(f'{display_param} on {semester} for each site - {year}')
            plt.grid(True, linestyle='dotted', linewidth=0.5)
            ax1.set_ylabel(display_param)
            control = 0
            
            for site in site_names:
                # Extract data for the specific site
                y = db[semester].copy()
                y = y[parameter][(y.loc[:,'Site'] == site)]
                y = y.loc[~(y.index.duplicated(keep=False) & y.isna())]
                
                if y.empty:
                    print(f'\nNo {parameter} data for {site} during {year} {semester}.')
                    continue
                
                control += 1
                y, gap_ids = fill_NaT_gap(y)  # Fill gaps

                # Compute elapsed hours since the start of the deployment (or since
                # the start of the fixed time window, when defined by the user)
                x_start = dataViewSettings.get('xAxisStart')
                time_origin = pd.Timestamp(x_start) if x_start is not None else y.index.min()
                x_hours = (y.index - time_origin).total_seconds() / 3600  # Convert to hours

                # Plotting the data
                if fit_lin_regression:
                    xp, yp = linear_regression(y, degree=deg)
                    xp_hours = (xp - time_origin).total_seconds() / 3600
                    
                    if points:
                        ax1.plot(x_hours, y, linestyle='none', marker='.', 
                                color=colors[site], markersize=3, label=f'{site} data')
                        ax1.plot(xp_hours, yp, linestyle='-', 
                                color=colors[site], label=f'{site} tendency')
                    else:
                        ax1.plot(xp_hours, yp, linestyle='-', 
                                color=colors[site], label=f'{site} tendency')
                else:
                        ax1.plot(x_hours, y, linestyle='none', marker='.', 
                                color=colors[site], markersize=3, label=f'{site} data')
            
            # Plot settings
            if control == 0:
                plt.close(fig)
                continue
                
            x_start = dataViewSettings.get('xAxisStart')
            x_end = dataViewSettings.get('xAxisEnd')
            if x_start is not None and x_end is not None:
                # user-defined window: same X axis in every plot, even where
                # there is no data, so different sites/files can be compared
                total_hours = (pd.Timestamp(x_end) - pd.Timestamp(x_start)).total_seconds() / 3600
                tick_step = max(1, int(round(total_hours / 8)))
                ax1.set_xlabel('Elapsed Time (hours) since %s' % pd.Timestamp(x_start).strftime('%d/%m/%Y %H:%M'))
                ax1.set_xlim(0, total_hours)
                ax1.set_xticks(np.arange(0, total_hours + tick_step * 0.5, tick_step))
            else:
                ax1.set_xlabel('Elapsed Time (hours)')
                ax1.set_xlim(0, 48)  # default: 48 hours
                ax1.set_xticks(np.arange(0, 49, 6))  # Ticks every 6 hours

            # Legend and layout
            ax1.legend(loc='upper left', bbox_to_anchor=(1, 1.01), fontsize=7)
            plt.subplots_adjust(left=0.06, right=0.80, top=0.88, bottom=0.11)

            # Fixed scale if needed
            if dataViewSettings['fixedScale'] and parameter in dataViewSettings['scaleSettings']:
                ax1.set_ylim(dataViewSettings['scaleSettings'][parameter]['min'],
                            dataViewSettings['scaleSettings'][parameter]['max'])

            # Strip parentheses from the file name
            parameter_r = re.sub(r'\([^()]*\)', '', parameter).strip()
            plt.savefig(f'panel2_{parameter_r}_{semester}_{year}.svg')
            enable_scroll_zoom(fig)
            plt.show()

def plot_database_panel3(database, dataViewSettings):
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
                raise ValueError('Empty sequence for both semesters in current combination of selected sites and year. Double check inputs or select different sites/year.')
        except ValueError as e:
            print('SelectionError:', e)
        for semester in db.keys():
            x_list, cParam, bcParam, parameter_names = setParam(dataViewSettings, db, semester, site)
            rParam = renameParameters(parameter_names)
            if len(x_list) > 0:
                figHeight = 500
                fig, ax1 = plt.subplots(figsize=(980 / 100, figHeight / 100))
                plt.subplots_adjust(left=0.050, right=0.840, top=0.950, bottom=0.500)
                ax1.invert_yaxis()
                plt.grid(True, axis='y', linestyle='dotted', linewidth=0.5)
                
                # Create legend handles and labels
                legend_handles = []
                legend_labels = []
                
                # Process first parameter
                x = x_list[0].loc[~(x_list[0].index.duplicated(keep=False) & x_list[0].isna())]
                x, gap_ids = fill_NaT_gap(x)
                x.name = x_list[0].name
                y = (db[semester]['Depth (m)']).loc[~(x_list[0].index.duplicated(keep=False) & x_list[0].isna())]
                sorted_df = pd.concat([x,y], axis=1).sort_values(by='Depth (m)')
                x, y = (sorted_df[x.name], sorted_df[y.name])
                
                # Plot first parameter
                if fit_lin_regression == True:
                    yp, xp = linear_regression_profile(x, y, degree=deg)
                    if points == True:
                        points_line = ax1.plot(x, y, color=cParam[x_list[0].name], linestyle='none', marker='.', markersize=3)
                    trend_line = ax1.plot(xp, yp, color=bcParam[x_list[0].name], linestyle='-')
                    legend_handles.append(trend_line[0])
                else:
                    points_line = ax1.plot(x, y, color=cParam[x_list[0].name], linestyle='none', marker='.', markersize=3)
                    legend_handles.append(points_line[0])
                legend_labels.append(rParam[0])
                
                # Configure first axis
                ax1.set_xlabel('')  # Remove x-axis label but keep ticks
                ax1.set_ylabel('Depth (m)')
                ax1.set_title('Parameters for %s over %s during %s'%(site, semester, year))
                # optional fixed depth axis (shallow at top, deep at bottom)
                if dataViewSettings.get('depthAxisMin') is not None and dataViewSettings.get('depthAxisMax') is not None:
                    ax1.set_ylim(dataViewSettings['depthAxisMax'], dataViewSettings['depthAxisMin'])
                else:
                    ax1.set_ylim(ymax=0)
                marginMax = 0.01 * x.max()
                ax1.set_xlim(xmax=x.max() + marginMax)
                
                # Style first axis
                ax1.spines['bottom'].set_color(bcParam[x_list[0].name])
                ax1.spines['bottom'].set_linewidth(1.5)
                ax1.tick_params(axis='x', which='both', colors=bcParam[x_list[0].name])
                
                # Process additional parameters
                axes = {'y1': ax1}
                spineOffset = 25
                if dataViewSettings['fixedScale'] == True and parameter_names[0] in dataViewSettings['scaleSettings']:
                    ax1.set_xlim(dataViewSettings['scaleSettings'][parameter_names[0]]['min'], dataViewSettings['scaleSettings'][parameter_names[0]]['max'])

                for i, x in enumerate(x_list[1:], start=2):
                    # Create additional axis
                    ax = ax1.twiny()
                    
                    # Configure ticks (show ticks but hide labels)
                    ax.tick_params(axis='x', which='both', colors=bcParam[x_list[i-1].name], 
                                 top=False, bottom=True, labeltop=False, labelbottom=True,
                                 direction='out')
                    
                    # Style axis spine
                    ax.spines['bottom'].set_position(('outward', spineOffset))
                    ax.spines['bottom'].set_color(bcParam[x_list[i-1].name])
                    ax.spines['bottom'].set_linewidth(1.5)
                    spineOffset += 25
                    
                    # Remove x label
                    ax.set_xlabel('')
                    
                    # Process data
                    x = x.loc[~(x.index.duplicated(keep=False) & x.isna())]
                    x, gap_ids = fill_NaT_gap(x)
                    x.name = x_list[i-1].name
                    y = (db[semester]['Depth (m)']).loc[~(x_list[i-1].index.duplicated(keep=False) & x_list[i-1].isna())]
                    sorted_df = pd.concat([x,y], axis=1).sort_values(by='Depth (m)')
                    x, y = (sorted_df[x.name], sorted_df[y.name])
                    
                    # Plot data
                    if fit_lin_regression == True:
                        yp, xp = linear_regression_profile(x, y, degree=deg)
                        xp[np.where(xp<0)[0]] = np.nan
                        if points == True:
                            ax.plot(x, y, linestyle='none', marker='.', markersize=3, c=cParam[x_list[i-1].name])
                        trend_line = ax.plot(xp, yp, linestyle='-', c=bcParam[x_list[i-1].name])
                        legend_handles.append(trend_line[0])
                    else:
                        points_line = ax.plot(x, y, linestyle='none', marker='.', markersize=3, c=cParam[x_list[i-1].name])
                        legend_handles.append(points_line[0])
                    legend_labels.append(rParam[i-1])
                    
                    # Configure axis limits
                    axes[f'y{i}'] = ax
                    if dataViewSettings.get('depthAxisMin') is not None and dataViewSettings.get('depthAxisMax') is not None:
                        ax.set_ylim(dataViewSettings['depthAxisMax'], dataViewSettings['depthAxisMin'])
                    else:
                        ax.set_ylim(ymax=0)
                    if fit_lin_regression == True: 
                        xRange = xp.max() - xp.min()  
                        marginMax = 0.01 * xRange
                        ax.set_xlim(xmax=xp.max() + marginMax)   
                    else:            
                        xRange = x.max() - x.min() 
                        marginMax = 0.01 * xRange
                        ax.set_xlim(xmax=x.max() + marginMax)      

                    if dataViewSettings['fixedScale'] == True and parameter_names[i-1] in dataViewSettings['scaleSettings']:
                        ax.set_xlim(dataViewSettings['scaleSettings'][parameter_names[i-1]]['min'], dataViewSettings['scaleSettings'][parameter_names[i-1]]['max'])

                # Add unified legend
                ax1.legend(handles=legend_handles, labels=legend_labels,
                          loc='upper center', bbox_to_anchor=(1.1, 1.01),
                          ncol=1, fontsize=7)
                
                plt.savefig('panel3_%s_%s_%d.svg'%(site, semester, year))
                enable_scroll_zoom(fig)
                plt.show()

def plot_light_window(lux_info, site=''):
    """Daily envelope of the HOBO light with baseline and fouling threshold.
    The parameters used are written ON the plot (traceability of the cutoff).
    Returns (fig, ax); the cutoff is drawn separately by mark_light_cutoff."""
    daily_peak = lux_info['daily_peak']
    params = lux_info['params']
    fig, ax = plt.subplots(figsize=(11, 5.5))
    ax.plot(daily_peak.index, daily_peak.values, '-', marker='.', ms=4,
            color='#b38f00', lw=1.2, label='Daily light peak')
    if np.isfinite(lux_info.get('baseline', np.nan)):
        ax.axhline(lux_info['baseline'], color='#1f7a1f', lw=1.2, linestyle='--',
                   label='Clean-sensor baseline (%.0f lux)' % lux_info['baseline'])
        ax.axhline(lux_info['threshold'], color='#b30000', lw=1.2, linestyle=':',
                   label='Fouling threshold (%.0f lux)' % lux_info['threshold'])
    ax.set_yscale('log')
    ax.set_ylabel('Lux (log scale)')
    ax.grid(alpha=0.3)
    ax.legend(loc='lower left', fontsize=8)
    ax.set_title('%s - light usable window (fouling)' % (site or 'HOBO'))
    # cutoff parameters visible on the plot itself
    rule_text = ('Rule: baseline = max daily peak of the first %d day(s); light becomes BAD '
                 'from the start of the FINAL run (>= %d day(s)) where the daily peak stays below '
                 '%.0f%% of the baseline and never recovers to it.  '
                 '[Settings: lux_baseline_days / lux_cutoff_frac / lux_sustain_days]'
                 % (params['baseline_days'], params['sustain_days'], 100 * params['cutoff_frac']))
    fig.text(0.5, 0.015, rule_text, ha='center', fontsize=7.5, color='#444444', wrap=True)
    fig.subplots_adjust(bottom=0.17)
    return fig, ax


def mark_light_cutoff(ax, cutoff, lux_info):
    """Draws (or redraws) the cutoff date on the light window plot.
    Returns the list of created artists so the caller can remove them."""
    artists = []
    daily_peak = lux_info['daily_peak']
    if cutoff is not None and len(daily_peak):
        artists.append(ax.axvline(cutoff, color='#b30000', lw=1.6))
        artists.append(ax.axvspan(cutoff, daily_peak.index.max(), color='#b30000', alpha=0.10))
        artists.append(ax.text(cutoff, ax.get_ylim()[1],
                               ' cutoff: %s' % pd.Timestamp(cutoff).strftime('%Y-%m-%d %H:%M'),
                               color='#b30000', fontsize=9, va='top'))
    else:
        artists.append(ax.text(0.02, 0.99, 'no cutoff: light usable for the whole deployment',
                               transform=ax.transAxes, color='#1f7a1f', fontsize=9, va='top'))
    # the non-monotonic recovery warning shows whether or not a cutoff was set
    if lux_info.get('recovers'):
        artists.append(ax.text(
            0.5, 0.94,
            'WARNING: the light dips and recovers (%.0f%% of later days reach the threshold) -\n'
            'not clean biofouling (possible cleaning / multiple deployments). Review!'
            % (100 * lux_info.get('recovery_day_frac_after', 0)),
            transform=ax.transAxes, ha='center', va='top', fontsize=8.5,
            color='#b30000', weight='bold',
            bbox=dict(boxstyle='round', facecolor='#fff0f0', edgecolor='#b30000')))
    return artists


def _hobo_site_slice (database, year, site):
    """Slice by year and site used by the HOBO panels (same annual slicing
    rule as the Seaguard panels), sorted in time."""
    db = database.copy()
    db = db[(db['Datetime'].dt.year == year) & (db['Site'] == site)]
    return db.sort_values('Datetime')


def _hobo_light_cutoff_start (db):
    """First instant with Flag_lux == 4 (start of the fouling window),
    or None if the light is usable for the entire plotted period."""
    flag_lux = pd.to_numeric(db['Flag_lux'], errors='coerce')
    flagged_times = db.loc[flag_lux == 4, 'Datetime']
    if flagged_times.empty:
        return None
    return flagged_times.iloc[0]


def _apply_hobo_common_settings (ax, dataViewSettings):
    """Optional fixed X-axis time window (same option as panels 1/2)
    and a date format suited to multi-month deployments."""
    if dataViewSettings.get('xAxisStart') is not None and dataViewSettings.get('xAxisEnd') is not None:
        ax.set_xlim(pd.Timestamp(dataViewSettings['xAxisStart']),
                    pd.Timestamp(dataViewSettings['xAxisEnd']))
    ax.xaxis.set_major_formatter(plt.matplotlib.dates.DateFormatter('%d/%m/%Y'))


def _mask_nonpositive_lux (lux, site):
    """A log scale cannot represent values <= 0 (night readings): they become
    gaps in the plot. The total omitted is always reported to the console."""
    n_nonpositive = int((lux <= 0).sum())
    if n_nonpositive:
        print('MESSAGE: %d light reading(s) <= 0 lux for %s omitted from the log-scale plot (night readings).'
              % (n_nonpositive, site))
    return lux.where(lux > 0)


def plot_hobo_temperature (database, dataViewSettings, site):
    """Time series of the HOBO temperature for a site, with the
    suspect/bad points (Flag_T >= 3) highlighted, as in the Seaguard."""
    year = dataViewSettings['filterByYear']
    cParam, bcParam = getParamColors()
    db = _hobo_site_slice(database, year, site)
    if db.empty:
        print('\nNo HOBO data for %s during %d.' % (site, year))
        return
    temp = pd.to_numeric(db['Temperature (degC)'], errors='coerce')
    flag_t = pd.to_numeric(db['Flag_T'], errors='coerce')

    fig, ax = plt.subplots(figsize=(980 / 100, 500 / 100))
    plt.xticks(rotation=35)
    ax.grid(True, linestyle='dotted', linewidth=0.5)
    ax.plot(db['Datetime'], temp, linestyle='None', marker='.', markersize=3,
            color=bcParam['Temperature (degC)'], label='Temperature')
    # highlight: flags 3 (suspect) and 4 (bad); 9 = missing, not highlighted
    flagged = flag_t.isin([3, 4])
    if flagged.any():
        ax.plot(db.loc[flagged, 'Datetime'], temp[flagged], linestyle='None',
                marker='x', markersize=5, color='black',
                label='Suspect/bad (Flag_T >= 3)')
    ax.set_ylabel(renameParameters(['Temperature (degC)'])[0])
    ax.set_title('HOBO temperature for %s during %d' % (site, year))
    if dataViewSettings.get('fixedScale') and 'Temperature (degC)' in dataViewSettings.get('scaleSettings', {}):
        ax.set_ylim(dataViewSettings['scaleSettings']['Temperature (degC)']['min'],
                    dataViewSettings['scaleSettings']['Temperature (degC)']['max'])
    _apply_hobo_common_settings(ax, dataViewSettings)
    ax.legend(fontsize=8)
    plt.savefig('hobo_temperature_%s_%d.svg' % (site, year), bbox_inches='tight')
    enable_scroll_zoom(fig)
    plt.show()


def plot_hobo_light (database, dataViewSettings, site):
    """Time series of the HOBO light (log scale) for a site, with the region
    after the fouling cutoff (Flag_lux == 4) shaded - same visual language
    as the QCS_light_window.svg generated during qualification."""
    year = dataViewSettings['filterByYear']
    cParam, bcParam = getParamColors()
    db = _hobo_site_slice(database, year, site)
    if db.empty:
        print('\nNo HOBO data for %s during %d.' % (site, year))
        return
    lux = _mask_nonpositive_lux(pd.to_numeric(db['Luminosity (lux)'], errors='coerce'), site)

    fig, ax = plt.subplots(figsize=(980 / 100, 500 / 100))
    plt.xticks(rotation=35)
    ax.grid(True, linestyle='dotted', linewidth=0.5)
    ax.plot(db['Datetime'], lux, linestyle='None', marker='.', markersize=3,
            color=bcParam['Luminosity (lux)'], label='Luminosity')
    ax.set_yscale('log')
    ax.set_ylabel('Luminosity (lux, log scale)')
    ax.set_title('HOBO light for %s during %d' % (site, year))
    if dataViewSettings.get('fixedScale') and 'Luminosity (lux)' in dataViewSettings.get('scaleSettings', {}):
        lim = dataViewSettings['scaleSettings']['Luminosity (lux)']
        if lim['min'] > 0:
            ax.set_ylim(lim['min'], lim['max'])
        else:
            print('WARNING: fixed scale for Luminosity ignored (min must be > 0 on a log axis).')
    _apply_hobo_common_settings(ax, dataViewSettings)

    # fouling window: same colors as mark_light_cutoff (qualification)
    cutoff = _hobo_light_cutoff_start(db)
    if cutoff is not None:
        ax.axvline(cutoff, color='#b30000', lw=1.6)
        ax.axvspan(cutoff, db['Datetime'].iloc[-1], color='#b30000', alpha=0.10,
                   label='Fouling window (Flag_lux == 4)')
        ax.text(cutoff, ax.get_ylim()[1], ' cutoff: %s' % pd.Timestamp(cutoff).date(),
                color='#b30000', fontsize=9, va='top')
    else:
        ax.text(0.02, 0.99, 'no cutoff: light usable for the whole deployment',
                transform=ax.transAxes, color='#1f7a1f', fontsize=9, va='top')

    ax.legend(fontsize=8, loc='lower left')
    plt.savefig('hobo_light_%s_%d.svg' % (site, year), bbox_inches='tight')
    enable_scroll_zoom(fig)
    plt.show()


def plot_hobo_light_multisite (database, dataViewSettings):
    """Multi-site comparison of the HOBO light (log scale). The start of each
    site's fouling window (first Flag_lux == 4) is marked with a dashed
    vertical line in the site's color, to compare when fouling
    started at each one."""
    year = dataViewSettings['filterByYear']
    site_names = dataViewSettings['siteList']
    colors = getSiteColors(site_names)

    fig, ax = plt.subplots(figsize=(980 / 100, 500 / 100))
    plt.xticks(rotation=35)
    ax.grid(True, linestyle='dotted', linewidth=0.5)
    plotted_sites = 0
    for site in site_names:
        db = _hobo_site_slice(database, year, site)
        if db.empty:
            print('\nNo HOBO data for %s during %d.' % (site, year))
            continue
        lux = _mask_nonpositive_lux(pd.to_numeric(db['Luminosity (lux)'], errors='coerce'), site)
        ax.plot(db['Datetime'], lux, linestyle='None', marker='.', markersize=3,
                color=colors[site], label=site)
        cutoff = _hobo_light_cutoff_start(db)
        if cutoff is not None:
            ax.axvline(cutoff, color=colors[site], lw=1.4, linestyle='--',
                       label='%s cutoff (%s)' % (site, pd.Timestamp(cutoff).date()))
        plotted_sites += 1
    if plotted_sites == 0:
        plt.close(fig)
        print('\nNo HOBO data for any selected site during %d.' % year)
        return
    ax.set_yscale('log')
    ax.set_ylabel('Luminosity (lux, log scale)')
    ax.set_title('HOBO light comparison between sites during %d' % year)
    if dataViewSettings.get('fixedScale') and 'Luminosity (lux)' in dataViewSettings.get('scaleSettings', {}):
        lim = dataViewSettings['scaleSettings']['Luminosity (lux)']
        if lim['min'] > 0:
            ax.set_ylim(lim['min'], lim['max'])
        else:
            print('WARNING: fixed scale for Luminosity ignored (min must be > 0 on a log axis).')
    _apply_hobo_common_settings(ax, dataViewSettings)
    ax.legend(fontsize=8, loc='lower left')
    plt.savefig('hobo_light_multisite_%d.svg' % year, bbox_inches='tight')
    enable_scroll_zoom(fig)
    plt.show()

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
            raise ValueError('Empty sequence for both semesters in current combination of selected sites and year. Double check inputs or select different sites/year.')
    except ValueError as e:
        print('SelectionError:', e)
    
    # working with one semester at a time
    for semester in db.keys():
        if semester in emptySemester:
            pass
        else:
            ###### create figure and contour lines
            fig = plt.figure(figsize=(980 / 100, 500 / 100))  # Create figure with specified resolution
            ax = fig.add_subplot(111)  # Create axes
            # selecting semester
            tspSemesterData = db[semester][['Pressure (dbar)', 'Depth (m)', 'Temperature (degC)', 'Salinity (PSU)', 'Site']].copy()
            # Convert temperature, salinity, and pressure data to arrays
            salt = np.asarray(tspSemesterData['Salinity (PSU)'].copy())
            temp = np.asarray(tspSemesterData['Temperature (degC)'].copy())
            p = np.asarray(tspSemesterData['Pressure (dbar)'].copy())
            depth = np.asarray(tspSemesterData['Depth (m)'].copy())
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
            cbar = fig.colorbar(cm.ScalarMappable(norm=norm, cmap=cm.plasma.reversed()), label='Depth (m)', ax=ax, location='right')
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
                        ax.scatter(tspData['Absolute Salinity (PSU)'], tspData['Conservative Temperature (degC)'], marker=markerList[a], c=tspData['Depth (m)'], lw=0, cmap=cm.plasma.reversed(), norm=norm, label=site)
                        ax.set_xlabel('Absolute Salinity (kg/m³)')  # Label x-axis
                        ax.set_ylabel('Conservative Temperature (C°)')  # Label y-axis
                    elif re.search('potential', tsParam, re.IGNORECASE):
                        ax.scatter(tspData['Salinity (PSU)'], tspData['Potential Temperature (degC)'], marker=markerList[a], c=tspData['Depth (m)'], lw=0, cmap=cm.plasma.reversed(), norm=norm, label=site)
                        ax.set_xlabel('Salinity (PSU)')  # Label x-axis
                        ax.set_ylabel('Potential Temperature (C°)')  # Label y-axis

                    plt.subplots_adjust(top=0.9, bottom=0.1, left=0.05, right=0.96)  # Adjust image spacing
                    a += 1
            # title and file name list every plotted site, not only the last one
            sites_label = '-'.join(site_names)
            ax.set_title('T-S Diagram for %s over %s during %s'%(sites_label, semester, year))
            custom_handles = []
            for a in range(len(site_names)):
                custom_handles.append(Line2D([0], [0], linestyle='None', marker=markerList[a], label=site_names[a], markeredgecolor='black', markerfacecolor='black', markersize=6))
            plt.legend(handles=custom_handles)  # Draw legend
            plt.savefig('TS_Diagram_%s_%s_%d.svg'%(sites_label, semester, year))
            enable_scroll_zoom(fig)
            plt.show()



import re
import math
import numpy as np # type: ignore
import pandas as pd # type: ignore
import datetime as _dt # type: ignore
import matplotlib.pyplot as plt # type: ignore
import matplotlib.dates as _mdates # type: ignore
from matplotlib.lines import Line2D # type: ignore
from matplotlib.ticker import MaxNLocator # type: ignore
import QCS_Theme as _theme


def show_panels(figures=None, browse=False):
    """Puts the panels produced so far on screen.

    A hook, not a helper: the tk shell keeps matplotlib's own windows
    (`plt.show()`); the Qt shell replaces it, because it runs on the Agg
    backend - where `plt.show()` does nothing at all - and opens the figures in
    its own windows instead (app icon, real title, navigation toolbar). The
    batch drivers leave it alone: with no display, `plt.show()` is already a
    no-op there.

    figures: the exact figures to show. None means 'every figure pyplot holds',
             which is what the scalar and HOBO panels rely on.
    browse:  ask the shell for ONE window paging through the figures instead of
             one window per figure (owner, v13.0: the four current panels
             opened as four windows, which is noise for a comparison). Only a
             request - a shell that cannot page them shows them side by side.
    """
    plt.show()

####################################################################

# Safe bounds for a matplotlib DATE axis (well inside the hard year 1..9999
# limit). Zoom/pan is clamped to these so panning a time axis far out does not
# produce an out-of-range date ordinal that crashes the tick formatter.
_DATE_MIN = _mdates.date2num(_dt.datetime(100, 1, 1))
_DATE_MAX = _mdates.date2num(_dt.datetime(9000, 1, 1))

def _apply_time_window(df, dataViewSettings):
    """Keep only the rows inside the chosen X-axis time window (start/end), so the
    mooring plots actually show ONLY those hours (and the y-axis / trend lines fit
    that window) instead of merely zooming into the full series."""
    xs = dataViewSettings.get('xAxisStart')
    xe = dataViewSettings.get('xAxisEnd')
    if xs is not None and xe is not None and 'Datetime' in df.columns:
        return df[(df['Datetime'] >= pd.Timestamp(xs)) & (df['Datetime'] <= pd.Timestamp(xe))]
    return df


def _clamp_x(ax, lo, hi):
    """Keep x-limits inside the valid date range when `ax` is a date axis,
    preserving the span (shift the window back in) so a big pan cannot invert or
    collapse it or crash the date-tick formatter."""
    try:
        if isinstance(ax.xaxis.get_major_locator(), _mdates.DateLocator):
            span = hi - lo
            if lo < _DATE_MIN:
                lo, hi = _DATE_MIN, _DATE_MIN + span
            if hi > _DATE_MAX:
                lo, hi = _DATE_MAX - span, _DATE_MAX
    except Exception:
        pass
    return lo, hi

def _window_day_hours(dataViewSettings, window_anchor):
    """The X-axis time window converted to midnight-anchored hours (h0, h1),
    or None when no window is set.

    `window_anchor` is the midnight of the FIRST day of the selected data; the
    window keeps its day offset from that anchor plus its clock time. Applied to
    each site's OWN midnight-anchored hours, this standardizes the TIME OF DAY:
    'day 2, 06:00-18:00' selects day 2 of every site even when the sites were
    sampled on different dates. With a single site it reduces exactly to the
    absolute window."""
    xs = dataViewSettings.get('xAxisStart')
    xe = dataViewSettings.get('xAxisEnd')
    if xs is None or xe is None or window_anchor is None or pd.isna(window_anchor):
        return None
    anchor = pd.Timestamp(window_anchor).normalize()
    h0 = (pd.Timestamp(xs) - anchor).total_seconds() / 3600.0
    h1 = (pd.Timestamp(xe) - anchor).total_seconds() / 3600.0
    return (h0, h1)


def _time_of_day_axis(ax, h0, h1):
    """Configure a midnight-anchored 'time of day' X axis: ticks labeled with the
    clock hour (00:00, 06:00, ...) and a light dashed line at each day boundary
    (multiples of 24 h). h0/h1 are hours since the first day's midnight."""
    span = max(h1 - h0, 1.0)
    # clock-aligned steps only, so the labels repeat identically day after day
    step = next(s for s in (1, 2, 3, 6, 12, 24, 48, 96) if span / s <= 10)
    ticks = np.arange(np.floor(h0 / step) * step, h1 + step * 0.5, step)
    ticks = ticks[ticks >= h0 - 1e-9]
    ax.set_xlim(h0, h1)
    ax.set_xticks(ticks)
    ax.set_xticklabels(['%02d:00' % (int(round(t)) % 24) for t in ticks])
    for d in np.arange(24.0, h1, 24.0):
        if d > h0:
            ax.axvline(d, color='0.75', lw=0.8, linestyle='--', zorder=0)
    ax.set_xlabel("Time of day (00:00 = midnight of each site's first day; dashed lines = day boundaries)")


# display labels for the internal semester keys (titles/log lines only; file
# names keep the compact space-less key)
_SEM_LABEL = {'1stSemester': '1st semester', '2ndSemester': '2nd semester'}


def _floor_fit(fitted):
    """Every variable in this software is physically >= 0 (values <= 0 are
    discarded or clamped at qualification), so a fitted tendency must not dip
    below zero either: the curve is floored at 0 - it follows the zero line
    where the polynomial goes negative and rejoins the fit where it returns
    above zero."""
    return np.maximum(fitted, 0.0)


def _fit_margins(fig, pad=6):
    """Measure the actually-drawn content (tick labels + axis labels of every
    axis) and pull the plot's left/right margins in so NOTHING is clipped at the
    window edges - regardless of how wide the tick numbers turn out to be or how
    many stacked axes there are. The window size itself stays fixed; only the
    plot area shrinks to make room. Runs a couple of passes to converge."""
    try:
        for _ in range(3):
            fig.canvas.draw()
            r = fig.canvas.get_renderer()
            fw = fig.bbox.width
            boxes = [a.get_tightbbox(r) for a in fig.axes if a.get_visible()]
            if not boxes:
                return
            x0 = min(b.x0 for b in boxes)
            x1 = max(b.x1 for b in boxes)
            sp = fig.subplotpars
            left, right = sp.left, sp.right
            if x0 < pad:
                left += (pad - x0) / fw
            if x1 > fw - pad:
                right -= (x1 - (fw - pad)) / fw
            if abs(left - sp.left) < 1e-4 and abs(right - sp.right) < 1e-4:
                break                      # converged: nothing clipped
            if right - left < 0.2:
                break                      # give up rather than collapse the plot
            fig.subplots_adjust(left=max(0.02, left), right=min(0.995, right))
    except Exception:
        pass


def _fit_stacked_yticks(fig, spacing=None, pad=4.0, min_pt=4.0):
    """When many parameter axes are stacked on the right, their number labels and
    rotated axis titles can collide with the next axis. Shrink the y fonts (tick
    numbers AND axis titles together) until every adjacent pair of label columns
    has at least `pad` px of clear gap - measured on the SAME renderer that draws
    the figure, so it reflects the real widths (e.g. a 6-char density value like
    1019.5) rather than a guess. No-op once there is already room."""
    if len(fig.axes) < 2:
        return
    try:
        for _ in range(8):
            fig.canvas.draw()
            r = fig.canvas.get_renderer()
            # each axis' label "column" = union of its y number labels + its title
            cols = []
            for ax in fig.axes:
                boxes = [t.get_window_extent(r) for t in ax.get_yticklabels() if t.get_text()]
                lab = ax.yaxis.get_label()
                if lab.get_text():
                    boxes.append(lab.get_window_extent(r))
                if boxes:
                    cols.append((min(b.x0 for b in boxes), max(b.x1 for b in boxes)))
            cols.sort()
            # worst horizontal encroachment between neighboring columns
            worst = max((a[1] - b[0] for a, b in zip(cols, cols[1:], strict=False)), default=-1e9)
            if worst <= -pad:                      # clear gap everywhere -> done
                return
            cur = min((t.get_fontsize() for ax in fig.axes
                       for t in ax.get_yticklabels() if t.get_text()), default=10.0)
            if cur <= min_pt:                      # already as small as we allow
                return
            for ax in fig.axes:                    # shrink numbers + title, redraw, re-check
                for t in ax.get_yticklabels():
                    t.set_fontsize(max(min_pt, t.get_fontsize() * 0.88))
                lab = ax.yaxis.get_label()
                lab.set_fontsize(max(min_pt, lab.get_fontsize() * 0.88))
    except Exception:
        pass


def _report_points_outside(fig):
    """Says how many plotted points fall OUTSIDE the view, per axis.

    With 'Fixed scale' on, the scale defaults are computed from APPROVED data
    only (flags 1/2 - see _param_data_extreme), so suspect or bad values the
    operator chose to keep in the sheet can sit outside the axis and simply not
    be drawn. That was silent, and it reads as missing data (owner, v12.3): a
    HOBO series with 881 suspect points out of 2127 lost 6 of them under the
    axis, and nothing said so.
    """
    try:
        for ax in fig.axes:
            lo, hi = ax.get_ylim()
            lo, hi = min(lo, hi), max(lo, hi)
            outside = total = 0
            for line in ax.get_lines():
                y = np.asarray(line.get_ydata(orig=False), dtype='float64')
                y = y[np.isfinite(y)]
                total += y.size
                outside += int(((y < lo) | (y > hi)).sum())
            if outside:
                print('Info: %d of %d %s point(s) are outside the plotted scale '
                      'and are not drawn (fixed scale uses the APPROVED range; '
                      'untick it or widen Min/Max in Scale settings to see them).'
                      % (outside, total, ax.get_ylabel() or 'axis'))
    except Exception:
        pass


def enable_scroll_zoom(fig):
    """Interaction for a shown panel: mouse-wheel zoom around the cursor,
    middle-button drag to pan, and the plotted limits remembered on the figure
    so the toolbar's home button returns to them. Call it right before the
    panel is shown (after all axes have their final limits)."""
    # pull the margins in so no tick/axis label is clipped at the window edges
    _fit_margins(fig)
    _report_points_outside(fig)
    # snapshot the original plotted view for Reset
    original = [(ax, ax.get_xlim(), ax.get_ylim()) for ax in fig.axes]

    def _overlaid_axes(ref_ax):
        # These panels stack several parameter y-axes with twinx(): they overlap
        # (same position) and SHARE the x-axis. Zoom/pan act on ALL of them in
        # DISPLAY (pixel) coordinates so the independent y-scales stay aligned.
        # Because the x-axis is shared, it is set ONCE (from the reference axis) -
        # setting it per-axis would compound the change N times and feel coarse.
        ref = ref_ax.get_position().bounds
        return [a for a in fig.axes
                if all(abs(p - q) < 1e-6 for p, q in zip(a.get_position().bounds, ref, strict=False))]

    ZOOM = 1.1   # gentle per-notch factor (was 1.2, too aggressive)

    def on_scroll(event):
        if event.inaxes is None:
            return
        axes = _overlaid_axes(event.inaxes)
        if not axes:
            return
        scale = 1 / ZOOM if event.button == 'up' else ZOOM   # wheel up = zoom in
        ref = event.inaxes
        xd, _ = ref.transData.inverted().transform((event.x, event.y))
        xl = ref.get_xlim()
        new_xlim = _clamp_x(ref, xd - (xd - xl[0]) * scale, xd + (xl[1] - xd) * scale)
        for ax in axes:
            ax.set_xlim(new_xlim)          # shared x: same absolute value, no compounding
            _, yd = ax.transData.inverted().transform((event.x, event.y))
            yl = ax.get_ylim()
            ax.set_ylim(yd - (yd - yl[0]) * scale, yd + (yl[1] - yd) * scale)
        fig.canvas.draw_idle()

    pan = {'x': None, 'y': None, 'ref': None, 'axes': None}

    def on_press(event):
        if event.button == 2 and event.inaxes is not None:   # 2 = middle button
            pan.update(x=event.x, y=event.y, ref=event.inaxes,
                       axes=_overlaid_axes(event.inaxes))

    def on_move(event):
        if pan['axes'] is None or event.x is None:
            return
        ref = pan['ref']
        inv = ref.transData.inverted()
        rx0, _ = inv.transform((pan['x'], pan['y']))         # shared x delta (once)
        rx1, _ = inv.transform((event.x, event.y))
        dxr = rx1 - rx0
        xl = ref.get_xlim()
        new_xlim = _clamp_x(ref, xl[0] - dxr, xl[1] - dxr)
        for ax in pan['axes']:
            ax.set_xlim(new_xlim)          # shared x: set once (same value for all)
            inv2 = ax.transData.inverted()
            _, y0 = inv2.transform((pan['x'], pan['y']))     # per-axis y delta
            _, y1 = inv2.transform((event.x, event.y))
            dy = y1 - y0
            yl = ax.get_ylim()
            ax.set_ylim(yl[0] - dy, yl[1] - dy)
        pan['x'], pan['y'] = event.x, event.y                # incremental
        fig.canvas.draw_idle()

    def on_release(event):
        if event.button == 2:
            pan['axes'] = None

    def reset_view(*_):
        for ax, xl, yl in original:
            ax.set_xlim(xl)
            ax.set_ylim(yl)
        fig.canvas.draw_idle()

    fig.canvas.mpl_connect('scroll_event', on_scroll)
    fig.canvas.mpl_connect('button_press_event', on_press)
    fig.canvas.mpl_connect('motion_notify_event', on_move)
    fig.canvas.mpl_connect('button_release_event', on_release)

    # The toolbar stays matplotlib's OWN, untouched (owner, v12.3): the house
    # icon is the reset, and it works after a wheel zoom too because the window
    # pushes the opening view onto the navigation stack (see PlotWindow in
    # QCS_QtApp). Hiding buttons and adding a 'Reset view' text button, as
    # v12.1 did, made these panels look unlike every other plot the program
    # shows - which is the standard the owner picked.
    fig._qcs_reset_view = reset_view      # the view the panel opened with

    # app icon + a meaningful window title (the plot's own title, so the taskbar
    # and window name say what is being shown instead of 'Figure 1')
    _title = next((a.get_title() for a in fig.axes if a.get_title()), '')
    _theme.style_plot_window(fig, _title)

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

# Operator color overrides, {parameter: '#rrggbb'} (v12.0). Set from the
# Visualization tab's Scale settings and persisted in the user settings, so a
# site keeps its house colors across sessions. EVERY plot goes through
# getParamColors, so an override reaches all of them.
PARAM_COLOR_OVERRIDES = {}


def darker(hex_color, factor=0.62):
    """The dark tone (trend lines, axes) of a chosen color."""
    c = str(hex_color).lstrip('#')
    if len(c) != 6:
        return hex_color
    r, g, b = (int(c[i:i + 2], 16) for i in (0, 2, 4))
    return '#%02x%02x%02x' % (int(r * factor), int(g * factor), int(b * factor))


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

    # operator overrides win, and their dark tone is derived from the choice
    for param, color in PARAM_COLOR_OVERRIDES.items():
        if color:
            cParam[param] = color
            bcParam[param] = darker(color)

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
                'RH30': 'darkslategray'}
    
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
            # Only report when the semester HAS data but this parameter is
            # missing. An entirely empty semester (e.g. viewing only March, so the
            # 2nd semester is empty) is expected and would just spam the log.
            if not db[semester].empty:
                print('\nNo %s data for %s during %d %s.'%(parameter_names[i], site, year, semester))
            parameter_names.pop(i)
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

    # combined-replicates sheet: the between-replicate disagreement, one
    # vertical bar per sample (bar = max - min, centered on the plotted mean) -
    # the same visual as the DataView HOBO panel. Single-logger sheets carry
    # the spread column EMPTY, so nothing is drawn for them.
    if variable == 'Temperature (degC)' and 'Temperature spread (degC)' in qualified_data.columns:
        spread = pd.to_numeric(qualified_data['Temperature spread (degC)'], errors='coerce')
        temp = pd.to_numeric(qualified_data[variable], errors='coerce')
        valid = spread.notna() & temp.notna() & (spread > 0)
        if valid.any():
            ax1.errorbar(qualified_data.loc[valid.values, 'Datetime'], temp[valid],
                         yerr=spread[valid] / 2, fmt='none',
                         ecolor=cParam.get(variable, plot_color), elinewidth=1.0,
                         alpha=0.7, label='Replicate disagreement (bar = max - min)')
            ax1.legend(loc='best', fontsize=8)

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
    db_raw = _apply_time_window(db_raw, dataViewSettings)   # plot ONLY the chosen hours (no-op for profiles)
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
            print('Error:', e)
        for semester in db.keys():
            # define list of dataframes for y axis parameters
            y_list, cParam, bcParam, parameter_names = setParam (dataViewSettings, db, semester, site)
            rParam = renameParameters(parameter_names)
            if len(y_list) > 0:
                # FIXED window size so it never grows past the screen. The stacked
                # parameter axes always fit its right zone: the spine SPACING is
                # computed to fit, and the y-axis FONTS shrink only when there are
                # so many axes that normal spacing/labels would not fit (few
                # parameters keep the normal 60 px spacing and font).
                n_right = max(0, len(y_list) - 1)
                TOTAL_PX, H_PX, LEFT_PX = 1050, 540, 78
                MAX_ZONE = TOTAL_PX - LEFT_PX - 560          # keep the plot >= 560 px
                spacing = min(60.0, max(22.0, (MAX_ZONE - 95) / (n_right - 1))) if n_right > 1 else 60.0
                actual_zone = min(MAX_ZONE, ((n_right - 1) * spacing + 95) if n_right >= 1 else 40)
                plot_px = TOTAL_PX - LEFT_PX - actual_zone   # plot gets the rest
                fscale = min(1.0, max(0.55, spacing / 58.0)) # shrink y fonts when tight
                nbins = 6 if n_right >= 4 else 8              # fewer, rounder y ticks when crowded
                fig, ax1 = plt.subplots(figsize=(TOTAL_PX / 100, H_PX / 100))
                plt.xticks(rotation=35)
                plt.subplots_adjust(left=LEFT_PX / TOTAL_PX,
                                    right=(LEFT_PX + plot_px) / TOTAL_PX, bottom=0.18)
                plt.grid(True, linestyle='dotted', linewidth=0.5)
                #define x and y
                # defining y while removing datetime duplicates
                y = y_list[0].loc[~(y_list[0].index.duplicated(keep=False) & y_list[0].isna())]
                # filling gaps greater than 1 hour
                y, gap_ids = fill_NaT_gap(y)
                #defining x
                x = y.index
                # Pressure is NEVER fitted: a mooring's pressure is dominated by the
                # tide, so a low-degree polynomial through it is meaningless. Its
                # raw series is drawn as a dashed line instead (same rule as the
                # twin axes below).
                if fit_lin_regression == True and y_list[0].name != 'Pressure (dbar)':
                    xp, yp = linear_regression (y, degree=deg)
                    yp = _floor_fit(yp)
                    if points == True:
                        ax1.plot(x, y, color=cParam[y_list[0].name], linestyle='none', marker='.', markersize=3, label=rParam[0])
                    ax1.plot(xp, yp, color=bcParam[y_list[0].name], linestyle='-', label=rParam[0])
                    if points != True:
                        # only the tendency curve is drawn: hug its range. With the
                        # data points visible the axis must NOT be clamped to the
                        # fit, or genuine (approved) data gets clipped out of view.
                        ax1.set_ylim(([max(0.0, yp.min() - 0.05 * np.abs(yp.max()-yp.min())), yp.max() + 0.05 * np.abs(yp.max()-yp.min())]))
                elif y_list[0].name == 'Pressure (dbar)':
                    ax1.plot(x, y, color=bcParam[y_list[0].name], linestyle='--', marker='None', label=rParam[0])
                else:
                    ax1.plot(x, y, color=bcParam[y_list[0].name], linestyle='None', marker='.', label=rParam[0])
                # set y label
                ax1.set_ylabel(rParam[0], color=bcParam[y_list[0].name], fontsize=10 * fscale)
                # set title
                # the year lives on the X axis since v12.0 (owner: the axis
                # must carry it; the title then drops the redundant year)
                ax1.set_title('Parameters for %s over %s'%(site, _SEM_LABEL.get(semester, semester)))
                # set y axis color and position
                ax1.spines['left'].set_color(bcParam[y_list[0].name])
                ax1.spines['left'].set_position(('outward', 1))
                ax1.spines['left'].set_linewidth(2.0)
                ax1.tick_params(axis='y', which='both', colors=bcParam[y_list[0].name], labelsize=10 * fscale)
                ax1.yaxis.set_major_locator(MaxNLocator(nbins=nbins, prune='both'))
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
                        yp = _floor_fit(yp)
                        if points == True:
                            ax.plot(x, y, linestyle='none', marker='.', markersize=3, c=cParam[y_list[i-1].name], label=rParam[i-1])
                        ax.plot(xp, yp, linestyle='-', c=bcParam[y_list[i-1].name], label=rParam[i-1])
                        if points != True:
                            # same rule as the first axis: clamp to the fit range
                            # only when the data points are hidden
                            ax.set_ylim(([max(0.0, yp.min() - 0.05 * np.abs(yp.max()-yp.min())), yp.max() + 0.05 * np.abs(yp.max()-yp.min())]))

                    else:
                        if y_list[i-1].name == 'Pressure (dbar)':
                            ax.plot(x, y, linestyle='--', marker='None', c=bcParam[y_list[i-1].name], label=rParam[i-1])
                        else:
                            ax.plot(x, y, linestyle='None', marker='.', c=bcParam[y_list[i-1].name], label=rParam[i-1])
                    # set axis label
                    ax.set_ylabel(rParam[i-1], c=bcParam[y_list[i-1].name], fontsize=10 * fscale)
                    # set y axis position
                    if i == 2:
                        pass
                    else:
                        ax.spines['right'].set_position(('outward', offset))
                    offset += spacing
                    # set y axis colors
                    ax.spines['right'].set_color(bcParam[y_list[i-1].name])
                    ax.spines['left'].set_color('none')
                    # set y axis width
                    ax.spines['right'].set_linewidth(1.5)
                    # change tick colors
                    ax.tick_params(axis='y', colors=cParam[y_list[i-1].name], labelsize=10 * fscale)
                    ax.yaxis.set_major_locator(MaxNLocator(nbins=nbins, prune='both'))
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
                plt.gca().xaxis.set_major_formatter(plt.matplotlib.dates.DateFormatter('%d/%m/%y %H:%M'))
                # shrink y tick fonts if the widest label would not fit between the
                # stacked spines, so adjacent axes' numbers never overlap
                _fit_stacked_yticks(fig, spacing)
                plt.savefig('panel1_%s_%s_%d.svg'%(site, semester, year), bbox_inches='tight')
                enable_scroll_zoom(fig)
                show_panels()

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
        # window anchor: midnight of the FIRST day of the selected sites' data in
        # this semester (see _window_day_hours - keeps the window's day offset)
        sem_sel = db[semester][db[semester]['Site'].isin(site_names)]
        window_anchor = sem_sel['Datetime'].min().normalize() if not sem_sel.empty else None
        win = _window_day_hours(dataViewSettings, window_anchor)
        for parameter in parameter_names:
            display_param = rParam[parameter_names.index(parameter)]
            fig, ax1 = plt.subplots(figsize=(980/100, 500/100))
            # the year lives on the X axis since v12.0 (title drops it)
            plt.title(f'{display_param} on {_SEM_LABEL.get(semester, semester)} for each site')
            plt.grid(True, linestyle='dotted', linewidth=0.5)
            ax1.set_ylabel(display_param)
            control = 0
            max_hour = 0.0

            for site in site_names:
                # Extract data for the specific site
                y = db[semester].copy()
                y = y[parameter][(y.loc[:,'Site'] == site)]
                y = y.loc[~(y.index.duplicated(keep=False) & y.isna())]

                # X axis standardized by TIME OF DAY (B6): hours since midnight of
                # each site's OWN first sampled day, so x=15 is 15:00 of day 1 for
                # every site and sites sampled on different dates overlay by clock
                # time. The time window filters in the same day-offset+clock terms.
                if not y.empty:
                    site_origin = y.index.min().normalize()
                    if win is not None:
                        x_all = (y.index - site_origin).total_seconds() / 3600
                        y = y[(x_all >= win[0]) & (x_all <= win[1])]

                if y.empty:
                    if not db[semester].empty:   # skip the noise for an empty semester
                        print(f'\nNo {parameter} data for {site} during {year} {semester}.')
                    continue

                control += 1
                y, gap_ids = fill_NaT_gap(y)  # Fill gaps
                x_hours = (y.index - site_origin).total_seconds() / 3600
                max_hour = max(max_hour, float(np.nanmax(x_hours)))

                # Plotting the data. Pressure is NEVER fitted (tidal signal: a
                # polynomial through it is meaningless) - its raw series is drawn
                # as a dashed line instead, the same rule used in Panel 1.
                if fit_lin_regression and parameter == 'Pressure (dbar)':
                    ax1.plot(x_hours, y, linestyle='--', marker='None',
                            color=colors[site], label=f'{site} data')
                elif fit_lin_regression:
                    xp, yp = linear_regression(y, degree=deg)
                    yp = _floor_fit(yp)
                    xp_hours = (xp - site_origin).total_seconds() / 3600

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

            # midnight-anchored clock axis; the window (when set) fixes the same
            # day-offset + clock range in every plot so sites/files compare 1:1
            if win is not None:
                _time_of_day_axis(ax1, win[0], win[1])
            else:
                _time_of_day_axis(ax1, 0.0, max(np.ceil(max_hour / 6.0) * 6.0, 24.0))

            # Legend and layout
            ax1.legend(loc='upper left', bbox_to_anchor=(1, 1.01), fontsize=7)
            plt.subplots_adjust(left=0.10, right=0.80, top=0.88, bottom=0.14)  # room for the y label + x labels

            # Fixed scale if needed
            if dataViewSettings['fixedScale'] and parameter in dataViewSettings['scaleSettings']:
                ax1.set_ylim(dataViewSettings['scaleSettings'][parameter]['min'],
                            dataViewSettings['scaleSettings'][parameter]['max'])

            # Strip parentheses from the file name
            parameter_r = re.sub(r'\([^()]*\)', '', parameter).strip()
            plt.savefig(f'panel2_{parameter_r}_{semester}_{year}.svg')
            enable_scroll_zoom(fig)
            show_panels()

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
    db_raw = _apply_time_window(db_raw, dataViewSettings)   # plot ONLY the chosen hours (no-op for profiles)
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
            print('Error:', e)
        for semester in db.keys():
            x_list, cParam, bcParam, parameter_names = setParam(dataViewSettings, db, semester, site)
            rParam = renameParameters(parameter_names)
            if len(x_list) > 0:
                # The parameter x-axes stack DOWNWARD from the plot (25 pts each).
                # Size the figure so they ALL fit: with a fixed 500 px height the
                # lower axes overflowed off the bottom and were silently hidden
                # once many parameters were selected (Chlorophyll/pH/DOM/... just
                # vanished). Give the stacked axes exactly the room they need.
                n_ax = len(x_list)
                below_in = (25 * max(n_ax - 1, 0) + 55) / 72.0   # stacked axes + last labels
                plot_in, top_in = 3.0, 0.45
                fig_h_in = plot_in + below_in + top_in
                fig, ax1 = plt.subplots(figsize=(980 / 100, fig_h_in))
                plt.subplots_adjust(left=0.050, right=0.840,
                                    top=1 - top_in / fig_h_in,
                                    bottom=below_in / fig_h_in)
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
                    xp = _floor_fit(xp)   # the parameter is on the X axis in profiles
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
                # the year lives on the X axis since v12.0 (owner: the axis
                # must carry it; the title then drops the redundant year)
                ax1.set_title('Parameters for %s over %s'%(site, _SEM_LABEL.get(semester, semester)))
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
                        xp = _floor_fit(xp)   # was NaN-hidden; now follows the zero line
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
                show_panels()

def plot_light_window(lux_info, site=''):
    """Daily envelope of the HOBO light with baseline and fouling threshold.
    The parameters used are written ON the plot (traceability of the cutoff).
    Returns (fig, ax); the cutoff is drawn separately by mark_light_cutoff."""
    daily_peak = lux_info['daily_peak']
    params = lux_info['params']
    fig, ax = plt.subplots(figsize=(11, 5.5))
    ax.plot(daily_peak.index, daily_peak.values, '-', marker='.', ms=4,
            color='#b38f00', lw=1.2, label='Daily light peak')
    thr_curve = lux_info.get('threshold_curve')
    if thr_curve is not None and len(thr_curve):
        # season-corrected rule (v10.0): the decision runs on peaks divided by
        # the astronomical clear-sky factor, so in RAW lux space the baseline
        # and threshold are CURVES that breathe with the season - a flat line
        # here would misrepresent the rule that was applied
        frac = lux_info['params']['cutoff_frac']
        base_curve = thr_curve / frac if frac else thr_curve
        ax.plot(base_curve.index, base_curve.values, color='#1f7a1f', lw=1.2,
                linestyle='--', label='Clean-sensor baseline (season-adjusted, lat %.1f)'
                % lux_info['params']['latitude'])
        ax.plot(thr_curve.index, thr_curve.values, color='#b30000', lw=1.2,
                linestyle=':', label='Fouling threshold (%.0f%% of baseline, season-adjusted)'
                % (100 * frac))
    elif np.isfinite(lux_info.get('baseline', np.nan)):
        ax.axhline(lux_info['baseline'], color='#1f7a1f', lw=1.2, linestyle='--',
                   label='Clean-sensor baseline (%.0f lux)' % lux_info['baseline'])
        ax.axhline(lux_info['threshold'], color='#b30000', lw=1.2, linestyle=':',
                   label='Fouling threshold (%.0f lux)' % lux_info['threshold'])
    ax.set_yscale('log')
    ax.set_ylabel('Lux (log scale)')
    ax.grid(alpha=0.3)
    ax.legend(loc='lower left', fontsize=8)
    ax.set_title('%s - light usable window (fouling)' % (site or 'HOBO'))
    # cutoff parameters visible on the plot itself - they must describe the rule
    # that was ACTUALLY applied (fixed mode still draws the adaptive baseline
    # and threshold, but only as context)
    if lux_info.get('fixed_days') is not None:
        rule_text = ('Rule: FIXED window - light becomes BAD %d day(s) after deployment, '
                     'regardless of the measured light (the baseline and threshold above are '
                     'shown for context only).  [Settings: lux_fixed_days]'
                     % lux_info['fixed_days'])
    else:
        season = ('' if params.get('latitude') is None else
                  ' Peaks are first divided by the clear-sky seasonal curve for latitude %.1f, '
                  'so a winter decline in ambient light is not read as fouling.'
                  % params['latitude'])
        rule_text = ('Rule: baseline = max daily peak of the first %d day(s); light becomes BAD '
                     'from the start of the FINAL run (>= %d day(s)) where the daily peak stays below '
                     '%.0f%% of the baseline and never recovers to it.%s  '
                     '[Settings: lux_baseline_days / lux_cutoff_frac / lux_sustain_days]'
                     % (params['baseline_days'], params['sustain_days'],
                        100 * params['cutoff_frac'], season))
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
            'Warning: the light dips and recovers (%.0f%% of later days reach the threshold) -\n'
            'not clean biofouling (possible cleaning / multiple deployments). Review!'
            % (100 * lux_info.get('recovery_day_frac_after', 0)),
            transform=ax.transAxes, ha='center', va='top', fontsize=8.5,
            color='#b30000', weight='bold',
            bbox=dict(boxstyle='round', facecolor='#fff0f0', edgecolor='#b30000')))
    return artists


def _hobo_slice_years (database, dataViewSettings, site, time_window=True):
    """Site slice over EVERY selected year in ONE series (a deployment crossing
    the new year is never split into truncated per-year plots), optionally
    filtered to the absolute X-axis time window, sorted in time."""
    years = dataViewSettings.get('filterByYears') or []
    db = database[database['Site'] == site]
    if years:
        db = db[db['Datetime'].dt.year.isin(years)]
    if time_window:
        db = _apply_time_window(db, dataViewSettings)
    return db.sort_values('Datetime')


def _lux_daily_peak (db):
    """Daily maximum of the light series - the envelope used by the fouling
    review plot - as a Series indexed by day."""
    lux = pd.to_numeric(db['Luminosity (lux)'], errors='coerce')
    s = pd.Series(lux.values, index=pd.DatetimeIndex(db['Datetime']))
    return s.resample('D').max().dropna()


def _hobo_light_cutoff_start (db):
    """First instant with Flag_lux == 4 (start of the fouling window),
    or None if the light is usable for the entire plotted period."""
    flag_lux = pd.to_numeric(db['Flag_lux'], errors='coerce')
    flagged_times = db.loc[flag_lux == 4, 'Datetime']
    if flagged_times.empty:
        return None
    return flagged_times.iloc[0]


def plot_hobo_params_at_site (database, dataViewSettings, site):
    """HOBO 'Parameters at a site': the selected parameters (temperature and/or
    light) for ONE site in a single figure spanning EVERY selected year (a
    deployment crossing the new year is not split). Temperature: dots +
    suspect/bad highlights + optional replicate-disagreement bars + tendency line
    (floored at 0). Light: LINEAR scale with the DAILY-PEAK envelope (the same
    visual as the fouling review), optional raw points, and the fouling window
    (Flag_lux == 4) shaded. Returns the number of figures generated (0 or 1)."""
    cParam, bcParam = getParamColors()
    db = _hobo_slice_years(database, dataViewSettings, site)
    params = [p for p in dataViewSettings['parameterList']
              if p in ('Temperature (degC)', 'Luminosity (lux)') and p in db.columns
              and pd.to_numeric(db[p], errors='coerce').notna().any()]
    if db.empty or not params:
        print('\nNo HOBO data to plot for %s (check the parameters/years/window).' % site)
        return 0
    fit = dataViewSettings['tendencyLines']
    deg = dataViewSettings['linearRegressionDegree']
    points = dataViewSettings['viewDataPoints']

    fig, ax1 = plt.subplots(figsize=(1050 / 100, 540 / 100))
    plt.xticks(rotation=35)
    plt.subplots_adjust(bottom=0.18)
    ax1.grid(True, linestyle='dotted', linewidth=0.5)
    handles = []
    for i, param in enumerate(params):
        ax = ax1 if i == 0 else ax1.twinx()
        display = renameParameters([param])[0]
        if param == 'Temperature (degC)':
            temp = pd.to_numeric(db['Temperature (degC)'], errors='coerce')
            # combined-replicates file: shade the between-replicate disagreement
            # (band of total width = spread, centered on the plotted mean),
            # unless the operator turned the bars off
            if ('Temperature spread (degC)' in db.columns
                    and dataViewSettings.get('showDisagreementBars', True)):
                spread = pd.to_numeric(db['Temperature spread (degC)'], errors='coerce')
                valid = spread.notna() & temp.notna() & (spread > 0)
                if valid.any():
                    # ONE vertical bar PER SAMPLE (bar length = max - min of the
                    # replicates at that instant), centered on the plotted mean.
                    # A continuous shaded band was tried first and read as
                    # translucent lines linking the dots (it interpolated the
                    # spread BETWEEN samples) - per-sample bars do not.
                    eb = ax.errorbar(db.loc[valid.values, 'Datetime'], temp[valid],
                                     yerr=spread[valid] / 2, fmt='none',
                                     ecolor=cParam[param], elinewidth=1.0,
                                     alpha=0.7,
                                     label='Replicate disagreement (bar = max - min)')
                    handles.append(eb)
            # NOTE: suspect/bad values are NOT highlighted here - keeping or
            # removing them was the operator's decision at qualification, and
            # the markers only cluttered the legend
            if points or not fit:
                h, = ax.plot(db['Datetime'], temp, linestyle='None', marker='.',
                             markersize=3, color=bcParam[param], label='Temperature')
                handles.append(h)
            if fit:
                s = pd.Series(temp.values, index=pd.DatetimeIndex(db['Datetime'])).dropna()
                if len(s) > 3:
                    xp, yp = linear_regression(s, degree=deg)
                    yp = _floor_fit(yp)
                    h, = ax.plot(xp, yp, linestyle='-', color=bcParam[param],
                                 label='Temperature tendency')
                    handles.append(h)
        else:
            # light: daily-peak envelope on a LINEAR scale (the fouling-review
            # visual the operator already knows), optional raw points
            lux = pd.to_numeric(db['Luminosity (lux)'], errors='coerce')
            peak = _lux_daily_peak(db)
            if points:
                h, = ax.plot(db['Datetime'], lux, linestyle='None', marker='.',
                             markersize=2, alpha=0.35, color=cParam[param],
                             label='Light readings')
                handles.append(h)
            h, = ax.plot(peak.index, peak.values, linestyle='-', marker='.',
                         markersize=4, lw=1.2, color=bcParam[param],
                         label='Daily light peak')
            handles.append(h)
            if 'Flag_lux' in db.columns:
                cutoff = _hobo_light_cutoff_start(db)
                if cutoff is not None:
                    ax.axvline(cutoff, color='#b30000', lw=1.6)
                    handles.append(ax.axvspan(cutoff, db['Datetime'].iloc[-1],
                                              color='#b30000', alpha=0.10,
                                              label='Fouling window (light unusable)'))
        ax.set_ylabel(display, color=bcParam[param])
        ax.tick_params(axis='y', colors=bcParam[param])
        if i == 1:
            ax.spines['right'].set_color(bcParam[param])
        if dataViewSettings.get('fixedScale') and param in dataViewSettings.get('scaleSettings', {}):
            ax.set_ylim(dataViewSettings['scaleSettings'][param]['min'],
                        dataViewSettings['scaleSettings'][param]['max'])
    # the year lives on the X axis since v12.0 (owner: day/month alone was
    # confusing; the title then drops the redundant year list)
    ax1.set_title('HOBO parameters for %s' % site)
    ax1.xaxis.set_major_formatter(_mdates.DateFormatter('%d/%m/%y'))
    ax1.legend(handles=handles, fontsize=8)
    plt.savefig('hobo_params_%s.svg' % site, bbox_inches='tight')
    enable_scroll_zoom(fig)
    show_panels()
    return 1


def plot_hobo_params_across_sites (database, dataViewSettings):
    """HOBO 'Parameters across sites': ONE figure per selected parameter with
    every selected site overlaid on the TIME-OF-DAY axis (hours since each
    site's own first midnight - B6), spanning every selected year in one plot.
    Temperature: dots + optional per-site tendency (floored at 0). Light: the
    daily-peak envelope per site (linear scale) with each site's fouling cutoff
    marked. Returns the number of figures generated."""
    site_names = dataViewSettings['siteList']
    params = [p for p in dataViewSettings['parameterList']
              if p in ('Temperature (degC)', 'Luminosity (lux)')]
    colors = getSiteColors(site_names)
    fit = dataViewSettings['tendencyLines']
    deg = dataViewSettings['linearRegressionDegree']
    points = dataViewSettings['viewDataPoints']

    # window anchor: midnight of the first day over the SELECTED sites/years
    # (see _window_day_hours - keeps the window's day offset + clock time)
    years = dataViewSettings.get('filterByYears') or []
    sel = database[database['Site'].isin(site_names)]
    if years:
        sel = sel[sel['Datetime'].dt.year.isin(years)]
    window_anchor = sel['Datetime'].min().normalize() if not sel.empty else None
    win = _window_day_hours(dataViewSettings, window_anchor)

    n_figs = 0
    for param in params:
        display = renameParameters([param])[0]
        fig, ax = plt.subplots(figsize=(1050 / 100, 540 / 100))
        plt.subplots_adjust(bottom=0.14)
        ax.grid(True, linestyle='dotted', linewidth=0.5)
        plotted = 0
        max_hour = 0.0
        for site in site_names:
            db = _hobo_slice_years(database, dataViewSettings, site, time_window=False)
            if db.empty or param not in db.columns:
                print('\nNo %s data for %s.' % (param, site))
                continue
            values = pd.to_numeric(db[param], errors='coerce')
            if not values.notna().any():
                print('\nNo %s data for %s.' % (param, site))
                continue
            site_origin = db['Datetime'].min().normalize()
            x_hours = (pd.DatetimeIndex(db['Datetime']) - site_origin).total_seconds() / 3600
            if win is not None:
                # x_hours is an Index, so the comparison already yields a
                # plain numpy bool array - '.values' on it crashed the panel
                # whenever a time window was set (latent since the B6 window)
                keep = (x_hours >= win[0]) & (x_hours <= win[1])
                db, values, x_hours = db[keep], values[keep], x_hours[keep]
                if db.empty:
                    print('\nNo %s data for %s inside the X-axis window.' % (param, site))
                    continue
            max_hour = max(max_hour, float(x_hours.max()))
            if param == 'Luminosity (lux)':
                peak = _lux_daily_peak(db)
                peak_h = (peak.index - site_origin).total_seconds() / 3600
                if points:
                    ax.plot(x_hours, values, linestyle='None', marker='.',
                            markersize=2, alpha=0.30, color=colors[site])
                ax.plot(peak_h, peak.values, linestyle='-', marker='.', markersize=4,
                        lw=1.2, color=colors[site], label='%s daily peak' % site)
                if 'Flag_lux' in db.columns:
                    cutoff = _hobo_light_cutoff_start(db)
                    if cutoff is not None:
                        cutoff_h = (pd.Timestamp(cutoff) - site_origin).total_seconds() / 3600
                        ax.axvline(cutoff_h, color=colors[site], lw=1.4, linestyle='--',
                                   label='%s cutoff (%s)' % (site, pd.Timestamp(cutoff).date()))
            else:
                if fit:
                    s = pd.Series(values.values, index=pd.DatetimeIndex(db['Datetime'])).dropna()
                    if points:
                        ax.plot(x_hours, values, linestyle='None', marker='.',
                                markersize=3, color=colors[site], label='%s data' % site)
                    if len(s) > 3:
                        xp, yp = linear_regression(s, degree=deg)
                        yp = _floor_fit(yp)
                        xp_hours = (xp - site_origin).total_seconds() / 3600
                        ax.plot(xp_hours, yp, linestyle='-', color=colors[site],
                                label='%s tendency' % site)
                else:
                    ax.plot(x_hours, values, linestyle='None', marker='.',
                            markersize=3, color=colors[site], label='%s data' % site)
            plotted += 1
        if plotted == 0:
            plt.close(fig)
            print('\nNo %s data for any selected site.' % param)
            continue
        if win is not None:
            _time_of_day_axis(ax, win[0], win[1])
        else:
            _time_of_day_axis(ax, 0.0, max(np.ceil(max_hour / 6.0) * 6.0, 24.0))
        ax.set_ylabel(display)
        ax.set_title('HOBO %s across sites' % display)
        if dataViewSettings.get('fixedScale') and param in dataViewSettings.get('scaleSettings', {}):
            ax.set_ylim(dataViewSettings['scaleSettings'][param]['min'],
                        dataViewSettings['scaleSettings'][param]['max'])
        ax.legend(fontsize=8, loc='lower left')
        param_r = re.sub(r'\([^()]*\)', '', param).strip().replace(' ', '_')
        plt.savefig('hobo_%s_across_sites.svg' % param_r, bbox_inches='tight')
        enable_scroll_zoom(fig)
        show_panels()
        n_figs += 1
    return n_figs

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
    db_raw = _apply_time_window(db_raw, dataViewSettings)   # plot ONLY the chosen hours (no-op for profiles)
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
        print('Error:', e)
    
    # working with one semester at a time
    for semester in db.keys():
        if semester in emptySemester:
            pass
        else:
            ###### create figure and contour lines
            fig = plt.figure(figsize=(980 / 100, 500 / 100))  # Create figure with specified resolution
            ax = fig.add_subplot(111)  # Create axes
            # selecting semester
            _ts_cols = ['Pressure (dbar)', 'Depth (m)', 'Temperature (degC)', 'Salinity (PSU)', 'Site']
            _ts_cols += [c for c in ('Flag_S', 'Flag_T') if c in db[semester].columns]
            tspSemesterData = db[semester][_ts_cols].copy()
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
            # Robust S/T envelope for the axis + contour grid: drive it from
            # GOOD-flagged rows only (plus a 0.5% tail trim), so out-of-water
            # spikes (salinity crashing toward 0 when a pool logger is exposed
            # - all flagged suspect/bad) cannot stretch the axis to 0-36 and
            # squash the real cluster into a vertical line. Plain nanmin/nanmax
            # let a single artifact drive it. Suspect/bad points are still
            # plotted; they just do not set the view.
            keep = np.isfinite(SA) & np.isfinite(CT)
            _has_flags = any(_fc in tspSemesterData.columns for _fc in ('Flag_S', 'Flag_T'))
            for _fc in ('Flag_S', 'Flag_T'):
                if _fc in tspSemesterData.columns:
                    keep &= (tspSemesterData[_fc].to_numpy() == 1)
            if _has_flags and not keep.any():   # no good rows: fall back to all finite
                keep = np.isfinite(SA) & np.isfinite(CT)

            def _ts_bounds(arr, frac, min_span, keep=keep):
                a = arr[keep] if keep.any() else arr
                a = a[np.isfinite(a)]
                if a.size == 0:
                    return 0.0, min_span
                lo, hi = np.nanpercentile(a, [0.5, 99.5])
                # a mooring sits at one depth, so its S (and sometimes T) can be
                # nearly constant: open a minimum window, else the contour grid
                # collapses to a single row/column and contour() rejects it
                if (hi - lo) < min_span:
                    mid = 0.5 * (lo + hi)
                    lo, hi = mid - min_span / 2.0, mid + min_span / 2.0
                pad = frac * (hi - lo)
                return lo - pad, hi + pad

            # Figure out boundaries (mins and maxs)
            if re.search('conservative', tsParam, re.IGNORECASE):
                smin, smax = _ts_bounds(SA, 0.05, 0.30)
                tmin, tmax = _ts_bounds(CT, 0.10, 1.50)

            elif re.search('potential', tsParam, re.IGNORECASE):
                smin, smax = _ts_bounds(salt, 0.05, 0.30)
                tmin, tmax = _ts_bounds(pt, 0.10, 1.50)

            dmin = np.nanmin(depth)
            dmax = np.nanmax(depth)
            # Calculate the number of grid cells in the x and y dimensions
            # (never below 3: contour() needs a >= 2x2 grid, and the linspace
            # below only yields distinct values from 3 cells up)
            xdim = max(3, int(round((smax - smin) / 0.1 + 1, 0)))
            ydim = max(3, int(round((tmax - tmin) + 1, 0)))
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
                    if not tspSemesterData.empty:   # skip the noise for an empty semester
                        print('\nNo data for %s during %d %s.'%( site, year, semester))
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
            ax.set_title('T-S Diagram for %s over %s during %s'%(sites_label, _SEM_LABEL.get(semester, semester), year))
            custom_handles = []
            for a in range(len(site_names)):
                custom_handles.append(Line2D([0], [0], linestyle='None', marker=markerList[a], label=site_names[a], markeredgecolor='black', markerfacecolor='black', markersize=6))
            plt.legend(handles=custom_handles)  # Draw legend
            ax.set_xlim(smin, smax)   # hold the view on the robust envelope
            ax.set_ylim(tmin, tmax)
            plt.savefig('TS_Diagram_%s_%s_%d.svg'%(sites_label, semester, year))
            enable_scroll_zoom(fig)
            show_panels()




# ---------------------------------------------------------------------------
# DCPS / Doppler current-profiler panels (v8.0). Four figures rendered from
# the QUALIFIED tidy frame (needs 'Flag_cur'): rows flagged BAD are excluded.
# ---------------------------------------------------------------------------

def plot_replicate_review(replicates, referee, reference=None, label=''):
    """Figure for the redundant-replicate review (v9.0): every replicate's
    temperature, the independent reference, and the referee's scores - so the
    operator sees WHY a replicate is being called faulty before accepting it.
    Returns (fig, ax)."""
    fig, ax = plt.subplots(figsize=(11.5, 6))
    colors = ['#d62728', '#1f77b4', '#2ca02c', '#9467bd']
    for i, r in enumerate(replicates):
        t = pd.to_datetime(r['Datetime'])
        v = pd.to_numeric(r['Temperature (degC)'], errors='coerce')
        sc = next((s for s in referee.get('scores', []) if s['replicate'] == i), None)
        tag = 'replicate %d' % (i + 1)
        if sc and np.isfinite(sc.get('change_corr', np.nan)):
            tag += ' (corr %+.2f, offset %+.2f, swing %.2fx)' % (
                sc['change_corr'], sc['bias'], sc['amplitude_ratio'])
        if referee.get('recommended') == i:
            tag += '  <- SOUND'
        ax.plot(t, v, lw=0.7, color=colors[i % len(colors)], label=tag,
                zorder=3 if referee.get('recommended') == i else 2)
    if reference is not None and len(reference):
        ref = pd.Series(reference).sort_index()
        ax.plot(ref.index, ref.values, lw=2.0, color='0.25', linestyle='--',
                label='independent reference (other sites)', zorder=4)
    ax.set_ylabel('Temperature (°C)')
    ax.set_title('Replicate review - %s\n%s' % (label, referee.get('verdict', '')),
                 fontsize=10)
    ax.grid(alpha=0.3)
    ax.legend(fontsize=8, loc='best')
    ax.xaxis.set_major_formatter(_mdates.DateFormatter('%d/%m/%y'))
    fig.autofmt_xdate()
    return fig, ax


def _keep_or_close(fig, show, figures):
    """What to do with a panel once it is saved: hand it to the caller's
    list, leave it on screen, or close it. Closing is the default because a
    batch run would otherwise pile up hundreds of open figures."""
    if figures is not None:
        figures.append(fig)
    elif not show:
        plt.close(fig)


def _date_axis(ax, fig=None, rotation=45):
    """Makes a time axis on a current panel readable.

    The panels used to set a fixed '%d/%m/%y %H:%M' formatter on a locator that
    chose its own number of ticks, and then rotate through fig.autofmt_xdate():
    on a three-day session that printed ~15 labels of 14 characters flat on an
    11-inch axis, which overprinted into a solid line (owner, v13.0). The
    labels are rotated 45 degrees and anchored at their right end - so each one
    ends under its own tick - and the locator is capped at what fits."""
    import matplotlib.dates as mdates
    locator = mdates.AutoDateLocator(minticks=3, maxticks=9)
    ax.xaxis.set_major_locator(locator)
    # the offset line (the '2025-Apr' at the right end of the axis) is what
    # carries the YEAR now: a current database can span several visits, and a
    # 'day/month' tick alone cannot say which one it belongs to
    ax.xaxis.set_major_formatter(mdates.ConciseDateFormatter(locator, show_offset=True))
    for label in ax.get_xticklabels():
        label.set_rotation(rotation)
        label.set_horizontalalignment('right')
        label.set_rotation_mode('anchor')
    if fig is not None:
        fig.subplots_adjust(bottom=0.18)


def _bar_tick_size(bar):
    """The tick-label size of a colorbar, or None when there is no bar to
    copy from. Read from the drawn label rather than from rcParams: a figure
    may have been built under different settings."""
    if bar is None:
        return None
    labels = bar.ax.get_yticklabels()
    return labels[0].get_fontsize() if labels else None


def _direction_compass(fig, slot, cmap, label_font=None, tick_font=None):
    """Circular colour key for a bearing, drawn where `slot` (a spent
    colorbar axes) reserved the space.

    A linear 0-360 bar puts north at both ends and says nothing about which
    colour is east: on a wheel oriented like a compass, the colour IS the
    direction (owner, 2026-08-19). `cmap` must be the cyclic map the heatmap
    used, normalised over the same 0-360 range, or the key would describe a
    different figure from the one it sits next to.

    label_font/tick_font are taken from the speed panel's own colorbar, so the
    two keys of the same figure are lettered alike (owner, v13.0) instead of
    this one carrying a hand-picked size.
    """
    pos = slot.get_position()
    side_x = 0.11                                   # figure fractions...
    side_y = side_x * fig.get_figwidth() / fig.get_figheight()   # ...kept round
    wheel = fig.add_axes([pos.x0, pos.y0 + (pos.height - side_y) / 2.0,
                          side_x, side_y], projection='polar')
    theta = np.linspace(0, 2 * np.pi, 361)
    radius = np.array([0.62, 1.0])
    tt, rr = np.meshgrid(theta, radius)
    bearing = np.rad2deg(tt[:-1, :-1])              # shading='flat': C is 1 smaller
    wheel.pcolormesh(tt, rr, bearing, cmap=cmap, vmin=0, vmax=360, shading='flat')
    wheel.set_theta_zero_location('N')              # compass, not trigonometry:
    wheel.set_theta_direction(-1)                   # 0 at the top, running E
    wheel.set_ylim(0, 1)
    wheel.set_yticks([])
    wheel.set_xticks(np.deg2rad([0, 90, 180, 270]))
    wheel.set_xticklabels(['N', 'E', 'S', 'W'],
                          fontsize=tick_font if tick_font else 8)
    wheel.grid(False)
    wheel.spines['polar'].set_visible(False)
    wheel.tick_params(pad=-1)
    # the title has to clear the 'N' tick BELOW it, and the tick moves with the
    # font size - so the gap is measured in the same units, never a fixed 13 pt
    size = label_font if label_font else 10
    wheel.set_title('Direction [deg]', fontsize=size, pad=1.9 * size)
    return wheel


def plot_doppler_panels(frame, out_dir, label='', settings=None, show=False,
                        figures=None):
    """Saves the 4 current panels as SVGs into out_dir. Returns file list.

    show=True also puts them ON SCREEN, like every other panel family does
    (plot_database_panel1/2/3, the HOBO panels and the T-S diagram all end in
    plt.show()). It is the CALLER's choice: the Visualization tab shows them,
    while the qualification and the batch drivers write the files silently -
    the panels were being generated and never displayed, which read as 'no
    panels at all' (owner, v12.2.4).

    settings (all optional; None -> the v8.0 behavior) lets the Visualization
    tab steer the panels:
      xAxisStart / xAxisEnd  keep only this datetime window (also on the X axis)
      depthAxisMin / Max     keep only cells in this depth band (m)
      currentRepDepth        force the stick/progressive-vector depth (m); the
                             default is still the best-covered cell
      currentSpeedMax        fix the heatmap speed color scale (cm/s), so
                             several sites/years compare 1:1; None -> autoscale

    figures: a list to APPEND every figure to instead of showing or closing it.
    The caller then owns them - which is how the Visualization tab collects the
    panels of all the selected sites and opens them in ONE browsable window
    (v13.0) instead of one window per site per panel.
    """
    import os
    import matplotlib.dates as mdates
    s = settings or {}
    os.makedirs(out_dir, exist_ok=True)
    ok = frame[frame['Flag_cur'] != 4].copy()
    # time window + depth band (no-ops when the bounds are None)
    xs, xe = s.get('xAxisStart'), s.get('xAxisEnd')
    if xs is not None and xe is not None:
        ok = ok[(ok['Datetime'] >= pd.Timestamp(xs)) & (ok['Datetime'] <= pd.Timestamp(xe))]
    dmin, dmax = s.get('depthAxisMin'), s.get('depthAxisMax')
    if dmin is not None and dmax is not None:
        ok = ok[(ok['Depth (m)'] >= float(dmin)) & (ok['Depth (m)'] <= float(dmax))]
    if not len(ok):
        return []
    files = []
    t0 = ok['Datetime'].min()
    speed_max = s.get('currentSpeedMax')

    # 1) time x depth heatmaps: speed + direction
    fig, axes = plt.subplots(2, 1, figsize=(11, 7), sharex=True)
    speed_bar = None
    for ax, col, cmap, unit, vmx in (
            (axes[0], 'Horizontal speed (cm/s)', 'viridis', 'cm/s', speed_max),
            (axes[1], 'Direction (deg)', 'twilight', 'deg', 360)):
        piv = ok.pivot_table(index='Depth (m)', columns='Datetime', values=col)
        if piv.size:
            kw = {'vmin': 0, 'vmax': float(vmx)} if vmx else {}
            m = ax.pcolormesh(piv.columns, piv.index, piv.values, cmap=cmap,
                              shading='nearest', **kw)
            bar = fig.colorbar(m, ax=ax, label='%s [%s]' % (col.split(' (')[0], unit))
            if col.startswith('Horizontal speed'):
                speed_bar = bar          # the compass copies its lettering
            if col.startswith('Direction'):
                # the bar still RESERVES the space (both subplots must keep the
                # same width or the shared time axis stops lining up), but the
                # key drawn in it is a compass wheel
                bar.ax.set_visible(False)
                _direction_compass(fig, bar.ax, cmap,
                                   label_font=speed_bar.ax.yaxis.label.get_fontsize()
                                   if speed_bar is not None else None,
                                   tick_font=_bar_tick_size(speed_bar))
        ax.invert_yaxis()
        ax.set_ylabel('Depth (m)')
    # ticks carry the year: a Doppler set can span several years/visits, and
    # a day/month tick alone cannot say which one it belongs to. ConciseDate
    # writes the year (and the date) once, on the offset line of the axis,
    # instead of repeating it on every label
    _date_axis(axes[1], fig)
    fig.suptitle('Current profile - %s' % label)
    p = os.path.join(out_dir, 'Current profile (time x depth).svg')
    fig.savefig(p, bbox_inches='tight'); files.append(p)
    _keep_or_close(fig, show, figures)

    # representative depth: the user's choice (nearest available cell) or the
    # GOOD cell with most samples. Rows can carry a NaN east/north pair even
    # when not flagged BAD (partial records) - they cannot enter the vector
    # panels: a single NaN would poison the arrow scale (int(NaN) crash) and
    # the progressive-vector cumsum.
    avail = ok['Depth (m)'].dropna()
    want = s.get('currentRepDepth')
    if want is None and dmin is not None and dmax is not None:
        want = (float(dmin) + float(dmax)) / 2.0   # centre of the chosen band
    if want is not None and len(avail):
        rep_depth = float(avail.iloc[(avail - float(want)).abs().argmin()])
    else:
        rep_depth = ok.groupby('Depth (m)').size().idxmax()
    rep = ok[ok['Depth (m)'] == rep_depth].sort_values('Datetime')
    rep = rep.dropna(subset=['East speed (cm/s)', 'North speed (cm/s)'])

    # 2) stick plot: current vectors rooted on the time axis, angle-true. A
    # plain scale=1 quiver mixes cm/s with the date x-units and blows the
    # sticks across the whole axis; scale_units='width' makes the arrow length
    # proportional to speed and independent of the date axis, and the
    # reference key carries the magnitude scale (so the y-axis carries none).
    if len(rep):
        fig, ax = plt.subplots(figsize=(11, 4))
        tnum = mdates.date2num(rep['Datetime'].to_numpy())
        u = rep['East speed (cm/s)'].to_numpy()
        v = rep['North speed (cm/s)'].to_numpy()
        vmax = float(np.nanmax(np.hypot(u, v)))
        if not np.isfinite(vmax) or vmax <= 0:
            vmax = 1.0
        q = ax.quiver(tnum, np.zeros(len(rep)), u, v, angles='uv',
                      scale_units='width', scale=vmax * 12.5, width=0.003, color='tab:blue')
        ref = max(10, int(round(vmax / 2 / 10)) * 10)
        ax.quiverkey(q, 0.88, 0.9, ref, '%d cm/s' % ref, labelpos='E', coordinates='axes')
        ax.axhline(0, color='0.6', lw=0.8)
        ax.set_ylim(-1, 1)
        ax.set_yticks([])
        ax.set_title('Current sticks at %.1f m - %s' % (rep_depth, label))
        ax.xaxis_date()
        _date_axis(ax, fig)
        p = os.path.join(out_dir, 'Current stick plot.svg')
        fig.savefig(p, bbox_inches='tight'); files.append(p)
        _keep_or_close(fig, show, figures)

    # 3) U/V component series at up to 4 depths
    depths = sorted(ok['Depth (m)'].dropna().unique())
    sel = depths[:: max(1, len(depths) // 4)][:4]
    fig, axes = plt.subplots(2, 1, figsize=(11, 6), sharex=True)
    for d in sel:
        sub = ok[ok['Depth (m)'] == d].sort_values('Datetime')
        axes[0].plot(sub['Datetime'], sub['East speed (cm/s)'], lw=0.9, label='%.1f m' % d)
        axes[1].plot(sub['Datetime'], sub['North speed (cm/s)'], lw=0.9, label='%.1f m' % d)
    axes[0].set_ylabel('East U (cm/s)'); axes[1].set_ylabel('North V (cm/s)')
    axes[0].legend(fontsize=8, ncol=len(sel)); axes[0].set_title('Current components - %s' % label)
    _date_axis(axes[1], fig)
    p = os.path.join(out_dir, 'Current components (U-V).svg')
    fig.savefig(p, bbox_inches='tight'); files.append(p)
    _keep_or_close(fig, show, figures)

    # 4) progressive vector diagram at the representative depth.
    # The series is NOT continuous: BAD cells are dropped, and a database can
    # hold several visits to the site. Integrating speed x elapsed-time across
    # such a gap invents displacement (one sample after a 30-day gap adds
    # ~130 km), so a gap is never integrated - it breaks the trajectory.
    if not len(rep):
        return files
    fig, ax = plt.subplots(figsize=(7, 7))
    dt_s = rep['Datetime'].diff().dt.total_seconds().fillna(0.0).to_numpy()
    step = np.median(dt_s[dt_s > 0]) if (dt_s > 0).any() else 0.0
    gap = (dt_s > 3 * step) if step > 0 else np.zeros(len(dt_s), dtype=bool)
    dt_eff = np.where(gap, 0.0, dt_s)            # no displacement across a gap
    x_km = np.cumsum(rep['East speed (cm/s)'].to_numpy() / 100.0 * dt_eff) / 1000.0
    y_km = np.cumsum(rep['North speed (cm/s)'].to_numpy() / 100.0 * dt_eff) / 1000.0
    x_plot, y_plot = x_km.astype(float).copy(), y_km.astype(float).copy()
    x_plot[gap] = np.nan                          # break the line at each gap
    y_plot[gap] = np.nan
    ax.plot(x_plot, y_plot, '-', lw=1.2)
    ax.plot([0], [0], 'o', ms=6)
    ax.set_xlabel('East displacement (km)')
    ax.set_ylabel('North displacement (km)')
    n_gap = int(gap.sum())
    ax.set_title('Progressive vector at %.1f m - %s\n(%s to %s%s)'
                 % (rep_depth, label, t0.strftime('%d/%m/%Y %H:%M'),
                    ok['Datetime'].max().strftime('%d/%m/%Y %H:%M'),
                    '; %d gap(s) not integrated' % n_gap if n_gap else ''))
    ax.set_aspect('equal', adjustable='datalim'); ax.grid(alpha=0.3)
    p = os.path.join(out_dir, 'Progressive vector diagram.svg')
    fig.savefig(p, bbox_inches='tight'); files.append(p)
    _keep_or_close(fig, show, figures)
    if show and figures is None:
        show_panels(browse=True)      # one window, paged (owner, v13.0)
    return files


def plot_doppler_across_sites(database, out_dir, sites, settings=None, show=False,
                              figures=None):
    """Cross-site current comparison (the current analogue of the scalar
    'parameter across sites'): mean horizontal speed vs depth, one line per
    site, over GOOD cells. Returns the file list ([] if <2 sites have data).
    Honours the same time-window / depth-band settings as the per-site panels.
    """
    import os
    s = settings or {}
    os.makedirs(out_dir, exist_ok=True)
    df = database[database['Flag_cur'] != 4].copy()
    xs, xe = s.get('xAxisStart'), s.get('xAxisEnd')
    if xs is not None and xe is not None:
        df = df[(df['Datetime'] >= pd.Timestamp(xs)) & (df['Datetime'] <= pd.Timestamp(xe))]
    dmin, dmax = s.get('depthAxisMin'), s.get('depthAxisMax')
    if dmin is not None and dmax is not None:
        df = df[(df['Depth (m)'] >= float(dmin)) & (df['Depth (m)'] <= float(dmax))]
    df = df.dropna(subset=['Depth (m)', 'Horizontal speed (cm/s)'])

    colors = getSiteColors(sites)
    fig, ax = plt.subplots(figsize=(6.5, 8))
    n = 0
    for site in sites:
        sd = df[df['Site'] == site]
        if not len(sd):
            continue
        prof = sd.groupby('Depth (m)')['Horizontal speed (cm/s)'].mean().sort_index()
        if len(prof) < 2:
            continue
        ax.plot(prof.to_numpy(), prof.index.to_numpy(), '-o', ms=3, lw=1.2,
                color=colors.get(site), label=site)
        n += 1
    if n < 2:
        plt.close(fig)
        return []
    ax.invert_yaxis()
    ax.set_xlabel('Mean horizontal speed (cm/s)')
    ax.set_ylabel('Depth (m)')
    ax.set_title('Mean current speed by depth - across sites')
    ax.grid(alpha=0.3)
    ax.legend(fontsize=8)
    p = os.path.join(out_dir, 'Current mean speed across sites.svg')
    fig.savefig(p, bbox_inches='tight')
    _keep_or_close(fig, show, figures)
    if show and figures is None:
        show_panels(browse=True)
    return [p]

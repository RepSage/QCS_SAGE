import re
import math
import os
import numpy as np # type: ignore
import pandas as pd # type: ignore
import datetime as _dt # type: ignore
import matplotlib.pyplot as plt # type: ignore
import matplotlib.dates as _mdates # type: ignore
from matplotlib.lines import Line2D # type: ignore
from matplotlib.ticker import MaxNLocator # type: ignore
import QCS_Theme as _theme


def line_only_legend(legend):
    """Show line entries without markers, preserving point-only keys and data."""
    if legend is not None:
        for handle in legend.legend_handles:
            if (isinstance(handle, Line2D) and
                    str(handle.get_linestyle()).strip().lower() not in ('', 'none')):
                handle.set_marker('None')
    return legend


def show_panels(figures=None, browse=False):
    """Puts the panels produced so far on screen.

    A hook, not a helper: the tk shell keeps matplotlib's own windows
    (`plt.show()`); the Qt shell replaces it, because it runs on the Agg
    backend - where `plt.show()` does nothing at all - and opens the figures in
    its own windows instead (app icon, real title, navigation toolbar). The
    batch drivers leave it alone: with no display, `plt.show()` is already a
    no-op there.

    figures: the exact figures to show. None means 'every figure pyplot holds'.
    browse:  ask the shell for ONE window paging through the figures instead of
             one window per figure (owner, v13.0: the current panels opened as
             separate windows, which is noise for a comparison). Only a
             request - a shell that cannot page them shows them side by side.
    """
    plt.show()

####################################################################

# Safe bounds for a matplotlib DATE axis (well inside the hard year 1..9999
# limit). Zoom/pan is clamped to these so panning a time axis far out does not
# produce an out-of-range date ordinal that crashes the tick formatter.
_DATE_MIN = _mdates.date2num(_dt.datetime(100, 1, 1))
_DATE_MAX = _mdates.date2num(_dt.datetime(9000, 1, 1))

# Navigation stays finite, but zoom-out must be genuinely useful. The opening
# panel is the Home view, not a hard outer wall (v13.2.1 accidentally made it
# both). One hundred opening spans is generous while keeping numeric axes sane.
ZOOM_OUT_FACTOR = 100.0


def selected_year_bounds(years):
    """Full continuous calendar domain covered by selected years.

    A non-contiguous selection keeps the intervening calendar gap visible on
    the datetime axis; rows from unselected years are still filtered out.
    """
    clean = sorted({int(year) for year in (years or [])})
    if not clean:
        return None, None
    return (pd.Timestamp(year=clean[0], month=1, day=1),
            pd.Timestamp(year=clean[-1] + 1, month=1, day=1))


def _calendar_axis_bounds(dataViewSettings):
    """Visible multi-deployment domain: explicit crop or full years."""
    start = dataViewSettings.get('xAxisStart')
    end = dataViewSettings.get('xAxisEnd')
    if start is not None and end is not None:
        return pd.Timestamp(start), pd.Timestamp(end)
    return selected_year_bounds(dataViewSettings.get('filterByYears'))


def _format_calendar_datetime_axis(ax, start, end):
    """Use calendar ticks, adding clock time only for short custom windows."""
    if start is not None and end is not None:
        start = pd.Timestamp(start)
        end = pd.Timestamp(end)
        ax.set_xlim(start, end)
        span = end - start
    else:
        span = pd.Timedelta(days=abs(np.diff(ax.get_xlim())[0]))
    locator = _mdates.AutoDateLocator(minticks=3, maxticks=9)
    ax.xaxis.set_major_locator(locator)
    tick_format = ('%d/%m/%y %H:%M'
                   if span <= pd.Timedelta(days=7) else '%d/%m/%y')
    ax.xaxis.set_major_formatter(_mdates.DateFormatter(tick_format))
    ax.set_xlabel('Datetime')


def _source_display_name(source):
    """Compact provenance name for line selectors without losing identity."""
    text = str(source).strip()
    if not text or text.lower() in ('nan', '<na>', 'none'):
        return 'Selected data'
    return os.path.splitext(os.path.basename(text))[0]


def _name_plot_line(fig, line, role, source=None, site=None):
    """Give Figure options a semantic name independent of legend labels."""
    parts = [str(value).strip() for value in (site, role)
             if value is not None and str(value).strip()]
    if source is not None:
        parts.append(_source_display_name(source))
    fig.__dict__.setdefault('_qcs_line_names', {})[line] = ' - '.join(parts)
    return line

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


def _elapsed_days_axis(ax, max_day):
    """Common deployment-relative axis for campaigns sampled on different dates."""
    upper = max(float(max_day), 1.0)
    ax.set_xlim(0.0, upper)
    ax.xaxis.set_major_locator(MaxNLocator(nbins=9, min_n_ticks=3))
    ax.set_xlabel("Elapsed days since each deployment's first selected day")


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


def tendency_lines_available(instrument, parameters):
    """Whether the selected variables contain a series QCS actually fits.

    HOBO luminosity is represented by its source-aware daily-peak envelope,
    not by a polynomial tendency. Temperature remains fit-capable, including
    when it is selected together with luminosity.
    """
    selected = set(parameters or ())
    return not (instrument == 'HOBO'
                and selected == {'Luminosity (lux)'})


def data_points_available(instrument, parameters):
    """Whether Show data points can add a meaningful raw-point layer.

    HOBO light is intentionally represented only by its daily-peak series.
    Dense nighttime raw readings otherwise resemble a dashed baseline.
    """
    selected = set(parameters or ())
    return not (instrument == 'HOBO'
                and selected == {'Luminosity (lux)'})


def disagreement_bars_available(instrument, parameters):
    """Whether the selection can contain HOBO replicate-temperature spread."""
    return (instrument == 'HOBO'
            and 'Temperature (degC)' in set(parameters or ()))


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

    Fixed-scale defaults span every value the panel draws (see
    _param_data_extreme).  This remains a guard for a manually narrowed scale:
    an operator can intentionally choose bounds that leave plotted values out,
    but the application must say so instead of making them look missing.
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


def enable_scroll_zoom(fig, fit=True):
    """Interaction for a shown panel: mouse-wheel zoom around the cursor,
    middle-button drag to pan, and the plotted limits remembered on the figure
    so the toolbar's home button returns to them. Call it right before the
    panel is shown (after all axes have their final limits)."""
    # Most scalar panels need a final margin pass. Doppler lays out its compass
    # explicitly, so its callers disable this pass to preserve that alignment.
    if fit:
        _fit_margins(fig)
    _report_points_outside(fig)
    # snapshot the original plotted view for Reset
    original = [(ax, ax.get_xlim(), ax.get_ylim()) for ax in fig.axes]
    opening = {ax: (xl, yl) for ax, xl, yl in original}

    def _bounded_zoom(limits, opening_limits):
        """Keep wheel zoom between 1/10,000 and 100x the opening span."""
        lo, hi = limits
        opening_span = abs(opening_limits[1] - opening_limits[0])
        minimum = max(
            opening_span / 10_000.0,
            max(abs(opening_limits[0]), abs(opening_limits[1]), 1.0) *
            np.finfo(float).eps * 64)
        span = abs(hi - lo)
        target = min(max(span, minimum), opening_span * ZOOM_OUT_FACTOR)
        if abs(target - span) <= np.finfo(float).eps * max(span, 1.0):
            return limits
        centre = (lo + hi) / 2.0
        lower, upper = centre - target / 2.0, centre + target / 2.0
        return (lower, upper) if hi >= lo else (upper, lower)

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
        if event.inaxes is None or not event.inaxes.get_navigate():
            return
        axes = _overlaid_axes(event.inaxes)
        if not axes:
            return
        scale = 1 / ZOOM if event.button == 'up' else ZOOM   # wheel up = zoom in
        ref = event.inaxes
        xd, _ = ref.transData.inverted().transform((event.x, event.y))
        xl = ref.get_xlim()
        new_xlim = (
            xd - (xd - xl[0]) * scale,
            xd + (xl[1] - xd) * scale)
        new_xlim = _bounded_zoom(new_xlim, opening[ref][0])
        new_xlim = _clamp_x(ref, *new_xlim)
        for ax in axes:
            ax.set_xlim(new_xlim)          # shared x: same absolute value, no compounding
            _, yd = ax.transData.inverted().transform((event.x, event.y))
            yl = ax.get_ylim()
            new_ylim = (yd - (yd - yl[0]) * scale,
                        yd + (yl[1] - yd) * scale)
            ax.set_ylim(_bounded_zoom(new_ylim, opening[ax][1]))
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

    # The house icon restores the opening view. The Qt shell supplies the shared
    # QCS toolbar; its Back/Forward history is intentionally omitted because it
    # cannot represent these wheel and middle-button interactions.
    fig._qcs_reset_view = reset_view      # the view the panel opened with

    # app icon + a meaningful window title (the plot's own title, so the taskbar
    # and window name say what is being shown instead of 'Figure 1')
    # A panel family may already have assigned its operator-facing name. Do not
    # replace it with an internal axes title (the Doppler compass, for example,
    # is titled "Direction [deg]" but the window is "Current profile").
    if not getattr(fig, '_qcs_window_title', ''):
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


def getDepthContextColors():
    """Keep working-depth and handling markers distinct in manual reviews."""
    return {'working_depth': '#228b22', 'handling': '#b30000'}


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
            line_only_legend(ax1.legend(loc='best', fontsize=8))

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
        elif re.search(r'\bPAR\b', variable, re.IGNORECASE):
            ax1.set_ylim(SETTINGS['env_min_PAR'], SETTINGS['env_max_PAR'])
        elif re.search('luminosity|lux', variable, re.IGNORECASE):
            ax1.set_ylim(SETTINGS.get('env_min_lux', 0),
                         SETTINGS.get('env_max_lux', 200000))

    if re.search('depth', variable, re.IGNORECASE):
        ax1.invert_yaxis()

    ax1.set_title('Site: %s   /   %s  to  %s' % (qualified_data['Site'].iloc[0],
                                                 t_start.strftime('%d/%m/%Y'),
                                                 t_end.strftime('%d/%m/%Y')))
    plt.savefig(dataview_path + '/' + re.search(r'^[^\(]+',variable, re.IGNORECASE).group().strip() + ' series.svg', bbox_inches='tight', dpi=100)
    plt.close(fig)

def plot_variable_profile(qualified_data, raw_data, variable, dataview_path, SETTINGS, fixed_scale):
    depth = pd.to_numeric(qualified_data['Depth (m)'], errors='coerce')
    values = pd.to_numeric(qualified_data[variable], errors='coerce')
    if not (np.isfinite(depth) & np.isfinite(values)).any():
        print('Info: %s profile not drawn: no finite measurement/depth pair.' % variable)
        return
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
        elif re.search(r'\bPAR\b', variable, re.IGNORECASE):
            ax1.set_xlim(SETTINGS['env_min_PAR'], SETTINGS['env_max_PAR'])
        elif re.search('luminosity|lux', variable, re.IGNORECASE):
            ax1.set_xlim(SETTINGS.get('env_min_lux', 0),
                         SETTINGS.get('env_max_lux', 200000))

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
    """Polynomial tendency against real elapsed time, not sample position.

    Uneven sampling and multi-year selections made the old ordinal fit treat
    two adjacent rows as equally separated even when they were months apart.
    Duplicate timestamps are averaged for the fit, missing values are omitted,
    and the time coordinate is normalized before ``polyfit`` for stability.
    """
    values = pd.to_numeric(pd.Series(y, copy=False), errors='coerce')
    times = pd.to_datetime(values.index, errors='coerce')
    fit_frame = pd.DataFrame({
        'Datetime': times,
        'Value': values.to_numpy(),
    }).dropna(subset=['Datetime', 'Value'])
    if fit_frame.empty:
        return pd.DatetimeIndex([]), np.asarray([], dtype=float)
    fit_frame = (fit_frame.groupby('Datetime', as_index=False, sort=True)['Value']
                 .mean())
    xi = pd.DatetimeIndex(fit_frame['Datetime'])
    yi = fit_frame['Value'].to_numpy(dtype=float)
    fit_degree = min(max(int(degree), 0), len(yi) - 1)
    if fit_degree == 0:
        return xi, np.full(len(yi), float(np.mean(yi)))
    elapsed = (xi - xi.min()).total_seconds().to_numpy(dtype=float) / 86400.0
    center = float(np.mean(elapsed))
    scale = float(np.max(np.abs(elapsed - center)))
    normalized = (elapsed - center) / scale if scale else elapsed
    coefficients = np.polyfit(normalized, yi, fit_degree)
    return xi, np.polyval(coefficients, normalized)

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
                    ax1.plot(x, y, color=bcParam[y_list[0].name],
                             linestyle='None', marker='.', markersize=3,
                             label=rParam[0])
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
                            ax.plot(x, y, linestyle='None', marker='.',
                                    markersize=3,
                                    c=bcParam[y_list[i-1].name],
                                    label=rParam[i-1])
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
                figure_axes = list(axes.values())
                fig._qcs_customize_axes = list(
                    zip(rParam, figure_axes, strict=True))
                fig._qcs_axes_names = dict(
                    zip(figure_axes, rParam, strict=True))
                plt.savefig('panel1_%s_%s_%d.svg'%(site, semester, year), bbox_inches='tight')
                enable_scroll_zoom(fig)
                show_panels()

def plot_database_panel2(database, dataViewSettings):
    """
    Compare each parameter across sites on elapsed time from each site's first
    selected sample; timestamps do not need to coincide.

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
    # The absolute window first selects the calendar rows. Each site's
    # surviving series is then overlaid on elapsed time, so no timestamp match
    # between deployments is required.
    db_raw = _apply_time_window(db_raw, dataViewSettings)
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
            # the year lives on the X axis since v12.0 (title drops it)
            plt.title(f'{display_param} on {_SEM_LABEL.get(semester, semester)} for each site')
            plt.grid(True, linestyle='dotted', linewidth=0.5)
            ax1.set_ylabel(display_param)
            control = 0
            max_day = 0.0

            for site in site_names:
                # Extract data for the specific site
                y = db[semester].copy()
                y = y[parameter][(y.loc[:,'Site'] == site)]
                y = y.loc[~(y.index.duplicated(keep=False) & y.isna())]

                if not y.empty:
                    site_origin = y.index.min()

                if y.empty:
                    if not db[semester].empty:   # skip the noise for an empty semester
                        print(f'\nNo {parameter} data for {site} during {year} {semester}.')
                    continue

                control += 1
                y, gap_ids = fill_NaT_gap(y)  # Fill gaps
                x_days = (y.index - site_origin).total_seconds() / 86400
                max_day = max(max_day, float(np.nanmax(x_days)))

                # Plotting the data. Pressure is NEVER fitted (tidal signal: a
                # polynomial through it is meaningless) - its raw series is drawn
                # as a dashed line instead, the same rule used in Panel 1.
                if fit_lin_regression and parameter == 'Pressure (dbar)':
                    ax1.plot(x_days, y, linestyle='--', marker='None',
                            color=colors[site], label=f'{site} data')
                elif fit_lin_regression:
                    xp, yp = linear_regression(y, degree=deg)
                    yp = _floor_fit(yp)
                    xp_days = (xp - site_origin).total_seconds() / 86400

                    if points:
                        ax1.plot(x_days, y, linestyle='none', marker='.',
                                color=colors[site], markersize=3, label=f'{site} data')
                        ax1.plot(xp_days, yp, linestyle='-',
                                color=colors[site], label=f'{site} tendency')
                    else:
                        ax1.plot(xp_days, yp, linestyle='-',
                                color=colors[site], label=f'{site} tendency')
                else:
                        ax1.plot(x_days, y, linestyle='none', marker='.',
                                color=colors[site], markersize=3, label=f'{site} data')

            # Plot settings
            if control == 0:
                plt.close(fig)
                continue

            _elapsed_days_axis(ax1, max_day)

            # Legend and layout
            line_only_legend(ax1.legend(
                loc='upper left', bbox_to_anchor=(1, 1.01), fontsize=7))
            plt.subplots_adjust(left=0.10, right=0.80, top=0.88, bottom=0.14)  # room for the y label + x labels

            # Fixed scale if needed
            if dataViewSettings['fixedScale'] and parameter in dataViewSettings['scaleSettings']:
                ax1.set_ylim(dataViewSettings['scaleSettings'][parameter]['min'],
                            dataViewSettings['scaleSettings'][parameter]['max'])

            # Strip parentheses from the file name
            parameter_r = re.sub(r'\([^()]*\)', '', parameter).strip()
            fig._qcs_customize_axes = [(display_param, ax1)]
            fig._qcs_axes_names = {ax1: display_param}
            plt.savefig(f'panel2_{parameter_r}_{semester}_{year}.svg')
            enable_scroll_zoom(fig)
            show_panels()


def _scalar_calendar_slice(database, dataViewSettings, site=None,
                           time_window=True):
    """Selected scalar-mooring rows on one absolute calendar axis."""
    years = dataViewSettings.get('filterByYears') or []
    if not years and dataViewSettings.get('filterByYear') is not None:
        years = [dataViewSettings['filterByYear']]
    db = database
    if years:
        db = db[db['Datetime'].dt.year.isin(years)]
    if site is not None:
        db = db[db['Site'] == site]
    elif dataViewSettings.get('siteList'):
        db = db[db['Site'].isin(dataViewSettings['siteList'])]
    if time_window:
        db = _apply_time_window(db, dataViewSettings)
    return db.sort_values('Datetime')


def deployment_count(database, dataViewSettings, site=None):
    """Count selected source products; fall back to sites without provenance."""
    db = _scalar_calendar_slice(
        database, dataViewSettings, site=site, time_window=False)
    if db.empty:
        return 0
    if 'Source file' in db.columns:
        columns = ['Source file']
        if 'Site' in db.columns:
            columns.insert(0, 'Site')
        return len(db[columns].fillna('Selected data').drop_duplicates())
    if 'Site' in db.columns:
        return int(db['Site'].nunique(dropna=False))
    return 1


def is_multi_deployment_selection(database, dataViewSettings):
    """Whether scalar mooring plots should use the combined calendar view."""
    return deployment_count(database, dataViewSettings) > 1


def _deployment_parameter_series(deployment, parameter):
    """Numeric deployment series with the established visible-gap rule."""
    values = pd.to_numeric(deployment[parameter], errors='coerce')
    series = pd.Series(
        values.to_numpy(), index=pd.DatetimeIndex(deployment['Datetime']),
        name=parameter)
    series = series.loc[
        ~(series.index.duplicated(keep=False) & series.isna())]
    if not series.notna().any():
        return series
    series, _gap_ids = fill_NaT_gap(series)
    return series


def _scalar_panel_axis_layout(parameter_count):
    """Opening geometry for a scalar Panel 1 with stacked parameter axes."""
    n_right = max(0, parameter_count - 1)
    total_px, height_px, left_px = 1050, 540, 78
    max_zone = total_px - left_px - 560
    spacing = (min(60.0, max(22.0, (max_zone - 95) / (n_right - 1)))
               if n_right > 1 else 60.0)
    actual_zone = min(
        max_zone, ((n_right - 1) * spacing + 95) if n_right >= 1 else 40)
    plot_px = total_px - left_px - actual_zone
    font_scale = min(1.0, max(0.55, spacing / 58.0))
    bins = 6 if n_right >= 4 else 8
    return (total_px, height_px, left_px, plot_px, spacing, font_scale, bins)


def plot_scalar_multi_params_at_site(database, dataViewSettings, site,
                                     figures=None, show=True):
    """Scalar mooring Panel 1 for several source deployments in calendar time."""
    db = _scalar_calendar_slice(database, dataViewSettings, site=site)
    parameters = [
        parameter for parameter in dataViewSettings['parameterList']
        if parameter in db.columns and
        pd.to_numeric(db[parameter], errors='coerce').notna().any()]
    if db.empty or not parameters:
        print('\nNo scalar mooring data to plot for %s.' % site)
        return 0

    colors, bold_colors = getParamColors()
    displays = renameParameters(parameters)
    fit = dataViewSettings['tendencyLines']
    degree = dataViewSettings['linearRegressionDegree']
    points = dataViewSettings['viewDataPoints']
    (total_px, height_px, left_px, plot_px, spacing,
     font_scale, bins) = _scalar_panel_axis_layout(len(parameters))
    fig, ax1 = plt.subplots(figsize=(total_px / 100, height_px / 100))
    fig.subplots_adjust(
        left=left_px / total_px,
        right=(left_px + plot_px) / total_px, bottom=0.18)
    ax1.grid(True, linestyle='dotted', linewidth=0.5)
    axes = []
    outward = 0.0

    for index, (parameter, display) in enumerate(
            zip(parameters, displays, strict=True)):
        ax = ax1 if index == 0 else ax1.twinx()
        axes.append(ax)
        fitted_values = []
        plotted = False
        for source, deployment in _source_deployments(db):
            series = _deployment_parameter_series(deployment, parameter)
            if not series.notna().any():
                continue
            plotted = True
            if parameter == 'Pressure (dbar)':
                line, = ax.plot(
                    series.index, series.values, linestyle='--', marker='None',
                    color=bold_colors[parameter])
                _name_plot_line(
                    fig, line, '%s data' % display, source=source)
                continue
            enough_for_fit = (
                fit and series.notna().sum() > max(3, int(degree or 1)))
            if points or not enough_for_fit:
                ax.plot(
                    series.index, series.values, linestyle='None', marker='.',
                    markersize=3, color=(colors[parameter] if fit
                                         else bold_colors[parameter]))
            if enough_for_fit:
                xp, yp = linear_regression(series, degree=degree)
                yp = _floor_fit(yp)
                line, = ax.plot(
                    xp, yp, linestyle='-', color=bold_colors[parameter])
                _name_plot_line(
                    fig, line, '%s tendency' % display, source=source)
                fitted_values.extend(np.asarray(yp, dtype=float))
        if not plotted:
            ax.set_visible(False)
            continue
        if fit and not points and fitted_values:
            low = float(np.nanmin(fitted_values))
            high = float(np.nanmax(fitted_values))
            margin = 0.05 * abs(high - low)
            ax.set_ylim(max(0.0, low - margin), high + margin)
        ax.set_ylabel(
            display, color=bold_colors[parameter], fontsize=10 * font_scale)
        ax.tick_params(
            axis='y', colors=bold_colors[parameter],
            labelsize=10 * font_scale)
        ax.yaxis.set_major_locator(MaxNLocator(nbins=bins, prune='both'))
        if index == 0:
            ax.spines['left'].set_color(bold_colors[parameter])
            ax.spines['left'].set_position(('outward', 1))
            ax.spines['left'].set_linewidth(2.0)
        else:
            if index > 1:
                ax.spines['right'].set_position(('outward', outward))
            outward += spacing
            ax.spines['right'].set_color(bold_colors[parameter])
            ax.spines['right'].set_linewidth(1.5)
            ax.spines['left'].set_color('none')
        if (dataViewSettings.get('fixedScale') and
                parameter in dataViewSettings.get('scaleSettings', {})):
            scale = dataViewSettings['scaleSettings'][parameter]
            ax.set_ylim(scale['min'], scale['max'])

    ax1.set_title('Parameters for %s across deployments' % site)
    axis_start, axis_end = _calendar_axis_bounds(dataViewSettings)
    _format_calendar_datetime_axis(ax1, axis_start, axis_end)
    _fit_stacked_yticks(fig, spacing)
    visible_axes = [ax for ax in axes if ax.get_visible()]
    visible_names = [display for display, ax in zip(
        displays, axes, strict=True) if ax.get_visible()]
    fig._qcs_customize_axes = list(zip(
        visible_names, visible_axes, strict=True))
    fig._qcs_axes_names = dict(zip(
        visible_axes, visible_names, strict=True))
    _name_panel(fig, 'Parameters across deployments', site)
    years = dataViewSettings.get('filterByYears') or []
    year_tag = '%d-%d' % (min(years), max(years)) if years else 'selected'
    plt.savefig(
        'panel1_%s_%s.svg' % (site, year_tag), bbox_inches='tight')
    enable_scroll_zoom(fig)
    _keep_or_close(fig, show, figures)
    if show and figures is None:
        show_panels([fig])
    return 1


def plot_scalar_multi_params_across_sites(database, dataViewSettings,
                                          figures=None, show=True):
    """Scalar mooring Panel 2 across sites and products in calendar time."""
    sites = dataViewSettings['siteList']
    parameters = [
        parameter for parameter in dataViewSettings['parameterList']
        if parameter in database.columns]
    colors = getSiteColors(sites)
    fit = dataViewSettings['tendencyLines']
    degree = dataViewSettings['linearRegressionDegree']
    points = dataViewSettings['viewDataPoints']
    figure_count = 0

    for parameter, display in zip(
            parameters, renameParameters(parameters), strict=True):
        fig, ax = plt.subplots(figsize=(10.5, 5.4))
        fig.subplots_adjust(left=0.10, right=0.80, top=0.88, bottom=0.18)
        ax.grid(True, linestyle='dotted', linewidth=0.5)
        plotted_sites = []
        for site in sites:
            db = _scalar_calendar_slice(
                database, dataViewSettings, site=site)
            if db.empty or not pd.to_numeric(
                    db[parameter], errors='coerce').notna().any():
                print('\nNo %s data for %s in the selected calendar domain.' %
                      (parameter, site))
                continue
            site_plotted = False
            for source, deployment in _source_deployments(db):
                series = _deployment_parameter_series(deployment, parameter)
                if not series.notna().any():
                    continue
                site_plotted = True
                if parameter == 'Pressure (dbar)':
                    line, = ax.plot(
                        series.index, series.values, linestyle='--',
                        marker='None', color=colors[site])
                    _name_plot_line(
                        fig, line, '%s data' % display,
                        source=source, site=site)
                    continue
                enough_for_fit = (
                    fit and series.notna().sum() > max(3, int(degree or 1)))
                if points or not enough_for_fit:
                    ax.plot(
                        series.index, series.values, linestyle='None',
                        marker='.', markersize=3, color=colors[site])
                if enough_for_fit:
                    xp, yp = linear_regression(series, degree=degree)
                    yp = _floor_fit(yp)
                    line, = ax.plot(
                        xp, yp, linestyle='-', color=colors[site])
                    _name_plot_line(
                        fig, line, '%s tendency' % display,
                        source=source, site=site)
            if site_plotted:
                plotted_sites.append(site)

        if not plotted_sites:
            plt.close(fig)
            continue
        axis_start, axis_end = _calendar_axis_bounds(dataViewSettings)
        _format_calendar_datetime_axis(ax, axis_start, axis_end)
        ax.set_ylabel(display)
        ax.set_title('%s across sites and deployments' % display)
        if (dataViewSettings.get('fixedScale') and
                parameter in dataViewSettings.get('scaleSettings', {})):
            scale = dataViewSettings['scaleSettings'][parameter]
            ax.set_ylim(scale['min'], scale['max'])
        legend_handles = [
            Line2D(
                [0], [0], color=colors[site],
                linestyle=('--' if parameter == 'Pressure (dbar)'
                           else ('-' if fit else 'None')),
                marker='.' if points or not fit else 'None')
            for site in plotted_sites]
        line_only_legend(ax.legend(
            legend_handles, plotted_sites, loc='upper left',
            bbox_to_anchor=(1, 1.01), fontsize=7))
        fig._qcs_customize_axes = [(display, ax)]
        fig._qcs_axes_names = {ax: display}
        _name_panel(fig, '%s across sites and deployments' % display)
        years = dataViewSettings.get('filterByYears') or []
        year_tag = '%d-%d' % (min(years), max(years)) if years else 'selected'
        parameter_tag = re.sub(r'\([^()]*\)', '', parameter).strip()
        plt.savefig(
            'panel2_%s_%s.svg' % (parameter_tag, year_tag),
            bbox_inches='tight')
        enable_scroll_zoom(fig)
        _keep_or_close(fig, show, figures)
        figure_count += 1
    if show and figures is None and figure_count:
        show_panels(browse=figure_count > 1)
    return figure_count

def plot_database_panel3(database, dataViewSettings):
    site_names = dataViewSettings['siteList']
    parameter_names = dataViewSettings['parameterList']
    year = dataViewSettings['filterByYear']
    fit_lin_regression = dataViewSettings['tendencyLines']
    deg = dataViewSettings['linearRegressionDegree']
    points = dataViewSettings['viewDataPoints']

    db_raw = database.copy()
    if not np.isfinite(pd.to_numeric(db_raw['Depth (m)'], errors='coerce')).any():
        print('Info: vertical profile panels not drawn: no finite depth coordinate.')
        return
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
                line_only_legend(ax1.legend(
                    handles=legend_handles, labels=legend_labels,
                    loc='upper center', bbox_to_anchor=(1.1, 1.01),
                    ncol=1, fontsize=7))

                figure_axes = list(axes.values())
                fig._qcs_customize_axes = list(
                    zip(rParam, figure_axes, strict=True))
                fig._qcs_axes_names = dict(
                    zip(figure_axes, rParam, strict=True))
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
    line_only_legend(ax.legend(loc='lower left', fontsize=8))
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


def _usable_lux(db):
    """Numeric light with qualified BAD samples removed from visualization."""
    lux = pd.to_numeric(db['Luminosity (lux)'], errors='coerce')
    if 'Flag_lux' in db.columns:
        flags = pd.to_numeric(db['Flag_lux'], errors='coerce')
        lux = lux.mask(flags.eq(4))
    return lux


def _lux_daily_peak (db):
    """Daily maximum of usable light as a gap-preserving Series.

    ``Flag_lux == 4`` samples are removed BEFORE resampling, so a cutoff in the
    middle of a day does not discard earlier usable readings from that day.
    Empty days stay NaN and visibly break the plotted line.
    """
    lux = _usable_lux(db)
    s = pd.Series(lux.values, index=pd.DatetimeIndex(db['Datetime']))
    return s.resample('D').max()


def _source_deployments(db):
    """Chronological deployment slices from preserved source provenance.

    Curated workbooks keep the original ``Source file`` written by
    ``build_database``. Treating all products at one site as one time series
    pooled sensors, connected campaigns and fitted trends across deployments.
    A standalone frame without provenance remains one deployment.
    """
    if db.empty:
        return []
    groups = (db.groupby('Source file', dropna=False, sort=False)
              if 'Source file' in db.columns else [('Selected data', db)])
    deployments = []
    for source, group in groups:
        group = group.sort_values('Datetime')
        valid = pd.to_datetime(group['Datetime'], errors='coerce').notna()
        group = group.loc[valid].copy()
        if not group.empty:
            deployments.append((str(source), group))
    deployments.sort(key=lambda item: item[1]['Datetime'].min())
    return deployments


def plot_hobo_params_at_site (database, dataViewSettings, site,
                              figures=None, show=True):
    """HOBO 'Parameters at a site': the selected parameters (temperature and/or
    light) for ONE site in a single figure on the continuous calendar domain of
    every selected year. Only rows in those years and the optional Time window
    are drawn. Temperature: dots + optional
    replicate-disagreement bars + one tendency per deployment (floored at 0).
    Light: LINEAR scale with one gap-aware DAILY-PEAK envelope per deployment
    and optional raw points; Flag_lux == 4 samples are not plotted.
    Returns the number of figures generated (0 or 1)."""
    cParam, bcParam = getParamColors()
    db = _hobo_slice_years(database, dataViewSettings, site)
    params = []
    for param in dataViewSettings['parameterList']:
        if (param not in ('Temperature (degC)', 'Luminosity (lux)')
                or param not in db.columns):
            continue
        values = (_usable_lux(db) if param == 'Luminosity (lux)'
                  else pd.to_numeric(db[param], errors='coerce'))
        if values.notna().any():
            params.append(param)
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
                tendency_added = False
                for source, deployment in _source_deployments(db):
                    dep_temp = pd.to_numeric(
                        deployment['Temperature (degC)'], errors='coerce')
                    s = pd.Series(dep_temp.values,
                                  index=pd.DatetimeIndex(deployment['Datetime'])).dropna()
                    if len(s) > 3:
                        xp, yp = linear_regression(s, degree=deg)
                        yp = _floor_fit(yp)
                        h, = ax.plot(
                            xp, yp, linestyle='-', color=bcParam[param],
                            label=('Temperature tendency (each deployment)'
                                   if not tendency_added else None))
                        _name_plot_line(
                            fig, h, 'Temperature tendency', source=source)
                        if not tendency_added:
                            handles.append(h)
                            tendency_added = True
        else:
            # Light stays source-aware: each qualified deployment has its own
            # daily envelope, and NaN days break the line across data gaps.
            # Do not overlay raw readings: their dense nighttime values form a
            # misleading dotted baseline and add no information to the daily
            # peak representation.
            peak_added = False
            for source, deployment in _source_deployments(db):
                peak = _lux_daily_peak(deployment)
                if not peak.notna().any():
                    continue
                h, = ax.plot(
                    peak.index, peak.values, linestyle='-', marker='.',
                    markersize=4, lw=1.2, color=bcParam[param],
                    label=('Daily light peak (each deployment)'
                           if not peak_added else None))
                _name_plot_line(fig, h, 'Daily light peak', source=source)
                if not peak_added:
                    handles.append(h)
                    peak_added = True
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
    axis_start, axis_end = _calendar_axis_bounds(dataViewSettings)
    _format_calendar_datetime_axis(ax1, axis_start, axis_end)
    line_only_legend(ax1.legend(handles=handles, fontsize=8))
    _name_panel(fig, 'HOBO parameters', site)
    plt.savefig('hobo_params_%s.svg' % site, bbox_inches='tight')
    enable_scroll_zoom(fig)
    _keep_or_close(fig, show, figures)
    if show and figures is None:
        show_panels([fig])
    return 1


def plot_hobo_params_across_sites (database, dataViewSettings,
                                   figures=None, show=True):
    """HOBO 'Parameters across sites': ONE figure per selected parameter with
    every selected deployment kept on its absolute datetime, spanning the full
    continuous calendar domain of the selected years in one plot. The optional
    Time window narrows both the rows and the visible domain; no timestamp match
    between sites is required.
    Temperature: dots + optional per-deployment tendency (floored at 0). Light:
    a gap-aware daily-peak envelope per deployment (linear scale), excluding
    Flag_lux == 4 samples. Returns the number of figures generated."""
    site_names = dataViewSettings['siteList']
    params = [p for p in dataViewSettings['parameterList']
              if p in ('Temperature (degC)', 'Luminosity (lux)')]
    colors = getSiteColors(site_names)
    fit = dataViewSettings['tendencyLines']
    deg = dataViewSettings['linearRegressionDegree']
    points = dataViewSettings['viewDataPoints']

    n_figs = 0
    for param in params:
        display = renameParameters([param])[0]
        fig, ax = plt.subplots(figsize=(1050 / 100, 540 / 100))
        plt.subplots_adjust(bottom=0.14)
        plt.xticks(rotation=35)
        ax.grid(True, linestyle='dotted', linewidth=0.5)
        plotted = 0
        for site in site_names:
            db = _hobo_slice_years(database, dataViewSettings, site)
            if db.empty or param not in db.columns:
                print('\nNo %s data for %s.' % (param, site))
                continue
            values = (_usable_lux(db) if param == 'Luminosity (lux)'
                      else pd.to_numeric(db[param], errors='coerce'))
            if not values.notna().any():
                print('\nNo %s data for %s.' % (param, site))
                continue
            label_added = False
            if param == 'Luminosity (lux)':
                for source, deployment in _source_deployments(db):
                    values = _usable_lux(deployment)
                    if not values.notna().any():
                        continue
                    peak = _lux_daily_peak(deployment)
                    if peak.first_valid_index() is None:
                        continue
                    if peak.notna().any():
                        line, = ax.plot(
                            peak.index, peak.values, linestyle='-',
                            marker='.', markersize=4, lw=1.2,
                            color=colors[site],
                            label=site if not label_added else None)
                        _name_plot_line(
                            fig, line, 'Daily light peak',
                            source=source, site=site)
                        label_added = True
            else:
                for source, deployment in _source_deployments(db):
                    values = pd.to_numeric(
                        deployment['Temperature (degC)'], errors='coerce')
                    if not values.notna().any():
                        continue
                    if fit:
                        s = pd.Series(
                            values.values,
                            index=pd.DatetimeIndex(deployment['Datetime'])).dropna()
                        if points:
                            ax.plot(
                                deployment['Datetime'], values,
                                linestyle='None', marker='.',
                                markersize=3, color=colors[site],
                                label=site if not label_added else None)
                            label_added = True
                        if len(s) > 3:
                            xp, yp = linear_regression(s, degree=deg)
                            yp = _floor_fit(yp)
                            line, = ax.plot(
                                xp, yp, linestyle='-', color=colors[site],
                                label=site if not label_added else None)
                            _name_plot_line(
                                fig, line, 'Temperature tendency',
                                source=source, site=site)
                            label_added = True
                    else:
                        ax.plot(
                            deployment['Datetime'], values,
                            linestyle='None', marker='.',
                            markersize=3, color=colors[site],
                            label=site if not label_added else None)
                        label_added = True
            plotted += 1
        if plotted == 0:
            plt.close(fig)
            print('\nNo %s data for any selected site.' % param)
            continue
        axis_start, axis_end = _calendar_axis_bounds(dataViewSettings)
        _format_calendar_datetime_axis(ax, axis_start, axis_end)
        ax.set_ylabel(display)
        ax.set_title('HOBO %s across sites' % display)
        if dataViewSettings.get('fixedScale') and param in dataViewSettings.get('scaleSettings', {}):
            ax.set_ylim(dataViewSettings['scaleSettings'][param]['min'],
                        dataViewSettings['scaleSettings'][param]['max'])
        handles, labels = ax.get_legend_handles_labels()
        line_only_legend(ax.legend(handles, labels, fontsize=8, loc='best'))
        _name_panel(fig, 'HOBO %s across sites' % display)
        param_r = re.sub(r'\([^()]*\)', '', param).strip().replace(' ', '_')
        plt.savefig('hobo_%s_across_sites.svg' % param_r, bbox_inches='tight')
        enable_scroll_zoom(fig)
        _keep_or_close(fig, show, figures)
        n_figs += 1
    if show and figures is None and n_figs:
        show_panels(browse=n_figs > 1)
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
            if not np.isfinite(pd.to_numeric(db[semester]['Depth (m)'], errors='coerce')).any():
                print('Info: depth-colored T-S diagram not drawn: no finite depth coordinate.')
                continue
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
            line_only_legend(plt.legend(handles=custom_handles))
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
    line_only_legend(ax.legend(fontsize=8, loc='best'))
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


def _name_panel(fig, panel, label=''):
    """Give exported and browsed panels one stable, directly selectable name."""
    title = '%s - %s' % (label, panel) if label else panel
    fig._qcs_window_title = title
    _theme.style_plot_window(fig, title)


def _date_axis(ax, fig=None, rotation=45):
    """Makes a time axis on a current panel readable.

    The scalar panels establish the program's datetime notation as
    day/month/two-digit-year plus hour:minute. Doppler used ConciseDateFormatter
    instead, which split the date between the ticks and an offset label. Keep
    the same notation as the scalar panels while retaining the capped locator,
    45-degree rotation and right anchoring that prevent overprinting."""
    import matplotlib.dates as mdates
    locator = mdates.AutoDateLocator(minticks=3, maxticks=9)
    ax.xaxis.set_major_locator(locator)
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%d/%m/%y %H:%M'))
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


def _coordinate_edges(values, singleton_width):
    """Convert ordered cell centres to pcolormesh edges.

    Matplotlib cannot infer a cell height from one centre: it duplicates that
    coordinate and draws a zero-height mesh. The explicit singleton width is
    therefore part of the caller's physical/time coordinate system.
    """
    values = np.asarray(values, dtype=float)
    if len(values) == 1:
        half = float(singleton_width) / 2.0
        return np.array([values[0] - half, values[0] + half])
    middle = (values[:-1] + values[1:]) / 2.0
    return np.concatenate(([values[0] - (middle[0] - values[0])], middle,
                           [values[-1] + (values[-1] - middle[-1])]))


def doppler_available_depths(frame):
    """Configured cell centres, including rejected cells shown by the QC grid."""
    if frame is None or 'Depth (m)' not in frame.columns:
        return pd.Series(dtype=float)
    depth = pd.to_numeric(frame['Depth (m)'], errors='coerce')
    return depth[depth.notna()]


def _direction_compass(fig, slot, align_ax, cmap, label_font=None,
                       tick_font=None):
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
    # The date formatter adjusts the subplot layout before this function is
    # called. Centre the absolute polar axes vertically on the direction
    # heatmap, while the spent colorbar's left edge anchors a dedicated key
    # column to the right. Creating the wheel before subplots_adjust left it
    # below the plot; centring its wide title on the thin bar made the text
    # overlap the data (owner, 2026-08-20).
    fig.canvas.draw()
    pos = slot.get_position()
    target = align_ax.get_position()
    side_x = 0.085                                  # figure fractions...
    side_y = side_x * fig.get_figwidth() / fig.get_figheight()   # ...kept round
    centre_y = target.y0 + target.height / 2.0
    wheel = fig.add_axes([pos.x0, centre_y - side_y / 2.0,
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
    wheel.set_in_layout(False)     # tight_layout moves its heatmap, not the key
    wheel.set_navigate(False)       # it is a key, never a zoomable data axes
    return wheel


def getCurrentColors():
    """Shared palette for current values, coverage and independent QC layers."""
    return {'speed_map': 'viridis', 'direction_map': 'twilight',
            'coverage_map': 'Blues', 'diagnostic_map': 'YlOrRd',
            'missing': '#eeeeee', 'good': '#228b22', 'suspect': '#e6a000',
            'bad': '#b30000', 'unknown': '#bdbdbd', 'dismissed': '#6a51a3',
            'zero': '#777777', 'vector': '#2878b5', 'candidate': '#111111',
            'lines': ['#2878b5', '#d97716', '#228b22', '#9c3d70']}


def _clear_current_panel_files(out_dir, across_sites=False):
    """Remove only this generated panel family's files when reusing a destination."""
    from pathlib import Path
    import re
    root = Path(out_dir).resolve()
    if not root.is_dir():
        return
    names = ({'Current mean speed across sites.svg'} if across_sites else {
        'Current profile (time x depth).svg', 'Current vectors (time x depth).svg',
        'Current components (U-V).svg', 'Current components (U-V, lines broken).svg',
        'Current components (U-V, connected).svg', 'Current stick plot.svg',
        'Progressive vector diagram.svg', 'Current quality and coverage.svg',
        'Current temporal QC preview.svg'})
    folders = [root]
    for folder in root.iterdir():
        owned = (folder.name in {'surface', 'instrument', 'unknown', 'unspecified', 'nan'}
                 or folder.name.startswith('reference_')) if across_sites else bool(
                     re.fullmatch(r'\d{2,}_[\w.-]+', folder.name))
        if owned and folder.is_dir() and not folder.is_symlink():
            resolved = folder.resolve()
            if root in resolved.parents:
                folders.append(resolved)
    for folder in folders:
        for name in names:
            path = folder / name
            if path.is_file():
                path.unlink()


def plot_doppler_panels(frame, out_dir, label='', settings=None, show=False,
                        figures=None):
    """Current panels sharing one velocity solution, cell grid and QC context."""
    from QCS_CurrentPanels import plot_panels
    return plot_panels(frame, out_dir, label, settings, show, figures)


def plot_doppler_across_sites(database, out_dir, sites, settings=None, show=False,
                              figures=None):
    """Mean displayed speed by native cell, preserving source/column identity.

    Shares the per-site quality, time, depth and vector-averaging settings.
    The final mean is scalar across occupied display bins, not net transport.
    """
    import os
    from QCS_CurrentPanels import prepare
    s = settings or {}
    _clear_current_panel_files(out_dir, across_sites=True)
    os.makedirs(out_dir, exist_ok=True)
    colors = getSiteColors(sites)
    fig, ax = plt.subplots(figsize=(6.5, 8))
    n = 0
    references = set()
    for site in sites:
        product = prepare(database[database['Site'] == site], dict(s, currentTemporalPreview=False))
        if product is None or not product['eligible_rows']:
            continue
        cells = product['cells'].copy()
        values = product['arrays']['speed']
        counts = np.isfinite(values).sum(axis=1)
        cells['_mean'] = np.divide(np.nansum(values, axis=1), counts,
                                   out=np.full(len(cells), np.nan), where=counts > 0)
        keys = [key for key in ['Source file', 'Column', 'Depth reference'] if key in cells]
        for i, (identity, group) in enumerate(cells.groupby(keys, dropna=False, sort=False)):
            if not group['_mean'].notna().any():
                continue
            references.update(group['Depth reference'])
            parts = [site] + [str(value) for value in identity]
            group = group.sort_values('Depth (m)')
            ax.plot(group['_mean'], group['Depth (m)'], marker='o', ms=3, lw=1.2,
                    linestyle=['-', '--', ':', '-.'][i % 4],
                    color=colors.get(site), label=' | '.join(parts))
        n += 1
    if n < 2:
        plt.close(fig)
        return []
    ax.invert_yaxis()
    ax.set_xlabel('Mean displayed horizontal speed (cm/s)')
    ax.set_ylabel('Configured depth / distance (m); reference in legend' if len(references) > 1
                  else 'Configured depth / distance (m; %s reference)' % next(iter(references)))
    ax.set_title('Mean current speed by depth - across sites')
    fig._qcs_axes_names = {ax: 'Mean current speed by depth'}
    fig._qcs_customize_axes = [('Mean current speed by depth', ax)]
    _name_panel(fig, 'Mean current speed by depth - across sites')
    ax.grid(alpha=0.3)
    ax.legend(fontsize=8)
    resolution = '%d-min vector means' % s['currentBinMinutes'] if s.get('currentBinMinutes') else 'native samples'
    quality = 'GOOD only' if s.get('currentQuality') == 'good' else 'GOOD + SUSPECT'
    fig.text(.5, .015, 'Scalar mean of occupied display bins | %s | %s' % (resolution, quality),
             ha='center', fontsize='small')
    p = os.path.join(out_dir, 'Current mean speed across sites.svg')
    fig.savefig(p, bbox_inches='tight')
    enable_scroll_zoom(fig, fit=False)
    fig._qcs_v140_doppler = True
    _keep_or_close(fig, show, figures)
    if show and figures is None:
        show_panels(browse=True)
    return [p]

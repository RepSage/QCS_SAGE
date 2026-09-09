"""Current display products, independent of archived qualification flags.

Uses the QCS pandas/NumPy/Matplotlib runtime. Polar native measurements define
the displayed solution. Equal-height rows identify configured cells; they are
not estimates of sampled layer thickness. Temporal checks are diagnostic only.
"""
from pathlib import Path
import re
import xml.etree.ElementTree as ET

import numpy as np
import pandas as pd


VIEW_OPTIONS = {
    'currentBinMinutes': ('Time resolution', {'Native samples': 0,
        '15-minute vector mean': 15, '30-minute vector mean': 30}, 15),
    'currentQuality': ('Data quality', {'GOOD + SUSPECT': 'good_suspect',
        'GOOD only': 'good'}, 'good_suspect'),
    'currentContrast': ('Speed contrast', {'Linear': 'linear',
        'Low-speed contrast (sqrt)': 'sqrt'}, 'linear'),
    'currentShowQuality': ('Quality panel', {'Show': True, 'Hide': False}, True),
    'currentTemporalPreview': ('Temporal QC', {'Off': False,
        'Preview (experimental)': True}, False),
}
TEMPORAL_OPTIONS = {
    'currentSpikeLimit': ('Spike residual (cm/s)', 50.),
    'currentRateLimit': ('Change rate (cm/s/min)', 10.),
    'currentFlatTolerance': ('Flat-line tolerance (cm/s)', .1),
    'currentFlatMinutes': ('Flat-line duration (min)', 30.),
}


def direction_metadata(config):
    """A label for the recorded coordinates, never a rotation of measurements."""
    enabled = str(config.get('Enable Magnetic Declination', '')).lower()
    try:
        angle = float(config.get('Declination Angle', np.nan))
    except (TypeError, ValueError):
        angle = np.nan
    reference = ('magnetic' if enabled == 'false' else
                 'true' if enabled == 'true' and np.isfinite(angle) else 'unknown')
    return {'Direction reference': reference,
            'Magnetic declination (deg)': angle if enabled == 'true' else
            0. if enabled == 'false' else np.nan}


def enrich_direction_metadata(frame, source):
    """Resolve an old product from its exact adjacent provenance block, read-only.

    Arbitrary/relocated files and ambiguous sources remain unknown. A session
    name alone is not evidence: it must occur in this product's provenance and
    resolve uniquely within the corresponding raw site subtree.
    """
    if 'Direction reference' in frame:
        return frame
    result = frame.copy()
    result['Direction reference'] = 'unknown'
    result['Magnetic declination (deg)'] = np.nan
    path = Path(source)
    sidecar = path.parent / 'provenance.txt'
    qualified = next((p for p in path.parents if p.name == 'qualified'), None)
    if qualified is None or not sidecar.is_file():
        return result
    blocks = sidecar.read_text(encoding='utf-8').split('\n\n')
    matching = [b.splitlines() for b in blocks if b.splitlines()
                and b.splitlines()[0].strip() == path.stem]
    if len(matching) != 1:
        return result
    props = {}
    for line in matching[0][1:]:
        match = re.match(r'\s*(\w+)\s*:\s*(.*)', line)
        if match:
            props[match[1]] = match[2].strip()
    sessions = [s for s in re.split(r'\s*[|,]\s*', props.get('inputs', '')) if s]
    raw_site = qualified.parent / 'raw' / path.parent.relative_to(qualified)
    if not sessions or not raw_site.is_dir():
        return result
    metadata = []
    for session in sessions:
        if Path(session).name != session or session in {'.', '..'}:
            return result
        configs = list(raw_site.glob('**/' + session + '/Config.xml'))
        if len(configs) != 1:
            return result
        try:
            tree = ET.parse(configs[0])
            nodes = [el for el in tree.iter() if el.get('Descr', '').startswith('DCPS #')]
            if len(nodes) != 1:
                return result
            values = {el.get('Descr'): el.text for el in nodes[0].iter()
                      if el.tag.split('}')[-1] == 'Property'}
            metadata.append(direction_metadata(values))
        except (OSError, ET.ParseError):
            return result
    first = metadata[0]
    if first['Direction reference'] != 'unknown' and all(m == first for m in metadata):
        for column, value in first.items():
            result[column] = value
    return result


def quality_reasons(row):
    """Explain stored tests and the supported native words without requalifying."""
    reasons = set()
    names = ['Speed range', 'Native/signal quality', 'Speed stdev', 'Tilt', 'Manual review']
    flag = str(row.get('Flag', '')).split('.')[0]
    if len(flag) == 5:
        for value, name in zip(flag, names, strict=True):
            if value in '349':
                reasons.add(name + ': ' + {'3': 'SUSPECT', '4': 'BAD', '9': 'missing'}[value])
        if flag[4] == '5':
            reasons.add('Manually dismissed')
    if row.get('Native status map') != 'TD304-2024':
        if int(row.get('Flag_cur', 2)) != 1:
            reasons.add('Native quality unavailable or unmapped')
        return '; '.join(sorted(reasons)) or 'No stored warning'
    def word(name):
        value = row.get(name, 0)
        return int(value) if pd.notna(value) else 0
    state, state2, record = word('Cell state'), word('Cell state 2'), word('Record state')
    for mask, name in [(15, 'Beam correlation'), (3 << 4, 'Weak signal'),
                       (3 << 6, 'Native speed stdev'), (3 << 8, 'Beam disagreement'),
                       (3 << 10, 'Vertical current'), (1 << 12, 'Blanking zone'),
                       (1 << 13, 'Side-lobe zone'), (1 << 14, 'Out of range'),
                       (1 << 15, 'Data not ready')]:
        if state & mask:
            reasons.add(name)
    if state2:
        reasons.add('Beam-level status 0x%04x' % (state2 & 0xffff))
    for mask, name in [(1, 'Orientation mismatch'), (255 << 1, 'Ambient acoustic noise'),
                       (3 << 9, 'Heading variability'), (3 << 11, 'Tilt variability'),
                       (63 << 13, 'Instrument health'), (1 << 19, 'Sensor in air'),
                       (1 << 20, 'Depth-reference mismatch'), (1 << 21, 'Surface mismatch')]:
        if record & mask:
            reasons.add(name)
    return '; '.join(sorted(reasons)) or 'No stored warning'


def _sample_times(values):
    times = pd.DatetimeIndex(values.dropna().unique()).sort_values()
    delta = np.diff(times.asi8) / 1e9
    cadence = float(np.median(delta[delta > 0])) if np.any(delta > 0) else 300.
    # Native AADI float conversion occasionally adds +/-1 ms to exact seconds.
    # Align display bins only when the record cadence supports that precision.
    round_seconds = (cadence >= 1 and (not len(delta) or delta.min() > .8 * cadence)
                     and np.all(np.abs(times.asi8 / 1e9 - np.round(times.asi8 / 1e9)) < .002))
    return cadence, round_seconds


def temporal_metrics(frame, settings):
    """Depth/source-specific experimental diagnostics; no stored flag mutation.

    Residuals use the selected polar solution. References require GOOD adjacent
    native records, and no test crosses a missing/BAD interval. Thresholds are
    user-visible exploratory choices, not calibrated qualification defaults.
    """
    metrics = pd.DataFrame(index=frame.index, columns=['spike', 'rate', 'flat'], dtype=float)
    limits = {key: float(settings.get(key, default))
              for key, (_, default) in TEMPORAL_OPTIONS.items()}
    if any(not np.isfinite(v) or v <= 0 for v in limits.values()):
        raise ValueError('Temporal preview thresholds must be finite and positive.')
    tolerance = limits['currentFlatTolerance']
    for _, sub in frame.groupby('_cell', sort=False):
        sub = sub.sort_values('_time')
        cadence, _ = _sample_times(sub['_time'])
        time = sub['_time'].astype('int64').to_numpy() / 6e10
        u, v = sub['_u'].to_numpy(), sub['_v'].to_numpy()
        eligible = sub['_eligible'].to_numpy()
        good = sub['Flag_cur'].eq(1).to_numpy() & eligible
        delta = np.diff(time)
        adjacent = (delta > 0) & (delta <= 1.5 * cadence / 60.)
        spike, rate, flat = (np.full(len(sub), np.nan) for _ in range(3))
        if len(sub) > 1:
            valid = adjacent & good[:-1] & eligible[1:]
            change = np.maximum(np.abs(np.diff(u)), np.abs(np.diff(v)))
            rate[1:] = np.where(valid, np.divide(change, delta, out=np.full_like(delta, np.nan),
                                                where=delta > 0), np.nan)
        if len(sub) > 2:
            valid = adjacent[:-1] & adjacent[1:] & good[:-2] & good[2:] & eligible[1:-1]
            residual = np.maximum(np.abs(u[1:-1] - (u[:-2] + u[2:]) / 2),
                                  np.abs(v[1:-1] - (v[:-2] + v[2:]) / 2))
            spike[1:-1] = np.where(valid, residual, np.nan)
        start = 0
        for i in range(len(sub)):
            if not eligible[i]:
                start = i + 1
                continue
            if i == 0 or start == i or not adjacent[i-1]:
                start = i
            while start < i and (np.ptp(u[start:i+1]) > tolerance or
                                 np.ptp(v[start:i+1]) > tolerance):
                start += 1
            flat[i] = time[i] - time[start]
        metrics.loc[sub.index, :] = np.column_stack([spike, rate, flat])
    return metrics, limits


def prepare(frame, settings=None):
    """Prepare one immutable display product with explicit coverage and identity."""
    s = settings or {}
    work = frame.copy(deep=True)
    for name, default in [('Column', 'Column'), ('Cell', 0), ('Depth reference', 'unknown'),
                          ('Direction reference', 'unknown'), ('Surface cell', False)]:
        if name not in work:
            work[name] = default
    work['Datetime'] = pd.to_datetime(work['Datetime'])
    work['Depth (m)'] = pd.to_numeric(work['Depth (m)'], errors='coerce')
    work = work.dropna(subset=['Datetime', 'Depth (m)']).reset_index(drop=True)
    for key, col, lower in [('xAxisStart', 'Datetime', True), ('xAxisEnd', 'Datetime', False),
                             ('depthAxisMin', 'Depth (m)', True), ('depthAxisMax', 'Depth (m)', False)]:
        value = s.get(key)
        if value is not None:
            value = pd.Timestamp(value) if col == 'Datetime' else float(value)
            work = work[work[col].ge(value) if lower else work[col].le(value)]
    if work.empty:
        return None
    cadence, snap = _sample_times(work['Datetime'])
    work['_time'] = work['Datetime'].dt.round('s') if snap else work['Datetime']
    for name in ('Depth reference', 'Direction reference'):
        work[name] = work[name].fillna('unknown')
    keys = [c for c in ['Source file', 'Column', 'Cell', 'Depth (m)', 'Depth reference',
                        'Surface cell', 'Direction reference'] if c in work]
    cells = work[keys].drop_duplicates().sort_values(['Depth (m)', 'Column', 'Cell']).reset_index(drop=True)
    # Do not join/drop source rows. One key index per existing native identity.
    ids = {tuple(row): i for i, row in enumerate(cells.itertuples(index=False, name=None))}
    work['_cell'] = [ids[tuple(row)] for row in work[keys].itertuples(index=False, name=None)]
    speed = pd.to_numeric(work['Horizontal speed (cm/s)'], errors='coerce')
    angle = pd.to_numeric(work['Direction (deg)'], errors='coerce')
    complete = np.isfinite(speed) & np.isfinite(angle) & speed.ge(0) & angle.between(0, 360)
    work['_eligible'] = complete & work['Flag_cur'].isin([1] if s.get('currentQuality') == 'good' else [1, 3])
    work['_u'] = speed * np.sin(np.deg2rad(angle))
    work['_v'] = speed * np.cos(np.deg2rad(angle))
    work['_reasons'] = [quality_reasons(row) for row in work.to_dict('records')]
    minutes = int(s.get('currentBinMinutes', 0))
    if minutes not in (0, 15, 30):
        raise ValueError('Current time resolution must be native, 15 or 30 minutes.')
    width = pd.Timedelta(minutes=minutes) if minutes else pd.Timedelta(seconds=cadence)
    cell_cadence = {cell: _sample_times(sub['_time'])[0]
                    for cell, sub in work.groupby('_cell', sort=False)}
    work['_bin'] = work['_time'].dt.floor('%dmin' % minutes) if minutes else work['_time'] - width / 2
    # Include a blank interval between distant samples, without allocating an
    # entire five-minute grid across the years separating distinct deployments.
    starts = pd.DatetimeIndex(work['_bin'].unique()).sort_values()
    edges = pd.DatetimeIndex(np.unique(np.concatenate([starts.asi8, (starts + width).asi8])))
    edge_index = {stamp: i for i, stamp in enumerate(edges[:-1])}
    shape = (len(cells), len(edges) - 1)
    arrays = {key: np.full(shape, np.nan) for key in ['u', 'v', 'speed', 'direction', 'qc', 'coverage']}
    details = {}
    metrics, limits = temporal_metrics(work, s) if s.get('currentTemporalPreview') else (None, None)
    temporal = {key: np.full(shape, np.nan) for key in ['spike', 'rate', 'flat']}
    for (cell, stamp), sub in work.groupby(['_cell', '_bin'], sort=False):
        j = edge_index[stamp]
        eligible = sub[sub['_eligible']]
        observed = len(sub)
        expected = max(observed, int(round(width.total_seconds() / cell_cadence[cell]))) if minutes else observed
        good = int(sub.Flag_cur.eq(1).sum())
        suspect = int(sub.Flag_cur.eq(3).sum())
        bad = int(sub.Flag_cur.eq(4).sum())
        manual = int(sub.Flag_cur.eq(5).sum())
        qc_flag = 4 if bad else 5 if manual else 3 if suspect else 1 if good == observed else 2
        arrays['qc'][cell, j] = qc_flag
        arrays['coverage'][cell, j] = len(eligible) / expected
        if len(eligible):
            u, v = eligible['_u'].mean(), eligible['_v'].mean()
            arrays['u'][cell, j], arrays['v'][cell, j] = u, v
            arrays['speed'][cell, j] = np.hypot(u, v)
            if np.hypot(u, v) > 1e-8:
                arrays['direction'][cell, j] = np.degrees(np.arctan2(u, v)) % 360
        reasons = sorted(set(sub['_reasons']) - {'No stored warning'})
        detail = {'valid': len(eligible), 'expected': expected, 'observed': observed,
                  'good': good, 'suspect': suspect, 'bad': bad, 'manual': manual,
                  'reasons': ' | '.join(reasons) or 'No stored warning'}
        if metrics is not None:
            for key in temporal:
                values = metrics.loc[sub.index, key]
                temporal[key][cell, j] = values.max() if values.notna().any() else np.nan
        details[cell, j] = detail
    labels = []
    multiple = cells['Column'].nunique() > 2 or cells.loc[~cells['Surface cell'].eq(True), 'Column'].nunique() > 1
    duplicate_depths = cells['Depth (m)'].duplicated(keep=False)
    refs = set(cells['Depth reference'].dropna())
    for i, row in cells.iterrows():
        surface = row['Surface cell'] in (True, 'True', 'true') or str(row.Column).lower() == 'surface'
        label = 'Surface' if surface else '%g m' % row['Depth (m)']
        if multiple or duplicate_depths.iloc[i]:
            label += ' | %s' % row.Column
        if 'Source file' in cells and cells['Source file'].nunique() > 1:
            source_label = re.search(r'20\d\dS\d', str(row['Source file']))
            label += ' | %s' % (source_label[0] if source_label else str(row['Source file'])[:16])
        if len(refs) > 1:
            label += ' (%s ref.)' % row['Depth reference']
        labels.append(label)
    ref_values = set(cells['Direction reference'].fillna('unknown'))
    reference = next(iter(ref_values)) if len(ref_values) == 1 else 'mixed/unknown'
    return dict(frame=work, cells=cells, labels=labels, edges=edges, arrays=arrays,
                details=details, temporal=temporal, limits=limits, minutes=minutes,
                cadence_seconds=cadence, reference=reference,
                selected_rows=len(work), eligible_rows=int(work['_eligible'].sum()),
                original_rows=len(frame), time_snapped_to_seconds=snap)


def hover_text(product, cell, time_bin):
    info = product['details'].get((cell, time_bin))
    start, end = product['edges'][time_bin:time_bin+2]
    prefix = '%s | %s to %s' % (product['labels'][cell], start.strftime('%d/%m/%y %H:%M'),
                                end.strftime('%H:%M'))
    if info is None:
        return prefix + ' | No observations in this interval'
    value = product['arrays']['speed'][cell, time_bin]
    direction = product['arrays']['direction'][cell, time_bin]
    return (prefix + ' | %.3g cm/s; toward %.1f deg (%s north)' %
            (value, direction, product['reference']) +
            ' | Used %d/%d expected (%d observed): GOOD %d, SUSPECT %d, BAD %d, dismissed %d | %s' %
            (info['valid'], info['expected'], info['observed'], info['good'], info['suspect'],
             info['bad'], info['manual'], info['reasons']))


def plot_panels(frame, out_dir, label='', settings=None, show=False, figures=None):
    """Render all current panels from one consistent, immutable display product."""
    import matplotlib.dates as mdates
    import matplotlib.colors as mcolors
    import matplotlib.pyplot as plt
    import QCS_DataView as view
    s = settings or {}
    view._clear_current_panel_files(out_dir)
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    p = prepare(frame, s)
    if p is None:
        return []
    colors = view.getCurrentColors()
    arrays = p['arrays']
    x = mdates.date2num(p['edges'].to_pydatetime())
    centers = (x[:-1] + x[1:]) / 2
    y = np.arange(len(p['cells']) + 1) - .5
    data_ylim = (len(p['cells']) - .5, -.5)
    reference = p['reference']
    resolution = '%d-min vector mean' % p['minutes'] if p['minutes'] else 'Native samples'
    quality = 'GOOD only' if s.get('currentQuality') == 'good' else 'GOOD + SUSPECT'
    caption = '%s | %s | north reference: %s | U/V derived from native speed + direction' % (
        resolution, quality, reference)
    files = []

    def axes_format(ax, max_labels=17):
        ax.set_xlim(x[0], x[-1])
        ax.set_ylim(*data_ylim)
        indices = np.unique(np.rint(np.linspace(0, len(p['cells'])-1, min(max_labels, len(p['cells'])))).astype(int))
        ax.set_yticks(indices, [p['labels'][i] for i in indices])
        ax.set_ylabel('Configured cell')
        ax.set_facecolor(colors['missing'])
        ax.format_coord = lambda tx, ty: hover_text(p, int(np.clip(round(ty), 0, len(p['cells'])-1)),
            int(np.clip(np.searchsorted(x, tx, side='right')-1, 0, len(centers)-1)))

    def dates(ax):
        locator = mdates.AutoDateLocator(minticks=3, maxticks=7)
        ax.xaxis.set_major_locator(locator)
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%d/%m/%y\n%H:%M'))
        ax.set_xlabel('Local time (GMT-3)')

    def finish(fig, panel, filename):
        fig._qcs_current_product = p
        fig._qcs_v140_doppler = True  # retained circular line legend handles
        fig.text(.5, .015, getattr(fig, '_qcs_caption', caption), ha='center', fontsize='small')
        view._name_panel(fig, panel, label)
        view.enable_scroll_zoom(fig, fit=False)
        path = str(Path(out_dir) / filename)
        fig.savefig(path, bbox_inches='tight')
        files.append(path)
        view._keep_or_close(fig, show, figures)

    def mesh(ax, values, **kwargs):
        artist = ax.pcolormesh(x, y, np.ma.masked_invalid(values), shading='flat', **kwargs)
        artist._qcs_current_hover = lambda row, col: hover_text(p, row, col)
        axes_format(ax)
        return artist

    fig, axes = plt.subplots(2, 1, figsize=(12, 8), sharex=True, sharey=True)
    fig.subplots_adjust(left=.13, right=.86, bottom=.16, top=.9, hspace=.15)
    vmax = s.get('currentSpeedMax')
    if not vmax or not np.isfinite(vmax):
        finite = arrays['speed'][np.isfinite(arrays['speed'])]
        vmax = max(1., float(finite.max())) if len(finite) else 1.
    contrast = s.get('currentContrast', 'linear')
    norm = mcolors.PowerNorm(.5, vmin=0, vmax=vmax) if contrast == 'sqrt' else mcolors.Normalize(0, vmax)
    speed_mesh = mesh(axes[0], arrays['speed'], cmap=colors['speed_map'], norm=norm)
    speed_mesh.set_label('Horizontal speed heatmap')
    bar = fig.colorbar(speed_mesh, ax=axes[0], label='Speed [cm/s]' + ('\nsqrt scale' if contrast == 'sqrt' else ''),
                       extend='max' if np.any(arrays['speed'] > vmax) else 'neither', pad=.025)
    bar.set_ticks(np.linspace(0, vmax, 6))
    bar.ax.set_navigate(False)
    direction_mesh = mesh(axes[1], arrays['direction'], cmap=colors['direction_map'], vmin=0, vmax=360)
    direction_mesh.set_label('Direction heatmap')
    unused = fig.colorbar(direction_mesh, ax=axes[1], pad=.025)
    unused.ax.set_visible(False)
    wheel = view._direction_compass(fig, unused.ax, axes[1], colors['direction_map'],
                                    label_font=bar.ax.yaxis.label.get_fontsize(), tick_font=view._bar_tick_size(bar))
    wheel.set_title('Direction (toward)\nNorth: %s' % reference, fontsize='small', pad=20)
    dates(axes[1])
    fig.suptitle('Current profile - %s' % label)
    axes[0].set_title('Horizontal speed' + (' of the mean vector' if p['minutes'] else ''), fontsize='medium')
    fig._qcs_customize_axes = [('Horizontal speed heatmap', axes[0]), ('Direction heatmap', axes[1])]
    fig._qcs_axes_names = dict((ax, name) for name, ax in fig._qcs_customize_axes)
    fig._qcs_layout_keys = [{'name': 'Horizontal speed color scale', 'axes': bar.ax, 'anchor': axes[0], 'vertical': 'match'},
                            {'name': 'Direction compass', 'axes': wheel, 'anchor': axes[1], 'vertical': 'center'}]
    fig._qcs_legend_labels = {
        axes[0]: [{'name': 'Horizontal speed color scale', 'artist': bar.ax.yaxis.label}],
        axes[1]: [{'name': 'Direction compass', 'artist': wheel.title}],
    }
    finish(fig, 'Current profile', 'Current profile (time x depth).svg')

    usable_cells = np.flatnonzero(np.isfinite(arrays['speed']).any(axis=1))
    selected = usable_cells[np.unique(np.rint(np.linspace(0, len(usable_cells)-1, min(4, len(usable_cells)))).astype(int))] if len(usable_cells) else []
    gap_mode = s.get('uvGapMode', 'break')
    modes = ['break', 'connect'] if gap_mode == 'both' else [gap_mode]
    for mode in modes:
        treatment = 'lines broken at data gaps' if mode != 'connect' else 'connected across data gaps'
        fig, axes = plt.subplots(2, 1, figsize=(12, 7), sharex=True)
        fig.subplots_adjust(left=.1, right=.94, bottom=.17, top=.87, hspace=.17)
        for i, cell in enumerate(selected):
            for ax, key in zip(axes, ['u', 'v'], strict=True):
                values = arrays[key][cell]
                keep = np.isfinite(values) if mode == 'connect' else np.ones(len(values), dtype=bool)
                marker = 'o' if np.isfinite(values).sum() == 1 else None
                ax.plot(centers[keep], values[keep], lw=.9, marker=marker, ms=3,
                        color=colors['lines'][i], label=p['labels'][cell])
        for ax in axes:
            ax.axhline(0, color=colors['zero'], lw=.6, zorder=0)
            ax.set_xlim(x[0], x[-1])
            ax.grid(alpha=.15)
        axes[0].set_ylabel('East U [cm/s]')
        axes[1].set_ylabel('North V [cm/s]')
        if len(selected):
            axes[0].legend(ncol=min(4, len(selected)), fontsize='small', loc='upper center', bbox_to_anchor=(.5, 1.16))
        dates(axes[1])
        fig.suptitle('Current components (%s) - %s' % (treatment, label))
        fig._qcs_customize_axes = [('East component (U)', axes[0]), ('North component (V)', axes[1])]
        fig._qcs_axes_names = {ax: name for name, ax in fig._qcs_customize_axes}
        filename = 'Current components (U-V, %s).svg' % ('connected' if mode == 'connect' else 'lines broken')
        finish(fig, 'U/V components - %s' % treatment, filename)

    fig, ax = plt.subplots(figsize=(12, 5.5))
    fig.subplots_adjust(left=.13, right=.94, bottom=.22, top=.85)
    anchors, tnum, u, v, hover = [], [], [], [], []
    # Shared time positions, including missing intervals, never a different
    # stride through each row's filtered samples.
    shared = np.rint(np.linspace(0, len(centers)-1, min(28, len(centers)))).astype(int)
    # Include a representative observation for even a sparsely available cell;
    # the resulting positions are then used by every row (at most 32 times).
    first_valid = [np.flatnonzero(np.isfinite(arrays['speed'][cell]))[0] for cell in selected]
    time_indices = np.unique(np.concatenate([shared, first_valid]).astype(int))
    for cell in selected:
        for j in time_indices:
            if np.isfinite(arrays['speed'][cell, j]):
                anchors.append(cell)
                tnum.append(centers[j])
                u.append(arrays['u'][cell, j])
                v.append(arrays['v'][cell, j])
                hover.append((cell, j))
    if u:
        vector_max = max(1., float(np.max(np.hypot(u, v))))
        quiver = ax.quiver(tnum, anchors, u, v, angles='uv', scale_units='width',
                           scale=vector_max*max(20., len(time_indices)*1.1),
                           width=.002, color=colors['vector'], pivot='middle')
        quiver._qcs_current_vector_hover = lambda index: hover_text(p, *hover[index])
        ref_speed = max(1., float(round(vector_max/2, 1)))
        ax.quiverkey(quiver, .89, 1.06, ref_speed, '%g cm/s' % ref_speed, coordinates='axes')
    axes_format(ax)
    # Space around boundary anchors prevents surface arrows being cut in half.
    margin = max(1., len(p['cells']) * .08)
    ax.set_ylim(len(p['cells']) - 1 + margin, -margin)
    time_margin = (x[-1] - x[0]) * .03
    ax.set_xlim(x[0] - time_margin, x[-1] + time_margin)
    ax.set_yticks(selected, [p['labels'][i] for i in selected])
    dates(ax)
    ax.set_title('Current vectors - %s\nArrows: N up, E right (%s); rows identify cells' % (label, reference))
    fig._qcs_customize_axes = [('Current vectors', ax)]
    fig._qcs_axes_names = {ax: 'Current vectors'}
    finish(fig, 'Current vectors', 'Current vectors (time x depth).svg')

    if s.get('currentShowQuality', True):
        fig, axes = plt.subplots(2, 1, figsize=(12, 8), sharex=True, sharey=True)
        fig.subplots_adjust(left=.13, right=.86, bottom=.16, top=.87, hspace=.19)
        qc_map = mcolors.ListedColormap([colors['good'], colors['unknown'],
                                        colors['suspect'], colors['bad'], colors['dismissed']])
        qc_mesh = mesh(axes[0], arrays['qc'], cmap=qc_map,
                       norm=mcolors.BoundaryNorm(np.arange(.5, 6), qc_map.N))
        qbar = fig.colorbar(qc_mesh, ax=axes[0], ticks=[1, 2, 3, 4, 5], pad=.025)
        qbar.ax.set_yticklabels(['GOOD', 'Unknown', 'SUSPECT', 'BAD', 'Dismissed'])
        qbar.ax.set_navigate(False)
        axes[0].set_title('Stored QC: most restrictive flag among observed samples', fontsize='medium')
        coverage_mesh = mesh(axes[1], arrays['coverage'] * 100, cmap=colors['coverage_map'], vmin=0, vmax=100)
        cbar = fig.colorbar(coverage_mesh, ax=axes[1], label='Used / expected [%]', pad=.025)
        cbar.ax.set_navigate(False)
        axes[1].set_title('Coverage under the selected quality filter; gaps stay empty', fontsize='medium')
        dates(axes[1])
        fig.suptitle('Current quality and coverage - %s\n%d of %d selected cell-time rows used' %
                     (label, p['eligible_rows'], p['selected_rows']))
        fig._qcs_customize_axes = [('Stored current quality', axes[0]), ('Current coverage', axes[1])]
        fig._qcs_axes_names = {ax: name for name, ax in fig._qcs_customize_axes}
        fig._qcs_layout_keys = [
            {'name': 'Stored QC key', 'axes': qbar.ax, 'anchor': axes[0], 'vertical': 'match'},
            {'name': 'Coverage key', 'axes': cbar.ax, 'anchor': axes[1], 'vertical': 'match'}]
        finish(fig, 'Current quality and coverage', 'Current quality and coverage.svg')

    if p['limits'] is not None:
        fig, axes = plt.subplots(3, 1, figsize=(12, 9), sharex=True, sharey=True)
        fig.subplots_adjust(left=.13, right=.86, bottom=.15, top=.87, hspace=.28)
        metrics = [('spike', 'U/V spike residual', 'cm/s', 'currentSpikeLimit'),
                   ('rate', 'U/V change rate', 'cm/s/min', 'currentRateLimit'),
                   ('flat', 'U/V stable duration', 'min', 'currentFlatMinutes')]
        fig._qcs_customize_axes = [(title, ax) for ax, (_, title, _, _) in zip(axes, metrics, strict=True)]
        fig._qcs_axes_names = {ax: name for name, ax in fig._qcs_customize_axes}
        fig._qcs_layout_keys = []
        fig._qcs_caption = ('Native-sample diagnostics; maximum within each %d-min display bin' % p['minutes']
                            if p['minutes'] else 'Native-sample diagnostics; no temporal averaging')
        for ax, (key, title, unit, limit_key) in zip(axes, metrics, strict=True):
            limit = p['limits'][limit_key]
            values = p['temporal'][key]
            m = mesh(ax, values, cmap=colors['diagnostic_map'], vmin=0, vmax=limit)
            axes_format(ax, max_labels=9)
            m._qcs_current_hover = lambda row, col, values=values, title=title, unit=unit, limit=limit: (
                '%s: %g %s | Experimental threshold: %g %s | ' %
                (title, values[row, col], unit, limit, unit) + hover_text(p, row, col))
            bar = fig.colorbar(m, ax=ax, label=unit, extend='max', pad=.025)
            bar.ax.set_navigate(False)
            fig._qcs_layout_keys.append({'name': title + ' scale', 'axes': bar.ax, 'anchor': ax, 'vertical': 'match'})
            flagged = np.isfinite(values) & (values >= limit)
            row, col = np.where(flagged)
            ax.scatter(centers[col], row, marker='x', s=13, color=colors['candidate'])
            ax.set_title('%s: candidate threshold %g %s (%d display bins)' %
                         (title, limit, unit, int(flagged.sum())), fontsize='medium')
        dates(axes[-1])
        fig.suptitle('Experimental temporal QC - %s\nUncalibrated preview; stored flags unchanged; flat tolerance %g cm/s' %
                     (label, p['limits']['currentFlatTolerance']))
        finish(fig, 'Experimental temporal QC', 'Current temporal QC preview.svg')
    print('Info: Current display %s: %d input -> %d selected -> %d eligible cell-time rows; %s, %d cells.' %
          (label, p['original_rows'], p['selected_rows'], p['eligible_rows'], resolution, len(p['cells'])))
    if show and figures is None:
        view.show_panels(browse=True)
    return files

"""Auditable HOBO decisions and sustained-disagreement screening.

Dependencies: pandas and numpy (the application's pinned runtime).
The 24-hour screen is a conservative review policy, not a sensor-failure test.
"""
from pathlib import Path
from datetime import datetime
import hashlib
import os
import shutil

import numpy as np
import pandas as pd

DECISION_FILE = Path(__file__).with_name('batch') / 'replicate_decisions.csv'
DECISION_COLUMNS = ['decision_id', 'source_file', 'variable', 'start', 'end',
                    'action', 'reason', 'reviewer', 'reviewed_at']
TEMP = 'Temperature (degC)'
LIGHT = 'Luminosity (lux)'
SUSTAINED_HOURS = 24


def load_decisions(path=DECISION_FILE):
    """Read the versioned ledger; incomplete or contradictory decisions fail closed."""
    frame = pd.read_csv(path, dtype=str, keep_default_na=False)
    if list(frame.columns) != DECISION_COLUMNS:
        raise ValueError('Invalid replicate decision columns: %s' % path)
    if frame['decision_id'].duplicated().any():
        raise ValueError('Duplicate replicate decision ID')
    for row in frame.to_dict('records'):
        required = ['decision_id', 'source_file', 'variable', 'action', 'reason',
                    'reviewer', 'reviewed_at']
        if any(not row[k].strip() for k in required):
            raise ValueError('Incomplete replicate decision: %s' % row)
        if row['variable'] not in (TEMP, LIGHT, '*') or row['action'] != 'exclude':
            raise ValueError('Unsupported replicate decision: %s' % row['decision_id'])
        pd.Timestamp(row['reviewed_at'])
        if row['start'] and row['end'] and pd.Timestamp(row['start']) > pd.Timestamp(row['end']):
            raise ValueError('Reversed replicate decision interval')
    return frame


def legacy_exclusions():
    """Whole-file, all-variable exclusions used by archive discovery."""
    decisions = load_decisions()
    rows = decisions[(decisions.variable == '*') & (decisions.start == '') &
                     (decisions.end == '')]
    return dict(zip(rows.source_file, rows.reason, strict=True))


def apply_decisions(aligned, names, decisions):
    """Mask only the decided variable/interval, never restore individually bad data."""
    frames = [r.copy() for r in aligned]
    applied = []
    for row in decisions.to_dict('records'):
        for name, frame in zip(names, frames, strict=True):
            if Path(name).name != row['source_file']:
                continue
            mask = pd.Series(True, index=frame.index)
            if row['start']:
                mask &= frame.index >= pd.Timestamp(row['start'])
            if row['end']:
                mask &= frame.index <= pd.Timestamp(row['end'])
            if not mask.any():
                continue
            variables = [TEMP, LIGHT] if row['variable'] == '*' else [row['variable']]
            count = 0
            for variable in variables:
                count += int(frame.loc[mask, variable].notna().sum())
                frame.loc[mask, variable] = np.nan
            applied.append(dict(row, aligned_rows=int(mask.sum()), values_excluded=count))
    return frames, pd.DataFrame(applied, columns=DECISION_COLUMNS + ['aligned_rows', 'values_excluded'])


def disagreement_episodes(values, temp_tol=0.5, hours=SUSTAINED_HOURS):
    """Contiguous paired disagreements, broken by agreement, missingness or gaps.

    At least three paired samples and 24 elapsed hours are required. No gap is
    bridged; a gap >1.5 times the median sampling interval starts a new episode.
    """
    spread = (values.max(axis=1) - values.min(axis=1)).where(values.notna().sum(axis=1) >= 2)
    over = spread > temp_tol
    step = values.index.to_series().diff().median()
    gap = values.index.to_series().diff() > 1.5 * step
    groups = ((over != over.shift(fill_value=False)) | gap).cumsum()
    held = pd.Series(False, index=values.index)
    rows = []
    for _, segment in spread[over].groupby(groups[over]):
        duration = (segment.index[-1] - segment.index[0]).total_seconds() / 3600
        sustained = len(segment) >= 3 and duration >= hours
        if sustained:
            held.loc[segment.index] = True
        rows.append({'start': segment.index[0], 'end': segment.index[-1],
                     'paired_samples': len(segment), 'duration_hours': duration,
                     'max_spread_degC': segment.max(), 'sustained': sustained})
    columns = ['start', 'end', 'paired_samples', 'duration_hours', 'max_spread_degC', 'sustained']
    return held, pd.DataFrame(rows, columns=columns), spread


def dismiss_single(frame, flags, flag_layout, bucket_map, name, decisions):
    """Apply the same ledger to a single input, with explicit per-test dismissal."""
    original = frame.copy()
    original.index = pd.DatetimeIndex(pd.to_datetime(original['Datetime']))
    masked, applied = apply_decisions([original], [name], decisions)
    result = frame.copy()
    final_flags = list(flags)
    for variable, bucket in [(TEMP, 'T'), (LIGHT, 'lux')]:
        cut = original[variable].notna() & masked[0][variable].isna()
        result[variable] = masked[0][variable].to_numpy()
        positions = [p for p, key in enumerate(flag_layout) if bucket in bucket_map.get(key, [])]
        for row in np.flatnonzero(cut.to_numpy()):
            chars = list(final_flags[row])
            for position in positions:
                chars[position] = '5'
            final_flags[row] = ''.join(chars)
    samples = frame[['Datetime', TEMP, LIGHT]].copy()
    samples['individual_flags_before_decision'] = flags
    return result, final_flags, applied, samples


def combined_report(frame):
    """Counts from the actual exported product; withheld is distinct from missing flag 9."""
    report = {'scope': 'combined', 'start': frame['Datetime'].min(),
              'end': frame['Datetime'].max(), 'Total': len(frame)}
    for short, variable, flag in [('T', TEMP, 'Flag_T'), ('lux', LIGHT, 'Flag_lux')]:
        values = pd.to_numeric(frame[variable], errors='coerce')
        flags = pd.to_numeric(frame[flag], errors='coerce')
        for label, code in [('good', 1), ('not_evaluated', 2), ('suspect', 3),
                            ('bad', 4), ('dismissed', 5), ('missing', 9)]:
            report[short + '_' + label] = int(flags.eq(code).sum())
        report[short + '_blank'] = int(values.isna().sum())
        report[short + '_withheld'] = int((values.isna() & flags.eq(3)).sum())
    report['Valid'] = int((frame['Flag_T'].le(2) & frame[TEMP].notna()).sum())
    report['Valid_definition'] = 'finite temperature with Flag_T <= 2'
    return pd.DataFrame([report])


def report_destination(source, run_root, final_csv, product):
    """Preserve the main report name and give each individual folder its own namespace."""
    source = Path(source)
    if source.parent == Path(final_csv).parent:
        if source.name.startswith('QCS_light_window_'):
            identity = hashlib.sha256(source.name.encode('utf-8')).hexdigest()[:12]
            return product + '__QCS_light_window_' + identity + source.suffix
        return product + '__' + source.name
    relative = source.relative_to(run_root)
    # Folder labels can repeat and full export names can exceed Windows' 255
    # character filename limit after concatenation. Keep a readable prefix and
    # a stable digest of the full relative folder; the report contains the full
    # source filename. No source-folder identity is discarded by truncation.
    identity = hashlib.sha256(str(relative.parent).encode('utf-8')).hexdigest()[:12]
    label = 'replica-' + identity
    return product + '__' + label + '__' + source.name


def archive_legacy_reports(folder, product):
    """Retain obsolete unscoped individual reports outside the current report set."""
    root = Path(folder).resolve()
    names = ['QCS_test_report.xlsx', 'QCS_tscp_stat.xlsx', 'QCS_flag_legend.xlsx',
             'QCS_light_window.svg']
    stale = [root / (product + '__' + name) for name in names]
    stale = [path for path in stale if path.is_file()]
    if not stale:
        return
    destination = root / 'previous' / datetime.now().strftime('%Y%m%dT%H%M%S%f')
    destination.mkdir(parents=True)
    for source in stale:
        if source.resolve().parent != root or root not in destination.resolve().parents:
            raise ValueError('Report archive path escaped the reports folder')
        source.replace(destination / source.name)


def copy_report_file(source, destination):
    """Copy long report paths through Windows' explicit extended-path API."""
    def extended(path):
        path = os.path.abspath(path)
        if os.name != 'nt' or path.startswith('\\\\?\\'):
            return path
        if path.startswith('\\\\'):
            return '\\\\?\\UNC\\' + path[2:]
        return '\\\\?\\' + path
    return shutil.copy2(extended(source), extended(destination))


def align_replicates(replicates):
    """Shared, duplicate-safe alignment for diagnostics and exported values."""
    # A repeated timestamp with identical signals is a harmless duplicated row.
    # Conflicting values at the same instant are not: the old collapsed 12-hour
    # clock produced exactly that shape, and choosing the first reading silently
    # throws away half a record. Condense only identical signal rows and fail
    # closed on an ambiguous timestamp.
    messages = []
    clean_replicates = []
    signal_cols = ['Temperature (degC)', 'Luminosity (lux)', 'Flag_T', 'Flag_lux']
    for i, replicate in enumerate(replicates):
        clean = replicate.copy()
        clean['Datetime'] = pd.to_datetime(clean['Datetime'])
        clean = clean.sort_values('Datetime', kind='stable')
        duplicate = clean['Datetime'].duplicated(keep=False)
        if duplicate.any():
            repeated = clean.loc[duplicate, ['Datetime'] + signal_cols]
            conflicts = [stamp for stamp, group in repeated.groupby('Datetime', sort=False)
                         if any(group[col].nunique(dropna=False) > 1
                                for col in signal_cols)]
            n_extra = int(clean['Datetime'].duplicated().sum())
            if conflicts:
                raise ValueError(
                    'HOBO replicate %d has %d repeated timestamp(s) with '
                    'conflicting values (first: %s). This can indicate a '
                    'collapsed 12-hour clock; the replicates were not combined.'
                    % (i + 1, len(conflicts), conflicts[0]))
            clean = clean.drop_duplicates(subset=['Datetime'], keep='first')
            messages.append(
                'Warning: HOBO replicate %d contained %d identical duplicate '
                'row(s); one copy per timestamp was kept before combination.'
                % (i + 1, n_extra))
        clean_replicates.append(clean)

    # align every replicate onto the first replicate's time grid (nearest match
    # within half the sampling interval, to absorb small clock differences)
    ref_times = pd.DatetimeIndex(clean_replicates[0]['Datetime'])
    step = ref_times.to_series().diff().median()
    tol = (step / 2) if (pd.notna(step) and step > pd.Timedelta(0)) else pd.Timedelta(0)
    aligned = []
    for r in clean_replicates:
        a = r.copy()
        a = a.set_index('Datetime')
        a = a.sort_index()
        aligned.append(a.reindex(ref_times, method='nearest', tolerance=tol))

    return aligned, clean_replicates, messages

import re
import numpy as np
import pandas as pd
from scipy import stats

#############################
class QC_flags:
    GOOD_DATA = 1
    UNKNOWN = 2
    SUSPECT = 3
    BAD_DATA = 4
    DISMISSED = 5
    MISSING = 9
#############################


def get_eps(series):
    clean_series = series.dropna().astype(str)

    max_decimals = 0
    for num_str in clean_series:
        if '.' in num_str:
            decimals = num_str.split('.')[1].rstrip('0')
            max_decimals = max(max_decimals, len(decimals))

    return 10 ** -max_decimals if max_decimals > 0 else 1.0


def parse_time_window_samples(time_window, sample_interval_s, n_total):
    """Converts the time window ('2D'/'3H'/'30M'/'45S'/'WHOLE') into a number of
    samples. Returns n_total for 'WHOLE' or an unrecognized format."""
    if re.search("whole", time_window, re.IGNORECASE):
        return n_total
    if re.search(r"\d+d", time_window, re.IGNORECASE):
        seconds = 24 * 3600 * int(re.search(r"\d+", time_window).group())
    elif re.search(r"\d+h", time_window, re.IGNORECASE):
        seconds = 3600 * int(re.search(r"\d+", time_window).group())
    elif re.search(r"\d+m", time_window, re.IGNORECASE):
        seconds = 60 * int(re.search(r"\d+", time_window).group())
    elif re.search(r"\d+s", time_window, re.IGNORECASE):
        seconds = int(re.search(r"\d+", time_window).group())
    else:
        return n_total
    return int(seconds / sample_interval_s)


# minimum number of samples to estimate a stable local sigma: with fewer than
# this the MAD degenerates (e.g. 3 points -> sigma ~0 and noise becomes mass rejection)
MIN_SIGMA_SAMPLES = 11


def robust_rolling_sigma(pop, win):
    """Rolling robust sigma (1.4826 x MAD), used as the threshold reference in the
    spike and rate-of-change tests: it is not inflated by the very outliers that
    the tests are looking for. Where the MAD is 0 (nearly constant data) it falls
    back to the rolling standard deviation so as not to reject resolution noise.
    A window smaller than MIN_SIGMA_SAMPLES or larger than the series -> constant
    global value."""
    n = len(pop)
    if win >= n or win < MIN_SIGMA_SAMPLES:
        med = pop.median()
        mad = (pop - med).abs().median()
        sigma = 1.4826 * mad
        if not np.isfinite(sigma) or sigma <= 0:
            sigma = pop.std(ddof=0)
        return pd.Series(sigma, index=pop.index)
    med = pop.rolling(win, center=True, min_periods=3).median()
    mad = (pop - med).abs().rolling(win, center=True, min_periods=3).median()
    sigma = 1.4826 * mad
    std = pop.rolling(win, center=True, min_periods=3).std()
    sigma = sigma.where(sigma > 0, std)
    return sigma.bfill().ffill()


def outlier_test(dataframe, parameter, n_cel, flags, time_window, sample_interval, threshold_fail, threshold_susp):
    # QARTOD 3-point spike test: spike = |V2 - (V1 + V3)/2|, compared to a
    # relative threshold (factor x robust local sigma of the values, 1.4826xMAD,
    # so the spikes themselves do not inflate the reference). Single pass.
    # Endpoints and neighbours of gaps have no valid pair of neighbours and are
    # flagged UNKNOWN (not evaluated), never GOOD.
    pop = dataframe[parameter].copy()
    n = len(pop)
    spike = (pop - (pop.shift(1) + pop.shift(-1)) / 2).abs()

    win = parse_time_window_samples(time_window, sample_interval / np.timedelta64(1, 's'), n)
    if 0 < win < MIN_SIGMA_SAMPLES and win < n:
        print("Warning: spike-test window '%s' spans only %d sample(s) at this "
              "sampling interval; using the whole-series sigma instead." % (time_window, win))
    std = robust_rolling_sigma(pop, win)

    upperLimit = (threshold_fail * std).abs().to_numpy()
    lowerLimit = (threshold_susp * std).abs().to_numpy()
    spike_vals = spike.to_numpy()

    missing = np.where(dataframe[parameter].isna())[0]
    # spike/threshold NaN => no valid neighbours or indeterminate sigma: not evaluable
    unevaluated = np.where(np.isnan(spike_vals) | np.isnan(upperLimit))[0]
    unevaluated = [i for i in unevaluated if i not in missing]
    reproved = list(np.where(spike_vals > upperLimit)[0])
    suspect = list(np.where((spike_vals > lowerLimit) & (spike_vals <= upperLimit))[0])
    reproved = [i for i in reproved if i not in missing]
    suspect = [i for i in suspect if i not in missing and i not in reproved]

    flagsDf = pd.DataFrame({'flags': flags})
    flagsDf.iloc[missing] += "%d" % QC_flags.MISSING
    flagsDf.iloc[reproved] += "%d" % QC_flags.BAD_DATA
    flagsDf.iloc[suspect] += "%d" % QC_flags.SUSPECT
    flagsDf.iloc[unevaluated] += "%d" % QC_flags.UNKNOWN
    flagged = list(dict.fromkeys(list(missing) + reproved + suspect + unevaluated))
    flagsDf.iloc[~flagsDf.index.isin(flagged)] += ("%d" % QC_flags.GOOD_DATA)
    return list(flagsDf['flags'])


def range_test(parameter, flags, range_min, range_max, fail_flag=QC_flags.BAD_DATA):
    # fail_flag: BAD_DATA for the sensor range (physically impossible);
    # SUSPECT for the environmental/climatological range (QARTOD: values outside
    # the regional envelope are suspect, not necessarily bad)
    missing = np.where(parameter.isna())[0]
    bad = np.concatenate(
        (np.where(range_max < parameter)[0], np.where((parameter < range_min))[0])
    )
    bad = [i for i in bad if i not in missing]
    flag = pd.DataFrame(flags)
    flag.iloc[missing] += "%d" % QC_flags.MISSING
    flag.iloc[bad] += "%d" % fail_flag
    flag.iloc[
        ~flag.index.isin(list(dict.fromkeys(np.concatenate((bad, missing)))))
    ] += ("%d" % QC_flags.GOOD_DATA)
    flags = list(flag[0])
    return flags


def sigma_rate_of_change_test(
    n_lines, ParamObs, n_cel, flags, ms_interval, time_window, rc_fail, rc_susp, DIR,
    var_positions=None
):
    # QARTOD rate-of-change test: |V_n - V_(n-1)| compared to factor x local sigma.
    # Aligned with QARTOD, the exceedance is flagged SUSPECT (3), never BAD:
    # real rapid variations (fronts, upwelling) do occur.
    # var_positions: positions of the flag string that belong to THIS variable;
    # used to propagate 'not evaluable' when the previous value of this variable
    # was already rejected/missing (without them, flags of other variables would
    # contaminate).
    interval_s = ms_interval.item().total_seconds()
    n_samples = parse_time_window_samples(time_window, interval_s, n_lines)
    if n_samples < MIN_SIGMA_SAMPLES:
        # a window too small does not estimate a stable local sigma; before this
        # the test silently became a no-op (sigma NaN -> nothing rejected)
        print("Warning: rate-of-change window '%s' spans only %d sample(s) at this "
              "sampling interval; using the whole-series sigma instead."
              % (time_window, n_samples))
        n_samples = n_lines

    index = np.arange(n_lines)
    df_flags = pd.DataFrame({"flag": flags})
    bad, suspect, unknown, missing = ([], [], [], [])
    for level in range(n_cel):
        i_bin = index[level::n_cel]
        PO = ParamObs[i_bin].copy()
        if DIR == False:
            std = pd.DataFrame({"sigma": robust_rolling_sigma(PO, n_samples)})
        elif DIR == True:
            std = []
            for i in range(len(PO)):
                if i < n_samples:
                    std.append(
                        (stats.circstd(PO.iloc[i : i + n_samples]) * 180) / np.pi
                    )
                elif i >= n_samples:
                    std.append(
                        (stats.circstd(PO.iloc[i - n_samples : i]) * 180) / np.pi
                    )
            std = pd.DataFrame({"sigma": std})
            std.index = i_bin
        RC = (
            PO.diff().abs()
            if DIR == False
            else np.abs((PO.diff() + 180 + 360) % 360 - 180)
        )
        # QARTOD: rate-of-change only produces SUSPECT; the two factors become
        # levels of the same flag (>= susp is already suspect)
        suspect += list((PO.loc[RC >= rc_susp * std.sigma]).index)
        missing += list((PO.loc[PO.isna()]).index)
        # previous value missing -> diff not evaluable (independent of prior flags)
        unknown += list(PO.index[PO.shift(1).isna() & PO.notna()])
    for f in range(len(df_flags)):
        if f < n_cel:
            unknown.append(f)
        else:
            prior = df_flags["flag"].iloc[f]
            if var_positions is not None:
                prior = ''.join(prior[p] for p in var_positions if p < len(prior))
            if re.search("9|4", prior):
                unknown.append(f)
                if f < len(df_flags) - n_cel:
                    unknown.append(f + n_cel)
    unknown = [i for i in unknown if i not in missing]
    bad = [i for i in bad if i not in missing]
    bad = [i for i in bad if i not in unknown]
    suspect = [i for i in suspect if i not in missing]
    suspect = [i for i in suspect if i not in unknown]
    suspect = [i for i in suspect if i not in bad]
    df_flags.iloc[unknown] += "%d" % QC_flags.UNKNOWN
    df_flags.iloc[missing] += "%d" % QC_flags.MISSING
    df_flags.iloc[bad] += "%d" % QC_flags.BAD_DATA
    df_flags.iloc[suspect] += "%d" % QC_flags.SUSPECT
    df_flags.iloc[
        ~df_flags.index.isin(list(dict.fromkeys(unknown + missing + bad + suspect)))
    ] += ("%d" % QC_flags.GOOD_DATA)
    return list(df_flags["flag"])


def single_flat_line_test(
    n_samples, n_cel, data, flags, rep_cnt_fail, rep_cnt_suspect
):
    # Flat line test (QARTOD): rep_cnt consecutive observations that do not differ
    # by more than eps => stuck sensor. Sporadic NaNs do NOT interrupt the
    # count (a stuck sensor that emits occasional NaNs remains detectable):
    # the sequence is evaluated over the valid values. Vectorized (O(n)).
    eps = get_eps(data)
    v = np.asarray(data, dtype=float)
    missing_mask = np.isnan(v) | (v == -9)  # -9: legacy missing-value sentinel
    out_char = np.full(n_samples, '%d' % QC_flags.GOOD_DATA, dtype='<U1')
    out_char[missing_mask] = '%d' % QC_flags.MISSING

    valid_idx = np.where(~missing_mask)[0]
    vv = v[valid_idx]
    if len(vv) > 0:
        # length of the "flat" sequence ending at each valid sample
        same = np.abs(np.diff(vv)) <= eps
        starts = np.r_[True, ~same]
        pos = np.arange(len(vv))
        start_idx = np.maximum.accumulate(np.where(starts, pos, 0))
        run = pos - start_idx + 1
        # flat sequence that touches the start of the data and has not yet reached
        # rep_cnt_fail: may be a continuation of an earlier stretch -> not evaluable
        unknown_mask = (start_idx == 0) & (run == pos + 1) & (pos + 1 < rep_cnt_fail)
        char_vv = np.where(run >= rep_cnt_fail, '%d' % QC_flags.BAD_DATA,
                   np.where(run >= rep_cnt_suspect, '%d' % QC_flags.SUSPECT,
                   np.where(unknown_mask, '%d' % QC_flags.UNKNOWN,
                            '%d' % QC_flags.GOOD_DATA)))
        out_char[valid_idx] = char_vv

    return [flags[i] + out_char[i] for i in range(n_samples)]


def vertical_gradient_test(values, depth, flags, grad_fail, grad_susp, min_dz=0.05):
    # Vertical gradient test (profiles): |dV/dz| between consecutive samples,
    # compared to relative thresholds (factor x robust sigma of the profile's
    # gradients). Uses the real depth (dV/dz), not the time sequence.
    # - NaN value -> MISSING
    # - first point, neighbour of a NaN or |dz| < min_dz (stopped at the same
    #   depth) -> UNKNOWN (indeterminate gradient)
    v = np.asarray(values, dtype=float)
    z = np.asarray(depth, dtype=float)
    n = len(v)

    grad = np.full(n, np.nan)
    dz = np.full(n, np.nan)
    dz[1:] = z[1:] - z[:-1]
    with np.errstate(divide='ignore', invalid='ignore'):
        grad[1:] = (v[1:] - v[:-1]) / dz[1:]
    computable = np.zeros(n, dtype=bool)
    computable[1:] = (~np.isnan(v[1:])) & (~np.isnan(v[:-1])) & \
                     (~np.isnan(dz[1:])) & (np.abs(dz[1:]) >= min_dz)

    # the deviation is measured relative to the profile's TYPICAL gradient (median):
    # a stratified profile has a nonzero background gradient, and the test looks
    # for anomalous deviations from that behaviour, not the gradient itself
    valid_grads = grad[computable]
    if len(valid_grads) >= 4:
        med = np.nanmedian(valid_grads)
        sigma = 1.4826 * np.nanmedian(np.abs(valid_grads - med))
        if not np.isfinite(sigma) or sigma <= 0:
            sigma = np.nanstd(valid_grads)
    else:
        med, sigma = np.nan, np.nan  # insufficient gradients: not evaluable

    out = []
    for i in range(n):
        if np.isnan(v[i]):
            out.append(flags[i] + "%d" % QC_flags.MISSING)
        elif not computable[i] or not np.isfinite(sigma) or sigma <= 0:
            out.append(flags[i] + "%d" % QC_flags.UNKNOWN)
        elif np.abs(grad[i] - med) >= grad_fail * sigma:
            out.append(flags[i] + "%d" % QC_flags.BAD_DATA)
        elif np.abs(grad[i] - med) >= grad_susp * sigma:
            out.append(flags[i] + "%d" % QC_flags.SUSPECT)
        else:
            out.append(flags[i] + "%d" % QC_flags.GOOD_DATA)
    return out


def light_fouling_baseline(datetimes, light, baseline_days=7, cutoff_frac=0.5,
                           sustain_days=3, recovery_day_frac=0.2):
    """Light sensor fouling analysis (HOBO): the light "usage window".

    Logic: the daily light peak of the unfouled sensor (baseline = highest peak
    of the first `baseline_days` days) decays as the sensor gets fouled. The
    proposed cutoff is the start of the FINAL sustained run (>= `sustain_days`)
    where the daily peak stays below `cutoff_frac` x baseline AND never rises
    back to the threshold afterwards. In other words, light that recovers above
    the threshold is kept; only the permanent decline at the end is cut. If the
    light never permanently drops (it still reaches the threshold at the end, or
    the final dip is shorter than `sustain_days`), no cutoff is proposed.

    It does NOT assume monotonic decay. If the daily peak dips below the threshold
    and later recovers above it, it issues a WARNING: the signal is not clean
    biofouling - likely sensor cleaning/redeployment or patchy fouling - and the
    file may span more than one deployment. The operator confirms/adjusts the
    cutoff during review.

    Returns dict: 'evaluable' (bool), 'baseline', 'threshold', 'daily_peak'
    (Series), 'proposed_cutoff' (Timestamp|None), 'recovers' (bool),
    'recovery_day_frac_after' (float) and 'warnings' (list[str]).
    """
    out = {'evaluable': False, 'baseline': np.nan, 'threshold': np.nan,
           'daily_peak': pd.Series(dtype=float), 'proposed_cutoff': None,
           'recovers': False, 'recovery_day_frac_after': 0.0, 'warnings': [],
           'params': {'baseline_days': baseline_days, 'cutoff_frac': cutoff_frac,
                      'sustain_days': sustain_days}}

    s = pd.Series(np.asarray(light, dtype=float), index=pd.DatetimeIndex(datetimes))
    s = s.dropna()
    if s.empty:
        out['warnings'].append('Light fouling test: no valid light data - test not evaluated.')
        return out

    daily_peak = s.resample('D').max().dropna()
    out['daily_peak'] = daily_peak
    if len(daily_peak) < baseline_days + sustain_days:
        out['warnings'].append('Light fouling test: only %d day(s) of data - too short to '
                               'establish a clean-sensor baseline of %d day(s); test not evaluated.'
                               % (len(daily_peak), baseline_days))
        return out

    baseline = daily_peak.iloc[:baseline_days].max()
    if not np.isfinite(baseline) or baseline <= 0:
        out['warnings'].append('Light fouling test: clean-sensor baseline is zero (sensor dark or '
                               'buried from the start?) - test not evaluated.')
        return out

    threshold = cutoff_frac * baseline
    out.update({'evaluable': True, 'baseline': float(baseline), 'threshold': float(threshold)})

    below_arr = (daily_peak < threshold).to_numpy()
    ge_positions = np.where(~below_arr)[0]      # days whose peak still reaches the threshold
    below_positions = np.where(below_arr)[0]

    # Proposed cutoff = start of the FINAL sustained run below the threshold that
    # reaches the end of the series (the light never recovers to the threshold
    # after it). Recovered points are kept; only the permanent decline is cut.
    cutoff = None
    if len(below_positions) > 0:
        if len(ge_positions) == 0:
            cutoff = daily_peak.index[0]            # never reaches threshold: fouled from day 1
        else:
            last_ge = int(ge_positions[-1])
            tail_len = len(daily_peak) - 1 - last_ge   # below-threshold days after the last crossing
            if tail_len >= sustain_days:
                cutoff = daily_peak.index[last_ge + 1]
            # else: only a short dip at the very end (likely clouds) -> no cutoff
    out['proposed_cutoff'] = cutoff

    # Non-monotonic signal: the peak dipped below the threshold and later rose
    # back above it (recovery). Warn - likely cleaning/redeployment or patchy
    # fouling; the file may span more than one deployment.
    if len(below_positions) > 0 and len(ge_positions) > 0 and below_positions.min() < ge_positions.max():
        after = daily_peak.iloc[int(below_positions.min()):]
        frac = float((after >= threshold).mean())
        out['recovery_day_frac_after'] = frac
        if frac > recovery_day_frac:
            out['recovers'] = True
            out['warnings'].append(
                'Warning: the daily light peak dips below the fouling threshold and then '
                'recovers above it on %.0f%% of the following days - not a clean, monotonic '
                'biofouling decline. Likely sensor cleaning/redeployment, patchy fouling or '
                'cloudy spells%s. Review the cutoff on the plot (drag it or press N for no '
                'cutoff) and check whether this file spans more than one deployment.'
                % (100 * frac, '' if cutoff is not None else ' - no permanent cutoff was set'))
    return out


def apply_light_window(datetimes, light, flags, cutoff, evaluable=True):
    """Appends 1 flag character per sample for the light:
    9 = missing value; 2 = test not evaluable; 4 = after the fouling cutoff
    (BAD = unusable fouled light; the value is kept in the sheet until the user
    removes it with 'Remove Bad Data'); 1 = inside the usage window."""
    ts = pd.DatetimeIndex(datetimes)
    v = np.asarray(light, dtype=float)
    out = []
    for i in range(len(v)):
        if np.isnan(v[i]):
            out.append(flags[i] + '%d' % QC_flags.MISSING)
        elif not evaluable:
            out.append(flags[i] + '%d' % QC_flags.UNKNOWN)
        elif cutoff is not None and ts[i] >= cutoff:
            out.append(flags[i] + '%d' % QC_flags.BAD_DATA)
        else:
            out.append(flags[i] + '%d' % QC_flags.GOOD_DATA)
    return out


def density_inversion_test(data, flags, tolerance, lat, lon):
    # QARTOD density inversion test (profiles only): potential density (sigma0)
    # must not decrease with depth beyond a tolerance. Inverted pairs are
    # flagged SUSPECT. Appends exactly one flag character per row.
    import gsw
    n = len(flags)

    # needs temperature, salinity and a vertical coordinate; otherwise the test
    # cannot be evaluated for any row (flag 2 = unknown)
    if 'Temperature (degC)' not in data.columns or 'Salinity (PSU)' not in data.columns:
        return [flags[i] + "%d" % QC_flags.UNKNOWN for i in range(n)]
    if 'Depth (m)' in data.columns:
        vert = np.asarray(data['Depth (m)'], dtype=float)
    elif 'Pressure (dbar)' in data.columns:
        vert = np.asarray(data['Pressure (dbar)'], dtype=float)
    else:
        return [flags[i] + "%d" % QC_flags.UNKNOWN for i in range(n)]

    t = np.asarray(data['Temperature (degC)'], dtype=float)
    s = np.asarray(data['Salinity (PSU)'], dtype=float)
    p = np.asarray(data['Pressure (dbar)'], dtype=float) if 'Pressure (dbar)' in data.columns else vert

    # potential density anomaly (ref 0 dbar); lat/lon affect only the absolute
    # value, which cancels in the vertical differences used by the test
    SA = gsw.SA_from_SP(s, p, lon, lat)
    CT = gsw.CT_from_t(SA, t, p)
    sigma0 = np.asarray(gsw.sigma0(SA, CT), dtype=float)

    # walk from surface to bottom; a deeper point lighter than the previous valid
    # (shallower) one by more than the tolerance is an inversion (both flagged
    # as SUSPECT - it signals a suspect T/S pair, not necessarily bad data)
    inverted = set()
    last = None
    for k in np.argsort(vert, kind='stable'):
        if np.isnan(sigma0[k]) or np.isnan(vert[k]):
            continue
        if last is not None and sigma0[k] < sigma0[last] - tolerance:
            inverted.add(int(k))
            inverted.add(int(last))
        last = k

    out = []
    for i in range(n):
        if np.isnan(sigma0[i]):
            out.append(flags[i] + "%d" % QC_flags.UNKNOWN)
        elif i in inverted:
            out.append(flags[i] + "%d" % QC_flags.SUSPECT)
        else:
            out.append(flags[i] + "%d" % QC_flags.GOOD_DATA)
    return out


# ---------------------------------------------------------------------------
# DCPS / Doppler current-profiler qualification (v8.0). Runs on the tidy frame
# produced by data.read_seaguard_doppler (one row per record x depth cell).
# Four tests, one flag character per test in this order (same architecture as
# the scalar flag string): current range, signal quality, speed stdev, tilt.
# ---------------------------------------------------------------------------

DOPPLER_TEST_SEQUENCE = [
    ('cur_range', 'Current speed range'),
    ('cur_signal', 'Signal quality (strength + cell state)'),
    ('cur_stdev', 'Speed standard deviation'),
    ('cur_tilt', 'Instrument tilt'),
]

DOPPLER_DEFAULTS = {
    'max_speed': 300.0,       # cm/s - physical cap for coastal reef currents
    'min_strength': -60.0,    # dB   - below the acoustic noise floor -> BAD
    'max_stdev': 50.0,        # cm/s - single-ping stdev above this -> SUSPECT
    'tilt_suspect': 15.0,     # deg  - manual: compensation degrades over this
    'tilt_bad': 35.0,         # deg
}


def doppler_qc(frame, settings=None):
    """Qualifies a Doppler current frame. Returns (flags, Flag_cur):
    flags = list of 4-char strings (one per row, DOPPLER_TEST_SEQUENCE order);
    Flag_cur = per-row rollup with the scalar priority (4 > 3 > 9 > 1)."""
    s = dict(DOPPLER_DEFAULTS)
    if settings:
        s.update({k: v for k, v in settings.items() if k in DOPPLER_DEFAULTS})
    speed = frame['Horizontal speed (cm/s)'].to_numpy(float)
    strength = frame['Signal strength (dB)'].to_numpy(float)
    state = frame['Cell state'].to_numpy(float)
    stdev = frame['Speed stdev (cm/s)'].to_numpy(float)
    tilt = frame['Tilt (deg)'].to_numpy(float)
    missing = np.isnan(speed)

    n = len(frame)
    flags = []
    rollup = np.ones(n, dtype=int)
    for i in range(n):
        if missing[i]:
            flags.append('%d' % QC_flags.MISSING * 4)
            rollup[i] = QC_flags.MISSING
            continue
        f = ''
        # 1) current range: impossible magnitude
        f += '%d' % (QC_flags.BAD_DATA if (speed[i] < 0 or speed[i] > s['max_speed'])
                     else QC_flags.GOOD_DATA)
        # 2) signal quality: cell state != 0 (out of range / no echo), return
        #    strength below the noise floor, or strength >= 0 dB - genuine
        #    echoes are always negative dB; 0.0 is the 'no ping' placeholder
        bad_sig = (not np.isnan(state[i]) and state[i] != 0) or \
                  (not np.isnan(strength[i]) and
                   (strength[i] < s['min_strength'] or strength[i] >= 0.0))
        f += '%d' % (QC_flags.BAD_DATA if bad_sig else QC_flags.GOOD_DATA)
        # 3) noisy measurement: single-ping stdev too high
        f += '%d' % (QC_flags.SUSPECT if (not np.isnan(stdev[i]) and stdev[i] > s['max_stdev'])
                     else QC_flags.GOOD_DATA)
        # 4) instrument attitude: tilt compromises the whole record
        if np.isnan(tilt[i]):
            f += '%d' % QC_flags.UNKNOWN
        elif tilt[i] > s['tilt_bad']:
            f += '%d' % QC_flags.BAD_DATA
        elif tilt[i] > s['tilt_suspect']:
            f += '%d' % QC_flags.SUSPECT
        else:
            f += '%d' % QC_flags.GOOD_DATA
        flags.append(f)
        chars = [int(c) for c in f]
        if QC_flags.BAD_DATA in chars:
            rollup[i] = QC_flags.BAD_DATA
        elif QC_flags.SUSPECT in chars:
            rollup[i] = QC_flags.SUSPECT
        else:
            rollup[i] = QC_flags.GOOD_DATA
    return flags, rollup


# ---------------------------------------------------------------------------
# Redundant-replicate referee (v9.0)
# ---------------------------------------------------------------------------
# Redundant HOBO replicates only help while BOTH loggers work. When one drifts,
# combine_hobo_replicates averages a sound and a faulty sensor: the disagreement
# is flagged SUSPECT, but a suspect flag does not fix the value, and dropping
# the suspect rows would throw away the sound replicate too.
#
# The individual QC cannot catch this - a sensor stuck on a PLAUSIBLE value
# passes every single-series test (sensor/environmental range, spike, rate of
# change, flat line). Only a comparison decides which replicate is sound, and
# it must be against an INDEPENDENT reference rather than an expected seasonal
# shape: requiring "temperature must fall in winter" would select the data that
# confirms the expectation, and a genuine marine heatwave would be condemned as
# sensor failure. Contemporaneous loggers at OTHER sites share the regional
# forcing and settle it empirically - if a heatwave warms the region, the
# reference warms with it and nobody is misjudged.

REPLICATE_REFEREE_DEFAULTS = {
    'temp_tol': 0.5,        # degC of spread that counts as disagreement
    'min_frac': 0.20,       # fraction of the record in disagreement to act on
    'min_points': 4,        # reference points needed to arbitrate at all
    'min_margin': 0.30,     # change-correlation lead needed to name a replicate
    # the reference must describe THIS site before it may judge it: a tide-pool
    # deployment is not arbitrated by reef loggers (different thermal regime)
    'min_ref_corr': 0.50,
    # the offset-drift and swing criteria MEASURE a replicate against the
    # reference, so they are only meaningful when the reference genuinely
    # tracks this site - a weak match may still allow the correlation lead to
    # decide, but not those two
    'min_ref_corr_secondary': 0.70,
    # offset-drift criterion: a replicate whose offset from the reference SHIFTS
    # between the agreement and the disagreement window is the one that moved.
    # (Absolute bias cannot decide - the site may genuinely sit warmer than the
    # region; what a sound logger keeps is a STABLE offset.)
    'min_bias_shift': 1.00,     # degC of shift to act on
    'bias_shift_ratio': 2.00,   # how many times the runner-up's shift
    # amplitude criterion: a damped or exaggerated seasonal swing is faulty even
    # when the shape still correlates
    'amp_bad': 2.00,        # factor away from the reference that is faulty
    'amp_good': 1.50,       # factor within which a replicate is acceptable
}


def _referee_cadence(index):
    """Resampling step giving a handful of comparison points for this
    deployment (monthly for seasonal records, weekly/daily for short ones)."""
    span_days = (index.max() - index.min()).total_seconds() / 86400.0
    if span_days > 150:
        return 'MS'
    if span_days > 30:
        return 'W'
    return 'D'


def replicate_referee(replicates, reference=None, settings=None):
    """Diagnoses sustained disagreement between redundant replicates and, when a
    reference is available, says WHICH replicate is sound.

    replicates: list of qualified HOBO frames ('Datetime', 'Temperature (degC)',
        optionally 'Flag_T' - only samples flagged <= 2 are compared).
    reference: optional temperature Series indexed by time, from INDEPENDENT
        contemporaneous loggers (other sites). Without it the disagreement is
        still reported, but no replicate is named.

    Returns a dict with 'disagrees', 'frac_over', 'max_spread', 'scores'
    (per replicate: change_corr, bias, amplitude, amplitude_ratio),
    'recommended' (index or None), 'verdict' and 'warnings'.
    """
    s = dict(REPLICATE_REFEREE_DEFAULTS)
    if settings:
        s.update({k: v for k, v in settings.items() if k in REPLICATE_REFEREE_DEFAULTS})
    out = {'disagrees': False, 'frac_over': 0.0, 'max_spread': 0.0, 'scores': [],
           'recommended': None, 'verdict': '', 'warnings': []}
    if len(replicates) < 2:
        out['verdict'] = 'single replicate - nothing to arbitrate'
        return out

    series = []
    for r in replicates:
        t = pd.DatetimeIndex(pd.to_datetime(r['Datetime']))
        v = pd.to_numeric(r['Temperature (degC)'], errors='coerce')
        if 'Flag_T' in r.columns:
            v = v.where(pd.to_numeric(r['Flag_T'], errors='coerce') <= 2)
        x = pd.Series(v.to_numpy(), index=t).sort_index()
        # duplicated timestamps DO occur in these exports (one file carries
        # 8833 of them) and reindex refuses to work on a duplicated axis
        series.append(x[~x.index.duplicated(keep='first')])
    grid = series[0].index
    aligned = [x.reindex(grid, method='nearest', tolerance=pd.Timedelta(minutes=30))
               for x in series]
    M = pd.concat(aligned, axis=1)
    spread = (M.max(axis=1) - M.min(axis=1)).where(M.notna().sum(axis=1) >= 2)
    over = spread > s['temp_tol']
    out['frac_over'] = float(over.mean()) if len(over) else 0.0
    out['max_spread'] = float(spread.max()) if spread.notna().any() else 0.0
    out['disagrees'] = out['frac_over'] >= s['min_frac']
    if not out['disagrees']:
        out['verdict'] = ('replicates agree (%.0f%% of the record above %.1f degC)'
                          % (100 * out['frac_over'], s['temp_tol']))
        return out

    if reference is None or not len(reference):
        out['warnings'].append(
            'Replicate referee: the replicates disagree on %.0f%% of the record '
            '(up to %.2f degC), but no independent reference was supplied, so '
            'neither can be named - both were kept and combined. Provide '
            'contemporaneous data from other sites to arbitrate.'
            % (100 * out['frac_over'], out['max_spread']))
        out['verdict'] = 'disagreement, no reference to arbitrate'
        return out

    freq = _referee_cadence(grid)
    ref = pd.Series(reference).sort_index().resample(freq).mean()
    d_ref = ref.diff().dropna()
    if len(d_ref) < s['min_points']:
        out['warnings'].append(
            'Replicate referee: only %d reference point(s) at %s cadence - too '
            'short to arbitrate; both replicates kept.' % (len(d_ref), freq))
        out['verdict'] = 'disagreement, reference too short'
        return out
    ref_amp = float(ref.max() - ref.min())

    # which periods are the replicates in disagreement? (same cadence as ref)
    dis = over.resample(freq).mean() > 0.5

    for i, x in enumerate(aligned):
        m = x.resample(freq).mean()
        d = m.diff().dropna()
        common = d_ref.index.intersection(d.index)
        corr = (float(np.corrcoef(d_ref[common], d[common])[0, 1])
                if len(common) >= 2 else np.nan)
        dev = m.reindex(ref.index) - ref            # offset from the reference
        bias = float(dev.mean())
        # offset BEFORE vs DURING the disagreement: a sound logger keeps the
        # site's own offset, a drifting one moves away from it
        dmask = dis.reindex(ref.index).fillna(False)
        before, during = dev[~dmask].dropna(), dev[dmask].dropna()
        shift = (float(during.mean() - before.mean())
                 if len(before) and len(during) else np.nan)
        amp = float(m.max() - m.min())
        out['scores'].append({'replicate': i, 'change_corr': corr, 'bias': bias,
                              'bias_shift': shift, 'amplitude': amp,
                              'amplitude_ratio': (amp / ref_amp) if ref_amp else np.nan})

    usable = [sc for sc in out['scores'] if np.isfinite(sc['change_corr'])]
    if len(usable) < 2:
        out['verdict'] = 'disagreement, not enough comparable replicates'
        return out

    # Does the reference describe this site at all? A tide pool is not
    # arbitrated by reef loggers - refuse rather than judge on a bad yardstick.
    if max(sc['change_corr'] for sc in usable) < s['min_ref_corr']:
        out['warnings'].append(
            'Replicate referee: the replicates disagree (up to %.2f degC) but NO '
            'replicate tracks the reference (best correlation %.2f) - the '
            'reference does not describe this site (a pool judged by reef '
            'loggers?), so nobody was named.'
            % (out['max_spread'], max(sc['change_corr'] for sc in usable)))
        out['verdict'] = 'disagreement, reference does not describe this site'
        return out

    # Criteria in order, each with its own margin; the first that separates the
    # replicates decides, and the verdict says which one did.
    best = worst = None
    ranked = sorted(usable, key=lambda sc: sc['change_corr'], reverse=True)
    if ranked[0]['change_corr'] - ranked[1]['change_corr'] >= s['min_margin']:
        best, worst, why = ranked[0], ranked[-1], 'it tracks the reference'
    # the secondary criteria compare each replicate WITH the reference, so they
    # need it to actually describe the site (a weak match may still let the
    # correlation lead above decide, but not these)
    secondary_ok = max(sc['change_corr'] for sc in usable) >= s['min_ref_corr_secondary']
    if best is None and secondary_ok:
        shifts = [sc for sc in usable if np.isfinite(sc.get('bias_shift', np.nan))]
        if len(shifts) >= 2:
            by_shift = sorted(shifts, key=lambda sc: abs(sc['bias_shift']))
            drift, steady = by_shift[-1], by_shift[0]
            if (abs(drift['bias_shift']) >= s['min_bias_shift'] and
                    abs(drift['bias_shift']) >= s['bias_shift_ratio'] * max(abs(steady['bias_shift']), 1e-6)):
                best, worst = steady, drift
                why = 'its offset from the reference stayed put'
    if best is None and secondary_ok:
        rated = [sc for sc in usable if np.isfinite(sc['amplitude_ratio'])]

        def _off(sc):                       # how far from the reference swing
            r = sc['amplitude_ratio']
            return max(r, 1.0 / r) if r > 0 else np.inf
        if len(rated) >= 2:
            by_amp = sorted(rated, key=_off)
            if _off(by_amp[-1]) >= s['amp_bad'] and _off(by_amp[0]) <= s['amp_good']:
                best, worst = by_amp[0], by_amp[-1]
                why = 'its seasonal swing matches the reference'
    if best is None:
        out['warnings'].append(
            'Replicate referee: the replicates disagree (up to %.2f degC) but no '
            'criterion separates them (correlation, offset drift, seasonal '
            'amplitude) - no replicate named; review manually.' % out['max_spread'])
        out['verdict'] = 'disagreement, replicates score too close to separate'
        return out

    out['recommended'] = best['replicate']
    out['verdict'] = (
        'replicate %d is the sound one - %s (change-correlation %+.2f, offset '
        '%+.2f degC, offset drift %+.2f, swing %.2fx the reference), while '
        'replicate %d does not (%+.2f, %+.2f, %+.2f, %.2fx) - replicate %d looks '
        'faulty'
        % (best['replicate'] + 1, why, best['change_corr'], best['bias'],
           best.get('bias_shift', float('nan')), best['amplitude_ratio'],
           worst['replicate'] + 1, worst['change_corr'], worst['bias'],
           worst.get('bias_shift', float('nan')), worst['amplitude_ratio'],
           worst['replicate'] + 1))
    out['warnings'].append('Replicate referee: ' + out['verdict'] + '.')
    return out

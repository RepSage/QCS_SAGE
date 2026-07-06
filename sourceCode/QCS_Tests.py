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
        print("WARNING: spike-test window '%s' spans only %d sample(s) at this "
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
        print("WARNING: rate-of-change window '%s' spans only %d sample(s) at this "
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


def light_fouling_baseline(datetimes, light, baseline_days=5, cutoff_frac=0.5,
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
                'WARNING: the daily light peak dips below the fouling threshold and then '
                'recovers above it on %.0f%% of the following days - not a clean, monotonic '
                'biofouling decline. Likely sensor cleaning/redeployment, patchy fouling or '
                'cloudy spells%s. Review the cutoff on the plot (drag it or press N for no '
                'cutoff) and check whether this file spans more than one deployment.'
                % (100 * frac, '' if cutoff is not None else ' - no permanent cutoff was set'))
    return out


def apply_light_window(datetimes, light, flags, cutoff, evaluable=True):
    """Appends 1 flag character per sample for the light:
    9 = missing value; 2 = test not evaluable; 3 = after the fouling cutoff
    (suspect; the value is kept); 1 = inside the usage window."""
    ts = pd.DatetimeIndex(datetimes)
    v = np.asarray(light, dtype=float)
    out = []
    for i in range(len(v)):
        if np.isnan(v[i]):
            out.append(flags[i] + '%d' % QC_flags.MISSING)
        elif not evaluable:
            out.append(flags[i] + '%d' % QC_flags.UNKNOWN)
        elif cutoff is not None and ts[i] >= cutoff:
            out.append(flags[i] + '%d' % QC_flags.SUSPECT)
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

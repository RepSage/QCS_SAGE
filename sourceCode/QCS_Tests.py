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
def outlier_test(dataframe, parameter, n_cel, flags, time_window, sample_interval, threshold_fail, threshold_susp):
    # QARTOD 3-point spike test: spike = |V2 - (V1 + V3)/2|, compared to a
    # relative threshold (factor x local standard deviation of the values).
    # Single pass (no iterative removal). Endpoints have no neighbours and are
    # therefore not evaluated as spikes.
    pop = dataframe[parameter].copy()
    n = len(pop)
    spike = (pop - (pop.shift(1) + pop.shift(-1)) / 2).abs()

    # local standard deviation used as the relative threshold reference
    if re.search("whole", time_window, re.IGNORECASE):
        win = n
    else:
        if re.search(r"\d+d", time_window, re.IGNORECASE):
            time_period = 24 * 3600 * int(re.search(r"\d+", time_window).group())
        elif re.search(r"\d+h", time_window, re.IGNORECASE):
            time_period = 3600 * int(re.search(r"\d+", time_window).group())
        elif re.search(r"\d+m", time_window, re.IGNORECASE):
            time_period = 60 * int(re.search(r"\d+", time_window).group())
        elif re.search(r"\d+s", time_window, re.IGNORECASE):
            time_period = int(re.search(r"\d+", time_window).group())
        else:
            time_period = None
        win = n if time_period is None else int(time_period / (sample_interval / np.timedelta64(1, 's')))

    if win >= n or win < 3:
        std = pd.Series(pop.std(ddof=0), index=pop.index)
    else:
        std = pop.rolling(win, center=True, min_periods=3).std().bfill().ffill()

    upperLimit = (threshold_fail * std).abs().to_numpy()
    lowerLimit = (threshold_susp * std).abs().to_numpy()
    spike_vals = spike.to_numpy()

    missing = np.where(dataframe[parameter].isna())[0]
    reproved = list(np.where(spike_vals > upperLimit)[0])
    suspect = list(np.where((spike_vals > lowerLimit) & (spike_vals <= upperLimit))[0])
    reproved = [i for i in reproved if i not in missing]
    suspect = [i for i in suspect if i not in missing and i not in reproved]

    flagsDf = pd.DataFrame({'flags': flags})
    flagsDf.iloc[missing] += "%d" % QC_flags.MISSING
    flagsDf.iloc[reproved] += "%d" % QC_flags.BAD_DATA
    flagsDf.iloc[suspect] += "%d" % QC_flags.SUSPECT
    flagged = list(dict.fromkeys(list(missing) + reproved + suspect))
    flagsDf.iloc[~flagsDf.index.isin(flagged)] += ("%d" % QC_flags.GOOD_DATA)
    return list(flagsDf['flags'])


def range_test(parameter, flags, range_min, range_max):
    missing = np.where(parameter.isna())[0]
    bad = np.concatenate(
        (np.where(range_max < parameter)[0], np.where((parameter < range_min))[0])
    )
    bad = [i for i in bad if i not in missing]
    flag = pd.DataFrame(flags)
    flag.iloc[missing] += "%d" % QC_flags.MISSING
    flag.iloc[bad] += "%d" % QC_flags.BAD_DATA
    flag.iloc[
        ~flag.index.isin(list(dict.fromkeys(np.concatenate((bad, missing)))))
    ] += ("%d" % QC_flags.GOOD_DATA)
    flags = list(flag[0])
    return flags

def sigma_rate_of_change_test(
    n_lines, ParamObs, n_cel, flags, ms_interval, time_window, rc_fail, rc_susp, DIR
):
    ms_interval = ms_interval.item().total_seconds()
    if re.search("D", time_window, re.IGNORECASE):
        ms_interval = ms_interval / 86400
    elif re.search("H", time_window, re.IGNORECASE):
        ms_interval = ms_interval / 3600
    elif re.search("M", time_window, re.IGNORECASE):
        ms_interval = ms_interval / 60
    elif re.search("S", time_window, re.IGNORECASE):
        pass
    if re.search("whole", time_window, re.IGNORECASE):
        n_samples = n_lines
    else:
        n_samples = int(int(re.search(r"\d{1,}", time_window).group()) / ms_interval)
    index = np.arange(n_lines)
    df_flags = pd.DataFrame({"flag": flags})
    bad, suspect, unknown, missing = ([], [], [], [])
    for level in range(n_cel):
        i_bin = index[level::n_cel]
        PO = ParamObs[i_bin].copy()
        if DIR == False:
            std = PO.rolling(n_samples).std()
            PO_reverse = PO[::-1]
            std_reverse = PO_reverse.rolling(n_samples).std()
            std[: n_samples - 1] = std_reverse[::-1][: n_samples - 1]
            std = pd.DataFrame({"sigma": std})
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
        bad += (
            list((PO.loc[RC >= rc_fail * std.sigma]).index)
            if DIR == False
            else list((PO.loc[RC >= rc_fail * std.sigma]).index)
        )
        suspect += (
            list(
                (PO.loc[(rc_susp * std.sigma <= RC) & (RC < rc_fail * std.sigma)]).index
            )
            if DIR == False
            else list(
                (PO.loc[(rc_susp * std.sigma <= RC) & (RC < rc_fail * std.sigma)]).index
            )
        )
        missing += list((PO.loc[PO.isna()]).index)
    for f in range(len(df_flags)):
        if f < n_cel:
            unknown.append(f)
        elif re.search("9|4", df_flags["flag"].iloc[f]):
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

    eps = get_eps(data)
    indice = np.arange(0, n_samples)
    for n in range(n_cel):
        bin_n = np.asarray(data)[n::n_cel]
        i_bin = indice[n::n_cel]
        for i in range(len(i_bin)):
            sub = np.abs(bin_n[i] - bin_n[i - rep_cnt_fail : i])
            sub = sub[::-1]
            i_linha = i_bin[i]
            if bin_n[i] == -9 or np.isnan(bin_n[i]):
                flags[i_linha] += "%d" % QC_flags.MISSING
            elif i_linha < (n_cel * rep_cnt_fail) or any(np.isnan(sub)):
                flags[i_linha] += "%d" % QC_flags.UNKNOWN
            elif all(sub[0:rep_cnt_fail] <= eps):
                flags[i_linha] += "%d" % QC_flags.BAD_DATA
            elif all(sub[0:rep_cnt_suspect] <= eps) and not (
                all(sub[0:rep_cnt_fail] <= eps)
            ):
                flags[i_linha] += "%d" % QC_flags.SUSPECT
            elif any(sub[0:rep_cnt_suspect] > eps):
                flags[i_linha] += "%d" % QC_flags.GOOD_DATA
    return flags


def vertical_gradient_test(
    n_lines, PO, n_cel, flags, ms_interval, time_window, rc_fail, rc_susp, DIR
):
    ms_interval = ms_interval.item().total_seconds()
    if re.search("D", time_window, re.IGNORECASE):
        ms_interval = ms_interval / 86400
    elif re.search("H", time_window, re.IGNORECASE):
        ms_interval = ms_interval / 3600
    elif re.search("M", time_window, re.IGNORECASE):
        ms_interval = ms_interval / 60
    elif re.search("S", time_window, re.IGNORECASE):
        pass
    if re.search("whole", time_window, re.IGNORECASE):
        n_samples = n_lines
    else:
        n_samples = (
            int(int(re.search(r"\d{1,}", time_window).group()) / ms_interval)
        ) * n_cel
    df_flags = pd.DataFrame({"flag": flags})
    PO = PO.copy()
    PO = PO.replace(-9, np.nan)
    bad, suspect, unknown, missing = ([], [], [], [])
    if DIR == False:
        std = PO.rolling(n_samples).std()
        PO_reverse = PO[::-1]
        std_reverse = PO_reverse.rolling(n_samples).std()
        std[: n_samples - 1] = std_reverse[::-1][: n_samples - 1]
        std = pd.DataFrame({"sigma": std})
    elif DIR == True:
        std = []
        for i in range(len(PO)):
            if i < n_samples:
                std.append((stats.circstd(PO.iloc[i : i + n_samples]) * 180) / np.pi)
            elif i >= n_samples:
                std.append((stats.circstd(PO.iloc[i - n_samples : i]) * 180) / np.pi)
        std = pd.DataFrame({"sigma": std})
        std.index = PO.index
    RC = (
        PO.diff().abs() if DIR == False else np.abs((PO.diff() + 180 + 360) % 360 - 180)
    )
    bad += (
        list((PO.loc[RC >= rc_fail * std.sigma]).index)
        if DIR == False
        else list((PO.loc[RC >= rc_fail * std.sigma]).index)
    )
    suspect += (
        list((PO.loc[(rc_susp * std.sigma <= RC) & (RC < rc_fail * std.sigma)]).index)
        if DIR == False
        else list(
            (PO.loc[(rc_susp * std.sigma <= RC) & (RC < rc_fail * std.sigma)]).index
        )
    )
    missing += list((PO.loc[PO.isna()]).index)
    unknown = [0]
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
    flags = list(df_flags["flag"])
    return flags


def density_inversion_test(data, flags, tolerance, lat, lon):
    # QARTOD density inversion test (profiles only): potential density (sigma0)
    # must not decrease with depth beyond a tolerance. Inverted points are
    # flagged BAD. Appends exactly one flag character per row.
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

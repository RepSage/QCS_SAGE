################################################################################
import os
import re
import numpy as np
import pandas as pd
from scipy import stats
from io import StringIO
from string import Template
import matplotlib.pyplot as plt
from datetime import datetime as dt
################################################################################

class QC_flags:
    GOOD_DATA=1
    UNKNOWN=2
    SUSPECT=3
    BAD_DATA=4
    DISMISSED=5
    MISSING=9
################################################################################

def range_test(parameter, flags, range_min, range_max):
    missing = np.where(parameter.isna())[0]
    bad = np.concatenate((np.where(range_max < parameter)[0], np.where((parameter < range_min))[0]))
    bad = [i for i in bad if i not in missing]
    flag = pd.DataFrame(flags)
    flag.iloc[missing]+='%d'%QC_flags.MISSING
    flag.iloc[bad]+='%d'%QC_flags.BAD_DATA
    flag.iloc[~flag.index.isin(list(dict.fromkeys(np.concatenate((bad,missing)))))]+='%d'%QC_flags.GOOD_DATA
    flags = list(flag[0])
    return flags

def depth_range_test (data, depth_range):
    mean_depth = np.nanmean(data['Depth(m)'])
    missing = np.where(data['Depth(m)'].isna())[0]
    bad = np.concatenate((np.where(data['Depth(m)'] < mean_depth - depth_range)[0], np.where((data['Depth(m)'] > mean_depth + depth_range))[0]))
    bad = [i for i in bad if i not in missing]
    exceptions = ['Datetime', 'Sample Number', 'Pitch[Deg]', 'Roll[Deg]', 'Timer[s]']
    for name in data.columns:
        if name not in exceptions:
            data.loc[bad, name] = np.nan
    return data

def z_score_method(df, var, time_window, sample_interval, fail, susp):
    series = df[['Datetime', var]].copy()
    threshold = fail
    susp_threshold = susp
    z = []
    index = []
    outlier = []
    suspect = []
    if time_window == 'WHOLE':
        sample = series[var]
        z = np.abs((sample - sample.mean(skipna=True)) / sample.std(skipna=True, ddof=0))
    else:
        measurement_interval = sample_interval.astype(int)
        if re.search('\\d+d',time_window, re.IGNORECASE):
            time_period = 24 * 3600 * (int(re.search('\\d+',time_window).group()))
        elif re.search('\\d+h',time_window, re.IGNORECASE):
            time_period = 3600 * (int(re.search('\\d+',time_window).group()))
        elif re.search('\\d+m',time_window, re.IGNORECASE):
            time_period = 60 * (int(re.search('\\d+',time_window).group()))
        elif re.search('\\d+s',time_window, re.IGNORECASE):
            time_period = (int(re.search('\\d+',time_window).group()))
        sample_length = int(time_period /  measurement_interval)
        for i in range(len(series[var])):
            if i < sample_length-1:
                sample = series[var].iloc[i:i+sample_length]
                zi = np.abs((sample.iloc[0] - sample.mean(skipna=True)) / sample.std(skipna=True, ddof=0)) if sample.std(skipna=True, ddof=0) > 0 else float(0)
            elif i >= sample_length-1:
                sample = series[var].iloc[i-sample_length:i+1]
                zi = np.abs((sample.iloc[-1] - sample.mean(skipna=True)) / sample.std(skipna=True, ddof=0)) if sample.std(skipna=True, ddof=0) > 0 else float(0)
            z.append(zi)
    series['z_score'] = z
    outlier = np.where(series['z_score'] >= threshold)[0]
    suspect = np.where((susp_threshold <= series['z_score']) & (series['z_score'] < threshold))[0]
    return outlier, suspect

def z_score_spike_test(df, var, n_cel, flags, time_window, sample_interval, fail, susp):
    outlier, suspect = ([],[])
    for b in range(n_cel):
        outlier_b, suspect_b = z_score_method(df[b::n_cel], var, time_window, sample_interval, fail, susp)
        for item in outlier_b:
            outlier.append(b + (item * n_cel))
        for item in suspect_b:
            suspect.append(b + (item * n_cel))
    flag = pd.DataFrame(flags)
    flag.iloc[outlier]+='%d'%QC_flags.BAD_DATA
    flag.iloc[suspect]+='%d'%QC_flags.SUSPECT
    flag.iloc[~flag.index.isin(list(dict.fromkeys(outlier+suspect)))]+='%d'%QC_flags.GOOD_DATA
    flags = list(flag[0])
    return flags

def sigma_rate_of_change_test (n_lines, ParamObs, n_cel, flags, ms_interval, time_window, rc_fail, rc_susp, DIR):
    ms_interval = ms_interval.item().total_seconds()
    if re.search('D', time_window, re.IGNORECASE):
        ms_interval = ms_interval/86400
    elif re.search('H', time_window, re.IGNORECASE):
        ms_interval = ms_interval/3600
    elif re.search('M', time_window, re.IGNORECASE):
        ms_interval = ms_interval/60
    elif re.search('S', time_window, re.IGNORECASE):
        pass
    if re.search('whole', time_window, re.IGNORECASE):
        n_samples = n_lines
    else:
        n_samples = int(int(re.search('\d{1,}', time_window).group())/ ms_interval)
    index = np.arange(n_lines)
    df_flags = pd.DataFrame({'flag': flags})
    bad, suspect, unknown, missing = ([],[],[],[])
    for level in range(n_cel):
        i_bin = index[level::n_cel]
        PO = ParamObs[i_bin].copy()
        if DIR == False:
            std = PO.rolling(n_samples).std()
            PO_reverse = PO[::-1]
            std_reverse = PO_reverse.rolling(n_samples).std()
            std[:n_samples-1] = std_reverse[::-1][:n_samples-1]
            std = pd.DataFrame({'sigma':std})
        elif DIR == True:
            from scipy import stats
            std = []
            for i in range(len(PO)):
                if i < n_samples:
                    std.append((stats.circstd(PO.iloc[i:i+n_samples])*180)/np.pi)
                elif i >= n_samples:
                    std.append((stats.circstd(PO.iloc[i-n_samples:i])*180)/np.pi)
            std = pd.DataFrame({'sigma':std})
            std.index = i_bin
        RC = PO.diff().abs() if DIR==False else np.abs((PO.diff() + 180 + 360) % 360 - 180)
        bad += list((PO.loc[RC >= rc_fail * std.sigma]).index) if DIR==False else list((PO.loc[RC >= rc_fail * std.sigma]).index)
        suspect += list((PO.loc[(rc_susp * std.sigma <= RC) & (RC < rc_fail * std.sigma)]).index) if DIR==False else list((PO.loc[(rc_susp * std.sigma <= RC) & (RC < rc_fail * std.sigma)]).index)
        missing += list((PO.loc[PO.isna()]).index)
    for f in range(len(df_flags)):
        if f < n_cel:
            unknown.append(f)
        elif re.search('9|4', df_flags['flag'].iloc[f]):
            unknown.append(f)
            if f < len(df_flags) - n_cel:
                unknown.append(f + n_cel)
    unknown = [i for i in unknown if i not in missing]
    bad = [i for i in bad if i not in missing]
    bad = [i for i in bad if i not in unknown]
    suspect = [i for i in suspect if i not in missing]
    suspect = [i for i in suspect if i not in unknown]
    suspect = [i for i in suspect if i not in bad]
    df_flags.iloc[unknown]+='%d'%QC_flags.UNKNOWN
    df_flags.iloc[missing]+='%d'%QC_flags.MISSING
    df_flags.iloc[bad]+='%d'%QC_flags.BAD_DATA
    df_flags.iloc[suspect]+='%d'%QC_flags.SUSPECT
    df_flags.iloc[~df_flags.index.isin(list(dict.fromkeys(unknown+missing+bad+suspect)))]+='%d'%QC_flags.GOOD_DATA
    return list(df_flags['flag'])

def single_flat_line_test (n_samples, n_cel, data, flags, rep_cnt_fail, rep_cnt_suspect, eps):
    indice = np.arange(0, n_samples)
    for n in range(n_cel):
        bin_n = np.asarray(data)[n::n_cel]
        i_bin = indice[n::n_cel]
        for i in range(len(i_bin)):
            sub = np.abs(bin_n[i] - bin_n[i-rep_cnt_fail:i])
            sub = sub[::-1]
            i_linha = i_bin[i]
            if bin_n[i] == -9 or np.isnan(bin_n[i]):
                flags[i_linha]+='%d'%QC_flags.MISSING
            elif i_linha <(n_cel * rep_cnt_fail) or any(np.isnan(sub)):
                flags[i_linha]+='%d'%QC_flags.UNKNOWN
            elif all(sub[0:rep_cnt_fail] <= eps):
                flags[i_linha]+='%d'%QC_flags.BAD_DATA
            elif all(sub[0:rep_cnt_suspect] <= eps) and not(all(sub[0:rep_cnt_fail] <= eps)):
                flags[i_linha]+='%d'%QC_flags.SUSPECT
            elif any(sub[0:rep_cnt_suspect] > eps):
                flags[i_linha]+='%d'%QC_flags.GOOD_DATA
    return flags

def vertical_gradient_test(n_samples, PO, n_cel, flags, ms_interval, time_window, rc_fail, rc_susp, DIR):
    ms_interval = float(re.search('\d{1,}', ms_interval).group())
    if re.search('D', time_window, re.IGNORECASE):
        ms_interval = ms_interval/86400
    elif re.search('H', time_window, re.IGNORECASE):
        ms_interval = ms_interval/3600
    elif re.search('M', time_window, re.IGNORECASE):
        ms_interval = ms_interval/60
    elif re.search('S', time_window, re.IGNORECASE):
        pass
    n_samples = (int(int(re.search('\d{1,}', time_window).group())/ ms_interval)) * n_cel
    index = np.arange(n_samples)
    df_flags = pd.DataFrame({'flag': flags})
    PO = PO.copy()
    PO = PO.replace(-9, np.nan)
    bad, suspect, unknown, missing = ([],[],[],[])
    if DIR == False:
        std = PO.rolling(n_samples).std()
        PO_reverse = PO[::-1]
        std_reverse = PO_reverse.rolling(n_samples).std()
        std[:n_samples-1] = std_reverse[::-1][:n_samples-1]
        std = pd.DataFrame({'sigma':std})
    elif DIR == True:
        from scipy import stats
        std = []
        for i in range(len(PO)):
            if i < n_samples:
                std.append((stats.circstd(PO.iloc[i:i+n_samples])*180)/np.pi)
            elif i >= n_samples:
                std.append((stats.circstd(PO.iloc[i-n_samples:i])*180)/np.pi)
        std = pd.DataFrame({'sigma':std})
        std.index = index
    RC = PO.diff().abs() if DIR==False else np.abs((PO.diff() + 180 + 360) % 360 - 180)
    bad += list((PO.loc[RC >= rc_fail * std.sigma]).index) if DIR==False else list((PO.loc[RC >= rc_fail * std.sigma]).index)
    suspect += list((PO.loc[(rc_susp * std.sigma <= RC) & (RC < rc_fail * std.sigma)]).index) if DIR==False else list((PO.loc[(rc_susp * std.sigma <= RC) & (RC < rc_fail * std.sigma)]).index)
    missing += list((PO.loc[PO.isna()]).index)
    unknown = [0]
    unknown = [i for i in unknown if i not in missing]
    bad = [i for i in bad if i not in missing]
    bad = [i for i in bad if i not in unknown]
    suspect = [i for i in suspect if i not in missing]
    suspect = [i for i in suspect if i not in unknown]
    suspect = [i for i in suspect if i not in bad]
    df_flags.iloc[unknown]+='%d'%QC_flags.UNKNOWN
    df_flags.iloc[missing]+='%d'%QC_flags.MISSING
    df_flags.iloc[bad]+='%d'%QC_flags.BAD_DATA
    df_flags.iloc[suspect]+='%d'%QC_flags.SUSPECT
    df_flags.iloc[~df_flags.index.isin(list(dict.fromkeys(unknown+missing+bad+suspect)))]+='%d'%QC_flags.GOOD_DATA
    flags = list(df_flags['flag'])
    return flags

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
    """Converte a janela de tempo ('2D'/'3H'/'30M'/'45S'/'WHOLE') em numero de
    amostras. Retorna n_total para 'WHOLE' ou formato nao reconhecido."""
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


# minimo de amostras para estimar um sigma local estavel: com menos que isso o
# MAD degenera (ex.: 3 pontos -> sigma ~0 e ruido vira reprovacao em massa)
MIN_SIGMA_SAMPLES = 11


def robust_rolling_sigma(pop, win):
    """Sigma robusto (1.4826 x MAD) rolante, usado como referencia de limiar nos
    testes de spike e rate-of-change: nao e inflado pelos proprios outliers que
    os testes procuram. Onde o MAD e 0 (dados quase constantes) recai no desvio
    padrao rolante para nao reprovar ruido de resolucao. Janela menor que
    MIN_SIGMA_SAMPLES ou maior que a serie -> valor global constante."""
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
    # spike/limiar NaN => sem vizinhos validos ou sigma indeterminado: nao avaliavel
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
    # fail_flag: BAD_DATA para faixa do sensor (fisicamente impossivel);
    # SUSPECT para faixa ambiental/climatologica (QARTOD: valores fora do
    # envelope regional sao suspeitos, nao necessariamente ruins)
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
    # QARTOD rate-of-change test: |V_n - V_(n-1)| comparado a fator x sigma local.
    # Alinhado ao QARTOD, o excedente e marcado como SUSPECT (3), nunca BAD:
    # variacoes rapidas reais (frentes, ressurgencia) existem.
    # var_positions: posicoes da string de flags que pertencem a ESTA variavel;
    # usadas para propagar 'nao avaliavel' quando o valor anterior desta variavel
    # ja foi reprovado/faltante (sem elas, flags de outras variaveis contaminariam).
    interval_s = ms_interval.item().total_seconds()
    n_samples = parse_time_window_samples(time_window, interval_s, n_lines)
    if n_samples < MIN_SIGMA_SAMPLES:
        # janela pequena demais nao estima sigma local estavel; antes disso o
        # teste virava um no-op silencioso (sigma NaN -> nada reprovado)
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
        # QARTOD: rate-of-change so gera SUSPECT; os dois fatores viram niveis
        # do mesmo flag (>= susp ja e suspeito)
        suspect += list((PO.loc[RC >= rc_susp * std.sigma]).index)
        missing += list((PO.loc[PO.isna()]).index)
        # valor anterior faltante -> diff nao avaliavel (independe de flags previas)
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
    # Flat line test (QARTOD): rep_cnt observacoes consecutivas que nao diferem
    # mais que eps => sensor travado. NaNs esporadicos NAO interrompem a
    # contagem (um sensor travado que emite NaNs ocasionais continua detectavel):
    # a sequencia e avaliada sobre os valores validos. Vetorizado (O(n)).
    eps = get_eps(data)
    v = np.asarray(data, dtype=float)
    missing_mask = np.isnan(v) | (v == -9)  # -9: sentinela legada de faltante
    out_char = np.full(n_samples, '%d' % QC_flags.GOOD_DATA, dtype='<U1')
    out_char[missing_mask] = '%d' % QC_flags.MISSING

    valid_idx = np.where(~missing_mask)[0]
    vv = v[valid_idx]
    if len(vv) > 0:
        # comprimento da sequencia "plana" terminando em cada amostra valida
        same = np.abs(np.diff(vv)) <= eps
        starts = np.r_[True, ~same]
        pos = np.arange(len(vv))
        start_idx = np.maximum.accumulate(np.where(starts, pos, 0))
        run = pos - start_idx + 1
        # sequencia plana que encosta no inicio dos dados e ainda nao atingiu
        # rep_cnt_fail: pode ser continuacao de um trecho anterior -> nao avaliavel
        unknown_mask = (start_idx == 0) & (run == pos + 1) & (pos + 1 < rep_cnt_fail)
        char_vv = np.where(run >= rep_cnt_fail, '%d' % QC_flags.BAD_DATA,
                   np.where(run >= rep_cnt_suspect, '%d' % QC_flags.SUSPECT,
                   np.where(unknown_mask, '%d' % QC_flags.UNKNOWN,
                            '%d' % QC_flags.GOOD_DATA)))
        out_char[valid_idx] = char_vv

    return [flags[i] + out_char[i] for i in range(n_samples)]


def vertical_gradient_test(values, depth, flags, grad_fail, grad_susp, min_dz=0.05):
    # Teste de gradiente vertical (perfis): |dV/dz| entre amostras consecutivas,
    # comparado a limiares relativos (fator x sigma robusto dos gradientes do
    # perfil). Usa a profundidade real (dV/dz), nao a sequencia temporal.
    # - valor NaN -> MISSING
    # - primeiro ponto, vizinho de NaN ou |dz| < min_dz (parado na mesma
    #   profundidade) -> UNKNOWN (gradiente indeterminado)
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

    # o desvio e medido em relacao ao gradiente TIPICO do perfil (mediana):
    # um perfil estratificado tem gradiente de fundo diferente de zero, e o
    # teste procura desvios anomalos desse comportamento, nao o gradiente em si
    valid_grads = grad[computable]
    if len(valid_grads) >= 4:
        med = np.nanmedian(valid_grads)
        sigma = 1.4826 * np.nanmedian(np.abs(valid_grads - med))
        if not np.isfinite(sigma) or sigma <= 0:
            sigma = np.nanstd(valid_grads)
    else:
        med, sigma = np.nan, np.nan  # gradientes insuficientes: nao avaliavel

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

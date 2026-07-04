# Teste rapido das funcoes de qualificacao (nao testa a interface grafica)
import matplotlib
matplotlib.use('Agg')
import numpy as np
import pandas as pd

import QCS_Tests as QC
import QCS_DataHandler as data

# flag layouts (param key per flag position), matching the test sequence order
MOORING_LAYOUT = (['T', 'S', 'C', 'P', 'O2', 'pH', 'chl', 'tur'] +          # sensor range
                  ['T', 'S', 'C', 'P', 'pH', 'chl', 'O2', 'org', 'tur'] +   # env range
                  ['T', 'S', 'C', 'P', 'pH', 'chl', 'O2', 'org', 'tur'] +   # spikes
                  ['T', 'S', 'C', 'P'] +                                    # rate of change
                  ['T', 'S', 'C', 'P'])                                     # flat line
PROFILE_LAYOUT = MOORING_LAYOUT + ['T', 'S', 'C'] + ['dens']  # + gradiente vertical + inversao

def flag_with(layout, target, code):
    # builds a flag string of len(layout) with 'code' at every position that maps
    # to 'target' and '1' elsewhere (robust to layout/order changes)
    return ''.join(code if k == target else '1' for k in layout)

ok = []

# 1) range_test: faixa de sensor reprova como BAD (4)
s = pd.Series([20.0, 21.0, 50.0, np.nan, 22.0])
flags = QC.range_test(s, ['' for _ in range(5)], range_min=15, range_max=35)
assert flags == ['1', '1', '4', '9', '1'], flags
ok.append('range_test (sensor -> BAD)')

# 1b) faixa ambiental marca SUSPECT (3), alinhado ao QARTOD (climatologia)
flags = QC.range_test(s, ['' for _ in range(5)], range_min=15, range_max=35,
                      fail_flag=QC.QC_flags.SUSPECT)
assert flags == ['1', '1', '3', '9', '1'], flags
ok.append('range_test (ambiental -> SUSPECT)')

# 2) outlier_test (spike de 3 pontos): reprova spike e nao reprova mudanca de regime
n = 50
vals = np.full(n, 25.0) + np.random.default_rng(0).normal(0, 0.01, n)
vals[25] = 40.0  # spike forte
df = pd.DataFrame({'Datetime': pd.date_range('2026-01-01', periods=n, freq='min'),
                   'Temperature (degC)': vals})
flags = QC.outlier_test(df, 'Temperature (degC)', 1, ['' for _ in range(n)],
                        'WHOLE', np.timedelta64(60, 's'), 3, 2.5)
assert len(flags) == n and all(len(f) == 1 for f in flags), flags
assert flags[25] == '4', 'spike forte deveria ser reprovado'
ok.append('outlier_test (spike detectado)')

# 2b) degrau/frente (mudanca de regime sustentada) NAO deve ser reprovado como spike
step = np.concatenate([np.full(40, 20.0), np.full(40, 26.0)]) + np.random.default_rng(1).normal(0, 0.02, 80)
df2 = pd.DataFrame({'Datetime': pd.date_range('2026-01-01', periods=80, freq='min'),
                    'Temperature (degC)': step})
flags2 = QC.outlier_test(df2, 'Temperature (degC)', 1, ['' for _ in range(80)],
                         'WHOLE', np.timedelta64(60, 's'), 3, 2.5)
# no maximo 1 ponto na transicao pode ser marcado; um spike-test ruim reprovaria varios
assert flags2.count('4') <= 1, 'mudanca de regime nao deveria ser reprovada em massa: %d' % flags2.count('4')
ok.append('outlier_test (degrau preservado)')

# 2c) endpoints nao tem vizinhos: flag 2 (nao avaliado), nunca 1
assert flags[0] == '2' and flags[-1] == '2', (flags[0], flags[-1])
ok.append('outlier_test (endpoints nao avaliados)')

# 3) single_flat_line_test
vals = list(np.arange(30, dtype=float)) + [7.7] * 25
flags = QC.single_flat_line_test(len(vals), 1, pd.Series(vals), ['' for _ in vals],
                                 rep_cnt_fail=20, rep_cnt_suspect=15)
assert flags[-1] == '4', flags[-1]
ok.append('single_flat_line_test')

# 3b) NaNs esporadicos NAO escondem um sensor travado (contagem pula os NaNs)
vals = [7.7] * 35
vals[10] = np.nan
vals[20] = np.nan
flags = QC.single_flat_line_test(len(vals), 1, pd.Series(vals), ['' for _ in vals],
                                 rep_cnt_fail=20, rep_cnt_suspect=15)
assert flags[10] == '9', flags[10]
assert flags[-1] == '4', 'sensor travado com NaNs esporadicos deveria ser detectado: %s' % flags[-1]
ok.append('single_flat_line_test (travado com NaNs)')

# 4) sigma_rate_of_change_test: salto marcado como SUSPECT (QARTOD), nao BAD
vals = np.sin(np.linspace(0, 6, 100)) * 2 + 25
vals[50] += 8
flags = QC.sigma_rate_of_change_test(100, pd.Series(vals), 1, ['' for _ in range(100)],
                                     np.timedelta64(60, 's'), '30M', 3, 2.5, DIR=False)
assert len(flags) == 100 and all(len(f) == 1 for f in flags)
assert '4' not in flags, 'rate of change nunca deve gerar BAD (QARTOD: suspeito)'
assert flags[50] == '3', 'salto deveria ser SUSPECT: %s' % flags[50]
ok.append('sigma_rate_of_change_test (salto -> SUSPECT)')

# 4b) flags previas de OUTRA variavel nao contaminam o rate-of-change
n = 30
vals = pd.Series(25 + np.random.default_rng(0).normal(0, 0.01, n))
clean = ['1' for _ in range(n)]
dirty = list(clean)
dirty[15] = '4'  # flag BAD vinda de um teste de outra variavel (posicao 0)
f_iso = QC.sigma_rate_of_change_test(n, vals.copy(), 1, list(dirty),
                                     np.timedelta64(60, 's'), '10M', 3, 2.5,
                                     DIR=False, var_positions=[])
assert f_iso[15][-1] != '2', 'flag de outra variavel nao pode virar "nao avaliado"'
f_own = QC.sigma_rate_of_change_test(n, vals.copy(), 1, list(dirty),
                                     np.timedelta64(60, 's'), '10M', 3, 2.5,
                                     DIR=False, var_positions=[0])
assert f_own[15][-1] == '2' and f_own[16][-1] == '2', 'flag da PROPRIA variavel deve propagar 2'
ok.append('sigma_rate_of_change_test (sem contaminacao entre variaveis)')

# 4c) janela menor que o intervalo de amostragem: usa sigma da serie inteira
# (antes virava um no-op silencioso que nunca reprovava nada)
n = 200
vals = 25 + np.random.default_rng(0).normal(0, 0.01, n)
vals[100] = 40.0
flags = QC.sigma_rate_of_change_test(n, pd.Series(vals), 1, ['1' for _ in range(n)],
                                     np.timedelta64(3600, 's'), '30M', 3, 2.5, DIR=False)
assert flags[100][-1] == '3', 'salto em dado horario com janela 30M deveria ser SUSPECT: %s' % flags[100][-1]
ok.append('sigma_rate_of_change_test (janela < intervalo nao vira no-op)')

# 5) vertical_gradient_test usa a profundidade real (dV/dz)
m = 50
z = np.arange(1, m + 1, dtype=float)
v = 25 - 0.5 * z + np.random.default_rng(7).normal(0, 0.01, m)  # estratificacao uniforme
fg = QC.vertical_gradient_test(pd.Series(v), pd.Series(z), ['' for _ in range(m)], 4, 3)
assert all(len(x) == 1 for x in fg)
assert '4' not in fg, 'perfil estratificado uniforme nao deveria ter gradiente reprovado'
v2 = v.copy()
v2[25] += 3.0  # anomalia local: gradiente ~200x o tipico
fg2 = QC.vertical_gradient_test(pd.Series(v2), pd.Series(z), ['' for _ in range(m)], 4, 3)
assert fg2[25] == '4' or fg2[26] == '4', 'gradiente anomalo deveria ser reprovado'
ok.append('vertical_gradient_test (dV/dz, anomalia detectada)')

# 5b) density_inversion_test (perfis): detecta inversao e preserva coluna estavel
m = 10
depth = np.arange(1, m + 1, dtype=float)
sal = np.full(m, 35.0)
temp_stable = np.linspace(25, 16, m)      # esfria com a profundidade -> densidade cresce
dfp = pd.DataFrame({'Temperature (degC)': temp_stable, 'Salinity (PSU)': sal,
                    'Pressure (dbar)': depth.copy(), 'Depth (m)': depth})
fdi = QC.density_inversion_test(dfp, ['' for _ in range(m)], 0.03, -23.0, -40.0)
assert all(len(x) == 1 for x in fdi)
assert '3' not in fdi, 'coluna estavel nao deveria ter inversao'
temp_inv = temp_stable.copy()
temp_inv[5] = 30.0                         # ponto fundo anomalamente quente -> leve -> inversao
dfp['Temperature (degC)'] = temp_inv
fdi2 = QC.density_inversion_test(dfp, ['' for _ in range(m)], 0.03, -23.0, -40.0)
assert fdi2[5] == '3', 'inversao de densidade deveria ser marcada como suspeito'
ok.append('density_inversion_test')

# 5c) light_fouling_baseline: incrustacao da luz (janela de uso do HOBO)
# 5c-i) decaimento PERMANENTE: limpo 10 dias, cai e fica baixo -> corte, sem recuperacao
decay_perm = [1.0]*10 + [0.8, 0.6, 0.45, 0.4] + [0.3]*16
dt = pd.date_range('2026-01-01', periods=30*24, freq='h')
lux = [10000.0 * decay_perm[(ts - dt[0]).days] if 8 <= ts.hour <= 16 else 0.0 for ts in dt]
res = QC.light_fouling_baseline(dt, lux, baseline_days=7, cutoff_frac=0.5, sustain_days=3)
assert res['evaluable'] is True
assert res['baseline'] == 10000.0, res['baseline']
assert res['proposed_cutoff'].date() == pd.Timestamp('2026-01-13').date(), res['proposed_cutoff']
assert res['recovers'] is False, 'decaimento permanente nao deveria acusar recuperacao'
ok.append('light_fouling_baseline (decaimento permanente -> corte firme)')

# 5c-ii) decaimento com RECUPERACAO (luz volta apos o corte) -> AVISO
decay_rec = [1.0]*10 + [0.8, 0.6, 0.45, 0.4] + [0.3]*6 + [0.9]*10
lux_rec = [10000.0 * decay_rec[(ts - dt[0]).days] if 8 <= ts.hour <= 16 else 0.0 for ts in dt]
res_rec = QC.light_fouling_baseline(dt, lux_rec, baseline_days=7, cutoff_frac=0.5, sustain_days=3)
assert res_rec['proposed_cutoff'] is not None
assert res_rec['recovers'] is True, 'recuperacao pos-corte deveria ser sinalizada'
assert any('NOT permanent' in w for w in res_rec['warnings']), res_rec['warnings']
ok.append('light_fouling_baseline (recuperacao -> aviso)')

# 5d) apply_light_window: 1 antes / 3 depois do corte, 9 p/ NaN, 2 se nao avaliavel
lux_nan = list(lux)
lux_nan[100] = np.nan
fl = QC.apply_light_window(dt, lux_nan, ['' for _ in dt], res['proposed_cutoff'])
assert fl[24] == '1', 'dia 1 (agua limpa) deveria ser bom: %s' % fl[24]
assert fl[100] == '9'
assert fl[-1] == '3', 'apos o corte deveria ser suspeito: %s' % fl[-1]
fl2 = QC.apply_light_window(dt[:48], lux[:48], ['' for _ in range(48)], None, evaluable=False)
assert set(fl2) <= {'2', '9'}, 'serie nao avaliavel deveria ser 2/9'
short = QC.light_fouling_baseline(dt[:5*24], lux[:5*24], baseline_days=7, cutoff_frac=0.5, sustain_days=3)
assert short['evaluable'] is False, 'serie curta demais nao pode estabelecer baseline'
ok.append('apply_light_window (flags e serie curta)')

# 6) pressure_to_depth: 110 dbar - 10.1325 atm = ~99.9 dbar -> ~99 m (e nao usar lat/5.29)
df = pd.DataFrame({'Pressure (dbar)': [110.0]})
df = data.pressure_to_depth(df, latitude=17.5, adjust_for_atm=True)
depth = df['Depth (m)'].iloc[0]
assert 98.5 < depth < 100.0, depth
ok.append('pressure_to_depth (%.2f m para 100 dbar)' % depth)

# 6b) clean_below_zero: optica mantem pequeno negativo como 0, descarta negativo grande;
# variavel nao-optica mantem <=0 -> NaN; contagens reportadas ao chamador
sett = {'env_min_chl': 0, 'env_max_chl': 30, 'env_min_tur': 0, 'env_max_tur': 50,
        'env_min_org': 0, 'env_max_org': 50}
dfz = pd.DataFrame({'Datetime': pd.date_range('2026-01-01', periods=3, freq='min'),
                    'Chlorophyll (ug/L)': [0.5, -0.2, -10.0],
                    'PAR (umol/m2/s)': [800.0, -0.01, 0.0],
                    'Temperature (degC)': [25.0, -1.0, 26.0]})
outz, zrep = data.clean_below_zero(dfz.copy(), sett)
assert outz['Chlorophyll (ug/L)'].iloc[0] == 0.5
assert outz['Chlorophyll (ug/L)'].iloc[1] == 0.0, 'pequeno negativo deveria virar 0'
assert np.isnan(outz['Chlorophyll (ug/L)'].iloc[2]), 'negativo grande deveria virar NaN'
assert outz['PAR (umol/m2/s)'].iloc[1] == 0.0, 'PAR negativo (noite) deveria virar 0, nao NaN'
assert not outz['PAR (umol/m2/s)'].isna().any(), 'PAR nao deveria ter NaN'
assert np.isnan(outz['Temperature (degC)'].iloc[1]), 'nao-optica <=0 deveria virar NaN'
assert zrep['Chlorophyll (ug/L)'] == {'clamped': 1, 'discarded': 1}, zrep
assert zrep['Temperature (degC)'] == {'clamped': 0, 'discarded': 1}, zrep
ok.append('clean_below_zero (opticas + PAR + contagens)')

# 6c) luz do HOBO: zero a noite e VALIDO (nunca vira NaN); negativo vira 0
dfl = pd.DataFrame({'Datetime': pd.date_range('2026-01-01', periods=3, freq='h'),
                    'Luminosity (lux)': [12000.0, 0.0, -1.2]})
outl, lrep = data.clean_below_zero(dfl.copy(), sett)
assert outl['Luminosity (lux)'].iloc[1] == 0.0, 'lux=0 (noite) deveria ser mantido'
assert outl['Luminosity (lux)'].iloc[2] == 0.0, 'lux negativo deveria virar 0'
assert not outl['Luminosity (lux)'].isna().any()
ok.append('clean_below_zero (lux noturno preservado)')

# 7) handle_output_file: flag de pH nao pode apagar clorofila
n = 3
df = pd.DataFrame({'Datetime': pd.date_range('2026-01-01', periods=n, freq='min'),
                   'Temperature (degC)': [25.0, 25.1, 25.2],
                   'pH': [8.1, 8.2, 8.3],
                   'Chlorophyll (ug/L)': [1.0, 2.0, 3.0]})
flags = ['1' * len(MOORING_LAYOUT),
         flag_with(MOORING_LAYOUT, 'pH', '4'),   # pH ruim em todas as posicoes de pH
         '1' * len(MOORING_LAYOUT)]
out = data.handle_output_file(df, flags, MOORING_LAYOUT, remove_suspect=False, remove_bad=True)
output_df = out[0]
assert np.isnan(output_df['pH'].iloc[1]), 'pH ruim deveria virar NaN'
assert output_df['Chlorophyll (ug/L)'].iloc[1] == 2.0, 'clorofila nao podia ser apagada por flag de pH'
ok.append('handle_output_file (pH/clorofila)')

# 7b) colunas Flag_ por variavel: pior flag daquela variavel na linha
assert output_df['Flag_pH'].iloc[1] == 4, output_df['Flag_pH'].tolist()
assert output_df['Flag_pH'].iloc[0] == 1
assert output_df['Flag_chl'].iloc[1] == 1, 'flag de pH nao pode contaminar Flag_chl'
assert output_df['Flag_T'].iloc[1] == 1
assert 'Flag_lux' not in output_df.columns, 'Flag_lux so deve existir em arquivos HOBO'
ok.append('handle_output_file (colunas Flag_ por variavel)')

# 7c) layout HOBO (com posicao 'lux'): Flag_lux criada; remove_suspect apaga a luz
HOBO_LAYOUT = MOORING_LAYOUT + ['lux']
dfh = pd.DataFrame({'Datetime': pd.date_range('2026-01-01', periods=3, freq='h'),
                    'Temperature (degC)': [25.0, 25.1, 25.2],
                    'Luminosity (lux)': [10000.0, 8000.0, 500.0]})
flags_h = ['1' * len(HOBO_LAYOUT),
           '1' * len(HOBO_LAYOUT),
           flag_with(HOBO_LAYOUT, 'lux', '3')]  # ultima linha: luz suspeita (incrustada)
outh = data.handle_output_file(dfh, flags_h, HOBO_LAYOUT, remove_suspect=True, remove_bad=False)
outh_df = outh[0]
assert list(outh_df['Flag_lux']) == [1, 1, 3], outh_df['Flag_lux'].tolist()
assert np.isnan(outh_df['Luminosity (lux)'].iloc[2]), 'remove_suspect deveria apagar a luz incrustada'
assert outh_df['Luminosity (lux)'].iloc[0] == 10000.0
assert outh_df['Temperature (degC)'].iloc[2] == 25.2, 'flag de luz nao pode afetar temperatura'
ok.append('handle_output_file (Flag_lux + remocao da luz suspeita)')

# 8) deduplicacao de indices com varios repetidos (antes quebrava/falhava)
L = len(MOORING_LAYOUT)
flags = ['4' * L, '4' * L, '3' * L]  # 2 linhas ruins repetidas em varios testes
out = data.handle_output_file(df, flags, MOORING_LAYOUT, remove_suspect=True, remove_bad=True)
output_df = out[0]
assert np.isnan(output_df['Temperature (degC)'].iloc[0])
assert np.isnan(output_df['Temperature (degC)'].iloc[2])
ok.append('handle_output_file (deduplicacao)')

# 8b) flag na ultima posicao (inversao de densidade, perfis) reprova T e S
n = 2
dfd = pd.DataFrame({'Datetime': pd.date_range('2026-01-01', periods=n, freq='min'),
                    'Temperature (degC)': [25.0, 26.0],
                    'Salinity (PSU)': [36.0, 36.5]})
flags = ['1' * len(PROFILE_LAYOUT),
         flag_with(PROFILE_LAYOUT, 'dens', '4')]  # linha 1 com inversao de densidade
out = data.handle_output_file(dfd, flags, PROFILE_LAYOUT, remove_suspect=False, remove_bad=True)
outdf = out[0]
assert np.isnan(outdf['Temperature (degC)'].iloc[1]) and np.isnan(outdf['Salinity (PSU)'].iloc[1]), 'inversao deveria reprovar T e S'
assert not np.isnan(outdf['Temperature (degC)'].iloc[0]), 'linha estavel nao podia ser afetada'
ok.append('handle_output_file (inversao de densidade na ultima posicao)')

# 9) tscp_stats_table com apenas parte das variaveis
qd = pd.DataFrame({'Temperature (degC)': [25.0, 26.0],
                   'Salinity (PSU)': [36.0, 36.5],
                   'Pressure (dbar)': [np.nan, np.nan]})
stat = data.tscp_stats_table(qd)
assert list(stat['Variable']) == ['Temperature (degC)', 'Salinity (PSU)'], stat
ok.append('tscp_stats_table (variaveis parciais)')

# 9b) order_var 'hobo': so temperatura + luz + metadados; sem colunas TSCP
qh = pd.DataFrame({'Sample number': [1, 2], 'Datetime': pd.date_range('2026-01-01', periods=2, freq='h'),
                   'Temperature (degC)': [25.0, 25.1], 'Luminosity (lux)': [10000.0, 8000.0],
                   'Salinity (PSU)': [36.0, 36.1], 'Depth (m)': [5.0, 5.0],  # nao devem sair
                   'Site': ['PAB3', 'PAB3'], 'Latitude': [-17.5, -17.5], 'Longitude': [-40.0, -40.0],
                   'Flag': ['11', '13'], 'Flag_T': [1, 1], 'Flag_lux': [1, 3], 'QCS version': ['v4.0', 'v4.0']})
oh = data.order_var(qh.copy(), 1, data_type='hobo')
cols = list(oh.columns)
assert 'Salinity (PSU)' not in cols and 'Depth (m)' not in cols, 'variaveis TSCP nao devem aparecer no HOBO: %s' % cols
assert 'Temperature (degC)' in cols and 'Luminosity (lux)' in cols
assert cols[:4] == ['Sample number', 'Datetime', 'Temperature (degC)', 'Luminosity (lux)'], cols
for meta in ('Site', 'Latitude', 'Longitude', 'Flag', 'Flag_T', 'Flag_lux', 'QCS version'):
    assert meta in cols, 'metadado %s faltando no HOBO' % meta
assert oh['Site'].iloc[0] == 'PAB3'
ok.append('order_var hobo (so temp+luz+metadados)')

# 9c) Lat/Long sao opcionais: ausentes na entrada -> NAO criadas vazias na saida
qh2 = qh.drop(columns=['Latitude', 'Longitude'])
oh2 = data.order_var(qh2.copy(), 1, data_type='hobo')
assert 'Latitude' not in oh2.columns and 'Longitude' not in oh2.columns, list(oh2.columns)
qt2 = pd.DataFrame({'Datetime': pd.date_range('2026-01-01', periods=2, freq='h'),
                    'Temperature (degC)': [25.0, 25.1], 'Site': ['D13', 'D13']})
ot2 = data.order_var(qt2.copy(), 1, data_type='tscp')
assert 'Latitude' not in ot2.columns and 'Longitude' not in ot2.columns, 'tscp nao deve criar lat/long vazias'
ok.append('order_var (Lat/Long opcionais, nao criadas vazias)')

# 10) order_var com data_type invalido deve avisar com clareza
try:
    data.order_var(qd.copy(), 1, data_type='outro')
    raise AssertionError('deveria ter levantado ValueError')
except ValueError:
    ok.append('order_var (erro claro p/ tipo invalido)')

print('\n'.join('OK: ' + t for t in ok))
print('\n%d testes passaram.' % len(ok))

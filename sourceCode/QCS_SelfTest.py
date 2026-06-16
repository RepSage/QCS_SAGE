# Teste rapido das funcoes corrigidas (nao testa a interface grafica)
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

# 1) range_test
s = pd.Series([20.0, 21.0, 50.0, np.nan, 22.0])
flags = QC.range_test(s, ['' for _ in range(5)], range_min=15, range_max=35)
assert flags == ['1', '1', '4', '9', '1'], flags
ok.append('range_test')

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

# 3) single_flat_line_test
vals = list(np.arange(30, dtype=float)) + [7.7] * 25
flags = QC.single_flat_line_test(len(vals), 1, pd.Series(vals), ['' for _ in vals],
                                 rep_cnt_fail=20, rep_cnt_suspect=15)
assert flags[-1] == '4', flags[-1]
ok.append('single_flat_line_test')

# 4) sigma_rate_of_change_test
vals = np.sin(np.linspace(0, 6, 100)) * 2 + 25
vals[50] += 8
flags = QC.sigma_rate_of_change_test(100, pd.Series(vals), 1, ['' for _ in range(100)],
                                     np.timedelta64(60, 's'), '30M', 3, 2.5, DIR=False)
assert len(flags) == 100 and all(len(f) == 1 for f in flags)
ok.append('sigma_rate_of_change_test')

# 5) vertical_gradient_test com janela em dias (antes quebrava)
flags = QC.vertical_gradient_test(100, pd.Series(vals), 1, ['' for _ in range(100)],
                                  np.timedelta64(60, 's'), '1D', 3, 2.5, DIR=False)
assert len(flags) == 100
ok.append('vertical_gradient_test (janela 1D)')

# 5b) density_inversion_test (perfis): detecta inversao e preserva coluna estavel
m = 10
depth = np.arange(1, m + 1, dtype=float)
sal = np.full(m, 35.0)
temp_stable = np.linspace(25, 16, m)      # esfria com a profundidade -> densidade cresce
dfp = pd.DataFrame({'Temperature (degC)': temp_stable, 'Salinity (PSU)': sal,
                    'Pressure (dbar)': depth.copy(), 'Depth (m)': depth})
fdi = QC.density_inversion_test(dfp, ['' for _ in range(m)], 0.03, -23.0, -40.0)
assert all(len(x) == 1 for x in fdi)
assert '4' not in fdi, 'coluna estavel nao deveria ter inversao'
temp_inv = temp_stable.copy()
temp_inv[5] = 30.0                         # ponto fundo anomalamente quente -> leve -> inversao
dfp['Temperature (degC)'] = temp_inv
fdi2 = QC.density_inversion_test(dfp, ['' for _ in range(m)], 0.03, -23.0, -40.0)
assert fdi2[5] == '4', 'inversao de densidade nao detectada'
ok.append('density_inversion_test')

# 6) pressure_to_depth: 100 dbar a 17.5 graus deve dar ~99 m (e nao usar lat/5.29)
df = pd.DataFrame({'Pressure (dbar)': [110.0]})  # 110 - 10 atm = 100 dbar
df = data.pressure_to_depth(df, latitude=17.5, adjust_for_atm=True)
depth = df['Depth (m)'].iloc[0]
assert 98.5 < depth < 100.0, depth
ok.append('pressure_to_depth (%.2f m para 100 dbar)' % depth)

# 6b) clean_below_zero: optica mantem pequeno negativo como 0, descarta negativo grande;
# variavel nao-optica mantem <=0 -> NaN
sett = {'env_min_chl': 0, 'env_max_chl': 30, 'env_min_tur': 0, 'env_max_tur': 50,
        'env_min_org': 0, 'env_max_org': 50}
dfz = pd.DataFrame({'Datetime': pd.date_range('2026-01-01', periods=3, freq='min'),
                    'Chlorophyll (ug/L)': [0.5, -0.2, -10.0],
                    'Temperature (degC)': [25.0, -1.0, 26.0]})
outz = data.clean_below_zero(dfz.copy(), sett)
assert outz['Chlorophyll (ug/L)'].iloc[0] == 0.5
assert outz['Chlorophyll (ug/L)'].iloc[1] == 0.0, 'pequeno negativo deveria virar 0'
assert np.isnan(outz['Chlorophyll (ug/L)'].iloc[2]), 'negativo grande deveria virar NaN'
assert np.isnan(outz['Temperature (degC)'].iloc[1]), 'nao-optica <=0 deveria virar NaN'
ok.append('clean_below_zero (opticas)')

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

# 8) deduplicacao de indices com varios repetidos (antes quebrava/falhava)
L = len(MOORING_LAYOUT)
flags = ['4' * L, '4' * L, '3' * L]  # 2 linhas ruins repetidas em varios testes
out = data.handle_output_file(df, flags, MOORING_LAYOUT, remove_suspect=True, remove_bad=True)
output_df = out[0]
assert np.isnan(output_df['Temperature (degC)'].iloc[0])
assert np.isnan(output_df['Temperature (degC)'].iloc[2])
ok.append('handle_output_file (deduplicacao)')

# 8b) flag na posicao 33 (inversao de densidade, perfis) reprova T e S
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
ok.append('handle_output_file (inversao de densidade pos.33)')

# 9) tscp_stats_table com apenas parte das variaveis
qd = pd.DataFrame({'Temperature (degC)': [25.0, 26.0],
                   'Salinity (PSU)': [36.0, 36.5],
                   'Pressure (dbar)': [np.nan, np.nan]})
stat = data.tscp_stats_table(qd)
assert list(stat['Variable']) == ['Temperature (degC)', 'Salinity (PSU)'], stat
ok.append('tscp_stats_table (variaveis parciais)')

# 10) order_var com data_type invalido deve avisar com clareza
try:
    data.order_var(qd.copy(), 1, data_type='outro')
    raise AssertionError('deveria ter levantado ValueError')
except ValueError:
    ok.append('order_var (erro claro p/ tipo invalido)')

print('\n'.join('OK: ' + t for t in ok))
print('\n%d testes passaram.' % len(ok))

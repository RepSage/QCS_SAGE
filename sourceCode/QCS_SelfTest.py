# Quick test of the qualification functions (does not test the graphical interface)
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
PROFILE_LAYOUT = MOORING_LAYOUT + ['T', 'S', 'C'] + ['dens']  # + vertical gradient + inversion

def flag_with(layout, target, code):
    # builds a flag string of len(layout) with 'code' at every position that maps
    # to 'target' and '1' elsewhere (robust to layout/order changes)
    return ''.join(code if k == target else '1' for k in layout)

ok = []

# 1) range_test: sensor range fails as BAD (4)
s = pd.Series([20.0, 21.0, 50.0, np.nan, 22.0])
flags = QC.range_test(s, ['' for _ in range(5)], range_min=15, range_max=35)
assert flags == ['1', '1', '4', '9', '1'], flags
ok.append('range_test (sensor -> BAD)')

# 1b) environmental range flags SUSPECT (3), aligned with QARTOD (climatology)
flags = QC.range_test(s, ['' for _ in range(5)], range_min=15, range_max=35,
                      fail_flag=QC.QC_flags.SUSPECT)
assert flags == ['1', '1', '3', '9', '1'], flags
ok.append('range_test (environmental -> SUSPECT)')

# 2) outlier_test (3-point spike): fails the spike and does not fail a regime change
n = 50
vals = np.full(n, 25.0) + np.random.default_rng(0).normal(0, 0.01, n)
vals[25] = 40.0  # strong spike
df = pd.DataFrame({'Datetime': pd.date_range('2026-01-01', periods=n, freq='min'),
                   'Temperature (degC)': vals})
flags = QC.outlier_test(df, 'Temperature (degC)', 1, ['' for _ in range(n)],
                        'WHOLE', np.timedelta64(60, 's'), 3, 2.5)
assert len(flags) == n and all(len(f) == 1 for f in flags), flags
assert flags[25] == '4', 'strong spike should be failed'
ok.append('outlier_test (spike detected)')

# 2b) step/front (sustained regime change) should NOT be failed as a spike
step = np.concatenate([np.full(40, 20.0), np.full(40, 26.0)]) + np.random.default_rng(1).normal(0, 0.02, 80)
df2 = pd.DataFrame({'Datetime': pd.date_range('2026-01-01', periods=80, freq='min'),
                    'Temperature (degC)': step})
flags2 = QC.outlier_test(df2, 'Temperature (degC)', 1, ['' for _ in range(80)],
                         'WHOLE', np.timedelta64(60, 's'), 3, 2.5)
# at most 1 point at the transition may be marked; a bad spike-test would fail several
assert flags2.count('4') <= 1, 'regime change should not be failed en masse: %d' % flags2.count('4')
ok.append('outlier_test (step preserved)')

# 2c) endpoints have no neighbors: flag 2 (not evaluated), never 1
assert flags[0] == '2' and flags[-1] == '2', (flags[0], flags[-1])
ok.append('outlier_test (endpoints not evaluated)')

# 3) single_flat_line_test
vals = list(np.arange(30, dtype=float)) + [7.7] * 25
flags = QC.single_flat_line_test(len(vals), 1, pd.Series(vals), ['' for _ in vals],
                                 rep_cnt_fail=20, rep_cnt_suspect=15)
assert flags[-1] == '4', flags[-1]
ok.append('single_flat_line_test')

# 3b) sporadic NaNs do NOT hide a stuck sensor (the count skips the NaNs)
vals = [7.7] * 35
vals[10] = np.nan
vals[20] = np.nan
flags = QC.single_flat_line_test(len(vals), 1, pd.Series(vals), ['' for _ in vals],
                                 rep_cnt_fail=20, rep_cnt_suspect=15)
assert flags[10] == '9', flags[10]
assert flags[-1] == '4', 'stuck sensor with sporadic NaNs should be detected: %s' % flags[-1]
ok.append('single_flat_line_test (stuck with NaNs)')

# 4) sigma_rate_of_change_test: jump flagged as SUSPECT (QARTOD), not BAD
vals = np.sin(np.linspace(0, 6, 100)) * 2 + 25
vals[50] += 8
flags = QC.sigma_rate_of_change_test(100, pd.Series(vals), 1, ['' for _ in range(100)],
                                     np.timedelta64(60, 's'), '30M', 3, 2.5, DIR=False)
assert len(flags) == 100 and all(len(f) == 1 for f in flags)
assert '4' not in flags, 'rate of change must never produce BAD (QARTOD: suspect)'
assert flags[50] == '3', 'jump should be SUSPECT: %s' % flags[50]
ok.append('sigma_rate_of_change_test (jump -> SUSPECT)')

# 4b) prior flags from ANOTHER variable do not contaminate the rate-of-change
n = 30
vals = pd.Series(25 + np.random.default_rng(0).normal(0, 0.01, n))
clean = ['1' for _ in range(n)]
dirty = list(clean)
dirty[15] = '4'  # BAD flag coming from a test of another variable (position 0)
f_iso = QC.sigma_rate_of_change_test(n, vals.copy(), 1, list(dirty),
                                     np.timedelta64(60, 's'), '10M', 3, 2.5,
                                     DIR=False, var_positions=[])
assert f_iso[15][-1] != '2', 'flag from another variable must not become "not evaluated"'
f_own = QC.sigma_rate_of_change_test(n, vals.copy(), 1, list(dirty),
                                     np.timedelta64(60, 's'), '10M', 3, 2.5,
                                     DIR=False, var_positions=[0])
assert f_own[15][-1] == '2' and f_own[16][-1] == '2', 'flag from the OWN variable must propagate 2'
ok.append('sigma_rate_of_change_test (no contamination between variables)')

# 4c) window smaller than the sampling interval: uses sigma of the whole series
# (previously became a silent no-op that never failed anything)
n = 200
vals = 25 + np.random.default_rng(0).normal(0, 0.01, n)
vals[100] = 40.0
flags = QC.sigma_rate_of_change_test(n, pd.Series(vals), 1, ['1' for _ in range(n)],
                                     np.timedelta64(3600, 's'), '30M', 3, 2.5, DIR=False)
assert flags[100][-1] == '3', 'jump in hourly data with a 30M window should be SUSPECT: %s' % flags[100][-1]
ok.append('sigma_rate_of_change_test (window < interval does not become no-op)')

# 5) vertical_gradient_test uses the real depth (dV/dz)
m = 50
z = np.arange(1, m + 1, dtype=float)
v = 25 - 0.5 * z + np.random.default_rng(7).normal(0, 0.01, m)  # uniform stratification
fg = QC.vertical_gradient_test(pd.Series(v), pd.Series(z), ['' for _ in range(m)], 4, 3)
assert all(len(x) == 1 for x in fg)
assert '4' not in fg, 'a uniformly stratified profile should not have a failed gradient'
v2 = v.copy()
v2[25] += 3.0  # local anomaly: gradient ~200x the typical
fg2 = QC.vertical_gradient_test(pd.Series(v2), pd.Series(z), ['' for _ in range(m)], 4, 3)
assert fg2[25] == '4' or fg2[26] == '4', 'anomalous gradient should be failed'
ok.append('vertical_gradient_test (dV/dz, anomaly detected)')

# 5b) density_inversion_test (profiles): detects inversion and preserves a stable column
m = 10
depth = np.arange(1, m + 1, dtype=float)
sal = np.full(m, 35.0)
temp_stable = np.linspace(25, 16, m)      # cools with depth -> density increases
dfp = pd.DataFrame({'Temperature (degC)': temp_stable, 'Salinity (PSU)': sal,
                    'Pressure (dbar)': depth.copy(), 'Depth (m)': depth})
fdi = QC.density_inversion_test(dfp, ['' for _ in range(m)], 0.03, -23.0, -40.0)
assert all(len(x) == 1 for x in fdi)
assert '3' not in fdi, 'a stable column should not have an inversion'
temp_inv = temp_stable.copy()
temp_inv[5] = 30.0                         # anomalously warm bottom point -> light -> inversion
dfp['Temperature (degC)'] = temp_inv
fdi2 = QC.density_inversion_test(dfp, ['' for _ in range(m)], 0.03, -23.0, -40.0)
assert fdi2[5] == '3', 'density inversion should be flagged as suspect'
ok.append('density_inversion_test')

# 5c) light_fouling_baseline: light fouling (HOBO usage window)
# 5c-i) PERMANENT decay: clean for 10 days, drops and stays low -> cutoff, no recovery
decay_perm = [1.0]*10 + [0.8, 0.6, 0.45, 0.4] + [0.3]*16
dt = pd.date_range('2026-01-01', periods=30*24, freq='h')
lux = [10000.0 * decay_perm[(ts - dt[0]).days] if 8 <= ts.hour <= 16 else 0.0 for ts in dt]
res = QC.light_fouling_baseline(dt, lux, baseline_days=7, cutoff_frac=0.5, sustain_days=3)
assert res['evaluable'] is True
assert res['baseline'] == 10000.0, res['baseline']
assert res['proposed_cutoff'].date() == pd.Timestamp('2026-01-13').date(), res['proposed_cutoff']
assert res['recovers'] is False, 'permanent decay should not report recovery'
ok.append('light_fouling_baseline (permanent decay -> firm cutoff)')

# 5c-ii) light dips and RECOVERS to clean at the end: no permanent cutoff, but a
# non-monotonic WARNING is issued (possible cleaning / multiple deployments)
decay_rec = [1.0]*10 + [0.8, 0.6, 0.45, 0.4] + [0.3]*6 + [0.9]*10
lux_rec = [10000.0 * decay_rec[(ts - dt[0]).days] if 8 <= ts.hour <= 16 else 0.0 for ts in dt]
res_rec = QC.light_fouling_baseline(dt, lux_rec, baseline_days=7, cutoff_frac=0.5, sustain_days=3)
assert res_rec['proposed_cutoff'] is None, 'light that recovers to clean at the end should not be cut'
assert res_rec['recovers'] is True, 'a mid-series recovery should be signaled'
assert any('recovers above' in w for w in res_rec['warnings']), res_rec['warnings']
ok.append('light_fouling_baseline (recovery -> no cut + warning)')

# 5c-ii-bis) dips, RECOVERS, then declines PERMANENTLY: cut only at the final
# decline (the recovered points before it are kept, not flagged)
decay_rp = [1.0]*10 + [0.3]*3 + [0.9]*5 + [0.3]*12
lux_rp = [10000.0 * decay_rp[(ts - dt[0]).days] if 8 <= ts.hour <= 16 else 0.0 for ts in dt]
res_rp = QC.light_fouling_baseline(dt, lux_rp, baseline_days=7, cutoff_frac=0.5, sustain_days=3)
assert res_rp['proposed_cutoff'] is not None
assert res_rp['proposed_cutoff'].date() == pd.Timestamp('2026-01-19').date(), res_rp['proposed_cutoff']
assert res_rp['recovers'] is True
ok.append('light_fouling_baseline (recover then permanent -> cut at final decline)')

# 5d) apply_light_window: 1 before / 4 after the cutoff (BAD, fouled), 9 for NaN, 2 if not evaluable
lux_nan = list(lux)
lux_nan[100] = np.nan
fl = QC.apply_light_window(dt, lux_nan, ['' for _ in dt], res['proposed_cutoff'])
assert fl[24] == '1', 'day 1 (clean sensor) should be good: %s' % fl[24]
assert fl[100] == '9'
assert fl[-1] == '4', 'after the cutoff the fouled light should be BAD: %s' % fl[-1]
fl2 = QC.apply_light_window(dt[:48], lux[:48], ['' for _ in range(48)], None, evaluable=False)
assert set(fl2) <= {'2', '9'}, 'a non-evaluable series should be 2/9'
short = QC.light_fouling_baseline(dt[:5*24], lux[:5*24], baseline_days=7, cutoff_frac=0.5, sustain_days=3)
assert short['evaluable'] is False, 'a series that is too short cannot establish a baseline'
ok.append('apply_light_window (flags and short series)')

# 6) pressure_to_depth: 110 dbar - 10.1325 atm = ~99.9 dbar -> ~99 m (and not using lat/5.29)
df = pd.DataFrame({'Pressure (dbar)': [110.0]})
df = data.pressure_to_depth(df, latitude=17.5, adjust_for_atm=True)
depth = df['Depth (m)'].iloc[0]
assert 98.5 < depth < 100.0, depth
ok.append('pressure_to_depth (%.2f m for 100 dbar)' % depth)

# 6b) clean_below_zero: optical keeps small negative as 0, discards large negative;
# non-optical variable keeps <=0 -> NaN; counts reported to the caller
sett = {'env_min_chl': 0, 'env_max_chl': 30, 'env_min_tur': 0, 'env_max_tur': 50,
        'env_min_org': 0, 'env_max_org': 50}
dfz = pd.DataFrame({'Datetime': pd.date_range('2026-01-01', periods=3, freq='min'),
                    'Chlorophyll (ug/L)': [0.5, -0.2, -10.0],
                    'PAR (umol/m2/s)': [800.0, -0.01, 0.0],
                    'Temperature (degC)': [25.0, -1.0, 26.0]})
outz, zrep = data.clean_below_zero(dfz.copy(), sett)
assert outz['Chlorophyll (ug/L)'].iloc[0] == 0.5
assert outz['Chlorophyll (ug/L)'].iloc[1] == 0.0, 'small negative should become 0'
assert np.isnan(outz['Chlorophyll (ug/L)'].iloc[2]), 'large negative should become NaN'
assert outz['PAR (umol/m2/s)'].iloc[1] == 0.0, 'negative PAR (night) should become 0, not NaN'
assert not outz['PAR (umol/m2/s)'].isna().any(), 'PAR should not have NaN'
assert np.isnan(outz['Temperature (degC)'].iloc[1]), 'non-optical <=0 should become NaN'
assert zrep['Chlorophyll (ug/L)'] == {'clamped': 1, 'discarded': 1}, zrep
assert zrep['Temperature (degC)'] == {'clamped': 0, 'discarded': 1}, zrep
ok.append('clean_below_zero (optical + PAR + counts)')

# 6c) HOBO light: zero at night is VALID (never becomes NaN); negative becomes 0
dfl = pd.DataFrame({'Datetime': pd.date_range('2026-01-01', periods=3, freq='h'),
                    'Luminosity (lux)': [12000.0, 0.0, -1.2]})
outl, lrep = data.clean_below_zero(dfl.copy(), sett)
assert outl['Luminosity (lux)'].iloc[1] == 0.0, 'lux=0 (night) should be kept'
assert outl['Luminosity (lux)'].iloc[2] == 0.0, 'negative lux should become 0'
assert not outl['Luminosity (lux)'].isna().any()
ok.append('clean_below_zero (nighttime lux preserved)')

# 7) handle_output_file: a pH flag must not erase chlorophyll
n = 3
df = pd.DataFrame({'Datetime': pd.date_range('2026-01-01', periods=n, freq='min'),
                   'Temperature (degC)': [25.0, 25.1, 25.2],
                   'pH': [8.1, 8.2, 8.3],
                   'Chlorophyll (ug/L)': [1.0, 2.0, 3.0]})
flags = ['1' * len(MOORING_LAYOUT),
         flag_with(MOORING_LAYOUT, 'pH', '4'),   # bad pH at every pH position
         '1' * len(MOORING_LAYOUT)]
out = data.handle_output_file(df, flags, MOORING_LAYOUT, remove_suspect=False, remove_bad=True)
output_df = out[0]
assert np.isnan(output_df['pH'].iloc[1]), 'bad pH should become NaN'
assert output_df['Chlorophyll (ug/L)'].iloc[1] == 2.0, 'chlorophyll must not be erased by a pH flag'
ok.append('handle_output_file (pH/chlorophyll)')

# 7b) per-variable Flag_ columns: worst flag of that variable in the row
assert output_df['Flag_pH'].iloc[1] == 4, output_df['Flag_pH'].tolist()
assert output_df['Flag_pH'].iloc[0] == 1
assert output_df['Flag_chl'].iloc[1] == 1, 'a pH flag must not contaminate Flag_chl'
assert output_df['Flag_T'].iloc[1] == 1
assert 'Flag_lux' not in output_df.columns, 'Flag_lux should only exist in HOBO files'
ok.append('handle_output_file (per-variable Flag_ columns)')

# 7c) HOBO layout (with 'lux' position): Flag_lux created; remove_bad erases the fouled light
HOBO_LAYOUT = MOORING_LAYOUT + ['lux']
dfh = pd.DataFrame({'Datetime': pd.date_range('2026-01-01', periods=3, freq='h'),
                    'Temperature (degC)': [25.0, 25.1, 25.2],
                    'Luminosity (lux)': [10000.0, 8000.0, 500.0]})
flags_h = ['1' * len(HOBO_LAYOUT),
           '1' * len(HOBO_LAYOUT),
           flag_with(HOBO_LAYOUT, 'lux', '4')]  # last row: bad light (fouled)
outh = data.handle_output_file(dfh, flags_h, HOBO_LAYOUT, remove_suspect=False, remove_bad=True)
outh_df = outh[0]
assert list(outh_df['Flag_lux']) == [1, 1, 4], outh_df['Flag_lux'].tolist()
assert np.isnan(outh_df['Luminosity (lux)'].iloc[2]), 'remove_bad should erase the fouled light'
assert outh_df['Luminosity (lux)'].iloc[0] == 10000.0
assert outh_df['Temperature (degC)'].iloc[2] == 25.2, 'a light flag must not affect temperature'
ok.append('handle_output_file (Flag_lux + removal of bad fouled light)')

# 8) deduplication of indices with several repeats (previously broke/failed)
L = len(MOORING_LAYOUT)
flags = ['4' * L, '4' * L, '3' * L]  # 2 bad rows repeated across several tests
out = data.handle_output_file(df, flags, MOORING_LAYOUT, remove_suspect=True, remove_bad=True)
output_df = out[0]
assert np.isnan(output_df['Temperature (degC)'].iloc[0])
assert np.isnan(output_df['Temperature (degC)'].iloc[2])
ok.append('handle_output_file (deduplication)')

# 8b) flag at the last position (density inversion, profiles) fails T and S
n = 2
dfd = pd.DataFrame({'Datetime': pd.date_range('2026-01-01', periods=n, freq='min'),
                    'Temperature (degC)': [25.0, 26.0],
                    'Salinity (PSU)': [36.0, 36.5]})
flags = ['1' * len(PROFILE_LAYOUT),
         flag_with(PROFILE_LAYOUT, 'dens', '4')]  # row 1 with density inversion
out = data.handle_output_file(dfd, flags, PROFILE_LAYOUT, remove_suspect=False, remove_bad=True)
outdf = out[0]
assert np.isnan(outdf['Temperature (degC)'].iloc[1]) and np.isnan(outdf['Salinity (PSU)'].iloc[1]), 'inversion should fail T and S'
assert not np.isnan(outdf['Temperature (degC)'].iloc[0]), 'a stable row must not be affected'
ok.append('handle_output_file (density inversion at the last position)')

# 9) tscp_stats_table with only part of the variables
qd = pd.DataFrame({'Temperature (degC)': [25.0, 26.0],
                   'Salinity (PSU)': [36.0, 36.5],
                   'Pressure (dbar)': [np.nan, np.nan]})
stat = data.tscp_stats_table(qd)
assert list(stat['Variable']) == ['Temperature (degC)', 'Salinity (PSU)'], stat
ok.append('tscp_stats_table (partial variables)')

# 9b) order_var 'hobo': only temperature + light + metadata; no TSCP columns
qh = pd.DataFrame({'Sample number': [1, 2], 'Datetime': pd.date_range('2026-01-01', periods=2, freq='h'),
                   'Temperature (degC)': [25.0, 25.1], 'Luminosity (lux)': [10000.0, 8000.0],
                   'Salinity (PSU)': [36.0, 36.1], 'Depth (m)': [5.0, 5.0],  # should not appear
                   'Site': ['PAB3', 'PAB3'],
                   'Flag': ['11', '13'], 'Flag_T': [1, 1], 'Flag_lux': [1, 3], 'QCS version': ['v4.0', 'v4.0']})
oh = data.order_var(qh.copy(), 1, data_type='hobo')
cols = list(oh.columns)
assert 'Salinity (PSU)' not in cols and 'Depth (m)' not in cols, 'TSCP variables must not appear in HOBO: %s' % cols
assert 'Temperature (degC)' in cols and 'Luminosity (lux)' in cols
assert cols[:6] == ['Sample number', 'Datetime', 'Site', 'Temperature (degC)',
                    'Temperature spread (degC)', 'Luminosity (lux)'], cols
assert 'Expedition' not in cols, 'the Expedition (empty) column must no longer exist: %s' % cols
assert oh['Temperature spread (degC)'].isna().all(), 'spread is empty for a single (non-combined) file'
for meta in ('Site', 'Flag', 'Flag_T', 'Flag_lux', 'QCS version'):
    assert meta in cols, 'metadata %s missing in HOBO' % meta
assert oh['Site'].iloc[0] == 'PAB3'
ok.append('order_var hobo (only temp+light+metadata)')

# 9c) Lat/Long NEVER appear in the qualified spreadsheet (fixed column layout),
# even when present in the input; discarded in both layouts
qh3 = qh.copy(); qh3['Latitude'] = -17.5; qh3['Longitude'] = -40.0
oh3 = data.order_var(qh3.copy(), 1, data_type='hobo')
assert 'Latitude' not in oh3.columns and 'Longitude' not in oh3.columns, list(oh3.columns)
qt2 = pd.DataFrame({'Datetime': pd.date_range('2026-01-01', periods=2, freq='h'),
                    'Temperature (degC)': [25.0, 25.1], 'Site': ['D13', 'D13'],
                    'Latitude': [-17.5, -17.5], 'Longitude': [-40.0, -40.0]})
ot2 = data.order_var(qt2.copy(), 1, data_type='tscp')
assert 'Latitude' not in ot2.columns and 'Longitude' not in ot2.columns, 'tscp must not emit lat/long'
ok.append('order_var (Lat/Long optional, not created empty)')

# 10) order_var with an invalid data_type should warn clearly
try:
    data.order_var(qd.copy(), 1, data_type='outro')
    raise AssertionError('should have raised ValueError')
except ValueError:
    ok.append('order_var (clear error for invalid type)')

# 11) build_database: single unification engine (discovery, dedup, provenance)
import os as _os
import tempfile as _tempfile
with _tempfile.TemporaryDirectory() as tmp:
    sub1 = _os.path.join(tmp, 'saidaA', 'QCS qualified hobo data')
    sub2 = _os.path.join(tmp, 'saidaB', 'QCS qualified hobo data')
    _os.makedirs(sub1); _os.makedirs(sub2)
    h1 = pd.DataFrame({'Datetime': pd.date_range('2026-01-01', periods=3, freq='h'),
                       'Temperature (degC)': [25.0, 25.1, 25.2],
                       'Luminosity (lux)': [0.0, 100.0, 200.0],
                       'Site': ['PAB3'] * 3, 'Flag_T': [1, 1, 1], 'Flag_lux': [1, 1, 1]})
    h1.to_csv(_os.path.join(sub1, 'PAB3_qlf.csv'), index=False)
    h2 = h1.copy(); h2['Site'] = 'RH30'
    h2.to_csv(_os.path.join(sub2, 'RH30_qlf.csv'), index=False)
    pd.DataFrame({'x': [1]}).to_csv(_os.path.join(sub1, 'QCS_report.csv'), index=False)  # report file: ignore
    h1.to_csv(_os.path.join(sub2, 'PAB3_copia.csv'), index=False)  # exact duplicates: dedup
    db, msgs = data.build_database('HOBO', input_path=tmp)
    assert len(db) == 6, 'expected 3+3 rows after dedup: %d' % len(db)
    assert 'Source file' in db.columns, 'provenance column missing'
    assert set(db['Site']) == {'PAB3', 'RH30'}
    assert any('duplicate' in m for m in msgs), msgs
    assert not any('QCS_report' in s for s in db['Source file'].unique()), 'a report file must not enter the database'
    # mixing instruments is refused with a clear message
    t1 = pd.DataFrame({'Datetime': pd.date_range('2026-01-01', periods=2, freq='h'),
                       'Temperature (degC)': [25.0, 25.1], 'Salinity (PSU)': [36.0, 36.1],
                       'Site': ['D13'] * 2})
    tpath = _os.path.join(tmp, 'tscp_qlf.csv')
    t1.to_csv(tpath, index=False)
    try:
        data.build_database('HOBO', file_list=[tpath])
        raise AssertionError('should refuse to mix TSCP with HOBO')
    except ValueError as e:
        assert 'stackable' in str(e), e
    # and the same file works as Seaguard (csv with correct header - header=1 used to corrupt it)
    dbt, _ = data.build_database('Seaguard', file_list=[tpath])
    assert len(dbt) == 2 and dbt['Temperature (degC)'].iloc[0] == 25.0, 'qualified csv corrupted on read'
ok.append('build_database (discovery, dedup, provenance, refuse mix, csv ok)')

# 12) combine_hobo_replicates: temperature mean + spread; light = max of the
# non-fouled readings, usable window extended to the last replicate to foul
tgrid = pd.date_range('2026-01-01', periods=10, freq='h')
repA = pd.DataFrame({'Datetime': tgrid, 'Site': 'PAB3',
                     'Temperature (degC)': [25.0] * 10,
                     'Luminosity (lux)': [10000., 9000, 8000, 7000, 6000, 500, 400, 300, 200, 100],
                     'Flag_T': [1] * 10,
                     'Flag_lux': [1, 1, 1, 1, 1, 4, 4, 4, 4, 4]})   # A fouls from index 5
repB = pd.DataFrame({'Datetime': tgrid, 'Site': 'PAB3',
                     'Temperature (degC)': [25.2, 25.2, 25.2, 26.0, 25.2, 25.2, 25.2, 25.2, 25.2, 25.2],
                     'Luminosity (lux)': [11000., 9500, 8500, 7500, 6500, 6000, 5500, 5000, 300, 200],
                     'Flag_T': [1] * 10,
                     'Flag_lux': [1, 1, 1, 1, 1, 1, 1, 1, 4, 4]})   # B fouls from index 8
comb, cmsgs = data.combine_hobo_replicates([repA, repB], temp_tol=0.5)
assert len(comb) == 10, len(comb)
assert abs(comb['Temperature (degC)'].iloc[0] - 25.1) < 1e-6      # mean(25.0, 25.2)
assert comb['Flag_T'].iloc[0] == 1
assert comb['Flag_T'].iloc[3] == 3, 'disagreeing replicate temperatures -> SUSPECT'
assert abs(comb['Temperature spread (degC)'].iloc[3] - 1.0) < 1e-6
assert abs(comb['Temperature (degC)'].iloc[3] - 25.5) < 1e-6      # mean(25.0, 26.0)
assert comb['Luminosity (lux)'].iloc[0] == 11000.0, 'light = max of the clean replicates'
assert comb['Flag_lux'].iloc[6] == 1 and comb['Luminosity (lux)'].iloc[6] == 5500.0, 'A fouled, B clean -> keep B'
assert list(comb['Flag_lux']) == [1, 1, 1, 1, 1, 1, 1, 1, 4, 4], comb['Flag_lux'].tolist()
assert comb['Site'].iloc[0] == 'PAB3'
assert any('disagree' in m for m in cmsgs) and any('usable until' in m for m in cmsgs), cmsgs
ok.append('combine_hobo_replicates (T mean+spread, light max-of-clean, window extended)')

# 13) read_ctd: Seaguard export with a COMMA decimal separator (locale-dependent)
# must be parsed as numbers, not left as text (which broke every numeric test).
with _tempfile.TemporaryDirectory() as tmp:
    csv_path = _os.path.join(tmp, 'PISCINA_qlf.csv')
    with open(csv_path, 'w', encoding='utf-8') as f:
        f.write('Description;Seaguard II Platform\n')
        f.write('Serial Number;2104\n')
        f.write(';;;;;;\n')  # a metadata/blank row above the header
        f.write('Record Time;Record Number;Pressure[kPa];Temperature[DegC];Salinity[PSU]\n')
        f.write('16/03/2026 18:02:00;1;131,7655;28,62414;35,3102\n')
        f.write('16/03/2026 18:03:00;2;132,2957;28,62993;35,30405\n')
        f.write('16/03/2026 18:04:00;3;130,9420;28,64612;35,29525\n')
    d = data.read_ctd({'raw_data_path': tmp, 'file_name': 'PISCINA_qlf.csv'})
    assert len(d) == 3, len(d)
    for c in ('Pressure (kPa)', 'Temperature (degC)', 'Salinity (PSU)'):
        assert str(d[c].dtype).startswith('float'), '%s not numeric (%s)' % (c, d[c].dtype)
    assert abs(d['Pressure (kPa)'].iloc[0] - 131.7655) < 1e-6, d['Pressure (kPa)'].iloc[0]
    assert abs(d['Temperature (degC)'].iloc[2] - 28.64612) < 1e-6
    assert str(d['Datetime'].dtype).startswith('datetime64')
ok.append('read_ctd (Seaguard comma-decimal export parsed as numbers)')

# 14) manual point-cut -> flag DISMISSED (5): setting all of a variable's flag
# positions to '5' must roll up to Flag_<var> = 5 WITHOUT corrupting another
# variable that shares a position (e.g. density maps to both T and S; 5 is the
# lowest priority in worst_flag, so a stray 5 there never overrides a real flag).
flag_layout_14 = ['T', 'S', 'dens']   # dens contributes to both T and S
inp = pd.DataFrame({'Temperature (degC)': [20.0, 21.0, 22.0],
                    'Salinity (PSU)': [35.0, 35.1, 35.2]})
# row 0: all good; row 1: T manually dismissed (T-pos and dens-pos -> '5'),
# S keeps its real suspect '3'; row 2: whole row dismissed (every pos '5')
flags_14 = ['111', '535', '555']
out14 = data.handle_output_file(inp, flags_14, flag_layout_14,
                                remove_suspect=False, remove_bad=False)[0]
assert list(out14['Flag_T']) == [1, 5, 5], out14['Flag_T'].tolist()
assert list(out14['Flag_S']) == [1, 3, 5], out14['Flag_S'].tolist()  # S row1 unharmed by the shared-dens 5
ok.append('handle_output_file (manual-cut flag 5 rolls up per variable, no cross-contamination)')

# 15) read_ctd on a SeaGuard II raw binary session (AADIBXML1.0): a synthetic
# mini-session built to the reverse-engineered spec (header sections, template
# XML, tag dictionary, sync-framed typed records) must decode into the same
# standardized frame as a CSV export would.
import struct as _struct

def _aadi_dict_entry(ident, parent, type_code, name):
    # 13-byte prefix (u16 id, u16 parent, 3B pad, u32 type, 2B pad) + name + NUL
    return (_struct.pack('<HH', ident, parent) + b'\x00' * 3 +
            _struct.pack('<I', type_code) + b'\x00' * 2 + name + b'\x00')

def _build_mini_aadi():
    template = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<Device ID="5650-0" ProdName="SeaGuard II">\n'
        '<Time>2026-03-16T18:02:01Z</Time><StatusCode>0</StatusCode>\n'
        '<Data><Time>t</Time><RecordNumber>0</RecordNumber>\n'
        '<SensorData ID="4117B-1" Descr="Pressure Sensor #1">\n'
        '<StatusCode>0</StatusCode><Parameters>\n'
        '<Point ID="0" Descr="Pressure" Type="VT_R4" Unit="kPa"><StatusCode>0</StatusCode><Value /></Point>\n'
        '<Point ID="1" Descr="Temperature" Type="VT_R4" Unit="DegC"><StatusCode>0</StatusCode><Value /></Point>\n'
        '</Parameters></SensorData></Data></Device>').encode()
    dictionary = b''.join([
        _aadi_dict_entry(1, 0, 0x00, b'Device'),
        _aadi_dict_entry(2, 1, 0x28, b'Time'),
        _aadi_dict_entry(3, 1, 0x00, b'Data'),
        _aadi_dict_entry(4, 3, 0x04, b'RecordNumber'),
        _aadi_dict_entry(5, 3, 0x28, b'Time'),
        _aadi_dict_entry(6, 3, 0x00, b'SensorData'),
        _aadi_dict_entry(7, 6, 0x04, b'StatusCode'),
        _aadi_dict_entry(8, 6, 0x00, b'Parameters'),
        _aadi_dict_entry(9, 8, 0x00, b'Point'),
        _aadi_dict_entry(10, 9, 0x04, b'StatusCode'),
        _aadi_dict_entry(11, 9, 0x14, b'Value'),
        _aadi_dict_entry(12, 8, 0x00, b'Point'),
        _aadi_dict_entry(13, 12, 0x04, b'StatusCode'),
        _aadi_dict_entry(14, 12, 0x14, b'Value'),
    ])
    tpl_off = 488
    header = (b'AADIBXML1.0' + b'\x00' * (0x1c - 11) +
              _struct.pack('<7I', tpl_off, 0, 0, tpl_off, len(template),
                           tpl_off + len(template), len(dictionary)))
    header += b'\x00' * (tpl_off - len(header))
    ticks0 = 638_990_000_000_000_000            # a 2026 date, .NET ticks
    records = b''
    for i in range(3):
        fields = (_struct.pack('<H', 2) + _struct.pack('<q', ticks0 + i * 600_000_000) +
                  _struct.pack('<H', 4) + _struct.pack('<i', i + 1) +
                  _struct.pack('<H', 5) + _struct.pack('<q', ticks0 + i * 600_000_000) +
                  _struct.pack('<H', 7) + _struct.pack('<i', 0) +
                  _struct.pack('<H', 11) + _struct.pack('<f', 101.5 + i) +
                  _struct.pack('<H', 14) + _struct.pack('<f', 27.25 + 0.1 * i))
        records += (b'\x11\x22\x33\x44\x55\x66\x77\x88' +
                    _struct.pack('<II', len(fields), 6) + fields + b'\xae\xfd')
    return header + template + dictionary + records

with _tempfile.TemporaryDirectory() as tmp:
    bin_path = _os.path.join(tmp, 'Data000.bin')
    with open(bin_path, 'wb') as f:
        f.write(_build_mini_aadi())
    d = data.read_ctd({'raw_data_path': tmp, 'file_name': 'Data000.bin'})
    assert len(d) == 3, len(d)
    assert 'Pressure (kPa)' in d.columns and 'Temperature (degC)' in d.columns, list(d.columns)
    assert abs(d['Pressure (kPa)'].iloc[0] - 101.5) < 1e-5
    assert abs(d['Temperature (degC)'].iloc[2] - 27.45) < 1e-5
    assert str(d['Datetime'].dtype).startswith('datetime64')
    assert d['Datetime'].iloc[1] - d['Datetime'].iloc[0] == pd.Timedelta(minutes=1)
    assert data.sniff_input_type(bin_path) == 'Seaguard'
ok.append('read_ctd (SeaGuard raw .bin session decoded and standardized; sniffer detects it)')

# 16) dissolved-CO2 import: the logger export (repeated headers, Year..Second
# date columns) is read, and the merge LINEARLY INTERPOLATES onto the Seaguard
# timestamps, never bridging logger gaps (> 2x the median interval) nor
# extrapolating outside the CO2 coverage.
with _tempfile.TemporaryDirectory() as tmp:
    co2_path = _os.path.join(tmp, 'PISCINA_CO2.txt')
    hdr = ('Measurement type,Year,Month,Day,Hour,Minute,Second,Reference A/D,'
           'Current A/D,CO2 (PPM),Corrected disolved CO2 (PPM),Pressure sensor '
           'temperature,Pressure,IRGA detector temperature,Supply voltage\n')
    with open(co2_path, 'w', encoding='utf-8') as f:
        f.write(hdr)
        # samples every 2 min at :00 (values rise 10 ppm per sample), with a
        # 20-min LOGGER GAP between 12:08 and 12:28
        for i, (hh, mm) in enumerate([(12, 0), (12, 2), (12, 4), (12, 6), (12, 8),
                                      (12, 28), (12, 30), (12, 32)]):
            f.write('W M,2026,03,16,%02d,%02d,00,02217,02463,%0.2f,%0.2f,31.8,1013.3,26.8,7.0\n'
                    % (hh, mm, 505.0 + 10 * i, 500.0 + 10 * i))
        f.write(hdr)   # repeated header line (logger restart) must be skipped
    co2_df, msgs = data.read_co2_file(co2_path)
    assert len(co2_df) == 8, len(co2_df)
    assert abs(co2_df['CO2 Level (ppm)'].iloc[0] - 500.0) < 1e-9   # corrected column used
    # Seaguard minute grid 11:59..12:33
    grid = pd.DataFrame({'Datetime': pd.date_range('2026-03-16 11:59', '2026-03-16 12:33', freq='min'),
                         'Temperature (degC)': 27.0})
    merged, mmsgs = data.merge_co2_data(grid, co2_path)
    got = merged.set_index('Datetime')['CO2 Level (ppm)']
    assert np.isnan(got.loc['2026-03-16 11:59']), 'no extrapolation before coverage'
    assert abs(got.loc['2026-03-16 12:00'] - 500.0) < 1e-9         # exact sample
    assert abs(got.loc['2026-03-16 12:01'] - 505.0) < 1e-9         # halfway between 500 and 510
    assert np.isnan(got.loc['2026-03-16 12:15']), 'logger gap must NOT be bridged'
    assert abs(got.loc['2026-03-16 12:29'] - 555.0) < 1e-9         # halfway between 550 and 560
    assert np.isnan(got.loc['2026-03-16 12:33']), 'no extrapolation after coverage'
ok.append('read_co2_file + merge_co2_data (interpolation, gap masking, no extrapolation)')

# 17) CO2 qualification (v6.0): the 'CO2' flag bucket must roll up to Flag_CO2,
# remove_bad must clear ONLY the flagged CO2 values, and the O2 removal must
# NOT touch the CO2 column ('CO2 Level (ppm)' also matches a naive 'o2' regex).
inp17 = pd.DataFrame({'O2 level (uM)': [200.0, 210.0, 220.0],
                      'CO2 Level (ppm)': [500.0, 600.0, 700.0]})
flag_layout_17 = ['O2', 'CO2']
# row 0: both good; row 1: O2 bad / CO2 good; row 2: O2 good / CO2 bad
flags_17 = ['11', '41', '14']
out17 = data.handle_output_file(inp17, flags_17, flag_layout_17,
                                remove_suspect=False, remove_bad=True)[0]
assert list(out17['Flag_O2']) == [1, 4, 1], out17['Flag_O2'].tolist()
assert list(out17['Flag_CO2']) == [1, 1, 4], out17['Flag_CO2'].tolist()
assert np.isnan(out17['O2 level (uM)'].iloc[1]) and not np.isnan(out17['O2 level (uM)'].iloc[2])
assert np.isnan(out17['CO2 Level (ppm)'].iloc[2]), 'bad CO2 value not removed'
assert not np.isnan(out17['CO2 Level (ppm)'].iloc[1]), 'O2 flags must NOT clear CO2 values'
ok.append('handle_output_file (CO2 bucket rolls up to Flag_CO2; O2/CO2 removals independent)')

# 18) reader fix (v7.0): a <Point> OUTSIDE the <SensorData> blocks (device
# housekeeping like 'Input Voltage'/'Memory Used') still owns a Value slot in the
# tag dictionary. The old reader counted only SensorData points and rejected the
# layout ('unsupported layout variant'); this is exactly the group that carries
# pH/chlorophyll/turbidity on real deployments. Now every <Point> is taken.
def _one_sensor_aadi(descr, unit, samples, ticks0, inside=True, sys_descr=None):
    # samples: list of (offset_seconds, value); one sensor Point (+ optional
    # system Point OUTSIDE <SensorData>). Mirrors _build_mini_aadi's layout.
    tps = 10_000_000                                    # .NET ticks per second
    sys_point = ('<Point ID="9" Descr="%s" Type="VT_R4" Unit="V" Format="%%.1f">'
                 '<StatusCode>0</StatusCode><Value /></Point>\n' % sys_descr) if sys_descr else ''
    template = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<Device ID="5650-0" ProdName="SeaGuard II">\n'
        '<Time>2026-03-16T18:02:01Z</Time><StatusCode>0</StatusCode>\n'
        '<Data><Time>t</Time><RecordNumber>0</RecordNumber>\n'
        '<SensorData ID="S-1" Descr="Group #0">\n'
        '<StatusCode>0</StatusCode><Parameters>\n'
        '<Point ID="0" Descr="%s" Type="VT_R4" Unit="%s"><StatusCode>0</StatusCode><Value /></Point>\n'
        '</Parameters></SensorData>\n%s</Data></Device>' % (descr, unit, sys_point)).encode()
    entries = [
        _aadi_dict_entry(1, 0, 0x00, b'Device'), _aadi_dict_entry(2, 1, 0x28, b'Time'),
        _aadi_dict_entry(3, 1, 0x00, b'Data'), _aadi_dict_entry(4, 3, 0x04, b'RecordNumber'),
        _aadi_dict_entry(5, 3, 0x28, b'Time'), _aadi_dict_entry(6, 3, 0x00, b'SensorData'),
        _aadi_dict_entry(7, 6, 0x04, b'StatusCode'), _aadi_dict_entry(8, 6, 0x00, b'Parameters'),
        _aadi_dict_entry(9, 8, 0x00, b'Point'), _aadi_dict_entry(10, 9, 0x04, b'StatusCode'),
        _aadi_dict_entry(11, 9, 0x14, b'Value'),
    ]
    if sys_descr:                                       # system Point outside SensorData
        entries += [_aadi_dict_entry(12, 3, 0x00, b'Point'),
                    _aadi_dict_entry(13, 12, 0x04, b'StatusCode'),
                    _aadi_dict_entry(14, 12, 0x14, b'Value')]
    dictionary = b''.join(entries)
    tpl_off = 488
    header = (b'AADIBXML1.0' + b'\x00' * (0x1c - 11) +
              _struct.pack('<7I', tpl_off, 0, 0, tpl_off, len(template),
                           tpl_off + len(template), len(dictionary)))
    header += b'\x00' * (tpl_off - len(header))
    records = b''
    for i, (off, val) in enumerate(samples):
        fields = (_struct.pack('<H', 2) + _struct.pack('<q', ticks0) +
                  _struct.pack('<H', 4) + _struct.pack('<i', i + 1) +
                  _struct.pack('<H', 5) + _struct.pack('<q', ticks0 + off * tps) +
                  _struct.pack('<H', 7) + _struct.pack('<i', 0) +
                  _struct.pack('<H', 11) + _struct.pack('<f', val))
        nf = 5
        if sys_descr:
            fields += _struct.pack('<H', 14) + _struct.pack('<f', 7.7); nf = 6
        records += (b'\x11\x22\x33\x44\x55\x66\x77\x88' +
                    _struct.pack('<II', len(fields), nf) + fields + b'\xae\xfd')
    return header + template + dictionary + records

_TICKS0 = 638_990_000_000_000_000
with _tempfile.TemporaryDirectory() as tmp:
    bin_path = _os.path.join(tmp, 'Data000.bin')
    with open(bin_path, 'wb') as f:
        f.write(_one_sensor_aadi('AMT pH#1', 'pH', [(0, 7.0), (10, 7.1), (20, 7.2)],
                                 _TICKS0, sys_descr='Input Voltage'))
    raw = data.read_seaguard_bin(bin_path)              # would raise before the fix
    assert 'AMT pH#1[pH]' in raw.columns and 'Input Voltage[V]' in raw.columns, list(raw.columns)
    assert abs(raw['AMT pH#1[pH]'].iloc[0] - 7.0) < 1e-5
    assert abs(raw['Input Voltage[V]'].iloc[0] - 7.7) < 1e-5
    std = data.read_ctd({'raw_data_path': tmp, 'file_name': 'Data000.bin'})
    assert 'pH' in std.columns and abs(std['pH'].iloc[2] - 7.2) < 1e-5, list(std.columns)
ok.append('read_seaguard_bin (Point outside <SensorData> decodes; pH/optical group unlocked)')

# 19) deployment merge (v7.0): sibling sensor-group folders of the same cast,
# sampled at DIFFERENT rates, are merged onto the FINEST group's time axis with
# linear interpolation (slower sensors), so a multi-group cast qualifies together.
with _tempfile.TemporaryDirectory() as tmp:
    coarse = _os.path.join(tmp, '5650-2097-0-2026-03-16T18-02-01.000Z')   # pH every 20 s
    fine = _os.path.join(tmp, '5650-2097-1-2026-03-16T18-02-01.100Z')     # temp every 10 s
    _os.makedirs(coarse); _os.makedirs(fine)
    with open(_os.path.join(coarse, 'Data000.bin'), 'wb') as f:
        f.write(_one_sensor_aadi('AMT pH#1', 'pH', [(0, 7.0), (20, 7.2), (40, 7.4)], _TICKS0))
    with open(_os.path.join(fine, 'Data000.bin'), 'wb') as f:
        f.write(_one_sensor_aadi('Temperature', 'DegC',
                                 [(0, 27.0), (10, 27.1), (20, 27.2), (30, 27.3), (40, 27.4)], _TICKS0))
    dep = data.read_seaguard_deployment(_os.path.join(fine, 'Data000.bin'))
    assert len(dep) == 5, len(dep)                      # master = finest (temperature) axis
    assert 'Temperature[DegC]' in dep.columns and 'AMT pH#1[pH]' in dep.columns, list(dep.columns)
    assert abs(dep['Temperature[DegC]'].iloc[0] - 27.0) < 1e-5
    assert abs(dep['AMT pH#1[pH]'].iloc[1] - 7.1) < 1e-5, dep['AMT pH#1[pH]'].tolist()  # interp at +10 s
    assert abs(dep['AMT pH#1[pH]'].iloc[3] - 7.3) < 1e-5                                 # interp at +30 s
ok.append('read_seaguard_deployment (sibling sensor groups merged onto finest axis by time interpolation)')

# 20) Doppler current QC (v8.0): the 4-test flag string and the Flag_cur rollup.
# Rows: good | over-speed BAD | dead cell (state!=0) BAD | noisy SUSPECT |
# tilted SUSPECT | missing.
import QCS_Tests as _QCT
dop = pd.DataFrame({
    'Horizontal speed (cm/s)': [10.0, 400.0, 0.0, 12.0, 11.0, np.nan],
    'Signal strength (dB)':    [-40.0, -40.0, 0.0, -40.0, -40.0, -40.0],
    'Cell state':              [0, 0, 9408, 0, 0, 0],
    'Speed stdev (cm/s)':      [5.0, 5.0, 5.0, 80.0, 5.0, 5.0],
    'Tilt (deg)':              [5.0, 5.0, 5.0, 5.0, 20.0, 5.0],
})
dflags, droll = _QCT.doppler_qc(dop)
assert dflags[0] == '1111' and droll[0] == 1, (dflags[0], droll[0])
assert dflags[1][0] == '4' and droll[1] == 4, dflags[1]          # over max_speed
assert dflags[2][1] == '4' and droll[2] == 4, dflags[2]          # dead cell state
assert dflags[3][2] == '3' and droll[3] == 3, dflags[3]          # noisy stdev
assert dflags[4][3] == '3' and droll[4] == 3, dflags[4]          # tilt suspect
assert dflags[5] == '9999' and droll[5] == 9, dflags[5]          # missing
# tilt BAD threshold
dflags2, droll2 = _QCT.doppler_qc(dop.assign(**{'Tilt (deg)': [40.0] * 6}))
assert dflags2[0][3] == '4' and droll2[0] == 4
ok.append('doppler_qc (speed range / signal quality / stdev / tilt; Flag_cur rollup)')

# 21) is_seaguard_doppler: detects the DCPS template, rejects the scalar one.
with _tempfile.TemporaryDirectory() as tmp:
    dcps_tpl = ('<?xml version="1.0"?><Device><Data>'
                '<SensorData ID="5400-1" Descr="DCPS #1" ProdName="Doppler Current '
                'Profiler Sensor"></SensorData></Data></Device>').encode()
    tpl_off = 488
    hdr = (b'AADIBXML1.0' + b'\x00' * (0x1c - 11) +
           _struct.pack('<7I', tpl_off, 0, 0, tpl_off, len(dcps_tpl),
                        tpl_off + len(dcps_tpl), 0))
    hdr += b'\x00' * (tpl_off - len(hdr))
    p_dcps = _os.path.join(tmp, 'Data000.bin')
    with open(p_dcps, 'wb') as f:
        f.write(hdr + dcps_tpl)
    assert data.is_seaguard_doppler(p_dcps) is True
    p_scalar = _os.path.join(tmp, 'Data001.bin')
    with open(p_scalar, 'wb') as f:
        f.write(_build_mini_aadi())
    assert data.is_seaguard_doppler(p_scalar) is False
ok.append('is_seaguard_doppler (DCPS template detected; scalar session rejected)')

# 22) Settings -> current QC plumbing (v8.1). Before v8.1 the pipeline read a
# CONFIG['dopplerSettings'] that nothing ever wrote, so the Settings window
# could not reach the current tests at all - this guards the whole path:
# every DOPPLER_DEFAULTS key is editable, the defaults agree, and an edited
# criterion really changes the flags.
import QCS_Theme as _thm
_orig_rdr, _orig_crash = _thm.install_output_redirect, _thm.install_crash_handler
_thm.install_output_redirect = lambda *a, **k: type(
    'S', (), {'history': [], 'set_sink': lambda *a, **k: None,
              'write': lambda *a, **k: None, 'flush': lambda *a, **k: None})()
_thm.install_crash_handler = lambda *a, **k: None
try:
    import QCS_Main as _QM
finally:
    _thm.install_output_redirect, _thm.install_crash_handler = _orig_rdr, _orig_crash
assert set(_QM.doppler_settings().keys()) == set(_QCT.DOPPLER_DEFAULTS.keys()), \
    (sorted(_QM.doppler_settings()), sorted(_QCT.DOPPLER_DEFAULTS))
assert _QM.doppler_settings() == _QCT.DOPPLER_DEFAULTS, \
    'Settings defaults diverge from DOPPLER_DEFAULTS'
_old_max = _QM.CONFIG['tsSettings']['doppler_max_speed']
try:
    _QM.CONFIG['tsSettings']['doppler_max_speed'] = 5.0
    dflags3, droll3 = _QCT.doppler_qc(dop, _QM.doppler_settings())
    assert dflags3[0][0] == '4' and droll3[0] == 4, dflags3[0]   # 10 cm/s > 5 -> BAD
finally:
    _QM.CONFIG['tsSettings']['doppler_max_speed'] = _old_max
ok.append('doppler_settings (Settings keys == DOPPLER_DEFAULTS; edited criterion reaches doppler_qc)')

# 23) Redundant-replicate referee (v9.0). Three outcomes on synthetic data:
# (a) sound replicates -> no disagreement, nobody named;
# (b) one replicate drifts off the regional signal -> the SOUND one is named;
# (c) same disagreement but NO reference -> reported, nobody named (never guess).
_days = pd.date_range('2022-03-17', periods=190, freq='D')
_season = 28.5 - 4.0 * np.linspace(0, 1, len(_days))     # regional cooling
_ref = pd.Series(_season, index=_days)


def _rep(values):
    return pd.DataFrame({'Datetime': _days, 'Temperature (degC)': values,
                         'Flag_T': [1] * len(_days)})


# (a) both track the season (tiny offsets)
_good_a, _good_b = _rep(_season + 0.05), _rep(_season - 0.05)
_r = _QCT.replicate_referee([_good_a, _good_b], reference=_ref)
assert _r['disagrees'] is False, _r
assert _r['recommended'] is None, _r

# (b) replicate 1 goes flat from day 45 (a stuck sensor on a plausible value)
_stuck = _season.copy()
_stuck[45:] = _season[45]
_r = _QCT.replicate_referee([_rep(_stuck), _rep(_season)], reference=_ref)
assert _r['disagrees'] is True, _r
assert _r['recommended'] == 1, _r          # the SOUND replicate (index 1)
assert _r['scores'][1]['change_corr'] > _r['scores'][0]['change_corr'], _r['scores']

# (c) same pair, no reference -> reported but nobody named
_r = _QCT.replicate_referee([_rep(_stuck), _rep(_season)], reference=None)
assert _r['disagrees'] is True and _r['recommended'] is None, _r
assert any('no independent reference' in w for w in _r['warnings']), _r['warnings']
ok.append('replicate_referee (agreement / names the sound replicate / refuses without a reference)')

print('\n'.join('OK: ' + t for t in ok))
print('\n%d tests passed.' % len(ok))

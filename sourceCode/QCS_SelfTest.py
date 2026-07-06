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

# 5d) apply_light_window: 1 before / 3 after the cutoff, 9 for NaN, 2 if not evaluable
lux_nan = list(lux)
lux_nan[100] = np.nan
fl = QC.apply_light_window(dt, lux_nan, ['' for _ in dt], res['proposed_cutoff'])
assert fl[24] == '1', 'day 1 (clean water) should be good: %s' % fl[24]
assert fl[100] == '9'
assert fl[-1] == '3', 'after the cutoff it should be suspect: %s' % fl[-1]
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

# 7c) HOBO layout (with 'lux' position): Flag_lux created; remove_suspect erases the light
HOBO_LAYOUT = MOORING_LAYOUT + ['lux']
dfh = pd.DataFrame({'Datetime': pd.date_range('2026-01-01', periods=3, freq='h'),
                    'Temperature (degC)': [25.0, 25.1, 25.2],
                    'Luminosity (lux)': [10000.0, 8000.0, 500.0]})
flags_h = ['1' * len(HOBO_LAYOUT),
           '1' * len(HOBO_LAYOUT),
           flag_with(HOBO_LAYOUT, 'lux', '3')]  # last row: suspect light (fouled)
outh = data.handle_output_file(dfh, flags_h, HOBO_LAYOUT, remove_suspect=True, remove_bad=False)
outh_df = outh[0]
assert list(outh_df['Flag_lux']) == [1, 1, 3], outh_df['Flag_lux'].tolist()
assert np.isnan(outh_df['Luminosity (lux)'].iloc[2]), 'remove_suspect should erase the fouled light'
assert outh_df['Luminosity (lux)'].iloc[0] == 10000.0
assert outh_df['Temperature (degC)'].iloc[2] == 25.2, 'a light flag must not affect temperature'
ok.append('handle_output_file (Flag_lux + removal of suspect light)')

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
assert cols[:5] == ['Sample number', 'Datetime', 'Site', 'Temperature (degC)', 'Luminosity (lux)'], cols
assert 'Expedition' not in cols, 'the Expedition (empty) column must no longer exist: %s' % cols
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

print('\n'.join('OK: ' + t for t in ok))
print('\n%d tests passed.' % len(ok))

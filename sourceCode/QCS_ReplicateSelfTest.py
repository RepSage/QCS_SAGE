"""Regression checks for the v14 HOBO decision and combination contract."""
from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np
import pandas as pd

import QCS_DataHandler as data
import QCS_Replicates as policy


def run():
    grid = pd.date_range('2025-01-01', periods=73, freq='h')
    a = pd.DataFrame({'Datetime': grid, policy.TEMP: 25., policy.LIGHT: 100.,
                      'Flag_T': 1, 'Flag_lux': 1})
    b = a.copy()
    b[policy.TEMP] = 29.
    b[policy.LIGHT] = 200.
    empty = pd.DataFrame(columns=policy.DECISION_COLUMNS)
    combined, _ = data.combine_hobo_replicates([a, b], decisions=empty)
    assert len(combined) == 73 and combined[policy.TEMP].isna().all()
    assert combined.Flag_T.eq(3).all() and combined[policy.LIGHT].eq(200).all()
    assert combined['Temperature spread (degC)'].eq(4).all()

    # Missing readings and clock gaps must split episodes, never bridge them.
    short = b.copy()
    short.loc[short.index % 24 == 0, policy.TEMP] = np.nan
    transient, _ = data.combine_hobo_replicates([a, short], decisions=empty)
    assert transient[policy.TEMP].notna().all()
    isolated = a.copy()
    isolated.loc[12, policy.TEMP] = 31.
    out, _ = data.combine_hobo_replicates([a, isolated], decisions=empty)
    assert out.loc[12, policy.TEMP] == 28 and out.loc[12, 'Flag_T'] == 3
    gaps = pd.concat([a.iloc[:12], a.iloc[48:60]])
    far = gaps.copy()
    far[policy.TEMP] = 29.
    out, _ = data.combine_hobo_replicates([gaps, far], decisions=empty)
    assert out[policy.TEMP].notna().all()

    row = ['test', 'bad.xlsx', policy.TEMP, str(grid[24]), str(grid[48]),
           'exclude', 'Known test fault', 'Test reviewer', '2026-09-03']
    decisions = pd.DataFrame([row], columns=policy.DECISION_COLUMNS)
    out, _ = data.combine_hobo_replicates([a, b], decisions=decisions,
                                         source_names=['good.xlsx', 'bad.xlsx'])
    assert out.loc[24:48, policy.TEMP].eq(25).all()
    assert out.loc[24:48, 'Temperature spread (degC)'].isna().all()
    assert out[policy.LIGHT].eq(200).all()  # a T decision cannot discard light
    assert out.loc[0, policy.TEMP] == 27 and out.loc[72, policy.TEMP] == 27
    assert len(out.attrs['replicate_audit']['decisions']) == 1

    # Diagnostic bad values survive optional cleaning but never enter a mean.
    bad_diagnostic = b.copy()
    bad_diagnostic['Flag_T'] = 4
    bad_output = bad_diagnostic.copy()
    bad_output[policy.TEMP] = np.nan
    out, _ = data.combine_hobo_replicates([a, bad_output], decisions=empty,
                                         diagnostics=[a, bad_diagnostic])
    assert out[policy.TEMP].eq(25).all()
    audit = out.attrs['replicate_audit']
    assert audit['episodes'].sustained.sum() == 1
    assert audit['samples'].temperature_2_degC.eq(29).all()
    assert audit['samples'].eligible_contributors.eq(1).all()

    report = policy.combined_report(combined).iloc[0]
    assert report.Total == 73 and report.T_suspect == 73 and report.T_withheld == 73
    assert report.Valid == 0 and report.lux_good == 73
    paths = [policy.report_destination(Path('run') / rep / 'QCS_report.xlsx',
                                       Path('run'), Path('run/combined/out.csv'), 'product')
             for rep in ['one', 'two', 'combined']]
    assert len(set(paths)) == 3 and paths[-1] == 'product__QCS_report.xlsx'
    assert len(policy.legacy_exclusions()) == 8
    dismissed, flags, applied, samples = policy.dismiss_single(
        b, ['111111'] * len(b), ['T'] * 5 + ['lux'], data.FLAG_BUCKET_MAP,
        'bad.xlsx', decisions)
    assert dismissed.loc[24:48, policy.TEMP].isna().all()
    assert dismissed[policy.LIGHT].eq(200).all() and flags[24] == '555551'
    assert flags[23] == '111111' and samples[policy.TEMP].eq(29).all()
    assert len(applied) == 1
    with TemporaryDirectory() as directory:
        path = Path(directory) / 'decisions.csv'
        duplicate = pd.concat([decisions, decisions])
        duplicate.to_csv(path, index=False)
        try:
            policy.load_decisions(path)
            raise AssertionError('Duplicate decisions accepted')
        except ValueError:
            pass
        legacy_report = Path(directory) / 'product__QCS_tscp_stat.xlsx'
        legacy_report.write_text('old individual report', encoding='utf-8')
        policy.archive_legacy_reports(directory, 'product')
        assert not legacy_report.exists()
        backups = list((Path(directory) / 'previous').rglob('*.xlsx'))
        assert len(backups) == 1 and backups[0].read_text(encoding='utf-8') == 'old individual report'
        long_folder = Path(directory) / ('a' * 65) / ('b' * 65) / ('c' * 50)
        long_folder.mkdir(parents=True)
        copied = policy.copy_report_file(backups[0], long_folder / ('QCS_' + 'd' * 70 + '.xlsx'))
        assert Path(copied).read_text(encoding='utf-8') == 'old individual report'
        Path(copied).unlink()
    return ['HOBO sustained versus transient disagreement and gap boundaries',
            'HOBO variable/interval decisions retain the grid and light',
            'HOBO diagnostics survive cleaning without restoring bad contributors',
            'HOBO actual combined counts and collision-free individual reports',
            'HOBO decision ledger validation and eight legacy exclusions',
            'HOBO single-file exclusions and legacy report preservation']

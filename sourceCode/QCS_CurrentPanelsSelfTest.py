"""Scientific display regressions, using the QCS NumPy/pandas runtime."""
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

import QCS_CurrentPanels as current


def frame(values, directions=None, flags=None):
    n = len(values)
    return pd.DataFrame({'Datetime': pd.date_range('2025-01-01', periods=n, freq='5min'),
        'Site': 'TEST', 'Column': 'Column 1', 'Cell': 0, 'Depth (m)': 6.,
        'Depth reference': 'surface', 'Direction reference': 'magnetic',
        'Horizontal speed (cm/s)': values, 'Direction (deg)': directions or [90.] * n,
        'East speed (cm/s)': [-100.] * n, 'North speed (cm/s)': [100.] * n,
        'Flag_cur': flags or [1] * n})


def run():
    checks = []
    f = frame([10., 10., 999.], [350., 10., 180.], [1, 1, 4])
    before = f.copy(deep=True)
    p = current.prepare(f, {'currentBinMinutes': 15})
    assert np.isclose(p['arrays']['speed'][0, 0], 10*np.cos(np.deg2rad(10)))
    assert np.isclose(p['arrays']['u'][0, 0], 0, atol=1e-12)
    assert min(p['arrays']['direction'][0, 0], 360-p['arrays']['direction'][0, 0]) < 1e-10
    assert p['details'][0, 0]['valid'] == 2 and p['details'][0, 0]['expected'] == 3
    assert p['arrays']['qc'][0, 0] == 4 and p['arrays']['coverage'][0, 0] == 2/3
    pd.testing.assert_frame_equal(f, before)
    checks.append('Current vector means: circular wrap, BAD exclusion, coverage and immutable native U/V')

    rows = pd.concat([frame([10., 10., 10.]).assign(**{'Depth (m)': d, 'Cell': i,
        'Flag_cur': 4 if d in (2., 4.) else 1, 'Surface cell': d == 0.})
        for i, d in enumerate([0., 2., 4., 6.])], ignore_index=True)
    p = current.prepare(rows, {'currentBinMinutes': 0})
    assert p['arrays']['speed'].shape == (4, 3)
    assert np.isnan(p['arrays']['speed'][1:3]).all()
    assert p['labels'][0] == 'Surface'
    assert 'BAD 1' in current.hover_text(p, 1, 0)
    good = current.prepare(rows.assign(Flag_cur=3), {'currentQuality': 'good'})
    assert good['eligible_rows'] == 0 and np.isnan(good['arrays']['speed']).all()
    gap = frame([10., 10.])
    gap.loc[1, 'Datetime'] += pd.Timedelta(days=100)
    p = current.prepare(gap, {'currentBinMinutes': 15})
    assert p['arrays']['speed'].shape[1] == 3 and np.isnan(p['arrays']['speed'][0, 1])
    checks.append('Current grid: discarded depths, explicit empty intervals, surface identity and GOOD-only view')

    single = current.prepare(rows, {'depthAxisMin': 2., 'depthAxisMax': 2., 'currentBinMinutes': 30})
    assert len(single['cells']) == 1 and single['details'][0, 0]['expected'] == 6
    assert np.isnan(single['arrays']['speed']).all()
    cancelled = current.prepare(frame([10., 10.], [90., 270.]), {'currentBinMinutes': 30})
    assert cancelled['arrays']['speed'][0, 0] < 1e-8
    assert np.isnan(cancelled['arrays']['direction'][0, 0])
    checks.append('Current resolution: single discarded cell, 30-minute expected count and undefined cancelling direction')

    outer = pd.concat([frame([10.] * 7, flags=[4, 1, 4, 1, 1, 4, 4]).assign(
        **{'Depth (m)': depth, 'Cell': i, 'Surface cell': depth == 0.,
           'Flag_cur': [4] * 7 if depth == 8. else [4, 1, 4, 1, 1, 4, 4]})
        for i, depth in enumerate([0., 4., 8.])], ignore_index=True)
    original = outer.copy(deep=True)
    p = current.prepare(outer, {'currentBinMinutes': 0})
    assert current.display_extent(p) == (0, 1, 1, 4)
    assert np.isnan(p['arrays']['speed'][:, 2]).all()  # internal BAD gap stays
    assert p['labels'] == ['Surface', '4 m', '8 m']
    assert p['tick_labels'] == ['Surface', '4', '8']
    assert current.display_extent(good) is None
    assert current.display_extent(cancelled) == (0, 0, 0, 0)  # calm is eligible
    pd.testing.assert_frame_equal(outer, original)
    with tempfile.TemporaryDirectory() as folder:
        import matplotlib.dates as mdates
        import matplotlib.pyplot as plt
        figures = []
        current.plot_panels(outer, folder, settings={'currentBinMinutes': 0}, figures=figures)
        for fig in figures:
            for _, ax in fig._qcs_customize_axes:
                footer = [record for record in fig._qcs_legend_labels[ax] if record['name'] == 'Figure footer']
                assert len(footer) == 1 and footer[0]['artist'] is fig._qcs_footer
        ax = figures[0].axes[0]
        assert ax.get_ylabel() == 'Configured cell (m)'
        assert ax.get_ylim() == (1.5, -.5)
        assert np.allclose(ax.get_xlim(), mdates.date2num(p['edges'][[1, 5]].to_pydatetime()))
        assert [label.get_text() for label in ax.get_yticklabels()] == ['Surface', '4']
        for fig in figures:
            plt.close(fig)
        assert current.plot_panels(outer.assign(Flag_cur=4), folder) == []
    checks.append('Current plot extent: eligible outer bounds, internal gaps, calm/single bin, unit ticks and editable footer')

    f = frame([10., 10., 110., 10., 10., 10., 10., 10., 10.])
    p = current.prepare(f, {'currentBinMinutes': 0, 'currentTemporalPreview': True,
                           'currentFlatTolerance': .1})
    assert np.isclose(p['temporal']['spike'][0, 2], 100.)
    assert np.isclose(p['temporal']['rate'][0, 2], 20.)
    assert np.isclose(p['temporal']['flat'][0, -1], 25.)
    f.loc[1, 'Flag_cur'] = 4
    p = current.prepare(f, {'currentBinMinutes': 0, 'currentTemporalPreview': True})
    assert np.isnan(p['temporal']['spike'][0, 2]) and np.isnan(p['temporal']['rate'][0, 2])
    assert f.Flag_cur.tolist() == [1, 4, 1, 1, 1, 1, 1, 1, 1]
    checks.append('Experimental current diagnostics: spike/rate units, flat duration, GOOD references and BAD gaps')

    assert current.direction_metadata({'Enable Magnetic Declination': 'false'})['Direction reference'] == 'magnetic'
    assert current.direction_metadata({'Enable Magnetic Declination': 'true', 'Declination Angle': '-20'})['Direction reference'] == 'true'
    assert current.direction_metadata({})['Direction reference'] == 'unknown'
    with tempfile.TemporaryDirectory() as folder:
        root = Path(folder)
        qualified = root / 'SEAGUARD/qualified/2025S1/TEST/product.csv'
        qualified.parent.mkdir(parents=True)
        (qualified.parent / 'provenance.txt').write_text('product\n    inputs : exact-session\n\n', encoding='utf-8')
        native = root / 'SEAGUARD/raw/2025S1/TEST/FUNDEIO/DATA/DOPPLER/exact-session/Config.xml'
        native.parent.mkdir(parents=True)
        native.write_text('<Device><Sensor Descr="DCPS #123"><Property Descr="Enable Magnetic Declination">false</Property></Sensor></Device>')
        unknown = frame([10.]).drop(columns='Direction reference')
        enriched = current.enrich_direction_metadata(unknown, qualified)
        assert enriched['Direction reference'].eq('magnetic').all() and len(enriched) == len(unknown)
        assert 'Direction reference' not in unknown
        missing = current.enrich_direction_metadata(unknown, root / 'elsewhere.csv')
        assert missing['Direction reference'].eq('unknown').all()
        (qualified.parent / 'provenance.txt').write_text('product\n    inputs : wrong-session\n\n', encoding='utf-8')
        assert current.enrich_direction_metadata(unknown, qualified)['Direction reference'].eq('unknown').all()
    checks.append('Current north reference: exact native provenance, unchanged rows and unknown fallback')
    return checks

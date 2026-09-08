"""Regression checks for native DCPS decoding, status and plot identity.

Dependencies: the QCS runtime in requirements.txt. Called by QCS_SelfTest.py.
"""
from pathlib import Path
import struct
import tempfile

import numpy as np
import pandas as pd

import QCS_DataHandler as data
import QCS_DataView as view
import QCS_Tests as qc


def _binary(width=2, partial=False, field_delta=0, container=False):
    """Small AADI fixture with a vector followed by signed native status words."""
    entries = [(1, 0, 0, 'Device'), (2, 1, 40, 'Time'), (3, 1, 0, 'Data'),
               (4, 3, 40, 'Time'), (5, 3, 4, 'RecordNumber'),
               (6, 3, 0, 'SensorData'), (7, 6, 0, 'Point'), (8, 7, 4, 'Value'),
               (9, 6, 0, 'Column'), (10, 9, 0, 'Cell'),
               (11, 10, 0, 'Point'), (12, 11, 20, 'Value'),
               (13, 10, 0, 'Point'), (14, 13, 2, 'Value'),
               (15, 10, 0, 'Point'), (16, 15, 2, 'Value'),
               (17, 6, 0, 'Vector'), (18, 17, 4, 'Value')]
    dictionary = b''.join(struct.pack('<HH', i, p) + b'\0'*3 + struct.pack('<I', tc)
                          + b'\0'*2 + name.encode() + b'\0'*4 for i, p, tc, name in entries)
    template = b'''<Device><Data><SensorData Descr="DCPS #test">
      <Point Descr="Record State"><Value>0</Value></Point>
      <Column Descr="Column 1" ColumnStartCellCenter="2" CellSize="2"
              CellCenterSpacing="1.5" NumCells="1" SurfaceReferred="true">
        <CellAttributes><Point ID="speed" Descr="Horizontal Speed" Unit="cm/s"/>
          <Point ID="state1" Descr="Cell State1"/><Point ID="state2" Descr="Cell State2"/>
        </CellAttributes><Cell Index="0"><Point ID="speed"><Value>1</Value></Point>
          <Point ID="state1"><Value>0</Value></Point><Point ID="state2"><Value>0</Value></Point>
        </Cell></Column></SensorData></Data></Device>'''
    ticks = (pd.Timestamp('2026-01-01') - pd.Timestamp('1970-01-01')).value // 100 + 621355968000000000
    fields = [struct.pack('<Hq', 2, ticks), struct.pack('<Hi', 5, 0), struct.pack('<Hq', 4, ticks),
              struct.pack('<H', 18) + struct.pack('<H' if width == 2 else '<I', 4) + b'\0'*16,
              struct.pack('<Hf', 12, 12.5), struct.pack('<Hh', 14, 64), struct.pack('<Hh', 16, -32768)]
    if not partial:
        fields.append(struct.pack('<Hi', 7 if container else 8, 512))
    payload = b''.join(fields)
    record = data._AADI_SYNC + struct.pack('<II', len(payload)+20, len(fields)+field_delta) + payload + b'\0'*4
    off = 256
    header = data._AADI_MAGIC + b'\0'*(0x1c-len(data._AADI_MAGIC))
    header += struct.pack('<7I', off, 0, 0, off, len(template), off+len(template), len(dictionary))
    return header + b'\0'*(off-len(header)) + template + dictionary + record


def run():
    checks = []
    with tempfile.TemporaryDirectory() as folder:
        path = Path(folder) / 'Data000.bin'
        for width in (2, 4):
            for partial in (False, True):
                path.write_bytes(_binary(width, partial))
                report, metadata = {}, {}
                records, slots, _ = data._decode_dcps_bin(path, diagnostics=report, metadata=metadata)
                assert len(records) == 1 and records[0][1][2] == 64
                assert records[0][1][3] == -32768 and slots[1][-1] == 2
                assert len(report['partial_records']) == int(partial)
                assert report['vector_width_counts'][width] == 1
                assert metadata['record_slots'] == {'Record State': 0}
        for options in ({'field_delta': 1}, {'field_delta': -1}, {'container': True}):
            path.write_bytes(_binary(**options))
            try:
                data._decode_dcps_bin(path)
            except ValueError:
                pass
            else:
                raise AssertionError('Malformed field structure accepted: %r' % options)
    checks.append('DCPS decoder: both vector widths, partial records, field kinds and declared counts')

    base = {'Cell state': 0., 'Cell state 2': 0., 'Record state': 0.,
            'Native status map': 'TD304-2024', 'Depth reference': 'surface',
            'Surface cell': False, 'AutoBeam replacement': False}
    cases = [({}, 1), ({'Cell state': 64}, 3), ({'Cell state': 256}, 3),
             ({'Cell state': 4096}, 4), ({'Cell state': -32768}, 4),
             ({'Cell state 2': 256}, 3), ({'Cell state 2': 1}, 4),
             ({'Cell state 2': 1, 'AutoBeam replacement': True}, 3),
             ({'Cell state 2': 3, 'AutoBeam replacement': True}, 4),
             ({'Record state': 1 << 19}, 4), ({'Record state': 512}, 3),
             ({'Record state': 1 << 20}, 4),
             ({'Record state': 1 << 20, 'Depth reference': 'instrument'}, 3),
             ({'Cell state': np.nan}, 2), ({'Native status map': 'unknown'}, 2)]
    frame = pd.DataFrame([dict(base, **changes) for changes, _ in cases])
    assert qc.doppler_native_quality(frame).tolist() == [expected for _, expected in cases]
    checks.append('DCPS native quality: warnings, invalidity, signed words, missing status and AutoBeam')

    times = pd.date_range('2026-01-01', periods=2, freq='h')
    rows = []
    for column, direction in (('A', 8.125), ('B', 343.331)):
        for timestamp in times:
            rows.append({'Datetime': timestamp, 'Site': 'selected', 'Column': column, 'Cell': 0,
                         'Depth (m)': 5., 'Depth reference': 'surface',
                         'Horizontal speed (cm/s)': 10., 'Direction (deg)': direction,
                         'East speed (cm/s)': 2., 'North speed (cm/s)': 9., 'Flag_cur': 1})
    frame = pd.DataFrame(rows)
    unchanged = frame.copy(deep=True)
    with tempfile.TemporaryDirectory() as folder:
        retired = Path(folder) / '01_previous_column' / 'Current profile (time x depth).svg'
        retired.parent.mkdir()
        retired.write_text('obsolete separated plot')
        note = Path(folder) / 'operator-note.txt'
        note.write_text('retain')
        figures = []
        paths = view.plot_doppler_panels(frame, folder, label='Example', figures=figures)
        assert len(paths) == len(figures) == 3
        assert not retired.exists() and note.read_text() == 'retain'
        # Historical display compatibility, explicitly requested by the owner:
        # v14.0 averages coincident coordinates. This is not a native-cell truth
        # assertion; the underlying qualified table must remain unchanged.
        actual = np.asarray(figures[0].axes[1].collections[0].get_array())
        assert np.allclose(actual, (8.125 + 343.331) / 2.)
        assert all(fig._qcs_v140_doppler for fig in figures)
        assert figures[0]._suptitle.get_text() == 'Current profile - Example'
        for fig in figures:
            view.plt.close(fig)
        pd.testing.assert_frame_equal(frame, unchanged)
        paths = view.plot_doppler_panels(frame, folder,
                                        settings={'depthAxisMin': 6, 'depthAxisMax': 7})
        assert paths == [] and not list(Path(folder).rglob('*.svg'))
        assert note.read_text() == 'retain'
    checks.append('DCPS v14.0 display: historical grouping, unchanged source rows and obsolete-panel cleanup')
    with tempfile.TemporaryDirectory() as folder:
        profile = pd.concat([frame, frame.assign(**{'Depth (m)': 10.})], ignore_index=True)
        comparison = pd.concat([profile, profile.assign(Site='second')], ignore_index=True)
        figures = []
        paths = view.plot_doppler_across_sites(comparison, folder, ['selected', 'second'], figures=figures)
        assert len(paths) == len(figures) == 1
        assert len(figures[0].axes[0].lines) == 2 and figures[0]._qcs_v140_doppler
        assert {line.get_label() for line in figures[0].axes[0].lines} == {'selected', 'second'}
        for line in figures[0].axes[0].lines:
            assert np.array_equal(line.get_ydata(), [5., 10.])
            assert np.array_equal(line.get_xdata(), [10., 10.])
        view.plt.close(figures[0])
    checks.append('DCPS v14.0 comparison: one temporal mean profile per site')
    with tempfile.TemporaryDirectory() as folder:
        no_depth = pd.DataFrame({'Depth (m)': [np.nan] * 3,
                                 'Temperature (degC)': [26.1523, 26.1522, 26.1515]})
        figures_before = view.plt.get_fignums()
        view.plot_variable_profile(no_depth, no_depth, 'Temperature (degC)', folder, {}, False)
        assert not list(Path(folder).iterdir()) and view.plt.get_fignums() == figures_before
    checks.append('Scalar profile: missing depth preserves the table without inventing a vertical panel')
    return checks

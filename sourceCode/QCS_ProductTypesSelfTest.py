"""Collection routing regression cases; pandas/NumPy/Matplotlib QCS runtime."""
from pathlib import Path
import tempfile

import pandas as pd

import QCS_Curated as curated
import QCS_DataHandler as data
from QCS_ProductTypes import (CATEGORIES, TYPE_COLUMN, annotate_scalar_collection,
                              collection_rows, qualified_scalar_type)


def run():
    checks = []
    with tempfile.TemporaryDirectory() as folder:
        root = Path(folder)
        site = root / 'SEAGUARD/qualified/2025S1/TEST'
        site.mkdir(parents=True)
        profile = site / 'TEST_2025S1_SEAGUARD_PERFIL_QLF.csv'
        mooring = site / 'TEST_2025S1_SEAGUARD_FUNDEIO_QLF.csv'
        original = pd.DataFrame({'Datetime': pd.date_range('2025-01-01', periods=3, freq='min'),
            'Site': 'TEST', 'Depth (m)': [1., 5., 10.], 'Temperature (degC)': [27., 26., 25.],
            'Salinity (PSU)': 36., 'Flag': 11111, 'Flag_T': 1})
        original.to_csv(profile, index=False)
        original.assign(Datetime=original.Datetime + pd.Timedelta(days=2)).to_csv(mooring, index=False)
        catalog, _ = curated.discover_qualified_corpus(root)
        assert catalog.instrument.tolist() == ['Seaguard (Mooring)', 'Seaguard (Profile)']
        assert len(curated.select_catalog(catalog, ['Seaguard (Profile)'], ['TEST'], [2025])) == 1
        tables, included, summary, _ = curated.build_curated_tables(catalog,
            list(CATEGORIES), ['TEST'], [2025])
        assert list(tables) == ['Seaguard (Mooring)', 'Seaguard (Profile)']
        assert summary['rows'] == 6 and included['Selected rows'].sum() == 6
        assert tables['Seaguard (Profile)'][TYPE_COLUMN].eq('TSCP Profile').all()
        book = root / 'curated.xlsx'
        curated.write_curated_workbook(book, root, tables, included, summary)
        assert data.curated_workbook_instruments(book) == ['Seaguard']
        try:
            data.build_database('Seaguard', file_list=[str(book)])
        except ValueError as exc:
            assert 'select a Seaguard collection sheet' in str(exc)
        else:
            raise AssertionError('Ambiguous scalar sheet silently selected')
        loaded, _ = data.build_database('Seaguard', file_list=[str(book)], sheet_name='Seaguard (Profile)')
        assert len(loaded) == 3 and loaded[TYPE_COLUMN].eq('TSCP Profile').all()
        assert loaded['Source file'].eq(profile.name).all()
        assert data.detect_known_qualified_instrument(loaded.assign(**{'Luminosity (lux)': float('nan')})) == 'Seaguard'
        checks.append('Curated scalar collections: separate facets/sheets, exact handoff and no implicit mixing')

        legacy = root / 'legacy.xlsx'
        old = pd.concat(list(tables.values()), ignore_index=True).drop(columns=TYPE_COLUMN)
        with pd.ExcelWriter(legacy) as writer:
            old.to_excel(writer, sheet_name='Seaguard', index=False)
            included.to_excel(writer, sheet_name='Included products', index=False)
            pd.DataFrame({'Field': ['Structure'], 'Value': ['legacy']}).to_excel(writer, sheet_name='Read me', index=False)
        recovered, _ = data.build_database('Seaguard', file_list=[str(legacy)])
        assert len(recovered) == 6
        assert len(collection_rows(recovered, 'TSCP Profile')) == 3
        assert collection_rows(recovered, 'TSCP Profile')['Source file'].eq(profile.name).all()
        unknown = annotate_scalar_collection(original, root / 'arbitrary.csv')
        assert unknown[TYPE_COLUMN].eq('Unknown').all()
        assert qualified_scalar_type(root / 'arbitrary.csv') is None
        checks.append('Legacy curated sheets: recover explicit source collection, preserve mixed rows and unknown identity')

        (site / 'provenance.txt').write_text(profile.stem + '\n    tipo : FUNDEIO\n\n')
        try:
            qualified_scalar_type(profile)
        except ValueError as exc:
            assert 'conflicts' in str(exc)
        else:
            raise AssertionError('Conflicting collection provenance was ignored')
        pd.testing.assert_frame_equal(pd.read_csv(profile).drop(columns='Datetime'), original.drop(columns='Datetime'))
        checks.append('Collection provenance: conflicting metadata refused, input measurements unchanged')

    import matplotlib.pyplot as plt
    from matplotlib.backend_bases import ResizeEvent
    import QCS_DataView as view
    fig, axes = plt.subplots(2, 1)
    bar = fig.colorbar(axes[0].imshow([[1., 2.]]), ax=axes[0])
    slot = fig.colorbar(axes[1].imshow([[1., 2.]]), ax=axes[1]).ax
    slot.set_visible(False)
    wheel = view._direction_compass(fig, slot, axes[1], 'twilight')
    view.align_compass_west(fig, wheel, bar.ax)
    for size in [(12., 8.), (14.5, 9.)]:
        fig.set_size_inches(*size)
        fig.canvas.callbacks.process('resize_event', ResizeEvent('resize_event', fig.canvas))
        fig.canvas.draw()
        west = next(t for t in wheel.get_xticklabels() if t.get_text() == 'W')
        wb = west.get_window_extent(fig.canvas.get_renderer())
        bb = bar.ax.get_window_extent(fig.canvas.get_renderer())
        assert abs((wb.x0+wb.x1-bb.x0-bb.x1)/2) < 1.
    plt.close(fig)
    checks.append('Doppler direction key: W centre aligns with speed bar after resizing')
    return checks

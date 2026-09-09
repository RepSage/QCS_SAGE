"""Qualified collection identity, separate from the three measurement layouts."""
from pathlib import Path
import re

import pandas as pd

CATEGORIES = {
    'Seaguard (Mooring)': ('Seaguard', 'TSCP Mooring'),
    'Seaguard (Profile)': ('Seaguard', 'TSCP Profile'),
    'Seaguard (Doppler)': ('Doppler', 'TSCP Doppler'),
    'HOBO': ('HOBO', 'HOBO'),
}
UNKNOWN_CATEGORY = 'Seaguard (Unspecified)'
SHEET_TYPES = dict(CATEGORIES, **{
    'Seaguard': ('Seaguard', None), 'Doppler': ('Doppler', 'TSCP Doppler'),
    UNKNOWN_CATEGORY: ('Seaguard', None),
})
SCALAR_TYPES = ('TSCP Mooring', 'TSCP Profile')
TYPE_COLUMN = 'Collection type'


def scalar_type_from_name(name):
    """Read the explicit collection token in a QCS qualified-product name."""
    match = re.search(r'(?:SEAGUARD|TSCP)_(FUNDEIO|PERFIL)(?:_|$)', str(name).upper())
    return {'FUNDEIO': 'TSCP Mooring', 'PERFIL': 'TSCP Profile'}.get(match[1]) if match else None


def qualified_scalar_type(path):
    """Exact product provenance plus its explicit name; conflicts are errors."""
    path = Path(path)
    named = scalar_type_from_name(path.stem)
    sidecar = path.parent / 'provenance.txt'
    if not sidecar.is_file():
        return named
    blocks = sidecar.read_text(encoding='utf-8').split('\n\n')
    exact = [block for block in blocks if block.splitlines()
             and block.splitlines()[0].strip() == path.stem]
    if len(exact) > 1:
        raise ValueError('Ambiguous collection provenance for %s.' % path.name)
    if not exact:
        return named
    match = re.search(r'^\s*tipo\s*:\s*(\S+)\s*$', exact[0], re.MULTILINE)
    proven = {'FUNDEIO': 'TSCP Mooring', 'PERFIL': 'TSCP Profile'}.get(match[1].upper()) if match else None
    if proven and named and proven != named:
        raise ValueError('Collection type conflicts between provenance and product name: %s.' % path.name)
    return proven or named


def annotate_scalar_collection(frame, path, sheet=None):
    """Retain/recover collection metadata without changing measurement fields."""
    result = frame.copy()
    declared = SHEET_TYPES.get(sheet, (None, None))[1]
    proven = declared or qualified_scalar_type(path)
    if TYPE_COLUMN in result:
        values = result[TYPE_COLUMN].fillna('Unknown').astype(str)
        invalid = set(values) - set(SCALAR_TYPES) - {'Unknown'}
        if invalid or (proven and values.isin(SCALAR_TYPES).any() and
                       not values[values.isin(SCALAR_TYPES)].eq(proven).all()):
            raise ValueError('Collection metadata conflicts in %s.' % Path(path).name)
    else:
        values = pd.Series('Unknown', index=result.index)
    if proven:
        values = values.replace('Unknown', proven)
    elif 'Source file' in result:
        # Old curated workbooks retain the exact qualified source names.
        recovered = result['Source file'].map(scalar_type_from_name).fillna('Unknown')
        values = values.where(values.ne('Unknown'), recovered)
    result[TYPE_COLUMN] = values
    return result


def collection_rows(frame, data_type):
    """Select known collections in legacy mixed sheets; unknown-only is manual."""
    if data_type not in SCALAR_TYPES or TYPE_COLUMN not in frame:
        return frame
    known = frame[TYPE_COLUMN].isin(SCALAR_TYPES)
    if not known.any():
        return frame  # the explicit editable type choice applies to this table
    return frame[frame[TYPE_COLUMN].eq(data_type)]

import os
import re
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.widgets import Button, RectangleSelector
import QCS_Theme as _theme

# Software version: single source of truth, shown in window titles,
# 'About' dialogs and in the 'QCS version' column of qualified files.
# Update ONLY here when releasing a new version.
QCS_VERSION = 'v12.3'

################################# Description ##################################
# QCS_DataHandler consists in a series of function to open and handle data files
# such as exported data from sensors and excel tables (.xls/.xlsx). Everything
# related to data formats and standardization, unit conversion, input and output
# files, etc.
################################################################################

# Search functions

# ---------------------------------------------------------------------------
# AADI Seaguard II raw binary sessions (Data000.bin, format 'AADIBXML1.0').
# The file is SELF-DESCRIBING: a header points to (1) a plain-XML template of
# one full record (sensor names, parameter names, units, types) and (2) a tag
# dictionary assigning a numeric id to every XML element; the data section is a
# sequence of records framed by a sync marker, each a list of (id, value)
# pairs. Decoding was validated against the instrument's own CSV export of a
# real deployment: 1550/1550 records, 12/12 compared columns identical within
# the CSV's print precision.
# ---------------------------------------------------------------------------

_AADI_MAGIC = b'AADIBXML'
_AADI_SYNC = b'\x11\x22\x33\x44\x55\x66\x77\x88'
_AADI_TICK0 = pd.Timestamp('0001-01-01').to_pydatetime()


def _decode_aadi_bin(file_path, max_records=None):
    """Decodes ONE DataNNN.bin file into a DataFrame with the same column
    names as the instrument's CSV export ('Record Time', 'Record Number',
    'Pressure[kPa]', ...), so the standard column mapping applies unchanged.
    Times are GMT, as in the export (the GMT-3 correction stays an option).

    max_records stops after that many records - the Selection summary asks for
    a handful just to read the sampling interval (v12.1) and must not pay for
    a whole mooring."""
    import struct
    import datetime as _dt
    with open(file_path, 'rb') as f:
        if max_records is None:
            blob = f.read()
        else:
            # A peek reads the header, the template and the dictionary (their
            # offsets live in the first 0x40 bytes) plus half a megabyte of
            # records - thousands of them, far more than a peek asks for.
            # Reading the whole file would make the PREVIEW cost grow with the
            # deployment: measured 1 s for a 10 MB session over the share.
            head = f.read(0x40)
            if head.startswith(_AADI_MAGIC) and len(head) >= 0x38:
                t_off, _a, _b, _c, t_len, d_off, d_len = struct.unpack_from(
                    '<7I', head, 0x1c)
                need = max(t_off + t_len, d_off + d_len) + 512 * 1024
            else:
                need = 1 << 20
            f.seek(0)
            blob = f.read(need)
    if not blob.startswith(_AADI_MAGIC):
        raise ValueError("'%s' is not an AADI binary session file (missing "
                         "AADIBXML header)." % os.path.basename(file_path))
    tpl_off, _, _, _, tpl_len, dict_off, dict_len = struct.unpack_from('<7I', blob, 0x1c)
    template = blob[tpl_off:tpl_off + tpl_len].decode('utf-8', errors='replace')
    dictionary = blob[dict_off:dict_off + dict_len]

    # tag dictionary: 13 bytes (u16 id, u16 parent, 3B pad, u32 type, 2B pad)
    # followed by the ASCII element name
    entries = {}
    value_ids = []
    for m in re.finditer(rb'[A-Za-z][A-Za-z0-9_]{3,}', dictionary):
        if m.start() < 13:
            continue
        ident, parent = struct.unpack_from('<HH', dictionary, m.start() - 13)
        type_code = struct.unpack_from('<I', dictionary, m.start() - 6)[0]
        name = m.group().decode()
        entries[ident] = (name, parent, type_code)
        if name == 'Value':
            value_ids.append(ident)

    # the k-th dictionary 'Value' id corresponds to the k-th Point in template
    # document order; column name = PointDescr[Unit], as in the CSV export.
    # Points may sit OUTSIDE the <SensorData> blocks (device housekeeping such as
    # 'Input Voltage' and 'Memory Used'), yet they still occupy a Value slot in
    # the tag dictionary - so every <Point> is taken, not only those nested in a
    # <SensorData>. Attribute order is not assumed (Descr/Unit read individually).
    columns = []
    for point in re.finditer(r'<Point\b[^>]*>', template):
        tag = point.group(0)
        descr = re.search(r'\bDescr="([^"]*)"', tag)
        unit = re.search(r'\bUnit="([^"]*)"', tag)
        columns.append('%s[%s]' % (descr.group(1) if descr else '',
                                   unit.group(1) if unit else ''))
    if len(columns) != len(value_ids):
        raise ValueError('AADI reader (%s): %d parameters in the template but %d value '
                         'slots in the tag dictionary - unsupported layout variant '
                         '(e.g. DCPS/Doppler current profiler).'
                         % (os.path.basename(file_path), len(columns), len(value_ids)))
    # duplicate parameter names (e.g. each sensor's own Temperature) get the
    # same .1/.2 suffixes pandas produces when reading the CSV export
    seen = {}
    for i, name in enumerate(columns):
        if name in seen:
            seen[name] += 1
            columns[i] = '%s.%d' % (name, seen[name])
        else:
            seen[name] = 0
    vid2col = dict(zip(value_ids, columns, strict=True))

    rows = []
    pos = blob.find(_AADI_SYNC)
    while pos != -1:
        q = pos + len(_AADI_SYNC)
        _rec_len, n_fields = struct.unpack_from('<II', blob, q)
        q += 8
        row = {}
        try:
            for _ in range(n_fields):
                ident = struct.unpack_from('<H', blob, q)[0]
                q += 2
                name, parent, type_code = entries[ident]
                if type_code == 0x28:                     # timestamp, .NET ticks
                    ticks = struct.unpack_from('<q', blob, q)[0]
                    q += 8
                    if name == 'Time' and parent != 1:    # the record's own time
                        row['Record Time'] = pd.Timestamp(
                            _AADI_TICK0 + _dt.timedelta(microseconds=ticks // 10))
                elif ident in vid2col:                    # float32 parameter value
                    row[vid2col[ident]] = struct.unpack_from('<f', blob, q)[0]
                    q += 4
                else:                                     # StatusCode / RecordNumber
                    value = struct.unpack_from('<i', blob, q)[0]
                    q += 4
                    if name == 'RecordNumber':
                        row['Record Number'] = value
        except (KeyError, struct.error) as e:
            raise ValueError('AADI reader (%s): corrupted record at byte %d (%s).'
                             % (os.path.basename(file_path), pos, e)) from e
        rows.append(row)
        if max_records is not None and len(rows) >= max_records:
            break
        pos = blob.find(_AADI_SYNC, pos + 1)
    if not rows:
        raise ValueError('AADI reader (%s): no data records found.'
                         % os.path.basename(file_path))
    return pd.DataFrame(rows, columns=['Record Time', 'Record Number'] + columns)


def read_seaguard_bin(file_path):
    """Reads a Seaguard II raw binary session: the selected DataNNN.bin plus any
    sibling DataNNN.bin files of the same session folder, concatenated in time
    order. Returns the CSV-export-equivalent DataFrame."""
    folder = os.path.dirname(file_path)
    selected = os.path.basename(file_path)
    siblings = sorted(f for f in os.listdir(folder)
                      if re.fullmatch(r'Data\d+\.bin', f, re.IGNORECASE))
    if not siblings:
        siblings = [selected]
    # 'Every DataNNN.bin of the folder is a part of this session' holds for a
    # real session folder, and NOT for a folder that merely happens to hold
    # binaries of different deployments (a Desktop, a staging folder). A DCPS
    # session among scalar ones cannot be a continuation of them: decoding it
    # as one aborted the whole qualification with 'unsupported layout variant',
    # naming a file the operator never selected (owner, v12.3).
    if len(siblings) > 1:
        selected_is_doppler = is_seaguard_doppler(file_path)
        kept, dropped = [], []
        for name in siblings:
            if name.lower() == selected.lower():
                kept.append(name)
            elif is_seaguard_doppler(os.path.join(folder, name)) == selected_is_doppler:
                kept.append(name)
            else:
                dropped.append(name)
        if dropped:
            print('Warning: %d file(s) in this folder belong to a different '
                  'instrument session and were NOT merged into %s: %s. Keep one '
                  'deployment per folder if they should be read together.'
                  % (len(dropped), selected, ', '.join(dropped)))
        siblings = kept
    parts = [_decode_aadi_bin(os.path.join(folder, f)) for f in siblings]
    if len(parts) > 1:
        print('Info: %d binary files of the session read together (%s).'
              % (len(parts), ', '.join(siblings)))
    frame = pd.concat(parts, ignore_index=True)
    frame = frame.sort_values('Record Time', kind='stable')
    frame.index = np.arange(len(frame))
    print('Info: AADI binary session decoded: %d records, %s to %s.'
          % (len(frame), frame['Record Time'].min(), frame['Record Time'].max()))
    return frame


# ---------------------------------------------------------------------------
# A Seaguard cast/deployment can be split into several sensor-GROUP folders that
# sit side by side (named '<serial>-<groupindex>-<start-timestamp>Z'): the
# current standard protocol logs all sensors together in one synchronous group
# (plus a separate Doppler group), but older deployments split the sensors into
# groups sampled at DIFFERENT rates (e.g. CTD 2 s, pH/optical 10 s, PAR 5 s) over
# the same time window. To qualify a deployment as one record, the groups are
# merged in time: the finest group is the master axis and the slower groups are
# linearly interpolated onto it (same approach as the dissolved-CO2 merge).
# Doppler/DCPS current-profiler groups are skipped - QCS qualifies scalar water
# properties, not current velocity; the raw .bin stays archived.
# ---------------------------------------------------------------------------

def _merge_sensor_groups(groups):
    """Aligns sensor groups (already decoded DataFrames) onto ONE time axis: the
    finest group (most records) is the master; every other group's parameter
    columns are linearly interpolated in time onto the master's 'Record Time'.
    A gap larger than 2x a group's own median interval is not bridged (NaN) and
    no value is extrapolated beyond a group's own coverage."""
    groups = sorted(groups, key=len, reverse=True)      # finest = most records
    master = groups[0].copy().reset_index(drop=True)
    master_t = master['Record Time'].values.astype('datetime64[ns]').astype('int64')
    for g in groups[1:]:
        g = g.sort_values('Record Time')
        gt = g['Record Time'].values.astype('datetime64[ns]').astype('int64')
        if len(gt) < 2:
            continue
        med = float(np.median(np.diff(gt)))             # median interval (ns)
        tol = 2.0 * med
        pos = np.searchsorted(gt, master_t)
        lo = np.clip(pos - 1, 0, len(gt) - 1)
        hi = np.clip(pos, 0, len(gt) - 1)
        gap = np.minimum(np.abs(master_t - gt[lo]), np.abs(master_t - gt[hi]))
        valid = (master_t >= gt[0]) & (master_t <= gt[-1]) & (gap <= tol)
        for col in g.columns:
            if col in ('Record Time', 'Record Number'):
                continue
            name = col
            k = 1
            while name in master.columns:               # keep cross-group names unique
                name = '%s.%d' % (col, k)
                k += 1
            vals = np.interp(master_t, gt, g[col].values.astype(float))
            vals[~valid] = np.nan
            master[name] = vals
    master = master.sort_values('Record Time', kind='stable')
    master.index = np.arange(len(master))
    return master


SESSION_FOLDER_RE = re.compile(
    r'(\d+-\d+)-(\d+)-(\d{4}-\d\d-\d\dT\d\d-\d\d-\d\d)')


def seaguard_cast_folders(file_path):
    """The sensor-group folders that belong to the SAME cast as `file_path`.

    A Seaguard session folder is named '<serial>-<group>-<start>Z'. The groups
    of one cast start close together (seconds to a couple of minutes apart -
    each group's logging begins at a slightly different instant, and the
    Doppler group can start a few minutes off), while different casts in the
    same folder are far apart, so a start-time gap larger than CAST_GAP opens a
    new cast. Anchoring on the SELECTED group's own start (the old 90 s window)
    missed groups when the selected one was the time outlier - picking the
    Doppler group made its sensor siblings invisible and the whole cast was
    lost.

    Returns (serial, [(start, folder_name), ...]) for the cast holding the
    selection, or (None, None) when the selection is not a session folder (a
    lone Data000.bin, an export). The deployment READER and the Selection
    summary both read the cast through this one function - the clustering rule
    lives here and nowhere else.
    """
    import datetime as _dt
    group_folder = os.path.dirname(file_path)
    parent = os.path.dirname(group_folder)
    sel_name = os.path.basename(group_folder)
    m = SESSION_FOLDER_RE.match(sel_name)
    if not m:
        return None, None
    serial = m.group(1)
    sessions = []
    for name in os.listdir(parent):
        mm = SESSION_FOLDER_RE.match(name)
        if not mm or mm.group(1) != serial:
            continue
        if os.path.exists(os.path.join(parent, name, 'Data000.bin')):
            sessions.append((_dt.datetime.strptime(mm.group(3),
                                                   '%Y-%m-%dT%H-%M-%S'), name))
    sessions.sort()
    CAST_GAP = 15 * 60
    clusters, cur = [], []
    for st, name in sessions:
        if cur and (st - cur[-1][0]).total_seconds() > CAST_GAP:
            clusters.append(cur)
            cur = []
        cur.append((st, name))
    if cur:
        clusters.append(cur)
    cast = next((c for c in clusters if any(n == sel_name for _, n in c)), None)
    if cast is None or len(cast) <= 1:
        return serial, None
    return serial, cast


# The BXML template at the head of every DataNNN.bin describes the session:
# <Device ID="5650-2104" ... SerialNo="2104">, the group's own
# <Data SessionID="5650-2104-0-2026-03-16T18-01-00.043Z" GroupDescr="FUNDEIO">
# and <SpecifiedInterval>60</SpecifiedInterval>. The session FOLDER name is
# built from the same values, which is why the folder route and this one agree.
_BXML_DEVICE_RE = re.compile(r'<Device[^>]*\bID="([^"]+)"')
_BXML_SESSION_RE = re.compile(
    r'<Data\b[^>]*\bSessionID="[^"]*?(\d{4}-\d\d-\d\dT\d\d-\d\d-\d\d)')
_BXML_INTERVAL_RE = re.compile(
    r'<SpecifiedInterval>\s*(\d+(?:\.\d+)?)\s*</SpecifiedInterval>')


def _read_aadi_template(file_path):
    """The BXML template at the head of a DataNNN.bin - the instrument's own
    description of the session. Two reads and no record decoding at all, so it
    costs the same for a 300 KB cast and for a 10 MB mooring."""
    import struct
    try:
        with open(file_path, 'rb') as f:
            head = f.read(0x40)
            if not head.startswith(_AADI_MAGIC) or len(head) < 0x38:
                return ''
            tpl_off, _a, _b, _c, tpl_len, _d, _e = struct.unpack_from('<7I', head, 0x1c)
            f.seek(tpl_off)
            return f.read(tpl_len).decode('utf-8', errors='replace')
    except Exception:
        return ''


def _specified_interval(template):
    """The sampling interval the instrument declares in its own template."""
    m = _BXML_INTERVAL_RE.search(template)
    if not m:
        return None
    value = float(m.group(1))
    return value if value > 0 else None


def _measure_bin_interval(file_path):
    """Median step of the first records of one DataNNN.bin, or None when the
    file cannot be decoded (a DCPS group raises - its layout is different).
    A preview must never be the thing that fails."""
    try:
        head = _decode_aadi_bin(file_path, max_records=60)
        times = pd.to_datetime(head['Record Time']).dropna()
    except Exception:
        return None
    if len(times) < 3:
        return None
    step = times.diff().dropna().median().total_seconds()
    return step if step > 0 else None


def _count_bin_parts(folder):
    try:
        return len([f for f in os.listdir(folder)
                    if re.fullmatch(r'Data\d+\.bin', f, re.IGNORECASE)]) or 1
    except OSError:
        return 1


def _peek_seaguard_header(file_path):
    """Selection summary for a Data000.bin that is NOT inside a
    '<serial>-<group>-<start>' session folder - a file copied out of the
    archive, which the reader accepts (read_seaguard_deployment falls back to
    the single file) but which the summary used to describe with three dashes
    (owner, 2026-08-19). Everything comes from the file's own BXML template, so
    it also answers for a DCPS session, whose records this module cannot
    decode."""
    import datetime as _dt
    template = _read_aadi_template(file_path)
    if not template:
        return {}
    device = _BXML_DEVICE_RE.search(template)
    session = _BXML_SESSION_RE.search(template)
    if not (device and session):
        return {}
    out = {'serial': device.group(1),
           'start': _dt.datetime.strptime(session.group(1), '%Y-%m-%dT%H-%M-%S'),
           'groups': 1,          # a lone file knows nothing about its siblings
           'parts': _count_bin_parts(os.path.dirname(file_path)),
           'interval_s': (_measure_bin_interval(file_path)
                          or _specified_interval(template))}
    return out


def peek_seaguard_session(file_path):
    """What a Seaguard selection says about itself WITHOUT decoding anything.

    The folder names carry the serial and the deployment start, and a directory
    listing says how many sensor groups the cast has and how many DataNNN.bin
    parts the selected group was split into - enough for the Selection summary,
    for the price of a listdir (decoding a long mooring just to preview it
    would freeze the window). A file that is NOT inside a session folder falls
    back to its own BXML header, which carries the same facts (v12.1, header
    fallback 2026-08-19).
    """
    group_folder = os.path.dirname(file_path)
    m = SESSION_FOLDER_RE.match(os.path.basename(group_folder))
    if not m:
        return _peek_seaguard_header(file_path)
    import datetime as _dt
    serial, cast = seaguard_cast_folders(file_path)
    parts = [f for f in os.listdir(group_folder)
             if re.fullmatch(r'Data\d+\.bin', f, re.IGNORECASE)]
    out = {'serial': m.group(1),
           'start': _dt.datetime.strptime(m.group(3), '%Y-%m-%dT%H-%M-%S'),
           'groups': len(cast) if cast else 1,
           'parts': len(parts) or 1,
           'interval_s': None}
    # The sampling interval is NOT in the folder names: it takes decoding,
    # but only of the first records of each sensor group. The FINEST group is
    # the one to report, because that is the axis the deployment reader merges
    # everything onto - reporting the selected group's own 10 s while the
    # qualified sheet carries 5 s rows would be a lie. A DCPS group raises
    # here (its own layout): skipped, never fatal - a preview must not be the
    # thing that fails.
    steps = []
    folders = [os.path.join(os.path.dirname(os.path.dirname(file_path)), name)
               for _st, name in (cast or [])] or [group_folder]
    for folder in folders:
        step = _measure_bin_interval(os.path.join(folder, 'Data000.bin'))
        if step:
            steps.append(step)
    # nothing decodable (a DCPS-only selection): the instrument declares its
    # own interval in the template, and reading that costs no decoding at all
    out['interval_s'] = (min(steps) if steps
                         else _specified_interval(_read_aadi_template(file_path)))
    return out


def read_seaguard_deployment(file_path):
    """Reads a whole Seaguard deployment: the selected sensor-group folder plus
    any sibling sensor-group folders of the SAME cast (same instrument serial and
    start time, within a small tolerance), merged onto one time axis by
    _merge_sensor_groups. Doppler/DCPS groups are skipped. Falls back to the
    single-folder read when the folder is not a '<serial>-<group>-<timestamp>'
    session folder (e.g. a lone Data000.bin)."""
    parent = os.path.dirname(os.path.dirname(file_path))
    _serial, cast = seaguard_cast_folders(file_path)
    if cast is None:
        return read_seaguard_bin(file_path)
    siblings = [(name, os.path.join(parent, name, 'Data000.bin')) for _, name in cast]
    if len(siblings) <= 1:
        return read_seaguard_bin(file_path)
    groups, skipped = [], []
    for name, path in siblings:
        try:
            groups.append(read_seaguard_bin(path))
        except ValueError as exc:                              # e.g. DCPS/Doppler
            skipped.append('%s (%s)' % (name, exc))
    if skipped:
        print('Info: %d sensor group(s) skipped in the deployment: %s'
              % (len(skipped), '; '.join(skipped)))
    groups = [g for g in groups if g is not None and len(g)]
    if not groups:
        raise ValueError('No readable sensor group in the deployment %r.' % parent)
    if len(groups) == 1:
        return groups[0]
    merged = _merge_sensor_groups(groups)
    print('Info: %d sensor groups merged onto the finest time axis: %d records, '
          '%d columns.' % (len(groups), len(merged), merged.shape[1]))
    return merged


# ---------------------------------------------------------------------------
# DCPS / Doppler current-profiler sessions (Aanderaa DCPS on the Seaguard II).
# Same AADIBXML container as the scalar sessions, but a much richer record:
# - the tag dictionary must be parsed SEQUENTIALLY (entry = 13-byte prefix,
#   name, NUL, 3 zero bytes); the regex scan used for scalar files corrupts on
#   dictionaries this large (payload bytes that look like ASCII swallow names).
# - value slots are the template <Point>s that CONTAIN a <Value/>; the
#   self-closing <Point/>s inside <CellAttributes> only DEFINE the per-cell
#   parameters (ID -> Descr/Unit), and each <Cell Index=k> holds bare Points
#   referencing them. k-th Point-parented dictionary 'Value' <-> k-th slot.
# - Value payloads come typed: 0x14 float32 (4 B), 0x04 int32 (4 B),
#   0x02 int16 (2 B - Air Detect, Ping Count, Cell States); one extra 'Value'
#   belongs to the <Vector> element (EventReg flags): u32 dim + dim x int32.
# - rec_len counts from the SYNC marker and the record ends with a 4-char
#   checksum, so records are walked BY BYTES, not by the field count.
# Decoding validated against the instrument's own CSV export (CFRIO1
# 22.03.2021): 15,948 value comparisons across 12 records, 100% of the
# measurement parameters identical (only export-side blanks differ).
# ---------------------------------------------------------------------------

def _parse_aadi_dictionary(dictionary):
    """Sequentially parses the tag dictionary. Returns (entries, value_ids):
    entries[id] = (name, parent_id, type_code); value_ids = 'Value' entries in
    dictionary order."""
    import struct
    entries = {}
    value_ids = []
    p = 0
    while p + 13 < len(dictionary):
        ident, parent = struct.unpack_from('<HH', dictionary, p)
        type_code = struct.unpack_from('<I', dictionary, p + 7)[0]
        q = dictionary.find(b'\x00', p + 13)
        if q < 0:
            break
        name = dictionary[p + 13:q].decode('ascii', errors='replace')
        if not name or not re.match(r'^[A-Za-z][A-Za-z0-9_]*$', name):
            break
        entries[ident] = (name, parent, type_code)
        if name == 'Value':
            value_ids.append(ident)
        p = q + 4                       # NUL + 3 trailing zero bytes
    return entries, value_ids


def is_seaguard_doppler(file_path):
    """True when the .bin session belongs to a DCPS / Doppler current profiler
    (template SensorData named 'DCPS ...' / product 'Doppler Current Profiler')."""
    import struct
    try:
        with open(file_path, 'rb') as f:
            blob = f.read(64 * 1024)
        if not blob.startswith(_AADI_MAGIC):
            return False
        tpl_off, _, _, _, tpl_len, _, _ = struct.unpack_from('<7I', blob, 0x1c)
        head = blob[tpl_off:tpl_off + min(tpl_len, 4096)].decode('utf-8', 'replace')
        return bool(re.search(r'Descr="DCPS|Doppler Current Profiler', head))
    except Exception:
        return False


def _decode_dcps_bin(file_path):
    """Decodes ONE DCPS DataNNN.bin. Returns (records, slots, columns):
    records = [(Timestamp, {slot_index: value}, vector_or_None), ...];
    slots[i] = (descr, unit, column_descr, cell_index, depth_m) with
    column_descr/cell None for the record-level (non-cell) parameters."""
    import struct
    import datetime as _dt
    import xml.etree.ElementTree as ET
    with open(file_path, 'rb') as f:
        blob = f.read()
    if not blob.startswith(_AADI_MAGIC):
        raise ValueError("'%s' is not an AADI binary session file." % os.path.basename(file_path))
    tpl_off, _, _, _, tpl_len, dict_off, dict_len = struct.unpack_from('<7I', blob, 0x1c)
    template = blob[tpl_off:tpl_off + tpl_len].decode('utf-8', 'replace')
    entries, value_ids = _parse_aadi_dictionary(blob[dict_off:dict_off + dict_len])

    def parent_name(ident):
        ent = entries.get(ident)
        par = entries.get(ent[1]) if ent else None
        return par[0] if par else ''

    # template: value slots in document order, with Column/Cell context
    tpl = template[:template.rfind('</Device>') + len('</Device>')]
    root = ET.fromstring(tpl)

    def local(el):
        return el.tag.split('}')[-1]

    slots = []
    columns = []                        # (descr, start, cellsize, numcells)

    def cell_defs(column_el):
        defs = {}
        for ca in column_el:
            if local(ca) == 'CellAttributes':
                for pt in ca:
                    if local(pt) == 'Point':
                        defs[pt.attrib.get('ID')] = (pt.attrib.get('Descr', '?'),
                                                     pt.attrib.get('Unit', ''))
        return defs

    def collect(el, col=None, cell=None, defs=None):
        tag = local(el)
        if tag == 'Column':
            col = (el.attrib.get('Descr', '?'),
                   float(el.attrib.get('ColumnStart', 0) or 0),
                   float(el.attrib.get('CellSize', 0) or 0))
            columns.append((col[0], col[1], col[2], int(el.attrib.get('NumCells', 0) or 0)))
            defs = cell_defs(el)
        elif tag == 'Cell':
            cell = int(el.attrib.get('Index', -1))
        if tag == 'Point' and any(local(c) == 'Value' for c in el):
            if el.attrib.get('Descr') is not None:
                slots.append((el.attrib.get('Descr'), el.attrib.get('Unit', ''),
                              None, None, None))
            else:
                d, u = (defs or {}).get(el.attrib.get('ID'), ('?', ''))
                depth = (col[1] + col[2] * (cell + 0.5)) if col else None
                slots.append((d, u, col[0] if col else None, cell, depth))
        for ch in el:
            collect(ch, col, cell, defs)
    collect(root)

    point_values = [i for i in value_ids if parent_name(i) == 'Point']
    if len(point_values) != len(slots):
        raise ValueError('DCPS reader (%s): %d value ids vs %d template slots - '
                         'unsupported layout.' % (os.path.basename(file_path),
                                                  len(point_values), len(slots)))
    vid2slot = dict(zip(point_values, range(len(slots)), strict=True))

    records = []
    def walk_record(pos, vec_dim_size):
        """Walks one record. Returns (rt, vals, vector) when the fields land
        EXACTLY on the checksum boundary, else None."""
        q = pos + 8
        rec_len, _nf = struct.unpack_from('<II', blob, q)
        q += 8
        field_end = pos + rec_len - 4          # 4-char checksum closes the record
        if field_end > len(blob):
            return None
        rt = None
        vals = {}
        vector = None
        while q + 2 <= field_end:
            ident = struct.unpack_from('<H', blob, q)[0]
            q += 2
            ent = entries.get(ident)
            if ent is None:
                return None
            name, parent, tc = ent
            if name == 'Value' and parent_name(ident) == 'Vector':
                # the element-count prefix is u32 on most deployments but u16
                # on some (same type code) - the size is detected per file by
                # requiring the walk to land exactly on the record boundary
                if vec_dim_size == 2:
                    dim = struct.unpack_from('<H', blob, q)[0]
                else:
                    dim = struct.unpack_from('<I', blob, q)[0]
                q += vec_dim_size
                if dim > 64:
                    return None
                vector = [struct.unpack_from('<i', blob, q + 4 * j)[0] for j in range(dim)]
                q += 4 * dim
            elif tc == 0x28:                    # 8-byte .NET ticks
                ticks = struct.unpack_from('<q', blob, q)[0]
                q += 8
                if name == 'Time' and parent != 1:
                    rt = pd.Timestamp(_AADI_TICK0 + _dt.timedelta(microseconds=ticks // 10))
            elif tc == 0x02:                    # 2-byte int16
                v = struct.unpack_from('<h', blob, q)[0]
                q += 2
                if name == 'Value' and ident in vid2slot:
                    vals[vid2slot[ident]] = float(v)
            else:                               # 4-byte float32 / int32
                raw = blob[q:q + 4]
                q += 4
                if name == 'Value' and ident in vid2slot:
                    si = vid2slot[ident]
                    vals[si] = (struct.unpack('<f', raw)[0] if tc == 0x14
                                else float(struct.unpack('<i', raw)[0]))
        if rt is None or q != field_end:
            return None
        return rt, vals, vector

    vec_dim_size = None                        # detected on the first record
    pos = blob.find(_AADI_SYNC)
    while pos != -1:
        if vec_dim_size is None:
            got = walk_record(pos, 4)
            if got is not None:
                vec_dim_size = 4
            else:
                got = walk_record(pos, 2)
                if got is not None:
                    vec_dim_size = 2
        else:
            got = walk_record(pos, vec_dim_size)
        if got is not None:
            records.append(got)
        pos = blob.find(_AADI_SYNC, pos + 1)
    if not records:
        raise ValueError('DCPS reader (%s): no data records found.'
                         % os.path.basename(file_path))
    return records, slots, columns


# per-cell parameters kept in the tidy frame (descr -> output column name);
# everything else in the bin stays available in the raw file
_DCPS_CELL_PARAMS = [
    ('Horizontal Speed', 'Horizontal speed (cm/s)'),
    ('Direction', 'Direction (deg)'),
    ('North Speed', 'North speed (cm/s)'),
    ('East Speed', 'East speed (cm/s)'),
    ('Vertical Speed', 'Vertical speed (cm/s)'),
    ('SP Stdev Horizontal', 'Speed stdev (cm/s)'),
    ('Strength', 'Signal strength (dB)'),
    ('Cell State1', 'Cell state'),
]
# record-level context repeated on every cell row
_DCPS_RECORD_PARAMS = [
    ('Heading', 'Heading (deg)'),
    ('Pitch', 'Pitch (deg)'),
    ('Roll', 'Roll (deg)'),
    ('Abs Tilt', 'Tilt (deg)'),
    ('Ping Count', 'Ping count'),
]


def read_seaguard_doppler(file_path):
    """Reads a DCPS / Doppler current-profiler session into a TIDY frame:
    one row per record x depth cell, with the current measurements, their
    native quality indicators (speed stdev, signal strength, cell state) and
    the record-level attitude context. Sibling DataNNN.bin files of the same
    session folder are read together, like the scalar reader."""
    folder = os.path.dirname(file_path)
    siblings = sorted(f for f in os.listdir(folder)
                      if re.fullmatch(r'Data\d+\.bin', f, re.IGNORECASE))
    if not siblings:
        siblings = [os.path.basename(file_path)]
    all_rows = []
    for fname in siblings:
        records, slots, columns = _decode_dcps_bin(os.path.join(folder, fname))
        # index slots per (column, cell) and record-level by descr
        rec_level = {}                  # descr -> slot index
        cell_level = {}                 # (column_descr, cell) -> {descr: slot}
        depths = {}                     # (column_descr, cell) -> depth
        for si, (d, _u, col, cell, depth) in enumerate(slots):
            if col is None:
                rec_level.setdefault(d, si)
            else:
                cell_level.setdefault((col, cell), {})[d] = si
                depths[(col, cell)] = depth
        for rt, vals, _vector in records:
            ctx = {out: vals.get(rec_level.get(d, -1)) for d, out in _DCPS_RECORD_PARAMS}
            for (col, cell), sl in sorted(cell_level.items()):
                row = {'Datetime': rt, 'Column': col, 'Cell': cell,
                       'Depth (m)': depths[(col, cell)]}
                row.update(ctx)
                for d, out in _DCPS_CELL_PARAMS:
                    si = sl.get(d)
                    row[out] = vals.get(si) if si is not None else np.nan
                all_rows.append(row)
    if not all_rows:
        raise ValueError('DCPS session %r has no current cells - the profile '
                         'output was disabled in this configuration (only '
                         'attitude/housekeeping parameters were logged).'
                         % os.path.basename(folder))
    frame = pd.DataFrame(all_rows)
    frame = frame.sort_values(['Datetime', 'Column', 'Cell'], kind='stable')
    frame.index = np.arange(len(frame))
    n_rec = frame['Datetime'].nunique()
    n_cells = frame.groupby('Datetime').size().max()
    print('Info: DCPS session decoded: %d records x %d cells = %d rows, %s to %s.'
          % (n_rec, n_cells, len(frame), frame['Datetime'].min(), frame['Datetime'].max()))
    return frame


# ---------------------------------------------------------------------------
# Dissolved-CO2 logger (separate instrument). Export: comma CSV with the header
# line repeated on every logger restart; date split into Year..Second columns;
# the value imported is 'Corrected disolved CO2 (PPM)' (the device's own
# spelling). The logger samples at its own rate (~2 min), different from the
# Seaguard's, so the merge interpolates in time.
# ---------------------------------------------------------------------------

def read_co2_file(file_path):
    """Reads the dissolved-CO2 logger export. Returns (DataFrame with
    ['Datetime', 'CO2 Level (ppm)'] sorted in time, messages)."""
    msgs = []
    header = None
    rows = []
    n_headers = 0
    n_badrows = 0
    with open(file_path, encoding='utf-8', errors='replace') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            if line.lower().startswith('measurement type'):
                n_headers += 1
                if header is None:
                    header = [h.strip() for h in line.split(',')]
                continue
            parts = [p.strip() for p in line.split(',')]
            if header is None or len(parts) != len(header):
                n_badrows += 1
                continue
            rows.append(parts)
    base = os.path.basename(file_path)
    if header is None:
        raise ValueError("CO2 reader (%s): no 'Measurement type' header line found - "
                         "not a dissolved-CO2 logger export." % base)
    df = pd.DataFrame(rows, columns=header)
    co2_col = next((c for c in df.columns
                    if re.search(r'corrected\s+dis+olved\s+co2', c, re.IGNORECASE)), None)
    if co2_col is None:   # fall back to the uncorrected reading
        co2_col = next((c for c in df.columns if re.fullmatch(r'CO2 \(PPM\)', c, re.IGNORECASE)), None)
        if co2_col is None:
            raise ValueError('CO2 reader (%s): no CO2 column found in the header.' % base)
        msgs.append("Warning: 'Corrected disolved CO2' column not found in %s - "
                    "using the uncorrected 'CO2 (PPM)' column." % base)
    for c in ('Year', 'Month', 'Day', 'Hour', 'Minute', 'Second'):
        if c not in df.columns:
            raise ValueError('CO2 reader (%s): date column %r missing.' % (base, c))
    stamp = pd.to_datetime(dict(year=pd.to_numeric(df['Year'], errors='coerce'),
                                month=pd.to_numeric(df['Month'], errors='coerce'),
                                day=pd.to_numeric(df['Day'], errors='coerce'),
                                hour=pd.to_numeric(df['Hour'], errors='coerce'),
                                minute=pd.to_numeric(df['Minute'], errors='coerce'),
                                second=pd.to_numeric(df['Second'], errors='coerce')),
                           errors='coerce')
    out = pd.DataFrame({'Datetime': stamp,
                        'CO2 Level (ppm)': pd.to_numeric(df[co2_col], errors='coerce')})
    n_invalid = int((out['Datetime'].isna() | out['CO2 Level (ppm)'].isna()).sum())
    out = out.dropna().sort_values('Datetime')
    out = out.drop_duplicates(subset='Datetime', keep='first')
    out.index = np.arange(len(out))
    if out.empty:
        raise ValueError('CO2 reader (%s): no valid CO2 records.' % base)
    if n_headers > 1:
        msgs.append('Info: %d repeated header line(s) skipped in %s (logger restarts).'
                    % (n_headers - 1, base))
    if n_badrows or n_invalid:
        msgs.append('Warning: %d malformed/invalid CO2 row(s) skipped in %s.'
                    % (n_badrows + n_invalid, base))
    interval = out['Datetime'].diff().median()
    msgs.append('Info: CO2 file read: %d records, %s to %s, median interval %s.'
                % (len(out), out['Datetime'].iloc[0], out['Datetime'].iloc[-1], interval))
    return out, msgs


def merge_co2_data(dataframe, co2_path, gap_factor=2.0):
    """Imports the dissolved-CO2 series into a Seaguard frame whose 'Datetime'
    is ALREADY in its final time base. The CO2 timestamps are used AS-IS: the
    GMT-3 correction is NEVER applied to them (the CO2 logger clock is set to
    local time, unlike the Seaguard's GMT clock) - the Seaguard side is
    corrected BEFORE this merge, so both series meet in local time.

    The two loggers sample at different rates, so the CO2 value at each
    Seaguard timestamp is LINEARLY INTERPOLATED in time between the two
    bracketing CO2 samples. A timestamp is filled only when those samples are
    at most `gap_factor` x the CO2 logger's median interval apart (logger gaps
    and off periods are never bridged) and never outside the CO2 coverage.
    Fills the 'CO2 Level (ppm)' column. Returns (dataframe, messages)."""
    co2, msgs = read_co2_file(co2_path)
    t_src = co2['Datetime'].astype('int64').to_numpy() / 1e9        # epoch seconds
    v_src = co2['CO2 Level (ppm)'].to_numpy(dtype=float)
    t_tgt = pd.to_datetime(dataframe['Datetime']).astype('int64').to_numpy() / 1e9
    interp = np.interp(t_tgt, t_src, v_src, left=np.nan, right=np.nan)
    inside = (t_tgt >= t_src[0]) & (t_tgt <= t_src[-1])
    tol = gap_factor * float(np.median(np.diff(t_src))) if len(t_src) > 1 else 0.0
    # bracketing-gap check: the two CO2 samples around each target must be close
    right = np.searchsorted(t_src, t_tgt, side='left').clip(1, len(t_src) - 1)
    bracket_gap = t_src[right] - t_src[right - 1]
    valid = inside & (bracket_gap <= tol)
    dataframe = dataframe.copy()
    dataframe['CO2 Level (ppm)'] = np.where(valid, interp, np.nan)
    n_fill = int(valid.sum())
    n_gap = int((inside & ~valid).sum())
    n_out = int((~inside).sum())
    msgs.append('Info: CO2 imported into %d of %d timestamps (linear interpolation '
                'between the bracketing CO2 samples); %d inside logger gaps > %.0f s '
                'and %d outside the CO2 coverage left empty.'
                % (n_fill, len(t_tgt), n_gap, tol, n_out))
    if n_fill == 0:
        msgs.append('Warning: NO timestamps could be filled - the CO2 timestamps are '
                    'used AS-IS (never GMT-corrected); check that the CO2 logger clock '
                    'is in the same time base as the qualified data.')
    return dataframe, msgs


def read_ctd(INPUT):
    # define file path
    file_path = os.path.join(INPUT['raw_data_path'], INPUT['file_name'])

    # First determine file type and handle accordingly
    if INPUT['file_name'].lower().endswith('.bin'):
        # Seaguard II raw binary session: decoded into the same layout as the
        # instrument's CSV export, so everything below applies unchanged. Reads
        # the whole deployment - all sibling sensor-group folders merged in time
        # (Doppler excluded) - so a multi-group cast qualifies as one record.
        dataframe = read_seaguard_deployment(file_path)
    elif INPUT['file_name'].lower().endswith('.xlsx'):
        # For Excel files, we need a different approach to find the header
        # Read the file line by line to find the header row
        header_row = 0
        with pd.ExcelFile(file_path) as xls:
            # Read first 20 rows to find the header
            df_sample = pd.read_excel(xls, nrows=20, header=None)
            for i, row in df_sample.iterrows():
                if row.astype(str).str.contains('record time', case=False).any():
                    header_row = i
                    break
        
        # Now read the file properly with the found header row
        dataframe = pd.read_excel(file_path, skiprows=header_row, header=0)
        
    elif INPUT['file_name'].lower().endswith('.csv'):
        # For CSV files, we can use the original approach
        i = 0
        with open(file_path) as f:
            for line in f:
                if re.search('record time', line, re.IGNORECASE):
                    break
                i += 1
        dataframe = pd.read_csv(file_path, skiprows=i, header=0, delimiter=';')
    else:
        raise ValueError("Unsupported file format. Only .bin (Seaguard session), "
                         ".xlsx and .csv files are supported.")

    # Units are read from the SOURCE, not asked of the user (v11.4): every
    # Seaguard .bin template and every AADI text export names the unit in the
    # column itself ('Pressure[kPa]', 'Conductivity[mS/cm]'). A text export
    # whose pressure/conductivity column names no unit is REFUSED - assuming
    # one silently is how a wrong conversion slips into a qualified file.
    def _unit_of(column_str, choices):
        m = re.search(r'[\[\(]([^\]\)]*)[\]\)]', column_str)
        if not m:
            return None
        txt = m.group(1).strip()
        for canon, pattern in choices:
            if re.fullmatch(pattern, txt, re.IGNORECASE):
                return canon
        return None

    detected_units = {}

    # set flags for identified columns
    column_flags = {
        'Datetime': False,
        'Pressure (dbar)': False,
        'Depth (m)': False,
        'Temperature (degC)': False,
        'Conductivity (mS/cm)': False,
        'Salinity (PSU)': False,
        'Density (kg/m3)': False,
        'Soundspeed (m/s)': False,
        'Turbidity (FTU)': False,
        'TSS (mg/L)': False,
        'Chlorophyll (ug/L)': False,
        'Dissolved organic matter (ppb)': False,
        'pH': False,
        'PAR (umol/m2/s)': False,
        'O2 level (uM)': False,
        'O2 content (mg/L)': False
    }
    
    # create renamed columns list
    renamed_columns = []
    
    # enter loop for finding and renaming columns
    for column in dataframe.columns:   
        column_str = str(column)  # Ensure we're working with string

        if not column_flags['Datetime'] and re.search('time', column_str, re.IGNORECASE):
            dataframe = dataframe.rename(columns={column: 'Datetime'})
            column_flags['Datetime'] = True
            renamed_columns.append('Datetime')

        elif not column_flags['Pressure (dbar)'] and re.search('pressure', column_str, re.IGNORECASE):
            unit = _unit_of(column_str, [('dbar', r'(deci\s*bar|dbar)'),
                                         ('kPa', r'k\s*pa'), ('bar', r'bar')])
            if unit is None:
                raise ValueError(
                    "The pressure column '%s' in '%s' does not name its unit "
                    "(expected [kPa], [dbar] or [bar] in the header). Re-export "
                    "the file with units, or qualify from the raw .bin session."
                    % (column_str, INPUT['file_name']))
            detected_units['pressure'] = unit
            dataframe = dataframe.rename(columns={column: 'Pressure (dbar)'})
            column_flags['Pressure (dbar)'] = True
            renamed_columns.append('Pressure (dbar)')

        elif not column_flags['Depth (m)'] and re.search('prof|depth', column_str, re.IGNORECASE):
            dataframe = dataframe.rename(columns={column: 'Depth (m)'})
            column_flags['Depth (m)'] = True
            renamed_columns.append('Depth (m)')

        elif not column_flags['Temperature (degC)'] and re.search('temperature', column_str, re.IGNORECASE):
            dataframe = dataframe.rename(columns={column: 'Temperature (degC)'})
            column_flags['Temperature (degC)'] = True
            renamed_columns.append('Temperature (degC)')

        elif not column_flags['Conductivity (mS/cm)'] and re.search('conductivity', column_str, re.IGNORECASE):
            unit = _unit_of(column_str, [('mS/cm', r'ms\s*/\s*cm'),
                                         ('S/m', r's\s*/\s*m')])
            if unit is None:
                raise ValueError(
                    "The conductivity column '%s' in '%s' does not name its "
                    "unit (expected [mS/cm] or [S/m] in the header). Re-export "
                    "the file with units, or qualify from the raw .bin session."
                    % (column_str, INPUT['file_name']))
            detected_units['conductivity'] = unit
            dataframe = dataframe.rename(columns={column: 'Conductivity (mS/cm)'})
            column_flags['Conductivity (mS/cm)'] = True
            renamed_columns.append('Conductivity (mS/cm)')

        elif not column_flags['Salinity (PSU)'] and re.search('salinity', column_str, re.IGNORECASE):
            dataframe = dataframe.rename(columns={column: 'Salinity (PSU)'})
            column_flags['Salinity (PSU)'] = True
            renamed_columns.append('Salinity (PSU)')

        elif not column_flags['Density (kg/m3)'] and re.search('density', column_str, re.IGNORECASE):
            dataframe = dataframe.rename(columns={column: 'Density (kg/m3)'})
            column_flags['Density (kg/m3)'] = True
            renamed_columns.append('Density (kg/m3)')

        elif not column_flags['Soundspeed (m/s)'] and re.search('soundspeed|speed of sound', column_str, re.IGNORECASE):
            dataframe = dataframe.rename(columns={column: 'Soundspeed (m/s)'})
            column_flags['Soundspeed (m/s)'] = True
            renamed_columns.append('Soundspeed (m/s)')

        elif not column_flags['Turbidity (FTU)'] and re.search('turbidity', column_str, re.IGNORECASE):
            dataframe = dataframe.rename(columns={column: 'Turbidity (FTU)'})
            column_flags['Turbidity (FTU)'] = True
            renamed_columns.append('Turbidity (FTU)')

        elif not column_flags['TSS (mg/L)'] and re.search('TSS', column_str):
            dataframe = dataframe.rename(columns={column: 'TSS (mg/L)'})
            column_flags['TSS (mg/L)'] = True
            renamed_columns.append('TSS (mg/L)')

        elif not column_flags['Chlorophyll (ug/L)'] and re.search('chlorophyll', column_str, re.IGNORECASE):
            dataframe = dataframe.rename(columns={column: 'Chlorophyll (ug/L)'})
            column_flags['Chlorophyll (ug/L)'] = True
            renamed_columns.append('Chlorophyll (ug/L)')

        elif not column_flags['Dissolved organic matter (ppb)'] and re.search('organic', column_str, re.IGNORECASE):
            dataframe = dataframe.rename(columns={column: 'Dissolved organic matter (ppb)'})
            column_flags['Dissolved organic matter (ppb)'] = True
            renamed_columns.append('Dissolved organic matter (ppb)')

        elif not column_flags['pH'] and re.search(r'^(?!.*raw).*pH.*$', column_str):
            dataframe = dataframe.rename(columns={column: 'pH'})
            column_flags['pH'] = True
            renamed_columns.append('pH')

        elif not column_flags['PAR (umol/m2/s)'] and re.search('PAR', column_str):
            dataframe = dataframe.rename(columns={column: 'PAR (umol/m2/s)'})
            column_flags['PAR (umol/m2/s)'] = True
            renamed_columns.append('PAR (umol/m2/s)')

        elif not column_flags['O2 level (uM)'] and re.search(r'^(?=.*O2)(?=.*uM).*$', column_str, re.IGNORECASE):
            dataframe = dataframe.rename(columns={column: 'O2 level (uM)'})
            column_flags['O2 level (uM)'] = True
            renamed_columns.append('O2 level (uM)')

        elif not column_flags['O2 content (mg/L)'] and re.search(r'^(?=.*O2)(?=.*content).*$', column_str, re.IGNORECASE):
            dataframe = dataframe.rename(columns={column: 'O2 content (mg/L)'})
            column_flags['O2 content (mg/L)'] = True
            renamed_columns.append('O2 content (mg/L)')
    
    # keep only identified columns
    dataframe = dataframe[renamed_columns]

    if 'Datetime' not in dataframe.columns:
        raise ValueError("No time column found in input file '%s'" % INPUT['file_name'])

    # set datetime column
    dataframe['Datetime'] = pd.to_datetime(dataframe['Datetime'], dayfirst=True)

    # Numeric columns: Seaguard exports use either '.' or ',' as the decimal
    # separator (locale-dependent). pandas parses '.'-decimals as floats, but a
    # ','-decimal column (e.g. '131,7655') is read as TEXT, which breaks every
    # numeric test downstream. Coerce every value column to float, accepting the
    # comma decimal, and report any value that could not be parsed (never dropped
    # silently). Columns already numeric ('.'-decimal files) are left untouched.
    for col in dataframe.columns:
        if col == 'Datetime' or dataframe[col].dtype != object:
            continue
        raw = dataframe[col]
        cleaned = raw.where(raw.isna(),
                            raw.astype(str).str.strip().str.replace(',', '.', regex=False))
        converted = pd.to_numeric(cleaned, errors='coerce')
        was_value = raw.notna() & (raw.astype(str).str.strip() != '')
        lost = int((converted.isna() & was_value).sum())
        if lost > 0:
            print("Warning: %d unparseable value(s) in column '%s' set to NaN (%s)"
                  % (lost, col, INPUT['file_name']))
        dataframe[col] = converted

    # discard records without a valid timestamp (e.g. truncated trailing rows
    # left by interrupted sensor exports) — they cannot be qualified
    n_invalid = int(dataframe['Datetime'].isna().sum())
    if n_invalid > 0:
        print('Warning: %d record(s) without valid timestamp discarded from %s'
              % (n_invalid, INPUT['file_name']))
        dataframe = dataframe[dataframe['Datetime'].notna()]
        dataframe.index = np.arange(len(dataframe))

    # convert to the software standards (dbar, mS/cm) using the units the
    # SOURCE declared - after the numeric cleanup, so values are numbers
    if detected_units:
        dataframe = convert_tscp_units(
            dataframe,
            pressure_unit=detected_units.get('pressure', 'dbar'),
            conductivity_unit=detected_units.get('conductivity', 'mS/cm'))
        print('Info: units read from the file: %s.' % ', '.join(
            '%s in %s' % (k, v) for k, v in sorted(detected_units.items())))

    return dataframe

# 1 lumen/ft2 = 10.7639 lux (HOBO Pendant exported in US units)
LUMEN_FT2_TO_LUX = 10.7639

# HOBO logger event column patterns (pt/en)
_HOBO_EVENT_PATTERN = (r'acoplador|coupler|anfitri|host|parado|stopped|'
                       r'fim do ficheiro|end of file|bateria|battery')
_HOBO_DETACH_PATTERN = r'acoplador desligado|coupler detached'
_HOBO_END_PATTERN = (r'acoplador ligado|coupler attached|anfitri|host|'
                     r'parado|stopped|fim do ficheiro|end of file')


def _hobo_error(file_name, message):
    # every reader error is self-localizing: "HOBO reader (file): what was missing"
    return ValueError('HOBO reader (%s): %s' % (file_name, message))


# pt-locale HOBOware clock, e.g. '04h0min0s' instead of '04:00:00'
_HOBO_PT_CLOCK = r'(?i)(\d{1,2})h(\d{1,2})min(\d{1,2})s'


# Physically possible water temperature for a moored HOBO. Deliberately wide -
# this is only used to recognize a LOST DECIMAL SEPARATOR, not to judge data.
_HOBO_T_MIN, _HOBO_T_MAX = -5.0, 60.0


def _hobo_fix_temp_scale(temp, file_name):
    """Undoes the decimal separator lost by some HOBOware exports.

    Several xlsx exports in this archive write 25.125 degC as the integer
    25125: the pt-BR comma decimal was dropped when the workbook was written,
    and the reader used to take the number at face value, so five corpus
    products carried temperatures in the tens of thousands of degrees.

    The correction is applied ONLY when it is unambiguous: essentially every
    value must be outside any possible temperature AND one single power of ten
    must bring essentially all of them back inside. A file that is merely
    warm, or that needs different factors for different rows, is left alone -
    a wrong rescale would silently invent plausible data, which is worse than
    an obviously absurd number.

    Returns (series, message-or-None).
    """
    v = temp.dropna()
    if len(v) < 10:
        return temp, None
    inside = ((v >= _HOBO_T_MIN) & (v <= _HOBO_T_MAX)).mean()
    if inside > 0.02:
        return temp, None                  # already on a plausible scale
    # A lost separator leaves INTEGERS behind: 25.125 becomes 25125. A sensor
    # that genuinely reads -84.77 degC still carries its decimals, and must be
    # reported as broken rather than divided into looking plausible - without
    # this guard, -84.77..156.53 would be "recovered" as -0.85..1.57.
    if (v != v.round()).mean() > 0.02:
        return temp, (
            'Warning: temperatures in %s are outside %.0f..%.0f degC (%.0f to %.0f) but '
            'still carry decimals, so this is not a lost separator - the sensor itself '
            'is reading out of range. Left untouched.'
            % (file_name, _HOBO_T_MIN, _HOBO_T_MAX, float(v.min()), float(v.max())))
    for factor in (10.0, 100.0, 1000.0):
        if (((v / factor >= _HOBO_T_MIN) & (v / factor <= _HOBO_T_MAX)).mean()) > 0.98:
            return temp / factor, (
                'Warning: every temperature in %s was outside %.0f..%.0f degC and '
                'dividing by %d brings them all back (e.g. %.0f -> %.3f). This export '
                'lost its decimal separator; the values were rescaled. Check the '
                'export locale - re-exporting with a dot decimal avoids the guess.'
                % (file_name, _HOBO_T_MIN, _HOBO_T_MAX, int(factor),
                   float(v.iloc[0]), float(v.iloc[0]) / factor))
    return temp, (
        'Warning: temperatures in %s are outside %.0f..%.0f degC (%.0f to %.0f) and no '
        'single power of ten brings them back - left untouched, but they are not '
        'usable as recorded.' % (file_name, _HOBO_T_MIN, _HOBO_T_MAX,
                                 float(v.min()), float(v.max())))


def _hobo_datetimes(series, say):
    """Parses a HOBOware time column.

    Exports mix locales: the clock may come as '04h0min0s' (pt HOBOware)
    instead of '04:00:00', and the date may be day-first ('17/03/18') or
    month-first ('03/17/18') - roughly half of the corpus is month-first, and a
    plain dayfirst=True parse turns EVERY row of those files into NaT ('no rows
    with valid timestamps'). So: normalize the clock, then let the data itself
    prove the day/month order. Day-first stays the default when the file is
    ambiguous, which is how every already-readable export was parsed."""
    if pd.api.types.is_datetime64_any_dtype(series):
        return pd.to_datetime(series, errors='coerce')
    txt = series.astype(str).str.strip()
    if txt.str.contains(_HOBO_PT_CLOCK, regex=True).any():
        txt = txt.str.replace(_HOBO_PT_CLOCK, r'\1:\2:\3', regex=True)
        say("Info: clock exported as 'HHhMMminSSs'; normalized to HH:MM:SS.")
    parts = txt.str.extract(r'^\s*(\d{1,2})\s*[/-]\s*(\d{1,2})\s*[/-]')
    first = pd.to_numeric(parts[0], errors='coerce')
    second = pd.to_numeric(parts[1], errors='coerce')
    dayfirst = True
    if (first > 12).any():
        pass                       # a first field > 12 can only be the day
    elif (second > 12).any():
        dayfirst = False           # a second field > 12 can only be the day
        say('Info: dates are month-first (a value > 12 in the second field '
            'proves it); parsed accordingly.')
    elif first.notna().any():
        # Neither field ever exceeds 12, so nothing in the file proves the
        # order and day-first is only an assumption. Say so: a wrong guess
        # silently moves every sample to another month instead of failing.
        say('Warning: this export never shows a day above 12, so the file does '
            'not prove whether its dates are day-first or month-first; '
            'day-first was assumed. Check the dates - if the deployment is '
            'month-first, every timestamp is in the wrong month.')
    return pd.to_datetime(txt, errors='coerce', dayfirst=dayfirst)


def peek_hobo_header(file_path):
    """Header-only peek at a raw .hobo file: model, serial, launch time,
    logging interval and the logger's UTC offset - without decoding the
    sample stream (v12.0, for the interface's Selection summary). Returns
    None when the file is not a readable .hobo; NEVER raises."""
    try:
        with open(file_path, 'rb') as f:
            blob = f.read(0x400)
        if not blob.startswith(b'HOBO'):
            return None
        tags, i = {}, 0
        while i < len(blob) - 2:
            if blob[i] == 0x88:
                t, ln = blob[i + 1], blob[i + 2]
                if t not in tags and 0 < ln < 64:
                    tags[t] = blob[i + 3:i + 3 + ln]
                i += 3 + ln if 0 < ln < 64 else 1
            else:
                i += 1
        out = {'model': tags.get(0x05, b'').decode('ascii', 'replace'),
               'serial': tags.get(0x06, b'').decode('ascii', 'replace'),
               'launch': None, 'interval_s': None, 'utc_offset_s': None}
        p = tags.get(0x07)
        if p is not None and len(p) >= 7:
            try:
                out['launch'] = pd.Timestamp(2000 + p[1], p[2], p[3], p[4], p[5], p[6])
            except ValueError:
                pass
        p = tags.get(0x08)
        if p is not None and len(p) == 4:
            out['interval_s'] = int.from_bytes(p, 'big')
        p = tags.get(0x12)
        if p is not None and len(p) == 4:
            out['utc_offset_s'] = int.from_bytes(p, 'big', signed=True)
        return out
    except Exception:
        return None


def _read_hobo_binary(file_path, say):
    """Decodes a raw HOBOware .hobo file (HOBO Pendant Temp/Light, UA-002
    family) into the standard frame Datetime / Temperature (degC) /
    Luminosity (lux) - no HOBOware export needed.

    Format, reverse-engineered 2026-08-14 and validated against 97 corpus
    file/export pairs (temperature >= 99.9% exact in every one; light >= 99%
    in every clean export, >= 99.9% in 81 of 89):

    * The file is a dump of the logger memory (0xFF-padded), preceded by a
      TLV header: ``88 <tag> <len> <payload>``. Tags used here: 0x05 model
      string, 0x06 serial, 0x07 launch datetime (binary bytes
      ``? yy mm dd HH MM SS ?``), 0x08 logging interval in seconds (int32
      BE), 0x12 the logger's UTC offset at launch in seconds (int32 BE).
      Sample data begins after the last ``88 11 00`` and ends at the 0xFF
      padding.
    * One sample = 18 bits, MSB-first: [light 8 bits][temperature 10 bits].
      The light byte of record i belongs to sample i-1 (one-slot lag).
      The current deployment sits at the FRONT of memory, after a short
      launch preamble whose length varies per file - hence the bit phase
      (0..17) and token offset (0..8) are found by scanning, anchored by the
      temperature calibration table: the right alignment is the only one
      whose codes fall inside the physical band of the table. Old
      deployments REMAIN in memory after the terminator and are ignored.
    * The deployment ends at the first token whose temperature bits are all
      ones (0x3FF) - a terminator/event marker - or at the 0xFF padding.
    * Timestamps: stored sample i = launch + 1 s + (i + 1) * interval, in
      the logger's own local clock (the reading HOBOware shows at launch+1s
      was taken in air during configuration and is NOT in the memory
      stream). When tag 0x12 differs from GMT-03 (-10800 s) the series is
      shifted to GMT-03, matching what HOBOware's exports show.
    * Calibration (QCS_HoboCal): temperature 10-bit code -> degC, table
      derived from the corpus, universal across loggers (zero conflicts),
      monotone, steps ~0.1 degC; light 8-bit companded code -> lux
      (linear to code 128, then mantissa/exponent; lux = raw x 10.7639).

    A file whose codes do not fit the table at any alignment (e.g. the
    older-HOBOware layout variant still undeciphered) is REFUSED with a
    clear message - never guessed.
    """
    from QCS_HoboCal import HOBO_TEMP_LUT, HOBO_LIGHT_LUT
    file_name = os.path.basename(file_path)
    with open(file_path, 'rb') as f:
        blob = f.read()
    if not blob.startswith(b'HOBO'):
        raise _hobo_error(file_name, 'not a .hobo binary (missing HOBO magic).')

    # ---- header TLV ----
    tags, i = {}, 0
    while i < min(len(blob), 0x400) - 2:
        if blob[i] == 0x88:
            t, ln = blob[i + 1], blob[i + 2]
            if t not in tags and 0 < ln < 64:
                tags[t] = blob[i + 3:i + 3 + ln]
            i += 3 + ln if 0 < ln < 64 else 1
        else:
            i += 1
    model = tags.get(0x05, b'').decode('ascii', 'replace')
    serial = tags.get(0x06, b'').decode('ascii', 'replace')
    if 'pendant' not in model.lower() or 'temp' not in model.lower():
        raise _hobo_error(file_name, 'logger model %r is not a Pendant '
                          'Temp/Light - only the UA-002 family is supported '
                          'for direct .hobo reading.' % model)
    p = tags.get(0x07)
    if p is None or len(p) < 7:
        raise _hobo_error(file_name, 'no launch datetime in the header (tag 0x07).')
    try:
        launch = pd.Timestamp(2000 + p[1], p[2], p[3], p[4], p[5], p[6])
    except ValueError:
        raise _hobo_error(file_name, 'invalid launch datetime in the header: %s'
                          % p.hex(' ')) from None
    p = tags.get(0x08)
    if p is None or len(p) != 4:
        raise _hobo_error(file_name, 'no logging interval in the header (tag 0x08).')
    interval_s = int.from_bytes(p, 'big')
    if not (0 < interval_s <= 24 * 3600):
        raise _hobo_error(file_name, 'implausible logging interval: %d s.' % interval_s)
    tz_shift_s = 0
    p = tags.get(0x12)
    if p is not None and len(p) == 4:
        offset_s = int.from_bytes(p, 'big', signed=True)
        if offset_s != -10800:
            tz_shift_s = -10800 - offset_s
            say('Warning: the logger clock was set at UTC offset %+d s, not '
                'GMT-03; timestamps shifted by %+d s to GMT-03 (what the '
                'HOBOware exports of this archive use).' % (offset_s, tz_shift_s))

    # ---- sample stream ----
    end = len(blob)
    while end > 0 and blob[end - 1] == 0xFF:
        end -= 1
    dstart = blob.rfind(b'\x88\x11\x00', 0, 0x300)
    if dstart < 0:
        raise _hobo_error(file_name, 'no end-of-header marker (88 11 00) found.')
    bits = np.unpackbits(np.frombuffer(blob[dstart + 3:end], dtype=np.uint8))

    def _walk(temp, off):
        """Greedy sample walk with EVENT skipping: an isolated temp==0x3FF
        token whose lookahead still fits the calibration is a logger event
        (skipped - it does not consume a time slot); a 0x3FF whose
        continuation stops fitting is the terminator. Mid-stream events were
        the cause of the families that decoded ~50-75% (each un-skipped
        event slid the alignment by one slot from there on)."""
        idx, n_events, i, ntok = [], 0, off, len(temp)
        while i < ntok:
            if temp[i] == 0x3FF:
                ahead = temp[i + 1:i + 11]
                fit = sum(1 for c in ahead
                          if int(c) in HOBO_TEMP_LUT or c == 0x3FF)
                if len(ahead) >= 5 and fit >= 0.9 * len(ahead):
                    n_events += 1
                    i += 1
                    continue
                break
            idx.append(i)
            i += 1
        return np.array(idx, dtype=np.int64), n_events

    step_limit = max(1.5, 2.0 * interval_s / 3600.0)
    t0_local = launch + pd.Timedelta(seconds=1 + interval_s + tz_shift_s)

    arrays = []                       # per bit phase: (temp codes, light codes)
    for phase in range(18):
        ntok = (len(bits) - phase) // 18
        if ntok < 12:
            arrays.append(None)
            continue
        seg = bits[phase:phase + ntok * 18].reshape(ntok, 18)
        arrays.append(((seg[:, 8:18] @ (1 << np.arange(9, -1, -1))).astype(int),
                       (seg[:, 0:8] @ (1 << np.arange(7, -1, -1))).astype(int)))

    def _evaluate(phase, off, anchored):
        """Walks one candidate alignment and applies the physical guards.
        Returns the candidate dict, or None. Anchored candidates (found via
        the preamble delimiter) skip the head-step guard: the anchor is
        structural, and a real first reading taken on a hot deck may
        legitimately jump - only UNANCHORED content scans need protection
        against a phantom preamble sample."""
        if arrays[phase] is None:
            return None
        temp, light = arrays[phase]
        idx, n_events = _walk(temp, off)
        nn = len(idx)
        if nn < 10:
            return None
        codes = temp[idx]
        inlut = np.fromiter((int(c) in HOBO_TEMP_LUT for c in codes),
                            bool, len(codes))
        coverage = float(np.mean(inlut))
        if coverage < 0.995:
            return None
        # physical guards against an alignment that lands in the table by
        # accident: a real deployment walks through many temperature codes,
        # and water temperature cannot jump (limit scaled by the sampling
        # interval - shallow pools move 3-4 degC between 2 h samples)
        degs = np.array([HOBO_TEMP_LUT.get(int(c), np.nan) for c in codes])
        step_ok = np.abs(np.diff(degs))
        step_ok = step_ok[~np.isnan(step_ok)]
        smooth = (float(np.mean(step_ok <= step_limit))
                  if len(step_ok) else 0.0)
        distinct = len(np.unique(codes[inlut]))
        if nn >= 50 and (distinct < 8 or smooth < 0.99):
            return None
        if not anchored:
            head = degs[:4]
            head_steps = np.abs(np.diff(head[~np.isnan(head)]))
            if np.isnan(degs[0]) or (len(head_steps) and
                                     float(head_steps.max()) > step_limit):
                return None
        # nighttime darkness (used to rank unanchored candidates - a wrong
        # alignment's light bytes are noise, and noise glows in the dark -
        # and by the clock-coherence gate below)
        nxt = idx + 1
        lc = np.where(nxt < len(light),
                      light[np.minimum(nxt, len(light) - 1)], 255)
        lx = np.array([HOBO_LIGHT_LUT.get(int(c), np.nan) for c in lc])
        hrs = ((t0_local.hour * 3600 + t0_local.minute * 60
                + np.arange(nn, dtype=np.int64) * interval_s) // 3600) % 24
        night = (hrs >= 22) | (hrs < 4)
        nlx = lx[night & ~np.isnan(lx)]
        dark = float(np.mean(nlx == 0.0)) if len(nlx) >= 20 else 1.0
        return dict(coverage=coverage, phase=phase, off=off, idx=idx,
                    n_events=n_events, temp=temp, light=light, dark=dark,
                    lux=lx, count=int(inlut.sum()))

    # ---- primary anchor: the preamble DELIMITER (v11.5) ----
    # The last preamble token before sample 0 has a fixed signature - bits
    # 4..13 set, low nibble clear (census over 185 export-proven files:
    # 03FF0, 0FFF0, 13FF0, ...; the varying high bits look like the launch
    # reading's light code). A SAMPLE can never match it: its temperature
    # field would read 1008..1023, far outside the calibration band. Sample 0
    # starts 18 bits after the LAST match in the head region; matches are
    # tried last-first, and the content scan below remains the fallback for
    # the minority whose delimiter is bit-shifted.
    def _tok_at(p):
        if p < 0 or p + 18 > len(bits):
            return None
        return int(bits[p:p + 18] @ (1 << np.arange(17, -1, -1)))

    best, anchored = None, False
    matches = [p for p in range(0, min(len(bits) - 18, 160))
               if ((_tok_at(p) & 0x3FF0) == 0x3FF0
                   and (_tok_at(p) & 0xF) == 0)]
    for p in reversed(matches):
        s0 = p + 18
        cand = _evaluate(s0 % 18, s0 // 18, anchored=True)
        if cand is not None:
            best, anchored = cand, True
            break

    # ---- fallback: full content scan ranked by count and darkness ----
    if best is None:
        best_rank = None
        for phase in range(18):
            for off in range(0, 9):
                cand = _evaluate(phase, off, anchored=False)
                if cand is None:
                    continue
                rank = (cand['count'] // 10, round(cand['dark'], 2),
                        cand['count'], -off, -phase)
                if best_rank is None or rank > best_rank:
                    best_rank, best = rank, cand
    if best is None:
        raise _hobo_error(
            file_name, 'the sample stream does not fit the deciphered layout '
            'at any alignment. Probably an unsupported HOBOware layout '
            'variant - qualify this logger from its exported sheet instead.')
    coverage, phase, off = best['coverage'], best['phase'], best['off']
    idx, n_events = best['idx'], best['n_events']
    temp, light, dark, lux = (best['temp'], best['light'], best['dark'],
                              best['lux'])
    nn = len(idx)

    # bright nights on the CHOSEN alignment: either the logger clock is wrong
    # (real sun in the wrong hour bins - the light pattern stays coherent, a
    # daily peak spanning a limited part of the day) or the decode is not
    # trustworthy (light bytes are noise - light at every hour). The first is
    # a data problem the pipeline's light-phase test exists to catch, so it
    # decodes WITH a warning; the second is refused.
    if dark < 0.9:
        hrs = ((launch.hour * 3600 + launch.minute * 60
                + (np.arange(nn, dtype=np.int64) + 1) * interval_s) // 3600) % 24
        prof = np.array([np.nanmean(np.where(hrs == h, lux, np.nan))
                         for h in range(24)])
        prof = np.nan_to_num(prof)
        lit_hours = int((prof > 0.1 * prof.max()).sum()) if prof.max() > 0 else 24
        if lit_hours <= 14:
            peak_h = int(np.argmax(prof))
            say('Warning: the decoded light is non-zero through the night, '
                'but keeps a coherent daily peak (~%02d:00) - the logger '
                'clock is probably WRONG (the light-phase test will check). '
                'Compare against the HOBOware export before trusting the '
                'timestamps.' % peak_h)
        else:
            raise _hobo_error(
                file_name, 'decoded light is non-zero through the night with '
                'no coherent daily cycle - the stream cannot be decoded '
                'reliably. Qualify this logger from its exported sheet '
                'instead.')

    if n_events:
        say('Info: %d logger event marker(s) inside the sample stream '
            'skipped (they do not consume a time slot).' % n_events)

    tcodes = temp[idx]
    degc = np.array([HOBO_TEMP_LUT.get(int(c), np.nan) for c in tcodes])
    n_unk = int(np.isnan(degc).sum())
    if n_unk:
        say('Warning: %d sample(s) with a temperature code outside the '
            'calibration table set to NaN.' % n_unk)
    # light of sample i lives in the NEXT stream record; 255 = saturated
    nxt = idx + 1
    lcodes = np.where(nxt < len(light), light[np.minimum(nxt, len(light) - 1)],
                      255)
    lux = np.array([HOBO_LIGHT_LUT.get(int(c), np.nan) for c in lcodes])
    n_sat = int((lcodes == 255).sum())
    if n_sat:
        say('Warning: %d light sample(s) marked saturated/invalid (code 255) '
            'set to NaN.' % n_sat)

    # The reading HOBOware shows at launch+1s (taken in air while the logger
    # is being configured) exists only in its exports, never in the memory
    # stream - the stored series begins one interval later. That first
    # reading is an out-of-water value the edge trim would drop anyway.
    t0 = launch + pd.Timedelta(seconds=1 + interval_s + tz_shift_s)
    times = t0 + pd.to_timedelta(np.arange(nn) * interval_s, unit='s')
    df = pd.DataFrame({'Datetime': times,
                       'Temperature (degC)': degc,
                       'Luminosity (lux)': lux})
    say('Info: the launch-time reading (shown only in HOBOware exports, taken '
        'in air) is not stored in the binary; the series starts one interval '
        'after launch.')
    say('Info: raw .hobo decoded: %s s/n %s, %d samples, launch %s, interval '
        '%d s (%s alignment: bit phase %d, offset %d; %.2f%% of codes in the '
        'calibration table).'
        % (model, serial, nn, launch, interval_s,
           'delimiter-anchored' if anchored else 'content-scan',
           phase, off, 100 * coverage))
    return df


def read_hobo(INPUT, tsSettings):
    """Reads HOBOware exports (.xlsx/.csv) from Pendant Temp/Light sensors.

    Tolerates: headers in Portuguese or English, a title line before the header,
    variable sampling frequency, light in Lux or lum/ft2 (converted to lux).
    Removes logger event-only rows, trims out-of-water readings at the edges
    (window between coupler events + temperature-jump heuristic) and
    returns (dataframe, info): dataframe with Datetime / Temperature (degC) /
    Luminosity (lux); info['messages'] documents everything that was done/discarded.
    """
    file_name = INPUT['file_name']
    file_path = os.path.join(INPUT['raw_data_path'], file_name)
    info = {'messages': []}
    say = info['messages'].append

    # Raw .hobo binary (v11.4): decoded directly, then the SAME out-of-water
    # edge trim as the export path (there are no event columns in a binary,
    # so no deployment window - exactly like an export without event columns).
    if file_name.lower().endswith('.hobo'):
        df = _read_hobo_binary(file_path, say)
        return _hobo_finish(df, tsSettings, say, info, file_name)

    # ---------- raw read with header line detection ----------
    def header_line(cells):
        joined = ' '.join(str(c) for c in cells).lower()
        return (re.search(r'data\s*hora|date\s*time', joined) is not None
                and re.search(r'temp', joined) is not None)

    if file_name.lower().endswith('.xlsx'):
        sample = pd.read_excel(file_path, header=None, nrows=20)
        header_row = next((i for i, row in sample.iterrows() if header_line(row.tolist())), None)
        if header_row is None:
            raise _hobo_error(file_name, "could not find the header row: expected a line "
                              "containing 'Data Hora'/'Date Time' AND 'Temp' in the first 20 rows. "
                              "Is this a HOBOware export?")
        df = pd.read_excel(file_path, skiprows=header_row, header=0)
    elif file_name.lower().endswith('.csv'):
        raw_lines, used_encoding = None, None
        for enc in ('utf-8-sig', 'cp1252', 'latin-1'):
            try:
                with open(file_path, 'r', encoding=enc) as f:
                    raw_lines = f.readlines()
                used_encoding = enc
                break
            except UnicodeDecodeError:
                continue
        if raw_lines is None:
            raise _hobo_error(file_name, 'could not decode the file with utf-8, cp1252 or latin-1.')
        header_row = next((i for i, line in enumerate(raw_lines[:20])
                           if header_line([line])), None)
        if header_row is None:
            raise _hobo_error(file_name, "could not find the header row: expected a line "
                              "containing 'Data Hora'/'Date Time' AND 'Temp' in the first 20 lines. "
                              "Is this a HOBOware export?")
        delimiter = ';' if raw_lines[header_row].count(';') > raw_lines[header_row].count(',') else ','
        df = pd.read_csv(file_path, skiprows=header_row, header=0,
                         sep=delimiter, encoding=used_encoding, engine='python')
        say('Info: csv read with encoding %s and delimiter %r' % (used_encoding, delimiter))
    else:
        raise _hobo_error(file_name, 'unsupported format (use the .xlsx or .csv HOBOware export).')

    # ---------- column identification ----------
    time_col = temp_col = light_col = None
    event_cols = []
    for c in df.columns:
        low = str(c).lower()
        if time_col is None and re.search(r'data\s*hora|date\s*time', low):
            time_col = c
        elif temp_col is None and re.search(r'temp', low):
            temp_col = c
        elif light_col is None and re.search(r'intensidade|intensity|lux|lum', low):
            light_col = c
        elif re.search(_HOBO_EVENT_PATTERN, low):
            event_cols.append(c)
    # Some exports split the stamp into TWO columns ('Data' + 'Hora, GMT-03:00')
    # instead of one 'Data Hora'. Resolve it to a single stamp, keeping the hour
    # column's label so the GMT tag below is still picked up.
    if time_col is None:
        date_c = next((c for c in df.columns
                       if re.fullmatch(r'\s*(data|date)\s*', str(c), re.IGNORECASE)), None)
        hour_c = next((c for c in df.columns
                       if re.match(r'\s*(hora|time|hour)\b', str(c), re.IGNORECASE)), None)
        if date_c is not None and hour_c is not None:
            d, h = df[date_c], df[hour_c]
            d_dt = pd.api.types.is_datetime64_any_dtype(d)
            h_dt = pd.api.types.is_datetime64_any_dtype(h)
            if h_dt and h.dt.date.nunique() > 1:
                # several exports repeat the WHOLE stamp in both columns
                time_col = hour_c
                say('Info: %r already carries the full date+time; used directly.' % str(hour_c))
            else:
                time_col = 'Data Hora %s' % str(hour_c)
                if d_dt and h_dt:      # date + time-of-day, both as datetimes
                    df[time_col] = d.dt.normalize() + (h - h.dt.normalize())
                else:
                    # Render each side explicitly. A datetime column stringified
                    # with astype(str) keeps its own date ('1899-12-31 04:00:00'
                    # for a time-only cell), which would poison the joined stamp.
                    d_txt = (d.dt.strftime('%Y-%m-%d') if d_dt
                             else d.astype(str).str.strip())
                    h_txt = (h.dt.strftime('%H:%M:%S') if h_dt
                             else h.astype(str).str.strip())
                    df[time_col] = d_txt + ' ' + h_txt
                say('Info: date and time came in separate columns (%r + %r); joined.'
                    % (str(date_c), str(hour_c)))

    found = 'columns found: %s' % ', '.join(repr(str(c)) for c in df.columns)
    if time_col is None:
        raise _hobo_error(file_name, 'no time column found (expected "Data Hora"/"Date Time"). ' + found)
    if temp_col is None:
        raise _hobo_error(file_name, 'no temperature column found (expected "Temp"). ' + found)

    # Light is OPTIONAL: some Pendant loggers only record temperature. Their
    # temperature is perfectly usable, so a missing light channel must not
    # reject the file - Luminosity is left empty and its tests are simply not
    # evaluated (the column still exists, which is what marks a HOBO layout).
    light_factor = 1.0
    if light_col is None:
        say('Warning: no light column in this export - temperature-only logger. '
            'Luminosity will be empty and the light tests are not evaluated.')
    else:
        light_label = str(light_col).lower()
        if re.search(r'lum/?\s*ft|lumen', light_label):
            light_factor = LUMEN_FT2_TO_LUX
            say('Info: light channel is in lum/ft2; converted to lux (x%.4f).' % LUMEN_FT2_TO_LUX)
        elif re.search(r'lux', light_label):
            light_factor = 1.0
        else:
            raise _hobo_error(file_name, 'light column %r has no recognizable unit '
                              '(expected Lux or lum/ft2 in the header).' % str(light_col))

    gmt = re.search(r'GMT\s*([+-]\d{1,2}):?(\d{2})?', str(time_col))
    if gmt:
        say('Info: timestamps exported as GMT%s (from the header). The "Correct GMT-3" '
            'option would subtract 3 MORE hours - only use it if the export is in GMT+00.' % gmt.group(1))

    # ---------- types ----------
    df[time_col] = _hobo_datetimes(df[time_col], say)
    n_bad_ts = int(df[time_col].isna().sum())
    if n_bad_ts:
        say('Warning: %d row(s) without a valid timestamp discarded.' % n_bad_ts)
        df = df[df[time_col].notna()]
    if df.empty:
        raise _hobo_error(file_name, 'no rows with valid timestamps after reading.')
    df[temp_col] = pd.to_numeric(df[temp_col], errors='coerce')
    df[temp_col], scale_msg = _hobo_fix_temp_scale(df[temp_col], file_name)
    if scale_msg:
        say(scale_msg)
    if light_col is None:                     # temperature-only logger
        light_col = 'Intensidade, Lux (absent)'
        df[light_col] = np.nan
    else:
        df[light_col] = pd.to_numeric(df[light_col], errors='coerce') * light_factor

    # ---------- deployment window from the logger events ----------
    if event_cols:
        detach_cols = [c for c in event_cols if re.search(_HOBO_DETACH_PATTERN, str(c).lower())]
        end_cols = [c for c in event_cols if re.search(_HOBO_END_PATTERN, str(c).lower())]
        start_t = df.loc[df[detach_cols].notna().any(axis=1), time_col].min() if detach_cols else pd.NaT
        end_t = pd.NaT
        if end_cols:
            end_times = df.loc[df[end_cols].notna().any(axis=1), time_col]
            if pd.notna(start_t):
                end_times = end_times[end_times > start_t]
            end_t = end_times.min() if not end_times.empty else pd.NaT
        # The coupler events delimit the deployment ONLY when they were recorded
        # at LAUNCH. In many exports the coupler was first touched at READOUT, so
        # every event sits at the very end of the record and the window they
        # imply would throw the whole deployment away (13 months of good data ->
        # 'no measurement rows left'). Trust the window only when it keeps most
        # of the measurements; otherwise say so and keep the series (the
        # out-of-water edge trim below still applies).
        n_meas = int(df[temp_col].notna().sum())
        in_win = pd.Series(True, index=df.index)
        if pd.notna(start_t):
            in_win &= (df[time_col] >= start_t)
        if pd.notna(end_t):
            in_win &= (df[time_col] < end_t)
        kept = int((in_win & df[temp_col].notna()).sum())
        if n_meas and kept < 0.5 * n_meas:
            say('Warning: the logger coupler/host events sit at the end of the record - '
                'they look like readout artifacts, not the launch. The deployment window '
                'they imply (%s to %s) would drop %d of %d measurement(s), so it was NOT '
                'applied; the whole series was kept. The out-of-water edge trim still '
                'applies - check the file edges.'
                % (start_t, end_t, n_meas - kept, n_meas))
        else:
            before = len(df)
            df = df[in_win]
            n_window = before - len(df)
            if n_window:
                say('Info: %d sample(s) outside the logger deployment window '
                    '(%s to %s) discarded.' % (n_window, start_t, end_t))
        # event-only rows (no measurement) are removed
        ev_mask = df[event_cols].notna().any(axis=1) & df[temp_col].isna()
        n_ev = int(ev_mask.sum())
        if n_ev:
            say('Info: %d logger-event row(s) (no measurement) discarded.' % n_ev)
        df = df[~ev_mask]
    else:
        say('Warning: no logger event columns found - deployment window not applied; '
            'check the file edges for out-of-water readings.')

    if df.empty:
        raise _hobo_error(file_name, 'no measurement rows left after removing logger events. '
                          'Check the deployment window events in the file.')

    df = df[[time_col, temp_col, light_col]]
    df.columns = ['Datetime', 'Temperature (degC)', 'Luminosity (lux)']
    if not df['Datetime'].is_monotonic_increasing:
        say('Warning: timestamps were not in chronological order; sorted by time.')
        df = df.sort_values('Datetime')
    df.index = np.arange(len(df))
    return _hobo_finish(df, tsSettings, say, info, file_name)


def _hobo_finish(df, tsSettings, say, info, file_name):
    """Shared tail of read_hobo (export and raw-binary paths): the
    out-of-water edge trim by temperature jump, and the summary line."""
    # ---------- trim of out-of-water readings at the edges (temperature jump) ----------
    tol = float(tsSettings.get('hobo_edge_temp_tol', 1.5))
    interval = df['Datetime'].diff().median()
    n_day = max(int(pd.Timedelta(days=1) / interval), 4) if pd.notna(interval) and interval > pd.Timedelta(0) else 12
    temp = df['Temperature (degC)']

    def edge_trim_count(series, reference):
        count = 0
        for value in series:
            if pd.notna(value) and abs(value - reference) > tol:
                count += 1
            else:
                break
        return count

    n_head = edge_trim_count(temp.iloc[:n_day], temp.iloc[:5 * n_day].median())
    n_tail = edge_trim_count(temp.iloc[::-1].iloc[:n_day], temp.iloc[-5 * n_day:].median())
    if n_head + n_tail > 0.1 * len(df):
        say('Warning: edge trim would remove >10%% of the series (%d+%d samples) - '
            'NOT applied; review the temperature plot manually.' % (n_head, n_tail))
    else:
        if n_head:
            say('Info: %d leading sample(s) trimmed - temperature deviates more than '
                '%.1f degC from the deployment start (out-of-water reading).' % (n_head, tol))
        if n_tail:
            say('Info: %d trailing sample(s) trimmed - temperature deviates more than '
                '%.1f degC from the deployment end (out-of-water reading).' % (n_tail, tol))
        if n_head or n_tail:
            df = df.iloc[n_head: len(df) - n_tail]
            df.index = np.arange(len(df))

    say('Info: HOBO file read: %d samples, %s to %s, median interval %s.'
        % (len(df), df['Datetime'].iloc[0], df['Datetime'].iloc[-1], interval))
    return df, info
# Conversion functions

def convert_tscp_units (data, pressure_unit, conductivity_unit):
    # convert units specified in the input files
    # to software standard ['dbar', 'mS/cm']
    #
    # supported units:
    #     -pressure[bar, kpa] --> dbar
    #     -conductivity[S/m] --> mS/cm
    #
    # does nothinh if the specified unit is already the software standard

    if re.match('bar', pressure_unit, re.IGNORECASE):
        for name in data.columns:
            if re.search('pressure', name, re.IGNORECASE):
                data[name] = data[name] * 10
    elif re.match('kpa', pressure_unit, re.IGNORECASE):
        for name in data.columns:
            if re.search('pressure', name, re.IGNORECASE):
                data[name] = data[name] / 10
    if re.match('s/m', conductivity_unit, re.IGNORECASE):
        for name in data.columns:
            if re.search('conductivity', name, re.IGNORECASE):
                data[name] = data[name] * 10
    return data

def pressure_to_depth (dataframe, latitude, adjust_for_atm):
    p = None
    for name in dataframe.columns:
        if re.search('pressure', name, re.IGNORECASE):
            p = dataframe[name]
            if adjust_for_atm == True:
                # standard atmospheric pressure = 101.325 kPa = 10.1325 dbar
                p = p - 10.1325
    if p is None:
        return dataframe
    # latitude converted from degrees to radians (UNESCO 1983 formula)
    x = np.square(np.sin(latitude/57.29578))
    g = 9.780318 * (1+(5.2788e-3 + 2.36e-5 * x)* x) + 1.092e-6 * p
    depth = ((((-1.82e-15 * p + 2.279e-10) * p-2.2512e-5) * p + 9.72659)*p) / g
    dataframe['Depth (m)'] = round(depth, 2)
    return dataframe

def sniff_input_type(file_path):
    """Best-effort detection of a RAW data file's instrument family from its
    header lines: returns 'Seaguard', 'HOBO' or None (unrecognized - the caller
    keeps the user's current choice). Only the first ~40 lines are read.

    Markers (from the real exports): Seaguard/TSCP files open with a device
    description block ('Description;Seaguard II Platform', 'Product Name;...');
    HOBOware exports carry a 'Plot Title' line and/or a Date-Time header
    together with a light-intensity column (Lux / lum/ft2), in English or
    Portuguese."""
    try:
        # raw binaries: unambiguous magic at byte 0
        with open(file_path, 'rb') as f:
            head8 = f.read(8)
        if head8 == _AADI_MAGIC:
            return 'Seaguard'
        if head8[:4] == b'HOBO' and str(file_path).lower().endswith('.hobo'):
            return 'HOBO'
        if str(file_path).lower().endswith(('.xlsx', '.xls')):
            head = pd.read_excel(file_path, header=None, nrows=40)
            lines = [' '.join(str(c) for c in row if pd.notna(c))
                     for row in head.itertuples(index=False)]
        else:
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                lines = [f.readline() for _ in range(40)]
    except Exception:
        return None
    text = ' '.join(lines).lower()
    if 'seaguard' in text or 'aanderaa' in text:
        return 'Seaguard'
    if ('plot title' in text or 'hoboware' in text
            or (re.search(r'data\s*hora|date\s*time', text) is not None
                and re.search(r'intensity|intensidade|lum/ft|lux', text) is not None)):
        return 'HOBO'
    return None


def clean_below_zero(data, settings):
    # Handles non-physical values <= 0 before the quality tests:
    # - PAR: irradiance is physically >= 0; small negatives at night are sensor
    #   dark-offset noise, so negatives are clamped to 0 (kept), not discarded.
    # - Optical sensors (chlorophyll, turbidity, CDOM/organic matter): the true
    #   value is physically >= 0, so a small negative reading is sensor noise
    #   around zero -> clamped to 0 (kept as valid "~0"); a gross negative is a
    #   sensor error -> NaN. The boundary is 5% of the variable's environmental
    #   span (tune via env_min/env_max if needed).
    # - All other variables: <= 0 -> NaN (sensor failure for marine data).
    #
    # Returns (data, report): report[column] = {'clamped': n, 'discarded': n},
    # only for columns where something was changed, so the caller can log it.
    exceptions = ['Datetime', 'Sample number', 'Pitch[Deg]', 'Roll[Deg]', 'Timer[s]', 'Site']
    optical = {
        'chlorophyll': ('env_min_chl', 'env_max_chl'),
        'turbidity': ('env_min_tur', 'env_max_tur'),
        'organic matter': ('env_min_org', 'env_max_org'),
    }
    report = {}
    for name in data.columns:
        if name in exceptions:
            continue
        clamped, discarded = 0, 0
        if re.search('par|luminosity|lux', name, re.IGNORECASE):
            # light/PAR: zero at night is a VALID value; negatives are offset noise
            clamped = int((data[name] < 0).sum())
            data.loc[data[name] < 0, name] = 0.0
        else:
            opt_key = next((k for k in optical if re.search(k, name, re.IGNORECASE)), None)
            if opt_key is not None:
                lo_key, hi_key = optical[opt_key]
                span = settings.get(hi_key, 0) - settings.get(lo_key, 0)
                tol = 0.05 * span if span > 0 else 0
                clamped = int(((data[name] < 0) & (data[name] >= -tol)).sum())
                discarded = int((data[name] < -tol).sum())
                data.loc[(data[name] < 0) & (data[name] >= -tol), name] = 0.0
                data.loc[data[name] < -tol, name] = np.nan
            else:
                discarded = int((data[name] <= 0).sum())
                data.loc[data[name] <= 0, name] = np.nan
        if clamped or discarded:
            report[name] = {'clamped': clamped, 'discarded': discarded}
    return data, report

# Function for preparing output files

# maps each test's parameter key (from the test sequence) to the variable
# bucket(s) it affects; 'dens' (density inversion) implicates temperature and salinity
FLAG_BUCKET_MAP = {
    'T': ['T'], 'S': ['S'], 'C': ['C'], 'P': ['P'], 'pH': ['pH'],
    'chl': ['chl'], 'O2': ['O2'], 'org': ['org'], 'tur': ['tur'],
    'dens': ['T', 'S'],
    'lux': ['lux'],  # HOBO light (fouling test)
    'CO2': ['CO2'],  # dissolved CO2 (imported from the separate logger, v6.0)
}

# Maps a data column to its per-variable rollup flag column, for consumers that
# need to select rows by qualification result (e.g. the DataView scale defaults).
# Density and Depth carry DERIVED flags (v11.1): they are computed values, so
# their flag is their parents' worst - dens from T+S, depth from P. Soundspeed
# and PAR remain untested and intentionally absent. (This comment once listed
# CO2 as unflagged; Flag_CO2 exists since v6.0.)
PARAM_FLAG_COLUMN = {
    'Temperature (degC)': 'Flag_T',
    'Salinity (PSU)': 'Flag_S',
    'Conductivity (mS/cm)': 'Flag_C',
    'Pressure (dbar)': 'Flag_P',
    'pH': 'Flag_pH',
    'Chlorophyll (ug/L)': 'Flag_chl',
    'O2 level (uM)': 'Flag_O2',
    'O2 content (mg/L)': 'Flag_O2',
    'CO2 Level (ppm)': 'Flag_CO2',
    'Dissolved organic matter (ppb)': 'Flag_org',
    'Turbidity (FTU)': 'Flag_tur',
    'TSS (mg/L)': 'Flag_tur',
    'Luminosity (lux)': 'Flag_lux',
    'Density (kg/m3)': 'Flag_dens',
    'Depth (m)': 'Flag_depth',
}

def handle_output_file (input_df, flags, flag_layout, remove_suspect, remove_bad):
    # standardize data frame to output file format and
    # classify bad, suspect and missing data for temperature,
    # salinity, conductivity or pressure parameters
    #
    # input_df: input data frame
    # flags: list conteining flag codes in string like formats
    # SUSPECT_DATA: condition for placing NaN in suspect data index
    # BAD_DATA: condition for placing NaN in bad data index
    #
    # outputs
    # output_df: output data frame
    # input_df: input data frame
    # T_bdata: : list of temperature bad data indexes
    # S_bdata: list of salinity bad data indexes
    # C_bdata: list of conductivity bad data indexes
    # P_bdata: list of pressure bad data indexes
    # T_sdata: list of temperature suspect data indexes
    # S_sdata: list of salinity suspect data indexes
    # C_sdata: list of conductivity suspect data indexes
    # P_sdata : list of pressure suspect data indexes
    # T_mdata: list of temperature missing data indexes
    # S_mdata: list of salinity missing data indexes
    # C_mdata: list of conductivity missing data indexes
    # P_mdata: list of temperapressureture missing data indexes
    # pH_bdata: list of pH bad data indexes
    # chl_bdata: list of chlorophyll bad data indexes
    # O2_bdata: list of dissolved oxygen bad data indexes
    # org_bdata: list of dissolved organic matter bad data indexes
    # tur_bdata: list of turbidity bad data indexes
    # pH_sdata: list of pH suspect data indexes
    # chl_sdata: list of chlorophyll suspect data indexes
    # O2_sdata: list of dissolved oxygen suspect data indexes
    # org_sdata: list of dissolved organic matter suspect data indexes
    # tur_sdata: list of turbidity suspect data indexes
    # pH_mdata: list of pH missing data indexes
    # chl_mdata: list of chlorophyll missing data indexes
    # O2_mdata: list of dissolved oxygen missing data indexes
    # org_mdata: list of dissolved organic matter missing data indexes
    # tur_mdata: list of turbidity missing data indexes

    output_df = input_df.copy()
    output_df['Flag'] = flags
    # Classify each row per variable using the worst flag across that variable's
    # tests (bad > suspect > missing). flag_layout[pos] tells which variable each
    # flag character belongs to, so positions are never hardcoded here.
    var_keys = ['T', 'S', 'C', 'P', 'pH', 'chl', 'O2', 'org', 'tur']
    # extra buckets present in the layout (e.g. 'lux' in HOBO files) get their
    # own Flag_ column without changing the format of files that don't use them
    for pkey in flag_layout:
        for bucket in FLAG_BUCKET_MAP.get(pkey, []):
            if bucket not in var_keys:
                var_keys.append(bucket)
    bdata = {k: [] for k in var_keys}
    sdata = {k: [] for k in var_keys}
    mdata = {k: [] for k in var_keys}
    agg_flags = {k: [] for k in var_keys}  # rollup flag per row/variable (Flag_T etc.)

    def worst_flag(chars):
        # aggregation priority: bad > suspect > missing > good > not-evaluated > off
        for code in ('4', '3', '9', '1', '2'):
            if code in chars:
                return int(code)
        return 5

    for i in range(len(flags)):
        flagstr = flags[i]
        per_var = {k: '' for k in var_keys}
        for pos, pkey in enumerate(flag_layout):
            if pos < len(flagstr):
                for bucket in FLAG_BUCKET_MAP.get(pkey, []):
                    per_var[bucket] += flagstr[pos]
        for k in var_keys:
            chars = per_var[k]
            if '4' in chars:
                bdata[k].append(i)
            elif '3' in chars:
                sdata[k].append(i)
            elif '9' in chars:
                mdata[k].append(i)
            agg_flags[k].append(worst_flag(chars))

    # per-variable rollup columns: downstream users read Flag_T etc. directly,
    # without having to decode the positional flag string
    for k in var_keys:
        output_df['Flag_' + k] = agg_flags[k]

    # Derived-variable flags (v11.1). Density and Depth are COMPUTED columns -
    # dens from T+S (the density-inversion test already implicates exactly that
    # pair in FLAG_BUCKET_MAP), depth from P - yet they carried no flag at all:
    # the corpus sweep found density at 996 kg/m3 (conductivity dead in the
    # water) readable at face value with no warning attached. Their flag is
    # their parents' worst, by the same priority as worst_flag above. Purely
    # additive: no existing flag changes, and order_var keeps these columns
    # only in the TSCP layout (HOBO has no Density or Depth).
    _sev = {4: 0, 3: 1, 9: 2, 1: 3, 2: 4, 5: 5}        # severity rank, worst first
    _by_rank = {r: f for f, r in _sev.items()}
    output_df['Flag_dens'] = [
        _by_rank[min(_sev[t], _sev[s])]
        for t, s in zip(agg_flags['T'], agg_flags['S'], strict=True)]
    output_df['Flag_depth'] = agg_flags['P']

    T_bdata, S_bdata, C_bdata, P_bdata = (np.asarray(bdata['T']), np.asarray(bdata['S']), np.asarray(bdata['C']), np.asarray(bdata['P']))
    pH_bdata, chl_bdata, O2_bdata, org_bdata, tur_bdata = (np.asarray(bdata['pH']), np.asarray(bdata['chl']), np.asarray(bdata['O2']), np.asarray(bdata['org']), np.asarray(bdata['tur']))
    T_sdata, S_sdata, C_sdata, P_sdata = (np.asarray(sdata['T']), np.asarray(sdata['S']), np.asarray(sdata['C']), np.asarray(sdata['P']))
    pH_sdata, chl_sdata, O2_sdata, org_sdata, tur_sdata = (np.asarray(sdata['pH']), np.asarray(sdata['chl']), np.asarray(sdata['O2']), np.asarray(sdata['org']), np.asarray(sdata['tur']))
    T_mdata, S_mdata, C_mdata, P_mdata = (np.asarray(mdata['T']), np.asarray(mdata['S']), np.asarray(mdata['C']), np.asarray(mdata['P']))
    pH_mdata, chl_mdata, O2_mdata, org_mdata, tur_mdata = (np.asarray(mdata['pH']), np.asarray(mdata['chl']), np.asarray(mdata['O2']), np.asarray(mdata['org']), np.asarray(mdata['tur']))
    # changing bad or suspect data to NaN according from operators input
    if remove_bad == True:
        for name in output_df.columns:
            if str(name).startswith('Flag'):
                continue  # flag columns are never erased (Flag_O2/Flag_lux match the patterns)
            if re.search('temperature', name, re.IGNORECASE):
                output_df.loc[T_bdata, name] = np.nan
            if re.search('salinity', name, re.IGNORECASE):
                output_df.loc[S_bdata, name] = np.nan
            if re.search('conductivity', name, re.IGNORECASE):
                output_df.loc[C_bdata, name] = np.nan
            if re.search('pressure', name, re.IGNORECASE):
                output_df.loc[P_bdata, name] = np.nan
            # exact match: a case-insensitive 'pH' search would also hit 'Chlorophyll'
            if name == 'pH':
                output_df.loc[pH_bdata, name] = np.nan
            if re.search('chlorophyll', name, re.IGNORECASE):
                output_df.loc[chl_bdata, name] = np.nan
            # (?<!c)o2: dissolved oxygen only - 'CO2 Level (ppm)' must NOT be
            # cleared by the O2 flags (it has its own CO2 bucket below)
            if re.search(r'(?<!c)o2', name, re.IGNORECASE):
                output_df.loc[O2_bdata, name] = np.nan
            if re.search('co2', name, re.IGNORECASE) and 'CO2' in bdata:
                output_df.loc[bdata['CO2'], name] = np.nan
            if re.search('organic matter', name, re.IGNORECASE):
                output_df.loc[org_bdata, name] = np.nan
            if re.search('turbidity|tss', name, re.IGNORECASE):
                output_df.loc[tur_bdata, name] = np.nan
            if re.search('luminosity|lux', name, re.IGNORECASE) and 'lux' in bdata:
                output_df.loc[bdata['lux'], name] = np.nan
    if remove_suspect == True:
        for name in output_df.columns:
            if str(name).startswith('Flag'):
                continue  # flag columns are never erased
            if re.search('temperature', name, re.IGNORECASE):
                output_df.loc[T_sdata, name] = np.nan
            if re.search('salinity', name, re.IGNORECASE):
                output_df.loc[S_sdata, name] = np.nan
            if re.search('conductivity', name, re.IGNORECASE):
                output_df.loc[C_sdata, name] = np.nan
            if re.search('pressure', name, re.IGNORECASE):
                output_df.loc[P_sdata, name] = np.nan
            if name == 'pH':
                output_df.loc[pH_sdata, name] = np.nan
            if re.search('chlorophyll', name, re.IGNORECASE):
                output_df.loc[chl_sdata, name] = np.nan
            # (?<!c)o2: dissolved oxygen only (see the remove_bad block)
            if re.search(r'(?<!c)o2', name, re.IGNORECASE):
                output_df.loc[O2_sdata, name] = np.nan
            if re.search('co2', name, re.IGNORECASE) and 'CO2' in sdata:
                output_df.loc[sdata['CO2'], name] = np.nan
            if re.search('organic matter', name, re.IGNORECASE):
                output_df.loc[org_sdata, name] = np.nan
            if re.search('turbidity|tss', name, re.IGNORECASE):
                output_df.loc[tur_sdata, name] = np.nan
            if re.search('luminosity|lux', name, re.IGNORECASE) and 'lux' in sdata:
                output_df.loc[sdata['lux'], name] = np.nan
    return output_df, input_df, T_bdata, S_bdata, C_bdata, P_bdata, pH_bdata, chl_bdata, O2_bdata, org_bdata, tur_bdata, T_sdata, S_sdata, C_sdata, P_sdata, pH_sdata, chl_sdata, O2_sdata, org_sdata, tur_sdata, T_mdata, S_mdata, C_mdata, P_mdata, pH_mdata, chl_mdata, O2_mdata, org_mdata, tur_mdata

def order_var (qualified_data, n_cel, data_type):
    if data_type == 'tscp':
        # 'Site' right after 'Datetime' (identification comes before the measurements).
        # 'Battery voltage (V)' is kept as a placeholder (currently empty; reserved
        # for when it is extracted from the raw data). 'Expedition' was removed.
        var_priority = {'Sample number': 0, 'Datetime': 1, 'Site': 2, 'Depth (m)': 3, 'Temperature (degC)': 4,
                        'Salinity (PSU)': 5, 'Conductivity (mS/cm)': 6, 'Pressure (dbar)': 7, 'Density (kg/m3)': 8,
                        'CO2 Level (ppm)': 9, 'O2 level (uM)': 10, 'O2 content (mg/L)': 11, 'PAR (umol/m2/s)': 12,
                        'Turbidity (FTU)': 13, 'TSS (mg/L)': 14, 'Chlorophyll (ug/L)': 15, 'pH': 16,
                        'Dissolved organic matter (ppb)': 17, 'Luminosity (lux)': 18, 'Soundspeed (m/s)': 19,
                        'Battery voltage (V)': 20, 'Flag': 21,
                        'Flag_T': 22, 'Flag_S': 23, 'Flag_C': 24, 'Flag_P': 25, 'Flag_pH': 26,
                        'Flag_chl': 27, 'Flag_CO2': 28, 'Flag_O2': 29, 'Flag_org': 30,
                        'Flag_tur': 31, 'Flag_lux': 32,
                        # derived-variable flags (v11.1) sit after the measured ones
                        'Flag_dens': 33, 'Flag_depth': 34, 'QCS version': 35}
    elif data_type == 'hobo':
        # HOBO Pendant: only the measured variables (temperature in Celsius and
        # light in lux), with the same metadata block as the TSCP standard. The
        # other TSCP variables do not apply and do not appear (non-stackable sheets).
        # 'Site' right after 'Datetime'; 'Battery voltage (V)' kept as a
        # placeholder (currently empty); 'Expedition' removed.
        # 'Temperature spread (degC)' is a FIXED column: the between-replicate spread
        # when N>1 redundant HOBOs are combined; empty for single files.
        var_priority = {'Sample number': 0, 'Datetime': 1, 'Site': 2,
                        'Temperature (degC)': 3, 'Temperature spread (degC)': 4,
                        'Luminosity (lux)': 5, 'Battery voltage (V)': 6, 'Flag': 7,
                        'Flag_T': 8, 'Flag_lux': 9, 'QCS version': 10}
    else:
        raise ValueError("Unsupported data_type '%s' in order_var (use 'tscp' or 'hobo')" % data_type)

    # Latitude/Longitude are never part of the qualified output (kept out on
    # purpose so every file has the same column layout); drop them if present.
    for coord in ('Latitude', 'Longitude'):
        if coord in qualified_data.columns:
            qualified_data = qualified_data.drop(columns=[coord])

    order = {}
    for var in var_priority.keys():
        if var in qualified_data.columns:
            order[var] = var_priority[var]
        else:
            # Flag_ columns only exist when the corresponding test ran
            # (e.g. Flag_lux only in HOBO files) - do not create them empty
            if re.search('correlation', var, re.IGNORECASE) or var.startswith('Flag_'):
                pass
            else:
                qualified_data[var] = np.nan
                order[var] = var_priority[var]
    order_l = sorted(order.items(), key=lambda x: x[1], reverse=False)
    n = 0
    for item in order_l:
        var = item[0]
        order[var] = n
        n +=1
    for var in order.keys():
        col = qualified_data.pop(var)
        qualified_data.insert(order[var], var, col)
    qualified_data = qualified_data.round(4)
    for var in qualified_data.columns:
        if var not in var_priority.keys():
            if re.search('depthlevel', var, re.IGNORECASE):
                n = int(re.search(r'\d{1,3}', var).group())
                if n > n_cel:
                    qualified_data = qualified_data.drop(columns=[var])
            else:
                if re.search('speed', var, re.IGNORECASE) or re.search('direction', var, re.IGNORECASE):
                    pass
                else:
                    qualified_data = qualified_data.drop(columns=[var])
    return qualified_data

def _autofit_worksheet(ws, dataframe, index=False):
    """Widens each column of an openpyxl worksheet to fit its content."""
    from openpyxl.utils import get_column_letter
    offset = 1 if index else 0  # column A is the index when index=True
    for i, col in enumerate(dataframe.columns):
        value_len = int(dataframe[col].astype(str).map(len).max()) if len(dataframe) else 0
        width = min(max(len(str(col)), value_len) + 2, 60)  # +padding, capped so it stays sane
        ws.column_dimensions[get_column_letter(i + 1 + offset)].width = width

def save_excel_autofit(dataframe, path, index=False):
    """Writes a DataFrame to an .xlsx with each column widened to fit its content
    (header and values), so the sheet is readable without resizing by hand.
    Used for every spreadsheet the app writes."""
    with pd.ExcelWriter(path, engine='openpyxl') as writer:
        dataframe.to_excel(writer, index=index)
        _autofit_worksheet(writer.sheets[next(iter(writer.sheets))], dataframe, index)

def save_excel_sheets(sheets, path, index=False):
    """Writes {sheet_name: DataFrame} to a single .xlsx, each column auto-fitted."""
    with pd.ExcelWriter(path, engine='openpyxl') as writer:
        for name, df in sheets.items():
            df.to_excel(writer, sheet_name=name, index=index)
            _autofit_worksheet(writer.sheets[name], df, index)

def tscp_stats_table (qualified_data):
    # builds the statistics table with whichever of the main variables
    # are present and hold at least one valid value
    expected = ['Temperature (degC)', 'Salinity (PSU)', 'Conductivity (mS/cm)',
                'Pressure (dbar)', 'Depth (m)', 'Density (kg/m3)', 'pH',
                'CO2 Level (ppm)', 'O2 level (uM)', 'O2 content (mg/L)',
                'Chlorophyll (ug/L)', 'Turbidity (FTU)',
                'Dissolved organic matter (ppb)', 'PAR (umol/m2/s)',
                'Soundspeed (m/s)', 'Luminosity (lux)']
    present = [var for var in expected
               if var in qualified_data.columns and not qualified_data[var].isna().all()]
    stat = pd.DataFrame({'Variable': present,
                          'Max': [np.nanmax(qualified_data[var]) for var in present],
                          'Min': [np.nanmin(qualified_data[var]) for var in present],
                          'Mean': [np.nanmean(qualified_data[var]) for var in present],
                          'Median': [np.nanmedian(qualified_data[var]) for var in present],
                          'std': [np.nanstd(qualified_data[var]) for var in present]})

    stat = stat[['Variable','Max','Min','Mean', 'Median', 'std']]
    stat = stat.round(2)
    return stat

# other functions

def count_test_bdata(flags):
    N = 0
    for i in range(len(flags)):
        if flags[i][-1] == '4':
            N+=1
    return N

def on_motion(event):
    # verify if mouse is above a line
    if event.inaxes is not None:
        for line in event.inaxes.lines:
            if line.contains(event)[0]:
                # define buffer linestyle
                line.set_linewidth(3.0)
                line.set_alpha(1.0)
            else:
                # define no buffer linestyle
                line.set_linewidth(1.0)
                line.set_alpha(0.5)
                # update plot
                event.inaxes.figure.canvas.draw_idle()

# Deployment/recovery vs tide (v12.1). The tide moves the depth of a moored
# instrument by centimetres per minute; lowering it to the bottom or hauling it
# up moves METRES per minute. One rate threshold separates the two cleanly, and
# it is 60x above any tidal rate on this coast, so the natural cycle is never
# marked.
TRANSIT_RATE_M_PER_MIN = 0.5
TRANSIT_JOIN_MIN = 2.0         # windows closer than this are one manoeuvre
# The movement is measured as NET displacement over this many minutes, not
# between consecutive samples: a shallow mooring rides the waves, and at a
# 5-10 s cadence that beats any instantaneous rate test (the TIM2 2019S1
# mooring came out 84% shaded). Over two minutes a wave returns to where it
# started and sums to nothing, while a descent or a recovery accumulates
# metres. Where the cadence is coarser than the window - the 10-min moorings
# that are the routine here - the window collapses to one step and the test is
# the plain rate it always was.
TRANSIT_WINDOW_MIN = 2.0
# Nothing about HANDLING is thrown away - handling can be the error the
# operator is hunting - so the amplitude test only has to clear the depth
# sensor's own noise. Measured on the PLES 2019S1 mooring (17,690 samples,
# 5 s): with no test at all, noise crossing 0.5 m/min gives 194 windows and
# shades 34% of the record; the real events are 16.0, 10.9 and 1.15 m and the
# noise cluster stops at 0.25 m. Any value from 0.3 to 1.0 keeps exactly those
# three, so the low end of that plateau is the one that discards least.
TRANSIT_MIN_AMPLITUDE_M = 0.3
# an in/out MARKER is a stronger claim than shading: it needs a real vertical
# excursion, not a step
TRANSIT_MARK_NET_M = 1.0


def depth_transit_windows(depth, times):
    """Sample ranges where the instrument was going INTO or OUT OF the water.

    Returns [(first_index, last_index), ...] in POSITIONAL indices, ordered in
    time: the first window is normally the descent and the last the recovery.
    Empty when nothing moves fast enough - a profile already at depth, or a
    series with no depth at all.
    """
    depth = pd.to_numeric(pd.Series(depth), errors='coerce').to_numpy(dtype=float)
    t = pd.to_datetime(pd.Series(times), errors='coerce')
    if len(depth) < 3 or t.isna().all():
        return []
    minutes = (t - t.iloc[0]).dt.total_seconds().to_numpy() / 60.0
    # partner sample: the last one still inside the window, never the sample
    # itself (a coarse cadence then compares neighbours, as before)
    partner = np.searchsorted(minutes, minutes + TRANSIT_WINDOW_MIN, side='right') - 1
    partner = np.minimum(np.maximum(partner, np.arange(len(minutes)) + 1),
                         len(minutes) - 1)
    elapsed = minutes[partner] - minutes
    net = np.abs(depth[partner] - depth)
    with np.errstate(invalid='ignore'):
        moved = np.nan_to_num(net, nan=0.0) >= TRANSIT_RATE_M_PER_MIN * elapsed
    fast = (moved & (elapsed > 0))[:-1]
    if not fast.any():
        return []
    # runs of fast samples -> windows, then join the ones a pause apart (a
    # manoeuvre is rarely one smooth movement: the instrument stops on deck,
    # on a ledge, at a stop for a reading)
    edges = np.flatnonzero(np.diff(np.concatenate(([0], fast.view(np.int8), [0]))))
    runs = [(edges[i], edges[i + 1]) for i in range(0, len(edges), 2)]
    windows = []
    for start, stop in runs:                       # stop is exclusive on diffs
        # the window reaches the PARTNER of its last fast sample: that is where
        # the movement measured at that sample actually ends
        i0 = int(start)
        i1 = int(min(max(stop, partner[min(stop, len(depth) - 1)]), len(depth) - 1))
        if windows and minutes[i0] - minutes[windows[-1][1]] <= TRANSIT_JOIN_MIN:
            windows[-1] = (windows[-1][0], i1)
        else:
            windows.append((i0, i1))
    # the test is on the depth RANGE inside the window, not on its endpoints:
    # a lift-and-lower (the instrument pulled up and put back, sample ~3600 of
    # the PLES 2019 mooring) nets to zero and would be discarded
    kept = []
    for i0, i1 in windows:
        segment = depth[i0:i1 + 1]
        if np.nanmax(segment) - np.nanmin(segment) >= TRANSIT_MIN_AMPLITUDE_M:
            kept.append((i0, i1))
    return kept


def draw_depth_context(ax, x, depth, times):
    """Shades the transit windows on a manual-cut panel and marks the water
    entry and exit, so the operator sees WHERE the instrument was still being
    handled instead of reading it off the parameter's own noise (owner, v12.1).
    Returns the number of windows drawn."""
    windows = depth_transit_windows(depth, times)
    if not windows:
        return 0
    x = np.asarray(x)
    depth_values = pd.to_numeric(pd.Series(depth), errors='coerce').to_numpy(float)
    seen = set()

    def once(text):
        """One legend entry per kind, however many manoeuvres there were."""
        if text in seen:
            return None
        seen.add(text)
        return text

    # a manoeuvre at a 10-min cadence is ONE step: two samples out of a few
    # hundred, a hairline nobody sees. Every band gets at least this share of
    # the axis (owner, v12.1)
    span_lo, span_hi = float(np.min(x)), float(np.max(x))
    floor_w = 0.006 * (span_hi - span_lo)
    for i0, i1 in windows:
        left, right = float(x[i0]), float(x[i1])
        if right - left < floor_w:
            mid = 0.5 * (left + right)
            left, right = mid - floor_w / 2, mid + floor_w / 2
        ax.axvspan(left, right, color='#b30000', alpha=0.10, zorder=0,
                   label=once('Being lowered / hauled up'))
        # WHICH manoeuvre it is comes from the direction, never from the
        # position in the record: most deployments here start logging already
        # in the water, so the only window is the RECOVERY - labelling the
        # first window's end 'at working depth' marked the moment the
        # instrument LEFT the water (caught on the 2019S1 moorings)
        net = depth_values[i1] - depth_values[i0]
        if abs(net) < TRANSIT_MARK_NET_M:
            continue          # handled in place: shaded, but neither in nor out
        if net > 0:
            ax.axvline(x[i1], color='#b30000', linestyle='--', linewidth=1,
                       zorder=1, label=once('At working depth'))
        else:
            ax.axvline(x[i0], color='#b30000', linestyle='--', linewidth=1,
                       zorder=1, label=once('Recovery starts'))
    ax.legend(loc='best', fontsize=8)
    return len(windows)


def extend_selection_beyond_axes(selector, ax):
    """Lets the selection rectangle keep following the mouse OUTSIDE the plot.

    matplotlib freezes the rubber band the moment the cursor leaves the axes:
    `_SelectorWidget._clean_event` replaces any event whose `xdata` is None -
    which is every event outside the axes - by the PREVIOUS one, so the drag
    stops at the edge. Points sitting on the very edge of a series are then
    hard to enclose, which is exactly where a manual cut usually starts
    (owner, 2026-08-19).

    The event still carries its PIXEL position, and the widget's own
    `_get_data_coords` converts that into data coordinates for this axes, so
    the drag can continue, clipped to the axis bounds.

    This reaches into private matplotlib API (read from 3.10.0, the pinned
    build). If a future version renames either name the patch is skipped and
    the old, frozen-at-the-edge behaviour returns - a panel that works less
    well, never one that fails. Returns True when the patch went in.
    """
    import copy
    if not (hasattr(selector, '_get_data_coords') and hasattr(selector, '_prev_event')):
        return False

    def _clean_event(event):
        if getattr(event, 'x', None) is None or getattr(event, 'y', None) is None:
            return selector._prev_event          # no position at all to use
        ev = copy.copy(event)
        xdata, ydata = selector._get_data_coords(ev)
        ev.xdata = float(np.clip(xdata, *ax.get_xbound()))
        ev.ydata = float(np.clip(ydata, *ax.get_ybound()))
        selector._prev_event = ev
        return ev

    selector._clean_event = _clean_event
    return True


def _show_and_wait(fig, tk_root):
    # Shows the interactive figure without freezing the interface. plt.show(block=True)
    # inside a Tkinter callback creates a nested event loop that hangs the main
    # window (same problem as Select Profile Data, fixed in v3.2.1); with tk_root,
    # it waits in Tk's own loop until the figure is closed.
    if tk_root is None:
        plt.show(block=True)
        return
    import tkinter as tk
    done = tk.BooleanVar(tk_root, value=False)
    fig.canvas.mpl_connect('close_event', lambda event: done.set(True))
    fig.show()
    # bring the plot window to the FRONT (it otherwise opens behind the main app
    # window and has to be fished out from the taskbar); topmost briefly, then off
    try:
        win = fig.canvas.manager.window
        win.lift()
        win.attributes('-topmost', True)
        win.after(300, lambda: win.attributes('-topmost', False))
        # focus the CANVAS widget (not just the window) so key events - Enter =
        # Done, Esc = Cancel - fire without the user clicking the plot first
        fig.canvas.get_tk_widget().focus_force()
    except Exception:
        pass
    tk_root.wait_variable(done)


class ManualCutCanceled(Exception):
    """Raised when the operator presses Cancel/Esc in a manual point-cut panel
    (or the variable chooser): the caller aborts the whole qualification run and
    returns to the input form instead of proceeding."""


def manual_cut_panel(x, y, label, tk_root=None, locked=None, progress=None,
                     depth=None, times=None):
    """Interactive panel to manually DISMISS points of a series. Drag a rectangle
    over points to mark them dismissed; mouse wheel zooms; Undo/Reset/Skip/Done/
    Help buttons and a live counter. Returns a SET of positional indices to
    dismiss (empty if none), or None if the user pressed Skip. Never modifies data.

    locked:   indices already dismissed upstream (e.g. the Depth whole-row cut) -
              shown grayed and not selectable, and excluded from the returned set.
    progress: (i, total) shown in the title, e.g. '[2 of 5]'.
    depth/times: the deployment's depth series and timestamps - the panel then
              shades the moments the instrument was being lowered or hauled up
              (see draw_depth_context), which is where a cut usually belongs."""
    x = np.asarray(x)
    y = np.asarray(y, dtype=float)
    locked = set() if locked is None else set(int(i) for i in locked)
    dismissed = set()
    history = []          # stack of per-box selections, for Undo
    state = {'skipped': False, 'drawn': False, 'canceled': False}

    fig, ax = plt.subplots(figsize=(10, 6.5))
    plt.subplots_adjust(bottom=0.20, top=0.88)
    # keep the useful navigation toolbar but drop the Zoom lens (wheel zoom
    # replaces it), the Home button (the 'Reset' button resets the view) and
    # Configure subplots (its wspace/hspace do nothing here); best-effort
    try:
        tb = fig.canvas.manager.toolbar
        for _name in ('Zoom', 'Home', 'Subplots'):
            btn = getattr(tb, '_buttons', {}).get(_name)
            if btn is not None:
                btn.pack_forget()
    except Exception:
        pass

    def redraw(keep_view=True):
        # preserve the current view (zoom/pan) across redraws; the first draw
        # (and Reset) autoscales. Track "first draw" with an explicit flag, NOT
        # ax.lines/collections - the RectangleSelector adds handle artists.
        restore = keep_view and state['drawn']
        if restore:
            xlim, ylim = ax.get_xlim(), ax.get_ylim()
        ax.clear()
        gone = dismissed | locked
        keep = np.array([i not in gone for i in range(len(y))], dtype=bool)
        ax.plot(x[keep], y[keep], linestyle='-', marker='x',
                markeredgecolor='r', markerfacecolor='r', picker=5)
        if locked:
            li = sorted(locked)
            ax.scatter(x[li], y[li], marker='o', facecolors='none',
                       edgecolors='0.75', s=40)   # already cut upstream (lighter)
        if dismissed:
            di = sorted(dismissed)
            ax.scatter(x[di], y[di], marker='o', facecolors='none',
                       edgecolors='0.45', s=45)
        prog = (' [%d of %d]' % progress) if progress else ''
        extra = ('    (+%d already cut via Depth)' % len(locked)) if locked else ''
        ax.set_title('%s%s - drag a box to DISMISS points (flag 5)   |   wheel = zoom\n'
                     '%d dismissed here%s    |    Enter = Done'
                     % (label, prog, len(dismissed), extra))
        if depth is not None and times is not None:
            draw_depth_context(ax, x, depth, times)
        ax.set_ylabel(label)
        ax.set_xlabel('Sample number')
        if restore:
            ax.set_xlim(xlim)
            ax.set_ylim(ylim)
        else:
            # compute the limits from the data NOW: draw_idle may not autoscale
            # before the window is shown, leaving the default (0,1) empty view
            ax.relim()
            ax.autoscale()
        state['drawn'] = True
        fig.canvas.draw_idle()

    def on_scroll(event):
        # mouse-wheel zoom centered on the cursor (no need for the toolbar lens)
        if event.inaxes is not ax:
            return
        scale = 1 / 1.2 if event.button == 'up' else 1.2   # wheel up = zoom in
        xlim, ylim = ax.get_xlim(), ax.get_ylim()
        xd, yd = event.xdata, event.ydata
        ax.set_xlim(xd - (xd - xlim[0]) * scale, xd + (xlim[1] - xd) * scale)
        ax.set_ylim(yd - (yd - ylim[0]) * scale, yd + (ylim[1] - yd) * scale)
        fig.canvas.draw_idle()

    # middle-mouse-button drag = pan the view (left button is the box-select)
    pan = {'x': None, 'y': None}

    def on_pan_press(event):
        if event.button == 2 and event.inaxes is ax:   # 2 = middle button
            pan['x'], pan['y'] = event.xdata, event.ydata

    def on_pan_move(event):
        if pan['x'] is None or event.inaxes is not ax:
            return
        dx = event.xdata - pan['x']
        dy = event.ydata - pan['y']
        xlim, ylim = ax.get_xlim(), ax.get_ylim()
        ax.set_xlim(xlim[0] - dx, xlim[1] - dx)
        ax.set_ylim(ylim[0] - dy, ylim[1] - dy)
        fig.canvas.draw_idle()

    def on_pan_release(event):
        if event.button == 2:
            pan['x'] = pan['y'] = None

    def on_select(eclick, erelease):
        x0, y0 = eclick.xdata, eclick.ydata
        x1, y1 = erelease.xdata, erelease.ydata
        mask = (x > min(x0, x1)) & (x < max(x0, x1)) & (y > min(y0, y1)) & (y < max(y0, y1))
        new_sel = set(int(i) for i in np.nonzero(mask)[0]) - dismissed - locked
        if new_sel:
            history.append(new_sel)
            dismissed.update(new_sel)
            redraw()

    def do_undo(_=None):
        if history:
            dismissed.difference_update(history.pop())
            redraw()

    def do_reset(_=None):
        dismissed.clear()
        history.clear()
        redraw(keep_view=False)   # also reset the zoom to fit the whole series

    def do_done(_=None):
        plt.close(fig)

    def do_skip(_=None):
        state['skipped'] = True
        dismissed.clear()
        plt.close(fig)

    def do_cancel(_=None):
        # abort the WHOLE qualification and go back to the form (not just this
        # series); raised after the window closes
        state['canceled'] = True
        plt.close(fig)

    def do_help(_=None):
        try:
            from tkinter import messagebox
            # parent the dialog to the PLOT window so it pops over the plot
            # instead of raising the main program window behind it
            parent = getattr(getattr(fig.canvas, 'manager', None), 'window', None)
            messagebox.showinfo(
                'Manual point cut - help',
                'Drag a rectangle (left button) over points to DISMISS them (flag 5).\n'
                'Mouse wheel zooms around the cursor; middle-button drag pans.\n\n'
                'The points are NOT deleted: they stay in the sheet with flag 5 and\n'
                'their value blanked, so the manual cut stays traceable. Points already\n'
                'cut in the Depth review appear grayed and are kept dismissed.\n\n'
                'Undo   - undo the last box\n'
                'Reset  - clear the dismissals made here and reset the zoom\n'
                'Skip   - leave this series untouched (continue)\n'
                'Cancel - abort the whole qualification (shortcut: Esc)\n'
                'Done   - confirm and continue (shortcut: Enter)',
                parent=parent)
        except Exception:
            pass

    def on_key(event):
        if event.key == 'enter':
            do_done()
        elif event.key == 'escape':
            do_cancel()

    _selector = RectangleSelector(ax, on_select, useblit=True, button=[1],  # noqa: F841 (kept alive vs GC)
                                  minspanx=5, minspany=5, spancoords='pixels',
                                  interactive=True)
    extend_selection_beyond_axes(_selector, ax)   # drag past the plot's edge
    fig.canvas.mpl_connect('key_press_event', on_key)
    fig.canvas.mpl_connect('scroll_event', on_scroll)
    fig.canvas.mpl_connect('button_press_event', on_pan_press)
    fig.canvas.mpl_connect('motion_notify_event', on_pan_move)
    fig.canvas.mpl_connect('button_release_event', on_pan_release)

    # buttons along the bottom (kept referenced so the GC does not collect them)
    _buttons = []
    for i, (txt, cb) in enumerate([('Undo', do_undo), ('Reset', do_reset),
                                   ('Skip', do_skip), ('Help', do_help),
                                   ('Done', do_done), ('Cancel', do_cancel)]):
        bax = fig.add_axes([0.025 + i * 0.163, 0.04, 0.145, 0.07])
        b = Button(bax, txt)
        b.on_clicked(cb)
        _buttons.append(b)

    redraw()
    _theme.style_plot_window(fig, 'Manual point cut - %s' % label)  # app icon + title
    _show_and_wait(fig, tk_root)
    if state['canceled']:
        raise ManualCutCanceled()
    return None if state['skipped'] else dismissed


def trim_by_depth(data, tk_root=None, locked=None, progress=None):
    """Manual review of a mooring depth series. Returns the SET of row positions
    the operator dismissed (whole-row dismissal). Does not modify `data`; the
    caller flags those rows DISMISSED (5) and blanks their values."""
    got = manual_cut_panel(data['Depth (m)'].index.to_numpy(),
                           data['Depth (m)'].to_numpy(), 'Depth (m)', tk_root,
                           locked=locked, progress=progress,
                           depth=data['Depth (m)'], times=data.get('Datetime'))
    return set() if got is None else set(got)


def trim_selected_variable(data, name, tk_root=None, locked=None, progress=None):
    """Manual review of a single variable. Returns the SET of row positions the
    operator dismissed for that variable (excluding any `locked` rows already cut
    upstream). Does not modify `data`; the caller flags those points DISMISSED (5)
    for this variable and blanks the value."""
    got = manual_cut_panel(np.arange(len(data)), data[name].to_numpy(), name, tk_root,
                           locked=locked, progress=progress,
                           depth=data.get('Depth (m)'), times=data.get('Datetime'))
    return set() if got is None else set(got)


# QCS output subfolders where each instrument's qualified spreadsheets live
# (the tscp name is the same since the pre-v4 versions)
QUALIFIED_SUBFOLDERS = {
    'tscp': ('QCS qualified tscp data',),
    'hobo': ('QCS qualified hobo data',),
    'doppler': ('QCS qualified current data',),
}


def detect_qualified_layout(df):
    """'doppler' = qualified current-profiler table (per-cell rows with
    Flag_cur); 'hobo' = only temperature+light (has Luminosity, no Salinity);
    any other qualified spreadsheet is 'tscp' (Seaguard)."""
    cols = set(str(c) for c in df.columns)
    if 'Flag_cur' in cols or 'Horizontal speed (cm/s)' in cols:
        return 'doppler'
    if 'Luminosity (lux)' in cols and 'Salinity (PSU)' not in cols:
        return 'hobo'
    return 'tscp'


def build_database(instrument, file_list=None, input_path=None):
    """Single unification engine for qualified spreadsheets (Seaguard and HOBO).

    Input (one of the two):
    - file_list: qualified files chosen by hand (multi-selection); or
    - input_path: parent folder swept recursively looking for the QCS output
      subfolders ('QCS qualified tscp data' / 'QCS qualified hobo data').

    Rules (v4.0, replaces join_files_to_database):
    - ignores the report files (name starting with 'QCS_');
    - reads .csv (header on line 0 - the old header=1 corrupted csvs) and .xlsx;
    - validates each file: needs Datetime+Site and the layout must match
      the instrument (HOBO and Seaguard are NEVER stackable);
    - adds the 'Source file' column (provenance of each row);
    - sorts by Site+Datetime; removes exact duplicates (keeping the first,
      with a warning) and reports rows with the same Site+Datetime and different values.

    Returns (database, messages). Problems raise a ValueError with a
    self-localizing message ('build_database: ...').
    """
    _inst = str(instrument).strip().upper()
    expected_layout = ('hobo' if _inst == 'HOBO'
                       else 'doppler' if _inst == 'DOPPLER' else 'tscp')
    messages = []

    if file_list:
        files = [f.strip() for f in file_list if f and f.strip()]
    elif input_path:
        target_subfolders = QUALIFIED_SUBFOLDERS[expected_layout]
        files = []
        for root, _dirs, names in os.walk(input_path):
            if os.path.basename(root) in target_subfolders:
                for name in sorted(names):
                    if name.lower().endswith(('.csv', '.xlsx')) and not name.startswith('QCS_'):
                        files.append(os.path.join(root, name))
        if not files:
            raise ValueError("build_database: no qualified %s files found under:\n%s\n"
                             "(searched inside '%s' subfolders for .csv/.xlsx not named 'QCS_*')."
                             % (instrument, input_path, "'/'".join(target_subfolders)))
    else:
        raise ValueError('build_database: provide file_list or input_path.')

    frames = []
    for file_path in files:
        base = os.path.basename(file_path)
        if base.startswith('QCS_'):
            messages.append('Info: report file skipped: %s' % base)
            continue
        try:
            if file_path.lower().endswith('.xlsx'):
                df = pd.read_excel(file_path, header=0)
            else:
                df = pd.read_csv(file_path, header=0)
        except Exception as e:
            raise ValueError('build_database: could not read %s:\n%s' % (file_path, e)) from e
        missing = [c for c in ('Datetime', 'Site') if c not in df.columns]
        if missing:
            raise ValueError("build_database: %s does not look like a QCS qualified file "
                             "(missing column(s): %s).\nColumns found: %s"
                             % (base, ', '.join(missing), ', '.join(str(c) for c in df.columns[:12])))
        layout = detect_qualified_layout(df)
        if layout != expected_layout:
            raise ValueError("build_database: %s looks like a %s spreadsheet, but the selected "
                             "instrument is %s. HOBO, Seaguard and Doppler qualified files are "
                             "never stackable - unify them into separate databases."
                             % (base, layout.upper(), instrument))
        df['Source file'] = base
        frames.append(df)
        messages.append('Info: %s: %d rows' % (base, len(df)))

    if not frames:
        raise ValueError('build_database: no readable qualified files in the selection.')

    database = pd.concat(frames, ignore_index=True)
    database['Datetime'] = pd.to_datetime(database['Datetime'], errors='coerce')
    n_bad_ts = int(database['Datetime'].isna().sum())
    if n_bad_ts:
        messages.append('Warning: %d row(s) without a valid timestamp discarded.' % n_bad_ts)
        database = database[database['Datetime'].notna()]

    database = database.sort_values(['Site', 'Datetime'], kind='stable')

    # exact duplicates (same values in all columns, except the provenance)
    value_cols = [c for c in database.columns if c != 'Source file']
    n_before = len(database)
    database = database.drop_duplicates(subset=value_cols, keep='first')
    n_exact = n_before - len(database)
    if n_exact:
        messages.append('Warning: %d exact duplicate row(s) (same Site+Datetime+values) '
                        'discarded - kept the first occurrence.' % n_exact)

    # overlaps with DIFFERENT values: kept, but the operator needs to know.
    # What identifies a row is not the same in every layout: a Doppler table is
    # tidy (one row per record x depth CELL), so Site+Datetime repeats once per
    # cell BY CONSTRUCTION and keying on it alone reported every single row as
    # an overlap (measured: 12 of 12 on a 4-record x 3-cell session, v12.2.4).
    overlap_keys = ['Site', 'Datetime']
    if expected_layout == 'doppler':
        overlap_keys += [c for c in ('Column', 'Cell') if c in database.columns]
    overlap_mask = database.duplicated(subset=overlap_keys, keep=False)
    if overlap_mask.any():
        offenders = sorted(database.loc[overlap_mask, 'Source file'].unique())
        messages.append('Warning: %d row(s) share the same %s with DIFFERENT values '
                        '(overlapping qualifications?) - ALL kept; check the files: %s'
                        % (int(overlap_mask.sum()), '+'.join(overlap_keys),
                           ', '.join(offenders)))

    database.index = np.arange(len(database))
    for site, group in database.groupby('Site'):
        messages.append('Info: site %s: %d rows, %s to %s'
                        % (site, len(group), group['Datetime'].min(), group['Datetime'].max()))
    messages.append('Info: database built: %d file(s), %d rows, instrument %s.'
                    % (len(frames), len(database), instrument))
    return database, messages


def combine_hobo_replicates(replicates, temp_tol=0.5):
    """Combine N (2-4) redundant HOBO replicates of the SAME site/deployment,
    each already qualified independently, into a single series.

    Temperature: the MEAN of the replicates that are acceptable (Flag_T <= 2) at
    each timestamp. The between-replicate spread (max - min) is kept in a
    'Temperature spread (degC)' column; when it exceeds `temp_tol` (with >= 2
    acceptable replicates) the combined Flag_T is SUSPECT (3) - the replicates
    disagree, which is itself a QC signal.

    Light: the per-timestamp MAX of the NON-fouled readings (Flag_lux != 4).
    Fouling only attenuates light, so the brightest unfouled sensor is the most
    reliable. The combined light stays good (Flag_lux 1) while AT LEAST ONE
    replicate is unfouled, and becomes BAD (4) only once EVERY replicate is
    fouled - i.e. the usable window is extended to the last replicate to foul.
    (No naive averaging of light: that would mix clean + fouled sensors.)

    replicates: list of qualified HOBO DataFrames (2-4), each with columns
    'Datetime', 'Temperature (degC)', 'Luminosity (lux)', 'Flag_T', 'Flag_lux'
    (and optionally 'Site'). Returns (combined_df, messages)."""
    if len(replicates) < 2:
        raise ValueError('combine_hobo_replicates: need at least 2 replicates.')
    messages = []

    # align every replicate onto the first replicate's time grid (nearest match
    # within half the sampling interval, to absorb small clock differences)
    ref_times = pd.DatetimeIndex(pd.to_datetime(replicates[0]['Datetime'])).sort_values()
    step = ref_times.to_series().diff().median()
    tol = (step / 2) if (pd.notna(step) and step > pd.Timedelta(0)) else None
    aligned = []
    for r in replicates:
        a = r.copy()
        a['Datetime'] = pd.to_datetime(a['Datetime'])
        a = a.set_index('Datetime')
        a = a[~a.index.duplicated(keep='first')].sort_index()
        aligned.append(a.reindex(ref_times, method='nearest', tolerance=tol))

    def stack(name):
        return pd.concat([a[name] for a in aligned], axis=1, ignore_index=True)

    T = stack('Temperature (degC)')
    FT = stack('Flag_T').apply(pd.to_numeric, errors='coerce')
    L = stack('Luminosity (lux)')
    FL = stack('Flag_lux').apply(pd.to_numeric, errors='coerce')

    # replicates configured at DIFFERENT sampling intervals leave every other
    # row of the finer grid without a partner - say so, or the holes in the
    # spread column read as noise
    steps = [pd.DatetimeIndex(pd.to_datetime(r['Datetime'])).to_series()
             .diff().median() for r in replicates]
    if len({s for s in steps if pd.notna(s)}) > 1:
        messages.append(
            'Warning: the replicates were configured at DIFFERENT sampling '
            'intervals (%s). The combined series follows the first replicate; '
            'rows covered by a single replicate carry no spread value.'
            % ', '.join(str(s) for s in steps))

    # temperature: mean over the acceptable (Flag_T <= 2) replicates
    t_ok = (FT <= 2) & T.notna()
    T_ok = T.where(t_ok)
    n_t = t_ok.sum(axis=1)
    temp_mean = T_ok.mean(axis=1)
    # spread with a SINGLE covering replicate is EMPTY, not 0: there was
    # nothing to compare, and a 0 would read as 'the replicates agreed
    # perfectly' (v11.5; same convention as the single-sound-replicate case)
    temp_spread = (T_ok.max(axis=1) - T_ok.min(axis=1)).where(n_t >= 2, np.nan)
    flag_t = pd.Series(9, index=ref_times)              # none acceptable -> missing
    flag_t[n_t >= 1] = 1                                # at least one good
    flag_t[(n_t >= 2) & (temp_spread > temp_tol)] = 3   # replicates disagree -> suspect

    # light: max of the non-fouled (Flag_lux != 4) readings
    l_clean = (FL != 4) & L.notna()
    n_clean = l_clean.sum(axis=1)
    lux_comb = L.where(l_clean).max(axis=1).where(n_clean >= 1, L.max(axis=1))
    flag_lux = pd.Series(9, index=ref_times)            # all light missing
    flag_lux[L.notna().any(axis=1)] = 4                 # present but all fouled -> bad
    flag_lux[n_clean >= 1] = 1                          # at least one unfouled -> good

    out = pd.DataFrame({
        'Datetime': ref_times,
        'Temperature (degC)': temp_mean.round(4).values,
        'Temperature spread (degC)': temp_spread.round(4).values,
        'Luminosity (lux)': lux_comb.round(4).values,
        'Flag_T': flag_t.values.astype(int),
        'Flag_lux': flag_lux.values.astype(int),
    })
    if 'Site' in replicates[0].columns and len(replicates[0]):
        out.insert(1, 'Site', replicates[0]['Site'].iloc[0])

    messages.append('Info: combined %d HOBO replicates over %d aligned timestamps.'
                    % (len(replicates), len(out)))
    n_disagree = int((flag_t == 3).sum())
    if n_disagree:
        messages.append('Warning: %d timestamp(s) where the replicate temperatures disagree by '
                        'more than %.2f degC - combined Flag_T set to SUSPECT there.'
                        % (n_disagree, temp_tol))
    all_fouled = flag_lux[flag_lux == 4]
    if len(all_fouled):
        messages.append('Info: combined light usable until %s (all replicates fouled after that).'
                        % pd.Timestamp(all_fouled.index[0]))
    return out, messages

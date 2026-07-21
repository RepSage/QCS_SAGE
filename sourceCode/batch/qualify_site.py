# -*- coding: utf-8 -*-
"""Batch-qualify one SITE for one SEMESTER (HOBO first, then SEAGUARD sensors,
   then DOPPLER), organising the results under CLAUDE\\<inst>\\qualified with a
   uniform semester-based name and every applicable DataView panel.

   The semester tag unifies the two corpora: the same expedition is labelled
   'ABRIL 2019' by Seaguard and 'MAI 2019' by HOBO, but both are 2019S1.

   Layout:  qualified\\<YEAR>S<n>\\<SITE>\\<NAME>.csv
            qualified\\<YEAR>S<n>\\<SITE>\\DataView\\      all applicable panels
            qualified\\<YEAR>S<n>\\<SITE>\\reports\\       QCS_* reports
            qualified\\<YEAR>S<n>\\<SITE>\\provenance.txt  what each name came from
   Name:    <SITE>_<YEAR>S<n>_<INSTRUMENT>[_<TIPO>][_<k>]_QLF
            (_k only when the semester holds several of that kind, by date -
             a semester can span two expeditions, e.g. ABRIL + JUNHO 2019)

   Usage: qualify_site.py <SITE> --sem 2019S1
"""
import sys, os, re, glob, shutil, tempfile
import datetime as _dt

# QCS modules live one level up (sourceCode\) from this batch\ folder
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import matplotlib; matplotlib.use('Agg')
import QCS_Theme as _t
_t.install_output_redirect = lambda *a, **k: type('S', (), {'history': [], 'set_sink': lambda *a, **k: None, 'write': lambda *a, **k: None, 'flush': lambda *a, **k: None})()
_t.install_crash_handler = lambda *a, **k: None
import QCS_Main as qm
import QCS_DataHandler as dh
import QCS_DataView as view
import pandas as pd

ROOT = r"\\Abrolhos\Projetos\Seaguard & HOBO\CLAUDE"
SG_RAW, SG_QLF = os.path.join(ROOT, 'SEAGUARD', 'raw'), os.path.join(ROOT, 'SEAGUARD', 'qualified')
H_RAW, H_QLF = os.path.join(ROOT, 'HOBO', 'raw'), os.path.join(ROOT, 'HOBO', 'qualified')
PT2NUM = {'JAN': 1, 'FEV': 2, 'MAR': 3, 'ABR': 4, 'MAI': 5, 'JUN': 6, 'JUL': 7, 'AGO': 8,
          'SET': 9, 'OUT': 10, 'NOV': 11, 'DEZ': 12, 'JANEIRO': 1, 'FEVEREIRO': 2,
          'MARÇO': 3, 'ABRIL': 4, 'MAIO': 5, 'JUNHO': 6, 'JULHO': 7, 'AGOSTO': 8,
          'SETEMBRO': 9, 'OUTUBRO': 10, 'NOVEMBRO': 11, 'DEZEMBRO': 12}


def log(m):
    print(m, flush=True)


def sem_tag(campaign):
    """'1 - ABRIL 2019' -> '2019S1'; 'RRDM 6a MAI 2019' -> '2019S1'."""
    yr = re.search(r'(19|20)\d\d', campaign)
    mon = None
    for w in re.findall(r'[A-Za-zÇÃÁÉÍÓÚçãáéíóú]+', campaign.upper()):
        if w in PT2NUM:
            mon = PT2NUM[w]
            break
    if not yr or not mon:
        return None
    return '%sS%d' % (yr.group(0), 1 if mon <= 6 else 2)


# ---------------- headless qualification driver ----------------
_root = qm.Tk(); _root.withdraw(); _fr = qm.ttk.Frame(_root); _fr.pack()
qm.build_qualification_tab(_fr, _root)
DIALOGS = []
qm.messagebox.showinfo = lambda *a, **k: None
qm.messagebox.showwarning = lambda *a, **k: DIALOGS.append(('warn', a))
qm.messagebox.showerror = lambda *a, **k: DIALOGS.append(('error', a))
qm.messagebox.askyesno = lambda *a, **k: True
qm.review_light_window = lambda lux, label: lux.get('proposed_cutoff')
qm.data._show_and_wait = lambda *a, **k: None
qm.save_user_prefs = lambda *a, **k: None
qm.log_line = lambda m: None


def _se(w, v):
    w.delete(0, 'end'); w.insert(0, v)


_REF_CACHE = {}


def replicate_reference(site, t0, t1):
    """Independent reference for the replicate referee: the mean daily
    temperature of every ALREADY-QUALIFIED HOBO product of OTHER sites in the
    same window. Other sites share the regional forcing but not this site's
    logger, so they arbitrate empirically - no assumption about what the season
    'should' do. Returns None when nothing contemporaneous exists."""
    key = (site, str(t0)[:10], str(t1)[:10])
    if key in _REF_CACHE:
        return _REF_CACHE[key]
    cols = []
    for p in glob.glob(os.path.join(H_QLF, '*', '**', '*_HOBO*_QLF.csv'), recursive=True):
        if os.path.basename(p).startswith(site + '_'):
            continue                       # never let the site arbitrate itself
        try:
            d = pd.read_csv(p, usecols=lambda c: c in ('Datetime', 'Temperature (degC)', 'Flag_T'))
        except Exception:
            continue
        d['Datetime'] = pd.to_datetime(d['Datetime'], errors='coerce')
        d = d[(d['Datetime'] >= t0) & (d['Datetime'] <= t1)]
        if 'Flag_T' in d.columns:
            d = d[pd.to_numeric(d['Flag_T'], errors='coerce') <= 2]
        if len(d) < 200:
            continue
        cols.append(d.set_index('Datetime')['Temperature (degC)'].resample('D').mean())
    ref = pd.concat(cols, axis=1).mean(axis=1) if cols else None
    _REF_CACHE[key] = ref
    return ref


def run_qualification(files, input_type, data_type, site, out_name, co2=None):
    DIALOGS.clear()
    outdir = tempfile.mkdtemp(prefix='q_')
    _se(qm.fileNames_entry, ';'.join(files) if isinstance(files, list) else files)
    qm.inputType_combobox.set(input_type)
    qm.inputType_combobox.event_generate('<<ComboboxSelected>>')
    if input_type != 'HOBO' and data_type:
        qm.dType_combobox.set(data_type)
        qm.dType_combobox.event_generate('<<ComboboxSelected>>')
    _se(qm.outputPath_entry, outdir); _se(qm.outputName_entry, out_name)
    qm.outputFilesFormat_combobox.set('.csv')
    # Seaguard bins record GMT; the CO2 logger and the HOBO exports are LOCAL
    # (GMT-3). Correct the Seaguard side so the whole corpus shares one
    # timebase and the CO2 merge aligns (proven on PAB1: the txt is named
    # 1525-1555 and the uncorrected cast sat at 18:13-19:07).
    qm.correct_gmt3h.set(input_type == 'Seaguard')
    qm.remove_bad.set(False); qm.remove_suspect.set(False)
    qm.select_profile_data.set(False); qm.check_variables.set(False)
    _se(qm.siteSelect_entry, site)
    qm._co2_file = co2 or ''
    if input_type == 'HOBO':
        qm.replicate_var.set(str(len(files) if isinstance(files, list) else 1))
    try:
        qm.start_qualification()
    except Exception as e:
        return None, None, 'EXC %r' % (e,)
    hits = glob.glob(os.path.join(outdir, '**', out_name + '.csv'), recursive=True)
    if not hits:
        return None, None, _dialog_reason(DIALOGS)
    return hits[0], outdir, None


def _dialog_reason(dialogs):
    """The reason out of a messagebox call, WITHOUT assuming its shape: the old
    DIALOGS[0][1][1].split('\\n')[2] raised IndexError on any shorter message,
    and that killed the whole site instead of just reporting one failure."""
    if not dialogs:
        return 'no table produced (no dialog)'
    try:
        args = dialogs[0][1]
        msg = str(args[1]) if len(args) > 1 else str(args)
    except Exception:
        msg = str(dialogs[0])
    lines = [ln.strip() for ln in msg.split('\n') if ln.strip()]
    for ln in lines:                       # the informative line, when present
        if ln.lower().startswith(('the qualification', 'error', 'location')):
            continue
        if len(ln) > 12:
            return ln[:110]
    return (lines[-1] if lines else 'no table produced')[:110]


# ---------------- cast clustering (the reader's own 15-min rule) ----------------
SESS = re.compile(r'(\d+-\d+)-(\d+)-(\d{4}-\d\d-\d\dT\d\d-\d\d-\d\d)')


def casts_in(group_dir):
    if not os.path.isdir(group_dir):
        return []
    timed = []
    for d in sorted(os.listdir(group_dir)):
        m = SESS.match(d)
        b = os.path.join(group_dir, d, 'Data000.bin')
        if m and os.path.isfile(b):
            timed.append((_dt.datetime.strptime(m.group(3), '%Y-%m-%dT%H-%M-%S'), b))
    timed.sort()
    out, cur = [], []
    for st, b in timed:
        if cur and (st - cur[-1][0]).total_seconds() > 15 * 60:
            out.append(cur); cur = []
        cur.append((st, b))
    if cur:
        out.append(cur)
    return [(c[0][0], [b for _, b in c]) for c in out]      # (start, [bins])


# ---------------- CO2 pairing by TIME OVERLAP ----------------
_co2_range_cache = {}


def _co2_range(txt):
    """(start, end) of a CO2 export, from its own Year/Month/Day columns
    (logger clock = LOCAL time). None when unreadable."""
    if txt in _co2_range_cache:
        return _co2_range_cache[txt]
    rng = None
    try:
        d = pd.read_csv(txt, skiprows=[1])
        st = pd.to_datetime(dict(year=d['Year'], month=d['Month'], day=d['Day'],
                                 hour=d['Hour'], minute=d['Minute'],
                                 second=d['Second']), errors='coerce').dropna()
        if len(st):
            rng = (st.min(), st.max())
    except Exception:
        rng = None
    _co2_range_cache[txt] = rng
    return rng


def pick_co2(co2s, cast_start_gmt):
    """The CO2 txt whose own time range covers the cast (both in LOCAL time -
    the cast folder stamp is GMT, so shift it by -3 h). 1 h of slack on each
    side covers logger start-up before deployment. None when nothing matches
    (never guess: a wrong pairing is worse than an empty column)."""
    local = cast_start_gmt - _dt.timedelta(hours=3)
    best, best_dur = None, None
    for c in co2s:
        rng = _co2_range(c)
        if not rng:
            continue
        t0, t1 = rng
        if t0 - pd.Timedelta(hours=1) <= local <= t1 + pd.Timedelta(hours=1):
            # several exports can cover the cast (a full overnight file AND its
            # per-cast trim start at the same launch); prefer the SHORTEST one -
            # that is the export made for this cast
            dur = (t1 - t0).total_seconds()
            if best is None or dur < best_dur:
                best, best_dur = c, dur
    return best


# ---------------- plan: every product of this site+semester ----------------
def plan(site, sem):
    """[{kind, tipo, campaign, start, files, co2}] across EVERY campaign of the
    semester (a semester can hold two expeditions)."""
    items = []
    # HOBO
    sdir = os.path.join(H_RAW, site)
    if os.path.isdir(sdir):
        for camp in sorted(os.listdir(sdir)):
            if not os.path.isdir(os.path.join(sdir, camp)) or sem_tag(camp) != sem:
                continue
            # a site's planilha folder can hold SEVERAL deployments, not just
            # the replicates of one (PAB3 8a = a reef-top logger AND a wall
            # logger spanning 2016-2018) - group them from the data
            pl = os.path.join(sdir, camp, 'planilha')
            dropped = _excluded_in(pl)
            for grp, span in _group_replicates(_sheets(pl)):
                items.append({'kind': 'HOBO', 'tipo': None, 'campaign': camp,
                              'start': span[0] if span else camp, 'files': grp,
                              'co2': None, 'excluded': dropped})
    # SEAGUARD / DOPPLER
    for camp in sorted(os.listdir(SG_RAW)):
        cdir = os.path.join(SG_RAW, camp, site)
        if not os.path.isdir(cdir) or sem_tag(camp) != sem:
            continue
        for tipo in sorted(os.listdir(cdir)):
            tdir = os.path.join(cdir, tipo)
            if not os.path.isdir(tdir):
                continue
            co2s = [c for c in sorted(glob.glob(os.path.join(tdir, 'MINICO2', '*.txt')))
                    if not os.path.basename(c).startswith('NOTA')]
            for kind, grp in (('SEAGUARD', 'SENSORES'), ('DOPPLER', 'DOPPLER')):
                cl = casts_in(os.path.join(tdir, 'DATA', grp))
                for start, bins in cl:
                    # CO2 pairs by TIME OVERLAP (the old '1 txt and 1 cast only'
                    # rule left 17 available files unused and 3 mismatched)
                    items.append({'kind': kind, 'tipo': tipo, 'campaign': camp,
                                  'start': start, 'files': bins,
                                  'co2': pick_co2(co2s, start) if kind == 'SEAGUARD' else None})
    # name them: _k only when the semester holds several of that kind+tipo
    from collections import defaultdict
    groups = defaultdict(list)
    for it in items:
        groups[(it['kind'], it['tipo'])].append(it)
    for (kind, tipo), lst in groups.items():
        lst.sort(key=lambda x: str(x['start']))
        for i, it in enumerate(lst, start=1):
            suf = '' if len(lst) == 1 else '_%d' % i
            it['name'] = '%s_%s_%s%s%s_QLF' % (site, sem, kind,
                                               ('_' + tipo) if tipo else '', suf)
    return items


# ---------------- the two HOBO-only buckets (_PISCINAS / _EXPERIMENTOS) -------
# Replicates excluded as FAULTY after diagnosis. A redundant pair only helps
# when both loggers work: the combine averages them, so a drifting sensor
# contaminates the mean (the QC flags the disagreement SUSPECT, but a suspect
# flag does not fix the value, and dropping the suspect rows would throw away
# the sound replicate too). Each entry must carry the evidence.
EXCLUDED_REPLICATES = {
    'HOBO1_PLES_A1_17032022_22092022.xlsx':
        'faulty sensor: from ~2022-05-01 it loses the seasonal signal (flat '
        '28.5-29.8 degC, even rising to 29.79 in September) while its twin and '
        'SEVEN contemporaneous loggers at other sites all cool 28.5->24.4 degC. '
        'Change-correlation with the regional signal 0.10 (twin: 0.92), bias '
        '+2.42 degC, own seasonal amplitude 0.35x regional. Its own individual '
        'QC passed it as GOOD - no single-series test catches a sensor stuck '
        'on a plausible value.',
    'PAB_RRDM_290120_110521.csv':
        'replicate referee (v9.0): change-correlation with the independent '
        'reference -0.24 (twin +0.91), bias +1.07 degC - it does not follow the '
        'regional signal at all.',
    'HOBO2_PAB3_A3_181023_220324.xlsx':
        'replicate referee (v9.0): change-correlation +0.35 (twin +0.94), bias '
        '+0.90 degC.',
    'HOBO1_PLES_A1_181023_300324_duvidoso.xlsx':
        'replicate referee (v9.0): seasonal swing 3.76x the reference (twin '
        '1.48x) with correlation +0.92 vs +1.00 - an exaggerated amplitude. The '
        'field name already reads "duvidoso" (doubtful).',
    'HOBO1_ESQNORTE_B2_290824_180325 (ERRO).xlsx':
        'replicate referee (v9.0): change-correlation +0.47 (twin +0.88), bias '
        '+4.81 degC - the largest offset in the corpus. The field name already '
        'reads "(ERRO)".',
    'HOBO1_ESQRODO_B1_160325_110925.xlsx':
        'replicate referee (v9.0): change-correlation -0.20 (twin +0.89), bias '
        '+3.15 degC - it moves against the regional signal.',
    # NOT excluded, deliberately: ESQCENTRAL 2024S1
    # (HOBO1_ESQCENTRAL_B3_281023_050424.xlsx). The referee names replicate 1 on
    # the seasonal-swing criterion (the other replicate swings only 0.48x the
    # reference, i.e. damped), but that replicate has the SLIGHTLY HIGHER
    # correlation (+0.90 vs +0.88) - the two criteria point opposite ways, so
    # this one is left for the operator to review rather than auto-dropped.
}


def _excluded_in(pl):
    """[(file, reason)] excluded from this planilha folder."""
    return [(os.path.basename(f), EXCLUDED_REPLICATES[os.path.basename(f)])
            for f in glob.glob(os.path.join(pl, '*.*'))
            if os.path.basename(f) in EXCLUDED_REPLICATES]


def _sheets(pl):
    """The exports of a planilha folder, ONE per logger: the corpus rule is
    '.xlsx, falling back to .csv only when that logger has no xlsx', so a plain
    'all xlsx else all csv' silently drops a replicate exported as csv next to a
    sibling exported as xlsx. Faulty replicates (EXCLUDED_REPLICATES) are
    dropped here, so every path that lists sheets honours the exclusion."""
    by_logger = {}
    for f in sorted(glob.glob(os.path.join(pl, '*.xlsx'))) + sorted(glob.glob(os.path.join(pl, '*.csv'))):
        if os.path.basename(f) in EXCLUDED_REPLICATES:
            continue
        # EXACT stem: one logger's xlsx and csv share it, while HOBO1 and HOBO2
        # (which ARE separate loggers) must stay apart
        by_logger.setdefault(os.path.splitext(os.path.basename(f))[0], []).append(f)
    out = []
    for _k, fs in by_logger.items():
        xl = [f for f in fs if f.lower().endswith('.xlsx')]
        out.append(xl[0] if xl else fs[0])
    return sorted(out)


def _span(path):
    """(start, end) of an export, straight from the reader; None if unreadable."""
    try:
        df, _ = dh.read_hobo({'raw_data_path': os.path.dirname(path),
                              'file_name': os.path.basename(path),
                              'input_type': 'HOBO', 'correct_gmt3h': False}, {})
        t = pd.to_datetime(df['Datetime'])
        return (t.min(), t.max())
    except Exception:
        return None


_REPL_TOL = pd.Timedelta(days=1)


def _group_replicates(files):
    """Group exports into DEPLOYMENTS from the DATA, not the names. Returns
    [(files, span)].

    A planilha folder does NOT always hold one deployment's replicates:
      - _EXPERIMENTOS: RH30 21a = 5 files / 3 experiments;
      - even a plain SITE: PAB3 8a = 'PAB3_200419_TOPO' (reef top) AND
        'PAB3_30062016_PAREDE' (wall, 2016-2018) - two different loggers.
    Averaging those as replicates is simply wrong. Names cannot decide it (the
    same SET's replicates get spelled 'ExpIncubacaoMacroalgas' vs
    'Expincubacaorodolito'; dates appear as both 260326 and 26032026), but the
    data can: replicates are deployed and recovered TOGETHER, so require BOTH
    ends within a day. Mere overlap is not enough - the 5-month BRITAS series
    contains the 1-day incubation and would swallow it."""
    spans = {f: _span(f) for f in files}
    groups = []
    for f in sorted([x for x in files if spans[x]], key=lambda x: spans[x][0]):
        s, e = spans[f]
        for g in groups:
            gs, ge = g['span']
            if abs(s - gs) <= _REPL_TOL and abs(e - ge) <= _REPL_TOL:
                g['files'].append(f)
                g['span'] = (min(s, gs), max(e, ge))
                break
        else:
            groups.append({'files': [f], 'span': (s, e)})
    for f in files:                       # unreadable: its own group, let it fail loudly
        if not spans[f]:
            groups.append({'files': [f], 'span': None})
    return [(g['files'], g['span']) for g in groups]


def _station_of(subpath, files):
    """Label for an experiment: the RH/centroid station it belongs to."""
    hay = subpath + ' ' + ' '.join(os.path.basename(f) for f in files)
    m = re.search(r'RH\s*_?(\d{1,2})', hay, re.IGNORECASE)
    if m:
        return 'RH%s' % m.group(1)
    m = re.search(r'CENTROID\w*\s*(\d+)', hay, re.IGNORECASE)
    if m:
        return 'CENTROID%s' % m.group(1)
    leaf = subpath.split(os.sep)[-1] if subpath and subpath != '.' else 'EXPERIMENTO'
    return (re.sub(r'[^A-Za-z0-9]+', '_', leaf).strip('_').upper() or 'EXPERIMENTO')[:24]


def _replicate_key(path):
    """Normalized stem used to group REPLICATES of one logger deployment: drop a
    leading/trailing 'HOBO<n>' and every separator. One _EXPERIMENTOS planilha
    folder can hold SEVERAL experiments (e.g. RH30 21a = incubation SET 2 +
    incubation + BRITAS, 5 files / 3 experiments); averaging those together as
    replicates would be plain wrong."""
    s = os.path.splitext(os.path.basename(path))[0]
    s = re.sub(r'(?i)^hobo\s*\d*[_\-\s]*', '', s)
    s = re.sub(r'(?i)[_\-\s]*hobo\s*\d*$', '', s)
    return re.sub(r'[^a-z0-9]+', '', s.lower())


def _md5(p):
    import hashlib
    h = hashlib.md5()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def _bucket_order(name):
    """_NA last: a bucket with an explicit DENTRO/FORA is the authoritative copy
    when the same export was archived twice (the field archive keeps per-person
    folders, e.g. PISCINAS\\CLARA\\HOBOs holds a byte-identical copy of
    PISCINAS\\FERNANDO\\SGOM\\DENTRO\\HOBOs)."""
    return (1 if name.endswith('_NA') else 0, name)


def plan_buckets(sem):
    """Products of the HOBO-only buckets for this semester."""
    items = []
    # _PISCINAS: <bucket>\<campaign>\planilha  - the bucket IS the site, and the
    # sheets in one campaign are replicates of that one pool deployment
    base = os.path.join(H_RAW, '_PISCINAS')
    if os.path.isdir(base):
        for bucket in sorted(os.listdir(base), key=_bucket_order):
            bdir = os.path.join(base, bucket)
            if not os.path.isdir(bdir):
                continue
            for camp in sorted(os.listdir(bdir)):
                if not os.path.isdir(os.path.join(bdir, camp)) or sem_tag(camp) != sem:
                    continue
                files = _sheets(os.path.join(bdir, camp, 'planilha'))
                if files:
                    items.append({'bucket': '_PISCINAS', 'site': bucket, 'campaign': camp,
                                  'subpath': '', 'files': files})
    # _EXPERIMENTOS: <campaign>\<subpath>\planilha, grouped by replicate key
    base = os.path.join(H_RAW, '_EXPERIMENTOS')
    if os.path.isdir(base):
        for camp in sorted(os.listdir(base)):
            cdir = os.path.join(base, camp)
            if not os.path.isdir(cdir) or sem_tag(camp) != sem:
                continue
            for root, _d, _f in os.walk(cdir):
                if os.path.basename(root) != 'planilha':
                    continue
                files = _sheets(root)
                if not files:
                    continue
                sub = os.path.relpath(os.path.dirname(root), cdir)
                for grp, _unused_span in _group_replicates(files):
                    items.append({'bucket': '_EXPERIMENTOS', 'site': _station_of(sub, grp),
                                  'campaign': camp, 'subpath': '' if sub == '.' else sub,
                                  'files': sorted(grp)})
    # drop byte-identical re-archives: the field archive stores some exports
    # twice (a per-person folder AND the site/treatment folder), so the same
    # data would otherwise be qualified twice under two different site labels
    seen, keep = {}, []
    for it in items:
        sig = tuple(sorted(_md5(f) for f in it['files']))
        if sig in seen:
            log('    (skipped %s/%s %s: byte-identical to %s)'
                % (it['bucket'], it['site'], it['campaign'], seen[sig]))
            continue
        seen[sig] = '%s/%s' % (it['bucket'], it['site'])
        keep.append(it)
    items = keep

    # name + number within (bucket, site)
    from collections import defaultdict
    g = defaultdict(list)
    for it in items:
        g[(it['bucket'], it['site'])].append(it)
    for (_b, site), lst in g.items():
        lst.sort(key=lambda x: (x['campaign'], os.path.basename(x['files'][0])))
        for i, it in enumerate(lst, start=1):
            suf = '' if len(lst) == 1 else '_%d' % i
            it['name'] = '%s_%s_HOBO%s_QLF' % (site, sem, suf)
    return items


def do_buckets(sem):
    out = []
    for it in plan_buckets(sem):
        name, site = it['name'], it['site']
        log('[%s] %s <- %s%s (%d file[s])'
            % (it['bucket'], name, it['campaign'],
               '/' + it['subpath'] if it['subpath'] else '', len(it['files'])))
        try:
            csv, root, err = run_qualification(it['files'], 'HOBO', None, site, name)
            if not csv:
                log('    FAILED: %s' % err); out.append((name, None, 0, err)); continue
            dest = os.path.join(H_QLF, sem, it['bucket'], site)
            fc = assemble(csv, root, dest, name)
            n = render(fc, dest, 'HOBO', None, name)
            log('    OK  %d panel(s)' % n)
            out.append((name, fc, n, None))
            write_provenance(dest, name,
                             '%s\n    bucket   : %s\n    campaign : %s\n    subpath  : %s\n'
                             '    inputs   : %s'
                             % (name, it['bucket'], it['campaign'], it['subpath'] or '-',
                                ' | '.join(os.path.basename(x) for x in it['files'])))
        except Exception as e:
            import traceback; traceback.print_exc()
            log('    EXC: %s' % str(e)[:90])
            out.append((name, None, 0, 'EXC %s' % str(e)[:80]))
    return out


PARAM_KEYS = ['Temperature (degC)', 'Salinity (PSU)', 'Conductivity (mS/cm)', 'Density (kg/m3)',
              'O2 level (uM)', 'PAR (umol/m2/s)', 'Turbidity (FTU)', 'Chlorophyll (ug/L)', 'pH',
              'Dissolved organic matter (ppb)', 'Soundspeed (m/s)', 'Pressure (dbar)',
              'CO2 Level (ppm)', 'Luminosity (lux)']


def make_settings(site, params, year, dtype):
    return {'siteList': [site], 'parameterList': list(params), 'filterByYear': year,
            'tendencyLines': False, 'linearRegressionDegree': 1, 'viewDataPoints': True,
            'fixedScale': False, 'scaleSettings': {}, 'xAxisStart': None, 'xAxisEnd': None,
            'depthAxisMin': None, 'depthAxisMax': None, 'dataType': dtype,
            'latitude': -17.96, 'longitude': -38.70, 'tsParam': 'Conservative Temperature'}


def write_provenance(dest, name, block):
    """Idempotent: re-running a semester must not append the same entry twice
    (an accidental re-run duplicated 24 provenance files once already)."""
    p = os.path.join(dest, 'provenance.txt')
    if os.path.exists(p):
        blocks = [b for b in open(p, encoding='utf-8').read().split('\n\n') if b.strip()]
        blocks = [b for b in blocks if b.split('\n')[0].strip() != name]
    else:
        blocks = []
    blocks.append(block.strip('\n'))
    with open(p, 'w', encoding='utf-8') as f:
        f.write('\n\n'.join(blocks) + '\n\n')


def assemble(csv, qlf_root, dest, name):
    os.makedirs(dest, exist_ok=True)
    final = os.path.join(dest, name + '.csv')
    shutil.copy2(csv, final)
    rep = os.path.join(dest, 'reports'); os.makedirs(rep, exist_ok=True)
    for f in glob.glob(os.path.join(qlf_root, '**', 'QCS_*'), recursive=True):
        if os.path.isfile(f):
            shutil.copy2(f, os.path.join(rep, '%s__%s' % (name, os.path.basename(f))))
    return final


def render(final_csv, dest, kind, tipo, name):
    # one folder PER PRODUCT: the panels are named after site/semester/year, so
    # several casts of the same site+semester would overwrite each other
    dv = os.path.join(dest, 'DataView', name); os.makedirs(dv, exist_ok=True)
    inst = {'HOBO': 'HOBO', 'DOPPLER': 'Doppler'}.get(kind, 'Seaguard')
    db, _ = dh.build_database(inst, file_list=[final_csv])
    db['Datetime'] = pd.to_datetime(db['Datetime'])
    site = str(db['Site'].iloc[0])
    year = int(db['Datetime'].dt.year.mode().iloc[0])
    before = set(glob.glob(os.path.join(dv, '*.svg')))
    cwd = os.getcwd(); os.chdir(dv)
    try:
        if kind == 'DOPPLER':
            view.plot_doppler_panels(db, dv, label=site)
        elif kind == 'HOBO':
            view.plot_hobo_params_at_site(db, make_settings(
                site, ['Temperature (degC)', 'Luminosity (lux)'], year, 'HOBO'), site)
        else:
            params = [p for p in PARAM_KEYS if p in db.columns
                      and not db[p].isna().all() and p != 'Luminosity (lux)']
            st = make_settings(site, params, year,
                               'TSCP Mooring' if tipo == 'FUNDEIO' else 'TSCP Profile')
            if tipo == 'FUNDEIO':
                view.plot_database_panel1(db, st)
                view.plot_database_panel2(db, st)
            else:
                view.plot_database_panel3(db, st)
            try:
                view.plot_TS_diagram(db, st)
            except Exception as e:
                log('      TS skipped: %s' % str(e)[:70])
    except Exception as e:
        log('      RENDER EXC: %s' % str(e)[:80])
    finally:
        os.chdir(cwd); view.plt.close('all')
    return len(set(glob.glob(os.path.join(dv, '*.svg'))) - before)


def do_site(site, sem):
    items = plan(site, sem)
    if os.environ.get('QCS_SG_ONLY'):     # timebase re-run: HOBO is already local
        items = [i for i in items if i['kind'] != 'HOBO']
    if not items:
        log('%s / %s : nothing to qualify' % (site, sem)); return []
    done = []
    for it in items:
        kind, name = it['kind'], it['name']
        dtype = ('TSCP Doppler' if kind == 'DOPPLER' else None if kind == 'HOBO'
                 else 'TSCP Mooring' if it['tipo'] == 'FUNDEIO' else 'TSCP Profile')
        log('[%s] %s <- %s%s%s' % (kind, name, it['campaign'],
                                   '/' + it['tipo'] if it['tipo'] else '',
                                   ' +CO2' if it['co2'] else ''))
        # one product must never take the whole site down with it
        try:
            files = it['files'] if kind == 'HOBO' else it['files'][0]
            # arm the replicate referee for multi-replicate HOBO deployments
            if kind == 'HOBO' and isinstance(files, list) and len(files) > 1:
                span = it.get('start')
                t0 = pd.Timestamp(span) if span and not isinstance(span, str) else None
                if t0 is not None:
                    qm.set_replicate_reference(
                        replicate_reference(site, t0 - pd.Timedelta(days=1),
                                            t0 + pd.Timedelta(days=400)))
            else:
                qm.set_replicate_reference(None)
            csv, root, err = run_qualification(files, 'HOBO' if kind == 'HOBO' else 'Seaguard',
                                               dtype, site, name, co2=it['co2'])
            if not csv:
                log('    FAILED: %s' % err); done.append((name, None, 0, err)); continue
            dest = os.path.join(H_QLF if kind == 'HOBO' else SG_QLF, sem, site)
            fc = assemble(csv, root, dest, name)
            n = render(fc, dest, kind, it['tipo'], name)
            log('    OK  %d panel(s)' % n)
            done.append((name, fc, n, None))
            # provenance: the semester tag drops the campaign label, so record it.
            # A Seaguard input is always '<session folder>\Data000.bin': name the
            # SESSION (the file name alone identifies nothing).
            srcs = it['files'] if isinstance(it['files'], list) else [it['files']]
            labels = [os.path.basename(os.path.dirname(x))
                      if os.path.basename(x).lower().startswith('data') else os.path.basename(x)
                      for x in srcs]
            block = ('%s\n    campaign : %s\n    tipo     : %s\n    cast     : %s\n'
                     '    inputs   : %s\n    co2      : %s'
                     % (name, it['campaign'], it['tipo'] or '-', it['start'],
                        ' | '.join(labels),
                        os.path.basename(it['co2']) if it['co2'] else '-'))
            for fn, why in it.get('excluded') or []:
                block += '\n    EXCLUDED : %s\n               (%s)' % (fn, why)
            write_provenance(dest, name, block)
        except Exception as e:
            import traceback; traceback.print_exc()
            log('    EXC: %s' % str(e)[:90])
            done.append((name, None, 0, 'EXC %s' % str(e)[:80]))
    return done


if __name__ == '__main__':
    site = sys.argv[1]
    sem = sys.argv[sys.argv.index('--sem') + 1]
    res = do_site(site, sem)
    log('\n=== %s / %s : %d product(s) ===' % (site, sem, len(res)))
    for n, f, k, err in res:
        log('  %-46s %s' % (n, ('%d panel(s)' % k) if f else 'FAILED: %s' % err))

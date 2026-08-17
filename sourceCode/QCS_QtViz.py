# -*- coding: utf-8 -*-
"""Qt Data Visualization tab for the v12.0 shell (phase 3).

Remote control over the REAL DatabaseView workflow: the hidden tk Step 1/2
(built once by the shell's bootstrap) remains the AUTHORITATIVE state - every
Qt change is pushed to its tk counterpart, the tk toggle logic runs, and the
Qt widgets are refreshed from the tk states. No visualization logic is
duplicated here; Preview/Next/Generate call the same functions the tk app
uses, with the dialogs routed to Qt through the QCS_DatabaseView facade.
"""
from PySide6.QtCore import QSignalBlocker, Qt
from PySide6.QtWidgets import (QCheckBox, QComboBox, QFileDialog, QFormLayout,
                               QGridLayout, QGroupBox, QHBoxLayout, QLabel,
                               QLineEdit, QPushButton, QScrollArea,
                               QSizePolicy, QStackedWidget, QVBoxLayout,
                               QWidget)

import pandas as pd

import QCS_DatabaseView as dbv
import QCS_QtTheme as qtheme

TOOLTIPS = dbv.TOOLTIPS


def _tk_enabled(widget):
    try:
        return not widget.instate(['disabled'])
    except Exception:
        return True


def _coverage_text():
    """The period the loaded database covers (the tk step 2 showed this under
    the X-axis fields; kept permanently on screen in Qt)."""
    db = dbv.database
    if db is None or 'Datetime' not in db.columns:
        return 'Data available: unknown'
    start, end = db['Datetime'].min(), db['Datetime'].max()
    if pd.isna(start) or pd.isna(end):
        return 'Data available: unknown (invalid dates)'
    return 'Data available: %s to %s' % (start.strftime('%d/%m/%Y %H:%M'),
                                         end.strftime('%d/%m/%Y %H:%M'))


def _depth_text():
    db = dbv.database
    if db is None or 'Depth (m)' not in db.columns or not db['Depth (m)'].notna().any():
        return 'Depth available: no depth column'
    return 'Depth available: %.2f to %.2f m' % (db['Depth (m)'].min(),
                                                db['Depth (m)'].max())


def _tk_set_entry(entry, text):
    state = str(entry.cget('state'))
    entry.config(state='normal')
    entry.delete(0, 'end')
    entry.insert(0, text)
    entry.config(state=state)


class VisualizationTab(QWidget):
    def __init__(self, shell):
        super().__init__()
        self.shell = shell
        # the folder-scan mode has no Qt surface (v12.0: several dropped
        # files already build a unified database) - pin file mode
        dbv.join.set(False)
        dbv.toggle_input_mode()
        v = QVBoxLayout(self)
        self.stack = QStackedWidget()
        self.stack.addWidget(self._build_step1())
        self._step2_page = QWidget()          # replaced on every Next
        self.stack.addWidget(self._step2_page)
        v.addWidget(self.stack)
        self.refresh_step1()

    # ---------- Step 1 ----------
    def _build_step1(self):
        # two columns, Input and Output settings, mirroring the Qualification
        # tab's structure (owner request, 2026-08-17)
        page = QWidget()
        grid = QGridLayout(page)

        gin = QGroupBox('Input settings')
        fin = QFormLayout(gin)
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        self.files = QLineEdit()
        self.files.setPlaceholderText(
            'Select or drop qualified file(s) here - several files build a '
            'unified database...')
        self.files.setToolTip(TOOLTIPS['database_files'])
        self.files.textEdited.connect(self._files_edited)
        b = QPushButton('Browse...')
        b.setToolTip(TOOLTIPS['database_files'])
        b.clicked.connect(self._browse_files)
        row.addWidget(self.files)
        row.addWidget(b)
        h = QWidget()
        h.setLayout(row)
        fin.addRow('Database file(s):', h)

        # Recent right under the files row; usable only while NO files are
        # selected (owner, 2026-08-17 - either pick files or reopen a recent
        # selection, never both at once)
        self.recent = QComboBox()
        self.recent.setPlaceholderText('Select a recent file to open')
        self.recent.setToolTip('Reopens one of the most recent file selections\n'
                               '(available while no file is selected above)')
        self.recent.activated.connect(self._apply_recent)
        fin.addRow('Recent:', self.recent)

        self.instrument = QComboBox()
        self.instrument.addItems(['Seaguard', 'HOBO', 'Doppler'])
        self.instrument.setToolTip(TOOLTIPS['instrument'])
        self.instrument.currentTextChanged.connect(
            lambda t: dbv.instrument_combobox.set(t))
        fin.addRow('Instrument:', self.instrument)

        self.sort = QCheckBox('Sort data chronologically')
        self.sort.setToolTip(TOOLTIPS['sort_time'])
        self.sort.toggled.connect(lambda on: dbv.sort.set(bool(on)))
        fin.addRow(self.sort)

        gout = QGroupBox('Output settings')
        fout = QFormLayout(gout)
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        self.out_path = QLineEdit()
        self.out_path.setPlaceholderText(
            'Select where the unified database will be saved...')
        self.out_path.setToolTip(TOOLTIPS['output_path'])
        self.out_path.textEdited.connect(
            lambda t: _tk_set_entry(dbv.outputPath_entry, t))
        bo = QPushButton('Browse...')
        bo.setToolTip(TOOLTIPS['output_path'])
        bo.clicked.connect(self._browse_output_folder)
        row.addWidget(self.out_path)
        row.addWidget(bo)
        h = QWidget()
        h.setLayout(row)
        fout.addRow('Output folder:', h)
        self.out_name = QLineEdit()
        self.out_name.setToolTip(TOOLTIPS['output_name'])
        self.out_name.textEdited.connect(
            lambda t: _tk_set_entry(dbv.outputName_entry, t))
        fout.addRow('Output name:', self.out_name)

        actions = QHBoxLayout()
        actions.addStretch()
        nxt = QPushButton('Next >')
        nxt.setDefault(True)
        nxt.setMinimumSize(120, 34)
        nf = nxt.font()
        nf.setBold(True)
        nxt.setFont(nf)
        nxt.setObjectName('AccentButton')   # blue primary action
        nxt.clicked.connect(self._next)
        actions.addWidget(nxt)
        ah = QWidget()
        ah.setLayout(actions)

        grid.addWidget(gin, 0, 0)
        grid.addWidget(gout, 0, 1)
        grid.addWidget(ah, 1, 0, 1, 2)
        grid.setRowStretch(0, 1)
        qtheme.bold_form_labels(fin)
        qtheme.bold_form_labels(fout)
        return page

    def refresh_step1(self):
        pairs = ((self.files, dbv.fileNames_entry),
                 (self.out_name, dbv.outputName_entry),
                 (self.out_path, dbv.outputPath_entry))
        for qt, tk in pairs:
            with QSignalBlocker(qt):
                qt.setText(tk.get())
                qt.setEnabled(_tk_enabled(tk))
        # the name is only used when several files build a NEW database;
        # the placeholder says which situation the field is in
        self.out_name.setPlaceholderText(
            'Name the new unified database...' if self.out_name.isEnabled()
            else 'Not needed for a single file')
        with QSignalBlocker(self.sort):
            self.sort.setChecked(bool(dbv.sort.get()))
        with QSignalBlocker(self.instrument):
            self.instrument.setCurrentText(dbv.instrument_combobox.get())
        with QSignalBlocker(self.recent):
            self.recent.clear()
            self.recent.addItems([dbv._recent_display(r)
                                  for r in dbv.USER_PREFS.get('dbv_recent', [])])
            self.recent.setCurrentIndex(-1)
        self.recent.setEnabled(not self.files.text().strip())

    def _files_edited(self, text):
        _tk_set_entry(dbv.fileNames_entry, text)
        self.recent.setEnabled(not text.strip())

    def _apply_recent(self, index):
        recents = dbv.USER_PREFS.get('dbv_recent', [])
        if 0 <= index < len(recents):
            files = [p for p in recents[index]['files'].split(';') if p.strip()]
            if files:
                self.apply_selected_files(files)

    def _browse_files(self):
        names, _f = QFileDialog.getOpenFileNames(
            self, 'Select database or qualified file(s)',
            dbv.USER_PREFS.get('dbv_last_db_dir', ''),
            'Database files (*.xlsx *.csv);;All files (*.*)')
        if names:
            self.apply_selected_files(names)

    def apply_selected_files(self, names):
        dbv.apply_selected_files(names)   # fills tk fields + autodetects
        self.refresh_step1()

    def _browse_output_folder(self):
        path = QFileDialog.getExistingDirectory(
            self, 'Select output folder', self.out_path.text())
        if path:
            _tk_set_entry(dbv.outputPath_entry, path)
            self.refresh_step1()

    def _next(self):
        if dbv._go_step2():
            self._rebuild_step2()
            self.stack.setCurrentIndex(1)

    # ---------- Step 2 ----------
    def _rebuild_step2(self):
        old = self._step2_page
        self._step2_page = self._build_step2()
        self.stack.removeWidget(old)
        old.deleteLater()
        self.stack.addWidget(self._step2_page)
        self.refresh_step2()

    def _all_none_row(self, boxes):
        """Compact 'All | None' pair for a filter group (owner request). The
        boxes are fetched lazily: the group is still being built here."""
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        for text, state in (('All', True), ('None', False)):
            btn = QPushButton(text)        # framed, like '< Back' (owner)
            btn.setMaximumWidth(64)
            btn.clicked.connect(
                lambda _c=False, s=state, get=boxes: [cb.setChecked(s) for cb in get()])
            row.addWidget(btn)
        row.addStretch()
        return row

    def _entry_pair(self, qt, tk):
        qt.textEdited.connect(lambda t, tk=tk: _tk_set_entry(tk, t))
        self._entries.append((qt, tk))

    def _check_pair(self, qt, var, widget, after=()):
        def push(on, var=var, after=after):
            var.set(bool(on))
            for fn in after:
                fn()
            self.refresh_step2()
        qt.toggled.connect(push)
        self._checks.append((qt, var, widget))

    def _build_step2(self):
        self._entries = []   # (QLineEdit, tk entry)
        self._checks = []    # (QCheckBox, tk BooleanVar, tk widget or None)
        page = QWidget()
        outer = QVBoxLayout(page)
        # same margins as the Qualification tab's grid, so the primary button
        # sits at the same distance from the boxes above it
        outer.setContentsMargins(9, 9, 9, 9)
        grid = QGridLayout()

        gdata = QGroupBox('Data settings')
        fd = QFormLayout(gdata)
        src = QLabel(dbv._current_source_label())
        src.setWordWrap(True)
        qtheme.muted(src)
        fd.addRow('Source:', src)
        # the data type is decided by what was imported in Step 1 - it is a
        # fact of the database, not a choice (owner, 2026-08-17)
        self.dtype_label = QLabel(dbv.dType_combobox.get() or '-')
        self.dtype_label.setToolTip(TOOLTIPS['data_type'])
        qtheme.muted(self.dtype_label)
        fd.addRow('Data type:', self.dtype_label)
        grid.addWidget(gdata, 0, 0, 1, 3, Qt.AlignTop)

        gvis = QGroupBox('Visualization settings')
        fv = QFormLayout(gvis)
        self._fv = fv
        self.panel_checks = []
        panel_tips = ((TOOLTIPS['hobo_params_site'], TOOLTIPS['hobo_params_across'], '')
                      if dbv.is_hobo_input() else
                      (TOOLTIPS['panel1'], TOOLTIPS['panel2'], TOOLTIPS['panel3']))
        for i, (pvar, pcb) in enumerate(((dbv.panel1, dbv.panel1_cb),
                                         (dbv.panel2, dbv.panel2_cb),
                                         (dbv.panel3, dbv.panel3_cb))):
            if not pcb.winfo_ismapped() and str(pcb.grid_info()) == '{}':
                continue     # HOBO hides its unused third panel entirely
            cb = QCheckBox(pcb.cget('text'))
            if panel_tips[i]:
                cb.setToolTip(panel_tips[i])
            self._check_pair(cb, pvar, pcb,
                             after=(dbv.toggle_panel_dependent_controls,
                                    dbv.toggle_parameter_checkboxes))
            fv.addRow(cb)
            self.panel_checks.append(cb)
        self.ts_check = QCheckBox('T-S Diagram')
        self.ts_check.setToolTip(TOOLTIPS['ts_diagram'])
        self._check_pair(self.ts_check, dbv.tsDiagram, dbv.ts_cb,
                         after=(dbv.toggle_ts_controls,))
        fv.addRow(self.ts_check)
        self.latitude = QLineEdit()
        self.latitude.setToolTip(TOOLTIPS['latitude'])
        self._entry_pair(self.latitude, dbv.latitude_entry)
        fv.addRow('Latitude:', self.latitude)
        self.longitude = QLineEdit()
        self.longitude.setToolTip(TOOLTIPS['longitude'])
        self._entry_pair(self.longitude, dbv.longitude_entry)
        fv.addRow('Longitude:', self.longitude)
        self.ts_param = QComboBox()
        self.ts_param.addItems(list(dbv.tsParam_combobox.cget('values')))
        self.ts_param.setToolTip(TOOLTIPS['ts_params'])
        self.ts_param.currentTextChanged.connect(
            lambda t: dbv.tsParam_combobox.set(t))
        fv.addRow('T-S variables:', self.ts_param)
        # the T-S diagram needs T, S and depth together: profiles only.
        # These rows only EXIST while Data type is TSCP Profile
        # (visibility handled in refresh_step2)
        self._ts_rows = [self.ts_check, self.latitude, self.longitude,
                         self.ts_param]
        self.tendency = QCheckBox('Tendency lines')
        self.tendency.setToolTip(TOOLTIPS['tendency'])
        self._check_pair(self.tendency, dbv.tendency, dbv.tendency_cb,
                         after=(dbv.toggle_panel_dependent_controls,))
        fv.addRow(self.tendency)
        self.degree = QLineEdit()
        self.degree.setFixedWidth(60)
        self.degree.setToolTip(TOOLTIPS['tendency_degree'])
        self._entry_pair(self.degree, dbv.tendency_entry)
        fv.addRow('Regression degree:', self.degree)
        self.points = QCheckBox('Show data points')
        self.points.setToolTip(TOOLTIPS['data_points'])
        self._check_pair(self.points, dbv.dataPoints, dbv.points_cb)
        fv.addRow(self.points)
        self.fixed_scale = QCheckBox('Fixed scale')
        self.fixed_scale.setToolTip(TOOLTIPS['fixed_scale'])
        self._check_pair(self.fixed_scale, dbv.fixedScale, dbv.fixed_scale_cb,
                         after=(dbv.toggle_scale_controls,))
        fv.addRow(self.fixed_scale)
        self.time_start = QLineEdit()
        self.time_start.setToolTip(TOOLTIPS['time_start'])
        self._entry_pair(self.time_start, dbv.time_start_entry)
        fv.addRow('Time window start:', self.time_start)
        self.time_end = QLineEdit()
        self.time_end.setToolTip(TOOLTIPS['time_end'])
        self._entry_pair(self.time_end, dbv.time_end_entry)
        fv.addRow('Time window end:', self.time_end)
        # what the database actually covers, permanently on screen: editing
        # the window must not cost the operator the reference (owner request;
        # the tk step 2 had these two lines)
        self.data_available = QLabel(_coverage_text())
        qtheme.muted(self.data_available)
        fv.addRow('', self.data_available)
        self.depth_min = QLineEdit()
        self.depth_min.setToolTip(TOOLTIPS['depth_min'])
        self._entry_pair(self.depth_min, dbv.depth_min_entry)
        fv.addRow('Depth axis min (m):', self.depth_min)
        self.depth_max = QLineEdit()
        self.depth_max.setToolTip(TOOLTIPS['depth_max'])
        self._entry_pair(self.depth_max, dbv.depth_max_entry)
        fv.addRow('Depth axis max (m):', self.depth_max)
        self.depth_available = QLabel(_depth_text())
        qtheme.muted(self.depth_available)
        fv.addRow('', self.depth_available)
        self._depth_rows = [self.depth_min, self.depth_max, self.depth_available]
        grid.addWidget(gvis, 1, 0, Qt.AlignTop)

        gfil = QGroupBox('Filter settings')
        ff = QVBoxLayout(gfil)
        sites_lab = QLabel('Filter by site:')
        f = sites_lab.font()
        f.setBold(True)
        sites_lab.setFont(f)
        ff.addWidget(sites_lab)
        self.site_checks = {}
        for site in dbv.site_names:
            cb = QCheckBox(str(site))
            cb.setToolTip(TOOLTIPS['site_filter'])
            self._check_pair(cb, dbv.site_vars[site], dbv.site_widgets.get(site),
                             after=(dbv.toggle_scale_controls,))
            self.site_checks[site] = cb
            ff.addWidget(cb)
        ff.addLayout(self._all_none_row(lambda: self.site_checks.values()))
        # years live under Sites in Filter settings (owner, 2026-08-17; two
        # columns so many years stay compact)
        year_lab = QLabel('Filter by year:')
        year_lab.setFont(f)        # same bold section font as 'Sites:'
        ff.addWidget(year_lab)
        ygrid = QGridLayout()
        ygrid.setContentsMargins(0, 0, 0, 0)   # level with the Sites/Parameters checks
        self.year_checks = {}
        for i, y in enumerate(sorted(dbv.year_vars)):
            cb = QCheckBox(str(y))
            cb.setToolTip(TOOLTIPS['filter_year'])
            self._check_pair(cb, dbv.year_vars[y], dbv.year_widgets.get(y),
                             after=(dbv.toggle_scale_controls,))
            self.year_checks[y] = cb
            ygrid.addWidget(cb, i // 2, i % 2)
        yh = QWidget()
        yh.setLayout(ygrid)
        ff.addWidget(yh)
        ff.addLayout(self._all_none_row(lambda: self.year_checks.values()))
        params_lab = QLabel('Filter by parameter:')
        params_lab.setFont(f)      # same bold section font as 'Sites:'
        ff.addWidget(params_lab)
        self.param_checks = {}
        for param in dbv.parameter_names:
            cb = QCheckBox(str(param))
            cb.setToolTip(TOOLTIPS['param_filter'])
            self._check_pair(cb, dbv.parameter_vars[param],
                             dbv.parameter_widgets.get(param),
                             after=(dbv.toggle_scale_controls,))
            self.param_checks[param] = cb
            ff.addWidget(cb)
        ff.addLayout(self._all_none_row(lambda: self.param_checks.values()))
        ff.addStretch()
        grid.addWidget(gfil, 1, 1, Qt.AlignTop)

        gscale = QGroupBox('Scale settings')
        gs = QGridLayout(gscale)
        gs.addWidget(QLabel('Parameter'), 0, 0)   # plain, not bold (owner)
        gs.addWidget(QLabel('Min'), 0, 1)
        gs.addWidget(QLabel('Max'), 0, 2)
        self.scale_edits = {}
        for r, param in enumerate(dbv.parameter_names, start=1):
            plab = QLabel(str(param))
            plab.setFont(f)        # bold, like the other section labels
            gs.addWidget(plab, r, 0)
            mn = QLineEdit()
            mn.setMinimumWidth(80)
            mn.setToolTip(TOOLTIPS['min_scale'])
            self._entry_pair(mn, dbv.min_scale_entries[param])
            mx = QLineEdit()
            mx.setMinimumWidth(80)
            mx.setToolTip(TOOLTIPS['max_scale'])
            self._entry_pair(mx, dbv.max_scale_entries[param])
            gs.addWidget(mn, r, 1)
            gs.addWidget(mx, r, 2)
            self.scale_edits[param] = (mn, mx)
        # the name column keeps its width; only the value boxes stretch when
        # the window grows (their text stays left-justified)
        gs.setColumnStretch(0, 0)
        gs.setColumnStretch(1, 1)
        gs.setColumnStretch(2, 1)
        gs.setRowStretch(len(dbv.parameter_names) + 1, 1)
        grid.addWidget(gscale, 1, 2, Qt.AlignTop)
        # the settings column takes the slack; the filter and scale columns
        # keep their natural width, so their checkboxes stop drifting apart
        # when the window is resized (owner)
        grid.setColumnStretch(0, 3)
        grid.setColumnStretch(1, 0)
        grid.setColumnStretch(2, 2)
        grid.setRowStretch(0, 0)     # the Data settings band keeps its height
        grid.setRowStretch(1, 1)
        for box in (gdata, gvis, gfil, gscale):
            box.setSizePolicy(box.sizePolicy().horizontalPolicy(),
                              QSizePolicy.Policy.Preferred)

        qtheme.bold_form_labels(fd)
        qtheme.bold_form_labels(fv)
        inner = QWidget()
        inner.setLayout(grid)
        grid.setContentsMargins(0, 0, 0, 0)
        area = QScrollArea()
        area.setWidgetResizable(True)
        # no frame: the scroll area's border drew a box around the whole page
        # (which also pushed 'Generate panels' further down than 'Run
        # qualification' sits on the other tab) - owner
        area.setFrameShape(QScrollArea.Shape.NoFrame)
        area.setWidget(inner)
        outer.addWidget(area)

        # Back on the left, Generate truly CENTERED and styled like the
        # Run qualification button (owner, 2026-08-17)
        actions = QGridLayout()
        for col in range(3):
            actions.setColumnStretch(col, 1)
        back = QPushButton('< Back')
        back.clicked.connect(self._back)
        actions.addWidget(back, 0, 0, Qt.AlignLeft | Qt.AlignVCenter)
        gen = QPushButton('Generate panels')
        gen.setDefault(True)
        gen.setMinimumSize(260, 42)
        gf = gen.font()
        gf.setBold(True)
        gf.setPointSizeF(gf.pointSizeF() + 1)
        gen.setFont(gf)
        gen.setObjectName('AccentButton')   # blue primary action
        gen.setToolTip('Generates the selected panels with the current settings')
        gen.clicked.connect(self._generate)
        actions.addWidget(gen, 0, 1, Qt.AlignHCenter)
        outer.addLayout(actions)
        return page

    def refresh_step2(self):
        # T-S rows exist only for profile data (owner: the diagram makes no
        # sense for HOBO, Doppler or moorings); hiding also unchecks it
        is_profile = dbv.dType_combobox.get() == 'TSCP Profile'
        if not is_profile and dbv.tsDiagram.get():
            dbv.tsDiagram.set(False)
            dbv.toggle_ts_controls()
        for w in self._ts_rows:
            self._fv.setRowVisible(w, is_profile)
        # HOBO has no depth at all: the whole depth block goes away
        for w in self._depth_rows:
            self._fv.setRowVisible(w, not dbv.is_hobo_input())
        self.dtype_label.setText(dbv.dType_combobox.get() or '-')
        for qt, tk in self._entries:
            with QSignalBlocker(qt):
                qt.setText(tk.get())
                qt.setEnabled(_tk_enabled(tk))
        for qt, var, widget in self._checks:
            with QSignalBlocker(qt):
                qt.setChecked(bool(var.get()))
                if widget is not None:
                    qt.setEnabled(_tk_enabled(widget))
        with QSignalBlocker(self.ts_param):
            self.ts_param.setCurrentText(dbv.tsParam_combobox.get())
            self.ts_param.setEnabled(_tk_enabled(dbv.tsParam_combobox))

    def _generate(self):
        dbv.generatePanels()
        self.refresh_step2()   # a run may adjust settings (e.g. skipped T-S)

    def _back(self):
        dbv._go_step1()
        self.stack.setCurrentIndex(0)
        self.refresh_step1()

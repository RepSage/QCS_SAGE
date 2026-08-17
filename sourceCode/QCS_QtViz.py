# -*- coding: utf-8 -*-
"""Qt Data Visualization tab for the v12.0 shell (phase 3).

Remote control over the REAL DatabaseView workflow: the hidden tk Step 1/2
(built once by the shell's bootstrap) remains the AUTHORITATIVE state - every
Qt change is pushed to its tk counterpart, the tk toggle logic runs, and the
Qt widgets are refreshed from the tk states. No visualization logic is
duplicated here; Preview/Next/Generate call the same functions the tk app
uses, with the dialogs routed to Qt through the QCS_DatabaseView facade.
"""
from PySide6.QtCore import QSignalBlocker
from PySide6.QtWidgets import (QCheckBox, QComboBox, QFileDialog, QFormLayout,
                               QGridLayout, QGroupBox, QHBoxLayout, QLabel,
                               QLineEdit, QPushButton, QScrollArea,
                               QStackedWidget, QVBoxLayout, QWidget)

import QCS_DatabaseView as dbv
import QCS_QtTheme as qtheme

TOOLTIPS = dbv.TOOLTIPS


def _tk_enabled(widget):
    try:
        return not widget.instate(['disabled'])
    except Exception:
        return True


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
        self.files.setToolTip(TOOLTIPS['database_files'])
        self.files.textEdited.connect(
            lambda t: _tk_set_entry(dbv.fileNames_entry, t))
        b = QPushButton('Browse...')
        b.setToolTip(TOOLTIPS['database_files'])
        b.clicked.connect(self._browse_files)
        row.addWidget(self.files)
        row.addWidget(b)
        h = QWidget()
        h.setLayout(row)
        fin.addRow('Database file(s):', h)

        self.join = QCheckBox('Build database from a folder')
        self.join.setToolTip(TOOLTIPS['join_files'])
        self.join.toggled.connect(self._join_toggled)
        fin.addRow(self.join)

        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        self.input_path = QLineEdit()
        self.input_path.setToolTip(TOOLTIPS['input_path'])
        self.input_path.textEdited.connect(
            lambda t: _tk_set_entry(dbv.inputPath_entry, t))
        bi = QPushButton('Browse...')
        bi.setToolTip(TOOLTIPS['input_path'])
        bi.clicked.connect(self._browse_input_folder)
        row.addWidget(self.input_path)
        row.addWidget(bi)
        self._input_browse = bi
        h = QWidget()
        h.setLayout(row)
        fin.addRow('Input folder:', h)

        self.sort = QCheckBox('Sort data chronologically')
        self.sort.setToolTip(TOOLTIPS['sort_time'])
        self.sort.toggled.connect(lambda on: dbv.sort.set(bool(on)))
        fin.addRow(self.sort)

        self.instrument = QComboBox()
        self.instrument.addItems(['Seaguard', 'HOBO', 'Doppler'])
        self.instrument.setToolTip(TOOLTIPS['instrument'])
        self.instrument.currentTextChanged.connect(
            lambda t: dbv.instrument_combobox.set(t))
        fin.addRow('Instrument:', self.instrument)

        gout = QGroupBox('Output settings')
        fout = QFormLayout(gout)
        self.out_name = QLineEdit()
        self.out_name.setToolTip(TOOLTIPS['output_name'])
        self.out_name.textEdited.connect(
            lambda t: _tk_set_entry(dbv.outputName_entry, t))
        fout.addRow('Output name:', self.out_name)

        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        self.out_path = QLineEdit()
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

        gprev = QGroupBox('Database preview')
        pv = QHBoxLayout(gprev)
        self.preview_btn = QPushButton('Preview')
        self.preview_btn.setToolTip(
            "Builds the database now and shows a summary below\n"
            "(sites, period, rows); 'Next >' reuses this build")
        self.preview_btn.clicked.connect(self._preview)
        self.preview_label = QLabel('')
        self.preview_label.setWordWrap(True)
        pv.addWidget(self.preview_btn)
        pv.addWidget(self.preview_label, stretch=1)

        actions = QHBoxLayout()
        actions.addStretch()
        nxt = QPushButton('Next >')
        nxt.setDefault(True)
        nxt.setMinimumSize(120, 34)
        nxt.clicked.connect(self._next)
        actions.addWidget(nxt)
        ah = QWidget()
        ah.setLayout(actions)

        grid.addWidget(gin, 0, 0)
        grid.addWidget(gout, 0, 1)
        grid.addWidget(gprev, 1, 0, 1, 2)
        grid.addWidget(ah, 2, 0, 1, 2)
        grid.setRowStretch(0, 1)
        qtheme.bold_form_labels(fin)
        qtheme.bold_form_labels(fout)
        return page

    def refresh_step1(self):
        pairs = ((self.files, dbv.fileNames_entry),
                 (self.input_path, dbv.inputPath_entry),
                 (self.out_name, dbv.outputName_entry),
                 (self.out_path, dbv.outputPath_entry))
        for qt, tk in pairs:
            with QSignalBlocker(qt):
                qt.setText(tk.get())
                qt.setEnabled(_tk_enabled(tk))
        with QSignalBlocker(self.join):
            self.join.setChecked(bool(dbv.join.get()))
        with QSignalBlocker(self.sort):
            self.sort.setChecked(bool(dbv.sort.get()))
        with QSignalBlocker(self.instrument):
            self.instrument.setCurrentText(dbv.instrument_combobox.get())
        self.preview_btn.setEnabled(_tk_enabled(dbv.preview_btn))
        self.preview_label.setText(dbv._preview_var.get())

    def _join_toggled(self, on):
        dbv.join.set(bool(on))
        dbv.toggle_input_mode()
        self.refresh_step1()

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

    def _browse_input_folder(self):
        path = QFileDialog.getExistingDirectory(
            self, 'Select the folder to scan', self.input_path.text())
        if path:
            _tk_set_entry(dbv.inputPath_entry, path)
            self.refresh_step1()

    def _browse_output_folder(self):
        path = QFileDialog.getExistingDirectory(
            self, 'Select output folder', self.out_path.text())
        if path:
            _tk_set_entry(dbv.outputPath_entry, path)
            self.refresh_step1()

    def _preview(self):
        dbv.preview_database()
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
        grid = QGridLayout()

        gdata = QGroupBox('Data settings')
        fd = QFormLayout(gdata)
        src = QLabel(dbv._current_source_label())
        src.setWordWrap(True)
        src.setStyleSheet('color: palette(mid);')
        fd.addRow('Source:', src)
        self.dtype = QComboBox()
        self.dtype.addItems(list(dbv.dType_combobox.cget('values')))
        self.dtype.setToolTip(TOOLTIPS['data_type'])

        def push_dtype(text):
            dbv.dType_combobox.set(text)
            dbv.dType_combobox.event_generate('<<ComboboxSelected>>')
            self.refresh_step2()
        self.dtype.currentTextChanged.connect(push_dtype)
        fd.addRow('Data type:', self.dtype)
        years = QHBoxLayout()
        self.year_checks = {}
        for y in sorted(dbv.year_vars):
            cb = QCheckBox(str(y))
            cb.setToolTip(TOOLTIPS['filter_year'])
            self._check_pair(cb, dbv.year_vars[y], dbv.year_widgets.get(y),
                             after=(dbv.toggle_scale_controls,))
            self.year_checks[y] = cb
            years.addWidget(cb)
        years.addStretch()
        yh = QWidget()
        yh.setLayout(years)
        fd.addRow('Filter by year:', yh)
        grid.addWidget(gdata, 0, 0, 1, 2)

        gvis = QGroupBox('Visualization settings')
        fv = QFormLayout(gvis)
        self.panel_checks = []
        for pvar, pcb in ((dbv.panel1, dbv.panel1_cb),
                          (dbv.panel2, dbv.panel2_cb),
                          (dbv.panel3, dbv.panel3_cb)):
            if not pcb.winfo_ismapped() and str(pcb.grid_info()) == '{}':
                continue     # HOBO hides its unused third panel entirely
            cb = QCheckBox(pcb.cget('text'))
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
        self.depth_min = QLineEdit()
        self.depth_min.setToolTip(TOOLTIPS['depth_min'])
        self._entry_pair(self.depth_min, dbv.depth_min_entry)
        fv.addRow('Depth axis min (m):', self.depth_min)
        self.depth_max = QLineEdit()
        self.depth_max.setToolTip(TOOLTIPS['depth_max'])
        self._entry_pair(self.depth_max, dbv.depth_max_entry)
        fv.addRow('Depth axis max (m):', self.depth_max)
        grid.addWidget(gvis, 1, 0)

        gfil = QGroupBox('Filter settings')
        ff = QVBoxLayout(gfil)
        sites_lab = QLabel('Sites:')
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
        params_lab = QLabel('Parameters:')
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
        ff.addStretch()
        grid.addWidget(gfil, 1, 1)

        gscale = QGroupBox('Scale settings')
        gs = QGridLayout(gscale)
        gs.addWidget(QLabel('Min'), 0, 1)
        gs.addWidget(QLabel('Max'), 0, 2)
        self.scale_edits = {}
        for r, param in enumerate(dbv.parameter_names, start=1):
            gs.addWidget(QLabel(str(param)), r, 0)
            mn = QLineEdit()
            mn.setFixedWidth(80)
            mn.setToolTip(TOOLTIPS['min_scale'])
            self._entry_pair(mn, dbv.min_scale_entries[param])
            mx = QLineEdit()
            mx.setFixedWidth(80)
            mx.setToolTip(TOOLTIPS['max_scale'])
            self._entry_pair(mx, dbv.max_scale_entries[param])
            gs.addWidget(mn, r, 1)
            gs.addWidget(mx, r, 2)
            self.scale_edits[param] = (mn, mx)
        gs.setRowStretch(len(dbv.parameter_names) + 1, 1)
        grid.addWidget(gscale, 1, 2)

        qtheme.bold_form_labels(fd)
        qtheme.bold_form_labels(fv)
        inner = QWidget()
        inner.setLayout(grid)
        area = QScrollArea()
        area.setWidgetResizable(True)
        area.setWidget(inner)
        outer.addWidget(area)

        actions = QHBoxLayout()
        back = QPushButton('< Back')
        back.clicked.connect(self._back)
        gen = QPushButton('Generate panels')
        gen.setDefault(True)
        gen.setMinimumSize(200, 38)
        gen.clicked.connect(self._generate)
        actions.addWidget(back)
        actions.addStretch()
        actions.addWidget(gen)
        actions.addStretch()
        outer.addLayout(actions)
        return page

    def refresh_step2(self):
        for qt, tk in self._entries:
            with QSignalBlocker(qt):
                qt.setText(tk.get())
                qt.setEnabled(_tk_enabled(tk))
        for qt, var, widget in self._checks:
            with QSignalBlocker(qt):
                qt.setChecked(bool(var.get()))
                if widget is not None:
                    qt.setEnabled(_tk_enabled(widget))
        with QSignalBlocker(self.dtype):
            self.dtype.setCurrentText(dbv.dType_combobox.get())
            self.dtype.setEnabled(_tk_enabled(dbv.dType_combobox))
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

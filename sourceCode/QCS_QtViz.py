# -*- coding: utf-8 -*-
"""Qt Data Visualization tab for the v12.0 shell (phase 3).

Remote control over the REAL DatabaseView workflow: the hidden tk Step 1/2
(built once by the shell's bootstrap) remains the AUTHORITATIVE state - every
Qt change is pushed to its tk counterpart, the tk toggle logic runs, and the
Qt widgets are refreshed from the tk states. No visualization logic is
duplicated here; Preview/Next/Generate call the same functions the tk app
uses, with the dialogs routed to Qt through the QCS_DatabaseView facade.
"""
import os

from PySide6.QtCore import QPoint, QSignalBlocker, Qt, QTimer
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (QAbstractSpinBox, QCheckBox, QColorDialog,
                               QComboBox,
                               QDialogButtonBox, QFileDialog,
                               QFormLayout,
                               QGridLayout, QGroupBox, QHBoxLayout, QLabel,
                               QLineEdit, QPushButton,
                               QSizePolicy, QSpinBox, QStackedWidget,
                               QVBoxLayout, QWidget)

import pandas as pd

import QCS_DatabaseView as dbv
import QCS_QtTheme as qtheme

# Placeholder of the 'Recent' box, usable only while no file is selected. Same
# two wordings as the Qualification tab (QCS_QtApp.RECENT_HINTS), with this
# tab's own name for what has to be cleared.
RECENT_HINTS = {
    True: 'Select a recent file to open',
    False: 'Clear the database file(s) to select a recent file',
}

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


def _line_up_picker(dialog, box, first, second):
    """Qt's color picker knows nothing about the two buttons added to it, so
    the tidying is done by hand once its layout is built (owner, 2026-08-18):

    - the reset pair spans exactly the 'Add to Custom Colors' button above it;
    - the HTML field reaches the right edge of the Blue/Green/Red column.

    Every number is MEASURED. Qt's metrics move with theme, font and DPI, and
    the picker's own button texts are translated, so the anchor is found by
    geometry (the two full-width buttons are the only ones parented to the
    dialog itself) and never by its label.
    """
    dialog.layout().activate()
    anchor = max((b for b in dialog.findChildren(QPushButton)
                  if b.parent() is dialog), key=lambda b: b.y())
    spacing = box.layout().spacing()
    width = (anchor.width() - spacing) // 2
    first.setFixedWidth(width)
    second.setFixedWidth(anchor.width() - spacing - width)

    # the spin boxes of a hidden channel (alpha) do not count for the edge
    spins = [sp for sp in dialog.findChildren(QSpinBox) if not sp.isHidden()]
    html = [e for e in dialog.findChildren(QLineEdit)
            if not isinstance(e.parent(), QAbstractSpinBox)][0]
    right = max(sp.mapTo(dialog, QPoint(0, 0)).x() + sp.width() for sp in spins)
    html.setFixedWidth(right - html.mapTo(dialog, QPoint(0, 0)).x())
    box.layout().activate()
    dialog.layout().activate()


class VisualizationTab(QWidget):
    def __init__(self, shell):
        super().__init__()
        self.shell = shell
        # the folder-scan mode has no Qt surface (v12.0: several dropped
        # files already build a unified database) - pin file mode
        dbv.join.set(False)
        dbv.toggle_input_mode()
        v = QVBoxLayout(self)
        # no margin of its own: each page sets the same 9 px the Qualification
        # tab uses, and stacking the two pushed this tab's boxes 18 px from the
        # window edge (owner, 2026-08-18)
        v.setContentsMargins(0, 0, 0, 0)
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
        self.recent.setPlaceholderText(RECENT_HINTS[True])
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
        # the boxes take the height of their CONTENT and 'Next >' sits right
        # under them: the stretch used to be on the boxes' own row, which blew
        # them up to the full page and pushed the button to the bottom edge
        # (owner, 2026-08-19)
        grid.setRowStretch(2, 1)
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
            # only meaningful when several files build a database
            self.sort.setEnabled(_tk_enabled(dbv.sort_cb))
        with QSignalBlocker(self.instrument):
            self.instrument.setCurrentText(dbv.instrument_combobox.get())
        with QSignalBlocker(self.recent):
            self.recent.clear()
            self.recent.addItems([dbv._recent_display(r)
                                  for r in dbv.USER_PREFS.get('dbv_recent', [])])
            self.recent.setCurrentIndex(-1)
        self._sync_recent_state()

    def apply_prefill(self, info):
        """A qualification just finished: Step 1 shows ITS file, and the tab
        goes back to Step 1 - landing on the Step 2 of an older database was
        the v12.0 bug (owner, v12.1)."""
        dbv.apply_pending_prefill(info)
        self.stack.setCurrentIndex(0)
        self.refresh_step1()
        qtheme.scroll_to_top(self)

    def _shown_params(self):
        """The parameters this database actually carries data for.

        A column that is present but EMPTY - CO2 when no CO2 logger file was
        merged, an optical group the cast did not have - used to take a row in
        the filter and another in Scale settings, offering a variable that
        cannot be plotted (owner, 2026-08-19). QCS_DatabaseView computes the
        list while it builds step 2; if it somehow has none, show them all
        rather than an empty panel."""
        with_data = list(getattr(dbv, 'params_with_data', []) or [])
        return ([p for p in dbv.parameter_names if p in with_data]
                or list(dbv.parameter_names))

    def _sync_recent_state(self):
        """Recent is usable only while nothing is selected above - and while it
        is greyed out it says what makes it usable again, the same wording the
        Qualification tab uses (owner, 2026-08-19)."""
        usable = not self.files.text().strip()
        self.recent.setEnabled(usable)
        self.recent.setPlaceholderText(RECENT_HINTS[usable])

    def _files_edited(self, text):
        _tk_set_entry(dbv.fileNames_entry, text)
        self._sync_recent_state()

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
        # same start folder and same save point as the tk selectOutputFolder:
        # the picker opens where the last one did instead of scanning the
        # drive root, and the choice survives the session (v12.2)
        start = (self.out_path.text().strip()
                 or dbv.USER_PREFS.get('dbv_last_output_dir')
                 or dbv.USER_PREFS.get('dbv_last_db_dir', ''))
        if not os.path.isdir(start):
            start = ''
        path = QFileDialog.getExistingDirectory(self, 'Select output folder', start)
        if path:
            _tk_set_entry(dbv.outputPath_entry, path)
            dbv.USER_PREFS['dbv_last_output_dir'] = path
            dbv.save_user_prefs()
            self.refresh_step1()

    def _next(self):
        if dbv._go_step2():
            self._rebuild_step2()
            self.stack.setCurrentIndex(1)
            qtheme.scroll_to_top(self)     # step 2 opens at its top

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
        # order asked by the owner (2026-08-18): what the axes do, then what
        # is drawn over the data, and the trend line with its degree last.
        # The T-S rows stay above, with the panel checkboxes: they choose a
        # FIGURE, not a way of drawing one.
        self.fixed_scale = QCheckBox('Fixed scale')
        self.fixed_scale.setToolTip(TOOLTIPS['fixed_scale'])
        self._check_pair(self.fixed_scale, dbv.fixedScale, dbv.fixed_scale_cb,
                         after=(dbv.toggle_scale_controls,))
        fv.addRow(self.fixed_scale)
        self.points = QCheckBox('Show data points')
        self.points.setToolTip(TOOLTIPS['data_points'])
        self._check_pair(self.points, dbv.dataPoints, dbv.points_cb)
        fv.addRow(self.points)
        # the replicate-disagreement bars only exist on a HOBO temperature
        # series, so the row is not even built for the other instruments
        self.disagreement = None
        if dbv.is_hobo_input():
            self.disagreement = QCheckBox('Show disagreement bars')
            self.disagreement.setToolTip(TOOLTIPS['disagreement_bars'])
            self._check_pair(self.disagreement, dbv.disagreement, None)
            fv.addRow(self.disagreement)
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
        # the rarely-used tail carries its own heading, as the tk Step 2 had:
        # these variables always start unchecked and the operator has to know
        # THAT is why they are off (owner, v12.1)
        shown = self._shown_params()
        rare = [p for p in getattr(dbv, 'secondary_params', []) or [] if p in shown]
        for param in shown:
            if rare and param == rare[0]:
                rare_lab = QLabel('Rarely used:')
                rare_lab.setFont(f)
                rare_lab.setToolTip(TOOLTIPS['param_secondary'])
                qtheme.muted(rare_lab)
                ff.addWidget(rare_lab)
            cb = QCheckBox(dbv.param_display(param))
            cb.setToolTip(TOOLTIPS['param_secondary'] if param in rare
                          else TOOLTIPS['param_filter'])
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
        for col, title in ((1, 'Parameter'), (2, 'Min'), (3, 'Max')):
            hdr = QLabel(title)
            hdr.setFont(f)         # bold headers, like the other sections
            gs.addWidget(hdr, 0, col)
        self.scale_edits = {}
        self.color_buttons = {}
        # the same 'Rarely used:' heading the parameter filter carries, so the
        # two columns break at the same place - the tk Step 2 headed both and
        # the port kept it only on the filter (owner, 2026-08-19)
        shown = self._shown_params()
        rare_scale = [p for p in getattr(dbv, 'secondary_params', []) or []
                      if p in shown]
        r = 0
        for param in shown:
            r += 1
            if rare_scale and param == rare_scale[0]:
                head = QLabel('Rarely used:')
                head.setFont(f)
                head.setToolTip(TOOLTIPS['param_secondary'])
                qtheme.muted(head)
                gs.addWidget(head, r, 0, 1, 4)
                r += 1
            # the plot color, clickable: opens the color wheel (which has a
            # hex field, so a house palette can be typed in) - v12.0
            swatch = QPushButton()
            swatch.setFixedSize(18, 18)
            swatch.setToolTip('Color of %s in the plots\nClick to change it '
                              '(the picker takes hex codes too)'
                              % dbv.param_display(param))
            swatch.setCursor(Qt.CursorShape.PointingHandCursor)   # it is clickable
            swatch.clicked.connect(lambda _c=False, p=param: self._pick_color(p))
            gs.addWidget(swatch, r, 0)
            self.color_buttons[param] = swatch
            plab = QLabel(dbv.param_display(param))   # plain, like the values
            gs.addWidget(plab, r, 1)
            mn = QLineEdit()
            mn.setMinimumWidth(80)
            mn.setToolTip(TOOLTIPS['min_scale'])
            self._entry_pair(mn, dbv.min_scale_entries[param])
            mx = QLineEdit()
            mx.setMinimumWidth(80)
            mx.setToolTip(TOOLTIPS['max_scale'])
            self._entry_pair(mx, dbv.max_scale_entries[param])
            gs.addWidget(mn, r, 2)
            gs.addWidget(mx, r, 3)
            self.scale_edits[param] = (mn, mx)
        self._refresh_color_buttons()
        # the swatch and name columns keep their width; only the value boxes
        # stretch when the window grows (their text stays left-justified)
        gs.setColumnStretch(0, 0)
        gs.setColumnStretch(1, 0)
        gs.setColumnStretch(2, 1)
        gs.setColumnStretch(3, 1)
        gs.setRowStretch(r + 1, 1)     # r counts the heading row too
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
        grid.setContentsMargins(0, 0, 0, 0)
        # the boxes take the slack and the action row hugs the bottom of the
        # PAGE, exactly like the Qualification tab. This page had a scroll
        # area of its own until v12.0 round 13, and it made '< Back' and
        # 'Generate panels' ride up with the Execution log while the settings
        # shrank; the whole page is inside the tab's scroll area since round
        # 11, so the buttons now scroll with the content instead of following
        # the log (owner, 2026-08-18).
        outer.addLayout(grid, 1)

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

    # ---------- plot colors ----------
    def _refresh_color_buttons(self):
        for param, btn in self.color_buttons.items():
            color = dbv.param_color(param)
            btn.setStyleSheet('QPushButton { background: %s; border: 1px solid '
                              'palette(mid); border-radius: 2px; }' % color)

    def _pick_color(self, param):
        dialog = QColorDialog(QColor(dbv.param_color(param)), self)
        dialog.setWindowTitle('Plot color - %s' % param)
        # Qt's own picker, not the platform one: the reset buttons are added to
        # its button box (and it is the picker that takes a hex code)
        dialog.setOption(QColorDialog.ColorDialogOption.DontUseNativeDialog)
        buttons = dialog.findChild(QDialogButtonBox)
        one = buttons.addButton('Reset this color',
                                QDialogButtonBox.ButtonRole.ResetRole)
        one.setToolTip('Puts %s back to the program default' % param)
        every = buttons.addButton('Reset all colors',
                                  QDialogButtonBox.ButtonRole.ResetRole)
        every.setToolTip('Puts EVERY parameter back to the program default')

        def reset(all_params):
            """Applied at once, with the picker STAYING OPEN (owner,
            2026-08-18) and showing the default it has just restored."""
            if all_params:
                dbv.reset_param_colors()
                self.shell.log_line('Info: every parameter back to its default '
                                    'plot color (saved).')
            else:
                dbv.set_param_color(param, None)
                self.shell.log_line('Info: %s back to its default color %s '
                                    '(saved).' % (param, dbv.param_color(param)))
            self._refresh_color_buttons()
            dialog.setCurrentColor(QColor(dbv.param_color(param)))

        one.clicked.connect(lambda: reset(False))
        every.clicked.connect(lambda: reset(True))
        # only once the picker is on screen: before that its columns are
        # still at their size-hint positions and the HTML field would be
        # stretched to the wrong edge (measured)
        QTimer.singleShot(0, lambda: _line_up_picker(dialog, buttons,
                                                     one, every))

        if dialog.exec() != QColorDialog.DialogCode.Accepted:
            return
        chosen = dialog.selectedColor()
        # compared with the LIVE color, not the one the picker opened with: OK
        # right after a reset must not write the default back as an override
        if not chosen.isValid() or chosen.name() == dbv.param_color(param):
            return
        dbv.set_param_color(param, chosen.name())
        self._refresh_color_buttons()
        self.shell.log_line('Info: %s will be plotted in %s (saved).'
                            % (param, chosen.name()))

    def _generate(self):
        dbv.generatePanels()
        self.refresh_step2()   # a run may adjust settings (e.g. skipped T-S)

    def _back(self):
        dbv._go_step1()
        self.stack.setCurrentIndex(0)
        self.refresh_step1()
        qtheme.scroll_to_top(self)

# -*- coding: utf-8 -*-
"""QCS v12.0 interface preview (PySide6/Qt) - NOT the real app.

Mocks the Data Qualification tab with the real widget structure. Owner
decisions applied (2026-08-14): Fusion style, with a Dark mode toggle in
the View menu (like today's app); View menu before Help; base font raised
to 10.5 pt; 'Parameter settings' on the left corner and a bigger, centered
'Run qualification' button.

Run with:  QCS_v12_preview.bat  (Desktop)
No QC logic here; buttons only log what they would do.
"""
import sys

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QAction, QColor, QPalette
from PySide6.QtWidgets import (QAbstractButton,
                               QApplication, QCheckBox, QComboBox, QDockWidget,
                               QFileDialog, QFormLayout, QGridLayout,
                               QGroupBox, QHBoxLayout, QLabel, QLineEdit,
                               QMainWindow, QProgressBar, QPushButton,
                               QRadioButton, QTabWidget, QTextEdit,
                               QVBoxLayout, QWidget)

APP_TITLE = 'QCS v12.0 preview  -  choose the interface style in View > Interface style'

# The REAL tooltip texts, synced with QCS_Main.TOOLTIPS after the v11.6.1
# editorial pass, so the owner reviews the actual content, not stand-ins.
TOOLTIPS = {
    'co2_file': "Seaguard only, one deployment at a time: adds the separate CO2\nlogger's export (.txt/.csv) -> 'CO2 Level (ppm)' column + CO2 tests\n(values time-interpolated onto the Seaguard timestamps).\nCO2 timestamps are used as-is: the GMT-3 correction never touches them",
    'data_file': "Raw data file(s) to qualify: .csv, .xlsx, Seaguard .bin session\nor raw HOBO .hobo\nSeaguard: several files = a batch, qualified in sequence\nHOBO: several files = replicates of one deployment, combined",
    'macroregion': "Broad world region (currently only Brazil)",
    'region': "Sets the site's representative latitude/longitude, used only to run\nthe tests: pressure->depth and density inversion (Seaguard),\nseasonal light correction (HOBO)\nSmall variations do not change the results",
    'input_type': "Instrument family: Seaguard (CTD platform) or HOBO\n(temperature/light logger)\nAuto-detected from the selected file",
    'data_type': "Seaguard collection type: Profile (vertical cast),\nMooring (fixed point) or Doppler (DCPS current profiler,\nauto-detected from the .bin)",
    'gmt_correction': "Converts the Seaguard clock (GMT) to local time - always ON for\nSeaguard runs\nHOBO and CO2 files are already local: HOBO disables it and the\nCO2 merge bypasses it",
    'profile_selection': "Profiles only: keeps a single phase of the cast\n(descent or ascent)",
    'variable_check': "Manual point cut: pick the variables, then dismiss spurious points\non a plot\nDismissed points get DISMISSED (5) and stay in the sheet for\ntraceability",
    'light_cutoff_mode': "HOBO only: how the light usable window ends\nReviewed (adaptive): the fouling decline is read from the light and\nthe proposed cutoff is reviewed on a plot (drag to adjust)\nFixed window: light -> BAD (4) a fixed number of days after deployment\n(lux_fixed_days, default 60); avoids the seasonal confound",
    'output_folder': "Folder for the qualification outputs",
    'output_name': "Base name of the output files (no extension);\nauto-filled from the selection",
    'output_format': "Qualified table format: .xlsx or .csv\n(report files are always .xlsx)",
    'remove_bad': "Blanks values flagged BAD (4) in the output\n(rows and timestamps are kept)",
    'remove_suspect': "Blanks values flagged SUSPECT (3) in the output\n(rows and timestamps are kept)",
    'site_code': "Site identification code, stamped on every row\n(max 20 characters)",
    'run_button': "Qualifies the selected file(s) with the current parameters",
    'settings_button': "Opens the quality tests and parameters window",
    'summary': "What the readers detected in the selected files (instrument,\nreplicates, period, interval, serials, timebase)\nFilled when the files are chosen - confirm the deployment\nbefore running",
    'log_area': "Progress, warnings and errors of the current run\nRight-click for copy options",
    'log_float': "Detaches the log into its own window (drag it back to re-dock)",
    'log_close': "Hides the log; messages keep accumulating\nReopen it in View > Execution log",
}


def dark_palette():
    p = QPalette()
    bg, base, text = QColor(37, 37, 38), QColor(30, 30, 30), QColor(220, 220, 220)
    hl = QColor(42, 130, 218)
    for role, color in ((QPalette.Window, bg), (QPalette.WindowText, text),
                        (QPalette.Base, base), (QPalette.AlternateBase, bg),
                        (QPalette.Text, text), (QPalette.Button, bg),
                        (QPalette.ButtonText, text), (QPalette.Highlight, hl),
                        (QPalette.HighlightedText, QColor('white')),
                        (QPalette.ToolTipBase, base), (QPalette.ToolTipText, text)):
        p.setColor(role, color)
    return p


class Preview(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_TITLE)
        self.resize(1180, 760)

        tabs = QTabWidget()
        tabs.addTab(self._qualification_tab(), 'Data qualification')
        tabs.addTab(self._visualization_stub(), 'Data visualization')
        tf = tabs.tabBar().font()
        tf.setBold(True)                     # main tabs in evidence (owner)
        tabs.tabBar().setFont(tf)
        self.setCentralWidget(tabs)

        # Execution log as a DOCK: draggable, collapsible, closable - the Qt
        # answer to v11.3's Hide log button. Grayed background to stand off
        # the input fields (owner request), and the SAME severity colors as
        # today's LogConsole: Info default, Warning amber, Error red,
        # Done green.
        self.log = QTextEdit(readOnly=True)
        self.log.setObjectName('ExecutionLog')
        dock = QDockWidget('Execution log', self)
        dock.setWidget(self.log)
        self.addDockWidget(Qt.BottomDockWidgetArea, dock)
        self.dock = dock
        self.log.setToolTip(TOOLTIPS['log_area'])
        # the float/close buttons live in the dock's default title bar; Qt
        # names them but gives them no tooltips of its own
        for btn in dock.findChildren(QAbstractButton):
            if 'float' in btn.objectName():
                btn.setToolTip(TOOLTIPS['log_float'])
            elif 'close' in btn.objectName():
                btn.setToolTip(TOOLTIPS['log_close'])
        for demo in ('Info: this is the Execution log (drag me, undock me, '
                     'close me - View menu brings me back).',
                     'Warning: warnings show in amber, like today.',
                     'Error: errors show in red.',
                     'Done: success shows in green.'):
            self.log_line(demo)

        self._menus()
        self.statusBar().showMessage('Preview only - no QC logic behind the buttons')
        # pipeline progress in the status bar, fed by the same stage
        # messages the pipeline already logs (hidden while idle)
        self.progress = QProgressBar()
        self.progress.setRange(0, 5)
        self.progress.setFixedWidth(220)
        self.progress.setVisible(False)
        self.statusBar().addPermanentWidget(self.progress)

    LOG_COLORS = {'light': {'error': '#b30000', 'warning': '#9a6a00',
                            'success': '#1f7a1f', 'default': '#202020'},
                  'dark': {'error': '#f48771', 'warning': '#dcdcaa',
                           'success': '#89d185', 'default': '#d4d4d4'}}

    def log_line(self, message):
        head = message.lstrip().lower()
        kind = ('error' if head.startswith(('error', 'critical')) else
                'warning' if head.startswith('warning') else
                'success' if head.startswith(('done', 'success')) else
                'default')
        scheme = 'dark' if QApplication.instance().property('qcs_dark') else 'light'
        self.log.append('<span style="color:%s">%s</span>'
                        % (self.LOG_COLORS[scheme][kind], message))

    def _qualification_tab(self):
        w = QWidget()
        grid = QGridLayout(w)

        gin = QGroupBox('Input settings')
        fin = QFormLayout(gin)
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        self.file_edit = QLineEdit()
        self.file_edit.setPlaceholderText('Select or drop data files here...')
        self.file_edit.setToolTip(TOOLTIPS['data_file'])
        self.file_edit.textChanged.connect(self._update_run_state)
        b = QPushButton('Browse...')
        b.setToolTip(TOOLTIPS['data_file'])
        b.clicked.connect(self._browse)
        co2 = QPushButton('Add CO\u2082 data')
        co2.setToolTip(TOOLTIPS['co2_file'])
        row.addWidget(self.file_edit)
        row.addWidget(b)
        row.addWidget(co2)
        holder = QWidget()
        holder.setLayout(row)
        fin.addRow('Data file(s):', holder)
        typ = QComboBox()
        typ.addItems(['Seaguard', 'HOBO'])
        typ.setToolTip(TOOLTIPS['input_type'])
        fin.addRow('Input type:', typ)
        dt = QComboBox()
        dt.addItems(['TSCP Profile', 'TSCP Mooring', 'TSCP Doppler'])
        dt.setToolTip(TOOLTIPS['data_type'])
        fin.addRow('Data type:', dt)
        lm = QHBoxLayout()
        lm.setContentsMargins(0, 0, 0, 0)   # radios level with their label
        for lbl, chk in (('Reviewed (adaptive)', True), ('Fixed window', False)):
            rb_ = QRadioButton(lbl, checked=chk)
            rb_.setToolTip(TOOLTIPS['light_cutoff_mode'])
            lm.addWidget(rb_)
        lm.addStretch()
        lmh = QWidget()
        lmh.setLayout(lm)
        lmh.setToolTip(TOOLTIPS['light_cutoff_mode'])
        fin.addRow('Light cutoff:', lmh)
        mac = QComboBox()
        mac.addItems(['Brazil'])
        mac.setToolTip(TOOLTIPS['macroregion'])
        fin.addRow('Macroregion:', mac)
        reg = QComboBox()
        reg.addItems(['Abrolhos (BA)'])
        reg.setToolTip(TOOLTIPS['region'])
        fin.addRow('Region:', reg)
        # Site code lives with the INPUT metadata now (owner decision - it
        # identifies the deployment, not the output)
        self.site_edit = QLineEdit()
        self.site_edit.setPlaceholderText('e.g. PLES')
        self.site_edit.setToolTip(TOOLTIPS['site_code'])
        self.site_edit.textChanged.connect(self._update_run_state)
        fin.addRow('Site code:', self.site_edit)
        # the three toggles LAST, boxed like Data filtering (owner request)
        gopt = QGroupBox('Options')
        vo = QVBoxLayout(gopt)
        for lbl, key in (('Correct GMT-3', 'gmt_correction'),
                         ('Select profile data', 'profile_selection'),
                         ('Check variables', 'variable_check')):
            cb = QCheckBox(lbl)
            cb.setToolTip(TOOLTIPS[key])
            vo.addWidget(cb)
        fin.addRow(gopt)

        gout = QGroupBox('Output settings')
        fout = QFormLayout(gout)
        self.out_folder = QLineEdit()
        self.out_folder.setPlaceholderText(
            'Choose where the qualified outputs will be saved...')
        self.out_folder.setToolTip(TOOLTIPS['output_folder'])
        self.out_folder.textChanged.connect(self._update_run_state)
        fout.addRow('Output folder:', self.out_folder)
        self.out_name = QLineEdit()
        self.out_name.setPlaceholderText(
            'Name for the qualified output (auto-filled from the selection)...')
        self.out_name.setToolTip(TOOLTIPS['output_name'])
        self.out_name.textChanged.connect(self._update_run_state)
        fout.addRow('Output file name:', self.out_name)
        fmt = QComboBox()
        fmt.addItems(['.xlsx', '.csv'])
        fmt.setToolTip(TOOLTIPS['output_format'])
        fout.addRow('Output format:', fmt)
        gfil = QGroupBox('Data filtering')
        vf = QVBoxLayout(gfil)
        for lbl, key in (('Remove bad data', 'remove_bad'),
                         ('Remove suspect data', 'remove_suspect')):
            cb = QCheckBox(lbl)
            cb.setToolTip(TOOLTIPS[key])
            vf.addWidget(cb)
        fout.addRow(gfil)
        # the dead space below Output becomes the SELECTION SUMMARY: what
        # the readers detected, at a glance, before RUN (today this scrolls
        # by in the log). Example values shown in the preview.
        gsum = QGroupBox('Selection summary')
        gsum.setToolTip(TOOLTIPS['summary'])
        fsum = QFormLayout(gsum)
        for k, v in (('Instrument:', 'HOBO UA-002-64 Pendant Temp/Light'),
                     ('Replicates:', '2 (HOBO1 + HOBO2)'),
                     ('Period:', '20/09/2025  to  16/03/2026'),
                     ('Interval:', '1 h  /  2 h  (differ - see log warning)'),
                     ('Serial(s):', '21832742, 21832736'),
                     ('Timebase:', 'local (HOBO) - GMT-3 correction off')):
            lab = QLabel(v)
            lab.setStyleSheet('color: palette(mid);')
            fsum.addRow(k, lab)
        fout.addRow(gsum)

        # Parameter settings on the LEFT corner; Run qualification truly
        # CENTERED and in evidence (owner decisions, 2026-08-14). The button
        # stays DISABLED until the required fields are set - the hint beside
        # it names the missing piece; no more pop-up scolding after RUN.
        self.run_btn = QPushButton('Run qualification')
        self.run_btn.setDefault(True)
        self.run_btn.setMinimumSize(260, 42)
        f = self.run_btn.font()
        f.setBold(True)
        f.setPointSizeF(f.pointSizeF() + 1)
        self.run_btn.setFont(f)
        self.run_btn.setToolTip(TOOLTIPS['run_button'])
        self.run_btn.clicked.connect(self._demo_run)
        self.run_hint = QLabel('')
        self.run_hint.setStyleSheet('color: palette(mid);')
        settings = QPushButton('Parameter settings')
        settings.setToolTip(TOOLTIPS['settings_button'])

        grid.addWidget(gin, 0, 0)
        grid.addWidget(gout, 0, 1)
        actions = QGridLayout()
        actions.setColumnStretch(0, 1)
        actions.setColumnStretch(1, 1)
        actions.setColumnStretch(2, 1)
        actions.addWidget(settings, 0, 0, Qt.AlignLeft | Qt.AlignVCenter)
        run_box = QVBoxLayout()
        run_box.setContentsMargins(0, 0, 0, 0)
        run_box.addWidget(self.run_btn, alignment=Qt.AlignHCenter)
        run_box.addWidget(self.run_hint, alignment=Qt.AlignHCenter)
        rb = QWidget()
        rb.setLayout(run_box)
        actions.addWidget(rb, 0, 1, Qt.AlignHCenter)
        ah = QWidget()
        ah.setLayout(actions)
        grid.addWidget(ah, 1, 0, 1, 2)
        grid.setRowStretch(0, 1)
        self._update_run_state()
        return w

    def _update_run_state(self):
        """RUN enables only when EVERYTHING required is filled; the hint
        below it names the NEXT missing step, in workflow order, updating
        as each one is completed (owner decision - no pop-up scolding)."""
        if not hasattr(self, 'run_btn'):
            return                          # fields still being built
        steps = ((self.file_edit, 'choose or drop the data file(s) to begin'),
                 (self.site_edit, 'fill in the Site code'),
                 (self.out_folder, 'choose the output folder'),
                 (self.out_name, 'name the output file'))
        missing = next((hint for widget, hint in steps
                        if not widget.text().strip()), None)
        self.run_btn.setEnabled(missing is None)
        self.run_hint.setText(missing or '')

    def _demo_run(self):
        # animated stage demo: the SAME stage messages the pipeline logs
        # today drive a progress bar in the status bar
        stages = ['Stage 1/5: reading the input files...',
                  'Stage 2/5: applying the quality tests...',
                  'Stage 3/5: reviewing the light window...',
                  'Stage 4/5: writing the qualified sheets and reports...',
                  'Stage 5/5: generating DataView plots...']
        self.progress.setVisible(True)
        self._stage = 0

        def tick():
            if self._stage < len(stages):
                self.log_line('Info: %s' % stages[self._stage])
                self._stage += 1
                self.progress.setValue(self._stage)
                self.progress.setFormat('Stage %d/5' % self._stage)
                QTimer.singleShot(600, tick)
            else:
                self.log_line('Done: qualification finished (preview).')
                QTimer.singleShot(1200, lambda: self.progress.setVisible(False))
        tick()

    def _visualization_stub(self):
        w = QWidget()
        v = QVBoxLayout(w)
        v.addStretch()
        lab = QLabel('Data visualization tab - same structure as today\n'
                     '(matplotlib panels embed natively in Qt).')
        lab.setAlignment(Qt.AlignCenter)
        v.addWidget(lab)
        v.addStretch()
        return w

    def _browse(self):
        names, _ = QFileDialog.getOpenFileNames(
            self, 'Select data file(s)', '',
            'Data files (*.csv *.xlsx *.bin *.hobo);;All files (*.*)')
        if names:
            self.file_edit.setText(';'.join(names))
            self.log_line('Info: %d file(s) selected.' % len(names))

    def _menus(self):
        # menu order fixed by the owner: File, Edit, Tools, View, Help
        mb = self.menuBar()
        for name in ('File', 'Edit', 'Tools'):
            mb.addMenu(name).addAction('(preview)')
        view = mb.addMenu('View')
        dark = QAction('Dark mode', self, checkable=True)
        dark.triggered.connect(
            lambda on: apply_style('fusion-dark' if on else 'fusion'))
        view.addAction(dark)
        view.addSeparator()
        view.addAction(self.dock.toggleViewAction())
        mb.addMenu('Help').addAction('(preview)')


def apply_style(key):
    # Fusion, light or dark (owner decision) - the scheme is pinned so the
    # toggle, not the OS, decides; the base font is raised to 10.5 pt
    # (Qt's Windows default ~9 pt read too small)
    app = QApplication.instance()
    font = app.font()
    font.setPointSizeF(10.5)
    app.setFont(font)
    dark = (key == 'fusion-dark')
    app.setProperty('qcs_dark', dark)
    if dark:
        app.styleHints().setColorScheme(Qt.ColorScheme.Dark)
        app.setStyle('Fusion')
        app.setPalette(dark_palette())
    else:
        app.styleHints().setColorScheme(Qt.ColorScheme.Light)
        app.setStyle('Fusion')
        app.setPalette(app.style().standardPalette())
    # the log stands off the white/dark input fields, and the two main tabs
    # carry bold labels (owner requests)
    app.setStyleSheet(
        'QTextEdit#ExecutionLog { background: %s; }\n'
        'QTabBar::tab { font-weight: bold; padding: 6px 14px; }'
        % ('#232324' if dark else '#e9e9e9'))


def main():
    app = QApplication(sys.argv)
    style = sys.argv[sys.argv.index('--style') + 1] if '--style' in sys.argv else 'fusion'
    apply_style(style)          # before the window: the log colors by scheme
    win = Preview()
    if '--shot' in sys.argv:
        # screenshot mode: the window is NEVER shown - grab() renders the
        # laid-out widget to a pixmap with the real platform fonts/style
        out = sys.argv[sys.argv.index('--shot') + 1]
        # stage the demo states the screenshots document: mid-guidance in
        # light (files chosen, Site code still missing -> hint names it),
        # ready-to-run in dark (everything filled, RUN enabled, stage 3/5)
        win.file_edit.setText('HOBO1_PLES_A1_200925_160326.hobo;'
                              'HOBO2_PLES_A1_200925_160326.hobo')
        if style == 'fusion-dark':
            win.site_edit.setText('PLES')
            win.out_folder.setText(r'C:\dados\PLES')
            win.out_name.setText('PLES_A1_200925_160326_combined_QLF')
            win.progress.setVisible(True)
            win.progress.setValue(3)
            win.progress.setFormat('Stage 3/5')
        # stage ONE tooltip (they only pop on hover, which a screenshot
        # cannot do): a label styled with the tooltip palette, over the
        # Light cutoff row, showing the REAL text
        tip = QLabel(TOOLTIPS['light_cutoff_mode'], win)
        dark_shot = (style == 'fusion-dark')
        tip.setStyleSheet(
            'background: %s; color: %s; border: 1px solid #767676; '
            'padding: 6px;' % (('#3c3c3c', '#e8e8e8') if dark_shot
                               else ('#ffffdc', '#202020')))
        tip.adjustSize()
        tip.move(210, 250)
        tip.show()
        app.processEvents()
        win.grab().save(out)
        return 0
    win.show()
    return app.exec()


if __name__ == '__main__':
    sys.exit(main())

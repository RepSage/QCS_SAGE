# -*- coding: utf-8 -*-
"""QCS v12.0 Qt shell - phase 1 of the interface port (DEV build).

The REAL qualification pipeline behind the approved Qt design: this window
fills the same `vals` dict as the tk interface (QCS_Main.apply_input_settings)
and runs the same start_qualification, with the UI facade pointed at Qt.
The tk pipeline closures are materialized once on a hidden tk root (the same
pattern the batch drivers use); no tk window is ever shown and no tk event
loop runs - every in-run interaction goes through the Qt overrides below.

Working in this build: Seaguard single/batch/Doppler/Profile qualification
(without 'Select profile data'), CO2 merge, HOBO single and replicates in
BOTH light modes (the adaptive review plot is pure matplotlib and opens as a
Qt window), the mooring Depth review, drag-and-drop, preferences (shared
qcs_user_settings.json). Not yet ported (phase 2): the Settings window,
'Select profile data' phase picking, 'Check variables' manual cut, the
replicate-review window (all replicates are kept, with a logged warning),
and the Data visualization tab.

Run with:  QCS_v12_dev.bat  (Desktop; packaging/v12_env venv, PySide6 6.8.3).
Master still ships the tk app - this shell is the port in progress.
"""
import os
import re
import sys

import matplotlib
matplotlib.use('QtAgg')            # before any QCS import binds pyplot

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import (QApplication, QCheckBox, QComboBox,
                               QFileDialog, QFormLayout, QGridLayout,
                               QGroupBox, QHBoxLayout, QLabel, QLineEdit,
                               QMainWindow, QMessageBox, QProgressBar,
                               QPushButton, QRadioButton, QTabWidget,
                               QToolButton, QVBoxLayout, QWidget)

import QCS_Theme as theme          # writable_app_dir + output redirect (shared)
_out = theme.install_output_redirect()
import QCS_QtTheme as qtheme
import QCS_Main as qm
import QCS_DataHandler as data

TOOLTIPS = qm.TOOLTIPS             # single source: the real texts (v11.6.1)

_ICON_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'qcs_icon.png')


def _app_icon():
    return QIcon(_ICON_PATH) if os.path.isfile(_ICON_PATH) else QIcon()


def _qt_style_plot_window(fig, title=None):
    """Qt replacement for theme.style_plot_window: app icon + meaningful title
    on the matplotlib window, brought to the front."""
    try:
        mgr = fig.canvas.manager
        if title:
            mgr.set_window_title(title)
        win = getattr(mgr, 'window', None)
        if win is not None:
            win.setWindowIcon(_app_icon())
            win.raise_()
            win.activateWindow()
    except Exception:
        pass


def wait_figure_close(fig):
    """Qt replacement for the pipeline's figure waits: shows the interactive
    matplotlib window (QtAgg) and pumps Qt events until it is closed."""
    state = {'open': True}

    def _closed(_event):
        state['open'] = False
        fig.canvas.stop_event_loop()

    fig.canvas.mpl_connect('close_event', _closed)
    fig.show()
    try:
        win = fig.canvas.manager.window
        win.setWindowIcon(_app_icon())   # figures not routed through style_plot_window
        win.raise_()
        win.activateWindow()
    except Exception:
        pass
    if state['open']:
        fig.canvas.start_event_loop()


class QtShell(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('QCS - Quality Control System %s  (v12.0 shell, phase 1)'
                            % data.QCS_VERSION)
        self.setWindowIcon(_app_icon())
        self.resize(1180, 760)
        self.setAcceptDrops(True)   # Qt-native drag-and-drop, whole window
        self._last_seaguard = {}    # Data type/GMT stored while HOBO is selected
        self._co2_file = ''
        self._run_scope = None      # 'File k/n' / 'Replicate k/n' progress prefix

        tabs = QTabWidget()
        tabs.addTab(self._qualification_tab(), 'Data qualification')
        tabs.addTab(self._visualization_stub(), 'Data visualization')
        self.setCentralWidget(tabs)

        self.log_dock = qtheme.LogDock(self)
        self.addDockWidget(Qt.BottomDockWidgetArea, self.log_dock)
        self._menus()
        self.statusBar().showMessage('v12.0 phase 1 - the tk app on master remains the released interface')
        # pipeline progress, bottom right: indeterminate while a single run is
        # busy, and a real fraction on the batch/replicate markers the
        # pipeline already logs ('=== File k/n ===' / '=== Replicate k/n ===')
        self.progress = QProgressBar()
        self.progress.setFixedWidth(220)
        self.progress.setVisible(False)
        self.statusBar().addPermanentWidget(self.progress)

    # ----- logging -----
    def log_line(self, message):
        # the pipeline's own markers drive the progress bar: every run logs
        # 'Stage k/5' (value + text), and batches/replicates prefix the text
        # with their '=== File k/n ===' / '=== Replicate k/n ===' scope
        msg = message.strip()
        m = re.match(r'=== (File|Replicate) (\d+)/(\d+)', msg)
        if m:
            self._run_scope = '%s %s/%s' % (m.group(1), m.group(2), m.group(3))
            self.progress.setRange(0, 5)
            self.progress.setValue(0)
            self.progress.setFormat(self._run_scope)
        else:
            s = re.match(r'Stage (\d)/5', msg)
            if s:
                stage = int(s.group(1))
                self.progress.setRange(0, 5)
                self.progress.setValue(stage)
                self.progress.setFormat(
                    '%s - Stage %d/5' % (self._run_scope, stage)
                    if self._run_scope else 'Stage %d/5' % stage)
        self.log_dock.log(message)
        QApplication.processEvents()   # progress shows while the pipeline runs

    # ----- qualification tab -----
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
        self.file_edit.textChanged.connect(self._file_text_changed)
        browse = QPushButton('Browse...')
        browse.setToolTip(TOOLTIPS['data_file'])
        browse.clicked.connect(self._browse)
        self.co2_btn = QPushButton('Add CO₂ data')
        self.co2_btn.setToolTip(TOOLTIPS['co2_file'])
        self.co2_btn.clicked.connect(self._select_co2)
        row.addWidget(self.file_edit)
        row.addWidget(browse)
        row.addWidget(self.co2_btn)
        holder = QWidget()
        holder.setLayout(row)
        fin.addRow('Data file(s):', holder)

        self.input_type = QComboBox()
        self.input_type.addItems(['Seaguard', 'HOBO'])
        self.input_type.setPlaceholderText('Select instrument')
        self.input_type.setCurrentIndex(-1)   # no instrument until a file (or prefs) says so
        self.input_type.setToolTip(TOOLTIPS['input_type'])
        self.input_type.currentTextChanged.connect(self._input_type_changed)
        fin.addRow('Instrument:', self.input_type)

        self.data_type = QComboBox()
        self.data_type.addItems(['TSCP Profile', 'TSCP Mooring', 'TSCP Doppler'])
        self.data_type.setToolTip(TOOLTIPS['data_type'])
        self.data_type.currentTextChanged.connect(lambda _t: self._update_profile_state())
        fin.addRow('Data type:', self.data_type)

        # replicates display + the selected CO2 file, one info row
        info_row = QHBoxLayout()
        info_row.setContentsMargins(0, 0, 0, 0)
        self.replicate_value = QLabel('')
        self.replicate_value.setToolTip(
            "HOBO only: number of replicate files selected in Browse\n"
            "(set automatically; each replicate is qualified separately,\n"
            "then combined into one series)")
        info_row.addWidget(self.replicate_value)
        info_row.addSpacing(16)
        self.co2_label = QLabel('')
        info_row.addWidget(self.co2_label)
        self.co2_clear = QToolButton()
        self.co2_clear.setText('×')
        self.co2_clear.setToolTip('Removes the selected CO2 file')
        self.co2_clear.clicked.connect(self._clear_co2)
        self.co2_clear.setVisible(False)
        info_row.addWidget(self.co2_clear)
        info_row.addStretch()
        ih = QWidget()
        ih.setLayout(info_row)
        fin.addRow('Replicates:', ih)
        # the row only exists while there is a HOBO selection to count
        self._fin = fin
        self._replicates_holder = ih
        fin.setRowVisible(ih, False)

        lm = QHBoxLayout()
        lm.setContentsMargins(0, 0, 0, 0)
        self.light_adaptive = QRadioButton('Reviewed (adaptive)', checked=True)
        self.light_fixed = QRadioButton('Fixed window')
        for rb in (self.light_adaptive, self.light_fixed):
            rb.setToolTip(TOOLTIPS['light_cutoff_mode'])
            lm.addWidget(rb)
        lm.addStretch()
        lmh = QWidget()
        lmh.setLayout(lm)
        lmh.setToolTip(TOOLTIPS['light_cutoff_mode'])
        fin.addRow('Light cutoff:', lmh)

        self.macroregion = QComboBox()
        self.macroregion.addItems(list(qm.REGIONS.keys()))
        self.macroregion.setCurrentText(qm.DEFAULT_MACROREGION)
        self.macroregion.setToolTip(TOOLTIPS['macroregion'])
        self.macroregion.currentTextChanged.connect(self._update_regions)
        fin.addRow('Macroregion:', self.macroregion)
        self.region = QComboBox()
        self.region.setToolTip(TOOLTIPS['region'])
        fin.addRow('Region:', self.region)
        self._update_regions()
        self.region.setCurrentText(qm.DEFAULT_REGION)

        self.site_edit = QLineEdit()
        self.site_edit.setPlaceholderText('e.g. PLES')
        self.site_edit.setMaxLength(qm.SITE_CODE_MAX)
        self.site_edit.setToolTip(TOOLTIPS['site_code'])
        self.site_edit.textChanged.connect(self._update_run_state)
        fin.addRow('Site code:', self.site_edit)

        gopt = QGroupBox('Options')
        vo = QVBoxLayout(gopt)
        self.gmt_check = QCheckBox('Correct GMT-3', checked=True)
        self.gmt_check.setToolTip(TOOLTIPS['gmt_correction'])
        vo.addWidget(self.gmt_check)
        self.profile_check = QCheckBox('Select profile data')
        self.profile_check.setToolTip(TOOLTIPS['profile_selection']
                                      + '\n(not yet in this v12.0 build)')
        self.profile_check.setEnabled(False)     # phase 2: tk phase-pick windows
        vo.addWidget(self.profile_check)
        self.varcheck = QCheckBox('Check variables')
        self.varcheck.setToolTip(TOOLTIPS['variable_check']
                                 + '\n(not yet in this v12.0 build)')
        self.varcheck.setEnabled(False)          # phase 2: manual-cut chooser
        vo.addWidget(self.varcheck)
        fin.addRow(gopt)

        gout = QGroupBox('Output settings')
        fout = QFormLayout(gout)
        orow = QHBoxLayout()
        orow.setContentsMargins(0, 0, 0, 0)
        self.out_folder = QLineEdit()
        self.out_folder.setPlaceholderText('Choose where the qualified outputs will be saved...')
        self.out_folder.setToolTip(TOOLTIPS['output_folder'])
        self.out_folder.textChanged.connect(self._update_run_state)
        ob = QPushButton('Browse...')
        ob.setToolTip(TOOLTIPS['output_folder'])
        ob.clicked.connect(self._browse_output)
        orow.addWidget(self.out_folder)
        orow.addWidget(ob)
        oh = QWidget()
        oh.setLayout(orow)
        fout.addRow('Output folder:', oh)
        self.out_name = QLineEdit()
        self.out_name.setPlaceholderText('Name for the qualified output (auto-filled from the selection)...')
        self.out_name.setToolTip(TOOLTIPS['output_name'])
        self.out_name.textChanged.connect(self._update_run_state)
        fout.addRow('Output file name:', self.out_name)
        self.out_format = QComboBox()
        self.out_format.addItems(['.xlsx', '.csv'])   # .xlsx factory default (v11.4.2)
        self.out_format.setToolTip(TOOLTIPS['output_format'])
        fout.addRow('Output format:', self.out_format)
        gfil = QGroupBox('Data filtering')
        vf = QVBoxLayout(gfil)
        self.remove_bad = QCheckBox('Remove bad data')
        self.remove_bad.setToolTip(TOOLTIPS['remove_bad'])
        vf.addWidget(self.remove_bad)
        self.remove_suspect = QCheckBox('Remove suspect data')
        self.remove_suspect.setToolTip(TOOLTIPS['remove_suspect'])
        vf.addWidget(self.remove_suspect)
        self.remove_dismissed = QCheckBox('Remove dismissed data')
        self.remove_dismissed.setToolTip(TOOLTIPS['remove_dismissed'])
        vf.addWidget(self.remove_dismissed)
        fout.addRow(gfil)

        gsum = QGroupBox('Selection summary')
        gsum.setToolTip(TOOLTIPS.get('summary', ''))
        fsum = QFormLayout(gsum)
        self.sum_labels = {}
        for key, label in (('instrument', 'Instrument:'), ('files', 'Files:'),
                           ('mode', 'Mode:'), ('timebase', 'Timebase:')):
            lab = QLabel('-')
            lab.setStyleSheet('color: palette(mid);')
            self.sum_labels[key] = lab
            fsum.addRow(label, lab)
        fout.addRow(gsum)

        self.run_btn = QPushButton('Run qualification')
        self.run_btn.setDefault(True)
        self.run_btn.setMinimumSize(260, 42)
        f = self.run_btn.font()
        f.setBold(True)
        f.setPointSizeF(f.pointSizeF() + 1)
        self.run_btn.setFont(f)
        self.run_btn.setToolTip(TOOLTIPS['run_button'])
        self.run_btn.clicked.connect(self._run)
        self.run_hint = QLabel('')
        self.run_hint.setStyleSheet('color: palette(mid);')
        settings = QPushButton('Parameter settings')
        settings.setToolTip(TOOLTIPS['settings_button'])
        settings.clicked.connect(self._open_settings)

        grid.addWidget(gin, 0, 0)
        grid.addWidget(gout, 0, 1)
        actions = QGridLayout()
        for col in range(3):
            actions.setColumnStretch(col, 1)
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
        self._input_type_changed(self.input_type.currentText())
        self._update_run_state()
        return w

    def _visualization_stub(self):
        w = QWidget()
        v = QVBoxLayout(w)
        v.addStretch()
        lab = QLabel('The Data visualization tab arrives in a later v12.0 build.\n'
                     'Until then, use the released (tk) app for visualization.')
        lab.setAlignment(Qt.AlignCenter)
        v.addWidget(lab)
        v.addStretch()
        return w

    def _menus(self):
        mb = self.menuBar()
        filem = mb.addMenu('File')
        act_exit = QAction('Exit', self)
        act_exit.triggered.connect(self.close)
        filem.addAction(act_exit)
        view = mb.addMenu('View')
        self.dark_action = QAction('Dark mode', self, checkable=True)
        self.dark_action.triggered.connect(self._toggle_dark)
        view.addAction(self.dark_action)
        view.addSeparator()
        view.addAction(self.log_dock.toggleViewAction())
        helpm = mb.addMenu('Help')
        manual = QAction('User manual', self)
        manual.triggered.connect(self._open_manual)
        helpm.addAction(manual)
        about = QAction('About', self)
        about.triggered.connect(lambda: QMessageBox.information(
            self, 'QCS', 'QCS - Quality Control System %s\n'
            'v12.0 interface port, phase 1 (Qt/PySide6).' % data.QCS_VERSION))
        helpm.addAction(about)

    def _toggle_dark(self, on):
        qtheme.apply_style(on)
        qm.USER_PREFS['ui_theme'] = 'dark' if on else 'light'
        qm.save_user_prefs()

    def _open_manual(self):
        path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                            'Quality Control System (SAGE) - User Manual.html')
        if os.path.isfile(path):
            os.startfile(path)
        else:
            QMessageBox.warning(self, 'User manual', 'Manual not found:\n%s' % path)

    def _open_settings(self):
        from QCS_QtSettings import SettingsDialog
        SettingsDialog(self).exec()

    # ----- drag-and-drop (Qt-native: one handler pair for the whole window) -----
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        paths = [u.toLocalFile() for u in event.mimeData().urls()
                 if u.isLocalFile()]
        if paths:
            self.apply_selected_files(paths)

    # ----- file selection (port of QCS_Main.apply_selected_files) -----
    def _browse(self):
        names, _f = QFileDialog.getOpenFileNames(
            self, ('Select the HOBO file(s) - one per replicate'
                   if self.input_type.currentText() == 'HOBO'
                   else 'Select data file(s) - each is qualified in sequence'),
            qm.USER_PREFS.get('last_data_dir', ''),
            'Data files (*.csv *.xlsx *.bin *.hobo);;All files (*.*)')
        if names:
            self.apply_selected_files(names)

    def apply_selected_files(self, names):
        first = names[0]
        self.file_edit.setText(';'.join(names))
        qm.USER_PREFS['last_data_dir'] = os.path.dirname(first)
        qm.save_user_prefs()
        detected = data.sniff_input_type(first)
        if detected:
            if detected != self.input_type.currentText():
                self.input_type.setCurrentText(detected)   # triggers the state update
                print('Info: input type auto-detected as %s (from the file header).' % detected)
            # the detected family is a fact of the file, not a choice: lock the
            # box so it cannot be overridden by mistake (owner request); it
            # unlocks when the selection is cleared or an unrecognized file
            # is selected
            self.input_type.setEnabled(False)
        else:
            self.input_type.setEnabled(True)
            print('Info: could not auto-detect the input type from the file header; '
                  'kept "%s" (editable).' % self.input_type.currentText())
        if self.input_type.currentText() == 'HOBO':
            self._set_replicates(str(len(names)))
        elif len(names) > 1:
            print('Info: %d files selected - each will be qualified independently, '
                  'in sequence (one _QLF output per file).' % len(names))
        if self.input_type.currentText() == 'Seaguard' and first.lower().endswith('.bin'):
            if data.is_seaguard_doppler(first):
                if self.data_type.currentText() != 'TSCP Doppler':
                    self.data_type.setCurrentText('TSCP Doppler')
                    print("Info: DCPS current profiler detected - Data type set to 'TSCP Doppler'.")
            elif self.data_type.currentText() == 'TSCP Doppler':
                self.data_type.setCurrentText('TSCP Mooring')
                print("Info: scalar Seaguard session selected - Data type reset to 'TSCP Mooring'.")
        self.out_folder.setText(os.path.dirname(first))
        self._apply_output_name()
        self._update_co2_controls()
        self._update_summary(names)

    def _apply_output_name(self):
        paths = [p.strip() for p in self.file_edit.text().split(';') if p.strip()]
        if not paths:
            return
        base = qm._output_base_for(paths[0])
        is_hobo = self.input_type.currentText() == 'HOBO'
        self.out_name.setEnabled(True)
        if is_hobo and len(paths) > 1:
            stripped = re.sub(r'(?i)^hobo\s*\d+[ _-]*', '', base)
            self.out_name.setText((stripped or base) + '_combined_QLF')
        elif not is_hobo and len(paths) > 1:
            self.out_name.setText('(automatic: <file>_QLF for each file)')
            self.out_name.setEnabled(False)
        else:
            self.out_name.setText(base + '_QLF')

    def _update_summary(self, names):
        itype = self.input_type.currentText()
        self.sum_labels['instrument'].setText(itype or '-')
        self.sum_labels['files'].setText(
            '%d  (%s%s)' % (len(names), os.path.basename(names[0]),
                            ', ...' if len(names) > 1 else ''))
        if itype == 'HOBO':
            mode = ('%d replicates of one deployment, combined' % len(names)
                    if len(names) > 1 else 'single logger')
            tb = 'local (HOBO) - GMT-3 correction not applied'
        else:
            mode = ('batch: %d files qualified in sequence' % len(names)
                    if len(names) > 1 else
                    ('current profiler (DCPS)'
                     if self.data_type.currentText() == 'TSCP Doppler'
                     else 'single deployment'))
            tb = 'GMT (Seaguard) -> corrected to local (GMT-3)'
        self.sum_labels['mode'].setText(mode)
        self.sum_labels['timebase'].setText(tb)

    # ----- output folder / CO2 -----
    def _browse_output(self):
        path = QFileDialog.getExistingDirectory(
            self, 'Select output folder', qm.USER_PREFS.get('last_output_dir', ''))
        if path:
            self.out_folder.setText(path)
            qm.USER_PREFS['last_output_dir'] = path
            qm.save_user_prefs()

    def _is_seaguard_batch(self):
        files = [p for p in self.file_edit.text().split(';') if p.strip()]
        return self.input_type.currentText() != 'HOBO' and len(files) > 1

    def _update_co2_controls(self):
        allowed = (self.input_type.currentText() == 'Seaguard'
                   and not self._is_seaguard_batch())
        if not allowed and self._co2_file:
            print('Info: CO2 file cleared (CO2 import applies to a single Seaguard '
                  'qualification).')
            self._co2_file = ''
        self.co2_btn.setEnabled(allowed)
        self.co2_label.setText(os.path.basename(self._co2_file) if self._co2_file else '')
        self.co2_clear.setVisible(bool(self._co2_file))

    def _select_co2(self):
        path, _f = QFileDialog.getOpenFileName(
            self, 'Select the dissolved-CO2 logger file',
            qm.USER_PREFS.get('last_data_dir', ''),
            'CO2 logger files (*.txt *.csv);;All files (*.*)')
        if not path:
            return
        try:
            _probe, msgs = data.read_co2_file(path)
            for m in msgs:
                print(m)
        except Exception as e:
            QMessageBox.critical(self, 'CO2 file', 'Could not read the CO2 file:\n%s' % e)
            return
        self._co2_file = path
        self._update_co2_controls()

    def _clear_co2(self):
        self._co2_file = ''
        self._update_co2_controls()

    # ----- field-state machine (port of update_inputtype_state) -----
    def _set_replicates(self, text):
        self.replicate_value.setText(text)
        self._fin.setRowVisible(self._replicates_holder, bool(text))

    def _input_type_changed(self, itype):
        if itype == 'HOBO':
            if self.data_type.currentText():
                self._last_seaguard['data_type'] = self.data_type.currentText()
            self.data_type.setCurrentIndex(-1)   # HOBO is neither profile nor mooring
            self.data_type.setEnabled(False)
            self._last_seaguard['gmt'] = self.gmt_check.isChecked()
            self.gmt_check.setChecked(False)     # HOBO exports are already local
            self.gmt_check.setEnabled(False)
            if not self.replicate_value.text():
                self._set_replicates('1')
            else:
                self._set_replicates(self.replicate_value.text())
            self.light_adaptive.setEnabled(True)
            self.light_fixed.setEnabled(True)
            # HOBO has no Depth column, so no whole-row dismissals ever exist
            self.remove_dismissed.setChecked(False)
            self.remove_dismissed.setEnabled(False)
        elif itype == 'Seaguard':
            if self._last_seaguard.get('data_type'):
                self.data_type.setCurrentText(self._last_seaguard['data_type'])
            self.data_type.setEnabled(True)
            self.gmt_check.setEnabled(True)
            self.gmt_check.setChecked(True)      # Seaguard records GMT: always corrected
            self._set_replicates('')             # replicates are HOBO-only
            self.light_adaptive.setEnabled(False)
            self.light_fixed.setEnabled(False)
            self.remove_dismissed.setEnabled(True)
        else:
            # no instrument selected ('Select instrument' placeholder): the
            # dependent fields wait for a selection
            if self.data_type.currentText():
                self._last_seaguard['data_type'] = self.data_type.currentText()
            self.data_type.setCurrentIndex(-1)
            self.data_type.setEnabled(False)
            self.gmt_check.setChecked(False)
            self.gmt_check.setEnabled(False)
            self._set_replicates('')
            self.light_adaptive.setEnabled(False)
            self.light_fixed.setEnabled(False)
            self.remove_dismissed.setChecked(False)
            self.remove_dismissed.setEnabled(False)
        self._update_profile_state()
        self._apply_output_name()
        self._update_co2_controls()

    def _update_profile_state(self):
        # 'Select profile data' applies to profiles only - and stays disabled
        # in this build anyway (phase 2); the state machine is kept so
        # enabling it later is one line
        pass

    # ----- run -----
    def _file_text_changed(self, text):
        if not text.strip():
            # selection cleared: back to 'Select instrument', editable, and
            # the Replicates line and summary go away with it
            self.input_type.setEnabled(True)
            self.input_type.setCurrentIndex(-1)
            for lab in self.sum_labels.values():
                lab.setText('-')
        self._update_run_state()

    def _update_run_state(self):
        if not hasattr(self, 'run_btn'):
            return
        steps = ((self.file_edit, 'choose or drop the data file(s) to begin'),
                 (self.site_edit, 'fill in the Site code'),
                 (self.out_folder, 'choose the output folder'),
                 (self.out_name, 'name the output file'))
        missing = next((hint for widget, hint in steps
                        if not widget.text().strip()), None)
        self.run_btn.setEnabled(missing is None)
        self.run_hint.setText(missing or '')

    def collect_from_qt(self):
        """Qt replacement for QCS_Main.collect_input_settings: same vals dict,
        same toolkit-free validation."""
        vals = {
            'files_raw': self.file_edit.text(),
            'input_type': self.input_type.currentText(),
            'data_type': self.data_type.currentText(),
            'out_dir': self.out_folder.text(),
            'out_name': self.out_name.text(),
            'out_format': self.out_format.currentText(),
            'correct_gmt3h': self.gmt_check.isChecked(),
            'select_profile_data': False,   # phase 2 (checkbox disabled above)
            'check_variables': False,       # phase 2 (checkbox disabled above)
            'remove_bad': self.remove_bad.isChecked(),
            'remove_suspect': self.remove_suspect.isChecked(),
            'remove_dismissed': self.remove_dismissed.isChecked(),
            'co2_file': self._co2_file,
            'site': self.site_edit.text(),
            'macroregion': self.macroregion.currentText(),
            'region': self.region.currentText(),
            'light_cutoff_mode': 'fixed' if self.light_fixed.isChecked() else 'adaptive',
        }
        if vals['input_type'] == 'HOBO' and vals['files_raw'].strip():
            n = len([p for p in vals['files_raw'].split(';') if p.strip()])
            self._set_replicates(str(n))
        return qm.apply_input_settings(vals)

    def set_busy(self, busy):
        self.run_btn.setEnabled(not busy)
        self.progress.setVisible(busy)
        if busy:
            self._run_scope = None
            self.progress.setRange(0, 0)   # indeterminate until the first Stage marker
            QApplication.setOverrideCursor(Qt.WaitCursor)
        else:
            QApplication.restoreOverrideCursor()
            self._update_run_state()

    def review_replicates_stub(self, qualified_dfs, referee, reference, site):
        self.log_line('Warning: the replicate-review window is not ported yet in '
                      'this v12.0 build - ALL replicates were kept and combined. '
                      'To accept/drop a named replicate, use the released app.')
        return None

    def _update_regions(self, _macro=None):
        macro = self.macroregion.currentText()
        regions = [r[0] for r in qm.REGIONS.get(macro, [])]
        current = self.region.currentText()
        self.region.clear()
        self.region.addItems(regions)
        if current in regions:
            self.region.setCurrentText(current)

    def _run(self):
        qm.start_qualification()

    # ----- prefs -----
    def restore_prefs(self):
        """Mirrors restore_user_prefs onto the Qt widgets (the criteria/version
        gate already ran inside the tk bootstrap's restore)."""
        p = qm.USER_PREFS
        if p.get('input_type') in ('Seaguard', 'HOBO'):
            self.input_type.setCurrentText(p['input_type'])
        if p.get('data_type') and self.input_type.currentText() != 'HOBO':
            self.data_type.setCurrentText(p['data_type'])
        for widget, key in ((self.file_edit, 'data_file'),
                            (self.out_folder, 'output_folder'),
                            (self.out_name, 'output_name'),
                            (self.site_edit, 'site_code')):
            if p.get(key):
                widget.setText(p[key])
        if p.get('output_format') in ('.csv', '.xlsx'):
            self.out_format.setCurrentText(p['output_format'])
        if p.get('light_cutoff_mode') == 'fixed':
            self.light_fixed.setChecked(True)
        elif p.get('light_cutoff_mode') == 'adaptive':
            self.light_adaptive.setChecked(True)
        self.remove_bad.setChecked(bool(p.get('remove_bad', False)))
        self.remove_suspect.setChecked(bool(p.get('remove_suspect', False)))
        if self.remove_dismissed.isEnabled():   # HOBO keeps it off and greyed
            self.remove_dismissed.setChecked(bool(p.get('remove_dismissed', False)))
        if p.get('macroregion') in qm.REGIONS:
            self.macroregion.setCurrentText(p['macroregion'])
        regions = [r[0] for r in qm.REGIONS.get(self.macroregion.currentText(), [])]
        if p.get('region') in regions:
            self.region.setCurrentText(p['region'])
        if p.get('select_profile_data') or p.get('check_variables'):
            print('Info: "Select profile data" / "Check variables" are saved in '
                  'your preferences but not yet available in this v12.0 build - '
                  'they stay OFF here.')


def _bootstrap_tk_pipeline(shared_log):
    """Materializes the pipeline closures (run_full_qualification, the review
    functions, log_line) exactly the way the batch drivers do: the
    qualification tab is built on a hidden tk root that is never shown and
    whose event loop never runs. Every interface touch during a RUN goes
    through the Qt facade installed afterwards. shared_log (the Qt LogDock,
    duck-typed: it only needs .log) stops the build from creating - and
    sinking prints into - a hidden tk log console."""
    root = qm.Tk()
    root.withdraw()
    frame = qm.ttk.Frame(root)
    frame.pack()
    qm.build_qualification_tab(frame, root, shared_log=shared_log)
    return root


def _install_qt_facade(shell):
    qm.ui_info = lambda t, m: QMessageBox.information(shell, t, m)
    qm.ui_warn = lambda t, m: QMessageBox.warning(shell, t, m)
    qm.ui_error = lambda t, m: QMessageBox.critical(shell, t, m)
    qm.ui_info_parented = lambda t, m, parent=None: QMessageBox.information(shell, t, m)
    qm.ui_busy = shell.set_busy
    qm.ui_pump = QApplication.processEvents
    qm.log_line = shell.log_line
    qm.collect_input_settings = shell.collect_from_qt
    qm.review_replicates = shell.review_replicates_stub
    qm.wait_figure_close = wait_figure_close
    data._show_and_wait = lambda fig, tk_root=None: wait_figure_close(fig)
    theme.style_plot_window = _qt_style_plot_window   # app icon on plot windows


def main():
    app = QApplication(sys.argv)
    app.setWindowIcon(_app_icon())
    qtheme.install_crash_handler('QCS (v12.0 shell)')
    dark = qm.USER_PREFS.get('ui_theme') == 'dark'
    qtheme.apply_style(dark)
    shell = QtShell()
    shell.dark_action.setChecked(dark)
    _out.set_sink(shell.log_dock.log)      # prints -> Qt log from here on
    _bootstrap_tk_pipeline(shell.log_dock)  # also runs restore prefs + version gate
    _install_qt_facade(shell)
    shell.restore_prefs()
    if '--shot' in sys.argv:
        # screenshot mode (no dialogs, window never shown): grab() renders the
        # laid-out widget with the real platform fonts/style
        out_path = sys.argv[sys.argv.index('--shot') + 1]
        app.processEvents()
        shell.grab().save(out_path)
        return 0
    if qm.SETTINGS_RESET_FROM:
        QMessageBox.information(
            shell, 'Quality criteria reset',
            'Your saved quality-test criteria were made by program version %s '
            'and this is %s: the criteria were reset to the new defaults.\n\n'
            'File paths and interface choices were kept.'
            % (qm.SETTINGS_RESET_FROM, data.QCS_VERSION))
    shell.show()
    return app.exec()


if __name__ == '__main__':
    sys.exit(main())

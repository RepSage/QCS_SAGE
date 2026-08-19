# -*- coding: utf-8 -*-
"""QCS Qt shell - the released interface since v12.0.

The REAL qualification pipeline behind the Qt design: this window fills the
same `vals` dict as the retired tk interface (QCS_Main.apply_input_settings)
and runs the same start_qualification, with the UI facade pointed at Qt.
The tk pipeline closures are materialized once on a hidden tk root (the same
pattern the batch drivers use); no tk window is ever shown and no tk event
loop runs - every in-run interaction goes through the Qt overrides below.

It hosts the whole program: the qualification workflow (Seaguard
single/batch/Doppler/Profile with phase picking, CO2 merge, HOBO single and
replicates in both light modes with the replicate review, Depth review,
'Check variables' manual cut), the Settings window, and the Data visualization
tab (QCS_QtViz remote-controls the real DatabaseView wizard). The review
windows are pure matplotlib and open as Qt windows.

Run with:  QCS.bat  (packaging/v12_env venv, PySide6 6.8.3).
"""
import os
import re
import sys

import matplotlib
matplotlib.use('QtAgg')            # before any QCS import binds pyplot

from PySide6.QtCore import (QByteArray, QEvent, QObject, QSignalBlocker, Qt,
                            Signal)
from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import (QApplication, QCheckBox, QComboBox, QDialog,
                               QDockWidget, QFileDialog, QFormLayout,
                               QGridLayout, QGroupBox, QHBoxLayout, QLabel,
                               QLineEdit, QMainWindow, QMessageBox,
                               QProgressBar, QProgressDialog, QPushButton,
                               QRadioButton, QScrollArea, QTableWidget,
                               QTableWidgetItem, QTabWidget, QToolButton,
                               QVBoxLayout, QWidget)

import QCS_Theme as theme          # writable_app_dir + output redirect (shared)
_out = theme.install_output_redirect()
import QCS_QtTheme as qtheme
import QCS_Main as qm
import QCS_DataHandler as data
# installs the tk crash handler at import; main() installs the Qt one after
import QCS_DatabaseView as dbv
import QCS_Update as upd
from QCS_QtViz import VisualizationTab

# Both tools share ONE preferences dict, so saving from either tab writes the
# same qcs_user_settings.json without clobbering the other tab's keys (the tk
# shell does this in QCS_App). The port shipped without it and the two modules
# each wrote the WHOLE file from their own copy, so whichever saved LAST
# silently reverted everything the other had written that session - this is why
# 'nothing persisted between sessions' (v12.2).
qm.USER_PREFS = dbv.USER_PREFS

# QCS_Main/QCS_DatabaseView install the TK crash handler at import (it pops a
# tk dialog that never shows in a Qt app, and a crash then looks like a hang).
# Claim the hook for Qt as soon as this module is imported - main() is too
# late for anything that runs the shell without it (drivers, tests).
qtheme.install_crash_handler('QCS %s' % data.QCS_VERSION)


# The status bar's criteria indicator, in both wordings: the widget is sized
# for the wider of the two so it never changes width when it toggles.
CRITERIA_TEXTS = ('criteria: defaults', 'criteria: CUSTOM')

# What the greyed-out 'Data type' field says about itself. A disabled empty box
# reads as a fault; these say which instrument the field belongs to.
DATA_TYPE_HINTS = {
    'none': 'Select the instrument first',
    'HOBO': 'Not used for HOBO - a pendant logger is always a time series',
}

# Placeholder of the 'Recent' box, which is usable only while no file is
# selected (a selection would be silently replaced by the recent one).
RECENT_HINTS = {
    True: 'Select a recent file to open',
    False: 'Clear data file(s) to select a recent file',
}


class _UpdateBridge(QObject):
    """Marshals the background update check's result onto the Qt main thread
    (the tk shell used root.after for the same purpose)."""
    newer = Signal(dict)

TOOLTIPS = qm.TOOLTIPS             # single source: the real texts (v11.6.1)

_ICON_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'qcs_icon.png')


def _app_icon():
    return QIcon(_ICON_PATH) if os.path.isfile(_ICON_PATH) else QIcon()


def _interval_text(seconds):
    """'3600' -> '1 h', '1800' -> '30 min', '45' -> '45 s'."""
    if seconds % 3600 == 0:
        return '%d h' % (seconds // 3600)
    if seconds % 60 == 0:
        return '%d min' % (seconds // 60)
    return '%d s' % seconds


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


class ChooseVariablesDialog(QDialog):
    """Qt replacement for choose_variables_to_check: same contract - a list
    of chosen columns, [] = review nothing, None = cancel (abort the run)."""

    def __init__(self, candidates, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Check variables - choose which to review')
        self.resize(440, 560)
        v = QVBoxLayout(self)
        v.addWidget(QLabel('Select the variables to review and cut manually:'))
        inner = QWidget()
        iv = QVBoxLayout(inner)
        self._boxes = {}
        for name in candidates:
            cb = QCheckBox(name, checked=True)
            iv.addWidget(cb)
            self._boxes[name] = cb
        iv.addStretch()
        area = QScrollArea()
        area.setWidgetResizable(True)
        area.setWidget(inner)
        v.addWidget(area)
        toggles = QHBoxLayout()
        all_btn = QPushButton('All variables')
        all_btn.clicked.connect(lambda: [cb.setChecked(True) for cb in self._boxes.values()])
        none_btn = QPushButton('None')
        none_btn.clicked.connect(lambda: [cb.setChecked(False) for cb in self._boxes.values()])
        toggles.addWidget(all_btn)
        toggles.addWidget(none_btn)
        toggles.addStretch()
        v.addLayout(toggles)
        actions = QHBoxLayout()
        actions.addStretch()
        review = QPushButton('Review selected')
        review.setDefault(True)
        review.clicked.connect(self.accept)
        cancel = QPushButton('Cancel')
        cancel.clicked.connect(self.reject)   # Esc and the window X reject too
        actions.addWidget(review)
        actions.addWidget(cancel)
        v.addLayout(actions)

    def chosen(self):
        return [n for n, cb in self._boxes.items() if cb.isChecked()]


def qt_choose_variables(candidates, root=None):
    dlg = ChooseVariablesDialog(candidates)
    dlg.setWindowIcon(_app_icon())
    return dlg.chosen() if dlg.exec() == QDialog.DialogCode.Accepted else None


class QtShell(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('QCS - Quality Control System (SAGE)  -  %s'
                            % data.QCS_VERSION)
        self.setWindowIcon(_app_icon())
        self.resize(1180, 760)
        self.setAcceptDrops(True)   # Qt-native drag-and-drop, whole window
        # ...but the fields and buttons cover most of the window, and a
        # QLineEdit/QTextEdit/QComboBox handles drops ITSELF (it would paste
        # the path as text instead of loading the file). An application-wide
        # filter takes file drops before they get there - the Qt answer to
        # the v11.5 'register every widget' fix (v12.1)
        QApplication.instance().installEventFilter(self)
        self._last_seaguard = {}    # Data type/GMT stored while HOBO is selected
        self._co2_file = ''
        self._run_scope = None      # 'File k/n' / 'Replicate k/n' progress prefix

        tabs = QTabWidget()
        # every page is wrapped: a page that cannot shrink caps how far the
        # Execution log can be dragged open (see qtheme.scrollable)
        tabs.addTab(qtheme.scrollable(self._qualification_tab()),
                    'Data qualification')
        self.viz_tab = None               # attached by main() after the bootstrap
        self._viz_page = None             # the scroll area that holds viz_tab
        self._viz_placeholder = QWidget()
        tabs.addTab(self._viz_placeholder, 'Data visualization')
        tabs.currentChanged.connect(self._tab_changed)
        tabs.tabBar().setObjectName('MainTabs')   # scoped pastel tab styling
        self.tabs = tabs
        self.setCentralWidget(tabs)

        self.log_dock = qtheme.LogDock(self)
        self.log_dock.setObjectName('LogDock')   # saveState skips unnamed docks
        self.addDockWidget(Qt.BottomDockWidgetArea, self.log_dock)
        # batch status: one row per file of a Seaguard batch, filled from the
        # pipeline's own markers (hidden outside batches). Built BEFORE the
        # menus: View lists its toggle action.
        self.batch_table = QTableWidget(0, 2)
        self.batch_table.setHorizontalHeaderLabels(['File', 'Status'])
        self.batch_table.horizontalHeader().setStretchLastSection(True)
        self.batch_table.setColumnWidth(0, 320)
        self.batch_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        # smooth (per-pixel) horizontal scrolling: the default per-item mode
        # jumps a whole column and reads as a truncated scrollbar
        self.batch_table.setHorizontalScrollMode(
            QTableWidget.ScrollMode.ScrollPerPixel)
        self.batch_table.setVerticalScrollMode(
            QTableWidget.ScrollMode.ScrollPerPixel)
        self.batch_table.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        # the dock's content starts at the tab PAGE's top, so the table lines
        # up with the boxes beside it instead of floating above them
        batch_holder = QWidget()
        self._batch_layout = QVBoxLayout(batch_holder)
        self._batch_layout.setContentsMargins(0, 0, 0, 0)
        self._batch_layout.addWidget(self.batch_table)
        self.batch_dock = QDockWidget('Batch status', self)
        self.batch_dock.setObjectName('BatchDock')
        self.batch_dock.setWidget(batch_holder)
        self.addDockWidget(Qt.RightDockWidgetArea, self.batch_dock)
        self.batch_dock.hide()
        qtheme.dock_tooltips(
            self.batch_dock,
            'Detaches the batch status into its own window (drag it back to re-dock)',
            'Hides the batch status; View > Batch status brings it back')
        self._batch_rows = {}
        self._menus()
        # no size grip: it reserved a ~24 px strip that pushed the criteria
        # indicator out of line with the log's Clear button (the window edges
        # and corners still resize normally)
        self.statusBar().setSizeGripEnabled(False)
        # Permanent status widgets, left to right: progress, criteria
        # indicator, alignment spacer. The progress bar comes FIRST so that
        # showing it during a run cannot shift the indicator sideways.
        #
        # pipeline progress: indeterminate while a single run is busy, and a
        # real fraction on the batch/replicate markers the pipeline already
        # logs ('=== File k/n ===' / '=== Replicate k/n ===')
        self.progress = QProgressBar()
        self.progress.setFixedWidth(220)
        self.progress.setVisible(False)
        self.statusBar().addPermanentWidget(self.progress)
        # criteria indicator: at a glance, are the quality criteria the
        # software defaults or operator-edited? (owner request, 2026-08-17)
        self.criteria_label = QLabel('')
        # the indicator shares its width with the log's 'Clear log' button so
        # the two line up on one axis (see _align_clear_button)
        self.statusBar().addPermanentWidget(self.criteria_label)

    def _criteria_width(self):
        """How wide the indicator must be to hold its text.

        Measured from the TEXT, and from the WIDER of the two wordings: a
        QLabel's sizeHint stops growing once setFixedWidth has been applied, so
        sizing from the hint left 'criteria: CUSTOM' clipped at both ends
        (owner, 2026-08-19), and measuring only the current text made the
        widget jump sideways whenever the indicator changed."""
        fm = self.criteria_label.fontMetrics()
        return max(fm.horizontalAdvance(t) for t in CRITERIA_TEXTS) + 18

    def _align_clear_button(self):
        """Puts 'Clear log' on the same vertical axis as the status bar's
        criteria indicator right below it (owner)."""
        if self.log_dock.isFloating() or not self.log_dock.isVisible():
            # nothing to line up with, but the indicator must still fit: this
            # early return used to leave it at whatever width it had
            needed = self._criteria_width()
            if self.criteria_label.width() != needed:
                self.criteria_label.setFixedWidth(needed)
                self.criteria_label.setAlignment(Qt.AlignCenter)
            return
        # Both sit flush against the right edge, so equal WIDTHS put them on
        # the same axis - deterministic, unlike nudging margins (the widths
        # differ by theme, text and DPI, so they are measured, not hardcoded).
        btn = self.log_dock.clear_button
        label = self.criteria_label
        width = max(btn.sizeHint().width(), self._criteria_width())
        if btn.width() != width or label.width() != width:
            btn.setFixedWidth(width)
            label.setFixedWidth(width)
            label.setAlignment(Qt.AlignCenter)
        # Equal widths are not enough on their own: the two live in different
        # containers (a dock and the status bar), and the dock does not always
        # span the whole window - the batch dock takes the right side during a
        # batch. So the button gets a fixed inset and the status bar's right
        # margin is then MEASURED against it, which lands the two right edges
        # on the same pixel whatever the dock is doing (owner, 2026-08-19).
        inset = 12
        if self.log_dock.button_row.contentsMargins().right() != inset:
            self.log_dock.button_row.setContentsMargins(0, 0, inset, 0)
        bar = self.statusBar()
        margins = bar.contentsMargins()
        delta = (label.mapTo(self, label.rect().topRight()).x()
                 - btn.mapTo(self, btn.rect().topRight()).x())
        if delta:
            right = min(400, max(0, margins.right() + delta))
            if right != margins.right():
                bar.setContentsMargins(6, 0, right, margins.bottom())

    def _align_batch_top(self):
        """Top margin that puts the batch table's top on the tab page's top
        (the dock title bar sits higher than the tab bar's baseline)."""
        if not self.batch_dock.isVisible() or self.batch_dock.isFloating():
            return
        bar = self.tabs.tabBar()
        page_top = bar.mapTo(self, bar.rect().bottomLeft()).y()
        table_top = self.batch_table.mapTo(self, self.batch_table.rect().topLeft()).y()
        current = self._batch_layout.contentsMargins().top()
        delta = page_top - table_top + current
        if delta >= 0 and delta != current:
            self._batch_layout.setContentsMargins(0, delta, 0, 0)

    def showEvent(self, event):
        super().showEvent(event)
        self._align_batch_top()
        self._align_clear_button()

    def closeEvent(self, event):
        """The window remembers how it was left, and so does the form: the tk
        shell saved on exit (QCS_App.remember_window_state) and the port had no
        closeEvent at all, so every session reopened at the default size
        (v12.2)."""
        try:
            self.remember_window_state()
        except Exception as e:
            print('Warning: could not save the window state: %s' % e)
        super().closeEvent(event)

    def remember_window_state(self):
        """Window geometry, dock layout, log visibility and the form itself.
        saveGeometry() already carries the maximized flag, so there is no
        separate win_state key on this side; the tk shell's own win_state /
        win_geometry are left untouched (different format, other shell)."""
        p = qm.USER_PREFS
        p['qt_win_geometry'] = bytes(self.saveGeometry().toBase64()).decode('ascii')
        p['qt_win_layout'] = bytes(self.saveState().toBase64()).decode('ascii')
        p['log_hidden'] = not self.log_dock.isVisible()
        # the form was only ever stored by a successful RUN (inside
        # apply_input_settings): anything selected and not run was lost
        qm.store_form_prefs(self._form_vals())   # writes the settings file

    def restore_window_state(self):
        """Reopens the window the way it was left. Called before show(), so
        the restored geometry is the one the window is first mapped with."""
        p = qm.USER_PREFS
        geo = p.get('qt_win_geometry')
        if geo:
            self.restoreGeometry(QByteArray.fromBase64(geo.encode('ascii')))
        layout = p.get('qt_win_layout')
        if layout:
            self.restoreState(QByteArray.fromBase64(layout.encode('ascii')))
        # the batch table is filled by the pipeline's own markers and starts
        # empty, so a restored layout must never bring it back on its own
        self.batch_dock.hide()
        self.log_dock.setVisible(not p.get('log_hidden', False))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._align_batch_top()
        self._align_clear_button()

    def update_criteria_indicator(self):
        d = qm.DEFAULT_QUALITY_CONFIG
        default = (qm.CONFIG['tsQualityTests'] == d['tsQualityTests']
                   and qm.CONFIG['tsSettings'] == d['tsSettings']
                   and {k: dict(v) for k, v in qm.CONFIG['tsFactors'].items()}
                   == d['tsFactors'])
        self.criteria_label.setText(CRITERIA_TEXTS[0] if default
                                    else CRITERIA_TEXTS[1])
        self._align_clear_button()      # 'CUSTOM' is the wider of the two
        self.criteria_label.setToolTip(
            'The quality criteria are the software defaults' if default else
            'At least one quality criterion differs from the defaults\n'
            '(the edited fields show in bold in Quality control settings)')

    # ----- logging -----
    def log_line(self, message):
        # the pipeline's own markers drive the progress bar: every run logs
        # 'Stage k/5', and batches/replicates scope it with '=== File k/n ==='
        # / '=== Replicate k/n ==='. Progress is CONTINUOUS across the whole
        # run: file k of n at stage s sits at (k-1)*5 + s out of n*5, so
        # finishing the first of two replicates reads 50%, not a reset.
        msg = message.strip()
        m = re.match(r'=== (File|Replicate) (\d+)/(\d+): (.+?) ===', msg)
        if m:
            kind, k, n = m.group(1), int(m.group(2)), int(m.group(3))
            self._run_scope = (kind, k, n)
            self.progress.setRange(0, n * 5)
            self.progress.setValue((k - 1) * 5)
            self.progress.setFormat('%s %d/%d' % (kind, k, n))
            if kind == 'File':
                self._batch_mark(m.group(4), k, n)
        fail = re.match(r'File (.+?) could not be qualified', msg)
        if fail and fail.group(1) in self._batch_rows:
            row = self._batch_rows[fail.group(1)]
            self.batch_table.setItem(row, 1, QTableWidgetItem('FAILED (see log)'))
        else:
            s = re.match(r'Stage (\d)/5', msg)
            if s:
                stage = int(s.group(1))
                if self._run_scope:
                    kind, k, n = self._run_scope
                    self.progress.setRange(0, n * 5)
                    self.progress.setValue((k - 1) * 5 + stage)
                    self.progress.setFormat('%s %d/%d - Stage %d/5'
                                            % (kind, k, n, stage))
                else:
                    self.progress.setRange(0, 5)
                    self.progress.setValue(stage)
                    self.progress.setFormat('Stage %d/5' % stage)
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

        # Recent selections, right under the files row and usable only while
        # NO file is selected - the same rule as the Visualization tab
        self.recent = QComboBox()
        self.recent.setPlaceholderText(RECENT_HINTS[True])
        self.recent.setToolTip('Reopens one of the most recent file selections\n'
                               '(available while no file is selected above)')
        self.recent.activated.connect(self._apply_recent)
        fin.addRow('Recent:', self.recent)

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
        # the field is greyed out for HOBO and while no instrument is chosen:
        # the placeholder says WHY, instead of leaving an empty grey box
        # (owner, 2026-08-19). Qt shows it whenever currentIndex is -1.
        self.data_type.setPlaceholderText(DATA_TYPE_HINTS['none'])
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
        self.gmt_check.toggled.connect(lambda _on: self._sync_timebase_row())
        vo.addWidget(self.gmt_check)
        self.profile_check = QCheckBox('Select profile data')
        self.profile_check.setToolTip(TOOLTIPS['profile_selection'])
        vo.addWidget(self.profile_check)
        self.varcheck = QCheckBox('Check variables')
        self.varcheck.setToolTip(TOOLTIPS['variable_check'])
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
        # Order and defaults are the owner's (2026-08-19): dismissed first,
        # because dropping the rows a review cut is the routine choice, and it
        # and 'bad' start CHECKED. These are OUTPUT filters, not QC criteria -
        # they change what the sheet carries, never a flag, so the status bar's
        # criteria indicator is untouched by them.
        self.remove_dismissed = QCheckBox('Remove dismissed data', checked=True)
        self.remove_dismissed.setToolTip(TOOLTIPS['remove_dismissed'])
        vf.addWidget(self.remove_dismissed)
        self.remove_bad = QCheckBox('Remove bad data', checked=True)
        self.remove_bad.setToolTip(TOOLTIPS['remove_bad'])
        vf.addWidget(self.remove_bad)
        self.remove_suspect = QCheckBox('Remove suspect data')
        self.remove_suspect.setToolTip(TOOLTIPS['remove_suspect'])
        vf.addWidget(self.remove_suspect)
        fout.addRow(gfil)

        gsum = QGroupBox('Selection summary')
        gsum.setToolTip(TOOLTIPS.get('summary', ''))
        fsum = QFormLayout(gsum)
        self.sum_labels = {}
        for key, label in (('instrument', 'Instrument:'), ('files', 'Files:'),
                           ('mode', 'Mode:'), ('period', 'Period:'),
                           ('interval', 'Interval:'), ('serials', 'Serial(s):'),
                           ('co2', 'CO₂ data:'), ('timebase', 'Timebase:')):
            lab = QLabel('-')
            qtheme.muted(lab)
            # the CO2 line is the long one (file, readings, period): it wraps
            # instead of widening the whole Output column
            lab.setWordWrap(key == 'co2')
            self.sum_labels[key] = lab
            fsum.addRow(label, lab)
        self._fsum = fsum          # the CO2 row is hidden for HOBO/Doppler
        fout.addRow(gsum)

        self.run_btn = QPushButton('Run qualification')
        self.run_btn.setDefault(True)
        self.run_btn.setMinimumSize(260, 42)
        f = self.run_btn.font()
        f.setBold(True)
        f.setPointSizeF(f.pointSizeF() + 1)
        self.run_btn.setFont(f)
        self.run_btn.setObjectName('AccentButton')   # blue primary action
        self.run_btn.setToolTip(TOOLTIPS['run_button'])
        self.run_btn.clicked.connect(self._run)
        self.run_hint = QLabel('')
        qtheme.muted(self.run_hint)
        settings = QPushButton('Quality control settings')
        settings.setToolTip(TOOLTIPS['settings_button'])
        settings.clicked.connect(self._open_settings)

        grid.addWidget(gin, 0, 0)
        grid.addWidget(gout, 0, 1)
        actions = QGridLayout()
        for col in range(3):
            actions.setColumnStretch(col, 1)
        # ordinary button height, but vertically centered on the RUN button -
        # not on the run box, which also holds the hint and the post-run
        # shortcuts below it (owner)
        settings_box = QWidget()
        sv = QVBoxLayout(settings_box)
        pad = max(0, (self.run_btn.minimumHeight()
                      - settings.sizeHint().height()) // 2)
        sv.setContentsMargins(0, pad, 0, 0)
        sv.addWidget(settings)
        sv.addStretch()
        actions.addWidget(settings_box, 0, 0, Qt.AlignLeft | Qt.AlignTop)
        # after a successful run: the two things the operator does next
        # (owner request) - the log line with the path stays, this is a
        # shortcut, not a replacement
        self.postrun_bar = QWidget()
        pr = QHBoxLayout(self.postrun_bar)
        pr.setContentsMargins(0, 0, 0, 0)
        open_out = QPushButton('Open output folder')
        open_out.clicked.connect(self._open_output_folder)
        to_viz = QPushButton('Go to visualization')
        to_viz.clicked.connect(
            lambda: self.tabs.setCurrentIndex(self.tabs.count() - 1))
        pr.addWidget(open_out)
        pr.addWidget(to_viz)
        self.postrun_bar.setVisible(False)

        run_box = QVBoxLayout()
        run_box.setContentsMargins(0, 0, 0, 0)
        run_box.setSpacing(4)   # the shortcuts hug RUN (owner, v12.1)
        run_box.addWidget(self.run_btn, alignment=Qt.AlignHCenter)
        run_box.addWidget(self.run_hint, alignment=Qt.AlignHCenter)
        run_box.addWidget(self.postrun_bar, alignment=Qt.AlignHCenter)
        rb = QWidget()
        rb.setLayout(run_box)
        actions.addWidget(rb, 0, 1, Qt.AlignHCenter)
        ah = QWidget()
        ah.setLayout(actions)
        grid.addWidget(ah, 1, 0, 1, 2)
        grid.setRowStretch(0, 1)
        qtheme.bold_form_labels(fin)
        qtheme.bold_form_labels(fout)
        qtheme.bold_form_labels(fsum)
        self._input_type_changed(self.input_type.currentText())
        self._update_run_state()
        return w

    def attach_visualization_tab(self):
        """Called by main() once the hidden tk pipeline (which the tab remote-
        controls) exists."""
        self.viz_tab = VisualizationTab(self)
        self._viz_page = qtheme.scrollable(self.viz_tab)
        idx = self.tabs.indexOf(self._viz_placeholder)
        self.tabs.removeTab(idx)
        self.tabs.insertTab(idx, self._viz_page, 'Data visualization')

    def _tab_changed(self, _index):
        # hand a just-qualified file to the Visualization tab, exactly like
        # the tk shell does on its tab switch
        if (self.viz_tab is not None
                and self.tabs.currentWidget() is self._viz_page
                and qm.PENDING_VIZ_PREFILL):
            self.viz_tab.apply_prefill(qm.PENDING_VIZ_PREFILL)
            qm.PENDING_VIZ_PREFILL = None
        # every switch starts at the top of the page, never wherever the tab
        # was left (owner, 2026-08-19)
        page = self.tabs.currentWidget()
        if isinstance(page, QScrollArea):
            qtheme.scroll_to_top(page.widget() or page)

    def _menus(self):
        # File carries the file-level actions of the active workflow, so the
        # keyboard reaches what the buttons do (owner asked what belongs here:
        # selection, output folder, settings, exit)
        mb = self.menuBar()
        filem = mb.addMenu('File')
        act_open = QAction('Select data file(s)...', self)
        act_open.setShortcut('Ctrl+O')
        act_open.triggered.connect(self._browse)
        filem.addAction(act_open)
        act_co2 = QAction('Add CO₂ data...', self)
        act_co2.triggered.connect(self._select_co2)
        filem.addAction(act_co2)
        act_outdir = QAction('Select output folder...', self)
        act_outdir.triggered.connect(self._browse_output)
        filem.addAction(act_outdir)
        filem.addSeparator()
        act_showout = QAction('Open output folder', self)
        act_showout.triggered.connect(self._open_output_folder)
        filem.addAction(act_showout)
        act_settings = QAction('Quality control settings...', self)
        act_settings.triggered.connect(self._open_settings)
        filem.addAction(act_settings)
        filem.addSeparator()
        act_exit = QAction('Exit', self)
        act_exit.setShortcut('Ctrl+Q')
        act_exit.triggered.connect(self.close)
        filem.addAction(act_exit)

        view = mb.addMenu('View')
        self.dark_action = QAction('Dark mode', self, checkable=True)
        self.dark_action.triggered.connect(self._toggle_dark)
        view.addAction(self.dark_action)
        view.addSeparator()
        view.addAction(self.log_dock.toggleViewAction())
        view.addAction(self.batch_dock.toggleViewAction())

        helpm = mb.addMenu('Help')
        manual = QAction('User manual', self)
        manual.triggered.connect(self._open_manual)
        helpm.addAction(manual)
        updates = QAction('Check for updates', self)
        updates.triggered.connect(self.check_for_updates)
        helpm.addAction(updates)
        about = QAction('About', self)
        about.triggered.connect(lambda: QMessageBox.information(
            self, 'QCS', 'QCS - Quality Control System %s\n'
            'Quality control of oceanographic sensor data (SAGE / COPPE-UFRJ).'
            % data.QCS_VERSION))
        helpm.addAction(about)

    # ----- update check (the network parts are shared with the tk shell) -----
    def check_for_updates(self):
        """Help > Check for updates: reports EVERY outcome (unlike the silent
        startup check)."""
        self.log_line('Info: checking for updates...')
        QApplication.processEvents()
        try:
            latest = upd.fetch_latest()
        except Exception as exc:
            QMessageBox.warning(self, 'Check for updates',
                                'The update check failed: %s' % upd.describe_error(exc))
            return
        if latest and upd.is_newer(latest['tag'], data.QCS_VERSION):
            self.offer_update(latest)
        else:
            QMessageBox.information(
                self, 'Check for updates',
                'QCS %s is the latest version.' % data.QCS_VERSION)

    def start_background_update_check(self):
        """Startup path: silent on every outcome except a newer release."""
        self._update_bridge = _UpdateBridge()
        self._update_bridge.newer.connect(self.offer_update)
        upd.check_in_background(data.QCS_VERSION, self._update_bridge.newer.emit)

    def offer_update(self, latest):
        size = (' (~%.0f MB)' % latest['size_mb']) if latest.get('size_mb') else ''
        answer = QMessageBox.question(
            self, 'Update available',
            'QCS %s is available - you are running %s.\n\n'
            'Download and install it now%s? The program closes and the '
            'installer opens; keep "Launch QCS after installation" ticked on '
            'its last page to come back updated. Your settings and '
            'preferences are kept.'
            % (latest['tag'], data.QCS_VERSION, size))
        if answer != QMessageBox.StandardButton.Yes:
            return
        if self._download_and_run(latest):
            self.close()

    def _download_and_run(self, latest):
        """Qt version of QCS_Update.download_and_run (that one builds a tk
        progress window): same contract - True when the installer started."""
        import subprocess
        import tempfile
        import urllib.request
        import webbrowser
        if not latest.get('setup_url'):
            webbrowser.open(upd.RELEASES_PAGE)      # release without an asset
            return False
        dest = os.path.join(tempfile.gettempdir(), latest['setup_name'])
        dlg = QProgressDialog('Downloading %s (%.0f MB)...'
                              % (latest['setup_name'], latest['size_mb'] or 0),
                              'Cancel', 0, 100, self)
        dlg.setWindowTitle('Downloading %s' % latest['tag'])
        dlg.setWindowModality(Qt.WindowModal)
        dlg.setValue(0)
        try:
            req = urllib.request.Request(latest['setup_url'], headers=upd._HEADERS)
            with urllib.request.urlopen(req, timeout=30,
                                        context=upd.ssl_context()) as resp, \
                    open(dest, 'wb') as f:
                total = int(resp.headers.get('Content-Length') or 0)
                got = 0
                while True:
                    if dlg.wasCanceled():
                        self.log_line('Info: update download canceled.')
                        return False
                    chunk = resp.read(1 << 16)
                    if not chunk:
                        break
                    f.write(chunk)
                    got += len(chunk)
                    if total:
                        dlg.setValue(int(100 * got / total))
                    QApplication.processEvents()
            if total and got != total:
                raise OSError('incomplete download: %d of %d bytes' % (got, total))
        except Exception as exc:
            dlg.close()
            QMessageBox.warning(
                self, 'Update download failed',
                'The installer could not be downloaded: %s\n\nThe release page '
                'will open in the browser instead.' % upd.describe_error(exc))
            webbrowser.open(upd.RELEASES_PAGE)
            return False
        dlg.close()
        # the wizard runs VISIBLY so its finish page can offer 'Launch QCS
        # after installation' - see QCS_Update.download_and_run for why the
        # silent path was abandoned
        log_path = upd.install_log_path()
        self.log_line('Info: installing the update; the installer log goes to %s' % log_path)
        subprocess.Popen([dest, '/NORESTART', '/LOG=%s' % log_path])
        return True

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
        self.update_criteria_indicator()   # the edit may have left the defaults

    # ----- drag-and-drop (Qt-native: one handler pair for the whole window) -----
    @staticmethod
    def _dropped_files(event):
        """Local file paths of a drag, or [] when it carries something else
        (dragged text, a URL from a browser)."""
        if not event.mimeData().hasUrls():
            return []
        return [u.toLocalFile() for u in event.mimeData().urls()
                if u.isLocalFile()]

    def dragEnterEvent(self, event):
        if self._dropped_files(event):
            event.acceptProposedAction()

    def dropEvent(self, event):
        self._take_dropped_files(self._dropped_files(event))

    def _take_dropped_files(self, paths):
        if not paths:
            return
        # drops land in the ACTIVE tab's file field, like the tk shell
        if self.viz_tab is not None and self.tabs.currentWidget() is self._viz_page:
            self.viz_tab.apply_selected_files(paths)
        else:
            self.apply_selected_files(paths)

    def eventFilter(self, obj, event):
        """File drops belong to the shell wherever they land: over a field,
        a button or the log, a widget that handles drops itself would swallow
        them (v12.1). Only drags carrying FILES are taken - dragging text
        inside a field still behaves normally."""
        kind = event.type()
        if kind in (QEvent.Type.DragEnter, QEvent.Type.DragMove,
                    QEvent.Type.Drop) and isinstance(obj, QWidget):
            if obj.window() is self and self._dropped_files(event):
                event.acceptProposedAction()
                if kind == QEvent.Type.Drop:
                    self._take_dropped_files(self._dropped_files(event))
                return True
        return super().eventFilter(obj, event)

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
        qm.remember_data_dir(first)
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
        qm.push_qual_recent(';'.join(names), self.input_type.currentText())
        self._refresh_recent()

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

    def _refresh_recent(self):
        with QSignalBlocker(self.recent):
            self.recent.clear()
            self.recent.addItems([qm.qual_recent_display(r)
                                  for r in qm.USER_PREFS.get('qual_recent', [])])
            self.recent.setCurrentIndex(-1)
        usable = not self.file_edit.text().strip()
        self.recent.setEnabled(usable)
        # greyed out, the box has to say what makes it usable again (owner)
        self.recent.setPlaceholderText(RECENT_HINTS[usable])

    def _apply_recent(self, index):
        recents = qm.USER_PREFS.get('qual_recent', [])
        if 0 <= index < len(recents):
            files = [p for p in recents[index]['files'].split(';') if p.strip()]
            existing = [f for f in files if os.path.isfile(f)]
            if not existing:
                QMessageBox.warning(self, 'Recent selection',
                                    'None of those files exist any more:\n\n%s'
                                    % '\n'.join(files))
                return
            if len(existing) < len(files):
                self.log_line('Warning: %d file(s) of that recent selection no '
                              'longer exist and were skipped.'
                              % (len(files) - len(existing)))
            self.apply_selected_files(existing)

    def _open_output_folder(self):
        root = qm.OUTPUT.get('last_output_root') or self.out_folder.text().strip()
        if root and os.path.isdir(root):
            os.startfile(root)
        else:
            QMessageBox.warning(self, 'Output folder',
                                'The output folder no longer exists:\n%s' % root)

    def _co2_applies(self):
        """CO2 is an addition to a SEAGUARD scalar run: no CO2 logger goes with
        a HOBO pendant or a current profiler, so the row does not belong in
        their summary at all (owner, v12.2)."""
        return (self.input_type.currentText() == 'Seaguard'
                and self.data_type.currentText() != 'TSCP Doppler')

    def _sync_co2_row(self):
        self._fsum.setRowVisible(self.sum_labels['co2'], self._co2_applies())

    def _update_summary(self, names):
        itype = self.input_type.currentText()
        self._sync_co2_row()
        for lab in self.sum_labels.values():
            lab.setText('-')
        self.sum_labels['instrument'].setText(itype or '-')
        self.sum_labels['files'].setText(
            '%d  (%s%s)' % (len(names), os.path.basename(names[0]),
                            ', ...' if len(names) > 1 else ''))
        # raw .hobo: the header is a 1 KB read, so the summary can state what
        # the logger itself recorded before anything is qualified (v12.0)
        heads = [data.peek_hobo_header(f) for f in names
                 if f.lower().endswith('.hobo')]
        heads = [h for h in heads if h]
        if heads:
            models = {h['model'] for h in heads if h['model']}
            if models:
                self.sum_labels['instrument'].setText('%s  (%s)'
                                                      % (itype, ', '.join(sorted(models))))
            serials = [h['serial'] for h in heads if h['serial']]
            if serials:
                self.sum_labels['serials'].setText(', '.join(serials))
            intervals = {h['interval_s'] for h in heads if h['interval_s']}
            if intervals:
                text = ', '.join(_interval_text(s) for s in sorted(intervals))
                if len(intervals) > 1:
                    text += '   (differ - see the log warning)'
                self.sum_labels['interval'].setText(text)
            launches = [h['launch'] for h in heads if h['launch'] is not None]
            if launches:
                self.sum_labels['period'].setText(
                    'launched %s' % min(launches).strftime('%d/%m/%Y %H:%M'))
        # Seaguard says as much about itself in its FOLDER NAMES as the .hobo
        # header does: serial, deployment start, how many sensor groups the
        # cast has and how many binary parts the group was split into. All of
        # it is a listdir - decoding the session to preview it would freeze
        # the window (v12.1)
        peek = (data.peek_seaguard_session(names[0])
                if itype in ('Seaguard', 'Doppler') else {})
        if peek:
            self.sum_labels['serials'].setText(peek['serial'])
            self.sum_labels['period'].setText(
                'logging started %s' % peek['start'].strftime('%d/%m/%Y %H:%M'))
            if peek.get('interval_s'):
                # the FINEST sensor group's interval: that is the axis the
                # deployment is merged onto, so it is the one the qualified
                # sheet will carry
                self.sum_labels['interval'].setText(
                    _interval_text(peek['interval_s']))
        if itype == 'HOBO':
            mode = ('%d replicates of one deployment, combined' % len(names)
                    if len(names) > 1 else 'single logger')
        else:
            mode = ('batch: %d files qualified in sequence' % len(names)
                    if len(names) > 1 else
                    ('current profiler (DCPS)'
                     if self.data_type.currentText() == 'TSCP Doppler'
                     else 'single deployment'))
            if peek and peek.get('groups', 1) > 1 and len(names) == 1:
                mode += ', %d sensor groups merged' % peek['groups']
            if peek and peek.get('parts', 1) > 1 and len(names) == 1:
                mode += ' (%d binary parts)' % peek['parts']
            self._summarize_co2()
        self.sum_labels['mode'].setText(mode)
        self._sync_timebase_row()

    def _sync_timebase_row(self):
        """The Timebase line follows the 'Correct GMT-3' box, which the owner
        can untick after the summary was built (2026-08-19). A Seaguard run
        with the correction OFF keeps GMT, and the summary must say so - it is
        the one setting that silently shifts a whole deployment."""
        if not hasattr(self, 'sum_labels'):
            return          # the box is built before the summary rows exist
        if self.input_type.currentText() == 'HOBO':
            text = 'local (HOBO) - GMT-3 correction not applied'
        elif self.gmt_check.isChecked():
            text = 'GMT (Seaguard) -> corrected to local (GMT-3)'
        else:
            text = 'GMT (Seaguard) - NOT corrected: the output stays on GMT'
        self.sum_labels['timebase'].setText(text)

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
        self._sync_co2_row()
        if allowed and self.file_edit.text().strip():
            self._summarize_co2()   # the summary must follow the CO2 choice

    def _summarize_co2(self):
        """The CO2 addition in the Selection summary: what file, what period it
        covers and the reminder that its clock is LOCAL - the one timebase the
        GMT-3 correction must not touch (v12.1)."""
        if not self._co2_file:
            self.sum_labels['co2'].setText('none')
            return
        base = os.path.basename(self._co2_file)
        try:
            frame, _msgs = data.read_co2_file(self._co2_file)
            span = '%s to %s' % (frame['Datetime'].min().strftime('%d/%m/%Y %H:%M'),
                                 frame['Datetime'].max().strftime('%d/%m/%Y %H:%M'))
            self.sum_labels['co2'].setText(
                '%s  (%d readings, %s - local clock, interpolated onto the '
                'Seaguard times)' % (base, len(frame), span))
        except Exception as exc:
            self.sum_labels['co2'].setText('%s  (unreadable: %s)' % (base, exc))

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
            self.data_type.setPlaceholderText(DATA_TYPE_HINTS['HOBO'])
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
            if self.remove_dismissed.isEnabled():   # only a Seaguard state is
                self._last_seaguard['remove_dismissed'] = (  # worth remembering
                    self.remove_dismissed.isChecked())
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
            self.remove_dismissed.setChecked(
                self._last_seaguard.get('remove_dismissed', True))
        else:
            # no instrument selected ('Select instrument' placeholder): the
            # dependent fields wait for a selection
            if self.data_type.currentText():
                self._last_seaguard['data_type'] = self.data_type.currentText()
            self.data_type.setCurrentIndex(-1)
            self.data_type.setPlaceholderText(DATA_TYPE_HINTS['none'])
            self.data_type.setEnabled(False)
            self.gmt_check.setChecked(False)
            self.gmt_check.setEnabled(False)
            self._set_replicates('')
            self.light_adaptive.setEnabled(False)
            self.light_fixed.setEnabled(False)
            if self.remove_dismissed.isEnabled():   # only a Seaguard state is
                self._last_seaguard['remove_dismissed'] = (  # worth remembering
                    self.remove_dismissed.isChecked())
            self.remove_dismissed.setChecked(False)
            self.remove_dismissed.setEnabled(False)
        self._update_profile_state()
        self._apply_output_name()
        self._update_co2_controls()

    def _update_profile_state(self):
        # 'Select profile data' applies to profiles only (port of
        # update_profile_checkbox_state)
        is_profile = self.data_type.currentText() == 'TSCP Profile'
        self.profile_check.setEnabled(is_profile)
        if not is_profile:
            self.profile_check.setChecked(False)

    # ----- run -----
    def _file_text_changed(self, text):
        if not text.strip():
            # selection cleared: back to 'Select instrument', editable, and
            # the Replicates line and summary go away with it
            self.input_type.setEnabled(True)
            self.input_type.setCurrentIndex(-1)
            for lab in self.sum_labels.values():
                lab.setText('-')
        self.recent.setEnabled(not text.strip())
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
        # an empty hint keeps a whole line of height, which pushed the
        # post-run shortcuts away from RUN (owner, v12.1)
        self.run_hint.setVisible(bool(missing))

    def _form_vals(self):
        """The vals dict the pipeline expects (QCS_Main.read_input_widgets is
        the tk half). Read-only: the close path persists the form through it."""
        return {
            'files_raw': self.file_edit.text(),
            'input_type': self.input_type.currentText(),
            'data_type': self.data_type.currentText(),
            'out_dir': self.out_folder.text(),
            'out_name': self.out_name.text(),
            'out_format': self.out_format.currentText(),
            'correct_gmt3h': self.gmt_check.isChecked(),
            'select_profile_data': self.profile_check.isChecked(),
            'check_variables': self.varcheck.isChecked(),
            'remove_bad': self.remove_bad.isChecked(),
            'remove_suspect': self.remove_suspect.isChecked(),
            'remove_dismissed': self.remove_dismissed.isChecked(),
            'co2_file': self._co2_file,
            'site': self.site_edit.text(),
            'macroregion': self.macroregion.currentText(),
            'region': self.region.currentText(),
            'light_cutoff_mode': 'fixed' if self.light_fixed.isChecked() else 'adaptive',
        }

    def collect_from_qt(self):
        """Qt replacement for QCS_Main.collect_input_settings: same vals dict,
        same toolkit-free validation."""
        vals = self._form_vals()
        if vals['input_type'] == 'HOBO' and vals['files_raw'].strip():
            n = len([p for p in vals['files_raw'].split(';') if p.strip()])
            self._set_replicates(str(n))
        return qm.apply_input_settings(vals)

    def _batch_mark(self, name, k, n):
        """Batch table: file k of n starts. The previous file, unless already
        FAILED, is done - a batch only advances past a finished file."""
        if k == 1:
            self.batch_table.setRowCount(n)
            self._batch_rows = {}
            self.batch_dock.show()
            self._align_batch_top()
        self._finish_running_batch_row()
        row = k - 1
        self._batch_rows[name] = row
        self.batch_table.setItem(row, 0, QTableWidgetItem(name))
        self.batch_table.setItem(row, 1, QTableWidgetItem('running...'))

    def _finish_running_batch_row(self):
        for row in range(self.batch_table.rowCount()):
            item = self.batch_table.item(row, 1)
            if item is not None and item.text() == 'running...':
                self.batch_table.setItem(row, 1, QTableWidgetItem('ok'))

    def set_busy(self, busy):
        self.run_btn.setEnabled(not busy)
        self.progress.setVisible(busy)
        if busy:
            self._run_scope = None
            self.batch_dock.hide()          # reappears on the first File marker
            self.batch_table.setRowCount(0)
            self._batch_rows = {}
            self.postrun_bar.setVisible(False)
            self.progress.setRange(0, 0)   # indeterminate until the first Stage marker
            # busy cursor on the MAIN window only (like the tk watch cursor):
            # an app-wide override cursor kept spinning over the interactive
            # review windows and dialogs, reading as a hang
            self.setCursor(Qt.WaitCursor)
        else:
            self.unsetCursor()
            self._finish_running_batch_row()
            self._update_run_state()
            # a run that produced an output offers the two next steps
            self.postrun_bar.setVisible(bool(qm.OUTPUT.get('last_output_root')))

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
        self.remove_bad.setChecked(bool(p.get('remove_bad', True)))
        self.remove_suspect.setChecked(bool(p.get('remove_suspect', False)))
        self._last_seaguard['remove_dismissed'] = bool(p.get('remove_dismissed', True))
        if self.remove_dismissed.isEnabled():   # HOBO keeps it off and grayed
            self.remove_dismissed.setChecked(self._last_seaguard['remove_dismissed'])
        if p.get('macroregion') in qm.REGIONS:
            self.macroregion.setCurrentText(p['macroregion'])
        regions = [r[0] for r in qm.REGIONS.get(self.macroregion.currentText(), [])]
        if p.get('region') in regions:
            self.region.setCurrentText(p['region'])
        if self.profile_check.isEnabled():
            self.profile_check.setChecked(bool(p.get('select_profile_data', False)))
        self.varcheck.setChecked(bool(p.get('check_variables', False)))
        # the Selection summary must survive a restart with the restored
        # selection (it only filled on Browse/drop before)
        files = [f for f in self.file_edit.text().split(';') if f.strip()]
        if files:
            self._update_summary(files)
            if self.input_type.currentText() == 'HOBO':
                self._set_replicates(str(len(files)))
        self._refresh_recent()
        self.update_criteria_indicator()
        self.restore_window_state()


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
    # the DatabaseView wizard too: its Step 1/2 stay the authoritative state
    # that the Qt Visualization tab remote-controls (see QCS_QtViz)
    viz_frame = qm.ttk.Frame(root)
    viz_frame.pack()
    dbv.build_visualization_tab(viz_frame, root, shared_log=shared_log)
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
    qm.choose_variables_to_check = qt_choose_variables
    qm.ui_ask_yes_no = lambda t, m: (QMessageBox.question(shell, t, m)
                                     == QMessageBox.StandardButton.Yes)
    qm.wait_figure_close = wait_figure_close
    data._show_and_wait = lambda fig, tk_root=None: wait_figure_close(fig)
    theme.style_plot_window = _qt_style_plot_window   # app icon on plot windows
    dbv.ui_info = lambda t, m: QMessageBox.information(shell, t, m)
    dbv.ui_warn = lambda t, m: QMessageBox.warning(shell, t, m)
    dbv.ui_error = lambda t, m: QMessageBox.critical(shell, t, m)


def main():
    app = QApplication(sys.argv)
    app.setWindowIcon(_app_icon())
    dark = qm.USER_PREFS.get('ui_theme') == 'dark'
    qtheme.apply_style(dark)
    shell = QtShell()
    shell.dark_action.setChecked(dark)
    _out.set_sink(shell.log_dock.log)      # prints -> Qt log from here on
    _bootstrap_tk_pipeline(shell.log_dock)  # also runs restore prefs + version gate
    _install_qt_facade(shell)
    shell.restore_prefs()
    shell.attach_visualization_tab()       # remote-controls the hidden wizard
    if '--shot' in sys.argv:
        # screenshot mode (no dialogs, window never shown): grab() renders the
        # laid-out widget with the real platform fonts/style
        out_path = sys.argv[sys.argv.index('--shot') + 1]
        app.processEvents()
        shell.grab().save(out_path)
        return 0
    shell.start_background_update_check()   # silent unless a newer release exists
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

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

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QColor, QPalette
from PySide6.QtWidgets import (QApplication, QCheckBox, QComboBox, QDockWidget,
                               QFileDialog, QFormLayout, QGridLayout,
                               QGroupBox, QHBoxLayout, QLabel, QLineEdit,
                               QMainWindow, QPushButton, QRadioButton,
                               QTabWidget, QTextEdit, QVBoxLayout, QWidget)

APP_TITLE = 'QCS v12.0 preview  -  choose the interface style in View > Interface style'


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
        for demo in ('Info: this is the Execution log (drag me, undock me, '
                     'close me - View menu brings me back).',
                     'Warning: warnings show in amber, like today.',
                     'Error: errors show in red.',
                     'Done: success shows in green.'):
            self.log_line(demo)

        self._menus()
        self.statusBar().showMessage('Preview only - no QC logic behind the buttons')

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
        self.file_edit = QLineEdit()
        b = QPushButton('Browse...')
        b.clicked.connect(self._browse)
        row.addWidget(self.file_edit)
        row.addWidget(b)
        row.addWidget(QPushButton('Add CO\u2082 data'))
        holder = QWidget()
        holder.setLayout(row)
        fin.addRow('Data file(s):', holder)
        typ = QComboBox()
        typ.addItems(['Seaguard', 'HOBO'])
        fin.addRow('Input type:', typ)
        dt = QComboBox()
        dt.addItems(['TSCP Profile', 'TSCP Mooring', 'TSCP Doppler'])
        fin.addRow('Data type:', dt)
        lm = QHBoxLayout()
        lm.setContentsMargins(0, 0, 0, 0)   # radios level with their label
        lm.addWidget(QRadioButton('Reviewed (adaptive)', checked=True))
        lm.addWidget(QRadioButton('Fixed window'))
        lm.addStretch()
        lmh = QWidget()
        lmh.setLayout(lm)
        fin.addRow('Light cutoff:', lmh)
        mac = QComboBox()
        mac.addItems(['Brazil'])
        fin.addRow('Macroregion:', mac)
        reg = QComboBox()
        reg.addItems(['Abrolhos (BA)'])
        fin.addRow('Region:', reg)
        # the three toggles LAST, boxed like Data filtering (owner request)
        gopt = QGroupBox('Options')
        vo = QVBoxLayout(gopt)
        vo.addWidget(QCheckBox('Correct GMT-3'))
        vo.addWidget(QCheckBox('Select profile data'))
        vo.addWidget(QCheckBox('Check variables'))
        fin.addRow(gopt)

        gout = QGroupBox('Output settings')
        fout = QFormLayout(gout)
        fout.addRow('Output folder:', QLineEdit())
        fout.addRow('Output file name:', QLineEdit())
        fmt = QComboBox()
        fmt.addItems(['.xlsx', '.csv'])
        fout.addRow('Output format:', fmt)
        fout.addRow('Site code:', QLineEdit())
        gfil = QGroupBox('Data filtering')
        vf = QVBoxLayout(gfil)
        vf.addWidget(QCheckBox('Remove bad data'))
        vf.addWidget(QCheckBox('Remove suspect data'))
        fout.addRow(gfil)

        # Parameter settings on the LEFT corner; Run qualification truly
        # CENTERED and in evidence (owner decisions, 2026-08-14)
        run = QPushButton('Run qualification')
        run.setDefault(True)
        run.setMinimumSize(260, 42)
        f = run.font()
        f.setBold(True)
        f.setPointSizeF(f.pointSizeF() + 1)
        run.setFont(f)
        run.clicked.connect(lambda: self.log.appendPlainText(
            'Info: (preview) this would run the real pipeline.'))
        settings = QPushButton('Parameter settings')

        grid.addWidget(gin, 0, 0)
        grid.addWidget(gout, 0, 1)
        actions = QGridLayout()
        actions.setColumnStretch(0, 1)
        actions.setColumnStretch(1, 1)
        actions.setColumnStretch(2, 1)
        actions.addWidget(settings, 0, 0, Qt.AlignLeft | Qt.AlignVCenter)
        actions.addWidget(run, 0, 1, Qt.AlignHCenter)
        ah = QWidget()
        ah.setLayout(actions)
        grid.addWidget(ah, 1, 0, 1, 2)
        grid.setRowStretch(0, 1)
        return w

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
            self.log.appendPlainText('Info: %d file(s) selected.' % len(names))

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
    # the log stands off the white/dark input fields (owner request)
    app.setStyleSheet('QTextEdit#ExecutionLog { background: %s; }'
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
        app.processEvents()
        win.grab().save(out)
        return 0
    win.show()
    return app.exec()


if __name__ == '__main__':
    sys.exit(main())

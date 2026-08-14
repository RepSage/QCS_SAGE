# -*- coding: utf-8 -*-
"""QCS v12.0 interface preview (PySide6/Qt) - NOT the real app.

Mocks the Data Qualification tab with the real widget structure so the owner
can choose the v12 visual identity by looking and clicking, not in the
abstract. The View > Interface style menu switches live between:

  1. Windows 11 native  - Qt's platform style, follows the system
  2. Fusion light       - Qt's own crisp cross-platform style
  3. Fusion dark        - the same, with a dark palette

Run with:  QCS_v12_preview.bat  (Desktop)  or
           & "C:\\Users\\LAMB\\anaconda3\\python.exe" packaging\\v12_preview.py
No QC logic here; buttons only log what they would do.
"""
import sys

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QActionGroup, QColor, QPalette
from PySide6.QtWidgets import (QApplication, QCheckBox, QComboBox, QDockWidget,
                               QFileDialog, QFormLayout, QGridLayout,
                               QGroupBox, QHBoxLayout, QLabel, QLineEdit,
                               QMainWindow, QPlainTextEdit, QPushButton,
                               QRadioButton, QTabWidget, QVBoxLayout, QWidget)

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
        # answer to v11.3's Hide log button
        self.log = QPlainTextEdit(readOnly=True)
        self.log.setPlainText('Info: this is the Execution log (drag me, '
                              'undock me, close me - View menu brings me back).')
        dock = QDockWidget('Execution log', self)
        dock.setWidget(self.log)
        self.addDockWidget(Qt.BottomDockWidgetArea, dock)
        self.dock = dock

        self._menus()
        self.statusBar().showMessage('Preview only - no QC logic behind the buttons')

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
        fin.addRow(QCheckBox('Correct GMT-3'))
        fin.addRow(QCheckBox('Select profile data'))
        fin.addRow(QCheckBox('Check variables'))
        lm = QHBoxLayout()
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

        run = QPushButton('Run qualification')
        run.setDefault(True)
        run.setMinimumHeight(34)
        run.clicked.connect(lambda: self.log.appendPlainText(
            'Info: (preview) this would run the real pipeline.'))
        settings = QPushButton('Settings')

        grid.addWidget(gin, 0, 0)
        grid.addWidget(gout, 0, 1)
        actions = QHBoxLayout()
        actions.addStretch()
        actions.addWidget(settings)
        actions.addWidget(run)
        actions.addStretch()
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
        mb = self.menuBar()
        for name in ('File', 'Edit', 'Tools', 'Help'):
            mb.addMenu(name).addAction('(preview)')
        view = mb.addMenu('View')
        style = view.addMenu('Interface style')
        group = QActionGroup(self)
        for label, key in (('1 - Windows 11 native', 'native'),
                           ('2 - Fusion light', 'fusion'),
                           ('3 - Fusion dark', 'fusion-dark')):
            act = QAction(label, self, checkable=True)
            act.triggered.connect(lambda _=False, k=key: apply_style(k))
            group.addAction(act)
            style.addAction(act)
        group.actions()[0].setChecked(True)
        view.addAction(self.dock.toggleViewAction())


def apply_style(key):
    # Qt 6.8 follows the WINDOWS dark/light mode by default; the light and
    # dark variants pin the scheme explicitly, the native one follows the
    # system (in v12 proper that gives automatic dark mode for free)
    app = QApplication.instance()
    if key == 'native':
        app.styleHints().setColorScheme(Qt.ColorScheme.Light)
        app.setStyle('windows11')
        app.setPalette(app.style().standardPalette())
    elif key == 'fusion':
        app.styleHints().setColorScheme(Qt.ColorScheme.Light)
        app.setStyle('Fusion')
        app.setPalette(app.style().standardPalette())
    elif key == 'fusion-dark':
        app.styleHints().setColorScheme(Qt.ColorScheme.Dark)
        app.setStyle('Fusion')
        app.setPalette(dark_palette())


def main():
    app = QApplication(sys.argv)
    win = Preview()
    style = sys.argv[sys.argv.index('--style') + 1] if '--style' in sys.argv else 'native'
    apply_style(style)
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

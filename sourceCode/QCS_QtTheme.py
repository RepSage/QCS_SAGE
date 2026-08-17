# -*- coding: utf-8 -*-
"""Qt theming and shared shell widgets for the v12.0 interface.

The Qt counterpart of QCS_Theme: Fusion style in light/dark (owner decisions,
2026-08-14 - scheme pinned so the toggle, not the OS, decides; base font
10.5 pt; bold main tabs; grayed Execution log background), the Execution log
as a dockable panel with the same severity colors as the tk LogConsole, and
the crash handler. File-path helpers (writable_app_dir) stay in QCS_Theme -
they are toolkit-free and both shells share them.
"""
import sys
import traceback

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import (QAbstractButton, QApplication, QDockWidget,
                               QMessageBox, QTextEdit)

import QCS_Theme as theme   # writable_app_dir + crash-log path (toolkit-free)

LOG_TOOLTIPS = {
    'area': "Progress, warnings and errors of the current run\nRight-click for copy options",
    'float': "Detaches the log into its own window (drag it back to re-dock)",
    'close': "Hides the log; messages keep accumulating\nReopen it in View > Execution log",
}

# same severity mapping as QCS_Theme.LogConsole._tag_for, adapted per scheme
LOG_COLORS = {'light': {'error': '#b30000', 'warning': '#9a6a00',
                        'success': '#1f7a1f', 'default': '#202020'},
              'dark': {'error': '#f48771', 'warning': '#dcdcaa',
                       'success': '#89d185', 'default': '#d4d4d4'}}


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


def apply_style(dark):
    """Fusion, light or dark. The scheme is pinned per variant so the in-app
    toggle, not the OS dark mode, decides (Qt 6.8 follows Windows otherwise)."""
    app = QApplication.instance()
    font = app.font()
    font.setPointSizeF(10.5)
    app.setFont(font)
    app.setProperty('qcs_dark', bool(dark))
    if dark:
        app.styleHints().setColorScheme(Qt.ColorScheme.Dark)
        app.setStyle('Fusion')
        app.setPalette(dark_palette())
    else:
        app.styleHints().setColorScheme(Qt.ColorScheme.Light)
        app.setStyle('Fusion')
        app.setPalette(app.style().standardPalette())
    # main tabs: no bold (owner, 2026-08-17); instead each of the two tabs
    # carries its own pastel, selected = the stronger shade. Scoped to
    # QTabBar#MainTabs so the Settings window's tabs stay native.
    if dark:
        log_bg = '#232324'
        tab1, tab1_sel = '#33475e', '#41608a'    # muted blue
        tab2, tab2_sel = '#37503b', '#4a7052'    # muted green
    else:
        log_bg = '#e9e9e9'
        tab1, tab1_sel = '#d7e7f7', '#b3d4f2'    # pastel blue
        tab2, tab2_sel = '#dcefd8', '#bce3b4'    # pastel green
    app.setStyleSheet(
        'QTextEdit#ExecutionLog { background: %s; }\n'
        'QTabBar#MainTabs::tab { padding: 6px 16px; }\n'
        'QTabBar#MainTabs::tab:first { background: %s; }\n'
        'QTabBar#MainTabs::tab:first:selected { background: %s; }\n'
        'QTabBar#MainTabs::tab:last { background: %s; }\n'
        'QTabBar#MainTabs::tab:last:selected { background: %s; }'
        % (log_bg, tab1, tab1_sel, tab2, tab2_sel))


def bold_form_labels(form):
    """Bolds every row label of a QFormLayout ('Data file(s):', 'Instrument:'
    ...) - owner decision 2026-08-17, applied to the Qualification and
    Visualization forms."""
    from PySide6.QtWidgets import QFormLayout
    for row in range(form.rowCount()):
        item = form.itemAt(row, QFormLayout.ItemRole.LabelRole)
        if item is not None and item.widget() is not None:
            f = item.widget().font()
            f.setBold(True)
            item.widget().setFont(f)


class LogDock(QDockWidget):
    """Execution log as a dock: draggable, collapsible, closable - the Qt
    answer to the tk Hide log button. Severity read from the message's leading
    label, exactly like QCS_Theme.LogConsole: Info default, Warning amber,
    Error red, Done green."""

    def __init__(self, parent):
        super().__init__('Execution log', parent)
        self.text = QTextEdit(readOnly=True)
        self.text.setObjectName('ExecutionLog')
        self.text.setToolTip(LOG_TOOLTIPS['area'])
        self.setWidget(self.text)
        for btn in self.findChildren(QAbstractButton):
            if 'float' in btn.objectName():
                btn.setToolTip(LOG_TOOLTIPS['float'])
            elif 'close' in btn.objectName():
                btn.setToolTip(LOG_TOOLTIPS['close'])

    def clear(self):
        self.text.clear()

    def log(self, message):
        head = message.lstrip().lower()
        kind = ('error' if head.startswith(('error', 'critical')) else
                'warning' if head.startswith('warning') else
                'success' if head.startswith(('done', 'success')) else
                'default')
        scheme = 'dark' if QApplication.instance().property('qcs_dark') else 'light'
        self.text.append('<span style="color:%s">%s</span>'
                         % (LOG_COLORS[scheme][kind], message.replace('<', '&lt;')))


def install_crash_handler(app_title):
    """Fatal-crash net for the Qt shell: full traceback to QCS_crash.log (the
    same file and folder rules as the tk shell, via QCS_Theme) and a dialog,
    so a frozen app can never die silently."""
    def handler(exc_type, exc, tb):
        text = ''.join(traceback.format_exception(exc_type, exc, tb))
        path = None
        try:
            import os
            path = os.path.join(theme.writable_app_dir(), 'QCS_crash.log')
            with open(path, 'a', encoding='utf-8') as f:
                f.write(text + '\n')
        except Exception:
            pass
        try:
            QMessageBox.critical(
                None, app_title,
                'A fatal error interrupted the program:\n\n%s\n\n'
                'Full traceback%s.' % (exc, ' in %s' % path if path else ' unavailable'))
        except Exception:
            pass
        sys.__excepthook__(exc_type, exc, tb)
    sys.excepthook = handler

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
                               QMessageBox, QProxyStyle, QStyle, QTextEdit)

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


# the accent used for checked boxes/radios and the primary action buttons
# (owner, 2026-08-17: the tk app's blue check marks were missed)
ACCENT = '#2a6fb5'
ACCENT_DARK = '#4a90d9'      # lighter, for the dark scheme


class AccentStyle(QProxyStyle):
    """Draws the check/radio indicators with the accent colour instead of the
    plain text colour, keeping Fusion's own shape: the base style paints the
    mark with palette.text(), so swapping that ONE role for the primitive is
    enough - no bitmap assets, and it survives freezing."""

    def __init__(self, base, accent):
        super().__init__(base)
        self._accent = QColor(accent)

    def drawPrimitive(self, element, option, painter, widget=None):
        marks = (QStyle.PrimitiveElement.PE_IndicatorCheckBox,
                 QStyle.PrimitiveElement.PE_IndicatorRadioButton)
        if (element in marks
                and option.state & QStyle.StateFlag.State_Enabled
                and option.state & (QStyle.StateFlag.State_On
                                    | QStyle.StateFlag.State_NoChange)):
            opt = type(option)(option)
            opt.palette.setColor(QPalette.ColorRole.Text, self._accent)
            opt.palette.setColor(QPalette.ColorRole.WindowText, self._accent)
            super().drawPrimitive(element, opt, painter, widget)
            return
        super().drawPrimitive(element, option, painter, widget)


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
    accent = ACCENT_DARK if dark else ACCENT
    if dark:
        app.styleHints().setColorScheme(Qt.ColorScheme.Dark)
        app.setStyle(AccentStyle('Fusion', accent))
        app.setPalette(dark_palette())
    else:
        app.styleHints().setColorScheme(Qt.ColorScheme.Light)
        app.setStyle(AccentStyle('Fusion', accent))
        app.setPalette(app.style().standardPalette())
    # main tabs: bold labels, no color - a subtle GREYSCALE step separates the
    # active tab from the inactive one (owner, 2026-08-17; the pastel round
    # was tried and dropped). Scoped to QTabBar#MainTabs so the Settings
    # window's tabs stay native.
    if dark:
        log_bg = '#232324'
        tab_off, tab_on = '#252526', '#3e3e40'
    else:
        log_bg = '#e9e9e9'
        tab_off, tab_on = '#d0d0d0', '#f6f6f6'
    # the primary action of each tab (Run qualification / Generate panels /
    # Next) in the accent colour, like the tk app's Accent.TButton
    app.setStyleSheet(
        'QTextEdit#ExecutionLog { background: %s; }\n'
        'QTabBar#MainTabs::tab { font-weight: bold; padding: 6px 16px; background: %s; }\n'
        'QTabBar#MainTabs::tab:selected { background: %s; }\n'
        'QPushButton#AccentButton { background: %s; color: white; border: none;'
        ' border-radius: 3px; padding: 6px 18px; }\n'
        'QPushButton#AccentButton:hover { background: %s; }\n'
        'QPushButton#AccentButton:pressed { background: %s; }\n'
        'QPushButton#AccentButton:disabled { background: %s; color: %s; }'
        % (log_bg, tab_off, tab_on, accent,
           _shift(accent, 18), _shift(accent, -22),
           '#4a4a4c' if dark else '#c8c8c8', '#8a8a8a' if dark else '#efefef'))


def _shift(hex_color, delta):
    """Lighter (delta > 0) or darker shade of an accent, for hover/pressed."""
    c = QColor(hex_color)
    return QColor(min(255, max(0, c.red() + delta)),
                  min(255, max(0, c.green() + delta)),
                  min(255, max(0, c.blue() + delta))).name()


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

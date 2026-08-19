# -*- coding: utf-8 -*-
"""Qt theming and shared shell widgets for the v12.0 interface.

The Qt counterpart of QCS_Theme: Fusion style in light/dark (owner decisions,
2026-08-14 - scheme pinned so the toggle, not the OS, decides; base font
10.5 pt; bold main tabs; grayed Execution log background), the Execution log
as a dockable panel with the same severity colors as the tk LogConsole, and
the crash handler. File-path helpers (writable_app_dir) stay in QCS_Theme -
they are toolkit-free and both shells share them.
"""
import math
import sys
import traceback

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import (QAbstractButton, QApplication, QDockWidget,
                               QHBoxLayout, QMessageBox, QProxyStyle,
                               QPushButton, QScrollArea, QStyle, QTextEdit,
                               QVBoxLayout, QWidget)

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
    """Draws the check/radio indicators with the accent color instead of the
    plain text color, keeping Fusion's own shape: the base style paints the
    mark with palette.text(), so swapping that ONE role for the primitive is
    enough - no bitmap assets, and it survives freezing."""

    def __init__(self, base, accent, muted):
        super().__init__(base)
        self._accent = QColor(accent)
        self._muted = QColor(muted)

    def drawPrimitive(self, element, option, painter, widget=None):
        marks = (QStyle.PrimitiveElement.PE_IndicatorCheckBox,
                 QStyle.PrimitiveElement.PE_IndicatorRadioButton)
        if element in marks and option.state & (QStyle.StateFlag.State_On
                                                | QStyle.StateFlag.State_NoChange):
            opt = type(option)(option)
            # a DISABLED checked box keeps a (muted) accent instead of fading
            # into the background - it still carries information
            color = (self._accent if option.state & QStyle.StateFlag.State_Enabled
                     else self._muted)
            opt.palette.setColor(QPalette.ColorRole.Text, color)
            opt.palette.setColor(QPalette.ColorRole.WindowText, color)
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
    # Secondary text (hints, the Selection summary, 'Data available: ...')
    # reads through palette(mid); Qt's derived value is far too dark on this
    # background (owner, 2026-08-17: "clareia tudo que fica com pouco
    # contraste"), as is placeholder text.
    p.setColor(QPalette.Mid, QColor(170, 170, 172))
    p.setColor(QPalette.PlaceholderText, QColor(150, 150, 152))
    # Disabled controls must stay READABLE, just clearly inactive: the derived
    # dark-on-dark gray made unavailable checkboxes almost invisible.
    for role in (QPalette.WindowText, QPalette.Text, QPalette.ButtonText):
        p.setColor(QPalette.Disabled, role, QColor(140, 140, 142))
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
    muted_accent = _shift(accent, -60) if dark else _shift(accent, 70)
    if dark:
        app.styleHints().setColorScheme(Qt.ColorScheme.Dark)
        app.setStyle(AccentStyle('Fusion', accent, muted_accent))
        app.setPalette(dark_palette())
    else:
        app.styleHints().setColorScheme(Qt.ColorScheme.Light)
        app.setStyle(AccentStyle('Fusion', accent, muted_accent))
        app.setPalette(app.style().standardPalette())
    # main tabs: bold labels, no color - a subtle GRAYSCALE step separates the
    # active tab from the inactive one (owner, 2026-08-17; the pastel round
    # was tried and dropped). Scoped to QTabBar#MainTabs so the Settings
    # window's tabs stay native.
    if dark:
        log_bg = '#232324'
        tab_off, tab_on = '#252526', '#3e3e40'
    else:
        log_bg = '#e9e9e9'
        tab_off, tab_on = '#d0d0d0', '#f6f6f6'
    # Tooltips: inverted against the window (dark slab with light text in the
    # light scheme, the reverse in the dark one), through the stylesheet - the
    # owner prefers this rendering to the palette-only version.
    tip_bg, tip_fg = ('#e8e8ea', '#1b1b1c') if dark else ('#3a3a3c', '#f2f2f2')
    # QGroupBox is left to Fusion. Styling it through the stylesheet meant
    # drawing its frame and title by hand, and the result was worse than the
    # panel it removed (owner, 2026-08-17: "você está destruindo as
    # visualizações") - so the native look stays, slab included.
    # the primary action of each tab (Run qualification / Generate panels /
    # Next) in the accent color, like the tk app's Accent.TButton
    app.setStyleSheet(
        'QToolTip { background: %s; color: %s; border: 1px solid %s;'
        ' padding: 4px; }\n'
        'QComboBox { combobox-popup: 0; }\n'
        'QTextEdit#ExecutionLog { background: %s; }\n'
        'QTabBar#MainTabs::tab { font-weight: bold; padding: 6px 16px; background: %s; }\n'
        'QTabBar#MainTabs::tab:selected { background: %s; }\n'
        'QPushButton#AccentButton { background: %s; color: white; border: none;'
        ' border-radius: 3px; padding: 6px 18px; }\n'
        'QPushButton#AccentButton:hover { background: %s; }\n'
        'QPushButton#AccentButton:pressed { background: %s; }\n'
        'QPushButton#AccentButton:disabled { background: %s; color: %s; }'
        % (tip_bg, tip_fg, _shift(tip_bg, -40 if dark else 40),
           log_bg, tab_off, tab_on, accent,
           _shift(accent, 18), _shift(accent, -22),
           '#4a4a4c' if dark else '#c8c8c8', '#8a8a8a' if dark else '#efefef'))


def _shift(hex_color, delta):
    """Lighter (delta > 0) or darker shade of an accent, for hover/pressed."""
    c = QColor(hex_color)
    return QColor(min(255, max(0, c.red() + delta)),
                  min(255, max(0, c.green() + delta)),
                  min(255, max(0, c.blue() + delta))).name()


# Geometry of the reset arrow, as chosen by the owner on 2026-08-19 from the
# candidate sheet (variant C1a). Everything is a fraction of the icon size, so
# the shape is identical at 16 px and at 64 px. Two opposed arcs, each ending
# in a head whose TIP and BASE both sit on the circle - a head built along the
# tangent instead has its base outside the ring and leans off the stroke.
_RESET_RADIUS = 8.0 / 24        # circle radius
_RESET_STROKE = 1.5 / 24        # arc weight
_RESET_HEAD_LEN = 5.0 / 24      # head, tip to base
_RESET_HEAD_HALF = 2.2 / 24     # head, half of the base
_RESET_TIPS = (155.0, 335.0)    # where each arc ends, degrees, 0 at 3 o'clock
_RESET_SWEEP = 130.0            # how far each arc runs back from its tip
_RESET_JOIN = 0.75              # of the head the stroke runs into, for no seam


def reset_icon(size=16, color=None):
    """The 'restore the default' arrow, PAINTED rather than typed.

    The reset buttons of the Settings window used the text glyph U+21BA, which
    is drawn by whatever font happens to carry it: it came out coarse and
    off-weight beside the rest of the interface (owner, 2026-08-19). Painting
    at the screen's device pixel ratio keeps it sharp on a HiDPI display, and
    the palette colour keeps it right in both themes.
    """
    from PySide6.QtCore import QPointF, QRectF
    from PySide6.QtGui import QIcon, QPainter, QPainterPath, QPen, QPixmap
    app = QApplication.instance()
    ratio = app.devicePixelRatio() if app else 1.0
    if color is None:
        color = (app.palette().color(QPalette.WindowText) if app
                 else QColor('#000000'))
    px = QPixmap(int(size * ratio), int(size * ratio))
    px.setDevicePixelRatio(ratio)
    px.fill(Qt.transparent)
    p = QPainter(px)
    p.setRenderHint(QPainter.Antialiasing, True)

    r = size * _RESET_RADIUS
    cx = cy = size / 2.0
    head_len = size * _RESET_HEAD_LEN
    half = size * _RESET_HEAD_HALF
    head_span = math.degrees(head_len / r)      # what the head covers, in degrees
    ring = QRectF(cx - r, cy - r, 2 * r, 2 * r)

    def on_circle(angle_deg):
        rad = math.radians(angle_deg)
        return QPointF(cx + r * math.cos(rad), cy - r * math.sin(rad))

    # the floor matters at the size the buttons actually use: the proportional
    # weight is 1.0 px at 16 px, which antialiasing then spreads into a grey
    # smudge - 1.35 keeps the two arcs reading as strokes
    pen = QPen(color, max(1.35, size * _RESET_STROKE))
    pen.setCapStyle(Qt.FlatCap)                 # the head finishes the stroke
    for tip_angle in _RESET_TIPS:
        # Qt angles are anticlockwise from 3 o'clock, in 1/16 degree. The arc
        # stops inside the head (_RESET_JOIN of it) so the two never show a
        # seam between them.
        start = tip_angle - _RESET_SWEEP
        stop = tip_angle - head_span * _RESET_JOIN
        p.setPen(pen)
        p.setBrush(Qt.NoBrush)
        p.drawArc(ring, int(round(start * 16)), int(round((stop - start) * 16)))

        tip = on_circle(tip_angle)
        base = on_circle(tip_angle - head_span)
        ax, ay = tip.x() - base.x(), tip.y() - base.y()
        norm = math.hypot(ax, ay) or 1.0
        nx, ny = -ay / norm, ax / norm          # unit normal to the head's axis
        path = QPainterPath(tip)
        path.lineTo(base.x() + nx * half, base.y() + ny * half)
        path.lineTo(base.x() - nx * half, base.y() - ny * half)
        path.closeSubpath()
        p.setPen(Qt.NoPen)
        p.setBrush(color)
        p.drawPath(path)
    p.end()
    return QIcon(px)


def muted(widget):
    """Secondary text (hints, summaries, 'Data available: ...').

    Uses the PALETTE, never a stylesheet: setting a stylesheet on a child
    makes Qt re-render its ancestors through the stylesheet engine, which
    painted a gray slab behind the enclosing QGroupBox (that was the
    unexplained box around 'Data settings' and 'Selection summary')."""
    widget.setForegroundRole(QPalette.Mid)
    return widget


def scrollable(page):
    """Wraps a TAB PAGE so it can shrink to nothing.

    A QMainWindow never lets a dock grow past the central widget's minimum,
    and the Qualification page alone asked for 608 px - so the Execution log
    stopped at ~124 px however hard it was dragged. Inside a scroll area the
    page's minimum is the scroll area's own (tiny): the log takes whatever
    height the operator drags it to and the boxes above get a scrollbar
    (owner, 2026-08-18).

    The background is left to the tab pane, exactly as in the Visualization
    settings area: setWidget() would otherwise fill it with a flat gray slab.
    """
    area = QScrollArea()
    area.setWidgetResizable(True)
    area.setFrameShape(QScrollArea.Shape.NoFrame)
    area.setWidget(page)
    page.setAutoFillBackground(False)
    area.viewport().setAutoFillBackground(False)
    return area


def scroll_to_top(widget):
    """Puts the scroll area that holds `widget` back at its top.

    Switching tab or step used to land wherever the previous page had been
    scrolled to - stepping into the Visualization tab opened it at the BOTTOM
    (owner, 2026-08-19). Qt also scrolls a page by itself to keep the focused
    widget visible, and that happens after the switch, so the reset is queued
    with a zero timer rather than applied inline."""
    from PySide6.QtCore import QTimer
    area = widget
    while area is not None and not isinstance(area, QScrollArea):
        area = area.parentWidget()
    if area is None:
        return

    def top():
        area.verticalScrollBar().setValue(0)
        area.horizontalScrollBar().setValue(0)
    top()
    QTimer.singleShot(0, top)


def dock_tooltips(dock, float_tip, close_tip):
    """Qt names the dock title-bar buttons but gives them no tooltips."""
    for btn in dock.findChildren(QAbstractButton):
        if 'float' in btn.objectName():
            btn.setToolTip(float_tip)
        elif 'close' in btn.objectName():
            btn.setToolTip(close_tip)


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
        # 'Clear log' was a button of the tk log console and is expected here
        # too (owner, 2026-08-17); 'Hide log' is the dock's own close button
        holder = QWidget()
        v = QVBoxLayout(holder)
        v.setContentsMargins(0, 0, 0, 0)
        v.addWidget(self.text)
        self.button_row = QHBoxLayout()
        self.button_row.setContentsMargins(0, 0, 0, 0)
        self.button_row.addStretch()
        self.clear_button = QPushButton('Clear log')
        self.clear_button.setToolTip('Erases the messages shown so far')
        self.clear_button.clicked.connect(self.clear)
        self.button_row.addWidget(self.clear_button)
        v.addLayout(self.button_row)
        self.setWidget(holder)
        dock_tooltips(self, LOG_TOOLTIPS['float'], LOG_TOOLTIPS['close'])

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

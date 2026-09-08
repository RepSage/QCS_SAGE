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
'Check variables' manual cut), the Settings window, the Curated database tab,
and the Data visualization tab (QCS_QtViz remote-controls the real DatabaseView
wizard). The review windows are pure matplotlib and open as Qt windows.

Run with:  QCS.bat  (packaging/v12_env venv, PySide6 6.8.3).
"""
import math
import os
import re
import sys
import threading
import warnings
from numbers import Real

import matplotlib
# Agg, not QtAgg (v12.3): under QtAgg every figure IS a QWidget, and Qt forbids
# building a widget outside the interface thread - which is exactly what the
# qualification does once it runs on a worker. Under Agg a figure is pure
# computation, buildable anywhere, and the shell provides the window itself
# (PlotWindow below). A figure keeps its mpl_connect callbacks when a QtAgg
# canvas is attached to it later: the registry lives on the FIGURE
# (matplotlib 3.10 `canvas.callbacks -> figure._canvas_callbacks`, measured).
matplotlib.use('Agg')              # before any QCS import binds pyplot
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import matplotlib.dates as mdates
import numpy as np
from matplotlib._pylab_helpers import Gcf
from matplotlib.backend_bases import CloseEvent
from matplotlib.backends.backend_qtagg import (FigureCanvasQTAgg,
                                               NavigationToolbar2QT)
from matplotlib.backends.backend_qt import SubplotToolQt
from matplotlib.backends.qt_editor import figureoptions
from matplotlib.collections import QuadMesh
from matplotlib.quiver import Quiver
from matplotlib.transforms import Bbox

from PySide6.QtCore import (QByteArray, QEvent, QEventLoop, QObject, QSize,
                            QSignalBlocker, Qt, QThread, QTimer, Signal, Slot)
from PySide6.QtGui import QAction, QColor, QIcon, QPainter, QPalette, QPixmap
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import (QApplication, QCheckBox, QComboBox, QDialog,
                               QDockWidget, QFileDialog, QFormLayout,
                               QGridLayout, QGroupBox, QHBoxLayout, QLabel,
                               QDoubleSpinBox, QLineEdit, QMainWindow,
                               QColorDialog, QMessageBox, QPlainTextEdit,
                               QInputDialog,
                               QProgressBar, QProgressDialog, QPushButton,
                               QRadioButton, QScrollArea, QStackedWidget,
                               QSizePolicy, QTableWidget, QTableWidgetItem,
                               QTabWidget, QToolButton, QVBoxLayout, QWidget)

import QCS_Theme as theme          # writable_app_dir + output redirect (shared)
_out = theme.install_output_redirect()
import QCS_QtTheme as qtheme
import QCS_Main as qm
import QCS_DataHandler as data
# installs the tk crash handler at import; main() installs the Qt one after
import QCS_DataView as view      # the panel plots (show_panels hook)
import QCS_DatabaseView as dbv
import QCS_Feedback as feedback_api
import QCS_Update as upd
from QCS_QtCurated import CuratedDatabaseTab
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

# Field mode is intentionally narrow: it only prevents access to the corpus
# workflow, which is not used while collecting data away from the office.
FIELD_MODE_TOOLTIP = (
    'Disable the Curated database tab while collecting data in the field.')
CURATED_TAB_TOOLTIP = (
    'Build a filtered, traceable workbook from the qualified corpus.')
CURATED_TAB_FIELD_TOOLTIP = (
    'Disabled by Field mode. Turn it off in View > Field mode to use '
    'Curated database.')


class _UpdateBridge(QObject):
    """Marshals the background update check's result onto the Qt main thread
    (the tk shell used root.after for the same purpose)."""
    newer = Signal(dict)

TOOLTIPS = qm.TOOLTIPS             # single source: the real texts (v11.6.1)

_ICON_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'qcs_icon.png')
_FLUENT_ICON_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                'icons', 'fluent')
_FLUENT_TOOLBAR_ICONS = {
    'home': 'home.svg',
    'move': 'pan.svg',
    'zoom_to_rect': 'zoom.svg',
    'subplots': 'subplots.svg',
    'qt4_editor_options': 'customize.svg',
    'filesave': 'save.svg',
}


def _app_icon():
    return QIcon(_ICON_PATH) if os.path.isfile(_ICON_PATH) else QIcon()


def _row_reset_button(tooltip, callback):
    """Small reset action shared by plot-editing value rows."""
    button = QToolButton()
    button.setIcon(qtheme.reset_icon(20))
    button.setIconSize(QSize(20, 20))
    button.setToolTip(tooltip)
    button.setAutoRaise(True)
    button.clicked.connect(callback)
    return button


class _QCSColorButton(QPushButton):
    """Full-size color swatch whose form value retains a hidden alpha."""

    def __init__(self, alpha=1.0, parent=None):
        super().__init__(parent)
        self._qcs_alpha = float(alpha)

    def text(self):
        color = getattr(self, '_qcs_color', '#000000')
        return mcolors.to_hex(
            mcolors.to_rgba(color, self._qcs_alpha), keep_alpha=True)


def _duration_text(hours):
    """A session length a person reads at a glance: minutes for a cast, hours
    for a day, days for a mooring."""
    if hours < 1:
        return '%d min' % round(hours * 60)
    if hours < 48:
        return '%.1f h' % hours
    return '%.1f days' % (hours / 24.0)


def _interval_text(seconds):
    """'3600' -> '1 h', '1800' -> '30 min', '45' -> '45 s'."""
    if seconds % 3600 == 0:
        return '%d h' % (seconds // 3600)
    if seconds % 60 == 0:
        return '%d min' % (seconds // 60)
    return '%d s' % seconds


def _qt_style_plot_window(fig, title=None):
    """Qt replacement for theme.style_plot_window. Under Agg there is no window
    to style yet, so the title is REMEMBERED on the figure and PlotWindow uses
    it when the figure is shown - the six call sites keep working unchanged."""
    if title:
        fig._qcs_window_title = title


def _axes_display_name(ax, index):
    """Return a stable, operator-facing name for a Matplotlib axes."""
    custom = getattr(ax.figure, '_qcs_axes_names', {}).get(ax)
    if custom:
        return custom
    title = (ax.get_title() or ax.get_title('left') or
             ax.get_title('right')).strip()
    if title:
        return title
    label = ax.get_label().strip()
    if label and not label.startswith(('_', '<')):
        return label
    if getattr(ax, 'name', '') == 'polar':
        return 'Direction compass'
    x_label = ax.get_xlabel().strip()
    y_label = ax.get_ylabel().strip()
    if label == '<colorbar>':
        scale_label = y_label or x_label
        return ('Color scale - %s' % scale_label
                if scale_label else 'Color scale')
    if x_label and y_label:
        return '%s by %s' % (y_label, x_label)
    if y_label or x_label:
        return y_label or x_label
    return 'Plot %d' % (index + 1)


def _unique_axes_names(axes):
    """Keep duplicate axes names readable without exposing memory addresses."""
    names = []
    counts = {}
    for index, ax in enumerate(axes):
        base = _axes_display_name(ax, index)
        counts[base] = counts.get(base, 0) + 1
        names.append(base if counts[base] == 1
                     else '%s (%d)' % (base, counts[base]))
    return names


def _subplot_grid_shape(fig):
    """Rows/columns in the top-level grids that subplotpars can affect."""
    rows = columns = 1
    for ax in fig.axes:
        try:
            spec = ax.get_subplotspec()
            if spec is None:
                continue
            grid = spec.get_topmost_subplotspec().get_gridspec()
            rows = max(rows, grid.nrows)
            columns = max(columns, grid.ncols)
        except (AttributeError, TypeError):
            continue
    return rows, columns


class QCSSubplotToolQt(SubplotToolQt):
    """Matplotlib's layout editor with clear names and legend positioning."""

    _FIELD_LABELS = {
        'top': 'Plot top edge',
        'bottom': 'Plot bottom edge',
        'left': 'Plot left edge',
        'right': 'Plot right edge',
        'hspace': 'Vertical gap',
        'wspace': 'Horizontal gap',
    }

    def __init__(self, targetfig, parent, window_icon=None):
        QDialog.__init__(self, parent)
        self.setObjectName('SubplotTool')
        self._figure = targetfig
        self._spinboxes = {}
        self._spinbox_labels = {}
        self._row_reset_buttons = {}
        self._defaults = {}
        self._export_values_dialog = None
        self._product_subplotpars = {
            name: getattr(targetfig.subplotpars, name) for name in (
                'top', 'bottom', 'left', 'right', 'hspace', 'wspace')
        }
        self.setWindowTitle('Adjust plot layout')
        if window_icon is not None:
            self.setWindowIcon(window_icon)

        outer = QVBoxLayout(self)
        controls = QHBoxLayout()
        controls.setSpacing(10)
        outer.addLayout(controls)
        for title, names in (
                ('Plot area', ('top', 'bottom', 'left', 'right')),
                ('Gaps between plots', ('hspace', 'wspace'))):
            box = QGroupBox(title)
            form = QFormLayout(box)
            for name in names:
                spinbox = QDoubleSpinBox()
                spinbox.setRange(0, 1)
                spinbox.setDecimals(3)
                spinbox.setSingleStep(0.005)
                spinbox.setKeyboardTracking(False)
                spinbox.valueChanged.connect(self._on_value_changed)
                label = QLabel(self._FIELD_LABELS[name])
                holder = QWidget()
                row = QHBoxLayout(holder)
                row.setContentsMargins(0, 0, 0, 0)
                row.setSpacing(4)
                row.addWidget(spinbox, 1)
                reset = _row_reset_button(
                    'Restore the original %s.' %
                    self._FIELD_LABELS[name].lower(),
                    lambda _checked=False, key=name:
                    self._reset_subplot_field(key))
                row.addWidget(reset)
                form.addRow(label, holder)
                self._spinboxes[name] = spinbox
                self._spinbox_labels[name] = label
                self._row_reset_buttons[name] = reset
            controls.addWidget(box)

        self._layout_keys = [dict(item) for item in
                             getattr(targetfig, '_qcs_layout_keys', [])]
        rows, columns = _subplot_grid_shape(targetfig)
        self._set_spacing_availability(
            'wspace', columns > 1,
            'Used only when the figure has two or more subplot columns.')
        self._set_spacing_availability(
            'hspace', rows > 1,
            'Used only when the figure has two or more subplot rows.')

        self._legend_group = QGroupBox('Legend / key position')
        legend_form = QFormLayout(self._legend_group)
        self._legend_target = QComboBox()
        legend_form.addRow('Apply to', self._legend_target)
        self._legend_x = self._legend_spinbox(
            'Fraction of the figure width; positive values move right.')
        self._legend_y = self._legend_spinbox(
            'Fraction of the figure height; positive values move up.')
        for name, label, spinbox in (
                ('legend_x', 'Horizontal offset', self._legend_x),
                ('legend_y', 'Vertical offset', self._legend_y)):
            holder = QWidget()
            row = QHBoxLayout(holder)
            row.setContentsMargins(0, 0, 0, 0)
            row.setSpacing(4)
            row.addWidget(spinbox, 1)
            reset = _row_reset_button(
                'Restore the original %s for the selected legend or key.' %
                label.lower(),
                lambda _checked=False, field=spinbox: field.setValue(0.0))
            row.addWidget(reset)
            legend_form.addRow(label, holder)
            self._row_reset_buttons[name] = reset
        controls.addWidget(self._legend_group)

        self._position_records = []
        self._position_bases = {}
        self._position_offsets = {}
        self._legend_target.currentIndexChanged.connect(
            self._show_target_legend_offset)
        self._legend_x.valueChanged.connect(self._legend_value_changed)
        self._legend_y.valueChanged.connect(self._legend_value_changed)
        for name, spinbox in self._spinboxes.items():
            spinbox.blockSignals(True)
            spinbox.setValue(self._product_subplotpars[name])
            spinbox.blockSignals(False)
        self._defaults = {
            spinbox: self._product_subplotpars[name]
            for name, spinbox in self._spinboxes.items()
        }
        self._refresh_position_items()
        self._on_value_changed()
        self._product_positions = {}
        for record in self._position_records:
            item = record['item']
            if record['kind'] == 'legend':
                bbox = item.get_bbox_to_anchor().transformed(
                    self._figure.transFigure.inverted())
            else:
                bbox = item.get_position()
            self._product_positions[item] = Bbox.from_extents(*bbox.extents)

        action_grid = QGridLayout()
        action_grid.setHorizontalSpacing(8)
        action_grid.setVerticalSpacing(6)
        self._buttons = {
            'tight': QPushButton('Tight layout'),
            'export': QPushButton('Export values'),
            'reset': QPushButton('Reset values'),
            'ok': QPushButton('OK'),
        }
        self._buttons['tight'].clicked.connect(self._tight_layout)
        self._buttons['export'].clicked.connect(self._export_values)
        self._buttons['reset'].clicked.connect(self._reset)
        self._buttons['reset'].setToolTip(
            'Restore all original product layout and legend/key positions.')
        self._buttons['ok'].clicked.connect(self.accept)
        self._buttons['ok'].setDefault(True)
        for button in self._buttons.values():
            button.setAutoDefault(False)
        button_width = max(
            132, *(button.sizeHint().width()
                   for button in self._buttons.values()))
        for button in self._buttons.values():
            button.setFixedWidth(button_width)
        action_grid.addWidget(self._buttons['tight'], 0, 0)
        action_grid.addWidget(self._buttons['reset'], 0, 1)
        action_grid.addWidget(self._buttons['export'], 1, 0)
        action_grid.addWidget(self._buttons['ok'], 1, 1)
        self._action_grid = action_grid
        actions = QHBoxLayout()
        actions.addStretch(1)
        actions.addLayout(action_grid)
        actions.addStretch(1)
        outer.addSpacing(4)
        outer.addLayout(actions)

    @staticmethod
    def _legend_spinbox(tooltip):
        spinbox = QDoubleSpinBox()
        spinbox.setRange(-1, 1)
        spinbox.setDecimals(3)
        spinbox.setSingleStep(0.005)
        spinbox.setKeyboardTracking(False)
        spinbox.setToolTip(tooltip)
        return spinbox

    def _set_spacing_availability(self, name, available, tooltip):
        spinbox = self._spinboxes[name]
        spinbox.setEnabled(available)
        spinbox.setToolTip(tooltip)
        self._row_reset_buttons[name].setEnabled(available)
        self._row_reset_buttons[name].setToolTip(tooltip)
        label = self._spinbox_labels.get(name)
        if label is not None:
            label.setEnabled(available)
            label.setToolTip(tooltip)

    def _reset_subplot_field(self, name):
        """Restore one plot-layout field without changing its neighbours."""
        self._spinboxes[name].setValue(self._product_subplotpars[name])

    def _on_value_changed(self):
        super()._on_value_changed()
        if hasattr(self, '_position_records'):
            self._apply_position_offsets()

    def _collect_position_items(self):
        records = [
            {'name': 'Figure legend', 'kind': 'legend', 'item': legend}
            for legend in self._figure.legends
        ]
        for index, ax in enumerate(self._figure.axes):
            legend = ax.get_legend()
            if legend is not None:
                records.append({
                    'name': 'Legend - %s' % _axes_display_name(ax, index),
                    'kind': 'legend',
                    'item': legend,
                })
        for item in self._layout_keys:
            key_axes = item.get('axes')
            anchor = item.get('anchor')
            if key_axes in self._figure.axes and anchor in self._figure.axes:
                records.append({
                    'name': item['name'],
                    'kind': 'axes',
                    'item': key_axes,
                    'anchor': anchor,
                    'vertical': item.get('vertical', 'fixed'),
                })
        unique = []
        seen = set()
        for record in records:
            identity = id(record['item'])
            if identity not in seen:
                unique.append(record)
                seen.add(identity)
        return unique

    def _refresh_position_items(self):
        self._position_records = self._collect_position_items()
        self._position_bases = {}
        self._position_offsets = {}
        self._legend_target.blockSignals(True)
        self._legend_target.clear()
        if len(self._position_records) > 1:
            self._legend_target.addItem('All legends and keys')
        for record in self._position_records:
            self._legend_target.addItem(record['name'])
            item = record['item']
            if record['kind'] == 'legend':
                bbox = item.get_bbox_to_anchor().transformed(
                    self._figure.transFigure.inverted())
                base = {'bbox': Bbox.from_extents(*bbox.extents)}
            else:
                position = item.get_position()
                anchor = record['anchor'].get_position()
                base = {
                    'gap_x': position.x0 - anchor.x1,
                    'relative_y': position.y0 - anchor.y0,
                    'width': position.width,
                    'height': position.height,
                }
            self._position_bases[item] = base
            self._position_offsets[item] = (0.0, 0.0)
        self._legend_target.blockSignals(False)
        available = bool(self._position_records)
        self._legend_group.setEnabled(available)
        if not available:
            self._legend_target.addItem('No legend or key on this figure')
        self._show_target_legend_offset()

    def _target_position_items(self):
        if not self._position_records:
            return []
        index = self._legend_target.currentIndex()
        if len(self._position_records) > 1:
            if index == 0:
                return [record['item'] for record in self._position_records]
            index -= 1
        return [self._position_records[max(0, index)]['item']]

    def _show_target_legend_offset(self, *_):
        items = self._target_position_items()
        x_value, y_value = (self._position_offsets.get(items[0], (0.0, 0.0))
                            if items else (0.0, 0.0))
        for spinbox, value in ((self._legend_x, x_value),
                               (self._legend_y, y_value)):
            spinbox.blockSignals(True)
            spinbox.setValue(value)
            spinbox.blockSignals(False)

    def _legend_value_changed(self, *_):
        for item in self._target_position_items():
            self._position_offsets[item] = (self._legend_x.value(),
                                            self._legend_y.value())
        self._apply_position_offsets()

    def _apply_position_offsets(self):
        for record in self._position_records:
            item = record['item']
            base = self._position_bases[item]
            dx, dy = self._position_offsets[item]
            if record['kind'] == 'legend':
                bbox = base['bbox']
                moved = Bbox.from_extents(bbox.x0 + dx, bbox.y0 + dy,
                                          bbox.x1 + dx, bbox.y1 + dy)
                item.set_bbox_to_anchor(moved,
                                        transform=self._figure.transFigure)
                continue
            anchor = record['anchor'].get_position()
            x0 = anchor.x1 + base['gap_x'] + dx
            if record['vertical'] == 'match':
                y0 = anchor.y0 + dy
                height = anchor.height
            elif record['vertical'] == 'center':
                y0 = anchor.y0 + anchor.height / 2 - base['height'] / 2 + dy
                height = base['height']
            else:
                y0 = anchor.y0 + base['relative_y'] + dy
                height = base['height']
            item.set_position([x0, y0, base['width'], height])
        self._figure.canvas.draw_idle()

    def update_from_current_subplotpars(self):
        if not hasattr(self, '_legend_x'):
            super().update_from_current_subplotpars()
            return
        self._defaults = {
            spinbox: self._product_subplotpars[name]
            for name, spinbox in self._spinboxes.items()
        }
        for name, spinbox in self._spinboxes.items():
            spinbox.blockSignals(True)
            spinbox.setValue(getattr(self._figure.subplotpars, name))
            spinbox.blockSignals(False)
        SubplotToolQt._on_value_changed(self)
        self._refresh_position_items()

    def _reset(self):
        if not hasattr(self, '_position_records'):
            super()._reset()
            return
        super()._reset()
        for record in self._position_records:
            item = record['item']
            bbox = self._product_positions.get(item)
            if bbox is None:
                continue
            if record['kind'] == 'legend':
                item.set_bbox_to_anchor(
                    bbox, transform=self._figure.transFigure)
            else:
                item.set_position(bbox)
        self._refresh_position_items()
        self._figure.canvas.draw_idle()

    def _tight_layout(self):
        with warnings.catch_warnings():
            warnings.filterwarnings(
                'ignore',
                message='This figure includes Axes that are not compatible '
                        'with tight_layout.*')
            super()._tight_layout()
        # Color scales are normal Matplotlib axes and follow tight_layout, but
        # the compass is an absolute polar axes. Re-anchor every side key after
        # the data axes move so neither can land on top of its heatmap.
        self._apply_position_offsets()

    def _export_values(self):
        dialog = QDialog(self, Qt.WindowType.Tool)
        dialog.setWindowTitle('Layout values')
        layout = QVBoxLayout(dialog)
        text = QPlainTextEdit()
        text.setReadOnly(True)
        values = [
            '%s=%.3f' % (name, spinbox.value())
            for name, spinbox in self._spinboxes.items()
        ]
        if self._position_records:
            values.extend([
                'legend_horizontal_offset=%.3f' % self._legend_x.value(),
                'legend_vertical_offset=%.3f' % self._legend_y.value(),
            ])
        text.setPlainText(',\n'.join(values))
        text.setMinimumWidth(330)
        layout.addWidget(text)
        buttons = QHBoxLayout()
        copy_button = QPushButton('Copy all')
        copy_button.clicked.connect(
            lambda: QApplication.clipboard().setText(text.toPlainText()))
        close_button = QPushButton('Close')
        close_button.clicked.connect(dialog.close)
        buttons.addWidget(copy_button)
        buttons.addStretch()
        buttons.addWidget(close_button)
        layout.addLayout(buttons)
        self._export_values_dialog = dialog
        dialog.show()
        dialog.raise_()
        dialog.activateWindow()


class QCSNavigationToolbar(NavigationToolbar2QT):
    """QCS plot toolbar: useful actions only, with readable Qt dialogs."""

    toolitems = tuple(
        item for item in NavigationToolbar2QT.toolitems
        if item[3] not in ('back', 'forward')
    )

    def __init__(self, canvas, parent=None, coordinates=True):
        super().__init__(canvas, parent, coordinates)
        configured = getattr(canvas.figure, '_qcs_customize_axes', None)
        default_axes = ([ax for _name, ax in configured]
                        if configured is not None else [
                            ax for ax in canvas.figure.axes
                            if ax.get_visible() and ax.get_label() != '<colorbar>'
                        ])
        # Capture the published product before wheel zoom, Pan or Customize can
        # alter it; Reset values must not treat the latest view as the default.
        self._figure_option_defaults = {
            ax: self._capture_figure_options(ax) for ax in default_axes
        }
        self._zoom_min_spans = {}
        self._zoom_max_spans = {}
        for ax in canvas.figure.axes:
            if not ax.get_visible() or not ax.get_navigate():
                continue
            xlim = ax.get_xlim()
            ylim = ax.get_ylim()
            self._zoom_min_spans[ax] = (
                self._minimum_axis_span(xlim),
                self._minimum_axis_span(ylim),
            )
            self._zoom_max_spans[ax] = (
                abs(float(xlim[1]) - float(xlim[0])) * view.ZOOM_OUT_FACTOR,
                abs(float(ylim[1]) - float(ylim[0])) * view.ZOOM_OUT_FACTOR,
            )
        # Doppler uses the owner's requested v14.0 legend appearance. Other
        # families retain line-only keys. Only cloned legend handles change.
        v140_doppler = getattr(canvas.figure, '_qcs_v140_doppler', False)
        if not v140_doppler:
            for ax in canvas.figure.axes:
                view.line_only_legend(ax.get_legend())
            for legend in canvas.figure.legends:
                view.line_only_legend(legend)
        for ax in default_axes:
            for record in self._collect_legend_labels(ax):
                handle = self._legend_symbol_handle(record)
                if (handle is not None and (v140_doppler or not self._is_editable_line(handle)) and
                        handle.get_marker() in (None, '', ' ', 'None', 'none', '.')):
                    handle.set_marker('o')
        self._legend_defaults = {
            ax: {
                record['key']: self._capture_legend_record(record)
                for record in self._collect_legend_labels(ax)
            }
            for ax in default_axes
        }
        self.setIconSize(QSize(20, 20))
        self.layout().setContentsMargins(5, 3, 5, 3)
        self.layout().setSpacing(3)
        zoom_action = self._actions.get('zoom')
        if zoom_action is not None:
            zoom_action.setToolTip(
                'Zoom to rectangle (range: 1/10,000 to 100x the opening view)')
        if coordinates:
            font = self.locLabel.font()
            font.setBold(True)
            self.locLabel.setFont(font)

    def _icon(self, name):
        """Render the selected Fluent Regular asset in the active palette."""
        stem = os.path.splitext(os.path.basename(name))[0]
        filename = _FLUENT_TOOLBAR_ICONS.get(stem)
        if filename is None:
            return super()._icon(name)
        path = os.path.join(_FLUENT_ICON_DIR, filename)
        try:
            with open(path, encoding='utf-8') as stream:
                svg = stream.read()
            color = self.palette().color(
                QPalette.ColorRole.WindowText).name()
            svg = svg.replace('#212121', color)
            renderer = QSvgRenderer(QByteArray(svg.encode('utf-8')))
            ratio = self.devicePixelRatioF() or 1.0
            pixmap = QPixmap(round(20 * ratio), round(20 * ratio))
            pixmap.fill(Qt.GlobalColor.transparent)
            painter = QPainter(pixmap)
            renderer.render(painter)
            painter.end()
            pixmap.setDevicePixelRatio(ratio)
            return QIcon(pixmap)
        except (OSError, RuntimeError):
            return super()._icon(name)

    def _refresh_icons(self):
        if not hasattr(self, '_actions'):
            return
        for _text, _tooltip, image_file, callback in self.toolitems:
            if image_file is not None and callback in self._actions:
                self._actions[callback].setIcon(self._icon(image_file + '.png'))

    def changeEvent(self, event):
        super().changeEvent(event)
        if event.type() == QEvent.Type.PaletteChange:
            self._refresh_icons()

    def _deactivate_navigation_mode(self):
        """Leave Pan/Zoom before another toolbar command takes focus."""
        if self.mode.name == 'PAN':
            super().pan()
        elif self.mode.name == 'ZOOM':
            super().zoom()

    def home(self, *args):
        self._deactivate_navigation_mode()
        return super().home(*args)

    def save_figure(self, *args):
        self._deactivate_navigation_mode()
        return super().save_figure(*args)

    @staticmethod
    def _minimum_axis_span(limits):
        """Finite zoom floor derived from one axis' published opening view."""
        low, high = map(float, limits)
        opening_span = abs(high - low)
        roundoff_floor = (max(abs(low), abs(high), 1.0) *
                          sys.float_info.epsilon * 64)
        return max(opening_span / 10_000.0, roundoff_floor)

    def _enforce_zoom_limits(self):
        """Bound extreme zoom without changing the Home view."""
        changed = False
        for ax, (min_x, min_y) in self._zoom_min_spans.items():
            if ax not in self.canvas.figure.axes:
                continue
            max_x, max_y = self._zoom_max_spans[ax]
            for getter, setter, minimum, maximum in (
                    (ax.get_xlim, ax.set_xlim, min_x, max_x),
                    (ax.get_ylim, ax.set_ylim, min_y, max_y)):
                low, high = map(float, getter())
                if not math.isfinite(low) or not math.isfinite(high):
                    continue
                span = abs(high - low)
                if span < minimum:
                    target = minimum
                elif span > maximum:
                    target = maximum
                else:
                    continue
                centre = (low + high) / 2.0
                lower = centre - target / 2.0
                upper = centre + target / 2.0
                setter((lower, upper) if high >= low else (upper, lower))
                changed = True
        if changed:
            self.canvas.draw_idle()
        return changed

    def release_zoom(self, event):
        super().release_zoom(event)
        self._enforce_zoom_limits()

    @staticmethod
    def _is_editable_line(line):
        """True for a real line, false for a point-only Line2D artist."""
        style = str(line.get_linestyle()).strip().lower()
        return style not in ('', 'none')

    @staticmethod
    def _coordinate_variable_name(ax, dimension, index):
        """Human label for one coordinate in a stack of twinned axes."""
        label = (ax.get_ylabel() if dimension == 'y'
                 else ax.get_xlabel()).strip()
        if label:
            return label
        custom = getattr(ax.figure, '_qcs_axes_names', {}).get(ax)
        if custom:
            return custom
        for line in ax.get_lines():
            candidate = line.get_label().strip()
            if candidate and not candidate.startswith('_'):
                return candidate
        return 'Plot %d' % (index + 1)

    @staticmethod
    def _hovered_line_values(event, axes):
        """Nearest actual Line2D value under the cursor, once per axes."""
        nearest = {}
        for index, ax in enumerate(axes):
            for line in ax.get_lines():
                marker = str(line.get_marker()).strip().lower()
                if (not line.get_visible() or
                        marker in ('', 'none', 'nothing')):
                    continue
                inside, details = line.contains(event)
                candidates = details.get('ind', ()) if inside else ()
                if not len(candidates):
                    continue
                xy = line.get_xydata()
                candidates = [int(item) for item in candidates
                              if 0 <= int(item) < len(xy)]
                if not candidates:
                    continue
                chosen = min(
                    candidates,
                    key=lambda item: sum((
                        ax.transData.transform(xy[item]) -
                        (event.x, event.y)) ** 2))
                x_value, y_value = xy[chosen]
                screen = ax.transData.transform((x_value, y_value))
                distance = float(sum((screen - (event.x, event.y)) ** 2))
                record = {
                    'ax': ax,
                    'index': index,
                    'distance': distance,
                    'x': x_value,
                    'y': y_value,
                }
                if (id(ax) not in nearest or
                        distance < nearest[id(ax)]['distance']):
                    nearest[id(ax)] = record
        return sorted(nearest.values(), key=lambda item: item['distance'])

    @staticmethod
    def _plain_number(value):
        """Readable decimal without scientific notation or false tail zeros."""
        number = float(value)
        if not math.isfinite(number):
            return ''
        if abs(number) < 5e-13:
            number = 0.0
        return format(number, '.12f').rstrip('0').rstrip('.')

    @staticmethod
    def _coordinate_value(ax, dimension, value, variable=''):
        """Use a full positional value for PAR; retain axes formatting else."""
        if re.search(r'\bPAR\b', variable, re.IGNORECASE):
            return format(float(value), '.0f')
        formatter = ax.format_ydata if dimension == 'y' else ax.format_xdata
        return formatter(value)

    @staticmethod
    def _edge_bin(edges, value):
        """Index of *value* inside monotonic pcolormesh cell edges."""
        edges = np.asarray(edges, dtype=float)
        if len(edges) < 2 or not np.isfinite(value):
            return None
        ascending = edges[-1] >= edges[0]
        search_edges = edges if ascending else -edges
        search_value = value if ascending else -value
        index = int(np.searchsorted(search_edges, search_value,
                                    side='right') - 1)
        if index == len(edges) - 1 and search_value == search_edges[-1]:
            index -= 1
        return index if 0 <= index < len(edges) - 1 else None

    @staticmethod
    def _hovered_doppler_message(event):
        """Read an actual current heatmap cell or vector under the cursor."""
        ax = event.inaxes
        if ax is None or event.xdata is None or event.ydata is None:
            return ''
        for item in reversed(ax.collections):
            if not item.get_visible():
                continue
            if isinstance(item, QuadMesh):
                coordinates = item.get_coordinates()
                if coordinates.ndim != 3:
                    continue
                x_index = QCSNavigationToolbar._edge_bin(
                    coordinates[0, :, 0], event.xdata)
                y_index = QCSNavigationToolbar._edge_bin(
                    coordinates[:, 0, 1], event.ydata)
                if x_index is None or y_index is None:
                    continue
                values = np.ma.asarray(item.get_array())
                rows = coordinates.shape[0] - 1
                columns = coordinates.shape[1] - 1
                if values.size != rows * columns:
                    continue
                value = values.reshape(rows, columns)[y_index, x_index]
                if np.ma.is_masked(value) or not np.isfinite(float(value)):
                    return ''
                name = item.get_label().removesuffix(' heatmap')
                if name == 'Horizontal speed':
                    name = 'Horizontal speed (cm/s)'
                elif name == 'Direction':
                    name = 'Direction (deg)'
                x_name = ax.get_xlabel().strip() or 'X'
                y_name = ax.get_ylabel().strip() or 'Y'
                return '%s: %s | %s: %s | %s: %s' % (
                    x_name, ax.format_xdata(event.xdata),
                    y_name, ax.format_ydata(event.ydata),
                    name, QCSNavigationToolbar._plain_number(value))
            if isinstance(item, Quiver):
                inside, details = item.contains(event)
                anchors = np.column_stack((item.X, item.Y))
                screen = ax.transData.transform(anchors)
                distances = np.sum(
                    (screen - np.array((event.x, event.y))) ** 2, axis=1)
                indices = details.get('ind', ()) if inside else ()
                if len(indices):
                    index = min(
                        (int(value) for value in indices),
                        key=lambda value: float(distances[value]))
                else:
                    index = int(np.argmin(distances))
                    if distances[index] > 8.0 ** 2:
                        continue
                x_value, y_value = anchors[index]
                return '%s: %s | %s: %s | East U (cm/s): %s | ' \
                       'North V (cm/s): %s' % (
                           ax.get_xlabel().strip() or 'X',
                           ax.format_xdata(x_value),
                           ax.get_ylabel().strip() or 'Y',
                           ax.format_ydata(y_value),
                           QCSNavigationToolbar._plain_number(item.U[index]),
                           QCSNavigationToolbar._plain_number(item.V[index]))
        return ''

    @staticmethod
    def _mouse_event_to_message(event):
        """Show only the plotted value(s) actually under the cursor."""
        ax = event.inaxes
        if ax is None or not ax.get_navigate():
            return ''
        doppler = QCSNavigationToolbar._hovered_doppler_message(event)
        if doppler:
            return doppler
        siblings = [item for item in ax.figure.axes
                    if item in ax._twinned_axes.get_siblings(ax)]
        try:
            shares_x = all(ax.get_shared_x_axes().joined(ax, item)
                           for item in siblings)
            shares_y = all(ax.get_shared_y_axes().joined(ax, item)
                           for item in siblings)
            hovered = QCSNavigationToolbar._hovered_line_values(
                event, siblings)
            if not hovered:
                return ''
            if len(siblings) == 1:
                item = hovered[0]
                x_name = ax.get_xlabel().strip() or 'X'
                y_name = QCSNavigationToolbar._coordinate_variable_name(
                    ax, 'y', 0)
                return '%s: %s | %s: %s' % (
                    x_name, ax.format_xdata(item['x']),
                    y_name, QCSNavigationToolbar._coordinate_value(
                        ax, 'y', item['y'], y_name))
            if shares_x:
                x_value = hovered[0]['x']
                fields = ['X: %s' % ax.format_xdata(x_value)]
                fields.extend(
                    '%s: %s' % (
                        QCSNavigationToolbar._coordinate_variable_name(
                            item['ax'], 'y', item['index']),
                        QCSNavigationToolbar._coordinate_value(
                            item['ax'], 'y', item['y'],
                            QCSNavigationToolbar._coordinate_variable_name(
                                item['ax'], 'y', item['index'])))
                    for item in hovered)
                return ' | '.join(fields)
            if shares_y:
                y_value = hovered[0]['y']
                fields = ['Y: %s' % ax.format_ydata(y_value)]
                fields.extend(
                    '%s: %s' % (
                        QCSNavigationToolbar._coordinate_variable_name(
                            item['ax'], 'x', item['index']),
                        QCSNavigationToolbar._coordinate_value(
                            item['ax'], 'x', item['x'],
                            QCSNavigationToolbar._coordinate_variable_name(
                                item['ax'], 'x', item['index'])))
                    for item in hovered)
                return ' | '.join(fields)
        except (TypeError, ValueError, OverflowError):
            return ''
        return NavigationToolbar2QT._mouse_event_to_message(event)

    @staticmethod
    def _capture_figure_options(ax):
        axes = {}
        for name, axis in ax._axis_map.items():
            axes[name] = {
                'limits': tuple(getattr(ax, 'get_%slim' % name)()),
                'label': axis.label.get_text(),
                'scale': axis.get_scale(),
            }
        lines = []
        for line in ax.get_lines():
            lines.append({
                'item': line,
                'editable': QCSNavigationToolbar._is_editable_line(line),
                'label': line.get_label(),
                'linestyle': line.get_linestyle(),
                'drawstyle': line.get_drawstyle(),
                'linewidth': line.get_linewidth(),
                'color': line.get_color(),
                'alpha': line.get_alpha(),
                'marker': line.get_marker(),
                'markersize': line.get_markersize(),
                'markerfacecolor': line.get_markerfacecolor(),
                'markeredgecolor': line.get_markeredgecolor(),
            })
        mappables = []
        for item in [*ax.images, *ax.collections]:
            if item.get_array() is None:
                continue
            values = {
                'item': item,
                'label': item.get_label(),
                'cmap': item.get_cmap(),
                'clim': item.get_clim(),
            }
            if hasattr(item, 'get_interpolation'):
                values['interpolation'] = item.get_interpolation()
                values['interpolation_stage'] = item.get_interpolation_stage()
            mappables.append(values)
        legend = ax.get_legend()
        legend_state = None
        if legend is not None:
            bbox = legend.get_bbox_to_anchor().transformed(
                ax.figure.transFigure.inverted())
            legend_state = {
                'loc': legend._loc,
                'bbox': Bbox.from_extents(*bbox.extents),
                'ncols': legend._ncols,
                'draggable': legend._draggable is not None,
                'frameon': legend.get_frame_on(),
            }
        return {
            'figure_title': (ax.figure._suptitle.get_text()
                             if ax.figure._suptitle is not None else ''),
            'title': ax.get_title(),
            'axes': axes,
            'lines': lines,
            'mappables': mappables,
            'legend': legend_state,
        }

    @staticmethod
    def _collect_legend_labels(ax):
        """Visible legend/key texts that Figure options can meaningfully edit."""
        records = []
        seen = set()

        def add(key, name, artist, kind, index=None, handle=None):
            if artist is None or id(artist) in seen:
                return
            records.append({
                'key': key,
                'name': name,
                'artist': artist,
                'kind': kind,
                'index': index,
                'handle': handle,
            })
            seen.add(id(artist))

        legend = ax.get_legend()
        if legend is not None:
            handles = getattr(legend, 'legend_handles', ())
            for index, artist in enumerate(legend.get_texts()):
                text = artist.get_text().strip()
                add(('legend', index),
                    'Entry %d%s' % (
                        index + 1, ' - ' + text if text else ''),
                    artist, 'legend', index,
                    handles[index] if index < len(handles) else None)
        for legend_index, figure_legend in enumerate(ax.figure.legends):
            handles = getattr(figure_legend, 'legend_handles', ())
            for index, artist in enumerate(figure_legend.get_texts()):
                text = artist.get_text().strip()
                add(('figure legend', legend_index, index),
                    'Figure entry %d%s' % (
                        index + 1, ' - ' + text if text else ''),
                    artist, 'figure legend', index,
                    handles[index] if index < len(handles) else None)
        metadata = getattr(ax.figure, '_qcs_legend_labels', {}).get(ax, [])
        for index, item in enumerate(metadata):
            add(('key', index, item['name']), item['name'], item['artist'],
                'key')
        for item in [*ax.images, *ax.collections]:
            colorbar = getattr(item, 'colorbar', None)
            if colorbar is None or not colorbar.ax.get_visible():
                continue
            axis = (colorbar.ax.xaxis if colorbar.orientation == 'horizontal'
                    else colorbar.ax.yaxis)
            artist = axis.label
            add(('colorbar', id(item)),
                artist.get_text() or 'Color scale', artist, 'key')
        return records

    @staticmethod
    def _legend_symbol_handle(record):
        """Return a legend-only Line2D-like handle that can show a symbol."""
        handle = record.get('handle')
        required = ('get_marker', 'set_marker', 'get_markersize',
                    'set_markersize', 'set_markerfacecolor',
                    'set_markeredgecolor')
        return handle if all(hasattr(handle, name) for name in required) else None

    @classmethod
    def _capture_legend_record(cls, record):
        """Capture text and legend-key style without touching plotted data."""
        values = {'text': record['artist'].get_text()}
        handle = cls._legend_symbol_handle(record)
        if handle is None:
            return values
        facecolor = handle.get_markerfacecolor()
        edgecolor = handle.get_markeredgecolor()
        color = facecolor
        if color is None or str(color).lower() in ('none', 'auto'):
            color = edgecolor
        if color is None or str(color).lower() in ('none', 'auto'):
            color = handle.get_color()
        values.update({
            'marker': handle.get_marker(),
            'color': mcolors.to_hex(mcolors.to_rgba(color)),
            'size': handle.get_markersize(),
            'facecolor': facecolor,
            'edgecolor': edgecolor,
        })
        return values

    @staticmethod
    def _set_color_button(button, color, mark_dirty=True,
                          update_alpha=False):
        """Store a valid Matplotlib RGB color and show it as a Qt swatch."""
        rgba = mcolors.to_rgba(color)
        if update_alpha and hasattr(button, '_qcs_alpha'):
            button._qcs_alpha = rgba[3]
        color = mcolors.to_hex(rgba)
        button._qcs_color = color
        rgb = mcolors.to_rgb(color)
        foreground = '#000000' if sum(rgb) > 1.55 else '#ffffff'
        button.setText(color.upper())
        button.setStyleSheet(
            'QPushButton { background-color: %s; color: %s; }' %
            (color, foreground))
        if mark_dirty and hasattr(button, '_qcs_legend_record'):
            button._qcs_legend_record['style_dirty'].add('color')

    @classmethod
    def _choose_color(cls, dialog, button):
        selected = QColorDialog.getColor(
            QColor(button._qcs_color), dialog,
            getattr(button, '_qcs_color_title', 'Select color'))
        if selected.isValid():
            cls._set_color_button(button, selected.name())

    @staticmethod
    def _set_legend_marker_combo(field, marker):
        marker = 'None' if marker in (None, '', ' ', 'None', 'none') else marker
        index = field.findData(marker)
        if index < 0:
            field.addItem('Custom (%s)' % marker, marker)
            index = field.count() - 1
        field.setCurrentIndex(index)

    @staticmethod
    def _set_form_values(form, values):
        """Put values into Matplotlib's private FormWidget without applying."""
        value_iter = iter(values)
        for index, (label, original) in enumerate(form.data):
            if label is None:
                continue
            value = next(value_iter)
            field = form.widgets[index]
            if isinstance(field, QPushButton) and hasattr(field, '_qcs_color'):
                QCSNavigationToolbar._set_color_button(
                    field, value, mark_dirty=False, update_alpha=True)
            elif hasattr(field, 'lineedit') and hasattr(field, 'colorbtn'):
                field.lineedit.setText(str(value))
                field.update_color()
            elif isinstance(field, QComboBox):
                choices = original
                if choices and isinstance(choices[0], (list, tuple)):
                    keys = [choice[0] for choice in choices]
                    texts = [str(choice[1]) for choice in choices]
                    if value in keys:
                        wanted = keys.index(value)
                    elif value in (None, '', ' ', 'None', 'none'):
                        wanted = next(
                            (item for item, choice in enumerate(choices)
                             if (choice[0] in ('', ' ', 'None', 'none') or
                                 str(choice[1]).lower() == 'nothing')), 0)
                    else:
                        shown = str(value)
                        wanted = (texts.index(shown)
                                  if shown in texts else 0)
                else:
                    texts = [str(choice) for choice in choices]
                    shown = str(value)
                    wanted = texts.index(shown) if shown in texts else 0
                field.setCurrentIndex(wanted)
            elif isinstance(field, QCheckBox):
                field.setChecked(bool(value))
            elif hasattr(field, 'setDateTime'):
                if isinstance(value, Real):
                    value = mdates.num2date(value)
                field.setDateTime(value)
            elif hasattr(field, 'setDate'):
                field.setDate(value)
            elif isinstance(field, QLineEdit):
                field.setText(
                    repr(float(value)) if field.validator() else str(value))
            elif hasattr(field, 'setValue'):
                field.setValue(value)

    @staticmethod
    def _form_widget_value(field):
        """Capture one editable Figure-options widget without applying it."""
        if isinstance(field, QPushButton) and hasattr(field, '_qcs_color'):
            return 'qcs_color', (
                field._qcs_color, getattr(field, '_qcs_alpha', None))
        if hasattr(field, 'lineedit') and hasattr(field, 'colorbtn'):
            return 'color', field.lineedit.text()
        if isinstance(field, QComboBox):
            return 'combo', field.currentIndex()
        if isinstance(field, QCheckBox):
            return 'check', field.isChecked()
        if isinstance(field, QLineEdit):
            return 'text', field.text()
        if hasattr(field, 'dateTime') and hasattr(field, 'setDateTime'):
            return 'datetime', field.dateTime()
        if hasattr(field, 'date') and hasattr(field, 'setDate'):
            return 'date', field.date()
        if hasattr(field, 'value') and hasattr(field, 'setValue'):
            return 'value', field.value()
        return None

    @staticmethod
    def _restore_form_widget_value(field, state):
        """Restore one captured Figure-options field, still form-only."""
        kind, value = state
        if kind == 'color':
            field.lineedit.setText(value)
            field.update_color()
        elif kind == 'combo':
            field.setCurrentIndex(value)
        elif kind == 'check':
            field.setChecked(value)
        elif kind == 'text':
            field.setText(value)
        elif kind == 'datetime':
            field.setDateTime(value)
        elif kind == 'date':
            field.setDate(value)
        elif kind == 'value':
            field.setValue(value)
        elif kind == 'qcs_color':
            color, alpha = value
            QCSNavigationToolbar._set_color_button(
                field, color, mark_dirty=False)
            if alpha is not None:
                field._qcs_alpha = alpha

    def _figure_option_form_rows(self, dialog):
        """All Figure-options value rows and whether each is user-visible."""
        rows = []
        seen = set()
        hidden_fields = getattr(dialog, '_qcs_hidden_option_fields', set())
        for form in dialog.findChildren(QFormLayout):
            for row in range(form.rowCount()):
                item = form.itemAt(row, QFormLayout.ItemRole.FieldRole)
                field = item.widget() if item is not None else None
                if field is None or id(field) in seen:
                    continue
                state = self._form_widget_value(field)
                if state is None:
                    continue
                seen.add(id(field))
                label_item = form.itemAt(
                    row, QFormLayout.ItemRole.LabelRole)
                label = label_item.widget() if label_item is not None else None
                label_text = label.text() if isinstance(label, QLabel) else ''
                label_text = re.sub('<[^>]+>', '', label_text).strip()
                rows.append({
                    'form': form,
                    'row': row,
                    'field': field,
                    'label': label_text,
                    # Runtime visibility is false for new rows and for every
                    # inactive tab. Only fields deliberately suppressed by the
                    # QCS adapter are excluded from per-row reset actions.
                    'visible': field not in hidden_fields,
                })
        return rows

    def _reset_one_figure_option(self, dialog, field, state):
        """Refill one product default; Apply remains the mutation step."""
        self._restore_form_widget_value(field, state)
        axis_name = getattr(dialog, '_qcs_axis_limit_fields', {}).get(field)
        if axis_name is not None:
            dialog._qcs_dirty_axis_limits.add(axis_name)
        for record in getattr(dialog, '_qcs_legend_records', []):
            if field in record.get('widgets', (record.get('field'),)):
                record['dirty'] = True
                if field is not record.get('field'):
                    style_fields = {
                        record.get('marker_field'): 'marker',
                        record.get('color_field'): 'color',
                        record.get('size_field'): 'size',
                    }
                    record['style_dirty'].add(style_fields[field])
                    record['restore_style'] = False
                break
        dialog.update_buttons()

    @staticmethod
    def _title_group_axes(ax):
        """Overlaid parameter axes share one visible plot title."""
        siblings = ax._twinned_axes.get_siblings(ax)
        return [item for item in ax.figure.axes
                if item in siblings and item.get_visible()]

    def _shared_plot_title(self, ax, defaults=False):
        for item in self._title_group_axes(ax):
            if defaults:
                state = self._figure_option_defaults.get(item)
                title = state['title'].strip() if state is not None else ''
            else:
                title = item.get_title().strip()
            if title:
                return title
        return ''

    def _apply_shared_plot_title(self, ax, title):
        group = self._title_group_axes(ax)
        owner = group[0] if group else ax
        for item in group or [ax]:
            item.set_title(title if item is owner else '')

    def _install_figure_option_row_resets(self, dialog, ax):
        """Add the Settings-style reset arrow to every editable visible row."""
        rows = self._figure_option_form_rows(dialog)
        current = {
            record['field']: self._form_widget_value(record['field'])
            for record in rows
        }
        legend_dirty = {
            record['key']: (
                record['dirty'], set(record.get('style_dirty', ())),
                record.get('restore_style', False))
            for record in getattr(dialog, '_qcs_legend_records', [])
        }
        self._reset_figure_options_form(dialog, ax)
        defaults = {
            record['field']: self._form_widget_value(record['field'])
            for record in rows
        }
        for field, state in current.items():
            self._restore_form_widget_value(field, state)
        for record in getattr(dialog, '_qcs_legend_records', []):
            (record['dirty'], record['style_dirty'],
             record['restore_style']) = legend_dirty[record['key']]
        dialog.update_buttons()

        installed = []
        for record in rows:
            if not record['visible'] or not record['label']:
                continue
            field = record['field']
            form = record['form']
            row = record['row']
            holder = QWidget()
            layout = QHBoxLayout(holder)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(4)
            form.removeWidget(field)
            layout.addWidget(field, 1)
            button = _row_reset_button(
                'Restore the original %s.' % record['label'].lower(),
                lambda _checked=False, widget=field, value=defaults[field]:
                self._reset_one_figure_option(dialog, widget, value))
            layout.addWidget(button)
            form.setWidget(row, QFormLayout.ItemRole.FieldRole, holder)
            installed.append({**record, 'button': button})
        dialog._qcs_row_reset_buttons = installed

    def _reset_figure_options_form(self, dialog, ax, preserve_view=False):
        """Refill product defaults; Apply remains the only mutation step."""
        state = self._figure_option_defaults[ax]
        axes_values = [self._shared_plot_title(ax, defaults=True)]
        for name in ax._axis_map:
            values = state['axes'][name]
            limits = (getattr(ax, 'get_%slim' % name)()
                      if preserve_view else values['limits'])
            axes_values.extend([
                *limits, values['label'], values['scale']])

        tabs = dialog.formwidget.tabwidget
        tab_forms = {
            tabs.tabText(index): dialog.formwidget.widgetlist[index]
            for index in range(len(dialog.formwidget.widgetlist))
        }
        self._set_form_values(tab_forms['Axes'], axes_values)
        dialog._qcs_figure_title.setText(state['figure_title'])
        datetime_fields = getattr(dialog, '_qcs_datetime_fields', None)
        if datetime_fields is not None:
            if preserve_view:
                lower, upper = dbv.normalized_time_bounds(
                    *(mdates.num2date(value)
                      for value in sorted(ax.get_xlim())))
                available_start, available_end = dialog._qcs_datetime_bounds
                if upper < available_start or lower > available_end:
                    lower, upper = available_start, available_end
                else:
                    lower = max(lower, available_start)
                    upper = min(upper, available_end)
            else:
                lower, upper = dialog._qcs_datetime_bounds
            datetime_fields[0].setText(lower.strftime(dbv.TIME_TEXT_FORMAT))
            datetime_fields[1].setText(upper.strftime(dbv.TIME_TEXT_FORMAT))

        curve_states = [
            values for values in state['lines']
            if values['editable'] and values['label'] != '_nolegend_'
        ]
        curves = tab_forms.get('Lines') or tab_forms.get('Curves')
        if curves is not None:
            for form, values in zip(
                    curves.widgetlist, curve_states, strict=True):
                color = mcolors.to_hex(mcolors.to_rgba(
                    values['color'], values['alpha']), keep_alpha=True)
                face = mcolors.to_hex(mcolors.to_rgba(
                    values['markerfacecolor'], values['alpha']),
                    keep_alpha=True)
                edge = mcolors.to_hex(mcolors.to_rgba(
                    values['markeredgecolor'], values['alpha']),
                    keep_alpha=True)
                self._set_form_values(form, [
                    values['label'], values['linestyle'],
                    values['drawstyle'], values['linewidth'], color,
                    values['marker'], values['markersize'], face, edge])

        graphs = tab_forms.get('Graphs')
        if graphs is not None:
            graph_states = [
                values for values in state['mappables']
                if values['label'] != '_nolegend_'
            ]
            for form, values in zip(
                    graphs.widgetlist, graph_states, strict=True):
                graph_values = [
                    values['label'], values['cmap'].name, *values['clim']]
                if 'interpolation' in values:
                    graph_values.extend([
                        values['interpolation'],
                        values['interpolation_stage']])
                self._set_form_values(form, graph_values)

        for record in getattr(dialog, '_qcs_legend_records', []):
            default = self._legend_defaults.get(ax, {}).get(
                record['key'], {'text': record['artist'].get_text()})
            record['field'].setText(default['text'])
            if 'marker' in default and 'marker_field' in record:
                self._set_legend_marker_combo(
                    record['marker_field'], default['marker'])
                self._set_color_button(
                    record['color_field'], default['color'], mark_dirty=False)
                record['size_field'].setValue(default['size'])
                record['style_dirty'] = {'marker', 'color', 'size'}
                record['restore_style'] = True
            record['dirty'] = True
        dialog.update_buttons()

    def _configure_datetime_x_options(self, dialog, ax):
        """Use readable text controls for the selected product time range."""
        converter = ax.xaxis.get_converter()
        converter_name = type(converter).__name__.lower()
        if (converter is None or 'date' not in converter_name or
                'converter' not in converter_name):
            return False
        general = dialog.formwidget.widgetlist[0]
        state = self._figure_option_defaults[ax]
        lower, upper = sorted(state['axes']['x']['limits'])
        available_start, available_end = dbv.normalized_time_bounds(
            mdates.num2date(lower), mdates.num2date(upper))
        x_section = False
        header_row = None
        min_position = max_position = None
        axis_label_row = None
        hidden_fields = getattr(dialog, '_qcs_hidden_option_fields', set())
        dialog._qcs_hidden_option_fields = hidden_fields
        for row, (label, value) in enumerate(general.data):
            if label is None and value == '<b>X-Axis</b>':
                x_section = True
                header_row = row
                heading = general.formlayout.itemAt(
                    row, QFormLayout.ItemRole.SpanningRole)
                if heading is not None and heading.widget() is not None:
                    heading.widget().setText('<b>Date/time range</b>')
                continue
            if not x_section:
                continue
            if label is None and value is None:
                general.formlayout.setRowVisible(row, False)
                break
            value_position = sum(
                item_label is not None
                for item_label, _item_value in general.data[:row])
            if label == 'Min':
                min_position = value_position
            elif label == 'Max':
                max_position = value_position
            field = general.widgets[row]
            if label == 'Label':
                axis_label_row = row
                field.setToolTip(
                    'Edit the X-axis label, such as Datetime.')
            else:
                general.formlayout.setRowVisible(row, False)
                hidden_fields.add(field)

        if (header_row is None or min_position is None or
                max_position is None or axis_label_row is None):
            return False

        axis_label = general.formlayout.takeRow(axis_label_row)
        axis_label_widget = axis_label.fieldItem.widget()
        axis_label_caption = axis_label.labelItem.widget()
        axis_label_caption.setText('Axis label')

        current_lower, current_upper = sorted(ax.get_xlim())
        current_lower, current_upper = dbv.normalized_time_bounds(
            mdates.num2date(current_lower), mdates.num2date(current_upper))
        current_lower = max(current_lower, available_start)
        current_upper = min(current_upper, available_end)
        start_field = QLineEdit()
        end_field = QLineEdit()
        for field, value in (
                (start_field, current_lower), (end_field, current_upper)):
            field.setInputMask('00/00/0000 00:00;_')
            field.setText(value.strftime(dbv.TIME_TEXT_FORMAT))
            field.setToolTip(
                'Edit as DD/MM/YYYY HH:MM. Both values must stay inside the '
                'selected calendar interval shown below.')
        available = QLabel(
            'From %s to %s' % (
                available_start.strftime('%d/%m/%Y %H:%M'),
                available_end.strftime('%d/%m/%Y %H:%M')))
        available.setToolTip(
            'Calendar domain established by the Data Visualization year and '
            'Time window selection.')
        general.formlayout.insertRow(header_row + 1, 'Start', start_field)
        general.formlayout.insertRow(header_row + 2, 'End', end_field)
        general.formlayout.insertRow(
            header_row + 3, axis_label_caption, axis_label_widget)
        general.formlayout.insertRow(header_row + 4, 'Available', available)
        dialog._qcs_datetime_fields = (start_field, end_field)
        dialog._qcs_datetime_data_positions = (min_position, max_position)
        dialog._qcs_datetime_bounds = (available_start, available_end)
        dialog._qcs_datetime_available = available
        return True

    @staticmethod
    def _datetime_form_values(dialog, show_error=True):
        fields = getattr(dialog, '_qcs_datetime_fields', None)
        if fields is None:
            return ()
        available_start, available_end = dialog._qcs_datetime_bounds
        try:
            return dbv.validate_time_window_texts(
                fields[0].text(), fields[1].text(),
                available_start, available_end)
        except ValueError:
            if show_error:
                QMessageBox.critical(
                    dialog, 'Invalid date/time range',
                    dbv.time_window_error_message(
                        available_start, available_end))
            return None

    @staticmethod
    def _hide_graph_names(dialog):
        """Mappable labels are metadata, not the visible color-key title."""
        tabs = dialog.formwidget.tabwidget
        hidden_fields = getattr(dialog, '_qcs_hidden_option_fields', set())
        dialog._qcs_hidden_option_fields = hidden_fields
        for index in range(len(dialog.formwidget.widgetlist)):
            if tabs.tabText(index) != 'Graphs':
                continue
            graphs = dialog.formwidget.widgetlist[index]
            if len(graphs.widgetlist) == 1:
                graphs.combobox.hide()
            else:
                graphs.combobox.setToolTip(
                    'Select the graph element to customize.')
            for form in graphs.widgetlist:
                for row, (label, _value) in enumerate(form.data):
                    if label == 'Label':
                        form.formlayout.setRowVisible(row, False)
                        hidden_fields.add(form.widgets[row])
                        break

    @classmethod
    def _configure_line_options(cls, dialog, ax):
        """Expose line styling only; points and legend text have other roles."""
        tabs = dialog.formwidget.tabwidget
        hidden_fields = getattr(dialog, '_qcs_hidden_option_fields', set())
        dialog._qcs_hidden_option_fields = hidden_fields
        for index in range(len(dialog.formwidget.widgetlist)):
            if tabs.tabText(index) != 'Curves':
                continue
            tabs.setTabText(index, 'Lines')
            curves = dialog.formwidget.widgetlist[index]
            metadata = getattr(ax.figure, '_qcs_line_names', {})
            names = []
            occurrences = {}
            for line_number, line in enumerate(ax.get_lines(), start=1):
                if (line.get_label() == '_nolegend_' or
                        not cls._is_editable_line(line)):
                    continue
                label = str(metadata.get(line, line.get_label())).strip()
                if not label or label.startswith('_'):
                    label = 'Line %d' % line_number
                occurrences[label] = occurrences.get(label, 0) + 1
                suffix = occurrences[label]
                names.append(label if suffix == 1 else '%s (%d)' % (label, suffix))
            if len(names) == len(curves.widgetlist):
                curves.combobox.clear()
                curves.combobox.addItems(names)
            else:
                fallback = []
                for item in range(curves.combobox.count()):
                    label = curves.combobox.itemText(item).strip()
                    fallback.append(
                        label if label and not label.startswith('_')
                        else 'Line %d' % (item + 1))
                curves.combobox.clear()
                curves.combobox.addItems(fallback)
            if len(curves.widgetlist) == 1:
                curves.combobox.hide()
            else:
                curves.combobox.setToolTip(
                    'Select a named plotted line to customize. Site and '
                    'source-product names distinguish deployments.')
            for form in curves.widgetlist:
                marker_section = False
                for row, (label, value) in enumerate(form.data):
                    if label is None and value == '<b>Marker</b>':
                        marker_section = True
                    hide = (label in ('Label', 'Draw style') or
                            marker_section)
                    if hide:
                        form.formlayout.setRowVisible(row, False)
                        field = form.widgets[row]
                        if field is not None:
                            hidden_fields.add(field)
                    if label == 'Color (RGBA)':
                        original = form.widgets[row]
                        rgba = mcolors.to_rgba(original.lineedit.text())
                        color = _QCSColorButton(rgba[3])
                        color._qcs_color_title = 'Select line color'
                        cls._set_color_button(
                            color, rgba, mark_dirty=False, update_alpha=True)
                        color.setToolTip(
                            'Choose the line color. The product opacity is '
                            'preserved automatically.')
                        color.clicked.connect(
                            lambda _checked=False, button=color:
                            cls._choose_color(dialog, button))
                        label_item = form.formlayout.itemAt(
                            row, QFormLayout.ItemRole.LabelRole)
                        original.lineedit.hide()
                        original.colorbtn.hide()
                        form.formlayout.removeItem(original)
                        form.formlayout.setWidget(
                            row, QFormLayout.ItemRole.FieldRole, color)
                        if (label_item is not None and
                                label_item.widget() is not None):
                            label_item.widget().setText('Color')
                        form.widgets[row] = color
                        color._qcs_upstream_color_layout = original
                    if label != 'Line style':
                        continue
                    field = form.widgets[row]
                    choices = form.data[row][1]
                    selected = choices[field.currentIndex()][0]
                    priority = {
                        'Solid': 0, 'Dashed': 1, 'Dotted': 2,
                        'DashDot': 3, 'None': 4,
                    }
                    choices.sort(key=lambda choice: (
                        priority.get(choice[1], 99), choice[1]))
                    field.clear()
                    field.addItems([choice[1] for choice in choices])
                    selected_index = next(
                        (item for item, choice in enumerate(choices)
                         if choice[0] == selected), 0)
                    field.setCurrentIndex(selected_index)

    @staticmethod
    def _capitalize_scale_options(dialog):
        """Keep Matplotlib scale keys while presenting sentence-case names."""
        general = dialog.formwidget.widgetlist[0]
        for row, (label, choices) in enumerate(general.data):
            if label != 'Scale':
                continue
            field = general.widgets[row]
            for index, choice in enumerate(choices):
                shown = choice[1] if isinstance(choice, (tuple, list)) else choice
                field.setItemText(index, str(shown).capitalize())

    def _track_axis_limit_edits(self, dialog, ax):
        """Distinguish an edited range from a stale non-modal form value."""
        general = dialog.formwidget.widgetlist[0]
        positions = {}
        fields = {}
        axis_name = None
        value_position = 0
        for row, (label, value) in enumerate(general.data):
            if label is None and isinstance(value, str):
                match = re.fullmatch(r'<b>(.+)-Axis</b>', value)
                if match:
                    axis_name = match.group(1).lower()
            elif label is not None:
                if axis_name in ax._axis_map and label in ('Min', 'Max'):
                    positions.setdefault(axis_name, {})[label] = value_position
                    fields.setdefault(axis_name, {})[label] = general.widgets[row]
                value_position += 1
        datetime_fields = getattr(dialog, '_qcs_datetime_fields', None)
        if datetime_fields is not None and 'x' in fields:
            fields['x'] = {'Min': datetime_fields[0], 'Max': datetime_fields[1]}
        dialog._qcs_axis_limit_positions = {
            name: (items['Min'], items['Max'])
            for name, items in positions.items()
            if 'Min' in items and 'Max' in items
        }
        dialog._qcs_axis_limit_fields = {}
        dialog._qcs_dirty_axis_limits = set()
        for name, items in fields.items():
            for field in items.values():
                dialog._qcs_axis_limit_fields[field] = name
                if isinstance(field, QLineEdit):
                    field.textEdited.connect(
                        lambda _text, axis=name:
                        dialog._qcs_dirty_axis_limits.add(axis))

    def _add_legends_tab(self, dialog, ax):
        tabs = dialog.formwidget.tabwidget
        records = self._collect_legend_labels(ax)
        dialog._qcs_legend_records = records
        if records:
            content = QWidget()
            layout = QVBoxLayout(content)
            for record in records:
                group = QGroupBox(record['name'])
                form = QFormLayout(group)
                field = QLineEdit(record['artist'].get_text())
                field.setToolTip(
                    'Edit the text displayed for this legend or key entry.')
                record['field'] = field
                record['widgets'] = [field]
                record['dirty'] = False
                record['style_dirty'] = set()
                record['restore_style'] = False
                field.textEdited.connect(
                    lambda _text, item=record:
                    item.__setitem__('dirty', True))
                form.addRow('Text', field)
                handle = self._legend_symbol_handle(record)
                if handle is not None:
                    marker = QComboBox()
                    for label, value in (
                            ('(None)', 'None'), ('Circle', 'o'),
                            ('Dot', '.'), ('Square', 's'),
                            ('Triangle up', '^'),
                            ('Triangle down', 'v'), ('Diamond', 'D'),
                            ('Plus', '+'), ('Cross', 'x'), ('Star', '*')):
                        marker.addItem(label, value)
                    self._set_legend_marker_combo(marker, handle.get_marker())
                    marker.setToolTip(
                        'Change the symbol in this legend key only; plotted '
                        'data are not changed.')
                    color = QPushButton()
                    source_color = self._legend_defaults[ax][
                        record['key']]['color']
                    self._set_color_button(
                        color, source_color, mark_dirty=False)
                    color._qcs_color_title = 'Select symbol color'
                    color._qcs_legend_record = record
                    color.setToolTip(
                        'Choose the symbol color in this legend key only.')
                    color.clicked.connect(
                        lambda _checked=False, button=color:
                        self._choose_color(dialog, button))
                    size = QDoubleSpinBox()
                    size.setRange(0.1, 100.0)
                    size.setDecimals(1)
                    size.setSingleStep(0.5)
                    size.setValue(handle.get_markersize())
                    size.setSuffix(' pt')
                    size.setToolTip(
                        'Change the symbol size in this legend key only.')
                    record.update({
                        'marker_field': marker,
                        'color_field': color,
                        'size_field': size,
                    })
                    marker.currentIndexChanged.connect(
                        lambda _index, item=record:
                        item['style_dirty'].add('marker'))
                    size.valueChanged.connect(
                        lambda _value, item=record:
                        item['style_dirty'].add('size'))
                    record['widgets'].extend((marker, color, size))
                    form.addRow('Symbol', marker)
                    form.addRow('Symbol color', color)
                    form.addRow('Symbol size', size)
                layout.addWidget(group)
            layout.addStretch(1)
            page = QScrollArea()
            page.setWidgetResizable(True)
            page.setWidget(content)
            tabs.addTab(page, 'Legends')

        # Keep the mappable forms available for the safe color-limit update in
        # the Apply wrapper below. Visible text belongs to the Legends tab.
        graph_widget = None
        for index in range(len(dialog.formwidget.widgetlist)):
            if tabs.tabText(index) == 'Graphs':
                graph_widget = dialog.formwidget.widgetlist[index]

        original_apply = dialog.apply_callback

        def apply_with_legends(data):
            datetime_fields = getattr(dialog, '_qcs_datetime_fields', None)
            if (datetime_fields is not None and
                    'x' in dialog._qcs_dirty_axis_limits):
                datetime_values = self._datetime_form_values(dialog)
                if datetime_values is None:
                    return
                min_position, max_position = \
                    dialog._qcs_datetime_data_positions
                data[0][min_position] = mdates.date2num(
                    datetime_values[0].to_pydatetime())
                data[0][max_position] = mdates.date2num(
                    datetime_values[1].to_pydatetime())
            # Figure options is non-modal.  A wheel/toolbar zoom can therefore
            # change the live view while the dialog remains open; untouched
            # Min/Max fields are stale and must not overwrite that newer view.
            for name, positions in dialog._qcs_axis_limit_positions.items():
                if name in dialog._qcs_dirty_axis_limits:
                    continue
                limits = getattr(ax, 'get_%slim' % name)()
                data[0][positions[0]], data[0][positions[1]] = limits
            # The upstream Matplotlib callback has one positional boolean at
            # the end of the Axes form. QCS has no automatic-regeneration
            # feature, field or saved state; the adapter always disables it.
            data[0].append(False)
            # Matplotlib sets vmin and vmax in two callback-emitting steps. If
            # the requested range sits wholly above/below the current one, the
            # attached colorbar can clamp the first endpoint. Expand once to
            # the union so the normal callback can then reach both exact values.
            if graph_widget is not None:
                graph_values = [form.get()
                                for form in graph_widget.widgetlist]
                graph_items = [
                    item for item in [*ax.images, *ax.collections]
                    if item.get_array() is not None and
                    item.get_label() != '_nolegend_'
                ]
                for item, values in zip(
                        graph_items, graph_values, strict=True):
                    low, high = sorted(values[2:4])
                    current_low, current_high = item.get_clim()
                    norm = item.norm
                    with norm.callbacks.blocked():
                        norm.vmin = min(current_low, low)
                        norm.vmax = max(current_high, high)
                    item.changed()
            original_apply(data)
            self._apply_shared_plot_title(
                ax, dialog._qcs_plot_title.text())
            figure_title = dialog._qcs_figure_title.text()
            if ax.figure._suptitle is None:
                if figure_title:
                    ax.figure.suptitle(figure_title)
            else:
                ax.figure._suptitle.set_text(figure_title)
            for record in records:
                record['artist'].set_text(record['field'].text())
                handle = self._legend_symbol_handle(record)
                if (handle is not None and 'marker_field' in record and
                        record['style_dirty']):
                    default = self._legend_defaults[ax][record['key']]
                    if record['restore_style']:
                        handle.set_marker(default['marker'])
                        handle.set_markersize(default['size'])
                        handle.set_markerfacecolor(default['facecolor'])
                        handle.set_markeredgecolor(default['edgecolor'])
                    else:
                        if 'marker' in record['style_dirty']:
                            marker = record['marker_field'].currentData()
                            handle.set_marker(
                                '' if marker == 'None' else marker)
                        if 'size' in record['style_dirty']:
                            handle.set_markersize(
                                record['size_field'].value())
                        if 'color' in record['style_dirty']:
                            color = record['color_field']._qcs_color
                            handle.set_markerfacecolor(color)
                            handle.set_markeredgecolor(color)
                    record['style_dirty'].clear()
                    record['restore_style'] = False
                record['dirty'] = False
            dialog._qcs_dirty_axis_limits.clear()
            ax.figure.canvas.draw_idle()

        dialog.apply_callback = apply_with_legends

    def _prepare_figure_options_dialog(self, dialog, ax, can_go_back=False,
                                       plot_name=None):
        dialog.setWindowIcon(self._actions['edit_parameters'].icon())
        dialog.setWindowTitle(
            'Figure options - %s' % (
                plot_name or _axes_display_name(ax, 0)))
        tabs = dialog.formwidget.tabwidget
        for index in range(tabs.count()):
            if tabs.tabText(index) == 'Images, etc.':
                tabs.setTabText(index, 'Graphs')
        general = dialog.formwidget.widgetlist[0]
        for row, (label, _value) in enumerate(general.data):
            if label == 'Title':
                general.widgets[row].setText(self._shared_plot_title(ax))
                dialog._qcs_plot_title = general.widgets[row]
                title_label = general.formlayout.labelForField(
                    general.widgets[row])
                if title_label is not None:
                    title_label.setText('Plot title')
                break
        for row, (label, _value) in enumerate(general.data):
            if label != '(Re-)Generate automatic legend':
                continue
            field = general.widgets[row]
            general.formlayout.removeRow(field)
            general.data.pop(row)
            general.widgets.pop(row)
            break
        self._configure_datetime_x_options(dialog, ax)
        self._capitalize_scale_options(dialog)
        figure_title = QLineEdit(
            ax.figure._suptitle.get_text()
            if ax.figure._suptitle is not None else '')
        figure_title.setToolTip(
            'Edit the title shown above the complete figure.')
        general.formlayout.insertRow(0, 'Figure title', figure_title)
        dialog._qcs_figure_title = figure_title
        self._configure_line_options(dialog, ax)
        self._hide_graph_names(dialog)
        self._add_legends_tab(dialog, ax)
        self._track_axis_limit_edits(dialog, ax)

        dialog.layout().removeWidget(dialog.bbox)
        dialog.bbox.hide()
        button_row = QHBoxLayout()
        button_row.addStretch(1)
        buttons = {
            'back': QPushButton('< Back'),
            'reset': QPushButton('Reset values'),
            'apply': QPushButton('Apply'),
            'ok': QPushButton('OK'),
        }
        button_width = max(
            108, *(button.sizeHint().width() for button in buttons.values()))
        for button in buttons.values():
            button.setFixedWidth(button_width)
            button.setAutoDefault(False)
            button_row.addWidget(button)
        button_row.addStretch(1)
        dialog.layout().addLayout(button_row)
        dialog._qcs_buttons = buttons
        buttons['back'].setEnabled(can_go_back)
        buttons['back'].setToolTip(
            'Return to plot selection.' if can_go_back
            else 'This figure has only one customizable plot.')
        buttons['ok'].setDefault(True)
        buttons['back'].clicked.connect(
            lambda: self._return_to_customize_picker(dialog))
        reset = buttons['reset']
        reset.setToolTip(
            'Refill the original figure values without changing the current '
            'zoom or position; use Apply to confirm them.')
        def reset_all_values():
            self._reset_figure_options_form(dialog, ax, preserve_view=True)
            dialog._qcs_dirty_axis_limits.clear()

        reset.clicked.connect(reset_all_values)

        def apply_checked():
            if ('x' not in dialog._qcs_dirty_axis_limits or
                    self._datetime_form_values(dialog) is not None):
                dialog.apply()

        def accept_checked():
            if ('x' in dialog._qcs_dirty_axis_limits and
                    self._datetime_form_values(dialog) is None):
                return
            dialog.apply()
            QDialog.accept(dialog)

        buttons['apply'].clicked.connect(apply_checked)
        buttons['ok'].clicked.connect(accept_checked)

        def update_buttons():
            valid = all(field.hasAcceptableInput()
                        for field in dialog.float_fields)
            valid = valid and all(
                field.hasAcceptableInput() for field in
                getattr(dialog, '_qcs_datetime_fields', ()))
            buttons['apply'].setEnabled(valid)
            buttons['ok'].setEnabled(valid)

        dialog.update_buttons = update_buttons
        update_buttons()
        self._install_figure_option_row_resets(dialog, ax)
        qtheme.enable_clear_buttons(dialog)

    def _return_to_customize_picker(self, dialog):
        dialog.reject()
        QTimer.singleShot(0, self.edit_parameters)

    def _open_figure_options(self, ax, can_go_back=False, plot_name=None):
        self._figure_option_defaults.setdefault(
            ax, self._capture_figure_options(ax))
        point_labels = []
        for line in ax.get_lines():
            if (line.get_label() != '_nolegend_' and
                    not self._is_editable_line(line)):
                point_labels.append((line, line.get_label()))
                line.set_label('_nolegend_')
        try:
            figureoptions.figure_edit(ax, self)
        finally:
            for line, label in point_labels:
                line.set_label(label)
        dialog = getattr(self, '_fedit_dialog', None)
        if dialog is not None:
            self._prepare_figure_options_dialog(
                dialog, ax, can_go_back=can_go_back,
                plot_name=plot_name)
        return dialog

    def edit_parameters(self):
        self._deactivate_navigation_mode()
        figure = self.canvas.figure
        configured = getattr(figure, '_qcs_customize_axes', None)
        if configured is not None:
            choices = [(name, ax) for name, ax in configured
                       if ax in figure.axes and ax.get_visible()]
        else:
            axes = [ax for ax in figure.get_axes()
                    if ax.get_visible() and ax.get_label() != '<colorbar>']
            names = _unique_axes_names(axes)
            choices = list(zip(names, axes, strict=True))
        if not choices:
            QMessageBox.warning(
                self.canvas.parent(), 'Error', 'There are no plots to edit.')
            return
        if len(choices) == 1:
            plot_name, ax = choices[0]
        else:
            names = [name for name, _ in choices]
            picker = QInputDialog(self.canvas.parent())
            picker.setWindowTitle('Customize')
            picker.setWindowIcon(
                self._actions['edit_parameters'].icon())
            picker.setLabelText('Select plot:')
            picker.setComboBoxItems(names)
            picker.setComboBoxEditable(False)
            if picker.exec() != QDialog.DialogCode.Accepted:
                return
            item = picker.textValue()
            plot_name = item
            ax = choices[names.index(item)][1]
        self._open_figure_options(
            ax, can_go_back=len(choices) > 1, plot_name=plot_name)

    def configure_subplots(self):
        self._deactivate_navigation_mode()
        if self._subplot_dialog is None:
            self._subplot_dialog = QCSSubplotToolQt(
                self.canvas.figure, self.canvas.parent(),
                self._actions['configure_subplots'].icon())
            self.canvas.mpl_connect(
                'close_event', lambda _event: self._subplot_dialog.reject())
        self._subplot_dialog.update_from_current_subplotpars()
        self._subplot_dialog.setModal(True)
        self._subplot_dialog.show()
        return self._subplot_dialog


def _prime_toolbar(fig, toolbar):
    """Prime the opening view used by Home in the QCS navigation toolbar.

    Back/Forward are intentionally absent: they tracked only toolbar Pan/Zoom,
    not the wheel and middle-button interactions used throughout QCS.
    """
    try:
        toolbar.push_current()
    except Exception:
        pass


class PlotWindow(QWidget):
    """The window a matplotlib figure is shown in.

    Under Agg the backend has no window of its own, so the shell builds one:
    canvas, navigation toolbar, the app icon and a real title. Closing works in
    BOTH directions - closing the window fires matplotlib's `close_event`,
    which is what the pipeline's waits are connected to, and a `plt.close(fig)`
    from the pipeline (Done / Skip / Cancel all call it) closes the window.

    A plain QWidget, not a QDialog: a dialog swallows Esc and Enter, and the
    manual point cut binds both (Enter = done, Esc = cancel the whole run).
    """

    _open = []          # non-modal windows, kept referenced against the GC
    _windows = []       # every window on screen, watched by the timer below
    _watch = None       # one QTimer for all of them

    # Under Agg, plt.close(fig) fires NOTHING: FigureManagerBase.destroy() is a
    # no-op (matplotlib 3.10, read), unlike the Qt manager, whose destroy closes
    # its window and emits close_event. The pipeline ends every review with
    # plt.close(fig) - Done, Skip and Cancel all do - so the window has to
    # notice by itself that its figure left pyplot. One timer serves every open
    # window; it runs only while at least one is on screen.

    @classmethod
    def _tick(cls):
        alive = {id(m.canvas.figure) for m in Gcf.figs.values()}
        for window in list(cls._windows):
            if window._watched and id(window._fig) not in alive:
                window.close()
        if not cls._windows and cls._watch is not None:
            cls._watch.stop()

    @classmethod
    def _register(cls, window):
        cls._windows.append(window)
        if cls._watch is None:
            cls._watch = QTimer()
            cls._watch.setInterval(150)
            cls._watch.timeout.connect(cls._tick)
        if not cls._watch.isActive():
            cls._watch.start()

    def __init__(self, fig, parent=None):
        super().__init__(parent)
        self.setWindowFlag(Qt.Window)
        self._fig = fig
        fig._qcs_plot_window = self
        self._closing = False
        self._loop = None
        canvas = fig.canvas
        if not isinstance(canvas, FigureCanvasQTAgg):
            canvas = FigureCanvasQTAgg(fig)
        self._canvas = canvas
        self.setWindowTitle(getattr(fig, '_qcs_window_title', '') or 'QCS - plot')
        self.setWindowIcon(_app_icon())
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        toolbar = QCSNavigationToolbar(canvas, self)
        self._toolbar = toolbar
        _prime_toolbar(fig, toolbar)
        lay.addWidget(toolbar)
        lay.addWidget(canvas)
        button_specs = getattr(fig, '_qcs_native_buttons', None)
        self._review_buttons = []
        if button_specs:
            # The figure retains its Matplotlib buttons for the legacy Tk shell.
            # In Qt, hide those drawn axes and use the same native QPushButtons,
            # margins and spacing as the panel browser's Previous / Next row.
            for button_ax in getattr(fig, '_qcs_mpl_button_axes', []):
                button_ax.set_visible(False)
            fig.subplots_adjust(bottom=0.12)
            canvas.draw_idle()
            lay.setContentsMargins(0, 0, 0, 8)
            lay.setSpacing(6)
            actions = QHBoxLayout()
            actions.setContentsMargins(9, 0, 9, 0)
            actions.setSpacing(6)
            for text, callback in button_specs:
                button = QPushButton(text)
                button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
                button.clicked.connect(lambda _checked=False, cb=callback: cb())
                actions.addWidget(button, 1)
                self._review_buttons.append(button)
            lay.addLayout(actions)
        w, h = fig.get_size_inches() * fig.dpi
        self.resize(int(w), int(h) + (96 if button_specs else 48))
        fig.canvas.mpl_connect('close_event', self._figure_closed)
        # only a figure pyplot KNOWS can be detected as closed by the watchdog;
        # one built straight from Figure() would otherwise be closed at once
        self._watched = any(m.canvas.figure is fig for m in Gcf.figs.values())

    def _figure_closed(self, _event):
        if not self._closing:      # plt.close(fig) came from the pipeline
            self._closing = True
            self.close()

    def closeEvent(self, event):
        if not self._closing:      # the operator closed the window
            self._closing = True
            CloseEvent('close_event', self._canvas)._process()
        if self in PlotWindow._open:
            PlotWindow._open.remove(self)
        if self in PlotWindow._windows:
            PlotWindow._windows.remove(self)
        if self._loop is not None and self._loop.isRunning():
            self._loop.quit()
        super().closeEvent(event)

    def show_and_wait(self):
        """Interactive review: show and block until the window is closed."""
        PlotWindow._register(self)
        self.show()
        self.raise_()
        self.activateWindow()
        self._canvas.setFocus()    # Enter/Esc reach the figure without a click
        self._loop = QEventLoop()
        self._loop.exec()

    def show_free(self):
        """A produced panel: show it and leave it open."""
        PlotWindow._open.append(self)
        PlotWindow._register(self)
        self.show()
        self.raise_()


class PanelBrowserWindow(QWidget):
    """One window holding several panels, paged with Previous / Next.

    Current panels and broad HOBO selections would otherwise open many separate
    windows. Here they share a window and the operator walks through them at
    their own pace, each page keeping its own navigation toolbar so a panel can
    still be zoomed, panned and saved.

    Only a REQUEST from the plotting code is honoured (`show_panels(browse=
    True)`); everything else still gets one window per figure, because the
    scalar panels are meant to be compared side by side.
    """

    def __init__(self, figs, parent=None):
        super().__init__(parent)
        self.setWindowFlag(Qt.Window)
        self.setWindowIcon(_app_icon())
        self._figs = list(figs)
        self._stack = QStackedWidget()
        self._toolbars = []
        for fig in self._figs:
            page = QWidget()
            pv = QVBoxLayout(page)
            pv.setContentsMargins(0, 0, 0, 0)
            pv.setSpacing(0)
            canvas = fig.canvas
            if not isinstance(canvas, FigureCanvasQTAgg):
                canvas = FigureCanvasQTAgg(fig)
            toolbar = QCSNavigationToolbar(canvas, page)
            self._toolbars.append(toolbar)
            _prime_toolbar(fig, toolbar)
            pv.addWidget(toolbar)
            pv.addWidget(canvas)
            self._stack.addWidget(page)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 8)
        lay.setSpacing(6)
        lay.addWidget(self._stack)
        nav = QHBoxLayout()
        nav.setContentsMargins(9, 0, 9, 0)
        self._prev = QPushButton('< Previous')
        self._prev.clicked.connect(lambda: self._step(-1))
        self._next = QPushButton('Next >')
        self._next.clicked.connect(lambda: self._step(1))
        self._counter = QLabel()
        self._picker = QComboBox()
        self._picker.setToolTip('Jump directly to a site and panel')
        for i, fig in enumerate(self._figs):
            title = getattr(fig, '_qcs_window_title', '') or 'Panel %d' % (i + 1)
            self._picker.addItem(title)
        self._picker.currentIndexChanged.connect(self._go)
        nav.addWidget(self._prev)
        nav.addStretch()
        nav.addWidget(QLabel('Go to:'))
        nav.addWidget(self._picker, 1)
        nav.addWidget(self._counter)
        nav.addStretch()
        nav.addWidget(self._next)
        lay.addLayout(nav)
        first = self._figs[0]
        w, h = first.get_size_inches() * first.dpi
        self.resize(int(w), int(h) + 96)     # toolbar + the paging row
        self._go(0)

    def _step(self, delta):
        self._go(self._stack.currentIndex() + delta)

    def _go(self, index):
        with qtheme.wait_cursor(self):
            index = max(0, min(index, len(self._figs) - 1))
            self._stack.setCurrentIndex(index)
            with QSignalBlocker(self._picker):
                self._picker.setCurrentIndex(index)
            self._counter.setText('Panel %d of %d' % (index + 1, len(self._figs)))
            self._prev.setEnabled(index > 0)
            self._next.setEnabled(index < len(self._figs) - 1)
            title = getattr(self._figs[index], '_qcs_window_title', '') or 'QCS - panels'
            self.setWindowTitle('%s  (%d of %d)' % (title, index + 1, len(self._figs)))

    def show_free(self):
        PlotWindow._open.append(self)     # the next set of panels closes it
        self.show()
        self.raise_()

    def closeEvent(self, event):
        if self in PlotWindow._open:
            PlotWindow._open.remove(self)
        super().closeEvent(event)


def _qt_show_panels(figures=None, browse=False):
    """view.show_panels replacement: the visualization's figures open in the
    shell's own windows. Under Agg `plt.show()` does nothing at all, so without
    this the panels would be written and never displayed.

    figures: the exact figures to show (None = every figure pyplot holds).
    browse:  the plotting code asked for ONE paged window (v13.0)."""
    for window in list(PlotWindow._open):
        window.close()
    figs = (list(figures) if figures is not None
            else [plt.figure(num) for num in plt.get_fignums()])
    if browse and len(figs) > 1:
        PanelBrowserWindow(figs).show_free()
        return
    for fig in figs:
        PlotWindow(fig).show_free()


def wait_figure_close(fig):
    """Qt replacement for the pipeline's figure waits: shows the interactive
    figure in a PlotWindow and returns once it is closed."""
    PlotWindow(fig).show_and_wait()


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


class FeedbackDialog(QDialog):
    """Collect a report and submit it without blocking the interface."""

    submission_finished = Signal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Bugs & Suggestions')
        self.setWindowIcon(_app_icon())
        self.resize(590, 500)

        layout = QVBoxLayout(self)
        intro = QLabel(
            'Describe a problem or suggestion. Title and description are '
            'required.')
        intro.setWordWrap(True)
        layout.addWidget(intro)

        layout.addWidget(QLabel('Your name:'))
        self.name_edit = QLineEdit()
        self.name_edit.setObjectName('feedbackName')
        self.name_edit.setMaxLength(feedback_api.MAX_NAME_LENGTH)
        self.name_edit.setPlaceholderText('Optional')
        layout.addWidget(self.name_edit)

        layout.addWidget(QLabel('Title:'))
        self.title_edit = QLineEdit()
        self.title_edit.setObjectName('feedbackTitle')
        self.title_edit.setMaxLength(feedback_api.MAX_TITLE_LENGTH)
        self.title_edit.setPlaceholderText('Short summary of the problem or suggestion')
        layout.addWidget(self.title_edit)

        layout.addWidget(QLabel('Description:'))
        self.description_edit = QPlainTextEdit()
        self.description_edit.setObjectName('feedbackDescription')
        self.description_edit.setPlaceholderText(
            'What were you doing, what happened, and what did you expect?')
        self.description_edit.textChanged.connect(self._update_count)
        layout.addWidget(self.description_edit, 1)

        self.count_label = QLabel()
        self.count_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        layout.addWidget(self.count_label)
        self._update_count()

        note = QLabel(
            '<b>The report will be public.</b> QCS submits it directly to the '
            'project issue tracker. Do not include passwords, private data or '
            'other sensitive information. If submission fails, your text stays '
            'in the form and can be copied.')
        note.setWordWrap(True)
        layout.addWidget(note)

        buttons = QHBoxLayout()
        self.cancel_button = QPushButton('Cancel')
        self.cancel_button.clicked.connect(self.reject)
        self.submit_button = QPushButton('Submit report')
        self.submit_button.setObjectName('submitFeedbackReport')
        self.submit_button.setDefault(True)
        self.submit_button.clicked.connect(self._submit)
        buttons.addStretch()
        buttons.addWidget(self.cancel_button)
        buttons.addWidget(self.submit_button)
        layout.addLayout(buttons)
        self._busy = False
        self.submission_finished.connect(self._submission_finished)

    def _values(self):
        return (self.name_edit.text(), self.title_edit.text(),
                self.description_edit.toPlainText())

    def _update_count(self):
        count = len(self.description_edit.toPlainText())
        self.count_label.setText(
            '%d / %d characters' %
            (count, feedback_api.MAX_DESCRIPTION_LENGTH))

    def _submit(self):
        try:
            feedback_api.validate_report(*self._values())
        except feedback_api.FeedbackError as exc:
            QMessageBox.warning(self, 'Bugs & Suggestions', str(exc))
            return
        values = self._values()
        self._set_busy(True)
        threading.Thread(
            target=self._submit_worker, args=(values,), daemon=True).start()

    def _submit_worker(self, values):
        try:
            receipt = feedback_api.submit_feedback(
                *values, data.QCS_VERSION)
            result = (True, receipt)
        except feedback_api.FeedbackError as exc:
            result = (False, str(exc))
        except Exception:
            result = (
                False,
                'The feedback report could not be sent. Your text is still in '
                'the form.')
        self.submission_finished.emit(result)

    @Slot(object)
    def _submission_finished(self, result):
        self._set_busy(False)
        succeeded, detail = result
        if not succeeded:
            QMessageBox.warning(self, 'Bugs & Suggestions', detail)
            return
        QMessageBox.information(
            self, 'Bugs & Suggestions',
            'Thank you. The report was submitted as Issue #%d.'
            % detail['issue_number'])
        self.accept()

    def _set_busy(self, busy):
        self._busy = busy
        self.name_edit.setEnabled(not busy)
        self.title_edit.setEnabled(not busy)
        self.description_edit.setEnabled(not busy)
        self.cancel_button.setEnabled(not busy)
        self.submit_button.setEnabled(not busy)
        self.submit_button.setText('Submitting...' if busy else 'Submit report')

    def closeEvent(self, event):
        if self._busy:
            event.ignore()
            return
        super().closeEvent(event)

    def reject(self):
        if not self._busy:
            super().reject()


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
        self._doppler_file = False  # the selected .bin is a DCPS session
        self._detected_type = None  # detected scalar Mooring/Profile identity
        self._advance_viz = False   # 'Go to visualization' asked for Step 2
        self._run_thread = None     # the qualification's worker (v12.3)
        self._cancel = threading.Event()   # read by the worker, set by Cancel
        self._cancel_raised = False        # RunCanceled already thrown once
        self._stage_total = 5       # stages the running pipeline logs (Doppler has 4)
        self._qualification_busy = False
        self._curated_busy = False

        tabs = QTabWidget()
        # Set before adding pages so size hints reserve enough width for the
        # bold active label while Figure options and other tabs stay native.
        tabs.tabBar().setObjectName('MainTabs')
        # every page is wrapped: a page that cannot shrink caps how far the
        # Execution log can be dragged open (see qtheme.scrollable)
        self._qualification_page = qtheme.scrollable(self._qualification_tab())
        tabs.addTab(self._qualification_page, 'Data qualification')
        self.curated_tab = None
        self._curated_page = None
        self._curated_placeholder = QWidget()
        tabs.addTab(self._curated_placeholder, 'Curated database')
        tabs.setTabToolTip(tabs.indexOf(self._curated_placeholder),
                           CURATED_TAB_TOOLTIP)
        self.viz_tab = None               # attached by main() after the bootstrap
        self._viz_page = None             # the scroll area that holds viz_tab
        self._viz_placeholder = QWidget()
        tabs.addTab(self._viz_placeholder, 'Data visualization')
        tabs.currentChanged.connect(self._tab_changed)
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
        status = self.statusBar()
        # No size grip: the window edges and corners still resize normally.
        # QStatusBar adds a native 2 px inset only on the left. These asymmetric
        # layout margins therefore put both widgets on the same 11 px axes as
        # the main content.
        status.setSizeGripEnabled(False)
        status.setContentsMargins(9, 0, 11, 0)
        # Criteria is an ordinary (left-side) status widget, while progress is
        # permanent and therefore stays against the far right when shown.
        self.criteria_label = QLabel('')
        self.criteria_label.setFixedWidth(self._criteria_width())
        self.criteria_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        status.addWidget(self.criteria_label)
        # Pipeline progress: indeterminate while a single run is busy, and a
        # real fraction on the batch/replicate markers the pipeline already
        # logs ('=== File k/n ===' / '=== Replicate k/n ===').
        self.progress = QProgressBar()
        self.progress.setFixedWidth(220)
        self.progress.setVisible(False)
        status.addPermanentWidget(self.progress)
        # Moving the indicator must not resize the existing log action. Keep
        # its established width and right-hand content axis independently.
        clear_width = max(
            self.log_dock.clear_button.sizeHint().width(),
            self._criteria_width())
        self.log_dock.clear_button.setFixedWidth(clear_width)
        self.log_dock.button_row.setContentsMargins(0, 0, 12, 0)

    def _criteria_width(self):
        """How wide the indicator must be to hold its text.

        Measured from the TEXT, and from the WIDER of the two wordings: a
        QLabel's sizeHint stops growing once setFixedWidth has been applied, so
        sizing from the hint left 'criteria: CUSTOM' clipped at both ends
        (owner, 2026-08-19), and measuring only the current text made the
        widget jump sideways whenever the indicator changed."""
        fm = self.criteria_label.fontMetrics()
        return max(fm.horizontalAdvance(t) for t in CRITERIA_TEXTS) + 18

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

    def closeEvent(self, event):
        """The window remembers how it was left, and so does the form: the tk
        shell saved on exit (QCS_App.remember_window_state) and the port had no
        closeEvent at all, so every session reopened at the default size
        (v12.2)."""
        if self.curated_tab is not None and self.curated_tab.is_busy():
            QMessageBox.warning(
                self, 'Curated database in progress',
                'Wait for the curated database operation to finish before closing QCS.')
            event.ignore()
            return
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

    def update_criteria_indicator(self):
        d = qm.DEFAULT_QUALITY_CONFIG
        default = (qm.CONFIG['tsQualityTests'] == d['tsQualityTests']
                   and qm.CONFIG['tsSettings'] == d['tsSettings']
                   and {k: dict(v) for k, v in qm.CONFIG['tsFactors'].items()}
                   == d['tsFactors'])
        self.criteria_label.setText(CRITERIA_TEXTS[0] if default
                                    else CRITERIA_TEXTS[1])
        self.criteria_label.setToolTip(
            'The quality criteria are the software defaults' if default else
            'At least one quality criterion differs from the defaults\n'
            '(the edited fields show in bold in Quality control settings)')

    # ----- logging -----
    def log_line(self, message):
        # the pipeline's own markers drive the progress bar: every run logs
        # 'Stage k/N', and batches/replicates scope it with '=== File k/n ==='
        # / '=== Replicate k/n ==='. Progress is CONTINUOUS across the whole
        # run: file k of n at stage s sits at (k-1)*N + s out of n*N, so
        # finishing the first of two replicates reads 50%, not a reset.
        # N comes from the marker itself: the scalar pipeline logs 5 stages and
        # the Doppler one 4, and a hardcoded '/5' matched neither - it left the
        # DCPS run with a blank, indeterminate bar (owner, v12.2.4).
        msg = message.strip()
        m = re.match(r'=== (File|Replicate) (\d+)/(\d+): (.+?) ===', msg)
        if m:
            kind, k, n = m.group(1), int(m.group(2)), int(m.group(3))
            self._run_scope = (kind, k, n)
            self.progress.setRange(0, n * self._stage_total)
            self.progress.setValue((k - 1) * self._stage_total)
            self.progress.setFormat('%s %d/%d' % (kind, k, n))
            if kind == 'File':
                self._batch_mark(m.group(4), k, n)
        fail = re.match(r'File (.+?) could not be qualified', msg)
        if fail and fail.group(1) in self._batch_rows:
            row = self._batch_rows[fail.group(1)]
            self.batch_table.setItem(row, 1, QTableWidgetItem('FAILED (see log)'))
        else:
            s = re.match(r'Stage (\d+)/(\d+)', msg)
            if s:
                stage, total = int(s.group(1)), int(s.group(2))
                self._stage_total = total
                if self._run_scope:
                    kind, k, n = self._run_scope
                    self.progress.setRange(0, n * total)
                    self.progress.setValue((k - 1) * total + stage)
                    self.progress.setFormat('%s %d/%d - Stage %d/%d'
                                            % (kind, k, n, stage, total))
                else:
                    self.progress.setRange(0, total)
                    self.progress.setValue(stage)
                    self.progress.setFormat('Stage %d/%d' % (stage, total))
        self.log_dock.log(message)
        if self._run_thread is None:
            # single-threaded callers (the visualization tab) still need the
            # window repainted mid-work; a threaded run repaints on its own
            QApplication.processEvents()

    # ----- qualification tab -----
    def _qualification_tab(self):
        w = QWidget()
        grid = QGridLayout(w)

        gin = QGroupBox('Input settings')
        self._qualification_input_group = gin
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
        self._qualification_output_group = gout
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
        self.cancel_btn = QPushButton('Cancel')
        self.cancel_btn.setToolTip('Stops the qualification at the next step.\n'
                                   'What is already written stays; the file '
                                   'being processed is not finished')
        self.cancel_btn.clicked.connect(self._cancel_run)
        self.cancel_btn.setVisible(False)      # only while a run is in progress
        self.run_hint = QLabel('')
        qtheme.muted(self.run_hint)
        settings = QPushButton('Quality control settings')
        settings.setToolTip(TOOLTIPS['settings_button'])
        settings.clicked.connect(self._open_settings)

        grid.addWidget(gin, 0, 0)
        grid.addWidget(gout, 0, 1)
        # Optional instrument-specific rows may change height, never the
        # horizontal Input/Output split.
        for group in (gin, gout):
            group.setSizePolicy(
                QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        grid.setColumnMinimumWidth(0, 520)
        grid.setColumnMinimumWidth(1, 520)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)
        # while a run is in progress the ONLY live control is Cancel (owner,
        # v12.3): the window stays responsive now, and a form edited mid-run
        # would describe a qualification that is no longer the one running
        self._busy_freeze = [gin, gout, settings]
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
        to_viz.setToolTip('Opens the visualization on the panels of what was '
                          'just qualified')
        to_viz.clicked.connect(self._go_to_visualization)
        pr.addWidget(open_out)
        pr.addWidget(to_viz)
        self.postrun_bar.setVisible(False)

        run_box = QVBoxLayout()
        run_box.setContentsMargins(0, 0, 0, 0)
        run_box.setSpacing(4)   # the shortcuts hug RUN (owner, v12.1)
        run_box.addWidget(self.run_btn, alignment=Qt.AlignHCenter)
        run_box.addWidget(self.cancel_btn, alignment=Qt.AlignHCenter)
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
        qtheme.enable_clear_buttons(w)
        self._input_type_changed(self.input_type.currentText())
        self._update_run_state()
        return w

    def attach_visualization_tab(self):
        """Attach the post-bootstrap visualization and curated-data tabs."""
        self.curated_tab = CuratedDatabaseTab(self)
        self._curated_page = qtheme.scrollable(self.curated_tab)
        idx = self.tabs.indexOf(self._curated_placeholder)
        self.tabs.removeTab(idx)
        self.tabs.insertTab(idx, self._curated_page, 'Curated database')
        self.viz_tab = VisualizationTab(self)
        self._viz_page = qtheme.scrollable(self.viz_tab)
        idx = self.tabs.indexOf(self._viz_placeholder)
        self.tabs.removeTab(idx)
        self.tabs.insertTab(idx, self._viz_page, 'Data visualization')
        self._sync_workflow_tabs()

    def _go_to_visualization(self):
        """The post-run shortcut: unlike the tab bar, it goes all the way to
        the panels of the run that just finished (owner, v12.3)."""
        self._advance_viz = True
        self.tabs.setCurrentIndex(self.tabs.indexOf(self._viz_page))

    def open_curated_visualization(self, path, instrument):
        """Hand one curated sheet to Visualization and land on Step 2."""
        self.viz_tab.apply_curated_workbook(path, instrument, advance=True)
        self.tabs.setCurrentWidget(self._viz_page)

    def _tab_changed(self, _index):
        page = self.tabs.currentWidget()
        if (self._field_mode_enabled()
                and page in (self._curated_placeholder, self._curated_page)):
            # setCurrentWidget can target a disabled tab programmatically. Keep
            # the field guarantee true for every navigation path, not only a
            # mouse click on the tab bar.
            self.tabs.setCurrentWidget(self._qualification_page)
            return
        # hand a just-qualified file to the Visualization tab, exactly like
        # the tk shell does on its tab switch
        advance, self._advance_viz = self._advance_viz, False
        if (self.viz_tab is not None
                and self.tabs.currentWidget() is self._viz_page
                and qm.PENDING_VIZ_PREFILL):
            self.viz_tab.apply_prefill(qm.PENDING_VIZ_PREFILL, advance=advance)
            qm.PENDING_VIZ_PREFILL = None
        # every switch starts at the top of the page, never wherever the tab
        # was left (owner, 2026-08-19)
        page = self.tabs.currentWidget()
        if isinstance(page, QScrollArea):
            qtheme.scroll_to_top(page.widget() or page)
        if hasattr(self, 'open_input_action'):
            if page is self._curated_page:
                self.open_input_action.setText('Select corpus folder...')
            elif page is self._viz_page:
                self.open_input_action.setText('Select database file(s)...')
            else:
                self.open_input_action.setText('Select data file(s)...')

    def _browse_active_input(self):
        page = self.tabs.currentWidget()
        if self.curated_tab is not None and page is self._curated_page:
            self.curated_tab._browse_corpus()
        elif self.viz_tab is not None and page is self._viz_page:
            self.viz_tab._browse_files()
        else:
            self._browse()

    def _browse_active_output(self):
        page = self.tabs.currentWidget()
        if self.curated_tab is not None and page is self._curated_page:
            self.curated_tab._browse_output()
        elif self.viz_tab is not None and page is self._viz_page:
            self.viz_tab._browse_output_folder()
        else:
            self._browse_output()

    def _open_active_output(self):
        page = self.tabs.currentWidget()
        if self.curated_tab is not None and page is self._curated_page:
            root = self.curated_tab.output_folder.text().strip()
        elif self.viz_tab is not None and page is self._viz_page:
            root = self.viz_tab.out_path.text().strip()
        else:
            self._open_output_folder()
            return
        if root and os.path.isdir(root):
            os.startfile(root)
        else:
            QMessageBox.warning(
                self, 'Output folder',
                'The output folder no longer exists:\n%s' % root)

    def _menus(self):
        # File carries the file-level actions of the active workflow, so the
        # keyboard reaches what the buttons do (owner asked what belongs here:
        # selection, output folder, settings, exit)
        mb = self.menuBar()
        filem = mb.addMenu('File')
        self.open_input_action = QAction('Select data file(s)...', self)
        self.open_input_action.setShortcut('Ctrl+O')
        self.open_input_action.triggered.connect(self._browse_active_input)
        filem.addAction(self.open_input_action)
        act_co2 = QAction('Add CO₂ data...', self)
        act_co2.triggered.connect(self._select_co2)
        filem.addAction(act_co2)
        act_outdir = QAction('Select output folder...', self)
        act_outdir.triggered.connect(self._browse_active_output)
        filem.addAction(act_outdir)
        filem.addSeparator()
        act_showout = QAction('Open output folder', self)
        act_showout.triggered.connect(self._open_active_output)
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
        view.setToolTipsVisible(True)
        self.dark_action = QAction('Dark mode', self, checkable=True)
        self.dark_action.triggered.connect(self._toggle_dark)
        view.addAction(self.dark_action)
        self.field_mode_action = QAction('Field mode', self, checkable=True)
        self.field_mode_action.setToolTip(FIELD_MODE_TOOLTIP)
        self.field_mode_action.setStatusTip(FIELD_MODE_TOOLTIP)
        self.field_mode_action.triggered.connect(self._toggle_field_mode)
        view.addAction(self.field_mode_action)
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

        feedback = QAction('Bugs && Suggestions', self)
        feedback.setStatusTip(
            'Describe a problem or suggestion and submit it to the project.')
        feedback.triggered.connect(self._open_feedback_form)
        mb.addAction(feedback)

    def _open_feedback_form(self):
        """Open the local report form; no GitHub account is required."""
        FeedbackDialog(self).exec()

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

    def _field_mode_enabled(self):
        return (hasattr(self, 'field_mode_action')
                and self.field_mode_action.isChecked())

    def _sync_workflow_tabs(self):
        """Apply the two job locks and the independent Field mode lock."""
        curated_page = self._curated_page or self._curated_placeholder
        job_busy = self._qualification_busy or self._curated_busy
        states = (
            (self._qualification_page, not job_busy),
            (curated_page, not job_busy and not self._field_mode_enabled()),
            (self._viz_page or self._viz_placeholder,
             not job_busy),
        )
        current_index = self.tabs.currentIndex()
        deferred_current = None
        for page, enabled in states:
            index = self.tabs.indexOf(page)
            if index >= 0:
                if job_busy and index == current_index and not enabled:
                    deferred_current = (index, page)
                else:
                    self.tabs.setTabEnabled(index, enabled)
        if deferred_current is not None:
            # QTabWidget.setTabEnabled(False) also disables the current PAGE,
            # which would kill its live Cancel button. Disable only the tab-bar
            # item after the other tabs so the page stays visible and Cancel
            # remains interactive while every workflow label looks unavailable.
            index, page = deferred_current
            page.setEnabled(True)
            self.tabs.tabBar().setTabEnabled(index, False)
        curated_index = self.tabs.indexOf(curated_page)
        if curated_index >= 0:
            tooltip = (CURATED_TAB_FIELD_TOOLTIP if self._field_mode_enabled()
                       else CURATED_TAB_TOOLTIP)
            self.tabs.setTabToolTip(curated_index, tooltip)

    def _apply_field_mode(self):
        if (self._field_mode_enabled()
                and self.tabs.currentWidget()
                in (self._curated_placeholder, self._curated_page)):
            self.tabs.setCurrentWidget(self._qualification_page)
        self._sync_workflow_tabs()

    def _toggle_field_mode(self, on):
        qm.USER_PREFS['field_mode'] = bool(on)
        qm.save_user_prefs()
        self._apply_field_mode()

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
        elif (self.curated_tab is not None
              and self.tabs.currentWidget() is self._curated_page):
            self.curated_tab.apply_dropped_paths(paths)
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
        # A new selection owns a new identity.  In particular, do not let the
        # detection/lock from the file that was cleared leak into a re-drop.
        self._doppler_file = False
        self._detected_type = None
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
                self._doppler_file = True
                if self.data_type.currentText() != 'TSCP Doppler':
                    print("Info: DCPS current profiler detected - Data type set to 'TSCP Doppler'.")
            else:
                self._doppler_file = False
                # A scalar session says whether it is a mooring or a cast: it
                # is a matter of how long it lasted, and reading that costs one
                # decode of a file the run will read anyway.  Once the rule can
                # decide, that detected identity is locked just like the family;
                # an ambiguous/too-short file deliberately remains editable.
                looks_like, hours, step = data.detect_seaguard_data_type(first)
                if looks_like:
                    if self.data_type.currentText() != looks_like:
                        self.data_type.setCurrentText(looks_like)
                    print('Info: the session spans %.1f h at one record every '
                          "%.0f s - Data type detected as '%s' and locked."
                          % (hours, step, looks_like))
                    self._detected_type = (looks_like, hours)
                else:
                    self._detected_type = None
                    if self.data_type.currentText() == 'TSCP Doppler':
                        self.data_type.setCurrentText('TSCP Mooring')
                    if hours is not None:
                        print('Info: the session spans %.1f h at one record every '
                              '%.0f s; the labelled archive contains both a mooring '
                              'and a cast with this short/slow pattern. Data type '
                              "left at '%s' (editable); check it before running."
                              % (hours, step, self.data_type.currentText()))
                    else:
                        print('Info: this session does not say whether it is a '
                              'mooring or a cast (too few records to time it) - '
                              "Data type left at '%s' (editable); check it before "
                              'running.' % self.data_type.currentText())
        self._apply_data_type_lock()
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
        detected = getattr(self, '_detected_type', None)
        if detected and itype == 'Seaguard' and len(names) == 1:
            # how long the session lasted, and what that makes it: the summary
            # is where the operator checks the auto-selected Data type (v13.0)
            looks_like, hours = detected
            self.sum_labels['period'].setText(
                '%s   -   %s over %s'
                % (self.sum_labels['period'].text(),
                   'mooring' if looks_like == 'TSCP Mooring' else 'cast',
                   _duration_text(hours)))
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
            self._apply_data_type_lock()
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

    def _apply_data_type_lock(self):
        """Lock every Data type that the selected Seaguard file establishes.

        DCPS is identified by its binary layout.  Scalar Mooring/Profile is
        identified by the calibrated session-duration/cadence rule.  Only an
        ambiguous scalar file leaves the operator a choice.
        """
        if self.input_type.currentText() != 'Seaguard':
            self.data_type.setToolTip(TOOLTIPS['data_type'])
            return
        if self._doppler_file:
            self.data_type.setCurrentText('TSCP Doppler')
            self.data_type.setEnabled(False)
            self.data_type.setToolTip(
                'Decided by the file: this .bin is a DCPS current-profiler '
                'session, so the collection type is not a choice')
        elif self._detected_type is not None:
            detected, hours = self._detected_type
            self.data_type.setCurrentText(detected)
            self.data_type.setEnabled(False)
            self.data_type.setToolTip(
                'Decided from this session (duration %s): the detected '
                'collection type is not a choice.' % _duration_text(hours))
        else:
            self.data_type.setEnabled(True)
            self.data_type.setToolTip(TOOLTIPS['data_type'])

    def _update_profile_state(self):
        # 'Select profile data' applies to profiles only (port of
        # update_profile_checkbox_state)
        is_profile = self.data_type.currentText() == 'TSCP Profile'
        self.profile_check.setEnabled(is_profile)
        if not is_profile:
            self.profile_check.setChecked(False)

    # ----- run -----
    def _file_text_changed(self, text):
        # 'Open output folder' and 'Go to visualization' point at the run that
        # just finished. The moment the selection changes - cleared, or another
        # file dropped in - they point at the WRONG thing, so they go away
        # (owner, v13.0). The next run brings them back.
        self.postrun_bar.setVisible(False)
        if not text.strip():
            # selection cleared: back to 'Select instrument', editable, and
            # the Replicates line and summary go away with it
            self._doppler_file = False
            self._detected_type = None
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
        self._qualification_busy = bool(busy)
        self.run_btn.setEnabled(not busy)
        self.progress.setVisible(busy)
        # everything but Cancel goes dead for the duration: the form, the
        # settings button, the menus and the data tabs (their panel/database
        # work must not compete with a qualification run)
        for widget in getattr(self, '_busy_freeze', ()):
            widget.setEnabled(not busy)
        self.menuBar().setEnabled(not busy)
        self._sync_workflow_tabs()
        self.cancel_btn.setVisible(busy)
        if busy:
            self.cancel_btn.setEnabled(True)
            self.cancel_btn.setText('Cancel')
            self._run_scope = None
            self._stage_total = 5   # re-learned from the first Stage marker
            self.batch_dock.hide()          # reappears on the first File marker
            self.batch_table.setRowCount(0)
            self._batch_rows = {}
            self.postrun_bar.setVisible(False)
            self.progress.setRange(0, 0)   # indeterminate until the first Stage marker
            # busy cursor on the MAIN window only (like the tk watch cursor):
            # an app-wide override cursor kept spinning over the interactive
            # review windows and dialogs, reading as a hang
            if not qm.THREADED:
                # the pipeline no longer holds the interface thread (v12.3), so
                # a wait cursor would say the opposite of what is true: the
                # window is live and Cancel is there to be clicked
                self.setCursor(Qt.WaitCursor)
        else:
            self.unsetCursor()
            self._finish_running_batch_row()
            self._update_run_state()
            # a run that produced an output offers the two next steps
            self.postrun_bar.setVisible(bool(qm.OUTPUT.get('last_output_root')))

    def set_curated_busy(self, busy):
        """Prevent another workflow from starting while a corpus job is active."""
        self._curated_busy = bool(busy)
        self._sync_workflow_tabs()
        self.menuBar().setEnabled(not busy)
        if busy:
            self.progress.setRange(0, 1)
            self.progress.setValue(0)
            self.progress.setFormat('Calculating...')
            self.progress.setToolTip(
                'Calculating the amount of work; the total is not known yet.')
            self.progress.setVisible(True)
        else:
            self.progress.setVisible(False)
            self.progress.reset()

    def update_curated_progress(self, message):
        """Show curated-corpus work in the shell's standard status-bar progress."""
        stage_match = re.match(r'Stage (\d+)/(\d+)(?: - (.*))?', message)
        catalog_match = re.match(
            r'Reading qualified product (\d+)/(\d+)\.\.\.', message)
        if stage_match:
            stage, total = (int(value) for value in stage_match.groups()[:2])
            detail = stage_match.group(3) or ''
            self.progress.setRange(0, total)
            self.progress.setValue(stage)
            self.progress.setFormat(
                'Stage %d/%d%s' %
                (stage, total, ' ' + detail if detail else ''))
        elif catalog_match:
            current, total = (int(value) for value in catalog_match.groups())
            self.progress.setRange(0, total)
            self.progress.setValue(current)
            self.progress.setFormat('Catalog %d/%d' % (current, total))
        else:
            if message.startswith('Unifying '):
                label = 'Building database...'
            elif message == 'Writing curated workbook...':
                label = 'Writing workbook...'
            elif message == 'Discovering qualified products...':
                self.progress.setRange(0, 1)
                self.progress.setValue(0)
                label = 'Calculating...'
            elif message == 'Preparing curated database...':
                self.progress.setRange(0, 1)
                self.progress.setValue(0)
                label = 'Preparing database...'
            else:
                label = message
            self.progress.setFormat(label)
        self.progress.setToolTip(message)

    def _update_regions(self, _macro=None):
        macro = self.macroregion.currentText()
        regions = [r[0] for r in qm.REGIONS.get(macro, [])]
        current = self.region.currentText()
        self.region.clear()
        self.region.addItems(regions)
        if current in regions:
            self.region.setCurrentText(current)

    def _run(self):
        """RUN: the qualification goes to a worker thread (v12.3), so the
        window keeps repainting and Cancel can be pressed while it runs."""
        if self._run_thread is not None and self._run_thread.isRunning():
            return                       # already running: RUN is disabled anyway
        self._cancel.clear()
        self._cancel_raised = False
        self._run_thread = _RunThread(self)
        self._run_thread.finished.connect(self._run_thread_done)
        self._run_thread.start()

    def _run_thread_done(self):
        self._run_thread = None
        self.set_busy(False)             # the pipeline's own ui_busy(False)
        self.cancel_btn.setVisible(False)   # already ran; this is the backstop

    def _cancel_run(self):
        """Cancel: cooperative. The worker notices at its next yield point or
        its next log line and unwinds through the pipeline's own canceled path,
        which closes the figures and restores the working directory."""
        if self._run_thread is None or not self._run_thread.isRunning():
            return
        self._cancel.set()
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.setText('Canceling...')
        self.log_line('Cancel requested - the run stops at the next step.')

    def check_canceled(self):
        """The pipeline's yield point (it replaces ui_pump: the window no
        longer needs pumping). Called ON THE WORKER - it must touch no widget."""
        if self._cancel.is_set() and not self._cancel_raised:
            self._cancel_raised = True
            raise qm.RunCanceled()

    # ----- prefs -----
    def restore_prefs(self):
        """Mirrors restore_user_prefs onto the Qt widgets (the criteria/version
        gate already ran inside the tk bootstrap's restore)."""
        p = qm.USER_PREFS
        self.field_mode_action.setChecked(bool(p.get('field_mode', False)))
        self._apply_field_mode()
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


# ----- the worker thread (v12.3) -----
# The qualification used to run ON the interface thread, with ui_pump() calls
# sprinkled through it to keep the window repainting. It now runs on a worker,
# and the pipeline is untouched: every point where it talks to the operator is
# already a swappable hook (the UI facade below), so the hooks are what move
# the call back to the interface thread and block the worker until it answers.

class _GuiBridge(QObject):
    """Runs a callable on the interface thread; the caller waits for it.

    The signal is emitted from the worker and delivered on the interface
    thread (a queued connection - that is what crossing threads means here),
    which then releases the semaphore the worker is blocked on. The result, or
    the exception, travels back in the same box: a dialog the operator cancels
    must raise INSIDE the pipeline, exactly as it did single-threaded.
    """

    request = Signal(object)

    def __init__(self):
        super().__init__()
        self.request.connect(self._serve)

    @Slot(object)
    def _serve(self, box):
        try:
            box['result'] = box['fn'](*box['args'], **box['kwargs'])
        except BaseException as exc:      # noqa: BLE001 - re-raised on the worker
            box['error'] = exc
        finally:
            box['done'].release()

    def call(self, fn, args, kwargs):
        box = {'fn': fn, 'args': args, 'kwargs': kwargs, 'result': None,
               'error': None, 'done': threading.Semaphore(0)}
        self.request.emit(box)
        box['done'].acquire()
        if box['error'] is not None:
            raise box['error']
        return box['result']


_BRIDGE = None       # created with the shell, on the interface thread


def _on_gui(fn):
    """Wraps a facade hook so it always executes on the interface thread."""
    def call_on_gui_thread(*args, **kwargs):
        if QThread.currentThread() is QApplication.instance().thread():
            return fn(*args, **kwargs)
        return _BRIDGE.call(fn, args, kwargs)
    return call_on_gui_thread


class _RunThread(QThread):
    """The qualification, off the interface thread."""

    def run(self):
        qm.start_qualification()      # handles its own errors and cleanup


def _install_qt_facade(shell):
    qm.THREADED = True                 # the log stops warning about a freeze
    # every hook is wrapped: called from the worker it hops to the interface
    # thread and blocks the worker; called from the interface thread it runs
    # straight through (the visualization tab still calls some of these)
    qm.ui_info = _on_gui(lambda t, m: QMessageBox.information(shell, t, m))
    qm.ui_warn = _on_gui(lambda t, m: QMessageBox.warning(shell, t, m))
    qm.ui_error = _on_gui(lambda t, m: QMessageBox.critical(shell, t, m))
    qm.ui_info_parented = _on_gui(
        lambda t, m, parent=None: QMessageBox.information(shell, t, m))
    data._show_plot_info = _on_gui(
        lambda fig, t, m: QMessageBox.information(
            getattr(fig, '_qcs_plot_window', shell), t, m))
    qm.ui_busy = _on_gui(shell.set_busy)
    # ui_pump was 'let the window repaint'; the window repaints on its own now,
    # so the pipeline's yield points become the CANCEL checkpoints instead
    qm.ui_pump = shell.check_canceled
    # the log is the FINE cancel checkpoint: every stage logs. The check runs
    # BEFORE the hop, on the worker - raising it on the interface thread would
    # throw inside the event loop and leave the run going (measured, v12.3)
    _log_on_gui = _on_gui(shell.log_line)

    def pipeline_log(message):
        _log_on_gui(message)
        shell.check_canceled()

    qm.log_line = pipeline_log
    qm.collect_input_settings = _on_gui(shell.collect_from_qt)
    qm.choose_variables_to_check = _on_gui(qt_choose_variables)
    qm.ui_ask_yes_no = _on_gui(lambda t, m: (QMessageBox.question(shell, t, m)
                                             == QMessageBox.StandardButton.Yes))
    qm.wait_figure_close = _on_gui(wait_figure_close)
    data._show_and_wait = _on_gui(lambda fig, tk_root=None: wait_figure_close(fig))
    theme.style_plot_window = _qt_style_plot_window   # app icon on plot windows
    view.show_panels = _qt_show_panels                # panels open in OUR windows
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
    global _BRIDGE
    _BRIDGE = _GuiBridge()                 # lives on the interface thread
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

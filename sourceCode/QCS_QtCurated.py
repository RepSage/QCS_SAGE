# -*- coding: utf-8 -*-
"""Qt tab for building read-only selections from the qualified QCS corpus."""
from __future__ import annotations

import os

from PySide6.QtCore import QSignalBlocker, Qt, QThread, Signal
from PySide6.QtWidgets import (QAbstractItemView, QFileDialog,
                               QFormLayout, QGridLayout, QGroupBox,
                               QHBoxLayout, QInputDialog, QLabel, QLineEdit, QListWidget,
                               QListWidgetItem, QMessageBox, QPushButton,
                               QVBoxLayout, QWidget)

import QCS_Curated as curated
import QCS_Main as qm
import QCS_QtTheme as qtheme


LARGE_SELECTION_ROW_THRESHOLD = 250_000


class _RowCheckListWidget(QListWidget):
    """A checkable list whose whole enabled row toggles its checkbox.

    Qt already toggles when the indicator itself is clicked. Remembering the
    state at press time lets the release handler add the same behavior to the
    rest of the row without toggling an indicator click twice.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._pressed_item = None
        self._pressed_check_state = None

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            item = self.itemAt(event.position().toPoint())
            if item is not None and item.flags() & Qt.ItemFlag.ItemIsEnabled:
                self._pressed_item = item
                self._pressed_check_state = item.checkState()
            else:
                self._pressed_item = None
                self._pressed_check_state = None
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        item = self.itemAt(event.position().toPoint())
        pressed_item = self._pressed_item
        pressed_state = self._pressed_check_state
        super().mouseReleaseEvent(event)
        self._pressed_item = None
        self._pressed_check_state = None
        if (event.button() != Qt.MouseButton.LeftButton
                or item is None or item is not pressed_item
                or not item.flags() & Qt.ItemFlag.ItemIsEnabled
                or item.checkState() != pressed_state):
            return
        item.setCheckState(
            Qt.CheckState.Unchecked
            if pressed_state == Qt.CheckState.Checked
            else Qt.CheckState.Checked)


class _CuratedWorker(QThread):
    succeeded = Signal(str, object)
    failed = Signal(str)
    cancelled = Signal(str)
    progress = Signal(str)

    def __init__(self, operation, payload, parent=None):
        super().__init__(parent)
        self.operation = operation
        self.payload = payload

    def run(self):
        try:
            if self.isInterruptionRequested():
                raise curated.CuratedOperationCancelled(
                    "Curated database operation canceled.")
            if self.operation == "catalog":
                catalog, messages = curated.discover_qualified_corpus(
                    self.payload["corpus_root"], progress=self.progress.emit,
                    should_cancel=self.isInterruptionRequested)
                result = {"catalog": catalog, "messages": messages}
            elif self.operation == "build":
                active = self.payload.get("active_instruments")
                if active is None:
                    requested = set(self.payload["instruments"])
                    active = [name for name in curated.INSTRUMENT_ORDER
                              if name in requested]
                total_stages = len(active) + 2
                stage = [1]
                self.progress.emit(
                    "Stage 1/%d - Select" % total_stages)

                def build_progress(message):
                    if message.startswith("Unifying "):
                        stage[0] += 1
                        instrument = active[stage[0] - 2]
                        self.progress.emit(
                            "Stage %d/%d - %s" %
                            (stage[0], total_stages, instrument))
                    else:
                        self.progress.emit(message)

                tables, included, summary, messages = curated.build_curated_tables(
                    self.payload["catalog"], self.payload["instruments"],
                    self.payload["sites"], self.payload["years"],
                    progress=build_progress,
                    should_cancel=self.isInterruptionRequested)
                # Keep the bar below 100% during the potentially long Excel
                # write. Full means the atomic output has actually finished.
                self.progress.emit("Writing curated workbook...")
                output_path = curated.write_curated_workbook(
                    self.payload["output_path"], self.payload["corpus_root"],
                    tables, included, summary,
                    should_cancel=self.isInterruptionRequested)
                self.progress.emit(
                    "Stage %d/%d - Complete"
                    % (total_stages, total_stages))
                result = {
                    "output_path": output_path,
                    "summary": summary,
                    "messages": messages,
                }
            else:
                raise curated.CuratedDatabaseError(
                    "Curated database: unknown worker operation %s." % self.operation)
        except (curated.CuratedOperationCancelled, InterruptedError) as exc:
            self.cancelled.emit(str(exc) or "Curated database operation canceled.")
            return
        except Exception as exc:
            self.failed.emit(str(exc))
            return
        self.succeeded.emit(self.operation, result)


class CuratedDatabaseTab(QWidget):
    """Select sites, calendar years and instruments from the qualified corpus."""

    def __init__(self, shell):
        super().__init__()
        self.shell = shell
        self.catalog = None
        self._worker = None
        self.last_output_path = None
        self.last_build_summary = None
        self._filter_updating = False
        self._build_ui()

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(9, 9, 9, 9)

        source_group = QGroupBox("Corpus source")
        self.source_group = source_group
        source_grid = QGridLayout(source_group)
        source_label = QLabel("Corpus folder:")
        source_font = source_label.font()
        source_font.setBold(True)
        source_label.setFont(source_font)
        self.corpus_root = QLineEdit(
            qm.USER_PREFS.get("curated_corpus_root", curated.DEFAULT_CORPUS_ROOT))
        self.corpus_root.setPlaceholderText("Select the root of the qualified corpus...")
        self.corpus_root.setToolTip(
            "Folder containing SEAGUARD\\qualified and HOBO\\qualified\n"
            "The catalog and qualified products are read-only")
        self.corpus_root.textEdited.connect(self._source_edited)
        self.browse_source_button = QPushButton("Browse...")
        self.browse_source_button.clicked.connect(self._browse_corpus)
        self.browse_source_button.setToolTip(
            "Select the root folder of the qualified corpus")
        self.catalog_summary = QLabel("Load the corpus catalog to enable the filters below.")
        self.catalog_summary.setWordWrap(True)
        qtheme.muted(self.catalog_summary)
        self.load_button = QPushButton("Load catalog")
        for button in (self.browse_source_button, self.load_button):
            button.setFixedWidth(130)
        self.load_button.setObjectName("AccentButton")
        self.load_button.clicked.connect(self._load_catalog)
        self.load_button.setToolTip(
            "Reads product paths, sites and calendar dates without changing the corpus")
        source_grid.addWidget(
            source_label, 0, 0,
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        source_grid.addWidget(self.corpus_root, 0, 1)
        source_grid.addWidget(self.browse_source_button, 0, 2)
        source_grid.addWidget(self.catalog_summary, 1, 1)
        source_grid.addWidget(self.load_button, 1, 2)
        source_grid.setColumnStretch(1, 1)
        outer.addWidget(source_group)

        selection_group = QGroupBox("Selection")
        self.selection_group = selection_group
        selection_layout = QVBoxLayout(selection_group)
        selection_grid = QGridLayout()
        self.site_list = self._filter_list("Site")
        self.year_list = self._filter_list("Year")
        self.instrument_list = self._filter_list("Instrument")
        filter_columns = (
            ("sites", "Sites", self.site_list),
            ("years", "Calendar years", self.year_list),
            ("instruments", "Instruments", self.instrument_list),
        )
        self._filter_widgets = {
            name: widget for name, _title, widget in filter_columns}
        for name, _title, widget in filter_columns:
            widget.itemChanged.connect(
                lambda _item, dimension=name: self._selection_changed(dimension))
        for column, (name, title, widget) in enumerate(filter_columns):
            label = QLabel(title + ":")
            font = label.font()
            font.setBold(True)
            label.setFont(font)
            selection_grid.addWidget(label, 0, column)
            selection_grid.addWidget(widget, 1, column)
            selection_grid.addLayout(self._all_none_row(name, widget), 2, column)
        selection_grid.setColumnStretch(0, 3)
        selection_grid.setColumnStretch(1, 1)
        selection_grid.setColumnStretch(2, 3)
        selection_layout.addLayout(selection_grid)
        self.selection_summary = QLabel("No catalog loaded.")
        self.selection_summary.setWordWrap(True)
        qtheme.muted(self.selection_summary)
        selection_layout.addWidget(self.selection_summary)
        selection_group.setEnabled(False)
        outer.addWidget(selection_group)

        output_group = QGroupBox("Output settings")
        self.output_group = output_group
        output_form = QFormLayout(output_group)
        output_row = QHBoxLayout()
        output_row.setContentsMargins(0, 0, 0, 0)
        output_default = (qm.USER_PREFS.get("curated_output_folder")
                          or qm.USER_PREFS.get("dbv_output_path")
                          or qm.USER_PREFS.get("last_output_dir", ""))
        self.output_folder = QLineEdit(output_default)
        self.output_folder.setPlaceholderText(
            "Select where the curated workbook will be saved...")
        self.output_folder.textEdited.connect(self._persist_output)
        browse_output = QPushButton("Browse...")
        browse_output.clicked.connect(self._browse_output)
        browse_output.setToolTip("Select the destination folder; the corpus is never written")
        output_row.addWidget(self.output_folder)
        output_row.addWidget(browse_output)
        output_holder = QWidget()
        output_holder.setLayout(output_row)
        output_form.addRow("Output folder:", output_holder)
        self.output_name = QLineEdit(
            qm.USER_PREFS.get("curated_output_name", "QCS_curated_database"))
        self.output_name.setPlaceholderText("Name the curated .xlsx workbook...")
        self.output_name.textEdited.connect(self._persist_output)
        output_form.addRow("Output name:", self.output_name)
        note = QLabel(
            "One workbook is created. Seaguard, Doppler and HOBO remain in separate "
            "data sheets because their columns and quality flags are not stackable.")
        note.setWordWrap(True)
        qtheme.muted(note)
        output_form.addRow("Structure:", note)
        qtheme.bold_form_labels(output_form)
        outer.addWidget(output_group)

        action_row = QHBoxLayout()
        action_row.addStretch()
        action_box = QWidget()
        action_column = QVBoxLayout(action_box)
        action_column.setContentsMargins(0, 0, 0, 0)
        action_column.setSpacing(4)
        self.build_button = QPushButton("Build curated database")
        self.build_button.setObjectName("AccentButton")
        self.build_button.setMinimumSize(260, 42)
        action_font = self.build_button.font()
        action_font.setBold(True)
        action_font.setPointSizeF(action_font.pointSizeF() + 1)
        self.build_button.setFont(action_font)
        self.build_button.setToolTip(
            "Builds one .xlsx workbook from the selected qualified products")
        self.build_button.clicked.connect(self._build_database)
        self.build_button.setEnabled(False)
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.setToolTip(
            "Stops catalog/build work at the next safe checkpoint; no partial "
            "workbook is published")
        self.cancel_button.clicked.connect(self._cancel_worker)
        self.cancel_button.setVisible(False)
        self.build_hint = QLabel("")
        qtheme.muted(self.build_hint)
        self.build_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.postbuild_bar = QWidget()
        postbuild_layout = QHBoxLayout(self.postbuild_bar)
        postbuild_layout.setContentsMargins(0, 0, 0, 0)
        self.open_output_button = QPushButton("Open output folder")
        self.open_output_button.clicked.connect(self._open_last_output)
        self.visualize_button = QPushButton("Go to visualization")
        self.visualize_button.setToolTip(
            "Opens the curated workbook in Data visualization; choose the "
            "instrument sheet when the workbook contains more than one")
        self.visualize_button.clicked.connect(self._go_to_visualization)
        postbuild_layout.addWidget(self.open_output_button)
        postbuild_layout.addWidget(self.visualize_button)
        self.postbuild_bar.setVisible(False)
        action_column.addWidget(self.build_button, alignment=Qt.AlignmentFlag.AlignHCenter)
        action_column.addWidget(self.cancel_button, alignment=Qt.AlignmentFlag.AlignHCenter)
        action_column.addWidget(self.build_hint, alignment=Qt.AlignmentFlag.AlignHCenter)
        action_column.addWidget(self.postbuild_bar, alignment=Qt.AlignmentFlag.AlignHCenter)
        action_row.addWidget(action_box)
        action_row.addStretch()
        outer.addLayout(action_row)
        outer.addStretch()
        qtheme.enable_clear_buttons(self)
        self._update_build_state()

    @staticmethod
    def _filter_list(_name):
        widget = _RowCheckListWidget()
        widget.setMinimumHeight(190)
        widget.setMaximumHeight(260)
        widget.setAlternatingRowColors(True)
        widget.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        return widget

    def _all_none_row(self, dimension, widget):
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        for text, state in (("All", Qt.CheckState.Checked),
                            ("None", Qt.CheckState.Unchecked)):
            button = QPushButton(text)
            button.setMaximumWidth(64)
            button.clicked.connect(
                lambda _checked=False, name=dimension, target=widget, value=state:
                self._set_all(name, target, value))
            row.addWidget(button)
        row.addStretch()
        return row

    def _set_all(self, dimension, widget, state):
        with QSignalBlocker(widget):
            for index in range(widget.count()):
                item = widget.item(index)
                # None means none in the whole dimension. All applies to the
                # currently compatible facet; incompatible values stay visible
                # but disabled and unchecked.
                enabled = bool(item.flags() & Qt.ItemFlag.ItemIsEnabled)
                if state == Qt.CheckState.Unchecked or enabled:
                    item.setCheckState(state)
        self._selection_changed(dimension)

    @staticmethod
    def _checked_values(widget):
        values = []
        for index in range(widget.count()):
            item = widget.item(index)
            if item.checkState() == Qt.CheckState.Checked:
                values.append(item.data(Qt.ItemDataRole.UserRole))
        return values

    @staticmethod
    def _populate(widget, values, labels=None):
        with QSignalBlocker(widget):
            widget.clear()
            for value in values:
                label = labels[value] if labels else str(value)
                item = QListWidgetItem(label)
                item.setData(Qt.ItemDataRole.UserRole, value)
                item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsUserCheckable)
                item.setCheckState(Qt.CheckState.Checked)
                widget.addItem(item)

    def _source_edited(self, _text):
        self.catalog = None
        self.selection_group.setEnabled(False)
        self.catalog_summary.setText("Source changed; load the catalog again.")
        self._invalidate_postbuild()
        self._update_build_state()
        qm.USER_PREFS["curated_corpus_root"] = self.corpus_root.text().strip()
        qm.save_user_prefs()

    def _browse_corpus(self):
        start = self.corpus_root.text().strip()
        if not os.path.isdir(start):
            start = ""
        path = QFileDialog.getExistingDirectory(self, "Select qualified corpus root", start)
        if path:
            self.corpus_root.setText(path)
            self._source_edited(path)
            qtheme.refresh_clear_buttons(self)

    def apply_dropped_paths(self, paths):
        """A folder dropped on this tab is the corpus root, never qualification input."""
        folders = [path for path in paths if os.path.isdir(path)]
        if len(paths) != 1 or len(folders) != 1:
            QMessageBox.warning(
                self, "Curated database",
                "Drop one corpus folder here. Qualified data files are selected "
                "through the site, year and instrument filters.")
            return
        self.corpus_root.setText(folders[0])
        self._source_edited(folders[0])
        qtheme.refresh_clear_buttons(self)

    def _browse_output(self):
        start = self.output_folder.text().strip()
        if not os.path.isdir(start):
            start = ""
        path = QFileDialog.getExistingDirectory(self, "Select output folder", start)
        if path:
            self.output_folder.setText(path)
            self._persist_output()
            qtheme.refresh_clear_buttons(self)

    def _persist_output(self, _text=None):
        qm.USER_PREFS["curated_output_folder"] = self.output_folder.text().strip()
        qm.USER_PREFS["curated_output_name"] = self.output_name.text().strip()
        qm.save_user_prefs()
        self._invalidate_postbuild()
        self._update_build_state()

    def _invalidate_postbuild(self):
        self.last_output_path = None
        self.last_build_summary = None
        self.postbuild_bar.setVisible(False)

    def _apply_filter_facets(self):
        """Disable impossible choices and clear any that became impossible."""
        if self.catalog is None or self._filter_updating:
            return
        self._filter_updating = True
        try:
            # Convergence is monotonic: an impossible checked value is cleared,
            # then availability is recomputed because that removal can broaden
            # another facet. Values stay visible, so the operator never has an
            # invisible selection or a list that appears to lose entries.
            while True:
                current = {
                    name: self._checked_values(widget)
                    for name, widget in self._filter_widgets.items()
                }
                available = curated.available_filters(
                    self.catalog, current["instruments"], current["sites"],
                    current["years"])
                cleared = False
                for name, widget in self._filter_widgets.items():
                    allowed = set(available[name])
                    with QSignalBlocker(widget):
                        for index in range(widget.count()):
                            item = widget.item(index)
                            compatible = (item.data(Qt.ItemDataRole.UserRole)
                                          in allowed)
                            flags = item.flags()
                            if compatible:
                                flags |= Qt.ItemFlag.ItemIsEnabled
                                item.setToolTip("")
                            else:
                                flags &= ~Qt.ItemFlag.ItemIsEnabled
                                item.setToolTip(
                                    "Unavailable with the other selected filters")
                            item.setFlags(flags)
                            item.setHidden(False)
                            if (not compatible and item.checkState()
                                    == Qt.CheckState.Checked):
                                item.setCheckState(Qt.CheckState.Unchecked)
                                cleared = True
                if not cleared:
                    break
        finally:
            self._filter_updating = False

    def _update_build_state(self, selected=None):
        """Explain the first missing requirement, like Qualification's RUN hint."""
        if self._worker is not None:
            self.build_button.setEnabled(False)
            self.build_hint.clear()
            self.build_hint.setVisible(False)
            self.build_button.setToolTip(
                "Unavailable while the curated operation is running")
            return
        instruments = self._checked_values(self.instrument_list)
        sites = self._checked_values(self.site_list)
        years = self._checked_values(self.year_list)
        if self.catalog is None:
            hint = "load the corpus catalog to begin"
        elif not sites:
            hint = "select at least one Site"
        elif not years:
            hint = "select at least one calendar year"
        elif not instruments:
            hint = "select at least one instrument"
        elif not os.path.isdir(self.output_folder.text().strip()):
            hint = "choose an existing output folder"
        elif not self.output_name.text().strip():
            hint = "name the curated database"
        else:
            if selected is None:
                selected = curated.select_catalog(
                    self.catalog, instruments, sites, years)
            hint = ("no products match the current selection"
                    if selected.empty else "")
        ready = not hint and self._worker is None
        self.build_button.setEnabled(ready)
        self.build_hint.setText(hint)
        self.build_hint.setVisible(bool(hint))
        self.build_button.setToolTip(
            "Builds one .xlsx workbook from the selected qualified products"
            if not hint else "Unavailable: %s" % hint)

    def _start_worker(self, operation, payload, status):
        if self._worker is not None:
            return
        # Both a new build and a catalog refresh invalidate the shortcuts to
        # the workbook produced under the previous catalog state.
        self._invalidate_postbuild()
        set_shell_busy = getattr(self.shell, "set_curated_busy", None)
        if callable(set_shell_busy):
            set_shell_busy(True)
        update_shell_progress = getattr(self.shell, "update_curated_progress", None)
        if callable(update_shell_progress):
            update_shell_progress(status)
            # Paint the known 0/N build state before the worker can queue
            # several very fast stage updates. This makes startup truthful
            # without sleeping or slowing the actual corpus work.
            progress_widget = getattr(self.shell, "progress", None)
            repaint_progress = getattr(progress_widget, "repaint", None)
            if operation == "build" and callable(repaint_progress):
                repaint_progress()
        worker = _CuratedWorker(operation, payload, self)
        if callable(update_shell_progress):
            worker.progress.connect(update_shell_progress)
        worker.succeeded.connect(self._worker_succeeded)
        worker.failed.connect(self._worker_failed)
        worker.cancelled.connect(self._worker_cancelled)
        worker.finished.connect(self._worker_finished)
        self._worker = worker
        self.cancel_button.setText("Cancel")
        self.cancel_button.setEnabled(True)
        self.cancel_button.setVisible(True)
        self._sync_enabled_state()
        worker.start()

    def _worker_finished(self):
        worker, self._worker = self._worker, None
        if worker is not None:
            worker.deleteLater()
        self.cancel_button.setVisible(False)
        self.cancel_button.setText("Cancel")
        self._sync_enabled_state()
        set_shell_busy = getattr(self.shell, "set_curated_busy", None)
        if callable(set_shell_busy):
            set_shell_busy(False)

    def _sync_enabled_state(self):
        """Make worker completion safe regardless of queued signal delivery order."""
        busy = self._worker is not None
        has_catalog = self.catalog is not None
        self.source_group.setEnabled(not busy)
        self.output_group.setEnabled(not busy)
        self.selection_group.setEnabled(has_catalog and not busy)
        if has_catalog and not busy:
            self._selection_changed()
        else:
            self._update_build_state()

    def is_busy(self):
        return self._worker is not None

    def _worker_failed(self, message):
        self.shell.log_line("Error: %s" % message)
        QMessageBox.critical(self, "Curated database", message)

    def _worker_cancelled(self, _message):
        self.shell.log_line(
            "Info: curated database operation canceled; no partial output published.")

    def _cancel_worker(self):
        worker = self._worker
        if worker is None or not worker.isRunning():
            return
        worker.requestInterruption()
        self.cancel_button.setEnabled(False)
        self.cancel_button.setText("Canceling...")
        update_shell_progress = getattr(self.shell, "update_curated_progress", None)
        if callable(update_shell_progress):
            update_shell_progress("Canceling...")
        self.shell.log_line(
            "Cancel requested - the curated operation stops at the next safe checkpoint.")

    def _worker_succeeded(self, operation, result):
        for message in result.get("messages", []):
            self.shell.log_line(message)
        if operation == "catalog":
            self.catalog = result["catalog"]
            filters = curated.available_filters(self.catalog)
            self._populate(self.site_list, filters["sites"])
            self._populate(self.year_list, filters["years"])
            self._populate(self.instrument_list, filters["instruments"],
                           curated.INSTRUMENT_LABELS)
            n_rows = int(self.catalog["n_rows"].sum())
            warning_count = sum(message.startswith("Warning:")
                                for message in result.get("messages", []))
            self.catalog_summary.setText(
                "%s products | %s source rows | %s sites | %s-%s%s"
                % (f"{len(self.catalog):,}", f"{n_rows:,}",
                   f"{len(filters['sites']):,}", min(filters["years"]),
                   max(filters["years"]),
                   " | %d warning(s)" % warning_count if warning_count else ""))
            self.load_button.setText("Refresh catalog")
            self._sync_enabled_state()
            if warning_count:
                QMessageBox.warning(
                    self, "Curated database catalog",
                    "%d product warning(s) occurred while loading the catalog. "
                    "Affected products were not included; review the Execution log."
                    % warning_count)
            return

        summary = result["summary"]
        self.last_output_path = result["output_path"]
        self.last_build_summary = summary
        self.postbuild_bar.setVisible(True)
        row_details = ", ".join(
            "%s: %s" % (curated.INSTRUMENT_LABELS[name], f"{count:,}")
            for name, count in summary["rows_by_instrument"].items())
        self.shell.log_line(
            "Done: curated database: %d product(s), %d selected row(s) -> %s"
            % (summary["products"], summary["rows"], result["output_path"]))
        QMessageBox.information(
            self, "Curated database created",
            "Workbook created successfully.\n\n"
            "%s selected product(s); %s contributed unique rows\n"
            "%s selected row(s)\n%s\n\n%s"
            % (f"{summary['products']:,}",
               f"{summary['contributing_products']:,}", f"{summary['rows']:,}",
               row_details, result["output_path"]))

    def _load_catalog(self):
        root = self.corpus_root.text().strip()
        if not root:
            QMessageBox.warning(self, "Curated database", "Select the corpus folder first.")
            return
        qm.USER_PREFS["curated_corpus_root"] = root
        qm.save_user_prefs()
        self._start_worker(
            "catalog", {"corpus_root": root}, "Discovering qualified products...")

    def _selection_changed(self, dimension=None):
        if self.catalog is None:
            self._update_build_state()
            return
        if dimension is not None:
            self._invalidate_postbuild()
        self._apply_filter_facets()
        instruments = self._checked_values(self.instrument_list)
        sites = self._checked_values(self.site_list)
        years = self._checked_values(self.year_list)
        selected = curated.select_catalog(self.catalog, instruments, sites, years)
        if selected.empty:
            self.selection_summary.setText("No products match the current selection.")
            self._update_build_state(selected)
            return
        source_rows = int(selected["n_rows"].sum())
        size_warning = (
            " | Large selection: the build may take several minutes"
            if source_rows >= LARGE_SELECTION_ROW_THRESHOLD else "")
        self.selection_summary.setText(
            "%s products match | %s source rows before exact calendar/site trimming%s"
            % (f"{len(selected):,}", f"{source_rows:,}", size_warning))
        self._update_build_state(selected)

    def _open_last_output(self):
        folder = os.path.dirname(self.last_output_path or "")
        if folder and os.path.isdir(folder):
            os.startfile(folder)
            return
        QMessageBox.warning(
            self, "Curated database",
            "The output folder no longer exists:\n%s" % folder)

    def _go_to_visualization(self):
        path = self.last_output_path
        summary = self.last_build_summary or {}
        instruments = list(summary.get("instruments", []))
        if not path or not os.path.isfile(path) or not instruments:
            QMessageBox.warning(
                self, "Curated database",
                "The curated workbook is no longer available for visualization.")
            return
        instrument = instruments[0]
        if len(instruments) > 1:
            labels = [curated.INSTRUMENT_LABELS[name] for name in instruments]
            label, accepted = QInputDialog.getItem(
                self, "Go to visualization", "Instrument sheet:",
                labels, 0, False)
            if not accepted:
                return
            instrument = instruments[labels.index(label)]
        handoff = getattr(self.shell, "open_curated_visualization", None)
        if callable(handoff):
            handoff(path, instrument)
        else:
            QMessageBox.warning(
                self, "Curated database",
                "Data visualization is not available in this session.")

    def _build_database(self):
        instruments = self._checked_values(self.instrument_list)
        sites = self._checked_values(self.site_list)
        years = self._checked_values(self.year_list)
        if not instruments or not sites or not years:
            QMessageBox.warning(
                self, "Curated database",
                "Select at least one site, one calendar year and one instrument.")
            return
        folder = self.output_folder.text().strip()
        if not os.path.isdir(folder):
            QMessageBox.warning(
                self, "Curated database", "Select an existing output folder.")
            return
        name = self.output_name.text().strip()
        if not name:
            QMessageBox.warning(self, "Curated database", "Define an output name.")
            return
        if not name.lower().endswith(".xlsx"):
            name += ".xlsx"
        output_path = os.path.join(folder, name)
        if os.path.exists(output_path):
            answer = QMessageBox.question(
                self, "Replace curated database?",
                "The output file already exists:\n%s\n\nReplace it?" % output_path)
            if answer != QMessageBox.StandardButton.Yes:
                return
        selected = curated.select_catalog(
            self.catalog, instruments, sites, years)
        active_instruments = [
            instrument for instrument in curated.INSTRUMENT_ORDER
            if instrument in set(selected["instrument"])]
        total_stages = len(active_instruments) + 2
        source_rows = int(selected["n_rows"].sum())
        if source_rows >= LARGE_SELECTION_ROW_THRESHOLD:
            answer = QMessageBox.question(
                self, "Large curated selection",
                "%s products match this selection, representing up to %s "
                "source rows before exact calendar/site trimming.\n\n"
                "Building the workbook may take several minutes and QCS may "
                "respond slowly. Cancel remains available during processing.\n\n"
                "Continue?"
                % (f"{len(selected):,}", f"{source_rows:,}"))
            if answer != QMessageBox.StandardButton.Yes:
                return
        self._persist_output()
        self._start_worker("build", {
            "catalog": self.catalog.copy(),
            "corpus_root": self.corpus_root.text().strip(),
            "instruments": instruments,
            "active_instruments": active_instruments,
            "sites": sites,
            "years": years,
            "output_path": output_path,
        }, "Stage 0/%d - Preparing" % total_stages)

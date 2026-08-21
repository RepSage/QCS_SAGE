# -*- coding: utf-8 -*-
"""Qt Settings dialog for the v12.0 shell (phase 2).

The same three tabs as the tk Settings window - Quality control tests,
Parameters, Statistical thresholds - reading and writing the SAME CONFIG
dictionaries through the toolkit-free core in QCS_Main
(apply_settings_values / persist_quality_criteria / DEFAULT_QUALITY_CONFIG),
so the two shells can never validate or persist differently.
"""
from PySide6.QtCore import QSize
from PySide6.QtWidgets import (QCheckBox, QDialog, QGridLayout, QHBoxLayout,
                               QGroupBox, QLabel, QLineEdit, QMessageBox, QPushButton,
                               QScrollArea, QTabWidget, QToolButton,
                               QVBoxLayout, QWidget)

import QCS_Main as qm
import QCS_QtTheme as qtheme


def _bold(text):
    lab = QLabel(text)
    f = lab.font()
    f.setBold(True)
    lab.setFont(f)
    return lab


def _scrolled(inner):
    area = QScrollArea()
    area.setWidgetResizable(True)
    area.setWidget(inner)
    return area


class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Quality control settings')
        self.resize(900, 700)
        self._rows = []
        self._filter_groups = []
        v = QVBoxLayout(self)
        # search box: the Parameters tab is long, and hunting for one limit
        # by scrolling was the slow part (owner request, 2026-08-17)
        search_row = QHBoxLayout()
        search_row.addWidget(QLabel('Find:'))
        self.search = QLineEdit()
        self.search.setPlaceholderText('Filter the rows by name, e.g. "temp" or "lux"')
        self.search.textChanged.connect(self._apply_filter)
        search_row.addWidget(self.search)
        edited_hint = QLabel('Bold = differs from defaults')
        hint_font = edited_hint.font()
        hint_font.setBold(True)
        edited_hint.setFont(hint_font)
        edited_hint.setToolTip('Only values or switches that differ from the installed '
                               'defaults are shown in bold.')
        search_row.addWidget(edited_hint)
        v.addLayout(search_row)
        tabs = QTabWidget()
        tabs.addTab(self._tests_tab(), 'Quality control tests')
        tabs.addTab(self._params_tab(), 'Parameters')
        tabs.addTab(self._factors_tab(), 'Statistical thresholds')
        v.addWidget(tabs)
        self._mark_non_defaults()
        btns = QHBoxLayout()
        reset = QPushButton('Reset to defaults')
        reset.clicked.connect(self._reset)
        save = QPushButton('Save settings')
        save.setDefault(True)
        save.clicked.connect(self._save)
        btns.addWidget(reset)
        btns.addStretch()
        btns.addWidget(save)
        v.addLayout(btns)

    # ----- tabs -----
    def _add_row(self, widgets, text):
        """Registers a logical row for the search filter (hiding every widget
        of a grid row collapses it)."""
        entry = (widgets, text.lower())
        self._rows.append(entry)
        return entry

    def _tests_tab(self):
        w = QWidget()
        v = QVBoxLayout(w)
        self.test_boxes = {}
        for instrument, categories in qm.QUALITY_TEST_GROUPS:
            box = QGroupBox(instrument)
            box_layout = QVBoxLayout(box)
            group_rows = []
            for category, tests in categories:
                head = _bold(category)
                box_layout.addWidget(head)
                group_rows.append(self._add_row(
                    [head], '%s %s' % (instrument, category)))
                for test, label in tests:
                    cb = QCheckBox(label)
                    cb.setObjectName('test_' + test.replace(' ', '_'))
                    cb.setProperty('test_key', test)
                    cb.setChecked(qm.CONFIG['tsQualityTests'][test] == 'ON')
                    cb.setToolTip(qm.TS_QUALITY_TESTS_TOOLTIPS[test])
                    cb.toggled.connect(lambda _on: self._tests_changed())
                    # Indented by its own LAYOUT, never by a stylesheet: an
                    # unqualified rule ('margin-left: 18px') is inherited by the
                    # widget's TOOLTIP, which then opened with an empty strip on
                    # its left.
                    holder = QWidget()
                    indent = QHBoxLayout(holder)
                    indent.setContentsMargins(18, 0, 0, 0)
                    indent.addWidget(cb)
                    box_layout.addWidget(holder)
                    self.test_boxes[test] = cb
                    group_rows.append(self._add_row(
                        [holder], '%s %s %s %s'
                        % (instrument, category, label, test)))
            self._filter_groups.append((box, group_rows))
            v.addWidget(box)
        v.addStretch()
        return _scrolled(w)

    def _tests_changed(self):
        self._mark_non_defaults()
        self._sync_factor_enabled()

    def _reset_button(self, tip, on_click):
        btn = QToolButton()
        # painted icon, not the U+21BA glyph: the font's version was coarse
        # beside the rest of the interface (owner, 2026-08-19). Drawn at 20 px
        # rather than 16: the shape is a PAIR of arcs, and at 16 px each head
        # is about three pixels and stops reading as an arrow.
        btn.setIcon(qtheme.reset_icon(20))
        btn.setIconSize(QSize(20, 20))
        btn.setToolTip(tip)
        btn.setAutoRaise(True)
        btn.clicked.connect(on_click)
        return btn

    def _params_tab(self):
        w = QWidget()
        outer = QVBoxLayout(w)
        self.setting_edits = {}

        def add_edit(grid, key, r, col):
            edit = QLineEdit(str(qm.CONFIG['tsSettings'][key]))
            edit.setFixedWidth(90)
            edit.setToolTip(qm.TS_SETTINGS_TOOLTIPS[key])
            grid.addWidget(edit, r, col)
            self.setting_edits[key] = edit
            edit.textChanged.connect(lambda _t: self._mark_non_defaults())
            return edit

        def reset_keys(keys):
            for k in keys:
                if k in self.setting_edits:
                    self.setting_edits[k].setText(
                        str(qm.DEFAULT_QUALITY_CONFIG['tsSettings'][k]))

        for instrument, sections in qm.PARAMETER_GROUPS:
            box = QGroupBox(instrument)
            grid = QGridLayout(box)
            group_rows = []
            row = 0
            for kind, title, definitions in sections:
                head = _bold(title)
                grid.addWidget(head, row, 0, 1, 5)
                group_rows.append(self._add_row(
                    [head], '%s %s' % (instrument, title)))
                row += 1
                if kind == 'range':
                    hmin, hmax = QLabel('Min'), QLabel('Max')
                    grid.addWidget(hmin, row, 1)
                    grid.addWidget(hmax, row, 2)
                    group_rows.append(self._add_row(
                        [hmin, hmax], '%s %s minimum maximum' % (instrument, title)))
                    row += 1
                    for variable, label, min_key, max_key, unit in definitions:
                        lab = QLabel(label + ':')
                        grid.addWidget(lab, row, 0)
                        widgets = [lab, add_edit(grid, min_key, row, 1),
                                   add_edit(grid, max_key, row, 2)]
                        if unit:
                            ulab = QLabel(unit)
                            grid.addWidget(ulab, row, 3)
                            widgets.append(ulab)
                        btn = self._reset_button(
                            'Restores the default %s %s range'
                            % (instrument.lower(), label.lower()),
                            lambda _c=False, kk=(min_key, max_key): reset_keys(kk))
                        grid.addWidget(btn, row, 4)
                        widgets.append(btn)
                        group_rows.append(self._add_row(
                            widgets, '%s %s %s %s' %
                            (instrument, title, label, variable)))
                        row += 1
                else:
                    for key, label, unit in definitions:
                        lab = QLabel(label + ':')
                        grid.addWidget(lab, row, 0)
                        widgets = [lab, add_edit(grid, key, row, 1)]
                        if unit:
                            ulab = QLabel(unit)
                            grid.addWidget(ulab, row, 2)
                            widgets.append(ulab)
                        btn = self._reset_button(
                            'Restores the default %s' % label.lower(),
                            lambda _c=False, kk=(key,): reset_keys(kk))
                        grid.addWidget(btn, row, 4)
                        widgets.append(btn)
                        group_rows.append(self._add_row(
                            widgets, '%s %s %s %s' %
                            (instrument, title, label, key)))
                        row += 1
            grid.setColumnStretch(5, 1)
            self._filter_groups.append((box, group_rows))
            outer.addWidget(box)
        outer.addStretch()
        return _scrolled(w)

    def _factors_tab(self):
        w = QWidget()
        outer = QVBoxLayout(w)
        self.factor_edits = {}
        self.factor_row_widgets = {}

        def reset_factor(key):
            for field in self.factor_edits[key]:
                self.factor_edits[key][field].setText(
                    str(qm.DEFAULT_QUALITY_CONFIG['tsFactors'][key][field]))

        field_labels = {'fail': 'Bad factor', 'susp': 'Suspect factor',
                        'window': 'Time window'}
        for instrument, sections in qm.FACTOR_SECTIONS:
            box = QGroupBox(instrument)
            box_layout = QVBoxLayout(box)
            group_rows = []
            if not sections:
                note = QLabel('Doppler uses direct physical thresholds in the Parameters tab; '
                              'it has no statistical-factor controls.')
                note.setWordWrap(True)
                box_layout.addWidget(note)
                group_rows.append(self._add_row(
                    [note], instrument + ' parameters direct physical thresholds'))
            for section, definitions in sections:
                head = _bold(section)
                box_layout.addWidget(head)
                group_rows.append(self._add_row(
                    [head], '%s %s' % (instrument, section)))
                grid = QGridLayout()
                box_layout.addLayout(grid)
                fields = definitions[0][2]
                headers = [_bold('Variable')]
                grid.addWidget(headers[0], 0, 0)
                for col, field in enumerate(fields, start=1):
                    label = _bold(field_labels[field])
                    grid.addWidget(label, 0, col)
                    headers.append(label)
                group_rows.append(self._add_row(
                    headers, '%s %s variable %s'
                    % (instrument, section, ' '.join(fields))))
                for row, (key, display, row_fields) in enumerate(definitions, start=1):
                    lab = QLabel(display)
                    grid.addWidget(lab, row, 0)
                    cfg = qm.CONFIG['tsFactors'][key]
                    edits = {}
                    widgets = [lab]
                    for col, field in enumerate(row_fields, start=1):
                        edit = QLineEdit(str(cfg[field]))
                        edit.setFixedWidth(90)
                        edit.setToolTip(qm.TS_FACTORS_TOOLTIPS[field])
                        edit.textChanged.connect(lambda _t: self._mark_non_defaults())
                        grid.addWidget(edit, row, col)
                        edits[field] = edit
                        widgets.append(edit)
                    self.factor_edits[key] = edits
                    btn = self._reset_button(
                        'Restores the default %s %s thresholds'
                        % (display.lower(), section.lower()),
                        lambda _c=False, kk=key: reset_factor(kk))
                    grid.addWidget(btn, row, len(row_fields) + 1)
                    widgets.append(btn)
                    self.factor_row_widgets[key] = widgets
                    group_rows.append(self._add_row(
                        widgets, '%s %s %s %s thresholds'
                        % (instrument, section, display, key)))
                grid.setColumnStretch(len(fields) + 2, 1)
            self._filter_groups.append((box, group_rows))
            outer.addWidget(box)
        outer.addStretch()
        self._sync_factor_enabled()
        return _scrolled(w)

    def _sync_factor_enabled(self):
        if not hasattr(self, 'factor_row_widgets'):
            return
        for key, widgets in self.factor_row_widgets.items():
            switch = qm.FACTOR_TEST_SWITCHES[key]
            checkbox = getattr(self, 'test_boxes', {}).get(switch)
            enabled = checkbox.isChecked() if checkbox is not None else (
                qm.CONFIG['tsQualityTests'].get(switch, 'OFF') == 'ON')
            for widget in widgets:
                widget.setEnabled(enabled)

    # ----- default markers and search -----
    def _mark_non_defaults(self):
        """Bolds every field whose value differs from the software default, so
        a custom criterion is visible at a glance (owner request)."""
        d = qm.DEFAULT_QUALITY_CONFIG

        def mark(widget, differs):
            f = widget.font()
            if f.bold() != differs:
                f.setBold(differs)
                widget.setFont(f)

        def text_differs(value, default):
            value = value.strip()
            if isinstance(default, (int, float)):
                try:
                    return float(value) != float(default)
                except ValueError:
                    return True
            return value.upper() != str(default).strip().upper()

        for key, edit in self.setting_edits.items():
            mark(edit, text_differs(edit.text(), d['tsSettings'][key]))
        for test, cb in self.test_boxes.items():
            mark(cb, ('ON' if cb.isChecked() else 'OFF') != d['tsQualityTests'][test])
        for key, edits in self.factor_edits.items():
            for field, edit in edits.items():
                mark(edit, text_differs(edit.text(), d['tsFactors'][key][field]))

    def _apply_filter(self, text):
        needle = text.strip().lower()
        row_visibility = {}
        for entry in self._rows:
            widgets, haystack = entry
            visible = not needle or needle in haystack
            row_visibility[id(entry)] = visible
            for w in widgets:
                w.setVisible(visible)
        for box, entries in self._filter_groups:
            box.setVisible(any(row_visibility.get(id(entry), True)
                               for entry in entries))

    # ----- actions -----
    def _save(self):
        # a filtered view must not save a partial picture: every widget is
        # read regardless of visibility (the filter only hides rows)
        tests = {t: ('ON' if cb.isChecked() else 'OFF')
                 for t, cb in self.test_boxes.items()}
        settings_text = {p: e.text() for p, e in self.setting_edits.items()}
        factors_text = {k: {f: e.text() for f, e in es.items()}
                        for k, es in self.factor_edits.items()}
        invalid = qm.apply_settings_values(tests, settings_text, factors_text)
        if invalid:
            QMessageBox.warning(
                self, 'Invalid values',
                'These fields are not valid and kept their previous value:\n\n- '
                + '\n- '.join(invalid)
                + '\n\nFix them and click Save settings again.')
            return
        qm.persist_quality_criteria()
        QMessageBox.information(self, 'Success', 'Success saving settings!')
        self.accept()

    def _reset(self):
        answer = QMessageBox.question(
            self, 'Reset to defaults',
            'Replace ALL quality tests, parameters and factors\n'
            'with the software defaults?')
        if answer != QMessageBox.StandardButton.Yes:
            return
        qm.CONFIG['tsQualityTests'].update(qm.DEFAULT_QUALITY_CONFIG['tsQualityTests'])
        qm.CONFIG['tsSettings'].update(qm.DEFAULT_QUALITY_CONFIG['tsSettings'])
        for k, v in qm.DEFAULT_QUALITY_CONFIG['tsFactors'].items():
            qm.CONFIG['tsFactors'][k].update(v)
        # reflect the defaults in the open widgets
        for test, cb in self.test_boxes.items():
            cb.setChecked(qm.CONFIG['tsQualityTests'][test] == 'ON')
        for param, edit in self.setting_edits.items():
            edit.setText(str(qm.CONFIG['tsSettings'][param]))
        for key, edits in self.factor_edits.items():
            for field in edits:
                edits[field].setText(str(qm.CONFIG['tsFactors'][key][field]))
        self._sync_factor_enabled()
        self._mark_non_defaults()

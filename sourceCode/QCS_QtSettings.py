# -*- coding: utf-8 -*-
"""Qt Settings dialog for the v12.0 shell (phase 2).

The same three tabs as the tk Settings window - Quality control tests,
Parameters, Factors per variable - reading and writing the SAME CONFIG
dictionaries through the toolkit-free core in QCS_Main
(apply_settings_values / persist_quality_criteria / DEFAULT_QUALITY_CONFIG),
so the two shells can never validate or persist differently.
"""
from PySide6.QtWidgets import (QCheckBox, QDialog, QGridLayout, QHBoxLayout,
                               QLabel, QLineEdit, QMessageBox, QPushButton,
                               QScrollArea, QTabWidget, QToolButton,
                               QVBoxLayout, QWidget)

import QCS_Main as qm


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
        v = QVBoxLayout(self)
        # search box: the Parameters tab is long, and hunting for one limit
        # by scrolling was the slow part (owner request, 2026-08-17)
        search_row = QHBoxLayout()
        search_row.addWidget(QLabel('Find:'))
        self.search = QLineEdit()
        self.search.setPlaceholderText('Filter the rows by name, e.g. "temp" or "lux"')
        self.search.textChanged.connect(self._apply_filter)
        search_row.addWidget(self.search)
        v.addLayout(search_row)
        tabs = QTabWidget()
        tabs.addTab(self._tests_tab(), 'Quality control tests')
        tabs.addTab(self._params_tab(), 'Parameters')
        tabs.addTab(self._factors_tab(), 'Factors per variable')
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
        self._rows.append((widgets, text.lower()))

    def _tests_tab(self):
        w = QWidget()
        v = QVBoxLayout(w)
        self.test_boxes = {}
        self._rows = getattr(self, '_rows', [])
        for category, tests in qm.TEST_CATEGORIES.items():
            head = _bold(category)
            v.addWidget(head)
            self._add_row([head], category)
            for test in tests:
                cb = QCheckBox(test)
                cb.setChecked(qm.CONFIG['tsQualityTests'][test] == 'ON')
                cb.setToolTip(qm.TS_QUALITY_TESTS_TOOLTIPS[test])
                cb.setStyleSheet('margin-left: 18px;')
                cb.toggled.connect(lambda _on: self._mark_non_defaults())
                v.addWidget(cb)
                self.test_boxes[test] = cb
                self._add_row([cb], test)
        v.addStretch()
        return _scrolled(w)

    def _reset_button(self, tip, on_click):
        btn = QToolButton()
        btn.setText('↺')
        btn.setToolTip(tip)
        btn.setAutoRaise(True)
        btn.clicked.connect(on_click)
        return btn

    def _params_tab(self):
        w = QWidget()
        grid = QGridLayout(w)
        self.setting_edits = {}
        self._rows = getattr(self, '_rows', [])

        def add_edit(key, r, col):
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

        row = 0
        # range sections: one row per variable, Min and Max side by side
        for prefix, title in (('sensor', 'Sensor Range'), ('env', 'Environmental Range')):
            head = _bold(title)
            grid.addWidget(head, row, 0, 1, 5)
            self._add_row([head], title)
            row += 1
            hmin, hmax = QLabel('Min'), QLabel('Max')
            grid.addWidget(hmin, row, 1)
            grid.addWidget(hmax, row, 2)
            self._add_row([hmin, hmax], title)
            row += 1
            variables = []
            for k in qm.CONFIG['tsSettings']:
                if k.startswith(prefix + '_min_'):
                    var = k[len(prefix + '_min_'):]
                    if var not in variables:
                        variables.append(var)
            for var in variables:
                name = qm._PARAM_NAME.get(var, var)
                lab = QLabel(name + ':')
                grid.addWidget(lab, row, 0)
                keys = ['%s_min_%s' % (prefix, var)]
                widgets = [lab, add_edit(keys[0], row, 1)]
                max_key = '%s_max_%s' % (prefix, var)
                if max_key in qm.CONFIG['tsSettings']:
                    keys.append(max_key)
                    widgets.append(add_edit(max_key, row, 2))
                unit = qm._PARAM_UNIT.get(var, '')
                if unit:
                    ulab = QLabel(unit)
                    grid.addWidget(ulab, row, 3)
                    widgets.append(ulab)
                btn = self._reset_button('Restores the default %s %s range'
                                         % (title.lower(), name.lower()),
                                         lambda _c=False, kk=tuple(keys): reset_keys(kk))
                grid.addWidget(btn, row, 4)
                widgets.append(btn)
                self._add_row(widgets, '%s %s %s' % (title, name, var))
                row += 1

        head = _bold('Current profiler (Doppler)')
        grid.addWidget(head, row, 0, 1, 5)
        self._add_row([head], 'current profiler doppler')
        row += 1
        for key, label, unit in qm._DOPPLER_PARAMS:
            lab = QLabel(label + ':')
            grid.addWidget(lab, row, 0)
            widgets = [lab, add_edit(key, row, 1)]
            ulab = QLabel(unit)
            grid.addWidget(ulab, row, 2)
            btn = self._reset_button('Restores the default %s' % label.lower(),
                                     lambda _c=False, kk=(key,): reset_keys(kk))
            grid.addWidget(btn, row, 4)
            widgets += [ulab, btn]
            self._add_row(widgets, '%s %s doppler current' % (label, key))
            row += 1

        head = _bold('Other parameters')
        grid.addWidget(head, row, 0, 1, 5)
        self._add_row([head], 'other parameters')
        row += 1
        for key in qm.CONFIG['tsSettings']:
            if 'sensor_' in key or 'env_' in key or key.startswith('doppler_'):
                continue
            label = key.replace('_', ' ').title()
            lab = QLabel(label + ':')
            grid.addWidget(lab, row, 0)
            widgets = [lab, add_edit(key, row, 1)]
            unit = qm._OTHER_UNIT.get(key, '')
            if unit:
                ulab = QLabel(unit)
                grid.addWidget(ulab, row, 2)
                widgets.append(ulab)
            btn = self._reset_button('Restores the default %s' % label.lower(),
                                     lambda _c=False, kk=(key,): reset_keys(kk))
            grid.addWidget(btn, row, 4)
            widgets.append(btn)
            self._add_row(widgets, '%s %s' % (label, key))
            row += 1
        grid.setRowStretch(row, 1)
        grid.setColumnStretch(5, 1)
        return _scrolled(w)

    def _factors_tab(self):
        w = QWidget()
        grid = QGridLayout(w)
        self._rows = getattr(self, '_rows', [])
        head = _bold('Spike / rate of change / vertical gradient thresholds')
        grid.addWidget(head, 0, 0, 1, 5)
        self._add_row([head], 'spike rate of change vertical gradient thresholds')
        headers = []
        for col, title in enumerate(['Variable', 'Fail factor', 'Susp factor',
                                     'Time window']):
            lab = _bold(title)
            grid.addWidget(lab, 1, col)
            headers.append(lab)
        self._add_row(headers, 'variable fail susp window')
        self.factor_edits = {}

        def reset_factor(key):
            for field in ('fail', 'susp', 'window'):
                self.factor_edits[key][field].setText(
                    str(qm.DEFAULT_QUALITY_CONFIG['tsFactors'][key][field]))

        for i, (key, display) in enumerate(qm.FACTOR_VARS):
            r = i + 2
            lab = QLabel(display)
            grid.addWidget(lab, r, 0)
            cfg = qm.CONFIG['tsFactors'][key]
            edits = {}
            widgets = [lab]
            for col, field in ((1, 'fail'), (2, 'susp'), (3, 'window')):
                edit = QLineEdit(str(cfg[field]))
                edit.setFixedWidth(80)
                edit.setToolTip(qm.TS_FACTORS_TOOLTIPS[field])
                edit.textChanged.connect(lambda _t: self._mark_non_defaults())
                grid.addWidget(edit, r, col)
                edits[field] = edit
                widgets.append(edit)
            self.factor_edits[key] = edits
            btn = self._reset_button('Restores the default %s factors' % display.lower(),
                                     lambda _c=False, kk=key: reset_factor(kk))
            grid.addWidget(btn, r, 4)
            widgets.append(btn)
            self._add_row(widgets, '%s %s factors' % (display, key))
        grid.setRowStretch(len(qm.FACTOR_VARS) + 2, 1)
        grid.setColumnStretch(5, 1)
        return _scrolled(w)

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
            widget.setToolTip(widget.toolTip().split('\n[edited')[0]
                              + ('\n[edited - differs from the default]' if differs else ''))

        for key, edit in self.setting_edits.items():
            mark(edit, edit.text().strip() != str(d['tsSettings'][key]))
        for test, cb in self.test_boxes.items():
            mark(cb, ('ON' if cb.isChecked() else 'OFF') != d['tsQualityTests'][test])
        for key, edits in self.factor_edits.items():
            for field, edit in edits.items():
                mark(edit, edit.text().strip() != str(d['tsFactors'][key][field]))

    def _apply_filter(self, text):
        needle = text.strip().lower()
        for widgets, haystack in self._rows:
            visible = not needle or needle in haystack
            for w in widgets:
                w.setVisible(visible)

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
            for field in ('fail', 'susp', 'window'):
                edits[field].setText(str(qm.CONFIG['tsFactors'][key][field]))
        self._mark_non_defaults()

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
                               QScrollArea, QTabWidget, QVBoxLayout, QWidget)

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
        tabs = QTabWidget()
        tabs.addTab(self._tests_tab(), 'Quality control tests')
        tabs.addTab(self._params_tab(), 'Parameters')
        tabs.addTab(self._factors_tab(), 'Factors per variable')
        v.addWidget(tabs)
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
    def _tests_tab(self):
        w = QWidget()
        v = QVBoxLayout(w)
        self.test_boxes = {}
        for category, tests in qm.TEST_CATEGORIES.items():
            v.addWidget(_bold(category))
            for test in tests:
                cb = QCheckBox(test)
                cb.setChecked(qm.CONFIG['tsQualityTests'][test] == 'ON')
                cb.setToolTip(qm.TS_QUALITY_TESTS_TOOLTIPS[test])
                cb.setStyleSheet('margin-left: 18px;')
                v.addWidget(cb)
                self.test_boxes[test] = cb
        v.addStretch()
        return _scrolled(w)

    def _params_tab(self):
        w = QWidget()
        grid = QGridLayout(w)
        self.setting_edits = {}

        def add_edit(key, r, col):
            edit = QLineEdit(str(qm.CONFIG['tsSettings'][key]))
            edit.setFixedWidth(90)
            edit.setToolTip(qm.TS_SETTINGS_TOOLTIPS[key])
            grid.addWidget(edit, r, col)
            self.setting_edits[key] = edit

        row = 0
        # range sections: one row per variable, Min and Max side by side
        for prefix, title in (('sensor', 'Sensor Range'), ('env', 'Environmental Range')):
            grid.addWidget(_bold(title), row, 0, 1, 4)
            row += 1
            grid.addWidget(QLabel('Min'), row, 1)
            grid.addWidget(QLabel('Max'), row, 2)
            row += 1
            variables = []
            for k in qm.CONFIG['tsSettings']:
                if k.startswith(prefix + '_min_'):
                    var = k[len(prefix + '_min_'):]
                    if var not in variables:
                        variables.append(var)
            for var in variables:
                grid.addWidget(QLabel(qm._PARAM_NAME.get(var, var) + ':'), row, 0)
                add_edit('%s_min_%s' % (prefix, var), row, 1)
                max_key = '%s_max_%s' % (prefix, var)
                if max_key in qm.CONFIG['tsSettings']:
                    add_edit(max_key, row, 2)
                unit = qm._PARAM_UNIT.get(var, '')
                if unit:
                    grid.addWidget(QLabel(unit), row, 3)
                row += 1

        grid.addWidget(_bold('Current profiler (Doppler)'), row, 0, 1, 4)
        row += 1
        for key, label, unit in qm._DOPPLER_PARAMS:
            grid.addWidget(QLabel(label + ':'), row, 0)
            add_edit(key, row, 1)
            grid.addWidget(QLabel(unit), row, 2)
            row += 1

        grid.addWidget(_bold('Other parameters'), row, 0, 1, 4)
        row += 1
        for key in qm.CONFIG['tsSettings']:
            if 'sensor_' in key or 'env_' in key or key.startswith('doppler_'):
                continue
            grid.addWidget(QLabel(key.replace('_', ' ').title() + ':'), row, 0)
            add_edit(key, row, 1)
            unit = qm._OTHER_UNIT.get(key, '')
            if unit:
                grid.addWidget(QLabel(unit), row, 2)
            row += 1
        grid.setRowStretch(row, 1)
        grid.setColumnStretch(4, 1)
        return _scrolled(w)

    def _factors_tab(self):
        w = QWidget()
        grid = QGridLayout(w)
        grid.addWidget(_bold('Spike / rate of change / vertical gradient thresholds'),
                       0, 0, 1, 4)
        for col, title in enumerate(['Variable', 'Fail factor', 'Susp factor',
                                     'Time window']):
            grid.addWidget(_bold(title), 1, col)
        self.factor_edits = {}
        for i, (key, display) in enumerate(qm.FACTOR_VARS):
            r = i + 2
            grid.addWidget(QLabel(display), r, 0)
            cfg = qm.CONFIG['tsFactors'][key]
            edits = {}
            for col, field in ((1, 'fail'), (2, 'susp'), (3, 'window')):
                edit = QLineEdit(str(cfg[field]))
                edit.setFixedWidth(80)
                edit.setToolTip(qm.TS_FACTORS_TOOLTIPS[field])
                grid.addWidget(edit, r, col)
                edits[field] = edit
            self.factor_edits[key] = edits
        grid.setRowStretch(len(qm.FACTOR_VARS) + 2, 1)
        grid.setColumnStretch(4, 1)
        return _scrolled(w)

    # ----- actions -----
    def _save(self):
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

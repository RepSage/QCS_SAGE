"""Exercise replicate review via the real Qt window/worker bridge, offscreen.

Run with packaging/v12_env Python (PySide6 6.8.3); no preferences are written.
"""
import hashlib
import json
import os
from pathlib import Path
import sys
import faulthandler

trace = Path(__file__).with_name('qt_review_trace.log').open('w')
faulthandler.enable(file=trace)
faulthandler.dump_traceback_later(30, file=trace)

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'sourceCode'))
os.environ['QT_QPA_PLATFORM'] = 'offscreen'
settings = ROOT / 'sourceCode/qcs_user_settings.json'
before = hashlib.sha256(settings.read_bytes()).hexdigest()
import QCS_Theme as theme
theme.install_output_redirect = lambda: type('Sink', (), {'set_sink': lambda *a: None})()
theme.install_crash_handler = lambda *a, **k: None
import QCS_Main as qm
import QCS_DatabaseView as dbv
qm.save_user_prefs = lambda *a, **k: None
dbv.save_user_prefs = lambda *a, **k: None
import QCS_QtApp as qt
sys.excepthook = sys.__excepthook__
import pandas as pd
from matplotlib.backend_bases import KeyEvent

app = qt.QApplication([])
app.setQuitOnLastWindowClosed(False)
qt.qtheme.apply_style(False)
root = qm.Tk()
root.withdraw()
frame = qm.ttk.Frame(root)
qm.build_qualification_tab(frame, root)
qt._BRIDGE = qt._GuiBridge()
qm.wait_figure_close = qt._on_gui(qt.wait_figure_close)
theme.style_plot_window = qt._qt_style_plot_window
times = pd.date_range('2025-09-01', periods=40, freq='D')
a = pd.DataFrame({'Datetime': times, 'Temperature (degC)': 29.})
b = pd.DataFrame({'Datetime': times, 'Temperature (degC)': 25.})
referee = {'recommended': 1, 'scores': [], 'verdict': 'Synthetic review control test'}
results = {'decisions': [], 'window_on_gui_thread': [], 'error': None}


class Worker(qt.QThread):
    case = 0

    def run(self):
        try:
            for case in range(2):
                self.case = case
                results['decisions'].append(qm.review_replicates([a, b], referee, None, 'TEST'))
        except Exception as exc:
            results['error'] = repr(exc)


worker = Worker()
handled = set()


def operate():
    for window in list(qt.PlotWindow._windows):
        case = worker.case
        if case in handled:
            continue
        handled.add(case)
        results['window_on_gui_thread'].append(window.thread() is app.thread())
        if case == 0:
            window.grab().save(str(Path(__file__).with_name('replicate_review.png')))
            window.close()
        else:
            canvas = window._canvas
            canvas.callbacks.process('key_press_event', KeyEvent('key_press_event', canvas, key='a'))
            canvas.callbacks.process('key_press_event', KeyEvent('key_press_event', canvas, key='enter'))


timer = qt.QTimer()
timer.timeout.connect(operate)
timer.start(100)
worker.finished.connect(app.quit)
worker.start()
qt.QTimer.singleShot(45000, app.quit)
app.exec()
assert worker.wait(1000), 'Review worker failed to finish'
results['settings_unchanged'] = hashlib.sha256(settings.read_bytes()).hexdigest() == before
Path(__file__).with_name('qt_review_result.json').write_text(json.dumps(results, indent=2), encoding='utf-8')
assert results['decisions'] == [None, 1], results
assert results['window_on_gui_thread'] == [True, True], results
assert results['settings_unchanged'] and results['error'] is None, results
root.destroy()
print(json.dumps(results))

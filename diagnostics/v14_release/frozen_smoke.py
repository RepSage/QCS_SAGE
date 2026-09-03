"""Check the built executable in its writable bundle, isolated from operator settings.

Dependencies: Python 3.13 stdlib and Windows user32. No QCS source shell is booted.
"""
import ctypes
from ctypes import wintypes
import hashlib
import json
from pathlib import Path
import subprocess
import time

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
BUNDLE = ROOT / 'packaging/dist/QCS'
EXE = BUNDLE / 'QCS.exe'
settings = ROOT / 'sourceCode/qcs_user_settings.json'
before = hashlib.sha256(settings.read_bytes()).hexdigest()
assert not (BUNDLE / 'qcs_user_settings.json').exists()
assert not list(BUNDLE.rglob('QCS_crash.log'))
startup = subprocess.STARTUPINFO()
startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
startup.wShowWindow = 0
shot = subprocess.run([str(EXE), '--shot', str(OUT / 'frozen_ui.png')],
                      cwd=BUNDLE, startupinfo=startup, timeout=60, check=True)
assert (OUT / 'frozen_ui.png').stat().st_size > 1000

user32 = ctypes.windll.user32
user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
user32.IsHungAppWindow.argtypes = [wintypes.HWND]
user32.PostMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)


def owned_windows(pid):
    windows = []

    @callback_type
    def visit(handle, _):
        owner = wintypes.DWORD()
        user32.GetWindowThreadProcessId(handle, ctypes.byref(owner))
        if owner.value == pid:
            title = ctypes.create_unicode_buffer(512)
            user32.GetWindowTextW(handle, title, len(title))
            if title.value:
                windows.append((handle, title.value))
        return True

    user32.EnumWindows(visit, 0)
    return windows


started = time.monotonic()
process = subprocess.Popen([str(EXE)], cwd=BUNDLE, startupinfo=startup)
window = None
try:
    while time.monotonic() - started < 30:
        assert process.poll() is None, 'Frozen program exited before its window appeared'
        windows = owned_windows(process.pid)
        window = next((w for w in windows if 'Quality Control System' in w[1] and 'v14.0' in w[1]), None)
        if window:
            break
        time.sleep(0.25)
    assert window, 'No v14.0 main window found'
    startup_seconds = time.monotonic() - started
    for _ in range(12):
        time.sleep(1)
        assert process.poll() is None and not user32.IsHungAppWindow(window[0])
    user32.PostMessageW(window[0], 0x0010, 0, 0)  # WM_CLOSE, only our own process
    process.wait(timeout=15)
    assert process.returncode == 0
finally:
    if process.poll() is None:
        process.terminate()
        process.wait(timeout=10)
assert not list(BUNDLE.rglob('QCS_crash.log'))
assert hashlib.sha256(settings.read_bytes()).hexdigest() == before
files = [p for p in BUNDLE.rglob('*') if p.is_file() and p.name != 'qcs_user_settings.json']
result = {'screenshot_exit': shot.returncode, 'main_window_title': window[1],
          'startup_seconds': round(startup_seconds, 2), 'responsive_seconds': 12,
          'close_exit': process.returncode, 'operator_settings_unchanged': True,
          'crash_log_present': False, 'bundle_files': len(files),
          'bundle_bytes': sum(p.stat().st_size for p in files)}
(OUT / 'frozen_smoke.json').write_text(json.dumps(result, indent=2))
print(json.dumps(result, indent=2))

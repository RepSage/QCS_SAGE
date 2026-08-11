@echo off
rem Unified QCS launcher: one window with the Data Qualification and Data
rem Visualization tabs (see sourceCode\QCS_App.py).
rem Launch with pythonw (no console window). Progress/warnings/errors show in the
rem app's Execution log; a fatal crash writes sourceCode\QCS_crash.log and pops a
rem message box (see install_crash_handler in QCS_Theme.py).
cd /d "%~dp0sourceCode"
start "" "%USERPROFILE%\anaconda3\pythonw.exe" QCS_App.py

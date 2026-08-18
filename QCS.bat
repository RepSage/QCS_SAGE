@echo off
rem Unified QCS launcher (v12.0, Qt shell): one window with the Data
rem Qualification and Data Visualization tabs (sourceCode\QCS_QtApp.py).
rem Progress/warnings/errors show in the app's Execution log; a fatal crash
rem writes QCS_crash.log and pops a message box.
rem
rem PySide6 6.8.3 lives in packaging\v12_env (see sourceCode\requirements.txt;
rem on this machine the Anaconda base cannot host PySide6 - Qt5 DLL conflict).
cd /d "%~dp0sourceCode"
start "" "%~dp0packaging\v12_env\Scripts\pythonw.exe" QCS_QtApp.py

@echo off
title QCS - Data Qualification Tool
cd /d "%~dp0sourceCode"
"%USERPROFILE%\anaconda3\python.exe" QCS_Main.py
if errorlevel 1 (
    echo.
    echo The program ended with an error. Press any key to close this window.
    pause >nul
)

@echo off
title QCS - Visualizacao de Dados (DatabaseView)
cd /d "%~dp0sourceCode"
"%USERPROFILE%\anaconda3\python.exe" QCS_DatabaseView.py
echo.
echo Programa encerrado. Pressione qualquer tecla para fechar esta janela.
pause >nul

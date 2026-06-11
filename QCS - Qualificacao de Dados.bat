@echo off
title QCS - Qualificacao de Dados
cd /d "%~dp0sourceCode"
"%USERPROFILE%\anaconda3\python.exe" QCS_Main.py
echo.
echo Programa encerrado. Pressione qualquer tecla para fechar esta janela.
pause >nul

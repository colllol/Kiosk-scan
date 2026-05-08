@echo off
title Kiosk Scan GUI
cd /d "%~dp0"

echo ============================================
echo   Kiosk Scan GUI - He thong quet tai lieu
echo ============================================
echo.
echo Dang khoi dong GUI...
echo.

:: KHONG kich hoat venv - PyQt5 duoc cai o system Python
:: Chay GUI truc tiep bang system Python
python gui\main_window.py

if %errorlevel% neq 0 (
    echo.
    echo [LOI] Khong the khoi dong GUI.
    echo Vui long dam bao da cai dat PyQt5:
    echo   pip install PyQt5 PyQtWebEngine
    echo.
    pause
)
@echo off
echo ==========================
echo BUILD PYTHON EXE (OPTIMIZED FOR SPEED)
echo ==========================

REM Clean previous build
if exist "build" rmdir /s /q "build"
if exist "dist" rmdir /s /q "dist"
if exist "main.spec" del /q "main.spec"

REM Using --onedir instead of --onefile for faster startup
REM --onedir keeps files unpacked, so no extraction delay on startup
pyinstaller --onedir ^
--clean ^
--name "WebcamScan" ^
--optimize=1 ^
--noconfirm ^
--collect-all numpy ^
--collect-all PIL ^
--collect-all escpos ^
--collect-all reportlab ^
--hidden-import=cv2 ^
--hidden-import=uvicorn ^
--hidden-import=fastapi ^
--hidden-import=uvicorn.logging ^
--hidden-import=uvicorn.loops ^
--hidden-import=uvicorn.protocols ^
--hidden-import=fastapi.staticfiles ^
--hidden-import=PIL.Image ^
--hidden-import=PIL.ImageDraw ^
--hidden-import=PIL.ImageFont ^
--hidden-import=escpos.printer ^
--hidden-import=reportlab.pdfgen ^
--hidden-import=reportlab.lib.pagesizes ^
--hidden-import=reportlab.lib.units ^
--hidden-import=reportlab.lib.utils ^
--hidden-import=print_ticket ^
--hidden-import=image_processor ^
--add-data "print_ticket.py;." ^
--add-data "image_processor.py;." ^
main.py

if %ERRORLEVEL% EQU 0 (
    echo ==========================
    echo BUILD SUCCESSFUL
    echo File exe: dist\WebcamScan.exe
    echo ==========================
) else (
    echo ==========================
    echo BUILD FAILED
    echo ==========================
)
pause
@echo off
echo ==========================
echo SIMPLE BUILD SCRIPT
echo ==========================
echo.
echo This script builds the backend EXE with minimal configuration.
echo For full configuration support, use build.bat instead.
echo.

REM Set error handling
setlocal enabledelayedexpansion

REM Check if PyInstaller is installed (try both command and module)
where pyinstaller >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo [OK] PyInstaller command is available in PATH
) else (
    REM Try checking if PyInstaller module is available (note: capital P)
    python -c "import PyInstaller" >nul 2>&1
    if %ERRORLEVEL% EQU 0 (
        echo [OK] PyInstaller module is available
    ) else (
        echo PyInstaller is not installed!
        echo Installing PyInstaller...
        pip install pyinstaller
        
        REM Check if installation succeeded
        python -c "import PyInstaller" >nul 2>&1
        if %ERRORLEVEL% EQU 0 (
            echo [OK] PyInstaller module installed successfully
        ) else (
            echo [ERROR] Failed to install PyInstaller!
            echo Please install manually: pip install pyinstaller
            pause
            exit /b 1
        )
    )
)

REM Clean previous build
if exist "build" rmdir /s /q "build"
if exist "dist" rmdir /s /q "dist"
if exist "WebcamScan.spec" del /q "WebcamScan.spec"

echo Building EXE...

REM Run PyInstaller (try command first, then module)
where pyinstaller >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    REM Use pyinstaller command
    echo Using pyinstaller command...
    pyinstaller --onedir ^
--name "WebcamScan" ^
--add-data "../config.json;." ^
--hidden-import=image_processor ^
--hidden-import=print_ticket ^
--hidden-import=config ^
--hidden-import=ultralytics ^
--hidden-import=pytesseract ^
--hidden-import=rembg ^
--hidden-import=onnxruntime ^
--hidden-import=cv2 ^
--hidden-import=uvicorn ^
--hidden-import=fastapi ^
--hidden-import=pydantic ^
main.py
) else (
    REM Use python -m pyinstaller
    echo Using python -m pyinstaller...
    python -m PyInstaller --onedir ^
--name "WebcamScan" ^
--add-data "../config.json;." ^
--hidden-import=image_processor ^
--hidden-import=print_ticket ^
--hidden-import=config ^
--hidden-import=ultralytics ^
--hidden-import=pytesseract ^
--hidden-import=rembg ^
--hidden-import=onnxruntime ^
--hidden-import=cv2 ^
--hidden-import=uvicorn ^
--hidden-import=fastapi ^
--hidden-import=pydantic ^
main.py
)

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ==========================
    echo BUILD COMPLETE!
    echo ==========================
    echo.
    echo EXE location: dist\WebcamScan\WebcamScan.exe
    echo.
    echo IMPORTANT: Copy config.json to the same directory as the EXE
    echo.
    echo To run:
    echo   1. Copy config.json to dist\WebcamScan\
    echo   2. Run dist\WebcamScan\WebcamScan.exe
    echo.
) else (
    echo.
    echo ==========================
    echo BUILD FAILED!
    echo ==========================
    echo.
)

pause
@echo off
echo ==========================
echo BUILD PYTHON EXE (WITH CONFIG SUPPORT)
echo ==========================

REM Clean previous build
if exist "build" rmdir /s /q "build"
if exist "dist" rmdir /s /q "dist"
if exist "WebcamScan.spec" del /q "WebcamScan.spec"

REM Copy config.json to backend directory for build
if exist "..\config.json" (
    copy "..\config.json" "config.json" > nul
    echo Copied config.json from parent directory
) else (
    echo Warning: config.json not found in parent directory
    echo Creating default config.json...
    echo { > config.json
    echo   "apiEndpoints": { >> config.json
    echo     "backend": "http://localhost:5000", >> config.json
    echo     "queueSystem": "http://27.71.20.120:2020/api/ticket/create" >> config.json
    echo   }, >> config.json
    echo   "targetUrl": "https://dichvucong.thainguyen.gov.vn/thong-tin-cong-dan", >> config.json
    echo   "backendSettings": { >> config.json
    echo     "host": "0.0.0.0", >> config.json
    echo     "port": 5000, >> config.json
    echo     "uploadDir": "uploads", >> config.json
    echo     "pdfDir": "pdfs" >> config.json
    echo   }, >> config.json
    echo   "extensionSettings": { >> config.json
    echo     "autoDetect": true, >> config.json
    echo     "debugMode": false, >> config.json
    echo     "timeout": 10000 >> config.json
    echo   } >> config.json
    echo } >> config.json
)

echo Current directory: %cd%

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

echo Building with PyInstaller...

REM Using --onedir for faster startup (no extraction delay)
REM Run PyInstaller (try command first, then module)
where pyinstaller >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    REM Use pyinstaller command
    echo Using pyinstaller command...
    pyinstaller --onedir ^
--clean ^
--name "WebcamScan" ^
--optimize=1 ^
--noconfirm ^
--noupx ^
--collect-all numpy ^
--collect-all PIL ^
--collect-all escpos ^
--collect-all reportlab ^
--add-data "config.json;." ^
--add-data "print_ticket.py;." ^
--add-data "image_processor.py;." ^
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
--hidden-import=config ^
--hidden-import=ultralytics ^
--hidden-import=pytesseract ^
--hidden-import=rembg ^
--hidden-import=rembg.models ^
--hidden-import=onnxruntime ^
--hidden-import=pydantic ^
--hidden-import=multipart ^
--hidden-import=typing_extensions ^
main.py
) else (
    REM Use python -m pyinstaller
    echo Using python -m pyinstaller...
    python -m PyInstaller --onedir ^
--clean ^
--name "WebcamScan" ^
--optimize=1 ^
--noconfirm ^
--noupx ^
--collect-all numpy ^
--collect-all PIL ^
--collect-all escpos ^
--collect-all reportlab ^
--add-data "config.json;." ^
--add-data "print_ticket.py;." ^
--add-data "image_processor.py;." ^
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
--hidden-import=config ^
--hidden-import=ultralytics ^
--hidden-import=pytesseract ^
--hidden-import=rembg ^
--hidden-import=rembg.models ^
--hidden-import=onnxruntime ^
--hidden-import=pydantic ^
--hidden-import=multipart ^
--hidden-import=typing_extensions ^
main.py
)

set BUILD_ERROR=%ERRORLEVEL%

REM Clean up temporary config.json
if exist "config.json" del /q "config.json"

if %BUILD_ERROR% EQU 0 (
    echo ==========================
    echo BUILD SUCCESSFUL
    echo.
    echo IMPORTANT: After building, copy config.json to EXE directory
    echo.
    echo File exe: dist\WebcamScan\WebcamScan.exe
    echo ==========================
    
    REM Create deployment package only if dist directory exists
    echo.
    if exist "dist\WebcamScan" (
        echo Creating deployment package...
        if exist "deployment" rmdir /s /q "deployment"
        mkdir deployment
        
        REM Copy all files from dist\WebcamScan to deployment
        xcopy "dist\WebcamScan\*" "deployment\" /E /I /H /Y
        
        REM Copy config.json if exists
        if exist "..\config.json" (
            copy "..\config.json" "deployment\config.json" > nul 2>&1
            echo [OK] Copied config.json to deployment
        ) else (
            echo [WARN] config.json not found in parent directory
        )
        
        echo.
        echo Deployment package created in: deployment\
        echo Files included:
        dir /b "deployment\"
        echo.
        echo To run the EXE:
        echo   cd deployment
        echo   WebcamScan.exe
        echo.
        echo Or use the start scripts in the project root:
        echo   ..\start_Kiosk.bat
        echo   ..\start_Backend_Only.bat
    ) else (
        echo [WARN] dist\WebcamScan directory not found!
        echo Build may have failed or EXE not created.
    )
    echo ==========================
) else (
    echo ==========================
    echo BUILD FAILED
    echo ==========================
)

pause
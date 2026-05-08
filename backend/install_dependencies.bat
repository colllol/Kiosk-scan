@echo off
echo ==========================
echo INSTALL DEPENDENCIES
echo ==========================
echo.
echo This script installs all required dependencies
echo before building the EXE.
echo.

REM Check Python
where python >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo ❌ Python not found!
    echo Please install Python 3.8+ and add to PATH
    pause
    exit /b 1
)

python --version
echo.

REM Install PyInstaller (check module with capital P)
echo 1. Installing PyInstaller...
python -c "import PyInstaller" >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    pip install pyinstaller --quiet
    if %ERRORLEVEL% EQU 0 (
        echo ✓ PyInstaller installed
    ) else (
        echo ❌ Failed to install PyInstaller
    )
) else (
    echo ✓ PyInstaller already installed
)

REM Install dependencies from requirements.txt
echo.
echo 2. Installing dependencies from requirements.txt...
if exist "requirements.txt" (
    pip install -r requirements.txt --quiet
    if %ERRORLEVEL% EQU 0 (
        echo ✓ Dependencies installed
    ) else (
        echo ❌ Failed to install some dependencies
        echo Trying individual installation...
        
        REM Try installing key packages individually
        echo   - Installing fastapi...
        pip install fastapi --quiet
        echo   - Installing uvicorn...
        pip install uvicorn[standard] --quiet
        echo   - Installing opencv-python...
        pip install opencv-python --quiet
        echo   - Installing ultralytics...
        pip install ultralytics --quiet
        echo   - Installing rembg...
        pip install rembg[cpu] --quiet
        echo   - Installing pytesseract...
        pip install pytesseract --quiet
    )
) else (
    echo ❌ requirements.txt not found!
    echo Creating default requirements.txt...
    
    echo fastapi > requirements.txt
    echo uvicorn[standard] >> requirements.txt
    echo python-multipart >> requirements.txt
    echo Pillow >> requirements.txt
    echo reportlab >> requirements.txt
    echo numpy >> requirements.txt
    echo opencv-python >> requirements.txt
    echo requests >> requirements.txt
    echo python-escpos >> requirements.txt
    echo ultralytics >> requirements.txt
    echo pytesseract >> requirements.txt
    echo rembg[cpu] >> requirements.txt
    
    echo ✓ Created requirements.txt
    pip install -r requirements.txt --quiet
)

REM Check key packages
echo.
echo 3. Verifying key packages...
echo   - Checking fastapi...
python -c "import fastapi; print('      ✓ fastapi ' + fastapi.__version__)" 2>nul || echo "      ❌ fastapi not installed"

echo   - Checking ultralytics...
python -c "import ultralytics; print('      ✓ ultralytics ' + ultralytics.__version__)" 2>nul || echo "      ❌ ultralytics not installed"

echo   - Checking rembg...
python -c "import rembg; print('      ✓ rembg')" 2>nul || echo "      ❌ rembg not installed"

echo   - Checking opencv...
python -c "import cv2; print('      ✓ OpenCV ' + cv2.__version__)" 2>nul || echo "      ❌ OpenCV not installed"

echo.
echo ==========================
echo DEPENDENCIES INSTALLATION COMPLETE
echo ==========================
echo.
echo You can now build the EXE:
echo   1. build.bat       - Full build with configuration
echo   2. build_simple.bat - Simple build
echo.
pause
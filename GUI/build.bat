@echo off
setlocal

title Build GridFlux GUI

set "MSYS_DIR=C:\msys64"
set "MINGW_BIN=%MSYS_DIR%\mingw64\bin"
set "USR_BIN=%MSYS_DIR%\usr\bin"
set "CC=%MINGW_BIN%\gcc.exe"
set "CXX=%MINGW_BIN%\g++.exe"
set "CMAKE=%MINGW_BIN%\cmake.exe"
set "NINJA=%MINGW_BIN%\ninja.exe"
set "SRC=%~dp0"

if "%SRC:~-1%"=="\" set "SRC=%SRC:~0,-1%"
set "BUILD=%SRC%\build"
set "PATH=%MINGW_BIN%;%USR_BIN%;%PATH%"

echo ========================================
echo   Build GridFlux GUI
echo ========================================
echo.

if not exist "%CMAKE%" (
    echo [ERROR] CMake not found: %CMAKE%
    echo Install MSYS2 MinGW64 or update this script with your toolchain path.
    pause
    exit /b 1
)

if not exist "%NINJA%" (
    echo [ERROR] Ninja not found: %NINJA%
    pause
    exit /b 1
)

if not exist "%CC%" (
    echo [ERROR] GCC not found: %CC%
    pause
    exit /b 1
)

if not exist "%SRC%\CMakeLists.txt" (
    echo [ERROR] Missing CMakeLists.txt in %SRC%
    pause
    exit /b 1
)

if exist "%BUILD%\CMakeCache.txt" del /f /q "%BUILD%\CMakeCache.txt"
if exist "%BUILD%\CMakeFiles" rmdir /s /q "%BUILD%\CMakeFiles"

echo [CONFIGURE] CMake + Ninja...
"%CMAKE%" -S "%SRC%" -B "%BUILD%" -G Ninja ^
  -DCMAKE_MAKE_PROGRAM="%NINJA%" ^
  -DCMAKE_C_COMPILER="%CC%" ^
  -DCMAKE_CXX_COMPILER="%CXX%" ^
  -DCMAKE_BUILD_TYPE=Release ^
  -DBUILD_SERVER=ON ^
  -DBUILD_CLI=ON

if errorlevel 1 (
    echo [ERROR] CMake configure failed.
    pause
    exit /b 1
)

echo [BUILD] Compiling...
"%CMAKE%" --build "%BUILD%"
if errorlevel 1 (
    echo [ERROR] Build failed.
    pause
    exit /b 1
)

echo.
echo [OK] Build complete.
dir /b "%BUILD%\bin\*.exe" "%BUILD%\lib\*.a" 2>nul
pause

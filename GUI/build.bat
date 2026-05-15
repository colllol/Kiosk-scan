@echo off
setlocal

set CC=C:\msys64\mingw64\bin\gcc.exe
set CXX=C:\msys64\mingw64\bin\g++.exe
set CMAKE=C:\msys64\mingw64\bin\cmake.exe
set NINJA=C:\msys64\mingw64\bin\ninja.exe
set SRC=%~dp0
if "%SRC:~-1%"=="\" set SRC=%SRC:~0,-1%
set BUILD=%SRC%\build
set PATH=C:\msys64\mingw64\bin;C:\msys64\usr\bin;%PATH%

if exist "%BUILD%\CMakeCache.txt" del /f /q "%BUILD%\CMakeCache.txt"
if exist "%BUILD%\CMakeFiles" rmdir /s /q "%BUILD%\CMakeFiles"

echo === Configuring ===
"%CMAKE%" -S "%SRC%" -B "%BUILD%" -G Ninja ^
  -DCMAKE_MAKE_PROGRAM="%NINJA%" ^
  -DCMAKE_C_COMPILER="%CC%" ^
  -DCMAKE_CXX_COMPILER="%CXX%" ^
  -DCMAKE_BUILD_TYPE=Release ^
  -DBUILD_SERVER=ON ^
  -DBUILD_CLI=ON

if %ERRORLEVEL% neq 0 (
    echo CMake configure failed!
    exit /b 1
)

echo === Building ===
cd /d "%BUILD%"
"%CMAKE%" --build .

if %ERRORLEVEL% neq 0 (
    echo Build failed!
    exit /b 1
)

echo === Build Complete ===
dir /b bin\*.exe lib\*.a 2>nul

@echo off
setlocal EnableExtensions
cd /d "%~dp0"

echo ========================================
echo  AirMouse single-file EXE builder
echo ========================================
echo.

where python >nul 2>nul
if errorlevel 1 (
    echo [ERROR] python not found in PATH.
    pause
    exit /b 1
)

echo [1/4] Installing build dependencies...
python -m pip install -r requirments.txt pyinstaller
if errorlevel 1 (
    echo [ERROR] failed to install dependencies.
    pause
    exit /b 1
)

if not exist "build" mkdir build

echo [2/4] Generating Windows icon...
python -c "from PIL import Image; im=Image.open(r'static/app-icon.png').convert('RGBA'); sizes=[(16,16),(32,32),(48,48),(64,64),(128,128),(256,256)]; im.save(r'build/app-icon.ico', format='ICO', sizes=sizes); print('wrote build/app-icon.ico')"
if errorlevel 1 (
    echo [ERROR] failed to generate icon.
    pause
    exit /b 1
)

echo [3/4] Cleaning previous build output...
if exist "dist\AirMouse.exe" del /f /q "dist\AirMouse.exe"
if exist "build\pyinstaller" rmdir /s /q "build\pyinstaller"
if exist "AirMouse.spec" del /f /q "AirMouse.spec"

echo [4/4] Packaging with PyInstaller...
python -m PyInstaller ^
  --noconfirm ^
  --clean ^
  --onefile ^
  --windowed ^
  --name AirMouse ^
  --icon "build\app-icon.ico" ^
  --distpath dist ^
  --workpath build\pyinstaller ^
  --specpath . ^
  --add-data "templates;templates" ^
  --add-data "static;static" ^
  --add-data "cert.pem;." ^
  --add-data "key.pem;." ^
  --hidden-import engineio.async_drivers.threading ^
  --hidden-import flask_socketio ^
  --hidden-import socketio ^
  --hidden-import engineio ^
  --hidden-import simple_websocket ^
  --hidden-import wsproto ^
  --hidden-import pystray._win32 ^
  --hidden-import tkinter ^
  --hidden-import _tkinter ^
  --collect-submodules engineio ^
  --collect-submodules socketio ^
  --collect-all pystray ^
  server.py

if errorlevel 1 (
    echo.
    echo [ERROR] packaging failed.
    pause
    exit /b 1
)

echo.
echo ========================================
echo  Build finished.
echo  Output: %cd%\dist\AirMouse.exe
echo ========================================
echo.
explorer /select,"%cd%\dist\AirMouse.exe"
pause

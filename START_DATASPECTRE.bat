@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"
title DataSpectre CLI

if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" dataspectre.py interactive
) else (
  python dataspectre.py interactive
)
set "EXIT_CODE=%errorlevel%"

if not "%EXIT_CODE%"=="0" (
  echo.
  echo [ERRO] O DataSpectre terminou com codigo %EXIT_CODE%.
  echo Execute INSTALL_DATASPECTRE.bat se as dependencias ainda nao foram instaladas.
  pause
)
endlocal & exit /b %EXIT_CODE%

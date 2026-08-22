@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"
title DataSpectre CLI - Instalacao

echo ===============================================================
echo   DATASPECTRE CLI - INSTALACAO LOCAL
echo ===============================================================

echo [1/4] Verificando Python...
python --version >nul 2>&1
if errorlevel 1 (
  echo [ERRO] Python 3.10 ou superior nao foi encontrado no PATH.
  echo Instale o Python e marque a opcao "Add Python to PATH".
  pause
  exit /b 1
)

echo [2/4] Criando ambiente virtual...
if not exist ".venv\Scripts\python.exe" python -m venv .venv
if errorlevel 1 goto :fail

echo [3/4] Instalando dependencias...
".venv\Scripts\python.exe" -m pip install --upgrade pip
if errorlevel 1 goto :fail
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto :fail

echo [4/4] Validando o DataSpectre...
".venv\Scripts\python.exe" main.py status
if errorlevel 1 goto :fail

echo.
echo [OK] Instalacao concluida.
echo Use START_DATASPECTRE.bat para abrir o terminal.
pause
exit /b 0

:fail
echo.
echo [ERRO] A instalacao nao foi concluida.
echo Nenhum projeto, relatorio ou investigacao existente foi removido.
pause
exit /b 1

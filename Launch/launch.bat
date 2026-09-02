@echo off
title DevLauncher
setlocal

set "LAUNCH=%~dp0"
set "USB=%LAUNCH%.."

REM --- pick a python that actually runs ---
set "PY="
if exist "%USB%\DevEnv\python\python.exe" set "PY=%USB%\DevEnv\python\python.exe"
if defined PY (
    "%PY%" --version >nul 2>&1
    if errorlevel 1 set "PY="
)
if not defined PY (
    where py >nul 2>&1
    if not errorlevel 1 set "PY=py"
)
if not defined PY (
    where python >nul 2>&1
    if not errorlevel 1 set "PY=python"
)
if not defined PY (
    echo [ERROR] No working Python found on this PC.
    echo         Either install Python, or run finish_setup.bat on the PC
    echo         that has Python so DevEnv\python gets copied to this drive.
    pause
    exit /b 1
)

echo [DevLauncher] Python : %PY%
"%PY%" "%LAUNCH%launcher.py"
if errorlevel 1 (
    echo [ERROR] launcher.py failed to start.
    pause
)

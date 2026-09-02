@echo off
title DevLauncher
setlocal EnableExtensions

set "LAUNCH=%~dp0"
set "USB=%LAUNCH%.."

REM --- pick a python that actually works, silently ---
set "PY="

REM 1) python bundled on this drive (only if it is a real file, >10KB)
if exist "%USB%\DevEnv\python\python.exe" (
    for %%A in ("%USB%\DevEnv\python\python.exe") do if %%~zA GTR 10000 set "PY=%USB%\DevEnv\python\python.exe"
)
if defined PY (
    "%PY%" --version >nul 2>&1
    if errorlevel 1 set "PY="
)

REM 2) Windows Python Launcher (generic on Windows)
if not defined PY (
    where py >nul 2>&1
    if not errorlevel 1 (
        py -3 --version >nul 2>&1
        if not errorlevel 1 set "PY=py -3"
    )
)

REM 3) python / python3 on PATH
if not defined PY (
    where python >nul 2>&1
    if not errorlevel 1 (
        python --version >nul 2>&1
        if not errorlevel 1 set "PY=python"
    )
)
if not defined PY (
    where python3 >nul 2>&1
    if not errorlevel 1 set "PY=python3"
)

if not defined PY (
    echo.
    echo [ERROR] No working Python was found.
    echo   The launcher needs Python 3. It is normally bundled on this drive.
    echo   To bundle it: plug this drive into ANY internet-connected PC and
    echo   run  finish_setup.bat  (it downloads a portable Python for you).
    echo.
    pause
    exit /b 1
)

echo [DevLauncher] Python : %PY%
%PY% "%LAUNCH%launcher.py"
if errorlevel 1 (
    echo.
    echo [ERROR] launcher.py failed to start. See messages above.
    pause
)

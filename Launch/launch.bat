@echo off
title NomadDev
setlocal EnableExtensions

set "LAUNCH=%~dp0"
set "USB=%LAUNCH%.."
set "PYBIN="
set "FOUND=0"

rem ============================================================
rem  Find a working Python 3, silently, with deep detection:
rem   1) python bundled on this drive (portable, preferred)
rem   2) Windows Python Launcher : py -3
rem   3) python / python3 on PATH
rem   4) common install locations (users often have Python
rem      but not on PATH) - LocalAppData, ProgramFiles, conda
rem ============================================================

rem ---- 1) bundled on drive (only if real file, >10KB) ----
if exist "%USB%\DevEnv\python\python.exe" (
    for %%A in ("%USB%\DevEnv\python\python.exe") do if %%~zA GTR 10000 (
        "%USB%\DevEnv\python\python.exe" --version >nul 2>&1
        if not errorlevel 1 (
            set PYBIN="%USB%\DevEnv\python\python.exe"
            set "FOUND=1"
        )
    )
)

rem ---- 2) Windows Python launcher ----
if not defined PYBIN (
    py -3 --version >nul 2>&1
    if not errorlevel 1 (
        set "PYBIN=py -3"
        set "FOUND=1"
    )
)

rem ---- 3) python on PATH ----
if not defined PYBIN (
    where python >nul 2>&1
    if not errorlevel 1 (
        python --version >nul 2>&1
        if not errorlevel 1 (
            set "PYBIN=python"
            set "FOUND=1"
        )
    )
)
if not defined PYBIN (
    where python3 >nul 2>&1
    if not errorlevel 1 (
        python3 --version >nul 2>&1
        if not errorlevel 1 (
            set "PYBIN=python3"
            set "FOUND=1"
        )
    )
)

rem ---- 4) deep scan: common install locations ----
if not defined PYBIN (
    for %%P in (
        "%LOCALAPPDATA%\Programs\Python\Python3*\python.exe"
        "%ProgramFiles%\Python3*\python.exe"
        "%ProgramW6432%\Python3*\python.exe"
        "C:\Python3*\python.exe"
        "%USERPROFILE%\anaconda3\python.exe"
        "%USERPROFILE%\miniconda3\python.exe"
        "%LOCALAPPDATA%\anaconda3\python.exe"
        "%LOCALAPPDATA%\miniconda3\python.exe"
        "%ProgramData%\anaconda3\python.exe"
        "%ProgramData%\miniconda3\python.exe"
    ) do (
        if not defined PYBIN if exist "%%~P" (
            "%%~P" --version >nul 2>&1
            if not errorlevel 1 (
                set PYBIN="%%~P"
                set "FOUND=1"
            )
        )
    )
)

if not defined PYBIN (
    echo.
    echo [ERROR] No working Python 3 was found on this PC.
    echo   Checked: this drive, py launcher, PATH, common install folders.
    echo   If you have Python somewhere unusual, it was not auto-detected.
    echo.
    echo   Solution A : plug this drive into ANY internet PC and run
    echo               finish_setup.bat  - it downloads a portable Python.
    echo   Solution B : install Python 3 from python.org, then retry.
    echo.
    pause
    exit /b 1
)

if "%FOUND%"=="1" echo [NomadDev] Using Python : %PYBIN%
%PYBIN% "%LAUNCH%launcher.py"
if errorlevel 1 (
    echo.
    echo [ERROR] launcher.py failed to start. See messages above.
    pause
)

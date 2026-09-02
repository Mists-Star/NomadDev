@echo off
title NomadDev
setlocal EnableExtensions

set "LAUNCH=%~dp0"
set "USB=%LAUNCH%.."
set "PYBIN="
set "FOUND=0"

rem ============================================================
rem  NomadDev launcher - finds a working Python 3 silently:
rem   1) runtime\python   (built-in minimal Python on this drive)
rem   2) DevEnv\python    (full portable Python on this drive)
rem   3) py launcher / python on PATH
rem   4) common install locations (deep scan)
rem ============================================================

rem ---- 1) built-in minimal runtime ----
if exist "%USB%runtime\python\python.exe" (
    for %%A in ("%USB%runtime\python\python.exe") do if %%~zA GTR 10000 (
        "%USB%runtime\python\python.exe" --version >nul 2>&1
        if not errorlevel 1 (
            set PYBIN="%USB%runtime\python\python.exe"
            set FOUND=1
        )
    )
)

rem ---- 2) full portable python on drive ----
if not defined PYBIN if exist "%USB%DevEnv\python\python.exe" (
    for %%A in ("%USB%DevEnv\python\python.exe") do if %%~zA GTR 10000 (
        "%USB%DevEnv\python\python.exe" --version >nul 2>&1
        if not errorlevel 1 (
            set PYBIN="%USB%DevEnv\python\python.exe"
            set FOUND=1
        )
    )
)

rem ---- 3) Windows Python launcher ----
if not defined PYBIN (
    py -3 --version >nul 2>&1
    if not errorlevel 1 ( set PYBIN=py -3 & set FOUND=1 )
)

rem ---- 4) python / python3 on PATH ----
if not defined PYBIN (
    where python >nul 2>&1
    if not errorlevel 1 (
        python --version >nul 2>&1
        if not errorlevel 1 ( set PYBIN=python & set FOUND=1 )
    )
)
if not defined PYBIN (
    where python3 >nul 2>&1
    if not errorlevel 1 ( set PYBIN=python3 & set FOUND=1 )
)

rem ---- 5) deep scan common install locations ----
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
            if not errorlevel 1 ( set PYBIN="%%~P" & set FOUND=1 )
        )
    )
)

if not defined PYBIN (
    echo.
    echo [ERROR] No working Python 3 found on this PC.
    echo   This drive can carry its own tiny Python so it runs anywhere.
    echo   Do ONE of these:
    echo     A. Run  Launch\_get_runtime.bat  on an internet PC once
    echo        (downloads a ~11MB minimal Python into runtime\python).
    echo     B. Run  finish_setup.bat  on an internet PC (full setup).
    echo     C. Install Python 3 from python.org, then retry.
    echo.
    pause
    exit /b 1
)

echo [NomadDev] Python : %PYBIN%
%PYBIN% "%LAUNCH%launcher.py"
if errorlevel 1 (
    echo.
    echo [ERROR] launcher.py failed to start. See messages above.
    pause
)

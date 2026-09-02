@echo off
title NomadDev - Get Minimal Runtime
setlocal EnableExtensions
set "AUTO=%~1"
set "USB=%~dp0.."
set "RT=%USB%runtime\python"
set "DL=%USB%Launch\_dl"
if not exist "%DL%" mkdir "%DL%"
if not exist "%USB%runtime" mkdir "%USB%runtime"

if /i not "%AUTO%"=="auto" (
echo ============================================================
echo   NomadDev - install minimal Python runtime (built-in env)
echo   Downloads python embed ~11MB into  runtime\python
echo   Run once on any internet PC; afterwards launcher runs
echo   anywhere with NO python installed.
echo ============================================================
echo.
)

if exist "%RT%\python.exe" (
    for %%A in ("%RT%\python.exe") do if %%~zA GTR 10000 (
        "%RT%\python.exe" --version >nul 2>&1
        if not errorlevel 1 (
            echo   runtime already OK: %RT%\python.exe
            goto :end
        )
    )
)

echo   - downloading minimal Python (huawei mirror, fallback python.org) ...
rd /s /q "%RT%" 2>nul
mkdir "%RT%" 2>nul
curl -L --fail -sS -o "%DL%\runtime_py.zip" "https://mirrors.huaweicloud.com/python/3.13.12/python-3.13.12-embed-amd64.zip"
if errorlevel 1 curl -L --fail -sS -o "%DL%\runtime_py.zip" "https://www.python.org/ftp/python/3.13.12/python-3.13.12-embed-amd64.zip"
if errorlevel 1 (
    echo   [FAIL] download failed. Manually get python.org 3.13.x embed-amd64
    echo          zip and unpack into  runtime\python
    goto :end
)
tar -xf "%DL%\runtime_py.zip" -C "%RT%"
"%RT%\python.exe" --version >nul 2>&1
if errorlevel 1 (
    echo   [FAIL] extracted runtime does not run.
) else (
    echo   [OK] minimal Python ready: %RT%\python.exe
)

:end
if /i not "%AUTO%"=="auto" pause

@echo off
setlocal enabledelayedexpansion
title Synthetic General Ledger Fuzzer
color 0B

:: Ensure working directory is the script's root directory
cd /d "%~dp0"

:: Ensure project root is in PYTHONPATH
set "PYTHONPATH=%~dp0;%PYTHONPATH%"

:: Autodetect Python executable (.venv, venv, system python, py launcher)
set "PYTHON_CMD="
if exist "%~dp0.venv\Scripts\python.exe" (
    set "PYTHON_CMD=%~dp0.venv\Scripts\python.exe"
) else if exist "%~dp0venv\Scripts\python.exe" (
    set "PYTHON_CMD=%~dp0venv\Scripts\python.exe"
) else (
    where python >nul 2>nul
    if not errorlevel 1 (
        set "PYTHON_CMD=python"
    ) else (
        where py >nul 2>nul
        if not errorlevel 1 (
            set "PYTHON_CMD=py"
        )
    )
)

if not defined PYTHON_CMD (
    echo.
    echo ===============================================================================
    echo [ERROR] Python 3.10+ was not found in PATH or a local virtual environment.
    echo Please install Python 3.10+ from https://www.python.org/downloads/
    echo Make sure to check "Add python.exe to PATH" during installation.
    echo ===============================================================================
    echo.
    pause
    exit /b 1
)

:: Set interactive mode default
set "INTERACTIVE_MODE=1"

:: Check direct command-line arguments if provided
if not "%~1"=="" (
    set "INTERACTIVE_MODE=0"
    if /i "%~1"=="1" goto run_web
    if /i "%~1"=="web" goto run_web
    if /i "%~1"=="--web" goto run_web
    if /i "%~1"=="-w" goto run_web
    if /i "%~1"=="2" goto run_desktop
    if /i "%~1"=="desktop" goto run_desktop
    if /i "%~1"=="--desktop" goto run_desktop
    if /i "%~1"=="-d" goto run_desktop
    if /i "%~1"=="3" goto run_generate
    if /i "%~1"=="generate" goto run_generate
    if /i "%~1"=="--generate" goto run_generate
    if /i "%~1"=="-g" goto run_generate
    if /i "%~1"=="4" goto run_audit
    if /i "%~1"=="audit" goto run_audit
    if /i "%~1"=="--audit" goto run_audit
    if /i "%~1"=="-a" goto run_audit
    if /i "%~1"=="5" goto run_tests
    if /i "%~1"=="test" goto run_tests
    if /i "%~1"=="--test" goto run_tests
    if /i "%~1"=="-t" goto run_tests
    if /i "%~1"=="6" goto end
    if /i "%~1"=="exit" goto end
    if /i "%~1"=="quit" goto end
)

:menu
cls
echo ===============================================================================
echo              SYNTHETIC GENERAL LEDGER (GL) FUZZER
echo       Double-Entry Accounting Synthesis ^& Calibrated Anomaly Studio
echo            Made with ^<3 by Atiqul-Akash ^| GitHub: Atiqul-Akash
echo ===============================================================================
echo.
echo Please select how you want to run the application:
echo.
echo   [1] Modern Web GUI (Recommended)
echo       Interactive browser dashboard with live charts, presets, and 1-click downloads
echo.
echo   [2] Native Windows Desktop GUI
echo       Offline desktop window (Tkinter) with tabbed workspaces
echo.
echo   [3] Generate Synthetic Dataset (CLI)
echo       Synthesizes 1,000 entries (Parquet, CSV, SAP BSEG, ACDOCA) with 5%% anomalies
echo.
echo   [4] Run SOX-404 Forensic Audit on Generated Dataset
echo       Runs Benford, DOA split-invoices, and circular round-trip tests
echo.
echo   [5] Run Complete Automated Test Suite (pytest)
echo       Runs all 228 unit and integration tests
echo.
echo   [6] Exit
echo.
echo ===============================================================================
set "CHOICE="
set /p CHOICE="Enter your choice (1-6) [default: 1]: "
if not defined CHOICE set "CHOICE=1"
set "CHOICE=%CHOICE:"=%"
set "CHOICE=%CHOICE: =%"

if "%CHOICE%"=="1" goto run_web
if "%CHOICE%"=="2" goto run_desktop
if "%CHOICE%"=="3" goto run_generate
if "%CHOICE%"=="4" goto run_audit
if "%CHOICE%"=="5" goto run_tests
if "%CHOICE%"=="6" goto end

echo.
echo [!] Invalid choice "%CHOICE%". Please enter a number between 1 and 6.
timeout /t 2 >nul
goto menu

:run_web
echo.
echo Starting Modern Web GUI at http://localhost:8080...
"%PYTHON_CMD%" -m gl_fuzzer.cli gui
goto pause_menu

:run_desktop
echo.
echo Starting Native Windows Desktop GUI...
"%PYTHON_CMD%" -m gl_fuzzer.cli gui --mode desktop
goto pause_menu

:run_generate
echo.
echo Synthesizing 1,000 journal entries with 5%% anomaly rate into ./output...
"%PYTHON_CMD%" -m gl_fuzzer.cli generate --count 1000 --anomaly-rate 0.05 --acdoca --out-dir ./output --export-formats parquet,csv,sap
goto pause_menu

:run_audit
echo.
if not exist "output\gl_feed.parquet" (
    echo [NOTICE] Dataset not found in ./output. Generating fresh dataset first...
    "%PYTHON_CMD%" -m gl_fuzzer.cli generate --count 1000 --anomaly-rate 0.05 --out-dir ./output --export-formats parquet,csv,sap
)
echo Running SOX-404 forensic audit screening...
"%PYTHON_CMD%" -m gl_fuzzer.cli audit-report --dataset ./output/gl_feed.parquet --manifest ./output/ground_truth_manifest.json
goto pause_menu

:run_tests
echo.
echo Executing full pytest verification suite (228 tests)...
"%PYTHON_CMD%" -m pytest -v
goto pause_menu

:pause_menu
if "!INTERACTIVE_MODE!"=="0" goto end
echo.
echo ===============================================================================
echo Execution finished. Press any key to return to the main menu...
pause >nul
goto menu

:end
echo.
echo Exiting Synthetic General Ledger Fuzzer. Goodbye!
endlocal

@echo off
setlocal
title Synthetic General Ledger Fuzzer
color 0B
cls

echo ===============================================================================
echo              SYNTHETIC GENERAL LEDGER (GL) FUZZER
echo       Double-Entry Accounting Synthesis & Calibrated Anomaly Studio
echo            Made with <3 by Atiqul-Akash | GitHub: Atiqul-Akash
echo ===============================================================================
echo.
echo Please select how you want to run the application:
echo.
echo   [1] Modern Web GUI (Recommended)
echo       Interactive browser dashboard with live charts, presets, and 1-click downloads
echo.
echo   [2] Native Windows Desktop GUI
echo       Offline desktop window (Tkinter) with 4 tabbed workspaces
echo.
echo   [3] Generate Synthetic Dataset (CLI)
echo       Synthesizes 1,000 entries (Parquet, CSV, SAP BSEG) with 5%% anomalies
echo.
echo   [4] Run SOX-404 Forensic Audit on Generated Dataset
echo       Runs Benford, DOA split-invoices, and circular round-trip tests
echo.
echo   [5] Run Complete Automated Test Suite (pytest)
echo       Runs all 83 unit and integration tests
echo.
echo   [6] Exit
echo.
echo ===============================================================================
choice /c 123456 /n /m "Enter your choice (1, 2, 3, 4, 5, or 6): "

if errorlevel 6 goto end
if errorlevel 5 goto run_tests
if errorlevel 4 goto run_audit
if errorlevel 3 goto run_generate
if errorlevel 2 goto run_desktop
if errorlevel 1 goto run_web

:run_web
echo.
echo Starting Modern Web GUI at http://localhost:8080...
python -m gl_fuzzer.cli gui
goto pause_exit

:run_desktop
echo.
echo Starting Native Windows Desktop GUI...
python -m gl_fuzzer.cli gui --mode desktop
goto pause_exit

:run_generate
echo.
echo Synthesizing 1,000 journal entries with 5%% anomaly rate into ./output...
python -m gl_fuzzer.cli generate --count 1000 --anomaly-rate 0.05 --acdoca --out-dir ./output --export-formats parquet,csv,sap
goto pause_exit

:run_audit
echo.
if not exist "output\gl_feed.parquet" (
    echo [NOTICE] Dataset not found in ./output. Generating fresh dataset first...
    python -m gl_fuzzer.cli generate --count 1000 --anomaly-rate 0.05 --out-dir ./output --export-formats parquet,csv,sap
)
echo Running SOX-404 forensic audit screening...
python -m gl_fuzzer.cli audit-report --dataset ./output/gl_feed.parquet --manifest ./output/ground_truth_manifest.json
goto pause_exit

:run_tests
echo.
echo Executing full pytest verification suite (75 tests)...
python -m pytest -v
goto pause_exit

:pause_exit
echo.
echo Press any key to return to main menu or close this window...
pause >nul
goto end

:end
endlocal

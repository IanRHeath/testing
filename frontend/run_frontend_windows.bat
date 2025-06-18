@echo off
setlocal

:: ============================================================================
:: Jira Agent Frontend LAUNCHER for Windows
:: ============================================================================
:: DESCRIPTION:
:: Use this script for daily startup. It quickly launches the
:: React development server without reinstalling packages.
:: ============================================================================

echo.
echo === Starting Jira Agent Frontend ===
echo.

:: --- Verify Location ---
if not exist "package.json" (
    echo [ERROR] This script must be run from the 'frontend' directory.
    echo 'package.json' not found.
    pause
    exit /b 1
)

:: --- Start the Application ---
echo      (A new browser window should open. To stop the server, press CTRL+C in this window.)
echo.
npm start

endlocal
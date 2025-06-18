@echo off
setlocal

:: ============================================================================
:: Jira Agent Frontend SETUP Script for Windows
:: ============================================================================
:: DESCRIPTION:
:: This script should be run ONLY ONCE to set up the frontend environment
:: or when you are experiencing issues with dependencies. It will:
:: 1. Check for Node.js/npm.
:: 2. Clean up any old installations.
:: 3. Install all necessary packages.
:: ============================================================================

echo.
echo === Jira Agent Frontend Setup ===
echo.

:: --- Step 1: Prerequisite Check ---
echo [1/4] Checking for Node.js and NPM...
where node >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] Node.js not found in your system's PATH.
    echo Please go to https://nodejs.org to download and install the LTS version.
    echo Make sure to restart your terminal after installation.
    pause
    exit /b 1
)

where npm >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] NPM not found in your system's PATH.
    echo This usually means Node.js is not installed correctly.
    echo Please go to https://nodejs.org to download and install the LTS version.
    pause
    exit /b 1
)
echo      ...Node.js and NPM found.
echo.


:: --- Step 2: Clean Up Old Dependencies ---
echo [2/4] Cleaning up previous installation...
if exist "node_modules" (
    echo      ...Removing 'node_modules' directory. This may take a moment.
    rmdir /s /q node_modules
)
if exist "package-lock.json" (
    echo      ...Removing 'package-lock.json' file.
    del package-lock.json
)
echo      ...Cleanup complete.
echo.

:: --- Step 3: Install Fresh Dependencies ---
echo [3/4] Installing Node.js packages...
npm install
if %errorlevel% neq 0 (
    echo [ERROR] 'npm install' failed. Please check your Node.js/npm installation and network connection.
    pause
    exit /b 1
)
echo      ...Dependencies installed successfully.
echo.

:: --- Step 4: Done ---
echo [4/4] Setup Complete!
echo.
echo You can now run the frontend application by double-clicking 'run_frontend.bat'.
echo.
pause

endlocal
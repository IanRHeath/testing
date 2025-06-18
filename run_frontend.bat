@echo off
setlocal

:: ============================================================================
:: Jira Agent Frontend Launcher for Windows
:: ============================================================================
:: This script checks for Node.js/npm, cleans up old dependencies, 
:: installs fresh ones, and starts the React development server.
:: Place this file in the 'frontend' directory.
:: ============================================================================

echo.
echo === Jira Agent Frontend Launcher ===
echo.

:: --- Step 1: Prerequisite Check ---
echo [1/5] Checking for Node.js and NPM...
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


:: --- Step 2: Verify Location ---
echo [2/5] Verifying location...
if not exist "package.json" (
    echo [ERROR] This script must be run from the 'frontend' directory.
    echo 'package.json' not found.
    pause
    exit /b 1
)
echo      ...Correct directory found.
echo.


:: --- Step 3: Clean Up Old Dependencies ---
echo [3/5] Cleaning up previous installation...
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

:: --- Step 4: Install Fresh Dependencies ---
echo [4/5] Installing Node.js packages...
npm install
if %errorlevel% neq 0 (
    echo [ERROR] 'npm install' failed. Please check your Node.js/npm installation and network connection.
    pause
    exit /b 1
)
echo      ...Dependencies installed successfully.
echo.


:: --- Step 5: Start the Frontend Application ---
echo [5/5] Starting the React development server...
echo      (A new browser window should open. To stop the server, press CTRL+C in this window.)
echo.
npm start

endlocal

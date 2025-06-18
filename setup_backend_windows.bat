@echo off
setlocal

:: ============================================================================
:: Jira Agent Setup Script for Windows
:: ============================================================================
:: This script will configure the necessary Python environment, install
:: dependencies, and prompt for the required credentials to create the .env file.
:: ============================================================================

echo.
echo === Jira Agent Setup ===
echo.

:: --- Step 1: Check for Python ---
echo [1/5] Checking for Python installation...
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] Python not found in your system's PATH.
    echo Please install Python 3.10 or higher and ensure it's added to your PATH.
    pause
    exit /b 1
)
echo      ...Python found.
echo.

:: --- Step 2: Create a Python Virtual Environment ---
echo [2/5] Setting up Python virtual environment...
if exist "venv" (
    echo      ...Virtual environment 'venv' already exists. Skipping creation.
) else (
    echo      ...Creating virtual environment 'venv'. This may take a moment.
    python -m venv venv
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to create the virtual environment.
        pause
        exit /b 1
    )
    echo      ...Virtual environment created successfully.
)
echo.

:: --- Step 3: Install Dependencies ---
echo [3/5] Installing required Python packages...
call venv\Scripts\activate.bat
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo [ERROR] Failed to install packages from requirements.txt.
    echo Please check the file and your internet connection.
    pause
    exit /b 1
)
echo      ...All packages installed successfully.
echo.

:: --- Step 4: Create the .env credentials file ---
echo [4/5] Configuring credentials...
if exist ".env" (
    echo      ...Existing .env file found. Skipping creation.
    echo      (To re-create, please delete the .env file and run this script again)
) else (
    echo      ...Creating new .env file. Please enter your credentials below.
    echo.
    
    set /p JIRA_USER="Enter your JIRA Username: "
    set /p JIRA_PASS="Enter your JIRA Password/API Token: "
    set /p LLM_KEY="Enter your Azure OpenAI API Key: "
    
    (
        echo JIRA_SERVER_URL=https://ontrack-internal.amd.com
        echo JIRA_USERNAME=%JIRA_USER%
        echo JIRA_PASSWORD=%JIRA_PASS%
        echo LLM_API_KEY=%LLM_KEY%
        echo LLM_API_VERSION=2024-06-01
        echo LLM_RESOURCE_ENDPOINT=https://llm-api.amd.com
        echo LLM_CHAT_DEPLOYMENT_NAME=gpt-4.1
    ) > .env
    
    echo.
    echo      ...Successfully created .env file.
)
echo.

:: --- Step 5: Create a Launcher Script ---
echo [5/5] Creating launcher script...
(
    echo @echo off
    echo echo Activating virtual environment and starting Jira Agent backend...
    echo call venv\Scripts\activate.bat
    echo python app.py
    echo pause
) > run_app.bat
echo      ...Created 'run_app.bat' for easy startup.
echo.

:: --- Done ---
echo.
echo === Setup Complete! ===
echo.
echo To start the agent's backend server, simply double-click the 'run_app.bat' file.
echo Then, start the frontend server to view the GUI.
echo.
pause

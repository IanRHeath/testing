@echo off
echo Activating virtual environment and starting Jira Agent backend...
call venv\Scripts\activate.bat
python app.py
pause

@echo off
echo Starting Payment API Server...

REM Activate virtual environment
call venv\Scripts\activate.bat

REM Check if .env exists
if not exist ".env" (
    echo Error: .env file not found
    echo Please copy .env.example to .env and configure your MySQL settings
    exit /b 1
)

REM Start the application
python src\payment_service\api.py
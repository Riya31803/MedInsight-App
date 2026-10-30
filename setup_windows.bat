@echo off
echo ========================================
echo PDF Redaction - Windows Setup
echo ========================================
echo.

where py >nul 2>nul
if %errorlevel% neq 0 (
    echo Python launcher "py" was not found.
    echo Install Python 3.12 from python.org and enable "Add Python to PATH".
    pause
    exit /b 1
)

echo Creating virtual environment...
py -3.12 -m venv venv
if %errorlevel% neq 0 (
    echo Python 3.12 was not found.
    echo Install Python 3.12 and run this file again.
    pause
    exit /b 1
)

call venv\Scripts\activate

echo.
echo Upgrading pip...
python -m pip install --upgrade pip

echo.
echo Installing Python packages...
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo Package installation failed.
    pause
    exit /b 1
)

echo.
echo Installing spaCy English model...
python -m spacy download en_core_web_lg
if %errorlevel% neq 0 (
    echo spaCy model installation failed.
    pause
    exit /b 1
)

echo.
echo ========================================
echo Setup completed successfully.
echo Run run_redaction.bat next.
echo ========================================
pause

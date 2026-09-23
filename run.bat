@echo off
setlocal

:: [0/4] Cleanup unnecessary temporary folders and caches
echo [0/4] Cleaning temporary files and caches...
for /d /r . %%d in (__pycache__) do @if exist "%%d" rd /s /q "%%d"
if exist .pytest_cache rd /s /q .pytest_cache
if exist build rd /s /q build
if exist dist rd /s /q dist
:: Optional: Clear pip cache to save space (commented out by default as it slows down first-time installs)
:: python -m pip cache purge

:: Check if virtual environment exists
if not exist .venv (
    echo [1/4] Creating virtual environment...
    python -m venv .venv
)

:: Activate virtual environment
echo [2/4] Activating virtual environment...
call .venv\Scripts\activate

:: Always try to install requirements to ensure new packages are picked up
echo [3/4] Checking/Installing requirements...
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

echo.
echo Starting E-Reader...
echo.
python -m ereader
if %ERRORLEVEL% neq 0 (
    echo.
    echo [ERROR] Application crashed with exit code %ERRORLEVEL%
    pause
)

endlocal

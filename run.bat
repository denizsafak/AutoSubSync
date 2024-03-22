@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"
set NAME=SubtitleSync
set RUN=SubtitleSync.pyw
set "requirementsFile=requirements.txt"
set VENV_PATH=.venv
set ACTIVATE_PATH=%VENV_PATH%\Scripts\activate

:: Display provided argument if any
if not "%~1"=="" (
    echo Open with: "%~1"
)

:: Check if Python is installed
pip --version >nul 2>&1
if errorlevel 1 (
    echo Python is not installed.
    set /p "userinp=Do you want to install Python (y/n)? "
    if /i "!userinp!"=="y" (
        echo Opening download link...
        start https://www.python.org/downloads/
        exit /b
    ) else (
        echo Please install Python and try again.
        pause
        exit /b
    )
)

:: Check if virtual environment exists
IF NOT EXIST %VENV_PATH% (
    echo Creating virtual environment...
    python -m venv %VENV_PATH%
) ELSE (
    goto check_python
)

:: Check if Python exists at the path stored in the virtual environment
set count_python=0
:check_python
%VENV_PATH%\Scripts\python.exe --version >nul 2>&1
if %errorlevel% neq 0 (
    set /a count_python+=1
    echo Python not found at the path stored in the virtual environment.
    echo Recreating virtual environment...
    rmdir /s /q %VENV_PATH%
    python -m venv %VENV_PATH%
    if !count_python! lss 3 (
        goto check_python
    ) else (
        echo Something went wrong. Please try again.
        pause
        exit /b
    )
)

:: Activate the virtual environment
set count_activate=0
:activate
echo Activating virtual environment...
call %ACTIVATE_PATH%
if errorlevel 1 (
    set /a count_activate+=1
    echo Failed to activate virtual environment.
    echo Recreating virtual environment...
    rmdir /s /q %VENV_PATH%
    python -m venv %VENV_PATH%
    if !count_activate! lss 3 (
        goto activate
    ) else (
        echo Failed to activate virtual environment. Please try again.
        pause
        exit /b
    )
)

:: Get the list of installed packages using pip freeze
echo Checking the requirements...
for /f "tokens=1,* delims==" %%i in ('pip freeze') do (
    set installed[%%i]=%%j
)

:: Compare with the requirements from the requirements.txt file
for /f "tokens=1,* delims==" %%i in (%requirementsFile%) do (
    if not "!installed[%%i]!"=="%%j" (
        echo Installing package: %%i==%%j
        pip install %%i==%%j --upgrade --quiet
        if errorlevel 1 (
            echo Failed to install %%i==%%j. Please check your internet connection and try again.
            pause
            exit /b
        )
    )
)

:: Run the program
echo Starting %NAME%...
start /B "" "%VENV_PATH%\Scripts\pythonw.exe" %RUN% %* > nul 2>&1
if errorlevel 1 (
    echo Failed to start %NAME%. Please try again.
    pause
    exit /b
)

exit /b

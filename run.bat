@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"
set NAME=AutoSubSync
set PROJECTFOLDER=main
set RUN=%PROJECTFOLDER%\AutoSubSync.pyw
set requirementsFile=%PROJECTFOLDER%\requirements.txt
set VENV_PATH=.venv
set ACTIVATE_PATH=%VENV_PATH%\Scripts\activate
set CURRENT_DIR=%CD%
set LAST_DIR_FILE=%PROJECTFOLDER%\last_known_directory.txt
set refrenv=%PROJECTFOLDER%\refrenv.bat
set PYTHON_DOWNLOAD_URL=https://www.python.org/ftp/python/3.13.0/python-3.13.0-amd64.exe
set FFSUBSYNC_RECOMMENDED_PYTHON_VERSION=31207

:: Display provided argument if any
if not "%~1"=="" (
    echo Open with: "%~1"
)

:: Check if the required programs are installed
pip --version >nul 2>&1 && (set python_installed=true) || (set python_installed=false)
ffmpeg -version >nul 2>&1 && (set ffmpeg_installed=true) || (set ffmpeg_installed=false)

:: Check if Python and ffmpeg are installed
if not "%python_installed%"=="true" (
    if not "%ffmpeg_installed%"=="true" (
        echo Python and ffmpeg are required to run this program.
        set /p "install_both=Do you want to install Python and ffmpeg (y/n)?: "
        if /i "!install_both!"=="y" (
            echo Installing Python and ffmpeg...
            winget install python ffmpeg --accept-package-agreements
            if errorlevel 1 (
                echo Failed to install Python or ffmpeg using winget. Trying to install Python manually...
                goto bothwingetfailed
            )
            set python_installed=true
            set ffmpeg_installed=true
            :: Refresh the environment variables
            call %refrenv%
        ) else (
            echo Both Python and ffmpeg are required to run this program. Please install them and try again.
            pause
            exit /b
        )
    )
)

if not "%python_installed%"=="true" (
    echo Python is required to run this program.
    set /p "userinp=Do you want to install Python (y/n)?: "
    if /i "!userinp!"=="y" (
        echo Downloading Python...
        winget install python --accept-package-agreements
        if errorlevel 1 (
            echo Download failed using winget method. Trying to download manually...
            :bothwingetfailed
            if not exist "%PROJECTFOLDER%\python_installer.exe" (
                echo Downloading Python from %PYTHON_DOWNLOAD_URL%
                curl %PYTHON_DOWNLOAD_URL% -o %PROJECTFOLDER%\python_installer.exe
                if not exist "%PROJECTFOLDER%\python_installer.exe" (
                    echo Download failed using curl. Trying with the powershell method
                    powershell -Command "& {Invoke-WebRequest -Uri '%PYTHON_DOWNLOAD_URL%' -OutFile '%PROJECTFOLDER%\python_installer.exe'}"
                    if errorlevel 1 (
                        echo Failed to install Python. Please install Python manually and try again.
                        pause
                        exit /b
                    )
                )
            )
            echo Installing Python. Please wait...
            start /wait %PROJECTFOLDER%\python_installer.exe /quiet InstallAllUsers=1 PrependPath=1 Include_test=0
            if errorlevel 1 (
                echo Failed to install Python. Please install Python manually and try again.
                pause
                exit /b
            )
            del %PROJECTFOLDER%\python_installer.exe
            goto python_ok
        )
    ) else (
        echo Python is required to run this program. Please install Python and try again.
        pause
        exit /b
    )
    :python_ok
    echo Python installed successfully.
    :: Refresh the environment variables
    call %refrenv%
    set python_installed=true
)



:: Check if ffmpeg is installed
if not "%ffmpeg_installed%"=="true" (
    echo ffmpeg is required to run this program.
    set /p "install_ffmpeg=Do you want to install ffmpeg (y/n)?: "
    if /i "!install_ffmpeg!"=="y" (
        echo Installing ffmpeg...
        winget install ffmpeg --accept-package-agreements
        if errorlevel 1 (
            echo Download failed using winget method. Trying chocolatey method...
            :: Check admin rights
            goto check_Permissions
            :continue_install_ffmpeg
            choco -v >nul 2>&1
            if errorlevel 1 (
                echo Installing chocolatey...
                powershell -Command "Set-ExecutionPolicy Bypass -Scope Process -Force; [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072; iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))"
                if errorlevel 1 (
                    echo Failed to install chocolatey. You need to install ffmpeg manually.
                    pause
                    exit /b
                )
                call %refrenv%
            )
            choco install ffmpeg-full -y
            if errorlevel 1 (
                echo Failed to install ffmpeg using chocolatey. Please install ffmpeg manually and try again.
                pause
                exit /b
            )
        )
        set ffmpeg_installed=true
        goto ffmpeg_ok
    ) else (
        echo ffmpeg is required to run this program. Please install ffmpeg and try again.
        pause
        exit /b
    )
    :ffmpeg_ok
    echo ffmpeg installed successfully.
    set python_installed=true
    :: Refresh the environment variables
    call %refrenv%
)

:: Check if virtual environment exists
IF NOT EXIST %VENV_PATH% (
    echo Creating virtual environment...
    echo %CURRENT_DIR% > "%LAST_DIR_FILE%"
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

:: Check if the current directory has changed since the last run
if exist "%LAST_DIR_FILE%" (
    set /p last_dir=<"%LAST_DIR_FILE%"
    cd "%CURRENT_DIR%" && (
        if not exist "!last_dir!" (
            echo Current directory: %CURRENT_DIR%
            echo Last known directory: !last_dir!
            echo Looks like the directory of the program has been changed. 
            echo It is hihgly recommended to recreate the virtual environment.
            set /p "recreate_venv=Recreate the virtual environment (y/n)?: "
            if /i "!recreate_venv!"=="y" (
                echo Recreating virtual environment...
                rmdir /s /q %VENV_PATH%
                python -m venv %VENV_PATH%
				:: Update the last directory file
				echo %CURRENT_DIR% > "%LAST_DIR_FILE%"
            )
        )
    )
) else (
    :: Create the last directory file if it doesn't exist
    echo %CURRENT_DIR% > "%LAST_DIR_FILE%"
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

:: Check if tkinter is installed
%VENV_PATH%\Scripts\python.exe -c "import tkinter" 2>nul
if errorlevel 1 (
    echo tkinter is not installed. Installing tkinter...
    pip install tk
    if errorlevel 1 (
        echo Failed to install tkinter. Please check your internet connection and try again.
        pause
        exit /b
    )
)

:: Check Python version for ffsubsync
for /f "tokens=2 delims= " %%i in ('python --version') do set PYTHON_VERSION=%%i
for /f "tokens=1,2,3 delims=." %%a in ("%PYTHON_VERSION%") do (
    set PYTHON_MAJOR=%%a
    set PYTHON_MINOR=%%b
    set PYTHON_PATCH=%%c
)
if not defined PYTHON_PATCH (
    set PYTHON_PATCH=0
)
for /f "tokens=* delims=0" %%i in ("%PYTHON_MAJOR%") do set PYTHON_MAJOR=%%i
for /f "tokens=* delims=0" %%i in ("%PYTHON_MINOR%") do set PYTHON_MINOR=%%i
for /f "tokens=* delims=0" %%i in ("%PYTHON_PATCH%") do set PYTHON_PATCH=%%i
set /a PYTHON_VERSION_NUMBER=%PYTHON_MAJOR%*10000 + %PYTHON_MINOR%*100 + %PYTHON_PATCH%
if %PYTHON_VERSION_NUMBER% gtr %FFSUBSYNC_RECOMMENDED_PYTHON_VERSION% (
    echo.
    echo Warning: Your Python version is %PYTHON_VERSION%.
    echo ffsubsync might give an error when installing.
    echo If that happens, please install Python 3.12.7 or lower.
    echo.
)

:: Get the list of installed packages using pip freeze
echo Checking the requirements...
:: python.exe -m pip install --upgrade pip --quiet
for /f "tokens=1,* delims==" %%i in ('pip freeze --all') do (
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

:check_Permissions
call :isAdmin
if %errorlevel% == 0 (
    goto :continue_install_ffmpeg
) else (
    cls
    set /p "runasadmin=Admin rights required for this operation. Do you want to run this script as an administrator (y/n)?: "
    if /i "!runasadmin!"=="y" (
        echo Running as administrator...
        powershell -Command "Start-Process cmd -Verb RunAs -ArgumentList '/c %~dpnx0 %*'"
        exit /b
    ) else (
    echo Exiting current command prompt...
    exit
    )
)
pause >nul
exit /b
:isAdmin
fsutil dirty query %systemdrive% >nul
exit /b
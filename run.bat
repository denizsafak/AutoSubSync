@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"
set NAME=AutoSubSync
set PROJECTFOLDER=main
set RUN=%PROJECTFOLDER%\AutoSubSync.pyw
set requirementsFile=%PROJECTFOLDER%\requirements.txt
set CURRENT_DIR=%CD%
set LAST_DIR_FILE=%PROJECTFOLDER%\last_known_directory.txt
set refrenv=%PROJECTFOLDER%\refrenv.bat
set PYTHON_PATH=python_embedded\python.exe
set PYTHONW_PATH=python_embedded\pythonw.exe
set PYTHON_EMBEDDED_URL=https://github.com/wojiushixiaobai/Python-Embed-Win64/releases/download/3.12.8/python-3.12.8-embed-amd64.zip
set PYTHON_EMBEDDED_FILE=%PROJECTFOLDER%\python_embedded.zip

:: Check if ffmpeg is installed
ffmpeg -version >nul 2>&1 && (set ffmpeg_installed=true) || (set ffmpeg_installed=false)
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
    :: Refresh the environment variables
    call %refrenv%
)

:: Check if Python exists
%PYTHON_PATH% -m chardet --version >nul 2>&1 && (set python_installed=true) || (set python_installed=false)
if "%python_installed%"=="false" (
    if not exist %PYTHON_EMBEDDED_FILE% (
        echo Downloading python_embedded.zip...
        curl -L -o %PYTHON_EMBEDDED_FILE% %PYTHON_EMBEDDED_URL%
        if errorlevel 1 (
            echo Failed to download embedded Python with curl. Trying with PowerShell method...
            powershell -Command "Invoke-WebRequest -Uri %PYTHON_EMBEDDED_URL% -OutFile %PYTHON_EMBEDDED_FILE%"
            if errorlevel 1 (
                echo Failed to download embedded Python. Please check your internet connection and try again.
                pause
                exit /b
            )
        )
    )

    if not exist "python_embedded" (
        echo Creating python_embedded directory...
        mkdir python_embedded
        if errorlevel 1 (
            echo Failed to create python_embedded directory.
            pause
            exit /b
        )
    )
    
    echo Unzipping python_embedded.zip...
    tar -xf %PYTHON_EMBEDDED_FILE% -C python_embedded
    if errorlevel 1 (
        echo Failed to unzip embedded Python with tar. Trying with PowerShell method...
        powershell -Command "Expand-Archive -Path %PYTHON_EMBEDDED_FILE% -DestinationPath python_embedded"
        if errorlevel 1 (
            echo Failed to unzip embedded Python.
            pause
            exit /b
        )
    )

    ::del %PYTHON_EMBEDDED_FILE%
    echo Editing python312._pth file...
    echo import site >> python_embedded\python312._pth
    echo ../main  >> python_embedded\python312._pth
        if errorlevel 1 (
            echo Failed to add import site and ../main to python312._pth file. Please edit the file manually and try again. You need to add 'import site' and '../main' to the file. You can find the file in python_embedded directory. After editing, please run this script again.
            pause
            exit /b
        )
    )

:: Display provided argument if any
if not "%~1"=="" (
    echo Open with: "%~1"
)

:: Check if the current directory has changed since the last run
if exist "%LAST_DIR_FILE%" (
    set /p last_dir=<"%LAST_DIR_FILE%"
    cd "%CURRENT_DIR%" && (
        if not exist "!last_dir!" (
            echo Current directory: %CURRENT_DIR%
            echo Last known directory: !last_dir!
            echo Looks like the directory of the program has been changed.
            :: Ask user if they want to reinstall requirements
            set /p choice="ffsubsync might not work. Do you want to re-install ffsubsync? (y/n): "
            if /i "!choice!"=="y" (
                echo Uninstalling ffsubsync...
                %PYTHON_PATH% -m pip uninstall ffsubsync -y
                echo Installing ffsubsync...
                %PYTHON_PATH% -m pip install ffsubsync --quiet
                :: Update the last directory file
                echo %CURRENT_DIR% > "%LAST_DIR_FILE%"
            )
        )
    )
) else (
    :: Create the last directory file if it doesn't exist
    echo %CURRENT_DIR% > "%LAST_DIR_FILE%"
)

:: Get the list of installed packages using pip freeze
echo Checking the requirements...
:: python.exe -m pip install --upgrade pip --quiet
for /f "tokens=1,* delims==" %%i in ('%PYTHON_PATH% -m pip freeze --all') do (
    set installed[%%i]=%%j
)

:: Compare with the requirements from the requirements.txt file
call :install_requirements

:: Run the program
echo Starting %NAME%...
start /B "" "%PYTHONW_PATH%" %RUN% %* > nul 2>&1
if errorlevel 1 (
    echo Failed to start %NAME%. Please try again.
    pause
    exit /b
)

exit /b

:install_requirements
for /f "tokens=1,* delims==" %%i in (%requirementsFile%) do (
    if "%%j"=="" (
        if not defined installed[%%i] (
            echo Installing latest package: %%i
            %PYTHON_PATH% -m pip install %%i --upgrade --quiet  --no-warn-script-location
            if errorlevel 1 (
                echo Failed to install %%i. Please check your internet connection and try again.
                pause
                exit /b
            )
        )
    ) else (
        if not "!installed[%%i]!"=="%%j" (
            echo Installing package: %%i==%%j
            %PYTHON_PATH% -m pip install %%i==%%j --upgrade --quiet  --no-warn-script-location
            if errorlevel 1 (
                echo Failed to install %%i==%%j. Please check your internet connection and try again.
                pause
                exit /b
            )
        )
    )
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
@echo off
echo AutoSubSync Docker Container Setup
echo ==================================

REM Check if Docker is installed
docker --version >nul 2>&1
if errorlevel 1 (
    echo Error: Docker is not installed or not in PATH
    echo Please install Docker Desktop first: https://docs.docker.com/get-docker/
    pause
    exit /b 1
)

REM Create necessary directories
echo Creating directories...
if not exist "input" mkdir input
if not exist "output" mkdir output  
if not exist "desktop" mkdir desktop

echo ✓ Directories created:
echo   - input\  (place your video and subtitle files here)
echo   - output\ (processed files will appear here)
echo   - desktop\ (container desktop directory)

REM Check if image exists, build if necessary
docker images autosubsync | findstr autosubsync >nul
if errorlevel 1 (
    echo Building Docker image...
    docker-compose build
    if errorlevel 1 (
        echo Error: Failed to build Docker image
        pause
        exit /b 1
    )
    echo ✓ Docker image built successfully
)

REM Start the container
echo Starting AutoSubSync container...
docker-compose up -d
if errorlevel 1 (
    echo Error: Failed to start container
    pause
    exit /b 1
)

REM Wait for container to start
timeout /t 3 /nobreak >nul

REM Check if container is running
docker ps | findstr autosubsync >nul
if errorlevel 1 (
    echo Error: Container failed to start
    echo Check logs with: docker-compose logs
    pause
    exit /b 1
)

echo ✓ AutoSubSync container is running!
echo.
echo Access AutoSubSync GUI:
echo 🌐 Web Interface: http://localhost:6080
echo 🖥️  VNC Client: localhost:5900 (no password)
echo.
echo File locations:
echo 📁 Input files: Place in .\input\ directory
echo 📁 Output files: Check .\output\ directory  
echo 📁 Desktop: .\desktop\ directory
echo.
echo Container management:
echo • View logs: docker-compose logs
echo • Stop: docker-compose stop
echo • Restart: docker-compose restart
echo • Remove: docker-compose down
echo.
echo Ready to use! Open http://localhost:6080 in your browser.

pause

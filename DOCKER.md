# AutoSubSync Docker Container

This Docker container packages AutoSubSync with all its dependencies, including a GUI accessible via web browser using PySide6.

## Quick Start

### Using Docker Compose (Recommended)

1. **Navigate to the AutoSubSync directory:**
   ```bash
   cd AutoSubSync
   ```

2. **Create input and output directories:**
   ```bash
   mkdir -p input output desktop
   ```

3. **Build and run the container:**
   ```bash
   docker-compose up --build -d
   ```

4. **Access the GUI:**
   Open your web browser and go to: http://localhost:6080

   Click "Connect" in the noVNC interface to access the desktop.

### Using provided scripts

For convenience, you can use the provided run scripts:

**On macOS/Linux:**
```bash
./run-docker.sh
```

**On Windows:**
```cmd
run-docker.bat
```

## What's Included

- ✅ AutoSubSync GUI with PySide6 (converted from PyQt6)
- ✅ FFmpeg for media processing
- ✅ All synchronization tools (ffsubsync, autosubsync, alass)
- ✅ Web-based VNC interface (noVNC)
- ✅ Fluxbox window manager
- ✅ File manager for easy file operations

## Usage

1. **Access the application:**
   - Open http://localhost:6080 in your web browser
   - Click "Connect" to access the desktop
   - AutoSubSync will be running automatically

2. **Upload files:**
   - Place your video and subtitle files in the `input/` directory
   - They will be accessible within the container at `/app/input/`
   - Use the file manager in the VNC interface to navigate

3. **Use AutoSubSync:**
   - The GUI works exactly like the desktop version
   - Load your video and subtitle files
   - Configure synchronization settings
   - Process your subtitles

4. **Download results:**
   - Processed files will appear in the `output/` directory
   - Or save directly to Desktop (mapped to `desktop/` directory)

## File Management

The container uses volume mounts to share files between your host system and the container:

- `./input/` ↔ `/app/input/` - Place your input files here
- `./output/` ↔ `/app/output/` - Output files will appear here
- `./desktop/` ↔ `/home/autosubsync/Desktop/` - Desktop directory for the container

## Features

- ✅ Full AutoSubSync GUI accessible via web browser
- ✅ PySide6 Qt framework (automatically converted from PyQt6)
- ✅ All synchronization tools included (ffsubsync, autosubsync, alass)
- ✅ FFmpeg included for media processing
- ✅ No need to install dependencies on your host system
- ✅ Cross-platform (works on Windows, macOS, Linux)
- ✅ Persistent file access via volume mounts
- ✅ Automatic PyQt6 to PySide6 conversion during build

## Technical Details

### Architecture

The container runs multiple services managed by supervisor:
- **Xvfb**: Virtual display server
- **Fluxbox**: Lightweight window manager
- **x11vnc**: VNC server for display sharing
- **noVNC**: Web-based VNC client (websockify + web interface)
- **AutoSubSync**: The main application

### PyQt6 to PySide6 Conversion

The container automatically converts PyQt6 imports to PySide6 during the build process:
- Handles import statement conversion
- Updates signal/slot syntax
- Manages Qt resource paths
- Safely handles None values in path operations

## Ports

- **6080**: Web-based VNC interface (primary access method)
- **5900**: Direct VNC port (optional, for VNC clients)

## Troubleshooting

### Container won't start
```bash
# Check container logs
docker-compose logs

# Check specific service status
docker exec autosubsync supervisorctl status
```

### Application crashes
```bash
# Check AutoSubSync logs
docker exec autosubsync cat /var/log/supervisor/autosubsync.log
docker exec autosubsync cat /var/log/supervisor/autosubsync_error.log
```

### Can't access files
Make sure your input files are in the `input/` directory and that you've created the necessary directories:
```bash
mkdir -p input output desktop
```

### GUI is not responsive
Refresh the browser page or restart the container:
```bash
docker-compose restart
```

### noVNC connection issues
If the web interface doesn't load:
```bash
# Check if all services are running
docker exec autosubsync supervisorctl status

# Restart specific services if needed
docker exec autosubsync supervisorctl restart novnc
```

### Performance issues
The container runs a full desktop environment. For better performance:
- Ensure Docker has sufficient memory allocated (at least 2GB recommended)
- Close other resource-intensive applications
- Use Docker Desktop's resource settings to allocate more CPU/memory

## Advanced Usage

### Using a VNC client instead of web browser

If you prefer using a dedicated VNC client:

1. Connect to `localhost:5900` with your VNC client
2. No password is required

### Custom display resolution

You can modify the display resolution by editing the `docker/supervisord.conf` file and changing the Xvfb screen parameter:
```
command=/usr/bin/Xvfb :0 -screen 0 1920x1080x24 -ac +extension GLX +render -noreset
```

### Development mode

To mount the source code for development:
```bash
docker-compose down
# Edit docker-compose.yml to add:
# - ./main:/app/main
docker-compose up --build
```

### Debugging

Access the container for debugging:
```bash
# Get a shell in the container
docker exec -it autosubsync bash

# Check running processes
docker exec autosubsync ps aux

# Monitor supervisor logs
docker exec autosubsync tail -f /var/log/supervisor/supervisord.log
```

## Building from source

The Dockerfile includes all necessary dependencies:
- Python 3.11 slim base image
- System packages (Qt6, X11, VNC tools)
- Python packages (PySide6, ffsubsync, autosubsync, etc.)
- Automatic PyQt6 to PySide6 conversion script
- Supervisor for service management
- All required binaries (alass, ffmpeg)

Build process:
1. Installs system dependencies
2. Installs Python packages (tries PyQt6, falls back to PySide6)
3. Copies application code
4. Runs conversion script to ensure PySide6 compatibility
5. Sets up services and permissions

## System Requirements

- Docker and Docker Compose
- At least 2GB available RAM
- 2GB available disk space for the image
- Modern web browser for the VNC interface

## Security Notes

- The container runs with a non-root user for the application
- No password is set for VNC (suitable for local use only)
- Services run on localhost only (not exposed to external networks)
- For production use, consider adding authentication and HTTPS

## Compatibility

- **Base Image**: Python 3.11 on Debian Bookworm
- **Qt Framework**: PySide6 (converted from PyQt6)
- **Supported Platforms**: x86_64 Linux containers
- **Host Systems**: Windows, macOS, Linux (with Docker)

## Support

For issues specific to the Docker container:
1. Check container logs: `docker-compose logs`
2. Verify directories exist: `mkdir -p input output desktop`
3. Ensure Docker has sufficient resources
4. Check service status: `docker exec autosubsync supervisorctl status`

For AutoSubSync application issues, refer to the main project documentation.

## Files Created

This Docker setup creates several files:
- `Dockerfile` - Main container definition
- `docker-compose.yml` - Service orchestration
- `docker/supervisord.conf` - Service management configuration
- `docker/start.sh` - Container startup script
- `docker/convert_qt.py` - PyQt6 to PySide6 conversion script
- `run-docker.sh` / `run-docker.bat` - Convenience run scripts
- `.dockerignore` - Build context exclusions

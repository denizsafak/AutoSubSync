# Use Python 3.11 official image
FROM python:3.11-slim-bookworm

# Set environment variables
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV DISPLAY=:0
ENV QT_QPA_PLATFORM=xcb

# Install system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    wget \
    xvfb \
    x11vnc \
    fluxbox \
    supervisor \
    curl \
    ca-certificates \
    fonts-dejavu-core \
    libgl1-mesa-glx \
    libegl1-mesa \
    libxrandr2 \
    libxss1 \
    libxcursor1 \
    libxcomposite1 \
    libasound2 \
    libxi6 \
    libxtst6 \
    libxcb-xinerama0 \
    libxcb-cursor0 \
    libxkbcommon-x11-0 \
    libxcb-icccm4 \
    libxcb-image0 \
    libxcb-keysyms1 \
    libxcb-randr0 \
    libxcb-render-util0 \
    libxcb-shape0 \
    libfontconfig1 \
    libfreetype6 \
    git \
    build-essential \
    qt6-base-dev \
    qt6-tools-dev \
    qt6-tools-dev-tools \
    libqt6gui6 \
    libqt6widgets6 \
    libqt6core6 \
    qt6-qpa-plugins \
    && rm -rf /var/lib/apt/lists/*

# Install NoVNC
RUN git clone https://github.com/novnc/noVNC.git /opt/novnc \
    && git clone https://github.com/novnc/websockify /opt/novnc/utils/websockify \
    && ln -s /opt/novnc/vnc.html /opt/novnc/index.html

# Install alass
RUN wget -O /usr/local/bin/alass-cli https://github.com/kaegi/alass/releases/latest/download/alass-linux64 \
    && chmod +x /usr/local/bin/alass-cli

# Create a non-root user
RUN useradd -ms /bin/bash autosubsync

# Set working directory
WORKDIR /app

# Copy pyproject.toml and install Python dependencies
COPY pyproject.toml .
COPY main/VERSION ./main/
RUN python -m pip install --no-cache-dir --upgrade pip setuptools wheel hatchling

# Try to install PyQt6 using pre-built wheels or system packages
# First try installing PyQt6 with specific flags to use system Qt
ENV QT_QPA_PLATFORM_PLUGIN_PATH=/usr/lib/qt6/plugins/platforms
RUN python -m pip install --no-cache-dir PyQt6 || \
    python -m pip install --no-cache-dir PySide6 || \
    echo "Both PyQt6 and PySide6 installation failed"

# Install Python packages from pyproject.toml dependencies
RUN python -m pip install --no-cache-dir \
    rich \
    faust-cchardet \
    charset-normalizer \
    chardet \
    requests \
    psutil \
    platformdirs \
    ffsubsync \
    autosubsync \
    websockify

# Copy the application
COPY main/ ./main/
COPY images/ ./images/
COPY README.md LICENSE CHANGELOG ./

# Copy and run Qt conversion script
COPY docker/convert_qt.py /tmp/convert_qt.py
RUN python /tmp/convert_qt.py && rm /tmp/convert_qt.py

# Create necessary directories
RUN mkdir -p /app/main/resources/alass-bin/ \
    && mkdir -p /app/main/resources/autosubsync/ \
    && mkdir -p /app/main/assets/ \
    && mkdir -p /home/autosubsync/.config \
    && mkdir -p /home/autosubsync/Desktop

# Copy alass binary to the expected location
RUN cp /usr/local/bin/alass-cli /app/main/resources/alass-bin/alass-linux64 \
    && chmod +x /app/main/resources/alass-bin/alass-linux64

# Test autosubsync installation
RUN python -c "import autosubsync; print('autosubsync installed successfully')"

# Set up VNC and web interface
COPY docker/supervisord.conf /etc/supervisor/conf.d/supervisord.conf
COPY docker/start.sh /start.sh
RUN chmod +x /start.sh

# Create supervisor config directory
RUN mkdir -p /etc/supervisor/conf.d/

# Change ownership to autosubsync user
RUN chown -R autosubsync:autosubsync /app /home/autosubsync

# Expose VNC and web interface ports
EXPOSE 5900 6080

# Set the entrypoint (run as root to start supervisor)
ENTRYPOINT ["/start.sh"]

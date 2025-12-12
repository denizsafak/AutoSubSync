# Use Python 3.11 official image
FROM python:3.11-slim-bookworm

# Set environment variables
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV DISPLAY=:0
ENV QT_QPA_PLATFORM=xcb

# Install system dependencies
RUN apt-get update && apt-get install -y \
    xvfb \
    x11vnc \
    fluxbox \
    supervisor \
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
    libqt6gui6 \
    libqt6widgets6 \
    libqt6core6 \
    qt6-qpa-plugins \
    && rm -rf /var/lib/apt/lists/*

# Install NoVNC
RUN git clone https://github.com/novnc/noVNC.git /opt/novnc \
    && git clone https://github.com/novnc/websockify /opt/novnc/utils/websockify \
    && ln -s /opt/novnc/vnc.html /opt/novnc/index.html

# Create a non-root user
RUN useradd -ms /bin/bash autosubsync

# Set working directory
WORKDIR /app

# Install assy from PyPI
RUN python -m pip install --no-cache-dir assy websockify

# Fix permissions for static_ffmpeg cache
RUN chown -R autosubsync:autosubsync /usr/local/lib/python3.11/site-packages/static_ffmpeg || true

# Test installation
RUN python -c "import main; print('assy installed successfully')"

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

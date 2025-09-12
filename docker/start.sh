#!/bin/bash

# Create necessary directories
mkdir -p /var/log/supervisor
mkdir -p /home/autosubsync/.config
mkdir -p /home/autosubsync/Desktop

# Set up the display
export DISPLAY=:0

# Change ownership of log directory
chown -R autosubsync:autosubsync /home/autosubsync
chown -R root:root /var/log/supervisor

# Start supervisor as root
exec supervisord -c /etc/supervisor/conf.d/supervisord.conf

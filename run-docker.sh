#!/bin/bash

# AutoSubSync Docker Runner Script

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}AutoSubSync Docker Container Setup${NC}"
echo "=================================="

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo -e "${RED}Error: Docker is not installed or not in PATH${NC}"
    echo "Please install Docker first: https://docs.docker.com/get-docker/"
    exit 1
fi

# Check if Docker Compose is available
if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo -e "${RED}Error: Docker Compose is not available${NC}"
    echo "Please install Docker Compose or use a newer version of Docker"
    exit 1
fi

# Create necessary directories
echo -e "${YELLOW}Creating directories...${NC}"
mkdir -p input output desktop

echo -e "${GREEN}✓ Directories created:${NC}"
echo "  - input/  (place your video and subtitle files here)"
echo "  - output/ (processed files will appear here)"
echo "  - desktop/ (container desktop directory)"

# Check if we should build or just run
if [[ "$1" == "build" ]] || [[ ! "$(docker images -q autosubsync 2> /dev/null)" ]]; then
    echo -e "${YELLOW}Building Docker image...${NC}"
    if command -v docker-compose &> /dev/null; then
        docker-compose build
    else
        docker compose build
    fi
    echo -e "${GREEN}✓ Docker image built successfully${NC}"
fi

# Start the container
echo -e "${YELLOW}Starting AutoSubSync container...${NC}"
if command -v docker-compose &> /dev/null; then
    docker-compose up -d
else
    docker compose up -d
fi

# Wait a moment for the container to start
sleep 3

# Check if container is running
if docker ps | grep -q autosubsync; then
    echo -e "${GREEN}✓ AutoSubSync container is running!${NC}"
    echo ""
    echo -e "${BLUE}Access AutoSubSync GUI:${NC}"
    echo "🌐 Web Interface: http://localhost:6080"
    echo "🖥️  VNC Client: localhost:5900 (no password)"
    echo ""
    echo -e "${BLUE}File locations:${NC}"
    echo "📁 Input files: Place in ./input/ directory"
    echo "📁 Output files: Check ./output/ directory"
    echo "📁 Desktop: ./desktop/ directory"
    echo ""
    echo -e "${BLUE}Container management:${NC}"
    echo "• View logs: docker-compose logs"
    echo "• Stop: docker-compose stop"
    echo "• Restart: docker-compose restart"
    echo "• Remove: docker-compose down"
    echo ""
    echo -e "${GREEN}Ready to use! Open http://localhost:6080 in your browser.${NC}"
else
    echo -e "${RED}Error: Container failed to start${NC}"
    echo "Check logs with: docker-compose logs"
    exit 1
fi

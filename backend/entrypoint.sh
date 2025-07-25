#!/bin/sh
set -e

echo "Building AirDecky backend..."
echo "Container's IP address: `awk 'END{print $1}' /etc/hosts`"

cd /backend

# Ensure Python dependencies are available
python3 -c "import zeroconf, requests; print('Dependencies OK')" || {
    echo "Installing Python dependencies..."
    pip3 install --break-system-packages "zeroconf>=0.120.0" "requests>=2.28.0"
}

# Run make to set up backend
make

echo "AirDecky backend build completed successfully."
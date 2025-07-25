#!/bin/bash
set -e

echo "Installing Python dependencies for AirDecky..."

pip install --target=/home/deck/homebrew/plugins/airdecky/py_modules \
    zeroconf==0.131.0 \
    requests==2.31.0 \
    Pillow==10.0.0

echo "Python dependencies installed successfully."

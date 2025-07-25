FROM ghcr.io/steamdeckhomebrew/holo-base:latest

# Install required system packages
RUN pacman -S --noconfirm python python-pip ffmpeg

# Copy requirements and install Python dependencies with system packages override
COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir --break-system-packages -r /tmp/requirements.txt

# Set working directory
WORKDIR /backend

ENTRYPOINT [ "/backend/entrypoint.sh" ]
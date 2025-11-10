#!/usr/bin/env bash
# Instalar dependencias del sistema necesarias para FFmpeg y PyAV
apt-get update && apt-get install -y \
    ffmpeg \
    libavformat-dev \
    libavcodec-dev \
    libavdevice-dev \
    libavutil-dev \
    libavfilter-dev \
    libswscale-dev \
    libswresample-dev

# Instalar dependencias de Python
pip install -r requirements.txt

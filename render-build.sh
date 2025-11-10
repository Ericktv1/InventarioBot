#!/usr/bin/env bash
set -eux

# Instalar librerías del sistema necesarias para FFmpeg y CTranslate2
apt-get update && apt-get install -y \
    ffmpeg \
    libavformat-dev \
    libavcodec-dev \
    libavdevice-dev \
    libavutil-dev \
    libavfilter-dev \
    libswscale-dev \
    libswresample-dev \
    build-essential \
    pkg-config \
    python3-dev

# Actualizar pip y setuptools
pip install --upgrade pip setuptools wheel

# Instalar dependencias del proyecto
pip install -r requirements.txt

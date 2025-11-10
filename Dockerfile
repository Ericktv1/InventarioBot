# Imagen base con Python 3.11.5
FROM python:3.11.5-slim

# Instalar dependencias del sistema necesarias para ffmpeg, ctranslate2, etc.
RUN apt-get update && apt-get install -y \
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
    python3-dev && \
    rm -rf /var/lib/apt/lists/*

# Crear el directorio de trabajo
WORKDIR /app

# Copiar los archivos del proyecto al contenedor
COPY . .

# Actualizar pip y setuptools
RUN pip install --upgrade pip setuptools wheel

# Instalar dependencias del proyecto
RUN pip install -r requirements.txt

# Comando para iniciar tu bot de Telegram
CMD ["python", "-m", "bot_app.main"]

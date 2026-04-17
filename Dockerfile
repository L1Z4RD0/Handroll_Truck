FROM python:3.12-slim

# Dependencias del sistema que necesita OpenCV headless y psycopg2
RUN apt-get update && apt-get install -y --no-install-recommends \
        libglib2.0-0 \
        libgl1 \
        libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Directorio de trabajo dentro del contenedor
WORKDIR /app

# Copiar primero requirements para aprovechar el cache de capas de Docker
COPY requirements.txt .

# Instalar dependencias Python (opencv-python-headless evita dependencias de GUI)
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el resto del código fuente
COPY control_acceso.py .
COPY database.py .
COPY dashboard.py .
COPY schema.sql .

# Punto de entrada principal
CMD ["python", "control_acceso.py"]

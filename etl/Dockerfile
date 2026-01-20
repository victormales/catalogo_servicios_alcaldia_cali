# Usamos una imagen ligera de Python
FROM python:3.9-slim

# Instalamos dependencias del sistema necesarias para PostgreSQL
RUN apt-get update && apt-get install -y libpq-dev gcc

WORKDIR /app

# Copiamos los requerimientos y los instalamos
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiamos el script ETL
COPY etl_pipeline.py .

# Comando por defecto: Esperar 10 seg (para que la BD inicie) y correr el ETL
CMD ["sh", "-c", "sleep 10 && python etl_pipeline.py"]

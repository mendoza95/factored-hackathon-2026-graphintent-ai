FROM python:3.11-slim

# Instalar Node.js para compilar el frontend
RUN apt-get update && apt-get install -y nodejs npm && rm -rf /var/lib/apt/lists/*

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=8080

# 1. Copiar package.json y package-lock.json
COPY app/frontend/package*.json ./app/frontend/

# Instalar dependencias limpias dentro de Linux
RUN cd app/frontend && npm install

# Copiar el código fuente del frontend (ya sin node_modules gracias a .dockerignore)
COPY app/frontend ./app/frontend

# Compilar la aplicación React/Vite
RUN cd app/frontend && npm run build

# 2. Instalar dependencias de Python del Backend
COPY pyproject.toml .
RUN pip install --no-cache-dir .

# 3. Copiar el resto del repositorio
COPY . .

EXPOSE 8080

CMD ["sh", "-c", "uvicorn app.backend.main:app --host 0.0.0.0 --port ${PORT:-8080}"]
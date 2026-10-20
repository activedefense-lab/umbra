# Umbra · Generador de señuelo. Contexto de construcción: senuelo/
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Instalar únicamente el paquete y sus dependencias de ejecución.
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install . && rm -rf /app/src

# Ejecutar sin privilegios de administrador.
RUN useradd --system --uid 10001 --no-create-home umbra
USER umbra

EXPOSE 8002

# Comprobar la API sin depender de que Ollama esté disponible.
HEALTHCHECK --interval=10s --timeout=3s --start-period=5s --retries=5 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8002/salud', timeout=2).status == 200 else 1)"

CMD ["uvicorn", "senuelo.api:app", "--host", "0.0.0.0", "--port", "8002"]

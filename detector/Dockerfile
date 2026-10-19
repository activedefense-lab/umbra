# Umbra · Detector (pasos 2 y 3). Contexto de construcción: detector/
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Solo lo necesario para instalar el paquete (no se copian pruebas ni .venv).
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install . && rm -rf /app/src

# Usuario sin privilegios.
RUN useradd --system --uid 10001 --no-create-home umbra
USER umbra

EXPOSE 8001

HEALTHCHECK --interval=10s --timeout=3s --start-period=5s --retries=5 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8001/salud', timeout=2).status == 200 else 1)"

CMD ["uvicorn", "detector.api:app", "--host", "0.0.0.0", "--port", "8001"]

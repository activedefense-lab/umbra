# Umbra · Detector (pasos 2 y 3).
# Nucleo independiente de CWE concretas (ADR-002).
# Contexto principal: detector/
# Contextos adicionales: contrato/ y complementos/

FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Incorporar el contrato y los complementos desde contextos independientes.
COPY --from=contrato . /build/contrato
COPY --from=complementos . /build/complementos

# Incorporar exclusivamente los archivos necesarios del detector.
COPY pyproject.toml README.md ./
COPY src ./src

# Resolver conjuntamente las dependencias locales y del servicio.
# Cada subdirectorio de complementos/ debe ser un paquete instalable.
RUN pip install /build/contrato /build/complementos/*/ . \
    && pip check \
    && rm -rf /build /app/src

# Ejecutar sin privilegios.
RUN useradd --system --uid 10001 --no-create-home umbra
USER umbra

EXPOSE 8001

HEALTHCHECK --interval=10s --timeout=3s --start-period=5s --retries=5 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8001/salud', timeout=2).status == 200 else 1)"

# Crear la aplicación al arrancar con el complemento configurado.
CMD ["uvicorn", "--factory", "detector.api:crear_app", "--host", "0.0.0.0", "--port", "8001"]

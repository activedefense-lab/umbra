# detector/ · Guía de desarrollo

Contenedor de **detección e inferencia** (pasos 2 y 3 del flujo). Versión mínima del sprint 1: reglas de metacaracteres e intención provisional por palabras clave. El sprint 5 reemplaza la puntuación por un clasificador scikit-learn sin cambiar la API ni los modelos.

## Estructura

```
detector/
  pyproject.toml                 Paquete umbra-detector, deps, config de pytest
  src/detector/
    modelos.py                   Pydantic: Peticion, Veredicto, enum Intencion
    reglas.py                    Motor genérico: normaliza, detecta, segmenta, puntúa, decide
    catalogo_cwe78.json          Datos: metacaracteres, separadores y palabras clave por intención
    api.py                       FastAPI: GET /salud, POST /analizar
  tests/                         pytest: motor y API
```

El **motor** (`reglas.py`) no conoce ningún comando; todo lo específico de CWE-78 vive en `catalogo_cwe78.json`. En la issue #13 ese catálogo pasa al complemento `cwe78` a través del contrato de complementos.

## Importante: el catálogo está vacío a propósito

Las listas de `palabras_clave` en `catalogo_cwe78.json` están **vacías**. Se llenan en el sprint 2, cuando el protocolo del conjunto de datos (`docs/dataset/protocolo.md`) fije las reglas de etiquetado por intención a partir de fuentes citables (documentación de commix, MITRE ATT&CK). Hasta entonces el detector marca `es_ataque` por metacaracteres e intención `desconocida`, que es correcto y honesto: no inventa un criterio de etiquetado sin respaldo.

## Entorno y pruebas

```bash
cd detector
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest
```

## Arrancar el servicio en local

```bash
uvicorn detector.api:app --reload --port 8001
# Documentación interactiva en http://127.0.0.1:8001/docs
```

Ejemplo:

```bash
curl -s -X POST http://127.0.0.1:8001/analizar \
  -H 'content-type: application/json' \
  -d '{"origen":"anon","ruta":"/diagnostico/ping","parametro":"host","valor":"127.0.0.1;id"}'
```

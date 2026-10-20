# detector/ · Guía de desarrollo

Contenedor de **detección e inferencia** (pasos 2 y 3 del flujo de Umbra). Forma parte del núcleo del sistema y no implementa reglas específicas de ninguna CWE.

Delega el análisis en el complemento activo mediante el [contrato de complementos](../docs/adr/ADR-002-contrato-complementos.md) (ADR-002) y verifica cada veredicto antes de devolverlo.

Según el plan de desarrollo, en el **sprint 5** se prevé reemplazar la puntuación por palabras clave de cada complemento por un clasificador scikit-learn, sin modificar el contrato establecido.

## Estructura

```text
detector/
  pyproject.toml          Paquete umbra-detector; depende de umbra-contrato
  src/detector/
    api.py                FastAPI: GET /salud y POST /analizar
  tests/
    falsos.py             Complementos simulados para pruebas aisladas
    test_api.py           Pruebas HTTP, validación y desacoplamiento
```

La lógica de detección de CWE-78, incluidos el motor y su catálogo, reside en `complementos/cwe78/`.

El detector carga el complemento activo mediante *entry points*, utilizando la variable de entorno `UMBRA_COMPLEMENTO`. No importa directamente ningún complemento específico.

## Entorno y pruebas

La instalación se realiza desde la **raíz del repositorio**, porque `umbra-contrato` es un paquete local y no debe resolverse desde PyPI.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ./contrato -e ./complementos/cwe78 -e "./detector[dev]"
(cd detector && pytest)
```

Las pruebas de la API utilizan complementos simulados para comprobar el comportamiento del núcleo sin depender de las reglas de CWE-78.

Las pruebas específicas del motor se encuentran en `complementos/cwe78/tests/`.

## Arrancar el servicio en local

La variable `UMBRA_COMPLEMENTO` identifica el complemento que debe cargarse.

Si no está configurada o el complemento solicitado no está instalado, la creación de la aplicación falla. Este comportamiento evita iniciar el detector sin un complemento válido.

```bash
UMBRA_COMPLEMENTO=cwe78 uvicorn --factory detector.api:crear_app --reload --port 8001
```

Documentación interactiva: http://127.0.0.1:8001/docs

## Ejemplo de análisis

```bash
curl -s -X POST http://127.0.0.1:8001/analizar \
  -H 'content-type: application/json' \
  -d '{"origen":"anon","ruta":"/diagnostico/ping","parametro":"host","valor":"127.0.0.1;id"}'
```

El endpoint `POST /analizar` recibe una `Peticion` definida por el contrato, delega su análisis en el complemento activo y devuelve un `Veredicto` validado.

El endpoint `GET /salud` informa el estado del servicio, su versión, el complemento activo y los complementos instalados.

## Responsabilidades

El detector es responsable de cargar el complemento, exponer la API HTTP y verificar los resultados conforme al contrato.

Cada complemento es responsable de su lógica de detección, sus catálogos y sus pruebas específicas.

Esta separación está diseñada para incorporar nuevas categorías de vulnerabilidad sin modificar la lógica interna del detector. Su desacoplamiento se comprobará mediante un complemento ficticio en las pruebas transversales y se evaluará posteriormente al incorporar CWE-79 ([ADR-002](../docs/adr/ADR-002-contrato-complementos.md), decisión 10).
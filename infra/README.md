
# infra/

Infraestructura del laboratorio y del esqueleto. Lidera: Santiago. Revisa y prueba: Camila.

| Ruta | Qué es |
|---|---|
| `docker-compose.yml` | Esqueleto integrado con PostgreSQL, detector (`127.0.0.1:8001`) y señuelo (`127.0.0.1:8002`). |
| `scripts/esqueleto.sh` | Comandos `arriba`, `estado`, `abajo`, `logs [servicio]` y `reiniciar-datos`. |
| `dev/compose.postgres.yml` | PostgreSQL independiente en `127.0.0.1:5433` para desarrollar `registro/` desde el anfitrión. |
| `pruebas/` | Pruebas de integración de `/interceptar` contra el esqueleto real. |
| `ci/` | Doble de prueba de Ollama para ejecutar esas pruebas en el CI (no sustituye las pruebas con Ollama real). |
| `../.github/workflows/ci.yml` | Integración continua: contrato, complementos, detector, señuelo, registro y Docker Compose. |

## Uso

Desde la raíz del repositorio:

```bash
infra/scripts/esqueleto.sh arriba
```

El comando construye las imágenes, inicia los servicios, espera sus verificaciones de salud y consulta los endpoints `/salud` del detector y del señuelo.

Servicios disponibles:

| Servicio | Dirección |
|---|---|
| Detector | `http://127.0.0.1:8001/docs` |
| Señuelo | `http://127.0.0.1:8002/docs` |
| Salud del detector | `http://127.0.0.1:8001/salud` |
| Salud del señuelo | `http://127.0.0.1:8002/salud` |
| Señuelo listo para generar | `http://127.0.0.1:8002/listo` |

Para consultar el estado:

```bash
infra/scripts/esqueleto.sh estado
```

Para detener los servicios sin eliminar los datos de PostgreSQL:

```bash
infra/scripts/esqueleto.sh abajo
```

El comando `reiniciar-datos` solicita confirmación antes de eliminar el volumen de PostgreSQL.

## Requisitos del anfitrión: Ollama

El señuelo usa un modelo de lenguaje local servido por Ollama **en el anfitrión**, fuera de Docker Compose, para aprovechar la GPU. Desde el contenedor lo alcanza en `http://host.docker.internal:11434`.

- **Una sola instalación de Ollama por anfitrión.** Dos instalaciones (por ejemplo, una en Windows y otra en WSL) compiten por el puerto 11434: el señuelo hablaría con la que arranque primero, sin aviso.
- **Modelo:** `llama3:latest`.
- **Dónde corre** puede variar entre equipos (Windows o WSL) siempre que el contenedor lo alcance en esa dirección. Lo que debe coincidir entre equipos es la versión del modelo (su ID en `ollama list`).

Comprobación desde un contenedor, con la misma resolución que usa el señuelo:

```bash
docker run --rm --add-host=host.docker.internal:host-gateway curlimages/curl:8.11.1 \
  -s http://host.docker.internal:11434/api/version
```

### Entornos del equipo

| | Camila | Santiago |
|---|---|---|
| Ollama | 0.40.3, servicio systemd en WSL 2 (Ubuntu) | En Windows (versión por registrar) |
| `llama3:latest` (ID) | `365c0bd3c000` | Por registrar |
| GPU | RTX 4070 Laptop, 8 GB (controlador 621.40) | RTX 5060 Laptop, 8 GB |

Mediciones orientativas de una sola ejecución en el equipo de Camila (27 nov 2026, `ollama run --verbose`), no resultados experimentales:

| | En frío | En caliente |
|---|---|---|
| Carga del modelo | 27,4 s | 0,002 s |
| Evaluación de la entrada | 2,2 tokens/s | 210 tokens/s |
| Generación | 2,1 tokens/s | 45,5 tokens/s |
| Total | 38,4 s | 2,4 s (107 tokens) |

El costo del arranque en frío depende del estado previo de Ollama, CUDA y el modelo. La primera ejecución tras arrancar WSL (tabla) superó el presupuesto de 20 s de una generación; con Ollama ya en marcha y el modelo descargado de memoria, el calentamiento del señuelo (un token) tardó 9,2 s. Son mediciones orientativas, en condiciones y operaciones distintas, y justifican el calentamiento al arrancar.

Con el modelo cargado la GPU ocupa 7,4 de 8 GB. Por eso `OLLAMA_KEEP_ALIVE` es `30m` por defecto y `-1` solo para la demostración y el experimento (ver `senuelo/README.md`).

### Antes de una demostración

```bash
OLLAMA_KEEP_ALIVE=-1 infra/scripts/esqueleto.sh arriba
curl -s http://127.0.0.1:8002/listo     # esperar "listo": true (200)
```

Si `/listo` responde 503 con `modelo no cargado en memoria` o el calentamiento `fallido`, `docker compose -f infra/docker-compose.yml restart senuelo` lo repite.

## Contrato y complementos

Las imágenes del detector y del señuelo instalan el paquete `contrato/` y los paquetes disponibles en `complementos/`.

Docker Compose utiliza contextos de construcción adicionales para incorporar estos paquetes.

La variable de entorno `UMBRA_COMPLEMENTO` selecciona el complemento activo. En el esqueleto actual se utiliza `cwe78` como complemento de referencia.

Ambos servicios exponen en `/salud` el complemento seleccionado y los complementos instalados.

## Decisiones

- **Ollama fuera de Docker Compose.** Se ejecuta en el anfitrión y el señuelo accede a él mediante `host.docker.internal:11434` (ver «Requisitos del anfitrión»).
- **PostgreSQL no se publica en el anfitrión** dentro del esqueleto; se utiliza desde los contenedores.
- **Contenedores sin privilegios.** Detector y señuelo utilizan el usuario `umbra` (UID 10001).
- **Red `arya-lab` (ADR-003).** La crea este Compose con nombre fijo. Solo el detector se une a ella; la aplicación objetivo (`lab-target`) la usa como red externa para llegar a `http://detector:8001`. Por eso el esqueleto se levanta antes que la aplicación objetivo.
- **Puertos locales.** Los endpoints HTTP del detector y del señuelo se publican únicamente en `127.0.0.1`.
- **Entorno de contención.** Su implementación queda separada del esqueleto actual, conforme a la planificación y las decisiones arquitectónicas del proyecto.

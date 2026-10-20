
# infra/

Infraestructura del laboratorio y del esqueleto. Lidera: Santiago. Revisa y prueba: Camila.

| Ruta | Qué es |
|---|---|
| `docker-compose.yml` | Esqueleto integrado con PostgreSQL, detector (`127.0.0.1:8001`) y señuelo (`127.0.0.1:8002`). |
| `scripts/esqueleto.sh` | Comandos `arriba`, `estado`, `abajo`, `logs [servicio]` y `reiniciar-datos`. |
| `dev/compose.postgres.yml` | PostgreSQL independiente en `127.0.0.1:5433` para desarrollar `registro/` desde el anfitrión. |
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

Para consultar el estado:

```bash
infra/scripts/esqueleto.sh estado
```

Para detener los servicios sin eliminar los datos de PostgreSQL:

```bash
infra/scripts/esqueleto.sh abajo
```

El comando `reiniciar-datos` solicita confirmación antes de eliminar el volumen de PostgreSQL.

## Contrato y complementos

Las imágenes del detector y del señuelo instalan el paquete `contrato/` y los paquetes disponibles en `complementos/`.

Docker Compose utiliza contextos de construcción adicionales para incorporar estos paquetes.

La variable de entorno `UMBRA_COMPLEMENTO` selecciona el complemento activo. En el esqueleto actual se utiliza `cwe78` como complemento de referencia.

Ambos servicios exponen en `/salud` el complemento seleccionado y los complementos instalados.

## Decisiones

- **Ollama fuera de Docker Compose.** Se ejecuta en el anfitrión y el señuelo accede a él mediante `host.docker.internal:11434`.
- **PostgreSQL no se publica en el anfitrión** dentro del esqueleto; se utiliza desde los contenedores.
- **Contenedores sin privilegios.** Detector y señuelo utilizan el usuario `umbra` (UID 10001).
- **Puertos locales.** Los endpoints HTTP del detector y del señuelo se publican únicamente en `127.0.0.1`.
- **Entorno de contención.** Su implementación queda separada del esqueleto actual, conforme a la planificación y las decisiones arquitectónicas del proyecto.

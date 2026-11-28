# senuelo/

Contenedor **Generador de señuelo** (pasos 4 y 5). Python + Ollama.

Produce, con un modelo de lenguaje local, respuestas ficticias coherentes con el contexto de simulación y la intención inferida. Nunca ejecuta comandos reales. Es parte del núcleo: no conoce ninguna CWE. Pide al complemento activo su contexto de simulación, lo compone con las restricciones de seguridad del núcleo y lo envía al modelo ([ADR-002](../docs/adr/ADR-002-contrato-complementos.md)). Sprint 6: plantillas por intención, estado de sesión y caché.

Lidera: Camila. Revisa y prueba: Santiago.

## Requisitos

- Python 3.12 o superior.
- Docker y Docker Compose para la ejecución en contenedores.
- Ollama instalado y en ejecución, con el modelo `llama3:latest`.

El microservicio utiliza Ollama para generar respuestas simuladas sin ejecutar los comandos recibidos. En la configuración actual, Ollama se ejecuta en el anfitrión y el señuelo puede ejecutarse localmente o dentro de Docker.

## Instalación local

Desde la raíz del repositorio `umbra`, en una sola invocación: `umbra-contrato` no existe en PyPI y debe resolverse desde las carpetas locales (ADR-002, decisión 9).

```bash
python3 -m venv senuelo/.venv
senuelo/.venv/bin/python -m pip install -e ./contrato -e ./complementos/cwe78 -e "./senuelo[dev]"
```

El entorno virtual mantiene las dependencias del señuelo separadas de los demás componentes del proyecto.

## Ejecución local

Con Ollama en funcionamiento y el modelo `llama3:latest` disponible, iniciar la API desde la raíz del repositorio. `UMBRA_COMPLEMENTO` es obligatoria: sin ella, o con un complemento no instalado, el servicio no arranca y el error lista los instalados.

```bash
UMBRA_COMPLEMENTO=cwe78 senuelo/.venv/bin/python -m uvicorn --factory senuelo.api:crear_app --host 127.0.0.1 --port 8002
```

La API estará disponible en `http://127.0.0.1:8002`.

Variables de configuración y sus valores por defecto:

| Variable | Defecto | Uso |
|---|---|---|
| `OLLAMA_URL` | `http://127.0.0.1:11434` | Dirección del servidor Ollama. |
| `OLLAMA_MODELO` | `llama3:latest` | Modelo utilizado. |
| `OLLAMA_TIMEOUT` | `20` | Segundos de espera de cada generación. Debe ser menor que el tiempo de espera del detector hacia el señuelo (25 s), y este menor que el del middleware (30 s). |
| `OLLAMA_TIMEOUT_CALENTAMIENTO` | `90` | Segundos de espera del calentamiento al arrancar. Es mayor porque en frío la primera generación tarda mucho más (medido: 38 s en WSL con una RTX 4070). |
| `OLLAMA_KEEP_ALIVE` | `30m` | Cuánto tiempo mantiene Ollama el modelo en memoria tras cada petición. Un número son segundos y `-1` es indefinido; un texto es una duración (`30m`, `2h`). Para la demostración y el experimento se usa `-1`. |

Los tiempos de espera y `OLLAMA_KEEP_ALIVE` se validan al arrancar: un valor inválido (por ejemplo, `OLLAMA_TIMEOUT=abc`, `0` o `nan`, u `OLLAMA_KEEP_ALIVE=incorrecto`) impide el arranque con un mensaje que nombra la variable. Una variable vacía toma su valor por defecto. `OLLAMA_URL` y `OLLAMA_MODELO` no se validan al arrancar: si son incorrectos, `/listo` lo muestra.

La temperatura (`0.3`) y el máximo de tokens (`128`) son constantes de `ollama.py`. La temperatura se devuelve en cada respuesta tomada del mismo cuerpo enviado a Ollama, para que el registro forense conserve el valor realmente usado.

## Ejecución con Docker

Desde la raíz del repositorio `umbra`, construir la imagen del señuelo:

```bash
docker compose -f infra/docker-compose.yml build senuelo
```

Iniciar únicamente el contenedor del señuelo:

```bash
docker compose -f infra/docker-compose.yml up -d --no-deps senuelo
```

Comprobar su estado:

```bash
docker compose -f infra/docker-compose.yml ps senuelo
```

El servicio expone la API en `http://127.0.0.1:8002`.

Dentro del contenedor, `OLLAMA_URL` está configurada como `http://host.docker.internal:11434` para comunicarse con Ollama en el anfitrión.

Esta conexión fue comprobada en el entorno de desarrollo con WSL2 y Docker. En otros entornos puede requerir ajustes de red.

## API HTTP

El microservicio dispone de tres endpoints:

### GET /salud

Comprueba que la API está funcionando e informa el complemento activo y los instalados.

Ejemplo ilustrativo de respuesta (con CWE-78 activo; los metadatos dependen de la instalación):

```json
{
  "estado": "ok",
  "version": "0.1.0",
  "complemento": {"nombre": "cwe78", "cwe": "CWE-78"},
  "instalados": [{"nombre": "cwe78", "paquete": "umbra-complemento-cwe78", "version": "0.1.0"}]
}
```

`/salud` responde mientras el proceso esté vivo y **no consulta a Ollama**: es la comprobación de vida (*liveness*) que usa el healthcheck de Docker. Que responda 200 no significa que el señuelo pueda generar.

### GET /listo

Indica si el señuelo puede generar **ahora** (*readiness*). En cada llamada consulta a Ollama qué modelos tiene cargados (`GET /api/ps`, máximo 2 s); no genera texto ni carga el modelo.

| Situación | Código | `motivo` |
|---|---|---|
| Ollama responde y el modelo está en memoria | 200 | — |
| Calentamiento inicial en curso | 503 | `calentamiento en curso` |
| Ollama no responde | 503 | `Ollama no disponible` |
| El modelo no está en memoria (p. ej. venció `keep_alive`) | 503 | `modelo no cargado en memoria` |

El cuerpo incluye además `modelo` y el estado del calentamiento (`pendiente`, `en_curso`, `completado` o `fallido`, con su detalle). Es la comprobación que se ejecuta antes de una demostración:

```bash
curl -s http://127.0.0.1:8002/listo
```

### Calentamiento al arrancar

Al iniciar, el señuelo lanza en segundo plano una generación mínima (un token) para cargar el modelo e inicializar la GPU. Se considera exitosa cuando Ollama responde con `"done": true`. Cargarlo no basta: en frío también la primera evaluación es lenta. El calentamiento **nunca bloquea ni impide el arranque**: si Ollama no está disponible, el resultado queda en el log (`docker compose logs senuelo`) y en `/listo`, y `/generar` responde 503 hasta que Ollama vuelva.

Para recuperar la disponibilidad (calentamiento fallido o modelo descargado), reiniciar el servicio repite el calentamiento:

```bash
docker compose -f infra/docker-compose.yml restart senuelo
```

### POST /generar

Recibe una `SolicitudSenuelo` del contrato con la información procesada por el detector y solicita a Ollama una respuesta simulada.

Ejemplo de solicitud:

```bash
curl -X POST http://127.0.0.1:8002/generar \
  -H "Content-Type: application/json" \
  -d '{"complemento":"cwe78","intencion":"reconocimiento","valor_normalizado":"hostname"}'
```

La respuesta incluye:

- `respuesta`: texto generado por el modelo.
- `modelo`: modelo de Ollama utilizado.
- `latencia_ms`: tiempo de generación en milisegundos.
- `temperatura`: temperatura enviada a Ollama en esta generación.

Respuestas de error:

- HTTP 422 si la solicitud no cumple el contrato (campos desconocidos, límites de longitud), si es para un complemento distinto del activo o si su intención no pertenece al catálogo del complemento activo (salvo `desconocida`). En estos casos no se compone ninguna instrucción.
- HTTP 503 si Ollama no está disponible o falla la generación.

## Pruebas automatizadas

Desde la raíz del repositorio, ejecutar:

```bash
senuelo/.venv/bin/python -m pytest senuelo/tests/ -v
```

La suite contiene 64 casos de prueba:

- `test_api.py` (14): API con un complemento falso: salud, composición de las instrucciones, errores 422 y 503, verificación del contexto, arranque obligatorio con `UMBRA_COMPLEMENTO` y comprobación de que el señuelo no importa complementos concretos.
- `test_ollama.py` (41): cliente de Ollama: transporte de las instrucciones, errores controlados, `keep_alive` (incluido `-1` como número y el rechazo de duraciones inválidas), temperatura registrada igual a la enviada, tiempos de espera independientes de generación, calentamiento y consulta, configuración inválida (incluidos `nan` e infinito), calentamiento exitoso aunque el token generado no tenga texto (pero solo si Ollama declara `done: true`) y consulta de modelos cargados.
- `test_disponibilidad.py` (9): `/salud` no depende de Ollama; el calentamiento no bloquea el arranque y no impide arrancar sin Ollama; `/listo` en cada situación, incluido el modelo descargado después de un calentamiento exitoso.

Las pruebas utilizan respuestas simuladas y no requieren que Ollama esté ejecutándose.

## Limitaciones actuales

- El señuelo no conserva el estado entre solicitudes.
- No dispone todavía de caché ni plantillas específicas por intención.
- Si el modelo se descarga de memoria (vence `keep_alive`), la siguiente generación vuelve a pagar el arranque en frío y puede superar `OLLAMA_TIMEOUT`. `/listo` lo detecta; para la demostración y el experimento se usa `OLLAMA_KEEP_ALIVE=-1`.
- Los tiempos de espera son valores iniciales de configuración; el presupuesto de latencia se mide en el sprint 6. Además, el tiempo de espera de `httpx` limita cada operación (conexión, envío, lectura), no la duración total de extremo a extremo. Como la generación no usa *streaming*, Ollama solo responde al terminar y el límite de lectura acota en la práctica la generación, pero la cadena 30 > 25 > 20 s es un presupuesto inicial, no una garantía demostrada.
- La coherencia de las respuestas entre solicitudes no está garantizada.
- La composición separa las instrucciones del núcleo de los datos del atacante, pero no garantiza que el modelo las respete; la resistencia frente a entradas adversariales se mide en la validación.

El señuelo genera texto según el contexto de simulación del complemento activo (con CWE-78, una terminal simulada). No ejecuta los comandos recibidos ni debe utilizarse como mecanismo independiente de aislamiento o contención.
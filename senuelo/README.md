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

Por defecto, el microservicio utiliza las siguientes variables de configuración:

- `OLLAMA_URL`: `http://127.0.0.1:11434`
- `OLLAMA_MODELO`: `llama3:latest`

Estas variables permiten modificar la dirección del servidor Ollama y el modelo utilizado.

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

El microservicio dispone de dos endpoints:

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

Respuestas de error:

- HTTP 422 si la solicitud no cumple el contrato (campos desconocidos, límites de longitud), si es para un complemento distinto del activo o si su intención no pertenece al catálogo del complemento activo (salvo `desconocida`). En estos casos no se compone ninguna instrucción.
- HTTP 503 si Ollama no está disponible o falla la generación.

## Pruebas automatizadas

Desde la raíz del repositorio, ejecutar:

```bash
senuelo/.venv/bin/python -m pytest senuelo/tests/ -v
```

La suite contiene diecisiete pruebas automatizadas:

- Doce pruebas de la API FastAPI con un complemento falso: salud, composición de las instrucciones, errores 422 y 503, verificación del contexto, arranque obligatorio con `UMBRA_COMPLEMENTO` y comprobación de que el señuelo no importa complementos concretos.
- Cinco pruebas del cliente Ollama, que verifican que transporta las instrucciones compuestas sin modificarlas.

Las pruebas utilizan respuestas simuladas y no requieren que Ollama esté ejecutándose.

## Limitaciones actuales

- El señuelo no conserva el estado entre solicitudes.
- No dispone todavía de caché ni plantillas específicas por intención.
- La primera inferencia puede presentar una latencia elevada mientras Ollama carga el modelo.
- La coherencia de las respuestas entre solicitudes no está garantizada.
- La composición separa las instrucciones del núcleo de los datos del atacante, pero no garantiza que el modelo las respete; la resistencia frente a entradas adversariales se mide en la validación.

El señuelo genera texto según el contexto de simulación del complemento activo (con CWE-78, una terminal simulada). No ejecuta los comandos recibidos ni debe utilizarse como mecanismo independiente de aislamiento o contención.
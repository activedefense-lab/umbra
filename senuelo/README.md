# senuelo/

Contenedor **Generador de señuelo** (pasos 4 y 5). Python + Ollama.

Produce, con un modelo de lenguaje local, las respuestas que un sistema real habría dado, coherentes con la intención inferida. Nunca ejecuta comandos reales. Sprint 1: un prompt de intérprete simulado y medición de latencia. Sprint 6: plantillas por intención, estado de sesión y caché.

Lidera: Camila. Revisa y prueba: Santiago.

## Requisitos

- Python 3.12 o superior.
- Docker y Docker Compose para la ejecución en contenedores.
- Ollama instalado y en ejecución, con el modelo `llama3:latest`.

El microservicio utiliza Ollama para generar respuestas simuladas sin ejecutar los comandos recibidos. En la configuración actual, Ollama se ejecuta en el anfitrión y el señuelo puede ejecutarse localmente o dentro de Docker.

## Instalación local

Desde la raíz del repositorio `umbra`, crear un entorno virtual e instalar las dependencias:

```bash
python3 -m venv senuelo/.venv
senuelo/.venv/bin/python -m pip install -e "./senuelo[dev]"
```

El entorno virtual mantiene las dependencias del señuelo separadas de los demás componentes del proyecto.

## Ejecución local

Con Ollama en funcionamiento y el modelo `llama3:latest` disponible, iniciar la API desde la raíz del repositorio:

```bash
senuelo/.venv/bin/python -m uvicorn senuelo.api:app --host 127.0.0.1 --port 8002
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

Comprueba que la API está funcionando.

Respuesta esperada:

```json
{
  "estado": "ok",
  "version": "0.1.0"
}
```

### POST /generar

Recibe la información procesada por el detector y solicita a Ollama una respuesta simulada.

Ejemplo de solicitud:

```bash
curl -X POST http://127.0.0.1:8002/generar \
  -H "Content-Type: application/json" \
  -d '{"intencion":"reconocimiento","segmentos":["hostname"],"valor_normalizado":"hostname"}'
```

La respuesta incluye:

- `respuesta`: texto generado por el modelo.
- `modelo`: modelo de Ollama utilizado.
- `latencia_ms`: tiempo de generación en milisegundos.

Si Ollama no está disponible o falla la generación, la API devuelve HTTP 503.

## Pruebas automatizadas

Desde la raíz del repositorio, ejecutar:

```bash
senuelo/.venv/bin/python -m pytest senuelo/tests/ -v
```

La suite contiene nueve pruebas automatizadas:

- Cuatro pruebas de la API FastAPI, incluida la validación de longitud de los segmentos.
- Cinco pruebas del cliente Ollama.

Las pruebas utilizan respuestas simuladas y no requieren que Ollama esté ejecutándose.

## Limitaciones actuales

- El señuelo no conserva el estado entre solicitudes.
- No dispone todavía de caché ni plantillas específicas por intención.
- La primera inferencia puede presentar una latencia elevada mientras Ollama carga el modelo.
- La coherencia de las respuestas entre solicitudes no está garantizada.
- La resistencia del modelo frente a entradas adversariales requiere pruebas adicionales.

El señuelo genera texto que representa una terminal simulada. No ejecuta los comandos recibidos ni debe utilizarse como mecanismo independiente de aislamiento o contención.
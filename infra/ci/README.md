# infra/ci/

Doble de prueba de Ollama **solo para el CI** (umbra#15, PR 3b). Permite que el job `compose` del CI ejecute las 7 pruebas de integración de `/interceptar` (`infra/pruebas/`) contra el esqueleto real, sin modelo de lenguaje.

| Archivo | Qué es |
|---|---|
| `ollama_doble.py` | Servidor HTTP mínimo, solo con biblioteca estándar. Imita `POST /api/generate`, `GET /api/ps` y `GET /api/version`. |
| `contrato_ollama_0.40.3.json` | Respuestas **reales** de Ollama 0.40.3 (`llama3:latest`) capturadas el 27 nov 2026. El doble las usa como plantilla. |
| `test_ollama_doble.py` | Pruebas del propio doble: fidelidad al contrato capturado y rechazo de peticiones incorrectas. |
| `simular_local.sh` | Simula en local el job `compose` del CI con el doble, sin tocar el Ollama real, y restaura siempre el señuelo al terminar. |

## Qué verifica el CI con el doble y qué no

**Verifica** el flujo: contratos entre servicios, calentamiento y `/listo` del señuelo, registro forense, fallo cerrado y recuperación.

**No verifica** la credibilidad del señuelo, la calidad de la generación, la latencia real ni el rendimiento de la GPU. El doble devuelve siempre el mismo texto, claramente artificial (`[doble de prueba de Ollama: respuesta fija del CI]`). Esas propiedades se miden con Ollama real (sprints 6 y 12). **El doble complementa las pruebas con el modelo real; no las sustituye.**

## Diseño

- **Corre en el anfitrión, fuera de Docker Compose**, en el puerto 11434, igual que Ollama en el laboratorio. El señuelo lo alcanza por `host.docker.internal`. No se usa un archivo de Compose adicional porque las pruebas destructivas reinician el señuelo solo con `infra/docker-compose.yml` y perderían la configuración del archivo adicional.
- **Escucha en `0.0.0.0`** para que los contenedores lleguen a él. El CI lo comprueba desde un contenedor antes de las pruebas.
- **Fidelidad:** las respuestas de `/api/generate` y `/api/ps` tienen los mismos campos que las capturadas. El 404 por modelo inexistente usa el texto real de Ollama. Los 400 (JSON inválido, petición incompleta) conservan el código y el formato `{"error": ...}`, pero con texto propio del doble: el mensaje de Ollama para el JSON inválido depende del error concreto del analizador de Go.
- **Valida lo que ARYA envía** para no dar por buenas peticiones incorrectas: el modelo configurado (si no, 404), `prompt` de texto, `stream: false`, `keep_alive` válido y `options.num_predict` entero positivo. Ollama real acepta peticiones sin `keep_alive` ni `num_predict`; el doble los exige porque ARYA siempre los envía, y sin `num_predict` la generación no tendría tope. La temperatura la cubren las pruebas del señuelo, que inspeccionan el cuerpo exacto enviado a Ollama.
- `/api/version` responde `0.40.3 (doble de prueba)`: el CI comprueba esa marca para detectar si otro proceso ocupa el puerto.
- `/api/ps` informa el modelo como cargado después de la primera generación (el calentamiento del señuelo).
- El CI guarda el log del doble y lo detiene al final, aunque las pruebas fallen. Además comprueba que la respuesta registrada en el evento 4 es el texto del doble: así se descarta que haya respondido otro servidor.

## Probar en local sin tocar el Ollama real

Con el esqueleto arriba (`infra/scripts/esqueleto.sh arriba`):

```bash
infra/ci/simular_local.sh
```

El script arranca el doble en el puerto 11435 (el Ollama real sigue en el 11434), recrea el señuelo apuntando a él, espera `/listo`, ejecuta las 7 pruebas y comprueba que no se usó el Ollama real: el señuelo conserva `OLLAMA_URL` después de las pruebas destructivas, el doble registró las generaciones y el texto del último evento 4 es el del doble. `OLLAMA_URL` solo existe dentro del script, nunca en la terminal.

**Al terminar, aunque falle o se interrumpa con Ctrl+C**, restaura el señuelo con el Ollama real, detiene el doble, comprueba que `OLLAMA_URL` volvió al puerto 11434 y espera `/listo`. El código de salida es el de las pruebas, o **3** si el entorno no se pudo restaurar. Si se cerrara la terminal a mitad de camino, la recuperación manual es:

```bash
env -u OLLAMA_URL docker compose -f infra/docker-compose.yml up -d --wait senuelo
pkill -f ollama_doble.py
curl -s http://127.0.0.1:8002/listo
```

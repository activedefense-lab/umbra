# infra/punta_a_punta/

Pruebas cruzadas del middleware `lab.deception` de la aplicación objetivo, **de punta a punta** (umbra#15, paso 5; ADR-003, «Consecuencias»). El middleware es de la línea de Santiago; estas pruebas las escribe Camila.

> **Estado: verificadas contra el entorno real el 2026-11-27 — 3 de 3 en 17 s** (esqueleto con Ollama real, `llama3:latest`; `lab-target` de `Kmilap/noctua` en `bf76d7f`, Docker en WSL). Verifican el **flujo** y la **evidencia**, no la **credibilidad** del señuelo: en esa ejecución el atacante recibió `$` como salida de `127.0.0.1;id`, idéntico a lo registrado, pero nada creíble. La credibilidad se trata en la demostración (#16).

| Prueba | Qué comprueba (lo que recibe el atacante y la evidencia forense) |
|---|---|
| (a) benigna | 200 con el ping real (`exit_code` 0, salida de `ping`), la misma forma JSON del endpoint y ninguna sesión forense nueva. |
| (b) inyección | 200 con exactamente `host`, `exit_code` y `output`, sin `sesion_id`; la sesión de **esa** carga tiene los eventos 2, 3 y 4 `respuesta_senuelo`, está cerrada y `output` es **igual** al texto del evento 4. |
| (c) señuelo detenido (`destructiva`) | 503 sin detalles internos; la sesión de esa carga queda con 2, 3 y 4 `error_senuelo` y cerrada. El señuelo se restaura siempre (`finally`) y se espera `/listo`. |

Las peticiones se hacen **desde dentro de `lab-target`** (`docker exec … curl`) contra `POST /api/lab/connectivity-check`, igual que la prueba manual de Santiago. La aplicación objetivo no reenvía `sesion_id` al atacante, así que cada prueba envía una carga **única** (con un token aleatorio) y busca la sesión cuyo evento 2 tiene exactamente ese valor: nunca se usa evidencia de una sesión anterior.

## Por qué en esta carpeta y no en `infra/pruebas/`

Requieren los dos repositorios (el esqueleto de umbra y `lab-target` de `Kmilap/noctua`), así que no pueden correr en el CI de umbra. En una carpeta propia **no entran en el CI ni en `pytest infra/pruebas`**; se piden con su ruta (ver «Siempre con la ruta» más abajo), sin tocar `infra/pruebas/pytest.ini` ni el CI (las 7 pruebas de `infra/pruebas/` siguen igual). Si al pedirlas falta el entorno, **la ejecución falla con código 2 y un mensaje claro**; nunca termina en verde con todo omitido.

## Ejecución (paso 5)

1. Esqueleto arriba: `infra/scripts/esqueleto.sh arriba` (crea la red `arya-lab`).
2. `lab-target` con el entorno de laboratorio. Con `php artisan serve`, `noctua-api/.env.lab` **manda** sobre el `environment:` del Compose; debe existir y contener `APP_ENV=lab`, `UMBRA_LAB_ENABLED=true`, `UMBRA_DETECTOR_URL=http://detector:8001/interceptar`, `UMBRA_DETECTOR_TIMEOUT=30` y un `APP_KEY` (ver `noctua-api/.env.lab-docker.example`).
3. `cd ~/noctua && docker compose --profile lab up -d lab-target`.
4. Señuelo listo: `curl -s http://127.0.0.1:8002/listo` debe dar 200. Si da 503 con «modelo no cargado en memoria» (Ollama lo descargó al vencer `keep_alive`), cargarlo sin generar texto:
   `curl -s http://127.0.0.1:11434/api/generate -d '{"model":"llama3:latest","prompt":"","keep_alive":"30m"}'`
5. Desde la raíz de umbra:

```bash
~/.venvs/umbra-int/bin/pytest infra/punta_a_punta
```

Sin la prueba que detiene el señuelo: `pytest infra/punta_a_punta -m "not destructiva"`.

> **Siempre con la ruta.** Un `pytest` sin argumentos desde la raíz del repositorio recoge todas las carpetas de pruebas, también esta y `infra/pruebas/`, y la sesión termina con código 2 en cuanto falta el entorno de alguna. No es un fallo del código: es la forma correcta de pedir estas pruebas.

Variables opcionales: `UMBRA_LAB_TARGET` (contenedor, `noctua-lab-target`), `UMBRA_LAB_ENDPOINT`, `UMBRA_DETECTOR`, `UMBRA_SENUELO`. No hay credenciales nuevas: se usan las del Compose de desarrollo.

El registro forense se consulta con `docker compose exec … psql` y cada consulta devuelve **un único valor JSON** (`json_agg`): un texto de señuelo con saltos de línea, barras o el separador no puede partir ni desalinear las filas.

Antes de las pruebas se verifica que el esqueleto responde, que `lab-target` corre, que la ruta de laboratorio no responde 404 (señal de un `.env.lab` incorrecto) y que el señuelo está listo. Si el señuelo está calentando, se espera hasta 2 minutos; si el modelo no está cargado, la ejecución termina con código 2 y la orden del paso 4.

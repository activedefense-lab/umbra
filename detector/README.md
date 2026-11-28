# detector/

Contenedor **Detección e inferencia** (pasos 2 y 3 del flujo). Python.

Recibe la petición derivada por la aplicación objetivo, delega el análisis en el complemento activo y devuelve un veredicto validado conforme al contrato definido en [ADR-002](../docs/adr/ADR-002-contrato-complementos.md).

Cada complemento implementa sus propias reglas de detección y declara las intenciones que puede identificar. Para **CWE-78**, estas corresponden a reconocimiento, descarga de herramientas, persistencia, exfiltración y movimiento lateral.

**Sprint 1:** detección mediante reglas y criterios provisionales. **Sprint 5:** incorporación planificada de un clasificador scikit-learn, manteniendo el contrato de complementos.

Lidera: Camila. Revisa y prueba: Santiago.

## Endpoints

| Endpoint | Uso |
|---|---|
| `GET /salud` | El proceso vive e informa el complemento activo. |
| `POST /analizar` | Devuelve solo el `Veredicto`. Lo usan el CI y el experimento de ablación. |
| `POST /interceptar` | Punto de entrada único de la aplicación objetivo ([ADR-003](../docs/adr/ADR-003-orquestacion-interceptacion.md)). |

`POST /interceptar` recibe una `Peticion` y devuelve una `Decision`:

- Petición legítima → `{"accion": "permitir", "respuesta": "", "sesion_id": null}`. No abre sesión.
- Ataque → abre una sesión forense, registra los eventos de los pasos 2, 3 y 4, pide la respuesta al señuelo y devuelve `{"accion": "senuelo", "respuesta": "<texto generado>", "sesion_id": "<uuid>"}`. La aplicación objetivo no reenvía `sesion_id` al atacante.
- **Fallo cerrado:** si el señuelo o el registro fallan, responde **503**. Nunca se degrada a `permitir`. Si falla el señuelo, la sesión queda registrada con un evento `error_senuelo`.

Límites, unidades y contenido de los eventos: «Precisiones de implementación» del ADR-003.

## Configuración

| Variable | Defecto | Uso |
|---|---|---|
| `UMBRA_COMPLEMENTO` | — (obligatoria) | Complemento activo. |
| `UMBRA_SENUELO_URL` | `http://127.0.0.1:8002` | Señuelo (`http://senuelo:8002` en Docker Compose). |
| `UMBRA_SENUELO_TIMEOUT` | `25` | Segundos de espera al señuelo. Un valor inválido impide arrancar. |
| `UMBRA_REGISTRO_DSN` | El de `registro/` | PostgreSQL del registro forense. El detector no se conecta al arrancar, sino en cada interceptación. |

## Pruebas

- `tests/test_api.py`: `/salud` y `/analizar` con complementos falsos.
- `tests/test_interceptar.py`: `/interceptar` con dobles del señuelo y del registro (`tests/registro_simulado.py`): decisión, orden y contenido de los eventos, sesión compartida, límites en caracteres y bytes, inyección después del carácter 4096, fallos parciales del registro y contrato.
- `tests/test_adaptadores.py`: cliente HTTP del señuelo (errores, tiempo de espera, validación de la respuesta) y registro con PostgreSQL no disponible.
- Integración con el señuelo, Ollama y PostgreSQL reales: `infra/pruebas/test_interceptar.py`.

# infra/pruebas/

Pruebas de integración contra el esqueleto real (umbra#15, ADR-003). Escribe: Santiago. Implementa lo probado: Camila (detector).

| Archivo | Qué verifica |
|---|---|
| `test_interceptar.py` | `POST /interceptar`: benigna → `permitir` sin sesión; ataque → `senuelo` con sesión cerrada y eventos de los pasos 2, 3 y 4; contrato `Peticion` estricto (422); `/analizar` sin cambios; fallo cerrado con el señuelo o el registro caídos (503) y recuperación tras reiniciar PostgreSQL. |

No usan simuladores: requieren el esqueleto arriba y Ollama en el anfitrión. PostgreSQL se consulta con `docker compose exec` porque no se publica en el anfitrión.

## Uso (desde la raíz del repositorio)

    python3 -m venv ~/.venvs/umbra-int
    ~/.venvs/umbra-int/bin/pip install -r infra/pruebas/requirements.txt
    infra/scripts/esqueleto.sh arriba
    ~/.venvs/umbra-int/bin/pytest infra/pruebas

Sin las destructivas: `pytest infra/pruebas -m "not destructiva"`.

## Estado

`/interceptar` está implementado en el detector (#15). Las 7 pruebas deben pasar con el esqueleto arriba y Ollama en el anfitrión. Su ejecución en el job `compose` del CI, con un doble de prueba de Ollama, llega en un PR aparte (#15, PR 3b).

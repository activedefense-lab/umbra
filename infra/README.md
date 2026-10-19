# infra/

Infraestructura del laboratorio y del esqueleto. Lidera: Santiago. Revisa y prueba: Camila.

| Ruta | Qué es |
|---|---|
| `docker-compose.yml` | Esqueleto de punta a punta: PostgreSQL (con el esquema de `registro/sql` aplicado al crear la base) y detector en `127.0.0.1:8001`. Señuelo (#11) y aplicación objetivo (#9) se añaden cuando existan. |
| `scripts/esqueleto.sh` | `arriba` · `estado` · `abajo` · `logs [servicio]` · `reiniciar-datos` |
| `dev/compose.postgres.yml` | PostgreSQL suelto en `127.0.0.1:5433` para desarrollar `registro/` desde el anfitrión. |
| `../.github/workflows/ci.yml` | Integración continua: pruebas del detector, pruebas del registro contra PostgreSQL real y arranque del compose en cada PR. |

## Uso

```bash
infra/scripts/esqueleto.sh arriba     # construye, levanta y espera salud
curl -s http://127.0.0.1:8001/salud
infra/scripts/esqueleto.sh abajo
```

## Decisiones

- **Ollama fuera del compose.** Corre en el anfitrión para usar la GPU (~35–50 tok/s frente a ~10 en CPU). El señuelo lo alcanzará en `host.docker.internal:11434`.
- **PostgreSQL no se publica en el anfitrión** dentro del esqueleto; solo lo usan los contenedores.
- **Contenedores sin privilegios** (usuario `umbra`, UID 10001) y puertos ligados a `127.0.0.1`.
- **Entorno de contención:** desde el sprint 7, según el ADR-001 (sprint 3).

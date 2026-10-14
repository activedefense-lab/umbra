# registro/ · Guía de desarrollo

Contenedor de **registro forense** (paso 6 del flujo). Versión mínima del sprint 1: esquema de sesiones y eventos, operaciones de escritura, consulta e informe en texto. El sprint 8 trae el esquema definitivo, la anonimización completa (Ley 1581 de 2012) y el informe de incidente.

## Estructura

```
registro/
  pyproject.toml           Paquete umbra-registro (psycopg 3)
  sql/001_esquema.sql      Tablas sesiones y eventos; idempotente; se aplica con `registro.cli esquema`
  src/registro/
    conexion.py            DSN por variable UMBRA_REGISTRO_DSN; aplicar_esquema()
    repositorio.py         abrir_sesion, registrar_evento, cerrar_sesion, obtener_sesion, eventos_de, listar_sesiones
    informe.py             informe_sesion(): cabecera + línea de tiempo por paso del flujo
    cli.py                 esquema | sesiones | informe <id> | demo
  tests/                   Integración contra PostgreSQL real; se omiten si no hay BD
```

## Modelo de datos

- `sesiones`: una por interacción del atacante. `origen_hash` es SHA-256 del origen; **la IP nunca se guarda en claro**. `intencion_final` se fija al cerrar.
- `eventos`: uno por acción de cualquier contenedor, con `paso` (1–8, el número del flujo C4), `tipo` y `detalle` JSONB. Cada contenedor escribe su propio evento con su número de paso.
- Marcas de tiempo con `clock_timestamp()` (instante real de inserción), no `now()` (instante de inicio de la transacción): un registro forense necesita el orden real.

## Entorno

```bash
# PostgreSQL de desarrollo (desde la raíz del repositorio)
docker compose -f infra/dev/compose.postgres.yml up -d

cd registro
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
python -m registro.cli esquema      # aplica sql/*.sql
pytest                              # 9 pruebas de integración
python -m registro.cli demo         # crea una sesión de ejemplo e imprime su informe
```

Variable de entorno `UMBRA_REGISTRO_DSN` para otro servidor; por defecto `postgresql://umbra:umbra_dev@127.0.0.1:5433/umbra_registro`.

## Uso desde otro contenedor

```python
from registro.conexion import conectar
from registro.repositorio import abrir_sesion, registrar_evento, cerrar_sesion

with conectar() as conn:
    sid = abrir_sesion(conn, origen=ip, ruta="/diagnostico/ping", parametro="host")
    registrar_evento(conn, sid, paso=3, tipo="veredicto", detalle=veredicto.model_dump())
    cerrar_sesion(conn, sid, intencion_final=veredicto.intencion)
```

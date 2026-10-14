"""Pruebas de integración contra PostgreSQL real.

Requiere el contenedor de desarrollo:
    docker compose -f infra/dev/compose.postgres.yml up -d
Si no hay base de datos alcanzable, las pruebas se omiten (skip), no fallan.
Cada prueba corre en una transacción que se revierte al final.
"""

import psycopg
import pytest

from registro.conexion import aplicar_esquema, conectar, dsn


@pytest.fixture(scope="session")
def _bd_disponible() -> None:
    try:
        with conectar() as conn:
            aplicar_esquema(conn)
    except psycopg.OperationalError as exc:
        pytest.skip(f"PostgreSQL no alcanzable en {dsn()}: {exc}")


@pytest.fixture
def conn(_bd_disponible):
    """Conexión con autocommit desactivado; todo se revierte al terminar la prueba.

    Las funciones del repositorio llaman conn.commit(); para que el rollback
    final funcione se envuelve cada prueba en un SAVEPOINT vía una conexión
    cuyo commit es inocuo (se reemplaza por un no-op).
    """
    c = conectar()
    c.autocommit = False
    commit_real = c.commit
    c.commit = lambda: None  # type: ignore[method-assign]
    try:
        yield c
    finally:
        c.commit = commit_real  # type: ignore[method-assign]
        c.rollback()
        c.close()

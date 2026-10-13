"""Conexión a PostgreSQL y aplicación del esquema."""

from __future__ import annotations

import os
from pathlib import Path

import psycopg

VARIABLE_DSN = "UMBRA_REGISTRO_DSN"
DSN_DESARROLLO = "postgresql://umbra:umbra_dev@127.0.0.1:5433/umbra_registro"
RUTA_SQL = Path(__file__).resolve().parents[2] / "sql"


def dsn() -> str:
    """DSN desde la variable de entorno; en su ausencia, el de desarrollo local."""
    return os.environ.get(VARIABLE_DSN, DSN_DESARROLLO)


def conectar(cadena: str | None = None) -> psycopg.Connection:
    return psycopg.connect(cadena or dsn())


def aplicar_esquema(conn: psycopg.Connection) -> list[str]:
    """Aplica en orden todos los sql/NNN_*.sql. Devuelve los nombres aplicados."""
    aplicados: list[str] = []
    for archivo in sorted(RUTA_SQL.glob("[0-9][0-9][0-9]_*.sql")):
        conn.execute(archivo.read_text(encoding="utf-8"))
        aplicados.append(archivo.name)
    conn.commit()
    return aplicados

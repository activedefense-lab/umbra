"""Operaciones del registro forense: sesiones y eventos."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb


def anonimizar_origen(origen: str, sal: str = "") -> str:
    """Hash SHA-256 del origen. Mínimo del sprint 1; la sal por despliegue y la
    política de retención se definen en el sprint 8 (Ley 1581 de 2012)."""
    return hashlib.sha256(f"{sal}{origen}".encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class Evento:
    id: int
    sesion_id: UUID
    paso: int
    tipo: str
    detalle: dict[str, Any]
    creado_en: datetime


@dataclass(frozen=True)
class Sesion:
    id: UUID
    origen_hash: str
    ruta: str
    parametro: str
    intencion_final: str | None
    inicio: datetime
    fin: datetime | None


def abrir_sesion(conn: psycopg.Connection, origen: str, ruta: str, parametro: str, sal: str = "") -> UUID:
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO sesiones (origen_hash, ruta, parametro) VALUES (%s, %s, %s) RETURNING id",
            (anonimizar_origen(origen, sal), ruta, parametro),
        )
        sesion_id = cur.fetchone()[0]
    conn.commit()
    return sesion_id


def registrar_evento(
    conn: psycopg.Connection, sesion_id: UUID, paso: int, tipo: str, detalle: dict[str, Any] | None = None
) -> int:
    if not 1 <= paso <= 8:
        raise ValueError(f"paso fuera del flujo de 8 pasos: {paso}")
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO eventos (sesion_id, paso, tipo, detalle) VALUES (%s, %s, %s, %s) RETURNING id",
            (sesion_id, paso, tipo, Jsonb(detalle or {})),
        )
        evento_id = cur.fetchone()[0]
    conn.commit()
    return evento_id


def cerrar_sesion(conn: psycopg.Connection, sesion_id: UUID, intencion_final: str | None = None) -> None:
    conn.execute(
        "UPDATE sesiones SET fin = clock_timestamp(), intencion_final = COALESCE(%s, intencion_final) WHERE id = %s",
        (intencion_final, sesion_id),
    )
    conn.commit()


def obtener_sesion(conn: psycopg.Connection, sesion_id: UUID) -> Sesion | None:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute("SELECT * FROM sesiones WHERE id = %s", (sesion_id,))
        fila = cur.fetchone()
    return Sesion(**fila) if fila else None


def eventos_de(conn: psycopg.Connection, sesion_id: UUID) -> list[Evento]:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            "SELECT * FROM eventos WHERE sesion_id = %s ORDER BY creado_en, id",
            (sesion_id,),
        )
        return [Evento(**f) for f in cur.fetchall()]


def listar_sesiones(conn: psycopg.Connection, limite: int = 50) -> list[Sesion]:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute("SELECT * FROM sesiones ORDER BY inicio DESC LIMIT %s", (limite,))
        return [Sesion(**f) for f in cur.fetchall()]

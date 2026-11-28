"""Orquestación de POST /interceptar (ADR-003 y sus precisiones de implementación).

El detector es el punto de entrada único: decide, pide la respuesta al
señuelo, registra la sesión forense y devuelve una `Decision`. El señuelo y el
registro se inyectan para poder probar la lógica sin Ollama ni PostgreSQL.

Unidades de los límites (revisión técnica externa, OBS-07):
- `MAX_CARACTERES_SENUELO` (4096) son caracteres Unicode: es el límite de
  `SolicitudSenuelo.valor_normalizado` en el contrato, y pydantic cuenta
  caracteres.
- `MAX_BYTES_REGISTRO` (65 536) son bytes UTF-8 del valor guardado en el
  evento del paso 2. El recorte nunca parte un carácter.
- El SHA-256 se calcula sobre la codificación UTF-8 de `Peticion.valor`
  completo, tal como lo recibió el detector (ya decodificado del JSON), no
  sobre la petición HTTP original de la aplicación objetivo.
"""

from __future__ import annotations

import hashlib
import math
import os
import time
from collections.abc import Callable, Iterator
from contextlib import AbstractContextManager, contextmanager
from typing import Any, Literal, Protocol
from uuid import UUID

import httpx
import psycopg
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from contrato.modelos import MAX_LONGITUD, SolicitudSenuelo
from registro import repositorio
from registro.conexion import dsn as dsn_por_defecto

MAX_CARACTERES_SENUELO = MAX_LONGITUD
MAX_BYTES_REGISTRO = 64 * 1024

URL_SENUELO_POR_DEFECTO = "http://127.0.0.1:8002"
TIMEOUT_SENUELO_POR_DEFECTO = 25.0
TIMEOUT_CONEXION_REGISTRO = 3  # segundos; libpq exige al menos 2
# Límite de cada sentencia en el servidor (incluye esperas por bloqueos).
# connect_timeout solo acota el establecimiento de la conexión.
TIMEOUT_SENTENCIA_REGISTRO_MS = 3000


# ------------------------------------------------------------------ modelos


class Decision(BaseModel):
    """Salida de /interceptar (ADR-003, decisión 3). Propia del núcleo."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    accion: Literal["permitir", "senuelo"]
    respuesta: str = ""
    sesion_id: UUID | None = None


class RespuestaGenerada(BaseModel):
    """Lo que el detector exige de la respuesta de POST /generar del señuelo."""

    respuesta: str = Field(min_length=1)
    modelo: str
    latencia_ms: float = Field(ge=0)
    # Opcional para no bloquear el engaño por un campo de trazabilidad;
    # el señuelo lo envía desde el PR #28 y queda registrado.
    temperatura: float | None = None


# ------------------------------------------------------------------- errores


class ErrorSenuelo(Exception):
    """El señuelo no respondió, respondió con error o con un cuerpo inválido."""


class ErrorRegistro(Exception):
    """El registro forense (PostgreSQL) no está disponible o falló una escritura."""


# ------------------------------------------------------------- configuración


def _segundos(variable: str, defecto: float) -> float:
    crudo = os.getenv(variable, "").strip()
    if not crudo:
        return defecto
    try:
        valor = float(crudo)
    except ValueError as error:
        raise ValueError(f"{variable} debe ser un número de segundos: {crudo!r}") from error
    if not math.isfinite(valor) or valor <= 0:
        raise ValueError(f"{variable} debe ser un número finito mayor que cero: {crudo!r}")
    return valor


# -------------------------------------------------------------------- señuelo

GeneradorSenuelo = Callable[[SolicitudSenuelo], RespuestaGenerada]


def cliente_senuelo(
    url: str | None = None,
    timeout: float | None = None,
    *,
    transporte: httpx.BaseTransport | None = None,
) -> GeneradorSenuelo:
    """Devuelve la función que pide una respuesta a POST {url}/generar.

    El tiempo de espera (UMBRA_SENUELO_TIMEOUT, 25 s) debe ser menor que el
    del middleware (30 s) y mayor que el del señuelo hacia Ollama (20 s).
    """

    base = (url or os.getenv("UMBRA_SENUELO_URL", URL_SENUELO_POR_DEFECTO)).rstrip("/")
    espera = timeout if timeout is not None else _segundos(
        "UMBRA_SENUELO_TIMEOUT", TIMEOUT_SENUELO_POR_DEFECTO
    )

    def generar(solicitud: SolicitudSenuelo) -> RespuestaGenerada:
        try:
            with httpx.Client(timeout=espera, transport=transporte) as cliente:
                respuesta = cliente.post(f"{base}/generar", json=solicitud.model_dump(mode="json"))
            respuesta.raise_for_status()
            return RespuestaGenerada.model_validate(respuesta.json())
        except httpx.TimeoutException as error:
            raise ErrorSenuelo(f"tiempo agotado ({espera:g} s)") from error
        except httpx.HTTPStatusError as error:
            raise ErrorSenuelo(f"HTTP {error.response.status_code}") from error
        except httpx.HTTPError as error:
            raise ErrorSenuelo(f"sin conexión: {type(error).__name__}") from error
        except (ValueError, ValidationError) as error:
            raise ErrorSenuelo("respuesta inválida") from error

    generar.timeout = espera  # type: ignore[attr-defined]  # visible en pruebas
    return generar


# ------------------------------------------------------------------- registro


class RegistroForense(Protocol):
    """Operaciones del registro que usa /interceptar dentro de una petición."""

    def abrir_sesion(self, origen: str, ruta: str, parametro: str) -> UUID: ...

    def registrar_evento(self, sesion_id: UUID, paso: int, tipo: str, detalle: dict[str, Any]) -> None: ...

    def cerrar_sesion(self, sesion_id: UUID, intencion: str) -> None: ...


AbridorRegistro = Callable[[], AbstractContextManager[RegistroForense]]


class _RegistroPostgres:
    """Adapta registro.repositorio a RegistroForense; todo error es ErrorRegistro."""

    def __init__(self, conn: psycopg.Connection) -> None:
        self._conn = conn

    def abrir_sesion(self, origen: str, ruta: str, parametro: str) -> UUID:
        try:
            return repositorio.abrir_sesion(self._conn, origen, ruta, parametro)
        except psycopg.Error as error:
            raise ErrorRegistro("no se pudo abrir la sesión") from error

    def registrar_evento(self, sesion_id: UUID, paso: int, tipo: str, detalle: dict[str, Any]) -> None:
        try:
            repositorio.registrar_evento(self._conn, sesion_id, paso, tipo, detalle)
        except psycopg.Error as error:
            raise ErrorRegistro(f"no se pudo registrar el evento {tipo}") from error

    def cerrar_sesion(self, sesion_id: UUID, intencion: str) -> None:
        try:
            repositorio.cerrar_sesion(self._conn, sesion_id, intencion)
        except psycopg.Error as error:
            raise ErrorRegistro("no se pudo cerrar la sesión") from error


def registro_postgres(dsn: str | None = None) -> AbridorRegistro:
    """Una conexión por interceptación: si PostgreSQL cae y vuelve, el detector
    se recupera sin reiniciarse. El pool de conexiones queda para cuando haya
    carga que lo justifique."""

    cadena = dsn or os.getenv("UMBRA_REGISTRO_DSN") or dsn_por_defecto()

    @contextmanager
    def abrir() -> Iterator[RegistroForense]:
        try:
            conn = psycopg.connect(
                cadena,
                connect_timeout=TIMEOUT_CONEXION_REGISTRO,
                options=f"-c statement_timeout={TIMEOUT_SENTENCIA_REGISTRO_MS}",
            )
        except psycopg.Error as error:
            raise ErrorRegistro("PostgreSQL no disponible") from error
        try:
            yield _RegistroPostgres(conn)
        finally:
            conn.close()

    return abrir


# ------------------------------------------------------- evidencia y límites


def recortar_caracteres(texto: str, maximo: int) -> tuple[str, bool]:
    if len(texto) <= maximo:
        return texto, False
    return texto[:maximo], True


def recortar_bytes(texto: str, maximo: int) -> tuple[str, bool]:
    """Recorta a `maximo` bytes UTF-8 sin partir un carácter."""
    codificado = texto.encode("utf-8")
    if len(codificado) <= maximo:
        return texto, False
    return codificado[:maximo].decode("utf-8", errors="ignore"), True


def evidencia_de_la_carga(valor: str) -> dict[str, Any]:
    """Detalle del evento del paso 2. Si el valor se recorta, el hash y las
    longitudes permiten verificar la carga completa, pero no la sustituyen."""
    codificado = valor.encode("utf-8")
    guardado, truncado = recortar_bytes(valor, MAX_BYTES_REGISTRO)
    return {
        "valor": guardado,
        "valor_truncado": truncado,
        "longitud_caracteres": len(valor),
        "longitud_bytes": len(codificado),
        "sha256": hashlib.sha256(codificado).hexdigest(),
    }

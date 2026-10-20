"""API HTTP del generador de señuelo (núcleo; ADR-002).

El señuelo utiliza el complemento activo para construir el contexto
de simulación y el contrato compartido para componer las instrucciones.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from fastapi import FastAPI, HTTPException

from contrato.cargador import cargar_activo, listar
from contrato.composicion import Instrucciones, componer
from contrato.interfaz import (
    Complemento,
    validar_complemento,
    verificar_contexto,
)
from contrato.modelos import INTENCION_DESCONOCIDA, SolicitudSenuelo

from .modelos import RespuestaSenuelo
from .ollama import ErrorOllama, generar


VERSION = "0.1.0"


def crear_app(
    complemento: Complemento | None = None,
    generador: Callable[[Instrucciones], RespuestaSenuelo] = generar,
) -> FastAPI:
    """Construye la API utilizando el complemento activo."""

    activo = (
        cargar_activo()
        if complemento is None
        else validar_complemento(complemento)
    )

    app = FastAPI(
        title="Umbra · Generador de señuelo",
        version=VERSION,
    )

    @app.get("/salud")
    def salud() -> dict[str, Any]:
        return {
            "estado": "ok",
            "version": VERSION,
            "complemento": {
                "nombre": activo.nombre,
                "cwe": activo.cwe,
            },
            "instalados": [
                {
                    "nombre": instalado.nombre,
                    "paquete": instalado.paquete,
                    "version": instalado.version,
                }
                for instalado in listar()
            ],
        }

    @app.post("/generar", response_model=RespuestaSenuelo)
    def generar_respuesta(
        solicitud: SolicitudSenuelo,
    ) -> RespuestaSenuelo:

        if solicitud.complemento != activo.nombre:
            raise HTTPException(
                status_code=422,
                detail=(
                    f"la solicitud es para {solicitud.complemento!r}; "
                    f"el complemento activo es {activo.nombre!r}"
                ),
            )

        if (
            solicitud.intencion != INTENCION_DESCONOCIDA
            and solicitud.intencion not in activo.intenciones
        ):
            raise HTTPException(
                status_code=422,
                detail=(
                    f"la intención {solicitud.intencion!r} no pertenece "
                    f"al catálogo de {activo.nombre!r}"
                ),
            )

        contexto = verificar_contexto(
            activo,
            activo.contexto_senuelo(solicitud),
        )

        instrucciones = componer(contexto)

        try:
            return generador(instrucciones)
        except ErrorOllama as error:
            raise HTTPException(
                status_code=503,
                detail="Generador de señuelo no disponible",
            ) from error

    return app
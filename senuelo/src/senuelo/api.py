"""API HTTP del generador de señuelo de Umbra."""

from __future__ import annotations

from collections.abc import Callable

from fastapi import FastAPI, HTTPException

from .modelos import RespuestaSenuelo, SolicitudSenuelo
from .ollama import ErrorOllama, generar


def crear_app(
    generador: Callable[[SolicitudSenuelo], RespuestaSenuelo] = generar,
) -> FastAPI:
    """Construye la API y permite sustituir el generador en pruebas."""

    app = FastAPI(
        title="Umbra · Generador de señuelo",
        version="0.1.0",
    )

    @app.get("/salud")
    def salud() -> dict[str, str]:
        return {"estado": "ok", "version": "0.1.0"}

    @app.post("/generar", response_model=RespuestaSenuelo)
    def generar_respuesta(
        solicitud: SolicitudSenuelo,
    ) -> RespuestaSenuelo:
        try:
            return generador(solicitud)
        except ErrorOllama as error:
            raise HTTPException(
                status_code=503,
                detail="Generador de señuelo no disponible",
            ) from error

    return app


app = crear_app()

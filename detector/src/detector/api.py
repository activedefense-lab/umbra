
"""API HTTP del contenedor de detección e inferencia (ADR-002).

El detector delega el análisis en el complemento activo y verifica
su resultado antes de devolverlo.

Arranque mediante fábrica:
    uvicorn --factory detector.api:crear_app
"""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI

from contrato.cargador import cargar_activo, listar
from contrato.interfaz import (
    Complemento,
    validar_complemento,
    verificar_resultado,
)
from contrato.modelos import Peticion, Veredicto

from . import __version__


def crear_app(complemento: Complemento | None = None) -> FastAPI:
    """Crea la API con el complemento configurado o uno inyectado.

    Sin argumento, carga el complemento indicado por UMBRA_COMPLEMENTO.
    Los complementos inyectados también se validan.
    """
    activo = (
        cargar_activo()
        if complemento is None
        else validar_complemento(complemento)
    )

    app = FastAPI(
        title="Umbra · Detector",
        version=__version__,
    )

    @app.get("/salud")
    def salud() -> dict[str, Any]:
        return {
            "estado": "ok",
            "version": __version__,
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

    @app.post("/analizar", response_model=Veredicto)
    def analizar_peticion(peticion: Peticion) -> Veredicto:
        veredicto = activo.analizar(peticion)
        return verificar_resultado(activo, veredicto)

    return app

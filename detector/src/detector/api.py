"""API HTTP del contenedor de detección e inferencia."""

from __future__ import annotations

from fastapi import FastAPI

from . import __version__
from .modelos import Peticion, Veredicto
from .reglas import Catalogo, analizar


def crear_app(catalogo: Catalogo | None = None) -> FastAPI:
    """Fábrica de la aplicación; permite inyectar un catálogo en pruebas."""
    cat = catalogo or Catalogo.desde_archivo()
    app = FastAPI(title="Umbra · Detector", version=__version__)

    @app.get("/salud")
    def salud() -> dict[str, str]:
        return {"estado": "ok", "version": __version__, "catalogo": cat.nombre}

    @app.post("/analizar", response_model=Veredicto)
    def analizar_peticion(peticion: Peticion) -> Veredicto:
        return analizar(peticion, cat)

    return app


app = crear_app()

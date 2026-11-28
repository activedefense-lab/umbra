"""API HTTP del generador de señuelo (núcleo; ADR-002).

El señuelo utiliza el complemento activo para construir el contexto
de simulación y el contrato compartido para componer las instrucciones.

Disponibilidad (umbra#15):
- GET /salud: el proceso vive (liveness). No consulta a Ollama; lo usa el
  healthcheck de Docker.
- GET /listo: el generador puede responder ya (readiness). Consulta en cada
  llamada si Ollama responde y si el modelo está cargado en memoria.
- Al arrancar, un calentamiento en segundo plano carga el modelo con una
  generación mínima. Nunca bloquea ni impide el arranque.
"""

from __future__ import annotations

import logging
import threading
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse

from contrato.cargador import cargar_activo, listar
from contrato.composicion import Instrucciones, componer
from contrato.interfaz import (
    Complemento,
    validar_complemento,
    verificar_contexto,
)
from contrato.modelos import INTENCION_DESCONOCIDA, SolicitudSenuelo

from .modelos import RespuestaSenuelo
from .ollama import Configuracion, ErrorOllama, calentar, generar, modelo_cargado


VERSION = "0.1.0"

# Logger de uvicorn: sus mensajes aparecen en `docker compose logs senuelo`.
registro_log = logging.getLogger("uvicorn.error")


class EstadoCalentamiento:
    """Estado del calentamiento, compartido entre el hilo y las peticiones."""

    PENDIENTE = "pendiente"
    EN_CURSO = "en_curso"
    COMPLETADO = "completado"
    FALLIDO = "fallido"

    def __init__(self) -> None:
        self._candado = threading.Lock()
        self._estado = self.PENDIENTE
        self._detalle: str | None = None

    def marcar(self, estado: str, detalle: str | None = None) -> None:
        with self._candado:
            self._estado = estado
            self._detalle = detalle

    def instantanea(self) -> dict[str, Any]:
        with self._candado:
            return {"estado": self._estado, "detalle": self._detalle}


def ejecutar_calentamiento(
    estado: EstadoCalentamiento,
    calentador: Callable[[], float],
) -> None:
    """Calienta el modelo y deja el resultado en `estado`. No lanza excepciones."""

    estado.marcar(EstadoCalentamiento.EN_CURSO)
    try:
        duracion_ms = calentador()
    except ErrorOllama as error:
        estado.marcar(EstadoCalentamiento.FALLIDO, str(error))
        registro_log.warning(
            "Calentamiento del modelo fallido: %s. El señuelo responderá 503 "
            "hasta que Ollama esté disponible; /listo informa el estado.",
            error,
        )
    except Exception as error:  # el hilo nunca debe morir en silencio
        estado.marcar(EstadoCalentamiento.FALLIDO, f"error inesperado: {error!r}")
        registro_log.exception("Error inesperado durante el calentamiento del modelo")
    else:
        estado.marcar(EstadoCalentamiento.COMPLETADO, f"{duracion_ms:.0f} ms")
        registro_log.info("Modelo calentado en %.0f ms", duracion_ms)


def crear_app(
    complemento: Complemento | None = None,
    generador: Callable[[Instrucciones], RespuestaSenuelo] = generar,
    *,
    calentador: Callable[[], float] | None = calentar,
    consultor: Callable[[], bool] = modelo_cargado,
) -> FastAPI:
    """Construye la API utilizando el complemento activo.

    `calentador=None` desactiva el calentamiento al arrancar.
    """

    # Configuración inválida (p. ej. OLLAMA_TIMEOUT=abc): fallar al arrancar.
    configuracion = Configuracion.desde_entorno()

    activo = (
        cargar_activo()
        if complemento is None
        else validar_complemento(complemento)
    )

    estado = EstadoCalentamiento()

    @asynccontextmanager
    async def ciclo_de_vida(_: FastAPI) -> AsyncIterator[None]:
        if calentador is not None:
            threading.Thread(
                target=ejecutar_calentamiento,
                args=(estado, calentador),
                name="calentamiento-ollama",
                daemon=True,
            ).start()
        yield

    app = FastAPI(
        title="Umbra · Generador de señuelo",
        version=VERSION,
        lifespan=ciclo_de_vida,
    )
    app.state.calentamiento = estado

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

    @app.get("/listo")
    def listo() -> JSONResponse:
        cuerpo: dict[str, Any] = {
            "listo": False,
            "modelo": configuracion.modelo,
            "calentamiento": estado.instantanea(),
        }

        if cuerpo["calentamiento"]["estado"] == EstadoCalentamiento.EN_CURSO:
            cuerpo["motivo"] = "calentamiento en curso"
            return JSONResponse(cuerpo, status_code=503)

        try:
            cargado = consultor()
        except ErrorOllama:
            cuerpo["motivo"] = "Ollama no disponible"
            return JSONResponse(cuerpo, status_code=503)

        if not cargado:
            cuerpo["motivo"] = "modelo no cargado en memoria"
            return JSONResponse(cuerpo, status_code=503)

        cuerpo["listo"] = True
        return JSONResponse(cuerpo, status_code=200)

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

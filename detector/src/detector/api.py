
"""API HTTP del contenedor de detección e inferencia (ADR-002 y ADR-003).

El detector delega el análisis en el complemento activo y verifica
su resultado antes de devolverlo.

- POST /analizar: solo el veredicto (CI y experimento de ablación). Sin cambios.
- POST /interceptar: punto de entrada único de la aplicación objetivo
  (ADR-003). Decide, pide la respuesta al señuelo, registra la sesión
  forense y devuelve una Decision. Fallo cerrado: si el señuelo o el
  registro fallan, 503; nunca se degrada a "permitir".

Arranque mediante fábrica:
    uvicorn --factory detector.api:crear_app
"""

from __future__ import annotations

import logging
import time
from typing import Any

from fastapi import FastAPI, HTTPException

from contrato.cargador import cargar_activo, listar
from contrato.interfaz import (
    Complemento,
    validar_complemento,
    verificar_resultado,
)
from contrato.modelos import Peticion, SolicitudSenuelo, Veredicto

from . import __version__
from .interceptacion import (
    MAX_CARACTERES_SENUELO,
    AbridorRegistro,
    Decision,
    ErrorRegistro,
    ErrorSenuelo,
    GeneradorSenuelo,
    cliente_senuelo,
    evidencia_de_la_carga,
    recortar_caracteres,
    registro_postgres,
)

# Logger de uvicorn: sus mensajes aparecen en `docker compose logs detector`.
registro_log = logging.getLogger("uvicorn.error")

BLOQUEO = "Framework no disponible; petición bloqueada (fallo cerrado)."


def crear_app(
    complemento: Complemento | None = None,
    *,
    generar_senuelo: GeneradorSenuelo | None = None,
    abrir_registro: AbridorRegistro | None = None,
) -> FastAPI:
    """Crea la API con el complemento configurado o uno inyectado.

    Sin argumento, carga el complemento indicado por UMBRA_COMPLEMENTO.
    Los complementos inyectados también se validan. El señuelo y el
    registro se construyen desde el entorno si no se inyectan; no se
    conectan al arrancar.
    """
    activo = (
        cargar_activo()
        if complemento is None
        else validar_complemento(complemento)
    )
    generar_senuelo = generar_senuelo or cliente_senuelo()
    abrir_registro = abrir_registro or registro_postgres()

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

    @app.post("/interceptar", response_model=Decision)
    def interceptar(peticion: Peticion) -> Decision:
        # El complemento analiza la carga completa: el recorte para el
        # señuelo ocurre después y no afecta la detección.
        veredicto = verificar_resultado(activo, activo.analizar(peticion))

        if not veredicto.es_ataque:
            return Decision(accion="permitir")

        valor_senuelo, truncado_senuelo = recortar_caracteres(
            veredicto.valor_normalizado, MAX_CARACTERES_SENUELO
        )
        # Se construye antes de abrir la sesión: con un Veredicto validado no
        # puede fallar (sus campos ya cumplen los tipos del contrato), pero si un
        # complemento defectuoso lo creara sin validar (model_construct), el
        # error ocurre sin efectos: ni sesión a medias ni llamada al señuelo.
        solicitud = SolicitudSenuelo(
            complemento=veredicto.complemento,
            intencion=veredicto.intencion,
            valor_normalizado=valor_senuelo,
            evidencia=veredicto.evidencia,
        )

        try:
            with abrir_registro() as registro:
                sesion_id = registro.abrir_sesion(peticion.origen, peticion.ruta, peticion.parametro)
                registro.registrar_evento(
                    sesion_id, 2, "peticion_recibida",
                    {"ruta": peticion.ruta, "parametro": peticion.parametro,
                     **evidencia_de_la_carga(peticion.valor)},
                )
                registro.registrar_evento(
                    sesion_id, 3, "veredicto",
                    {"complemento": veredicto.complemento, "intencion": veredicto.intencion,
                     "confianza": veredicto.confianza, "evidencia": veredicto.evidencia,
                     "valor_senuelo_truncado": truncado_senuelo},
                )

                inicio = time.perf_counter()
                try:
                    generada = generar_senuelo(solicitud)
                except ErrorSenuelo as error:
                    # La sesión fallida también es evidencia: se registra y se cierra.
                    registro.registrar_evento(
                        sesion_id, 4, "error_senuelo",
                        {"motivo": str(error),
                         "duracion_ms": (time.perf_counter() - inicio) * 1000},
                    )
                    registro.cerrar_sesion(sesion_id, veredicto.intencion)
                    registro_log.warning("Señuelo no disponible (%s); sesión %s bloqueada con 503", error, sesion_id)
                    raise HTTPException(status_code=503, detail=BLOQUEO) from error

                registro.registrar_evento(
                    sesion_id, 4, "respuesta_senuelo",
                    {"respuesta": generada.respuesta, "modelo": generada.modelo,
                     "temperatura": generada.temperatura, "latencia_ms": generada.latencia_ms,
                     "duracion_ms": (time.perf_counter() - inicio) * 1000},
                )
                registro.cerrar_sesion(sesion_id, veredicto.intencion)
        except ErrorRegistro as error:
            # Puede quedar una sesión incompleta (sin cierre): no se puede
            # cerrar si el propio registro falla. Queda en el log del contenedor.
            registro_log.error("Registro forense no disponible (%s); petición bloqueada con 503", error)
            raise HTTPException(status_code=503, detail=BLOQUEO) from error

        return Decision(accion="senuelo", respuesta=generada.respuesta, sesion_id=sesion_id)

    return app

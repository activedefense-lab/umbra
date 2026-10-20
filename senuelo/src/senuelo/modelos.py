"""Modelos propios del generador de señuelo.

La solicitud de entrada pertenece al contrato compartido de Umbra.
Aquí permanece únicamente el modelo de respuesta del servicio.
"""

from pydantic import BaseModel, Field


class RespuestaSenuelo(BaseModel):
    """Respuesta ficticia generada por el modelo de lenguaje."""

    respuesta: str
    modelo: str
    latencia_ms: float = Field(ge=0)
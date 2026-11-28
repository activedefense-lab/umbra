"""Modelos propios del generador de señuelo.

La solicitud de entrada pertenece al contrato compartido de Umbra.
Aquí permanece únicamente el modelo de respuesta del servicio.
"""

from pydantic import BaseModel, Field


class RespuestaSenuelo(BaseModel):
    """Respuesta ficticia generada por el modelo de lenguaje.

    `modelo` y `temperatura` son los parámetros realmente enviados a Ollama;
    el registro forense los conserva para reproducir la generación.
    """

    respuesta: str
    modelo: str
    latencia_ms: float = Field(ge=0)
    temperatura: float = Field(ge=0)

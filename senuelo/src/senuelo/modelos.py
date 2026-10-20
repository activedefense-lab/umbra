"""Contratos de entrada y salida del generador de señuelo."""

from enum import StrEnum

from typing import Annotated

from pydantic import BaseModel, Field, StringConstraints


class Intencion(StrEnum):
    """Intenciones compatibles con el contrato del detector."""

    RECONOCIMIENTO = "reconocimiento"
    DESCARGA = "descarga_herramientas"
    PERSISTENCIA = "persistencia"
    EXFILTRACION = "exfiltracion"
    MOVIMIENTO_LATERAL = "movimiento_lateral"
    DESCONOCIDA = "desconocida"


class SolicitudSenuelo(BaseModel):
    """Contexto del ataque previamente analizado por el detector."""

    intencion: Intencion
    segmentos: list[Annotated[str, StringConstraints(max_length=4096)]] = Field(max_length=20)
    valor_normalizado: str = Field(max_length=4096)


class RespuestaSenuelo(BaseModel):
    """Respuesta ficticia generada por Ollama."""

    respuesta: str
    modelo: str
    latencia_ms: float = Field(ge=0)

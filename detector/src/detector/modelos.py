"""Modelos de entrada y salida del servicio de detección."""

from enum import StrEnum

from pydantic import BaseModel, Field


class Intencion(StrEnum):
    """Catálogo de intenciones del anteproyecto (sección 6.1.5).

    `DESCONOCIDA` se usa cuando hay inyección pero ninguna regla de intención
    coincide; el clasificador del sprint 5 reemplaza este valor.
    """

    RECONOCIMIENTO = "reconocimiento"
    DESCARGA = "descarga_herramientas"
    PERSISTENCIA = "persistencia"
    EXFILTRACION = "exfiltracion"
    MOVIMIENTO_LATERAL = "movimiento_lateral"
    DESCONOCIDA = "desconocida"


class Peticion(BaseModel):
    """Petición derivada por el middleware de la aplicación objetivo."""

    origen: str = Field(description="Identificador del origen (p. ej. IP ya anonimizada por la aplicación)")
    ruta: str = Field(description="Ruta HTTP atacada, p. ej. /diagnostico/ping")
    parametro: str = Field(description="Nombre del parámetro donde llegó la carga útil")
    valor: str = Field(description="Valor crudo del parámetro, tal como llegó")


class Veredicto(BaseModel):
    """Resultado del análisis de una petición."""

    es_ataque: bool
    metacaracteres: list[str] = Field(default_factory=list, description="Metacaracteres de intérprete encontrados")
    segmentos: list[str] = Field(default_factory=list, description="Comandos inyectados, separados y limpios")
    intencion: Intencion = Intencion.DESCONOCIDA
    confianza: float = Field(ge=0.0, le=1.0, default=0.0)
    coincidencias: dict[str, list[str]] = Field(
        default_factory=dict,
        description="Por intención, las palabras clave que coincidieron (trazabilidad del veredicto)",
    )
    valor_normalizado: str = Field(default="", description="Valor tras decodificar URL y normalizar espacios")

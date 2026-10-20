"""Modelos que cruzan la frontera núcleo–complemento (ADR-002, decisión 2).

Cada modelo valida lo que depende solo de sí mismo. Lo que depende del
complemento activo (que el veredicto provenga de él y que su intención
pertenezca a su catálogo) lo valida el núcleo, no estos modelos.
"""

from typing import Annotated, Self

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

MAX_CLAVES = 20
MAX_ELEMENTOS = 20
MAX_LONGITUD = 4096
INTENCION_DESCONOCIDA = "desconocida"

Identificador = Annotated[
    str,
    StringConstraints(min_length=1, max_length=64, pattern=r"^[a-z][a-z0-9_]*$"),
]
TextoLimitado = Annotated[str, StringConstraints(max_length=MAX_LONGITUD)]
Evidencia = Annotated[
    dict[Identificador, Annotated[list[TextoLimitado], Field(max_length=MAX_ELEMENTOS)]],
    Field(max_length=MAX_CLAVES),
]


class _Modelo(BaseModel):
    """Base común: inmutable y sin campos desconocidos."""

    model_config = ConfigDict(extra="forbid", frozen=True)


class Peticion(_Modelo):
    """Petición derivada por el middleware de la aplicación objetivo."""

    origen: str = Field(description="Identificador del origen (p. ej. IP ya anonimizada por la aplicación)")
    ruta: str = Field(description="Ruta HTTP atacada, p. ej. /diagnostico/ping")
    parametro: str = Field(description="Nombre del parámetro donde llegó la carga útil")
    valor: str = Field(description="Valor crudo del parámetro, tal como llegó")


class Veredicto(_Modelo):
    """Resultado del análisis de una petición por un complemento."""

    complemento: Identificador
    es_ataque: bool
    intencion: Identificador = INTENCION_DESCONOCIDA
    confianza: float = Field(default=0.0, ge=0.0, le=1.0)
    valor_normalizado: str = ""
    evidencia: Evidencia = Field(default_factory=dict)

    @model_validator(mode="after")
    def _sin_ataque_es_neutro(self) -> Self:
        if not self.es_ataque:
            if self.intencion != INTENCION_DESCONOCIDA:
                raise ValueError("un veredicto sin ataque debe tener intención 'desconocida'")
            if self.confianza != 0.0:
                raise ValueError("un veredicto sin ataque debe tener confianza 0")
            if self.evidencia:
                raise ValueError("un veredicto sin ataque no puede contener evidencia")
        return self


class SolicitudSenuelo(_Modelo):
    """Datos que el señuelo recibe sobre un ataque ya analizado."""

    complemento: Identificador
    intencion: Identificador = INTENCION_DESCONOCIDA
    valor_normalizado: TextoLimitado = ""
    evidencia: Evidencia = Field(default_factory=dict)


class ContextoSenuelo(_Modelo):
    """Contexto que aporta el complemento: simulación fija y datos no confiables, separados."""

    simulacion: str = Field(min_length=1)
    datos: Annotated[dict[Identificador, TextoLimitado], Field(max_length=MAX_CLAVES)] = Field(
        default_factory=dict
    )
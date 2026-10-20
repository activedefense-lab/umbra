"""Interfaz que implementa cada complemento (ADR-002, decisiones 2 y 3).

El Protocol declara qué debe tener un complemento; validar_complemento comprueba
que lo que tiene es válido, porque isinstance con un Protocol solo verifica que
los atributos existen. verificar_resultado es la capa del núcleo de los
invariantes: lo que depende del complemento activo, no del modelo.
"""

import inspect
import re
from typing import Protocol, runtime_checkable

from pydantic import TypeAdapter, ValidationError

from .errores import ComplementoInvalido, ResultadoInvalido, VersionIncompatible
from .modelos import (
    INTENCION_DESCONOCIDA,
    ContextoSenuelo,
    Identificador,
    Peticion,
    SolicitudSenuelo,
    Veredicto,
)

VERSION_CONTRATO = 0

_identificador = TypeAdapter(Identificador)
_PATRON_CWE = re.compile(r"CWE-[1-9][0-9]*")


@runtime_checkable
class Complemento(Protocol):
    """Lo que el núcleo exige a un complemento."""

    nombre: str
    cwe: str
    version_contrato: int
    intenciones: frozenset[str]

    def analizar(self, peticion: Peticion) -> Veredicto: ...

    def contexto_senuelo(self, solicitud: SolicitudSenuelo) -> ContextoSenuelo: ...


def _es_identificador(valor: object) -> bool:
    try:
        _identificador.validate_python(valor)
    except ValidationError:
        return False
    return True


def _acepta_un_argumento(funcion: object) -> bool:
    """Comprueba que el método puede recibir un argumento (no que reciba exactamente uno).

    Los tipos y la firma completa son contrato estático (mypy, pyright).
    """
    if not callable(funcion):
        return False
    try:
        inspect.signature(funcion).bind(object())
    except (TypeError, ValueError):
        return False
    return True


def validar_complemento(objeto: object) -> Complemento:
    """Devuelve el complemento si cumple el contrato; si no, el error específico."""
    if not isinstance(objeto, Complemento):
        raise ComplementoInvalido(f"{objeto!r} no implementa la interfaz Complemento")
    if type(objeto.version_contrato) is not int or objeto.version_contrato != VERSION_CONTRATO:
        raise VersionIncompatible(
            f"el complemento declara la versión de contrato {objeto.version_contrato!r}; "
            f"el núcleo exige {VERSION_CONTRATO}"
        )
    if not _es_identificador(objeto.nombre):
        raise ComplementoInvalido(f"nombre de complemento inválido: {objeto.nombre!r}")
    if not isinstance(objeto.cwe, str) or not _PATRON_CWE.fullmatch(objeto.cwe):
        raise ComplementoInvalido(f"cwe inválido en {objeto.nombre!r}: {objeto.cwe!r}")
    if not isinstance(objeto.intenciones, frozenset) or not objeto.intenciones:
        raise ComplementoInvalido(f"{objeto.nombre!r} debe declarar un frozenset no vacío de intenciones")
    for intencion in objeto.intenciones:
        if not _es_identificador(intencion):
            raise ComplementoInvalido(f"intención inválida en {objeto.nombre!r}: {intencion!r}")
        if intencion == INTENCION_DESCONOCIDA:
            raise ComplementoInvalido(
                f"{objeto.nombre!r} no puede declarar la intención reservada {INTENCION_DESCONOCIDA!r}"
            )
    for metodo in ("analizar", "contexto_senuelo"):
        if not _acepta_un_argumento(getattr(objeto, metodo)):
            raise ComplementoInvalido(f"{objeto.nombre!r}: {metodo} debe poder recibir un argumento")
    return objeto


def verificar_resultado(complemento: Complemento, veredicto: object) -> Veredicto:
    """Capa del núcleo: el veredicto viene del complemento activo y su intención es suya."""
    if not isinstance(veredicto, Veredicto):
        raise ResultadoInvalido(f"{complemento.nombre!r} devolvió {type(veredicto).__name__}, no un Veredicto")
    if veredicto.complemento != complemento.nombre:
        raise ResultadoInvalido(
            f"veredicto atribuido a {veredicto.complemento!r}; el complemento activo es {complemento.nombre!r}"
        )
    if veredicto.intencion != INTENCION_DESCONOCIDA and veredicto.intencion not in complemento.intenciones:
        raise ResultadoInvalido(
            f"la intención {veredicto.intencion!r} no pertenece al catálogo de {complemento.nombre!r}"
        )
    return veredicto
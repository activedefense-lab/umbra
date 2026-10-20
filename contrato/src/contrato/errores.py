"""Errores del contrato de complementos (ADR-002, decisión 5).

Todos heredan de ErrorComplemento para que un servicio pueda capturarlos juntos
y, a la vez, las pruebas puedan distinguir cada causa.
"""


class ErrorComplemento(Exception):
    """Base de los errores del contrato."""


class ComplementoNoEncontrado(ErrorComplemento):
    """No hay ningún complemento instalado con ese nombre."""


class ComplementoDuplicado(ErrorComplemento):
    """Más de un paquete registra un complemento con el mismo nombre."""


class VersionIncompatible(ErrorComplemento):
    """El complemento declara una versión de contrato distinta a la del núcleo."""


class ComplementoInvalido(ErrorComplemento):
    """El objeto no cumple la interfaz o sus datos de identidad son inválidos."""


class ResultadoInvalido(ErrorComplemento):
    """Un complemento devolvió un resultado que el núcleo no puede propagar."""
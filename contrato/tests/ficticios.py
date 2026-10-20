
"""Complementos ficticios para las pruebas del cargador.

No contiene pruebas ejecutables directamente por pytest.
"""

from contrato.interfaz import VERSION_CONTRATO
from contrato.modelos import ContextoSenuelo, Veredicto


class Ficticio:
    """Implementación válida del contrato."""

    nombre = "ficticio"
    cwe = "CWE-1"
    version_contrato = VERSION_CONTRATO
    intenciones = frozenset({"intencion_a"})

    def analizar(self, peticion):
        return Veredicto(complemento=self.nombre, es_ataque=False)

    def contexto_senuelo(self, solicitud):
        return ContextoSenuelo(simulacion="sistema ficticio")


class OtroFicticio(Ficticio):
    """Segunda implementación para comprobar registros duplicados."""


class VersionFutura(Ficticio):
    """Complemento que declara una versión incompatible."""

    version_contrato = VERSION_CONTRATO + 1


class SinMetodos:
    """Complemento incompleto: no implementa los métodos exigidos."""

    nombre = "ficticio"
    cwe = "CWE-1"
    version_contrato = VERSION_CONTRATO
    intenciones = frozenset({"intencion_a"})


class FallaAlCrear(Ficticio):
    """Complemento cuya construcción produce una excepción."""

    def __init__(self):
        raise RuntimeError("fallo al construir el complemento")


NO_INVOCABLE = "un texto, no una fábrica"

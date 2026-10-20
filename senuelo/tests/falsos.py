"""Complementos falsos para probar el señuelo sin depender de ninguna CWE."""

from contrato.interfaz import VERSION_CONTRATO
from contrato.modelos import ContextoSenuelo, Veredicto


class Falso:
    nombre = "falso"
    cwe = "CWE-1"
    version_contrato = VERSION_CONTRATO
    intenciones = frozenset({"intencion_a"})

    def analizar(self, peticion):
        return Veredicto(complemento=self.nombre, es_ataque=False)

    def contexto_senuelo(self, solicitud):
        return ContextoSenuelo(
            simulacion="simulación falsa",
            datos={"valor_normalizado": solicitud.valor_normalizado},
        )


class ContextoInvalido(Falso):
    """Complemento que devuelve un contexto de tipo incorrecto."""

    def contexto_senuelo(self, solicitud):
        return "no es un contexto"
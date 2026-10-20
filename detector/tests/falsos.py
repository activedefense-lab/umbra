
"""Complementos falsos para probar el detector sin depender de ninguna CWE."""

from contrato.interfaz import VERSION_CONTRATO
from contrato.modelos import ContextoSenuelo, Veredicto


class Falso:
    """Complemento válido con una intención de prueba."""

    nombre = "falso"
    cwe = "CWE-1"
    version_contrato = VERSION_CONTRATO
    intenciones = frozenset({"intencion_a"})

    def analizar(self, peticion):
        if ";" not in peticion.valor:
            return Veredicto(
                complemento=self.nombre,
                es_ataque=False,
                valor_normalizado=peticion.valor,
            )

        return Veredicto(
            complemento=self.nombre,
            es_ataque=True,
            intencion="intencion_a",
            confianza=1.0,
            valor_normalizado=peticion.valor,
            evidencia={"pistas": [";"]},
        )

    def contexto_senuelo(self, solicitud):
        return ContextoSenuelo(
            simulacion="simulación falsa",
        )


class Suplantador(Falso):
    """Devuelve un veredicto atribuido a otro complemento."""

    def analizar(self, peticion):
        return Veredicto(
            complemento="otro",
            es_ataque=False,
        )


class IntencionAjena(Falso):
    """Devuelve una intención que no pertenece a su catálogo."""

    def analizar(self, peticion):
        return Veredicto(
            complemento=self.nombre,
            es_ataque=True,
            intencion="intencion_ajena",
            confianza=0.5,
        )

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


class FormaCWE79:
    """Complemento ficticio con la forma de CWE-79 (ADR-002, criterio 2).

    No detecta XSS: demuestra que el núcleo acepta un complemento cuyas
    intenciones, evidencia y simulación no dependen de inyección de comandos.
    """

    nombre = "forma_cwe79"
    cwe = "CWE-79"
    version_contrato = VERSION_CONTRATO
    intenciones = frozenset({"robo_de_sesion", "desfiguracion"})

    def analizar(self, peticion):
        # Condición artificial: solo se prueba la forma del contrato.
        if "<" not in peticion.valor:
            return Veredicto(
                complemento=self.nombre,
                es_ataque=False,
                valor_normalizado=peticion.valor,
            )

        return Veredicto(
            complemento=self.nombre,
            es_ataque=True,
            intencion="desfiguracion",
            confianza=0.5,
            valor_normalizado=peticion.valor,
            evidencia={
                "contexto_html": ["cuerpo"],
                "etiquetas": ["marca_ficticia"],
            },
        )

    def contexto_senuelo(self, solicitud):
        return ContextoSenuelo(
            simulacion="Simulación ficticia de una página web.",
            datos={
                "intencion": solicitud.intencion,
                "valor_normalizado": solicitud.valor_normalizado,
            },
        )
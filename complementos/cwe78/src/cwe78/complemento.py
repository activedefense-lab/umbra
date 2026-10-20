
"""Adaptador CWE-78 al contrato de complementos de Umbra (ADR-002)."""

from contrato.interfaz import VERSION_CONTRATO
from contrato.modelos import (
    ContextoSenuelo,
    Peticion,
    SolicitudSenuelo,
    Veredicto,
)

from .motor import Catalogo, analizar


SIMULACION = (
    "Eres un simulador de respuestas de una terminal Linux ficticia.\n\n"
    "Tu tarea es producir únicamente el texto que una terminal "
    "simulada podría mostrar ante una solicitud.\n\n"
    "Responde de forma breve, coherente y como una terminal simulada."
)


class ComplementoCWE78:
    """Complemento de detección y simulación para CWE-78."""

    nombre = "cwe78"
    cwe = "CWE-78"
    version_contrato = VERSION_CONTRATO

    def __init__(self, catalogo: Catalogo | None = None) -> None:
        self._catalogo = (
            catalogo if catalogo is not None else Catalogo.incluido()
        )
        self.intenciones: frozenset[str] = self._catalogo.intenciones

    def analizar(self, peticion: Peticion) -> Veredicto:
        """Analiza la petición mediante el motor CWE-78."""
        return analizar(
            peticion,
            self._catalogo,
            complemento=self.nombre,
        )

    def contexto_senuelo(
        self,
        solicitud: SolicitudSenuelo,
    ) -> ContextoSenuelo:
        """Aporta la simulación de terminal y los datos del ataque."""
        return ContextoSenuelo(
            simulacion=SIMULACION,
            datos={
                "intencion": solicitud.intencion,
                "valor_normalizado": solicitud.valor_normalizado,
            },
        )

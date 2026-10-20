
"""Datos de prueba compartidos para el complemento CWE-78."""

import re

import pytest

from cwe78.motor import Catalogo


@pytest.fixture
def catalogo_prueba() -> Catalogo:
    """Catálogo sintético con palabras clave neutras.

    Las pruebas del motor no dependen de las decisiones de
    etiquetado del catálogo real.
    """
    base = Catalogo.incluido()

    return Catalogo(
        nombre="prueba",
        metacaracteres=base.metacaracteres,
        separadores=base.separadores,
        palabras_clave={
            "reconocimiento": (re.compile(r"\balfa\b", re.I),),
            "descarga_herramientas": (re.compile(r"\bbeta\b", re.I),),
            "persistencia": (re.compile(r"\bgamma\b", re.I),),
        },
        prioridad=(
            "persistencia",
            "descarga_herramientas",
            "reconocimiento",
        ),
    )


@pytest.fixture
def catalogo_real() -> Catalogo:
    """Carga el catálogo incluido en el paquete."""
    return Catalogo.incluido()

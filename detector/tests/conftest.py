import json
import re
from pathlib import Path

import pytest

from detector.modelos import Intencion
from detector.reglas import RUTA_CATALOGO_POR_DEFECTO, Catalogo


@pytest.fixture
def catalogo_prueba() -> Catalogo:
    """Catálogo sintético: mismas reglas de metacaracteres que el real, palabras clave neutras.

    Las pruebas del motor no dependen del catálogo real para no acoplarse a
    decisiones de etiquetado que cambian en el sprint 2.
    """
    base = json.loads(RUTA_CATALOGO_POR_DEFECTO.read_text(encoding="utf-8"))
    return Catalogo(
        nombre="prueba",
        metacaracteres=tuple(base["metacaracteres"]),
        separadores=re.compile(base["separadores"]),
        palabras_clave={
            Intencion.RECONOCIMIENTO: (re.compile(r"\balfa\b", re.I),),
            Intencion.DESCARGA: (re.compile(r"\bbeta\b", re.I),),
            Intencion.PERSISTENCIA: (re.compile(r"\bgamma\b", re.I),),
        },
        prioridad=(Intencion.PERSISTENCIA, Intencion.DESCARGA, Intencion.RECONOCIMIENTO),
    )


@pytest.fixture
def catalogo_real() -> Catalogo:
    return Catalogo.desde_archivo(RUTA_CATALOGO_POR_DEFECTO)

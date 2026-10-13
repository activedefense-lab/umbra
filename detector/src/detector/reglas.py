"""Motor de reglas provisional (sprint 1).

Separa el *motor* (genérico: normaliza, detecta metacaracteres, segmenta y
puntúa) del *catálogo* (datos: metacaracteres, separadores y palabras clave
por intención), que se carga desde un archivo JSON. En la issue #13 el
catálogo pasa al complemento `cwe78` a través del contrato de complementos
sin cambiar este módulo. En el sprint 5 la puntuación por palabras clave se
reemplaza por el clasificador scikit-learn sin cambiar la API.

El catálogo lo redacta el equipo a partir de fuentes citables y se formaliza
en el protocolo del conjunto de datos (sprint 2).
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import unquote_plus

from .modelos import Intencion, Peticion, Veredicto

RUTA_CATALOGO_POR_DEFECTO = Path(__file__).with_name("catalogo_cwe78.json")


@dataclass(frozen=True)
class Catalogo:
    """Reglas de un tipo de inyección, cargadas desde JSON."""

    nombre: str
    metacaracteres: tuple[str, ...]
    separadores: re.Pattern[str]
    palabras_clave: dict[Intencion, tuple[re.Pattern[str], ...]]
    prioridad: tuple[Intencion, ...]

    @classmethod
    def desde_archivo(cls, ruta: Path = RUTA_CATALOGO_POR_DEFECTO) -> "Catalogo":
        datos = json.loads(ruta.read_text(encoding="utf-8"))
        palabras: dict[Intencion, tuple[re.Pattern[str], ...]] = {}
        for nombre, patrones in datos.get("palabras_clave", {}).items():
            palabras[Intencion(nombre)] = tuple(re.compile(p, re.IGNORECASE) for p in patrones)
        return cls(
            nombre=datos["nombre"],
            metacaracteres=tuple(datos["metacaracteres"]),
            separadores=re.compile(datos["separadores"]),
            palabras_clave=palabras,
            prioridad=tuple(Intencion(n) for n in datos.get("prioridad", [])),
        )


def normalizar(valor: str) -> str:
    """Decodifica URL (dos veces, por doble codificación) y compacta espacios."""
    texto = unquote_plus(unquote_plus(valor))
    return re.sub(r"[ \t]+", " ", texto).strip()


def metacaracteres_presentes(texto: str, catalogo: Catalogo) -> list[str]:
    """Devuelve los metacaracteres del catálogo que aparecen, sin repetir y en orden."""
    encontrados: list[str] = []
    for m in catalogo.metacaracteres:
        if m in texto and m not in encontrados:
            encontrados.append(m)
    # Si aparece un operador compuesto, su componente simple no cuenta aparte.
    for compuesto, simple in (("&&", "&"), ("||", "|")):
        if compuesto in encontrados and simple in encontrados and texto.count(simple) == 2 * texto.count(compuesto):
            encontrados.remove(simple)
    return encontrados


def segmentar(texto: str, catalogo: Catalogo) -> list[str]:
    """Separa el valor en segmentos de comando; descarta el primero (valor legítimo del parámetro)."""
    partes = [p.strip() for p in catalogo.separadores.split(texto)]
    partes = [p for p in partes if p]
    return partes[1:] if len(partes) > 1 else partes


def puntuar(segmentos: list[str], catalogo: Catalogo) -> dict[Intencion, list[str]]:
    """Por intención, lista de coincidencias de palabras clave en los segmentos."""
    coincidencias: dict[Intencion, list[str]] = {}
    for segmento in segmentos:
        for intencion, patrones in catalogo.palabras_clave.items():
            for patron in patrones:
                m = patron.search(segmento)
                if m:
                    coincidencias.setdefault(intencion, []).append(m.group(0))
    return coincidencias


def decidir(coincidencias: dict[Intencion, list[str]], catalogo: Catalogo) -> tuple[Intencion, float]:
    """Intención con más coincidencias; empate por orden de prioridad del catálogo."""
    if not coincidencias:
        return Intencion.DESCONOCIDA, 0.0
    total = sum(len(v) for v in coincidencias.values())
    maximo = max(len(v) for v in coincidencias.values())
    empatadas = [i for i, v in coincidencias.items() if len(v) == maximo]
    if len(empatadas) == 1:
        ganadora = empatadas[0]
    else:
        orden = {i: n for n, i in enumerate(catalogo.prioridad)}
        ganadora = min(empatadas, key=lambda i: orden.get(i, len(orden)))
    return ganadora, round(maximo / total, 3)


def analizar(peticion: Peticion, catalogo: Catalogo) -> Veredicto:
    """Flujo completo: normalizar → metacaracteres → segmentar → puntuar → decidir."""
    texto = normalizar(peticion.valor)
    metas = metacaracteres_presentes(texto, catalogo)
    if not metas:
        return Veredicto(es_ataque=False, valor_normalizado=texto)
    segmentos = segmentar(texto, catalogo)
    coincidencias = puntuar(segmentos, catalogo)
    intencion, confianza = decidir(coincidencias, catalogo)
    return Veredicto(
        es_ataque=True,
        metacaracteres=metas,
        segmentos=segmentos,
        intencion=intencion,
        confianza=confianza,
        coincidencias={str(k): v for k, v in coincidencias.items()},
        valor_normalizado=texto,
    )

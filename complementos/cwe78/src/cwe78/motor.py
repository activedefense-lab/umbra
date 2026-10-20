
"""Motor de reglas CWE-78 (migración de detector/reglas.py).

Conserva el algoritmo de detección original. Adapta los tipos de
intención al contrato y limita la evidencia después de clasificar.
"""

import json
import re
from dataclasses import dataclass
from importlib.resources import files
from urllib.parse import unquote_plus

from contrato.modelos import (
    INTENCION_DESCONOCIDA,
    MAX_ELEMENTOS,
    MAX_LONGITUD,
    Peticion,
    Veredicto,
)


@dataclass(frozen=True)
class Catalogo:
    """Reglas CWE-78 con intenciones ordenadas por prioridad."""

    nombre: str
    metacaracteres: tuple[str, ...]
    separadores: re.Pattern[str]
    palabras_clave: dict[str, tuple[re.Pattern[str], ...]]
    prioridad: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.prioridad:
            raise ValueError(
                "el catálogo debe declarar al menos una intención en 'prioridad'"
            )
        if len(set(self.prioridad)) != len(self.prioridad):
            raise ValueError("'prioridad' contiene intenciones repetidas")
        if INTENCION_DESCONOCIDA in self.prioridad:
            raise ValueError(
                f"'prioridad' no puede incluir la intención reservada "
                f"{INTENCION_DESCONOCIDA!r}"
            )
        ajenas = set(self.palabras_clave) - set(self.prioridad)
        if ajenas:
            raise ValueError(
                f"'palabras_clave' usa intenciones que 'prioridad' "
                f"no declara: {sorted(ajenas)}"
            )

    @property
    def intenciones(self) -> frozenset[str]:
        return frozenset(self.prioridad)

    @classmethod
    def desde_json(cls, texto: str) -> "Catalogo":
        datos = json.loads(texto)
        return cls(
            nombre=datos["nombre"],
            metacaracteres=tuple(datos["metacaracteres"]),
            separadores=re.compile(datos["separadores"]),
            palabras_clave={
                intencion: tuple(
                    re.compile(p, re.IGNORECASE) for p in patrones
                )
                for intencion, patrones in datos.get(
                    "palabras_clave", {}
                ).items()
            },
            prioridad=tuple(datos["prioridad"]),
        )

    @classmethod
    def incluido(cls) -> "Catalogo":
        """Carga el catálogo distribuido dentro del paquete."""
        recurso = files("cwe78").joinpath("catalogo.json")
        return cls.desde_json(recurso.read_text(encoding="utf-8"))


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


def puntuar(segmentos: list[str], catalogo: Catalogo) -> dict[str, list[str]]:
    """Por intención, lista de coincidencias de palabras clave en los segmentos."""
    coincidencias: dict[str, list[str]] = {}
    for segmento in segmentos:
        for intencion, patrones in catalogo.palabras_clave.items():
            for patron in patrones:
                m = patron.search(segmento)
                if m:
                    coincidencias.setdefault(intencion, []).append(m.group(0))
    return coincidencias


def decidir(coincidencias: dict[str, list[str]], catalogo: Catalogo) -> tuple[str, float]:
    """Intención con más coincidencias; empate por orden de prioridad del catálogo."""
    if not coincidencias:
        return INTENCION_DESCONOCIDA, 0.0
    total = sum(len(v) for v in coincidencias.values())
    maximo = max(len(v) for v in coincidencias.values())
    empatadas = [i for i, v in coincidencias.items() if len(v) == maximo]
    if len(empatadas) == 1:
        ganadora = empatadas[0]
    else:
        orden = {i: n for n, i in enumerate(catalogo.prioridad)}
        ganadora = min(empatadas, key=lambda i: orden.get(i, len(orden)))
    return ganadora, round(maximo / total, 3)


def _recortar(
    clave: str,
    valores: list[str],
    truncado: list[str],
) -> list[str]:
    """Limita la evidencia y registra qué campos fueron truncados."""
    recortados = [v[:MAX_LONGITUD] for v in valores[:MAX_ELEMENTOS]]
    if len(valores) > MAX_ELEMENTOS or any(
        len(v) > MAX_LONGITUD for v in valores[:MAX_ELEMENTOS]
    ):
        truncado.append(clave)
    return recortados


def analizar(
    peticion: Peticion,
    catalogo: Catalogo,
    *,
    complemento: str,
) -> Veredicto:
    """Normaliza, detecta, segmenta, puntúa y decide antes de recortar."""
    texto = normalizar(peticion.valor)
    metas = metacaracteres_presentes(texto, catalogo)

    if not metas:
        return Veredicto(
            complemento=complemento,
            es_ataque=False,
            valor_normalizado=texto,
        )

    segmentos = segmentar(texto, catalogo)
    coincidencias = puntuar(segmentos, catalogo)
    intencion, confianza = decidir(coincidencias, catalogo)

    truncado: list[str] = []
    evidencia = {
        "metacaracteres": _recortar("metacaracteres", metas, truncado),
        "segmentos": _recortar("segmentos", segmentos, truncado),
        "coincidencias": _recortar(
            "coincidencias",
            [
                f"{i}:{palabra}"
                for i, palabras in coincidencias.items()
                for palabra in palabras
            ],
            truncado,
        ),
    }
    if truncado:
        evidencia["truncado"] = truncado

    return Veredicto(
        complemento=complemento,
        es_ataque=True,
        intencion=intencion,
        confianza=confianza,
        valor_normalizado=texto,
        evidencia=evidencia,
    )

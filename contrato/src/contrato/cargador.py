
"""Cargador de complementos (ADR-002, decisiones 5 y 6).

Descubre complementos mediante entry points del grupo umbra.complementos.
listar() solo lee metadatos; cargar() importa, instancia y valida.
Cada entry point apunta a una fábrica sin argumentos.
"""

import os
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from importlib.metadata import EntryPoint, entry_points

from .errores import ComplementoDuplicado, ComplementoInvalido, ComplementoNoEncontrado
from .interfaz import Complemento, validar_complemento

GRUPO = "umbra.complementos"
VARIABLE_ACTIVO = "UMBRA_COMPLEMENTO"


@dataclass(frozen=True)
class Instalado:
    """Metadatos disponibles sin importar el código del complemento."""

    nombre: str
    paquete: str | None
    version: str | None


def _registrados(registros: Iterable[EntryPoint] | None) -> list[EntryPoint]:
    return list(entry_points(group=GRUPO) if registros is None else registros)


def listar(registros: Iterable[EntryPoint] | None = None) -> list[Instalado]:
    """Lista complementos instalados sin importar ni ejecutar su código."""
    return sorted(
        (
            Instalado(
                nombre=ep.name,
                paquete=ep.dist.name if ep.dist else None,
                version=ep.dist.version if ep.dist else None,
            )
            for ep in _registrados(registros)
        ),
        key=lambda instalado: (instalado.nombre, instalado.paquete or ""),
    )


def cargar(nombre: str, registros: Iterable[EntryPoint] | None = None) -> Complemento:
    """Importa, instancia y valida el complemento registrado con ese nombre."""
    disponibles = _registrados(registros)
    coincidencias = [ep for ep in disponibles if ep.name == nombre]

    if not coincidencias:
        instalados = ", ".join(sorted({ep.name for ep in disponibles})) or "ninguno"
        raise ComplementoNoEncontrado(
            f"no hay un complemento {nombre!r} instalado; instalados: {instalados}"
        )

    if len(coincidencias) > 1:
        origenes = ", ".join(sorted(ep.value for ep in coincidencias))
        raise ComplementoDuplicado(
            f"el nombre {nombre!r} está registrado {len(coincidencias)} veces: {origenes}"
        )

    registro = coincidencias[0]
    try:
        fabrica = registro.load()
        objeto = fabrica()
    except Exception as error:
        raise ComplementoInvalido(
            f"no se pudo cargar {nombre!r} desde {registro.value!r}: {error}"
        ) from error

    complemento = validar_complemento(objeto)

    if complemento.nombre != nombre:
        raise ComplementoInvalido(
            f"el registro {nombre!r} carga un complemento "
            f"que se identifica como {complemento.nombre!r}"
        )

    return complemento


def cargar_activo(
    entorno: Mapping[str, str] | None = None,
    registros: Iterable[EntryPoint] | None = None,
) -> Complemento:
    """Carga el complemento indicado por la variable obligatoria UMBRA_COMPLEMENTO."""
    registros = None if registros is None else list(registros)
    entorno = os.environ if entorno is None else entorno
    nombre = entorno.get(VARIABLE_ACTIVO, "").strip()

    if not nombre:
        instalados = ", ".join(i.nombre for i in listar(registros)) or "ninguno"
        raise ComplementoNoEncontrado(
            f"falta la variable {VARIABLE_ACTIVO}; "
            f"complementos instalados: {instalados}"
        )

    return cargar(nombre, registros)

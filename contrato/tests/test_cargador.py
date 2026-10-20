
"""Pruebas del cargador (ADR-002, decisiones 5 y 6).

Los registros son ficticios: no dependen de complementos instalados.
El descubrimiento real se verificará al instalar complementos/cwe78.
"""

import sys
from importlib.metadata import EntryPoint

import pytest

from contrato.cargador import GRUPO, VARIABLE_ACTIVO, cargar, cargar_activo, listar
from contrato.errores import (
    ComplementoDuplicado,
    ComplementoInvalido,
    ComplementoNoEncontrado,
    VersionIncompatible,
)


def registro(nombre: str, valor: str) -> EntryPoint:
    return EntryPoint(name=nombre, value=valor, group=GRUPO)


VALIDO = registro("ficticio", "ficticios:Ficticio")
EXPLOSIVO = registro("explosivo", "explosivo:Complemento")


# --- Carga de complementos ---


def test_carga_un_complemento_registrado():
    assert cargar("ficticio", [VALIDO]).nombre == "ficticio"


def test_inexistente_lista_los_instalados():
    with pytest.raises(ComplementoNoEncontrado, match="instalados: ficticio"):
        cargar("otro", [VALIDO])


def test_sin_complementos_instalados():
    with pytest.raises(ComplementoNoEncontrado, match="ninguno"):
        cargar("ficticio", [])


def test_nombre_registrado_dos_veces():
    with pytest.raises(ComplementoDuplicado, match="2 veces"):
        cargar("ficticio", [VALIDO, registro("ficticio", "ficticios:OtroFicticio")])


def test_modulo_inexistente():
    with pytest.raises(ComplementoInvalido):
        cargar("ficticio", [registro("ficticio", "modulo_que_no_existe:Clase")])


def test_objeto_inexistente_en_el_modulo():
    with pytest.raises(ComplementoInvalido):
        cargar("ficticio", [registro("ficticio", "ficticios:NoExiste")])


def test_fabrica_que_falla_al_instanciar():
    with pytest.raises(ComplementoInvalido, match="fallo al construir"):
        cargar("ficticio", [registro("ficticio", "ficticios:FallaAlCrear")])


def test_fabrica_no_invocable():
    with pytest.raises(ComplementoInvalido, match="not callable"):
        cargar("ficticio", [registro("ficticio", "ficticios:NO_INVOCABLE")])


def test_registro_que_no_cumple_la_interfaz():
    with pytest.raises(ComplementoInvalido):
        cargar("ficticio", [registro("ficticio", "ficticios:SinMetodos")])


def test_version_incompatible():
    with pytest.raises(VersionIncompatible):
        cargar("ficticio", [registro("ficticio", "ficticios:VersionFutura")])


def test_nombre_registrado_distinto_del_declarado():
    with pytest.raises(ComplementoInvalido, match="se identifica como"):
        cargar("alias", [registro("alias", "ficticios:Ficticio")])


def test_modulo_que_falla_al_importarse():
    with pytest.raises(ComplementoInvalido):
        cargar("explosivo", [EXPLOSIVO])


# --- Descubrimiento sin importar código ---


def test_listar_no_importa_el_codigo_de_los_complementos(monkeypatch):
    monkeypatch.delitem(sys.modules, "explosivo", raising=False)
    instalados = listar([EXPLOSIVO, VALIDO])
    assert [i.nombre for i in instalados] == ["explosivo", "ficticio"]
    assert "explosivo" not in sys.modules


# --- Selección mediante UMBRA_COMPLEMENTO ---


def test_activo_desde_la_variable():
    assert cargar_activo({VARIABLE_ACTIVO: "ficticio"}, [VALIDO]).nombre == "ficticio"


def test_activo_sin_variable_lista_los_instalados():
    with pytest.raises(ComplementoNoEncontrado, match=f"{VARIABLE_ACTIVO}.*ficticio"):
        cargar_activo({}, [VALIDO])


def test_activo_con_variable_vacia():
    with pytest.raises(ComplementoNoEncontrado):
        cargar_activo({VARIABLE_ACTIVO: "   "}, [VALIDO])


def test_activo_con_nombre_no_instalado():
    with pytest.raises(ComplementoNoEncontrado, match="instalados: ficticio"):
        cargar_activo({VARIABLE_ACTIVO: "otro"}, [VALIDO])


"""Pruebas del complemento CWE-78 ante el contrato (ADR-002).

Incluyen validación de interfaz, composición de instrucciones
y descubrimiento real mediante entry points.
"""

from contrato.cargador import cargar, listar
from contrato.composicion import RESTRICCIONES, componer
from contrato.interfaz import (
    validar_complemento,
    verificar_contexto,
    verificar_resultado,
)
from contrato.modelos import (
    MAX_LONGITUD,
    ContextoSenuelo,
    Peticion,
    SolicitudSenuelo,
)

from cwe78.complemento import ComplementoCWE78
from cwe78.motor import Catalogo


def _solicitud(**cambios) -> SolicitudSenuelo:
    datos = {
        "complemento": "cwe78",
        "intencion": "reconocimiento",
        "valor_normalizado": "127.0.0.1;x",
        "evidencia": {"segmentos": ["x"]},
    }
    datos.update(cambios)
    return SolicitudSenuelo(**datos)


def test_cumple_el_contrato():
    complemento = ComplementoCWE78()
    assert validar_complemento(complemento) is complemento


def test_identidad_fija_con_catalogo_sintetico(catalogo_prueba):
    complemento = ComplementoCWE78(catalogo_prueba)

    veredicto = complemento.analizar(
        Peticion(
            origen="anon",
            ruta="/ping",
            parametro="host",
            valor="ip;alfa",
        )
    )

    assert veredicto.complemento == "cwe78"
    assert verificar_resultado(complemento, veredicto) is veredicto


def test_las_intenciones_vienen_del_catalogo():
    assert (
        ComplementoCWE78().intenciones
        == Catalogo.incluido().intenciones
    )


def test_contexto_lleva_solo_intencion_y_valor():
    complemento = ComplementoCWE78()
    contexto = complemento.contexto_senuelo(_solicitud())

    assert verificar_contexto(complemento, contexto) is contexto
    assert set(contexto.datos) == {
        "intencion",
        "valor_normalizado",
    }
    assert contexto.simulacion.strip()


def test_contexto_admite_el_valor_maximo_de_la_solicitud():
    contexto = ComplementoCWE78().contexto_senuelo(
        _solicitud(valor_normalizado="a" * MAX_LONGITUD)
    )

    assert isinstance(contexto, ContextoSenuelo)


def test_se_compone_con_las_restricciones_del_nucleo():
    contexto = ComplementoCWE78().contexto_senuelo(_solicitud())
    instrucciones = componer(contexto)

    assert instrucciones.sistema.startswith(RESTRICCIONES)
    assert contexto.simulacion in instrucciones.sistema
    assert "127.0.0.1;x" in instrucciones.entrada
    assert "127.0.0.1;x" not in instrucciones.sistema


def test_descubrimiento_real_por_entry_point():
    complemento = cargar("cwe78")
    assert isinstance(complemento, ComplementoCWE78)


def test_listar_muestra_el_paquete_instalado():
    instalados = {i.nombre: i for i in listar()}

    assert instalados["cwe78"].paquete == "umbra-complemento-cwe78"
    assert instalados["cwe78"].version == "0.1.0"

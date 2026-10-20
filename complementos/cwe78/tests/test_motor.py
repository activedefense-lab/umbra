
"""Pruebas del motor CWE-78 (ADR-002, criterio de aceptación 1).

Conservan los casos del detector original, adaptados al nuevo contrato.
También comprueban la identidad, el catálogo y los límites de evidencia.
"""

import re

import pytest

from contrato.modelos import (
    INTENCION_DESCONOCIDA,
    MAX_ELEMENTOS,
    MAX_LONGITUD,
    Peticion,
)
from cwe78.motor import (
    Catalogo,
    analizar,
    decidir,
    metacaracteres_presentes,
    normalizar,
    segmentar,
)


def _peticion(valor: str) -> Peticion:
    return Peticion(
        origen="anon",
        ruta="/diagnostico/ping",
        parametro="host",
        valor=valor,
    )


def _analizar(valor: str, catalogo: Catalogo):
    return analizar(
        _peticion(valor),
        catalogo,
        complemento="cwe78",
    )


# Pruebas trasladadas del detector original


class TestNormalizar:
    def test_decodifica_url_simple(self):
        assert normalizar("127.0.0.1%3Bcmd") == "127.0.0.1;cmd"

    def test_decodifica_doble_codificacion(self):
        assert normalizar("x%253By") == "x;y"

    def test_compacta_espacios_y_recorta(self):
        assert normalizar("  a    b  ") == "a b"


class TestMetacaracteres:
    def test_valor_limpio_no_tiene_metacaracteres(self, catalogo_prueba):
        assert metacaracteres_presentes("127.0.0.1", catalogo_prueba) == []

    def test_detecta_punto_y_coma(self, catalogo_prueba):
        assert ";" in metacaracteres_presentes(
            "127.0.0.1;alfa", catalogo_prueba
        )

    def test_detecta_varios_sin_repetir(self, catalogo_prueba):
        metas = metacaracteres_presentes("a;b;c|d", catalogo_prueba)
        assert metas.count(";") == 1
        assert "|" in metas

    def test_operador_compuesto_no_duplica_el_simple(self, catalogo_prueba):
        metas = metacaracteres_presentes("a && b", catalogo_prueba)
        assert "&&" in metas
        assert "&" not in metas


class TestSegmentar:
    def test_descarta_el_valor_legitimo_inicial(self, catalogo_prueba):
        assert segmentar("127.0.0.1;alfa", catalogo_prueba) == ["alfa"]

    def test_varios_segmentos(self, catalogo_prueba):
        assert segmentar("ip;alfa|beta", catalogo_prueba) == [
            "alfa",
            "beta",
        ]


class TestDecidir:
    def test_sin_coincidencias_es_desconocida(self, catalogo_prueba):
        assert decidir({}, catalogo_prueba) == (
            INTENCION_DESCONOCIDA,
            0.0,
        )

    def test_mayoria_simple(self, catalogo_prueba):
        coincidencias = {
            "reconocimiento": ["alfa", "alfa"],
            "descarga_herramientas": ["beta"],
        }
        intencion, confianza = decidir(coincidencias, catalogo_prueba)

        assert intencion == "reconocimiento"
        assert confianza == round(2 / 3, 3)

    def test_empate_se_resuelve_por_prioridad(self, catalogo_prueba):
        coincidencias = {
            "reconocimiento": ["alfa"],
            "persistencia": ["gamma"],
        }
        intencion, _ = decidir(coincidencias, catalogo_prueba)

        assert intencion == "persistencia"


class TestAnalizar:
    def test_peticion_limpia_no_es_ataque(self, catalogo_prueba):
        v = _analizar("127.0.0.1", catalogo_prueba)

        assert v.es_ataque is False
        assert v.intencion == INTENCION_DESCONOCIDA
        assert v.evidencia == {}

    def test_ataque_con_intencion(self, catalogo_prueba):
        v = _analizar("127.0.0.1;alfa", catalogo_prueba)

        assert v.es_ataque is True
        assert ";" in v.evidencia["metacaracteres"]
        assert v.intencion == "reconocimiento"
        assert v.evidencia["coincidencias"] == [
            "reconocimiento:alfa"
        ]

    def test_ataque_sin_palabra_clave_conocida_es_desconocida(
        self, catalogo_prueba
    ):
        v = _analizar("127.0.0.1;delta", catalogo_prueba)

        assert v.es_ataque is True
        assert v.intencion == INTENCION_DESCONOCIDA
        assert v.confianza == 0.0

    def test_ataque_codificado_en_url(self, catalogo_prueba):
        v = _analizar("127.0.0.1%3Bbeta", catalogo_prueba)

        assert v.es_ataque is True
        assert v.intencion == "descarga_herramientas"

    def test_el_catalogo_real_carga(self, catalogo_real):
        v = _analizar("127.0.0.1;cualquiercosa", catalogo_real)
        assert v.es_ataque is True


# Pruebas nuevas del contrato


def test_la_identidad_viene_del_parametro_no_del_catalogo(catalogo_prueba):
    assert catalogo_prueba.nombre == "prueba"

    v = _analizar("ip;alfa", catalogo_prueba)
    assert v.complemento == "cwe78"


@pytest.mark.parametrize(
    ("prioridad", "palabras_clave"),
    [
        ((), {}),
        (("intencion_a", "intencion_a"), {}),
        (("intencion_a", INTENCION_DESCONOCIDA), {}),
        (("intencion_a",), {"intencion_ajena": ()}),
    ],
    ids=["vacia", "repetida", "reservada", "ajena"],
)
def test_catalogo_invalido(prioridad, palabras_clave):
    with pytest.raises(ValueError):
        Catalogo(
            nombre="prueba",
            metacaracteres=(";",),
            separadores=re.compile(";"),
            palabras_clave=palabras_clave,
            prioridad=prioridad,
        )


def test_el_catalogo_incluido_es_valido_y_declara_cinco_intenciones(
    catalogo_real,
):
    assert len(catalogo_real.intenciones) == 5


def test_clasifica_antes_de_recortar(catalogo_prueba):
    # Solo el segmento 21 coincide. La clasificación debe verlo,
    # aunque ese segmento no aparezca en la evidencia recortada.
    valor = "ip" + ";x" * MAX_ELEMENTOS + ";alfa"
    v = _analizar(valor, catalogo_prueba)

    assert v.intencion == "reconocimiento"
    assert len(v.evidencia["segmentos"]) == MAX_ELEMENTOS
    assert "alfa" not in v.evidencia["segmentos"]
    assert v.evidencia["coincidencias"] == [
        "reconocimiento:alfa"
    ]
    assert v.evidencia["truncado"] == ["segmentos"]


def test_segmento_demasiado_largo_se_recorta(catalogo_prueba):
    valor = "ip;" + "a" * (MAX_LONGITUD + 1)
    v = _analizar(valor, catalogo_prueba)

    assert len(v.evidencia["segmentos"][0]) == MAX_LONGITUD
    assert v.evidencia["truncado"] == ["segmentos"]


def test_sin_recorte_no_aparece_truncado(catalogo_prueba):
    v = _analizar("ip;alfa", catalogo_prueba)
    assert "truncado" not in v.evidencia

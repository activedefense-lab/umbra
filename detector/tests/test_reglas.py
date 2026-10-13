"""Pruebas unitarias del motor de reglas (issue #10)."""

from detector.modelos import Intencion, Peticion
from detector.reglas import (
    analizar,
    decidir,
    metacaracteres_presentes,
    normalizar,
    segmentar,
)


def _peticion(valor: str) -> Peticion:
    return Peticion(origen="anon", ruta="/diagnostico/ping", parametro="host", valor=valor)


class TestNormalizar:
    def test_decodifica_url_simple(self):
        assert normalizar("127.0.0.1%3Bcmd") == "127.0.0.1;cmd"

    def test_decodifica_doble_codificacion(self):
        # %253B -> %3B -> ;
        assert normalizar("x%253By") == "x;y"

    def test_compacta_espacios_y_recorta(self):
        assert normalizar("  a    b  ") == "a b"


class TestMetacaracteres:
    def test_valor_limpio_no_tiene_metacaracteres(self, catalogo_prueba):
        assert metacaracteres_presentes("127.0.0.1", catalogo_prueba) == []

    def test_detecta_punto_y_coma(self, catalogo_prueba):
        assert ";" in metacaracteres_presentes("127.0.0.1;alfa", catalogo_prueba)

    def test_detecta_varios_sin_repetir(self, catalogo_prueba):
        metas = metacaracteres_presentes("a;b;c|d", catalogo_prueba)
        assert metas.count(";") == 1 and "|" in metas

    def test_operador_compuesto_no_duplica_el_simple(self, catalogo_prueba):
        # "a && b" tiene '&&' pero no debe reportar también '&' por separado.
        metas = metacaracteres_presentes("a && b", catalogo_prueba)
        assert "&&" in metas and "&" not in metas


class TestSegmentar:
    def test_descarta_el_valor_legitimo_inicial(self, catalogo_prueba):
        # El primer segmento es el valor legítimo del parámetro, no un comando inyectado.
        assert segmentar("127.0.0.1;alfa", catalogo_prueba) == ["alfa"]

    def test_varios_segmentos(self, catalogo_prueba):
        assert segmentar("ip;alfa|beta", catalogo_prueba) == ["alfa", "beta"]


class TestDecidir:
    def test_sin_coincidencias_es_desconocida(self, catalogo_prueba):
        intencion, confianza = decidir({}, catalogo_prueba)
        assert intencion is Intencion.DESCONOCIDA and confianza == 0.0

    def test_mayoria_simple(self, catalogo_prueba):
        coincidencias = {Intencion.RECONOCIMIENTO: ["alfa", "alfa"], Intencion.DESCARGA: ["beta"]}
        intencion, confianza = decidir(coincidencias, catalogo_prueba)
        assert intencion is Intencion.RECONOCIMIENTO
        assert confianza == round(2 / 3, 3)

    def test_empate_se_resuelve_por_prioridad(self, catalogo_prueba):
        # Reconocimiento y persistencia empatan a 1; la prioridad del catálogo
        # pone persistencia por delante.
        coincidencias = {Intencion.RECONOCIMIENTO: ["alfa"], Intencion.PERSISTENCIA: ["gamma"]}
        intencion, _ = decidir(coincidencias, catalogo_prueba)
        assert intencion is Intencion.PERSISTENCIA


class TestAnalizar:
    def test_peticion_limpia_no_es_ataque(self, catalogo_prueba):
        v = analizar(_peticion("127.0.0.1"), catalogo_prueba)
        assert v.es_ataque is False
        assert v.intencion is Intencion.DESCONOCIDA
        assert v.segmentos == []

    def test_ataque_con_intencion(self, catalogo_prueba):
        v = analizar(_peticion("127.0.0.1;alfa"), catalogo_prueba)
        assert v.es_ataque is True
        assert ";" in v.metacaracteres
        assert v.intencion is Intencion.RECONOCIMIENTO
        assert v.coincidencias == {"reconocimiento": ["alfa"]}

    def test_ataque_sin_palabra_clave_conocida_es_desconocida(self, catalogo_prueba):
        v = analizar(_peticion("127.0.0.1;delta"), catalogo_prueba)
        assert v.es_ataque is True
        assert v.intencion is Intencion.DESCONOCIDA
        assert v.confianza == 0.0

    def test_ataque_codificado_en_url(self, catalogo_prueba):
        v = analizar(_peticion("127.0.0.1%3Bbeta"), catalogo_prueba)
        assert v.es_ataque is True
        assert v.intencion is Intencion.DESCARGA

    def test_el_catalogo_real_carga(self, catalogo_real):
        # No afirma intención (las palabras clave reales se llenan en el sprint 2),
        # solo que el catálogo real es válido y el motor corre con él.
        v = analizar(_peticion("127.0.0.1;cualquiercosa"), catalogo_real)
        assert v.es_ataque is True


"""Pruebas de la interfaz y de la capa del núcleo (ADR-002, decisiones 2, 3 y 5)."""

import pytest

from contrato.errores import ComplementoInvalido, ResultadoInvalido, VersionIncompatible
from contrato.interfaz import VERSION_CONTRATO, Complemento, validar_complemento, verificar_resultado
from contrato.modelos import INTENCION_DESCONOCIDA, ContextoSenuelo, Veredicto


class Ficticio:
    nombre = "ficticio"
    cwe = "CWE-1"
    version_contrato = VERSION_CONTRATO
    intenciones = frozenset({"intencion_a", "intencion_b"})

    def analizar(self, peticion):
        return Veredicto(complemento=self.nombre, es_ataque=False)

    def contexto_senuelo(self, solicitud):
        return ContextoSenuelo(simulacion="sistema ficticio")


def variante(**atributos) -> Ficticio:
    """Un Ficticio con atributos reemplazados solo en la instancia."""
    complemento = Ficticio()
    for nombre, valor in atributos.items():
        setattr(complemento, nombre, valor)
    return complemento


# --- validar_complemento ---

def test_complemento_valido_se_acepta():
    complemento = Ficticio()
    assert validar_complemento(complemento) is complemento
    assert isinstance(complemento, Complemento)


def test_objeto_sin_metodos_es_invalido():
    class Incompleto:
        nombre, cwe, version_contrato = "incompleto", "CWE-1", VERSION_CONTRATO
        intenciones = frozenset({"intencion_a"})

    with pytest.raises(ComplementoInvalido):
        validar_complemento(Incompleto())


@pytest.mark.parametrize("version", [1, -1, "0", 0.0, False, None])
def test_version_distinta_o_de_otro_tipo(version):
    with pytest.raises(VersionIncompatible):
        validar_complemento(variante(version_contrato=version))


@pytest.mark.parametrize("nombre", ["", "Ficticio", "fic-ticio", 7])
def test_nombre_invalido(nombre):
    with pytest.raises(ComplementoInvalido):
        validar_complemento(variante(nombre=nombre))


@pytest.mark.parametrize("cwe", ["78", "cwe-78", "CWE-", "CWE-078", "CWE-78 ", None])
def test_cwe_invalido(cwe):
    with pytest.raises(ComplementoInvalido):
        validar_complemento(variante(cwe=cwe))


@pytest.mark.parametrize(
    "intenciones",
    [frozenset(), {"intencion_a"}, ["intencion_a"], frozenset({"Mala Intencion"}), frozenset({1})],
)
def test_catalogo_de_intenciones_invalido(intenciones):
    with pytest.raises(ComplementoInvalido):
        validar_complemento(variante(intenciones=intenciones))


def test_catalogo_no_puede_declarar_la_intencion_reservada():
    with pytest.raises(ComplementoInvalido, match="reservada"):
        validar_complemento(variante(intenciones=frozenset({"intencion_a", INTENCION_DESCONOCIDA})))


@pytest.mark.parametrize(
    ("metodo", "valor"),
    [("analizar", lambda: None), ("analizar", "no invocable"), ("contexto_senuelo", lambda a, b: None)],
)
def test_metodo_que_no_puede_recibir_un_argumento(metodo, valor):
    with pytest.raises(ComplementoInvalido):
        validar_complemento(variante(**{metodo: valor}))


# --- verificar_resultado (capa del núcleo) ---

def test_veredicto_sin_ataque_del_complemento_activo():
    veredicto = Veredicto(complemento="ficticio", es_ataque=False)
    assert verificar_resultado(Ficticio(), veredicto) is veredicto


def test_ataque_con_intencion_del_catalogo():
    veredicto = Veredicto(complemento="ficticio", es_ataque=True, intencion="intencion_a", confianza=0.9)
    assert verificar_resultado(Ficticio(), veredicto) is veredicto


def test_ataque_con_intencion_desconocida_es_valido():
    # Hay inyección pero no se infiere la intención: concepto del núcleo, siempre admitido.
    veredicto = Veredicto(complemento="ficticio", es_ataque=True)
    assert verificar_resultado(Ficticio(), veredicto) is veredicto


@pytest.mark.parametrize("resultado", [None, {"complemento": "ficticio", "es_ataque": False}])
def test_resultado_que_no_es_veredicto(resultado):
    with pytest.raises(ResultadoInvalido):
        verificar_resultado(Ficticio(), resultado)


def test_veredicto_atribuido_a_otro_complemento():
    with pytest.raises(ResultadoInvalido, match="activo"):
        verificar_resultado(Ficticio(), Veredicto(complemento="otro", es_ataque=False))


def test_intencion_fuera_del_catalogo():
    veredicto = Veredicto(complemento="ficticio", es_ataque=True, intencion="intencion_ajena", confianza=0.5)
    with pytest.raises(ResultadoInvalido, match="catálogo"):
        verificar_resultado(Ficticio(), veredicto)

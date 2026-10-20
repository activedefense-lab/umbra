"""Pruebas de los modelos compartidos (ADR-002, decisión 2; criterio de aceptación 7).

Usan un complemento ficticio a propósito: el contrato no conoce ninguna CWE.
"""

import pytest
from pydantic import ValidationError

from contrato.modelos import (
    INTENCION_DESCONOCIDA,
    MAX_CLAVES,
    MAX_ELEMENTOS,
    MAX_LONGITUD,
    ContextoSenuelo,
    Peticion,
    SolicitudSenuelo,
    Veredicto,
)


def ataque(**cambios) -> Veredicto:
    """Veredicto de ataque válido; cada prueba altera solo lo que examina."""
    datos = {
        "complemento": "ficticio",
        "es_ataque": True,
        "intencion": "intencion_ficticia",
        "confianza": 0.8,
        "valor_normalizado": "x",
        "evidencia": {"pistas": ["a"]},
    }
    datos.update(cambios)
    return Veredicto(**datos)


# --- Veredicto: invariantes de "sin ataque" (una prueba por invariante) ---

def test_veredicto_sin_ataque_por_defecto_es_neutro():
    v = Veredicto(complemento="ficticio", es_ataque=False)
    assert v.intencion == INTENCION_DESCONOCIDA
    assert v.confianza == 0.0
    assert v.evidencia == {}


def test_sin_ataque_rechaza_intencion_distinta_de_desconocida():
    with pytest.raises(ValidationError, match="intención"):
        Veredicto(complemento="ficticio", es_ataque=False, intencion="intencion_ficticia")


def test_sin_ataque_rechaza_confianza_distinta_de_cero():
    with pytest.raises(ValidationError, match="confianza"):
        Veredicto(complemento="ficticio", es_ataque=False, confianza=0.5)


def test_sin_ataque_rechaza_evidencia():
    with pytest.raises(ValidationError, match="evidencia"):
        Veredicto(complemento="ficticio", es_ataque=False, evidencia={"pistas": ["a"]})


def test_ataque_valido_se_construye():
    v = ataque()
    assert v.es_ataque and v.intencion == "intencion_ficticia"


@pytest.mark.parametrize("confianza", [-0.01, 1.01])
def test_confianza_fuera_de_rango(confianza):
    with pytest.raises(ValidationError):
        ataque(confianza=confianza)


# --- Límites de evidencia, probados en el borde exacto ---

def test_evidencia_admite_el_maximo_de_claves():
    ataque(evidencia={f"clave{i}": ["a"] for i in range(MAX_CLAVES)})


def test_evidencia_rechaza_una_clave_de_mas():
    with pytest.raises(ValidationError):
        ataque(evidencia={f"clave{i}": ["a"] for i in range(MAX_CLAVES + 1)})


def test_evidencia_admite_el_maximo_de_elementos():
    ataque(evidencia={"pistas": ["a"] * MAX_ELEMENTOS})


def test_evidencia_rechaza_un_elemento_de_mas():
    with pytest.raises(ValidationError):
        ataque(evidencia={"pistas": ["a"] * (MAX_ELEMENTOS + 1)})


def test_evidencia_admite_la_longitud_maxima():
    ataque(evidencia={"pistas": ["a" * MAX_LONGITUD]})


def test_evidencia_rechaza_un_caracter_de_mas():
    with pytest.raises(ValidationError):
        ataque(evidencia={"pistas": ["a" * (MAX_LONGITUD + 1)]})


# --- Identificadores ---

@pytest.mark.parametrize("nombre", ["", "Ficticio", "9ficticio", "fic-ticio", "fic ticio", "ficticio\n", "a" * 65])
def test_identificador_invalido_en_complemento(nombre):
    with pytest.raises(ValidationError):
        ataque(complemento=nombre)


def test_identificador_admite_64_caracteres():
    ataque(complemento="a" * 64)


def test_identificador_invalido_en_intencion():
    with pytest.raises(ValidationError):
        ataque(intencion="Intencion Ficticia")


def test_identificador_invalido_en_clave_de_evidencia():
    with pytest.raises(ValidationError):
        ataque(evidencia={"Clave Invalida": ["a"]})


# --- Campos desconocidos e inmutabilidad ---

def test_veredicto_rechaza_campos_desconocidos():
    # `segmentos` era un campo del modelo anterior; ahora va dentro de evidencia.
    with pytest.raises(ValidationError):
        ataque(segmentos=["a"])


def test_veredicto_es_inmutable():
    v = ataque()
    with pytest.raises(ValidationError):
        v.es_ataque = False


# --- SolicitudSenuelo: conserva el límite que ya tenía ---

def test_solicitud_admite_valor_normalizado_de_4096():
    SolicitudSenuelo(complemento="ficticio", valor_normalizado="a" * MAX_LONGITUD)


def test_solicitud_rechaza_valor_normalizado_de_4097():
    with pytest.raises(ValidationError):
        SolicitudSenuelo(complemento="ficticio", valor_normalizado="a" * (MAX_LONGITUD + 1))


def test_solicitud_rechaza_el_campo_segmentos_anterior():
    with pytest.raises(ValidationError):
        SolicitudSenuelo(complemento="ficticio", segmentos=["a"])


def test_solicitud_aplica_los_limites_de_evidencia():
    with pytest.raises(ValidationError):
        SolicitudSenuelo(complemento="ficticio", evidencia={"pistas": ["a"] * (MAX_ELEMENTOS + 1)})


# --- ContextoSenuelo ---

def test_contexto_exige_simulacion_no_vacia():
    with pytest.raises(ValidationError):
        ContextoSenuelo(simulacion="")


def test_contexto_rechaza_una_clave_de_datos_de_mas():
    with pytest.raises(ValidationError):
        ContextoSenuelo(simulacion="s", datos={f"dato{i}": "a" for i in range(MAX_CLAVES + 1)})


def test_contexto_rechaza_un_dato_demasiado_largo():
    with pytest.raises(ValidationError):
        ContextoSenuelo(simulacion="s", datos={"dato": "a" * (MAX_LONGITUD + 1)})


# --- Peticion: mismos cuatro campos obligatorios ---

def test_peticion_exige_sus_cuatro_campos():
    with pytest.raises(ValidationError):
        Peticion(origen="o", ruta="/r", parametro="p")


def test_peticion_rechaza_campos_desconocidos():
    with pytest.raises(ValidationError):
        Peticion(origen="o", ruta="/r", parametro="p", valor="v", extra="x")
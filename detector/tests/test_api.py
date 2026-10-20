
"""Pruebas de la API del detector (ADR-002).

Conservan los cuatro casos originales y verifican que el núcleo
funciona con complementos independientes de una CWE concreta.
"""

import ast
from importlib.metadata import entry_points
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from contrato.cargador import GRUPO, VARIABLE_ACTIVO
from contrato.errores import (
    ComplementoInvalido,
    ComplementoNoEncontrado,
    ResultadoInvalido,
)
from detector.api import crear_app
from falsos import Falso, IntencionAjena, Suplantador


PETICION = {
    "origen": "anon",
    "ruta": "/ping",
    "parametro": "host",
}


def _cliente(complemento=None) -> TestClient:
    if complemento is None:
        complemento = Falso()
    return TestClient(crear_app(complemento))


# Casos originales adaptados al contrato


def test_salud_informa_el_complemento_activo():
    respuesta = _cliente().get("/salud")
    assert respuesta.status_code == 200

    cuerpo = respuesta.json()
    assert cuerpo["estado"] == "ok"
    assert cuerpo["complemento"] == {
        "nombre": "falso",
        "cwe": "CWE-1",
    }
    assert isinstance(cuerpo["instalados"], list)


def test_analizar_peticion_limpia():
    respuesta = _cliente().post(
        "/analizar",
        json={**PETICION, "valor": "127.0.0.1"},
    )

    assert respuesta.status_code == 200
    assert respuesta.json()["es_ataque"] is False
    assert respuesta.json()["complemento"] == "falso"


def test_analizar_ataque():
    respuesta = _cliente().post(
        "/analizar",
        json={**PETICION, "valor": "127.0.0.1;x"},
    )

    assert respuesta.status_code == 200
    assert respuesta.json()["es_ataque"] is True
    assert respuesta.json()["intencion"] == "intencion_a"


def test_peticion_invalida_devuelve_422():
    respuesta = _cliente().post(
        "/analizar",
        json={"valor": "falta todo lo demas"},
    )

    assert respuesta.status_code == 422


# Nuevas pruebas del contrato


def test_campo_desconocido_devuelve_422():
    respuesta = _cliente().post(
        "/analizar",
        json={**PETICION, "valor": "v", "extra": "x"},
    )

    assert respuesta.status_code == 422


@pytest.mark.parametrize(
    "complemento",
    [Suplantador(), IntencionAjena()],
    ids=["otro_complemento", "intencion_ajena"],
)
def test_veredicto_invalido_no_se_propaga(complemento):
    with pytest.raises(ResultadoInvalido):
        _cliente(complemento).post(
            "/analizar",
            json={**PETICION, "valor": "127.0.0.1;x"},
        )


def test_un_complemento_inyectado_tambien_se_valida():
    complemento = Falso()
    complemento.nombre = "No Valido"

    with pytest.raises(ComplementoInvalido):
        crear_app(complemento)


def test_sin_variable_no_arranca(monkeypatch):
    monkeypatch.delenv(VARIABLE_ACTIVO, raising=False)

    with pytest.raises(ComplementoNoEncontrado):
        crear_app()


def _complementos_instalados() -> list[str]:
    nombres = sorted(
        ep.name for ep in entry_points(group=GRUPO)
    )
    assert nombres, (
        "No hay complementos instalados junto al detector"
    )
    return nombres


def test_arranca_con_un_complemento_instalado(monkeypatch):
    nombre = _complementos_instalados()[0]
    monkeypatch.setenv(VARIABLE_ACTIVO, nombre)

    respuesta = TestClient(crear_app()).get("/salud")

    assert respuesta.status_code == 200
    assert respuesta.json()["complemento"]["nombre"] == nombre


def test_el_detector_no_importa_complementos_concretos():
    """Comprueba el desacoplamiento mediante análisis estático."""

    prohibidos = {
        ep.module.split(".")[0]
        for ep in entry_points(group=GRUPO)
    }

    assert prohibidos, (
        "No hay complementos instalados para comprobar"
    )

    raiz = Path(__file__).resolve().parents[1]

    for archivo in raiz.rglob("*.py"):
        relativo = archivo.relative_to(raiz)

        if any(
            parte.startswith(".")
            for parte in relativo.parts
        ):
            continue

        arbol = ast.parse(
            archivo.read_text(encoding="utf-8")
        )

        for nodo in ast.walk(arbol):
            if isinstance(nodo, ast.Import):
                modulos = [
                    alias.name for alias in nodo.names
                ]

            elif (
                isinstance(nodo, ast.ImportFrom)
                and nodo.module
                and nodo.level == 0
            ):
                modulos = [nodo.module]

            else:
                continue

            for modulo in modulos:
                assert modulo.split(".")[0] not in prohibidos, (
                    f"{relativo} importa {modulo}"
                )

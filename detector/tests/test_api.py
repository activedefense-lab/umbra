"""Pruebas de la API del detector (issue #10)."""

import re

from fastapi.testclient import TestClient

from detector.api import crear_app
from detector.modelos import Intencion
from detector.reglas import Catalogo


def _catalogo() -> Catalogo:
    return Catalogo(
        nombre="prueba",
        metacaracteres=(";", "|", "&&"),
        separadores=re.compile(r"\s*(?:;|&&|\|)\s*"),
        palabras_clave={Intencion.RECONOCIMIENTO: (re.compile(r"\balfa\b", re.I),)},
        prioridad=(Intencion.RECONOCIMIENTO,),
    )


def _cliente() -> TestClient:
    return TestClient(crear_app(_catalogo()))


def test_salud():
    r = _cliente().get("/salud")
    assert r.status_code == 200
    assert r.json()["estado"] == "ok"


def test_analizar_peticion_limpia():
    r = _cliente().post(
        "/analizar",
        json={"origen": "anon", "ruta": "/ping", "parametro": "host", "valor": "127.0.0.1"},
    )
    assert r.status_code == 200
    assert r.json()["es_ataque"] is False


def test_analizar_ataque():
    r = _cliente().post(
        "/analizar",
        json={"origen": "anon", "ruta": "/ping", "parametro": "host", "valor": "127.0.0.1;alfa"},
    )
    assert r.status_code == 200
    cuerpo = r.json()
    assert cuerpo["es_ataque"] is True
    assert cuerpo["intencion"] == "reconocimiento"


def test_peticion_invalida_devuelve_422():
    r = _cliente().post("/analizar", json={"valor": "falta todo lo demas"})
    assert r.status_code == 422

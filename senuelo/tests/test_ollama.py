"""Pruebas del cliente de Ollama sin conexiones reales.

El cliente transporta sistema → system y entrada → prompt.
"""

import json

import httpx
import pytest

from contrato.composicion import Instrucciones
from senuelo.ollama import ErrorOllama, generar


INSTRUCCIONES = Instrucciones(
    sistema="sistema de prueba",
    entrada="entrada de prueba",
)


@pytest.fixture(autouse=True)
def _ollama_de_prueba(monkeypatch):
    monkeypatch.setenv("OLLAMA_URL", "http://ollama-prueba:11434")
    monkeypatch.setenv("OLLAMA_MODELO", "llama3:latest")


def _generar(responder):
    with httpx.Client(transport=httpx.MockTransport(responder)) as cliente:
        return generar(INSTRUCCIONES, cliente=cliente)


def test_generar_respuesta_simulada():
    def responder(peticion: httpx.Request) -> httpx.Response:
        assert peticion.method == "POST"
        assert str(peticion.url) == "http://ollama-prueba:11434/api/generate"

        cuerpo = json.loads(peticion.content)

        assert cuerpo["model"] == "llama3:latest"
        assert cuerpo["stream"] is False
        assert cuerpo["system"] == "sistema de prueba"
        assert cuerpo["prompt"] == "entrada de prueba"

        return httpx.Response(
            200,
            json={
                "response": "ping: host simulado alcanzable",
                "done": True,
            },
        )

    resultado = _generar(responder)

    assert resultado.respuesta == "ping: host simulado alcanzable"
    assert resultado.modelo == "llama3:latest"
    assert resultado.latencia_ms >= 0


def test_error_si_ollama_no_esta_disponible():
    def fallar(peticion: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError(
            "Servidor no disponible",
            request=peticion,
        )

    with pytest.raises(ErrorOllama):
        _generar(fallar)


def test_error_http_de_ollama():
    with pytest.raises(ErrorOllama):
        _generar(
            lambda peticion: httpx.Response(
                500,
                json={"error": "Error interno del servidor"},
            )
        )


def test_error_si_ollama_devuelve_respuesta_vacia():
    with pytest.raises(ErrorOllama):
        _generar(
            lambda peticion: httpx.Response(
                200,
                json={"response": "", "done": True},
            )
        )


def test_error_si_ollama_devuelve_json_malformado():
    with pytest.raises(ErrorOllama):
        _generar(
            lambda peticion: httpx.Response(
                200,
                text="{respuesta_incompleta",
            )
        )
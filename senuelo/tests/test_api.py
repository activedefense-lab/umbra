"""Pruebas HTTP de la API del señuelo."""

from fastapi.testclient import TestClient

from senuelo.api import crear_app
from senuelo.modelos import RespuestaSenuelo
from senuelo.ollama import ErrorOllama


def test_salud():
    cliente = TestClient(crear_app())

    respuesta = cliente.get("/salud")

    assert respuesta.status_code == 200
    assert respuesta.json()["estado"] == "ok"


def test_generar_respuesta():
    def generador_simulado(solicitud):
        assert solicitud.intencion.value == "reconocimiento"
        return RespuestaSenuelo(
            respuesta="usuario_simulado",
            modelo="modelo-prueba",
            latencia_ms=12.5,
        )

    cliente = TestClient(crear_app(generador_simulado))

    respuesta = cliente.post(
        "/generar",
        json={
            "intencion": "reconocimiento",
            "segmentos": ["whoami"],
            "valor_normalizado": "whoami",
        },
    )

    assert respuesta.status_code == 200
    assert respuesta.json() == {
        "respuesta": "usuario_simulado",
        "modelo": "modelo-prueba",
        "latencia_ms": 12.5,
    }


def test_generar_devuelve_503_si_ollama_falla():
    def generador_fallido(solicitud):
        raise ErrorOllama("Servidor no disponible")

    cliente = TestClient(crear_app(generador_fallido))

    respuesta = cliente.post(
        "/generar",
        json={
            "intencion": "desconocida",
            "segmentos": [],
            "valor_normalizado": "entrada de prueba",
        },
    )

    assert respuesta.status_code == 503
    assert respuesta.json()["detail"] == (
        "Generador de señuelo no disponible"
    )

def test_generar_rechaza_segmento_demasiado_largo():
    def generador_no_debe_ejecutarse(solicitud):
        raise AssertionError("El generador no debe recibir entradas inválidas")

    cliente = TestClient(crear_app(generador_no_debe_ejecutarse))

    respuesta = cliente.post(
        "/generar",
        json={
            "intencion": "reconocimiento",
            "segmentos": ["A" * 4097],
            "valor_normalizado": "entrada de prueba",
        },
    )

    assert respuesta.status_code == 422
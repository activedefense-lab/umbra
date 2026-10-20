"""Pruebas del cliente de Ollama sin conexiones reales."""

import httpx

from senuelo.modelos import Intencion, SolicitudSenuelo
from senuelo.ollama import generar


def test_generar_respuesta_simulada(monkeypatch):
    monkeypatch.setenv("OLLAMA_URL", "http://ollama-prueba:11434")
    monkeypatch.setenv("OLLAMA_MODELO", "llama3:latest")

    def responder(peticion: httpx.Request) -> httpx.Response:
        assert peticion.method == "POST"
        assert str(peticion.url) == "http://ollama-prueba:11434/api/generate"

        cuerpo = __import__("json").loads(peticion.content)
        assert cuerpo["model"] == "llama3:latest"
        assert cuerpo["stream"] is False
        assert "system" in cuerpo
        assert "prompt" in cuerpo

        return httpx.Response(
            200,
            json={"response": "ping: host simulado alcanzable", "done": True},
        )

    transporte = httpx.MockTransport(responder)

    solicitud = SolicitudSenuelo(
        intencion=Intencion.RECONOCIMIENTO,
        segmentos=["ping -c 1 ejemplo.local"],
        valor_normalizado="ping -c 1 ejemplo.local",
    )

    with httpx.Client(transport=transporte) as cliente:
        resultado = generar(solicitud, cliente=cliente)

    assert resultado.respuesta == "ping: host simulado alcanzable"
    assert resultado.modelo == "llama3:latest"
    assert resultado.latencia_ms >= 0


def test_error_si_ollama_no_esta_disponible(monkeypatch):
    """Un fallo de conexión debe convertirse en ErrorOllama."""
    import pytest

    from senuelo.ollama import ErrorOllama

    monkeypatch.setenv("OLLAMA_URL", "http://ollama-prueba:11434")

    def fallar(peticion: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError(
            "Servidor no disponible",
            request=peticion,
        )

    solicitud = SolicitudSenuelo(
        intencion=Intencion.DESCONOCIDA,
        segmentos=[],
        valor_normalizado="entrada de prueba",
    )

    with httpx.Client(transport=httpx.MockTransport(fallar)) as cliente:
        with pytest.raises(ErrorOllama):
            generar(solicitud, cliente=cliente)


def test_error_http_de_ollama(monkeypatch):
    """Una respuesta HTTP 500 debe convertirse en ErrorOllama."""
    import pytest

    from senuelo.ollama import ErrorOllama

    monkeypatch.setenv("OLLAMA_URL", "http://ollama-prueba:11434")

    def responder(peticion: httpx.Request) -> httpx.Response:
        return httpx.Response(
            500,
            json={"error": "Error interno del servidor"},
        )

    solicitud = SolicitudSenuelo(
        intencion=Intencion.RECONOCIMIENTO,
        segmentos=["whoami"],
        valor_normalizado="whoami",
    )

    with httpx.Client(transport=httpx.MockTransport(responder)) as cliente:
        with pytest.raises(ErrorOllama):
            generar(solicitud, cliente=cliente)


def test_error_si_ollama_devuelve_respuesta_vacia(monkeypatch):
    """Una respuesta HTTP exitosa sin texto debe rechazarse."""
    import pytest

    from senuelo.ollama import ErrorOllama

    monkeypatch.setenv("OLLAMA_URL", "http://ollama-prueba:11434")

    def responder(peticion: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"response": "", "done": True},
        )

    solicitud = SolicitudSenuelo(
        intencion=Intencion.DESCONOCIDA,
        segmentos=[],
        valor_normalizado="entrada de prueba",
    )

    with httpx.Client(transport=httpx.MockTransport(responder)) as cliente:
        with pytest.raises(ErrorOllama):
            generar(solicitud, cliente=cliente)


def test_error_si_ollama_devuelve_json_malformado(monkeypatch):
    """Una respuesta que no sea JSON válido debe producir ErrorOllama."""
    import pytest

    from senuelo.ollama import ErrorOllama

    monkeypatch.setenv("OLLAMA_URL", "http://ollama-prueba:11434")

    def responder(peticion: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            text="{respuesta_incompleta",
        )

    solicitud = SolicitudSenuelo(
        intencion=Intencion.DESCONOCIDA,
        segmentos=[],
        valor_normalizado="entrada de prueba",
    )

    with httpx.Client(transport=httpx.MockTransport(responder)) as cliente:
        with pytest.raises(ErrorOllama):
            generar(solicitud, cliente=cliente)

"""Pruebas del cliente de Ollama sin conexiones reales.

El cliente transporta sistema → system y entrada → prompt.
"""

import json

import httpx
import pytest

from contrato.composicion import Instrucciones
from senuelo import ollama
from senuelo.ollama import Configuracion, ErrorOllama, calentar, generar, modelo_cargado


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

# ------------------------------------------------ configuración y tiempos (umbra#15)


def _cuerpo_enviado():
    enviados = []

    def responder(peticion: httpx.Request) -> httpx.Response:
        enviados.append(json.loads(peticion.content))
        return httpx.Response(200, json={"response": "ok", "done": True})

    resultado = _generar(responder)
    return enviados[0], resultado


def test_keep_alive_por_defecto_es_30_minutos(monkeypatch):
    monkeypatch.delenv("OLLAMA_KEEP_ALIVE", raising=False)

    cuerpo, _ = _cuerpo_enviado()

    assert cuerpo["keep_alive"] == "30m"


@pytest.mark.parametrize(
    ("crudo", "enviado"),
    [("-1", -1), ("600", 600), ("2h", "2h"), ("1h30m", "1h30m"), ("1.5h", "1.5h"), (" 30m ", "30m")],
)
def test_keep_alive_entero_se_envia_como_numero(monkeypatch, crudo, enviado):
    # Ollama rechaza el texto "-1" (duración sin unidad); el número -1 = indefinido.
    monkeypatch.setenv("OLLAMA_KEEP_ALIVE", crudo)

    cuerpo, _ = _cuerpo_enviado()

    assert cuerpo["keep_alive"] == enviado


def test_temperatura_registrada_es_la_enviada():
    cuerpo, resultado = _cuerpo_enviado()

    assert resultado.temperatura == cuerpo["options"]["temperature"]


def test_configuracion_por_defecto(monkeypatch):
    for variable in ("OLLAMA_TIMEOUT", "OLLAMA_TIMEOUT_CALENTAMIENTO", "OLLAMA_KEEP_ALIVE"):
        monkeypatch.delenv(variable, raising=False)

    config = Configuracion.desde_entorno()

    assert config.timeout == 20.0
    assert config.timeout_calentamiento == 90.0
    assert config.keep_alive == "30m"
    # El calentamiento tolera el arranque en frío; la generación ordinaria no.
    assert config.timeout_calentamiento > config.timeout


@pytest.mark.parametrize("crudo", ["abc", "0", "-5", "nan", "inf", "-inf"])
def test_timeout_invalido_es_error_de_configuracion(monkeypatch, crudo):
    monkeypatch.setenv("OLLAMA_TIMEOUT", crudo)

    with pytest.raises(ValueError, match="OLLAMA_TIMEOUT"):
        Configuracion.desde_entorno()


class _ClienteEspia:
    """Sustituye a httpx.Client para observar el tiempo de espera configurado."""

    timeouts: list[float] = []

    def __init__(self, *, timeout):
        _ClienteEspia.timeouts.append(timeout)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def post(self, url, json):
        return httpx.Response(200, json={"response": "ok", "done": True}, request=httpx.Request("POST", url))

    def get(self, url):
        return httpx.Response(200, json={"models": []}, request=httpx.Request("GET", url))


@pytest.fixture
def espia(monkeypatch):
    _ClienteEspia.timeouts = []
    monkeypatch.setattr(ollama.httpx, "Client", _ClienteEspia)
    return _ClienteEspia


def test_generar_usa_ollama_timeout(monkeypatch, espia):
    monkeypatch.setenv("OLLAMA_TIMEOUT", "7")

    generar(INSTRUCCIONES)

    assert espia.timeouts == [7.0]


def test_calentar_usa_su_propio_timeout(monkeypatch, espia):
    monkeypatch.setenv("OLLAMA_TIMEOUT", "7")
    monkeypatch.setenv("OLLAMA_TIMEOUT_CALENTAMIENTO", "45")

    calentar()

    assert espia.timeouts == [45.0]


def test_consulta_de_modelos_usa_timeout_corto(espia):
    modelo_cargado()

    assert espia.timeouts == [ollama.TIMEOUT_CONSULTA]


# ------------------------------------------------------------------ calentamiento


def test_calentar_genera_un_token_con_keep_alive(monkeypatch):
    monkeypatch.setenv("OLLAMA_KEEP_ALIVE", "-1")
    enviados = []

    def responder(peticion: httpx.Request) -> httpx.Response:
        assert str(peticion.url) == "http://ollama-prueba:11434/api/generate"
        enviados.append(json.loads(peticion.content))
        return httpx.Response(200, json={"response": "ok", "done": True})

    with httpx.Client(transport=httpx.MockTransport(responder)) as cliente:
        duracion = calentar(cliente=cliente)

    (cuerpo,) = enviados
    assert cuerpo["model"] == "llama3:latest"
    assert cuerpo["options"]["num_predict"] == 1
    assert cuerpo["keep_alive"] == -1
    assert duracion >= 0


def test_calentar_falla_con_error_controlado():
    def fallar(peticion: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("sin servidor", request=peticion)

    with httpx.Client(transport=httpx.MockTransport(fallar)) as cliente:
        with pytest.raises(ErrorOllama):
            calentar(cliente=cliente)


# --------------------------------------------------- modelo cargado (/api/ps)


def _cargado(responder) -> bool:
    with httpx.Client(transport=httpx.MockTransport(responder)) as cliente:
        return modelo_cargado(cliente=cliente)


def test_modelo_cargado_consulta_api_ps():
    def responder(peticion: httpx.Request) -> httpx.Response:
        assert peticion.method == "GET"
        assert str(peticion.url) == "http://ollama-prueba:11434/api/ps"
        return httpx.Response(200, json={"models": [{"name": "llama3:latest"}]})

    assert _cargado(responder) is True


def test_modelo_sin_etiqueta_equivale_a_latest(monkeypatch):
    monkeypatch.setenv("OLLAMA_MODELO", "llama3")

    assert _cargado(lambda p: httpx.Response(200, json={"models": [{"name": "llama3:latest"}]}))


def test_modelo_no_cargado():
    assert _cargado(lambda p: httpx.Response(200, json={"models": []})) is False
    assert _cargado(
        lambda p: httpx.Response(200, json={"models": [{"name": "otro:latest"}]})
    ) is False


@pytest.mark.parametrize(
    "responder",
    [
        pytest.param(lambda p: httpx.Response(500), id="error-http"),
        pytest.param(lambda p: httpx.Response(200, json={"sin": "modelos"}), id="sin-lista"),
        pytest.param(lambda p: httpx.Response(200, text="{roto"), id="json-malformado"),
    ],
)
def test_consulta_invalida_es_error_controlado(responder):
    with pytest.raises(ErrorOllama):
        _cargado(responder)


@pytest.mark.parametrize("crudo", ["incorrecto", "30 minutos", "m", "-1x", "1.h"])
def test_keep_alive_invalido_es_error_de_configuracion(monkeypatch, crudo):
    monkeypatch.setenv("OLLAMA_KEEP_ALIVE", crudo)

    with pytest.raises(ValueError, match="OLLAMA_KEEP_ALIVE"):
        Configuracion.desde_entorno()


@pytest.mark.parametrize("texto", ["", " ", "\n"])
def test_calentar_acepta_respuesta_sin_texto(texto):
    # Con un token el modelo puede no producir texto visible: igual quedó cargado.
    respuesta = lambda p: httpx.Response(200, json={"response": texto, "done": True})

    with httpx.Client(transport=httpx.MockTransport(respuesta)) as cliente:
        assert calentar(cliente=cliente) >= 0


@pytest.mark.parametrize(
    "cuerpo",
    [
        pytest.param({"response": "ok", "done": False}, id="done-falso"),
        pytest.param({"response": "ok"}, id="sin-done"),
    ],
)
def test_calentar_exige_generacion_terminada(cuerpo):
    # Respuesta real de Ollama 0.40.3 (27 nov 2026): "done": true, "done_reason": "length".
    respuesta = lambda p: httpx.Response(200, json=cuerpo)

    with httpx.Client(transport=httpx.MockTransport(respuesta)) as cliente:
        with pytest.raises(ErrorOllama):
            calentar(cliente=cliente)

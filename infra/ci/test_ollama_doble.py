"""Pruebas del doble de Ollama: fidelidad al contrato capturado y validación.

Si el doble respondiera 200 a todo, el CI quedaría en verde con peticiones
incorrectas. Estas pruebas lo impiden.
"""

from __future__ import annotations

import json
import sys
import threading
from pathlib import Path

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).parent))
from ollama_doble import CONTRATO, TEXTO_FIJO, crear_servidor  # noqa: E402

VALIDA = {"model": "llama3:latest", "prompt": "ok", "stream": False, "keep_alive": "30m",
          "options": {"temperature": 0.3, "num_predict": 128}}


@pytest.fixture
def doble():
    servidor = crear_servidor("127.0.0.1", 0, "llama3:latest")
    hilo = threading.Thread(target=servidor.serve_forever, daemon=True)
    hilo.start()
    url = f"http://127.0.0.1:{servidor.server_address[1]}"
    yield url, servidor
    servidor.shutdown()


def test_generate_reproduce_el_contrato_real(doble):
    url, _ = doble
    r = httpx.post(f"{url}/api/generate", json=VALIDA)

    assert r.status_code == 200
    cuerpo = r.json()
    assert set(cuerpo) == set(CONTRATO["generate"])  # mismos campos que Ollama 0.40.3
    assert cuerpo["done"] is True and cuerpo["done_reason"] == "length"
    assert cuerpo["response"] == TEXTO_FIJO and cuerpo["model"] == "llama3:latest"


def test_ps_vacio_hasta_la_primera_generacion_y_con_los_campos_reales_despues(doble):
    url, _ = doble
    assert httpx.get(f"{url}/api/ps").json() == {"models": []}

    httpx.post(f"{url}/api/generate", json=VALIDA)
    (modelo,) = httpx.get(f"{url}/api/ps").json()["models"]

    assert set(modelo) == set(CONTRATO["ps_modelo"])
    assert modelo["name"] == "llama3:latest"


def test_version_identifica_al_doble(doble):
    # El CI comprueba esta marca: si otro proceso ocupara el puerto, se notaría.
    url, _ = doble
    assert "doble de prueba" in httpx.get(f"{url}/api/version").json()["version"]


def test_modelo_inexistente_con_el_mensaje_real(doble):
    url, _ = doble
    r = httpx.post(f"{url}/api/generate", json={**VALIDA, "model": "no-existe:latest"})

    assert r.status_code == 404
    assert r.json() == CONTRATO["errores"]["modelo_inexistente"]["cuerpo"]


def test_json_invalido_es_400(doble):
    url, _ = doble
    r = httpx.post(f"{url}/api/generate", content=b"{roto")

    assert r.status_code == 400 and set(r.json()) == {"error"}


@pytest.mark.parametrize(
    "cambio",
    [
        pytest.param({"keep_alive": None}, id="sin-keep_alive"),
        pytest.param({"keep_alive": "incorrecto"}, id="keep_alive-invalido"),
        pytest.param({"stream": True}, id="stream-true"),
        pytest.param({"prompt": None}, id="sin-prompt"),
        pytest.param({"system": 3}, id="system-no-texto"),
        pytest.param({"options": {"num_predict": 0}}, id="num_predict-cero"),
        pytest.param({"options": {"temperature": 0.3}}, id="sin-num_predict"),
        pytest.param({"options": None}, id="sin-options"),
    ],
)
def test_rechaza_peticiones_que_arya_no_deberia_enviar(doble, cambio):
    url, servidor = doble
    cuerpo = {**VALIDA, **cambio}
    cuerpo = {k: v for k, v in cuerpo.items() if v is not None}

    r = httpx.post(f"{url}/api/generate", content=json.dumps(cuerpo))

    assert r.status_code == 400
    assert servidor.estado["cargado"] is False  # una petición rechazada no "carga" el modelo


@pytest.mark.parametrize("keep_alive", [-1, 1800, "30m", "1h30m"])
def test_acepta_los_keep_alive_que_envia_el_senuelo(doble, keep_alive):
    url, _ = doble
    assert httpx.post(f"{url}/api/generate", json={**VALIDA, "keep_alive": keep_alive}).status_code == 200

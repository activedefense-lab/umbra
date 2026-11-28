"""Disponibilidad del señuelo: /salud (liveness), /listo (readiness) y calentamiento.

umbra#15. Los criterios vienen de la revisión del PR con el auditor externo:
el calentamiento no bloquea el arranque, /listo refleja el estado actual
(no recuerda el calentamiento) y /salud no depende de Ollama.
"""

import threading

from fastapi.testclient import TestClient

from falsos import Falso
from senuelo.api import EstadoCalentamiento, crear_app, ejecutar_calentamiento
from senuelo.modelos import RespuestaSenuelo
from senuelo.ollama import ErrorOllama


RESPUESTA = RespuestaSenuelo(respuesta="x", modelo="m", latencia_ms=1.0, temperatura=0.3)
ESPERA = 5  # segundos; solo para no colgar la suite si algo falla


def _app(*, calentador=None, consultor=lambda: True):
    return crear_app(
        Falso(),
        lambda instrucciones: RESPUESTA,
        calentador=calentador,
        consultor=consultor,
    )


def _ollama_caido():
    raise ErrorOllama("sin servidor")


# ---------------------------------------------------------------------- /salud


def test_salud_no_depende_de_ollama():
    with TestClient(_app(calentador=_ollama_caido, consultor=_ollama_caido)) as cliente:
        respuesta = cliente.get("/salud")

    assert respuesta.status_code == 200
    assert respuesta.json()["estado"] == "ok"


# --------------------------------------------------------------------- arranque


def test_el_calentamiento_no_bloquea_el_arranque():
    empezo, liberar = threading.Event(), threading.Event()

    def calentador_lento():
        empezo.set()
        assert liberar.wait(ESPERA)
        return 1.0

    app = _app(calentador=calentador_lento)
    with TestClient(app) as cliente:
        assert empezo.wait(ESPERA)
        # Con el calentamiento todavía en curso, el servicio ya responde.
        assert cliente.get("/salud").status_code == 200
        listo = cliente.get("/listo")
        assert listo.status_code == 503
        assert listo.json()["motivo"] == "calentamiento en curso"
        liberar.set()


def test_arranca_aunque_ollama_no_este_disponible():
    termino = threading.Event()

    def calentador_fallido():
        try:
            _ollama_caido()
        finally:
            termino.set()

    app = _app(calentador=calentador_fallido, consultor=_ollama_caido)
    with TestClient(app) as cliente:
        assert termino.wait(ESPERA)
        assert cliente.get("/salud").status_code == 200
        listo = cliente.get("/listo")

    assert listo.status_code == 503
    assert listo.json()["motivo"] == "Ollama no disponible"


def test_estado_del_calentamiento():
    estado = EstadoCalentamiento()
    ejecutar_calentamiento(estado, lambda: 1234.0)
    assert estado.instantanea() == {"estado": "completado", "detalle": "1234 ms"}

    ejecutar_calentamiento(estado, _ollama_caido)
    assert estado.instantanea()["estado"] == "fallido"


def test_error_inesperado_no_rompe_el_hilo():
    estado = EstadoCalentamiento()

    def roto():
        raise RuntimeError("fallo no previsto")

    ejecutar_calentamiento(estado, roto)

    assert estado.instantanea()["estado"] == "fallido"


# ---------------------------------------------------------------------- /listo


def test_listo_cuando_el_modelo_esta_cargado():
    respuesta = TestClient(_app(consultor=lambda: True)).get("/listo")

    assert respuesta.status_code == 200
    assert respuesta.json()["listo"] is True


def test_listo_detecta_que_el_modelo_se_descargo():
    # El calentamiento terminó bien, pero ahora el modelo ya no está en memoria
    # (p. ej. venció keep_alive): /listo consulta el estado actual.
    cargado = {"valor": True}
    app = _app(calentador=lambda: 1.0, consultor=lambda: cargado["valor"])

    with TestClient(app) as cliente:
        estado = app.state.calentamiento
        for _ in range(100):
            if estado.instantanea()["estado"] == "completado":
                break
            threading.Event().wait(0.05)
        assert cliente.get("/listo").status_code == 200

        cargado["valor"] = False
        respuesta = cliente.get("/listo")

    assert respuesta.status_code == 503
    assert respuesta.json()["motivo"] == "modelo no cargado en memoria"
    assert respuesta.json()["calentamiento"]["estado"] == "completado"


def test_listo_cuando_ollama_no_responde():
    respuesta = TestClient(_app(consultor=_ollama_caido)).get("/listo")

    assert respuesta.status_code == 503
    assert respuesta.json()["motivo"] == "Ollama no disponible"


def test_listo_informa_el_modelo_configurado(monkeypatch):
    monkeypatch.setenv("OLLAMA_MODELO", "modelo-de-prueba:1b")

    respuesta = TestClient(_app()).get("/listo")

    assert respuesta.json()["modelo"] == "modelo-de-prueba:1b"

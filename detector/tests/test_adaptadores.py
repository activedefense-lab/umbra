"""Pruebas de los adaptadores reales de /interceptar: cliente del señuelo y registro.

Sin servicios reales: el señuelo se simula con httpx.MockTransport y el
registro apunta a un puerto sin PostgreSQL para verificar el fallo controlado.
"""

import json

import httpx
import pytest

from contrato.modelos import SolicitudSenuelo
from detector.api import crear_app
from detector import interceptacion
from detector.interceptacion import ErrorRegistro, ErrorSenuelo, cliente_senuelo, registro_postgres
from falsos import Falso


SOLICITUD = SolicitudSenuelo(complemento="falso", intencion="intencion_a", valor_normalizado="x;id",
                             evidencia={"pistas": [";"]})
CUERPO_OK = {"respuesta": "uid=33(www-data)", "modelo": "llama3:latest", "latencia_ms": 241.1, "temperatura": 0.3}


def _cliente(responder):
    return cliente_senuelo("http://senuelo:8002/", 7, transporte=httpx.MockTransport(responder))


# -------------------------------------------------------------------- señuelo


def test_envia_la_solicitud_a_generar_y_lee_la_respuesta():
    recibidas = []

    def responder(peticion):
        recibidas.append(peticion)
        return httpx.Response(200, json=CUERPO_OK)

    generada = _cliente(responder)(SOLICITUD)

    (peticion,) = recibidas
    assert peticion.method == "POST" and str(peticion.url) == "http://senuelo:8002/generar"
    assert json.loads(peticion.content) == SOLICITUD.model_dump(mode="json")
    assert (generada.respuesta, generada.modelo, generada.temperatura) == ("uid=33(www-data)", "llama3:latest", 0.3)


def test_temperatura_ausente_no_bloquea():
    cuerpo = {k: v for k, v in CUERPO_OK.items() if k != "temperatura"}

    assert _cliente(lambda p: httpx.Response(200, json=cuerpo))(SOLICITUD).temperatura is None


@pytest.mark.parametrize(
    ("responder", "motivo"),
    [
        pytest.param(lambda p: httpx.Response(503, json={"detail": "x"}), "HTTP 503", id="error-http"),
        pytest.param(lambda p: (_ for _ in ()).throw(httpx.ConnectError("x", request=p)), "sin conexión",
                     id="sin-conexion"),
        pytest.param(lambda p: (_ for _ in ()).throw(httpx.ReadTimeout("x", request=p)), "tiempo agotado (7 s)",
                     id="tiempo-agotado"),
        pytest.param(lambda p: httpx.Response(200, text="{roto"), "respuesta inválida", id="json-malformado"),
        pytest.param(lambda p: httpx.Response(200, json={**CUERPO_OK, "respuesta": ""}), "respuesta inválida",
                     id="respuesta-vacia"),
        pytest.param(lambda p: httpx.Response(200, json={"respuesta": "x"}), "respuesta inválida",
                     id="faltan-campos"),
    ],
)
def test_todo_fallo_del_senuelo_es_error_controlado(responder, motivo):
    with pytest.raises(ErrorSenuelo, match=motivo.replace("(", r"\(").replace(")", r"\)")):
        _cliente(responder)(SOLICITUD)


def test_timeout_por_defecto_y_desde_el_entorno(monkeypatch):
    monkeypatch.delenv("UMBRA_SENUELO_TIMEOUT", raising=False)
    assert cliente_senuelo().timeout == 25.0

    monkeypatch.setenv("UMBRA_SENUELO_TIMEOUT", "12")
    assert cliente_senuelo().timeout == 12.0


@pytest.mark.parametrize("crudo", ["abc", "0", "-1", "nan", "inf"])
def test_timeout_invalido_impide_arrancar(monkeypatch, crudo):
    monkeypatch.setenv("UMBRA_SENUELO_TIMEOUT", crudo)

    with pytest.raises(ValueError, match="UMBRA_SENUELO_TIMEOUT"):
        crear_app(Falso())


# ------------------------------------------------------------------- registro


def test_postgres_no_disponible_es_error_controlado():
    # Puerto 1 en localhost: sin servidor; la conexión se rechaza de inmediato.
    abrir = registro_postgres("postgresql://umbra:x@127.0.0.1:1/umbra_registro")

    with pytest.raises(ErrorRegistro, match="PostgreSQL no disponible"):
        with abrir():
            pass


def test_crear_la_app_no_conecta_al_registro():
    # Arrancar sin PostgreSQL debe funcionar: la conexión se abre por interceptación.
    crear_app(Falso(), abrir_registro=registro_postgres("postgresql://umbra:x@127.0.0.1:1/x"))


def test_cada_sentencia_tiene_limite_de_tiempo(monkeypatch):
    llamadas = []

    class ConexionFalsa:
        def close(self):
            pass

    def conectar(cadena, **opciones):
        llamadas.append(opciones)
        return ConexionFalsa()

    monkeypatch.setattr(interceptacion.psycopg, "connect", conectar)

    with registro_postgres("postgresql://x")():
        pass

    (opciones,) = llamadas
    assert opciones["connect_timeout"] == 3
    assert opciones["options"] == "-c statement_timeout=3000"

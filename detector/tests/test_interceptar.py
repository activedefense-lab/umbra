"""Pruebas unitarias de POST /interceptar (ADR-003 y precisiones de implementación).

El señuelo y el registro son dobles de prueba: estas pruebas verifican la
lógica del detector (decisión, orden y contenido de los eventos, límites,
fallo cerrado). La integración con el señuelo, Ollama y PostgreSQL reales la
verifican las pruebas de Santiago en infra/pruebas/test_interceptar.py.
"""

import hashlib

import pytest
from pydantic import ValidationError

from contrato.modelos import Veredicto
from fastapi.testclient import TestClient

from detector.api import crear_app
from detector.interceptacion import (
    MAX_BYTES_REGISTRO,
    MAX_CARACTERES_SENUELO,
    ErrorSenuelo,
    RespuestaGenerada,
    recortar_bytes,
)
from falsos import Falso
from registro_simulado import RegistroSimulado


BENIGNA = {"origen": "a" * 64, "ruta": "/api/lab/connectivity-check", "parametro": "host", "valor": "127.0.0.1"}
ATAQUE = {**BENIGNA, "valor": "127.0.0.1;id"}
GENERADA = RespuestaGenerada(respuesta="uid=33(www-data)", modelo="modelo-prueba", latencia_ms=12.5, temperatura=0.3)


class SenueloSimulado:
    def __init__(self, *, error: str | None = None) -> None:
        self.error = error
        self.solicitudes = []

    def __call__(self, solicitud):
        self.solicitudes.append(solicitud)
        if self.error:
            raise ErrorSenuelo(self.error)
        return GENERADA


class ComplementoEspia(Falso):
    """Falso que además recuerda la petición que recibió."""

    def analizar(self, peticion):
        self.recibida = peticion
        return super().analizar(peticion)


def _montar(*, senuelo=None, registro=None, complemento=None):
    senuelo = senuelo or SenueloSimulado()
    registro = registro or RegistroSimulado()
    app = crear_app(complemento or Falso(), generar_senuelo=senuelo, abrir_registro=registro)
    return TestClient(app), senuelo, registro


def _interceptar(cuerpo, **kwargs):
    cliente, senuelo, registro = _montar(**kwargs)
    return cliente.post("/interceptar", json=cuerpo), senuelo, registro


# ------------------------------------------------------------------ decisión


def test_benigna_permite_sin_sesion_ni_senuelo():
    respuesta, senuelo, registro = _interceptar(BENIGNA)

    assert respuesta.status_code == 200
    assert respuesta.json() == {"accion": "permitir", "respuesta": "", "sesion_id": None}
    assert registro.aperturas == 0 and registro.sesiones == {}
    assert senuelo.solicitudes == []


def test_ataque_devuelve_senuelo_con_la_sesion_registrada():
    respuesta, senuelo, registro = _interceptar(ATAQUE)

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    sesion_id, sesion = registro.unica()
    assert cuerpo == {"accion": "senuelo", "respuesta": "uid=33(www-data)", "sesion_id": str(sesion_id)}

    assert (sesion.origen, sesion.ruta, sesion.parametro) == (ATAQUE["origen"], ATAQUE["ruta"], ATAQUE["parametro"])
    assert sesion.cerrada and sesion.intencion_final == "intencion_a"
    assert [(paso, tipo) for paso, tipo, _ in sesion.eventos] == [
        (2, "peticion_recibida"),
        (3, "veredicto"),
        (4, "respuesta_senuelo"),
    ]


def test_contenido_de_los_eventos():
    _, _, registro = _interceptar(ATAQUE)
    _, sesion = registro.unica()
    (_, _, e2), (_, _, e3), (_, _, e4) = sesion.eventos

    assert e2["ruta"] == ATAQUE["ruta"] and e2["parametro"] == "host"
    assert e2["valor"] == "127.0.0.1;id" and e2["valor_truncado"] is False
    assert e2["sha256"] == hashlib.sha256(b"127.0.0.1;id").hexdigest()
    assert (e2["longitud_caracteres"], e2["longitud_bytes"]) == (12, 12)

    assert e3 == {
        "complemento": "falso", "intencion": "intencion_a", "confianza": 1.0,
        "evidencia": {"pistas": [";"]}, "valor_senuelo_truncado": False,
    }

    assert e4["respuesta"] == "uid=33(www-data)"
    assert (e4["modelo"], e4["temperatura"], e4["latencia_ms"]) == ("modelo-prueba", 0.3, 12.5)
    assert e4["duracion_ms"] >= 0


def test_solicitud_enviada_al_senuelo():
    _, senuelo, _ = _interceptar(ATAQUE)

    (solicitud,) = senuelo.solicitudes
    assert solicitud.complemento == "falso"
    assert solicitud.intencion == "intencion_a"
    assert solicitud.valor_normalizado == "127.0.0.1;id"
    assert solicitud.evidencia == {"pistas": [";"]}


def test_la_respuesta_al_atacante_no_trae_datos_forenses():
    respuesta, _, _ = _interceptar(ATAQUE)

    assert set(respuesta.json()) == {"accion", "respuesta", "sesion_id"}


# ------------------------------------------------------------------ límites


def test_inyeccion_escondida_despues_de_4096_se_detecta():
    # El detector analiza la carga completa; solo el contexto del señuelo se recorta.
    espia = ComplementoEspia()
    valor = "A" * 5000 + ";id"

    respuesta, senuelo, registro = _interceptar({**BENIGNA, "valor": valor}, complemento=espia)

    assert len(espia.recibida.valor) == 5003
    assert respuesta.json()["accion"] == "senuelo"
    (solicitud,) = senuelo.solicitudes
    assert len(solicitud.valor_normalizado) == MAX_CARACTERES_SENUELO
    _, sesion = registro.unica()
    (_, _, e2), (_, _, e3), _ = sesion.eventos
    assert e3["valor_senuelo_truncado"] is True
    assert e2["valor"] == valor and e2["valor_truncado"] is False  # 5003 bytes < 64 KB


def test_el_limite_del_senuelo_se_cuenta_en_caracteres():
    valor = ";" + "ñ" * (MAX_CARACTERES_SENUELO + 10)  # 2 bytes por carácter

    _, senuelo, _ = _interceptar({**BENIGNA, "valor": valor})

    (solicitud,) = senuelo.solicitudes
    assert len(solicitud.valor_normalizado) == MAX_CARACTERES_SENUELO


def test_carga_mayor_a_64_kb_se_recorta_en_el_registro_con_hash_de_la_completa():
    valor = ";" + "B" * (MAX_BYTES_REGISTRO + 1000)

    respuesta, _, registro = _interceptar({**BENIGNA, "valor": valor})

    assert respuesta.status_code == 200
    _, sesion = registro.unica()
    e2 = sesion.eventos[0][2]
    assert e2["valor_truncado"] is True
    assert len(e2["valor"].encode("utf-8")) == MAX_BYTES_REGISTRO
    assert e2["longitud_bytes"] == len(valor)
    assert e2["sha256"] == hashlib.sha256(valor.encode("utf-8")).hexdigest()


def test_el_recorte_por_bytes_no_parte_caracteres():
    texto = "ñ" * 40_000  # 80 000 bytes

    recortado, truncado = recortar_bytes(texto, MAX_BYTES_REGISTRO)

    assert truncado is True
    assert set(recortado) == {"ñ"}
    assert len(recortado.encode("utf-8")) == MAX_BYTES_REGISTRO  # 32 768 caracteres completos


def test_el_recorte_impar_descarta_el_caracter_incompleto():
    recortado, _ = recortar_bytes("ñ" * 10, 5)

    assert recortado == "ññ"


# ------------------------------------------------------------- fallo cerrado


def test_senuelo_caido_registra_error_cierra_y_bloquea():
    respuesta, _, registro = _interceptar(ATAQUE, senuelo=SenueloSimulado(error="tiempo agotado (25 s)"))

    assert respuesta.status_code == 503
    _, sesion = registro.unica()
    assert [(paso, tipo) for paso, tipo, _ in sesion.eventos] == [
        (2, "peticion_recibida"),
        (3, "veredicto"),
        (4, "error_senuelo"),
    ]
    assert sesion.eventos[2][2]["motivo"] == "tiempo agotado (25 s)"
    assert sesion.cerrada


def test_registro_caido_bloquea_sin_llamar_al_senuelo():
    respuesta, senuelo, registro = _interceptar(ATAQUE, registro=RegistroSimulado(fallar_en="conectar"))

    assert respuesta.status_code == 503
    assert senuelo.solicitudes == [] and registro.sesiones == {}


@pytest.mark.parametrize("fallo", ["abrir_sesion", "peticion_recibida", "veredicto"])
def test_fallo_del_registro_antes_del_senuelo_bloquea_sin_generar(fallo):
    respuesta, senuelo, registro = _interceptar(ATAQUE, registro=RegistroSimulado(fallar_en=fallo))

    assert respuesta.status_code == 503
    assert senuelo.solicitudes == []
    # Fallo parcial: lo ya escrito queda, sin cierre (no se puede cerrar si el registro falla).
    assert all(not s.cerrada for s in registro.sesiones.values())


@pytest.mark.parametrize("fallo", ["respuesta_senuelo", "cerrar_sesion"])
def test_fallo_del_registro_despues_del_senuelo_tambien_bloquea(fallo):
    # Fallo cerrado: un engaño que no quedó registrado no se entrega.
    respuesta, senuelo, registro = _interceptar(ATAQUE, registro=RegistroSimulado(fallar_en=fallo))

    assert respuesta.status_code == 503
    assert len(senuelo.solicitudes) == 1
    _, sesion = registro.unica()
    assert not sesion.cerrada


def test_fallo_del_registro_al_anotar_el_error_del_senuelo_bloquea():
    respuesta, _, registro = _interceptar(
        ATAQUE, senuelo=SenueloSimulado(error="HTTP 503"), registro=RegistroSimulado(fallar_en="error_senuelo")
    )

    assert respuesta.status_code == 503
    _, sesion = registro.unica()
    assert not sesion.cerrada


def test_el_503_no_revela_detalles_internos():
    respuesta, _, _ = _interceptar(ATAQUE, senuelo=SenueloSimulado(error="sin conexión: ConnectError"))

    assert "ConnectError" not in respuesta.text and "senuelo" not in respuesta.text.lower()


# ------------------------------------------------------- contrato y /analizar


@pytest.mark.parametrize(
    "cuerpo",
    [{**BENIGNA, "metodo": "POST"}, {k: v for k, v in BENIGNA.items() if k != "valor"}],
    ids=["campo-adicional", "falta-valor"],
)
def test_contrato_peticion_se_aplica_en_interceptar(cuerpo):
    respuesta, senuelo, registro = _interceptar(cuerpo)

    assert respuesta.status_code == 422
    assert registro.aperturas == 0 and senuelo.solicitudes == []


def test_analizar_sigue_devolviendo_el_veredicto_sin_tocar_senuelo_ni_registro():
    cliente, senuelo, registro = _montar()

    respuesta = cliente.post("/analizar", json=ATAQUE)

    assert respuesta.status_code == 200
    assert respuesta.json()["es_ataque"] is True and "accion" not in respuesta.json()
    assert registro.aperturas == 0 and senuelo.solicitudes == []


class VeredictoSinValidar(Falso):
    """Complemento defectuoso: crea el veredicto sin validación (model_construct)."""

    def analizar(self, peticion):
        return Veredicto.model_construct(
            complemento=self.nombre, es_ataque=True, intencion="intencion_a", confianza=1.0,
            valor_normalizado=peticion.valor, evidencia={"pistas": ["A" * 5000]},
        )


def test_veredicto_defectuoso_falla_antes_de_abrir_sesion():
    # Con veredictos validados es imposible; con uno defectuoso, el error es del
    # complemento (500, que el middleware convierte en 503) y no deja efectos.
    cliente, senuelo, registro = _montar(complemento=VeredictoSinValidar())

    with pytest.raises(ValidationError):
        cliente.post("/interceptar", json=ATAQUE)

    assert registro.aperturas == 0 and senuelo.solicitudes == []

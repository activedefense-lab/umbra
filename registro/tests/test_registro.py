"""Pruebas de integración del registro forense (issue #12)."""

from uuid import uuid4

import pytest

from registro.informe import informe_sesion
from registro.repositorio import (
    abrir_sesion,
    anonimizar_origen,
    cerrar_sesion,
    eventos_de,
    listar_sesiones,
    obtener_sesion,
    registrar_evento,
)


def test_anonimizar_es_determinista_y_no_contiene_el_origen():
    h1 = anonimizar_origen("203.0.113.7")
    h2 = anonimizar_origen("203.0.113.7")
    assert h1 == h2
    assert "203.0.113.7" not in h1
    assert len(h1) == 64


def test_anonimizar_cambia_con_la_sal():
    assert anonimizar_origen("x", sal="a") != anonimizar_origen("x", sal="b")


def test_abrir_sesion_no_guarda_ip_en_claro(conn):
    sid = abrir_sesion(conn, "203.0.113.7", "/ping", "host")
    s = obtener_sesion(conn, sid)
    assert s is not None
    assert s.origen_hash == anonimizar_origen("203.0.113.7")
    assert "203.0.113.7" not in s.origen_hash
    assert s.fin is None


def test_eventos_se_leen_en_orden(conn):
    sid = abrir_sesion(conn, "o", "/ping", "host")
    registrar_evento(conn, sid, 1, "peticion_recibida", {"valor": "a;b"})
    registrar_evento(conn, sid, 3, "veredicto", {"es_ataque": True})
    registrar_evento(conn, sid, 5, "respuesta_enviada")
    evs = eventos_de(conn, sid)
    assert [e.paso for e in evs] == [1, 3, 5]
    assert evs[0].detalle == {"valor": "a;b"}
    assert evs[2].detalle == {}


def test_paso_fuera_de_rango_se_rechaza(conn):
    sid = abrir_sesion(conn, "o", "/ping", "host")
    with pytest.raises(ValueError):
        registrar_evento(conn, sid, 9, "x")
    with pytest.raises(ValueError):
        registrar_evento(conn, sid, 0, "x")


def test_cerrar_sesion_fija_fin_e_intencion(conn):
    sid = abrir_sesion(conn, "o", "/ping", "host")
    cerrar_sesion(conn, sid, intencion_final="reconocimiento")
    s = obtener_sesion(conn, sid)
    assert s.fin is not None
    assert s.intencion_final == "reconocimiento"


def test_listar_sesiones_devuelve_la_mas_reciente_primero(conn):
    a = abrir_sesion(conn, "o", "/a", "p")
    b = abrir_sesion(conn, "o", "/b", "p")
    ids = [s.id for s in listar_sesiones(conn, limite=2)]
    assert ids == [b, a]


def test_informe_contiene_cabecera_y_linea_de_tiempo(conn):
    sid = abrir_sesion(conn, "203.0.113.7", "/diagnostico/ping", "host")
    registrar_evento(conn, sid, 1, "peticion_recibida", {"valor": "127.0.0.1;id"})
    registrar_evento(conn, sid, 3, "veredicto", {"intencion": "desconocida"})
    cerrar_sesion(conn, sid, "desconocida")
    texto = informe_sesion(conn, sid)
    assert str(sid) in texto
    assert "/diagnostico/ping" in texto
    assert "Eventos: 2" in texto
    assert "[1] Petición del atacante" in texto
    assert "[3] Detección e inferencia" in texto
    assert "203.0.113.7" not in texto  # la IP nunca aparece en el informe


def test_informe_de_sesion_inexistente_lanza_lookup_error(conn):
    with pytest.raises(LookupError):
        informe_sesion(conn, uuid4())

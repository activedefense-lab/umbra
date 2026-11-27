"""Pruebas de integración de POST /interceptar (umbra#15, ADR-003).

Pruebas cruzadas: las escribe Santiago para la línea de Camila (detector).
Corren contra el esqueleto real (`infra/scripts/esqueleto.sh arriba`) con
Ollama en el anfitrión. No usan simuladores.

Hasta que el detector implemente /interceptar, responden 404 y fallan: es lo
esperado. Definen el criterio de aceptación del PR del detector.

Las pruebas marcadas `destructiva` detienen y vuelven a levantar servicios del
esqueleto; van al final del archivo.
"""

from __future__ import annotations

import json
import os
import subprocess
import uuid
from pathlib import Path

import httpx
import pytest

RAIZ = Path(__file__).resolve().parents[2]
COMPOSE = ["docker", "compose", "-f", str(RAIZ / "infra" / "docker-compose.yml")]
DETECTOR = os.environ.get("UMBRA_DETECTOR", "http://127.0.0.1:8001")
TIEMPO = float(os.environ.get("UMBRA_TIEMPO_PRUEBA", "60"))
SEPARADOR = "\x1f"  # la salida del señuelo puede contener "|"

BENIGNA = {
    "origen": "prueba-integracion",
    "ruta": "/api/lab/connectivity-check",
    "parametro": "host",
    "valor": "127.0.0.1",
}
ATAQUE = {**BENIGNA, "valor": "127.0.0.1;id"}
CAMPOS_DECISION = {"accion", "respuesta", "sesion_id"}


def sql(consulta: str) -> list[list[str]]:
    """Consulta el registro forense dentro del contenedor (PostgreSQL no se publica)."""
    r = subprocess.run(
        [*COMPOSE, "exec", "-T", "postgres", "psql", "-U", "umbra", "-d", "umbra_registro",
         "-At", "-F", SEPARADOR, "-c", consulta],
        capture_output=True, text=True, check=True,
    )
    return [linea.split(SEPARADOR) for linea in r.stdout.splitlines() if linea]


def contar_sesiones() -> int:
    return int(sql("SELECT count(*) FROM sesiones")[0][0])


def interceptar(cuerpo: dict) -> httpx.Response:
    return httpx.post(f"{DETECTOR}/interceptar", json=cuerpo, timeout=TIEMPO)


def compose(*args: str) -> None:
    subprocess.run([*COMPOSE, *args], check=True, capture_output=True, text=True)


@pytest.fixture(scope="session", autouse=True)
def esqueleto_arriba() -> None:
    try:
        r = httpx.get(f"{DETECTOR}/salud", timeout=5)
    except httpx.HTTPError as error:
        pytest.exit(
            f"El esqueleto no responde en {DETECTOR}; ejecuta infra/scripts/esqueleto.sh arriba ({error})",
            returncode=2,
        )
    assert r.status_code == 200


# ------------------------------------------------------------------ contrato


def test_benigna_permite_sin_abrir_sesion() -> None:
    antes = contar_sesiones()

    r = interceptar(BENIGNA)

    assert r.status_code == 200, r.text
    assert r.json() == {"accion": "permitir", "respuesta": "", "sesion_id": None}
    assert contar_sesiones() == antes


def test_ataque_devuelve_senuelo_y_deja_sesion_con_eventos_2_3_4() -> None:
    r = interceptar(ATAQUE)

    assert r.status_code == 200, r.text
    decision = r.json()
    assert set(decision) == CAMPOS_DECISION
    assert decision["accion"] == "senuelo"
    assert isinstance(decision["respuesta"], str) and decision["respuesta"].strip()
    sesion_id = uuid.UUID(decision["sesion_id"])  # valida el formato antes de usarlo en SQL

    sesiones = sql(
        "SELECT origen_hash, ruta, parametro, coalesce(intencion_final, ''), (fin IS NOT NULL)::text "
        f"FROM sesiones WHERE id = '{sesion_id}'"
    )
    assert len(sesiones) == 1
    origen_hash, ruta, parametro, intencion, cerrada = sesiones[0]
    assert len(origen_hash) == 64 and origen_hash != ATAQUE["origen"]  # nunca el origen en claro
    assert (ruta, parametro) == (ATAQUE["ruta"], ATAQUE["parametro"])
    assert intencion, "la sesión debe cerrarse con la intención inferida"
    assert cerrada == "true"

    eventos = sql(
        "SELECT paso, tipo, detalle::text FROM eventos "
        f"WHERE sesion_id = '{sesion_id}' ORDER BY creado_en, id"
    )
    assert [(paso, tipo) for paso, tipo, _ in eventos] == [
        ("2", "peticion_recibida"),
        ("3", "veredicto"),
        ("4", "respuesta_senuelo"),
    ]
    detalles = [json.loads(detalle) for _, _, detalle in eventos]
    assert detalles[0].get("valor") == ATAQUE["valor"]
    assert "intencion" in detalles[1]
    assert "modelo" in detalles[2]


@pytest.mark.parametrize(
    "cuerpo",
    [
        pytest.param({**BENIGNA, "metodo": "POST"}, id="campo-adicional-contrato-de-9"),
        pytest.param({k: v for k, v in BENIGNA.items() if k != "valor"}, id="falta-valor"),
    ],
)
def test_contrato_peticion_rechaza_cuerpos_invalidos(cuerpo: dict) -> None:
    assert interceptar(cuerpo).status_code == 422


def test_analizar_se_conserva_sin_cambios() -> None:
    r = httpx.post(f"{DETECTOR}/analizar", json=ATAQUE, timeout=TIEMPO)

    assert r.status_code == 200, r.text
    veredicto = r.json()
    assert veredicto["es_ataque"] is True
    assert "accion" not in veredicto


# --------------------------------------------------- fallo cerrado (destructivas)


@pytest.mark.destructiva
def test_senuelo_caido_bloquea_el_ataque_con_503() -> None:
    compose("stop", "senuelo")
    try:
        assert interceptar(ATAQUE).status_code == 503
        # Lo benigno no depende del señuelo: sigue permitiéndose.
        assert interceptar(BENIGNA).json()["accion"] == "permitir"
    finally:
        compose("up", "-d", "--wait", "senuelo")


@pytest.mark.destructiva
def test_registro_caido_bloquea_con_503_y_se_recupera() -> None:
    compose("stop", "postgres")
    try:
        assert interceptar(ATAQUE).status_code == 503
    finally:
        compose("up", "-d", "--wait", "postgres")

    # Tras reiniciar el registro, el detector vuelve a operar sin reiniciarse.
    r = interceptar(ATAQUE)
    assert r.status_code == 200, r.text
    assert r.json()["accion"] == "senuelo"

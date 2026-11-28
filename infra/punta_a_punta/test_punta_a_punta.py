"""Pruebas cruzadas del middleware de la aplicación objetivo, de punta a punta (umbra#15, paso 5).

Pruebas cruzadas (ADR-003, «Consecuencias»): el middleware `lab.deception` es
de la línea de Santiago; estas pruebas las escribe Camila. Atacan el endpoint
real de Noctúa desde dentro de `lab-target` (docker exec), igual que la prueba
manual de Santiago, y comprueban LO QUE RECIBE EL ATACANTE y la evidencia
forense, no detalles internos del detector:

  (a) petición benigna → 200 con el ping real, sin sesión forense;
  (b) inyección → 200 con la misma forma que la respuesta real, sin
      `sesion_id`, y `output` igual al texto del evento 4 de SU sesión;
  (c) señuelo detenido → 503, con la sesión registrada como `error_senuelo`.

ESTADO: preparadas, todavía no ejecutadas contra lab-target. La primera
ejecución es la verificación conjunta del paso 5 (Santiago y Camila).

Requieren los dos repositorios: el esqueleto de umbra arriba y `lab-target`
de Kmilap/noctua corriendo. Por eso viven fuera de `infra/pruebas/` y del CI.
No entran en el CI ni en `pytest infra/pruebas`. Se piden con su ruta:

    ~/.venvs/umbra-int/bin/pytest infra/punta_a_punta

Un `pytest` sin ruta desde la raíz también las recogería (igual que a
`infra/pruebas/`) y la sesión terminaría con código 2 si falta el entorno.

Si falta el entorno, FALLAN (código 2) con un mensaje claro: una ejecución
explícita nunca termina en verde con todo omitido.
"""

from __future__ import annotations

import json
import os
import secrets
import subprocess
import time
import urllib.request
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[2]
COMPOSE = ["docker", "compose", "-f", str(RAIZ / "infra" / "docker-compose.yml")]
LAB_TARGET = os.environ.get("UMBRA_LAB_TARGET", "noctua-lab-target")
URL_ENDPOINT = os.environ.get(
    "UMBRA_LAB_ENDPOINT", "http://127.0.0.1:8000/api/lab/connectivity-check"
)
DETECTOR = os.environ.get("UMBRA_DETECTOR", "http://127.0.0.1:8001")
SENUELO = os.environ.get("UMBRA_SENUELO", "http://127.0.0.1:8002")
TIEMPO = 45  # segundos; mayor que los 30 s del middleware
SEPARADOR = "\x1f"  # separa el cuerpo del código HTTP en la salida de curl
CLAVES_RESPUESTA_REAL = {"host", "exit_code", "output"}


# ------------------------------------------------------------------ utilidades


class Respuesta:
    def __init__(self, estado: int, texto: str) -> None:
        self.estado = estado
        self.texto = texto

    def json(self) -> dict:
        return json.loads(self.texto)


def atacar(host: str) -> Respuesta:
    """POST al endpoint real desde dentro de lab-target, como un cliente HTTP."""
    cuerpo = json.dumps({"host": host})
    r = subprocess.run(
        ["docker", "exec", LAB_TARGET, "curl", "-s", "--max-time", str(TIEMPO),
         "-o", "/dev/stdout", "-w", f"{SEPARADOR}%{{http_code}}",
         "-X", "POST", URL_ENDPOINT,
         "-H", "Content-Type: application/json", "-H", "Accept: application/json",
         "--data", cuerpo],
        capture_output=True, text=True, timeout=TIEMPO + 15, check=False,
    )
    texto, _, estado = r.stdout.rpartition(SEPARADOR)
    return Respuesta(int(estado or 0), texto)


def sql(consulta: str) -> list[dict]:
    """Filas del registro forense como JSON (PostgreSQL no se publica en el anfitrión).

    `json_agg` devuelve un único valor JSON: un texto de señuelo con saltos de
    línea o con el separador no puede partir ni desalinear las filas (OBS-28).
    """
    envuelta = f"SELECT coalesce(json_agg(t), '[]'::json) FROM ({consulta}) AS t"
    r = subprocess.run(
        [*COMPOSE, "exec", "-T", "postgres", "psql", "-U", "umbra", "-d", "umbra_registro",
         "-At", "-c", envuelta],
        capture_output=True, text=True, check=True,
    )
    return json.loads(r.stdout)


def contar_sesiones() -> int:
    return sql("SELECT count(*) AS n FROM sesiones")[0]["n"]


def literal(texto: str) -> str:
    return "'" + texto.replace("'", "''") + "'"


def sesion_de(valor: str) -> tuple[str, bool, list[tuple[int, str, str]]]:
    """Sesión cuyo evento 2 tiene exactamente este valor (correlación sin sesion_id)."""
    filas = sql(
        "SELECT s.id, s.fin IS NOT NULL AS cerrada FROM sesiones s "
        "JOIN eventos e ON e.sesion_id = s.id "
        f"WHERE e.paso = 2 AND e.detalle->>'valor' = {literal(valor)}"
    )
    assert len(filas) == 1, f"se esperaba exactamente una sesión para la carga, hay {len(filas)}"
    sesion_id, cerrada = filas[0]["id"], filas[0]["cerrada"]
    eventos = sql(
        "SELECT paso, tipo, coalesce(detalle->>'respuesta', '') AS respuesta FROM eventos "
        f"WHERE sesion_id = {literal(sesion_id)} ORDER BY creado_en, id"
    )
    return sesion_id, cerrada, [(e["paso"], e["tipo"], e["respuesta"]) for e in eventos]


def carga_unica() -> str:
    # El token hace única la carga: así se encuentra SU sesión y no otra anterior.
    return f"127.0.0.1;id #{secrets.token_hex(8)}"


def esperar_listo() -> None:
    for _ in range(24):
        try:
            with urllib.request.urlopen(f"{SENUELO}/listo", timeout=5) as r:
                if r.status == 200:
                    return
        except OSError:
            pass
        time.sleep(5)
    raise AssertionError("el señuelo no quedó listo tras restaurarlo")


# --------------------------------------------------------------------- entorno


@pytest.fixture(scope="session", autouse=True)
def entorno_completo() -> None:
    """Si falta algo, la sesión FALLA (código 2): no se omite en silencio."""
    try:
        urllib.request.urlopen(f"{DETECTOR}/salud", timeout=5)
    except OSError as error:
        pytest.exit(f"El esqueleto de umbra no responde ({error}): infra/scripts/esqueleto.sh arriba",
                    returncode=2)

    estado = subprocess.run(["docker", "inspect", "-f", "{{.State.Running}}", LAB_TARGET],
                            capture_output=True, text=True, check=False)
    if estado.stdout.strip() != "true":
        pytest.exit(f"El contenedor {LAB_TARGET} no está corriendo: "
                    "cd ~/noctua && docker compose --profile lab up -d lab-target", returncode=2)

    sonda = atacar("127.0.0.1")
    if sonda.estado == 404:
        pytest.exit("La ruta de laboratorio responde 404: lab-target no está en APP_ENV=lab con "
                    "UMBRA_LAB_ENABLED=true (revisar noctua-api/.env.lab)", returncode=2)
    if sonda.estado == 0:
        pytest.exit(f"No se pudo hacer la petición dentro de {LAB_TARGET}", returncode=2)

    esperar_listo()


# ---------------------------------------------------------------------- pruebas


def test_a_benigna_llega_al_ping_real_sin_sesion() -> None:
    antes = contar_sesiones()

    r = atacar("127.0.0.1")

    assert r.estado == 200, r.texto
    cuerpo = r.json()
    assert set(cuerpo) == CLAVES_RESPUESTA_REAL
    assert cuerpo["host"] == "127.0.0.1"
    assert cuerpo["exit_code"] == 0
    assert "127.0.0.1" in cuerpo["output"] and "transmitted" in cuerpo["output"], cuerpo["output"]
    assert contar_sesiones() == antes


def test_b_inyeccion_recibe_el_senuelo_registrado_en_su_sesion() -> None:
    carga = carga_unica()

    r = atacar(carga)

    assert r.estado == 200, r.texto
    cuerpo = r.json()
    # Misma forma que la respuesta real; nada interno para el atacante.
    assert set(cuerpo) == CLAVES_RESPUESTA_REAL
    assert cuerpo["host"] == carga and cuerpo["exit_code"] == 0
    assert "sesion_id" not in r.texto

    _, cerrada, eventos = sesion_de(carga)
    assert [(paso, tipo) for paso, tipo, _ in eventos] == [
        (2, "peticion_recibida"), (3, "veredicto"), (4, "respuesta_senuelo"),
    ]
    assert cerrada
    # Lo que recibió el atacante es exactamente lo que quedó registrado (OBS-14).
    assert cuerpo["output"] == eventos[2][2]


@pytest.mark.destructiva
def test_c_senuelo_detenido_bloquea_con_503_y_queda_registrado() -> None:
    carga = carga_unica()
    subprocess.run([*COMPOSE, "stop", "senuelo"], check=True, capture_output=True)
    try:
        r = atacar(carga)

        assert r.estado == 503, r.texto
        assert "sesion_id" not in r.texto and "ConnectError" not in r.texto
        _, cerrada, eventos = sesion_de(carga)
        assert [(paso, tipo) for paso, tipo, _ in eventos] == [
            (2, "peticion_recibida"), (3, "veredicto"), (4, "error_senuelo"),
        ]
        assert cerrada
    finally:
        # Restauración garantizada aunque falle una aserción.
        subprocess.run([*COMPOSE, "up", "-d", "--wait", "senuelo"], check=True, capture_output=True)
        esperar_listo()

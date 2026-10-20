"""Pruebas HTTP de la API del señuelo (núcleo; ADR-002)."""

import ast
from importlib.metadata import entry_points
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from contrato.cargador import GRUPO, VARIABLE_ACTIVO
from contrato.composicion import RESTRICCIONES
from contrato.errores import ComplementoNoEncontrado, ResultadoInvalido
from falsos import ContextoInvalido, Falso, FormaCWE79
from senuelo.api import crear_app
from senuelo.modelos import RespuestaSenuelo
from senuelo.ollama import ErrorOllama


RESPUESTA = RespuestaSenuelo(
    respuesta="salida simulada",
    modelo="modelo-prueba",
    latencia_ms=12.5,
)


def _solicitud(**cambios) -> dict:
    datos = {
        "complemento": "falso",
        "intencion": "intencion_a",
        "valor_normalizado": "127.0.0.1;x",
    }
    datos.update(cambios)
    return datos


def _no_debe_ejecutarse(instrucciones):
    raise AssertionError("El generador no debe recibir solicitudes rechazadas")


def _cliente(generador=None, complemento=None) -> TestClient:
    if complemento is None:
        complemento = Falso()
    if generador is None:
        generador = lambda instrucciones: RESPUESTA

    return TestClient(crear_app(complemento, generador))


def test_salud_informa_el_complemento_activo():
    respuesta = _cliente().get("/salud")

    assert respuesta.status_code == 200
    assert respuesta.json()["estado"] == "ok"
    assert respuesta.json()["complemento"] == {
        "nombre": "falso",
        "cwe": "CWE-1",
    }


def test_generar_respuesta_con_instrucciones_compuestas():
    recibidas = []

    def generador(instrucciones):
        recibidas.append(instrucciones)
        return RESPUESTA

    respuesta = _cliente(generador).post(
        "/generar",
        json=_solicitud(),
    )

    assert respuesta.status_code == 200
    assert respuesta.json() == RESPUESTA.model_dump()

    (instrucciones,) = recibidas

    assert instrucciones.sistema.startswith(RESTRICCIONES)
    assert "simulación falsa" in instrucciones.sistema
    assert "127.0.0.1;x" in instrucciones.entrada
    assert "127.0.0.1;x" not in instrucciones.sistema


def test_generar_devuelve_503_si_ollama_falla():
    def generador_fallido(instrucciones):
        raise ErrorOllama("Servidor no disponible")

    respuesta = _cliente(generador_fallido).post(
        "/generar",
        json=_solicitud(),
    )

    assert respuesta.status_code == 503
    assert respuesta.json()["detail"] == (
        "Generador de señuelo no disponible"
    )


def test_generar_rechaza_evidencia_demasiado_larga():
    respuesta = _cliente(_no_debe_ejecutarse).post(
        "/generar",
        json=_solicitud(
            evidencia={"segmentos": ["A" * 4097]},
        ),
    )

    assert respuesta.status_code == 422


def test_solicitud_para_otro_complemento_devuelve_422():
    respuesta = _cliente(_no_debe_ejecutarse).post(
        "/generar",
        json=_solicitud(complemento="otro"),
    )

    assert respuesta.status_code == 422
    assert "activo" in respuesta.json()["detail"]


def test_intencion_ajena_devuelve_422():
    respuesta = _cliente(_no_debe_ejecutarse).post(
        "/generar",
        json=_solicitud(intencion="intencion_ajena"),
    )

    assert respuesta.status_code == 422
    assert "catálogo" in respuesta.json()["detail"]


def test_intencion_desconocida_se_acepta():
    respuesta = _cliente().post(
        "/generar",
        json=_solicitud(intencion="desconocida"),
    )

    assert respuesta.status_code == 200


def test_el_campo_segmentos_anterior_devuelve_422():
    respuesta = _cliente(_no_debe_ejecutarse).post(
        "/generar",
        json=_solicitud(segmentos=["x"]),
    )

    assert respuesta.status_code == 422


def test_contexto_invalido_no_se_propaga():
    with pytest.raises(ResultadoInvalido):
        _cliente(
            _no_debe_ejecutarse,
            ContextoInvalido(),
        ).post(
            "/generar",
            json=_solicitud(),
        )


def test_sin_variable_no_arranca(monkeypatch):
    monkeypatch.delenv(VARIABLE_ACTIVO, raising=False)

    with pytest.raises(ComplementoNoEncontrado):
        crear_app()


def _complementos_instalados() -> list[str]:
    nombres = sorted(
        ep.name for ep in entry_points(group=GRUPO)
    )

    assert nombres, (
        "No hay complementos instalados junto al señuelo"
    )

    return nombres


def test_arranca_con_un_complemento_instalado(monkeypatch):
    nombre = _complementos_instalados()[0]
    monkeypatch.setenv(VARIABLE_ACTIVO, nombre)

    respuesta = TestClient(crear_app()).get("/salud")

    assert respuesta.json()["complemento"]["nombre"] == nombre


def test_el_senuelo_no_importa_complementos_concretos():
    prohibidos = {
        ep.module.split(".")[0]
        for ep in entry_points(group=GRUPO)
    }

    assert prohibidos, (
        "No hay complementos instalados para comprobar"
    )

    raiz = Path(__file__).resolve().parents[1]

    for archivo in raiz.rglob("*.py"):
        if any(
            parte.startswith(".")
            for parte in archivo.relative_to(raiz).parts
        ):
            continue

        for nodo in ast.walk(
            ast.parse(archivo.read_text(encoding="utf-8"))
        ):
            if isinstance(nodo, ast.Import):
                modulos = [
                    alias.name for alias in nodo.names
                ]
            elif (
                isinstance(nodo, ast.ImportFrom)
                and nodo.module
                and nodo.level == 0
            ):
                modulos = [nodo.module]
            else:
                continue

            for modulo in modulos:
                assert modulo.split(".")[0] not in prohibidos, (
                    f"{archivo.relative_to(raiz)} "
                    f"importa {modulo}"
                )

# Criterio 2: compatibilidad con un complemento de forma CWE-79


def test_forma_cwe79_compone_su_propia_simulacion():
    recibidas = []

    def generador(instrucciones):
        recibidas.append(instrucciones)
        return RESPUESTA

    respuesta = _cliente(generador, FormaCWE79()).post(
        "/generar",
        json={
            "complemento": "forma_cwe79",
            "intencion": "desfiguracion",
            "valor_normalizado": "<marca>",
            "evidencia": {
                "etiquetas": ["marca_ficticia"],
            },
        },
    )

    assert respuesta.status_code == 200
    assert respuesta.json() == RESPUESTA.model_dump()

    (instrucciones,) = recibidas

    # El núcleo mantiene sus restricciones de seguridad.
    assert instrucciones.sistema.startswith(RESTRICCIONES)

    # La simulación procede del complemento CWE-79 ficticio.
    assert "página web" in instrucciones.sistema

    # La entrada del usuario no se incorpora al mensaje de sistema.
    assert "<marca>" in instrucciones.entrada
    assert "<marca>" not in instrucciones.sistema


def test_una_intencion_de_cwe78_no_vale_para_forma_cwe79():
    """Rechaza intenciones ajenas antes de consultar el contexto."""

    class SinContexto(FormaCWE79):
        def contexto_senuelo(self, solicitud):
            raise AssertionError(
                "contexto_senuelo no debe ejecutarse "
                "en una solicitud rechazada"
            )

    respuesta = _cliente(
        _no_debe_ejecutarse,
        SinContexto(),
    ).post(
        "/generar",
        json={
            "complemento": "forma_cwe79",
            "intencion": "reconocimiento",
            "valor_normalizado": "x",
        },
    )

    assert respuesta.status_code == 422
    assert "catálogo" in respuesta.json()["detail"]
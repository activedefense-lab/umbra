"""Cliente HTTP de Ollama para el generador de señuelo.

Recibe instrucciones compuestas por el núcleo y las envía a Ollama.
No construye instrucciones ni ejecuta comandos del atacante.
"""

from __future__ import annotations

import os
import time

import httpx

from contrato.composicion import Instrucciones

from .modelos import RespuestaSenuelo


class ErrorOllama(Exception):
    """Fallo controlado al comunicarse con Ollama."""


def generar(
    instrucciones: Instrucciones,
    *,
    cliente: httpx.Client | None = None,
) -> RespuestaSenuelo:
    """Envía instrucciones compuestas y devuelve una respuesta simulada."""

    url = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434")
    modelo = os.getenv("OLLAMA_MODELO", "llama3:latest")

    cuerpo = {
        "model": modelo,
        "system": instrucciones.sistema,
        "prompt": instrucciones.entrada,
        "stream": False,
        "options": {"temperature": 0.3, "num_predict": 128},
    }

    inicio = time.perf_counter()

    try:
        if cliente is None:
            with httpx.Client(timeout=60.0) as cliente_local:
                respuesta = cliente_local.post(
                    f"{url.rstrip('/')}/api/generate",
                    json=cuerpo,
                )
        else:
            respuesta = cliente.post(
                f"{url.rstrip('/')}/api/generate",
                json=cuerpo,
            )

        respuesta.raise_for_status()
        datos = respuesta.json()

        if not isinstance(datos, dict):
            raise ValueError("La respuesta no es un objeto JSON")

        texto = datos.get("response")

        if not isinstance(texto, str) or not texto.strip():
            raise ValueError("Ollama devolvió una respuesta vacía o inválida")

    except (httpx.HTTPError, ValueError) as error:
        raise ErrorOllama(
            "No fue posible generar la respuesta simulada"
        ) from error

    latencia_ms = (time.perf_counter() - inicio) * 1000

    return RespuestaSenuelo(
        respuesta=texto,
        modelo=modelo,
        latencia_ms=latencia_ms,
    )
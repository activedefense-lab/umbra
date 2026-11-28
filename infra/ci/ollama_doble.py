#!/usr/bin/env python3
"""Doble de prueba de Ollama, solo para el CI (umbra#15, PR 3b).

Imita el subconjunto de la API de Ollama que usa ARYA, con las respuestas
reales capturadas en `contrato_ollama_0.40.3.json`:

- POST /api/generate  generación sin streaming (señuelo y calentamiento).
- GET  /api/ps        modelos cargados (/listo del señuelo).
- GET  /api/version   versión (comprobación de conectividad).

Devuelve siempre el mismo texto, claramente artificial. Sirve para verificar
el FLUJO (contratos entre servicios, registro forense, fallo cerrado), no la
credibilidad, la latencia ni el comportamiento del modelo real, que se miden
con Ollama real (sprints 6 y 12).

Valida lo que ARYA envía para no dar por buenas peticiones incorrectas: modelo
configurado (404 como Ollama si no), `prompt` de texto, `stream` en false,
`keep_alive` válido y `options.num_predict` entero positivo. Ollama real acepta
peticiones sin `keep_alive` ni `num_predict`, pero ARYA siempre los envía: sin
`num_predict` la generación no tiene tope y rompería el presupuesto de latencia.
La temperatura no se valida aquí: la cubren las pruebas del señuelo, que
inspeccionan el cuerpo exacto enviado a Ollama.

Mensajes de error: el 404 por modelo inexistente usa el texto real de Ollama;
los 400 conservan el código y el formato `{"error": ...}`, con texto propio.

Solo biblioteca estándar. Uso:
    python3 infra/ci/ollama_doble.py --host 0.0.0.0 --puerto 11434
"""

from __future__ import annotations

import argparse
import copy
import datetime as dt
import json
import re
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

CONTRATO = json.loads(
    Path(__file__).with_name("contrato_ollama_0.40.3.json").read_text(encoding="utf-8")
)
TEXTO_FIJO = "[doble de prueba de Ollama: respuesta fija del CI]"
VERSION = "0.40.3 (doble de prueba)"
_DURACION = re.compile(r"-?(?:\d+(?:\.\d+)?(?:ns|us|µs|ms|s|m|h))+")


class ErrorPeticion(Exception):
    def __init__(self, estado: int, mensaje: str) -> None:
        super().__init__(mensaje)
        self.estado = estado
        self.mensaje = mensaje


def validar_generate(cuerpo: object, modelo: str) -> dict:
    """Devuelve el cuerpo si cumple lo que ARYA debe enviar; si no, ErrorPeticion."""
    if not isinstance(cuerpo, dict):
        raise ErrorPeticion(400, "doble de prueba: el cuerpo debe ser un objeto JSON")
    pedido = cuerpo.get("model")
    if not isinstance(pedido, str) or not pedido:
        raise ErrorPeticion(400, "doble de prueba: falta 'model'")
    if pedido != modelo:
        # Mismo formato que Ollama 0.40.3 (comillas simples).
        raise ErrorPeticion(404, f"model '{pedido}' not found")
    if not isinstance(cuerpo.get("prompt"), str):
        raise ErrorPeticion(400, "doble de prueba: falta 'prompt' (texto)")
    if cuerpo.get("stream") is not False:
        raise ErrorPeticion(400, "doble de prueba: ARYA debe enviar 'stream': false")
    if "system" in cuerpo and not isinstance(cuerpo["system"], str):
        raise ErrorPeticion(400, "doble de prueba: 'system' debe ser texto")
    keep_alive = cuerpo.get("keep_alive")
    valido = (isinstance(keep_alive, int) and not isinstance(keep_alive, bool)) or (
        isinstance(keep_alive, str) and _DURACION.fullmatch(keep_alive)
    )
    if not valido:
        raise ErrorPeticion(400, "doble de prueba: falta 'keep_alive' válido (ARYA siempre lo envía)")
    opciones = cuerpo.get("options")
    if not isinstance(opciones, dict):
        raise ErrorPeticion(400, "doble de prueba: falta 'options' (ARYA siempre envía num_predict)")
    num_predict = opciones.get("num_predict")
    if isinstance(num_predict, bool) or not isinstance(num_predict, int) or num_predict <= 0:
        raise ErrorPeticion(400, "doble de prueba: 'options.num_predict' debe ser un entero positivo")
    return cuerpo


def _ahora() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z")


def crear_servidor(host: str, puerto: int, modelo: str) -> ThreadingHTTPServer:
    estado = {"cargado": False, "peticiones": 0}
    candado = threading.Lock()

    class Manejador(BaseHTTPRequestHandler):
        server_version = "ollama-doble"

        def _responder(self, codigo: int, cuerpo: dict) -> None:
            datos = json.dumps(cuerpo).encode("utf-8")
            self.send_response(codigo)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(datos)))
            self.end_headers()
            self.wfile.write(datos)

        def log_message(self, formato: str, *args: object) -> None:
            sys.stdout.write(f"[ollama-doble] {self.address_string()} {formato % args}\n")
            sys.stdout.flush()

        def do_GET(self) -> None:  # noqa: N802 (nombre impuesto por http.server)
            if self.path == "/api/version":
                self._responder(200, {"version": VERSION})
            elif self.path == "/api/ps":
                with candado:
                    cargado = estado["cargado"]
                modelos = []
                if cargado:
                    entrada = copy.deepcopy(CONTRATO["ps_modelo"])
                    entrada["name"] = entrada["model"] = modelo
                    modelos.append(entrada)
                self._responder(200, {"models": modelos})
            else:
                self._responder(404, {"error": "not found"})

        def do_POST(self) -> None:  # noqa: N802
            if self.path != "/api/generate":
                self._responder(404, {"error": "not found"})
                return
            crudo = self.rfile.read(int(self.headers.get("Content-Length") or 0))
            try:
                try:
                    cuerpo = json.loads(crudo)
                except json.JSONDecodeError as error:
                    raise ErrorPeticion(400, f"doble de prueba: JSON inválido ({error.msg})") from error
                pedido = validar_generate(cuerpo, modelo)
            except ErrorPeticion as error:
                self._responder(error.estado, {"error": error.mensaje})
                return

            respuesta = copy.deepcopy(CONTRATO["generate"])
            respuesta.update(model=pedido["model"], created_at=_ahora(), response=TEXTO_FIJO)
            with candado:
                estado["cargado"] = True
                estado["peticiones"] += 1
            sys.stdout.write(
                f"[ollama-doble] generate keep_alive={pedido['keep_alive']!r} "
                f"options={pedido.get('options', {})}\n"
            )
            self._responder(200, respuesta)

    servidor = ThreadingHTTPServer((host, puerto), Manejador)
    servidor.estado = estado  # type: ignore[attr-defined]  # visible en pruebas
    return servidor


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--host", default="0.0.0.0", help="0.0.0.0: accesible desde los contenedores")
    parser.add_argument("--puerto", type=int, default=11434)
    parser.add_argument("--modelo", default="llama3:latest")
    args = parser.parse_args()
    servidor = crear_servidor(args.host, args.puerto, args.modelo)
    print(f"[ollama-doble] escuchando en {args.host}:{args.puerto} con el modelo {args.modelo}", flush=True)
    servidor.serve_forever()


if __name__ == "__main__":
    main()

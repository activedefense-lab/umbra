"""Cliente HTTP de Ollama para el generador de señuelo.

Recibe instrucciones compuestas por el núcleo y las envía a Ollama.
No construye instrucciones ni ejecuta comandos del atacante.

Tiempos de espera (umbra#15, precisiones de implementación del ADR-003):
la cadena es middleware (30 s) > detector→señuelo (25 s) > señuelo→Ollama
(OLLAMA_TIMEOUT, 20 s). El calentamiento tiene su propio límite
(OLLAMA_TIMEOUT_CALENTAMIENTO, 90 s) porque en frío se midieron 38 s.
"""

from __future__ import annotations

import math
import os
import re
import time
from dataclasses import dataclass

import httpx

from contrato.composicion import Instrucciones

from .modelos import RespuestaSenuelo

# Parámetros de generación. La temperatura se envía a Ollama y se devuelve
# en la respuesta desde el mismo cuerpo de la petición: lo registrado es lo usado.
TEMPERATURA = 0.3
MAX_TOKENS = 128

# Valores por defecto de configuración (sobrescribibles por entorno).
URL_POR_DEFECTO = "http://127.0.0.1:11434"
MODELO_POR_DEFECTO = "llama3:latest"
TIMEOUT_POR_DEFECTO = 20.0
TIMEOUT_CALENTAMIENTO_POR_DEFECTO = 90.0
KEEP_ALIVE_POR_DEFECTO = "30m"

# Consulta de disponibilidad (/listo): ligera y corta, nunca genera texto.
TIMEOUT_CONSULTA = 2.0


class ErrorOllama(Exception):
    """Fallo controlado al comunicarse con Ollama."""


def _segundos(variable: str, defecto: float) -> float:
    crudo = os.getenv(variable)
    if crudo is None or crudo.strip() == "":
        return defecto
    try:
        valor = float(crudo)
    except ValueError as error:
        raise ValueError(f"{variable} debe ser un número de segundos: {crudo!r}") from error
    if not math.isfinite(valor) or valor <= 0:
        raise ValueError(f"{variable} debe ser un número finito mayor que cero: {crudo!r}")
    return valor


# Duraciones que acepta Ollama (formato de Go): "30m", "1h30m", "1.5h", "-1m".
_DURACION = re.compile(r"-?(?:\d+(?:\.\d+)?(?:ns|us|µs|ms|s|m|h))+")


def _keep_alive(crudo: str) -> int | str:
    """Ollama interpreta un número como segundos (negativo = indefinido) y un
    texto como duración ("30m"). El texto "-1" sin unidad no es una duración
    válida, por eso los enteros se envían como número. Cualquier otro texto
    se valida aquí para fallar al arrancar y no en la primera petición."""
    valor = crudo.strip()
    try:
        return int(valor)
    except ValueError:
        pass
    if not _DURACION.fullmatch(valor):
        raise ValueError(
            f"OLLAMA_KEEP_ALIVE debe ser un entero de segundos (-1 = indefinido) "
            f"o una duración como '30m': {crudo!r}"
        )
    return valor


def con_etiqueta(modelo: str) -> str:
    """Ollama lista "llama3:latest" aunque se haya pedido "llama3"."""
    return modelo if ":" in modelo.rsplit("/", 1)[-1] else f"{modelo}:latest"


@dataclass(frozen=True)
class Configuracion:
    url: str
    modelo: str
    timeout: float
    timeout_calentamiento: float
    keep_alive: int | str

    @classmethod
    def desde_entorno(cls) -> Configuracion:
        """Lee y valida la configuración. Un valor inválido es un error de despliegue."""
        return cls(
            url=os.getenv("OLLAMA_URL", URL_POR_DEFECTO).rstrip("/"),
            modelo=os.getenv("OLLAMA_MODELO", MODELO_POR_DEFECTO),
            timeout=_segundos("OLLAMA_TIMEOUT", TIMEOUT_POR_DEFECTO),
            timeout_calentamiento=_segundos(
                "OLLAMA_TIMEOUT_CALENTAMIENTO", TIMEOUT_CALENTAMIENTO_POR_DEFECTO
            ),
            keep_alive=_keep_alive(
                os.getenv("OLLAMA_KEEP_ALIVE", "").strip() or KEEP_ALIVE_POR_DEFECTO
            ),
        )


def _texto_generado(respuesta: httpx.Response) -> str:
    respuesta.raise_for_status()
    datos = respuesta.json()
    if not isinstance(datos, dict):
        raise ValueError("La respuesta no es un objeto JSON")
    texto = datos.get("response")
    if not isinstance(texto, str) or not texto.strip():
        raise ValueError("Ollama devolvió una respuesta vacía o inválida")
    return texto


def _post(
    url: str,
    cuerpo: dict,
    timeout: float,
    cliente: httpx.Client | None,
) -> httpx.Response:
    if cliente is not None:
        return cliente.post(url, json=cuerpo)
    with httpx.Client(timeout=timeout) as cliente_local:
        return cliente_local.post(url, json=cuerpo)


def generar(
    instrucciones: Instrucciones,
    *,
    cliente: httpx.Client | None = None,
) -> RespuestaSenuelo:
    """Envía instrucciones compuestas y devuelve una respuesta simulada."""

    config = Configuracion.desde_entorno()

    cuerpo = {
        "model": config.modelo,
        "system": instrucciones.sistema,
        "prompt": instrucciones.entrada,
        "stream": False,
        "keep_alive": config.keep_alive,
        "options": {"temperature": TEMPERATURA, "num_predict": MAX_TOKENS},
    }

    inicio = time.perf_counter()

    try:
        texto = _texto_generado(
            _post(f"{config.url}/api/generate", cuerpo, config.timeout, cliente)
        )
    except (httpx.HTTPError, ValueError) as error:
        raise ErrorOllama("No fue posible generar la respuesta simulada") from error

    latencia_ms = (time.perf_counter() - inicio) * 1000

    return RespuestaSenuelo(
        respuesta=texto,
        modelo=config.modelo,
        latencia_ms=latencia_ms,
        temperatura=cuerpo["options"]["temperature"],
    )


def calentar(*, cliente: httpx.Client | None = None) -> float:
    """Generación mínima real para cargar el modelo e inicializar la GPU.

    Cargar el modelo no basta: en frío también la primera evaluación es lenta
    (medido en WSL: 2 tokens/s frente a 210 en caliente). Devuelve la
    duración en milisegundos.

    El éxito es que Ollama declare la generación terminada (HTTP 200 y
    "done": true), no el texto: con un solo token el modelo puede devolver
    solo espacios o un fin de secuencia, y el modelo igual quedó cargado.
    """

    config = Configuracion.desde_entorno()

    cuerpo = {
        "model": config.modelo,
        "prompt": "ok",
        "stream": False,
        "keep_alive": config.keep_alive,
        "options": {"num_predict": 1},
    }

    inicio = time.perf_counter()

    try:
        respuesta = _post(
            f"{config.url}/api/generate",
            cuerpo,
            config.timeout_calentamiento,
            cliente,
        )
        respuesta.raise_for_status()
        datos = respuesta.json()
        if not isinstance(datos, dict) or datos.get("done") is not True:
            raise ValueError("Ollama no declaró terminada la generación")
    except (httpx.HTTPError, ValueError) as error:
        raise ErrorOllama("No fue posible calentar el modelo") from error

    return (time.perf_counter() - inicio) * 1000


def modelo_cargado(*, cliente: httpx.Client | None = None) -> bool:
    """Indica si el modelo configurado está cargado ahora en memoria.

    Consulta GET /api/ps: no genera texto ni carga el modelo.
    Lanza ErrorOllama si Ollama no responde o la respuesta es inválida.
    """

    config = Configuracion.desde_entorno()
    url = f"{config.url}/api/ps"

    try:
        if cliente is not None:
            respuesta = cliente.get(url)
        else:
            with httpx.Client(timeout=TIMEOUT_CONSULTA) as cliente_local:
                respuesta = cliente_local.get(url)
        respuesta.raise_for_status()
        datos = respuesta.json()
        modelos = datos.get("models") if isinstance(datos, dict) else None
        if not isinstance(modelos, list):
            raise ValueError("La respuesta de /api/ps no contiene una lista de modelos")
        nombres = {
            con_etiqueta(m.get("name", ""))
            for m in modelos
            if isinstance(m, dict)
        }
    except (httpx.HTTPError, ValueError) as error:
        raise ErrorOllama("No fue posible consultar los modelos cargados") from error

    return con_etiqueta(config.modelo) in nombres

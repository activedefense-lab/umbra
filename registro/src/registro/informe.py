"""Informe de una sesión en texto plano (versión mínima del sprint 1).

El informe de incidente completo, con intención inferida, línea de tiempo,
comandos y respuestas en formato definitivo, es la tarea del sprint 8.
"""

from __future__ import annotations

import json
from uuid import UUID

import psycopg

from .repositorio import eventos_de, obtener_sesion

NOMBRES_PASO = {
    1: "Petición del atacante",
    2: "Derivación al detector",
    3: "Detección e inferencia",
    4: "Generación del señuelo",
    5: "Respuesta al atacante",
    6: "Registro forense",
    7: "Consulta de visualización",
    8: "Informe al defensor",
}


def informe_sesion(conn: psycopg.Connection, sesion_id: UUID) -> str:
    sesion = obtener_sesion(conn, sesion_id)
    if sesion is None:
        raise LookupError(f"sesión no encontrada: {sesion_id}")
    eventos = eventos_de(conn, sesion_id)

    lineas = [
        f"UMBRA · Informe de sesión {sesion.id}",
        f"Origen (hash): {sesion.origen_hash[:16]}…",
        f"Ruta: {sesion.ruta}   Parámetro: {sesion.parametro}",
        f"Inicio: {sesion.inicio.isoformat(timespec='seconds')}",
        f"Fin:    {sesion.fin.isoformat(timespec='seconds') if sesion.fin else '(abierta)'}",
        f"Intención final: {sesion.intencion_final or '(sin inferir)'}",
        f"Eventos: {len(eventos)}",
        "",
        "Línea de tiempo",
        "---------------",
    ]
    for e in eventos:
        hora = e.creado_en.strftime("%H:%M:%S.%f")[:-3]
        nombre = NOMBRES_PASO.get(e.paso, f"paso {e.paso}")
        detalle = json.dumps(e.detalle, ensure_ascii=False, sort_keys=True) if e.detalle else ""
        lineas.append(f"{hora}  [{e.paso}] {nombre:<26} {e.tipo:<20} {detalle}".rstrip())
    return "\n".join(lineas)

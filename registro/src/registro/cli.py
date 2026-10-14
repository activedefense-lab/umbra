"""Línea de comandos del registro forense.

    python -m registro.cli esquema              Aplica sql/*.sql
    python -m registro.cli sesiones [--limite N] Lista sesiones recientes
    python -m registro.cli informe <sesion_id>   Imprime el informe de una sesión
    python -m registro.cli demo                  Crea una sesión de ejemplo y la imprime
"""

from __future__ import annotations

import argparse
import sys
from uuid import UUID

from .conexion import aplicar_esquema, conectar
from .informe import informe_sesion
from .repositorio import abrir_sesion, cerrar_sesion, listar_sesiones, registrar_evento


def _demo(conn) -> UUID:
    sid = abrir_sesion(conn, origen="203.0.113.7", ruta="/diagnostico/ping", parametro="host")
    registrar_evento(conn, sid, 1, "peticion_recibida", {"valor": "127.0.0.1;id"})
    registrar_evento(conn, sid, 2, "derivada_al_detector")
    registrar_evento(conn, sid, 3, "veredicto", {"es_ataque": True, "intencion": "desconocida", "segmentos": ["id"]})
    registrar_evento(conn, sid, 4, "senuelo_generado", {"latencia_ms": 0, "nota": "pendiente issue #11"})
    registrar_evento(conn, sid, 5, "respuesta_enviada")
    cerrar_sesion(conn, sid, intencion_final="desconocida")
    return sid


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="registro")
    sub = parser.add_subparsers(dest="orden", required=True)
    sub.add_parser("esquema")
    p_ses = sub.add_parser("sesiones")
    p_ses.add_argument("--limite", type=int, default=20)
    p_inf = sub.add_parser("informe")
    p_inf.add_argument("sesion_id", type=UUID)
    sub.add_parser("demo")
    args = parser.parse_args(argv)

    with conectar() as conn:
        if args.orden == "esquema":
            for nombre in aplicar_esquema(conn):
                print(f"aplicado: {nombre}")
        elif args.orden == "sesiones":
            for s in listar_sesiones(conn, args.limite):
                print(f"{s.id}  {s.inicio.isoformat(timespec='seconds')}  {s.ruta}  {s.intencion_final or '-'}")
        elif args.orden == "informe":
            print(informe_sesion(conn, args.sesion_id))
        elif args.orden == "demo":
            sid = _demo(conn)
            print(informe_sesion(conn, sid))
    return 0


if __name__ == "__main__":
    sys.exit(main())

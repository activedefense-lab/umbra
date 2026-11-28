"""Doble de prueba del registro forense para las pruebas unitarias de /interceptar.

Guarda sesiones y eventos en memoria con el mismo orden y los mismos datos
que recibiría PostgreSQL, y permite provocar un fallo en una operación
concreta para probar los fallos parciales. Las escrituras anteriores al
fallo se conservan, como ocurre con el registro real (cada operación hace
su propio commit).
"""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any
from uuid import UUID, uuid4

from detector.interceptacion import ErrorRegistro


@dataclass
class SesionSimulada:
    origen: str
    ruta: str
    parametro: str
    intencion_final: str | None = None
    cerrada: bool = False
    eventos: list[tuple[int, str, dict[str, Any]]] = field(default_factory=list)


class RegistroSimulado:
    def __init__(self, *, fallar_en: str | None = None) -> None:
        """`fallar_en`: "conectar", "abrir_sesion", "cerrar_sesion" o el tipo de un evento."""
        self.fallar_en = fallar_en
        self.sesiones: dict[UUID, SesionSimulada] = {}
        self.aperturas = 0

    def _quizas_fallar(self, operacion: str) -> None:
        if operacion == self.fallar_en:
            raise ErrorRegistro(f"fallo simulado en {operacion}")

    @contextmanager
    def __call__(self):
        self._quizas_fallar("conectar")
        self.aperturas += 1
        yield self

    def abrir_sesion(self, origen: str, ruta: str, parametro: str) -> UUID:
        self._quizas_fallar("abrir_sesion")
        sesion_id = uuid4()
        self.sesiones[sesion_id] = SesionSimulada(origen, ruta, parametro)
        return sesion_id

    def registrar_evento(self, sesion_id: UUID, paso: int, tipo: str, detalle: dict[str, Any]) -> None:
        self._quizas_fallar(tipo)
        self.sesiones[sesion_id].eventos.append((paso, tipo, detalle))

    def cerrar_sesion(self, sesion_id: UUID, intencion: str) -> None:
        self._quizas_fallar("cerrar_sesion")
        sesion = self.sesiones[sesion_id]
        sesion.cerrada = True
        sesion.intencion_final = intencion

    # ayudas para las aserciones
    def unica(self) -> tuple[UUID, SesionSimulada]:
        assert len(self.sesiones) == 1, f"se esperaba una sesión, hay {len(self.sesiones)}"
        return next(iter(self.sesiones.items()))

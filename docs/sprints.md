# Umbra · Estado de los sprints

Framework extensible de engaño y contención activa asistido por IA para la caracterización de ataques de inyección en aplicaciones web.
Méndez Jaimes · Niño Ariza · Director: Fabián Enrique Suárez Carvajal · Codirector: Yamid Gabriel Gamba González · UNAB.

Repositorio: https://github.com/activedefense-lab/umbra · Tablero: https://github.com/orgs/activedefense-lab/projects/1
Actualizado: 2026-10-13. Sin fechas: cada sprint cierra cuando su entregable cumple el criterio de cierre.

| # | Sprint | Criterio de cierre | Lidera | Días | Estado |
|---|---|---|---|---|---|
| 0 | Casa del proyecto | Repo con estructura, `main` protegida, tablero con milestones, issues del sprint 1, primer PR integrado con revisión | Ambos | 1–2 | **Cerrado** |
| 1 | Esqueleto de punta a punta | commix ataca → se detecta, clasifica, recibe respuesta generada y queda registrada; informe impreso; CI en verde | S / C | 7–10 | En curso |
| 2 | Conjunto de datos v1 (CWE-78) | ≥ 200 cargas útiles con doble etiquetado, grado de acuerdo, desacuerdos al codirector; conjunto de control | Ambos | 6–8 | Por hacer |
| 3 | Decisión de contención | ADR-001 aprobado por el director; informe de restricciones de virtualización | Santiago | 5–7 | Por hacer |
| 4 | Requisitos y diseño detallado | Especificación 29148 revisada en cruzado; contrato de complementos v1; trazabilidad v1; plan de pruebas | Ambos | 8–10 | Por hacer |
| 5 | Clasificador de intención v1 | Inferencia ≥ 80 %; falsos positivos ≤ 5 %; pruebas cruzadas | Camila | 8–10 | Por hacer |
| 6 | Señuelo dinámico v1 | Sesión coherente en varias peticiones; latencia dentro del presupuesto | Camila | 8–10 | Por hacer |
| 7 | Contención integrada | Ninguna acción alcanza la app real ni la red, verificado con captura de tráfico | Santiago | 8–10 | Por hacer |
| 8 | Registro forense e informe | Informe automático por sesión; trazas anonimizadas | Santiago | 6–8 | Por hacer |
| 9 | Cliente de visualización | El defensor consulta sesiones e informes | Camila | 6–8 | Por hacer |
| 10 | Complemento CWE-79 | Cero líneas cambiadas fuera de `complementos/` | Ambos | 6–8 | Por hacer |
| 11 | Línea base y conjunto de control | Suricata y señuelo estático operativos; guion aprobado por el director | Santiago | 5–7 | Por hacer |
| 12 | Experimento de ablación | Resultados de las cinco métricas (Tabla 5) con análisis | Ambos | 6–8 | Por hacer |
| 13 | Informe final y sustentación | Documento final entregado; código publicado | Ambos | 10–12 | Por hacer |

Sprints 0–3 = Fase 0 del anteproyecto (evidencia TRL 3). Sprints 4–13 = diseño, construcción y validación (TRL 4). S = Santiago (infraestructura y contención); C = Camila (inteligencia).

## Sprint 0 · Cerrado el 2026-10-13

- Organización `activedefense-lab` (ambos propietarios) y repositorio público `umbra`, licencia Apache-2.0.
- Estructura por contenedores del C4: `detector/`, `senuelo/`, `registro/`, `objetivo/`, `complementos/cwe78/`, `infra/`, `docs/`.
- `main` protegida (PR + 1 aprobación, sin force-push); plantillas de issue y PR; etiquetas por línea y fase; 14 milestones.
- Tablero `Umbra · Sprints` con flujo automático; issues #1–#6 (sprint 0) y #9–#16 (sprint 1) con líder asignado.
- PR #7 y #8 integrados con revisión cruzada. ADR-000 aceptado.

## Pendiente de decisión con el director

1. Aval formal del cambio del primer caso de uso a CWE-78 (ya reflejado en la Entrega 2).
2. Umbrales de las métricas de validación (Tabla 5 del anteproyecto).
3. Tecnología de contención (tras el sprint 3, ADR-001).

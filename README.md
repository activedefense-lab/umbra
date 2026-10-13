# Umbra

**Framework extensible de engaño y contención activa asistido por inteligencia artificial para la caracterización de ataques de inyección en aplicaciones web.**

Proyecto de grado · Ingeniería de Sistemas · Universidad Autónoma de Bucaramanga (UNAB).
Autores: Noel Santiago Méndez Jaimes y Nicole Camila Niño Ariza.
Director: Fabián Enrique Suárez Carvajal. Codirector: Yamid Gabriel Gamba González.

## Propósito

Los sistemas de detección de intrusiones y los cortafuegos de aplicación web detectan y bloquean un ataque de inyección, pero no sostienen interacción con el adversario ni infieren su objetivo. Umbra, ante una inyección contra una aplicación web, **infiere la intención del atacante**, **genera un señuelo verosímil** con un modelo de lenguaje local, **lo contiene** en un entorno confinado y **produce un informe forense** de su comportamiento.

Alcance: categoría de inyección de OWASP (A05:2025). Primer caso de uso: inyección de comandos del sistema operativo (CWE-78). Segundo: Cross-Site Scripting (CWE-79), que demuestra la extensibilidad sobre un intérprete distinto. Otros tipos, incluida la inyección SQL, quedan fuera del alcance como complementos futuros.

Umbra es estrictamente defensivo: el señuelo nunca ejecuta comandos reales, el framework no responde con acciones ofensivas y opera solo sobre infraestructura propia de laboratorio.

## Arquitectura: flujo de ocho pasos

Diagrama de contenedores (C4, nivel 2) del anteproyecto. Cada carpeta de este repositorio corresponde a un contenedor.

| Paso | Qué ocurre | Contenedor | Carpeta |
|---|---|---|---|
| 1 | El atacante envía una petición maliciosa a la aplicación web objetivo. | Aplicación objetivo (Laravel) | `objetivo/` |
| 2 | La aplicación, instrumentada, deriva la carga útil sospechosa al detector. | Aplicación objetivo | `objetivo/` |
| 3 | El detector clasifica la carga útil y estima la intención del adversario. | Detección e inferencia (Python, scikit-learn) | `detector/` |
| 4 | El generador abre una sesión en el entorno de contención y produce respuestas coherentes con la intención. | Generador de señuelo (Ollama) · Entorno de contención | `senuelo/` · `infra/` |
| 5 | Las respuestas llegan al atacante a través de la aplicación; interactúa con el señuelo, nunca con el sistema real. | Aplicación objetivo | `objetivo/` |
| 6 | Todos los eventos de la sesión se escriben con trazas anonimizadas. | Registro forense (PostgreSQL) | `registro/` |
| 7 | El cliente de visualización consulta el registro. | Visualización | (sprint 9) |
| 8 | El defensor recibe el informe forense del incidente. | Defensor | — |

Los **complementos** (`complementos/`) materializan la extensibilidad: cada tipo de inyección aporta sus reglas de detección, su catálogo de intenciones y sus plantillas de señuelo mediante una interfaz común, sin modificar el núcleo.

## Estructura del repositorio

```text
docs/            Documentación: ADR, plan de sprints, trazabilidad, protocolo de datos
detector/        Detección e inferencia (Python)
senuelo/         Generador de señuelo (Python + Ollama)
registro/        Registro forense (PostgreSQL)
objetivo/        Instrumentación de la aplicación objetivo (Laravel)
complementos/    Complementos por tipo de inyección (cwe78/, cwe79/)
infra/           docker-compose, scripts de aprovisionamiento, CI, contención
```

La aplicación objetivo es un banco de pruebas con vulnerabilidades intencionales que vive en su propio repositorio; no forma parte del framework.

## Metodología y validación

Investigación aplicada. Gestión con el ciclo PHVA y las fases del PMBOK; construcción con un modelo en V híbrido, donde cada requisito y caso de abuso tiene su prueba antes de escribir código. El trabajo se organiza en sprints por criterio de cierre (`docs/plan.md`).

Validación mediante estudio de ablación en laboratorio frente a una línea base de defensa pasiva (Suricata y un señuelo estático de respuestas fijas), con ataques ejecutados por commix y XSStrike sobre un conjunto de ≥ 200 cargas útiles por tipo con doble etiquetado. Métricas: inferencia de intención ≥ 80 % (CWE-78), contención 100 %, credibilidad mayor que la línea base, falsos positivos ≤ 5 %, extensibilidad con cero cambios en el núcleo al añadir CWE-79. Meta: TRL 4.

## Forma de trabajo

- Una issue por tarea, una rama por issue, un PR por rama. Ningún PR se integra sin revisión aprobada del otro integrante. Nunca `push --force` sobre `main`.
- Quien lidera una tarea abre el PR; el otro revisa y escribe las pruebas de integración de esa parte.
- Decisiones de arquitectura en `docs/adr/`.

## Licencia

Apache License 2.0. Véase `LICENSE`.

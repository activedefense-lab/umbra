# Plan de trabajo por sprints

Versión 2 · Documento interno del equipo · No forma parte de ninguna entrega académica.

Autores: Noel Santiago Méndez Jaimes, Nicole Camila Niño Ariza. Director: Fabián Enrique Suárez Carvajal. Codirector: Yamid Gabriel Gamba González. Universidad Autónoma de Bucaramanga, Ingeniería de Sistemas.

## 1. Qué cambia respecto a la versión 1

La versión 1 organizaba el trabajo por fechas y dejaba la construcción del framework para Proyecto de Grado II. Esta versión elimina las fechas y cambia el foco: el equipo trabaja desde ahora como si ya estuviera en la fase de construcción; el calendario académico solo marca los hitos de entrega del anteproyecto, que se atienden en paralelo. Los sprints se ordenan por dependencia técnica y se estiman en días de trabajo. Un sprint termina cuando su entregable existe y cumple el criterio de cierre; entonces empieza el siguiente.

El documento es coherente con el diseño metodológico del anteproyecto: el modelo en V fija qué se construye y cómo se verifica; los sprints fijan el orden y el reparto; cada sprint cierra un ciclo PHVA. No se adopta Scrum: "sprint" significa aquí un bloque de trabajo con un entregable definido.

**Estándar de calidad.** Todo sprint se construye con el mejor estándar posible: código revisado por el otro integrante, pruebas que verifican el criterio de cierre, scripts versionados y documentación al día. Lo que distingue un sprint temprano de uno tardío es el alcance, no la calidad. El esqueleto del sprint 1 es la primera versión real del framework; todo lo que se escriba en él permanece en el producto final.

## 2. Reglas de trabajo

### 2.1 Reparto

El equipo trabaja en sesiones conjuntas con pantalla compartida y ambos integrantes conocen todo el sistema. Cada línea tiene un líder que conduce la tarea y abre el PR; el otro revisa, prueba e integra.

| Línea | Lidera | Componentes | Revisa |
|---|---|---|---|
| Infraestructura y contención | Santiago | Instrumentación de la aplicación objetivo; entorno de contención; registro forense (PostgreSQL); scripts de aprovisionamiento; integración continua. | Camila |
| Inteligencia | Camila | Detección e inferencia (Python, scikit-learn); generador de señuelo (Ollama); cliente de visualización. | Santiago |
| Conjunto | Ambos | Repositorio y tablero; contrato de complementos; complementos CWE-78 y CWE-79; conjunto de datos con doble etiquetado; integración; experimento de validación; documentación. | Director |

### 2.2 Dónde vive el proyecto

- Repositorio propio del framework (`activedefense-lab/umbra`), separado del repositorio de la aplicación objetivo. La aplicación objetivo es el banco de pruebas; el framework es otro producto. Véase `docs/adr/ADR-000-estructura.md`.
- Tablero en GitHub Projects (`Umbra · Sprints`): columnas Por hacer, En curso, En revisión y Hecho; un milestone por sprint; una issue por tarea de este plan, con líder y etiquetas por línea (`linea:*`) y por fase del modelo en V (`fase:*`).
- Ramas y PR: una rama por issue; ningún PR se integra sin revisión aprobada del otro integrante; el PR enlaza la issue (`Closes #N`) y la prueba que la verifica. Nunca `push --force` sobre `main`.
- `docs/`: decisiones de arquitectura (ADR), protocolo del conjunto de datos, matriz de trazabilidad requisito → componente → issue → prueba, y este plan.
- Bitácora: cada sprint cerrado se registra en el acta de la tutoría siguiente, con el enlace al milestone.

### 2.3 Ritmo

Sesiones conjuntas de unas cuatro horas, tantas por semana como la carga académica permita. Tutoría con el director los jueves de 4:00 a 5:00 p. m., que funciona como revisión del avance: a cada tutoría se lleva un sprint cerrado o un avance medible. Al abrir un sprint se planean sus tareas en el tablero; al cerrarlo se verifica el criterio de cierre y se anota lo aprendido. Si un sprint se atrasa, se recorta el alcance del siguiente; el complemento CWE-79 es el primer candidato a recorte.

### 2.4 Hitos académicos en paralelo

Entrega final del anteproyecto (secciones 7 a 10, ya en borrador) del 9 al 13 de noviembre de 2026 y sustentación el 17 de noviembre. Lo construido en los sprints 0 a 3 es la evidencia de la Fase 0 y del nivel TRL 3 que el anteproyecto declara, y se incorpora al documento final y a la presentación.

## 3. Resumen de sprints

| Sprint | Nombre | Entregable | Días |
|---|---|---|---|
| 0 | Casa del proyecto | Repositorio, tablero, estructura, convenciones y primera issue cerrada | 1–2 |
| 1 | Esqueleto de punta a punta | Flujo de 8 pasos con componentes mínimos; demostración con commix | 7–10 |
| 2 | Conjunto de datos v1 (CWE-78) | ≥ 200 cargas útiles etiquetadas por intención con doble etiquetado y grado de acuerdo | 6–8 |
| 3 | Decisión de contención | Pruebas de gVisor y microVM en los equipos; ADR definitivo; informe de restricciones | 5–7 |
| 4 | Requisitos y diseño detallado | Especificación ISO/IEC/IEEE 29148, casos de abuso, C4 nivel 3, contrato de complementos | 8–10 |
| 5 | Clasificador de intención v1 | Modelo scikit-learn evaluado; inferencia medida sobre el conjunto de datos | 8–10 |
| 6 | Señuelo dinámico v1 | Plantillas por intención, caché, latencia medida frente a respuestas fijas | 8–10 |
| 7 | Contención integrada | Entorno de contención real en el flujo; verificación con captura de tráfico | 8–10 |
| 8 | Registro forense e informe | Esquema definitivo, anonimización, informe de incidente generado | 6–8 |
| 9 | Cliente de visualización | Consulta del registro y presentación del informe | 6–8 |
| 10 | Complemento CWE-79 | Segundo complemento sin cambios en el núcleo; medición de extensibilidad | 6–8 |
| 11 | Línea base y conjunto de control | Suricata, señuelo estático, peticiones legítimas, guion del experimento | 5–7 |
| 12 | Experimento de ablación | Ejecución, análisis frente a la Tabla 5 del anteproyecto | 6–8 |
| 13 | Informe final y sustentación | Informe de validación, documento final, código publicado | 10–12 |

Los sprints 0 a 3 constituyen la Fase 0 del anteproyecto; los sprints 4 a 13 cubren el diseño, la construcción y la validación. Un día de trabajo es una sesión conjunta de unas cuatro horas. Las estimaciones se revisan al cerrar cada sprint.

## 4. Sprints detallados

### Sprint 0. Casa del proyecto

Estimación: 1–2 días. Fase del modelo en V: Fase 0.
Objetivo: dejar el proyecto con un lugar propio y reglas de trabajo verificables.
Criterio de cierre: repositorio con estructura, rama protegida, tablero con milestones y las issues del sprint 1 creadas; primera PR integrada con revisión.
Se muestra al director: el repositorio, el tablero y la hoja de sprints.

| Tarea | Tecnología | Lidera | Días |
|---|---|---|---|
| Crear el repositorio del framework (licencia abierta, README con el propósito y la arquitectura de 8 pasos, .gitignore, estructura de carpetas). | GitHub | Ambos | 0,5 |
| Proteger la rama principal; plantilla de PR con enlace a issue y prueba; plantilla de issue. | GitHub | Camila | 0,25 |
| Tablero con columnas y milestones de los sprints 0 a 13; etiquetas por línea y por fase. | GitHub Projects | Santiago | 0,25 |
| Crear las issues del sprint 1 con líder asignado. | GitHub | Ambos | 0,25 |
| `docs/plan.md` y `docs/adr/ADR-000-estructura.md`. | Markdown | Ambos | 0,5 |
| Hoja de una página con los 14 sprints y su estado, para la tutoría. | Markdown/PDF | Ambos | 0,25 |

### Sprint 1. Esqueleto de punta a punta

Estimación: 7–10 días. Fase: Fase 0 (prototipo que verifica la arquitectura).
Objetivo: construir el flujo completo de 8 pasos con cada componente en su versión mínima, de modo que la arquitectura C4 funcione en la práctica.
Criterio de cierre: commix ataca el endpoint; la petición se detecta, se clasifica, recibe una respuesta generada y queda registrada; el informe de la sesión se imprime; todas las pruebas pasan en integración continua.
Se muestra al director: demostración en vivo con commix y el registro de la sesión en PostgreSQL.

| Tarea | Tecnología | Lidera | Días |
|---|---|---|---|
| Endpoint vulnerable a CWE-78 en la aplicación objetivo y middleware que reenvía la petición sospechosa al detector. Documentar el caso de abuso. | Laravel, PHP | Santiago | 1,5 |
| Servicio de detección: API que recibe la petición, aplica reglas de metacaracteres y asigna una intención provisional por palabras clave. Pruebas unitarias. | Python, FastAPI, pytest | Camila | 1,5 |
| Generador de señuelo: cliente de Ollama con prompt de intérprete simulado coherente con la intención; sin ejecución real. Medir latencia. | Python, Ollama | Camila | 1,5 |
| Registro forense mínimo: esquema de sesiones y eventos; cada paso escribe su evento; consulta que imprime el informe de una sesión. | PostgreSQL, SQL | Santiago | 1 |
| Contrato de complementos v0: interfaz de reglas, catálogo de intenciones y plantillas; el complemento cwe78 la implementa. | Python | Ambos | 1 |
| Infraestructura del esqueleto: docker-compose con detector, señuelo, PostgreSQL y aplicación objetivo; scripts de arranque; CI en cada PR. | Docker Compose, GitHub Actions | Santiago | 1 |
| Integración de punta a punta y pruebas cruzadas: cada uno escribe la prueba de integración del componente del otro. | pytest, PHPUnit | Ambos | 1 |
| Demostración: commix contra el endpoint; registro de la sesión; informe impreso. Grabar la demostración. | commix | Ambos | 0,5 |

### Sprint 2. Conjunto de datos v1 (CWE-78)

Estimación: 6–8 días. Fase: Requisitos (insumo de la validación).
Objetivo: construir el conjunto de cargas útiles que exige el anteproyecto antes de entrenar el clasificador.
Criterio de cierre: ≥ 200 cargas útiles CWE-78 etiquetadas por los dos integrantes, grado de acuerdo calculado y desacuerdos remitidos al codirector; conjunto de control de peticiones legítimas.
Se muestra al director: el protocolo, el conjunto de datos y el grado de acuerdo.

| Tarea | Tecnología | Lidera | Días |
|---|---|---|---|
| Protocolo del conjunto de datos: fuentes públicas, reglas de etiquetado por intención, procedimiento de doble etiquetado y cálculo del grado de acuerdo. | Markdown | Ambos | 1 |
| Recolección: cargas útiles de repositorios públicos y de las sesiones de commix del sprint 1; CSV con identificador, carga útil, fuente. | Python, CSV | Camila | 2 |
| Etiquetado independiente por cada integrante; comparación; lista de desacuerdos para el codirector. | Hoja de cálculo | Ambos | 2 |
| Conjunto de control de peticiones legítimas de la aplicación objetivo. | Python | Santiago | 1 |

### Sprint 3. Decisión de contención

Estimación: 5–7 días. Fase: Fase 0 / arquitectura.
Objetivo: cerrar el riesgo ya materializado de la virtualización anidada con una decisión documentada.
Criterio de cierre: ADR-001 aprobado por el director; informe de restricciones de virtualización.
Se muestra al director: las pruebas comparadas y el ADR.

| Tarea | Tecnología | Lidera | Días |
|---|---|---|---|
| Verificar si WSL2 en los equipos del laboratorio expone KVM; prueba mínima de microVM. | WSL2, Firecracker | Santiago | 2 |
| Prueba de contenedor con aislamiento reforzado (gVisor); comparación de arranque, aislamiento y complejidad. | gVisor, Docker | Santiago | 2 |
| ADR-001 decisión de contención, con criterios y resultado; informe de restricciones de virtualización (Tabla 7 del anteproyecto). | Markdown | Ambos | 1 |

### Sprint 4. Requisitos y diseño detallado

Estimación: 8–10 días. Fase: requisitos, arquitectura y componentes (brazo izquierdo de la V).
Objetivo: fijar la especificación antes de reemplazar los componentes mínimos por los definitivos.
Criterio de cierre: especificación revisada en cruzado; contrato de complementos v1; matriz de trazabilidad v1; plan de pruebas.
Se muestra al director: la especificación y los diagramas.

| Tarea | Tecnología | Lidera | Días |
|---|---|---|---|
| Requisitos funcionales y no funcionales por línea conforme a ISO/IEC/IEEE 29148; casos de uso y casos de abuso. | Markdown, UML | Ambos | 4 |
| Diagramas C4 de nivel 3 de cada contenedor; diagramas de secuencia del flujo de 8 pasos; modelo de datos definitivo del registro. | C4, PlantUML | Ambos | 3 |
| Contrato de complementos v1 y plan de pruebas por nivel de la V; matriz de trazabilidad v1. | Python, Markdown | Ambos | 2 |

### Sprint 5. Clasificador de intención v1

Estimación: 8–10 días. Fase: implementación.
Objetivo: reemplazar las reglas provisionales por el clasificador entrenado.
Criterio de cierre: inferencia ≥ 80 % sobre el conjunto de prueba y falsos positivos ≤ 5 % sobre el conjunto de control; pruebas cruzadas en verde.
Se muestra al director: la métrica de inferencia.

| Tarea | Tecnología | Lidera | Días |
|---|---|---|---|
| Ingeniería de características sobre las cargas útiles; entrenamiento y comparación de modelos; selección. | scikit-learn | Camila | 4 |
| Integración del clasificador en el servicio de detección en reemplazo de las reglas provisionales; umbral de confianza. | Python, FastAPI | Camila | 2 |
| Evaluación de inferencia sobre el conjunto de prueba y de falsos positivos sobre el conjunto de control; pruebas cruzadas. | pytest | Santiago | 2 |

### Sprint 6. Señuelo dinámico v1

Estimación: 8–10 días. Fase: implementación.
Objetivo: reemplazar el prompt único por un generador con estado y plantillas por intención.
Criterio de cierre: sesión coherente a lo largo de varias peticiones; latencia medida y dentro del presupuesto definido.
Se muestra al director: comparación de credibilidad y latencia frente a respuestas fijas.

| Tarea | Tecnología | Lidera | Días |
|---|---|---|---|
| Plantillas de señuelo por intención y por comando frecuente; estado de sesión (directorio, usuario, archivos simulados). | Python, Ollama | Camila | 4 |
| Caché de respuestas frecuentes y presupuesto de latencia; medición frente a respuestas fijas. | Python | Camila | 2 |
| Pruebas cruzadas de coherencia y latencia. | pytest | Santiago | 2 |

### Sprint 7. Contención integrada

Estimación: 8–10 días. Fase: implementación e integración.
Objetivo: confinar la sesión del atacante en el entorno elegido.
Criterio de cierre: ninguna acción del atacante alcanza la aplicación real ni la red, verificado por captura de tráfico.
Se muestra al director: la prueba de contención.

| Tarea | Tecnología | Lidera | Días |
|---|---|---|---|
| Implementación del entorno de contención según el ADR-001, aprovisionado por scripts; una sesión confinada por atacante. | Según ADR | Santiago | 4 |
| Integración con el generador de señuelo: la sesión vive en el entorno confinado. | Python | Ambos | 2 |
| Verificación de contención con captura de tráfico; pruebas cruzadas. | tcpdump, Wireshark | Camila | 2 |

### Sprint 8. Registro forense e informe

Estimación: 6–8 días. Fase: implementación.
Objetivo: completar el registro y el informe de incidente.
Criterio de cierre: informe generado automáticamente para cualquier sesión; trazas anonimizadas.
Se muestra al director: un informe de incidente real.

| Tarea | Tecnología | Lidera | Días |
|---|---|---|---|
| Esquema definitivo del registro forense; anonimización de trazas conforme a la Ley 1581 de 2012. | PostgreSQL | Santiago | 3 |
| Generación del informe de incidente por sesión (intención inferida, línea de tiempo, comandos, respuestas). | Python | Santiago | 2 |
| Pruebas cruzadas. | pytest | Camila | 1 |

### Sprint 9. Cliente de visualización

Estimación: 6–8 días. Fase: implementación.
Objetivo: completar el paso 7 del flujo.
Criterio de cierre: el defensor consulta sesiones e informes desde el cliente.
Se muestra al director: el cliente funcionando.

| Tarea | Tecnología | Lidera | Días |
|---|---|---|---|
| Cliente de visualización: lista de sesiones, detalle y descarga del informe. | Definida en el diseño | Camila | 5 |
| Pruebas cruzadas. | — | Santiago | 1 |

### Sprint 10. Complemento CWE-79

Estimación: 6–8 días. Fase: validación de extensibilidad.
Objetivo: demostrar que el núcleo admite un nuevo tipo de inyección sin cambios.
Criterio de cierre: complemento operativo con cero líneas cambiadas fuera de `complementos/`.
Se muestra al director: la medición de extensibilidad.

| Tarea | Tecnología | Lidera | Días |
|---|---|---|---|
| Complemento CWE-79 implementado solo con la interfaz del contrato: reglas, intenciones y plantillas para el navegador. | Python | Ambos | 5 |
| Medición de extensibilidad: líneas cambiadas fuera del complemento (meta: cero). | git diff | Ambos | 1 |

### Sprint 11. Línea base y conjunto de control

Estimación: 5–7 días. Fase: validación.
Objetivo: dejar lista la comparación del estudio de ablación.
Criterio de cierre: Suricata y señuelo estático operativos; guion del experimento aprobado por el director.
Se muestra al director: la línea base corriendo.

| Tarea | Tecnología | Lidera | Días |
|---|---|---|---|
| Línea base: Suricata con reglas de comunidad y señuelo estático de respuestas fijas (mismo framework sin generador). | Suricata | Santiago | 3 |
| Guion del experimento y hoja de registro de métricas; conjunto de datos CWE-79. | Markdown, CSV | Ambos | 3 |

### Sprint 12. Experimento de ablación

Estimación: 6–8 días. Fase: validación.
Objetivo: medir el framework frente a la línea base.
Criterio de cierre: resultados de las cinco métricas de la Tabla 5 del anteproyecto con su análisis.
Se muestra al director: los resultados.

| Tarea | Tecnología | Lidera | Días |
|---|---|---|---|
| Ejecución del experimento con commix y XSStrike frente al framework y a la línea base. | Laboratorio | Ambos | 3 |
| Análisis de resultados contra los criterios de la Tabla 5 del anteproyecto. | Python (pandas) | Ambos | 3 |

### Sprint 13. Informe final y sustentación

Estimación: 10–12 días. Fase: cierre.
Objetivo: documentar y sustentar.
Criterio de cierre: documento final entregado; código publicado.
Se muestra al director: la sustentación.

| Tarea | Tecnología | Lidera | Días |
|---|---|---|---|
| Informe de validación y discusión de resultados; documento final. | — | Ambos | 8 |
| Preparación de la sustentación; publicación del código con licencia abierta y documentación de uso. | GitHub | Ambos | 3 |

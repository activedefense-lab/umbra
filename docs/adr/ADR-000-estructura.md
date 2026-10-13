# ADR-000. Repositorio propio del framework, estructura por contenedores y convenciones de trabajo

- Estado: aceptado
- Fecha: 2026-10-13
- Deciden: Noel Santiago Méndez Jaimes, Nicole Camila Niño Ariza
- Issues: #1, #2, #3, #5

## Contexto

El proyecto de grado produce un framework de engaño y contención activa cuya arquitectura está descrita en el anteproyecto como un diagrama de contenedores C4 (nivel 2) con un flujo de ocho pasos. Para probarlo se usa una aplicación web propia sobre Laravel, desplegada en una máquina virtual de laboratorio, que ya tiene su propio repositorio y su propio ciclo de vida. Al iniciar la construcción había que decidir dónde vive el código del framework, cómo se organiza y bajo qué reglas trabajan dos personas con revisión del director.

## Decisión

1. **Repositorio propio y separado de la aplicación objetivo.** El framework vive en `activedefense-lab/umbra`. La aplicación objetivo es un banco de pruebas con vulnerabilidades intencionales; el framework es un producto distinto que debe poder instrumentar cualquier aplicación. Mezclarlos confundiría el sistema atacado con el sistema defensor y haría imposible medir la extensibilidad del núcleo. La carpeta `objetivo/` contiene solo la instrumentación que el framework añade (endpoint de laboratorio, middleware de derivación, caso de abuso), no la aplicación.

2. **Organización de GitHub con nombre general.** El repositorio pertenece a la organización `activedefense-lab`, con ambos autores como propietarios. El nombre de la organización no es el del producto porque las organizaciones no redirigen al renombrarse; el repositorio sí puede renombrarse sin romper enlaces.

3. **Una carpeta por contenedor del diagrama C4.** `detector/` (detección e inferencia), `senuelo/` (generador de señuelo), `registro/` (registro forense), `objetivo/` (instrumentación de la aplicación objetivo), `infra/` (docker-compose, scripts, CI y entorno de contención), `complementos/<cwe>/` (un complemento por tipo de inyección) y `docs/` (ADR, plan, trazabilidad, protocolo de datos). La correspondencia uno a uno entre documento y código permite que el jurado verifique la arquitectura leyendo el repositorio. La meta de extensibilidad (cero cambios en el núcleo al añadir CWE-79) se mide exactamente como "líneas cambiadas fuera de `complementos/`".

4. **Licencia Apache-2.0.** Licencia abierta compatible con la Política de Propiedad Intelectual de la UNAB (2021); a diferencia de MIT incluye una concesión explícita de patentes, pertinente dado el análisis de patentes de la sección 6.2.3 del anteproyecto.

5. **Convenciones de trabajo.**
   - Una issue por tarea del plan de sprints; una rama por issue, nombrada `<número>-<descripción-corta>`; un PR por rama.
   - `main` protegida por ruleset sin excepciones: PR obligatorio, una aprobación del otro integrante, aprobaciones descartadas ante commits nuevos, hilos de revisión resueltos, sin `push --force` ni borrado.
   - Los PR cierran issues con la palabra clave `Closes #N` (GitHub solo reconoce las palabras clave en inglés).
   - Quien lidera la tarea abre el PR; el otro revisa y escribe las pruebas de integración de esa parte.
   - Milestones: uno por sprint (0–13), con el criterio de cierre del plan en su descripción. Etiquetas `linea:*` (quién lidera) y `fase:*` (fase del modelo en V).
   - Tablero GitHub Projects `Umbra · Sprints` con columnas Por hacer, En curso, En revisión, Hecho; las issues y PR abiertos se añaden solos y pasan a Hecho al cerrarse.
   - Decisiones de arquitectura en `docs/adr/ADR-NNN-<tema>.md`, numeradas en orden; un ADR no se edita después de aceptado, se reemplaza con uno nuevo que lo referencia.

## Consecuencias

- Toda contribución queda trazada issue → rama → PR → revisión → merge, que es la evidencia de trabajo cooperativo que el director puede auditar.
- El esqueleto del sprint 1 se escribe directamente en la estructura definitiva; nada se construye para desecharlo.
- La aplicación objetivo puede reemplazarse por otra sin tocar `detector/`, `senuelo/`, `registro/` ni `complementos/`.
- Pendiente: ADR-001 (tecnología de contención), que se decide en el sprint 3 tras las pruebas de gVisor y microVM, porque el laboratorio no dispone de virtualización anidada.

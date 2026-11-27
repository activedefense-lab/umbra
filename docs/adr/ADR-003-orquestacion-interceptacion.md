# ADR-003. Orquestación del flujo de interceptación: el detector como punto de entrada único

- Estado: aceptado (PR #25, aprobado por ambos integrantes)
- Fecha: 2026-11-27
- Deciden: Noel Santiago Méndez Jaimes, Nicole Camila Niño Ariza
- Issues: #15
- Relación: aplica la máquina de estados del anteproyecto (sección 7.5) y usa el contrato de ADR-002 sin modificarlo. ADR-001 sigue reservado para la tecnología de contención (sprint 3).

## Contexto

La issue #15 conecta por primera vez el flujo real: herramienta de ataque → aplicación objetivo (middleware `lab.deception`) → detector → señuelo → registro forense. La revisión del código en `main` (umbra `eb67738`, aplicación objetivo `bf439b9`) encontró cuatro brechas:

1. **Contrato incompatible.** El middleware envía `{metodo, ruta, entrada}`; el detector exige `Peticion {origen, ruta, parametro, valor}` con `extra="forbid"`. En el flujo real toda petición recibe 422 y el middleware responde 503. Las pruebas de #9 no lo detectaron porque simulan el detector con `Http::fake()`.
2. **Red.** `lab-target` resuelve `detector:8001`, pero el detector pertenece a otro proyecto de Docker Compose y a otra red.
3. **Sin engaño.** Ante un ataque el middleware responde 409; nunca se solicita la respuesta del señuelo.
4. **Sin registro.** `registro/` es una biblioteca; ningún servicio escribe eventos en el flujo real.

Opciones:

- **A.** El detector es el punto de entrada único: recibe la petición, decide, solicita la respuesta al señuelo, registra y devuelve una decisión.
- **B.** El middleware llama al detector, luego al señuelo y luego al registro.

B acopla la aplicación objetivo a la estructura interna del framework (tres URL, tres contratos y el orden del flujo escrito en PHP) y obliga a repetir esa lógica en cada aplicación protegida, en contra de la extensibilidad declarada en el anteproyecto.

## Decisión

1. Se adopta **A**. El detector expone `POST /interceptar`. La aplicación objetivo conoce una sola URL.
2. **Entrada:** `Peticion` de ADR-002, sin cambios. El middleware envía `origen` = SHA-256 de la IP del cliente, `ruta`, `parametro` y `valor` crudo.
3. **Salida:** modelo `Decision`, propio del núcleo (no cruza la frontera núcleo–complemento):

   | Campo | Valor |
   |---|---|
   | `accion` | `permitir` o `senuelo` |
   | `respuesta` | Texto generado por el señuelo; vacío con `permitir` |
   | `sesion_id` | UUID de la sesión forense; nulo con `permitir` |

   `POST /analizar` se conserva sin cambios para pruebas unitarias y para el experimento de ablación.
4. **Secuencia ante ataque** (`es_ataque = true`): abrir sesión → evento paso 2 `peticion_recibida` → evento paso 3 `veredicto` → `POST /generar` al señuelo → evento paso 4 `respuesta_senuelo` → cerrar sesión con la intención inferida → devolver `accion = senuelo`. Una petición legítima no abre sesión y devuelve `accion = permitir`.
5. **Fallo cerrado.** Invariante de la máquina de estados: la petición llega a la aplicación objetivo solo si f(p) = legítima. Si el señuelo o el registro fallan, el detector responde 503 y el middleware bloquea. La decisión nunca se degrada a `permitir`.
6. **Middleware:** `permitir` → controlador real. `senuelo` → HTTP 200 con la misma forma JSON del endpoint real (`host`, `exit_code` = 0, `output` = `respuesta`), sin exponer `sesion_id`. Cualquier error, tiempo agotado o cuerpo inválido → 503. Se elimina la respuesta 409.
7. **Red:** red Docker `arya-lab`, creada por el Compose del framework (`infra/docker-compose.yml`), que es su dueño; la aplicación objetivo la declara como externa y, por tanto, el framework se levanta primero. Solo el detector se une a ella desde el framework; `lab-target` se une desde el Compose de la aplicación objetivo. El señuelo y PostgreSQL no se exponen a la aplicación objetivo.
8. **Tiempo de espera:** 2 s no alcanzan para la generación con Ollama. `UMBRA_DETECTOR_TIMEOUT` pasa a 30 s en el laboratorio; el presupuesto de latencia se mide en el sprint 6.
9. **Fuera de alcance:** continuidad de sesión entre peticiones (sprint 6), contención (sprints 3 y 7) e informe automático (sprint 8). En este esqueleto, una petición maliciosa equivale a una sesión.

## Consecuencias

- El detector depende del señuelo y de PostgreSQL; `depends_on` ya declara PostgreSQL.
- Los falsos negativos llegan a la aplicación objetivo (anteproyecto, sección 7.5); en el laboratorio corre en el contenedor aislado `lab-target`.
- Pruebas cruzadas: Santiago escribe las de `/interceptar` (línea de Camila); Camila escribe las del middleware (línea de Santiago).
- **Prueba de aceptación de #15:** con los dos Compose en marcha, (a) una petición benigna recibe el ping real (200); (b) una inyección recibe la respuesta del señuelo (200) y el registro muestra una sesión con los eventos de los pasos 2, 3 y 4; (c) con el señuelo detenido, la misma inyección recibe 503.

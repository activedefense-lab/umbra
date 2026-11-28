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

## Precisiones de implementación (2026-11-27, PR del señuelo y PR de `/interceptar`)

No cambian ninguna decisión anterior. Concretan cómo se implementan, con lo acordado entre los dos integrantes y las observaciones de una revisión técnica externa.

1. **Cadena de tiempos de espera, configurable:** middleware 30 s (`UMBRA_DETECTOR_TIMEOUT`) > detector→señuelo 25 s (`UMBRA_SENUELO_TIMEOUT`) > señuelo→Ollama 20 s (`OLLAMA_TIMEOUT`). Son valores iniciales; el presupuesto de latencia se mide en el sprint 6. El tiempo de espera de `httpx` limita cada operación (conexión, envío, lectura), no la duración total.
2. **Arranque en frío de Ollama:** el señuelo mantiene el modelo cargado (`OLLAMA_KEEP_ALIVE`, `30m`; `-1` para la demostración y el experimento) y lo calienta al arrancar sin bloquearse. `GET /listo` informa si puede generar. Medido: 38 s con Ollama recién iniciado, 9,2 s con el modelo descargado y 0,3 s con el modelo cargado.
3. **Límites y evidencia de la carga:**
   - El detector analiza siempre la carga **completa**; recortar antes de analizar permitiría esconder una inyección después del límite.
   - Al señuelo se envían como máximo 4096 **caracteres** (límite de `SolicitudSenuelo` en el contrato). El evento del paso 3 registra `valor_senuelo_truncado`.
   - El evento del paso 2 guarda el valor hasta 64 KiB (65 536 **bytes** UTF-8, sin partir caracteres), con `valor_truncado`, `longitud_caracteres`, `longitud_bytes` y el `sha256` de la carga completa. El hash se calcula sobre la codificación UTF-8 de `Peticion.valor` tal como lo recibe el detector, no sobre la petición HTTP original. Si el valor se recorta, el hash y las longitudes permiten verificar la carga completa, pero **no la sustituyen**.
   - Por qué 64 KiB: las cargas de inyección de comandos son de unos cientos de bytes (las de commix rara vez superan 1 KB), y el límite acota lo que se guarda de la carga frente a cuerpos enormes enviados a propósito (RS-07). PostgreSQL admite valores `jsonb` mucho mayores; el límite es una decisión de diseño, no una restricción del esquema.
   - Alcance: los 64 KiB limitan el campo `valor` del evento del paso 2, **no el tamaño de todos los eventos**. Los demás campos tienen sus propias cotas: la evidencia del veredicto la acota el contrato (20 claves × 20 elementos × 4096 caracteres); la respuesta del señuelo, `num_predict` (128 tokens); `ruta` y `parametro` los envía la aplicación objetivo y hoy no tienen límite. Los requisitos definitivos de almacenamiento se fijan con el esquema del registro (sprint 8).
4. **Eventos de la sesión:** paso 2 `peticion_recibida`; paso 3 `veredicto` (complemento, intención, confianza, evidencia); paso 4 `respuesta_senuelo` (respuesta, modelo, temperatura, latencia del señuelo y duración medida por el detector) o, si el señuelo falla, `error_senuelo` (motivo y duración). En ambos casos la sesión se cierra con la intención inferida.
   - `respuesta_senuelo` prueba que la respuesta se **generó y se registró**, no que llegó al atacante: el middleware podría agotar su tiempo de espera o el cliente desconectarse después. No debe interpretarse como evidencia de entrega en las métricas de engaño y contención; confirmar la entrega exigiría un evento de la aplicación objetivo (fuera del alcance del esqueleto).
   - La `SolicitudSenuelo` se construye antes de abrir la sesión. Con un veredicto validado no puede fallar, porque sus campos ya cumplen los tipos del contrato; si un complemento defectuoso creara el veredicto sin validar, el error (500, que el middleware convierte en 503) no deja una sesión a medias ni llama al señuelo.
5. **Fallos del registro:** si PostgreSQL falla en cualquier punto, `/interceptar` responde 503 y el fallo queda en el log del contenedor del detector. Lo escrito antes del fallo se conserva (cada operación hace su propio commit), por lo que puede quedar una **sesión incompleta, sin cierre**; no se puede cerrar una sesión si el propio registro no está disponible. Tampoco se entrega un engaño que no quedó registrado. El detector abre una conexión por interceptación, de modo que se recupera sin reiniciarse cuando PostgreSQL vuelve.
   - Tiempos del registro: `connect_timeout` (3 s) acota la conexión y `statement_timeout` (3 s) cada sentencia en el servidor, incluidas las esperas por bloqueos. No acotan una conexión que se queda colgada en la red a mitad de una operación. En el peor caso la suma puede superar los 30 s del middleware; entonces el middleware responde 503 por su cuenta y el fallo cerrado se mantiene.
6. **Origen:** el middleware envía el SHA-256 de la IP y el registro vuelve a aplicar su función de anonimización (`anonimizar_origen`, con la sal por despliegue del sprint 8). Nunca se guarda la IP en claro.

### Riesgo aceptado: el 503 delata el engaño

Un atacante que logra provocar un 503 (por ejemplo, si el señuelo no está disponible) puede inferir que hay un componente detrás de la aplicación. Se acepta: el fallo cerrado (RS-01) pesa más que pasar desapercibido, porque la alternativa sería dejar pasar la petición a la aplicación real. El 503 no revela detalles internos (el motivo solo queda en el registro forense y en los logs).

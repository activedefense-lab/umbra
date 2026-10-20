# ADR-002. Contrato de complementos: responsabilidades, modelos comunes, descubrimiento y distribución

- Estado: propuesto
- Fecha: 2026-10-20
- Deciden: Noel Santiago Méndez Jaimes, Nicole Camila Niño Ariza
- Issues: #13
- Relación: complementa el punto 3 de ADR-000 sin modificarlo. ADR-001 sigue reservado para la tecnología de contención (sprint 3).

## Contexto

El anteproyecto (sección 7.5) establece que "cada tipo de inyección aporta sus reglas de detección, su catálogo de intenciones y sus plantillas de señuelo mediante una interfaz común, sin modificar el núcleo", y que el segundo complemento, Cross-Site Scripting (CWE-79), "demuestra que el mismo núcleo sirve para un intérprete distinto". ADR-000 mide esa meta como "líneas cambiadas fuera de `complementos/`".

El diagnóstico del código integrado en `main` (commit `1960af2`) encontró cinco acoplamientos que impiden cumplir esa meta:

1. El motor de `detector/src/detector/reglas.py` (metacaracteres, separadores, segmentación que descarta el primer segmento) es la gramática de un intérprete de comandos, no un motor genérico. Un catálogo de datos para ese motor no sirve para analizar XSS.
2. La enumeración `Intencion` está definida dos veces, en `detector/modelos.py` y en `senuelo/modelos.py`, con los mismos seis valores, y esos valores son propios de CWE-78.
3. Los modelos de intercambio presuponen inyección de comandos: `Veredicto` expone `metacaracteres` y `segmentos`, y `SolicitudSenuelo` exige `segmentos`.
4. Las instrucciones del señuelo (`INSTRUCCIONES` en `senuelo/ollama.py`) mezclan las restricciones de seguridad con el contexto de simulación de una terminal.
5. Cada servicio se construye con su propia carpeta como contexto de Docker (`detector/`, `senuelo/`), de modo que un `COPY` no alcanza código compartido fuera de ella.

Las API HTTP del detector y del señuelo todavía no tienen consumidores: el middleware de la aplicación objetivo (#9) y la integración de punta a punta (#15) están pendientes. Es el momento de menor costo para corregir los modelos de intercambio.

## Decisión

1. **Reparto de responsabilidades.**

   | Responsabilidad | Pertenece a |
   |---|---|
   | Recibir solicitudes HTTP | Núcleo (`detector/`, `senuelo/`) |
   | Localizar, validar y cargar complementos | Núcleo (`contrato/`, cargador) |
   | Reconocer la sintaxis del ataque y producir el veredicto | Complemento |
   | Declarar el catálogo de intenciones | Complemento |
   | Aportar el contexto de simulación del señuelo | Complemento |
   | Restricciones de seguridad del señuelo y su composición con el contexto | Núcleo |

2. **Modelos comunes con evidencia extensible.** Los modelos que cruzan la frontera núcleo–complemento viven en `contrato/` y solo contienen datos válidos para cualquier tipo de inyección:
   - `Peticion`: sin cambios (`origen`, `ruta`, `parametro`, `valor`).
   - `Veredicto`: `complemento`, `es_ataque`, `intencion`, `confianza`, `valor_normalizado` y `evidencia`.
   - `SolicitudSenuelo`: `complemento`, `intencion`, `valor_normalizado` y `evidencia`.

   `evidencia` es un diccionario de listas de texto, de un solo nivel, donde cada complemento registra lo que su análisis encontró. CWE-78 registra allí `metacaracteres`, `segmentos` y `coincidencias`; CWE-79 registrará lo propio sin cambiar el modelo. El campo `complemento` existe desde v0 para que el señuelo verifique que la solicitud corresponde a su complemento activo y para que un enrutamiento futuro no cambie el modelo.
   
   **Restricciones estructurales.** Los modelos compartidos rechazan campos desconocidos (`extra="forbid"`) y son inmutables respecto a la reasignación de atributos (`frozen=True`). Esta inmutabilidad no impide modificar las colecciones internas. Los identificadores de complemento, intención y claves de los diccionarios admiten entre 1 y 64 caracteres, comienzan por una letra minúscula y contienen únicamente letras minúsculas, dígitos y guiones bajos. Estas restricciones se verifican mediante pruebas automatizadas.

   **Invariantes.** Se validan en dos capas:
   - *En el modelo* (Pydantic, `model_validator`), lo que depende solo del propio veredicto: si `es_ataque` es falso, `intencion` es `desconocida`, `confianza` es `0` y `evidencia` está vacía; `confianza` está en `[0, 1]`; `evidencia` tiene a lo sumo 20 claves, 20 elementos por lista y 4096 caracteres por elemento (los mismos límites que ya usa `SolicitudSenuelo`).
   - *En el núcleo*, lo que depende del complemento: el campo `complemento` de todo veredicto coincide con el complemento activo del detector, y su `intencion` pertenece al catálogo de ese complemento o es `desconocida`; un veredicto que incumple cualquiera de las dos condiciones es un error del complemento y no se propaga.

3. **Contrato v0.** Una interfaz (`typing.Protocol`) que cada complemento implementa:
   - identidad: `nombre`, `cwe`, `version_contrato`;
   - catálogo de intenciones propio;
   - `analizar(peticion) -> Veredicto`, que incluye el caso "no es un ataque";
   - `contexto_senuelo(solicitud: SolicitudSenuelo) -> ContextoSenuelo`, donde `ContextoSenuelo` tiene dos partes: `simulacion`, texto fijo del complemento que describe el sistema que se simula, y `datos`, un diccionario de cadenas (límite de 4096 caracteres cada una) con la información derivada de la solicitud. `datos` contiene exclusivamente información derivada de la solicitud, nunca instrucciones.

   El catálogo de intenciones es un `frozenset[str]`: no admite duplicados, evita modificaciones accidentales y permite consultar la pertenencia de una intención en tiempo constante promedio. Al cargar un complemento se comprueban su identidad, su catálogo y que cada método pueda recibir un argumento. Esta comprobación no garantiza que el método reciba exactamente uno ni que su firma coincida con la del protocolo; los tipos y las firmas completas forman parte del contrato estático, verificable mediante herramientas como mypy o pyright. La versión del contrato debe ser un `int` auténtico: no se aceptan valores `bool` ni `float`.

   El complemento no construye el texto que contiene la entrada del atacante. El núcleo compone en este orden: restricciones de seguridad → `simulacion` → `datos`, delimitados y marcados como no confiables. Esa separación garantiza la delimitación; no garantiza que el modelo de lenguaje ignore instrucciones contenidas en los datos, lo que se evalúa en la validación (decisión 7).

   Compatibilidad en v0: `version_contrato` debe coincidir exactamente con la versión que declara el núcleo. No se implementa negociación de versiones.

4. **Intenciones por complemento.** Cada complemento declara las suyas y el núcleo las valida al cargarlo y en cada veredicto. El valor `desconocida` lo reserva el núcleo, porque es un concepto del framework (hay inyección pero no se infiere la intención) y no de una CWE; un complemento no puede declararlo. Se elimina la doble definición de `Intencion`. Los valores de intención de CWE-78 no cambian.

5. **Contrato y cargador separados.** El contrato define qué implementa un complemento; el cargador define cómo se descubre. El cargador usa *entry points* de la biblioteca estándar (`importlib.metadata`, grupo `umbra.complementos`) y distingue dos operaciones:
   - `listar()`: lee metadatos de los complementos instalados (nombre, versión) sin ejecutar su código;
   - `cargar(nombre)`: importa, instancia y valida el complemento (identidad, versión de contrato, interfaz, catálogo de intenciones).

   Cada falla tiene un error específico: complemento inexistente, nombre registrado más de una vez, versión de contrato incompatible e implementación inválida. Las pruebas pueden inyectar complementos falsos sin pasar por el descubrimiento.

6. **Instalar no es activar. Varios instalados, uno activo en v0.** El contrato y el cargador no presuponen un único complemento: no hay instancias globales, y cada servicio recibe su complemento activo por inyección (`crear_app(complemento=...)`). En v0 el operador activa uno con la variable de entorno `UMBRA_COMPLEMENTO`, que es obligatoria: si falta o nombra un complemento no instalado, el servicio no arranca y el error lista los instalados. Un complemento instalado pero no activo nunca procesa solicitudes. El señuelo rechaza con `422`, antes de componer instrucción alguna, toda `SolicitudSenuelo` cuyo campo `complemento` no coincida con el activo o cuya `intencion` no pertenezca al catálogo del complemento activo (salvo `desconocida`); así, una solicitud de un complemento nunca se simula con el contexto de otro ni con una intención ajena a su catálogo. El enrutamiento simultáneo de varios complementos queda pendiente.

7. **Modelo de confianza del señuelo.** Los complementos son código de confianza que instala el operador del framework; el adversario es el atacante web, no el autor del complemento. El núcleo compone siempre sus restricciones de seguridad con el contexto del complemento y marca la entrada del atacante, incluida la `evidencia`, como dato no confiable. No se promete aislamiento frente a un complemento malicioso (corre en el mismo proceso) ni obediencia perfecta del modelo de lenguaje; esta última se mide en la validación, no se garantiza con pruebas unitarias.

8. **Estructura de carpetas.**

   ```
   contrato/            biblioteca compartida del núcleo (interfaz, modelos, cargador, reglas de seguridad del señuelo)
   complementos/
     cwe78/             paquete propio; se registra por entry point
     cwe79/             (futuro) otra carpeta igual
   detector/  senuelo/  servicios del núcleo; dependen de contrato/, nunca de un complemento concreto
   ```

   `contrato/` es una carpeta nueva en la raíz. No es un contenedor del diagrama C4 sino una biblioteca que comparten dos contenedores; por eso no contradice la regla "una carpeta por contenedor" de ADR-000. Vive fuera de `complementos/` para que todo cambio al contrato cuente en la métrica de extensibilidad.

9. **Distribución reproducible.**
   - `contrato/` y cada `complementos/<cwe>/` son paquetes Python instalables, con sus archivos de datos declarados en `package-data` (lección de la issue #14).
   - Contrato, complementos y servicio se instalan en una sola invocación de `pip`, para que las dependencias se resuelvan en conjunto: un conflicto de versiones detiene la instalación en lugar de sobrescribir bibliotecas de otro paquete. Después se ejecuta `pip check`.
   - Instalación genérica: se instalan todas las carpetas de `complementos/`. Una carpeta sin `pyproject.toml` es un error que detiene la construcción; no se omite en silencio. Incorporar un complemento no exige editar Dockerfiles ni el CI.
   - El mismo procedimiento rige en desarrollo, en el CI y en Docker. El CI verifica la instalación conjunta, no solo cada paquete por separado.
   - `/salud` de cada servicio informa los complementos instalados (nombre y versión) y el activo.
   - Docker usa contextos de construcción adicionales (`additional_contexts` de Compose, BuildKit): cada servicio conserva su carpeta como contexto principal y su `.dockerignore`. `infra/README.md` documenta el equivalente sin Compose (`docker build --build-context ...`).

10. **Métrica de extensibilidad: dos indicadores.** ADR-000 no se modifica ni se reinterpreta. Al incorporar CWE-79 se reportan:
    - **indicador de ADR-000, sin cambios:** todas las líneas modificadas fuera de `complementos/`;
    - **indicador complementario:** esas mismas líneas desglosadas en código del núcleo (`contrato/`, `detector/`, `senuelo/`, `registro/`; meta: cero) y configuración de despliegue (`infra/`, por ejemplo la activación del complemento).

    Si activar CWE-79 exige cambiar configuración, el indicador de ADR-000 lo mostrará y el complementario explicará qué tipo de cambio fue.

## Alternativas descartadas

- **El complemento entrega solo un catálogo de datos para un motor común.** El motor actual es la gramática de un intérprete de comandos; CWE-79 obligaría a modificar el núcleo.
- **Una enumeración global de intenciones en el contrato.** Contradice la sección 7.5 del anteproyecto, que asigna el catálogo de intenciones a cada complemento.
- **Conservar `metacaracteres` y `segmentos` como campos de los modelos comunes.** Presuponen inyección de comandos; sin consumidores todavía, corregirlos ahora es más barato que mantenerlos como compatibilidad.
- **El contrato dentro de `complementos/`.** Sus cambios no contarían en la métrica y el resultado "cero cambios en el núcleo" no sería válido.
- **Copiar el contrato en cada servicio.** Duplicación que reintroduce el problema de las dos definiciones de `Intencion`.
- **Contexto de construcción en la raíz del repositorio.** Viable, pero obliga a reescribir todos los `COPY` y deja sin efecto el `.dockerignore` de cada servicio.
- **Construir un *wheel* previo y copiarlo a cada servicio.** Introduce un paso manual frágil.
- **Instalar los paquetes en invocaciones sucesivas de `pip`.** Cada invocación puede reemplazar versiones que otro paquete necesita sin detectar el conflicto.
- **Cargar por ruta de módulo con `importlib`.** Expone rutas internas al operador y no permite listar los complementos instalados.
- **Una lista explícita de complementos en el núcleo.** Cada complemento nuevo obligaría a editar el núcleo.
- **`contexto_senuelo` devuelve una sola cadena.** El núcleo no podría distinguir el contexto del complemento de la entrada del atacante, y el criterio de aceptación 5 sería incomprobable.

## Criterios de aceptación

1. El comportamiento que verifican hoy las 21 pruebas del detector y las 9 del señuelo se conserva: cada caso sigue probado. Las pruebas de la lógica de detección se trasladan a `complementos/cwe78/` y verifican lo mismo a través de `evidencia`; las de las API permanecen en cada servicio.
2. Un complemento ficticio con la forma de CWE-79, definido solo en las pruebas, funciona en el detector y en el señuelo a través del contrato, sin campos propios de inyección de comandos.
3. Una prueba automática verifica que ningún archivo de `detector/` ni de `senuelo/` importa un complemento concreto.
4. El cargador produce el error específico correspondiente ante un complemento inexistente, un nombre duplicado, una versión de contrato distinta y una implementación inválida; `listar()` no ejecuta código del complemento.
5. Las instrucciones que el señuelo envía al modelo contienen siempre las restricciones del núcleo, seguidas de `simulacion` y de `datos` delimitados como no confiables; una prueba con un complemento ficticio verifica que el contenido de `datos` nunca aparece fuera de los delimitadores.
6. Un servicio sin `UMBRA_COMPLEMENTO`, o con un nombre no instalado, no arranca y el error lista los complementos instalados.
7. Los invariantes de `Veredicto` se verifican con pruebas, una por invariante: un veredicto sin ataque con intención distinta de `desconocida`, con confianza distinta de cero o con `evidencia` no vacía es rechazado por el modelo; una `evidencia` fuera de límites es rechazada por el modelo; un veredicto cuyo `complemento` no es el activo, o cuya intención no pertenece al catálogo del complemento activo, es rechazado por el núcleo del detector. El señuelo responde `422` a una solicitud cuyo `complemento` no es el activo.
8. En el CI, la instalación conjunta pasa `pip check`; Compose construye ambas imágenes con los contextos adicionales; el detector detecta un ataque, el señuelo responde en `/salud` y ambos informan el complemento activo.
9. La instalación no editable de cada paquete incluye sus archivos de datos.

## Consecuencias

- Agregar CWE-79 se reduce a crear `complementos/cwe79/` y activarlo por configuración; los dos indicadores muestran el resultado sin ambigüedad.
- Los modelos de intercambio cambian una vez, antes de tener consumidores. El middleware (#9) y la integración (#15) se construyen sobre los modelos definitivos de v0.
- El repositorio pasa de paquetes independientes a paquetes con dependencias entre sí, instalados en conjunto.
- La construcción de imágenes requiere BuildKit y Docker Compose 2.17 o posterior.
- El contenido propio de CWE-78 lo redacta el equipo: el contexto de simulación se separa de las restricciones de seguridad actuales, y el catálogo de intenciones se completa en el sprint 2 con el protocolo del conjunto de datos.

## Procedimiento de aceptación

El ADR permanece en estado "propuesto" durante la revisión. Cuando ambos integrantes estén conformes, quien abrió el PR cambia el estado a "aceptado" en un commit explícito; el ruleset descarta las aprobaciones anteriores, de modo que la aprobación del otro integrante posterior a ese commit es la decisión conjunta y queda registrada en GitHub. Esa aprobación cubre únicamente las decisiones numeradas de este ADR; los puntos de la sección "Pendiente" siguen abiertos y se resuelven en un ADR posterior o en el protocolo de validación.

## Pendiente

- **Verificación:** versión de Docker Compose en la máquina de Santiago (≥ 2.17; la de Camila es v5.5.1) y primera construcción real en el CI.
- **Enrutamiento simultáneo** de varios complementos activos, a decidir antes del sprint de CWE-79. El diseño v0 no lo impide.
- **Bloqueo de versiones** (archivo de restricciones o de bloqueo) para todos los paquetes del repositorio. La resolución conjunta y `pip check` detectan conflictos, pero no fijan versiones entre construcciones.
- **Referencia Git de la métrica:** el protocolo de validación fija contra qué commit se calculan los dos indicadores al incorporar CWE-79.
- **Excepciones de un complemento durante la ejecución:** definir cómo responde y registra el núcleo un fallo de `analizar` o `contexto_senuelo` durante la integración (#15).

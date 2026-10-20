# complementos/cwe78/

Complemento **CWE-78** (inyección de comandos del sistema operativo). Primer caso de uso del framework Umbra: reglas de metacaracteres, catálogo de intenciones y plantillas de intérprete de comandos simulado.

## Responsabilidades

El complemento implementa la lógica específica de CWE-78 y se integra con el núcleo mediante el contrato definido en [ADR-002](../../docs/adr/ADR-002-contrato-complementos.md).

El motor y el catálogo se encuentran en `src/cwe78/`. El detector utiliza el contrato común para solicitar análisis y verificar los veredictos, sin importar directamente el motor de CWE-78.

## El catálogo de intenciones está vacío a propósito

Las listas de `palabras_clave` en `src/cwe78/catalogo.json` están **vacías deliberadamente**.

Según el plan de desarrollo, su contenido se definirá en el **sprint 2**, cuando el protocolo del conjunto de datos (`docs/dataset/protocolo.md`) establezca criterios de etiquetado por intención respaldados por fuentes verificables.

Mientras no existan esos criterios, el complemento puede identificar indicios de ataque mediante metacaracteres, pero mantiene la intención como `desconocida` cuando no dispone de evidencia suficiente.

Esta decisión evita presentar como validada una clasificación de intenciones que todavía no cuenta con respaldo metodológico.
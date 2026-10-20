# detector/

Contenedor **Detección e inferencia** (pasos 2 y 3 del flujo). Python.

Recibe la petición derivada por la aplicación objetivo, delega el análisis en el complemento activo y devuelve un veredicto validado conforme al contrato definido en [ADR-002](../docs/adr/ADR-002-contrato-complementos.md).

Cada complemento implementa sus propias reglas de detección y declara las intenciones que puede identificar. Para **CWE-78**, estas corresponden a reconocimiento, descarga de herramientas, persistencia, exfiltración y movimiento lateral.

**Sprint 1:** detección mediante reglas y criterios provisionales. **Sprint 5:** incorporación planificada de un clasificador scikit-learn, manteniendo el contrato de complementos.

Lidera: Camila. Revisa y prueba: Santiago.
# Contrato de complementos

Biblioteca compartida del núcleo de Umbra. Define la interfaz que implementa cada complemento, los modelos que cruzan la frontera núcleo–complemento, el cargador que los descubre y las restricciones de seguridad del señuelo. No es un contenedor del diagrama C4: es código que comparten `detector/` y `senuelo/`.

Decisión de arquitectura: [ADR-002](../docs/adr/ADR-002-contrato-complementos.md). Lideran: ambos integrantes (issue #13).

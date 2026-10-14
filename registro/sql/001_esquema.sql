-- Umbra · Registro forense · Esquema mínimo (sprint 1, issue #12).
-- Idempotente: se puede aplicar varias veces. El esquema definitivo, con
-- anonimización completa y política de retención (Ley 1581 de 2012), llega
-- en el sprint 8 como migración 002+.

CREATE TABLE IF NOT EXISTS sesiones (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    origen_hash     TEXT        NOT NULL,   -- hash del origen; nunca la IP en claro
    ruta            TEXT        NOT NULL,   -- ruta HTTP atacada
    parametro       TEXT        NOT NULL,   -- parámetro donde llegó la carga útil
    intencion_final TEXT,                   -- última intención inferida en la sesión
    inicio          TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),  -- instante real, no el de la transacción
    fin             TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS eventos (
    id          BIGSERIAL   PRIMARY KEY,
    sesion_id   UUID        NOT NULL REFERENCES sesiones(id) ON DELETE CASCADE,
    paso        SMALLINT    NOT NULL CHECK (paso BETWEEN 1 AND 8),  -- paso del flujo C4
    tipo        TEXT        NOT NULL,   -- p. ej. peticion_recibida, veredicto, respuesta_senuelo
    detalle     JSONB       NOT NULL DEFAULT '{}'::jsonb,
    creado_en   TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);

CREATE INDEX IF NOT EXISTS eventos_sesion_idx ON eventos (sesion_id, creado_en);
CREATE INDEX IF NOT EXISTS sesiones_inicio_idx ON sesiones (inicio DESC);

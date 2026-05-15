-- Migracion 005: tablas perceptions + perception_items
-- Comprobante de percepcion del IGV (tipo 40).
-- Solo agentes de percepcion designados por SUNAT pueden emitir esto.
-- Correr desde Supabase SQL Editor (o via scripts/bootstrap_db.py).

CREATE TABLE IF NOT EXISTS perceptions (
    id              SERIAL PRIMARY KEY,

    ruc_emisor      VARCHAR(11) NOT NULL,
    tipo_doc        VARCHAR(2) NOT NULL DEFAULT '40',
    serie           VARCHAR(4) NOT NULL,
    numero          INTEGER NOT NULL,
    fecha_emision   DATE NOT NULL,
    moneda          VARCHAR(3) NOT NULL DEFAULT 'PEN',

    receptor_tipo_doc       VARCHAR(1) NOT NULL,
    receptor_numero_doc     VARCHAR(15) NOT NULL,
    receptor_razon_social   VARCHAR(250) NOT NULL,

    -- Catalogo SUNAT 22: 01 combustible, 02 venta interna, 03 importacion.
    regimen         VARCHAR(2) NOT NULL,
    tasa            NUMERIC(5, 2) NOT NULL,

    total_percibido NUMERIC(14, 2) NOT NULL,
    total_cobrado   NUMERIC(14, 2) NOT NULL,
    nota            VARCHAR(500),

    status              VARCHAR(20) NOT NULL DEFAULT 'pending',
    sunat_code          VARCHAR(10),
    sunat_description   VARCHAR(500),
    xml_signed_url      VARCHAR(500),
    cdr_xml_url         VARCHAR(500),
    hash_signature      VARCHAR(100),
    error_message       VARCHAR(500),

    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT uq_perceptions_doc UNIQUE (ruc_emisor, serie, numero)
);

CREATE INDEX IF NOT EXISTS idx_perceptions_ruc_emisor ON perceptions (ruc_emisor);
CREATE INDEX IF NOT EXISTS idx_perceptions_status ON perceptions (status);


CREATE TABLE IF NOT EXISTS perception_items (
    id              SERIAL PRIMARY KEY,
    perception_id   INTEGER NOT NULL REFERENCES perceptions(id) ON DELETE CASCADE,

    -- SUNAT admite 01 factura, 03 boleta, 07 NC, 08 ND, 12 ticket.
    ref_tipo_doc        VARCHAR(2) NOT NULL,
    ref_serie           VARCHAR(4) NOT NULL,
    ref_numero          INTEGER NOT NULL,
    ref_fecha_emision   DATE NOT NULL,
    ref_moneda          VARCHAR(3) NOT NULL DEFAULT 'PEN',
    ref_total           NUMERIC(14, 2) NOT NULL,

    -- Cobro percibido (si hay pagos parciales, un item por pago).
    fecha_pago              DATE NOT NULL,
    correlativo_pago        INTEGER NOT NULL DEFAULT 1,
    importe_sin_percepcion  NUMERIC(14, 2) NOT NULL,
    importe_percepcion      NUMERIC(14, 2) NOT NULL,
    fecha_percepcion        DATE NOT NULL,
    importe_total_cobrado   NUMERIC(14, 2) NOT NULL,

    -- Solo si ref_moneda != PEN.
    tipo_cambio         NUMERIC(10, 4),
    tipo_cambio_fecha   DATE
);

CREATE INDEX IF NOT EXISTS idx_perception_items_perception_id ON perception_items (perception_id);

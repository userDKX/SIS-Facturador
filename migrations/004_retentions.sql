-- Migracion 004: tablas retentions + retention_items
-- Comprobante de retencion del IGV (tipo 20).
-- Solo agentes de retencion designados por SUNAT pueden emitir esto.
-- Correr desde Supabase SQL Editor (o via scripts/bootstrap_db.py).

CREATE TABLE IF NOT EXISTS retentions (
    id              SERIAL PRIMARY KEY,

    ruc_emisor      VARCHAR(11) NOT NULL,
    tipo_doc        VARCHAR(2) NOT NULL DEFAULT '20',
    serie           VARCHAR(4) NOT NULL,
    numero          INTEGER NOT NULL,
    fecha_emision   DATE NOT NULL,
    moneda          VARCHAR(3) NOT NULL DEFAULT 'PEN',

    receptor_tipo_doc       VARCHAR(1) NOT NULL,
    receptor_numero_doc     VARCHAR(15) NOT NULL,
    receptor_razon_social   VARCHAR(250) NOT NULL,

    -- Catalogo SUNAT 23 — siempre "01".
    regimen         VARCHAR(2) NOT NULL DEFAULT '01',
    -- Tasa aplicada: 3.00 vigente desde 2014, 6.00 historico.
    tasa            NUMERIC(5, 2) NOT NULL,

    total_retenido  NUMERIC(14, 2) NOT NULL,
    total_pagado    NUMERIC(14, 2) NOT NULL,
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

    CONSTRAINT uq_retentions_doc UNIQUE (ruc_emisor, serie, numero)
);

CREATE INDEX IF NOT EXISTS idx_retentions_ruc_emisor ON retentions (ruc_emisor);
CREATE INDEX IF NOT EXISTS idx_retentions_status ON retentions (status);


CREATE TABLE IF NOT EXISTS retention_items (
    id              SERIAL PRIMARY KEY,
    retention_id    INTEGER NOT NULL REFERENCES retentions(id) ON DELETE CASCADE,

    -- Factura referenciada (SUNAT solo admite "01" en retencion del IGV).
    ref_tipo_doc        VARCHAR(2) NOT NULL DEFAULT '01',
    ref_serie           VARCHAR(4) NOT NULL,
    ref_numero          INTEGER NOT NULL,
    ref_fecha_emision   DATE NOT NULL,
    ref_moneda          VARCHAR(3) NOT NULL DEFAULT 'PEN',
    ref_total           NUMERIC(14, 2) NOT NULL,

    -- Pago retenido (si la factura tiene pagos parciales, un item por pago).
    fecha_pago              DATE NOT NULL,
    correlativo_pago        INTEGER NOT NULL DEFAULT 1,
    importe_sin_retencion   NUMERIC(14, 2) NOT NULL,
    importe_retencion       NUMERIC(14, 2) NOT NULL,
    fecha_retencion         DATE NOT NULL,
    importe_neto_pagado     NUMERIC(14, 2) NOT NULL,

    -- Solo si ref_moneda != PEN.
    tipo_cambio         NUMERIC(10, 4),
    tipo_cambio_fecha   DATE
);

CREATE INDEX IF NOT EXISTS idx_retention_items_retention_id ON retention_items (retention_id);

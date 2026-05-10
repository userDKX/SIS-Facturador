-- Migracion 002: tabla credit_notes
-- Notas de credito (tipo 07) emitidas contra una factura o boleta.
-- Correr desde Supabase SQL Editor (o via scripts/bootstrap_db.py).

CREATE TABLE IF NOT EXISTS credit_notes (
    id              SERIAL PRIMARY KEY,
    invoice_id      INTEGER REFERENCES invoices(id) ON DELETE SET NULL,

    ruc_emisor      VARCHAR(11) NOT NULL,
    tipo_doc        VARCHAR(2) NOT NULL DEFAULT '07',
    serie           VARCHAR(4) NOT NULL,
    numero          INTEGER NOT NULL,
    fecha_emision   DATE NOT NULL,
    moneda          VARCHAR(3) NOT NULL DEFAULT 'PEN',

    motivo_codigo       VARCHAR(2) NOT NULL,
    motivo_descripcion  VARCHAR(250) NOT NULL,
    ref_tipo_doc        VARCHAR(2) NOT NULL,
    ref_serie           VARCHAR(4) NOT NULL,
    ref_numero          INTEGER NOT NULL,

    receptor_tipo_doc       VARCHAR(1) NOT NULL,
    receptor_numero_doc     VARCHAR(15) NOT NULL,
    receptor_razon_social   VARCHAR(250) NOT NULL,

    subtotal        NUMERIC(14, 2) NOT NULL DEFAULT 0,
    igv             NUMERIC(14, 2) NOT NULL DEFAULT 0,
    total           NUMERIC(14, 2) NOT NULL DEFAULT 0,

    status              VARCHAR(20) NOT NULL DEFAULT 'pending',
    sunat_code          VARCHAR(10),
    sunat_description   VARCHAR(500),
    xml_signed_url      VARCHAR(500),
    cdr_xml_url         VARCHAR(500),
    hash_signature      VARCHAR(100),
    error_message       VARCHAR(500),

    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT uq_credit_notes_doc UNIQUE (ruc_emisor, serie, numero)
);

CREATE INDEX IF NOT EXISTS idx_credit_notes_invoice_id ON credit_notes (invoice_id);
CREATE INDEX IF NOT EXISTS idx_credit_notes_ruc_emisor ON credit_notes (ruc_emisor);
CREATE INDEX IF NOT EXISTS idx_credit_notes_status ON credit_notes (status);

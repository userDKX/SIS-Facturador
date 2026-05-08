-- Migracion 001: tabla invoices
-- Correr desde Supabase SQL Editor

CREATE TABLE IF NOT EXISTS invoices (
    id              SERIAL PRIMARY KEY,
    ruc_emisor      VARCHAR(11) NOT NULL,
    tipo_doc        VARCHAR(2) NOT NULL DEFAULT '01',
    serie           VARCHAR(4) NOT NULL,
    numero          INTEGER NOT NULL,
    fecha_emision   DATE NOT NULL,
    moneda          VARCHAR(3) NOT NULL DEFAULT 'PEN',

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

    CONSTRAINT uq_invoice_serie_numero UNIQUE (ruc_emisor, tipo_doc, serie, numero)
);

CREATE INDEX IF NOT EXISTS idx_invoices_ruc_emisor ON invoices (ruc_emisor);
CREATE INDEX IF NOT EXISTS idx_invoices_status ON invoices (status);

-- Storage bucket setup (correr desde Supabase Storage UI):
-- 1. Crear bucket "comprobantes"
-- 2. Configurarlo como publico (mas simple para MVP) o privado (con signed URLs)
-- 3. Si publico: las URLs en xml_signed_url/cdr_xml_url son accesibles directamente

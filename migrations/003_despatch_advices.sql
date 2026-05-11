-- Migracion 003: tabla despatch_advices
-- Guias de remision remitente (tipo 09) emitidas via Nueva GRE REST.
-- Correr desde Supabase SQL Editor (o via scripts/bootstrap_db.py).

CREATE TABLE IF NOT EXISTS despatch_advices (
    id              SERIAL PRIMARY KEY,

    ruc_emisor      VARCHAR(11) NOT NULL,
    tipo_doc        VARCHAR(2) NOT NULL DEFAULT '09',
    serie           VARCHAR(4) NOT NULL,
    numero          INTEGER NOT NULL,
    fecha_emision   DATE NOT NULL,

    motivo_traslado     VARCHAR(2) NOT NULL,
    motivo_descripcion  VARCHAR(250) NOT NULL,
    modalidad           VARCHAR(2) NOT NULL,
    peso_bruto_total    NUMERIC(10, 2) NOT NULL,
    peso_bruto_unidad   VARCHAR(5) NOT NULL DEFAULT 'KGM',
    numero_bultos       INTEGER,

    destinatario_tipo_doc       VARCHAR(1) NOT NULL,
    destinatario_numero_doc     VARCHAR(15) NOT NULL,
    destinatario_razon_social   VARCHAR(250) NOT NULL,

    partida_ubigeo      VARCHAR(6) NOT NULL,
    partida_direccion   VARCHAR(500) NOT NULL,
    partida_cod_local   VARCHAR(4),
    llegada_ubigeo      VARCHAR(6) NOT NULL,
    llegada_direccion   VARCHAR(500) NOT NULL,
    llegada_cod_local   VARCHAR(4),

    transportista_ruc           VARCHAR(11),
    transportista_razon_social  VARCHAR(250),
    conductor_tipo_doc          VARCHAR(1),
    conductor_numero_doc        VARCHAR(15),
    conductor_licencia          VARCHAR(15),
    vehiculo_placa              VARCHAR(10),

    status              VARCHAR(20) NOT NULL DEFAULT 'pending',
    sunat_code          VARCHAR(10),
    sunat_description   VARCHAR(500),
    xml_signed_url      VARCHAR(500),
    cdr_xml_url         VARCHAR(500),
    hash_signature      VARCHAR(100),
    error_message       VARCHAR(500),

    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT uq_despatch_advices_doc UNIQUE (ruc_emisor, serie, numero)
);

CREATE INDEX IF NOT EXISTS idx_despatch_advices_ruc_emisor ON despatch_advices (ruc_emisor);
CREATE INDEX IF NOT EXISTS idx_despatch_advices_status ON despatch_advices (status);

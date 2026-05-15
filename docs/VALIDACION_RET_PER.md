# Validación de retención y percepción — 3 niveles

Playbook para validar la emisión de comprobantes de **retención (tipo 20)**
y **percepción (tipo 40)** antes de declararlos listos para producción.
Sigue la regla de los 3 niveles del proyecto: local → SUNAT beta → SUNAT
prod. No saltarse pasos.

## Nivel 1 — Local (build + sign + XSD client-side)

Verifica que el pipeline UBL completo arme un XML válido, firme bien y
pase el validador XSD client-side. No toca SUNAT.

### Pre

```powershell
# Postgres local con la DB del facturador y migraciones 004/005 aplicadas
psql -d sis_facturador -f migrations/004_retentions.sql
psql -d sis_facturador -f migrations/005_perceptions.sql

# .env apuntando a la BD local + cert beta (o de prueba)
# SUNAT_MODE=beta, SUNAT_RUC=20000000001, USER/PASS=MODDATOS/MODDATOS
```

Levantar `uvicorn` como ya lo hacés normalmente.

### Smoke offline (sin server, solo SDK)

Lo más rápido: build + sign + XSD validate sin tocar HTTP ni BD.

```python
from sunat_py import build_retention_xml, build_perception_xml
from sunat_py.xsd import validate_retention, validate_perception
from examples.emit_retention import retention_demo   # ver script
from examples.emit_perception import perception_demo

xml_ret = build_retention_xml(retention_demo())
validate_retention(xml_ret)   # raises XSDValidationError si rompe

xml_per = build_perception_xml(perception_demo())
validate_perception(xml_per)
```

### Curl contra el server local

`R001-1` retención sobre `F001-1` (PEN, 3% sobre 1180):

```bash
curl -X POST http://localhost:8000/v1/retentions \
  -H 'Content-Type: application/json' \
  -d '{
    "serie": "R001",
    "numero": 1,
    "fecha_emision": "2026-05-14",
    "regimen": "01",
    "tasa": "3.00",
    "total_retenido": "35.40",
    "total_pagado": "1144.60",
    "receptor": {
      "tipo_doc": "6",
      "numero_doc": "20100070970",
      "razon_social": "PROVEEDOR EJEMPLO SAC",
      "direccion": "AV PROVEEDOR 456 LIMA"
    },
    "items": [{
      "ref_tipo_doc": "01",
      "ref_serie": "F001",
      "ref_numero": 1,
      "ref_fecha_emision": "2026-05-01",
      "ref_moneda": "PEN",
      "ref_total": "1180.00",
      "fecha_pago": "2026-05-14",
      "correlativo_pago": 1,
      "importe_sin_retencion": "1180.00",
      "importe_retencion": "35.40",
      "fecha_retencion": "2026-05-14",
      "importe_neto_pagado": "1144.60"
    }]
  }'
```

`P001-1` percepción venta interna (2%) sobre `F001-2`:

```bash
curl -X POST http://localhost:8000/v1/perceptions \
  -H 'Content-Type: application/json' \
  -d '{
    "serie": "P001",
    "numero": 1,
    "fecha_emision": "2026-05-14",
    "regimen": "02",
    "tasa": "2.00",
    "total_percibido": "23.60",
    "total_cobrado": "1203.60",
    "receptor": {
      "tipo_doc": "6",
      "numero_doc": "20100070970",
      "razon_social": "CLIENTE EJEMPLO SAC",
      "direccion": "AV CLIENTE 456 LIMA"
    },
    "items": [{
      "ref_tipo_doc": "01",
      "ref_serie": "F001",
      "ref_numero": 2,
      "ref_fecha_emision": "2026-05-01",
      "ref_moneda": "PEN",
      "ref_total": "1180.00",
      "fecha_pago": "2026-05-14",
      "correlativo_pago": 1,
      "importe_sin_percepcion": "1180.00",
      "importe_percepcion": "23.60",
      "fecha_percepcion": "2026-05-14",
      "importe_total_cobrado": "1203.60"
    }]
  }'
```

### Qué buscar

- HTTP 200 con `status` poblado (sería `rejected` con `sunat_code=1071`
  si el RUC del cert no está en padrón — eso confirma que el pipeline
  build/sign/zip/sendBill funciona).
- `xml_signed_url` y `cdr_xml_url` no nulos (XML firmado y CDR
  persistidos en storage).
- En BD: `retentions` y `perceptions` con sus items, status reflejando
  la respuesta de SUNAT.
- 422 si rompés a propósito alguna suma (ej. `total_retenido` que no
  cuadre con la suma de items) — confirma que `validate_retention` /
  `validate_perception` corren antes de tocar SUNAT.

## Nivel 2 — SUNAT beta

Mismo payload, pero apuntando a `e-beta.sunat.gob.pe`. Confirma que el
ZIP llega, el endpoint acepta el formato y devuelve un CDR parseable.

### Pre

Override solo `MODE=beta` en el shell del proceso uvicorn (sin tocar
`.env`); mantené `SUNAT_RUC`, `SUNAT_USER`, `SUNAT_PASSWORD` y
`CERT_PFX_BASE64` reales. SUNAT beta acepta firmas con cert real y la
mayoría de credenciales SOL del contribuyente.

```powershell
$env:MODE='beta'; uvicorn sis_facturador.main:app --host 127.0.0.1 --port 8000
```

### Resultado 2026-05-14

Retención aceptada con `code=0`. Percepción llega al endpoint pero
SUNAT la rechaza con `2603` porque el RUC del cert no está inscrito
como agente — el roundtrip está OK, falta padrón.

## Nivel 3 — SUNAT prod

Aún no probado. Requiere RUC inscrito en el padrón de agentes de
retención o percepción (<http://www.sunat.gob.pe/padronesnotificaciones/>).
Con `MODE=prod` el flujo es el mismo del nivel 2, apuntando al
endpoint `e-factura.sunat.gob.pe`.

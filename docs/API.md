# Referencia HTTP

Endpoints del SIS Facturador. Esto es referencia copy-paste — los detalles
de cada campo viven en `sis_facturador/schemas/invoice.py` y se renderan automáticos
en `/docs` cuando levantas el server (`make run`).

Base URL: en local `http://localhost:8000`. En el deploy de Vercel,
`https://tu-deploy.vercel.app`.

## Health

### `GET /v1/health`

Liveness check. Devuelve `{"status": "ok"}` si el proceso está corriendo.
No verifica BD ni SUNAT.

```bash
curl http://localhost:8000/v1/health
```

```json
{"status": "ok"}
```

### `GET /v1/health/cert`

Carga el `.pfx` desde `CERT_PFX_BASE64`, extrae metadata del certificado
X.509 y reporta si está vigente. Útil después de un deploy para confirmar
que el cert quedó bien instalado.

```bash
curl http://localhost:8000/v1/health/cert
```

```json
{
  "common_name": "EJEMPLO PERSONA NATURAL",
  "serial": "4D72FD37A7EA01C1466C7B5083D297675CF7391E",
  "not_valid_before": "2026-05-05T07:30:00+00:00",
  "not_valid_after": "2029-05-04T07:30:00+00:00",
  "expired": false
}
```

Si devuelve 500: revisa `CERT_PFX_BASE64` (puede haberse pegado
truncado) y `CERT_PASSWORD` (puede no coincidir).

## Comprobantes

### `POST /v1/invoices`

Emite una Factura (`tipo_documento="01"`) o Boleta (`tipo_documento="03"`).

Hace todo el flujo end-to-end: arma el UBL, lo firma, lo empaqueta en ZIP,
lo manda a SUNAT, parsea el CDR, sube los XML al storage y persiste el
registro.

#### Body

```json
{
  "tipo_documento": "01",
  "serie": "F001",
  "numero": 123,
  "fecha_emision": "2026-05-08",
  "moneda": "PEN",
  "receptor": {
    "tipo_doc": "6",
    "numero_doc": "20512345678",
    "razon_social": "EMPRESA EJEMPLO S.A.C.",
    "direccion": "AV. JAVIER PRADO 1234, SAN ISIDRO, LIMA"
  },
  "lines": [
    {
      "codigo": "PROD001",
      "descripcion": "Servicio de consultoría",
      "unidad": "ZZ",
      "cantidad": "1.00",
      "precio_unitario": "100.00",
      "igv_afectacion": "10"
    }
  ]
}
```

#### Reglas que valida Pydantic antes de tocar SUNAT

- `tipo_documento` debe ser `"01"` (factura) o `"03"` (boleta).
- `serie` debe matchear el tipo: factura usa `F###`, boleta usa `B###`.
  Si no coincide, devuelve **422** con explicación.
- `numero` > 0.
- `receptor.tipo_doc`: catálogo SUNAT 06 (`"0"` sin doc, `"1"` DNI, `"4"`
  CE, `"6"` RUC, `"7"` pasaporte). Recuerda: factura solo acepta `"6"`.
- `lines` debe tener al menos uno.
- `cantidad` > 0, `precio_unitario` >= 0.

#### Códigos de respuesta

| HTTP  | Cuándo                                                              |
|-------|---------------------------------------------------------------------|
| `200` | El comprobante fue procesado por SUNAT (ver campo `status` para detalle: `accepted` / `accepted_with_obs` / `rejected`) |
| `409` | Ya existe un comprobante con la misma `(ruc, tipo, serie, numero)`. La idempotencia es por constraint UNIQUE en BD. |
| `422` | El payload no pasó validación Pydantic. Mensaje detallado con el campo problemático. |
| `502` | SUNAT no respondió correctamente (transport error, fault no parseable, credenciales mal). El detail trae el código y mensaje original. |
| `500` | Error inesperado del server. Revisa los logs.                       |

#### Respuesta exitosa (200)

```json
{
  "id": 42,
  "ruc_emisor": "20XXXXXXXXX",
  "tipo_doc": "01",
  "serie": "F001",
  "numero": 123,
  "fecha_emision": "2026-05-08",
  "moneda": "PEN",
  "subtotal": "100.00",
  "igv": "18.00",
  "total": "118.00",
  "status": "accepted",
  "sunat_code": "0",
  "sunat_description": "La Factura numero F001-123, ha sido aceptada",
  "xml_signed_url": "https://xxx.supabase.co/storage/v1/object/public/comprobantes/xml/20XXXXXXXXX-01-F001-123.xml",
  "cdr_xml_url": "https://xxx.supabase.co/storage/v1/object/public/comprobantes/cdr/R-20XXXXXXXXX-01-F001-123.xml",
  "error_message": null
}
```

#### Importante sobre el campo `status`

El HTTP 200 **no** garantiza que SUNAT aceptó el comprobante — solo que
el procesamiento llegó hasta el final sin errores de transporte. Hay que
mirar `status`:

- `"accepted"` (CDR `code=0`): aceptado, efecto tributario activo, está
  registrado en SUNAT.
- `"accepted_with_obs"` (CDR `code=098`): aceptado pero con observaciones
  (ej. INFO 4242). Igual tiene efecto tributario.
- `"rejected"`: SUNAT lo rechazó por reglas de negocio (`sunat_code` trae
  el código tipo `2800`, `3244`, etc.). El comprobante **no** está
  registrado en SUNAT.

### `GET /v1/invoices/{invoice_id}`

Devuelve un comprobante persistido. Es lookup local — no consulta a SUNAT.

```bash
curl http://localhost:8000/v1/invoices/42
```

Response: igual al body de respuesta del POST.

| HTTP  | Cuándo                                          |
|-------|-------------------------------------------------|
| `200` | Comprobante encontrado                          |
| `404` | No existe comprobante con ese `id`              |

## Notas de crédito

### `POST /v1/credit-notes`

Emite una nota de crédito (tipo 07) que modifica una factura o boleta
previa. Mismo flujo síncrono que `/v1/invoices`: arma el UBL `<CreditNote>`,
firma, sube al storage, manda a SUNAT, persiste el resultado.

#### Body

```json
{
  "serie": "FC01",
  "numero": 1,
  "fecha_emision": "2026-05-10",
  "moneda": "PEN",
  "motivo_codigo": "01",
  "motivo_descripcion": "ANULACION DE LA OPERACION",
  "referencia": {
    "tipo_doc": "01",
    "serie": "F001",
    "numero": 123
  },
  "receptor": {
    "tipo_doc": "6",
    "numero_doc": "20512345678",
    "razon_social": "EMPRESA EJEMPLO S.A.C.",
    "direccion": "AV. JAVIER PRADO 1234, SAN ISIDRO, LIMA"
  },
  "lines": [
    {
      "codigo": "PROD001",
      "descripcion": "Servicio de consultoría",
      "unidad": "ZZ",
      "cantidad": "1.00",
      "precio_unitario": "100.00",
      "igv_afectacion": "10"
    }
  ]
}
```

#### Reglas que valida Pydantic antes de tocar SUNAT

- `serie` con prefijo F (NC de factura) o B (NC de boleta), 4 caracteres.
- `referencia.tipo_doc`: `"01"` (factura) o `"03"` (boleta).
- La serie debe coincidir con el prefijo del comprobante referenciado:
  NC de factura usa `F###`, NC de boleta usa `B###`. Si no coincide,
  devuelve **422**.
- `motivo_codigo`: catálogo SUNAT 09 (ver tabla en `docs/SUNAT.md`).
- `motivo_descripcion`: texto libre (3-250 chars), SUNAT lo muestra en
  consultas.
- `lines` debe tener al menos uno (los items que la NC corrige/anula).

#### Códigos de respuesta

| HTTP  | Cuándo                                                              |
|-------|---------------------------------------------------------------------|
| `200` | Procesada por SUNAT (ver `status`: `accepted` / `accepted_with_obs` / `rejected`) |
| `409` | Ya existe una NC con la misma `(ruc, serie, numero)`                |
| `422` | Payload inválido (ej. serie no coincide con `referencia.tipo_doc`)  |
| `502` | SUNAT no respondió correctamente                                    |

#### Respuesta exitosa (200)

```json
{
  "id": 1,
  "invoice_id": 42,
  "ruc_emisor": "20XXXXXXXXX",
  "tipo_doc": "07",
  "serie": "FC01",
  "numero": 1,
  "fecha_emision": "2026-05-10",
  "moneda": "PEN",
  "motivo_codigo": "01",
  "motivo_descripcion": "ANULACION DE LA OPERACION",
  "ref_tipo_doc": "01",
  "ref_serie": "F001",
  "ref_numero": 123,
  "subtotal": "100.00",
  "igv": "18.00",
  "total": "118.00",
  "status": "accepted",
  "sunat_code": "0",
  "sunat_description": "La Nota de Credito numero FC01-1, ha sido aceptada",
  "xml_signed_url": "https://xxx.supabase.co/storage/v1/object/public/comprobantes/xml/20XXXXXXXXX-07-FC01-1.xml",
  "cdr_xml_url": "https://xxx.supabase.co/storage/v1/object/public/comprobantes/cdr/R-20XXXXXXXXX-07-FC01-1.xml",
  "error_message": null
}
```

`invoice_id` es `null` cuando el comprobante referenciado no existe en
la tabla `invoices` (ej. emitido por otro sistema antes de migrar). La NC
se emite igual — los campos `ref_*` son la fuente de verdad para SUNAT.

### `GET /v1/credit-notes/{credit_note_id}`

Devuelve una NC persistida. Lookup local, no consulta a SUNAT.

| HTTP  | Cuándo                              |
|-------|-------------------------------------|
| `200` | Nota de crédito encontrada          |
| `404` | No existe NC con ese `id`           |

## Una nota sobre auth

En el modo single-tenant actual, **el API no tiene autenticación**.
Cualquiera con la URL puede emitir comprobantes a tu nombre. Asume que la
URL solo la conoce el cliente del facturador (típicamente el backend del
SIS) y vive detrás de su propia auth.

Si vas a exponer públicamente, pon Cloudflare Access, una API key
intermedia, o algo equivalente delante. La autenticación nativa por API
key viene en el modo provider (ver `docs/DEPLOY_PROVIDER.md`).

## Para más

- OpenAPI completo: `GET /openapi.json`
- Swagger UI: `GET /docs`
- ReDoc: `GET /redoc`

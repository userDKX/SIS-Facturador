# Changelog

Cambios relevantes del **SIS Facturador**. Sigue el formato de
[Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/) y
[Semantic Versioning](https://semver.org/lang/es/).

## [Sin publicar]

## [0.1.0] - 2026-05-08

Primer release público. El pipeline ya emitió comprobantes reales en
producción contra `e-factura.sunat.gob.pe`, ambos con `code=0` y registrados
como "Procesado" en el portal SOL del contribuyente.

### Agregado

- API HTTP con `POST /v1/invoices` y `GET /v1/invoices/{id}`.
- Generación UBL 2.1 con plantilla Jinja2 (`app/ubl/builder.py`), incluyendo
  conversor de números a letras en español y cálculo de IGV al 18%.
- Firma XMLDSig RSA-SHA256 con Exclusive C14N (`app/signer/xmldsig.py`); el
  elemento `ds:Signature` se reubica dentro de
  `cac:UBLExtensions/cac:UBLExtension/cac:ExtensionContent` como exige SUNAT.
- Cliente SOAP `sendBill` sobre `zeep` (`app/sunat/client.py`), con WSDLs
  bundleados localmente para beta y prod (evita el rate-limit de SUNAT en
  `?ns1.wsdl`).
- `tipo_documento` parametrizable en `InvoiceInput` (default `"01"`); permite
  emitir tanto Factura (`01` / serie `F###`) como Boleta de venta
  (`03` / serie `B###`) con la misma plantilla UBL.
- Scripts de producción con flag `--confirm-real`:
  - `scripts/sendbill_prod.py` — emite una Factura real tipo 01.
  - `scripts/sendbill_prod_boleta.py` — emite una Boleta real tipo 03.
- Adaptadores de storage local y Supabase para persistir XML firmado y CDR.

### Verificado en producción (2026-05-08)

- Boleta `B001-1` — `accepted`, code 0, ticket SUNAT `202620668493873`.
- Factura `F001-1` — `accepted`, code 0, ticket SUNAT `202620668506859`.
- Ambos figuran como "Procesado" en el portal SOL del contribuyente.

### Gotchas documentados (ya resueltos en el código)

- Cache de SUNAT: cambios de permisos del usuario secundario tardan **24
  horas calendario** en propagarse. Antes de ese plazo, todo intento devuelve
  `0111`.
- Factura tipo `01` no acepta DNI como receptor (`schemeID=1`); devuelve
  `2800`. Solo RUC (`schemeID=6`). Boletas (`03`) sí aceptan DNI/CE/Pasaporte.
- `cac:PaymentTerms` es obligatorio después de `AccountingCustomerParty`
  (sin esto, `3244`).
- `AddressTypeCode` debe ser el código de establecimiento (típicamente
  `"0000"`), no el ubigeo (sino INFO `4242`).
- `zeep` auto-decodifica `xsd:base64Binary`; `sendBill()` devuelve bytes ZIP
  crudos (`PK..`), no string base64.
- `CDATA` + autoescape de Jinja2 produce double-encoding de entidades — la
  plantilla deja que Jinja maneje el escape.

[Sin publicar]: https://github.com/dukex57/sis-facturador/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/dukex57/sis-facturador/releases/tag/v0.1.0

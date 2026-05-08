# Changelog

All notable changes to **SIS Facturador** are documented here. Format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project adheres to
[Semantic Versioning](https://semver.org/).

## [Unreleased]

## [0.1.0] - 2026-05-08

First public release. The pipeline has been **validated end-to-end against SUNAT
production** with `code=0` CDRs registered as "Procesado" in the contributor's SOL
portal.

### Added

- FastAPI HTTP API with `POST /v1/invoices` and `GET /v1/invoices/{id}`.
- UBL 2.1 invoice generation via Jinja2 templates (`app/ubl/builder.py`) with
  Spanish numero-a-letras converter and IGV 18% computation.
- XMLDSig RSA-SHA256 signer with Exclusive C14N (`app/signer/xmldsig.py`); the
  `ds:Signature` element is relocated into `cac:UBLExtensions/cac:UBLExtension/cac:ExtensionContent`
  per SUNAT spec.
- SOAP `sendBill` client over zeep (`app/sunat/client.py`) with locally bundled
  WSDLs for beta and prod (avoids SUNAT rate-limit on `?ns1.wsdl`).
- Parameterizable `tipo_documento` on `InvoiceInput` (default `"01"`); enables
  emitting both **Factura** (`01` / serie `F###`) and **Boleta de Venta**
  (`03` / serie `B###`) from a single UBL template.
- Production scripts with `--confirm-real` guard:
  - `scripts/sendbill_prod.py` — emits a real Factura tipo 01.
  - `scripts/sendbill_prod_boleta.py` — emits a real Boleta tipo 03.
- Local-storage and Supabase-storage adapters for signed XML + CDR persistence.

### Verified in production (2026-05-08)

- **Boleta `B001-1`** — `Status accepted`, `Code 0`. SUNAT ticket `202620668493873`.
- **Factura `F001-1`** — `Status accepted`, `Code 0`. SUNAT ticket `202620668506859`.
- Both registered as **Procesado** in the SOL portal under
  *Empresas → Comprobantes de pago → SEE - Del Contribuyente y Envío de Documentos
  → Consultar Envíos de CPE*.

### Documented gotchas (resolved upstream)

- SUNAT cache delay: secondary-user permission changes propagate after **24
  calendar hours**. Premature attempts return `0111`.
- `Factura` tipo `01` rejects DNI receivers (`schemeID=1`) with code `2800`; only
  RUC (`schemeID=6`) is accepted. Boletas (`03`) accept DNI/CE/Passport.
- `cac:PaymentTerms` is mandatory after `AccountingCustomerParty` (else `3244`).
- `AddressTypeCode` must be the establecimiento code (e.g. `"0000"`), not the
  ubigeo (else INFO `4242`).
- zeep auto-decodes `xsd:base64Binary`; `sendBill()` returns raw ZIP bytes
  (`PK..`), not a base64 string.
- `CDATA` + Jinja2 autoescape produces double-encoded entities — the template
  relies on autoescape only.

[Unreleased]: https://github.com/dukex57/sis-facturador/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/dukex57/sis-facturador/releases/tag/v0.1.0

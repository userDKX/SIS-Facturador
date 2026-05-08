# pe-invoicing

SDK Python para emitir comprobantes electrónicos a SUNAT (Perú). Construye
UBL 2.1, firma con XMLDSig RSA-SHA256, manda por SOAP al webservice del
contribuyente y devuelve el CDR.

Sin opinión sobre HTTP ni persistencia: lo importas en tu código y decides
cómo usarlo.

## Instalación

```bash
pip install pe-invoicing
```

## Uso mínimo

```python
from pe_invoicing.security.cert_loader import load_cert
from pe_invoicing.signer.xmldsig import sign_invoice_xml
from pe_invoicing.sunat.client import send_bill
from pe_invoicing.sunat.packager import pack_invoice
from pe_invoicing.ubl.builder import build_invoice_xml
from pe_invoicing.ubl.models import InvoiceInput, InvoiceLine, Party

# Construir entrada
emisor = Party(tipo_doc="6", numero_doc="20XXXXXXXXX", razon_social="MI EMPRESA")
receptor = Party(tipo_doc="6", numero_doc="20YYYYYYYYY", razon_social="CLIENTE")
invoice = InvoiceInput(
    serie="F001", numero=1, fecha_emision=date.today(),
    moneda="PEN", emisor=emisor, receptor=receptor,
    lines=[InvoiceLine(codigo="SERV01", descripcion="Servicio", unidad="ZZ",
                       cantidad=Decimal("1"), precio_unitario=Decimal("100"))],
)

# Pipeline
cert = load_cert()                            # lee CERT_PFX_BASE64 + CERT_PASSWORD del env
xml = build_invoice_xml(invoice)              # UBL 2.1 sin firmar
signed = sign_invoice_xml(xml, cert)          # ds:Signature en cac:UBLExtensions
zip_bytes = pack_invoice(signed, "20XXXXXXXXX-01-F001-1")
result = send_bill(zip_bytes, "20XXXXXXXXX-01-F001-1.zip")

print(result.status, result.code, result.description)
# accepted 0 La Factura numero F001-1, ha sido aceptada
```

## Qué incluye

- `pe_invoicing.ubl` — generación UBL 2.1 con plantillas Jinja2 (factura,
  boleta) + dataclasses + cálculo de totales + monto en letras.
- `pe_invoicing.signer` — firma XMLDSig RSA-SHA256 con Exclusive C14N.
  Reubica `<ds:Signature>` dentro de `cac:UBLExtensions` como exige SUNAT.
- `pe_invoicing.sunat` — cliente SOAP `sendBill` sobre `zeep` con WSDLs
  bundleados localmente (evita rate-limit de SUNAT). Decodifica CDR.
- `pe_invoicing.security` — carga del cert `.pfx` desde base64 (env var).

## Qué NO incluye

- HTTP API (eso vive en el paquete `sis-facturador` del repo padre).
- Persistencia, BD, ORM.
- Multi-tenant resolution.
- Storage adapters.

Si necesitas todo eso, ver el repositorio del proyecto.

## Documentación

Detalle técnico vive en el [repositorio padre](https://github.com/userDKX/SIS-Facturador):

- [`docs/SIGNING.md`](https://github.com/userDKX/SIS-Facturador/blob/main/docs/SIGNING.md) — XMLDSig vs XAdES, gotchas
- [`docs/UBL.md`](https://github.com/userDKX/SIS-Facturador/blob/main/docs/UBL.md) — UBL 2.1 aplicado a SUNAT
- [`docs/SUNAT.md`](https://github.com/userDKX/SIS-Facturador/blob/main/docs/SUNAT.md) — protocolo SOAP, errores
- [`docs/SUNAT_SETUP.md`](https://github.com/userDKX/SIS-Facturador/blob/main/docs/SUNAT_SETUP.md) — onboarding del titular del RUC

## Licencia

MIT.

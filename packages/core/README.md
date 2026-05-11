# sunat-py

SDK Python para emitir comprobantes electrónicos a SUNAT. Builders
UBL 2.1, firma XMLDSig, clientes SOAP (factura/boleta/NC/ND, baja y
resumen) y REST (GRE remitente). Validaciones previas: RUC con DV
módulo 11, fechas en hora Lima, catálogos tipados.

El ecosistema SUNAT en open source vive en PHP (Greenter, Mifact,
q8factura, NubeFacT) y está bastante maduro. `sunat-py` es una opción
para los que trabajan en Python/FastAPI — todavía joven y con features
pendientes (retención, percepción, ICBPER, etc.), pero ya emite los
comprobantes principales contra producción.

**Comprobantes soportados y validados en producción (CDR code 0):**
factura (`01`), boleta (`03`), nota de crédito (`07`), nota de débito
(`08`), guía de remisión remitente (`09`, REST nueva), comunicación de
baja (`RA`), resumen diario de boletas (`RC`). Todos validados contra
`e-factura.sunat.gob.pe` / `api-cpe.sunat.gob.pe` el 2026-05-11.

**No soporta todavía:** retención (20), percepción (40), GRE
transportista (31), detracción, percepción ICBPER, ISC, anticipos,
descuentos globales. PRs bienvenidos.

Sin opinión sobre HTTP ni persistencia: lo importás en tu código y
decidís cómo usarlo. Para un servicio HTTP listo, ver el repo padre.

## Instalación

```bash
pip install sunat-py
```

## Uso mínimo

```python
from sunat_py import today_lima
from sunat_py.security.cert_loader import load_cert
from sunat_py.signer.xmldsig import sign_invoice_xml
from sunat_py.sunat.client import send_bill
from sunat_py.sunat.packager import pack_invoice
from sunat_py.ubl.builder import build_invoice_xml
from sunat_py.ubl.models import InvoiceInput, InvoiceLine, Party

# Construir entrada
emisor = Party(tipo_doc="6", numero_doc="20XXXXXXXXX", razon_social="MI EMPRESA")
receptor = Party(tipo_doc="6", numero_doc="20YYYYYYYYY", razon_social="CLIENTE")
invoice = InvoiceInput(
    serie="F001", numero=1, fecha_emision=today_lima(),
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

## Notas de crédito

Para anular o modificar una factura/boleta ya emitida, el SDK expone
`build_creditnote_xml` con su propia plantilla UBL `<CreditNote>`. La NC
referencia al comprobante original y declara el motivo del catálogo SUNAT
09. Se manda por el mismo `send_bill` síncrono.

```python
from sunat_py import (
    CreditNoteInput, ReferenciaDoc, InvoiceLine, Party,
    build_creditnote_xml, sign_invoice_xml, pack_invoice, send_bill,
)

nc = CreditNoteInput(
    serie="FC01", numero=1, fecha_emision=today_lima(), moneda="PEN",
    motivo_codigo="01",                                    # cat. 09: anulación
    motivo_descripcion="ANULACION DE LA OPERACION",
    referencia=ReferenciaDoc(tipo_doc="01", serie="F001", numero=1),
    emisor=emisor, receptor=receptor,
    lines=[InvoiceLine(codigo="SERV01", descripcion="Servicio",
                       unidad="ZZ", cantidad=Decimal("1"),
                       precio_unitario=Decimal("100"))],
)

xml = build_creditnote_xml(nc)
signed = sign_invoice_xml(xml, cert)
zip_bytes = pack_invoice(signed, f"{ruc}-07-FC01-1")
result = send_bill(client, zip_bytes, f"{ruc}-07-FC01-1.zip")
```

Motivos válidos del catálogo 09: `"01"` anulación, `"02"` anulación por
error de RUC, `"03"` corrección por error en descripción, `"04"` descuento
global, `"05"` descuento por ítem, `"06"` devolución total, `"07"`
devolución por ítem, `"08"` bonificación, `"09"` disminución del valor,
`"10"` otros, `"13"` ajuste de montos/fechas de pago.

La serie de la NC sigue el prefijo del documento referenciado: si la NC
modifica una factura (tipo `01`), la serie debe empezar con `F`; si
modifica una boleta (tipo `03`), con `B`. SUNAT no acepta cruzar prefijos.

Hay un script ejecutable en `examples/emit_creditnote.py` con el flujo
completo end-to-end usando solo este SDK.

**Validado en producción 2026-05-11:** NC `FC01-2` aceptada, code 0.

## Notas de débito

Para aumentar el monto de una factura/boleta emitida (intereses por mora,
penalidad, ajuste al alza), el SDK expone `build_debitnote_xml` con la
plantilla UBL `<DebitNote>`. La ND referencia al comprobante original y
declara el motivo del catálogo SUNAT 10. Se manda por el mismo
`send_bill` síncrono que NC y factura.

```python
from sunat_py import (
    DebitNoteInput, ReferenciaDoc, InvoiceLine, Party,
    build_debitnote_xml, sign_invoice_xml, pack_invoice, send_bill,
)

nd = DebitNoteInput(
    serie="FD01", numero=1, fecha_emision=today_lima(), moneda="PEN",
    motivo_codigo="01",                                    # cat. 10: intereses por mora
    motivo_descripcion="INTERES POR MORA",
    referencia=ReferenciaDoc(tipo_doc="01", serie="F001", numero=1),
    emisor=emisor, receptor=receptor,
    lines=[InvoiceLine(codigo="MORA01", descripcion="Interés por mora",
                       unidad="NIU", cantidad=Decimal("1"),
                       precio_unitario=Decimal("50.00"))],
)

xml = build_debitnote_xml(nd)
signed = sign_invoice_xml(xml, cert)
zip_bytes = pack_invoice(signed, f"{ruc}-08-FD01-1")
result = send_bill(client, zip_bytes, f"{ruc}-08-FD01-1.zip")
```

Motivos válidos del catálogo 10: `"01"` intereses por mora, `"02"`
aumento en el valor, `"03"` penalidades / otros conceptos.

La serie de la ND sigue el prefijo del documento referenciado: si la ND
modifica una factura (tipo `01`), la serie debe empezar con `F`; si
modifica una boleta (tipo `03`), con `B`. Igual que con NC, SUNAT no
acepta cruzar prefijos.

Hay un script ejecutable en `examples/emit_debitnote.py` con el flujo
completo end-to-end.

**Validado en producción 2026-05-11:** ND `FD01-1` aceptada, code 0.

## Comunicación de baja (RA) y resumen diario (RC)

A diferencia de factura/NC/ND (que se envían síncronos por `sendBill`), la
comunicación de baja y el resumen diario van por `sendSummary`, que es
**asíncrono**: SUNAT devuelve un ticket y procesa el documento en
segundos a minutos. Luego se consulta el CDR con `getStatus(ticket)`.

```python
from sunat_py import (
    VoidedDocumentsInput, VoidedItem, Party,
    build_voided_xml, sign_invoice_xml, pack_invoice,
    send_summary, get_status,
)

ra = VoidedDocumentsInput(
    correlativo=1,
    fecha_referencia=date(2026, 5, 8),   # fecha del CPE que se anula
    fecha_emision=today_lima(),
    emisor=emisor,
    items=[
        VoidedItem(tipo_doc="01", serie="F001", numero=5,
                   motivo="ERROR EN MONTO"),
    ],
)

xml = build_voided_xml(ra)               # ID interno: RA-20260508-1
signed = sign_invoice_xml(xml, cert)
zip_bytes = pack_invoice(signed, f"{ruc}-{ra.id_ra}")

ticket = send_summary(client, zip_bytes, f"{ruc}-{ra.id_ra}.zip")
result = get_status(client, ticket)      # poll hasta CDR
print(result.status, result.code, result.description)
```

El mismo patrón aplica a RC (resumen diario de boletas):

```python
from sunat_py import SummaryDocumentsInput, SummaryItem, build_summary_xml

rc = SummaryDocumentsInput(
    correlativo=1,
    fecha_referencia=today_lima(),
    fecha_emision=today_lima(),
    emisor=emisor,
    items=[
        SummaryItem(
            tipo_doc="03", serie="B001", numero=1,
            cliente_tipo_doc="1", cliente_numero_doc="12345678",
            moneda="PEN",
            total=Decimal("118.00"),
            base_gravada=Decimal("100.00"),
            igv=Decimal("18.00"),
            estado="1",                  # 1=adicionar, 2=modificar, 3=anular
        ),
    ],
)
```

**Reglas SUNAT que vale la pena saber**:

- Un RA solo agrupa CPE emitidos en la **misma fecha** (`fecha_referencia`).
  Si querés anular CPE de varios días, mandá un RA por día.
- SUNAT acepta el RA dentro de los **7 días** posteriores a la emisión
  del CPE original. Después de ese plazo, ya no se puede anular.
- El RC se envía como máximo el día siguiente a la fecha de las boletas
  (`fecha_referencia`). Tarde, SUNAT lo rechaza con error 1078.
- Los tickets de `sendSummary` pueden tardar varios minutos en procesarse.
  `get_status()` hace polling con `retries=10` cada `interval=3.0`s por
  defecto — extender ambos si necesitás esperar más.
- **El RA NO acepta boletas (tipo `03`) en `DocumentTypeCode`** — SUNAT
  rechaza con error 2308. Para anular una boleta, mandá un nuevo RC con
  el item de esa boleta y `estado="3"`.

Hay scripts ejecutables: `examples/emit_voided.py` (RA) y
`examples/emit_summary.py` (RC).

**Validado en producción 2026-05-11:** RC `RC-20260511-1` aceptado, code 0,
ticket `202620699620214`. RA `RA-20260511-1` aceptada, code 0, ticket
`202620699633180`.

## Guía de remisión remitente (tipo 09)

A diferencia de las CPE, SUNAT migró las GR a una **REST nueva**
(`api-cpe.sunat.gob.pe`) con OAuth2 password. El SDK provee
`build_despatchadvice_xml` para el UBL `<DespatchAdvice>` (sin valores
monetarios) y `get_gre_token` + `send_gre` como cliente REST.

```python
from datetime import date
from decimal import Decimal
from sunat_py import (
    Conductor, DespatchAdviceInput, DireccionTraslado, GRLine, Party, Vehiculo,
    build_despatchadvice_xml, sign_invoice_xml, pack_invoice,
    get_gre_token, send_gre, load_cert_from_base64,
)

cert = load_cert_from_base64(cert_b64, cert_password)

gr = DespatchAdviceInput(
    serie="T001", numero=1, fecha_emision=today_lima(),
    motivo_traslado="01",                     # cat. 20: 01 venta, 04 entre establec., ...
    motivo_descripcion="VENTA",
    modalidad="02",                           # cat. 18: 01 público, 02 privado
    peso_bruto_total=Decimal("10.00"), peso_bruto_unidad="KGM",
    emisor=Party(tipo_doc="6", numero_doc=ruc, razon_social="MI EMPRESA SAC"),
    destinatario=Party(tipo_doc="6", numero_doc="20512345678",
                       razon_social="CLIENTE SAC", direccion="AV LIMA 456"),
    partida=DireccionTraslado(ubigeo="150101", direccion="AV PRINCIPAL 123",
                              cod_local="0000"),    # 0000=casa matriz, 0001+=anexos
    llegada=DireccionTraslado(ubigeo="150122", direccion="AV LIMA 456"),
    lines=[GRLine(codigo="P001", descripcion="Producto",
                  unidad="NIU", cantidad=Decimal("5"))],
    conductor=Conductor(tipo_doc="1", numero_doc="12345678",
                        nombres="JUAN", apellidos="PEREZ",
                        licencia="Q12345678"),     # numero de licencia vigente
    vehiculo=Vehiculo(placa="ABC123"),
    numero_bultos=2,
)

xml = build_despatchadvice_xml(gr)
signed = sign_invoice_xml(xml, cert)
zip_bytes = pack_invoice(signed, f"{ruc}-09-T001-1")

token = get_gre_token(client_id=gre_client_id, client_secret=gre_client_secret,
                      ruc=ruc, username=sol_user, password=sol_password)
result = send_gre(token=token, ruc=ruc, zip_bytes=zip_bytes,
                  filename_base=f"{ruc}-09-T001-1")

print(result.status, result.code, result.description)
# accepted 0 Aceptado
```

**Credenciales API GRE**: el `client_id`/`client_secret` se generan en SOL
> *Empresas > Comprobantes de Pago > SEE > Credenciales API SUNAT*. Son
independientes del usuario SOL del SEE-DSC.

**Reglas SUNAT que vale la pena saber**:

- `cod_local` (catálogo SUNAT establecimientos anexos) es obligatorio para
  el punto de partida cuando el motivo es `04` (traslado entre
  establecimientos). Usa `"0000"` para casa matriz.
- El DNI del conductor se valida contra RENIEC en tiempo real. Si no
  existe, SUNAT rechaza con error `3359`.
- Las placas no aceptan guion: `ABC123` ✓, `ABC-001` ✗ (error `2567`).
- La licencia de conducir es obligatoria para modalidad `02` (privada)
  — error `2572` si falta.
- Fecha de emisión: la valida contra el reloj de Lima (UTC-5). Si tu
  máquina está en otra TZ (servidor en UTC, contenedor con `TZ` rara),
  usa `from sunat_py import today_lima` en vez de `date.today()` para
  no caer en error `2329`.

## Qué incluye

- `sunat_py.ubl` — generación UBL 2.1 con plantillas Jinja2 (factura,
  boleta, nota de crédito, nota de débito, guía de remisión) + dataclasses
  + cálculo de totales + monto en letras.
- `sunat_py.validators` — validación previa al envío (RUC con dígito
  verificador módulo 11, tipo de documento de identidad según catálogo 06,
  fecha de emisión contra reloj de Lima, líneas y catálogo de afectación
  IGV). Falla rápido con `ValidationError` claro antes de armar el XML.
- `sunat_py.signer` — firma XMLDSig RSA-SHA256 con Exclusive C14N.
  Reubica `<ds:Signature>` dentro de `cac:UBLExtensions` como exige SUNAT.
- `sunat_py.sunat.client` — cliente SOAP `sendBill` sobre `zeep` con
  WSDLs bundleados localmente. Para factura/boleta/NC.
- `sunat_py.sunat.gre_client` — cliente REST OAuth2 para la Nueva GRE
  (api-cpe.sunat.gob.pe). Envío + polling de CDR.
- `sunat_py.security` — carga del cert `.pfx` desde base64 (env var).

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

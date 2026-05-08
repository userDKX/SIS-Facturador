# UBL 2.1 aplicado a SUNAT

UBL (Universal Business Language) es un estándar grande de OASIS para
documentos de negocio. SUNAT usa el subset UBL 2.1 con sus propias
restricciones y extensiones. Este doc cubre los detalles que SUNAT valida
con dureza — los que si los pifeas, te tira un código de error.

La plantilla está en `app/ubl/templates/invoice_01.xml.j2`. Una sola para
factura (`01`) y boleta (`03`); el `tipo_documento` se interpola en el
`InvoiceTypeCode`.

## Namespaces obligatorios

Todo `<Invoice>` arranca con estos namespaces:

```xml
<Invoice xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2"
         xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2"
         xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
         xmlns:ext="urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2"
         xmlns:ds="http://www.w3.org/2000/09/xmldsig#">
```

Sin `ds:`, la firma no encaja. Sin `ext:`, no puedes meter
`<UBLExtensions>` que es donde va el `<ds:Signature>`.

## Atributos obligatorios en elementos clave

Estos son los que más causan rechazo silencioso porque la validación de
SUNAT no siempre dice "te falta el atributo X", solo te tira un código
genérico.

### `DocumentCurrencyCode`

```xml
<cbc:DocumentCurrencyCode listID="ISO 4217 Alpha"
                          listName="Currency"
                          listAgencyName="United Nations Economic Commission for Europe">PEN</cbc:DocumentCurrencyCode>
```

Sin esos tres atributos (`listID`, `listName`, `listAgencyName`) algunos
validadores XSD de SUNAT lo aceptan, otros no. Mejor ponerlos siempre.

### `InvoiceTypeCode`

```xml
<cbc:InvoiceTypeCode listAgencyName="PE:SUNAT"
                     listName="Tipo de Documento"
                     listURI="urn:pe:gob:sunat:cpe:see:gem:catalogos:catalogo01"
                     listID="0101"
                     listSchemeURI="urn:pe:gob:sunat:cpe:see:gem:catalogos:catalogo51"
                     name="Tipo de Operacion">01</cbc:InvoiceTypeCode>
```

El `listID="0101"` viene del Catálogo 51 de SUNAT — es el código de
operación (en este caso "venta interna"). Si manejas otros tipos
(exportación, ICBPER, gratuita), el listID cambia y hay que ajustar la
plantilla.

El valor del elemento (`01` o `03`) es el Catálogo 01 de SUNAT (tipo de
documento).

### `Note` con monto en letras

```xml
<cbc:Note languageLocaleID="1000">SON CIENTO DIECIOCHO CON 00/100 SOLES</cbc:Note>
```

El `languageLocaleID="1000"` corresponde al Catálogo 7 código `1000`
("monto en letras"). Es **obligatorio** desde 2019 en facturas y boletas.
Sin esto, código `2624` o similar.

El builder calcula el monto en letras con `monto_en_letras()` en
`app/ubl/builder.py` — convierte un Decimal a su representación en español
peruano ("SON ... CON XX/100 SOLES").

### `AddressTypeCode` — el infame INFO 4242

```xml
<cac:RegistrationAddress>
  <cbc:AddressTypeCode>0000</cbc:AddressTypeCode>
  ...
</cac:RegistrationAddress>
```

`AddressTypeCode` **no es el ubigeo**. Es el código del establecimiento
anexo registrado en SOL. Si tienes un solo local, ese código es `"0000"`
(sede principal). Si tienes locales adicionales, cada uno tiene su código
de 4 dígitos asignado por SUNAT.

Si pones acá el ubigeo (ej. `"150101"` para Lima), te sale observación
INFO `4242`. No bloquea el envío en beta pero conviene corregirlo: en prod
es bloqueante en algunos casos.

## Receptor: factura vs boleta

La diferencia operativa más relevante entre los dos comprobantes en sendBill:

### Factura tipo `01`

```xml
<cac:AccountingCustomerParty>
  <cac:Party>
    <cac:PartyIdentification>
      <cbc:ID schemeID="6">20512345678</cbc:ID>
    </cac:PartyIdentification>
    ...
  </cac:Party>
</cac:AccountingCustomerParty>
```

Solo acepta **RUC** (`schemeID="6"`). Si mandas DNI, te rechaza con `2800`.

### Boleta tipo `03`

```xml
<cac:AccountingCustomerParty>
  <cac:Party>
    <cac:PartyIdentification>
      <cbc:ID schemeID="1">12345678</cbc:ID>
    </cac:PartyIdentification>
    ...
  </cac:Party>
</cac:AccountingCustomerParty>
```

Acepta:

- `schemeID="1"` — DNI
- `schemeID="4"` — Carnet de extranjería
- `schemeID="6"` — RUC (sí, también)
- `schemeID="7"` — Pasaporte
- `schemeID="0"` — Sin documento (consumidor final, válido para boletas
  hasta cierto monto)

## `cac:PaymentTerms` — el causante del 3244

Este elemento es obligatorio desde 2019, y la plantilla lo pone justo
después de `AccountingCustomerParty`:

```xml
<cac:PaymentTerms>
  <cbc:ID>FormaPago</cbc:ID>
  <cbc:PaymentMeansID>Contado</cbc:PaymentMeansID>
</cac:PaymentTerms>
```

Si no está, te tira:

```
3244 - El dato ingresado en el tipo de transaccion del comprobante no es válido
```

El mensaje es engañoso — uno asume que es algo del `InvoiceTypeCode`, pero
el problema real es `PaymentTerms` faltante. Si lo necesitas con crédito,
agregas más nodos para las cuotas (`Cuota001`, `Cuota002`...).

## Catálogo 7 — afectación de IGV

En cada `InvoiceLine` hay un `<cac:TaxCategory>` que indica la afectación
del IGV. Códigos del Catálogo 7 que el builder maneja:

| Código | Significado            | tax_scheme_id | tax_scheme_name | tax_scheme_type |
|--------|------------------------|---------------|-----------------|-----------------|
| `10`   | Gravado - operación onerosa | `1000`   | `IGV`           | `VAT`           |
| `20`   | Exonerado              | `9997`        | `EXO`           | `VAT`           |
| `30`   | Inafecto               | `9998`        | `INA`           | `FRE`           |

Si manejas operaciones con bonificaciones, retiros, exportación, etc. hay
más códigos en el catálogo. La función `_enrich_line()` en `builder.py` es
donde se mapean — agregar nuevos casos ahí.

## Profile ID del catálogo 51

```xml
<cbc:ProfileID schemeName="Tipo de Operacion"
               schemeAgencyName="PE:SUNAT"
               schemeURI="urn:pe:gob:sunat:cpe:see:gem:catalogos:catalogo51">0101</cbc:ProfileID>
```

`0101` es "venta interna". Otros valores (catálogo 51 completo): `0200`
exportación, `0401` ventas no domiciliadas, etc. Para la mayoría de casos
de un comercio normal, `0101`.

## El elemento `cac:Signature` (no es la firma)

Confusión típica: hay dos cosas que se llaman "Signature" en el UBL:

- `<cac:Signature>` — metadata del firmante (quién firma, qué cert usa).
  Esto es parte del UBL, no es la firma criptográfica.
- `<ds:Signature>` — la firma XMLDSig real, dentro de
  `cac:UBLExtensions/.../ExtensionContent`.

El primero apunta al segundo via el atributo `URI` en
`<cbc:URI>#SignatureSP</cbc:URI>`, que matchea el
`Id="SignatureSP"` que el signer asigna al `<ds:Signature>` real.

## El builder, la decisión clave

`app/ubl/builder.py` tiene una sola función pública: `build_invoice_xml(inv:
InvoiceInput) -> str`. Toda la lógica vive ahí. Decisiones explícitas:

- **`Decimal` para todos los montos.** No `float`. SUNAT redondea con
  `ROUND_HALF_UP` a 2 decimales — el builder usa `quantize(TWO_DP,
  rounding=ROUND_HALF_UP)`.
- **Pre-cálculo en Python, no en Jinja.** `_enrich_line()` calcula todos
  los campos derivados (subtotal, IGV, precio con IGV, percent, scheme id)
  para cada línea antes de pasar al template. Esto mantiene el template
  como visualización pura.
- **Validación XML al final.** `etree.fromstring(rendered.encode("utf-8"))`
  parsea lo renderizado para detectar XML malformado antes de enviarlo al
  signer.

## Para ver más

- Catálogos de SUNAT: https://cpe.sunat.gob.pe/sites/default/files/inline-files/anexoVIII.pdf
- Plantilla del builder: `app/ubl/templates/invoice_01.xml.j2`
- Validador online de SUNAT (útil para depurar): https://e-factura.sunat.gob.pe/cl-ti-itcpfegem-beta/billService

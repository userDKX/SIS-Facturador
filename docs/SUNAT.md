# SUNAT: protocolo, errores, marco normativo

Doc de referencia para entender qué pasa entre que armas el ZIP y SUNAT te
devuelve un veredicto. Cubre el WS, los códigos de error más frecuentes, y
el marco normativo 2024-2026 que afecta al onboarding de clientes nuevos.

## El protocolo: SOAP con WS-Security

SUNAT expone su Webservice de Documentos Electrónicos (SEE-DSC) sobre SOAP
1.1. La operación principal es `sendBill` (síncrona); para baja de
comprobantes y resumen diario de boletas existe `sendSummary` (asíncrona,
devuelve un ticket que se consulta después con `getStatus`).

WS-Security con `UsernameToken`:

- `Username` = `{RUC}{usuario_secundario}` concatenado, por ejemplo
  `20495184120FACSIS11`. (El código arma esto solo en
  `settings.sunat_username` — tú pones `SUNAT_USER=FACSIS11` en `.env` y se
  prefija el RUC.)
- `Password` = clave del secundario, en plaintext (en el SOAP, sobre TLS).

`zeep` maneja esto con `from zeep.wsse.username import UsernameToken`.

## sendBill, en seis líneas

```python
client = Client(wsdl="...", wsse=UsernameToken(user, pwd))
response_b64 = client.service.sendBill(
    fileName="20495184120-01-F001-1.zip",
    contentFile=zip_bytes,           # bytes crudos del ZIP
)
# response_b64 son bytes ZIP del CDR (zeep ya decodifica xsd:base64Binary)
```

Variantes del resultado:

- Si SUNAT acepta o acepta-con-observaciones: devuelve un
  `applicationResponse` (otro UBL XML, con `ResponseCode=0` o `=098`)
  empaquetado en un ZIP y devuelto como `xsd:base64Binary`.
- Si SUNAT rechaza por reglas de negocio: lanza un `soap:Fault` con un
  código numérico de SUNAT en el faultcode.
- Si hay error de transporte / autenticación / fault no parseable: lanza un
  `soap:Fault` también pero con un código no numérico (ej. `0102`).

El cliente en `app/sunat/client.py` distingue los tres casos.

## El detalle raro: zeep ya decodifica el base64

El campo `contentFile` y `applicationResponse` están declarados como
`xsd:base64Binary` en el WSDL. `zeep` los maneja transparente: cuando le
pasas `bytes` los codifica a base64 para el envío, y cuando recibe la
respuesta te devuelve `bytes` ya decodificados (con el magic `PK..` del
ZIP).

Caímos al inicio en intentar decodificar otra vez la respuesta como base64
y eso fallaba con `binascii.Error: Incorrect padding`. La función
`unpack_cdr()` en `app/sunat/packager.py` detecta el magic `PK` y omite el
decode si los bytes ya son ZIP crudos:

```python
def unpack_cdr(b64_zip):
    if isinstance(b64_zip, bytes) and b64_zip[:2] == b"PK":
        zip_bytes = b64_zip
    else:
        zip_bytes = base64.b64decode(b64_zip)
    ...
```

## Los WSDL están bundleados localmente

`app/sunat/wsdl/{beta,prod}/` tiene los WSDLs descargados una sola vez.
SUNAT publica el WSDL en `https://...billService?wsdl`, que importa otro:
`?ns1.wsdl`. Ese segundo endpoint **rate-limita**: la primera petición
responde 200, las siguientes 401. `zeep` durante init hace varias
peticiones al WSDL completo, por lo que después del primer cliente fallan
todos los siguientes.

La solución estándar (la usa Greenter, la usa cualquier proyecto serio): se
descarga el WSDL una vez, se descargan los archivos referenciados
(`?ns1.wsdl`, `?xsd2.xsd`), se patchean las refs internas para apuntar a
los archivos locales (`billService_ns1.wsdl`, `billService_xsd2.xsd`), y se
guarda todo en disco. `client.py` carga desde local según `settings.MODE`.

## Endpoints de SUNAT (al 2026-05)

### Beta (homologación, sin efecto tributario)

```
https://e-beta.sunat.gob.pe/ol-ti-itcpfegem-beta/billService?wsdl
```

Cualquier comprobante mandado acá es de prueba — no se factura nada
realmente. Las credenciales públicas MODDATOS funcionan acá (RUC
`20000000001`, usuario `MODDATOS`, clave `MODDATOS`, cert `.pfx` de prueba).

### Producción

Endpoint principal:

```
https://e-factura.sunat.gob.pe/ol-ti-itcpfegem/billService?wsdl
```

Failover (mismo backend, distinto host — útil cuando el principal cae
intermitentemente, lo cual pasa de vez en cuando):

```
https://www.sunat.gob.pe/ol-ti-itcpfegem/billService?wsdl
https://ww1.sunat.gob.pe/ol-ti-itcpfegem/billService?wsdl
```

Los tres están expuestos por SUNAT y devuelven la misma respuesta. El
namespace de las operaciones es:

```
http://service.gem.factura.comppago.registro.servicio.sunat.gob.pe/
```

## Los códigos de error que más vas a ver

El catálogo completo está en el manual del programador del SEE. Esta tabla
es solo lo más frecuente y lo aprendido en producción real:

### Auth y configuración del lado de SUNAT

| Código | Causa                                                      | Acción                                                                                    |
|--------|------------------------------------------------------------|-------------------------------------------------------------------------------------------|
| `0102` | Credenciales SOL inválidas                                 | Revisa `SUNAT_USER` (sin RUC adelante) y `SUNAT_PASSWORD`                                 |
| `0111` | El secundario no tiene perfil para emitir vía WS           | (a) Espera 24h post-Grabar permisos; (b) revisa el árbol de permisos en SOL completo; (c) crea secundario nuevo |
| `0150` | El RUC del emisor no coincide con el del cert              | Revisa que el cert registrado en SOL sea el mismo que tienes en `CERT_PFX_BASE64`         |
| `0156` | El cert no está vigente                                    | Renueva el cert con tu CA y vuelve a registrar en SOL                                     |

### Validación del UBL

| Código | Causa                                                      | Acción                                                                                    |
|--------|------------------------------------------------------------|-------------------------------------------------------------------------------------------|
| `2624` | Falta `Note` con monto en letras                           | Ya cubierto por el builder; si lo ves es porque modificaste la plantilla                  |
| `2800` | Tipo de documento de identidad del receptor no permitido   | Factura `01` solo acepta RUC. Boleta `03` acepta DNI/CE/Pasaporte                         |
| `3244` | Tipo de transacción del comprobante no válido (mensaje engañoso) | Falta `cac:PaymentTerms` después de `AccountingCustomerParty`                       |
| `3203` | El monto total no concuerda con la suma de líneas + IGV    | Bug en cálculo; revisa quantize y rounding en `compute_totals()`                          |
| `0306` | El nombre del archivo ZIP no coincide con el contenido     | El ZIP debe llamarse `{RUC}-{tipo}-{serie}-{numero}.zip` y contener `{mismo_nombre}.xml`  |

### Observaciones (no bloquean en beta, pueden bloquear en prod)

| Código     | Causa                                                                   | Acción                                              |
|------------|-------------------------------------------------------------------------|-----------------------------------------------------|
| `INFO 4242`| `AddressTypeCode` con ubigeo en lugar de código de establecimiento      | Usa `"0000"` para sede principal                    |
| `INFO 2336`| Email del receptor inválido o vacío                                     | Si pones email del receptor, valida formato         |

El código 098 es especial: significa "ACEPTADO con observaciones". El CDR
vendrá con `<ResponseCode>098</ResponseCode>` y la observación detallada
adentro. El comprobante igual queda emitido con efecto tributario.

## SEE-SOL vs SEE-DSC

Es la confusión número uno cuando uno se mete a leer la doc de SUNAT.

- **SEE-SOL** (Sistema de Emisión Electrónica - SOL) = emites entrando al
  portal SOL y llenando un formulario web. SUNAT te genera el comprobante
  desde su lado. Es para gente que no tiene sistema propio.
- **SEE-DSC** (Sistema de Emisión Electrónica - Del Contribuyente) =
  emites desde tu propio sistema, lo firmas con tu cert, lo mandas por WS.
  Es lo que usa este facturador.

Los permisos del usuario secundario son diferentes para uno y otro:

```
SEE - SOL                                     ← solo para emisión web
└─ Factura Electrónica
   ├─ Emitir Factura
   ├─ Emitir Boleta
   └─ ...

SEE - Del Contribuyente y Envío de Documentos ← lo que necesitas para WS
├─ Servicio de Envío de Documentos Electrónicos
│  └─ Servicio de Envío de Documentos Electrónicos por Servicio Web
├─ Certificado Digital
└─ Consultar Envíos de CPE
```

Tener marcado SEE-SOL no habilita el WS, y al revés tampoco. Si solo tienes
SEE-SOL, vas a llegar al `0111` aunque "veas que tiene permisos de Factura
Electrónica".

## Marco normativo a tener en mente

Estos son los cambios regulatorios recientes que afectan al onboarding de
clientes nuevos:

### RS 075-2026/SUNAT (vigente 2026-06-01)

Contribuyentes nuevos quedan **emisores electrónicos automáticos desde la
inscripción del RUC**. No hay que pedirles afiliación al SEE-DSC, ya vienen
afiliados. Para clientes ya inscritos antes, no cambia nada.

Implicancia para el SIS Facturador: el flujo de
[`SUNAT_SETUP.md`](./SUNAT_SETUP.md) puede saltar el Paso 1 para clientes
post-2026-06-01.

### RS 062-2026/SUNAT (proyecto público)

Cambios adicionales a designación de emisores. Watching, no aprobado al
momento de escribir.

### RS 240-2024 + RS 133-2025

Solo aplican a Guía de Remisión Electrónica. Es otro WSDL, otro flujo,
fuera del alcance del SIS Facturador en su release actual.

### SIRE obligatorio en paralelo

El Sistema Integrado de Registros Electrónicos (SIRE) reemplaza los
registros físicos de ventas y compras. Lo lleva el contribuyente o su
contador, no este facturador, pero conviene mencionarlo a clientes para
que estén al tanto.

## Catálogos vigentes

Los catálogos de SUNAT (versiones que están en uso al 2026-05):

- **Catálogo 1**: tipos de documento (`01` factura, `03` boleta, `07` NC, `08` ND)
- **Catálogo 6**: tipos de documento de identidad (`1` DNI, `4` CE, `6` RUC, `7` pasaporte, `0` sin doc)
- **Catálogo 7**: afectación del IGV (`10`, `20`, `30`, …)
- **Catálogo 51**: tipo de operación (`0101` venta interna, …)
- **Catálogo 52**: motivos de Nota de Crédito (`01` anulación, `02` corrección, …)

URL del anexo VIII (donde están todos):
https://cpe.sunat.gob.pe/sites/default/files/inline-files/anexoVIII.pdf

## Diagnóstico cuando algo se rompe

Cuando el envío falla, el orden lógico para diagnosticar:

1. **Cargó el cert?** Corre `make verify-cert`. Si falla, el problema es
   `CERT_PFX_BASE64` o `CERT_PASSWORD`.
2. **El cliente SOAP construye?** Mira los logs — si `_get_client()`
   revienta, el WSDL local no está o `MODE` está mal.
3. **El sendBill autenticó?** Si te tira `0102`, son las credenciales SOL.
4. **El sendBill llegó al validador de UBL?** Si te tira un código `2XXX` o
   `3XXX` con descripción de qué nodo falla, el cert + auth están bien y
   el problema es la plantilla.
5. **El comprobante quedó aceptado?** El CDR tiene `ResponseCode=0`. Si
   ves `098`, hay observaciones pero está emitido. Si ves cualquier otro
   código, está rechazado y no tiene efecto tributario.

[`TROUBLESHOOTING.md`](./TROUBLESHOOTING.md) tiene un runbook más detallado
por código de error.

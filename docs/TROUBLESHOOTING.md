# Troubleshooting

Cuando algo no jala, este doc te ayuda a identificar en qué capa está
fallando y qué hacer. Está organizado por síntoma — busca lo que ves y
salta a la sección.

## Mapa de capas (para ubicar dónde está el problema)

```
1. Cliente (request HTTP)
   ↓
2. FastAPI (validación Pydantic, routing)
   ↓
3. Servicio (orquestación)
   ↓
4. Builder UBL (construcción del XML)
   ↓
5. Signer XMLDSig (firma)
   ↓
6. Cliente SOAP (zeep + WS-Security)
   ↓
7. SUNAT (auth, validación de UBL, devuelve CDR)
   ↓
8. Storage (Supabase / local)
   ↓
9. BD (Postgres)
```

Cada error tiene un origen típico en una capa específica. Las tablas más
abajo lo aclaran.

## Errores en setup local

### `pip install` falla en Windows con `lxml` o `cryptography`

Causa: pip no encuentra wheel pre-compilado y trata de compilar contra
fuentes C, pero Windows no tiene compilador.

Fix: instala las **Visual C++ Build Tools** (vienen con Visual Studio
Installer, marca "Desktop development with C++"). Después:

```powershell
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
```

### `cryptography: invalid PKCS12 password` al cargar el cert

Causa: tu `CERT_PASSWORD` no coincide con el password del `.pfx`.

Fix:

- Para MODDATOS (cert público de prueba), el password es `MODDATOS`.
- Para tu cert real, revisa con quien te lo emitió (RENIEC u otra CA).
- A veces el `.pfx` no tiene password — prueba dejando `CERT_PASSWORD=`
  vacío.

### `WSDL local no encontrado: packages/core/src/sunat_py/sunat/wsdl/{mode}/billService.wsdl`

Causa: el `MODE` está mal o no clonaste el repo completo (los WSDL están
bundleados en `packages/core/src/sunat_py/sunat/wsdl/{beta,prod}/`).

Fix:

- Verifica `MODE=beta` o `MODE=prod` en `.env`.
- Verifica que `ls packages/core/src/sunat_py/sunat/wsdl/beta/` muestra
  `billService.wsdl billService_ns1.wsdl billService_xsd2.xsd`.
- Si los WSDL no están, vuelve a clonar el repo (no son submódulos, deben
  venir en el clone normal).

### `psycopg.errors.OperationalError` corriendo tests o el server

Causa: `DATABASE_URL` apunta a una BD que no existe / no está corriendo.

Fix:

- Si usas Postgres local: confirma que está corriendo (`pg_isready`) y
  crea la BD (`createdb sis_facturador_dev`).
- Si usas Supabase: verifica que copiaste la connection string completa
  (incluye host, port, password, sslmode).
- En Windows con PostgreSQL en `D:\PostgreSQL\18`, el servicio puede no
  estar corriendo — arranca `services.msc` → buscar postgresql-x64-18 →
  Start.

## Errores hablando con SUNAT

Estos vienen del WS, después de que tu envío llegó. Cada uno tiene una
acción específica.

### `0102` — Usuario o contraseña inválidos

**Capa**: 6 (auth WS-Security).

Causa: `SUNAT_USER` o `SUNAT_PASSWORD` están mal, o estás apuntando al
WS equivocado (mandando creds de prod a beta o viceversa).

Fix:

1. Revisa que `SUNAT_USER` no tenga el RUC adelante. Es solo el username
   del secundario (ej. `FACSIS11`, no `20495184120FACSIS11`). El código
   prefija el RUC al armar el UsernameToken.
2. Revisa `MODE` — credenciales de beta no funcionan en prod.
3. Para beta con MODDATOS: `SUNAT_USER=MODDATOS`, `SUNAT_PASSWORD=MODDATOS`.
4. Para prod: tienen que ser las del usuario secundario que creaste en SOL
   ([`SUNAT_SETUP.md`](./SUNAT_SETUP.md) paso 3).

### `0111` — No tiene el perfil para enviar comprobantes

**Capa**: 7 (policy de SUNAT post-auth).

El `0111` es el error más frustrante de diagnosticar porque la auth pasó —
SUNAT te identificó pero te rechaza por configuración. Por orden de
probabilidad:

1. **Cambiaste permisos del secundario hace menos de 24 horas.** SUNAT
   cachea el perfil del usuario secundario por 24 horas calendario desde
   el último Grabar. No hay forma de forzar refresh. Espera el día.
2. **Permisos incompletos del árbol SEE-DSC.** Revisa que el secundario
   tenga marcado:
   - `Servicio de Envío de Documentos Electrónicos por Servicio Web`
     (aparece dos veces, marca los dos).
   - `Certificado Digital`.
   - `Consultar Envíos de CPE`.
3. **Username del secundario contiene partes del nombre comercial.** Por
   ejemplo, si tu razón social es "TRANSP M & L EIRL" y creaste el
   secundario como `TRANSPSIS` o `MYLEIRL`, SUNAT lo bloquea. Crea uno
   nuevo con username alfanumérico neutro.
4. **El RUC no está en el padrón de Emisores Electrónicos.** Verifica:
   https://ww1.sunat.gob.pe/ol-ti-itobligado-consulta/padronObligadosCPE
5. **Endpoint principal caído.** Usa el failover:
   - `https://www.sunat.gob.pe/ol-ti-itcpfegem/billService?wsdl`
   - `https://ww1.sunat.gob.pe/ol-ti-itcpfegem/billService?wsdl`

Si pasaron las 24 horas y nada de lo anterior aplica: la salida más
documentada en foros peruanos es **crear un secundario nuevo desde cero**.
A veces el cache del perfil corrupto no se purga.

### `2800` — Tipo de documento de identidad del receptor no permitido

**Capa**: 7 (validación UBL de SUNAT).

Causa: estás mandando una factura tipo `01` con DNI como receptor. La
factura solo acepta RUC.

Fix:

- Si el receptor es persona natural sin RUC, emite **boleta** tipo `03`
  (acepta DNI/CE/Pasaporte). Cambia `tipo_documento="03"` y la serie a
  `B###`.
- Si el receptor es empresa, usa su RUC (`schemeID="6"`).

Mensaje completo típico:

```
2800 - El dato ingresado en el tipo de documento de identidad del receptor
no esta permitido. (nodo: "cbc:ID/schemeID" valor: "1")
```

El `valor: "1"` te confirma que llegó como DNI.

### `3244` — Tipo de transacción del comprobante (mensaje engañoso)

**Capa**: 7 (validación UBL).

Causa: falta `<cac:PaymentTerms>` después de `<cac:AccountingCustomerParty>`
en el UBL. El mensaje del error suena a problema con el `InvoiceTypeCode`
pero no es eso.

Fix: el bug ya está cubierto por la plantilla actual. Si lo ves, es porque
modificaste `sunat_py/ubl/templates/invoice_01.xml.j2` y removiste el bloque:

```xml
<cac:PaymentTerms>
  <cbc:ID>FormaPago</cbc:ID>
  <cbc:PaymentMeansID>Contado</cbc:PaymentMeansID>
</cac:PaymentTerms>
```

Vuelve a ponerlo.

### `INFO 4242` — AddressTypeCode no es código de establecimiento

**Capa**: 7 (validación UBL, no bloqueante en beta).

Causa: estás poniendo el ubigeo (ej. `"150101"`) en `<cbc:AddressTypeCode>`
en lugar del código del establecimiento (`"0000"` para sede principal).

Fix: el `AddressTypeCode` no es ubigeo — es el código de 4 dígitos que
SUNAT le asigna a cada local del contribuyente. Para el local principal,
es `"0000"`. Si tienes locales adicionales, cada uno tiene su código
asignado.

En prod en algunos casos la observación se vuelve bloqueante. Mejor
corregirla siempre.

### `0306` — El nombre del archivo no coincide con el contenido

**Capa**: 7.

Causa: el nombre del ZIP que mandas no matchea el formato esperado, o el
XML adentro no se llama igual.

Fix: el formato exacto es `{RUC}-{tipo}-{serie}-{numero}.zip`, conteniendo
`{RUC}-{tipo}-{serie}-{numero}.xml`. Por ejemplo:

```
20495184120-01-F001-1.zip
└── 20495184120-01-F001-1.xml
```

Si modificaste la lógica de naming en los scripts o el service, este es el
síntoma.

### `0150` — RUC del emisor no coincide con el del cert

**Capa**: 7.

Causa: el cert que estás usando es de otro RUC distinto al de
`SUNAT_RUC`.

Fix: revisa que el cert registrado en SOL para producción sea el mismo que
tienes en `CERT_PFX_BASE64`. Cuando renuevas el cert, hay que volver a
registrarlo en SOL (paso 2 de [`SUNAT_SETUP.md`](./SUNAT_SETUP.md)).

### `binascii.Error: Incorrect padding` después de sendBill

**Capa**: 6 (cliente).

Causa: estás intentando decodificar como base64 una respuesta que zeep ya
decodificó.

Fix: ya cubierto. Si lo ves, es porque modificaste `unpack_cdr()` y le
sacaste la detección del magic `PK`. Restaura:

```python
if isinstance(b64_zip, bytes) and b64_zip[:2] == b"PK":
    zip_bytes = b64_zip
else:
    zip_bytes = base64.b64decode(b64_zip)
```

### Timeout >120s al llamar sendBill

**Capa**: 6 / 7.

Causa: SUNAT está lento (pasa, sobre todo en horas pico). El cliente está
configurado con `timeout=120` en `Transport(timeout=120, operation_timeout=120)`.

Fix:

- Reintenta en unos minutos.
- Si quieres más margen, sube los timeouts en `sunat_py/sunat/client.py`. En
  Vercel Hobby el límite duro de la función es 300s, así que máximo
  `timeout=270` para dejar margen al wrap up.
- Si el timeout es persistente, prueba el endpoint failover (cambiar
  hardcoded en `config.py:SUNAT_WSDL_PROD` o agregar lógica de retry con
  failover).

## Errores en Vercel después de deploy

### Healthcheck base devuelve 200 pero `/v1/health/cert` devuelve 500

Causa: `CERT_PFX_BASE64` se pegó truncado en Vercel, o `CERT_PASSWORD`
está mal.

Fix:

1. Vercel limita la longitud de env vars a 64 KB. Un `.pfx` típico
   pasado a base64 pesa ~3-5 KB, no debería tener problema pero verifica
   en **Project Settings → Environment Variables** que el valor completo
   está pegado (a veces se trunca al copiar de la consola).
2. Si el password tiene caracteres especiales (`#`, `$`, etc.), Vercel los
   maneja bien, pero verifica que no se hayan escapado al pegar.

### Logs de Vercel muestran `Storage backend not configured`

Causa: pusiste `STORAGE_BACKEND=local` en Vercel, pero local usa
filesystem que es efímero — la siguiente request no encuentra los
archivos.

Fix: en producción Vercel, **siempre** `STORAGE_BACKEND=supabase`. Local
solo para dev.

### El primer envío después de deploy es lento (~30s)

Causa: cold start. El primer request al pod inicializa el cliente zeep,
parsea WSDL, carga el cert. Es esperado.

Fix: Fluid Compute en Vercel reduce esto manteniendo el pod warm. Si te
importa la latencia del primer request, considera ping cada 5 minutos a
`/v1/health` (con un cron externo).

## Errores con la BD

### `Invoice` no se persiste pero el comprobante fue aceptado por SUNAT

**Capa**: 9.

Causa: el envío a SUNAT funcionó pero el `db.commit()` falló. El
comprobante existe del lado de SUNAT pero tú no tienes registro local.

Fix: revisa los logs por la excepción de SQLAlchemy. Causas comunes:

- Constraint violation (otro proceso insertó el mismo `(ruc, tipo, serie,
  numero)`).
- BD desconectada.
- Schema desactualizado (las migraciones no se aplicaron).

**Importante**: el comprobante existe en SUNAT y tiene efecto tributario
aunque tú no lo tengas registrado. Si quieres invalidarlo, tienes que
emitir Nota de Crédito. No basta con borrar la fila local.

### `IntegrityError` con violación de UNIQUE constraint

Causa: estás intentando emitir un comprobante con `(ruc, tipo, serie,
numero)` que ya existe.

Fix: el router devuelve 409 Conflict con mensaje claro. Revisa el
contador de la serie — si llevas un contador en tu lado, está
desincronizado. Si lo manejas a través de la BD (`MAX(numero) + 1`), hay
race condition; usa una sequence Postgres dedicada.

## Cuando nada de lo anterior aplica

Pasos generales para diagnosticar:

1. Reproducir el problema en local con `MODE=beta` y MODDATOS.
2. Si en local funciona pero en prod no, comparar env vars.
3. Si en local también falla, capturar el XML firmado generado y validar
   el UBL contra el XSD de SUNAT (`xmllint --schema`).
4. Si el UBL es válido pero SUNAT lo rechaza con un código que no está acá,
   buscar en el [Anexo VIII de SUNAT](https://cpe.sunat.gob.pe/sites/default/files/inline-files/anexoVIII.pdf)
   — tiene el catálogo completo de códigos de error.
5. Como último recurso, abrir un issue con: el código exacto, el mensaje
   completo de SUNAT, el XML firmado anonimizado, y el escenario.

## Recursos externos útiles

- Manual del Programador SEE-DSC: descargable desde
  https://cpe.sunat.gob.pe (sección "Manuales y documentos")
- Catálogos SUNAT (Anexo VIII): el documento que tiene todos los códigos
- [Greenter (PHP)](https://github.com/giansalex/greenter): la
  implementación de referencia. Útil para contrastar comportamiento
  cuando algo no está claro.
- Foros donde la gente reporta problemas reales y soluciones:
  - r/Peru en Reddit (busca "SUNAT facturación electrónica")
  - Foros de NubeFacT, Mifact, Tumi-soft (con cuidado, mucho está
    desactualizado pre-2024)
  - StackOverflow tag `sunat` (poco activo pero hay joyas)

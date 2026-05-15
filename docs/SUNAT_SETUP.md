# Habilitar un RUC para emitir comprobantes electrónicos en producción

Esta guía es para el titular del RUC (o quien tenga el usuario primario del
SOL) que va a usar el SIS Facturador en producción real. **Sin estos pasos,
el código no sirve** — el WS de producción te va a rechazar todo intento con
algún código de la familia `01XX`.

Asume que ya pasaste la homologación en beta (si todavía no, primero corre
`scripts/sendbill_beta.py` con MODDATOS). El proceso a continuación es lo
que SUNAT exige adicional para emitir contra `e-factura.sunat.gob.pe`.

## Requisitos legales mínimos

El contribuyente tiene que estar:

- Con **RUC activo** (no suspendido ni de baja).
- Con estado **HABIDO**. Si está NO HABIDO, primero hay que regularizar
  domicilio fiscal — ningún WS te va a aceptar nada hasta entonces.

Lo verificas en la consulta RUC pública de SUNAT.

## Paso 1 — Confirmar afiliación al SEE-DSC en producción

El SEE-DSC ("Sistema de Emisión Electrónica - Del Contribuyente") es el modo
de emitir desde tu propio sistema vía WS. Es distinto del SEE-SOL (emitir
desde un formulario web del portal). Tener permisos de uno **no** te
habilita el otro.

Entra al SOL con el usuario primario y anda a:

> Empresas → Comprobantes de Pago → SEE - Del Contribuyente y Envío de
> Documentos → Servicio de Envío de Documentos Electrónicos

Ahí debe aparecer marcado el checkbox "Deseo emitir a través del SEE - Del
Contribuyente". Si no, márcalo.

En la misma pantalla está el campo de email de notificaciones. **Tiene que
ser un correo real y operable** — SUNAT lo usa para alertas asíncronas
(rechazos de resumen diario, baja de comprobantes, etc.). Si es un
placeholder tipo `noreply@example.com`, las notificaciones se pierden.

> **Nota para clientes nuevos (RS 075-2026/SUNAT, vigente 2026-06-01):** los
> contribuyentes inscritos después de esa fecha quedan emisores electrónicos
> automáticos desde la inscripción del RUC. Saltan este paso 1, ya vienen
> afiliados. Pasos 2 a 5 siguen aplicando igual.

## Paso 2 — Registrar el certificado digital en producción

En la misma sección del paso anterior, hay una sub-sección "Registre aquí su
certificado digital". Sube el `.cer` (la parte pública del cert) y graba.

Ojo: el cert que pasó beta **no se hereda** a producción. Hay que registrarlo
de nuevo aquí. Después de grabar, tiene que aparecer con estado **Activo** y
vigencia válida (de `not_valid_before` a `not_valid_after`).

## Paso 3 — Crear el usuario secundario en SOL

Por las dudas: **no uses el usuario primario para emitir vía WS**. Crea uno
secundario dedicado.

> Empresas → Administración → Usuarios → Mantenimiento de Usuarios
> Secundarios → Nuevo

Sobre el username del secundario hay una restricción rara y poco
documentada: **no puede contener partes del nombre comercial ni palabras del
razón social**. Si tu razón social tiene "MI EMPRESA EIRL", usernames como
`MIEMPSIS` o `MIEMPEIRL` van a ser rechazados. Algo alfanumérico y neutro
funciona — por ejemplo `FACSIS11`, `WSFAC01`, etc.

Si SUNAT te rechaza el username sin explicación clara, casi seguro es por
esto.

## Paso 4 — Marcar los permisos exactos en el árbol del secundario

Este paso es el que más causa `0111` cuando está mal. Después de crear el
secundario, edítalo. En el árbol de permisos a la izquierda, abre la rama:

> SEE - Del Contribuyente y Envío de Documentos

Y marca lo siguiente en el panel de la derecha:

- ✅ **Servicio de Envío de Documentos Electrónicos → Servicio de Envío de
  Documentos Electrónicos por Servicio Web**.
  **Esto aparece dos veces idéntico en el panel.** Uno corresponde al WS
  síncrono `sendBill`, el otro al WS asíncrono `sendSummary` (para
  comunicación de baja y resumen diario). **Marca los dos.**
- ✅ **Certificado Digital** — para que el secundario pueda usar el cert
  registrado del contribuyente.
- ✅ **Consultar Envíos de CPE** — para poder consultar tickets de los WS
  asíncronos con `getStatus`.
- Recomendado por la mesa de ayuda de SUNAT (2024-2026): marcar también
  **Comprobantes de Contingencia** y **Factura Electrónica** completos.
  El WS funciona sin estos, pero marcarlos reduce la chance de que el
  secundario quede con un perfil "gap" no documentado y SUNAT te tire `0111`
  en producción aunque la config se vea correcta.

Graba.

## Paso 5 — Esperar 24 horas calendario

Esto no es opcional, no se puede acortar y es la causa #1 documentada del
`0111` persistente.

SUNAT cachea el perfil del usuario secundario por 24 horas calendario desde
el último Grabar de permisos. Antes de ese plazo, todo `sendBill` te va a
devolver:

```
0111 - No tiene el perfil para enviar comprobantes electronicos
```

Aunque tengas todo perfectamente bien configurado. No hay forma de
forzar refresh; espera el día.

Si pasaron las 24 horas y sigues con `0111`, lo más rápido es crear un
secundario nuevo desde cero con todos los permisos marcados (algunos casos
en foros peruanos reportan que el cache del perfil corrupto no se purga
nunca).

## Paso 6 — Confirmar que el RUC está en el padrón de Emisores Electrónicos

El padrón es la base pública de RUCs habilitados para emisión electrónica.
Verifica que el tuyo aparece:

- Consulta dinámica por RUC:
  https://ww1.sunat.gob.pe/ol-ti-itobligado-consulta/padronObligadosCPE?action=verConsultaComprobanteObligado
- Descarga del padrón:
  https://www2.sunat.gob.pe/cpe/padronobligados.html

Ojo: la URL antigua `cl-ti-itsemisorestados` está caída con 404, fue
renombrada. Si encuentras una guía vieja que la mencione, está
desactualizada.

## Paso 7 — Configurar el `.env` del facturador

```env
MODE=prod
SUNAT_RUC=<tu RUC>
SUNAT_USER=<el username del secundario, ej. FACSIS11>
SUNAT_PASSWORD=<la clave del secundario>
CERT_PFX_BASE64=<el cert real en base64>
CERT_PASSWORD=<la password del .pfx>
```

(El código antepone el RUC al `SUNAT_USER` cuando arma el username
WS-Security, así que `SUNAT_USER` va sin el RUC.)

## Paso 8 — Primer envío real

**Empieza por una boleta**, no por una factura. La boleta acepta DNI y es
más permisiva — si algo está mal en el cert o en los permisos, te enteras
sin haber tocado un RUC ajeno.

```bash
python scripts/sendbill_prod_boleta.py --confirm-real
```

El flag `--confirm-real` es obligatorio: el script aborta sin él. Es para
evitar que corras esto por accidente.

Lo que esperas ver:

```
Status      : accepted
Code        : 0
Description : La Boleta numero B001-1, ha sido aceptada
```

Si ves esto, ya estás en producción.

## Paso 9 — Confirmar en el portal SOL

Entra al SOL y verifica que el comprobante figura como **Procesado**:

> Empresas → Comprobantes de pago → SEE - Del Contribuyente y Envío de
> Documentos → Consultar Envíos de CPE

Te aparece la lista con: fecha, ticket SUNAT, nombre del archivo
(`{RUC}-{tipo}-{serie}-{numero}`), usuario que envió, y estado. "Procesado"
es el estado terminal exitoso.

## Paso 10 — Consulta pública de validez

Esto es lo que vería un cliente del titular si quisiera verificar la validez
del comprobante. Sin login, accesible para cualquiera:

https://www.sunat.gob.pe/ol-ti-itconsvalicpe/ConsValiCpe.htm

Llenas: RUC del emisor, tipo (`01` factura o `03` boleta), serie y número,
fecha de emisión, importe total. Te devuelve "ACEPTADO" si SUNAT lo tiene
registrado.

**Puede tardar varios minutos a horas en aparecer aquí**, aunque el CDR ya
diga aceptado y figure en "Consultar Envíos de CPE" — la sincronización
entre el WS de recepción y la BD pública no es inmediata. El CDR sigue
siendo válido durante ese intervalo.

## Si algo sale mal

| Síntoma                                                              | Causa probable                                                                  | Acción                                                                                                |
|----------------------------------------------------------------------|---------------------------------------------------------------------------------|-------------------------------------------------------------------------------------------------------|
| No encuentras el formulario del SEE-DSC                              | Estás logueado con el secundario, no el primario                                | Cierra sesión, entra con el usuario primario del RUC                                                  |
| El checkbox "Deseo emitir a través del SEE-DC" no aparece            | Tu RUC no es contribuyente normal (puede ser persona natural sin negocio)       | Llama a la mesa de ayuda; algunos tipos de RUC no pueden ser emisores electrónicos                    |
| El árbol del secundario no muestra "SEE - Del Contribuyente y Envío…" | Tu plan de afiliación no está activado                                          | Vuelve al paso 1 y confirma la afiliación antes de configurar permisos                                |
| `0111` persiste pasadas las 24 horas                                 | Cache de perfil corrupto; o algún permiso del árbol no quedó marcado            | Crea un secundario nuevo desde cero (`FACSIS12` etc.) con todos los permisos del árbol y cambia `.env` |
| `0102 - Usuario o contraseña inválidos`                              | Credenciales del secundario están mal                                           | Revisa que `SUNAT_USER` no incluya el RUC; el código lo prefija solo                                  |
| `2800` al emitir factura                                             | Estás mandando DNI como receptor en una factura tipo `01`                       | Cambia a RUC del receptor, o emítelo como boleta `03`                                                 |
| El cert da `cryptography: invalid PKCS12 password`                   | `CERT_PASSWORD` no coincide                                                     | Revisa el password con quien emitió el cert (RENIEC u otra CA)                                        |
| El padrón no muestra tu RUC                                          | Recién te afiliaste, falta sincronización                                       | Espera 24-48 horas; si pasa más, llama a SUNAT                                                        |

## SEE-SOL vs SEE-DSC: la confusión típica

Es probable que en algún punto te ofrezcan "habilitar Factura Electrónica" y
no quede claro qué te están habilitando. Hay dos cosas distintas:

- **SEE-SOL** = emites desde el propio portal SUNAT (formulario web). Los
  permisos `SEE - SOL → Factura Electrónica → Emitir Factura/Boleta/NC/ND`
  son para esto.
- **SEE-DSC** = emites desde tu sistema propio vía WS. Es lo que usa este
  facturador. Los permisos van bajo `SEE - Del Contribuyente y Envío de
  Documentos`.

Tener marcado SEE-SOL no te habilita el WS, y al revés tampoco. Si tu
secundario solo tiene permisos de SEE-SOL, vas a llegar al `0111` aunque te
parezca que "tiene permisos de Factura Electrónica".

## Marco normativo que conviene tener en mente (2024-2026)

- **RS 075-2026/SUNAT** (vigente 2026-06-01): contribuyentes nuevos quedan
  emisores electrónicos automáticos desde la inscripción del RUC. Para
  contribuyentes ya inscritos antes, no cambia nada.
- **RS 062-2026/SUNAT**: proyecto público con cambios adicionales a
  designación de emisores. Vale la pena seguirlo.
- **RS 240-2024 + RS 133-2025**: solo aplican a Guía de Remisión
  Electrónica, que es otro WSDL distinto.
- **SIRE obligatorio en paralelo**: registro de ventas/compras electrónico,
  lo lleva el contribuyente (o su contador), no este facturador. Vale
  mencionarlo a clientes para que sepan que existe.

# Changelog

Cambios del SDK `sunat-py` (Python). Sigue el formato de
[Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/) y
[Semantic Versioning](https://semver.org/lang/es/).

> Este changelog cubre **solamente el SDK** (`packages/core/`). Para
> cambios del microservicio FastAPI o de la infraestructura de deploy,
> ver el [CHANGELOG raiz del repo](../../CHANGELOG.md).

## [0.5.0] - 2026-05-14

Cierre del roadmap de tipos faltantes vs Greenter para el IGV:
retencion (tipo 20) y percepcion (tipo 40). Suma validacion XSD
client-side (UBL 2.1 + extensiones SUNAT 1.0 bundleados) y los 4
fixes de seguridad del audit interno del 2026-05-12
(`docs/security/audit-2026-05-12.md`). Sin breaking changes de API
funcional sobre 0.3.0; el bump a minor refleja el alcance de superficie
publica nueva, no rupturas.

### Validado en SUNAT beta (2026-05-14)

Retencion `R001-1` aceptada con `code=0`. Prod aun no probado.

### Agregado

- **Comprobante de retencion (tipo 20)**: `RetentionInput`,
  `RetentionDocReference`, `build_retention_xml`, plantilla
  `retention_20.xml.j2`. Sobre UBL 2.0 + extensiones SUNAT
  (`urn:sunat:names:specification:ubl:peru:schema:xsd:Retention-1`).
  Catalogo SUNAT 23 (`retention_regime`) con la tasa vigente 3% (2014+)
  y la historica 6%. Validador previo en `validate_retention`: regimen,
  tasa, serie `R###`, consistencia de totales contra suma de items y
  exigencia de tipo de cambio para items en moneda extranjera.
- **Comprobante de percepcion (tipo 40)**: `PerceptionInput`,
  `PerceptionDocReference`, `build_perception_xml`, plantilla
  `perception_40.xml.j2`. Mismo namespace SUNAT con local-name
  `Perception`. Catalogo SUNAT 22 (`perception_regime`) con regimenes
  combustible (01, 1%), venta interna (02, 2%), importacion (03).
  Validador previo en `validate_perception` simetrico al de retencion
  (suma de items, tipo de cambio, serie `P###`).
- **Validador XSD client-side** (`sunat_py.xsd`): valida XML UBL contra
  los XSD oficiales antes de firmar y enviar. Bundle de schemas en
  `sunat_py/xsd/schemas/` con dos arboles paralelos: `ubl-2.1/`
  (Invoice/CreditNote/DebitNote/DespatchAdvice) y `sunat-1.0/`
  (SummaryDocuments/VoidedDocuments/Retention/Perception). Funciones
  publicas: `validate_invoice`, `validate_creditnote`, `validate_debitnote`,
  `validate_despatchadvice`, `validate_summary`, `validate_voided`,
  `validate_retention`, `validate_perception`, y
  `validate_signed_xml(xml)` que infiere el kind del root element.
  Errores como `XSDValidationError` con linea + XPath de cada falla.
  Carga lazy con `lru_cache`. Cierra el dev loop opaco: ya no hace
  falta esperar el CDR de SUNAT para descubrir un tag mal formado.
- **`sunat_py.security.install_log_redactor()`**: helper opt-in que
  enmascara `password=`, `client_secret=` y `Authorization: Bearer ...`
  en los loggers `urllib3.connectionpool` y `zeep`. Para callers que
  activan `logging.DEBUG` para depurar trafico SUNAT y no quieren que
  los secretos OAuth2 ni el bearer token del GRE terminen en cleartext
  en su pipeline de logs. No se instala automaticamente: el SDK respeta
  la cadena de loggers del proceso del caller.
- **`scripts/refresh_xsd_schemas.py`**: script para regenerar el bundle
  XSD desde las publicaciones oficiales (OASIS UBL 2.1 + SUNAT 1.0).
  Permite reproducir el contenido de `sunat_py/xsd/schemas/` sin tener
  que confiar en lo que esta versionado en el repo.

### Corregido

- **Endpoint SOAP de retencion y percepcion**: el SDK mandaba tipo 20 y
  40 al billService principal (`ol-ti-itcpfegem/billService`) que solo
  acepta factura/boleta/NC/ND/RA/RC. Resultado: SUNAT devolvia `0151`
  ("nombre de archivo / cpe no es valido") para todo intento de RET/PER.
  Fix: nuevo WSDL bundleado `billService_otroscpe.wsdl` apuntando a
  `ol-ti-itemision-otroscpe-gem/billService` y selector `service` en
  `build_zeep_client(..., service="bill"|"otroscpe")`. Default "bill"
  preserva backwards-compat para callers que solo usan factura/boleta.
- **Extraccion del codigo de error en SOAP Fault**: SUNAT manda algunos
  faults con `faultcode="soap-env:Client"` y el codigo numerico
  embebido en `faultstring` (`<faultstring>2603</faultstring>`). El
  patron previo solo cubria `faultcode="soap-env:Client.0306"`. Sin
  este fix los rechazos del servicio otroscpe se promovian a
  `SunatError`/HTTP 502 en lugar de mapearse a `SunatResult(status="rejected")`/200.
  Fix: si el faultcode no contiene un sufijo numerico, leer
  `fault.message` y usarlo como codigo cuando es solo digitos.

### Cambiado

- **`CertBundle`** ya no expone `private_key` ni `key_pem` en `repr()`.
  Antes, un `print(bundle)` o `logger.info("%s", bundle)` filtraba la
  PEM PKCS8 sin encriptar de la clave privada del contribuyente. La
  estructura del dataclass queda igual; solo cambia la salida de
  `repr()`. Para identificar bundles en logs usar las properties
  `common_name` y `serial_hex`.
- **Cliente zeep SOAP** (`build_zeep_client`): `xml_huge_tree=True` fuera
  (cierra Billion Laughs / quadratic blowup en el parser XML del CDR)
  y `strict=True` (zeep valida la respuesta contra el WSDL local).
- Docstrings de `get_gre_token` y `send_gre` ahora documentan que el
  body OAuth2 y el header Authorization llevan secretos en cleartext,
  y apuntan al redactor como mitigacion.
- **`pyproject.toml`** incluye `sunat_py.xsd` en `package-data`, asi
  `pip install sunat-py` se lleva el bundle completo de schemas.

### Resuelto incidentalmente

- Mismatch entre `pyproject.toml` (`0.3.0`) y tag `v0.4.0`: el tag se
  creo al hacer el rename `pe-invoicing -> sunat-py`, pero el bump
  del `version` field quedo pendiente y el wheel jamas se publico
  bajo `v0.4.0`. Este release alinea pyproject, CHANGELOG y un tag
  nuevo `v0.5.0`. El tag `v0.4.0` queda como artefacto del rename
  sin release asociado en PyPI.

## [0.3.0] - 2026-05-11

Primer release publicado a PyPI bajo el nombre `sunat-py`. Hasta esta
version el paquete vivia en el monorepo como `pe-invoicing` y no se
distribuia por PyPI. El renombre es por descubribilidad (devs peruanos
googlean "sunat python", no "pe invoicing").

### Validado en produccion (2026-05-11)

Cinco comprobantes nuevos aceptados por SUNAT prod con `code=0`:

| Tipo | Comprobante | Status | Ticket |
|------|---|---|---|
| NC (07) | `FC01-1` | accepted (2026-05-10) | — |
| NC (07) | `FC01-2` | accepted | — |
| ND (08) | `FD01-1` | accepted | — |
| RC | `RC-20260511-1` | accepted | `202620699620214` |
| RA | `RA-20260511-1` | accepted | `202620699633180` |

CDR de cada uno en `examples/R-20XXXXXXXXX-*.xml` para referencia.

### Agregado

- **Notas de credito (tipo 07)**: `CreditNoteInput`, `ReferenciaDoc`,
  `build_creditnote_xml`, plantilla `creditnote_07.xml.j2`. Catalogo 9 de
  motivos. Validado en prod 2026-05-10 (`FC01-1`) y 2026-05-11 (`FC01-2`).
- **Notas de debito (tipo 08)**: `DebitNoteInput`, `build_debitnote_xml`,
  plantilla `debitnote_08.xml.j2`. Catalogo 10 de motivos. Validado en
  prod 2026-05-11 (`FD01-1` aceptada code 0).
- **Comunicacion de baja (RA)**: `VoidedDocumentsInput`, `VoidedItem`,
  `build_voided_xml`, plantilla `voided_RA.xml.j2`. Envio asincrono por
  `sendSummary` + polling con `get_status` por ticket. Validado en prod
  2026-05-11 (`RA-20260511-1`, ticket `202620699633180`).
- **Resumen diario de boletas (RC)**: `SummaryDocumentsInput`,
  `SummaryItem`, `build_summary_xml`, plantilla `summary_RC.xml.j2`. Mismo
  flujo asincrono que la baja. Validado en prod 2026-05-11
  (`RC-20260511-1`, ticket `202620699620214`).
- **Guia de Remision Remitente (tipo 09)** por la Nueva GRE REST
  (`api-cpe.sunat.gob.pe`): `DespatchAdviceInput`, `DireccionTraslado`,
  `GRLine`, `Transportista`, `Conductor`, `Vehiculo`,
  `build_despatchadvice_xml`, plantilla `despatchadvice_09.xml.j2`.
  Cliente REST `sunat_py.sunat.gre_client` con OAuth2 password grant,
  envio sin `.zip` en el path y polling de CDR por `numTicket`. Verificado
  en prod 2026-05-11.
- **Validadores previos al envio** (`sunat_py.validators`): RUC con DV
  modulo 11, fechas (hoy en zona Lima UTC-5, no permite emision futura ni
  > 3 dias atras para boletas), totales (recalculo de IGV y consistencia
  linea vs total), identidad (catalogo 6) y emisor (consistencia
  RUC↔cert).
- **Catalogos SUNAT** (`sunat_py.catalogs`): motivos NC (cat. 9), motivos
  ND (cat. 10), tipos doc (cat. 1), identidad (cat. 6), afectacion IGV
  (cat. 7), modalidad transporte (cat. 18), motivos traslado (cat. 20).
  Constantes con docstrings de cada codigo.
- **Jerarquia de errores propia** (`sunat_py.errors`): `ValidationError`,
  `SunatError` y subclases. Antes el SDK propagaba excepciones genericas
  de zeep/lxml/signxml; ahora se envuelven para que el consumer pueda
  catchear `SunatError` sin importar libs internas.
- **`py.typed` marker** (PEP 561). Los consumers ahora ven los tipos del
  SDK con mypy/pyright sin configuracion extra.
- **Tests con mocks de zeep.Client** (`tests/mocks/sunat_mock.py`,
  `tests/unit/test_pipeline_with_mocks.py`). Antes solo habia integration
  contra SUNAT beta; ahora el pipeline (build → sign → pack → send) se
  puede testear offline en CI.

### Cambiado

- **Nombre del paquete**: `pe-invoicing` → `sunat-py`. Import name:
  `pe_invoicing` → `sunat_py`. Es un breaking change pero no hay usuarios
  externos (no estaba publicado).
- **Patron de serie** aflojado a `^[FB][A-Z0-9]{3}$` para aceptar series
  alternativas como `FC01`, `BC01` usadas en notas de credito.

### Corregido

- `cbc:InvoiceTypeCode` ahora interpola `tipo_documento` de
  `InvoiceInput` en lugar de hardcodear `"01"`. Bug latente: la misma
  plantilla servia para factura y boleta pero el codigo iba duro.

### Gotchas SUNAT documentados (2026-05-11)

- **RA no anula boletas (tipo 03)** — SUNAT devuelve error `2308`. Las
  boletas se anulan **modificando** el resumen diario (RC) original con
  `EstadoItem="3"` (baja), no enviando un RA. El SDK no bloquea esto:
  validar en el caller que `VoidedItem.tipo_doc != "03"` antes de armar
  un RA.
- **Resumen diario de boletas y RA son distintos** aunque comparten el
  `sendSummary` async. RC = consolidado del dia para boletas (obligatorio
  enviarlo D+7). RA = anulacion de facturas o NC/ND emitidas. No confundir.

## [0.2.0] - 2026-05-10 (interno, no publicado)

- Notas de credito tipo 07 (validado contra SUNAT beta). Vivio en el
  monorepo como `pe-invoicing 0.2.0`.

## [0.1.0] - 2026-05-08 (interno, no publicado)

Primer pipeline funcional end-to-end. Boleta `B001-1` y factura `F001-1`
aceptadas con code 0 en SUNAT prod (RUC `20XXXXXXXXX`). Vivio como
`pe-invoicing 0.1.0`.

### Incluido

- Generacion UBL 2.1 con Jinja2 + lxml. Conversor de numeros a letras en
  espanol. Calculo de IGV 18%.
- Firma XMLDSig RSA-SHA256 + Exclusive C14N con `signxml`. Reubicacion
  del `ds:Signature` dentro de `cac:UBLExtensions`.
- Cliente SOAP `sendBill` sobre `zeep` con WSDLs bundleados (beta y prod)
  para evitar rate-limit de SUNAT en `?ns1.wsdl`.
- Loader de cert `.pfx` desde archivo o base64.
- Helpers de packaging ZIP y unpack de CDR.

[0.5.0]: https://github.com/userDKX/SIS-Facturador/releases/tag/v0.5.0
[0.3.0]: https://github.com/userDKX/SIS-Facturador/releases/tag/v0.3.0
[0.2.0]: https://github.com/userDKX/SIS-Facturador/releases/tag/v0.2.0
[0.1.0]: https://github.com/userDKX/SIS-Facturador/releases/tag/v0.1.0

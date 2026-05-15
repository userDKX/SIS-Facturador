# Bundle de XSDs para validacion client-side

Este directorio aloja los XSD oficiales que `sunat_py.xsd.validator` usa
para validar XML UBL antes de firmar/enviar. Los XSDs van **versionados
en git** y empaquetados en la wheel PyPI — un usuario que instale
`sunat-py` no descarga nada en runtime.

## Layout

```
schemas/
├── README.md                   (este archivo)
├── NOTICE.md                   (atribucion OASIS / SUNAT)
├── ubl-2.1/                    OASIS UBL 2.1 (factura/boleta/NC/ND/GRE)
│   ├── maindoc/
│   │   ├── UBL-Invoice-2.1.xsd
│   │   ├── UBL-CreditNote-2.1.xsd
│   │   ├── UBL-DebitNote-2.1.xsd
│   │   └── UBL-DespatchAdvice-2.1.xsd
│   └── common/
│       ├── UBL-CommonAggregateComponents-2.1.xsd
│       ├── ...                 (resto de common UBL 2.1)
└── sunat-1.0/                  SUNAT UBL 2.0 + extensiones (RA/RC/RET/PER)
    ├── maindoc/
    │   ├── UBLPE-Retention-1.0.xsd
    │   ├── UBLPE-Perception-1.0.xsd
    │   ├── UBLPE-SummaryDocuments-1.0.xsd
    │   ├── UBLPE-VoidedDocuments-1.0.xsd
    │   └── UBLPE-ApplicationResponse-1.0.xsd   (CDR)
    └── common/
        ├── UBL-CommonAggregateComponents-2.0.xsd
        ├── UBL-CommonBasicComponents-2.0.xsd
        ├── UBLPE-SunatAggregateComponents-1.0.xsd
        ├── UBLPE-SunatAggregateComponents-1.1.xsd
        ├── ...                 (resto de common UBL 2.0)
```

## Por que dos arboles

SUNAT publica los CPE en dos generaciones tecnicas distintas:

- **Factura, boleta, nota de credito, nota de debito, GRE**: migraron a
  UBL 2.1 a partir de la Resolucion 097-2012 y mantuvieron ese
  esquema. Validan contra los XSD OASIS UBL 2.1 puros (mas las
  extensiones SUNAT que viven dentro de `<ext:UBLExtensions>` como
  contenido libre).
- **Retencion (20), percepcion (40), comunicacion de baja (RA),
  resumen diario (RC)**: nacieron en UBL 2.0 (Resolucion 188-2010) con
  extensiones SUNAT propias (`UBLPE-*-1.0.xsd`). SUNAT nunca publico
  version 2.1 para estos CPE. Usan namespaces `urn:sunat:names:
  specification:ubl:peru:schema:xsd:...`.

Por eso el bundle tiene dos arboles separados con UBL 2.0 y UBL 2.1
en paralelo. Es como SUNAT lo distribuye.

## Refrescar el bundle (rol de mantenedor)

Solo el mantenedor del repo corre este flujo, antes de publicar una
release que actualice el bundle. El usuario final del SDK NO necesita
hacer nada — la wheel PyPI viene con todo adentro.

```
make refresh-xsd
```

O directo:

```
python scripts/refresh_xsd_schemas.py
```

El script:

1. **OASIS UBL 2.1**: descarga los XSDs uno por uno desde
   `https://docs.oasis-open.org/ubl/os-UBL-2.1/xsd/`. URL estable,
   estandar congelado desde 2013.
2. **SUNAT UBL 2.0 + extensiones**: descarga el ZIP oficial desde
   `https://cpe.sunat.gob.pe/sites/default/files/inline-files/
   Archivos%20XSD%20%281%29.zip` (publicado al 28/02/2022) y extrae
   los XSDs relevantes a `sunat-1.0/`.

Cada archivo se valida (parsea como `xs:schema`, reporta su
`targetNamespace`) antes de escribirse al repo. Si OASIS o SUNAT cambia
un URL/contenido, el script aborta con error claro.

Despues:

```
git diff packages/core/src/sunat_py/xsd/schemas/
git add packages/core/src/sunat_py/xsd/schemas/
git commit -m "chore(xsd): refresh bundle vYYYY-MM"
```

## Por que bundlear en el repo

- **Wheel self-contained**: `pip install sunat-py` y la validacion XSD
  funciona offline. Sin URLs externas en runtime ni en setup.
- **Hash versionado**: cualquier cambio queda como diff en `git log`.
- **Reproducibilidad**: clone limpio + `make test` funciona sin tocar
  red. CI no depende de la disponibilidad de docs.oasis-open.org o
  cpe.sunat.gob.pe.

## Politica de redistribucion

- **OASIS UBL 2.1**: redistribuible bajo OASIS Open IPR (preservar
  copyright header). Atribucion en `NOTICE.md`.
- **SUNAT UBLPE-* + UBL 2.0**: artefactos publicos del Estado peruano,
  publicados en el portal CPE como parte de la regulacion de CPE.
  Reconocimiento en `NOTICE.md`.

## Bypass / opt-out

Si el bundle no esta presente (ej. instalacion editable sin haber
corrido el flujo de refresh todavia), `validate_*()` levanta
`FileNotFoundError` con mensaje claro. El SDK sigue funcionando sin
validacion client-side: `validate_signed_xml()` solo se invoca cuando
el caller lo pide explicitamente.

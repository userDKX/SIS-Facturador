# SIS Facturador

[![CI](https://github.com/userDKX/SIS-Facturador/actions/workflows/ci.yml/badge.svg)](https://github.com/userDKX/SIS-Facturador/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.11%2B-3776AB?logo=python&logoColor=white)](https://www.python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![License](https://img.shields.io/github/license/userDKX/SIS-Facturador)](./LICENSE)
[![Last commit](https://img.shields.io/github/last-commit/userDKX/SIS-Facturador)](https://github.com/userDKX/SIS-Facturador/commits/main)

API REST para facturar electrónicamente ante SUNAT (Perú), escrita en Python.
Genera Factura (`01`) y Boleta (`03`) en UBL 2.1, las firma con XMLDSig
RSA-SHA256, las manda por SOAP al webservice del contribuyente (SEE-DSC) y
guarda el CDR aceptado.

Está corriendo en producción real desde el 2026-05-08.

## Por qué Python (y no otra cosa)

Si has buscado cómo facturar a SUNAT desde código, ya te diste cuenta: casi
todo lo que hay es PHP. Greenter, Mifact, q8factura, NubeFacT — todos viven en
ese mundo. Para alguien que trabaja en Python (FastAPI, Django, data, ML), eso
significa o usar un wrapper, o lanzar un subproceso PHP, o pelearte con la
documentación traducida.

Este repo es la implementación nativa en Python del flujo entero: firma con
`signxml`, UBL con `lxml` + `Jinja2`, SOAP con `zeep`, HTTP con `FastAPI` y
Pydantic v2. No envuelve a Greenter ni porta su código — implementa el
estándar de SUNAT directo.

## Lo que ya funciona en producción

El 2026-05-08 se mandaron a `e-factura.sunat.gob.pe`:

- Boleta `B001-1`: aceptada, code 0, ticket `202620668493873`
- Factura `F001-1`: aceptada, code 0, ticket `202620668506859`

Ambos figuran como **Procesado** en el portal SOL bajo
*Empresas → Comprobantes de pago → SEE - Del Contribuyente y Envío de
Documentos → Consultar Envíos de CPE*.

## Stack

- FastAPI 0.115 + Pydantic v2 + Uvicorn
- `lxml` + `Jinja2` para construir el UBL 2.1
- `signxml` + `cryptography` para la firma XMLDSig (RSA-SHA256, Exclusive C14N)
- `zeep` para el cliente SOAP (con WSDL bundleado local)
- SQLAlchemy 2.0 + `psycopg` v3 sobre Postgres (Supabase free tier funciona)
- Vercel Hobby + Fluid Compute (300s) en el modo single-tenant

## Cómo correrlo en local (con cert de prueba MODDATOS)

```powershell
git clone https://github.com/userDKX/SIS-Facturador.git
cd SIS-Facturador
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
# editas .env y pegas el CERT_PFX_BASE64
uvicorn sis_facturador.main:app --reload
```

Health: `GET http://localhost:8000/v1/health`. Swagger: `http://localhost:8000/docs`.

Detalle paso a paso (incluye la conversión del `.pfx` a base64 y el
troubleshooting típico) en [`docs/INSTALL.md`](./docs/INSTALL.md).

## El flujo, en cinco cajas

```
POST /v1/invoices
      │
      ▼
schemas.InvoiceCreate          (validación Pydantic)
      ▼
ubl.builder.build_invoice_xml  (UBL 2.1 sin firmar)
      ▼
signer.xmldsig.sign_invoice_xml  (XMLDSig embebido en
      │                           cac:UBLExtensions/.../ExtensionContent)
      ▼
sunat.packager.pack_invoice    (ZIP {ruc}-{tipo}-{serie}-{nro}.zip)
      ▼
sunat.client.send_bill         (SOAP a SUNAT, parsea CDR, devuelve resultado)
```

## Modos de despliegue

Hay dos, que conviven en el mismo codebase (regla "cero ramas por modo": todo
configurable por envs, nunca por `if` en el código):

- **Single-tenant en Vercel.** 1 cliente = 1 deploy. Es lo que está
  implementado y validado. Sirve para un comercio individual, un freelancer,
  alguien que solo factura para su propia empresa. Costo: Vercel Hobby gratis
  + Supabase free.
- **Multi-tenant provider en Kubernetes.** Para una empresa que quiere ser
  proveedora de facturación a varios RUCs (un holding, un contador, un SaaS).
  Por ahora solo existe la arquitectura conceptual en
  [`docs/DEPLOY_PROVIDER.md`](./docs/DEPLOY_PROVIDER.md) — no hay código aún.
  Agrega auth por API key, RLS por tenant, vault para los `.pfx`, rate limit
  y stack de observabilidad.

## Para empezar

- [`docs/INSTALL.md`](./docs/INSTALL.md) — instalar y correr local en 10
  minutos, con cert de prueba.
- [`docs/SUNAT_SETUP.md`](./docs/SUNAT_SETUP.md) — onboarding del titular del
  RUC en producción: crear el usuario secundario, marcar los permisos
  exactos, registrar el certificado, esperar las 24 horas.
- [`docs/SIGNING.md`](./docs/SIGNING.md) — el lado técnico de la firma:
  XMLDSig vs XAdES, dónde tiene que ir el `<ds:Signature>`, los gotchas que
  cuestan horas si no los conoces.

## Documentación completa

- [`docs/ARCHITECTURE.md`](./docs/ARCHITECTURE.md) — capas y diagrama del
  código.
- [`docs/UBL.md`](./docs/UBL.md) — los detalles de UBL 2.1 que SUNAT valida.
- [`docs/SUNAT.md`](./docs/SUNAT.md) — protocolo SOAP, errores frecuentes,
  marco normativo 2024-2026.
- [`docs/DEPLOY_VERCEL.md`](./docs/DEPLOY_VERCEL.md) — desplegar el modo
  single-tenant.
- [`docs/DEPLOY_PROVIDER.md`](./docs/DEPLOY_PROVIDER.md) — arquitectura del
  modo multi-tenant en Kubernetes (conceptual).
- [`docs/TROUBLESHOOTING.md`](./docs/TROUBLESHOOTING.md) — qué hacer cuando
  SUNAT te devuelve un código que no entiendes.

## Errores SUNAT más frecuentes

| Código | Qué significa                                                | Qué hacer                                                |
|--------|--------------------------------------------------------------|----------------------------------------------------------|
| `0102` | Usuario o contraseña SOL inválidos                           | Revisa `SUNAT_USER` (el código le antepone el RUC).      |
| `0111` | Tu secundario no tiene perfil para emitir vía WS             | Espera 24 horas calendario después del último Grabar.    |
| `2800` | DNI como receptor en factura tipo 01                         | Usa RUC, o emite como boleta tipo 03.                    |
| `3244` | Falta `cac:PaymentTerms` después de `AccountingCustomerParty`| Bug del template UBL.                                    |
| `4242` | `AddressTypeCode` con ubigeo en lugar del código de local    | Usa `"0000"` para sede principal.                        |

Detalle de cada uno en [`docs/SUNAT.md`](./docs/SUNAT.md) y
[`docs/TROUBLESHOOTING.md`](./docs/TROUBLESHOOTING.md).

## Roadmap

Ya hecho:

- Factura tipo `01` end-to-end (validada en prod)
- Boleta tipo `03` end-to-end (validada en prod)

Por hacer:

- Nota de Crédito (`07`)
- Nota de Débito (`08`)
- Comunicación de baja (sendSummary async + Vercel Cron)
- Resumen diario de boletas
- PDF con QR (WeasyPrint)
- Auth por API key (preparación multi-tenant)
- Soporte OSE (operador de servicios electrónicos)
- Guía de Remisión (otro WSDL)
- Implementación del modo provider en K8s

## Estructura del repo

El repo es un workspace con dos paquetes:

```
packages/
├── core/                       pe-invoicing (SDK, publicable a PyPI)
│   ├── pyproject.toml
│   └── src/pe_invoicing/
│       ├── ubl/                generación UBL 2.1 (Jinja2 + lxml)
│       ├── signer/             firma XMLDSig RSA-SHA256
│       ├── sunat/              cliente zeep + WSDLs bundleados
│       └── security/           carga del cert .pfx desde base64
└── api/                        sis-facturador (microservicio HTTP)
    ├── pyproject.toml          depende de pe-invoicing
    └── src/sis_facturador/
        ├── main.py             FastAPI + middleware + healthcheck
        ├── config.py           pydantic-settings (lee .env)
        ├── database.py         SQLAlchemy + psycopg v3
        ├── sunat_runtime.py    wrappers cacheados del SDK
        ├── storage/            adaptadores local + Supabase Storage
        ├── models/             ORM SQLAlchemy
        ├── schemas/            Pydantic v2
        ├── services/           orquestación
        └── routers/            endpoints REST

api/index.py                    entry-point para Vercel (importa sis_facturador)
scripts/                        bootstrap_db, verify_cert, sendbill_*
migrations/                     SQL plano para Supabase
docs/                           documentación
examples/                       payloads y curl listos para usar
```

**El SDK** (`packages/core`) no toca FastAPI ni la BD — es una librería pura
que cualquier dev Python puede `pip install pe-invoicing` y usar desde su
propia app. **El microservicio** (`packages/api`) es un wrapper delgado
encima del SDK: agrega HTTP, persistencia, storage y deploy.

## Contribuir

Si encuentras un bug, una observación INFO de SUNAT que no documentamos, o
quieres agregar Notas de Crédito antes que yo — abre un issue o un PR. La
gente que más puede ayudar es quien ya peleó con esto antes y se acuerda de
los detalles raros del SOL.

## Quién mantiene esto

Construido por **Luis Luza M.** ([@userDKX](https://github.com/userDKX)) en
Lima. Lo uso en producción para clientes del sistema SIS y lo dejo abierto
para que cualquier dev peruano que esté empezando con SUNAT en Python tenga
una referencia que funcione.

## Licencia

[MIT](./LICENSE) — usa, modifica, vende, distribuye, lo que necesites.
Atribución agradecida pero no exigida más allá del aviso de copyright.

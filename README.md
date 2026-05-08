# SIS Facturador

> **API REST de facturación electrónica SUNAT (Perú) en Python nativo —
> validada en producción real.**

[![Python](https://img.shields.io/badge/python-3.11%2B-3776AB?logo=python&logoColor=white)](https://www.python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](./LICENSE)
[![Status](https://img.shields.io/badge/status-production-brightgreen.svg)](#production-validated)
[![SUNAT](https://img.shields.io/badge/SUNAT-validated-success.svg)](#production-validated)

Genera Facturas (`01`) y Boletas (`03`) UBL 2.1, las firma con XMLDSig
RSA-SHA256, las envía por SOAP al webservice del contribuyente (SEE-DSC) y
persiste el CDR aceptado.

---

## ¿Por qué Python?

El ecosistema de facturación electrónica peruana está **dominado por
PHP/Laravel** (Greenter, Mifact, q8factura, NubeFacT, Tumi-soft). Casi toda la
documentación pública, las librerías y los foros están en PHP. Para un equipo
que vive en el mundo Python — FastAPI, Django, data pipelines, ML — eso obliga
a operar wrappers, sub-procesos PHP o re-implementar.

**SIS Facturador es Python nativo de extremo a extremo:**

- `signxml` para la firma XMLDSig (no `phpseclib`)
- `lxml` + `Jinja2` para UBL 2.1 (no `DOMDocument` de PHP)
- `zeep` para el SOAP a SUNAT (no `SoapClient`)
- `FastAPI` + `Pydantic v2` para la HTTP API (no Laravel)

No es un wrapper. Es la implementación end-to-end del estándar SUNAT en stack
Python moderno. El objetivo es ser la **referencia abierta para devs Python
peruanos** que hoy tienen que portar código de PHP.

---

## Production-validated

El pipeline emitió los siguientes comprobantes reales contra `e-factura.sunat.gob.pe`
el **2026-05-08**:

| Tipo    | Serie-Número | Status     | Code | Ticket SUNAT          |
|---------|--------------|------------|------|------------------------|
| Boleta  | `B001-1`     | `accepted` | `0`  | `202620668493873`     |
| Factura | `F001-1`     | `accepted` | `0`  | `202620668506859`     |

Ambos figuran como **Procesado** en el portal SOL del contribuyente bajo
*Empresas → Comprobantes de pago → SEE - Del Contribuyente y Envío de Documentos
→ Consultar Envíos de CPE*.

---

## Stack

| Capa             | Tecnología                                    |
|------------------|-----------------------------------------------|
| HTTP API         | FastAPI 0.115 + Pydantic v2 + Uvicorn         |
| UBL 2.1          | `lxml` 5.x + `Jinja2` 3.x                     |
| Firma XMLDSig    | `signxml` 4.x + `cryptography` 44.x (RSA-SHA256, Exclusive C14N) |
| SOAP a SUNAT     | `zeep` 4.x (WSDL bundlados localmente)        |
| Persistencia     | Supabase Postgres (`SQLAlchemy 2.0` + `psycopg 3`) + Supabase Storage |
| Hosting (default) | Vercel Hobby + Fluid Compute (300s)          |

---

## Quick-start

```powershell
# 1. Clonar
git clone https://github.com/dukex57/sis-facturador.git
cd sis-facturador

# 2. Entorno virtual
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 3. Dependencias
pip install -r requirements.txt

# 4. Configurar envs (cert MODDATOS público de SUNAT para pruebas)
Copy-Item .env.example .env
# Editar .env si quieres usar tu cert real

# 5. Correr
uvicorn app.main:app --reload
```

Healthcheck: `GET http://localhost:8000/v1/health`
OpenAPI: `http://localhost:8000/docs`

---

## Flujo

```
   POST /v1/invoices
        │
        ▼
   schemas.InvoiceCreate  (Pydantic validation)
        │
        ▼
   ubl.builder.build_invoice_xml   ──► UBL 2.1 sin firmar
        │
        ▼
   signer.xmldsig.sign_invoice_xml ──► XML firmado (ds:Signature en
        │                              cac:UBLExtensions/ExtensionContent)
        ▼
   sunat.packager.pack_invoice     ──► ZIP {ruc}-{tipo}-{serie}-{num}.zip
        │
        ▼
   sunat.client.send_bill          ──► SOAP a e-factura.sunat.gob.pe
        │
        ▼
   sunat.packager.unpack_cdr       ──► CDR XML (ResponseCode=0 si aceptado)
        │
        ▼
   storage.upload_xml + .upload_cdr ──► Supabase Storage / filesystem
        │
        ▼
   models.Invoice (insert)         ──► Postgres
```

---

## Modos de deploy

| Modo                         | Estado          | Hosting target          | Casos de uso                                  |
|------------------------------|-----------------|-------------------------|-----------------------------------------------|
| **Single-tenant Vercel**     | ✅ Implementado | Vercel Hobby + Supabase | 1 cliente = 1 deploy. Comercio individual, freelancer. |
| **Multi-tenant Provider K8s**| 📋 Doc conceptual | GKE / EKS / DOKS       | SaaS provider, holding con N RUCs, contadores. |

El código actual cubre el modo single-tenant. La arquitectura del modo provider
está documentada conceptualmente en `docs/DEPLOY_PROVIDER.md` (a publicar) e
incluirá auth por API key, RLS por tenant, vault para certificados, rate
limiting con Redis y observability stack — todo activable por env vars sin
ramificar el código (regla *cero ramas por modo*).

---

## Para empezar

> Los enlaces a `docs/` se publicarán en la siguiente fase del repo. Por ahora
> el quick-start de arriba es suficiente para correr local con cert MODDATOS.

- 📦 `docs/INSTALL.md` — instalación técnica paso a paso (clonar, venv, cert, primer test).
- 🏛️ `docs/SUNAT_SETUP.md` — onboarding operativo SUNAT (crear secundario, marcar permisos exactos, registrar cert, esperar 24h).
- 🔐 `docs/SIGNING.md` — showcase técnico de la firma XMLDSig (XAdES vs XMLDSig puro, ubicación de `ds:Signature`, gotchas).

## Documentación completa

- `docs/ARCHITECTURE.md` — capas y diagrama Mermaid.
- `docs/UBL.md` — UBL 2.1 aplicado a SUNAT (catálogos, atributos obligatorios).
- `docs/SUNAT.md` — protocolo SOAP, errores, marco normativo 2024-2026.
- `docs/DEPLOY_VERCEL.md` — deploy single-tenant en Vercel + Supabase.
- `docs/DEPLOY_PROVIDER.md` — arquitectura conceptual multi-tenant en Kubernetes.
- `docs/API.md` — referencia copy-paste de endpoints.
- `docs/TROUBLESHOOTING.md` — runbook end-to-end por código de error.

---

## Errores SUNAT comunes

| Code  | Causa típica                                          | Acción                                                   |
|-------|-------------------------------------------------------|----------------------------------------------------------|
| `0102`| Credenciales SOL inválidas                            | Verificar `SUNAT_USER` con sufijo `<RUC><USER>`.         |
| `0111`| Cache 24h post-Grabar permisos del secundario SOL     | Esperar 24h calendario. No es bug del código.            |
| `2800`| DNI como receptor en factura tipo 01                  | Usar RUC, o emitir como boleta tipo 03.                  |
| `3244`| Falta `cac:PaymentTerms` post `AccountingCustomerParty` | Verificar template UBL.                                |
| `4242`| `AddressTypeCode` con ubigeo en lugar de `"0000"`     | Usar el código de establecimiento, no ubigeo.            |

Detalle completo en `docs/SUNAT.md` + `docs/TROUBLESHOOTING.md`.

---

## Roadmap

- [x] Factura tipo `01` end-to-end (validada en prod).
- [x] Boleta tipo `03` end-to-end (validada en prod).
- [ ] Nota de Crédito (`07`).
- [ ] Nota de Débito (`08`).
- [ ] Comunicación de baja (sendSummary async + Vercel Cron).
- [ ] Resumen diario de boletas.
- [ ] PDF con QR (WeasyPrint).
- [ ] Auth por API key (multi-tenant prep).
- [ ] Soporte OSE (operador de servicios electrónicos).
- [ ] Guía de Remisión (otro WSDL).
- [ ] Implementación del modo provider multi-tenant en K8s.

---

## Estructura

```
api/index.py              entry-point Vercel
app/
  main.py                 FastAPI app + middleware + healthcheck
  config.py               pydantic-settings (envs)
  database.py             SQLAlchemy + psycopg v3
  security/               cert .pfx loader (base64)
  storage/                local + Supabase Storage adapters
  ubl/                    UBL 2.1 generator + Jinja2 templates
  signer/                 XMLDSig RSA-SHA256
  sunat/                  zeep SOAP client + WSDLs bundlados
  models/                 SQLAlchemy ORM
  schemas/                Pydantic v2
  services/               orquestación
  routers/                endpoints REST
scripts/                  bootstrap_db, verify_cert, sendbill_{beta,prod,prod_boleta}
migrations/               SQL plano para Supabase SQL editor
tests/                    unit + integration + e2e (markers: beta)
```

---

## Acerca de

Construido por **Luis Luza M.** ([@dukex57](https://github.com/dukex57)) en Lima,
Perú. Producto en producción real para clientes del sistema SIS y proyecto
abierto de portafolio.

Si te ayudó o quieres adaptarlo para tu negocio, dale ⭐ y abre un Issue para
preguntas concretas. Pull requests bienvenidos.

## Licencia

[MIT](./LICENSE) © 2026 Luis Luza M.

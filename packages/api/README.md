# sis-facturador

Microservicio HTTP que envuelve [pe-invoicing](../core) y agrega
persistencia, storage y deploy en Vercel.

Es un paquete privado del workspace — no se publica a PyPI. La forma de
correrlo es clonar el repo padre y seguir
[`docs/INSTALL.md`](../../docs/INSTALL.md).

## Qué hace

- Emisión de **factura** (`01`) y **boleta** (`03`): `POST /v1/invoices`,
  `GET /v1/invoices/{id}` (FastAPI).
- Emisión de **nota de crédito** (`07`) referenciando una factura/boleta
  previa: `POST /v1/credit-notes`, `GET /v1/credit-notes/{id}`.
- Emisión de **guía de remisión remitente** (`09`) por la Nueva GRE REST:
  `POST /v1/despatch-advices`, `GET /v1/despatch-advices/{id}`. Requiere
  `GRE_CLIENT_ID` / `GRE_CLIENT_SECRET` en `.env` (Credenciales API SUNAT,
  distintas del usuario SOL).
- Orquesta el pipeline del SDK (build → sign → zip → sendBill/sendGre → CDR).
- Persiste comprobantes en Postgres (Supabase). Tablas `invoices`,
  `credit_notes` y `despatch_advices`.
- Sube XML firmado y CDR a Supabase Storage.
- Healthchecks `/v1/health` y `/v1/health/cert`.

## Por qué está separado del core

El SDK `pe-invoicing` no tiene FastAPI ni SQLAlchemy entre sus
dependencias — eso lo hace importable desde cualquier app Python (Django,
Flask, scripts CLI, lambdas) sin arrastrar opinión sobre web framework
ni ORM. Si necesitas solo la firma, no levantas un servicio.

Este paquete agrega esa capa cuando la quieres.

## Estructura

```
src/sis_facturador/
├── main.py            FastAPI app + middleware + healthchecks
├── config.py          pydantic-settings (lee .env)
├── database.py        SQLAlchemy + psycopg v3
├── sunat_runtime.py   caches del SDK (cert, zeep client) leyendo settings
├── models/            ORM SQLAlchemy (invoice, credit_note, despatch_advice)
├── schemas/           Pydantic v2 (invoice, credit_note, despatch_advice)
├── services/          orquestación que usa pe_invoicing
├── routers/           endpoints REST (invoices, credit_notes, despatch_advices)
└── storage/           adaptadores local + Supabase Storage
```

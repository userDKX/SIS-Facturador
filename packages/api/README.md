# sis-facturador

Microservicio HTTP que envuelve [pe-invoicing](../core) y agrega
persistencia, storage y deploy en Vercel.

Es un paquete privado del workspace — no se publica a PyPI. La forma de
correrlo es clonar el repo padre y seguir
[`docs/INSTALL.md`](../../docs/INSTALL.md).

## Qué hace

- Expone `POST /v1/invoices` y `GET /v1/invoices/{id}` (FastAPI).
- Orquesta el pipeline del SDK (build → sign → zip → sendBill → CDR).
- Persiste comprobantes en Postgres (Supabase).
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
├── models/            ORM SQLAlchemy
├── schemas/           Pydantic v2
├── services/          orquestación que usa pe_invoicing
├── routers/           endpoints REST
└── storage/           adaptadores local + Supabase Storage
```

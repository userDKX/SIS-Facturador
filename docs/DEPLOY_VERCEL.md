# Deploy single-tenant en Vercel

Esta es la forma simple, gratuita y operativa para un cliente individual:
1 deploy en Vercel + 1 proyecto en Supabase. Es lo que está implementado
y validado en producción real.

Si necesitas servir a varios RUCs desde una sola instancia, no es esto —
léete [`DEPLOY_PROVIDER.md`](./DEPLOY_PROVIDER.md).

## Por qué Vercel funciona acá

- **Fluid Compute** activado por default desde abril 2025: una sola función
  serverless puede ejecutar varias requests simultáneas durante su lifetime
  (warm). Reduce coldstart entre requests cercanas.
- **Max duration en Hobby**: 300 segundos. SUNAT en sus peores momentos
  responde en ~30s, así que tienes margen amplio.
- **Bundle Python en Hobby**: 500 MB uncompressed. El proyecto entero con
  deps pesa ~120 MB.
- **Cron Jobs**: 1 minuto de mínimo. Útil para futuros polling de tickets
  asíncronos (NC, baja, resumen diario).

Lo que **no** maneja Vercel: persistencia de filesystem, procesos largos
(>300s), conexiones persistentes a Postgres. Por eso usamos Supabase para
datos y Storage.

## Requisitos antes de empezar

Tienes que tener:

1. Cuenta en GitHub con el repo del facturador (puede ser fork del público).
2. Cuenta en Vercel (gratis, login con GitHub).
3. Proyecto Supabase (gratis hasta 500 MB BD + 1 GB Storage).
4. Cert digital `.pfx` real con su password.
5. Usuario secundario SOL configurado y con 24h ya pasadas (ver
   [`SUNAT_SETUP.md`](./SUNAT_SETUP.md)).

## Paso 1 — Crear el proyecto Supabase

Entra a https://supabase.com, "New Project". Pones nombre, password, región
(la más cercana a Perú es `us-east-2 (Ohio)` para Vercel pero
`sa-east-1 (São Paulo)` da menor latencia desde Lima).

Una vez creado, anda a:

- **Project Settings → Database → Connection string → Direct connection**.
  Copia esa URL. Va a `DATABASE_URL`.
- **Project Settings → API**. Copia `URL` (va a `SUPABASE_URL`) y
  `service_role` key (va a `SUPABASE_SERVICE_KEY`). El service_role bypassa
  RLS — nunca lo expongas al cliente.

### Crear el bucket de Storage

En la sidebar de Supabase: **Storage → New bucket**. Nombre:
`comprobantes`. Público: **No** (privado, solo accesible por service key).

### Aplicar las migraciones

En Supabase: **SQL Editor → New query**. Copia y pega el contenido de
`migrations/001_invoices.sql` y ejecuta. Crea la tabla `invoices` con sus
índices y constraints.

## Paso 2 — Pasar el cert a base64

```powershell
[Convert]::ToBase64String([IO.File]::ReadAllBytes("MICERT.pfx")) | Set-Clipboard
```

```bash
base64 -w0 MICERT.pfx
```

Copia ese string completo (es largo, no lo pierdas).

## Paso 3 — Crear el proyecto en Vercel

En https://vercel.com:

- "Add New… → Project"
- Selecciona el repo del facturador
- Framework Preset: "Other" (Vercel detectará `vercel.json` automáticamente)
- Build Command: dejar vacío
- Output Directory: dejar vacío
- Install Command: dejar vacío

**No** despliegues todavía — primero las env vars.

## Paso 4 — Configurar env vars

En Vercel: **Project Settings → Environment Variables**. Marca las tres
columnas (`Production`, `Preview`, `Development`) salvo donde indique lo
contrario.

| Variable                | Valor                                                  | Notas                                                 |
|-------------------------|--------------------------------------------------------|-------------------------------------------------------|
| `MODE`                  | `prod`                                                 | Para Preview y Development pon `beta`                 |
| `DATABASE_URL`          | (la URL de Supabase del paso 1)                        |                                                       |
| `STORAGE_BACKEND`       | `supabase`                                             | En Vercel el filesystem es efímero, no uses `local`   |
| `SUPABASE_URL`          | (de Project Settings → API)                            |                                                       |
| `SUPABASE_SERVICE_KEY`  | (de Project Settings → API)                            | Sensible — marcar como Sensitive en Vercel             |
| `SUPABASE_BUCKET`       | `comprobantes`                                         |                                                       |
| `SUNAT_RUC`             | tu RUC                                                 |                                                       |
| `SUNAT_USER`            | el username del secundario (sin RUC adelante)          | Ej. `FACSIS11`                                        |
| `SUNAT_PASSWORD`        | la clave del secundario                                | Sensible                                              |
| `CERT_PFX_BASE64`       | (el base64 del paso 2)                                 | Sensible — string largo                                |
| `CERT_PASSWORD`         | la clave del `.pfx`                                    | Sensible                                              |

## Paso 5 — Deploy

Click "Deploy". El primer build tarda ~3-5 minutos (instala deps Python en
Vercel). Cuando termine, te da una URL tipo `sis-facturador-xxx.vercel.app`.

Verifica:

```bash
curl https://sis-facturador-xxx.vercel.app/v1/health
# {"status":"ok","mode":"prod"}

curl https://sis-facturador-xxx.vercel.app/v1/health/cert
# {"common_name":"...","serial":"...","not_valid_after":"..."}
```

Si `health/cert` te devuelve 500, revisa los logs de Vercel — probablemente
el `CERT_PFX_BASE64` se pegó truncado o el password está mal.

## Paso 6 — Mandar tu primer comprobante real

Desde tu máquina (no desde Vercel):

```bash
curl -X POST https://sis-facturador-xxx.vercel.app/v1/invoices \
  -H "Content-Type: application/json" \
  -d '{
    "tipo_documento": "03",
    "serie": "B001",
    "numero": 1,
    "moneda": "PEN",
    ...
  }'
```

Si todo está bien, response 200 con el `Invoice` persistido y URLs al XML
firmado y al CDR en Supabase Storage.

## Modelo 1-cliente = 1-deploy

El código actual asume un solo RUC por deploy. Para servir a un segundo
cliente:

- Forkea o clona el repo (puedes seguir apuntando al mismo origin).
- Crea un nuevo proyecto Supabase para ese cliente (BD + Storage separados).
- Crea un nuevo proyecto Vercel apuntando al mismo repo.
- Configura env vars con el nuevo RUC, su cert, sus credenciales SOL, sus
  URLs de Supabase.

Aislamiento total entre clientes (datos, cert, credenciales). El costo
escala lineal: cada cliente nuevo es otro Vercel Hobby + otro Supabase
free.

## Costos esperados

A 2026-05, todo gratis:

| Recurso                       | Tier free                                          |
|-------------------------------|----------------------------------------------------|
| Vercel Hobby                  | 100 GB bandwidth/mes, 100h compute/mes             |
| Supabase Free                 | 500 MB DB, 1 GB Storage, 5 GB egress/mes           |

En la práctica, un comercio individual emitiendo ~1000 comprobantes al mes
está muy lejos de los límites. El cuello típico es Storage si guardas XML
firmados grandes (~10 KB cada uno) sin limpieza — ahí va a tronar a varios
miles de comprobantes.

## Limitaciones del modelo single-tenant

Cosas que el modelo actual **no** hace y conviene tener claras:

- **No hay autenticación en la API.** Cualquiera con la URL puede emitir
  comprobantes. Asume que la URL solo la conoce el cliente del facturador
  (típicamente el backend del SIS) y vive detrás de su propia auth. Si vas
  a exponer públicamente, **necesitas** poner Cloudflare Access, una API
  key, o algo parecido por delante.
- **No hay rate limiting.** Si te DDOSean, Vercel te corta antes que nada,
  pero por dentro la app no se defiende.
- **No hay audit logs** explícitos más allá de la tabla `invoices`.
- **No hay multi-tenant.** Para varios RUCs, necesitas varios deploys.

Si necesitas todas estas cosas, el modo provider en
[`DEPLOY_PROVIDER.md`](./DEPLOY_PROVIDER.md) las cubre.

## Cuando algo se rompe en Vercel

| Síntoma                                                       | Probable causa                                                                |
|---------------------------------------------------------------|-------------------------------------------------------------------------------|
| `health/cert` devuelve 500                                    | `CERT_PFX_BASE64` pegado truncado o `CERT_PASSWORD` mal                        |
| `health` 200 pero envío de invoice da 500                     | `DATABASE_URL` no apunta a Supabase, o las migraciones no se aplicaron         |
| Endpoint timeout a los 300s                                   | Stack se quedó en `_get_client()` (WSDL local no está); revisa el bundle       |
| `0102` desde Vercel pero localmente funciona                   | Las env vars de prod tienen otra cuenta SOL — revisa `SUNAT_USER` y password   |
| `0111` en producción                                          | Esperaste menos de 24h después de Grabar permisos — asunto de SUNAT, no Vercel |

Los logs de Vercel los ves en **Project → Deployments → (último) → Logs →
Functions**. Para errores en runtime, busca por nivel `error` o filtra por
endpoint.

## Cron Jobs (cuando llegue Notas y resumen diario)

Cuando el roadmap llegue a comunicación de baja y resumen diario, vamos a
necesitar polling asíncrono de tickets SUNAT. Vercel Cron sirve para eso:

```json
// vercel.json
{
  "crons": [
    { "path": "/v1/tasks/poll-tickets", "schedule": "*/5 * * * *" }
  ]
}
```

Cada 5 minutos golpea el endpoint, que internamente busca tickets pending y
llama `getStatus`. Hobby tier permite hasta 2 cron jobs.

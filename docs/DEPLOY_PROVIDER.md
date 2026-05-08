# Deploy multi-tenant en Kubernetes — arquitectura conceptual

> **Estado: conceptual.** Este documento describe la arquitectura objetivo
> del modo provider. **Aún no hay código que la implemente.** El roadmap
> al final del doc lista qué falta construir.

Este modo es para casos donde una sola instancia del facturador sirve a
varios RUCs distintos. Casos típicos:

- Un **SaaS de facturación** que cobra por comprobante y onboarda múltiples
  empresas.
- Un **holding** con varios RUCs que comparte la infra de facturación
  entre todas sus empresas hijas.
- Un **contador o estudio contable** que emite por sus clientes.
- Un **proveedor que ofrece facturación electrónica como servicio**
  white-label.

La diferencia esencial con el modo Vercel single-tenant: ahí cada RUC tiene
su deploy aislado; acá conviven en una sola instancia con isolation lógica
(no física) por tenant. Eso te obliga a meter capas de seguridad que el
modo single-tenant no necesita.

## Arquitectura objetivo

```mermaid
flowchart TB
    Client[Cliente HTTP del tenant]

    subgraph Edge[Edge / TLS]
      LB[Ingress NGINX/Traefik<br/>cert-manager TLS]
    end

    subgraph App[Cluster K8s managed]
      direction TB
      AuthMW[API Key Auth Middleware<br/>resuelve tenant_id]
      RateLimit[Rate Limit<br/>Redis backed]
      TenantCtx[Tenant Context Injector]
      App1[Pod FastAPI #1]
      App2[Pod FastAPI #2]
      AppN[Pod FastAPI #N]
      HPA[HPA: scale on CPU/RPS]
    end

    subgraph Secrets[Secrets layer]
      Vault[(Vault / SOPS / Sealed Secrets)]
      CertCache[Cert in-memory cache<br/>per pod, TTL 5min]
    end

    subgraph Data[Data layer]
      DB[(Postgres managed<br/>RLS por tenant_id)]
      Storage[(S3-compatible<br/>R2 / S3 / MinIO)]
      Audit[(Audit log<br/>append-only)]
    end

    subgraph Obs[Observability]
      Prom[Prometheus]
      Loki[Loki]
      Grafana[Grafana]
    end

    Client -->|HTTPS<br/>X-API-Key| LB
    LB --> AuthMW
    AuthMW --> RateLimit
    RateLimit --> TenantCtx
    TenantCtx --> App1
    TenantCtx --> App2
    TenantCtx --> AppN
    HPA -.controls.-> App1

    App1 -->|cert por tenant| Vault
    Vault --> CertCache
    CertCache -.serves.-> App1

    App1 -->|tenant_id en RLS| DB
    App1 -->|prefijo {tenant_id}/| Storage
    App1 -->|append| Audit

    App1 -.metrics.-> Prom
    App1 -.logs JSON.-> Loki
    Prom --> Grafana
    Loki --> Grafana
```

## Resolución del tenant en cada request

Dos opciones razonables:

- **Header `X-Tenant-Id`** (más simple). El cliente del facturador (su
  backend) manda el header con cada request. La API key autentica, el
  header dice de qué tenant es.
- **Subdominio** `{tenant}.api.facturador.example.com` resuelto por el
  middleware. Más limpio para portales con UI por tenant, pero requiere
  wildcard DNS y wildcard cert.

Recomendación: arrancar con `X-Tenant-Id`. Si después se quiere agregar
subdominio, se hace sin romper compatibilidad (el subdominio resolver
inyecta el header internamente).

El middleware:

```python
# Esbozo conceptual — no existe en el código aún
@app.middleware("http")
async def tenant_resolver(request: Request, call_next):
    api_key = request.headers.get("X-API-Key")
    tenant_id = request.headers.get("X-Tenant-Id")

    tenant = authenticate_and_resolve(api_key, tenant_id)
    if not tenant:
        return JSONResponse({"detail": "Invalid credentials"}, status_code=401)

    request.state.tenant = tenant
    return await call_next(request)
```

## Aislamiento de datos: RLS sobre Postgres

Hay dos patrones típicos:

- **Schema-per-tenant.** Cada tenant tiene su propio schema (`tenant_001`,
  `tenant_002`...) con la misma tabla `invoices` adentro. Aislamiento
  fuerte, escala feo (cada migration tiene que aplicarse N veces, los
  schemas crecen sin control).
- **Row-level security (RLS).** Una sola tabla `invoices` con columna
  `tenant_id`, política de RLS que filtra por
  `current_setting('app.current_tenant')::int`. La aplicación setea ese
  setting al inicio de cada request. Una sola migración para todos.

Para este proyecto, **RLS gana**. Las queries son simples, la cantidad de
tenants puede crecer sin causar pain operacional, y SUNAT no requiere
isolation físico (solo lógico).

Ejemplo de la política:

```sql
ALTER TABLE invoices ENABLE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation ON invoices
  FOR ALL
  USING (tenant_id = current_setting('app.current_tenant')::int);
```

El middleware después de resolver el tenant ejecuta:

```sql
SET app.current_tenant = 42;
```

Por la sesión de esa request. Cualquier query a `invoices` sale filtrada
por tenant transparente.

## Manejo de certificados por tenant

Esto es lo más sensible del diseño multi-tenant. Cada tenant tiene su
propio `.pfx` y password — y SUNAT exige que cada comprobante esté firmado
con el cert del RUC emisor (no se puede compartir cert entre tenants).

Opciones de almacenamiento:

| Opción                              | Pros                                         | Contras                                          |
|-------------------------------------|----------------------------------------------|--------------------------------------------------|
| **HashiCorp Vault**                 | Estándar enterprise, audit logs, rotación    | Más infra que mantener, costo de licencia OSS    |
| **AWS Secrets Manager** (en EKS)    | Integrado con IAM, audit nativo              | Vendor lock-in si no estás en AWS                |
| **Doppler / Infisical**             | Managed, UI agradable, free tier             | Dependes del proveedor                           |
| **K8s Secrets cifrados con SOPS+age**| Cero infra extra, en git encriptado          | Rotación manual, no audit out-of-the-box          |

Recomendación para empezar: **Doppler** o **Infisical** si no tienes
Vault desplegado. Ambos tienen SDKs Python y free tier suficiente para
~50 tenants.

Carga del cert:

- En boot del pod: precarga todos los certs activos. Rápido por request,
  consume RAM proporcional a tenants × tamaño cert (~5 KB cada uno, así
  que 1000 tenants = 5 MB, manejable).
- Lazy con cache: primer request del tenant carga el cert del vault, lo
  cachea en memoria con TTL de 5 minutos. Mejor escalabilidad pero
  primera request del día es lenta.

Para empezar, lazy + cache es más simple.

## Auth: API keys por tenant

Tabla `tenant_api_keys`:

```sql
CREATE TABLE tenant_api_keys (
  id            BIGSERIAL PRIMARY KEY,
  tenant_id     INT NOT NULL REFERENCES tenants(id),
  key_hash      TEXT NOT NULL,           -- bcrypt o argon2 hash
  prefix        TEXT NOT NULL,           -- primeros 8 chars en plain, para identificar
  scope         TEXT[] NOT NULL,         -- ['invoices:create', 'invoices:read']
  rate_limit_rpm INT,                    -- override del default
  created_at    TIMESTAMPTZ DEFAULT NOW(),
  expires_at    TIMESTAMPTZ,
  revoked_at    TIMESTAMPTZ
);

CREATE INDEX ON tenant_api_keys(prefix) WHERE revoked_at IS NULL;
```

El cliente envía `X-API-Key: sf_live_abc123…`. El middleware extrae el
prefix, busca por índice, hace bcrypt compare, autentica y resuelve
tenant.

Para portales web (futuro): JWT firmado por el provider, revocable via
denylist en Redis.

## Rate limiting

Por API key + por tenant. Backend Redis (sliding window con `INCR` + `TTL`
o el algoritmo de fixed window). Defaults configurables:

- Por API key: 60 requests/minuto, 1000/hora.
- Por tenant (suma de todas sus keys): 1000 requests/minuto.

Al exceder, devuelve 429 con header `Retry-After`. Si SUNAT está caído y
todos los tenants están reintentando, el rate limit por tenant evita que
uno solo monopolice el cluster.

## Audit logs

Tabla append-only:

```sql
CREATE TABLE audit_log (
  id          BIGSERIAL PRIMARY KEY,
  tenant_id   INT NOT NULL,
  actor       TEXT NOT NULL,           -- api_key prefix o user id
  action      TEXT NOT NULL,           -- 'invoice.create', 'invoice.cancel', ...
  resource    TEXT,                    -- 'F001-1', 'B001-23', ...
  ip          INET,
  user_agent  TEXT,
  metadata    JSONB,                   -- payload sanitizado, response status
  created_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX ON audit_log(tenant_id, created_at DESC);
```

Para compliance: replicación periódica (cron diario) a almacenamiento WORM
(S3 con Object Lock, GCS Bucket Lock) — los registros tributarios no se
pueden borrar.

## Helm chart layout (no implementado)

Estructura de archivos esperada cuando se construya:

```
deploy/helm/sis-facturador/
├── Chart.yaml
├── values.yaml             ← defaults
├── values.gke.yaml         ← override para GKE
├── values.eks.yaml         ← override para EKS
├── values.doks.yaml        ← override para DigitalOcean
├── templates/
│   ├── deployment.yaml
│   ├── service.yaml
│   ├── ingress.yaml
│   ├── hpa.yaml            ← horizontal pod autoscaler
│   ├── configmap.yaml
│   ├── secret.yaml         ← solo non-cert secrets (DB url, Redis url)
│   ├── servicemonitor.yaml ← Prometheus operator
│   └── networkpolicy.yaml  ← pod-to-pod restricción
└── README.md
```

`values.yaml` con las variables por entorno (DB url, Redis url, Vault url,
ingress class, replicas, recursos).

## Stack de observabilidad

Métricas (Prometheus):

- `requests_total{method,path,status,tenant_id}` — counter
- `request_duration_seconds{method,path,tenant_id}` — histogram
- `sunat_send_duration_seconds{result,tenant_id}` — histogram
- `cdr_status_total{status,tenant_id}` — counter (`accepted`,
  `accepted_with_obs`, `rejected`)
- `cert_expiry_days{tenant_id}` — gauge (alertar a 30 días, 7 días)

Logs (Loki):

- Estructurados JSON con `tenant_id`, `request_id`, `actor`.
- Nunca loggear el `.pfx`, password, payload completo del cert. Sí: hashes,
  prefijos, timestamps.

Dashboards Grafana:

- Health del cluster (CPU, memoria, restarts).
- Salud de SUNAT por tenant (latencia, % rechazos).
- Top tenants por volumen.
- Alertas: cert por vencer, % rechazos > 5% en última hora, SUNAT
  unreachable >5min.

## Comparativa GKE / EKS / DOKS

| Aspecto            | GKE                            | EKS                             | DOKS                             |
|--------------------|--------------------------------|---------------------------------|----------------------------------|
| Costo control plane| Gratis (Standard) / $0.10/h Autopilot | $0.10/h                  | Gratis                           |
| Managed Postgres   | Cloud SQL (caro pero sólido)   | RDS (cualquier flavor)          | Managed PostgreSQL ($15/mes inicio) |
| Storage S3-compat  | GCS                            | S3                              | Spaces (compat S3)               |
| Networking         | VPC + Cloud Load Balancing     | VPC + ALB                       | VPC + Load Balancer ($12/mes)    |
| Observability nativa | Cloud Operations (Stackdriver)| CloudWatch                      | Limitada — usar Prom+Loki self-hosted |
| Recomendación      | Si ya estás en GCP             | Si ya estás en AWS              | Para empezar barato y crecer     |

Para un provider que arranca: **DOKS** + Spaces + Managed PostgreSQL +
Prometheus/Loki self-hosted en el mismo cluster. Costo total para un
cluster pequeño (3 nodos s-2vcpu-4gb, DB managed, LB): ~$80/mes. Escala
hasta varios cientos de tenants antes de necesitar bumping.

## Migración desde el modo Vercel

La regla heredada del SIS: **cero ramas por modo**. El código no debe
tener `if MODE == 'multi_tenant'` — todo se controla por configuración
opt-in.

Plan progresivo (no implementado, conceptual):

1. Agregar columna `tenant_id` opcional a `invoices` (default a un valor
   sentinel en el modo single-tenant).
2. Agregar middleware de tenant resolver, activable por env
   (`TENANT_RESOLVER=header|subdomain|disabled`). Default `disabled`
   (modo Vercel actual).
3. Agregar tabla `tenants` y `tenant_api_keys` solo si el modo está
   activado.
4. Agregar abstracción de cert provider: `EnvCertProvider` (modo Vercel,
   carga del env), `VaultCertProvider` (modo provider).
5. RLS opt-in por env (`ENABLE_RLS=true`).

El modo Vercel queda como caso particular: tenant resolver `disabled`,
cert provider `env`, RLS off.

## Roadmap de implementación

Lo que falta construir para tener el modo provider operativo:

- [ ] Tabla `tenants` con migration
- [ ] Tabla `tenant_api_keys` con migration
- [ ] Middleware tenant resolver (header + subdomain + disabled)
- [ ] Middleware API key auth (bcrypt compare, scope check)
- [ ] Abstracción `CertProvider` con impls `Env` y `Vault` (Doppler,
      Infisical, AWS Secrets Manager)
- [ ] Migration RLS opt-in para `invoices`
- [ ] Middleware `SET app.current_tenant` por request
- [ ] Tabla `audit_log` con migration + writer middleware
- [ ] Rate limiting middleware con backend Redis
- [ ] Métricas Prometheus + endpoint `/metrics`
- [ ] Logging estructurado JSON
- [ ] Dockerfile producción multi-stage
- [ ] Helm chart con `values.{gke,eks,doks}.yaml`
- [ ] Tests multi-tenant
- [ ] Doc de operación (runbook on-call)

Estimado: ~6-8 semanas de trabajo concentrado, dependiendo del scope final
de auth (solo API key vs API key + JWT + portal admin).

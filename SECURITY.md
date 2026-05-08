# Security Policy

## Reporting a vulnerability

If you discover a security vulnerability in **SIS Facturador**, please **do not
open a public GitHub issue**. Instead, report it privately:

- Open a [private security advisory](https://github.com/dukex57/sis-facturador/security/advisories/new)
  on this repository, or
- Email the maintainer (contact in the GitHub profile).

We aim to acknowledge reports within 72 hours and to publish a fix or mitigation
within 14 days for critical issues.

Please include, when possible:

- Affected version (commit SHA or release tag).
- Reproduction steps or proof of concept.
- Impact assessment (what an attacker can do).

## Supported versions

Until the project reaches `1.0.0`, only the latest minor release is supported.

| Version | Supported |
|---------|-----------|
| `0.1.x` | ✅        |

## Sensitive material handling

This project signs and submits real tax documents to SUNAT. The following items
are sensitive and **must never** be committed, logged, or shared:

| Item                          | Where it lives                         | Notes                                                |
|-------------------------------|----------------------------------------|------------------------------------------------------|
| Digital certificate `.pfx`    | `CERT_PFX_BASE64` env var (base64)     | Not on filesystem. Not in DB. Not in logs.           |
| Certificate password          | `CERT_PASSWORD` env var                | Distinct from SOL password.                          |
| SOL secondary-user password   | `SUNAT_PASSWORD` env var               | Rotate immediately if exposed.                       |
| Database connection string    | `DATABASE_URL` env var                 | Use service role key only on the server.             |
| Supabase service key          | `SUPABASE_SERVICE_KEY` env var         | Bypasses RLS — never expose to clients.              |
| Signed `.xml` and CDR files   | `storage/` (gitignored)                | Contain real RUC, amounts, customer data.            |

The repository's `.gitignore` already excludes `.env`, `*.pfx`, `*.p12`, `*.pem`,
`*.key`, `*.crt`, and `storage/`. Verify with `git status` before any commit.

## Incident response

### Certificate compromise

If the `.pfx` is leaked or suspected compromised:

1. **Immediately** revoke it through the issuing CA (RENIEC for ECEP-RENIEC
   certificates).
2. Generate a new certificate and re-register it in SUNAT SOL (production):
   *Empresas → Comprobantes de Pago → SEE-DSC → Servicio de Envío de Documentos
   Electrónicos → Registre aquí su certificado digital*.
3. Update `CERT_PFX_BASE64` and `CERT_PASSWORD` on every deploy.
4. Audit the last 30 days of `Consultar Envíos de CPE` for any unrecognised
   submissions.

### SOL password compromise

1. Log into SOL with the primary user and reset the secondary-user password.
2. Update `SUNAT_PASSWORD` on every deploy.
3. Wait the standard SUNAT propagation window (up to 24h calendar) before
   resuming WS submissions — premature attempts may return `0102`/`0111`.

## Threat model summary (single-tenant Vercel deployment)

- **Public surface**: HTTPS endpoints exposed by Vercel; no auth on the API in
  the current single-tenant model — assume the deployment is reachable only by
  trusted callers (e.g., the SIS backend over an outbound firewall, or a VPN).
- **Data at rest**: Supabase Postgres (managed, encrypted) + Supabase Storage
  bucket with service-key-only access (RLS bypass).
- **Data in transit**: TLS 1.2+ to Vercel; TLS 1.2+ to SUNAT WS.
- **Secrets**: env vars on Vercel (encrypted at rest). The `.pfx` itself never
  touches disk.
- **Out of scope** for the current release: API-key authentication, per-tenant
  isolation, audit logs, rate limiting. These are part of the planned
  multi-tenant provider mode (see `docs/DEPLOY_PROVIDER.md` once published).
